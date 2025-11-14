# Restore CLI Test Updates

**Date**: 2025-11-13  
**Type**: Test Maintenance  
**Status**: Complete  
**Owner**: Codex Agent  
**Related**: Restore namespace migration for CLI commands  
**Scope**: CLI regression tests / documentation

## 1. Purpose

Align the CLI test suite with the new `restore` command namespace introduced during the snapshot/restore refactor. Prior runs failed or asserted against
non-existent `snapshots` subcommands such as `contents`, `restore`, `mount`, `umount`, and `find-in`.

## 2. Summary

- Updated CLI error-handling, help-system, integration, and snapshot-ID validation tests to target the `restore` command group.
- Added deterministic mocks for the restore module to cover browse, search, mount, and recovery flows without depending on real repositories.
- Documented the expectation that `restore umount` is not yet implemented so tests assert the correct failure semantics.

## 3. Implementation Notes

- Files touched: `tests/TimeLocker/cli/test_cli_error_handling.py`, `test_cli_help_system.py`, `test_cli_integration.py`,
  `test_snapshot_id_cli_validation.py`, `test_config_commands.py`, and `test_utils.py` (new helpers for restore/service patching). Updated
  `docs/updates/index.md`.
- Added contextual helper `patch_restore_commands` so CLI tests can reliably simulate restore workflows and validation failures.
- Adjusted CLI integration mocks so snapshot operations use the service manager facade (matching the runtime wiring) before invoking restore commands, and
  expanded config-show tests to patch the new `_create_config_service` factory.

## 4. Testing

- `pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_invalid_snapshot_id_validation`
- `pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_error_message_quality`
- `pytest tests/TimeLocker/cli/test_cli_help_system.py`
- `pytest tests/TimeLocker/cli/test_monitoring_commands.py`
- `pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_snapshot_management_workflow`
- `pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_restore_workflow`
- `pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_repository_management_workflow`
- `pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_backup_creation_workflow`
- `pytest tests/TimeLocker/cli/test_cli_integration.py::TestCLIIntegrationWorkflows::test_error_recovery_workflow`
- `pytest tests/TimeLocker/cli/test_snapshot_id_cli_validation.py`
- `pytest tests/TimeLocker/cli/test_repos_commands.py`
- `pytest tests/TimeLocker/cli/test_restore_commands.py`
- `pytest tests/TimeLocker/cli/test_restore_commands_enhanced.py`
- `pytest tests/TimeLocker/cli/test_performance_compatibility.py -k "CommandStartupPerformance or CrossPlatformBehavior"`
- `pytest tests/TimeLocker/cli/test_config_commands.py::TestConfigCommands::test_config_show_configuration_error`

## 5. Rules Consulted

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md` (priority 50) — repository-wide coordination guidance and requirement to log consulted rules.
- `docs/guides/ai-agent/AGENT-RULE-Testing-Conventions.md` (priority 25) — dictates placement/naming for test changes and testing expectations.
