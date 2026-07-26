---
title: System CLI, independent tray, retention, and control tasks
doc_type: spec
artifact_type: tasks
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Tasks

**Input**: `canonical-context.md`, `requirements.md`, `design.md`,
`change-impact.md`, `traceability.md`, and `verification.md`

**Prerequisites**: Requirements and design approved; no implementation starts
until the project owner approves the task plan.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004
T004 -> T005 -> T006
T004 -> T007
T004 -> T008
T006 + T007 + T008 -> T009
T009 -> T010 -> T011 -> T012
```

## Phase 1: Shared contracts and safety foundation

- [x] T001 Define shared protocol, action, policy, run, diagnostic, and client
  models with strict validation.
  - Depends on: none
  - Requirements: Requirement 2 AC4-AC6; Requirement 4 AC1-AC7, AC9-AC11;
    Requirement 5 AC1-AC2, AC5-AC8; Requirement 6 AC5
  - Properties: CP-001, CP-004, CP-005, CP-006, CP-009, CP-011
  - Files: new focused modules under `src/TimeLocker/system_control/`;
    matching tests under `tests/TimeLocker/system_control/`
  - Acceptance: Versioned bounded schemas reject unknown fields, secret-bearing
    inputs, raw arguments, and invalid transitions; response projection returns
    only allowlisted fields.
  - Evidence: T001 complete: 70 focused tests passed with 92.7% branch-aware coverage; compileall and git diff --check passed; focused review-timelocker implementation review found no remaining actionable findings. No transport, store, CLI, or live-host behavior was changed.
  - Evidence mode: validation
  - [x] T001.1 Add failing contract and model tests.
  - Evidence: Added focused contract, model, transition, response-projection, security-boundary, and portability tests under tests/TimeLocker/system_control; final focused run: 70 passed.
  - Evidence mode: validation
  - [x] T001.2 Implement schemas, enums, validation, and response projection.
  - Evidence: Implemented strict frozen enums, request/response envelopes, run/transition/diagnostic/policy/action models, validation helpers, immutable projections, and code-owned safe summaries under src/TimeLocker/system_control.
  - Evidence mode: implementation
  - [x] T001.3 Add Linux and Windows adapter protocol test doubles.

  - Evidence: Added platform-neutral peer identity, membership, transport, handler, and client protocols with Linux UID and Windows SID adapter test doubles; platform tests passed.
  - Evidence mode: validation
- [x] T002 Implement atomic run/diagnostic storage, repository mutation
  locking, and interrupted-run reconciliation.
  - Depends on: T001
  - Requirements: Requirement 4 AC2-AC3, AC5-AC6, AC10-AC11; Requirement 5
    AC4-AC6, AC11; Requirement 6 AC6
  - Properties: CP-003, CP-004, CP-008, CP-010, CP-011
  - Files: `src/TimeLocker/system_control/`, focused storage and recovery tests
  - Acceptance: Records transition atomically to exactly one terminal state;
    concurrent mutations cannot overlap; abandoned runs become interrupted and
    stale locks are reusable without duplicate terminal records.
  - Evidence: Atomic storage, bounded diagnostics, repository mutation leases, and idempotent abandoned-run reconciliation implemented in src/TimeLocker/system_control/storage.py. Focused T002 validation passed 11 tests, including cross-process lease recovery; final Phase 1 validation remains tracked by T004.
  - Status: Complete and dependency-ready for T003.
  - Evidence mode: command
  - [x] T002.1 Add transition, concurrency, corruption, and kill/restart tests.
  - Evidence: Added transition, concurrency, corruption, persistence, bounded-stream, process-exit, and restart-reconciliation tests in tests/TimeLocker/system_control/test_storage.py; focused run passed 11 tests.
  - Evidence mode: command
  - [x] T002.2 Implement atomic record store and bounded diagnostic stream.
  - Evidence: Implemented AtomicRecordStore with strict schema parsing, per-run atomic JSON replacement, fsync of files and directories, process-safe transition locking, bounded immutable diagnostic records, filtering, and mode enforcement.
  - Evidence mode: artifact
  - [x] T002.3 Implement repository lock leases and startup reconciliation.

  - Evidence: Implemented nonblocking flock repository leases with safe run ownership metadata, conflict behavior, process-exit release, stale metadata clearing, and idempotent startup reconciliation of abandoned queued/running records.
  - Evidence mode: artifact
- [x] T003 Implement Linux local transport and current operator-group
  authorization.
  - Depends on: T002
  - Requirements: Requirement 2 AC2-AC6; Requirement 4 AC1, AC4-AC11
  - Properties: CP-001, CP-006, CP-007, CP-011
  - Files: Linux adapter modules, systemd socket/service assets, security tests
  - Acceptance: The server derives peer credentials, revalidates current
    `timelocker-operators` membership for every protected request, rejects stale
    or self-asserted identity, and leaks no protected metadata on denial.
  - Evidence: Linux local transport, kernel peer-credential adapter, fresh NSS operator-group authorization, strict dispatcher/audit/redaction, root-policy loader, and least-privilege staged unit assets implemented. Focused T003 validation passed 15 tests; no units were installed or activated.
  - Status: Complete and dependency-ready for T004; live socket/unit acceptance remains T010.
  - Evidence mode: command
  - [x] T003.1 Add authorized, unauthorized, removed-member, malformed,
    oversized, and version-mismatch tests.
  - Evidence: Added authorized, unauthorized, membership-removal, handler-failure, self-asserted identity, malformed JSON, oversized request, and version mismatch tests in test_dispatcher.py; Linux adapter suite also covers peer parsing and NSS failures.
  - Evidence mode: command
  - [x] T003.2 Implement `SO_PEERCRED`, NSS group resolver, dispatcher, audit,
    and redaction.
  - Evidence: Implemented SO_PEERCRED parsing, per-request primary/supplementary NSS lookup, strict JSON dispatcher, metadata-free denial/error responses, secret-free audit events, and systemd-activated AF_UNIX transport adapter.
  - Evidence mode: artifact
  - [x] T003.3 Add root-owned policy, runtime directory, socket, and service
    templates with least-privilege modes.

  - Evidence: Added packaged policy JSON plus staged socket/service templates with root ownership intent, timelocker-operators 0660 socket access, restrictive umask, AF_UNIX-only address family, filesystem protections, and no GUI/session or credential environment forwarding.
  - Evidence mode: artifact
- [x] T004 Checkpoint - Foundation security and agent-readiness review.
  - Depends on: T003
  - Files: Spec artifacts and Phase 1 source/tests
  - Acceptance: Focused tests pass, Spec Lifecycle Manager reports bounded task
    context and traceability, and every `review-timelocker`
    security/architecture finding has a recorded disposition before public CLI
    or live rollout.
  - Evidence mode: command
  - Evidence: Phase 1 checkpoint passed: 98 focused tests passed at 88.4% coverage; Ruff check/format, compileall, wheel build and 3/3 asset inventory, git diff --check, spec lint, and T002/T003 task audits passed. The review-timelocker panel identified TLR-001 through TLR-005; all were fixed and their dispositions are recorded in verification.md. Agent Workbench diagnostics had no provider for these Python files, so executed checks and direct review are the proof. No host assets were installed or activated.

  - Status: Phase 1 complete. Real socket activation, installed permissions, live NSS, host restart, and Windows implementation remain assigned to later tasks.
## Phase 2: System CLI and authorized visibility

- [ ] T005 Implement the root-owned system launcher and centralized action
  classification.
  - Depends on: T004
  - Requirements: Requirement 1 AC1-AC4; Requirement 2 AC1-AC6;
    Requirement 6 AC1-AC3
  - Properties: CP-001, CP-006
  - Files: packaging/install assets, launcher/action-policy modules, tests
  - Acceptance: `timelocker` and `tl` resolve one immutable release; user-local
    actions remain unprivileged; protected actions use the backend; invalid
    release or unknown action fails closed without pyenv/checkout fallback.
  - Evidence: Pending.
  - [ ] T005.1 Add launcher resolution, rollback, recursion, and routing tests.
  - [ ] T005.2 Implement immutable release launcher and action classifier.
  - [ ] T005.3 Add staged install/rollback assets without changing the live
    selected release.

- [ ] T006 Add structured system run and diagnostic CLI views.
  - Depends on: T005
  - Requirements: Requirement 4 AC1-AC3, AC6, AC8-AC11
  - Properties: CP-004, CP-006, CP-007, CP-011
  - Files: `src/TimeLocker/cli_modules/commands/monitoring.py`, focused system
    client modules, CLI and integration tests
  - Acceptance: `runs list`, `runs show`, and
    `logs view --scope local|system` clearly distinguish local and system data;
    only current operator-group members receive protected structured records.
  - Evidence: Pending.
  - [ ] T006.1 Add CLI contract, compatibility, denial, and redaction tests.
  - [ ] T006.2 Implement focused `SystemControlClient` integration.
  - [ ] T006.3 Preserve local log behavior and correct `--config-dir`/scope
    resolution without reading protected files directly.

## Phase 3: Independent tray and retention

- [ ] T007 Remove tray ownership from CLI/headless services and add the
  independent tray client.
  - Depends on: T004
  - Requirements: Requirement 3 AC1-AC8; Requirement 4 AC1, AC4-AC9;
    Requirement 6 AC1-AC5
  - Properties: CP-002, CP-006, CP-007, CP-009
  - Files: notification/monitoring services, tray entry point, platform
    adapters, packaging, tray/headless tests
  - Acceptance: CLI, backup, retention, scheduler, and backend paths import no
    tray platform code and emit no tray warning; the user-session tray connects,
    reconnects, displays authorized state, and requests only allowlisted
    actions.
  - Evidence: Pending.
  - [ ] T007.1 Add import-boundary, headless, absence, crash, singleton, and
    reconnect tests.
  - [ ] T007.2 Refactor notification delivery to publish structured state
    without constructing `SystemTrayIntegration`.
  - [ ] T007.3 Add standalone tray entry point and Linux Mint Cinnamon/X11
    adapter.

- [ ] T008 Implement approved retention execution and all three trigger modes.
  - Depends on: T004
  - Requirements: Requirement 5 AC1-AC11; Requirement 6 AC1-AC3, AC6
  - Properties: CP-003, CP-004, CP-005, CP-008, CP-010
  - Files: retention policy/executor/trigger modules, scheduling integration,
    unit/integration tests
  - Acceptance: Dry-run approval fingerprints the complete policy; backup
    success, independent schedule, and explicit request create separate locked
    retention runs; failure or conflict never changes the backup result.
  - Evidence: Pending.
  - [ ] T008.1 Add policy fingerprint, approval, conflict, idempotency, and
    failure-isolation tests.
  - [ ] T008.2 Implement retention executor and protected explicit request.
  - [ ] T008.3 Implement post-backup success trigger after terminal record and
    lock release.
  - [ ] T008.4 Implement independently configurable schedule, disabled in the
    initial production profile.

## Phase 4: Installation, portability, and live acceptance

- [ ] T009 Integrate release assets, platform adapters, upgrade, and rollback.
  - Depends on: T006, T007, T008
  - Requirements: Requirement 1; Requirement 2; Requirement 3 AC6-AC8;
    Requirement 6 AC1-AC6
  - Properties: CP-001, CP-006, CP-008, CP-009
  - Files: build/install scripts, systemd assets, platform adapter contracts,
    package tests
  - Acceptance: One compatibility-checked artifact set installs launchers,
    backend, socket, tray, and schedules; upgrade validates them before
    retirement; rollback restores the prior release without deleting records or
    changing policy.
  - Evidence: Pending.
  - [ ] T009.1 Add artifact manifest, permission, upgrade, and rollback tests.
  - [ ] T009.2 Complete Linux install assets and Windows service/named-pipe test
    double.
  - [ ] T009.3 Prove headless install requires no GUI dependencies.

- [ ] T010 Run controlled Linux Mint live acceptance and rollback rehearsal.
  - Depends on: T009
  - Requirements: Requirements 1-6; SC-001-SC-011
  - Files: `verification.md`, external system assets only after explicit rollout
    approval
  - Acceptance: Authorized and denied system views, system launcher, scheduled
    backup, restore, post-success retention, independent retention, tray
    reconnect, interrupted-run recovery, upgrade, and rollback are evidenced.
  - Evidence mode: validation
  - Evidence: Pending.
  - [ ] T010.1 Stage without changing the working 03:30 backup.
  - [ ] T010.2 Obtain explicit approval before group membership, service,
    launcher, timer, or live-retention mutations.
  - [ ] T010.3 Execute acceptance and record secret-free evidence.
  - [ ] T010.4 Rehearse rollback and confirm backup scheduling remains healthy.

## Phase 5: Promotion, review, and closure

- [ ] T011 Promote accepted behavior into durable documentation.
  - Depends on: T010
  - Files: all promotion targets in `change-impact.md`
  - Acceptance: Durable requirements, architecture, CLI reference,
    installation, tray, scheduling, troubleshooting, rollout, and rollback docs
    match implemented behavior and no future intent is presented as current.
  - Evidence: Pending.

- [ ] T012 Complete expert review, full validation, residual disposition, and
  closure preparation.
  - Depends on: T011
  - Files: Spec verification/traceability, durable docs, closure records
  - Acceptance: Security, Restic/recovery, operations/portability, Python CLI,
    tests, and documentation findings have recorded dispositions; all
    requirements, ACs, and properties have evidence; closure and archive checks
    pass.
  - Evidence mode: validation
  - Evidence: Pending.

## Execution Rules

- Do not implement from this file alone. Load the linked requirement, design,
  traceability, change-impact, and verification context first.
- Mark only one implementation task `[~]` at a time unless tasks have no file
  or state conflict.
- Do not use `AccessManager` sessions as proof of operating-system identity or
  operator-group membership.
- Do not grant `timelocker-operators` direct access to journald, credentials,
  `/var/restic`, raw Restic arguments, or protected source paths.
- Live installation, group membership, service enablement, schedule changes,
  retention mutation, and rollback require explicit operator approval at T010.
- Record evidence before marking any task complete.

## Related Artifacts

- Requirements: `requirements.md`
- Canonical context: `canonical-context.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Traceability: `traceability.md`
- Verification: `verification.md`

## Reconciliation

Reviewed against the 2026-07-26 requirements and design revisions. T001-T006
cover the tightened system-record authorization, audit separation, diagnostic
projection, NSS failure, transport-bound, and storage-hardening work. No task
dependency or live-mutation approval boundary changed.
