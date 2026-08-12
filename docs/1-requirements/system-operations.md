---
title: "System Operations Requirements"
doc_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# System Operations Requirements

## Scope

These are the accepted current requirements for protected host-level TimeLocker
backup, retention, status, diagnostics, and tray operations.

## Command And Release Requirements

- `timelocker` and `tl` must be stable commands on the system path.
- Protected deployments must execute a root-owned selected immutable release,
  independent of the caller's shell, pyenv selection, checkout, home directory,
  or current working directory.
- Missing, incompatible, or untrusted release metadata must fail closed.
- Activation and rollback must verify compatible CLI, backend, and tray
  entrypoints before changing the selected release.

## Authorization Requirements

- Protected reads and actions must use a local authenticated, least-privilege
  boundary. That boundary must be activated for a bounded request or operation
  and must exit when its work is complete; authorization does not justify a
  continuously resident TimeLocker daemon.
- Only current members of the configured operator group may read system run
  records, read structured system diagnostics, or trigger the allowlisted
  backup and retention actions.
- Authorization must be evaluated from the operating system's current identity
  and group database for each request.
- Administrator maintenance, including installation, operator-group changes,
  policy approval, service changes, activation, and rollback, remains root-only.
- Denial and unavailability must not fall back to direct privileged execution.

## Resource Residency Requirements

- TimeLocker must consume no CPU and retain no service process while no backup,
  retention, restore, explicit query, or explicit control action is running.
- Scheduled backup and retention must use one-shot scheduler jobs rather than a
  continuously resident TimeLocker scheduler or control daemon.
- Protected queries and manual actions must use short-lived authenticated
  helpers or one-shot service activation.
- A sanitized status snapshot may be written atomically for unprivileged
  readers. Reading status must not wake a privileged process repeatedly or
  create a read-notify-read feedback loop.
- The optional user-session tray may remain open only by explicit operator
  choice. It must observe sanitized state directly and must not require a
  resident privileged event broker, heartbeat, or status service.

## Operation Requirements

- System backup and retention must create durable, queryable run records.
- Backup and retention must share a repository mutation lock.
- Retention may run after successful backup, on an independent schedule, or by
  explicit authorized request.
- Backup-success retention must be a separate run started only after successful
  backup completion and lock release.
- Independent retention must not depend on a preceding backup result.
- Interrupted queued or running operations must be reconciled explicitly.
- Retention mutation must require a root-owned enable marker and an exact
  approved policy/target fingerprint. Dry-run remains available without
  snapshot removal.

## Visibility And Privacy Requirements

- Operators must be able to list and inspect structured backup and retention
  runs and safe diagnostics.
- User-local logs must remain distinct from protected system records.
- The protected interface must not disclose repository passwords, cloud
  credentials, environment-file contents, raw backend output, raw journald
  content, or unnecessary protected filesystem paths.
- Root-owned target, repository-configuration, credential-source, and retention
  enable-marker files accepted by the backend must be owner-only.
- Run records must use bounded states, result codes, counters, and safe
  summaries.

## Tray Requirements

- The tray must be an independent user-session process, not part of normal CLI
  initialization or the privileged backend.
- It may show backend availability, current activity, latest backup and
  retention status, and next known schedules.
- It may request only allowlisted actions through the protected backend.
- Tray failure, exit, or restart must not affect backend services or active
  operations.
- Tray operation must not keep a privileged TimeLocker process resident.
- A full desktop UI is not part of the current product surface.

## Platform Requirement

The architecture must preserve portable contracts for Linux and Windows
adapters. Linux Mint live acceptance for the protected installation and
independent tray is in progress under Spec 010. This requirement does not yet
claim an accepted Linux or Windows deployment.

## References

- [System Architecture](../2-architecture/system-architecture.md)
- [Scheduling Architecture](../2-architecture/scheduling-system.md)
- [CLI Command Hierarchy](../reference/timelocker-cli-command-hierarchy.md)
