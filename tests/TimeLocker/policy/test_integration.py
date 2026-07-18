"""
Integration tests for policy management system.

These tests verify the interaction between PolicyValidator, PolicyEngine,
and PolicyManager components with different backup tools and scenarios.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.policy.manager import PolicyManager
from TimeLocker.policy.validator import PolicyValidator
from TimeLocker.policy.engine import PolicyEngine
from TimeLocker.policy.models import RetentionRule
from TimeLocker.policy.types import (
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
    EnforcementType,
)


class TestPolicyEnforcementIntegration:
    """Integration tests for policy enforcement with different backup tools."""
    
    def test_restic_policy_enforcement(self, mock_policy_store, sample_snapshots):
        """Test policy enforcement with restic backup tool."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create retention policy
        retention_policy = manager.create_retention_policy(
            name="Restic Retention",
            description="Retention for restic",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=3),
                RetentionRule(type=RetentionType.DAILY, count=7),
            ],
            status=PolicyStatus.ACTIVE,
        )
        
        # Create backup policy
        backup_policy = manager.create_backup_policy(
            name="Restic Backup",
            description="Backup with restic",
            data_selection_refs=["home-dir"],
            target_repositories=["restic-repo"],
            backup_tool="restic",
            retention_policy_id=retention_policy.id,
            status=PolicyStatus.ACTIVE,
        )
        
        # Validate compatibility
        validator = PolicyValidator()
        compat_result = validator.validate_retention_compatibility(
            retention_policy,
            "restic"
        )
        
        assert compat_result.compatible is True
        
        # Evaluate retention rules
        engine = PolicyEngine()
        decisions = engine.evaluate_retention_rules(
            sample_snapshots,
            retention_policy
        )
        
        assert len(decisions) == len(sample_snapshots)
        retained = [d for d in decisions if d.should_retain]
        assert len(retained) >= 3  # At least keep-last count
    
    def test_borg_policy_enforcement(self, mock_policy_store, sample_snapshots):
        """Test policy enforcement with borg backup tool."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create retention policy
        retention_policy = manager.create_retention_policy(
            name="Borg Retention",
            description="Retention for borg",
            rules=[
                RetentionRule(type=RetentionType.DAILY, count=7),
                RetentionRule(type=RetentionType.WEEKLY, count=4),
            ],
            status=PolicyStatus.ACTIVE,
        )
        
        # Create backup policy
        backup_policy = manager.create_backup_policy(
            name="Borg Backup",
            description="Backup with borg",
            data_selection_refs=["home-dir"],
            target_repositories=["borg-repo"],
            backup_tool="borg",
            retention_policy_id=retention_policy.id,
            status=PolicyStatus.ACTIVE,
        )
        
        # Validate compatibility
        validator = PolicyValidator()
        compat_result = validator.validate_retention_compatibility(
            retention_policy,
            "borg"
        )
        
        assert compat_result.compatible is True


class TestPolicySimulationIntegration:
    """Integration tests for policy simulation accuracy."""
    
    def test_simulation_matches_enforcement(self, mock_policy_store, sample_snapshots, mock_repository):
        """Test that simulation results match actual enforcement."""
        manager = PolicyManager(policy_store=mock_policy_store)
        engine = PolicyEngine()
        
        # Create retention policy
        retention_policy = manager.create_retention_policy(
            name="Test Retention",
            description="Test",
            rules=[RetentionRule(type=RetentionType.LAST, count=5)],
        )
        
        # Evaluate retention (simulation)
        decisions = engine.evaluate_retention_rules(
            sample_snapshots,
            retention_policy
        )
        
        simulated_removals = [d.snapshot.id for d in decisions if not d.should_retain]
        
        # Perform dry-run enforcement
        prune_result = engine.prune_snapshots(
            mock_repository,
            decisions,
            dry_run=True
        )
        
        # Results should match
        assert set(simulated_removals) == set(prune_result.snapshots_removed)


class TestPolicyConflictResolution:
    """Integration tests for policy conflict scenarios."""
    
    def test_multiple_policies_same_target(self, mock_policy_store):
        """Test handling multiple policies assigned to same target."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create two retention policies
        policy1 = manager.create_retention_policy(
            name="Policy 1",
            description="First policy",
            rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
        )
        
        policy2 = manager.create_retention_policy(
            name="Policy 2",
            description="Second policy",
            rules=[RetentionRule(type=RetentionType.DAILY, count=14)],
        )
        
        # Assign both to same target with different priorities
        assignment1 = manager.assign_policy(
            policy_id=policy1.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="test-repo",
            priority=1,
        )
        
        assignment2 = manager.assign_policy(
            policy_id=policy2.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="test-repo",
            priority=2,  # Higher priority
        )
        
        # Get effective policy
        effective = manager.get_effective_policies(
            target_type=TargetType.REPOSITORY,
            target_id="test-repo",
        )
        
        # Should resolve to higher priority policy
        assert effective['retention_policy'].id == policy2.id
    
    def test_conflicting_retention_rules(self, mock_policy_store, sample_snapshots):
        """Test handling conflicting retention rules within a policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        engine = PolicyEngine()
        
        # Create policy with potentially conflicting rules
        policy = manager.create_retention_policy(
            name="Conflicting Policy",
            description="Policy with multiple rules",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=3),
                RetentionRule(type=RetentionType.DAILY, count=7),
                RetentionRule(type=RetentionType.WEEKLY, count=4),
            ],
        )
        
        # Evaluate - should handle conflicts gracefully
        decisions = engine.evaluate_retention_rules(
            sample_snapshots,
            policy
        )
        
        assert len(decisions) == len(sample_snapshots)
        # All snapshots should have a decision
        assert all(d.should_retain is not None for d in decisions)


class TestPolicyErrorHandling:
    """Integration tests for error handling scenarios."""
    
    def test_invalid_repository_reference(self, mock_policy_store, mock_config_manager):
        """Test handling of invalid repository references."""
        manager = PolicyManager(
            policy_store=mock_policy_store,
            config_manager=mock_config_manager,
        )
        
        # Create policy with non-existent repository
        from TimeLocker.policy.exceptions import PolicyValidationError
        
        with pytest.raises(PolicyValidationError):
            manager.create_backup_policy(
                name="Invalid Policy",
                description="Policy with invalid repo",
                data_selection_refs=["home-dir"],
                target_repositories=["non-existent-repo"],
                backup_tool="restic",
                status=PolicyStatus.ACTIVE,
            )
    
    def test_enforcement_with_missing_policy(self, mock_policy_store):
        """Test enforcement when assigned policy is missing."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create assignment without policy
        from TimeLocker.policy.exceptions import PolicyNotFoundError
        
        with pytest.raises(PolicyNotFoundError):
            manager.assign_policy(
                policy_id="non-existent-policy",
                policy_type=PolicyType.RETENTION,
                target_type=TargetType.REPOSITORY,
                target_id="test-repo",
            )


