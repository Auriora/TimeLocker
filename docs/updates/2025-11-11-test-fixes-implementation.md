# Test Fixes Implementation

**Date**: 2025-11-11  
**Status**: Implementation in Progress

## Summary

After analyzing the test failures and current implementation, I've identified that the issue is NOT with patch paths (test_repos_commands.py already uses correct paths), but with:

1. **Missing service manager methods** - Tests expect methods that don't exist
2. **Incorrect mock return values** - Mocks don't match actual service structure  
3. **Test isolation issues** - Tests interfere with each other

## Key Findings

### Finding 1: test_repos_commands.py Uses Correct Patches

The file already patches `src.TimeLocker.cli.get_cli_service_manager` correctly. The failures are due to:
- Missing methods on the mocked service manager
- Incorrect return value structures
- Service manager not being properly initialized in tests

### Finding 2: Service Manager Method Mismatches

Tests expect these methods that may not exist or have different signatures:
- `remove_repository()` 
- `check_repository()`
- `get_repository_stats()`
- `check_all_repositories()`
- `get_all_repository_stats()`
- `unlock_repository()`
- `migrate_repository()`
- `apply_retention_policy()`

### Finding 3: Snapshot Commands Use Wrong Patch Path

`test_snapshots_commands.py` patches:
```python
@patch('TimeLocker.cli_modules.commands.base._get_service_manager_for_command')
```

Should be:
```python
@patch('src.TimeLocker.cli.get_cli_service_manager')
```

## Implementation Strategy

### Step 1: Verify Actual CLI Service Manager API

Need to check `src/TimeLocker/cli_services.py` to see what methods actually exist on `CLIServiceManager`.

### Step 2: Update Test Mocks to Match Reality

Update mocks to:
1. Only mock methods that actually exist
2. Return structures that match actual implementation
3. Handle cases where methods don't exist gracefully

### Step 3: Fix Incorrect Patch Paths

Files needing patch path fixes:
- `tests/TimeLocker/cli/test_snapshots_commands.py` - Change to `src.TimeLocker.cli.get_cli_service_manager`
- `tests/TimeLocker/cli/test_cli_integration.py` - Verify patch paths

### Step 4: Fix Repository Manager Tests

For `test_repository_error_handling_recovery.py`:
1. Remove tests for non-existent private methods
2. Test actual public API instead
3. Use ValidationService correctly (validate_connectivity, validate_integrity)

### Step 5: Fix Credential Storage Tests

For `test_store_backend_credentials.py`:
1. Review actual `cli_helpers.store_backend_credentials` implementation
2. Update mocks to match actual call flow
3. Fix credential data structure expectations

## Next Actions

1. Read `src/TimeLocker/cli_services.py` to understand actual API
2. Create standardized mock factory in `test_utils.py`
3. Apply fixes systematically to each test file
4. Run tests incrementally to verify fixes

## Files Requiring Changes

### High Priority
- [ ] `tests/TimeLocker/cli/test_snapshots_commands.py` - Fix patch paths
- [ ] `tests/TimeLocker/cli/test_cli_integration.py` - Fix patch paths and mocks
- [ ] `tests/TimeLocker/cli/test_repos_commands_integration.py` - Fix mocks
- [ ] `tests/TimeLocker/services/test_repository_error_handling_recovery.py` - Rewrite to use actual API
- [ ] `tests/TimeLocker/cli/test_store_backend_credentials.py` - Fix credential flow

### Medium Priority  
- [ ] `tests/TimeLocker/config/test_configuration_backup_manager.py` - Fix backup logic tests
- [ ] `tests/TimeLocker/config/test_configuration_integration_workflows.py` - Fix integration tests

### Test Infrastructure
- [x] `tests/TimeLocker/cli/test_patch_helper.py` - Created helper module
- [ ] `tests/TimeLocker/cli/test_utils.py` - Add standardized mock factory

## Rules Applied

- **operational-best-practices.md**: Thorough analysis before changes
- **testing-conventions.md**: Maintaining test organization
- **coding-standards.md**: Following SOLID principles in test design
