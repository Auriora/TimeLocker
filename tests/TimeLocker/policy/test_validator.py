"""
Unit tests for PolicyValidator component.
"""

import pytest
from datetime import timedelta
from pathlib import Path

from src.TimeLocker.policy.validator import PolicyValidator, ValidationResult, CompatibilityResult
from src.TimeLocker.policy.models import (
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    ScheduleConfig,
    ComplianceRule,
)
from src.TimeLocker.policy.types import (
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
)
from src.TimeLocker.policy.exceptions import (
    PolicyValidationError,
    PolicyCompatibilityError,
)
from src.TimeLocker.selection_template_manager import SelectionTemplateManager
from src.TimeLocker.selection_models import SelectionTemplate, SelectionConfig


class TestPolicyValidator:
    """Tests for PolicyValidator class."""
    
    def test_validate_backup_policy_success(self, sample_backup_policy):
        """Test successful backup policy validation."""
        validator = PolicyValidator()
        result = validator.validate_backup_policy(sample_backup_policy)
        
        assert result.valid is True
        assert len([i for i in result.issues if i.severity == "error"]) == 0
    
    def test_validate_backup_policy_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        policy = BackupPolicy(
            id="",  # Missing ID
            name="",  # Missing name
            description="Test",
            data_selection_refs=[],  # Empty
            target_repositories=[],  # Empty
            backup_tool="",  # Missing
        )
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError) as exc_info:
            validator.validate_backup_policy(policy)
        
        assert "validation failed" in str(exc_info.value).lower()

    def test_validate_backup_policy_missing_selection_template_errors(self, sample_backup_policy, tmp_path):
        """Selection references must exist when a template manager is available."""
        template_manager = SelectionTemplateManager(storage_dir=tmp_path / "validator-templates")
        validator = PolicyValidator(selection_template_manager=template_manager)
        sample_backup_policy.data_selection_refs = ["unknown-template"]

        with pytest.raises(PolicyValidationError) as exc_info:
            validator.validate_backup_policy(sample_backup_policy)

        assert "data selection" in str(exc_info.value).lower()
    
    def test_validate_backup_policy_unsupported_tool(self, sample_backup_policy):
        """Test validation fails with unsupported backup tool."""
        sample_backup_policy.backup_tool = "unsupported-tool"
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError) as exc_info:
            validator.validate_backup_policy(sample_backup_policy)
        
        assert "unsupported backup tool" in str(exc_info.value).lower()
    
    def test_validate_retention_policy_success(self, sample_retention_policy):
        """Test successful retention policy validation."""
        validator = PolicyValidator()
        result = validator.validate_retention_policy(sample_retention_policy)
        
        assert result.valid is True
        assert len([i for i in result.issues if i.severity == "error"]) == 0
    
    def test_validate_retention_policy_no_rules(self):
        """Test validation fails when no retention rules specified."""
        policy = RetentionPolicy(
            id="test-policy",
            name="Test Policy",
            description="Test",
            rules=[],  # No rules
        )
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError) as exc_info:
            validator.validate_retention_policy(policy)
        
        assert "at least one retention rule" in str(exc_info.value).lower()
    
    def test_validate_retention_rule_negative_count(self):
        """Test validation fails with negative retention count."""
        with pytest.raises(ValueError) as exc_info:
            RetentionRule(
                type=RetentionType.DAILY,
                count=-1,  # Negative count
            )
        
        assert "non-negative" in str(exc_info.value).lower()
    
    def test_check_repository_compatibility_success(self, sample_backup_policy):
        """Test successful repository compatibility check."""
        validator = PolicyValidator()
        repo_config = {
            'uri': '/tmp/test-repo',
            'enabled': True,
            'read_only': False,
        }
        
        result = validator.check_repository_compatibility(sample_backup_policy, repo_config)
        
        assert result.compatible is True
        assert len(result.incompatibility_reasons) == 0
    
    def test_check_repository_compatibility_unsupported_tool(self, sample_backup_policy):
        """Test compatibility check fails with unsupported tool."""
        sample_backup_policy.backup_tool = "unsupported-tool"
        validator = PolicyValidator()
        repo_config = {'uri': '/tmp/test-repo', 'enabled': True, 'read_only': False}
        
        result = validator.check_repository_compatibility(sample_backup_policy, repo_config)
        assert result.compatible is False
        assert any("not supported" in reason.lower() for reason in result.incompatibility_reasons)
    
    def test_check_repository_compatibility_read_only(self, sample_backup_policy):
        """Test compatibility check fails with read-only repository."""
        validator = PolicyValidator()
        repo_config = {
            'uri': '/tmp/test-repo',
            'read_only': True,
        }
        
        with pytest.raises(PolicyCompatibilityError) as exc_info:
            validator.check_repository_compatibility(sample_backup_policy, repo_config)
        
        # Check that the incompatibility reasons contain read-only message
        assert exc_info.value.incompatibility_reasons
        assert any("read-only" in reason.lower() for reason in exc_info.value.incompatibility_reasons)
    
    def test_validate_policy_assignment_success(self, sample_policy_assignment):
        """Test successful policy assignment validation."""
        validator = PolicyValidator()
        result = validator.validate_policy_assignment(sample_policy_assignment)
        
        assert result.valid is True
    
    def test_validate_policy_assignment_missing_fields(self):
        """Test assignment validation fails with missing fields."""
        assignment = PolicyAssignment(
            id="",  # Missing
            policy_id="",  # Missing
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="",  # Missing
        )
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError):
            validator.validate_policy_assignment(assignment)
    
    def test_validate_retention_compatibility_success(self, sample_retention_policy):
        """Test retention policy compatibility with backup tool."""
        validator = PolicyValidator()
        result = validator.validate_retention_compatibility(
            sample_retention_policy,
            "restic"
        )
        
        assert result.compatible is True
    
    def test_validate_retention_compatibility_unsupported_type(self):
        """Test retention compatibility fails with unsupported retention type."""
        policy = RetentionPolicy(
            id="test-policy",
            name="Test Policy",
            description="Test",
            rules=[
                RetentionRule(type=RetentionType.DAILY, count=7),
            ],
        )
        
        validator = PolicyValidator()
        result = validator.validate_retention_compatibility(policy, "unsupported-tool")
        
        assert result.compatible is False
    
    def test_determine_repository_type_s3(self):
        """Test repository type determination for S3."""
        validator = PolicyValidator()
        
        assert validator._determine_repository_type("s3://bucket/path") == "s3"
        assert validator._determine_repository_type("s3:bucket/path") == "s3"
    
    def test_determine_repository_type_local(self):
        """Test repository type determination for local."""
        validator = PolicyValidator()
        
        assert validator._determine_repository_type("/tmp/repo") == "local"
        assert validator._determine_repository_type("file:///tmp/repo") == "local"
    
    def test_validate_schedule_invalid_cron(self, sample_backup_policy):
        """Test validation detects invalid cron expression."""
        sample_backup_policy.schedule = ScheduleConfig(
            cron_expression="invalid cron",
        )
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError):
            validator.validate_backup_policy(sample_backup_policy)
    
    def test_validate_compliance_requirements_negative_days(self, sample_backup_policy):
        """Test validation fails with negative compliance days."""
        sample_backup_policy.compliance_requirements = [
            ComplianceRule(
                rule_id="test-rule",
                description="Test",
                minimum_retention_days=-1,  # Negative
            )
        ]
        
        validator = PolicyValidator()
        with pytest.raises(PolicyValidationError):
            validator.validate_backup_policy(sample_backup_policy)


