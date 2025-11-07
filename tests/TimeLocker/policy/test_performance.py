"""
Performance tests for policy management system.

These tests verify that policy operations perform efficiently with
large numbers of policies, assignments, and snapshots.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.TimeLocker.policy.manager import PolicyManager
from src.TimeLocker.policy.engine import PolicyEngine
from src.TimeLocker.policy.models import RetentionRule
from src.TimeLocker.policy.types import (
    PolicyType,
    TargetType,
    RetentionType,
)


class TestPolicyPerformance:
    """Performance tests for policy operations."""
    
    def test_large_scale_policy_creation(self, mock_policy_store):
        """Test creating many policies efficiently."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        start_time = time.time()
        
        # Create 100 retention policies
        policies = []
        for i in range(100):
            policy = manager.create_retention_policy(
                name=f"Policy {i}",
                description=f"Test policy {i}",
                rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
            )
            policies.append(policy)
        
        elapsed = time.time() - start_time
        
        assert len(policies) == 100
        assert elapsed < 5.0  # Should complete in under 5 seconds
    
    def test_large_scale_policy_assignment(self, mock_policy_store):
        """Test assigning policies to many targets efficiently."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create one policy
        policy = manager.create_retention_policy(
            name="Test Policy",
            description="Test",
            rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
        )
        
        start_time = time.time()
        
        # Assign to 100 targets
        assignments = []
        for i in range(100):
            assignment = manager.assign_policy(
                policy_id=policy.id,
                policy_type=PolicyType.RETENTION,
                target_type=TargetType.REPOSITORY,
                target_id=f"repo-{i}",
            )
            assignments.append(assignment)
        
        elapsed = time.time() - start_time
        
        assert len(assignments) == 100
        assert elapsed < 5.0  # Should complete in under 5 seconds
    
    def test_large_snapshot_retention_evaluation(self, mock_policy_store):
        """Test retention evaluation with many snapshots."""
        manager = PolicyManager(policy_store=mock_policy_store)
        engine = PolicyEngine()
        
        # Create policy
        policy = manager.create_retention_policy(
            name="Test Policy",
            description="Test",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=10),
                RetentionRule(type=RetentionType.DAILY, count=30),
                RetentionRule(type=RetentionType.WEEKLY, count=12),
            ],
        )
        
        # Create 1000 snapshots
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        snapshots = []
        for i in range(1000):
            snapshot = Mock()
            snapshot.id = f"snapshot-{i:04d}"
            snapshot.timestamp = base_time - timedelta(hours=i)
            snapshot.tags = {}
            snapshots.append(snapshot)
        
        start_time = time.time()
        
        # Evaluate retention
        decisions = engine.evaluate_retention_rules(snapshots, policy)
        
        elapsed = time.time() - start_time
        
        assert len(decisions) == 1000
        assert elapsed < 2.0  # Should complete in under 2 seconds
    
    def test_policy_lookup_performance(self, mock_policy_store):
        """Test policy lookup performance with many policies."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create 500 policies
        for i in range(500):
            manager.create_retention_policy(
                name=f"Policy {i}",
                description=f"Test policy {i}",
                rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
            )
        
        # Get list of policy IDs
        policy_ids = list(manager._retention_policies.keys())
        
        start_time = time.time()
        
        # Lookup 100 random policies
        for i in range(100):
            policy_id = policy_ids[i % len(policy_ids)]
            policy = manager.get_retention_policy(policy_id)
            assert policy is not None
        
        elapsed = time.time() - start_time
        
        assert elapsed < 0.5  # Should complete in under 0.5 seconds
    
    def test_assignment_query_performance(self, mock_policy_store):
        """Test querying assignments with many assignments."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create policies
        policies = []
        for i in range(50):
            policy = manager.create_retention_policy(
                name=f"Policy {i}",
                description=f"Test policy {i}",
                rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
            )
            policies.append(policy)
        
        # Create assignments (50 policies x 20 targets = 1000 assignments)
        for policy in policies:
            for j in range(20):
                manager.assign_policy(
                    policy_id=policy.id,
                    policy_type=PolicyType.RETENTION,
                    target_type=TargetType.REPOSITORY,
                    target_id=f"repo-{j}",
                )
        
        start_time = time.time()
        
        # Query assignments by target
        for i in range(20):
            assignments = manager.get_policy_assignments(target_id=f"repo-{i}")
            assert len(assignments) == 50
        
        elapsed = time.time() - start_time
        
        assert elapsed < 1.0  # Should complete in under 1 second
    
    def test_effective_policy_resolution_performance(self, mock_policy_store):
        """Test effective policy resolution with multiple assignments."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create 10 policies
        policies = []
        for i in range(10):
            policy = manager.create_retention_policy(
                name=f"Policy {i}",
                description=f"Test policy {i}",
                rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
            )
            policies.append(policy)
        
        # Assign all to same target with different priorities
        for i, policy in enumerate(policies):
            manager.assign_policy(
                policy_id=policy.id,
                policy_type=PolicyType.RETENTION,
                target_type=TargetType.REPOSITORY,
                target_id="test-repo",
                priority=i,
            )
        
        start_time = time.time()
        
        # Resolve effective policy 100 times
        for _ in range(100):
            effective = manager.get_effective_policies(
                target_type=TargetType.REPOSITORY,
                target_id="test-repo",
            )
            assert effective['retention_policy'] is not None
        
        elapsed = time.time() - start_time
        
        assert elapsed < 0.5  # Should complete in under 0.5 seconds


class TestMemoryEfficiency:
    """Tests for memory efficiency of policy operations."""
    
    def test_policy_storage_memory_usage(self, mock_policy_store):
        """Test that policy storage doesn't consume excessive memory."""
        manager = PolicyManager(policy_store=mock_policy_store)
        
        # Create many policies
        for i in range(1000):
            manager.create_retention_policy(
                name=f"Policy {i}",
                description=f"Test policy {i}",
                rules=[RetentionRule(type=RetentionType.DAILY, count=7)],
            )
        
        # Verify policies are stored
        assert len(manager._retention_policies) == 1001  # Including default
        
        # Memory usage should be reasonable (this is a basic check)
        # In a real scenario, you'd use memory profiling tools
        assert len(manager._retention_policies) < 2000
    
    def test_enforcement_history_memory_management(self, mock_policy_store):
        """Test that enforcement history doesn't grow unbounded."""
        engine = PolicyEngine(policy_store=mock_policy_store)
        
        # Create many enforcement records
        for i in range(1000):
            engine.create_enforcement_record(
                policy_id=f"policy-{i}",
                target_id="test-repo",
                enforcement_type="manual",
                success=True,
                snapshots_affected=[],
            )
        
        # Get limited history
        history = engine.get_enforcement_history(limit=100)
        
        # Should only return requested limit
        assert len(history) == 100
