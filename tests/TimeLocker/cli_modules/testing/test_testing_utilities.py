"""
Tests for CLI testing utilities.

This module tests the testing utilities themselves to ensure they work correctly.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from TimeLocker.cli_modules.testing import (
    # Fixtures
    CLITestFixtures,
    create_test_config,
    create_test_repository,
    create_test_snapshot,
    create_test_target,
    create_test_policy,
    create_test_selection,
    
    # Mocks
    MockServiceFactory,
    create_mock_service_manager,
    create_mock_config_service,
    create_mock_repository_resolver,
    create_mock_service_facade,
    create_mock_prompt_service,
    create_mock_output_formatter,
    create_mock_progress_service,
    
    # Generators
    TestDataGenerator,
    generate_snapshot_data,
    generate_repository_data,
    generate_backup_data,
    generate_restore_data,
    
    # Assertions
    CLIAssertions,
    
    # Runners
    CLITestRunner,
    get_test_runner,
)


class TestFixtures:
    """Tests for fixture factories."""
    
    def test_cli_test_fixtures(self):
        """Test CLITestFixtures container."""
        fixtures = CLITestFixtures()
        
        assert fixtures.default_repository_name == "test-repo"
        assert fixtures.default_snapshot_id == "abc123def456"
        
        repo = fixtures.get_test_repository()
        assert repo['name'] == "test-repo"
        
        snapshot = fixtures.get_test_snapshot()
        assert snapshot['id'] == "abc123def456"
    
    def test_create_test_config(self):
        """Test config fixture creation."""
        config = create_test_config()
        
        assert 'version' in config
        assert 'repositories' in config
        assert 'selections' in config
        assert 'policies' in config
        assert 'settings' in config
    
    def test_create_test_repository(self):
        """Test repository fixture creation."""
        repo = create_test_repository(name="my-repo", backend="s3")
        
        assert repo['name'] == "my-repo"
        assert repo['backend'] == "s3"
        assert 's3:' in repo['uri']
        assert repo['initialized'] is True
    
    def test_create_test_snapshot(self):
        """Test snapshot fixture creation."""
        snapshot = create_test_snapshot(
            snapshot_id="test123",
            repository="my-repo"
        )
        
        assert snapshot['id'] == "test123"
        assert snapshot['repository'] == "my-repo"
        assert snapshot['short_id'] == "test123"[:8]
    
    def test_create_test_target(self):
        """Test target fixture creation."""
        target = create_test_target(name="my-target")
        
        assert target['name'] == "my-target"
        assert isinstance(target['paths'], list)
        assert target['enabled'] is True
    
    def test_create_test_policy(self):
        """Test policy fixture creation."""
        policy = create_test_policy(name="my-policy")
        
        assert policy['name'] == "my-policy"
        assert policy['keep_last'] == 7
        assert policy['enabled'] is True
    
    def test_create_test_selection(self):
        """Test selection fixture creation."""
        selection = create_test_selection(name="my-selection")
        
        assert selection['name'] == "my-selection"
        assert isinstance(selection['include_patterns'], list)
        assert isinstance(selection['exclude_patterns'], list)


class TestMocks:
    """Tests for mock factories."""
    
    def test_mock_service_factory(self):
        """Test MockServiceFactory."""
        factory = MockServiceFactory()
        
        service_manager = factory.create_service_manager()
        assert service_manager is not None
        assert hasattr(service_manager, 'repository_service')
        
        config_service = factory.create_config_service()
        assert config_service is not None
        assert hasattr(config_service, 'get_config')
    
    def test_create_mock_service_manager(self):
        """Test service manager mock creation."""
        repos = [create_test_repository(name="repo1")]
        snapshots = [create_test_snapshot(snapshot_id="snap1")]
        
        mock_manager = create_mock_service_manager(
            repositories=repos,
            snapshots=snapshots
        )
        
        assert mock_manager.repository_service.list_repositories() == repos
        assert mock_manager.snapshot_service.list_snapshots() == snapshots
    
    def test_create_mock_config_service(self):
        """Test config service mock creation."""
        config = {'version': '1.0'}
        mock_service = create_mock_config_service(config=config)
        
        assert mock_service.get_config() == config
        assert mock_service.validate_config()['valid'] is True
    
    def test_create_mock_repository_resolver(self):
        """Test repository resolver mock creation."""
        repos = {'test-repo': create_test_repository(name="test-repo")}
        mock_resolver = create_mock_repository_resolver(repositories=repos)
        
        resolved = mock_resolver.resolve_repository("test-repo")
        assert resolved['name'] == "test-repo"
    
    def test_create_mock_service_facade(self):
        """Test service facade mock creation."""
        mock_facade = create_mock_service_facade()
        
        assert mock_facade.get_backup_service() is not None
        assert mock_facade.get_restore_service() is not None
        assert mock_facade.health_check()['healthy'] is True
    
    def test_create_mock_prompt_service(self):
        """Test prompt service mock creation."""
        responses = {
            'text': 'custom-input',
            'confirm': False
        }
        mock_service = create_mock_prompt_service(responses=responses)
        
        assert mock_service.prompt_text() == 'custom-input'
        assert mock_service.prompt_confirm() is False
    
    def test_create_mock_output_formatter(self):
        """Test output formatter mock creation."""
        mock_formatter = create_mock_output_formatter()
        
        assert mock_formatter.format_table([]) is not None
        assert mock_formatter.format_json({}) is not None
    
    def test_create_mock_progress_service(self):
        """Test progress service mock creation."""
        mock_service = create_mock_progress_service()
        
        progress = mock_service.create_progress()
        assert progress is not None
        
        # Test context manager
        with mock_service.with_progress() as p:
            assert p is not None


class TestGenerators:
    """Tests for test data generators."""
    
    def test_test_data_generator(self):
        """Test TestDataGenerator class."""
        generator = TestDataGenerator(seed=42)
        
        snapshot_id = generator.generate_snapshot_id()
        assert len(snapshot_id) == 16
        
        repo_name = generator.generate_repository_name()
        assert repo_name.startswith("repo-")
    
    def test_generate_snapshot_data(self):
        """Test snapshot data generation."""
        snapshot = generate_snapshot_data(repository="test-repo")
        
        assert 'id' in snapshot
        assert 'repository' in snapshot
        assert snapshot['repository'] == "test-repo"
        assert len(snapshot['id']) == 16
    
    def test_generate_repository_data(self):
        """Test repository data generation."""
        repo = generate_repository_data(backend="s3")
        
        assert 'name' in repo
        assert 'uri' in repo
        assert repo['backend'] == "s3"
        assert 's3:' in repo['uri']
    
    def test_generate_backup_data(self):
        """Test backup data generation."""
        backup = generate_backup_data(repository="test-repo")
        
        assert backup['repository'] == "test-repo"
        assert isinstance(backup['paths'], list)
        assert isinstance(backup['tags'], list)
    
    def test_generate_restore_data(self):
        """Test restore data generation."""
        restore = generate_restore_data(repository="test-repo")
        
        assert restore['repository'] == "test-repo"
        assert 'snapshot_id' in restore
        assert 'target_path' in restore
    
    def test_generate_snapshots(self):
        """Test generating multiple snapshots."""
        generator = TestDataGenerator(seed=42)
        snapshots = generator.generate_snapshots(count=5, repository="test-repo")
        
        assert len(snapshots) == 5
        for snapshot in snapshots:
            assert snapshot['repository'] == "test-repo"
    
    def test_generate_repositories(self):
        """Test generating multiple repositories."""
        generator = TestDataGenerator(seed=42)
        repos = generator.generate_repositories(count=3, backend="local")
        
        assert len(repos) == 3
        for repo in repos:
            assert repo['backend'] == "local"


class TestAssertions:
    """Tests for assertion helpers."""
    
    def test_cli_assertions_class(self):
        """Test CLIAssertions class."""
        assertions = CLIAssertions()
        
        # Create mock result
        result = Mock()
        result.exit_code = 0
        result.stdout = "Success"
        result.stderr = ""
        
        # Should not raise
        assertions.assert_success(result)
        assertions.assert_output_contains(result, "Success")
    
    def test_assert_success(self):
        """Test success assertion."""
        from TimeLocker.cli_modules.testing import assert_cli_success
        
        result = Mock()
        result.exit_code = 0
        result.stdout = "Success"
        
        # Should not raise
        assert_cli_success(result)
    
    def test_assert_error(self):
        """Test error assertion."""
        from TimeLocker.cli_modules.testing import assert_cli_error
        
        result = Mock()
        result.exit_code = 1
        result.stdout = "Error"
        
        # Should not raise
        assert_cli_error(result, exit_code=1)
    
    def test_assert_output_contains(self):
        """Test output contains assertion."""
        from TimeLocker.cli_modules.testing import assert_cli_output_contains
        
        result = Mock()
        result.stdout = "Success message"
        result.stderr = ""
        
        # Should not raise
        assert_cli_output_contains(result, "Success")
        assert_cli_output_contains(result, "success", case_sensitive=False)


class TestRunners:
    """Tests for CLI test runners."""
    
    def test_cli_test_runner(self):
        """Test CLITestRunner class."""
        runner = CLITestRunner(columns=200)
        
        assert runner.columns == 200
        assert 'COLUMNS' in runner.env
        assert runner.env['TIMELOCKER_TEST_MODE'] == '1'
    
    def test_get_test_runner(self):
        """Test get_test_runner function."""
        runner = get_test_runner()
        
        assert isinstance(runner, CLITestRunner)
        assert runner.columns == 200
    
    def test_runner_get_output(self):
        """Test runner output retrieval."""
        runner = get_test_runner()
        
        result = Mock()
        result.stdout = "stdout content"
        result.stderr = "stderr content"
        
        output = runner.get_output(result)
        assert "stdout content" in output
        assert "stderr content" in output
