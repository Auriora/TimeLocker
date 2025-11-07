# Pattern Groups and Application Presets Implementation

**Date**: 2025-11-07  
**Type**: Feature Implementation  
**Component**: Data Selection  
**Status**: Completed

## Overview

Implemented comprehensive pattern group and application preset management systems for the data selection feature. This provides reusable pattern collections and pre-configured application-specific backup templates.

## Changes Made

### 1. Enhanced Data Models

**File**: `src/TimeLocker/selection_models.py`

Added new data models:
- `PatternCategory`: Enum for categorizing pattern groups
- `PatternGroup`: Data class for named pattern collections
- `ApplicationCategory`: Enum for categorizing application presets
- `ApplicationPreset`: Data class for application-specific backup configurations

### 2. Pattern Group Manager

**File**: `src/TimeLocker/pattern_group_manager.py`

Implemented `PatternGroupManager` class with:
- **System Pattern Groups**: Pre-defined groups for common file types
  - Office Documents (10 patterns)
  - Temporary Files (11 patterns)
  - Media Files (16 patterns)
  - Source Code (14 patterns)
- **CRUD Operations**: Create, read, update, delete custom pattern groups
- **Persistence**: JSON-based storage for custom groups
- **Pattern Expansion**: Convert group names to constituent patterns
- **Duplication**: Clone system or custom groups for customization

### 3. Application Preset Manager

**File**: `src/TimeLocker/application_preset_manager.py`

Implemented `ApplicationPresetManager` class with:
- **System Presets**: Pre-configured templates for common applications
  - PostgreSQL Database
  - MySQL Database
  - Web Development Project
  - Docker Data
- **Platform-Specific Configurations**: OS-specific path and pattern configurations
- **CRUD Operations**: Create, read, update, delete custom presets
- **Preset Customization**: Create modified versions of existing presets
- **Persistence**: JSON-based storage for custom presets

### 4. Demo Script

**File**: `examples/pattern_group_and_preset_demo.py`

Comprehensive demonstration script showing:
- Pattern group management operations
- Application preset management operations
- Integration between pattern groups and presets
- Platform-specific configuration handling
- Preset customization workflows

## Features

### Pattern Groups

1. **System Groups**: Four pre-defined pattern groups covering common file types
2. **Custom Groups**: User-defined pattern collections with full CRUD support
3. **Categorization**: Groups organized by category (documents, media, temporary, source, etc.)
4. **Pattern Expansion**: Automatic expansion of group names to patterns during evaluation
5. **Usage Tracking**: Track how often groups are used
6. **Duplication**: Clone and customize existing groups

### Application Presets

1. **System Presets**: Four pre-configured application templates
2. **Custom Presets**: User-defined application-specific configurations
3. **Platform Support**: OS-specific configurations (Windows, Linux, macOS)
4. **Version Compatibility**: Track compatible application versions
5. **Customization**: Create modified versions of existing presets
6. **Template Integration**: Each preset includes a complete selection template

## Technical Details

### Pattern Group Structure

```python
PatternGroup(
    id="system_office_docs",
    name="Office Documents",
    description="Common office document formats",
    patterns=[...],  # List of PatternRule objects
    category=PatternCategory.DOCUMENT_TYPES,
    is_system_group=True,
    created_at=datetime,
    usage_count=0,
    metadata={}
)
```

### Application Preset Structure

```python
ApplicationPreset(
    id="preset_postgresql",
    name="PostgreSQL Database",
    description="PostgreSQL data directory and configuration files",
    application_name="PostgreSQL",
    selection_template=SelectionTemplate(...),
    category=ApplicationCategory.DATABASE,
    platform_specific={"windows": SelectionConfig(...)},
    version_compatibility=["9.x", "10.x", ...],
    installation_paths=[...],
    is_system_preset=True,
    metadata={}
)
```

## Requirements Satisfied

### Requirement 3: Pattern Groups
- ✅ 3.1: Predefined pattern groups for common file categories
- ✅ 3.2: Multiple group selection and combination with custom patterns
- ✅ 3.3: Custom pattern group creation
- ✅ 3.4: Custom group modification and removal
- ✅ 3.5: Pattern group expansion during evaluation

### Requirement 12: Application Presets
- ✅ 12.1: Predefined presets for common applications
- ✅ 12.2: Preset customization while maintaining base configuration
- ✅ 12.3: Custom application preset creation
- ✅ 12.4: Community preset library foundation (extensible design)
- ✅ 12.5: Preset documentation and usage guidance

## Usage Examples

### Pattern Groups

```python
from TimeLocker.pattern_group_manager import PatternGroupManager

manager = PatternGroupManager()

# List system groups
groups = manager.list_pattern_groups(include_custom=False)

# Create custom group
custom_group = PatternGroup(
    id="custom_python",
    name="Python Files",
    patterns=[...],
    category=PatternCategory.SOURCE_CODE
)
manager.create_pattern_group(custom_group)

# Expand groups to patterns
patterns = manager.expand_pattern_groups(["office_documents", "temporary_files"])
```

### Application Presets

```python
from TimeLocker.application_preset_manager import ApplicationPresetManager

manager = ApplicationPresetManager()

# Get preset
preset = manager.get_application_preset("preset_postgresql")

# Get platform-specific config
config = manager.get_platform_specific_config("preset_postgresql")

# Customize preset
custom = manager.customize_preset(
    "preset_web_dev",
    "My Web Project",
    {"include_patterns": [...]}
)
```

## Testing

Verified functionality through comprehensive demo script:
- ✅ Pattern group CRUD operations
- ✅ System and custom group management
- ✅ Pattern expansion
- ✅ Application preset CRUD operations
- ✅ Platform-specific configurations
- ✅ Preset customization
- ✅ Integration between groups and presets

## Configuration Storage

Custom data is persisted to:
- Pattern Groups: `~/.timelocker/pattern_groups.json`
- Application Presets: `~/.timelocker/application_presets.json`

## Next Steps

1. Integrate with SelectionManager for complete workflow
2. Add CLI commands for pattern group and preset management
3. Implement preset import/export functionality
4. Add community preset repository support
5. Create additional system presets for more applications

## Notes

- System groups and presets are read-only and cannot be modified
- Custom groups and presets can be freely created, modified, and deleted
- Pattern groups are automatically expanded during selection evaluation
- Platform-specific configurations override default configurations when available
- All operations include proper error handling and validation

## Related Files

- `src/TimeLocker/selection_models.py` - Data models
- `src/TimeLocker/pattern_group_manager.py` - Pattern group management
- `src/TimeLocker/application_preset_manager.py` - Application preset management
- `examples/pattern_group_and_preset_demo.py` - Demonstration script
- `.kiro/specs/data-selection/tasks.md` - Implementation tasks

## Task Status

- ✅ Task 5.1: Enhance PatternGroup system
- ✅ Task 5.2: Implement application presets
- ✅ Task 5: Create pattern groups and application presets
