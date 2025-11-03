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
Optimized Service Context Manager for TimeLocker Integration Architecture

This module provides context managers and utilities for using optimized services
with automatic resource management, performance tracking, and error handling.
"""

import time
import logging
from contextlib import contextmanager
from typing import Type, TypeVar, Optional, Generator, Any, Dict
from dataclasses import dataclass

from ..interfaces.service_interface import ServiceInterface

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


@dataclass
class ServiceOperationContext:
    """
    Context information for service operations.
    
    Tracks operation timing, success status, and metadata for
    performance monitoring and optimization.
    """
    
    service_name: str
    operation_type: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def duration_seconds(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time
    
    def complete(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """Mark operation as complete."""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message


class OptimizedServiceContext:
    """
    Context manager for optimized service usage.
    
    Provides automatic resource management, performance tracking, and
    error handling for service operations with connection pooling support.
    
    Requirements addressed:
    - 7.1: Service connection pooling and reuse
    - 7.3: Performance monitoring for service interactions
    """
    
    def __init__(self, 
                 service_manager: 'ServiceManager',
                 service_type: Type[T],
                 operation_type: str = "service_operation",
                 use_pooling: bool = True,
                 timeout_seconds: float = 10.0,
                 track_performance: bool = True):
        """
        Initialize optimized service context.
        
        Args:
            service_manager: ServiceManager instance
            service_type: Type of service to use
            operation_type: Type of operation for performance tracking
            use_pooling: Whether to use connection pooling
            timeout_seconds: Timeout for getting service connection
            track_performance: Whether to track performance metrics
        """
        self.service_manager = service_manager
        self.service_type = service_type
        self.operation_type = operation_type
        self.use_pooling = use_pooling
        self.timeout_seconds = timeout_seconds
        self.track_performance = track_performance
        
        self.service: Optional[T] = None
        self.operation_context: Optional[ServiceOperationContext] = None
    
    def __enter__(self) -> T:
        """Enter the context and get optimized service instance."""
        try:
            # Start operation tracking
            if self.track_performance:
                self.operation_context = ServiceOperationContext(
                    service_name=self.service_type.__name__,
                    operation_type=self.operation_type,
                    start_time=time.time()
                )
            
            # Get optimized service instance
            self.service = self.service_manager.get_optimized_service(
                service_type=self.service_type,
                use_pooling=self.use_pooling,
                timeout_seconds=self.timeout_seconds
            )
            
            logger.debug(f"Acquired optimized service {self.service_type.__name__}")
            return self.service
        
        except Exception as e:
            # Mark operation as failed
            if self.operation_context:
                self.operation_context.complete(success=False, error_message=str(e))
            
            logger.error(f"Failed to acquire optimized service {self.service_type.__name__}: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context and return service to pool."""
        if self.service is None:
            return
        
        try:
            # Determine operation success
            success = exc_type is None
            error_message = str(exc_val) if exc_val else None
            
            # Complete operation tracking
            if self.operation_context:
                self.operation_context.complete(success=success, error_message=error_message)
                operation_time = self.operation_context.duration_seconds
            else:
                operation_time = 0.0
            
            # Return service to pool
            self.service_manager.return_optimized_service(
                service=self.service,
                operation_time=operation_time,
                success=success,
                error=error_message
            )
            
            logger.debug(f"Returned optimized service {self.service_type.__name__} "
                        f"(duration: {operation_time:.3f}s, success: {success})")
        
        except Exception as e:
            logger.error(f"Error returning optimized service {self.service_type.__name__}: {e}")
        
        finally:
            self.service = None
            self.operation_context = None


