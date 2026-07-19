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
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008
  -> T009 -> T010 -> T011 -> T012 -> T013
```

## Phase 1: Restore Trustworthy Validation

- [x] T001 Classify live MinIO tests and repair normal CI ownership.
  - Depends on: none
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1, AC4, AC5, AC6
  - Properties: CP-001
  - Files: `pyproject.toml`, `.github/workflows/test-suite.yml`,
    `tests/TimeLocker/integration/test_s3_minio.py`,
    `tests/TimeLocker/integration/test_minio_connection.py`, MinIO fixtures
  - Acceptance: `minio` marks only live-service tests; collection performs no
    configuration failure or network access; mocked S3/MinIO contract tests
    remain in normal CI; every intended node is accounted for.
  - Validation: Complete and partitioned collection, focused mocked tests,
    `pytest -m "not performance and not stress and not minio"`.
  - Evidence: `.github/workflows/test-suite.yml:69` owns the corrected CI
    selector. Its local execution produced 2,754 successful tests and 52.13%
    coverage. Collection found 2,812 nodes: 2,755 in the CI profile, 53 in the
    performance/stress profile, and four in the live MinIO profile.
  - Status: Complete on 2026-07-18; provisioned live-service execution remains T002.
  - Evidence mode: implementation
  - [x] T001.1 Capture complete, normal, MinIO, performance, and stress collections and failing-run evidence.
    - Evidence: Full collection found 2,812 nodes; selector counts were 2,755,
      53, and four respectively. GitHub Actions run 29653160911 recorded the
      original one failure and four setup errors.
  - [x] T001.2 Register `minio` and mark only tests that contact the live service.
    - Evidence: `pyproject.toml` registers `minio`; contract test
      `test_only_live_service_tests_use_minio_marker` passed for the four named
      live-service nodes.
  - [x] T001.3 Move configuration and network access from import/collection into fixtures or runtime preflight.
    - Evidence: Clean-environment collection reported `4/2812`; runtime fixtures
      at `tests/TimeLocker/integration/test_s3_minio.py:45` and line 58 load
      settings and perform reachability checks.
  - [x] T001.4 Prove mocked MinIO contract tests remain in normal CI and collection nodes are not lost.
    - Evidence: `test_mocked_minio_contracts_remain_in_normal_profile` passed;
      the focused profile produced nine successful tests, and the full profile
      produced 2,754 successful tests at 52.13% coverage.

- [x] T002 Add and validate the provisioned MinIO profile.
  - Depends on: T001
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC2, AC3, AC6
  - Properties: CP-001
  - Files: `.github/workflows/test-suite.yml`, MinIO fixtures or preflight tests,
    `docs/4-testing/README.md`
  - Acceptance: The explicit profile provisions or validates MinIO, runs
    `pytest -m minio`, passes its tests, and reports an actionable dependency
    error when unavailable.
  - Validation: Provisioned profile plus a negative preflight test.
  - Evidence: The workflow provisions pinned MinIO image
    `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`, waits on its live
    health endpoint, creates the isolated bucket, and runs the four live nodes.
    The final local provisioned profile passed all four nodes in 20.39 seconds; the
    negative fixture contract reports the endpoint and required recovery action.
  - Status: Complete on 2026-07-18; T003 owns hosted validation.
  - Evidence mode: implementation
  - [x] T002.1 Define ephemeral endpoint and credential inputs.
    - Evidence: `.github/workflows/test-suite.yml` defines the loopback endpoint,
      disposable `timelocker-ci` credentials, bucket, region, TLS-verification,
      and log-level values in the `minio-test` job.
  - [x] T002.2 Provision MinIO and wait for readiness before pytest.
    - Evidence: The job starts the pinned container, polls
      `/minio/health/live`, creates the bucket with `boto3`, and always removes
      the container.
  - [x] T002.3 Add clear dependency-preflight failure behavior.
    - Evidence: `test_live_minio_preflight_failure_is_actionable` and
      `test_workflow_provisions_and_runs_live_minio_profile` passed, proving
      unavailable MinIO reports its endpoint and recovery action instead of
      skipping.
  - [x] T002.4 Run and record the explicit profile.
    - Evidence: A disposable local container served all four `minio` nodes;
      pytest reported four passed and 2,812 deselected.

- [x] T003 Checkpoint - CI profile validation.
  - Depends on: T002
  - Requirement: Requirement 1
  - Acceptance Criteria: Requirement 1 AC1, AC2, AC3, AC4, AC5, AC6
  - Acceptance: Normal and MinIO profiles pass, all intended test nodes are
    partitioned or intentionally shared, mocked contracts remain normal,
    coverage remains at least 50 percent, and no unrelated test is excluded.
  - Validation: GitHub Actions evidence, pytest collection partition, coverage report.
  - Evidence: GitHub Actions run `29676747955` passed at commit `8a7e1c1`:
    the normal job completed 2,760 selected nodes with 2,759 successes and
    52.15% coverage; 57 nodes were outside its selector. The provisioned MinIO
    job passed all four live nodes, and the coverage quality gate and final
    notification also passed. Full collection contains 2,817 nodes: 2,760
    normal, 53 performance/stress, and four MinIO.
  - Status: Complete on 2026-07-19; Phase 1 is complete and T004 is next.
  - Evidence mode: validation

## Phase 2: Stabilize the Extended Signal

- [ ] T004 Implement and validate the selection stress-threshold contract.
  - Depends on: T003
  - Requirement: Requirement 2
  - Acceptance Criteria: Requirement 2 AC1, AC2, AC3, AC4
  - Files: `tests/TimeLocker/selection/test_performance_stress.py`,
    `src/TimeLocker/selection_testing_harness.py`, related test tooling,
    `docs/4-testing/README.md`
  - Acceptance: Spec 007 owns the implementation and validation; deterministic
    correctness is separated from timing; a representative baseline and
    tolerance are implemented; the repeatable extended profile passes or a
    release-blocking disposition is recorded.
  - Evidence mode: implementation
  - Destination: <https://github.com/Auriora/TimeLocker/issues/68>
  - Evidence: Pending.
  - [ ] T004.1 Capture representative host timings and environment context in issue #68.
  - [ ] T004.2 Separate deterministic correctness assertions from environment-sensitive timing assertions.
  - [ ] T004.3 Implement the evidence-backed baseline and tolerance strategy.
  - [ ] T004.4 Run a repeatable extended profile and link results from issue #68.

- [ ] T005 Checkpoint - Release validation prerequisites.
  - Depends on: T004
  - Requirements: Requirements 1 and 2
  - Acceptance: Normal CI is green, explicit external-service coverage is
    green, Spec 007 stress acceptance is met, and issue #68 contains linked
    evidence or an explicit release-blocking disposition.
  - Validation: Review T003 and T004 evidence and the linked issue history.
  - Evidence: Pending.

## Phase 3: Build and Install v0.9.1

- [ ] T006 Prepare version `0.9.1` safely and build reproducible artifacts.
  - Depends on: T005
  - Requirement: Requirement 3
  - Acceptance Criteria: Requirement 3 AC1, AC2, AC3, AC4, AC5
  - Properties: CP-002, CP-004
  - Files: `pyproject.toml`, `src/TimeLocker/__init__.py`,
    `scripts/bump_version.py`, `.bumpversion.cfg`, build and release tooling
  - Acceptance: The non-publishing version command changes only versioned
    working-tree files; commit, tag, and GitHub-release identity remain
    unchanged; version sources, sdist, wheel, metadata, entry points, package
    data, and SHA-256 hashes validate from a clean source baseline.
  - Validation: Pre/post Git and release-state comparison,
    `python scripts/bump_version.py bump patch --no-commit --no-tag`, version
    guard, `python -m build`, artifact inspection.
  - Evidence: Pending.
  - [ ] T006.1 Record pre-change commit, tag, tag-triggered release-workflow run, and GitHub-release identity.
  - [ ] T006.2 Run the version helper with both commit and tag side effects disabled.
  - [ ] T006.3 Update `requires-python` to `>=3.12,<3.14`, remove `OS Independent`, and reconcile Python and OS classifiers.
  - [ ] T006.4 Build sdist and wheel once; inspect metadata, contents, entry points, and hashes.
  - [ ] T006.5 Prove a version mismatch blocks the guard and prove commit, tag, tag-triggered release-workflow run, and release identity did not change.

- [ ] T007 Validate wheel and sdist across the declared support matrix.
  - Depends on: T006
  - Requirement: Requirement 4
  - Acceptance Criteria: Requirement 4 AC1, AC2, AC3, AC4, AC5
  - Properties: CP-003
  - Files: `.github/workflows/`, smoke tooling,
    `docs/guides/user/installation.md`, `pyproject.toml`
  - Acceptance: Wheel and sdist pass the shared CLI smoke contract on Linux,
    macOS, and Windows for Python 3.12 and 3.13; an unvalidated combination
    blocks readiness until its support claim is corrected and reviewed.
  - Validation: Six OS/Python combinations, both artifact types, both console entry points.
  - Evidence: Pending.
  - [ ] T007.1 Add or reconcile the six-combination Linux/macOS/Windows and Python 3.12/3.13 smoke matrix.
  - [ ] T007.2 Install the wheel and run version, root help, and safe quick-start smoke checks in every combination.
  - [ ] T007.3 Install the sdist and run the identical smoke contract in every combination.
  - [ ] T007.4 Record platform prerequisites and correct any support claim that cannot be validated.

- [ ] T008 Checkpoint - Artifact and installation readiness.
  - Depends on: T007
  - Requirements: Requirements 3 and 4
  - Acceptance: Side-effect safety, artifact identity, hashes, six-combination
    installation results, platform coverage, and residual risk are recorded
    before release rehearsal.
  - Validation: Review artifact and clean-install evidence against CP-002, CP-003, and CP-004.
  - Evidence: Pending.

## Phase 4: Rehearse, Promote, and Review

- [ ] T009 Implement a safe pre-tag validation interface.
  - Depends on: T008
  - Requirement: Requirement 5
  - Acceptance Criteria: Requirement 5 AC1, AC5
  - Properties: CP-004
  - Files: `.github/workflows/release.yml`, release validation scripts or tests
  - Acceptance: A reusable pre-tag path validates release inputs and steps but
    contains no commit, tag, release, or package-index publication action.
  - Evidence mode: implementation
  - Validation: Workflow syntax, focused script tests, publication-boundary review.
  - Evidence: Pending.
  - [ ] T009.1 Identify and isolate every pre-publication release step.
  - [ ] T009.2 Implement a manual or local validation entry point with read-only permissions.
  - [ ] T009.3 Add regression coverage for the publication boundary and failure propagation.

- [ ] T010 Execute and record a non-publishing release rehearsal.
  - Depends on: T009
  - Requirement: Requirement 5
  - Acceptance Criteria: Requirement 5 AC1, AC4, AC5
  - Properties: CP-004
  - Files: `verification.md`, workflow-run or local rehearsal evidence
  - Acceptance: Build, smoke, artifact configuration, permissions, and failure
    paths are exercised; pre/post commit, tag, and GitHub-release identity are
    unchanged; no external publication occurs.
  - Evidence mode: validation
  - Validation: Non-publishing rehearsal and external-state comparison.
  - Evidence: Pending.
  - [ ] T010.1 Capture pre-rehearsal commit, tag, release, and permission state.
  - [ ] T010.2 Exercise successful build, smoke, artifact, and release-note inputs.
  - [ ] T010.3 Exercise version mismatch, missing prerequisite, and permission failure paths.
  - [ ] T010.4 Capture unchanged post-rehearsal external state and link all logs.

- [ ] T011 Update existing durable release and installation procedures.
  - Depends on: T010
  - Requirements: Requirements 4 and 5
  - Acceptance Criteria: Requirement 4 AC3, AC4, AC5; Requirement 5 AC2, AC5
  - Files: `docs/processes/version-management.md`, `docs/processes/README.md`,
    `docs/guides/user/installation.md`, `README.md` if required
  - Acceptance: The existing version-management procedure documents the safe
    preparation command, authorized publication boundary, checks, failure and
    rollback handling, and is indexed; installation guidance reflects only
    the validated support matrix and prerequisites.
  - Evidence mode: implementation
  - Validation: Procedure review, Markdown and internal-link checks, command review.
  - Evidence: Pending.
  - [ ] T011.1 Correct `version-management.md` in place; do not create a duplicate release procedure.
  - [ ] T011.2 Link the procedure from `docs/processes/README.md`.
  - [ ] T011.3 Update installation and front-door claims from T007 evidence.

- [ ] T012 Prepare evidence-backed `v0.9.1` communications.
  - Depends on: T011
  - Requirement: Requirement 5
  - Acceptance Criteria: Requirement 5 AC3, AC5, AC6
  - Properties: CP-005
  - Files: `CHANGELOG.md`, GitHub release-body input or derivation tooling
  - Acceptance: The `v0.9.1` changelog section is the single checked-in
    canonical release-note source; every claim maps to evidence or a known
    limitation; the eventual GitHub release body is derived from that section.
  - Evidence mode: implementation
  - Validation: Claim-to-evidence review and release-body derivation preview.
  - Evidence: Pending.
  - [ ] T012.1 Draft the changelog section from verified changes and limitations.
  - [ ] T012.2 Map each public claim to verification, commits, specs, or issues.
  - [ ] T012.3 Preview the GitHub release body without creating a release.

- [ ] T013 Checkpoint - Human release decision and spec closure readiness.
  - Depends on: T012
  - Requirements: Requirement 1, Requirement 2, Requirement 3, Requirement 4,
    Requirement 5
  - Acceptance: All required evidence is linked; durable content is promoted;
    residual risks and owners are explicit; no commit, tag, GitHub release, or
    PyPI publication was created by preparation or rehearsal; and the package
    is ready for separate human release approval and lifecycle closure.
  - Decision owner: release maintainer
  - Validation: Lifecycle lint, readiness, traceability and evidence checks,
    required test profiles, Markdown and internal-link checks,
    `git diff --check`, security and release-readiness expert review.
  - Evidence: Pending.

## Execution Rules

- Read the linked row in `traceability.md` and the relevant requirements,
  design, change-impact, and verification sections before starting a task.
- Mark a selected task `[~]` before implementation and record evidence before
  marking it `[x]`.
- Do not create a commit, production tag, GitHub release, or PyPI publication
  as a side effect of version preparation or rehearsal. A normal task commit
  may occur only after validation and separate explicit commit instruction;
  tagging and publication always require separate release approval.
- Spec 007 owns stress-threshold scope, implementation, sequencing,
  acceptance, and validation. GitHub issue #68 tracks assignment, state, and
  chronological evidence.
- A failed prerequisite blocks downstream release tasks; it is not waived by
  reducing test or support scope without an approved spec reconciliation.

## Rules Consulted

Rules consulted and applied: General Preferences (priority 50), Operational
Best Practices (priority 40), Planning Protocol (priority 30), Testing
Conventions (priority 25), and Documentation Conventions (priority 20).
Override: the user already approved remediation by requesting that the review
findings be addressed, so no repeated approval gate was required.
Final downstream review confirmed these tasks implement the reconciled
requirements and design, including the changelog-derived communications model.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Design: `design.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
