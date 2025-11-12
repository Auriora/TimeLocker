#!/usr/bin/env python3
"""
Compliance Reporting Demo

This example demonstrates the compliance reporting capabilities of the
Scheduling & Automation system, including:
- Generating compliance reports
- Analyzing schedule adherence
- Detecting violations
- Exporting compliance data
- Policy-specific compliance summaries

Copyright © Bruce Cherrington
Licensed under GNU General Public License v3.0
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.scheduling.schedule_manager import ScheduleManager
from TimeLocker.scheduling.scheduling_configuration import SchedulingConfiguration
from TimeLocker.scheduling.scheduling_models import (
    ScheduleRequest,
    SchedulePattern,
    SchedulePatternType,
    CalendarConfig
)


async def demo_compliance_reporting():
    """Demonstrate compliance reporting capabilities."""
    
    print("=" * 80)
    print("Compliance Reporting Demo")
    print("=" * 80)
    print()
    
    # Initialize schedule manager
    config_dir = Path.home() / ".timelocker" / "demo" / "compliance"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config = SchedulingConfiguration()
    manager = ScheduleManager(config=config, config_dir=config_dir)
    
    print("✓ Schedule manager initialized")
    print()
    
    # Create some demo schedules for testing
    print("Creating demo schedules...")
    print("-" * 80)
    
    schedules = []
    
    # Schedule 1: Daily backup
    schedule1 = ScheduleRequest(
        name="Daily Database Backup",
        description="Daily backup of production database",
        policy_id="policy-db-prod",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.CALENDAR,
            calendar_config=CalendarConfig(
                days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
                time_of_day=datetime.strptime("02:00", "%H:%M").time()
            )
        ),
        enabled=True
    )
    
    try:
        result1 = await manager.create_scheduled_backup(schedule1)
        schedules.append(result1.schedule_id)
        print(f"✓ Created schedule: {schedule1.name}")
        print(f"  Schedule ID: {result1.schedule_id}")
    except Exception as e:
        print(f"✗ Failed to create schedule: {e}")
    
    # Schedule 2: Weekly backup
    schedule2 = ScheduleRequest(
        name="Weekly Full Backup",
        description="Weekly full system backup",
        policy_id="policy-full-weekly",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.CALENDAR,
            calendar_config=CalendarConfig(
                days_of_week=[6],  # Sunday
                time_of_day=datetime.strptime("01:00", "%H:%M").time()
            )
        ),
        enabled=True
    )
    
    try:
        result2 = await manager.create_scheduled_backup(schedule2)
        schedules.append(result2.schedule_id)
        print(f"✓ Created schedule: {schedule2.name}")
        print(f"  Schedule ID: {result2.schedule_id}")
    except Exception as e:
        print(f"✗ Failed to create schedule: {e}")
    
    print()
    
    # Get audit statistics
    print("Audit Statistics")
    print("-" * 80)
    
    stats = manager.get_audit_statistics()
    print(f"Total audit entries: {stats.get('total_entries', 0)}")
    print(f"Total log files: {stats.get('log_files', 0)}")
    print(f"Total size: {stats.get('total_size_bytes', 0):,} bytes")
    print(f"Retention period: {stats.get('retention_days', 0)} days")
    
    if stats.get('oldest_entry'):
        print(f"Oldest entry: {stats['oldest_entry']}")
    if stats.get('newest_entry'):
        print(f"Newest entry: {stats['newest_entry']}")
    
    if stats.get('event_type_counts'):
        print("\nEvent type distribution:")
        for event_type, count in stats['event_type_counts'].items():
            print(f"  {event_type}: {count}")
    
    print()
    
    # Generate compliance report
    print("Generating Compliance Report")
    print("-" * 80)
    
    # Report for last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    try:
        report = manager.generate_compliance_report(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"Report ID: {report.report_id}")
        print(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Period: {report.report_period_start.strftime('%Y-%m-%d')} to {report.report_period_end.strftime('%Y-%m-%d')}")
        print()
        
        print("Summary:")
        print(f"  Total schedules: {report.total_schedules}")
        print(f"  Compliant: {report.compliant_schedules}")
        print(f"  Warnings: {report.warning_schedules}")
        print(f"  Violations: {report.violation_schedules}")
        print(f"  Total violations: {report.total_violations}")
        print(f"  Compliance rate: {report.summary.get('compliance_rate', 0):.1f}%")
        print()
        
        # Show schedule details
        if report.schedule_statuses:
            print("Schedule Status Details:")
            for status in report.schedule_statuses:
                print(f"\n  Schedule: {status.schedule_name} ({status.schedule_id})")
                print(f"    Policy: {status.policy_id}")
                print(f"    Status: {status.compliance_status.value.upper()}")
                print(f"    Violations: {len(status.violations)}")
                print(f"    Failed executions: {status.failed_executions}")
                print(f"    Missed executions: {status.missed_executions}")
                
                if status.last_successful_execution:
                    print(f"    Last success: {status.last_successful_execution.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"    Last success: Never")
                
                if status.violations:
                    print(f"    Violation details:")
                    for violation in status.violations:
                        print(f"      - {violation.violation_type.value}: {violation.description}")
                        print(f"        Severity: {violation.severity}")
        
        print()
        
        # Show summary details
        if report.summary.get('most_common_violations'):
            print("Most Common Violations:")
            for violation in report.summary['most_common_violations']:
                print(f"  {violation['type']}: {violation['count']} occurrences")
            print()
        
        if report.summary.get('schedules_needing_attention'):
            print("Schedules Needing Attention:")
            for schedule in report.summary['schedules_needing_attention'][:5]:
                print(f"  {schedule['schedule_name']} ({schedule['schedule_id']})")
                print(f"    Status: {schedule['compliance_status']}")
                print(f"    Violations: {schedule['violation_count']}")
            print()
        
        # Export report to JSON
        json_output = config_dir / "compliance_report.json"
        if manager.export_compliance_report(report, json_output, format='json'):
            print(f"✓ Exported compliance report to: {json_output}")
        
        # Export report to HTML
        html_output = config_dir / "compliance_report.html"
        if manager.export_compliance_report(report, html_output, format='html'):
            print(f"✓ Exported compliance report to: {html_output}")
        
        print()
        
    except Exception as e:
        print(f"✗ Failed to generate compliance report: {e}")
        import traceback
        traceback.print_exc()
    
    # Get policy-specific compliance
    print("Policy-Specific Compliance")
    print("-" * 80)
    
    for policy_id in ["policy-db-prod", "policy-full-weekly"]:
        try:
            summary = manager.get_policy_compliance_summary(policy_id)
            
            if 'error' in summary:
                print(f"Policy {policy_id}: Error - {summary['error']}")
            elif summary.get('schedule_count', 0) == 0:
                print(f"Policy {policy_id}: No schedules found")
            else:
                print(f"\nPolicy: {policy_id}")
                print(f"  Schedules: {summary['schedule_count']}")
                print(f"  Compliant: {summary['compliant_count']}")
                print(f"  Warnings: {summary['warning_count']}")
                print(f"  Violations: {summary['violation_count']}")
                print(f"  Compliance rate: {summary['compliance_rate']:.1f}%")
                print(f"  Total violations: {summary['total_violations']}")
                
                if summary.get('schedules'):
                    print(f"  Schedule details:")
                    for sched in summary['schedules']:
                        print(f"    - {sched['schedule_name']}: {sched['compliance_status']}")
        
        except Exception as e:
            print(f"✗ Failed to get policy compliance: {e}")
    
    print()
    
    # Export audit trail
    print("Exporting Audit Trail")
    print("-" * 80)
    
    audit_output = config_dir / "audit_trail.json"
    try:
        if manager.export_audit_trail(
            audit_output,
            start_date=start_date,
            end_date=end_date
        ):
            print(f"✓ Exported audit trail to: {audit_output}")
        else:
            print(f"✗ Failed to export audit trail")
    except Exception as e:
        print(f"✗ Failed to export audit trail: {e}")
    
    print()
    
    # Cleanup demo schedules
    print("Cleaning up demo schedules...")
    print("-" * 80)
    
    for schedule_id in schedules:
        try:
            await manager.delete_scheduled_backup(schedule_id)
            print(f"✓ Deleted schedule: {schedule_id}")
        except Exception as e:
            print(f"✗ Failed to delete schedule {schedule_id}: {e}")
    
    print()
    print("=" * 80)
    print("Demo completed!")
    print("=" * 80)


def main():
    """Run the demo."""
    try:
        asyncio.run(demo_compliance_reporting())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
