---
title: NPBackup migration parity tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Tasks

## Phase 1: Implement Migration Parity

- [x] T001 Create and reconcile the migration-parity package.
  - Depends on: Spec 007 implementation commit `433c0aa`
  - Requirements: Requirement 1, Requirement 2, Requirement 3
  - Acceptance Criteria: all
  - Properties: CP-001-CP-005
  - Acceptance: Safe host evidence, sequencing, implementation boundary, and
    later operator gates are explicit and contain no secret values.
  - Evidence: Spec Lifecycle Manager allocated `008`; the approved read-only
    host inspection identified the active root cron, six sources, option and
    retention shape, exclusion sources, and recent snapshot without changing
    host state or revealing plaintext credentials.
  - Evidence mode: artifact

- [x] T002 Carry compression and filesystem-boundary options to Restic.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: AC1-AC4
  - Properties: CP-002, CP-003
  - Files: backup CLI/request/target/orchestrator paths, Restic adapter, tests
  - Acceptance: Direct and selection backups propagate valid options; invalid
    or conflicting options fail before execution; defaults remain compatible.
  - Validation: Focused CLI, service, target, and Restic command tests.
  - Evidence mode: implementation

  - Evidence: Implemented compression and one-filesystem propagation through direct CLI requests, selection-job metadata, BackupTarget, configuration, both orchestrator paths, and Restic argv. Adapter validation rejects invalid or conflicting values before subprocess execution; defaults emit no new arguments. Focused parity suite contribution passed within 99 tests on 2026-07-19.
- [x] T003 Persist and render schedule parity fields.
  - Depends on: T002
  - Requirement: Requirement 2
  - Acceptance Criteria: AC1-AC4
  - Properties: CP-001, CP-004
  - Files: schedule CLI/renderers, tests, operator guide
  - Acceptance: Create/edit/show/test and all renderers preserve tags,
    exclusions, compression, and one-filesystem intent with safe quoting.
  - Validation: Focused schedule tests and parser round trip.
  - Evidence mode: implementation

  - Evidence: Schedule create/edit persist tags, exclusions, compression, and one-filesystem fields; list/show expose them; test validates the generated command; cron, systemd, and Windows render from the shared argument-safe builder. Durable backup and scheduling guides were promoted. Focused parity suite passed 99 tests on 2026-07-19.
- [x] T004 Checkpoint - Phase 1 parity ready for host staging.
  - Depends on: T002, T003
  - Requirements: Requirement 1, Requirement 2, Requirement 3 AC1
  - Properties: CP-001-CP-005
  - Acceptance: Focused tests, CLI help, lifecycle checks, compile, docs, and
    whitespace checks pass; host scheduler and credentials remain unchanged.
  - Decision owner: project maintainer
  - Evidence mode: validation

  - Evidence: Phase 1 checkpoint passed on 2026-07-19: 99 focused tests and the full normal profile (2,796 passed, one skipped, 57 deselected, 52.52% coverage) passed; compileall, git diff --check, zero-diagnostic Spec 008 lint, and zero-finding durable-guide Markdown checks passed. Read-only root-cron comparison still shows the 17:30 NPBackup job; no TimeLocker unit or /opt/timelocker installation exists, and no credential values were read or written.

## Phase 2: Operator-Controlled Installation And Observation

- [x] T005 Resolve the secure production repository and credential source.
  - Depends on: T004
  - Requirement: Requirement 3
  - Acceptance: Exact URI and required environment values are supplied through
    a root-only path without being printed or copied from masked ciphertext.
  - Decision owner: operator
  - Evidence mode: manual

  - Evidence: Operator-approved T005 completed on 2026-07-19: `/etc/timelocker/npbackup-migration.env` is root:root mode 0600 and byte-identical to the existing Restic service-account environment. It contains exactly the five expected non-empty Restic/AWS assignments and loads successfully as root; no values were emitted. Root's 17:30 NPBackup cron is unchanged, and no TimeLocker unit or `/opt/timelocker` installation exists.
  - Status: D001 resolved; protected credential source ready. T006 privileged artifact installation remains separately gated.
- [~] T006 Install a committed root-owned TimeLocker artifact and attach read-only.
  - Depends on: T005 and explicit privileged-install approval
  - Requirement: Requirement 3
  - Acceptance: Root-owned versioned installation lists and restores existing
    snapshot `8958659e`; NPBackup remains unchanged.
  - Evidence mode: validation

  - Evidence: Operator authorized T006 on 2026-07-19. The validated Phase 1/T005 tree will be committed before building; only that commit may be installed. Repository access is limited to snapshot listing and a bounded restore, with NPBackup and scheduling unchanged.
  - Evidence: Phase 1 was committed as `2c93709`; its root-owned release listed
    the protected repository and found snapshot `8958659e`. The first bounded
    restore exposed two recovery defects before Restic ran: selective validation
    supplied an unsupported selection name, and include/exclude paths were not
    propagated to the backend. The repair removes the invalid field and carries
    bounded paths through the restore interfaces to repeated Restic arguments;
    64 focused recovery and adapter tests pass.
  - Status: Preparing a replacement committed artifact for the live bounded
    restore; production backup and timer operations remain prohibited.
- [ ] T007 Stage, install, and observe a non-overlapping TimeLocker timer.
  - Depends on: T006 and explicit timer-install approval
  - Requirement: Requirement 3
  - Acceptance: Production-equivalent sources/options run successfully on the
    scheduler and a subsequent restore passes; no retention deletion runs.
  - Evidence mode: validation

- [ ] T008 Checkpoint - Separate NPBackup cutover decision.
  - Depends on: T007
  - Requirement: Requirement 3
  - Acceptance: Evidence supports a deliberate decision to retain, disable, or
    roll back TimeLocker; changing root's NPBackup cron requires explicit approval.
  - Decision owner: operator
  - Evidence mode: manual

## Rules Consulted

Coding Standards (100), General Preferences (50), Operational Best Practices
(40), Planning Protocol (30), Testing Conventions (25), Documentation
Conventions (20), and Git Conventions (15). User approval on 2026-07-19 covers
Phase 1 implementation and the separate T005 credential copy. T006-T008
privileged installation, scheduling, and cutover gates remain separate.
