from typing import Optional, List

from file_exclusions import FileExclusions
from file_selections import FileSelections


class BackupTarget:
    """Represents a backup target with paths and metadata"""

    def __init__(self,
                 selection: FileSelections,
                 exclusion: Optional[FileExclusions] = None,
                 tags: List[str] = None):
        self.selection = selection
        self.exclusion = exclusion or FileExclusions([], [])
        self.tags = tags or []
