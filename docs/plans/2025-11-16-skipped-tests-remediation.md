---
title: "RFC: Skipped Test Remediation Roadmap"
id: "rfc-2025-11-skipped-tests"
type: [ plan ]
status: [ draft ]
owner: "Codex Agent"
last_reviewed: "16-11-2025"
tags: [plan, tests, cli, monitoring]
links:
  tooling: [pytest]
---

# RFC: Skipped Test Remediation Roadmap

- **Owner**: Codex Agent
- **Status**: Draft
- **Last Updated**: 16-11-2025
- **Created Date**: 16-11-2025
- **Audience**: CLI maintainers, QA, Monitoring & Repository sub-teams

## 1. Purpose

Eliminate or justify the ~20 skipped tests scattered across CLI, monitoring, and service suites by either (a) implementing the missing behavior promised in `.kiro/specs/` or (b) retiring the obsolete coverage. Success criteria:

- No unconditional skips caused by unmet roadmap features; remaining skips must be environment-conditional (e.g., restic binary absent) and documented.
- CLI integration/regression suites reflect the current Typer command graph defined in `cli-interface` specs and security/configuration requirements.
- Monitoring, repository, and service tests validate platform-agnostic behavior via mocks or adapters, aligning with `monitoring-reporting` and `repository-management` specs.
- Plan execution tracked through follow-up issues/tasks with measurable deliverables.

## 2. Problem Statement

The following groups of tests are permanently skipped, masking regressions:

| Area | Files / Tests | Skip Reason | Spec Tie-In |
| --- | --- | --- | --- |
| CLI Registry | `tests/TimeLocker/cli_modules/test_registry_integration.py` (8 tests) | "Requires fixing logger in cli.py" | `.kiro/specs/cli-interface`, `.kiro/specs/repository-management` (command availability) |
| CLI Config & Credentials | `tests/TimeLocker/cli/test_config_commands.py`, `tests/TimeLocker/cli/test_cli_help_system.py`, `tests/TimeLocker/cli/test_cli_integration.py` | Claims commands missing | `.kiro/specs/configuration-management`, `.kiro/specs/security-services` |
| CLI Workflows (Targets) | `tests/TimeLocker/cli/test_cli_integration.py::test_first_time_user_workflow` | Targets deprecated | `.kiro/specs/data-selection` (selections replace targets) |
| CLI Error Handling | `tests/TimeLocker/cli/test_cli_error_handling.py::test_keyboard_interrupt_handling` | Mocking strategy obsolete | `.kiro/specs/cli-interface` (interactive robustness) |
| S3 Service Manager | `tests/TimeLocker/services/test_s3_service_manager.py` (custom service cases) | Custom type "not yet implemented" | `.kiro/specs/repository-management` Req 7 |
| Monitoring Notifications | `tests/TimeLocker/monitoring/test_monitoring_integration.py::TestCrossPlatformIntegration` | Platform-specific placeholder | `.kiro/specs/monitoring-reporting` Req 2 |
| Environment Constraints | `tests/TimeLocker/restic/conftest.py`, regression Unicode/special paths, MinIO integration, backup path edge cases | Depend on external binaries or FS capabilities | `.kiro/specs/recovery-operations`, `.kiro/specs/integration-architecture` |

Without a remediation plan, we cannot trust CLI coverage during refactors, and spec compliance drifts unnoticed.

## 3. Proposed Solution

### 3.1 CLI Registry Logging Coupling
- **Issue**: Registry tests import `TimeLocker.cli`, which configures Rich logging and side-effectful handlers before tests can isolate loggers.
- **Plan**:
  1. Extract logging bootstrap (`setup_logging` + Rich handler wiring) into a lazily-called helper so registry functions can be imported without immediate logging configuration (aligns with `.kiro/specs/cli-interface/design.md` requirement for command discovery).
  2. Provide pytest fixture to reset global registry and temporarily silence logging (using `logging.NullHandler`).
  3. Remove `@pytest.mark.skip` and assert metadata/statistics.
- **Dependencies**: None beyond CLI module refactor; ensure docs reference `docs/updates/2025-11-12-command-registry-implementation.md` remain accurate.

### 3.2 CLI Config & Credentials Coverage
- **Issue**: Skips claim commands are unimplemented even though Typer apps exist following Phase 3 refactor.
- **Plan**:
  1. Refresh tests to import command apps from `src.TimeLocker.cli_modules.commands` instead of legacy `cli` functions and assert help text/behavior per `.kiro/specs/configuration-management/requirements.md` (Req 1–3) and `.kiro/specs/security-services/requirements.md` (Req 2).
  2. Update integration tests to use new command group names and mocks (e.g., `credentials store/remove`, `config show/setup`).
  3. Delete obsolete skip decorators once behavior verified.
- **Dependencies**: Ensure CLI runner fixtures in `tests/TimeLocker/cli/test_utils.py` handle new Typer apps.

### 3.3 First-Time Workflow (Targets → Selections)
- **Issue**: Test references deprecated `targets` commands.
- **Plan**:
  1. Replace workflow with `selections` commands defined in `.kiro/specs/data-selection/design.md` (create/list/test/export) and align repository default-setting steps.
  2. Verify service-manager mocks cover selection creation flows (aligning with `docs/TimeLocker/cli_modules/commands/selections.py`).
  3. Remove skip once scenario reflects current onboarding path.
- **Dependencies**: Selection manager fixtures (see `tests/TimeLocker/cli/test_cli_integration.py` patch_restore_commands) need expansion.

