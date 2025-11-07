#!/usr/bin/env python3
"""
Policy Storage Demo

This script demonstrates the policy storage and persistence layer functionality,
including:
- Saving and loading policies
- Policy serialization/deserialization
- Assignment persistence
- Audit trail storage
- Integration with PolicyManager
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.policy import (
    PolicyManager,
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    EnforcementRecord,
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
    EnforcementType,
    FileSystemPolicyStore,
    PolicySerializer,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_policy_serialization():
    """Demonstrate policy serialization and deserialization."""
    print_section("Policy Serialization Demo")
    
    # Create a retention policy
    policy = RetentionPolicy(
        id="test-retention-001",
        name="Test Retention Policy",
        description="A test retention policy for demonstration",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=7),
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
        ],
        priority=10,
        status=PolicyStatus.ACTIVE,
        created_by="demo_user",
    )
    
    print("Original Policy:")
    print(f"  ID: {policy.id}")
    print(f"  Name: {policy.name}")
    print(f"  Rules: {len(policy.rules)}")
    print(f"  Status: {policy.status.value}")
    
    # Serialize
    serializer = PolicySerializer()
    serialized = serializer.serialize_retention_policy(policy)
    
    print("\nSerialized to dictionary:")
    print(f"  Keys: {list(serialized.keys())}")
    print(f"  Rules count: {len(serialized['rules'])}")
    
    # Deserialize
    deserialized = serializer.deserialize_retention_policy(serialized)
    
    print("\nDeserialized Policy:")
    print(f"  ID: {deserialized.id}")
    print(f"  Name: {deserialized.name}")
    print(f"  Rules: {len(deserialized.rules)}")
    print(f"  Status: {deserialized.status.value}")
    print(f"  Match: {policy.id == deserialized.id}")


def demo_file_system_storage():
    """Demonstrate file system policy storage."""
    print_section("File System Storage Demo")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary storage: {temp_dir}")
        
        # Initialize storage
        store = FileSystemPolicyStore(config_dir=Path(temp_dir))
        
        print(f"\nStorage directories created:")
        print(f"  Backup policies: {store.backup_policies_dir}")
        print(f"  Retention policies: {store.retention_policies_dir}")
        print(f"  Assignments: {store.assignments_dir}")
        print(f"  Audit trail: {store.audit_dir}")
        
        # Create and save a retention policy
        policy = RetentionPolicy(
            id="demo-retention-001",
            name="Demo Retention Policy",
            description="Demonstration of policy storage",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=10),
                RetentionRule(type=RetentionType.DAILY, count=14),
            ],
            status=PolicyStatus.ACTIVE,
        )
        
        print(f"\nSaving retention policy: {policy.name}")
        success = store.save_retention_policy(policy)
        print(f"  Save result: {'Success' if success else 'Failed'}")
        
        # Load the policy back
        print(f"\nLoading retention policy: {policy.id}")
        loaded_policy = store.load_retention_policy(policy.id)
        
        if loaded_policy:
            print(f"  Loaded successfully!")
            print(f"  Name: {loaded_policy.name}")
            print(f"  Rules: {len(loaded_policy.rules)}")
            print(f"  Status: {loaded_policy.status.value}")
        else:
            print(f"  Failed to load policy")
        
        # List all policies
        print(f"\nListing all retention policies:")
        all_policies = store.list_retention_policies()
        print(f"  Found {len(all_policies)} policies")
        for p in all_policies:
            print(f"    - {p.name} (ID: {p.id})")
        
        # Create and save an assignment
        assignment = PolicyAssignment(
            id="demo-assignment-001",
            policy_id=policy.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id="demo-repo-001",
            priority=5,
            active=True,
        )
        
        print(f"\nSaving policy assignment:")
        print(f"  Policy: {assignment.policy_id}")
        print(f"  Target: {assignment.target_id}")
        success = store.save_assignment(assignment)
        print(f"  Save result: {'Success' if success else 'Failed'}")
        
        # List assignments
        print(f"\nListing assignments for policy {policy.id}:")
        assignments = store.list_assignments(policy_id=policy.id)
        print(f"  Found {len(assignments)} assignments")
        for a in assignments:
            print(f"    - Target: {a.target_id}, Active: {a.active}")
        
        # Create and save an enforcement record
        record = EnforcementRecord(
            id="demo-record-001",
            policy_id=policy.id,
            target_id="demo-repo-001",
            enforcement_type=EnforcementType.SCHEDULED,
            execution_time=datetime.utcnow(),
            success=True,
            snapshots_affected=["snap-001", "snap-002", "snap-003"],
        )
        
        print(f"\nSaving enforcement record:")
        print(f"  Policy: {record.policy_id}")
        print(f"  Snapshots affected: {len(record.snapshots_affected)}")
        success = store.save_enforcement_record(record)
        print(f"  Save result: {'Success' if success else 'Failed'}")
        
        # List enforcement records
        print(f"\nListing enforcement records for policy {policy.id}:")
        records = store.list_enforcement_records(policy_id=policy.id)
        print(f"  Found {len(records)} records")
        for r in records:
            print(f"    - Time: {r.execution_time.isoformat()}")
            print(f"      Success: {r.success}")
            print(f"      Snapshots: {len(r.snapshots_affected)}")


def demo_policy_manager_integration():
    """Demonstrate PolicyManager integration with storage."""
    print_section("PolicyManager Storage Integration Demo")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary storage: {temp_dir}")
        
        # Initialize storage
        store = FileSystemPolicyStore(config_dir=Path(temp_dir))
        
        # Create PolicyManager with storage
        print("\nInitializing PolicyManager with storage...")
        manager = PolicyManager(policy_store=store)
        print("  PolicyManager initialized")
        print(f"  Default retention policy loaded: {manager.DEFAULT_RETENTION_POLICY['id']}")
        
        # Create a retention policy
        print("\nCreating retention policy...")
        retention_policy = manager.create_retention_policy(
            name="Weekly Backup Retention",
            description="Keep weekly backups for 4 weeks",
            rules=[
                RetentionRule(type=RetentionType.LAST, count=7),
                RetentionRule(type=RetentionType.WEEKLY, count=4),
            ],
            status=PolicyStatus.ACTIVE,
            created_by="demo_user",
        )
        print(f"  Created: {retention_policy.name} (ID: {retention_policy.id})")
        
        # Verify it was persisted
        print("\nVerifying persistence...")
        loaded = store.load_retention_policy(retention_policy.id)
        if loaded:
            print(f"  ✓ Policy persisted successfully")
            print(f"    Name: {loaded.name}")
            print(f"    Rules: {len(loaded.rules)}")
        else:
            print(f"  ✗ Policy not found in storage")
        
        # Create a backup policy
        print("\nCreating backup policy...")
        backup_policy = manager.create_backup_policy(
            name="Daily System Backup",
            description="Daily backup of system files",
            data_selection_refs=["system-files"],
            target_repositories=["local-repo"],
            backup_tool="restic",
            retention_policy_id=retention_policy.id,
            status=PolicyStatus.ACTIVE,
            created_by="demo_user",
        )
        print(f"  Created: {backup_policy.name} (ID: {backup_policy.id})")
        
        # Assign policy to a repository
        print("\nAssigning policy to repository...")
        assignment = manager.assign_policy(
            policy_id=backup_policy.id,
            policy_type=PolicyType.BACKUP,
            target_type=TargetType.REPOSITORY,
            target_id="local-repo",
            priority=10,
            assigned_by="demo_user",
        )
        print(f"  Assigned: {assignment.id}")
        
        # Verify assignment was persisted
        print("\nVerifying assignment persistence...")
        loaded_assignment = store.load_assignment(assignment.id)
        if loaded_assignment:
            print(f"  ✓ Assignment persisted successfully")
            print(f"    Policy: {loaded_assignment.policy_id}")
            print(f"    Target: {loaded_assignment.target_id}")
        else:
            print(f"  ✗ Assignment not found in storage")
        
        # List all policies
        print("\nListing all policies in storage:")
        backup_policies = store.list_backup_policies()
        retention_policies = store.list_retention_policies()
        print(f"  Backup policies: {len(backup_policies)}")
        for p in backup_policies:
            print(f"    - {p.name}")
        print(f"  Retention policies: {len(retention_policies)}")
        for p in retention_policies:
            print(f"    - {p.name}")
        
        # Simulate creating a new PolicyManager instance (reload from storage)
        print("\nSimulating application restart...")
        print("  Creating new PolicyManager instance...")
        manager2 = PolicyManager(policy_store=store)
        
        print(f"\nPolicies loaded from storage:")
        print(f"  Backup policies: {len(manager2._backup_policies)}")
        print(f"  Retention policies: {len(manager2._retention_policies)}")
        print(f"  Assignments: {len(manager2._policy_assignments)}")
        
        # Verify we can access the previously created policy
        try:
            loaded_backup = manager2.get_backup_policy(backup_policy.id)
            print(f"\n✓ Successfully loaded backup policy from storage:")
            print(f"    Name: {loaded_backup.name}")
            print(f"    Status: {loaded_backup.status.value}")
            print(f"    Retention policy: {loaded_backup.retention_policy_id}")
        except Exception as e:
            print(f"\n✗ Failed to load backup policy: {e}")


def demo_audit_trail():
    """Demonstrate audit trail functionality."""
    print_section("Audit Trail Demo")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary storage: {temp_dir}")
        
        store = FileSystemPolicyStore(config_dir=Path(temp_dir))
        
        # Create multiple enforcement records
        print("\nCreating enforcement records...")
        for i in range(5):
            record = EnforcementRecord(
                id=f"record-{i:03d}",
                policy_id="test-policy-001",
                target_id="test-repo-001",
                enforcement_type=EnforcementType.SCHEDULED,
                execution_time=datetime.utcnow() - timedelta(hours=i),
                success=i % 2 == 0,  # Alternate success/failure
                snapshots_affected=[f"snap-{j:03d}" for j in range(i + 1)],
                errors=[] if i % 2 == 0 else [f"Error in iteration {i}"],
            )
            store.save_enforcement_record(record)
            print(f"  Created record {i + 1}: {'Success' if record.success else 'Failed'}")
        
        # Query audit trail
        print("\nQuerying audit trail...")
        all_records = store.list_enforcement_records()
        print(f"  Total records: {len(all_records)}")
        
        # Filter by policy
        policy_records = store.list_enforcement_records(policy_id="test-policy-001")
        print(f"  Records for policy 'test-policy-001': {len(policy_records)}")
        
        # Show recent records
        print("\nRecent enforcement records (most recent first):")
        for record in policy_records[:3]:
            print(f"  - {record.id}")
            print(f"    Time: {record.execution_time.isoformat()}")
            print(f"    Success: {record.success}")
            print(f"    Snapshots: {len(record.snapshots_affected)}")
            if record.errors:
                print(f"    Errors: {', '.join(record.errors)}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  Policy Storage and Persistence Demo")
    print("=" * 70)
    
    try:
        demo_policy_serialization()
        demo_file_system_storage()
        demo_policy_manager_integration()
        demo_audit_trail()
        
        print_section("Demo Complete")
        print("All storage and persistence features demonstrated successfully!")
        print("\nKey Features:")
        print("  ✓ Policy serialization/deserialization")
        print("  ✓ File system storage with atomic operations")
        print("  ✓ Policy persistence (backup and retention)")
        print("  ✓ Assignment persistence")
        print("  ✓ Audit trail storage")
        print("  ✓ PolicyManager integration")
        print("  ✓ Storage reload on restart")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
