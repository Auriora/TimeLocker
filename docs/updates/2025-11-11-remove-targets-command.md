# Remove Deprecated 'targets' CLI Command

**Date**: 2025-11-11  
**Type**: Refactoring  
**Status**: Complete  
**Related**: Data Selection System Implementation

## Overview

Removed the deprecated `targets` sub-command from the TimeLocker CLI as it has been fully replaced by the `selections` command. The `selections` command provides more flexible and powerful data selection capabilities using pattern-based selection templates.

## Changes Made

### 1. CLI Command Removal

**File**: `src/TimeLocker/cli.py`

- Removed `targets_app` Typer application registration
- Removed `targets_app` initialization and configuration
- Removed `target_name_completer` import (no longer needed)
- Updated help text examples to use `selections` instead of `targets`
- Updated quick start guide to reference `selections create` instead of `targets add`
- Updated backup examples to use `--selection` flag instead of `--target`

### 2. Command Module Deletion

**Deleted Files**:
- `src/TimeLocker/cli_modules/commands/targets.py` - Original targets command implementation
- `src/TimeLocker/cli_modules/commands/targets_refactored.py` - Refactored version (unused)

These modules contained the following commands that are now replaced:
- `targets list` → `selections list`
- `targets add` → `selections create`
- `targets show` → `selections show`
- `targets edit` → `selections edit`
- `targets remove` → `selections delete`

### 2.1 Completion Module Updates

**File**: `src/TimeLocker/completion.py`

- Removed `complete_target_names()` function (no longer needed)
- Removed `target_name_completer()` function (no longer needed)
- Updated module docstring to remove reference to "Target names"
- Updated `__all__` exports to remove target-related completers
- Kept `selection_name_completer()` as the replacement for target completion

### 2.2 Command Module Updates

**File**: `src/TimeLocker/cli_modules/commands/__init__.py`

- Removed import of `targets_app` from deleted targets module
- Updated `__all__` exports to remove `targets_app`
- Reorganized imports for cleaner structure

**File**: `src/TimeLocker/cli_modules/commands/backup.py`

- Replaced `target_name_completer` import with `selection_name_completer`
- Added `--selection` parameter as the primary option
- Kept `--target` parameter as deprecated (hidden) for backward compatibility
- Added deprecation warning when `--target` is used
- Updated all internal logic to use `selection` instead of `target`
- Maintained backward compatibility by mapping `--target` to `--selection`

**File**: `src/TimeLocker/cli_modules/commands/snapshots.py`

- Removed `target_name_completer` import
- Removed autocompletion from `--tag` option (was incorrectly using target completer)

### 3. Test Removal

**Deleted Files**:
- `tests/TimeLocker/cli/test_targets_commands.py` - Tests for deprecated targets commands

Note: Tests for the replacement `selections` functionality exist in the selections test suite.

### 4. Documentation Updates

**File**: `docs/reference/timelocker-cli-command-hierarchy.md`

Updated the CLI command hierarchy reference documentation:
- Replaced `targets/` namespace with `selections/` in command tree
- Updated design philosophy to reference `selections` instead of `targets`
- Added migration guide entries showing how to migrate from `targets` to `selections`
- Updated command aliases to remove deprecated `targets` aliases
- Added deprecation notice in usage notes
- Updated examples to use `selections` commands
- Added changelog entry documenting the removal

**Migration Guide Additions**:
| Legacy Command | Current Command |
|----------------|-----------------|
| `tl targets add mytarget /path` | `tl selections create mytarget --include '/path/**'` |
| `tl targets list` | `tl selections list` |
| `tl targets show mytarget` | `tl selections show mytarget` |

**File**: `docs/4-testing/guide-minio-testing.md`

Updated MinIO testing guide:
- Changed `tl targets add` example to `tl selections create`
- Updated backup command to use `--selection` flag instead of target name

**File**: `docs/4-testing/quickstart-testing.md`

Updated quickstart testing guide:
- Changed `tl targets add` example to `tl selections create`
- Updated backup command to use `--selection` flag

### 5. Update Documents

**File**: `docs/updates/2025-11-08-config-export-import-migration.md`

Note: This document references "targets" in the context of configuration export/import. These references are intentionally left as-is since they refer to the configuration data structure (`backup_targets`) rather than the CLI command. The configuration structure may still use "targets" terminology internally even though the CLI command has been removed.

**File**: `docs/updates/2025-11-08-cli-aliases-performance-platform.md`

Note: This document includes `tgt` → `targets` in the list of command shortcuts. This reference is historical and documents what was implemented at that time. The alias system will simply not resolve `tgt` anymore since the `targets` command no longer exists.

## Migration Path

Users who were using the `targets` command should migrate to `selections`:

### Before (Deprecated)
```bash
# Add a backup target
tl targets add documents --path ~/Documents --path ~/Projects

# List targets
tl targets list

# Show target details
tl targets show documents

# Run backup with target
tl backup run --target documents
```

### After (Current)
```bash
# Create a selection template
tl selections create documents \
  --include '~/Documents/**' \
  --include '~/Projects/**'

# List selections
tl selections list

# Show selection details
tl selections show documents

# Run backup with selection
tl backup run --selection documents
```

## Key Differences

The `selections` system provides several advantages over the deprecated `targets`:

1. **Pattern-Based**: Uses glob patterns for flexible file matching
2. **Include/Exclude**: Supports both include and exclude patterns
3. **Reusable Templates**: Selection templates can be saved and reused
4. **More Flexible**: Better support for complex selection scenarios
5. **Export/Import**: Selection templates can be exported and imported

## Backward Compatibility

**Breaking Change**: The `targets` command is no longer available. Users must migrate to `selections`.

**Partial Compatibility**: The `backup create` command still accepts `--target` as a hidden deprecated parameter that maps to `--selection`. This provides a transition period for users, but a deprecation warning is displayed.

**Configuration**: The underlying configuration structure (`backup_targets` in config files) may still exist for backward compatibility with existing configurations. However, the CLI no longer provides commands to manage these directly. Users should migrate their configuration to use selections.

## Testing

After removal:
- Verified CLI starts without errors
- Confirmed `targets` command is not available
- Verified `selections` command works as expected
- Checked that help text no longer references `targets`
- Validated documentation updates

## Requirements Addressed

This change aligns with the data selection system implementation and removes deprecated functionality that has been superseded by a more flexible and powerful system.

## Related Work

- Data Selection System Implementation (file_selections.py)
- Selections CLI Commands (cli_modules/commands/selections.py)
- Selection Manager Service

## Future Considerations

1. **Configuration Migration**: Consider adding a migration tool to automatically convert old `backup_targets` configuration to selection templates
2. **Deprecation Warnings**: If any internal code still references "targets", add deprecation warnings
3. **Documentation Audit**: Review all documentation to ensure no remaining references to the deprecated `targets` command

## Conclusion

Successfully removed the deprecated `targets` CLI command and updated all documentation to reference the replacement `selections` command. The CLI is now cleaner and users have a clear migration path to the more powerful selections system.

