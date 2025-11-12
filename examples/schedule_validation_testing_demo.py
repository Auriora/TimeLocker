#!/usr/bin/env python3
"""
Schedule Validation and Testing Demo

This example demonstrates the validation and testing capabilities
of the TimeLocker Scheduling & Automation system.

Copyright © Bruce Cherrington
Licensed under GNU General Public License v3.0
"""

import asyncio
import sys
from pathlib import Path
from datetime import time

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.scheduling import (
    ScheduleManager,
    ScheduleRequest,
    SchedulePattern,
    SchedulePatternType,
    CalendarConfig,
    RetryConfig,
    MonitoringConfig,
    ScheduleValidator,
    ScheduleTester
)


async def demo_schedule_validation():
    """Demonstrate schedule validation capabilities."""
    print("=" * 80)
    print("Schedule Validation Demo")
    print("=" * 80)
    
    try:
        # Create schedule manager
        manager = ScheduleManager()
        
        # Create a test schedule configuration
        schedule_request = ScheduleRequest(
            name="Daily Backup Test",
            description="Test schedule for validation demo",
            policy_id="test-policy-001",
            schedule_pattern=SchedulePattern(
                pattern_type=SchedulePatternType.CALENDAR,
                calendar_config=CalendarConfig(
                    days_of_week=[0, 1, 2, 3, 4],  # Monday-Friday
                    time_of_day=time(2, 0)  # 2:00 AM
                ),
                randomize_delay_minutes=15
            ),
            enabled=True,
            execution_timeout=3600,
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay_minutes=5,
                backoff_multiplier=2.0,
                max_delay_minutes=60
            ),
            monitoring_config=MonitoringConfig(
                notification_on_success=True,
                notification_on_failure=True
            )
        )
        
        print("\n1. Creating schedule configuration...")
        print(f"   Name: {schedule_request.name}")
        print(f"   Policy ID: {schedule_request.policy_id}")
        print(f"   Pattern: {schedule_request.schedule_pattern.pattern_type.value}")
        
        # Note: This will fail validation because the policy doesn't exist
        # but it demonstrates the validation process
        print("\n2. Attempting to create schedule (will fail validation)...")
        try:
            result = await manager.create_scheduled_backup(schedule_request)
            print(f"   ✓ Schedule created: {result.schedule_id}")
        except Exception as e:
            print(f"   ✗ Validation failed (expected): {str(e)}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nError in validation demo: {e}")
        import traceback
        traceback.print_exc()


async def demo_schedule_testing():
    """Demonstrate schedule testing capabilities."""
    print("\n" + "=" * 80)
    print("Schedule Testing Demo")
    print("=" * 80)
    
    try:
        # Create schedule manager
        manager = ScheduleManager()
        
        print("\n1. Checking platform scheduler health...")
        health_result = await manager.check_platform_health()
        
        print(f"   Platform: {health_result.details.get('platform', 'unknown')}")
        print(f"   Status: {'✓ Healthy' if health_result.is_healthy else '✗ Unhealthy'}")
        
        if health_result.issues:
            print("   Issues:")
            for issue in health_result.issues:
                print(f"     - {issue}")
        
        if health_result.recommendations:
            print("   Recommendations:")
            for rec in health_result.recommendations:
                print(f"     - {rec}")
        
        print("\n2. Checking system resources...")
        resource_result = await manager.check_system_resources()
        
        print(f"   Status: {'✓ Healthy' if resource_result.is_healthy else '✗ Issues Found'}")
        print(f"   Disk Free: {resource_result.details.get('disk_free_gb', 'N/A')} GB")
        print(f"   Disk Usage: {resource_result.details.get('disk_usage_percent', 'N/A')}%")
        print(f"   TimeLocker: {resource_result.details.get('timelocker_executable', 'not found')}")
        
        if resource_result.issues:
            print("   Issues:")
            for issue in resource_result.issues:
                print(f"     - {issue}")
        
        if resource_result.recommendations:
            print("   Recommendations:")
            for rec in resource_result.recommendations:
                print(f"     - {rec}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nError in testing demo: {e}")
        import traceback
        traceback.print_exc()


async def demo_cron_validation():
    """Demonstrate cron expression validation."""
    print("\n" + "=" * 80)
    print("Cron Expression Validation Demo")
    print("=" * 80)
    
    try:
        from TimeLocker.scheduling import PlatformDetector
        
        # Detect platform adapter
        adapter_class = PlatformDetector.detect_best_scheduler()
        adapter = adapter_class()
        
        # Create validator
        validator = ScheduleValidator(platform_adapter=adapter)
        
        # Test various cron expressions
        test_expressions = [
            ("0 2 * * *", "Daily at 2:00 AM"),
            ("0 */6 * * *", "Every 6 hours"),
            ("0 0 * * 0", "Weekly on Sunday at midnight"),
            ("invalid", "Invalid expression"),
            ("0 2 * *", "Missing field (invalid)"),
        ]
        
        print("\nValidating cron expressions:")
        for expr, description in test_expressions:
            print(f"\n  Expression: {expr}")
            print(f"  Description: {description}")
            
            # Create a test schedule pattern
            from TimeLocker.scheduling.scheduling_models import ValidationResult
            result = ValidationResult(is_valid=True)
            
            try:
                validator._validate_cron_expression(expr, result)
                if result.is_valid:
                    print(f"  Status: ✓ Valid")
                else:
                    print(f"  Status: ✗ Invalid")
                    for error in result.errors:
                        print(f"    - {error}")
            except Exception as e:
                print(f"  Status: ✗ Error - {str(e)}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nError in cron validation demo: {e}")
        import traceback
        traceback.print_exc()


async def demo_health_summary():
    """Demonstrate schedule health summary."""
    print("\n" + "=" * 80)
    print("Schedule Health Summary Demo")
    print("=" * 80)
    
    try:
        # Create schedule manager
        manager = ScheduleManager()
        
        print("\n1. Getting schedule health summary...")
        summary = await manager.get_schedule_health_summary()
        
        print(f"\n   Total Schedules: {summary.get('total_schedules', 0)}")
        print(f"   Enabled: {summary.get('enabled_schedules', 0)}")
        print(f"   Disabled: {summary.get('disabled_schedules', 0)}")
        print(f"   Healthy: {summary.get('healthy_schedules', 0)}")
        print(f"   Warning: {summary.get('warning_schedules', 0)}")
        print(f"   Error: {summary.get('error_schedules', 0)}")
        print(f"   Platform: {summary.get('platform', 'unknown')}")
        
        print("\n2. Getting next scheduled runs...")
        next_runs = await manager.get_next_scheduled_runs(limit=5)
        
        if next_runs:
            print(f"\n   Next {len(next_runs)} scheduled runs:")
            for run in next_runs:
                print(f"     - {run['schedule_name']}: {run['next_run_time']}")
        else:
            print("\n   No scheduled runs found")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nError in health summary demo: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "TimeLocker Schedule Validation & Testing Demo" + " " * 13 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run demos
    await demo_schedule_validation()
    await demo_schedule_testing()
    await demo_cron_validation()
    await demo_health_summary()
    
    print("\n")
    print("Demo completed!")
    print("\nNote: Some operations may fail if TimeLocker is not fully configured.")
    print("This is expected and demonstrates the validation capabilities.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
