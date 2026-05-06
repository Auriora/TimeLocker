---
title: "Update: Policy Date Static Analysis Cleanup"
id: "update-2026-05-06-195516-policy-date-static-analysis-cleanup"
type: [ update ]
status: [ approved ]
owner: "Agent"
last_reviewed: "06-05-2026"
tags: [update, static-analysis, cli, policy]
links:
  tooling: [python-agent-ide, pytest, basedpyright, ruff]
---

# Update: Policy Date Static Analysis Cleanup

- **Owner**: Agent
- **Created Date**: 06-05-2026
- **Audience**: Developers, maintainers
- **Related**: `docs/updates/2026-05-06-190611-static-analysis-runtime-api-cleanup.md`
- **Scope**: Policy CLI optional datetime handling

## 1. Purpose

Address the next narrow static-analysis slice after the CLI runtime/API cleanup by fixing `policy.py` optional datetime display paths.

## 2. Summary

The policy command module now formats optional datetime-like fields through small helpers instead of calling `.isoformat()` or `.strftime()` after only checking
that an attribute exists. This clears the remaining blocker-level `policy.py` optional member access diagnostics while preserving CLI JSON and table output.

## 3. Implementation Notes

- Added `_format_optional_datetime()` and `_optional_isoformat()` helpers.
- Updated backup policy, retention policy, assignment, and audit timestamp rendering to tolerate missing or `None` datetime values.
- Removed clearly unused policy command imports surfaced by Ruff.
- Replaced a placeholder-free f-string in assignment deletion output.
- Validation:
  - Python Agent IDE `diagnostics_for_change` on `src/TimeLocker/cli_modules/commands/policy.py`: 0 error-level findings; remaining diagnostics are warnings around legacy typing and command-helper boundaries.
  - `git diff --check`: passed.
  - `python -m pytest tests/TimeLocker/cli/test_policy_commands.py -q`: 13 passed.

## 4. Documentation & Links

- `src/TimeLocker/cli_modules/commands/policy.py`
- `docs/updates/index.md`

# References

- `docs/updates/2026-05-06-181759-static-analysis-triage.md`
- `docs/updates/2026-05-06-190611-static-analysis-runtime-api-cleanup.md`
