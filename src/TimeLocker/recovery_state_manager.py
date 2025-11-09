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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock

from .interfaces.recovery_models import (
    RecoveryOperation,
    RecoveryOptions,
    RecoveryType,
    OperationStatus,
    ProgressStatus,
    ErrorDetails,
    ValidationResult,
    NotificationPreferences,
    FileType,
    FailureType
)

logger = logging.getLogger(__name__)


class RecoveryStateManager:
    """
    Manages persistence and lifecycle of recovery operations.
    
    This class handles saving and loading recovery operation state to/from
    disk, enabling recovery operations to survive application restarts and
    providing operation history tracking.
    """
    
    def __init__(self, state_directory: Optional[Path] = None):
        """
        Initialize the RecoveryStateManager.
        
        Args:
            state_directory: Directory for storing operation state files.
                           Defaults to ~/.timelocker/recovery_state
        """
        if state_directory is None:
            state_directory = Path.home() / ".timelocker" / "recovery_state"
        
        self.state_directory = Path(state_directory)
        self.state_directory.mkdir(parents=True, exist_ok=True)
        
        self._state_lock = Lock()
        
        logger.info(f"RecoveryStateManager initialized with state directory: {self.state_directory}")
    
    def save_operation(self, operation: RecoveryOperation) -> bool:
        """
        Save recovery operation state to disk.
        
        Args:
            operation: RecoveryOperation to save
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            with self._state_lock:
                state_file = self._get_state_file_path(operation.operation_id)
                
                # Convert operation to dictionary
                operation_dict = self._operation_to_dict(operation)
                
                # Write to file
                with open(state_file, 'w') as f:
                    json.dump(operation_dict, f, indent=2, default=str)
                
                logger.debug(f"Saved operation state for {operation.operation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save operation state for {operation.operation_id}: {e}")
            return False
    
    def load_operation(self, operation_id: str) -> Optional[RecoveryOperation]:
        """
        Load recovery operation state from disk.
        
        Args:
            operation_id: ID of the operation to load
            
        Returns:
            RecoveryOperation if found and loaded successfully, None otherwise
        """
        try:
            with self._state_lock:
                state_file = self._get_state_file_path(operation_id)
                
                if not state_file.exists():
                    logger.debug(f"No state file found for operation {operation_id}")
                    return None
                
                # Read from file
                with open(state_file, 'r') as f:
                    operation_dict = json.load(f)
                
                # Convert dictionary to operation
                operation = self._dict_to_operation(operation_dict)
                
                logger.debug(f"Loaded operation state for {operation_id}")
                return operation
                
        except Exception as e:
            logger.error(f"Failed to load operation state for {operation_id}: {e}")
            return None
    
    def delete_operation(self, operation_id: str) -> bool:
        """
        Delete recovery operation state from disk.
        
        Args:
            operation_id: ID of the operation to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            with self._state_lock:
                state_file = self._get_state_file_path(operation_id)
                
                if state_file.exists():
                    state_file.unlink()
                    logger.debug(f"Deleted operation state for {operation_id}")
                    return True
                else:
                    logger.debug(f"No state file to delete for operation {operation_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete operation state for {operation_id}: {e}")
            return False
    
    def list_operations(
        self,
        status_filter: Optional[List[OperationStatus]] = None,
        limit: Optional[int] = None
    ) -> List[RecoveryOperation]:
        """
        List all persisted recovery operations.
        
        Args:
            status_filter: Optional list of statuses to filter by
            limit: Optional maximum number of operations to return
            
        Returns:
            List of RecoveryOperation objects
        """
        operations = []
        
        try:
            with self._state_lock:
                # Get all state files
                state_files = sorted(
                    self.state_directory.glob("*.json"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                
                for state_file in state_files:
                    try:
                        with open(state_file, 'r') as f:
                            operation_dict = json.load(f)
                        
                        operation = self._dict_to_operation(operation_dict)
                        
                        # Apply status filter
                        if status_filter and operation.status not in status_filter:
                            continue
                        
                        operations.append(operation)
                        
                        # Apply limit
                        if limit and len(operations) >= limit:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Failed to load operation from {state_file}: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"Failed to list operations: {e}")
        
        return operations
    
    def cleanup_old_operations(self, days: int = 30) -> int:
        """
        Clean up operation state files older than specified days.
        
        Args:
            days: Number of days to keep operation history
            
        Returns:
            Number of operations cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        try:
            with self._state_lock:
                state_files = self.state_directory.glob("*.json")
                
                for state_file in state_files:
                    try:
                        # Check file modification time
                        if state_file.stat().st_mtime < cutoff_time:
                            state_file.unlink()
                            cleaned_count += 1
                            logger.debug(f"Cleaned up old operation state: {state_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {state_file}: {e}")
                        continue
                
            logger.info(f"Cleaned up {cleaned_count} old operation state files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old operations: {e}")
        
        return cleaned_count
    
    def _get_state_file_path(self, operation_id: str) -> Path:
        """Get the file path for an operation's state file."""
        return self.state_directory / f"{operation_id}.json"
    
    def _operation_to_dict(self, operation: RecoveryOperation) -> Dict:
        """Convert RecoveryOperation to dictionary for JSON serialization."""
        operation_dict = {
            "operation_id": operation.operation_id,
            "snapshot_id": operation.snapshot_id,
            "recovery_type": operation.recovery_type.value,
            "target_path": str(operation.target_path),
            "status": operation.status.value,
            "start_time": operation.start_time.isoformat(),
            "completion_time": operation.completion_time.isoformat() if operation.completion_time else None,
            "progress": {
                "files_processed": operation.progress.files_processed,
                "total_files": operation.progress.total_files,
                "bytes_transferred": operation.progress.bytes_transferred,
                "total_bytes": operation.progress.total_bytes,
                "current_file": operation.progress.current_file,
                "estimated_completion": operation.progress.estimated_completion.isoformat() 
                    if operation.progress.estimated_completion else None,
                "transfer_rate": operation.progress.transfer_rate
            }
        }
        
        # Add optional fields
        if operation.validation_result:
            operation_dict["validation_result"] = {
                "is_valid": operation.validation_result.is_valid,
                "validated_files": operation.validation_result.validated_files,
                "validation_time": operation.validation_result.validation_time.isoformat()
            }
        
        if operation.error_details:
            operation_dict["error_details"] = {
                "error_type": operation.error_details.error_type,
                "error_message": operation.error_details.error_message,
                "timestamp": operation.error_details.timestamp.isoformat(),
                "is_recoverable": operation.error_details.is_recoverable
            }
        
        return operation_dict
    
    def _dict_to_operation(self, operation_dict: Dict) -> RecoveryOperation:
        """Convert dictionary to RecoveryOperation object."""
        # Parse progress
        progress_dict = operation_dict.get("progress", {})
        progress = ProgressStatus(
            files_processed=progress_dict.get("files_processed", 0),
            total_files=progress_dict.get("total_files", 0),
            bytes_transferred=progress_dict.get("bytes_transferred", 0),
            total_bytes=progress_dict.get("total_bytes", 0),
            current_file=progress_dict.get("current_file"),
            estimated_completion=datetime.fromisoformat(progress_dict["estimated_completion"])
                if progress_dict.get("estimated_completion") else None,
            transfer_rate=progress_dict.get("transfer_rate", 0.0)
        )
        
        # Parse optional fields
        validation_result = None
        if "validation_result" in operation_dict:
            vr_dict = operation_dict["validation_result"]
            validation_result = ValidationResult(
                is_valid=vr_dict["is_valid"],
                validated_files=vr_dict["validated_files"],
                validation_time=datetime.fromisoformat(vr_dict["validation_time"])
            )
        
        error_details = None
        if "error_details" in operation_dict:
            ed_dict = operation_dict["error_details"]
            error_details = ErrorDetails(
                error_type=ed_dict["error_type"],
                error_message=ed_dict["error_message"],
                timestamp=datetime.fromisoformat(ed_dict["timestamp"]),
                is_recoverable=ed_dict.get("is_recoverable", False)
            )
        
        # Create operation
        operation = RecoveryOperation(
            operation_id=operation_dict["operation_id"],
            snapshot_id=operation_dict["snapshot_id"],
            recovery_type=RecoveryType(operation_dict["recovery_type"]),
            target_path=operation_dict["target_path"],
            status=OperationStatus(operation_dict["status"]),
            start_time=datetime.fromisoformat(operation_dict["start_time"]),
            completion_time=datetime.fromisoformat(operation_dict["completion_time"])
                if operation_dict.get("completion_time") else None,
            progress=progress,
            validation_result=validation_result,
            error_details=error_details
        )
        
        return operation
