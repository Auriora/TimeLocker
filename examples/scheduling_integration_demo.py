#!/usr/bin/env python3
"""
Scheduling System Integration Demo

This script demonstrates the complete integration of the Scheduling & Automation
system with Policy Management, Monitoring & Reporting, and other TimeLocker systems.

Usage:
    python examples/scheduling_integration_demo.py
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_policy_integration():
    """Demonstrate Policy Management integration."""
    print("\n" + "=" * 80)
    print("Policy Management Integration Demo")
    print("=" * 80)
    
    try:
        from TimeLocker.scheduling import ScheduleManager
        
        # Create schedule manager
        manager = ScheduleManager()
        
        # List schedulable policies
        print("\n1. Listing schedulable policies...")
        policies = manager.policy_client.list_policies_for_scheduling()
        print(f"   Found {len(policies)} schedulable policies")
        
        if policies:
            policy = policies[0]
            print(f"   Example policy: {policy['name']} (ID: {policy['id']})")
            
            # Check policy compatibility
            print("\n2. Checking policy automation compatibility...")
            is_compatible, reasons = manager.policy_client.check_policy_compatibility_for_automation(
                policy['id']
            )
            print(f"   Compatible: {is_compatible}")
            if not is_compatible:
                print(f"   Reasons: {', '.join(reasons)}")
            
            # Get policy schedule requirements
            print("\n3. Getting policy schedule requirements...")
            requirements = manager.policy_client.get_policy_schedule_requirements(policy['id'])
            if requirements:
                print(f"   Requirements: {requirements}")
            
            # Get schedules using this policy
            print("\n4. Getting schedules for policy...")
            schedules = manager.get_schedules_by_policy(policy['id'])
            print(f"   Found {len(schedules)} schedules using this policy")
        
        print("\n✓ Policy Management integration working correctly")
        
    except Exception as e:
        print(f"\n✗ Error in Policy Management integration: {e}")
        logger.exception("Policy integration error")


async def demo_monitoring_integration():
    """Demonstrate Monitoring & Reporting integration."""
    print("\n" + "=" * 80)
    print("Monitoring & Reporting Integration Demo")
    print("=" * 80)
    
    try:
        from TimeLocker.scheduling import ScheduleManager
        
        # Create schedule manager
        manager = ScheduleManager()
        
        # Register health check webhook
        print("\n1. Registering health check webhook...")
        webhook_url = "https://example.com/health-check"
        manager.register_health_check_webhook(webhook_url)
        print(f"   Registered webhook: {webhook_url}")
        
        # Get schedule health summary
        print("\n2. Getting schedule health summary...")
        health_summary = await manager.get_schedule_health_summary()
        print(f"   Total schedules: {health_summary['total_schedules']}")
        print(f"   Enabled schedules: {health_summary['enabled_schedules']}")
        print(f"   Healthy schedules: {health_summary['healthy_schedules']}")
        print(f"   Platform: {health_summary['platform']}")
        
        # Report scheduling metrics
        print("\n3. Reporting scheduling metrics...")
        await manager.report_scheduling_metrics()
        print("   Metrics reported to monitoring system")
        
        # Get cached metrics
        print("\n4. Getting cached metrics...")
        cached_metrics = manager.monitoring_client.get_cached_metrics()
        if cached_metrics:
            print(f"   Cached metrics: {len(cached_metrics)} entries")
            print(f"   Last updated: {cached_metrics.get('last_updated', 'N/A')}")
        
        # Get next scheduled runs
        print("\n5. Getting next scheduled runs...")
        next_runs = await manager.get_next_scheduled_runs(limit=5)
        print(f"   Next {len(next_runs)} scheduled runs:")
        for run in next_runs:
            print(f"     - {run['schedule_name']}: {run['next_run_time']}")
        
        # Unregister webhook
        print("\n6. Unregistering health check webhook...")
        manager.unregister_health_check_webhook(webhook_url)
        print(f"   Unregistered webhook: {webhook_url}")
        
        print("\n✓ Monitoring & Reporting integration working correctly")
        
    except Exception as e:
        print(f"\n✗ Error in Monitoring integration: {e}")
        logger.exception("Monitoring integration error")


async def demo_integration_testing():
    """Demonstrate integration testing framework."""
    print("\n" + "=" * 80)
    print("Integration Testing Framework Demo")
    print("=" * 80)
    
    try:
        from TimeLocker.scheduling import SchedulingIntegrationTester
        
        # Create integration tester
        print("\n1. Creating integration tester...")
        tester = SchedulingIntegrationTester()
        print("   Integration tester created")
        
        # Run full test suite
        print("\n2. Running full integration test suite...")
        print("   (This may take a few moments...)")
        suite = await tester.run_full_integration_test_suite()
        
        # Display results
        print(f"\n3. Test Results:")
        print(f"   Total tests: {suite.total_tests}")
        print(f"   Passed: {suite.passed_tests}")
        print(f"   Failed: {suite.failed_tests}")
        print(f"   Success rate: {suite.success_rate:.1f}%")
        print(f"   Duration: {suite.total_duration.total_seconds():.2f}s")
        
        # Show individual test results
        print("\n4. Individual Test Results:")
        for result in suite.test_results:
            status = "✓" if result.success else "✗"
            print(f"   {status} {result.test_name} ({result.duration.total_seconds():.2f}s)")
            if result.errors:
                for error in result.errors:
                    print(f"      ERROR: {error}")
            if result.warnings:
                for warning in result.warnings:
                    print(f"      WARNING: {warning}")
        
        # Generate and display report
        print("\n5. Generating test report...")
        report = tester.generate_test_report(suite)
        print("\n" + report)
        
        # Export results
        print("\n6. Exporting test results...")
        output_file = Path("scheduling_integration_test_results.txt")
        success = tester.export_test_results(suite, output_file)
        if success:
            print(f"   Results exported to: {output_file}")
        
        print("\n✓ Integration testing framework working correctly")
        
    except Exception as e:
        print(f"\n✗ Error in integration testing: {e}")
        logger.exception("Integration testing error")


async def demo_schedule_monitoring():
    """Demonstrate schedule health monitoring."""
    print("\n" + "=" * 80)
    print("Schedule Health Monitoring Demo")
    print("=" * 80)
    
    try:
        from TimeLocker.scheduling import ScheduleManager
        
        # Create schedule manager
        manager = ScheduleManager()
        
        # List all schedules
        print("\n1. Listing all schedules...")
        schedules = await manager.list_scheduled_backups()
        print(f"   Found {len(schedules)} schedules")
        
        if schedules:
            # Monitor first schedule
            schedule = schedules[0]
            print(f"\n2. Monitoring schedule: {schedule.name}")
            await manager.monitor_schedule_health(schedule.schedule_id)
            print("   Health monitoring complete")
            
            # Get schedule status
            print("\n3. Getting schedule status...")
            status = await manager.get_schedule_status(schedule.schedule_id)
            print(f"   Enabled: {status.enabled}")
            print(f"   Health: {status.health_status.value}")
            if status.next_execution_time:
                print(f"   Next execution: {status.next_execution_time}")
        
        # Monitor all schedules
        print("\n4. Monitoring all schedules...")
        results = await manager.monitor_all_schedules()
        print(f"   Monitored: {results['monitored']}")
        print(f"   Healthy: {results['healthy']}")
        print(f"   Warning: {results['warning']}")
        print(f"   Error: {results['error']}")
        
        # Get conflict summary
        print("\n5. Getting conflict summary...")
        conflict_summary = manager.get_conflict_summary()
        print(f"   Total conflicts: {conflict_summary.get('total_conflicts', 0)}")
        print(f"   Critical: {conflict_summary.get('critical_conflicts', 0)}")
        print(f"   High: {conflict_summary.get('high_conflicts', 0)}")
        
        # Get optimization summary
        print("\n6. Getting optimization summary...")
        opt_summary = manager.get_optimization_summary()
        print(f"   Total optimizations: {opt_summary.get('total_optimizations', 0)}")
        print(f"   Load distribution: {opt_summary.get('load_distribution_opportunities', 0)}")
        print(f"   Resource usage: {opt_summary.get('resource_usage_opportunities', 0)}")
        
        print("\n✓ Schedule health monitoring working correctly")
        
    except Exception as e:
        print(f"\n✗ Error in schedule monitoring: {e}")
        logger.exception("Schedule monitoring error")


async def main():
    """Run all integration demos."""
    print("\n" + "=" * 80)
    print("TimeLocker Scheduling System Integration Demo")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all demos
    await demo_policy_integration()
    await demo_monitoring_integration()
    await demo_schedule_monitoring()
    await demo_integration_testing()
    
    print("\n" + "=" * 80)
    print("Demo Complete")
    print("=" * 80)
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nAll integration features demonstrated successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        logger.exception("Demo error")
