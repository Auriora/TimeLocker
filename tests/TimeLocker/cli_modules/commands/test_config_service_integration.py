"""
Tests for ConfigService integration in CLI commands.

This test suite verifies that CLI commands properly use ConfigService
instead of direct ConfigurationModule access.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.cli_modules.commands.base import (
    _create_config_service,
    ConfigService,
    CommandBase
)


class TestConfigServiceIntegration:
    """Test ConfigService integration with CLI commands."""
    
    def test_create_config_service_default(self):
        """Test creating ConfigService with default config directory."""
        config_service = _create_config_service()
        
        assert isinstance(config_service, ConfigService)
        assert config_service.config_file is not None
        assert config_service.config_dir is not None
    
    def test_create_config_service_custom_dir(self, tmp_path):
        """Test creating ConfigService with custom config directory."""
        custom_dir = tmp_path / "custom_config"
        custom_dir.mkdir()
        
        config_service = _create_config_service(custom_dir)
        
        assert isinstance(config_service, ConfigService)
        assert config_service.config_dir == custom_dir
    
    def test_command_base_setup_returns_config_service(self):
        """Test that CommandBase.setup returns ConfigService."""
        with patch('TimeLocker.cli_modules.commands.base.setup_logging'):
            with patch('TimeLocker.cli_modules.commands.base._get_service_manager_for_command') as mock_sm:
                mock_sm.return_value = Mock()
                
                service_manager, config_service = CommandBase.setup(verbose=False)
                
                assert service_manager is not None
                assert isinstance(config_service, ConfigService)
    
    def test_command_base_setup_legacy_returns_config_module(self):
        """Test that CommandBase.setup_legacy returns ConfigurationModule."""
        with patch('TimeLocker.cli_modules.commands.base.setup_logging'):
            with patch('TimeLocker.cli_modules.commands.base._get_service_manager_for_command') as mock_sm:
                with patch('TimeLocker.cli_modules.commands.base._create_configuration_module') as mock_cm:
                    mock_sm.return_value = Mock()
                    mock_config_module = Mock()
                    mock_cm.return_value = mock_config_module
                    
                    service_manager, config_module = CommandBase.setup_legacy(verbose=False)
                    
                    assert service_manager is not None
                    assert config_module == mock_config_module
    
    @patch('TimeLocker.cli_modules.commands.base.ConfigService')
    def test_config_service_used_in_commands(self, mock_config_service_class):
        """Test that ConfigService is properly instantiated when creating config service."""
        mock_instance = Mock()
        mock_config_service_class.return_value = mock_instance
        
        result = _create_config_service()
        
        mock_config_service_class.assert_called_once_with(config_dir=None)
        assert result == mock_instance
    
    @patch('TimeLocker.cli_modules.commands.base.ConfigService')
    def test_config_service_with_custom_dir(self, mock_config_service_class, tmp_path):
        """Test that ConfigService receives custom config directory."""
        mock_instance = Mock()
        mock_config_service_class.return_value = mock_instance
        custom_dir = tmp_path / "test_config"
        
        result = _create_config_service(custom_dir)
        
        mock_config_service_class.assert_called_once_with(config_dir=custom_dir)
        assert result == mock_instance


class TestConfigServiceCommandUsage:
    """Test that commands properly use ConfigService methods."""
    
    def test_config_service_get_config(self):
        """Test ConfigService.get_config() method."""
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_config = Mock()
            mock_cm.return_value.get_config.return_value = mock_config
            
            config_service = ConfigService()
            result = config_service.get_config()
            
            assert result == mock_config
    
    def test_config_service_get_repositories(self):
        """Test ConfigService.get_repositories() method."""
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_config = Mock()
            mock_config.repositories = {'repo1': Mock(), 'repo2': Mock()}
            mock_cm.return_value.get_config.return_value = mock_config
            
            config_service = ConfigService()
            result = config_service.get_repositories()
            
            assert len(result) == 2
            assert 'repo1' in result
            assert 'repo2' in result
    
    def test_config_service_get_repository(self):
        """Test ConfigService.get_repository() method."""
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_repo = Mock()
            mock_cm.return_value.get_repository.return_value = mock_repo
            
            config_service = ConfigService()
            result = config_service.get_repository('test-repo')
            
            assert result == mock_repo
            mock_cm.return_value.get_repository.assert_called_once_with('test-repo')
    
    def test_config_service_get_backup_targets(self):
        """Test ConfigService.get_backup_targets() method."""
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_config = Mock()
            mock_config.backup_targets = {'target1': Mock(), 'target2': Mock()}
            mock_cm.return_value.get_config.return_value = mock_config
            
            config_service = ConfigService()
            result = config_service.get_backup_targets()
            
            assert len(result) == 2
            assert 'target1' in result
            assert 'target2' in result
    
    def test_config_service_get_default_repository(self):
        """Test ConfigService.get_default_repository() method."""
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_cm.return_value.get_default_repository.return_value = 'default-repo'
            
            config_service = ConfigService()
            result = config_service.get_default_repository()
            
            assert result == 'default-repo'


class TestConfigServiceErrorHandling:
    """Test ConfigService error handling in commands."""
    
    def test_config_service_handles_configuration_error(self):
        """Test that ConfigService properly handles configuration errors."""
        from TimeLocker.interfaces.exceptions import ConfigurationError
        
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_cm.return_value.get_config.side_effect = Exception("Config error")
            
            config_service = ConfigService()
            
            with pytest.raises(ConfigurationError) as exc_info:
                config_service.get_config()
            
            assert "Failed to get configuration" in str(exc_info.value)
    
    def test_config_service_handles_repository_not_found(self):
        """Test that ConfigService properly handles repository not found errors."""
        from TimeLocker.interfaces.exceptions import RepositoryNotFoundError
        
        with patch('TimeLocker.cli_modules.services.config_service.ConfigurationModule') as mock_cm:
            mock_cm.return_value.get_repository.side_effect = RepositoryNotFoundError("Repository not found")
            
            config_service = ConfigService()
            
            with pytest.raises(RepositoryNotFoundError):
                config_service.get_repository('nonexistent')


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_legacy_setup_still_works(self):
        """Test that legacy setup method still works for non-migrated commands."""
        with patch('TimeLocker.cli_modules.commands.base.setup_logging'):
            with patch('TimeLocker.cli_modules.commands.base._get_service_manager_for_command') as mock_sm:
                with patch('TimeLocker.cli_modules.commands.base._create_configuration_module') as mock_cm:
                    mock_sm.return_value = Mock()
                    mock_config_module = Mock()
                    mock_cm.return_value = mock_config_module
                    
                    service_manager, config_module = CommandBase.setup_legacy()
                    
                    assert service_manager is not None
                    assert config_module == mock_config_module
                    mock_cm.assert_called_once()
    
    def test_both_setup_methods_available(self):
        """Test that both setup and setup_legacy methods are available."""
        assert hasattr(CommandBase, 'setup')
        assert hasattr(CommandBase, 'setup_legacy')
        assert callable(CommandBase.setup)
        assert callable(CommandBase.setup_legacy)
