---
title: "Backup Operations Troubleshooting Guide"
doc_type: guide
status: active
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Backup Operations Troubleshooting Guide

## Start With The Correct Scope

User-local CLI logs and protected system operation records are different data
sources:

```bash
# Invoking user's CLI log
timelocker logs view

# Protected system backup and retention records
timelocker runs list --limit 20
timelocker logs view --scope system --lines 100
```

Scheduled system backups do not write into another user's local TimeLocker log.
An empty local log therefore does not mean the scheduled backup did not run.

## Access Denied

Only current members of the configured operator group can view system runs,
view structured system diagnostics, or trigger protected actions.

```bash
id
getent group timelocker-operators
```

If an administrator has just added the user, start a new login session so the
desktop and shell obtain the new group membership. Do not solve access denial
by making the control socket world-readable or by copying protected credentials
into a user account.

## Backend Unavailable

Check the socket and service:

```bash
systemctl status timelocker-control.socket
systemctl status timelocker-control.service
ls -l /run/timelocker/control.sock
```

The socket should be owned by root and the operator group with group read/write
access. The public CLI returns a bounded backend-unavailable error; it does not
fall back to a checkout, pyenv shim, root home, or legacy configuration.

## Scheduled Backup Did Not Run

```bash
systemctl status timelocker-npbackup-migration.timer
systemctl status timelocker-npbackup-migration.service
systemctl list-timers 'timelocker-*'
timelocker runs list --operation backup --limit 20
```

Distinguish:

- no run record: the timer or pre-start hook did not reach TimeLocker;
- `queued` or `running`: execution is active or awaiting reconciliation;
- `skipped`: the shared repository lock or another protected conflict blocked
  the run;
- `failed`: inspect the matching structured diagnostics;
- `interrupted`: a prior process ended without a terminal finish hook; the
  coordinator reconciled it on the next start.

## Retention Did Not Run

Retention has three valid triggers:

- after a successful backup;
- the independent retention timer; or
- an authorized explicit request.

Inspect records and the timer:

```bash
timelocker runs list --operation retention --limit 20
systemctl status timelocker-retention.timer
```

If backup succeeded but no backup-success retention record exists, verify that
the backup unit has the installed TimeLocker finish hook. If independent
retention did not run, verify the timer is enabled and the root-owned enable
marker exists. If the result is skipped, check for overlapping backup or
retention activity.

Production retention also fails closed when the policy fingerprint no longer
matches the protected target. Reapprove the exact changed policy; do not edit
the fingerprint to silence the check.

## Repository Password Or Credentials Requested

Protected scheduled operations obtain repository and backend credentials from
root-readable configured references. Operators should not read or copy their
contents. If a protected run prompts for a password, the service is not using
the expected credential reference or permissions.

Inspect metadata only:

```bash
sudo stat /etc/timelocker/production-target.json
sudo systemctl cat timelocker-control.service
```

Do not paste secrets into command history, logs, issue reports, or ordinary
TimeLocker configuration.

## Repository Lock Conflict

Backup and retention serialize mutations through the same lock. A concurrent
request is recorded as skipped. Wait for the active run to finish and retry:

```bash
timelocker runs list --state running
```

Do not run `restic unlock` or delete TimeLocker lock files until you have proved
that no backup or retention process is running and have an administrator's
approval.

## Tray Problems

```bash
timelocker-tray status --once
```

- `Access denied`: refresh login group membership.
- `System backend unavailable`: inspect the control socket/service.
- No icon: confirm the desktop has AppIndicator support and the autostart entry
  exists.
- Stale status: restart only the user tray process; this does not stop backend
  operations.

The CLI must not emit tray warnings. If `timelocker --help`, `logs`, or another
normal CLI command initializes a tray toolkit, report it as a regression.

## Safe Evidence Collection

Collect:

```bash
timelocker version --short
timelocker runs list --json --limit 20
timelocker logs view --scope system --lines 100
systemctl list-timers 'timelocker-*'
```

Share only structured safe summaries. Do not attach raw environment files,
repository configuration, passwords, cloud keys, raw journald output, or
protected path contents.

## Rollback

For a faulty selected release or schedule:

1. disable the affected timer;
2. retain run records and diagnostics;
3. use the root-only release selector to return to the previous validated
   release;
4. restore the preserved legacy scheduler if required; and
5. resume the reviewed manual retention procedure if automated retention is
   disabled.

Rollback should preserve `/var/lib/timelocker` run and policy state.

## References

- [Installation](./installation.md)
- [Scheduling Guide](../developer/scheduling-guide.md)
- [Independent System Tray Setup](../../SYSTEM-TRAY-SETUP.md)
- [System Operations Requirements](../../1-requirements/system-operations.md)
