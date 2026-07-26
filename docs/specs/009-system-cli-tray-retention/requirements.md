---
title: System CLI, independent tray, and retention requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-26
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
independently runnable retention with backup-success, scheduled, and explicit
triggers plus visible outcomes.

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
- Restrict system-backup status and control to members of a root-controlled
  operator group whose identity is verified by the operating system.
- Automate the accepted production retention policy as an independently
  runnable operation that can be triggered immediately after a successful
  scheduled backup, by its own schedule, or by an explicit request: keep 5
  daily, 4 weekly, 12 monthly, and 3 yearly snapshots, grouped by host and
  paths, without prune.
- Keep shared tray, control/status, and run-state contracts platform-neutral,
  with replaceable Linux and Windows adapters.
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
- Completing every Linux desktop and Windows adapter in the initial delivery.
  The initial implementation may validate one Linux environment first, but it
  must not embed Linux, GTK, systemd, Unix-socket, or filesystem-layout
  assumptions in shared contracts and domain services.

## Glossary

| Term | Definition |
|------|------------|
| System command | The stable `timelocker` executable discoverable through the normal system `PATH`. |
| System backend | The privileged, headless execution boundary that owns machine-level configuration and scheduled operations. It does not imply a network service. |
| Tray client | An unprivileged process running in a user's graphical session and communicating through the approved local control/status boundary. |
| Elevation broker | The narrow operating-system authorization path used to request a privileged operation without making the whole desktop or CLI session privileged. |
| System operator group | A root-controlled operating-system group whose members may inspect system-backup status and request allowlisted system-backup actions. |
| Run record | Durable, secret-free status for one backup or retention attempt, including type, target, timestamps, state, result, and safe error summary. |
| Access domain | The files, metadata, snapshots, and restore destinations a user is authorized to inspect or modify; future user partitions may never expand this boundary. |

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
| architecture | modify | `docs/2-architecture/scheduling-system.md` | Document backup-success, independent-schedule, and explicit retention triggers plus overlap control. |
| implementation | modify | `docs/3-implementation/service-layer-integration.md` | Identify the owning services and prohibit UI initialization in headless execution. |
| runbook | modify | `docs/guides/developer/scheduling-guide.md` | Document installation, retention staging, rollback, and validation. |
| user guide | modify | `docs/guides/user/installation.md` | Document system-path command and supported elevation behavior. |
| user guide | supersede | `docs/SYSTEM-TRAY-SETUP.md` | Replace current in-process assumptions with the independent tray lifecycle. |

## Staged Readiness

- **Current stage:** design and task-plan review
- **Next stage:** implementation
- **Ready to implement when:** the design, task plan, traceability, and
  verification package pass lifecycle validation, the security and operations
  review has no unresolved blocking finding, and the project owner explicitly
  approves implementation.
- **Design-first exception:** no
- **Optional artifacts recommended:** none currently; create
  `canonical-context.md` only if a concrete authority conflict is found.
- **Downstream review needed:** implementation-slice security and architecture
  review at T004, then full expert review before closure.
- **Package sequencing:** Spec 007 is closed and its durable release-readiness
  gates remain applicable independently. Spec 009 is the only active package;
  it must produce new implementation and validation evidence rather than reuse
  Spec 007 evidence as proof.

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
6. The tray lifecycle SHALL support the declared Linux reference environment
   first and retain explicit capability boundaries for other Linux desktop
   environments and Windows.
7. Shared tray lifecycle, status, action, and run-state logic SHALL be
   independent of Linux, GTK, systemd, Unix sockets, Windows services, and
   Windows notification-area APIs; platform behavior SHALL be supplied through
   replaceable adapters.
8. Initial live acceptance SHALL target Linux Mint Cinnamon/X11. The design
   SHALL define capability-based adapter contracts for common Linux desktop
   environments and supported Windows versions, with unsupported capabilities
   reported explicitly instead of inferred from operating-system name alone.

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
8. Only members of the configured system operator group SHALL be allowed to
   inspect system-backup status or request an on-demand system backup. Group
   configuration and membership SHALL be controlled outside the unprivileged
   client and SHALL require system authority to change.
