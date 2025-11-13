# PyYAML Dependency Registration

**Date**: 2025-11-13  
**Type**: Dependency / Test Fix  
**Status**: Complete  
**Owner**: Codex Agent  
**Related**: pytest collection failures for selection + CLI suites  
**Scope**: Core package metadata

## 1. Purpose

Pytest collection aborted because `yaml` (PyYAML) was missing when selection-related modules imported `TimeLocker.selection_template_manager`. This update makes
PyYAML an explicit core dependency so environments created from `pyproject.toml` automatically provide the module.

## 2. Summary

- Added `PyYAML~=6.0` to the `project.dependencies` list in `pyproject.toml`, ensuring `pip install .` pulls the parser.
- Documented the change here per `docs/guides/ai-agent` rules and refreshed the updates index.

## 3. Implementation Notes

- Files touched:
    - `pyproject.toml`: append PyYAML to the runtime dependency list.
    - `docs/updates/index.md`: register this log entry at the top (newest first).
- Testing:
    - `pytest --maxfail 250` *(blocked)* — environment still needs `pip install -e .[dev]` after updating dependencies to pick up PyYAML. Once packages are
      reinstalled, the import error should be resolved.

## 4. Rules Consulted

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md` (priority 50) — dependency change guidance + requirement to log consulted rules.
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md` (priority 20) — mandates logging task-scoped changes under `docs/updates/`.

## 5. Follow-Up

1. Reinstall the project (e.g., `pip install -e '.[dev]'`) so PyYAML becomes available to the active interpreter.
2. Rerun `pytest --maxfail 250` to confirm collection now succeeds.
