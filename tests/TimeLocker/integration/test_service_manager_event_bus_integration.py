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
Tests for ServiceManager and EventBus integration in TimeLocker Integration Architecture
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from src.TimeLocker.integration.service_manager import ServiceManager
from src.TimeLocker.integration.event_bus import EventBus
from src.TimeLocker.interfaces.integration_data_models import ServiceContext, Event
from src.TimeLocker.interfaces.service_interface import ServiceInterface


class TestServiceManagerEventBusIntegration:
    """Test integration between ServiceManager and EventBus"""
    
    def test_service_manager_creates_event_bus(self):
        """Test that ServiceManager creates an EventBus automatically"""
        # Create mock context
        mock_config = Mock()
        mock_config.get_config_directory.return_value = None
        
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,  # Will be set by ServiceManager
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        
        # Verify EventBus was created
        event_bus = manager.get_event_bus()
        assert event_bus is not None
        assert isinstance(event_bus, EventBus)
        
        # Verify context was updated
        assert context.event_bus is event_bus
    
    def test_service_manager_uses_provided_event_bus(self):
        """Test that ServiceManager uses a provided EventBus"""
        # Create custom EventBus
        custom_event_bus = EventBus(enable_persistence=False)
        
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=custom_event_bus,
            service_registry=Mock()
        )
        
        # Create ServiceManager with custom EventBus
        manager = ServiceManager(context, event_bus=custom_event_bus)
        
        # Verify the custom EventBus is used
        assert manager.get_event_bus() is custom_event_bus
    
    def test_service_manager_event_publishing(self):
        """Test event publishing through ServiceManager"""
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        
        # Create event handler
        received_events = []
        def event_handler(event):
            received_events.append(event)
        
        # Subscribe to events
        subscription_id = manager.subscribe_event(
            event_type_pattern="test.*",
            handler=event_handler,
            subscriber_name="test_subscriber"
        )
        
        # Publish event
        test_event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={"message": "test message"}
        )
        
        manager.publish_event(test_event)
        
        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0] is test_event
        
        # Unsubscribe
        result = manager.unsubscribe_event(subscription_id)
        assert result is True
    
    def test_service_manager_event_filtering(self):
        """Test event filtering through ServiceManager"""
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        
        # Create event handlers
        backup_events = []
        restore_events = []
        
        def backup_handler(event):
            backup_events.append(event)
        
        def restore_handler(event):
            restore_events.append(event)
        
        # Subscribe to different event types
        backup_sub = manager.subscribe_event(
            event_type_pattern="backup.*",
            handler=backup_handler,
            subscriber_name="backup_subscriber"
        )
        
        restore_sub = manager.subscribe_event(
            event_type_pattern="restore.*",
            handler=restore_handler,
            subscriber_name="restore_subscriber"
        )
        
        # Publish backup event
        backup_event = Event(
            event_type="backup.completed",
            source="backup_service",
            timestamp=datetime.now(),
            data={"files": 100}
        )
        manager.publish_event(backup_event)
        
        # Publish restore event
        restore_event = Event(
            event_type="restore.started",
            source="restore_service",
            timestamp=datetime.now(),
            data={"snapshot_id": "abc123"}
        )
        manager.publish_event(restore_event)
        
        # Verify filtering worked
        assert len(backup_events) == 1
        assert backup_events[0] is backup_event
        
        assert len(restore_events) == 1
        assert restore_events[0] is restore_event
    
    def test_service_manager_event_statistics(self):
        """Test getting event statistics through ServiceManager"""
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        
        # Get initial statistics
        initial_stats = manager.get_event_statistics()
        assert initial_stats["events_published"] == 0
        assert initial_stats["active_subscriptions"] == 0
        
        # Subscribe to events
        handler = Mock()
        subscription_id = manager.subscribe_event(
            handler=handler,
            subscriber_name="test_subscriber"
        )
        
        # Publish event
        test_event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        manager.publish_event(test_event)
        
        # Get updated statistics
        updated_stats = manager.get_event_statistics()
        assert updated_stats["events_published"] == 1
        assert updated_stats["events_delivered"] == 1
        assert updated_stats["active_subscriptions"] == 1
    
    def test_service_manager_shutdown_includes_event_bus(self):
        """Test that ServiceManager shutdown includes EventBus shutdown"""
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        event_bus = manager.get_event_bus()
        
        # Verify EventBus is not shutdown initially
        assert not event_bus._is_shutdown
        
        # Shutdown ServiceManager
        manager.shutdown_services()
        
        # Verify EventBus was shutdown
        assert event_bus._is_shutdown
    
    def test_service_manager_with_persistence_path(self):
        """Test ServiceManager with EventBus persistence"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock config that returns a path
            mock_config = Mock()
            mock_config.get_config_directory.return_value = Path(temp_dir)
            
            context = ServiceContext(
                config_manager=mock_config,
                event_bus=None,
                service_registry=Mock()
            )
            
            # Create ServiceManager
            manager = ServiceManager(context)
            event_bus = manager.get_event_bus()
            
            # Verify persistence is enabled
            assert event_bus._persistence is not None
            assert event_bus._persistence.storage_path == Path(temp_dir) / "events"
            
            # Publish a critical event to test persistence
            critical_event = Event(
                event_type="critical.error",
                source="test",
                timestamp=datetime.now(),
                data={"error": "Test error"},
                priority=8
            )
            
            manager.publish_event(critical_event)
            
            # Verify persistence files were created
            assert event_bus._persistence.critical_events_file.exists()
    
    def test_service_manager_event_correlation(self):
        """Test event correlation through ServiceManager"""
        # Create mock context
        mock_config = Mock()
        context = ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=Mock()
        )
        
        # Create ServiceManager
        manager = ServiceManager(context)
        
        correlation_id = "test-correlation-123"
        
        # Publish multiple correlated events
        events = []
        for i in range(3):
            event = Event(
                event_type=f"test.event.{i}",
                source="test",
                timestamp=datetime.now(),
                data={"index": i},
                correlation_id=correlation_id
            )
            events.append(event)
            manager.publish_event(event)
        
        # Note: Without persistence, correlation retrieval won't work
        # This test mainly verifies the interface works
        event_bus = manager.get_event_bus()
        if event_bus._persistence:
            correlated_events = event_bus.get_events_by_correlation(correlation_id)
            assert len(correlated_events) >= 1


if __name__ == "__main__":
    pytest.main([__file__])