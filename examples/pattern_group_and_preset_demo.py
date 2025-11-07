#!/usr/bin/env python3
"""
Demo script for Pattern Groups and Application Presets functionality.

This script demonstrates:
1. Pattern Group management (CRUD operations)
2. Application Preset management
3. Platform-specific configurations
4. Preset customization
"""

from pathlib import Path
from datetime import datetime

from TimeLocker.selection_models import (
    ApplicationCategory,
    ApplicationPreset,
    PatternCategory,
    PatternGroup,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution,
    SelectionConfig,
    SelectionTemplate
)
from TimeLocker.pattern_group_manager import PatternGroupManager
from TimeLocker.application_preset_manager import ApplicationPresetManager


def demo_pattern_groups():
    """Demonstrate pattern group management"""
    print("=" * 80)
    print("PATTERN GROUP MANAGEMENT DEMO")
    print("=" * 80)
    
    # Initialize manager
    manager = PatternGroupManager(config_path=Path("/tmp/test_pattern_groups.json"))
    
    # List system pattern groups
    print("\n1. System Pattern Groups:")
    print("-" * 80)
    system_groups = manager.list_pattern_groups(include_custom=False)
    for group in system_groups:
        print(f"  - {group.name} ({group.id})")
        print(f"    Category: {group.category.value}")
        print(f"    Patterns: {len(group.patterns)}")
        print(f"    Description: {group.description}")
        print()
    
    # Create a custom pattern group
    print("\n2. Creating Custom Pattern Group:")
    print("-" * 80)
    custom_group = PatternGroup(
        id="custom_python_project",
        name="Python Project Files",
        description="Essential files for Python projects",
        patterns=[
            PatternRule("*.py", PatternSyntax.GLOB, True, PathComponent.FILENAME, 100),
            PatternRule("requirements.txt", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
            PatternRule("setup.py", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
            PatternRule("pyproject.toml", PatternSyntax.LITERAL, True, PathComponent.FILENAME, 100),
            PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        category=PatternCategory.SOURCE_CODE,
        is_system_group=False,
        created_at=datetime.utcnow(),
        usage_count=0,
        metadata={"author": "demo_user"}
    )
    
    try:
        group_id = manager.create_pattern_group(custom_group)
        print(f"  Created custom pattern group: {group_id}")
        print(f"  Name: {custom_group.name}")
        print(f"  Patterns: {len(custom_group.patterns)}")
    except ValueError as e:
        print(f"  Error: {e}")
    
    # List all pattern groups
    print("\n3. All Pattern Groups (System + Custom):")
    print("-" * 80)
    all_groups = manager.list_pattern_groups()
    for group in all_groups:
        group_type = "System" if group.is_system_group else "Custom"
        print(f"  - [{group_type}] {group.name} ({group.id})")
    
    # Expand pattern groups
    print("\n4. Expanding Pattern Groups:")
    print("-" * 80)
    try:
        patterns = manager.expand_pattern_groups(["office_documents", "temporary_files"])
        print(f"  Expanded 2 groups into {len(patterns)} patterns:")
        for i, pattern in enumerate(patterns[:5], 1):
            print(f"    {i}. {pattern.pattern} ({pattern.syntax.value})")
        if len(patterns) > 5:
            print(f"    ... and {len(patterns) - 5} more")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Update custom group
    print("\n5. Updating Custom Pattern Group:")
    print("-" * 80)
    try:
        updated_group = manager.update_pattern_group(
            "custom_python_project",
            {
                "description": "Updated: Essential files for Python projects with tests",
                "metadata": {"author": "demo_user", "version": "1.1"}
            }
        )
        print(f"  Updated group: {updated_group.name}")
        print(f"  New description: {updated_group.description}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Duplicate a system group
    print("\n6. Duplicating System Pattern Group:")
    print("-" * 80)
    try:
        duplicated = manager.duplicate_pattern_group(
            "source_code",
            "My Source Code",
            "custom_my_source_code"
        )
        print(f"  Duplicated 'source_code' to '{duplicated.name}'")
        print(f"  New ID: {duplicated.id}")
        print(f"  Patterns: {len(duplicated.patterns)}")
    except Exception as e:
        print(f"  Error: {e}")


def demo_application_presets():
    """Demonstrate application preset management"""
    print("\n" + "=" * 80)
    print("APPLICATION PRESET MANAGEMENT DEMO")
    print("=" * 80)
    
    # Initialize manager
    manager = ApplicationPresetManager(config_path=Path("/tmp/test_app_presets.json"))
    
    # List system presets
    print("\n1. System Application Presets:")
    print("-" * 80)
    system_presets = manager.list_application_presets(include_custom=False)
    for preset in system_presets:
        print(f"  - {preset.name} ({preset.id})")
        print(f"    Application: {preset.application_name}")
        print(f"    Category: {preset.category.value}")
        print(f"    Description: {preset.description}")
        print(f"    Versions: {', '.join(preset.version_compatibility)}")
        print()
    
    # Get a specific preset
    print("\n2. PostgreSQL Preset Details:")
    print("-" * 80)
    try:
        pg_preset = manager.get_application_preset("preset_postgresql")
        print(f"  Name: {pg_preset.name}")
        print(f"  Application: {pg_preset.application_name}")
        print(f"  Include Paths:")
        for path in pg_preset.selection_template.selection_config.include_paths:
            print(f"    - {path}")
        print(f"  Exclude Paths:")
        for path in pg_preset.selection_template.selection_config.exclude_paths:
            print(f"    - {path}")
        print(f"  Pattern Groups: {', '.join(pg_preset.selection_template.selection_config.pattern_groups)}")
        print(f"  Platform-specific configs: {len(pg_preset.platform_specific)}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Get platform-specific configuration
    print("\n3. Platform-Specific Configuration:")
    print("-" * 80)
    try:
        # Get config for current platform
        config = manager.get_platform_specific_config("preset_postgresql")
        print(f"  Current platform configuration:")
        print(f"  Include paths: {len(config.include_paths)}")
        print(f"  Exclude paths: {len(config.exclude_paths)}")
        print(f"  Case sensitive: {config.case_sensitive}")
        
        # Get Windows-specific config
        windows_config = manager.get_platform_specific_config("preset_postgresql", "windows")
        print(f"\n  Windows-specific configuration:")
        print(f"  Include paths: {len(windows_config.include_paths)}")
        for path in windows_config.include_paths:
            print(f"    - {path}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Customize a preset
    print("\n4. Customizing Application Preset:")
    print("-" * 80)
    try:
        custom_preset = manager.customize_preset(
            "preset_web_dev",
            "My Web Project",
            {
                "description": "Custom web development preset with additional patterns",
                "include_patterns": [
                    PatternRule("*.vue", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.scss", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                "exclude_patterns": [
                    PatternRule(".vscode/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                ],
                "pattern_groups": ["office_documents"],
                "created_by": "demo_user"
            }
        )
        print(f"  Created custom preset: {custom_preset.name}")
        print(f"  ID: {custom_preset.id}")
        print(f"  Based on: {custom_preset.metadata.get('customized_from')}")
        print(f"  Include patterns: {len(custom_preset.selection_template.selection_config.include_patterns)}")
        print(f"  Exclude patterns: {len(custom_preset.selection_template.selection_config.exclude_patterns)}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Create a completely custom preset
    print("\n5. Creating Custom Application Preset:")
    print("-" * 80)
    custom_app_preset = ApplicationPreset(
        id="custom_nodejs_app",
        name="Node.js Application",
        description="Custom preset for Node.js applications",
        application_name="Node.js",
        selection_template=SelectionTemplate(
            id="template_nodejs_custom",
            name="Node.js Custom Backup",
            description="Node.js application backup excluding dependencies",
            selection_config=SelectionConfig(
                include_paths=[Path(".")],
                exclude_paths=[],
                include_patterns=[
                    PatternRule("*.js", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.json", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                    PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                exclude_patterns=[
                    PatternRule("node_modules/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
                    PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
                ],
                pattern_groups=["temporary_files"],
                precedence_config=PrecedenceConfig(
                    default_strategy=PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                    conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                ),
                case_sensitive=True,
                performance_hints={}
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=["nodejs", "javascript", "development"],
            is_system_template=False,
            metadata={"author": "demo_user"}
        ),
        category=ApplicationCategory.DEVELOPMENT,
        platform_specific={},
        version_compatibility=["14.x", "16.x", "18.x", "20.x"],
        installation_paths=[],
        is_system_preset=False,
        metadata={"author": "demo_user"}
    )
    
    try:
        preset_id = manager.create_application_preset(custom_app_preset)
        print(f"  Created custom application preset: {preset_id}")
        print(f"  Name: {custom_app_preset.name}")
        print(f"  Application: {custom_app_preset.application_name}")
        print(f"  Category: {custom_app_preset.category.value}")
    except ValueError as e:
        print(f"  Error: {e}")
    
    # List all presets
    print("\n6. All Application Presets (System + Custom):")
    print("-" * 80)
    all_presets = manager.list_application_presets()
    for preset in all_presets:
        preset_type = "System" if preset.is_system_preset else "Custom"
        print(f"  - [{preset_type}] {preset.name} ({preset.application_name})")


def demo_integration():
    """Demonstrate integration between pattern groups and presets"""
    print("\n" + "=" * 80)
    print("INTEGRATION DEMO")
    print("=" * 80)
    
    pattern_manager = PatternGroupManager(config_path=Path("/tmp/test_pattern_groups.json"))
    preset_manager = ApplicationPresetManager(config_path=Path("/tmp/test_app_presets.json"))
    
    print("\n1. Using Pattern Groups in Application Presets:")
    print("-" * 80)
    
    # Get a preset
    try:
        preset = preset_manager.get_application_preset("preset_web_dev")
        print(f"  Preset: {preset.name}")
        print(f"  Pattern groups used: {preset.selection_template.selection_config.pattern_groups}")
        
        # Expand the pattern groups
        if preset.selection_template.selection_config.pattern_groups:
            expanded_patterns = pattern_manager.expand_pattern_groups(
                preset.selection_template.selection_config.pattern_groups
            )
            print(f"  Expanded to {len(expanded_patterns)} patterns")
            print(f"  Sample patterns:")
            for pattern in expanded_patterns[:5]:
                print(f"    - {pattern.pattern} ({pattern.syntax.value})")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n2. Complete Selection Configuration:")
    print("-" * 80)
    try:
        preset = preset_manager.get_application_preset("preset_postgresql")
        config = preset.selection_template.selection_config
        
        print(f"  Preset: {preset.name}")
        print(f"  Direct include patterns: {len(config.include_patterns)}")
        print(f"  Direct exclude patterns: {len(config.exclude_patterns)}")
        print(f"  Pattern groups: {len(config.pattern_groups)}")
        
        # Expand pattern groups
        if config.pattern_groups:
            group_patterns = pattern_manager.expand_pattern_groups(config.pattern_groups)
            print(f"  Patterns from groups: {len(group_patterns)}")
            print(f"  Total patterns: {len(config.include_patterns) + len(config.exclude_patterns) + len(group_patterns)}")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "Pattern Groups and Application Presets Demo" + " " * 20 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        demo_pattern_groups()
        demo_application_presets()
        demo_integration()
        
        print("\n" + "=" * 80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNote: Demo data was saved to /tmp/test_*.json files")
        print("These files can be safely deleted after reviewing the demo.")
        
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
