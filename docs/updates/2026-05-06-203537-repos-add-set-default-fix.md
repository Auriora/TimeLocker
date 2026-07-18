---
title: "Update: Repos Add Set Default Fix"
id: "update-2026-05-06-203537-repos-add-set-default-fix"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "18-07-2026"
tags: [update, cli, repositories, e2e]
links:
  tooling: [python-agent-ide, pytest, basedpyright, ruff]
---

# Update: Repos Add Set Default Fix

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers
- **Related**: `src/TimeLocker/cli_modules/commands/repositories.py`
- **Scope**: `repos add --set-default`

## 1. Purpose

Fix the E2E repository setup failure where `repos add --set-default` reported `Repository '<name>' not found`.

## 2. Summary

`repos_add` now runs its repository persistence verification/fallback before invoking `set_default_repository`. This keeps the service-manager add path and the
configuration path used by default-setting aligned before the default repository is set.

## 3. Validation

- [x] `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py::TestCLIPolicyEndToEndFlows::test_policy_lifecycle_flow -q`: passed.
- [x] Python Agent IDE diagnostics for `repositories.py`: 0 errors, 285 pre-existing warnings.
- [x] `python -m py_compile src/TimeLocker/cli_modules/commands/repositories.py`: passed.
- [x] `python -m pytest tests/TimeLocker/cli/test_repos_commands.py -q`: 26 passed.
- [x] `test_selection_backup_uses_default_repository` got past `repos add --set-default` and then failed at the separate stale `backup.get_cli_service_manager`
  patch target.

## 4. Follow-Up

The next unrelated blocker is the backup E2E patch target in `tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`.

# References

- `docs/updates/2026-05-06-203255-unrelated-e2e-failure-investigation.md`
