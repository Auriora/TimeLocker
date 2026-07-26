---
title: System CLI, independent tray, retention, and control tasks
doc_type: spec
artifact_type: tasks
status: draft
owner: Auriora Team
last_reviewed: 2026-07-26
---

# Tasks

**Input**: `canonical-context.md`, `requirements.md`, `design.md`,
`change-impact.md`, `traceability.md`, and `verification.md`

**Prerequisites**: Requirements and design approved; no implementation starts
until the project owner approves the task plan.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004
T004 -> T005 -> T006
T004 -> T007
T004 -> T008
T006 + T007 + T008 -> T009
T009 -> T010 -> T011 -> T012
```

## Phase 1: Shared contracts and safety foundation

- [x] T001 Define shared protocol, action, policy, run, diagnostic, and client
  models with strict validation.
  - Depends on: none
  - Requirements: Requirement 2 AC4-AC6; Requirement 4 AC1-AC7, AC9-AC11;
    Requirement 5 AC1-AC2, AC5-AC8; Requirement 6 AC5
  - Properties: CP-001, CP-004, CP-005, CP-006, CP-009, CP-011
  - Files: new focused modules under `src/TimeLocker/system_control/`;
    matching tests under `tests/TimeLocker/system_control/`
  - Acceptance: Versioned bounded schemas reject unknown fields, secret-bearing
    inputs, raw arguments, and invalid transitions; response projection returns
    only allowlisted fields.
  - Evidence: T001 complete: 70 focused tests passed with 92.7% branch-aware coverage; compileall and git diff --check passed; focused review-timelocker implementation review found no remaining actionable findings. No transport, store, CLI, or live-host behavior was changed.
  - Evidence mode: validation
  - [x] T001.1 Add failing contract and model tests.
  - Evidence: Added focused contract, model, transition, response-projection, security-boundary, and portability tests under tests/TimeLocker/system_control; final focused run: 70 passed.
  - Evidence mode: validation
  - [x] T001.2 Implement schemas, enums, validation, and response projection.
  - Evidence: Implemented strict frozen enums, request/response envelopes, run/transition/diagnostic/policy/action models, validation helpers, immutable projections, and code-owned safe summaries under src/TimeLocker/system_control.
  - Evidence mode: implementation
  - [x] T001.3 Add Linux and Windows adapter protocol test doubles.

  - Evidence: Added platform-neutral peer identity, membership, transport, handler, and client protocols with Linux UID and Windows SID adapter test doubles; platform tests passed.
  - Evidence mode: validation
- [x] T002 Implement atomic run/diagnostic storage, repository mutation
  locking, and interrupted-run reconciliation.
  - Depends on: T001
  - Requirements: Requirement 4 AC2-AC3, AC5-AC6, AC10-AC11; Requirement 5
    AC4-AC6, AC11; Requirement 6 AC6
  - Properties: CP-003, CP-004, CP-008, CP-010, CP-011
  - Files: `src/TimeLocker/system_control/`, focused storage and recovery tests
  - Acceptance: Records transition atomically to exactly one terminal state;
    concurrent mutations cannot overlap; abandoned runs become interrupted and
    stale locks are reusable without duplicate terminal records.
  - Evidence: Atomic storage, bounded diagnostics, repository mutation leases, and idempotent abandoned-run reconciliation implemented in src/TimeLocker/system_control/storage.py. Focused T002 validation passed 11 tests, including cross-process lease recovery; final Phase 1 validation remains tracked by T004.
  - Status: Complete and dependency-ready for T003.
  - Evidence mode: command
  - [x] T002.1 Add transition, concurrency, corruption, and kill/restart tests.
  - Evidence: Added transition, concurrency, corruption, persistence, bounded-stream, process-exit, and restart-reconciliation tests in tests/TimeLocker/system_control/test_storage.py; focused run passed 11 tests.
  - Evidence mode: command
  - [x] T002.2 Implement atomic record store and bounded diagnostic stream.
  - Evidence: Implemented AtomicRecordStore with strict schema parsing, per-run atomic JSON replacement, fsync of files and directories, process-safe transition locking, bounded immutable diagnostic records, filtering, and mode enforcement.
  - Evidence mode: artifact
  - [x] T002.3 Implement repository lock leases and startup reconciliation.

  - Evidence: Implemented nonblocking flock repository leases with safe run ownership metadata, conflict behavior, process-exit release, stale metadata clearing, and idempotent startup reconciliation of abandoned queued/running records.
  - Evidence mode: artifact
- [x] T003 Implement Linux local transport and current operator-group
  authorization.
  - Depends on: T002
  - Requirements: Requirement 2 AC2-AC6; Requirement 4 AC1, AC4-AC11
  - Properties: CP-001, CP-006, CP-007, CP-011
  - Files: Linux adapter modules, systemd socket/service assets, security tests
  - Acceptance: The server derives peer credentials, revalidates current
    `timelocker-operators` membership for every protected request, rejects stale
    or self-asserted identity, and leaks no protected metadata on denial.
  - Evidence: Linux local transport, kernel peer-credential adapter, fresh NSS operator-group authorization, strict dispatcher/audit/redaction, root-policy loader, and least-privilege staged unit assets implemented. Focused T003 validation passed 15 tests; no units were installed or activated.
  - Status: Complete and dependency-ready for T004; live socket/unit acceptance remains T010.
  - Evidence mode: command
  - [x] T003.1 Add authorized, unauthorized, removed-member, malformed,
    oversized, and version-mismatch tests.
  - Evidence: Added authorized, unauthorized, membership-removal, handler-failure, self-asserted identity, malformed JSON, oversized request, and version mismatch tests in test_dispatcher.py; Linux adapter suite also covers peer parsing and NSS failures.
  - Evidence mode: command
  - [x] T003.2 Implement `SO_PEERCRED`, NSS group resolver, dispatcher, audit,
    and redaction.
  - Evidence: Implemented SO_PEERCRED parsing, per-request primary/supplementary NSS lookup, strict JSON dispatcher, metadata-free denial/error responses, secret-free audit events, and systemd-activated AF_UNIX transport adapter.
  - Evidence mode: artifact
  - [x] T003.3 Add root-owned policy, runtime directory, socket, and service
    templates with least-privilege modes.

  - Evidence: Added packaged policy JSON plus staged socket/service templates with root ownership intent, timelocker-operators 0660 socket access, restrictive umask, AF_UNIX-only address family, filesystem protections, and no GUI/session or credential environment forwarding.
  - Evidence mode: artifact
- [x] T004 Checkpoint - Foundation security and agent-readiness review.
  - Depends on: T003
  - Files: Spec artifacts and Phase 1 source/tests
  - Acceptance: Focused tests pass, Spec Lifecycle Manager reports bounded task
    context and traceability, and every `review-timelocker`
    security/architecture finding has a recorded disposition before public CLI
    or live rollout.
  - Evidence mode: command
  - Evidence: Phase 1 checkpoint passed: 98 focused tests passed at 88.4% coverage; Ruff check/format, compileall, wheel build and 3/3 asset inventory, git diff --check, spec lint, and T002/T003 task audits passed. The review-timelocker panel identified TLR-001 through TLR-005; all were fixed and their dispositions are recorded in verification.md. Agent Workbench diagnostics had no provider for these Python files, so executed checks and direct review are the proof. No host assets were installed or activated.

  - Status: Phase 1 complete. Real socket activation, installed permissions, live NSS, host restart, and Windows implementation remain assigned to later tasks.
## Phase 2: System CLI and authorized visibility

- [x] T005 Implement the root-owned system launcher and centralized action
  classification.
  - Depends on: T004
  - Requirements: Requirement 1 AC1-AC4; Requirement 2 AC1-AC6;
    Requirement 6 AC1-AC3
  - Properties: CP-001, CP-006
  - Files: packaging/install assets, launcher/action-policy modules, tests
  - Acceptance: `timelocker` and `tl` resolve one immutable release; user-local
    actions remain unprivileged; protected actions use the backend; invalid
    release or unknown action fails closed without pyenv/checkout fallback.
  - Evidence: The 22-test launcher/action-policy subset passed inside the 177-test Phase 2 run. `release_launcher.py` and `action_policy.py` enforce exact routing, immutable release resolution, and fail-closed unknown actions; the built wheel inventory contains the staged selector plus both command launcher assets. Ruff and `git diff --check` passed; no host state changed.
  - Status: Phase 2 launcher/classification contract complete; live artifact integration and authorization-agent acceptance remain T009/T010.
  - Evidence mode: validation
  - [x] T005.1 Add launcher resolution, rollback, recursion, and routing tests.
  - Evidence: 22 focused launcher/action-policy tests passed in the Phase 2 integrated test run; coverage includes resolution, switch/rollback, recursion, invalid ownership/modes/symlinks, alias compatibility, protected routing, and unknown-action denial.
  - Status: Verified without changing the live selected release.
  - Evidence mode: validation
  - [x] T005.2 Implement immutable release launcher and action classifier.
  - Evidence: `src/TimeLocker/system_control/release_launcher.py` contains `ImmutableReleaseResolver`, strict selector/manifest validation, recursion protection, and atomic selection/rollback; `src/TimeLocker/system_control/action_policy.py` contains the exact fail-closed registry. The 22-test launcher/action-policy subset and Ruff checks passed.
  - Status: Repository implementation verified; live launcher installation remains T009/T010.
  - Evidence mode: implementation
  - [x] T005.3 Add staged install/rollback assets without changing the live
    selected release.

  - Evidence: The no-isolation wheel build passed and its inventory contains `timelocker-launcher`, `tl-launcher`, and `timelocker-release-select` plus their module entry points. `test_release_entrypoints.py` and `test_release_launcher.py` prove the assets do not use pyenv, a checkout, or `/root` overlay fallback.
  - Status: Assets are staged only; `/opt`, `/usr/local/bin`, systemd, and the host selector were not modified.
  - Evidence mode: validation
- [x] T006 Add structured system run and diagnostic CLI views.
  - Depends on: T005
  - Requirements: Requirement 4 AC1-AC3, AC6, AC8-AC11
  - Properties: CP-004, CP-006, CP-007, CP-011
  - Files: `src/TimeLocker/cli_modules/commands/monitoring.py`, focused system
    client modules, CLI and integration tests
  - Acceptance: `runs list`, `runs show`, and
    `logs view --scope local|system` clearly distinguish local and system data;
    only current operator-group members receive protected structured records.
  - Evidence: Completed structured system run and diagnostic CLI views plus the bounded system-control client. The integrated system-control/CLI/help suite passed 177 tests; scoped system-control coverage is 88.2%. Ruff check and format, compileall, wheel build and asset inventory, and git diff --check passed. Review findings TLR-006 through TLR-009 were fixed. No host state changed.
  - Status: Phase 2 complete. Live socket, installed launcher, current NSS membership, and authorized/denied host acceptance remain T009/T010.
  - Evidence mode: validation
  - [x] T006.1 Add CLI contract, compatibility, denial, and redaction tests.
  - Evidence: Added CLI contract, compatibility, denial, redaction, bounded-filter, scope-validation, and protected-metadata tests. The integrated Phase 2 suite passed 177 tests; denied requests expose only safe result codes and summaries.
  - Status: Verified in the integrated Phase 2 suite; live authorized and denied host acceptance remains T010.
  - Evidence mode: validation
  - [x] T006.2 Implement focused `SystemControlClient` integration.
  - Evidence: `src/TimeLocker/system_control/client.py` provides bounded versioned Unix-socket requests, request-ID correlation, timeouts, strict line framing, safe errors, run list/show, diagnostics, and backup/retention requests. `tests/TimeLocker/system_control/test_client.py` passed within the 177-test Phase 2 run.
  - Status: Repository client boundary verified; real AF_UNIX socket activation remains T009/T010.
  - Evidence mode: validation
  - [x] T006.3 Preserve local log behavior and correct `--config-dir`/scope
    resolution without reading protected files directly.

  - Evidence: `src/TimeLocker/cli_modules/commands/monitoring.py` now provides `runs list`, `runs show`, and `logs view --scope local|system`; local logs resolve from the explicit config directory while system scope requests only backend records. `tests/TimeLocker/cli/test_monitoring_commands.py` passed within the 177-test run, including default/local compatibility, invalid scope/limits, and no direct protected-read cases.
  - Status: No protected system file or journal is read directly by the user CLI.
  - Evidence mode: validation
## Phase 3: Independent tray and retention

- [x] T007 Remove tray ownership from CLI/headless services and add the
  independent tray client.
  - Depends on: T004
  - Requirements: Requirement 3 AC1-AC8; Requirement 4 AC1, AC4-AC9;
    Requirement 6 AC1-AC5
  - Properties: CP-002, CP-006, CP-007, CP-009
  - Files: notification/monitoring services, tray entry point, platform
    adapters, packaging, tray/headless tests
  - Acceptance: CLI, backup, retention, scheduler, and backend paths import no
    tray platform code and emit no tray warning; the user-session tray connects,
    reconnects, displays authorized state, and requests only allowlisted
    actions.
  - Evidence: Removed platform tray ownership and exports from NotificationService/headless monitoring; added standalone timelocker-tray entry point, safe tray IPC projection, schedule status, strict action allowlist, backend absence/denial display, bounded reconnect, and singleton locking. Integrated Phase 3 repository slice passed 190 tests including import-boundary, headless, reconnect, authorization projection, singleton, and monitoring compatibility cases; no host state changed.
  - Status: Repository behavior verified. Installed desktop-session and live IPC acceptance remains T009/T010.
  - Evidence mode: validation
  - [x] T007.1 Add import-boundary, headless, absence, crash, singleton, and
    reconnect tests.
  - Evidence: Added direct import-boundary, headless availability, backend absence/denial, reconnect, strict allowlist, and singleton-lock tests; all passed in the 190-test integrated slice.
  - Evidence mode: validation
  - [x] T007.2 Refactor notification delivery to publish structured state
    without constructing `SystemTrayIntegration`.
  - Evidence: `tests/TimeLocker/system_control/test_tray_process_boundary.py` verifies that `NotificationService`, CLI imports, and the monitoring package do not import or construct the platform tray; the integrated 190-test slice passed.
  - Evidence mode: code
  - [x] T007.3 Add standalone tray entry point and Linux Mint Cinnamon/X11
    adapter.

  - Evidence: `pyproject.toml` packages the `timelocker-tray` entry point; wheel inventory confirmed that entry point plus `tray_entry.py` and `tray_client.py`, and tray/process tests passed. Live desktop installation remains T009/T010.
  - Evidence mode: code
- [x] T008 Implement approved retention execution and all three trigger modes.
  - Depends on: T004
  - Requirements: Requirement 5 AC1-AC11; Requirement 6 AC1-AC3, AC6
  - Properties: CP-003, CP-004, CP-005, CP-008, CP-010
  - Files: retention policy/executor/trigger modules, scheduling integration,
    unit/integration tests
  - Acceptance: Dry-run approval fingerprints the complete policy; backup
    success, independent schedule, and explicit request create separate locked
    retention runs; failure or conflict never changes the backup result.
  - Evidence: Implemented approved retention execution and all three trigger modes in the repository slice. Evidence: `src/TimeLocker/system_control/retention.py` adds exact retention-plan fingerprinting, approval-gated mutation, durable trigger claims, explicit protected request handling, and independently gated scheduling. Focused validation passed with `python3 -m pytest tests/TimeLocker/system_control/test_retention.py tests/TimeLocker/system_control/test_tray_client.py tests/TimeLocker/system_control/test_tray_process_boundary.py tests/TimeLocker/monitoring/test_system_tray_integration.py tests/TimeLocker/system_control/test_client.py --cov-reset --cov=src/TimeLocker/system_control --cov-fail-under=50` (32 passed, 58.7% coverage). `git diff --check` passed. No host state changed.
  - Status: Repository implementation complete; live asset integration and host acceptance remain T009-T010.
  - Evidence mode: validation
  - [x] T008.1 Add policy fingerprint, approval, conflict, idempotency, and
    failure-isolation tests.
  - Evidence: Added nine focused tests covering complete fingerprint sensitivity, dry-run non-approval, exact approval, lock conflict, safe failure, durable idempotency, non-success rejection, independent schedule configuration, and protected request projection. The system-control suite passed 149 tests at 83.09% branch-aware coverage.
  - Evidence mode: validation
  - [x] T008.2 Implement retention executor and protected explicit request.
  - Evidence: `src/TimeLocker/system_control/retention.py` implements canonical fingerprinting, separate durable runs, shared repository locking, exact mutation approval, dry-run behavior, safe adapter projection, and the protected request handler; the nine retention tests passed.
  - Evidence mode: code
  - [x] T008.3 Implement post-backup success trigger after terminal record and
    lock release.
  - Evidence: `test_success_trigger_is_durable_and_idempotent_across_restart` and `test_success_trigger_rejects_non_successful_backup` passed, proving durable at-most-once claiming and rejection of non-success terminal records.
  - Evidence mode: validation
  - [x] T008.4 Implement independently configurable schedule, disabled in the
    initial production profile.
  - Evidence: `test_independent_schedule_is_disabled_by_default_and_configurable` passed; the coordinator defaults the independent trigger off and creates a separate scheduled retention run only when enabled. Initial production activation remains T009/T010.
  - Evidence mode: validation

## Phase 4: Installation, portability, and live acceptance

- [x] T009 Integrate release assets, platform adapters, upgrade, and rollback.
  - Depends on: T006, T007, T008
  - Requirements: Requirement 1; Requirement 2; Requirement 3 AC6-AC8;
    Requirement 6 AC1-AC6
  - Properties: CP-001, CP-006, CP-008, CP-009
  - Files: build/install scripts, systemd assets, platform adapter contracts,
    package tests
  - Acceptance: One compatibility-checked artifact set installs launchers,
    backend, socket, tray, and schedules; upgrade validates them before
    retirement; rollback restores the prior release without deleting records or
    changing policy.
  - Evidence: Compatibility-checked deployment and immutable selected-release activation now cover CLI/backend/tray entrypoints, exact asset hashes and permissions, atomic installation, health-gated upgrade, rollback preserving policy and run records, Linux service/socket/tray/disabled-retention-timer assets, and a fail-closed Windows token/group/named-pipe adapter seam. The focused Phase 4 suite passed 178 tests; the expanded system-control/monitoring/integration suite passed 753 with 1 skipped; wheel/sdist validation covered four console entrypoints and 20 package-data files; an installed headless artifact imported CLI without loading tray code or requiring pystray; staged systemd unit verification passed with recursive dependency errors disabled.
  - Status: Repository readiness complete; live Mint installation, production adapter activation, authorized/denied actions, retention execution, and rollback rehearsal remain T010 and require explicit host-mutation approval.
  - Evidence mode: validation
  - [x] T009.1 Add artifact manifest, permission, upgrade, and rollback tests.
    - Evidence: `test_deployment.py` passed manifest hash, installed-mode,
      health-gated upgrade, failed-upgrade, rollback, and policy/run-record
      preservation cases inside the 178-test Phase 4 suite.
    - Evidence mode: validation
  - [x] T009.2 Complete Linux install assets and Windows service/named-pipe test
    double.
    - Evidence: The validated artifact contains backend/socket, stable
      CLI/backend/tray launchers, tray autostart, and disabled retention timer
      assets; `test_windows_adapter.py` passed four token, membership, request
      bound, and close-path tests.
    - Evidence mode: validation
  - [x] T009.3 Prove headless install requires no GUI dependencies.
    - Evidence: A fresh artifact venv installed the wheel without GUI extras,
      ran `timelocker-system-control --help`, imported `TimeLocker.cli` without
      loading tray integration, and confirmed `pystray` was absent.
    - Evidence mode: validation

- [~] T010 Run controlled Linux Mint live acceptance and rollback rehearsal.
  - Depends on: T009
  - Requirements: Requirements 1-6; SC-001-SC-011
  - Files: `verification.md`, external system assets only after explicit rollout
    approval
  - Acceptance: Authorized and denied system views, system launcher, scheduled
    backup, restore, post-success retention, independent retention, tray
    reconnect, interrupted-run recovery, upgrade, and rollback are evidenced.
  - Evidence mode: external
  - Evidence: Operator approved T010 rollout on 2026-07-26. Scope: create the operator group, install root-owned committed-release launchers/assets, enable the control socket, install tray autostart, stage retention units disabled, and rehearse upgrade/rollback while preserving the existing 03:30 backup timer. Retention mutation remains gated on separate approval of a successful identical dry-run fingerprint. Rules consulted and applied: Coding Standards (100), General Preferences (50), Operational Best Practices (40), Planning Protocol (30), Testing Conventions (25), Documentation Conventions (20), Git Conventions (15).
  - Status: Live Linux Mint rollout and acceptance in progress; retention mutation not approved.
  - [ ] T010.1 Stage without changing the working 03:30 backup.
  - [ ] T010.2 Obtain explicit approval before group membership, service,
    launcher, timer, or live-retention mutations.
  - [ ] T010.3 Execute acceptance and record secret-free evidence.
  - [ ] T010.4 Rehearse rollback and confirm backup scheduling remains healthy.

## Phase 5: Promotion, review, and closure

- [ ] T011 Promote accepted behavior into durable documentation.
  - Depends on: T010
  - Files: all promotion targets in `change-impact.md`
  - Acceptance: Durable requirements, architecture, CLI reference,
    installation, tray, scheduling, troubleshooting, rollout, and rollback docs
    match implemented behavior and no future intent is presented as current.
  - Evidence: Pending.

- [ ] T012 Complete expert review, full validation, residual disposition, and
  closure preparation.
  - Depends on: T011
  - Files: Spec verification/traceability, durable docs, closure records
  - Acceptance: Security, Restic/recovery, operations/portability, Python CLI,
    tests, and documentation findings have recorded dispositions; all
    requirements, ACs, and properties have evidence; closure and archive checks
    pass.
  - Evidence mode: validation
  - Evidence: Pending.

## Execution Rules

- Do not implement from this file alone. Load the linked requirement, design,
  traceability, change-impact, and verification context first.
- Mark only one implementation task `[~]` at a time unless tasks have no file
  or state conflict.
- Do not use `AccessManager` sessions as proof of operating-system identity or
  operator-group membership.
- Do not grant `timelocker-operators` direct access to journald, credentials,
  `/var/restic`, raw Restic arguments, or protected source paths.
- Live installation, group membership, service enablement, schedule changes,
  retention mutation, and rollback require explicit operator approval at T010.
- Record evidence before marking any task complete.

## Related Artifacts

- Requirements: `requirements.md`
- Canonical context: `canonical-context.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Traceability: `traceability.md`
- Verification: `verification.md`

## Reconciliation

Reviewed against the 2026-07-26 requirements and design revisions. T001-T006
cover the tightened system-record authorization, audit separation, diagnostic
projection, NSS failure, transport-bound, and storage-hardening work. No task
dependency or live-mutation approval boundary changed.
