---
title: System CLI, tray, retention, and control traceability
doc_type: spec
artifact_type: traceability
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Traceability Matrix

## Purpose

Map Spec 009 requirements, design, tasks, verification, and durable promotion
targets. Reconcile this matrix whenever any linked artifact changes.

## Task To Context Matrix

| Task ID | Requirements | Acceptance Criteria | Design Sections | Change Impact | Verification | Durable Targets | Open Decisions |
|---------|--------------|---------------------|-----------------|---------------|--------------|-----------------|----------------|
| T001 | Requirement 2, Requirement 4, Requirement 5, Requirement 6 | Requirement 2 AC4; Requirement 2 AC5; Requirement 2 AC6; Requirement 4 AC1; Requirement 4 AC2; Requirement 4 AC3; Requirement 4 AC4; Requirement 4 AC5; Requirement 4 AC6; Requirement 4 AC7; Requirement 4 AC9; Requirement 4 AC10; Requirement 4 AC11; Requirement 5 AC1; Requirement 5 AC2; Requirement 5 AC5; Requirement 5 AC6; Requirement 5 AC7; Requirement 5 AC8; Requirement 6 AC5 | Decisions D002-D005; Data Models; Interfaces | Protocol, authorization, run visibility | V1, V2 | System requirements, architecture, CLI reference | none |
| T002 | Requirement 4, Requirement 5, Requirement 6 | Requirement 4 AC2; Requirement 4 AC3; Requirement 4 AC5; Requirement 4 AC6; Requirement 4 AC10; Requirement 4 AC11; Requirement 5 AC4; Requirement 5 AC5; Requirement 5 AC6; Requirement 5 AC11; Requirement 6 AC6 | Run store; Atomic transition; Error Handling | Run records and recovery | V1, V3 | System and scheduling architecture | none |
| T003 | Requirement 2, Requirement 4 | Requirement 2 AC2; Requirement 2 AC3; Requirement 2 AC4; Requirement 2 AC5; Requirement 2 AC6; Requirement 4 AC1; Requirement 4 AC4; Requirement 4 AC5; Requirement 4 AC6; Requirement 4 AC7; Requirement 4 AC8; Requirement 4 AC9; Requirement 4 AC10; Requirement 4 AC11 | D001-D004; Authorization; Security | Operator authorization | V2, V4 | Requirements, architecture, installation | none |
| T004 | Requirement 2, Requirement 4, Requirement 5, Requirement 6 | Requirement 2 AC4; Requirement 4 AC8; Requirement 4 AC9; Requirement 4 AC10; Requirement 4 AC11; Requirement 5 AC8; Requirement 6 AC5 | Downstream Task Guidance | All security-sensitive deltas | V1-V4, V11 | none | none |
| T005 | Requirement 1, Requirement 2, Requirement 6 | Requirement 1 AC1; Requirement 1 AC2; Requirement 1 AC3; Requirement 1 AC4; Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3; Requirement 2 AC4; Requirement 2 AC5; Requirement 2 AC6; Requirement 6 AC1; Requirement 6 AC2; Requirement 6 AC3 | D004; Launcher; Migration | System launcher/elevation | V5, V9 | Installation, version management | none |
| T006 | Requirement 4 | Requirement 4 AC1; Requirement 4 AC2; Requirement 4 AC3; Requirement 4 AC6; Requirement 4 AC8; Requirement 4 AC9; Requirement 4 AC10; Requirement 4 AC11 | D002, D003, D005; Protected read | Local/system log split | V2, V6 | Requirements, CLI reference, troubleshooting | none |
| T007 | Requirement 3, Requirement 4, Requirement 6 | Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3; Requirement 3 AC4; Requirement 3 AC5; Requirement 3 AC6; Requirement 3 AC7; Requirement 3 AC8; Requirement 4 AC1; Requirement 4 AC4; Requirement 4 AC5; Requirement 4 AC6; Requirement 4 AC7; Requirement 4 AC8; Requirement 4 AC9; Requirement 6 AC1; Requirement 6 AC2; Requirement 6 AC3; Requirement 6 AC4; Requirement 6 AC5 | D006; Tray status; Migration | Independent tray | V7, V9 | Architecture, tray setup, installation | none |
| T008 | Requirement 5, Requirement 6 | Requirement 5 AC1; Requirement 5 AC2; Requirement 5 AC3; Requirement 5 AC4; Requirement 5 AC5; Requirement 5 AC6; Requirement 5 AC7; Requirement 5 AC8; Requirement 5 AC9; Requirement 5 AC10; Requirement 5 AC11; Requirement 6 AC1; Requirement 6 AC2; Requirement 6 AC3; Requirement 6 AC6 | D007; Backup-triggered retention | Retention automation | V3, V8 | Scheduling architecture and guide | none |
| T009 | Requirement 1, Requirement 2, Requirement 3, Requirement 6 | Requirement 1 AC1; Requirement 1 AC2; Requirement 1 AC3; Requirement 1 AC4; Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3; Requirement 3 AC6; Requirement 3 AC7; Requirement 3 AC8; Requirement 6 AC1; Requirement 6 AC2; Requirement 6 AC3; Requirement 6 AC4; Requirement 6 AC5; Requirement 6 AC6 | Migration; Slice Boundary | Package/install migration | V5, V7, V9 | Installation and version management | none |
| T010 | Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5, Requirement 6 | SC-001; SC-002; SC-003; SC-004; SC-005; SC-006; SC-007; SC-008; SC-009; SC-010; SC-011 | Operational Considerations | Live operational behavior | V10 | Operator guides and verification | rollout approval |
| T011 | Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5, Requirement 6 | All accepted criteria promoted after evidence | Related Artifacts | Promotion Targets | V12 | All promotion targets | none |
| T012 | Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5, Requirement 6 | All accepted criteria reconciled before closure | Validation Strategy | All | V1-V12 | Closure/history records | closure approval |