### 3.4 KeyboardInterrupt Handling Test
- **Issue**: Backup command architecture changed; existing mocks hook deep orchestrator.
- **Plan**:
  1. Introduce injectable hook (e.g., context manager around `_call_service_method`) to raise `KeyboardInterrupt` deterministically.
  2. Update test to use `monkeypatch` on `_call_service_method` or `BackupCLIHandler.execute_backup_with_selection` and assert exit code 130 (per `.kiro/specs/cli-interface` error semantics).
  3. Remove skip.
- **Dependencies**: None; ensure new helper reused by other signal tests.

### 3.5 S3 Custom Service Coverage
- **Issue**: Tests prematurely skip when catching `ValueError` for custom service type.
- **Plan**:
  1. Audit `S3_SERVICE_TEMPLATES` to ensure `S3ServiceType.CUSTOM` entry exists with `supports_custom_endpoint=True` per `.kiro/specs/repository-management/requirements.md` Req 7.
  2. If incomplete, implement template + validator handling (including TLS warnings) and add explicit assertions in tests rather than skipping.
  3. Cover error path by parametrizing test with intentionally invalid endpoint to confirm user-facing warning.
- **Dependencies**: None; may require doc update in `docs/1-requirements/repository-management` if behavior changes.

### 3.6 Monitoring Notification Tests
- **Issue**: Platform-specific tests permanently skipped.
- **Plan**:
  1. Abstract desktop notification dispatch behind interface (e.g., `NotificationAdapter`) with platform tag enumerations.
  2. Write unit tests that inject fake adapters and assert the monitoring service triggers them (align `.kiro/specs/monitoring-reporting/requirements.md` Req 2 & 8).
  3. Replace unconditional `skipif(True, ...)` with `skipif(not adapter.is_supported(platform))` to keep optional real-platform smoke tests.
- **Dependencies**: Monitoring service maintainers; ensure CLI monitoring commands re-use same adapter for parity.

### 3.7 Environment-Constrained Suites
- **Restic (`tests/TimeLocker/restic/conftest.py`)**: Keep skip-if-binary-missing guard but document requirement in README/testing docs; add CI job to install restic where feasible.
- **Regression Unicode/Special Paths**: Leave conditional `pytest.skip` triggered only when filesystem rejects path; no action beyond ensuring logging when skip occurs for awareness.
- **MinIO Integration**: Provide deterministic credential manager fixture unlocking with fallback test master password to avoid spurious skip; if still unavailable, surface skip reason with actionable instructions.
- **Backup Critical Paths**: These skip only on filesystems lacking symlink/long filename support; keep guard but capture metrics to know when tests run.

### 3.8 Tracking & Communication
- File follow-up tickets per category above and link them in `docs/updates` as progress is made.
- Add CI dashboard metric counting `skipped` tests; fail build if unapproved skip reasons appear (optional stretch).

## 4. Alternatives

1. **Do nothing**: Maintains blind spots; unacceptable due to spec compliance mandates.
2. **Delete affected tests**: Would reduce coverage and violate `.kiro/specs/testing` intent unless functionality officially deprecated; only acceptable for target-based workflow once selections replacement is verified (outlined above).
3. **Move tests to integration-only pipelines**: Would still require enabling features elsewhere; does not solve spec drift.

## 5. Impact

- **Touched areas**: `src/TimeLocker/cli.py`, `cli_modules`, S3 service manager, monitoring adapters, CLI tests, docs.
- **Risks**: Refactoring logging/CLI bootstrap could affect runtime logging; mitigated via regression tests and staged roll-out.
- **Rollout**: Implement per module; after each cluster fix, run corresponding pytest subset and update docs. Target completion in three iterations (Registry/CLI commands, Services/Monitoring, Environment harnesses).

## 6. Decision Log

| Date | Decision | Notes |
| --- | --- | --- |
| 16-11-2025 | Draft remediation plan created and approved by user | Aligns with AI agent planning protocol |

## 7. Progress Update (2025-11-16)

- **CLI coverage restored**: Registry, config/help, credential workflows, first-time onboarding, and KeyboardInterrupt handling now run without skips. Tests `tests/TimeLocker/cli_modules/test_registry_integration.py`, `tests/TimeLocker/cli/test_config_commands.py`, `tests/TimeLocker/cli/test_cli_help_system.py`, `tests/TimeLocker/cli/test_cli_integration.py`, and `tests/TimeLocker/cli/test_cli_error_handling.py` all pass.
- **S3 custom services implemented**: `S3ServiceType.CUSTOM` template/validation added and the corresponding unit coverage in `tests/TimeLocker/services/test_s3_service_manager.py` no longer skips.
- **Monitoring notifications mocked**: `NotificationService` gained injectable desktop adapters; cross-platform notification tests now use fake adapters (`tests/TimeLocker/monitoring/test_monitoring_integration.py`) so the prior `skipif(True, ...)` decorators were removed.
- **External dependency mocks**: Restic suite uses monkeypatched version detection/executable checks, and MinIO integration tests rely on mocked settings/clients, eliminating unconditional skips due to missing binaries or services.

Remaining actions focus on regression suites (filesystem constraints) and any newly discovered skips that surface as we expand coverage.

# References

- `.kiro/specs/cli-interface/requirements.md`
- `.kiro/specs/configuration-management/requirements.md`
- `.kiro/specs/security-services/requirements.md`
- `.kiro/specs/data-selection/requirements.md`
- `.kiro/specs/repository-management/requirements.md`
- `.kiro/specs/monitoring-reporting/requirements.md`
- `docs/guides/ai-agent/AGENT-GUIDE-Planning-Protocol.md`
