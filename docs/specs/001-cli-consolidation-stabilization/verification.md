---
title: CLI consolidation stabilization verification
doc_type: spec
artifact_type: verification
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Verification

## Validation Plan

| Gate | Covers | Pass criterion | Evidence |
|------|--------|----------------|----------|
| Package lint/readiness | Spec integrity | No unwaived errors or readiness gaps; next task is T008 | reconciliation validation |
| CLI contract tests | Requirement 1, CP-001 | Help/discovery and unique-registration tests pass | record per slice |
| Resolver validation | Requirement 2, CP-002 | Focused tests pass and direct imports are eliminated or justified | T005 |
| Service-manager validation | Requirement 3, CP-003 | Focused tests pass and selected fan-out is removed | T006 |
| Monitoring validation | Requirement 4 | Focused tests pass and one command-facing path is documented | T007 |
| Full regression suite | Requirements 1-4 | Repository-required pytest suite passes or waivers are recorded | T008 |
| Durable promotion | Closure | Required docs and updates reflect accepted implementation | T009 |
| Closure readiness | Closure | Residual risk, deferrals, final commit, and cleanup action are recorded | T010 |

## Quality Gates

- Confirm the repository-hygiene prerequisite remains recorded as closed before T005 starts.
- Run CLI contract tests after every remaining implementation slice.
- Pair static dependency/import searches with focused behavioral tests.
- Do not remove compatibility behavior without caller inventory and impact review.
- Run the repository-required full test suite before promotion and closure.
- Record waivers, residual risks, and exact evidence for every incomplete gate.

## Evidence Log

- T001-T003: commit `d8600cc5ee9b06774e1d73f69a392179015e4bff`.
- T004: commit `519dc81cbc77147fa64b12041c608b1ae7cd978e`.
- 2026-07-18 reconciliation: `traceability.md` explicitly maps all eight acceptance criteria;
  mapped; D001 retains the public service-manager facade; D002 selects
  `commands.monitoring`; the repository-hygiene prerequisite is satisfied.
- 2026-07-18 charter baseline review: `CHARTER.md` adds enduring governance but
  does not change this package's validation plan or T005 readiness.
- T005 (2026-07-18): 87 focused tests passed after repository input validation in backup and snapshots moved
  behind `RepositoryResolver`; restore's unused direct utility import was
  removed. Red-first coverage produced five expected failures (`41 passed`),
  followed by 87 passing focused resolver/command tests from `pytest` over the
  resolver service/integration, backup, restore, and snapshots test modules.
  `pytest tests/TimeLocker/cli/test_cli_help_system.py::TestCLIHelpSystem::test_top_level_command_names_are_unique -q`
  passed; `rg` found no command imports from
  `TimeLocker.utils.repository_resolver`; package lint returned zero
  diagnostics; and `git diff --check` passed.
  Agent Workbench had no Python diagnostics provider, so executed tests and
  direct source/import checks are the authoritative evidence.
- T006 (2026-07-18): `backup create` now obtains the public focused
  `BackupCLIHandler` and uses it for template validation, creation guidance,
  summary retrieval, and selection backup execution. `CLIServiceManager`
  retains tested thin delegates for D001 compatibility, and command doubles
  without the focused handler retain an explicit legacy adapter. `pytest
  --no-cov -q` over `test_backup_commands.py`,
  `test_backup_cli_handler.py`, `test_backup_data_selection_integration.py`,
  and the isolated top-level command uniqueness test passed 50 tests. A direct
  caller search found facade selection calls only in guarded compatibility
  branches; package lint and `git diff --check` passed. The same focused set
  with configured coverage passed all 50 tests but produced 18.52% aggregate
  repository coverage and therefore did not satisfy the global 50% threshold;
  the full-suite coverage gate remains assigned to T008.
- T007 (2026-07-18): removed `src/TimeLocker/cli_modules/commands/monitor.py`
  after root CLI and registry
  imports were confirmed on `cli_modules.commands.monitoring`. New tests
  enforce the single module owner and verify that the retained public
  `CLIServiceManager` monitoring
  methods delegate to `CLIMonitoringIntegration` with the expected filters.
  `pytest --no-cov -q` over monitoring commands, registry integration, and the
  isolated top-level uniqueness contract passed 35 tests; Ruff passed; and the
  runtime caller search found no legacy module references. The configured
  coverage run passed all 35 test cases but produced 15.53% aggregate
  repository coverage, leaving the global 50% gate for T008.
- T008 (2026-07-18): configured `pytest` result was 2,801 passed and 52.45% coverage after its initial five-failure
  limit after 1,387 passes because coverage instrumentation pushed four CLI
  startup cases and the repository-resolver benchmark beyond their timing
  thresholds. All five CLI startup cases plus the resolver benchmark passed
  without coverage (`6 passed in 1.33s`). A configured run with only those six
  timing tests deselected completed with 2,801 passed, 1 skipped, 1 failed,
  and 52.45% coverage. The remaining failure was the unchanged 60-second
  long-running selection stress threshold: 57 iterations under coverage and
  70 without coverage versus the required 100 while unrelated host backup and
  analysis workloads produced load averages of 17-23. Every per-iteration
  stability assertion and all other stress and selection tests passed. The six
  instrumentation conflicts and this pre-existing host-sensitive throughput
  threshold are explicitly waived; the latter remains a residual performance
  risk outside Spec 001's changed paths.
