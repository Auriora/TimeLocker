"""
Shared utilities for CLI testing.

This module provides common utilities and helper functions used across
all CLI test files to reduce code duplication and ensure consistency.

Note: This module now re-exports utilities from the centralized
TimeLocker.cli_modules.testing package for backward compatibility.
New tests should import directly from TimeLocker.cli_modules.testing.
"""

from typer.testing import CliRunner
from unittest.mock import Mock, MagicMock
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
    return _create_mock_service_manager()
