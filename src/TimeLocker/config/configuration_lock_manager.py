"""
Configuration lock manager for TimeLocker.

This module provides cross-platform file locking capabilities for configuration
operations, following the Single Responsibility Principle by focusing solely
on lock management.
"""

import os
import time
import logging
import psutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..interfaces.configuration_lock import IConfigurationLock, ConfigurationLock
from ..interfaces.exceptions import (
    ConfigurationLockError,
    ConfigurationLockTimeoutError,
    ConfigurationLockNotHeldError,
    ConfigurationStaleLockError
)

logger = logging.getLogger(__name__)

# Platform-specific imports
try:
    import fcntl  # Unix/Linux/macOS
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt  # Windows
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


@dataclass
class LockFileData:
    """Data stored in lock files"""
    lock_id: str
    process_id: int
    acquired_at: str  # ISO format datetime
    expires_at: str   # ISO format datetime
    operation: str
    sections: List[str]
    hostname: str


class ConfigurationLockManager(IConfigurationLock):
    """
    Cross-platform configuration lock manager.
    
    Provides file-based locking with process validation and stale lock cleanup.
    Uses fcntl on Unix systems and msvcrt on Windows for platform-appropriate
    locking mechanisms.
    """

    def __init__(self, lock_directory: Optional[Path] = None):
        """
        Initialize the lock manager.
        
        Args:
            lock_directory: Directory to store lock files (defaults to system temp)
        """
        if lock_directory is None:
            import tempfile
            lock_directory = Path(tempfile.gettempdir()) / "timelocker_locks"
        
        self.lock_directory = lock_directory
        self.lock_directory.mkdir(parents=True, exist_ok=True)
        
        # Track locks held by this process
        self._held_locks: Dict[str, Dict] = {}
        
        # Platform detection
        self._use_fcntl = HAS_FCNTL and os.name != 'nt'
        self._use_msvcrt = HAS_MSVCRT and os.name == 'nt'
        
        if not (self._use_fcntl or self._use_msvcrt):
            logger.warning("No native locking mechanism available, using file-based fallback")

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
        lock_file_path = self._get_lock_file_path(lock_path)
        lock_id = self._generate_lock_id(lock_path)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check for existing lock
                if self._is_lock_file_valid(lock_file_path):
                    time.sleep(0.1)  # Brief wait before retry
                    continue
                
                # Try to acquire lock
                if self._acquire_file_lock(lock_file_path, lock_id, lock_path):
                    logger.debug(f"Acquired lock for {lock_path}")
                    return True
                    
            except Exception as e:
                logger.error(f"Error acquiring lock for {lock_path}: {e}")
                raise ConfigurationLockError(f"Failed to acquire lock: {e}")
        
        raise ConfigurationLockTimeoutError(f"Lock acquisition timed out after {timeout} seconds")

    def release_lock(self, lock_path: Path) -> None:
        """
        Release a lock on a configuration resource.
        
        Args:
            lock_path: Path to the resource to unlock
            
        Raises:
            ConfigurationLockError: If lock cannot be released
        """
        lock_file_path = self._get_lock_file_path(lock_path)
        lock_key = str(lock_path)
        
        if lock_key not in self._held_locks:
            raise ConfigurationLockNotHeldError(f"No lock held for {lock_path}")
        
        try:
            # Release file lock
            lock_info = self._held_locks[lock_key]
            if 'file_handle' in lock_info:
                self._release_file_lock(lock_info['file_handle'])
            
            # Remove lock file
            if lock_file_path.exists():
                lock_file_path.unlink()
            
            # Remove from held locks
            del self._held_locks[lock_key]
            
            logger.debug(f"Released lock for {lock_path}")
            
        except Exception as e:
            logger.error(f"Error releasing lock for {lock_path}: {e}")
            raise ConfigurationLockError(f"Failed to release lock: {e}")

    def is_locked(self, lock_path: Path) -> bool:
        """
        Check if a configuration resource is currently locked.
        
        Args:
            lock_path: Path to check for locks
            
        Returns:
            True if resource is locked
        """
        lock_file_path = self._get_lock_file_path(lock_path)
        return self._is_lock_file_valid(lock_file_path)

    def get_lock_info(self, lock_path: Path) -> Optional[ConfigurationLock]:
        """
        Get information about a lock on a configuration resource.
        
        Args:
            lock_path: Path to get lock information for
            
        Returns:
            Lock information if locked, None if not locked
        """
        lock_file_path = self._get_lock_file_path(lock_path)
        
        if not lock_file_path.exists():
            return None
        
        try:
            lock_data = self._read_lock_file(lock_file_path)
            if lock_data and self._is_process_alive(lock_data.process_id):
                return ConfigurationLock(
                    lock_id=lock_data.lock_id,
                    acquired_at=datetime.fromisoformat(lock_data.acquired_at),
                    expires_at=datetime.fromisoformat(lock_data.expires_at),
                    process_id=lock_data.process_id,
                    operation=lock_data.operation,
                    sections=lock_data.sections
                )
        except Exception as e:
            logger.warning(f"Error reading lock file {lock_file_path}: {e}")
        
        return None

    def cleanup_stale_locks(self, max_age: int = 300) -> int:
        """
        Clean up stale locks that are older than max_age seconds.
        
        Args:
            max_age: Maximum age in seconds for locks to be considered stale
            
        Returns:
            Number of stale locks cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(seconds=max_age)
        
        try:
            for lock_file in self.lock_directory.glob("*.lock"):
                try:
                    lock_data = self._read_lock_file(lock_file)
                    if not lock_data:
                        # Invalid lock file
                        lock_file.unlink()
                        cleaned_count += 1
                        continue
                    
                    acquired_time = datetime.fromisoformat(lock_data.acquired_at)
                    expires_time = datetime.fromisoformat(lock_data.expires_at)
                    
                    # Check if lock is stale
                    is_stale = (
                        acquired_time < cutoff_time or
                        expires_time < datetime.now() or
                        not self._is_process_alive(lock_data.process_id)
                    )
                    
                    if is_stale:
                        lock_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up stale lock: {lock_file}")
                        
                except Exception as e:
                    logger.warning(f"Error processing lock file {lock_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during stale lock cleanup: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale locks")
        
        return cleaned_count

    def list_active_locks(self) -> List[ConfigurationLock]:
        """
        List all currently active locks.
        
        Returns:
            List of active lock information
        """
        active_locks = []
        
        try:
            for lock_file in self.lock_directory.glob("*.lock"):
                try:
                    lock_data = self._read_lock_file(lock_file)
                    if lock_data and self._is_process_alive(lock_data.process_id):
                        active_locks.append(ConfigurationLock(
                            lock_id=lock_data.lock_id,
                            acquired_at=datetime.fromisoformat(lock_data.acquired_at),
                            expires_at=datetime.fromisoformat(lock_data.expires_at),
                            process_id=lock_data.process_id,
                            operation=lock_data.operation,
                            sections=lock_data.sections
                        ))
                except Exception as e:
                    logger.warning(f"Error reading lock file {lock_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error listing active locks: {e}")
        
        return active_locks

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
        lock_file_path = self._get_lock_file_path(lock_path)
        
        try:
            if lock_file_path.exists():
                lock_file_path.unlink()
                logger.warning(f"Force released lock for {lock_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error force releasing lock for {lock_path}: {e}")
            raise ConfigurationLockError(f"Failed to force release lock: {e}")

    # Private helper methods

    def _get_lock_file_path(self, resource_path: Path) -> Path:
        """Get the lock file path for a resource"""
        # Create a safe filename from the resource path
        safe_name = str(resource_path).replace(os.sep, '_').replace(':', '_')
        return self.lock_directory / f"{safe_name}.lock"

    def _generate_lock_id(self, resource_path: Path) -> str:
        """Generate a unique lock ID"""
        import uuid
        return f"{resource_path.name}_{os.getpid()}_{uuid.uuid4().hex[:8]}"

    def _acquire_file_lock(self, lock_file_path: Path, lock_id: str, resource_path: Path) -> bool:
        """Acquire a file-based lock"""
        try:
            # Create lock data
            lock_data = LockFileData(
                lock_id=lock_id,
                process_id=os.getpid(),
                acquired_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
                operation="configuration_update",
                sections=[],
                hostname=os.uname().nodename if hasattr(os, 'uname') else 'unknown'
            )
            
            # Try to create lock file exclusively
            try:
                with open(lock_file_path, 'x') as f:
                    import json
                    json.dump(asdict(lock_data), f, indent=2)
                
                # Store lock info using the original resource path as key
                lock_key = str(resource_path)
                self._held_locks[lock_key] = {
                    'lock_id': lock_id,
                    'lock_file': lock_file_path,
                    'acquired_at': datetime.now()
                }
                
                return True
                
            except FileExistsError:
                # Lock file already exists
                return False
                
        except Exception as e:
            logger.error(f"Error acquiring file lock: {e}")
            return False

    def _release_file_lock(self, file_handle) -> None:
        """Release a file lock"""
        try:
            if self._use_fcntl and hasattr(file_handle, 'fileno'):
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            elif self._use_msvcrt and hasattr(file_handle, 'fileno'):
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception as e:
            logger.warning(f"Error releasing file lock: {e}")

    def _is_lock_file_valid(self, lock_file_path: Path) -> bool:
        """Check if a lock file represents a valid active lock"""
        if not lock_file_path.exists():
            return False
        
        try:
            lock_data = self._read_lock_file(lock_file_path)
            if not lock_data:
                return False
            
            # Check if process is still alive
            if not self._is_process_alive(lock_data.process_id):
                # Clean up stale lock
                lock_file_path.unlink()
                return False
            
            # Check if lock has expired
            expires_at = datetime.fromisoformat(lock_data.expires_at)
            if expires_at < datetime.now():
                # Clean up expired lock
                lock_file_path.unlink()
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating lock file {lock_file_path}: {e}")
            return False

    def _read_lock_file(self, lock_file_path: Path) -> Optional[LockFileData]:
        """Read and parse a lock file"""
        try:
            with open(lock_file_path, 'r') as f:
                import json
                data = json.load(f)
                return LockFileData(**data)
        except Exception as e:
            logger.warning(f"Error reading lock file {lock_file_path}: {e}")
            return None

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process is still alive"""
        try:
            return psutil.pid_exists(pid)
        except Exception:
            # Fallback method if psutil is not available
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False