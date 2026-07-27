---
title: Event-driven tray status verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Verification

## Scope

This plan covers Requirements 1-7, CP-001-CP-006, T001-T013, the protected
snapshot/event contracts, Linux implementation, Windows contract tests, tray
presentation, packaging, approved live acceptance, durable promotion, and
closure.

## Quality Gates

| Gate | Required? | Status | Evidence |
|------|-----------|--------|----------|
| Requirements and acceptance criteria reviewed | yes | pass | User approval recorded 2026-07-27; lifecycle readiness passed |
| Traceability complete | yes | pass | Lifecycle lint and readiness found no blocking gaps |
| Focused model/protocol/security tests pass | yes | partial-pass | T001-T005 system-control slice: 224 passed; tray presentation T006 pending |
| Tray and event integration tests pass | yes | pass | T007 focused event-driven integration checkpoint: 58 passed |
| Windows platform contract tests pass | yes | pass | T008 injected named-pipe contract; live Windows acceptance remains deferred |
| Package and deployment checks pass | yes | pass | T009 deployment contract and T010 wheel/sdist installed-artifact checks passed |
| Approved Linux Mint acceptance passes | yes | pending | T011 |
| Expert review findings resolved | yes | pending | T012 |
| Configured regression and coverage gate pass | yes | pending | T013 |
| Durable documentation promoted | yes | pending | T013 |
| Closure and cleanup evidence complete | yes | pending | T013 |

## Validation Commands

| Command | Purpose | Result | Evidence |
|---------|---------|--------|----------|
| `python -m pytest --no-cov tests/TimeLocker/system_control/ tests/TimeLocker/monitoring/test_system_tray_integration.py` | Fast focused diagnostic during implementation | pending | Not final coverage evidence |
| `python -m pytest -m "unit or security or platform" --no-cov` with selected event files | Focused contract and negative controls | pending | Exact selection recorded per task |
| `python -m pytest -m "not performance and not stress and not minio"` | Normal correctness and 50 percent coverage gate | pending | Final suite evidence |
| `python -m pytest -m "performance or stress" --no-cov` | Timing/stress only if affected or required by review | pending | May be waived with rationale |
| `PYENV_VERSION=3.12.4 ruff check src tests` | Static style and lint | pending | |
| `python -m compileall -q src` | Package syntax/import compilation | pending | |
| `python -m build` and `python scripts/validate_release_artifacts.py --expected-version 0.9.1 --dist dist` | Artifact completeness and hashes | pending | Use current version at execution |
| isolated wheel/sdist CLI, backend, tray, control, and event-protocol smoke | Installed-artifact contract | pending | Exact commands recorded at T010 |
| Agent Workbench Markdown document checks for changed Markdown files | Markdown structure, frontmatter, links, lists, and tables | pending | MCP evidence |
| `python scripts/link_checker.py` | Internal links | pending | |
| `git diff --check` | Patch integrity | pending | |
| lifecycle lint/readiness/traceability/evidence/promotion/closure tools | Spec gates | pending | MCP outputs preferred |

## Requirement Coverage

| Requirement | Acceptance criteria covered | Evidence | Residual risk |
|-------------|-----------------------------|----------|---------------|
| Requirement 1 | AC1-AC5 | T001, T003-T005, T007, T011 | pending |
| Requirement 2 | AC1-AC5 | T001-T005, T008, T011-T012 | pending |
| Requirement 3 | AC1-AC5 | T001-T002, T006-T007, T011 | pending |
| Requirement 4 | AC1-AC5 | T002-T005, T007-T011 | pending |
| Requirement 5 | AC1-AC6 | T006-T007, T010-T011 | partial-pass; deterministic Linux badges and honest never-run/failure projection passed, live acceptance pending |
| Requirement 6 | AC1-AC4 | T006-T007, T011 | pending |
| Requirement 7 | AC1-AC5 | T001, T005, T008-T011 | pending |

## Correctness Property Coverage

