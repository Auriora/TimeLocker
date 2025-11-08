# Task: Fix Targets → Selections Test Migration

## Context

The TimeLocker CLI has deprecated the "targets" terminology in favor of "selections" (backup selections). However, there's an entire test file `tests/TimeLocker/cli/test_targets_commands.py` with 22 failing tests that still reference the old "targets" commands.

## Current Situation

**Test File:** `tests/TimeLocker/cli/test_targets_commands.py`
**Status:** 22 tests failing (100% failure rate in this file)
**Root Cause:** Tests reference deprecated `targets` commands that no longer exist

### What Changed:
- **Old:** `targets` command group with subcommands: `add`, `list`, `show`, `edit`, `remove`
- **New:** `selections` command group with subcommands: `create`, `list`, `show`, `edit`, `delete`, `test`, `export`, `import`

### Available Commands:
```bash
# Old (deprecated, no longer has subcommands)
timelocker targets --help

# New (current implementation)
timelocker selections --help
  Commands:
    create  Create a new data selection template
    list    List all data selection templates
    show    Show details of a data selection template
    edit    Edit an existing data selection template
    delete  Delete a data selection template
    test    Test a selection template to preview which files would be selected
    export  Export a selection template to a file
    import  Import a selection template from a file
```

## Task Requirements

### Option 1: Update Tests to Use Selections (Recommended)

Update all tests in `tests/TimeLocker/cli/test_targets_commands.py` to use the new `selections` commands:

1. **Rename test file** (optional but recommended):
   - From: `test_targets_commands.py`
   - To: `test_selections_commands.py`

2. **Update all command references:**
   - `targets` → `selections`
   - `targets add` → `selections create`
   - `targets remove` → `selections delete`
   - Keep: `list`, `show`, `edit` (same names)

3. **Update test class name:**
   - From: `TestTargetsCommands`
   - To: `TestSelectionsCommands`

4. **Update test method names:**
   - `test_targets_*` → `test_selections_*`
   - `test_targets_add_*` → `test_selections_create_*`
   - `test_targets_remove_*` → `test_selections_delete_*`

5. **Update test assertions:**
   - Check for "selections" instead of "targets" in output
   - Update help text expectations
   - Verify new command names in error messages

6. **Add tests for new commands:**
   - `test_selections_test_command` - Test the preview functionality
   - `test_selections_export_command` - Test export functionality
   - `test_selections_import_command` - Test import functionality

### Option 2: Skip All Tests (Quick Fix)

If selections commands are not fully implemented or tests need complete rewrite:

1. Add `@pytest.mark.skip` decorator to the entire test class with reason
2. Document that tests need rewrite for selections architecture

## Files to Modify

### Primary File:
- `tests/TimeLocker/cli/test_targets_commands.py` (22 tests)

### Reference Files (for understanding):
- `src/TimeLocker/cli_modules/commands/selections.py` - Implementation
- `tests/TimeLocker/cli/test_cli_help_system.py` - Already updated examples
- `tests/TimeLocker/cli/test_cli_integration.py` - Shows skipped targets tests

## Example Transformations

### Before (Old):
```python
def test_targets_add_help(self):
    """Test targets add command help output."""
    result = runner.invoke(app, ["targets", "add", "--help"])
    assert result.exit_code == 0
    assert "add" in combined.lower()
    assert "target" in combined.lower()
```

### After (New):
```python
def test_selections_create_help(self):
    """Test selections create command help output."""
    result = runner.invoke(app, ["selections", "create", "--help"])
    assert result.exit_code == 0
    assert "create" in combined.lower()
    assert "selection" in combined.lower()
```

## Testing Strategy

1. **Run current tests to see failures:**
   ```bash
   pytest tests/TimeLocker/cli/test_targets_commands.py -v
   ```

2. **After updates, verify all pass:**
   ```bash
   pytest tests/TimeLocker/cli/test_selections_commands.py -v
   ```

3. **Check integration with full suite:**
   ```bash
   pytest tests/TimeLocker/cli/ -k "selection" -v
   ```

## Success Criteria

- [ ] All 22 tests either passing or properly skipped with documentation
- [ ] Test file renamed to reflect selections terminology
- [ ] All command references updated from targets → selections
- [ ] All subcommand references updated (add → create, remove → delete)
- [ ] Help text assertions updated for new terminology
- [ ] Tests for new commands added (test, export, import) if applicable
- [ ] No references to deprecated "targets" terminology remain
- [ ] Full test suite shows improvement in pass rate

## Additional Context

### Related Changes Already Made:
- `test_cli_help_system.py` - Updated to use selections
- `test_cli_integration.py` - Skipped targets-based integration tests
- CLI implementation - Selections commands fully implemented

### Command Mapping:
| Old (Targets)    | New (Selections) | Notes                          |
|------------------|------------------|--------------------------------|
| targets add      | selections create| Different verb                 |
| targets list     | selections list  | Same                          |
| targets show     | selections show  | Same                          |
| targets edit     | selections edit  | Same                          |
| targets remove   | selections delete| Different verb                 |
| N/A              | selections test  | New command                    |
| N/A              | selections export| New command                    |
| N/A              | selections import| New command                    |

## Expected Impact

**Before:** 22 failing tests in test_targets_commands.py
**After:** 22+ passing tests in test_selections_commands.py (including new command tests)
**Overall:** Improvement from 1,629/1,727 (94.3%) to ~1,651/1,749 (94.4%) pass rate

## Notes

- The `targets` command group still exists in CLI but has no registered subcommands
- This is intentional to provide helpful error messages for users using old commands
- Tests should use the new `selections` commands exclusively
- Consider adding deprecation warnings in tests if needed
