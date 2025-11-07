"""
Policy Validator component for TimeLocker.

This module provides comprehensive validation for backup and retention policies,
including configuration validation, repository compatibility checking, and
policy assignment validation.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import timedelta

from .models import (
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
)
from .types import (
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
)
from .exceptions import (
    PolicyValidationError,
    PolicyCompatibilityError,
)


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    
    severity: str  # "error", "warning", "info"
    field: str
    message: str
    code: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'severity': self.severity,
            'field': self.field,
            'message': self.message,
            'code': self.code,
        }


@dataclass
class ValidationResult:
    """Result of policy validation."""
    
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        """Add an error to the validation result."""
        self.valid = False
        self.issues.append(ValidationIssue(
            severity="error",
            field=field,
            message=message,
            code=code
        ))
    
    def add_warning(self, field: str, message: str, code: str = "VALIDATION_WARNING"):
        """Add a warning to the validation result."""
        self.warnings.append(message)
        self.issues.append(ValidationIssue(
            severity="warning",
            field=field,
            message=message,
            code=code
        ))
    
    def add_info(self, field: str, message: str, code: str = "VALIDATION_INFO"):
        """Add an informational message to the validation result."""
        self.issues.append(ValidationIssue(
            severity="info",
            field=field,
            message=message,
            code=code
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'valid': self.valid,
            'issues': [issue.to_dict() for issue in self.issues],
            'warnings': self.warnings,
            'metadata': self.metadata,
        }


@dataclass
class CompatibilityResult:
    """Result of compatibility checking."""
    
    compatible: bool
    incompatibility_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_incompatibility(self, reason: str):
        """Add an incompatibility reason."""
        self.compatible = False
        self.incompatibility_reasons.append(reason)
    
    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'compatible': self.compatible,
            'incompatibility_reasons': self.incompatibility_reasons,
            'warnings': self.warnings,
            'metadata': self.metadata,
        }


class PolicyValidator:
    """
    Validates policy configurations and compatibility.
    
    This class provides comprehensive validation for backup and retention
    policies, including configuration validation, repository compatibility
    checking, and policy assignment validation.
    """
    
    # Supported backup tools and their capabilities
    SUPPORTED_BACKUP_TOOLS = {
        'restic': {
            'retention_types': {
                RetentionType.LAST,
                RetentionType.HOURLY,
                RetentionType.DAILY,
                RetentionType.WEEKLY,
                RetentionType.MONTHLY,
                RetentionType.YEARLY,
            },
            'repository_types': {'local', 's3', 'b2', 'sftp', 'rest'},
            'features': {'encryption', 'compression', 'deduplication', 'tags'},
        },
        'borg': {
            'retention_types': {
                RetentionType.LAST,
                RetentionType.HOURLY,
                RetentionType.DAILY,
                RetentionType.WEEKLY,
                RetentionType.MONTHLY,
                RetentionType.YEARLY,
            },
            'repository_types': {'local', 'ssh'},
            'features': {'encryption', 'compression', 'deduplication'},
        },
    }
    
    def __init__(self, repository_manager=None, config_manager=None):
        """
        Initialize the policy validator.
        
        Args:
            repository_manager: Optional repository manager for checking repository existence
            config_manager: Optional configuration manager for accessing system configuration
        """
        self.repository_manager = repository_manager
        self.config_manager = config_manager
    
    def validate_backup_policy(self, policy: BackupPolicy) -> ValidationResult:
        """
        Validate backup policy configuration and dependencies.
        
        Args:
            policy: Backup policy to validate
            
        Returns:
            ValidationResult with validation status and issues
            
        Raises:
            PolicyValidationError: If validation fails with critical errors
        """
        result = ValidationResult(valid=True)
        
        # Validate required fields
        self._validate_required_fields(policy, result)
        
        # Validate backup tool
        self._validate_backup_tool(policy, result)
        
        # Validate data selection references
        self._validate_data_selection_refs(policy, result)
        
        # Validate target repositories
        self._validate_target_repositories(policy, result)
        
        # Validate schedule configuration
        if policy.schedule:
            self._validate_schedule(policy.schedule, result)
        
        # Validate execution parameters
        self._validate_execution_params(policy, result)
        
        # Validate compliance requirements
        self._validate_compliance_requirements(policy, result)
        
        # Validate policy status
        self._validate_policy_status(policy, result)
        
        # If there are critical errors, raise exception
        if not result.valid:
            error_messages = [issue.message for issue in result.issues if issue.severity == "error"]
            raise PolicyValidationError(
                f"Backup policy validation failed: {'; '.join(error_messages)}",
                policy_id=policy.id,
                validation_errors=error_messages
            )
        
        return result
    
    def validate_retention_policy(self, policy: RetentionPolicy) -> ValidationResult:
        """
        Validate retention policy rules and constraints.
        
        Args:
            policy: Retention policy to validate
            
        Returns:
            ValidationResult with validation status and issues
            
        Raises:
            PolicyValidationError: If validation fails with critical errors
        """
        result = ValidationResult(valid=True)
        
        # Validate required fields
        if not policy.id:
            result.add_error("id", "Policy ID is required", "MISSING_ID")
        if not policy.name:
            result.add_error("name", "Policy name is required", "MISSING_NAME")
        
        # Validate retention rules
        if not policy.rules and not policy.tag_based_rules:
            result.add_error(
                "rules",
                "At least one retention rule or tag-based rule must be specified",
                "NO_RULES"
            )
        
        # Validate individual retention rules
        for idx, rule in enumerate(policy.rules):
            self._validate_retention_rule(rule, f"rules[{idx}]", result)
        
        # Validate tag-based rules
        for idx, tag_rule in enumerate(policy.tag_based_rules):
            self._validate_tag_based_rule(tag_rule, f"tag_based_rules[{idx}]", result)
        
        # Validate compliance period
        if policy.compliance_period:
            if policy.compliance_period.total_seconds() < 0:
                result.add_error(
                    "compliance_period",
                    "Compliance period must be non-negative",
                    "INVALID_COMPLIANCE_PERIOD"
                )
        
        # Validate priority
        if policy.priority < 0:
            result.add_error("priority", "Priority must be non-negative", "INVALID_PRIORITY")
        
        # Check for conflicting rules
        self._check_retention_rule_conflicts(policy, result)
        
        # If there are critical errors, raise exception
        if not result.valid:
            error_messages = [issue.message for issue in result.issues if issue.severity == "error"]
            raise PolicyValidationError(
                f"Retention policy validation failed: {'; '.join(error_messages)}",
                policy_id=policy.id,
                validation_errors=error_messages
            )
        
        return result
    
    def check_repository_compatibility(
        self,
        policy: BackupPolicy,
        repository_config: Dict[str, Any]
    ) -> CompatibilityResult:
        """
        Check if policy is compatible with target repository.
        
        Args:
            policy: Backup policy to check
            repository_config: Repository configuration dictionary
            
        Returns:
            CompatibilityResult with compatibility status and reasons
            
        Raises:
            PolicyCompatibilityError: If policy is incompatible with repository
        """
        result = CompatibilityResult(compatible=True)
        
        # Extract repository type from URI/location
        repo_uri = repository_config.get('uri') or repository_config.get('location', '')
        repo_type = self._determine_repository_type(repo_uri)
        
        # Check if backup tool supports this repository type
        tool_config = self.SUPPORTED_BACKUP_TOOLS.get(policy.backup_tool)
        if not tool_config:
            result.add_incompatibility(
                f"Backup tool '{policy.backup_tool}' is not supported"
            )
            return result
        
        if repo_type not in tool_config['repository_types']:
            result.add_incompatibility(
                f"Backup tool '{policy.backup_tool}' does not support "
                f"repository type '{repo_type}'"
            )
        
        # Check if repository is read-only
        if repository_config.get('read_only', False):
            result.add_incompatibility(
                "Cannot apply backup policy to read-only repository"
            )
        
        # Check if repository is enabled
        if not repository_config.get('enabled', True):
            result.add_warning(
                "Repository is currently disabled"
            )
        
        # Check encryption compatibility
        if 'encryption' in tool_config['features']:
            if not repository_config.get('password') and \
               not repository_config.get('password_file') and \
               not repository_config.get('password_command'):
                result.add_warning(
                    "Repository has no password configured; encryption may not be available"
                )
        
        # If incompatible, raise exception
        if not result.compatible:
            raise PolicyCompatibilityError(
                f"Policy '{policy.id}' is incompatible with repository",
                policy_id=policy.id,
                target_id=repository_config.get('name'),
                incompatibility_reasons=result.incompatibility_reasons
            )
        
        return result
    
    def validate_policy_assignment(
        self,
        assignment: PolicyAssignment,
        policy: Optional[BackupPolicy] = None
    ) -> ValidationResult:
        """
        Validate policy assignment to specific targets.
        
        Args:
            assignment: Policy assignment to validate
            policy: Optional policy object for additional validation
            
        Returns:
            ValidationResult with validation status and issues
            
        Raises:
            PolicyValidationError: If validation fails with critical errors
        """
        result = ValidationResult(valid=True)
        
        # Validate required fields
        if not assignment.id:
            result.add_error("id", "Assignment ID is required", "MISSING_ID")
        if not assignment.policy_id:
            result.add_error("policy_id", "Policy ID is required", "MISSING_POLICY_ID")
        if not assignment.target_id:
            result.add_error("target_id", "Target ID is required", "MISSING_TARGET_ID")
        
        # Validate priority
        if assignment.priority < 0:
            result.add_error("priority", "Priority must be non-negative", "INVALID_PRIORITY")
        
        # Validate target type compatibility with policy type
        if assignment.policy_type == PolicyType.BACKUP:
            if assignment.target_type not in {TargetType.REPOSITORY, TargetType.BACKUP_TARGET, TargetType.SYSTEM}:
                result.add_error(
                    "target_type",
                    f"Backup policies cannot be assigned to target type '{assignment.target_type.value}'",
                    "INVALID_TARGET_TYPE"
                )
        
        # If policy is provided, perform additional validation
        if policy:
            # Check if target repository is in policy's target list
            if assignment.target_type == TargetType.REPOSITORY:
                if assignment.target_id not in policy.target_repositories:
                    result.add_warning(
                        "target_id",
                        f"Target repository '{assignment.target_id}' is not in policy's target list",
                        "TARGET_NOT_IN_POLICY"
                    )
        
        # If there are critical errors, raise exception
        if not result.valid:
            error_messages = [issue.message for issue in result.issues if issue.severity == "error"]
            raise PolicyValidationError(
                f"Policy assignment validation failed: {'; '.join(error_messages)}",
                policy_id=assignment.policy_id,
                validation_errors=error_messages
            )
        
        return result
    
    def validate_retention_compatibility(
        self,
        retention_policy: RetentionPolicy,
        backup_tool: str
    ) -> CompatibilityResult:
        """
        Check if retention policy is compatible with backup tool.
        
        Args:
            retention_policy: Retention policy to check
            backup_tool: Backup tool identifier
            
        Returns:
            CompatibilityResult with compatibility status
        """
        result = CompatibilityResult(compatible=True)
        
        tool_config = self.SUPPORTED_BACKUP_TOOLS.get(backup_tool)
        if not tool_config:
            result.add_incompatibility(
                f"Backup tool '{backup_tool}' is not supported"
            )
            return result
        
        supported_types = tool_config['retention_types']
        
        # Check each retention rule
        for rule in retention_policy.rules:
            if rule.type not in supported_types:
                result.add_incompatibility(
                    f"Backup tool '{backup_tool}' does not support "
                    f"retention type '{rule.type.value}'"
                )
        
        # Check tag-based rules
        if retention_policy.tag_based_rules:
            if 'tags' not in tool_config.get('features', set()):
                result.add_incompatibility(
                    f"Backup tool '{backup_tool}' does not support tag-based retention"
                )
        
        return result
    
    # Private helper methods
    
    def _validate_required_fields(self, policy: BackupPolicy, result: ValidationResult):
        """Validate required fields in backup policy."""
        if not policy.id:
            result.add_error("id", "Policy ID is required", "MISSING_ID")
        if not policy.name:
            result.add_error("name", "Policy name is required", "MISSING_NAME")
        if not policy.backup_tool:
            result.add_error("backup_tool", "Backup tool is required", "MISSING_BACKUP_TOOL")
        if not policy.target_repositories:
            result.add_error(
                "target_repositories",
                "At least one target repository is required",
                "NO_TARGET_REPOSITORIES"
            )
        if not policy.data_selection_refs:
            result.add_error(
                "data_selection_refs",
                "At least one data selection reference is required",
                "NO_DATA_SELECTIONS"
            )
    
    def _validate_backup_tool(self, policy: BackupPolicy, result: ValidationResult):
        """Validate backup tool configuration."""
        if policy.backup_tool not in self.SUPPORTED_BACKUP_TOOLS:
            result.add_error(
                "backup_tool",
                f"Unsupported backup tool: '{policy.backup_tool}'. "
                f"Supported tools: {', '.join(self.SUPPORTED_BACKUP_TOOLS.keys())}",
                "UNSUPPORTED_BACKUP_TOOL"
            )
    
    def _validate_data_selection_refs(self, policy: BackupPolicy, result: ValidationResult):
        """Validate data selection references."""
        if not policy.data_selection_refs:
            return
        
        # Check for duplicate references
        if len(policy.data_selection_refs) != len(set(policy.data_selection_refs)):
            result.add_warning(
                "data_selection_refs",
                "Duplicate data selection references found",
                "DUPLICATE_DATA_SELECTIONS"
            )
        
        # If config manager is available, check if selections exist
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                available_targets = set(config.backup_targets.keys())
                
                for ref in policy.data_selection_refs:
                    if ref not in available_targets:
                        result.add_warning(
                            "data_selection_refs",
                            f"Data selection '{ref}' not found in configuration",
                            "DATA_SELECTION_NOT_FOUND"
                        )
            except Exception:
                # If we can't check, just add an info message
                result.add_info(
                    "data_selection_refs",
                    "Could not verify data selection references",
                    "VERIFICATION_SKIPPED"
                )
    
    def _validate_target_repositories(self, policy: BackupPolicy, result: ValidationResult):
        """Validate target repository references."""
        if not policy.target_repositories:
            return
        
        # Check for duplicate repositories
        if len(policy.target_repositories) != len(set(policy.target_repositories)):
            result.add_warning(
                "target_repositories",
                "Duplicate target repositories found",
                "DUPLICATE_REPOSITORIES"
            )
        
        # If config manager is available, check if repositories exist
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                available_repos = set(config.repositories.keys())
                
                for repo_id in policy.target_repositories:
                    if repo_id not in available_repos:
                        result.add_error(
                            "target_repositories",
                            f"Repository '{repo_id}' not found in configuration",
                            "REPOSITORY_NOT_FOUND"
                        )
            except Exception:
                # If we can't check, just add an info message
                result.add_info(
                    "target_repositories",
                    "Could not verify repository references",
                    "VERIFICATION_SKIPPED"
                )
    
    def _validate_schedule(self, schedule, result: ValidationResult):
        """Validate schedule configuration."""
        if schedule.cron_expression:
            # Basic cron expression validation
            parts = schedule.cron_expression.split()
            if len(parts) not in {5, 6}:
                result.add_error(
                    "schedule.cron_expression",
                    "Invalid cron expression format",
                    "INVALID_CRON"
                )
    
    def _validate_execution_params(self, policy: BackupPolicy, result: ValidationResult):
        """Validate execution parameters."""
        # Check for known problematic parameter combinations
        params = policy.execution_params
        
        if params.get('dry_run') and params.get('prune'):
            result.add_warning(
                "execution_params",
                "Dry run mode with prune enabled may not have expected effect",
                "CONFLICTING_PARAMS"
            )
    
    def _validate_compliance_requirements(self, policy: BackupPolicy, result: ValidationResult):
        """Validate compliance requirements."""
        for idx, req in enumerate(policy.compliance_requirements):
            if req.minimum_retention_days and req.minimum_retention_days < 0:
                result.add_error(
                    f"compliance_requirements[{idx}].minimum_retention_days",
                    "Minimum retention days must be non-negative",
                    "INVALID_RETENTION_DAYS"
                )
            
            if req.immutable_period_days and req.immutable_period_days < 0:
                result.add_error(
                    f"compliance_requirements[{idx}].immutable_period_days",
                    "Immutable period days must be non-negative",
                    "INVALID_IMMUTABLE_PERIOD"
                )
    
    def _validate_policy_status(self, policy: BackupPolicy, result: ValidationResult):
        """Validate policy status."""
        if policy.status == PolicyStatus.ACTIVE:
            # Active policies must have all required configuration
            if not policy.target_repositories:
                result.add_error(
                    "status",
                    "Active policy must have target repositories configured",
                    "INCOMPLETE_ACTIVE_POLICY"
                )
    
    def _validate_retention_rule(self, rule: RetentionRule, field_path: str, result: ValidationResult):
        """Validate individual retention rule."""
        if rule.count < 0:
            result.add_error(
                f"{field_path}.count",
                "Retention count must be non-negative",
                "INVALID_COUNT"
            )
        
        if rule.count == 0:
            result.add_warning(
                f"{field_path}.count",
                "Retention count of 0 means no snapshots will be kept for this rule",
                "ZERO_COUNT"
            )
        
        if rule.minimum_age and rule.minimum_age.total_seconds() < 0:
            result.add_error(
                f"{field_path}.minimum_age",
                "Minimum age must be non-negative",
                "INVALID_MINIMUM_AGE"
            )
    
    def _validate_tag_based_rule(self, rule, field_path: str, result: ValidationResult):
        """Validate tag-based retention rule."""
        if not rule.tag_filters:
            result.add_error(
                f"{field_path}.tag_filters",
                "Tag-based rule must have at least one tag filter",
                "NO_TAG_FILTERS"
            )
        
        if rule.retention_days is None and rule.keep_count is None:
            result.add_error(
                f"{field_path}",
                "Tag-based rule must specify either retention_days or keep_count",
                "NO_RETENTION_CRITERIA"
            )
        
        if rule.retention_days is not None and rule.retention_days < 0:
            result.add_error(
                f"{field_path}.retention_days",
                "Retention days must be non-negative",
                "INVALID_RETENTION_DAYS"
            )
        
        if rule.keep_count is not None and rule.keep_count < 0:
            result.add_error(
                f"{field_path}.keep_count",
                "Keep count must be non-negative",
                "INVALID_KEEP_COUNT"
            )
    
    def _check_retention_rule_conflicts(self, policy: RetentionPolicy, result: ValidationResult):
        """Check for conflicting retention rules."""
        # Check for duplicate retention types
        rule_types = [rule.type for rule in policy.rules]
        duplicates = [rt for rt in rule_types if rule_types.count(rt) > 1]
        
        if duplicates:
            result.add_warning(
                "rules",
                f"Duplicate retention types found: {', '.join(set(rt.value for rt in duplicates))}",
                "DUPLICATE_RETENTION_TYPES"
            )
    
    def _determine_repository_type(self, uri: str) -> str:
        """Determine repository type from URI."""
        if not uri:
            return 'unknown'
        
        uri_lower = uri.lower()
        if uri_lower.startswith('s3:') or uri_lower.startswith('s3://'):
            return 's3'
        elif uri_lower.startswith('b2:') or uri_lower.startswith('b2://'):
            return 'b2'
        elif uri_lower.startswith('sftp:') or uri_lower.startswith('sftp://'):
            return 'sftp'
        elif uri_lower.startswith('rest:') or uri_lower.startswith('rest://'):
            return 'rest'
        elif uri_lower.startswith('ssh:') or uri_lower.startswith('ssh://'):
            return 'ssh'
        elif uri_lower.startswith('file://') or uri_lower.startswith('/'):
            return 'local'
        else:
            return 'local'  # Default to local
