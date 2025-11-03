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
Tests for EventBus implementation in TimeLocker Integration Architecture
"""

import pytest
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.TimeLocker.integration.event_bus import (
    EventBus, EventFilter, EventSubscription, EventPersistence, DeadLetterQueue
)
from src.TimeLocker.interfaces.integration_data_models import Event
from src.TimeLocker.interfaces.integration_exceptions import (
    EventBusError, EventPublishError, EventSubscriptionError, EventPersistenceError
)


class TestEventFilter:
    """Test EventFilter functionality"""
    
    def test_event_filter_creation(self):
        """Test EventFilter creation with various parameters"""
        # Test with all parameters
        event_filter = EventFilter(
            event_type_pattern="backup.*",
            source_pattern="service.*",
            min_priority=5,
            max_age_seconds=3600,
            custom_filter=lambda e: e.priority > 0
        )
        
        assert event_filter.event_type_pattern is not None
        assert event_filter.source_pattern is not None
        assert event_filter.min_priority == 5
        assert event_filter.max_age_seconds == 3600
        assert event_filter.custom_filter is not None
        
        # Test with no parameters
        empty_filter = EventFilter()
        assert empty_filter.event_type_pattern is None
        assert empty_filter.source_pattern is None
        assert empty_filter.min_priority is None
        assert empty_filter.max_age_seconds is None
        assert empty_filter.custom_filter is None
    
    def test_event_filter_matching(self):
        """Test event matching with filters"""
        # Create test event
        event = Event(
            event_type="backup.completed",
            source="service.backup",
            timestamp=datetime.now(),
            data={"test": "data"},
            priority=7
        )
        
        # Test event type pattern matching
        type_filter = EventFilter(event_type_pattern="backup.*")
        assert type_filter.matches(event) is True
        
        non_matching_filter = EventFilter(event_type_pattern="restore.*")
        assert non_matching_filter.matches(event) is False
        
        # Test source pattern matching
        source_filter = EventFilter(source_pattern="service.*")
        assert source_filter.matches(event) is True
        
        # Test priority filtering
        priority_filter = EventFilter(min_priority=5)
        assert priority_filter.matches(event) is True
        
        high_priority_filter = EventFilter(min_priority=10)
        assert high_priority_filter.matches(event) is False
        
        # Test custom filter
        custom_filter = EventFilter(custom_filter=lambda e: "backup" in e.event_type)
        assert custom_filter.matches(event) is True
        
        # Test age filtering (event should be very recent)
        age_filter = EventFilter(max_age_seconds=60)
        assert age_filter.matches(event) is True
        
        # Test combined filters
        combined_filter = EventFilter(
            event_type_pattern="backup.*",
            min_priority=5
        )
        assert combined_filter.matches(event) is True


class TestEventSubscription:
    """Test EventSubscription functionality"""
    
    def test_subscription_creation(self):
        """Test EventSubscription creation"""
        handler = Mock()
        event_filter = EventFilter(event_type_pattern="test.*")
        
        subscription = EventSubscription(
            subscription_id="test-sub-1",
            handler=handler,
            event_filter=event_filter,
            subscriber_name="test_subscriber"
        )
        
        assert subscription.subscription_id == "test-sub-1"
        assert subscription.handler is handler
        assert subscription.event_filter is event_filter
        assert subscription.subscriber_name == "test_subscriber"
        assert subscription.event_count == 0
        assert subscription.error_count == 0
    
    def test_subscription_event_matching(self):
        """Test subscription event matching"""
        handler = Mock()
        event_filter = EventFilter(event_type_pattern="backup.*")
        
        subscription = EventSubscription(
            subscription_id="test-sub-1",
            handler=handler,
            event_filter=event_filter
        )
        
        # Test matching event
        matching_event = Event(
            event_type="backup.started",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        assert subscription.matches_event(matching_event) is True
        
        # Test non-matching event
        non_matching_event = Event(
            event_type="restore.started",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        assert subscription.matches_event(non_matching_event) is False
        
        # Test subscription without filter (should match all)
        no_filter_subscription = EventSubscription(
            subscription_id="test-sub-2",
            handler=handler
        )
        assert no_filter_subscription.matches_event(matching_event) is True
        assert no_filter_subscription.matches_event(non_matching_event) is True
    
    def test_subscription_event_handling(self):
        """Test subscription event handling"""
        handler = Mock()
        subscription = EventSubscription(
            subscription_id="test-sub-1",
            handler=handler
        )
        
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        
        # Test successful handling
        result = subscription.handle_event(event)
        assert result is True
        assert subscription.event_count == 1
        assert subscription.last_event_at is not None
        handler.assert_called_once_with(event)
        
        # Test handler error
        handler.side_effect = Exception("Handler error")
        result = subscription.handle_event(event)
        assert result is False
        assert subscription.error_count == 1
        assert subscription.last_error == "Handler error"


class TestEventPersistence:
    """Test EventPersistence functionality"""
    
    def test_persistence_creation(self):
        """Test EventPersistence creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "events"
            persistence = EventPersistence(storage_path)
            
            assert persistence.storage_path == storage_path
            assert storage_path.exists()
            assert persistence.critical_events_file.parent.exists()
            assert persistence.audit_events_file.parent.exists()
    
    def test_event_persistence(self):
        """Test event persistence operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "events"
            persistence = EventPersistence(storage_path)
            
            # Create test event
            event = Event(
                event_type="test.event",
                source="test",
                timestamp=datetime.now(),
                data={"key": "value"},
                correlation_id="test-correlation"
            )
            
            # Test persisting critical event
            persistence.persist_event(event, is_critical=True)
            assert persistence.critical_events_file.exists()
            
            # Test persisting regular event
            persistence.persist_event(event, is_critical=False)
            assert persistence.audit_events_file.exists()
            
            # Test correlation index update
            assert "test-correlation" in persistence._correlation_index
            assert event.event_id in persistence._correlation_index["test-correlation"]
    
    def test_correlation_retrieval(self):
        """Test retrieving events by correlation ID"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "events"
            persistence = EventPersistence(storage_path)
            
            correlation_id = "test-correlation-123"
            
            # Create and persist multiple correlated events
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
                persistence.persist_event(event, is_critical=(i == 0))
            
            # Retrieve correlated events
            retrieved_events = persistence.get_events_by_correlation(correlation_id)
            assert len(retrieved_events) == 3
            
            # Check that all events have the same correlation ID
            for event in retrieved_events:
                assert event.correlation_id == correlation_id
    
    def test_recent_events_retrieval(self):
        """Test retrieving recent events"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "events"
            persistence = EventPersistence(storage_path)
            
            # Create events with different timestamps
            now = datetime.now()
            old_event = Event(
                event_type="old.event",
                source="test",
                timestamp=now - timedelta(hours=25),  # Older than 24 hours
                data={}
            )
            recent_event = Event(
                event_type="recent.event",
                source="test",
                timestamp=now - timedelta(hours=1),  # Within 24 hours
                data={}
            )
            
            # Persist events
            persistence.persist_event(old_event)
            persistence.persist_event(recent_event)
            
            # Retrieve recent events (last 24 hours)
            recent_events = persistence.get_recent_events(hours=24)
            
            # Should only get the recent event
            assert len(recent_events) == 1
            assert recent_events[0].event_type == "recent.event"


class TestDeadLetterQueue:
    """Test DeadLetterQueue functionality"""
    
    def test_dead_letter_queue_creation(self):
        """Test DeadLetterQueue creation"""
        dlq = DeadLetterQueue(max_size=100)
        assert dlq.max_size == 100
        assert len(dlq.get_failed_events()) == 0
    
    def test_failed_event_handling(self):
        """Test adding and retrieving failed events"""
        dlq = DeadLetterQueue()
        
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        
        # Add failed event
        dlq.add_failed_event(event, "sub-123", "Handler failed")
        
        failed_events = dlq.get_failed_events()
        assert len(failed_events) == 1
        
        failed_entry = failed_events[0]
        assert failed_entry["event"] is event
        assert failed_entry["subscription_id"] == "sub-123"
        assert failed_entry["error"] == "Handler failed"
        assert failed_entry["retry_count"] == 0
    
    def test_clear_old_entries(self):
        """Test clearing old entries from dead letter queue"""
        dlq = DeadLetterQueue()
        
        # Add old entry
        old_event = Event(
            event_type="old.event",
            source="test",
            timestamp=datetime.now() - timedelta(hours=25),
            data={}
        )
        dlq.add_failed_event(old_event, "sub-1", "Old error")
        
        # Manually set failed_at to be old
        dlq._queue[0]["failed_at"] = datetime.now() - timedelta(hours=25)
        
        # Add recent entry
        recent_event = Event(
            event_type="recent.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        dlq.add_failed_event(recent_event, "sub-2", "Recent error")
        
        # Clear old entries
        cleared_count = dlq.clear_old_entries(max_age_hours=24)
        assert cleared_count == 1
        
        # Should only have recent entry
        remaining_events = dlq.get_failed_events()
        assert len(remaining_events) == 1
        assert remaining_events[0]["event"].event_type == "recent.event"


class TestEventBus:
    """Test EventBus functionality"""
    
    def test_event_bus_creation(self):
        """Test EventBus creation"""
        # Test without persistence
        event_bus = EventBus(enable_persistence=False)
        assert event_bus._persistence is None
        assert not event_bus._is_shutdown
        
        # Test with persistence
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence_path = Path(temp_dir) / "events"
            event_bus = EventBus(persistence_path=persistence_path)
            assert event_bus._persistence is not None
            assert event_bus._persistence.storage_path == persistence_path
    
    def test_event_publishing_and_subscription(self):
        """Test basic event publishing and subscription"""
        event_bus = EventBus(enable_persistence=False)
        
        # Create handler mock
        handler = Mock()
        
        # Subscribe to events
        subscription_id = event_bus.subscribe_event(
            event_type_pattern="test.*",
            handler=handler,
            subscriber_name="test_subscriber"
        )
        
        assert subscription_id is not None
        
        # Publish matching event
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={"message": "test"}
        )
        
        event_bus.publish_event(event)
        
        # Verify handler was called
        handler.assert_called_once_with(event)
        
        # Check statistics
        stats = event_bus.get_statistics()
        assert stats["events_published"] == 1
        assert stats["events_delivered"] == 1
        assert stats["active_subscriptions"] == 1
    
    def test_event_filtering(self):
        """Test event filtering in subscriptions"""
        event_bus = EventBus(enable_persistence=False)
        
        # Create handlers
        backup_handler = Mock()
        restore_handler = Mock()
        all_handler = Mock()
        
        # Subscribe with different filters
        backup_sub = event_bus.subscribe_event(
            event_type_pattern="backup.*",
            handler=backup_handler,
            subscriber_name="backup_subscriber"
        )
        
        restore_sub = event_bus.subscribe_event(
            event_type_pattern="restore.*",
            handler=restore_handler,
            subscriber_name="restore_subscriber"
        )
        
        all_sub = event_bus.subscribe_event(
            handler=all_handler,
            subscriber_name="all_subscriber"
        )
        
        # Publish backup event
        backup_event = Event(
            event_type="backup.completed",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        event_bus.publish_event(backup_event)
        
        # Verify only backup and all handlers were called
        backup_handler.assert_called_once_with(backup_event)
        restore_handler.assert_not_called()
        all_handler.assert_called_once_with(backup_event)
        
        # Reset mocks
        backup_handler.reset_mock()
        all_handler.reset_mock()
        
        # Publish restore event
        restore_event = Event(
            event_type="restore.started",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        event_bus.publish_event(restore_event)
        
        # Verify only restore and all handlers were called
        backup_handler.assert_not_called()
        restore_handler.assert_called_once_with(restore_event)
        all_handler.assert_called_once_with(restore_event)
    
    def test_priority_filtering(self):
        """Test priority-based event filtering"""
        event_bus = EventBus(enable_persistence=False)
        
        high_priority_handler = Mock()
        all_handler = Mock()
        
        # Subscribe with priority filter
        high_priority_sub = event_bus.subscribe_event(
            min_priority=5,
            handler=high_priority_handler,
            subscriber_name="high_priority_subscriber"
        )
        
        all_sub = event_bus.subscribe_event(
            handler=all_handler,
            subscriber_name="all_subscriber"
        )
        
        # Publish low priority event
        low_priority_event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={},
            priority=2
        )
        event_bus.publish_event(low_priority_event)
        
        # Only all handler should be called
        high_priority_handler.assert_not_called()
        all_handler.assert_called_once_with(low_priority_event)
        
        # Reset mock
        all_handler.reset_mock()
        
        # Publish high priority event
        high_priority_event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={},
            priority=7
        )
        event_bus.publish_event(high_priority_event)
        
        # Both handlers should be called
        high_priority_handler.assert_called_once_with(high_priority_event)
        all_handler.assert_called_once_with(high_priority_event)
    
    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        event_bus = EventBus(enable_persistence=False)
        
        handler = Mock()
        
        # Subscribe
        subscription_id = event_bus.subscribe_event(
            handler=handler,
            subscriber_name="test_subscriber"
        )
        
        # Publish event - should be delivered
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        event_bus.publish_event(event)
        handler.assert_called_once_with(event)
        
        # Unsubscribe
        result = event_bus.unsubscribe_event(subscription_id)
        assert result is True
        
        # Reset mock and publish again - should not be delivered
        handler.reset_mock()
        event_bus.publish_event(event)
        handler.assert_not_called()
        
        # Try to unsubscribe again - should return False
        result = event_bus.unsubscribe_event(subscription_id)
        assert result is False
    
    def test_error_handling_and_dead_letter_queue(self):
        """Test error handling and dead letter queue"""
        event_bus = EventBus(enable_persistence=False)
        
        # Create handler that raises exception
        failing_handler = Mock(side_effect=Exception("Handler error"))
        working_handler = Mock()
        
        # Subscribe both handlers
        failing_sub = event_bus.subscribe_event(
            handler=failing_handler,
            subscriber_name="failing_subscriber"
        )
        
        working_sub = event_bus.subscribe_event(
            handler=working_handler,
            subscriber_name="working_subscriber"
        )
        
        # Publish event
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        event_bus.publish_event(event)
        
        # Both handlers should be called
        failing_handler.assert_called_once_with(event)
        working_handler.assert_called_once_with(event)
        
        # Check statistics
        stats = event_bus.get_statistics()
        assert stats["events_published"] == 1
        assert stats["events_delivered"] == 1  # Only working handler succeeded
        assert stats["events_failed"] == 1
        assert stats["dead_letter_queue_size"] == 1
        
        # Check dead letter queue
        failed_events = event_bus._dead_letter_queue.get_failed_events()
        assert len(failed_events) == 1
        assert failed_events[0]["subscription_id"] == failing_sub
        assert "Handler error" in failed_events[0]["error"]
    
    def test_event_persistence_integration(self):
        """Test event persistence integration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence_path = Path(temp_dir) / "events"
            event_bus = EventBus(persistence_path=persistence_path)
            
            # Create critical event (high priority)
            critical_event = Event(
                event_type="critical.error",
                source="test",
                timestamp=datetime.now(),
                data={"error": "Critical system error"},
                priority=8,
                correlation_id="critical-123"
            )
            
            # Publish critical event
            event_bus.publish_event(critical_event)
            
            # Verify persistence files were created
            assert event_bus._persistence.critical_events_file.exists()
            assert event_bus._persistence.audit_events_file.exists()
            
            # Retrieve by correlation
            correlated_events = event_bus.get_events_by_correlation("critical-123")
            assert len(correlated_events) >= 1
            assert any(e.event_id == critical_event.event_id for e in correlated_events)
    
    def test_shutdown(self):
        """Test event bus shutdown"""
        event_bus = EventBus(enable_persistence=False)
        
        # Subscribe to events
        handler = Mock()
        subscription_id = event_bus.subscribe_event(handler=handler)
        
        # Shutdown
        event_bus.shutdown()
        assert event_bus._is_shutdown is True
        
        # Should not be able to publish after shutdown
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        
        with pytest.raises(EventPublishError):
            event_bus.publish_event(event)
        
        # Should not be able to subscribe after shutdown
        with pytest.raises(EventSubscriptionError):
            event_bus.subscribe_event(handler=handler)
    
    def test_subscription_info(self):
        """Test getting subscription information"""
        event_bus = EventBus(enable_persistence=False)
        
        handler = Mock()
        
        # Create subscription
        subscription_id = event_bus.subscribe_event(
            event_type_pattern="test.*",
            handler=handler,
            subscriber_name="test_subscriber"
        )
        
        # Get subscription info
        info = event_bus.get_subscription_info()
        assert subscription_id in info
        
        sub_info = info[subscription_id]
        assert sub_info["subscriber_name"] == "test_subscriber"
        assert sub_info["event_count"] == 0
        assert sub_info["error_count"] == 0
        assert sub_info["has_filter"] is True
        
        # Publish event to update stats
        event = Event(
            event_type="test.event",
            source="test",
            timestamp=datetime.now(),
            data={}
        )
        event_bus.publish_event(event)
        
        # Check updated info
        updated_info = event_bus.get_subscription_info()
        updated_sub_info = updated_info[subscription_id]
        assert updated_sub_info["event_count"] == 1
        assert updated_sub_info["last_event_at"] is not None
    
    def test_concurrent_operations(self):
        """Test concurrent event publishing and subscription"""
        event_bus = EventBus(enable_persistence=False)
        
        # Shared state for testing
        received_events = []
        lock = threading.Lock()
        
        def handler(event):
            with lock:
                received_events.append(event)
        
        # Subscribe
        subscription_id = event_bus.subscribe_event(
            handler=handler,
            subscriber_name="concurrent_subscriber"
        )
        
        # Publish events from multiple threads
        def publish_events(thread_id, count):
            for i in range(count):
                event = Event(
                    event_type=f"thread.{thread_id}.event.{i}",
                    source=f"thread-{thread_id}",
                    timestamp=datetime.now(),
                    data={"thread_id": thread_id, "index": i}
                )
                event_bus.publish_event(event)
                time.sleep(0.001)  # Small delay to allow interleaving
        
        # Create and start threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=publish_events, args=(thread_id, 5))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all events were received
        with lock:
            assert len(received_events) == 15  # 3 threads * 5 events each
            
            # Verify events from all threads are present
            thread_ids = set(event.data["thread_id"] for event in received_events)
            assert thread_ids == {0, 1, 2}


if __name__ == "__main__":
    pytest.main([__file__])