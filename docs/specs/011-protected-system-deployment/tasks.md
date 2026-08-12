---
title: Protected system deployment tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-08-12
---

# Tasks

**Input:** All artifacts in `docs/specs/011-protected-system-deployment/`

## Dependency Graph

`T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007`

## Phase 1: Daemonless Runtime

- [x] T001 Make the protected Linux helper serve one request and exit.
  - Depends on: none
  - Requirements: Requirement 4, Requirement 8, Requirement 9
  - Properties: CP-005, CP-007, CP-008
  - Files: backend entry, Linux transport, systemd assets, focused tests
  - Acceptance: Production socket activation handles one authorized request,
    closes, and exits; no event socket, heartbeat, watcher, or resident monitor
    is required by installed assets.
  - Evidence: `src/TimeLocker/system_control/backend_entry.py`, `linux_adapter.py`, and `assets/timelocker-control.service` use one-request `serve_once`; `python3 -m pytest` focused run passed 295 tests, including `test_run_linux_backend_serves_one_request_and_exits` and unit asset assertions.

- [x] T002 Publish and consume an atomic sanitized status snapshot.
  - Depends on: T001
  - Requirements: Requirement 2, Requirement 7, Requirement 9
  - Properties: CP-004, CP-006, CP-008
  - Files: snapshot store/watcher, backend worker hooks, tray client/entry, tests
  - Acceptance: Root-owned workers write exact group-readable status state;
    reads do not publish changes; the tray performs an initial read and direct
    filesystem observation without a privileged event channel.
  - Evidence: `status_snapshot.py`, `tray_client.py`, and `tray_entry.py` provide atomic 0640 publication, fd-safe reads, startup refresh, and direct filesystem watching; the 295-test focused pytest run includes `test_status_snapshot.py` and tray subscription tests.

- [x] T003 Replace resident deployment assets and migration gates.
  - Depends on: T002
  - Requirements: Requirement 4, Requirement 5, Requirement 9
  - Properties: CP-003, CP-005, CP-008
  - Files: packaged units, asset manifest, activation/rollback checks, tests
  - Acceptance: The status-event socket is absent, service startup is
    socket-only and non-resident, legacy units are stopped/disabled during
    activation, timers and protected state are preserved.
  - Evidence: Release schema 3 and packaged asset tests assert `timelocker-status-events.socket` is absent, legacy units are disabled, only the control socket is enabled, timers are preserved, and `RuntimeDirectoryPreserve=yes`; focused pytest passed 295 tests.

## Phase 2: Supported Deployment Workflow

- [x] T004 Add the supported local-wheel administrator deployment entrypoint.
  - Depends on: T003
  - Requirements: Requirement 1-Requirement 8
  - Properties: CP-001-CP-007
  - Files: deployment engine/entrypoint, packaging metadata, tests
  - Acceptance: Install/upgrade/status/rollback expose stable JSON results;
    validate artifact identity, privately stage once, lock mutation, derive
    manifests, preserve rollback state, and produce redacted evidence.
  - Evidence: `deployment_entry.py`, `timelocker-deploy-launcher`, and the `timelocker-deploy` project entry point cover offline local-wheel install, upgrade, status, and rollback; focused pytest passed 295 tests and artifact smoke executed the installed wheel.

- [x] T005 Run focused, package, full regression, and Linux-safe acceptance.
  - Depends on: T004
  - Requirements: Requirement 1-Requirement 9
  - Properties: CP-001-CP-008
  - Acceptance: Focused tests, full configured regression, Ruff, compile,
    package validation, installed-artifact smoke, lifecycle checks, and a
    non-mutating process-residency probe pass. Protected deployment and the
    90-second live host interval require their separate operational approval.
  - Evidence: `git diff --check`, scoped Ruff, compileall, 295 focused pytest tests, wheel/sdist validation of 28 package-data files, and installed-wheel smoke on Python 3.12.6 passed. Full pytest recorded 3166 passed, 1 skipped, and one unrelated repository-resolver timing failure.

## Phase 3: Review And Closure

- [x] T006 Run the TimeLocker MoE review and address findings.
  - Depends on: T005
  - Requirements: Requirement 1-Requirement 9
  - Acceptance: All seven expert roles are applied; actionable findings are
    fixed, rejected with evidence, or routed once.
  - Evidence: The seven-role review table in `verification.md` records each conclusion and disposition. Remediation is directly covered by `test_t011_linux_deployment.py`, `test_status_snapshot.py`, backend, tray, release-artifact, and deployment tests in the 295-test passing run.

- [x] T007 Promote durable documentation and close Spec 011.
  - Depends on: T006
  - Requirements: Requirement 1-Requirement 9
  - Acceptance: Accepted behavior is promoted, residual Windows/live-host work
    is explicitly routed, lifecycle closure passes, the complete final package
    is committed, and cleanup metadata is resolved.
  - Evidence: Promotion changes are present in `docs/1-requirements/system-operations.md`, architecture, service integration, installation, troubleshooting, tray, version management, and command reference. `lint_spec_package` and `task_state_audit` report zero errors and zero warnings; separate Windows and protected-host acceptance are recorded in `verification.md`.

## Execution Rules

- Do not mutate the protected host, run backup/retention, publish a release, or
  activate a candidate without the separate operational approval.
- Preserve protected configuration, credentials, timers, and run records.
- Record executed checks and review disposition under the owning task.

## Related Artifacts

- Requirements: [requirements.md](./requirements.md)
- Design: [design.md](./design.md)
- Traceability: [traceability.md](./traceability.md)
- Verification: [verification.md](./verification.md)
