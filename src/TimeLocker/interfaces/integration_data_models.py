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
Integration Data Models for TimeLocker Service Architecture

This module defines the core data models used in the TimeLocker integration
architecture, including service context and event system data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from ..config import ConfigurationManager


@dataclass
class ServiceContext:
    """
    Runtime context information available to services during execution.
    
    This data model provides services with access to core system components
    and configuration information needed for proper operation within the
    TimeLocker integration architecture.
    
    Requirements addressed:
    - 6.1: Service context containing configuration and runtime state
    - 6.2: Context inheritance for child operations
    - 6.3: Context validation for required information
    """
    
    config_manager: 'ConfigurationManager'
    """Configuration manager for accessing system configuration"""
    
    event_bus: Any  # Will be typed properly when EventBus is implemented
    """Event bus for publishing and subscribing to system events"""
    
    service_registry: Any  # Will be typed properly when ServiceRegistry is implemented
    """Service registry for service discovery and registration"""
    
    user_context: Optional[Dict[str, Any]] = None
    """Optional user-specific context information"""
    
    operation_id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for the current operation context"""
    
    parent_context: Optional['ServiceContext'] = None
    """Reference to parent context for context inheritance"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the service context"""
    
    def __post_init__(self):
        """Validate service context after initialization"""
        if self.config_manager is None:
            raise ValueError("ServiceContext requires a valid config_manager")
        
        if self.event_bus is None:
            raise ValueError("ServiceContext requires a valid event_bus")
        
        if self.service_registry is None:
            raise ValueError("ServiceContext requires a valid service_registry")
    
    def create_child_context(self, **kwargs) -> 'ServiceContext':
        """
        Create a child context that inherits from this context.
        
        Child contexts inherit configuration and core components from the parent
        while allowing override of specific values. This supports context
        inheritance for nested operations.
        
        Args:
            **kwargs: Values to override in the child context
            
        Returns:
            ServiceContext: New child context with inheritance
        """
        child_data = {
            'config_manager': self.config_manager,
            'event_bus': self.event_bus,
            'service_registry': self.service_registry,
            'user_context': self.user_context.copy() if self.user_context else None,
            'parent_context': self,
            'metadata': self.metadata.copy()
        }
        
        # Override with provided values
        child_data.update(kwargs)
        
        return ServiceContext(**child_data)
    
    def get_inherited_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from this context or inherited from parent contexts.
        
        This method searches up the context hierarchy to find the requested
        value, supporting context inheritance patterns.
        
        Args:
            key: Key to search for
            default: Default value if key is not found
            
        Returns:
            Any: Value from context hierarchy or default
        """
        # Check current context metadata
        if key in self.metadata:
            return self.metadata[key]
        
        # Check user context
        if self.user_context and key in self.user_context:
            return self.user_context[key]
        
        # Check parent context recursively
        if self.parent_context:
            return self.parent_context.get_inherited_value(key, default)
        
        return default
    
    def cleanup(self) -> None:
        """
        Clean up context resources and sensitive information.
        
        This method should be called when the context is no longer needed
        to prevent memory leaks and credential exposure.
        """
        # Clear sensitive user context information
        if self.user_context:
            # Remove any credential-related information
            sensitive_keys = ['password', 'token', 'api_key', 'secret']
            for key in list(self.user_context.keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    del self.user_context[key]
        
        # Clear metadata
        self.metadata.clear()
        
        # Don't clear parent reference to avoid breaking inheritance chain


@dataclass
class Event:
    """
    Event data model for the TimeLocker event system.
    
    This data model represents events that flow through the TimeLocker event
    bus, enabling loosely coupled communication between system components.
    
    Requirements addressed:
    - 4.1: Event bus for publishing and subscribing to system events
    - 4.4: Event correlation capabilities for linking related events
    """
    
    event_type: str
    """Type identifier for the event (e.g., 'backup.completed', 'config.changed')"""
    
    source: str
    """Source component that generated the event"""
    
    timestamp: datetime
    """When the event was created"""
    
    data: Dict[str, Any]
    """Event payload data"""
    
    correlation_id: Optional[str] = None
    """Optional correlation ID for linking related events"""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this event"""
    
    priority: int = 0
    """Event priority (higher numbers = higher priority)"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional event metadata"""
    
    def __post_init__(self):
        """Validate event data after initialization"""
        if not self.event_type:
            raise ValueError("Event requires a valid event_type")
        
        if not self.source:
            raise ValueError("Event requires a valid source")
        
        if self.data is None:
            self.data = {}
    
    def add_correlation(self, correlation_id: str) -> None:
        """
        Add correlation ID to link this event with related events.
        
        Args:
            correlation_id: Correlation identifier to add
        """
        self.correlation_id = correlation_id
        
        # Also add to metadata for searchability
        if 'correlations' not in self.metadata:
            self.metadata['correlations'] = []
        
        if correlation_id not in self.metadata['correlations']:
            self.metadata['correlations'].append(correlation_id)
    
    def is_correlated_with(self, other_event: 'Event') -> bool:
        """
        Check if this event is correlated with another event.
        
        Args:
            other_event: Event to check correlation with
            
        Returns:
            bool: True if events are correlated, False otherwise
        """
        if not self.correlation_id or not other_event.correlation_id:
            return False
        
        return self.correlation_id == other_event.correlation_id
    
    def get_age_seconds(self) -> float:
        """
        Get the age of this event in seconds.
        
        Returns:
            float: Age in seconds since event creation
        """
        return (datetime.now() - self.timestamp).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the event
        """
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'priority': self.priority,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        Create event from dictionary representation.
        
        Args:
            data: Dictionary containing event data
            
        Returns:
            Event: Event instance created from dictionary
        """
        # Parse timestamp
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            event_type=data['event_type'],
            source=data['source'],
            timestamp=timestamp,
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            event_id=data.get('event_id', str(uuid.uuid4())),
            priority=data.get('priority', 0),
            metadata=data.get('metadata', {})
        )