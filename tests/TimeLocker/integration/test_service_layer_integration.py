"""
Integration tests for CLI Refactoring Service Layer

This module tests the integration of ConfigurationService, RepositoryResolver,
and ServiceFacade with real configuration files and service managers.

Requirements addressed:
- Task 4.1: Integration testing for service layer components
- Validates ConfigService with real configuration files
- Validates RepositoryResolver with various repository types
- Validates ServiceFacade with service manager
- Includes performance benchmarks
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

from TimeLocker.services.configuration_service import ConfigurationService
from TimeLocker.utils.repository_resolver import (
    resolve_repository_uri,
    get_repository_info,
    list_available_repositories,
    normalize_repository_uri,
    validate_repository_name_or_uri
)
from TimeLocker.utils.service_facade import ServiceFacade, create_service_facade
from TimeLocker.interfaces import ConfigurationError


class TestConfigurationServiceIntegration:
    """Integration tests for ConfigurationService with real configuration files"""
    
    def test_load_real_configuration_file(self, tmp_path):
        """Test loading a real configuration file"""
        # Create a real configuration file
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {
                "app_name": "TimeLocker",
                "version": "1.0.0",
                "log_level": "INFO"
            },
            "repositories": {
                "local-test": {
                    "uri": "file:///tmp/test-repo",
                    "location": "file:///tmp/test-repo",
                    "description": "Test repository"
                },
                "s3-test": {
                    "uri": "s3:minio.lan/test-bucket",
                    "location": "s3:minio.lan/test-bucket",
                    "description": "S3 test repository"
                }
            },
            "backup_targets": {
                "home": {
                    "paths": ["/home/user"],
                    "description": "Home directory"
                }
            },
            "backup": {
                "compression": "auto",
                "exclude_caches": True
            },
            "restore": {
                "verify_after_restore": True
            },
            "security": {
                "encryption_enabled": True
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Load configuration
        config_service = ConfigurationService(config_path=config_file)
        
        # Verify configuration loaded correctly
        assert config_service.get_config_value("general.app_name") == "TimeLocker"
        assert config_service.get_config_value("general.version") == "1.0.0"
        
        # Verify repositories loaded
        repos = config_service.get_repositories()
        assert len(repos) == 2
        repo_names = [r['name'] for r in repos]
        assert "local-test" in repo_names
        assert "s3-test" in repo_names
        
        # Verify backup targets loaded
        targets = config_service.get_backup_targets()
        assert len(targets) == 1
        assert targets[0]['name'] == "home"
    
    def test_save_and_reload_configuration(self, tmp_path):
        """Test saving configuration and reloading it"""
        config_file = tmp_path / "config.json"
        
        # Create initial configuration
        config_service = ConfigurationService(config_path=config_file)
        
        # Add a repository
        config_service.add_repository({
            "name": "test-repo",
            "uri": "file:///tmp/test",
            "location": "file:///tmp/test",
            "description": "Test repository"
        })
        
        # Save configuration
        config_service.save_configuration(config_service._config_data, config_file)
        
        # Create new service instance and load
        new_service = ConfigurationService(config_path=config_file)
        
        # Verify repository was persisted
        repo = new_service.get_repository_by_name("test-repo")
        assert repo['name'] == "test-repo"
        assert repo['location'] == "file:///tmp/test"
    
    def test_configuration_validation_with_invalid_data(self, tmp_path):
        """Test configuration validation rejects invalid data"""
        config_file = tmp_path / "config.json"
        
        # Create configuration with invalid repository (missing uri)
        invalid_config = {
            "general": {
                "app_name": "TimeLocker"
            },
            "repositories": {
                "bad-repo": {
                    "description": "Missing URI"
                    # Missing required 'uri' field
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(invalid_config, f)
        
        # Should raise error on load
        with pytest.raises(ConfigurationError):
            ConfigurationService(config_path=config_file)
    
    def test_configuration_caching_performance(self, tmp_path):
        """Test configuration caching improves performance"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {},
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config_service = ConfigurationService(config_path=config_file)
        
        # First access (should load from file)
        start = time.time()
        value1 = config_service.get_config_value("general.app_name")
        first_access_time = time.time() - start
        
        # Second access (should use cache)
        start = time.time()
        value2 = config_service.get_config_value("general.app_name")
        second_access_time = time.time() - start
        
        assert value1 == value2
        # Cache access should be faster (or at least not significantly slower)
        assert second_access_time <= first_access_time * 2


