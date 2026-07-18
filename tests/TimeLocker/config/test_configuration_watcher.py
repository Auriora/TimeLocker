"""
Unit tests for ConfigurationWatcher.

Tests file system change monitoring, event notifications, subscription management,
and fallback polling mechanisms.
"""

import json
import time
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from TimeLocker.config.configuration_watcher import ConfigurationWatcher, WatchSubscription
from TimeLocker.interfaces.configuration_watcher import ConfigurationChangeEvent
from TimeLocker.interfaces.exceptions import ConfigurationWatchError, ConfigurationWatchStartupError


class TestConfigurationWatcher:
    """Test suite for ConfigurationWatcher"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "config.json"
        
        # Create initial configuration
        self.initial_config = {
            "general": {
                "app_name": "TimeLocker",
                "version": "1.0.0"
            },
            "backup": {
                "compression": "auto",
                "exclude_caches": True
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(self.initial_config, f, indent=2)
        
        # Create watcher with short polling interval for tests
        self.watcher = ConfigurationWatcher(self.config_file, polling_interval=0.1)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.watcher.is_watching():
            self.watcher.stop_watching()
        
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.config
    @pytest.mark.unit
    def test_watcher_initialization(self):
        """Test watcher initialization"""
        assert self.watcher.config_file == self.config_file
        assert self.watcher.polling_interval == 0.1
        assert not self.watcher.is_watching()
        assert len(self.watcher._subscriptions) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_section_watch_subscription(self):
        """Test watching configuration sections"""
        callback = Mock()
        
        # Subscribe to section changes
        watch_id = self.watcher.watch_section("general", callback)
        assert watch_id is not None
        assert len(self.watcher._subscriptions) == 1
        
        # Verify subscription details
        subscription = self.watcher._subscriptions[watch_id]
        assert subscription.pattern == "general"
        assert subscription.watch_type == "section"
        assert subscription.callback == callback

    @pytest.mark.config
    @pytest.mark.unit
    def test_key_watch_subscription(self):
        """Test watching specific configuration keys"""
        callback = Mock()
        
        # Subscribe to key changes
        watch_id = self.watcher.watch_key("general.version", callback)
        assert watch_id is not None
        assert len(self.watcher._subscriptions) == 1
        
        # Verify subscription details
        subscription = self.watcher._subscriptions[watch_id]
        assert subscription.pattern == "general.version"
        assert subscription.watch_type == "key"
        assert subscription.callback == callback

    @pytest.mark.config
    @pytest.mark.unit
    def test_unwatch_subscription(self):
        """Test removing watch subscriptions"""
        callback = Mock()
        
        # Create subscription
        watch_id = self.watcher.watch_section("general", callback)
        assert len(self.watcher._subscriptions) == 1
        
        # Remove subscription
        self.watcher.unwatch(watch_id)
        assert len(self.watcher._subscriptions) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_unwatch_nonexistent_subscription(self):
        """Test removing non-existent subscription"""
        # Should not raise error
        self.watcher.unwatch("nonexistent_id")

    @pytest.mark.config
    @pytest.mark.unit
    def test_start_and_stop_watching(self):
        """Test starting and stopping the watcher"""
        # Start watching
        self.watcher.start_watching()
        assert self.watcher.is_watching()
        
        # Stop watching
        self.watcher.stop_watching()
        assert not self.watcher.is_watching()

    @pytest.mark.config
    @pytest.mark.unit
    def test_start_watching_twice(self):
        """Test starting watcher when already running"""
        self.watcher.start_watching()
        assert self.watcher.is_watching()
        
        # Starting again should not cause issues
        self.watcher.start_watching()
        assert self.watcher.is_watching()

    @pytest.mark.config
    @pytest.mark.unit
    def test_file_change_detection_polling(self):
        """Test file change detection using polling"""
        callback = Mock()
        
        # Force polling mode
        with patch.object(self.watcher, '_use_watchdog', False):
            # Subscribe and start watching
            self.watcher.watch_section("general", callback)
            self.watcher.start_watching()
            
            # Wait for initial state to be loaded
            time.sleep(0.2)
            
            # Modify configuration file
            modified_config = self.initial_config.copy()
            modified_config["general"]["version"] = "2.0.0"
            
            with open(self.config_file, 'w') as f:
                json.dump(modified_config, f, indent=2)
            
            # Wait for polling to detect change
            time.sleep(0.3)
            
            # Verify callback was called
            assert callback.called
            
            # Verify event details
            call_args = callback.call_args[0][0]
            assert isinstance(call_args, ConfigurationChangeEvent)
            assert call_args.section == "general"

    @pytest.mark.config
    @pytest.mark.unit
    def test_change_detection_algorithm(self):
        """Test configuration change detection algorithm"""
        old_config = {
            "section1": {
                "key1": "value1",
                "key2": "value2"
            },
            "section2": {
                "nested": {
                    "key": "nested_value"
                }
            }
        }
        
        new_config = {
            "section1": {
                "key1": "modified_value1",  # Modified
                "key3": "new_value"         # Added
                # key2 removed
            },
            "section2": {
                "nested": {
                    "key": "nested_value"   # Unchanged
                }
            },
            "section3": {                   # New section
                "new_key": "new_section_value"
            }
        }
        
        changes = self.watcher._detect_changes(old_config, new_config)
        
        # Should detect modifications, additions, and removals
        assert len(changes) > 0
        
        # Check for specific change types
        change_types = [change['type'] for change in changes]
        assert 'modified' in change_types
        assert 'added' in change_types
        assert 'removed' in change_types

    @pytest.mark.config
    @pytest.mark.unit
    def test_subscription_matching(self):
        """Test subscription matching against events"""
        # Create test event
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="version",
            old_value="1.0.0",
            new_value="2.0.0",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        # Test section subscription matching
        section_subscription = WatchSubscription(
            watch_id="section_watch",
            pattern="general",
            callback=Mock(),
            watch_type="section",
            created_at=datetime.now()
        )
        
        assert self.watcher._subscription_matches_event(section_subscription, event)
        
        # Test key subscription matching
        key_subscription = WatchSubscription(
            watch_id="key_watch",
            pattern="general.version",
            callback=Mock(),
            watch_type="key",
            created_at=datetime.now()
        )
        
        assert self.watcher._subscription_matches_event(key_subscription, event)
        
        # Test non-matching subscription
        non_matching_subscription = WatchSubscription(
            watch_id="non_matching",
            pattern="backup",
            callback=Mock(),
            watch_type="section",
            created_at=datetime.now()
        )
        
        assert not self.watcher._subscription_matches_event(non_matching_subscription, event)

    @pytest.mark.config
    @pytest.mark.unit
    def test_change_history(self):
        """Test change event history tracking"""
        # Initially no history
        history = self.watcher.get_change_history()
        assert len(history) == 0
        
        # Create and process test event
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="version",
            old_value="1.0.0",
            new_value="2.0.0",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        self.watcher._process_change_event(event)
        
        # Should now have history
        history = self.watcher.get_change_history()
        assert len(history) == 1
        assert history[0].event_id == "test_event"

    @pytest.mark.config
    @pytest.mark.unit
    def test_change_history_limit(self):
        """Test change history size limiting"""
        # Add many events to test history limiting
        for i in range(1200):  # More than the 1000 limit
            event = ConfigurationChangeEvent(
                event_id=f"event_{i}",
                timestamp=datetime.now(),
                section="test",
                key="key",
                old_value=f"old_{i}",
                new_value=f"new_{i}",
                source="test",
                user_context=None,
                transaction_id=None
            )
            self.watcher._process_change_event(event)
        
        # History should be limited to 100 (default limit in get_change_history)
        history = self.watcher.get_change_history()
        assert len(history) == 100
        
        # Should contain the most recent events
        assert history[-1].event_id == "event_1199"

    @pytest.mark.config
    @pytest.mark.unit
    def test_watch_statistics(self):
        """Test watch statistics collection"""
        stats = self.watcher.get_watch_statistics()
        
        # Check basic statistics
        assert 'subscription_count' in stats
        assert 'history_count' in stats
        assert 'is_watching' in stats
        assert 'monitoring_method' in stats
        assert 'config_file' in stats
        
        assert stats['subscription_count'] == 0
        assert stats['is_watching'] is False
        assert str(self.config_file) in stats['config_file']

    @pytest.mark.config
    @pytest.mark.unit
    def test_statistics_after_activity(self):
        """Test statistics after watcher activity"""
        callback = Mock()
        
        # Add subscription
        self.watcher.watch_section("general", callback)
        
        # Process some events
        for i in range(3):
            event = ConfigurationChangeEvent(
                event_id=f"event_{i}",
                timestamp=datetime.now(),
                section="general",
                key="test",
                old_value=f"old_{i}",
                new_value=f"new_{i}",
                source="test",
                user_context=None,
                transaction_id=None
            )
            self.watcher._process_change_event(event)
        
        stats = self.watcher.get_watch_statistics()
        
        assert stats['subscription_count'] == 1
        assert stats['history_count'] == 3
        assert stats['events_processed'] == 3
        assert stats['notifications_sent'] == 3  # One notification per event

    @pytest.mark.config
    @pytest.mark.unit
    def test_callback_error_handling(self):
        """Test error handling in subscription callbacks"""
        # Create callback that raises exception
        error_callback = Mock(side_effect=Exception("Callback error"))
        
        # Subscribe with error callback
        self.watcher.watch_section("general", error_callback)
        
        # Process event
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="test",
            old_value="old",
            new_value="new",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        # Should not raise exception, but should increment error count
        self.watcher._process_change_event(event)
        
        stats = self.watcher.get_watch_statistics()
        assert stats['errors'] > 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_multiple_subscriptions_same_section(self):
        """Test multiple subscriptions to the same section"""
        callback1 = Mock()
        callback2 = Mock()
        
        # Subscribe with multiple callbacks
        watch_id1 = self.watcher.watch_section("general", callback1)
        watch_id2 = self.watcher.watch_section("general", callback2)
        
        assert watch_id1 != watch_id2
        assert len(self.watcher._subscriptions) == 2
        
        # Process event
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="test",
            old_value="old",
            new_value="new",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        self.watcher._process_change_event(event)
        
        # Both callbacks should be called
        assert callback1.called
        assert callback2.called

    @pytest.mark.config
    @pytest.mark.unit
    def test_nested_key_watching(self):
        """Test watching nested configuration keys"""
        callback = Mock()
        
        # Watch nested key
        self.watcher.watch_key("general.nested.deep_key", callback)
        
        # Create event for nested key
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="nested.deep_key",
            old_value="old_value",
            new_value="new_value",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        # Find matching subscriptions
        matching = self.watcher._find_matching_subscriptions(event)
        assert len(matching) == 1

    @pytest.mark.config
    @pytest.mark.unit
    def test_key_prefix_matching(self):
        """Test key subscription prefix matching"""
        callback = Mock()
        
        # Watch parent key
        self.watcher.watch_key("general.parent", callback)
        
        # Create event for child key
        event = ConfigurationChangeEvent(
            event_id="test_event",
            timestamp=datetime.now(),
            section="general",
            key="parent.child",
            old_value="old_value",
            new_value="new_value",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        # Should match due to prefix matching
        matching = self.watcher._find_matching_subscriptions(event)
        assert len(matching) == 1

    @pytest.mark.config
    @pytest.mark.unit
    def test_nonexistent_config_file(self):
        """Test watcher behavior with non-existent config file"""
        nonexistent_file = self.temp_dir / "nonexistent.json"
        watcher = ConfigurationWatcher(nonexistent_file, polling_interval=0.1)
        
        # Should be able to start watching even if file doesn't exist
        watcher.start_watching()
        assert watcher.is_watching()
        
        watcher.stop_watching()

    @pytest.mark.config
    @pytest.mark.unit
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in config file"""
        callback = Mock()
        
        # Subscribe to changes
        self.watcher.watch_section("general", callback)
        
        # Force polling mode and start watching
        with patch.object(self.watcher, '_use_watchdog', False):
            self.watcher.start_watching()
            time.sleep(0.1)
            
            # Write invalid JSON
            with open(self.config_file, 'w') as f:
                f.write("invalid json content")
            
            # Wait for polling
            time.sleep(0.3)
            
            # Should handle gracefully without crashing
            stats = self.watcher.get_watch_statistics()
            # Error count may increase due to JSON parsing error
            assert 'errors' in stats

    @pytest.mark.config
    @pytest.mark.unit
    @patch('TimeLocker.config.configuration_watcher.HAS_WATCHDOG', False)
    def test_polling_fallback(self):
        """Test fallback to polling when watchdog is not available"""
        watcher = ConfigurationWatcher(self.config_file, polling_interval=0.1)
        
        # Should use polling mode
        assert not watcher._use_watchdog
        
        # Should still work normally
        watcher.start_watching()
        assert watcher.is_watching()
        
        stats = watcher.get_watch_statistics()
        assert stats['monitoring_method'] == 'polling'
        
        watcher.stop_watching()

    @pytest.mark.config
    @pytest.mark.unit
    def test_watchdog_fallback_on_error(self):
        """Test fallback to polling when watchdog fails"""
        with patch('TimeLocker.config.configuration_watcher.Observer') as mock_observer:
            # Make Observer initialization fail
            mock_observer.side_effect = Exception("Watchdog failed")
            
            watcher = ConfigurationWatcher(self.config_file, polling_interval=0.1)
            watcher.start_watching()
            
            # Should fall back to polling
            stats = watcher.get_watch_statistics()
            assert stats['monitoring_method'] == 'polling'
            
            watcher.stop_watching()

    @pytest.mark.config
    @pytest.mark.unit
    def test_event_queue_processing(self):
        """Test event queue processing"""
        callback = Mock()
        
        # Subscribe to changes
        self.watcher.watch_section("general", callback)
        
        # Start watching to initialize event processing
        self.watcher.start_watching()
        
        # Manually queue an event
        event = ConfigurationChangeEvent(
            event_id="queued_event",
            timestamp=datetime.now(),
            section="general",
            key="test",
            old_value="old",
            new_value="new",
            source="test",
            user_context=None,
            transaction_id=None
        )
        
        self.watcher._event_queue.put(event)
        
        # Wait for processing
        time.sleep(0.2)
        
        # Callback should be called
        assert callback.called

    @pytest.mark.config
    @pytest.mark.unit
    def test_thread_cleanup_on_stop(self):
        """Test proper thread cleanup when stopping watcher"""
        self.watcher.start_watching()
        
        # Verify threads are running
        assert self.watcher._processing_thread is not None
        assert self.watcher._processing_thread.is_alive()
        
        self.watcher.stop_watching()
        
        # Threads should be stopped and cleaned up
        if self.watcher._processing_thread:
            assert not self.watcher._processing_thread.is_alive()
        if self.watcher._polling_thread:
            assert not self.watcher._polling_thread.is_alive()

    @pytest.mark.config
    @pytest.mark.unit
    def test_concurrent_subscription_management(self):
        """Test thread-safe subscription management"""
        callbacks = [Mock() for _ in range(10)]
        watch_ids = []
        
        def add_subscription(callback):
            watch_id = self.watcher.watch_section("general", callback)
            watch_ids.append(watch_id)
        
        # Add subscriptions concurrently
        threads = []
        for callback in callbacks:
            thread = threading.Thread(target=add_subscription, args=(callback,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All subscriptions should be added
        assert len(self.watcher._subscriptions) == 10
        assert len(watch_ids) == 10
        assert len(set(watch_ids)) == 10  # All unique