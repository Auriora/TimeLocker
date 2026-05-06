---
title: "Update: CLI ConfigService Command Standardization"
id: "update-2026-05-06-181418-cli-configservice-command-standardization"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, cli, config-service, tests]
links:
  tooling: [python-agent-ide, pytest, basedpyright, ruff]
---

# Update: CLI ConfigService Command Standardization

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`
- **Scope**: CLI command modules and ConfigService compatibility access

## 1. Purpose

Complete the CLI consolidation slice that standardizes command-module configuration access on `ConfigService`.

## 2. Summary

Command modules no longer import or instantiate `ConfigurationModule` directly. Legacy APIs that still require a configuration module now receive it through
an explicit `ConfigService.get_legacy_config_module()` compatibility accessor.

## 3. Implementation Notes

- Added `ConfigService.get_legacy_config_module()` for compatibility adapters that still require `ConfigurationModule`.
- Removed unused `_create_configuration_module` imports from CLI command modules.
- Removed direct `ConfigurationModule` imports from `config.py` and `repositories.py`.
- Updated repository credential storage to use the ConfigService compatibility accessor instead of private `_config_module` access.
- Updated `security config` to create `ConfigService` first and pass the compatibility module into `SecurityConfigurationCLI`.
- Added an AST-based regression test that flags direct command-module imports, constructor references, or private `_config_module` access.
- Validation:
  - `diagnostics_for_files` on touched command, service, and test files: direct results usable while Python Agent IDE background warmup was refreshing; many pre-existing static-analysis findings remain in broad command modules.
  - `diagnostics_for_files` on `tests/TimeLocker/cli_modules/commands/test_config_service_integration.py`: 0 error-level findings and 0 Ruff findings.
  - `python -m pytest tests/TimeLocker/cli_modules/commands/test_config_service_integration.py tests/TimeLocker/cli_modules/services/test_config_service.py -q`: 61 passed.

## 4. Documentation & Links

- `src/TimeLocker/cli_modules/services/config_service.py`
- `src/TimeLocker/cli_modules/commands/config.py`
- `src/TimeLocker/cli_modules/commands/repositories.py`
- `src/TimeLocker/cli_modules/commands/security.py`
- `tests/TimeLocker/cli_modules/commands/test_config_service_integration.py`
- `docs/plans/2026-04-23-173102-cli-consolidation-stabilization-plan.md`

# References

- `docs/updates/2026-05-06-175815-servicefacade-alignment-slice.md`
