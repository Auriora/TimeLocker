"""
Shared utilities for CLI testing.

This module provides common utilities and helper functions used across
all CLI test files to reduce code duplication and ensure consistency.
"""

from typer.testing import CliRunner
from unittest.mock import Mock, MagicMock
from typing import Any, Dict, Optional
from TimeLocker.cli_services import CLIServiceManager
from TimeLocker.services.snapshot_service import SnapshotService
from TimeLocker.services.repository_service import RepositoryService


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


def create_mock_service_manager() -> Mock:
    """
    Create a standardized mock service manager for CLI testing.

    Uses spec_set to ensure mocks match the actual CLIServiceManager interface,
    catching typos and ensuring mocks match real implementations.

    Returns:
        Mock service manager with common methods configured with realistic return values
    """
    # Create mock with spec to match actual CLIServiceManager interface
    mock_service_manager = Mock(spec=CLIServiceManager)

    # Configure service properties with specs matching actual service classes
    mock_service_manager.snapshot_service = Mock(spec=SnapshotService)
    mock_service_manager.repository_service = Mock(spec=RepositoryService)

    # Configure backup orchestrator (using Mock without spec as it's an interface)
    mock_service_manager.backup_orchestrator = Mock()
    mock_service_manager.configuration_service = Mock()
    mock_service_manager.config_module = Mock()

    # Configure common return values with more realistic Mock objects
    # This provides better test coverage for edge cases and attribute access
    mock_service_manager.backup_orchestrator.execute_backup.return_value = Mock(
            success=True,
            snapshot_id="test123abc"
    )
    mock_service_manager.snapshot_service.list_snapshots.return_value = []
    mock_service_manager.repository_service.list_repositories.return_value = []

    return mock_service_manager


def create_mock_snapshot(snapshot_id: str = "abc123def", **kwargs) -> Dict[str, Any]:
    """
    Create a mock snapshot object for testing.
    
    Args:
        snapshot_id: Snapshot identifier
        **kwargs: Additional snapshot properties
        
    Returns:
        Mock snapshot dictionary
    """
    snapshot = {
            'id':       snapshot_id,
            'time':     '2024-01-01T12:00:00Z',
            'hostname': 'test-host',
            'username': 'test-user',
            'paths':    ['/home/user'],
            'tags':     [],
            'short_id': snapshot_id[:8] if len(snapshot_id) >= 8 else snapshot_id,
            **kwargs
    }
    return snapshot


def create_mock_repository(name: str = "test-repo", **kwargs) -> Dict[str, Any]:
    """
    Create a mock repository object for testing.
    
    Args:
        name: Repository name
        **kwargs: Additional repository properties
        
    Returns:
        Mock repository dictionary
    """
    repository = {
            'name':        name,
            'uri':         f'file:///tmp/{name}',
            'initialized': True,
            'locked':      False,
            **kwargs
    }
    return repository


def create_mock_target(name: str = "test-target", **kwargs) -> Dict[str, Any]:
    """
    Create a mock backup target object for testing.
    
    Args:
        name: Target name
        **kwargs: Additional target properties
        
    Returns:
        Mock target dictionary
    """
    target = {
            'name':             name,
            'paths':            ['/home/user/Documents'],
            'exclude_patterns': [],
            'include_patterns': [],
            'tags':             [],
            **kwargs
    }
    return target


def assert_exit_code(result, expected_code: int, message: Optional[str] = None):
    """
    Assert specific exit code with helpful error message.
    
    Args:
        result: CliRunner result object
        expected_code: Expected exit code
        message: Optional custom error message
    """
    if result.exit_code != expected_code:
        output = combined_output(result)
        error_msg = (
                f"Expected exit code {expected_code}, got {result.exit_code}\n"
                f"Output: {output}"
        )
        if message:
            error_msg = f"{message}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_success(result, message: Optional[str] = None):
    """
    Assert command succeeded (exit code 0).
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    assert_exit_code(result, 0, message)


def assert_command_error(result, message: Optional[str] = None):
    """
    Assert command failed with command error (exit code 2).
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    assert_exit_code(result, 2, message)


def assert_handled_error(result, message: Optional[str] = None):
    """
    Assert command failed with handled error (exit code 1).
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    """
    assert_exit_code(result, 1, message)


