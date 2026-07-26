---
title: System CLI, independent tray, retention, and local control design
doc_type: spec
artifact_type: design
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Technical Design

## Overview

TimeLocker will separate the public CLI, privileged machine operations, desktop
tray, and Restic execution into explicit process boundaries. A root-owned
system backend will expose a small versioned local contract. On Linux, a
systemd-activated Unix-domain socket will authenticate callers from kernel peer
credentials and revalidate membership in the root-controlled
`timelocker-operators` group for every protected request. Windows support will
use the same protocol and domain services behind a named-pipe/service adapter.

The backend will expose structured run and diagnostic records rather than
granting users direct access to journald, root configuration, repository
credentials, or raw Restic output. The CLI and independent tray will be clients
of this contract. Ordinary user-local commands and logs will remain
unprivileged and separate.

The Linux reference deployment remains Linux Mint Cinnamon/X11. The initial
delivery will include a Linux implementation and contract-tested Windows
adapter seam; it will not claim live Windows acceptance until that adapter is
implemented and validated.

## Decisions

### D001: Dedicated operator group

The default system operator group is `timelocker-operators`. It is distinct from
the `restic` service account and any broad `systemd-journal` or administrator
group. Installation creates the group but does not add users automatically.
Membership changes remain an explicit system-administrator action.

### D002: Structured records, not raw journal delegation

TimeLocker will persist allowlisted `RunRecord` and `DiagnosticRecord` objects
under `/var/lib/timelocker`. Authorized clients may query those records through
the backend. Membership in `timelocker-operators` does not grant direct access
to journald, `/etc/timelocker`, `/var/restic`, environment files, or raw Restic
output.

### D003: Kernel identity plus current group revalidation

Linux socket permissions provide a first gate, but the backend also obtains the
peer UID through `SO_PEERCRED`, resolves the account through the operating
system, and checks current NSS group membership on every protected request. A
username, UID, group list, or authorization flag supplied in a request is
ignored. This second check rejects a process whose inherited supplementary
groups became stale after the account was removed from the operator group.

### D004: Backend-mediated machine actions

The system launcher does not elevate the entire CLI process. User-scope
commands run locally. Allowlisted machine operations are sent to the privileged
backend, which authenticates current operating-system identity and group
membership, validates, locks, audits, and executes them. Installation, upgrade,
rollback, group management, and service-file changes remain explicit
administrator operations through the platform's normal system authorization
mechanism.

### D005: Explicit local and system log scopes

`timelocker logs view` remains backward-compatible and reads user-local
application logs by default. `timelocker logs view --scope system` queries
authorized structured diagnostic records. Backup and retention outcomes use
`timelocker runs list` and `timelocker runs show RUN_ID`; they are not inferred
from free-form log text.

### D006: Independent tray client

`NotificationService`, CLI services, schedulers, retention workers, and the
backend will not import or construct platform tray implementations. A separate
`timelocker-tray` entry point runs in the graphical user session, reads status
through the local contract, and requests only allowlisted actions. Platform UI
modules are loaded only by that entry point.

### D007: Retention trigger independence

