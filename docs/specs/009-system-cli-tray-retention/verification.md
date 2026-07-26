---
title: System CLI, independent tray, retention, and control verification
doc_type: spec
artifact_type: verification
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Verification

## Scope

This plan covers all Spec 009 requirements and tasks. It distinguishes local
automated evidence, Linux integration evidence, live host acceptance, expert
review, durable promotion, and closure.

## Quality Gates

| Gate | Required? | Status | Evidence |
|------|-----------|--------|----------|
| Requirements acceptance criteria reviewed | yes | pending | Requirements amended through 2026-07-26 |
| Design and traceability approved | yes | passed | Owner approved implementation; lifecycle context reports no Phase 1 gaps |
| Task evidence complete | yes | partial | T001-T010 complete; T011-T012 pending |
| Automated tests pass or alternate verification recorded | yes | passed for Phase 4 | System-control suite: 176 passed before live rollout; 22 focused backup/backend/tray tests passed after live defect fixes |
| Security and operations expert review complete | yes | partial | T004 and Phase 2 checkpoints complete; final T012 review pending |
| Linux Mint live acceptance and rollback rehearsal complete | yes | passed | V10 completed on 2026-07-26; selected release `32ab1fefd8fd9334fe37b68b1f2262565f32bebd` |
| Durable documentation promoted | yes | pending | |
| Governance or policy conflicts resolved | yes | pending | |
| Spec cleanup decision recorded | yes | pending | |

## Verification Gates

| ID | Gate | Covers | Required evidence |
|----|------|--------|-------------------|
| V1 | Protocol/model validation | T001, CP-004-CP-006, CP-009, CP-011 | Focused schema, transition, projection, and property tests |
| V2 | Authorization validation | T001, T003, T006, CP-001, CP-006, CP-007, CP-011 | Authorized/denied/stale-membership/NSS-failure/primary-and-supplementary-group/metadata-leak tests |
| V3 | Run store and lock validation | T002, T008, CP-003, CP-004, CP-008, CP-010 | Concurrency, atomicity, corruption, kill/restart tests |
| V4 | Linux IPC integration | T003-T004 | Real AF_UNIX peer-credential, socket-mode, timeout, request-bound, concurrency-bound, and session-refresh tests |
| V5 | Launcher/elevation validation | T005 | Resolution, routing, denial, recursion, upgrade, rollback tests |
| V6 | CLI visibility validation | T006 | Local/system scope, runs, formatting, compatibility, denial tests |
| V7 | Tray/headless validation | T007 | Import boundary, absence, crash, reconnect, singleton, live session tests |
| V8 | Retention validation | T008 | Fingerprint, approval, three triggers, conflict, no-prune tests |
| V9 | Packaging/portability validation | T009 | Wheel/assets, systemd, permissions, Windows test double, rollback |
| V10 | Live Linux acceptance | T010 | Secret-free command, systemd, backup, restore, retention, tray evidence |
| V11 | Expert review | T004, T012 | `review-timelocker` findings and dispositions |
| V12 | Promotion and closure | T011-T012 | Markdown/link checks, lifecycle gates, closure records |

## Planned Validation Commands

Commands are refined through Agent Workbench before execution.

| Command | Purpose | Result | Evidence |
|---------|---------|--------|----------|
| `python3 -m pytest tests/TimeLocker/system_control -q` | Protocol, auth, storage, IPC, locks | passed in expanded suite | V1-V4, V9 |
| `python3 -m pytest tests/TimeLocker/cli/test_monitoring_commands.py -q` | CLI local/system log and run behavior | pending | V6 |
| `python3 -m pytest tests/TimeLocker/monitoring -q` | Notification/tray/headless regression | passed in expanded suite | V7, V9 |
| `python3 -m pytest tests/TimeLocker/scheduling -q` | Retention and scheduler regression where present | pending | V8 |
| `python3 -m pytest tests/TimeLocker/platform -q` | Platform adapters and portability | pending | V4, V7, V9 |
| `python3 -m pytest -m "not performance and not stress and not minio"` | Full configured non-live regression suite | pending | V1-V9 |
| `systemd-analyze verify <staged units>` | Linux unit and socket validation | passed in isolated root | V4, V9 |
| `python3 scripts/link_checker.py` | Durable/spec link validation | pending | V12 |
| `git diff --check` | Patch integrity | passed | Every implementation slice |

