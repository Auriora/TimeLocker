---
title: Release readiness stabilization change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Change Impact

## Purpose

Record the durable behavior and documentation changed while preparing the
bounded `v0.9.1` stabilization release.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `.github/workflows/test-suite.yml` | Normal CI runs all non-performance, non-stress tests but provisions no MinIO. | high | Current failure source. |
| `.github/workflows/release.yml` | A version tag triggers tests, build, wheel smoke, artifact upload, and GitHub release creation. | high | Must be rehearsed without publication. |
| `pyproject.toml` | Version `0.9.0`, Python range, package metadata, scripts, markers, and coverage threshold. | high | Will move to `0.9.1`. |
| `docs/guides/user/installation.md` | Current source install and test guidance. | high | Must reflect only verified artifact and platform behavior. |
| `CHARTER.md` | PyPI distribution is outside current project state. | high | Remains unchanged. |

## Change Type

- **Primary type:** operational
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** yes, CI and release artifacts

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Separate normal and MinIO-dependent test ownership | modify | `.github/workflows/test-suite.yml` | `docs/4-testing/README.md` and workflow | yes |
| Stabilize the selection stress signal | bug_fix | GitHub issue #68 | test code and durable testing guidance | yes |
| Bump package version to `0.9.1` | modify | `pyproject.toml` and package version module | same files, README or changelog where appropriate | yes |
| Validate sdist and wheel installs | add | release evidence | `docs/guides/user/installation.md` | yes |
| Define the release operator procedure | add | Spec 007 design and rehearsal evidence | `docs/processes/` | yes |
| Publish accurate `v0.9.1` communications | add | Git history and verification evidence | `CHANGELOG.md` and durable release notes | yes |
| Defer PyPI and `1.0.0` | clarify | `CHARTER.md`, milestone decision | release process and release notes | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Test profile contract and commands | `docs/4-testing/README.md` | pending | Include MinIO prerequisites and extended profile. |
| Verified install matrix and prerequisites | `docs/guides/user/installation.md` | pending | Do not claim untested platforms. |
| Release procedure and rollback boundary | new current-state document under `docs/processes/` | pending | Link from process index. |
| Release contents and limitations | `CHANGELOG.md` and durable `v0.9.1` release notes | pending | Evidence-backed claims only. |
| Current version and release path | `README.md` where needed | pending | Keep front door concise. |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| Product scope | `CHARTER.md` | Stabilization does not expand the product or publication boundary. |
| Application architecture | `docs/2-architecture/` | No runtime component boundary changes are intended. |
| Credential handling | durable security and user guidance | CI uses only ephemeral MinIO values; repository credential behavior is out of scope. |
| CLI feature backlog | GitHub issues #5, #7, #9, #11, #28-#30, #33-#34, #54-#56 | These are reconciled but not pulled into the patch release spec. |

## Bug Fix Details

- **Observed behavior:** GitHub Actions run 29653160911 failed with one failure
  and four setup errors because MinIO tests attempted to resolve an unavailable
  endpoint; 1310 tests passed before the maximum-failure stop.
- **Expected behavior:** Each CI profile provisions every external dependency
  needed by its selected tests and fails dependency preflight clearly.
- **Root cause evidence:** `.github/workflows/test-suite.yml` runs
  `pytest -m "not performance and not stress"` and contains no MinIO service or
  exclusion for tests under the MinIO integration class.
- **Regression risk:** An over-broad marker expression could hide integration
  coverage; collection comparison and the explicit profile mitigate it.
- **Durable doc update needed:** Yes, testing profile and prerequisite guidance.

## Open Questions

None block implementation. Platform claims are reconciled from current
metadata and executable evidence in T007.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
