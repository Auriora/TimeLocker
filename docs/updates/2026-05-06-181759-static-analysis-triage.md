---
title: "Update: Static Analysis Triage"
id: "update-2026-05-06-181759-static-analysis-triage"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, static-analysis, cli, triage]
links:
  tooling: [python-agent-ide, basedpyright, ruff]
---

# Update: Static Analysis Triage

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`
- **Scope**: Pre-existing static-analysis findings in CLI command modules

## 1. Purpose

Identify which pre-existing static-analysis findings are worth addressing first after the ConfigService command standardization slice.

## 2. Summary

Python Agent IDE diagnostics over the large CLI command modules remain noisy, but several findings correspond to likely runtime defects or stale command/API
contracts. These are higher value than broad unused-import cleanup.

## 3. Implementation Notes

Highest-value findings to address:

- `src/TimeLocker/cli_modules/commands/credentials.py`: `_ensure_manager_unlocked()` calls `CredentialManager.is_unlocked()`, but the concrete manager exposes `is_locked()`. This can break credential store fallback paths when not fully mocked.
- `src/TimeLocker/cli_modules/commands/config.py`: `config_validate()` and `config_diff()` call `ConfigurationPathResolver.get_config_file()`, but the resolver exposes `get_config_file_path()`. These commands likely fail when no explicit file is provided.
- `src/TimeLocker/cli_modules/commands/policy.py`: policy simulation displays `storage_impact.bytes_freed`, while the model exposes `estimated_space_freed_bytes`. This can fail on successful simulation result display.
- `src/TimeLocker/cli_modules/commands/policy.py`: policy enforcement passes `repository_uri=repo_config.get('uri') or repo_config.get('location')` without guarding the missing case, despite `EnforcementContext` requiring a string.
- `src/TimeLocker/cli_modules/commands/backup.py`: `backup_create()` lets `sources` default to `None` even though `CLIBackupRequest.sources` is `List[Path]`, and can pass a missing repository name into credential resolution.
- `src/TimeLocker/cli_modules/commands/backup.py`: the command checks for a legacy `service_manager.execute_backup` method that is not defined on `CLIServiceManager`; tests mock it, but runtime should primarily use `execute_backup_from_cli()`.
- `src/TimeLocker/cli_modules/commands/repositories.py`: S3 credential payload typing mixes string and boolean values; this is lower risk but related to real helper contracts.

Lower-value findings to defer:

- Large-scale `F401` unused imports in generated/extracted command modules.
- `F541` f-strings without placeholders.
- Python 3.9/3.10 typing-style modernization warnings.
- Broad `Any` and unknown-type warnings from legacy helper boundaries.

Validation:

- `diagnostics_for_files` over command modules and `ConfigService`: 229 error-level findings and 1144 warning-level findings; targeted result trust was usable while background warmup was refreshing.
- Direct source inspection confirmed the top API-mismatch findings above.

## 4. Documentation & Links

- `src/TimeLocker/cli_modules/commands/credentials.py`
- `src/TimeLocker/cli_modules/commands/config.py`
- `src/TimeLocker/cli_modules/commands/policy.py`
- `src/TimeLocker/cli_modules/commands/backup.py`
- `src/TimeLocker/cli_modules/commands/repositories.py`

# References

- `docs/updates/2026-05-06-181418-cli-configservice-command-standardization.md`
