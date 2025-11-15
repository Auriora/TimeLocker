---
title: "Update: Test environment isolation"
id: "update-2025-11-15-111812-test-environment-isolation"
type: [ update ]
status: [ draft ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, tests, cli]
links:
  tooling: [pytest]
---

# Update: Test environment isolation

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: User request to stop tests from polluting real config directories
- **Scope**: tests/, scripts/, docs/guides

## 1. Purpose

Ensure automated tests never touch a developer's real `$HOME`/XDG directories and document how to clean any residual state. Previously, pytest never loaded the
`tests/TimeLocker/test_fixtures.py` helpers, so CLI suites inherited real XDG paths and left repositories behind in `/.jbdevcontainer/config/timelocker`.

## 2. Summary

- Registered `tests.TimeLocker.test_fixtures` as a pytest plugin so every test receives the autouse fixtures that rewrite `HOME`, `XDG_*`, and
  `TIMELOCKER_*` to temporary directories and clean them afterwards.
- Taught `scripts/clean-user-environment.sh` (and the companion guide) to honor the actual `XDG_CONFIG_HOME`/`XDG_DATA_HOME` values so manual cleanups remove
  devcontainer paths such as `/.jbdevcontainer/config/timelocker`.

## 3. Implementation Notes

- Updated `tests/conftest.py` to expose the fixture module via `pytest_plugins`, ensuring `ResourceManager`, `isolate_environment`, and related autouse hooks
  run for all suites.
- Added XDG-aware path resolution to `scripts/clean-user-environment.sh` and documented the behavior plus manual cleanup variables in
  `docs/guides/user-environment-cleanup.md`.

## 4. Testing

- `pytest tests/TimeLocker/cli/test_cli_help_tree_walk.py::test_timelocker_command_tree_help_output -q`
- `tl repos list` (returns “No repositories configured” before and after running the above test, confirming the real config directory stays untouched).

## 5. Follow-up

- None.