## Requirement Coverage

| Requirement | Acceptance criteria covered | Evidence | Residual risk |
|-------------|-----------------------------|----------|---------------|
| Requirement 1 | AC1-AC4 | V5, V9, and V10 passed | Durable promotion remains T011 |
| Requirement 2 | AC1-AC6 | V2, V4-V5, and V10 passed on Linux Mint | Other platform authorization remains roadmap work |
| Requirement 3 | AC1-AC8 | V7, V9, and V10 passed for the Linux reference desktop | Desktop diversity remains a portability risk |
| Requirement 4 | AC1-AC11 | V1-V4, V6, and V10 passed | NSS variance remains a residual portability risk |
| Requirement 5 | AC1-AC11 | V1, V3, V8, and V10 passed | Production timing remains observable through durable runs |
| Requirement 6 | AC1-AC6 | V3, V5, V7, V9, and V10 passed for Linux | Live Windows support remains follow-up work |

## Correctness Property Coverage

| Property | Covered by | Evidence | Residual risk |
|----------|------------|----------|---------------|
| CP-001 | V2, V5 | repository and Linux live authorization passed | Other platform authorization remains follow-up |
| CP-002 | V7, V10 | repository and Linux Mint live tray acceptance passed | Desktop diversity |
| CP-003 | V3, V8, V10 | repository locking and live backup/retention coordination passed | Production timing variance |
| CP-004 | V1, V3, V6, V8 | repository and live terminal-state projection passed | none after T010 evidence |
| CP-005 | V1, V8, V10 | exact-fingerprint dry-run and live retention passed | Operator policy accuracy |
| CP-006 | V1-V2, V4-V6 | repository and live local IPC authorization passed | Other platform IPC |
| CP-007 | V2, V4, V10 | authorized, denied, and live NSS behavior passed | NSS variance across Linux distributions |
| CP-008 | V3, V9-V10 | interrupted recovery, installed coordination, upgrade, and rollback passed | Crash timing remains observable |
| CP-009 | V1, V7, V9 | V1, V7, and V9 repository validation passed | Live Windows remains follow-up |
| CP-010 | V3, V8, V10 | repository idempotency and both live retention trigger modes passed | none after T010 evidence |
| CP-011 | V1-V2, V4, V6, V10 | repository and live safe projection passed | Continue canary tests during promotion |

## Scope Reconciliation Before Closure

| Broad requirement, design target, or review finding | Implemented in this spec | Coverage state | Deferred or rejected work | Destination | Blocks closure? | Evidence |
|-----------------------------------------------------|--------------------------|----------------|---------------------------|-------------|-----------------|----------|
| Linux system command/control plane | Shared contracts, store, dispatcher, backend, immutable launcher, CLI views, installed socket, and live acceptance | live-validated | Durable documentation promotion | T011 | yes | T001-T010 evidence |
| Group-authorized system records | Current-membership dispatcher, structured projection, and authorized/denied live acceptance | live-validated | Durable documentation promotion | T011 | yes | T003, T004, T006, T009-T010 evidence |
| Independent tray | Standalone process, bounded IPC client, strict menu allowlist, singleton lock, launcher/autostart, reconnect, and live status | live-validated | Durable documentation promotion | T011 | yes | T007, T009-T010 evidence |
| Retention automation | Exact-fingerprint approval, protected adapter, post-success trigger, independent timer, shared lock, and durable runs | live-validated | Durable documentation promotion | T011 | yes | T008-T010 evidence |
| Windows shared architecture | Token-derived identity, current-group resolver, and named-pipe transport seam with Linux-hosted contract tests | repository-validated | Live Windows service/pipe implementation and acceptance | Platform roadmap | no for this Linux reference closure | T009 evidence |
| Raw journald delegation | rejected | out-of-scope | Rejected because it exposes unrelated/protected records | none | no | Design D002 |
| User-scoped backup partitions | none | out-of-scope | Separate authorization model | GitHub issue #70 | no | Requirements non-goal |

