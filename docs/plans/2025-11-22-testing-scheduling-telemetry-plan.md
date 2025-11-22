---
title: "RFC: Stabilize CLI repo tests, scheduling adapters, and telemetry guardrails"
id: "rfc-2025-11-22-testing-scheduling-telemetry"
type: [ plan ]
status: [ accepted ]
owner: "Codex AI Agent"
last_reviewed: "22-11-2025"
tags: [plan, testing, scheduling, telemetry]
links:
  tooling: [pytest]
---

# RFC: Stabilize CLI repo tests, scheduling adapters, and telemetry guardrails

- **Owner**: Codex AI Agent
- **Status**: Accepted
- **Last Updated**: 22-11-2025
- **Created Date**: 22-11-2025
- **Audience**: Engineering, QA, Observability

## 1. Purpose

Deliver a short, high-impact stabilization pass to close the known CLI repository test failures, validate scheduling adapters against the automation
requirements, and harden the new PostHog/OpenTelemetry integration so it is safe-by-default in CI and offline environments.

## 2. Problem Statement

- Repository CLI tests are still failing due to incomplete service mocking and mock/dict mismatches (see `docs/test-failure-analysis-summary.md`).
- Scheduling adapters have requirements in `.kiro/specs/scheduling-automation/requirements.md` that have not been fully exercised or verified after recent
  refactors.
- Telemetry was newly added (see `docs/updates/2025-11-22-120000-posthog-telemetry.md`); CI needs non-network defaults and guardrails to avoid flaky runs.

## 3. Proposed Solution

1) **Test stabilization:**
    - Patch CLI repository tests to use dict fixtures for repositories and fully mock service methods and configuration lookups.
    - Add focused unit tests for service-layer mocks to prevent regressions.
2) **Scheduling verification:**
    - Create minimal platform-adapter contract tests (feature-flagged) that assert requirement coverage for schedule generation and conflict detection.
    - Add dry-run validation path so adapters can be tested without invoking OS schedulers.
3) **Telemetry guardrails:**
    - Default telemetry to disabled in CI/dev when env vars are absent; add safe no-op exporters.
    - Add unit tests covering env parsing and backend selection without network I/O.

## 4. Alternatives

- Keep skipping failing tests and rely on manual runs (rejected: hides regressions).
- Remove telemetry integration until a later release (rejected: feature already merged and documented).
- Limit scheduling checks to documentation-only validation (rejected: risk of runtime gaps).

## 5. Impact

- **Affected areas:** `tests/TimeLocker/cli/*`, `tests/TimeLocker/monitoring/*`, `src/TimeLocker/monitoring/telemetry.py`, `src/TimeLocker/scheduling/*`.
- **Risks:** Over-mocking could mask real integration issues; scheduling dry-runs must not mutate host schedulers.
- **Mitigations:** Use dict-based fixtures mirroring real objects; keep dry-run behind env/flag; add coverage for failure paths.
- **Rollout:** Land as one stabilization PR with clear test matrix (unit + optional platform-tagged tests).

## 6. Decision Log

- 22-11-2025: Draft plan created for review. Pending approval from maintainers.

# References

- `.kiro/specs/scheduling-automation/requirements.md`
- `.kiro/specs/integration-architecture/design.md`
- `.kiro/specs/monitoring-reporting/`
- `docs/test-failure-analysis-summary.md`
- `docs/updates/2025-11-22-120000-posthog-telemetry.md`
- `pyproject.toml` (pytest config, dependencies)
