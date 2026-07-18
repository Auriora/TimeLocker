---
title: "Reference: Repository Orientation and Change Map"
id: "RM-014"
type: [ reference ]
status: [ approved ]
owner: "Codex"
last_reviewed: "18-07-2026"
tags: [reference, cli, architecture, onboarding]
links:
  tooling: [python-agent-ide]
---

# Reference: Repository Orientation and Change Map

Last updated: 2026-07-18

## 1. Purpose

This document gives contributors a practical map of the TimeLocker codebase:

- the live CLI command surface
- the major runtime subsystems
- the best starting files for common kinds of changes

Use this as an onboarding and navigation reference, not as a replacement for implementation or architecture documents.

## 2. Scope and Source of Truth

- CLI wiring source of truth: `src/TimeLocker/cli.py`
- Command-module implementation source of truth: `src/TimeLocker/cli_modules/commands/`
- Package/subsystem source of truth: `src/TimeLocker/`
- Supporting references:
  - `docs/reference/timelocker-cli-command-hierarchy.md`
  - `docs/3-implementation/cli-modules.md`
  - `docs/README.md`

Observed with runtime-backed exploration using the Python Agent IDE plugin plus direct verification of the mounted Typer apps.

## 3. CLI Command Map

The public root command is:

```text
timelocker
tl
```

The live command surface is mounted in `src/TimeLocker/cli.py`. The main top-level groups are:

### 3.1 Backup

- Module: `src/TimeLocker/cli_modules/commands/backup.py`
- Purpose: backup creation and verification
- Key commands:
  - `backup create`
  - `backup verify`

### 3.2 Snapshots

- Module: `src/TimeLocker/cli_modules/commands/snapshots.py`
- Purpose: snapshot browsing and management
- Key commands:
  - `snapshots list`
  - `snapshots show`
  - `snapshots find`
  - `snapshots forget`
  - `snapshots prune`
  - `snapshots diff`

### 3.3 Restore

- Module: `src/TimeLocker/cli_modules/commands/restore.py`
- Purpose: restore and recovery workflows
- Documented command family includes:
  - `restore list`
  - `restore browse`
  - `restore files`
  - `restore full`
  - `restore mount`
  - `restore umount`
  - `restore find`
  - `restore diff`
  - `restore verify`

### 3.4 Repositories

- Module: `src/TimeLocker/cli_modules/commands/repositories.py`
- Purpose: repository configuration, lifecycle, and validation
- Key commands:
  - `repos list`
  - `repos add`
  - `repos show`
  - `repos remove`
  - `repos update`
  - `repos edit`
  - `repos default`
  - `repos lock`
  - `repos mode`
  - `repos init`
  - `repos unlock`
  - `repos migrate`
  - `repos forget`
  - `repos check`
  - `repos stats`
  - `repos prune`
  - `repos validate`
  - `repos validate-all`
- Nested group:
  - `repos credentials`

### 3.5 Selections

- Module: `src/TimeLocker/cli_modules/commands/selections.py`
- Purpose: selection templates, include/exclude rules, and data-set definitions
- Notes:
  - Replaces older `targets`-style workflows in the current docs

### 3.6 Config

- Module: `src/TimeLocker/cli_modules/commands/config.py`
- Purpose: configuration inspection, import, export, and migration support
- Mounted groups:
  - `config`
  - `config import`
  - `config export`
  - root-level `migrate`

### 3.7 Credentials

- Module: `src/TimeLocker/cli_modules/commands/credentials.py`
- Purpose: repository and backend credential management

### 3.8 Security

- Module: `src/TimeLocker/cli_modules/commands/security.py`
- Purpose: access control, security workflows, and privacy operations

### 3.9 Policy

- Module: `src/TimeLocker/cli_modules/commands/policy.py`
- Purpose: policy definition, enforcement, and audit
- Top-level commands include:
  - `policy enforce`
  - `policy simulate`
  - `policy status`
  - `policy audit`
- Nested groups include:
  - `policy backup`
  - `policy retention`
  - `policy assignment`

### 3.10 Schedule

- Module: `src/TimeLocker/cli_modules/commands/schedule.py`
- Purpose: automation and scheduled backup job management
- Key commands:
  - `schedule create`
  - `schedule list`
  - `schedule show`
  - `schedule edit`
  - `schedule delete`
  - `schedule enable`
  - `schedule disable`
  - `schedule generate-scripts`
  - `schedule test`

### 3.11 Monitoring

- Command owner: `src/TimeLocker/cli_modules/commands/monitoring.py`
- Integration bridge:
  `src/TimeLocker/cli_modules/monitoring_integration.py`
- Mounted groups in the current root CLI:
  - `monitor`
  - `logs`
  - `reports`
- `monitor` commands include:
  - `monitor status`
  - `monitor operations`
  - `monitor health`
  - `monitor history`
  - `monitor stats`
