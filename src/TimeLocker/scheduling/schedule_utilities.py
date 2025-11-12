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

Schedule Management Utilities

This module provides utilities for schedule conflict detection,
automatic rescheduling, and schedule optimization.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .scheduling_models import (
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    BackupWindow,
    CalendarConfig
)
from .scheduling_exceptions import SchedulingError, ScheduleConflictError

logger = logging.getLogger(__name__)


class ConflictSeverity(Enum):
    """Severity level of schedule conflicts."""
    LOW = "low"  # Minor overlap, unlikely to cause issues
    MEDIUM = "medium"  # Moderate overlap, may cause resource contention
    HIGH = "high"  # Significant overlap, likely to cause issues
    CRITICAL = "critical"  # Complete overlap, will definitely cause issues


@dataclass
class ScheduleConflict:
    """
    Represents a conflict between two schedules.
    """
    schedule_id_1: str
    schedule_id_2: str
    conflict_type: str
    severity: ConflictSeverity
    description: str
    estimated_overlap_minutes: int
    suggested_resolution: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictResolution:
    """
    Represents a resolution for a schedule conflict.
    """
    conflict: ScheduleConflict
    resolution_type: str  # 'reschedule', 'adjust_window', 'increase_resources', 'accept'
    new_schedule_pattern: Optional[SchedulePattern] = None
    new_backup_window: Optional[BackupWindow] = None
    estimated_improvement: float = 0.0  # 0.0 to 1.0
    description: str = ""


@dataclass
class ScheduleOptimization:
    """
    Represents an optimization suggestion for schedules.
    """
    schedule_id: str
    optimization_type: str
    current_value: Any
    suggested_value: Any
    expected_benefit: str
    estimated_improvement: float  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)


