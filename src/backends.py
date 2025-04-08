from typing import Dict, List, Optional, Protocol, Union
from dataclasses import dataclass

from snapshot import BackupSnapshot
from target import BackupTarget


@dataclass
class RetentionPolicy:
    """Defines how many snapshots to keep for different time periods"""
    hourly: Optional[int] = None
    daily: Optional[int] = None
    weekly: Optional[int] = None
    monthly: Optional[int] = None
    yearly: Optional[int] = None
    last: Optional[int] = None

    def is_valid(self) -> bool:
        """Check if at least one retention period is specified"""
        return any(
            value is not None and value > 0
            for value in [self.hourly, self.daily, self.weekly,
                          self.monthly, self.yearly, self.last]
        )


class BackupRepository(Protocol):
    """Interface for backup repositories"""

    def initialize(self) -> bool:
        """Initialize the backup repository"""
        ...

    def create_backup(self,
                      targets: List[BackupTarget],
                      tags: Optional[List[str]] = None) -> Dict:
        """Create a new backup"""
        ...

    def list_snapshots(self,
                       tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        """List available snapshots"""
        ...

    def forget(self, policy: RetentionPolicy, prune: bool = False) -> bool:
        """
        Remove snapshots according to retention policy.
        At least one retention period must be specified.

        Args:
            policy: Retention policy specifying which snapshots to keep
            prune: If True, automatically run prune after forgetting snapshots
        """
        ...

    def prune(self) -> bool:
        """
        Remove unreferenced data from the repository.
        This removes file chunks that are no longer used by any snapshot.
        """
        ...


class BackupError(Exception):
    """Base exception class for backup operations"""
    pass
