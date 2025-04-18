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

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget


class MockBackupRepository(BackupRepository):
    """Mock implementation of BackupRepository for testing"""

    def __init__(self):
        self._initialized = False
        self._snapshots = {}
        self._location = "/mock/backup/location"

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def check(self) -> bool:
        return self._initialized

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        snapshot_id = f"mock-snapshot-{len(self._snapshots)}"
        paths = [target.path for target in targets]
        snapshot = BackupSnapshot(self, snapshot_id, datetime.now(), paths)
        self._snapshots[snapshot_id] = snapshot
        return {"snapshot_id": snapshot_id, "summary": "Mock backup completed"}

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        if snapshot_id in self._snapshots:
            return "Mock restore completed successfully"
        return "Snapshot not found"

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        return list(self._snapshots.values())

    def stats(self) -> dict:
        return {
            "total_size": 1000000,
            "total_files": 100,
            "unique_files": 50
        }

    def location(self) -> str:
        return self._location

    def forget_snapshot(self, snapshotid: str, prune: bool = False) -> bool:
        if snapshotid in self._snapshots:
            del self._snapshots[snapshotid]
            if prune:
                self.prune_data()
            return True
        return False

    def prune_data(self) -> bool:
        return True

    def validate(self) -> bool:
        return self._initialized