9. The local contract SHALL bind authorization to operating-system peer
   identity and current group membership. It SHALL reject self-asserted
   identities, unauthorized local users, stale authorization, arbitrary
   executable paths, and arguments outside the allowlisted action schema
   without disclosing protected status or selection metadata.
10. System-scope run history and diagnostic-log views SHALL require current
    membership in the configured system operator group. Responses SHALL contain
    only allowlisted, secret-free fields and SHALL NOT disclose raw environment
    values, repository credentials, protected source paths, or unrestricted
    journal content.
11. User-local application logs SHALL remain distinct from system-scope run and
    diagnostic records. An authorization failure SHALL NOT disclose whether a
    protected run, repository, selection, schedule, or diagnostic record exists.

### Requirement 5: Automatic retention as an independent operation

**User Story:** As an operator, I want TimeLocker to apply my retention policy
automatically after a successful scheduled backup while remaining independently
runnable, so that snapshot cleanup is consistent without making backup success
a general prerequisite for retention.

**Priority:** must-have

#### Acceptance Criteria

1. THE production policy SHALL explicitly keep 5 daily, 4 weekly, 12 monthly,
   and 3 yearly snapshots, SHALL explicitly group by `host,paths`, and SHALL
   leave prune disabled.
2. BEFORE first enablement or any policy change, THE SYSTEM SHALL support a dry
   run using the same repository identity, credential source, snapshot filters,
   explicit grouping, policy values, and prune setting as the eventual
   mutation, and SHALL record those inputs as one reviewable policy fingerprint.
3. Retention SHALL use a separately identifiable operation and service from
   backup. It SHALL support three trigger modes without merging backup and
   retention results: successful scheduled-backup completion, an independent
   schedule, and an explicit operator request.
4. Retention SHALL NOT run while a backup or another repository mutation is
   active, and a skipped conflict SHALL be visible as a run result rather than
   silently lost.
5. A retention result SHALL NOT rewrite a backup result, and backup success or
   failure SHALL NOT change the eligibility of an independently approved
   retention run.
6. Each retention attempt SHALL produce a durable run record visible through
   the CLI and tray, including whether it was a dry run and how many snapshots
   were selected or removed, together with the applied policy fingerprint.
7. Disabling automatic retention SHALL be reversible without disabling
   backups, and rollback guidance SHALL preserve the manual forget command.
8. First enablement and every change to the repository, credential source,
   snapshot filters, grouping, retention values, or prune setting SHALL require
   explicit operator approval of a successful dry run with the identical policy
   fingerprint. A dry run alone SHALL NOT enable mutation.
9. Retention eligibility SHALL be independent of backup success, failure,
   absence, age, or freshness. Retention MAY run at any scheduled or explicitly
   requested time when its policy is approved and no conflicting repository
   mutation is active.
10. In the production automation profile, each successful scheduled backup
    SHALL trigger at most one retention attempt immediately after the backup has
    recorded terminal success and released its repository lock. A failed,
    cancelled, skipped, or interrupted backup SHALL NOT emit that success
    trigger; this SHALL NOT prevent a later independent or explicit retention
    run.
11. A backup-triggered retention attempt SHALL acquire the normal repository
    mutation lock and SHALL create its own run record. Its success, failure, or
    conflict result SHALL NOT alter the preceding backup's terminal result.

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
5. Shared protocol and domain components SHALL support Linux and Windows
   adapters without changing their public schema or authorization semantics.
   Platform support claims SHALL identify the validated adapter capabilities
   and environments rather than assuming all environments behave alike.
6. On startup after a process crash or system restart, THE SYSTEM SHALL
   reconcile every non-terminal run and lock against its owning process or
   lease, mark abandoned attempts with a durable `interrupted` result, and make
   stale locks safely recoverable without creating duplicate terminal records.

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
  explicit tuple `(group-by=host,paths, 5, 4, 12, 3, prune=false)` and a matching
  approved dry-run fingerprint; no CLI or Restic default may change it.
