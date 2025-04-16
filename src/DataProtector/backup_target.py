from typing import List
from file_selections import FileSelection


class BackupTarget:
    """Represents a backup target with paths and metadata"""

    def __init__(self,
                 selection: FileSelection,
                 tags: List[str] = None):
        """
        Initialize a backup target
        
        Args:
            selection: FileSelection instance defining what to backup
            tags: Optional list of tags to associate with this backup target
        """
        self.selection = selection
        self.tags = tags or []

    def validate(self) -> bool:
        """
        Validate the backup target configuration
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If the selection configuration is invalid
        """
        return self.selection.validate()

