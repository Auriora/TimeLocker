# Prompt: Fix CLI Integration Tests (5 failures)

## Copy this prompt to start a new conversation:

---

I need help fixing 5 failing CLI integration tests in the TimeLocker project. These tests have complex mocking issues and runtime import errors.

## Failing Tests

**File:** `tests/TimeLocker/cli/test_cli_integration.py`

1. `test_repository_management_workflow` - Repository init fails with mocked service manager
2. `test_backup_creation_workflow` - Backup with target fails: 'NoneType' object has no attribute 'get_backup_targets'
3. `test_snapshot_management_workflow` - Snapshots list fails with import error
4. `test_restore_workflow` - Snapshot restore fails with import error
5. `test_error_recovery_workflow` - Duplicate repo add should fail gracefully

## Common Issues

### 1. Import Error (affects tests 3, 4)
```
Error: No module named 'src.TimeLocker.cli_modules.commands.utils'
```
- This module doesn't exist
- Error occurs at runtime when commands try to resolve repositories
- May be a dynamic import or cached import issue

### 2. Mock Configuration Issues (affects tests 2, 3)
```
'NoneType' object has no attribute 'get_backup_targets'
'NoneType' object has no attribute 'get_snapshot_details'
```
- Service manager mocks are incomplete
- Need to mock all methods that commands might call
- Need to mock both `get_cli_service_manager()` and `_get_service_manager_for_command()`

### 3. Mock Path Issues
Some tests still use old mock paths:
- ❌ `@patch('src.TimeLocker.cli.get_cli_service_manager')`
- ✅ `@patch('TimeLocker.cli_services.get_cli_service_manager')`

## Current Mock Setup Example

```python
@pytest.mark.integration
@patch('TimeLocker.cli_services.get_cli_service_manager')
def test_snapshot_management_workflow(self, mock_service_manager, temp_repo_dir):
    mock_manager = Mock()
    mock_service_manager.return_value = mock_manager
    
    # Need to add get_snapshot_details as a method, not just return_value
    mock_manager.get_snapshot_details = Mock(return_value=Mock(
        id="abc123def456", time="2024-01-01T12:00:00Z", hostname="test"
    ))
```

## Tasks

1. **Find and fix the import error:**
   - Search for any references to `cli_modules.commands.utils`
   - Check for dynamic imports using `importlib.import_module`
   - Look in `src/TimeLocker/cli.py` around line 207
   - May need to clear `__pycache__` directories

2. **Fix mock configurations:**
   - Ensure all service manager methods are properly mocked
   - Add missing methods like `get_backup_targets`, `get_snapshot_details`
   - Mock both service manager functions used in commands

3. **Update mock paths:**
   - Change any remaining `src.TimeLocker` paths to `TimeLocker`
   - Ensure consistent mocking across all tests

4. **Enhance mocks for backup workflow:**
   ```python
   @patch('TimeLocker.cli_services.get_cli_service_manager')
   @patch('TimeLocker.cli._get_service_manager_for_command')
   def test_backup_creation_workflow(self, mock_get_for_command, mock_service_manager, ...):
       mock_manager = Mock()
       mock_config_service = Mock()
       mock_manager._config_service = mock_config_service
       mock_service_manager.return_value = mock_manager
       mock_get_for_command.return_value = mock_manager
       
       # Add all methods that might be called
       mock_manager.get_backup_targets = Mock(return_value=[])
       mock_manager.execute_backup = Mock(return_value=Mock(success=True))
   ```

## Investigation Steps

1. **For import error:**
   ```bash
   # Search for the bad import
   grep -r "cli_modules.commands.utils" src/ tests/
   grep -r "src\.TimeLocker" tests/TimeLocker/cli/test_cli_integration.py
   
   # Clear cache
   find . -type d -name __pycache__ -exec rm -rf {} +
   find . -type f -name "*.pyc" -delete
   ```

2. **For mock issues:**
   - Run tests with verbose output to see exact error location
   - Check what methods the commands actually call
   - Review `src/TimeLocker/cli_modules/commands/backup.py` and `snapshots.py`

3. **Test individually:**
   ```bash
   pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_snapshot_management_workflow -xvs
   ```

## Success Criteria

- [ ] All 5 integration tests pass
- [ ] No import errors
- [ ] All mocks properly configured
- [ ] No references to `src.TimeLocker` in mock paths
- [ ] Tests run reliably without flakiness

## Alternative Approach

If the tests are too complex to fix, consider:
1. Marking them as `@pytest.mark.skip` with detailed reason
2. Creating simpler integration tests that test one workflow at a time
3. Moving to end-to-end tests with real (temporary) repositories instead of mocks

## Reference Files

- `tests/TimeLocker/cli/test_cli_integration.py` - The failing tests
- `src/TimeLocker/cli_modules/commands/backup.py` - Backup command implementation
- `src/TimeLocker/cli_modules/commands/snapshots.py` - Snapshot command implementation
- `src/TimeLocker/cli_services.py` - Service manager implementation

---

## Shorter Version:

---

Fix 5 failing CLI integration tests in `tests/TimeLocker/cli/test_cli_integration.py`:

**Issues:**
1. Import error: `No module named 'src.TimeLocker.cli_modules.commands.utils'` - find and fix this
2. Mock issues: Service manager mocks missing methods like `get_backup_targets`, `get_snapshot_details`
3. Need to mock both `get_cli_service_manager()` and `_get_service_manager_for_command()`

**Tasks:**
- Search for bad import reference (check `src/TimeLocker/cli.py` line ~207)
- Add missing methods to service manager mocks
- Ensure mocks use `TimeLocker.cli_services.get_cli_service_manager` not `src.TimeLocker.cli`
- Clear `__pycache__` if needed

**Tests:**
- test_repository_management_workflow
- test_backup_creation_workflow  
- test_snapshot_management_workflow
- test_restore_workflow
- test_error_recovery_workflow

---
