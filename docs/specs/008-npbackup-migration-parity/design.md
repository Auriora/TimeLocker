---
title: NPBackup migration parity design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Technical Design

## Overview

Add typed backup execution options at the existing CLI-to-target boundary.
`CLIBackupRequest` and selection-job metadata carry `compression` and
`one_file_system`; `BackupTarget` exposes them to `ResticRepository`, which
validates one invocation-wide value and adds the corresponding Restic flags.
This avoids widening the abstract repository interface or changing unrelated
backend signatures.

Schedules persist `tags`, `exclude_patterns`, `compression`, and
`one_file_system`. `_build_backup_command` remains the single renderer
source for cron, systemd, and Windows and emits current CLI options using
argument-safe platform quoting.

## High-Level Design

### Components And Changes

- The backup CLI and `CLIBackupRequest` accept typed execution options.
- Direct and selection-based orchestrators carry them into `BackupTarget`.
- `ResticRepository` converts consistent target options to Restic argv.
- Schedule storage and `_build_backup_command` preserve the same options
  across cron, systemd, and Windows renderers.

### Data Flow

```text
CLI or stored schedule -> CLIBackupRequest/job metadata -> BackupTarget
  -> ResticRepository -> argument-safe restic backup argv
```

## Low-Level Design

### Contracts And Interfaces

Add optional `compression`, default-false `one_file_system` and
`exclude_caches`, repeatable `exclude_files`, and repeatable allowlisted
`backend_options` fields to `CLIBackupRequest` and `BackupTarget`. Add the same
execution fields to schedule records. The abstract
repository method remains unchanged; the Restic adapter reads invocation
options from the concrete targets it already receives.

### Error Handling

Click validates the public compression choice. The Restic adapter independently
rejects unsupported or inconsistent target values before invoking Restic so
programmatic callers cannot bypass the guardrail.

## Compatibility

- `compression=None` emits no argument and preserves Restic's current default.
- `one_file_system=False` emits no argument.
- Missing schedule fields load as empty/false/none.
- Existing repository adapters may ignore target execution options; Restic is
  the only backend in this migration acceptance path.

## Validation And Failure Handling

- Validate compression at the CLI and Restic adapter boundary.
- Reject conflicting target-level invocation options rather than choosing one.
- Accept only `s3.storage-class` as the initial migrated backend option and
  validate its Restic-supported value before invoking the repository.
- Test direct and selection-based backup propagation.
- Test stored schedule creation, editing, display, parser round trip, and all
  renderers.
- Run focused tests, CLI help checks, compile, and whitespace checks before the
  Phase 1 checkpoint.

## Operator Staging Design

After Phase 1 is committed, build a wheel and install it into a root-owned
virtual environment such as `/opt/timelocker/venv`. Store configuration under
`/etc/timelocker` and reference a mode-0600 root-owned environment file. Attach
to the existing repository read-only, list and restore snapshot `8958659e`,
then stage a disabled system timer at a non-overlapping time. Retention remains
simulation-only during overlap.

The T007 host reconciliation found 252 unique patterns across three NPBackup
exclude files, cache-directory exclusion enabled, and
`s3.storage-class=INTELLIGENT_TIERING`. Preserve the files by reference rather
than expanding their contents into generated unit arguments; preserve cache
semantics with Restic `--exclude-caches` and the storage class through the
allowlisted global backend option.

## Security And Rollback

No NPBackup ciphertext is copied as a usable credential. Credential transfer
must use operator-supplied values or an explicitly approved secure export that
never prints values. For this host, the operator approved a byte-identical copy
of the existing Restic service-account environment into the root-owned,
mode-0600 `/etc/timelocker/npbackup-migration.env`; its values remain outside
repository and session evidence. Phase 1 rollback is a code revert. Later host
rollback is disabling/removing the TimeLocker timer while leaving root's
NPBackup cron untouched until final cutover approval.

## Durable Promotion

Promote accepted CLI options to user backup guidance and schedule fields to the
operator scheduling guide. Production installation and cutover evidence remain
in verification until accepted, then only current operating instructions are
promoted.

## Operational Considerations

Phase 1 changes code, tests, and durable guidance only. Root installation,
credential provisioning, repository attachment, timer installation, retention,
and NPBackup cutover remain explicit Phase 2 operator gates.

## Resolved Decisions

- D001 is resolved: `/etc/timelocker/npbackup-migration.env`, copied without
  value output from the existing Restic service-account environment, supplies
  the production repository and backend credentials.

## Resolved T007 Reconciliation

- The effective NPBackup exclusion set requires explicit migration support:
  three reviewed exclusion files remain referenced, and cache-directory
  exclusion is carried separately. Expanding 252 patterns into generated unit
  arguments is rejected because it duplicates another tool's maintained files.

## Open Questions

- No implementation question remains for T007. D002 remains the separate
  operator decision about production schedule retention and NPBackup cutover.
