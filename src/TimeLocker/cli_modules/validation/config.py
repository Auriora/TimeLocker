"""
Configuration-specific validators.

This module provides validators for TimeLocker configuration objects,
including repositories, backup targets, and complete configurations.
"""

from typing import Any, Optional, Dict
from pathlib import Path

from .base import Validator, ValidationResult, CompositeValidator
from .common import (
    PathValidator,
    NameValidator,
    EmailValidator,
    URLValidator,
    PortValidator,
    IntegerRangeValidator,
)


class RepositoryConfigValidator(Validator):
    """
    Validator for repository configurations.
    
    Validates repository location, password configuration, and other settings.
    """
    
    def __init__(self, field_name: str = "repository"):
        """Initialize repository config validator."""
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate repository configuration."""
        result = ValidationResult()
        
        if not value:
            result.add_error(
                self.field_name,
                "Repository configuration cannot be empty",
                "EMPTY_REPOSITORY_CONFIG"
            )
            return result
        
        # Validate name
        if hasattr(value, 'name'):
            name_validator = NameValidator(field_name=f"{self.field_name}.name")
            name_result = name_validator.validate(value.name, context)
            result.merge(name_result)
        else:
            result.add_error(
                f"{self.field_name}.name",
                "Repository must have a name",
                "MISSING_NAME"
            )
        
        # Validate location
        if hasattr(value, 'location'):
            if not value.location:
                result.add_error(
                    f"{self.field_name}.location",
                    "Repository must have a location",
                    "MISSING_LOCATION"
                )
            else:
                # Validate location format based on type
                location = value.location
                if location.startswith(('file://', '/')):
                    # Local path
                    path_validator = PathValidator(
                        allow_relative=False,
                        field_name=f"{self.field_name}.location"
                    )
                    path_result = path_validator.validate(
                        location.replace('file://', ''),
                        context
                    )
                    result.merge(path_result)
                elif location.startswith(('http://', 'https://', 'sftp://', 'ssh://')):
                    # URL-based location
                    url_validator = URLValidator(field_name=f"{self.field_name}.location")
                    url_result = url_validator.validate(location, context)
                    result.merge(url_result)
        else:
            result.add_error(
                f"{self.field_name}.location",
                "Repository must have a location",
                "MISSING_LOCATION"
            )
        
        # Validate password configuration
        password_fields = []
        if hasattr(value, 'password') and value.password:
            password_fields.append('password')
        if hasattr(value, 'password_file') and value.password_file:
            password_fields.append('password_file')
        if hasattr(value, 'password_command') and value.password_command:
            password_fields.append('password_command')
        
        if len(password_fields) > 1:
            result.add_error(
                f"{self.field_name}.password",
                f"Only one password method can be configured, found: {', '.join(password_fields)}",
                "MULTIPLE_PASSWORD_METHODS",
                {"methods": password_fields}
            )
        
        # Validate password file if specified
        if hasattr(value, 'password_file') and value.password_file:
            path_validator = PathValidator(
                must_exist=True,
                must_be_file=True,
                must_be_readable=True,
                field_name=f"{self.field_name}.password_file"
            )
            path_result = path_validator.validate(value.password_file, context)
            result.merge(path_result)
        
        return result


class BackupTargetConfigValidator(Validator):
    """
    Validator for backup target configurations.
    
    Validates paths, schedules, and other backup target settings.
    """
    
    def __init__(self, field_name: str = "backup_target"):
        """Initialize backup target config validator."""
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate backup target configuration."""
        result = ValidationResult()
        
        if not value:
            result.add_error(
                self.field_name,
                "Backup target configuration cannot be empty",
                "EMPTY_BACKUP_TARGET_CONFIG"
            )
            return result
        
        # Validate name
        if hasattr(value, 'name'):
            name_validator = NameValidator(field_name=f"{self.field_name}.name")
            name_result = name_validator.validate(value.name, context)
            result.merge(name_result)
        else:
            result.add_error(
                f"{self.field_name}.name",
                "Backup target must have a name",
                "MISSING_NAME"
            )
        
        # Validate paths
        if hasattr(value, 'paths'):
            if not value.paths:
                result.add_error(
                    f"{self.field_name}.paths",
                    "Backup target must have at least one path",
                    "NO_PATHS"
                )
            else:
                for idx, path in enumerate(value.paths):
                    path_validator = PathValidator(
                        field_name=f"{self.field_name}.paths[{idx}]"
                    )
                    path_result = path_validator.validate(path, context)
                    
                    # Convert errors to warnings for non-existent paths
                    # (they might be created later)
                    for issue in path_result.get_errors():
                        if issue.code == "PATH_NOT_FOUND":
                            result.add_warning(
                                issue.field,
                                f"Path does not exist: {path}",
                                "PATH_NOT_FOUND_WARNING",
                                issue.context
                            )
                        else:
                            result.issues.append(issue)
                            result.valid = False
        else:
            result.add_error(
                f"{self.field_name}.paths",
                "Backup target must have paths",
                "MISSING_PATHS"
            )
        
        # Validate schedule if present
        if hasattr(value, 'schedule') and value.schedule:
            from .common import CronValidator
            cron_validator = CronValidator(field_name=f"{self.field_name}.schedule")
            cron_result = cron_validator.validate(value.schedule, context)
            result.merge(cron_result)
        
        return result


