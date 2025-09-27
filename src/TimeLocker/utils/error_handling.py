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
from typing import Optional, Dict, Any, Callable, Type, Union
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErrorContext:
    """Context information for error handling"""

    def __init__(self, operation: str, component: str, **kwargs):
        self.operation = operation
        self.component = component
        self.metadata = kwargs
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
                'operation': self.operation,
                'component': self.component,
                'metadata':  self.metadata,
                'timestamp': self.timestamp
        }


class ErrorHandler:
    """
    Centralized error handling utility following DRY principles.
    
    Provides consistent error handling patterns across the TimeLocker codebase,
    including logging, context preservation, and retry mechanisms.
    """

    def __init__(self):
        self._error_callbacks: Dict[Type[Exception], Callable] = {}
        self._default_callback: Optional[Callable] = None

    def register_error_callback(self, exception_type: Type[Exception], callback: Callable) -> None:
        """Register a callback for specific exception types"""
        self._error_callbacks[exception_type] = callback
        logger.debug(f"Registered error callback for {exception_type.__name__}")

    def set_default_callback(self, callback: Callable) -> None:
        """Set default callback for unhandled exception types"""
        self._default_callback = callback

    def handle_error(self,
                     exception: Exception,
                     context: Optional[ErrorContext] = None,
                     reraise: bool = True) -> Optional[Any]:
        """
        Handle an exception with appropriate logging and callbacks
        
        Args:
            exception: The exception to handle
            context: Optional context information
            reraise: Whether to reraise the exception after handling
            
        Returns:
            Result from callback if any, None otherwise
        """
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
        """Log error with context information"""
        error_msg = f"{type(exception).__name__}: {exception}"

        if context:
            error_msg = f"[{context.component}:{context.operation}] {error_msg}"
            logger.error(error_msg, extra=context.to_dict())
        else:
            logger.error(error_msg)

        # Log stack trace for debugging
        logger.debug("Stack trace:", exc_info=True)

    def _find_callback(self, exception_type: Type[Exception]) -> Optional[Callable]:
        """Find appropriate callback for exception type"""
        # Check for exact match first
        if exception_type in self._error_callbacks:
            return self._error_callbacks[exception_type]

        # Check for parent class matches
        for registered_type, callback in self._error_callbacks.items():
            if issubclass(exception_type, registered_type):
                return callback

        # Return default callback if available
        return self._default_callback

    @contextmanager
    def error_context(self, operation: str, component: str, **kwargs):
        """Context manager for error handling"""
        context = ErrorContext(operation, component, **kwargs)
        try:
            yield context
        except Exception as e:
            self.handle_error(e, context, reraise=True)

    def with_error_handling(self,
                            operation: str,
                            component: str,
                            reraise: bool = True,
                            **context_kwargs):
        """Decorator for automatic error handling"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = ErrorContext(operation, component, **context_kwargs)
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
    """Convenience function for error handling"""
    return error_handler.handle_error(exception, context, reraise)


def with_error_handling(operation: str, component: str, reraise: bool = True, **kwargs):
    """Convenience decorator for error handling"""
    return error_handler.with_error_handling(operation, component, reraise, **kwargs)


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff_multiplier: float = 2.0):
    """Convenience decorator for retry logic"""
    return error_handler.with_retry(max_retries, delay, backoff_multiplier)
