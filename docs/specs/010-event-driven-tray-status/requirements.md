---
title: Event-driven tray status requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Requirements

## Introduction

The independent tray currently polls the protected backend every 30 seconds,
prints each successful refresh to standard output, reports the newest backup
attempt's start time as the last backup, and exposes a `View Status` action
that does not open a view. The tray needs an authenticated event-driven status
path and precise operator-facing semantics without becoming part of the CLI or
privileged backend.

## Goals

- Deliver backend status changes to an authorized tray without steady-state
  status polling.
- Show the completion time of the most recent successfully completed backup.
- Present useful status directly in the tray menu and keep background operation
  quiet.
- Preserve fail-closed authorization, privacy, process independence, immutable
  release rollback, and portable Linux/Windows contracts.

## Non-Goals

- A full desktop application, settings window, restore browser, or remote API.
- Direct tray access to protected record files, journals, credentials, or
  privileged commands.
- Live Windows deployment acceptance in this package.
- Replacing the existing request/response control channel for CLI actions.
- Guaranteeing delivery across process failure without reconnecting and
  obtaining a fresh snapshot.

## Glossary

| Term | Definition |
|------|------------|
| Status snapshot | A typed, sanitized backend projection of current activity, recent results, and known schedules. |
| Status event | A bounded notification that a newer status snapshot may be available. |
| Subscription revision | A backend-session identifier and monotonic sequence used to order and coalesce status events. |
| Healthy subscription | An authorized event connection that has completed its initial snapshot and has not failed or timed out. |
| Last successful backup | The backup run in `SUCCEEDED` state with the greatest non-null `completed_at` value. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | The CLI remains primary; optional tray integration must support dependable, observable backup operations. | high | Governing mandate. |
| `docs/1-requirements/system-operations.md` | Protected reads are group-authorized; the tray is independent and may show run and schedule status. | high | Current durable requirements. |
| `docs/2-architecture/system-architecture.md` | The tray currently polls the AF_UNIX backend; protected output is structured and redacted. | high | This spec changes the polling statement. |
| `docs/3-implementation/service-layer-integration.md` | `system_control` owns typed IPC, authorization, records, and the independent tray client. | high | Ownership remains unchanged. |
| `docs/SYSTEM-TRAY-SETUP.md` | Linux tray setup, authorization, failure behavior, and current menu capability. | high | Promotion target. |
| `src/TimeLocker/system_control/` and focused tests | Current protocol is one bounded request/response per control connection. | high | Code-derived contract. |

## Durable Impact

See [change-impact.md](./change-impact.md). Accepted behavior must be promoted
before closure.

## Staged Readiness

- **Current stage:** implementation
- **Next stage:** T001 contract implementation
- **Ready to implement:** yes - lifecycle lint and readiness pass, acceptance
  criteria are traceable, and user approval was recorded on 2026-07-27.
- **Design-first exception:** no
- **Optional artifacts included:** `change-impact.md`, `traceability.md`,
  `verification.md`, `canonical-context.md`
- **Downstream review needed:** requirements, design, tasks, traceability,
  verification

## Requirements

### Requirement 1: Event-Driven Status Delivery

**User Story:** As an operator, I want the tray to react to backend changes, so
that status is current without repeated polling and terminal output.

**Priority:** must-have

#### Acceptance Criteria

1. GIVEN an authorized tray starts or reconnects, WHEN it establishes a status
   subscription, THEN it SHALL obtain an initial status snapshot before
   presenting the connection as current.
2. WHILE a subscription is healthy, THE TRAY SHALL NOT issue periodic status
   snapshot requests solely because a fixed refresh interval elapsed.
3. WHEN backup, retention, backend-availability, or TimeLocker-managed schedule
   status changes in the backend process or a separate protected worker, THEN
   an authorized connected tray SHALL be prompted to refresh within two seconds
   under normal local-host load.
4. WHEN multiple changes occur faster than the tray can render them, THEN the
   system SHALL coalesce them without applying an older revision after a newer
   revision.
5. WHEN the subscription session changes or a revision gap is detected, THEN
   the tray SHALL discard incremental assumptions and obtain a fresh snapshot.

### Requirement 2: Authorization And Privacy

**User Story:** As an administrator, I want event subscriptions to preserve the
protected control boundary, so that continuous status does not weaken access
control or expose secrets.

**Priority:** must-have

