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
Tests for DependencyInjector in TimeLocker Integration Architecture

This module tests the dependency injection system including service registration,
dependency resolution, circular dependency detection, and optional dependencies.
"""

import pytest
from typing import List
from unittest.mock import Mock

from TimeLocker.integration.dependency_injector import DependencyInjector, ServiceRegistration, DependencyType
from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.interfaces.integration_data_models import ServiceContext
from TimeLocker.interfaces.integration_exceptions import (
    DependencyResolutionError,
    ServiceRegistrationError,
    ServiceInitializationError
)


# Test service implementations
class MockServiceA(ServiceInterface):
    """Mock service A for testing"""
    
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
        return ['capability_a']
    
    def inject_dependencies(self, dependencies: dict) -> None:
        self.dependencies = dependencies


class MockServiceB(ServiceInterface):
    """Mock service B for testing (depends on A)"""
    
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
        return ['capability_b']
    
    def inject_dependencies(self, dependencies: dict) -> None:
        self.dependencies = dependencies


class MockServiceC(ServiceInterface):
    """Mock service C for testing (depends on B, optionally on A)"""
    
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
        return ['capability_c']
    
    def inject_dependencies(self, dependencies: dict) -> None:
        self.dependencies = dependencies


class FailingService(ServiceInterface):
    """Service that fails during initialization"""
    
    def __init__(self):
        raise RuntimeError("Service initialization failed")
    
    def initialize(self, context: ServiceContext) -> bool:
        return False
    
    def shutdown(self) -> None:
        pass
    
    def health_check(self) -> bool:
        return False
    
    def get_capabilities(self) -> List[str]:
        return []


class TestDependencyInjector:
    """Test cases for DependencyInjector"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.injector = DependencyInjector()
    
    def test_register_service_basic(self):
        """Test basic service registration"""
        self.injector.register_service(MockServiceA)
        
        assert self.injector.is_service_registered(MockServiceA)
        registered_services = self.injector.get_registered_services()
        assert MockServiceA in registered_services
    
    def test_register_service_with_implementation(self):
        """Test service registration with separate implementation"""
        self.injector.register_service(MockServiceA, MockServiceA)
        
        service_info = self.injector.get_service_info(MockServiceA)
        assert service_info['service_type'] == 'MockServiceA'
        assert service_info['implementation_type'] == 'MockServiceA'
    
    def test_register_service_with_dependencies(self):
        """Test service registration with dependencies"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        
        service_info = self.injector.get_service_info(MockServiceB)
        assert 'MockServiceA' in service_info['dependencies']
    
    def test_register_service_with_optional_dependencies(self):
        """Test service registration with optional dependencies"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB)
        self.injector.register_service(
            MockServiceC, 
            dependencies=[MockServiceB],
            optional_dependencies=[MockServiceA]
        )
        
        service_info = self.injector.get_service_info(MockServiceC)
        assert 'MockServiceB' in service_info['dependencies']
        assert 'MockServiceA' in service_info['optional_dependencies']
        assert 'MockServiceA' in service_info['available_optional_dependencies']
    
    def test_register_duplicate_service_fails(self):
        """Test that registering duplicate service fails"""
        self.injector.register_service(MockServiceA)
        
        with pytest.raises(ServiceRegistrationError) as exc_info:
            self.injector.register_service(MockServiceA)
        
        assert "already registered" in str(exc_info.value)
    
    def test_register_instance(self):
        """Test registering a pre-created instance"""
        instance = MockServiceA()
        self.injector.register_instance(MockServiceA, instance)
        
        resolved = self.injector.resolve_service(MockServiceA)
        assert resolved is instance
    
    def test_resolve_service_basic(self):
        """Test basic service resolution"""
        self.injector.register_service(MockServiceA)
        
        service = self.injector.resolve_service(MockServiceA)
        assert isinstance(service, MockServiceA)
    
    def test_resolve_service_with_dependencies(self):
        """Test service resolution with dependencies"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        
        service_b = self.injector.resolve_service(MockServiceB)
        assert isinstance(service_b, MockServiceB)
        assert MockServiceA in service_b.dependencies
        assert isinstance(service_b.dependencies[MockServiceA], MockServiceA)
    
    def test_resolve_service_with_optional_dependencies(self):
        """Test service resolution with optional dependencies"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB)
        self.injector.register_service(
            MockServiceC,
            dependencies=[MockServiceB],
            optional_dependencies=[MockServiceA]
        )
        
        service_c = self.injector.resolve_service(MockServiceC)
        assert isinstance(service_c, MockServiceC)
        assert MockServiceB in service_c.dependencies
        assert MockServiceA in service_c.dependencies  # Optional dependency should be resolved
    
    def test_resolve_service_missing_optional_dependency(self):
        """Test service resolution with missing optional dependency"""
        self.injector.register_service(MockServiceB)
        self.injector.register_service(
            MockServiceC,
            dependencies=[MockServiceB],
            optional_dependencies=[MockServiceA]  # MockServiceA not registered
        )
        
        service_c = self.injector.resolve_service(MockServiceC)
        assert isinstance(service_c, MockServiceC)
        assert MockServiceB in service_c.dependencies
        assert MockServiceA not in service_c.dependencies  # Optional dependency not available
    
    def test_resolve_unregistered_service_fails(self):
        """Test that resolving unregistered service fails"""
        with pytest.raises(DependencyResolutionError) as exc_info:
            self.injector.resolve_service(MockServiceA)
        
        assert "MockServiceA" in str(exc_info.value)
    
    def test_resolve_missing_required_dependency_fails(self):
        """Test that missing required dependency causes failure"""
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            self.injector.resolve_service(MockServiceB)
        
        assert "MockServiceA" in str(exc_info.value)
    
    def test_get_dependency_order_basic(self):
        """Test dependency order calculation"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        self.injector.register_service(MockServiceC, dependencies=[MockServiceB])
        
        order = self.injector.get_dependency_order()
        
        # MockServiceA should come before MockServiceB, which should come before MockServiceC
        a_index = order.index(MockServiceA)
        b_index = order.index(MockServiceB)
        c_index = order.index(MockServiceC)
        
        assert a_index < b_index < c_index
    
    def test_get_dependency_order_with_priority(self):
        """Test dependency order with initialization priority"""
        self.injector.register_service(MockServiceA, initialization_priority=1)
        self.injector.register_service(MockServiceB, initialization_priority=2)
        self.injector.register_service(MockServiceC, initialization_priority=0)
        
        order = self.injector.get_dependency_order()
        
        # Higher priority services should come first (when no dependencies)
        b_index = order.index(MockServiceB)  # Priority 2
        a_index = order.index(MockServiceA)  # Priority 1
        c_index = order.index(MockServiceC)  # Priority 0
        
        assert b_index < a_index < c_index
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        # Create circular dependency: A -> B -> A
        self.injector.register_service(MockServiceA, dependencies=[MockServiceB])
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            self.injector.get_dependency_order()
        
        assert "Circular dependencies" in str(exc_info.value)
    
    def test_circular_dependency_during_resolution(self):
        """Test circular dependency detection during resolution"""
        self.injector.register_service(MockServiceA, dependencies=[MockServiceB])
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        
        with pytest.raises(DependencyResolutionError) as exc_info:
            self.injector.resolve_service(MockServiceA)
        
        assert "Circular dependencies" in str(exc_info.value)
    
    def test_resolve_dependencies_all(self):
        """Test resolving all dependencies at once"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(MockServiceB, dependencies=[MockServiceA])
        self.injector.register_service(MockServiceC, dependencies=[MockServiceB])
        
        resolved = self.injector.resolve_dependencies()
        
        assert len(resolved) == 3
        assert MockServiceA in resolved
        assert MockServiceB in resolved
        assert MockServiceC in resolved
        
        # Check that dependencies are properly injected
        service_c = resolved[MockServiceC]
        assert MockServiceB in service_c.dependencies
    
    def test_singleton_behavior(self):
        """Test singleton service behavior"""
        self.injector.register_service(MockServiceA, is_singleton=True)
        
        service1 = self.injector.resolve_service(MockServiceA)
        service2 = self.injector.resolve_service(MockServiceA)
        
        assert service1 is service2  # Same instance
    
    def test_non_singleton_behavior(self):
        """Test non-singleton service behavior"""
        self.injector.register_service(MockServiceA, is_singleton=False)
        
        service1 = self.injector.resolve_service(MockServiceA)
        service2 = self.injector.resolve_service(MockServiceA)
        
        assert service1 is not service2  # Different instances
    
    def test_factory_function(self):
        """Test service creation with factory function"""
        def create_service():
            service = MockServiceA()
            service.factory_created = True
            return service
        
        self.injector.register_service(
            MockServiceA,
            factory_function=create_service
        )
        
        service = self.injector.resolve_service(MockServiceA)
        assert hasattr(service, 'factory_created')
        assert service.factory_created is True
    
    def test_get_optional_dependencies(self):
        """Test getting optional dependencies for a service"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(
            MockServiceC,
            optional_dependencies=[MockServiceA]
        )
        
        optional_deps = self.injector.get_optional_dependencies(MockServiceC)
        assert MockServiceA in optional_deps
    
    def test_get_available_optional_dependencies(self):
        """Test getting available optional dependencies"""
        self.injector.register_service(MockServiceA)
        self.injector.register_service(
            MockServiceC,
            optional_dependencies=[MockServiceA, MockServiceB]  # MockServiceB not registered
        )
        
        available_deps = self.injector.get_available_optional_dependencies(MockServiceC)
        assert MockServiceA in available_deps
        assert MockServiceB not in available_deps
    
    def test_unregister_service(self):
        """Test service unregistration"""
        self.injector.register_service(MockServiceA)
        assert self.injector.is_service_registered(MockServiceA)
        
        result = self.injector.unregister_service(MockServiceA)
        assert result is True
        assert not self.injector.is_service_registered(MockServiceA)
        
        # Unregistering non-existent service should return False
        result = self.injector.unregister_service(MockServiceB)
        assert result is False
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.injector.register_service(MockServiceA)
        service1 = self.injector.resolve_service(MockServiceA)
        
        self.injector.clear_cache()
        service2 = self.injector.resolve_service(MockServiceA)
        
        # Should be different instances after cache clear
        assert service1 is not service2
    
    def test_service_initialization_failure(self):
        """Test handling of service initialization failure"""
        self.injector.register_service(FailingService)
        
        with pytest.raises(ServiceInitializationError):
            self.injector.resolve_service(FailingService)
    
    def test_get_service_info(self):
        """Test getting detailed service information"""
        self.injector.register_service(
            MockServiceC,
            dependencies=[MockServiceB],
            optional_dependencies=[MockServiceA],
            initialization_priority=5
        )
        
        info = self.injector.get_service_info(MockServiceC)
        
        assert info['service_type'] == 'MockServiceC'
        assert info['implementation_type'] == 'MockServiceC'
        assert info['is_singleton'] is True
        assert info['has_instance'] is False
        assert 'MockServiceB' in info['dependencies']
        assert 'MockServiceA' in info['optional_dependencies']
        assert info['initialization_priority'] == 5
        assert info['has_factory'] is False
    
    def test_empty_injector(self):
        """Test behavior with empty injector"""
        order = self.injector.get_dependency_order()
        assert order == []
        
        resolved = self.injector.resolve_dependencies()
        assert resolved == {}
        
        services = self.injector.get_registered_services()
        assert services == []