| Property | Covered by | Evidence | Residual risk |
|----------|------------|----------|---------------|
| CP-001 | Generated/table-driven histories, snapshot tests, live result | partial-pass | Model, backend, and tray projection passed; live evidence pending |
| CP-002 | Revision sequence and coalescing tests | partial-pass | Broker, duplicate/older rejection, gap, and stale-snapshot controls passed; live integration remains |
| CP-003 | Subscribe, per-frame revocation, and denied-client tests | partial-pass | Linux per-delivery revocation and denial passed; Windows live evidence deferred |
| CP-004 | Restart, session change, gap, and snapshot convergence tests | partial-pass | Reconnect, new session, gap, and initial-snapshot recovery passed; live integration remains |
| CP-005 | Interface isolation, lock spy, and live operation independence | partial-pass | Separate event/control failure isolation passed; live operation evidence remains |
| CP-006 | Captured idle serve test and live 90-second observation | partial-pass | Healthy serve is silent and one-shot output remains; live 90-second evidence pending |

## Scope Reconciliation Before Closure

| Broad target | Implemented in this spec | Coverage state | Deferred or rejected work | Destination | Blocks closure? | Evidence |
|--------------|--------------------------|----------------|---------------------------|-------------|-----------------|----------|
| Event-driven Linux tray status | T001-T007, T009-T011 | partial | none | rollout tasks T009-T011 | yes | T001-T007 implementation and Phase 2 checkpoint passed |
| Continuous authorization/privacy | T001-T005, T008, T011-T012 | partial | Windows live revocation | Windows follow-up spec | yes for Linux; no for Windows live |
| Accurate and quiet tray UX | T001-T002, T006-T007, T011 | partial | Live desktop acceptance remains | T007, T011 | yes | Correct local last-success rows and silent serve passed in T006 |
| Portable Windows architecture | T001, T008 | covered | Concrete Windows service and live acceptance | follow-up spec or issue | no after routing | Injected token-derived named-pipe event contract passed 232-test checkpoint |
| Full desktop application | none | out-of-scope | Product UI | backlog/roadmap | no | charter and requirements |

## Agent Readiness Evidence

| Field | Evidence | Residual risk |
|-------|----------|---------------|
| Scope and out-of-scope files | Requirements, design slice table, change impact | Review pending |
| Must-read context | `canonical-context.md` and linked durable sources | Source may change before implementation |
| Permissions and approval points | `README.md`, tasks execution rules, T011 | Live commands require renewed approval |
| Validation commands | This file and testing conventions | Exact new test paths finalized during T001 |
| Review needs | T004 security/protocol checkpoint and T012 expert panel | Review pending |
| Durable-doc and closure impact | `change-impact.md` and promotion table | Promotion pending |
| Repository evidence caveats | Agent Workbench is routing evidence; direct reads and commands establish claims | Re-run after relevant changes |

## Task Evidence

| Task | Status | Evidence | Notes |
|------|--------|----------|-------|
| T001 | complete | Immutable status models, platform-neutral interfaces, 75 focused tests, Ruff, patch integrity | Public snapshot action remains T002. |
| T002 | complete | Authorized read-only snapshot action, backend builder, client parsing, safe denial, 108 focused tests | Event publication remains T003. |
| T003 | complete | Bounded broker, coalescing, synchronized revision boundary, mutation seams, watcher resync, 96 focused tests | Platform transport remains T005. |
| T004 | complete | Bounded expert checkpoint; 208 system-control tests, Ruff, compileall, patch integrity | No blocking Phase 1 findings remain. |
| T005 | complete | Authenticated bounded Linux event transport, reconnecting client, fresh-snapshot coordinator, 224 system-control tests | Deployment and live-host evidence remain in T009-T011. |
| T006 | complete | Snapshot-driven status rows, accurate local last-success time, silent serve, 228 system-control and 9 monitoring tests | Phase 2 integration checkpoint remains T007. |
| T007 | complete | 58-test Phase 2 transport, security, reconnect, snapshot, tray, menu, and no-polling checkpoint | Windows, deployment, package, and live acceptance remain. |
| T008 | complete | Token-derived bounded Windows named-pipe event contracts, four new platform tests, 232 system-control tests | No live Windows service or acceptance is claimed. |
| T009 | complete | Named protected event socket asset, named systemd descriptor mapping, dual-protocol release metadata, structured activation/rollback gates, 246 system-control tests | Installed-artifact and live-host evidence remain T010-T011. |
| T010 | complete | Five deterministic accessible logo badges, honest never-run/failure projection, 268-test regression, 27-file package-data validation, SHA-256 verification, and clean-install wheel/sdist smoke | No live selector, unit, socket, timer, backup, retention, or protected path changed. |
| T011-T013 | pending | none | Sequenced by the task dependency graph. |

## Evidence Log