## Agent Readiness Evidence

| Field | Evidence | Residual risk |
|-------|----------|---------------|
| Scope and out-of-scope files | Design slice table and change impact | Affected-file list will sharpen per task |
| Must-read and optional context | `canonical-context.md`, full Spec 009 package, and linked durable docs | Refresh current-state evidence before each implementation phase |
| Permissions and approval points | T010 requires explicit host-mutation approval | No live mutation before approval |
| Validation commands and expected signals | V1-V12 and planned commands | Commands must be refreshed after files exist |
| Review needs | Security/architecture at T004; full expert panel at T012 | Findings may change design/tasks |
| Durable-doc or closure impact | `change-impact.md` promotion table | Promotion remains pending |
| Optional repo-evidence provider caveats | Agent Workbench evidence is routing/planning, not executed proof | Direct reads and commands required |

## Task Evidence

| Task ID | Status | Evidence | Notes |
|---------|--------|----------|-------|
| T001 | complete | 70 focused tests passed; 92.7% branch-aware coverage; compile and patch checks passed | Shared strict contracts only; no transport, store, CLI, or live-system behavior |
| T002 | complete | Atomic storage, bounded diagnostics, `flock` mutation leases, and startup reconciliation; focused T002 suite passed | No live state directory or production repository used |
| T003 | complete | Linux peer credentials, current NSS membership, strict dispatcher/audit, policy loader, and staged unit assets; focused T003 suite passed | No group, socket, service, or policy installed |
| T004 | complete | Phase 1 suite passed 98 tests at 88.4% coverage; Ruff, compileall, wheel asset, patch, lifecycle, and expert-panel checks passed | Real systemd/AF_UNIX host acceptance remains V4/T010 |
| T005 | complete | 22 focused launcher/action-policy tests; staged alias, selector, and launcher assets; wheel inventory; Ruff and patch checks passed | No live launcher or selector changed |
| T006 | complete | Integrated system-control/CLI/help suite passed 177 tests; system-control package measured 88.2% branch-aware coverage; Ruff, format, compile, wheel, and patch checks passed | Live socket and operator-group acceptance remain T009/T010 |
| T007 | complete | Independent tray entry point, strict tray allowlist, backend-unavailable/denied projection, and headless-safe monitoring imports; 190-test repository slice passed | Installed desktop-session and live IPC acceptance remain T009-T010 |
| T008 | complete | Approved retention executor, trigger claiming, protected request handler, and independent schedule gate; system-control suite passed 149 tests with 83.09% branch-aware coverage | Live backend composition and host scheduling acceptance remain T009-T010 |
| T009 | complete | 178-test focused Phase 4 suite; 753-test expanded regression; validated wheel/sdist, entrypoints, assets, headless import, staged units, upgrade, and rollback | No host state changed; live installation and production adapter activation remain T010 |
| T010 | complete | Selected immutable release, authorized/denied system views, launcher/socket/tray acceptance, successful backup and restore, approved post-success and independent retention, interrupted recovery, upgrade, and rollback | Linux Mint reference acceptance only; no live Windows claim |
| T011-T012 | pending | No completion evidence | Durable promotion, final review, and closure |

## Evidence Log

