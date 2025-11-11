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

Launchd Adapter

This module provides launchd integration for macOS systems.
"""

import asyncio
import plistlib
import re
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .platform_adapter import PlatformAdapter
from .scheduling_models import (
    ScheduleConfig,
    SchedulePatternType,
    PlatformScheduleResult,
    PlatformScheduleStatus,
    PlatformScheduleInfo,
    ValidationResult
)
from .scheduling_exceptions import PlatformSchedulerError


class LaunchdAdapter(PlatformAdapter):
    """
    Launchd adapter for macOS.
    
    This adapter creates and manages launchd plists for scheduled
    backup operations.
    
    Features:
    - Launchd plist generation and management
    - launchctl command integration for job control
    - Wrapper script generation for proper execution
    - macOS-specific scheduling and status monitoring
    """
    
    def __init__(self):
        """Initialize launchd adapter."""
        super().__init__()
        self.launchd_dir = Path.home() / "Library" / "LaunchAgents"
        self.launchd_dir.mkdir(parents=True, exist_ok=True)
        self.script_dir = Path.home() / "Library" / "Application Support" / "TimeLocker" / "Scripts"
        self.script_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path.home() / "Library" / "Logs" / "TimeLocker"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Create launchd plist and wrapper script.
        
        Args:
            config: Schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule creation
            
        Raises:
            PlatformSchedulerError: If schedule creation fails
        """
        try:
            self.logger.info(f"Creating launchd schedule for {config.schedule_id}")
            
            # Validate configuration
            validation = self.validate_schedule_config(config)
            if not validation.is_valid:
                raise PlatformSchedulerError(
                    f"Invalid schedule configuration: {', '.join(validation.errors)}"
                )
            
            # Generate wrapper script
            script_path = await self._generate_wrapper_script(config)
            
            # Generate plist
            plist_content = self._generate_plist(config, script_path)
            plist_file = self.launchd_dir / f"com.timelocker.backup.{config.schedule_id}.plist"
            
            # Write plist file
            with open(plist_file, 'wb') as f:
                plistlib.dump(plist_content, f)
            
            self.logger.debug(f"Created plist file: {plist_file}")
            
            # Load launchd job if enabled
            if config.enabled:
                await self._load_launchd_job(plist_file)
            
            # Calculate next run time
            next_run = self._calculate_next_launchd_run(config.schedule_pattern)
            
            platform_id = plist_file.stem
            self._log_operation("create", config.schedule_id, True, f"Platform ID: {platform_id}")
            
            return PlatformScheduleResult(
                success=True,
                platform_id=platform_id,
                next_run=next_run
            )
            
        except Exception as e:
            self._log_operation("create", config.schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to create launchd schedule: {e}",
                details={"schedule_id": config.schedule_id}
            ) from e
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Update an existing launchd job.
        
        Args:
            schedule_id: Unique identifier for the schedule
            config: Updated schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule update
            
        Raises:
            PlatformSchedulerError: If schedule update fails
        """
        try:
            self.logger.info(f"Updating launchd schedule {schedule_id}")
            
            # Unload existing job
            plist_file = self.launchd_dir / f"com.timelocker.backup.{schedule_id}.plist"
            if plist_file.exists():
                try:
                    await self._unload_launchd_job(plist_file)
                except PlatformSchedulerError:
                    self.logger.warning(f"Could not unload existing job {plist_file}")
            
            # Create new schedule
            result = await self.create_schedule(config)
            
            self._log_operation("update", schedule_id, True)
            return result
            
        except Exception as e:
            self._log_operation("update", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to update launchd schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Remove a launchd job.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            PlatformSchedulerError: If schedule deletion fails
        """
        try:
            self.logger.info(f"Deleting launchd schedule {schedule_id}")
            
            # Unload job
            plist_file = self.launchd_dir / f"com.timelocker.backup.{schedule_id}.plist"
            if plist_file.exists():
                try:
                    await self._unload_launchd_job(plist_file)
                except PlatformSchedulerError:
                    self.logger.warning(f"Job {plist_file} was not loaded")
                
                # Remove plist file
                plist_file.unlink()
            
            # Remove wrapper script
            script_path = self.script_dir / f"timelocker-{schedule_id}.sh"
            if script_path.exists():
                script_path.unlink()
            
            self._log_operation("delete", schedule_id, True)
            return True
            
        except Exception as e:
            self._log_operation("delete", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to delete launchd schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """
        Get launchd job status.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            PlatformScheduleStatus: Current status of the schedule
            
        Raises:
            PlatformSchedulerError: If status retrieval fails
        """
        try:
            platform_id = f"com.timelocker.backup.{schedule_id}"
            
            # Check if job is loaded
            is_active = await self._is_job_loaded(platform_id)
            
            # Get last run time from log
            last_run = await self._get_last_run_time(schedule_id)
            
            # Calculate next run time
            plist_file = self.launchd_dir / f"{platform_id}.plist"
            next_run = None
            if plist_file.exists():
                with open(plist_file, 'rb') as f:
                    plist_data = plistlib.load(f)
                next_run = self._calculate_next_run_from_plist(plist_data)
            
            return PlatformScheduleStatus(
                platform_id=platform_id,
                is_active=is_active,
                last_run_time=last_run,
                next_run_time=next_run
            )
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to get launchd schedule status: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """
        List all launchd jobs.
        
        Returns:
            List[PlatformScheduleInfo]: List of all scheduled tasks
            
        Raises:
            PlatformSchedulerError: If listing fails
        """
        try:
            schedules = []
            
            # Find all TimeLocker plist files
            for plist_file in self.launchd_dir.glob("com.timelocker.backup.*.plist"):
                # Extract schedule_id from filename
                match = re.match(r"com\.timelocker\.backup\.(.+)\.plist", plist_file.name)
                if not match:
                    continue
                
                schedule_id = match.group(1)
                platform_id = plist_file.stem
                
                # Check if job is loaded
                is_active = await self._is_job_loaded(platform_id)
                
                # Calculate next run time
                with open(plist_file, 'rb') as f:
                    plist_data = plistlib.load(f)
                next_run = self._calculate_next_run_from_plist(plist_data)
                
                schedules.append(PlatformScheduleInfo(
                    platform_id=platform_id,
                    schedule_id=schedule_id,
                    is_active=is_active,
                    next_run_time=next_run
                ))
            
            return schedules
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to list launchd schedules: {e}"
            ) from e
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration for launchd compatibility.
        
        Args:
            config: Schedule configuration to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Validate required fields
        if not config.schedule_id:
            result.add_error("schedule_id is required")
        
        if not config.policy_id:
            result.add_error("policy_id is required")
        
        # Validate schedule_id format (must be valid for plist names)
        if config.schedule_id and not re.match(r'^[a-zA-Z0-9_-]+$', config.schedule_id):
            result.add_error("schedule_id must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate schedule pattern
        if config.schedule_pattern.pattern_type == SchedulePatternType.CRON:
            result.add_warning("CRON pattern type will be converted to launchd format")
        elif config.schedule_pattern.pattern_type == SchedulePatternType.INTERVAL:
            if not config.schedule_pattern.interval_minutes:
                result.add_error("interval_minutes is required for INTERVAL pattern type")
            elif config.schedule_pattern.interval_minutes < 1:
                result.add_error("interval_minutes must be at least 1")
        elif config.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            if not config.schedule_pattern.calendar_config:
                result.add_error("calendar_config is required for CALENDAR pattern type")
        
        # Validate execution timeout
        if config.execution_timeout and config.execution_timeout < 60:
            result.add_warning("execution_timeout less than 60 seconds may be too short for backup operations")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "launchd"
    
    # Private helper methods
    
    async def _generate_wrapper_script(self, config: ScheduleConfig) -> Path:
        """
        Generate wrapper script for launchd execution.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated script
        """
        script_path = self.script_dir / f"timelocker-{config.schedule_id}.sh"
        log_file = self.log_dir / f"timelocker-{config.schedule_id}.log"
        
        timeout = config.execution_timeout or 3600
        
        script_content = f"""#!/bin/bash
# TimeLocker Scheduled Backup Wrapper Script
# Schedule ID: {config.schedule_id}
# Policy ID: {config.policy_id}
# Generated: {datetime.utcnow().isoformat()}

set -e

# Logging
LOG_FILE="{log_file}"
exec >> "$LOG_FILE" 2>&1

echo "=== TimeLocker Backup Execution Started: $(date) ==="
echo "Schedule ID: {config.schedule_id}"
echo "Policy ID: {config.policy_id}"

# Set timeout
TIMEOUT={timeout}

# Execute backup with timeout
if timeout $TIMEOUT timelocker backup execute --policy-id {config.policy_id} --scheduled; then
    echo "=== Backup Completed Successfully: $(date) ==="
    exit 0
else
    EXIT_CODE=$?
    echo "=== Backup Failed with exit code $EXIT_CODE: $(date) ==="
    exit $EXIT_CODE
fi
"""
        
        # Write script
        script_path.write_text(script_content)
        
        # Make executable
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        self.logger.debug(f"Generated wrapper script: {script_path}")
        return script_path
    
    def _generate_plist(self, config: ScheduleConfig, script_path: Path) -> Dict[str, Any]:
        """
        Generate launchd plist dictionary.
        
        Args:
            config: Schedule configuration
            script_path: Path to wrapper script
            
        Returns:
            Dict[str, Any]: Plist dictionary
        """
        pattern = config.schedule_pattern
        
        # Base plist structure
        plist = {
            "Label": f"com.timelocker.backup.{config.schedule_id}",
            "ProgramArguments": [str(script_path)],
            "StandardOutPath": str(self.log_dir / f"timelocker-{config.schedule_id}.stdout.log"),
            "StandardErrorPath": str(self.log_dir / f"timelocker-{config.schedule_id}.stderr.log"),
            "RunAtLoad": False,
            "KeepAlive": False,
        }
        
        # Add scheduling based on pattern type
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            # Use StartInterval for interval-based scheduling
            plist["StartInterval"] = pattern.interval_minutes * 60
        
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            # Use StartCalendarInterval for calendar-based scheduling
            cal = pattern.calendar_config
            
            # Convert days of week (0=Mon to 6=Sun) to launchd format (0=Sun to 6=Sat)
            # Create multiple calendar intervals for each day
            calendar_intervals = []
            for day in cal.days_of_week:
                launchd_day = (day + 1) % 7
                calendar_intervals.append({
                    "Weekday": launchd_day,
                    "Hour": cal.time_of_day.hour,
                    "Minute": cal.time_of_day.minute
                })
            
            plist["StartCalendarInterval"] = calendar_intervals
        
        else:  # CRON
            # Convert cron to calendar interval
            calendar_interval = self._cron_to_calendar_interval(pattern.cron_expression)
            plist["StartCalendarInterval"] = calendar_interval
        
        # Add timeout if specified
        if config.execution_timeout:
            plist["TimeOut"] = config.execution_timeout
        
        # Add environment variables if needed
        plist["EnvironmentVariables"] = {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        }
        
        return plist
    
    def _cron_to_calendar_interval(self, cron_expression: str) -> Dict[str, int]:
        """
        Convert cron expression to launchd calendar interval.
        
        Args:
            cron_expression: Cron expression
            
        Returns:
            Dict[str, int]: Calendar interval dictionary
        """
        parts = cron_expression.split()
        if len(parts) < 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        minute, hour, day, month, weekday = parts[:5]
        
        interval = {}
        
        if minute.isdigit():
            interval["Minute"] = int(minute)
        if hour.isdigit():
            interval["Hour"] = int(hour)
        if day.isdigit():
            interval["Day"] = int(day)
        if month.isdigit():
            interval["Month"] = int(month)
        if weekday.isdigit():
            # Convert cron weekday (0=Sun) to launchd weekday (0=Sun)
            interval["Weekday"] = int(weekday)
        
        return interval
    
    def _calculate_next_launchd_run(self, pattern: Any) -> Optional[datetime]:
        """
        Calculate next run time for launchd schedule.
        
        Args:
            pattern: Schedule pattern
            
        Returns:
            Optional[datetime]: Next run time or None
        """
        now = datetime.now()
        
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            # Next run is interval minutes from now
            return now + timedelta(minutes=pattern.interval_minutes)
        
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            cal = pattern.calendar_config
            
            # Find next occurrence of the scheduled time
            target_time = cal.time_of_day
            next_run = now.replace(
                hour=target_time.hour,
                minute=target_time.minute,
                second=0,
                microsecond=0
            )
            
            # If time has passed today, move to next scheduled day
            if next_run <= now:
                next_run += timedelta(days=1)
            
            # Find next day that matches schedule
            while next_run.weekday() not in cal.days_of_week:
                next_run += timedelta(days=1)
            
            return next_run
        
        return None
    
    def _calculate_next_run_from_plist(self, plist_data: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate next run time from plist data.
        
        Args:
            plist_data: Plist dictionary
            
        Returns:
            Optional[datetime]: Next run time or None
        """
        now = datetime.now()
        
        if "StartInterval" in plist_data:
            # Interval-based scheduling
            interval_seconds = plist_data["StartInterval"]
            return now + timedelta(seconds=interval_seconds)
        
        elif "StartCalendarInterval" in plist_data:
            # Calendar-based scheduling
            intervals = plist_data["StartCalendarInterval"]
            if not isinstance(intervals, list):
                intervals = [intervals]
            
            # Find next occurrence
            next_runs = []
            for interval in intervals:
                next_run = now.replace(second=0, microsecond=0)
                
                if "Minute" in interval:
                    next_run = next_run.replace(minute=interval["Minute"])
                if "Hour" in interval:
                    next_run = next_run.replace(hour=interval["Hour"])
                
                # If time has passed, move to next occurrence
                if next_run <= now:
                    if "Weekday" in interval:
                        # Move to next week
                        next_run += timedelta(days=7)
                    else:
                        # Move to next day
                        next_run += timedelta(days=1)
                
                next_runs.append(next_run)
            
            return min(next_runs) if next_runs else None
        
        return None
    
    async def _launchctl_command(self, args: List[str]) -> str:
        """
        Execute launchctl command.
        
        Args:
            args: Command arguments
            
        Returns:
            str: Command output
            
        Raises:
            PlatformSchedulerError: If command fails
        """
        try:
            cmd = ["launchctl"] + args
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                raise PlatformSchedulerError(
                    f"launchctl command failed: {error_msg}",
                    details={"command": " ".join(cmd), "returncode": process.returncode}
                )
            
            return stdout.decode().strip()
            
        except FileNotFoundError:
            raise PlatformSchedulerError(
                "launchctl command not found - launchd may not be available"
            )
        except Exception as e:
            if isinstance(e, PlatformSchedulerError):
                raise
            raise PlatformSchedulerError(f"Failed to execute launchctl: {e}") from e
    
    async def _load_launchd_job(self, plist_file: Path) -> None:
        """
        Load launchd job.
        
        Args:
            plist_file: Path to plist file
        """
        await self._launchctl_command(["load", str(plist_file)])
        self.logger.debug(f"Loaded launchd job: {plist_file}")
    
    async def _unload_launchd_job(self, plist_file: Path) -> None:
        """
        Unload launchd job.
        
        Args:
            plist_file: Path to plist file
        """
        await self._launchctl_command(["unload", str(plist_file)])
        self.logger.debug(f"Unloaded launchd job: {plist_file}")
    
    async def _is_job_loaded(self, label: str) -> bool:
        """
        Check if a launchd job is loaded.
        
        Args:
            label: Job label
            
        Returns:
            bool: True if job is loaded
        """
        try:
            output = await self._launchctl_command(["list"])
            return label in output
        except PlatformSchedulerError:
            return False
    
    async def _get_last_run_time(self, schedule_id: str) -> Optional[datetime]:
        """
        Get last run time from log file.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Optional[datetime]: Last run time or None
        """
        try:
            log_file = self.log_dir / f"timelocker-{schedule_id}.log"
            if not log_file.exists():
                return None
            
            # Read last few lines of log file
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Look for last "Started" timestamp
            for line in reversed(lines):
                if "Started:" in line:
                    # Extract timestamp
                    match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                    if match:
                        return datetime.strptime(match.group(), "%Y-%m-%d %H:%M:%S")
            
            return None
            
        except Exception:
            return None