class TestRepositoryResolverIntegration:
    """Integration tests for RepositoryResolver with various repository types"""
    
    def test_resolve_named_repository(self, tmp_path):
        """Test resolving a named repository from configuration"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                "production": {
                    "uri": "s3:s3.amazonaws.com/prod-bucket",
                    "location": "s3:s3.amazonaws.com/prod-bucket",
                    "description": "Production repository"
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Resolve repository
        uri = resolve_repository_uri("production", config_dir=tmp_path)
        
        assert uri == "s3:s3.amazonaws.com/prod-bucket"
    
    def test_resolve_direct_uri_passthrough(self, tmp_path):
        """Test that direct URIs are passed through unchanged"""
        # S3 URI
        uri = resolve_repository_uri("s3://bucket/path", config_dir=tmp_path)
        assert uri == "s3://bucket/path"
        
        # File URI
        uri = resolve_repository_uri("file:///tmp/repo", config_dir=tmp_path)
        assert uri == "file:///tmp/repo"
        
        # Absolute path
        uri = resolve_repository_uri("/tmp/repo", config_dir=tmp_path)
        assert uri == "/tmp/repo"
    
    def test_resolve_various_repository_types(self, tmp_path):
        """Test resolving different repository backend types"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                "local": {
                    "uri": "file:///var/backups/local",
                    "location": "file:///var/backups/local",
                    "description": "Local filesystem"
                },
                "s3": {
                    "uri": "s3:s3.amazonaws.com/bucket",
                    "location": "s3:s3.amazonaws.com/bucket",
                    "description": "AWS S3"
                },
                "b2": {
                    "uri": "b2:bucket-name/path",
                    "location": "b2:bucket-name/path",
                    "description": "Backblaze B2"
                },
                "sftp": {
                    "uri": "sftp://user@host:/path",
                    "location": "sftp://user@host:/path",
                    "description": "SFTP server"
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Test each repository type
        assert resolve_repository_uri("local", config_dir=tmp_path) == "file:///var/backups/local"
        assert resolve_repository_uri("s3", config_dir=tmp_path) == "s3:s3.amazonaws.com/bucket"
        assert resolve_repository_uri("b2", config_dir=tmp_path) == "b2:bucket-name/path"
        assert resolve_repository_uri("sftp", config_dir=tmp_path) == "sftp://user@host:/path"
    
    def test_get_repository_info_for_named_repo(self, tmp_path):
        """Test getting repository information for named repository"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                "test-repo": {
                    "uri": "s3:minio.lan/bucket",
                    "location": "s3:minio.lan/bucket",
                    "description": "Test S3 repository"
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        info = get_repository_info("test-repo", config_dir=tmp_path)
        
        assert info['is_named'] is True
        assert info['name'] == "test-repo"
        assert info['uri'] == "s3:minio.lan/bucket"
        assert info['description'] == "Test S3 repository"
        assert info['type'] == "s3"
    
    def test_get_repository_info_for_direct_uri(self):
        """Test getting repository information for direct URI"""
        info = get_repository_info("s3://bucket/path")
        
        assert info['is_named'] is False
        assert info['uri'] == "s3://bucket/path"
        assert 'name' not in info
    
    def test_list_available_repositories(self, tmp_path):
        """Test listing all available repositories"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                "repo1": {
                    "uri": "file:///tmp/repo1",
                    "location": "file:///tmp/repo1",
                    "description": "First repository"
                },
                "repo2": {
                    "uri": "s3:bucket/path",
                    "location": "s3:bucket/path",
                    "description": "Second repository"
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        repos = list_available_repositories(config_dir=tmp_path)
        
        assert len(repos) == 2
        assert "repo1" in repos
        assert "repo2" in repos
        assert repos["repo1"]["uri"] == "file:///tmp/repo1"
        assert repos["repo2"]["uri"] == "s3:bucket/path"
    
    def test_normalize_repository_uri_formats(self):
        """Test URI normalization for different formats"""
        # S3 standard to restic format
        assert normalize_repository_uri("s3://minio.lan/bucket") == "s3:minio.lan/bucket"
        assert normalize_repository_uri("s3://minio.lan/bucket/path") == "s3:minio.lan/bucket/path"
        
        # B2 standard to restic format
        assert normalize_repository_uri("b2://bucket/path") == "b2:bucket/path"
        
        # Already in restic format (no change)
        assert normalize_repository_uri("s3:minio.lan/bucket") == "s3:minio.lan/bucket"
        assert normalize_repository_uri("file:///path/to/repo") == "file:///path/to/repo"
    
    def test_validate_repository_name_or_uri(self):
        """Test repository name/URI validation"""
        # Valid URIs should not raise
        validate_repository_name_or_uri("s3://bucket/path")
        validate_repository_name_or_uri("file:///tmp/repo")
        validate_repository_name_or_uri("s3:bucket/path")
        validate_repository_name_or_uri("my-repo-name")
        
        # Invalid local paths should raise
        with pytest.raises(ValueError, match="must use file:// prefix"):
            validate_repository_name_or_uri("/tmp/repo")
        
        with pytest.raises(ValueError, match="must use file:// prefix"):
            validate_repository_name_or_uri("C:\\backups")


class TestServiceFacadeIntegration:
    """Integration tests for ServiceFacade with service manager"""
    
    def test_service_facade_with_real_service_manager(self, tmp_path):
        """Test ServiceFacade with a real service manager"""
        # Create a mock service manager with realistic structure
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        
        # Add realistic services
        mock_service_manager.repository_service = Mock()
        mock_service_manager.snapshot_service = Mock()
        mock_service_manager.configuration_service = Mock()
        mock_service_manager.repository_factory = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager, config_dir=tmp_path)
        
        # Test service access
        repo_service = facade.get_repository_service()
        assert repo_service is mock_service_manager.repository_service
        
        snapshot_service = facade.get_snapshot_service()
        assert snapshot_service is mock_service_manager.snapshot_service
        
        config_service = facade.get_configuration_service()
        assert config_service is mock_service_manager.configuration_service
    
    def test_service_facade_lazy_initialization(self):
        """Test that ServiceFacade initializes services lazily"""
        facade = ServiceFacade()
        
        # Service manager should not be created yet
        assert facade._service_manager is None
        assert not facade._initialized
        
        # Access a service - should trigger initialization
        with patch('TimeLocker.cli_services.get_cli_service_manager') as mock_get:
            mock_manager = Mock()
            mock_manager.initialize_services = Mock()
            mock_manager.repository_service = Mock()
            mock_get.return_value = mock_manager
            
            facade.get_repository_service()
            
            # Now service manager should be initialized
            assert facade._service_manager is mock_manager
            assert facade._initialized
            mock_manager.initialize_services.assert_called_once()
    
    def test_service_facade_caching_reduces_overhead(self):
        """Test that service caching reduces access overhead"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.repository_service = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        # First access
        start = time.time()
        service1 = facade.get_repository_service()
        first_time = time.time() - start
        
        # Second access (cached)
        start = time.time()
        service2 = facade.get_repository_service()
        second_time = time.time() - start
        
        assert service1 is service2
        # Cached access should be faster
        assert second_time <= first_time
    
    def test_service_facade_health_check_integration(self):
        """Test health check with realistic service manager"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.get_service_health = Mock(return_value={
            'repository': True,
            'snapshot': True,
            'configuration': True
        })
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        health = facade.health_check()
        
        assert health['repository'] is True
        assert health['snapshot'] is True
        assert health['configuration'] is True
    
    def test_service_facade_error_handling(self):
        """Test ServiceFacade error handling with service failures"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.repository_service = None  # Service not available
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        # Should raise ServiceAccessError
        from TimeLocker.utils.service_facade import ServiceAccessError
        with pytest.raises(ServiceAccessError, match="Repository service not available"):
            facade.get_repository_service()
    
    def test_service_facade_shutdown_cleanup(self):
        """Test that shutdown properly cleans up resources"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.shutdown_services = Mock()
        mock_service_manager.repository_service = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        # Access a service to populate cache
        facade.get_repository_service()
        assert len(facade._services_cache) > 0
        
        # Shutdown
        facade.shutdown_services()
        
        # Verify cleanup
        assert len(facade._services_cache) == 0
        assert not facade._initialized
        mock_service_manager.shutdown_services.assert_called_once()


