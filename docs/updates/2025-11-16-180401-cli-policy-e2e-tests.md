---
title: "Update: CLI policy end-to-end workflows"
id: "update-cli-policy-e2e-tests"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, testing, cli, policy]
links:
  tooling: [pytest]
---

# Update: CLI policy end-to-end workflows

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: Developers
- **Related**: tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py
- **Scope**: CLI policy commands & tests

## 1. Purpose

Add realistic policy workflows to the CLI end-to-end suite and align the CLI
implementation with the current PolicyManager API so that backup/retention
policies, selections, and assignments can be exercised exactly the way users do.

## 2. Summary

- Introduced `tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py`, which
  provisions repositories and selections, creates retention and backup
  policies, assigns them, and validates status output. Tests carry the
  `integration`, `e2e`, and `policy` markers for filtering.
- Added `TIMELOCKER_SHOW_CLI_OUTPUT`-controlled logging helpers plus a shared
  `isolated_cli_environment` fixture in `tests/TimeLocker/cli/conftest.py`
  so multiple CLI suites can reuse the same sandbox setup.
- Fixed CLI regressions in `policy.py`: PolicyManager no longer receives
  unsupported kwargs, backup creation now accepts `--selection` references,
  retention creation passes the expected signature, and assignment commands
  resolve target types/policy types correctly.
- Rules consulted: AGENT-GUIDE-General-Preferences (50),
  AGENT-GUIDE-Operational-Best-Practices (40), AGENT-RULE-Testing-Conventions (25)
  — applied without overrides.

## 3. Implementation Notes

- Key files: `tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py`,
  `tests/TimeLocker/cli/conftest.py`, `src/TimeLocker/cli_modules/commands/policy.py`.
- Helper improvements were reused by the existing selection/backup E2E tests to
  keep behavior consistent between suites.
- Testing: `pytest tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py`,
  `pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`.

## 4. Documentation & Links

- tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py
- src/TimeLocker/cli_modules/commands/policy.py
- pytest.ini (marker reference)

# References

- README.md (CLI overview)
