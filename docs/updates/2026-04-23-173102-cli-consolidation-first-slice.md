---
title: "Update: CLI Consolidation First Slice"
id: "update-2026-04-23-173102-cli-consolidation-first-slice"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "23-04-2026"
tags: [update, cli, consolidation, testing]
links:
  tooling: [pytest, python-agent-ide]
---

# Update: CLI Consolidation First Slice

- **Owner**: Codex
- **Created Date**: 23-04-2026
- **Audience**: Developers, Reviewers
- **Related**: `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`
- **Scope**: `src/TimeLocker/cli.py`, CLI help tests

## 1. Purpose

Capture the first executed slice of the CLI consolidation plan: reduce the duplicated CLI registration seam in `src/TimeLocker/cli.py` without changing user-facing
command behavior.

## 2. Summary

This slice did two things:

- introduced a small `_merge_typer_app()` helper in `src/TimeLocker/cli.py` so hybrid command groups no longer duplicate manual `registered_commands` and
  `registered_groups` append loops
- removed the duplicate `security` app mount by merging modular security commands into the already-mounted root `security_app`

This keeps the first stabilization step narrow and directly addresses one of the highest-risk registration inconsistencies found during repo exploration.

Rules consulted: `AGENT-GUIDE-General-Preferences` (priority 50), `AGENT-GUIDE-Operational-Best-Practices` (priority 40), `AGENT-GUIDE-Coding-Standards`
(priority 100), `AGENT-RULE-Documentation-Conventions` (priority 20), `AGENT-RULE-Testing-Conventions` (priority 25). Rules applied: all listed. Overrides:
none.

## 3. Implementation Notes

- Updated code paths:
  - `src/TimeLocker/cli.py`
  - `tests/TimeLocker/cli/test_cli_help_system.py`
- Added regression coverage:
  - `test_top_level_command_names_are_unique`
- Testing performed:
  - `python3 -m pytest tests/TimeLocker/cli/test_cli_help_system.py tests/TimeLocker/cli/test_cli_help_tree_walk.py -q`
- Follow-up tasks:
  - standardize config access on `ConfigService`
  - standardize repository resolution on `cli_modules.services.RepositoryResolver`
  - reduce `CLIServiceManager` compatibility logic

## 4. Documentation & Links

- Added plan: `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`
- This update is indexed in `docs/updates/index.md`
- `docs/plans/README.md` updated to include the new plan

# References

- `src/TimeLocker/cli.py`
- `tests/TimeLocker/cli/test_cli_help_system.py`
- `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`
