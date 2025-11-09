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

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from TimeLocker.selection_models import (
    PatternCategory,
    PatternGroup,
    PatternRule,
    PatternSyntax,
    PathComponent
)


class PatternGroupNotFoundError(Exception):
    """Raised when a pattern group is not found"""
    pass


class PatternGroupManager:
    """
    Manages pattern groups with CRUD operations and persistence.
    
    Provides functionality to create, read, update, and delete pattern groups,
    including both system-provided and custom groups. Supports persistence to
    configuration storage and pattern group expansion during evaluation.
    """
    
    # System-provided pattern groups
    SYSTEM_GROUPS: Dict[str, PatternGroup] = {}
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the pattern group manager.
        
        Args:
            config_path: Path to configuration file for custom groups.
                        If None, uses default location.
        """
        if config_path is None:
            # Use centralized path resolver for XDG compliance
            # Pattern groups are user data, so use XDG_DATA_HOME
            from .config.configuration_path_resolver import ConfigurationPathResolver
            import os
            
            xdg_data_home = os.environ.get('XDG_DATA_HOME')
            if xdg_data_home:
                data_dir = Path(xdg_data_home) / "timelocker"
            else:
                data_dir = Path.home() / ".local" / "share" / "timelocker"
            
            config_path = data_dir / "pattern_groups.json"
        
        self.config_path = config_path
        self.custom_groups: Dict[str, PatternGroup] = {}
        self._initialize_system_groups()
        self._load_custom_groups()
    
    def _initialize_system_groups(self) -> None:
        """Initialize system-provided pattern groups"""
        self.SYSTEM_GROUPS = {
            "office_documents": PatternGroup(
                id="system_office_docs",
                name="Office Documents",
                description="Common office document formats",
                patterns=[
                    PatternRule("*.doc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.docx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.xls", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.xlsx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.ppt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.pptx", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.pdf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.odt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.ods", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.odp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                category=PatternCategory.DOCUMENT_TYPES,
                is_system_group=True,
                created_at=datetime.utcnow(),
                usage_count=0,
                metadata={"version": "1.0", "maintainer": "system"}
            ),
            
            "temporary_files": PatternGroup(
                id="system_temp_files",
                name="Temporary Files",
                description="Temporary and cache files that can be safely excluded",
                patterns=[
                    PatternRule("*.tmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.temp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("~*", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.bak", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.swp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.cache", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("__pycache__/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 100),
                    PatternRule("*.pyc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 100),
                    PatternRule(".DS_Store", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
                    PatternRule("Thumbs.db", PatternSyntax.LITERAL, False, PathComponent.FILENAME, 100),
                ],
                category=PatternCategory.TEMPORARY_FILES,
                is_system_group=True,
                created_at=datetime.utcnow(),
                usage_count=0,
                metadata={"version": "1.0", "maintainer": "system"}
            ),
            
            "media_files": PatternGroup(
                id="system_media_files",
                name="Media Files",
                description="Common image, audio, and video file formats",
                patterns=[
                    # Images
                    PatternRule("*.jpg", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.jpeg", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.png", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.gif", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.bmp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.tiff", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.webp", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    # Audio
                    PatternRule("*.mp3", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.wav", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.flac", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.aac", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    # Video
                    PatternRule("*.mp4", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.avi", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.mov", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.mkv", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.wmv", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                category=PatternCategory.MEDIA_FILES,
                is_system_group=True,
                created_at=datetime.utcnow(),
                usage_count=0,
                metadata={"version": "1.0", "maintainer": "system"}
            ),
            
            "source_code": PatternGroup(
                id="system_source_code",
                name="Source Code",
                description="Common programming language source files",
                patterns=[
                    PatternRule("*.py", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.java", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.cpp", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.c", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.h", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.js", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.ts", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
                    PatternRule("*.html", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.css", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.xml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.json", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.yaml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.yml", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                category=PatternCategory.SOURCE_CODE,
                is_system_group=True,
                created_at=datetime.utcnow(),
                usage_count=0,
                metadata={"version": "1.0", "maintainer": "system"}
            )
        }

    def _load_custom_groups(self) -> None:
        """Load custom pattern groups from configuration file"""
        if not self.config_path.exists():
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            for group_data in data.get("pattern_groups", []):
                group = self._deserialize_pattern_group(group_data)
                self.custom_groups[group.id] = group
        except Exception as e:
            raise RuntimeError(f"Failed to load custom pattern groups: {e}") from e
    
    def _save_custom_groups(self) -> None:
        """Save custom pattern groups to configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "pattern_groups": [
                self._serialize_pattern_group(group)
                for group in self.custom_groups.values()
            ]
        }
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save custom pattern groups: {e}") from e
    
    def _serialize_pattern_group(self, group: PatternGroup) -> Dict:
        """Serialize a pattern group to dictionary"""
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "patterns": [
                {
                    "pattern": p.pattern,
                    "syntax": p.syntax.value,
                    "case_sensitive": p.case_sensitive,
                    "applies_to": p.applies_to.value,
                    "priority": p.priority,
                    "metadata": p.metadata
                }
                for p in group.patterns
            ],
            "category": group.category.value,
            "is_system_group": group.is_system_group,
            "created_at": group.created_at.isoformat(),
            "usage_count": group.usage_count,
            "metadata": group.metadata
        }
    
    def _deserialize_pattern_group(self, data: Dict) -> PatternGroup:
        """Deserialize a pattern group from dictionary"""
        patterns = [
            PatternRule(
                pattern=p["pattern"],
                syntax=PatternSyntax(p["syntax"]),
                case_sensitive=p.get("case_sensitive", False),
                applies_to=PathComponent(p.get("applies_to", "full_path")),
                priority=p.get("priority", 100),
                metadata=p.get("metadata", {})
            )
            for p in data["patterns"]
        ]
        
        return PatternGroup(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            patterns=patterns,
            category=PatternCategory(data.get("category", "custom")),
            is_system_group=data.get("is_system_group", False),
            created_at=datetime.fromisoformat(data["created_at"]),
            usage_count=data.get("usage_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def create_pattern_group(self, group: PatternGroup) -> str:
        """
        Create a new custom pattern group.
        
        Args:
            group: The pattern group to create
            
        Returns:
            The ID of the created pattern group
            
        Raises:
            ValueError: If a group with the same ID already exists
        """
        if group.id in self.custom_groups or group.id in self.SYSTEM_GROUPS:
            raise ValueError(f"Pattern group with ID '{group.id}' already exists")
        
        if group.is_system_group:
            raise ValueError("Cannot create system pattern groups through this method")
        
        self.custom_groups[group.id] = group
        self._save_custom_groups()
        return group.id
    
    def get_pattern_group(self, group_id: str) -> PatternGroup:
        """
        Get a pattern group by ID.
        
        Args:
            group_id: The ID of the pattern group
            
        Returns:
            The pattern group
            
        Raises:
            PatternGroupNotFoundError: If the group is not found
        """
        # Check system groups first
        if group_id in self.SYSTEM_GROUPS:
            return self.SYSTEM_GROUPS[group_id]
        
        # Check custom groups
        if group_id in self.custom_groups:
            return self.custom_groups[group_id]
        
        raise PatternGroupNotFoundError(f"Pattern group '{group_id}' not found")
    
    def get_pattern_group_by_name(self, name: str) -> PatternGroup:
        """
        Get a pattern group by name.
        
        Args:
            name: The name of the pattern group
            
        Returns:
            The pattern group
            
        Raises:
            PatternGroupNotFoundError: If the group is not found
        """
        # Check system groups
        for group in self.SYSTEM_GROUPS.values():
            if group.name.lower() == name.lower():
                return group
        
        # Check custom groups
        for group in self.custom_groups.values():
            if group.name.lower() == name.lower():
                return group
        
        raise PatternGroupNotFoundError(f"Pattern group with name '{name}' not found")
    
    def list_pattern_groups(
        self,
        category: Optional[PatternCategory] = None,
        include_system: bool = True,
        include_custom: bool = True
    ) -> List[PatternGroup]:
        """
        List pattern groups with optional filtering.
        
        Args:
            category: Filter by category (None for all)
            include_system: Include system groups
            include_custom: Include custom groups
            
        Returns:
            List of pattern groups matching the criteria
        """
        groups = []
        
        if include_system:
            groups.extend(self.SYSTEM_GROUPS.values())
        
        if include_custom:
            groups.extend(self.custom_groups.values())
        
        if category:
            groups = [g for g in groups if g.category == category]
        
        return sorted(groups, key=lambda g: (not g.is_system_group, g.name))
    
    def update_pattern_group(self, group_id: str, updates: Dict) -> PatternGroup:
        """
        Update a custom pattern group.
        
        Args:
            group_id: The ID of the pattern group to update
            updates: Dictionary of fields to update
            
        Returns:
            The updated pattern group
            
        Raises:
            PatternGroupNotFoundError: If the group is not found
            ValueError: If attempting to update a system group
        """
        if group_id in self.SYSTEM_GROUPS:
            raise ValueError("Cannot update system pattern groups")
        
        if group_id not in self.custom_groups:
            raise PatternGroupNotFoundError(f"Pattern group '{group_id}' not found")
        
        group = self.custom_groups[group_id]
        
        # Update allowed fields
        if "name" in updates:
            group.name = updates["name"]
        if "description" in updates:
            group.description = updates["description"]
        if "patterns" in updates:
            group.patterns = updates["patterns"]
        if "category" in updates:
            group.category = updates["category"]
        if "metadata" in updates:
            group.metadata.update(updates["metadata"])
        
        self._save_custom_groups()
        return group
    
    def delete_pattern_group(self, group_id: str) -> bool:
        """
        Delete a custom pattern group.
        
        Args:
            group_id: The ID of the pattern group to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            PatternGroupNotFoundError: If the group is not found
            ValueError: If attempting to delete a system group
        """
        if group_id in self.SYSTEM_GROUPS:
            raise ValueError("Cannot delete system pattern groups")
        
        if group_id not in self.custom_groups:
            raise PatternGroupNotFoundError(f"Pattern group '{group_id}' not found")
        
        del self.custom_groups[group_id]
        self._save_custom_groups()
        return True
    
    def expand_pattern_groups(self, group_names: List[str]) -> List[PatternRule]:
        """
        Expand pattern group names to their constituent patterns.
        
        Args:
            group_names: List of pattern group names or IDs
            
        Returns:
            List of all patterns from the specified groups
            
        Raises:
            PatternGroupNotFoundError: If any group is not found
        """
        all_patterns = []
        
        for group_name in group_names:
            try:
                # Try as ID first
                group = self.get_pattern_group(group_name)
            except PatternGroupNotFoundError:
                # Try as name
                group = self.get_pattern_group_by_name(group_name)
            
            # Increment usage count
            group.usage_count += 1
            if not group.is_system_group:
                self._save_custom_groups()
            
            all_patterns.extend(group.patterns)
        
        return all_patterns
    
    def duplicate_pattern_group(self, group_id: str, new_name: str, new_id: Optional[str] = None) -> PatternGroup:
        """
        Duplicate a pattern group (system or custom).
        
        Args:
            group_id: The ID of the pattern group to duplicate
            new_name: Name for the new group
            new_id: ID for the new group (auto-generated if None)
            
        Returns:
            The newly created pattern group
            
        Raises:
            PatternGroupNotFoundError: If the source group is not found
        """
        source_group = self.get_pattern_group(group_id)
        
        if new_id is None:
            new_id = f"custom_{new_name.lower().replace(' ', '_')}"
        
        new_group = PatternGroup(
            id=new_id,
            name=new_name,
            description=f"Duplicated from {source_group.name}",
            patterns=source_group.patterns.copy(),
            category=source_group.category,
            is_system_group=False,
            created_at=datetime.utcnow(),
            usage_count=0,
            metadata={"duplicated_from": group_id}
        )
        
        self.create_pattern_group(new_group)
        return new_group
