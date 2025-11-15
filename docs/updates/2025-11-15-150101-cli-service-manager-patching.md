---
title: "Update: CLI service-manager patch alignment"
id: "update-2025-11-15-cli-service-manager-patching"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, testing, cli]
links:
  tooling: [pytest]
---

# Update: CLI service-manager patch alignment

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: docs/updates/2025-11-14-cli-test-failure-plan.md
- **Scope**: tests/TimeLocker/cli

## 1. Purpose

Extend the service-manager mocking fix from the repos suite to the rest of the CLI test batteries so every command exercises the shared mock factory introduced in plan item 9. Several suites were still intercepting `src.TimeLocker.cli_services.get_cli_service_manager`, which bypassed the real entry point used by the live CLI.

## 2. Summary

- Updated `tests/TimeLocker/cli/test_cli_integration.py`, `tests/TimeLocker/cli/test_snapshots_commands.py`, and `tests/TimeLocker/cli/test_cli_error_handling.py` to patch `src.TimeLocker.cli.get_cli_service_manager`, matching the import path used at runtime.
- Adjusted the legacy keyboard-interrupt regression test (still skipped) to intercept `_get_service_manager_for_command` from the same module for consistency.
- Verified that the CLI integration, snapshot, and error-handling suites still pass with the new patch target, proving that the mocks now flow through the CLI module.

## 3. Implementation Notes

- Key files: `tests/TimeLocker/cli/test_cli_integration.py`, `tests/TimeLocker/cli/test_snapshots_commands.py`, `tests/TimeLocker/cli/test_cli_error_handling.py`.
- Rules consulted: `AGENT-GUIDE-General-Preferences`, `AGENT-GUIDE-Coding-Standards`, `AGENT-RULE-Testing-Conventions`, `AGENT-RULE-Documentation-Conventions`.
- Tests:
  - `pytest tests/TimeLocker/cli/test_cli_integration.py -q`
  - `pytest tests/TimeLocker/cli/test_snapshots_commands.py -q`
  - `pytest tests/TimeLocker/cli/test_cli_error_handling.py -q`

## 4. Documentation & Links

- Reference plan: `docs/updates/2025-11-14-cli-test-failure-plan.md`.

# References

- docs/updates/2025-11-14-cli-test-failure-plan.md
