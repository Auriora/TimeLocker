"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Type, Union, List
from functools import wraps
from contextlib import contextmanager
from threading import local

logger = logging.getLogger(__name__)

# Thread-local storage for error context stack
_context_stack = local()


def _get_context_stack() -> List['ErrorContext']:
    """Get the thread-local context stack"""
    if not hasattr(_context_stack, 'stack'):
        _context_stack.stack = []
    return _context_stack.stack


class ErrorContext:
    """
    Enhanced context information for error handling with call stack preservation.
    
    This class provides:
    - Context tracking through the call stack
    - User-friendly error formatting
    - Recovery suggestions based on error type
    - Integration with existing error handling
    
    Requirements addressed:
    - Requirement 8: Error context preservation through ErrorContext
    """

    def __init__(self, 
                 operation: str, 
                 component: str, 
                 error_id: Optional[str] = None,
                 **kwargs):
        """
        Initialize error context.
        
        Args:
            operation: Operation being performed
            component: Component where operation is executing
            error_id: Optional unique identifier for this context
            **kwargs: Additional context metadata
        """
        self.operation = operation
        self.component = component
        self.error_id = error_id or str(uuid.uuid4())
        self.metadata = kwargs
        self.timestamp = datetime.now()
        self.parent_context: Optional['ErrorContext'] = None
        self._recovery_suggestions: List[str] = []
        
        # Capture parent context from stack
        stack = _get_context_stack()
        if stack:
            self.parent_context = stack[-1]

    def add_context(self, key: str, value: Any) -> None:
        """
        Add additional context information.
        
        Args:
            key: Context key
            value: Context value
        """
        self.metadata[key] = value

    def add_recovery_suggestion(self, suggestion: str) -> None:
        """
        Add a recovery suggestion for this error context.
        
        Args:
            suggestion: Recovery suggestion text
        """
        if suggestion and suggestion not in self._recovery_suggestions:
            self._recovery_suggestions.append(suggestion)

    def get_context(self) -> Dict[str, Any]:
        """
        Get all context information including parent contexts.
        
        Returns:
            Dictionary containing all context information
        """
        context = self.to_dict()
        
        # Include parent context chain
        if self.parent_context:
            context['parent_context'] = self.parent_context.get_context()
        
        return context

    def get_recovery_suggestions(self) -> List[str]:
        """
        Get recovery suggestions for this context and parent contexts.
        
        Returns:
            List of recovery suggestions
        """
        suggestions = list(self._recovery_suggestions)
        
        # Include parent suggestions
        if self.parent_context:
            parent_suggestions = self.parent_context.get_recovery_suggestions()
            for suggestion in parent_suggestions:
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions

    def format_error(self, error: Exception) -> str:
        """
        Format error message with context information.
        
        Args:
            error: Exception to format
            
        Returns:
            Formatted error message with context
        """
        lines = []
        
        # Error header
        error_type = type(error).__name__
        lines.append(f"❌ {error_type}: {str(error)}")
        lines.append("")
        
        # Context information
        lines.append("📍 Context:")
        lines.append(f"  Component: {self.component}")
        lines.append(f"  Operation: {self.operation}")
        
        if self.metadata:
            lines.append("  Details:")
            for key, value in self.metadata.items():
                lines.append(f"    • {key}: {value}")
        
        # Parent context chain
        if self.parent_context:
            lines.append("")
            lines.append("📚 Call Stack:")
            parent = self.parent_context
            depth = 1
            while parent:
                indent = "  " * depth
                lines.append(f"{indent}↳ {parent.component}:{parent.operation}")
                parent = parent.parent_context
                depth += 1
        
        # Recovery suggestions
        suggestions = self.get_recovery_suggestions()
        if suggestions:
            lines.append("")
            lines.append("💡 Suggested Actions:")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for logging and serialization.
        
        Returns:
            Dictionary representation of context
        """
        return {
            'error_id': self.error_id,
            'operation': self.operation,
            'component': self.component,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'recovery_suggestions': self._recovery_suggestions
        }

    def __enter__(self) -> 'ErrorContext':
        """Enter context manager - push to stack"""
        _get_context_stack().append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - pop from stack"""
        stack = _get_context_stack()
        if stack and stack[-1] is self:
            stack.pop()
        return False  # Don't suppress exceptions


