---
title: "Reference: TimeLocker CLI Command Hierarchy"
doc_type: reference
id: "ref-cli-hierarchy"
type: [ reference ]
status: [ approved ]
owner: "CLI Team"
last_reviewed: "2026-07-26"
tags: [reference, cli, command-structure]
links:
  tooling: []
---

# Reference: TimeLocker CLI Command Hierarchy

## Entry Points

`timelocker` and `tl` are equivalent root commands. A user/source installation
invokes the packaged Typer CLI. A protected system deployment installs stable
root-owned launchers at `/usr/local/bin/timelocker` and `/usr/local/bin/tl`;
both resolve the same selected immutable release.

## Root Command Groups

```text
timelocker (alias: tl)
├── version
├── help
├── completion
├── backup
├── snapshots
├── repos
├── config
├── credentials
├── security
├── migrate
├── policy
├── selections
├── schedule
├── monitor
├── logs
├── reports
├── runs
├── system
└── restore
```

Run `timelocker GROUP --help` for the current leaf commands and options.

## Protected System Reads

```text
timelocker runs list
  [--limit N]
  [--operation backup|retention]
  [--state STATE]
  [--json]

timelocker runs show RUN_ID [--json]

timelocker logs view
  [--scope local|system]
  [--lines N]
  [--level LEVEL]
  [--component COMPONENT]
  [--since TIME]
```

`runs` and `logs view --scope system` use the authenticated local backend and
require current operator-group membership. System diagnostics are structured
safe records, not raw journald. `--follow` is available for local logs but is
rejected for system diagnostics.

Without `--scope system`, `logs view` reads only the invoking user's local CLI
log. Scheduled system backups and retention runs are intentionally absent from
that file.

## Protected System Actions

```text
timelocker system backup [--target TARGET]

timelocker system retention
  --policy-fingerprint FINGERPRINT
  [--dry-run]
```

These commands keep the caller process unprivileged and send only the bounded
request to the protected backend. The backend derives the caller identity from
the local transport and rechecks current operator-group membership. Denial or
backend unavailability never falls back to direct elevated execution.

## Independent Tray Command

`timelocker-tray` is a separate executable, not a CLI command group:

```text
timelocker-tray
  status
  serve
  backup_now
  retention_now
  open_ui
  quit
```

`open_ui` is currently a reserved no-op. `retention_now` requires the exact
approved policy fingerprint and is hidden from the graphical menu when the
tray was not configured with one. The tray communicates with the protected
backend and does not own backup execution.

## Administrator Deployment Tool

`timelocker-deploy` is the supported root administration surface and is
installed at `/usr/local/sbin/timelocker-deploy`:

```text
timelocker-deploy install WHEEL --operator-user ACCOUNT
timelocker-deploy upgrade WHEEL --operator-user ACCOUNT
timelocker-deploy status
timelocker-deploy rollback
```

Every operation returns one JSON object. Mutating operations require root;
status does not start a TimeLocker service process. The command derives the
wheel digest, release identity, and manifest rather than accepting manually
assembled identity inputs.

`timelocker-release-select` is a root-only deployment tool. It is deliberately
not the supported operator workflow; it remains a restricted internal
primitive used by the transactional entrypoint.

## Routing Rules

- User-local commands operate in the invoking user's configuration boundary.
- Protected reads and allowlisted actions cross the local backend.
- Installation, upgrade, rollback, operator membership, policy approval, and
  service changes are administrator maintenance.
- Unknown public actions and unsupported system log scopes fail closed.
- The CLI does not initialize the tray or prompt through a GUI.

## References

- [System Operations Requirements](../1-requirements/system-operations.md)
- [System Architecture](../2-architecture/system-architecture.md)
- [Installation](../guides/user/installation.md)
- [Independent System Tray Setup](../SYSTEM-TRAY-SETUP.md)
