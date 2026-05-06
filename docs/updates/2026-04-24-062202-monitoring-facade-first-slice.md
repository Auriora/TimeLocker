---
title: "Update: Monitoring Facade First Slice"
id: "update-2026-04-24-062202-monitoring-facade-first-slice"
type: [ update ]
status: [ approved ]
owner: "Codex"
last_reviewed: "24-04-2026"
tags: [update, cli, monitoring, service-facade, testing]
links:
  tooling: [pytest, python-agent-ide]
---

# Update: Monitoring Facade First Slice

- **Owner**: Codex
- **Created Date**: 24-04-2026
- **Audience**: Developers, Reviewers
- **Related**: `docs/guides/developer/cli-service-layer-migration.md`
- **Scope**: `src/TimeLocker/cli_modules/commands/monitoring.py`

## 1. Purpose

Capture the first modular CLI refactor slice that moves a real command module toward the `ServiceFacade` access path without widening the change beyond a single file.

## 2. Summary

This slice refactors `src/TimeLocker/cli_modules/commands/monitoring.py` to create a module-local `ServiceFacade` and route command setup through that facade instead of repeated direct service-manager construction.

The migration stays compatible with existing test patch points by keeping service-manager lookup inside the module before creating the facade. It also fixes one adjacent bug in the same module where the storage-usage report path referenced an undefined `config_module` variable instead of `config_service`.

## 3. Implementation Notes

- Updated code path:
  - `src/TimeLocker/cli_modules/commands/monitoring.py`
- Refactoring details:
  - added `_setup_monitoring_facade(config_dir)`
  - switched status, operations, history, stats, log-search, log-recent, report-generation, and health-data setup to use the facade
  - retrieved configuration data through `facade.get_configuration_service()`
  - retained manager-backed monitoring calls via `facade.service_manager`
- Testing performed:
  - `python3 -m pytest -q tests/TimeLocker/cli/test_monitoring_commands.py`
- Follow-up tasks:
  - extend `ServiceFacade` with explicit monitoring helpers so command modules stop reaching through `facade.service_manager`
  - migrate the next CLI module with a similar bounded pattern, likely `repositories.py` or `restore.py`

## 4. Documentation & Links

- Migration guidance:
  - `docs/guides/developer/cli-service-layer-migration.md`
- Architecture background:
  - `docs/3-implementation/service-facade.md`
  - `docs/3-implementation/service-layer-integration.md`

# References

- `src/TimeLocker/cli_modules/commands/monitoring.py`
- `tests/TimeLocker/cli/test_monitoring_commands.py`
- `docs/guides/developer/cli-service-layer-migration.md`