#### Acceptance Criteria

1. WHEN a client subscribes, THEN the backend SHALL derive its identity from
   the operating-system transport and verify current operator-group membership.
2. BEFORE sending each status event or heartbeat, THE BACKEND SHALL re-evaluate
   current membership, and SHALL disconnect a client whose authorization is no
   longer valid.
3. THE STATUS SNAPSHOT AND EVENT CONTRACTS SHALL contain only versioned,
   allowlisted fields and SHALL NOT expose credentials, environment contents,
   raw backend output, raw journal content, or unnecessary protected paths.
4. IF event authorization or transport validation fails, THEN the tray SHALL
   show a safe unavailable or denied state and SHALL NOT fall back to privileged
   execution or direct protected-file access.
5. WHEN an unauthorized local client attempts to subscribe, THEN it SHALL
   receive no status payload beyond a bounded safe denial.

### Requirement 3: Accurate Backup Health And Activity

**User Story:** As an operator, I want the tray's backup time to mean successful
completion, so that a failed or running attempt cannot misrepresent protection.

**Priority:** must-have

#### Acceptance Criteria

1. THE `Last Backup` value SHALL be selected only from backup runs in
   `SUCCEEDED` state and SHALL display that run's `completed_at` time.
2. WHEN a newer backup is queued, running, failed, skipped, or interrupted,
   THEN it SHALL NOT replace the last successful backup completion time.
3. WHEN no successful backup exists, THEN the tray SHALL display `Never` or
   `Unknown`, not the time of another run state.
4. WHERE a latest backup or retention attempt exists, THE STATUS SNAPSHOT SHALL
   preserve its safe state and summary separately from the last successful
   backup completion.
5. WHEN a timestamp is displayed, THEN the tray SHALL convert the stored
   timezone-aware UTC value to the desktop session's local time and identify
   the timezone.
6. THE BACKEND SHALL derive backup schedule health from the configured system
   timer, its service state, and durable backup-run records without granting the
   tray direct systemd or protected-file access.
7. WHEN an enabled scheduled occurrence passes its configured grace deadline
   without a matching active or terminal backup run, THEN schedule health SHALL
   become `backup_missed`. A failed matching run SHALL be `backup_failed`, not
   `backup_missed`.

### Requirement 4: Resilience And Process Independence

**User Story:** As an operator, I want tray failures and backend restarts to be
recoverable, so that presentation failures never disrupt backup or retention.

**Priority:** must-have

#### Acceptance Criteria

1. WHEN the tray process starts, THEN it SHALL present a connecting state before
   beginning backend subscription work. WHEN the backend or event channel is
   unavailable, THEN the presented tray SHALL remain responsive and reconnect
   using bounded exponential backoff.
2. WHEN the backend restarts, THEN a connected or reconnecting tray SHALL
   establish a new subscription session and obtain a fresh snapshot.
3. THE BACKEND SHALL bound subscriber count, frame size, queued event state,
   heartbeat interval, and slow-client handling.
4. WHEN a tray exits, crashes, or is killed, THEN backend services and active
   backup or retention operations SHALL continue unaffected.
5. WHEN the event channel fails while the request/response control channel
   remains available, THEN explicit CLI status and action requests SHALL remain
   functional.

### Requirement 5: Useful And Honest Tray Presentation

**User Story:** As an operator, I want the tray menu to show actionable current
status, so that its labels accurately describe what they do.

**Priority:** must-have

#### Acceptance Criteria

1. THE MENU SHALL contain exactly three non-actionable status rows: `State`,
   `Activity`, and `Last Backup`. `State` SHALL contain health only; `Activity`
   SHALL contain transient work such as connecting, backup running, retention
   running, or idle.
2. THE MENU SHALL NOT show `Open TimeLocker` until an implemented desktop
   application exists.
3. THE MENU SHALL NOT show an actionable `View Status` item unless activating
   it opens a distinct status view; for this slice, status SHALL be represented
   by non-actionable menu rows.
4. `Backup Now` and conditionally configured `Run Retention` SHALL remain the
   only mutation actions exposed by this slice, in addition to `Quit`.
5. WHEN a status event arrives, THEN the visible menu SHALL update without
   restarting the tray process.
6. ON Linux, THE TRAY SHALL preserve the TimeLocker logo while applying a
   distinct non-colour-only badge consistent with health and activity. Running
   activity MAY temporarily select the running badge; otherwise failed, missed,
   unavailable, disabled, healthy, and never-run health SHALL select an honest
   error, warning, success, or idle badge.
