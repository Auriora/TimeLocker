---
title: "Update: MinIO Endpoint Refresh"
id: "update-20251101-minio-host-refresh"
type: [ update ]
status: [ draft ]
owner: "AI Agent"
last_reviewed: "01-11-2025"
tags: [ update, minio, integration ]
links:
    tooling: [ pytest ]
---

# Update: MinIO Endpoint Refresh

- **Owner**: AI Agent
- **Created Date**: 01-11-2025
- **Audience**: Developers
- **Related**: Internal test infrastructure upkeep
- **Scope**: root

## 1. Purpose

Ensure all test fixtures, sample configuration, and developer documentation reference the current MinIO endpoint `minio.lan`. Align CLI integration tests and
samples with the supported non-interactive credential flow while keeping restic tooling current.

## 2. Summary

- Updated `.env.test`, `.env.test.example`, and `test-config.example.json` to default to `https://minio.lan` with explicit TLS settings.
- Replaced lingering `minio.local` references across docs and helper comments to avoid stale setup instructions.
- Confirmed Typer-based credentials flows operate non-interactively after recent prompt patches.
- Verified Dockerfile now pins restic `0.18.1` fetched from upstream release archives.
- Added `MINIO_VERIFY_SSL` toggle and `RESTIC_INSECURE_TLS` default for local testing so boto3/restic can connect to self-signed endpoints without manual
  tweaks.
- Patched `CommandBuilder` cloning and restic restore synopsis handling to prevent command-chain leakage (e.g., `init check`) and support positional snapshot
  IDs.
- Restic-dependent tests now auto-skip when the system binary is missing or below the supported minimum and repository initialization fails fast in those
  scenarios.

## 3. Implementation Notes

- Key paths: `.env.test`, `.env.test.example`, `test-config.example.json`, `src/TimeLocker/utils/repository_resolver.py`,
  `src/TimeLocker/restic/Repositories/s3.py`, `src/TimeLocker/command_builder/core.py`, `src/TimeLocker/restic/restic_repository.py`, `docs/`.
- Tests:
  `pytest tests/TimeLocker/cli/test_repos_credentials_commands.py tests/TimeLocker/integration/test_repos_credentials_command_usage.py tests/TimeLocker/integration/test_timeshift_cli_integration.py tests/TimeLocker/config/test_configuration_module.py::TestConfigurationModule::test_default_configuration tests/TimeLocker/restic/Repositories/test_s3.py -q`
- Follow-up: Run MinIO-backed integration suites once environment access is available to confirm connectivity checks succeed against `minio.lan`.
- Additional: Restored clean environment baselines in local restic repository tests to avoid cross-test leakage from `.env.test` defaults.

## 4. Documentation & Links

- Refreshed MinIO setup guides and testing checklists under `docs/`.

# References

- Existing MinIO maintenance notes within `../4-testing/checklist-minio-testing.md`