Retention is a separate locked operation. The production profile emits one
retention request after a successful scheduled backup has recorded terminal
success and released its repository lock. Manual and independent scheduled
retention remain supported. The initial production profile leaves the
independent catch-up schedule disabled until an operator explicitly enables a
reviewed schedule.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC4 | Root-owned launchers, immutable release selector, fail-closed resolution | Launcher unit and live smoke tests |
| Requirement 2 | AC1-AC6 | Action classifier, backend-mediated machine actions, platform authorization adapter | Privilege-routing and denial tests |
| Requirement 3 | AC1-AC8 | Independent tray entry point, platform adapters, no tray imports in headless paths | Import-boundary, headless, reconnect, and live tray tests |
| Requirement 4 | AC1-AC11 | Versioned local contract, peer authorization, structured records, allowlisted actions | Contract, authorization, redaction, CLI, and tray tests |
| Requirement 5 | AC1-AC11 | Retention policy fingerprint, shared repository lock, three trigger modes | Policy, trigger, conflict, dry-run, and live retention tests |
| Requirement 6 | AC1-AC6 | Release manifest, asset compatibility, record reconciliation, rollback | Packaging, upgrade, interruption, and rollback tests |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Central action classifier and backend authorization gate | Table-driven routing tests | No command-local privilege guesses |
| CP-002 | Tray is only an IPC client | Process-kill and import-boundary tests | Headless operations have no GUI dependency |
| CP-003 | One repository mutation lock shared by backup and retention | Concurrency and crash-recovery tests | Lock identity derives from protected repository identity |
| CP-004 | Atomic run-record state machine | Transition and interruption tests | One terminal state per run |
| CP-005 | Approved retention fingerprint is carried into execution | Policy serialization and mutation tests | Restic defaults are not trusted |
| CP-006 | Contract/version/auth failure precedes action dispatch | Negative contract tests | No state change on denial |
| CP-007 | OS peer identity and current operator-group membership | Linux peer-credential integration tests | Socket permissions alone are insufficient |
| CP-008 | Startup reconciliation leases abandoned runs and locks | Kill/restart tests | Reconciliation is idempotent |
| CP-009 | Platform adapters implement one shared contract | Linux adapter and Windows test-double suite | No platform fields in public protocol |
| CP-010 | Backup success emits at most one retention trigger | Idempotency and failure-path tests | Trigger occurs after lock release |
| CP-011 | Protected records require current group membership and schema filtering | Authorized/denied/redaction tests | Raw journal data is never returned |

## High-Level Design

### System Architecture

```text
User shell                         Graphical user session
     |                                      |
     v                                      v
/usr/local/bin/timelocker             timelocker-tray
     |                                      |
     +---------- local protocol client -----+
                         |
               platform transport adapter
                         |
       Linux: /run/timelocker/control.sock
       Windows: protected named pipe
                         |
                         v
              root/system TimeLocker backend
                 |       |        |
                 v       v        v
             Run store  Action   Repository
             and audit  policy   mutation lock
                 |                  |
                 +--------+---------+
                          v
                 Backup / retention workers
                          |
                          v
                        Restic
```

### Components and Changes

- **System launcher**
  - Install root-owned `timelocker` and `tl` launchers on the normal system
    path.
  - Resolve one immutable release manifest and never fall back to pyenv, a
    checkout, or a user virtual environment.
  - Keep release code executable but store configuration, credentials, run
    state, and environment files outside the release tree with stricter modes.

- **Action classifier**
  - Classify every public operation as `user_local_read`,
    `user_local_mutation`, `system_read`, `system_action`, or
    `administrator_maintenance`.
  - Only the two system categories use the backend contract.
  - Unknown actions fail closed.

- **Local control server**
  - Own protocol negotiation, request bounds, peer authentication,
    authorization, dispatch, audit, and response redaction.
  - Provide only allowlisted operations: health, run list/detail, diagnostic
    list, schedule summary, backup request, retention request, and future UI
    availability.
  - Never accept executable paths, raw Restic arguments, environment maps,
    repository credentials, or unrestricted filesystem paths.

- **Platform security adapters**
  - Linux: systemd socket/service, `SO_PEERCRED`, NSS group resolution, file
    modes, atomic filesystem storage, and `flock`.
  - Windows: service and named-pipe ACL/token adapter implementing the same
    domain interfaces.

- **Run store**
  - Persist one JSON document per run using temporary-file, `fsync`, and atomic
    replace.
  - Keep a bounded append-only diagnostic stream with structured codes and
    safe summaries.
  - Reconcile non-terminal runs against process/lease ownership at backend
    startup.

- **CLI system client**
  - Add focused `SystemControlClient`; do not expand `CLIServiceManager` with
    backend implementation details.
  - Add `runs list`, `runs show`, and `logs view --scope system`.
  - Preserve `logs view --scope local` and make the selected scope visible in
    output.

