#!/usr/bin/env python3
"""
Policy Manager Demonstration Script.

This script demonstrates the PolicyManager functionality including:
- Creating backup and retention policies
- CRUD operations on policies
- Policy assignment to repositories
- Policy template and duplication
- Default policy application
- Effective policy resolution
"""

import sys
from pathlib import Path
from datetime import timedelta

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from TimeLocker.policy import (
    PolicyManager,
    RetentionRule,
    ScheduleConfig,
    ComplianceRule,
    PolicyType,
    TargetType,
    RetentionType,
    PolicyStatus,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def demo_policy_creation():
    """Demonstrate policy creation."""
    print_section("Policy Creation")
    
    # Initialize PolicyManager
    manager = PolicyManager()
    print("✓ PolicyManager initialized")
    print(f"  Default retention policy: {manager.DEFAULT_RETENTION_POLICY['id']}")
    
    # Create a retention policy
    print("\n1. Creating retention policy...")
    retention_policy = manager.create_retention_policy(
        name="Standard Retention",
        description="Standard retention policy for daily backups",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=7),
            RetentionRule(type=RetentionType.DAILY, count=14),
            RetentionRule(type=RetentionType.WEEKLY, count=8),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        priority=10,
        status=PolicyStatus.ACTIVE,
        created_by="demo_user",
    )
    print(f"✓ Created retention policy: {retention_policy.name}")
    print(f"  ID: {retention_policy.id}")
    print(f"  Rules: {len(retention_policy.rules)}")
    print(f"  Status: {retention_policy.status.value}")
    
    # Create a backup policy
    print("\n2. Creating backup policy...")
    backup_policy = manager.create_backup_policy(
        name="Daily Home Backup",
        description="Daily backup of home directory",
        data_selection_refs=["home-documents", "home-photos"],
        target_repositories=["local-backup", "cloud-backup"],
        backup_tool="restic",
        schedule=ScheduleConfig(
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
            timezone="UTC",
        ),
        execution_params={
            "compression": "auto",
            "exclude_caches": True,
        },
        retention_policy_id=retention_policy.id,
        tags={"environment": "production", "type": "daily"},
        compliance_requirements=[
            ComplianceRule(
                rule_id="gdpr-retention",
                description="GDPR 30-day minimum retention",
                minimum_retention_days=30,
            ),
        ],
        priority=10,
        status=PolicyStatus.ACTIVE,
        created_by="demo_user",
    )
    print(f"✓ Created backup policy: {backup_policy.name}")
    print(f"  ID: {backup_policy.id}")
    print(f"  Backup tool: {backup_policy.backup_tool}")
    print(f"  Target repositories: {', '.join(backup_policy.target_repositories)}")
    print(f"  Retention policy: {backup_policy.retention_policy_id}")
    
    return manager, backup_policy, retention_policy


def demo_policy_crud(manager: PolicyManager, backup_policy, retention_policy):
    """Demonstrate CRUD operations."""
    print_section("Policy CRUD Operations")
    
    # List policies
    print("1. Listing all backup policies...")
    backup_policies = manager.list_backup_policies()
    print(f"✓ Found {len(backup_policies)} backup policies:")
    for policy in backup_policies:
        print(f"  - {policy.name} ({policy.status.value})")
    
    print("\n2. Listing all retention policies...")
    retention_policies = manager.list_retention_policies()
    print(f"✓ Found {len(retention_policies)} retention policies:")
    for policy in retention_policies:
        print(f"  - {policy.name} ({policy.status.value})")
    
    # Update a policy
    print("\n3. Updating backup policy...")
    updated_policy = manager.update_backup_policy(
        backup_policy.id,
        description="Updated: Daily backup of home directory with cloud sync",
        tags={"environment": "production", "type": "daily", "sync": "cloud"},
    )
    print(f"✓ Updated backup policy: {updated_policy.name}")
    print(f"  New description: {updated_policy.description}")
    print(f"  New tags: {updated_policy.tags}")
    
    # Get a specific policy
    print("\n4. Retrieving specific policy...")
    retrieved_policy = manager.get_backup_policy(backup_policy.id)
    print(f"✓ Retrieved policy: {retrieved_policy.name}")
    print(f"  Created at: {retrieved_policy.created_at}")
    print(f"  Updated at: {retrieved_policy.updated_at}")


