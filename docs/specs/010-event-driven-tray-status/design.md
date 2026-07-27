---
title: Event-driven tray status design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Technical Design

## Overview

Add a typed status snapshot to the existing authenticated control protocol and
a separate authenticated event subscription transport. Events are sanitized
revisioned invalidations, not copies of protected records. The tray subscribes,
fetches an initial snapshot, and refreshes only after a newer event or
reconnection. This preserves the request/response control path while removing
steady-state tray polling.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| Requirement 1 | AC1-AC5 | Subscription handshake, session revisions, invalidation stream | Protocol, broker, integration, idle tests |
| Requirement 2 | AC1-AC5 | Peer identity, per-frame authorization, allowlisted models | Security and negative-control tests |
| Requirement 3 | AC1-AC5 | Backend-derived `StatusSnapshot` and local presentation | Model, store, tray tests |
| Requirement 4 | AC1-AC5 | Separate transport, backoff, heartbeat, bounded clients | Failure, restart, slow-client tests |
| Requirement 5 | AC1-AC6 | Disabled status rows, action-only mutations, and deterministic logo badges | Platform menu/icon tests and Linux acceptance |
| Requirement 6 | AC1-AC4 | Silent serve loop and logging boundary | Captured-stream and logging tests |
| Requirement 7 | AC1-AC5 | Portable interfaces, Linux adapter, Windows contracts, release probes | Platform, package, deployment, rollback tests |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Snapshot builder selects maximum successful backup `completed_at`. | Generated histories plus conventional edge tests | No new property dependency required if Hypothesis is unavailable. |
| CP-002 | `(session_id, sequence)` ordering and coalescing guard. | Generated event sequences | Older/duplicate revisions are ignored. |
| CP-003 | Membership resolver runs before every emitted event or heartbeat. | Revocation and denied-subscription tests | Connection is closed on denial. |
| CP-004 | Initial/reconnect flow always fetches `status.snapshot`. | Restart, gap, and reconnect integration tests | Events are invalidations, not state. |
| CP-005 | Event components have read/status dependencies only. | Interface and lock-spy tests | Mutations retain existing action path. |
| CP-006 | Serve path has no successful-state `print`. | Captured 90-second idle test with shortened test clock | One-shot output remains tested separately. |

## High-Level Design

### System Architecture

```text
user-session tray
    |  request/response                    | long-lived subscription
    v                                      v
control.sock                         status-events.sock
    |                                      |
    v                                      v
authenticated dispatcher        authenticated event transport
    |                                      |
    +------- status.snapshot <---- status event broker
                                           ^
                                           |
                              record/schedule change sources
```

The control socket remains bounded to one request and response per connection.
The event socket is separate so a long-lived subscriber cannot block CLI
requests or mutation actions.

### Components and Changes

- **Status models and snapshot builder**
  - Add allowlisted `StatusSnapshot`, `StatusRevision`, and `StatusEvent`
    models.
  - Compute last successful backup by maximum successful `completed_at`.
  - Preserve latest attempt state separately.
- **Control protocol**
  - Add `status.snapshot` as a read-only authorized action.
  - Bump and negotiate protocol compatibility if the wire schema changes.
- **Event broker**
  - Own one random backend-session ID and a monotonic sequence.
  - Coalesce pending changes; retain no unbounded event history.
  - Emit only invalidation, heartbeat, and resynchronization event kinds.
- **Change sources**
  - Explicitly notify after TimeLocker-owned run and schedule mutations.
  - Monitor protected atomic record/schedule state changes produced by separate
    workers through an injectable platform change-watcher boundary.
- **Linux event transport**
  - Adopt a systemd-owned AF_UNIX listener.
  - Derive `SO_PEERCRED`, enforce current NSS membership, bound connections and
    frames, and disconnect slow or unauthorized clients.
- **Windows event contract**
  - Define injectable named-pipe acceptor, peer-token, subscription, and send
    interfaces with contract/security tests.
  - Defer concrete service deployment and live acceptance.
