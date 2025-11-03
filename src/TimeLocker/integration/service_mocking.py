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
Service Mocking Capabilities for Integration Testing

This module provides service mocking capabilities for testing individual components
in isolation, supporting requirement 9.1 of the integration architecture.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Optional, List, Callable, Union
from unittest.mock import Mock, MagicMock
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import inspect

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import ServiceMockingError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


@dataclass
class MockBehavior:
    """
    Configuration for mock service behavior.
    
    This class defines how a mock service should behave during testing,
    including return values, exceptions, and call tracking.
    """
    
    # Method return values
    return_values: Dict[str, Any] = field(default_factory=dict)
    
    # Method exceptions to raise
    exceptions: Dict[str, Exception] = field(default_factory=dict)
    
    # Method call delays (in seconds)
    delays: Dict[str, float] = field(default_factory=dict)
    
    # Call count limits (method will fail after N calls)
    call_limits: Dict[str, int] = field(default_factory=dict)
    
    # Side effects (functions to call when method is invoked)
    side_effects: Dict[str, Callable] = field(default_factory=dict)
    
    # Whether to track method calls
    track_calls: bool = True
    
    # Whether to validate method arguments
    validate_arguments: bool = True


@dataclass
class MockCallRecord:
    """
    Record of a mock service method call.
    
    This class tracks information about calls made to mock services
    for verification and debugging purposes.
    """
    
    method_name: str
    args: tuple
    kwargs: dict
    timestamp: datetime
    return_value: Any = None
    exception: Optional[Exception] = None
    duration_seconds: float = 0.0


class MockServiceInterface(ServiceInterface):
    """
    Base class for mock service implementations.
    
    This class provides a foundation for creating mock services that
    implement the ServiceInterface contract while providing configurable
    behavior for testing scenarios.
    """
    
    def __init__(self, 
                 service_name: str = "MockService",
                 capabilities: List[str] = None,
                 behavior: MockBehavior = None):
        """
        Initialize mock service.
        
        Args:
            service_name: Name of the mock service
            capabilities: List of capabilities the service provides
            behavior: Mock behavior configuration
        """
        self.service_name = service_name
        self.capabilities = capabilities or []
        self.behavior = behavior or MockBehavior()
        
        # Call tracking
        self.call_records: List[MockCallRecord] = []
        self.call_counts: Dict[str, int] = {}
        
        # Service state
        self.initialized = False
        self.shutdown_called = False
        self.init_context: Optional[ServiceContext] = None
        
        logger.debug(f"Created mock service: {service_name}")
    
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the mock service.
        
        Args:
            context: Service context for initialization
            
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            Exception: If behavior is configured to raise exception
        """
        return self._execute_method('initialize', context)
    
    def shutdown(self) -> None:
        """
        Shutdown the mock service.
        
        Raises:
            Exception: If behavior is configured to raise exception
        """
        self._execute_method('shutdown')
        self.shutdown_called = True
    
    def health_check(self) -> bool:
        """
        Perform health check on mock service.
        
        Returns:
            Health status based on mock behavior
            
        Raises:
            Exception: If behavior is configured to raise exception
        """
        return self._execute_method('health_check')
    
    def get_capabilities(self) -> List[str]:
        """
        Get mock service capabilities.
        
        Returns:
            List of capabilities
        """
        return self.capabilities
    
    def get_service_name(self) -> str:
        """
        Get mock service name.
        
        Returns:
            Service name
        """
        return self.service_name
    
    def _execute_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a method with mock behavior applied.
        
        Args:
            method_name: Name of the method being called
            *args: Method arguments
            **kwargs: Method keyword arguments
            
        Returns:
            Method return value based on mock behavior
            
        Raises:
            Exception: If behavior is configured to raise exception
        """
        import time
        
        start_time = time.time()
        
        # Track call count
        self.call_counts[method_name] = self.call_counts.get(method_name, 0) + 1
        
        # Check call limits
        if method_name in self.behavior.call_limits:
            if self.call_counts[method_name] > self.behavior.call_limits[method_name]:
                exception = RuntimeError(f"Call limit exceeded for {method_name}")
                self._record_call(method_name, args, kwargs, start_time, exception=exception)
                raise exception
        
        # Apply delay if configured
        if method_name in self.behavior.delays:
            time.sleep(self.behavior.delays[method_name])
        
        # Check for configured exception
        if method_name in self.behavior.exceptions:
            exception = self.behavior.exceptions[method_name]
            self._record_call(method_name, args, kwargs, start_time, exception=exception)
            raise exception
        
        # Execute side effect if configured
        if method_name in self.behavior.side_effects:
            try:
                self.behavior.side_effects[method_name](*args, **kwargs)
            except Exception as e:
                self._record_call(method_name, args, kwargs, start_time, exception=e)
                raise
        
        # Get return value
        if method_name in self.behavior.return_values:
            return_value = self.behavior.return_values[method_name]
        else:
            # Default return values for standard methods
            default_returns = {
                'initialize': True,
                'health_check': self.initialized,
                'shutdown': None,
                'get_capabilities': self.capabilities,
                'get_service_name': self.service_name
            }
            return_value = default_returns.get(method_name, None)
        
        # Handle special initialization logic
        if method_name == 'initialize' and return_value:
            self.initialized = True
            self.init_context = args[0] if args else None
        
        self._record_call(method_name, args, kwargs, start_time, return_value=return_value)
        return return_value
    
    def _record_call(self, 
                    method_name: str, 
                    args: tuple, 
                    kwargs: dict, 
                    start_time: float,
                    return_value: Any = None,
                    exception: Optional[Exception] = None) -> None:
        """
        Record a method call for tracking and verification.
        
        Args:
            method_name: Name of the method called
            args: Method arguments
            kwargs: Method keyword arguments
            start_time: Time when method execution started
            return_value: Value returned by method
            exception: Exception raised by method (if any)
        """
        if not self.behavior.track_calls:
            return
        
        import time
        
        record = MockCallRecord(
            method_name=method_name,
            args=args,
            kwargs=kwargs,
            timestamp=datetime.now(),
            return_value=return_value,
            exception=exception,
            duration_seconds=time.time() - start_time
        )
        
        self.call_records.append(record)
    
    def get_call_count(self, method_name: str) -> int:
        """
        Get the number of times a method was called.
        
        Args:
            method_name: Name of the method
            
        Returns:
            Number of calls made to the method
        """
        return self.call_counts.get(method_name, 0)
    
    def get_call_records(self, method_name: Optional[str] = None) -> List[MockCallRecord]:
        """
        Get call records for verification.
        
        Args:
            method_name: Optional method name to filter by
            
        Returns:
            List of call records
        """
        if method_name is None:
            return self.call_records.copy()
        
        return [record for record in self.call_records if record.method_name == method_name]
    
    def reset_call_tracking(self) -> None:
        """Reset call tracking data."""
        self.call_records.clear()
        self.call_counts.clear()
    
    def was_called(self, method_name: str, *args, **kwargs) -> bool:
        """
        Check if a method was called with specific arguments.
        
        Args:
            method_name: Name of the method
            *args: Expected arguments
            **kwargs: Expected keyword arguments
            
        Returns:
            True if method was called with specified arguments
        """
        for record in self.call_records:
            if (record.method_name == method_name and 
                record.args == args and 
                record.kwargs == kwargs):
                return True
        return False


