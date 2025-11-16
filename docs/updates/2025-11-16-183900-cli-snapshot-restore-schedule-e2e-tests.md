---
title: "Update: CLI snapshot, restore, and schedule E2E workflows"
id: "update-cli-snapshot-restore-schedule-e2e-tests"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, testing, cli, snapshots, restore, schedule]
links:
  tooling: [pytest]
---

# Update: CLI snapshot, restore, and schedule E2E workflows

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: Developers
- **Related**: tests/TimeLocker/cli/test_cli_end_to_end_snapshots_schedule_flows.py,
  tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- **Scope**: CLI snapshot/restore/schedule coverage

## 1. Purpose

Add high-level tests that mimic how operators inspect snapshots, manage restore
comparisons, and configure schedules so we can validate realistic workflows
instead of only checking help output or isolated units.

- Added `test_cli_end_to_end_snapshots_schedule_flows.py` with snapshot listing,
  detail, search, forget, and prune coverage backed by deterministic snapshot
  service mocks, and expanded schedule coverage to include script generation
  and schedule testing on top of create/list/show/enable/disable.
- Extended `test_cli_end_to_end_user_flows.py` with restore diff and verify
  scenarios so users can compare snapshots and validate restored data after a
  selection-driven backup.
- Shared helpers (`isolated_cli_environment`, `maybe_show_cli_output`) keep the
  command output visible when `TIMELOCKER_SHOW_CLI_OUTPUT=1` is set.
- Rules consulted: AGENT-GUIDE-General-Preferences (50),
  AGENT-GUIDE-Operational-Best-Practices (40), AGENT-RULE-Testing-Conventions (25).

## 3. Implementation Notes

- Key files: `tests/TimeLocker/cli/test_cli_end_to_end_snapshots_schedule_flows.py`,
  `tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py` (new restore test),
  `tests/TimeLocker/cli/conftest.py` for the shared environment fixture.
- Snapshot flows patch `snapshots._get_service_manager_for_command` so commands
  exercise the real CLI stack without hitting external repositories.
- Testing commands:
  - `pytest tests/TimeLocker/cli/test_cli_end_to_end_snapshots_schedule_flows.py`
  - `pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`

## 4. Documentation & Links

- tests/TimeLocker/cli/test_cli_end_to_end_snapshots_schedule_flows.py
- tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- README.md (CLI overview)

# References

- README.md (CLI overview)
