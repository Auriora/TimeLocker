# Plugin Wrapper System Implementation

**Date**: 2025-11-07  
**Type**: Feature Implementation  
**Component**: Backup Operations  
**Status**: Completed

## Overview

Implemented a comprehensive plugin wrapper system for backup tools that provides standardized interfaces and capability gap filling for different backup engines. This system sits between the backup orchestration layer and actual backup tools, enabling consistent functionality across different tools.

## Implementation Details

### Core Components

#### 1. Base Plugin Wrapper (`plugin_wrapper.py`)

Created abstract base class `PluginWrapper` that defines the standard interface for all backup tool wrappers:

**Key Features:**
- Abstract methods for capability reporting (native vs wrapper-provided)
- Standardized backup execution interface
- Configuration validation
- Pattern translation for data selection rules
- Capability checking and comparison utilities

**Data Models:**
- `BackupConfig`: Standardized backup configuration
- `PluginWrapperError`: Base exception for wrapper errors
- `CapabilityNotSupportedError`: Exception for unsupported capabilities

#### 2. Restic Plugin Wrapper (`restic_plugin_wrapper.py`)

Implemented concrete wrapper for Restic backup tool:

**Native Capabilities:**
- Incremental and full backups
- Integrity verification and checksum validation
- Data deduplication
- Parallel processing
- Compression and bandwidth limiting
- Encryption (at rest and in transit)
- Include/exclude patterns
- Snapshot tagging and metadata
- Repository locking and verification
- Resume support and progress reporting
- Dry run mode

**Wrapper-Provided Capabilities:**
- Regex pattern translation to Restic glob patterns
- Multi-repository coordination

**Key Methods:**
- `execute_backup()`: Execute backup with standardized interface
- `validate_configuration()`: Validate backup configuration
- `translate_selection_rules()`: Translate patterns to Restic format
- `_translate_pattern()`: Convert regex to glob patterns
- `_detect_regex_patterns()`: Identify regex patterns

#### 3. Wrapper Registry (`wrapper_registry.py`)

Created registry system for managing plugin wrappers:

**Features:**
- Singleton pattern for global registry
- Wrapper registration and discovery
- Instance caching for performance
- Case-insensitive tool name lookup
- Capability-based wrapper search
- Wrapper comparison utilities

**Key Functions:**
- `get_wrapper_registry()`: Get global registry instance
- `initialize_wrappers()`: Register all built-in wrappers
- `register_wrapper()`: Register wrapper class
- `get_wrapper()`: Get wrapper instance
- `find_wrappers_with_capability()`: Find wrappers by feature
- `compare_wrappers()`: Compare wrapper capabilities

### Integration Points

#### Tool Manager Integration

The wrapper system integrates with the existing `ToolManager`:
- Uses `Feature` enum for capability definitions
- Leverages `ToolCapabilities` for capability reporting
- Coordinates with tool detection and configuration

#### Backup Orchestration Integration

Wrappers provide standardized interfaces for:
- Backup job execution
- Configuration validation
- Pattern translation
- Error handling and reporting

### Pattern Translation

Implemented intelligent pattern translation from regex to tool-specific formats:

**Supported Translations:**
- `.*\.ext$` → `*.ext` (file extension patterns)
- `^/path/.*` → `/path/*` (path prefix patterns)
- `.*/filename` → `**/filename` (recursive patterns)
- Glob patterns passed through unchanged

**Unsupported Patterns:**
- Complex regex with lookahead/lookbehind
- Character classes with ranges
- Backreferences

### Testing

Created comprehensive test suites:

#### `test_plugin_wrapper.py`
- Base wrapper functionality
- Capability checking and reporting
- Configuration validation
- Pattern translation
- Mock wrapper implementation

#### `test_wrapper_registry.py`
- Registry singleton pattern
- Wrapper registration and retrieval
- Capability-based search
- Wrapper comparison
- Instance caching

### Documentation

#### Example Script (`plugin_wrapper_demo.py`)

Created comprehensive demonstration script showing:
- Wrapper registration and discovery
- Capability detection and querying
- Pattern translation examples
- Configuration validation
- Capability comparison
- Required capability checking
- Comprehensive wrapper information

## Requirements Satisfied

This implementation satisfies the following requirements from the backup-operations spec:

