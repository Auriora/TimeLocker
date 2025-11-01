---
title: "Update: Docs Root Reorganization"
id: "update-20251101-docs-root-reorg"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "01-11-2025"
tags: [update, documentation, reorg]
links:
  tooling: []
---

# Update: Docs Root Reorganization

- **Owner**: Codex Agent
- **Created Date**: 01-11-2025
- **Audience**: Developers, Documentation Maintainers
- **Related**: Internal documentation cleanup request
- **Scope**: docs/ root structure

## 1. Purpose

Moved standalone markdown and resource files from the `docs/` root into their canonical subdirectories to align with the documentation taxonomy and remove redundant paths. Eliminated stale references caused by the relocation.

## 2. Summary

- Added a consolidated `docs/README.md` landing page covering navigation, quick starts, and maintenance expectations.
- Re-homed user-facing guides (installation, repository management, credentials, auto-completion, Timeshift import, S3 compatibility) under `docs/guides/user/`.
- Placed developer operations content (automation, scheduling, version management) in `docs/guides/developer/` and `docs/processes/`.
- Consolidated testing collateral—including MinIO setup walkthroughs and quickstarts—under `docs/4-testing/`, and moved CLI specifications and URI reference material into `docs/reference/`.
- Archived the generic document template inside `docs/_template/` and relocated `restic_commands.json` to `docs/resources/`.

## 3. Implementation Notes

- Updated all internal links and references to match the new file locations (e.g., MinIO guides, repository management references, installation guide lookups).
- Rules consulted/applied: `AGENT-GUIDE-General-Preferences` (priority 50), `AGENT-RULE-Documentation-Conventions` (priority 20).
- Testing: `grep -R` sweeps to confirm no references to deprecated root-level paths remain.

## 4. Documentation & Links

- `docs/guides/user/installation.md`
- `docs/guides/user/repository-management-guide.md`
- `docs/4-testing/guide-minio-testing.md`
- `docs/reference/timelocker-cli-command-hierarchy.md`
- `docs/processes/version-management.md`

# References

- Task directive: reorganize root documentation by folder purpose.
