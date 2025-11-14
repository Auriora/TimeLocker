---
title: "CLI Deprecation Cleanup"
date: "2025-11-12"
type: [ update ]
status: [ completed ]
tags: [cli, selections, snapshots]
---

# CLI Deprecation Cleanup

## Summary

Completed the final cleanup pass of the TimeLocker CLI so that only the modern command surface is exposed. Snapshot lifecycle management now lives exclusively
under `tl snapshots`, recovery workflows live exclusively under `tl restore`, and backup creation only accepts selection-based inputs. No hidden flags,
compatibility shims, or deprecated command aliases remain in the CLI or user-facing documentation.

## Changes

- Removed all recovery-oriented subcommands from the `snapshots` namespace. The group now exposes only `list`, `show`, `find`, `forget`, `prune`, and `diff`.
  All restore/browse/mount flows must use the `restore` namespace.
- Updated the snapshots command tests to reflect the streamlined surface and removed fixtures that referenced the old commands.
- Eliminated the dormant `--target` flag and the Timeshift import overrides that were reintroduced during earlier refactors. The backup CLI exclusively accepts
  `--selection` or explicit source paths, and the Timeshift importer uses the standard defaults without user-specified compatibility switches.
- Scrubbed user documentation so that all examples and references use the selections system and the restore namespace. Historical docs that only existed to
  describe the deprecated surface were removed.

## Impact

- The CLI help output now matches the authoritative command hierarchy with no references to removed commands or flags.
- Tests no longer exercise incompatibility paths that can never be triggered.
- Documentation reflects the final product surface, keeping onboarding guides focused on the supported workflows.

## Verification

- `tl snapshots --help` displays only lifecycle commands.
- `tl restore --help` exposes the full recovery workflow.
- `tl backup create --help` documents `--selection` as the sole template option; invoking `--target` now results in the default Typer “no such option” error.
- Updated CLI unit and integration tests covering snapshots, backup, and Timeshift import paths.
