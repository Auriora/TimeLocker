"""
Testing utilities for CLI commands.

This module provides shared test fixtures, mock factories, test data generators,
and assertion helpers to simplify and standardize CLI command testing.
"""

from .fixtures import (
    CLITestFixtures,
    create_test_config,
    create_test_repository,
    create_test_snapshot,
    create_test_target,
    create_test_policy,
    create_test_selection,
)

from .mocks import (
    MockServiceFactory,
    create_mock_service_manager,
    create_mock_config_service,
    create_mock_repository_resolver,
    create_mock_service_facade,
    create_mock_prompt_service,
    create_mock_output_formatter,
    create_mock_progress_service,
)

from .generators import (
    TestDataGenerator,
    generate_snapshot_data,
    generate_repository_data,
    generate_backup_data,
    generate_restore_data,
)

from .assertions import (
    CLIAssertions,
    assert_cli_success,
    assert_cli_error,
    assert_cli_output_contains,
    assert_cli_help_quality,
    assert_service_called,
    assert_service_not_called,
)

from .runners import (
    CLITestRunner,
    get_test_runner,
    run_cli_command,
)

__all__ = [
    # Fixtures
    'CLITestFixtures',
    'create_test_config',
    'create_test_repository',
    'create_test_snapshot',
    'create_test_target',
    'create_test_policy',
    'create_test_selection',
    
    # Mocks
    'MockServiceFactory',
    'create_mock_service_manager',
    'create_mock_config_service',
    'create_mock_repository_resolver',
    'create_mock_service_facade',
    'create_mock_prompt_service',
    'create_mock_output_formatter',
    'create_mock_progress_service',
    
    # Generators
    'TestDataGenerator',
    'generate_snapshot_data',
    'generate_repository_data',
    'generate_backup_data',
    'generate_restore_data',
    
    # Assertions
    'CLIAssertions',
    'assert_cli_success',
    'assert_cli_error',
    'assert_cli_output_contains',
    'assert_cli_help_quality',
    'assert_service_called',
    'assert_service_not_called',
    
    # Runners
    'CLITestRunner',
    'get_test_runner',
    'run_cli_command',
]
