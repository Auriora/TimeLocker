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

TimeLocker Configuration Module

This module provides a unified, SOLID-compliant configuration management system
for TimeLocker, replacing the previous dual configuration system with a single,
well-structured approach.

Key Components:
- ConfigurationModule: Main facade for all configuration operations
- ConfigurationSchema: Type-safe configuration models using dataclasses
- ConfigurationDefaults: Single source of truth for default values
- ConfigurationValidator: Comprehensive validation with clear error messages
- ConfigurationPathResolver: XDG-compliant path resolution
- ConfigurationMigrator: Legacy configuration migration support

Usage:
    from TimeLocker.config import ConfigurationModule

    # Initialize configuration system
    config_module = ConfigurationModule()

    # Get complete configuration
    config = config_module.get_config()

    # Get specific sections
    general_config = config_module.get_section('general')

    # Manage repositories
    repositories = config_module.get_repositories()
    config_module.add_repository(new_repo)

    # Validate configuration
    validation_result = config_module.validate_configuration()
"""

# Main configuration interface
from .configuration_module import ConfigurationModule

# Configuration schema and models
from .configuration_schema import (
    TimeLockerConfig,
    GeneralConfig,
    BackupConfig,
    RestoreConfig,
    SecurityConfig,
    UIConfig,
    NotificationConfig,
    MonitoringConfig,
    RepositoryConfig,
    BackupTargetConfig,
    LogLevel,
    CompressionType,
    ThemeType,
    ConfigDict,
    ConfigValue
)

# Configuration defaults
from .configuration_defaults import ConfigurationDefaults

# Validation
from .configuration_validator import (
    ConfigurationValidator,
    ValidationResult
)

# Path resolution
from .configuration_path_resolver import ConfigurationPathResolver

# Migration support
from .configuration_migrator import (
    ConfigurationMigrator,
    MigrationResult
)


# Legacy imports removed - use ConfigurationModule instead


# Convenience functions for common operations
def get_default_configuration_module() -> ConfigurationModule:
    """
    Get default configuration module instance.

    Returns:
        ConfigurationModule: Default configuration module
    """
    return ConfigurationModule()


def create_configuration_module(config_dir: str = None) -> ConfigurationModule:
    """
    Create configuration module with specific directory.

    Args:
        config_dir: Optional configuration directory path

    Returns:
        ConfigurationModule: Configuration module instance
    """
    from pathlib import Path
    config_path = Path(config_dir) if config_dir else None
    return ConfigurationModule(config_path)


def validate_configuration_file(config_file_path: str) -> ValidationResult:
    """
    Validate configuration file without loading it into the system.

    Args:
        config_file_path: Path to configuration file

    Returns:
        ValidationResult: Validation result
    """
    import json
    from pathlib import Path

    validator = ConfigurationValidator()

    try:
        with open(config_file_path, 'r') as f:
            config_data = json.load(f)

        return validator.validate_config(config_data)

    except Exception as e:
        result = ValidationResult()
        result.add_error(f"Failed to load configuration file: {e}")
        return result


def get_configuration_path_info() -> dict:
    """
    Get information about configuration paths.

    Returns:
        dict: Configuration path information
    """
    return ConfigurationPathResolver.get_path_info()


def migrate_legacy_configuration(source_dir: str = None, target_dir: str = None) -> MigrationResult:
    """
    Migrate legacy configuration to new format.

    Args:
        source_dir: Optional source directory (defaults to legacy location)
        target_dir: Optional target directory (defaults to current location)

    Returns:
        MigrationResult: Migration result
    """
    from pathlib import Path

    migrator = ConfigurationMigrator()

    if source_dir is None:
        source_path = ConfigurationPathResolver.get_legacy_config_directory()
    else:
        source_path = Path(source_dir)

    if target_dir is None:
        target_path = ConfigurationPathResolver.get_config_directory()
    else:
        target_path = Path(target_dir)

    return migrator.migrate_directory(source_path, target_path)


# Export all public components
__all__ = [
        # Main interface
        'ConfigurationModule',

        # Schema and models
        'TimeLockerConfig',
        'GeneralConfig',
        'BackupConfig',
        'RestoreConfig',
        'SecurityConfig',
        'UIConfig',
        'NotificationConfig',
        'MonitoringConfig',
        'RepositoryConfig',
        'BackupTargetConfig',
        'LogLevel',
        'CompressionType',
        'ThemeType',
        'ConfigDict',
        'ConfigValue',

        # Components
        'ConfigurationDefaults',
        'ConfigurationValidator',
        'ValidationResult',
        'ConfigurationPathResolver',
        'ConfigurationMigrator',
        'MigrationResult',

        # Convenience functions
        'get_default_configuration_module',
        'create_configuration_module',
        'validate_configuration_file',
        'get_configuration_path_info',
        'migrate_legacy_configuration'
]
