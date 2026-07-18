# Changelog

All notable changes to TimeLocker are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

TimeLocker currently declares package version `0.9.0` and Beta status. The
repository has no release tags, so this file does not present an untagged
version as a published release. Git history retains implementation detail;
[`docs/history/spec-closure-log.md`](docs/history/spec-closure-log.md) provides
compact discovery for closed specification packages.

## [Unreleased]

### Added

- Active specification lifecycle governance, deterministic readiness checks,
  durable-document promotion, and compact closure history.
- Automatic test workflow triggers for pushes and pull requests to `main` and
  `staging`.

### Changed

- Consolidated pytest configuration in `pyproject.toml` as the source of truth,
  including the 50 percent coverage gate.
- Reorganized documentation around current requirements, architecture,
  implementation, testing, guides, references, and temporary active specs.
- Centralized repository agent instructions under `docs/guides/ai-agent/`.

### Fixed

- Removed stale navigation to deleted plans, update diaries, archives, and
  superseded requirement/design packages.
- Aligned package and version-bump configuration with the declared `0.9.0`
  project version.
- Stopped representing historical `v1.0.0` design inventory as a released
  implementation.

## Current Beta Baseline

The current `0.9.0` codebase includes CLI support for repository management,
backup and recovery, file selection, scheduling, credentials, monitoring, and
service integration. Policy management is partially implemented. The REST API,
desktop GUI, and database-backed storage remain design ideas rather than
released features.

See the [documentation status](docs/DOCUMENTATION-STATUS.md) for the current
feature boundary and the [active specification index](docs/specs/README.md) for
approved work in progress.

## Historical Design Material

The former `v1.0.0` changelog entry was an initial design specification, not
evidence of a tagged or published release. Current design belongs under
`docs/2-architecture/`; superseded plans, reports, and implementation diaries
remain recoverable through Git history.
