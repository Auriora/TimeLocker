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

Scheduling Configuration Management

This module provides configuration management for the scheduling system
with validation and persistence capabilities.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .scheduling_models import RetryConfig, MonitoringConfig, ValidationResult
from .scheduling_exceptions import SchedulingError
import platform as platform_module
import shutil

logger = logging.getLogger(__name__)

# Configuration version for migration tracking
CURRENT_CONFIG_VERSION = "1.0.0"


@dataclass
class SchedulingConfiguration:
    """
    Master configuration for scheduling system.
    
    This configuration defines system-wide defaults and preferences
    for the scheduling system.
    """
    
    # Platform preferences: platform name -> preferred scheduler
    platform_preferences: Dict[str, str] = field(default_factory=dict)
    
    # Default retry configuration for all schedules
    default_retry_config: RetryConfig = field(default_factory=lambda: RetryConfig())
    
    # Default monitoring configuration
    default_monitoring_config: MonitoringConfig = field(default_factory=lambda: MonitoringConfig())
    
    # Audit log retention in days
    audit_retention_days: int = 365
    
    # Maximum concurrent backup executions
    max_concurrent_executions: int = 3
    
    # Default execution timeout in minutes
    execution_timeout_minutes: int = 60
    
    # Credential store configuration
    credential_store_config: Dict[str, Any] = field(default_factory=dict)
    
    # Schedule storage directory
    schedule_storage_dir: Optional[Path] = None
    
    # Configuration version for migration tracking
    config_version: str = CURRENT_CONFIG_VERSION
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'SchedulingConfiguration':
        """
        Load configuration from file with validation.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            SchedulingConfiguration: Loaded configuration
            
        Raises:
            SchedulingError: If loading or validation fails
        """
        try:
            if not config_path.exists():
                logger.info(f"Configuration file not found at {config_path}, using defaults")
                return cls()
            
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Convert nested dicts to dataclass instances
            if 'default_retry_config' in data:
                data['default_retry_config'] = RetryConfig(**data['default_retry_config'])
            
            if 'default_monitoring_config' in data:
                data['default_monitoring_config'] = MonitoringConfig(**data['default_monitoring_config'])
            
            if 'schedule_storage_dir' in data and data['schedule_storage_dir']:
                data['schedule_storage_dir'] = Path(data['schedule_storage_dir'])
            
            config = cls(**data)
            
            # Validate loaded configuration
            validation_result = config.validate()
            if not validation_result.is_valid:
                raise SchedulingError(
                    f"Configuration validation failed: {', '.join(validation_result.errors)}",
                    details={"errors": validation_result.errors}
                )
            
            logger.info(f"Successfully loaded configuration from {config_path}")
            return config
            
        except json.JSONDecodeError as e:
            raise SchedulingError(
                f"Failed to parse configuration file: {e}",
                details={"path": str(config_path), "error": str(e)}
            )
        except Exception as e:
            raise SchedulingError(
                f"Failed to load configuration: {e}",
                details={"path": str(config_path), "error": str(e)}
            )
    
    def save_to_file(self, config_path: Path) -> None:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save configuration
            
        Raises:
            SchedulingError: If saving fails
        """
        try:
            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict for JSON serialization
            data = asdict(self)
            
            # Convert Path objects to strings
            if data.get('schedule_storage_dir'):
                data['schedule_storage_dir'] = str(data['schedule_storage_dir'])
            
            # Write configuration
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully saved configuration to {config_path}")
            
        except Exception as e:
            raise SchedulingError(
                f"Failed to save configuration: {e}",
                details={"path": str(config_path), "error": str(e)}
            )
    
    def validate(self) -> ValidationResult:
        """
        Validate configuration for current platform.
        
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Validate audit retention
        if self.audit_retention_days < 1:
            result.add_error("audit_retention_days must be at least 1")
        elif self.audit_retention_days < 30:
            result.add_warning("audit_retention_days less than 30 may not meet compliance requirements")
        
        # Validate concurrent executions
        if self.max_concurrent_executions < 1:
            result.add_error("max_concurrent_executions must be at least 1")
        elif self.max_concurrent_executions > 10:
            result.add_warning("max_concurrent_executions > 10 may impact system performance")
        
        # Validate execution timeout
        if self.execution_timeout_minutes < 1:
            result.add_error("execution_timeout_minutes must be at least 1")
        elif self.execution_timeout_minutes < 5:
            result.add_warning("execution_timeout_minutes < 5 may be too short for most backups")
        
        # Validate schedule storage directory if specified
        if self.schedule_storage_dir:
            if not isinstance(self.schedule_storage_dir, Path):
                result.add_error("schedule_storage_dir must be a Path object")
            elif not self.schedule_storage_dir.exists():
                result.add_warning(f"schedule_storage_dir does not exist: {self.schedule_storage_dir}")
        
        return result
    
    def get_default_config_path(self) -> Path:
        """
        Get default configuration file path.
        
        Returns:
            Path: Default configuration path following XDG conventions
        """
        from ..config import ConfigurationPathResolver
        config_dir = ConfigurationPathResolver.get_config_directory()
        return config_dir / "scheduling" / "config.json"
    
    def get_platform_preference(self, platform: Optional[str] = None) -> Optional[str]:
        """
        Get preferred scheduler for a platform.
        
        Args:
            platform: Platform name (defaults to current platform)
            
        Returns:
            Preferred scheduler name or None if not set
        """
        if platform is None:
            platform = platform_module.system().lower()
        
        return self.platform_preferences.get(platform)
    
    def set_platform_preference(self, platform: str, scheduler: str) -> None:
        """
        Set preferred scheduler for a platform.
        
        Args:
            platform: Platform name (e.g., 'linux', 'darwin', 'windows')
            scheduler: Scheduler name (e.g., 'systemd', 'cron', 'launchd', 'windows_task_scheduler')
        """
        valid_platforms = ['linux', 'darwin', 'windows']
        if platform.lower() not in valid_platforms:
            raise ValueError(f"Invalid platform: {platform}. Must be one of {valid_platforms}")
        
        valid_schedulers = {
            'linux': ['systemd', 'cron'],
            'darwin': ['launchd', 'cron'],
            'windows': ['windows_task_scheduler']
        }
        
        if scheduler not in valid_schedulers.get(platform.lower(), []):
            raise ValueError(
                f"Invalid scheduler '{scheduler}' for platform '{platform}'. "
                f"Valid options: {valid_schedulers.get(platform.lower(), [])}"
            )
        
        self.platform_preferences[platform.lower()] = scheduler
        logger.info(f"Set platform preference: {platform} -> {scheduler}")
    
    def clear_platform_preference(self, platform: str) -> None:
        """
        Clear preferred scheduler for a platform.
        
        Args:
            platform: Platform name
        """
        if platform.lower() in self.platform_preferences:
            del self.platform_preferences[platform.lower()]
            logger.info(f"Cleared platform preference for: {platform}")
    
    def merge_with_defaults(self) -> None:
        """
        Merge configuration with system defaults for any missing values.
        
        This ensures that configurations loaded from older versions
        have sensible defaults for new fields.
        """
        default_config = SchedulingConfiguration()
        
        # Merge platform preferences (don't overwrite existing)
        for platform, scheduler in default_config.platform_preferences.items():
            if platform not in self.platform_preferences:
                self.platform_preferences[platform] = scheduler
        
        # Set defaults for None values
        if self.default_retry_config is None:
            self.default_retry_config = default_config.default_retry_config
        
        if self.default_monitoring_config is None:
            self.default_monitoring_config = default_config.default_monitoring_config
        
        if self.credential_store_config is None:
            self.credential_store_config = default_config.credential_store_config
        
        logger.debug("Merged configuration with defaults")


