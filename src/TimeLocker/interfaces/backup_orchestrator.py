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

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupResult:
    """Result of a backup operation"""
    status: BackupStatus
    snapshot_id: Optional[str] = None
    repository_name: str = ""
    target_names: List[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    files_processed: int = 0
    bytes_processed: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.target_names is None:
            self.target_names = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class IBackupOrchestrator(ABC):
    """
    Abstract interface for high-level backup orchestration.
    
    This interface follows the Single Responsibility Principle by focusing
    on backup workflow coordination and supports the Open/Closed Principle
    by allowing different backup strategies to be implemented.
    """

    @abstractmethod
    def execute_backup(self,
                       repository_name: str,
                       target_names: List[str],
                       tags: Optional[List[str]] = None,
                       dry_run: bool = False) -> BackupResult:
        """
        Execute a backup operation.
        
        Args:
            repository_name: Name of repository to backup to
            target_names: Names of backup targets to include
            tags: Optional tags to apply to backup
            dry_run: Whether to perform a dry run without actual backup
            
        Returns:
            BackupResult with operation details
            
        Raises:
            BackupOrchestratorError: If backup cannot be executed
        """
        pass

    @abstractmethod
    def execute_scheduled_backups(self) -> List[BackupResult]:
        """
        Execute all scheduled backup operations.
        
        Returns:
            List of BackupResult objects for each scheduled backup
        """
        pass

    @abstractmethod
    def validate_backup_configuration(self,
                                      repository_name: str,
                                      target_names: List[str]) -> bool:
        """
        Validate backup configuration before execution.
        
        Args:
            repository_name: Name of repository to validate
            target_names: Names of backup targets to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            BackupOrchestratorError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_backup_status(self, operation_id: str) -> Optional[BackupResult]:
        """
        Get status of a backup operation.
        
        Args:
            operation_id: Unique identifier for backup operation
            
        Returns:
            BackupResult if operation found, None otherwise
        """
        pass

    @abstractmethod
    def cancel_backup(self, operation_id: str) -> bool:
        """
        Cancel a running backup operation.
        
        Args:
            operation_id: Unique identifier for backup operation
            
        Returns:
            True if backup was cancelled, False if not found or not running
        """
        pass

    @abstractmethod
    def list_active_backups(self) -> List[BackupResult]:
        """
        List all currently active backup operations.
        
        Returns:
            List of BackupResult objects for active operations
        """
        pass

    @abstractmethod
    def get_backup_history(self,
                           repository_name: Optional[str] = None,
                           limit: int = 100) -> List[BackupResult]:
        """
        Get backup operation history.
        
        Args:
            repository_name: Optional repository name to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of BackupResult objects from history
        """
        pass

    @abstractmethod
    def estimate_backup_size(self,
                             repository_name: str,
                             target_names: List[str]) -> Dict[str, Any]:
        """
        Estimate backup size and duration.
        
        Args:
            repository_name: Name of repository
            target_names: Names of backup targets
            
        Returns:
            Dictionary with size and time estimates
        """
        pass

    @abstractmethod
    def verify_backup_integrity(self,
                                repository_name: str,
                                snapshot_id: Optional[str] = None) -> bool:
        """
        Verify backup integrity.
        
        Args:
            repository_name: Name of repository to verify
            snapshot_id: Optional specific snapshot to verify
            
        Returns:
            True if verification successful
            
        Raises:
            BackupOrchestratorError: If verification fails
        """
        pass


class BackupOrchestratorError(Exception):
    """Exception raised by backup orchestrator operations"""
    pass


class InvalidBackupConfigurationError(BackupOrchestratorError):
    """Exception raised when backup configuration is invalid"""
    pass


class BackupExecutionError(BackupOrchestratorError):
    """Exception raised when backup execution fails"""
    pass
