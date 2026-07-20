---
title: System CLI, independent tray, and retention requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-20
---

# Requirements

## Introduction

TimeLocker now runs the machine's production backup through a root-owned,
systemd-managed installation, but operators must invoke a virtual-environment
path, retention remains manual, and ordinary CLI service construction can try
to initialize desktop tray components. The tray is currently an in-process
notification integration rather than an independent desktop client, and
operation history is not yet a single durable cross-process contract.

This package defines a coherent system-operations experience: a stable
system-path command that requests elevation only when required, an independent
per-user tray process, a local authenticated control/status boundary, and
separately scheduled retention with visible outcomes.

## Goals

- Install a stable `timelocker` command on the system path and retain `tl` as a
  compatible alias.
- Let unprivileged commands remain unprivileged while privileged system actions
  request elevation through an explicit, reviewable boundary.
- Remove all tray initialization from normal CLI, scheduler, and backend
  execution paths.
- Run the tray as an independent process in the signed-in user's graphical
  session.
- Let the tray observe current work, last backup, last retention run, and next
  scheduled runs, and safely request an on-demand backup.
- Automate the accepted production retention policy independently of backup:
  keep 5 daily, 4 weekly, 12 monthly, and 3 yearly snapshots without prune.
- Preserve safe rollback, headless operation, secret isolation, and failure
  independence between backup, retention, CLI, and tray processes.

## Non-Goals

- Building the future full desktop UI or presenting an unimplemented UI as
  available.
- Implementing a network-accessible REST API, hosted control plane, or remote
  administration service.
- Running the tray as root or granting the desktop process direct access to
  protected repository credentials.
- Automatically elevating every TimeLocker command or bypassing an operator's
  authorization policy.
- Enabling Restic prune as part of the initial automated retention policy.
- Allowing retention failure to make an otherwise successful backup appear to
  have failed, or vice versa.
- Implementing user-scoped management of the user's accessible subset of the
  system backup. That capability belongs in the product backlog and must later
  receive its own access-control and restore-boundary specification.

## Glossary

| Term | Definition |
|------|------------|
| System command | The stable `timelocker` executable discoverable through the normal system `PATH`. |
| System backend | The privileged, headless execution boundary that owns machine-level configuration and scheduled operations. It does not imply a network service. |
| Tray client | An unprivileged process running in a user's graphical session and communicating through the approved local control/status boundary. |
| Elevation broker | The narrow operating-system authorization path used to request a privileged operation without making the whole desktop or CLI session privileged. |
| Run record | Durable, secret-free status for one backup or retention attempt, including type, target, timestamps, state, result, and safe error summary. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | TimeLocker is CLI-first and may provide optional tray integration, automation, monitoring, and schedules. | high | The proposed work is within the current mandate and remains short of a full GUI or hosted service. |
| `pyproject.toml` | Both `timelocker` and `tl` resolve to `TimeLocker.cli:main` after package installation. | high | Package entry points do not by themselves provide the machine deployment's stable system-path launcher. |
| `src/TimeLocker/monitoring/notification_service.py` | Notification service construction currently initializes `SystemTrayIntegration` in-process. | high | This causes CLI/headless coupling and produced warnings during a retention dry run. |
| `src/TimeLocker/monitoring/system_tray_integration.py` | Platform tray rendering and callbacks exist as a library component. | high | It is not an independently managed process or a backend client. |
| `src/TimeLocker/cli_modules/commands/schedule.py` | Generated schedules currently execute `tl backup create` only. | high | Retention is not chained or separately scheduled. |
| `src/TimeLocker/cli_modules/commands/repositories.py` | `tl repos forget` supports explicit daily, weekly, monthly, yearly, dry-run, and optional prune values. | high | Production dry run passed with 5/4/12/3 and no prune. |
| `docs/guides/developer/scheduling-guide.md` | Backup schedules and the current manual-retention boundary are documented. | high | Promotion target for accepted installation and maintenance behavior. |
| `docs/SYSTEM-TRAY-SETUP.md` | Current tray documentation describes optional in-process monitoring and notifications. | high | Must be replaced or rewritten when independent tray behavior is implemented. |

## Durable Impact

| Durable area | Action | Target | Notes |
|--------------|--------|--------|-------|
| requirements | add | `docs/1-requirements/system-operations.md` | Promote privilege, status, retention, and process-boundary invariants. |
| architecture | modify | `docs/2-architecture/system-architecture.md` | Document CLI, backend, tray, local control/status, and durable run-state boundaries after implementation. |
| architecture | modify | `docs/2-architecture/scheduling-system.md` | Document independent backup and retention scheduling and overlap control. |
| implementation | modify | `docs/3-implementation/service-layer-integration.md` | Identify the owning services and prohibit UI initialization in headless execution. |
| runbook | modify | `docs/guides/developer/scheduling-guide.md` | Document installation, retention staging, rollback, and validation. |
| user guide | modify | `docs/guides/user/installation.md` | Document system-path command and supported elevation behavior. |
| user guide | supersede | `docs/SYSTEM-TRAY-SETUP.md` | Replace current in-process assumptions with the independent tray lifecycle. |

