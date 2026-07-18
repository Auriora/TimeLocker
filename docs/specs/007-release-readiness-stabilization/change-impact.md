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
| `scripts/bump_version.py` and `.bumpversion.cfg` | Version bumping commits and tags by default unless both are disabled. | high | Preparation must use `--no-commit --no-tag`. |
| `docs/guides/user/installation.md` | Current source install and test guidance. | high | Must reflect only verified artifact and platform behavior. |
| `docs/processes/version-management.md` | Existing version and release procedure. | high | Correct in place rather than creating a duplicate process. |
| `docs/processes/README.md` | Existing process index. | high | Must link the corrected procedure. |
| `CHARTER.md` | PyPI distribution is outside current project state. | high | Remains unchanged. |

## Change Type

- **Primary type:** operational
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** yes, CI and release artifacts

## Proposed Changes

| Change | Type | Source of truth | New durable destination | Promotion required |
|--------|------|-----------------|-------------------------|-------------------|
| Separate normal and live MinIO test ownership with collection safety | modify | `pyproject.toml`, tests, `.github/workflows/test-suite.yml` | `docs/4-testing/README.md` and workflow | yes |
| Stabilize the selection stress signal under spec authority | bug_fix | Spec 007; issue #68 tracks assignment and evidence | test code and durable testing guidance | yes |
| Prepare version `0.9.1` without commit, tag, or release side effects | modify | `scripts/bump_version.py`, `.bumpversion.cfg`, package version sources | same files and corrected version process | yes |
| Bound Python support and validate six OS/Python combinations | modify | `pyproject.toml` and release evidence | `docs/guides/user/installation.md` | yes |
| Correct the release operator procedure | modify | Spec 007 design and rehearsal evidence | `docs/processes/version-management.md` and process index | yes |
| Publish accurate `v0.9.1` communications | add | Git history and verification evidence | `CHANGELOG.md`; GitHub release body derived from its version section | yes |
| Defer PyPI and `1.0.0` | clarify | `CHARTER.md`, milestone decision | version process and changelog | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Test profile contract and commands | `docs/4-testing/README.md` | pending | Include MinIO prerequisites and extended profile. |
| Verified install matrix and prerequisites | `docs/guides/user/installation.md` | pending | Do not claim untested platforms. |
| Release procedure and rollback boundary | `docs/processes/version-management.md` | pending | Correct in place and link from `docs/processes/README.md`. |
| Release contents and limitations | `CHANGELOG.md` | pending | Canonical checked-in source; derive the GitHub release body from the `v0.9.1` section. |
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
  dedicated marker; the live suite also performs configuration work during
  import/collection while mocked MinIO contracts are not a live-service class.
- **Regression risk:** An over-broad marker expression could hide integration
  coverage; collection comparison and the explicit profile mitigate it.
- **Durable doc update needed:** Yes, testing profile and prerequisite guidance.

## Open Questions

None block implementation. The declared validation contract is Python 3.12 and
3.13 on Linux, macOS, and Windows. T007 must validate all six combinations or
correct the affected claim before downstream work continues.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
