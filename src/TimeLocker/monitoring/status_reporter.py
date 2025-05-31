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

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class StatusLevel(Enum):
    """Status levels for operations"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class OperationStatus:
    """Represents the status of a backup/restore operation"""
    operation_id: str
    operation_type: str  # backup, restore, check, etc.
    status: StatusLevel
    message: str
    timestamp: datetime
    repository_id: Optional[str] = None
    progress_percentage: Optional[int] = None
    files_processed: Optional[int] = None
    total_files: Optional[int] = None
    bytes_processed: Optional[int] = None
    total_bytes: Optional[int] = None
    estimated_completion: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['status'] = self.status.value
        if self.estimated_completion:
            result['estimated_completion'] = self.estimated_completion.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationStatus':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['status'] = StatusLevel(data['status'])
        if data.get('estimated_completion'):
            data['estimated_completion'] = datetime.fromisoformat(data['estimated_completion'])
        return cls(**data)


class StatusReporter:
    """
    Status reporting system for backup and restore operations
    Provides real-time status updates, progress tracking, and historical reporting
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize status reporter
        
        Args:
            config_dir: Directory for status logs and configuration
        """
        if config_dir is None:
            config_dir = Path.home() / ".timelocker" / "status"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.status_log_file = self.config_dir / "operations.log"
        self.current_operations_file = self.config_dir / "current_operations.json"

        # In-memory tracking
        self._current_operations: Dict[str, OperationStatus] = {}
        self._status_handlers: List[Callable[[OperationStatus], None]] = []
        self._lock = threading.Lock()

        # Load current operations from disk
        self._load_current_operations()

    def add_status_handler(self, handler: Callable[[OperationStatus], None]):
        """Add a status update handler"""
        with self._lock:
            self._status_handlers.append(handler)

    def remove_status_handler(self, handler: Callable[[OperationStatus], None]):
        """Remove a status update handler"""
        with self._lock:
            if handler in self._status_handlers:
                self._status_handlers.remove(handler)

    def start_operation(self, operation_id: str, operation_type: str,
                        repository_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> OperationStatus:
        """
        Start tracking a new operation
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (backup, restore, check, etc.)
            repository_id: Repository being operated on
            metadata: Additional operation metadata
            
        Returns:
            OperationStatus: Initial status object
        """
        status = OperationStatus(
                operation_id=operation_id,
                operation_type=operation_type,
                status=StatusLevel.INFO,
                message=f"Starting {operation_type} operation",
                timestamp=datetime.now(),
                repository_id=repository_id,
                metadata=metadata or {}
        )

        with self._lock:
            self._current_operations[operation_id] = status
            self._save_current_operations()

        self._notify_handlers(status)
        self._log_status(status)

        logger.info(f"Started operation {operation_id}: {operation_type}")
        return status

    def update_operation(self, operation_id: str, status: Optional[StatusLevel] = None,
                         message: Optional[str] = None, progress_percentage: Optional[int] = None,
                         files_processed: Optional[int] = None, total_files: Optional[int] = None,
                         bytes_processed: Optional[int] = None, total_bytes: Optional[int] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[OperationStatus]:
        """
        Update an existing operation's status
        
        Args:
            operation_id: Operation to update
            status: New status level
            message: Status message
            progress_percentage: Progress percentage (0-100)
            files_processed: Number of files processed
            total_files: Total number of files
            bytes_processed: Bytes processed
            total_bytes: Total bytes to process
            metadata: Additional metadata
            
        Returns:
            Updated OperationStatus or None if operation not found
        """
        with self._lock:
            if operation_id not in self._current_operations:
                logger.warning(f"Attempted to update unknown operation: {operation_id}")
                return None

            current_status = self._current_operations[operation_id]

            # Update fields if provided
            if status is not None:
                current_status.status = status
            if message is not None:
                current_status.message = message
            if progress_percentage is not None:
                current_status.progress_percentage = max(0, min(100, progress_percentage))
            if files_processed is not None:
                current_status.files_processed = files_processed
            if total_files is not None:
                current_status.total_files = total_files
            if bytes_processed is not None:
                current_status.bytes_processed = bytes_processed
            if total_bytes is not None:
                current_status.total_bytes = total_bytes
            if metadata is not None:
                current_status.metadata.update(metadata)

            # Update timestamp
            current_status.timestamp = datetime.now()

            # Calculate estimated completion if we have progress info
            if (current_status.progress_percentage is not None and
                    current_status.progress_percentage > 0 and
                    current_status.progress_percentage < 100):
                # Simple linear estimation based on progress
                elapsed = datetime.now() - datetime.fromisoformat(
                        current_status.metadata.get('start_time', datetime.now().isoformat())
                )
                remaining_progress = 100 - current_status.progress_percentage
                estimated_remaining = elapsed * (remaining_progress / current_status.progress_percentage)
                current_status.estimated_completion = datetime.now() + estimated_remaining

            self._save_current_operations()

        self._notify_handlers(current_status)
        self._log_status(current_status)

        return current_status

    def complete_operation(self, operation_id: str, status: StatusLevel,
                           message: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[OperationStatus]:
        """
        Mark an operation as completed
        
        Args:
            operation_id: Operation to complete
            status: Final status
            message: Completion message
            metadata: Final metadata
            
        Returns:
            Final OperationStatus or None if operation not found
        """
        final_status = self.update_operation(
                operation_id=operation_id,
                status=status,
                message=message,
                progress_percentage=100 if status == StatusLevel.SUCCESS else None,
                metadata=metadata
        )

        if final_status:
            # Remove from current operations
            with self._lock:
                if operation_id in self._current_operations:
                    del self._current_operations[operation_id]
                    self._save_current_operations()

            logger.info(f"Completed operation {operation_id}: {status.value}")

        return final_status

    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """Get current status of an operation"""
        with self._lock:
            return self._current_operations.get(operation_id)

    def get_current_operations(self) -> List[OperationStatus]:
        """Get all currently running operations"""
        with self._lock:
            return list(self._current_operations.values())

    def get_operation_history(self, days: int = 7, operation_type: Optional[str] = None,
                              repository_id: Optional[str] = None) -> List[OperationStatus]:
        """
        Get operation history for the specified period
        
        Args:
            days: Number of days to look back
            operation_type: Filter by operation type
            repository_id: Filter by repository
            
        Returns:
            List of historical operations
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        operations = []

        if not self.status_log_file.exists():
            return operations

        try:
            with open(self.status_log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        operation = OperationStatus.from_dict(data)

                        # Apply filters
                        if operation.timestamp < cutoff_date:
                            continue
                        if operation_type and operation.operation_type != operation_type:
                            continue
                        if repository_id and operation.repository_id != repository_id:
                            continue

                        operations.append(operation)
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception as e:
            logger.error(f"Failed to read operation history: {e}")

        return sorted(operations, key=lambda x: x.timestamp, reverse=True)

    def get_status_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get a summary of operation statuses for the specified period
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dict containing status summary
        """
        operations = self.get_operation_history(days)

        summary = {
                "period_days":        days,
                "total_operations":   len(operations),
                "by_type":            defaultdict(int),
                "by_status":          defaultdict(int),
                "by_repository":      defaultdict(int),
                "current_operations": len(self._current_operations),
                "generated_at":       datetime.now().isoformat()
        }

        for op in operations:
            summary["by_type"][op.operation_type] += 1
            summary["by_status"][op.status.value] += 1
            if op.repository_id:
                summary["by_repository"][op.repository_id] += 1

        return dict(summary)

    def _notify_handlers(self, status: OperationStatus):
        """Notify all registered status handlers"""
        with self._lock:
            handlers = self._status_handlers.copy()

        for handler in handlers:
            try:
                handler(status)
            except Exception as e:
                logger.error(f"Error in status handler: {e}")

    def _log_status(self, status: OperationStatus):
        """Log status to persistent storage"""
        try:
            with open(self.status_log_file, 'a') as f:
                f.write(json.dumps(status.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to log status: {e}")

    def _save_current_operations(self):
        """Save current operations to disk"""
        try:
            data = {op_id: status.to_dict() for op_id, status in self._current_operations.items()}
            with open(self.current_operations_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save current operations: {e}")

    def _load_current_operations(self):
        """Load current operations from disk"""
        try:
            if self.current_operations_file.exists():
                with open(self.current_operations_file, 'r') as f:
                    data = json.load(f)
                    for op_id, status_data in data.items():
                        try:
                            self._current_operations[op_id] = OperationStatus.from_dict(status_data)
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Failed to load operation {op_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to load current operations: {e}")
