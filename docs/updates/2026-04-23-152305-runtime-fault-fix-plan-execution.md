---
title: "Update: Runtime fault fix plan execution"
id: "update-2026-04-23-152305-runtime-fault-fix-plan-execution"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [update, cli, backup, config, static-analysis]
links:
  tooling: [pytest, compileall]
---

# Update: Runtime fault fix plan execution

- **Owner**: Codex
- **Created Date**: 23-04-2026
- **Audience**: Developers
- **Related**: Static-analysis fault triage and fix plan execution
- **Scope**: `src/TimeLocker`, `docs/updates`

## 1. Purpose

Execute the previously defined fix plan for high-confidence runtime faults found during static analysis, then verify the repaired command paths and model contracts with targeted tests.

## 2. Summary

The implementation removed two concrete CLI runtime faults, repaired several backup snapshot contract mismatches, and tightened one repository interface seam that had drifted from its callers.

The main command-path changes were:

- `backup` commands now use the existing `_get_service_manager_for_command(...)` helper instead of calling an undefined `get_cli_service_manager(...)`.
- `config` commands now import `setup_logging` explicitly and use package-correct imports for configuration helpers.

The main model/interface changes were:

- `BackupSnapshot` now initializes `tags` and `size`, uses modern built-in generic annotations, and exposes a `delete()` return type aligned with repository behavior.
- `BackupSnapshot.from_dict()` keeps the legacy `Path` behavior expected by current tests while using a typed mapping input.
- `BackupRepository` now exposes `verify_backup(...)` as a defined method instead of relying on interface drift.
- `application_preset_manager.py` no longer rebinds a class constant through an instance attribute.

## 3. Implementation Notes

- Updated [src/TimeLocker/cli_modules/commands/backup.py](../../src/TimeLocker/cli_modules/commands/backup.py)
- Updated [src/TimeLocker/cli_modules/commands/config.py](../../src/TimeLocker/cli_modules/commands/config.py)
- Updated [src/TimeLocker/backup_snapshot.py](../../src/TimeLocker/backup_snapshot.py)
- Updated [src/TimeLocker/backup_repository.py](../../src/TimeLocker/backup_repository.py)
- Updated [src/TimeLocker/application_preset_manager.py](../../src/TimeLocker/application_preset_manager.py)

Testing performed:

```bash
python3 -m compileall -q src/TimeLocker
python3 -m pytest -q tests/TimeLocker/backup/test_snapshot.py tests/TimeLocker/backup/test_manager.py tests/TimeLocker/cli/test_backup_commands.py tests/TimeLocker/cli/test_config_commands.py tests/TimeLocker/cli/test_config_export_import.py
```

Results:

- `compileall` passed
- `pytest` passed: `76 passed`

Follow-up notes:

- This change set intentionally avoided a broad import-cycle refactor. The highest-confidence runtime faults were fixed first, with structural cleanup left as separate work.

## 4. Documentation & Links

- Added this task-scoped implementation log in `docs/updates/`
- Updated [docs/updates/index.md](./index.md)

# References

- [docs/updates/index.md](./index.md)
