from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BackupSnapshot():
    """Interface for backup snapshots"""
    id: str
    timestamp: datetime
    tags: List[str]
    size: int

    def __init__(self, snapshot_id: str, timestamp: str, paths: list[str]):
        self.id = snapshot_id
        self.timestamp = timestamp
        self.paths = paths

    def restore(self, target_path: Optional[Path] = None) -> bool:
        """Restore this snapshot"""
        ...

    def verify(self) -> bool:
        """Verify snapshot integrity"""
        ...

    def delete(self) -> bool:
        """Delete this snapshot"""
        ...
