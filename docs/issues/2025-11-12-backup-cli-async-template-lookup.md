# Backup CLI Async Template Lookup Issue

**Date**: 2025-11-12  
**Type**: Bug  
**Status**: Identified - Needs Fix  
**Severity**: High (Blocks backup functionality)  
**Related Task**: Task 14 - Update backup CLI commands to use data selections

## Issue Description

When executing `tl backup create --selection temporary-files --repository test-pickle`, the command fails with:
- RuntimeWarning: coroutine 'SelectionTemplateManager.get_template' was never awaited
- TemplateNotFoundError: Template with ID 'temporary-files' not found

## Root Causes

### 1. Async/Await Mismatch

**Problem**: `SelectionTemplateManager.get_template()` is an async method, but it's being called without `await` in several places:

```python
# In backup_cli_handler.py - validate_selection_exists()
template = self.selection_manager.template_manager.get_template(selection_name)
# Should be: template = await self.selection_manager.template_manager.get_template(selection_name)
```

**Impact**: The coroutine is never executed, so validation always fails.

### 2. Template Lookup by Name vs ID

**Problem**: `get_template()` expects a template ID, but we're passing a template name.

From `selection_template_manager.py`:
```python
async def get_template(self, template_id: str) -> Optional[SelectionTemplate]:
    """Get template by ID"""
    # ...
```

But we're calling it with a name:
```python
template = await self.selection_manager.template_manager.get_template(selection_name)
```

**Impact**: Even if async is fixed, lookup fails because names don't match IDs.

## Affected Components

### 1. BackupCLIHandler (`src/TimeLocker/cli_modules/helpers/backup_cli_handler.py`)

**Methods with issues:**
- `validate_selection_exists()` - Line ~100: Calls `get_template()` without await
- `get_selection_summary()` - Line ~130: Calls `get_template()` without await  
- `execute_backup_with_selection()` - Line ~212: Calls `get_template()` without await

**Current signature:**
```python
def validate_selection_exists(self, selection_name: str) -> bool:
```

**Should be:**
```python
async def validate_selection_exists(self, selection_name: str) -> bool:
```

### 2. Backup CLI Command (`src/TimeLocker/cli_modules/commands/backup.py`)

**Issues:**
- Line ~128: Calls `validate_selection_exists()` without await
- Line ~168: Calls `get_selection_summary()` without await
- The entire selection handling block needs to be async

## Design Issues

### Issue 1: Synchronous CLI with Async Services

**Current Design:**
```
CLI Command (sync) → BackupCLIHandler (sync) → SelectionManager (async)
```

**Problem**: CLI commands in Typer are synchronous, but SelectionManager uses async methods.

**Options:**

**Option A: Make BackupCLIHandler methods async**
- Pros: Proper async/await chain
- Cons: Requires CLI command to handle async (already using asyncio.run)

**Option B: Add synchronous wrapper methods in SelectionManager**
- Pros: Simpler CLI integration
- Cons: Duplicates code, loses async benefits

**Option C: Use asyncio.run() in BackupCLIHandler methods**
- Pros: Keeps CLI simple, handles async internally
- Cons: Multiple event loops, potential performance issues

### Issue 2: Template Lookup API Inconsistency

**Current API:**
```python
async def get_template(self, template_id: str) -> Optional[SelectionTemplate]
```

**Problem**: No method to get template by name, only by ID.

**Solution Needed:**
```python
async def get_template_by_name(self, name: str) -> Optional[SelectionTemplate]
```

Or update `get_template()` to accept both ID and name.

## Requirements Impact

### Requirement 10.2: Template Retrieval from Selection Manager

**Current Requirement:**
> The CLI shall retrieve data selection templates from the Selection Manager using template names provided by users.

**Issue**: SelectionManager only supports lookup by ID, not by name.

**Recommendation**: Update requirement to clarify:
- Users provide template names in CLI
- CLI must resolve names to IDs before calling SelectionManager
- OR SelectionManager must support name-based lookup

### Requirement 10.4: Clear Error Messages

**Current Requirement:**
> When a specified template is not found, the CLI shall display a clear error message listing available templates.

**Issue**: Current implementation shows "Template with ID 'temporary-files' not found" which is confusing because users think in terms of names, not IDs.

