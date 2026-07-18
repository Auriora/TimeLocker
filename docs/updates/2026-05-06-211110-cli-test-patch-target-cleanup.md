---
title: "Update: CLI Test Patch Target Cleanup"
id: "update-2026-05-06-211110-cli-test-patch-target-cleanup"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "18-07-2026"
tags: [update, cli, tests, repositories, credentials]
links:
  tooling: [python-agent-ide, pytest, py_compile]
---

# Update: CLI Test Patch Target Cleanup

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers
- **Related**: `tests/TimeLocker/cli/test_cli_error_handling.py`, `tests/TimeLocker/cli/test_repos_commands_integration.py`, `tests/TimeLocker/cli/test_repos_credentials_commands.py`
- **Scope**: CLI repository and credential test stabilization

## 1. Purpose

Continue the broader CLI integration/E2E validation slice after the repository default and service-manager patch target fixes.

## 2. Summary

The full CLI suite first exposed stale repository command patch targets and mock-shape mismatches. Repository tests now patch
`src.TimeLocker.cli_modules.commands.repositories._get_service_manager_for_command`, matching the helper imported by the command module.

Repository update tests now provide mutable mapping configurations where `repos update` expects to assign configuration fields. Repository credential tests now use
simple repository objects instead of bare `Mock` instances, avoiding the unintended `Mock.to_dict()` path in `cli.py`.

## 3. Validation

- [x] `python -m pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_service_manager_exceptions tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryCreationWithExistingDetection::test_add_new_repository_no_existing tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryCreationWithExistingDetection::test_add_repository_with_engine_selection tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryValidationCommands::test_validate_single_repository_success tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryValidationCommands::test_validate_with_performance_metrics -q`: 5 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryStateTransitions::test_repository_lifecycle_complete tests/TimeLocker/cli/test_repos_commands_integration.py::TestRepositoryStateTransitions::test_repository_state_active_to_inactive -q`: 2 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_repos_credentials_commands.py -q`: 11 passed.
- [x] `python -m py_compile tests/TimeLocker/cli/test_cli_error_handling.py tests/TimeLocker/cli/test_repos_commands_integration.py tests/TimeLocker/cli/test_repos_credentials_commands.py`: passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_cli_error_handling.py tests/TimeLocker/cli/test_repos_commands_integration.py tests/TimeLocker/cli/test_repos_credentials_commands.py -q`: 61 passed.
- [x] `python -m pytest tests/TimeLocker/cli -q`: 485 passed, 8 warnings.

Python Agent IDE was used for task context and post-edit feedback. One post-edit feedback call failed with `table schema_version already exists`; direct pytest and
py_compile validation were used for the final verification.

## 4. Follow-Up

The full CLI package is green. The next useful slice is broader non-CLI test validation or a focused static-analysis cleanup of the remaining test typing warnings.

# References

- `docs/updates/2026-05-06-204145-backup-e2e-patch-target-fix.md`