7. `State` SHALL use bounded user-facing values including `Healthy`,
   `Backup failed`, `Backup missed`, `Schedule disabled`,
   `Backend unavailable`, and `Access denied`. Connection progress and running
   operations SHALL NOT be reported as health states.

### Requirement 6: Quiet Background Operation

**User Story:** As a desktop user, I want the background tray to be silent
during normal operation, so that it does not pollute session output or logs.

**Priority:** must-have

#### Acceptance Criteria

1. WHILE `timelocker-tray serve` is healthy, THE PROCESS SHALL NOT write
   periodic successful status snapshots to standard output or standard error.
2. WHEN an operator explicitly invokes a one-shot `status` action, THEN the
   command SHALL continue to render a bounded human-readable result.
3. WHEN a recoverable connection failure repeats, THEN diagnostics SHALL use
   the configured logging path with bounded repetition rather than unbounded
   terminal output.
4. WHEN debug logging is explicitly enabled, THEN connection and event
   diagnostics MAY be emitted without including protected or secret values.

### Requirement 7: Portable Contract And Safe Rollout

**User Story:** As a maintainer, I want the event contract separated from its
transport, so that Linux is deliverable now without blocking a later Windows
implementation.

**Priority:** must-have

#### Acceptance Criteria

1. THE STATUS SNAPSHOT, EVENT, subscription, reconnect, and authorization
   interfaces SHALL be platform-neutral.
2. Linux SHALL provide a protected local event transport with peer-derived
   identity and systemd-managed deployment assets.
3. Windows SHALL have injectable named-pipe event-transport contracts and
   platform tests, without this package claiming live Windows acceptance.
4. Activation SHALL verify compatible CLI, backend, tray, control protocol, and
   event protocol artifacts before selecting a release.
5. Rollback SHALL restore the prior selected release without disabling backup,
   retention, or explicit control-channel status commands.

## Correctness Properties

- **CP-001:** For any run history, the displayed last successful backup is
  either absent or equals the maximum `completed_at` among successful backup
  runs.
- **CP-002:** Within one subscription session, applied event revisions are
  strictly increasing; duplicate or older events do not regress presentation.
- **CP-003:** No event payload is delivered after the backend observes that the
  subscriber is no longer an operator-group member.
- **CP-004:** Reconnect or session change always converges to the same snapshot
  that an authorized one-shot status request would return.
- **CP-005:** Tray lifecycle operations cannot acquire the repository mutation
  lock or alter an active run except through existing allowlisted requests.
- **CP-006:** A healthy tray over any interval emits zero periodic successful
  status records to stdout or stderr.
- **CP-007:** An enabled backup occurrence becomes missed only after its grace
  deadline when no matching active or terminal backup run exists; any matching
  failed run is reported as failed instead.

## Technical Context

- **Language/Version:** Python 3.12-3.13
- **Primary Dependencies:** standard library sockets/threading, existing GTK or
  platform tray adapters, systemd on accepted Linux deployments
- **Target Platform:** production acceptance on Linux Mint; portable Windows
  contracts and tests
- **Constraints:** local-only IPC, current group authorization, bounded frames,
  safe projections, immutable releases, no GUI dependency in CLI/backend
- **Performance Goals:** present the connecting tray before starting backend
  subscription work; event-to-menu update within two seconds under normal local
  load; no steady-state snapshot polling; bounded idle heartbeat

## Success Criteria

- **SC-001:** Integration evidence shows zero fixed-interval status requests
  during at least 90 seconds of healthy idle subscription.
- **SC-002:** A successful backup transition updates the tray within two
  seconds, while a later failed transition leaves its last-success time intact.
- **SC-003:** Authorization tests prove denial at subscribe time and disconnect
  before the next event/heartbeat after membership removal.
- **SC-004:** Restart and revision-gap tests converge to a fresh snapshot
  without restarting the desktop session.
- **SC-005:** Focused, platform-contract, security, configured regression,
  packaging, and approved Linux acceptance checks pass with no secret-bearing
  output.

## Related Artifacts

- Change Impact: [change-impact.md](./change-impact.md)
- Design: [design.md](./design.md)
- Tasks: [tasks.md](./tasks.md)
- Verification: [verification.md](./verification.md)
