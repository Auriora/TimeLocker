---
title: "Update: Credential store + repository manager stabilization"
id: "update-2025-11-15-credential-repo-manager"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, credentials, repository-manager, cli]
links:
  tooling: [pytest]
---

# Update: Credential store + repository manager stabilization

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: docs/updates/2025-11-14-cli-test-failure-plan.md
- **Scope**: src/TimeLocker/security, services/repository_manager, CLI snapshots & credentials commands

## 1. Purpose

Continue executing milestone #2 of the CLI failure plan by fixing credential-store initialization, repository manager persistence, and the downstream multi-backend/plugin tests that depend on both.

## 2. Summary

- `CredentialManager` now defaults to `~/.timelocker/credentials` (with optional override) so tests that isolate `HOME` observe the encrypted store and CLI fixtures stop writing into `/tmp/config/timelocker`.
- Repository manager persistence is reliable again: `_load/_save` guard against mock objects, `ConfigurationManager.save_config()` accepts optional payloads, and new repository creations call a credential-hook so service tests can assert `store_credentials` interactions.
- `tl repos credentials set/show` prompts work inside Typer's CliRunner by forcing interactive mode, and `tl snapshots …` commands accept `--config-dir`, allowing credential suites to run entirely inside their sandbox.
- Plugin registry / capability interfaces share the same `BackupEngine` enum as repository models and expose `EngineCapabilities.supported_backends`, aligning with integration expectations.

## 3. Implementation Notes

- Key files: `src/TimeLocker/security/credential_manager.py`, `src/TimeLocker/services/repository_manager.py`, `src/TimeLocker/config/configuration_manager.py`, `src/TimeLocker/cli.py`, `src/TimeLocker/cli_modules/commands/snapshots.py`, `src/TimeLocker/interfaces/backup_engine_plugin.py`.
- Rules consulted/applied: `AGENT-GUIDE-General-Preferences`, `AGENT-GUIDE-Coding-Standards`, `AGENT-RULE-Documentation-Conventions`.
- Tests:
  - `pytest tests/TimeLocker/integration/test_repos_credentials_command_usage.py`
  - `pytest tests/TimeLocker/integration/test_repos_credentials_integration.py::test_backend_credentials_store_and_show_s3`
  - `pytest tests/TimeLocker/integration/test_repository_multi_backend_integration.py`

## 4. Documentation & Links

- Tracking doc: `docs/updates/2025-11-14-cli-test-failure-plan.md`

# References

- docs/updates/2025-11-14-cli-test-failure-plan.md
