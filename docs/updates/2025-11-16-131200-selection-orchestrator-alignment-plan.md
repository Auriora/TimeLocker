---
title: "Update: Selection orchestration alignment plan"
id: "update-selection-orchestrator-plan"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, planning, cli, backup]
links:
  tooling: []
---

# Update: Selection orchestration alignment plan

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: Developers
- **Related**: src/TimeLocker/services/backup_orchestrator.py, src/TimeLocker/services/data_selection_integration_service.py
- **Scope**: selection/orchestration workflow

## 1. Purpose

Document the implementation plan for enabling the real backup orchestrator to fully
support selection-driven dry runs and ensure consistent selection handling across
all integration points (CLI, policy automation, background jobs).

## 2. Plan Summary

1. **Scope & Identifier Audit**
   - Inventory each call site that loads selection templates (CLI, policy simulators,
     scheduling/automation suites) and confirm whether they expect names or IDs.
2. **Template Retrieval Contract**
   - Decide on synchronous vs async API for `SelectionTemplateManager` and update
     all consumers accordingly (current `DataSelectionIntegrationService` usage is
     incorrect and returns coroutines).
3. **Normalize Selection IDs**
   - When the CLI accepts `--selection <name>`, resolve the canonical template ID
     before constructing `BackupJobConfig`, store both ID and display name in metadata,
     and ensure orchestrator validation/prep use the same identifier.
4. **Service-Manager Entry Point**
   - Expose an official `CLIServiceManager.run_selection_backup(...)` (or similar)
     that builds the job config and calls `BackupOrchestrator.execute_backup_job`,
     removing direct access to `_backup_orchestrator`.
5. **Dry-Run Validation**
   - After the above fixes, run the real dry-run flow and ensure `_execute_job_dry_run`
     enumerates the selected paths and reports file/byte counts; add regression tests
     (CLI + orchestrator-level) that exercise this path.
6. **Broader Fix Propagation**
   - Apply the same template-retrieval and identifier fixes to other modules that
     integrate selections (policy engine, retention workflows, restore planners) to
     keep behavior consistent across the app.
7. **Documentation & Tracking**
   - Update developer docs describing the new API and selection identifier flow and
     log the change once implemented.

- Rules consulted: AGENT-GUIDE-General-Preferences (50), AGENT-RULE-Documentation-Conventions (20)
  — Rules applied: same — Overrides: none.

### Spec Alignment & Follow-Ups

- `.kiro/specs/backup-operations/requirements.md`
  - **Req 105‑109** (selection integration, translation, compatibility warnings) and
    **Req 141‑145/155** (CLI selection usage and help) are satisfied only after the
    orchestrator uses real templates, surfaces unsupported-rule warnings, and help
    text favors selection templates over legacy targets.
- `.kiro/specs/data-selection/requirements.md`
  - **Req 125** (integrate selections into backup workflows) relies on the same fixes
    to SelectionTemplateManager access and identifier flow.
- `.kiro/specs/recovery-operations/requirements.md`
  - **Req 7** demands that recovery operations reuse data selection templates with
    compatibility validation and warnings for unmatched patterns. The recovery path
    needs the same template retrieval/ID normalization work plus tests.
- `.kiro/specs/scheduling-automation` / `.kiro/specs/policy-management`
  - Scheduling and policy engines that invoke selections must be audited for the
    coroutine bug and migrated to the corrected service-manager API.

Outstanding follow-up work:
1. Propagate the template retrieval/ID normalization fixes to recovery, scheduling,
   and policy modules.
2. Ensure unsupported-selection warnings bubble up through CLI output (req 108‑109).
3. Review CLI help/examples to remove references to deprecated backup targets (req 155).

## 3. Implementation Notes

- Prioritize fixing the async/sync mismatch first; other work depends on being able to
  retrieve a real template object from `SelectionTemplateManager`.
- When updating the CLI, keep the existing tests for stubbed orchestrators until the
  real flow is proven, then migrate tests to use the genuine service path.

## 4. Documentation & Links

- src/TimeLocker/selection_template_manager.py
- src/TimeLocker/services/data_selection_integration_service.py
- src/TimeLocker/services/backup_orchestrator.py

# References

- README.md (CLI overview)
