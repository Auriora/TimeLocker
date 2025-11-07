#!/usr/bin/env python3
"""
Policy Simulator Demonstration.

This script demonstrates the policy simulation and preview capabilities,
showing how to:
- Simulate retention policy enforcement
- Preview policy assignments
- Detect and resolve policy conflicts
- Compare different policies
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.policy import (
    PolicySimulator,
    PolicyEngine,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    RetentionType,
    PolicyType,
    TargetType,
    PolicyStatus,
    ConflictResolution,
)
from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_snapshot import BackupSnapshot


def create_sample_snapshots(count: int = 30) -> list:
    """Create sample snapshots for demonstration."""
    from pathlib import Path
    
    # Create a mock repository
    class MockRepo:
        def __init__(self):
            self.name = "demo-repository"
        
        def forget_snapshot(self, snapshot_id, prune=False):
            return f"Forgot snapshot {snapshot_id}"
    
    mock_repo = MockRepo()
    snapshots = []
    base_time = datetime.now()
    
    for i in range(count):
        # Create snapshots going back in time
        timestamp = base_time - timedelta(days=i)
        
        snapshot = BackupSnapshot(
            repo=mock_repo,
            snapshot_id=f"snapshot_{i:03d}",
            timestamp=timestamp,
            paths=[Path("/backup/data")],
        )
        # Add additional attributes that policy engine expects
        snapshot.tags = {'type': 'daily', 'host': 'demo-host'}
        snapshot.size_bytes = 1024 * 1024 * 100 * (i + 1)  # Varying sizes
        snapshot.repository = mock_repo  # For compatibility
        
        snapshots.append(snapshot)
    
    return snapshots


def demo_retention_simulation():
    """Demonstrate retention policy simulation."""
    print("=" * 70)
    print("RETENTION POLICY SIMULATION DEMO")
    print("=" * 70)
    
    # Create a retention policy
    policy = RetentionPolicy(
        id="retention_001",
        name="Standard Retention",
        description="Keep last 7 daily, 4 weekly, 6 monthly",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=7),
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
            RetentionRule(type=RetentionType.MONTHLY, count=6),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy: {policy.name}")
    print(f"Description: {policy.description}")
    print("\nRetention Rules:")
    for rule in policy.rules:
        print(f"  - {rule.type.value}: keep {rule.count}")
    
    # Create sample snapshots
    snapshots = create_sample_snapshots(30)
    print(f"\nCreated {len(snapshots)} sample snapshots")
    print(f"Date range: {snapshots[-1].timestamp.date()} to {snapshots[0].timestamp.date()}")
    
    # Create mock repository
    class MockRepository:
        def __init__(self):
            self.name = "demo-repository"
            self._snapshots = []
        
        def list_snapshots(self):
            return self._snapshots
    
    repository = MockRepository()
    repository._snapshots = snapshots
    
    # Create simulator and run simulation
    simulator = PolicySimulator()
    
    print("\n" + "-" * 70)
    print("Running simulation...")
    print("-" * 70)
    
    result = simulator.simulate_retention_policy(
        policy=policy,
        repository=repository,
        target_id="demo-repository",
    )
    
    # Display results
    print(f"\nSimulation completed at: {result.simulation_time}")
    print(f"\nSnapshots to retain: {len(result.snapshots_to_retain)}")
    print(f"Snapshots to prune: {len(result.snapshots_to_prune)}")
    
    if result.storage_impact:
        impact = result.storage_impact
        print(f"\nStorage Impact:")
        print(f"  Space to free: {impact.estimated_space_freed_bytes / (1024**2):.2f} MB")
        print(f"  Space to retain: {impact.total_retained_size_bytes / (1024**2):.2f} MB")
    
    if result.compliance_warnings:
        print(f"\nCompliance Warnings:")
        for warning in result.compliance_warnings:
            print(f"  - {warning}")
    
    # Show some snapshots that would be pruned
    if result.snapshots_to_prune:
        print(f"\nFirst 5 snapshots to prune:")
        for snapshot_info in result.snapshots_to_prune[:5]:
            print(f"  - {snapshot_info.snapshot_id}: {snapshot_info.timestamp.date()}")
    
    # Show some snapshots that would be retained
    if result.snapshots_to_retain:
        print(f"\nFirst 5 snapshots to retain:")
        for snapshot_info in result.snapshots_to_retain[:5]:
            print(f"  - {snapshot_info.snapshot_id}: {snapshot_info.timestamp.date()}")


def demo_conflict_detection():
    """Demonstrate policy conflict detection."""
    print("\n\n" + "=" * 70)
    print("POLICY CONFLICT DETECTION DEMO")
    print("=" * 70)
    
    # Create two policies
    policy1 = RetentionPolicy(
        id="retention_001",
        name="Aggressive Retention",
        description="Keep only recent snapshots",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=3),
            RetentionRule(type=RetentionType.DAILY, count=7),
        ],
        priority=10,
        status=PolicyStatus.ACTIVE,
    )
    
    policy2 = RetentionPolicy(
        id="retention_002",
        name="Conservative Retention",
        description="Keep many snapshots",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=10),
            RetentionRule(type=RetentionType.DAILY, count=30),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        priority=5,
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy 1: {policy1.name} (Priority: {policy1.priority})")
    print(f"  Rules: {len(policy1.rules)}")
    
    print(f"\nPolicy 2: {policy2.name} (Priority: {policy2.priority})")
    print(f"  Rules: {len(policy2.rules)}")
    
    # Create existing assignment
    existing_assignment = PolicyAssignment(
        id="assignment_001",
        policy_id=policy2.id,
        policy_type=PolicyType.RETENTION,
        target_type=TargetType.REPOSITORY,
        target_id="demo-repository",
        priority=5,
        active=True,
        conflict_resolution=ConflictResolution.PRIORITY,
    )
    
    print(f"\nExisting Assignment:")
    print(f"  Policy: {existing_assignment.policy_id}")
    print(f"  Target: {existing_assignment.target_type.value}/{existing_assignment.target_id}")
    print(f"  Conflict Resolution: {existing_assignment.conflict_resolution.value}")
    
    # Detect conflicts
    simulator = PolicySimulator()
    
    print("\n" + "-" * 70)
    print("Detecting conflicts...")
    print("-" * 70)
    
    conflicts = simulator.detect_policy_conflicts(
        new_policy=policy1,
        existing_assignments=[existing_assignment],
        target_type=TargetType.REPOSITORY,
        target_id="demo-repository",
    )
    
    if conflicts:
        print(f"\nFound {len(conflicts)} conflict(s):")
        for conflict in conflicts:
            print(f"\n  Conflict Type: {conflict.conflict_type}")
            print(f"  Description: {conflict.description}")
            print(f"  Resolution Strategy: {conflict.resolution_strategy.value}")
    else:
        print("\nNo conflicts detected")
    
    # Simulate conflict resolution
    if conflicts:
        print("\n" + "-" * 70)
        print("Simulating conflict resolution...")
        print("-" * 70)
        
        policies_dict = {
            policy1.id: policy1,
            policy2.id: policy2,
        }
        
        resolution = simulator.simulate_conflict_resolution(
            conflicts=conflicts,
            policies=policies_dict,
            resolution_strategy=ConflictResolution.PRIORITY,
        )
        
        print(f"\nResolution Results:")
        print(f"  Conflicts resolved: {resolution['conflicts_resolved']}")
        print(f"  Strategy: {resolution['resolution_strategy']}")
        
        for res in resolution['resolutions']:
            print(f"\n  Winning Policy: {res['winning_policy_name']} (ID: {res['winning_policy_id']})")


def demo_policy_comparison():
    """Demonstrate policy comparison."""
    print("\n\n" + "=" * 70)
    print("POLICY COMPARISON DEMO")
    print("=" * 70)
    
    # Create two different policies
    policy_aggressive = RetentionPolicy(
        id="retention_aggressive",
        name="Aggressive Retention",
        description="Minimal retention for space savings",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=3),
            RetentionRule(type=RetentionType.DAILY, count=7),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    policy_conservative = RetentionPolicy(
        id="retention_conservative",
        name="Conservative Retention",
        description="Maximum retention for safety",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=10),
            RetentionRule(type=RetentionType.DAILY, count=30),
            RetentionRule(type=RetentionType.WEEKLY, count=8),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy A: {policy_aggressive.name}")
    print(f"  Description: {policy_aggressive.description}")
    print(f"  Rules: {len(policy_aggressive.rules)}")
    
    print(f"\nPolicy B: {policy_conservative.name}")
    print(f"  Description: {policy_conservative.description}")
    print(f"  Rules: {len(policy_conservative.rules)}")
    
    # Create sample snapshots
    snapshots = create_sample_snapshots(60)
    print(f"\nComparing policies on {len(snapshots)} snapshots")
    
    # Compare policies
    simulator = PolicySimulator()
    
    print("\n" + "-" * 70)
    print("Running comparison...")
    print("-" * 70)
    
    comparison = simulator.compare_policies(
        policy1=policy_aggressive,
        policy2=policy_conservative,
        snapshots=snapshots,
    )
    
    # Display comparison results
    print(f"\nComparison Results:")
    print(f"\n{comparison['policy1']['name']}:")
    print(f"  Snapshots retained: {comparison['policy1']['snapshots_retained']}")
    print(f"  Estimated size: {comparison['policy1']['estimated_size_bytes'] / (1024**2):.2f} MB")
    
    print(f"\n{comparison['policy2']['name']}:")
    print(f"  Snapshots retained: {comparison['policy2']['snapshots_retained']}")
    print(f"  Estimated size: {comparison['policy2']['estimated_size_bytes'] / (1024**2):.2f} MB")
    
    print(f"\nDifferences:")
    diff = comparison['differences']
    print(f"  Snapshots only in Policy A: {diff['snapshots_only_in_policy1']}")
    print(f"  Snapshots only in Policy B: {diff['snapshots_only_in_policy2']}")
    print(f"  Snapshots in both: {diff['snapshots_in_both']}")
    print(f"  Size difference: {diff['size_difference_bytes'] / (1024**2):.2f} MB")


def demo_preview_assignment():
    """Demonstrate policy assignment preview."""
    print("\n\n" + "=" * 70)
    print("POLICY ASSIGNMENT PREVIEW DEMO")
    print("=" * 70)
    
    # Create a policy
    policy = RetentionPolicy(
        id="retention_new",
        name="New Retention Policy",
        description="Testing assignment preview",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=5),
            RetentionRule(type=RetentionType.DAILY, count=14),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy to assign: {policy.name}")
    print(f"Target: repository/backup-repo-01")
    
    # Create existing assignments
    existing_assignments = [
        PolicyAssignment(
            id="assignment_001",
            policy_id="retention_old",
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="backup-repo-01",
            priority=5,
            active=True,
            conflict_resolution=ConflictResolution.PRIORITY,
        ),
    ]
    
    print(f"\nExisting assignments: {len(existing_assignments)}")
    
    # Preview assignment
    simulator = PolicySimulator()
    
    print("\n" + "-" * 70)
    print("Previewing assignment...")
    print("-" * 70)
    
    preview = simulator.preview_policy_assignment(
        policy=policy,
        target_type=TargetType.REPOSITORY,
        target_id="backup-repo-01",
        existing_assignments=existing_assignments,
    )
    
    print(f"\nPreview Results:")
    print(f"  Policy: {preview.policy_id}")
    print(f"  Target: {preview.target_id}")
    print(f"  Conflicts detected: {len(preview.conflicts)}")
    
    if preview.conflicts:
        print(f"\n  Conflicts:")
        for conflict in preview.conflicts:
            print(f"    - {conflict.conflict_type}: {conflict.description}")
    else:
        print(f"\n  No conflicts - assignment can proceed safely")


def main():
    """Run all demonstrations."""
    print("\n")
    print("*" * 70)
    print("POLICY SIMULATOR DEMONSTRATION")
    print("*" * 70)
    
    try:
        demo_retention_simulation()
        demo_conflict_detection()
        demo_policy_comparison()
        demo_preview_assignment()
        
        print("\n\n" + "=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\nAll policy simulation features demonstrated successfully!")
        
    except Exception as e:
        print(f"\n\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
