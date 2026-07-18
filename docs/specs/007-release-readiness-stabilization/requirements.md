---
title: Release readiness stabilization requirements
doc_type: spec
artifact_type: requirements
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Requirements

## Introduction

TimeLocker is versioned as `0.9.0`, has no published release tags, and its
normal GitHub Actions test profile currently fails because MinIO integration
tests run without a reachable MinIO service. The next milestone is a bounded
`v0.9.1` stabilization release that restores trustworthy CI, validates built
artifacts in clean environments, rehearses the tag-triggered release path, and
publishes evidence-backed release notes.

## Goals

- Restore a green, deterministic normal CI profile without silently discarding
  MinIO integration coverage.
- Stabilize the separate selection stress signal tracked by GitHub issue #68.
- Build and validate source and wheel artifacts for version `0.9.1`.
- Prove the supported installation and CLI smoke paths in clean environments.
- Rehearse the release workflow without creating a production tag.
- Produce accurate changelog-derived release communications and operator documentation.

## Non-Goals

- Publishing to PyPI or configuring PyPI credentials or trusted publishing.
- Declaring TimeLocker `1.0.0` or promising a stable public Python API.
- Implementing unrelated feature, CLI, configuration, or performance backlog.
- Creating a release tag or GitHub release during implementation rehearsal.
- Weakening tests, coverage, or supported-platform claims to obtain a pass.

## Glossary

| Term | Definition |
|------|------------|
| Normal CI | The test profile run for pushes and pull requests: tests excluding the `performance`, `stress`, and `minio` markers. |
| MinIO profile | Tests marked `minio` that contact an explicitly provisioned S3-compatible MinIO endpoint. Mocked S3/MinIO contract tests remain in normal CI. |
| Release rehearsal | Non-publishing validation of the release workflow, commands, inputs, artifacts, and permissions. |
| Release evidence | CI runs, commands, artifact metadata, hashes, install results, and review records supporting a release decision. |
| Release notes | The eventual GitHub release body derived from the canonical `v0.9.1` section in `CHANGELOG.md`, not a separate durable document. |

## Durable Source Baseline

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `CHARTER.md` | TimeLocker is a local-first CLI and is not currently distributed through PyPI. | high | Product and distribution boundary. |
| `README.md` | Version, installation, test, and project maturity front door. | high | Must remain aligned with verified behavior. |
| `pyproject.toml` | Package version, Python support, dependencies, console scripts, test markers, and coverage configuration. | high | Authoritative build metadata. |
| `.github/workflows/test-suite.yml` | Normal and manually dispatched extended test profiles. | high | Normal CI currently lacks MinIO provisioning or isolation. |
| `.github/workflows/release.yml` | Tag-triggered version check, tests, build, smoke install, artifact upload, and GitHub release. | high | Exists but has not been exercised by a repository release. |
| `scripts/bump_version.py` and `.bumpversion.cfg` | The version helper commits and tags by default unless both side effects are disabled. | high | Release preparation must use `--no-commit --no-tag`. |
| `docs/guides/user/installation.md` | Current installation and validation guidance. | high | Promotion target for verified clean-install behavior. |
| `docs/processes/version-management.md` | Current version-bump and release procedure. | high | Must be corrected in place and linked from the process index. |
| `docs/processes/README.md` | Durable process index. | high | Must link the corrected version-management procedure. |
| `CHANGELOG.md` | Durable project change history. | high | Target for the `v0.9.1` entry. |
| `docs/history/spec-closure-log.md` | Records the waived selection stress threshold from Spec 001. | high | Follow-up is GitHub issue #68. |

## Durable Impact

See `change-impact.md`. This spec modifies test workflow behavior, package
version metadata, installation guidance, the release process, and release
communications. It does not change product architecture or the supported
credential model.

## Staged Readiness

- **Current stage:** implementation-ready
- **Next stage:** implementation
- **Ready to implement when:** package lint, traceability, task dependency, and
  agent-readiness checks pass.
- **Design-first exception:** no
- **Optional artifacts included:** `change-impact.md`, `verification.md`,
  `traceability.md`
- **Downstream review needed:** verification and release readiness

## Requirements

### Requirement 1: Deterministic CI profiles

**User Story:** As a maintainer, I want normal CI to exercise only tests whose
dependencies it provisions, so that a green result is a trustworthy release
signal and integration coverage remains explicit.

#### Acceptance Criteria

1. GIVEN a push or pull request, WHEN normal CI runs, THEN it SHALL complete
   without attempting to contact an unprovisioned MinIO endpoint.
2. WHERE MinIO integration tests are retained, THE SYSTEM SHALL provide an
   explicit profile that provisions or validates MinIO before those tests run.
3. IF the MinIO service is unavailable in its explicit profile, THEN the job
   SHALL fail with a clear dependency error rather than an ambiguous test
   failure or silent skip.
4. THE SYSTEM SHALL retain the configured coverage threshold and SHALL NOT
   exclude unrelated correctness tests to make CI pass.
5. THE `minio` marker SHALL identify only tests that contact a live MinIO
   service; mocked credential, backend, and protocol-contract tests SHALL
   remain in normal CI.
6. GIVEN a checkout without MinIO configuration, WHEN pytest collects the
   suite, THEN collection SHALL complete without a module-import exception or
   network access and the normal, MinIO, performance, and stress selections
   SHALL form an auditable ownership map for the intended suite.

### Requirement 2: Stable performance and stress signal

**User Story:** As a maintainer, I want the known host-sensitive selection
stress threshold resolved, so that the extended profile detects regressions
without producing routine false failures.

#### Acceptance Criteria