| Date | Evidence | Result | Notes |
|------|----------|--------|-------|
| 2026-07-26 | Live CLI/user-log and systemd-journal diagnosis | confirmed gap | User log scope differs from root system backup journal |
| 2026-07-26 | Repository context and direct source reads | confirmed design seams | No OS peer/group auth or local IPC exists; tray is constructed in notification services |
| 2026-07-26 | Spec artifacts created | pending validation | Design/tasks do not constitute implementation |
| 2026-07-26 | Canonical context reconciliation | current/future authority split recorded | Durable docs remain current until verified promotion |
| 2026-07-26 | Focused `review-timelocker` design/security review | blocking design findings addressed | Explicit AC mappings, fail-closed NSS, root-only audit, safe summaries, storage hardening, and transport bounds added |
| 2026-07-26 | `python3 -m pytest tests/TimeLocker/system_control ... --cov-fail-under=90` | 70 passed; 92.7% coverage | T001 strict models, envelopes, projection, transition, portability, and negative security cases |
| 2026-07-26 | `python3 -m compileall -q src/TimeLocker/system_control tests/TimeLocker/system_control` and `git diff --check` | passed | T001 syntax and patch integrity |
| 2026-07-26 | Focused `review-timelocker` T001 implementation review | no actionable findings after remediation | Response summaries were made code-owned; response envelope and transition model omissions were corrected before completion |
| 2026-07-26 | `python3 -m pytest tests/TimeLocker/system_control ... --cov-fail-under=85` | 98 passed; 88.4% coverage | T001-T003 contracts, storage, locking, recovery, authorization, redaction, policy, and Linux adapter tests |
| 2026-07-26 | `PYENV_VERSION=3.12.4 ruff check ...` and `ruff format --check ...` | passed | Phase 1 source and focused tests |
| 2026-07-26 | `python3 -m compileall -q ...` and `git diff --check` | passed | Phase 1 syntax and patch integrity |
| 2026-07-26 | `PYENV_VERSION=3.12.4 python -m build --wheel --no-isolation ...` plus wheel inventory | passed; 3/3 assets present | Policy, socket unit, and service unit are packaged; isolated build could not resolve build dependencies because network access was unavailable |
| 2026-07-26 | Agent Workbench verification planning and diagnostics | planning returned; diagnostics unavailable | No Python diagnostics provider was configured, so direct review and executed checks remain the proof |
| 2026-07-26 | Rules consulted and applied | recorded | Coding Standards (100), General Preferences (50), Operational Best Practices (40), Planning Protocol (30), Testing Conventions (25), Documentation Conventions, and Git Conventions; no overrides |
| 2026-07-26 | `PYENV_VERSION=3.12.6 python -m pytest tests/TimeLocker/system_control tests/TimeLocker/cli/test_monitoring_commands.py tests/TimeLocker/cli/test_cli_help_system.py -q --no-cov` | 177 passed | Phase 2 launcher, action routing, client, authorization, structured run/log views, compatibility, denial, and redaction |
| 2026-07-26 | `coverage report --include='src/TimeLocker/system_control/*' --skip-empty --fail-under=0` | 88.2% branch-aware coverage | Scoped report for the system-control package; a pytest coverage attempt inherited repository-wide `source=src` and failed the global 50% threshold at 17.3%, so it is not presented as a focused coverage result |
| 2026-07-26 | Ruff check/format, compileall, wheel build/inventory, and `git diff --check` | passed | Wheel contains the Phase 2 modules and all six system-control assets, including distinct `timelocker` and `tl` launcher assets; isolated build dependency resolution was unavailable, and the Python 3.12.4 no-isolation build passed |
| 2026-07-26 | Agent Workbench verification planning | partial routing only | Its index had not incorporated newly created files and proposed unrelated tests; direct source review, the focused suite, and package inventory are the proof |
| 2026-07-26 | `python3 -m pytest tests/TimeLocker/system_control/test_retention.py tests/TimeLocker/system_control/test_tray_client.py tests/TimeLocker/system_control/test_tray_process_boundary.py tests/TimeLocker/monitoring/test_system_tray_integration.py tests/TimeLocker/system_control/test_client.py` | 32 passed; repository-wide coverage gate failed at 12.2% | Narrow slice inherited repository-wide `--cov=src/TimeLocker`; tests passed and exposed a coverage-accounting mismatch rather than a functional regression |
| 2026-07-26 | `PYENV_VERSION=3.12.4 PYTHONPATH=src python -m pytest -o addopts='' tests/TimeLocker/system_control --cov-config=/dev/null --cov=TimeLocker.system_control --cov-branch --cov-report=term --cov-fail-under=80 -q` | 149 passed; 83.09% branch-aware coverage | Complete system-control regression and focused Phase 3 coverage without inheriting the repository-wide coverage source |
| 2026-07-26 | System-control, monitoring, and integration regression slice | 190 passed | Tray/process boundaries, retention execution, monitoring compatibility, reconnect, authorization projection, and schedule summaries |
| 2026-07-26 | Ruff check/format, compileall, wheel build/inventory, and `git diff --check` | passed | Wheel contains `timelocker-tray` and all new Phase 3 modules; no host state changed |
| 2026-07-26 | Expanded `system_control`, `monitoring`, and `integration` pytest run | 733 passed, 1 skipped, 2 failed, 4 setup errors | The failures are confined to repository credential integration paths outside this diff: five expect a legacy credential-file location and one cannot register S3 because optional `b2sdk` is absent. They do not invalidate the bounded Phase 3 suites but remain repository test debt. |
| 2026-07-26 | Credential-path and backend-registration reconciliation | 6 focused tests passed | `--config-dir` consistently treats the argument as the configuration root and stores credentials under `credentials/credentials.enc`; missing B2 registration no longer prevents S3 registration. No credential contents or live stores were read, copied, or deleted. |
| 2026-07-26 | Phase 4 focused system-control, credential, and artifact suite | 178 passed | Backend/release entrypoints, exact asset manifest, permissions, Windows adapter seam, upgrade, rollback, credential paths, and release metadata passed. |
| 2026-07-26 | Expanded `system_control`, `monitoring`, and `integration` pytest run | 753 passed, 1 skipped | Previous six credential/backend-registration failures are resolved; existing warnings remain non-blocking. |
| 2026-07-26 | Wheel/sdist validation and installed headless smoke | passed | Four console entrypoints and 20 package-data files validated; CLI import did not load tray code and the environment had no `pystray` dependency. |
| 2026-07-26 | Staged `systemd-analyze verify --recursive-errors=no --root=...` | passed | Backend socket/service and disabled retention service/timer parsed successfully against an isolated staged executable. |
| 2026-07-26 | Controlled Linux Mint T010 rollout and immutable-release rehearsal | passed | Root-owned launchers/backend, current operator-group authorization and denial, socket activation, tray disconnect/reconnect, interrupted-run recovery, upgrade, and rollback passed; selected release is `32ab1fefd8fd9334fe37b68b1f2262565f32bebd`. |
| 2026-07-26 | Production backup and restore acceptance | passed | Scheduled backup remained healthy; explicit backup run `287f480c-283f-45c0-85ed-2eb8b6392596` succeeded and a one-file restore completed. Evidence contains no credentials, repository URI, or protected source inventory. |
| 2026-07-26 | Exact-fingerprint retention activation | passed | Operator accepted fingerprint `e62033fd33259af14b68305e6d1179f840697f4a89f0c0df8cb95a5d69e81d94`; independent retention and post-backup retention run `b3e5baff-56a7-4437-9295-9611a0c56156` succeeded without pruning. Both timers remain enabled and waiting. |
| 2026-07-26 | Live tray queued/history regression | fixed and passed | Initial accepted request displayed stale `error` while queued; commits `2388e1d` and `32ab1fe` added durable backup coordination and made queued/latest operation state authoritative. Focused regression: 22 passed; live tray reports `success`, zero active operations, and backend available. |

