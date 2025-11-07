"""
Unit tests for PolicyManager component.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.TimeLocker.policy.manager import PolicyManager
from src.TimeLocker.policy.models import (
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
)
from src.TimeLocker.policy.types import (
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
)
from src.TimeLocker.policy.exceptions import (
    PolicyNotFoundError,
    PolicyError,
    PolicyValidationError,
)


class TestPolicyManager:
    """Tests for PolicyManager class."""
    
    def test_initialization(self, mock_policy_store):
        """Test PolicyManager initialization."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        assert manager.policy_store is not None
        assert manager.validator is not None
        assert manager.engine is not None
    
    def test_create_backup_policy(self, mock_policy_store):
        """Test creating a backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        policy = manager.create_backup_policy(
            name="Test Backup Policy",
            description="Test description",
            data_selection_refs=["home-dir"],
            target_repositories=["local-repo"],
            backup_tool="restic",
        )
        
        assert policy is not None
        assert policy.name == "Test Backup Policy"
        assert policy.backup_tool == "restic"
        assert policy.retention_policy_id == "default-retention"  # Default applied
        mock_policy_store.save_backup_policy.assert_called_once()
    
    def test_create_backup_policy_with_retention(self, mock_policy_store):
        """Test creating backup policy with specific retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        policy = manager.create_backup_policy(
            name="Test Policy",
            description="Test",
            data_selection_refs=["home-dir"],
            target_repositories=["local-repo"],
            backup_tool="restic",
            retention_policy_id="custom-retention",
        )
        
        assert policy.retention_policy_id == "custom-retention"
    
    def test_get_backup_policy(self, mock_policy_store, sample_backup_policy):
        """Test retrieving a backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        policy = manager.get_backup_policy(sample_backup_policy.id)
        
        assert policy == sample_backup_policy
    
    def test_get_backup_policy_not_found(self, mock_policy_store):
        """Test retrieving non-existent backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        with pytest.raises(PolicyNotFoundError):
            manager.get_backup_policy("non-existent-id")
    
    def test_update_backup_policy(self, mock_policy_store, sample_backup_policy):
        """Test updating a backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        updated = manager.update_backup_policy(
            sample_backup_policy.id,
            name="Updated Name",
        )
        
        assert updated.name == "Updated Name"
        mock_policy_store.save_backup_policy.assert_called()
    
    def test_delete_backup_policy(self, mock_policy_store, sample_backup_policy):
        """Test deleting a backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        result = manager.delete_backup_policy(sample_backup_policy.id)
        
        assert result is True
        assert sample_backup_policy.id not in manager._backup_policies
        mock_policy_store.delete_backup_policy.assert_called_once()
    
    def test_delete_backup_policy_with_assignments(self, mock_policy_store, sample_backup_policy, sample_policy_assignment):
        """Test deleting policy with active assignments fails without force."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        sample_policy_assignment.policy_id = sample_backup_policy.id
        sample_policy_assignment.policy_type = PolicyType.BACKUP
        manager._policy_assignments[sample_policy_assignment.id] = sample_policy_assignment
        
        with pytest.raises(PolicyError) as exc_info:
            manager.delete_backup_policy(sample_backup_policy.id, force=False)
        
        assert "active assignments" in str(exc_info.value).lower()
    
    def test_list_backup_policies(self, mock_policy_store, sample_backup_policy):
        """Test listing backup policies."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        policies = manager.list_backup_policies()
        
        assert len(policies) >= 1
        assert sample_backup_policy in policies
    
    def test_list_backup_policies_filtered_by_status(self, mock_policy_store, sample_backup_policy):
        """Test listing backup policies filtered by status."""
        manager = PolicyManager(policy_store=mock_policy_store)
        sample_backup_policy.status = PolicyStatus.ACTIVE
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        policies = manager.list_backup_policies(status=PolicyStatus.ACTIVE)
        
        assert len(policies) >= 1
        assert all(p.status == PolicyStatus.ACTIVE for p in policies)
    
    def test_create_retention_policy(self, mock_policy_store):
        """Test creating a retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        rules = [
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
        ]
        
        # Reset mock to ignore default policy creation
        mock_policy_store.save_retention_policy.reset_mock()
        
        policy = manager.create_retention_policy(
            name="Test Retention Policy",
            description="Test description",
            rules=rules,
        )
        
        assert policy is not None
        assert policy.name == "Test Retention Policy"
        assert len(policy.rules) == 2
        mock_policy_store.save_retention_policy.assert_called_once()
    
    def test_get_retention_policy(self, mock_policy_store, sample_retention_policy):
        """Test retrieving a retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._retention_policies[sample_retention_policy.id] = sample_retention_policy
        
        policy = manager.get_retention_policy(sample_retention_policy.id)
        
        assert policy == sample_retention_policy
    
    def test_delete_retention_policy(self, mock_policy_store, sample_retention_policy):
        """Test deleting a retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._retention_policies[sample_retention_policy.id] = sample_retention_policy
        
        result = manager.delete_retention_policy(sample_retention_policy.id)
        
        assert result is True
        assert sample_retention_policy.id not in manager._retention_policies
    
    def test_delete_default_retention_policy_fails(self, mock_policy_store):
        """Test that default retention policy cannot be deleted."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        with pytest.raises(PolicyError) as exc_info:
            manager.delete_retention_policy("default-retention")
        
        assert "default" in str(exc_info.value).lower()
    
    def test_assign_policy(self, mock_policy_store, sample_retention_policy):
        """Test assigning a policy to a target."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._retention_policies[sample_retention_policy.id] = sample_retention_policy
        
        assignment = manager.assign_policy(
            policy_id=sample_retention_policy.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        assert assignment is not None
        assert assignment.policy_id == sample_retention_policy.id
        assert assignment.target_id == "local-repo"
        mock_policy_store.save_assignment.assert_called_once()
    
    def test_unassign_policy(self, mock_policy_store, sample_policy_assignment):
        """Test unassigning a policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._policy_assignments[sample_policy_assignment.id] = sample_policy_assignment
        
        result = manager.unassign_policy(sample_policy_assignment.id)
        
        assert result is True
        assert sample_policy_assignment.id not in manager._policy_assignments
        mock_policy_store.delete_assignment.assert_called_once()
    
    def test_get_policy_assignments(self, mock_policy_store, sample_policy_assignment):
        """Test retrieving policy assignments."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._policy_assignments[sample_policy_assignment.id] = sample_policy_assignment
        
        assignments = manager.get_policy_assignments(
            policy_id=sample_policy_assignment.policy_id
        )
        
        assert len(assignments) == 1
        assert assignments[0] == sample_policy_assignment
    
    def test_get_policy_assignments_filtered_by_target(self, mock_policy_store, sample_policy_assignment):
        """Test retrieving assignments filtered by target."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._policy_assignments[sample_policy_assignment.id] = sample_policy_assignment
        
        assignments = manager.get_policy_assignments(
            target_id=sample_policy_assignment.target_id
        )
        
        assert len(assignments) == 1
    
    def test_duplicate_backup_policy(self, mock_policy_store, sample_backup_policy):
        """Test duplicating a backup policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        new_policy = manager.duplicate_backup_policy(
            source_policy_id=sample_backup_policy.id,
            new_name="Duplicated Policy",
        )
        
        assert new_policy.id != sample_backup_policy.id
        assert new_policy.name == "Duplicated Policy"
        assert new_policy.backup_tool == sample_backup_policy.backup_tool
    
    def test_duplicate_retention_policy(self, mock_policy_store, sample_retention_policy):
        """Test duplicating a retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._retention_policies[sample_retention_policy.id] = sample_retention_policy
        
        new_policy = manager.duplicate_retention_policy(
            source_policy_id=sample_retention_policy.id,
            new_name="Duplicated Retention",
        )
        
        assert new_policy.id != sample_retention_policy.id
        assert new_policy.name == "Duplicated Retention"
        assert len(new_policy.rules) == len(sample_retention_policy.rules)
    
    def test_create_policy_template(self, mock_policy_store, sample_backup_policy):
        """Test creating a policy template."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        
        template = manager.create_policy_template(
            template_name="Test Template",
            policy_id=sample_backup_policy.id,
            policy_type=PolicyType.BACKUP,
        )
        
        assert template is not None
        assert template['template_name'] == "Test Template"
        assert template['policy_type'] == PolicyType.BACKUP.value
        assert 'configuration' in template
    
    def test_apply_default_retention_policy(self, mock_policy_store):
        """Test applying default retention policy."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        assignment = manager.apply_default_retention_policy(
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        assert assignment is not None
        assert assignment.policy_id == "default-retention"
        assert assignment.target_id == "local-repo"
    
    def test_get_effective_policies(self, mock_policy_store, sample_backup_policy, sample_retention_policy):
        """Test getting effective policies for a target."""
        manager = PolicyManager(policy_store=mock_policy_store)
        manager._backup_policies[sample_backup_policy.id] = sample_backup_policy
        manager._retention_policies[sample_retention_policy.id] = sample_retention_policy
        
        # Create assignments
        backup_assignment = manager.assign_policy(
            policy_id=sample_backup_policy.id,
            policy_type=PolicyType.BACKUP,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        retention_assignment = manager.assign_policy(
            policy_id=sample_retention_policy.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        effective = manager.get_effective_policies(
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        assert effective['backup_policy'] == sample_backup_policy
        assert effective['retention_policy'] == sample_retention_policy
    
    def test_get_effective_policies_priority_resolution(self, mock_policy_store, sample_retention_policy):
        """Test effective policy resolution with multiple assignments."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create two retention policies
        policy1 = sample_retention_policy
        policy2 = RetentionPolicy(
            id="policy-2",
            name="Policy 2",
            description="Test",
            rules=[RetentionRule(type=RetentionType.DAILY, count=14)],
        )
        
        manager._retention_policies[policy1.id] = policy1
        manager._retention_policies[policy2.id] = policy2
        
        # Assign both with different priorities
        manager.assign_policy(
            policy_id=policy1.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
            priority=1,
        )
        manager.assign_policy(
            policy_id=policy2.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
            priority=2,  # Higher priority
        )
        
        effective = manager.get_effective_policies(
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        # Should get the higher priority policy
        assert effective['retention_policy'].id == policy2.id


class TestPolicyManagerIntegration:
    """Integration tests for PolicyManager."""
    
    def test_full_policy_lifecycle(self, mock_policy_store):
        """Test complete policy lifecycle: create, assign, update, delete."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create retention policy
        retention_policy = manager.create_retention_policy(
            name="Test Retention",
            description="Test",
            rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
        )
        
        # Create backup policy
        backup_policy = manager.create_backup_policy(
            name="Test Backup",
            description="Test",
            data_selection_refs=["home-dir"],
            target_repositories=["local-repo"],
            backup_tool="restic",
            retention_policy_id=retention_policy.id,
        )
        
        # Assign policy
        assignment = manager.assign_policy(
            policy_id=backup_policy.id,
            policy_type=PolicyType.BACKUP,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
        )
        
        # Update policy
        updated = manager.update_backup_policy(
            backup_policy.id,
            name="Updated Backup",
        )
        assert updated.name == "Updated Backup"
        
        # Unassign
        manager.unassign_policy(assignment.id)
        
        # Delete policies
        manager.delete_backup_policy(backup_policy.id)
        manager.delete_retention_policy(retention_policy.id)
        
        # Verify deletion
        with pytest.raises(PolicyNotFoundError):
            manager.get_backup_policy(backup_policy.id)
