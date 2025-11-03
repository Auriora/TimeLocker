"""
File system configuration store for TimeLocker.

This module provides a file-based implementation of the configuration store
interface with atomic operations, locking, and backup capabilities.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..interfaces.configuration_store import IConfigurationStore
from ..interfaces.exceptions import (
    ConfigurationStoreError,
    ConfigurationAtomicUpdateError,
    ConfigurationBackupError,
    ConfigurationLockError
)

logger = logging.getLogger(__name__)


class FileSystemConfigurationStore(IConfigurationStore):
    """
    File system-based configuration store.
    
    Provides atomic file operations, locking, and backup capabilities
    for JSON-based configuration storage following ACID principles.
    """

    def __init__(self, config_file: Path, lock_manager=None, backup_manager=None):
        """
        Initialize the file system configuration store.
        
        Args:
            config_file: Path to the configuration file
            lock_manager: Optional lock manager for concurrency control
            backup_manager: Optional backup manager for backup operations
        """
        self.config_file = config_file
        self.lock_manager = lock_manager
        self.backup_manager = backup_manager
        
        # Ensure parent directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

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
        try:
            config_data = self._load_config()
            return config_data.get(section, {})
            
        except Exception as e:
            logger.error(f"Failed to read section '{section}': {e}")
            raise ConfigurationStoreError(f"Failed to read section: {e}")

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
        try:
            # Load current configuration
            config_data = self._load_config()
            
            # Update section
            config_data[section] = data
            
            # Save atomically
            return self._save_config_atomic(config_data)
            
        except Exception as e:
            logger.error(f"Failed to write section '{section}': {e}")
            raise ConfigurationStoreError(f"Failed to write section: {e}")

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
        lock_acquired = False
        try:
            # Acquire lock if available
            if self.lock_manager:
                lock_acquired = self.lock_manager.acquire_lock(self.config_file, timeout=30)
                if not lock_acquired:
                    raise ConfigurationLockError("Could not acquire lock for atomic update")
            
            # Create backup if available
            backup_id = None
            if self.backup_manager:
                try:
                    from .configuration_backup_manager import BackupReason
                    backup_id = self.backup_manager.create_backup(
                        self.config_file, 
                        BackupReason.PRE_UPDATE,
                        ["atomic_update"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to create backup before atomic update: {e}")
            
            # Load current configuration
            config_data = self._load_config()
            
            # Apply all updates
            for section, section_data in updates.items():
                config_data[section] = section_data
            
            # Save atomically
            success = self._save_config_atomic(config_data)
            
            if not success and backup_id and self.backup_manager:
                # Restore from backup on failure
                try:
                    self.backup_manager.restore_backup(backup_id, self.config_file)
                    logger.info("Restored configuration from backup after atomic update failure")
                except Exception as e:
                    logger.error(f"Failed to restore backup after atomic update failure: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Atomic update failed: {e}")
            raise ConfigurationAtomicUpdateError(f"Atomic update failed: {e}")
        finally:
            # Always release lock if we acquired it
            if lock_acquired and self.lock_manager:
                try:
                    self.lock_manager.release_lock(self.config_file)
                except Exception as e:
                    logger.warning(f"Failed to release lock after atomic update: {e}")

    def list_sections(self) -> List[str]:
        """
        List all available configuration sections.
        
        Returns:
            List of section names
        """
        try:
            config_data = self._load_config()
            return list(config_data.keys())
            
        except Exception as e:
            logger.error(f"Failed to list sections: {e}")
            return []

    def create_backup(self) -> str:
        """
        Create a backup of the current configuration.
        
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationError: If backup creation fails
        """
        if not self.backup_manager:
            raise ConfigurationBackupError("No backup manager available")
        
        try:
            from .configuration_backup_manager import BackupReason
            return self.backup_manager.create_backup(
                self.config_file, 
                BackupReason.MANUAL,
                ["store_backup"]
            )
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise ConfigurationBackupError(f"Backup creation failed: {e}")

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
        if not self.backup_manager:
            raise ConfigurationBackupError("No backup manager available")
        
        try:
            return self.backup_manager.restore_backup(backup_id, self.config_file)
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            raise ConfigurationBackupError(f"Backup restoration failed: {e}")

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
        if not self.lock_manager:
            raise ConfigurationLockError("No lock manager available")
        
        try:
            return self.lock_manager.acquire_lock(self.config_file, timeout)
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            raise ConfigurationLockError(f"Lock acquisition failed: {e}")

    def release_lock(self) -> None:
        """
        Release the configuration lock.
        
        Raises:
            ConfigurationLockError: If lock cannot be released
        """
        if not self.lock_manager:
            raise ConfigurationLockError("No lock manager available")
        
        try:
            self.lock_manager.release_lock(self.config_file)
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            raise ConfigurationLockError(f"Lock release failed: {e}")

    def is_locked(self) -> bool:
        """
        Check if configuration is currently locked.
        
        Returns:
            True if configuration is locked
        """
        if not self.lock_manager:
            return False
        
        return self.lock_manager.is_locked(self.config_file)

    def get_store_info(self) -> Dict[str, Any]:
        """
        Get information about the configuration store.
        
        Returns:
            Store information including path, size, last modified, etc.
        """
        try:
            info = {
                'store_type': 'filesystem',
                'config_file': str(self.config_file),
                'file_exists': self.config_file.exists(),
                'has_lock_manager': self.lock_manager is not None,
                'has_backup_manager': self.backup_manager is not None,
                'is_locked': self.is_locked()
            }
            
            if self.config_file.exists():
                stat = self.config_file.stat()
                info.update({
                    'file_size': stat.st_size,
                    'last_modified': stat.st_mtime,
                    'permissions': oct(stat.st_mode)[-3:]
                })
                
                # Try to get section count
                try:
                    sections = self.list_sections()
                    info['section_count'] = len(sections)
                    info['sections'] = sections
                except Exception:
                    info['section_count'] = 0
                    info['sections'] = []
            else:
                info.update({
                    'file_size': 0,
                    'last_modified': None,
                    'permissions': None,
                    'section_count': 0,
                    'sections': []
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get store info: {e}")
            return {
                'store_type': 'filesystem',
                'config_file': str(self.config_file),
                'error': str(e)
            }

    # Private helper methods

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if not self.config_file.exists():
                return {}
            
            with open(self.config_file, 'r') as f:
                return json.load(f)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise ConfigurationStoreError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationStoreError(f"Failed to load configuration: {e}")

    def _save_config_atomic(self, config_data: Dict[str, Any]) -> bool:
        """Save configuration atomically using temporary file and atomic move"""
        try:
            # Create temporary file in same directory as config file
            temp_file = self.config_file.with_suffix('.tmp')
            
            try:
                # Write to temporary file
                with open(temp_file, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                # Atomic move (rename) to final location
                temp_file.replace(self.config_file)
                
                logger.debug(f"Atomically saved configuration to {self.config_file}")
                return True
                
            except Exception as e:
                # Clean up temporary file on failure
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
                raise e
                
        except Exception as e:
            logger.error(f"Failed to save configuration atomically: {e}")
            return False

    def delete_section(self, section: str) -> bool:
        """
        Delete a configuration section.
        
        Args:
            section: Section name to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            ConfigurationStoreError: If section cannot be deleted
        """
        try:
            # Load current configuration
            config_data = self._load_config()
            
            # Remove section if it exists
            if section in config_data:
                del config_data[section]
                
                # Save atomically
                return self._save_config_atomic(config_data)
            else:
                # Section doesn't exist, consider it successful
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete section '{section}': {e}")
            raise ConfigurationStoreError(f"Failed to delete section: {e}")

    def section_exists(self, section: str) -> bool:
        """
        Check if a configuration section exists.
        
        Args:
            section: Section name to check
            
        Returns:
            True if section exists
        """
        try:
            config_data = self._load_config()
            return section in config_data
        except Exception:
            return False

    def get_section_size(self, section: str) -> int:
        """
        Get the size of a configuration section in bytes.
        
        Args:
            section: Section name
            
        Returns:
            Section size in bytes
        """
        try:
            section_data = self.read_section(section)
            return len(json.dumps(section_data).encode('utf-8'))
        except Exception:
            return 0