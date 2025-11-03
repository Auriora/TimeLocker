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

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfigurationChangeEvent:
    """Configuration change event data"""
    event_id: str
    timestamp: datetime
    section: str
    key: Optional[str]
    old_value: Any
    new_value: Any
    source: str
    user_context: Optional[str]
    transaction_id: Optional[str]


class IConfigurationWatcher(ABC):
    """
    Abstract interface for configuration change monitoring.
    
    This interface provides file system watching and change notification
    capabilities, following the Single Responsibility Principle by focusing
    solely on change detection and notification.
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def unwatch(self, watch_id: str) -> None:
        """
        Remove a configuration watch.
        
        Args:
            watch_id: Watch identifier to remove
            
        Raises:
            ConfigurationWatchError: If watch cannot be removed
        """
        pass

    @abstractmethod
    def start_watching(self) -> None:
        """
        Start the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be started
        """
        pass

    @abstractmethod
    def stop_watching(self) -> None:
        """
        Stop the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be stopped
        """
        pass

    @abstractmethod
    def get_change_history(self, limit: int = 100) -> List[ConfigurationChangeEvent]:
        """
        Get recent configuration change history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent change events
        """
        pass

    @abstractmethod
    def is_watching(self) -> bool:
        """
        Check if the watcher is currently active.
        
        Returns:
            True if watching is active
        """
        pass

    @abstractmethod
    def get_watch_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configuration watching.
        
        Returns:
            Statistics including watch count, event count, etc.
        """
        pass