@pytest.mark.performance
class TestServiceLayerPerformanceBenchmarks:
    """Performance benchmarks for service layer components"""
    
    def test_configuration_service_load_performance(self, tmp_path):
        """Benchmark configuration loading performance"""
        config_file = tmp_path / "config.json"
        
        # Create a configuration with many repositories
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                f"repo-{i}": {
                    "uri": f"file:///tmp/repo-{i}",
                    "location": f"file:///tmp/repo-{i}",
                    "description": f"Repository {i}"
                }
                for i in range(100)
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Benchmark loading
        start = time.time()
        config_service = ConfigurationService(config_path=config_file)
        load_time = time.time() - start
        
        # Should load in reasonable time (< 100ms for 100 repos)
        assert load_time < 0.1, f"Configuration loading took {load_time}s, expected < 0.1s"
        
        # Verify all repositories loaded
        repos = config_service.get_repositories()
        assert len(repos) == 100
    
    def test_repository_resolver_performance(self, tmp_path):
        """Benchmark repository resolution performance"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                f"repo-{i}": {
                    "uri": f"s3:bucket-{i}/path",
                    "location": f"s3:bucket-{i}/path",
                    "description": f"Repository {i}"
                }
                for i in range(50)
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Benchmark resolution
        start = time.time()
        for i in range(50):
            uri = resolve_repository_uri(f"repo-{i}", config_dir=tmp_path)
            assert uri == f"s3:bucket-{i}/path"
        resolution_time = time.time() - start
        
        # Should resolve all in reasonable time (< 200ms for 50 resolutions, accounting for config module overhead)
        assert resolution_time < 0.2, f"Repository resolution took {resolution_time}s, expected < 0.2s"
    
    def test_service_facade_overhead(self):
        """Benchmark ServiceFacade overhead"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.repository_service = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        # Benchmark service access overhead
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            facade.get_repository_service()
        total_time = time.time() - start
        
        avg_time_ms = (total_time / iterations) * 1000
        
        # Average overhead should be < 5ms per operation (requirement from design)
        assert avg_time_ms < 5, f"ServiceFacade overhead {avg_time_ms}ms, expected < 5ms"


