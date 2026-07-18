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

- [x] T007 Consolidate monitoring command and integration paths.
  - Depends on: T006
  - Requirement: Requirement 4
  - Acceptance Criteria: Requirement 4 AC1, Requirement 4 AC2
  - Properties: CP-001
  - Files: monitoring command modules, `src/TimeLocker/cli_modules/monitoring_integration.py`, focused tests
  - Acceptance: One documented command-facing monitoring integration path remains; compatibility delegates are explicit and tested.
  - Validation: Focused monitoring tests, CLI contract tests, and caller/dependency search.
  - Evidence: Completed 2026-07-18. Root CLI and the command registry both
    mount `cli_modules.commands.monitoring`; the unreferenced singular
    `commands.monitor` duplicate was removed. Focused ownership, facade,
    monitoring-command, registry, and CLI uniqueness validation passed 35
    tests. The retained `CLIServiceManager` methods are tested delegates to
    `CLIMonitoringIntegration`.
  - Status: Completed 2026-07-18; T008 is now dependency-ready.
  - Evidence mode: implementation
  - [x] T007.1 Inventory monitoring commands, formatters, integrations, and tests.
    - Evidence: `rg` and Agent Workbench reference inventory found both root
      CLI and registry mounting the plural module, four bridge construction or
      import references, no runtime caller of the singular module, and the
      focused monitoring and registry test surfaces.
  - [x] T007.2 Choose the retained owner and document compatibility constraints.
    - Evidence: Applied D002: `cli_modules.commands.monitoring` owns the
      `monitor`, `logs`, and `reports` groups; `CLIMonitoringIntegration` owns
      data access and formatting. Public `CLIServiceManager` monitoring methods
      remain compatibility delegates and have focused coverage.
  - [x] T007.3 Migrate callers and remove unreachable duplicate orchestration.
    - Evidence: No callers required migration because both supported mounting
      paths already imported `commands.monitoring`; removed the 449-line
      unreferenced `commands.monitor` duplicate and added a regression that
      enforces the single module owner.
  - [x] T007.4 Run focused validation and record commands/results.
    - Evidence: `pytest --no-cov -q` over monitoring commands, registry
      integration, and isolated CLI uniqueness passed 35 tests; Ruff and the
      runtime caller search passed. Configured coverage also passed all 35 test
      cases but reported 15.53% repository-wide coverage, below the global 50%
      gate assigned to T008.
  - Rules consulted and applied: Coding Standards (100), General Preferences
    (50), Operational Best Practices (40), Testing Conventions (25),
    Documentation Conventions (20), and Git Conventions (15); no overrides.

## Phase 3: Promotion and Closure

- [x] T008 Run the full required regression suite.
  - Depends on: T007
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 2 AC1, Requirement 2 AC2, Requirement 3 AC1, Requirement 3 AC2, Requirement 4 AC1, Requirement 4 AC2
  - Properties: CP-001, CP-002, CP-003
  - Files: `verification.md`, repository test suite
  - Acceptance: Focused and full tests pass or have explicit justified waivers and recorded residual risk.
  - Evidence: Completed 2026-07-18. The configured suite reached 2,801 passed, 1 skipped, 6 timing-only deselections, 1 environment-sensitive stress timing failure, and 52.45% coverage. All five CLI startup benchmarks plus the repository-resolver benchmark passed without coverage (6 passed in 1.33s), establishing a coverage-instrumentation waiver. The unchanged 60-second long-running selection stress test completed 57 iterations under coverage and 70 without coverage versus its >100 threshold while unrelated host workloads produced load averages of 17-23; its stability assertions and every other stress/selection test passed. This pre-existing, host-sensitive throughput threshold is waived with residual performance risk; Spec 001 did not change the test or its FileSelection implementation.

  - Status: Complete with explicit timing waivers and recorded residual risk; T009 is dependency-ready.
  - Evidence mode: validation
- [x] T009 Promote accepted service and ownership boundaries into durable docs.
  - Depends on: T008
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Files: durable promotion targets listed in `change-impact.md`
  - Acceptance: Durable docs describe the final seams and implementation evidence is linked without duplicating the spec.
  - Evidence: Completed 2026-07-18. Promoted the final RepositoryResolver command seam, focused BackupCLIHandler selection routing, retained CLIServiceManager compatibility boundary, and single monitoring command/integration ownership into docs/3-implementation/service-layer-integration.md and docs/reference/repo-orientation-and-change-map.md. The public command hierarchy was unchanged. Agent Workbench checked both documents with zero findings; the repository link checker found no broken links; the deleted monitoring module is absent from current implementation/reference docs; and git diff --check passed.

  - Status: Durable promotion complete; T010 is dependency-ready.
  - Evidence mode: documentation
- [x] T010 Record residual risk and prepare lifecycle closure.
  - Depends on: T009
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4
  - Files: `verification.md`
  - Acceptance: `verification.md` contains a complete, evidence-backed closure-readiness decision.
  - Evidence: Completed 2026-07-18. verification.md contains the full-suite results and waivers, four residual-risk classes, the stress-threshold test-infrastructure destination, complete durable-promotion status, the final-spec and cleanup sequence, and an affirmative closure-readiness decision. T010.1-T010.3 each contain concrete lifecycle evidence; package lint, links, and Git integrity passed.
  - Status: Closure preparation complete; package is ready for final deterministic checks and final-spec commit.
  - Evidence mode: lifecycle
  - [x] T010.1 Record residual risks and any deferred destinations.
  - Evidence: Completed 2026-07-18. verification.md now contains four explicit residual-risk entries covering the retained facade, backend variation, optional monitoring integrations, and environment-sensitive timing. Its routing section states that every Spec 001 requirement and implementation task was delivered and assigns the baseline stress-threshold concern to test-infrastructure intake through the durable closure record.
  - Status: Residual-risk classification and destination are documented.
  - Evidence mode: lifecycle
  - [x] T010.2 Record the final-spec-commit requirement and cleanup action.
  - Evidence: Completed 2026-07-18. verification.md records removal as the package disposition, Git as the recovery path, a complete-package commit before removal, the final commit hash in both history records, package and active-index removal in the cleanup commit, and exact cleanup-hash recording in a following history-only commit.
  - Status: Final-spec commit and cleanup sequence documented.
  - Evidence mode: lifecycle
  - [x] T010.3 Run closure checks and record their results.

  - Evidence: Completed 2026-07-18. Final package lint and task audit returned 0 findings; evidence quality classified all 34 records as 33 concrete and 1 explicitly waived with 0 diagnostics; promotion reported 6 targets and 0 missing; closure risk was low with 0 findings and blind spots; and closure readiness was ready with 0 blockers. Promoted durable docs had 0 Markdown findings, the link checker found 0 broken links, and git diff --check passed. verification.md records these results.
  - Status: Final deterministic closure checks passed with zero blockers.
  - Evidence mode: lifecycle
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
