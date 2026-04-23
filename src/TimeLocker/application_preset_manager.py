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
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from TimeLocker.selection_models import (
    ApplicationCategory,
    ApplicationPreset,
    ConflictResolution,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    SelectionConfig,
    SelectionTemplate
)


class ApplicationPresetNotFoundError(Exception):
    """Raised when an application preset is not found"""
    pass


class ApplicationPresetManager:
    """
    Manages application presets with CRUD operations and persistence.
    
    Provides functionality to create, read, update, and delete application presets,
    including both system-provided and custom presets. Supports platform-specific
    configurations and preset customization.
    """

    # System-provided application presets
    SYSTEM_PRESETS: Dict[str, ApplicationPreset] = {}

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the application preset manager.
        
        Args:
            config_path: Path to configuration file for custom presets.
                        If None, uses default location.
        """
        self.config_path = config_path or Path.home() / ".timelocker" / "application_presets.json"
        self.custom_presets: Dict[str, ApplicationPreset] = {}
        self._initialize_system_presets()
        self._load_custom_presets()

    def _initialize_system_presets(self) -> None:
        """Initialize system-provided application presets"""
        presets = [
                self._create_postgresql_preset(),
                self._create_web_development_preset(),
                self._create_mysql_preset(),
                self._create_docker_preset(),
        ]
        type(self).SYSTEM_PRESETS = {preset.id: preset for preset in presets}

    def _create_postgresql_preset(self) -> ApplicationPreset:
        """Create PostgreSQL database preset"""
        return ApplicationPreset(
                id="preset_postgresql",
                name="PostgreSQL Database",
                description="PostgreSQL data directory and configuration files",
                application_name="PostgreSQL",
                selection_template=SelectionTemplate(
                        id="template_postgresql",
                        name="PostgreSQL Backup",
                        description="Complete PostgreSQL installation backup",
                        selection_config=SelectionConfig(
                                include_paths=[
                                        Path("/var/lib/postgresql"),
                                        Path("/etc/postgresql"),
                                ],
                                exclude_paths=[
                                        Path("/var/lib/postgresql/*/main/pg_log"),
                                ],
                                include_patterns=[
                                        PatternRule("*.conf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                exclude_patterns=[
                                        PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("postmaster.pid", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
                                ],
                                pattern_groups=["temporary_files"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=True,
                                performance_hints={"skip_large_logs": True}
                        ),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        tags=["database", "postgresql", "system"],
                        is_system_template=True,
                        metadata={"preset_id": "preset_postgresql"}
                ),
                category=ApplicationCategory.DATABASE,
                platform_specific={
                        "windows": SelectionConfig(
                                include_paths=[Path("C:/Program Files/PostgreSQL")],
                                exclude_paths=[],
                                include_patterns=[],
                                exclude_patterns=[],
                                pattern_groups=["temporary_files"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=False,
                                performance_hints={}
                        )
                },
                version_compatibility=["9.x", "10.x", "11.x", "12.x", "13.x", "14.x", "15.x", "16.x"],
                installation_paths=[
                        "/var/lib/postgresql",
                        "/usr/lib/postgresql",
                        "C:/Program Files/PostgreSQL"
                ],
                is_system_preset=True,
                metadata={"maintainer": "system", "version": "1.0"}
        )

    def _create_web_development_preset(self) -> ApplicationPreset:
        """Create web development project preset"""
        return ApplicationPreset(
                id="preset_web_dev",
                name="Web Development Project",
                description="Typical web development project structure",
                application_name="Web Development",
                selection_template=SelectionTemplate(
                        id="template_web_dev",
                        name="Web Development Backup",
                        description="Web development project with dependencies excluded",
                        selection_config=SelectionConfig(
                                include_paths=[Path(".")],
                                exclude_paths=[],
                                include_patterns=[
                                        PatternRule("*.html", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.css", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.js", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.ts", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.json", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                exclude_patterns=[
                                        PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                                        PatternRule("dist/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                                        PatternRule("build/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                                        PatternRule(".git/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                                        PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                pattern_groups=["temporary_files", "source_code"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=True,
                                performance_hints={"skip_node_modules": True}
                        ),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        tags=["development", "web", "javascript", "typescript"],
                        is_system_template=True,
                        metadata={"preset_id": "preset_web_dev"}
                ),
                category=ApplicationCategory.DEVELOPMENT,
                platform_specific={},
                version_compatibility=["*"],
                installation_paths=[],
                is_system_preset=True,
                metadata={"maintainer": "system", "version": "1.0"}
        )

    def _create_mysql_preset(self) -> ApplicationPreset:
        """Create MySQL database preset"""
        return ApplicationPreset(
                id="preset_mysql",
                name="MySQL Database",
                description="MySQL data directory and configuration files",
                application_name="MySQL",
                selection_template=SelectionTemplate(
                        id="template_mysql",
                        name="MySQL Backup",
                        description="Complete MySQL installation backup",
                        selection_config=SelectionConfig(
                                include_paths=[
                                        Path("/var/lib/mysql"),
                                        Path("/etc/mysql"),
                                ],
                                exclude_paths=[],
                                include_patterns=[
                                        PatternRule("*.cnf", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.sql", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                exclude_patterns=[
                                        PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.pid", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                        PatternRule("*.sock", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                pattern_groups=["temporary_files"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=True,
                                performance_hints={"skip_large_logs": True}
                        ),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        tags=["database", "mysql", "system"],
                        is_system_template=True,
                        metadata={"preset_id": "preset_mysql"}
                ),
                category=ApplicationCategory.DATABASE,
                platform_specific={
                        "windows": SelectionConfig(
                                include_paths=[Path("C:/ProgramData/MySQL")],
                                exclude_paths=[],
                                include_patterns=[],
                                exclude_patterns=[],
                                pattern_groups=["temporary_files"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=False,
                                performance_hints={}
                        )
                },
                version_compatibility=["5.x", "8.x"],
                installation_paths=[
                        "/var/lib/mysql",
                        "/usr/lib/mysql",
                        "C:/ProgramData/MySQL"
                ],
                is_system_preset=True,
                metadata={"maintainer": "system", "version": "1.0"}
        )

    def _create_docker_preset(self) -> ApplicationPreset:
        """Create Docker data preset"""
        return ApplicationPreset(
                id="preset_docker",
                name="Docker Data",
                description="Docker volumes and configuration",
                application_name="Docker",
                selection_template=SelectionTemplate(
                        id="template_docker",
                        name="Docker Backup",
                        description="Docker volumes and configuration backup",
                        selection_config=SelectionConfig(
                                include_paths=[
                                        Path("/var/lib/docker/volumes"),
                                ],
                                exclude_paths=[
                                        Path("/var/lib/docker/overlay2"),
                                        Path("/var/lib/docker/tmp"),
                                ],
                                include_patterns=[],
                                exclude_patterns=[
                                        PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                                ],
                                pattern_groups=["temporary_files"],
                                precedence_config=PrecedenceConfig(
                                        default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                                ),
                                case_sensitive=True,
                                performance_hints={"skip_overlay": True}
                        ),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        tags=["container", "docker", "system"],
                        is_system_template=True,
                        metadata={"preset_id": "preset_docker"}
                ),
                category=ApplicationCategory.SYSTEM_ADMIN,
                platform_specific={},
                version_compatibility=["*"],
                installation_paths=[
                        "/var/lib/docker",
                ],
                is_system_preset=True,
                metadata={"maintainer": "system", "version": "1.0"}
        )

    def _load_custom_presets(self) -> None:
        """Load custom application presets from configuration file"""
        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            for preset_data in data.get("application_presets", []):
                preset = self._deserialize_application_preset(preset_data)
                self.custom_presets[preset.id] = preset
        except Exception as e:
            raise RuntimeError(f"Failed to load custom application presets: {e}") from e

    def _save_custom_presets(self) -> None:
        """Save custom application presets to configuration file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
                "application_presets": [
                        self._serialize_application_preset(preset)
                        for preset in self.custom_presets.values()
                ]
        }

        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save custom application presets: {e}") from e

    def _serialize_selection_config(self, config: SelectionConfig) -> Dict:
        """Serialize a selection config to dictionary"""
        return {
                "include_paths":     [str(p) for p in config.include_paths],
                "exclude_paths":     [str(p) for p in config.exclude_paths],
                "include_patterns":  [
                        {
                                "pattern":        p.pattern,
                                "syntax":         p.syntax.value,
                                "case_sensitive": p.case_sensitive,
                                "applies_to":     p.applies_to.value,
                                "priority":       p.priority,
                                "metadata":       p.metadata
                        }
                        for p in config.include_patterns
                ],
                "exclude_patterns":  [
                        {
                                "pattern":        p.pattern,
                                "syntax":         p.syntax.value,
                                "case_sensitive": p.case_sensitive,
                                "applies_to":     p.applies_to.value,
                                "priority":       p.priority,
                                "metadata":       p.metadata
                        }
                        for p in config.exclude_patterns
                ],
                "pattern_groups":    config.pattern_groups,
                "precedence_config": {
                        "default_strategy":         config.precedence_config.default_strategy.value,
                        "path_specific_rules":      {
                                k: v.value for k, v in config.precedence_config.path_specific_rules.items()
                        },
                        "specificity_weight":       config.precedence_config.specificity_weight,
                        "explicit_override_weight": config.precedence_config.explicit_override_weight,
                        "pattern_type_priority":    {
                                k.value: v for k, v in config.precedence_config.pattern_type_priority.items()
                        },
                        "conflict_resolution":      config.precedence_config.conflict_resolution.value
                },
                "case_sensitive":    config.case_sensitive,
                "performance_hints": config.performance_hints
        }

    def _deserialize_selection_config(self, data: Dict) -> SelectionConfig:
        """Deserialize a selection config from dictionary"""
        include_patterns = [
                PatternRule(
                        pattern=p["pattern"],
                        syntax=PatternSyntax(p["syntax"]),
                        case_sensitive=p.get("case_sensitive", False),
                        applies_to=PathComponent(p.get("applies_to", "full_path")),
                        priority=p.get("priority", 100),
                        metadata=p.get("metadata", {})
                )
                for p in data.get("include_patterns", [])
        ]

        exclude_patterns = [
                PatternRule(
                        pattern=p["pattern"],
                        syntax=PatternSyntax(p["syntax"]),
                        case_sensitive=p.get("case_sensitive", False),
                        applies_to=PathComponent(p.get("applies_to", "full_path")),
                        priority=p.get("priority", 100),
                        metadata=p.get("metadata", {})
                )
                for p in data.get("exclude_patterns", [])
        ]

        prec_config_data = data.get("precedence_config", {})
        precedence_config = PrecedenceConfig(
                default_strategy=PrecedenceStrategy(prec_config_data.get("default_strategy", "exclude_first")),
                path_specific_rules={
                        k: PrecedenceStrategy(v) for k, v in prec_config_data.get("path_specific_rules", {}).items()
                },
                specificity_weight=prec_config_data.get("specificity_weight", 1.0),
                explicit_override_weight=prec_config_data.get("explicit_override_weight", 1.0),
                pattern_type_priority={
                        PatternSyntax(k): v for k, v in prec_config_data.get("pattern_type_priority", {}).items()
                } if prec_config_data.get("pattern_type_priority") else {},
                conflict_resolution=ConflictResolution(prec_config_data.get("conflict_resolution", "warn"))
        )

        return SelectionConfig(
                include_paths=[Path(p) for p in data.get("include_paths", [])],
                exclude_paths=[Path(p) for p in data.get("exclude_paths", [])],
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                pattern_groups=data.get("pattern_groups", []),
                precedence_config=precedence_config,
                case_sensitive=data.get("case_sensitive", False),
                performance_hints=data.get("performance_hints", {})
        )

    def _serialize_application_preset(self, preset: ApplicationPreset) -> Dict:
        """Serialize an application preset to dictionary"""
        return {
                "id":                    preset.id,
                "name":                  preset.name,
                "description":           preset.description,
                "application_name":      preset.application_name,
                "selection_template":    {
                        "id":                 preset.selection_template.id,
                        "name":               preset.selection_template.name,
                        "description":        preset.selection_template.description,
                        "selection_config":   self._serialize_selection_config(preset.selection_template.selection_config),
                        "created_at":         preset.selection_template.created_at.isoformat(),
                        "updated_at":         preset.selection_template.updated_at.isoformat(),
                        "created_by":         preset.selection_template.created_by,
                        "tags":               preset.selection_template.tags,
                        "usage_count":        preset.selection_template.usage_count,
                        "is_system_template": preset.selection_template.is_system_template,
                        "metadata":           preset.selection_template.metadata
                },
                "category":              preset.category.value,
                "platform_specific":     {
                        platform: self._serialize_selection_config(config)
                        for platform, config in preset.platform_specific.items()
                },
                "version_compatibility": preset.version_compatibility,
                "installation_paths":    preset.installation_paths,
                "is_system_preset":      preset.is_system_preset,
                "metadata":              preset.metadata
        }

    def _deserialize_application_preset(self, data: Dict) -> ApplicationPreset:
        """Deserialize an application preset from dictionary"""
        template_data = data["selection_template"]
        selection_template = SelectionTemplate(
                id=template_data["id"],
                name=template_data["name"],
                description=template_data.get("description"),
                selection_config=self._deserialize_selection_config(template_data["selection_config"]),
                created_at=datetime.fromisoformat(template_data["created_at"]),
                updated_at=datetime.fromisoformat(template_data["updated_at"]),
                created_by=template_data.get("created_by"),
                tags=template_data.get("tags", []),
                usage_count=template_data.get("usage_count", 0),
                is_system_template=template_data.get("is_system_template", False),
                metadata=template_data.get("metadata", {})
        )

        platform_specific = {
                platform: self._deserialize_selection_config(config_data)
                for platform, config_data in data.get("platform_specific", {}).items()
        }

        return ApplicationPreset(
                id=data["id"],
                name=data["name"],
                description=data["description"],
                application_name=data["application_name"],
                selection_template=selection_template,
                category=ApplicationCategory(data.get("category", "custom")),
                platform_specific=platform_specific,
                version_compatibility=data.get("version_compatibility", []),
                installation_paths=data.get("installation_paths", []),
                is_system_preset=data.get("is_system_preset", False),
                metadata=data.get("metadata", {})
        )

    def create_application_preset(self, preset: ApplicationPreset) -> str:
        """
        Create a new custom application preset.
        
        Args:
            preset: The application preset to create
            
        Returns:
            The ID of the created preset
            
        Raises:
            ValueError: If a preset with the same ID already exists
        """
        if preset.id in self.custom_presets or preset.id in self.SYSTEM_PRESETS:
            raise ValueError(f"Application preset with ID '{preset.id}' already exists")

        if preset.is_system_preset:
            raise ValueError("Cannot create system presets through this method")

        self.custom_presets[preset.id] = preset
        self._save_custom_presets()
        return preset.id

    def get_application_preset(self, preset_id: str) -> ApplicationPreset:
        """
        Get an application preset by ID.
        
        Args:
            preset_id: The ID of the preset
            
        Returns:
            The application preset
            
        Raises:
            ApplicationPresetNotFoundError: If the preset is not found
        """
        # Check system presets first
        if preset_id in self.SYSTEM_PRESETS:
            return self.SYSTEM_PRESETS[preset_id]

        # Check custom presets
        if preset_id in self.custom_presets:
            return self.custom_presets[preset_id]

        raise ApplicationPresetNotFoundError(f"Application preset '{preset_id}' not found")

    def get_application_preset_by_name(self, name: str) -> ApplicationPreset:
        """
        Get an application preset by name.
        
        Args:
            name: The name of the preset
            
        Returns:
            The application preset
            
        Raises:
            ApplicationPresetNotFoundError: If the preset is not found
        """
        # Check system presets
        for preset in self.SYSTEM_PRESETS.values():
            if preset.name.lower() == name.lower():
                return preset

        # Check custom presets
        for preset in self.custom_presets.values():
            if preset.name.lower() == name.lower():
                return preset

        raise ApplicationPresetNotFoundError(f"Application preset with name '{name}' not found")

    def list_application_presets(
            self,
            category: Optional[ApplicationCategory] = None,
            include_system: bool = True,
            include_custom: bool = True
    ) -> List[ApplicationPreset]:
        """
        List application presets with optional filtering.
        
        Args:
            category: Filter by category (None for all)
            include_system: Include system presets
            include_custom: Include custom presets
            
        Returns:
            List of application presets matching the criteria
        """
        presets = []

        if include_system:
            presets.extend(self.SYSTEM_PRESETS.values())

        if include_custom:
            presets.extend(self.custom_presets.values())

        if category:
            presets = [p for p in presets if p.category == category]

        return sorted(presets, key=lambda p: (not p.is_system_preset, p.name))

    def update_application_preset(self, preset_id: str, updates: Dict) -> ApplicationPreset:
        """
        Update a custom application preset.
        
        Args:
            preset_id: The ID of the preset to update
            updates: Dictionary of fields to update
            
        Returns:
            The updated preset
            
        Raises:
            ApplicationPresetNotFoundError: If the preset is not found
            ValueError: If attempting to update a system preset
        """
        if preset_id in self.SYSTEM_PRESETS:
            raise ValueError("Cannot update system application presets")

        if preset_id not in self.custom_presets:
            raise ApplicationPresetNotFoundError(f"Application preset '{preset_id}' not found")

        preset = self.custom_presets[preset_id]

        # Update allowed fields
        if "name" in updates:
            preset.name = updates["name"]
        if "description" in updates:
            preset.description = updates["description"]
        if "application_name" in updates:
            preset.application_name = updates["application_name"]
        if "category" in updates:
            preset.category = updates["category"]
        if "version_compatibility" in updates:
            preset.version_compatibility = updates["version_compatibility"]
        if "installation_paths" in updates:
            preset.installation_paths = updates["installation_paths"]
        if "metadata" in updates:
            preset.metadata.update(updates["metadata"])

        self._save_custom_presets()
        return preset

    def delete_application_preset(self, preset_id: str) -> bool:
        """
        Delete a custom application preset.
        
        Args:
            preset_id: The ID of the preset to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            ApplicationPresetNotFoundError: If the preset is not found
            ValueError: If attempting to delete a system preset
        """
        if preset_id in self.SYSTEM_PRESETS:
            raise ValueError("Cannot delete system application presets")

        if preset_id not in self.custom_presets:
            raise ApplicationPresetNotFoundError(f"Application preset '{preset_id}' not found")

        del self.custom_presets[preset_id]
        self._save_custom_presets()
        return True

    def get_platform_specific_config(self, preset_id: str, platform_name: Optional[str] = None) -> SelectionConfig:
        """
        Get platform-specific configuration for a preset.
        
        Args:
            preset_id: The ID of the preset
            platform_name: Platform name (defaults to current platform)
            
        Returns:
            Platform-specific selection config, or default if not available
            
        Raises:
            ApplicationPresetNotFoundError: If the preset is not found
        """
        preset = self.get_application_preset(preset_id)

        if platform_name is None:
            platform_name = platform.system().lower()

        # Return platform-specific config if available
        if platform_name in preset.platform_specific:
            return preset.platform_specific[platform_name]

        # Return default config
        return preset.selection_template.selection_config

    def customize_preset(
            self,
            preset_id: str,
            custom_name: str,
            modifications: Dict,
            custom_id: Optional[str] = None
    ) -> ApplicationPreset:
        """
        Create a customized version of an existing preset.
        
        Args:
            preset_id: The ID of the preset to customize
            custom_name: Name for the customized preset
            modifications: Dictionary of modifications to apply
            custom_id: ID for the new preset (auto-generated if None)
            
        Returns:
            The newly created customized preset
            
        Raises:
            ApplicationPresetNotFoundError: If the source preset is not found
        """
        source_preset = self.get_application_preset(preset_id)

        if custom_id is None:
            custom_id = f"custom_{custom_name.lower().replace(' ', '_')}"

        # Create a copy of the selection template
        new_template = SelectionTemplate(
                id=f"{custom_id}_template",
                name=f"{custom_name} Template",
                description=f"Customized from {source_preset.name}",
                selection_config=source_preset.selection_template.selection_config,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=modifications.get("created_by"),
                tags=source_preset.selection_template.tags.copy(),
                usage_count=0,
                is_system_template=False,
                metadata={"customized_from": preset_id}
        )

        # Apply modifications to the template's selection config
        if "include_paths" in modifications:
            new_template.selection_config.include_paths.extend(modifications["include_paths"])
        if "exclude_paths" in modifications:
            new_template.selection_config.exclude_paths.extend(modifications["exclude_paths"])
        if "include_patterns" in modifications:
            new_template.selection_config.include_patterns.extend(modifications["include_patterns"])
        if "exclude_patterns" in modifications:
            new_template.selection_config.exclude_patterns.extend(modifications["exclude_patterns"])
        if "pattern_groups" in modifications:
            new_template.selection_config.pattern_groups.extend(modifications["pattern_groups"])

        new_preset = ApplicationPreset(
                id=custom_id,
                name=custom_name,
                description=modifications.get("description", f"Customized from {source_preset.name}"),
                application_name=source_preset.application_name,
                selection_template=new_template,
                category=modifications.get("category", source_preset.category),
                platform_specific=source_preset.platform_specific.copy(),
                version_compatibility=source_preset.version_compatibility.copy(),
                installation_paths=source_preset.installation_paths.copy(),
                is_system_preset=False,
                metadata={"customized_from": preset_id}
        )

        self.create_application_preset(new_preset)
        return new_preset
