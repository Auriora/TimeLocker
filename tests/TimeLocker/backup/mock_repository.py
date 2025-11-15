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

from TimeLocker.backup_repository import BackupRepository, RetentionPolicy
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget


DEFAULT_REPOSITORY_NAME = "mock-repo"
DEFAULT_REPOSITORY_URI = "file:///mock/backup/location"
SUCCESSFUL_RESTORE_MESSAGE = "Mock restore completed successfully"


def _derive_name_from_uri(uri: str) -> str:
    """Best-effort extraction of a repository name from its URI."""
    if not uri:
        return "mock-repo"
    normalized = uri.split("://", 1)[-1]
    candidate = Path(normalized).name or normalized.strip("/ ")
    return candidate or "mock-repo"


class MockBackupRepository(BackupRepository):
    """Mock implementation of BackupRepository for testing."""

    def __init__(self, name: Optional[str] = None, uri: Optional[str] = None, password: Optional[str] = None):
        self._name = name or DEFAULT_REPOSITORY_NAME
        self._uri = uri or DEFAULT_REPOSITORY_URI
        self._password = password
        self._initialized = False
        self._snapshots: Dict[str, BackupSnapshot] = {}
        self._location = self._uri

    @classmethod
    def from_uri(cls, uri: str, password: Optional[str] = None) -> "MockBackupRepository":
        """Create a mock repository instance bound to a URI."""
        name = _derive_name_from_uri(uri)
        repo = cls(name=name, uri=uri, password=password)
        repo._initialized = True
        return repo

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def name(self) -> str:
        return self._name

    def to_env(self) -> Dict[str, str]:
        """Return environment variables needed to access the mock repo."""
        env = {
            "RESTIC_REPOSITORY": self._uri,
            "TIMELOCKER_REPOSITORY_NAME": self._name,
        }
        env["RESTIC_PASSWORD"] = self._password or "test-password"
        return env

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def initialize_repository(self) -> bool:
        return self.initialize()

    def is_repository_initialized(self) -> bool:
        return self._initialized

    def check(self) -> bool:
        return self._initialized

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        if not self._initialized:
            self.initialize()
        snapshot_id = f"mock-snapshot-{len(self._snapshots) + 1}"
        paths = [target.path for target in targets]
        snapshot = BackupSnapshot(self, snapshot_id, datetime.now(), paths)
        snapshot.tags = tags or []
        self._snapshots[snapshot_id] = snapshot
        return {"snapshot_id": snapshot_id, "summary": "Mock backup completed"}

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        if snapshot_id not in self._snapshots:
            return "Snapshot not found"
        destination = target_path or "original location"
        # Keep message stable for unit tests while still providing traceable info.
        if destination == "original location":
            return SUCCESSFUL_RESTORE_MESSAGE
        return SUCCESSFUL_RESTORE_MESSAGE

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        return self.list_snapshots(tags=tags)

    def list_snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        if not tags:
            return list(self._snapshots.values())
        required = set(tags)
        return [
                snapshot
                for snapshot in self._snapshots.values()
                if required.issubset(set(getattr(snapshot, "tags", [])))
        ]

    def stats(self) -> dict:
        return {
                "total_size": len(self._snapshots) * 1024,
                "total_files": max(len(self._snapshots) * 10, 1),
                "unique_files": max(len(self._snapshots) * 5, 1)
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

    def apply_retention_policy(self, policy: Optional[RetentionPolicy], prune: bool = False) -> bool:
        """
        Basic retention policy handler that trims snapshots to the newest item per policy field.
        The real implementation performs more advanced logic; here we simply ensure the method
        exists for tests expecting it.
        """
        if not policy:
            return True
        # Keep at most `policy.last` newest snapshots when specified.
        if policy.last and policy.last > 0:
            sorted_ids = sorted(self._snapshots.items(), key=lambda item: item[1].timestamp, reverse=True)
            for snapshot_id, _ in sorted_ids[policy.last:]:
                self._snapshots.pop(snapshot_id, None)
        if prune:
            self.prune_data()
        return True
