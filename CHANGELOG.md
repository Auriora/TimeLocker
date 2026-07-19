# Changelog

All notable changes to TimeLocker are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A version section records release contents, not proof that publication occurred.
The `Prepared` qualifier on `0.9.1` marks it as a Beta release candidate until
the release maintainer approves and finalizes the production tag.

## [Unreleased]

No changes have been assigned beyond the `0.9.1` release candidate.

## [0.9.1] - Prepared 2026-07-19

### Added

- Deterministic normal and provisioned-MinIO CI profiles, with explicit
  dependency ownership and failure preflight.
- Reproducible wheel and source-distribution validation for package metadata,
  both CLI entry points, packaged data, and SHA-256 hashes.
- Clean-install smoke coverage for wheel and source distributions on Linux,
  macOS, and Windows with Python 3.12 and 3.13.
- A reusable, read-only release rehearsal that derives its release-body preview
  from this changelog section.

### Changed

- Bounded supported Python versions to `>=3.12,<3.14` and documented Restic
  0.18.0 or later as the runtime prerequisite.
- Replaced the host-sensitive fixed-iteration selection stress gate with a
  calibrated correctness and timing contract.
- Isolated GitHub release creation behind successful validation and a single
  job-scoped `contents: write` permission.

### Fixed

- Prevented normal CI from contacting an unprovisioned MinIO service.
- Made root CLI help safe for the Windows default `cp1252` encoding.
- Aligned package, source, and version-bump metadata at `0.9.1`.

### Known Limitations

- This is a Beta release candidate. A production tag and GitHub release still
  require separate maintainer approval.
- TimeLocker is not published to PyPI; install from source until an authorized
  GitHub release provides downloadable artifacts.
- The first production tag will exercise GitHub release creation in the live
  repository for the first time. The non-publishing rehearsal cannot reproduce
  that final external write.
- GitHub Actions currently reports a non-blocking upstream Node.js runtime
  deprecation advisory for pinned actions.

## Current Beta Feature Boundary

TimeLocker includes CLI support for repository management, backup and recovery,
file selection, scheduling, credentials, monitoring, and service integration.
Policy management is partially implemented. The REST API, desktop GUI, and
database-backed storage remain design ideas rather than released features.

See the [documentation status](docs/DOCUMENTATION-STATUS.md) for the current
feature boundary and the [active specification index](docs/specs/README.md) for
approved work in progress.
