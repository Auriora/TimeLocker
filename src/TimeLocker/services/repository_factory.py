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

import logging
from typing import Dict, List, Type, Optional
from urllib.parse import urlparse

from ..interfaces import IRepositoryFactory, RepositoryFactoryError, UnsupportedSchemeError
from ..backup_repository import BackupRepository
from . import ValidationService
from ..utils import with_error_handling, ErrorContext

logger = logging.getLogger(__name__)


class RepositoryFactory(IRepositoryFactory):
    """
    Concrete implementation of repository factory following Abstract Factory pattern.
    
    This factory supports the Open/Closed Principle by allowing new repository
    types to be registered without modifying existing code, and follows the
    Single Responsibility Principle by focusing solely on repository creation.
    """

    def __init__(self, validation_service: Optional[ValidationService] = None):
        """
        Initialize repository factory.
        
        Args:
            validation_service: Optional validation service for URI validation
        """
        self._repository_types: Dict[str, Type[BackupRepository]] = {}
        self._validation_service = validation_service or ValidationService()
        self._register_default_types()
        logger.debug("RepositoryFactory initialized")

    def _register_default_types(self) -> None:
        """Register default repository types"""
        try:
            # Import and register built-in repository types
            from ..restic.Repositories.local import LocalResticRepository
            self.register_repository_type('local', LocalResticRepository)
            self.register_repository_type('file', LocalResticRepository)
            logger.debug("Registered default repository types")
        except ImportError as e:
            logger.warning(f"Could not register default repository types: {e}")

    @with_error_handling("register_repository_type", "RepositoryFactory")
    def register_repository_type(self,
                                 scheme: str,
                                 repository_class: Type[BackupRepository]) -> None:
        """
        Register a repository implementation for a specific URI scheme.
        
        Args:
            scheme: URI scheme (e.g., 'local', 's3', 'b2')
            repository_class: Repository implementation class
            
        Raises:
            RepositoryFactoryError: If registration fails
        """
        if not scheme:
            raise RepositoryFactoryError("URI scheme cannot be empty")

        if not issubclass(repository_class, BackupRepository):
            raise RepositoryFactoryError(
                    f"Repository class must inherit from BackupRepository: {repository_class}"
            )

        scheme = scheme.lower()

        if scheme in self._repository_types:
            logger.warning(f"Overriding existing repository type for scheme: {scheme}")

        self._repository_types[scheme] = repository_class
        logger.debug(f"Registered repository type '{repository_class.__name__}' for scheme '{scheme}'")

    @with_error_handling("create_repository", "RepositoryFactory")
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
            UnsupportedSchemeError: If URI scheme is not supported
            RepositoryFactoryError: If repository creation fails
        """
        # Validate URI format
        validation_result = self._validation_service.validate_repository_uri(uri)
        if not validation_result.is_valid:
            raise RepositoryFactoryError(
                    f"Invalid repository URI: {', '.join(validation_result.errors)}"
            )

        # Parse URI to extract scheme
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'local'

        # Check if scheme is supported
        if not self.is_scheme_supported(scheme):
            raise UnsupportedSchemeError(
                    f"Unsupported URI scheme '{scheme}'. "
                    f"Supported schemes: {', '.join(self.get_supported_schemes())}"
            )

        # Get repository class and create instance
        repository_class = self._repository_types[scheme]

        try:
            # Create repository instance with appropriate parameters
            logger.debug(f"Repository factory received password: {'***' if password else 'None'}")
            if password:
                kwargs['password'] = password
                logger.debug("Password added to kwargs")

            # Use from_parsed_uri class method if available, otherwise fall back to constructor
            if hasattr(repository_class, 'from_parsed_uri'):
                logger.debug(f"Using from_parsed_uri with kwargs: {list(kwargs.keys())}")
                repository = repository_class.from_parsed_uri(parsed, **kwargs)
            else:
                logger.debug(f"Using constructor with kwargs: {list(kwargs.keys())}")
                repository = repository_class(uri, **kwargs)

            logger.info(f"Created {repository_class.__name__} for URI: {uri}")
            return repository

        except Exception as e:
            raise RepositoryFactoryError(f"Failed to create repository: {e}") from e

    def get_supported_schemes(self) -> List[str]:
        """
        Get list of supported URI schemes.
        
        Returns:
            List of supported URI schemes
        """
        return list(self._repository_types.keys())

    def is_scheme_supported(self, scheme: str) -> bool:
        """
        Check if a URI scheme is supported.
        
        Args:
            scheme: URI scheme to check
            
        Returns:
            True if scheme is supported, False otherwise
        """
        return scheme.lower() in self._repository_types

    def get_repository_class(self, scheme: str) -> Optional[Type[BackupRepository]]:
        """
        Get repository class for a specific scheme.
        
        Args:
            scheme: URI scheme
            
        Returns:
            Repository class if found, None otherwise
        """
        return self._repository_types.get(scheme.lower())

    def unregister_repository_type(self, scheme: str) -> bool:
        """
        Unregister a repository type.
        
        Args:
            scheme: URI scheme to unregister
            
        Returns:
            True if scheme was unregistered, False if not found
        """
        scheme = scheme.lower()
        if scheme in self._repository_types:
            del self._repository_types[scheme]
            logger.debug(f"Unregistered repository type for scheme: {scheme}")
            return True
        return False

    def get_repository_info(self) -> Dict[str, str]:
        """
        Get information about registered repository types.
        
        Returns:
            Dictionary mapping schemes to repository class names
        """
        return {
                scheme: repo_class.__name__
                for scheme, repo_class in self._repository_types.items()
        }


# Global factory instance for convenience
repository_factory = RepositoryFactory()
