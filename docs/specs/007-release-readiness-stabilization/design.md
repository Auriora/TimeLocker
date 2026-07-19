---
title: Release readiness stabilization design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Technical Design

## Overview

The release is prepared as a sequence of independently verifiable gates. CI
profiles first become dependency-correct; the known stress signal is resolved
under this spec with issue #68 retaining assignment and evidence history;
versioned artifacts are then built once and installed into
clean environments; finally, the existing release workflow is rehearsed and
the evidence is promoted into durable guidance and release communications.
Phase 5 adds a machine-acceptance gate after a Linux Mint pilot exposed runtime
defects that artifact smoke tests could not detect. Release readiness now also
requires a TimeLocker-owned backup, listing, restore, tray, and scheduling path
to work without changing the existing NPBackup job prematurely.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| R1 | AC1-AC6 | Dedicated live-service marker, collection-safe fixtures, and explicit MinIO dependency gate | Workflow review, collection partition, normal CI, MinIO profile |
| R2 | AC1-AC4 | Spec-owned stress implementation and validation; issue #68 tracks assignment and chronological evidence | Stress tests, issue evidence, extended profile |
| R3 | AC1-AC5 | Side-effect-safe version preparation, one version guard, and one artifact set reused by smoke validation | Git-state comparison, build, metadata inspection, hashes, CLI version |
| R4 | AC1-AC5 | Explicit six-combination support contract | Wheel and sdist installs, CLI smoke matrix |
| R5 | AC1-AC6 | Non-publishing rehearsal followed by in-place process updates and changelog-derived communications | Workflow lint/review, rehearsal, docs review |
| R6 | AC1-AC4 | Consistent credential resolution, side-effect-free dry-run, source validation, and truthful backup results | Focused CLI/service tests and local pilot |
| R7 | AC1-AC4 | Canonical snapshot mapping plus robust latest/exact restore and error propagation | Focused snapshot/restore tests and digest-verified restore |
| R8 | AC1-AC3 | Ayatana-first Linux indicator discovery with legacy fallback and non-fatal headless behavior | Import-path tests and Linux Mint tray smoke |
| R9 | AC1-AC4 | Schedule records bind executable repository/source inputs and render only supported CLI options | Parser round-trip tests and staged systemd asset inspection |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Only live-service tests carry `minio`; collection is side-effect-free; normal CI excludes that marker while retaining mocked S3/MinIO contract tests | Collection partition checks plus both workflow profiles | Marker selection must not hide unrelated integration tests. |
| CP-002 | A shared version verification command compares intended tag, `pyproject.toml`, import version, and installed CLI | Negative and positive version checks | Production tag is never needed for rehearsal. |
| CP-003 | The same smoke contract is run against wheel and sdist installs | Clean virtual environments and supported platform jobs | System prerequisites remain explicit. |
| CP-004 | Rehearsal stops before tag creation and uses workflow validation or a non-publishing harness | Command review and absence of new tag/release | Any external write needs separate release approval. |
| CP-005 | Release-note items link to commits, specs, issues, tests, or known limitations | Documentation and release review | Generated notes may be input, not sole evidence. |
| CP-006 | Credential sources converge on one repository password boundary and generated assets contain references, never values | Unit tests and redacted asset review | Existing NPBackup secrets are not inspected. |
| CP-007 | TimeLocker creates, lists, restores, and digest-verifies the same snapshot | Focused tests plus local round trip | Raw Restic proof alone is insufficient. |
| CP-008 | Rendered schedule commands are parsed by the installed CLI before installation | Parser contract tests | Privileged execution still requires operator approval. |
| CP-009 | Tray imports and initialization are optional and isolated from core CLI execution | Namespace/fallback tests and headless CLI smoke | Desktop packaging varies by distribution. |

## High-Level Design

### Release Gate Flow

```text
CI profile repair
    -> MinIO profile proof
    -> Spec 007 stress implementation and issue #68 evidence
    -> version bump and artifact build
    -> clean-install matrix
    -> release workflow rehearsal
    -> durable docs and changelog-derived release communications
    -> Linux Mint machine acceptance and staged schedule validation
    -> human release decision
```

### Components and Changes

- `.github/workflows/test-suite.yml`: make normal and external-service test
  ownership explicit; add or invoke a MinIO-capable profile.
- Test markers and MinIO fixtures: register `minio`, mark only live-service
  tests, keep collection free of configuration failures and network calls, and
  provide actionable runtime dependency behavior.
- Selection stress tests and tooling: implement the calibrated baseline and
  deterministic/timing separation under Spec 007; GitHub issue #68 tracks
  assignment, state, representative timings, and chronological evidence.
