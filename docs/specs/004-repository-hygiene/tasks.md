---
title: Repository hygiene tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

**Input**: `docs/specs/004-repository-hygiene/`
**Prerequisites**: approved requirements and design; reconciled Spec 001

## Task Dependency Graph

```text
T001 -> T002 -> T003
T002 -> T004
T003 + T004 -> T005 -> T006
```

## Phase 1: Baseline And Authority

- [x] T001 Reconcile Spec 001 and establish the bounded cleanup baseline.
  - Depends on: none
  - Requirements: Requirement 4 AC1, CP-003
  - Files: `docs/specs/001-cli-consolidation-stabilization/`, repository inventory
  - Acceptance: Spec 001 decisions, acceptance mappings, downstream reviews,
    and the Spec 004 prerequisite are explicit; lifecycle readiness has no gaps.
  - Evidence mode: validation
  - Evidence: 2026-07-18 lifecycle lint, readiness, and task audit passed with
    zero findings; D001 and D002 were resolved from current code and tests.

- [x] T002 Establish one current agent-instruction authority.
  - Depends on: T001
  - Requirements: Requirement 1 AC1-AC3, CP-001
  - Files: `AGENTS.md`, `.kiro/steering/`, `docs/guides/ai-agent/`
  - Acceptance: The minimal router and centralized TimeLocker-specific rules do
    not duplicate or contradict one another; MCP settings remain.
  - Evidence mode: implementation
  - Evidence: `rg` scans returned zero active copied-project or forbidden-directory references; `.kiro/settings/mcp.json` remains and all seven tracked `.kiro/steering/` files are deleted.
  - [x] T002.1 Remove the forbidden updates-directory instruction from
    `AGENTS.md`.
  - Evidence: Removed the forbidden docs/updates instruction; AGENTS.md now routes evidence to lifecycle and Git artifacts.
  - Evidence mode: implementation
  - [x] T002.2 Remove tracked `.kiro/steering/` duplicates while preserving
    `.kiro/settings/mcp.json`.
  - Evidence: Removed all tracked .kiro/steering duplicates and preserved .kiro/settings/mcp.json.
  - Evidence mode: implementation
  - [x] T002.3 Rewrite copied coding, operations, and testing guidance for the
    actual TimeLocker stack and paths.
  - Evidence: Rewrote coding, operational, testing, and agent-index guidance for Python 3.12+, pytest, Typer, current docs, and exact rule filenames.
  - Evidence mode: implementation
  - [x] T002.4 Validate the rule set and scan for stale copied terms.

  - Evidence: `rg` scans for admin-assistant, Microsoft 365, Vitest, Flask, SQLAlchemy, the nonexistent logging guide, and legacy active directories returned zero active rule conflicts.
  - Evidence mode: implementation
## Phase 2: Front Door And Durable Organization

- [x] T003 Repair repository front doors and canonical resource paths.
  - Depends on: T002
  - Requirements: Requirement 2 AC1-AC3, CP-001, CP-002
  - Files: `README.md`, `CHANGELOG.md`, `docs/resources/`, scripts and consumers
  - Acceptance: Current links, structure, coverage policy, assets, and script
    inputs agree with the repository.
  - Evidence mode: implementation
  - Evidence: `python scripts/link_checker.py` reported zero broken links; `docs/resources/restic_commands.json` loaded 37 records through the updated conversion script.
  - [x] T003.1 Rewrite stale README and changelog references.
  - Evidence: `python scripts/link_checker.py` reported zero broken links; README.md now states the 50 percent pyproject.toml coverage gate and both front doors reference current paths.
  - Evidence mode: implementation
  - [x] T003.2 Move documentation assets to `docs/resources/`.
  - Evidence: `docs/resources/` contains `restic_commands.json`, `images/infra.dot`, and `images/infra.svg`; the former hidden `docs/.resources/` files are deleted.
  - Evidence mode: implementation
  - [x] T003.3 Update all tracked resource consumers and validate their paths.

  - Evidence: `scripts/json2command_definition/json2command_definition.py` loaded all 37 records and built the command definition from `docs/resources/restic_commands.json`; both conversion scripts resolve the canonical directory.
  - Evidence mode: implementation
