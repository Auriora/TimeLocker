#!/usr/bin/env python3
"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Schedule Utilities Demo

This example demonstrates the schedule management utilities including:
- Conflict detection between schedules
- Automatic conflict resolution
- Schedule optimization
- Load distribution optimization
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.scheduling import (
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    CalendarConfig,
    RetryConfig,
    ScheduleConflictDetector,
    AutomaticRescheduler,
    ScheduleOptimizer,
    ConflictSeverity
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def create_sample_schedules():
    """Create sample schedules for demonstration."""
    schedules = []
    
    # Schedule 1: Daily backup at 2 AM
    schedule1 = ScheduleConfig(
        schedule_id="schedule-001",
        name="Daily Database Backup",
        description="Daily backup of production database",
        policy_id="policy-001",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.CALENDAR,
            calendar_config=CalendarConfig(
                days_of_week=[0, 1, 2, 3, 4, 5, 6],  # Every day
                time_of_day=time(hour=2, minute=0)
            )
        ),
        enabled=True,
        execution_timeout=1800,  # 30 minutes
        retry_config=RetryConfig()
    )
    schedules.append(schedule1)
    
    # Schedule 2: Daily backup at 2:15 AM (overlaps with schedule 1)
    schedule2 = ScheduleConfig(
        schedule_id="schedule-002",
        name="Daily File Backup",
        description="Daily backup of file server",
        policy_id="policy-002",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.CALENDAR,
            calendar_config=CalendarConfig(
                days_of_week=[0, 1, 2, 3, 4, 5, 6],
                time_of_day=time(hour=2, minute=15)
            )
        ),
        enabled=True,
        execution_timeout=2400,  # 40 minutes
        retry_config=RetryConfig()
    )
    schedules.append(schedule2)
    
    # Schedule 3: Hourly backup (very frequent)
    schedule3 = ScheduleConfig(
        schedule_id="schedule-003",
        name="Hourly Incremental Backup",
        description="Hourly incremental backup",
        policy_id="policy-003",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.INTERVAL,
            interval_minutes=30  # Every 30 minutes (too frequent)
        ),
        enabled=True,
        execution_timeout=600,  # 10 minutes
        retry_config=RetryConfig()
    )
    schedules.append(schedule3)
    
    # Schedule 4: Weekly backup at 2 AM Sunday (overlaps with schedule 1)
    schedule4 = ScheduleConfig(
        schedule_id="schedule-004",
        name="Weekly Full Backup",
        description="Weekly full system backup",
        policy_id="policy-004",
        schedule_pattern=SchedulePattern(
            pattern_type=SchedulePatternType.CALENDAR,
            calendar_config=CalendarConfig(
                days_of_week=[6],  # Sunday
                time_of_day=time(hour=2, minute=0)
            )
        ),
        enabled=True,
        execution_timeout=7200,  # 2 hours (very long)
        retry_config=RetryConfig()
    )
    schedules.append(schedule4)
    
    return schedules


def demo_conflict_detection():
    """Demonstrate schedule conflict detection."""
    print_section("Schedule Conflict Detection")
    
    schedules = create_sample_schedules()
    
    print(f"Analyzing {len(schedules)} schedules for conflicts...")
    print("\nSchedules:")
    for schedule in schedules:
        print(f"  - {schedule.name} ({schedule.schedule_id})")
        if schedule.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            print(f"    Time: {schedule.schedule_pattern.calendar_config.time_of_day}")
        elif schedule.schedule_pattern.pattern_type == SchedulePatternType.INTERVAL:
            print(f"    Interval: {schedule.schedule_pattern.interval_minutes} minutes")
    
    # Create conflict detector
    detector = ScheduleConflictDetector(max_concurrent_executions=3)
    
    # Detect conflicts
    conflicts = detector.detect_conflicts(schedules, time_window_hours=24)
    
    print(f"\n✓ Detected {len(conflicts)} conflicts")
    
    if conflicts:
        print("\nConflict Details:")
        for i, conflict in enumerate(conflicts, 1):
            print(f"\n  Conflict {i}:")
            print(f"    Type: {conflict.conflict_type}")
            print(f"    Severity: {conflict.severity.value.upper()}")
            print(f"    Schedules: {conflict.schedule_id_1} ↔ {conflict.schedule_id_2}")
            print(f"    Description: {conflict.description}")
            print(f"    Estimated Overlap: {conflict.estimated_overlap_minutes} minutes")
            print(f"    Suggested Resolution: {conflict.suggested_resolution}")


def demo_automatic_resolution():
    """Demonstrate automatic conflict resolution."""
    print_section("Automatic Conflict Resolution")
    
    schedules = create_sample_schedules()
    
    # Detect conflicts
    detector = ScheduleConflictDetector(max_concurrent_executions=3)
    conflicts = detector.detect_conflicts(schedules, time_window_hours=24)
    
    print(f"Found {len(conflicts)} conflicts to resolve")
    
    # Create automatic rescheduler
    rescheduler = AutomaticRescheduler(detector)
    
    # Generate resolutions
    resolutions = rescheduler.resolve_conflicts(schedules, conflicts)
    
    print(f"\n✓ Generated {len(resolutions)} resolutions")
    
    if resolutions:
        print("\nResolution Details:")
        for i, resolution in enumerate(resolutions, 1):
            print(f"\n  Resolution {i}:")
            print(f"    Type: {resolution.resolution_type}")
            print(f"    Description: {resolution.description}")
            print(f"    Estimated Improvement: {resolution.estimated_improvement * 100:.0f}%")
            
            if resolution.new_schedule_pattern:
                pattern = resolution.new_schedule_pattern
                print(f"    New Pattern:")
                if pattern.pattern_type == SchedulePatternType.CALENDAR and pattern.calendar_config:
                    print(f"      Time: {pattern.calendar_config.time_of_day}")
                elif pattern.pattern_type == SchedulePatternType.INTERVAL:
                    print(f"      Interval: {pattern.interval_minutes} minutes")
                if pattern.randomize_delay_minutes > 0:
                    print(f"      Randomized Delay: {pattern.randomize_delay_minutes} minutes")


