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

import os
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RepositoryProtectionError(Exception):
    """Base exception for repository protection operations"""
    pass


class RepositoryLockError(RepositoryProtectionError):
    """Exception for repository locking errors"""
    pass


class RepositoryAccessError(RepositoryProtectionError):
    """Exception for repository access errors"""
    pass


class RepositoryMode(Enum):
    """Repository access modes"""
    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    LOCKED = "locked"


@dataclass
class RepositoryLock:
    """Repository lock information"""
    repository_id: str
    lock_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    locked_by: str
    operation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if lock has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if lock is valid (not expired)"""
        return not self.is_expired()


@dataclass
class RepositoryInfo:
    """Repository information for protection decisions"""
    repository_id: str
    name: str
    location: str
    size_bytes: Optional[int] = None
    snapshot_count: Optional[int] = None
    last_backup: Optional[datetime] = None
    created_at: Optional[datetime] = None
    mode: RepositoryMode = RepositoryMode.READ_WRITE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DestructiveOperation:
    """Information about a destructive operation requiring confirmation"""
    operation_type: str
    repository_info: RepositoryInfo
    description: str
    confirmation_text: str
    warning_level: str = "high"
    additional_info: Dict[str, Any] = field(default_factory=dict)


class RepositoryProtectionManager:
    """
    Repository Protection Manager for TimeLocker.
    
    Provides repository locking mechanism to prevent accidental modifications,
    confirmation dialogs for destructive operations, and read-only mode support.
    """

    # Default lock timeout in minutes
    DEFAULT_LOCK_TIMEOUT = 60
    
    # Lock cleanup interval in minutes
    LOCK_CLEANUP_INTERVAL = 5

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize Repository Protection Manager
        
        Args:
            config_dir: Directory for protection configuration and lock storage
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            base_config_dir = ConfigurationPathResolver.get_config_directory()
            config_dir = base_config_dir / "repository_protection"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.locks_file = self.config_dir / "repository_locks.json"
        self.modes_file = self.config_dir / "repository_modes.json"
        self.protection_log_file = self.config_dir / "protection.log"

        # In-memory storage for performance
        self._locks: Dict[str, RepositoryLock] = {}
        self._repository_modes: Dict[str, RepositoryMode] = {}
        
        # Thread safety
        self._locks_lock = threading.RLock()
        self._modes_lock = threading.RLock()

        # Load existing data
        self._load_locks()
        self._load_repository_modes()

        # Initialize protection logging
        self._initialize_protection_log()

    def _initialize_protection_log(self) -> None:
        """Initialize protection logging"""
        if not self.protection_log_file.exists():
            with open(self.protection_log_file, 'w') as f:
                f.write("# TimeLocker Repository Protection Log\n")
                f.write(f"# Initialized: {datetime.now().isoformat()}\n")
                f.write("# Format: timestamp|operation|repository_id|user|success|details\n")

    def _log_protection_event(self, operation: str, repository_id: str = "", 
                            user: str = "", success: bool = True, 
                            details: str = "") -> None:
        """Log protection event"""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp}|{operation}|{repository_id}|{user}|{success}|{details}\n"

        try:
            with open(self.protection_log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.warning(f"Failed to log protection event: {e}")

    def _load_locks(self) -> None:
        """Load repository locks from persistent storage"""
        if not self.locks_file.exists():
            return

        try:
            with open(self.locks_file, 'r') as f:
                locks_data = json.load(f)

            with self._locks_lock:
                for lock_id, lock_dict in locks_data.items():
                    lock = RepositoryLock(
                        repository_id=lock_dict['repository_id'],
                        lock_id=lock_dict['lock_id'],
                        created_at=datetime.fromisoformat(lock_dict['created_at']),
                        expires_at=datetime.fromisoformat(lock_dict['expires_at']) if lock_dict.get('expires_at') else None,
                        locked_by=lock_dict['locked_by'],
                        operation=lock_dict['operation'],
                        metadata=lock_dict.get('metadata', {})
                    )
                    
                    # Only load valid locks
                    if lock.is_valid():
                        self._locks[lock_id] = lock

            logger.debug(f"Loaded {len(self._locks)} valid repository locks")

        except Exception as e:
            logger.error(f"Failed to load repository locks: {e}")
            self._locks = {}

    def _save_locks(self) -> None:
        """Save repository locks to persistent storage"""
        try:
            locks_data = {}
            
            with self._locks_lock:
                for lock_id, lock in self._locks.items():
                    if lock.is_valid():
                        locks_data[lock_id] = {
                            'repository_id': lock.repository_id,
                            'lock_id': lock.lock_id,
                            'created_at': lock.created_at.isoformat(),
                            'expires_at': lock.expires_at.isoformat() if lock.expires_at else None,
                            'locked_by': lock.locked_by,
                            'operation': lock.operation,
                            'metadata': lock.metadata
                        }

            with open(self.locks_file, 'w') as f:
                json.dump(locks_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save repository locks: {e}")

    def _load_repository_modes(self) -> None:
        """Load repository modes from persistent storage"""
        if not self.modes_file.exists():
            return

        try:
            with open(self.modes_file, 'r') as f:
                modes_data = json.load(f)

            with self._modes_lock:
                for repo_id, mode_str in modes_data.items():
                    try:
                        self._repository_modes[repo_id] = RepositoryMode(mode_str)
                    except ValueError:
                        logger.warning(f"Invalid repository mode for {repo_id}: {mode_str}")

            logger.debug(f"Loaded {len(self._repository_modes)} repository modes")

        except Exception as e:
            logger.error(f"Failed to load repository modes: {e}")
            self._repository_modes = {}

    def _save_repository_modes(self) -> None:
        """Save repository modes to persistent storage"""
        try:
            modes_data = {}
            
            with self._modes_lock:
                for repo_id, mode in self._repository_modes.items():
                    modes_data[repo_id] = mode.value

            with open(self.modes_file, 'w') as f:
                json.dump(modes_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save repository modes: {e}")

    def lock_repository(self, repository_id: str, operation: str, 
                       locked_by: str, timeout_minutes: Optional[int] = None) -> str:
        """
        Lock repository to prevent accidental modifications
        
        Args:
            repository_id: Repository ID to lock
            operation: Operation that requires the lock
            locked_by: User or process locking the repository
            timeout_minutes: Lock timeout in minutes (default: 60)
            
        Returns:
            str: Lock ID for the created lock
            
        Raises:
            RepositoryLockError: If repository is already locked or lock creation fails
        """
        try:
            # Check if repository is already locked
            if self.is_repository_locked(repository_id):
                existing_lock = self.get_repository_lock(repository_id)
                if existing_lock:
                    raise RepositoryLockError(
                        f"Repository {repository_id} is already locked by {existing_lock.locked_by} "
                        f"for operation: {existing_lock.operation}"
                    )

            # Create new lock
            import uuid
            lock_id = str(uuid.uuid4())
            now = datetime.now()
            timeout = timeout_minutes or self.DEFAULT_LOCK_TIMEOUT
            expires_at = now + timedelta(minutes=timeout)

            lock = RepositoryLock(
                repository_id=repository_id,
                lock_id=lock_id,
                created_at=now,
                expires_at=expires_at,
                locked_by=locked_by,
                operation=operation
            )

            with self._locks_lock:
                self._locks[lock_id] = lock
                self._save_locks()

            self._log_protection_event("lock_repository", repository_id, locked_by, 
                                     success=True, details=f"Operation: {operation}")
            
            logger.info(f"Locked repository {repository_id} for {operation} by {locked_by}")
            return lock_id

        except Exception as e:
            self._log_protection_event("lock_repository", repository_id, locked_by,
                                     success=False, details=str(e))
            raise RepositoryLockError(f"Failed to lock repository {repository_id}: {e}")

    def unlock_repository(self, repository_id: str, lock_id: Optional[str] = None,
                         unlocked_by: str = "") -> bool:
        """
        Unlock repository
        
        Args:
            repository_id: Repository ID to unlock
            lock_id: Specific lock ID to remove (optional)
            unlocked_by: User or process unlocking the repository
            
        Returns:
            bool: True if repository was unlocked successfully
        """
        try:
            with self._locks_lock:
                locks_to_remove = []
                
                for current_lock_id, lock in self._locks.items():
                    if lock.repository_id == repository_id:
                        if lock_id is None or current_lock_id == lock_id:
                            locks_to_remove.append(current_lock_id)

                if not locks_to_remove:
                    self._log_protection_event("unlock_repository", repository_id, unlocked_by,
                                             success=False, details="No locks found")
                    return False

                for lock_id_to_remove in locks_to_remove:
                    del self._locks[lock_id_to_remove]

                self._save_locks()

            self._log_protection_event("unlock_repository", repository_id, unlocked_by,
                                     success=True, details=f"Removed {len(locks_to_remove)} locks")
            
            logger.info(f"Unlocked repository {repository_id} by {unlocked_by}")
            return True

        except Exception as e:
            self._log_protection_event("unlock_repository", repository_id, unlocked_by,
                                     success=False, details=str(e))
            logger.error(f"Failed to unlock repository {repository_id}: {e}")
            return False

    def is_repository_locked(self, repository_id: str) -> bool:
        """
        Check if repository is currently locked
        
        Args:
            repository_id: Repository ID to check
            
        Returns:
            bool: True if repository is locked
        """
        with self._locks_lock:
            for lock in self._locks.values():
                if lock.repository_id == repository_id and lock.is_valid():
                    return True
            return False

    def get_repository_lock(self, repository_id: str) -> Optional[RepositoryLock]:
        """
        Get current lock for repository
        
        Args:
            repository_id: Repository ID to get lock for
            
        Returns:
            RepositoryLock: Current lock if exists and valid, None otherwise
        """
        with self._locks_lock:
            for lock in self._locks.values():
                if lock.repository_id == repository_id and lock.is_valid():
                    return lock
            return None

    def set_repository_mode(self, repository_id: str, mode: RepositoryMode,
                           changed_by: str = "") -> bool:
        """
        Set repository access mode
        
        Args:
            repository_id: Repository ID to set mode for
            mode: Repository mode to set
            changed_by: User or process changing the mode
            
        Returns:
            bool: True if mode was set successfully
        """
        try:
            with self._modes_lock:
                self._repository_modes[repository_id] = mode
                self._save_repository_modes()

            self._log_protection_event("set_repository_mode", repository_id, changed_by,
                                     success=True, details=f"Mode: {mode.value}")
            
            logger.info(f"Set repository {repository_id} mode to {mode.value} by {changed_by}")
            return True

        except Exception as e:
            self._log_protection_event("set_repository_mode", repository_id, changed_by,
                                     success=False, details=str(e))
            logger.error(f"Failed to set repository mode for {repository_id}: {e}")
            return False

    def get_repository_mode(self, repository_id: str) -> RepositoryMode:
        """
        Get repository access mode
        
        Args:
            repository_id: Repository ID to get mode for
            
        Returns:
            RepositoryMode: Current repository mode (default: READ_WRITE)
        """
        with self._modes_lock:
            return self._repository_modes.get(repository_id, RepositoryMode.READ_WRITE)

    def is_operation_allowed(self, repository_id: str, operation: str) -> bool:
        """
        Check if operation is allowed on repository based on current mode and locks
        
        Args:
            repository_id: Repository ID to check
            operation: Operation to check ('read', 'write', 'delete', etc.)
            
        Returns:
            bool: True if operation is allowed
        """
        # Check if repository is locked
        if self.is_repository_locked(repository_id):
            # Only allow read operations on locked repositories
            return operation.lower() in ['read', 'list', 'show', 'check']

        # Check repository mode
        mode = self.get_repository_mode(repository_id)
        
        if mode == RepositoryMode.LOCKED:
            return False
        elif mode == RepositoryMode.READ_ONLY:
            return operation.lower() in ['read', 'list', 'show', 'check', 'stats']
        else:  # READ_WRITE
            return True

    def create_destructive_operation_info(self, operation_type: str, 
                                        repository_info: RepositoryInfo) -> DestructiveOperation:
        """
        Create destructive operation information for confirmation
        
        Args:
            operation_type: Type of destructive operation
            repository_info: Repository information
            
        Returns:
            DestructiveOperation: Operation information for confirmation
        """
        if operation_type.lower() == "delete_repository":
            description = (
                f"This will permanently delete the entire repository '{repository_info.name}' "
                f"and all its backup data. This action cannot be undone."
            )
            confirmation_text = "DELETE ALL DATA"
            warning_level = "critical"
            
        elif operation_type.lower() == "forget_snapshot":
            description = (
                f"This will remove the selected snapshot from repository '{repository_info.name}'. "
                f"The snapshot data will be marked for deletion and removed during the next prune operation."
            )
            confirmation_text = "DELETE SNAPSHOT"
            warning_level = "high"
            
        elif operation_type.lower() == "prune_repository":
            description = (
                f"This will permanently remove unreferenced data from repository '{repository_info.name}'. "
                f"This operation cannot be undone and may take a long time."
            )
            confirmation_text = "PRUNE DATA"
            warning_level = "high"
            
        else:
            description = f"This operation will modify repository '{repository_info.name}' in a way that cannot be undone."
            confirmation_text = "CONFIRM OPERATION"
            warning_level = "medium"

        additional_info = {}
        if repository_info.size_bytes:
            additional_info["repository_size"] = self._format_size(repository_info.size_bytes)
        if repository_info.snapshot_count:
            additional_info["snapshot_count"] = repository_info.snapshot_count
        if repository_info.last_backup:
            additional_info["last_backup"] = repository_info.last_backup.isoformat()

        return DestructiveOperation(
            operation_type=operation_type,
            repository_info=repository_info,
            description=description,
            confirmation_text=confirmation_text,
            warning_level=warning_level,
            additional_info=additional_info
        )

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def cleanup_expired_locks(self) -> int:
        """
        Clean up expired repository locks
        
        Returns:
            int: Number of locks cleaned up
        """
        cleaned_count = 0
        
        try:
            with self._locks_lock:
                expired_locks = []
                
                for lock_id, lock in self._locks.items():
                    if not lock.is_valid():
                        expired_locks.append(lock_id)

                for lock_id in expired_locks:
                    lock = self._locks[lock_id]
                    del self._locks[lock_id]
                    cleaned_count += 1
                    
                    self._log_protection_event("cleanup_expired_lock", lock.repository_id,
                                             details=f"Lock ID: {lock_id}")

                if cleaned_count > 0:
                    self._save_locks()

        except Exception as e:
            logger.error(f"Lock cleanup error: {e}")

        return cleaned_count

    def get_protection_status(self) -> Dict[str, Any]:
        """
        Get repository protection status
        
        Returns:
            Dict: Protection status information
        """
        with self._locks_lock:
            active_locks = len([lock for lock in self._locks.values() if lock.is_valid()])
            
        with self._modes_lock:
            read_only_repos = len([mode for mode in self._repository_modes.values() 
                                 if mode == RepositoryMode.READ_ONLY])
            locked_repos = len([mode for mode in self._repository_modes.values() 
                              if mode == RepositoryMode.LOCKED])

        return {
            'active_locks': active_locks,
            'total_locks': len(self._locks),
            'read_only_repositories': read_only_repos,
            'locked_repositories': locked_repos,
            'total_protected_repositories': len(self._repository_modes),
            'config_directory': str(self.config_dir),
            'protection_log_exists': self.protection_log_file.exists()
        }

    def get_repository_locks(self, repository_id: Optional[str] = None) -> List[RepositoryLock]:
        """
        Get list of repository locks
        
        Args:
            repository_id: Optional repository ID to filter locks
            
        Returns:
            List[RepositoryLock]: List of repository locks
        """
        locks = []
        
        with self._locks_lock:
            for lock in self._locks.values():
                if lock.is_valid():
                    if repository_id is None or lock.repository_id == repository_id:
                        locks.append(lock)

        return locks