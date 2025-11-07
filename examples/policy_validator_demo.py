#!/usr/bin/env python3
"""
Policy Validator Demo

This script demonstrates the PolicyValidator component for validating
backup and retention policies, checking repository compatibility, and
validating policy assignments.
"""

from datetime import timedelta
from TimeLocker.policy import (
    PolicyValidator,
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    RetentionType,
    PolicyType,
    TargetType,
    PolicyStatus,
    ScheduleConfig,
    ComplianceRule,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_validation_result(result):
    """Print validation result details."""
    print(f"\n✓ Valid: {result.valid}")
    
    if result.issues:
        print("\nIssues:")
        for issue in result.issues:
            icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
            print(f"  {icon} [{issue.severity.upper()}] {issue.field}: {issue.message}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")


def print_compatibility_result(result):
    """Print compatibility result details."""
    print(f"\n✓ Compatible: {result.compatible}")
    
    if result.incompatibility_reasons:
        print("\nIncompatibility Reasons:")
        for reason in result.incompatibility_reasons:
            print(f"  ❌ {reason}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")


def demo_backup_policy_validation():
    """Demonstrate backup policy validation."""
    print_section("Backup Policy Validation")
    
    validator = PolicyValidator()
    
    # Example 1: Valid backup policy
    print("\n1. Validating a valid backup policy:")
    valid_policy = BackupPolicy(
        id="bp-001",
        name="Daily Home Backup",
        description="Daily backup of home directory",
        data_selection_refs=["home-selection"],
        target_repositories=["local-repo"],
        backup_tool="restic",
        schedule=ScheduleConfig(cron_expression="0 2 * * *"),
        status=PolicyStatus.ACTIVE,
    )
    
    try:
        result = validator.validate_backup_policy(valid_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 2: Invalid backup policy (missing required fields)
    print("\n2. Validating an invalid backup policy (missing fields):")
    invalid_policy = BackupPolicy(
        id="",  # Missing ID
        name="",  # Missing name
        description="Invalid policy",
        data_selection_refs=[],  # No data selections
        target_repositories=[],  # No repositories
        backup_tool="",  # Missing tool
    )
    
    try:
        result = validator.validate_backup_policy(invalid_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 3: Policy with unsupported backup tool
    print("\n3. Validating policy with unsupported backup tool:")
    unsupported_tool_policy = BackupPolicy(
        id="bp-003",
        name="Unsupported Tool Policy",
        description="Policy with unsupported tool",
        data_selection_refs=["home-selection"],
        target_repositories=["local-repo"],
        backup_tool="unsupported-tool",
    )
    
    try:
        result = validator.validate_backup_policy(unsupported_tool_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")


def demo_retention_policy_validation():
    """Demonstrate retention policy validation."""
    print_section("Retention Policy Validation")
    
    validator = PolicyValidator()
    
    # Example 1: Valid retention policy
    print("\n1. Validating a valid retention policy:")
    valid_policy = RetentionPolicy(
        id="rp-001",
        name="Standard Retention",
        description="Keep 7 daily, 4 weekly, 12 monthly snapshots",
        rules=[
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    try:
        result = validator.validate_retention_policy(valid_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 2: Invalid retention policy (no rules)
    print("\n2. Validating invalid retention policy (no rules):")
    no_rules_policy = RetentionPolicy(
        id="rp-002",
        name="No Rules Policy",
        description="Policy with no retention rules",
        rules=[],
    )
    
    try:
        result = validator.validate_retention_policy(no_rules_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 3: Policy with compliance period
    print("\n3. Validating policy with compliance requirements:")
    compliance_policy = RetentionPolicy(
        id="rp-003",
        name="Compliance Retention",
        description="Policy with compliance requirements",
        rules=[
            RetentionRule(
                type=RetentionType.DAILY,
                count=30,
                minimum_age=timedelta(days=1)
            ),
        ],
        compliance_period=timedelta(days=365),
        status=PolicyStatus.ACTIVE,
    )
    
    try:
        result = validator.validate_retention_policy(compliance_policy)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")


def demo_repository_compatibility():
    """Demonstrate repository compatibility checking."""
    print_section("Repository Compatibility Checking")
    
    validator = PolicyValidator()
    
    # Example 1: Compatible restic + S3 repository
    print("\n1. Checking restic policy with S3 repository:")
    restic_policy = BackupPolicy(
        id="bp-s3",
        name="S3 Backup",
        description="Backup to S3",
        data_selection_refs=["home-selection"],
        target_repositories=["s3-repo"],
        backup_tool="restic",
    )
    
    s3_repo_config = {
        'name': 's3-repo',
        'uri': 's3:s3.amazonaws.com/my-bucket',
        'enabled': True,
        'read_only': False,
        'password': 'secret',
    }
    
    try:
        result = validator.check_repository_compatibility(restic_policy, s3_repo_config)
        print_compatibility_result(result)
    except Exception as e:
        print(f"❌ Compatibility check failed: {e}")
    
    # Example 2: Incompatible borg + S3 repository
    print("\n2. Checking borg policy with S3 repository (incompatible):")
    borg_policy = BackupPolicy(
        id="bp-borg-s3",
        name="Borg S3 Backup",
        description="Borg backup to S3 (not supported)",
        data_selection_refs=["home-selection"],
        target_repositories=["s3-repo"],
        backup_tool="borg",
    )
    
    try:
        result = validator.check_repository_compatibility(borg_policy, s3_repo_config)
        print_compatibility_result(result)
    except Exception as e:
        print(f"❌ Compatibility check failed: {e}")
    
    # Example 3: Read-only repository
    print("\n3. Checking policy with read-only repository:")
    readonly_repo_config = {
        'name': 'readonly-repo',
        'uri': '/backup/readonly',
        'enabled': True,
        'read_only': True,
    }
    
    try:
        result = validator.check_repository_compatibility(restic_policy, readonly_repo_config)
        print_compatibility_result(result)
    except Exception as e:
        print(f"❌ Compatibility check failed: {e}")


def demo_policy_assignment_validation():
    """Demonstrate policy assignment validation."""
    print_section("Policy Assignment Validation")
    
    validator = PolicyValidator()
    
    # Example 1: Valid policy assignment
    print("\n1. Validating valid policy assignment:")
    valid_assignment = PolicyAssignment(
        id="pa-001",
        policy_id="bp-001",
        policy_type=PolicyType.BACKUP,
        target_type=TargetType.REPOSITORY,
        target_id="local-repo",
        priority=10,
        active=True,
    )
    
    try:
        result = validator.validate_policy_assignment(valid_assignment)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
    
    # Example 2: Invalid assignment (missing fields)
    print("\n2. Validating invalid assignment (missing fields):")
    invalid_assignment = PolicyAssignment(
        id="",  # Missing ID
        policy_id="",  # Missing policy ID
        policy_type=PolicyType.BACKUP,
        target_type=TargetType.REPOSITORY,
        target_id="",  # Missing target ID
    )
    
    try:
        result = validator.validate_policy_assignment(invalid_assignment)
        print_validation_result(result)
    except Exception as e:
        print(f"❌ Validation failed: {e}")


def demo_retention_compatibility():
    """Demonstrate retention policy compatibility with backup tools."""
    print_section("Retention Policy Compatibility")
    
    validator = PolicyValidator()
    
    # Example 1: Compatible retention policy with restic
    print("\n1. Checking retention policy compatibility with restic:")
    retention_policy = RetentionPolicy(
        id="rp-restic",
        name="Restic Retention",
        description="Standard retention for restic",
        rules=[
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
    )
    
    result = validator.validate_retention_compatibility(retention_policy, "restic")
    print_compatibility_result(result)
    
    # Example 2: Unsupported backup tool
    print("\n2. Checking retention policy with unsupported tool:")
    result = validator.validate_retention_compatibility(retention_policy, "unsupported-tool")
    print_compatibility_result(result)


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  Policy Validator Demonstration")
    print("=" * 70)
    
    demo_backup_policy_validation()
    demo_retention_policy_validation()
    demo_repository_compatibility()
    demo_policy_assignment_validation()
    demo_retention_compatibility()
    
    print("\n" + "=" * 70)
    print("  Demonstration Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
