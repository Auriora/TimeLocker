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
| Package lint/readiness | Spec integrity | No unwaived errors or readiness gaps; next task is T006 | reconciliation validation |
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
- 2026-07-18 reconciliation: all eight acceptance criteria are explicitly
  mapped; D001 retains the public service-manager facade; D002 selects
  `commands.monitoring`; the repository-hygiene prerequisite is satisfied.
- 2026-07-18 charter baseline review: `CHARTER.md` adds enduring governance but
  does not change this package's validation plan or T005 readiness.
- T005 (2026-07-18): repository input validation in backup and snapshots moved
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
- T006-T008: pending.

## Evidence Recording Rules

For each remaining task, record the exact focused commands, result summary,
changed caller group, compatibility behavior retained, and residual risk. A
search result alone does not prove runtime behavior; pair it with focused tests.

## Durable Promotion And Cleanup

| Spec content | Durable destination or deferral | Status | Evidence |
|--------------|---------------------------------|--------|----------|
| Resolver/service/monitoring boundaries | `docs/3-implementation/service-layer-integration.md` | pending | T009 |
| Code navigation and ownership | `docs/reference/repo-orientation-and-change-map.md` | pending | T009 |
| Public command hierarchy | unchanged unless drift is discovered | pending review | CLI contract tests |
| Implementation history | Git commits, pull requests, and CI evidence | complete | Existing completed slices cite their commits; future slices record equivalent evidence |

### Spec Cleanup Decision

- **Cleanup action:** keep active
- **Reason:** T005-T008 remain pending.
- **Final spec commit:** pending
- **Closure log path:** `docs/history/spec-closure-log.md`
- **Closure log entry updated:** no
- **Closure cleanup commit:** pending
- **Active indexes updated:** no
- **Durable docs linked back to evidence where useful:** yes
- **Residual spec-only content:** remaining requirements, tasks, and validation evidence

## Ship Or Closure Risk

- **Risk level:** medium
- **Breaking change:** no
- **Blast radius checked:** partial — required per remaining task
- **Rollback path:** revert each bounded implementation slice
- **Requires human review:** yes for compatibility removals
- **Release notes needed:** only if user-visible behavior changes
- **Follow-up issue or spec needed:** only for newly discovered out-of-scope defects

### Risk Rationale

The CLI has broad command coverage and compatibility seams. Small slices and
contract tests reduce risk, but hidden consumers and backend-specific resolution
paths remain possible until inventory and full validation complete.

## Residual Risks

- External consumers of `CLIServiceManager` may not be visible in repository
  searches; D001 therefore retains the tested public facade.
- Repository-resolution behavior may vary across local, S3, and B2 backends.
- Optional monitoring integrations may need validation outside the focused
  unit suite; D002 fixes command ownership while retaining the integration
  bridge.

## Readiness Decision

- **Ready for promotion:** no
- **Ready for release:** no
- **Ready for closure:** no
