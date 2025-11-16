---
title: "Update: Selection-first CLI docs refresh"
id: "update-selection-cli-docs-refresh"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [docs, cli, selection]
links:
  tooling: []
---

# Update: Selection-first CLI docs refresh

- **Owner**: Codex Agent  
- **Created Date**: 16-11-2025  
- **Audience**: Developers & CLI users  
- **Related**: README.md, docs/guides/user/backup-operations-troubleshooting.md  
- **Scope**: selection-focused documentation

## 1. Purpose

Document the removal of deprecated backup-target references from user-facing docs and highlight the canonical selection-driven workflow that now powers the CLI.

## 2. Summary

- Replaced the README’s `BackupTarget` example with SelectionTemplateManager + CLIServiceManager usage, including quick CLI snippets so users stay on the supported path.
- Updated the data-flow section to describe template definition, service-manager orchestration, and snapshot creation.
- Refreshed the backup troubleshooting guide so “test selections” instructions rely on `cli.run_selection_backup` instead of the deprecated repository/target API.

## 3. Notes

- These docs now align with Req 155 (CLI help/examples prefer selection templates over legacy targets).
- No functional code changes were required; only documentation was updated.

## 4. Tests

- Not applicable (documentation-only change).
