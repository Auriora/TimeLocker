---
title: "Update: TimeLocker Doc/Code Alignment Findings"
id: "update-2026-05-06-171653-timelocker-doc-code-alignment-findings"
type: [ update ]
status: [ draft ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, docs, service-facade, alignment, implementation-plan]
links:
  tooling: [python-agent-ide, basedpyright, ruff]
---

# Update: TimeLocker Doc/Code Alignment Findings

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/3-implementation/service-facade.md`, `docs/2-architecture/integration-layer.md`, `src/TimeLocker/utils/service_facade.py`
- **Scope**: ServiceFacade docs, CLI service access, dependency declarations, static diagnostics

## 1. Purpose

Record doc/code alignment findings from the TimeLocker exploration pass so they can be implemented or triaged later. This note captures project findings only;
Agent IDE tool feedback is intentionally excluded from local documentation.

## 2. Summary

The ServiceFacade implementation documentation is mostly aligned with the current public API, but one architecture document still describes capabilities that
do not exist in code. Static diagnostics also surfaced several implementation issues that should be handled before treating the ServiceFacade layer as fully
stable.

## 3. Implementation Notes

- The ServiceFacade API reference in `docs/3-implementation/service-facade.md` broadly matches the methods implemented by
  `src/TimeLocker/utils/service_facade.py`, including service getters, `initialize_services`, `health_check`, `get_service_status`,
  `shutdown_services`, and `create_service_facade`.
- `docs/2-architecture/integration-layer.md` shows stale ServiceFacade usage with `with ServiceFacade(config_dir) as facade`,
  `facade.list_repositories()`, and `facade.execute_backup(policy_id)`. The current `ServiceFacade` implementation does not define `__enter__`,
  `__exit__`, `list_repositories`, or `execute_backup`.
- `ServiceFacade.health_check()` is annotated as `Dict[str, bool]`, but its exception path returns an `error` string alongside boolean service statuses.
  Either the return type and docs should be widened, or the error representation should be changed to keep the declared bool-only shape.
- The fallback path in `ServiceFacade.get_restore_service()` calls `RestoreManager()` with no arguments. Static diagnostics reported this as a missing
  required `repository` argument, so the restore fallback should be verified and fixed before relying on it.
- CLI modules import `click` directly while `pyproject.toml` declares `typer` but not `click`. If direct `click` usage remains intentional, add it as an
  explicit runtime dependency instead of relying on Typer's transitive dependency.
- Static diagnostics over `src/TimeLocker/utils/service_facade.py`, `src/TimeLocker/cli_modules/commands/base.py`, and
  `src/TimeLocker/cli_modules/commands/monitoring.py` reported error-level issues, including monitoring type mismatches, an import cycle involving CLI
  command modules, and Ruff E402 import-order findings.

## 4. Suggested Follow-Up

- Update `docs/2-architecture/integration-layer.md` to remove or replace stale ServiceFacade context-manager and facade-operation examples.
- Decide whether ServiceFacade should gain context-manager support. If yes, implement and test it before documenting it as an architectural feature.
- Add focused tests for `ServiceFacade.get_restore_service()` fallback behavior and `ServiceFacade.health_check()` error behavior.
- Add `click` to runtime dependencies or remove direct imports if Typer-only usage is preferred.
- Re-run static diagnostics and nearby ServiceFacade tests after implementation changes.

## 5. Documentation & Links

- `docs/3-implementation/service-facade.md`
- `docs/2-architecture/integration-layer.md`
- `src/TimeLocker/utils/service_facade.py`
- `src/TimeLocker/cli_modules/commands/base.py`
- `src/TimeLocker/cli_modules/commands/monitoring.py`

# References

- Agent exploration pass on 06-05-2026
