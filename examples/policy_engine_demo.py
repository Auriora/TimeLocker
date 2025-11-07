#!/usr/bin/env python3
"""
Policy Engine Demo

This script demonstrates the Policy Engine functionality for policy enforcement,
retention rule evaluation, snapshot pruning, and compliance validation.

The Policy Engine coordinates with backup repositories and the existing retention
logic to safely enforce retention policies.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.policy import (
    PolicyEngine,
    RetentionPolicy,
    RetentionRule,
    RetentionType,
    EnforcementType,
    PolicyStatus,
)
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_repository import BackupRepository


def create_mock_snapshots(count: int, start_date: datetime) -> list:
    """Create mock snapshots for demonstration."""
    snapshots = []
    for i in range(count):
        # Create snapshots going back in time
        timestamp = start_date - timedelta(days=i)
        snapshot = BackupSnapshot(
            repo=None,  # Mock repository
            snapshot_id=f"snapshot_{i:03d}",
            timestamp=timestamp,
            paths=[Path("/data")]
        )
        snapshots.append(snapshot)
    return snapshots


def demo_retention_evaluation():
    """Demonstrate retention rule evaluation."""
    print("=" * 80)
    print("DEMO 1: Retention Rule Evaluation")
    print("=" * 80)
    
    # Create a retention policy
    policy = RetentionPolicy(
        id="policy_001",
        name="Standard Retention",
        description="Keep last 7 daily, 4 weekly, 12 monthly snapshots",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=3),
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy: {policy.name}")
    print(f"Description: {policy.description}")
    print("\nRetention Rules:")
    for rule in policy.rules:
        print(f"  - {rule.type.value}: keep {rule.count}")
    
    # Create mock snapshots (30 days worth)
    snapshots = create_mock_snapshots(30, datetime.utcnow())
    print(f"\nEvaluating {len(snapshots)} snapshots...")
    
    # Create policy engine and evaluate
    engine = PolicyEngine()
    decisions = engine.evaluate_retention_rules(snapshots, policy)
    
    # Analyze results
    to_retain = [d for d in decisions if d.should_retain]
    to_remove = [d for d in decisions if not d.should_retain]
    
    print(f"\nResults:")
    print(f"  Snapshots to retain: {len(to_retain)}")
    print(f"  Snapshots to remove: {len(to_remove)}")
    
    print("\nSnapshots to retain (first 5):")
    for decision in to_retain[:5]:
        print(f"  - {decision.snapshot.id} ({decision.snapshot.timestamp.date()})")
        print(f"    Reason: {decision.reason}")
    
    print("\nSnapshots to remove (first 5):")
    for decision in to_remove[:5]:
        print(f"  - {decision.snapshot.id} ({decision.snapshot.timestamp.date()})")
        print(f"    Reason: {decision.reason}")


def demo_dry_run_pruning():
    """Demonstrate dry-run snapshot pruning."""
    print("\n" + "=" * 80)
    print("DEMO 2: Dry-Run Snapshot Pruning")
    print("=" * 80)
    
    # Create a simple retention policy
    policy = RetentionPolicy(
        id="policy_002",
        name="Aggressive Retention",
        description="Keep only last 5 snapshots",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=5),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy: {policy.name}")
    print(f"Description: {policy.description}")
    
    # Create mock snapshots
    snapshots = create_mock_snapshots(15, datetime.utcnow())
    print(f"\nTotal snapshots: {len(snapshots)}")
    
    # Evaluate retention
    engine = PolicyEngine()
    decisions = engine.evaluate_retention_rules(snapshots, policy)
    
    # Perform dry-run pruning
    print("\nPerforming dry-run pruning...")
    try:
        # Note: This will fail without a real repository, but demonstrates the API
        result = engine.prune_snapshots(
            repository=None,  # Would be a real BackupRepository
            retention_decisions=decisions,
            dry_run=True
        )
        
        print(f"\nDry-run results:")
        print(f"  Success: {result.success}")
        print(f"  Would remove: {len(result.snapshots_removed)} snapshots")
        print(f"  Failed: {len(result.snapshots_failed)} snapshots")
        
        if result.snapshots_removed:
            print(f"\nSnapshots that would be removed:")
            for snapshot_id in result.snapshots_removed[:5]:
                print(f"  - {snapshot_id}")
    
    except Exception as e:
        print(f"\nNote: Dry-run simulation (no real repository): {type(e).__name__}")
        print("In production, this would show which snapshots would be removed")


def demo_compliance_validation():
    """Demonstrate compliance validation."""
    print("\n" + "=" * 80)
    print("DEMO 3: Compliance Validation")
    print("=" * 80)
    
    # Create a policy with compliance period
    policy = RetentionPolicy(
        id="policy_003",
        name="Compliance Retention",
        description="Keep snapshots with 90-day compliance period",
        rules=[
            RetentionRule(type=RetentionType.DAILY, count=7),
        ],
        compliance_period=timedelta(days=90),
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"\nPolicy: {policy.name}")
    print(f"Compliance Period: {policy.compliance_period.days} days")
    
    # Create snapshots including some within compliance period
    snapshots = create_mock_snapshots(100, datetime.utcnow())
    print(f"\nTotal snapshots: {len(snapshots)}")
    
    # Validate compliance
    engine = PolicyEngine()
    compliance_status = engine.validate_compliance(policy, snapshots)
    
    print(f"\nCompliance Status:")
    print(f"  Compliant: {compliance_status.compliant}")
    print(f"  Violations: {len(compliance_status.violations)}")
    
    if compliance_status.violations:
        print("\nViolations detected:")
        for violation in compliance_status.violations[:3]:
            print(f"  - Rule: {violation.rule_id}")
            print(f"    Severity: {violation.severity}")
            print(f"    Description: {violation.description}")
    
    if compliance_status.next_required_action:
        action = compliance_status.next_required_action
        print(f"\nNext Required Action:")
        print(f"  Type: {action.action_type}")
        print(f"  Priority: {action.priority}")
        print(f"  Description: {action.description}")


def demo_enforcement_tracking():
    """Demonstrate enforcement record tracking."""
    print("\n" + "=" * 80)
    print("DEMO 4: Enforcement Record Tracking")
    print("=" * 80)
    
    engine = PolicyEngine()
    
    # Create some enforcement records
    print("\nCreating enforcement records...")
    
    record1 = engine.create_enforcement_record(
        policy_id="policy_001",
        target_id="repo_001",
        enforcement_type=EnforcementType.SCHEDULED,
        success=True,
        snapshots_affected=["snap_001", "snap_002", "snap_003"],
        metadata={"duration_seconds": 45.2}
    )
    print(f"  Created record: {record1.id}")
    
    record2 = engine.create_enforcement_record(
        policy_id="policy_001",
        target_id="repo_002",
        enforcement_type=EnforcementType.MANUAL,
        success=True,
        snapshots_affected=["snap_004", "snap_005"],
        metadata={"duration_seconds": 23.1}
    )
    print(f"  Created record: {record2.id}")
    
    record3 = engine.create_enforcement_record(
        policy_id="policy_002",
        target_id="repo_001",
        enforcement_type=EnforcementType.BACKUP_TRIGGERED,
        success=False,
        snapshots_affected=[],
        errors=["Repository locked by another process"],
        metadata={"retry_count": 3}
    )
    print(f"  Created record: {record3.id}")
    
    # Retrieve enforcement history
    print("\nRetrieving enforcement history...")
    
    all_records = engine.get_enforcement_history()
    print(f"\nTotal enforcement records: {len(all_records)}")
    
    for record in all_records:
        print(f"\n  Record ID: {record.id}")
        print(f"  Policy: {record.policy_id}")
        print(f"  Target: {record.target_id}")
        print(f"  Type: {record.enforcement_type.value}")
        print(f"  Success: {record.success}")
        print(f"  Snapshots affected: {len(record.snapshots_affected)}")
        print(f"  Execution time: {record.execution_time}")
        if record.errors:
            print(f"  Errors: {', '.join(record.errors)}")
    
    # Filter by policy
    print(f"\nFiltering by policy 'policy_001'...")
    policy_records = engine.get_enforcement_history(policy_id="policy_001")
    print(f"  Found {len(policy_records)} records for policy_001")
    
    # Filter by target
    print(f"\nFiltering by target 'repo_001'...")
    target_records = engine.get_enforcement_history(target_id="repo_001")
    print(f"  Found {len(target_records)} records for repo_001")


def demo_integration_workflow():
    """Demonstrate complete policy enforcement workflow."""
    print("\n" + "=" * 80)
    print("DEMO 5: Complete Policy Enforcement Workflow")
    print("=" * 80)
    
    # Step 1: Create policy
    policy = RetentionPolicy(
        id="policy_workflow",
        name="Production Retention Policy",
        description="Standard production retention with compliance",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=5),
            RetentionRule(type=RetentionType.DAILY, count=14),
            RetentionRule(type=RetentionType.WEEKLY, count=8),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        compliance_period=timedelta(days=30),
        status=PolicyStatus.ACTIVE,
    )
    
    print("\nStep 1: Policy Configuration")
    print(f"  Policy: {policy.name}")
    print(f"  Rules: {len(policy.rules)}")
    print(f"  Compliance Period: {policy.compliance_period.days} days")
    
    # Step 2: Get snapshots
    snapshots = create_mock_snapshots(60, datetime.utcnow())
    print(f"\nStep 2: Snapshot Discovery")
    print(f"  Total snapshots: {len(snapshots)}")
    
    # Step 3: Evaluate retention
    engine = PolicyEngine()
    print(f"\nStep 3: Evaluate Retention Rules")
    decisions = engine.evaluate_retention_rules(snapshots, policy)
    
    to_retain = sum(1 for d in decisions if d.should_retain)
    to_remove = sum(1 for d in decisions if not d.should_retain)
    print(f"  To retain: {to_retain}")
    print(f"  To remove: {to_remove}")
    
    # Step 4: Validate compliance
    print(f"\nStep 4: Validate Compliance")
    compliance = engine.validate_compliance(policy, snapshots)
    print(f"  Compliant: {compliance.compliant}")
    print(f"  Violations: {len(compliance.violations)}")
    
    # Step 5: Dry-run enforcement
    print(f"\nStep 5: Dry-Run Enforcement")
    print("  Simulating snapshot removal...")
    print(f"  Would remove {to_remove} snapshots")
    
    # Step 6: Create enforcement record
    print(f"\nStep 6: Create Audit Record")
    record = engine.create_enforcement_record(
        policy_id=policy.id,
        target_id="production_repo",
        enforcement_type=EnforcementType.SCHEDULED,
        success=True,
        snapshots_affected=[d.snapshot.id for d in decisions if not d.should_retain],
        metadata={
            "snapshots_retained": to_retain,
            "snapshots_removed": to_remove,
            "compliance_status": "compliant" if compliance.compliant else "violations",
        }
    )
    print(f"  Record ID: {record.id}")
    print(f"  Snapshots affected: {len(record.snapshots_affected)}")
    
    print("\nWorkflow complete!")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("POLICY ENGINE DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo shows the Policy Engine capabilities:")
    print("  1. Retention rule evaluation")
    print("  2. Dry-run snapshot pruning")
    print("  3. Compliance validation")
    print("  4. Enforcement record tracking")
    print("  5. Complete enforcement workflow")
    
    try:
        demo_retention_evaluation()
        demo_dry_run_pruning()
        demo_compliance_validation()
        demo_enforcement_tracking()
        demo_integration_workflow()
        
        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE")
        print("=" * 80)
        print("\nThe Policy Engine provides:")
        print("  ✓ Retention rule evaluation using existing retention.py logic")
        print("  ✓ Safe snapshot pruning with dry-run support")
        print("  ✓ Compliance validation and violation detection")
        print("  ✓ Comprehensive enforcement tracking and audit logging")
        print("  ✓ Integration with repository services")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