- **Independent tray**
  - Move tray construction and platform callbacks behind the standalone tray
    entry point.
  - Poll or subscribe through the protocol adapter with bounded reconnect and
    stale-state handling.

- **Backup and retention workers**
  - Use the same repository lock and run-record writer.
  - Emit structured state transitions and safe diagnostic codes.
  - Emit the post-backup retention request only after terminal backup success
    and lock release.

### Data Models

#### Protocol envelope

```text
Request {
  protocol_version: integer
  request_id: UUID
  action: enum
  parameters: action-specific bounded object
}

Response {
  protocol_version: integer
  request_id: UUID
  status: ok | denied | conflict | unavailable | invalid | failed
  result: action-specific allowlisted object or null
  error_code: stable code or null
  safe_summary: bounded string or null
}
```

#### RunRecord

```text
RunRecord {
  schema_version: integer
  run_id: UUID
  operation: backup | retention
  trigger: scheduled | backup_success | explicit | retry | recovery
  target_id: opaque stable identifier
  policy_fingerprint: optional digest
  started_at: UTC timestamp
  completed_at: optional UTC timestamp
  state: queued | running | succeeded | failed | skipped | interrupted
  result_code: stable code
  safe_summary: bounded string
  counters: allowlisted numeric map
}
```

`RunRecord` excludes repository URIs, credentials, environment values, raw
commands, source paths, selection contents, and raw Restic output.

#### DiagnosticRecord

```text
DiagnosticRecord {
  schema_version: integer
  record_id: UUID
  run_id: optional UUID
  timestamp: UTC timestamp
  level: info | warning | error
  component: allowlisted component code
  message_code: stable code
  safe_summary: bounded string
}
```

#### SystemPolicy

```text
SystemPolicy {
  protocol_version: integer
  operator_group: string
  socket_or_pipe: platform-owned identifier
  max_request_bytes: integer
  max_response_records: integer
  retention_policy: explicit values and approved fingerprint
}
```

The policy file is root-owned and validated before the backend starts.

### Data Flow

#### Protected read

1. CLI or tray connects through the platform transport.
2. Transport adapter obtains kernel/OS peer identity.
3. Authorization service resolves current group membership.
4. Contract validates version, action, request size, and parameters.
5. Run store returns bounded structured records.
6. Response serializer projects only the action's allowlisted fields.
7. Audit records the caller UID/account, action, decision, record count, and
   result code without protected payload contents.

#### Backup-triggered retention

1. Backup worker acquires the repository lock and creates a running record.
2. Backup completes and atomically writes terminal success.
3. Backup releases the lock.
4. Trigger coordinator records an idempotency key derived from backup run ID
   and policy fingerprint.
5. Retention worker acquires the repository lock and creates a distinct run.
6. Retention result is recorded independently.

#### Tray status

1. Tray starts in the user session and connects as the user.
2. Unauthorized users receive a generic unavailable/denied state with no
   protected metadata.
3. Authorized users receive current and recent structured records.
4. Tray reconnects with bounded backoff and never blocks backend work.

## Low-Level Design

### Algorithms and Logic

#### Authorization

```text
authorize(connection, action):
    peer = transport.peer_identity(connection)
    if peer is unavailable:
        deny GENERIC_ACCESS_DENIED
    policy = load_validated_root_policy()
    if not group_resolver.is_current_member(peer.uid, policy.operator_group):
        audit denied action without protected parameters
        deny GENERIC_ACCESS_DENIED
    if action not in allowlist_for_operator_group:
        deny GENERIC_ACCESS_DENIED
    return AuthorizedPrincipal(peer.uid, peer.pid, policy.operator_group)
```

The Linux group resolver uses the account database, not only the peer process's
inherited supplementary-group list. It recognizes both the account's primary
group and supplementary memberships. Authorization is recomputed per request
and fails closed when the peer account, configured group, or current membership
cannot be resolved. No positive membership result is cached across requests.

#### Atomic run transition

