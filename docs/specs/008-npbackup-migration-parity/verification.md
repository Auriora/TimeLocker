---
title: NPBackup migration parity verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-20
---

# Verification

## Quality Gates

| Gate | Status | Evidence |
|------|--------|----------|
| Package and traceability ready | passed | Zero Spec 008 lifecycle lint diagnostics; readiness selects T005 after T004. |
| Direct backup parity | passed | T002 focused CLI, target, and Restic tests. |
| Selection backup parity | passed | T002 handler metadata and orchestrator target tests. |
| Stored and rendered schedule parity | passed | T003 create/edit/show/list and cron/systemd/Windows tests. |
| Phase 1 host state unchanged | passed | Root cron still contains the 17:30 NPBackup job; no TimeLocker unit installed. |
| Durable guidance promoted | passed | Both current guides pass bounded Markdown checks with zero findings. |
| Production attachment and restore | passed | Root-owned release `6896c8d` listed snapshot `8958659e` and restored `/etc/hostname` selectively with a byte-for-byte match. |
| Scheduled production observation | passed | Controlled snapshot `f7417b35`, the normal 03:30 snapshot `ffafd15e`, and a subsequent byte-matched bounded restore passed. |
| NPBackup cutover | blocked | T008 remains a separate explicit operator decision; NPBackup is unchanged. |

## Baseline Evidence

- Spec 007 implementation is committed at `433c0aa` with 2,787 normal-profile
  tests passing and 52.38% coverage.
- Root cron runs NPBackup at 17:30 over six protected sources. The most recent
  verified snapshot is `8958659e` from 2026-07-18.
- NPBackup configuration is valid and credentials remain encrypted; no service,
  crontab, repository, or credential state changed during discovery.

## Requirement Coverage

| Requirement | Acceptance criteria covered | Evidence | Residual risk |
|-------------|-----------------------------|----------|---------------|
| Requirement 1 | AC1-AC5 | T002 focused tests, normal-profile coverage, and live production-equivalent Restic command evidence | none |
| Requirement 2 | AC1-AC4 | T003 stored schedule and renderer tests | none for Phase 1 |
| Requirement 3 | AC1-AC4 | Protected credential source, committed root-owned release, repository listing, non-overlapping scheduled runs, bounded restore, and unchanged NPBackup fallback | Cutover remains a separate T008 decision. |

## Evidence Log

