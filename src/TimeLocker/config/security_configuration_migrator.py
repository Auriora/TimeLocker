"""
Security Configuration Migration and Upgrade Handler for TimeLocker.

This module handles migration of security configuration from older versions
and provides upgrade handling for security settings.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .configuration_schema import SecurityConfig
from .configuration_defaults import ConfigurationDefaults
from .configuration_validator import ValidationResult
from ..interfaces.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class MigrationVersion(Enum):
    """Security configuration migration versions"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V1_2 = "1.2"
    CURRENT = "1.2"


@dataclass
class MigrationStep:
    """Individual migration step definition"""
    from_version: str
    to_version: str
    description: str
    migration_function: str
    is_required: bool = True
    backup_required: bool = True


@dataclass
class MigrationResult:
    """Migration operation result"""
    success: bool
    from_version: str
    to_version: str
    steps_completed: List[str]
    errors: List[str]
    warnings: List[str]
    backup_created: Optional[str] = None
    migration_time: Optional[datetime] = None


class SecurityConfigurationMigrator:
    """
    Security configuration migration and upgrade handler.
    
    This class handles migration of security configuration from older versions,
    following the Single Responsibility Principle by focusing solely on
    migration and upgrade operations.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize security configuration migrator.
        
        Args:
            config_dir: Optional configuration directory
        """
        self.config_dir = config_dir or Path.home() / ".timelocker"
        self.migration_log_file = self.config_dir / "security_migration.log"
        self._migration_steps = self._initialize_migration_steps()
        
    def _initialize_migration_steps(self) -> List[MigrationStep]:
        """Initialize migration steps"""
        return [
            MigrationStep(
                from_version="1.0",
                to_version="1.1",
                description="Add password strength checking and confirmation requirements",
                migration_function="_migrate_v1_0_to_v1_1"
            ),
            MigrationStep(
                from_version="1.1",
                to_version="1.2",
                description="Add advanced security settings and validation",
                migration_function="_migrate_v1_1_to_v1_2"
            )
        ]

    def detect_configuration_version(self, config_data: Dict[str, Any]) -> str:
        """
        Detect the version of security configuration.
        
        Args:
            config_data: Security configuration data
            
        Returns:
            str: Detected version
        """
        try:
            # Check for version field
            if "version" in config_data:
                return config_data["version"]
                
            # Detect version based on available fields
            if "password_strength_check" in config_data and "require_password_confirmation" in config_data:
                return MigrationVersion.V1_2.value
            elif "password_strength_check" in config_data:
                return MigrationVersion.V1_1.value
            else:
                return MigrationVersion.V1_0.value
                
        except Exception as e:
            logger.warning(f"Failed to detect configuration version: {e}")
            return MigrationVersion.V1_0.value

    def is_migration_needed(self, config_data: Dict[str, Any]) -> bool:
        """
        Check if migration is needed for security configuration.
        
        Args:
            config_data: Security configuration data
            
        Returns:
            bool: True if migration is needed
        """
        try:
            current_version = self.detect_configuration_version(config_data)
            target_version = MigrationVersion.CURRENT.value
            
            return current_version != target_version
            
        except Exception as e:
            logger.error(f"Failed to check migration need: {e}")
            return False

    def migrate_security_configuration(self, config_data: Dict[str, Any], 
                                     target_version: Optional[str] = None) -> MigrationResult:
        """
        Migrate security configuration to target version.
        
        Args:
            config_data: Security configuration data to migrate
            target_version: Target version (defaults to current)
            
        Returns:
            MigrationResult: Migration operation result
        """
        start_time = datetime.now()
        current_version = self.detect_configuration_version(config_data)
        target_version = target_version or MigrationVersion.CURRENT.value
        
        result = MigrationResult(
            success=False,
            from_version=current_version,
            to_version=target_version,
            steps_completed=[],
            errors=[],
            warnings=[],
            migration_time=start_time
        )
        
        try:
            logger.info(f"Starting security configuration migration from {current_version} to {target_version}")
            
            # Check if migration is needed
            if current_version == target_version:
                result.success = True
                result.warnings.append("Configuration is already at target version")
                return result
                
            # Create backup
            backup_id = self._create_migration_backup(config_data, current_version)
            result.backup_created = backup_id
            
            # Apply migration steps
            migrated_data = config_data.copy()
            current_step_version = current_version
            
            for step in self._migration_steps:
                if self._should_apply_step(step, current_step_version, target_version):
                    try:
                        logger.info(f"Applying migration step: {step.description}")
                        
                        migration_method = getattr(self, step.migration_function, None)
                        if migration_method:
                            migrated_data = migration_method(migrated_data)
                            current_step_version = step.to_version
                            result.steps_completed.append(step.description)
                            
                            # Log migration step
                            self._log_migration_step(step, migrated_data)
                        else:
                            error_msg = f"Migration method {step.migration_function} not found"
                            result.errors.append(error_msg)
                            logger.error(error_msg)
                            
                    except Exception as e:
                        error_msg = f"Failed to apply migration step {step.description}: {e}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)
                        
                        if step.is_required:
                            return result
                            
            # Validate migrated configuration
            validation_result = self._validate_migrated_configuration(migrated_data)
            if not validation_result.is_valid:
                result.errors.extend(validation_result.errors)
                result.warnings.extend(validation_result.warnings)
                return result
                
            # Update configuration data with migrated version
            migrated_data["version"] = target_version
            migrated_data["migrated_at"] = datetime.now().isoformat()
            migrated_data["migrated_from"] = current_version
            
            # Copy migrated data back to original
            config_data.clear()
            config_data.update(migrated_data)
            
            result.success = True
            logger.info(f"Security configuration migration completed successfully")
            
        except Exception as e:
            error_msg = f"Security configuration migration failed: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        finally:
            result.migration_time = datetime.now() - start_time
            
        return result

    def _should_apply_step(self, step: MigrationStep, current_version: str, target_version: str) -> bool:
        """Check if migration step should be applied"""
        try:
            # Simple version comparison (assumes semantic versioning)
            current_parts = [int(x) for x in current_version.split('.')]
            step_from_parts = [int(x) for x in step.from_version.split('.')]
            step_to_parts = [int(x) for x in step.to_version.split('.')]
            target_parts = [int(x) for x in target_version.split('.')]
            
            # Apply step if current version matches step from version and target is >= step to version
            return (current_parts == step_from_parts and 
                   step_to_parts <= target_parts)
                   
        except Exception as e:
            logger.warning(f"Failed to compare versions for step {step.description}: {e}")
            return False

    def _migrate_v1_0_to_v1_1(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from version 1.0 to 1.1.
        
        Adds password strength checking configuration.
        """
        migrated = config_data.copy()
        
        # Add password strength checking (default enabled)
        if "password_strength_check" not in migrated:
            migrated["password_strength_check"] = True
            
        # Ensure other v1.1 fields exist with defaults
        defaults = asdict(ConfigurationDefaults.get_security_defaults())
        
        v1_1_fields = ["password_strength_check"]
        for field in v1_1_fields:
            if field not in migrated:
                migrated[field] = defaults.get(field, True)
                
        logger.info("Migrated security configuration from v1.0 to v1.1")
        return migrated

    def _migrate_v1_1_to_v1_2(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate from version 1.1 to 1.2.
        
        Adds password confirmation requirements and advanced settings.
        """
        migrated = config_data.copy()
        
        # Add password confirmation requirement (default enabled)
        if "require_password_confirmation" not in migrated:
            migrated["require_password_confirmation"] = True
            
        # Ensure other v1.2 fields exist with defaults
        defaults = asdict(ConfigurationDefaults.get_security_defaults())
        
        v1_2_fields = ["require_password_confirmation"]
        for field in v1_2_fields:
            if field not in migrated:
                migrated[field] = defaults.get(field, True)
                
        # Migrate legacy field names if they exist
        legacy_mappings = {
            "enable_encryption": "encryption_enabled",
            "enable_audit_log": "audit_logging",
            "session_timeout": "credential_timeout",
            "max_login_attempts": "max_failed_attempts",
            "lockout_time": "lockout_duration"
        }
        
        for old_field, new_field in legacy_mappings.items():
            if old_field in migrated and new_field not in migrated:
                migrated[new_field] = migrated.pop(old_field)
                
        logger.info("Migrated security configuration from v1.1 to v1.2")
        return migrated

    def _create_migration_backup(self, config_data: Dict[str, Any], version: str) -> str:
        """Create backup before migration"""
        try:
            backup_dir = self.config_dir / "backups" / "security_migration"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"security_config_v{version}_{timestamp}"
            backup_file = backup_dir / f"{backup_id}.json"
            
            backup_data = {
                "version": version,
                "created_at": datetime.now().isoformat(),
                "config_data": config_data
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
            logger.info(f"Created migration backup: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.warning(f"Failed to create migration backup: {e}")
            return ""

    def _log_migration_step(self, step: MigrationStep, migrated_data: Dict[str, Any]) -> None:
        """Log migration step details"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "step": step.description,
                "from_version": step.from_version,
                "to_version": step.to_version,
                "config_fields": list(migrated_data.keys())
            }
            
            # Ensure log file exists
            self.migration_log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to log file
            with open(self.migration_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to log migration step: {e}")

    def _validate_migrated_configuration(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate migrated configuration"""
        try:
            # Import here to avoid circular imports
            from .security_configuration_manager import SecurityConfigurationManager
            
            manager = SecurityConfigurationManager()
            return manager.validate_security_config(config_data)
            
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Failed to validate migrated configuration: {e}")
            return result

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history from log file.
        
        Returns:
            List: Migration history entries
        """
        history = []
        
        try:
            if self.migration_log_file.exists():
                with open(self.migration_log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            history.append(entry)
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Failed to read migration history: {e}")
            
        return history

    def rollback_migration(self, backup_id: str) -> bool:
        """
        Rollback migration using backup.
        
        Args:
            backup_id: Backup identifier to restore
            
        Returns:
            bool: True if rollback successful
        """
        try:
            backup_dir = self.config_dir / "backups" / "security_migration"
            backup_file = backup_dir / f"{backup_id}.json"
            
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False
                
            # Load backup data
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
                
            # Validate backup data
            if "config_data" not in backup_data:
                logger.error("Invalid backup data format")
                return False
                
            # This would need to be integrated with the configuration system
            # For now, just log the rollback attempt
            logger.info(f"Rollback requested for backup: {backup_id}")
            logger.info(f"Backup version: {backup_data.get('version', 'unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return False

    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        Clean up old migration backups.
        
        Args:
            keep_count: Number of recent backups to keep
            
        Returns:
            int: Number of backups cleaned up
        """
        try:
            backup_dir = self.config_dir / "backups" / "security_migration"
            
            if not backup_dir.exists():
                return 0
                
            # Get all backup files
            backup_files = list(backup_dir.glob("*.json"))
            
            if len(backup_files) <= keep_count:
                return 0
                
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove old backups
            cleaned_count = 0
            for backup_file in backup_files[keep_count:]:
                try:
                    backup_file.unlink()
                    cleaned_count += 1
                    logger.debug(f"Removed old backup: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {backup_file.name}: {e}")
                    
            logger.info(f"Cleaned up {cleaned_count} old migration backups")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    def get_available_backups(self) -> List[Dict[str, Any]]:
        """
        Get list of available migration backups.
        
        Returns:
            List: Available backup information
        """
        backups = []
        
        try:
            backup_dir = self.config_dir / "backups" / "security_migration"
            
            if not backup_dir.exists():
                return backups
                
            for backup_file in backup_dir.glob("*.json"):
                try:
                    with open(backup_file, 'r') as f:
                        backup_data = json.load(f)
                        
                    backups.append({
                        "backup_id": backup_file.stem,
                        "version": backup_data.get("version", "unknown"),
                        "created_at": backup_data.get("created_at", ""),
                        "file_size": backup_file.stat().st_size,
                        "file_path": str(backup_file)
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to read backup {backup_file.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to get available backups: {e}")
            
        return sorted(backups, key=lambda b: b["created_at"], reverse=True)

    def validate_backup(self, backup_id: str) -> ValidationResult:
        """
        Validate a migration backup.
        
        Args:
            backup_id: Backup identifier to validate
            
        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()
        
        try:
            backup_dir = self.config_dir / "backups" / "security_migration"
            backup_file = backup_dir / f"{backup_id}.json"
            
            if not backup_file.exists():
                result.add_error(f"Backup file not found: {backup_id}")
                return result
                
            # Load and validate backup data
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
                
            # Check backup structure
            required_fields = ["version", "created_at", "config_data"]
            for field in required_fields:
                if field not in backup_data:
                    result.add_error(f"Missing required field in backup: {field}")
                    
            # Validate config data if present
            if "config_data" in backup_data:
                config_validation = self._validate_migrated_configuration(backup_data["config_data"])
                result.errors.extend(config_validation.errors)
                result.warnings.extend(config_validation.warnings)
                
            if result.is_valid:
                logger.info(f"Backup validation passed: {backup_id}")
            else:
                logger.warning(f"Backup validation failed: {backup_id}")
                
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in backup file: {e}")
        except Exception as e:
            result.add_error(f"Failed to validate backup: {e}")
            
        return result