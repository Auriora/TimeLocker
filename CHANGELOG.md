# Changelog

All notable changes to TimeLocker are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

TimeLocker currently declares package version `0.9.0` and Beta status. The repository has no release tags, so this file does not present an untagged version as
a published release. Detailed implementation history lives in the [updates index](docs/updates/index.md).

## [Unreleased]

### Added

- Explicit lifecycle states and review rules for plans and implementation updates.
- Live GitHub issue-state snapshot with current repository context and verification date.
- Automatic test workflow triggers for pushes and pull requests to `main` and `staging`.

### Changed

- Reconciled completed, active, and superseded plans against implementation evidence.
- Reviewed and approved the remaining May 2026 draft update records.
- Consolidated pytest configuration in `pyproject.toml` as the single source of truth.
- Made coverage artifacts and the measured 50% baseline mandatory in the GitHub Actions quality gate.
- Split timing-sensitive performance and stress checks into an explicit manual workflow job outside coverage instrumentation.
- Refreshed top-level documentation status and navigation for the current Beta posture.

### Fixed

- Removed stale task-map references to documentation files that no longer exist.
- Removed a missing update-index target and replaced ambiguous directory links with explicit documentation entry points.
- Aligned the package and version-bump configuration with the declared `0.9.0` project version.
- Stopped representing the historical `v1.0.0` design inventory as a released implementation.

## Current Beta Baseline

The current `0.9.0` codebase includes active CLI support for repository management, backup and recovery operations, file selection, scheduling, credential
management, monitoring, and service integration. Policy management is partially implemented. The REST API, desktop GUI, and database-backed storage remain
design work rather than released features.

See the [documentation status report](docs/DOCUMENTATION-STATUS.md) for the current feature boundary and the [active plans](docs/plans/README.md#active-plans)
for remaining consolidation work.

## Historical Design Material

The former `v1.0.0` changelog entry was an initial design specification, not evidence of a tagged or published release. Durable design material remains under
`docs/2-architecture/`; completed implementation history remains under `docs/updates/` and historical reports under `docs/archive/`.