## Staged Readiness

- **Current stage:** requirements
- **Next stage:** design
- **Ready to design when:** elevation and tray trust boundaries, operation
  status semantics, retention policy, failure isolation, compatibility, and
  roadmap exclusions are accepted.
- **Design-first exception:** no
- **Optional artifacts recommended:** `research.md`, `change-impact.md`, and
  `open-decisions.md`
- **Downstream review needed:** design, security, operations, desktop
  integration, testing, traceability, and verification
- **Concurrent package sequencing:** Spec 007 has no incomplete task but still
  needs evidence-quality reconciliation and closure. Spec 009 may author
  requirements and design concurrently; implementation must not reuse Spec
  007 release evidence as proof and must preserve its release-readiness gates.

## Requirements

### Requirement 1: Stable system-path command

**User Story:** As an operator, I want to invoke TimeLocker by name from a
normal shell, so that machine operations do not depend on knowing an internal
release or virtual-environment path.

**Priority:** must-have

#### Acceptance Criteria

1. GIVEN a supported system installation, WHEN the operator resolves
   `timelocker`, THEN it SHALL execute the current immutable TimeLocker release
   through a root-owned system-path launcher.
2. THE `tl` alias SHALL remain available and behaviorally compatible.
3. GIVEN a release switch or rollback, WHEN either command is invoked, THEN it
   SHALL resolve the same selected release without rewriting user shell files.
4. IF the selected release is missing or invalid, THEN the launcher SHALL fail
   without falling back to a mutable checkout, user environment, or legacy
   root configuration overlay.

### Requirement 2: Contextual privilege elevation

**User Story:** As an operator, I want TimeLocker to request elevation only for
operations that require system authority, so that routine inspection remains
convenient without widening privilege unnecessarily.

**Priority:** must-have

#### Acceptance Criteria

1. GIVEN a read-only operation whose data is accessible to the caller, WHEN it
   runs, THEN TimeLocker SHALL remain in the caller's security context.
2. GIVEN an allowlisted machine-level operation that requires elevated access,
   WHEN an interactive caller invokes it, THEN TimeLocker SHALL request
   authorization through the supported operating-system elevation mechanism
   and preserve the intended command arguments.
3. IF no interactive authorization agent or terminal is available, THEN the
   command SHALL fail promptly with the exact manual or automation-safe next
   action; it SHALL NOT wait indefinitely.
4. ELEVATION SHALL NOT forward repository passwords, unrestricted environment
   variables, display/session credentials, or arbitrary executable paths.
5. THE SYSTEM SHALL prevent recursive elevation and SHALL record a secret-free
   audit event identifying the requested operation, caller, decision, and
   result.
6. A denied or failed elevation SHALL leave configuration, schedules,
   repositories, and run state unchanged.

### Requirement 3: Independent tray process

**User Story:** As a desktop user, I want the TimeLocker tray to run separately
from backup commands, so that desktop integration neither destabilizes nor
pollutes headless operations.

**Priority:** must-have

#### Acceptance Criteria

1. CLI, scheduler, retention, and backend processes SHALL NOT import,
   initialize, or shut down a platform tray implementation during ordinary
   command execution.
2. THE tray SHALL run as a separately installable and independently restartable
   process in the signed-in user's graphical session, never as root.
3. IF the tray is absent, crashes, or cannot connect, THEN scheduled backup and
   retention SHALL continue unaffected.
4. IF the backend is unavailable, THEN the tray SHALL display a disconnected
   or unavailable state without presenting stale success as current.
5. Starting more than one tray instance for the same user SHALL be prevented or
   resolved deterministically.
6. The tray lifecycle SHALL support Linux Mint's GNOME-based session first and
   retain explicit portability boundaries for other supported platforms.

### Requirement 4: Local control and status contract

**User Story:** As a desktop user, I want the tray to show what TimeLocker is
doing and request a backup safely, so that I can understand and operate the
machine backup without handling protected credentials.

**Priority:** must-have

#### Acceptance Criteria

1. THE backend SHALL expose an authenticated, local-only, versioned contract
   for current operation state, last backup run, last retention run, next
   scheduled runs, and safe error summaries.
2. Run state SHALL persist across CLI and scheduler processes and remain
   inspectable after process exit and system restart.
3. Backup and retention run records SHALL be distinguishable and SHALL include
   start time, completion time, state, result, target identity, and a
   secret-free diagnostic summary.
4. THE tray MAY request an on-demand backup only through an allowlisted backend
   action that performs normal authorization, validation, locking, and audit.
5. IF a conflicting backup or retention operation is active, THEN a new request
   SHALL be rejected or queued according to one documented policy; it SHALL NOT
   start an unsafe concurrent Restic mutation.
6. Status and control messages SHALL NOT contain repository passwords, cloud
   credentials, unrestricted environment data, or unredacted Restic output.
7. The contract SHALL reserve a future UI-launch action without claiming that
   a UI exists; until implemented, the tray action SHALL be hidden or clearly
   unavailable.

### Requirement 5: Automatic retention as an independent operation

