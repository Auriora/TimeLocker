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
Tests for Service Manager

This module tests the ServiceManager and ServiceRegistry classes that provide
service lifecycle management, discovery, and health monitoring.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from TimeLocker.interfaces import (
    ServiceInterface,
    ServiceContext,
    ServiceInitializationError,
    ServiceShutdownError,
    ServiceDiscoveryError,
    ServiceRegistrationError,
    DependencyResolutionError
)
from TimeLocker.integration import ServiceManager, ServiceRegistry


class MockService(ServiceInterface):
    """Mock service for testing"""
    
    def __init__(self, name: str = "MockService", capabilities: list = None, fail_init: bool = False, 
                 fail_health: bool = False, fail_shutdown: bool = False):
        self.name = name
        self.capabilities = capabilities or ['mock_capability']
        self.fail_init = fail_init
        self.fail_health = fail_health
        self.fail_shutdown = fail_shutdown
        self.initialized = False
        self.shutdown_called = False
        self.init_context = None
    
    def initialize(self, context: ServiceContext) -> bool:
        if self.fail_init:
            raise RuntimeError(f"Mock initialization failure for {self.name}")
        self.init_context = context
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        if self.fail_shutdown:
            raise RuntimeError(f"Mock shutdown failure for {self.name}")
        self.shutdown_called = True
        self.initialized = False
    
    def health_check(self) -> bool:
        if self.fail_health:
            raise RuntimeError(f"Mock health check failure for {self.name}")
        return self.initialized
    
    def get_capabilities(self) -> list:
        return self.capabilities
    
    def get_service_name(self) -> str:
        return self.name


