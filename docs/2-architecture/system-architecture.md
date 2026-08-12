---
title: "Architecture Document: System Architecture"
doc_type: architecture
id: "arch-system-architecture"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "2026-08-12"
tags: [architecture, system, layers]
links:
    tooling: []
---

# Architecture Document: System Architecture

## Purpose

Describe TimeLocker's implemented system boundaries and dependency direction.
This document is a current-state architecture contract, not a roadmap.

## Current State

TimeLocker is a Python 3.12+ CLI application that orchestrates Restic. A normal
source or wheel install exposes `timelocker` and `tl` through
`TimeLocker.cli:main`. A protected system deployment instead places stable
root-owned launchers on the system path; those launchers resolve one validated
immutable release under `/opt/timelocker` before invoking its CLI. The supported
repository adapters are local filesystem, S3-compatible storage, and
Backblaze B2.

```text
user CLI                         user-session tray
    |                                   |
    +--------- user-local work          |
    |                                   |
    +----- protected reads/actions -----+
                       |
                       v
          authenticated local AF_UNIX protocol
                       |
                       v
       socket-activated one-request helper
             |         |          |
             v         v          v
          backup   retention   run/diagnostic
          adapter   adapter       stores
             \         /
              shared repository lock
                       |
                       v
             Restic command adapter
```

## Zero-Idle Protected Runtime

The accepted protected runtime uses:

- existing one-shot scheduler units for scheduled backup and retention;
- bounded, short-lived authenticated helpers for protected queries and manual
  actions;
- atomically written sanitized status state for unprivileged readers; and
- direct filesystem notification in the optional tray, without a privileged
  event broker or heartbeat process.

The enabled AF_UNIX socket is kernel state, not a TimeLocker process. systemd
starts the selected root helper for one connection; the helper authenticates,
serves one bounded request, closes, and exits. Backup and retention workers
publish `/run/timelocker/status.json` atomically after durable run-state
changes. The optional tray registers a filesystem watch before its initial
read and ignores read/open notifications, preventing read-notify-read loops.

## Component Boundaries

- **CLI boundary** — `src/TimeLocker/cli.py` owns the installed entry point;
  `src/TimeLocker/cli_modules/commands/` owns modular command groups and input/
  output handling. User-local commands remain in-process. `runs` and
  `logs view --scope system` use the protected client, as do the bounded
  `system backup` and `system retention` request commands.
- **Release boundary** — root-owned launchers resolve the selected immutable
  release from `/opt/timelocker/selected-release.json`. They do not consult
  pyenv, a source checkout, the caller's home, or current working directory.
- **System-control boundary** — `src/TimeLocker/system_control/` owns the
  versioned local protocol, peer identity, current group authorization,
  allowlisted dispatch, protected adapters, repository locking, durable run
  records, safe diagnostics, deployment assets, and release activation. Its
  one-request socket activation and sanitized status publication.
- **Tray boundary** — `timelocker-tray` is an independent unprivileged
  user-session process. It observes sanitized state directly and invokes a
  short-lived protected helper only for explicit actions. CLI startup never
  initializes it.
- **Application boundary** — managers, orchestrators, and focused services
  coordinate repositories, backups, snapshots, recovery, policies, schedules,
  validation, and monitoring. CLI modules should delegate domain work here.
- **Configuration and security boundary** — `src/TimeLocker/config/` persists
  application configuration; `src/TimeLocker/security/` and credential-facing
  services protect repository secrets and audit access.
- **Repository boundary** — `BackupRepository` and repository services expose
  backend-neutral operations. `src/TimeLocker/restic/Repositories/` supplies
  the supported local, S3, and B2 adapters.
- **Process boundary** — the Restic command definition/builder constructs and
  executes the external `restic` process. Backend environment variables and
  repository passwords are passed at this boundary.
- **Platform boundary** — user schedule adapters integrate with systemd/cron,
  launchd, and Windows scheduling facilities. Protected system-control adapters
  preserve a portable contract, with live acceptance currently established for
  Linux Mint/systemd.

## Invariants

- The CLI is the public application interface.
- No TimeLocker-owned privileged process remains resident while idle.
- Protected reads and actions fail closed if the authenticated backend,
  authorization, selected release, policy approval, or protected target cannot
  be validated.
- System backup and retention share a repository mutation lock and have
  separate durable run records.
- System output is structured and redacted; it does not expose secrets, raw
  backend output, raw journald, or unnecessary protected paths.
- Tray availability is independent of CLI and backend correctness.
- Domain behavior belongs behind command-facing services or orchestration, not
  in presentation-only command code.
- Repository secrets must not be written into ordinary configuration files or
  logs.
- Restore execution must pass an explicit Restic overwrite policy; the default
  is non-destructive.
- Local, S3-compatible, and B2 are the supported storage repository families.
- External process failures must be translated into TimeLocker errors and
  operator-visible diagnostics without exposing secrets.

## Operational Notes

Restic 0.18.0 or later must be available on `PATH`. User configuration
locations are resolved through `ConfigurationPathResolver`. Protected
deployment configuration is root-owned under `/etc/timelocker`; durable system
state is under `/var/lib/timelocker`; the local socket is
`/run/timelocker/control.sock`; sanitized transient status is
`/run/timelocker/status.json`. Unattended credentials are referenced from
protected files and are never copied into user-readable configuration.

## Validation

- `python -m pytest -m "not performance and not stress"`
- `tl --help`
- `tl version --short`
- `python scripts/link_checker.py`

## Change Rules

Update this document when the public interface, application/service ownership,
repository contract, supported backend families, process boundary, or platform
integration changes. Proposed interfaces and backends belong in an approved
active spec, not in this current-state document.

## References

- [Component Breakdown](./component-breakdown.md)
- [Data Flow](./data-flow.md)
- [Service-Layer Integration](../3-implementation/service-layer-integration.md)
- [CLI Command Hierarchy](../reference/timelocker-cli-command-hierarchy.md)
- [System Operations Requirements](../1-requirements/system-operations.md)
- [Scheduling System](./scheduling-system.md)