- `pyproject.toml` and `src/TimeLocker/__init__.py`: move together to `0.9.1`
  using the version helper with commit and tag side effects disabled; bound
  Python support to `>=3.12,<3.14` and align classifiers.
- Build and smoke tooling: build once, inspect both artifacts, and install each
  in isolated environments.
- `.github/workflows/release.yml`: preserve tag-triggered publication while
  extracting or documenting a safe pre-tag rehearsal path where practical.
- `CHANGELOG.md`, installation guide, and the existing version-management
  process receive accepted current-state guidance before spec closure. The
  GitHub release body is derived from the `v0.9.1` changelog section.
- Repository, backup, snapshot, and restore commands: reconcile credential
  precedence, source handling, snapshot mapping, progress cleanup, and reported
  results around the existing Restic adapter.
- Linux tray integration: prefer `AyatanaAppIndicator3` on current Mint while
  retaining the legacy `AppIndicator3` fallback and non-fatal headless mode.
- Schedule generation: persist an executable repository/source target, render
  current CLI commands, and make configuration and environment-file boundaries
  explicit without embedding secrets.

### Data Models

The schedule record gains the repository and source/selection inputs required
to execute a backup; compatibility handling is required for existing records.
Other release evidence uses files and
external records: workflow runs, `dist/` artifacts, `SHA256SUMS`, clean-install
logs, issue #68, changelog text, and release review notes. Generated `dist/`
content remains untracked unless repository policy explicitly says otherwise.

### Data Flow

Source metadata determines the build version. A clean checkout produces sdist
and wheel artifacts plus hashes. Each artifact is installed into a fresh
environment and queried through both console entry points. CI, stress-test
results, and linked issue evidence feed the verification record. Accepted
operator and user guidance
is promoted to durable docs, while the spec remains the temporary coordination
surface until closure.

### Phase 5 Machine Acceptance Flow

```text
resolve repository credential -> initialize isolated repository
    -> validate dry-run without mutation -> create TimeLocker backup
    -> list snapshot through TimeLocker -> restore latest and exact snapshot
    -> verify reference-file digest -> validate Mint tray namespace
    -> render and parse staged schedule assets -> operator cutover decision
```

The pilot uses isolated TimeLocker configuration and data directories. It does
not read masked NPBackup secret values, install privileged units, or disable an
existing schedule. The raw Restic CLI remains a diagnostic control only.

## Low-Level Design

### CI Profile Logic

1. Register a dedicated `minio` pytest marker in `pyproject.toml`.
2. Apply it only to tests that contact a live MinIO service. Keep mocked
   credential, backend, and protocol-contract tests unmarked in normal CI.
3. Move configuration validation and client/network access out of module import
   and collection into fixtures or an explicit runtime preflight.
4. Run normal CI with
   `pytest -m "not performance and not stress and not minio"`.
5. Add a job that provisions MinIO, waits for readiness, exports ephemeral
   endpoint and credential inputs, and runs `pytest -m minio`.
6. Ensure missing dependency state produces a clear preflight failure.
7. Compare the complete collection with the normal, MinIO, performance, and
   stress selections so every intended node is accounted for and no mocked
   contract test moves out of normal CI.

### Version and Artifact Guard

```text
expected = "0.9.1"
before_commit = git_head
before_tags = git_tags
before_release_runs = tag_triggered_release_workflow_runs
before_releases = github_releases
run "python scripts/bump_version.py bump patch --no-commit --no-tag"
assert git_head == before_commit
assert git_tags == before_tags
assert tag_triggered_release_workflow_runs == before_release_runs
assert github_releases == before_releases
assert pyproject_version == expected
assert imported_version == expected
build sdist and wheel once
for artifact in [wheel, sdist]:
    install artifact in a fresh environment
    assert timelocker version --short == expected
    assert tl version --short == expected
record metadata and SHA-256
```

### Clean-Install Matrix

The release contract is exactly Python 3.12 and 3.13 on Linux, macOS, and
Windows. `requires-python` becomes `>=3.12,<3.14`; Python classifiers list 3.12
and 3.13; OS classifiers name the three supported systems and remove
`Operating System :: OS Independent`.
Artifact smoke validation covers all six OS/Python combinations. The normal
correctness suite runs on Ubuntu for both Python versions; artifact smoke
coverage on every declared OS is mandatory. If a runner cannot validate a
combination, the support claim must be corrected before release or readiness
remains blocked.

### Release Rehearsal

The rehearsal validates checkout depth, Restic acquisition and checksum,
version guard, normal tests, artifact build, smoke install, artifact upload
configuration, release-note inputs, permissions, and rollback instructions.
It records pre/post commit, tag, and GitHub-release identity. The publishing
boundary is a hard stop before any commit, `git tag`, tag push,
`gh release create`, or package-index upload.

### Repository and Credential Boundary