| Date | Evidence | Result | Notes |
|------|----------|--------|-------|
| 2026-07-27 | Source and durable-doc inspection for spec authoring | pass | Current polling, stdout, menu, authorization, transport, and deployment boundaries read directly. |
| 2026-07-27 | Existing menu-removal focused tests | 14 passed | Pre-spec partial implementation evidence; final suite not run for this package. |
| 2026-07-27 | Ruff and `git diff --check` for existing menu removal | pass | Does not validate event-driven behavior. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control/test_status_contracts.py tests/TimeLocker/system_control/test_models.py tests/TimeLocker/system_control/test_protocol.py tests/TimeLocker/system_control/test_interfaces.py` | 75 passed | T001 exact models, safe failures, existing protocol compatibility, CP-001, and CP-002. |
| 2026-07-27 | T001 scoped Ruff and `git diff --check` | pass | No static or patch-integrity findings in the contract slice. |
| 2026-07-27 | T002 authorized snapshot action focused suite | 108 passed | Safe projection, denial, client, storage, backend, and compatibility evidence. |
| 2026-07-27 | T003 broker/change-source focused suite | 96 passed | Monotonicity, coalescing, bounds, race boundary, mutation isolation, and watcher resync evidence. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` | 208 passed | Phase 1 system-control regression checkpoint. |
| 2026-07-27 | Scoped Ruff, `compileall`, and `git diff --check` | pass | Phase 1 static, import-syntax, and patch-integrity evidence. |
| 2026-07-27 | `$review-timelocker` bounded Phase 1 security/protocol review | pass after direct fix | One watcher-failure resync gap was found, fixed, and regression-tested; no remaining blocking findings. Scope excluded T005+ transport, deployment, live operations, and durable-doc promotion. |
| 2026-07-27 | T005 transport, security, reconnect, and tray subscription negative controls | 13 passed | Authorized/denied subscription, per-delivery revocation, heartbeat, slow sender, frame overflow, disconnect/restart, revision gap/staleness, initial recovery, and event/control independence. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` | 224 passed | T005 system-control regression evidence. |
| 2026-07-27 | Scoped Ruff, `compileall`, and `git diff --check` | pass | T005 static, import-syntax, and patch-integrity evidence; Agent Workbench had no Python diagnostics provider. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` | 228 passed | T006 snapshot projection, event-driven serve, action, and quiet-output regression evidence. |
| 2026-07-27 | Focused monitoring tray suite | 9 passed | Disabled status rows, local timezone, icon/menu lifecycle, and absence of misleading actions. |
| 2026-07-27 | T007 focused event-driven integration checkpoint | 58 passed | Initial snapshot/update, coalescing, reconnect/restart, revocation, honest last-success, dynamic menu, silence, and no legacy polling. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` after T008 | 232 passed | Windows injected event transport, token identity, per-delivery authorization, bounded heartbeat/frame/send behavior, and no live Windows claim. |
| 2026-07-27 | T009 focused deployment, backend-entry, Linux asset, release, and snapshot suite | 52 passed | Event socket ownership/mode, named descriptor order independence, dual-protocol release metadata, fail-closed activation, timer gates, atomic selection, and rollback. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` after T009 | 246 passed | Phase 3 deployment-contract regression checkpoint. |
| 2026-07-27 | T009 scoped Ruff and `git diff --check` | pass | Ruff used the repository-installed Python 3.12.4 toolchain; Agent Workbench reported no provider-backed Python diagnostics. |
| 2026-07-27 | `systemd-analyze verify` against packaged units | environment-limited | Unit directives parsed without an unknown-directive finding, but host-wide permission errors and absent protected launcher executability prevented a clean verification claim; installed-host evidence remains T011. |
| 2026-07-27 | `PYENV_VERSION=3.12.6 python -m build --outdir /tmp/timelocker-spec010-build.xcoQSY` | pass after network retry | Isolated build produced the `0.9.1` wheel and sdist without overwriting the repository's existing `dist/` artifacts. |
| 2026-07-27 | `validate_release_artifacts.py` against isolated T010 output | pass | Validated versions, Python constraint, four entrypoints, 22 package-data files, and SHA-256 hashes. Wheel: `231cfe2289cdb408ad6d4e8194909cfa867a11aeae8f847b41d32c53ab4dc5c2`; sdist: `9712e7484eca2d5a5f878a7fb9f76d2fd7c93f25511d3eb5b964b682bd734761`. |
| 2026-07-27 | Clean-install smoke for isolated wheel and sdist on Python 3.12.6 | pass | Both artifacts passed `timelocker`, `tl`, backend and tray help, dual-protocol import, and packaged system-asset checks. |
| 2026-07-27 | Release-artifact tests, scoped Ruff, compileall, and patch integrity | pass | 10 artifact tests passed; source/system-control/project-test Ruff, compilation, and `git diff --check` passed. |
| 2026-07-27 | T010 Linux status-badge focused and regression validation | pass | 53 focused tests and 268 system-control/monitoring/icon/release-artifact tests passed; scoped Ruff, compileall, and patch integrity passed. |
| 2026-07-27 | Rebuilt badge-aware wheel/sdist validation and clean-install smoke | pass | Validator found 27 package-data files; both artifacts passed four-entrypoint, dual-protocol, system-asset, and five-icon smoke checks. Wheel SHA-256: `ceb610a5eafeedc1d0b13f0626d0ac9a74f33a4cb46735778c37fc4712b5bb7b`; sdist SHA-256: `ac9371a6e3087dc515dc5cd0c871687dd7cd23e7ce3468cc2d7d3b09c65bb7e0`. |