class ServiceMockFactory:
    """
    Factory for creating mock services with predefined behaviors.
    
    This class provides convenient methods for creating mock services
    with common testing scenarios and behaviors.
    """
    
    @staticmethod
    def create_basic_mock(service_type: Type[T], 
                         service_name: str = None,
                         capabilities: List[str] = None) -> MockServiceInterface:
        """
        Create a basic mock service with default behavior.
        
        Args:
            service_type: Type of service to mock
            service_name: Name for the mock service
            capabilities: Capabilities the mock should provide
            
        Returns:
            Mock service instance
        """
        if service_name is None:
            service_name = f"Mock{service_type.__name__}"
        
        return MockServiceInterface(
            service_name=service_name,
            capabilities=capabilities or [],
            behavior=MockBehavior()
        )
    
    @staticmethod
    def create_failing_mock(service_type: Type[T],
                           fail_on: List[str] = None,
                           exception: Exception = None) -> MockServiceInterface:
        """
        Create a mock service that fails on specified methods.
        
        Args:
            service_type: Type of service to mock
            fail_on: List of method names that should fail
            exception: Exception to raise (defaults to RuntimeError)
            
        Returns:
            Mock service that fails on specified methods
        """
        fail_on = fail_on or ['initialize']
        exception = exception or RuntimeError("Mock service failure")
        
        behavior = MockBehavior()
        for method_name in fail_on:
            behavior.exceptions[method_name] = exception
        
        return MockServiceInterface(
            service_name=f"Failing{service_type.__name__}",
            capabilities=[],
            behavior=behavior
        )
    
    @staticmethod
    def create_slow_mock(service_type: Type[T],
                        delays: Dict[str, float] = None) -> MockServiceInterface:
        """
        Create a mock service with artificial delays.
        
        Args:
            service_type: Type of service to mock
            delays: Dictionary of method names to delay times in seconds
            
        Returns:
            Mock service with delays
        """
        delays = delays or {'initialize': 0.1, 'health_check': 0.05}
        
        behavior = MockBehavior()
        behavior.delays = delays
        
        return MockServiceInterface(
            service_name=f"Slow{service_type.__name__}",
            capabilities=[],
            behavior=behavior
        )
    
    @staticmethod
    def create_unreliable_mock(service_type: Type[T],
                              failure_rate: float = 0.3) -> MockServiceInterface:
        """
        Create a mock service that fails randomly.
        
        Args:
            service_type: Type of service to mock
            failure_rate: Probability of failure (0.0 to 1.0)
            
        Returns:
            Mock service with random failures
        """
        import random
        
        def random_failure(*args, **kwargs):
            if random.random() < failure_rate:
                raise RuntimeError("Random mock failure")
        
        behavior = MockBehavior()
        behavior.side_effects = {
            'initialize': random_failure,
            'health_check': random_failure
        }
        
        return MockServiceInterface(
            service_name=f"Unreliable{service_type.__name__}",
            capabilities=[],
            behavior=behavior
        )


