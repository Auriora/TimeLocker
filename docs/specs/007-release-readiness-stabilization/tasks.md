---
title: Release readiness stabilization tasks
doc_type: spec
artifact_type: tasks
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Tasks

**Input:** `docs/specs/007-release-readiness-stabilization/`

## Task Dependency Graph

```text
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010
```

## Phase 1: Restore Trustworthy Validation

- [ ] T001 Repair normal CI ownership of MinIO integration tests.
  - Depends on: none
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1, AC2, AC4
  - Properties: CP-001
  - Files: `.github/workflows/test-suite.yml`, pytest marker or fixture files,
    `tests/TimeLocker/integration/`
  - Acceptance: Normal CI does not contact an unprovisioned MinIO endpoint,
    unrelated test coverage is retained, and collection-count evidence is
    recorded.
  - Validation: Focused MinIO collection, normal pytest profile, workflow run.
  - Evidence: Pending.
  - [ ] T001.1 Capture current normal and MinIO test collections and failing-run evidence.
  - [ ] T001.2 Add an explicit MinIO dependency classification without hiding other integration tests.
  - [ ] T001.3 Update normal CI selection and add regression coverage for profile ownership.
  - [ ] T001.4 Run the normal profile locally and in GitHub Actions.

- [ ] T002 Add and validate the provisioned MinIO profile.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC2, AC3
  - Properties: CP-001
  - Files: `.github/workflows/test-suite.yml`, MinIO fixtures or preflight tests,
    `docs/4-testing/`
  - Acceptance: The explicit profile provisions or validates MinIO, passes its
    tests, and reports an actionable dependency error when unavailable.
  - Validation: Provisioned profile plus a negative preflight test.
  - Evidence: Pending.
  - [ ] T002.1 Define ephemeral endpoint and credential inputs.
  - [ ] T002.2 Provision MinIO and wait for readiness before pytest.
  - [ ] T002.3 Add clear dependency-preflight failure behavior.
  - [ ] T002.4 Run and record the explicit profile.

- [ ] T003 Checkpoint - CI profile validation.
  - Depends on: T002
  - Requirement: Requirement 1
  - Acceptance: Normal and MinIO profiles pass, collected-test drift is
    explained, coverage remains at least 50 percent, and no unrelated tests are
    excluded.
  - Validation: GitHub Actions evidence, pytest collection comparison, coverage report.
  - Evidence: Pending.

## Phase 2: Stabilize the Extended Signal

- [ ] T004 Verify completion of the selection stress-threshold work in GitHub issue #68.
  - Depends on: T003
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, AC2, AC3
  - Files: GitHub issue #68 and affected stress tests; implementation remains
    owned by the issue to avoid duplicate active work.
  - Acceptance: Issue #68 contains representative timings, separated
    correctness and timing semantics, the chosen regression strategy, and a
    repeatable validation result or an explicit release-blocking disposition.
  - Evidence mode: validation
  - Destination: <https://github.com/Auriora/TimeLocker/issues/68>
  - Evidence: Pending.

- [ ] T005 Checkpoint - Release validation prerequisites.
  - Depends on: T004
  - Requirements: Requirements 1 and 2
  - Acceptance: Normal CI is green, explicit external-service coverage is
    green, and stress evidence is acceptable for release preparation.
  - Validation: Review T003 evidence and issue #68 acceptance criteria.
  - Evidence: Pending.

## Phase 3: Build and Install v0.9.1

- [ ] T006 Set version `0.9.1` and build reproducible release artifacts.
  - Depends on: T005
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1, AC2, AC3, AC4
  - Properties: CP-002
  - Files: `pyproject.toml`, `src/TimeLocker/__init__.py`, build and release tooling
  - Acceptance: Version sources agree; sdist, wheel, metadata, entry points,
    package data, and SHA-256 hashes validate from a clean checkout.
  - Validation: Version guard, `python -m build`, artifact inspection.
  - Evidence: Pending.
  - [ ] T006.1 Update and test all authoritative version sources.
  - [ ] T006.2 Build sdist and wheel once from a clean source state.
  - [ ] T006.3 Inspect metadata, contents, entry points, and hashes.
  - [ ] T006.4 Prove a version mismatch blocks the release guard.