def demo_policy_assignment(manager: PolicyManager, backup_policy, retention_policy):
    """Demonstrate policy assignment."""
    print_section("Policy Assignment")
    
    # Assign backup policy to repository
    print("1. Assigning backup policy to repository...")
    assignment1 = manager.assign_policy(
        policy_id=backup_policy.id,
        policy_type=PolicyType.BACKUP,
        target_type=TargetType.REPOSITORY,
        target_id="local-backup",
        priority=10,
        active=True,
        assigned_by="demo_user",
        metadata={"reason": "primary backup target"},
    )
    print(f"✓ Assigned backup policy to repository 'local-backup'")
    print(f"  Assignment ID: {assignment1.id}")
    print(f"  Priority: {assignment1.priority}")
    
    # Assign retention policy to repository
    print("\n2. Assigning retention policy to repository...")
    assignment2 = manager.assign_policy(
        policy_id=retention_policy.id,
        policy_type=PolicyType.RETENTION,
        target_type=TargetType.REPOSITORY,
        target_id="cloud-backup",
        priority=5,
        active=True,
        assigned_by="demo_user",
    )
    print(f"✓ Assigned retention policy to repository 'cloud-backup'")
    print(f"  Assignment ID: {assignment2.id}")
    
    # List assignments
    print("\n3. Listing all policy assignments...")
    all_assignments = manager.get_policy_assignments()
    print(f"✓ Found {len(all_assignments)} assignments:")
    for assignment in all_assignments:
        print(f"  - {assignment.policy_type.value} policy → "
              f"{assignment.target_type.value} '{assignment.target_id}'")
    
    # Get assignments for specific policy
    print("\n4. Getting assignments for backup policy...")
    policy_assignments = manager.get_policy_assignments(policy_id=backup_policy.id)
    print(f"✓ Found {len(policy_assignments)} assignments for this policy")
    
    # Update assignment status
    print("\n5. Deactivating an assignment...")
    updated_assignment = manager.update_assignment_status(assignment1.id, active=False)
    print(f"✓ Assignment {assignment1.id} is now inactive")
    
    # Reactivate it
    print("\n6. Reactivating the assignment...")
    updated_assignment = manager.update_assignment_status(assignment1.id, active=True)
    print(f"✓ Assignment {assignment1.id} is now active again")
    
    return assignment1, assignment2


def demo_policy_templates(manager: PolicyManager, backup_policy, retention_policy):
    """Demonstrate policy templates and duplication."""
    print_section("Policy Templates and Duplication")
    
    # Create a template from backup policy
    print("1. Creating template from backup policy...")
    template = manager.create_policy_template(
        template_name="Daily Backup Template",
        policy_id=backup_policy.id,
        policy_type=PolicyType.BACKUP,
    )
    print(f"✓ Created template: {template['template_name']}")
    print(f"  Source policy: {template['source_policy_id']}")
    print(f"  Created at: {template['created_at']}")
    
    # Duplicate backup policy
    print("\n2. Duplicating backup policy...")
    duplicated_backup = manager.duplicate_backup_policy(
        source_policy_id=backup_policy.id,
        new_name="Weekly Home Backup",
        new_description="Weekly backup of home directory",
        status=PolicyStatus.DRAFT,
    )
    print(f"✓ Created duplicate: {duplicated_backup.name}")
    print(f"  New ID: {duplicated_backup.id}")
    print(f"  Status: {duplicated_backup.status.value}")
    print(f"  Inherits configuration from: {backup_policy.name}")
    
    # Duplicate retention policy
    print("\n3. Duplicating retention policy...")
    duplicated_retention = manager.duplicate_retention_policy(
        source_policy_id=retention_policy.id,
        new_name="Extended Retention",
        new_description="Extended retention for compliance",
        status=PolicyStatus.DRAFT,
    )
    print(f"✓ Created duplicate: {duplicated_retention.name}")
    print(f"  New ID: {duplicated_retention.id}")
    print(f"  Rules: {len(duplicated_retention.rules)}")
    
    return duplicated_backup, duplicated_retention


