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

from typing_extensions import Self


class BackupSnapshot():
    """Interface for backup snapshots"""
    from TimeLocker.backup_repository import BackupRepository
    repo: BackupRepository
    id: str
    timestamp: datetime
    paths: list[Path]
    tags: List[str]
    size: int

    def __init__(self, repo: BackupRepository, snapshot_id: str, timestamp: datetime, paths: list[Path]):
        self.repo = repo
        self.id = snapshot_id
        self.timestamp = timestamp
        self.paths = paths

    def restore(self, target_path: Optional[Path] = None) -> str:
        """Restore this snapshot"""
        return self.repo.restore(self.id, target_path)

    def restore_file(self, target_path: Optional[Path] = None) -> bool:
        """Restore a single file from this snapshot"""
        try:
            self.repo.restore(self.id, target_path)
            return True
        except:
            return False

    def find(self, pattern: str) -> list[str]:
        """Find files matching pattern in this snapshot"""
        if not pattern:
            return []
        return []  # Mock implementation - in real code would search snapshot contents

    def list(self, dir: Optional[Path] = None) -> list[str]:
        """List files in this snapshot"""
        return []  # Mock implementation - in real code would list snapshot contents

    def get_stats(self) -> dict:
        """Get snapshot stats"""
        return {
            'total_size': 0,
            'total_files': 0,
            'unique_files': 0
        }

    def verify(self) -> bool:
        """Verify snapshot integrity"""
        return False  # Mock implementation - in real code would verify snapshot integrity

    def delete(self, prune: bool = False) -> str:
        """Delete this snapshot"""
        return self.repo.forget_snapshot(self.id, prune)

    @classmethod
    def from_dict(cls, repository: BackupRepository, data: Dict) -> Self:
        """Create a snapshot instance from dictionary data"""
        return cls(
            repo=repository,
            snapshot_id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            paths=Path(data['path'])
        )

