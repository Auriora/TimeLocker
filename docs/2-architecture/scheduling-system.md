---
title: "Architecture Document: Scheduling System"
id: "arch-scheduling-system"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "2026-07-26"
tags: [architecture, scheduling, backup, retention]
links:
  tooling: []
---

# Architecture Document: Scheduling System

## Purpose

Describe the implemented scheduling boundaries for user-managed backup
schedules and protected system backup and retention operations.

## Scheduling Surfaces

TimeLocker has two distinct scheduling surfaces:

1. `tl schedule` stores schedule definitions and generates native scheduler
   assets for user-managed backups. Generation is non-mutating; an operator
   must review and install the assets.
2. A protected Linux deployment uses root-owned systemd units for the approved
   system backup and retention target. These units execute through the selected
   immutable TimeLocker release and write structured run records through the
   system-control layer.

The source package contains adapters for systemd, cron, launchd, and Windows
Task Scheduler. The protected system-control deployment has live acceptance
evidence on Linux Mint with systemd. Other protected-host adapters are not
claimed as live-accepted by this document.

## Protected Operation Flow

```text
backup timer or authorized request
              |
              v
      allowlisted backup unit
              |
              v
 durable backup RunRecord + repository lock
              |
       backup completes
        /           \
   success          failure
      |                |
      v                v
release lock      terminal backup record
      |
      v
separate retention RunRecord (backup-success trigger)
```

Retention may also start from its independent timer or from an authorized
operator request. It does not require a preceding successful backup. When it
follows a successful backup, it starts as a separate run only after the backup
has reached a terminal success state and released the shared repository lock.

## Retention Contract

The packaged production policy keeps 5 daily, 4 weekly, 12 monthly, and
3 yearly snapshots, grouped by `host,paths`. Prune is disabled. A production
retention mutation is accepted only when all of the following are true:

- the root-owned enable marker exists;
- the requested policy fingerprint matches the protected approved policy;
- the protected repository and credential references still match the approved
  target; and
- the shared repository mutation lock is available.

Dry runs do not remove snapshots. A lock conflict produces a structured skipped
run rather than overlapping a backup or another retention operation.

## Run State and Recovery

Backup and retention runs use durable states: queued, running, succeeded,
failed, skipped, or interrupted. Start and finish hooks bind systemd backup
execution to one run identifier. On startup, an unfinished active record is
reconciled to interrupted before new work proceeds.

System run history is read with:

```bash
timelocker runs list
timelocker runs show RUN_ID
```

These commands cross the protected local backend and are available only to
current members of the configured operator group.

## Failure Isolation

- Backup failure does not start backup-success retention.
- Independent retention remains eligible regardless of the most recent backup
  result.
- Retention failure does not rewrite a successful backup result.
- A repository lock conflict skips the later operation.
- Credentials, repository passwords, raw backend output, protected file paths,
  and raw journald content are not placed in run records.

## Platform Assets

The Linux package supplies:

- `timelocker-control.socket` and `timelocker-control.service`;
- `timelocker-retention.service` and `timelocker-retention.timer`;
- stable launchers under `/usr/local`; and
- an independent user-session tray launcher.

The generic retention timer uses a daily calendar. Administrators may choose a
specific local time when installing the deployment, provided backup and
retention still share the repository lock. The accepted reference deployment
uses a 03:30 backup and a 00:00 independent retention run; those times are not
portable defaults.

## Change Rules

Update this document when trigger semantics, locking, durable run states,
supported protected-host adapters, or the retention safety contract changes.
Host-specific credentials, repository URIs, and secrets never belong here.

## References

- [System Operations Requirements](../1-requirements/system-operations.md)
- [System Architecture](./system-architecture.md)
- [Scheduling Guide](../guides/developer/scheduling-guide.md)
- [Backup Operations Troubleshooting](../guides/user/backup-operations-troubleshooting.md)