- **CP-006:** A denied elevation or incompatible client/backend contract causes
  no privileged mutation.
- **CP-007:** A caller can inspect system-backup status or request a system
  backup if and only if its operating-system peer identity is currently a
  member of the configured system operator group.
- **CP-008:** Every non-terminal run left by a dead process or expired lease is
  reconciled exactly once to an interrupted terminal record before its lock can
  be reused.
- **CP-009:** Replacing a Linux or Windows platform adapter cannot change the
  shared status, action, authorization, locking, or run-record contracts.
- **CP-010:** One successful scheduled backup emits at most one
  backup-success retention trigger after terminal success and lock release;
  every resulting retention attempt remains independently locked and recorded.
- **CP-011:** A system-scope run or diagnostic record is returned if and only
  if the server derives the caller's operating-system identity and confirms
  current membership in the configured system operator group; returned fields
  are a strict subset of the allowlisted response schema.

## Technical Context

- **Language/Version:** Python 3.12-3.13
- **Primary Dependencies:** Typer, Restic, existing monitoring and scheduling
  services, platform adapters such as systemd/desktop integration on Linux and
  native service/session integration on Windows, and optional tray dependencies
- **Target Platform:** Linux Mint Cinnamon/X11 for initial live acceptance;
  architecture for common Linux desktop environments and supported Windows
  versions through capability-based adapters; preserve an explicit macOS
  compatibility boundary
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
  explicit `host,paths`, 5/4/12/3, no-prune policy and matching approval
  fingerprint, and appear in both CLI and tray status.
- **SC-007:** An authorized system-operator-group member can inspect status and
  request one allowlisted backup, while an otherwise valid local user receives
  no protected status, selection metadata, or control capability.
- **SC-008:** Killing a backup or retention process and restarting the backend
  produces one interrupted terminal record, releases or recovers its stale lock,
  and lets the tray reconnect without showing the attempt as still running.
- **SC-009:** Shared contract tests pass unchanged against the Linux adapter and
  a Windows adapter test double, while Linux Mint Cinnamon/X11 live acceptance
  proves the first supported desktop environment.
- **SC-010:** One controlled successful scheduled backup produces a distinct
  subsequent retention run, while controlled failed and interrupted backups do
  not emit the success trigger and a later explicit retention run remains
  possible.
- **SC-011:** An authorized operator can view system backup and retention runs
  through the CLI and tray, while an unauthorized local user and a user removed
  from the operator group receive the same metadata-free denial and cannot read
  protected system log files or raw journal records through TimeLocker.

## Resolved Design Questions

- System reads and allowlisted actions use the privileged local backend;
  administrator maintenance continues through the platform elevation adapter.
- Linux uses a systemd-managed Unix-domain socket with kernel peer credentials;
  shared contracts retain a Windows named-pipe adapter boundary.
- The tray reads structured state exclusively through the backend contract.
- Successful scheduled backups trigger retention after terminal success and
  lock release. The independent schedule remains supported but initially
  disabled until an operator approves its cadence.
- A new atomic run store under root-owned system state becomes authoritative
  for system operations; legacy user-local logs remain a separate local scope.

## Routed Future Work

- [GitHub issue #70](https://github.com/Auriora/TimeLocker/issues/70) tracks
  partitioned user views and user-scoped selection/restore management. A
  signed-in user may define selection sets only within their access domain,
  inspect only the corresponding partition of snapshot content and metadata,
  and restore only to authorized destinations without learning about or
  controlling the system selection set. That future work must define selection
  ownership, partition identity, snapshot filtering, restore destinations,
  symlink, hard-link, ACL, ownership, and special-file behavior, privilege
  boundaries, and defenses against using the system service to read or write
  inaccessible paths.

## Related Artifacts

- Canonical context: `canonical-context.md`
- Change impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Traceability: `traceability.md`
- Verification: `verification.md`
