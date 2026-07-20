---
title: NPBackup migration parity traceability
doc_type: spec
artifact_type: traceability
status: active
owner: Auriora Team
last_reviewed: 2026-07-20
---

# Traceability Matrix

## Task To Context Matrix

| Task ID | Requirements | Acceptance Criteria | Design Sections | Verification | Durable Targets | Open Decisions |
|---------|--------------|---------------------|-----------------|--------------|-----------------|----------------|
| T001 | Requirement 1, Requirement 2, Requirement 3 | all | Overview; Operational Considerations | host and lifecycle discovery | spec package | none |
| T002 | Requirement 1 | AC1-AC4 | Overview; Low-Level Design; Compatibility | CLI, service, target, and Restic tests | backup operations guide | none |
| T003 | Requirement 2 | AC1-AC4 | High-Level Design; Compatibility | schedule and renderer tests | scheduling guide | none |
| T004 | Requirement 1, Requirement 2, Requirement 3 | R1-R2 all; R3 AC1 | Validation And Failure Handling | Phase 1 checkpoint | both guides | none |
| T005 | Requirement 3 | AC2 | Security And Rollback | credential-path review | installation guidance | D001 resolved |
| T006 | Requirement 3 | AC2-AC3 | Operator Staging Design | version, list, and restore | installation and recovery guides | none |
| T007 | Requirement 1, Requirement 3 | R1 AC5; R3 AC3-AC4 | Low-Level Design; Operator Staging Design | focused parity tests, scheduled runs, and restore | backup and scheduling guides | none |
| T008 | Requirement 3 | AC4 | Security And Rollback | operator decision and guarded cutover | scheduling guide | D002 resolved |

## Requirement To Delivery Matrix

| Requirement | Priority | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets | Coverage State | Residual Destination |
|-------------|----------|---------------------|-----------------|-------|--------------|-----------------|----------------|----------------------|
| Requirement 1 | must-have | AC1-AC5 | Overview; Low-Level Design | T002, T004, T007 | focused and normal-profile backup tests; live migrated command | recovery operations guide | complete | none |
| Requirement 2 | must-have | AC1-AC4 | High-Level Design; Compatibility | T003, T004 | schedule and renderer tests | scheduling guide | complete | none |
| Requirement 3 | must-have | AC1-AC4 | Operational Considerations; Security And Rollback | T004-T008 | host comparison, restore, observation, and guarded cutover | installation and scheduling guides | complete | none |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification | Coverage State | Residual Destination |
|----------------|--------------|-------|---------------------|--------------|----------------|----------------------|
| Overview and Low-Level Design | Requirement 1 | T002 | backup CLI, request, target, orchestrators, Restic adapter | focused and normal-profile backup tests | complete | none |
| High-Level Design and Compatibility | Requirement 2 | T003 | schedule commands, records, renderers | schedule tests and parser round trip | complete | none |
| Operational Considerations | Requirement 3 | T004-T008 | docs, root-owned installation, timer | host comparison, list, restore, observed runs, and guarded cutover | complete | none |

## Open Decision Impact

| Decision ID | Blocks | Affected Requirements | Affected Tasks | Resolution Needed |
|-------------|--------|-----------------------|----------------|-------------------|
| D001 (resolved 2026-07-19) | none | Requirement 3 | T005-T006 | Operator approved root-owned mode-0600 `/etc/timelocker/npbackup-migration.env`; no values enter repository evidence. |
| D002 (resolved 2026-07-20) | none | Requirement 3 | T008 | Operator selected option 2: retain the active TimeLocker timer and disable the single NPBackup cron entry, preserving a root-only crontab rollback artifact. Retention remains manual and outside this cutover decision. |

## Open Gate

T001-T008 are complete. The TimeLocker backup timer is active and the NPBackup
cron entry is disabled with a recoverable crontab backup. Automatic retention
is not configured and must be handled as separate follow-on work.