## T004 Review Finding Dispositions

| Finding | Severity / confidence | Roles | Disposition | Validation |
|---------|-----------------------|-------|-------------|------------|
| TLR-001: reconciling an older abandoned run could fail when a newer run held the same repository lock | medium / high | Security and Privacy; Reliability and Testing; Operations and Portability | fixed: the older run is interrupted while the newer live lease is preserved; stale metadata clearing tolerates the live owner | `test_newer_live_lease_does_not_block_old_run_reconciliation` |
| TLR-002: startup reconciliation inspected at most 1,000 runs despite the requirement to reconcile every non-terminal run | medium / high | Project Steward; Reliability and Testing | fixed: internal reconciliation now scans the complete run inventory while public queries remain bounded | focused storage suite and direct source review |
| TLR-003: a client could hold the single-threaded socket server indefinitely with an incomplete request | medium / high | Security and Privacy; Reliability and Testing; Operations and Portability | fixed: each connection receives a bounded timeout and timeout produces an empty invalid frame without dispatch | Linux transport timeout assertion and dispatcher malformed-request tests |
| TLR-004: unconditional POSIX locking imports would break the shared package import on Windows | medium / high | Python CLI Architecture; Operations and Portability | fixed: POSIX locking is capability-checked at use time; the shared contract remains importable and unsupported locking fails explicitly | Ruff/compile checks and platform adapter contract tests |
| TLR-005: the dispatcher allowed an implicit no-op audit sink | medium / high | Security and Privacy; Project Steward | fixed: an audit sink is mandatory and every event carries caller identity, action, decision, response status, and stable result code without parameters | dispatcher authorization, denial, failure, and audit assertions |