class TestServiceLayerIntegrationWorkflows:
    """Integration tests for complete workflows using service layer"""
    
    def test_complete_configuration_workflow(self, tmp_path):
        """Test complete workflow: load config, add repo, save, reload"""
        config_file = tmp_path / "config.json"
        
        # Step 1: Create initial configuration
        config_service = ConfigurationService(config_path=config_file)
        
        # Step 2: Add repository
        config_service.add_repository({
            "name": "workflow-test",
            "uri": "s3:bucket/path",
            "location": "s3:bucket/path",
            "description": "Workflow test repository"
        })
        
        # Step 3: Save configuration
        config_service.save_configuration(config_service._config_data, config_file)
        
        # Step 4: Resolve repository using RepositoryResolver
        uri = resolve_repository_uri("workflow-test", config_dir=tmp_path)
        assert uri == "s3:bucket/path"
        
        # Step 5: Get repository info
        info = get_repository_info("workflow-test", config_dir=tmp_path)
        assert info['is_named'] is True
        assert info['name'] == "workflow-test"
        assert info['description'] == "Workflow test repository"
    
    def test_service_facade_with_configuration_service(self, tmp_path):
        """Test ServiceFacade integration with ConfigurationService"""
        config_file = tmp_path / "config.json"
        config_data = {
            "general": {"app_name": "TimeLocker"},
            "repositories": {
                "test": {
                    "uri": "file:///tmp/test",
                    "location": "file:///tmp/test",
                    "description": "Test"
                }
            },
            "backup_targets": {},
            "backup": {},
            "restore": {},
            "security": {}
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Create ConfigurationService
        config_service = ConfigurationService(config_path=config_file)
        
        # Create mock service manager with config service
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.configuration_service = config_service
        
        # Create ServiceFacade
        facade = ServiceFacade(service_manager=mock_service_manager, config_dir=tmp_path)
        
        # Access configuration through facade
        retrieved_config_service = facade.get_configuration_service()
        assert retrieved_config_service is config_service
        
        # Verify we can use it
        repos = retrieved_config_service.get_repositories()
        assert len(repos) == 1
        assert repos[0]['name'] == "test"