1. GIVEN representative supported hosts, WHEN the selection stress scenario is
   measured under Spec 007, THEN issue #68 SHALL record timings and the chosen
   tolerance or baseline strategy as chronological evidence.
2. WHERE correctness and throughput assertions are combined, THE TEST SUITE
   SHALL separate deterministic correctness from environment-sensitive timing.
3. WHILE stress tests remain opt-in, THE RELEASE EVIDENCE SHALL record their
   result or an explicit, owner-approved residual risk.
4. THE active spec SHALL own the approved stress-test implementation scope,
   acceptance criteria, sequencing, and validation; issue #68 SHALL track
   assignment, state, and linked evidence without overriding this contract.

### Requirement 3: Reproducible release artifacts

**User Story:** As a release operator, I want version-consistent source and
wheel artifacts, so that the GitHub release contains installable outputs built
from the tagged source.

#### Acceptance Criteria

1. GIVEN a clean checkout prepared for `v0.9.1`, WHEN the package is built,
   THEN both sdist and wheel SHALL be produced successfully.
2. THE package version, importable `__version__`, intended tag version, and
   installed CLI version SHALL all equal `0.9.1`.
3. THE artifacts SHALL contain the declared package data, both `timelocker` and
   `tl` entry points, valid metadata, and recorded SHA-256 hashes.
4. IF artifact validation fails, THEN no release tag SHALL be created.
5. GIVEN the repository's side-effecting version helper, WHEN version sources
   are prepared for `0.9.1`, THEN the operator SHALL use
   `python scripts/bump_version.py bump patch --no-commit --no-tag` (or an
   equivalently proven non-publishing operation) and SHALL record unchanged
   pre/post commit, tag, tag-triggered release-workflow run, and GitHub-release
   state.

### Requirement 4: Clean installation validation

**User Story:** As a user, I want verified installation instructions and
artifacts, so that I can install TimeLocker on a supported environment without
undeclared dependencies.

#### Acceptance Criteria

1. GIVEN Python 3.12 and 3.13, WHEN the wheel and sdist are installed into fresh
   environments, THEN installation SHALL complete without undeclared Python
   dependencies.
2. GIVEN each of Linux, macOS, and Windows on Python 3.12 and 3.13, WHEN the
   supported smoke path runs, THEN `timelocker`, `tl`, version output, and root
   help SHALL work in all six combinations.
3. WHERE a platform requires Restic or another system prerequisite, THE
   INSTALLATION GUIDE SHALL state the verified prerequisite and limitation.
4. IF a declared support claim cannot be validated, THEN the claim SHALL be
   corrected before release or the release SHALL remain blocked.
5. THE package metadata SHALL express the bounded Python support range
   `>=3.12,<3.14`, and its Python and operating-system classifiers SHALL agree
   with the six-combination validation contract without retaining the broader
   `Operating System :: OS Independent` classifier.

### Requirement 5: Safe release rehearsal and communications

**User Story:** As a release operator, I want a rehearsed process and accurate
release notes, so that `v0.9.1` can be published deliberately and recovered
from failures.

#### Acceptance Criteria

1. GIVEN the tag-triggered workflow, WHEN it is rehearsed, THEN every step
   before tag publication SHALL be validated without creating a production tag
   or GitHub release.
2. THE durable release procedure SHALL identify prerequisites, authorized
   operator, commands, checks, failure handling, and rollback boundaries.
3. THE `CHANGELOG.md` entry and release notes SHALL describe only changes and
   limitations supported by repository evidence.
4. BEFORE release approval, THE VERIFICATION RECORD SHALL link required CI,
   artifact, clean-install, stress, documentation, and review evidence.
5. PyPI publication and `1.0.0` SHALL remain explicitly deferred.
6. `CHANGELOG.md` SHALL be the checked-in canonical source for `v0.9.1`
   release communications; the eventual GitHub release body SHALL be derived
   from that version section rather than a second durable release-note file.

## Correctness Properties

- **CP-001:** Every test in normal CI either has all external dependencies
  provisioned by the job or is assigned to an explicit dependency-owning
  profile.
- **CP-002:** A version mismatch among tag intent, package metadata,
  `TimeLocker.__version__`, or installed CLI output always blocks release.
- **CP-003:** Installing either release artifact in a clean supported
  environment yields the same version and console entry-point behavior.
- **CP-004:** Rehearsal cannot create a production tag, GitHub release, or PyPI
  publication, commit, or tag as a side effect.
- **CP-005:** Each public release claim maps to a recorded validation result or
  an explicit known limitation.

## Technical Context

- **Language/Version:** Python 3.12 and 3.13 only, expressed as
  `requires-python = ">=3.12,<3.14"` and matching classifiers.
- **Primary Dependencies:** pytest, coverage, build, GitHub Actions, Restic,
  MinIO for S3 integration tests.
- **Target Platform:** Linux, macOS, and Windows, each on Python 3.12 and 3.13.
- **Constraints:** No secrets in logs or artifacts; no production tag during
  rehearsal; coverage threshold remains 50 percent; PyPI is deferred.
- **Performance Goals:** Stress thresholds must distinguish regression from
  normal host variance; no new absolute target is invented by this spec.

## Success Criteria

- **SC-001:** Normal GitHub Actions CI passes from a clean checkout.
- **SC-002:** The explicit MinIO profile passes with a provisioned endpoint and
  fails clearly when its dependency is unavailable.
- **SC-003:** Issue #68 has closure-quality threshold evidence or an explicit
  release-blocking disposition.
- **SC-004:** Both `0.9.1` artifacts pass metadata, hash, and clean-install
  validation.
- **SC-005:** Release rehearsal completes without external publication.
- **SC-006:** Durable operator guidance, installation guidance, changelog, and
  release notes are ready for human release approval.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
