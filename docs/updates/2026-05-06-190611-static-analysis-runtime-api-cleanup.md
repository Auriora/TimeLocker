---
title: "Update: Static Analysis Runtime API Cleanup"
id: "update-2026-05-06-190611-static-analysis-runtime-api-cleanup"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, static-analysis, cli, tests]
links:
  tooling: [python-agent-ide, pytest, basedpyright, ruff]
---

# Update: Static Analysis Runtime API Cleanup

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/updates/2026-05-06-181759-static-analysis-triage.md`
- **Scope**: CLI command runtime/API mismatches

## 1. Purpose

Address the high-value static-analysis findings identified in the CLI command triage note.

## 2. Summary

The slice fixes stale API calls and missing guards in CLI command paths while avoiding broad generated-command lint cleanup.

## 3. Implementation Notes

- Changed credential fallback unlock checks from nonexistent `is_unlocked()` to `is_locked()`.
- Added explicit password guards before local credential unlock/store calls.
- Replaced stale `ConfigurationPathResolver.get_config_file()` usage with `get_config_file_path()`.
- Replaced stale config backup directory construction with `ConfigurationPathResolver.get_backup_directory()`.
- Guarded policy enforcement and simulation against repositories without a URI/location.
- Updated policy simulation display to use `StorageImpact.estimated_space_freed_bytes`.
- Normalized nullable backup CLI inputs before creating `CLIBackupRequest`.
- Guarded default repository resolution before credential lookup.
- Avoided direct typed access to nonexistent `CLIServiceManager.execute_backup()` by using a callable compatibility lookup.
- Normalized repository-list service responses before rendering and batch validation.
- Routed repository credential-update helper calls through `ConfigurationModule` compatibility access where the helper expects `update_repository()`.
- Validation:
  - `diagnostics_for_files` on touched command modules: original triaged API mismatches are cleared; remaining findings are broad unused imports, optional policy date display, and legacy typing noise.
  - `post_edit_feedback` on touched command modules: active findings remain in unrelated policy date optionality and backup unused imports; runtime tests were run for the touched slice.
  - `python -m pytest tests/TimeLocker/cli/test_credentials_commands.py tests/TimeLocker/cli/test_backup_commands.py tests/TimeLocker/cli/test_repos_commands.py tests/TimeLocker/cli/test_policy_commands.py -q`: 71 passed, 3 warnings.
  - `python -m pytest tests/TimeLocker/cli/test_config_commands.py tests/TimeLocker/cli/test_cli_real_service_integration.py::TestCLIRealServiceIntegration::test_configuration_validation_with_real_services -q`: 20 passed.

## 4. Documentation & Links

- `src/TimeLocker/cli_modules/commands/credentials.py`
- `src/TimeLocker/cli_modules/commands/config.py`
- `src/TimeLocker/cli_modules/commands/policy.py`
- `src/TimeLocker/cli_modules/commands/backup.py`
- `src/TimeLocker/cli_modules/commands/repositories.py`

# References

- `docs/updates/2026-05-06-181759-static-analysis-triage.md`
