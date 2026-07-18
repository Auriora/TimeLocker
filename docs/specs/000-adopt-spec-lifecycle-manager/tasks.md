---
title: Adopt Spec Lifecycle Manager tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004 -> T005 -> T006
```

## Phase 1: Lifecycle Foundation

- [x] T001 Classify the repository and approve the migration boundary.
  - Depends on: none
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1
  - Files: `docs/`, `AGENTS.md`
  - Acceptance: Durable sources, active plans, and lifecycle readiness are reviewed; implementation is approved.
  - Evidence mode: validation
  - Evidence: Spec Lifecycle Manager classified the repository as `documented_no_specs`; user approved the migration plan on 2026-07-18.

- [x] T002 Create the active-spec lifecycle entry point and adoption package.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3
  - Files: `docs/specs/README.md`, `docs/specs/000-adopt-spec-lifecycle-manager/`
  - Acceptance: The lifecycle, artifacts, task states, and authority boundaries are explicit.
  - Evidence mode: implementation
  - Evidence: Commit `ce23d07` adds `docs/specs/README.md` and all six Spec 000 artifacts; `scan_specs` later reported `total=2`, `active_pass=2`, and `active_error=0`.

## Phase 2: Migration and Promotion

- [x] T003 Migrate the active CLI plan and retain legacy history.
  - Depends on: T002
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3
  - Properties: CP-001, CP-003
  - Files: `docs/specs/001-cli-consolidation-stabilization/`, `docs/plans/`
  - Acceptance: Spec 001 carries completed evidence and pending tasks; no standalone plan remains active.
  - Evidence mode: implementation
  - Evidence: Commit `ce23d07` changes the legacy CLI plan from `active` to `superseded`, adds Spec 001, and leaves the completed-plan inventory under `docs/plans/README.md` unchanged.

- [x] T004 Promote the lifecycle contract into durable governance and navigation.
  - Depends on: T003
  - Requirement: Requirement 1, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3, Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-002
  - Files: `AGENTS.md`, `docs/README.md`, `docs/guides/ai-agent/`, `docs/history/`, `docs/updates/`
  - Acceptance: Future agents can discover, execute, promote, and close spec work without competing authorities.
  - Evidence mode: implementation
  - Evidence: Commit `ce23d07` updates `AGENTS.md`, `docs/README.md`, both governing agent rules, lifecycle history, the issue crosswalk, and update index; the scoped link check resolved all links in 25 changed Markdown files.

## Phase 3: Verification and Closure Readiness

- [x] T005 Validate packages, task evidence, history consistency, links, and formatting.
  - Depends on: T004
  - Requirement: Requirement 1, Requirement 2, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3, Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3, Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-001, CP-002, CP-003
  - Files: `docs/specs/`, `docs/history/`, `docs/updates/`
  - Acceptance: Required lifecycle checks have no unwaived errors; residual warnings are explained.
  - Evidence mode: validation
  - Evidence: Lifecycle packages have no lint errors; Spec 001 is agent-ready with T005 selected; the archive warning is explicitly accepted as commit-dependent; 25 changed docs passed internal-link checks; `git diff --check` passed.
  - [x] T005.1 Run lifecycle package lint, scan, readiness, and task-state checks.
    - Evidence: `scan_specs` returned `total=2`, `active_pass=2`, `active_warn=0`, and `active_error=0`; `active_spec_preflight` selected Spec 001 T005 with status `ready`.
  - [x] T005.2 Validate archive history and record commit-dependent warnings.
    - Evidence: Before commit `ce23d07`, `archive_index` returned `error=0`, `warn=1`, code `ARCHIVE_INDEX_CLEANUP_COMMIT_PENDING`; T006 reconciles that historical record to the committed migration.
  - [x] T005.3 Validate changed internal links and formatting.
    - Evidence: Read-only link checker resolved all links across 25 changed documentation files; `git diff --check` passed.
  - [x] T005.4 Record final evidence and readiness in `verification.md`.
    - Evidence: `verification.md` records the package results at lines 16-22, evidence log at lines 34-48, promotion map at lines 52-58, and closure decision at lines 62-70 in commit `ce23d07`.

## Phase 4: Review Remediation

- [x] T006 Address whole-package review findings and reconcile closure readiness.
  - Depends on: T005
  - Requirement: Requirement 1, Requirement 2, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3, Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3, Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-001, CP-002, CP-003
  - Files: `docs/specs/000-adopt-spec-lifecycle-manager/`, `docs/specs/README.md`, `docs/history/`
  - Acceptance: Closure commits are accurate, lifecycle state is current, evidence and traceability checks pass, tooling fallback is durable, and readability findings are resolved or explicitly justified.
  - Evidence mode: validation
  - Evidence: `lint_spec_package`, `stage_readiness`, `task_context T006`, `evidence_quality_check`, and `archive_index` returned `0` errors, warnings, blockers, or traceability gaps; Agent Workbench checked `9` changed documents with no broken-link findings and `53` explicitly waived table-readability advisories.
  - [x] T006.1 Correct legacy closure history and Spec 000 commit state.
    - Evidence: `docs/history/spec-archive-index.md` and `docs/history/spec-closure-log.md` now identify `ce23d07` as both the legacy final-spec and cleanup commit; `archive_index` returned `error=0`, `warn=0`.
  - [x] T006.2 Strengthen completed-task and verification evidence.
    - Evidence: `evidence_quality_check` returned `error=0`, `warn=0` across `28` evidence records after task and verification proof signals were made concrete or explicitly waived.
  - [x] T006.3 Make acceptance and success-criterion traceability explicit.
    - Evidence: `stage_readiness` returned `acceptance_gap_count=0`, `property_gap_count=0`, and `context_gap_count=0`; `task_context T006` returned `gaps=[]`.
  - [x] T006.4 Add durable tooling prerequisites and fallback behavior.
    - Evidence: `docs/specs/README.md` now documents the external plugin prerequisite, manual fallback contract, lower-confidence boundary, and closure restoration rule.
  - [x] T006.5 Rerun lifecycle, evidence, history, link, and Markdown checks.
    - Evidence: Lifecycle lint, evidence, readiness, context, history, task-state, and closure checks returned no warnings, gaps, or blockers; Agent Workbench examined `9` documents with `0` broken links and `53` waived `markdown.table.readability` advisories; `git diff --check` returned exit code `0`.

## Execution Rules

- Read the full package before changing task state.
- Mark the selected task `[~]` before implementation.
- Complete a task only when its acceptance criteria and evidence are recorded.
- Promote accepted content into durable docs before closure.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