## Manual Or External Verification

T011 requires explicit approval before protected deployment or live operations.
The reviewed sequence is:

1. Record the current and previous selected release IDs plus active/enabled
   backup and retention timer states.
2. Stage the validated artifact as an immutable root-owned release with
   schema-2 control/event protocol metadata.
3. Install the exact hashed assets, reload systemd, and enable the protected
   control and status-event sockets without changing backup or retention
   policy.
4. Run staged CLI/backend/tray/protocol probes and verify both existing timers
   before atomically selecting the new release.
5. Run authorized/denied event, status, silence, restart, and independence
   acceptance checks.
6. Probe and atomically roll back to the previous release, then verify explicit
   control status and both timers before deciding whether to reselect the
   candidate.

Record selected release IDs, artifact hashes, service/socket/timer states,
authorized and denied observations, event latency, idle-output capture, restart
recovery, and rollback without recording credentials or raw protected content.

## Residual Risks

- A long-lived subscription expands denial-of-service and revocation concerns;
  bound subscribers and reauthorize each event/heartbeat.
- Cross-process record changes may race event publication; watcher uncertainty
  and session/snapshot recovery are mandatory.
- Desktop toolkits differ in dynamic menu behavior; keep platform tests and
  Linux Mint visual acceptance.
- Concrete Windows service behavior remains unverified and must not be claimed.
- Immutable rollback can leave new inert unit assets; verify prior control and
  timers remain healthy.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Requirements and security behavior | `docs/1-requirements/system-operations.md` | pending | |
| Architecture and platform contract | `docs/2-architecture/system-architecture.md` | pending | |
| Component/interface ownership | `docs/3-implementation/service-layer-integration.md` | pending | |
| Tray setup, menu, reconnect, rollback | `docs/SYSTEM-TRAY-SETUP.md` | pending | |
| Command/action reference | `docs/reference/timelocker-cli-command-hierarchy.md` | pending | |
| Troubleshooting and installation | user guides and version process | pending | |
| Windows live implementation | follow-up spec or issue | pending routing | |
| Full desktop UI | product backlog/roadmap | excluded | |

### Spec Cleanup Decision

- **Cleanup action:** remove after final spec commit and promotion
- **Reason:** Repository policy uses Git plus compact history indexes.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** no
- **Residual spec-only content:** none expected

## Ship Or Closure Risk

- **Risk level:** high until security review and live acceptance; expected
  medium after all gates
- **Breaking change:** coherent local protocol/release upgrade required
- **Blast radius checked:** no
- **Rollback path:** designed, not yet verified
- **Requires human review:** yes
- **Release notes needed:** yes if shipped in a release
- **Follow-up issue or spec needed:** yes, Windows live implementation and
  acceptance

### Risk Rationale

The change crosses a privileged backend, continuous local authorization,
cross-process state observation, desktop presentation, systemd deployment, and
rollback. No repository secrets or Restic mutation semantics need to change,
but implementation and live evidence must prove that the new read path cannot
weaken those boundaries.

## Readiness Decision

- **Ready to implement:** yes - lifecycle review passed and user approval was
  recorded on 2026-07-27
- **Ready for promotion:** no
- **Ready for release:** no
- **Ready for closure:** no

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Change Impact: [change-impact.md](./change-impact.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
