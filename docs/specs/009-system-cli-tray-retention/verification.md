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
| Task evidence complete | yes | partial | T001-T004 complete; T005-T012 pending |
| Automated tests pass or alternate verification recorded | yes | partial | Phase 1 focused suite: 98 passed, 88.4% coverage |
| Security and operations expert review complete | yes | partial | T004 checkpoint complete; final T012 review pending |
| Linux Mint live acceptance and rollback rehearsal complete | yes | pending | |
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
| `python3 -m pytest tests/TimeLocker/system_control -q` | Protocol, auth, storage, IPC, locks | pending | V1-V4 |
| `python3 -m pytest tests/TimeLocker/cli/test_monitoring_commands.py -q` | CLI local/system log and run behavior | pending | V6 |
| `python3 -m pytest tests/TimeLocker/monitoring -q` | Notification/tray/headless regression | pending | V7 |
| `python3 -m pytest tests/TimeLocker/scheduling -q` | Retention and scheduler regression where present | pending | V8 |
| `python3 -m pytest tests/TimeLocker/platform -q` | Platform adapters and portability | pending | V4, V7, V9 |
| `python3 -m pytest -m "not performance and not stress and not minio"` | Full configured non-live regression suite | pending | V1-V9 |
| `systemd-analyze verify <staged units>` | Linux unit and socket validation | pending | V4, V9 |
| `python3 scripts/link_checker.py` | Durable/spec link validation | pending | V12 |
| `git diff --check` | Patch integrity | pending | Every implementation slice |

## Requirement Coverage

| Requirement | Acceptance criteria covered | Evidence | Residual risk |
|-------------|-----------------------------|----------|---------------|
| Requirement 1 | AC1-AC4 | V5, V9, V10 pending | Live launcher/rollback |
| Requirement 2 | AC1-AC6 | V2, V4-V5, V10 pending | Platform authorization UX |
| Requirement 3 | AC1-AC8 | V7, V9-V10 pending | Desktop diversity |
| Requirement 4 | AC1-AC11 | V1-V4, V6, V10 pending | Redaction and NSS variance |
| Requirement 5 | AC1-AC11 | V1, V3, V8, V10 pending | Live repository timing |
| Requirement 6 | AC1-AC6 | V3, V5, V7, V9-V10 pending | Cross-platform rollout |

## Correctness Property Coverage

| Property | Covered by | Evidence | Residual risk |
|----------|------------|----------|---------------|
| CP-001 | V2, V5 | pending | |
| CP-002 | V7, V10 | pending | |
| CP-003 | V3, V8, V10 | pending | |
| CP-004 | V1, V3, V6, V8 | pending | |
| CP-005 | V1, V8, V10 | pending | |
| CP-006 | V1-V2, V4-V6 | pending | |
| CP-007 | V2, V4, V10 | pending | |
| CP-008 | V3, V9-V10 | pending | |
| CP-009 | V1, V7, V9 | pending | Live Windows remains follow-up |
| CP-010 | V3, V8, V10 | pending | |
| CP-011 | V1-V2, V4, V6, V10 | pending | |

## Scope Reconciliation Before Closure

| Broad requirement, design target, or review finding | Implemented in this spec | Coverage state | Deferred or rejected work | Destination | Blocks closure? | Evidence |
|-----------------------------------------------------|--------------------------|----------------|---------------------------|-------------|-----------------|----------|
| Linux system command/control plane | none | not-covered | Implementation pending | T001-T006, T009-T010 | yes | pending |
| Group-authorized system records | none | not-covered | Implementation pending | T001-T004, T006 | yes | pending |
| Independent tray | none | not-covered | Implementation pending | T007, T009-T010 | yes | pending |
| Retention automation | none | not-covered | Implementation pending | T008-T010 | yes | pending |
| Windows shared architecture | none | not-covered | Live Windows adapter/acceptance | T001, T009 then roadmap | yes for contracts; no for live Windows | pending |
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
| T005-T012 | pending | No implementation evidence | Later implementation phases |

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
- **Reason:** no implementation evidence exists
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

- **Ready for promotion:** no
- **Ready for release:** no
- **Ready for closure:** no
- **Ready for implementation:** yes for the next dependency-ordered task after
  the Phase 1 lifecycle audit; later live-host mutations still require T010
  approval

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
- Canonical context: `canonical-context.md`

## Reconciliation

Reviewed against the 2026-07-26 requirements and design revisions. T001-T004
now provide executed Phase 1 evidence for V1-V3 and repository-local portions
of V4/V11. Real socket activation, installed ownership/modes, live NSS behavior,
and host restart remain pending under T010; later tasks and durable promotion
remain incomplete.
