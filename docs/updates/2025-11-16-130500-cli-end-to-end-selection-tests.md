---
title: "Update: CLI end-to-end selection workflows"
id: "update-cli-end-to-end-selection-tests"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, testing, cli]
links:
  tooling: [pytest]
---

# Update: CLI end-to-end selection workflows

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: Developers
- **Related**: tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- **Scope**: tests/TimeLocker/cli

## 1. Purpose

Extend the CLI test suite with executable user journeys that reflect how operators
configure repositories, define selection templates, and trigger backups. The new
coverage ensures help-only tests are complemented by flows that validate command
interactions and configuration persistence.

## 2. Summary

- Added `test_cli_end_to_end_user_flows.py` with integration-tagged tests that
  orchestrate repository creation, selection template authoring, and backup
  execution.
- Verified repository defaults by exercising the `--set-default` flag and
  asserting `backup create` resolves repositories automatically when not
  specified.
- Introduced lightweight stubs for the backup orchestrator to keep tests
  deterministic while still running the real CLI commands.
- Rules consulted: AGENT-GUIDE-General-Preferences (50), AGENT-RULE-Testing-Conventions (25) — Rules applied: same — Overrides: none.

## 3. Implementation Notes

- Created helper utilities inside the test module to provision isolated HOME,
  XDG config/data directories, add repositories, and author selections.
- Patched `backup` command dependencies with stub service managers to bypass
  heavy orchestrator calls while still verifying emitted job configs.
- Test command: `pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`

## 4. Documentation & Links

- tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- tests/TimeLocker/cli/test_utils.py
- Requirement follow-up: `.kiro/specs/data-selection/requirements.md` (Req 105‑109) are
  implemented in `SelectionManager.estimate_selection_size` / `SelectionPreviewService`
  but lack a dedicated CLI entry point. Next work item is a `tl selections estimate`
  command (or equivalent) that surfaces the byte/file counts, accuracy, and progress
  exposed by `SizeEstimate`.

# References

- README.md (CLI overview)