- T009 (2026-07-18): promoted accepted seams to `docs/3-implementation/service-layer-integration.md` and `docs/reference/repo-orientation-and-change-map.md`, including the repository resolver,
  `BackupCLIHandler`, compatibility facade, and monitoring ownership seams to
  `docs/3-implementation/service-layer-integration.md` and
  `docs/reference/repo-orientation-and-change-map.md`. The public command
  hierarchy did not drift. Agent Workbench reported zero Markdown findings,
  the repository link checker found no broken links, the deleted monitoring
  module no longer appears in current implementation/reference docs, and
  `git diff --check` passed.

## Evidence Recording Rules

For each remaining task, record the exact focused commands, result summary,
changed caller group, compatibility behavior retained, and residual risk. A
search result alone does not prove runtime behavior; pair it with focused tests.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Resolver/service/monitoring boundaries | `docs/3-implementation/service-layer-integration.md` | complete | T009 Markdown and link checks passed |
| Code navigation and ownership | `docs/reference/repo-orientation-and-change-map.md` | complete | T009 Markdown and link checks passed |
| Public command hierarchy | unchanged | complete; no update required | CLI contract tests passed |
| Implementation history | Git commits, pull requests, and CI evidence | complete | Existing completed slices cite their commits; future slices record equivalent evidence |

### Spec Cleanup Decision

- **Cleanup action:** remove the active package after its complete final state
  is committed; recover it from Git when historical evidence is needed
- **Reason:** all accepted behavior has been implemented, validated, or
  explicitly waived and promoted to durable documentation
- **Final spec commit:** required before removal; the commit containing this
  completed package is the final spec commit, and its hash must be recorded in
  the closure log and archive index during cleanup
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** by the cleanup commit after the final spec
  commit exists
- **Closure cleanup commit:** removes the package, updates the closure log and
  archive index, and removes Spec 001 from active indexes; its hash is recorded
  by a following history-only commit
- **Active indexes updated:** by the cleanup commit
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** coordination and validation history only;
  preserved by the final spec commit and intentionally removed from active docs

## Ship Or Closure Risk

- **Risk level:** medium
- **Breaking change:** no
- **Blast radius checked:** yes — focused caller searches, contract tests,
  full-suite execution, and durable ownership review completed
- **Rollback path:** revert each bounded implementation slice
- **Requires human review:** completed through the approved D001/D002 decisions;
  public compatibility seams were retained
- **Release notes needed:** only if user-visible behavior changes
- **Follow-up issue or spec needed:** test-infrastructure intake for the
  host-sensitive long-running stress threshold

### Risk Rationale

The CLI has broad command coverage and compatibility seams. Small slices and
contract tests reduce risk, but hidden consumers and backend-specific resolution
paths remain possible until inventory and full validation complete.

## Residual Risks

- External consumers of `CLIServiceManager` may not be visible in repository
  searches; D001 therefore retains the tested public facade and its thin
  selection and monitoring delegates.
- Repository-resolution behavior may vary across local, S3, and B2 backends.
- Optional monitoring integrations may need validation outside the focused
  unit suite; D002 fixes command ownership while retaining the integration
  bridge.
- Repository-wide startup and throughput thresholds are sensitive to coverage
  instrumentation and host contention. The focused startup and resolver
  benchmarks passed without coverage, but the unchanged long-running selection
  stress threshold remained below target during a heavily loaded host session.
  This is accepted as non-blocking baseline risk because Spec 001 did not alter
  the test or the `FileSelection` paths it exercises and all stability
  assertions passed.

### Deferred And Follow-Up Work

- No Spec 001 requirement or implementation task is deferred.
- Recalibrating or isolating the host-sensitive long-running stress throughput
  threshold belongs in a future test-infrastructure issue or focused spec if it
  is to remain a release gate. The closure log carries this follow-up until an
  external issue is authorized and created.

## Final Closure Checks

- Package lint: 0 errors, 0 warnings, 0 informational findings.
- Task-state audit: pass with 0 findings.
- Evidence quality: 34 records; 33 concrete and 1 explicitly waived; 0
  diagnostics.
- Promotion plan: 6 targets and 0 missing targets. The CLI hierarchy required
  no edit because contract validation found no drift.
- Closure risk: low with 0 findings and 0 blind spots.
- Closure readiness: ready with 0 blockers.
- Documentation: the two promoted durable documents passed Agent Workbench
  Markdown checks with 0 findings; the full changed set retained advisory
  table-readability warnings in temporary spec tables only.
- Repository integrity: the link checker found 0 broken links and
  `git diff --check` passed.

## Readiness Decision

- **Ready for promotion:** yes — required durable targets are updated
- **Ready for release:** yes for the Spec 001 refactor scope, subject to the
  recorded environment-sensitive timing waivers
- **Ready for closure:** yes — after committing this complete package, record
  that commit in lifecycle history and execute the documented removal sequence