- Ownership notes:
  - the root CLI and command registry both mount the same command-owner module
  - `CLIMonitoringIntegration` owns monitoring data access and presentation
    conversion
  - public `CLIServiceManager` monitoring methods are compatibility delegates,
    not a second command owner

### 3.12 Root Commands

- Defined in `src/TimeLocker/cli.py`
- Key commands:
  - `version`
  - `help`
  - `completion`

## 4. Subsystem Map

The codebase is organized as a CLI-first application with a broad service layer and several domain-focused packages.

### 4.1 Command and User-Facing Layer

- `src/TimeLocker/cli.py`
- `src/TimeLocker/cli_modules/commands/`
- `src/TimeLocker/cli_modules/helpers/`
- `src/TimeLocker/cli_modules/services/`
- `src/TimeLocker/cli_modules/validation/`
- `src/TimeLocker/cli_modules/testing/`

This layer handles:

- Typer app mounting
- command parsing and help output
- CLI-specific helpers and formatting
- command-facing validation and testing utilities

### 4.2 Application and Orchestration Layer

- `src/TimeLocker/cli_services.py`
- `src/TimeLocker/services/`
- `src/TimeLocker/integration/`

This layer coordinates:

- service initialization
- dependency wiring
- repository/service orchestration
- integration seams between legacy and newer service-oriented code

Treat much of `integration/` as orchestration glue and migration seams rather than standalone business domains.

### 4.3 Core Domain Subsystems

#### Configuration

- `src/TimeLocker/config/`
- Responsibilities:
  - configuration persistence
  - validation
  - locking
  - migration
  - path resolution
  - audit/performance helpers

#### Restic and Repository Backends

- `src/TimeLocker/restic/`
- `src/TimeLocker/restic/Repositories/`
- Responsibilities:
  - Restic command execution
  - repository URI/backend support
  - local, S3, and B2 repository implementations

#### Security and Credentials

- `src/TimeLocker/security/`
- Responsibilities:
  - credential management
  - privacy and security services
  - repository protection and access control

#### Monitoring and Telemetry

- `src/TimeLocker/monitoring/`
- Responsibilities:
  - telemetry
  - notifications
  - status and health reporting
  - progress monitoring
  - history and troubleshooting

#### Scheduling and Automation

- `src/TimeLocker/scheduling/`
- Responsibilities:
  - schedule models and validation
  - automation engine
  - platform-specific adapters
  - script generation
  - scheduler integration

#### Policy Management

- `src/TimeLocker/policy/`
- Responsibilities:
  - policy models
  - validation
  - engine and enforcement
  - storage and simulation

#### Backup, Snapshot, Recovery, and Selection Flows

These are split across package-root modules rather than confined to one subpackage.

- Backup and snapshot modules:
  - `backup_manager.py`
  - `backup_repository.py`
  - `backup_snapshot.py`
  - `snapshot_manager.py`
  - `snapshot_browser.py`
- Recovery and restore modules:
  - `restore_manager.py`
  - `recovery_orchestrator.py`
  - `recovery_validator.py`
  - related recovery handlers/state modules
- Selection modules:
  - `selection_manager.py`
  - `selection_template_manager.py`
  - `pattern_engine.py`
  - `precedence_resolver.py`
  - related preview, validation, and optimization modules

### 4.4 Shared Contracts and Infrastructure

- `src/TimeLocker/interfaces/`
- `src/TimeLocker/command_builder/`
- `src/TimeLocker/adapters/`
- `src/TimeLocker/importers/`
- `src/TimeLocker/performance/`
- `src/TimeLocker/utils/`

These areas provide:

- shared protocols and models
- command construction
- tool adapters
- importer/migration support
- performance helpers
- reusable utilities

## 5. Change Map

This section answers a practical question: where should a contributor start when changing a specific area?

### 5.1 Backup Creation and Execution

Start here:

- `src/TimeLocker/cli_modules/commands/backup.py`
- `src/TimeLocker/cli_modules/helpers/backup_cli_handler.py`
- `src/TimeLocker/cli_services.py`
- `src/TimeLocker/services/backup_orchestrator.py`
- `src/TimeLocker/services/repository_service.py`

Also inspect selection-related modules when the change involves include/exclude rules, reusable templates, or template-driven backup execution.

### 5.2 Repository Management

Start here:

- `src/TimeLocker/cli_modules/commands/repositories.py`
- `src/TimeLocker/cli_modules/services/repository_resolver.py`
- `src/TimeLocker/services/repository_manager.py`
- `src/TimeLocker/services/repository_factory.py`
- `src/TimeLocker/config/configuration_manager.py`
- `src/TimeLocker/restic/`

Use this area for:

- add/remove/update repository commands
- repository initialization and validation
- backend selection and repository factory changes
- named repository behavior and defaults

