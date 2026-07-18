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
T001 -> T002 -> T003 -> T004 -> T005
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
  - Evidence: Files created in this change; validation is recorded by T005.

## Phase 2: Migration and Promotion

- [x] T003 Migrate the active CLI plan and retain legacy history.
  - Depends on: T002
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3
  - Properties: CP-001, CP-003
  - Files: `docs/specs/001-cli-consolidation-stabilization/`, `docs/plans/`
  - Acceptance: Spec 001 carries completed evidence and pending tasks; no standalone plan remains active.
  - Evidence mode: implementation
  - Evidence: The legacy plan is marked superseded and linked to Spec 001; completed plans were not migrated.

- [x] T004 Promote the lifecycle contract into durable governance and navigation.
  - Depends on: T003
  - Requirement: Requirement 1, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3, Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-002
  - Files: `AGENTS.md`, `docs/README.md`, `docs/guides/ai-agent/`, `docs/history/`, `docs/updates/`
  - Acceptance: Future agents can discover, execute, promote, and close spec work without competing authorities.
  - Evidence mode: implementation
  - Evidence: Governance, indexes, history scaffolding, issue crosswalk, and update log are updated in this change.

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
    - Evidence: Two current-format active specs discovered with no package errors; Spec 001 reports ready for agent and implementation.
  - [x] T005.2 Validate archive history and record commit-dependent warnings.
    - Evidence: Archive index has no errors and one expected warning because this uncommitted migration cannot yet name its cleanup commit.
  - [x] T005.3 Validate changed internal links and formatting.
    - Evidence: Read-only link checker resolved all links across 25 changed documentation files; `git diff --check` passed.
  - [x] T005.4 Record final evidence and readiness in `verification.md`.
    - Evidence: Validation results, prompt-tool limitation, residual risks, and closure state are recorded.

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
