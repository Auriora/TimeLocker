---
title: "Update: CLI Static Analysis Five-Slice Cleanup"
id: "update-2026-05-06-202457-cli-static-analysis-five-slice-cleanup"
type: [ update ]
status: [ draft ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, cli, static-analysis, policy, backup, repositories]
links:
  tooling: [python-agent-ide, basedpyright, ruff, pytest]
---

# Update: CLI Static Analysis Five-Slice Cleanup

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers
- **Related**: `policy.py`, `backup.py`, `repositories.py`
- **Scope**: CLI command static-analysis cleanup

## 1. Purpose

Track and implement the next five narrow static-analysis cleanup slices identified from Python Agent IDE diagnostics.

## 2. Summary

The task covers typed policy creation/list boundaries, small backup command warning cleanup, safe use of the backup `--latest` option, and repository show-command
mapping/object normalization.

## 3. Implementation Notes

- [x] `policy.py` typed policy creation boundaries.
- [x] `policy.py` policy list display boundary.
- [x] `backup.py` simple static cleanup.
- [x] `backup.py` option/parameter cleanup for `--latest`.
- [x] `repositories.py` show-command boundary.
- [x] Targeted diagnostics and tests.

Validation performed:

- `python -m py_compile src/TimeLocker/cli_modules/commands/policy.py src/TimeLocker/cli_modules/commands/backup.py src/TimeLocker/cli_modules/commands/repositories.py`
- Python Agent IDE diagnostics:
  - `policy.py`: 0 errors, 47 warnings.
  - `backup.py`: 0 errors, 24 warnings.
  - `repositories.py`: 0 errors, 285 warnings.
- `python -m pytest tests/TimeLocker/cli/test_repos_commands.py -q`: 26 passed.
- `python -m pytest tests/TimeLocker/cli/test_backup_commands.py tests/TimeLocker/cli/test_backup_data_selection_integration.py -q`: 29 passed.
- CLI help smoke checks for `backup verify`, `policy backup list`, and `repos show` passed.
- `git diff --check` passed.

Known unrelated validation failures:

- `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py -q` still fails while adding repositories with `Repository '<name>' not found`.
- `python -m pytest tests/TimeLocker/cli -q -k 'backup or policy'` also hits existing E2E failures around repository add setup and a missing
  `backup.get_cli_service_manager` patch target.

## 4. Documentation & Links

- Updated this task-scoped implementation note and `docs/updates/index.md`.

# References

- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
