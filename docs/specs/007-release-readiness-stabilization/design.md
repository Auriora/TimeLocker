---
title: Release readiness stabilization design
doc_type: spec
artifact_type: design
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Technical Design

## Overview

The release is prepared as a sequence of independently verifiable gates. CI
profiles first become dependency-correct; the known stress signal is resolved
through issue #68; versioned artifacts are then built once and installed into
clean environments; finally, the existing release workflow is rehearsed and
the evidence is promoted into durable guidance and release communications.

## Requirement Coverage

| Requirement | Acceptance Criteria | Design Coverage | Validation Approach |
|-------------|---------------------|-----------------|---------------------|
| R1 | AC1-AC4 | Marker/profile ownership plus explicit MinIO dependency gate | Workflow review, normal CI, MinIO profile |
| R2 | AC1-AC3 | Issue #68 remains the single execution record; Spec 007 consumes its evidence | Issue acceptance review, extended profile |
| R3 | AC1-AC4 | One version guard and one artifact set reused by smoke validation | Build, metadata inspection, hashes, CLI version |
| R4 | AC1-AC4 | Clean environment matrix derived from current support claims | Wheel and sdist installs, CLI smoke tests |
| R5 | AC1-AC5 | Non-publishing rehearsal followed by durable process and release-note promotion | Workflow lint/review, dry run, docs review |

## Correctness Property Coverage

| Property | Design Behavior | Validation Direction | Notes |
|----------|-----------------|----------------------|-------|
| CP-001 | Tests requiring MinIO are collected into a dependency-owning profile; normal CI excludes only that explicit integration class | Collection checks plus both workflow profiles | Marker selection must not hide unrelated integration tests. |
| CP-002 | A shared version verification command compares intended tag, `pyproject.toml`, import version, and installed CLI | Negative and positive version checks | Production tag is never needed for rehearsal. |
| CP-003 | The same smoke contract is run against wheel and sdist installs | Clean virtual environments and supported platform jobs | System prerequisites remain explicit. |
| CP-004 | Rehearsal stops before tag creation and uses workflow validation or a non-publishing harness | Command review and absence of new tag/release | Any external write needs separate release approval. |
| CP-005 | Release-note items link to commits, specs, issues, tests, or known limitations | Documentation and release review | Generated notes may be input, not sole evidence. |

## High-Level Design

### Release Gate Flow

```text
CI profile repair
    -> MinIO profile proof
    -> issue #68 stress evidence
    -> version bump and artifact build
    -> clean-install matrix
    -> release workflow rehearsal
    -> durable docs and release notes
    -> human release decision
```

### Components and Changes

- `.github/workflows/test-suite.yml`: make normal and external-service test
  ownership explicit; add or invoke a MinIO-capable profile.
- Test markers and MinIO fixtures: expose dependency requirements before a
  network call and provide actionable failure behavior.
- GitHub issue #68: own calibration of the selection stress threshold; this
  spec links its result instead of duplicating implementation tasks.
- `pyproject.toml` and `src/TimeLocker/__init__.py`: move together to `0.9.1`.
- Build and smoke tooling: build once, inspect both artifacts, and install each
  in isolated environments.
- `.github/workflows/release.yml`: preserve tag-triggered publication while
  extracting or documenting a safe pre-tag rehearsal path where practical.
- `CHANGELOG.md`, release notes, installation guide, and release process:
  receive accepted current-state guidance before spec closure.

### Data Models

No application data model changes are required. Release evidence uses files and
external records: workflow runs, `dist/` artifacts, `SHA256SUMS`, clean-install
logs, issue #68, changelog text, and release review notes. Generated `dist/`
content remains untracked unless repository policy explicitly says otherwise.

### Data Flow

Source metadata determines the build version. A clean checkout produces sdist
and wheel artifacts plus hashes. Each artifact is installed into a fresh
environment and queried through both console entry points. CI and external
issue results feed the verification record. Accepted operator and user guidance
is promoted to durable docs, while the spec remains the temporary coordination
surface until closure.

