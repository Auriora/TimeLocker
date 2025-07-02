"""
Configuration defaults for TimeLocker.

This module provides the single source of truth for default configuration values,
following the DRY principle by centralizing all default configurations.
"""

from pathlib import Path
from typing import Dict, Any
import os

from .configuration_schema import (
    TimeLockerConfig,
    GeneralConfig,
    BackupConfig,
    RestoreConfig,
    SecurityConfig,
    UIConfig,
    NotificationConfig,
    MonitoringConfig,
    LogLevel,
    CompressionType,
    ThemeType
)


class ConfigurationDefaults:
    """
    Centralized configuration defaults following Single Responsibility Principle.
    
    This class provides the single source of truth for all default configuration
    values, eliminating duplication across the codebase.
    """

    @staticmethod
    def get_default_config() -> TimeLockerConfig:
        """
        Get the complete default configuration.
        
        Returns:
            TimeLockerConfig: Complete default configuration
        """
        return TimeLockerConfig(
                general=ConfigurationDefaults.get_general_defaults(),
                backup=ConfigurationDefaults.get_backup_defaults(),
                restore=ConfigurationDefaults.get_restore_defaults(),
                security=ConfigurationDefaults.get_security_defaults(),
                ui=ConfigurationDefaults.get_ui_defaults(),
                notifications=ConfigurationDefaults.get_notification_defaults(),
                monitoring=ConfigurationDefaults.get_monitoring_defaults(),
                repositories={},
                backup_targets={}
        )

    @staticmethod
    def get_general_defaults() -> GeneralConfig:
        """Get default general configuration"""
        # Determine default directories based on context
        config_dir = ConfigurationDefaults._get_default_config_directory()

        return GeneralConfig(
                app_name="TimeLocker",
                version="1.0.0",
                log_level=LogLevel.INFO,
                data_dir=str(config_dir / "data"),
                temp_dir=str(config_dir / "temp"),
                max_concurrent_operations=2,
                default_repository=None
        )

    @staticmethod
    def get_backup_defaults() -> BackupConfig:
        """Get default backup configuration"""
        return BackupConfig(
                compression=CompressionType.AUTO,
                exclude_caches=True,
                exclude_if_present=[".nobackup", "CACHEDIR.TAG", ".timelocker-ignore"],
                one_file_system=False,
                verify_after_backup=True,
                check_before_backup=False,
                dry_run=False,
                verbose=False,
                progress=True,
                stats=True,
                cleanup_cache=True,
                limit_upload=None,
                limit_download=None,
                retention_keep_last=10,
                retention_keep_daily=7,
                retention_keep_weekly=4,
                retention_keep_monthly=12
        )

    @staticmethod
    def get_restore_defaults() -> RestoreConfig:
        """Get default restore configuration"""
        return RestoreConfig(
                verify_after_restore=True,
                create_target_directory=True,
                overwrite_existing=False,
                preserve_permissions=True,
                preserve_ownership=True,
                preserve_timestamps=True,
                sparse_files=True,
                progress=True,
                verbose=False,
                conflict_resolution="prompt"
        )

    @staticmethod
    def get_security_defaults() -> SecurityConfig:
        """Get default security configuration"""
        return SecurityConfig(
                encryption_enabled=True,
                audit_logging=True,
                credential_timeout=3600,  # 1 hour
                max_failed_attempts=3,
                lockout_duration=300,  # 5 minutes
                password_strength_check=True,
                require_password_confirmation=True
        )

    @staticmethod
    def get_ui_defaults() -> UIConfig:
        """Get default UI configuration"""
        return UIConfig(
                theme=ThemeType.AUTO,
                show_advanced_options=False,
                auto_refresh_interval=30,
                max_log_entries=1000,
                confirm_destructive_actions=True,
                show_hidden_files=False,
                default_view="list",
                window_width=1200,
                window_height=800
        )

    @staticmethod
    def get_notification_defaults() -> NotificationConfig:
        """Get default notification configuration"""
        return NotificationConfig(
                enabled=True,
                desktop_enabled=True,
                email_enabled=False,
                notify_on_success=True,
                notify_on_error=True,
                notify_on_warning=True,
                sound_enabled=False,
                email_smtp_server=None,
                email_smtp_port=587,
                email_username=None,
                email_recipients=[]
        )

    @staticmethod
    def get_monitoring_defaults() -> MonitoringConfig:
        """Get default monitoring configuration"""
        return MonitoringConfig(
                status_retention_days=30,
                metrics_enabled=True,
                performance_monitoring=True,
                detailed_logging=False,
                log_rotation_size=10,  # MB
                log_retention_days=7,
                export_metrics=False,
                metrics_endpoint=None
        )

    @staticmethod
    def get_legacy_config_dict() -> Dict[str, Any]:
        """
        Get default configuration in legacy dictionary format.
        
        This method provides backward compatibility with the existing
        configuration system during migration.
        
        Returns:
            Dict[str, Any]: Configuration in legacy format
        """
        default_config = ConfigurationDefaults.get_default_config()
        return default_config.to_dict()

    @staticmethod
    def _get_default_config_directory() -> Path:
        """
        Get the default configuration directory based on context.
        
        Returns:
            Path: Default configuration directory
        """
        # Check if running as root/system context
        if os.geteuid() == 0:
            # System-wide configuration
            return Path("/etc/timelocker")
        else:
            # User configuration following XDG specification
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config_home:
                return Path(xdg_config_home) / "timelocker"
            else:
                return Path.home() / ".config" / "timelocker"

    @staticmethod
    def get_environment_overrides() -> Dict[str, Any]:
        """
        Get configuration overrides from environment variables.
        
        This method checks for TimeLocker-specific environment variables
        and returns configuration overrides.
        
        Returns:
            Dict[str, Any]: Configuration overrides from environment
        """
        overrides = {}

        # General configuration overrides
        if log_level := os.environ.get('TIMELOCKER_LOG_LEVEL'):
            overrides['general.log_level'] = log_level.upper()

        if data_dir := os.environ.get('TIMELOCKER_DATA_DIR'):
            overrides['general.data_dir'] = data_dir

        if temp_dir := os.environ.get('TIMELOCKER_TEMP_DIR'):
            overrides['general.temp_dir'] = temp_dir

        # Security configuration overrides
        if password := os.environ.get('TIMELOCKER_PASSWORD'):
            # This would be used for default repository password
            overrides['_env_password'] = password

        if password_file := os.environ.get('TIMELOCKER_PASSWORD_FILE'):
            overrides['_env_password_file'] = password_file

        # Backup configuration overrides
        if compression := os.environ.get('TIMELOCKER_COMPRESSION'):
            overrides['backup.compression'] = compression.lower()

        if exclude_caches := os.environ.get('TIMELOCKER_EXCLUDE_CACHES'):
            overrides['backup.exclude_caches'] = exclude_caches.lower() in ('true', '1', 'yes')

        # Monitoring overrides
        if metrics_enabled := os.environ.get('TIMELOCKER_METRICS_ENABLED'):
            overrides['monitoring.metrics_enabled'] = metrics_enabled.lower() in ('true', '1', 'yes')

        return overrides

    @staticmethod
    def apply_environment_overrides(config: TimeLockerConfig) -> TimeLockerConfig:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Base configuration to override
            
        Returns:
            TimeLockerConfig: Configuration with environment overrides applied
        """
        overrides = ConfigurationDefaults.get_environment_overrides()

        if not overrides:
            return config

        # Convert config to dict for easier manipulation
        config_dict = config.to_dict()

        # Apply overrides using dot notation
        for key, value in overrides.items():
            if key.startswith('_env_'):
                # Special environment variables (not direct config overrides)
                continue

            keys = key.split('.')
            current = config_dict

            # Navigate to parent of target key
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            # Set the value
            current[keys[-1]] = value

        # Convert back to TimeLockerConfig
        return TimeLockerConfig.from_dict(config_dict)
