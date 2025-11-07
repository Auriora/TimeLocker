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

from typing import Any, Dict, List, Optional

from .file_selections import FileSelection


class BackupTarget:
    """
    Represents a backup target with paths and metadata.
    
    BackupTarget now supports integration with the SelectionManager for
    advanced selection capabilities including templates, pattern groups,
    and precedence rules.
    """

    def __init__(self,
                 selection: FileSelection = None,
                 tags: List[str] = None,
                 name: str = None,
                 template_id: Optional[str] = None,
                 template_overrides: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        Initialize a backup target

        Args:
            selection: FileSelection instance defining what to backup
            tags: Optional list of tags to associate with this backup target
            name: Optional name for the backup target (for backward compatibility)
            template_id: Optional selection template ID to use
            template_overrides: Optional overrides for template configuration
            **kwargs: Additional parameters for backward compatibility
        """
        # Handle backward compatibility for old API
        if selection is None and 'source_paths' in kwargs:
            # Create FileSelection from old API parameters
            from .file_selections import SelectionType
            selection = FileSelection()
            for path in kwargs.get('source_paths', []):
                selection.add_path(path, SelectionType.INCLUDE)

        if selection is None and template_id is None:
            raise AttributeError("Either selection or template_id must be provided")

        # Normalize selection instances coming from different import paths (e.g., src.TimeLocker vs TimeLocker)
        if selection is not None and not isinstance(selection, FileSelection):
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
        
        # New selection management integration
        self.template_id = template_id
        self.template_overrides = template_overrides or {}
        self._selection_service = None
        self._data_selection = None

    def validate(self) -> bool:
        """
        Validate the backup target configuration
        
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If the selection configuration is invalid
        """
        if self.selection is not None:
            return self.selection.validate()
        elif self.template_id is not None:
            # Template-based selection will be validated when resolved
            return True
        else:
            raise ValueError("BackupTarget must have either selection or template_id")
    
    async def resolve_selection(self):
        """
        Resolve the selection configuration.
        
        If a template_id is specified, this method will create a DataSelection
        from the template with any specified overrides. This allows backup
        operations to use advanced selection features.
        
        Returns:
            DataSelection: Resolved data selection
            
        Raises:
            Exception: If template resolution fails
        """
        if self._data_selection is not None:
            return self._data_selection
        
        if self.template_id is not None:
            # Initialize selection service if needed
            if self._selection_service is None:
                from .selection_service_interface import SelectionServiceInterface
                self._selection_service = SelectionServiceInterface()
            
            # Create selection from template
            self._data_selection = await self._selection_service.create_selection_from_template(
                self.template_id,
                self.template_overrides
            )
            
            return self._data_selection
        
        return None
    
    def get_selection_info(self) -> Dict[str, Any]:
        """
        Get information about the selection configuration.
        
        Returns:
            Dictionary with selection information
        """
        info = {
            'name': self.name,
            'tags': self.tags,
            'has_legacy_selection': self.selection is not None,
            'has_template': self.template_id is not None
        }
        
        if self.template_id:
            info['template_id'] = self.template_id
            info['has_overrides'] = bool(self.template_overrides)
        
        if self.selection:
            info['include_count'] = len(getattr(self.selection, 'includes', []))
            info['exclude_count'] = len(getattr(self.selection, 'excludes', []))
            info['include_pattern_count'] = len(getattr(self.selection, 'include_patterns', []))
            info['exclude_pattern_count'] = len(getattr(self.selection, 'exclude_patterns', []))
        
        return info

