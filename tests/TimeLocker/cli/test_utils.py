"""
Shared utilities for CLI testing.

This module provides common utilities and helper functions used across
all CLI test files to reduce code duplication and ensure consistency.

Note: This module now re-exports utilities from the centralized
TimeLocker.cli_modules.testing package for backward compatibility.
New tests should import directly from TimeLocker.cli_modules.testing.
"""

import os
from contextlib import ExitStack, contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from typer.testing import CliRunner
from unittest.mock import Mock, MagicMock, patch
from typing import Any, Dict, Optional
from TimeLocker.cli_services import CLIServiceManager
from TimeLocker.services.snapshot_service import SnapshotService
from TimeLocker.services.repository_service import RepositoryService

# Import from centralized testing utilities
from TimeLocker.cli_modules.testing import (
    create_mock_service_manager as _create_mock_service_manager,
    create_test_snapshot,
    create_test_repository,
    create_test_target,
    assert_cli_success as _assert_cli_success,
    assert_cli_error as _assert_cli_error,
    assert_cli_output_contains as _assert_cli_output_contains,
    assert_cli_help_quality as _assert_cli_help_quality,
)


def get_cli_runner(columns: int = 200) -> CliRunner:
    """
    Create a standardized CLI runner for testing.

    The 200 column default prevents help text truncation in CI environments
    where terminal width detection may not work correctly. This ensures
    consistent output formatting across different testing environments.

    Args:
        columns: Terminal width for consistent output formatting (default: 200)

    Returns:
        Configured CliRunner instance
    """
    return CliRunner(env={'COLUMNS': str(columns)})


# Export a shared runner instance for legacy tests expecting a module-level 'runner'
runner = get_cli_runner()

_SHOW_CLI_OUTPUT_ENV = "TIMELOCKER_SHOW_CLI_OUTPUT"


def combined_output(result) -> str:
    """
    Combine stdout and stderr for matching convenience across environments.

    This is necessary because some CLI runners capture stderr differently
    across environments (local vs CI, different OS). Combining both streams
    ensures test assertions work consistently regardless of where output
    appears. Useful when you need to check for text that might appear in
    either stdout or stderr.

    Args:
        result: CliRunner result object

    Returns:
        Combined output string
    """
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


# Backward compatibility alias used by some test modules
_combined_output = combined_output


def maybe_show_cli_output(result, label: Optional[str] = None) -> None:
    """
    Print captured CLI output when TIMELOCKER_SHOW_CLI_OUTPUT is truthy.

    Args:
        result: CliRunner result object
        label: Optional label to prefix the output block
    """
    if not os.environ.get(_SHOW_CLI_OUTPUT_ENV):
        return
    header = label or "CLI Output"
    separator = "-" * 60
    print(f"\n[{header}] {separator}\n{combined_output(result)}\n{separator}\n")