### 5.3 Restore and Snapshot Behavior

Start here:

- `src/TimeLocker/cli_modules/commands/restore.py`
- `src/TimeLocker/cli_modules/commands/snapshots.py`
- `src/TimeLocker/restore_manager.py`
- `src/TimeLocker/recovery_orchestrator.py`
- `src/TimeLocker/snapshot_manager.py`
- `src/TimeLocker/snapshot_browser.py`

### 5.4 Configuration Behavior

Start here:

- `src/TimeLocker/cli_modules/commands/config.py`
- `src/TimeLocker/config/configuration_module.py`
- `src/TimeLocker/config/configuration_manager.py`

Then narrow into the relevant specialized file under `config/` for locking, migration, validation, auditing, or storage changes.

### 5.5 Credentials and Security

Start here:

- `src/TimeLocker/cli_modules/commands/credentials.py`
- `src/TimeLocker/cli_modules/commands/security.py`
- `src/TimeLocker/security/credential_manager.py`
- `src/TimeLocker/security/security_service.py`

Also inspect repository/backend-specific credential resolution in `services/` and `restic/Repositories/` when the behavior depends on repository type.

### 5.6 Scheduling and Automation

Start here:

- `src/TimeLocker/cli_modules/commands/schedule.py`
- `src/TimeLocker/scheduling/schedule_manager.py`
- `src/TimeLocker/scheduling/schedule_validator.py`

Then inspect the relevant platform adapter:

- `cron_adapter.py`
- `systemd_adapter.py`
- `launchd_adapter.py`
- `windows_adapter.py`

### 5.7 Monitoring and Telemetry

Start here:

- `src/TimeLocker/cli_modules/commands/monitoring.py`
- `src/TimeLocker/cli_modules/monitoring_integration.py`
- `src/TimeLocker/cli_services.py` for retained compatibility delegates
- `src/TimeLocker/monitoring/monitoring_service.py`
- `src/TimeLocker/monitoring/status_reporter.py`
- `src/TimeLocker/monitoring/telemetry.py`
- `src/TimeLocker/monitoring/notification_service.py`
- `src/TimeLocker/monitoring/progress_monitor.py`

### 5.8 Selection Templates and Pattern Logic

Start here:

- `src/TimeLocker/cli_modules/commands/selections.py`
- `src/TimeLocker/cli_modules/commands/backup.py` for selection-driven backup
  command routing
- `src/TimeLocker/cli_modules/helpers/backup_cli_handler.py` for focused
  selection-backup orchestration
- `src/TimeLocker/selection_manager.py`
- `src/TimeLocker/selection_template_manager.py`
- `src/TimeLocker/pattern_engine.py`
- `src/TimeLocker/precedence_resolver.py`

### 5.9 Policy Behavior

Start here:

- `src/TimeLocker/cli_modules/commands/policy.py`
- `src/TimeLocker/policy/engine.py`
- `src/TimeLocker/policy/manager.py`
- `src/TimeLocker/policy/validator.py`

### 5.10 Cross-Cutting CLI or Service-Layer Changes

Start here:

- `src/TimeLocker/cli.py`
- `src/TimeLocker/cli_services.py`
- `src/TimeLocker/integration/service_manager.py`
- `src/TimeLocker/cli_modules/registry_integration.py`
- `src/TimeLocker/cli_modules/commands/base.py`
- `src/TimeLocker/cli_modules/services/repository_resolver.py`
- `src/TimeLocker/cli_modules/monitoring_integration.py`

Use this route when:

- a change affects multiple command groups
- service initialization or dependency flow changes
- help output, command registration, or plugin/registry behavior changes
- behavior appears duplicated between the root CLI and command modules

Preserve `CLIServiceManager` and `get_cli_service_manager()` as public
compatibility seams. Prefer focused command services and integrations for new
work; compatibility methods should remain thin delegates.

## 6. Navigation Notes

- If you need the public CLI tree first, read `docs/reference/timelocker-cli-command-hierarchy.md`.
- If you need command-layer implementation details, read `docs/3-implementation/cli-modules.md`.
- If you need architecture context before editing, start in `docs/README.md` and `docs/2-architecture/`.
- If you are unsure whether a module is core behavior or glue code, inspect whether it lives in a domain package (`config`, `restic`, `security`,
  `monitoring`, `scheduling`, `policy`) or in orchestration-heavy packages (`integration`, `cli_services`, `cli_modules` helpers/registry layers).

# References

- `src/TimeLocker/cli.py`
- `src/TimeLocker/cli_modules/commands/`
- `src/TimeLocker/cli_services.py`
- `src/TimeLocker/services/`
- `src/TimeLocker/integration/`
- `docs/reference/timelocker-cli-command-hierarchy.md`
- `docs/3-implementation/cli-modules.md`
