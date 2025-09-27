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
from typing import Dict, Any, Optional, List
from pathlib import Path


class IConfigurationProvider(ABC):
    """
    Abstract interface for configuration management.
    
    This interface follows the Single Responsibility Principle by focusing
    solely on configuration access and management, and supports the
    Dependency Inversion Principle by abstracting configuration sources.
    """

    @abstractmethod
    def load_configuration(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from source.
        
        Args:
            config_path: Optional specific configuration file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        pass

    @abstractmethod
    def save_configuration(self,
                           config: Dict[str, Any],
                           config_path: Optional[Path] = None) -> None:
        """
        Save configuration to source.
        
        Args:
            config: Configuration dictionary to save
            config_path: Optional specific configuration file path
            
        Raises:
            ConfigurationError: If configuration cannot be saved
        """
        pass

    @abstractmethod
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        pass

    @abstractmethod
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a specific configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            value: Value to set
        """
        pass

    @abstractmethod
    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Get list of configured repositories.
        
        Returns:
            List of repository configurations
        """
        pass

    @abstractmethod
    def add_repository(self, repository_config: Dict[str, Any]) -> None:
        """
        Add a new repository configuration.
        
        Args:
            repository_config: Repository configuration dictionary
            
        Raises:
            ConfigurationError: If repository configuration is invalid
        """
        pass

    @abstractmethod
    def remove_repository(self, repository_name: str) -> bool:
        """
        Remove a repository configuration.
        
        Args:
            repository_name: Name of repository to remove
            
        Returns:
            True if repository was removed, False if not found
        """
        pass

    @abstractmethod
    def get_backup_targets(self) -> List[Dict[str, Any]]:
        """
        Get list of configured backup targets.
        
        Returns:
            List of backup target configurations
        """
        pass

    @abstractmethod
    def add_backup_target(self, target_config: Dict[str, Any]) -> None:
        """
        Add a new backup target configuration.
        
        Args:
            target_config: Backup target configuration dictionary
            
        Raises:
            ConfigurationError: If target configuration is invalid
        """
        pass

    @abstractmethod
    def remove_backup_target(self, target_name: str) -> bool:
        """
        Remove a backup target configuration.
        
        Args:
            target_name: Name of backup target to remove
            
        Returns:
            True if target was removed, False if not found
        """
        pass

    @abstractmethod
    def get_default_config_path(self) -> Path:
        """
        Get the default configuration file path.
        
        Returns:
            Path to default configuration file
        """
        pass

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and values.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass


class ConfigurationError(Exception):
    """Exception raised by configuration operations"""
    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Exception raised when configuration file is not found"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Exception raised when configuration is invalid"""
    pass
