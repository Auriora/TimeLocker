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
Unit Tests for Plugin Integration with Repository Operations

This module tests the integration between the plugin system and repository
management operations.

Requirements: 4.1, 4.2, 4.4, 4.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Any

from TimeLocker.services.plugin_registry import PluginRegistry
from TimeLocker.interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    EngineCapabilities,
    ValidationResult,
    PluginError,
    EngineNotAvailableError
)


class MockPlugin(BackupEnginePlugin):
    """Mock plugin for integration testing"""
    
    def __init__(self, engine_type: BackupEngine, available: bool = True):
        self._engine_type = engine_type
        self._available = available
        self._create_repo_called = False
        self._validate_config_called = False
    
    @property
    def engine_name(self) -> str:
        return self._engine_type.value
    
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
        self._validate_config_called = True
        if 'invalid' in config:
            return ValidationResult(
                is_valid=False,
                errors=['Invalid configuration'],
                warnings=[]
            )
        return ValidationResult(is_valid=True, errors=[], warnings=[])
    
    def supports_storage_type(self, storage_type: str) -> bool:
        return storage_type in ['local', 's3']
    
    def get_supported_storage_backends(self) -> List[str]:
        return ['local', 's3']
    
    def create_repository(self, uri: str, password=None, **kwargs):
        self._create_repo_called = True
        mock_repo = Mock()
        mock_repo.uri = uri
        mock_repo.password = password
        return mock_repo
    
    def validate_uri(self, uri: str) -> ValidationResult:
        if not uri:
            return ValidationResult(
                is_valid=False,
                errors=['URI cannot be empty'],
                warnings=[]
            )
        return ValidationResult(is_valid=True, errors=[], warnings=[])


@pytest.fixture
def plugin_registry():
    """Create plugin registry with mock plugins"""
    registry = PluginRegistry()
    registry.clear()
    
    # Register mock plugins
    class ResticMockPlugin(MockPlugin):
        def __init__(self):
            super().__init__(BackupEngine.RESTIC)
    
    class RsyncMockPlugin(MockPlugin):
        def __init__(self):
            super().__init__(BackupEngine.RSYNC)
    
    registry.register_plugin(ResticMockPlugin)
    registry.register_plugin(RsyncMockPlugin)
    
    yield registry
    registry.clear()


class TestPluginEngineSelection:
    """Test engine selection through plugin system"""
    
    def test_select_available_engine(self, plugin_registry):
        """Test selecting an available engine"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None
        assert plugin.engine_type == BackupEngine.RESTIC
    
    def test_select_multiple_engines(self, plugin_registry):
        """Test selecting different engines"""
        restic_plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        rsync_plugin = plugin_registry.get_plugin(BackupEngine.RSYNC)
        
        assert restic_plugin.engine_type == BackupEngine.RESTIC
        assert rsync_plugin.engine_type == BackupEngine.RSYNC
        assert restic_plugin is not rsync_plugin
    
    def test_engine_availability_check_before_use(self, plugin_registry):
        """Test checking engine availability before use"""
        is_available = plugin_registry.is_engine_available(BackupEngine.RESTIC)
        assert is_available is True
        
        # Should be able to get plugin after availability check
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None


class TestPluginConfigurationValidation:
    """Test configuration validation through plugin system"""
    
    def test_validate_engine_configuration(self, plugin_registry):
        """Test validating engine-specific configuration"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        config = {'compression': 'auto'}
        result = plugin.validate_configuration(config)
        
        assert result.is_valid is True
        assert plugin._validate_config_called is True
    
    def test_validate_invalid_configuration(self, plugin_registry):
        """Test validation of invalid configuration"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        config = {'invalid': True}
        result = plugin.validate_configuration(config)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_configuration_for_different_engines(self, plugin_registry):
        """Test that different engines validate independently"""
        restic_plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        rsync_plugin = plugin_registry.get_plugin(BackupEngine.RSYNC)
        
        config = {'test': 'value'}
        
        restic_result = restic_plugin.validate_configuration(config)
        rsync_result = rsync_plugin.validate_configuration(config)
        
        assert restic_result.is_valid is True
        assert rsync_result.is_valid is True


class TestPluginRepositoryCreation:
    """Test repository creation through plugin system"""
    
    def test_create_repository_with_plugin(self, plugin_registry):
        """Test creating repository using plugin"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        repo = plugin.create_repository('/path/to/repo', password='test123')
        
        assert repo is not None
        assert repo.uri == '/path/to/repo'
        assert repo.password == 'test123'
        assert plugin._create_repo_called is True
    
    def test_create_repository_different_engines(self, plugin_registry):
        """Test creating repositories with different engines"""
        restic_plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        rsync_plugin = plugin_registry.get_plugin(BackupEngine.RSYNC)
        
        restic_repo = restic_plugin.create_repository('/restic/repo')
        rsync_repo = rsync_plugin.create_repository('/rsync/repo')
        
        assert restic_repo.uri == '/restic/repo'
        assert rsync_repo.uri == '/rsync/repo'
    
    def test_create_repository_with_engine_config(self, plugin_registry):
        """Test creating repository with engine-specific config"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        repo = plugin.create_repository(
            '/path/to/repo',
            password='test123',
            compression='max',
            exclude_caches=True
        )
        
        assert repo is not None


class TestPluginStorageBackendMatching:
    """Test matching storage backends to engines"""
    
    def test_find_engines_for_storage_type(self, plugin_registry):
        """Test finding engines that support storage type"""
        engines = plugin_registry.get_engines_supporting_storage('s3')
        
        assert len(engines) > 0
        assert BackupEngine.RESTIC in engines
        assert BackupEngine.RSYNC in engines
    
    def test_no_engines_for_unsupported_storage(self, plugin_registry):
        """Test finding engines for unsupported storage type"""
        engines = plugin_registry.get_engines_supporting_storage('unsupported')
        
        assert len(engines) == 0
    
    def test_storage_backend_capabilities(self, plugin_registry):
        """Test querying storage backend capabilities"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        assert plugin.supports_storage_type('local') is True
        assert plugin.supports_storage_type('s3') is True
        assert plugin.supports_storage_type('unsupported') is False