class TestServiceRegistry:
    """Test cases for ServiceRegistry"""
    
    def test_service_registration(self):
        """Test service registration and retrieval"""
        registry = ServiceRegistry()
        service = MockService("TestService")
        
        # Test registration
        registry.register(MockService, service, {'test': 'metadata'})
        
        # Test retrieval
        retrieved = registry.get(MockService)
        assert retrieved is service
        
        # Test metadata
        metadata = registry.get_service_metadata(MockService)
        assert metadata['test'] == 'metadata'
    
    def test_duplicate_registration_error(self):
        """Test that duplicate registration raises error"""
        registry = ServiceRegistry()
        service1 = MockService("Service1")
        service2 = MockService("Service2")
        
        registry.register(MockService, service1)
        
        with pytest.raises(ServiceRegistrationError, match="already registered"):
            registry.register(MockService, service2)
    
    def test_service_unregistration(self):
        """Test service unregistration"""
        registry = ServiceRegistry()
        service = MockService("TestService")
        
        registry.register(MockService, service)
        assert registry.get(MockService) is service
        
        # Test unregistration
        result = registry.unregister(MockService)
        assert result is True
        assert registry.get(MockService) is None
        
        # Test unregistering non-existent service
        result = registry.unregister(MockService)
        assert result is False
    
    def test_get_all_services(self):
        """Test getting all registered services"""
        registry = ServiceRegistry()
        
        class Service1(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        class Service2(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        service1 = Service1()
        service2 = Service2()
        
        registry.register(Service1, service1)
        registry.register(Service2, service2)
        
        all_services = registry.get_all_services()
        assert len(all_services) == 2
        assert all_services[Service1] is service1
        assert all_services[Service2] is service2
    
    def test_get_services_by_capability(self):
        """Test finding services by capability"""
        registry = ServiceRegistry()
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        class Service3(MockService):
            pass
        
        service1 = Service1("Service1", capabilities=['backup', 'restore'])
        service2 = Service2("Service2", capabilities=['backup', 'monitor'])
        service3 = Service3("Service3", capabilities=['restore'])
        
        registry.register(Service1, service1)
        registry.register(Service2, service2)
        registry.register(Service3, service3)
        
        # Test finding by capability
        backup_services = registry.get_services_by_capability('backup')
        assert len(backup_services) == 2
        assert service1 in backup_services
        assert service2 in backup_services
        
        restore_services = registry.get_services_by_capability('restore')
        assert len(restore_services) == 2
        assert service1 in restore_services
        assert service3 in restore_services
        
        monitor_services = registry.get_services_by_capability('monitor')
        assert len(monitor_services) == 1
        assert service2 in monitor_services


class TestServiceManager:
    """Test cases for ServiceManager"""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock service context for testing"""
        return ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock()
        )
    
    def test_service_manager_initialization(self, mock_context):
        """Test ServiceManager initialization"""
        manager = ServiceManager(mock_context)
        assert manager._context is mock_context
        assert isinstance(manager._registry, ServiceRegistry)
        assert len(manager._initialized_services) == 0
    
    def test_invalid_context_initialization(self):
        """Test ServiceManager initialization with invalid context"""
        with pytest.raises(ServiceInitializationError, match="Invalid service context"):
            ServiceManager("invalid_context")
    
    def test_service_registration(self, mock_context):
        """Test service registration"""
        manager = ServiceManager(mock_context)
        service = MockService("TestService")
        
        manager.register_service(MockService, service)
        
        # Verify service is registered but not initialized
        with pytest.raises(ServiceDiscoveryError, match="not initialized"):
            manager.get_service(MockService)
    
    def test_invalid_service_registration(self, mock_context):
        """Test registration of invalid service"""
        manager = ServiceManager(mock_context)
        
        # Test registering non-ServiceInterface
        with pytest.raises(ServiceRegistrationError, match="must implement ServiceInterface"):
            manager.register_service(MockService, "not_a_service")
    
    def test_service_initialization_simple(self, mock_context):
        """Test simple service initialization without dependencies"""
        manager = ServiceManager(mock_context)
        service = MockService("TestService")
        
        manager.register_service(MockService, service)
        result = manager.initialize_services()
        
        assert result is True
        assert service.initialized
        assert service.init_context is not None
        
        # Test service can now be retrieved
        retrieved = manager.get_service(MockService)
        assert retrieved is service
    
    def test_service_initialization_with_dependencies(self, mock_context):
        """Test service initialization with dependencies"""
        manager = ServiceManager(mock_context)
        
        class ServiceA(ServiceInterface):
            def __init__(self):
                self.initialized = False
            def initialize(self, context): 
                self.initialized = True
                return True
            def shutdown(self): 
                self.initialized = False
            def health_check(self): 
                return self.initialized
            def get_capabilities(self): 
                return ['service_a']
        
        class ServiceB(ServiceInterface):
            def __init__(self):
                self.initialized = False
            def initialize(self, context): 
                self.initialized = True
                return True
            def shutdown(self): 
                self.initialized = False
            def health_check(self): 
                return self.initialized
            def get_capabilities(self): 
                return ['service_b']
        
        service_a = ServiceA()
        service_b = ServiceB()
        
        # Register B with dependency on A
        manager.register_service(ServiceA, service_a)
        manager.register_service(ServiceB, service_b, dependencies=[ServiceA])
        
        result = manager.initialize_services()
        
        assert result is True
        assert service_a.initialized
        assert service_b.initialized
        
        # Verify both services can be retrieved
        assert manager.get_service(ServiceA) is service_a
        assert manager.get_service(ServiceB) is service_b
    
    def test_circular_dependency_detection(self, mock_context):
        """Test circular dependency detection"""
        manager = ServiceManager(mock_context)
        
        class ServiceA(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        class ServiceB(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        service_a = ServiceA()
        service_b = ServiceB()
        
        # Create circular dependency: A depends on B, B depends on A
        manager.register_service(ServiceA, service_a, dependencies=[ServiceB])
        manager.register_service(ServiceB, service_b, dependencies=[ServiceA])
        
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
    
    def test_missing_dependency_error(self, mock_context):
        """Test missing dependency error"""
        manager = ServiceManager(mock_context)
        
        class ServiceA(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        class ServiceB(ServiceInterface):
            def initialize(self, context): return True
            def shutdown(self): pass
            def health_check(self): return True
            def get_capabilities(self): return []
        
        service_a = ServiceA()
        
        # Register A with dependency on B, but don't register B
        manager.register_service(ServiceA, service_a, dependencies=[ServiceB])
        
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
    
    def test_service_initialization_failure(self, mock_context):
        """Test handling of service initialization failure"""
        manager = ServiceManager(mock_context)
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        service1 = Service1("Service1")
        service2 = Service2("Service2", fail_init=True)
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
        
        # Verify that service1 was shut down after service2 failed
        assert not service1.initialized
    
    def test_service_shutdown(self, mock_context):
        """Test service shutdown"""
        manager = ServiceManager(mock_context)
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        service1 = Service1("Service1")
        service2 = Service2("Service2")
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        manager.initialize_services()
        assert service1.initialized
        assert service2.initialized
        
        manager.shutdown_services()
        assert service1.shutdown_called
        assert service2.shutdown_called
        assert not service1.initialized
        assert not service2.initialized
    
    def test_service_shutdown_with_errors(self, mock_context):
        """Test service shutdown with errors"""
        manager = ServiceManager(mock_context)
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        service1 = Service1("Service1")
        service2 = Service2("Service2", fail_shutdown=True)
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        manager.initialize_services()
        
        with pytest.raises(ServiceShutdownError):
            manager.shutdown_services()
        
        # Service1 should still be shut down despite service2 failure
        assert service1.shutdown_called
    
    def test_health_check(self, mock_context):
        """Test service health checking"""
        manager = ServiceManager(mock_context)
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        service1 = Service1("Service1")
        service2 = Service2("Service2", fail_health=True)
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        manager.initialize_services()
        
        health_status = manager.health_check()
        
        assert health_status['Service1'] is True
        assert health_status['Service2'] is False
    
    def test_get_service_status(self, mock_context):
        """Test getting comprehensive service status"""
        manager = ServiceManager(mock_context)
        
        service = MockService("TestService", capabilities=['test', 'mock'])
        manager.register_service(MockService, service)
        manager.initialize_services()
        
        status = manager.get_service_status()
        
        assert 'MockService' in status
        service_status = status['MockService']
        
        assert service_status['registered'] is True
        assert service_status['initialized'] is True
        assert service_status['healthy'] is True
        assert service_status['service_name'] == 'TestService'
        assert service_status['capabilities'] == ['test', 'mock']
    
    def test_find_services_by_capability(self, mock_context):
        """Test finding services by capability"""
        manager = ServiceManager(mock_context)
        
        class Service1(MockService):
            pass
        
        class Service2(MockService):
            pass
        
        service1 = Service1("Service1", capabilities=['backup', 'restore'])
        service2 = Service2("Service2", capabilities=['backup', 'monitor'])
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        manager.initialize_services()
        
        backup_services = manager.find_services_by_capability('backup')
        assert len(backup_services) == 2
        assert service1 in backup_services
        assert service2 in backup_services
        
        restore_services = manager.find_services_by_capability('restore')
        assert len(restore_services) == 1
        assert service1 in restore_services
    
    def test_service_discovery_error(self, mock_context):
        """Test service discovery errors"""
        manager = ServiceManager(mock_context)
        
        # Test getting unregistered service
        with pytest.raises(ServiceDiscoveryError, match="not registered"):
            manager.get_service(MockService)
        
        # Test getting registered but uninitialized service
        service = MockService("TestService")
        manager.register_service(MockService, service)
        
        with pytest.raises(ServiceDiscoveryError, match="not initialized"):
            manager.get_service(MockService)
    
    def test_registration_during_shutdown(self, mock_context):
        """Test that registration is prevented during shutdown"""
        manager = ServiceManager(mock_context)
        service = MockService("TestService")
        
        manager.register_service(MockService, service)
        manager.initialize_services()
        
        # Start shutdown process
        manager._is_shutting_down = True
        
        new_service = MockService("NewService")
        with pytest.raises(ServiceRegistrationError, match="during shutdown"):
            manager.register_service(type(new_service), new_service)