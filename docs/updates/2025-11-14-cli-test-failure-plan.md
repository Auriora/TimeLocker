---
title: "Plan: Resolve Current CLI/Test Failures"
date: "2025-11-14"
type: [ plan ]
status: [ in-progress ]
---

# Plan: Resolve Current CLI/Test Failures

This document captures the major clusters of remaining test failures so agents can tackle them one at a time. Each section references the failing suites and
highlights the expected fixes.

> **Latest test run (2025-11-15)**: `pytest` reported **50 failed, 16 errors**. The failures listed below map each stack trace to an existing cluster or call
> out new work when necessary.

• Failure Priorities

- Blocking Infrastructure – Fix the mock/service scaffolding first so future CI runs give actionable feedback.
    - MockBackupRepository implementation gaps (cluster 4) prevent 14 snapshot unit tests from even instantiating; once the abstract methods are stubbed, the
      suite can prove snapshot logic still works.
    - MockRepositoryService / CLI fixtures (cluster 3 + cluster 9) currently let commands fall through to real Restic binaries, causing almost every repos CLI
      and multi-backend test to fail with “repository does not exist.” Stabilize these mocks before touching higher-level flows so we stop debugging external
      errors.
    - Repository resolver integration fixtures (cluster 13) throw FileExistsError before command logic runs, hiding real regressions. Isolate temp directories
      per test to unblock the entire CLI modules suite.
- Core Functional Coverage – Once the scaffolding is solid, restore internal behaviors that impact multiple subsystems.
    - Credential store initialization and multi-backend credential flows (cluster 1 + cluster 12) block nine integration tests and anything that depends on
      encrypted storage; these should pass before touching optional features.
    - Configuration/locking workflows (cluster 6) influence both CLI state transitions and service orchestration; without deterministic locking and config
      injection, other fixes can’t be validated.
- User-Facing Regressions – After foundational issues, focus on high-visibility behavior.
    - Timeshift CLI exit codes (cluster 5) and Restic repository initialization semantics (cluster 11) affect real users and produce clear expectations in docs;
      resolve them early to keep released workflows accurate.
    - Performance/selection services (cluster 8 + cluster 10) guard SLA-style contracts (help latency, selection accuracy, performance reports). They’re less
      urgent than getting CLI commands to run, but still important once stateful infrastructure is restored.
- Remaining Integration Polish – Finally address package-specific suites once the big rocks are done.
    - Repository manager lifecycle/state transition tests, credential rotation, and plugin registry scenarios (part of cluster 9) will naturally fall into place
      after the manager/mocks are fixed.
    - Monitoring CLI fixtures (cluster 7) currently have no failing tests but should still be updated before new regressions appear.

Suggested order of operations

1. Rebuild MockBackupRepository; patch CLI/service mocks so commands stay inside fakes; isolate repo-resolver temp dirs.
2. Fix credential store creation and repository manager persistence so CLI/integration suites can create realistic repos/credentials.
3. Restore configuration injection + lock semantics.
4. Address Timeshift exit codes and Restic error handling.
5. Tackle performance/selection metric regressions.
6. Clean up remaining integrations (plugin registry, monitoring fixtures, etc.).

Each step should be followed by a targeted pytest run to confirm that cluster’s checklist drops to zero before moving on.

## 1. Credential Store Initialization *(COMPLETED 2025-11-15)*

- **Tests:** `tests/TimeLocker/integration/test_repos_credentials_command_usage.py` and the other credential suites.
- **Issue:** Credential manager now honors `~/.timelocker/credentials` (or `TIMELOCKER_CREDENTIAL_DIR`), so the CLI fixtures create encrypted stores inside each isolated HOME. Verified by `pytest tests/TimeLocker/integration/test_repos_credentials_command_usage.py`.
- **Failing tests (2025-11-15):** _None_

## 2. Snapshot Namespace Cleanup (COMPLETE)

- **Tests:** `tests/TimeLocker/cli/test_cli_error_handling.py`, `test_cli_help_system.py`, `test_cli_integration.py`, `test_snapshot_id_cli_validation.py`, etc.
- **Issue:** These still reference `snapshots restore/contents/mount/umount/find-in`. Update them to use the `restore` namespace equivalents and adjust
  assertions to reflect the new command surface.

