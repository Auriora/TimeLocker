from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from backup_repository import BackupRepository
from backup_target import BackupTarget
from backup_snapshot import BackupSnapshot


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