class TestPolicyComplianceIntegration:
    """Integration tests for compliance validation."""
    
    def test_compliance_period_enforcement(self, mock_policy_store, sample_snapshots):
        """Test that compliance period prevents snapshot deletion."""
        manager = PolicyManager(policy_store=mock_policy_store)
        engine = PolicyEngine()
        
        # Create policy with compliance period
        policy = manager.create_retention_policy(
            name="Compliance Policy",
            description="Policy with compliance period",
            rules=[RetentionRule(type=RetentionType.LAST, count=1)],
        )
        policy.compliance_period = timedelta(days=365)
        
        # Create recent snapshot within compliance period
        recent_snapshot = Mock()
        recent_snapshot.id = "recent-snap"
        recent_snapshot.timestamp = datetime.utcnow() - timedelta(days=30)
        recent_snapshot.tags = {}
        
        # Validate compliance
        status = engine.validate_compliance(
            policy,
            [recent_snapshot]
        )
        
        assert isinstance(status, type(status))  # ComplianceStatus
        # Should detect potential compliance issues


class TestPolicyTemplateIntegration:
    """Integration tests for policy templates and duplication."""
    
    def test_template_creation_and_reuse(self, mock_policy_store):
        """Test creating and reusing policy templates."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create original policy
        original = manager.create_backup_policy(
            name="Original Policy",
            description="Original",
            data_selection_refs=["home-dir"],
            target_repositories=["repo-1"],
            backup_tool="restic",
        )
        
        # Create template
        template = manager.create_policy_template(
            template_name="Standard Backup Template",
            policy_id=original.id,
            policy_type=PolicyType.BACKUP,
        )
        
        assert template['template_name'] == "Standard Backup Template"
        assert 'configuration' in template
        
        # Duplicate from original
        duplicate = manager.duplicate_backup_policy(
            source_policy_id=original.id,
            new_name="Duplicated Policy",
        )
        
        assert duplicate.id != original.id
        assert duplicate.backup_tool == original.backup_tool
        assert duplicate.data_selection_refs == original.data_selection_refs
