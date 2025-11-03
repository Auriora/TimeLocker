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
from typing import Dict, Any, List, Optional
from pathlib import Path


class IConfigurationStore(ABC):
    """
    Abstract interface for configuration storage backends.
    
    This interface provides atomic operations, locking, and backup capabilities
    for configuration persistence, following the Single Responsibility Principle
    by focusing solely on storage operations.
    """

    @abstractmethod
    def read_section(self, section: str) -> Dict[str, Any]:
        """
        Read a specific configuration section.
        
        Args:
            section: Section name to read
            
        Returns:
            Configuration section data
            
        Raises:
            ConfigurationError: If section cannot be read
        """
        pass

    @abstractmethod
    def write_section(self, section: str, data: Dict[str, Any]) -> bool:
        """
        Write a configuration section.
        
        Args:
            section: Section name to write
            data: Section data to write
            
        Returns:
            True if write was successful
            
        Raises:
            ConfigurationError: If section cannot be written
        """
        pass

    @abstractmethod
    def atomic_update(self, updates: Dict[str, Dict[str, Any]]) -> bool:
        """
        Perform atomic update of multiple configuration sections.
        
        Args:
            updates: Dictionary mapping section names to their new data
            
        Returns:
            True if all updates were successful
            
        Raises:
            ConfigurationError: If atomic update fails
        """
        pass

    @abstractmethod
    def list_sections(self) -> List[str]:
        """
        List all available configuration sections.
        
        Returns:
            List of section names
        """
        pass

    @abstractmethod
    def create_backup(self) -> str:
        """
        Create a backup of the current configuration.
        
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationError: If backup creation fails
        """
        pass

    @abstractmethod
    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore configuration from a backup.
        
        Args:
            backup_id: Backup identifier to restore
            
        Returns:
            True if restore was successful
            
        Raises:
            ConfigurationError: If backup restoration fails
        """
        pass

    @abstractmethod
    def acquire_lock(self, timeout: int = 30) -> bool:
        """
        Acquire exclusive lock for configuration operations.
        
        Args:
            timeout: Lock timeout in seconds
            
        Returns:
            True if lock was acquired
            
        Raises:
            ConfigurationLockError: If lock cannot be acquired
        """
        pass

    @abstractmethod
    def release_lock(self) -> None:
        """
        Release the configuration lock.
        
        Raises:
            ConfigurationLockError: If lock cannot be released
        """
        pass

    @abstractmethod
    def is_locked(self) -> bool:
        """
        Check if configuration is currently locked.
        
        Returns:
            True if configuration is locked
        """
        pass

    @abstractmethod
    def get_store_info(self) -> Dict[str, Any]:
        """
        Get information about the configuration store.
        
        Returns:
            Store information including path, size, last modified, etc.
        """
        pass