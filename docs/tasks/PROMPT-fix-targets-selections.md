# Prompt for New Conversation: Fix Targets → Selections Tests

## Copy this prompt to start a new conversation:

---

I need help fixing 22 failing tests in the TimeLocker project. The tests are failing because they reference deprecated "targets" commands that have been replaced with "selections" commands.

## Background

The CLI has migrated from "targets" terminology to "selections" (backup selections), but the test file `tests/TimeLocker/cli/test_targets_commands.py` hasn't been updated yet.

## Current Status

- **File:** `tests/TimeLocker/cli/test_targets_commands.py`
- **Failing tests:** 22 (100% of tests in this file)
- **Reason:** All tests use deprecated `targets` commands

## What Changed

**Old commands (deprecated):**
```bash
timelocker targets add <name> --path <path>
timelocker targets list
timelocker targets show <name>
timelocker targets edit <name>
timelocker targets remove <name>
```

**New commands (current):**
```bash
timelocker selections create <name> --path <path>
timelocker selections list
timelocker selections show <name>
timelocker selections edit <name>
timelocker selections delete <name>
timelocker selections test <name>      # New
timelocker selections export <name>    # New
timelocker selections import <file>    # New
```

## Task

Update `tests/TimeLocker/cli/test_targets_commands.py` to use the new selections commands:

1. **Rename the file** to `test_selections_commands.py`
2. **Update all command references:**
   - `targets` → `selections`
   - `targets add` → `selections create`
   - `targets remove` → `selections delete`
3. **Update test class and method names:**
   - `TestTargetsCommands` → `TestSelectionsCommands`
   - `test_targets_*` → `test_selections_*`
   - `test_targets_add_*` → `test_selections_create_*`
   - `test_targets_remove_*` → `test_selections_delete_*`
4. **Update assertions** to check for "selections" instead of "targets" in output
5. **Add tests for new commands** (test, export, import) if time permits

## Reference Files

For understanding the new implementation:
- `src/TimeLocker/cli_modules/commands/selections.py` - The actual implementation
- `tests/TimeLocker/cli/test_cli_help_system.py` - Has examples of updated tests using selections

## Example Transformation

**Before:**
```python
def test_targets_add_help(self):
    result = runner.invoke(app, ["targets", "add", "--help"])
    assert result.exit_code == 0
    assert "add" in combined.lower()
```

**After:**
```python
def test_selections_create_help(self):
    result = runner.invoke(app, ["selections", "create", "--help"])
    assert result.exit_code == 0
    assert "create" in combined.lower()
```

## Success Criteria

- All 22 tests should pass after the update
- No references to "targets" commands should remain
- Test file renamed to reflect new terminology
- All assertions updated for new command names and output

## Additional Info

- The selections commands are fully implemented and working
- Other test files have already been updated (see test_cli_help_system.py)
- The targets command group still exists but has no subcommands (intentional for helpful error messages)

Please help me update this test file systematically to use the new selections commands.

---

## Alternative Shorter Prompt:

---

Fix 22 failing tests in `tests/TimeLocker/cli/test_targets_commands.py`. 

The tests fail because they use deprecated `targets` commands. Update them to use the new `selections` commands:
- `targets add` → `selections create`
- `targets remove` → `selections delete`  
- `targets list/show/edit` → `selections list/show/edit` (same names)

Also rename the file to `test_selections_commands.py` and update all test names and assertions accordingly.

Reference: `src/TimeLocker/cli_modules/commands/selections.py` for the implementation.

---
