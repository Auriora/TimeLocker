# Changelog

All notable changes to TimeLocker are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

A version section records the evidence-backed contents of a release. GitHub is
the authority for whether its corresponding tag and release were published.

## [Unreleased]

No changes have been assigned beyond `0.9.1`.

## [0.9.1] - 2026-08-13

### Added

- Deterministic normal and provisioned-MinIO CI profiles, with explicit
  dependency ownership and failure preflight.
- Reproducible wheel and source-distribution validation for package metadata,
  both CLI entry points, packaged data, and SHA-256 hashes.
- Clean-install smoke coverage for wheel and source distributions on Linux,
  macOS, and Windows with Python 3.12 and 3.13.
- A reusable, read-only release rehearsal that derives its release-body preview
  from this changelog section.
- NPBackup-compatible selection, exclusion, scheduling, and recovery migration
  with a retained rollback path.
- Protected system backup, run-status, retention, and tray workflows with
  authenticated local requests and sanitized durable status.
- Transactional local-wheel install, upgrade, status, and rollback through
  `timelocker-deploy`, including immutable release selection and evidence.
- Branded tray states for connecting, idle, running, success, warning, and
  failure conditions.

### Changed

- Bounded supported Python versions to `>=3.12,<3.14` and documented Restic
  0.18.0 or later as the runtime prerequisite.
- Replaced the host-sensitive fixed-iteration selection stress gate with a
  calibrated correctness and timing contract.
- Isolated GitHub release creation behind successful validation and a single
  job-scoped `contents: write` permission.
- Replaced the resident privileged event backend with socket-activated,
  one-request execution that exits after each explicit request.
- Preserved independent backup and retention timers while making tray status
  observation daemonless and filesystem-based.

### Fixed

- Prevented normal CI from contacting an unprovisioned MinIO service.
- Made root CLI help safe for the Windows default `cp1252` encoding.
- Aligned package, source, and version-bump metadata at `0.9.1`.
- Preserved native Restic repository URIs and selective recovery paths during
  migration.
- Prevented headless commands from initializing the system tray and prevented
  schedule installation from immediately starting its backup service.
- Hardened protected release staging, protocol upgrades, rollback, offline
  dependency installation, and unprivileged read-only deployment status.
- Made the Linux-only system-control entry point importable for `--help` and
  package smoke validation on Windows.

### Known Limitations

- TimeLocker is distributed through GitHub Releases and is not published to
  PyPI.
- Protected system deployment is accepted on Linux Mint/systemd. Windows has
  package and adapter coverage but no live protected-service acceptance.
- Optional tray presentation remains a user-session process by operator choice;
  no continuously resident privileged TimeLocker backend is required.
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
