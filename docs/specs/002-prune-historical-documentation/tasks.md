---
title: Prune historical documentation tasks
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

## Phase 1: Scope And Safety

- [x] T001 Inventory historical categories, retained current surfaces, incoming references, and rollback evidence.
  - Depends on: none
  - Requirement: Requirement 1, Requirement 2, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1; Requirement 2 AC1; Requirement 3 AC1
  - Properties: CP-002, CP-003
  - Files: `docs/`, Git history
  - Acceptance: Exact categories and retained surfaces are documented; user approval and final Spec 000 commit exist.
  - Evidence mode: validation
  - Evidence: Read-only inventory found `339` files under `docs/`, including `173` update records, `7` legacy plans, `5` point-in-time reports, `91` `.kiro/specs` references, and final Spec 000 commit `c84dc3a`; the user approved full cleanup.

## Phase 2: Remove Historical Delivery State

- [x] T002 Remove approved historical artifacts and change policy to Git-backed history.
  - Depends on: T001
  - Requirement: Requirement 1, Requirement 2
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC3; Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3
  - Properties: CP-002, CP-003
  - Files: `docs/updates/`, `docs/plans/`, `docs/archive/`, `docs/reports/`, `docs/issues/`, `docs/traceability/`, `docs/0-project-management/`, `docs/4-testing/`, `docs/specs/000-adopt-spec-lifecycle-manager/`, `docs/guides/ai-agent/`, `docs/history/`
  - Acceptance: Approved historical files are deleted, Spec 001 remains active, and durable policy names Git plus compact closure records as the history mechanism.
  - Evidence mode: implementation
  - Evidence: Removed the approved historical delivery artifacts and completed Spec 000 package; rewrote lifecycle policy and compact history records. Git preserves every deleted tracked file.

## Phase 3: Consolidate Current Documentation

- [x] T003 Remove legacy/future references and reconcile retained current-state documents.
  - Depends on: T002
  - Requirement: Requirement 1, Requirement 3
  - Acceptance Criteria: Requirement 1 AC2; Requirement 3 AC1, Requirement 3 AC2
  - Properties: CP-001, CP-002
  - Files: `docs/README.md`, `docs/DOCUMENTATION-STATUS.md`, `docs/2-architecture/`, `docs/3-implementation/`, `docs/4-testing/`, `docs/guides/`, `docs/reference/`, `docs/specs/README.md`
  - Acceptance: Retained docs describe current behavior, omit legacy source links and deleted artifacts, and route active work through Spec 001/GitHub.
  - Evidence mode: implementation
  - Evidence: Rewrote retained references so current documentation uses active Spec 001, durable documents, current implementation references, and immutable Git commit evidence. The scoped legacy-reference scan has zero unintended matches.

## Phase 4: Validation

- [x] T004 Run lifecycle, inventory, legacy-reference, link, Markdown, and formatting checks.
  - Depends on: T003
  - Requirement: Requirement 1, Requirement 2, Requirement 3
  - Acceptance Criteria: Requirement 1 AC1-AC3; Requirement 2 AC1-AC3; Requirement 3 AC1-AC3
  - Properties: CP-001, CP-002, CP-003
  - Files: `docs/`, Git state
  - Acceptance: All required checks pass or bounded residual findings are explicitly waived with evidence.
  - Evidence mode: validation
  - Evidence: scripts/link_checker.py reports no broken links; git diff --check passes; legacy-reference scan is clean outside the cleanup package; lifecycle validation recorded in verification.md.

## Phase 5: Promotion And Closure

- [~] T005 Record durable policy, final evidence, final-spec commit, compact closure breadcrumbs, and remove this temporary package.
  - Depends on: T004
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1-AC3
  - Properties: CP-003
  - Files: `docs/guides/ai-agent/`, `docs/specs/README.md`, `docs/history/`, Git history
  - Acceptance: Durable policy is promoted, Spec 002 final package is committed, closed packages are removed, and history indexes are consistent.
  - Evidence mode: validation
  - Evidence: Durable policy and navigation are promoted; compact history rows are prepared. Final-spec commit, cleanup hashes, package removal, and post-removal archive validation remain in the closure sequence.

## Execution Rules

- Use `apply_patch` for every file edit or deletion.
- Do not delete active Spec 001 or runtime code/tests/config.
- Treat Git commits as the recovery mechanism for deleted historical docs.
- Complete tasks only with concrete command, count, path, or commit evidence.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