```text
transition(run_id, expected_states, new_state, update):
    acquire run-store lock
    current = read and validate record
    require current.state in expected_states
    require current is not terminal
    candidate = schema_validate(current + update + new_state)
    write temporary file, fsync, atomic replace, fsync directory
    release lock
```

Terminal-to-terminal transitions fail without modifying the record.

#### Response projection

```text
project(action, records):
    schema = response_schema_for(action)
    bounded = records[:schema.max_records]
    return [schema.copy_allowlisted_fields(record) for record in bounded]
```

### Function Signatures and Interfaces

```python
class PeerIdentityProvider(Protocol):
    def peer_identity(self, connection: object) -> "PeerIdentity": ...

class GroupMembershipResolver(Protocol):
    def is_current_member(self, uid: int, group_name: str) -> bool: ...

class LocalControlTransport(Protocol):
    def serve(self, handler: "ControlRequestHandler") -> None: ...

class RunRecordStore(Protocol):
    def create(self, record: "RunRecord") -> None: ...
    def transition(self, run_id: UUID, transition: "RunTransition") -> "RunRecord": ...
    def list(self, query: "RunQuery") -> list["RunRecord"]: ...
    def get(self, run_id: UUID) -> "RunRecord | None": ...
    def reconcile_interrupted(self, active_leases: set[str]) -> list[UUID]: ...

class SystemControlClient(Protocol):
    def list_runs(self, query: "RunQuery") -> list["RunRecordView"]: ...
    def get_run(self, run_id: UUID) -> "RunRecordView": ...
    def list_diagnostics(self, query: "DiagnosticQuery") -> list["DiagnosticView"]: ...
    def request_backup(self, request: "BackupActionRequest") -> "ActionReceipt": ...
    def request_retention(self, request: "RetentionActionRequest") -> "ActionReceipt": ...
```

### Error Handling

- Connection absence returns `SYSTEM_BACKEND_UNAVAILABLE` and the manual
  service-health command.
- Authentication and authorization failures return one
  `SYSTEM_ACCESS_DENIED` response without confirming resource existence.
- Version mismatch returns `CONTRACT_VERSION_UNSUPPORTED` with supported
  version bounds and no protected state.
- Invalid or oversized requests are rejected before dispatch.
- Stale locks are recovered only through lease reconciliation.
- Store corruption moves the invalid record to a root-only quarantine
  directory and emits a safe diagnostic; it does not silently discard history.
- Tray failures are local to the tray. CLI and scheduled workers do not import
  tray code and cannot emit tray-toolkit warnings.

### Security, Trust, and Access

- `/run/timelocker` is root-owned and not writable by clients.
- The Linux socket is `root:timelocker-operators` mode `0660`.
- `/var/lib/timelocker`, its run-store and quarantine directories, and
  `/etc/timelocker` remain `root:root`, inaccessible to non-root users, and
  non-writable through symlink traversal; clients read none of them directly.
- Run-store writes use root-created files with restrictive modes, validated
  UUID-derived names, same-directory temporary files, no-follow semantics,
  atomic replacement, and directory `fsync`.
- Group membership is necessary but not sufficient: the server verifies peer
  identity and current membership for each request.
- The backend drops requests containing unknown fields, executable paths,
  environment maps, raw arguments, or unbounded strings.
- Audit records decisions, not secret-bearing payloads. The audit sink is
  root-only and distinct from operator-visible diagnostics; system-log
  projections never return peer UIDs, account names, or another caller's audit
  trail.
- `safe_summary` values are selected from bounded templates keyed by stable
  diagnostic codes. They are never copied from exception strings, subprocess
  output, command arguments, environment values, repository URIs, or protected
  paths.
- The transport enforces bounded request size, read/idle timeouts, connection
  concurrency, and response pagination before allocating unbounded work.
- The operator group does not imply repository credential access, raw journal
  access, arbitrary restore, schedule editing, retention-policy editing, or
  administrator maintenance.
- Windows named-pipe security must derive the caller token and current group
  membership rather than trust payload identity.

### Migration and Compatibility

1. Install new backend, socket, group, run-store directory, and launchers in a
   disabled/staged state.
