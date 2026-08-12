---
title: Event-driven tray status traceability
doc_type: spec
artifact_type: traceability
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Traceability Matrix

## Task To Context Matrix

| Task | Requirements | Acceptance criteria | Design coverage | Verification | Durable targets |
|------|--------------|---------------------|-----------------|--------------|-----------------|
| T001 | Requirement 1, Requirement 2, Requirement 3, Requirement 7 | Requirement 1 AC4-AC5; Requirement 2 AC3; Requirement 3 AC1-AC5; Requirement 7 AC1 | Data Models, Function Signatures | V1, V2 | requirements, architecture |
| T002 | Requirement 2, Requirement 3, Requirement 4 | Requirement 2 AC1, AC3-AC5; Requirement 3 AC1-AC4; Requirement 4 AC5 | Control Protocol, Snapshot Builder | V1, V3 | requirements, implementation |
| T003 | Requirement 1, Requirement 2, Requirement 4 | Requirement 1 AC3-AC5; Requirement 2 AC2-AC3; Requirement 4 AC2-AC3 | Event Broker, Change Sources | V2, V4 | architecture, implementation |
| T004 | Requirement 1-Requirement 4 | Phase 1 criteria | Validation Strategy | V1-V4 | none |
| T005 | Requirement 1, Requirement 2, Requirement 4, Requirement 7 | Requirement 1 AC1-AC5; Requirement 2 AC1-AC5; Requirement 4 AC1-AC5; Requirement 7 AC1-AC3 | Linux Transport, Tray Client, Security | V2-V5 | architecture, tray setup |
| T006 | Requirement 3, Requirement 5, Requirement 6 | all | Tray Presentation, Error Handling | V1, V5, V6 | tray setup, reference, troubleshooting |
| T007 | Requirement 1-Requirement 6 | Phase 2 criteria | Data Flow, Failure Handling | V1-V6 | none |
| T008 | Requirement 2, Requirement 4, Requirement 7 | Requirement 2 AC1-AC5; Requirement 4 AC3-AC5; Requirement 7 AC1, AC3 | Windows Event Contract | V3, V7 | requirements, architecture |
| T009 | Requirement 4, Requirement 7 | Requirement 4 AC5; Requirement 7 AC2, AC4-AC5 | Migration and Compatibility | V8, V9 | installation, version management |
| T010 | Requirement 5, Requirement 7 | Requirement 5 AC6; Requirement 7 all | Tray Presentation, Operational Considerations | V5, V8, V9 | tray setup |
| T011 | Requirement 1-Requirement 7 | all Linux acceptance criteria, including external-worker invalidation, Requirement 3 AC6-AC7, Requirement 5 AC1 and AC7 | Complete Linux flow | V10 | operational docs |
| T012 | Requirement 1-Requirement 7 | review disposition | Security, Reliability, Portability | V11 | all promotion targets |
| T013 | Requirement 1-Requirement 7 | all | Promotion and Closure | V12-V15 | all promotion targets and history |

## Requirement To Delivery Matrix

| Requirement | Priority | Tasks | Verification gates | Durable targets | Coverage State | Residual Destination |
|-------------|----------|-------|--------------------|-----------------|----------------|----------------------|
| Requirement 1 | must-have | T001, T003-T005, T007, T011-T013 | V1, V2, V4, V5, V10 | requirements, architecture, tray setup | partial-routed | Human decision superseded resident event delivery; reusable snapshot semantics are retained and daemonless delivery is routed to Spec 011 Requirement 9. |
| Requirement 2 | must-have | T001-T005, T007-T008, T011-T013 | V1-V5, V7, V10-V11 | requirements, architecture | partial-routed | Human decision superseded continuous resident authorization; allowlisted models are retained and bounded authentication is routed to Spec 011. |
| Requirement 3 | must-have | T001-T002, T006-T007, T011-T013 | V1, V5-V6, V10 | requirements, tray setup | complete | Last-success, health/activity separation, schedule health, local tray projection, and `Never` fallback are implemented and regression-tested. |
| Requirement 4 | must-have | T002-T005, T007-T011, T013 | V2-V5, V7-V10 | architecture, troubleshooting | partial-routed | Human decision superseded resident reconnect and heartbeat behavior; process independence and daemonless resilience are routed to Spec 011. |
| Requirement 5 | must-have | T006-T007, T010-T013 | V5, V6, V8-V10 | tray setup, command reference | complete | Honest three-row presentation, actions, deterministic non-colour-only badges, and connecting state passed local and package checks. |
| Requirement 6 | must-have | T006-T007, T011-T013 | V6, V10 | tray setup, troubleshooting | partial-routed | One-shot output silence is retained; human decision superseded idle resident service operation and zero-idle acceptance is routed to Spec 011 Requirement 9. |
| Requirement 7 | must-have | T001, T005, T008-T013 | V1-V3, V7-V11, V13 | requirements, architecture, installation | partial-routed | Human decision superseded rollout of the resident architecture; supported daemonless deployment and remaining platform acceptance are routed to Spec 011. |

