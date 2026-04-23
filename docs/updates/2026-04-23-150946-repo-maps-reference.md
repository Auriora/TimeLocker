---
title: "Update: Repository maps reference"
id: "update-2026-04-23-150946-repo-maps-reference"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [update, documentation, onboarding, reference]
links:
  tooling: [python-agent-ide]
---

# Update: Repository maps reference

- **Owner**: Codex
- **Created Date**: 23-04-2026
- **Audience**: Developers, contributors
- **Related**: Repo onboarding and change-navigation docs
- **Scope**: `docs/reference/repo-orientation-and-change-map.md`, `docs/reference/README.md`, `docs/README.md`, `docs/updates/index.md`

## 1. Purpose

Store the repo exploration results in project documentation so the CLI map, subsystem map, and change map live in `docs/` and can be reused by future
contributors.

## 2. Summary

- Added a new reference document covering:
  - live CLI command groups
  - package/subsystem boundaries
  - practical starting points for common code changes
- Linked the new reference from the reference docs index.
- Linked the new reference from the main docs hub architecture section.

## 3. Implementation Notes

- The CLI map was based on the actual Typer app wiring in `src/TimeLocker/cli.py`, with supporting confirmation from command modules and the existing CLI
  hierarchy reference.
- The subsystem and change maps were based on runtime-backed repo exploration plus direct verification of package layout.
- Testing performed:
  - documentation-only review
- Rules consulted: `AGENT-GUIDE-General-Preferences`, `AGENT-RULE-Documentation-Conventions`
- Rules applied: docs placed under `docs/reference/`, docs hub cross-links updated, task-scoped update logged in `docs/updates/`

## 4. Documentation & Links

- Added [repo-orientation-and-change-map.md](../reference/repo-orientation-and-change-map.md)
- Updated [docs/reference/README.md](../reference/README.md)
- Updated [docs/README.md](../README.md)

# References

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
