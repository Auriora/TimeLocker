---
title: Repository safety and release readiness tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008
```

- [x] T001 Establish the remediation package and active-spec sequencing.
  - Depends on: none
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5
  - Files: `docs/specs/002-repository-safety-release-readiness/`, `docs/specs/README.md`
  - Acceptance: Package maps all five accepted findings and explicitly pauses Spec 001 at T005.
  - Evidence: `scan_specs` found the complete seven-artifact package and `lint_spec_package` returned 0 errors and 0 warnings on 2026-07-18; `docs/specs/README.md` records the Spec 002 preemption boundary.

- [x] T002 Enforce non-destructive restore execution by default.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1, Requirement 1 AC2, Requirement 1 AC3
  - Properties: CP-001
  - Files: restore CLI, orchestrator, snapshot/repository contracts, Restic adapter, focused tests
  - Acceptance: Restic always receives `never` unless explicit authorization reaches execution as `always`.
  - Evidence: Restore contract and Restic adapter emit explicit `never`/`always`; 66-test restore/security focused run passed on 2026-07-18.

- [x] T003 Remove deterministic credential auto-unlock.
  - Depends on: T002
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, Requirement 2 AC2, Requirement 2 AC3
  - Properties: CP-002
  - Files: `src/TimeLocker/security/credential_manager.py`, focused tests, credential guide
  - Acceptance: Only explicit environment or protected-file secrets unlock non-interactively.
  - Evidence: `python -m pytest` focused on restore, Restic, and credential-manager tests returned 66 passed; explicit-secret, missing-file, empty-file, directory, permissions, and symlink cases also passed in the 2,743-test regression run.

- [x] T004 Normalize the test package identity.
  - Depends on: T003
  - Requirement: Requirement 4
  - Acceptance Criteria: Requirement 4 AC1, Requirement 4 AC2
  - Properties: CP-003
  - Files: `tests/**/*.py`
  - Acceptance: No Python test imports or patches `src.TimeLocker`; a guard prevents recurrence.
  - Evidence: All Python test imports/patch targets normalized; guard plus representative CLI/service tests passed (48 tests) on 2026-07-18.

- [x] T005 Repair installation and release automation.
  - Depends on: T004
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1, Requirement 3 AC2, Requirement 3 AC3
  - Properties: CP-004
  - Files: `.github/workflows/release.yml`, `README.md`, installation/release docs, `pyproject.toml`
  - Acceptance: Source install is truthful and the tag workflow tests, builds, smokes, and attaches Python artifacts.
  - Evidence: Python workflow and durable guidance implemented; source/wheel build and isolated wheel install/import/CLI smoke passed at version 0.9.0 on 2026-07-18; missing runtime `psutil` declaration found and fixed.

- [x] T006 Rewrite durable architecture docs to current state.
  - Depends on: T005
  - Requirement: Requirement 5
  - Acceptance Criteria: Requirement 5 AC1, Requirement 5 AC2, Requirement 5 AC3
  - Files: `docs/2-architecture/system-architecture.md`, `component-breakdown.md`, `data-flow.md`, related indexes
  - Acceptance: Durable architecture omits future-only components, unsupported backends, and orphan requirement IDs.
  - Evidence: Current-state architecture set rewritten; unimplemented sections and orphan mappings removed across `docs/2-architecture/`; the 21-document parser check and `python scripts/link_checker.py` completed successfully on 2026-07-18.

- [x] T007 Run focused and full verification and perform final expert review.
  - Depends on: T006
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5
  - Properties: CP-001-CP-004
  - Files: changed source/tests/docs, `verification.md`
  - Acceptance: Required tests, build smoke, diagnostics, Markdown/link checks, lifecycle checks, and review are recorded.
  - Evidence: `pytest` returned 2,743 passed with 51.89% coverage; build, wheel smoke, compile, YAML, link, guard, lifecycle, and seven expert-perspective gates passed on 2026-07-18.

- [x] T008 Promote lasting behavior and prepare lifecycle closure.
  - Depends on: T007
  - Requirement: Requirement 1, Requirement 2, Requirement 3, Requirement 4, Requirement 5
  - Files: durable targets, package artifacts, active-spec and documentation-status indexes
  - Acceptance: Durable docs are current, residual risks are routed, Spec 001 may resume, and closure is ready for a separately authorized commit-backed step.
  - Evidence: All promotion targets are checked in `change-impact.md`; `docs/specs/README.md` releases Spec 001 to resume at T005; lifecycle lint is clean and the package is ready for its final commit-backed closure step.

## Execution Rules

- Spec 002 preempts Spec 001; do not advance Spec 001 while T002-T007 run.
- Mark a task `[~]` before implementation and `[x]` only with recorded evidence.
- Do not publish to PyPI or create a GitHub release during implementation.
- Do not restore deterministic auto-unlock as a compatibility fallback.
- Closure requires a final spec commit before package removal; no commit is
  authorized by the current request.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
