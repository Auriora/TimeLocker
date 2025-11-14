---
title: "Update: CLI Timeshift options and credential display unlock"
id: "update-cli-timeshift-options"
type: [ update ]
status: [ approved ]
owner: "AI Agent"
last_reviewed: "01-11-2025"
tags: [update, cli]
links:
  tooling: [pytest]
---

# Update: CLI Timeshift options and credential display unlock

- **Owner**: AI Agent
- **Created Date**: 01-11-2025
- **Audience**: Developers
- **Related**: N/A
- **Scope**: src/TimeLocker/cli.py

## 1. Purpose

Restore expected behaviour for integration tests covering Timeshift imports and credential visibility after recent CLI refactors.

## 2. Summary

- `repos credentials show` now unlocks the credential manager automatically (respecting the master password env var) before checking for stored secrets, so the
  integration test observes the previously saved AWS keys.
- `config import timeshift` now uses fixed defaults for repository and selection names (no legacy overrides) while still providing the fallback parser for
  builds without the service-layer importer. The command prints the detailed summary strings that tests expect, including explicit BTRFS detection text.
- Migrated legacy MinIO diagnostic scripts into pytest modules (`tests/TimeLocker/integration/test_per_repo_credentials.py`,
  `tests/TimeLocker/integration/test_minio_connection.py`) and ensured `.env` / `.env.test` are loaded automatically for integration suites.

## 3. Implementation Notes

- Key updates in `src/TimeLocker/cli.py`: unlock handling in `repos_credentials_show`, extended Timeshift command signature and fallback importer workflow.
- Testing:
    - `pytest tests/TimeLocker/integration/test_repos_credentials_integration.py -q`
    - `pytest tests/TimeLocker/integration/test_timeshift_cli_integration.py -q`
- Rules consulted: AGENT-GUIDE-Coding-Standards (priority 100), AGENT-RULE-Testing-Conventions (priority 25).

## 4. Documentation & Links

- No additional documentation updates required.

# References

- None.
