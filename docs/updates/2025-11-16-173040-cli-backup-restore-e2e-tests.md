---
title: "Update: CLI backup + restore E2E workflows"
id: "update-cli-backup-restore-e2e-tests"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, testing, cli, backup, restore]
links:
  tooling: [pytest]
---

# Update: CLI backup + restore E2E workflows

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: Developers
- **Related**: tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- **Scope**: tests/TimeLocker/cli

## 1. Purpose

Backfill realistic CLI end-to-end workflows so backup and restore scenarios are
validated the same way the `tl --help` coverage verifies surface-level output.
The goal is to exercise repository setup, selection authoring, backup
invocation, snapshot inspection, and targeted file restoration with the real
command surface while keeping orchestration deterministic.

## 2. Summary

- Added reusable helpers for running `backup create` with the stub orchestrator
  and for configuring restore patches backed by realistic snapshot metadata.
- Introduced two new E2E tests that list/browse snapshots and restore files
  after performing a selection-backed backup flow, ensuring `backup`, `restore`,
  `integration`, and `e2e` markers are all present for filtering.
- Updated existing tests to share the helpers and documented rule compliance.
- Rules consulted: AGENT-GUIDE-General-Preferences (50),
  AGENT-GUIDE-Operational-Best-Practices (40), AGENT-RULE-Testing-Conventions (25)
  — Applied without overrides.

## 3. Implementation Notes

- Key paths: tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
  (new helpers, tagging, and restore workflows).
- CLI restore dependencies are patched via `patch_restore_commands` with
  contextual metadata so commands render realistic tables without touching real
  repositories.
- Testing: `pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`

## 4. Documentation & Links

- tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py
- pytest.ini (marker definitions)

# References

- README.md (CLI usage overview)
