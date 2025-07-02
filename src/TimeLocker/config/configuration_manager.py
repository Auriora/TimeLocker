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
import os
import shutil
import copy
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Base exception for configuration-related errors"""
    pass


class RepositoryNotFoundError(ConfigurationError):
    """Raised when a repository name cannot be resolved"""
    pass


class RepositoryAlreadyExistsError(ConfigurationError):
    """Raised when trying to add a repository with an existing name"""
    pass


class ConfigSection(Enum):
    """Configuration sections"""
    GENERAL = "general"
    REPOSITORIES = "repositories"
    BACKUP = "backup"
    RESTORE = "restore"
    SECURITY = "security"
    NOTIFICATIONS = "notifications"
    MONITORING = "monitoring"
    UI = "ui"
    BACKUP_TARGETS = "backup_targets"


@dataclass
class BackupDefaults:
    """Default backup configuration"""
    compression: str = "auto"
    exclude_caches: bool = True
    exclude_if_present: List[str] = None
    one_file_system: bool = False
    check_before_backup: bool = True
    verify_after_backup: bool = True
    retention_keep_last: int = 10
    retention_keep_daily: int = 7
    retention_keep_weekly: int = 4
    retention_keep_monthly: int = 12

    def __post_init__(self):
        if self.exclude_if_present is None:
            self.exclude_if_present = [".nobackup", "CACHEDIR.TAG"]


@dataclass
class RestoreDefaults:
    """Default restore configuration"""
    verify_after_restore: bool = True
    create_target_directory: bool = True
    preserve_permissions: bool = True
    conflict_resolution: str = "prompt"  # prompt, skip, overwrite, keep_both


@dataclass
class SecurityDefaults:
    """Default security configuration"""
    encryption_enabled: bool = True
    audit_logging: bool = True
    credential_timeout: int = 3600  # seconds
    max_failed_attempts: int = 3
    lockout_duration: int = 300  # seconds


@dataclass
class UIDefaults:
    """Default UI configuration"""
    theme: str = "auto"  # auto, light, dark
    show_advanced_options: bool = False
    auto_refresh_interval: int = 30  # seconds
    max_log_entries: int = 1000
    confirm_destructive_actions: bool = True


class ConfigurationPathResolver:
    """
    Utility class for resolving configuration directory paths
    Handles XDG Base Directory Specification and system vs user contexts
    """

    @staticmethod
    def is_system_context() -> bool:
        """
        Determine if running in system context (as root for system backups)

        Returns:
            bool: True if running as root or in system context
        """
        return os.geteuid() == 0 if hasattr(os, 'geteuid') else False

    @staticmethod
    def get_xdg_config_home() -> Path:
        """
        Get XDG config home directory

        Returns:
            Path: XDG config home directory
        """
        xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config_home:
            return Path(xdg_config_home)
        return Path.home() / ".config"

    @staticmethod
    def get_config_directory() -> Path:
        """
        Get appropriate configuration directory based on context

        Returns:
            Path: Configuration directory to use
        """
        if ConfigurationPathResolver.is_system_context():
            # System-wide configuration for root/system backups
            system_config = Path("/etc/timelocker")
            if system_config.exists() or system_config.parent.exists():
                return system_config
            # Fallback to XDG system directory
            return Path("/etc/xdg/timelocker")
        else:
            # User configuration following XDG specification
            return ConfigurationPathResolver.get_xdg_config_home() / "timelocker"

    @staticmethod
    def get_legacy_config_directory() -> Path:
        """
        Get legacy configuration directory for migration

        Returns:
            Path: Legacy configuration directory
        """
        return Path.home() / ".timelocker"

    @staticmethod
    def should_migrate_from_legacy() -> bool:
        """
        Check if migration from legacy config is needed

        Returns:
            bool: True if legacy config exists and new config doesn't
        """
        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
        new_dir = ConfigurationPathResolver.get_config_directory()

        legacy_config = legacy_dir / "config.json"
        new_config = new_dir / "config.json"

        return legacy_config.exists() and not new_config.exists()


class ConfigurationMigrationManager:
    """
    Handles migration of configuration files from legacy locations
    """

    @staticmethod
    def calculate_file_checksum(file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file

        Args:
            file_path: Path to file

        Returns:
            str: Hexadecimal checksum
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    @staticmethod
    def create_migration_backup(source_path: Path, backup_dir: Path) -> Optional[Path]:
        """
        Create backup of source file before migration

        Args:
            source_path: Source file to backup
            backup_dir: Directory to store backup

        Returns:
            Optional[Path]: Path to backup file if successful
        """
        if not source_path.exists():
            return None

        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"migration_backup_{timestamp}_{source_path.name}"
            shutil.copy2(source_path, backup_path)
            logger.info(f"Created migration backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create migration backup: {e}")
            return None

    @staticmethod
    def migrate_configuration_directory(legacy_dir: Path, new_dir: Path) -> bool:
        """
        Migrate entire configuration directory from legacy to new location

        Args:
            legacy_dir: Legacy configuration directory
            new_dir: New configuration directory

        Returns:
            bool: True if migration successful
        """
        if not legacy_dir.exists():
            logger.info("No legacy configuration directory found")
            return True

        if new_dir.exists() and (new_dir / "config.json").exists():
            logger.info("New configuration already exists, skipping migration")
            return True

        try:
            logger.info(f"Migrating configuration from {legacy_dir} to {new_dir}")

            # Create new directory
            new_dir.mkdir(parents=True, exist_ok=True)

            # Create backup directory in new location
            backup_dir = new_dir / "migration_backups"
            backup_dir.mkdir(exist_ok=True)

            # Files to migrate
            files_to_migrate = ["config.json"]
            migrated_files = []

            for filename in files_to_migrate:
                legacy_file = legacy_dir / filename
                new_file = new_dir / filename

                if legacy_file.exists():
                    # Create backup
                    backup_path = ConfigurationMigrationManager.create_migration_backup(
                            legacy_file, backup_dir
                    )

                    # Calculate checksum before migration
                    original_checksum = ConfigurationMigrationManager.calculate_file_checksum(legacy_file)

                    # Copy file
                    shutil.copy2(legacy_file, new_file)

                    # Verify checksum after migration
                    new_checksum = ConfigurationMigrationManager.calculate_file_checksum(new_file)

                    if original_checksum and original_checksum == new_checksum:
                        migrated_files.append(filename)
                        logger.info(f"Successfully migrated {filename}")
                    else:
                        logger.error(f"Checksum mismatch for {filename}, migration may have failed")
                        if new_file.exists():
                            new_file.unlink()
                        return False

            if migrated_files:
                logger.info(f"Migration completed successfully. Migrated files: {migrated_files}")

                # Create migration marker file
                migration_marker = new_dir / ".migrated_from_legacy"
                with open(migration_marker, 'w') as f:
                    f.write(f"Migrated from {legacy_dir} on {datetime.now().isoformat()}\n")
                    f.write(f"Migrated files: {', '.join(migrated_files)}\n")

                return True
            else:
                logger.info("No files to migrate")
                return True

        except Exception as e:
            logger.error(f"Failed to migrate configuration directory: {e}")
            return False


class ConfigurationManager:
    """
    Centralized configuration management for TimeLocker
    Handles loading, saving, validation, and migration of configuration settings
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Directory for configuration files (if None, uses path resolver)
        """
        if config_dir is None:
            # Check if migration from legacy location is needed
            if ConfigurationPathResolver.should_migrate_from_legacy():
                legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
                new_dir = ConfigurationPathResolver.get_config_directory()

                logger.info("Legacy configuration detected, performing migration...")
                migration_success = ConfigurationMigrationManager.migrate_configuration_directory(
                        legacy_dir, new_dir
                )

                if migration_success:
                    logger.info("Configuration migration completed successfully")
                else:
                    logger.warning("Configuration migration failed, using legacy location")
                    config_dir = legacy_dir

            if config_dir is None:
                config_dir = ConfigurationPathResolver.get_config_directory()

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"
        self.backup_dir = self.config_dir / "config_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Configuration data
        self._config: Dict[str, Any] = {}
        self._defaults = self._get_default_config()

        # Load existing configuration
        self.load_config()

        # Check for and migrate legacy configuration files (within same directory)
        self._migrate_legacy_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
                ConfigSection.GENERAL.value:        {
                        "app_name":                  "TimeLocker",
                        "version":                   "1.0.0",
                        "log_level":                 "INFO",
                        "data_dir":                  str(self.config_dir / "data"),
                        "temp_dir":                  str(self.config_dir / "temp"),
                        "max_concurrent_operations": 2,
                        "default_repository":        None
                },
                ConfigSection.BACKUP.value:         asdict(BackupDefaults()),
                ConfigSection.RESTORE.value:        asdict(RestoreDefaults()),
                ConfigSection.SECURITY.value:       asdict(SecurityDefaults()),
                ConfigSection.UI.value:             asdict(UIDefaults()),
                ConfigSection.REPOSITORIES.value:   {},
                ConfigSection.BACKUP_TARGETS.value: {},
                ConfigSection.NOTIFICATIONS.value:  {
                        "enabled":           True,
                        "desktop_enabled":   True,
                        "email_enabled":     False,
                        "notify_on_success": True,
                        "notify_on_error":   True
                },
                ConfigSection.MONITORING.value:     {
                        "status_retention_days":  30,
                        "metrics_enabled":        True,
                        "performance_monitoring": True
                }
        }

    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)

                # Merge with defaults to ensure all keys exist
                self._config = self._merge_config(self._defaults, loaded_config)

                # Validate configuration
                self._validate_config()

                logger.info("Configuration loaded successfully")
            else:
                # Use defaults for new installation
                self._config = copy.deepcopy(self._defaults)
                self.save_config()
                logger.info("Created default configuration")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fall back to defaults
            self._config = copy.deepcopy(self._defaults)
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def save_config(self):
        """Save current configuration to file"""
        try:
            # Create backup of existing config
            if self.config_file.exists():
                self._backup_config()

            # Save configuration
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)

            logger.info("Configuration saved successfully")

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get(self, section: Union[ConfigSection, str], key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            section: Configuration section
            key: Configuration key (optional, returns entire section if None)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        section_name = section.value if isinstance(section, ConfigSection) else section

        if section_name not in self._config:
            return default

        section_data = self._config[section_name]

        if key is None:
            return section_data

        return section_data.get(key, default)

    def set(self, section: Union[ConfigSection, str], key: str, value: Any):
        """
        Set configuration value
        
        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        section_name = section.value if isinstance(section, ConfigSection) else section

        if section_name not in self._config:
            self._config[section_name] = {}

        self._config[section_name][key] = value

    def update_section(self, section: Union[ConfigSection, str], data: Dict[str, Any]):
        """
        Update entire configuration section
        
        Args:
            section: Configuration section
            data: New section data
        """
        section_name = section.value if isinstance(section, ConfigSection) else section

        if section_name not in self._config:
            self._config[section_name] = {}

        self._config[section_name].update(data)

    def delete(self, section: Union[ConfigSection, str], key: str):
        """
        Delete configuration key
        
        Args:
            section: Configuration section
            key: Configuration key to delete
        """
        section_name = section.value if isinstance(section, ConfigSection) else section

        if section_name in self._config and key in self._config[section_name]:
            del self._config[section_name][key]

    def reset_section(self, section: Union[ConfigSection, str]):
        """
        Reset section to defaults

        Args:
            section: Configuration section to reset
        """
        section_name = section.value if isinstance(section, ConfigSection) else section

        if section_name in self._defaults:
            self._config[section_name] = copy.deepcopy(self._defaults[section_name])

    def reset_all(self):
        """Reset all configuration to defaults"""
        self._config = copy.deepcopy(self._defaults)

    def export_config(self, export_path: Path) -> bool:
        """
        Export configuration to file
        
        Args:
            export_path: Path to export configuration
            
        Returns:
            bool: True if successful
        """
        try:
            with open(export_path, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False

    def import_config(self, import_path: Path) -> bool:
        """
        Import configuration from file
        
        Args:
            import_path: Path to import configuration from
            
        Returns:
            bool: True if successful
        """
        try:
            with open(import_path, 'r') as f:
                imported_config = json.load(f)

            # Validate imported configuration
            merged_config = self._merge_config(self._defaults, imported_config)

            # Backup current config before importing
            self._backup_config()

            # Apply imported configuration
            self._config = merged_config
            self.save_config()

            logger.info(f"Configuration imported from {import_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False

    def load_configuration(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a specific file path

        Args:
            config_path: Path to configuration file

        Returns:
            Dict: Loaded configuration data
        """
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            return {}

    def save_configuration(self, config_data: Dict[str, Any], config_path: str) -> bool:
        """
        Save configuration data to a specific file path

        Args:
            config_data: Configuration data to save
            config_path: Path to save configuration file

        Returns:
            bool: True if successful
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {e}")
            return False

    def get_configuration(self) -> Dict[str, Any]:
        """
        Get the complete configuration data

        Returns:
            Dict: Complete configuration data
        """
        return self._config.copy()

    def get_config_info(self) -> Dict[str, Any]:
        """
        Get information about configuration paths and status

        Returns:
            Dict: Configuration information including paths and migration status
        """
        legacy_dir = ConfigurationPathResolver.get_legacy_config_directory()
        current_dir = self.config_dir

        return {
                "current_config_dir":      str(current_dir),
                "current_config_file":     str(self.config_file),
                "is_system_context":       ConfigurationPathResolver.is_system_context(),
                "xdg_config_home":         str(ConfigurationPathResolver.get_xdg_config_home()),
                "legacy_config_dir":       str(legacy_dir),
                "legacy_config_exists":    (legacy_dir / "config.json").exists(),
                "migration_marker_exists": (current_dir / ".migrated_from_legacy").exists(),
                "config_file_exists":      self.config_file.exists(),
                "backup_dir":              str(self.backup_dir),
                "backup_count":            len(list(self.backup_dir.glob("config_*.json"))) if self.backup_dir.exists() else 0
        }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration"""
        summary = {
                "config_file":    str(self.config_file),
                "last_modified":  datetime.fromtimestamp(
                        self.config_file.stat().st_mtime
                ).isoformat() if self.config_file.exists() else None,
                "sections":       list(self._config.keys()),
                "total_settings": sum(
                        len(section) if isinstance(section, dict) else 1
                        for section in self._config.values()
                )
        }
        return summary

    def _merge_config(self, defaults: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults"""
        merged = copy.deepcopy(defaults)

        for section, values in user_config.items():
            if section in merged:
                if isinstance(merged[section], dict) and isinstance(values, dict):
                    merged[section].update(values)
                else:
                    merged[section] = values
            else:
                merged[section] = values

        return merged

    def _validate_config(self):
        """Validate configuration values"""
        # Validate general settings
        general = self._config.get(ConfigSection.GENERAL.value, {})
        if general.get("max_concurrent_operations", 1) < 1:
            self.set(ConfigSection.GENERAL, "max_concurrent_operations", 1)

        # Validate backup settings
        backup = self._config.get(ConfigSection.BACKUP.value, {})
        if backup.get("retention_keep_last", 1) < 1:
            self.set(ConfigSection.BACKUP, "retention_keep_last", 1)

        # Validate security settings
        security = self._config.get(ConfigSection.SECURITY.value, {})
        if security.get("credential_timeout", 3600) < 60:
            self.set(ConfigSection.SECURITY, "credential_timeout", 60)

    def _backup_config(self):
        """Create backup of current configuration"""
        if not self.config_file.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_{timestamp}.json"

        try:
            shutil.copy2(self.config_file, backup_file)

            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob("config_*.json"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()

        except Exception as e:
            logger.warning(f"Failed to backup configuration: {e}")

    def add_repository(self, name: str, uri: str, description: str = "",
                       repo_type: str = "auto") -> None:
        """Add a new repository to configuration"""
        repositories = self.get(ConfigSection.REPOSITORIES, default={})

        if name in repositories:
            raise RepositoryAlreadyExistsError(f"Repository '{name}' already exists")

        # Auto-detect repository type from URI
        if repo_type == "auto":
            if uri.startswith("s3:") or uri.startswith("s3://"):
                repo_type = "s3"
            elif uri.startswith("b2:") or uri.startswith("b2://"):
                repo_type = "b2"
            elif uri.startswith("sftp:") or uri.startswith("sftp://"):
                repo_type = "sftp"
            elif uri.startswith("/") or uri.startswith("file://"):
                repo_type = "local"
            else:
                repo_type = "unknown"

        repositories[name] = {
                "uri":         uri,
                "description": description,
                "type":        repo_type,
                "created":     datetime.now().isoformat()
        }

        self.update_section(ConfigSection.REPOSITORIES, repositories)
        self.save_config()
        logger.info(f"Added repository '{name}' with URI: {uri}")

    def remove_repository(self, name: str) -> None:
        """Remove a repository from configuration"""
        repositories = self.get(ConfigSection.REPOSITORIES, default={})

        if name not in repositories:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")

        # Check if this is the default repository
        if self.get(ConfigSection.GENERAL, "default_repository") == name:
            self.set(ConfigSection.GENERAL, "default_repository", None)

        del repositories[name]
        self.update_section(ConfigSection.REPOSITORIES, repositories)
        self.save_config()
        logger.info(f"Removed repository '{name}'")

    def get_repository(self, name: str) -> Dict[str, Any]:
        """Get repository configuration by name"""
        repositories = self.get(ConfigSection.REPOSITORIES, default={})

        if name not in repositories:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")

        return repositories[name]

    def list_repositories(self) -> Dict[str, Dict[str, Any]]:
        """List all configured repositories"""
        return self.get(ConfigSection.REPOSITORIES, default={})

    def _migrate_legacy_config(self):
        """Migrate legacy timelocker.json configuration to config.json"""
        legacy_file = self.config_dir / "timelocker.json"

        if not legacy_file.exists():
            return

        try:
            logger.info("Found legacy configuration file, migrating...")

            # Load legacy configuration
            with open(legacy_file, 'r') as f:
                legacy_config = json.load(f)

            # Backup legacy file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_legacy = self.config_dir / f"timelocker_backup_{timestamp}.json"
            shutil.copy2(legacy_file, backup_legacy)

            # Merge legacy config with current config
            if legacy_config.get("repositories"):
                current_repos = self.get(ConfigSection.REPOSITORIES, default={})
                current_repos.update(legacy_config["repositories"])
                self.update_section(ConfigSection.REPOSITORIES, current_repos)

            if legacy_config.get("backup_targets"):
                current_targets = self.get(ConfigSection.BACKUP_TARGETS, default={})
                current_targets.update(legacy_config["backup_targets"])
                self.update_section(ConfigSection.BACKUP_TARGETS, current_targets)

            if legacy_config.get("settings"):
                settings = legacy_config["settings"]
                if settings.get("default_repository"):
                    self.set(ConfigSection.GENERAL, "default_repository", settings["default_repository"])

            # Save migrated configuration
            self.save_config()

            # Remove legacy file after successful migration
            legacy_file.unlink()

            logger.info(f"Successfully migrated configuration from {legacy_file} to {self.config_file}")

        except Exception as e:
            logger.error(f"Failed to migrate legacy configuration: {e}")
            # Don't raise exception - continue with current config

    def add_backup_target(self, name: str, paths: List[str], description: str = "",
                          include_patterns: List[str] = None, exclude_patterns: List[str] = None) -> None:
        """Add a new backup target to configuration"""
        backup_targets = self.get(ConfigSection.BACKUP_TARGETS, default={})

        if name in backup_targets:
            raise ValueError(f"Backup target '{name}' already exists")

        # Set default patterns if not provided
        if include_patterns is None:
            include_patterns = ["*"]
        if exclude_patterns is None:
            exclude_patterns = ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]

        backup_targets[name] = {
                "name":        description or name,
                "description": description or f"Backup target for {name}",
                "paths":       paths,
                "patterns":    {
                        "include": include_patterns,
                        "exclude": exclude_patterns
                },
                "created":     datetime.now().isoformat()
        }

        self.update_section(ConfigSection.BACKUP_TARGETS, backup_targets)
        self.save_config()
        logger.info(f"Added backup target '{name}' with {len(paths)} path(s)")

    def remove_backup_target(self, name: str) -> None:
        """Remove a backup target from configuration"""
        backup_targets = self.get(ConfigSection.BACKUP_TARGETS, default={})

        if name not in backup_targets:
            raise ValueError(f"Backup target '{name}' not found")

        del backup_targets[name]
        self.update_section(ConfigSection.BACKUP_TARGETS, backup_targets)
        self.save_config()
        logger.info(f"Removed backup target '{name}'")

    def get_backup_target(self, name: str) -> Dict[str, Any]:
        """Get backup target configuration by name"""
        backup_targets = self.get(ConfigSection.BACKUP_TARGETS, default={})

        if name not in backup_targets:
            raise ValueError(f"Backup target '{name}' not found")

        return backup_targets[name]

    def list_backup_targets(self) -> Dict[str, Dict[str, Any]]:
        """List all configured backup targets"""
        return self.get(ConfigSection.BACKUP_TARGETS, default={})

    def set_default_repository(self, name: str) -> None:
        """Set the default repository"""
        repositories = self.get(ConfigSection.REPOSITORIES, default={})

        if name not in repositories:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")

        self.set(ConfigSection.GENERAL, "default_repository", name)
        self.save_config()
        logger.info(f"Set default repository to '{name}'")

    def get_default_repository(self) -> Optional[str]:
        """Get the default repository name"""
        return self.get(ConfigSection.GENERAL, "default_repository")

    def resolve_repository(self, name_or_uri: str) -> str:
        """Resolve repository name to URI, or return URI if already a URI"""
        if not name_or_uri:
            # Try to use default repository
            default_repo = self.get_default_repository()
            if default_repo:
                return self.get_repository(default_repo)["uri"]
            raise RepositoryNotFoundError("No repository specified and no default repository set")

        # Check if it's already a URI (contains :// or starts with known schemes)
        if ("://" in name_or_uri or
                name_or_uri.startswith("s3:") or
                name_or_uri.startswith("b2:") or
                name_or_uri.startswith("/") or
                name_or_uri.startswith("sftp:")):
            return name_or_uri

        # Try to resolve as repository name
        repositories = self.get(ConfigSection.REPOSITORIES, default={})
        if name_or_uri in repositories:
            return repositories[name_or_uri]["uri"]

        # If not found as name, assume it's a URI
        return name_or_uri
