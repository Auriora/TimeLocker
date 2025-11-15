---
title: "Update: CLI help tree validation"
id: "update-2025-11-15-094402-cli-help-tree-validation"
type: [ update ]
status: [ draft ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, tests, cli]
links:
  tooling: [pytest]
---

# Update: CLI help tree validation

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: User request for CLI help coverage regression guard
- **Scope**: tests/TimeLocker/cli, docs/updates

## 1. Purpose

Add a regression test that walks the published `timelocker` command tree via the actual entry point to ensure every registered command responds to `--help`
and that curated topics work with `timelocker help <topic>`.

## 2. Summary

- Created a subprocess-based integration test that enumerates the Typer command hierarchy and invokes `timelocker <path> --help` for every command (plus the
  root command) using Python’s entry point bootstrap.
- Added `timelocker help <topic>` coverage for every top-level command (repos, backup, snapshots, config, monitor, etc.) so missing documentation is surfaced
  immediately.
- Expanded `timelocker help` output with new sections for snapshots, config, credentials, security, monitor, logs, reports, and migrate so the new test passes
  and users have consistent guidance.
- Parallelized help invocations with a thread pool so the new test completes within a minute even though it touches 100+ commands.

## 3. Implementation Notes

- Added `tests/TimeLocker/cli/test_cli_help_tree_walk.py` with helpers to collect the command graph via `typer.main.get_command`, spawn the actual CLI
  entry point, and assert on exit codes/output.
- Ensured subprocesses inherit a `PYTHONPATH` seeded with `src/` and a fixed `COLUMNS` width to get deterministic Rich output.
- Recorded this update and linked it from `docs/updates/index.md`.
- Updated `src/TimeLocker/cli.py` to provide dedicated topic help for snapshots, config, credentials, security, monitor, logs, reports, and migrate and
  refreshed the main help banner so users discover those namespaces.
- Added a `TIMELOCKER_HELP_TREE_VERBOSE=1` escape hatch so running the test with `-s` streams each command’s stdout/stderr for debugging, and rebuilt the CLI
  subprocess environment on every invocation so it always honors the per-test XDG/TIMELOCKER overrides instead of touching developer machines.

## 4. Documentation & Links

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md`
- `docs/guides/ai-agent/AGENT-RULE-Testing-Conventions.md`

## 5. Testing

- `pytest tests/TimeLocker/cli/test_cli_help_tree_walk.py`

## 6. Rules Consulted

- `AGENT-GUIDE-General-Preferences` (priority 50) — repository-wide coordination instructions and requirement to log applied rules.
- `AGENT-RULE-Testing-Conventions` (priority 25) — dictates placement and structure for new tests.
