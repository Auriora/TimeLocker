---
title: "Update: Mock repository + CLI fixtures restored"
id: "update-2025-11-15-mock-repo-cli-fixtures"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, testing, cli]
links:
  tooling: [pytest]
---

# Update: Mock repository + CLI fixtures restored

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: docs/updates/2025-11-14-cli-test-failure-plan.md
- **Scope**: tests/TimeLocker/backup, tests/TimeLocker/cli, CLI repo resolver tests

## 1. Purpose

Rebuilt the testing scaffolding called out in the 2025-11-14 CLI failure plan so snapshot unit tests and CLI suites stop hitting the real Restic stack. The focus was MockBackupRepository, CLI service manager mocks, and repo-resolver fixtures.

## 2. Summary

- MockBackupRepository once again satisfies BackupRepository requirements and returns the deterministic values expected by `tests/TimeLocker/backup/test_snapshot.py`.
- `create_mock_cli_service_manager()` now exposes every CLI-facing method (e.g., `get_repository`, `list_snapshots`) and keeps repository calls inside fake handlers that tests can still override.
- Repository resolver integration tests now allocate unique temp config roots per test via `tmp_path_factory` to prevent `FileExistsError` collisions.

## 3. Implementation Notes

- Key files: `tests/TimeLocker/backup/mock_repository.py`, `tests/TimeLocker/cli/test_utils.py`, `tests/TimeLocker/cli_modules/commands/test_repository_resolver_integration.py`.
- Rules consulted/applied: `AGENT-GUIDE-General-Preferences`, `AGENT-GUIDE-Coding-Standards`, `AGENT-RULE-Documentation-Conventions`.
- Tests:
  - `pytest tests/TimeLocker/backup/test_snapshot.py`
  - `pytest tests/TimeLocker/cli/test_mock_verification.py`
  - `pytest tests/TimeLocker/cli_modules/commands/test_repository_resolver_integration.py`

## 4. Documentation & Links

- Reference recovery plan: `docs/updates/2025-11-14-cli-test-failure-plan.md`.

# References

- docs/updates/2025-11-14-cli-test-failure-plan.md