## 3. CLI Service Mocking *(COMPLETED 2025-11-15)*

- **Tests:** Most CLI suites (`test_cli_integration.py`, `test_repos_commands*.py`, `test_monitoring_commands.py`, etc.).
- **Issue:** Shared mocks still expose legacy attributes (e.g., `add_backup_target`, dict-like repository service). Refactor the fixtures in
  `tests/TimeLocker/cli/test_utils.py` to provide realistic services compatible with ServiceFacade/RepositoryResolver and update tests to rely on existing
  commands only. The latest run highlights additional gaps:
    - `tests/TimeLocker/cli/test_mock_verification.py` now fails because `MockRepositoryService` lacks `get_repository` and `list_repositories`.
    - `test_repos_commands*` exit with real Restic errors (“repository does not exist”) because mocks fall through to production code. Strengthen the fake
      service facade so CLI commands never invoke the external binary in tests.
- **Status:** `tests/TimeLocker/cli/test_mock_verification.py` now passes after the shared mock factory rewrite.
- **Failing tests (2025-11-15):** _None_

## 4. Backup Snapshot Mock *(COMPLETED 2025-11-15)*

- **Tests:** `tests/TimeLocker/backup/test_snapshot.py`.
- **Issue:** `MockBackupRepository` no longer satisfies the `BackupRepository` ABC. Add implementations for the new abstract methods (`from_uri`, `name`, `uri`,
  `to_env`, etc.) so the snapshot unit tests can instantiate it again. The most recent run shows all snapshot tests erroring with “Can't instantiate abstract
  class MockBackupRepository…”, blocking the suite until the mock is rebuilt.
- **Status:** The mock now satisfies the ABC surface; `pytest tests/TimeLocker/backup/test_snapshot.py` passes end-to-end.
- **Failing tests (2025-11-15):** _None_

## 5. Timeshift CLI Exit Codes

- **Tests:** `tests/TimeLocker/integration/test_timeshift_cli_integration.py`.
- **Issue:** The simplified command now raises Click usage errors (exit code 2) for missing/invalid configs. Either catch those exceptions to return exit code
  1 (restoring old behavior) or update the tests to expect exit code 2 consistently. Failures (`test_timeshift_import_missing_config`,
  `test_timeshift_import_invalid_json`) continue to assert exit code `1` but receive `2`.
- **Failing tests (2025-11-15):**
    - `tests/TimeLocker/integration/test_timeshift_cli_integration.py::TestTimeshiftCLIIntegration::test_timeshift_import_missing_config`
    - `tests/TimeLocker/integration/test_timeshift_cli_integration.py::TestTimeshiftCLIIntegration::test_timeshift_import_invalid_json`

## 6. Configuration & Locking Tests

- **Tests:** `tests/TimeLocker/config/test_configuration_integration_workflows.py`, `test_configuration_lock_manager.py`, etc.
- **Issues:**
    - Tests patch `_get_migration_rules` and set `config_module.config_file`, but those hooks no longer exist. Introduce public injection points or adapt the
      tests to the new API.
    - Locking tests expect only one successful acquisition; ensure `ConfigurationLockManager` enforces exclusivity (or update expectations if the design
      intentionally changed).
    - `ConfigurationManager.save_config` now takes no arguments; update repository manager/tests to call the new signature.
- **Failing tests (2025-11-15):**
    - `tests/TimeLocker/config/test_configuration_integration_workflows.py::TestConfigurationIntegrationWorkflows::test_configuration_migration_workflow`
    - `tests/TimeLocker/config/test_configuration_integration_workflows.py::TestConfigurationIntegrationWorkflows::test_concurrent_access_workflow`
    - `tests/TimeLocker/config/test_configuration_integration_workflows.py::TestConfigurationIntegrationWorkflows::test_atomic_update_workflow`
    - `tests/TimeLocker/config/test_configuration_lock_manager.py::TestConfigurationLockManager::test_concurrent_lock_acquisition`
    - `tests/TimeLocker/integration/test_integration_service.py::TestIntegrationService::test_configuration_integration`

## 7. Monitoring CLI Fixtures

