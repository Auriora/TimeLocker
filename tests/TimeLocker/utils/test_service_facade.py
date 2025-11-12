"""
Tests for ServiceFacade

This module tests the ServiceFacade class that provides simplified
service access for CLI commands.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.utils.service_facade import (
    ServiceFacade,
    ServiceFacadeError,
    ServiceInitializationError,
    ServiceAccessError,
    create_service_facade
)


class TestServiceFacade:
    """Test ServiceFacade functionality"""
    
    def test_initialization_without_service_manager(self):
        """Test ServiceFacade can be initialized without service manager"""
        facade = ServiceFacade(config_dir=Path("/tmp/test"))
        
        assert facade._service_manager is None
        assert facade._config_dir == Path("/tmp/test")
        assert not facade._initialized
        assert facade._services_cache == {}
    
    def test_initialization_with_service_manager(self):
        """Test ServiceFacade can be initialized with service manager"""
        mock_service_manager = Mock()
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        assert facade._service_manager is mock_service_manager
        assert not facade._initialized
    
    def test_ensure_service_manager_creates_manager(self):
        """Test _ensure_service_manager creates service manager if needed"""
        facade = ServiceFacade()
        
        with patch('TimeLocker.cli_services.get_cli_service_manager') as mock_get:
            mock_manager = Mock()
            mock_manager.initialize_services = Mock()
            mock_get.return_value = mock_manager
            
            result = facade._ensure_service_manager()
            
            assert result is mock_manager
            assert facade._service_manager is mock_manager
            assert facade._initialized
            mock_manager.initialize_services.assert_called_once()
    
    def test_ensure_service_manager_initialization_error(self):
        """Test _ensure_service_manager raises error on initialization failure"""
        facade = ServiceFacade()
        
        with patch('TimeLocker.cli_services.get_cli_service_manager') as mock_get:
            mock_get.side_effect = Exception("Initialization failed")
            
            with pytest.raises(ServiceInitializationError) as exc_info:
                facade._ensure_service_manager()
            
            assert "Failed to create service manager" in str(exc_info.value)
    
    def test_get_backup_service_success(self):
        """Test get_backup_service returns backup orchestrator"""
        mock_service_manager = Mock()
        mock_backup_service = Mock()
        mock_service_manager.backup_orchestrator = mock_backup_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_backup_service()
        
        assert result is mock_backup_service
        assert facade._services_cache['backup'] is mock_backup_service
    
    def test_get_backup_service_caching(self):
        """Test get_backup_service uses cache on subsequent calls"""
        mock_service_manager = Mock()
        mock_backup_service = Mock()
        mock_service_manager.backup_orchestrator = mock_backup_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        # First call
        result1 = facade.get_backup_service()
        # Second call
        result2 = facade.get_backup_service()
        
        assert result1 is result2
        assert result1 is mock_backup_service
    
    def test_get_backup_service_not_available(self):
        """Test get_backup_service raises error when service not available"""
        mock_service_manager = Mock()
        mock_service_manager.backup_orchestrator = None
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        with pytest.raises(ServiceAccessError) as exc_info:
            facade.get_backup_service()
        
        assert "Backup orchestrator not available" in str(exc_info.value)
    
    def test_get_repository_service_success(self):
        """Test get_repository_service returns repository service"""
        mock_service_manager = Mock()
        mock_repo_service = Mock()
        mock_service_manager.repository_service = mock_repo_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_repository_service()
        
        assert result is mock_repo_service
        assert facade._services_cache['repository'] is mock_repo_service
    
    def test_get_snapshot_service_success(self):
        """Test get_snapshot_service returns snapshot service"""
        mock_service_manager = Mock()
        mock_snapshot_service = Mock()
        mock_service_manager.snapshot_service = mock_snapshot_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_snapshot_service()
        
        assert result is mock_snapshot_service
        assert facade._services_cache['snapshot'] is mock_snapshot_service
    
    def test_get_configuration_service_success(self):
        """Test get_configuration_service returns configuration service"""
        mock_service_manager = Mock()
        mock_config_service = Mock()
        mock_service_manager.configuration_service = mock_config_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_configuration_service()
        
        assert result is mock_config_service
        assert facade._services_cache['configuration'] is mock_config_service
    
    def test_get_configuration_service_fallback(self):
        """Test get_configuration_service falls back to config_module"""
        mock_service_manager = Mock()
        mock_config_module = Mock()
        mock_service_manager.configuration_service = None
        mock_service_manager.config_module = mock_config_module
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_configuration_service()
        
        assert result is mock_config_module
        assert facade._services_cache['configuration'] is mock_config_module
    
    def test_get_repository_factory_success(self):
        """Test get_repository_factory returns repository factory"""
        mock_service_manager = Mock()
        mock_factory = Mock()
        mock_service_manager.repository_factory = mock_factory
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_repository_factory()
        
        assert result is mock_factory
        assert facade._services_cache['repository_factory'] is mock_factory
    
    def test_get_monitoring_service_optional(self):
        """Test get_monitoring_service returns None if not available"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        # No monitoring integration available - remove the method
        mock_service_manager.get_monitoring_integration = Mock(return_value=None)
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_monitoring_service()
        
        assert result is None
    
    def test_get_monitoring_service_success(self):
        """Test get_monitoring_service returns monitoring integration"""
        mock_service_manager = Mock()
        mock_monitoring = Mock()
        mock_service_manager.get_monitoring_integration = Mock(return_value=mock_monitoring)
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_monitoring_service()
        
        assert result is mock_monitoring
        assert facade._services_cache['monitoring'] is mock_monitoring
    
    def test_get_security_service_success(self):
        """Test get_security_service creates security service"""
        facade = ServiceFacade(config_dir=Path("/tmp/test"))
        
        with patch('TimeLocker.security.SecurityService') as mock_security_class:
            with patch('TimeLocker.security.CredentialManager') as mock_cred_class:
                mock_security = Mock()
                mock_security_class.return_value = mock_security
                
                result = facade.get_security_service()
                
                assert result is mock_security
                assert facade._services_cache['security'] is mock_security
                mock_cred_class.assert_called_once_with(config_dir=Path("/tmp/test"))
    
    def test_initialize_services_success(self):
        """Test initialize_services explicitly initializes services"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.initialize_services()
        
        assert result is True
        assert facade._initialized
    
    def test_health_check_with_service_manager_method(self):
        """Test health_check uses service manager's health check"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.get_service_health = Mock(return_value={
            'repository': True,
            'snapshot': True
        })
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.health_check()
        
        assert result == {'repository': True, 'snapshot': True}
        mock_service_manager.get_service_health.assert_called_once()
    
    def test_health_check_fallback(self):
        """Test health_check falls back to checking individual services"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        # No get_service_health method
        delattr(mock_service_manager, 'get_service_health')
        
        mock_repo_service = Mock()
        mock_repo_service.health_check = Mock(return_value=True)
        mock_service_manager.repository_service = mock_repo_service
        
        mock_snapshot_service = Mock()
        mock_snapshot_service.health_check = Mock(return_value=True)
        mock_service_manager.snapshot_service = mock_snapshot_service
        
        mock_service_manager.configuration_service = None
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.health_check()
        
        assert result['repository'] is True
        assert result['snapshot'] is True
        assert result['configuration'] is False
    
    def test_get_service_status_success(self):
        """Test get_service_status returns comprehensive status"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.get_service_status = Mock(return_value={
            'repository': {'initialized': True},
            'snapshot': {'initialized': True}
        })
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_service_status()
        
        assert 'repository' in result
        assert 'snapshot' in result
    
    def test_shutdown_services_success(self):
        """Test shutdown_services cleans up resources"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        mock_service_manager.shutdown_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        facade._initialized = True
        facade._services_cache['test'] = Mock()
        
        facade.shutdown_services()
        
        assert not facade._initialized
        assert facade._services_cache == {}
        mock_service_manager.shutdown_services.assert_called_once()
    
    def test_service_manager_property(self):
        """Test service_manager property returns service manager"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.service_manager
        
        assert result is mock_service_manager
    
    def test_config_dir_property(self):
        """Test config_dir property returns configuration directory"""
        config_dir = Path("/tmp/test")
        facade = ServiceFacade(config_dir=config_dir)
        
        assert facade.config_dir == config_dir
    
    def test_create_service_facade_factory(self):
        """Test create_service_facade factory function"""
        config_dir = Path("/tmp/test")
        mock_service_manager = Mock()
        
        facade = create_service_facade(
            config_dir=config_dir,
            service_manager=mock_service_manager
        )
        
        assert isinstance(facade, ServiceFacade)
        assert facade._config_dir == config_dir
        assert facade._service_manager is mock_service_manager
    
    def test_get_restore_service_with_restore_service_attr(self):
        """Test get_restore_service when service manager has restore_service"""
        mock_service_manager = Mock()
        mock_restore_service = Mock()
        mock_service_manager.restore_service = mock_restore_service
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_restore_service()
        
        assert result is mock_restore_service
        assert facade._services_cache['restore'] is mock_restore_service
    
    def test_get_restore_service_with_recovery_orchestrator(self):
        """Test get_restore_service when service manager has recovery_orchestrator"""
        mock_service_manager = Mock()
        mock_recovery = Mock()
        # No restore_service attribute
        delattr(mock_service_manager, 'restore_service')
        mock_service_manager.recovery_orchestrator = mock_recovery
        mock_service_manager.initialize_services = Mock()
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        result = facade.get_restore_service()
        
        assert result is mock_recovery
        assert facade._services_cache['restore'] is mock_recovery
    
    def test_get_restore_service_fallback(self):
        """Test get_restore_service creates RestoreManager as fallback"""
        mock_service_manager = Mock()
        mock_service_manager.initialize_services = Mock()
        # No restore_service or recovery_orchestrator
        delattr(mock_service_manager, 'restore_service')
        delattr(mock_service_manager, 'recovery_orchestrator')
        
        facade = ServiceFacade(service_manager=mock_service_manager)
        
        with patch('TimeLocker.restore_manager.RestoreManager') as mock_restore_class:
            mock_restore = Mock()
            mock_restore_class.return_value = mock_restore
            
            result = facade.get_restore_service()
            
            assert result is mock_restore
            assert facade._services_cache['restore'] is mock_restore
            mock_restore_class.assert_called_once()
