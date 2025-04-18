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

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backup_snapshot import BackupSnapshot

from TimeLocker.backup_target import BackupTarget


class BackupError(Exception):
    """Base exception class for backup operations"""
    pass

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


class BackupRepository(ABC):
    """Abstract class for backup repository"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the backup repository"""
        ...

    @abstractmethod
    def check(self) -> bool:
        """Check if the backup repository is available"""
        ...

    @abstractmethod
    def backup_target(self,
                      targets: List[BackupTarget],
                      tags: Optional[List[str]] = None) -> Dict:
        """Create a new backup"""
        ...

    @abstractmethod
    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        """
        Restores a specific snapshot to the given target path.

        This method is responsible for taking an identified snapshot
        and restoring its data to a provided destination path. The
        operation's result is returned as a string.

        :param snapshot_id: The unique identifier of the snapshot to
            restore.
        :param target_path: The file system path where the snapshot
            should be restored to.
        :return: A string message indicating the result of the
            restore operation.
        """
        ...

    @abstractmethod
    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        """List available snapshots"""
        ...

    @abstractmethod
    def stats(self) -> dict:
        """Get snapshot stats"""
        ...

    @abstractmethod
    def location(self) -> str:
        """Get repository location"""
        pass

    def apply_retention_policy(self, policy: RetentionPolicy, prune: bool = False) -> bool:
        """
        Remove snapshots according to retention policy.
        At least one retention period must be specified.

        Args:
            policy: Retention policy specifying which snapshots to keep
            prune: If True, automatically run prune after forgetting snapshots
        """
        ...

    @abstractmethod
    def forget_snapshot(self, snapshotid: str, prune: bool = False) -> bool:
        """
        Remove a snapshot by id.

        Args:
            snapshotid: ID of snapshot to be removed
            prune: If True, automatically run prune after forgetting snapshots
        """
        ...

    @abstractmethod
    def prune_data(self) -> bool:
        """
        Remove unreferenced data from the repository.
        This removes file chunks that are no longer used by any snapshot.
        """
        ...

    @abstractmethod
    def validate(self) -> bool:
        """Validate repository configuration"""
        pass