2. Preserve the current backup timer and root environment file.
3. Wrap scheduled execution with run recording and shared locking while leaving
   the backup command semantics unchanged.
4. Validate authorized and denied reads before enabling tray or actions.
5. Remove tray construction from `NotificationService` only after the
   independent tray client is available or explicitly disabled.
6. Enable backup requests, retention triggers, and tray actions separately.
7. Retain the prior release and unit assets for rollback.

Existing `timelocker` and `tl` package entry points remain. Existing
`logs view` behavior becomes `--scope local` and remains the default.

### Slice Boundary And Residual Architecture

| Design target | In this slice | Out of this slice | Follow-up destination | Blocks closure? |
|---------------|---------------|-------------------|-----------------------|-----------------|
| Linux system launcher and backend | Full Linux implementation and live acceptance | Other Linux init systems beyond capability reporting | Backlog after Linux reference acceptance | no |
| Windows portability | Shared contracts and adapter test double | Live Windows service/named-pipe implementation | Roadmap/platform follow-up | no |
| Operator system views | Runs and sanitized diagnostics | Direct/raw journald access | Rejected for least privilege | no |
| Independent tray | Linux Mint Cinnamon/X11 client and headless isolation | Full desktop UI | Existing UI backlog | no |
| Retention | Approved 5/4/12/3 policy, three triggers, no prune | Prune automation | Backlog/spec if requested | no |
| User partitions | No implementation | User-scoped selections and restores | GitHub issue #70 | no |

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Protocol/model unit and property tests | Requirements 4-6, CP-003-CP-011 | `verification.md`, CI | Platform kernels still need integration evidence |
| Linux socket authorization integration tests | Requirement 4 AC8-AC11, CP-007, CP-011 | `verification.md` | NSS behavior varies by deployment |
| CLI launcher and action-routing tests | Requirements 1-2 | `verification.md` | Live authorization-agent behavior |
| Headless import and tray lifecycle tests | Requirement 3 | `verification.md` | Desktop-environment diversity |
| Backup/retention lock and trigger tests | Requirement 5 | `verification.md` | Restic/storage timing under production load |
| Live Mint systemd acceptance and rollback rehearsal | Success criteria | `verification.md` | One validated Linux environment |
| `review-timelocker` security and operations review | Trust boundary and recovery | review artifact or verification log | Findings must be resolved before rollout |

## Downstream Task Guidance

- Required checkpoints before implementation: requirements approval, design
  approval, complete traceability, and no unresolved blocking decisions.
- CP-007, CP-008, CP-010, and CP-011 require explicit negative and
  interruption-path tests.
- Do not reuse the existing `AccessManager` session model for OS peer
  authorization.
- Do not make `timelocker-operators` a member of `systemd-journal` or grant it
  access to repository credentials.
- Run security review after the first complete backend/authorization slice and
  again before live rollout.

## Operational Considerations

- Group membership additions normally require a new login session before
  filesystem socket access is available; removals are rejected immediately by
  server-side NSS revalidation.
- Backend health, protocol version, run-store corruption, denied requests,
  trigger conflicts, and interrupted-run reconciliation need stable diagnostic
  codes.
- Rollout must preserve the working 03:30 backup timer until a replacement has
  completed backup and restore acceptance.
- A rollback restores prior launchers and units but preserves run records and
  the approved retention policy.
- Raw journal inspection remains an administrator troubleshooting operation.

## Open Questions

No design-blocking questions remain. The independent retention catch-up schedule
is supported but disabled in the initial production profile; enabling it is a
separate operator decision with duplicate-window validation.

## Related Artifacts

- Requirements: `requirements.md`
- Canonical context: `canonical-context.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
- Verification: `verification.md`

## Reconciliation

Reviewed against the 2026-07-26 requirements revision. AC10-AC11 system-record
authorization, metadata-free denial, current group membership, and local/system
log separation remain fully represented. The security review additionally
clarified fail-closed NSS resolution, root-only audit data, safe-summary
provenance, storage hardening, and transport resource bounds.
