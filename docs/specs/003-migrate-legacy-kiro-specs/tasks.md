---
title: Migrate legacy Kiro specifications tasks
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

## Phase 1: Inventory and Reconciliation

- [x] T001 Inventory all legacy packages and establish the migration contract.
  - Depends on: none
  - Requirement: Requirement 1, Requirement 2
  - Acceptance Criteria: Requirement 1 AC1; Requirement 2 AC1; Requirement 2 AC2
  - Properties: CP-001, CP-002
  - Files: `.kiro/specs/`, `docs/specs/`, repository rules
  - Acceptance: All source packages are counted; template authority and selective-migration policy are recorded.
  - Evidence mode: validation
  - Evidence: Direct inventory found 13 ordinary packages plus 2 deferred requirements packages under .kiro/specs; the repository has no spec-package templates, so the approved migration uses the lifecycle skill fallback templates and an active-only destination policy.

- [x] T002 Reconcile every package against current code, tests, durable docs, and Spec 001.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1; Requirement 1 AC2; Requirement 1 AC3
  - Properties: CP-001, CP-003, CP-004
  - Files: `.kiro/specs/`, `src/`, `tests/`, `docs/`
  - Acceptance: Fifteen unique package dispositions have concrete current evidence and no unresolved classification remains.
  - Evidence mode: validation
  - Evidence: Recorded exactly fifteen unique package dispositions in verification.md using current durable documents, legacy task state, Spec 001, and a focused run in which all 316 selected tests passed; the command's only nonzero gate was repository-wide coverage on the intentionally scoped selection.

## Phase 2: Selective Migration and Promotion

- [x] T003 Apply the lifecycle destination decision to every reconciled package.
  - Depends on: T002
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1; Requirement 2 AC2; Requirement 2 AC3
  - Properties: CP-002, CP-003
  - Files: `docs/specs/`, `docs/specs/README.md`
  - Acceptance: New packages, if any, are coherent and lifecycle-clean; completed, stale, superseded, and deferred packages are not active.
  - Evidence mode: validation
  - Evidence: Applied the disposition matrix: no new active package was justified; Spec 001 remains the only destination for accepted unfinished legacy scope, and all other packages are completed, stale, rejected optional scope, or deferred proposals.

- [x] T004 Confirm durable ownership and prepare compact closure evidence.
  - Depends on: T003
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1
  - Properties: CP-004
  - Files: current durable docs, `docs/history/`, `docs/specs/README.md`
  - Acceptance: No accepted implemented behavior exists only in a legacy package; closure destinations and recovery evidence are prepared.
  - Evidence mode: validation
  - Evidence: Verified durable ownership for every confirmed current behavior in the fifteen-package matrix and redirected retained CLI and recovery references to current docs. No legacy-only desired-state content was accepted for promotion; Git plus compact lifecycle history is the recovery destination.

## Phase 3: Cleanup and Closure

- [x] T005 Remove `.kiro/specs/` and eliminate retained authoritative references.
  - Depends on: T004
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1; Requirement 3 AC2
  - Properties: CP-001, CP-004
  - Files: `.kiro/specs/`, retained repository docs
  - Acceptance: Legacy spec files and empty package directories are absent; current docs contain no links to them.
  - Evidence mode: implementation
  - Evidence: `test ! -e .kiro/specs` returned 0 after removal of 44 tracked files and empty directories. `rg` found zero retained Markdown links targeting the legacy tree. CLI and recovery references now target current durable docs.

- [x] T006 Validate the migration and prepare the final Spec 003 state for closure.
  - Depends on: T005
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1; Requirement 3 AC2; Requirement 3 AC3
  - Properties: CP-001-CP-004
  - Files: `docs/specs/003-migrate-legacy-kiro-specs/`, `docs/history/`, Git history
  - Acceptance: Lifecycle, link, legacy-target, syntax, and formatting checks pass; the migration commit is recorded and the package is ready for its required final-state commit.
  - Evidence mode: validation
  - Evidence: Migration commit `c32f9a3` preserves the complete source-removal change. Spec lifecycle lint has 0 findings and stage readiness has 0 gaps; `scripts/link_checker.py` scanned 111 docs and 215 links with 0 broken links; legacy link and directory checks, example `py_compile`, and `git diff --check` passed. The package is ready for its final-state commit and recorded removal.

## Execution Rules

- Do not implement runtime features or mutate external issue state.
- Do not treat legacy checkboxes as current proof.
- Do not copy completed or deferred packages into the active spec tree.
- Use current code, tests, durable docs, and executable checks as evidence.
- Commit the complete final Spec 003 package before removing it.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
