---
title: "Architecture Document: System Architecture"
id: "arch-system-architecture"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "18-07-2026"
tags: [architecture, system, layers]
links:
    tooling: []
---

# Architecture Document: System Architecture

## Purpose

Describe TimeLocker's implemented system boundaries and dependency direction.
This document is a current-state architecture contract, not a roadmap.

## Current State

TimeLocker is a Python 3.12+ CLI application that orchestrates Restic. The
installed `timelocker` and `tl` entry points both invoke `TimeLocker.cli:main`.
The supported repository adapters are local filesystem, S3-compatible storage,
and Backblaze B2.

```text
Operator / automation
        |
        v
Typer CLI and modular command groups
        |
        v
Command-facing services and orchestration
        |
        +--------------------+
        |                    |
        v                    v
Configuration /         Backup, snapshot,
credential services     recovery, policy,
                        scheduling, monitoring
        |                    |
        +----------+---------+
                   v
         Repository abstractions
                   |
                   v
          Restic command adapter
                   |
          +--------+--------+
          |        |        |
        Local      S3       B2
```

## Component Boundaries

- **CLI boundary** — `src/TimeLocker/cli.py` owns the installed entry point;
  `src/TimeLocker/cli_modules/commands/` owns modular command groups and input/
  output handling.
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
- **Platform boundary** — scheduling adapters integrate with systemd/cron,
  launchd, and Windows scheduling facilities. Optional system-tray code provides
  notifications; it is not an alternative application interface.

## Invariants

- The CLI is the public application interface.
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

Restic 0.18.0 or later must be available on `PATH`. Configuration locations are
resolved through `ConfigurationPathResolver`; tests and operators should not
hard-code a single home-directory layout. Unattended credential-store access
requires an explicit master-password environment value or protected file.

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