def demo_default_policies(manager: PolicyManager):
    """Demonstrate default policy application."""
    print_section("Default Policy Application")
    
    # Apply default retention policy
    print("1. Applying default retention policy to a repository...")
    default_assignment = manager.apply_default_retention_policy(
        target_type=TargetType.REPOSITORY,
        target_id="new-repository",
    )
    print(f"✓ Applied default retention policy")
    print(f"  Assignment ID: {default_assignment.id}")
    print(f"  Policy ID: {default_assignment.policy_id}")
    print(f"  Is default: {default_assignment.metadata.get('is_default')}")
    
    # Get effective policies for a target
    print("\n2. Getting effective policies for 'local-backup'...")
    effective = manager.get_effective_policies(
        target_type=TargetType.REPOSITORY,
        target_id="local-backup",
    )
    print(f"✓ Effective policies:")
    if effective['backup_policy']:
        print(f"  Backup: {effective['backup_policy'].name}")
    else:
        print(f"  Backup: None")
    if effective['retention_policy']:
        print(f"  Retention: {effective['retention_policy'].name}")
    else:
        print(f"  Retention: None")


def demo_policy_deletion(manager: PolicyManager, duplicated_backup, duplicated_retention):
    """Demonstrate policy deletion."""
    print_section("Policy Deletion")
    
    # Delete duplicated policies (they have no assignments)
    print("1. Deleting duplicated backup policy...")
    result = manager.delete_backup_policy(duplicated_backup.id)
    print(f"✓ Deleted backup policy: {duplicated_backup.name}")
    
    print("\n2. Deleting duplicated retention policy...")
    result = manager.delete_retention_policy(duplicated_retention.id)
    print(f"✓ Deleted retention policy: {duplicated_retention.name}")
    
    # Try to delete a policy with assignments (should fail without force)
    print("\n3. Attempting to delete policy with assignments...")
    try:
        # This should fail because the policy has assignments
        manager.delete_backup_policy(manager.list_backup_policies()[0].id)
        print("✗ Unexpected: deletion succeeded")
    except Exception as e:
        print(f"✓ Deletion prevented (as expected): {type(e).__name__}")
        print(f"  Message: {str(e)}")


def demo_policy_statistics(manager: PolicyManager):
    """Display policy statistics."""
    print_section("Policy Statistics")
    
    backup_policies = manager.list_backup_policies()
    retention_policies = manager.list_retention_policies()
    assignments = manager.get_policy_assignments()
    active_assignments = manager.get_policy_assignments(active_only=True)
    
    print(f"Total backup policies: {len(backup_policies)}")
    print(f"  Active: {len([p for p in backup_policies if p.status == PolicyStatus.ACTIVE])}")
    print(f"  Draft: {len([p for p in backup_policies if p.status == PolicyStatus.DRAFT])}")
    
    print(f"\nTotal retention policies: {len(retention_policies)}")
    print(f"  Active: {len([p for p in retention_policies if p.status == PolicyStatus.ACTIVE])}")
    print(f"  Draft: {len([p for p in retention_policies if p.status == PolicyStatus.DRAFT])}")
    
    print(f"\nTotal policy assignments: {len(assignments)}")
    print(f"  Active: {len(active_assignments)}")
    print(f"  Inactive: {len(assignments) - len(active_assignments)}")
    
    # Count assignments by type
    backup_assignments = [a for a in assignments if a.policy_type == PolicyType.BACKUP]
    retention_assignments = [a for a in assignments if a.policy_type == PolicyType.RETENTION]
    print(f"\nAssignments by type:")
    print(f"  Backup: {len(backup_assignments)}")
    print(f"  Retention: {len(retention_assignments)}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  Policy Manager Demonstration")
    print("=" * 70)
    
    try:
        # Create policies
        manager, backup_policy, retention_policy = demo_policy_creation()
        
        # CRUD operations
        demo_policy_crud(manager, backup_policy, retention_policy)
        
        # Policy assignment
        assignment1, assignment2 = demo_policy_assignment(
            manager, backup_policy, retention_policy
        )
        
        # Templates and duplication
        duplicated_backup, duplicated_retention = demo_policy_templates(
            manager, backup_policy, retention_policy
        )
        
        # Default policies
        demo_default_policies(manager)
        
        # Policy deletion
        demo_policy_deletion(manager, duplicated_backup, duplicated_retention)
        
        # Statistics
        demo_policy_statistics(manager)
        
        print_section("Demonstration Complete")
        print("✓ All PolicyManager operations demonstrated successfully")
        
    except Exception as e:
        print(f"\n✗ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