Repository initialization and later operations use the same credential
resolver. Explicit command input takes precedence over the documented
environment chain; interactive prompting occurs only when allowed and no
non-interactive source is available. Credentials are passed to Restic without
being stored in schedule commands, normal logs, or verification evidence.

Dry-run validates the same repository and sources as execution but must not
create a snapshot. Deterministic source or credential validation failures are
returned directly and are not retried.

### Snapshot and Restore Boundary

Snapshot adapters map Restic's canonical timestamp into the domain model once.
Listing and restore share exact/latest resolution. Progress and status cleanup
must preserve the primary exception even if cleanup itself encounters stale or
partially initialized state.

### Schedule Rendering Boundary

A schedule is executable only when it identifies a repository and explicit
sources or a saved selection. Renderers build argv from commands accepted by
the current parser and validate that argv before writing cron or systemd
assets. Non-default config and credential environment files are references in
the asset; secret values are never serialized. Privileged sources require a
system-level unit and remain an operator/sudo gate.

### Error Handling

- Missing MinIO fails at dependency preflight in the MinIO profile.
- Test collection drift blocks the CI-profile task.
- Version mismatch or artifact-install failure blocks downstream release tasks.
- Unsupported platform results are recorded as blocking support-claim gaps, not
  silently ignored.
- Rehearsal or workflow uncertainty remains a release blocker until reviewed.
- Repository and source validation errors remain primary and are not retried.
- Progress/status cleanup logs secondary failures without replacing the
  original backup or restore error.
- An incomplete schedule target blocks generation before any asset is written.
- Missing tray libraries disable only the optional tray integration.

### Security, Trust, and Access

MinIO CI credentials must be ephemeral non-production values. Logs and
artifacts must not contain repository passwords, tokens, or callback material.
The rehearsal requires read access only; tag push and GitHub release creation
remain separately authorized release actions. PyPI credentials are neither
required nor accessed.

### Migration and Compatibility

This is a patch release with no intended breaking CLI change. Existing schedule
records without an executable target remain readable but cannot generate new
assets until repository and source/selection fields are supplied. Any other
discovered breaking change is removed from the release or escalated for a new
requirement and explicit versioning decision.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Normal CI and collection comparison | R1, CP-001 | `verification.md`, Actions run | Hosted-runner variance |
| Provisioned MinIO profile and dependency preflight | R1, CP-001 | `verification.md`, Actions run | Service image drift |
| Spec-owned stress implementation, issue #68 evidence, and extended profile | R2 | tests, GitHub issue #68, `verification.md` | Hardware variance |
| Build, metadata, hashes, wheel and sdist installs | R3, R4, CP-002, CP-003 | `verification.md`, artifacts | OS coverage limits |
| Non-publishing workflow rehearsal | R5, CP-004 | `verification.md`, review record | Tag-only behavior not executed until release approval |
| Changelog-derived communications, install, and process review | R4, R5, CP-005 | durable docs and review | Human wording error |
| Repository init, dry-run, backup, and result checks | R6, CP-006 | focused tests and `verification.md` | Host credential differences |
| TimeLocker snapshot list/restore and digest round trip | R7, CP-007 | focused tests and isolated Mint pilot | Filesystem metadata variance |
| Ayatana, legacy, and headless tray paths | R8, CP-009 | focused tests and Mint tray smoke | Desktop session variance |
| Schedule render/parser round trip and staged asset review | R9, CP-006, CP-008 | focused tests and `verification.md` | Privileged installation remains manual |

## Downstream Task Guidance

- Repair CI before treating any release validation as authoritative.
- Do not start artifact release validation until Spec 007 stress acceptance is
  met and issue #68 contains the linked evidence or blocking disposition.
- Build once and reuse artifacts across clean-install checks.
- Stop for human release approval after rehearsal and documentation; this spec
  does not authorize tagging or publishing.
- Reconcile requirements, design, tasks, verification, and traceability after
  any support-matrix or workflow-scope change.
- Do not restore release-ready status until the TimeLocker-owned machine round
  trip succeeds and generated schedule commands parse against the current CLI.
- Do not disable NPBackup or install a privileged timer within implementation;
  prepare redacted assets and leave those actions as explicit operator gates.

## Operational Considerations

The first real tag remains a controlled external change. A failed release must
leave the existing code and documentation recoverable by correcting the source,
incrementing version if necessary, and creating a new tag; published tags or
releases must not be silently overwritten. Exact policy is promoted to the
durable release procedure.

## Open Questions

Implementation can proceed on the isolated pilot. Final cutover still requires
the operator to provide a supported TimeLocker repository credential, approve
sudo installation for protected sources, identify the actual NPBackup scheduler,
and observe successful TimeLocker scheduled runs before disabling it.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
