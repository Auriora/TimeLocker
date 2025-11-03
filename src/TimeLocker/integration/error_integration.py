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

"""
Error Integration Module for TimeLocker Integration Architecture

This module provides integration between the error propagation system and
the service architecture, including decorators and utilities for seamless
error handling across service boundaries.
"""

import logging
import functools
from typing import Any, Callable, Optional, Type, TypeVar, Union
from contextlib import contextmanager

from .error_propagation import (
    ErrorPropagationSystem,
    ErrorSeverity,
    ErrorCategory,
    PropagatedError,
    ErrorContext
)
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_exceptions import ServiceIntegrationError

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class ServiceErrorHandler:
    """
    Service-specific error handler that integrates with the error propagation system.
    
    This class provides service-specific error handling capabilities while
    maintaining integration with the global error propagation system.
    """
    
    def __init__(self, 
                 service_name: str, 
                 error_propagation_system: ErrorPropagationSystem):
        """
        Initialize service error handler.
        
        Args:
            service_name: Name of the service this handler is for
            error_propagation_system: Global error propagation system
        """
        self.service_name = service_name
        self.error_system = error_propagation_system
        self._operation_context = {}
    
    def set_operation_context(self, **context) -> None:
        """
        Set operation context for error handling.
        
        Args:
            **context: Context information for operations
        """
        self._operation_context.update(context)
    
    def clear_operation_context(self) -> None:
        """Clear operation context"""
        self._operation_context.clear()
    
    def handle_service_error(self, 
                           exception: Exception, 
                           operation: str,
                           component: str = "",
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           category: ErrorCategory = ErrorCategory.SYSTEM,
                           correlation_id: Optional[str] = None,
                           **kwargs) -> PropagatedError:
        """
        Handle a service error with full context propagation.
        
        Args:
            exception: Exception to handle
            operation: Operation being performed
            component: Component where error occurred
            severity: Error severity level
            category: Error category
            correlation_id: Optional correlation ID
            **kwargs: Additional context information
            
        Returns:
            PropagatedError with full context
        """
        # Merge operation context with provided context
        context = {**self._operation_context, **kwargs}
        
        return self.error_system.propagate_error(
            exception=exception,
            operation=operation,
            component=component or self.service_name,
            service_name=self.service_name,
            severity=severity,
            category=category,
            correlation_id=correlation_id,
            technical_details=context
        )
    
    def with_error_handling(self, 
                          operation: str,
                          component: str = "",
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          category: ErrorCategory = ErrorCategory.SYSTEM,
                          reraise: bool = True,
                          attempt_recovery: bool = True) -> Callable[[F], F]:
        """
        Decorator for automatic service error handling.
        
        Args:
            operation: Operation name for context
            component: Component name for context
            severity: Error severity level
            category: Error category
            reraise: Whether to reraise the exception after handling
            attempt_recovery: Whether to attempt error recovery
            
        Returns:
            Decorated function with error handling
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Handle the error
                    propagated_error = self.handle_service_error(
                        exception=e,
                        operation=operation,
                        component=component,
                        severity=severity,
                        category=category
                    )
                    
                    # Attempt recovery if requested
                    if attempt_recovery:
                        recovery_result = self.error_system.attempt_error_recovery(propagated_error)
                        if recovery_result is not None:
                            logger.info(f"Recovered from error in {operation}")
                            return recovery_result
                    
                    # Reraise if requested
                    if reraise:
                        raise propagated_error.original_exception
                    
                    return None
            
            return wrapper
        return decorator
    
    def with_retry(self, 
                  operation: str,
                  max_retries: int = 3,
                  component: str = "",
                  severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                  category: ErrorCategory = ErrorCategory.SYSTEM) -> Callable[[F], F]:
        """
        Decorator for automatic retry with error propagation.
        
        Args:
            operation: Operation name for context
            max_retries: Maximum number of retry attempts
            component: Component name for context
            severity: Error severity level
            category: Error category
            
        Returns:
            Decorated function with retry logic
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_error = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        # Handle the error
                        propagated_error = self.handle_service_error(
                            exception=e,
                            operation=operation,
                            component=component,
                            severity=severity,
                            category=category,
                            technical_details={'attempt': attempt + 1, 'max_retries': max_retries}
                        )
                        
                        last_error = propagated_error
                        
                        # Check if we should retry
                        if attempt < max_retries and self.error_system.should_retry_error(propagated_error):
                            # Increment retry count
                            self.error_system.increment_retry_count(propagated_error)
                            
                            # Get retry delay
                            delay = self.error_system.get_retry_delay(propagated_error)
                            
                            logger.warning(f"Attempt {attempt + 1} failed for {operation}, retrying in {delay:.1f}s")
                            
                            import time
                            time.sleep(delay)
                        else:
                            break
                
                # All retries failed, raise the last error
                if last_error:
                    raise last_error.original_exception
                
                return None
            
            return wrapper
        return decorator