- **Requirement 1.5**: Support execution across multiple backup tool types with plugin wrappers for consistent functionality
- **Requirement 4.4**: Handle parallel operation failures gracefully by relying on backup tool error handling
- **Requirement 7.4**: Use plugin wrappers to translate selection rules appropriately for different tools
- **Requirement 8.2**: Display which orchestration features are natively supported versus provided through plugin wrappers
- **Requirement 8.3**: Validate backup job configurations against target backup tool capabilities

## Design Alignment

Implementation follows the design document specifications:

### Architecture
- Plugin wrapper layer between orchestration and backup tools
- Standardized interfaces for consistent functionality
- Capability gap filling where tools lack features

### Components
- `PluginWrapper`: Base class with abstract methods
- `ResticPluginWrapper`: Concrete implementation for Restic
- `WrapperRegistry`: Registry system for wrapper management

### Data Models
- `BackupConfig`: Standardized configuration
- Capability reporting through `Feature` enum
- Validation results with errors and warnings

## Usage Examples

### Basic Wrapper Usage

```python
from TimeLocker.services import get_wrapper_registry, initialize_wrappers

# Initialize wrappers
initialize_wrappers()

# Get registry
registry = get_wrapper_registry()

# Get Restic wrapper
restic_wrapper = registry.get_wrapper('restic')

# Check capabilities
if restic_wrapper.has_capability(Feature.ENCRYPTION):
    print("Encryption supported")

# Execute backup
config = BackupConfig(
    source_paths=[Path("/data")],
    repository_uri="/backup/repo",
    exclude_patterns=["*.tmp"]
)

result = restic_wrapper.execute_backup(config)
```

### Pattern Translation

```python
# Translate patterns
include_patterns = ["*.py", ".*\\.log$"]
exclude_patterns = ["__pycache__", ".*/temp/.*"]

translated = restic_wrapper.translate_selection_rules(
    include_patterns,
    exclude_patterns
)

print(f"Translated include: {translated['include']}")
print(f"Translated exclude: {translated['exclude']}")
print(f"Unsupported: {translated['unsupported']}")
```

### Capability Search

```python
# Find wrappers with encryption
encryption_tools = registry.find_wrappers_with_capability(
    Feature.ENCRYPTION
)

# Find wrappers with native parallel processing
parallel_tools = registry.find_wrappers_with_native_capability(
    Feature.PARALLEL_PROCESSING
)
```

## Files Created

- `src/TimeLocker/services/plugin_wrapper.py` - Base wrapper class
- `src/TimeLocker/services/restic_plugin_wrapper.py` - Restic wrapper
- `src/TimeLocker/services/wrapper_registry.py` - Registry system
- `examples/plugin_wrapper_demo.py` - Demonstration script
- `tests/TimeLocker/services/test_plugin_wrapper.py` - Wrapper tests
- `tests/TimeLocker/services/test_wrapper_registry.py` - Registry tests
- `docs/updates/2025-11-07-plugin-wrapper-system.md` - This document

## Files Modified

- `src/TimeLocker/services/__init__.py` - Added wrapper exports

## Future Enhancements

### Additional Wrappers
- Borg backup wrapper
- Duplicity wrapper
- Custom tool wrappers

### Enhanced Pattern Translation
- More sophisticated regex to glob conversion
- Pattern validation and optimization
- Tool-specific pattern dialects

### Advanced Features
- Wrapper plugin discovery from external packages
- Dynamic wrapper loading
- Wrapper versioning and compatibility checking
- Performance profiling per wrapper

## Testing

Run the test suite:
```bash
# Run wrapper tests
pytest tests/TimeLocker/services/test_plugin_wrapper.py -v

# Run registry tests
pytest tests/TimeLocker/services/test_wrapper_registry.py -v

# Run demonstration
python examples/plugin_wrapper_demo.py
```

## Notes

- The wrapper system is designed to be extensible for future backup tools
- Pattern translation is best-effort; complex regex may not translate perfectly
- Wrappers cache instances for performance
- Registry follows singleton pattern for global access
- All wrappers must implement the abstract base class methods

## Related Components

- Tool Manager (`tool_manager.py`) - Capability detection
- Job Executor (`job_executor.py`) - Backup execution
- Backup Orchestrator (`backup_orchestrator.py`) - Job coordination
- Data Selection System - Pattern management

## Conclusion

The plugin wrapper system provides a robust foundation for supporting multiple backup tools with consistent interfaces and enhanced capabilities. The system successfully abstracts tool-specific details while preserving native functionality and filling capability gaps where needed.
