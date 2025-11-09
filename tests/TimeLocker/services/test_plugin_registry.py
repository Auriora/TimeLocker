"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
Unit Tests for Plugin Registry

This module tests the plugin registry system for backup engine discovery,
registration, and management.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from TimeLocker.services.plugin_registry import PluginRegistry, get_plugin_registry
from TimeLocker.interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    EngineCapabilities,
    ValidationResult,
    PluginError,
    EngineNotAvailableError
)


class MockBackupEnginePlugin(BackupEnginePlugin):
    """Mock plugin for testing"""
    
    def __init__(self, name: str = "mock", available: bool = True):
        self._name = name
        self._available = available
        self._engine_type = BackupEngine.RESTIC
    
    @property
    def engine_name(self) -> str:
        return self._name
    
    @property
    def engine_type(self) -> BackupEngine:
        return self._engine_type
    
    @property
    def engine_version(self) -> str:
        return "1.0.0"
    
    def is_available(self) -> bool:
        return self._available
    
    def get_capabilities(self) -> EngineCapabilities:
        return EngineCapabilities(
            supports_encryption=True,
            supports_deduplication=True,
            storage_backends=['local', 's3']
        )
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], warnings=[])
    
    def supports_storage_type(self, storage_type: str) -> bool:
        return storage_type in ['local', 's3']
    
    def get_supported_storage_backends(self) -> List[str]:
        return ['local', 's3']
    
    def create_repository(self, uri: str, password=None, **kwargs):
        return Mock()
    
    def validate_uri(self, uri: str) -> ValidationResult:
        return ValidationResult(is_valid=True, errors=[], warnings=[])


@pytest.fixture
def clean_registry():
    """Create a clean plugin registry for testing"""
    registry = PluginRegistry()
    registry.clear()
    yield registry
    registry.clear()


class TestPluginRegistryInitialization:
    """Test plugin registry initialization and singleton behavior"""
    
    def test_singleton_pattern(self):
        """Test that PluginRegistry follows singleton pattern"""
        registry1 = PluginRegistry()
        registry2 = PluginRegistry()
        assert registry1 is registry2
    
    def test_global_registry_function(self):
        """Test get_plugin_registry returns singleton instance"""
        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()
        assert registry1 is registry2
        assert isinstance(registry1, PluginRegistry)
    
    def test_initialization_state(self, clean_registry):
        """Test registry initializes with empty state"""
        assert clean_registry.get_registered_engines() == []


class TestPluginRegistration:
    """Test plugin registration functionality"""
    
    def test_register_valid_plugin(self, clean_registry):
        """Test registering a valid plugin class"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        registered = clean_registry.get_registered_engines()
        assert BackupEngine.RESTIC in registered
    
    def test_register_invalid_plugin_class(self, clean_registry):
        """Test registering invalid plugin class raises error"""
        class NotAPlugin:
            pass
        
        with pytest.raises(PluginError) as exc_info:
            clean_registry.register_plugin(NotAPlugin)
        assert "must inherit from BackupEnginePlugin" in str(exc_info.value)
    
    def test_register_plugin_override_warning(self, clean_registry, caplog):
        """Test that re-registering a plugin logs warning"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        assert "Overriding existing plugin" in caplog.text
    
    def test_register_multiple_plugins(self, clean_registry):
        """Test registering multiple different plugins"""
        class MockRsyncPlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("rsync")
                self._engine_type = BackupEngine.RSYNC
        
        clean_registry.register_plugin(MockBackupEnginePlugin)
        clean_registry.register_plugin(MockRsyncPlugin)
        
        registered = clean_registry.get_registered_engines()
        assert len(registered) == 2
        assert BackupEngine.RESTIC in registered
        assert BackupEngine.RSYNC in registered