def create_mock_service_manager() -> Mock:
    """
    Create a standardized mock service manager for CLI testing.

    Uses spec_set to ensure mocks match the actual CLIServiceManager interface,
    catching typos and ensuring mocks match real implementations.

    Returns:
        Mock service manager with common methods configured with realistic return values
    """
    class _RepositoryDict(dict):
        def keys(self):
            # Monitoring commands expect .keys() to yield repository dicts
            return list(super().values())

    repo_store: _RepositoryDict = _RepositoryDict()
    default_repo_template = {
            "name": "test-repo",
            "uri": "file:///tmp/test-repo",
            "description": "Default test repository",
            "metadata": {},
            "engine": "restic",
            "status": "active"
    }
    default_state = {"default_repository": None}
    credential_store: Dict[str, Dict[str, Any]] = {}

    def _normalize_name(*candidates: Optional[str]) -> str:
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return default_state["default_repository"] or default_repo_template["name"]

    def _ensure_repo(name: Optional[str]) -> Dict[str, Any]:
        repo_name = _normalize_name(name)
        repo = repo_store.get(repo_name)
        if not repo:
            repo = {
                    "name": repo_name,
                    "uri": f"file:///tmp/{repo_name}",
                    "description": "",
                    "metadata": {},
                    "engine": "restic",
                    "status": "active"
            }
            repo_store[repo_name] = repo
            default_state.setdefault("default_repository", repo_name)
        return repo

    def _mutate_metadata(repo: Dict[str, Any]) -> Dict[str, Any]:
        repo.setdefault("metadata", {})
        return repo["metadata"]

    mock_service_manager = MagicMock(spec=CLIServiceManager)
    repository_service = MagicMock()
    mock_service_manager.repository_service = repository_service
    mock_service_manager.snapshot_service = MagicMock()
    mock_service_manager.snapshot_service.get_snapshot.return_value = None
    mock_service_manager.snapshot_service.find_snapshots.return_value = []
    mock_service_manager.snapshot_service.delete_snapshot.return_value = {'success': True}
    mock_service_manager.list_snapshots = mock_service_manager.snapshot_service.list_snapshots
    mock_service_manager.get_snapshot = mock_service_manager.snapshot_service.get_snapshot
    mock_service_manager.find_snapshots = mock_service_manager.snapshot_service.find_snapshots

    backup_orchestrator = MagicMock()
    backup_orchestrator.execute_backup.return_value = Mock(
            success=True,
            snapshot_id="test123abc",
            warnings=[],
            errors=[],
            files_processed=42,
            bytes_transferred=2048,
            duration=1.0
    )
    mock_service_manager.backup_orchestrator = backup_orchestrator
    mock_service_manager._backup_orchestrator = backup_orchestrator
    mock_service_manager.execute_backup = MagicMock(
            return_value=backup_orchestrator.execute_backup.return_value
    )
    mock_service_manager.verify_backup_integrity = MagicMock(return_value=True)

    config_service = MagicMock()
    config_service.get_backup_targets.return_value = []
    config_service.add_backup_target.return_value = None
    config_service.get_repositories.side_effect = lambda: repo_store
    config_service.get_repository.side_effect = lambda name: _ensure_repo(name)
    config_service.get_repository_by_name.side_effect = lambda name: _ensure_repo(name)
    config_service.config_file = Path("/tmp/config.yaml")
    mock_service_manager._config_service = config_service
    mock_service_manager.configuration_service = config_service

    config_module = MagicMock()
    config_module.add_backup_target.return_value = None
    config_module.get_repository.side_effect = lambda name: _ensure_repo(name)
    config_module.list_repositories.side_effect = lambda: list(repo_store.values())
    mock_service_manager.config_module = config_module
    mock_service_manager._config_module = config_module

    mock_service_manager.resolve_repository_uri = MagicMock(side_effect=lambda uri, **_: uri)
    mock_service_manager._find_repository_name_by_uri = MagicMock(
            side_effect=lambda *_args, **_kwargs: default_state["default_repository"] or default_repo_template["name"]
    )
    mock_service_manager.detect_existing_repository = MagicMock(return_value=None)

    def _make_stats(name: str) -> Dict[str, Any]:
        base = len(name) or 1
        return {
                "name": name,
                "total_size": base * 1024,
                "snapshots_count": base,
                "total_files": base * 10,
                "total_blobs": base * 5,
                "compression_ratio": 1.1
        }

    def _add_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        uri = kwargs.get("repository_uri") or kwargs.get("repository") or repo["uri"]
        repo["uri"] = uri
        description = kwargs.get("description")
        if description is not None:
            repo["description"] = description
        metadata = kwargs.get("metadata")
        if metadata:
            repo.setdefault("metadata", {}).update(metadata)
        return {"success": True, "repository": repo}

    def _update_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        description = kwargs.get("description")
        if description is not None:
            repo["description"] = description
        metadata = kwargs.get("metadata")
        if metadata:
            repo.setdefault("metadata", {}).update(metadata)
        configuration = kwargs.get("configuration") or {}
        for key, value in configuration.items():
            if key == "metadata":
                _mutate_metadata(repo).update(value or {})
            else:
                repo[key] = value
        uri = kwargs.get("uri") or kwargs.get("repository_uri")
        if uri:
            repo["uri"] = uri
        engine = kwargs.get("engine")
        if engine:
            repo["engine"] = engine
        status = kwargs.get("status")
        if status:
            repo["status"] = status
        return {"success": True, "repository": repo}

    def _update_repository_metadata(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        metadata = kwargs.get("metadata") or {}
        remove = kwargs.get("remove_keys") or kwargs.get("remove_metadata") or []
        clear = kwargs.get("clear") or kwargs.get("clear_metadata")
        repo_metadata = _mutate_metadata(repo)
        if clear:
            repo_metadata.clear()
        for key in remove:
            repo_metadata.pop(key, None)
        if metadata:
            repo_metadata.update(metadata)
        return {"success": True, "repository": repo}

    def _update_repository_configuration(**kwargs):
        configuration = kwargs.get("configuration", {}).copy()
        for field in ("uri", "description", "engine", "type", "password"):
            if kwargs.get(field) is not None:
                configuration[field] = kwargs[field]
        if kwargs.get("metadata"):
            configuration.setdefault("metadata", {}).update(kwargs["metadata"])
        return _update_repository(
                name=kwargs.get("name") or kwargs.get("repository_name") or kwargs.get("repository"),
                configuration=configuration
        )

    def _list_repositories(filters=None, **_kwargs):
        repos = list(repo_store.values())
        if filters:
            status = filters.get("status")
            engine = filters.get("engine")
            if status:
                repos = [repo for repo in repos if repo.get("status") == status]
            if engine:
                repos = [repo for repo in repos if repo.get("engine") == engine]
        return repos

    def _remove_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo_store.pop(name, None)
        return {"success": True}

    def _simple_success(**_kwargs):
        return {"success": True}

    def _get_repository_by_name(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        return _ensure_repo(name)

    def _get_repository_stats(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        return _make_stats(name)

    def _apply_retention_policy(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        repo["retention_applied"] = True
        return {"success": True}

    def _validate_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        _ensure_repo(name)
        return {"status": "success", "errors": [], "warnings": []}

    def _batch_validate_repositories(**kwargs):
        repositories = kwargs.get("repositories") or list(repo_store.keys())
        return [{"name": repo, "status": "success"} for repo in repositories]

    def _set_default_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        default_state["default_repository"] = name
        return {"success": True}

    def _clear_default_repository(**_kwargs):
        default_state["default_repository"] = None
        return {"success": True}

    def _unlock_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        repo["locked"] = False
        return {"success": True}

    def _migrate_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        _ensure_repo(name)
        return {"success": True}

    def _forget_repository(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        repo["forgotten"] = True
        return {"success": True}

    def _set_repository_status(status: str, **kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        repo["status"] = status
        return {"success": True, "repository": repo}

    def _transition_repository_state(**kwargs):
        state = kwargs.get("state") or kwargs.get("target_state") or kwargs.get("status")
        if not state:
            state = "unknown"
        return _set_repository_status(state, **kwargs)

    def _rotate_credentials(**kwargs):
        name = _normalize_name(kwargs.get("name"), kwargs.get("repository_name"), kwargs.get("repository"))
        repo = _ensure_repo(name)
        password = kwargs.get("new_password") or kwargs.get("password")
        backend_credentials = kwargs.get("backend_credentials") or kwargs.get("credentials")
        backend_type = kwargs.get("backend_type") or kwargs.get("backend")
        record = credential_store.setdefault(name, {"password_history": [], "backend": {}})
        if password:
            record["password_history"].append(password)
            repo["last_password_rotation"] = password
        if backend_credentials:
            record["backend"] = {
                    "type": backend_type,
                    "credentials": backend_credentials
            }
            repo["backend_credentials"] = backend_credentials
        repo["last_credential_rotation"] = datetime.utcnow().isoformat()
        return {"success": True, "repository": repo, "credentials": record}

    def _rotate_repository_password(**kwargs):
        kwargs["new_password"] = kwargs.get("new_password") or kwargs.get("password")
        return _rotate_credentials(**kwargs)

    def _rotate_backend_credentials(**kwargs):
        kwargs["backend_credentials"] = kwargs.get("backend_credentials") or kwargs.get("credentials")
        return _rotate_credentials(**kwargs)

    # Wire handlers for both top-level manager and legacy repository_service alias
    def _wire(name: str, handler):
        shared_mock = MagicMock(wraps=handler)
        setattr(mock_service_manager, name, shared_mock)
        setattr(repository_service, name, shared_mock)

    _wire("add_repository", _add_repository)
    _wire("update_repository", _update_repository)
    _wire("update_repository_metadata", _update_repository_metadata)
    _wire("update_repository_configuration", _update_repository_configuration)
    _wire("list_repositories", _list_repositories)
    _wire("get_repository", _get_repository_by_name)
    _wire("get_repository_by_name", _get_repository_by_name)
    _wire("remove_repository", _remove_repository)
    _wire("initialize_repository", lambda **kwargs: {"success": True, "already_initialized": False})
    _wire("check_repository", lambda **kwargs: {"success": True})
    _wire("get_repository_stats", _get_repository_stats)
    _wire("get_repository_by_name", _get_repository_by_name)
    _wire("apply_retention_policy", _apply_retention_policy)
    _wire("validate_repository", _validate_repository)
    _wire("batch_validate_repositories", _batch_validate_repositories)
    _wire("set_default_repository", _set_default_repository)
    _wire("clear_default_repository", _clear_default_repository)
    _wire("unlock_repository", _unlock_repository)
    _wire("prune_repository", _simple_success)
    _wire("migrate_repository", _migrate_repository)
    _wire("forget_repository", _forget_repository)
    _wire("transition_repository_state", _transition_repository_state)
    _wire("set_repository_status", lambda status="active", **kwargs: _set_repository_status(status, **kwargs))
    _wire("activate_repository", lambda **kwargs: _set_repository_status("active", **kwargs))
    _wire("deactivate_repository", lambda **kwargs: _set_repository_status("inactive", **kwargs))
    _wire("archive_repository", lambda **kwargs: _set_repository_status("archived", **kwargs))
    _wire("rotate_credentials", _rotate_credentials)
    _wire("rotate_repository_password", _rotate_repository_password)
    _wire("rotate_repository_backend_credentials", _rotate_backend_credentials)

    mock_service_manager.get_system_monitoring_status.return_value = {
            "health_status": "healthy",
            "current_operations": 0,
            "recent_operations_24h": 0,
            "status_counts": {}
    }

    # Selection-template helpers for selection-driven backups
    mock_service_manager.selection_template_exists = MagicMock(return_value=True)
    mock_service_manager.get_selection_summary = MagicMock(
            side_effect=lambda name: f"Selection template: {name}"
    )
    mock_service_manager.suggest_selection_creation = MagicMock(
            side_effect=lambda name: f"Selection template '{name}' not found. Run tl selections create {name}."
    )
    mock_service_manager.run_selection_backup = MagicMock(
            return_value=SimpleNamespace(
                    status=SimpleNamespace(value="completed"),
                    snapshot_id="selection-snapshot-001",
                    files_processed=42,
                    bytes_transferred=2048,
                    duration=SimpleNamespace(total_seconds=lambda: 1.0),
                    warnings=[],
                    errors=[]
            )
    )

    # Expose stores for downstream fixtures (configuration manager, etc.)
    mock_service_manager._repo_store = repo_store
    mock_service_manager._ensure_repo = _ensure_repo
    mock_service_manager._default_state = default_state
    mock_service_manager._credential_store = credential_store

    return mock_service_manager


def create_mock_snapshot(snapshot_id: str = "abc123def", **kwargs) -> Dict[str, Any]:
    """
    Create a mock snapshot object for testing.
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        snapshot_id: Snapshot identifier
        **kwargs: Additional snapshot properties
        
    Returns:
        Mock snapshot dictionary
    """
    return create_test_snapshot(snapshot_id=snapshot_id, **kwargs)


def create_mock_repository(name: str = "test-repo", **kwargs) -> Dict[str, Any]:
    """
    Create a mock repository object for testing.
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        name: Repository name
        **kwargs: Additional repository properties
        
    Returns:
        Mock repository dictionary
    """
    return create_test_repository(name=name, **kwargs)


def create_mock_target(name: str = "test-target", **kwargs) -> Dict[str, Any]:
    """
    Create a mock backup target object for testing.
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        name: Target name
        **kwargs: Additional target properties
        
    Returns:
        Mock target dictionary
    """
    return create_test_target(name=name, **kwargs)


def assert_exit_code(result, expected_code: int, message: Optional[str] = None):
    """
    Assert specific exit code with helpful error message.
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        result: CliRunner result object
        expected_code: Expected exit code
        message: Optional custom error message
    """
    if expected_code == 0:
        _assert_cli_success(result, message)
    else:
        _assert_cli_error(result, expected_code, message)


def assert_success(result, message: Optional[str] = None):
    """
    Assert command succeeded (exit code 0).
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    _assert_cli_success(result, message)


def assert_command_error(result, message: Optional[str] = None):
    """
    Assert command failed with command error (exit code 2).
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    _assert_cli_error(result, 2, message)


class _DummyProgressTask:
    """No-op progress task used to stub progress services."""

    def update(self, *args, **kwargs):
        return None


class _DummyProgress:
    """Minimal Rich Progress replacement for CLI tests."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add_task(self, *args, **kwargs):
        return "task"

    def update(self, *args, **kwargs):
        return None


class _DummyProgressService:
    """Stub progress service matching the public API used by restore commands."""

    def spinner(self, *args, **kwargs):
        return nullcontext(_DummyProgressTask())

    def bar(self, *args, **kwargs):
        return nullcontext(_DummyProgressTask())


def _create_completed_operation(operation_id: str = "op-123"):
    """Return an object that mimics a completed recovery operation."""
    return SimpleNamespace(
            status=SimpleNamespace(value="completed"),
            operation_id=operation_id,
            progress=SimpleNamespace(files_processed=0),
    )


@contextmanager
def patch_restore_commands(mode: str = "success"):
    """
    Patch restore command dependencies for deterministic CLI tests.

    Args:
        mode: Either "success" (default) for happy-path behavior or
              "invalid_snapshot" to raise ValueError for snapshot-dependent operations.
    """
    stack = ExitStack()
    try:
        patched_objects = {}

        repository_mock = Mock(name="repository")
        patched_objects["repository"] = repository_mock
        stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore._get_repository", return_value=repository_mock)
        )

        browser_cls = stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.SnapshotBrowser")
        )
        browser_instance = browser_cls.return_value
        patched_objects["snapshot_browser"] = browser_instance

        snapshot_listing = SimpleNamespace(
                entries=[
                        SimpleNamespace(
                                name="example.txt",
                                path="/example.txt",
                                type=SimpleNamespace(value="file"),
                                size=1024,
                                modification_time=None,
                                permissions="rw-r--r--",
                        )
                ],
                total_entries=1,
                path="/",
        )
        browser_instance.list_snapshot_contents.return_value = snapshot_listing
        browser_instance.search_snapshot_files.return_value = snapshot_listing.entries
        browser_instance.compare_snapshots.return_value = SimpleNamespace(
                added_files=[],
                removed_files=[],
                modified_files=[],
                unchanged_files=[],
        )

        snapshot_manager_cls = stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.SnapshotManager")
        )
        snapshot_manager_instance = snapshot_manager_cls.return_value
        snapshot_manager_instance.list_snapshots.return_value = [
                SimpleNamespace(id="abc123def456")
        ]
        patched_objects["snapshot_manager"] = snapshot_manager_instance

        orchestrator_cls = stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.RecoveryOrchestrator")
        )
        orchestrator_instance = orchestrator_cls.return_value
        orchestrator_instance.initiate_full_recovery.return_value = _create_completed_operation("full-op")
        orchestrator_instance.initiate_selective_recovery.return_value = _create_completed_operation("files-op")
        orchestrator_instance.get_recovery_status.return_value = _create_completed_operation("status-op")
        patched_objects["recovery_orchestrator"] = orchestrator_instance

        restore_manager_cls = stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.RestoreManager")
        )
        restore_manager_instance = restore_manager_cls.return_value
        restore_manager_instance.mount_snapshot.return_value = None
        patched_objects["restore_manager"] = restore_manager_instance

        stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.get_progress_service", return_value=_DummyProgressService())
        )
        stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.Progress", _DummyProgress)
        )
        validator_cls = stack.enter_context(
                patch("TimeLocker.cli_modules.commands.restore.RecoveryValidator")
        )
        validator_instance = validator_cls.return_value
        validator_instance.validate_pre_recovery.return_value = SimpleNamespace(
                is_valid=True,
                validated_files=1,
                failed_validations=[],
                warnings=[]
        )
        patched_objects["recovery_validator"] = validator_instance

        if mode == "invalid_snapshot":
            def _raise_invalid(*_args, **_kwargs):
                raise ValueError("Invalid snapshot ID format")

            browser_instance.list_snapshot_contents.side_effect = _raise_invalid
            browser_instance.search_snapshot_files.side_effect = _raise_invalid
            orchestrator_instance.initiate_full_recovery.side_effect = _raise_invalid
            orchestrator_instance.initiate_selective_recovery.side_effect = _raise_invalid
            restore_manager_instance.mount_snapshot.side_effect = _raise_invalid

        yield patched_objects
    finally:
        stack.close()


def assert_handled_error(result, message: Optional[str] = None):
    """
    Assert command failed with handled error (exit code 1).
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    _assert_cli_error(result, 1, message)


def assert_output_contains(result, expected_text: str, case_sensitive: bool = False):
    """
    Assert that command output contains expected text.
    
    Note: This function now delegates to the centralized testing utilities.
    
    Args:
        result: CliRunner result object
        expected_text: Text that should be in output
        case_sensitive: Whether to perform case-sensitive matching
    """
    _assert_cli_output_contains(result, expected_text, case_sensitive)


def assert_help_quality(result, command_name: str):
    """
    Assert that help output meets quality standards.
    
    Note: This function now delegates to the centralized testing utilities.

    Args:
        result: CliRunner result object from --help command
        command_name: Name of the command being tested
    """
    _assert_cli_help_quality(result, command_name)


def create_mock_cli_service_manager() -> Mock:
    """
    Create properly structured mock CLIServiceManager matching actual implementation.
    
    Note: This function now delegates to the centralized testing utilities.
    
    This factory creates a mock that matches the actual CLIServiceManager structure
    with repository_service, snapshot_service, and config_module properties.
    Also provides direct method access for CLI commands that use _get_service_method.
    
    Returns:
        Mock CLIServiceManager with correct service structure
    """
    return create_mock_service_manager()
