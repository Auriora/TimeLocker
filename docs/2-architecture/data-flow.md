---
title: "Architecture Document: Data Flow"
id: "arch-data-flow"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "18-07-2026"
tags: [architecture, flow, processes]
links:
    tooling: []
---

# Architecture Document: Data Flow

## Purpose

Describe the implemented control and data paths used to create backups, inspect
snapshots, restore data, and resolve protected credentials.

## Common Control Flow

```text
CLI input
  -> command validation and repository resolution
  -> application service / orchestrator
  -> repository abstraction
  -> Restic command builder and process
  -> local, S3-compatible, or B2 repository
  -> parsed result, audit/monitoring events, CLI output
```

Commands resolve configuration and credentials before invoking the repository.
Services own domain coordination; the Restic adapter owns external command
construction and execution.

## Backup Flow

1. The CLI receives source paths, a selection/target, and repository identity.
2. Configuration and repository services resolve the repository adapter and
   required backend credentials.
3. Selection services expand and validate included/excluded paths.
4. Backup orchestration invokes the repository with targets and tags.
5. The Restic adapter constructs the backup command and process environment.
6. Restic reads source data and writes encrypted, deduplicated repository data.
7. Status and summary events flow back through monitoring/progress services to
   the CLI; audit-capable services append operation evidence.

## Snapshot And Retention Flow

1. A command resolves the repository and requests snapshots or statistics.
2. The adapter executes the relevant Restic command and parses its JSON output.
3. Snapshot models are returned through snapshot/application services.
4. Retention actions translate an accepted policy into explicit forget/prune
   parameters before Restic mutates repository data.

## Restore Flow

1. The CLI resolves repository, snapshot ID, destination, and operator options.
2. Recovery orchestration validates inputs and converts them to restore options.
3. `RestoreManager` verifies the snapshot/destination and selects `never` as the
   overwrite policy unless the operator explicitly authorized overwrite.
4. `BackupSnapshot` passes that policy through `BackupRepository.restore`.
5. The Restic adapter always emits `--overwrite never` or `--overwrite always`.
6. Restic reads repository data and writes permitted files to the destination.
7. Verification, progress, warnings, and errors flow back to the operation state
   and CLI.

## Credential Flow

1. Interactive users unlock the encrypted credential store with a master
   password. Automation supplies `TIMELOCKER_MASTER_PASSWORD` or a protected
   file named by `TIMELOCKER_MASTER_PASSWORD_FILE`.
2. The credential manager derives an encryption key from that explicit secret
   and the store salt, then decrypts repository/backend credentials in memory.
3. Repository services select stored credentials or backend-specific environment
   values according to their documented resolution order.
4. The adapter places required values in the child Restic process environment.
5. Secret values are not persisted in ordinary configuration or emitted to
   logs. Credential access and changes produce audit events.

## Scheduling Flow

1. Schedule commands validate and persist schedule definitions.
2. Scheduling services select the platform adapter and generate the executable
   invocation.
3. The platform scheduler starts the CLI later with configuration and explicit
   secret injection supplied by the operator's service environment.
4. The scheduled operation then follows the same backup or maintenance flow as
   an interactive CLI invocation.

## Failure Flow

Input/configuration failures stop before process execution. Restic process
failures are translated into TimeLocker errors and operation state. Monitoring,
audit, and CLI layers receive safe diagnostics; secrets must not be included.
Recovery verification failures do not retroactively report success.

## Validation

- Focused command, service, repository, restore, and credential tests.
- Full configured suite: `python -m pytest -m "not performance and not stress"`.
- Internal links: `python scripts/link_checker.py`.

## Change Rules

Update this document when data ownership, execution order, credential routing,
restore conflict semantics, or process/result propagation changes. Keep
operation-specific proposed flows in an active spec until implemented.

## References

- [System Architecture](./system-architecture.md)
- [Component Breakdown](./component-breakdown.md)
- [Per-Repository Credentials](../guides/user/per-repo-credentials.md)
