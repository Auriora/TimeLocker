"""
Snapshot Interface for TimeLocker

This interface defines the contract for snapshot management operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Any

from .data_models import SnapshotInfo, SnapshotResult, SnapshotSearchResult
from ..backup_repository import BackupRepository


class ISnapshotService(ABC):
    """Interface for snapshot management operations"""

    @abstractmethod
    def get_snapshot_details(self, repository: BackupRepository, snapshot_id: str) -> SnapshotInfo:
        """
        Get detailed information about a specific snapshot
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to examine
            
        Returns:
            SnapshotInfo: Detailed snapshot information
        """
        pass

    @abstractmethod
    def list_snapshot_contents(self, repository: BackupRepository, snapshot_id: str,
                               path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List contents of a snapshot
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to list
            path: Optional path within snapshot to list (defaults to root)
            
        Returns:
            List of file/directory information dictionaries
        """
        pass

    @abstractmethod
    def mount_snapshot(self, repository: BackupRepository, snapshot_id: str,
                       mount_path: Path) -> SnapshotResult:
        """
        Mount a snapshot as a filesystem
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to mount
            mount_path: Path where to mount the snapshot
            
        Returns:
            SnapshotResult: Result of mount operation
        """
        pass

    @abstractmethod
    def unmount_snapshot(self, snapshot_id: str) -> SnapshotResult:
        """
        Unmount a previously mounted snapshot
        
        Args:
            snapshot_id: ID of the snapshot to unmount
            
        Returns:
            SnapshotResult: Result of unmount operation
        """
        pass

    @abstractmethod
    def search_in_snapshot(self, repository: BackupRepository, snapshot_id: str,
                           pattern: str, search_type: str = 'name') -> List[SnapshotSearchResult]:
        """
        Search for files/content within a snapshot

        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to search
            pattern: Search pattern (glob for names, regex for content)
            search_type: Type of search ('name', 'content', 'path')

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    def forget_snapshot(self, repository: BackupRepository, snapshot_id: str) -> SnapshotResult:
        """
        Remove a specific snapshot from the repository

        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to remove

        Returns:
            SnapshotResult: Result of the forget operation
        """
        pass