## Requirement To Delivery Matrix

| Requirement | Priority | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets | Coverage State | Residual Destination |
|-------------|----------|---------------------|-----------------|-------|--------------|-----------------|----------------|----------------------|
| Requirement 1 | must-have | AC1-AC4 | D004; System launcher; Migration | T005, T009, T010 | V5, V9, V10 | Installation, version management | complete | none |
| Requirement 2 | must-have | AC1-AC6 | D003-D004; Action classifier; Security | T001, T003-T005, T010 | V2, V4, V5, V10 | System requirements/architecture | complete | none |
| Requirement 3 | must-have | AC1-AC8 | D006; Independent tray; Tray status | T007, T009, T010 | V7, V9, V10 | Architecture and tray setup | complete | none |
| Requirement 4 | must-have | AC1-AC11 | D001-D005; Local server; Models; Protected read | T001-T004, T006, T010 | V1-V4, V6, V10 | Requirements, architecture, CLI/troubleshooting | complete | none |
| Requirement 5 | must-have | AC1-AC11 | D007; Run store; Backup-triggered retention | T001-T002, T004, T008, T010 | V1, V3, V8, V10 | Requirements and scheduling docs | complete | none |
| Requirement 6 | must-have | AC1-AC6 | Platform adapters; Migration; Reconciliation | T001-T002, T007-T010 | V1, V3, V7, V9, V10 | Architecture, installation, version management | complete | none |

## Correctness Property Coverage

| Property | Requirements | Design Sections | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-----------------|-------|-----------------------|---------------|
| CP-001 | R2 | D004; Action classifier | T001, T003, T005 | V2, V5 | Live platform authorization |
| CP-002 | R3 | D006; Independent tray | T007 | V7, V10 | Desktop diversity |
| CP-003 | R4, R5 | Run store and lock | T002, T008 | V3, V8 | Production timing |
| CP-004 | R4, R5 | RunRecord state machine | T001-T002, T006, T008 | V1, V3, V6, V8 | none after evidence |
| CP-005 | R5 | D007; SystemPolicy | T001, T008 | V1, V8 | Operator policy accuracy |
| CP-006 | R2, R4 | Authorization before dispatch | T001, T003, T005-T006 | V2, V4-V6 | none after evidence |
| CP-007 | R4 | D001, D003; Authorization | T003, T006 | V2, V4, V10 | NSS/platform variance |
| CP-008 | R6 | Reconciliation algorithm | T002, T009-T010 | V3, V9-V10 | Crash timing |
| CP-009 | R3, R6 | Platform adapter contracts | T001, T007, T009 | V1, V7, V9 | Windows live follow-up |
| CP-010 | R5 | D007; trigger idempotency | T002, T008 | V3, V8, V10 | none after evidence |
| CP-011 | R4 | D002-D003; response projection | T001, T003, T006 | V1-V2, V4, V6, V10 | Redaction completeness |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification | Coverage State | Residual Destination |
|----------------|--------------|-------|---------------------|--------------|----------------|----------------------|
| Decisions D001-D005 | R1, R2, R4 | T001, T003, T005-T006 | `system_control`, CLI, install assets | V1-V6 | not-covered | T001 |
| Decision D006 and independent tray | R3, R4 | T007, T009 | monitoring/tray/platform modules | V7, V9-V10 | not-covered | T007 |
| Decision D007 and retention flow | R5 | T002, T008 | retention/scheduling modules | V3, V8, V10 | not-covered | T008 |
| Migration and compatibility | R1-R6 | T005, T007-T010 | install/release/system assets | V9-V10 | not-covered | T009 |
| Durable promotion | R1-R6 | T011-T012 | `docs/` targets | V12 | not-covered | T011 |

## Open Decision Impact

| Decision ID | Blocks | Affected Requirements | Affected Tasks | Resolution Needed |
|-------------|--------|-----------------------|----------------|-------------------|
| Live rollout approval | T010 only | R1-R6 | T010 | Explicit approval before host mutation |
| Closure approval | Closure only | R1-R6 | T012 | Review and evidence complete |

## Maintenance Notes

- `R1` through `R6` abbreviate Requirement 1 through Requirement 6.
- `V1` through `V12` identify verification gates in `verification.md`.
- `complete` in the requirement-delivery matrix means every accepted criterion
  has an explicit design, task, verification, and durable-target mapping. It
  does not claim implementation completion.
- Implementation and verification evidence remains pending in `tasks.md` and
  `verification.md`; update those states only from executed evidence.

## Reconciliation

Reviewed against the 2026-07-26 requirements and design revisions. Every
Requirement 1-6 acceptance criterion has an explicit task mapping, including
Requirement 4 AC10-AC11 and the tightened security constraints. No
implementation-completion claim is made.
