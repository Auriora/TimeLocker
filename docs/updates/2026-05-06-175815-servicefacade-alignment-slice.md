---
title: "Update: ServiceFacade Alignment Slice"
id: "update-2026-05-06-175815-servicefacade-alignment-slice"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, service-facade, docs, tests, dependencies]
links:
  tooling: [python-agent-ide, pytest, ruff, basedpyright]
---

# Update: ServiceFacade Alignment Slice

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/updates/2026-05-06-171653-timelocker-doc-code-alignment-findings.md`
- **Scope**: ServiceFacade implementation, tests, architecture docs, runtime dependencies

## 1. Purpose

Implement the ServiceFacade follow-up slice identified during the doc/code alignment pass.

## 2. Summary

ServiceFacade now supports context-manager lifecycle usage, keeps `health_check()` in a bool-only result shape, and no longer attempts to construct
`RestoreManager` without a repository. Documentation now reflects the current service-access contract instead of showing facade-owned domain operations.

## 3. Implementation Notes

- Added `ServiceFacade.__enter__()` and `ServiceFacade.__exit__()` so context-manager usage initializes and shuts down services.
- Changed `get_restore_service()` to return configured `restore_service` or `recovery_orchestrator` only.
- Changed restore-service absence to a clear `ServiceAccessError` instead of calling `RestoreManager()` without its required repository.
- Normalized `health_check()` results to `dict[str, bool]`, including the failure path.
- Added `click` as an explicit runtime dependency because CLI modules import it directly.
- Updated ServiceFacade tests for context-manager behavior, bool-only health failure, and restore-service absence.
- Updated architecture and implementation docs to remove stale facade-owned `list_repositories()` and `execute_backup()` examples.
- Validation:
  - `diagnostics_for_files` on `src/TimeLocker/utils/service_facade.py` and `tests/TimeLocker/utils/test_service_facade.py`: 0 error-level findings.
  - `python -m pytest tests/TimeLocker/utils/test_service_facade.py -q`: 28 passed.

## 4. Documentation & Links

- `src/TimeLocker/utils/service_facade.py`
- `tests/TimeLocker/utils/test_service_facade.py`
- `docs/2-architecture/integration-layer.md`
- `docs/3-implementation/service-facade.md`
- `pyproject.toml`

# References

- `docs/updates/2026-05-06-171653-timelocker-doc-code-alignment-findings.md`