class ConfigValidator(Validator):
    """
    Validator for complete TimeLocker configuration.
    
    Validates all configuration sections and cross-references.
    """
    
    def __init__(self, field_name: str = "config"):
        """Initialize config validator."""
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate complete configuration."""
        result = ValidationResult()
        
        if not value:
            result.add_error(
                self.field_name,
                "Configuration cannot be empty",
                "EMPTY_CONFIG"
            )
            return result
        
        # Validate general section
        if hasattr(value, 'general'):
            self._validate_general_section(value.general, result)
        
        # Validate backup section
        if hasattr(value, 'backup'):
            self._validate_backup_section(value.backup, result)
        
        # Validate security section
        if hasattr(value, 'security'):
            self._validate_security_section(value.security, result)
        
        # Validate UI section
        if hasattr(value, 'ui'):
            self._validate_ui_section(value.ui, result)
        
        # Validate notifications section
        if hasattr(value, 'notifications'):
            self._validate_notifications_section(value.notifications, result)
        
        # Validate monitoring section
        if hasattr(value, 'monitoring'):
            self._validate_monitoring_section(value.monitoring, result)
        
        # Validate repositories
        if hasattr(value, 'repositories'):
            if not value.repositories:
                result.add_warning(
                    f"{self.field_name}.repositories",
                    "No repositories configured",
                    "NO_REPOSITORIES"
                )
            else:
                for name, repo_config in value.repositories.items():
                    repo_validator = RepositoryConfigValidator(
                        field_name=f"{self.field_name}.repositories.{name}"
                    )
                    repo_result = repo_validator.validate(repo_config, context)
                    result.merge(repo_result)
        
        # Validate backup targets
        if hasattr(value, 'backup_targets'):
            for name, target_config in value.backup_targets.items():
                target_validator = BackupTargetConfigValidator(
                    field_name=f"{self.field_name}.backup_targets.{name}"
                )
                target_result = target_validator.validate(target_config, context)
                result.merge(target_result)
        
        return result
    
    def _validate_general_section(self, general: Any, result: ValidationResult) -> None:
        """Validate general configuration section."""
        field_prefix = f"{self.field_name}.general"
        
        if not hasattr(general, 'app_name') or not general.app_name:
            result.add_error(
                f"{field_prefix}.app_name",
                "Application name is required",
                "MISSING_APP_NAME"
            )
        
        if hasattr(general, 'max_concurrent_operations'):
            int_validator = IntegerRangeValidator(
                min_value=1,
                field_name=f"{field_prefix}.max_concurrent_operations"
            )
            int_result = int_validator.validate(general.max_concurrent_operations)
            result.merge(int_result)
    
    def _validate_backup_section(self, backup: Any, result: ValidationResult) -> None:
        """Validate backup configuration section."""
        field_prefix = f"{self.field_name}.backup"
        
        # Validate bandwidth limits
        for limit_attr in ['limit_upload', 'limit_download']:
            if hasattr(backup, limit_attr):
                limit_value = getattr(backup, limit_attr)
                if limit_value is not None:
                    int_validator = IntegerRangeValidator(
                        min_value=0,
                        field_name=f"{field_prefix}.{limit_attr}"
                    )
                    int_result = int_validator.validate(limit_value)
                    result.merge(int_result)
    
    def _validate_security_section(self, security: Any, result: ValidationResult) -> None:
        """Validate security configuration section."""
        field_prefix = f"{self.field_name}.security"
        
        if hasattr(security, 'credential_timeout'):
            int_validator = IntegerRangeValidator(
                min_value=0,
                field_name=f"{field_prefix}.credential_timeout"
            )
            int_result = int_validator.validate(security.credential_timeout)
            result.merge(int_result)
        
        if hasattr(security, 'max_failed_attempts'):
            int_validator = IntegerRangeValidator(
                min_value=1,
                field_name=f"{field_prefix}.max_failed_attempts"
            )
            int_result = int_validator.validate(security.max_failed_attempts)
            result.merge(int_result)
    
    def _validate_ui_section(self, ui: Any, result: ValidationResult) -> None:
        """Validate UI configuration section."""
        field_prefix = f"{self.field_name}.ui"
        
        if hasattr(ui, 'auto_refresh_interval'):
            int_validator = IntegerRangeValidator(
                min_value=1,
                field_name=f"{field_prefix}.auto_refresh_interval"
            )
            int_result = int_validator.validate(ui.auto_refresh_interval)
            result.merge(int_result)
    
    def _validate_notifications_section(self, notifications: Any, result: ValidationResult) -> None:
        """Validate notifications configuration section."""
        field_prefix = f"{self.field_name}.notifications"
        
        if hasattr(notifications, 'email_smtp_port'):
            port_validator = PortValidator(field_name=f"{field_prefix}.email_smtp_port")
            port_result = port_validator.validate(notifications.email_smtp_port)
            result.merge(port_result)
        
        if hasattr(notifications, 'email_recipients') and notifications.email_recipients:
            for idx, email in enumerate(notifications.email_recipients):
                email_validator = EmailValidator(
                    field_name=f"{field_prefix}.email_recipients[{idx}]"
                )
                email_result = email_validator.validate(email)
                result.merge(email_result)
    
    def _validate_monitoring_section(self, monitoring: Any, result: ValidationResult) -> None:
        """Validate monitoring configuration section."""
        field_prefix = f"{self.field_name}.monitoring"
        
        int_attrs = ['status_retention_days', 'log_rotation_size', 'log_retention_days']
        
        for attr in int_attrs:
            if hasattr(monitoring, attr):
                value = getattr(monitoring, attr)
                int_validator = IntegerRangeValidator(
                    min_value=1,
                    field_name=f"{field_prefix}.{attr}"
                )
                int_result = int_validator.validate(value)
                result.merge(int_result)