def assert_output_contains(result, expected_text: str, case_sensitive: bool = False):
    """
    Assert that command output contains expected text.
    
    Args:
        result: CliRunner result object
        expected_text: Text that should be in output
        case_sensitive: Whether to perform case-sensitive matching
    """
    output = combined_output(result)
    if not case_sensitive:
        output = output.lower()
        expected_text = expected_text.lower()

    if expected_text not in output:
        raise AssertionError(
                f"Expected text '{expected_text}' not found in output:\n{output}"
        )


def assert_help_quality(result, command_name: str):
    """
    Assert that help output meets quality standards.

    Args:
        result: CliRunner result object from --help command
        command_name: Name of the command being tested
    """
    assert_success(result, f"Help for '{command_name}' should succeed")

    output = combined_output(result)

    # Check for basic help structure
    assert "Usage:" in output, f"Help for '{command_name}' should show usage"
    assert "Options" in output or "Arguments" in output, f"Help for '{command_name}' should show options/arguments"

    # Check for helpful content (minimum 50 chars ensures more than just a basic stub)
    # This threshold was chosen to catch cases where help text is missing or truncated
    # while allowing for simple commands with minimal documentation
    assert len(output.strip()) > 50, f"Help for '{command_name}' should be substantial"

    # Check that help doesn't contain error indicators
    error_indicators = ["error", "failed", "exception", "traceback"]
    output_lower = output.lower()
    for indicator in error_indicators:
        assert indicator not in output_lower, f"Help for '{command_name}' should not contain '{indicator}'"


def create_mock_cli_service_manager() -> Mock:
    """
    Create properly structured mock CLIServiceManager matching actual implementation.
    
    This factory creates a mock that matches the actual CLIServiceManager structure
    with repository_service, snapshot_service, and config_module properties.
    Also provides direct method access for CLI commands that use _get_service_method.
    
    Returns:
        Mock CLIServiceManager with correct service structure
    """
    # Don't use spec as it prevents dynamic attribute assignment
    mock_manager = Mock()
    
    # Repository service with common methods (no spec to allow dynamic attributes)
    mock_manager.repository_service = Mock()
    mock_manager.repository_service.list_repositories.return_value = []
    mock_manager.repository_service.get_repository.return_value = None
    mock_manager.repository_service.add_repository.return_value = {'success': True}
    mock_manager.repository_service.remove_repository.return_value = {'success': True}
    mock_manager.repository_service.update_repository.return_value = {'success': True}
    mock_manager.repository_service.initialize_repository.return_value = {'success': True, 'already_initialized': False}
    mock_manager.repository_service.check_repository.return_value = {'success': True}
    mock_manager.repository_service.get_repository_stats.return_value = {}
    
    # Snapshot service with common methods (no spec to allow dynamic attributes)
    mock_manager.snapshot_service = Mock()
    mock_manager.snapshot_service.list_snapshots.return_value = []
    mock_manager.snapshot_service.get_snapshot.return_value = None
    mock_manager.snapshot_service.find_snapshots.return_value = []
    mock_manager.snapshot_service.delete_snapshot.return_value = {'success': True}
    
    # Config module (no spec to allow dynamic attributes)
    mock_manager.config_module = Mock()
    mock_manager.config_module.get_repository.return_value = None
    mock_manager.config_module.list_repositories.return_value = []
    
    # Backup orchestrator (currently not implemented in actual code)
    mock_manager.backup_orchestrator = None
    
    # Service manager properties
    mock_manager._is_initialized = True
    mock_manager._config_dir = None
    
    # IMPORTANT: CLI commands use _get_service_method which looks for methods directly on the manager
    # So we need to provide direct method access that delegates to the services
    mock_manager.list_repositories = mock_manager.repository_service.list_repositories
    mock_manager.get_repository = mock_manager.repository_service.get_repository
    mock_manager.add_repository = mock_manager.repository_service.add_repository
    mock_manager.remove_repository = mock_manager.repository_service.remove_repository
    mock_manager.update_repository = mock_manager.repository_service.update_repository
    mock_manager.initialize_repository = mock_manager.repository_service.initialize_repository
    mock_manager.check_repository = mock_manager.repository_service.check_repository
    mock_manager.get_repository_stats = mock_manager.repository_service.get_repository_stats
    mock_manager.list_snapshots = mock_manager.snapshot_service.list_snapshots
    mock_manager.get_snapshot = mock_manager.snapshot_service.get_snapshot
    mock_manager.find_snapshots = mock_manager.snapshot_service.find_snapshots
    
    return mock_manager
