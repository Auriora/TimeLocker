---
title: Daemonless protected system deployment design
doc_type: spec
artifact_type: design
status: approved
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Technical Design

## Overview

Spec 011 replaces the resident root backend with a systemd socket-activated,
single-request helper. The socket remains a kernel-owned authorization entry
point; each TimeLocker process accepts one connection, derives peer identity,
serves one allowlisted request, atomically publishes a sanitized status
snapshot when appropriate, and exits. Scheduled backup and retention remain
one-shot units.

The privileged status-event socket, heartbeat broker, resident filesystem
observer, and resident schedule monitor are removed from the installed asset
set. The optional user tray reads a group-authorized sanitized snapshot and
watches that file directly. Explicit tray actions still use the protected
single-request socket.

The supported administrator entrypoint is `timelocker-deploy`. It owns local
wheel validation, trusted staging, manifest derivation, transactional install,
status, and rollback. It reuses the immutable-release resolver and deployment
primitives proven by Spec 010, while replacing acceptance-only inputs and
resident-service health gates.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC5 | `timelocker-deploy` install, upgrade, status, rollback command | CLI and installed-artifact tests |
| Requirement 2 | AC1-AC5 | Wheel metadata/digest validation and derived manifests | Tamper and mismatch tests |
| Requirement 3 | AC1-AC6 | Root-owned staging snapshot and bounded cleanup | Symlink, mode, ownership, and source-swap tests |
| Requirement 4 | AC1-AC5 | Preflight transaction and expected-current selection | Failure-injection transaction tests |
| Requirement 5 | AC1-AC5 | Probed rollback with state preservation | Rollback and preservation tests |
| Requirement 6 | AC1-AC5 | Deployment lock, idempotency, attention record | Concurrency and interruption tests |
| Requirement 7 | AC1-AC5 | Typed redacted results and root-owned evidence | Schema, permission, and redaction tests |
| Requirement 8 | AC1-AC5 | Platform-neutral engine with Linux adapter | Interface and unsupported-platform tests |
| Requirement 9 | AC1-AC7 | Single-request helper and direct snapshot watcher | Process-exit, asset, tray, and 90-second live checks |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Validation and preflight precede the mutation boundary | Failure injection at every preflight gate | No host writes before boundary |
| CP-002 | Selector uses locked expected-current compare-and-swap | Competing selector tests | Existing resolver retained |
| CP-003 | Post-boundary failure restores state or writes attention | Forced failure and signal tests | Mutation remains fail closed |
| CP-004 | Staged digest is rechecked before installation | Mutable-source and digest tests | Source is never reread |
| CP-005 | Deployment dispatcher has no backup/retention execution route | Action-spy tests | Timer state may be inspected only |
| CP-006 | Evidence schema admits only allowlisted non-secret fields | Redaction and exact-schema tests | No raw environment or subprocess output |
| CP-007 | Systemd and filesystem operations live behind Linux adapters | Interface and fake-adapter tests | Windows remains contractual |
| CP-008 | Helper serves one request and exits; no event service is installed | Unit, package, and live process checks | Socket unit is not a process |

## High-Level Design

### System Architecture

```text
CLI or tray action -> systemd control socket -> one root helper -> response -> exit
                                                   |
scheduled one-shot worker --------------------------+
                                                   v
                                    atomic sanitized status snapshot
                                                   |
optional user tray -> initial read + filesystem watch (no privileged event service)

administrator -> timelocker-deploy -> trusted staging -> preflight -> atomic activation
```

### Components and Changes

- `backend_entry.py` and `linux_adapter.py`: add single-request serving and
  remove resident monitors from the production path.
- `status_snapshot.py`: own exact atomic sanitized snapshot persistence and
  authorized reads.
- `tray_client.py` and `tray_entry.py`: replace privileged event subscription
  with direct snapshot-file observation; retain socket use for explicit actions.
- packaged systemd assets: remove the status-event socket and make the control
  service exit after one request.
- `deployment.py` and new deployment entrypoint: derive trusted release inputs,
  stage privately, transact, report status, and roll back.
- deployment and artifact tests: require the daemonless asset set and reject
  resident event/service dependencies.

### Data Models

`SanitizedStatusFile` uses the existing strict `StatusSnapshot` wire model plus
an outer file schema version. It contains no repository URI, credential,
environment, journal, command, or arbitrary path fields. Writes use a temporary
file in the destination directory, `fsync`, mode `0640`, and atomic replace.

`DeploymentResult` contains operation, stable result code, selected/previous
release IDs, mutation-started and recovery fields, and evidence location.
`DeploymentEvidence` contains only validated digest, package/release identity,
stage outcomes, timestamps, and rollback disposition.