def demo_schedule_optimization():
    """Demonstrate schedule optimization."""
    print_section("Schedule Optimization")
    
    schedules = create_sample_schedules()
    
    print(f"Analyzing {len(schedules)} schedules for optimization opportunities...")
    
    # Create optimizer
    optimizer = ScheduleOptimizer()
    
    # Analyze schedules
    optimizations = optimizer.analyze_schedules(schedules)
    
    print(f"\n✓ Found {len(optimizations)} optimization opportunities")
    
    if optimizations:
        print("\nOptimization Suggestions:")
        for i, opt in enumerate(optimizations, 1):
            print(f"\n  Optimization {i}:")
            print(f"    Schedule: {opt.schedule_id}")
            print(f"    Type: {opt.optimization_type}")
            print(f"    Current Value: {opt.current_value}")
            print(f"    Suggested Value: {opt.suggested_value}")
            print(f"    Expected Benefit: {opt.expected_benefit}")
            print(f"    Estimated Improvement: {opt.estimated_improvement * 100:.0f}%")


def demo_load_distribution():
    """Demonstrate load distribution optimization."""
    print_section("Load Distribution Optimization")
    
    schedules = create_sample_schedules()
    
    print(f"Optimizing distribution of {len(schedules)} schedules...")
    print("\nOriginal Schedule Times:")
    for schedule in schedules:
        if schedule.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            print(f"  {schedule.name}: {schedule.schedule_pattern.calendar_config.time_of_day}")
    
    # Create optimizer
    optimizer = ScheduleOptimizer()
    
    # Optimize distribution
    optimized_schedules = optimizer.optimize_schedule_distribution(schedules, time_window_hours=24)
    
    print("\n✓ Distribution optimized")
    print("\nOptimized Schedule Times:")
    for schedule in optimized_schedules:
        if schedule.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            print(f"  {schedule.name}: {schedule.schedule_pattern.calendar_config.time_of_day}")


def demo_severity_levels():
    """Demonstrate different conflict severity levels."""
    print_section("Conflict Severity Levels")
    
    print("Conflict Severity Levels:")
    print(f"  {ConflictSeverity.LOW.value.upper()}: Minor overlap, unlikely to cause issues")
    print(f"  {ConflictSeverity.MEDIUM.value.upper()}: Moderate overlap, may cause resource contention")
    print(f"  {ConflictSeverity.HIGH.value.upper()}: Significant overlap, likely to cause issues")
    print(f"  {ConflictSeverity.CRITICAL.value.upper()}: Complete overlap, will definitely cause issues")
    
    schedules = create_sample_schedules()
    detector = ScheduleConflictDetector(max_concurrent_executions=3)
    conflicts = detector.detect_conflicts(schedules, time_window_hours=24)
    
    # Count by severity
    severity_counts = {
        ConflictSeverity.LOW: 0,
        ConflictSeverity.MEDIUM: 0,
        ConflictSeverity.HIGH: 0,
        ConflictSeverity.CRITICAL: 0
    }
    
    for conflict in conflicts:
        severity_counts[conflict.severity] += 1
    
    print("\nDetected Conflicts by Severity:")
    for severity, count in severity_counts.items():
        if count > 0:
            print(f"  {severity.value.upper()}: {count}")


def demo_resolution_strategies():
    """Demonstrate different resolution strategies."""
    print_section("Resolution Strategies")
    
    print("Available Resolution Strategies:")
    print("  1. RESCHEDULE: Adjust schedule time to avoid conflict")
    print("  2. ADJUST_WINDOW: Add randomized delays to distribute load")
    print("  3. INCREASE_RESOURCES: Increase max concurrent executions")
    print("  4. ACCEPT: Accept conflict if severity is low")
    
    schedules = create_sample_schedules()
    detector = ScheduleConflictDetector(max_concurrent_executions=3)
    conflicts = detector.detect_conflicts(schedules, time_window_hours=24)
    
    rescheduler = AutomaticRescheduler(detector)
    resolutions = rescheduler.resolve_conflicts(schedules, conflicts)
    
    # Count by resolution type
    resolution_types = {}
    for resolution in resolutions:
        resolution_type = resolution.resolution_type
        resolution_types[resolution_type] = resolution_types.get(resolution_type, 0) + 1
    
    print("\nGenerated Resolutions by Type:")
    for res_type, count in resolution_types.items():
        print(f"  {res_type.upper()}: {count}")


def main():
    """Run all schedule utilities demos."""
    print("\n" + "=" * 70)
    print("  TimeLocker Schedule Management Utilities Demo")
    print("=" * 70)
    print(f"\nDemo Time: {datetime.utcnow().isoformat()}")
    
    try:
        # Run demos
        demo_conflict_detection()
        demo_automatic_resolution()
        demo_schedule_optimization()
        demo_load_distribution()
        demo_severity_levels()
        demo_resolution_strategies()
        
        print_section("Demo Complete")
        print("All schedule management utilities demonstrated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
