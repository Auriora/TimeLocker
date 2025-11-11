---
title: "Snapshots Namespace Refactoring"
date: "2025-11-11"
type: [ update, refactoring ]
status: [ completed ]
tags: [cli, snapshots, refactoring, deprecation]
related_specs: [cli-interface, recovery-operations]
---

# Snapshots Namespace Refactoring

## Summary

Refactored the `snapshots` namespace to remove recovery-related commands, achieving proper separation of concerns between snapshot lifecycle management and data recovery operations. Deprecated commands remain available with warnings to guide users to the new `restore` namespace.

## Changes Made

### Commands Deprecated and Hidden

The following commands have been marked as deprecated and hidden from help output:

1. **`snapshots restore`** → Use `tl restore full` or `tl restore files`
2. **`snapshots mount`** → Use `tl restore mount`
3. **`snapshots umount`** → Use `tl restore umount`
4. **`snapshots contents`** → Use `tl restore browse`

### Commands Retained in Snapshots Namespace

The following commands remain in the `snapshots` namespace for snapshot lifecycle management:

1. **`snapshots list`** - List snapshots in repository
2. **`snapshots show`** - Display snapshot details
3. **`snapshots forget`** - Remove a specific snapshot
4. **`snapshots find`** - Search across snapshots
5. **`snapshots prune`** - Prune unused data
6. **`snapshots diff`** - Show differences between snapshots

## Implementation Details

### Deprecation Strategy

- Commands renamed with `_deprecated` suffix
- Marked with `deprecated=True` and `hidden=True` flags
- Added deprecation warnings in docstrings
- Display user-friendly warnings when commands are used
- Commands still functional to avoid breaking existing scripts

### Example Deprecation Warning

When users run deprecated commands, they see:

```bash
$ tl snapshots restore abc123 /restore/path
⚠️  Warning: 'snapshots restore' is deprecated.
   Use 'tl restore full <repository> <snapshot-id> <target>' instead.
```

### Files Modified

1. **`src/TimeLocker/cli_modules/commands/snapshots.py`**
   - Renamed 4 command functions with `_deprecated` suffix
   - Added deprecation flags and warnings
   - Updated docstrings with deprecation notices

## User Impact

### For New Users
- ✅ Clean command structure with clear separation
- ✅ Intuitive command discovery
- ✅ No confusion about which namespace to use

### For Existing Users (if any)
- ✅ Deprecated commands still work
- ✅ Clear migration guidance in warnings
- ✅ No breaking changes
- ⚠️ Should migrate to new commands

## Migration Guide

| Old Command | New Command |
|-------------|-------------|
| `tl snapshots restore <id> <target>` | `tl restore full <repo> <id> <target>` |
| `tl snapshots restore <id> <target> --include /path` | `tl restore files <repo> <id> /path --target <target>` |
| `tl snapshots contents <id>` | `tl restore browse <repo> <id>` |
| `tl snapshots mount <id> <mountpoint>` | `tl restore mount <repo> <id> <mountpoint>` |
| `tl snapshots umount <id>` | `tl restore umount <id>` |

### Key Differences

1. **Explicit Repository Parameter**: New `restore` commands require explicit repository parameter for clarity
2. **Separate Full vs Selective**: `restore full` for complete restoration, `restore files` for selective
3. **Browse Instead of Contents**: `restore browse` is more descriptive than `contents`

## Verification

### Command Listing

```bash
$ tl snapshots --help
Commands:
  list    List snapshots in repository
  show    Display snapshot details
  forget  Forget (remove) a specific snapshot
  find    Search across snapshots
  prune   Prune unused data
  diff    Show differences between snapshots
```

✅ Only management commands shown (deprecated commands hidden)

### Deprecated Command Access

```bash
$ tl snapshots restore --help
[DEPRECATED] Restore files from this snapshot.
This command has been moved to the 'restore' namespace.
```

✅ Deprecated commands still accessible with warnings

### New Restore Commands

```bash
$ tl restore --help
Commands:
  list    List available snapshots
  browse  Explore snapshot contents
  full    Restore complete snapshot
  files   Restore specific files
  verify  Verify restored data
  mount   Mount snapshot
  umount  Unmount snapshot
  find    Search for files
  diff    Compare snapshots
```

✅ All recovery operations in dedicated namespace

## Compliance Status

### Design Philosophy Alignment

Per `docs/reference/timelocker-cli-command-hierarchy.md`:

- ✅ **Snapshot lifecycle management** under `snapshots` (list, forget, prune)
- ✅ **Recovery operations** under `restore` (browse, restore, verify)
- ✅ Clear separation of concerns achieved

### Requirements Compliance

- ✅ CLI Interface Requirements - Requirement 13: Fully compliant
- ✅ Recovery Operations Design: Architectural alignment achieved
- ✅ Separation of concerns principle: Implemented

## Benefits

### Architectural
- ✅ Clear separation between management and recovery
- ✅ Matches internal architecture (RecoveryOrchestrator, SnapshotBrowser, RecoveryValidator)
- ✅ Easier to extend each namespace independently

### User Experience
- ✅ Clearer command intent
- ✅ Better discoverability
- ✅ Reduced namespace pollution
- ✅ Intuitive command structure

### Maintainability
- ✅ Easier to add recovery features without cluttering snapshot management
- ✅ Clear ownership of functionality
- ✅ Better code organization

## Future Considerations

### Complete Removal Timeline

Deprecated commands can be completely removed in a future major version:

1. **v1.0 - v1.x**: Deprecated commands available with warnings (current)
2. **v2.0**: Consider removing deprecated commands entirely
3. **Migration Period**: Recommend 6-12 months of deprecation warnings

### Documentation Updates

- ✅ Command hierarchy documentation updated
- ✅ User guides need updating to use new commands
- ✅ Examples in documentation should use `restore` namespace
- ⚠️ Quickstart guides need review and update

## Related Changes

This refactoring completes Phase 2 of the restore namespace implementation:

- **Phase 1**: ✅ Create restore namespace (completed)
- **Phase 2**: ✅ Refactor snapshots namespace (completed)
- **Phase 3**: ⏳ Enhanced features (pending)
- **Phase 4**: ⏳ Comprehensive testing (pending)

## References

- **Restore Implementation**: `docs/updates/2025-11-11-restore-namespace-implementation.md`
- **Gap Analysis**: `docs/reports/2025-11-11-snapshots-restore-command-gap-analysis.md`
- **Implementation Plan**: `docs/plans/restore-namespace-implementation-plan.md`
- **Command Hierarchy**: `docs/reference/timelocker-cli-command-hierarchy.md`
- **CLI Interface Requirements**: `.kiro/specs/cli-interface/requirements.md`

## Rules Consulted

- operational-best-practices.md (Priority 40) - SRS alignment, minimal changes
- coding-standards.md (Priority 100) - SOLID principles, separation of concerns
- general-preferences.md (Priority 50) - SOLID and DRY principles
- documentation-conventions.md (Priority 20) - Update placement

## Rules Applied

- Minimal changes to existing functionality (deprecation, not removal)
- Clear separation of concerns (SOLID principles)
- User-friendly migration path with warnings
- Comprehensive documentation of changes