### Data Flow

1. A client connects to `/run/timelocker/control.sock`.
2. systemd launches the selected helper only if no instance is active.
3. The helper accepts one bounded frame and derives the kernel peer identity.
4. The dispatcher rechecks group membership and executes one allowlisted action.
5. Status-producing paths atomically refresh the sanitized snapshot.
6. The helper sends one bounded response and exits.
7. The tray reads the current snapshot and receives direct filesystem changes.

## Low-Level Design

### Algorithms and Logic

```text
serve_one_request:
    adopt systemd control socket
    accept one connection
    derive peer identity and dispatch one bounded request
    send one bounded response
    close listener and exit

deploy_local_wheel:
    require root and acquire deployment lock
    validate source filename, metadata, assets, and digest
    copy once into private root-owned staging; revalidate digest
    derive release and asset manifests
    run candidate and authorization preflights
    mark mutation boundary
    install assets and compare-and-swap selector
    verify one-shot helper, timers, and installed entrypoints
    write redacted evidence and result
    on failure after boundary, restore and verify or write attention
```

### Function Signatures and Interfaces

```text
LinuxUnixSocketTransport.serve_once(handler) -> None
AtomicStatusSnapshotStore.read() -> StatusSnapshot
AtomicStatusSnapshotStore.write(snapshot) -> None
StatusSnapshotWatcher.events(stop_event) -> Iterator[StatusSnapshot]
DeploymentEntrypoint.install(artifact) -> DeploymentResult
DeploymentEntrypoint.upgrade(artifact) -> DeploymentResult
DeploymentEntrypoint.status() -> DeploymentResult
DeploymentEntrypoint.rollback() -> DeploymentResult
```

### Error Handling

Malformed requests, identity failures, unavailable snapshots, and invalid
deployment inputs use stable bounded errors. No error includes raw paths beyond
documented evidence locations, environment values, repository identifiers, or
subprocess output. Pre-boundary deployment errors mutate nothing. Post-boundary
errors recover or create an attention record that blocks later mutation.

### Security, Trust, and Access

Kernel peer credentials and current operator-group membership remain the
authorization source. The sanitized snapshot directory is root-owned and
operator-group readable, never writable by the tray. Deployment requires root,
rejects symlinks/untrusted writable inputs, snapshots mutable input once, and
does not read caller configuration or credentials. No shell command strings are
constructed from untrusted values.

### Migration and Compatibility

Upgrade installs the new service and control socket, stops and disables the
legacy status-event socket, and removes its socket path. Existing protected
configuration, run records, timers, selected/previous releases, and public
status semantics are retained. Old releases remain rollback candidates only if
their activation does not re-enable a rejected resident backend; otherwise the
entrypoint fails with an explicit incompatible-rollback result.

### Slice Boundary And Residual Architecture

| Design target | In this slice | Out of this slice | Follow-up destination | Blocks closure? |
|---------------|---------------|-------------------|-----------------------|-----------------|
| Daemonless Linux protected runtime | Single-request socket helper, snapshot, tray watch, assets | none | none | yes |
| Supported local-wheel deployment | install, upgrade, status, rollback | network release acquisition | future spec if requested | no |
| Windows portability | interfaces and fail-closed unsupported result | live Windows implementation/acceptance | future Windows spec | no |
| Release publication | deployment consumes a local artifact | PyPI/GitHub publication | existing release process | no |

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Focused system-control and deployment tests | Requirements 1-9, CP-001-CP-008 | tasks and `verification.md` | systemd integration remains host-specific |
| Package asset and installed-wheel smoke | Entrypoints and daemonless asset set | `verification.md` | distro packaging differences |
| TimeLocker MoE review | architecture, backup safety, security, tests, operations, docs | T review task | bounded review limitations |
| Linux live acceptance with 90-second idle observation | Requirement 9 and operational migration | protected evidence | requires separate host-mutation approval |

## Downstream Task Guidance

- Implement daemonless runtime and tests before deployment consolidation.
- Cover every CP property in task and traceability artifacts.
- Create change impact, tasks, traceability, and verification before code edits.
- Repeat expert review after implementation and before promotion.

## Operational Considerations

The kernel may retain an enabled socket while no TimeLocker process exists.
That is compliant zero process/CPU residency. The optional tray is an explicitly
chosen user process, not privileged, and must tolerate a missing or stale
snapshot. Migration must stop the existing daemon and event socket without
triggering backup or retention.

## Open Questions

None blocking. The approved initial artifact source is a local wheel; remote
release acquisition is explicitly outside this implementation slice.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Canonical context: [canonical-context.md](./canonical-context.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
