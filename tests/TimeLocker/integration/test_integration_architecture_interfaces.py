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
Tests for Integration Architecture Interfaces

This module tests the core integration architecture interfaces including
ServiceInterface, ServiceContext, and Event data models.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from TimeLocker.interfaces import (
    ServiceInterface, 
    ServiceContext, 
    Event,
    ServiceInitializationError,
    ServiceShutdownError,
    ServiceContextValidationError,
    EventValidationError
)


class TestServiceInterface:
    """Test cases for ServiceInterface base class"""

    def test_service_interface_is_abstract(self):
        """Test that ServiceInterface cannot be instantiated directly"""
        with pytest.raises(TypeError):
            ServiceInterface()

    def test_concrete_service_implementation(self):
        """Test that concrete service implementations work correctly"""
        
        class TestService(ServiceInterface):
            def __init__(self):
                self.initialized = False
                self.shutdown_called = False
            
            def initialize(self, context: ServiceContext) -> bool:
                if not self.validate_context(context):
                    return False
                self.initialized = True
                return True
            
            def shutdown(self) -> None:
                self.shutdown_called = True
            
            def health_check(self) -> bool:
                return self.initialized
            
            def get_capabilities(self) -> list:
                return ['test_capability']
        
        # Create mock context
        mock_config = Mock()
        mock_event_bus = Mock()
        mock_registry = Mock()
        
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=mock_event_bus,
            service_registry=mock_registry
        )
        
        # Test service lifecycle
        service = TestService()
        assert not service.initialized
        assert not service.shutdown_called
        
        # Test initialization
        result = service.initialize(context)
        assert result is True
        assert service.initialized
        
        # Test health check
        assert service.health_check() is True
        
        # Test capabilities
        capabilities = service.get_capabilities()
        assert capabilities == ['test_capability']
        
        # Test service name and version
        assert service.get_service_name() == 'TestService'
        assert service.get_service_version() == '1.0.0'
        
        # Test shutdown
        service.shutdown()
        assert service.shutdown_called

    def test_context_validation(self):
        """Test service context validation"""
        
        class TestService(ServiceInterface):
            def initialize(self, context: ServiceContext) -> bool:
                return True
            def shutdown(self) -> None:
                pass
            def health_check(self) -> bool:
                return True
            def get_capabilities(self) -> list:
                return []
        
        service = TestService()
        
        # Test with None context
        assert service.validate_context(None) is False
        
        # Test with valid context
        valid_context = ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock()
        )
        assert service.validate_context(valid_context) is True
        
        # Test validation logic by creating a mock context object
        # that bypasses __post_init__ validation
        class MockContext:
            def __init__(self):
                self.config_manager = Mock()
                self.event_bus = None  # Missing component
                self.service_registry = Mock()
        
        mock_context = MockContext()
        assert service.validate_context(mock_context) is False


class TestServiceContext:
    """Test cases for ServiceContext data model"""

    def test_service_context_creation(self):
        """Test ServiceContext creation and validation"""
        mock_config = Mock()
        mock_event_bus = Mock()
        mock_registry = Mock()
        
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=mock_event_bus,
            service_registry=mock_registry
        )
        
        assert context.config_manager is mock_config
        assert context.event_bus is mock_event_bus
        assert context.service_registry is mock_registry
        assert context.user_context is None
        assert context.operation_id is not None
        assert context.parent_context is None
        assert isinstance(context.metadata, dict)

    def test_service_context_validation_errors(self):
        """Test ServiceContext validation with missing components"""
        
        # Test missing config_manager
        with pytest.raises(ValueError, match="ServiceContext requires a valid config_manager"):
            ServiceContext(
                config_manager=None,
                event_bus=Mock(),
                service_registry=Mock()
            )
        
        # Test missing event_bus
        with pytest.raises(ValueError, match="ServiceContext requires a valid event_bus"):
            ServiceContext(
                config_manager=Mock(),
                event_bus=None,
                service_registry=Mock()
            )
        
        # Test missing service_registry
        with pytest.raises(ValueError, match="ServiceContext requires a valid service_registry"):
            ServiceContext(
                config_manager=Mock(),
                event_bus=Mock(),
                service_registry=None
            )

    def test_child_context_creation(self):
        """Test child context creation and inheritance"""
        parent_context = ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock(),
            user_context={'user': 'test_user'},
            metadata={'parent_key': 'parent_value'}
        )
        
        child_context = parent_context.create_child_context(
            metadata={'child_key': 'child_value'}
        )
        
        # Test inheritance
        assert child_context.config_manager is parent_context.config_manager
        assert child_context.event_bus is parent_context.event_bus
        assert child_context.service_registry is parent_context.service_registry
        assert child_context.parent_context is parent_context
        
        # Test that user_context is copied, not shared
        assert child_context.user_context == parent_context.user_context
        assert child_context.user_context is not parent_context.user_context
        
        # Test metadata override
        assert child_context.metadata == {'child_key': 'child_value'}

    def test_inherited_value_lookup(self):
        """Test inherited value lookup through context hierarchy"""
        grandparent_context = ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock(),
            metadata={'grandparent_key': 'grandparent_value'}
        )
        
        parent_context = grandparent_context.create_child_context(
            user_context={'parent_key': 'parent_value'},
            metadata={'parent_key': 'parent_metadata'}
        )
        
        child_context = parent_context.create_child_context(
            metadata={'child_key': 'child_value'}
        )
        
        # Test value lookup
        assert child_context.get_inherited_value('child_key') == 'child_value'
        assert child_context.get_inherited_value('parent_key') == 'parent_value'
        assert child_context.get_inherited_value('grandparent_key') == 'grandparent_value'
        assert child_context.get_inherited_value('nonexistent', 'default') == 'default'

    def test_context_cleanup(self):
        """Test context cleanup functionality"""
        context = ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock(),
            user_context={
                'username': 'test_user',
                'password': 'secret123',
                'api_key': 'key123',
                'normal_data': 'keep_this'
            },
            metadata={'test_key': 'test_value'}
        )
        
        context.cleanup()
        
        # Test that sensitive data is removed
        assert 'password' not in context.user_context
        assert 'api_key' not in context.user_context
        
        # Test that non-sensitive data is kept
        assert context.user_context['username'] == 'test_user'
        assert context.user_context['normal_data'] == 'keep_this'
        
        # Test that metadata is cleared
        assert len(context.metadata) == 0


