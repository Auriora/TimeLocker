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
import time
import socket
from typing import Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .recovery_errors import (
    NetworkInterruptionError,
    NetworkTimeoutError,
    RepositoryConnectionError
)

logger = logging.getLogger(__name__)


@dataclass
class NetworkState:
    """Tracks network connectivity state"""
    is_connected: bool = True
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    last_successful_operation: Optional[datetime] = None


@dataclass
class ResumePoint:
    """Represents a point where recovery can be resumed"""
    operation_id: str
    snapshot_id: str
    last_completed_file: Optional[str] = None
    files_completed: int = 0
    bytes_transferred: int = 0
    timestamp: Optional[datetime] = None


class NetworkInterruptionHandler:
    """
    Handles network interruptions during recovery operations with
    automatic resume capabilities.
    
    This handler provides:
    - Network connectivity monitoring
    - Automatic retry with exponential backoff
    - Resume point tracking for interrupted operations
    - Connection health checks
    """
    
    def __init__(
        self,
        max_retries: int = 5,
        initial_retry_delay: float = 2.0,
        max_retry_delay: float = 60.0,
        connection_timeout: float = 10.0
    ):
        """
        Initialize the NetworkInterruptionHandler.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
            connection_timeout: Timeout for connection checks in seconds
        """
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.connection_timeout = connection_timeout
        
        self._network_state = NetworkState()
        self._resume_points: dict[str, ResumePoint] = {}
        
        logger.info(f"NetworkInterruptionHandler initialized with max_retries={max_retries}")
    
    def handle_network_error(
        self,
        error: Exception,
        operation_id: str,
        retry_count: int = 0
    ) -> bool:
        """
        Handle a network error and determine if operation should be retried.
        
        Args:
            error: The network error that occurred
            operation_id: ID of the recovery operation
            retry_count: Current retry attempt number
            
        Returns:
            True if operation should be retried, False otherwise
        """
        self._network_state.consecutive_failures += 1
        self._network_state.is_connected = False
        self._network_state.last_check = datetime.now()
        
        logger.warning(
            f"Network error in operation {operation_id} (attempt {retry_count + 1}): {error}"
        )
        
        # Check if we should retry
        if retry_count >= self.max_retries:
            logger.error(
                f"Max retries ({self.max_retries}) exceeded for operation {operation_id}"
            )
            return False
        
        # Calculate retry delay with exponential backoff
        retry_delay = min(
            self.initial_retry_delay * (2 ** retry_count),
            self.max_retry_delay
        )
        
        logger.info(
            f"Will retry operation {operation_id} in {retry_delay:.1f}s "
            f"(attempt {retry_count + 1}/{self.max_retries})"
        )
        
        # Wait before retry
        time.sleep(retry_delay)
        
        # Check if network is back
        if self.check_network_connectivity():
            logger.info(f"Network connectivity restored for operation {operation_id}")
            self._network_state.consecutive_failures = 0
            return True
        else:
            logger.warning(f"Network still unavailable for operation {operation_id}")
            return retry_count + 1 < self.max_retries
    
    def check_network_connectivity(self, host: str = "8.8.8.8", port: int = 53) -> bool:
        """
        Check if network connectivity is available.
        
        Args:
            host: Host to check connectivity against (default: Google DNS)
            port: Port to use for connectivity check
            
        Returns:
            True if network is available, False otherwise
        """
        try:
            socket.setdefaulttimeout(self.connection_timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            
            self._network_state.is_connected = True
            self._network_state.last_check = datetime.now()
            self._network_state.last_successful_operation = datetime.now()
            
            return True
            
        except (socket.error, socket.timeout) as e:
            logger.debug(f"Network connectivity check failed: {e}")
            self._network_state.is_connected = False
            self._network_state.last_check = datetime.now()
            return False
    
    def save_resume_point(
        self,
        operation_id: str,
        snapshot_id: str,
        last_completed_file: Optional[str] = None,
        files_completed: int = 0,
        bytes_transferred: int = 0
    ) -> None:
        """
        Save a resume point for an operation.
        
        Args:
            operation_id: ID of the recovery operation
            snapshot_id: ID of the snapshot being recovered
            last_completed_file: Path of the last successfully completed file
            files_completed: Number of files completed so far
            bytes_transferred: Number of bytes transferred so far
        """
        resume_point = ResumePoint(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            last_completed_file=last_completed_file,
            files_completed=files_completed,
            bytes_transferred=bytes_transferred,
            timestamp=datetime.now()
        )
        
        self._resume_points[operation_id] = resume_point
        
        logger.debug(
            f"Saved resume point for operation {operation_id}: "
            f"{files_completed} files, {bytes_transferred} bytes"
        )
    
    def get_resume_point(self, operation_id: str) -> Optional[ResumePoint]:
        """
        Get the resume point for an operation.
        
        Args:
            operation_id: ID of the recovery operation
            
        Returns:
            ResumePoint if available, None otherwise
        """
        return self._resume_points.get(operation_id)
    
    def clear_resume_point(self, operation_id: str) -> None:
        """
        Clear the resume point for a completed operation.
        
        Args:
            operation_id: ID of the recovery operation
        """
        if operation_id in self._resume_points:
            del self._resume_points[operation_id]
            logger.debug(f"Cleared resume point for operation {operation_id}")
    
    def with_network_retry(
        self,
        operation: Callable[..., Any],
        operation_id: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with automatic network error retry.
        
        Args:
            operation: Function to execute
            operation_id: ID of the recovery operation
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            NetworkInterruptionError: If operation fails after all retries
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                result = operation(*args, **kwargs)
                
                # Operation succeeded
                self._network_state.last_successful_operation = datetime.now()
                self._network_state.consecutive_failures = 0
                
                return result
                
            except (NetworkInterruptionError, NetworkTimeoutError, 
                    RepositoryConnectionError, ConnectionError, 
                    socket.timeout, socket.error) as e:
                last_error = e
                
                if not self.handle_network_error(e, operation_id, retry_count):
                    break
                
                retry_count += 1
        
        # All retries exhausted
        error_msg = (
            f"Operation {operation_id} failed after {retry_count} retries: {last_error}"
        )
        logger.error(error_msg)
        raise NetworkInterruptionError(error_msg) from last_error
    
    def get_network_state(self) -> NetworkState:
        """
        Get the current network state.
        
        Returns:
            Current NetworkState
        """
        return self._network_state
    
    def is_network_healthy(self, max_failures: int = 3) -> bool:
        """
        Check if network is in a healthy state.
        
        Args:
            max_failures: Maximum consecutive failures before considering unhealthy
            
        Returns:
            True if network is healthy, False otherwise
        """
        if not self._network_state.is_connected:
            return False
        
        if self._network_state.consecutive_failures >= max_failures:
            return False
        
        # Check if last successful operation was recent (within 5 minutes)
        if self._network_state.last_successful_operation:
            time_since_success = datetime.now() - self._network_state.last_successful_operation
            if time_since_success > timedelta(minutes=5):
                return False
        
        return True
