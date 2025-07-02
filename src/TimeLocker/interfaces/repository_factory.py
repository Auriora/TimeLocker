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
from typing import Optional, Dict, List, Type
from TimeLocker.backup_repository import BackupRepository


class IRepositoryFactory(ABC):
    """
    Abstract factory interface for creating backup repositories.
    
    This interface follows the Abstract Factory pattern and supports
    the Open/Closed Principle by allowing new repository types to be
    added without modifying existing code.
    """

    @abstractmethod
    def register_repository_type(self,
                                 scheme: str,
                                 repository_class: Type[BackupRepository]) -> None:
        """
        Register a repository implementation for a specific URI scheme.
        
        Args:
            scheme: URI scheme (e.g., 'local', 's3', 'b2')
            repository_class: Repository implementation class
        """
        pass

    @abstractmethod
    def create_repository(self,
                          uri: str,
                          password: Optional[str] = None,
                          **kwargs) -> BackupRepository:
        """
        Create a repository instance from URI.
        
        Args:
            uri: Repository URI
            password: Optional password for repository
            **kwargs: Additional repository-specific parameters
            
        Returns:
            BackupRepository instance
            
        Raises:
            ValueError: If URI scheme is not supported
            RepositoryError: If repository creation fails
        """
        pass

    @abstractmethod
    def get_supported_schemes(self) -> List[str]:
        """
        Get list of supported URI schemes.
        
        Returns:
            List of supported URI schemes
        """
        pass

    @abstractmethod
    def is_scheme_supported(self, scheme: str) -> bool:
        """
        Check if a URI scheme is supported.
        
        Args:
            scheme: URI scheme to check
            
        Returns:
            True if scheme is supported, False otherwise
        """
        pass


class RepositoryFactoryError(Exception):
    """Exception raised by repository factory operations"""
    pass


class UnsupportedSchemeError(RepositoryFactoryError):
    """Exception raised when URI scheme is not supported"""
    pass
