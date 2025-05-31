"""
Mock repository implementation for recovery operations testing
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock

from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget


class MockRecoveryRepository(BackupRepository):
    """Enhanced mock repository for testing recovery operations"""

    def __init__(self):
        self._initialized = False
        self._snapshots = {}
        self._location = "/mock/recovery/repository"
        self._restore_results = {}
        self._should_fail_restore = False
        self._should_fail_snapshots = False

        # Create some test snapshots
        self._create_test_snapshots()

    def _create_test_snapshots(self):
        """Create test snapshots for testing"""
        base_time = datetime.now() - timedelta(days=7)

        # Snapshot 1: Recent full backup
        snapshot1 = BackupSnapshot(
                repo=self,
                snapshot_id="abc123",
                timestamp=base_time + timedelta(days=6),
                paths=[Path("/home/user/documents"), Path("/home/user/photos")]
        )
        snapshot1.tags = ["full", "documents", "photos"]
        snapshot1.size = 1024 * 1024 * 100  # 100MB
        # Override get_stats to return the size
        snapshot1.get_stats = lambda: {'total_size': snapshot1.size, 'total_files': 100, 'unique_files': 95}
        self._snapshots["abc123"] = snapshot1

        # Snapshot 2: Older incremental backup
        snapshot2 = BackupSnapshot(
                repo=self,
                snapshot_id="def456",
                timestamp=base_time + timedelta(days=3),
                paths=[Path("/home/user/documents")]
        )
        snapshot2.tags = ["incremental", "documents"]
        snapshot2.size = 1024 * 1024 * 50  # 50MB
        # Override get_stats to return the size
        snapshot2.get_stats = lambda: {'total_size': snapshot2.size, 'total_files': 50, 'unique_files': 45}
        self._snapshots["def456"] = snapshot2

        # Snapshot 3: Very old backup
        snapshot3 = BackupSnapshot(
                repo=self,
                snapshot_id="ghi789",
                timestamp=base_time,
                paths=[Path("/home/user/config")]
        )
        snapshot3.tags = ["full", "config"]
        snapshot3.size = 1024 * 1024 * 10  # 10MB
        # Override get_stats to return the size
        snapshot3.get_stats = lambda: {'total_size': snapshot3.size, 'total_files': 10, 'unique_files': 10}
        self._snapshots["ghi789"] = snapshot3

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def check(self) -> bool:
        return self._initialized

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        # Not needed for recovery testing
        return {"snapshot_id": "new-snapshot", "summary": "Mock backup"}

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        """Mock restore operation"""
        if self._should_fail_restore:
            raise Exception("Mock restore failure")

        if snapshot_id not in self._snapshots:
            raise Exception(f"Snapshot {snapshot_id} not found")

        # Simulate restore output
        result = f"Mock restore of snapshot {snapshot_id} to {target_path} completed successfully"
        self._restore_results[snapshot_id] = {
                "target_path": str(target_path) if target_path else None,
                "timestamp":   datetime.now(),
                "success":     True
        }
        return result

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        """Return mock snapshots"""
        if self._should_fail_snapshots:
            raise Exception("Mock snapshots listing failure")

        result = list(self._snapshots.values())

        # Filter by tags if provided
        if tags:
            filtered = []
            for snapshot in result:
                if any(tag in getattr(snapshot, 'tags', []) for tag in tags):
                    filtered.append(snapshot)
            result = filtered

        return result

    def stats(self) -> dict:
        return {
                "total_size":      sum(s.size for s in self._snapshots.values()),
                "total_snapshots": len(self._snapshots)
        }

    def location(self) -> str:
        return self._location

    def forget_snapshot(self, snapshotid: str, prune: bool = False) -> bool:
        if snapshotid in self._snapshots:
            del self._snapshots[snapshotid]
            return True
        return False

    def prune_data(self) -> bool:
        return True

    def validate(self) -> bool:
        return True

    # Test helper methods
    def set_restore_failure(self, should_fail: bool):
        """Configure restore operations to fail for testing"""
        self._should_fail_restore = should_fail

    def set_snapshots_failure(self, should_fail: bool):
        """Configure snapshot listing to fail for testing"""
        self._should_fail_snapshots = should_fail

    def get_restore_history(self) -> Dict:
        """Get history of restore operations for testing"""
        return self._restore_results.copy()

    def add_test_snapshot(self, snapshot_id: str, timestamp: datetime,
                          paths: List[Path], tags: List[str] = None, size: int = 0):
        """Add a test snapshot"""
        snapshot = BackupSnapshot(
                repo=self,
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                paths=paths
        )
        snapshot.tags = tags or []
        snapshot.size = size
        # Override get_stats to return the size
        snapshot.get_stats = lambda: {'total_size': snapshot.size, 'total_files': 1, 'unique_files': 1}
        self._snapshots[snapshot_id] = snapshot

    def clear_snapshots(self):
        """Clear all snapshots for testing"""
        self._snapshots.clear()
        self._restore_results.clear()