class SchedulingConfigurationValidator:
    """
    Validator for scheduling configuration.
    
    Provides comprehensive validation of scheduling configurations
    with detailed error reporting.
    """
    
    @staticmethod
    def validate_configuration(config: SchedulingConfiguration) -> ValidationResult:
        """
        Validate a scheduling configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            ValidationResult: Validation result
        """
        return config.validate()
    
    @staticmethod
    def validate_configuration_file(config_path: Path) -> ValidationResult:
        """
        Validate a configuration file without loading it into the system.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            ValidationResult: Validation result
        """
        result = ValidationResult(is_valid=True)
        
        try:
            if not config_path.exists():
                result.add_error(f"Configuration file does not exist: {config_path}")
                return result
            
            # Try to load and validate
            config = SchedulingConfiguration.load_from_file(config_path)
            return config.validate()
            
        except SchedulingError as e:
            result.add_error(str(e))
            return result
        except Exception as e:
            result.add_error(f"Unexpected error validating configuration: {e}")
            return result



class ConfigurationMigrator:
    """
    Handles migration and upgrade of scheduling configurations.
    
    This class provides capabilities to migrate configurations from
    older versions to the current version, ensuring backward compatibility.
    """
    
    @staticmethod
    def needs_migration(config_data: Dict[str, Any]) -> bool:
        """
        Check if configuration data needs migration.
        
        Args:
            config_data: Raw configuration data dictionary
            
        Returns:
            True if migration is needed, False otherwise
        """
        current_version = config_data.get('config_version', '0.0.0')
        return current_version != CURRENT_CONFIG_VERSION
    
    @staticmethod
    def migrate_configuration(config_path: Path) -> SchedulingConfiguration:
        """
        Migrate configuration file to current version.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Migrated SchedulingConfiguration
            
        Raises:
            SchedulingError: If migration fails
        """
        try:
            # Load raw configuration data
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            original_version = config_data.get('config_version', '0.0.0')
            logger.info(f"Migrating configuration from version {original_version} to {CURRENT_CONFIG_VERSION}")
            
            # Create backup before migration
            backup_path = ConfigurationMigrator._create_backup(config_path)
            logger.info(f"Created configuration backup at {backup_path}")
            
            # Apply migrations based on version
            migrated_data = ConfigurationMigrator._apply_migrations(config_data, original_version)
            
            # Update version
            migrated_data['config_version'] = CURRENT_CONFIG_VERSION
            
            # Convert to SchedulingConfiguration
            config = ConfigurationMigrator._data_to_config(migrated_data)
            
            # Validate migrated configuration
            validation_result = config.validate()
            if not validation_result.is_valid:
                raise SchedulingError(
                    f"Migrated configuration validation failed: {', '.join(validation_result.errors)}",
                    details={"errors": validation_result.errors}
                )
            
            # Save migrated configuration
            config.save_to_file(config_path)
            
            logger.info(f"Successfully migrated configuration to version {CURRENT_CONFIG_VERSION}")
            return config
            
        except Exception as e:
            raise SchedulingError(
                f"Configuration migration failed: {e}",
                details={"path": str(config_path), "error": str(e)}
            ) from e
    
    @staticmethod
    def _create_backup(config_path: Path) -> Path:
        """
        Create backup of configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Path to backup file
        """
        from datetime import datetime
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"
        
        shutil.copy2(config_path, backup_path)
        
        return backup_path
    
    @staticmethod
    def _apply_migrations(config_data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """
        Apply version-specific migrations.
        
        Args:
            config_data: Raw configuration data
            from_version: Version to migrate from
            
        Returns:
            Migrated configuration data
        """
        # Migration chain - apply migrations in order
        migrations = [
            ('0.0.0', '1.0.0', ConfigurationMigrator._migrate_0_to_1),
        ]
        
        migrated_data = config_data.copy()
        
        for min_version, target_version, migration_func in migrations:
            if ConfigurationMigrator._version_less_than(from_version, target_version):
                logger.debug(f"Applying migration: {min_version} -> {target_version}")
                migrated_data = migration_func(migrated_data)
        
        return migrated_data
    
    @staticmethod
    def _migrate_0_to_1(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from version 0.x to 1.0.0.
        
        Args:
            config_data: Configuration data
            
        Returns:
            Migrated configuration data
        """
        migrated = config_data.copy()
        
        # Add config_version if missing
        if 'config_version' not in migrated:
            migrated['config_version'] = '1.0.0'
        
        # Add platform_preferences if missing
        if 'platform_preferences' not in migrated:
            migrated['platform_preferences'] = {}
        
        # Add default_retry_config if missing
        if 'default_retry_config' not in migrated:
            migrated['default_retry_config'] = {
                'max_attempts': 3,
                'initial_delay_minutes': 5,
                'backoff_multiplier': 2.0,
                'max_delay_minutes': 60
            }
        
        # Add default_monitoring_config if missing
        if 'default_monitoring_config' not in migrated:
            migrated['default_monitoring_config'] = {
                'webhook_url': None,
                'health_check_url': None,
                'notification_on_success': True,
                'notification_on_failure': True,
                'notification_on_retry': False
            }
        
        # Add audit_retention_days if missing
        if 'audit_retention_days' not in migrated:
            migrated['audit_retention_days'] = 365
        
        # Add max_concurrent_executions if missing
        if 'max_concurrent_executions' not in migrated:
            migrated['max_concurrent_executions'] = 3
        
        # Add execution_timeout_minutes if missing
        if 'execution_timeout_minutes' not in migrated:
            migrated['execution_timeout_minutes'] = 60
        
        # Add credential_store_config if missing
        if 'credential_store_config' not in migrated:
            migrated['credential_store_config'] = {}
        
        # Add schedule_storage_dir if missing
        if 'schedule_storage_dir' not in migrated:
            migrated['schedule_storage_dir'] = None
        
        logger.debug("Applied migration 0.x -> 1.0.0")
        return migrated
    
    @staticmethod
    def _version_less_than(version1: str, version2: str) -> bool:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            True if version1 < version2
        """
        def parse_version(v: str) -> tuple:
            return tuple(int(x) for x in v.split('.'))
        
        try:
            return parse_version(version1) < parse_version(version2)
        except (ValueError, AttributeError):
            # If parsing fails, assume migration is needed
            return True
    
    @staticmethod
    def _data_to_config(config_data: Dict[str, Any]) -> SchedulingConfiguration:
        """
        Convert raw configuration data to SchedulingConfiguration.
        
        Args:
            config_data: Raw configuration data
            
        Returns:
            SchedulingConfiguration instance
        """
        # Convert nested dicts to dataclass instances
        if 'default_retry_config' in config_data and isinstance(config_data['default_retry_config'], dict):
            config_data['default_retry_config'] = RetryConfig(**config_data['default_retry_config'])
        
        if 'default_monitoring_config' in config_data and isinstance(config_data['default_monitoring_config'], dict):
            config_data['default_monitoring_config'] = MonitoringConfig(**config_data['default_monitoring_config'])
        
        if 'schedule_storage_dir' in config_data and config_data['schedule_storage_dir']:
            config_data['schedule_storage_dir'] = Path(config_data['schedule_storage_dir'])
        
        return SchedulingConfiguration(**config_data)
    
    @staticmethod
    def upgrade_configuration(config_path: Path) -> SchedulingConfiguration:
        """
        Upgrade configuration to latest version with enhanced features.
        
        This is different from migration - it adds new optional features
        and optimizations while maintaining compatibility.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Upgraded SchedulingConfiguration
            
        Raises:
            SchedulingError: If upgrade fails
        """
        try:
            # Load existing configuration
            config = SchedulingConfiguration.load_from_file(config_path)
            
            # Merge with defaults to get new features
            config.merge_with_defaults()
            
            # Apply platform-specific optimizations
            ConfigurationMigrator._apply_platform_optimizations(config)
            
            # Save upgraded configuration
            config.save_to_file(config_path)
            
            logger.info("Successfully upgraded configuration with latest features")
            return config
            
        except Exception as e:
            raise SchedulingError(
                f"Configuration upgrade failed: {e}",
                details={"path": str(config_path), "error": str(e)}
            ) from e
    
    @staticmethod
    def _apply_platform_optimizations(config: SchedulingConfiguration) -> None:
        """
        Apply platform-specific optimizations to configuration.
        
        Args:
            config: Configuration to optimize
        """
        current_platform = platform_module.system().lower()
        
        # Set platform-specific defaults if not already set
        if current_platform == 'linux':
            if not config.get_platform_preference('linux'):
                # Prefer systemd on Linux if available
                try:
                    from .platform_detector import PlatformDetector
                    if PlatformDetector._has_systemd():
                        config.set_platform_preference('linux', 'systemd')
                        logger.debug("Set default preference: linux -> systemd")
                    elif PlatformDetector._has_cron():
                        config.set_platform_preference('linux', 'cron')
                        logger.debug("Set default preference: linux -> cron")
                except Exception as e:
                    logger.warning(f"Failed to detect Linux scheduler: {e}")
        
        elif current_platform == 'darwin':
            if not config.get_platform_preference('darwin'):
                # Prefer launchd on macOS
                config.set_platform_preference('darwin', 'launchd')
                logger.debug("Set default preference: darwin -> launchd")
        
        elif current_platform == 'windows':
            if not config.get_platform_preference('windows'):
                # Use Windows Task Scheduler
                config.set_platform_preference('windows', 'windows_task_scheduler')
                logger.debug("Set default preference: windows -> windows_task_scheduler")
        
        # Optimize concurrent executions based on system resources
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            if cpu_count and config.max_concurrent_executions == 3:
                # Adjust based on CPU count (but cap at reasonable limit)
                optimized_count = min(max(2, cpu_count // 2), 8)
                config.max_concurrent_executions = optimized_count
                logger.debug(f"Optimized max_concurrent_executions to {optimized_count} based on {cpu_count} CPUs")
        except ImportError:
            logger.debug("psutil not available, skipping resource-based optimization")
        except Exception as e:
            logger.warning(f"Failed to optimize concurrent executions: {e}")


class ConfigurationManager:
    """
    High-level manager for scheduling configuration operations.
    
    Provides a unified interface for loading, saving, migrating,
    and managing scheduling configurations.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Optional configuration directory
        """
        if config_dir is None:
            from ..config import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "scheduling"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / "scheduling_config.json"
        self.logger = logging.getLogger(f"{__name__}.ConfigurationManager")
    
    def load_configuration(self, auto_migrate: bool = True) -> SchedulingConfiguration:
        """
        Load scheduling configuration with optional auto-migration.
        
        Args:
            auto_migrate: If True, automatically migrate old configurations
            
        Returns:
            SchedulingConfiguration instance
            
        Raises:
            SchedulingError: If loading fails
        """
        try:
            if not self.config_path.exists():
                self.logger.info("No configuration file found, creating default")
                config = SchedulingConfiguration()
                config.save_to_file(self.config_path)
                return config
            
            # Check if migration is needed
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            if auto_migrate and ConfigurationMigrator.needs_migration(config_data):
                self.logger.info("Configuration migration needed")
                return ConfigurationMigrator.migrate_configuration(self.config_path)
            
            # Load normally
            return SchedulingConfiguration.load_from_file(self.config_path)
            
        except Exception as e:
            raise SchedulingError(
                f"Failed to load configuration: {e}",
                details={"path": str(self.config_path), "error": str(e)}
            ) from e
    
    def save_configuration(self, config: SchedulingConfiguration) -> None:
        """
        Save scheduling configuration.
        
        Args:
            config: Configuration to save
            
        Raises:
            SchedulingError: If saving fails
        """
        try:
            config.save_to_file(self.config_path)
            self.logger.info("Configuration saved successfully")
            
        except Exception as e:
            raise SchedulingError(
                f"Failed to save configuration: {e}",
                details={"path": str(self.config_path), "error": str(e)}
            ) from e
    
    def upgrade_configuration(self) -> SchedulingConfiguration:
        """
        Upgrade configuration to latest version.
        
        Returns:
            Upgraded SchedulingConfiguration
            
        Raises:
            SchedulingError: If upgrade fails
        """
        return ConfigurationMigrator.upgrade_configuration(self.config_path)
    
    def reset_to_defaults(self, create_backup: bool = True) -> SchedulingConfiguration:
        """
        Reset configuration to defaults.
        
        Args:
            create_backup: If True, create backup before reset
            
        Returns:
            New default SchedulingConfiguration
            
        Raises:
            SchedulingError: If reset fails
        """
        try:
            if create_backup and self.config_path.exists():
                backup_path = ConfigurationMigrator._create_backup(self.config_path)
                self.logger.info(f"Created backup at {backup_path}")
            
            # Create and save default configuration
            config = SchedulingConfiguration()
            config.save_to_file(self.config_path)
            
            self.logger.info("Configuration reset to defaults")
            return config
            
        except Exception as e:
            raise SchedulingError(
                f"Failed to reset configuration: {e}",
                details={"path": str(self.config_path), "error": str(e)}
            ) from e
    
    def export_configuration(self, output_path: Path) -> bool:
        """
        Export configuration to a file.
        
        Args:
            output_path: Path to export configuration
            
        Returns:
            True if export successful
        """
        try:
            if not self.config_path.exists():
                self.logger.error("No configuration to export")
                return False
            
            shutil.copy2(self.config_path, output_path)
            self.logger.info(f"Configuration exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_configuration(self, input_path: Path, validate: bool = True) -> SchedulingConfiguration:
        """
        Import configuration from a file.
        
        Args:
            input_path: Path to import configuration from
            validate: If True, validate imported configuration
            
        Returns:
            Imported SchedulingConfiguration
            
        Raises:
            SchedulingError: If import fails
        """
        try:
            if not input_path.exists():
                raise SchedulingError(f"Import file not found: {input_path}")
            
            # Load and validate imported configuration
            config = SchedulingConfiguration.load_from_file(input_path)
            
            if validate:
                validation_result = config.validate()
                if not validation_result.is_valid:
                    raise SchedulingError(
                        f"Imported configuration validation failed: {', '.join(validation_result.errors)}",
                        details={"errors": validation_result.errors}
                    )
            
            # Create backup of current configuration
            if self.config_path.exists():
                backup_path = ConfigurationMigrator._create_backup(self.config_path)
                self.logger.info(f"Created backup at {backup_path}")
            
            # Save imported configuration
            config.save_to_file(self.config_path)
            
            self.logger.info(f"Configuration imported from {input_path}")
            return config
            
        except Exception as e:
            raise SchedulingError(
                f"Failed to import configuration: {e}",
                details={"path": str(input_path), "error": str(e)}
            ) from e
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get information about current configuration.
        
        Returns:
            Dictionary with configuration information
        """
        try:
            if not self.config_path.exists():
                return {
                    'exists': False,
                    'path': str(self.config_path)
                }
            
            config = SchedulingConfiguration.load_from_file(self.config_path)
            validation_result = config.validate()
            
            return {
                'exists': True,
                'path': str(self.config_path),
                'version': config.config_version,
                'is_valid': validation_result.is_valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings,
                'platform_preferences': config.platform_preferences,
                'max_concurrent_executions': config.max_concurrent_executions,
                'execution_timeout_minutes': config.execution_timeout_minutes,
                'audit_retention_days': config.audit_retention_days
            }
            
        except Exception as e:
            return {
                'exists': True,
                'path': str(self.config_path),
                'error': str(e)
            }
