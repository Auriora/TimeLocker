---
title: CLI consolidation stabilization traceability
doc_type: spec
artifact_type: traceability
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Traceability Matrix

## Purpose

Provide task-first navigation for the migrated CLI consolidation package.

## Task To Context Matrix

| Task ID | Requirements | Acceptance Criteria | Design Sections | Change Impact | Verification | Durable Targets | Open Decisions |
|---------|--------------|---------------------|-----------------|---------------|--------------|-----------------|----------------|
| T001-T003 | Requirement 1 | AC1-AC2 | Components and Changes | command hierarchy unchanged | Existing Evidence | CLI hierarchy | none |
| T004 | Requirements 1, 3 | R1 AC2, R3 AC1 | Components and Changes | service boundary | Existing Evidence | service-layer docs | none |
| T005 | Requirement 2 | AC1-AC2 | Components; Error Handling | repository resolution | Resolver validation | service-layer and orientation docs | none |
| T006 | Requirement 3 | AC1-AC2 | Interfaces; Migration | service manager | Service-manager validation | service-layer docs | external consumer inventory |
| T007 | Requirement 4 | AC1-AC2 | Components; Data Flow | monitoring integration | Monitoring validation | service-layer and orientation docs | retained monitoring owner |
| T008 | Requirements 1-4 | all | Validation Strategy | validation | Full regression suite | `verification.md` | resolved before validation |
| T009 | Requirements 1-4 | all | Operational Considerations | Promotion Targets | durable-doc review | implementation, orientation, updates | resolved before promotion |
| T010 | Requirements 1-4 | all | Operational Considerations | Promotion Targets | closure checks | lifecycle history | resolved before closure |

## Requirement To Delivery Matrix

| Requirement | Acceptance Criteria | Design Sections | Tasks | Verification | Durable Targets |
|-------------|---------------------|-----------------|-------|--------------|-----------------|
| Requirement 1 | AC1-AC2 | Architecture, Compatibility | T001-T004, T008-T010 | CLI contract tests | CLI hierarchy |
| Requirement 2 | AC1-AC2 | Components, Error Handling | T005, T008-T010 | resolver validation | service-layer docs |
| Requirement 3 | AC1-AC2 | Interfaces, Compatibility | T004, T006, T008-T010 | facade validation | service-layer docs |
| Requirement 4 | AC1-AC2 | Components, Data Flow | T007-T010 | monitoring validation | implementation/orientation docs |

## Correctness Property Coverage

| Property | Requirements | Design Sections | Tasks | Tests Or Verification | Residual Risk |
|----------|--------------|-----------------|-------|-----------------------|---------------|
| CP-001 | Requirement 1 | Architecture | T003, T005-T010 | CLI contract tests per slice | plugin-provided commands |
| CP-002 | Requirement 2 | Data Flow, Error Handling | T005 | parameterized resolver/command tests | backend URI edges |
| CP-003 | Requirement 3 | Interfaces, Compatibility | T006 | facade/service tests | external consumers |

## Design To Implementation Matrix

| Design Section | Requirements | Tasks | Interfaces Or Files | Verification |
|----------------|--------------|-------|---------------------|--------------|
| Components and Changes | Requirements 2-4 | T005-T007 | command, service, facade, monitoring modules | focused tests and searches |
| Error Handling | Requirements 2-4 | T005-T007 | service errors and CLI translations | error-path tests |
| Migration and Compatibility | Requirements 1, 3, 4 | T005-T010 | compatibility delegates | contract and facade tests |
| Validation Strategy | Requirements 1-4 | T005-T010 | test suite and durable docs | recorded commands/results |

## Open Decision Impact

| Decision ID | Blocks | Affected Requirements | Affected Tasks | Resolution Needed |
|-------------|--------|-----------------------|----------------|-------------------|
| D001 | compatibility removal | Requirement 3 | T006 | determine external `CLIServiceManager` consumers |
| D002 | monitoring implementation | Requirement 4 | T007 | choose retained command-facing monitoring owner |

## Maintenance Notes

Reconcile this matrix after each caller inventory and before changing a task's
scope or completion state.
