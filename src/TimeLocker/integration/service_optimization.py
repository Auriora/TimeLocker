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
Service Communication Optimization for TimeLocker Integration Architecture

This module provides service communication optimization features including
connection pooling, asynchronous operations, performance monitoring, and
performance alerts for the TimeLocker service architecture.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic, Union
from collections import defaultdict, deque
from threading import Lock, RLock
from queue import Queue, Empty
import weakref

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import Event, ServiceContext
from ..interfaces.integration_exceptions import (
    ServiceOptimizationError,
    ServiceConnectionError,
    PerformanceThresholdError
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


@dataclass
class ServiceConnectionMetrics:
    """
    Metrics for service connection performance.
    
    Tracks connection usage, timing, and performance characteristics
    for optimization and monitoring purposes.
    """
    
    service_type: str
    connection_id: str
    created_at: datetime
    last_used_at: datetime
    use_count: int = 0
    total_operation_time: float = 0.0
    average_operation_time: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    is_active: bool = True
    
    def record_operation(self, operation_time: float, success: bool = True, error: Optional[str] = None) -> None:
        """
        Record an operation performed with this connection.
        
        Args:
            operation_time: Time taken for the operation in seconds
            success: Whether the operation was successful
            error: Error message if operation failed
        """
        self.last_used_at = datetime.now()
        self.use_count += 1
        self.total_operation_time += operation_time
        self.average_operation_time = self.total_operation_time / self.use_count
        
        if not success:
            self.error_count += 1
            self.last_error = error
    
    def get_age_seconds(self) -> float:
        """Get the age of this connection in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_time_seconds(self) -> float:
        """Get the idle time since last use in seconds."""
        return (datetime.now() - self.last_used_at).total_seconds()


@dataclass
class PerformanceThreshold:
    """
    Performance threshold configuration for monitoring and alerts.
    """
    
    operation_type: str
    max_duration_ms: float
    max_error_rate: float = 0.05  # 5% error rate threshold
    min_throughput_ops_per_sec: Optional[float] = None
    alert_after_violations: int = 3
    current_violations: int = 0
    last_violation_at: Optional[datetime] = None
    
    def check_violation(self, duration_ms: float, error_occurred: bool = False, 
                       throughput_ops_per_sec: Optional[float] = None) -> bool:
        """
        Check if performance thresholds are violated.
        
        Args:
            duration_ms: Operation duration in milliseconds
            error_occurred: Whether an error occurred
            throughput_ops_per_sec: Current throughput if available
            
        Returns:
            True if threshold is violated
        """
        violated = False
        
        # Check duration threshold
        if duration_ms > self.max_duration_ms:
            violated = True
        
        # Check throughput threshold
        if (self.min_throughput_ops_per_sec is not None and 
            throughput_ops_per_sec is not None and 
            throughput_ops_per_sec < self.min_throughput_ops_per_sec):
            violated = True
        
        if violated or error_occurred:
            self.current_violations += 1
            self.last_violation_at = datetime.now()
            return True
        else:
            # Reset violation count on successful operation
            self.current_violations = max(0, self.current_violations - 1)
            return False
    
    def should_alert(self) -> bool:
        """Check if an alert should be triggered."""
        return self.current_violations >= self.alert_after_violations


class ServiceConnectionPool:
    """
    Connection pool for service instances to minimize initialization overhead.
    
    Manages a pool of service connections with automatic cleanup, health checking,
    and performance monitoring.
    
    Requirements addressed:
    - 7.1: Service connection pooling and reuse to minimize initialization overhead
    - 7.3: Performance monitoring for service interactions
    """
    
    def __init__(self, 
                 service_type: type,
                 min_connections: int = 1,
                 max_connections: int = 10,
                 max_idle_time_seconds: int = 300,
                 health_check_interval_seconds: int = 60):
        """
        Initialize service connection pool.
        
        Args:
            service_type: Type of service to pool
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            max_idle_time_seconds: Maximum idle time before connection cleanup
            health_check_interval_seconds: Interval for health checks
        """
        self.service_type = service_type
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time_seconds = max_idle_time_seconds
        self.health_check_interval_seconds = health_check_interval_seconds
        
        self._available_connections: Queue = Queue()
        self._active_connections: Dict[str, ServiceInterface] = {}
        self._connection_metrics: Dict[str, ServiceConnectionMetrics] = {}
        self._lock = RLock()
        self._shutdown = False
        
        # Health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name=f"HealthCheck-{service_type.__name__}"
        )
        self._health_check_thread.start()
        
        logger.info(f"Initialized connection pool for {service_type.__name__}")
    
    def get_connection(self, context: ServiceContext, timeout_seconds: float = 10.0) -> ServiceInterface:
        """
        Get a connection from the pool.
        
        Args:
            context: Service context for initialization
            timeout_seconds: Timeout for getting connection
            
        Returns:
            Service instance from the pool
            
        Raises:
            ServiceConnectionError: If unable to get connection
        """
        if self._shutdown:
            raise ServiceConnectionError(
                self.service_type.__name__,
                "Connection pool is shutdown"
            )
        
        start_time = time.time()
        
        try:
            # Try to get an available connection
            try:
                connection = self._available_connections.get(timeout=timeout_seconds)
                connection_id = id(connection)
                
                with self._lock:
                    self._active_connections[str(connection_id)] = connection
                
                logger.debug(f"Reused connection {connection_id} for {self.service_type.__name__}")
                return connection
                
            except Empty:
                # No available connections, create new one if under limit
                with self._lock:
                    total_connections = (len(self._active_connections) + 
                                       self._available_connections.qsize())
                    
                    if total_connections >= self.max_connections:
                        raise ServiceConnectionError(
                            self.service_type.__name__,
                            f"Maximum connections ({self.max_connections}) reached"
                        )
                    
                    # Create new connection
                    connection = self._create_connection(context)
                    connection_id = str(id(connection))
                    
                    self._active_connections[connection_id] = connection
                    
                    # Create metrics for new connection
                    self._connection_metrics[connection_id] = ServiceConnectionMetrics(
                        service_type=self.service_type.__name__,
                        connection_id=connection_id,
                        created_at=datetime.now(),
                        last_used_at=datetime.now()
                    )
                    
                    logger.debug(f"Created new connection {connection_id} for {self.service_type.__name__}")
                    return connection
        
        except Exception as e:
            elapsed_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to get connection for {self.service_type.__name__} after {elapsed_time:.1f}ms: {e}")
            raise ServiceConnectionError(self.service_type.__name__, str(e), e)
    
    def return_connection(self, connection: ServiceInterface, 
                         operation_time: float = 0.0, 
                         success: bool = True, 
                         error: Optional[str] = None) -> None:
        """
        Return a connection to the pool.
        
        Args:
            connection: Service connection to return
            operation_time: Time taken for the operation in seconds
            success: Whether the operation was successful
            error: Error message if operation failed
        """
        if self._shutdown:
            return
        
        connection_id = str(id(connection))
        
        try:
            with self._lock:
                # Remove from active connections
                if connection_id in self._active_connections:
                    del self._active_connections[connection_id]
                
                # Update metrics
                if connection_id in self._connection_metrics:
                    self._connection_metrics[connection_id].record_operation(
                        operation_time, success, error
                    )
                
                # Check connection health before returning to pool
                if success and connection.health_check():
                    self._available_connections.put(connection)
                    logger.debug(f"Returned healthy connection {connection_id} to pool")
                else:
                    # Connection is unhealthy, don't return to pool
                    logger.warning(f"Discarding unhealthy connection {connection_id}")
                    try:
                        connection.shutdown()
                    except Exception as e:
                        logger.error(f"Error shutting down unhealthy connection: {e}")
                    
                    # Remove metrics for discarded connection
                    self._connection_metrics.pop(connection_id, None)
        
        except Exception as e:
            logger.error(f"Error returning connection {connection_id}: {e}")
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            available_count = self._available_connections.qsize()
            active_count = len(self._active_connections)
            total_count = available_count + active_count
            
            # Calculate aggregate metrics
            total_operations = sum(m.use_count for m in self._connection_metrics.values())
            total_errors = sum(m.error_count for m in self._connection_metrics.values())
            avg_operation_time = 0.0
            
            if self._connection_metrics:
                avg_operation_time = sum(
                    m.average_operation_time for m in self._connection_metrics.values()
                ) / len(self._connection_metrics)
            
            return {
                'service_type': self.service_type.__name__,
                'available_connections': available_count,
                'active_connections': active_count,
                'total_connections': total_count,
                'max_connections': self.max_connections,
                'min_connections': self.min_connections,
                'total_operations': total_operations,
                'total_errors': total_errors,
                'error_rate': total_errors / total_operations if total_operations > 0 else 0.0,
                'average_operation_time_ms': avg_operation_time * 1000,
                'connection_metrics': {
                    cid: {
                        'use_count': m.use_count,
                        'average_operation_time_ms': m.average_operation_time * 1000,
                        'error_count': m.error_count,
                        'age_seconds': m.get_age_seconds(),
                        'idle_time_seconds': m.get_idle_time_seconds()
                    }
                    for cid, m in self._connection_metrics.items()
                }
            }
    
    def cleanup_idle_connections(self) -> int:
        """
        Clean up idle connections that exceed the maximum idle time.
        
        Returns:
            Number of connections cleaned up
        """
        cleaned_count = 0
        current_time = datetime.now()
        
        try:
            with self._lock:
                # Get all available connections and check their idle time
                temp_connections = []
                
                while not self._available_connections.empty():
                    try:
                        connection = self._available_connections.get_nowait()
                        connection_id = str(id(connection))
                        
                        metrics = self._connection_metrics.get(connection_id)
                        if metrics:
                            idle_time = metrics.get_idle_time_seconds()
                            
                            if idle_time > self.max_idle_time_seconds:
                                # Connection is too idle, shut it down
                                try:
                                    connection.shutdown()
                                    cleaned_count += 1
                                    logger.debug(f"Cleaned up idle connection {connection_id}")
                                except Exception as e:
                                    logger.error(f"Error shutting down idle connection: {e}")
                                
                                # Remove metrics
                                del self._connection_metrics[connection_id]
                            else:
                                # Connection is still fresh, keep it
                                temp_connections.append(connection)
                        else:
                            # No metrics, keep connection but create metrics
                            temp_connections.append(connection)
                            self._connection_metrics[connection_id] = ServiceConnectionMetrics(
                                service_type=self.service_type.__name__,
                                connection_id=connection_id,
                                created_at=current_time,
                                last_used_at=current_time
                            )
                    
                    except Empty:
                        break
                
                # Put back the connections we're keeping
                for connection in temp_connections:
                    self._available_connections.put(connection)
        
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
        
        return cleaned_count
    
    def shutdown(self) -> None:
        """Shutdown the connection pool and clean up all connections."""
        with self._lock:
            if self._shutdown:
                return
            
            self._shutdown = True
            
            # Shutdown all available connections
            while not self._available_connections.empty():
                try:
                    connection = self._available_connections.get_nowait()
                    connection.shutdown()
                except (Empty, Exception) as e:
                    if not isinstance(e, Empty):
                        logger.error(f"Error shutting down available connection: {e}")
            
            # Shutdown all active connections
            for connection in self._active_connections.values():
                try:
                    connection.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down active connection: {e}")
            
            self._active_connections.clear()
            self._connection_metrics.clear()
            
            logger.info(f"Connection pool for {self.service_type.__name__} shutdown complete")
    
    def _create_connection(self, context: ServiceContext) -> ServiceInterface:
        """Create a new service connection."""
        try:
            # Create new instance
            connection = self.service_type()
            
            # Initialize with context
            if not connection.initialize(context):
                raise ServiceConnectionError(
                    self.service_type.__name__,
                    "Service initialization failed"
                )
            
            return connection
        
        except Exception as e:
            raise ServiceConnectionError(
                self.service_type.__name__,
                f"Failed to create connection: {e}",
                e
            )
    
    def _health_check_worker(self) -> None:
        """Background worker for periodic health checks."""
        while not self._shutdown:
            try:
                time.sleep(self.health_check_interval_seconds)
                
                if self._shutdown:
                    break
                
                # Perform cleanup of idle connections
                cleaned_count = self.cleanup_idle_connections()
                if cleaned_count > 0:
                    logger.debug(f"Cleaned up {cleaned_count} idle connections for {self.service_type.__name__}")
                
                # Ensure minimum connections are available
                with self._lock:
                    available_count = self._available_connections.qsize()
                    if available_count < self.min_connections:
                        # This is a simple approach - in production you might want
                        # to create connections proactively with a proper context
                        logger.debug(f"Available connections ({available_count}) below minimum ({self.min_connections})")
            
            except Exception as e:
                logger.error(f"Error in health check worker for {self.service_type.__name__}: {e}")


class AsyncServiceOperationManager:
    """
    Manager for asynchronous service operations to maintain CLI responsiveness.
    
    Provides support for long-running operations without blocking the main thread,
    with progress tracking and cancellation support.
    
    Requirements addressed:
    - 7.2: Asynchronous operation support for long-running tasks
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize async operation manager.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AsyncService")
        self._active_operations: Dict[str, Future] = {}
        self._operation_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = Lock()
        self._shutdown = False
        
        logger.info(f"Initialized async operation manager with {max_workers} workers")
    
    def submit_async_operation(self, 
                              operation_id: str,
                              operation_func: Callable,
                              *args,
                              progress_callback: Optional[Callable[[str, float], None]] = None,
                              completion_callback: Optional[Callable[[str, Any], None]] = None,
                              error_callback: Optional[Callable[[str, Exception], None]] = None,
                              **kwargs) -> str:
        """
        Submit an asynchronous operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_func: Function to execute asynchronously
            *args: Arguments for the operation function
            progress_callback: Optional callback for progress updates
            completion_callback: Optional callback for completion
            error_callback: Optional callback for errors
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Operation ID for tracking
            
        Raises:
            ServiceOptimizationError: If operation cannot be submitted
        """
        if self._shutdown:
            raise ServiceOptimizationError("AsyncServiceOperationManager is shutdown")
        
        with self._lock:
            if operation_id in self._active_operations:
                raise ServiceOptimizationError(f"Operation {operation_id} is already active")
            
            # Wrap the operation function to handle callbacks
            def wrapped_operation():
                try:
                    # Execute the operation
                    result = operation_func(*args, **kwargs)
                    
                    # Call completion callback if provided
                    if completion_callback:
                        try:
                            completion_callback(operation_id, result)
                        except Exception as e:
                            logger.error(f"Error in completion callback for {operation_id}: {e}")
                    
                    return result
                
                except Exception as e:
                    # Call error callback if provided
                    if error_callback:
                        try:
                            error_callback(operation_id, e)
                        except Exception as callback_error:
                            logger.error(f"Error in error callback for {operation_id}: {callback_error}")
                    
                    raise e
                
                finally:
                    # Clean up operation tracking
                    with self._lock:
                        self._active_operations.pop(operation_id, None)
                        self._operation_callbacks.pop(operation_id, None)
            
            # Submit to executor
            future = self._executor.submit(wrapped_operation)
            self._active_operations[operation_id] = future
            
            # Store callbacks
            if progress_callback:
                self._operation_callbacks[operation_id].append(('progress', progress_callback))
            if completion_callback:
                self._operation_callbacks[operation_id].append(('completion', completion_callback))
            if error_callback:
                self._operation_callbacks[operation_id].append(('error', error_callback))
            
            logger.debug(f"Submitted async operation {operation_id}")
            return operation_id
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Get the status of an async operation.
        
        Args:
            operation_id: ID of the operation to check
            
        Returns:
            Dictionary with operation status information
        """
        with self._lock:
            if operation_id not in self._active_operations:
                return {'status': 'not_found'}
            
            future = self._active_operations[operation_id]
            
            if future.done():
                try:
                    result = future.result()
                    return {
                        'status': 'completed',
                        'result': result
                    }
                except Exception as e:
                    return {
                        'status': 'failed',
                        'error': str(e)
                    }
            else:
                return {
                    'status': 'running',
                    'callbacks_count': len(self._operation_callbacks.get(operation_id, []))
                }
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel an async operation.
        
        Args:
            operation_id: ID of the operation to cancel
            
        Returns:
            True if operation was cancelled, False otherwise
        """
        with self._lock:
            if operation_id not in self._active_operations:
                return False
            
            future = self._active_operations[operation_id]
            cancelled = future.cancel()
            
            if cancelled:
                self._active_operations.pop(operation_id, None)
                self._operation_callbacks.pop(operation_id, None)
                logger.debug(f"Cancelled async operation {operation_id}")
            
            return cancelled
    
    def get_active_operations(self) -> List[str]:
        """
        Get list of active operation IDs.
        
        Returns:
            List of active operation IDs
        """
        with self._lock:
            return list(self._active_operations.keys())
    
    def wait_for_operation(self, operation_id: str, timeout: Optional[float] = None) -> Any:
        """
        Wait for an operation to complete and return its result.
        
        Args:
            operation_id: ID of the operation to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Operation result
            
        Raises:
            ServiceOptimizationError: If operation not found or times out
        """
        with self._lock:
            if operation_id not in self._active_operations:
                raise ServiceOptimizationError(f"Operation {operation_id} not found")
            
            future = self._active_operations[operation_id]
        
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            raise ServiceOptimizationError(f"Operation {operation_id} failed: {e}", e)
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the async operation manager.
        
        Args:
            wait: Whether to wait for active operations to complete
        """
        with self._lock:
            if self._shutdown:
                return
            
            self._shutdown = True
            
            # Cancel all active operations if not waiting
            if not wait:
                for operation_id in list(self._active_operations.keys()):
                    self.cancel_operation(operation_id)
            
            self._executor.shutdown(wait=wait)
            
            self._active_operations.clear()
            self._operation_callbacks.clear()
            
            logger.info("AsyncServiceOperationManager shutdown complete")


class ServicePerformanceMonitor:
    """
    Performance monitoring system for service interactions with bottleneck identification.
    
    Tracks operation timing, throughput, error rates, and identifies performance
    bottlenecks across the service architecture.
    
    Requirements addressed:
    - 7.3: Performance monitoring for service interactions with bottleneck identification
    - 7.4: Performance alerts and optimization recommendations
    """
    
    def __init__(self, 
                 alert_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
                 history_size: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            alert_callback: Optional callback for performance alerts
            history_size: Number of recent operations to keep in history
        """
        self.alert_callback = alert_callback
        self.history_size = history_size
        
        self._operation_history: deque = deque(maxlen=history_size)
        self._performance_thresholds: Dict[str, PerformanceThreshold] = {}
        self._service_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_operations': 0,
            'total_time': 0.0,
            'error_count': 0,
            'last_operation_at': None,
            'bottleneck_score': 0.0
        })
        self._lock = RLock()
        
        # Default thresholds
        self._setup_default_thresholds()
        
        logger.info("ServicePerformanceMonitor initialized")
    
    def record_operation(self, 
                        service_name: str,
                        operation_type: str,
                        duration_seconds: float,
                        success: bool = True,
                        error_message: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a service operation for performance monitoring.
        
        Args:
            service_name: Name of the service
            operation_type: Type of operation performed
            duration_seconds: Duration of the operation in seconds
            success: Whether the operation was successful
            error_message: Error message if operation failed
            metadata: Additional metadata about the operation
        """
        timestamp = datetime.now()
        duration_ms = duration_seconds * 1000
        
        # Create operation record
        operation_record = {
            'timestamp': timestamp,
            'service_name': service_name,
            'operation_type': operation_type,
            'duration_ms': duration_ms,
            'success': success,
            'error_message': error_message,
            'metadata': metadata or {}
        }
        
        with self._lock:
            # Add to history
            self._operation_history.append(operation_record)
            
            # Update service metrics
            service_metrics = self._service_metrics[service_name]
            service_metrics['total_operations'] += 1
            service_metrics['total_time'] += duration_seconds
            service_metrics['last_operation_at'] = timestamp
            
            if not success:
                service_metrics['error_count'] += 1
            
            # Calculate average operation time
            service_metrics['average_time_ms'] = (
                service_metrics['total_time'] / service_metrics['total_operations'] * 1000
            )
            
            # Calculate error rate
            service_metrics['error_rate'] = (
                service_metrics['error_count'] / service_metrics['total_operations']
            )
            
            # Check performance thresholds
            threshold_key = f"{service_name}.{operation_type}"
            if threshold_key in self._performance_thresholds:
                threshold = self._performance_thresholds[threshold_key]
                
                # Calculate current throughput
                recent_ops = self._get_recent_operations(service_name, operation_type, minutes=1)
                throughput = len(recent_ops) / 60.0 if recent_ops else 0.0
                
                # Check for threshold violations
                if threshold.check_violation(duration_ms, not success, throughput):
                    if threshold.should_alert():
                        self._trigger_performance_alert(service_name, operation_type, threshold, operation_record)
            
            # Update bottleneck scores
            self._update_bottleneck_scores()
    
    def set_performance_threshold(self, 
                                 service_name: str,
                                 operation_type: str,
                                 max_duration_ms: float,
                                 max_error_rate: float = 0.05,
                                 min_throughput_ops_per_sec: Optional[float] = None,
                                 alert_after_violations: int = 3) -> None:
        """
        Set performance threshold for a service operation.
        
        Args:
            service_name: Name of the service
            operation_type: Type of operation
            max_duration_ms: Maximum allowed duration in milliseconds
            max_error_rate: Maximum allowed error rate (0.0-1.0)
            min_throughput_ops_per_sec: Minimum required throughput
            alert_after_violations: Number of violations before alerting
        """
        threshold_key = f"{service_name}.{operation_type}"
        
        with self._lock:
            self._performance_thresholds[threshold_key] = PerformanceThreshold(
                operation_type=threshold_key,
                max_duration_ms=max_duration_ms,
                max_error_rate=max_error_rate,
                min_throughput_ops_per_sec=min_throughput_ops_per_sec,
                alert_after_violations=alert_after_violations
            )
        
        logger.info(f"Set performance threshold for {threshold_key}: {max_duration_ms}ms")
    
    def get_performance_summary(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance summary for services.
        
        Args:
            service_name: Optional service name to filter by
            
        Returns:
            Dictionary with performance summary
        """
        with self._lock:
            if service_name:
                services_to_include = [service_name] if service_name in self._service_metrics else []
            else:
                services_to_include = list(self._service_metrics.keys())
            
            summary = {
                'total_operations': len(self._operation_history),
                'services': {},
                'bottlenecks': self._identify_bottlenecks(),
                'recommendations': self._generate_recommendations()
            }
            
            for svc_name in services_to_include:
                metrics = self._service_metrics[svc_name]
                recent_ops = self._get_recent_operations(svc_name, minutes=5)
                
                summary['services'][svc_name] = {
                    'total_operations': metrics['total_operations'],
                    'average_time_ms': metrics.get('average_time_ms', 0.0),
                    'error_rate': metrics.get('error_rate', 0.0),
                    'recent_operations_5min': len(recent_ops),
                    'bottleneck_score': metrics.get('bottleneck_score', 0.0),
                    'last_operation_at': metrics['last_operation_at'].isoformat() if metrics['last_operation_at'] else None
                }
            
            return summary
    
    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """
        Get detailed bottleneck analysis.
        
        Returns:
            Dictionary with bottleneck analysis and recommendations
        """
        with self._lock:
            bottlenecks = self._identify_bottlenecks()
            recommendations = self._generate_recommendations()
            
            # Analyze operation patterns
            operation_patterns = self._analyze_operation_patterns()
            
            return {
                'bottlenecks': bottlenecks,
                'recommendations': recommendations,
                'operation_patterns': operation_patterns,
                'threshold_violations': self._get_threshold_violations()
            }
    
    def _setup_default_thresholds(self) -> None:
        """Setup default performance thresholds for common operations."""
        default_thresholds = [
            ('*.initialize', 100.0),  # Service initialization should be under 100ms
            ('*.health_check', 10.0),  # Health checks should be very fast
            ('*.backup', 5000.0),  # Backup operations can take up to 5 seconds
            ('*.restore', 10000.0),  # Restore operations can take up to 10 seconds
            ('*.configuration', 50.0),  # Configuration operations should be fast
        ]
        
        for operation_pattern, max_duration_ms in default_thresholds:
            service_name, operation_type = operation_pattern.split('.', 1)
            threshold_key = operation_pattern
            
            self._performance_thresholds[threshold_key] = PerformanceThreshold(
                operation_type=threshold_key,
                max_duration_ms=max_duration_ms,
                max_error_rate=0.05,
                alert_after_violations=3
            )
    
    def _get_recent_operations(self, 
                              service_name: Optional[str] = None,
                              operation_type: Optional[str] = None,
                              minutes: int = 5) -> List[Dict[str, Any]]:
        """Get recent operations matching criteria."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        matching_ops = []
        for op in self._operation_history:
            if op['timestamp'] >= cutoff_time:
                if service_name and op['service_name'] != service_name:
                    continue
                if operation_type and op['operation_type'] != operation_type:
                    continue
                matching_ops.append(op)
        
        return matching_ops
    
    def _update_bottleneck_scores(self) -> None:
        """Update bottleneck scores for all services."""
        for service_name, metrics in self._service_metrics.items():
            # Calculate bottleneck score based on multiple factors
            avg_time = metrics.get('average_time_ms', 0.0)
            error_rate = metrics.get('error_rate', 0.0)
            total_ops = metrics.get('total_operations', 0)
            
            # Normalize factors (higher score = more bottleneck)
            time_score = min(avg_time / 1000.0, 10.0)  # Cap at 10 for very slow operations
            error_score = error_rate * 10.0  # Scale error rate
            volume_score = min(total_ops / 100.0, 5.0)  # Higher volume can indicate bottleneck
            
            # Weighted combination
            bottleneck_score = (time_score * 0.5) + (error_score * 0.3) + (volume_score * 0.2)
            metrics['bottleneck_score'] = bottleneck_score
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        # Sort services by bottleneck score
        sorted_services = sorted(
            self._service_metrics.items(),
            key=lambda x: x[1].get('bottleneck_score', 0.0),
            reverse=True
        )
        
        # Top 3 bottlenecks or services with score > 2.0
        for service_name, metrics in sorted_services[:3]:
            score = metrics.get('bottleneck_score', 0.0)
            if score > 2.0:
                bottlenecks.append({
                    'service_name': service_name,
                    'bottleneck_score': score,
                    'average_time_ms': metrics.get('average_time_ms', 0.0),
                    'error_rate': metrics.get('error_rate', 0.0),
                    'total_operations': metrics.get('total_operations', 0)
                })
        
        return bottlenecks
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        bottlenecks = self._identify_bottlenecks()
        
        for bottleneck in bottlenecks:
            service_name = bottleneck['service_name']
            avg_time = bottleneck['average_time_ms']
            error_rate = bottleneck['error_rate']
            
            if avg_time > 1000:
                recommendations.append(
                    f"Consider optimizing {service_name} - average operation time is {avg_time:.1f}ms"
                )
            
            if error_rate > 0.1:
                recommendations.append(
                    f"Investigate errors in {service_name} - error rate is {error_rate:.1%}"
                )
            
            # Check if connection pooling might help
            recent_ops = self._get_recent_operations(service_name, minutes=1)
            if len(recent_ops) > 10:
                recommendations.append(
                    f"Consider connection pooling for {service_name} - high operation frequency"
                )
        
        return recommendations
    
    def _analyze_operation_patterns(self) -> Dict[str, Any]:
        """Analyze operation patterns for insights."""
        patterns = {
            'peak_hours': {},
            'operation_distribution': {},
            'error_patterns': {}
        }
        
        # Analyze by hour of day
        hour_counts = defaultdict(int)
        operation_counts = defaultdict(int)
        error_by_hour = defaultdict(int)
        
        for op in self._operation_history:
            hour = op['timestamp'].hour
            hour_counts[hour] += 1
            operation_counts[op['operation_type']] += 1
            
            if not op['success']:
                error_by_hour[hour] += 1
        
        patterns['peak_hours'] = dict(hour_counts)
        patterns['operation_distribution'] = dict(operation_counts)
        patterns['error_patterns'] = dict(error_by_hour)
        
        return patterns
    
    def _get_threshold_violations(self) -> List[Dict[str, Any]]:
        """Get current threshold violations."""
        violations = []
        
        for threshold_key, threshold in self._performance_thresholds.items():
            if threshold.current_violations > 0:
                violations.append({
                    'threshold_key': threshold_key,
                    'current_violations': threshold.current_violations,
                    'max_duration_ms': threshold.max_duration_ms,
                    'last_violation_at': threshold.last_violation_at.isoformat() if threshold.last_violation_at else None,
                    'should_alert': threshold.should_alert()
                })
        
        return violations
    
    def _trigger_performance_alert(self, 
                                  service_name: str,
                                  operation_type: str,
                                  threshold: PerformanceThreshold,
                                  operation_record: Dict[str, Any]) -> None:
        """Trigger a performance alert."""
        alert_data = {
            'alert_type': 'performance_threshold_violation',
            'service_name': service_name,
            'operation_type': operation_type,
            'threshold_violations': threshold.current_violations,
            'max_duration_ms': threshold.max_duration_ms,
            'actual_duration_ms': operation_record['duration_ms'],
            'timestamp': operation_record['timestamp'].isoformat(),
            'recommendations': self._generate_recommendations()
        }
        
        logger.warning(f"Performance alert for {service_name}.{operation_type}: {alert_data}")
        
        if self.alert_callback:
            try:
                self.alert_callback(f"{service_name}.{operation_type}", alert_data)
            except Exception as e:
                logger.error(f"Error in performance alert callback: {e}")


class ServiceOptimizationManager:
    """
    Central manager for service communication optimization features.
    
    Coordinates connection pooling, async operations, performance monitoring,
    and optimization recommendations across the service architecture.
    
    Requirements addressed:
    - 7.1: Service connection pooling and reuse
    - 7.2: Asynchronous operation support
    - 7.3: Performance monitoring with bottleneck identification
    - 7.4: Performance alerts and optimization recommendations
    - 7.5: Integration with existing service architecture
    """
    
    def __init__(self, 
                 event_bus: Optional['EventBus'] = None,
                 max_async_workers: int = 4):
        """
        Initialize service optimization manager.
        
        Args:
            event_bus: Optional event bus for publishing optimization events
            max_async_workers: Maximum number of async worker threads
        """
        self.event_bus = event_bus
        
        # Initialize optimization components
        self._connection_pools: Dict[type, ServiceConnectionPool] = {}
        self._async_manager = AsyncServiceOperationManager(max_workers=max_async_workers)
        self._performance_monitor = ServicePerformanceMonitor(
            alert_callback=self._handle_performance_alert
        )
        
        self._lock = RLock()
        self._shutdown = False
        
        logger.info("ServiceOptimizationManager initialized")
    
    def create_connection_pool(self, 
                              service_type: type,
                              min_connections: int = 1,
                              max_connections: int = 10,
                              max_idle_time_seconds: int = 300) -> ServiceConnectionPool:
        """
        Create a connection pool for a service type.
        
        Args:
            service_type: Type of service to pool
            min_connections: Minimum number of connections
            max_connections: Maximum number of connections
            max_idle_time_seconds: Maximum idle time before cleanup
            
        Returns:
            ServiceConnectionPool instance
        """
        with self._lock:
            if service_type in self._connection_pools:
                return self._connection_pools[service_type]
            
            pool = ServiceConnectionPool(
                service_type=service_type,
                min_connections=min_connections,
                max_connections=max_connections,
                max_idle_time_seconds=max_idle_time_seconds
            )
            
            self._connection_pools[service_type] = pool
            
            logger.info(f"Created connection pool for {service_type.__name__}")
            return pool
    
    def get_optimized_service(self, 
                             service_type: type,
                             context: ServiceContext,
                             use_pooling: bool = True) -> ServiceInterface:
        """
        Get an optimized service instance with connection pooling.
        
        Args:
            service_type: Type of service to get
            context: Service context for initialization
            use_pooling: Whether to use connection pooling
            
        Returns:
            Service instance (pooled or new)
        """
        if use_pooling:
            # Get or create connection pool
            if service_type not in self._connection_pools:
                self.create_connection_pool(service_type)
            
            pool = self._connection_pools[service_type]
            return pool.get_connection(context)
        else:
            # Create new instance without pooling
            service = service_type()
            service.initialize(context)
            return service
    
    def return_service(self, 
                      service: ServiceInterface,
                      operation_time: float = 0.0,
                      success: bool = True,
                      error: Optional[str] = None) -> None:
        """
        Return a service instance to its pool (if pooled).
        
        Args:
            service: Service instance to return
            operation_time: Time taken for the operation
            success: Whether the operation was successful
            error: Error message if operation failed
        """
        service_type = type(service)
        
        # Record performance metrics
        self._performance_monitor.record_operation(
            service_name=service_type.__name__,
            operation_type='service_operation',
            duration_seconds=operation_time,
            success=success,
            error_message=error
        )
        
        # Return to pool if pooled
        if service_type in self._connection_pools:
            pool = self._connection_pools[service_type]
            pool.return_connection(service, operation_time, success, error)
        else:
            # Not pooled, just shutdown
            try:
                service.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down non-pooled service: {e}")
    
    def submit_async_operation(self, 
                              operation_id: str,
                              operation_func: Callable,
                              *args,
                              **kwargs) -> str:
        """
        Submit an asynchronous operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_func: Function to execute asynchronously
            *args: Arguments for the operation function
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Operation ID for tracking
        """
        return self._async_manager.submit_async_operation(
            operation_id,
            operation_func,
            *args,
            **kwargs
        )
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive optimization statistics.
        
        Returns:
            Dictionary with optimization statistics
        """
        with self._lock:
            stats = {
                'connection_pools': {},
                'async_operations': {
                    'active_operations': self._async_manager.get_active_operations(),
                    'max_workers': self._async_manager.max_workers
                },
                'performance_summary': self._performance_monitor.get_performance_summary(),
                'bottleneck_analysis': self._performance_monitor.get_bottleneck_analysis()
            }
            
            # Get connection pool statistics
            for service_type, pool in self._connection_pools.items():
                stats['connection_pools'][service_type.__name__] = pool.get_pool_statistics()
            
            return stats
    
    def set_performance_threshold(self, 
                                 service_name: str,
                                 operation_type: str,
                                 max_duration_ms: float,
                                 **kwargs) -> None:
        """
        Set performance threshold for monitoring.
        
        Args:
            service_name: Name of the service
            operation_type: Type of operation
            max_duration_ms: Maximum allowed duration in milliseconds
            **kwargs: Additional threshold parameters
        """
        self._performance_monitor.set_performance_threshold(
            service_name=service_name,
            operation_type=operation_type,
            max_duration_ms=max_duration_ms,
            **kwargs
        )
    
    def shutdown(self) -> None:
        """Shutdown the optimization manager and clean up resources."""
        with self._lock:
            if self._shutdown:
                return
            
            self._shutdown = True
            
            # Shutdown connection pools
            for pool in self._connection_pools.values():
                try:
                    pool.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down connection pool: {e}")
            
            # Shutdown async manager
            try:
                self._async_manager.shutdown(wait=True)
            except Exception as e:
                logger.error(f"Error shutting down async manager: {e}")
            
            self._connection_pools.clear()
            
            logger.info("ServiceOptimizationManager shutdown complete")
    
    def _handle_performance_alert(self, threshold_key: str, alert_data: Dict[str, Any]) -> None:
        """Handle performance alerts by publishing events."""
        if self.event_bus:
            try:
                alert_event = Event(
                    event_type='service.performance.alert',
                    source='ServiceOptimizationManager',
                    timestamp=datetime.now(),
                    data=alert_data,
                    priority=7  # High priority for performance alerts
                )
                
                self.event_bus.publish_event(alert_event)
                logger.info(f"Published performance alert event for {threshold_key}")
                
            except Exception as e:
                logger.error(f"Error publishing performance alert event: {e}")