- **Tests:** `tests/TimeLocker/cli/test_monitoring_commands.py`.
- **Issue:** The CLI now expects dict-like monitoring payloads with `.get()`, but mocks return strings. Update the fixtures to return a structure similar to
  `MonitoringSummary`.
- **Failing tests (2025-11-15):** _None reported in the latest run (cluster blocked by other failures but kept here for completeness)._

## 8. Performance Threshold & Path Resolver

- **Tests:** `tests/TimeLocker/cli/test_performance_compatibility.py`.
- **Issues:**
    - `repos --help` exceeds the 150 ms budget. Either optimize the command startup path or adjust the threshold in the test.
    - The config directory test expects `.config/.local`, but with the new isolation fixture the detected directory is `/tmp/.../config/timelocker`. Update
      the test (or fixture) to accept the temporary XDG path.
- **Failing tests (2025-11-15):**
    - `tests/TimeLocker/cli/test_performance_compatibility.py::TestCrossPlatformBehavior::test_config_directory_platform_appropriate`

## 9. Repository Manager & Credential Flow *(PARTIAL – CLI repos commands still failing)*

- **Tests:** `test_repos_commands*.py`, `test_repository_manager_*`, `tests/TimeLocker/integration/test_repository_multi_backend_integration.py`, etc.
- **Issues:** Repository manager now loads/saves safely, `ConfigurationManager.save_config` accepts optional payloads, and credential hooks fire — the multi-backend and credential integration suites are green. Remaining work is isolated to the CLI repos command batteries, which still rely on the older service/mocking patterns.
- **Remaining failing tests (2025-11-15):**
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_add_with_set_default`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_remove_command`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_check_command`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_stats_command`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_unlock_command`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_migrate_command`
    - `tests/TimeLocker/cli/test_repos_commands.py::TestReposCommands::test_repos_forget_command`

## 10. Selection & Optimization Services

- **Tests:** `tests/TimeLocker/selection/test_performance_stress.py`, `tests/TimeLocker/services/test_performance_optimization_service.py`.
- **Issues:** SelectionManager no longer marks all results as matched; investigate pattern evaluation caching/performance to restore the previous behavior.
  Additionally, convert `metrics.duration_seconds` to seconds before comparing to integers to fix the optimization service TypeError.
- **Failing tests (2025-11-15):**
    - `tests/TimeLocker/selection/test_performance_stress.py::TestPatternMatchingPerformance::test_literal_pattern_performance`
    - `tests/TimeLocker/selection/test_performance_stress.py::TestPatternMatchingPerformance::test_mixed_pattern_performance`
    - `tests/TimeLocker/services/test_performance_optimization_service.py::TestPerformanceOptimizationService::test_generate_performance_report`

## 11. Restic Local Repository

- **Tests:** `tests/TimeLocker/restic/test_local_repository_enhanced.py`.
- **Issue:** `LocalResticRepository.initialize_repository()` now raises when directory creation fails; tests expect a `False` return. Decide whether to restore
  the previous behavior (catch exception, return False) or update the tests to allow exceptions. Latest failures still surface the raised exceptions, so the
  contract decision remains unresolved.
- **Failing tests (2025-11-15):**
    - `tests/TimeLocker/restic/test_local_repository_enhanced.py::TestLocalResticRepositoryEnhanced::test_initialize_repository_directory_creation_fails`
    - `tests/TimeLocker/restic/test_local_repository_enhanced.py::TestLocalResticRepositoryEnhanced::test_initialize_repository_exception_handling`

## 12. Credential Storage & Multi-backend Repo Tests *(COMPLETED 2025-11-15)*

- **Tests:** `tests/TimeLocker/integration/test_repos_credentials_integration.py`, `test_repository_multi_backend_integration.py`.
- **Status:** With the credential manager path fixes and repository manager hooks, all credential + multi-backend integration cases currently pass.
- **Failing tests (2025-11-15):** _None_

## 13. Repository Resolver Integration Fixtures *(COMPLETED 2025-11-15)*

- **Tests:** `tests/TimeLocker/cli_modules/commands/test_repository_resolver_integration.py`.
- **Status:** Fixture now allocates unique config dirs per test via `tmp_path_factory`, eliminating the `FileExistsError` collisions.
- **Failing tests (2025-11-15):** _None_
