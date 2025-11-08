---
title: "Update: CLI URI validation and credential manager usage"
id: "update-cli-uri-validation-credential-manager"
type: [ update ]
status: [ approved ]
owner: "AI Agent"
last_reviewed: "01-11-2025"
tags: [update, cli]
links:
  tooling: [pytest]
---

# Update: CLI URI validation and credential manager usage

- **Owner**: AI Agent
- **Created Date**: 01-11-2025
- **Audience**: Developers
- **Related**: N/A
- **Scope**: src/TimeLocker/cli.py

## 1. Purpose

Resolve regression test failures around repository URI validation and credential manager mocking by tightening CLI checks and isolating per-invocation
credential manager instances.

## 2. Summary

Added explicit allow-list validation for repository URI schemes in `repos add`, ensuring malformed values such as `invalid://` or incomplete `s3://` URLs fail
early with actionable messaging. Updated `repos credentials set` to construct a fresh credential manager for each invocation, reattaching it to the service
factory when present. This restores deterministic behaviour for mocked tests and prevents stale singletons from leaking across commands.

## 3. Implementation Notes

- Key updates in `src/TimeLocker/cli.py`: URI validation now leverages `urlparse` with scheme checks and additional file URI safeguards; credential manager
  acquisition always calls `_create_credential_manager` and updates the repository factory reference.
- Testing:
    - `pytest tests/TimeLocker/cli/test_cli_error_handling.py::TestCLIErrorHandling::test_invalid_repository_uri_validation -q`
    - `pytest tests/TimeLocker/cli/test_repos_credentials_commands.py -q`
- Rules consulted: AGENT-GUIDE-Coding-Standards (priority 100), AGENT-RULE-Testing-Conventions (priority 25).
- Follow-up tasks: None.

## 4. Documentation & Links

- No additional documentation updates required.

# References

- None.
