"""
Integration tests for CLI with real service implementations.

These tests verify that CLI commands work correctly with actual service
implementations (not mocks), testing real configuration files, service
integration, and end-to-end workflows.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock

from src.TimeLocker.cli import app
from src.TimeLocker.cli_services import CLIServiceManager
from src.TimeLocker.services.configuration_service import ConfigurationService
from src.TimeLocker.services.repository_service import RepositoryService
from src.TimeLocker.services.snapshot_service import SnapshotService
from src.TimeLocker.services.validation_service import ValidationService
from src.TimeLocker.utils.performance_utils import PerformanceModule
from src.TimeLocker.config.configuration_module import ConfigurationModule
from tests.TimeLocker.cli.test_utils import get_cli_runner, assert_success

runner = get_cli_runner()


class TestCLIRealServiceIntegration:
    """Test CLI integration with real service implementations"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory with real config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            
            # Create a real configuration file
            config_data = {
                "general": {
                    "app_name": "TimeLocker",
                    "version": "1.0.0",
                    "log_level": "INFO"
                },
                "repositories": {},
                "backup_targets": {},
                "backup": {
                    "compression": "auto",
                    "exclude_caches": True,
                    "verify_after_backup": True
                },
                "restore": {
                    "verify_after_restore": True,
                    "create_target_directory": True
                },
                "security": {
                    "encryption_enabled": True,
                    "audit_logging": True
                }
            }
            
            config_file.write_text(json.dumps(config_data, indent=2))
            yield config_dir

    @pytest.fixture
    def real_validation_service(self):
        """Create a real ValidationService instance"""
        return ValidationService()

    @pytest.fixture
    def real_performance_module(self):
        """Create a real PerformanceModule instance"""
        return PerformanceModule()

    @pytest.fixture
    def real_configuration_service(self, temp_config_dir):
        """Create a real ConfigurationService with actual config file"""
        config_file = temp_config_dir / "config.json"
        validation_service = ValidationService()
        return ConfigurationService(
            config_path=config_file,
            validation_service=validation_service
        )

    @pytest.fixture
    def real_repository_service(self, real_validation_service, real_performance_module):
        """Create a real RepositoryService instance"""
        return RepositoryService(
            validation_service=real_validation_service,
            performance_module=real_performance_module
        )

    @pytest.fixture
    def real_snapshot_service(self, real_validation_service, real_performance_module):
        """Create a real SnapshotService instance"""
        return SnapshotService(
            validation_service=real_validation_service,
            performance_module=real_performance_module
        )

    @pytest.mark.integration
    def test_configuration_service_integration(self, real_configuration_service, temp_config_dir):
        """Test CLI integration with real ConfigurationService"""
        # Test loading configuration
        config = real_configuration_service.load_configuration()
        assert config is not None
        assert "general" in config
        assert "repositories" in config
        
        # Test adding repository through service
        repo_config = {
            "name": "test-repo",
            "uri": "file:///tmp/test-repo",
            "description": "Test repository"
        }
        real_configuration_service.add_repository(repo_config)
        
        # Verify repository was added
        repos = real_configuration_service.get_repositories()
        assert len(repos) == 1
        assert repos[0]["name"] == "test-repo"
        
        # Test saving configuration
        config = real_configuration_service._config_data
        real_configuration_service.save_configuration(config)
        
        # Verify file was updated
        config_file = temp_config_dir / "config.json"
        assert config_file.exists()
        saved_data = json.loads(config_file.read_text())
        assert "test-repo" in saved_data["repositories"]

    @pytest.mark.integration
    def test_configuration_module_integration(self, temp_config_dir):
        """Test CLI integration with real ConfigurationModule"""
        # Create ConfigurationModule with real config directory
        config_module = ConfigurationModule(config_dir=temp_config_dir)
        
        # Test getting configuration
        config = config_module.get_config()
        assert config is not None
        
        # Test adding repository
        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        repo_config = RepositoryConfig(
            name="test-repo",
            location="file:///tmp/test-repo",
            description="Test repository"
        )
        config_module.add_repository(repo_config)
        
        # Verify repository was added
        retrieved_repo = config_module.get_repository("test-repo")
        assert retrieved_repo.name == "test-repo"
        assert retrieved_repo.location == "file:///tmp/test-repo"

    @pytest.mark.integration
    def test_validation_service_integration(self, real_validation_service):
        """Test CLI integration with real ValidationService"""
        # Test repository config validation
        valid_repo_config = {
            "name": "test-repo",
            "uri": "file:///tmp/test-repo",
            "description": "Test repository"
        }
        result = real_validation_service.validate_repository_config(valid_repo_config)
        assert result.is_valid is True
        assert len(result.errors) == 0
        
        # Test invalid repository config
        invalid_repo_config = {
            "name": "",  # Empty name is invalid
            "uri": "file:///tmp/test-repo"
        }
        result = real_validation_service.validate_repository_config(invalid_repo_config)
        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.integration
    def test_cli_service_manager_real_services(self, temp_config_dir):
        """Test CLIServiceManager with real service instances"""
        # Create CLIServiceManager with real config directory
        manager = CLIServiceManager(config_dir=temp_config_dir)
        
        # Verify services are initialized
        assert manager.config_module is not None
        assert manager.repository_factory is not None
        assert manager.snapshot_service is not None
        assert manager.repository_service is not None
        
        # Test configuration operations
        config = manager.config_module.get_config()
        assert config is not None
        
        # Test adding repository through manager
        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        repo_config = RepositoryConfig(
            name="integration-test-repo",
            location="file:///tmp/integration-test",
            description="Integration test repository"
        )
        manager.config_module.add_repository(repo_config)
        
        # Verify repository was added
        repos = manager.config_module.get_repositories()
        assert any(r.get("name") == "integration-test-repo" for r in repos)

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_cli_repos_commands_with_real_config(self, mock_get_manager, temp_config_dir):
        """Test repos commands with real configuration file"""
        # Create real service manager
        real_manager = CLIServiceManager(config_dir=temp_config_dir)
        mock_get_manager.return_value = real_manager
        
        # Test repos list command (should work even with no repos)
        result = runner.invoke(app, [
            "repos", "list",
            "--config-dir", str(temp_config_dir)
        ])
        
        # Should succeed even if no repositories configured
        assert result.exit_code == 0, f"Repos list should succeed. Output: {result.stdout}"

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_cli_repos_list_with_real_config(self, mock_get_manager, temp_config_dir):
        """Test repos list command with real configuration"""
        # Create real service manager and add a repository
        real_manager = CLIServiceManager(config_dir=temp_config_dir)
        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        repo_config = RepositoryConfig(
            name="test-repo",
            location="file:///tmp/test-repo",
            description="Test repository"
        )
        real_manager.config_module.add_repository(repo_config)
        
        mock_get_manager.return_value = real_manager
        
        # Run repos list command
        result = runner.invoke(app, [
            "repos", "list",
            "--config-dir", str(temp_config_dir)
        ])
        
        assert_success(result, "Repos list should succeed with real configuration")
        output = result.stdout
        assert "test-repo" in output

    @pytest.mark.integration
    def test_cli_service_manager_list_repositories_refreshes_config(self, temp_config_dir):
        """CLIServiceManager should reflect repositories added after initialization."""
        manager = CLIServiceManager(config_dir=temp_config_dir)

        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        repo_config = RepositoryConfig(
            name="refresh-repo",
            location="file:///tmp/refresh-repo",
            description="Repository added after manager initialization",
        )
        manager.config_module.add_repository(repo_config)

        repositories = manager.list_repositories()

        assert any(repo.get("name") == "refresh-repo" for repo in repositories)

    @pytest.mark.integration
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_cli_repos_add_with_real_config(self, mock_get_manager, temp_config_dir):
        """Test repos add command with real configuration persistence"""
        # Create real service manager
        real_manager = CLIServiceManager(config_dir=temp_config_dir)
        mock_get_manager.return_value = real_manager
        
        # Run repos add command
        result = runner.invoke(app, [
            "repos", "add", "new-repo", "file:///tmp/new-repo",
            "--description", "New test repository",
            "--config-dir", str(temp_config_dir)
        ])
        
        assert_success(result, "Repos add should succeed with real configuration")
        
        # Verify repository was persisted to config file
        config_file = temp_config_dir / "config.json"
        config_data = json.loads(config_file.read_text())
        assert "new-repo" in config_data["repositories"]
        assert config_data["repositories"]["new-repo"]["uri"] == "file:///tmp/new-repo"

    @pytest.mark.integration
    def test_end_to_end_repository_workflow_real_services(self, temp_config_dir):
        """Test complete repository workflow with real services"""
        # Create real service manager
        manager = CLIServiceManager(config_dir=temp_config_dir)
        
        # Step 1: Add repository
        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        repo_config = RepositoryConfig(
            name="workflow-repo",
            location="file:///tmp/workflow-repo",
            description="Workflow test repository"
        )
        manager.config_module.add_repository(repo_config)
        
        # Step 2: Verify repository exists
        repos = manager.config_module.get_repositories()
        assert any(r.get("name") == "workflow-repo" for r in repos)
        
        # Step 3: Get repository details
        repo = manager.config_module.get_repository("workflow-repo")
        assert repo.name == "workflow-repo"
        assert repo.location == "file:///tmp/workflow-repo"
        
        # Step 4: Update repository description using correct signature
        updated_config = RepositoryConfig(
            name="workflow-repo",
            location="file:///tmp/workflow-repo",
            description="Updated description"
        )
        manager.config_module.update_repository("workflow-repo", updated_config)
        
        # Step 5: Verify update persisted
        updated_repo = manager.config_module.get_repository("workflow-repo")
        assert updated_repo.description == "Updated description"
        
        # Step 6: Remove repository
        manager.config_module.remove_repository("workflow-repo")
        
        # Step 7: Verify repository removed
        repos = manager.config_module.get_repositories()
        assert not any(r.get("name") == "workflow-repo" for r in repos)

    @pytest.mark.integration
    def test_end_to_end_backup_target_workflow_real_services(self, temp_config_dir):
        """Test complete backup target workflow with real services"""
        # Create real service manager
        manager = CLIServiceManager(config_dir=temp_config_dir)
        
        # Step 1: Add backup target
        from src.TimeLocker.config.configuration_schema import BackupTargetConfig
        target_config = BackupTargetConfig(
            name="workflow-target",
            paths=["/tmp/test-data"],
            description="Workflow test target"
        )
        manager.config_module.add_backup_target(target_config)
        
        # Step 2: Verify target exists
        targets = manager.config_module.get_backup_targets()
        assert any(t.get("name") == "workflow-target" for t in targets)
        
        # Step 3: Get target details
        target = manager.config_module.get_backup_target("workflow-target")
        assert target.name == "workflow-target"
        assert "/tmp/test-data" in target.paths
        
        # Step 4: Update target paths using correct signature
        updated_config = BackupTargetConfig(
            name="workflow-target",
            paths=["/tmp/test-data", "/tmp/additional-data"],
            description="Workflow test target"
        )
        manager.config_module.update_backup_target("workflow-target", updated_config)
        
        # Step 5: Verify update persisted
        updated_target = manager.config_module.get_backup_target("workflow-target")
        assert "/tmp/additional-data" in updated_target.paths
        
        # Step 6: Remove target
        manager.config_module.remove_backup_target("workflow-target")
        
        # Step 7: Verify target removed
        targets = manager.config_module.get_backup_targets()
        assert not any(t.get("name") == "workflow-target" for t in targets)

    @pytest.mark.integration
    def test_configuration_validation_with_real_services(self, temp_config_dir):
        """Test configuration validation with real ValidationService"""
        # Create real services
        validation_service = ValidationService()
        config_service = ConfigurationService(
            config_path=temp_config_dir / "config.json",
            validation_service=validation_service
        )
        
        # Test valid configuration
        valid_config = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {},
            "backup_targets": {}
        }
        assert config_service.validate_configuration(valid_config) is True
        
        # Test invalid configuration (missing required section)
        invalid_config = {
            "general": {"app_name": "TimeLocker"}
            # Missing repositories and backup_targets
        }
        with pytest.raises(Exception):  # Should raise InvalidConfigurationError
            config_service.validate_configuration(invalid_config)

    @pytest.mark.integration
    def test_service_health_checks_real_services(self, temp_config_dir):
        """Test service health checks with real service instances"""
        # Create real service manager
        manager = CLIServiceManager(config_dir=temp_config_dir)
        
        # Test repository service health
        repo_service = manager.repository_service
        # Health check should fail before initialization
        assert repo_service.health_check() is False
        
        # Initialize service with proper context from manager
        if manager._service_context:
            repo_service.initialize(manager._service_context)
            
            # Health check should pass after initialization
            assert repo_service.health_check() is True
            
            # Test snapshot service health
            snapshot_service = manager.snapshot_service
            snapshot_service.initialize(manager._service_context)
            assert snapshot_service.health_check() is True

    @pytest.mark.integration
    def test_multi_step_configuration_workflow(self, temp_config_dir):
        """Test complex multi-step configuration workflow with real services"""
        # Create real service manager
        manager = CLIServiceManager(config_dir=temp_config_dir)
        
        # Step 1: Add multiple repositories
        from src.TimeLocker.config.configuration_schema import RepositoryConfig
        for i in range(3):
            repo_config = RepositoryConfig(
                name=f"repo-{i}",
                location=f"file:///tmp/repo-{i}",
                description=f"Repository {i}"
            )
            manager.config_module.add_repository(repo_config)
        
        # Step 2: Add multiple backup targets
        from src.TimeLocker.config.configuration_schema import BackupTargetConfig
        for i in range(2):
            target_config = BackupTargetConfig(
                name=f"target-{i}",
                paths=[f"/tmp/data-{i}"],
                description=f"Target {i}"
            )
            manager.config_module.add_backup_target(target_config)
        
        # Step 3: Verify all entities exist
        repos = manager.config_module.get_repositories()
        assert len(repos) == 3
        
        targets = manager.config_module.get_backup_targets()
        assert len(targets) == 2
        
        # Step 4: Update one repository using correct signature
        repo = manager.config_module.get_repository("repo-1")
        updated_config = RepositoryConfig(
            name="repo-1",
            location=repo.location,
            description="Updated repository 1"
        )
        manager.config_module.update_repository("repo-1", updated_config)
        
        # Step 5: Remove one target
        manager.config_module.remove_backup_target("target-0")
        
        # Step 6: Verify final state
        repos = manager.config_module.get_repositories()
        assert len(repos) == 3
        assert manager.config_module.get_repository("repo-1").description == "Updated repository 1"
        
        targets = manager.config_module.get_backup_targets()
        assert len(targets) == 1
        assert targets[0].get("name") == "target-1"
        
        # Step 7: Verify persistence
        config_file = temp_config_dir / "config.json"
        config_data = json.loads(config_file.read_text())
        assert len(config_data["repositories"]) == 3
        assert len(config_data["backup_targets"]) == 1
