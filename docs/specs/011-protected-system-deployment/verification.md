---
title: Protected system deployment verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Verification

## Scope

Verify daemonless protected request execution, sanitized status publication and
tray observation, supported local-wheel deployment, rollback safety, evidence
redaction, packaging, and lifecycle closure without mutating the protected host
unless separately approved.

## Quality Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Requirements and design reviewed | pass | User approved implementation on 2026-08-12. |
| Focused runtime and deployment regression | pass | 295 focused tests passed; configured suite executed with one unrelated timing-benchmark failure routed below. |
| Package and installed-artifact checks | pass | Wheel/sdist validation and installed-wheel smoke passed. |
| MoE review | pass | All seven roles completed; findings remediated or routed. |
| Durable promotion and closure | pass | Current-state documents promoted; lifecycle checks recorded below. |

## Validation Commands

- Focused pytest paths selected by changed-file impact.
- Full configured `python3 -m pytest`.
- Scoped `ruff check` and `python3 -m compileall`.
- Wheel/sdist build, asset validation, and installed-wheel smoke.
- Agent Workbench diagnostics, Markdown checks, and verification plan.
- Spec Lifecycle Manager lint, task audit, evidence, promotion, and closure.
- `git diff --check`.

## Live Or Protected Verification

Protected installation, unit mutation, backup/retention execution, rollback,
and the 90-second root-process/CPU observation retain separate operational
approval. Without that approval, automated systemd fakes, packaged-unit
inspection, process-exit tests, and a non-mutating current-process probe are
recorded; live acceptance is routed rather than implied.

## Durable Promotion And Cleanup

| Spec content | Durable destination | Status | Evidence |
|--------------|---------------------|--------|----------|
| Zero-idle and authorization requirements | `CHARTER.md`, `docs/1-requirements/system-operations.md` | complete | T007 |
| Daemonless runtime/deployment architecture | `docs/2-architecture/system-architecture.md` | complete | T007 |
| Component ownership | `docs/3-implementation/service-layer-integration.md` | complete | T007 |
| Installation and troubleshooting | `docs/guides/user/installation.md`, `docs/guides/user/backup-operations-troubleshooting.md` | complete | T007 |
| Tray behavior | `docs/SYSTEM-TRAY-SETUP.md` | complete | T007 |
| Release activation | `docs/processes/version-management.md` | complete | T007 |
| Command surface | `docs/reference/timelocker-cli-command-hierarchy.md` | complete | T007 |
| Windows live work | future Windows spec | routed | T007 |

## MoE Review

The repository-local TimeLocker review method was applied across all seven
roles after implementation. Findings were deduplicated before remediation.

| Expert role | Review conclusion | Finding disposition |
|-------------|-------------------|---------------------|
| Project steward | The change restores the chartered zero-idle boundary while retaining explicit protected actions. | accepted; resident Linux event service removed |
| Restic backup and recovery | Deployment and verification do not execute backup or retention; existing timer state is preserved and checked. | fixed activation so only the control socket is enabled; added rollback timer-health verification |
| Python CLI architecture | One supported command owns install, upgrade, status, and rollback; the old script is only a compatibility wrapper. | fixed non-POSIX imports, stable failure results, retry behavior, and launcher packaging |
| Security and privacy | Kernel peer identity remains authoritative; status and evidence are bounded, sanitized, and protected. | fixed status-read TOCTOU, symlink-safe evidence writes, trusted lock roots, missing-group failure, and raw-error disclosure |
| Reliability and testing | One-shot execution, atomic publication, idempotency, recovery attention, and inert cleanup have direct tests. | fixed initial-install recovery, rollback health verification, stale input cleanup, and timer-start regression |
| Operations and portability | Linux uses socket activation without a resident service; live host mutation remains approval-gated. | fixed offline wheel installation, clean-host status, unit health output, and executable wrapper mode; Windows live work routed |
| Documentation lifecycle | Durable documents describe current behavior and immediate legacy shutdown. | promoted current state; Spec 010 rejection and Spec 011 ownership remain explicit |

No unresolved high- or medium-severity finding remains in the automated scope.

## Evidence Log

| Date | Requirements | Gate | Result | Evidence |
|------|--------------|------|--------|----------|
| 2026-08-12 | Requirement 1-Requirement 9 | Focused daemonless system-control suite | pass | 295 tests passed after MoE remediation |
| 2026-08-12 | Requirement 2-Requirement 7, Requirement 9 | New deployment and snapshot contracts | pass | Focused coverage includes symlink, clean-host status, timer activation, rollback health, initial missing snapshot, and runtime-directory preservation |
| 2026-08-12 | Requirement 1-Requirement 9 | Static checks | pass | scoped Ruff and Python compile checks passed; `git diff --check` clean |
| 2026-08-12 | Requirement 1-Requirement 9 | Package contract | pass | wheel and sdist built; 28 package-data files and SHA-256 hashes validated; installed-wheel smoke passed on Python 3.12.6 |
| 2026-08-12 | Requirement 1-Requirement 9 | Full configured regression | routed | 3166 passed, 1 skipped, 1 failed: pre-existing `test_repository_resolver_performance` exceeded its 0.2-second threshold (0.3097 seconds; isolated rerun 0.3637 seconds) outside changed modules |
| 2026-08-12 | Requirement 1-Requirement 9 | Agent Workbench routing | limited | changed-file context was stale for the deleted asset; direct source and executed checks were used as authority |

## Residual Risks

- The protected install/upgrade/rollback transaction and 90-second live
  root-process observation were not run because they require separate host
  mutation approval. The exact operational check remains documented.
- Windows service-control, named-pipe deployment, elevation, interruption, and
  rollback acceptance remain routed to a future Windows spec; no live Windows
  support is claimed.
- Legacy event protocol classes remain as uncomposed compatibility code. They
  are absent from Linux production composition and packaged service assets and
  therefore create no idle process residency; removal can be handled as narrow
  cleanup after downstream compatibility is assessed.
- The full configured suite retains one unrelated repository-resolver timing
  benchmark failure. Its functional assertions pass elsewhere in the suite;
  performance-threshold investigation is routed outside this system-control
  change.

## Readiness Decision

- **Ready to implement:** yes - user approval recorded 2026-08-12
- **Ready for promotion:** yes
- **Ready for closure:** yes, subject to the mechanical closure transaction

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Traceability: [traceability.md](./traceability.md)
