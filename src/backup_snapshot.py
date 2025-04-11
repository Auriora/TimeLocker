from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from typing_extensions import Self

from backup_repository import BackupRepository


class BackupSnapshot():
    """Interface for backup snapshots"""
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
        ...

    def find(self, pattern: str) -> list[str]:
        """Find files matching pattern in this snapshot"""
        ...

    def list(self, dir: Optional[Path] = None) -> list[str]:
        """List files in this snapshot"""
        ...

    def get_stats(self) -> dict:
        """Get snapshot stats"""
        ...

    def verify(self) -> bool:
        """Verify snapshot integrity"""
        ...

    def delete(self, prune: bool = False) -> str:
        """Delete this snapshot"""
        return self.repo.forget_snapshot(self.id, prune)

    @classmethod
    def from_dict(cls, repository: 'BackupRepository', data: Dict) -> Self:
        """Create a snapshot instance from dictionary data"""
        return cls(
            repo=repository,
            snapshot_id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            paths=Path(data['path'])
        )
