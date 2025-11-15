---
title: "Update: CLI repos commands test alignment"
id: "update-2025-11-15-cli-repos-commands-tests"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, testing, cli]
links:
  tooling: [pytest]
---

# Update: CLI repos commands test alignment

- **Owner**: Codex Agent
- **Created Date**: 2025-11-15
- **Audience**: Developers
- **Related**: docs/updates/2025-11-14-cli-test-failure-plan.md
- **Scope**: tests/TimeLocker/cli

## 1. Purpose

Complete item 9 of the CLI test failure plan by updating the `repos` command suite to the current service-layer wiring. The old mocks intercepted `TimeLocker.cli_services` directly, but commands now call through `src.TimeLocker.cli.get_cli_service_manager`. The test expectations also assumed legacy error paths, so successful command runs were treated as failures.

## 2. Summary

- Retargeted every `@patch` in `tests/TimeLocker/cli/test_repos_commands.py` to `src.TimeLocker.cli.get_cli_service_manager`, ensuring the suite exercises the mock service manager instead of the real singleton.
- Added a `ConfigurationManager` patch to `test_repos_remove_command` and reused the deterministic repository fixture so delete flows no longer fail before hitting service mocks.
- Updated the remaining CLI repos command tests (check/stats/unlock/migrate/forget/validate-all) to expect successful exits now that the service mocks handle those operations end to end.

## 3. Implementation Notes

- Key file: `tests/TimeLocker/cli/test_repos_commands.py`.
- Rules consulted: `AGENT-GUIDE-General-Preferences`, `AGENT-GUIDE-Coding-Standards`, `AGENT-RULE-Testing-Conventions`, `AGENT-RULE-Documentation-Conventions`.
- Tests:
  - `pytest tests/TimeLocker/cli/test_repos_commands.py -q`

## 4. Documentation & Links

- Reference plan: `docs/updates/2025-11-14-cli-test-failure-plan.md`.

# References

- docs/updates/2025-11-14-cli-test-failure-plan.md
