---
title: "Update: Skipped Test Remediation Plan"
id: "update-2025-11-16-skipped-tests-plan"
type: [ update ]
status: [ draft ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [update, testing, cli]
links:
  tooling: [pytest]
---

# Update: Skipped Test Remediation Plan

- **Owner**: Codex Agent
- **Created Date**: 16-11-2025
- **Audience**: CLI/QA engineers
- **Related**: `docs/plans/2025-11-16-skipped-tests-remediation.md`
- **Scope**: Repository-wide test plan

## 1. Purpose

Document the approved plan for eliminating permanent `pytest.skip` decorators across CLI, monitoring, and service suites. The effort follows `AGENT-GUIDE-Planning-Protocol`, `AGENT-RULE-Documentation-Conventions`, and `AGENT-RULE-Testing-Conventions`.

## 2. Summary

- Catalogued all skip sites (registry, config/credentials, workflow, monitoring, S3 custom, and environment guards).
- Authored `docs/plans/2025-11-16-skipped-tests-remediation.md` outlining remediation per `.kiro/specs/cli-interface`, `configuration-management`, `security-services`, `repository-management`, `monitoring-reporting`, and `data-selection`.
- Defined success criteria: remove unconditional skips, modernize tests to current Typer commands, and keep only environment-gated skips with documentation.

## 3. Implementation Notes

- No code changes yet; next steps include logging bootstrap refactor, CLI integration test updates, notification adapter abstraction, and S3 custom template validation.
- Testing to be performed per area once changes are implemented (`pytest tests/TimeLocker/cli_modules/test_registry_integration.py`, etc.).
- Follow-up tasks: create issues per cluster after stakeholder review of the plan.

## 4. Documentation & Links

- Added `docs/plans/2025-11-16-skipped-tests-remediation.md`.
- Updated this log per documentation rule set; index entry added in `docs/updates/index.md`.

# References

- `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md`
- `docs/guides/ai-agent/AGENT-RULE-Documentation-Conventions.md`
- `docs/guides/ai-agent/AGENT-RULE-Testing-Conventions.md`
- `.kiro/specs/cli-interface/requirements.md`
