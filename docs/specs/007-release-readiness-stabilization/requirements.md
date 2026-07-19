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

TimeLocker is prepared as `0.9.1` but has no published release tags. Phases 1-4
restored CI, artifact, cross-platform smoke, and non-publishing release
evidence. A subsequent Linux Mint machine pilot proved that a valid Restic
backup can be created but exposed release-blocking defects in repository
initialization, dry-run, snapshot discovery, restore, system-tray integration,
and generated scheduling commands. Phase 5 extends the stabilization boundary
until a real local backup can be discovered and restored through TimeLocker and
an executable staged-migration schedule can be prepared safely.

## Goals

- Restore a green, deterministic normal CI profile without silently discarding
  MinIO integration coverage.
- Stabilize the separate selection stress signal tracked by GitHub issue #68.
- Build and validate source and wheel artifacts for version `0.9.1`.
- Prove the supported installation and CLI smoke paths in clean environments.
- Rehearse the release workflow without creating a production tag.
- Produce accurate changelog-derived release communications and operator documentation.
- Prove repository setup, backup, snapshot discovery, restore, Linux Mint tray
  compatibility, and schedule generation on a real operator machine.

## Non-Goals

- Publishing to PyPI or configuring PyPI credentials or trusted publishing.
- Declaring TimeLocker `1.0.0` or promising a stable public Python API.
- Implementing unrelated feature, CLI, configuration, or performance backlog.
- Creating a release tag or GitHub release during implementation rehearsal.
- Weakening tests, coverage, or supported-platform claims to obtain a pass.
- Extracting masked NPBackup secrets, disabling NPBackup before TimeLocker
  restore proof, or installing a privileged timer without explicit sudo access.

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
version metadata, installation guidance, the release process, release
communications, CLI recovery behavior, optional Linux tray integration, and
schedule generation. It preserves the supported credential model while making
its precedence and non-interactive use consistent.

## Staged Readiness

- **Current stage:** implementation
- **Next stage:** validation
- **Ready to implement when:** package lint, traceability, task dependency, and
  agent-readiness checks pass.
- **Design-first exception:** no
- **Optional artifacts included:** `change-impact.md`, `verification.md`,
  `traceability.md`
- **Downstream review needed:** recovery, security, operations, documentation,
  and release readiness

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

### Requirement 6: Operator-ready repository and backup workflow

**User Story:** As an operator, I want repository initialization and backup
commands to honor the documented credential and source contracts, so that I can
run TimeLocker non-interactively without hidden CLI exceptions.

#### Acceptance Criteria

1. GIVEN a repository password from the explicit option or supported
   environment chain, WHEN a local repository is initialized, THEN TimeLocker
   SHALL initialize it without requiring an unrelated interactive prompt.
2. GIVEN a file or directory accepted by `backup create`, WHEN a dry-run is
   requested, THEN it SHALL complete without repository mutation or an
   undefined-variable exception.
3. GIVEN a valid initialized repository and source, WHEN a backup completes,
   THEN the result SHALL identify the created snapshot and SHALL NOT report a
   false zero-file count when files were stored.
4. IF source validation fails, THEN TimeLocker SHALL report the actionable
   validation error without retrying a deterministic input failure.

### Requirement 7: Recoverable snapshot workflow

**User Story:** As an operator, I want TimeLocker to list and restore its
snapshots, so that a successful backup represents recoverable data rather than
an opaque Restic artifact.

#### Acceptance Criteria

1. GIVEN a valid Restic snapshot, WHEN table or JSON listing is requested,
   THEN TimeLocker SHALL map the canonical snapshot timestamp and return the
   snapshot without an attribute error.
2. GIVEN `latest` or an exact snapshot ID, WHEN a full restore is requested,
   THEN TimeLocker SHALL resolve the snapshot and restore its files.
3. GIVEN a restored reference file, WHEN its digest is compared with the
   source, THEN the digests SHALL match.
4. IF discovery or restore fails, THEN the original failure SHALL remain
   visible and SHALL NOT be replaced by progress-context or persisted-status
   secondary errors.

### Requirement 8: Linux Mint system-tray compatibility

**User Story:** As a Linux Mint operator, I want optional tray integration to
use the desktop toolkit actually installed, so that TimeLocker does not claim
the tray is unavailable on a supported Cinnamon session.

#### Acceptance Criteria

1. GIVEN PyGObject and `AyatanaAppIndicator3`, WHEN TimeLocker initializes the
   Linux tray, THEN it SHALL create an indicator through that namespace.
2. WHERE legacy `AppIndicator3` is available, THE SYSTEM SHALL retain that
   supported compatibility path.
3. IF no tray toolkit is importable or a command runs headlessly, THEN CLI
   backup and recovery behavior SHALL remain usable and the diagnostic SHALL
   identify the missing optional dependency rather than deny platform support.

### Requirement 9: Executable staged-migration schedules

**User Story:** As an operator replacing a privileged NPBackup job, I want
generated automation to invoke a real TimeLocker command with explicit
configuration and credential boundaries, so that scheduling cannot silently
run an unsupported CLI shape or omit protected sources.

#### Acceptance Criteria

1. GIVEN a schedule bound to a repository and either explicit sources or a
   selection, WHEN cron or systemd assets are generated, THEN every emitted
   TimeLocker option SHALL be accepted by the current CLI.
2. WHERE a non-default configuration directory or protected environment file
   is required, THE GENERATED ASSET SHALL reference it explicitly without
   embedding secret values.
3. GIVEN sources such as `/etc`, `/var`, or `/root`, WHEN system scheduling is
   prepared, THEN the guidance SHALL preserve the required privileged execution
   boundary and SHALL NOT imply that a user timer provides equivalent coverage.
4. UNTIL TimeLocker backup, listing, and restore validation pass and the new
   timer has observed successful runs, NPBackup SHALL remain enabled or its
   external scheduling state SHALL remain unchanged.

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
- **CP-006:** Every accepted credential source produces the same Restic
  repository password without exposing it in generated assets or logs.
- **CP-007:** A snapshot created through TimeLocker can be listed and restored
  through TimeLocker with byte-identical file content.
- **CP-008:** Every generated schedule command parses successfully against the
  installed TimeLocker CLI.
- **CP-009:** Optional tray initialization cannot make core CLI backup or
  recovery operations fail.

## Technical Context

- **Language/Version:** Python 3.12 and 3.13 only, expressed as
  `requires-python = ">=3.12,<3.14"` and matching classifiers.
- **Primary Dependencies:** pytest, coverage, build, GitHub Actions, Restic,
  MinIO for S3 integration tests.
- **Target Platform:** Linux, macOS, and Windows, each on Python 3.12 and 3.13.
- **Machine Acceptance Platform:** Linux Mint/Cinnamon on X11, with the system
  `python3-gi` and Ayatana AppIndicator typelib available.
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
- **SC-007:** A fresh local pilot repository completes init, backup, TimeLocker
  snapshot listing, TimeLocker restore, and digest verification.
- **SC-008:** Linux Mint tray initialization recognizes Ayatana when the GUI
  extra and system typelib are present.
- **SC-009:** Generated systemd assets use only supported commands and preserve
  the separate credential, sudo, and NPBackup cutover gates.

## Related Artifacts

- Change Impact: `change-impact.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
