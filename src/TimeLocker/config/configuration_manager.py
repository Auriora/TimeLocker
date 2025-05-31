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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Base exception for configuration-related errors"""
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


class ConfigurationManager:
    """
    Centralized configuration management for TimeLocker
    Handles loading, saving, validation, and migration of configuration settings
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory for configuration files
        """
        if config_dir is None:
            config_dir = Path.home() / ".timelocker"

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

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
                ConfigSection.GENERAL.value:       {
                        "app_name":                  "TimeLocker",
                        "version":                   "1.0.0",
                        "log_level":                 "INFO",
                        "data_dir":                  str(self.config_dir / "data"),
                        "temp_dir":                  str(self.config_dir / "temp"),
                        "max_concurrent_operations": 2
                },
                ConfigSection.BACKUP.value:        asdict(BackupDefaults()),
                ConfigSection.RESTORE.value:       asdict(RestoreDefaults()),
                ConfigSection.SECURITY.value:      asdict(SecurityDefaults()),
                ConfigSection.UI.value:            asdict(UIDefaults()),
                ConfigSection.REPOSITORIES.value:  {},
                ConfigSection.NOTIFICATIONS.value: {
                        "enabled":           True,
                        "desktop_enabled":   True,
                        "email_enabled":     False,
                        "notify_on_success": True,
                        "notify_on_error":   True
                },
                ConfigSection.MONITORING.value:    {
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
                self._config = self._defaults.copy()
                self.save_config()
                logger.info("Created default configuration")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Fall back to defaults
            self._config = self._defaults.copy()
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
            self._config[section_name] = self._defaults[section_name].copy()

    def reset_all(self):
        """Reset all configuration to defaults"""
        self._config = self._defaults.copy()

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
        merged = defaults.copy()

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
