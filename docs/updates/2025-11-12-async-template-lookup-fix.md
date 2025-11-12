# Async Template Lookup Fix

**Date**: 2025-11-12  
**Type**: Bug Fix (Partial)  
**Status**: In Progress  
**Related**: Task 14, Backup CLI Selection Integration

## Summary

Fixed async/await issues in BackupCLIHandler and SelectionTemplateManager to properly handle template lookups by name. The CLI can now validate and retrieve selection templates, but full backup execution requires additional changes to BackupOrchestrator.

## Changes Implemented

### 1. SelectionTemplateManager - Added Name-Based Lookup

**File**: `src/TimeLocker/selection_template_manager.py`

Added two new methods:

```python
async def get_template_by_name(self, name: str) -> Optional[SelectionTemplate]:
    """Get a template by name (returns None if not found)"""
    
async def get_template(self, identifier: str, by_name: bool = False) -> SelectionTemplate:
    """Get a template by ID or name (raises TemplateNotFoundError if not found)"""
```

**Benefits**:
- Users can reference templates by name (user-friendly)
- Maintains backward compatibility with ID-based lookup
- Clear parameter naming prevents ambiguity

### 2. BackupCLIHandler - Made Methods Async

**File**: `src/TimeLocker/cli_modules/helpers/backup_cli_handler.py`

Updated methods to properly handle async operations:

```python
async def validate_selection_exists(self, selection_name: str) -> bool:
    """Check if template exists (now properly async)"""
    
async def get_selection_summary(self, selection_name: str) -> str:
    """Get template summary (now properly async)"""
    
async def execute_backup_with_selection(...):
    """Execute backup (already async, now uses by_name=True)"""
```

**Changes**:
- Removed synchronous wrappers (caused event loop issues)
- Made all methods properly async
- Use `by_name=True` for all template lookups
- Fixed `template.config` → `template.selection_config`

### 3. Backup CLI Command - Added Async Handling

**File**: `src/TimeLocker/cli_modules/commands/backup.py`

Updated to properly call async methods:

```python
# Validate template
async def validate_template():
    return await cli_handler.validate_selection_exists(selection)

if not asyncio.run(validate_template()):
    # error handling
    
# Get summary
async def get_summary():
    return await cli_handler.get_selection_summary(selection)

summary = asyncio.run(get_summary())
```

**Changes**:
- Added `asyncio` import at module level
- Wrapped async calls in `asyncio.run()`
- Proper error handling for template not found

## Testing Results

### ✅ Working
- Template lookup by name
- Template validation
- Template summary generation
- Error messages for missing templates

### ❌ Not Yet Working
- Full backup execution (BackupOrchestrator issue)

## Current Status

The CLI can now:
1. ✅ Validate that a selection template exists
2. ✅ Display template summary
3. ✅ Show helpful error messages for missing templates
4. ❌ Execute backup (blocked by BackupOrchestrator)

## Remaining Issues

### Issue: BackupOrchestrator Async Incompatibility

**Error**:
```
'coroutine' object has no attribute 'selection_config'
```

**Root Cause**:
BackupOrchestrator tries to load selection config but doesn't await the async call:

```python
# In backup_orchestrator.py
selection_config = self._configuration_provider.get_selection_config(selection_id)
# Should be: selection_config = await self._configuration_provider.get_selection_config(selection_id)
```

**Impact**:
- Template validation works
- Backup execution fails
- Users see confusing error about data selection not found

**Solution Required**:
1. Make BackupOrchestrator methods async
2. Update ConfigurationProvider to support async selection loading
3. Update all callers to await BackupOrchestrator methods

This is a larger refactoring that affects multiple components and is beyond the scope of the immediate CLI fix.

## Workaround

For now, users can:
1. Use direct path backups (not selection-based)
2. Wait for BackupOrchestrator async refactoring

## Files Modified

- `src/TimeLocker/selection_template_manager.py` - Added name-based lookup
- `src/TimeLocker/cli_modules/helpers/backup_cli_handler.py` - Made methods async
- `src/TimeLocker/cli_modules/commands/backup.py` - Added async handling

## Test Results

**Unit Tests**: Need to be updated for async methods  
**Integration Tests**: Partial success (validation works, execution fails)  
**Manual Testing**: Template lookup and validation confirmed working

## Next Steps

1. **High Priority**: Update BackupOrchestrator to support async selection loading
2. **High Priority**: Update ConfigurationProvider interface
3. **Medium Priority**: Update all BackupOrchestrator callers
4. **Medium Priority**: Update unit tests for async methods
5. **Low Priority**: Add integration tests for full backup flow

## Documentation

See also:
- `docs/issues/2025-11-12-backup-cli-async-template-lookup.md` - Detailed issue analysis
- `docs/issues/2025-11-12-requirements-design-updates.md` - Requirements and design proposals

---

**Status**: Partial fix implemented. Template lookup works, but full backup execution requires BackupOrchestrator refactoring.
