---
title: Documentation status
doc_type: reference
status: active
owner: Auriora Team
last_reviewed: 2026-07-18
---

# Documentation Status

## Current Assessment

The visible documentation tree is current-state oriented. Historical plans,
implementation diaries, reports, local issue/task snapshots, legacy Kiro
traceability, and unimplemented REST API/database designs are preserved only in
Git history.

## Implemented Product Surface

- CLI repository, backup, snapshot, restore, selection, credential, policy,
  scheduling, monitoring, and integration workflows.
- Filesystem/XDG configuration and Restic-backed snapshot storage.
- Optional system-tray integration.
- Pytest-based unit, integration, and environment-dependent test suites.

The repository does not currently implement a REST API, database application
store, desktop GUI, or mobile client. New future work belongs in GitHub or an
approved active spec.

## Current Work

- GitHub is authoritative for issue assignment and state.
- [Spec 001](./specs/001-cli-consolidation-stabilization/requirements.md) is
  authoritative for the active CLI consolidation and stabilization slice.
- [The active-spec index](./specs/README.md) lists all current delivery packages.

## Documentation Health

- Front-door navigation points to current guides, architecture, implementation,
  testing, processes, reference, and active specs.
- Current durable documents no longer depend on legacy `.kiro/specs/`, removed
  plans, old completion reports, or dated update files.
- Compact lifecycle evidence remains under `history/`; source packages are
  recoverable from their recorded Git commits.
- Code and tests remain the final authority where prose has not been freshly
  validated.

## Maintenance

- Before changing behavior, find the owning durable document and active spec.
- After changing behavior, update current durable docs and record evidence in
  the spec, commit, pull request, or CI result.
- Before release, validate installation, CLI references, test commands, version
  metadata, links, and active-spec closure state.
- Do not reintroduce historical milestone reports or unimplemented designs as
  current documentation.
