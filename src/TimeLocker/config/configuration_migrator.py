"""
Configuration migration for TimeLocker.

This module provides configuration migration capabilities following the
Single Responsibility Principle by focusing solely on migration logic.
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .configuration_schema import TimeLockerConfig
from .configuration_defaults import ConfigurationDefaults
from .configuration_validator import ConfigurationValidator
from ..interfaces.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class MigrationResult:
    """Result of configuration migration"""

    def __init__(self):
        self.success: bool = True
        self.messages: List[str] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.migrated_files: List[str] = []

    def add_message(self, message: str) -> None:
        """Add informational message"""
        self.messages.append(message)
        logger.info(message)

    def add_warning(self, warning: str) -> None:
        """Add warning message"""
        self.warnings.append(warning)
        logger.warning(warning)

    def add_error(self, error: str) -> None:
        """Add error message"""
        self.errors.append(error)
        self.success = False
        logger.error(error)

    def add_migrated_file(self, file_path: str) -> None:
        """Add migrated file to list"""
        self.migrated_files.append(file_path)


class ConfigurationMigrator:
    """
    Configuration migrator following Single Responsibility Principle.
    
    This class focuses solely on migrating configuration files and directories
    from legacy formats and locations to the new structure.
    """

    def __init__(self, validator: Optional[ConfigurationValidator] = None):
        """
        Initialize configuration migrator.
        
        Args:
            validator: Optional configuration validator
        """
        self._validator = validator or ConfigurationValidator()

    def migrate_directory(self, source_dir: Path, target_dir: Path) -> MigrationResult:
        """
        Migrate entire configuration directory.
        
        Args:
            source_dir: Source configuration directory
            target_dir: Target configuration directory
            
        Returns:
            MigrationResult: Migration result
        """
        result = MigrationResult()

        if not source_dir.exists():
            result.add_error(f"Source directory does not exist: {source_dir}")
            return result

        if target_dir.exists() and any(target_dir.iterdir()):
            result.add_warning(f"Target directory is not empty: {target_dir}")

        try:
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Migrate configuration files
            self._migrate_config_files(source_dir, target_dir, result)

            # Migrate data directories
            self._migrate_data_directories(source_dir, target_dir, result)

            # Create migration marker
            self._create_migration_marker(target_dir, source_dir, result)

            if result.success:
                result.add_message(f"Successfully migrated configuration from {source_dir} to {target_dir}")

        except Exception as e:
            result.add_error(f"Migration failed: {e}")

        return result

    def migrate_config_file(self, source_file: Path, target_file: Path) -> MigrationResult:
        """
        Migrate individual configuration file.
        
        Args:
            source_file: Source configuration file
            target_file: Target configuration file
            
        Returns:
            MigrationResult: Migration result
        """
        result = MigrationResult()

        if not source_file.exists():
            result.add_error(f"Source file does not exist: {source_file}")
            return result

        try:
            # Load and validate source configuration
            with open(source_file, 'r') as f:
                source_config = json.load(f)

            # Migrate configuration format if needed
            migrated_config = self._migrate_config_format(source_config, result)

            # Validate migrated configuration
            validation_result = self._validator.validate_config(migrated_config)
            if not validation_result:
                for error in validation_result.errors:
                    result.add_error(f"Validation error: {error}")
                for warning in validation_result.warnings:
                    result.add_warning(f"Validation warning: {warning}")

            if result.success:
                # Ensure target directory exists
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Create backup of target if it exists
                if target_file.exists():
                    self._backup_existing_file(target_file, result)

                # Write migrated configuration
                with open(target_file, 'w') as f:
                    json.dump(migrated_config, f, indent=2)

                result.add_migrated_file(str(target_file))
                result.add_message(f"Successfully migrated configuration file: {source_file} -> {target_file}")

        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in source file: {e}")
        except Exception as e:
            result.add_error(f"Failed to migrate configuration file: {e}")

        return result

    def _migrate_config_files(self, source_dir: Path, target_dir: Path, result: MigrationResult) -> None:
        """Migrate configuration files"""
        config_files = [
                "config.json",
                "repositories.json",
                "backup_targets.json"
        ]

        for config_file in config_files:
            source_file = source_dir / config_file
            target_file = target_dir / config_file

            if source_file.exists():
                file_result = self.migrate_config_file(source_file, target_file)

                # Merge results
                result.messages.extend(file_result.messages)
                result.warnings.extend(file_result.warnings)
                result.errors.extend(file_result.errors)
                result.migrated_files.extend(file_result.migrated_files)

                if not file_result.success:
                    result.success = False

    def _migrate_data_directories(self, source_dir: Path, target_dir: Path, result: MigrationResult) -> None:
        """Migrate data directories"""
        data_dirs = [
                "data",
                "temp",
                "logs",
                "cache"
        ]

        for data_dir in data_dirs:
            source_data_dir = source_dir / data_dir
            target_data_dir = target_dir / data_dir

            if source_data_dir.exists() and source_data_dir.is_dir():
                try:
                    if target_data_dir.exists():
                        result.add_warning(f"Target data directory already exists: {target_data_dir}")
                    else:
                        shutil.copytree(source_data_dir, target_data_dir)
                        result.add_message(f"Migrated data directory: {source_data_dir} -> {target_data_dir}")
                        result.add_migrated_file(str(target_data_dir))

                except Exception as e:
                    result.add_error(f"Failed to migrate data directory {data_dir}: {e}")

    def _migrate_config_format(self, config: Dict[str, Any], result: MigrationResult) -> Dict[str, Any]:
        """
        Migrate configuration format from legacy to current.
        
        Args:
            config: Legacy configuration
            result: Migration result to add messages to
            
        Returns:
            Dict[str, Any]: Migrated configuration
        """
        migrated = config.copy()

        # Get default configuration for structure reference
        defaults = ConfigurationDefaults.get_default_config().to_dict()

        # Migrate legacy field names
        field_migrations = {
                "app_settings":          "general",
                "backup_settings":       "backup",
                "restore_settings":      "restore",
                "security_settings":     "security",
                "ui_settings":           "ui",
                "notification_settings": "notifications",
                "monitoring_settings":   "monitoring"
        }

        for old_key, new_key in field_migrations.items():
            if old_key in migrated:
                migrated[new_key] = migrated.pop(old_key)
                result.add_message(f"Migrated section: {old_key} -> {new_key}")

        # Ensure all required sections exist
        for section in defaults.keys():
            if section not in migrated:
                migrated[section] = defaults[section]
                result.add_message(f"Added missing section: {section}")

        # Migrate specific field changes
        self._migrate_general_section(migrated.get("general", {}), result)
        self._migrate_backup_section(migrated.get("backup", {}), result)
        self._migrate_security_section(migrated.get("security", {}), result)

        return migrated

    def _migrate_general_section(self, general: Dict[str, Any], result: MigrationResult) -> None:
        """Migrate general section specific changes"""
        # Migrate log level format
        if "log_level" in general:
            log_level = general["log_level"]
            if isinstance(log_level, str):
                general["log_level"] = log_level.upper()

        # Migrate directory paths
        if "config_dir" in general:
            # Legacy config_dir is now handled by path resolver
            general.pop("config_dir")
            result.add_message("Removed legacy config_dir setting (now handled automatically)")

    def _migrate_backup_section(self, backup: Dict[str, Any], result: MigrationResult) -> None:
        """Migrate backup section specific changes"""
        # Migrate compression format
        if "compression" in backup:
            compression = backup["compression"]
            if isinstance(compression, str):
                backup["compression"] = compression.lower()

        # Migrate exclude patterns
        if "exclude_patterns" in backup and "exclude_if_present" not in backup:
            backup["exclude_if_present"] = backup.get("exclude_patterns", [])
            result.add_message("Migrated exclude_patterns to exclude_if_present")

    def _migrate_security_section(self, security: Dict[str, Any], result: MigrationResult) -> None:
        """Migrate security section specific changes"""
        # Migrate timeout format (convert minutes to seconds if needed)
        if "credential_timeout" in security:
            timeout = security["credential_timeout"]
            if isinstance(timeout, int) and timeout < 3600:  # Assume minutes if < 1 hour
                security["credential_timeout"] = timeout * 60
                result.add_message("Converted credential_timeout from minutes to seconds")

    def _backup_existing_file(self, file_path: Path, result: MigrationResult) -> None:
        """Create backup of existing file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".backup_{timestamp}{file_path.suffix}")

        try:
            shutil.copy2(file_path, backup_path)
            result.add_message(f"Created backup: {backup_path}")
        except Exception as e:
            result.add_warning(f"Could not create backup of {file_path}: {e}")

    def _create_migration_marker(self, target_dir: Path, source_dir: Path, result: MigrationResult) -> None:
        """Create migration marker file"""
        marker_file = target_dir / ".migrated_from_legacy"

        try:
            with open(marker_file, 'w') as f:
                migration_info = {
                        "migrated_at":      datetime.now().isoformat(),
                        "source_directory": str(source_dir),
                        "target_directory": str(target_dir),
                        "migrated_files":   result.migrated_files
                }
                json.dump(migration_info, f, indent=2)

            result.add_message(f"Created migration marker: {marker_file}")

        except Exception as e:
            result.add_warning(f"Could not create migration marker: {e}")

    def rollback_migration(self, target_dir: Path) -> MigrationResult:
        """
        Rollback a migration using the migration marker.
        
        Args:
            target_dir: Target directory to rollback
            
        Returns:
            MigrationResult: Rollback result
        """
        result = MigrationResult()
        marker_file = target_dir / ".migrated_from_legacy"

        if not marker_file.exists():
            result.add_error("No migration marker found - cannot rollback")
            return result

        try:
            with open(marker_file, 'r') as f:
                migration_info = json.load(f)

            # Remove migrated files
            for file_path in migration_info.get("migrated_files", []):
                file_to_remove = Path(file_path)
                if file_to_remove.exists():
                    if file_to_remove.is_dir():
                        shutil.rmtree(file_to_remove)
                    else:
                        file_to_remove.unlink()
                    result.add_message(f"Removed migrated file: {file_path}")

            # Remove migration marker
            marker_file.unlink()
            result.add_message("Migration rollback completed successfully")

        except Exception as e:
            result.add_error(f"Rollback failed: {e}")

        return result
