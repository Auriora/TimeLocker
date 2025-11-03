"""
Repository Credential Manager

Provides secure credential management for repositories by integrating with Security Services.
Implements per-repository credential storage with fallback resolution order.
"""

import os
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from pathlib import Path

from ..security import SecurityService, CredentialManager, SecurityEvent, SecurityLevel
from ..interfaces.exceptions import CredentialError

logger = logging.getLogger(__name__)


class RepositoryCredentialManager:
    """
    Repository credential manager that integrates with Security Services.
    
    Provides per-repository credential storage using repository identifiers as keys
    and implements credential resolution order: stored -> environment -> interactive.
    """

    def __init__(self, security_service: SecurityService):
        """
        Initialize repository credential manager.
        
        Args:
            security_service: SecurityService instance for credential operations
        """
        self.security_service = security_service
        self.credential_manager = security_service.credential_manager
        
    async def store_credentials(self, repo_id: str, credentials: Dict[str, Any]) -> bool:
        """
        Store credentials for a repository using Security Services.
        
        Args:
            repo_id: Repository identifier (unique key)
            credentials: Dictionary containing credential data
            
        Returns:
            bool: True if credentials were stored successfully
            
        Raises:
            CredentialError: If credential storage fails
        """
        try:
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                raise CredentialError("Cannot store credentials: credential manager is locked")
            
            # Store repository password if provided
            if 'password' in credentials:
                self.credential_manager.store_repository_password(
                    repo_id, 
                    credentials['password']
                )
            
            # Store backend-specific credentials if provided
            if 'backend_credentials' in credentials:
                backend_type = credentials.get('backend_type', 'unknown')
                self.credential_manager.store_repository_backend_credentials(
                    repo_id,
                    backend_type,
                    credentials['backend_credentials']
                )
            
            # Log security event
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_storage",
                level=SecurityLevel.MEDIUM,
                description=f"Repository credentials stored for {repo_id}",
                repository_id=repo_id,
                metadata={
                    "credential_types": list(credentials.keys()),
                    "backend_type": credentials.get('backend_type')
                }
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credentials for repository {repo_id}: {e}")
            
            # Log security event for failure
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_storage",
                level=SecurityLevel.HIGH,
                description=f"Failed to store credentials for {repo_id}: {str(e)}",
                repository_id=repo_id,
                metadata={"error": str(e)}
            ))
            
            raise CredentialError(f"Failed to store credentials for repository {repo_id}: {e}")

    async def retrieve_credentials(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a repository using Security Services.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Optional[Dict]: Credential data if found, None otherwise
            
        Raises:
            CredentialError: If credential retrieval fails
        """
        try:
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                raise CredentialError("Cannot retrieve credentials: credential manager is locked")
            
            credentials = {}
            
            # Retrieve repository password
            password = self.credential_manager.get_repository_password(repo_id)
            if password:
                credentials['password'] = password
            
            # Try to retrieve backend credentials for common backend types
            backend_types = ['s3', 'b2', 'sftp', 'local']
            for backend_type in backend_types:
                backend_creds = self.credential_manager.get_repository_backend_credentials(
                    repo_id, backend_type
                )
                if backend_creds:
                    credentials['backend_credentials'] = backend_creds
                    credentials['backend_type'] = backend_type
                    break
            
            if credentials:
                # Log successful retrieval
                self.security_service.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="credential_retrieval",
                    level=SecurityLevel.LOW,
                    description=f"Repository credentials retrieved for {repo_id}",
                    repository_id=repo_id,
                    metadata={
                        "credential_types": list(credentials.keys()),
                        "backend_type": credentials.get('backend_type')
                    }
                ))
                
                return credentials
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for repository {repo_id}: {e}")
            
            # Log security event for failure
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_retrieval",
                level=SecurityLevel.MEDIUM,
                description=f"Failed to retrieve credentials for {repo_id}: {str(e)}",
                repository_id=repo_id,
                metadata={"error": str(e)}
            ))
            
            raise CredentialError(f"Failed to retrieve credentials for repository {repo_id}: {e}")

    async def rotate_credentials(self, repo_id: str, new_credentials: Dict[str, Any]) -> bool:
        """
        Rotate credentials for a repository without requiring re-initialization.
        
        Args:
            repo_id: Repository identifier
            new_credentials: New credential data
            
        Returns:
            bool: True if rotation was successful
            
        Raises:
            CredentialError: If credential rotation fails
        """
        try:
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                raise CredentialError("Cannot rotate credentials: credential manager is locked")
            
            # Get existing credentials for audit trail
            old_credentials = await self.retrieve_credentials(repo_id)
            
            # Rotate password if provided
            if 'password' in new_credentials:
                self.credential_manager.rotate_credential(repo_id, new_credentials['password'])
            
            # Rotate backend credentials if provided
            if 'backend_credentials' in new_credentials and 'backend_type' in new_credentials:
                self.credential_manager.rotate_repository_backend_credentials(
                    repo_id,
                    new_credentials['backend_type'],
                    new_credentials['backend_credentials']
                )
            
            # Log credential rotation event with detailed audit information
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_rotation",
                level=SecurityLevel.HIGH,
                description=f"Repository credentials rotated for {repo_id}",
                repository_id=repo_id,
                metadata={
                    "old_credential_types": list(old_credentials.keys()) if old_credentials else [],
                    "new_credential_types": list(new_credentials.keys()),
                    "backend_type": new_credentials.get('backend_type'),
                    "rotation_timestamp": datetime.now().isoformat(),
                    "rotation_method": "security_services"
                }
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate credentials for repository {repo_id}: {e}")
            
            # Log security event for failure
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_rotation",
                level=SecurityLevel.CRITICAL,
                description=f"Failed to rotate credentials for {repo_id}: {str(e)}",
                repository_id=repo_id,
                metadata={
                    "error": str(e),
                    "rotation_timestamp": datetime.now().isoformat(),
                    "rotation_method": "security_services"
                }
            ))
            
            raise CredentialError(f"Failed to rotate credentials for repository {repo_id}: {e}")

    async def rotate_password(self, repo_id: str, new_password: str) -> bool:
        """
        Rotate only the password for a repository.
        
        Args:
            repo_id: Repository identifier
            new_password: New password
            
        Returns:
            bool: True if rotation was successful
        """
        return await self.rotate_credentials(repo_id, {'password': new_password})

    async def rotate_backend_credentials(self, repo_id: str, backend_type: str, 
                                       new_backend_credentials: Dict[str, str]) -> bool:
        """
        Rotate only the backend credentials for a repository.
        
        Args:
            repo_id: Repository identifier
            backend_type: Backend type (s3, b2, etc.)
            new_backend_credentials: New backend credential dictionary
            
        Returns:
            bool: True if rotation was successful
        """
        return await self.rotate_credentials(repo_id, {
            'backend_type': backend_type,
            'backend_credentials': new_backend_credentials
        })

    async def remove_credentials(self, repo_id: str) -> bool:
        """
        Remove credentials for a repository.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            bool: True if credentials were removed successfully
            
        Raises:
            CredentialError: If credential removal fails
        """
        try:
            # Ensure credential manager is unlocked
            if not self._ensure_credential_manager_unlocked():
                raise CredentialError("Cannot remove credentials: credential manager is locked")
            
            # Remove repository password
            password_removed = self.credential_manager.remove_repository(repo_id)
            
            # Remove backend credentials for all types
            backend_removed = False
            backend_types = ['s3', 'b2', 'sftp', 'local']
            for backend_type in backend_types:
                if self.credential_manager.remove_repository_backend_credentials(repo_id, backend_type):
                    backend_removed = True
            
            success = password_removed or backend_removed
            
            if success:
                # Log credential removal event
                self.security_service.log_security_event(SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="credential_removal",
                    level=SecurityLevel.MEDIUM,
                    description=f"Repository credentials removed for {repo_id}",
                    repository_id=repo_id,
                    metadata={
                        "password_removed": password_removed,
                        "backend_removed": backend_removed
                    }
                ))
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove credentials for repository {repo_id}: {e}")
            
            # Log security event for failure
            self.security_service.log_security_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="credential_removal",
                level=SecurityLevel.HIGH,
                description=f"Failed to remove credentials for {repo_id}: {str(e)}",
                repository_id=repo_id,
                metadata={"error": str(e)}
            ))
            
            raise CredentialError(f"Failed to remove credentials for repository {repo_id}: {e}")

    def resolve_credentials(self, repo_id: str, credential_type: str = 'password') -> Optional[str]:
        """
        Resolve credentials using fallback order: stored -> environment -> interactive.
        
        Args:
            repo_id: Repository identifier
            credential_type: Type of credential to resolve ('password', 'access_key', etc.)
            
        Returns:
            Optional[str]: Resolved credential value, None if not found
        """
        try:
            # Step 1: Try stored credentials
            if not self.credential_manager.is_locked():
                if credential_type == 'password':
                    stored_password = self.credential_manager.get_repository_password(repo_id)
                    if stored_password:
                        logger.debug(f"Resolved {credential_type} for {repo_id} from stored credentials")
                        return stored_password
                else:
                    # Try backend credentials
                    backend_types = ['s3', 'b2', 'sftp', 'local']
                    for backend_type in backend_types:
                        backend_creds = self.credential_manager.get_repository_backend_credentials(
                            repo_id, backend_type
                        )
                        if backend_creds and credential_type in backend_creds:
                            logger.debug(f"Resolved {credential_type} for {repo_id} from {backend_type} backend credentials")
                            return backend_creds[credential_type]
            
            # Step 2: Try environment variables
            env_var_name = f"TIMELOCKER_{repo_id.upper()}_{credential_type.upper()}"
            env_value = os.getenv(env_var_name)
            if env_value:
                logger.debug(f"Resolved {credential_type} for {repo_id} from environment variable {env_var_name}")
                return env_value
            
            # Generic environment variables
            if credential_type == 'password':
                generic_env = os.getenv('TIMELOCKER_REPOSITORY_PASSWORD')
                if generic_env:
                    logger.debug(f"Resolved {credential_type} for {repo_id} from generic environment variable")
                    return generic_env
            
            # Step 3: Interactive prompt (if supported)
            try:
                import getpass
                prompt_message = f"Enter {credential_type} for repository '{repo_id}': "
                if credential_type == 'password':
                    interactive_value = getpass.getpass(prompt_message)
                else:
                    interactive_value = input(prompt_message)
                
                if interactive_value:
                    logger.debug(f"Resolved {credential_type} for {repo_id} from interactive prompt")
                    return interactive_value
                    
            except (KeyboardInterrupt, EOFError):
                logger.debug(f"Interactive prompt cancelled for {credential_type} of {repo_id}")
            except Exception as e:
                logger.debug(f"Interactive prompt failed for {credential_type} of {repo_id}: {e}")
            
            logger.debug(f"Could not resolve {credential_type} for {repo_id} using any method")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving {credential_type} for repository {repo_id}: {e}")
            return None

    def _ensure_credential_manager_unlocked(self) -> bool:
        """
        Ensure the credential manager is unlocked using the resolution chain.
        
        Returns:
            bool: True if credential manager is unlocked, False otherwise
        """
        try:
            # Already unlocked?
            if not self.credential_manager.is_locked():
                return True
            
            # Try to unlock using the credential manager's ensure_unlocked method
            return self.credential_manager.ensure_unlocked(allow_prompt=True)
            
        except Exception as e:
            logger.error(f"Failed to unlock credential manager: {e}")
            return False

    def list_repository_credentials(self) -> List[str]:
        """
        List all repositories that have stored credentials.
        
        Returns:
            List[str]: List of repository identifiers with stored credentials
        """
        try:
            if self.credential_manager.is_locked():
                return []
            
            return self.credential_manager.list_repositories()
            
        except Exception as e:
            logger.error(f"Failed to list repository credentials: {e}")
            return []

    def has_credentials(self, repo_id: str) -> bool:
        """
        Check if a repository has any stored credentials.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            bool: True if repository has stored credentials
        """
        try:
            if self.credential_manager.is_locked():
                return False
            
            # Check for repository password
            password = self.credential_manager.get_repository_password(repo_id)
            if password:
                return True
            
            # Check for backend credentials
            backend_types = ['s3', 'b2', 'sftp', 'local']
            for backend_type in backend_types:
                if self.credential_manager.has_repository_backend_credentials(repo_id, backend_type):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check credentials for repository {repo_id}: {e}")
            return False

    def get_credential_metadata(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about stored credentials without exposing sensitive data.
        
        Args:
            repo_id: Repository identifier
            
        Returns:
            Optional[Dict]: Credential metadata if found, None otherwise
        """
        try:
            if self.credential_manager.is_locked():
                return None
            
            metadata = self.credential_manager.get_credential_metadata(repo_id)
            if metadata:
                # Add backend credential information
                backend_types = ['s3', 'b2', 'sftp', 'local']
                backend_info = {}
                for backend_type in backend_types:
                    if self.credential_manager.has_repository_backend_credentials(repo_id, backend_type):
                        backend_info[backend_type] = True
                
                if backend_info:
                    metadata['backend_credentials'] = backend_info
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get credential metadata for repository {repo_id}: {e}")
            return None