No actionable Phase 1 findings remain after these dispositions. The review was
bounded to Spec 009 Phase 1 source, focused tests, packaged assets, and lifecycle
artifacts. It did not install or execute the staged service, inspect real NSS
membership, or claim live Windows support.

## Phase 2 Review Finding Dispositions

| Finding | Severity / confidence | Roles | Disposition | Validation |
|---------|-----------------------|-------|-------------|------------|
| TLR-006: the staged launcher assets did not provide a distinct `tl` compatibility alias | medium / high | Project Steward; Operations and Portability | fixed: packaged `tl-launcher` delegates through the same immutable launcher module as `timelocker-launcher` | wheel inventory and launcher-entrypoint tests |
| TLR-007: rollback selection trusted a selector file without revalidating its parent directory | high / high | Security and Privacy; Operations and Portability | fixed: every selector read validates the root-owned, non-writable selector directory before parsing | release-launcher ownership, mode, symlink, selection, and rollback tests |
| TLR-008: CLI record and diagnostic limits were not bounded at argument parsing | medium / high | Security and Privacy; Python CLI Architecture | fixed: run and log limits are constrained to 1-1,000 before transport requests are built | CLI invalid-limit and request-shape tests |
| TLR-009: client framing, safe errors, entrypoint delegation, and scope rejection lacked focused regression coverage | medium / high | Reliability and Testing; Python CLI Architecture | fixed: added client, release-entrypoint, invalid-scope, request-correlation, timeout, framing, and safe-error tests | integrated 177-test Phase 2 suite |

No actionable Phase 2 findings remain after these dispositions. The review was
bounded to T005-T006 source, tests, packaged assets, and lifecycle artifacts.
It did not install the launcher, select a live release, activate the socket,
inspect real group membership, or prove platform authorization prompts.

## Phase 3 Review Finding Dispositions

| Finding | Severity / confidence | Roles | Disposition | Validation |
|---------|-----------------------|-------|-------------|------------|
| TLR-010: the standalone tray used a predictable shared `/tmp` singleton path and did not drain GTK events | high / high | Security and Privacy; Operations and Portability; Reliability and Testing | fixed: the lock now lives in a private XDG runtime/cache directory, rejects symlinks, and the tray loop drains platform UI events | singleton, process-boundary, and tray adapter tests |
| TLR-011: the retention IPC handler returned an `ActionReceipt` object instead of the dispatcher contract's wire mapping | high / high | Python CLI Architecture; Reliability and Testing | fixed: the protected handler projects the receipt through `to_wire()` | protected request projection test |
| TLR-012: backend loss or access denial could leave stale successful state visible in the tray | medium / high | Project Steward; Security and Privacy; Operations and Portability | fixed: bounded retry/reset now replaces stale state with explicit unavailable or denied projections | backend absence, denial, reconnect, and safe-projection tests |