def with_service_error_handling(service_name: str,
                               operation: str,
                               component: str = "",
                               severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                               category: ErrorCategory = ErrorCategory.SYSTEM,
                               error_system: Optional[ErrorPropagationSystem] = None) -> Callable[[F], F]:
    """
    Standalone decorator for service error handling.
    
    Args:
        service_name: Name of the service
        operation: Operation name for context
        component: Component name for context
        severity: Error severity level
        category: Error category
        error_system: Optional error propagation system (uses global if not provided)
        
    Returns:
        Decorated function with error handling
    """
    from .error_propagation import error_propagation_system
    
    if error_system is None:
        error_system = error_propagation_system
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Propagate error
                propagated_error = error_system.propagate_error(
                    exception=e,
                    operation=operation,
                    component=component or service_name,
                    service_name=service_name,
                    severity=severity,
                    category=category
                )
                
                # Attempt recovery
                recovery_result = error_system.attempt_error_recovery(propagated_error)
                if recovery_result is not None:
                    logger.info(f"Recovered from error in {service_name}:{operation}")
                    return recovery_result
                
                # Re-raise original exception
                raise e
        
        return wrapper
    return decorator


@contextmanager
def service_error_context(service_name: str,
                         operation: str,
                         component: str = "",
                         severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                         category: ErrorCategory = ErrorCategory.SYSTEM,
                         correlation_id: Optional[str] = None,
                         error_system: Optional[ErrorPropagationSystem] = None,
                         **context_kwargs):
    """
    Context manager for service error handling.
    
    Args:
        service_name: Name of the service
        operation: Operation name for context
        component: Component name for context
        severity: Error severity level
        category: Error category
        correlation_id: Optional correlation ID
        error_system: Optional error propagation system
        **context_kwargs: Additional context information
        
    Yields:
        ErrorContext for the operation
    """
    from .error_propagation import error_propagation_system
    
    if error_system is None:
        error_system = error_propagation_system
    
    error_context = ErrorContext(
        operation=operation,
        component=component or service_name,
        service_name=service_name,
        correlation_id=correlation_id,
        severity=severity,
        category=category,
        technical_details=context_kwargs
    )
    
    try:
        yield error_context
    except Exception as e:
        # Propagate error with context
        propagated_error = error_system.propagate_error(
            exception=e,
            operation=operation,
            component=component or service_name,
            service_name=service_name,
            severity=severity,
            category=category,
            correlation_id=correlation_id,
            technical_details=context_kwargs
        )
        
        # Attempt recovery
        recovery_result = error_system.attempt_error_recovery(propagated_error)
        if recovery_result is not None:
            logger.info(f"Recovered from error in {service_name}:{operation}")
            return
        
        # Re-raise original exception
        raise e


