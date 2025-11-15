"""
Unified configuration module for TimeLocker.

This module provides a unified facade for configuration management following
SOLID principles and serving as the single entry point for all configuration operations.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from threading import RLock
from datetime import datetime, timedelta

from .configuration_schema import TimeLockerConfig, RepositoryConfig, BackupTargetConfig
from .configuration_defaults import ConfigurationDefaults
from .configuration_validator import ConfigurationValidator, ValidationResult
from .configuration_path_resolver import ConfigurationPathResolver
from .configuration_migrator import ConfigurationMigrator, MigrationResult
from .configuration_lock_manager import ConfigurationLockManager
from .configuration_backup_manager import ConfigurationBackupManager, BackupReason
from .configuration_watcher import ConfigurationWatcher
from .configuration_transaction_manager import ConfigurationTransactionManager
from .configuration_performance_monitor import ConfigurationPerformanceMonitor
from .configuration_error_handler import ConfigurationErrorHandler, RecoveryAction
from .security_configuration_manager import SecurityConfigurationManager
from .security_configuration_ui import SecurityConfigurationUI
from .security_configuration_migrator import SecurityConfigurationMigrator
from ..interfaces.configuration_provider import IConfigurationProvider
from ..interfaces.exceptions import (
    ConfigurationError, 
    InvalidConfigurationError, 
    RepositoryNotFoundError,
    ConfigurationLockError,
    ConfigurationLockTimeoutError
)

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
        self._lock_manager = ConfigurationLockManager(self._config_dir / "locks")
        self._backup_manager = ConfigurationBackupManager(
            self._path_resolver.get_backup_directory(self._config_dir),
            self._validator
        )
        self._watcher = ConfigurationWatcher(self._config_file)
        self._transaction_manager = ConfigurationTransactionManager(
            self._config_file,
            self._lock_manager,
            self._backup_manager
        )
        self._performance_monitor = ConfigurationPerformanceMonitor()
        self._error_handler = ConfigurationErrorHandler(
            self._backup_manager,
            self._lock_manager,
            self._performance_monitor
        )
        
        # Security configuration components
        self._security_config_manager = SecurityConfigurationManager(self)
        self._security_config_ui = SecurityConfigurationUI(self._security_config_manager)
        self._security_config_migrator = SecurityConfigurationMigrator(self._config_dir)

        # Enhanced caching
        self._section_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_max_age = timedelta(minutes=5)  # Cache sections for 5 minutes

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
        """Save configuration to file with locking"""
        lock_acquired = False
        try:
            # Acquire lock before making changes
            lock_acquired = self._lock_manager.acquire_lock(self._config_file, timeout=30)
            if not lock_acquired:
                raise ConfigurationLockTimeoutError("Could not acquire lock for configuration save")

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
        finally:
            # Always release lock if we acquired it
            if lock_acquired:
                try:
                    self._lock_manager.release_lock(self._config_file)
                except Exception as e:
                    logger.warning(f"Failed to release configuration lock: {e}")

    def _create_backup(self, reason: BackupReason = BackupReason.AUTOMATIC) -> Optional[str]:
        """Create backup of current configuration using enhanced backup manager"""
        try:
            backup_id = self._backup_manager.create_backup(self._config_file, reason)
            logger.debug(f"Created configuration backup: {backup_id}")
            return backup_id
        except Exception as e:
            logger.warning(f"Failed to create configuration backup: {e}")
            return None

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
        # Invalidate section cache to ensure callers observe updated values
        self._section_cache.clear()
        self._cache_timestamps.clear()

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

    @property
    def performance_monitor(self) -> ConfigurationPerformanceMonitor:
        """Get the performance monitor instance"""
        return self._performance_monitor

    def get_config(self) -> TimeLockerConfig:
        """Get complete configuration with performance monitoring"""
        start_time = time.time()
        cache_hit = False
        
        try:
            needs_reload = False

            # Check for updates and cache status while holding lock
            with self._cache_lock:
                # Check if file has been updated externally
                if self._config_file.exists():
                    current_modified = datetime.fromtimestamp(self._config_file.stat().st_mtime)
                    if self._last_modified is None or current_modified > self._last_modified:
                        needs_reload = True
                    elif self._config_cache is not None:
                        cache_hit = True
                        self._performance_monitor.track_cache_hit()
                        return self._config_cache
                elif self._config_cache is not None:
                    cache_hit = True
                    self._performance_monitor.track_cache_hit()
                    return self._config_cache

            # Cache miss - need to load configuration
            if not cache_hit:
                self._performance_monitor.track_cache_miss()

            # Load configuration outside of lock to avoid recursive locking in _load_configuration
            if needs_reload:
                logger.debug("Configuration file updated externally, reloading")
            self._load_configuration()

            # Return the loaded config
            with self._cache_lock:
                if self._config_cache is None:
                    raise ConfigurationError("Failed to load configuration")
                return self._config_cache
                
        finally:
            # Track operation performance
            duration = time.time() - start_time
            self._performance_monitor.track_operation('get_config', duration, True)


    def get_configuration(self) -> Dict[str, Any]:
        """Get complete configuration as a plain dictionary (legacy-compatible).
        Returns a JSON-serializable dict representing current configuration.
        """
        cfg = self.get_config()
        return cfg.to_dict()

    def save_config(self, config: Optional[TimeLockerConfig] = None) -> None:
        """Save complete configuration with error handling and recovery.

        If config is None, save the current in-memory configuration.
        """
        saved_config: Optional[TimeLockerConfig] = None

        def _save_operation():
            nonlocal saved_config
            if config is None:
                current_config = self.get_config()
            else:
                current_config = config
                
            # Validate before saving
            validation_result = self._validator.validate_config(current_config)
            if not validation_result:
                error_msg = f"Configuration validation failed: {'; '.join(validation_result.errors)}"
                raise InvalidConfigurationError(error_msg)

            self._save_config_to_file(current_config)
            saved_config = current_config
        
        # Execute with error handling and retry
        try:
            self._error_handler.retry_with_backoff(
                _save_operation,
                "save_config",
                context_data={'config_file': str(self._config_file)}
            )
        except Exception as e:
            # Handle the error and attempt recovery
            recovery_action = self._error_handler.handle_error(
                e, 
                "save_config",
                {'config_file': str(self._config_file)}
            )
            
            if recovery_action == RecoveryAction.RESTORE_BACKUP:
                logger.warning("Attempting to restore from backup after save failure")
                # The error handler will handle the restoration
            
            # Re-raise the exception after handling
            raise e
        else:
            if saved_config is not None:
                with self._cache_lock:
                    self._config_cache = saved_config
                    try:
                        self._last_modified = datetime.fromtimestamp(self._config_file.stat().st_mtime)
                    except FileNotFoundError:
                        self._last_modified = None
                self._section_cache.clear()
                self._cache_timestamps.clear()

    def get_section(self, section_name: Any) -> Dict[str, Any]:
        """Get configuration section with caching and performance monitoring.

        Accepts string names or legacy enum values (ConfigSection). Provides
        alias mapping for backward compatibility (e.g., 'settings' -> 'general').
        """
        start_time = time.time()
        
        try:
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

            # Check section cache first
            cache_key = f"section_{section_key}"
            now = datetime.now()
            
            if (cache_key in self._section_cache and 
                cache_key in self._cache_timestamps and
                now - self._cache_timestamps[cache_key] < self._cache_max_age):
                
                self._performance_monitor.track_cache_hit()
                return self._section_cache[cache_key].copy()  # Return copy to prevent modification
            
            # Cache miss - get from full config
            self._performance_monitor.track_cache_miss()
            config = self.get_config()
            config_dict = config.to_dict()

            if section_key not in config_dict:
                raise ConfigurationError(f"Configuration section '{section_key}' not found")

            section_data = config_dict[section_key]
            
            # Update section cache
            self._section_cache[cache_key] = section_data.copy()
            self._cache_timestamps[cache_key] = now
            
            # Update cache size metrics
            self._performance_monitor.update_cache_size(len(self._section_cache), 50)  # Max 50 sections
            
            # Clean up old cache entries if needed
            self._cleanup_section_cache()

            return section_data
            
        finally:
            # Track operation performance
            duration = time.time() - start_time
            self._performance_monitor.track_operation('get_section', duration, True)

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
        self._section_cache.clear()
        self._cache_timestamps.clear()

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

    def update_repository(self, repository_name: str, repository_config: Union[Dict[str, Any], RepositoryConfig]) -> None:
        """Update existing repository configuration"""
        config = self.get_config()

        # Check if repository exists
        if repository_name not in config.repositories:
            raise RepositoryNotFoundError(f"Repository '{repository_name}' not found")

        if isinstance(repository_config, dict):
            # Get existing repository
            existing_repo = config.repositories[repository_name]
            existing_dict = existing_repo.to_dict() if hasattr(existing_repo, 'to_dict') else existing_repo.__dict__

            # Merge with new configuration
            existing_dict.update(repository_config)

            # Ensure name is set correctly
            existing_dict['name'] = repository_name

            # Map legacy 'uri' field to 'location' (same as from_dict does)
            if 'uri' in existing_dict:
                existing_dict['location'] = existing_dict.pop('uri')

            # Remove legacy fields not supported by RepositoryConfig
            legacy_fields = ['type', 'created', 'encryption']
            for field in legacy_fields:
                existing_dict.pop(field, None)

            # Convert dict to RepositoryConfig
            repo = RepositoryConfig(name=repository_name, **{k: v for k, v in existing_dict.items() if k != 'name'})
        else:
            repo = repository_config

        config.repositories[repository_name] = repo
        self.save_config(config)
        logger.debug(f"Repository '{repository_name}' updated successfully")

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
    # Configuration Locking Methods
    # ------------------------------------------------------------------

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
        try:
            return self._lock_manager.acquire_lock(self._config_file, timeout)
        except Exception as e:
            logger.error(f"Failed to acquire configuration lock: {e}")
            raise ConfigurationLockError(f"Lock acquisition failed: {e}")

    def release_lock(self) -> None:
        """
        Release the configuration lock.
        
        Raises:
            ConfigurationLockError: If lock cannot be released
        """
        try:
            self._lock_manager.release_lock(self._config_file)
        except Exception as e:
            logger.error(f"Failed to release configuration lock: {e}")
            raise ConfigurationLockError(f"Lock release failed: {e}")

    def is_locked(self) -> bool:
        """
        Check if configuration is currently locked.
        
        Returns:
            True if configuration is locked
        """
        return self._lock_manager.is_locked(self._config_file)

    def get_lock_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current configuration lock.
        
        Returns:
            Lock information if locked, None if not locked
        """
        lock_info = self._lock_manager.get_lock_info(self._config_file)
        if lock_info:
            return {
                'lock_id': lock_info.lock_id,
                'acquired_at': lock_info.acquired_at.isoformat(),
                'expires_at': lock_info.expires_at.isoformat(),
                'process_id': lock_info.process_id,
                'operation': lock_info.operation,
                'sections': lock_info.sections
            }
        return None

    def cleanup_stale_locks(self) -> int:
        """
        Clean up stale configuration locks.
        
        Returns:
            Number of stale locks cleaned up
        """
        return self._lock_manager.cleanup_stale_locks()

    # ------------------------------------------------------------------
    # Enhanced Backup Management Methods
    # ------------------------------------------------------------------

    def create_backup(self, reason: BackupReason = BackupReason.MANUAL, 
                     tags: Optional[List[str]] = None) -> str:
        """
        Create a backup of the current configuration.
        
        Args:
            reason: Reason for creating the backup
            tags: Optional tags for the backup
            
        Returns:
            Backup identifier
            
        Raises:
            ConfigurationBackupError: If backup creation fails
        """
        return self._backup_manager.create_backup(self._config_file, reason, tags)

    def list_backups(self, limit: Optional[int] = None, 
                    reason_filter: Optional[BackupReason] = None) -> List[Dict[str, Any]]:
        """
        List available configuration backups.
        
        Args:
            limit: Maximum number of backups to return
            reason_filter: Filter backups by reason
            
        Returns:
            List of backup information dictionaries
        """
        return self._backup_manager.list_backups(limit, reason_filter)

    def restore_backup(self, backup_id: str) -> bool:
        """
        Restore configuration from a backup.
        
        Args:
            backup_id: Backup identifier to restore
            
        Returns:
            True if restore was successful
            
        Raises:
            ConfigurationBackupError: If backup restoration fails
        """
        return self._backup_manager.restore_backup(backup_id, self._config_file)

    def compare_backups(self, backup_id1: str, backup_id2: str) -> Dict[str, Any]:
        """
        Compare two configuration backups.
        
        Args:
            backup_id1: First backup to compare
            backup_id2: Second backup to compare
            
        Returns:
            Comparison result with differences
            
        Raises:
            ConfigurationBackupError: If comparison fails
        """
        return self._backup_manager.compare_backups(backup_id1, backup_id2)

    def restore_section(self, backup_id: str, section: str) -> bool:
        """
        Restore a specific section from a backup.
        
        Args:
            backup_id: Backup identifier
            section: Section name to restore
            
        Returns:
            True if section restore was successful
            
        Raises:
            ConfigurationBackupError: If section restoration fails
        """
        return self._backup_manager.restore_section(backup_id, section, self._config_file)

    def cleanup_old_backups(self, keep_count: int = 5, max_age_days: Optional[int] = None) -> int:
        """
        Clean up old configuration backups.
        
        Args:
            keep_count: Number of recent backups to keep
            max_age_days: Maximum age in days for backups
            
        Returns:
            Number of backups cleaned up
        """
        return self._backup_manager.cleanup_old_backups(keep_count, max_age_days)

    def validate_backup(self, backup_id: str) -> ValidationResult:
        """
        Validate a configuration backup.
        
        Args:
            backup_id: Backup identifier to validate
            
        Returns:
            Validation result
        """
        return self._backup_manager.validate_backup(backup_id)

    # ------------------------------------------------------------------
    # Configuration Change Watching Methods
    # ------------------------------------------------------------------

    def watch_section(self, section: str, callback: Callable) -> str:
        """
        Watch for changes to a specific configuration section.
        
        Args:
            section: Section name to watch
            callback: Function to call when section changes
            
        Returns:
            Watch identifier for later removal
            
        Raises:
            ConfigurationWatchError: If watching cannot be established
        """
        return self._watcher.watch_section(section, callback)

    def watch_key(self, key: str, callback: Callable) -> str:
        """
        Watch for changes to a specific configuration key.
        
        Args:
            key: Configuration key to watch (supports dot notation)
            callback: Function to call when key changes
            
        Returns:
            Watch identifier for later removal
            
        Raises:
            ConfigurationWatchError: If watching cannot be established
        """
        return self._watcher.watch_key(key, callback)

    def unwatch(self, watch_id: str) -> None:
        """
        Remove a configuration watch.
        
        Args:
            watch_id: Watch identifier to remove
            
        Raises:
            ConfigurationWatchError: If watch cannot be removed
        """
        self._watcher.unwatch(watch_id)

    def start_watching(self) -> None:
        """
        Start the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be started
        """
        self._watcher.start_watching()

    def stop_watching(self) -> None:
        """
        Stop the configuration watching system.
        
        Raises:
            ConfigurationWatchError: If watching cannot be stopped
        """
        self._watcher.stop_watching()

    def get_change_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent configuration change history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent change events as dictionaries
        """
        events = self._watcher.get_change_history(limit)
        return [
            {
                'event_id': event.event_id,
                'timestamp': event.timestamp.isoformat(),
                'section': event.section,
                'key': event.key,
                'old_value': event.old_value,
                'new_value': event.new_value,
                'source': event.source,
                'user_context': event.user_context,
                'transaction_id': event.transaction_id
            }
            for event in events
        ]

    def is_watching(self) -> bool:
        """
        Check if the configuration watcher is currently active.
        
        Returns:
            True if watching is active
        """
        return self._watcher.is_watching()

    def get_watch_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configuration watching.
        
        Returns:
            Statistics including watch count, event count, etc.
        """
        return self._watcher.get_watch_statistics()

    # ------------------------------------------------------------------
    # Transaction Support Methods
    # ------------------------------------------------------------------

    def begin_transaction(self, timeout_minutes: int = 5) -> str:
        """
        Begin a new configuration transaction.
        
        Args:
            timeout_minutes: Transaction timeout in minutes
            
        Returns:
            Transaction identifier
            
        Raises:
            ConfigurationError: If transaction cannot be started
        """
        from datetime import timedelta
        timeout = timedelta(minutes=timeout_minutes)
        return self._transaction_manager.begin_transaction(timeout)

    def commit_transaction(self, transaction_id: str) -> bool:
        """
        Commit a configuration transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            True if commit was successful
            
        Raises:
            ConfigurationError: If commit fails
        """
        return self._transaction_manager.commit_transaction(transaction_id)

    def rollback_transaction(self, transaction_id: str) -> bool:
        """
        Rollback a configuration transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            True if rollback was successful
            
        Raises:
            ConfigurationError: If rollback fails
        """
        return self._transaction_manager.rollback_transaction(transaction_id)

    def atomic_update(self, updates: Dict[str, Dict[str, Any]]) -> bool:
        """
        Perform atomic update of multiple configuration sections.
        
        Args:
            updates: Dictionary mapping section names to their new data
            
        Returns:
            True if all updates were successful
            
        Raises:
            ConfigurationAtomicUpdateError: If atomic update fails
        """
        return self._transaction_manager.atomic_update(updates)

    def get_transaction_info(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Transaction information or None if not found
        """
        return self._transaction_manager.get_transaction_info(transaction_id)

    def list_active_transactions(self) -> List[Dict[str, Any]]:
        """
        List all active transactions.
        
        Returns:
            List of active transaction information
        """
        return self._transaction_manager.list_active_transactions()

    def cleanup_expired_transactions(self) -> int:
        """
        Clean up expired transactions.
        
        Returns:
            Number of transactions cleaned up
        """
        return self._transaction_manager.cleanup_expired_transactions()

    # ------------------------------------------------------------------
    # Performance Monitoring and Optimization Methods
    # ------------------------------------------------------------------

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        return self._performance_monitor.get_performance_metrics()

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        return self._performance_monitor.get_cache_statistics()

    def optimize_cache(self) -> Dict[str, Any]:
        """
        Analyze cache performance and provide optimization recommendations.
        
        Returns:
            Optimization recommendations
        """
        return self._performance_monitor.optimize_cache()

    def get_optimization_recommendations(self) -> List[str]:
        """
        Get performance optimization recommendations.
        
        Returns:
            List of optimization recommendations
        """
        return self._performance_monitor.get_recommendations()

    def clear_performance_metrics(self) -> None:
        """Clear all performance metrics and caches"""
        self._performance_monitor.clear_metrics()
        self._section_cache.clear()
        self._cache_timestamps.clear()

    def enable_performance_monitoring(self) -> None:
        """Enable performance monitoring"""
        self._performance_monitor.enable_monitoring()

    def disable_performance_monitoring(self) -> None:
        """Disable performance monitoring"""
        self._performance_monitor.disable_monitoring()

    # ------------------------------------------------------------------
    # Error Handling and Recovery Methods
    # ------------------------------------------------------------------

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and trends.
        
        Returns:
            Error statistics dictionary
        """
        return self._error_handler.get_error_statistics()

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent error information.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error information
        """
        return self._error_handler.get_recent_errors(limit)

    def add_error_callback(self, callback: Callable) -> None:
        """
        Add a callback for error notifications.
        
        Args:
            callback: Function to call when errors occur
        """
        self._error_handler.add_error_callback(callback)

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults with error handling"""
        try:
            logger.warning("Resetting configuration to defaults")

            # Create backup first
            if self._config_file.exists():
                try:
                    self._backup_manager.create_backup(
                        self._config_file, 
                        BackupReason.PRE_UPDATE,
                        ["reset_to_defaults"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to create backup before reset: {e}")

            # Create and save default configuration
            default_config = ConfigurationDefaults.get_default_config()
            default_config = ConfigurationDefaults.apply_environment_overrides(default_config)

            self.save_config(default_config)
            
            # Clear caches
            self._section_cache.clear()
            self._cache_timestamps.clear()
            
            logger.info("Configuration successfully reset to defaults")
            
        except Exception as e:
            recovery_action = self._error_handler.handle_error(
                e, 
                "reset_to_defaults",
                {'config_file': str(self._config_file)}
            )
            
            if recovery_action != RecoveryAction.FAIL:
                logger.info("Attempting recovery after reset failure")
            
            raise ConfigurationError(f"Failed to reset configuration to defaults: {e}")

    def recover_from_corruption(self) -> bool:
        """
        Attempt to recover from configuration corruption.
        
        Returns:
            True if recovery was successful
        """
        try:
            logger.warning("Attempting to recover from configuration corruption")
            
            # Try to restore from the most recent backup
            backups = self._backup_manager.list_backups(limit=5)
            
            for backup in backups:
                try:
                    backup_id = backup['backup_id']
                    logger.info(f"Attempting to restore from backup: {backup_id}")
                    
                    # Validate backup before restoration
                    validation_result = self._backup_manager.validate_backup(backup_id)
                    if validation_result.is_valid:
                        success = self._backup_manager.restore_backup(backup_id, self._config_file)
                        if success:
                            # Clear caches after restoration
                            self._section_cache.clear()
                            self._cache_timestamps.clear()
                            
                            # Reload configuration
                            self._load_configuration()
                            
                            logger.info(f"Successfully recovered from backup: {backup_id}")
                            return True
                    else:
                        logger.warning(f"Backup {backup_id} is invalid: {validation_result.errors}")
                        
                except Exception as e:
                    logger.warning(f"Failed to restore from backup {backup_id}: {e}")
                    continue
            
            # If no backups work, reset to defaults as last resort
            logger.warning("No valid backups found, resetting to defaults")
            self.reset_to_defaults()
            return True
            
        except Exception as e:
            logger.error(f"Failed to recover from corruption: {e}")
            return False

    def validate_and_repair(self) -> Dict[str, Any]:
        """
        Validate configuration and attempt automatic repairs.
        
        Returns:
            Validation and repair results
        """
        try:
            config = self.get_config()
            validation_result = self._validator.validate_config(config)
            
            repair_results = {
                'validation_passed': validation_result.is_valid,
                'errors_found': len(validation_result.errors),
                'warnings_found': len(validation_result.warnings),
                'repairs_attempted': 0,
                'repairs_successful': 0,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            }
            
            if not validation_result.is_valid:
                logger.warning(f"Configuration validation failed with {len(validation_result.errors)} errors")
                
                # Attempt automatic repairs for common issues
                config_dict = config.to_dict()
                repaired = False
                
                # Try to repair missing sections
                defaults = ConfigurationDefaults.get_default_config().to_dict()
                for section_name, default_section in defaults.items():
                    if section_name not in config_dict:
                        config_dict[section_name] = default_section
                        repair_results['repairs_attempted'] += 1
                        repaired = True
                        logger.info(f"Repaired missing section: {section_name}")
                
                # Try to repair invalid enum values
                for section_name, section_data in config_dict.items():
                    if isinstance(section_data, dict):
                        for key, value in section_data.items():
                            # Check for invalid log levels
                            if key == 'log_level' and isinstance(value, str):
                                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                                if value.upper() not in valid_levels:
                                    section_data[key] = 'INFO'
                                    repair_results['repairs_attempted'] += 1
                                    repaired = True
                                    logger.info(f"Repaired invalid log level: {value} -> INFO")
                
                if repaired:
                    try:
                        # Save repaired configuration
                        repaired_config = TimeLockerConfig.from_dict(config_dict)
                        self.save_config(repaired_config)
                        repair_results['repairs_successful'] = repair_results['repairs_attempted']
                        
                        # Re-validate
                        new_validation = self._validator.validate_config(repaired_config)
                        repair_results['validation_passed'] = new_validation.is_valid
                        repair_results['errors_found'] = len(new_validation.errors)
                        
                    except Exception as e:
                        logger.error(f"Failed to save repaired configuration: {e}")
            
            return repair_results
            
        except Exception as e:
            logger.error(f"Configuration validation and repair failed: {e}")
            return {
                'validation_passed': False,
                'error': str(e),
                'repairs_attempted': 0,
                'repairs_successful': 0
            }

    def _cleanup_section_cache(self) -> None:
        """Clean up expired section cache entries"""
        now = datetime.now()
        expired_keys = []
        
        for cache_key, timestamp in self._cache_timestamps.items():
            if now - timestamp > self._cache_max_age:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            self._section_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._performance_monitor.track_cache_eviction()
        
        # Also limit cache size
        if len(self._section_cache) > 50:
            # Remove oldest entries
            sorted_items = sorted(self._cache_timestamps.items(), key=lambda x: x[1])
            for key, _ in sorted_items[:len(self._section_cache) - 40]:  # Keep 40, remove excess
                self._section_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
                self._performance_monitor.track_cache_eviction()

    # ------------------------------------------------------------------
    # Security Configuration Management Methods
    # ------------------------------------------------------------------

    def get_security_configuration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive security configuration status.
        
        Returns:
            Dict: Security configuration status information
        """
        try:
            status = self._security_config_manager.get_security_configuration_status()
            return {
                "is_valid": status.is_valid,
                "security_level": status.security_level,
                "issues_count": status.issues_count,
                "warnings_count": status.warnings_count,
                "last_validated": status.last_validated.isoformat(),
                "recommendations": status.recommendations,
                "compliance_score": status.compliance_score
            }
        except Exception as e:
            logger.error(f"Failed to get security configuration status: {e}")
            return {"error": str(e)}

    def validate_security_configuration(self, validation_level: str = "moderate") -> ValidationResult:
        """
        Validate security configuration with specified level.
        
        Args:
            validation_level: Validation strictness ("strict", "moderate", "permissive")
            
        Returns:
            ValidationResult: Validation results
        """
        try:
            from .security_configuration_manager import SecurityValidationLevel
            
            level_mapping = {
                "strict": SecurityValidationLevel.STRICT,
                "moderate": SecurityValidationLevel.MODERATE,
                "permissive": SecurityValidationLevel.PERMISSIVE
            }
            
            level = level_mapping.get(validation_level, SecurityValidationLevel.MODERATE)
            config = self.get_config()
            
            return self._security_config_manager.validate_security_config(config.security, level)
            
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Failed to validate security configuration: {e}")
            return result

    def update_security_configuration(self, updates: Dict[str, Any], validate: bool = True) -> ValidationResult:
        """
        Update security configuration settings.
        
        Args:
            updates: Dictionary of security configuration updates
            validate: Whether to validate before applying updates
            
        Returns:
            ValidationResult: Update operation results
        """
        return self._security_config_manager.update_security_configuration(updates, validate)

    def reset_security_configuration(self) -> ValidationResult:
        """
        Reset security configuration to defaults.
        
        Returns:
            ValidationResult: Reset operation results
        """
        return self._security_config_manager.reset_security_configuration()

    def get_security_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get security configuration recommendations.
        
        Returns:
            List: Security recommendations with priorities
        """
        return self._security_config_manager.get_security_recommendations()

    def apply_security_recommendations(self, recommendation_ids: List[str]) -> ValidationResult:
        """
        Apply selected security recommendations.
        
        Args:
            recommendation_ids: List of recommendation IDs to apply
            
        Returns:
            ValidationResult: Application results
        """
        return self._security_config_manager.apply_security_recommendations(recommendation_ids)

    def export_security_configuration(self, output_path: Path, include_sensitive: bool = False) -> bool:
        """
        Export security configuration to file.
        
        Args:
            output_path: Path to export file
            include_sensitive: Whether to include sensitive settings
            
        Returns:
            bool: True if export successful
        """
        return self._security_config_manager.export_security_configuration(output_path, include_sensitive)

    def import_security_configuration(self, import_path: Path, validate: bool = True) -> ValidationResult:
        """
        Import security configuration from file.
        
        Args:
            import_path: Path to import file
            validate: Whether to validate imported configuration
            
        Returns:
            ValidationResult: Import operation results
        """
        return self._security_config_manager.import_security_configuration(import_path, validate)

    def get_security_configuration_summary(self) -> Dict[str, Any]:
        """
        Get security configuration summary for display.
        
        Returns:
            Dict: Security configuration summary
        """
        return self._security_config_manager.get_security_configuration_summary()

    def migrate_security_configuration(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate security configuration to target version.
        
        Args:
            target_version: Target version (defaults to current)
            
        Returns:
            Dict: Migration operation results
        """
        try:
            config = self.get_config()
            security_dict = config.security.__dict__.copy()
            
            result = self._security_config_migrator.migrate_security_configuration(
                security_dict, target_version
            )
            
            if result.success:
                # Update configuration with migrated data
                from .configuration_schema import SecurityConfig
                config.security = SecurityConfig(**security_dict)
                self.save_config(config)
                
            return {
                "success": result.success,
                "from_version": result.from_version,
                "to_version": result.to_version,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
                "warnings": result.warnings,
                "backup_created": result.backup_created,
                "migration_time": result.migration_time.total_seconds() if result.migration_time else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to migrate security configuration: {e}")
            return {
                "success": False,
                "errors": [str(e)],
                "warnings": [],
                "steps_completed": []
            }

    # ------------------------------------------------------------------
    # Security Configuration UI Methods
    # ------------------------------------------------------------------

    def create_security_configuration_form(self) -> Dict[str, Any]:
        """
        Create security configuration form UI components.
        
        Returns:
            Dict: Form component definitions
        """
        try:
            config = self.get_config()
            security_dict = config.security.__dict__
            return self._security_config_ui.create_security_configuration_form(security_dict)
        except Exception as e:
            logger.error(f"Failed to create security configuration form: {e}")
            return {"error": str(e)}

    def create_security_status_display(self) -> Dict[str, Any]:
        """
        Create security status display UI components.
        
        Returns:
            Dict: Status display component definitions
        """
        try:
            status_data = self.get_security_configuration_summary()
            return self._security_config_ui.create_security_status_display(status_data)
        except Exception as e:
            logger.error(f"Failed to create security status display: {e}")
            return {"error": str(e)}

    def create_security_validation_display(self) -> Dict[str, Any]:
        """
        Create security validation display UI components.
        
        Returns:
            Dict: Validation display component definitions
        """
        try:
            validation_result = self.validate_security_configuration()
            return self._security_config_ui.create_validation_display(validation_result)
        except Exception as e:
            logger.error(f"Failed to create security validation display: {e}")
            return {"error": str(e)}

    def create_security_recommendations_display(self) -> Dict[str, Any]:
        """
        Create security recommendations display UI components.
        
        Returns:
            Dict: Recommendations display component definitions
        """
        try:
            recommendations = self.get_security_recommendations()
            return self._security_config_ui.create_recommendations_display(recommendations)
        except Exception as e:
            logger.error(f"Failed to create security recommendations display: {e}")
            return {"error": str(e)}

    def create_security_dashboard(self) -> Dict[str, Any]:
        """
        Create comprehensive security dashboard UI.
        
        Returns:
            Dict: Dashboard component definitions
        """
        try:
            security_data = {
                "status": self.get_security_configuration_summary(),
                "configuration": self.get_config().security.__dict__,
                "validation": self.validate_security_configuration(),
                "recommendations": self.get_security_recommendations()
            }
            return self._security_config_ui.create_security_dashboard(security_data)
        except Exception as e:
            logger.error(f"Failed to create security dashboard: {e}")
            return {"error": str(e)}

    def handle_security_ui_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle security configuration UI events.
        
        Args:
            event_type: Type of UI event
            event_data: Event data
            
        Returns:
            Dict: Event handling results
        """
        return self._security_config_ui.handle_ui_event(event_type, event_data)

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