**User Story:** As an operator, I want TimeLocker to apply my retention policy
automatically after backups, so that snapshot cleanup is consistent without
coupling deletion to backup success.

**Priority:** must-have

#### Acceptance Criteria

1. THE production policy SHALL explicitly keep 5 daily, 4 weekly, 12 monthly,
   and 3 yearly snapshots and SHALL leave prune disabled.
2. BEFORE first enablement or any policy change, THE SYSTEM SHALL support a dry
   run using the same repository, credentials, grouping semantics, and policy
   values as the eventual mutation.
3. Retention SHALL use a separately identifiable service and schedule from the
   backup service and schedule.
4. Retention SHALL NOT run while a backup or another repository mutation is
   active, and a skipped conflict SHALL be visible as a run result rather than
   silently lost.
5. A retention failure SHALL NOT rewrite the preceding backup result, and a
   backup failure SHALL NOT implicitly authorize retention.
6. Each retention attempt SHALL produce a durable run record visible through
   the CLI and tray, including whether it was a dry run and how many snapshots
   were selected or removed.
7. Disabling automatic retention SHALL be reversible without disabling
   backups, and rollback guidance SHALL preserve the manual forget command.

### Requirement 6: Installation, upgrade, and recovery safety

**User Story:** As an operator, I want the launcher, backend, schedules, and
tray to upgrade and roll back coherently, so that a partial deployment cannot
silently select the wrong code or privilege boundary.

**Priority:** must-have

#### Acceptance Criteria

1. System launchers, privileged units, local contract definitions, and tray
   startup assets SHALL be installed from one committed release artifact or a
   compatibility-checked set of artifacts.
2. Upgrade SHALL validate launcher resolution, backend health, contract
   compatibility, timer state, and tray reconnection before retiring the prior
   release.
3. Rollback SHALL restore the prior selected release and compatible system
   assets without deleting run records or changing retention policy.
4. Headless installations SHALL remain supported without GUI dependencies or
   tray warnings.

## Correctness Properties

- **CP-001:** An operation executes with elevated authority if and only if its
  centrally classified action requires that authority and authorization was
  granted.
- **CP-002:** Removing, stopping, or crashing every tray process cannot stop,
  start, or alter a scheduled backup or retention run by itself.
- **CP-003:** At most one mutating Restic operation for the protected repository
  is active at any time.
- **CP-004:** Every completed or failed backup and retention attempt yields one
  durable terminal run record without secret material.
- **CP-005:** The enabled production retention invocation always carries the
  explicit tuple `(5, 4, 12, 3, prune=false)`; no CLI default may change it.
- **CP-006:** A denied elevation or incompatible client/backend contract causes
  no privileged mutation.

## Technical Context

- **Language/Version:** Python 3.12-3.13
- **Primary Dependencies:** Typer, systemd on Linux, Restic, existing
  monitoring and scheduling services, optional PyGObject tray support
- **Target Platform:** Linux Mint GNOME first; preserve documented macOS and
  Windows compatibility boundaries
- **Constraints:** local-first, least privilege, root-owned production
  configuration, no secret-bearing IPC, immutable release selection, no
  unsafe backup/retention overlap
- **Performance Goals:** status reads should feel interactive and must not
  initialize the repository or block on Restic; tray disconnection must not
  delay backend work

## Success Criteria

- **SC-001:** `command -v timelocker` and `command -v tl` resolve the selected
  system release without a project checkout or virtual-environment path in the
  caller's command.
- **SC-002:** A representative read-only command runs without elevation, while
  a representative privileged command requests authorization once and records
  its result without exposing secrets.
- **SC-003:** CLI and systemd retention runs produce no tray initialization
  attempt or tray warning.
- **SC-004:** Restarting or terminating the tray leaves scheduled operations
  unaffected and the tray recovers current and last-run state after reconnect.
- **SC-005:** An approved on-demand tray backup follows the same lock,
  credentials, configuration, and run-record paths as a scheduled backup.
- **SC-006:** A dry run and one controlled automatic retention run prove the
  explicit 5/4/12/3, no-prune policy and appear in both CLI and tray status.

## Open Questions For Design

- Which Linux elevation split best serves terminal and graphical callers:
  `sudo`, polkit/`pkexec`, a narrow privileged helper, or a combination?
- Which local IPC mechanism provides the smallest authenticated interface and
  cleanest systemd integration without creating a general application server?
- Should the tray read durable run state directly through a read-only library
  or exclusively through the backend contract?
- What exact timer offset and missed-run policy should automatic retention use
  relative to the 03:30 backup? The initial recommendation is daily at 04:30.
- Which existing history implementation should become authoritative, and what
  migration is required for old or in-memory records?

## Routed Future Work

- [GitHub issue #70](https://github.com/Auriora/TimeLocker/issues/70) tracks
  user-scoped backup and restore management: a signed-in user may manage only
  files they can access within the overall system backup. That future work must
  define selection ownership, snapshot visibility, restore destinations,
  symlink and ACL behavior, privilege boundaries, and defenses against using
  the system service to read or write inaccessible paths.

## Related Artifacts

- Change Impact: pending
- Design: pending
- Tasks: pending
- Verification: pending
