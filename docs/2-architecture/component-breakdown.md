---
title: "Architecture Document: Component Breakdown"
id: "arch-component-breakdown"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "18-07-2026"
tags: [architecture, components]
links:
    tooling: []
---

# Architecture Document: Component Breakdown

## Purpose

Map implemented TimeLocker components to their current responsibilities and
source locations. Code and tests remain authoritative for low-level behavior.

## Public Interface

### CLI

- **Location:** `src/TimeLocker/cli.py`, `src/TimeLocker/cli_modules/`
- **Responsibilities:** command registration, argument validation, interactive
  prompts, progress/output formatting, and delegation to services.
- **Contract:** both `timelocker` and `tl` invoke the same `TimeLocker` package
  and command tree.

### Optional System-Tray Notifications

- **Location:** `src/TimeLocker/monitoring/system_tray_integration.py`
- **Responsibilities:** desktop status and notification integration where the
  platform dependency is installed.
- **Boundary:** this is an optional notification surface, not a second control
  plane.

## Application And Domain Components

### Repository Management

- **Location:** `src/TimeLocker/services/repository_*.py`,
  `src/TimeLocker/backup_repository.py`
- **Responsibilities:** resolve named repositories and URIs, validate
  configuration, construct adapters, manage credentials, and expose lifecycle
  operations.

### Backup And Snapshot Operations

- **Location:** `backup_manager.py`, `snapshot_manager.py`,
  `services/backup_orchestrator.py`, `services/snapshot_service.py`
- **Responsibilities:** resolve selections, invoke repository backup actions,
  enumerate snapshots, apply retention, and report results.

### Recovery Operations

- **Location:** `recovery_orchestrator.py`, `restore_manager.py`,
  `recovery_*.py`
- **Responsibilities:** validate recovery inputs, track operation state, invoke
  snapshot restore, verify results, and report failures. Conflict policy is
  carried to the repository adapter as an explicit overwrite mode.

### Selection And Policy

- **Location:** `selection_*.py`, `file_selections.py`, `pattern_engine.py`,
  `policy/`
- **Responsibilities:** reusable path selection, include/exclude evaluation,
  policy persistence, validation, simulation, and retention decisions.

### Scheduling

- **Location:** `scheduling/`
- **Responsibilities:** schedule models, validation, persistence, audit, script
  generation, credential readiness, and platform-specific scheduler adapters.

### Monitoring And Reporting

- **Location:** `monitoring/`, `cli_modules/monitoring_integration.py`
- **Responsibilities:** activity/history recording, integrity and storage
  checks, progress, notifications, telemetry, status, and troubleshooting data.

## Infrastructure Components

### Configuration

- **Location:** `config/`
- **Responsibilities:** path resolution, schema/defaults, filesystem storage,
  validation, migration, locking, transactions, backup/restore, and audit.

### Credentials And Security

- **Location:** `security/`, `services/repository_credential_manager.py`
- **Responsibilities:** encrypted credential storage, explicit unlock,
  repository/backend credential resolution, access logging, and protection
  utilities. Non-interactive unlock accepts only operator-supplied secrets.

### Restic Integration

- **Location:** `restic/`, `command_builder/`
- **Responsibilities:** define Restic commands and parameters, construct process
  calls, supply repository environments, parse results, and expose local/S3/B2
  repository adapters.

### Plugin Services

- **Location:** `services/plugin_*.py`, `services/plugins/`
- **Responsibilities:** register and select backup-engine wrappers behind
  service interfaces. Plugin presence does not by itself make an additional
  storage family part of the supported product surface.

### Error And Integration Services

- **Location:** `integration/`, `utils/error_handling.py`, domain-specific
  `*_error*.py` modules
- **Responsibilities:** dependency wiring, event propagation, health checks,
  error translation, diagnostics, and service coordination.

## Supported Repository Adapters

| Adapter | Location | Current role |
|---------|----------|--------------|
| Local | `restic/Repositories/local.py` | Restic repository on a local filesystem path. |
| S3 | `restic/Repositories/s3.py` | AWS S3 or S3-compatible Restic repository. |
| B2 | `restic/Repositories/b2.py` | Backblaze B2 Restic repository. |

## Change Rules

Update this map when component ownership or supported adapters change. Link
accepted requirements from their durable requirements document; do not copy
legacy or unverified requirement identifiers into this architecture map.

## References

- [System Architecture](./system-architecture.md)
- [Data Flow](./data-flow.md)
- [Repository Orientation And Change Map](../reference/repo-orientation-and-change-map.md)