class TestValidationResult:
    """Tests for ValidationResult class."""
    
    def test_add_error(self):
        """Test adding an error to validation result."""
        result = ValidationResult(valid=True)
        result.add_error("field", "Error message", "ERROR_CODE")
        
        assert result.valid is False
        assert len(result.issues) == 1
        assert result.issues[0].severity == "error"
    
    def test_add_warning(self):
        """Test adding a warning to validation result."""
        result = ValidationResult(valid=True)
        result.add_warning("field", "Warning message", "WARNING_CODE")
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert len(result.issues) == 1
        assert result.issues[0].severity == "warning"
    
    def test_to_dict(self):
        """Test converting validation result to dictionary."""
        result = ValidationResult(valid=True)
        result.add_error("field", "Error", "CODE")
        
        data = result.to_dict()
        assert data['valid'] is False
        assert len(data['issues']) == 1


class TestCompatibilityResult:
    """Tests for CompatibilityResult class."""
    
    def test_add_incompatibility(self):
        """Test adding incompatibility reason."""
        result = CompatibilityResult(compatible=True)
        result.add_incompatibility("Incompatible reason")
        
        assert result.compatible is False
        assert len(result.incompatibility_reasons) == 1
    
    def test_add_warning(self):
        """Test adding warning to compatibility result."""
        result = CompatibilityResult(compatible=True)
        result.add_warning("Warning message")
        
        assert result.compatible is True  # Warnings don't affect compatibility
        assert len(result.warnings) == 1
    
    def test_to_dict(self):
        """Test converting compatibility result to dictionary."""
        result = CompatibilityResult(compatible=True)
        result.add_warning("Warning")
        
        data = result.to_dict()
        assert data['compatible'] is True
        assert len(data['warnings']) == 1
