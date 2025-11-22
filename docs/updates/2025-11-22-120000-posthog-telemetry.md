---
title: "Update: PostHog telemetry integration via OpenTelemetry"
id: "update-2025-11-22-120000-posthog-telemetry"
type: [ update ]
status: [ approved ]
owner: "Codex AI Agent"
last_reviewed: "22-11-2025"
tags: [update, monitoring, telemetry]
links:
  tooling: [pytest]
---

# Update: PostHog telemetry integration via OpenTelemetry

- **Owner**: Codex AI Agent
- **Created Date**: 22-11-2025
- **Audience**: Developers, Observability
- **Related**: Monitoring & Reporting spec, Integration Architecture
- **Scope**: CLI, monitoring telemetry

## 1. Purpose

Add PostHog analytics support using OpenTelemetry so telemetry backends can be swapped without touching call sites. Ensure exceptions are captured as spans and
that telemetry can be disabled or re-pointed via configuration.

## 2. Summary

- Introduced `monitoring.telemetry` module that configures OTLP/HTTP exporters for PostHog (EU region) with sampler control and fail-open behaviour.
- Wired CLI entrypoint to initialise telemetry on startup and record uncaught exceptions as spans without affecting exit codes.
- Exposed env configuration: `POSTHOG_API_KEY`, `POSTHOG_OTLP_ENDPOINT` (default `https://eu.i.posthog.com`), `TIMELOCKER_TELEMETRY_ENABLED`, and
  `TIMELOCKER_TELEMETRY_SAMPLE_RATIO`.

## 3. Implementation Notes

- New module: `src/TimeLocker/monitoring/telemetry.py` (resource setup, exporter factories, exception recorder).
- CLI startup now calls `setup_telemetry_from_env()`; exceptions flow through `record_exception` before re-raising.
- Added unit coverage in `tests/TimeLocker/monitoring/test_telemetry.py` using dummy exporters to avoid network calls.
- Added opt-in system test `tests/TimeLocker/monitoring/test_telemetry_system.py` (network/integration) that sends a span + metric to PostHog OTLP when
  `POSTHOG_API_KEY` is set.
- Dependencies: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` added to `pyproject.toml`.
- Suggested runtime config: export `POSTHOG_API_KEY='phc_emB3QtpPpfAURUCtjiTJ1N9e3MY0S7mR4ooDBP6wX8L'` and optional sampling/env overrides; OTLP targets
  `https://eu.i.posthog.com/ingest/otlp/v1/{traces|metrics}`.

## 4. Testing

- Not run in CI here (new dependencies may need installation); unit suite added to cover config/build paths.

# References

- `.kiro/specs/monitoring-reporting`
- `.kiro/specs/integration-architecture`
