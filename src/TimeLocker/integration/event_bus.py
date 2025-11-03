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
Event Bus for TimeLocker Integration Architecture

This module provides the EventBus class that implements publish/subscribe messaging,
event filtering, routing, persistence, and correlation capabilities for the
TimeLocker integration architecture.
"""

import logging
import json
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any, Set, Union
from collections import defaultdict, deque
from dataclasses import asdict
import re

from ..interfaces.integration_data_models import Event
from ..interfaces.integration_exceptions import (
    EventBusError,
    EventPublishError,
    EventSubscriptionError,
    EventPersistenceError
)

logger = logging.getLogger(__name__)


class EventFilter:
    """
    Event filter for targeted subscriptions.
    
    Supports filtering by event type patterns, source patterns, priority levels,
    and custom filter functions.
    """
    
    def __init__(self, 
                 event_type_pattern: Optional[str] = None,
                 source_pattern: Optional[str] = None,
                 min_priority: Optional[int] = None,
                 max_age_seconds: Optional[float] = None,
                 custom_filter: Optional[Callable[[Event], bool]] = None):
        """
        Initialize event filter.
        
        Args:
            event_type_pattern: Regex pattern for event types (e.g., "backup.*")
            source_pattern: Regex pattern for event sources
            min_priority: Minimum priority level to match
            max_age_seconds: Maximum age in seconds for events to match
            custom_filter: Custom filter function that takes Event and returns bool
        """
        self.event_type_pattern = re.compile(event_type_pattern) if event_type_pattern else None
        self.source_pattern = re.compile(source_pattern) if source_pattern else None
        self.min_priority = min_priority
        self.max_age_seconds = max_age_seconds
        self.custom_filter = custom_filter
    
    def matches(self, event: Event) -> bool:
        """
        Check if event matches this filter.
        
        Args:
            event: Event to check
            
        Returns:
            bool: True if event matches filter criteria
        """
        # Check event type pattern
        if self.event_type_pattern and not self.event_type_pattern.match(event.event_type):
            return False
        
        # Check source pattern
        if self.source_pattern and not self.source_pattern.match(event.source):
            return False
        
        # Check minimum priority
        if self.min_priority is not None and event.priority < self.min_priority:
            return False
        
        # Check maximum age
        if self.max_age_seconds is not None:
            age = event.get_age_seconds()
            if age > self.max_age_seconds:
                return False
        
        # Check custom filter
        if self.custom_filter and not self.custom_filter(event):
            return False
        
        return True


class EventSubscription:
    """
    Event subscription with handler and filter information.
    """
    
    def __init__(self, 
                 subscription_id: str,
                 handler: Callable[[Event], None],
                 event_filter: Optional[EventFilter] = None,
                 subscriber_name: Optional[str] = None):
        """
        Initialize event subscription.
        
        Args:
            subscription_id: Unique identifier for the subscription
            handler: Function to call when matching events are published
            event_filter: Optional filter for targeted subscriptions
            subscriber_name: Optional name of the subscriber for debugging
        """
        self.subscription_id = subscription_id
        self.handler = handler
        self.event_filter = event_filter
        self.subscriber_name = subscriber_name or "unknown"
        self.created_at = datetime.now()
        self.event_count = 0
        self.last_event_at: Optional[datetime] = None
        self.error_count = 0
        self.last_error: Optional[str] = None
    
    def matches_event(self, event: Event) -> bool:
        """
        Check if this subscription matches the given event.
        
        Args:
            event: Event to check
            
        Returns:
            bool: True if subscription should receive this event
        """
        if self.event_filter is None:
            return True
        
        return self.event_filter.matches(event)
    
    def handle_event(self, event: Event) -> bool:
        """
        Handle an event with this subscription.
        
        Args:
            event: Event to handle
            
        Returns:
            bool: True if handled successfully, False if error occurred
        """
        try:
            self.handler(event)
            self.event_count += 1
            self.last_event_at = datetime.now()
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Error in event handler for subscription {self.subscription_id}: {e}")
            return False


class EventPersistence:
    """
    Event persistence mechanism for critical events and audit trails.
    """
    
    def __init__(self, storage_path: Path, max_events: int = 10000):
        """
        Initialize event persistence.
        
        Args:
            storage_path: Path to store persistent events
            max_events: Maximum number of events to keep in storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self._lock = threading.Lock()
        
        # Files for different event categories
        self.critical_events_file = self.storage_path / "critical_events.jsonl"
        self.audit_events_file = self.storage_path / "audit_events.jsonl"
        self.correlation_index_file = self.storage_path / "correlation_index.json"
        
        # Load correlation index
        self._correlation_index = self._load_correlation_index()
    
    def persist_event(self, event: Event, is_critical: bool = False) -> None:
        """
        Persist an event to storage.
        
        Args:
            event: Event to persist
            is_critical: Whether this is a critical event
            
        Raises:
            EventPersistenceError: If persistence fails
        """
        try:
            with self._lock:
                # Choose appropriate file
                target_file = self.critical_events_file if is_critical else self.audit_events_file
                
                # Append event to file
                event_data = event.to_dict()
                event_line = json.dumps(event_data) + "\n"
                
                with open(target_file, "a", encoding="utf-8") as f:
                    f.write(event_line)
                
                # Update correlation index if event has correlation ID
                if event.correlation_id:
                    self._update_correlation_index(event)
                
                # Rotate files if they get too large
                self._rotate_files_if_needed()
                
        except Exception as e:
            raise EventPersistenceError(f"Failed to persist event {event.event_id}: {e}", e)
    
    def get_events_by_correlation(self, correlation_id: str) -> List[Event]:
        """
        Get all events with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of events with the correlation ID
        """
        events = []
        
        try:
            with self._lock:
                # Check correlation index first
                if correlation_id not in self._correlation_index:
                    return events
                
                event_ids = self._correlation_index[correlation_id]
                
                # Search through both files
                for file_path in [self.critical_events_file, self.audit_events_file]:
                    if file_path.exists():
                        events.extend(self._search_file_for_events(file_path, event_ids))
                
        except Exception as e:
            logger.error(f"Error retrieving events by correlation {correlation_id}: {e}")
        
        return events
    
    def get_recent_events(self, hours: int = 24, event_type_pattern: Optional[str] = None) -> List[Event]:
        """
        Get recent events from storage.
        
        Args:
            hours: Number of hours back to search
            event_type_pattern: Optional regex pattern for event types
            
        Returns:
            List of recent events
        """
        events = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        pattern = re.compile(event_type_pattern) if event_type_pattern else None
        
        try:
            with self._lock:
                for file_path in [self.critical_events_file, self.audit_events_file]:
                    if file_path.exists():
                        events.extend(self._search_file_by_time(file_path, cutoff_time, pattern))
        
        except Exception as e:
            logger.error(f"Error retrieving recent events: {e}")
        
        return events
    
    def _load_correlation_index(self) -> Dict[str, List[str]]:
        """Load correlation index from storage."""
        try:
            if self.correlation_index_file.exists():
                with open(self.correlation_index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load correlation index: {e}")
        
        return {}
    
    def _save_correlation_index(self) -> None:
        """Save correlation index to storage."""
        try:
            with open(self.correlation_index_file, "w", encoding="utf-8") as f:
                json.dump(self._correlation_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save correlation index: {e}")
    
    def _update_correlation_index(self, event: Event) -> None:
        """Update correlation index with new event."""
        if event.correlation_id:
            if event.correlation_id not in self._correlation_index:
                self._correlation_index[event.correlation_id] = []
            
            if event.event_id not in self._correlation_index[event.correlation_id]:
                self._correlation_index[event.correlation_id].append(event.event_id)
                self._save_correlation_index()
    
    def _search_file_for_events(self, file_path: Path, event_ids: List[str]) -> List[Event]:
        """Search file for specific event IDs."""
        events = []
        event_id_set = set(event_ids)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        if event_data.get("event_id") in event_id_set:
                            events.append(Event.from_dict(event_data))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error searching file {file_path}: {e}")
        
        return events
    
    def _search_file_by_time(self, file_path: Path, cutoff_time: datetime, pattern: Optional[re.Pattern]) -> List[Event]:
        """Search file for events after cutoff time."""
        events = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event_data["timestamp"].replace('Z', '+00:00'))
                        
                        if event_time >= cutoff_time:
                            if pattern is None or pattern.match(event_data.get("event_type", "")):
                                events.append(Event.from_dict(event_data))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            logger.error(f"Error searching file by time {file_path}: {e}")
        
        return events
    
    def _rotate_files_if_needed(self) -> None:
        """Rotate files if they exceed maximum event count."""
        for file_path in [self.critical_events_file, self.audit_events_file]:
            if not file_path.exists():
                continue
            
            try:
                # Count lines in file
                with open(file_path, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                
                if line_count > self.max_events:
                    # Keep only the most recent events
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    # Keep last max_events/2 lines
                    keep_count = self.max_events // 2
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(lines[-keep_count:])
                    
                    logger.info(f"Rotated {file_path}, kept {keep_count} most recent events")
            
            except Exception as e:
                logger.error(f"Error rotating file {file_path}: {e}")


class DeadLetterQueue:
    """
    Dead letter queue for failed event processing.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize dead letter queue.
        
        Args:
            max_size: Maximum number of failed events to keep
        """
        self.max_size = max_size
        self._queue: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
    
    def add_failed_event(self, event: Event, subscription_id: str, error: str) -> None:
        """
        Add a failed event to the dead letter queue.
        
        Args:
            event: Event that failed processing
            subscription_id: ID of subscription that failed
            error: Error message
        """
        with self._lock:
            failed_entry = {
                "event": event,
                "subscription_id": subscription_id,
                "error": error,
                "failed_at": datetime.now(),
                "retry_count": 0
            }
            self._queue.append(failed_entry)
    
    def get_failed_events(self) -> List[Dict[str, Any]]:
        """
        Get all failed events from the queue.
        
        Returns:
            List of failed event entries
        """
        with self._lock:
            return list(self._queue)
    
    def retry_failed_events(self, event_bus: 'EventBus', max_retries: int = 3) -> int:
        """
        Retry failed events.
        
        Args:
            event_bus: EventBus instance to retry events on
            max_retries: Maximum number of retry attempts
            
        Returns:
            Number of events successfully retried
        """
        retried_count = 0
        
        with self._lock:
            # Process a copy to avoid modification during iteration
            failed_events = list(self._queue)
            self._queue.clear()
            
            for entry in failed_events:
                if entry["retry_count"] < max_retries:
                    try:
                        # Try to republish the event
                        event_bus.publish_event(entry["event"])
                        retried_count += 1
                        logger.info(f"Successfully retried event {entry['event'].event_id}")
                    except Exception as e:
                        # Add back to queue with incremented retry count
                        entry["retry_count"] += 1
                        entry["error"] = str(e)
                        self._queue.append(entry)
                        logger.warning(f"Retry failed for event {entry['event'].event_id}: {e}")
                else:
                    # Max retries exceeded, add back to queue
                    self._queue.append(entry)
                    logger.error(f"Max retries exceeded for event {entry['event'].event_id}")
        
        return retried_count
    
    def clear_old_entries(self, max_age_hours: int = 24) -> int:
        """
        Clear old entries from the dead letter queue.
        
        Args:
            max_age_hours: Maximum age in hours for entries to keep
            
        Returns:
            Number of entries cleared
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleared_count = 0
        
        with self._lock:
            original_size = len(self._queue)
            
            # Filter out old entries
            self._queue = deque(
                (entry for entry in self._queue if entry["failed_at"] >= cutoff_time),
                maxlen=self.max_size
            )
            
            cleared_count = original_size - len(self._queue)
        
        return cleared_count


class EventBus:
    """
    Event Bus for TimeLocker Integration Architecture.
    
    Provides publish/subscribe messaging with event filtering, routing,
    persistence, correlation, and error recovery capabilities.
    
    Requirements addressed:
    - 4.1: Event bus for publishing and subscribing to system events
    - 4.2: Event filtering and routing for targeted subscriptions
    - 4.3: Event persistence for critical events and audit trails
    - 4.4: Event correlation for linking related events
    - 4.5: Dead letter queues and error recovery mechanisms
    """
    
    def __init__(self, 
                 persistence_path: Optional[Path] = None,
                 enable_persistence: bool = True,
                 max_dead_letter_size: int = 1000):
        """
        Initialize the event bus.
        
        Args:
            persistence_path: Path for event persistence storage
            enable_persistence: Whether to enable event persistence
            max_dead_letter_size: Maximum size of dead letter queue
        """
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._subscriptions_by_type: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._is_shutdown = False
        
        # Event persistence
        self._enable_persistence = enable_persistence
        if enable_persistence and persistence_path:
            self._persistence = EventPersistence(persistence_path)
        else:
            self._persistence = None
        
        # Dead letter queue for failed events
        self._dead_letter_queue = DeadLetterQueue(max_dead_letter_size)
        
        # Statistics
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "events_failed": 0,
            "subscriptions_created": 0,
            "subscriptions_removed": 0
        }
        
        logger.info("EventBus initialized")
    
    def publish_event(self, event: Event, persist_critical: bool = True) -> None:
        """
        Publish an event to all matching subscribers.
        
        Args:
            event: Event to publish
            persist_critical: Whether to persist critical events (priority >= 5)
            
        Raises:
            EventPublishError: If event publishing fails
        """
        if self._is_shutdown:
            raise EventPublishError("EventBus is shutdown")
        
        if not isinstance(event, Event):
            raise EventPublishError("Invalid event type")
        
        try:
            with self._lock:
                self._stats["events_published"] += 1
                
                # Persist critical events if enabled
                if (self._persistence and persist_critical and 
                    event.priority >= 5):
                    try:
                        self._persistence.persist_event(event, is_critical=True)
                    except EventPersistenceError as e:
                        logger.error(f"Failed to persist critical event {event.event_id}: {e}")
                
                # Persist all events for audit if enabled
                if self._persistence:
                    try:
                        self._persistence.persist_event(event, is_critical=False)
                    except EventPersistenceError as e:
                        logger.warning(f"Failed to persist event for audit {event.event_id}: {e}")
                
                # Find matching subscriptions
                matching_subscriptions = self._find_matching_subscriptions(event)
                
                # Deliver to subscribers
                delivered_count = 0
                failed_count = 0
                
                for subscription in matching_subscriptions:
                    try:
                        success = subscription.handle_event(event)
                        if success:
                            delivered_count += 1
                        else:
                            failed_count += 1
                            # Add to dead letter queue
                            self._dead_letter_queue.add_failed_event(
                                event, 
                                subscription.subscription_id,
                                subscription.last_error or "Unknown error"
                            )
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Unexpected error delivering event to {subscription.subscription_id}: {e}")
                        self._dead_letter_queue.add_failed_event(event, subscription.subscription_id, str(e))
                
                self._stats["events_delivered"] += delivered_count
                self._stats["events_failed"] += failed_count
                
                logger.debug(f"Published event {event.event_id} to {delivered_count} subscribers, {failed_count} failed")
        
        except Exception as e:
            # Create enhanced error with context
            error_context = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'source': event.source,
                'subscriber_count': len(matching_subscriptions) if 'matching_subscriptions' in locals() else 0
            }
            
            enhanced_error = EventPublishError(f"Failed to publish event {event.event_id}: {e}", e)
            enhanced_error.add_note(f"Event context: {error_context}")
            raise enhanced_error
    
    def subscribe_event(self, 
                       event_type_pattern: Optional[str] = None,
                       handler: Optional[Callable[[Event], None]] = None,
                       source_pattern: Optional[str] = None,
                       min_priority: Optional[int] = None,
                       max_age_seconds: Optional[float] = None,
                       custom_filter: Optional[Callable[[Event], bool]] = None,
                       subscriber_name: Optional[str] = None) -> str:
        """
        Subscribe to events with optional filtering.
        
        Args:
            event_type_pattern: Regex pattern for event types to subscribe to
            handler: Function to call when matching events are published
            source_pattern: Regex pattern for event sources
            min_priority: Minimum priority level to receive
            max_age_seconds: Maximum age for events to receive
            custom_filter: Custom filter function
            subscriber_name: Optional name for the subscriber
            
        Returns:
            Subscription ID that can be used to unsubscribe
            
        Raises:
            EventSubscriptionError: If subscription fails
        """
        if self._is_shutdown:
            raise EventSubscriptionError("EventBus is shutdown")
        
        if handler is None:
            raise EventSubscriptionError("Handler function is required")
        
        try:
            with self._lock:
                subscription_id = str(uuid.uuid4())
                
                # Create event filter if any criteria specified
                event_filter = None
                if any([event_type_pattern, source_pattern, min_priority is not None, 
                       max_age_seconds is not None, custom_filter]):
                    event_filter = EventFilter(
                        event_type_pattern=event_type_pattern,
                        source_pattern=source_pattern,
                        min_priority=min_priority,
                        max_age_seconds=max_age_seconds,
                        custom_filter=custom_filter
                    )
                
                # Create subscription
                subscription = EventSubscription(
                    subscription_id=subscription_id,
                    handler=handler,
                    event_filter=event_filter,
                    subscriber_name=subscriber_name
                )
                
                # Store subscription
                self._subscriptions[subscription_id] = subscription
                
                # Index by event type pattern for faster lookup
                if event_type_pattern:
                    self._subscriptions_by_type[event_type_pattern].add(subscription_id)
                else:
                    # Wildcard subscription
                    self._subscriptions_by_type["*"].add(subscription_id)
                
                self._stats["subscriptions_created"] += 1
                
                logger.debug(f"Created subscription {subscription_id} for {subscriber_name or 'unknown'}")
                
                return subscription_id
        
        except Exception as e:
            # Create enhanced error with context
            subscription_context = {
                'event_type_pattern': event_type_pattern,
                'subscriber_name': subscriber_name,
                'has_custom_filter': custom_filter is not None
            }
            
            enhanced_error = EventSubscriptionError(f"Failed to create subscription: {e}", e)
            enhanced_error.add_note(f"Subscription context: {subscription_context}")
            raise enhanced_error
    
    def unsubscribe_event(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was removed, False if not found
        """
        try:
            with self._lock:
                if subscription_id not in self._subscriptions:
                    return False
                
                subscription = self._subscriptions[subscription_id]
                
                # Remove from main storage
                del self._subscriptions[subscription_id]
                
                # Remove from type index
                for event_type, subscription_ids in self._subscriptions_by_type.items():
                    subscription_ids.discard(subscription_id)
                
                # Clean up empty type entries
                empty_types = [t for t, ids in self._subscriptions_by_type.items() if not ids]
                for empty_type in empty_types:
                    del self._subscriptions_by_type[empty_type]
                
                self._stats["subscriptions_removed"] += 1
                
                logger.debug(f"Removed subscription {subscription_id}")
                
                return True
        
        except Exception as e:
            logger.error(f"Error removing subscription {subscription_id}: {e}")
            return False
    
    def get_events_by_correlation(self, correlation_id: str) -> List[Event]:
        """
        Get all events with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of correlated events
        """
        if not self._persistence:
            logger.warning("Event persistence not enabled, cannot retrieve correlated events")
            return []
        
        return self._persistence.get_events_by_correlation(correlation_id)
    
    def get_recent_events(self, hours: int = 24, event_type_pattern: Optional[str] = None) -> List[Event]:
        """
        Get recent events from persistence.
        
        Args:
            hours: Number of hours back to search
            event_type_pattern: Optional regex pattern for event types
            
        Returns:
            List of recent events
        """
        if not self._persistence:
            logger.warning("Event persistence not enabled, cannot retrieve recent events")
            return []
        
        return self._persistence.get_recent_events(hours, event_type_pattern)
    
    def get_subscription_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all active subscriptions.
        
        Returns:
            Dictionary with subscription information
        """
        with self._lock:
            info = {}
            for sub_id, subscription in self._subscriptions.items():
                info[sub_id] = {
                    "subscriber_name": subscription.subscriber_name,
                    "created_at": subscription.created_at.isoformat(),
                    "event_count": subscription.event_count,
                    "last_event_at": subscription.last_event_at.isoformat() if subscription.last_event_at else None,
                    "error_count": subscription.error_count,
                    "last_error": subscription.last_error,
                    "has_filter": subscription.event_filter is not None
                }
            return info
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                "active_subscriptions": len(self._subscriptions),
                "dead_letter_queue_size": len(self._dead_letter_queue.get_failed_events()),
                "persistence_enabled": self._persistence is not None,
                "is_shutdown": self._is_shutdown
            })
            return stats
    
    def retry_failed_events(self, max_retries: int = 3) -> int:
        """
        Retry events in the dead letter queue.
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Number of events successfully retried
        """
        return self._dead_letter_queue.retry_failed_events(self, max_retries)
    
    def clear_old_failed_events(self, max_age_hours: int = 24) -> int:
        """
        Clear old failed events from dead letter queue.
        
        Args:
            max_age_hours: Maximum age in hours for entries to keep
            
        Returns:
            Number of entries cleared
        """
        return self._dead_letter_queue.clear_old_entries(max_age_hours)
    
    def shutdown(self) -> None:
        """
        Shutdown the event bus and clean up resources.
        """
        with self._lock:
            if self._is_shutdown:
                return
            
            self._is_shutdown = True
            
            # Clear all subscriptions
            self._subscriptions.clear()
            self._subscriptions_by_type.clear()
            
            logger.info("EventBus shutdown complete")
    
    def _find_matching_subscriptions(self, event: Event) -> List[EventSubscription]:
        """
        Find subscriptions that match the given event.
        
        Args:
            event: Event to match against subscriptions
            
        Returns:
            List of matching subscriptions
        """
        matching = []
        
        # Check wildcard subscriptions first
        wildcard_ids = self._subscriptions_by_type.get("*", set())
        for sub_id in wildcard_ids:
            subscription = self._subscriptions.get(sub_id)
            if subscription and subscription.matches_event(event):
                matching.append(subscription)
        
        # Check type-specific subscriptions
        for pattern, subscription_ids in self._subscriptions_by_type.items():
            if pattern == "*":
                continue  # Already handled
            
            try:
                if re.match(pattern, event.event_type):
                    for sub_id in subscription_ids:
                        subscription = self._subscriptions.get(sub_id)
                        if subscription and subscription.matches_event(event):
                            matching.append(subscription)
            except re.error:
                # Invalid regex pattern, skip
                logger.warning(f"Invalid regex pattern in subscription: {pattern}")
                continue
        
        return matching