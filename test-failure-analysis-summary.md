# Test Failure Analysis Summary

## Overview

Analyzed test failures in `tests/TimeLocker/cli/test_repos_commands.py` and `tests/TimeLocker/cli/test_repos_commands_integration.py`.

## Root Causes

### 1. Missing ConfigurationManager Mocking

**Issue**: Commands fall back to `ConfigurationManager(config_dir=config_dir).get_repository(name)` when service methods return `None`. This raises
`RepositoryNotFoundError` when the repository doesn't exist.

**Affected Tests**:

- test_repos_show_command
- test_repos_default_command
- test_repos_init_command
- test_repos_init_with_repository_uri
- test_repos_check_command
- test_repos_stats_command
- test_repos_unlock_command
- test_repos_migrate_command
- test_repos_forget_command

**Fix Applied**: Added `@patch('src.TimeLocker.cli_modules.commands.repositories.ConfigurationManager')` to mock the fallback configuration manager.

### 2. Service Methods Calling Real Implementation

**Issue**: Even with mocked service managers, the service methods (check_repository, get_repository_stats, unlock_repository, etc.) are being called and
internally try to look up repositories from the real configuration.

**Affected Tests**:

- test_repos_check_command
- test_repos_stats_command
- test_repos_unlock_command
- test_repos_migrate_command
- test_repos_forget_command

**Status**: Partially fixed. The ConfigurationManager is now mocked, but the service methods still raise exceptions. This suggests the mocking isn't preventing
the actual service implementation from running.

### 3. Password Required for Init Command

**Issue**: The `repos init` command requires a password in non-interactive mode.

**Fix Applied**: Added `--password "test-password"` to init command invocations.

### 4. Mock vs Dict Incompatibility (Integration Tests)

**Issue**: Integration tests expect dict objects for repositories but are receiving Mock objects, causing "'Mock' object does not support item assignment"
errors.

**Affected Tests**:

- test_update_repository_metadata
- test_update_repository_configuration
- test_set_default_repository
- test_repository_lifecycle_complete
- test_repository_state_active_to_inactive
- test_repository_error_state_recovery
- test_show_nonexistent_repository

**Status**: Not fixed yet. Tests need to use actual dict objects instead of Mock objects for repository data.

## Fixes Applied

### Unit Tests (test_repos_commands.py)

1. Added ConfigurationManager mocking to 9 tests
2. Changed repository mocks to return dicts instead of Mock objects where appropriate
3. Added password parameter to init command tests
4. Changed service method return values from `Mock(success=True)` to `{"success": True}` for better compatibility

### Tests Still Failing

- test_repos_check_command: "Repository 'test-repo' not found"
- test_repos_stats_command: "Repository 'test-repo' not found"
- test_repos_unlock_command: "Repository 'test-repo' not found"
- test_repos_migrate_command: "Repository 'test-repo' not found"
- test_repos_forget_command: "Repository 'test-repo' not found"

## Recommended Next Steps

### Short-term (Quick Fixes)

1. **For remaining unit test failures**: The service methods need to be mocked more completely. Options:
    - Mock the repository lookup within service methods
    - Use `side_effect` instead of `return_value` to ensure the mock function is called
    - Patch at a deeper level (e.g., patch the repository resolution logic)

2. **For integration test failures**: Replace Mock objects with actual dict objects in test setup:
   ```python
   repo_dict = {
       "name": "test-repo",
       "uri": "file:///tmp/test",
       "description": "Test repository",
       "metadata": {}
   }
   ```

### Long-term (Architectural)

1. **Refactor service methods**: Service methods should accept repository objects as parameters instead of looking them up internally. This makes them easier to
   test.

2. **Improve test utilities**: Create better mock factories that properly simulate the entire service stack without calling real implementations.

3. **Separate concerns**: Commands should handle repository resolution, not service methods. This makes both more testable.

## Test Status

### Unit Tests (test_repos_commands.py)

- **Passing**: 17/22 tests
- **Failing**: 5/22 tests (check, stats, unlock, migrate, forget)

### Integration Tests (test_repos_commands_integration.py)

- **Failing**: Multiple tests due to Mock vs dict issues

## Files Modified

- `tests/TimeLocker/cli/test_repos_commands.py`: Added ConfigurationManager mocking, fixed repository object types, added passwords

## Files Needing Modification

- `tests/TimeLocker/cli/test_repos_commands.py`: Fix remaining 5 failing tests
- `tests/TimeLocker/cli/test_repos_commands_integration.py`: Replace Mock objects with dicts in 7+ tests
