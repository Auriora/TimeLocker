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

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from typing_extensions import Self

if TYPE_CHECKING:
    from .backup_repository import BackupRepository


class BackupSnapshot:
    """Interface for backup snapshots"""
    repo: 'BackupRepository'
    id: str
    timestamp: datetime
    paths: Path | list[Path]
    tags: list[str]
    size: int

    def __init__(self, repo: 'BackupRepository', snapshot_id: str, timestamp: datetime, paths: Path | list[Path]):
        self.repo = repo
        self.id = snapshot_id
        self.timestamp = timestamp
        self.paths = paths
        self.tags = []
        self.size = 0
        self.hostname = ""
        self.username = ""

    @property
    def time(self) -> datetime:
        """Backward-compatible alias for the canonical snapshot timestamp."""
        return self.timestamp

    def restore(
            self,
            target_path: Optional[Path] = None,
            *,
            overwrite: str = "never",
            include_paths: Optional[list[Path]] = None,
            exclude_paths: Optional[list[Path]] = None,
    ) -> str:
        """Restore this snapshot"""
        return self.repo.restore(
            self.id,
            target_path,
            overwrite=overwrite,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
        )

    def restore_file(self, target_path: Optional[Path] = None) -> bool:
        """Restore a single file from this snapshot"""
        try:
            self.repo.restore(self.id, target_path, overwrite="never")
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

    def get_stats(self) -> dict[str, int]:
        """Get snapshot stats"""
        return {
            'total_size': 0,
            'total_files': 0,
            'unique_files': 0
        }

    def verify(self) -> bool:
        """Verify snapshot integrity"""
        return False  # Mock implementation - in real code would verify snapshot integrity

    def delete(self, prune: bool = False) -> bool:
        """Delete this snapshot"""
        return self.repo.forget_snapshot(self.id, prune)

    @classmethod
    def from_dict(cls, repository: 'BackupRepository', data: Mapping[str, object]) -> Self:
        """Create a snapshot instance from dictionary data"""
        if 'paths' not in data and 'path' not in data:
            raise KeyError('path')
        raw_paths = data.get('paths', data.get('path'))
        if isinstance(raw_paths, (str, Path)):
            paths = [Path(str(raw_paths))]
        else:
            paths = [Path(str(path)) for path in raw_paths]
        timestamp_value = data.get('timestamp', data.get('time'))
        if timestamp_value is None:
            raise ValueError("Snapshot timestamp is required")
        return cls(
            repo=repository,
            snapshot_id=str(data['id']),
            timestamp=datetime.fromisoformat(str(timestamp_value).replace('Z', '+00:00')),
            paths=paths
        )
