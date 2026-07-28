---
title: Event-driven tray status tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-27
---

# Tasks

**Input:** All artifacts in `docs/specs/010-event-driven-tray-status/`

**Prerequisites:** Approved requirements and design, complete traceability,
implementation approval, and preserved unrelated worktree changes.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004
T004 -> T005 -> T006 -> T007
T007 -> T008 -> T009
T009 -> T010 -> T011 -> T012 -> T013
```

## Phase 1: Status And Event Contracts

- [x] T001 Add typed status snapshot and event contracts.
  - Depends on: none
  - Requirements: Requirement 1, Requirement 2, Requirement 3, Requirement 7
  - Properties: CP-001, CP-002, CP-004
  - Files: `src/TimeLocker/system_control/models.py`,
    `src/TimeLocker/system_control/types.py`,
    `src/TimeLocker/system_control/protocol.py`,
    `src/TimeLocker/system_control/interfaces.py`, focused tests
  - Acceptance: Allowlisted snapshot, revision, and event models validate exact
    schemas; last-success selection uses maximum successful `completed_at`;
    protocol compatibility and safe failures are tested.
  - Evidence: Implemented immutable allowlisted StatusRevision, StatusEvent, and StatusSnapshot contracts; added platform-neutral provider, broker, transport, and client protocols; and added permutation/table-driven CP-001 and CP-002 coverage. Validation on 2026-07-27: `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control/test_status_contracts.py tests/TimeLocker/system_control/test_models.py tests/TimeLocker/system_control/test_protocol.py tests/TimeLocker/system_control/test_interfaces.py` -> 75 passed; `PYENV_VERSION=3.12.4 ruff check src/TimeLocker/system_control/models.py src/TimeLocker/system_control/types.py src/TimeLocker/system_control/interfaces.py src/TimeLocker/system_control/__init__.py tests/TimeLocker/system_control/test_status_contracts.py` -> passed; `git diff --check` -> passed.
  - Status: T001 complete; T002 is now dependency-ready. No backend action, deployment, or live host state was changed.
  - Evidence mode: implementation
  - [x] T001.1 Add failing model and protocol tests.
  - Evidence: Added focused model and compatibility tests in `tests/TimeLocker/system_control/test_status_contracts.py`; the final focused run passed as part of the 75-test T001 suite.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T001.2 Implement exact wire models and version handling.
  - Evidence: Implemented exact immutable `StatusRevision`, `StatusEvent`, and `StatusSnapshot` wire models with strict version, enum, UUID, integer, UTC timestamp, nested run, and unknown-field validation. Existing control protocol behavior remained compatible.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T001.3 Add generated or table-driven CP-001 and CP-002 coverage.

  - Evidence: Added permutation coverage proving last-success selection is order-independent and equals the maximum successful backup `completed_at`, plus strict same-session revision-ordering cases for duplicate, older, newer, and changed-session revisions.
  - Status: Complete.
  - Evidence mode: implementation
- [x] T002 Add the authorized `status.snapshot` control action.
  - Depends on: T001
  - Requirements: Requirement 2, Requirement 3, Requirement 4
  - Properties: CP-001, CP-004, CP-005
  - Files: `src/TimeLocker/system_control/action_policy.py`,
    `src/TimeLocker/system_control/backend_entry.py`,
    `src/TimeLocker/system_control/client.py`,
    `src/TimeLocker/system_control/storage.py`, focused tests
  - Acceptance: Authorized clients receive one coherent safe snapshot;
    unauthorized clients receive only a safe denial; explicit existing
    control actions remain compatible.
  - Evidence: Added the read-only `status.snapshot` SystemAction and public system-read classification; strict response projection; `UnixSocketSystemControlClient.get_status_snapshot()`; an internal locked full-history store read; and a backend snapshot handler with one backend-session revision, active-operation count, latest safe attempts, last successful backup completion, and schedule projection. Authorized/denied, redaction, client, protocol, storage, dispatcher, backend, interface, and T001 contract checks passed: `PYENV_VERSION=3.12.6 python -m pytest --no-cov ...` -> 108 passed. Scoped Ruff and `git diff --check` passed. No mutation route, event transport, deployment, or live host state changed.

  - Status: T002 complete; T003 is dependency-ready.
  - Evidence mode: implementation
- [x] T003 Implement the bounded status event broker and change sources.
  - Depends on: T002
  - Requirements: Requirement 1, Requirement 2, Requirement 4
  - Properties: CP-002, CP-004, CP-005
  - Files: new focused module under `src/TimeLocker/system_control/`, run and
    schedule mutation seams, focused tests
  - Acceptance: Broker revisions are monotonic per session, changes coalesce,
    subscriber state is bounded, and watcher uncertainty forces
    resynchronization.
  - Evidence: Implemented `status_events.py` with bounded session broker/subscriptions, monotonic revisions, one-event coalescing, subscriber bounds, synchronized snapshot/publication coordinator, schedule and durable-run change seams, and injectable watcher uncertainty-to-resync handling. Integrated the broker/coordinator and post-persistence run callbacks into Linux backend composition while isolating event failures from mutations. Validation: focused T001-T003/status/storage/backend/protocol/client/dispatcher suite -> 96 passed; scoped Ruff -> passed; `git diff --check` -> passed. No transport, deployment, or live host operations were performed.
  - Status: T003 complete; Phase 1 checkpoint T004 is dependency-ready.
  - Evidence mode: implementation
  - [x] T003.1 Implement session revision and coalescing behavior.
  - Evidence: Implemented `BoundedStatusEventBroker` and `BoundedStatusSubscription` with random session identity, monotonic bounded sequence, initial snapshot-required event, one-slot per-subscriber coalescing, subscriber limits, and close/unregister behavior. Focused broker and race tests passed.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T003.2 Publish after TimeLocker-owned durable state changes.
  - Evidence: Integrated a shared `StatusChangeCoordinator` into Linux backend composition; durable run create/transition operations publish after atomic persistence, schedule changes have an explicit publication seam, and callback failures are isolated from completed mutations. Snapshot building shares the coordinator boundary.
  - Status: Complete; concrete schedule change call sites do not yet exist in the protected backend and later watcher/transport tasks consume the seam.
  - Evidence mode: implementation
  - [x] T003.3 Add injectable protected-state watcher and overflow handling.

  - Evidence: Added the injectable `ProtectedStateWatcher`/`ProtectedStateChangeMonitor` boundary and sanitized `StatusWatchSignal`; uncertain or unknown observations publish a coalesced `resync_required` event. Focused uncertainty test passed.
  - Status: Complete; platform watcher implementation is consumed by the Linux transport/integration slice.
  - Evidence mode: implementation
- [x] T004 Checkpoint - contract, security, and broker validation.
  - Depends on: T003
  - Requirements: Requirement 1-Requirement 4
  - Acceptance: Focused tests pass, protocol and privacy review has no blocking
    findings, and `verification.md` contains concrete phase evidence before
    transport work begins.
  - Validation: Focused system-control model, protocol, storage, dispatcher,
    and broker tests.
  - Evidence: Completed the bounded Phase 1 security/protocol checkpoint using `$review-timelocker` across project/operator, Python/IPC architecture, security/privacy, reliability/testing, operations/portability, and documentation lifecycle lenses; Restic data semantics were not materially changed. The review found one actionable watcher-failure resync gap, which was fixed and regression-tested. No blocking findings remain in T001-T003 scope. Validation: `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` -> 208 passed; scoped Ruff, `python -m compileall -q src/TimeLocker/system_control`, and `git diff --check` -> passed. Agent Workbench static diagnostics had no actionable findings but no Python diagnostics provider was available.

  - Status: Phase 1 complete; T005 Linux event transport is dependency-ready. Review excluded T005+ transport, deployment, live operations, and durable promotion.
  - Evidence mode: implementation
## Phase 2: Transport And Tray Client

- [x] T005 Implement authenticated Linux event transport and subscription
  client.
  - Depends on: T004
  - Requirements: Requirement 1, Requirement 2, Requirement 4, Requirement 7
  - Properties: CP-002, CP-003, CP-004, CP-005
  - Files: `src/TimeLocker/system_control/linux_adapter.py`,
    `src/TimeLocker/system_control/backend_entry.py`,
    `src/TimeLocker/system_control/tray_client.py`, new event client module,
    focused tests
  - Acceptance: The dedicated socket does not block control requests; peer
    identity and membership are rechecked; slow clients, oversized frames,
    disconnect, heartbeat, restart, and revision gaps are bounded and tested.
  - Evidence: Implemented the separate authenticated Linux event channel, bounded concurrent subscriber transport, systemd listener adoption, reconnecting bounded-frame event client, and event-driven tray snapshot coordinator. Negative controls cover peer-derived authorization, per-event/heartbeat membership rechecks, revocation, safe denial, slow senders, frame overflow, disconnect/reconnect, backend-session restart, revision gaps/duplicates, stale snapshots, initial snapshot recovery, and event/control independence. Validation on 2026-07-27: focused T005 suite -> 13 passed; `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` -> 224 passed; scoped Ruff, compileall, and `git diff --check` passed. Agent Workbench reported no actionable diagnostics but no Python diagnostics provider was available. No deployment or live host mutation was performed.
  - Status: T005 complete; T006 tray presentation is dependency-ready. Deployment assets and live host changes remain gated to later tasks.
  - Evidence mode: implementation
  - [x] T005.1 Add transport and security negative-control tests.
  - Evidence: Added eight negative-control cases in `tests/TimeLocker/system_control/test_status_event_transport.py`; the focused T005 run passed 13 tests, including authorization, revocation, denial, heartbeat, slow sender, systemd adoption, overflow/reconnect, and denial parsing.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T005.2 Implement systemd listener adoption and bounded subscribers.
  - Evidence: Implemented `LinuxStatusEventTransport` in `src/TimeLocker/system_control/linux_adapter.py` and backend isolation in `backend_entry.py`; systemd adoption, bounded sender, revocation, heartbeat, and event/control independence cases passed in the 13-test focused T005 run.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T005.3 Implement tray reconnect, coalescing, and fresh-snapshot flow.
  - Evidence: Added `event_client.py` and `TrayStatusSubscriptionClient` in `tray_client.py`; four cases in `test_tray_status_subscription.py` passed for initial snapshot, gaps/restart, duplicate/older revisions, stale snapshots, denied state, and heartbeat-only recovery while unsynchronized.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T005.4 Prove CP-003 and CP-004 with revocation/restart tests.

  - Evidence: CP-003/CP-004 controls in `test_status_event_transport.py`, `test_tray_status_subscription.py`, and `test_backend_entry.py` passed in the 13-test focused T005 run: revocation before delivery, safe denial, overflow/disconnect reconnect, new backend session, revision gap, stale snapshot rejection, and event/control independence.
  - Status: Complete.
  - Evidence mode: implementation
- [x] T006 Correct and simplify tray presentation.
  - Depends on: T005
  - Requirements: Requirement 3, Requirement 5, Requirement 6
  - Properties: CP-001, CP-006
  - Files: `src/TimeLocker/system_control/tray_entry.py`,
    `src/TimeLocker/system_control/tray_client.py`,
    `src/TimeLocker/monitoring/system_tray_integration.py`, focused tests
  - Acceptance: Menu rows show current safe status; last backup means
    successful completion; `Open TimeLocker` and non-functional `View Status`
    are absent; healthy serve mode is silent; explicit one-shot status remains.
  - Worktree caution: Reconcile and retain the pre-spec menu-removal changes.
  - Evidence: Implemented coherent snapshot-to-tray projection, local-time last-success semantics, seven non-actionable status rows, cross-platform menu removal of `Open TimeLocker`/`View Status`, event-driven UI updates, and silent healthy serve behavior while retaining bounded explicit one-shot output. Validation on 2026-07-27: `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` -> 228 passed; focused monitoring tray suite -> 9 passed; scoped Ruff, compileall, and `git diff --check` passed. No deployment or live host state changed.
  - Status: T006 complete; Phase 2 integration checkpoint T007 is dependency-ready.
  - Evidence mode: implementation
  - [x] T006.1 Reconcile the existing `Open TimeLocker` removal.
  - Evidence: Reconciled and retained the pre-spec menu removal in `system_tray_integration.py`; focused menu tests confirm neither `Open TimeLocker` nor `View Status` is created.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T006.2 Replace `View Status` with non-actionable status rows.
  - Evidence: Replaced actionable status entries with seven disabled backend/activity/backup/retention/schedule rows in `system_tray_integration.py`; Linux dynamic-row tests passed and macOS/Windows adapters use the same platform-neutral labels.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T006.3 Project `last_successful_backup_completed_at` in local time.
  - Evidence: `TrayControlClient.project_snapshot()` now projects `last_successful_backup_completed_at`, and platform menu labels convert it with `astimezone()` including the timezone; tests prove a newer failed backup does not replace the successful completion and no success renders `Never`.
  - Status: Complete.
  - Evidence mode: implementation
  - [x] T006.4 Remove periodic stdout/stderr success output and test CP-006.

  - Evidence: `tray_entry.py` now consumes a coalesced event-update queue without periodic `refresh_status()` calls or successful stdout/stderr writes. `test_healthy_serve_is_silent_and_applies_event_snapshot` passed while the explicit one-shot status rendering test remained green.
  - Status: Complete.
  - Evidence mode: implementation
- [x] T007 Checkpoint - event-driven tray integration.
  - Depends on: T006
  - Requirements: Requirement 1-Requirement 6
  - Acceptance: Integration tests show initial snapshot, event update,
    coalescing, reconnection, honest last-success semantics, live menu update,
    and no steady-state status polling or output.
  - Validation: Focused tray, client, transport, monitoring, security, and
    integration tests.
  - Evidence: Completed the Phase 2 integration checkpoint. The 58-test focused transport/broker/snapshot/subscription/tray/menu suite passed initial snapshot, invalidation update, one-slot coalescing, oversized-frame disconnect/reconnect, backend-session restart, duplicate/older/gap handling, per-delivery revocation, honest last-success/`Never` semantics, dynamic disabled menu rows, silent serve, explicit one-shot output, and an assertion that healthy serve never calls the legacy polling method. Scoped Ruff, compileall, and `git diff --check` passed; the broader system-control suite passed 228 tests during T006.

  - Status: Phase 2 complete; T008 Windows-portable event contracts are dependency-ready. No deployment or live host state changed.
  - Evidence mode: validation
## Phase 3: Portability And Deployment

- [x] T008 Add Windows-portable event transport contracts and tests.
  - Depends on: T007
  - Requirements: Requirement 2, Requirement 4, Requirement 7
  - Properties: CP-002-CP-005
  - Files: `src/TimeLocker/system_control/windows_adapter.py`, platform tests,
    protocol tests
  - Acceptance: Named-pipe interfaces derive peer identity from token
    providers, enforce the same bounded event contract, and pass injected
    contract/security tests without claiming a live Windows service.
  - Evidence: Added injectable `NamedPipeEventConnection`/`NamedPipeEventAcceptor` contracts and `WindowsNamedPipeStatusEventTransport` in `windows_adapter.py`. The adapter derives identity only from the injected token provider, rechecks current group membership before every event/heartbeat, emits only a safe denial, shares the bounded broker, bounds frames/heartbeat/send timeout, closes slow clients, and releases subscription capacity. Four new Windows event tests plus existing platform-neutral contracts passed; `PYENV_VERSION=3.12.6 python -m pytest --no-cov tests/TimeLocker/system_control` -> 232 passed. Scoped Ruff, compileall, and `git diff --check` passed. This is an injected contract tested on Linux and does not claim a live Windows service or deployment.

  - Status: T008 complete; T009 protected deployment/compatibility assets are dependency-ready.
  - Evidence mode: implementation
- [x] T009 Add protected deployment, compatibility, and rollback assets.
  - Depends on: T008
  - Requirements: Requirement 4, Requirement 7
  - Files: `src/TimeLocker/system_control/assets/`,
    `src/TimeLocker/system_control/deployment.py`,
    release manifest/launcher code, deployment and package tests
  - Acceptance: Event socket ownership/mode, release probes, packaging, atomic
    selection, rollback, and existing backup/retention timers are verified.
  - Evidence: Added the root-owned/group-accessible `timelocker-status-events.socket` package asset with mode 0660 and named `status-events` descriptor; the control socket is named `control`. Backend activation resolves descriptors from validated `LISTEN_PID`/`LISTEN_FDS`/`LISTEN_FDNAMES` rather than positional assumptions. Schema-2 release metadata binds control and event protocol versions while schema 1 remains readable for legacy rollback without claiming event compatibility. Structured activation probes require compatible CLI/backend/tray, explicit control status, event channel, and active+enabled backup/retention timers before atomic selection; rollback requires coherent artifacts, control status, and both timer states while permitting the added event socket to remain inert. Focused deployment/release/backend/Linux asset suite: 52 passed. Full system-control suite: 246 passed. Scoped Ruff and `git diff --check` passed. `systemd-analyze verify` was environment-limited by unrelated host permissions and absent protected installed launcher executability, so clean installed-unit evidence remains T011. The original unit required both sockets; T011 remediation makes the event dependency non-fatal while retaining named descriptor validation. No protected host mutation occurred.

  - Status: T009 complete; T010 local package build and installed-artifact smoke are dependency-ready. Live deployment remains gated at T011.
  - Evidence mode: validation
- [x] T010 Checkpoint - package and deployment readiness.
  - Depends on: T009
  - Requirements: Requirement 5, Requirement 7
  - Acceptance: Linux packages deterministic TimeLocker-logo variants for
    running, success, warning or never-run, and failure; snapshot state selects
    them honestly; wheel/sdist validation and installed-artifact smoke pass;
    live deployment commands and rollback are reviewed; no protected host
    mutation has occurred without explicit approval.
  - Evidence: Added a deterministic Pillow build script and five packaged
    TimeLocker-logo variants with non-colour-only glyphs for idle/connecting,
    running, success, warning/never-run, and failed/interrupted. Linux
    AppIndicator now selects the projected variant with safe base-logo/theme
    fallbacks. Snapshot projection treats no backup attempt as warning even
    after successful retention, preserves latest failed/interrupted as error,
    and keeps the last-successful timestamp independent. Deployment targets
    and installed-artifact smoke cover every new asset. Validation on
    2026-07-27: focused UX/deployment suite -> 53 passed; system-control,
    monitoring, icon, and release-artifact regression suite -> 268 passed;
    scoped Ruff, compileall, and `git diff --check` -> passed. Isolated wheel
    and sdist validation passed with 27 package-data files; both clean-install
    smoke contracts passed. SHA-256: wheel
    `ceb610a5eafeedc1d0b13f0626d0ac9a74f33a4cb46735778c37fc4712b5bb7b`;
    sdist
    `ac9371a6e3087dc515dc5cd0c871687dd7cd23e7ce3468cc2d7d3b09c65bb7e0`.
    Visual inspection confirmed the base logo remains recognizable and each
    status uses a distinct shape/glyph. No protected host mutation occurred.

  - Status: T010 complete; T011 remains separately approval-gated.
  - Evidence mode: implementation
## Phase 4: Acceptance, Review, Promotion, And Closure

- [~] T011 Perform approved Linux Mint acceptance.
  - Depends on: T010
  - Requirements: Requirement 1-Requirement 7
  - Properties: CP-001-CP-006
  - Approval: Explicit protected deployment and any live backup/retention
    execution approval required.
  - Acceptance: Authorized and denied subscription, event latency, last-success
    semantics, 90-second idle silence, backend restart, tray restart, action
    independence, timer health, external-worker invalidation, missed-backup
    health, the exact three-row menu, and rollback are evidenced from the
    installed artifact.
  - Evidence: User approved remediation of T011 review findings. Implementation
    maps OS socket permission denial to the safe denied state, reports other
    transport failures as unavailable with bounded reconnect, accepts
    control-only systemd activation, and makes the event socket a weak service
    dependency. A repository-owned redacted-evidence validator separates
    ordinary mutation-to-presentation latency from graceful shutdown and restart
    convergence. After a temporary deployment script failed because its `0660`
    probe was executed as an identity that could not read it, the rollout path
    was replaced with the repository-owned `scripts/deploy_t011_linux.py`
    harness. It snapshots exact inputs into private root-owned evidence, runs
    inline authorized and denied identity probes before protected mutation,
    rejects packaged assets outside the staged release, uses a locked
    expected-current selector compare-and-swap, and restores the selector,
    service unit, sockets, service, and timer gates on failure or interruption.
    Focused harness, selector, deployment, and evidence validation passed 46
    tests; the complete system-control plus harness/evidence regression passed
    272 tests. Scoped Ruff, compileall, and patch integrity passed. A fresh wheel
    and sdist passed artifact validation with 27 package-data files; the wheel
    passed installed-artifact smoke and explicit installed selector-contract
    checks. Wheel SHA-256:
    `5603dd6c4aae461f5e6e673eea97b2d2b2972e843b6d9a32f8f3d8347e1c3dde`;
    sdist SHA-256:
    `fc0f4bda037a7c41128a8834129a7be9c20040d0efd8580dab05ff0599427748`.
    The first commit-bound harness deployment failed closed during staged pip
    installation because the private evidence copy renamed the valid wheel to
    `candidate.whl`, which pip rejects before inspecting the artifact. Recovery
    removed the inert candidate; the prior selector, unit, sockets, service,
    and timers remained unchanged. The harness now validates the supplied wheel
    basename, preserves it in private evidence, and rejects an invalid basename
    before creating host state. Eleven focused harness tests, scoped Ruff,
    compileall, patch integrity, and an exact `/usr/bin/python3` staging
    rehearsal with the release wheel passed. Live redeployment and acceptance
    remained separately approval-gated. The subsequent commit-bound deployment
    of `a67c83ac09ac29b94a3ed481ee536b3380db3337` succeeded on Linux Mint:
    preflight identity checks passed, no backup or retention was triggered, the
    selector retained `d540b453864fce9b1c96a85ad9ecf604b98b7f57` as the
    previous release, the control service, sockets, backup timer, and retention
    timer remained healthy, and installed CLI/tray status probes passed. The
    absence of a supported general deployment entrypoint is routed to
    [Spec 011](../011-protected-system-deployment/README.md). A subsequent
    startup correction adds an explicit deterministic connecting badge,
    processes the desktop event loop before starting the subscription worker,
    and lazily loads unrelated package and system-control exports. Focused tray,
    asset, deployment, and artifact tests passed 42 cases; the broader
    system-control, tray-monitoring, and backup compatibility regression passed
    415 tests. Scoped Ruff, compileall, patch integrity, and public lazy-export
    compatibility checks passed. Direct source startup measurements were
    approximately 0.11 seconds for the launcher import and 0.56 seconds for the
    full tray entry import. A fresh wheel and sdist passed release validation
    with 28 package-data files, and the wheel passed clean installed-artifact
    smoke. Wheel SHA-256:
    `d9fb99bbe856c7659304701ab8b12d5dd8d97fc194f5b8ce5825d33a559609c8`;
    sdist SHA-256:
    `bb5df2b2450db07335ccbb848f03e01b010ed568d6609f29cdd3b24f827ffeea`.
    No protected host mutation occurred. The first protocol-2 deployment of
    commit `2e1b565c823dd9a2714e43ed976338d45a9cbee5` failed closed during
    staged backend preflight because the repository deployer still compared
    the candidate's correct `2:1` protocol report to a stale hard-coded `1:1`
    expectation. Activation did not begin and the candidate release was
    removed. The deployer now derives the expected signature from the staged,
    already-validated schema-2 manifest and records the probe output in private
    evidence. A regression proves a stale `1:1` candidate fails before
    activation; the exact committed wheel independently reported `2:1`.
    Twelve focused harness tests, a 284-test system-control/artifact regression,
    scoped Ruff, and patch integrity passed before another deployment attempt.
    A further exact preflight rehearsal found that a protocol-2 candidate
    `runs list` cannot query the still-active protocol-1 backend. Before any
    retry, the pre-activation CLI check was narrowed to the candidate's local,
    manifest-bound version; the real system read remains a required
    post-activation check after the candidate backend is coherently selected.
    Simulated transaction ordering proves no protocol-2 system read occurs
    before selection and that the post-activation read still runs.

  - Status: Corrected release activated successfully; the remaining installed
    T011 acceptance checks, including visible connecting-state startup, and
    evidence validation are in progress.
  - [x] T011.1 Reconcile and test backup-health and tray-row contracts.
    - Acceptance: State is health-only; Activity is transient; Last Backup is
      successful completion or Never; exact wire and menu tests fail before the
      implementation change.
    - Evidence: User approved the corrected State/Activity distinction on
      2026-07-28. Requirements, design, traceability, verification, and tests
      now define health-only State, transient Activity, and successful-only
      Last Backup. The strict status snapshot contract includes bounded backup
      schedule health and control protocol version 2; schema-1 release metadata
      and preserved protocol-1 policy declarations remain readable for upgrade
      and rollback without accepting protocol-1 traffic as the new contract.
  - [x] T011.2 Implement external-worker invalidation and backup schedule health.
    - Acceptance: Separate protected run-record writes prompt a snapshot within
      two seconds; systemd timer/service state and durable runs distinguish
      healthy, failed, missed, disabled, and unavailable without fixed polling.
    - Evidence: Added watchdog-backed native filesystem invalidation for
      protected run-record atomic renames, a bounded systemd timer/service
      observer, durable run matching, a 15-minute missed-occurrence grace
      deadline, and a one-shot deadline monitor. Tests cover unavailable,
      disabled, healthy, missed, failed-run matching, late manual backup,
      numeric systemd timestamps, deadline publication, and an external
      `AtomicRecordStore` write. The current host's read-only observer returned
      an enabled/active timer with the expected last and next trigger times.
  - [x] T011.3 Implement and validate the exact three-row tray presentation.
    - Acceptance: All platform adapters show only State, Activity, and Last
      Backup; retention affects Activity only while running and never health.
    - Evidence: Tray projection and all platform menu adapters now expose only
      `State`, `Activity`, and `Last Backup`. Backup failure/miss, schedule
      disabled/unavailable, backend unavailable, access denial, and healthy
      states are separate from connecting, backup-running,
      retention-running, combined-running, and idle activity. Retention
      terminal outcomes do not affect health. A 416-test system-control,
      tray, deployment, artifact, backup, and CLI regression passed; scoped
      Ruff, compileall, patch integrity, wheel/sdist build, and installed-wheel
      smoke passed. No protected host mutation or live backup/retention ran.
- [ ] T012 Run the TimeLocker expert review and address findings.
  - Depends on: T011
  - Requirements: Requirement 1-Requirement 7
  - Review: Use `$review-timelocker` with project stewardship, Restic,
    Python/IPC architecture, security/privacy, reliability/testing,
    operations/portability, and documentation lifecycle perspectives.
  - Acceptance: Blocking findings are fixed; advisory findings are fixed,
    rejected with rationale, or routed to one owned destination.
  - Evidence: Pending.

- [ ] T013 Promote durable documentation, run final validation, and close.
  - Depends on: T012
  - Requirements: Requirement 1-Requirement 7
  - Files: promotion targets in `change-impact.md`, `verification.md`,
    `docs/specs/README.md`, `docs/history/`
  - Acceptance: Configured regression and all required focused/platform/
    security/package checks pass; accepted behavior is promoted; Windows live
    work has one follow-up destination; general protected deployment workflow
    debt is owned by Spec 011; lifecycle evidence, traceability, closure,
    final-spec commit, cleanup, and history indexes are complete.
  - Evidence: Pending.

## Execution Rules

- Do not implement from this file alone. Read the full package and durable
  baseline first.
- Mark only one implementation task `[~]` at a time unless non-conflicting work
  is explicitly approved.
- Preserve unrelated worktree changes and reconcile the existing tray-menu
  correction rather than reverting it.
- Record commands and results under the task and in `verification.md`.
- A focused `--no-cov` run is diagnostic only; the configured final profile
  owns the 50 percent coverage gate.
- Protected deployment, group changes, live backup, live retention, rollback,
  publication, and release selection retain explicit approval gates.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Change Impact: [change-impact.md](./change-impact.md)
- Design: [design.md](./design.md)
- Verification: [verification.md](./verification.md)
