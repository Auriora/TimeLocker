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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from threading import Lock

from .interfaces.recovery_models import (
    RecoveryOperation,
    RecoveryOptions,
    RecoveryType,
    OperationStatus,
    SelectionCriteria,
    ProgressStatus,
    ErrorDetails
)
from .recovery_errors import (
    RecoveryError,
    RestoreError,
    RestoreTargetError,
    SnapshotNotFoundError
)
from .restore_manager import RestoreManager, RestoreOptions as LegacyRestoreOptions
from .backup_repository import BackupRepository
from .snapshot_manager import SnapshotManager
from .recovery_state_manager import RecoveryStateManager

logger = logging.getLogger(__name__)


class RecoveryOrchestrator:
    """
    Coordinates recovery operations across different backup tools and manages
    the overall recovery workflow including validation and progress monitoring.
    
    This class serves as the central coordination component for all recovery
    operations, providing a unified interface while maintaining backward
    compatibility with the existing RestoreManager.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        snapshot_manager: Optional[SnapshotManager] = None,
        restore_manager: Optional[RestoreManager] = None,
        state_manager: Optional[RecoveryStateManager] = None
    ):
        """
        Initialize the RecoveryOrchestrator.
        
        Args:
            repository: BackupRepository instance for accessing snapshots
            snapshot_manager: Optional SnapshotManager instance
            restore_manager: Optional RestoreManager for backward compatibility
            state_manager: Optional RecoveryStateManager for operation persistence
        """
        self.repository = repository
        self.snapshot_manager = snapshot_manager or SnapshotManager(repository)
        self.restore_manager = restore_manager or RestoreManager(repository, self.snapshot_manager)
        self.state_manager = state_manager or RecoveryStateManager()
        
        # Track active and completed operations
        self._operations: Dict[str, RecoveryOperation] = {}
        self._operation_options: Dict[str, RecoveryOptions] = {}
        self._operations_lock = Lock()
        
        # Load any existing operations from persistent storage
        self._load_persisted_operations()
        
        logger.info("RecoveryOrchestrator initialized")
    
    def initiate_full_recovery(
        self,
        snapshot_id: str,
        target_path: str,
        options: Optional[RecoveryOptions] = None
    ) -> RecoveryOperation:
        """
        Initiates full snapshot restoration.
        
        This method performs a complete restoration of all files from the
        specified snapshot to the target location.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Destination path for restored files
            options: Optional recovery configuration options
            
        Returns:
            RecoveryOperation object tracking the operation
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RestoreTargetError: If the target path is invalid
            RecoveryError: For other recovery-related errors
        """
        if options is None:
            options = RecoveryOptions()
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
            if not snapshot:
                raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Validate target path
        target = Path(target_path)
        if target.exists() and not target.is_dir():
            raise RestoreTargetError(f"Target path exists but is not a directory: {target_path}")
        
        # Create recovery operation
        operation = RecoveryOperation(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            recovery_type=RecoveryType.FULL,
            target_path=str(target),
            status=OperationStatus.PENDING,
            start_time=datetime.now()
        )
        
        # Store options separately (not part of the data model)
        self._operation_options[operation_id] = options
        
        # Register operation
        with self._operations_lock:
            self._operations[operation_id] = operation
        
        # Persist operation state
        self.state_manager.save_operation(operation)
        
        logger.info(f"Initiated full recovery operation {operation_id} for snapshot {snapshot_id}")
        
        # Execute recovery in the background (or synchronously for now)
        try:
            self._execute_full_recovery(operation)
        except Exception as e:
            logger.error(f"Full recovery operation {operation_id} failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            # Update persisted state
            self.state_manager.save_operation(operation)
        
        return operation
    
    def initiate_selective_recovery(
        self,
        snapshot_id: str,
        selection_criteria: SelectionCriteria,
        target_path: str,
        options: Optional[RecoveryOptions] = None
    ) -> RecoveryOperation:
        """
        Initiates selective file restoration.
        
        This method performs restoration of specific files matching the
        selection criteria from the specified snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore from
            selection_criteria: Criteria for selecting files to restore
            target_path: Destination path for restored files
            options: Optional recovery configuration options
            
        Returns:
            RecoveryOperation object tracking the operation
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RestoreTargetError: If the target path is invalid
            RecoveryError: For other recovery-related errors
        """
        if options is None:
            options = RecoveryOptions()
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
            if not snapshot:
                raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found")
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Validate target path
        target = Path(target_path)
        if target.exists() and not target.is_dir():
            raise RestoreTargetError(f"Target path exists but is not a directory: {target_path}")
        
        # Create recovery operation
        operation = RecoveryOperation(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            recovery_type=RecoveryType.SELECTIVE,
            target_path=str(target),
            status=OperationStatus.PENDING,
            start_time=datetime.now()
        )
        
        # Store options separately (not part of the data model)
        self._operation_options[operation_id] = options
        
        # Register operation
        with self._operations_lock:
            self._operations[operation_id] = operation
        
        # Persist operation state
        self.state_manager.save_operation(operation)
        
        logger.info(f"Initiated selective recovery operation {operation_id} for snapshot {snapshot_id}")
        
        # Execute recovery
        try:
            self._execute_selective_recovery(operation, selection_criteria)
        except Exception as e:
            logger.error(f"Selective recovery operation {operation_id} failed: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            # Update persisted state
            self.state_manager.save_operation(operation)
        
        return operation
    
    def get_recovery_status(self, operation_id: str) -> Optional[RecoveryOperation]:
        """
        Retrieves current status of a recovery operation.
        
        Args:
            operation_id: ID of the recovery operation
            
        Returns:
            RecoveryOperation object if found, None otherwise
        """
        with self._operations_lock:
            return self._operations.get(operation_id)
    
    def cancel_recovery(self, operation_id: str) -> bool:
        """
        Cancels an ongoing recovery operation.
        
        Args:
            operation_id: ID of the recovery operation to cancel
            
        Returns:
            True if operation was cancelled, False if not found or already complete
        """
        with self._operations_lock:
            operation = self._operations.get(operation_id)
            
            if not operation:
                logger.warning(f"Cannot cancel operation {operation_id}: not found")
                return False
            
            if not operation.is_active():
                logger.warning(f"Cannot cancel operation {operation_id}: already complete")
                return False
            
            # Mark as cancelled
            operation.status = OperationStatus.CANCELLED
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
            logger.info(f"Cancelled recovery operation {operation_id}")
            return True

    
    def list_operations(self, include_completed: bool = True) -> List[RecoveryOperation]:
        """
        List all recovery operations.
        
        Args:
            include_completed: Whether to include completed operations
            
        Returns:
            List of RecoveryOperation objects
        """
        with self._operations_lock:
            operations = list(self._operations.values())
            
            if not include_completed:
                operations = [op for op in operations if op.is_active()]
            
            return operations
    
    def _execute_full_recovery(self, operation: RecoveryOperation) -> None:
        """
        Execute full recovery using the RestoreManager for backward compatibility.
        
        Args:
            operation: RecoveryOperation to execute
        """
        operation.status = OperationStatus.RUNNING
        logger.info(f"Executing full recovery for operation {operation.operation_id}")
        
        try:
            # Convert new RecoveryOptions to legacy RestoreOptions
            legacy_options = self._convert_to_legacy_options(operation)
            
            # Execute restore using existing RestoreManager
            result = self.restore_manager.restore_snapshot(
                operation.snapshot_id,
                legacy_options
            )
            
            # Update operation with results
            operation.progress.files_processed = result.files_restored
            operation.progress.total_files = result.files_restored + result.files_skipped
            operation.progress.bytes_transferred = result.bytes_restored
            
            if result.success:
                operation.status = OperationStatus.COMPLETED
                logger.info(f"Full recovery operation {operation.operation_id} completed successfully")
            else:
                operation.status = OperationStatus.FAILED
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                operation.error_details = ErrorDetails(
                    error_type="RestoreError",
                    error_message=error_msg,
                    timestamp=datetime.now(),
                    is_recoverable=False
                )
                logger.error(f"Full recovery operation {operation.operation_id} failed: {error_msg}")
            
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
        except Exception as e:
            logger.error(f"Exception during full recovery {operation.operation_id}: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            raise
    
    def _execute_selective_recovery(
        self,
        operation: RecoveryOperation,
        selection_criteria: SelectionCriteria
    ) -> None:
        """
        Execute selective recovery using the RestoreManager.
        
        Args:
            operation: RecoveryOperation to execute
            selection_criteria: Criteria for file selection
        """
        operation.status = OperationStatus.RUNNING
        logger.info(f"Executing selective recovery for operation {operation.operation_id}")
        
        try:
            # Convert new RecoveryOptions to legacy RestoreOptions
            legacy_options = self._convert_to_legacy_options(operation)
            
            # Apply selection criteria to legacy options
            if selection_criteria.include_patterns:
                legacy_options.include_paths = [
                    Path(pattern) for pattern in selection_criteria.include_patterns
                ]
            
            if selection_criteria.exclude_patterns:
                legacy_options.exclude_paths = [
                    Path(pattern) for pattern in selection_criteria.exclude_patterns
                ]
            
            # Execute restore using existing RestoreManager
            result = self.restore_manager.restore_snapshot(
                operation.snapshot_id,
                legacy_options
            )
            
            # Update operation with results
            operation.progress.files_processed = result.files_restored
            operation.progress.total_files = result.files_restored + result.files_skipped
            operation.progress.bytes_transferred = result.bytes_restored
            
            if result.success:
                operation.status = OperationStatus.COMPLETED
                logger.info(f"Selective recovery operation {operation.operation_id} completed successfully")
            else:
                operation.status = OperationStatus.FAILED
                error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
                operation.error_details = ErrorDetails(
                    error_type="RestoreError",
                    error_message=error_msg,
                    timestamp=datetime.now(),
                    is_recoverable=False
                )
                logger.error(f"Selective recovery operation {operation.operation_id} failed: {error_msg}")
            
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            
        except Exception as e:
            logger.error(f"Exception during selective recovery {operation.operation_id}: {e}")
            operation.status = OperationStatus.FAILED
            operation.error_details = ErrorDetails(
                error_type=type(e).__name__,
                error_message=str(e),
                timestamp=datetime.now(),
                is_recoverable=False
            )
            operation.completion_time = datetime.now()
            
            # Update persisted state
            self.state_manager.save_operation(operation)
            raise
    
    def _convert_to_legacy_options(self, operation: RecoveryOperation) -> LegacyRestoreOptions:
        """
        Convert new RecoveryOptions to legacy RestoreOptions for backward compatibility.
        
        Args:
            operation: RecoveryOperation containing options to convert
            
        Returns:
            LegacyRestoreOptions instance
        """
        legacy_options = LegacyRestoreOptions()
        
        # Get options from separate storage
        options = self._operation_options.get(operation.operation_id)
        
        if options:
            legacy_options.target_path = Path(operation.target_path)
            legacy_options.preserve_permissions = options.preserve_permissions
            legacy_options.verify_after_restore = options.verify_integrity
            
            # Map conflict resolution based on overwrite setting
            from .restore_manager import ConflictResolution
            if options.overwrite_existing:
                legacy_options.conflict_resolution = ConflictResolution.OVERWRITE
            else:
                legacy_options.conflict_resolution = ConflictResolution.SKIP
        else:
            legacy_options.target_path = Path(operation.target_path)
        
        return legacy_options

    
    def cleanup_operation(self, operation_id: str) -> bool:
        """
        Clean up a completed recovery operation.
        
        This removes the operation from memory and optionally from persistent storage.
        
        Args:
            operation_id: ID of the operation to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        with self._operations_lock:
            operation = self._operations.get(operation_id)
            
            if not operation:
                logger.warning(f"Cannot cleanup operation {operation_id}: not found")
                return False
            
            if operation.is_active():
                logger.warning(f"Cannot cleanup operation {operation_id}: still active")
                return False
            
            # Remove from memory
            del self._operations[operation_id]
            
            # Remove from persistent storage
            self.state_manager.delete_operation(operation_id)
            
            logger.info(f"Cleaned up recovery operation {operation_id}")
            return True
    
    def cleanup_old_operations(self, days: int = 30) -> int:
        """
        Clean up old completed operations.
        
        Args:
            days: Number of days to keep operation history
            
        Returns:
            Number of operations cleaned up
        """
        # Clean up from persistent storage
        cleaned_count = self.state_manager.cleanup_old_operations(days)
        
        # Clean up from memory
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        with self._operations_lock:
            operations_to_remove = []
            
            for operation_id, operation in self._operations.items():
                if operation.is_complete():
                    completion_time = operation.completion_time or operation.start_time
                    if completion_time.timestamp() < cutoff_time:
                        operations_to_remove.append(operation_id)
            
            for operation_id in operations_to_remove:
                del self._operations[operation_id]
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old recovery operations")
        return cleaned_count
    
    def _load_persisted_operations(self) -> None:
        """Load persisted operations from storage on initialization."""
        try:
            # Load only active operations
            active_statuses = [
                OperationStatus.PENDING,
                OperationStatus.RUNNING,
                OperationStatus.VALIDATING
            ]
            
            persisted_operations = self.state_manager.list_operations(
                status_filter=active_statuses
            )
            
            with self._operations_lock:
                for operation in persisted_operations:
                    self._operations[operation.operation_id] = operation
            
            if persisted_operations:
                logger.info(f"Loaded {len(persisted_operations)} persisted recovery operations")
            
        except Exception as e:
            logger.error(f"Failed to load persisted operations: {e}")
