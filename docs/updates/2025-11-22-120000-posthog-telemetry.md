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

- Introduced `monitoring.telemetry` module that configures OTLP/HTTP exporters for PostHog (EU region) with sampler control and fail-open behaviour, plus a
  PostHog client backend.
- Wired CLI entrypoint to initialise telemetry on startup and record uncaught exceptions as spans/logs without affecting exit codes.
- Exposed env configuration: `POSTHOG_API_KEY`, `POSTHOG_OTLP_ENDPOINT` (default `https://eu.i.posthog.com`), `POSTHOG_OTLP_LOGS_ENDPOINT` (derived from the
  base), `POSTHOG_HOST` (for client backend, default EU), `TIMELOCKER_TELEMETRY_ENABLED`, `TIMELOCKER_TELEMETRY_BACKEND`, and
  `TIMELOCKER_TELEMETRY_SAMPLE_RATIO`.

## 3. Implementation Notes

- New module: `src/TimeLocker/monitoring/telemetry.py` (resource setup, exporter factories, exception recorder).
- CLI startup now calls `setup_telemetry_from_env()`; exceptions flow through `record_exception` before re-raising.
- Added unit coverage in `tests/TimeLocker/monitoring/test_telemetry.py` (including backend selection) using dummy exporters to avoid network calls.
- Added opt-in system test `tests/TimeLocker/monitoring/test_telemetry_system.py` (network/integration) that sends a synthetic exception via the active backend
  when `POSTHOG_API_KEY` is set.
- Dependencies: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `posthog` added to `pyproject.toml`.
- Suggested runtime config: export `POSTHOG_API_KEY='phc_emB3QtpPpfAURUCtjiTJ1N9e3MY0S7mR4ooDBP6wX8L'`; OTLP defaults to
  `https://eu.i.posthog.com/otlp/v1/{traces|metrics}` and logs to `https://eu.i.posthog.com/i/v1/logs` unless overridden; set
  `TIMELOCKER_TELEMETRY_BACKEND=posthog` to use the client backend.

## 4. Testing

- Not run in CI here (new dependencies may need installation); unit suite added to cover config/build paths.

# References

- `.kiro/specs/monitoring-reporting`
- `.kiro/specs/integration-architecture`
