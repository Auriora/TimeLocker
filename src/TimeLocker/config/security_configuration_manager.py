"""
Security Configuration Manager for TimeLocker.

This module provides comprehensive security configuration management,
including validation, UI components, migration, and integration with
the existing configuration system.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .configuration_schema import SecurityConfig
from .configuration_validator import ValidationResult
from .configuration_defaults import ConfigurationDefaults
from ..interfaces.exceptions import ConfigurationError, InvalidConfigurationError

logger = logging.getLogger(__name__)


class SecurityConfigurationError(ConfigurationError):
    """Security configuration specific error"""
    pass


class SecurityValidationLevel(Enum):
    """Security validation levels"""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class SecurityValidationRule:
    """Security validation rule definition"""
    name: str
    description: str
    level: SecurityValidationLevel
    validator_function: str
    error_message: str
    recommendation: Optional[str] = None


@dataclass
class SecurityConfigurationStatus:
    """Security configuration status information"""
    is_valid: bool
    security_level: str
    issues_count: int
    warnings_count: int
    last_validated: datetime
    recommendations: List[str]
    compliance_score: float  # 0.0 to 1.0


class SecurityConfigurationManager:
    """
    Comprehensive security configuration management following SOLID principles.
    
    This class handles security configuration validation, UI components,
    migration, and integration with the existing configuration system.
    """

    def __init__(self, config_module: Optional['ConfigurationModule'] = None):
        """
        Initialize security configuration manager.
        
        Args:
            config_module: Optional configuration module instance
        """
        self.config_module = config_module
        self._validation_rules = self._initialize_validation_rules()
        self._ui_components = {}
        
    def _initialize_validation_rules(self) -> Dict[str, SecurityValidationRule]:
        """Initialize security validation rules"""
        return {
            "encryption_enabled": SecurityValidationRule(
                name="encryption_enabled",
                description="Encryption must be enabled for security",
                level=SecurityValidationLevel.STRICT,
                validator_function="_validate_encryption_enabled",
                error_message="Encryption is disabled - this is a critical security risk",
                recommendation="Enable encryption to protect backup data"
            ),
            "audit_logging": SecurityValidationRule(
                name="audit_logging",
                description="Audit logging should be enabled for security monitoring",
                level=SecurityValidationLevel.MODERATE,
                validator_function="_validate_audit_logging",
                error_message="Audit logging is disabled - reduces security monitoring capability",
                recommendation="Enable audit logging to track security events"
            ),
            "credential_timeout": SecurityValidationRule(
                name="credential_timeout",
                description="Credential timeout should be reasonable for security",
                level=SecurityValidationLevel.MODERATE,
                validator_function="_validate_credential_timeout",
                error_message="Credential timeout is not within recommended range",
                recommendation="Set credential timeout between 5 minutes and 4 hours"
            ),
            "max_failed_attempts": SecurityValidationRule(
                name="max_failed_attempts",
                description="Maximum failed attempts should prevent brute force attacks",
                level=SecurityValidationLevel.MODERATE,
                validator_function="_validate_max_failed_attempts",
                error_message="Maximum failed attempts setting is not secure",
                recommendation="Set max failed attempts between 3 and 10"
            ),
            "lockout_duration": SecurityValidationRule(
                name="lockout_duration",
                description="Lockout duration should balance security and usability",
                level=SecurityValidationLevel.MODERATE,
                validator_function="_validate_lockout_duration",
                error_message="Lockout duration is not within recommended range",
                recommendation="Set lockout duration between 1 minute and 30 minutes"
            ),
            "password_strength": SecurityValidationRule(
                name="password_strength",
                description="Password strength checking should be enabled",
                level=SecurityValidationLevel.MODERATE,
                validator_function="_validate_password_strength",
                error_message="Password strength checking is disabled",
                recommendation="Enable password strength checking for better security"
            )
        }

    def validate_security_config(self, security_config: Union[SecurityConfig, Dict[str, Any]], 
                                validation_level: SecurityValidationLevel = SecurityValidationLevel.MODERATE) -> ValidationResult:
        """
        Validate security configuration with comprehensive checks.
        
        Args:
            security_config: Security configuration to validate
            validation_level: Validation strictness level
            
        Returns:
            ValidationResult: Detailed validation results
        """
        result = ValidationResult()
        
        try:
            # Convert dict to SecurityConfig if needed
            if isinstance(security_config, dict):
                config = SecurityConfig(**security_config)
            else:
                config = security_config
                
            # Run validation rules based on level
            for rule_name, rule in self._validation_rules.items():
                if rule.level.value in [validation_level.value, "strict"] or validation_level == SecurityValidationLevel.PERMISSIVE:
                    validator_method = getattr(self, rule.validator_function, None)
                    if validator_method:
                        try:
                            is_valid, message = validator_method(config)
                            if not is_valid:
                                if rule.level == SecurityValidationLevel.STRICT:
                                    result.add_error(f"{rule.error_message}: {message}")
                                else:
                                    result.add_warning(f"{rule.error_message}: {message}")
                                    
                                if rule.recommendation:
                                    result.add_warning(f"Recommendation: {rule.recommendation}")
                        except Exception as e:
                            logger.error(f"Error running validation rule {rule_name}: {e}")
                            result.add_warning(f"Could not validate {rule_name}: {e}")
                            
        except Exception as e:
            result.add_error(f"Security configuration validation failed: {e}")
            
        return result

    def _validate_encryption_enabled(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate encryption is enabled"""
        if not config.encryption_enabled:
            return False, "Encryption is disabled"
        return True, "Encryption is properly enabled"

    def _validate_audit_logging(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate audit logging is enabled"""
        if not config.audit_logging:
            return False, "Audit logging is disabled"
        return True, "Audit logging is properly enabled"

    def _validate_credential_timeout(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate credential timeout is within reasonable range"""
        timeout = config.credential_timeout
        if timeout < 300:  # Less than 5 minutes
            return False, f"Timeout ({timeout}s) is too short, minimum 300s recommended"
        elif timeout > 14400:  # More than 4 hours
            return False, f"Timeout ({timeout}s) is too long, maximum 14400s recommended"
        return True, f"Credential timeout ({timeout}s) is within recommended range"

    def _validate_max_failed_attempts(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate max failed attempts setting"""
        attempts = config.max_failed_attempts
        if attempts <= 0:
            return False, "Max failed attempts must be greater than 0"
        elif attempts > 10:
            return False, f"Max failed attempts ({attempts}) is too high, consider reducing"
        return True, f"Max failed attempts ({attempts}) is within recommended range"

    def _validate_lockout_duration(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate lockout duration setting"""
        duration = config.lockout_duration
        if duration < 60:  # Less than 1 minute
            return False, f"Lockout duration ({duration}s) is too short"
        elif duration > 1800:  # More than 30 minutes
            return False, f"Lockout duration ({duration}s) is too long"
        return True, f"Lockout duration ({duration}s) is within recommended range"

    def _validate_password_strength(self, config: SecurityConfig) -> Tuple[bool, str]:
        """Validate password strength checking is enabled"""
        if not config.password_strength_check:
            return False, "Password strength checking is disabled"
        return True, "Password strength checking is enabled"

    def get_security_configuration_status(self) -> SecurityConfigurationStatus:
        """
        Get comprehensive security configuration status.
        
        Returns:
            SecurityConfigurationStatus: Current security status
        """
        try:
            if not self.config_module:
                # Get config from default location if no module provided
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            config = self.config_module.get_config()
            security_config = config.security
            
            # Validate configuration
            validation_result = self.validate_security_config(security_config)
            
            # Calculate compliance score
            total_rules = len(self._validation_rules)
            passed_rules = total_rules - len(validation_result.errors)
            compliance_score = passed_rules / total_rules if total_rules > 0 else 0.0
            
            # Determine security level
            if compliance_score >= 0.9:
                security_level = "high"
            elif compliance_score >= 0.7:
                security_level = "medium"
            else:
                security_level = "low"
                
            # Generate recommendations
            recommendations = []
            if not security_config.encryption_enabled:
                recommendations.append("Enable encryption for data protection")
            if not security_config.audit_logging:
                recommendations.append("Enable audit logging for security monitoring")
            if security_config.credential_timeout < 900:
                recommendations.append("Consider increasing credential timeout for better security")
                
            return SecurityConfigurationStatus(
                is_valid=validation_result.is_valid,
                security_level=security_level,
                issues_count=len(validation_result.errors),
                warnings_count=len(validation_result.warnings),
                last_validated=datetime.now(),
                recommendations=recommendations,
                compliance_score=compliance_score
            )
            
        except Exception as e:
            logger.error(f"Failed to get security configuration status: {e}")
            return SecurityConfigurationStatus(
                is_valid=False,
                security_level="unknown",
                issues_count=1,
                warnings_count=0,
                last_validated=datetime.now(),
                recommendations=["Fix configuration errors"],
                compliance_score=0.0
            )

    def update_security_configuration(self, updates: Dict[str, Any], 
                                    validate: bool = True) -> ValidationResult:
        """
        Update security configuration with validation.
        
        Args:
            updates: Dictionary of security configuration updates
            validate: Whether to validate before applying updates
            
        Returns:
            ValidationResult: Validation results
        """
        try:
            if not self.config_module:
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            # Get current configuration
            config = self.config_module.get_config()
            current_security = config.security
            
            # Create updated security config
            security_dict = asdict(current_security)
            security_dict.update(updates)
            updated_security = SecurityConfig(**security_dict)
            
            # Validate if requested
            validation_result = ValidationResult()
            if validate:
                validation_result = self.validate_security_config(updated_security)
                if not validation_result.is_valid:
                    return validation_result
                    
            # Apply updates
            config.security = updated_security
            self.config_module.save_config(config)
            
            logger.info(f"Security configuration updated: {list(updates.keys())}")
            return validation_result
            
        except Exception as e:
            error_msg = f"Failed to update security configuration: {e}"
            logger.error(error_msg)
            result = ValidationResult()
            result.add_error(error_msg)
            return result

    def reset_security_configuration(self) -> ValidationResult:
        """
        Reset security configuration to defaults.
        
        Returns:
            ValidationResult: Reset operation results
        """
        try:
            if not self.config_module:
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            # Get default security configuration
            default_security = ConfigurationDefaults.get_security_defaults()
            
            # Update configuration
            config = self.config_module.get_config()
            config.security = default_security
            self.config_module.save_config(config)
            
            logger.info("Security configuration reset to defaults")
            
            # Validate the reset configuration
            return self.validate_security_config(default_security)
            
        except Exception as e:
            error_msg = f"Failed to reset security configuration: {e}"
            logger.error(error_msg)
            result = ValidationResult()
            result.add_error(error_msg)
            return result

    def migrate_security_configuration(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate security configuration from older versions.
        
        Args:
            old_config: Old configuration format
            
        Returns:
            Dict: Migrated security configuration
        """
        try:
            migrated = {}
            
            # Map old field names to new ones
            field_mapping = {
                "enable_encryption": "encryption_enabled",
                "enable_audit_log": "audit_logging",
                "session_timeout": "credential_timeout",
                "max_login_attempts": "max_failed_attempts",
                "lockout_time": "lockout_duration",
                "check_password_strength": "password_strength_check",
                "require_confirmation": "require_password_confirmation"
            }
            
            # Apply field mappings
            for old_field, new_field in field_mapping.items():
                if old_field in old_config:
                    migrated[new_field] = old_config[old_field]
                    
            # Handle special cases
            if "timeout" in old_config and "credential_timeout" not in migrated:
                # Convert minutes to seconds if needed
                timeout_value = old_config["timeout"]
                if isinstance(timeout_value, int) and timeout_value < 1000:
                    # Assume it's in minutes, convert to seconds
                    migrated["credential_timeout"] = timeout_value * 60
                else:
                    migrated["credential_timeout"] = timeout_value
                    
            # Set defaults for missing fields
            defaults = asdict(ConfigurationDefaults.get_security_defaults())
            for field, default_value in defaults.items():
                if field not in migrated:
                    migrated[field] = default_value
                    
            logger.info(f"Migrated security configuration: {len(migrated)} fields")
            return migrated
            
        except Exception as e:
            logger.error(f"Failed to migrate security configuration: {e}")
            # Return defaults on migration failure
            return asdict(ConfigurationDefaults.get_security_defaults())

    def export_security_configuration(self, output_path: Path, 
                                    include_sensitive: bool = False) -> bool:
        """
        Export security configuration to file.
        
        Args:
            output_path: Path to export file
            include_sensitive: Whether to include sensitive settings
            
        Returns:
            bool: True if export successful
        """
        try:
            if not self.config_module:
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            config = self.config_module.get_config()
            security_config = asdict(config.security)
            
            # Remove sensitive fields if requested
            if not include_sensitive:
                sensitive_fields = ["credential_timeout", "max_failed_attempts", "lockout_duration"]
                for field in sensitive_fields:
                    security_config.pop(field, None)
                    
            # Add metadata
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
                "security_configuration": security_config
            }
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            logger.info(f"Security configuration exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export security configuration: {e}")
            return False

    def import_security_configuration(self, import_path: Path, 
                                    validate: bool = True) -> ValidationResult:
        """
        Import security configuration from file.
        
        Args:
            import_path: Path to import file
            validate: Whether to validate imported configuration
            
        Returns:
            ValidationResult: Import operation results
        """
        result = ValidationResult()
        
        try:
            if not import_path.exists():
                result.add_error(f"Import file does not exist: {import_path}")
                return result
                
            # Read import file
            with open(import_path, 'r') as f:
                import_data = json.load(f)
                
            # Extract security configuration
            if "security_configuration" in import_data:
                security_config = import_data["security_configuration"]
            else:
                # Assume the entire file is security configuration
                security_config = import_data
                
            # Validate if requested
            if validate:
                validation_result = self.validate_security_config(security_config)
                if not validation_result.is_valid:
                    result.errors.extend(validation_result.errors)
                    result.warnings.extend(validation_result.warnings)
                    return result
                    
            # Apply configuration
            update_result = self.update_security_configuration(security_config, validate=False)
            result.errors.extend(update_result.errors)
            result.warnings.extend(update_result.warnings)
            
            if result.is_valid:
                logger.info(f"Security configuration imported from {import_path}")
            
            return result
            
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in import file: {e}")
            return result
        except Exception as e:
            result.add_error(f"Failed to import security configuration: {e}")
            return result

    def get_security_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get security configuration recommendations.
        
        Returns:
            List: Security recommendations with priorities
        """
        try:
            if not self.config_module:
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            config = self.config_module.get_config()
            security_config = config.security
            
            recommendations = []
            
            # Check encryption
            if not security_config.encryption_enabled:
                recommendations.append({
                    "priority": "critical",
                    "category": "encryption",
                    "title": "Enable Encryption",
                    "description": "Backup data encryption is currently disabled",
                    "action": "Enable encryption to protect backup data from unauthorized access",
                    "setting": "encryption_enabled",
                    "recommended_value": True
                })
                
            # Check audit logging
            if not security_config.audit_logging:
                recommendations.append({
                    "priority": "high",
                    "category": "monitoring",
                    "title": "Enable Audit Logging",
                    "description": "Security event logging is currently disabled",
                    "action": "Enable audit logging to monitor security events and troubleshoot issues",
                    "setting": "audit_logging",
                    "recommended_value": True
                })
                
            # Check credential timeout
            if security_config.credential_timeout < 900:  # Less than 15 minutes
                recommendations.append({
                    "priority": "medium",
                    "category": "authentication",
                    "title": "Increase Credential Timeout",
                    "description": f"Current timeout ({security_config.credential_timeout}s) is quite short",
                    "action": "Consider increasing credential timeout to reduce frequent re-authentication",
                    "setting": "credential_timeout",
                    "recommended_value": 1800  # 30 minutes
                })
                
            # Check password strength
            if not security_config.password_strength_check:
                recommendations.append({
                    "priority": "medium",
                    "category": "authentication",
                    "title": "Enable Password Strength Checking",
                    "description": "Password strength validation is currently disabled",
                    "action": "Enable password strength checking to ensure strong passwords",
                    "setting": "password_strength_check",
                    "recommended_value": True
                })
                
            # Check max failed attempts
            if security_config.max_failed_attempts > 5:
                recommendations.append({
                    "priority": "low",
                    "category": "authentication",
                    "title": "Reduce Max Failed Attempts",
                    "description": f"Current setting ({security_config.max_failed_attempts}) is quite high",
                    "action": "Consider reducing max failed attempts to improve security",
                    "setting": "max_failed_attempts",
                    "recommended_value": 3
                })
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get security recommendations: {e}")
            return []

    def apply_security_recommendations(self, recommendation_ids: List[str]) -> ValidationResult:
        """
        Apply selected security recommendations.
        
        Args:
            recommendation_ids: List of recommendation IDs to apply
            
        Returns:
            ValidationResult: Application results
        """
        result = ValidationResult()
        
        try:
            recommendations = self.get_security_recommendations()
            recommendations_by_setting = {rec["setting"]: rec for rec in recommendations}
            
            updates = {}
            for rec_id in recommendation_ids:
                if rec_id in recommendations_by_setting:
                    rec = recommendations_by_setting[rec_id]
                    updates[rec["setting"]] = rec["recommended_value"]
                    
            if updates:
                update_result = self.update_security_configuration(updates)
                result.errors.extend(update_result.errors)
                result.warnings.extend(update_result.warnings)
                
                if result.is_valid:
                    logger.info(f"Applied {len(updates)} security recommendations")
                    
            return result
            
        except Exception as e:
            result.add_error(f"Failed to apply security recommendations: {e}")
            return result

    def get_security_configuration_summary(self) -> Dict[str, Any]:
        """
        Get security configuration summary for display.
        
        Returns:
            Dict: Security configuration summary
        """
        try:
            if not self.config_module:
                from . import ConfigurationModule
                self.config_module = ConfigurationModule()
                
            config = self.config_module.get_config()
            security_config = config.security
            status = self.get_security_configuration_status()
            
            return {
                "encryption_enabled": security_config.encryption_enabled,
                "audit_logging": security_config.audit_logging,
                "credential_timeout_minutes": security_config.credential_timeout // 60,
                "max_failed_attempts": security_config.max_failed_attempts,
                "lockout_duration_minutes": security_config.lockout_duration // 60,
                "password_strength_check": security_config.password_strength_check,
                "require_password_confirmation": security_config.require_password_confirmation,
                "security_level": status.security_level,
                "compliance_score": status.compliance_score,
                "issues_count": status.issues_count,
                "warnings_count": status.warnings_count,
                "recommendations_count": len(status.recommendations)
            }
            
        except Exception as e:
            logger.error(f"Failed to get security configuration summary: {e}")
            return {
                "error": str(e),
                "security_level": "unknown",
                "compliance_score": 0.0
            }