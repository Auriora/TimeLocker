"""
Unit tests for PolicyEngine component.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.TimeLocker.policy.engine import PolicyEngine, RetentionDecision, PruneResult
from src.TimeLocker.policy.models import (
    RetentionPolicy,
    RetentionRule,
    EnforcementRecord,
    ComplianceStatus,
)
from src.TimeLocker.policy.types import (
    RetentionType,
    EnforcementType,
)
from src.TimeLocker.policy.exceptions import (
    PolicyEnforcementError,
)
from src.TimeLocker.backup_snapshot import BackupSnapshot


class TestPolicyEngine:
    """Tests for PolicyEngine class."""
    
    def test_evaluate_retention_rules_empty_snapshots(self, sample_retention_policy):
        """Test evaluation with no snapshots."""
        engine = PolicyEngine()
        decisions = engine.evaluate_retention_rules([], sample_retention_policy)
        
        assert len(decisions) == 0
    
    def test_evaluate_retention_rules_keep_last(self, sample_snapshots):
        """Test retention evaluation with keep-last rule."""
        policy = RetentionPolicy(
            id="test-policy",
            name="Test Policy",
            description="Test",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=3),
            ],
        )
        
        engine = PolicyEngine()
        decisions = engine.evaluate_retention_rules(sample_snapshots, policy)
        
        assert len(decisions) == len(sample_snapshots)
        retained = [d for d in decisions if d.should_retain]
        assert len(retained) >= 3  # At least 3 should be retained
    
    def test_evaluate_retention_rules_daily(self, sample_snapshots):
        """Test retention evaluation with daily rule."""
        policy = RetentionPolicy(
            id="test-policy",
            name="Test Policy",
            description="Test",
            rules=[
                RetentionRule(type=RetentionType.DAILY, count=7),
            ],
        )
        
        engine = PolicyEngine()
        decisions = engine.evaluate_retention_rules(sample_snapshots, policy)
        
        assert len(decisions) == len(sample_snapshots)
        # Should have retention decisions for all snapshots
        assert all(isinstance(d, RetentionDecision) for d in decisions)
    
    def test_build_retention_params(self):
        """Test building retention parameters from rules."""
        rules = [
            RetentionRule(type=RetentionType.LAST, count=5),
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
        ]
        
        engine = PolicyEngine()
        params = engine._build_retention_params(rules)
        
        assert params['keep_last'] == 5
        assert params['keep_daily'] == 7
        assert params['keep_weekly'] == 4
        assert params['keep_monthly'] == 0
        assert params['keep_yearly'] == 0
    
    def test_prune_snapshots_dry_run(self, mock_repository, sample_snapshots):
        """Test snapshot pruning in dry-run mode."""
        decisions = [
            RetentionDecision(
                snapshot=sample_snapshots[0],
                should_retain=True,
                reason="Keep last",
            ),
            RetentionDecision(
                snapshot=sample_snapshots[1],
                should_retain=False,
                reason="Too old",
            ),
        ]
        
        engine = PolicyEngine()
        result = engine.prune_snapshots(mock_repository, decisions, dry_run=True)
        
        assert result.success is True
        assert len(result.snapshots_removed) == 1
        assert len(result.snapshots_failed) == 0
    
    def test_prune_snapshots_no_removals(self, mock_repository, sample_snapshots):
        """Test pruning when no snapshots need removal."""
        decisions = [
            RetentionDecision(
                snapshot=snapshot,
                should_retain=True,
                reason="Keep",
            )
            for snapshot in sample_snapshots
        ]
        
        engine = PolicyEngine()
        result = engine.prune_snapshots(mock_repository, decisions, dry_run=False)
        
        assert result.success is True
        assert len(result.snapshots_removed) == 0
    
    def test_prune_snapshots_with_failures(self, mock_repository, sample_snapshots):
        """Test pruning with some snapshot deletion failures."""
        # Mock snapshot delete to fail for one snapshot
        sample_snapshots[0].delete = Mock(return_value=True)
        sample_snapshots[1].delete = Mock(side_effect=Exception("Delete failed"))
        
        decisions = [
            RetentionDecision(
                snapshot=sample_snapshots[0],
                should_retain=False,
                reason="Remove",
            ),
            RetentionDecision(
                snapshot=sample_snapshots[1],
                should_retain=False,
                reason="Remove",
            ),
        ]
        
        engine = PolicyEngine()
        result = engine.prune_snapshots(mock_repository, decisions, dry_run=False)
        
        assert result.success is False
        assert len(result.snapshots_removed) == 1
        assert len(result.snapshots_failed) == 1
    
    def test_validate_compliance_no_violations(self, sample_retention_policy, sample_snapshots):
        """Test compliance validation with no violations."""
        engine = PolicyEngine()
        status = engine.validate_compliance(
            sample_retention_policy,
            sample_snapshots,
        )
        
        assert isinstance(status, ComplianceStatus)
        assert status.compliant is True
        assert len(status.violations) == 0
    
    def test_validate_compliance_with_compliance_period(self, sample_snapshots):
        """Test compliance validation with compliance period."""
        policy = RetentionPolicy(
            id="test-policy",
            name="Test Policy",
            description="Test",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=1),  # Only keep 1
            ],
            compliance_period=timedelta(days=365),  # 1 year compliance
        )
        
        # Create a recent snapshot that would be removed but is in compliance period
        recent_snapshot = Mock(spec=BackupSnapshot)
        recent_snapshot.id = "recent-snapshot"
        recent_snapshot.timestamp = datetime.utcnow() - timedelta(days=30)
        recent_snapshot.tags = {}
        
        engine = PolicyEngine()
        status = engine.validate_compliance(policy, [recent_snapshot])
        
        assert isinstance(status, ComplianceStatus)
        # Compliance check should detect if recent snapshot would be removed
    
    def test_create_enforcement_record(self):
        """Test creating enforcement record."""
        engine = PolicyEngine()
        record = engine.create_enforcement_record(
            policy_id="test-policy",
            target_id="test-repo",
            enforcement_type=EnforcementType.MANUAL,
            success=True,
            snapshots_affected=["snap-1", "snap-2"],
            errors=[],
        )
        
        assert isinstance(record, EnforcementRecord)
        assert record.policy_id == "test-policy"
        assert record.target_id == "test-repo"
        assert record.success is True
        assert len(record.snapshots_affected) == 2
    
    def test_get_enforcement_history_no_filters(self):
        """Test retrieving enforcement history without filters."""
        engine = PolicyEngine()
        
        # Create some records
        engine.create_enforcement_record(
            policy_id="policy-1",
            target_id="repo-1",
            enforcement_type=EnforcementType.MANUAL,
            success=True,
            snapshots_affected=[],
        )
        engine.create_enforcement_record(
            policy_id="policy-2",
            target_id="repo-2",
            enforcement_type=EnforcementType.SCHEDULED,
            success=True,
            snapshots_affected=[],
        )
        
        history = engine.get_enforcement_history()
        assert len(history) == 2
    
    def test_get_enforcement_history_with_policy_filter(self):
        """Test retrieving enforcement history filtered by policy ID."""
        engine = PolicyEngine()
        
        engine.create_enforcement_record(
            policy_id="policy-1",
            target_id="repo-1",
            enforcement_type=EnforcementType.MANUAL,
            success=True,
            snapshots_affected=[],
        )
        engine.create_enforcement_record(
            policy_id="policy-2",
            target_id="repo-2",
            enforcement_type=EnforcementType.MANUAL,
            success=True,
            snapshots_affected=[],
        )
        
        history = engine.get_enforcement_history(policy_id="policy-1")
        assert len(history) == 1
        assert history[0].policy_id == "policy-1"
    
    def test_get_enforcement_history_with_limit(self):
        """Test retrieving enforcement history with limit."""
        engine = PolicyEngine()
        
        # Create multiple records
        for i in range(5):
            engine.create_enforcement_record(
                policy_id=f"policy-{i}",
                target_id="repo-1",
                enforcement_type=EnforcementType.MANUAL,
                success=True,
                snapshots_affected=[],
            )
        
        history = engine.get_enforcement_history(limit=3)
        assert len(history) == 3


class TestRetentionDecision:
    """Tests for RetentionDecision class."""
    
    def test_retention_decision_creation(self, sample_snapshots):
        """Test creating a retention decision."""
        decision = RetentionDecision(
            snapshot=sample_snapshots[0],
            should_retain=True,
            reason="Keep last snapshot",
            rule_applied="last_7",
        )
        
        assert decision.snapshot == sample_snapshots[0]
        assert decision.should_retain is True
        assert decision.reason == "Keep last snapshot"
        assert decision.rule_applied == "last_7"
    
    def test_retention_decision_to_dict(self, sample_snapshots):
        """Test converting retention decision to dictionary."""
        decision = RetentionDecision(
            snapshot=sample_snapshots[0],
            should_retain=False,
            reason="Too old",
        )
        
        data = decision.to_dict()
        assert 'snapshot_id' in data
        assert 'should_retain' in data
        assert data['should_retain'] is False


class TestPruneResult:
    """Tests for PruneResult class."""
    
    def test_prune_result_success(self):
        """Test creating successful prune result."""
        result = PruneResult(
            success=True,
            snapshots_removed=["snap-1", "snap-2"],
            snapshots_failed=[],
            space_freed_bytes=1000000,
        )
        
        assert result.success is True
        assert len(result.snapshots_removed) == 2
        assert len(result.snapshots_failed) == 0
        assert result.space_freed_bytes == 1000000
    
    def test_prune_result_with_failures(self):
        """Test creating prune result with failures."""
        result = PruneResult(
            success=False,
            snapshots_removed=["snap-1"],
            snapshots_failed=[("snap-2", "Delete failed")],
            errors=["Some snapshots failed to delete"],
        )
        
        assert result.success is False
        assert len(result.snapshots_removed) == 1
        assert len(result.snapshots_failed) == 1
        assert len(result.errors) == 1