class ScheduleConflictDetector:
    """
    Detects conflicts between scheduled backups.
    
    Analyzes schedule patterns, backup windows, and resource requirements
    to identify potential conflicts.
    """
    
    def __init__(self, max_concurrent_executions: int = 3):
        """
        Initialize conflict detector.
        
        Args:
            max_concurrent_executions: Maximum number of concurrent backup executions
        """
        self.max_concurrent_executions = max_concurrent_executions
        self.logger = logging.getLogger(f"{__name__}.ScheduleConflictDetector")
    
    def detect_conflicts(
        self,
        schedules: List[ScheduleConfig],
        time_window_hours: int = 24
    ) -> List[ScheduleConflict]:
        """
        Detect conflicts between schedules.
        
        Args:
            schedules: List of schedule configurations
            time_window_hours: Time window to analyze for conflicts
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Only check enabled schedules
        enabled_schedules = [s for s in schedules if s.enabled]
        
        if len(enabled_schedules) < 2:
            return conflicts
        
        # Calculate next run times for all schedules
        schedule_runs = []
        for schedule in enabled_schedules:
            try:
                next_runs = self._calculate_next_runs(schedule, time_window_hours)
                schedule_runs.append((schedule, next_runs))
            except Exception as e:
                self.logger.warning(f"Failed to calculate runs for schedule {schedule.schedule_id}: {e}")
                continue
        
        # Check for overlaps
        for i, (schedule1, runs1) in enumerate(schedule_runs):
            for schedule2, runs2 in schedule_runs[i+1:]:
                conflict = self._check_schedule_overlap(
                    schedule1, runs1,
                    schedule2, runs2
                )
                if conflict:
                    conflicts.append(conflict)
        
        # Check for resource conflicts
        resource_conflicts = self._check_resource_conflicts(schedule_runs)
        conflicts.extend(resource_conflicts)
        
        self.logger.info(f"Detected {len(conflicts)} schedule conflicts")
        return conflicts
    
    def _calculate_next_runs(
        self,
        schedule: ScheduleConfig,
        hours: int
    ) -> List[Tuple[datetime, datetime]]:
        """
        Calculate next run times for a schedule.
        
        Args:
            schedule: Schedule configuration
            hours: Number of hours to calculate
            
        Returns:
            List of (start_time, end_time) tuples
        """
        runs = []
        current_time = datetime.utcnow()
        end_time = current_time + timedelta(hours=hours)
        
        # Estimate execution duration (default to 30 minutes if not specified)
        execution_duration = timedelta(minutes=schedule.execution_timeout or 30)
        
        pattern = schedule.schedule_pattern
        
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            # Calculate interval-based runs
            interval = timedelta(minutes=pattern.interval_minutes)
            next_run = current_time
            
            while next_run < end_time:
                run_end = next_run + execution_duration
                runs.append((next_run, run_end))
                next_run += interval
        
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            # Calculate calendar-based runs (simplified)
            # In a real implementation, this would use croniter or similar
            if pattern.calendar_config:
                # For now, assume daily at specified time
                next_run = current_time.replace(
                    hour=pattern.calendar_config.time_of_day.hour,
                    minute=pattern.calendar_config.time_of_day.minute,
                    second=0,
                    microsecond=0
                )
                
                if next_run < current_time:
                    next_run += timedelta(days=1)
                
                while next_run < end_time:
                    run_end = next_run + execution_duration
                    runs.append((next_run, run_end))
                    next_run += timedelta(days=1)
        
        elif pattern.pattern_type == SchedulePatternType.CRON:
            # For cron expressions, we'd use croniter
            # For now, simplified implementation
            self.logger.debug(f"Cron pattern calculation not fully implemented for {schedule.schedule_id}")
        
        return runs
    
    def _check_schedule_overlap(
        self,
        schedule1: ScheduleConfig,
        runs1: List[Tuple[datetime, datetime]],
        schedule2: ScheduleConfig,
        runs2: List[Tuple[datetime, datetime]]
    ) -> Optional[ScheduleConflict]:
        """
        Check if two schedules have overlapping execution times.
        
        Args:
            schedule1: First schedule
            runs1: Calculated runs for first schedule
            schedule2: Second schedule
            runs2: Calculated runs for second schedule
            
        Returns:
            ScheduleConflict if overlap detected, None otherwise
        """
        total_overlap_minutes = 0
        overlap_count = 0
        
        for start1, end1 in runs1:
            for start2, end2 in runs2:
                # Check for overlap
                overlap_start = max(start1, start2)
                overlap_end = min(end1, end2)
                
                if overlap_start < overlap_end:
                    overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
                    total_overlap_minutes += overlap_duration
                    overlap_count += 1
        
        if overlap_count == 0:
            return None
        
        # Determine severity based on overlap
        avg_overlap = total_overlap_minutes / overlap_count
        
        if avg_overlap < 5:
            severity = ConflictSeverity.LOW
        elif avg_overlap < 15:
            severity = ConflictSeverity.MEDIUM
        elif avg_overlap < 30:
            severity = ConflictSeverity.HIGH
        else:
            severity = ConflictSeverity.CRITICAL
        
        return ScheduleConflict(
            schedule_id_1=schedule1.schedule_id,
            schedule_id_2=schedule2.schedule_id,
            conflict_type="time_overlap",
            severity=severity,
            description=f"Schedules overlap {overlap_count} times in analysis window",
            estimated_overlap_minutes=int(total_overlap_minutes),
            suggested_resolution=self._suggest_overlap_resolution(schedule1, schedule2, severity),
            details={
                'overlap_count': overlap_count,
                'average_overlap_minutes': avg_overlap,
                'schedule1_name': schedule1.name,
                'schedule2_name': schedule2.name
            }
        )
    
    def _check_resource_conflicts(
        self,
        schedule_runs: List[Tuple[ScheduleConfig, List[Tuple[datetime, datetime]]]]
    ) -> List[ScheduleConflict]:
        """
        Check for resource conflicts (too many concurrent executions).
        
        Args:
            schedule_runs: List of schedules with their calculated runs
            
        Returns:
            List of resource conflicts
        """
        conflicts = []
        
        # Build timeline of concurrent executions
        timeline = []
        for schedule, runs in schedule_runs:
            for start, end in runs:
                timeline.append(('start', start, schedule))
                timeline.append(('end', end, schedule))
        
        # Sort by time
        timeline.sort(key=lambda x: x[1])
        
        # Track concurrent executions
        concurrent = []
        max_concurrent_seen = 0
        conflict_periods = []
        
        for event_type, event_time, schedule in timeline:
            if event_type == 'start':
                concurrent.append(schedule)
                if len(concurrent) > max_concurrent_seen:
                    max_concurrent_seen = len(concurrent)
                
                if len(concurrent) > self.max_concurrent_executions:
                    conflict_periods.append((event_time, list(concurrent)))
            else:
                if schedule in concurrent:
                    concurrent.remove(schedule)
        
        # Create conflicts for resource contention
        if conflict_periods:
            # Group by involved schedules
            schedule_groups = {}
            for time, schedules in conflict_periods:
                schedule_ids = tuple(sorted(s.schedule_id for s in schedules))
                if schedule_ids not in schedule_groups:
                    schedule_groups[schedule_ids] = []
                schedule_groups[schedule_ids].append(time)
            
            for schedule_ids, times in schedule_groups.items():
                if len(schedule_ids) >= 2:
                    conflicts.append(ScheduleConflict(
                        schedule_id_1=schedule_ids[0],
                        schedule_id_2=schedule_ids[1],
                        conflict_type="resource_contention",
                        severity=ConflictSeverity.HIGH if len(times) > 5 else ConflictSeverity.MEDIUM,
                        description=f"Resource contention: {len(schedule_ids)} schedules exceed max concurrent limit",
                        estimated_overlap_minutes=len(times) * 5,  # Estimate
                        suggested_resolution="Adjust schedule times to reduce concurrent executions or increase max_concurrent_executions",
                        details={
                            'concurrent_count': len(schedule_ids),
                            'max_allowed': self.max_concurrent_executions,
                            'conflict_count': len(times),
                            'all_schedule_ids': list(schedule_ids)
                        }
                    ))
        
        return conflicts
    
    def _suggest_overlap_resolution(
        self,
        schedule1: ScheduleConfig,
        schedule2: ScheduleConfig,
        severity: ConflictSeverity
    ) -> str:
        """
        Suggest resolution for schedule overlap.
        
        Args:
            schedule1: First schedule
            schedule2: Second schedule
            severity: Conflict severity
            
        Returns:
            Suggested resolution description
        """
        if severity == ConflictSeverity.LOW:
            return "Monitor for performance impact; no immediate action required"
        elif severity == ConflictSeverity.MEDIUM:
            return "Consider adjusting schedule times or adding randomized delays"
        elif severity == ConflictSeverity.HIGH:
            return "Reschedule one backup to different time window"
        else:  # CRITICAL
            return "Immediate rescheduling required to prevent backup failures"


class AutomaticRescheduler:
    """
    Provides automatic rescheduling capabilities for conflicting schedules.
    
    Analyzes conflicts and generates optimized schedule adjustments.
    """
    
    def __init__(self, conflict_detector: ScheduleConflictDetector):
        """
        Initialize automatic rescheduler.
        
        Args:
            conflict_detector: Conflict detector instance
        """
        self.conflict_detector = conflict_detector
        self.logger = logging.getLogger(f"{__name__}.AutomaticRescheduler")
    
    def resolve_conflicts(
        self,
        schedules: List[ScheduleConfig],
        conflicts: List[ScheduleConflict]
    ) -> List[ConflictResolution]:
        """
        Generate resolutions for detected conflicts.
        
        Args:
            schedules: List of schedule configurations
            conflicts: List of detected conflicts
            
        Returns:
            List of proposed conflict resolutions
        """
        resolutions = []
        
        # Group conflicts by severity
        critical_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
        high_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
        
        # Resolve critical conflicts first
        for conflict in critical_conflicts:
            resolution = self._resolve_critical_conflict(conflict, schedules)
            if resolution:
                resolutions.append(resolution)
        
        # Then resolve high severity conflicts
        for conflict in high_conflicts:
            resolution = self._resolve_high_conflict(conflict, schedules)
            if resolution:
                resolutions.append(resolution)
        
        self.logger.info(f"Generated {len(resolutions)} conflict resolutions")
        return resolutions
    
    def _resolve_critical_conflict(
        self,
        conflict: ScheduleConflict,
        schedules: List[ScheduleConfig]
    ) -> Optional[ConflictResolution]:
        """
        Resolve a critical conflict.
        
        Args:
            conflict: Conflict to resolve
            schedules: All schedules
            
        Returns:
            ConflictResolution if resolution found
        """
        # Find the schedules involved
        schedule1 = next((s for s in schedules if s.schedule_id == conflict.schedule_id_1), None)
        schedule2 = next((s for s in schedules if s.schedule_id == conflict.schedule_id_2), None)
        
        if not schedule1 or not schedule2:
            return None
        
        # Try to reschedule the one with more flexible pattern
        if self._is_more_flexible(schedule1, schedule2):
            new_pattern = self._adjust_schedule_pattern(schedule1, schedule2)
            if new_pattern:
                return ConflictResolution(
                    conflict=conflict,
                    resolution_type='reschedule',
                    new_schedule_pattern=new_pattern,
                    estimated_improvement=0.9,
                    description=f"Reschedule {schedule1.name} to avoid conflict with {schedule2.name}"
                )
        else:
            new_pattern = self._adjust_schedule_pattern(schedule2, schedule1)
            if new_pattern:
                return ConflictResolution(
                    conflict=conflict,
                    resolution_type='reschedule',
                    new_schedule_pattern=new_pattern,
                    estimated_improvement=0.9,
                    description=f"Reschedule {schedule2.name} to avoid conflict with {schedule1.name}"
                )
        
        return None
    
    def _resolve_high_conflict(
        self,
        conflict: ScheduleConflict,
        schedules: List[ScheduleConfig]
    ) -> Optional[ConflictResolution]:
        """
        Resolve a high severity conflict.
        
        Args:
            conflict: Conflict to resolve
            schedules: All schedules
            
        Returns:
            ConflictResolution if resolution found
        """
        # For high conflicts, try adding randomized delays first
        schedule = next((s for s in schedules if s.schedule_id == conflict.schedule_id_1), None)
        
        if schedule and schedule.schedule_pattern.randomize_delay_minutes < 15:
            new_pattern = SchedulePattern(
                pattern_type=schedule.schedule_pattern.pattern_type,
                cron_expression=schedule.schedule_pattern.cron_expression,
                interval_minutes=schedule.schedule_pattern.interval_minutes,
                calendar_config=schedule.schedule_pattern.calendar_config,
                randomize_delay_minutes=15,
                backup_window=schedule.schedule_pattern.backup_window
            )
            
            return ConflictResolution(
                conflict=conflict,
                resolution_type='adjust_window',
                new_schedule_pattern=new_pattern,
                estimated_improvement=0.6,
                description=f"Add 15-minute randomized delay to {schedule.name}"
            )
        
        return None
    
    def _is_more_flexible(
        self,
        schedule1: ScheduleConfig,
        schedule2: ScheduleConfig
    ) -> bool:
        """
        Determine which schedule is more flexible for rescheduling.
        
        Args:
            schedule1: First schedule
            schedule2: Second schedule
            
        Returns:
            True if schedule1 is more flexible
        """
        # Interval-based schedules are most flexible
        if schedule1.schedule_pattern.pattern_type == SchedulePatternType.INTERVAL:
            if schedule2.schedule_pattern.pattern_type != SchedulePatternType.INTERVAL:
                return True
        
        # Calendar-based are more flexible than cron
        if schedule1.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            if schedule2.schedule_pattern.pattern_type == SchedulePatternType.CRON:
                return True
        
        return False
    
    def _adjust_schedule_pattern(
        self,
        schedule_to_adjust: ScheduleConfig,
        conflicting_schedule: ScheduleConfig
    ) -> Optional[SchedulePattern]:
        """
        Adjust schedule pattern to avoid conflict.
        
        Args:
            schedule_to_adjust: Schedule to modify
            conflicting_schedule: Schedule to avoid
            
        Returns:
            New SchedulePattern if adjustment possible
        """
        pattern = schedule_to_adjust.schedule_pattern
        
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            # Adjust interval slightly
            new_interval = pattern.interval_minutes + 30
            return SchedulePattern(
                pattern_type=pattern.pattern_type,
                interval_minutes=new_interval,
                randomize_delay_minutes=pattern.randomize_delay_minutes,
                backup_window=pattern.backup_window
            )
        
        elif pattern.pattern_type == SchedulePatternType.CALENDAR and pattern.calendar_config:
            # Adjust time of day
            current_time = pattern.calendar_config.time_of_day
            new_hour = (current_time.hour + 2) % 24
            
            from datetime import time
            new_time = time(hour=new_hour, minute=current_time.minute)
            
            new_calendar_config = CalendarConfig(
                days_of_week=pattern.calendar_config.days_of_week,
                time_of_day=new_time,
                weeks_of_month=pattern.calendar_config.weeks_of_month,
                months_of_year=pattern.calendar_config.months_of_year
            )
            
            return SchedulePattern(
                pattern_type=pattern.pattern_type,
                calendar_config=new_calendar_config,
                randomize_delay_minutes=pattern.randomize_delay_minutes,
                backup_window=pattern.backup_window
            )
        
        return None
    
    def apply_resolution(
        self,
        schedule: ScheduleConfig,
        resolution: ConflictResolution
    ) -> ScheduleConfig:
        """
        Apply a conflict resolution to a schedule.
        
        Args:
            schedule: Schedule to modify
            resolution: Resolution to apply
            
        Returns:
            Modified ScheduleConfig
        """
        if resolution.new_schedule_pattern:
            schedule.schedule_pattern = resolution.new_schedule_pattern
        
        if resolution.new_backup_window:
            schedule.schedule_pattern.backup_window = resolution.new_backup_window
        
        schedule.updated_at = datetime.utcnow()
        
        self.logger.info(f"Applied resolution to schedule {schedule.schedule_id}: {resolution.description}")
        return schedule


class ScheduleOptimizer:
    """
    Optimizes schedules for resource usage and load distribution.
    
    Analyzes schedule patterns and suggests optimizations to improve
    system performance and backup reliability.
    """
    
    def __init__(self):
        """Initialize schedule optimizer."""
        self.logger = logging.getLogger(f"{__name__}.ScheduleOptimizer")
    
    def analyze_schedules(
        self,
        schedules: List[ScheduleConfig]
    ) -> List[ScheduleOptimization]:
        """
        Analyze schedules and suggest optimizations.
        
        Args:
            schedules: List of schedule configurations
            
        Returns:
            List of optimization suggestions
        """
        optimizations = []
        
        for schedule in schedules:
            if not schedule.enabled:
                continue
            
            # Check for load distribution opportunities
            load_opt = self._check_load_distribution(schedule, schedules)
            if load_opt:
                optimizations.append(load_opt)
            
            # Check for resource usage optimizations
            resource_opt = self._check_resource_usage(schedule)
            if resource_opt:
                optimizations.append(resource_opt)
            
            # Check for timing optimizations
            timing_opt = self._check_timing_optimization(schedule)
            if timing_opt:
                optimizations.append(timing_opt)
        
        self.logger.info(f"Generated {len(optimizations)} optimization suggestions")
        return optimizations
    
    def _check_load_distribution(
        self,
        schedule: ScheduleConfig,
        all_schedules: List[ScheduleConfig]
    ) -> Optional[ScheduleOptimization]:
        """
        Check if schedule could benefit from better load distribution.
        
        Args:
            schedule: Schedule to analyze
            all_schedules: All schedules for context
            
        Returns:
            ScheduleOptimization if improvement possible
        """
        # If no randomized delay, suggest adding one
        if schedule.schedule_pattern.randomize_delay_minutes == 0:
            return ScheduleOptimization(
                schedule_id=schedule.schedule_id,
                optimization_type="load_distribution",
                current_value=0,
                suggested_value=10,
                expected_benefit="Distribute load and reduce resource contention",
                estimated_improvement=0.3,
                details={
                    'schedule_name': schedule.name,
                    'suggestion': 'Add 10-minute randomized delay'
                }
            )
        
        return None
    
    def _check_resource_usage(
        self,
        schedule: ScheduleConfig
    ) -> Optional[ScheduleOptimization]:
        """
        Check if schedule could use resources more efficiently.
        
        Args:
            schedule: Schedule to analyze
            
        Returns:
            ScheduleOptimization if improvement possible
        """
        # Check if execution timeout is too long
        if schedule.execution_timeout and schedule.execution_timeout > 7200:  # 2 hours
            return ScheduleOptimization(
                schedule_id=schedule.schedule_id,
                optimization_type="resource_usage",
                current_value=schedule.execution_timeout,
                suggested_value=3600,
                expected_benefit="Reduce resource lock time and improve responsiveness",
                estimated_improvement=0.2,
                details={
                    'schedule_name': schedule.name,
                    'suggestion': 'Reduce execution timeout to 1 hour'
                }
            )
        
        return None
    
    def _check_timing_optimization(
        self,
        schedule: ScheduleConfig
    ) -> Optional[ScheduleOptimization]:
        """
        Check if schedule timing could be optimized.
        
        Args:
            schedule: Schedule to analyze
            
        Returns:
            ScheduleOptimization if improvement possible
        """
        pattern = schedule.schedule_pattern
        
        # For interval-based schedules, check if interval is too frequent
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            if pattern.interval_minutes and pattern.interval_minutes < 60:
                return ScheduleOptimization(
                    schedule_id=schedule.schedule_id,
                    optimization_type="timing",
                    current_value=pattern.interval_minutes,
                    suggested_value=60,
                    expected_benefit="Reduce backup frequency to improve system performance",
                    estimated_improvement=0.4,
                    details={
                        'schedule_name': schedule.name,
                        'suggestion': 'Increase interval to at least 60 minutes'
                    }
                )
        
        return None
    
    def optimize_schedule_distribution(
        self,
        schedules: List[ScheduleConfig],
        time_window_hours: int = 24
    ) -> List[ScheduleConfig]:
        """
        Optimize distribution of schedules across time window.
        
        Args:
            schedules: List of schedules to optimize
            time_window_hours: Time window for distribution
            
        Returns:
            List of optimized schedules
        """
        if not schedules:
            return schedules
        
        # Calculate ideal spacing
        enabled_schedules = [s for s in schedules if s.enabled]
        if len(enabled_schedules) < 2:
            return schedules
        
        ideal_spacing_minutes = (time_window_hours * 60) // len(enabled_schedules)
        
        # Adjust calendar-based schedules
        optimized = []
        current_offset = 0
        
        for schedule in schedules:
            if not schedule.enabled:
                optimized.append(schedule)
                continue
            
            pattern = schedule.schedule_pattern
            
            if pattern.pattern_type == SchedulePatternType.CALENDAR and pattern.calendar_config:
                # Adjust time of day to distribute load
                from datetime import time
                offset_hours = current_offset // 60
                offset_minutes = current_offset % 60
                
                new_time = time(hour=offset_hours % 24, minute=offset_minutes)
                
                new_calendar_config = CalendarConfig(
                    days_of_week=pattern.calendar_config.days_of_week,
                    time_of_day=new_time,
                    weeks_of_month=pattern.calendar_config.weeks_of_month,
                    months_of_year=pattern.calendar_config.months_of_year
                )
                
                schedule.schedule_pattern = SchedulePattern(
                    pattern_type=pattern.pattern_type,
                    calendar_config=new_calendar_config,
                    randomize_delay_minutes=pattern.randomize_delay_minutes,
                    backup_window=pattern.backup_window
                )
                
                current_offset += ideal_spacing_minutes
            
            optimized.append(schedule)
        
        self.logger.info(f"Optimized distribution for {len(enabled_schedules)} schedules")
        return optimized
