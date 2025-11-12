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

Schedule Validation System

This module provides comprehensive validation for schedule configurations,
including integration point validation and dry-run capabilities.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .scheduling_models import (
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    ValidationResult,
    RetryConfig,
    MonitoringConfig
)
from .scheduling_exceptions import (
    SchedulingError,
    PolicyValidationError,
    DataSelectionValidationError,
    RepositoryValidationError
)
from .integration_clients import (
    PolicyManagementClient,
    DataSelectionClient,
    RepositoryManagementClient
)
from .platform_adapter import PlatformAdapter

logger = logging.getLogger(__name__)


class ScheduleValidator:
    """
    Comprehensive validation system for schedule configurations.
    
    Validates schedule configurations against all integration points
    and provides dry-run capabilities for testing.
    """
    
    def __init__(
        self,
        platform_adapter: PlatformAdapter,
        policy_client: Optional[PolicyManagementClient] = None,
        data_selection_client: Optional[DataSelectionClient] = None,
        repository_client: Optional[RepositoryManagementClient] = None
    ):
        """
        Initialize schedule validator.
        
        Args:
            platform_adapter: Platform adapter for platform-specific validation
            policy_client: Optional policy management client
            data_selection_client: Optional data selection client
            repository_client: Optional repository management client
        """
        self.logger = logging.getLogger(f"{__name__}.ScheduleValidator")
        self.platform_adapter = platform_adapter
        
        # Initialize integration clients
        self.policy_client = policy_client or PolicyManagementClient()
        self.data_selection_client = data_selection_client or DataSelectionClient()
        self.repository_client = repository_client or RepositoryManagementClient()
    
    def validate_schedule_configuration(
        self,
        config: ScheduleConfig,
        comprehensive: bool = True
    ) -> ValidationResult:
        """
        Validate schedule configuration comprehensively.
        
        Args:
            config: Schedule configuration to validate
            comprehensive: If True, perform deep validation including integration checks
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validate basic configuration
            self._validate_basic_config(config, result)
            
            # Validate schedule pattern
            self._validate_schedule_pattern(config.schedule_pattern, result)
            
            # Validate retry configuration
            if config.retry_config:
                self._validate_retry_config(config.retry_config, result)
            
            # Validate monitoring configuration
            if config.monitoring_config:
                self._validate_monitoring_config(config.monitoring_config, result)
            
            # Validate platform compatibility
            self._validate_platform_compatibility(config, result)
            
            # Perform comprehensive validation if requested
            if comprehensive:
                self._validate_policy_integration(config, result)
                self._validate_data_selection_integration(config, result)
                self._validate_repository_integration(config, result)
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
            self.logger.error(f"Validation failed for schedule {config.schedule_id}: {e}")
        
        return result
    
    def _validate_basic_config(self, config: ScheduleConfig, result: ValidationResult) -> None:
        """Validate basic configuration fields."""
        if not config.schedule_id:
            result.add_error("Schedule ID is required")
        
        if not config.name or not config.name.strip():
            result.add_error("Schedule name is required")
        
        if not config.policy_id:
            result.add_error("Policy ID is required")
        
        if config.execution_timeout is not None:
            if config.execution_timeout <= 0:
                result.add_error("Execution timeout must be positive")
            elif config.execution_timeout < 60:
                result.add_warning("Execution timeout is very short (< 60 seconds)")
            elif config.execution_timeout > 86400:
                result.add_warning("Execution timeout is very long (> 24 hours)")
    
    def _validate_schedule_pattern(self, pattern: SchedulePattern, result: ValidationResult) -> None:
        """Validate schedule pattern configuration."""
        try:
            if pattern.pattern_type == SchedulePatternType.CRON:
                self._validate_cron_expression(pattern.cron_expression, result)
            
            elif pattern.pattern_type == SchedulePatternType.INTERVAL:
                self._validate_interval_pattern(pattern.interval_minutes, result)
            
            elif pattern.pattern_type == SchedulePatternType.CALENDAR:
                self._validate_calendar_pattern(pattern.calendar_config, result)
            
            # Validate randomize delay
            if pattern.randomize_delay_minutes < 0:
                result.add_error("Randomize delay cannot be negative")
            elif pattern.randomize_delay_minutes > 60:
                result.add_warning("Randomize delay is very long (> 60 minutes)")
            
            # Validate backup window if present
            if pattern.backup_window:
                self._validate_backup_window(pattern.backup_window, result)
                
        except Exception as e:
            result.add_error(f"Schedule pattern validation error: {str(e)}")
    
    def _validate_cron_expression(self, expression: Optional[str], result: ValidationResult) -> None:
        """Validate cron expression syntax."""
        if not expression:
            result.add_error("Cron expression is required for CRON pattern type")
            return
        
        try:
            # Basic cron validation - check field count
            fields = expression.strip().split()
            if len(fields) not in [5, 6]:
                result.add_error(f"Invalid cron expression: expected 5 or 6 fields, got {len(fields)}")
                return
            
            # Validate each field
            for i, field in enumerate(fields[:5]):
                if not self._is_valid_cron_field(field, i):
                    result.add_error(f"Invalid cron field at position {i}: {field}")
            
        except Exception as e:
            result.add_error(f"Cron expression validation error: {str(e)}")
    
    def _is_valid_cron_field(self, field: str, position: int) -> bool:
        """
        Validate a single cron field.
        
        Args:
            field: Cron field value
            position: Field position (0=minute, 1=hour, 2=day, 3=month, 4=weekday)
            
        Returns:
            True if field is valid
        """
        # Allow wildcards and ranges
        if field in ['*', '?']:
            return True
        
        # Allow step values
        if '/' in field:
            parts = field.split('/')
            if len(parts) != 2:
                return False
            return self._is_valid_cron_field(parts[0], position) and parts[1].isdigit()
        
        # Allow ranges
        if '-' in field:
            parts = field.split('-')
            if len(parts) != 2:
                return False
            return all(p.isdigit() for p in parts)
        
        # Allow lists
        if ',' in field:
            return all(self._is_valid_cron_field(f, position) for f in field.split(','))
        
        # Must be a number
        return field.isdigit()
    
    def _validate_interval_pattern(self, interval_minutes: Optional[int], result: ValidationResult) -> None:
        """Validate interval-based pattern."""
        if interval_minutes is None:
            result.add_error("Interval minutes is required for INTERVAL pattern type")
            return
        
        if interval_minutes <= 0:
            result.add_error("Interval minutes must be positive")
        elif interval_minutes < 5:
            result.add_warning("Interval is very short (< 5 minutes)")
        elif interval_minutes > 10080:  # 1 week
            result.add_warning("Interval is very long (> 1 week)")
    
    def _validate_calendar_pattern(self, calendar_config, result: ValidationResult) -> None:
        """Validate calendar-based pattern."""
        if calendar_config is None:
            result.add_error("Calendar config is required for CALENDAR pattern type")
            return
        
        # Validation is done in CalendarConfig.__post_init__
        # Just check for reasonable values
        if len(calendar_config.days_of_week) == 0:
            result.add_error("At least one day of week must be specified")
        
        if calendar_config.weeks_of_month and len(calendar_config.weeks_of_month) == 0:
            result.add_warning("Weeks of month is empty, will run all weeks")
        
        if calendar_config.months_of_year and len(calendar_config.months_of_year) == 0:
            result.add_warning("Months of year is empty, will run all months")
    
    def _validate_backup_window(self, backup_window, result: ValidationResult) -> None:
        """Validate backup window configuration."""
        if backup_window.start_time >= backup_window.end_time:
            result.add_error("Backup window start time must be before end time")
        
        # Check for reasonable window size
        from datetime import datetime, timedelta
        start_dt = datetime.combine(datetime.today(), backup_window.start_time)
        end_dt = datetime.combine(datetime.today(), backup_window.end_time)
        window_duration = end_dt - start_dt
        
        if window_duration < timedelta(hours=1):
            result.add_warning("Backup window is very short (< 1 hour)")
    
    def _validate_retry_config(self, retry_config: RetryConfig, result: ValidationResult) -> None:
        """Validate retry configuration."""
        # Validation is done in RetryConfig.__post_init__
        # Just add warnings for extreme values
        if retry_config.max_attempts > 10:
            result.add_warning("Max retry attempts is very high (> 10)")
        
        if retry_config.max_delay_minutes > 1440:  # 24 hours
            result.add_warning("Max retry delay is very long (> 24 hours)")
    
    def _validate_monitoring_config(self, monitoring_config: MonitoringConfig, result: ValidationResult) -> None:
        """Validate monitoring configuration."""
        if monitoring_config.webhook_url:
            if not monitoring_config.webhook_url.startswith(('http://', 'https://')):
                result.add_error("Webhook URL must start with http:// or https://")
        
        if monitoring_config.health_check_url:
            if not monitoring_config.health_check_url.startswith(('http://', 'https://')):
                result.add_error("Health check URL must start with http:// or https://")
    
    def _validate_platform_compatibility(self, config: ScheduleConfig, result: ValidationResult) -> None:
        """Validate platform-specific compatibility."""
        try:
            platform_result = self.platform_adapter.validate_schedule_config(config)
            
            for error in platform_result.errors:
                result.add_error(f"Platform validation: {error}")
            
            for warning in platform_result.warnings:
                result.add_warning(f"Platform warning: {warning}")
                
        except Exception as e:
            result.add_error(f"Platform validation error: {str(e)}")
    
    def _validate_policy_integration(self, config: ScheduleConfig, result: ValidationResult) -> None:
        """Validate policy management integration."""
        try:
            is_valid, errors = self.policy_client.validate_policy_for_scheduling(config.policy_id)
            
            if not is_valid:
                for error in errors:
                    result.add_error(f"Policy validation: {error}")
            
            # Get policy to validate data selection and repository references
            policy = self.policy_client.get_backup_policy(config.policy_id)
            if policy:
                # Store references for further validation
                config._policy_data_selections = getattr(policy, 'data_selection_refs', [])
                config._policy_repositories = getattr(policy, 'target_repositories', [])
            else:
                result.add_error(f"Failed to retrieve policy {config.policy_id}")
                
        except Exception as e:
            result.add_error(f"Policy integration validation error: {str(e)}")
    
    def _validate_data_selection_integration(self, config: ScheduleConfig, result: ValidationResult) -> None:
        """Validate data selection integration."""
        try:
            # Get data selection references from policy
            data_selections = getattr(config, '_policy_data_selections', [])
            
            if not data_selections:
                result.add_warning("No data selection references found in policy")
                return
            
            for selection_ref in data_selections:
                is_valid, errors = self.data_selection_client.validate_selection_for_scheduling(selection_ref)
                
                if not is_valid:
                    for error in errors:
                        result.add_error(f"Data selection validation ({selection_ref}): {error}")
                        
        except Exception as e:
            result.add_error(f"Data selection integration validation error: {str(e)}")
    
    def _validate_repository_integration(self, config: ScheduleConfig, result: ValidationResult) -> None:
        """Validate repository management integration."""
        try:
            # Get repository references from policy
            repositories = getattr(config, '_policy_repositories', [])
            
            if not repositories:
                result.add_error("No target repositories found in policy")
                return
            
            for repo_id in repositories:
                is_valid, errors = self.repository_client.validate_repository_for_scheduling(repo_id)
                
                if not is_valid:
                    for error in errors:
                        result.add_error(f"Repository validation ({repo_id}): {error}")
                        
        except Exception as e:
            result.add_error(f"Repository integration validation error: {str(e)}")
    
    def validate_dry_run_configuration(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate configuration for dry-run execution.
        
        This performs all validations plus additional checks specific to
        testing scheduled backup configurations.
        
        Args:
            config: Schedule configuration to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = self.validate_schedule_configuration(config, comprehensive=True)
        
        # Additional dry-run specific validations
        try:
            # Check that policy exists and is accessible
            policy = self.policy_client.get_backup_policy(config.policy_id)
            if not policy:
                result.add_error("Policy not found for dry-run")
                return result
            
            # Check data selection accessibility
            data_selections = getattr(policy, 'data_selection_refs', [])
            for selection_ref in data_selections:
                template = self.data_selection_client.get_selection_template(selection_ref)
                if not template:
                    result.add_error(f"Data selection template {selection_ref} not accessible for dry-run")
            
            # Check repository accessibility
            repositories = getattr(policy, 'target_repositories', [])
            for repo_id in repositories:
                repo_config = self.repository_client.get_repository_config(repo_id)
                if not repo_config:
                    result.add_error(f"Repository {repo_id} not accessible for dry-run")
            
            # Validate that paths in data selection exist and are readable
            self._validate_path_accessibility(data_selections, result)
            
        except Exception as e:
            result.add_error(f"Dry-run validation error: {str(e)}")
        
        return result
    
    def _validate_path_accessibility(self, data_selections: List[str], result: ValidationResult) -> None:
        """
        Validate that paths in data selections are accessible.
        
        Args:
            data_selections: List of data selection template IDs
            result: ValidationResult to update
        """
        for selection_ref in data_selections:
            try:
                template = self.data_selection_client.get_selection_template(selection_ref)
                if not template:
                    continue
                
                # Check include paths
                include_paths = getattr(template, 'include_paths', [])
                for path_str in include_paths:
                    path = Path(path_str)
                    if not path.exists():
                        result.add_warning(f"Include path does not exist: {path}")
                    elif not os.access(path, os.R_OK):
                        result.add_error(f"Include path is not readable: {path}")
                        
            except Exception as e:
                result.add_warning(f"Failed to validate paths for {selection_ref}: {str(e)}")
