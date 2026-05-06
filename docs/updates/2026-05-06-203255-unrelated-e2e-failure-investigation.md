---
title: "Update: Unrelated E2E Failure Investigation"
id: "update-2026-05-06-203255-unrelated-e2e-failure-investigation"
type: [ update ]
status: [ draft ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, cli, e2e, repositories, backup]
links:
  tooling: [python-agent-ide, pytest]
---

# Update: Unrelated E2E Failure Investigation

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers
- **Related**: `tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py`, `tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py`, `repositories.py`, `backup.py`
- **Scope**: Investigation only

## 1. Purpose

Record the unrelated E2E failures observed after the CLI static-analysis cleanup commit.

## 2. Findings

- [x] `repos add --set-default` fails before repository persistence fallback completes.
- [x] `test_selection_driven_backup_flow` patches a stale backup command module attribute.

The repository setup failure reproduces in `TestCLIPolicyEndToEndFlows::test_policy_lifecycle_flow` with
`Failed to add repository: Repository 'docs-policy-repo' not found`.

The likely cause is command ordering in `repos_add`: the service-manager `add_repository` path runs before `set_default_repository`, but the command only performs
the direct `ConfigService` persistence fallback after the default-repository call. `CLIServiceManager.add_repository` uses `ConfigurationService.add_repository`
first, and that service mutates in-memory config without saving to the legacy `ConfigurationModule` path used by `set_default_repository`. The fallback that would
write through `ConfigService` is too late for `--set-default`.

The backup patch failure reproduces in `TestCLIEndToEndWorkflows::test_selection_driven_backup_flow`:
`backup.get_cli_service_manager` does not exist. `backup.py` imports `_get_service_manager_for_command`, not `get_cli_service_manager`; the previous committed
version had the same import shape, so this is not introduced by the static-analysis cleanup.

## 3. Validation

- `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_policy_flows.py::TestCLIPolicyEndToEndFlows::test_policy_lifecycle_flow -q`: failed as expected.
- `python -m pytest tests/TimeLocker/cli/test_cli_end_to_end_user_flows.py::TestCLIEndToEndWorkflows::test_selection_driven_backup_flow -q`: failed as expected.
- `git show 19c7ac8:src/TimeLocker/cli_modules/commands/backup.py` confirmed the missing `get_cli_service_manager` patch target predates the latest cleanup.

## 4. Recommended Next Slice

Fix the `repos add --set-default` ordering/persistence issue first because it blocks multiple E2E flows. Then update the backup E2E patch target or restore a
module-level compatibility alias in `backup.py`, depending on the preferred testing contract.

# References

- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
