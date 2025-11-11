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

logger = logging.getLogger(__name__)


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
