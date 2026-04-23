---
title: "Update: Repository unlock contract cleanup"
id: "update-2026-04-23-142743-repo-unlock-contract-cleanup"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [update, cli, repositories, testing]
links:
  tooling: [pytest]
---

# Update: Repository unlock contract cleanup

- **Owner**: Codex
- **Created Date**: 23-04-2026
- **Audience**: Developers
- **Related**: CLI consolidation follow-up
- **Scope**: `src/TimeLocker/cli_modules/commands/repositories.py`, `tests/TimeLocker/cli/test_repos_commands.py`

## 1. Purpose

Remove the shadowed duplicate `repos unlock` implementation so the source matches the currently exposed public CLI contract, then add command-graph coverage
to prevent duplicate registration from silently returning.

## 2. Summary

- Removed the earlier security-session-oriented `repos unlock` command definition that was being shadowed by the later service-level `repos unlock`
  definition.
- Preserved the public unlock contract that the runtime CLI currently exposes: `name`, `--repository`, `--password`, `--verbose`, and `--config-dir`.
- Added unit coverage that inspects the built command graph and asserts:
  - `repos unlock` exists exactly once
  - its parameter surface matches the service-level unlock command

## 3. Implementation Notes

- Updated the repository command module to leave only one public `unlock` command.
- Added direct command-graph assertions using Typer/Click command introspection in the repo command tests.
- Testing performed:
  - targeted repo command unit tests for unlock contract coverage
- Follow-up tasks:
  - decide whether the removed security-session unlock behavior should reappear under a different command name in the later CLI decomposition
  - continue extracting shared repository command orchestration helpers before splitting the file

## 4. Documentation & Links

- Rules consulted: `AGENT-GUIDE-General-Preferences`, `AGENT-RULE-Testing-Conventions`, `AGENT-RULE-Documentation-Conventions`
- Rules applied: task-scoped update logging in `docs/updates/`, targeted unit coverage for changed public behavior

# References

- `docs/guides/ai-agent/AGENT-GUIDE-General-Preferences.md`
- `docs/guides/ai-agent/AGENT-RULE-Testing-Conventions.md`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