class MockServiceRegistry:
    """
    Registry for managing mock services during testing.
    
    This class provides a centralized way to manage mock services
    and their behaviors during integration testing.
    """
    
    def __init__(self):
        """Initialize empty mock registry."""
        self._mocks: Dict[Type[ServiceInterface], MockServiceInterface] = {}
        self._original_services: Dict[Type[ServiceInterface], ServiceInterface] = {}
    
    def register_mock(self, 
                     service_type: Type[T], 
                     mock_service: MockServiceInterface) -> None:
        """
        Register a mock service for a service type.
        
        Args:
            service_type: Type of service to mock
            mock_service: Mock service instance
        """
        self._mocks[service_type] = mock_service
        logger.debug(f"Registered mock for {service_type.__name__}")
    
    def get_mock(self, service_type: Type[T]) -> Optional[MockServiceInterface]:
        """
        Get mock service for a service type.
        
        Args:
            service_type: Type of service
            
        Returns:
            Mock service instance or None if not registered
        """
        return self._mocks.get(service_type)
    
    def remove_mock(self, service_type: Type[ServiceInterface]) -> bool:
        """
        Remove mock service for a service type.
        
        Args:
            service_type: Type of service
            
        Returns:
            True if mock was removed, False if not found
        """
        if service_type in self._mocks:
            del self._mocks[service_type]
            logger.debug(f"Removed mock for {service_type.__name__}")
            return True
        return False
    
    def clear_mocks(self) -> None:
        """Clear all registered mocks."""
        self._mocks.clear()
        logger.debug("Cleared all mock services")
    
    def get_all_mocks(self) -> Dict[Type[ServiceInterface], MockServiceInterface]:
        """
        Get all registered mock services.
        
        Returns:
            Dictionary of service types to mock instances
        """
        return self._mocks.copy()
    
    def backup_original_service(self, 
                               service_type: Type[ServiceInterface], 
                               original_service: ServiceInterface) -> None:
        """
        Backup original service before replacing with mock.
        
        Args:
            service_type: Type of service
            original_service: Original service instance
        """
        self._original_services[service_type] = original_service
    
    def restore_original_service(self, service_type: Type[ServiceInterface]) -> Optional[ServiceInterface]:
        """
        Restore original service after testing.
        
        Args:
            service_type: Type of service
            
        Returns:
            Original service instance or None if not backed up
        """
        return self._original_services.pop(service_type, None)
    
    def restore_all_services(self) -> Dict[Type[ServiceInterface], ServiceInterface]:
        """
        Restore all original services.
        
        Returns:
            Dictionary of restored services
        """
        restored = self._original_services.copy()
        self._original_services.clear()
        return restored