## Low-Level Design

### CI Profile Logic

1. Identify MinIO-dependent tests by marker, path, or dedicated pytest
   collection contract.
2. Make normal CI exclude that exact external-service class while retaining all
   other non-performance, non-stress tests.
3. Add a job or documented command that provisions MinIO, waits for readiness,
   exports the endpoint and credentials, and runs only the MinIO class.
4. Ensure missing dependency state produces a clear preflight failure.
5. Compare collected test counts before and after the profile change to catch
   accidental test loss.

### Version and Artifact Guard

```text
expected = "0.9.1"
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

The matrix is derived from `requires-python`, classifiers, workflow coverage,
and installation claims. At minimum it covers Python 3.12 and 3.13. Operating
systems are either validated or their claims are narrowed; the spec does not
manufacture support from unexecuted workflow branches.

### Release Rehearsal

The rehearsal validates checkout depth, Restic acquisition and checksum,
version guard, normal tests, artifact build, smoke install, artifact upload
configuration, release-note inputs, permissions, and rollback instructions.
The publishing boundary is a hard stop before `git tag`, tag push,
`gh release create`, or any package-index upload.

### Error Handling

- Missing MinIO fails at dependency preflight in the MinIO profile.
- Test collection drift blocks the CI-profile task.
- Version mismatch or artifact-install failure blocks downstream release tasks.
- Unsupported platform results are recorded as blocking support-claim gaps, not
  silently ignored.
- Rehearsal or workflow uncertainty remains a release blocker until reviewed.

### Security, Trust, and Access

MinIO CI credentials must be ephemeral non-production values. Logs and
artifacts must not contain repository passwords, tokens, or callback material.
The rehearsal requires read access only; tag push and GitHub release creation
remain separately authorized release actions. PyPI credentials are neither
required nor accessed.

### Migration and Compatibility

This is a patch release. No application data migration or intended breaking CLI
change is included. Any discovered breaking change is removed from the release
or escalated for a new requirement and explicit versioning decision.

## Validation Strategy

| Validation | Covers | Evidence Location | Residual Risk |
|------------|--------|-------------------|---------------|
| Normal CI and collection comparison | R1, CP-001 | `verification.md`, Actions run | Hosted-runner variance |
| Provisioned MinIO profile and dependency preflight | R1, CP-001 | `verification.md`, Actions run | Service image drift |
| Issue #68 evidence and extended profile | R2 | GitHub issue #68, `verification.md` | Hardware variance |
| Build, metadata, hashes, wheel and sdist installs | R3, R4, CP-002, CP-003 | `verification.md`, artifacts | OS coverage limits |
| Non-publishing workflow rehearsal | R5, CP-004 | `verification.md`, review record | Tag-only behavior not executed until release approval |
| Changelog, release notes, install and process review | R4, R5, CP-005 | durable docs and review | Human wording error |

## Downstream Task Guidance

- Repair CI before treating any release validation as authoritative.
- Do not start artifact release validation until issue #68 has a disposition.
- Build once and reuse artifacts across clean-install checks.
- Stop for human release approval after rehearsal and documentation; this spec
  does not authorize tagging or publishing.
- Reconcile requirements, design, tasks, verification, and traceability after
  any support-matrix or workflow-scope change.

## Operational Considerations

The first real tag remains a controlled external change. A failed release must
leave the existing code and documentation recoverable by correcting the source,
incrementing version if necessary, and creating a new tag; published tags or
releases must not be silently overwritten. Exact policy is promoted to the
durable release procedure.

## Open Questions

None block implementation. The supported OS matrix is resolved from current
metadata and executable evidence during T006; any mismatch becomes an explicit
task result rather than an implicit assumption.

## Related Artifacts

- Requirements: `requirements.md`
- Change Impact: `change-impact.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
