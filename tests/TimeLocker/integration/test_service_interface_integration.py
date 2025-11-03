"""
Test integration of existing services with ServiceInterface base class.

This test verifies that all updated services properly implement the ServiceInterface
and can be initialized, health-checked, and shutdown correctly.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import tempfile

from src.TimeLocker.interfaces.integration_data_models import ServiceContext
from src.TimeLocker.services.repository_service import RepositoryService
from src.TimeLocker.services.snapshot_service import SnapshotService
from src.TimeLocker.security.security_service import SecurityService
from src.TimeLocker.monitoring.notification_service import NotificationService


class TestServiceInterfaceIntegration:
    """Test suite for ServiceInterface integration with existing services"""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager"""
        config_manager = Mock()
        config_manager.get_config.return_value = {}
        return config_manager

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus"""
        event_bus = Mock()
        return event_bus

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry"""
        service_registry = Mock()
        return service_registry

    @pytest.fixture
    def service_context(self, mock_config_manager, mock_event_bus, mock_service_registry):
        """Create a valid service context"""
        return ServiceContext(
            config_manager=mock_config_manager,
            event_bus=mock_event_bus,
            service_registry=mock_service_registry,
            user_context={"user_id": "test_user"}
        )

    @pytest.fixture
    def repository_service(self):
        """Create a RepositoryService instance"""
        validation_service = Mock()
        performance_module = Mock()
        return RepositoryService(validation_service, performance_module)

    @pytest.fixture
    def snapshot_service(self):
        """Create a SnapshotService instance"""
        validation_service = Mock()
        performance_module = Mock()
        return SnapshotService(validation_service, performance_module)

    @pytest.fixture
    def security_service(self):
        """Create a SecurityService instance"""
        credential_manager = Mock()
        temp_dir = Path(tempfile.mkdtemp())
        temp_dir.mkdir(parents=True, exist_ok=True)
        return SecurityService(credential_manager, config_dir=temp_dir)

    @pytest.fixture
    def notification_service(self):
        """Create a NotificationService instance"""
        temp_dir = Path(tempfile.mkdtemp())
        temp_dir.mkdir(parents=True, exist_ok=True)
        return NotificationService(config_dir=temp_dir)

    def test_repository_service_interface_implementation(self, repository_service, service_context):
        """Test that RepositoryService properly implements ServiceInterface"""
        # Test initialization
        assert repository_service.initialize(service_context) is True
        assert repository_service._initialized is True
        assert repository_service._context is service_context

        # Test health check
        assert repository_service.health_check() is True

        # Test capabilities
        capabilities = repository_service.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert 'repository_check' in capabilities

        # Test service name and version
        assert repository_service.get_service_name() == 'RepositoryService'
        assert repository_service.get_service_version() == '1.0.0'

        # Test shutdown
        repository_service.shutdown()
        assert repository_service._initialized is False
        assert repository_service._context is None

    def test_snapshot_service_interface_implementation(self, snapshot_service, service_context):
        """Test that SnapshotService properly implements ServiceInterface"""
        # Test initialization
        assert snapshot_service.initialize(service_context) is True
        assert snapshot_service._initialized is True
        assert snapshot_service._context is service_context

        # Test health check
        assert snapshot_service.health_check() is True

        # Test capabilities
        capabilities = snapshot_service.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert 'snapshot_details' in capabilities

        # Test service name and version
        assert snapshot_service.get_service_name() == 'SnapshotService'
        assert snapshot_service.get_service_version() == '1.0.0'

        # Test shutdown
        snapshot_service.shutdown()
        assert snapshot_service._initialized is False
        assert snapshot_service._context is None

    def test_security_service_interface_implementation(self, security_service, service_context):
        """Test that SecurityService properly implements ServiceInterface"""
        # Test initialization
        assert security_service.initialize(service_context) is True
        assert security_service._initialized is True
        assert security_service._context is service_context

        # Test health check
        assert security_service.health_check() is True

        # Test capabilities
        capabilities = security_service.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert 'encryption_verification' in capabilities

        # Test service name and version
        assert security_service.get_service_name() == 'SecurityService'
        assert security_service.get_service_version() == '1.0.0'

        # Test shutdown
        security_service.shutdown()
        assert security_service._initialized is False
        assert security_service._context is None

    def test_notification_service_interface_implementation(self, notification_service, service_context):
        """Test that NotificationService properly implements ServiceInterface"""
        # Test initialization
        assert notification_service.initialize(service_context) is True
        assert notification_service._initialized is True
        assert notification_service._context is service_context

        # Test health check
        assert notification_service.health_check() is True

        # Test capabilities
        capabilities = notification_service.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert 'desktop_notifications' in capabilities

        # Test service name and version
        assert notification_service.get_service_name() == 'NotificationService'
        assert notification_service.get_service_version() == '1.0.0'

        # Test shutdown
        notification_service.shutdown()
        assert notification_service._initialized is False
        assert notification_service._context is None

    def test_invalid_context_handling(self, repository_service):
        """Test that services handle invalid context properly"""
        # Test with None context
        assert repository_service.initialize(None) is False
        assert repository_service._initialized is False

    def test_health_check_before_initialization(self, repository_service):
        """Test that health check fails before initialization"""
        assert repository_service.health_check() is False

    def test_context_validation(self, repository_service, service_context):
        """Test context validation functionality"""
        # Valid context should pass validation
        assert repository_service.validate_context(service_context) is True

        # Invalid context should fail validation
        assert repository_service.validate_context(None) is False

    def test_all_services_implement_interface_methods(self, service_context):
        """Test that all services implement required interface methods"""
        services = [
            RepositoryService(Mock(), Mock()),
            SnapshotService(Mock(), Mock()),
            SecurityService(Mock(), config_dir=Path(tempfile.mkdtemp())),
            NotificationService(config_dir=Path(tempfile.mkdtemp()))
        ]

        for service in services:
            # Check that all required methods exist and are callable
            assert hasattr(service, 'initialize')
            assert callable(service.initialize)
            
            assert hasattr(service, 'shutdown')
            assert callable(service.shutdown)
            
            assert hasattr(service, 'health_check')
            assert callable(service.health_check)
            
            assert hasattr(service, 'get_capabilities')
            assert callable(service.get_capabilities)
            
            assert hasattr(service, 'get_service_name')
            assert callable(service.get_service_name)
            
            assert hasattr(service, 'get_service_version')
            assert callable(service.get_service_version)
            
            assert hasattr(service, 'validate_context')
            assert callable(service.validate_context)

            # Test that methods return expected types
            assert isinstance(service.get_service_name(), str)
            assert isinstance(service.get_service_version(), str)
            assert isinstance(service.health_check(), bool)
            assert isinstance(service.get_capabilities(), list)
            assert isinstance(service.validate_context(service_context), bool)

    def test_service_lifecycle_integration(self, repository_service, service_context):
        """Test complete service lifecycle"""
        # Initial state
        assert repository_service._initialized is False
        assert repository_service._context is None
        assert repository_service.health_check() is False

        # Initialize
        assert repository_service.initialize(service_context) is True
        assert repository_service._initialized is True
        assert repository_service._context is service_context
        assert repository_service.health_check() is True

        # Shutdown
        repository_service.shutdown()
        assert repository_service._initialized is False
        assert repository_service._context is None
        # Note: health_check may still return True if dependencies are available