@contextmanager
def optimized_service(service_manager: 'ServiceManager',
                     service_type: Type[T],
                     operation_type: str = "service_operation",
                     use_pooling: bool = True,
                     timeout_seconds: float = 10.0,
                     track_performance: bool = True) -> Generator[T, None, None]:
    """
    Context manager for optimized service usage.
    
    This is a convenience function that provides a context manager for
    using optimized services with automatic resource management.
    
    Args:
        service_manager: ServiceManager instance
        service_type: Type of service to use
        operation_type: Type of operation for performance tracking
        use_pooling: Whether to use connection pooling
        timeout_seconds: Timeout for getting service connection
        track_performance: Whether to track performance metrics
        
    Yields:
        Optimized service instance
        
    Example:
        ```python
        with optimized_service(service_manager, RepositoryService, "backup") as repo_service:
            result = repo_service.perform_backup(backup_config)
        ```
        
    Requirements addressed:
    - 7.1: Service connection pooling and reuse
    - 7.3: Performance monitoring for service interactions
    """
    context = OptimizedServiceContext(
        service_manager=service_manager,
        service_type=service_type,
        operation_type=operation_type,
        use_pooling=use_pooling,
        timeout_seconds=timeout_seconds,
        track_performance=track_performance
    )
    
    with context as service:
        yield service


class AsyncServiceOperationContext:
    """
    Context for managing asynchronous service operations.
    
    Provides utilities for submitting, tracking, and managing
    long-running asynchronous service operations.
    
    Requirements addressed:
    - 7.2: Asynchronous operation support for long-running tasks
    """
    
    def __init__(self, 
                 service_manager: 'ServiceManager',
                 operation_id: str,
                 operation_name: str = "async_operation"):
        """
        Initialize async service operation context.
        
        Args:
            service_manager: ServiceManager instance
            operation_id: Unique identifier for the operation
            operation_name: Human-readable name for the operation
        """
        self.service_manager = service_manager
        self.operation_id = operation_id
        self.operation_name = operation_name
        self._submitted = False
    
    def submit(self, 
              operation_func,
              *args,
              progress_callback=None,
              completion_callback=None,
              error_callback=None,
              **kwargs) -> str:
        """
        Submit the asynchronous operation.
        
        Args:
            operation_func: Function to execute asynchronously
            *args: Arguments for the operation function
            progress_callback: Optional callback for progress updates
            completion_callback: Optional callback for completion
            error_callback: Optional callback for errors
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Operation ID for tracking
        """
        if self._submitted:
            raise ValueError(f"Operation {self.operation_id} has already been submitted")
        
        result = self.service_manager.submit_async_service_operation(
            self.operation_id,
            operation_func,
            *args,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback,
            **kwargs
        )
        
        self._submitted = True
        logger.info(f"Submitted async operation {self.operation_name} ({self.operation_id})")
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the operation."""
        if not self._submitted:
            return {'status': 'not_submitted'}
        
        return self.service_manager.get_async_operation_status(self.operation_id)
    
    def cancel(self) -> bool:
        """Cancel the operation if it's still running."""
        if not self._submitted:
            return False
        
        result = self.service_manager.cancel_async_operation(self.operation_id)
        if result:
            logger.info(f"Cancelled async operation {self.operation_name} ({self.operation_id})")
        
        return result
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> Any:
        """
        Wait for the operation to complete and return its result.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Operation result
        """
        if not self._submitted:
            raise ValueError(f"Operation {self.operation_id} has not been submitted")
        
        return self.service_manager._optimization_manager._async_manager.wait_for_operation(
            self.operation_id, timeout
        )


def create_async_operation(service_manager: 'ServiceManager',
                          operation_id: str,
                          operation_name: str = "async_operation") -> AsyncServiceOperationContext:
    """
    Create an asynchronous service operation context.
    
    This is a convenience function for creating async operation contexts
    with proper setup and error handling.
    
    Args:
        service_manager: ServiceManager instance
        operation_id: Unique identifier for the operation
        operation_name: Human-readable name for the operation
        
    Returns:
        AsyncServiceOperationContext for managing the operation
        
    Example:
        ```python
        async_op = create_async_operation(service_manager, "backup_001", "System Backup")
        async_op.submit(perform_backup, backup_config)
        
        # Check status
        status = async_op.get_status()
        
        # Wait for completion
        result = async_op.wait_for_completion(timeout=300)
        ```
        
    Requirements addressed:
    - 7.2: Asynchronous operation support for long-running tasks
    """
    return AsyncServiceOperationContext(
        service_manager=service_manager,
        operation_id=operation_id,
        operation_name=operation_name
    )