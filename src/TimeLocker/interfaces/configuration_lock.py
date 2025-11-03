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
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConfigurationLock:
    """Configuration lock information"""
    lock_id: str
    acquired_at: datetime
    expires_at: datetime
    process_id: int
    operation: str
    sections: List[str]


class IConfigurationLock(ABC):
    """
    Abstract interface for configuration locking mechanisms.
    
    This interface provides cross-platform file locking capabilities
    for configuration operations, following the Single Responsibility
    Principle by focusing solely on lock management.
    """

    @abstractmethod
    def acquire_lock(self, lock_path: Path, timeout: int = 30) -> bool:
        """
        Acquire an exclusive lock on a configuration resource.
        
        Args:
            lock_path: Path to the resource to lock
            timeout: Lock timeout in seconds
            
        Returns:
            True if lock was acquired successfully
            
        Raises:
            ConfigurationLockError: If lock cannot be acquired
        """
        pass

    @abstractmethod
    def release_lock(self, lock_path: Path) -> None:
        """
        Release a lock on a configuration resource.
        
        Args:
            lock_path: Path to the resource to unlock
            
        Raises:
            ConfigurationLockError: If lock cannot be released
        """
        pass

    @abstractmethod
    def is_locked(self, lock_path: Path) -> bool:
        """
        Check if a configuration resource is currently locked.
        
        Args:
            lock_path: Path to check for locks
            
        Returns:
            True if resource is locked
        """
        pass

    @abstractmethod
    def get_lock_info(self, lock_path: Path) -> Optional[ConfigurationLock]:
        """
        Get information about a lock on a configuration resource.
        
        Args:
            lock_path: Path to get lock information for
            
        Returns:
            Lock information if locked, None if not locked
        """
        pass

    @abstractmethod
    def cleanup_stale_locks(self, max_age: int = 300) -> int:
        """
        Clean up stale locks that are older than max_age seconds.
        
        Args:
            max_age: Maximum age in seconds for locks to be considered stale
            
        Returns:
            Number of stale locks cleaned up
        """
        pass

    @abstractmethod
    def list_active_locks(self) -> List[ConfigurationLock]:
        """
        List all currently active locks.
        
        Returns:
            List of active lock information
        """
        pass

    @abstractmethod
    def force_release_lock(self, lock_path: Path) -> bool:
        """
        Force release a lock (use with caution).
        
        Args:
            lock_path: Path to force unlock
            
        Returns:
            True if lock was force released
            
        Raises:
            ConfigurationLockError: If force release fails
        """
        pass