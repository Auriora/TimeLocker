---
title: CLI consolidation stabilization tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

The `CHARTER.md` durable-baseline addition was reviewed on 2026-07-18; no task,
dependency, acceptance, or sequencing change is required.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010
```

## Phase 1: Completed Foundation

- [x] T001 Normalize root CLI registration through one merge helper.
  - Depends on: none
  - Requirement: Requirement 1
  - Files: `src/TimeLocker/cli.py`
  - Acceptance: Hybrid command groups use one merge helper.
  - Evidence mode: implementation
  - Evidence: commit `d8600cc5ee9b06774e1d73f69a392179015e4bff`.

- [x] T002 Remove duplicate security command-group mounting.
  - Depends on: T001
  - Requirement: Requirement 1
  - Files: `src/TimeLocker/cli.py`
  - Acceptance: `security` is mounted once and modular commands merge into the existing app.
  - Evidence mode: implementation
  - Evidence: commit `d8600cc5ee9b06774e1d73f69a392179015e4bff`.

- [x] T003 Add a unique top-level command registration regression test.
  - Depends on: T002
  - Requirement: Requirement 1
  - Files: `tests/TimeLocker/cli/`
  - Acceptance: Tests fail if duplicate root command registrations reappear.
  - Evidence mode: validation
  - Evidence: commit `d8600cc5ee9b06774e1d73f69a392179015e4bff`.

- [x] T004 Standardize CLI command configuration access on `ConfigService`.
  - Depends on: T003
  - Requirement: Requirements 1 and 3
  - Files: `src/TimeLocker/cli_modules/commands/`, `src/TimeLocker/cli_modules/services/config_service.py`
  - Acceptance: Command code no longer constructs `ConfigurationModule` outside explicit compatibility helpers.
  - Evidence mode: implementation
  - Evidence: commit `519dc81cbc77147fa64b12041c608b1ae7cd978e`.

## Phase 2: Remaining Consolidation

- [x] T005 Standardize CLI command modules on `RepositoryResolver`.
  - Depends on: T004
  - Status note: Completed 2026-07-18; T006 is now dependency-ready.
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, Requirement 2 AC2
  - Properties: CP-001, CP-002
  - Files: `src/TimeLocker/cli_modules/commands/`, `src/TimeLocker/cli_modules/services/repository_resolver.py`, focused tests
  - Acceptance: Command modules use the service seam; remaining direct utility imports are documented compatibility cases with tests.
  - Validation: Focused resolver/command tests, CLI contract tests, and an import search.
  - Evidence mode: implementation
  - Evidence: Repository input validation in backup and snapshots now uses the
    `RepositoryResolver` seam; restore's unused direct utility import was
    removed. Focused resolver/command validation passed 87 tests; the unique
    top-level command test passed; the direct-import search returned no matches;
    package lint and `git diff --check` passed.
  - [x] T005.1 Inventory command callers, direct utility imports, and current tests.
    - Evidence: `rg` inventory on 2026-07-18 identified the three command
      imports and existing resolver, backup, restore, snapshots, and CLI tests.
  - [x] T005.2 Add or refine regression coverage for repository inputs and errors.
    - Evidence: Added service delegation/error-contract tests and a command
      import-boundary regression; the pre-implementation run failed with five
      expected failures (`41 passed, 5 failed`).
  - [x] T005.3 Migrate one coherent caller group and remove duplicate resolution logic.
    - Evidence: Repository input validation in backup and snapshots now crosses
      the `RepositoryResolver` service seam; restore's unused direct utility
      import was removed. The first focused post-change run passed all 87 tests.
  - [x] T005.4 Run focused validation and record commands/results.
    - Evidence: `pytest` over resolver integration/service plus backup, restore,
      and snapshots command tests passed 87 tests; the isolated CLI uniqueness
      test passed; `rg` found no command imports from
      `TimeLocker.utils.repository_resolver`; lifecycle lint and diff checks
      passed. Agent Workbench static diagnostics were unavailable for Python
      files and returned no actionable findings.

- [x] T006 Reduce `CLIServiceManager` domain fan-out.
  - Depends on: T005
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-001, CP-003
  - Files: `src/TimeLocker/cli_services.py`, command/service callers, focused tests
  - Acceptance: Selected callers use narrow services while `get_cli_service_manager()` remains a tested compatibility facade.
  - Validation: Focused service/facade tests, CLI contract tests, and dependency search.
  - Evidence: Completed 2026-07-18. The four selection-template operations in
    `backup create` now use `BackupCLIHandler` directly for real managers, while
    D001's public `CLIServiceManager` methods remain tested thin delegates and
    compatible manager doubles retain the legacy path. The focused service,
    command, integration, and CLI-contract run passed 50 tests.
  - [x] T006.1 Inventory manager methods, callers, fallbacks, and external compatibility risk.
    - Evidence: `rg` inventory on 2026-07-18 mapped manager methods, command
      callers, focused services, and tests; selection backup is isolated behind
      `BackupCLIHandler`, while monitoring is reserved for T007.
  - [x] T006.2 Select a bounded caller group and add regression coverage.
    - Evidence: Selected selection-template backup orchestration; added tests
      for the focused handler, public facade property, and legacy facade
      compatibility. The first focused run passed 31 tests.
  - [x] T006.3 Move domain logic to focused services and retain thin delegates as needed.
    - Evidence: `CLIServiceManager.selection_handler` exposes the focused
      service. Template existence, missing-template guidance, selection
      summaries, and selection backup execution now use it for real managers.
      The public facade remains a tested thin delegate, and compatible
      test/external doubles retain the legacy adapter path.
  - [x] T006.4 Run focused validation and record commands/results.
    - Evidence: `pytest --no-cov -q` over backup command, focused handler,
      selection integration, and isolated CLI uniqueness tests passed 50 tests;
      the caller search found facade calls only in explicit compatibility
      branches; lifecycle lint and `git diff --check` passed. The same focused
      set under configured coverage passed all 50 tests but reported 18.52%
      repository-wide coverage, below the global 50% gate; T008 owns the full
      suite and coverage decision.
  - Rules consulted and applied: Coding Standards (100), General Preferences
    (50), Operational Best Practices (40), Testing Conventions (25),
    Documentation Conventions (20), and Git Conventions (15); no overrides.

- [ ] T007 Consolidate monitoring command and integration paths.
  - Depends on: T006
  - Requirement: Requirement 4
  - Acceptance Criteria: Requirement 4 AC1, Requirement 4 AC2
  - Properties: CP-001
  - Files: monitoring command modules, `src/TimeLocker/cli_modules/monitoring_integration.py`, focused tests
  - Acceptance: One documented command-facing monitoring integration path remains; compatibility delegates are explicit and tested.
  - Validation: Focused monitoring tests, CLI contract tests, and caller/dependency search.
  - Evidence: Pending.
  - [ ] T007.1 Inventory monitoring commands, formatters, integrations, and tests.
  - [ ] T007.2 Choose the retained owner and document compatibility constraints.
  - [ ] T007.3 Migrate callers and remove unreachable duplicate orchestration.
  - [ ] T007.4 Run focused validation and record commands/results.

## Phase 3: Promotion and Closure

- [ ] T008 Run the full required regression suite.
  - Depends on: T007
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 2 AC1, Requirement 2 AC2, Requirement 3 AC1, Requirement 3 AC2, Requirement 4 AC1, Requirement 4 AC2
  - Properties: CP-001, CP-002, CP-003
  - Files: `verification.md`, repository test suite
  - Acceptance: Focused and full tests pass or have explicit justified waivers and recorded residual risk.
  - Evidence: Pending.

- [ ] T009 Promote accepted service and ownership boundaries into durable docs.
  - Depends on: T008
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Files: durable promotion targets listed in `change-impact.md`
  - Acceptance: Durable docs describe the final seams and implementation evidence is linked without duplicating the spec.
  - Evidence: Pending.

- [ ] T010 Record residual risk and prepare lifecycle closure.
  - Depends on: T009
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Files: `verification.md`
  - Acceptance: `verification.md` contains a complete, evidence-backed closure-readiness decision.
  - Evidence: Pending.
  - [ ] T010.1 Record residual risks and any deferred destinations.
  - [ ] T010.2 Record the final-spec-commit requirement and cleanup action.
  - [ ] T010.3 Run closure checks and record their results.

## Execution Rules

- Start with T005; the repository-hygiene prerequisite is satisfied.
- Do not implement from this checklist alone; read the linked requirements,
  design, impact, verification, and traceability context first.
- Before starting a task or subtask, mark it `[~]`.
- Split a task further if caller inventory reveals multiple independent slices.
- Complete parent tasks only after acceptance criteria and evidence are recorded.
- Do not remove public compatibility entry points without explicit impact review.
- Apply D001 by retaining the tested `CLIServiceManager` public facade; apply
  D002 by treating `cli_modules.commands.monitoring` as the command owner and
  `CLIMonitoringIntegration` as its bridge.

Rules consulted and applied: Coding Standards (100), General Preferences (50),
Operational Best Practices (40), Planning Protocol (30), Testing Conventions
(25), Documentation Conventions (20). Overrides: none.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
