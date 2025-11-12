"""
Tests for ConfigService

This module tests the centralized configuration service for CLI commands.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from TimeLocker.cli_modules.services.config_service import ConfigService
from TimeLocker.config.configuration_schema import TimeLockerConfig, RepositoryConfig, BackupTargetConfig
from TimeLocker.interfaces.exceptions import ConfigurationError, RepositoryNotFoundError


@pytest.fixture
def mock_config_module():
    """Create a mock ConfigurationModule."""
    with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock:
        module = Mock()
        mock.return_value = module
        
        # Setup default mock behavior
        module.config_file = Path("/test/config.json")
        module.config_dir = Path("/test")
        
        yield module


@pytest.fixture
def config_service(mock_config_module):
    """Create a ConfigService instance with mocked dependencies."""
    return ConfigService()


@pytest.fixture
def sample_config():
    """Create a sample TimeLockerConfig for testing."""
    config = Mock(spec=TimeLockerConfig)
    config.to_dict = Mock(return_value={'general': {}, 'repositories': {}, 'backup_targets': {}})
    config.repositories = {}
    config.backup_targets = {}
    config.general = Mock()
    config.general.default_repository = None
    return config


@pytest.fixture
def sample_repository():
    """Create a sample RepositoryConfig for testing."""
    repo = Mock(spec=RepositoryConfig)
    repo.name = "test-repo"
    repo.location = "file:///test/repo"
    repo.description = "Test repository"
    return repo


class TestConfigServiceInitialization:
    """Test ConfigService initialization."""
    
    def test_init_default(self, mock_config_module):
        """Test initialization with default config directory."""
        service = ConfigService()
        
        assert service is not None
        assert service._operation_count == 0
        assert service._cache_hits == 0
        assert service._cache_misses == 0
    
    def test_init_custom_config_dir(self, mock_config_module):
        """Test initialization with custom config directory."""
        custom_dir = Path("/custom/config")
        service = ConfigService(config_dir=custom_dir)
        
        assert service is not None


class TestConfigServiceCoreAccess:
    """Test core configuration access methods."""
    
    def test_get_config_success(self, config_service, mock_config_module, sample_config):
        """Test successful configuration retrieval."""
        mock_config_module.get_config.return_value = sample_config
        
        result = config_service.get_config()
        
        assert result == sample_config
        assert config_service._operation_count == 1
        assert config_service._cache_hits == 1
        mock_config_module.get_config.assert_called_once()
    
    def test_get_config_error(self, config_service, mock_config_module):
        """Test configuration retrieval with error."""
        mock_config_module.get_config.side_effect = Exception("Config error")
        
        with pytest.raises(ConfigurationError, match="Failed to get configuration"):
            config_service.get_config()
        
        assert config_service._cache_misses == 1
    
    def test_get_config_dict(self, config_service, mock_config_module, sample_config):
        """Test getting configuration as dictionary."""
        mock_config_module.get_config.return_value = sample_config
        
        result = config_service.get_config_dict()
        
        assert isinstance(result, dict)
        sample_config.to_dict.assert_called_once()
    
    def test_save_config_success(self, config_service, mock_config_module, sample_config):
        """Test successful configuration save."""
        config_service.save_config(sample_config)
        
        mock_config_module.save_config.assert_called_once_with(sample_config)
    
    def test_save_config_none(self, config_service, mock_config_module):
        """Test saving current configuration (None parameter)."""
        config_service.save_config(None)
        
        mock_config_module.save_config.assert_called_once_with(None)
    
    def test_save_config_error(self, config_service, mock_config_module, sample_config):
        """Test configuration save with error."""
        mock_config_module.save_config.side_effect = Exception("Save error")
        
        with pytest.raises(ConfigurationError, match="Failed to save configuration"):
            config_service.save_config(sample_config)
    
    def test_reload_config(self, config_service, mock_config_module):
        """Test configuration reload."""
        config_service.reload_config()
        
        mock_config_module._load_configuration.assert_called_once()
    
    def test_reload_config_error(self, config_service, mock_config_module):
        """Test configuration reload with error."""
        mock_config_module._load_configuration.side_effect = Exception("Reload error")
        
        with pytest.raises(ConfigurationError, match="Failed to reload configuration"):
            config_service.reload_config()


class TestConfigServiceSections:
    """Test configuration section access methods."""
    
    def test_get_section_success(self, config_service, mock_config_module):
        """Test successful section retrieval."""
        section_data = {'key': 'value'}
        mock_config_module.get_section.return_value = section_data
        
        result = config_service.get_section('general')
        
        assert result == section_data
        mock_config_module.get_section.assert_called_once_with('general')
    
    def test_get_section_error(self, config_service, mock_config_module):
        """Test section retrieval with error."""
        mock_config_module.get_section.side_effect = Exception("Section error")
        
        with pytest.raises(ConfigurationError, match="Failed to get section"):
            config_service.get_section('invalid')
    
    def test_update_section_success(self, config_service, mock_config_module):
        """Test successful section update."""
        section_data = {'key': 'new_value'}
        
        config_service.update_section('general', section_data)
        
        mock_config_module.update_section.assert_called_once_with('general', section_data)
    
    def test_update_section_error(self, config_service, mock_config_module):
        """Test section update with error."""
        mock_config_module.update_section.side_effect = Exception("Update error")
        
        with pytest.raises(ConfigurationError, match="Failed to update section"):
            config_service.update_section('general', {})


class TestConfigServiceRepositories:
    """Test repository management methods."""
    
    def test_get_repositories(self, config_service, mock_config_module, sample_config):
        """Test getting all repositories."""
        sample_config.repositories = {'repo1': Mock(), 'repo2': Mock()}
        mock_config_module.get_config.return_value = sample_config
        
        result = config_service.get_repositories()
        
        assert len(result) == 2
        assert 'repo1' in result
        assert 'repo2' in result
    
    def test_get_repository_success(self, config_service, mock_config_module, sample_repository):
        """Test successful repository retrieval."""
        mock_config_module.get_repository.return_value = sample_repository
        
        result = config_service.get_repository('test-repo')
        
        assert result == sample_repository
        mock_config_module.get_repository.assert_called_once_with('test-repo')
    
    def test_get_repository_not_found(self, config_service, mock_config_module):
        """Test repository retrieval when not found."""
        mock_config_module.get_repository.side_effect = RepositoryNotFoundError("Not found")
        
        with pytest.raises(RepositoryNotFoundError):
            config_service.get_repository('nonexistent')
    
    def test_get_repository_error(self, config_service, mock_config_module):
        """Test repository retrieval with general error."""
        mock_config_module.get_repository.side_effect = Exception("General error")
        
        with pytest.raises(ConfigurationError, match="Failed to get repository"):
            config_service.get_repository('test-repo')
    
    def test_add_repository_success(self, config_service, mock_config_module, sample_repository):
        """Test successful repository addition."""
        config_service.add_repository(sample_repository)
        
        mock_config_module.add_repository.assert_called_once_with(sample_repository)
    
    def test_add_repository_error(self, config_service, mock_config_module, sample_repository):
        """Test repository addition with error."""
        mock_config_module.add_repository.side_effect = Exception("Add error")
        
        with pytest.raises(ConfigurationError, match="Failed to add repository"):
            config_service.add_repository(sample_repository)
    
    def test_update_repository_success(self, config_service, mock_config_module, sample_repository):
        """Test successful repository update."""
        config_service.update_repository('test-repo', sample_repository)
        
        mock_config_module.update_repository.assert_called_once_with('test-repo', sample_repository)
    
    def test_update_repository_not_found(self, config_service, mock_config_module, sample_repository):
        """Test repository update when not found."""
        mock_config_module.update_repository.side_effect = RepositoryNotFoundError("Not found")
        
        with pytest.raises(RepositoryNotFoundError):
            config_service.update_repository('nonexistent', sample_repository)
    
    def test_remove_repository_success(self, config_service, mock_config_module):
        """Test successful repository removal."""
        config_service.remove_repository('test-repo')
        
        mock_config_module.remove_repository.assert_called_once_with('test-repo')
    
    def test_remove_repository_not_found(self, config_service, mock_config_module):
        """Test repository removal when not found."""
        mock_config_module.remove_repository.side_effect = RepositoryNotFoundError("Not found")
        
        with pytest.raises(RepositoryNotFoundError):
            config_service.remove_repository('nonexistent')
    
    def test_get_default_repository(self, config_service, mock_config_module):
        """Test getting default repository."""
        mock_config_module.get_default_repository.return_value = 'default-repo'
        
        result = config_service.get_default_repository()
        
        assert result == 'default-repo'
    
    def test_set_default_repository_success(self, config_service, mock_config_module):
        """Test setting default repository."""
        config_service.set_default_repository('test-repo')
        
        mock_config_module.set_default_repository.assert_called_once_with('test-repo')
    
    def test_set_default_repository_not_found(self, config_service, mock_config_module):
        """Test setting default repository when not found."""
        mock_config_module.set_default_repository.side_effect = RepositoryNotFoundError("Not found")
        
        with pytest.raises(RepositoryNotFoundError):
            config_service.set_default_repository('nonexistent')


class TestConfigServiceBackupTargets:
    """Test backup target management methods."""
    
    def test_get_backup_targets(self, config_service, mock_config_module, sample_config):
        """Test getting all backup targets."""
        sample_config.backup_targets = {'target1': Mock(), 'target2': Mock()}
        mock_config_module.get_config.return_value = sample_config
        
        result = config_service.get_backup_targets()
        
        assert len(result) == 2
        assert 'target1' in result
        assert 'target2' in result
    
    def test_get_backup_target_success(self, config_service, mock_config_module):
        """Test successful backup target retrieval."""
        target = Mock(spec=BackupTargetConfig)
        mock_config_module.get_backup_target.return_value = target
        
        result = config_service.get_backup_target('test-target')
        
        assert result == target
        mock_config_module.get_backup_target.assert_called_once_with('test-target')
    
    def test_get_backup_target_error(self, config_service, mock_config_module):
        """Test backup target retrieval with error."""
        mock_config_module.get_backup_target.side_effect = Exception("Target error")
        
        with pytest.raises(ConfigurationError, match="Failed to get backup target"):
            config_service.get_backup_target('test-target')
    
    def test_add_backup_target_success(self, config_service, mock_config_module):
        """Test successful backup target addition."""
        target = Mock(spec=BackupTargetConfig)
        target.name = 'test-target'
        
        config_service.add_backup_target(target)
        
        mock_config_module.add_backup_target.assert_called_once_with(target)
    
    def test_remove_backup_target_success(self, config_service, mock_config_module):
        """Test successful backup target removal."""
        mock_config_module.remove_backup_target.return_value = True
        
        result = config_service.remove_backup_target('test-target')
        
        assert result is True
        mock_config_module.remove_backup_target.assert_called_once_with('test-target')


class TestConfigServiceValidation:
    """Test configuration validation methods."""
    
    def test_validate_config_success(self, config_service, mock_config_module, sample_config):
        """Test successful configuration validation."""
        mock_config_module.get_config.return_value = sample_config
        
        result = config_service.validate_config()
        
        assert result is True
    
    def test_validate_config_error(self, config_service, mock_config_module):
        """Test configuration validation with error."""
        mock_config_module.get_config.side_effect = Exception("Validation error")
        
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            config_service.validate_config()


class TestConfigServiceChangeNotification:
    """Test configuration change notification system."""
    
    def test_register_change_listener(self, config_service):
        """Test registering a change listener."""
        listener = Mock()
        
        config_service.register_change_listener(listener)
        
        assert listener in config_service._change_listeners
    
    def test_register_duplicate_listener(self, config_service):
        """Test registering the same listener twice."""
        listener = Mock()
        
        config_service.register_change_listener(listener)
        config_service.register_change_listener(listener)
        
        # Should only be registered once
        assert config_service._change_listeners.count(listener) == 1
    
    def test_unregister_change_listener(self, config_service):
        """Test unregistering a change listener."""
        listener = Mock()
        config_service.register_change_listener(listener)
        
        config_service.unregister_change_listener(listener)
        
        assert listener not in config_service._change_listeners
    
    def test_notify_change_listeners(self, config_service, mock_config_module, sample_config):
        """Test notifying change listeners."""
        listener1 = Mock()
        listener2 = Mock()
        
        config_service.register_change_listener(listener1)
        config_service.register_change_listener(listener2)
        
        config_service.save_config(sample_config)
        
        listener1.assert_called_once_with(sample_config)
        listener2.assert_called_once_with(sample_config)
    
    def test_notify_change_listeners_with_error(self, config_service, mock_config_module, sample_config):
        """Test that listener errors don't break notification."""
        listener1 = Mock(side_effect=Exception("Listener error"))
        listener2 = Mock()
        
        config_service.register_change_listener(listener1)
        config_service.register_change_listener(listener2)
        
        # Should not raise exception
        config_service.save_config(sample_config)
        
        # Second listener should still be called
        listener2.assert_called_once_with(sample_config)


