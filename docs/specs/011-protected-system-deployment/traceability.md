---
title: Protected system deployment traceability
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
| T001 | Requirement 4, Requirement 8, Requirement 9 | R4 AC1/AC4; R8 AC2/AC5; R9 AC1-AC3/AC6 | single-request helper | V1, V3 | architecture, operations |
| T002 | Requirement 2, Requirement 7, Requirement 9 | R2 AC5; R7 AC2/AC4; R9 AC4-AC6 | snapshot store and watcher | V1-V3 | requirements, tray guide |
| T003 | Requirement 4, Requirement 5, Requirement 9 | R4 AC1/AC5; R5 AC2-AC3; R9 AC1-AC3/AC5 | daemonless assets and migration | V1, V3-V4 | architecture, installation |
| T004 | Requirement 1-Requirement 8 | all local-wheel criteria | deployment entrypoint and transaction | V1-V5 | installation, version process, reference |
| T005 | Requirement 1-Requirement 9 | all automated criteria | validation strategy | V1-V7 | testing docs |
| T006 | Requirement 1-Requirement 9 | review disposition | all security and operational sections | V8 | all targets |
| T007 | Requirement 1-Requirement 9 | promotion and closure | residual architecture | V9-V10 | all targets and history |

## Requirement To Delivery Matrix

| Requirement | Priority | Tasks | Verification gates | Durable targets | Coverage State | Residual Destination |
|-------------|----------|-------|--------------------|-----------------|----------------|----------------------|
| Requirement 1 | must-have | T004-T007 | V1, V5-V10 | installation, reference | complete | Supported entrypoint implementation and documentation. |
| Requirement 2 | must-have | T002, T004-T007 | V1-V2, V5-V10 | requirements, version process | complete | Local-wheel provenance; remote acquisition is outside this slice. |
| Requirement 3 | must-have | T004-T007 | V1-V2, V5-V10 | installation, security guidance | complete | Private staging and bounded cleanup. |
| Requirement 4 | must-have | T001, T003-T007 | V1, V3-V10 | architecture, operations | complete | Preflight-first daemonless activation. |
| Requirement 5 | must-have | T003-T007 | V1, V4-V10 | installation, version process | complete | Rollback and protected-state preservation. |
| Requirement 6 | must-have | T004-T007 | V1, V5-V10 | operations | complete | Lock, idempotency, and attention evidence. |
| Requirement 7 | must-have | T002, T004-T007 | V1-V2, V5-V10 | troubleshooting, reference | complete | Redacted typed evidence and status. |
| Requirement 8 | should-have | T001, T004-T007 | V1, V5-V10 | architecture | partial-routed | Platform-neutral contracts included; live Windows implementation routed to a future Windows spec. |
| Requirement 9 | must-have | T001-T003, T005-T007 | V1-V4, V6-V10 | charter, requirements, architecture, tray guide | complete | Automated zero-residency proof; protected live deployment remains operationally approval-gated. |

## Correctness Property Coverage

| Property | Tasks | Verification | Residual risk |
|----------|-------|--------------|---------------|
| CP-001 | T004-T005 | V1, V5 | platform command behavior |
| CP-002 | T003-T005 | V1, V4-V5 | live competing administrator |
| CP-003 | T003-T005 | V1, V4-V5 | signal timing on live systemd |
| CP-004 | T002, T004-T005 | V1-V2, V5 | filesystem-specific durability |
| CP-005 | T001, T003-T005 | V1, V3-V5 | none |
| CP-006 | T002, T004-T006 | V1-V2, V5, V8 | unknown future secret categories |
| CP-007 | T001, T004-T006 | V1, V5, V8 | Windows live implementation |
| CP-008 | T001-T003, T005-T006 | V1-V4, V6, V8 | live 90-second interval requires approval |

## Design To Implementation Matrix

| Design element | Implementation | Direct verification |
|----------------|----------------|---------------------|
| Single-request protected helper | `backend_entry.py`, `linux_adapter.py`, `timelocker-control.service` | one-shot backend and descriptor-contract tests |
| Sanitized atomic status | `status_snapshot.py`, backend publication hooks, `tray_client.py` | permissions, schema, atomic-replace, real watcher, and tray subscription tests |
| Removal of resident Linux event service | deleted status-event socket asset, schema-3 deployment manifest, release launcher | asset, release, artifact-validator, and installed-wheel smoke checks |
| Supported administrator command | `deployment_entry.py`, `timelocker-deploy-launcher`, project entry point | local-wheel, status, activation, rollback, and wrapper tests |
| Preflight, recovery, and evidence | deployment transaction, trusted lock/staging paths, attention evidence | validation, recovery, symlink, idempotency, and timer-health tests |
| Durable operator guidance | architecture, installation, troubleshooting, tray, release, and command docs | Markdown set checks and lifecycle promotion review |

## Open Decision Impact

| Decision | Delivery impact | Disposition |
|----------|-----------------|-------------|
| Linux must have zero idle TimeLocker service residency | The kernel may retain the socket; the privileged Python helper handles one request and exits. | accepted and implemented |
| Status must not require a privileged event daemon | Workers atomically publish one sanitized group-readable file; the optional tray watches that file directly. | accepted and implemented |
| Protected host mutation requires separate approval | Automated fakes, source/asset checks, packaging, and non-mutating probes are used here. | live install and 90-second observation routed |
| Windows deployment must not be implied by Linux delivery | Imports/help fail safely across platforms, while service-control acceptance remains unclaimed. | future Windows spec |
| Legacy event abstractions may remain as compatibility code | They are not referenced by Linux production composition or packaged service assets. | accepted low-risk cleanup debt |

## Verification Gate Key

| Gate | Description |
|------|-------------|
| V1 | Focused daemonless runtime and deployment tests |
| V2 | Snapshot schema, permissions, atomicity, watcher, and redaction tests |
| V3 | Unit/asset proof that one request exits and no event service is installed |
| V4 | Rollback/migration state-preservation tests |
| V5 | Administrator entrypoint, failure injection, package and artifact smoke |
| V6 | Process-residency probe and separately approved 90-second live check |
| V7 | Full configured regression, Ruff, compile, Markdown, and Git checks |
| V8 | TimeLocker MoE review and disposition |
| V9 | Durable promotion and lifecycle closure checks |
| V10 | Final-spec commit, package cleanup, and resolved history metadata |

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