| Date | Evidence | Result | Notes |
|------|----------|--------|-------|
| 2026-07-19 | Spec 007 commit and full normal-profile test evidence | pass | Dependency commit `433c0aa`; 2,787 passed. |
| 2026-07-19 | Read-only masked NPBackup configuration, root cron, journal, and Restic snapshot inspection | pass | Root job remains `30 17 * * *`; snapshot `8958659e`; no plaintext secret captured. |
| 2026-07-19 | Focused Phase 1 parity suite | pass | 99 tests passed in 14.29 seconds with coverage disabled for the focused run. |
| 2026-07-19 | Full normal profile | pass | `python -m pytest -m "not performance and not stress and not minio"` exited 0: 2,796 passed; 52.52% coverage in 953.40 seconds. |
| 2026-07-19 | Compile and workspace hygiene | pass | `compileall` and `git diff --check` completed successfully. |
| 2026-07-19 | Current durable-guide Markdown checks | pass | `check_markdown_set`: two documents checked, zero findings. |
| 2026-07-19 | Spec 008 lifecycle checks | pass | `lint_spec_package`: error=0, warn=0; `task_state_audit`: error=0, warn=0. |
| 2026-07-19 | Post-implementation host comparison | pass | Root crontab is unchanged with NPBackup at 17:30; no installed TimeLocker unit or `/opt/timelocker` path. |
| 2026-07-19 | T005 protected credential-source installation | pass | Root-only `/etc/timelocker/npbackup-migration.env` is a mode-0600, root-owned, byte-identical copy containing exactly the five expected non-empty assignments; values were not emitted. |
| 2026-07-19 | T005 post-install host comparison | pass | Root loaded all required variables; NPBackup cron remained unchanged, with no TimeLocker unit or `/opt/timelocker` installation. |
| 2026-07-19 | First committed T006 artifact and repository attachment | partial | Root-owned release from `2c93709` reported version 0.9.1 and listed snapshot `8958659e` through the protected named repository without changing NPBackup. |
| 2026-07-19 | First T006 bounded restore | fail-safe | Root-only log `restore-8958659e.log` records `SelectionConfig.__init__()` rejecting keyword `name` before Restic invocation; code review found include/exclude paths were also dropped. No full restore or backup ran. |
| 2026-07-19 | Selective-restore repair focused suite | pass | 64 adapter, restore-manager, orchestrator, and repository tests passed with coverage disabled; tests verify include/exclude propagation and completed selective orchestration. |
| 2026-07-19 | Replacement T006 committed artifact | pass | Wheel SHA-256 `876246c4783d63f4d9f1fae80c5a4180afe95fbcb5161df01278e5b60de8da3c` was built from `6896c8d`, installed root-owned under `/opt/timelocker/releases/`, and both entry points reported 0.9.1. |
| 2026-07-19 | T006 protected repository listing and bounded restore | pass | Snapshot `8958659e` was present; selective `/etc/hostname` restore produced a nonempty file matching the live file byte-for-byte. Output remains in root-only verification logs. |
| 2026-07-19 | T006 scheduler safety comparison | pass | Root `crontab -l`, `systemctl list-unit-files`, and `systemctl list-timers --all` checks found the 17:30 NPBackup job and zero TimeLocker scheduler entries. No backup, retention, schedule, or cutover operation ran. |
| 2026-07-19 | Repaired-artifact full normal profile | pass | `python -m pytest -m "not performance and not stress and not minio"` exited 0: 2,797 passed, one skipped, 57 deselected, and 52.53% coverage in 803.23 seconds. |
| 2026-07-19 | T007 masked execution-parity reconciliation | pass | Three exclusion files contain 252 unique patterns; cache exclusion and `s3.storage-class=INTELLIGENT_TIERING` are enabled. No credential value was emitted. |
| 2026-07-19 | T007 focused parity profile | pass | 77 backup, CLI, schedule, target, and selection tests passed with coverage disabled. |
| 2026-07-19 | T007 full normal profile | pass | `python -m pytest -m "not performance and not stress and not minio"` exited 0: 2,797 passed, one skipped, 57 deselected, and 52.56% coverage in 797.47 seconds. |
| 2026-07-19 | T007 committed artifact and timer staging | pass | Commit `3a4572c`, wheel SHA-256 `90c45af99b3e6c913757fcc9539afe91ae5c6c735556ee252a015637c9dbbbf8`, generated-unit parity, installation, and active-timer checks passed. The first observation trigger was set for 19:30, safely after NPBackup. |
| 2026-07-19 | T007 first scheduler observation | fail-safe | The 19:30 timer and non-overlap condition ran, but the service exited by `SIGTRAP` during GTK tray initialization before Restic started. No backup, retention, or cutover operation completed. |
| 2026-07-19 | T007 headless-service repair | pass | Commit `2eb9928` skips native Linux tray startup without `DISPLAY` or `WAYLAND_DISPLAY`. Seven focused tests passed; the full normal profile passed 2,798 tests with one skipped, 57 deselected, and 52.55% coverage. Replacement wheel SHA-256: `c6998f9af68068185d80ad6261086fdc0dd8092cc38d97565a529bce1ab421e5`. Privileged installation and live retry remain pending. |
| 2026-07-19 | T007 native S3 URI repair | pass | Commit `daaad53` preserves Restic-native repository URIs during the CLI service manager's second resolution pass. The exact root-owned wheel SHA-256 is `5c3106e573d3805b3e9962007c20d5e47cd88faccb1ac8d20c0c1f315f212867`; 84 focused/adjacent tests passed. The full configured suite reached 52.89% coverage with 2,857 passed, one skipped, and one unrelated timing-threshold miss that passed three immediate reruns. |
| 2026-07-19 | T007 controlled production backup | pass | The NPBackup overlap condition passed. Restic received the native S3 URI and all production parity options. Snapshot `f7417b35ab2e497052e33894d5b084a16260bc71e5c76780c7405cbf4454551f` completed with 659,639 files and 455,495,193 bytes; no retention or cutover ran. |
| 2026-07-20 | T007 normal scheduled backup | pass | The enabled 03:30 timer completed snapshot `ffafd15e6948ba278101463f85ac192176e83f8e423d109b5c06254859197de9` with 659,639 files and 16,771,834 bytes. |
| 2026-07-20 | T007 post-backup bounded restore | pass | `tl restore files` restored `/etc/hostname` from `f7417b35...` into root-only verification storage; the restored file matched the live file byte-for-byte. |
| 2026-07-20 | T007 timer dependency repair | pass | The invalid generated `Requires=...service` dependency was removed on-host and from the renderer. One persistent catch-up run completed safely as `a57f037d...`; 43 focused schedule/integration tests passed. The service is inactive and the enabled timer is waiting for 2026-07-21 03:30. |

## Residual Risks

- Credential values now exist in a second protected location and must be
  rotated when the source Restic service-account environment changes.
- Same-repository overlap can lock or duplicate work; timers must not overlap.
- A manual restart of a persistent timer after a missed calendar event can
  legitimately trigger one catch-up run; operators must observe service state
  when changing installed timer configuration.
- Retention enforcement can delete snapshots and remains simulation-only until
  separately reviewed.
- The first installed T006 artifact is retained for rollback; the accepted
  `current` release is the repaired `daaad53` artifact.
- NPBackup cutover remains an external mutation requiring separate approval.

## Readiness Decision

- **Phase 1 ready for host staging:** yes
- **Credential source ready for production attachment:** yes; T005 passed.
- **Ready for production repository attachment:** yes; T006 passed listing and
  bounded restore from the committed root-owned artifact.
- **Ready for scheduled TimeLocker backups:** yes; T007 passed controlled and
  normal timer runs plus a subsequent bounded restore.
- **Ready for NPBackup cutover:** no; T008 and explicit operator approval remain
  pending.
