"""
Configuration watcher for TimeLocker.

This module provides file system monitoring and change notification capabilities
for configuration files, following the Single Responsibility Principle by
focusing solely on change detection and notification.
"""

import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from queue import Queue, Empty

from ..interfaces.configuration_watcher import IConfigurationWatcher, ConfigurationChangeEvent
from ..interfaces.exceptions import ConfigurationWatchError, ConfigurationWatchStartupError

logger = logging.getLogger(__name__)

# Try to import watchdog for file system monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog library not available, using polling fallback")


@dataclass
class WatchSubscription:
    """Configuration watch subscription"""
    watch_id: str
    pattern: str  # section name or key pattern
    callback: Callable[[ConfigurationChangeEvent], None]
    watch_type: str  # 'section' or 'key'
    created_at: datetime


class ConfigurationFileHandler(FileSystemEventHandler):
    """File system event handler for configuration changes"""
    
    def __init__(self, watcher: 'ConfigurationWatcher'):
        self.watcher = watcher
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.watcher._handle_file_change(Path(event.src_path))
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.watcher._handle_file_change(Path(event.src_path))


class ConfigurationWatcher(IConfigurationWatcher):
    """
    Configuration change watcher with file system monitoring.
    
    Provides file system watching with fallback polling, change event
    queuing, and subscription management for configuration monitoring.
    """

    def __init__(self, config_file: Path, polling_interval: float = 1.0):
        """
        Initialize the configuration watcher.
        
        Args:
            config_file: Configuration file to watch
            polling_interval: Polling interval in seconds for fallback mode
        """
        self.config_file = config_file
        self.polling_interval = polling_interval
        
        # Watch subscriptions
        self._subscriptions: Dict[str, WatchSubscription] = {}
        self._subscriptions_lock = threading.RLock()
        
        # File system monitoring
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[ConfigurationFileHandler] = None
        self._use_watchdog = HAS_WATCHDOG
        
        # Polling fallback
        self._polling_thread: Optional[threading.Thread] = None
        self._polling_stop_event = threading.Event()
        self._last_modified: Optional[datetime] = None
        self._last_config: Optional[Dict[str, Any]] = None
        
        # Change history and event queue
        self._change_history: List[ConfigurationChangeEvent] = []
        self._change_history_lock = threading.RLock()
        self._event_queue: Queue = Queue()
        
        # Processing thread
        self._processing_thread: Optional[threading.Thread] = None
        self._processing_stop_event = threading.Event()
        
        # Statistics
        self._stats = {
            'events_processed': 0,
            'notifications_sent': 0,
            'errors': 0,
            'started_at': None,
            'last_event_at': None
        }
        
        # State
        self._is_watching = False

    def watch_section(self, section: str, callback: Callable[[ConfigurationChangeEvent], None]) -> str:
        """
        Watch for changes to a specific configuration section.
        
        Args:
            section: Section name to watch
            callback: Function to call when section changes
            
        Returns:
            Watch identifier for later removal
            
        Raises:
            ConfigurationWatchError: If watching cannot be established
        """
        try:
            watch_id = str(uuid.uuid4())
            
            subscription = WatchSubscription(
                watch_id=watch_id,
                pattern=section,
                callback=callback,
                watch_type='section',
                created_at=datetime.now()
            )
            
            with self._subscriptions_lock:
                self._subscriptions[watch_id] = subscription
            
            logger.debug(f"Added section watch for '{section}' with ID {watch_id}")
            return watch_id
            
        except Exception as e:
            logger.error(f"Failed to create section watch for '{section}': {e}")
            raise ConfigurationWatchError(f"Failed to create section watch: {e}")

    def watch_key(self, key: str, callback: Callable[[ConfigurationChangeEvent], None]) -> str:
        """
        Watch for changes to a specific configuration key.
        
        Args:
            key: Configuration key to watch (supports dot notation)
            callback: Function to call when key changes
            
        Returns:
            Watch identifier for later removal
            
        Raises:
            ConfigurationWatchError: If watching cannot be established
        """
        try:
            watch_id = str(uuid.uuid4())
            
            subscription = WatchSubscription(
                watch_id=watch_id,
                pattern=key,
                callback=callback,
                watch_type='key',
                created_at=datetime.now()
            )
            
            with self._subscriptions_lock:
                self._subscriptions[watch_id] = subscription
            
            logger.debug(f"Added key watch for '{key}' with ID {watch_id}")
            return watch_id
            
        except Exception as e:
            logger.error(f"Failed to create key watch for '{key}': {e}")
            raise ConfigurationWatchError(f"Failed to create key watch: {e}")

    def unwatch(self, watch_id: str) -> None:
        """
        Remove a configuration watch.
        
        Args:
            watch_id: Watch identifier to remove
            
        Raises:
            ConfigurationWatchError: If watch cannot be removed
        """
        try:
            with self._subscriptions_lock:
                if watch_id in self._subscriptions:
                    del self._subscriptions[watch_id]
                    logger.debug(f"Removed watch with ID {watch_id}")
                else:
                    logger.warning(f"Watch ID not found: {watch_id}")
                    
        except Exception as e:
            logger.error(f"Failed to remove watch {watch_id}: {e}")
            raise ConfigurationWatchError(f"Failed to remove watch: {e}")

    def start_watching(self) -> None:
        """
        Start the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be started
        """
        try:
            if self._is_watching:
                logger.warning("Configuration watcher is already running")
                return
            
            # Initialize last known state
            self._load_initial_state()
            
            # Start file system monitoring
            if self._use_watchdog:
                self._start_watchdog_monitoring()
            else:
                self._start_polling_monitoring()
            
            # Start event processing thread
            self._start_event_processing()
            
            self._is_watching = True
            self._stats['started_at'] = datetime.now()
            
            logger.info("Configuration watcher started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start configuration watcher: {e}")
            self._cleanup()
            raise ConfigurationWatchStartupError(f"Failed to start watcher: {e}")

    def stop_watching(self) -> None:
        """
        Stop the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be stopped
        """
        try:
            if not self._is_watching:
                return
            
            self._is_watching = False
            
            # Stop monitoring
            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=5.0)
            
            if self._polling_thread:
                self._polling_stop_event.set()
                self._polling_thread.join(timeout=5.0)
            
            # Stop event processing
            if self._processing_thread:
                self._processing_stop_event.set()
                self._processing_thread.join(timeout=5.0)
            
            self._cleanup()
            
            logger.info("Configuration watcher stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop configuration watcher: {e}")
            raise ConfigurationWatchError(f"Failed to stop watcher: {e}")

    def get_change_history(self, limit: int = 100) -> List[ConfigurationChangeEvent]:
        """
        Get recent configuration change history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent change events
        """
        with self._change_history_lock:
            return self._change_history[-limit:] if limit > 0 else self._change_history.copy()

    def is_watching(self) -> bool:
        """
        Check if the watcher is currently active.
        
        Returns:
            True if watching is active
        """
        return self._is_watching

    def get_watch_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configuration watching.
        
        Returns:
            Statistics including watch count, event count, etc.
        """
        with self._subscriptions_lock:
            subscription_count = len(self._subscriptions)
            
        with self._change_history_lock:
            history_count = len(self._change_history)
        
        stats = self._stats.copy()
        stats.update({
            'subscription_count': subscription_count,
            'history_count': history_count,
            'is_watching': self._is_watching,
            'monitoring_method': 'watchdog' if self._use_watchdog else 'polling',
            'config_file': str(self.config_file)
        })
        
        return stats

    # Private helper methods

    def _load_initial_state(self) -> None:
        """Load initial configuration state"""
        try:
            if self.config_file.exists():
                self._last_modified = datetime.fromtimestamp(self.config_file.stat().st_mtime)
                with open(self.config_file, 'r') as f:
                    self._last_config = json.load(f)
            else:
                self._last_modified = None
                self._last_config = {}
        except Exception as e:
            logger.warning(f"Failed to load initial configuration state: {e}")
            self._last_config = {}

    def _start_watchdog_monitoring(self) -> None:
        """Start watchdog-based file system monitoring"""
        try:
            self._observer = Observer()
            self._file_handler = ConfigurationFileHandler(self)
            
            # Watch the directory containing the config file
            watch_dir = self.config_file.parent
            self._observer.schedule(self._file_handler, str(watch_dir), recursive=False)
            self._observer.start()
            
            logger.debug("Started watchdog file system monitoring")
            
        except Exception as e:
            logger.warning(f"Failed to start watchdog monitoring, falling back to polling: {e}")
            self._use_watchdog = False
            self._start_polling_monitoring()

    def _start_polling_monitoring(self) -> None:
        """Start polling-based file monitoring"""
        self._polling_stop_event.clear()
        self._polling_thread = threading.Thread(
            target=self._polling_worker,
            name="ConfigWatcher-Polling",
            daemon=True
        )
        self._polling_thread.start()
        logger.debug("Started polling file system monitoring")

    def _polling_worker(self) -> None:
        """Polling worker thread"""
        while not self._polling_stop_event.wait(self.polling_interval):
            try:
                if self.config_file.exists():
                    current_modified = datetime.fromtimestamp(self.config_file.stat().st_mtime)
                    if self._last_modified is None or current_modified > self._last_modified:
                        self._handle_file_change(self.config_file)
            except Exception as e:
                logger.error(f"Error in polling worker: {e}")
                self._stats['errors'] += 1

    def _start_event_processing(self) -> None:
        """Start event processing thread"""
        self._processing_stop_event.clear()
        self._processing_thread = threading.Thread(
            target=self._event_processing_worker,
            name="ConfigWatcher-EventProcessor",
            daemon=True
        )
        self._processing_thread.start()

    def _event_processing_worker(self) -> None:
        """Event processing worker thread"""
        while not self._processing_stop_event.is_set():
            try:
                # Process events from queue
                try:
                    event = self._event_queue.get(timeout=0.5)
                    self._process_change_event(event)
                    self._event_queue.task_done()
                except Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in event processing worker: {e}")
                self._stats['errors'] += 1

    def _handle_file_change(self, file_path: Path) -> None:
        """Handle file system change event"""
        try:
            if file_path != self.config_file:
                return
            
            # Load new configuration
            if not file_path.exists():
                new_config = {}
            else:
                with open(file_path, 'r') as f:
                    new_config = json.load(f)
            
            # Compare with last known state
            if self._last_config is not None:
                changes = self._detect_changes(self._last_config, new_config)
                
                # Create change events
                for change in changes:
                    event = ConfigurationChangeEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.now(),
                        section=change['section'],
                        key=change.get('key'),
                        old_value=change.get('old_value'),
                        new_value=change.get('new_value'),
                        source='file_system',
                        user_context=None,
                        transaction_id=None
                    )
                    
                    # Queue event for processing
                    self._event_queue.put(event)
            
            # Update last known state
            self._last_config = new_config
            self._last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            
        except Exception as e:
            logger.error(f"Error handling file change for {file_path}: {e}")
            self._stats['errors'] += 1

    def _detect_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect changes between configuration versions"""
        changes = []
        
        def compare_recursive(old_obj, new_obj, section="", key_path=""):
            if isinstance(old_obj, dict) and isinstance(new_obj, dict):
                all_keys = set(old_obj.keys()) | set(new_obj.keys())
                
                for key in all_keys:
                    current_section = section or key
                    current_key_path = f"{key_path}.{key}" if key_path else key
                    
                    if key not in old_obj:
                        # Key added
                        changes.append({
                            'type': 'added',
                            'section': current_section,
                            'key': current_key_path,
                            'new_value': new_obj[key]
                        })
                    elif key not in new_obj:
                        # Key removed
                        changes.append({
                            'type': 'removed',
                            'section': current_section,
                            'key': current_key_path,
                            'old_value': old_obj[key]
                        })
                    else:
                        # Key exists in both, check for changes
                        if section:  # We're inside a section
                            compare_recursive(old_obj[key], new_obj[key], section, current_key_path)
                        else:  # This is a top-level section
                            compare_recursive(old_obj[key], new_obj[key], key, "")
            else:
                # Direct value comparison
                if old_obj != new_obj:
                    changes.append({
                        'type': 'modified',
                        'section': section,
                        'key': key_path if key_path else None,
                        'old_value': old_obj,
                        'new_value': new_obj
                    })
        
        compare_recursive(old_config, new_config)
        return changes

    def _process_change_event(self, event: ConfigurationChangeEvent) -> None:
        """Process a configuration change event"""
        try:
            # Add to history
            with self._change_history_lock:
                self._change_history.append(event)
                # Keep history size manageable
                if len(self._change_history) > 1000:
                    self._change_history = self._change_history[-500:]
            
            # Notify subscribers
            matching_subscriptions = self._find_matching_subscriptions(event)
            
            for subscription in matching_subscriptions:
                try:
                    subscription.callback(event)
                    self._stats['notifications_sent'] += 1
                except Exception as e:
                    logger.error(f"Error in subscription callback {subscription.watch_id}: {e}")
                    self._stats['errors'] += 1
            
            self._stats['events_processed'] += 1
            self._stats['last_event_at'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing change event: {e}")
            self._stats['errors'] += 1

    def _find_matching_subscriptions(self, event: ConfigurationChangeEvent) -> List[WatchSubscription]:
        """Find subscriptions that match the change event"""
        matching = []
        
        with self._subscriptions_lock:
            for subscription in self._subscriptions.values():
                if self._subscription_matches_event(subscription, event):
                    matching.append(subscription)
        
        return matching

    def _subscription_matches_event(self, subscription: WatchSubscription, event: ConfigurationChangeEvent) -> bool:
        """Check if a subscription matches a change event"""
        if subscription.watch_type == 'section':
            return event.section == subscription.pattern
        
        elif subscription.watch_type == 'key':
            # For key watching, check if the event key matches the pattern
            if event.key is None:
                return False
            
            # Support exact match and prefix match for nested keys
            pattern = subscription.pattern
            event_key = f"{event.section}.{event.key}" if event.key else event.section
            
            return event_key == pattern or event_key.startswith(f"{pattern}.")
        
        return False

    def _cleanup(self) -> None:
        """Clean up resources"""
        self._observer = None
        self._file_handler = None
        self._polling_thread = None
        self._processing_thread = None