class TestPluginRetrieval:
    """Test plugin instance retrieval"""
    
    def test_get_registered_plugin(self, clean_registry):
        """Test retrieving a registered and available plugin"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        plugin = clean_registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None
        assert plugin.engine_name == "mock"
    
    def test_get_unregistered_plugin(self, clean_registry):
        """Test retrieving unregistered plugin raises error"""
        with pytest.raises(PluginError) as exc_info:
            clean_registry.get_plugin(BackupEngine.RSYNC)
        assert "No plugin registered" in str(exc_info.value)
    
    def test_get_unavailable_plugin(self, clean_registry):
        """Test retrieving unavailable plugin raises error"""
        class UnavailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("unavailable", available=False)
        
        clean_registry.register_plugin(UnavailablePlugin)
        
        with pytest.raises(EngineNotAvailableError) as exc_info:
            clean_registry.get_plugin(BackupEngine.RESTIC)
        assert "not available on this system" in str(exc_info.value)
    
    def test_plugin_instance_caching(self, clean_registry):
        """Test that plugin instances are cached"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        plugin1 = clean_registry.get_plugin(BackupEngine.RESTIC)
        plugin2 = clean_registry.get_plugin(BackupEngine.RESTIC)
        
        assert plugin1 is plugin2


class TestEngineAvailability:
    """Test engine availability checking"""
    
    def test_is_engine_available_true(self, clean_registry):
        """Test checking available engine"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        assert clean_registry.is_engine_available(BackupEngine.RESTIC) is True
    
    def test_is_engine_available_false_unregistered(self, clean_registry):
        """Test checking unregistered engine"""
        assert clean_registry.is_engine_available(BackupEngine.RSYNC) is False
    
    def test_is_engine_available_false_unavailable(self, clean_registry):
        """Test checking unavailable engine"""
        class UnavailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("unavailable", available=False)
        
        clean_registry.register_plugin(UnavailablePlugin)
        
        assert clean_registry.is_engine_available(BackupEngine.RESTIC) is False
    
    def test_get_available_engines(self, clean_registry):
        """Test getting list of available engines"""
        class AvailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("available", available=True)
        
        class UnavailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("unavailable", available=False)
                self._engine_type = BackupEngine.RSYNC
        
        clean_registry.register_plugin(AvailablePlugin)
        clean_registry.register_plugin(UnavailablePlugin)
        
        available = clean_registry.get_available_engines()
        assert BackupEngine.RESTIC in available
        assert BackupEngine.RSYNC not in available
    
    def test_get_registered_engines(self, clean_registry):
        """Test getting all registered engines regardless of availability"""
        class AvailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("available", available=True)
        
        class UnavailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("unavailable", available=False)
                self._engine_type = BackupEngine.RSYNC
        
        clean_registry.register_plugin(AvailablePlugin)
        clean_registry.register_plugin(UnavailablePlugin)
        
        registered = clean_registry.get_registered_engines()
        assert BackupEngine.RESTIC in registered
        assert BackupEngine.RSYNC in registered


class TestEngineCapabilities:
    """Test engine capabilities retrieval"""
    
    def test_get_engine_capabilities(self, clean_registry):
        """Test retrieving engine capabilities"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        capabilities = clean_registry.get_engine_capabilities(BackupEngine.RESTIC)
        assert capabilities.supports_encryption is True
        assert capabilities.supports_deduplication is True
        assert 'local' in capabilities.storage_backends
        assert 's3' in capabilities.storage_backends
    
    def test_get_capabilities_unregistered_engine(self, clean_registry):
        """Test getting capabilities for unregistered engine raises error"""
        with pytest.raises(PluginError):
            clean_registry.get_engine_capabilities(BackupEngine.RSYNC)