class ErrorHandler:
    """
    Centralized error handling utility following DRY principles.
    
    Provides consistent error handling patterns across the TimeLocker codebase,
    including logging, context preservation, retry mechanisms, and recovery suggestions.
    
    Requirements addressed:
    - Requirement 8: Error context preservation and recovery suggestions
    """

    def __init__(self):
        self._error_callbacks: Dict[Type[Exception], Callable] = {}
        self._default_callback: Optional[Callable] = None
        self._recovery_suggestion_providers: Dict[Type[Exception], Callable[[Exception, ErrorContext], List[str]]] = {}
        self._register_default_recovery_suggestions()

    def register_error_callback(self, exception_type: Type[Exception], callback: Callable) -> None:
        """
        Register a callback for specific exception types.
        
        Args:
            exception_type: Exception type to handle
            callback: Callback function to execute
        """
        self._error_callbacks[exception_type] = callback
        logger.debug(f"Registered error callback for {exception_type.__name__}")

    def set_default_callback(self, callback: Callable) -> None:
        """
        Set default callback for unhandled exception types.
        
        Args:
            callback: Default callback function
        """
        self._default_callback = callback

    def register_recovery_suggestion_provider(self,
                                             exception_type: Type[Exception],
                                             provider: Callable[[Exception, ErrorContext], List[str]]) -> None:
        """
        Register a recovery suggestion provider for specific exception types.
        
        Args:
            exception_type: Exception type to provide suggestions for
            provider: Function that returns list of recovery suggestions
        """
        self._recovery_suggestion_providers[exception_type] = provider
        logger.debug(f"Registered recovery suggestion provider for {exception_type.__name__}")

    def suggest_recovery(self, exception: Exception, context: Optional[ErrorContext] = None) -> List[str]:
        """
        Generate recovery suggestions for an exception.
        
        Args:
            exception: Exception to generate suggestions for
            context: Optional error context
            
        Returns:
            List of recovery suggestions
        """
        suggestions = []
        
        # Get suggestions from context if available
        if context:
            suggestions.extend(context.get_recovery_suggestions())
        
        # Find provider for this exception type
        provider = self._find_recovery_provider(type(exception))
        if provider:
            try:
                provider_suggestions = provider(exception, context)
                for suggestion in provider_suggestions:
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
            except Exception as e:
                logger.warning(f"Error generating recovery suggestions: {e}")
        
        return suggestions

    def handle_error(self,
                     exception: Exception,
                     context: Optional[ErrorContext] = None,
                     reraise: bool = True) -> Optional[Any]:
        """
        Handle an exception with appropriate logging, callbacks, and recovery suggestions.
        
        Args:
            exception: The exception to handle
            context: Optional context information
            reraise: Whether to reraise the exception after handling
            
        Returns:
            Result from callback if any, None otherwise
        """
        # Add recovery suggestions to context
        if context:
            suggestions = self.suggest_recovery(exception, context)
            for suggestion in suggestions:
                context.add_recovery_suggestion(suggestion)
        
        # Log the error with context
        self._log_error(exception, context)

        # Find and execute appropriate callback
        callback = self._find_callback(type(exception))
        result = None

        if callback:
            try:
                result = callback(exception, context)
            except Exception as callback_error:
                logger.error(f"Error in error callback: {callback_error}")

        if reraise:
            raise exception

        return result

    def _log_error(self, exception: Exception, context: Optional[ErrorContext]) -> None:
        """
        Log error with context information.
        
        Args:
            exception: Exception to log
            context: Optional error context
        """
        if context:
            # Use formatted error message with context
            error_msg = context.format_error(exception)
            logger.error(error_msg, extra=context.to_dict())
        else:
            error_msg = f"{type(exception).__name__}: {exception}"
            logger.error(error_msg)

        # Log stack trace for debugging
        logger.debug("Stack trace:", exc_info=True)

    def _find_callback(self, exception_type: Type[Exception]) -> Optional[Callable]:
        """
        Find appropriate callback for exception type.
        
        Args:
            exception_type: Exception type to find callback for
            
        Returns:
            Callback function or None
        """
        # Check for exact match first
        if exception_type in self._error_callbacks:
            return self._error_callbacks[exception_type]

        # Check for parent class matches
        for registered_type, callback in self._error_callbacks.items():
            if issubclass(exception_type, registered_type):
                return callback

        # Return default callback if available
        return self._default_callback

    def _find_recovery_provider(self, exception_type: Type[Exception]) -> Optional[Callable]:
        """
        Find appropriate recovery suggestion provider for exception type.
        
        Args:
            exception_type: Exception type to find provider for
            
        Returns:
            Provider function or None
        """
        # Check for exact match first
        if exception_type in self._recovery_suggestion_providers:
            return self._recovery_suggestion_providers[exception_type]

        # Check for parent class matches
        for registered_type, provider in self._recovery_suggestion_providers.items():
            if issubclass(exception_type, registered_type):
                return provider

        return None

    def _register_default_recovery_suggestions(self) -> None:
        """Register default recovery suggestion providers for common exception types"""
        
        # File not found errors
        def file_not_found_suggestions(exc: Exception, ctx: Optional[ErrorContext]) -> List[str]:
            suggestions = ["Check that the file path is correct"]
            if ctx and 'path' in ctx.metadata:
                suggestions.append(f"Verify that '{ctx.metadata['path']}' exists")
            suggestions.append("Ensure you have read permissions for the file")
            return suggestions
        
        # Permission errors
        def permission_error_suggestions(exc: Exception, ctx: Optional[ErrorContext]) -> List[str]:
            return [
                "Check file/directory permissions",
                "Ensure you have the necessary access rights",
                "Try running with appropriate privileges if needed"
            ]
        
        # Connection errors
        def connection_error_suggestions(exc: Exception, ctx: Optional[ErrorContext]) -> List[str]:
            return [
                "Check your network connection",
                "Verify the server/service is accessible",
                "Check firewall settings",
                "Retry the operation after a short delay"
            ]
        
        # Value errors
        def value_error_suggestions(exc: Exception, ctx: Optional[ErrorContext]) -> List[str]:
            return [
                "Check that input values are in the correct format",
                "Verify all required parameters are provided",
                "Review the command documentation for correct usage"
            ]
        
        # Register providers
        try:
            self.register_recovery_suggestion_provider(FileNotFoundError, file_not_found_suggestions)
            self.register_recovery_suggestion_provider(PermissionError, permission_error_suggestions)
            self.register_recovery_suggestion_provider(ConnectionError, connection_error_suggestions)
            self.register_recovery_suggestion_provider(ValueError, value_error_suggestions)
        except Exception as e:
            logger.warning(f"Error registering default recovery suggestions: {e}")

    @contextmanager
    def error_context(self, operation: str, component: str, **kwargs):
        """
        Context manager for error handling with automatic context tracking.
        
        Args:
            operation: Operation being performed
            component: Component executing the operation
            **kwargs: Additional context metadata
            
        Yields:
            ErrorContext instance
            
        Example:
            with error_handler.error_context("backup", "BackupService", repo="my-repo"):
                perform_backup()
        """
        context = ErrorContext(operation, component, **kwargs)
        with context:  # Use ErrorContext's context manager for stack tracking
            try:
                yield context
            except Exception as e:
                self.handle_error(e, context, reraise=True)

    def with_error_handling(self,
                            operation: str,
                            component: str,
                            reraise: bool = True,
                            **context_kwargs):
        """
        Decorator for automatic error handling with context preservation.
        
        Args:
            operation: Operation being performed
            component: Component executing the operation
            reraise: Whether to reraise exceptions after handling
            **context_kwargs: Additional context metadata
            
        Returns:
            Decorator function
            
        Example:
            @error_handler.with_error_handling("backup", "BackupService")
            def create_backup():
                ...
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = ErrorContext(operation, component, **context_kwargs)
                with context:  # Use ErrorContext's context manager for stack tracking
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        return self.handle_error(e, context, reraise=reraise)

            return wrapper

        return decorator

    def with_retry(self,
                   max_retries: int = 3,
                   delay: float = 1.0,
                   backoff_multiplier: float = 2.0,
                   exceptions: tuple = (Exception,)):
        """Decorator for retry logic with exponential backoff"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time

                last_exception = None
                current_delay = delay

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt < max_retries:
                            logger.warning(
                                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                                    f"Retrying in {current_delay:.1f}s..."
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff_multiplier
                        else:
                            logger.error(f"All {max_retries + 1} attempts failed")

                # Re-raise the last exception if all retries failed
                if last_exception:
                    raise last_exception

            return wrapper

        return decorator


# Global instance for easy access
error_handler = ErrorHandler()


# Convenience functions
def handle_error(exception: Exception,
                 context: Optional[ErrorContext] = None,
                 reraise: bool = True) -> Optional[Any]:
    """
    Convenience function for error handling.
    
    Args:
        exception: Exception to handle
        context: Optional error context
        reraise: Whether to reraise the exception
        
    Returns:
        Result from callback if any, None otherwise
    """
    return error_handler.handle_error(exception, context, reraise)


def with_error_handling(operation: str, component: str, reraise: bool = True, **kwargs):
    """
    Convenience decorator for error handling.
    
    Args:
        operation: Operation being performed
        component: Component executing the operation
        reraise: Whether to reraise exceptions
        **kwargs: Additional context metadata
        
    Returns:
        Decorator function
    """
    return error_handler.with_error_handling(operation, component, reraise, **kwargs)


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff_multiplier: float = 2.0):
    """
    Convenience decorator for retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        
    Returns:
        Decorator function
    """
    return error_handler.with_retry(max_retries, delay, backoff_multiplier)


def format_error_with_context(exception: Exception, context: Optional[ErrorContext] = None) -> str:
    """
    Format an error with context information for user-friendly display.
    
    Args:
        exception: Exception to format
        context: Optional error context
        
    Returns:
        Formatted error message
    """
    if context:
        return context.format_error(exception)
    else:
        return f"❌ {type(exception).__name__}: {str(exception)}"


def suggest_recovery(exception: Exception, context: Optional[ErrorContext] = None) -> List[str]:
    """
    Get recovery suggestions for an exception.
    
    Args:
        exception: Exception to get suggestions for
        context: Optional error context
        
    Returns:
        List of recovery suggestions
    """
    return error_handler.suggest_recovery(exception, context)