- [x] T004 Consolidate durable templates and remove historical clutter.
  - Depends on: T002
  - Requirements: Requirement 3 AC1-AC3, CP-001
  - Files: `docs/templates/`, scattered `_template` files,
    `docs/troubleshooting/pickle-error-investigation.md`, empty legacy directories
  - Acceptance: Current template guidance is centralized, the obsolete
    investigation is removed after validation, and legacy directories are gone.
  - Evidence mode: implementation
  - Evidence: The inventory shows four central templates, 16 deleted scattered template files, zero legacy discovery directories, and 25 passing CredentialManager tests.
  - [x] T004.1 Validate the durable pickle behavior and remove or rewrite the
    investigation according to the result.
  - Evidence: CredentialManager pickle round trip passed and all 25 credential-manager tests passed with --no-cov; removed the obsolete investigation plan.
  - Evidence mode: implementation
  - [x] T004.2 Create the compact central template set and update references.
  - Evidence: Created `docs/templates/durable-document.md`, `decision-record.md`, `test-plan.md`, and `agent-instruction.md`; section README links pass `python scripts/link_checker.py`.
  - Evidence mode: implementation
  - [x] T004.3 Remove redundant template files and empty legacy directories.

  - Evidence: Git records 16 scattered template deletions; directory inventory returned zero empty legacy plans, updates, archive, reports, issues, traceability, troubleshooting, project-management, or old template directories.
  - Evidence mode: implementation
## Phase 3: Verification, Promotion, And Closure

- [x] T005 Run repository and lifecycle validation and resolve findings.
  - Depends on: T003, T004
  - Requirements: Requirement 1, Requirement 2, Requirement 3, Requirement 4,
    CP-001, CP-002, CP-003, SC-001, SC-002, SC-003
  - Files: all changed files, `verification.md`
  - Acceptance: Required focused, documentation, lifecycle, diff, and regression
    checks pass or an exact pre-existing limitation is recorded.
  - Evidence mode: validation
  - Evidence: Focused resource/pickle checks, documentation and stale-reference checks, lifecycle lint, patch integrity, and regression validation passed; exact commands and results are recorded in verification.md.
  - [x] T005.1 Run focused resource and pickle checks.
  - Evidence: Loaded 37 canonical Restic resource records and built the command definition; CredentialManager pickle round trip passed and pytest --no-cov -q tests/TimeLocker/security/test_credential_manager.py reported 25 passed.
  - Evidence mode: validation
  - [x] T005.2 Run Markdown, link, stale-reference, and Git checks.
  - Evidence: python scripts/link_checker.py and git diff --check passed; Agent Workbench found zero root, durable-doc, and template findings; stale-path, copied-project, scattered-template, empty-directory, and tracked-steering scans found no active leftovers.
  - Evidence mode: validation
  - [x] T005.3 Run lifecycle lint, readiness, evidence, and task-state audits.
  - Evidence: Spec Lifecycle Manager stage readiness returned blocking_gap_count=0 and downstream_review_need_count=0; package lint returned error=0, warn=0, info=0; task audit returned error=0 and warn=0.
  - Evidence mode: validation
  - [x] T005.4 Run the full test suite and record the result.

  - Evidence: The functional pytest selection reported 2730 passed with 51.83 percent coverage; the serial performance/stress selection reported 49 passed, and the isolated startup class reported 5 passed in 1.30 seconds.
  - Evidence mode: validation
- [~] T006 Promote accepted governance and close Spec 004.
  - Depends on: T005
  - Requirements: Requirement 4 AC2, CP-003
  - Files: durable docs, lifecycle history, Specs 001 and 004
  - Acceptance: No accepted behavior remains spec-only; closure history and
    indexes are current; Spec 004 is removed or archived; Spec 001 is ready.
  - Evidence mode: implementation
  - Evidence: Promotion targets are present in durable documentation; executing final active-state commit and lifecycle-history cleanup.
  - [x] T006.1 Complete promotion and closure-risk reviews.
  - Evidence: Promotion plan returned target_count=10 and missing_target_count=0; closure-risk signals returned decision_count=0 and stale_candidate_count=0; verification.md records low risk and Git-history rollback.
  - Evidence mode: validation
  - [ ] T006.2 Commit the final active package state.
  - [ ] T006.3 Record closure, update indexes, and remove the temporary package.
  - [ ] T006.4 Validate the post-closure active-spec state and commit metadata.

## Execution Rules

- Read the complete package context before changing a task state.
- Keep task and subtask markers synchronized with evidence.
- Do not implement Spec 001 product tasks while Spec 004 is active.
- Treat historical Git content as recoverable; do not recreate update diaries or
  legacy archive directories.
- Use the installed lifecycle tools for readiness, task state, evidence,
  promotion, and closure checks.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