class TestStorageBackendSupport:
    """Test storage backend support queries"""
    
    def test_get_engines_supporting_storage(self, clean_registry):
        """Test finding engines that support specific storage type"""
        class S3Plugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("s3-plugin")
            
            def supports_storage_type(self, storage_type: str) -> bool:
                return storage_type == 's3'
            
            def get_supported_storage_backends(self) -> List[str]:
                return ['s3']
        
        class LocalPlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("local-plugin")
                self._engine_type = BackupEngine.RSYNC
            
            def supports_storage_type(self, storage_type: str) -> bool:
                return storage_type == 'local'
            
            def get_supported_storage_backends(self) -> List[str]:
                return ['local']
        
        clean_registry.register_plugin(S3Plugin)
        clean_registry.register_plugin(LocalPlugin)
        
        s3_engines = clean_registry.get_engines_supporting_storage('s3')
        assert BackupEngine.RESTIC in s3_engines
        assert BackupEngine.RSYNC not in s3_engines
        
        local_engines = clean_registry.get_engines_supporting_storage('local')
        assert BackupEngine.RSYNC in local_engines
    
    def test_get_engines_supporting_storage_none_found(self, clean_registry):
        """Test querying for unsupported storage type"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        engines = clean_registry.get_engines_supporting_storage('unsupported')
        assert engines == []


class TestPluginUnregistration:
    """Test plugin unregistration functionality"""
    
    def test_unregister_plugin(self, clean_registry):
        """Test unregistering a plugin"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        assert BackupEngine.RESTIC in clean_registry.get_registered_engines()
        
        result = clean_registry.unregister_plugin(BackupEngine.RESTIC)
        assert result is True
        assert BackupEngine.RESTIC not in clean_registry.get_registered_engines()
    
    def test_unregister_nonexistent_plugin(self, clean_registry):
        """Test unregistering non-existent plugin"""
        result = clean_registry.unregister_plugin(BackupEngine.RSYNC)
        assert result is False
    
    def test_unregister_removes_cached_instance(self, clean_registry):
        """Test that unregistering removes cached plugin instance"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        # Get plugin to cache it
        plugin = clean_registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None
        
        # Unregister
        clean_registry.unregister_plugin(BackupEngine.RESTIC)
        
        # Should raise error now
        with pytest.raises(PluginError):
            clean_registry.get_plugin(BackupEngine.RESTIC)


class TestRegistryClear:
    """Test registry clearing functionality"""
    
    def test_clear_registry(self, clean_registry):
        """Test clearing all plugins from registry"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        assert len(clean_registry.get_registered_engines()) > 0
        
        clean_registry.clear()
        assert len(clean_registry.get_registered_engines()) == 0


class TestPluginInfo:
    """Test plugin information retrieval"""
    
    def test_get_plugin_info(self, clean_registry):
        """Test getting comprehensive plugin information"""
        clean_registry.register_plugin(MockBackupEnginePlugin)
        
        info = clean_registry.get_plugin_info()
        assert 'restic' in info
        
        restic_info = info['restic']
        assert restic_info['name'] == 'mock'
        assert restic_info['version'] == '1.0.0'
        assert restic_info['available'] is True
        assert 'capabilities' in restic_info
        assert restic_info['capabilities']['encryption'] is True
        assert 'local' in restic_info['storage_backends']
    
    def test_get_plugin_info_unavailable_engine(self, clean_registry):
        """Test plugin info for unavailable engine"""
        class UnavailablePlugin(MockBackupEnginePlugin):
            def __init__(self):
                super().__init__("unavailable", available=False)
        
        clean_registry.register_plugin(UnavailablePlugin)
        
        info = clean_registry.get_plugin_info()
        assert 'restic' in info
        assert info['restic']['available'] is False
        assert 'error' in info['restic']
    
    def test_get_plugin_info_empty_registry(self, clean_registry):
        """Test getting plugin info from empty registry"""
        info = clean_registry.get_plugin_info()
        assert info == {}


class TestPluginRegistrationErrors:
    """Test error handling during plugin registration"""
    
    def test_register_plugin_initialization_error(self, clean_registry):
        """Test handling plugin that fails to initialize"""
        class FailingPlugin(BackupEnginePlugin):
            def __init__(self):
                raise RuntimeError("Initialization failed")
            
            @property
            def engine_name(self) -> str:
                return "failing"
            
            @property
            def engine_type(self) -> BackupEngine:
                return BackupEngine.RESTIC
            
            @property
            def engine_version(self) -> str:
                return "1.0.0"
            
            def is_available(self) -> bool:
                return True
            
            def get_capabilities(self) -> EngineCapabilities:
                return EngineCapabilities()
            
            def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
                return ValidationResult(is_valid=True, errors=[], warnings=[])
            
            def supports_storage_type(self, storage_type: str) -> bool:
                return False
            
            def get_supported_storage_backends(self) -> List[str]:
                return []
            
            def create_repository(self, uri: str, password=None, **kwargs):
                return Mock()
            
            def validate_uri(self, uri: str) -> ValidationResult:
                return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        with pytest.raises(PluginError) as exc_info:
            clean_registry.register_plugin(FailingPlugin)
        assert "Failed to register plugin" in str(exc_info.value)