class TestConfigServiceUtilities:
    """Test utility methods."""
    
    def test_config_file_property(self, config_service, mock_config_module):
        """Test config_file property."""
        result = config_service.config_file
        
        assert result == mock_config_module.config_file
    
    def test_config_dir_property(self, config_service, mock_config_module):
        """Test config_dir property."""
        result = config_service.config_dir
        
        assert result == mock_config_module.config_dir
    
    def test_get_performance_stats_no_operations(self, config_service):
        """Test performance stats with no operations."""
        stats = config_service.get_performance_stats()
        
        assert stats['total_operations'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['cache_hit_rate'] == '0.0%'
    
    def test_get_performance_stats_with_operations(self, config_service, mock_config_module, sample_config):
        """Test performance stats with operations."""
        mock_config_module.get_config.return_value = sample_config
        
        # Perform some operations
        config_service.get_config()
        config_service.get_config()
        
        stats = config_service.get_performance_stats()
        
        assert stats['total_operations'] == 2
        assert stats['cache_hits'] == 2
        assert stats['cache_hit_rate'] == '100.0%'


class TestConfigServiceIntegration:
    """Integration tests for ConfigService."""
    
    def test_full_repository_workflow(self, config_service, mock_config_module, sample_config, sample_repository):
        """Test complete repository management workflow."""
        # Setup
        sample_config.repositories = {}
        mock_config_module.get_config.return_value = sample_config
        
        # Add repository
        config_service.add_repository(sample_repository)
        
        # Get repository
        mock_config_module.get_repository.return_value = sample_repository
        repo = config_service.get_repository('test-repo')
        assert repo == sample_repository
        
        # Set as default
        config_service.set_default_repository('test-repo')
        
        # Get default
        mock_config_module.get_default_repository.return_value = 'test-repo'
        default = config_service.get_default_repository()
        assert default == 'test-repo'
        
        # Remove repository
        config_service.remove_repository('test-repo')
    
    def test_configuration_change_workflow(self, config_service, mock_config_module, sample_config):
        """Test configuration change notification workflow."""
        listener_called = []
        
        def listener(config):
            listener_called.append(config)
        
        # Register listener
        config_service.register_change_listener(listener)
        
        # Save config (should trigger listener)
        config_service.save_config(sample_config)
        
        # Verify listener was called
        assert len(listener_called) == 1
        assert listener_called[0] == sample_config
        
        # Unregister and save again
        config_service.unregister_change_listener(listener)
        config_service.save_config(sample_config)
        
        # Listener should not be called again
        assert len(listener_called) == 1