class TestEvent:
    """Test cases for Event data model"""

    def test_event_creation(self):
        """Test Event creation and validation"""
        timestamp = datetime.now()
        event_data = {'key': 'value'}
        
        event = Event(
            event_type='test.event',
            source='test_service',
            timestamp=timestamp,
            data=event_data
        )
        
        assert event.event_type == 'test.event'
        assert event.source == 'test_service'
        assert event.timestamp == timestamp
        assert event.data == event_data
        assert event.correlation_id is None
        assert event.event_id is not None
        assert event.priority == 0
        assert isinstance(event.metadata, dict)

    def test_event_validation_errors(self):
        """Test Event validation with invalid data"""
        
        # Test missing event_type
        with pytest.raises(ValueError, match="Event requires a valid event_type"):
            Event(
                event_type='',
                source='test_service',
                timestamp=datetime.now(),
                data={}
            )
        
        # Test missing source
        with pytest.raises(ValueError, match="Event requires a valid source"):
            Event(
                event_type='test.event',
                source='',
                timestamp=datetime.now(),
                data={}
            )

    def test_event_correlation(self):
        """Test event correlation functionality"""
        event1 = Event(
            event_type='test.event1',
            source='service1',
            timestamp=datetime.now(),
            data={}
        )
        
        event2 = Event(
            event_type='test.event2',
            source='service2',
            timestamp=datetime.now(),
            data={}
        )
        
        # Test initial state
        assert not event1.is_correlated_with(event2)
        
        # Add correlation
        correlation_id = 'test_correlation_123'
        event1.add_correlation(correlation_id)
        event2.add_correlation(correlation_id)
        
        # Test correlation
        assert event1.correlation_id == correlation_id
        assert event2.correlation_id == correlation_id
        assert event1.is_correlated_with(event2)
        assert event2.is_correlated_with(event1)
        
        # Test metadata correlation tracking
        assert correlation_id in event1.metadata['correlations']
        assert correlation_id in event2.metadata['correlations']

    def test_event_serialization(self):
        """Test event serialization and deserialization"""
        original_event = Event(
            event_type='test.event',
            source='test_service',
            timestamp=datetime.now(),
            data={'key': 'value'},
            correlation_id='test_correlation',
            priority=5,
            metadata={'meta_key': 'meta_value'}
        )
        
        # Test to_dict
        event_dict = original_event.to_dict()
        assert event_dict['event_type'] == 'test.event'
        assert event_dict['source'] == 'test_service'
        assert event_dict['data'] == {'key': 'value'}
        assert event_dict['correlation_id'] == 'test_correlation'
        assert event_dict['priority'] == 5
        
        # Test from_dict
        reconstructed_event = Event.from_dict(event_dict)
        assert reconstructed_event.event_type == original_event.event_type
        assert reconstructed_event.source == original_event.source
        assert reconstructed_event.data == original_event.data
        assert reconstructed_event.correlation_id == original_event.correlation_id
        assert reconstructed_event.priority == original_event.priority
        assert reconstructed_event.metadata == original_event.metadata

    def test_event_age_calculation(self):
        """Test event age calculation"""
        import time
        
        event = Event(
            event_type='test.event',
            source='test_service',
            timestamp=datetime.now(),
            data={}
        )
        
        # Wait a small amount of time
        time.sleep(0.1)
        
        age = event.get_age_seconds()
        assert age >= 0.1
        assert age < 1.0  # Should be less than 1 second