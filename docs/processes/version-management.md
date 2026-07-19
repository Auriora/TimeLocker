---
title: Version management and GitHub releases
doc_type: process
status: active
owner: Auriora Team
last_reviewed: 2026-07-19
---

# Version Management And GitHub Releases

This procedure separates safe release preparation from publication. Running a
rehearsal does not authorize or create a commit, tag, GitHub release, or PyPI
distribution. The release maintainer must approve publication separately.

## Release Contract

- Versions follow `MAJOR.MINOR.PATCH` semantic versioning.
- `pyproject.toml`, `src/TimeLocker/__init__.py`, and `.bumpversion.cfg` must
  agree.
- A tag has the exact form `vMAJOR.MINOR.PATCH`.
- The matching `CHANGELOG.md` section is the canonical release-note source.
- `.github/workflows/release-validation.yml` owns read-only validation.
- `.github/workflows/release.yml` owns the isolated GitHub release action.
- TimeLocker is not published to PyPI. Adding registry publication requires a
  separate scope decision, credentials, process changes, and approval.

## Roles And Approval Boundary

Contributors may prepare versions and run non-publishing validation. Only the
release maintainer may approve a release commit and production tag. Pushing the
tag is the publication boundary: it starts the workflow whose final job creates
the GitHub release. Never push a release tag as part of preparation or
rehearsal.

## Prepare A Version Safely

Start from the intended release branch and inspect the tree. Do not hide
unrelated changes.

```bash
git status --short --branch
python scripts/bump_version.py show
python scripts/bump_version.py bump patch --dry-run
```

When a version change is required, disable both automatic side effects:

```bash
python scripts/bump_version.py bump patch --no-commit --no-tag
```

Review the three expected version files, update the matching changelog section,
and request a separate commit instruction. A dirty tree or disagreement about
the target version stops preparation.

## Run The Non-Publishing Rehearsal

For `v0.9.1`, run:

```bash
python scripts/validate_release_intent.py --version-ref v0.9.1
python scripts/validate_release_workflows.py
python -m pytest -m "not performance and not stress and not minio"
python -m build
python scripts/validate_release_artifacts.py --expected-version 0.9.1
python scripts/smoke_release_artifact.py dist/*.whl --expected-version 0.9.1
python scripts/smoke_release_artifact.py dist/*.tar.gz --expected-version 0.9.1
python scripts/extract_release_notes.py --version 0.9.1 --output release-notes.md
```

The reusable workflow may also be run manually with `version_ref=v0.9.1` after
the preparation changes are committed. It has `contents: read` permission and
uploads only validation artifacts and a release-note preview. Confirm the
commit, local tags, GitHub releases, and tag-triggered release-run inventory are
unchanged after either rehearsal.

The normal suite deliberately excludes performance, stress, and live MinIO
profiles. Those profiles and their prerequisites are defined in the
[testing guide](../4-testing/README.md) and must already have current passing
evidence for the release candidate.

## Authorize And Publish

Publication requires all of the following:

1. The release candidate is committed on the intended protected branch and CI
   is green.
2. The active release-readiness spec is ready for closure and its residual
   risks have an owner.
3. The version guard, artifacts, supported OS/Python matrix, changelog preview,
   and non-publishing rehearsal pass.
4. The release maintainer explicitly approves the exact commit and version.
5. The approved release commit replaces the changelog's `Prepared` qualifier
   with the actual release date without changing its evidence-backed body.

The maintainer then creates and pushes the approved signed tag according to the
repository Git policy. The tag-triggered workflow reruns the read-only contract,
downloads only those validated artifacts, and grants `contents: write` solely
to the dependent job that creates the GitHub release. The release body is the
derived changelog section; it is not generated independently.

## Verify Publication

After the workflow completes:

1. Confirm the release tag and GitHub release point to the approved commit.
2. Download both distributions and `SHA256SUMS` from the release.
3. Compare hashes and smoke a clean install through `timelocker` and `tl`.
4. Confirm the published body matches the corresponding changelog section.
5. Announce the release only after these checks pass.

## Failure And Recovery

- **Version mismatch:** stop before building; reconcile the three version
  sources and the approved tag intent. Do not move an existing published tag.
- **Missing Restic, build tool, or artifact:** install the documented
  prerequisite or correct the build. Do not bypass the failing check.
- **Permission failure:** keep rehearsal permissions read-only. Check repository
  Actions policy and the publish job's narrowly scoped `contents: write`
  permission; do not grant write permission to validation.
- **Test, artifact, or smoke failure:** retain the failed run as evidence, fix
  through the normal review path, and rerun the whole validation contract.
- **Failure after a tag is pushed:** stop announcements and record an issue.
  Do not overwrite or silently move a public tag. The release maintainer decides
  whether to remove an unpublished erroneous tag/release or issue a new patch.

The practical rollback before publication is to discard the uncommitted
preparation changes or revert the reviewed preparation commit. After
publication, prefer a new corrective patch release so consumers retain an
immutable history.

## Current Deferrals

Version `0.9.1` remains a Beta GitHub release candidate until separately
approved. PyPI distribution and the `1.0.0` milestone remain deferred and are
not implied by completing this procedure.