class MockingContext:
    """
    Context manager for service mocking during tests.
    
    This class provides a convenient way to temporarily replace services
    with mocks during testing and automatically restore them afterwards.
    """
    
    def __init__(self, service_manager):
        """
        Initialize mocking context.
        
        Args:
            service_manager: ServiceManager instance to mock services in
        """
        self.service_manager = service_manager
        self.mock_registry = MockServiceRegistry()
        self._active_mocks: Dict[Type[ServiceInterface], MockServiceInterface] = {}
    
    def mock_service(self, 
                    service_type: Type[T], 
                    mock_service: MockServiceInterface = None,
                    behavior: MockBehavior = None) -> MockServiceInterface:
        """
        Mock a service in the service manager.
        
        Args:
            service_type: Type of service to mock
            mock_service: Pre-created mock service (optional)
            behavior: Mock behavior configuration (optional)
            
        Returns:
            Mock service instance
        """
        if mock_service is None:
            mock_service = ServiceMockFactory.create_basic_mock(service_type)
            if behavior is not None:
                mock_service.behavior = behavior
        
        # Backup original service if it exists
        try:
            original_service = self.service_manager.get_service(service_type)
            self.mock_registry.backup_original_service(service_type, original_service)
        except:
            # Service not registered or not initialized - that's okay
            pass
        
        # Register mock
        self.mock_registry.register_mock(service_type, mock_service)
        self._active_mocks[service_type] = mock_service
        
        # Replace in service manager (unregister first if already registered)
        self.service_manager._registry.unregister(service_type)
        self.service_manager._registry.register(service_type, mock_service)
        self.service_manager._initialized_services.add(service_type)
        
        logger.info(f"Mocked service: {service_type.__name__}")
        return mock_service
    
    def unmock_service(self, service_type: Type[ServiceInterface]) -> bool:
        """
        Remove mock and restore original service.
        
        Args:
            service_type: Type of service to unmock
            
        Returns:
            True if service was unmocked, False if not mocked
        """
        if service_type not in self._active_mocks:
            return False
        
        # Remove mock
        del self._active_mocks[service_type]
        self.mock_registry.remove_mock(service_type)
        
        # Restore original service if available
        original_service = self.mock_registry.restore_original_service(service_type)
        if original_service is not None:
            # Unregister mock first, then register original
            self.service_manager._registry.unregister(service_type)
            self.service_manager._registry.register(service_type, original_service)
        else:
            # Remove from service manager if no original
            self.service_manager._registry.unregister(service_type)
            self.service_manager._initialized_services.discard(service_type)
        
        logger.info(f"Unmocked service: {service_type.__name__}")
        return True
    
    def get_mock(self, service_type: Type[T]) -> Optional[MockServiceInterface]:
        """
        Get active mock for a service type.
        
        Args:
            service_type: Type of service
            
        Returns:
            Mock service instance or None if not mocked
        """
        return self._active_mocks.get(service_type)
    
    def __enter__(self):
        """Enter mocking context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit mocking context and restore all services."""
        # Restore all services
        for service_type in list(self._active_mocks.keys()):
            self.unmock_service(service_type)
        
        logger.info("Exited mocking context - all services restored")


# Convenience functions for common mocking scenarios

def create_mock_service_context(config_manager=None, 
                               event_bus=None, 
                               service_registry=None) -> ServiceContext:
    """
    Create a mock service context for testing.
    
    Args:
        config_manager: Mock config manager (creates one if None)
        event_bus: Mock event bus (creates one if None)
        service_registry: Mock service registry (creates one if None)
        
    Returns:
        Mock service context
    """
    if config_manager is None:
        config_manager = Mock()
    if event_bus is None:
        event_bus = Mock()
    if service_registry is None:
        service_registry = Mock()
    
    return ServiceContext(
        config_manager=config_manager,
        event_bus=event_bus,
        service_registry=service_registry
    )


def mock_service_method(service: MockServiceInterface, 
                       method_name: str, 
                       return_value: Any = None,
                       exception: Exception = None,
                       side_effect: Callable = None) -> None:
    """
    Configure mock behavior for a specific method.
    
    Args:
        service: Mock service to configure
        method_name: Name of method to configure
        return_value: Value to return when method is called
        exception: Exception to raise when method is called
        side_effect: Function to call when method is invoked
    """
    if return_value is not None:
        service.behavior.return_values[method_name] = return_value
    
    if exception is not None:
        service.behavior.exceptions[method_name] = exception
    
    if side_effect is not None:
        service.behavior.side_effects[method_name] = side_effect


def verify_service_calls(service: MockServiceInterface, 
                        expected_calls: List[tuple]) -> bool:
    """
    Verify that a mock service was called with expected arguments.
    
    Args:
        service: Mock service to verify
        expected_calls: List of (method_name, args, kwargs) tuples
        
    Returns:
        True if all expected calls were made
    """
    for method_name, args, kwargs in expected_calls:
        if not service.was_called(method_name, *args, **kwargs):
            return False
    return True