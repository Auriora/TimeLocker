---
title: "Operator Guide: Scheduling Backups And Retention"
id: "guide-scheduling"
type: [ guide ]
status: [ approved ]
owner: "Auriora Team"
last_reviewed: "2026-07-26"
tags: [guide, developer, operator, scheduling, retention]
links:
  tooling: []
---

# Operator Guide: Scheduling Backups And Retention

## Purpose

Configure reviewable user schedules and operate the protected Linux system
backup and retention schedules without exposing credentials.

## User-Managed Schedules

Create schedules disabled, then generate assets into a staging directory:

```bash
tl schedule create nightly-documents \
  --repository my-repository \
  --source "$HOME/Documents" \
  --cron-expression "30 3 * * *" \
  --environment-file "$HOME/.config/timelocker/backup.env"

tl schedule generate-scripts nightly-documents \
  --platform systemd \
  --output "$HOME/.local/share/timelocker/staged-schedules"
```

Review generated commands, absolute executable paths, source and exclusion
arguments, the configuration directory, environment-file permissions, and
calendar behavior before installation. Asset generation does not install,
enable, start, or disable a scheduler.

Inspect the stored definition with:

```bash
tl schedule list
tl schedule show nightly-documents
tl schedule test nightly-documents
```

## Protected System Schedule

The protected Linux deployment is administrator-installed. It uses root-owned
systemd units, root-owned configuration under `/etc/timelocker`, durable state
under `/var/lib/timelocker`, and the stable launcher selected under
`/opt/timelocker`.

Inspect it without reading secret files:

```bash
systemctl status timelocker-control.socket
systemctl status timelocker-npbackup-migration.timer
systemctl status timelocker-retention.timer
systemctl list-timers 'timelocker-*'
```

The backup unit records each scheduled or authorized invocation. On successful
completion it may request retention as a separate `backup-success` run.
Retention also has an independent timer and may be requested explicitly by an
authorized operator. It therefore does not need a separate *dependency* on a
backup, even when the chosen deployment also runs it after successful backups.

## Retention Safety

The current protected policy is:

```text
keep daily:   5
keep weekly:  4
keep monthly: 12
keep yearly:  3
group by:     host,paths
prune:        disabled
```

Production mutation requires the root-owned enable marker and an exact approved
policy fingerprint. Changing any repository reference, credential reference,
filter, retention count, grouping, or prune setting changes that fingerprint
and requires an administrator to review and approve the new policy.

Backup and retention share a repository mutation lock. A conflict is recorded
as skipped; do not bypass the lock by calling Restic directly while an operation
is active.

## Operator Visibility

Current members of `timelocker-operators` can inspect protected records:

```bash
timelocker runs list --limit 20
timelocker runs list --operation backup
timelocker runs list --operation retention
timelocker runs show RUN_ID
timelocker logs view --scope system --lines 100
```

`timelocker logs view` without `--scope system` reads the invoking user's local
CLI log and does not contain protected scheduled-run records.

## Cutover From Another Scheduler

1. Reproduce the existing repository, sources, exclusions, tags, traversal
   behavior, environment reference, and calendar in a disabled TimeLocker
   schedule.
2. Dry-run and manually exercise the exact protected target.
3. Complete a backup and a restore acceptance test.
4. Approve the retention fingerprint and verify a dry run.
5. Install and enable TimeLocker timers.
6. Confirm `runs list` contains successful backup and retention records.
7. Disable the legacy scheduler only after TimeLocker acceptance succeeds.
8. Preserve the legacy scheduler configuration and crontab as rollback
   evidence until the observation window is complete.

## Rollback

If scheduling or the selected release is unhealthy:

1. disable the affected TimeLocker timer;
2. inspect structured runs and diagnostics;
3. select the previously validated immutable release with the administrator
   release tool;
4. restore the preserved legacy scheduler configuration if service continuity
   requires it; and
5. retain TimeLocker run and policy records for diagnosis.

Rollback does not require deleting credentials or state. If automated retention
is disabled during rollback, resume the previously reviewed manual
`restic forget` procedure as the authorized restic account. Do not enable prune
unless it has been separately reviewed.

## References

- [Scheduling Architecture](../../2-architecture/scheduling-system.md)
- [Installation](../user/installation.md)
- [Backup Operations Troubleshooting](../user/backup-operations-troubleshooting.md)
- [Version Management](../../processes/version-management.md)
