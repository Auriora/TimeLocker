---
title: "Update: Scheduling dry-run validation and telemetry CI guardrails"
id: "update-2025-11-22-150500-scheduling-telemetry-guardrails"
type: [ update ]
status: [ approved ]
owner: "Codex AI Agent"
last_reviewed: "22-11-2025"
tags: [update, testing, scheduling, telemetry]
links:
  tooling: [pytest]
---

# Update: Scheduling dry-run validation and telemetry CI guardrails

- **Owner**: Codex AI Agent
- **Created Date**: 22-11-2025
- **Audience**: Developers, QA
- **Related**: `.kiro/specs/scheduling-automation`, `docs/test-failure-analysis-summary.md`
- **Scope**: scheduling, monitoring

## 1. Purpose

Add contract-level scheduling tests that exercise dry-run validation without touching host schedulers, and harden telemetry to default-off in CI unless
explicitly opted in.

## 2. Summary

- Added fake platform adapter contract tests covering platform validation errors and dry-run execution to prevent accidental scheduler writes.
- Introduced CI-aware telemetry configuration that stays disabled unless explicitly opted in, even when API keys are present.

## 3. Implementation Notes

- New tests: `tests/TimeLocker/scheduling/test_schedule_validator_contracts.py`.
- Telemetry guardrails: CI opt-out in `TelemetryConfig.from_env` plus test coverage.
- Testing: `pytest tests/TimeLocker/scheduling/test_schedule_validator_contracts.py tests/TimeLocker/monitoring/test_telemetry.py`.

## 4. Documentation & Links

- Specs referenced: `.kiro/specs/scheduling-automation/requirements.md`.
- Telemetry update referenced by: `docs/updates/2025-11-22-120000-posthog-telemetry.md`.

# References

- `.kiro/specs/scheduling-automation/requirements.md`
- `docs/test-failure-analysis-summary.md`
