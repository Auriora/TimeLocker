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
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Credential:
    """Represents a credential with metadata"""
    value: str
    source: str  # e.g., 'environment', 'keyring', 'config', 'prompt'
    is_secure: bool = True  # Whether credential should be handled securely


class ICredentialProvider(ABC):
    """
    Abstract interface for credential management.
    
    This interface follows the Single Responsibility Principle by focusing
    solely on credential access and management, and supports the
    Dependency Inversion Principle by abstracting credential sources.
    """

    @abstractmethod
    def get_credential(self,
                       key: str,
                       repository_name: Optional[str] = None,
                       prompt_if_missing: bool = False) -> Optional[Credential]:
        """
        Get a credential by key.
        
        Args:
            key: Credential key (e.g., 'password', 'access_key')
            repository_name: Optional repository name for scoped credentials
            prompt_if_missing: Whether to prompt user if credential not found
            
        Returns:
            Credential object if found, None otherwise
        """
        pass

    @abstractmethod
    def set_credential(self,
                       key: str,
                       value: str,
                       repository_name: Optional[str] = None,
                       persist: bool = True) -> None:
        """
        Set a credential value.
        
        Args:
            key: Credential key
            value: Credential value
            repository_name: Optional repository name for scoped credentials
            persist: Whether to persist credential for future use
        """
        pass

    @abstractmethod
    def remove_credential(self,
                          key: str,
                          repository_name: Optional[str] = None) -> bool:
        """
        Remove a credential.
        
        Args:
            key: Credential key
            repository_name: Optional repository name for scoped credentials
            
        Returns:
            True if credential was removed, False if not found
        """
        pass

    @abstractmethod
    def has_credential(self,
                       key: str,
                       repository_name: Optional[str] = None) -> bool:
        """
        Check if a credential exists.
        
        Args:
            key: Credential key
            repository_name: Optional repository name for scoped credentials
            
        Returns:
            True if credential exists, False otherwise
        """
        pass

    @abstractmethod
    def get_environment_credential(self, env_var: str) -> Optional[Credential]:
        """
        Get credential from environment variable.
        
        Args:
            env_var: Environment variable name
            
        Returns:
            Credential object if found, None otherwise
        """
        pass

    @abstractmethod
    def get_keyring_credential(self,
                               service: str,
                               username: str) -> Optional[Credential]:
        """
        Get credential from system keyring.
        
        Args:
            service: Service name
            username: Username
            
        Returns:
            Credential object if found, None otherwise
        """
        pass

    @abstractmethod
    def set_keyring_credential(self,
                               service: str,
                               username: str,
                               password: str) -> None:
        """
        Set credential in system keyring.
        
        Args:
            service: Service name
            username: Username
            password: Password to store
            
        Raises:
            CredentialError: If credential cannot be stored
        """
        pass

    @abstractmethod
    def prompt_for_credential(self,
                              prompt: str,
                              is_password: bool = True) -> Optional[Credential]:
        """
        Prompt user for credential input.
        
        Args:
            prompt: Prompt message to display
            is_password: Whether to hide input (password field)
            
        Returns:
            Credential object if provided, None if cancelled
        """
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """
        Clear any cached credentials.
        """
        pass


class CredentialError(Exception):
    """Exception raised by credential operations"""
    pass


class CredentialNotFoundError(CredentialError):
    """Exception raised when credential is not found"""
    pass


class CredentialAccessError(CredentialError):
    """Exception raised when credential cannot be accessed"""
    pass
