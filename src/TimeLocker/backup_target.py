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

from .file_selections import FileSelection


class BackupTarget:
    """Represents a backup target with paths and metadata"""

    def __init__(self,
                 selection: FileSelection = None,
                 tags: List[str] = None,
                 name: str = None,
                 **kwargs):
        """
        Initialize a backup target

        Args:
            selection: FileSelection instance defining what to backup
            tags: Optional list of tags to associate with this backup target
            name: Optional name for the backup target (for backward compatibility)
            **kwargs: Additional parameters for backward compatibility
        """
        # Handle backward compatibility for old API
        if selection is None and 'source_paths' in kwargs:
            # Create FileSelection from old API parameters
            from .file_selections import SelectionType
            selection = FileSelection()
            for path in kwargs.get('source_paths', []):
                selection.add_path(path, SelectionType.INCLUDE)

        if selection is None:
            raise AttributeError("selection cannot be None")

        # Normalize selection instances coming from different import paths (e.g., src.TimeLocker vs TimeLocker)
        if not isinstance(selection, FileSelection):
            try:
                # Best-effort conversion by copying known properties
                from .file_selections import SelectionType
                normalized = FileSelection()
                # Includes
                for p in getattr(selection, 'includes', []):
                    normalized.add_path(p, SelectionType.INCLUDE)
                # Excludes
                for p in getattr(selection, 'excludes', []):
                    normalized.add_path(p, SelectionType.EXCLUDE)
                # Include patterns
                for pat in getattr(selection, 'include_patterns', []):
                    normalized.add_pattern(pat, SelectionType.INCLUDE)
                # Exclude patterns
                for pat in getattr(selection, 'exclude_patterns', []):
                    normalized.add_pattern(pat, SelectionType.EXCLUDE)
                selection = normalized
            except Exception:
                # If conversion fails, still assign; downstream may only need duck-typing
                pass

        self.selection = selection
        self.tags = tags or []
        self.name = name

    def validate(self) -> bool:
        """
        Validate the backup target configuration
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If the selection configuration is invalid
        """
        return self.selection.validate()