class ServiceInterfaceErrorMixin:
    """
    Mixin class for ServiceInterface implementations to add error handling capabilities.
    
    This mixin provides error handling methods that can be used by service implementations
    to integrate with the error propagation system.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the error handling mixin"""
        super().__init__(*args, **kwargs)
        self._error_handler: Optional[ServiceErrorHandler] = None
    
    def _initialize_error_handler(self, error_system: ErrorPropagationSystem) -> None:
        """
        Initialize the error handler for this service.
        
        Args:
            error_system: Error propagation system to use
        """
        service_name = self.get_service_name() if hasattr(self, 'get_service_name') else self.__class__.__name__
        self._error_handler = ServiceErrorHandler(service_name, error_system)
    
    def _handle_service_error(self, 
                            exception: Exception, 
                            operation: str,
                            **kwargs) -> PropagatedError:
        """
        Handle a service error using the error handler.
        
        Args:
            exception: Exception to handle
            operation: Operation being performed
            **kwargs: Additional context information
            
        Returns:
            PropagatedError with full context
        """
        if self._error_handler is None:
            raise RuntimeError("Error handler not initialized. Call _initialize_error_handler first.")
        
        return self._error_handler.handle_service_error(exception, operation, **kwargs)
    
    def _with_error_handling(self, operation: str, **kwargs) -> Callable[[F], F]:
        """
        Get error handling decorator for this service.
        
        Args:
            operation: Operation name for context
            **kwargs: Additional decorator arguments
            
        Returns:
            Error handling decorator
        """
        if self._error_handler is None:
            raise RuntimeError("Error handler not initialized. Call _initialize_error_handler first.")
        
        return self._error_handler.with_error_handling(operation, **kwargs)
    
    def _with_retry(self, operation: str, **kwargs) -> Callable[[F], F]:
        """
        Get retry decorator for this service.
        
        Args:
            operation: Operation name for context
            **kwargs: Additional decorator arguments
            
        Returns:
            Retry decorator
        """
        if self._error_handler is None:
            raise RuntimeError("Error handler not initialized. Call _initialize_error_handler first.")
        
        return self._error_handler.with_retry(operation, **kwargs)


def create_service_with_error_handling(service_class: Type[T], 
                                     error_system: ErrorPropagationSystem,
                                     *args, **kwargs) -> T:
    """
    Create a service instance with error handling capabilities.
    
    Args:
        service_class: Service class to instantiate
        error_system: Error propagation system to use
        *args: Arguments for service constructor
        **kwargs: Keyword arguments for service constructor
        
    Returns:
        Service instance with error handling
    """
    # Create service instance
    service = service_class(*args, **kwargs)
    
    # Initialize error handling if the service supports it
    if hasattr(service, '_initialize_error_handler'):
        service._initialize_error_handler(error_system)
    
    return service


# Convenience functions for common error scenarios
def handle_configuration_error(exception: Exception, 
                             service_name: str, 
                             operation: str = "configuration",
                             **kwargs) -> PropagatedError:
    """Handle configuration-related errors"""
    from .error_propagation import error_propagation_system
    
    return error_propagation_system.propagate_error(
        exception=exception,
        operation=operation,
        component=service_name,
        service_name=service_name,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.CONFIGURATION,
        **kwargs
    )


def handle_network_error(exception: Exception, 
                        service_name: str, 
                        operation: str = "network_operation",
                        **kwargs) -> PropagatedError:
    """Handle network-related errors"""
    from .error_propagation import error_propagation_system
    
    return error_propagation_system.propagate_error(
        exception=exception,
        operation=operation,
        component=service_name,
        service_name=service_name,
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.NETWORK,
        **kwargs
    )


def handle_authentication_error(exception: Exception, 
                              service_name: str, 
                              operation: str = "authentication",
                              **kwargs) -> PropagatedError:
    """Handle authentication-related errors"""
    from .error_propagation import error_propagation_system
    
    return error_propagation_system.propagate_error(
        exception=exception,
        operation=operation,
        component=service_name,
        service_name=service_name,
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.AUTHENTICATION,
        **kwargs
    )