- **Tray subscription client**
  - Run blocking event reads independently from the desktop event loop.
  - Signal the presentation loop to fetch a fresh snapshot after newer events.
  - Reconnect with bounded exponential backoff and coalesce refresh requests.
- **Tray presentation**
  - Replace `View Status` with non-actionable status rows.
  - Keep `Open TimeLocker` absent.
  - Remove periodic successful stdout rendering from `serve`.

### Data Models

```text
StatusRevision
  session_id: UUID
  sequence: non-negative integer

StatusEvent
  schema_version: integer
  protocol_version: integer
  revision: StatusRevision
  kind: snapshot_required | changed | heartbeat | resync_required

StatusSnapshot
  revision: StatusRevision
  backend_status: bounded enum
  active_operations: non-negative integer
  latest_backup: optional safe run summary
  last_successful_backup_completed_at: optional UTC datetime
  latest_retention: optional safe run summary
  next_backup_at: optional UTC datetime
  next_retention_at: optional UTC datetime
```

The exact snapshot schema must reuse existing stable enums and safe summaries.
It must not include arbitrary strings, raw commands, paths, environment data,
or backend output.

### Data Flow

1. Tray connects to the event socket.
2. Backend derives peer identity and authorizes current group membership.
3. Backend sends `snapshot_required` with the current revision.
4. Tray requests `status.snapshot` through the control socket and renders it.
5. A durable run or managed schedule change advances the broker sequence.
6. Backend reauthorizes each subscriber and sends one coalesced `changed`
   event.
7. Tray fetches and renders the newest snapshot if its revision is newer.
8. On disconnect, session change, gap, or `resync_required`, the tray reconnects
   and repeats the initial snapshot flow.

## Low-Level Design

### Algorithms and Logic

```text
on_subscription_connected(peer):
    authorize(peer)
    send(snapshot_required, broker.current_revision)
    while connected:
        event = broker.next_event_or_heartbeat()
        authorize(peer)
        send(event)

on_tray_event(event):
    if event.session_id != applied.session_id:
        request_snapshot()
    elif event.sequence > applied.sequence:
        coalesce_refresh_request(event.sequence)
    ignore duplicate or older revisions

build_status_snapshot():
    runs = protected_store.list_for_status()
    successful = backup runs with state SUCCEEDED and completed_at present
    last_success = max(successful, key=completed_at, default=None)
    return sanitized snapshot at broker.current_revision
```

The snapshot builder and revision read must use a synchronization boundary that
prevents returning a snapshot marked newer than the state it contains. If a
change races with snapshot construction, the resulting newer event causes
another refresh.

### Function Signatures and Interfaces

```text
class StatusSnapshotProvider(Protocol):
    def snapshot(self) -> StatusSnapshot: ...

class StatusEventBroker(Protocol):
    def current_revision(self) -> StatusRevision: ...
    def publish_change(self, kind: StatusChangeKind) -> StatusRevision: ...
    def subscribe(self) -> StatusSubscription: ...

class StatusEventTransport(Protocol):
    def serve(self, broker, identity_provider, membership_resolver) -> None: ...

class StatusEventClient(Protocol):
    def events(
        self,
        stop_event,
        *,
        on_connection_state: Callable[[StatusEventConnectionState], None] | None,
    ) -> Iterator[StatusEvent]: ...
```

### Error Handling

- Invalid, oversized, unknown-version, or unauthorized subscription frames fail
  closed with a stable safe result and connection close.
- Platform clients project `connected`, `denied`, and `unavailable` connection
  states through the platform-neutral callback. Linux maps an operating-system
  socket `PermissionError` to `denied`; other transport failures map to
  `unavailable` while bounded reconnect continues.
- Event channel unavailability changes tray presentation to unavailable but
  does not disable explicit control-channel commands.
- Backoff is bounded and resets only after a successful authorized handshake.
- Slow subscribers retain at most the newest pending revision; if they cannot
  keep up, the backend disconnects them.
- Watcher overflow or uncertainty emits `resync_required`.
- Logging uses stable codes and redacted summaries with repetition control.

### Security, Trust, and Access

- `/run/timelocker/status-events.sock` is root-owned and group-accessible only
  to the configured operator group.