No actionable Phase 3 findings remain after these dispositions. The review was
bounded to T007-T008 source, tests, packaging, and lifecycle artifacts. It did
not install a desktop-session process, connect to the live system backend,
activate production retention, or mutate host state.

## Manual Or External Verification

Live T010 evidence must record the reviewer, timestamp, exact non-secret command,
result, and rollback state. It must not copy environment files, credentials,
repository URIs, protected source paths, or raw journal payloads into this
package.

## Residual Risks

- Group/NSS behavior differs across Linux environments; verify current
  membership and stale-process removal behavior live.
- Raw diagnostic messages can leak paths or secrets; the backend must emit
  allowlisted structured records rather than redact arbitrary text after the
  fact.
- Operator-visible `safe_summary` fields require code-keyed templates and
  canary tests proving exception strings, subprocess output, peer identity,
  repository URIs, and protected paths cannot enter responses.
- Crash timing remains sensitive despite passing atomicity and process-exit
  tests; live kill/restart acceptance remains V4/T010.
- Changing launcher and `/opt` permissions can expose protected assets if code
  and state are not separated.
- Windows live support is not proven by a test double and must not be claimed.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| System requirements and authorization invariants | `docs/1-requirements/system-operations.md` | pending | T011 |
| Launcher/backend/tray/run-store architecture | `docs/2-architecture/system-architecture.md` | pending | T011 |
| Scheduling/retention behavior | `docs/2-architecture/scheduling-system.md` | pending | T011 |
| Focused service ownership | `docs/3-implementation/service-layer-integration.md` | pending | T011 |
| Installation/group/launcher guidance | `docs/guides/user/installation.md` | pending | T011 |
| Scheduling rollout/rollback | `docs/guides/developer/scheduling-guide.md` | pending | T011 |
| Independent tray setup | `docs/SYSTEM-TRAY-SETUP.md` | pending | T011 |
| CLI commands and troubleshooting | CLI reference and backup troubleshooting guide | pending | T011 |
| User partitions | GitHub issue #70 | routed | Existing backlog authority |

### Spec Cleanup Decision

- **Cleanup action:** keep active until implementation, promotion, and closure
- **Reason:** repository implementation evidence exists through T008, but live integration, durable promotion, and closure evidence remain incomplete
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** no
- **Residual spec-only content:** all design and task content remains temporary

## Ship Or Closure Risk

- **Risk level:** high
- **Breaking change:** no intended public-command break
- **Blast radius checked:** partially
- **Rollback path:** designed; not yet implemented or rehearsed
- **Requires human review:** yes
- **Release notes needed:** yes
- **Follow-up issue or spec needed:** Windows live adapter/acceptance

### Risk Rationale

This change introduces a privileged process boundary, OS identity and group
authorization, machine-level installation assets, repository mutation
coordination, and desktop IPC. Incorrect implementation could disclose
protected metadata, widen privilege, interrupt backups, or delete snapshots.

## Readiness Decision

- **Ready for promotion:** yes
- **Ready for release:** no
- **Ready for closure:** no
- **Ready for implementation:** yes for Phase 5 task T011

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
- Canonical context: `canonical-context.md`

## Reconciliation

Reviewed against the 2026-07-26 requirements and design revisions. T001-T010
now provide repository and Linux Mint live evidence for V1-V10 and
repository-local portions of V11. Real socket activation, installed
ownership/modes, live NSS behavior, protected backup/restore, post-success and
independent retention, tray reconnect/status, interrupted recovery, upgrade,
and rollback passed. Durable promotion, final expert review, and closure remain
T011-T012.
