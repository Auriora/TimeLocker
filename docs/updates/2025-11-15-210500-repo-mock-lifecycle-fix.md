---
title: "Update: Repository Mock Lifecycle & Credential Flow"
id: "update-repo-mock-lifecycle-fix"
type: [ update ]
status: [ approved ]
owner: "Codex Agent"
last_reviewed: "15-11-2025"
tags: [update, cli, testing]
links:
  tooling: [pytest]
---

# Update: Repository Mock Lifecycle & Credential Flow

- **Owner**: Codex Agent
- **Created Date**: 15-11-2025
- **Audience**: Developers
- **Related**: Cluster #9 follow-ups (repository CLI integration)
- **Scope**: tests/TimeLocker, src/TimeLocker/cli_modules/testing

## 1. Purpose

Repository CLI integration tests were still red because the shared CLI service manager mock lacked lifecycle helpers (`update_repository_metadata/configuration`, state transitions) and credential rotation APIs. The CLI update command also now requires a realistic `ConfigurationManager`, so the previous fixture left commands without backing data. This change restores parity between the mocks and the real services so integration suites exercise the intended flows again.

## 2. Summary

- Expanded `create_mock_service_manager` (tests + shared testing package) with in-memory repository stores, metadata/configuration update helpers, repository state transitions, and credential rotation shims. These methods are exposed on both the service manager and `repository_service`.
- Updated the CLI integration fixture to supply an auto-populated configuration manager that mirrors the mock store, ensuring metadata updates report to the service manager for backward-compatible assertions.
- Added credential store tracking plus backend rotation helpers so credential rotation commands/tests can run without AttributeErrors.

## 3. Implementation Notes

- Key Paths:
  - `tests/TimeLocker/cli/test_utils.py`
  - `tests/TimeLocker/cli/test_repos_commands_integration.py`
  - `src/TimeLocker/cli_modules/testing/mocks.py`
- Testing:
  - `pytest tests/TimeLocker/cli/test_repos_commands_integration.py -k "update_repository_metadata or update_repository_configuration or lifecycle_complete or state_active_to_inactive or credential_rotation"`
- Follow-up: run the full repository CLI suite before merging broader refactors.

## 4. Documentation & Links

- Linked from `docs/updates/index.md`
- Reference plan: `docs/updates/2025-11-14-cli-test-failure-plan.md`

# References

- `docs/updates/2025-11-14-cli-test-failure-plan.md`
