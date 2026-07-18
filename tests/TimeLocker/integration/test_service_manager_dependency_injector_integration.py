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
Integration tests for ServiceManager and DependencyInjector working together

This module tests the integration between ServiceManager and DependencyInjector
to ensure they work together properly for service orchestration.
"""

import pytest
from typing import List
from unittest.mock import Mock

from TimeLocker.integration.service_manager import ServiceManager
from TimeLocker.integration.dependency_injector import DependencyInjector
from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.interfaces.integration_data_models import ServiceContext
from TimeLocker.interfaces.integration_exceptions import ServiceRegistrationError


# Test service implementations
class TestServiceA(ServiceInterface):
    """Test service A"""
    
    def __init__(self):
        self.initialized = False
        self.dependencies = {}
    
    def initialize(self, context: ServiceContext) -> bool:
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> List[str]:
        return ['test_capability_a']
    
    def inject_dependencies(self, dependencies: dict) -> None:
        self.dependencies = dependencies


class TestServiceB(ServiceInterface):
    """Test service B that depends on A"""
    
    def __init__(self):
        self.initialized = False
        self.dependencies = {}
    
    def initialize(self, context: ServiceContext) -> bool:
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> List[str]:
        return ['test_capability_b']
    
    def inject_dependencies(self, dependencies: dict) -> None:
        self.dependencies = dependencies


class TestServiceManagerDependencyInjectorIntegration:
    """Test integration between ServiceManager and DependencyInjector"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create mock context
        self.mock_config_manager = Mock()
        self.mock_event_bus = Mock()
        self.mock_service_registry = Mock()
        
        self.context = ServiceContext(
            config_manager=self.mock_config_manager,
            event_bus=self.mock_event_bus,
            service_registry=self.mock_service_registry
        )
        
        self.service_manager = ServiceManager(self.context)
        self.dependency_injector = DependencyInjector()
    
    def test_set_dependency_injector(self):
        """Test setting dependency injector on service manager"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        injector = self.service_manager.get_dependency_injector()
        assert injector is self.dependency_injector
    
    def test_register_service_with_injector_basic(self):
        """Test basic service registration with dependency injector"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        self.service_manager.register_service_with_injector(TestServiceA)
        
        # Verify service is registered in both systems
        assert self.dependency_injector.is_service_registered(TestServiceA)
        
        # Initialize services to make them available
        self.service_manager.initialize_services()
        
        # Verify service can be retrieved from ServiceManager
        service = self.service_manager.get_service(TestServiceA)
        assert isinstance(service, TestServiceA)
    
    def test_register_service_with_injector_dependencies(self):
        """Test service registration with dependencies using injector"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        # Register services with dependencies
        self.service_manager.register_service_with_injector(TestServiceA)
        self.service_manager.register_service_with_injector(
            TestServiceB, 
            dependencies=[TestServiceA]
        )
        
        # Verify both services are registered
        assert self.dependency_injector.is_service_registered(TestServiceA)
        assert self.dependency_injector.is_service_registered(TestServiceB)
        
        # Initialize services to make them available
        self.service_manager.initialize_services()
        
        # Verify dependency injection worked
        service_b = self.service_manager.get_service(TestServiceB)
        assert isinstance(service_b, TestServiceB)
        assert TestServiceA in service_b.dependencies
        assert isinstance(service_b.dependencies[TestServiceA], TestServiceA)
    
    def test_register_service_with_injector_optional_dependencies(self):
        """Test service registration with optional dependencies"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        # Register services with optional dependencies
        self.service_manager.register_service_with_injector(TestServiceA)
        self.service_manager.register_service_with_injector(
            TestServiceB,
            optional_dependencies=[TestServiceA]
        )
        
        # Initialize services to make them available
        self.service_manager.initialize_services()
        
        # Verify optional dependency was resolved
        service_b = self.service_manager.get_service(TestServiceB)
        assert TestServiceA in service_b.dependencies
    
    def test_register_service_without_injector_fails(self):
        """Test that registering with injector fails if no injector is set"""
        with pytest.raises(ServiceRegistrationError) as exc_info:
            self.service_manager.register_service_with_injector(TestServiceA)
        
        assert "No dependency injector configured" in str(exc_info.value)
    
    def test_initialize_services_with_injector(self):
        """Test service initialization using dependency injector"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        # Register services
        self.service_manager.register_service_with_injector(TestServiceA)
        self.service_manager.register_service_with_injector(
            TestServiceB,
            dependencies=[TestServiceA]
        )
        
        # Initialize services using injector
        result = self.service_manager.initialize_services_with_injector()
        assert result is True
        
        # Verify services are initialized
        service_a = self.service_manager.get_service(TestServiceA)
        service_b = self.service_manager.get_service(TestServiceB)
        
        assert service_a.initialized
        assert service_b.initialized
        
        # Verify health checks pass
        health_status = self.service_manager.health_check()
        assert health_status[TestServiceA.__name__] is True
        assert health_status[TestServiceB.__name__] is True
    
    def test_initialize_services_without_injector_fails(self):
        """Test that initializing with injector fails if no injector is set"""
        with pytest.raises(Exception) as exc_info:
            self.service_manager.initialize_services_with_injector()
        
        assert "No dependency injector configured" in str(exc_info.value)
    
    def test_service_manager_and_injector_consistency(self):
        """Test that ServiceManager and DependencyInjector stay consistent"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        # Register service through ServiceManager with injector
        self.service_manager.register_service_with_injector(TestServiceA)
        
        # Initialize services to make them available
        self.service_manager.initialize_services()
        
        # Verify service is available through both systems
        sm_service = self.service_manager.get_service(TestServiceA)
        di_service = self.dependency_injector.resolve_service(TestServiceA)
        
        # Should be the same instance (singleton behavior)
        assert sm_service is di_service
    
    def test_dependency_order_respected_in_initialization(self):
        """Test that dependency order is respected during initialization"""
        self.service_manager.set_dependency_injector(self.dependency_injector)
        
        # Register services in reverse dependency order
        # First register TestServiceA (dependency)
        self.service_manager.register_service_with_injector(TestServiceA)
        # Then register TestServiceB (dependent)
        self.service_manager.register_service_with_injector(
            TestServiceB,
            dependencies=[TestServiceA]
        )
        
        # Initialize - should work despite registration order
        result = self.service_manager.initialize_services_with_injector()
        assert result is True
        
        # Verify both services are properly initialized
        service_a = self.service_manager.get_service(TestServiceA)
        service_b = self.service_manager.get_service(TestServiceB)
        
        assert service_a.initialized
        assert service_b.initialized
        assert TestServiceA in service_b.dependencies