**Recommendation**: Error messages should reference template names, not IDs.

## Proposed Solutions

### Solution 1: Add Synchronous Wrapper Methods (Recommended)

Add synchronous wrapper methods to BackupCLIHandler that handle async internally:

```python
class BackupCLIHandler:
    def validate_selection_exists(self, selection_name: str) -> bool:
        """Synchronous wrapper for async validation"""
        return asyncio.run(self._validate_selection_exists_async(selection_name))
    
    async def _validate_selection_exists_async(self, selection_name: str) -> bool:
        """Async implementation"""
        try:
            template = await self.selection_manager.template_manager.get_template_by_name(selection_name)
            return template is not None
        except Exception:
            return False
```

**Pros:**
- Keeps CLI code simple and synchronous
- Properly handles async SelectionManager
- Clear separation of sync/async boundaries

**Cons:**
- Creates multiple event loops (one per method call)
- Slightly more complex BackupCLIHandler

### Solution 2: Make Entire Selection Flow Async

Make the entire selection handling block in the CLI async:

```python
async def handle_selection_backup(selection, repository, ...):
    # All async operations here
    cli_handler = BackupCLIHandler(...)
    if not await cli_handler.validate_selection_exists(selection):
        # error handling
    result = await cli_handler.execute_backup_with_selection(...)
    return result

# In backup_create command:
if selection:
    result = asyncio.run(handle_selection_backup(selection, repository, ...))
```

**Pros:**
- Single event loop
- Cleaner async flow
- Better performance

**Cons:**
- More complex CLI code
- Harder to debug

### Solution 3: Add Template Name Lookup to SelectionManager

Add a method to SelectionManager to get templates by name:

```python
# In SelectionTemplateManager
async def get_template_by_name(self, name: str) -> Optional[SelectionTemplate]:
    """Get template by name"""
    for template in self.templates_cache.values():
        if template.name == name:
            return template
    return None

# Or make get_template() accept both
async def get_template(self, identifier: str) -> Optional[SelectionTemplate]:
    """Get template by ID or name"""
    # Try ID first
    if identifier in self.templates_cache:
        return self.templates_cache[identifier]
    
    # Try name
    for template in self.templates_cache.values():
        if template.name == identifier:
            return template
    
    return None
```

**Pros:**
- More flexible API
- Matches user expectations (lookup by name)
- Simpler CLI code

**Cons:**
- Changes SelectionManager API
- Potential ambiguity if ID and name collide

## Recommended Approach

**Combination of Solutions 1 and 3:**

1. **Update SelectionTemplateManager** to support name-based lookup
2. **Add synchronous wrappers** in BackupCLIHandler for CLI convenience
3. **Keep async methods** for internal use and future async CLI support

This provides:
- ✅ Backward compatibility
- ✅ Simple CLI integration
- ✅ Proper async handling
- ✅ Flexible template lookup
- ✅ Clear error messages

## Implementation Priority

1. **High Priority** (Blocks functionality):
   - Fix async/await in BackupCLIHandler
   - Add template name lookup to SelectionManager

2. **Medium Priority** (Improves UX):
   - Update error messages to use names instead of IDs
   - Add better validation error messages

3. **Low Priority** (Future improvement):
   - Optimize to use single event loop
   - Add caching for template lookups

## Testing Requirements

### Unit Tests Needed:
- [ ] Test synchronous wrapper methods
- [ ] Test template lookup by name
- [ ] Test template lookup by ID
- [ ] Test error handling for missing templates
- [ ] Test async/sync boundary handling

### Integration Tests Needed:
- [ ] Test full backup flow with selection
- [ ] Test error messages shown to users
- [ ] Test completion still works after changes

## Related Files

- `src/TimeLocker/cli_modules/helpers/backup_cli_handler.py`
- `src/TimeLocker/selection_template_manager.py`
- `src/TimeLocker/cli_modules/commands/backup.py`
- `.kiro/specs/backup-operations/requirements.md`
- `.kiro/specs/backup-operations/design.md`

---

**Next Steps:**
1. Review and approve proposed solution
2. Update requirements and design documents
3. Implement fixes
4. Add comprehensive tests
5. Update documentation