class TestPluginCapabilityQuerying:
    """Test querying plugin capabilities for repository operations"""
    
    def test_query_engine_capabilities(self, plugin_registry):
        """Test querying engine capabilities"""
        capabilities = plugin_registry.get_engine_capabilities(BackupEngine.RESTIC)
        
        assert capabilities.supports_encryption is True
        assert capabilities.supports_deduplication is True
        assert len(capabilities.storage_backends) > 0
    
    def test_compare_engine_capabilities(self, plugin_registry):
        """Test comparing capabilities of different engines"""
        restic_caps = plugin_registry.get_engine_capabilities(BackupEngine.RESTIC)
        rsync_caps = plugin_registry.get_engine_capabilities(BackupEngine.RSYNC)
        
        # Both should have capabilities
        assert restic_caps is not None
        assert rsync_caps is not None
        
        # Should have same mock capabilities
        assert restic_caps.supports_encryption == rsync_caps.supports_encryption
    
    def test_capabilities_inform_repository_creation(self, plugin_registry):
        """Test using capabilities to inform repository creation"""
        capabilities = plugin_registry.get_engine_capabilities(BackupEngine.RESTIC)
        
        # Check if engine supports required features
        if capabilities.supports_encryption:
            plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
            repo = plugin.create_repository('/path/to/repo', password='encrypted')
            assert repo is not None


class TestPluginErrorHandling:
    """Test error handling in plugin integration"""
    
    def test_handle_unavailable_engine(self):
        """Test handling unavailable engine"""
        registry = PluginRegistry()
        registry.clear()
        
        class UnavailablePlugin(MockPlugin):
            def __init__(self):
                super().__init__(BackupEngine.RESTIC, available=False)
        
        registry.register_plugin(UnavailablePlugin)
        
        with pytest.raises(EngineNotAvailableError):
            registry.get_plugin(BackupEngine.RESTIC)
    
    def test_handle_unregistered_engine(self, plugin_registry):
        """Test handling unregistered engine"""
        with pytest.raises(PluginError) as exc_info:
            plugin_registry.get_plugin(BackupEngine.RCLONE)
        assert "No plugin registered" in str(exc_info.value)
    
    def test_handle_invalid_uri(self, plugin_registry):
        """Test handling invalid URI in repository creation"""
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        validation = plugin.validate_uri('')
        assert validation.is_valid is False
        assert len(validation.errors) > 0


class TestPluginLifecycleIntegration:
    """Test plugin lifecycle in repository operations"""
    
    def test_plugin_registration_before_use(self):
        """Test that plugins must be registered before use"""
        registry = PluginRegistry()
        registry.clear()
        
        # Should fail before registration
        with pytest.raises(PluginError):
            registry.get_plugin(BackupEngine.RESTIC)
        
        # Register plugin
        class TestPlugin(MockPlugin):
            def __init__(self):
                super().__init__(BackupEngine.RESTIC)
        
        registry.register_plugin(TestPlugin)
        
        # Should succeed after registration
        plugin = registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None
    
    def test_plugin_unregistration_prevents_use(self, plugin_registry):
        """Test that unregistered plugins cannot be used"""
        # Verify plugin is available
        plugin = plugin_registry.get_plugin(BackupEngine.RESTIC)
        assert plugin is not None
        
        # Unregister plugin
        plugin_registry.unregister_plugin(BackupEngine.RESTIC)
        
        # Should fail after unregistration
        with pytest.raises(PluginError):
            plugin_registry.get_plugin(BackupEngine.RESTIC)
    
    def test_plugin_reregistration(self, plugin_registry):
        """Test re-registering a plugin"""
        # Get initial plugin
        plugin1 = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        # Unregister and re-register
        plugin_registry.unregister_plugin(BackupEngine.RESTIC)
        
        class NewPlugin(MockPlugin):
            def __init__(self):
                super().__init__(BackupEngine.RESTIC)
        
        plugin_registry.register_plugin(NewPlugin)
        
        # Get new plugin
        plugin2 = plugin_registry.get_plugin(BackupEngine.RESTIC)
        
        # Should be different instances
        assert plugin1 is not plugin2


class TestPluginMultiEngineScenarios:
    """Test scenarios involving multiple engines"""
    
    def test_list_all_available_engines(self, plugin_registry):
        """Test listing all available engines"""
        available = plugin_registry.get_available_engines()
        
        assert len(available) >= 2
        assert BackupEngine.RESTIC in available
        assert BackupEngine.RSYNC in available
    
    def test_get_plugin_info_all_engines(self, plugin_registry):
        """Test getting info for all registered engines"""
        info = plugin_registry.get_plugin_info()
        
        assert 'restic' in info
        assert 'rsync' in info
        
        assert info['restic']['available'] is True
        assert info['rsync']['available'] is True
    
    def test_engine_selection_based_on_capabilities(self, plugin_registry):
        """Test selecting engine based on required capabilities"""
        # Find engines with encryption support
        engines_with_encryption = []
        for engine_type in plugin_registry.get_available_engines():
            caps = plugin_registry.get_engine_capabilities(engine_type)
            if caps.supports_encryption:
                engines_with_encryption.append(engine_type)
        
        assert len(engines_with_encryption) > 0
        assert BackupEngine.RESTIC in engines_with_encryption
