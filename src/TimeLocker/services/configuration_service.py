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

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import copy

from ..interfaces import (
    IConfigurationProvider,
    ConfigurationError,
    ConfigurationNotFoundError,
    InvalidConfigurationError
)
from . import ValidationService
from ..utils import with_error_handling, ErrorContext

logger = logging.getLogger(__name__)


class ConfigurationService(IConfigurationProvider):
    """
    Concrete implementation of configuration provider following SRP.
    
    This service focuses solely on configuration management, separating
    concerns from the original ConfigurationManager which mixed multiple
    responsibilities.
    """

    def __init__(self,
                 config_path: Optional[Path] = None,
                 validation_service: Optional[ValidationService] = None):
        """
        Initialize configuration service.
        
        Args:
            config_path: Optional specific configuration file path
            validation_service: Optional validation service
        """
        self._config_path = config_path
        self._validation_service = validation_service or ValidationService()
        self._config_data: Dict[str, Any] = {}
        self._defaults = self._get_default_config()

        # Load configuration on initialization
        if config_path and config_path.exists():
            self.load_configuration(config_path)
        else:
            self._config_data = copy.deepcopy(self._defaults)

        logger.debug(f"ConfigurationService initialized with path: {config_path}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure"""
        return {
                "general":        {
                        "app_name":  "TimeLocker",
                        "version":   "1.0.0",
                        "log_level": "INFO"
                },
                "repositories":   {},
                "backup_targets": {},
                "backup":         {
                        "compression":         "auto",
                        "exclude_caches":      True,
                        "verify_after_backup": True
                },
                "restore":        {
                        "verify_after_restore":    True,
                        "create_target_directory": True
                },
                "security":       {
                        "encryption_enabled": True,
                        "audit_logging":      True
                }
        }

    @with_error_handling("load_configuration", "ConfigurationService")
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
        path_to_load = config_path or self._config_path

        if not path_to_load:
            raise ConfigurationError("No configuration path specified")

        if not path_to_load.exists():
            raise ConfigurationNotFoundError(f"Configuration file not found: {path_to_load}")

        try:
            with open(path_to_load, 'r') as f:
                loaded_config = json.load(f)

            # Merge with defaults to ensure all required keys exist
            self._config_data = self._merge_with_defaults(loaded_config)

            # Validate the loaded configuration
            if not self.validate_configuration(self._config_data):
                raise InvalidConfigurationError("Configuration validation failed")

            logger.info(f"Configuration loaded successfully from: {path_to_load}")
            return self._config_data.copy()

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    @with_error_handling("save_configuration", "ConfigurationService")
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
        path_to_save = config_path or self._config_path

        if not path_to_save:
            raise ConfigurationError("No configuration path specified")

        # Validate configuration before saving
        if not self.validate_configuration(config):
            raise InvalidConfigurationError("Configuration validation failed")

        try:
            # Ensure parent directory exists
            path_to_save.parent.mkdir(parents=True, exist_ok=True)

            # Save configuration
            with open(path_to_save, 'w') as f:
                json.dump(config, f, indent=2, default=str)

            # Update internal state
            self._config_data = config.copy()

            logger.info(f"Configuration saved successfully to: {path_to_save}")

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        current = self._config_data

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a specific configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            value: Value to set
        """
        keys = key.split('.')
        current = self._config_data

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the final value
        current[keys[-1]] = value

    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Get list of configured repositories.

        Returns:
            List of repository configurations
        """
        repositories_dict = self._config_data.get('repositories', {})
        return [
                {**repo_config, 'name': name}
                for name, repo_config in repositories_dict.items()
        ]

    def get_repository_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific repository configuration by name.

        Args:
            name: Repository name

        Returns:
            Repository configuration dictionary

        Raises:
            ConfigurationNotFoundError: If repository is not found
        """
        repositories_dict = self._config_data.get('repositories', {})

        if name not in repositories_dict:
            raise ConfigurationNotFoundError(f"Repository '{name}' not found")

        # Return repository config with name included
        return {**repositories_dict[name], 'name': name}

    def add_repository(self, repository_config: Dict[str, Any]) -> None:
        """
        Add a new repository configuration.
        
        Args:
            repository_config: Repository configuration dictionary
            
        Raises:
            ConfigurationError: If repository configuration is invalid
        """
        # Validate repository configuration
        validation_result = self._validation_service.validate_repository_config(repository_config)
        if not validation_result.is_valid:
            raise InvalidConfigurationError(
                    f"Invalid repository configuration: {', '.join(validation_result.errors)}"
            )

        name = repository_config['name']
        repositories = self._config_data.setdefault('repositories', {})

        if name in repositories:
            raise ConfigurationError(f"Repository '{name}' already exists")

        # Store repository config without the name (name is the key)
        repo_data = {k: v for k, v in repository_config.items() if k != 'name'}
        repositories[name] = repo_data

        logger.info(f"Added repository configuration: {name}")

    def remove_repository(self, repository_name: str) -> bool:
        """
        Remove a repository configuration.
        
        Args:
            repository_name: Name of repository to remove
            
        Returns:
            True if repository was removed, False if not found
        """
        repositories = self._config_data.get('repositories', {})

        if repository_name in repositories:
            del repositories[repository_name]
            logger.info(f"Removed repository configuration: {repository_name}")
            return True

        return False

    def get_backup_targets(self) -> List[Dict[str, Any]]:
        """
        Get list of configured backup targets.

        Returns:
            List of backup target configurations
        """
        targets_dict = self._config_data.get('backup_targets', {})
        return [
                {**target_config, 'name': name}
                for name, target_config in targets_dict.items()
        ]

    def get_backup_target_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific backup target configuration by name.

        Args:
            name: Backup target name

        Returns:
            Backup target configuration dictionary

        Raises:
            ConfigurationNotFoundError: If backup target is not found
        """
        targets_dict = self._config_data.get('backup_targets', {})

        if name not in targets_dict:
            raise ConfigurationNotFoundError(f"Backup target '{name}' not found")

        # Return target config with name included
        return {**targets_dict[name], 'name': name}

    def add_backup_target(self, target_config: Dict[str, Any]) -> None:
        """
        Add a new backup target configuration.
        
        Args:
            target_config: Backup target configuration dictionary
            
        Raises:
            ConfigurationError: If target configuration is invalid
        """
        # Validate backup target configuration
        validation_result = self._validation_service.validate_backup_target_config(target_config)
        if not validation_result.is_valid:
            raise InvalidConfigurationError(
                    f"Invalid backup target configuration: {', '.join(validation_result.errors)}"
            )

        name = target_config['name']
        targets = self._config_data.setdefault('backup_targets', {})

        if name in targets:
            raise ConfigurationError(f"Backup target '{name}' already exists")

        # Store target config without the name (name is the key)
        target_data = {k: v for k, v in target_config.items() if k != 'name'}
        targets[name] = target_data

        logger.info(f"Added backup target configuration: {name}")

    def remove_backup_target(self, target_name: str) -> bool:
        """
        Remove a backup target configuration.
        
        Args:
            target_name: Name of backup target to remove
            
        Returns:
            True if target was removed, False if not found
        """
        targets = self._config_data.get('backup_targets', {})

        if target_name in targets:
            del targets[target_name]
            logger.info(f"Removed backup target configuration: {target_name}")
            return True

        return False

    def get_default_config_path(self) -> Path:
        """
        Get the default configuration file path.
        
        Returns:
            Path to default configuration file
        """
        if self._config_path:
            return self._config_path

        # Use XDG Base Directory Specification
        from ..config.configuration_manager import ConfigurationPathResolver
        config_dir = ConfigurationPathResolver.get_config_directory()
        return config_dir / "config.json"

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
        try:
            # Check required top-level sections
            required_sections = ['general', 'repositories', 'backup_targets']
            for section in required_sections:
                if section not in config:
                    raise InvalidConfigurationError(f"Missing required section: {section}")

            # Validate repositories
            repositories = config.get('repositories', {})
            for name, repo_config in repositories.items():
                repo_with_name = {**repo_config, 'name': name}
                validation_result = self._validation_service.validate_repository_config(repo_with_name)
                if not validation_result.is_valid:
                    raise InvalidConfigurationError(
                            f"Invalid repository '{name}': {', '.join(validation_result.errors)}"
                    )

            # Validate backup targets
            targets = config.get('backup_targets', {})
            for name, target_config in targets.items():
                target_with_name = {**target_config, 'name': name}
                validation_result = self._validation_service.validate_backup_target_config(target_with_name)
                if not validation_result.is_valid:
                    raise InvalidConfigurationError(
                            f"Invalid backup target '{name}': {', '.join(validation_result.errors)}"
                    )

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge configuration with defaults to ensure all required keys exist.
        
        Args:
            config: Configuration to merge
            
        Returns:
            Merged configuration
        """

        def deep_merge(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively merge dictionaries"""
            result = default.copy()

            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        return deep_merge(self._defaults, config)
