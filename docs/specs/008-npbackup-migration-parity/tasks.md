---
title: NPBackup migration parity tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-20
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
- [x] T006 Install a committed root-owned TimeLocker artifact and attach read-only.
  - Depends on: T005 and explicit privileged-install approval
  - Requirement: Requirement 3
  - Acceptance: Root-owned versioned installation lists and restores existing
    snapshot `8958659e`; NPBackup remains unchanged.
  - Evidence mode: validation

  - Evidence: Committed selective-restore repair `6896c8d` passed 64 focused tests and the full normal profile (2,797 passed, one skipped, 57 deselected, 52.53% coverage). Wheel SHA-256 `876246c4783d63f4d9f1fae80c5a4180afe95fbcb5161df01278e5b60de8da3c` was installed root-owned at `/opt/timelocker/releases/6896c8d6d90cb4c8320ec1fa66b966d9eb2dabcd`; both entry points report 0.9.1. The protected named repository listed snapshot `8958659e`; a bounded `/etc/hostname` restore produced a nonempty root-only result matching the live file byte-for-byte. Root's 17:30 NPBackup cron remains present; no TimeLocker cron entry, systemd unit, or timer exists. No backup, retention, schedule, or cutover action ran.
  - Evidence: Phase 1 was committed as `2c93709`; its root-owned release listed
    the protected repository and found snapshot `8958659e`. The first bounded
    restore exposed two recovery defects before Restic ran: selective validation
    supplied an unsupported selection name, and include/exclude paths were not
    propagated to the backend. The repair removes the invalid field and carries
    bounded paths through the restore interfaces to repeated Restic arguments;
    64 focused recovery and adapter tests pass.
  - Status: T006 complete. T007 remains separately gated by explicit timer-install approval.
- [x] T007 Stage, install, and observe a non-overlapping TimeLocker timer.
  - Depends on: T006 and explicit timer-install approval
  - Requirements: Requirement 1, Requirement 3
  - Acceptance Criteria: Requirement 1 AC5; Requirement 3 AC3-AC4
  - Properties: CP-006
  - Acceptance: Production-equivalent sources/options run successfully on the
    scheduler and a subsequent restore passes; no retention deletion runs.
  - Evidence mode: validation

  - Evidence: Root-owned release from commit `daaad53` (wheel SHA-256 `5c3106e573d3805b3e9962007c20d5e47cd88faccb1ac8d20c0c1f315f212867`) was installed under `/opt/timelocker/releases/daaad538f7adb02e27e86b744af43ead79f07408`. The NPBackup overlap condition passed and the controlled systemd run used the native repository URI `s3:s3.af-south-1.amazonaws.com/5560-restic` with six production sources, tag `Bruce-5560`, three direct exclusions, three exclusion files, cache exclusion, `s3.storage-class=INTELLIGENT_TIERING`, compression `max`, and one-filesystem traversal. It completed successfully on 2026-07-19 as snapshot `f7417b35ab2e497052e33894d5b084a16260bc71e5c76780c7405cbf4454551f` (659,639 files; 455,495,193 bytes). The normal 2026-07-20 03:30 timer run also completed successfully as snapshot `ffafd15e6948ba278101463f85ac192176e83f8e423d109b5c06254859197de9`. A bounded `tl restore files` of `/etc/hostname` from `f7417b35...` to `/var/lib/timelocker/verification/restore-f7417b35` completed and matched `/etc/hostname` byte-for-byte. The timer's invalid service dependency was removed on-host and from the generator; 43 focused schedule/integration tests passed. After one harmless persistent catch-up snapshot (`a57f037d...`), the service is inactive and the enabled timer is waiting for 2026-07-21 03:30. NPBackup remains active; no retention, prune, or cutover action ran.
  - Evidence: Masked NPBackup reconciliation found three exclusion files with
    252 unique patterns, cache-directory exclusion enabled, and reviewed
    `s3.storage-class=INTELLIGENT_TIERING` intent. These must be carried by the
    committed TimeLocker artifact before the timer may run.
  - Evidence: The 19:30 timer triggered and its NPBackup exclusion condition
    passed, but the service exited by `SIGTRAP` before Restic started because
    GTK tray initialization ran without a display. No backup or retention
    operation completed. Commit `2eb9928` now skips native Linux tray startup
    when neither `DISPLAY` nor `WAYLAND_DISPLAY` is present. Seven focused
    tests and the full normal profile passed: 2,798 passed, one skipped, 57
    deselected, and 52.55% coverage. The replacement wheel SHA-256 is
    `c6998f9af68068185d80ad6261086fdc0dd8092cc38d97565a529bce1ab421e5`.
  - Status: Complete: production-equivalent scheduled backup and subsequent
    bounded restore passed. T008 subsequently completed the separately approved
    option-2 cutover.
- [x] T008 Checkpoint - Separate NPBackup cutover decision.
  - Depends on: T007
  - Requirement: Requirement 3
  - Acceptance: Evidence supports a deliberate decision to retain, disable, or
    roll back TimeLocker; changing root's NPBackup cron requires explicit approval.
  - Decision owner: operator
  - Evidence mode: manual

  - Evidence: On 2026-07-20 the operator selected cutover option 2. The guarded root cutover verified the TimeLocker timer enabled and active, refused overlap with a running service, saved root's prior crontab at /var/lib/timelocker/migration-backup/root-crontab-before-cutover-20260720T054308Z, and disabled the single active NPBackup cron entry. The TimeLocker timer remained active with next run Tue 2026-07-21 03:30:00 IST. Retention automation is not configured; the existing manual forget process remains required.
  - Status: Complete: TimeLocker retained as the scheduled backup and the NPBackup cron entry disabled with an explicit rollback artifact; retention remains manual.
## Rules Consulted

Coding Standards (100), General Preferences (50), Operational Best Practices
(40), Planning Protocol (30), Testing Conventions (25), Documentation
Conventions (20), and Git Conventions (15). User approvals covered Phase 1,
the T005 credential copy, T006 installation, T007 timer observation, and the
T008 option-2 cutover. The NPBackup cron entry is disabled with a root-only
rollback artifact. Retention is unchanged and remains manual.
