---
title: "Plan: Resolve Current CLI/Test Failures"
date: "2025-11-14"
type: [ plan ]
status: [ in-progress ]
---

# Plan: Resolve Current CLI/Test Failures

This document captures the major clusters of remaining test failures so agents can tackle them one at a time. Each section references the failing suites and
highlights the expected fixes.

## 1. Credential Store Initialization

- **Tests:** `tests/TimeLocker/integration/test_repos_credentials_command_usage.py` and the other credential suites.
- **Issue:** The CLI repo setup never creates `~/.timelocker/credentials/credentials.enc` under the test HOME. Ensure the credential manager is instantiated and
  `initialize_store()` runs (even when service manager mocks are used), or adjust the fixture to call it explicitly.

## 2. Snapshot Namespace Cleanup (COMPLETE)

- **Tests:** `tests/TimeLocker/cli/test_cli_error_handling.py`, `test_cli_help_system.py`, `test_cli_integration.py`, `test_snapshot_id_cli_validation.py`, etc.
- **Issue:** These still reference `snapshots restore/contents/mount/umount/find-in`. Update them to use the `restore` namespace equivalents and adjust
  assertions to reflect the new command surface.

``## 3. CLI Service Mocking

- **Tests:** Most CLI suites (`test_cli_integration.py`, `test_repos_commands*.py`, `test_monitoring_commands.py`, etc.).
- **Issue:** Shared mocks still expose legacy attributes (e.g., `add_backup_target`, dict-like repository service). Refactor the fixtures in
  `tests/TimeLocker/cli/test_utils.py` to provide realistic services compatible with ServiceFacade/RepositoryResolver and update tests to rely on existing
  commands only.``

## 4. Backup Snapshot Mock

- **Tests:** `tests/TimeLocker/backup/test_snapshot.py`.
- **Issue:** `MockBackupRepository` no longer satisfies the `BackupRepository` ABC. Add implementations for the new abstract methods (`from_uri`, `name`, `uri`,
  `to_env`, etc.) so the snapshot unit tests can instantiate it again.

## 5. Timeshift CLI Exit Codes

- **Tests:** `tests/TimeLocker/integration/test_timeshift_cli_integration.py`.
- **Issue:** The simplified command now raises Click usage errors (exit code 2) for missing/invalid configs. Either catch those exceptions to return exit code
  1 (restoring old behavior) or update the tests to expect exit code 2 consistently.

## 6. Configuration & Locking Tests

- **Tests:** `tests/TimeLocker/config/test_configuration_integration_workflows.py`, `test_configuration_lock_manager.py`, etc.
- **Issues:**
    - Tests patch `_get_migration_rules` and set `config_module.config_file`, but those hooks no longer exist. Introduce public injection points or adapt the
      tests to the new API.
    - Locking tests expect only one successful acquisition; ensure `ConfigurationLockManager` enforces exclusivity (or update expectations if the design
      intentionally changed).
    - `ConfigurationManager.save_config` now takes no arguments; update repository manager/tests to call the new signature.

## 7. Monitoring CLI Fixtures

- **Tests:** `tests/TimeLocker/cli/test_monitoring_commands.py`.
- **Issue:** The CLI now expects dict-like monitoring payloads with `.get()`, but mocks return strings. Update the fixtures to return a structure similar to
  `MonitoringSummary`.

## 8. Performance Threshold & Path Resolver

- **Tests:** `tests/TimeLocker/cli/test_performance_compatibility.py`.
- **Issues:**
    - `repos --help` exceeds the 150 ms budget. Either optimize the command startup path or adjust the threshold in the test.
    - The config directory test expects `.config/.local`, but CI runs inside `/.jbdevcontainer/config`. Update the test to accept this path or set XDG env vars
      via the fixture.

## 9. Repository Manager & Credential Flow

- **Tests:** `test_repos_commands*.py`, `test_repository_manager_*`, integration suites relying on `RepositoryManager`.
- **Issues:** Tests expect methods like `ConfigurationManager.save_config(config)` and mutable repo configs. Adjust the manager to the new API (or patch the
  tests) and ensure `_repositories` is hydrated when reloading so persistence tests pass.

## 10. Selection & Optimization Services

- **Tests:** `tests/TimeLocker/selection/test_performance_stress.py`, `tests/TimeLocker/services/test_performance_optimization_service.py`.
- **Issues:** SelectionManager no longer marks all results as matched; investigate pattern evaluation caching/performance to restore the previous behavior.
  Additionally, convert `metrics.duration_seconds` to seconds before comparing to integers to fix the optimization service TypeError.

## 11. Restic Local Repository

- **Tests:** `tests/TimeLocker/restic/test_local_repository_enhanced.py`.
- **Issue:** `LocalResticRepository.initialize_repository()` now raises when directory creation fails; tests expect a `False` return. Decide whether to restore
  the previous behavior (catch exception, return False) or update the tests to allow exceptions.

## 12. Credential Storage & Multi-backend Repo Tests

- **Tests:** `tests/TimeLocker/integration/test_repos_credentials_integration.py`, `test_repository_multi_backend_integration.py`.
- **Issue:** `store_credentials` mocks never fire and repo loading complains `'Mock' object is not iterable`. Once the CLI/service mocks are updated (see
  cluster 3/9) and credential store creation is fixed (cluster 1), verify these integration tests receive the expected calls and adjust the fixtures
  accordingly.
