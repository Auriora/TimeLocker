"""
Configuration validation for TimeLocker.

This module provides comprehensive configuration validation following the
Single Responsibility Principle by focusing solely on validation logic.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import urlparse

from .configuration_schema import (
    TimeLockerConfig,
    LogLevel,
    CompressionType,
    ThemeType,
    RepositoryConfig,
    BackupTargetConfig
)
from ..interfaces.exceptions import ConfigurationError, InvalidConfigurationError

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of configuration validation"""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str) -> None:
        """Add validation error"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add validation warning"""
        self.warnings.append(message)

    def __bool__(self) -> bool:
        """Return True if validation passed"""
        return self.is_valid


class ConfigurationValidator:
    """
    Configuration validator following Single Responsibility Principle.
    
    This class focuses solely on validating configuration data and structure,
    providing comprehensive validation with clear error messages.
    """

    def __init__(self):
        """Initialize configuration validator"""
        self._cron_pattern = re.compile(
                r'^(\*|[0-5]?\d)(\s+(\*|[01]?\d|2[0-3]))(\s+(\*|[12]?\d|3[01]))(\s+(\*|[1-9]|1[0-2]))(\s+(\*|[0-6]))$'
        )

    def validate_config(self, config: Union[TimeLockerConfig, Dict[str, Any]]) -> ValidationResult:
        """
        Validate complete configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        result = ValidationResult()

        try:
            # Convert dict to TimeLockerConfig if needed
            if isinstance(config, dict):
                config = TimeLockerConfig.from_dict(config)

            # Validate each section
            self._validate_general_config(config.general, result)
            self._validate_backup_config(config.backup, result)
            self._validate_restore_config(config.restore, result)
            self._validate_security_config(config.security, result)
            self._validate_ui_config(config.ui, result)
            self._validate_notification_config(config.notifications, result)
            self._validate_monitoring_config(config.monitoring, result)
            self._validate_repositories(config.repositories, result)
            self._validate_backup_targets(config.backup_targets, config.repositories, result)

        except Exception as e:
            result.add_error(f"Configuration validation failed: {e}")

        return result

    def _validate_general_config(self, general: Any, result: ValidationResult) -> None:
        """Validate general configuration section"""
        if not hasattr(general, 'app_name') or not general.app_name:
            result.add_error("General.app_name is required")

        if hasattr(general, 'log_level'):
            if isinstance(general.log_level, str):
                if general.log_level.upper() not in [level.value for level in LogLevel]:
                    result.add_error(f"Invalid log level: {general.log_level}")

        if hasattr(general, 'max_concurrent_operations'):
            if not isinstance(general.max_concurrent_operations, int) or general.max_concurrent_operations < 1:
                result.add_error("General.max_concurrent_operations must be a positive integer")

        # Validate directory paths
        for dir_attr in ['data_dir', 'temp_dir']:
            if hasattr(general, dir_attr):
                dir_path = getattr(general, dir_attr)
                if dir_path and not self._is_valid_path(dir_path):
                    result.add_error(f"General.{dir_attr} is not a valid path: {dir_path}")

    def _validate_backup_config(self, backup: Any, result: ValidationResult) -> None:
        """Validate backup configuration section"""
        if hasattr(backup, 'compression'):
            if isinstance(backup.compression, str):
                if backup.compression.lower() not in [comp.value for comp in CompressionType]:
                    result.add_error(f"Invalid compression type: {backup.compression}")

        # Validate bandwidth limits
        for limit_attr in ['limit_upload', 'limit_download']:
            if hasattr(backup, limit_attr):
                limit_value = getattr(backup, limit_attr)
                if limit_value is not None and (not isinstance(limit_value, int) or limit_value < 0):
                    result.add_error(f"Backup.{limit_attr} must be a non-negative integer or None")

    def _validate_restore_config(self, restore: Any, result: ValidationResult) -> None:
        """Validate restore configuration section"""
        # Most restore config is boolean flags, basic type checking is sufficient
        boolean_attrs = [
                'verify_after_restore', 'create_target_directory', 'overwrite_existing',
                'preserve_permissions', 'preserve_ownership', 'preserve_timestamps',
                'sparse_files', 'progress', 'verbose'
        ]

        for attr in boolean_attrs:
            if hasattr(restore, attr):
                value = getattr(restore, attr)
                if not isinstance(value, bool):
                    result.add_warning(f"Restore.{attr} should be a boolean value")

    def _validate_security_config(self, security: Any, result: ValidationResult) -> None:
        """Validate security configuration section"""
        if hasattr(security, 'credential_timeout'):
            if not isinstance(security.credential_timeout, int) or security.credential_timeout < 0:
                result.add_error("Security.credential_timeout must be a non-negative integer")

        if hasattr(security, 'max_failed_attempts'):
            if not isinstance(security.max_failed_attempts, int) or security.max_failed_attempts < 1:
                result.add_error("Security.max_failed_attempts must be a positive integer")

        if hasattr(security, 'lockout_duration'):
            if not isinstance(security.lockout_duration, int) or security.lockout_duration < 0:
                result.add_error("Security.lockout_duration must be a non-negative integer")

    def _validate_ui_config(self, ui: Any, result: ValidationResult) -> None:
        """Validate UI configuration section"""
        if hasattr(ui, 'theme'):
            if isinstance(ui.theme, str):
                if ui.theme.lower() not in [theme.value for theme in ThemeType]:
                    result.add_error(f"Invalid UI theme: {ui.theme}")

        if hasattr(ui, 'auto_refresh_interval'):
            if not isinstance(ui.auto_refresh_interval, int) or ui.auto_refresh_interval < 1:
                result.add_error("UI.auto_refresh_interval must be a positive integer")

        if hasattr(ui, 'max_log_entries'):
            if not isinstance(ui.max_log_entries, int) or ui.max_log_entries < 1:
                result.add_error("UI.max_log_entries must be a positive integer")

    def _validate_notification_config(self, notifications: Any, result: ValidationResult) -> None:
        """Validate notification configuration section"""
        if hasattr(notifications, 'email_smtp_port'):
            port = notifications.email_smtp_port
            if not isinstance(port, int) or port < 1 or port > 65535:
                result.add_error("Notifications.email_smtp_port must be between 1 and 65535")

        if hasattr(notifications, 'email_recipients'):
            recipients = notifications.email_recipients
            if recipients:
                for email in recipients:
                    if not self._is_valid_email(email):
                        result.add_error(f"Invalid email address: {email}")

    def _validate_monitoring_config(self, monitoring: Any, result: ValidationResult) -> None:
        """Validate monitoring configuration section"""
        int_attrs = ['status_retention_days', 'log_rotation_size', 'log_retention_days']

        for attr in int_attrs:
            if hasattr(monitoring, attr):
                value = getattr(monitoring, attr)
                if not isinstance(value, int) or value < 1:
                    result.add_error(f"Monitoring.{attr} must be a positive integer")

    def _validate_repositories(self, repositories: Dict[str, Any], result: ValidationResult) -> None:
        """Validate repository configurations"""
        if not repositories:
            result.add_warning("No repositories configured")
            return

        for name, repo_config in repositories.items():
            self._validate_repository(name, repo_config, result)

    def _validate_repository(self, name: str, repo_config: Any, result: ValidationResult) -> None:
        """Validate individual repository configuration"""
        if not name or not isinstance(name, str):
            result.add_error("Repository name must be a non-empty string")
            return

        if not hasattr(repo_config, 'location') or not repo_config.location:
            result.add_error(f"Repository '{name}' must have a location")
            return

        # Validate repository location
        if not self._is_valid_repository_location(repo_config.location):
            result.add_error(f"Repository '{name}' has invalid location: {repo_config.location}")

        # Validate password configuration
        password_fields = [
                bool(hasattr(repo_config, 'password') and repo_config.password),
                bool(hasattr(repo_config, 'password_file') and repo_config.password_file),
                bool(hasattr(repo_config, 'password_command') and repo_config.password_command)
        ]

        password_count = sum(password_fields)
        if password_count > 1:
            result.add_error(f"Repository '{name}' can only have one password method configured")
        elif password_count == 0:
            result.add_warning(f"Repository '{name}' has no password configured")

    def _validate_backup_targets(self, targets: Dict[str, Any], repositories: Dict[str, Any], result: ValidationResult) -> None:
        """Validate backup target configurations"""
        for name, target_config in targets.items():
            self._validate_backup_target(name, target_config, repositories, result)

    def _validate_backup_target(self, name: str, target_config: Any, repositories: Dict[str, Any], result: ValidationResult) -> None:
        """Validate individual backup target configuration"""
        if not name or not isinstance(name, str):
            result.add_error("Backup target name must be a non-empty string")
            return

        # Validate required fields
        if not hasattr(target_config, 'paths') or not target_config.paths:
            result.add_error(f"Backup target '{name}' must have at least one path")

        if not hasattr(target_config, 'repository') or not target_config.repository:
            result.add_error(f"Backup target '{name}' must specify a repository")
        elif target_config.repository not in repositories:
            result.add_error(f"Backup target '{name}' references unknown repository: {target_config.repository}")

        # Validate paths exist
        if hasattr(target_config, 'paths'):
            for path in target_config.paths:
                if not Path(path).exists():
                    result.add_warning(f"Backup target '{name}' path does not exist: {path}")

        # Validate schedule if present
        if hasattr(target_config, 'schedule') and target_config.schedule:
            if not self._is_valid_cron_expression(target_config.schedule):
                result.add_error(f"Backup target '{name}' has invalid schedule: {target_config.schedule}")

    def _is_valid_path(self, path: str) -> bool:
        """Check if path is valid"""
        try:
            Path(path)
            return True
        except (ValueError, OSError):
            return False

    def _is_valid_email(self, email: str) -> bool:
        """Check if email address is valid"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return bool(email_pattern.match(email))

    def _is_valid_repository_location(self, location: str) -> bool:
        """Check if repository location is valid"""
        # Check for various repository location formats
        if location.startswith(('file://', '/')):
            # Local file path
            return self._is_valid_path(location.replace('file://', ''))
        elif location.startswith(('sftp://', 'ssh://', 'rest:', 'rclone:')):
            # Remote repository
            return True  # Basic validation, could be more sophisticated
        else:
            # Assume it's a valid location format
            return True

    def _is_valid_cron_expression(self, cron_expr: str) -> bool:
        """Check if cron expression is valid"""
        return bool(self._cron_pattern.match(cron_expr.strip()))
