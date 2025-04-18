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

from typing import List

from TimeLocker.file_selections import FileSelection


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

