---
title: "Backup and Recovery Operations"
id: "user-guide-recovery-operations"
type: [ guide ]
status: [ approved ]
owner: "Operations Team"
last_reviewed: "19-07-2026"
tags: [guide, user, backup, recovery]
links:
  tooling: []
---

# Backup and Recovery Operations

This guide covers the current TimeLocker-owned path from repository access to a
digest-verified restore. Use `tl <command> --help` for the complete option set.

## Prerequisites

- Restic is installed and available on `PATH`.
- The named repository is present in TimeLocker configuration.
- Its credential is available from the configured credential store, an
  environment variable, a protected environment file loaded by the caller, or
  an explicit interactive command option.
- Backup sources exist and the executing user can read them.
- Restore targets have enough space and are writable.

Repository passwords are runtime inputs. TimeLocker does not persist them in a
backup result or generated schedule. See
[Per-Repository Credentials](./per-repo-credentials.md).

## Initialize and verify a repository

For a configured repository named `primary`, load the intended environment and
initialize without placing the password on the command line:

```bash
set -a
. ~/.config/timelocker/backup.env
set +a
tl repos init primary --yes --config-dir ~/.config/timelocker
```

If the repository already exists, TimeLocker reports that state without
reinitializing it. An explicit `--password` remains available for interactive
use, but shell history makes the protected environment or credential store
preferable.

## Preview a backup

Direct files and directories are valid sources. A dry run validates the source
and reports the planned file and byte totals without creating a snapshot:

```bash
tl backup create ~/Documents/report.odt \
  --repository primary \
  --dry-run \
  --config-dir ~/.config/timelocker

tl backup create ~/Documents \
  --repository primary \
  --dry-run \
  --config-dir ~/.config/timelocker
```

Missing sources and invalid targets fail before retry. Alternatively, use one
configured selection:

```bash
tl backup create \
  --selection documents \
  --repository primary \
  --dry-run \
  --config-dir ~/.config/timelocker
```

## Create a snapshot

Remove `--dry-run` only after reviewing the preview:

```bash
tl backup create ~/Documents/report.odt \
  --repository primary \
  --tags manual-check \
  --config-dir ~/.config/timelocker
```

When migrating an existing Restic job, preserve its reviewed execution
semantics explicitly. Compression accepts `auto`, `off`, or `max`;
`--one-file-system` prevents traversal into other mounted filesystems and
subvolumes. Both options work with direct paths and selection templates:

```bash
tl backup create /home /etc /var /srv /root /nix/var \
  --repository primary \
  --tags Bruce-5560 \
  --exclude 'cache/*' \
  --exclude-file /etc/timelocker/excludes \
  --exclude-caches \
  --backend-option s3.storage-class=INTELLIGENT_TIERING \
  --compression max \
  --one-file-system \
  --dry-run \
  --config-dir ~/.config/timelocker
```

Omitting these options preserves the existing defaults: TimeLocker does not
add a Restic compression argument and permits cross-filesystem traversal.
Unsupported compression values fail CLI validation before repository access.
Exclusion files remain external inputs and must be readable by the backup
service account. `--exclude-caches` preserves Restic's CACHEDIR.TAG semantics.
Backend options are validated before execution; the initial migration
allowlist accepts only documented `s3.storage-class` values.

Record the full snapshot ID from the result or JSON listing. Reported file and
byte counts come from Restic's summary.

## List and inspect snapshots

The restore listing exposes the full ID, canonical timestamp, host, user, tags,
and source paths:

```bash
tl restore list primary --config-dir ~/.config/timelocker
tl restore list primary --format json --config-dir ~/.config/timelocker
tl restore browse primary latest --config-dir ~/.config/timelocker
tl restore find primary '*.odt' --config-dir ~/.config/timelocker
```

`latest` resolves to the newest snapshot. An exact full ID or unambiguous ID
prefix is also accepted.

## Restore safely

Restore into a fresh directory first:

```bash
mkdir -p ~/timelocker-restore-check
tl restore full primary latest ~/timelocker-restore-check \
  --config-dir ~/.config/timelocker
```

Restore an exact snapshot when reproducing a particular recovery point:

```bash
tl restore full primary 0123456789abcdef ~/timelocker-exact-check \
  --config-dir ~/.config/timelocker
```

The default restore path requests verification. Use `--no-verify` only when an
independent validation step is deliberately taking its place. `--overwrite`
must be explicit when existing target files may be replaced.

For selected paths:

```bash
tl restore files primary latest /home/user/Documents/report.odt \
  --target ~/timelocker-file-check \
  --config-dir ~/.config/timelocker
```

## Verify recovered content

Compare a known reference after the restore:

```bash
sha256sum ~/Documents/report.odt
sha256sum ~/timelocker-restore-check/home/user/Documents/report.odt
```

The digests must match. Keep the existing backup scheduler active until a
TimeLocker-created snapshot has been listed and restored through TimeLocker and
scheduled TimeLocker runs have been observed successfully.

## Common failures

- **Repository not found:** pass the intended `--config-dir` and confirm `tl
  repos list` shows the name.
- **Wrong password or repository unavailable:** load the intended credential
  source and run `tl repos check <name>` before retrying.
- **Source missing:** correct the direct path or selection; TimeLocker will not
  retry a deterministic path-validation failure.
- **Tray unavailable:** this does not block backup or recovery. Install the
  optional Linux GUI prerequisites described in
  [Installation](./installation.md) if tray status is wanted.
- **Scheduled command differs from a successful manual run:** compare its user,
  environment-file reference, repository, source or selection, executable, and
  `--config-dir` with the manual command. See the
  [Scheduling Guide](../developer/scheduling-guide.md).

## References

- [Repository Management](./repository-management-guide.md)
- [Per-Repository Credentials](./per-repo-credentials.md)
- [Installation](./installation.md)
- [Scheduling Backups](../developer/scheduling-guide.md)
