---
title: Release readiness stabilization change impact
doc_type: spec
artifact_type: change-impact
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Change Impact

## Purpose

Record the durable behavior and documentation changed while preparing and
machine-validating the bounded `v0.9.1` stabilization release.

## Durable Source Mapping

| Source | Current behavior relied on | Confidence | Notes |
|--------|----------------------------|------------|-------|
| `.github/workflows/test-suite.yml` | Normal CI runs all non-performance, non-stress tests but provisions no MinIO. | high | Current failure source. |
| `.github/workflows/release-validation.yml` | A reusable read-only workflow validates intent, tests, artifacts, both smoke installs, and release-note derivation. | high | Added by T009 and exercised locally by T010. |
| `.github/workflows/release.yml` | A version tag calls the validation workflow before a separately permissioned GitHub release job. | high | Publication remains human-authorized. |
| `pyproject.toml` | Version `0.9.1`, bounded Python range, package metadata, scripts, markers, and coverage threshold. | high | Prepared but not published. |
| `scripts/bump_version.py` and `.bumpversion.cfg` | Version bumping commits and tags by default unless both are disabled. | high | Preparation must use `--no-commit --no-tag`. |
| `docs/guides/user/installation.md` | Current source install and test guidance. | high | Must reflect only verified artifact and platform behavior. |
| `docs/processes/version-management.md` | Existing version and release procedure. | high | Correct in place rather than creating a duplicate process. |
| `docs/processes/README.md` | Existing process index. | high | Must link the corrected procedure. |
| `CHARTER.md` | PyPI distribution is outside current project state. | high | Remains unchanged. |
| Repository, backup, snapshot, and restore command paths | A Linux Mint pilot created a valid Restic snapshot but exposed TimeLocker credential, dry-run, listing, restore, and reporting defects. | high | Raw Restic recovery proved the data while TimeLocker recovery remained blocked. |
| Linux tray integration | Mint provides the Ayatana namespace while the implementation expects only the legacy namespace. | high | Optional GUI behavior must not affect CLI availability. |
| Schedule generation | Generated commands currently reference unsupported policy and non-interactive options. | high | Assets are not safe to install until parser validation passes. |

## Change Type

- **Primary type:** operational
- **Breaking change:** no
- **Durable docs required:** yes
- **External behavior affected:** yes, CI, release artifacts, backup/recovery,
  optional tray behavior, and generated schedules

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
| Repair local repository initialization, dry-run, backup result, snapshot listing, and restore | bug_fix | runtime command and Restic adapter behavior | user backup/recovery guidance | yes |
| Support Mint's Ayatana indicator with legacy fallback | bug_fix | tray integration | installation and troubleshooting guidance | yes |
| Generate executable schedules with explicit configuration and privilege boundaries | modify | schedule model and renderers | scheduling/operator guidance | yes |

## Promotion Targets

| Spec content | Durable destination | Promotion status | Notes |
|--------------|---------------------|------------------|-------|
| Test profile contract and commands | `docs/4-testing/README.md` | complete | T001-T004 promoted normal, MinIO, and extended-profile ownership and commands. |
| Verified install matrix and prerequisites | `docs/guides/user/installation.md` | complete | T007 and T011 limit claims to the validated six-combination matrix. |
| Release procedure and rollback boundary | `docs/processes/version-management.md` | complete | Corrected in place and linked from `docs/processes/README.md` by T011. |
| Release contents and limitations | `CHANGELOG.md` | complete | T012 made the `v0.9.1` section canonical and previewed its derived release body. |
| Current version and release path | `README.md` | complete | T011 records Python 3.12-3.13 and `0.9.1` prepared, not published. |
| Backup/recovery credential and source contract | `docs/guides/user/recovery-operations-guide.md` | complete | T015-T016 machine acceptance and T019 review passed. |
| Linux tray prerequisites and fallback | `docs/guides/user/installation.md` | complete | T017 Mint and headless validation passed. |
| Schedule configuration, environment, privilege, and cutover boundary | `docs/guides/developer/scheduling-guide.md` | complete | T018 staging and T019 handoff review passed. |

## Unchanged Durable Areas

| Durable area | Reviewed source | Reason unchanged |
|--------------|-----------------|------------------|
| Product scope | `CHARTER.md` | Stabilization does not expand the product or publication boundary. |
| Product mandate | `CHARTER.md` | Runtime stabilization remains within the existing backup and recovery mandate. |
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

Implementation is unblocked in the isolated pilot. Privileged schedule
installation, repository credential selection, identification of the actual
NPBackup scheduler, and final cutover remain explicit operator decisions after
T019; publication and lifecycle closure remain separate human decisions.

## Related Artifacts

- Requirements: `requirements.md`
- Design: `design.md`
- Tasks: `tasks.md`
- Verification: `verification.md`
- Traceability: `traceability.md`
