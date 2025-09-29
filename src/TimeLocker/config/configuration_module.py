"""
Unified configuration module for TimeLocker.

This module provides a unified facade for configuration management following
SOLID principles and serving as the single entry point for all configuration operations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from threading import RLock
from datetime import datetime

from .configuration_schema import TimeLockerConfig, RepositoryConfig, BackupTargetConfig
from .configuration_defaults import ConfigurationDefaults
from .configuration_validator import ConfigurationValidator, ValidationResult
from .configuration_path_resolver import ConfigurationPathResolver
from .configuration_migrator import ConfigurationMigrator, MigrationResult
from ..interfaces.configuration_provider import IConfigurationProvider
from ..interfaces.exceptions import ConfigurationError, InvalidConfigurationError, RepositoryNotFoundError

logger = logging.getLogger(__name__)


class ConfigurationModule(IConfigurationProvider):
    """
    Unified configuration module following SOLID principles.

    This class serves as a facade for all configuration operations, providing
    a clean interface while delegating specific responsibilities to specialized
    components.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration module.

        Args:
            config_dir: Optional specific configuration directory
        """
        self._config_dir = config_dir or ConfigurationPathResolver.get_config_directory()
        self._config_file = ConfigurationPathResolver.get_config_file_path(self._config_dir)

        # Initialize components
        self._validator = ConfigurationValidator()
        self._migrator = ConfigurationMigrator(self._validator)
        self._path_resolver = ConfigurationPathResolver()

        # Configuration cache and synchronization
        self._config_cache: Optional[TimeLockerConfig] = None
        self._cache_lock = RLock()  # Use RLock to prevent deadlocks from recursive calls
        self._last_modified: Optional[datetime] = None

        # Initialize configuration
        self._initialize_configuration()

    @property
    def config_file(self) -> Path:
        """Get configuration file path"""
        return self._config_file

    @property
    def config_dir(self) -> Path:
        """Get configuration directory path"""
        return self._config_dir

    def _initialize_configuration(self) -> None:
        """Initialize configuration system"""
        try:
            # Ensure directories exist
            self._path_resolver.ensure_directories_exist(self._config_dir)

            # Check for migration needs
            if self._path_resolver.should_migrate_from_legacy():
                self._perform_migration()

            # Load or create configuration
            if not self._config_file.exists():
                self._create_default_configuration()

            # Load configuration into cache
            self._load_configuration()

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigurationError(f"Configuration initialization failed: {e}")

    def _perform_migration(self) -> None:
        """Perform migration from legacy configuration"""
        legacy_dir = self._path_resolver.get_legacy_config_directory()

        logger.info(f"Migrating configuration from {legacy_dir} to {self._config_dir}")

        result = self._migrator.migrate_directory(legacy_dir, self._config_dir)

        if not result.success:
            error_msg = f"Migration failed: {'; '.join(result.errors)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        for message in result.messages:
            logger.info(f"Migration: {message}")

        for warning in result.warnings:
            logger.warning(f"Migration warning: {warning}")

    def _create_default_configuration(self) -> None:
        """Create default configuration file"""
        logger.info(f"Creating default configuration at {self._config_file}")

        default_config = ConfigurationDefaults.get_default_config()

        # Apply environment overrides
        default_config = ConfigurationDefaults.apply_environment_overrides(default_config)

        # Validate default configuration
        validation_result = self._validator.validate_config(default_config)
        if not validation_result:
            error_msg = f"Default configuration is invalid: {'; '.join(validation_result.errors)}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

        # Save default configuration
        self._save_config_to_file(default_config)

    def _load_configuration(self) -> None:
        """Load configuration from file with project > user precedence"""
        try:
            # Load base (user/system) configuration
            with open(self._config_file, 'r') as f:
                base_data = json.load(f)

            # Optionally load project-level overrides
            merged_data = base_data
            try:
                project_path = ConfigurationPathResolver.get_project_config_file_path()
                if project_path.exists():
                    with open(project_path, 'r') as pf:
                        project_data = json.load(pf)

                    def _deep_merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
                        result = dict(d1)
                        for k, v in d2.items():
                            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                                result[k] = _deep_merge(result[k], v)
                            else:
                                result[k] = v
                        return result

                    merged_data = _deep_merge(base_data, project_data)
            except Exception as pe:
                # Do not fail CLI completions or normal runs due to project file issues
                logger.debug(f"Project config overlay skipped: {pe}")

            # Convert to TimeLockerConfig
            config = TimeLockerConfig.from_dict(merged_data)

            # Apply environment overrides
            config = ConfigurationDefaults.apply_environment_overrides(config)

            # Validate configuration
            validation_result = self._validator.validate_config(config)
            if not validation_result:
                error_msg = f"Configuration validation failed: {'; '.join(validation_result.errors)}"
                logger.error(error_msg)
                raise InvalidConfigurationError(error_msg)

            # Log warnings at DEBUG level to avoid console display during normal operations
            for warning in validation_result.warnings:
                logger.debug(f"Configuration warning: {warning}")

            # Update cache (track base file mtime)
            with self._cache_lock:
                self._config_cache = config
                self._last_modified = datetime.fromtimestamp(self._config_file.stat().st_mtime)

            logger.debug("Configuration loaded successfully (with project overlay if present)")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def _save_config_to_file(self, config: TimeLockerConfig) -> None:
        """Save configuration to file"""
        try:
            # Create backup of existing configuration
            if self._config_file.exists():
                self._create_backup()

            # Ensure directory exists
            self._config_file.parent.mkdir(parents=True, exist_ok=True)

            # Save configuration
            # Include a backward-compatibility alias for 'settings' expected by older UX/tests
            output_data = config.to_dict()
            try:
                # Only include keys that make sense under legacy 'settings'
                legacy_settings = {}
                if getattr(config.general, 'default_repository', None):
                    legacy_settings['default_repository'] = config.general.default_repository
                if legacy_settings:
                    output_data['settings'] = legacy_settings
            except Exception:
                # Best-effort; do not fail saving due to compatibility mapping
                pass

            with open(self._config_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            # Update cache
            with self._cache_lock:
                self._config_cache = config
                self._last_modified = datetime.fromtimestamp(self._config_file.stat().st_mtime)

            logger.debug("Configuration saved successfully")

        except Exception as e:
            error_msg = f"Failed to save configuration: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def _create_backup(self) -> None:
        """Create backup of current configuration"""
        backup_dir = self._path_resolver.get_backup_directory(self._config_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"config_backup_{timestamp}.json"

        try:
            import shutil
            shutil.copy2(self._config_file, backup_file)
            logger.debug(f"Created configuration backup: {backup_file}")
        except Exception as e:
            logger.warning(f"Failed to create configuration backup: {e}")

    def _check_for_updates(self) -> None:
        """Check if configuration file has been updated externally"""
        if not self._config_file.exists():
            return

        current_modified = datetime.fromtimestamp(self._config_file.stat().st_mtime)

        # Check if reload is needed without holding lock
        needs_reload = False
        with self._cache_lock:
            if self._last_modified is None or current_modified > self._last_modified:
                needs_reload = True

        # Reload outside of lock check to avoid recursive locking
        if needs_reload:
            logger.debug("Configuration file updated externally, reloading")
            self._load_configuration()

    # IConfigurationProvider implementation

    def load_configuration(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from source"""
        if config_path:
            # Load from specific path
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")
        else:
            # Load current configuration
            config = self.get_config()
            return config.to_dict()

    def save_configuration(self, config: Dict[str, Any], config_path: Optional[Path] = None) -> None:
        """Save configuration to source"""
        if config_path:
            # Save to specific path
            try:
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}")
        else:
            # Save to current configuration file
            timelocker_config = TimeLockerConfig.from_dict(config)
            self.save_config(timelocker_config)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation"""
        config = self.get_config()
        config_dict = config.to_dict()

        keys = key.split('.')
        current = config_dict

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def set_config_value(self, key: str, value: Any) -> None:
        """Set a specific configuration value using dot notation"""
        config = self.get_config()
        config_dict = config.to_dict()

        keys = key.split('.')
        current = config_dict

        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Save updated configuration
        updated_config = TimeLockerConfig.from_dict(config_dict)
        self.save_config(updated_config)

    def get_default_config_path(self) -> Path:
        """Get the default configuration file path"""
        return self._config_file

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and values"""
        try:
            validation_result = self._validator.validate_config(config)
            if not validation_result:
                error_msg = f"Configuration validation failed: {'; '.join(validation_result.errors)}"
                raise ConfigurationError(error_msg)
            return True
        except Exception as e:
            raise ConfigurationError(f"Configuration validation error: {e}")

    # Extended interface methods (beyond IConfigurationProvider)

    def get_config(self) -> TimeLockerConfig:
        """Get complete configuration"""
        # Check for updates first (this may trigger a reload)
        self._check_for_updates()

        # Return cached config with minimal lock time
        with self._cache_lock:
            if self._config_cache is None:
                # This should rarely happen after _check_for_updates()
                # but we handle it for safety
                logger.debug("Cache miss in get_config, loading configuration")
                # Release lock and reload (avoid recursive locking)
                pass
            else:
                return self._config_cache

        # Handle cache miss outside of lock
        if self._config_cache is None:
            self._load_configuration()

        with self._cache_lock:
            if self._config_cache is None:
                raise ConfigurationError("Failed to load configuration")
            return self._config_cache


    def get_configuration(self) -> Dict[str, Any]:
        """Get complete configuration as a plain dictionary (legacy-compatible).
        Returns a JSON-serializable dict representing current configuration.
        """
        cfg = self.get_config()
        return cfg.to_dict()

    def save_config(self, config: Optional[TimeLockerConfig] = None) -> None:
        """Save complete configuration.

        If config is None, save the current in-memory configuration.
        """
        if config is None:
            config = self.get_config()
        # Validate before saving
        validation_result = self._validator.validate_config(config)
        if not validation_result:
            error_msg = f"Configuration validation failed: {'; '.join(validation_result.errors)}"
            raise InvalidConfigurationError(error_msg)

        self._save_config_to_file(config)

    def get_section(self, section_name: Any) -> Dict[str, Any]:
        """Get configuration section.

        Accepts string names or legacy enum values (ConfigSection). Provides
        alias mapping for backward compatibility (e.g., 'settings' -> 'general').
        """
        # Coerce enum values to their string value
        try:
            section_key = section_name.value  # type: ignore[attr-defined]
        except Exception:
            section_key = str(section_name)

        # Backward-compatibility alias
        alias_map = {
                'settings': 'general',
        }
        section_key = alias_map.get(section_key, section_key)

        config = self.get_config()
        config_dict = config.to_dict()

        if section_key not in config_dict:
            raise ConfigurationError(f"Configuration section '{section_key}' not found")

        return config_dict[section_key]

    def update_section(self, section_name: Any, section_data: Dict[str, Any]) -> None:
        """Update configuration section

        Accepts string or legacy enum (ConfigSection) for section_name.
        """
        # Coerce enum values to string
        try:
            section_key = section_name.value  # type: ignore[attr-defined]
        except Exception:
            section_key = str(section_name)

        config = self.get_config()
        config_dict = config.to_dict()

        # Backward-compatibility: accept legacy/alias section names
        alias_map = {
                'settings': 'general',  # legacy umbrella section used in older UX tests
        }
        target_section = alias_map.get(section_key, section_key)

        if target_section not in config_dict:
            # Be tolerant: ignore unknown sections to improve UX
            logger.debug(f"Ignoring update for unknown configuration section '{section_key}'")
            return

        # If mapping from 'settings', only apply known keys
        if section_name == 'settings':
            filtered = {}
            if 'default_repository' in section_data:
                filtered['default_repository'] = section_data['default_repository']
            section_data = filtered

        # Merge dictionaries when possible; otherwise replace
        if isinstance(config_dict[target_section], dict):
            config_dict[target_section].update(section_data)
        else:
            config_dict[target_section] = section_data

        updated_config = TimeLockerConfig.from_dict(config_dict)
        self.save_config(updated_config)

    def get_repositories(self) -> List[Dict[str, Any]]:
        """Get list of configured repositories"""
        repositories = self.get_config().repositories
        return [repo.to_dict() if hasattr(repo, 'to_dict') else repo.__dict__ for repo in repositories.values()]

    def get_default_repository(self) -> Optional[str]:
        """Get the default repository name"""
        config = self.get_config()
        return getattr(config.general, 'default_repository', None)

    def set_default_repository(self, name: str) -> None:
        """Set the default repository name"""
        # First verify the repository exists
        if name not in self.get_config().repositories:
            from ..interfaces.exceptions import RepositoryNotFoundError
            raise RepositoryNotFoundError(f"Repository '{name}' not found")

        # Update the configuration
        config = self.get_config()
        config.general.default_repository = name

        # Save the updated configuration
        self.save_config(config)
        logger.info(f"Default repository set to: {name}")

    def get_repository(self, name: str) -> RepositoryConfig:
        """Get specific repository configuration"""
        repositories_dict = self.get_config().repositories
        if name not in repositories_dict:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")
        return repositories_dict[name]

    def add_repository(self, repository_config: Union[Dict[str, Any], RepositoryConfig]) -> None:
        """Add repository configuration"""
        config = self.get_config()

        if isinstance(repository_config, dict):
            # Create a copy to avoid modifying original data
            repo_data_copy = repository_config.copy()
            # Extract name and remove from data to avoid duplicate parameter
            name = repo_data_copy.pop('name')
            # Convert dict to RepositoryConfig
            repo = RepositoryConfig(name=name, **repo_data_copy)
        else:
            repo = repository_config

        config.repositories[repo.name] = repo
        self.save_config(config)

    def remove_repository(self, repository_name: str) -> None:
        """Remove repository configuration"""
        config = self.get_config()
        if repository_name not in config.repositories:
            raise RepositoryNotFoundError(f"Repository '{repository_name}' not found")

        # Clear default repository if it's the one being removed
        if config.general.default_repository == repository_name:
            config.general.default_repository = None

        del config.repositories[repository_name]
        self.save_config(config)
        logger.info(f"Repository '{repository_name}' removed successfully")

    def get_backup_targets(self) -> List[Dict[str, Any]]:
        """Get list of configured backup targets"""
        targets = self.get_config().backup_targets
        return [target.to_dict() if hasattr(target, 'to_dict') else target.__dict__ for target in targets.values()]

    def get_backup_target(self, name: str) -> BackupTargetConfig:
        """Get specific backup target configuration"""
        targets_dict = self.get_config().backup_targets
        if name not in targets_dict:
            raise ConfigurationError(f"Backup target '{name}' not found")
        return targets_dict[name]

    def add_backup_target(self, target_config: Union[Dict[str, Any], BackupTargetConfig]) -> None:
        """Add backup target configuration"""
        config = self.get_config()

        if isinstance(target_config, dict):
            # Convert dict to BackupTargetConfig
            target = BackupTargetConfig(**target_config)
        else:
            target = target_config

        config.backup_targets[target.name] = target
        self.save_config(config)

    def remove_backup_target(self, target_name: str) -> bool:
        """Remove backup target configuration"""
        config = self.get_config()
        if target_name not in config.backup_targets:
            return False

        del config.backup_targets[target_name]
        self.save_config(config)
        return True

    def update_backup_target(self, target_name: str, target_config: Union[Dict[str, Any], BackupTargetConfig]) -> None:
        """Update backup target configuration"""
        config = self.get_config()
        if target_name not in config.backup_targets:
            raise ConfigurationError(f"Backup target '{target_name}' not found")

        if isinstance(target_config, dict):
            # Convert dict to BackupTargetConfig, preserving the name
            target_config_copy = target_config.copy()
            target_config_copy['name'] = target_name
            target = BackupTargetConfig(**target_config_copy)
        else:
            target = target_config
            target.name = target_name

        config.backup_targets[target_name] = target
        self.save_config(config)
        logger.info(f"Backup target '{target_name}' updated successfully")

    def validate_current_configuration(self) -> ValidationResult:
        """Validate current configuration and return detailed result"""
        config = self.get_config()
        return self._validator.validate_config(config)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        logger.warning("Resetting configuration to defaults")

        # Create backup first
        if self._config_file.exists():
            self._create_backup()

        # Create and save default configuration
        default_config = ConfigurationDefaults.get_default_config()
        default_config = ConfigurationDefaults.apply_environment_overrides(default_config)

        self.save_config(default_config)

    def get_path_info(self) -> Dict[str, Any]:
        """Get configuration path information"""
        return self._path_resolver.get_path_info()

    def reload_configuration(self) -> None:
        """Force reload configuration from file"""
        logger.debug("Forcing configuration reload")

        # Clear cache first
        with self._cache_lock:
            self._config_cache = None
            self._last_modified = None

        # Reload configuration
        self._load_configuration()

    # Additional utility methods

    def export_configuration(self, export_path: Path) -> None:
        """Export configuration to specified path"""
        config = self.get_config()

        try:
            with open(export_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Configuration exported to {export_path}")
        except Exception as e:
            error_msg = f"Failed to export configuration: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def import_configuration(self, import_path: Path) -> None:
        """Import configuration from specified path"""
        if not import_path.exists():
            raise ConfigurationError(f"Import file does not exist: {import_path}")

        try:
            with open(import_path, 'r') as f:
                config_data = json.load(f)

            config = TimeLockerConfig.from_dict(config_data)
            self.save_config(config)
            logger.info(f"Configuration imported from {import_path}")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in import file: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        except Exception as e:
            error_msg = f"Failed to import configuration: {e}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary for display"""
        config = self.get_config()

        summary = {
                "general":        {
                        "app_name":           config.general.app_name,
                        "version":            config.general.version,
                        "log_level":          config.general.log_level.value if hasattr(config.general.log_level, 'value') else config.general.log_level,
                        "data_dir":           config.general.data_dir,
                        "default_repository": config.general.default_repository
                },
                "repositories":   {
                        "count": len(config.repositories),
                        "names": list(config.repositories.keys())
                },
                "backup_targets": {
                        "count": len(config.backup_targets),
                        "names": list(config.backup_targets.keys())
                },
                "security":       {
                        "encryption_enabled": config.security.encryption_enabled,
                        "audit_logging":      config.security.audit_logging
                },
                "monitoring":     {
                        "metrics_enabled":        config.monitoring.metrics_enabled,
                        "performance_monitoring": config.monitoring.performance_monitoring
                }
        }
        # Provide aggregate counts for UX/tests
        try:
            general_keys = [k for k in summary["general"].keys()]
            total_settings = len(general_keys)
        except Exception:
            total_settings = 0
        summary["total_settings"] = total_settings
        summary["total_repositories"] = summary["repositories"]["count"]
        summary["total_backup_targets"] = summary["backup_targets"]["count"]

        return summary

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about configuration paths and status

        Returns:
            Dict: Configuration information including paths and migration status
        """
        from .configuration_path_resolver import ConfigurationPathResolver

        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
        current_dir = self.config_dir
        project_file = ConfigurationPathResolver.get_project_config_file_path()

        return {
                "current_config_dir":      str(current_dir),
                "current_config_file":     str(self.config_file),
                "project_config_file":     str(project_file),
                "project_config_exists":   project_file.exists(),
                "is_system_context":       ConfigurationPathResolver.is_system_context(),
                "xdg_config_home":         os.environ.get('XDG_CONFIG_HOME', 'not set'),
                "legacy_config_dir":       str(legacy_dir),
                "legacy_config_exists":    (legacy_dir / "config.json").exists(),
                "migration_marker_exists": (current_dir / ".migrated_from_legacy").exists(),
                "config_file_exists":      self.config_file.exists(),
                "backup_dir":              str(self.backup_dir) if hasattr(self, 'backup_dir') else "N/A",
                "backup_count":            0  # ConfigurationModule doesn't use backup system
        }

    # ------------------------------------------------------------------
    # Backward-compatibility aliases (legacy API)
    # ------------------------------------------------------------------
    def get_config_summary(self) -> Dict[str, Any]:
        """Deprecated alias for get_configuration_summary."""
        return self.get_configuration_summary()

    def import_config(self, import_path: Path) -> bool:
        """Deprecated alias for import_configuration.

        Legacy behavior: return False instead of raising on failure.
        """
        try:
            self.import_configuration(import_path)
            return True
        except Exception as _:
            # Align with tests expecting graceful handling
            return False

    def get(self, section_name: str) -> Dict[str, Any]:
        """Deprecated alias for get_section."""
        return self.get_section(section_name)
