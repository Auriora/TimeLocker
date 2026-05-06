---
title: "Update: Backup E2E Patch Target Fix"
id: "update-2026-05-06-204145-backup-e2e-patch-target-fix"
type: [ update ]
status: [ draft ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, cli, e2e, backup, tests]
links:
  tooling: [python-agent-ide, pytest, basedpyright, ruff]
---

# Update: Backup E2E Patch Target Fix

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers
- **Related**: `tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`, `tests/TimeLocker/cli/test_cli_integration.py`, `tests/TimeLocker/cli/test_cli_error_handling.py`, `tests/TimeLocker/cli/test_snapshots_commands.py`
- **Scope**: Stale command service-manager patch targets

## 1. Purpose

Fix the remaining E2E blocker where tests patched `src.TimeLocker.cli_modules.commands.backup.get_cli_service_manager`, which is no longer exposed by
`backup.py`.

## 2. Summary

Updated backup CLI tests to patch the command module dependency actually used by `backup.py`: `_get_service_manager_for_command`.

The E2E helper already patched `_get_service_manager_for_command`, so the stale second patch was removed. Older integration/error-handling tests that still
referenced `backup.get_cli_service_manager` were retargeted to the same command-module helper.

The follow-on snapshots-list mock gap had the same root shape: `snapshots.py` imports `_get_service_manager_for_command` into the snapshots command module, so
tests that patched only `src.TimeLocker.cli.get_cli_service_manager` did not affect the command under test. Those tests now patch
`src.TimeLocker.cli_modules.commands.snapshots._get_service_manager_for_command`.

## 3. Validation

- [x] `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py -q`: 6 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py::TestCLIEndToEndWorkflows::test_selection_driven_backup_flow tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py::TestCLIEndToEndWorkflows::test_selection_backup_uses_default_repository -q`: 2 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_keyboard_interrupt_handling -q`: passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_backup_commands.py tests/TimeLocker/cli/test_backup_data_selection_integration.py -q`: 29 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_backup_creation_workflow tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_snapshot_management_workflow tests/TimeLocker/cli/test_snapshots_commands.py -q`: 15 passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_cli_integration.py -q`: 8 passed.
- [x] `python -m py_compile tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py tests/TimeLocker/cli/test_cli_integration.py tests/TimeLocker/cli/test_cli_error_handling.py`: passed.
- [x] `python -m py_compile tests/TimeLocker/cli/test_cli_integration.py tests/TimeLocker/cli/test_snapshots_commands.py`: passed.
- [x] Python Agent IDE diagnostics for the edited files: Ruff clean; remaining basedpyright findings are existing test-harness typing issues.

## 4. Follow-Up

Continue with broader CLI integration failures if that suite is next.

# References

- `docs/updates/2026-05-06-203255-unrelated-e2e-failure-investigation.md`