- [ ] T007 Validate wheel and sdist in clean supported environments.
  - Depends on: T006
  - Requirement: Requirement 4
  - Acceptance Criteria: Requirement 4 AC1, AC2, AC3, AC4
  - Properties: CP-003
  - Files: `.github/workflows/`, smoke tooling, `docs/guides/user/installation.md`
  - Acceptance: Both artifact types pass the shared CLI smoke contract on the
    supported Python and OS matrix, or unsupported claims are corrected and
    reviewed before proceeding.
  - Validation: Fresh-environment installs for wheel and sdist; both console entry points.
  - Evidence: Pending.
  - [ ] T007.1 Reconcile Python and OS claims from metadata, workflows, and docs.
  - [ ] T007.2 Install wheel and run version, root help, and safe quick-start smoke checks.
  - [ ] T007.3 Install sdist and run the same smoke contract.
  - [ ] T007.4 Record or correct platform prerequisites and limitations.

- [ ] T008 Checkpoint - Artifact and installation readiness.
  - Depends on: T007
  - Requirements: Requirements 3 and 4
  - Acceptance: Artifact identity, hashes, installation results, platform
    coverage, and residual risk are recorded before release rehearsal.
  - Validation: Review artifact and clean-install evidence against CP-002 and CP-003.
  - Evidence: Pending.

## Phase 4: Rehearse, Promote, and Review

- [ ] T009 Rehearse the release workflow and promote durable release guidance.
  - Depends on: T008
  - Requirement: Requirement 5
  - Acceptance Criteria: Requirement 5 AC1, AC2, AC3, AC4, AC5
  - Properties: CP-004, CP-005
  - Files: `.github/workflows/release.yml`, `CHANGELOG.md`, release notes,
    `docs/processes/`, `docs/guides/user/installation.md`, `README.md`
  - Acceptance: Every pre-publication release step is validated without a
    production tag; durable operator and user guidance and evidence-backed
    `v0.9.1` communications are complete; PyPI and `1.0.0` remain deferred.
  - Validation: Workflow validation, non-publishing rehearsal, links and docs review.
  - Evidence: Pending.
  - [ ] T009.1 Establish one safe pre-tag validation command or workflow path.
  - [ ] T009.2 Rehearse build, smoke, artifact, permissions, and failure paths without publishing.
  - [ ] T009.3 Write the durable release operator procedure and rollback boundary.
  - [ ] T009.4 Update installation guidance, changelog, and `v0.9.1` release notes.
  - [ ] T009.5 Perform release-readiness documentation and security review.

- [ ] T010 Checkpoint - Human release decision and spec closure readiness.
  - Depends on: T009
  - Requirements: Requirements 1 through 5
  - Acceptance: All required evidence is linked; durable content is promoted;
    residual risks and owners are explicit; no tag or release has been created;
    and the package is ready for human release approval and lifecycle closure.
  - Validation: Lifecycle lint, readiness and traceability checks, full required
    test profiles, internal-link check, `git diff --check`, expert review.
  - Evidence: Pending.

## Execution Rules

- Read the linked row in `traceability.md` and the relevant requirements,
  design, change-impact, and verification sections before starting a task.
- Mark a selected task `[~]` before implementation and record evidence before
  marking it `[x]`.
- Do not create a production tag, GitHub release, or PyPI publication under
  this package without a separate explicit release approval.
- GitHub issue #68 owns stress-threshold implementation; T004 consumes and
  verifies its evidence rather than restating its engineering work.
- A failed prerequisite blocks downstream release tasks; it is not waived by
  reducing test or support scope without an approved spec reconciliation.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
