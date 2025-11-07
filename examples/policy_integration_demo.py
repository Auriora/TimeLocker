#!/usr/bin/env python3
"""
Policy Integration Demo

This example demonstrates how policy management integrates with existing
TimeLocker services including repository service, backup orchestrator,
and monitoring infrastructure.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_repository_service_integration():
    """Demonstrate policy enforcement through repository service."""
    print("\n" + "=" * 80)
    print("REPOSITORY SERVICE INTEGRATION DEMO")
    print("=" * 80 + "\n")
    
    from TimeLocker.policy import (
        PolicyManager,
        PolicyEngine,
        RetentionPolicy,
        RetentionRule,
        RetentionType,
        PolicyStatus,
    )
    from TimeLocker.policy.integration import PolicyIntegrationService
    from TimeLocker.monitoring.status_reporter import StatusReporter
    
    # Initialize components
    print("1. Initializing policy management components...")
    policy_manager = PolicyManager()
    policy_engine = PolicyEngine()
    status_reporter = StatusReporter()
    
    # Create policy integration service
    integration_service = PolicyIntegrationService(
        policy_manager=policy_manager,
        policy_engine=policy_engine,
        status_reporter=status_reporter,
    )
    
    print("   ✓ Policy integration service initialized\n")
    
    # Create a retention policy
    print("2. Creating retention policy...")
    retention_policy = policy_manager.create_retention_policy(
        name="Standard Retention",
        description="Standard retention policy for production repositories",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=10),
            RetentionRule(type=RetentionType.DAILY, count=7),
            RetentionRule(type=RetentionType.WEEKLY, count=4),
            RetentionRule(type=RetentionType.MONTHLY, count=6),
        ],
        status=PolicyStatus.ACTIVE,
    )
    print(f"   ✓ Created retention policy: {retention_policy.name} (ID: {retention_policy.id})\n")
    
    # Simulate repository service integration
    print("3. Repository Service Integration:")
    print("   - Repository service can now enforce policies via policy_integration_service")
    print("   - Method: repository_service.enforce_policy(repository, policy_id, dry_run)")
    print("   - This delegates to PolicyIntegrationService.enforce_retention_policy_on_repository()")
    print("   - Status updates are sent to monitoring infrastructure\n")
    
    # Show what happens during enforcement
    print("4. Policy Enforcement Flow:")
    print("   a) Repository service receives enforce_policy() call")
    print("   b) Delegates to PolicyIntegrationService")
    print("   c) Integration service:")
    print("      - Starts monitoring operation")
    print("      - Gets effective retention policy for repository")
    print("      - Retrieves snapshots from repository")
    print("      - Evaluates retention rules via PolicyEngine")
    print("      - Prunes snapshots according to policy")
    print("      - Creates enforcement record for audit trail")
    print("      - Reports status to monitoring infrastructure")
    print("   d) Returns enforcement results\n")


def demo_backup_orchestrator_integration():
    """Demonstrate policy-driven backups through backup orchestrator."""
    print("\n" + "=" * 80)
    print("BACKUP ORCHESTRATOR INTEGRATION DEMO")
    print("=" * 80 + "\n")
    
    from TimeLocker.policy import (
        PolicyManager,
        BackupPolicy,
        ScheduleConfig,
        PolicyStatus,
    )
    from TimeLocker.policy.integration import PolicyIntegrationService
    
    # Initialize components
    print("1. Initializing policy management components...")
    policy_manager = PolicyManager()
    integration_service = PolicyIntegrationService(
        policy_manager=policy_manager,
        policy_engine=None,  # Not needed for this demo
    )
    
    print("   ✓ Policy integration service initialized\n")
    
    # Create a backup policy
    print("2. Creating backup policy...")
    backup_policy = policy_manager.create_backup_policy(
        name="Daily Production Backup",
        description="Daily backup of production data",
        data_selection_refs=["production-data", "config-files"],
        target_repositories=["prod-repo-1", "prod-repo-2"],
        backup_tool="restic",
        schedule=ScheduleConfig(
            cron_expression="0 2 * * *",  # Daily at 2 AM
            enabled=True,
        ),
        tags={"environment": "production", "schedule": "daily"},
        status=PolicyStatus.ACTIVE,
    )
    print(f"   ✓ Created backup policy: {backup_policy.name} (ID: {backup_policy.id})\n")
    
    # Simulate backup orchestrator integration
    print("3. Backup Orchestrator Integration:")
    print("   - Orchestrator can execute policy-driven backups")
    print("   - Method: orchestrator.execute_policy_driven_backup(policy_id, dry_run)")
    print("   - This delegates to PolicyIntegrationService.execute_policy_driven_backup()")
    print("   - Backups are executed according to policy configuration\n")
    
    # Show what happens during policy-driven backup
    print("4. Policy-Driven Backup Flow:")
    print("   a) Backup orchestrator receives execute_policy_driven_backup() call")
    print("   b) Delegates to PolicyIntegrationService")
    print("   c) Integration service:")
    print("      - Retrieves backup policy configuration")
    print("      - Validates policy status (must be ACTIVE)")
    print("      - Executes backup for each target repository")
    print("      - Uses policy's data_selection_refs as backup targets")
    print("      - Applies policy tags to backup snapshots")
    print("      - Optionally enforces retention policy after backup")
    print("   d) Returns backup results for all repositories\n")


def demo_monitoring_integration():
    """Demonstrate policy compliance tracking through monitoring."""
    print("\n" + "=" * 80)
    print("MONITORING INTEGRATION DEMO")
    print("=" * 80 + "\n")
    
    from TimeLocker.policy import (
        PolicyManager,
        PolicyType,
        TargetType,
        RetentionPolicy,
        RetentionRule,
        RetentionType,
        PolicyStatus,
    )
    from TimeLocker.policy.integration import PolicyIntegrationService
    from TimeLocker.monitoring.status_reporter import StatusReporter
    
    # Initialize components
    print("1. Initializing monitoring and policy components...")
    policy_manager = PolicyManager()
    status_reporter = StatusReporter()
    integration_service = PolicyIntegrationService(
        policy_manager=policy_manager,
        policy_engine=None,
        status_reporter=status_reporter,
    )
    
    print("   ✓ Components initialized\n")
    
    # Create and assign a retention policy
    print("2. Creating and assigning retention policy...")
    retention_policy = policy_manager.create_retention_policy(
        name="Compliance Retention",
        description="Retention policy for compliance requirements",
        rules=[
            RetentionRule(type=RetentionType.DAILY, count=30),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    # Assign to a repository
    assignment = policy_manager.assign_policy(
        policy_id=retention_policy.id,
        policy_type=PolicyType.RETENTION,
        target_type=TargetType.REPOSITORY,
        target_id="compliance-repo",
        active=True,
    )
    
    print(f"   ✓ Created and assigned retention policy to 'compliance-repo'\n")
    
    # Report compliance status
    print("3. Reporting Policy Compliance Status:")
    compliance_status = integration_service.report_policy_compliance_status(
        target_type=TargetType.REPOSITORY,
        target_id="compliance-repo",
    )
    
    print(f"   Target: {compliance_status['target_id']}")
    print(f"   Compliant: {compliance_status['compliant']}")
    if compliance_status.get('retention_policy'):
        print(f"   Retention Policy: {compliance_status['retention_policy']['name']}")
    if compliance_status.get('warnings'):
        print(f"   Warnings: {len(compliance_status['warnings'])}")
        for warning in compliance_status['warnings']:
            print(f"     - {warning}")
    print()
    
    # Get policy status summary
    print("4. Policy Status Summary:")
    summary = integration_service.get_policy_status_summary()
    
    print(f"   Backup Policies: {summary['backup_policies']['total']}")
    print(f"   Retention Policies: {summary['retention_policies']['total']}")
    print(f"   Active Assignments: {summary['assignments']['active']}")
    print()
    
    # Show monitoring integration features
    print("5. Monitoring Integration Features:")
    print("   - Policy compliance status reporting")
    print("   - Enforcement operation tracking")
    print("   - Policy status summaries for dashboards")
    print("   - Historical compliance data")
    print("   - Integration with StatusReporter for unified monitoring\n")
    
    # Show status reporter policy methods
    print("6. StatusReporter Policy Methods:")
    print("   - report_policy_status(policy_id, target_id, compliance_status, details)")
    print("   - get_policy_compliance_history(policy_id, target_id, days)")
    print("   - These integrate policy compliance into existing monitoring infrastructure\n")


def demo_end_to_end_integration():
    """Demonstrate end-to-end policy management integration."""
    print("\n" + "=" * 80)
    print("END-TO-END INTEGRATION DEMO")
    print("=" * 80 + "\n")
    
    from TimeLocker.policy import (
        PolicyManager,
        PolicyEngine,
        BackupPolicy,
        RetentionPolicy,
        RetentionRule,
        RetentionType,
        PolicyType,
        TargetType,
        PolicyStatus,
    )
    from TimeLocker.policy.integration import PolicyIntegrationService
    from TimeLocker.monitoring.status_reporter import StatusReporter
    
    # Initialize all components
    print("1. Initializing complete policy management system...")
    policy_manager = PolicyManager()
    policy_engine = PolicyEngine()
    status_reporter = StatusReporter()
    
    integration_service = PolicyIntegrationService(
        policy_manager=policy_manager,
        policy_engine=policy_engine,
        status_reporter=status_reporter,
    )
    
    print("   ✓ All components initialized\n")
    
    # Create comprehensive backup policy
    print("2. Creating comprehensive backup policy...")
    
    # First create retention policy
    retention_policy = policy_manager.create_retention_policy(
        name="Production Retention",
        description="Retention policy for production backups",
        rules=[
            RetentionRule(type=RetentionType.LAST, count=5),
            RetentionRule(type=RetentionType.DAILY, count=14),
            RetentionRule(type=RetentionType.WEEKLY, count=8),
            RetentionRule(type=RetentionType.MONTHLY, count=12),
        ],
        status=PolicyStatus.ACTIVE,
    )
    
    # Create backup policy with retention
    backup_policy = policy_manager.create_backup_policy(
        name="Production Backup Policy",
        description="Complete backup policy for production environment",
        data_selection_refs=["app-data", "databases", "configs"],
        target_repositories=["primary-repo", "backup-repo"],
        backup_tool="restic",
        retention_policy_id=retention_policy.id,
        tags={"environment": "production"},
        status=PolicyStatus.ACTIVE,
    )
    
    print(f"   ✓ Created backup policy with retention: {backup_policy.name}\n")
    
    # Assign policies to repositories
    print("3. Assigning policies to repositories...")
    
    for repo in ["primary-repo", "backup-repo"]:
        assignment = policy_manager.assign_policy(
            policy_id=retention_policy.id,
            policy_type=PolicyType.RETENTION,
            target_type=TargetType.REPOSITORY,
            target_id=repo,
            active=True,
        )
        print(f"   ✓ Assigned retention policy to {repo}")
    
    print()
    
    # Show complete integration workflow
    print("4. Complete Integration Workflow:")
    print("\n   A. Policy-Driven Backup:")
    print("      1. Backup orchestrator executes policy-driven backup")
    print("      2. Integration service retrieves backup policy")
    print("      3. Backup executed for all target repositories")
    print("      4. Snapshots tagged according to policy")
    print("      5. Status reported to monitoring")
    
    print("\n   B. Automatic Retention Enforcement:")
    print("      1. After backup completes, retention policy enforced")
    print("      2. Integration service gets effective retention policy")
    print("      3. Policy engine evaluates snapshots")
    print("      4. Old snapshots pruned according to rules")
    print("      5. Enforcement record created for audit")
    print("      6. Status reported to monitoring")
    
    print("\n   C. Compliance Monitoring:")
    print("      1. Integration service reports compliance status")
    print("      2. Monitoring tracks policy enforcement history")
    print("      3. Dashboards show policy status summaries")
    print("      4. Alerts triggered for compliance violations")
    
    print("\n   D. Repository Operations:")
    print("      1. Repository service supports policy enforcement")
    print("      2. Can enforce policies on-demand or scheduled")
    print("      3. Integrates with existing repository operations")
    print("      4. Performance tracking via performance module")
    
    print()
    
    # Show integration benefits
    print("5. Integration Benefits:")
    print("   ✓ Unified policy management across all services")
    print("   ✓ Consistent enforcement through integration layer")
    print("   ✓ Comprehensive monitoring and audit trails")
    print("   ✓ Policy-driven automation of backup operations")
    print("   ✓ Compliance tracking and reporting")
    print("   ✓ Minimal changes to existing service interfaces")
    print()


def main():
    """Run all integration demos."""
    print("\n" + "=" * 80)
    print("POLICY MANAGEMENT INTEGRATION DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo shows how policy management integrates with existing")
    print("TimeLocker services for unified backup and retention management.")
    
    try:
        # Run individual demos
        demo_repository_service_integration()
        demo_backup_orchestrator_integration()
        demo_monitoring_integration()
        demo_end_to_end_integration()
        
        print("\n" + "=" * 80)
        print("INTEGRATION DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")
        
        print("Key Integration Points:")
        print("  1. Repository Service: enforce_policy() method")
        print("  2. Backup Orchestrator: execute_policy_driven_backup() method")
        print("  3. Status Reporter: report_policy_status() and compliance tracking")
        print("  4. Policy Integration Service: Central coordination layer")
        print("\nAll services now support policy-driven operations!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
