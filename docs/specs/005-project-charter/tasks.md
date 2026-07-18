---
title: Project charter tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

**Input:** `docs/specs/005-project-charter/`
**Approval:** User approved the charter plan and Auriora Team ownership on
2026-07-18.
**Design review:** Task scope and file boundaries were reviewed against the
final design on 2026-07-18; no task changes were required.

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004
```

## Phase 1: Lifecycle Baseline

- [x] T001 Establish the approved documentation-only charter package.
  - Depends on: none
  - Requirements: Requirement 1-4, CP-003
  - Files: `docs/specs/005-project-charter/`, active-spec inventory
  - Acceptance: Core artifacts are coherent, Spec 005 is explicitly
    documentation-only, and Spec 001 remains ready at T005.
  - Evidence mode: validation
  - Evidence: For `docs/specs/005-project-charter`, `lint_spec_package` returned error=0, warn=0, info=0 and `stage_readiness` returned blocking_gap_count=0, downstream_review_need_count=0, acceptance_gap_count=0.

## Phase 2: Durable Charter

- [x] T002 Create the enduring TimeLocker project charter.
  - Depends on: T001
  - Requirements: Requirement 1-3, CP-001, CP-002
  - Files: `CHARTER.md`
  - Acceptance: The charter defines mandate, users, principles, scope,
    exclusions, governance, success measures, authority, and next steps without
    future-only claims or invented individual ownership.
  - Evidence mode: implementation
  - Evidence: Created root `CHARTER.md` with mandate, audiences, seven operating principles, current scope, seven explicit exclusions, responsibility boundaries, role-based governance, six success measures, authority order, change rules, and reader next paths; Agent Workbench reported zero Markdown findings.

- [x] T003 Align repository authority links without duplicating the charter.
  - Depends on: T002
  - Requirements: Requirement 4, CP-002, CP-003
  - Files: `README.md`, `docs/README.md`, `AGENTS.md`, Spec 001 requirements
  - Acceptance: Entry points route to the charter; Spec 001 stays subordinate
    and retains its approved implementation scope and next task.
  - Evidence mode: implementation
  - Evidence: Added charter authority links to `README.md`, `docs/README.md`, `AGENTS.md`, and the Spec 001 durable baseline; `docs/specs/README.md` records non-blocking coexistence; Spec 001 lint returned error=0, warn=0, info=0 and readiness returned blocking_gap_count=0 with T005 unchanged.

## Phase 3: Validation And Closure

- [~] T004 Validate, promote, and close Spec 005.
  - Depends on: T003
  - Requirements: Requirement 1-4, CP-001-CP-003, SC-001-SC-004
  - Files: all changed documents, lifecycle history and indexes
  - Acceptance: Documentation and lifecycle checks pass, all lasting content is
    durable, the final package state is committed, and Spec 005 is removed with
    a valid closure record.
  - Evidence mode: validation
  - Evidence: Running documentation, duplication, lifecycle, promotion, closure, and Git validation before the final active-state commit.
  - [x] T004.1 Run Markdown, link, duplication, and Git checks.
  - Evidence: `python scripts/link_checker.py` and `git diff --check` exited 0; Agent Workbench reported 0 findings for `CHARTER.md` and 0 findings across the five changed front-door/authority documents; `rg` found detailed charter authority headings only in `CHARTER.md`.
  - Evidence mode: validation
  - [x] T004.2 Run Spec 005 and Spec 001 lifecycle checks.
  - Evidence: Spec 005 `lint_spec_package` returned error=0, warn=0, info=0 and readiness gap counts=0; Spec 001 returned the same clean lint/readiness signals with T005 unchanged and ready.
  - Evidence mode: validation
  - [ ] T004.3 Commit the final active package state.
  - [ ] T004.4 Remove the package and record closure metadata.

## Execution Rules

- Do not change TimeLocker runtime code, tests, configuration, or packaging.
- Do not change Spec 001 tasks, acceptance criteria, or sequencing.
- Keep mandate and governance details in `CHARTER.md`; use links elsewhere.
- Prefer role ownership over an invented individual name.
- Remove this package after durable promotion and final-state commit.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Change Impact: `change-impact.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