## Correctness Property Coverage

| Property | Requirements | Tasks | Tests or verification | Residual risk |
|----------|--------------|-------|-----------------------|---------------|
| CP-001 | Requirement 3 | T001, T002, T006, T011 | V1 permutation coverage passed; backend, tray, and live evidence pending | none after live evidence |
| CP-002 | Requirement 1, Requirement 4 | T001, T003, T005, T008 | V1 strict revision ordering passed; broker/coalescing evidence pending | concurrency scheduling remains host-sensitive |
| CP-003 | Requirement 2 | T005, T008, T011 | V3, V5, V7, V10 | Windows live revocation deferred |
| CP-004 | Requirement 1, Requirement 4 | T001-T005, T008, T011 | V1-V5, V7, V10 | none for accepted Linux slice |
| CP-005 | Requirement 2, Requirement 4 | T002-T005, T008, T011 | V3-V5, V7, V10 | none |
| CP-006 | Requirement 6 | T006-T007, T011 | V6, V10 | desktop session capture variation |
| CP-007 | Requirement 3, Requirement 5 | T011 | V1, V4-V6, V10 | live systemd deadline timing remains host-sensitive |

## Design To Implementation Matrix

| Design section | Requirements | Tasks | Interfaces or files | Verification | Coverage state | Residual destination |
|----------------|--------------|-------|---------------------|--------------|----------------|----------------------|
| Status models and snapshot | Requirement 2, Requirement 3 | T001-T002 | models, protocol, backend, storage | V1, V3 | partial-pass | T001 contracts passed; T002 backend action remains |
| Event broker and change sources | Requirement 1, Requirement 4 | T003 | new broker/watcher modules | V2, V4 | pass | Bounded broker, mutation seams, snapshot race boundary, and watcher resync validated |
| Linux event transport | Requirement 1, Requirement 2, Requirement 4, Requirement 7 | T005 | Linux adapter, backend, event client | V3-V5 | pass | Authenticated bounded listener, reconnect, revocation, restart, and independence tests passed |
| Tray presentation | Requirement 3-Requirement 6 | T006, T011 | tray client, entry, platform integration | V5-V6, V10 | partial | Exact State/Activity/Last Backup rows, local last-success, health/activity separation, menu actions, quiet serve, and connecting-before-subscription ordering pass local checks; installed visual startup remains T011 |
| Windows event contract | Requirement 2, Requirement 4, Requirement 7 | T008 | Windows adapter and platform tests | V7 | not-covered | T008 |
| Deployment and compatibility | Requirement 4, Requirement 7 | T009-T011 | assets, deployment, release probes | V8-V10 | partial | Corrected Linux activation passed; remaining installed acceptance stays in T011 and reusable deployment workflow debt is routed to Spec 011 |
| Promotion and closure | Requirement 1-Requirement 7 | T012-T013 | durable docs and lifecycle artifacts | V11-V15 | not-covered | T012-T013 |

## Open Decision Impact

The dedicated privileged event channel, continuous resident backend, and
heartbeat design were rejected by explicit user direction on 2026-07-28 after
T011 live diagnosis demonstrated an idle CPU feedback loop. This is a resolved
project-direction decision, not an open implementation choice.

Spec 010 may preserve independently valid snapshot semantics, last-success
meaning, and tray presentation. It must not promote or resume acceptance of the
resident backend. Spec 011 owns traceability for zero idle residency,
short-lived authenticated helpers, atomically published sanitized status, and
daemonless live acceptance.

## Verification Gate Key

| Gate | Description |
|------|-------------|
| V1 | Model, snapshot, protocol, and CP-001/CP-002 tests |
| V2 | Broker revision, coalescing, and race tests |
| V3 | Authorization and privacy negative controls |
| V4 | Change-source, watcher overflow, and resync tests |
| V5 | Linux transport, reconnect, restart, and independence tests |
| V6 | Tray menu, last-success, local-time, one-shot, and idle-output tests |
| V7 | Windows named-pipe contract and platform tests |
| V8 | Deployment asset and rollback tests |
| V9 | Wheel/sdist validation and installed-artifact smoke |
| V10 | Approved Linux Mint live acceptance |
| V11 | `$review-timelocker` expert review and disposition |
| V12 | Configured normal regression and coverage profile |
| V13 | Ruff, compile, link, Markdown, and Git checks |
| V14 | Lifecycle lint, readiness, task, evidence, promotion, and closure checks |
| V15 | Final spec commit, cleanup, active index, closure log, and archive index |
