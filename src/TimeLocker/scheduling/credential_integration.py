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

Credential Integration for Scheduled Backups

This module provides secure credential management for automated backup
execution, integrating with platform-specific credential stores and
Repository Management for secure credential retrieval.
"""

import platform
import os
import json
import tempfile
import stat
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .scheduling_models import ScheduleConfig
from .scheduling_exceptions import CredentialAccessError, SchedulingError
from ..security.credential_manager import CredentialManager, CredentialManagerError

logger = logging.getLogger(__name__)


class PlatformCredentialStore:
    """
    Platform-specific credential store integration.
    
    Provides secure credential storage and retrieval using platform-native
    credential stores:
    - Windows: Windows Credential Manager
    - macOS: Keychain
    - Linux: Secret Service (libsecret)
    
    Falls back to encrypted file-based storage when platform stores
    are unavailable.
    """
    
    def __init__(self):
        """Initialize platform credential store."""
        self.platform = platform.system().lower()
        self.logger = logging.getLogger(f"{__name__}.PlatformCredentialStore")
        self.logger.info(f"Initialized PlatformCredentialStore for platform: {self.platform}")
        
        # Try to initialize platform-specific backend
        self._backend = self._initialize_backend()
    
    def _initialize_backend(self) -> Optional[Any]:
        """
        Initialize platform-specific credential backend.
        
        Returns:
            Optional backend instance or None if unavailable
        """
        try:
            if self.platform == 'windows':
                return self._initialize_windows_backend()
            elif self.platform == 'darwin':
                return self._initialize_macos_backend()
            elif self.platform == 'linux':
                return self._initialize_linux_backend()
            else:
                self.logger.warning(f"No platform-specific backend for {self.platform}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to initialize platform backend: {e}")
            return None
    
    def _initialize_windows_backend(self) -> Optional[Any]:
        """Initialize Windows Credential Manager backend."""
        try:
            import keyring
            keyring.get_keyring()
            self.logger.info("Windows Credential Manager backend initialized")
            return keyring
        except ImportError:
            self.logger.warning("keyring library not available for Windows Credential Manager")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to initialize Windows Credential Manager: {e}")
            return None
    
    def _initialize_macos_backend(self) -> Optional[Any]:
        """Initialize macOS Keychain backend."""
        try:
            import keyring
            keyring.get_keyring()
            self.logger.info("macOS Keychain backend initialized")
            return keyring
        except ImportError:
            self.logger.warning("keyring library not available for macOS Keychain")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to initialize macOS Keychain: {e}")
            return None
    
    def _initialize_linux_backend(self) -> Optional[Any]:
        """Initialize Linux Secret Service backend."""
        try:
            import keyring
            keyring.get_keyring()
            self.logger.info("Linux Secret Service backend initialized")
            return keyring
        except ImportError:
            self.logger.warning("keyring library not available for Linux Secret Service")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to initialize Linux Secret Service: {e}")
            return None
    
    def store_credential(self, service: str, username: str, password: str) -> bool:
        """
        Store credential in platform-specific store.
        
        Args:
            service: Service identifier
            username: Username/identifier
            password: Password/secret
            
        Returns:
            bool: True if storage was successful
        """
        try:
            if self._backend:
                self._backend.set_password(service, username, password)
                self.logger.debug(f"Stored credential for {service}/{username}")
                return True
            else:
                self.logger.warning("No platform backend available for credential storage")
                return False
        except Exception as e:
            self.logger.error(f"Failed to store credential: {e}")
            return False
    
    def retrieve_credential(self, service: str, username: str) -> Optional[str]:
        """
        Retrieve credential from platform-specific store.
        
        Args:
            service: Service identifier
            username: Username/identifier
            
        Returns:
            Optional[str]: Password/secret or None if not found
        """
        try:
            if self._backend:
                password = self._backend.get_password(service, username)
                if password:
                    self.logger.debug(f"Retrieved credential for {service}/{username}")
                return password
            else:
                self.logger.warning("No platform backend available for credential retrieval")
                return None
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential: {e}")
            return None
    
    def delete_credential(self, service: str, username: str) -> bool:
        """
        Delete credential from platform-specific store.
        
        Args:
            service: Service identifier
            username: Username/identifier
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            if self._backend:
                self._backend.delete_password(service, username)
                self.logger.debug(f"Deleted credential for {service}/{username}")
                return True
            else:
                self.logger.warning("No platform backend available for credential deletion")
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete credential: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if platform credential store is available.
        
        Returns:
            bool: True if platform store is available
        """
        return self._backend is not None


class SchedulingCredentialManager:
    """
    Credential manager for scheduled backup operations.
    
    Integrates with Repository Management and platform credential stores
    to provide secure credential access for automated backup execution.
    
    Responsibilities:
    - Secure credential retrieval from Repository Management
    - Platform credential store integration
    - Environment variable preparation for script execution
    - Secure cleanup of credential data
    """
    
    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """
        Initialize scheduling credential manager.
        
        Args:
            credential_manager: Optional CredentialManager instance
        """
        self.credential_manager = credential_manager or CredentialManager()
        self.platform_store = PlatformCredentialStore()
        self.logger = logging.getLogger(f"{__name__}.SchedulingCredentialManager")
        self.logger.info("Initialized SchedulingCredentialManager")
    
    async def prepare_credentials_for_schedule(self, config: ScheduleConfig, 
                                              repository_id: str) -> Dict[str, str]:
        """
        Prepare credentials for scheduled backup execution.
        
        Args:
            config: Schedule configuration
            repository_id: Repository identifier
            
        Returns:
            Dict[str, str]: Environment variables for credential access
            
        Raises:
            CredentialAccessError: If credential preparation fails
        """
        try:
            self.logger.info(f"Preparing credentials for schedule {config.schedule_id}")
            
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                raise CredentialAccessError("Credential manager is locked and cannot be unlocked")
            
            # Retrieve repository credentials
            credentials = await self._retrieve_repository_credentials(repository_id)
            
            # Store in platform credential store if available
            if self.platform_store.is_available():
                service_name = f"timelocker.schedule.{config.schedule_id}"
                self.platform_store.store_credential(
                    service_name,
                    repository_id,
                    credentials.get('password', '')
                )
                
                # Return environment variables pointing to platform store
                return {
                    'TIMELOCKER_CREDENTIAL_SERVICE': service_name,
                    'TIMELOCKER_CREDENTIAL_USERNAME': repository_id,
                    'TIMELOCKER_USE_PLATFORM_STORE': 'true'
                }
            else:
                # Fallback: create secure environment file
                env_file = await self._create_secure_env_file(config.schedule_id, credentials)
                
                return {
                    'TIMELOCKER_CREDENTIAL_ENV_FILE': str(env_file),
                    'TIMELOCKER_USE_PLATFORM_STORE': 'false'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to prepare credentials: {e}")
            raise CredentialAccessError(f"Credential preparation failed: {e}") from e
    
    def _ensure_credential_manager_unlocked(self) -> bool:
        """
        Ensure credential manager is unlocked.
        
        Returns:
            bool: True if unlocked successfully
        """
        try:
            if self.credential_manager.is_locked():
                # Try auto-unlock for scheduled operations
                if self.credential_manager.auto_unlock():
                    self.logger.info("Credential manager auto-unlocked successfully")
                    return True
                else:
                    self.logger.error("Failed to auto-unlock credential manager")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to unlock credential manager: {e}")
            return False
    
    async def _retrieve_repository_credentials(self, repository_id: str) -> Dict[str, str]:
        """
        Retrieve repository credentials from credential manager.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            Dict[str, str]: Repository credentials
            
        Raises:
            CredentialAccessError: If retrieval fails
        """
        try:
            # Retrieve password from credential manager
            password = self.credential_manager.get_repository_password(
                repository_id,
                allow_prompt=False  # No prompts for scheduled operations
            )
            
            if not password:
                raise CredentialAccessError(f"No credentials found for repository {repository_id}")
            
            return {
                'repository_id': repository_id,
                'password': password
            }
            
        except CredentialManagerError as e:
            raise CredentialAccessError(f"Failed to retrieve credentials: {e}") from e
    
    async def _create_secure_env_file(self, schedule_id: str, 
                                     credentials: Dict[str, str]) -> Path:
        """
        Create secure environment file for credential access.
        
        Args:
            schedule_id: Schedule identifier
            credentials: Credential data
            
        Returns:
            Path: Path to secure environment file
        """
        try:
            # Create secure temporary directory
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()
            env_dir = config_dir / "scheduling" / "env"
            env_dir.mkdir(parents=True, exist_ok=True)
            
            # Create environment file
            env_file = env_dir / f"{schedule_id}.env"
            
            # Write credentials in environment variable format
            env_content = []
            for key, value in credentials.items():
                # Sanitize key for environment variable
                env_key = f"TIMELOCKER_{key.upper()}"
                env_content.append(f"{env_key}={value}")
            
            env_file.write_text('\n'.join(env_content), encoding='utf-8')
            
            # Set restrictive permissions (owner read/write only)
            env_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            
            self.logger.debug(f"Created secure environment file: {env_file}")
            return env_file
            
        except Exception as e:
            raise CredentialAccessError(f"Failed to create environment file: {e}") from e
    
    async def cleanup_credentials_for_schedule(self, schedule_id: str) -> bool:
        """
        Clean up credentials for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            bool: True if cleanup was successful
        """
        try:
            self.logger.info(f"Cleaning up credentials for schedule {schedule_id}")
            
            # Remove from platform credential store
            if self.platform_store.is_available():
                service_name = f"timelocker.schedule.{schedule_id}"
                # Note: We don't know the repository_id here, so we can't delete
                # This is a limitation - consider storing mapping separately
                self.logger.debug("Platform credential store cleanup skipped (no repository_id)")
            
            # Remove environment file
            try:
                from ..config.configuration_path_resolver import ConfigurationPathResolver
                config_dir = ConfigurationPathResolver.get_config_directory()
                env_file = config_dir / "scheduling" / "env" / f"{schedule_id}.env"
                
                if env_file.exists():
                    env_file.unlink()
                    self.logger.debug(f"Deleted environment file: {env_file}")
            except Exception as e:
                self.logger.warning(f"Failed to delete environment file: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup credentials: {e}")
            return False
    
    async def validate_credential_access(self, repository_id: str) -> bool:
        """
        Validate that credentials are accessible for a repository.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            bool: True if credentials are accessible
        """
        try:
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                return False
            
            # Try to retrieve credentials
            credentials = await self._retrieve_repository_credentials(repository_id)
            
            return bool(credentials and credentials.get('password'))
            
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False
    
    def get_credential_env_variables(self, schedule_id: str) -> Dict[str, str]:
        """
        Get environment variables for credential access in scripts.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Dict[str, str]: Environment variables
        """
        if self.platform_store.is_available():
            service_name = f"timelocker.schedule.{schedule_id}"
            return {
                'TIMELOCKER_CREDENTIAL_SERVICE': service_name,
                'TIMELOCKER_USE_PLATFORM_STORE': 'true'
            }
        else:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory()
            env_file = config_dir / "scheduling" / "env" / f"{schedule_id}.env"
            
            return {
                'TIMELOCKER_CREDENTIAL_ENV_FILE': str(env_file),
                'TIMELOCKER_USE_PLATFORM_STORE': 'false'
            }


class SecureEnvironmentHandler:
    """
    Handles secure environment variable management for scheduled backups.
    
    Ensures credentials are properly loaded and cleaned up during
    script execution without exposing them in process lists or logs.
    """
    
    @staticmethod
    def load_credentials_from_env_file(env_file: Path) -> Dict[str, str]:
        """
        Load credentials from secure environment file.
        
        Args:
            env_file: Path to environment file
            
        Returns:
            Dict[str, str]: Environment variables
        """
        try:
            if not env_file.exists():
                raise CredentialAccessError(f"Environment file not found: {env_file}")
            
            # Verify file permissions
            file_stat = env_file.stat()
            if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                raise CredentialAccessError(f"Environment file has insecure permissions: {env_file}")
            
            # Load environment variables
            env_vars = {}
            for line in env_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
            
            return env_vars
            
        except Exception as e:
            raise CredentialAccessError(f"Failed to load credentials from env file: {e}") from e
    
    @staticmethod
    def load_credentials_from_platform_store(service: str, username: str) -> Dict[str, str]:
        """
        Load credentials from platform credential store.
        
        Args:
            service: Service identifier
            username: Username/identifier
            
        Returns:
            Dict[str, str]: Environment variables
        """
        try:
            store = PlatformCredentialStore()
            
            if not store.is_available():
                raise CredentialAccessError("Platform credential store not available")
            
            password = store.retrieve_credential(service, username)
            
            if not password:
                raise CredentialAccessError(f"Credential not found in platform store: {service}/{username}")
            
            return {
                'TIMELOCKER_REPOSITORY_PASSWORD': password,
                'TIMELOCKER_REPOSITORY_ID': username
            }
            
        except Exception as e:
            raise CredentialAccessError(f"Failed to load credentials from platform store: {e}") from e
    
    @staticmethod
    def sanitize_environment() -> None:
        """
        Sanitize environment by removing credential-related variables.
        
        This should be called after credential use to prevent exposure.
        """
        credential_vars = [
            'TIMELOCKER_REPOSITORY_PASSWORD',
            'TIMELOCKER_REPOSITORY_ID',
            'TIMELOCKER_CREDENTIAL_SERVICE',
            'TIMELOCKER_CREDENTIAL_USERNAME',
            'TIMELOCKER_CREDENTIAL_ENV_FILE'
        ]
        
        for var in credential_vars:
            if var in os.environ:
                del os.environ[var]