- Linux identity comes from `SO_PEERCRED`; Windows identity comes from the
  connected named-pipe token. Request content never asserts identity.
- Membership is checked at subscription and before each event or heartbeat,
  bounding group-removal latency by the heartbeat interval.
- Event payloads are allowlisted and independently size-bounded.
- The tray never reads `/var/lib/timelocker`, `/etc/timelocker`, environment
  files, journal content, or repository credentials.
- The event path cannot invoke backup, retention, release selection, or
  arbitrary commands.

### Migration and Compatibility

- Existing CLI control actions remain request/response compatible.
- Release metadata records both control and event protocol compatibility.
- Activation installs and probes the event socket/service assets before
  selecting the release.
- A new tray paired with an incompatible backend shows a safe unavailable state
  rather than reverting to indefinite status polling.
- Linux uses packaged deterministic variants of the TimeLocker logo. A
  shape-coded badge distinguishes running, success, warning or never-run, and
  failure without requiring a runtime image library or relying on colour alone.
- Rollback selects the prior coherent CLI/backend/tray release. Additional
  event assets may remain inert, but must not break the prior control socket,
  backup timer, or retention timer.

### Slice Boundary And Residual Architecture

| Design target | In this slice | Out of this slice | Follow-up destination | Blocks closure? |
|---------------|---------------|-------------------|-----------------------|-----------------|
| Event-driven local tray status | Snapshot, broker, subscription, Linux transport, tray client | Remote/network subscribers | rejected: outside charter | no |
| Portable desktop contract | Platform-neutral protocol and Windows contract tests | Concrete Windows service, installer, live acceptance | follow-up Windows acceptance spec | no |
| Tray status presentation | Current status rows and mutation actions | Full desktop app or restore UI | product backlog/roadmap | no |
| Reliable change detection | TimeLocker-owned run/schedule changes and resync on uncertainty | Arbitrary external systemd edits without TimeLocker mediation | operator restart/reload guidance | no |

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Model/protocol/property tests | Requirements 1-3; CP-001-CP-004 | `verification.md`, task evidence | Generated histories may not represent all host races. |
| Transport/security tests | Requirements 2, 4, 7; CP-003, CP-005 | `verification.md`, security review | NSS and named-pipe behavior need live platform evidence. |
| Tray/menu/output tests | Requirements 3, 5, 6; CP-006 | `verification.md`, focused tests | Desktop toolkit variations. |
| Configured regression and package smoke | Compatibility and release integrity | `verification.md`, CI/command evidence | Host timing and optional integrations. |
| Approved Linux Mint acceptance | End-to-end event, restart, authorization, rollback | `verification.md`, root-owned evidence path | Requires explicit deployment and operation approval. |

## Downstream Task Guidance

- Complete protocol/security review before transport implementation.
- Give CP-001, CP-002, CP-003, CP-004, and CP-006 explicit test coverage.
- Preserve the existing uncommitted removal of `Open TimeLocker`.
- Run `$review-timelocker` after a runnable implementation and before live
  deployment.
- Reconcile design and traceability if concrete Windows delivery enters scope.

## Operational Considerations

- Install the event socket with the same operator-group ownership model as the
  control socket.
- Keep the control socket as the service's required activation dependency and
  the event socket as a weak dependency. The backend accepts a named control
  descriptor without an event descriptor and disables only event delivery in
  that mode, so an event-unit failure cannot disable explicit control actions.
- Expose health without raw subscriber identities or payloads.
- Record bounded connection counts and safe error codes, not user data.
- Activation and rollback must verify both timers remain active and enabled.
- Live acceptance must avoid production mutation unless separately approved.
- Measure ordinary status-change latency from completed state mutation to tray
  presentation. Measure backend restart as separate graceful-shutdown and
  new-service-start-to-fresh-presentation intervals; do not count shutdown time
  against the ordinary two-second change budget.

## Open Questions

None currently block implementation review. Any change from a dedicated event
transport, per-event authorization, or invalidation-plus-snapshot model requires
design reconciliation and user approval.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Change Impact: [change-impact.md](./change-impact.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
