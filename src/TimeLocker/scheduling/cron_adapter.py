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

Cron Adapter

This module provides cron integration for Unix-like systems.
"""

import asyncio
import re
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

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


class CronAdapter(PlatformAdapter):
    """
    Cron adapter for Unix-like systems.
    
    This adapter creates and manages cron jobs for scheduled backup operations.
    
    Features:
    - Cron job management with crontab manipulation
    - Cron expression validation and next-run calculation
    - Wrapper script generation for proper environment setup
    - Cron-specific logging and error handling
    """
    
    def __init__(self):
        """Initialize cron adapter."""
        super().__init__()
        self.cron_comment_prefix = "# TimeLocker Scheduled Backup"
        self.wrapper_script_dir = Path.home() / ".local" / "bin"
        self.wrapper_script_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path.home() / ".local" / "share" / "timelocker" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Create cron job and wrapper script.
        
        Args:
            config: Schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule creation
            
        Raises:
            PlatformSchedulerError: If schedule creation fails
        """
        try:
            self.logger.info(f"Creating cron schedule for {config.schedule_id}")
            
            # Validate configuration
            validation = self.validate_schedule_config(config)
            if not validation.is_valid:
                raise PlatformSchedulerError(
                    f"Invalid schedule configuration: {', '.join(validation.errors)}"
                )
            
            # Generate wrapper script
            script_path = await self._generate_wrapper_script(config)
            
            # Generate cron expression
            cron_expression = self._generate_cron_expression(config)
            
            # Add cron entry
            await self._add_cron_entry(config.schedule_id, cron_expression, script_path)
            
            # Calculate next run time
            next_run = self._calculate_next_cron_run(cron_expression)
            
            platform_id = f"cron-{config.schedule_id}"
            self._log_operation("create", config.schedule_id, True, f"Platform ID: {platform_id}")
            
            return PlatformScheduleResult(
                success=True,
                platform_id=platform_id,
                next_run=next_run,
                platform_specific_data={"cron_expression": cron_expression}
            )
            
        except Exception as e:
            self._log_operation("create", config.schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to create cron schedule: {e}",
                details={"schedule_id": config.schedule_id}
            ) from e
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Update an existing cron job.
        
        Args:
            schedule_id: Unique identifier for the schedule
            config: Updated schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule update
            
        Raises:
            PlatformSchedulerError: If schedule update fails
        """
        try:
            self.logger.info(f"Updating cron schedule {schedule_id}")
            
            # Remove existing cron entry
            await self._remove_cron_entry(schedule_id)
            
            # Create new schedule
            result = await self.create_schedule(config)
            
            self._log_operation("update", schedule_id, True)
            return result
            
        except Exception as e:
            self._log_operation("update", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to update cron schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Remove a cron job.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            PlatformSchedulerError: If schedule deletion fails
        """
        try:
            self.logger.info(f"Deleting cron schedule {schedule_id}")
            
            # Remove cron entry
            await self._remove_cron_entry(schedule_id)
            
            # Remove wrapper script
            script_path = self.wrapper_script_dir / f"timelocker-{schedule_id}.sh"
            if script_path.exists():
                script_path.unlink()
            
            self._log_operation("delete", schedule_id, True)
            return True
            
        except Exception as e:
            self._log_operation("delete", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to delete cron schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """
        Get cron job status.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            PlatformScheduleStatus: Current status of the schedule
            
        Raises:
            PlatformSchedulerError: If status retrieval fails
        """
        try:
            platform_id = f"cron-{schedule_id}"
            
            # Get cron entry
            cron_entry = await self._get_cron_entry(schedule_id)
            is_active = cron_entry is not None
            
            # Calculate next run time
            next_run = None
            if cron_entry:
                cron_expression = self._extract_cron_expression(cron_entry)
                next_run = self._calculate_next_cron_run(cron_expression)
            
            # Get last run time from log file
            last_run = await self._get_last_run_time(schedule_id)
            
            return PlatformScheduleStatus(
                platform_id=platform_id,
                is_active=is_active,
                last_run_time=last_run,
                next_run_time=next_run,
                platform_specific_data={"cron_entry": cron_entry or ""}
            )
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to get cron schedule status: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """
        List all cron jobs.
        
        Returns:
            List[PlatformScheduleInfo]: List of all scheduled tasks
            
        Raises:
            PlatformSchedulerError: If listing fails
        """
        try:
            schedules = []
            
            # Get current crontab
            crontab_content = await self._get_crontab()
            
            # Parse TimeLocker entries
            lines = crontab_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith(self.cron_comment_prefix):
                    # Extract schedule_id from comment
                    match = re.search(r'ID:\s*(\S+)', line)
                    if match and i + 1 < len(lines):
                        schedule_id = match.group(1)
                        cron_line = lines[i + 1]
                        
                        # Extract cron expression
                        cron_expression = self._extract_cron_expression(cron_line)
                        next_run = self._calculate_next_cron_run(cron_expression)
                        
                        schedules.append(PlatformScheduleInfo(
                            platform_id=f"cron-{schedule_id}",
                            schedule_id=schedule_id,
                            is_active=True,
                            next_run_time=next_run
                        ))
            
            return schedules
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to list cron schedules: {e}"
            ) from e
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration for cron compatibility.
        
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
        
        # Validate schedule_id format (must be valid for script names)
        if config.schedule_id and not re.match(r'^[a-zA-Z0-9_-]+$', config.schedule_id):
            result.add_error("schedule_id must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate schedule pattern
        if config.schedule_pattern.pattern_type == SchedulePatternType.CRON:
            if not config.schedule_pattern.cron_expression:
                result.add_error("cron_expression is required for CRON pattern type")
            else:
                # Validate cron expression format
                if not self._validate_cron_expression(config.schedule_pattern.cron_expression):
                    result.add_error(f"Invalid cron expression: {config.schedule_pattern.cron_expression}")
        elif config.schedule_pattern.pattern_type == SchedulePatternType.INTERVAL:
            if not config.schedule_pattern.interval_minutes:
                result.add_error("interval_minutes is required for INTERVAL pattern type")
            elif config.schedule_pattern.interval_minutes < 1:
                result.add_error("interval_minutes must be at least 1")
            else:
                result.add_warning("INTERVAL pattern type is not natively supported by cron - will use approximate scheduling")
        elif config.schedule_pattern.pattern_type == SchedulePatternType.CALENDAR:
            if not config.schedule_pattern.calendar_config:
                result.add_error("calendar_config is required for CALENDAR pattern type")
        
        # Validate execution timeout
        if config.execution_timeout and config.execution_timeout < 60:
            result.add_warning("execution_timeout less than 60 seconds may be too short for backup operations")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "cron"
    
    # Private helper methods
    
    async def _generate_wrapper_script(self, config: ScheduleConfig) -> Path:
        """
        Generate wrapper script for cron execution.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated script
        """
        script_path = self.wrapper_script_dir / f"timelocker-{config.schedule_id}.sh"
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
    
    def _generate_cron_expression(self, config: ScheduleConfig) -> str:
        """
        Generate cron expression from schedule pattern.
        
        Args:
            config: Schedule configuration
            
        Returns:
            str: Cron expression
        """
        pattern = config.schedule_pattern
        
        if pattern.pattern_type == SchedulePatternType.CRON:
            return pattern.cron_expression
        
        elif pattern.pattern_type == SchedulePatternType.INTERVAL:
            # Convert interval to cron (run every N minutes)
            # Note: Cron doesn't support arbitrary intervals, so we approximate
            interval = pattern.interval_minutes
            if interval <= 59:
                return f"*/{interval} * * * *"
            else:
                # For intervals > 59 minutes, run hourly at minute 0
                hours = interval // 60
                return f"0 */{hours} * * *"
        
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            cal = pattern.calendar_config
            
            # Convert days of week (0=Mon to 6=Sun) to cron format (0=Sun to 6=Sat)
            cron_days = [(d + 1) % 7 for d in cal.days_of_week]
            days_str = ",".join(str(d) for d in sorted(cron_days))
            
            # Format time
            minute = cal.time_of_day.minute
            hour = cal.time_of_day.hour
            
            # Build cron expression: minute hour day month weekday
            return f"{minute} {hour} * * {days_str}"
        
        else:
            raise ValueError(f"Unsupported pattern type: {pattern.pattern_type}")
    
    def _validate_cron_expression(self, expression: str) -> bool:
        """
        Validate cron expression format.
        
        Args:
            expression: Cron expression to validate
            
        Returns:
            bool: True if valid
        """
        parts = expression.split()
        if len(parts) not in [5, 6]:  # 5 fields (standard) or 6 fields (with seconds)
            return False
        
        # Basic validation of each field
        # This is simplified - full cron validation is complex
        for part in parts:
            if not re.match(r'^[\d\*,\-/]+$', part):
                return False
        
        return True
    
    def _extract_cron_expression(self, cron_line: str) -> str:
        """
        Extract cron expression from cron line.
        
        Args:
            cron_line: Full cron line
            
        Returns:
            str: Cron expression (first 5 fields)
        """
        parts = cron_line.split()
        if len(parts) >= 5:
            return " ".join(parts[:5])
        return ""
    
    def _calculate_next_cron_run(self, cron_expression: str) -> Optional[datetime]:
        """
        Calculate next run time for cron expression.
        
        Args:
            cron_expression: Cron expression
            
        Returns:
            Optional[datetime]: Next run time or None if cannot calculate
        """
        try:
            # This is a simplified calculation
            # For production, consider using croniter library
            parts = cron_expression.split()
            if len(parts) < 5:
                return None
            
            minute, hour, day, month, weekday = parts[:5]
            
            now = datetime.now()
            next_run = now.replace(second=0, microsecond=0)
            
            # Simple case: specific minute and hour
            if minute.isdigit() and hour.isdigit():
                target_minute = int(minute)
                target_hour = int(hour)
                
                next_run = next_run.replace(minute=target_minute, hour=target_hour)
                
                # If time has passed today, move to tomorrow
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run
            
            # For complex expressions, return approximate time
            return now + timedelta(hours=1)
            
        except Exception:
            return None
    
    async def _get_crontab(self) -> str:
        """
        Get current crontab content.
        
        Returns:
            str: Crontab content
            
        Raises:
            PlatformSchedulerError: If crontab retrieval fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "crontab", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode()
            elif process.returncode == 1:
                # No crontab exists yet
                return ""
            else:
                error_msg = stderr.decode().strip()
                raise PlatformSchedulerError(f"Failed to get crontab: {error_msg}")
                
        except FileNotFoundError:
            raise PlatformSchedulerError("crontab command not found")
        except Exception as e:
            raise PlatformSchedulerError(f"Failed to get crontab: {e}") from e
    
    async def _set_crontab(self, content: str) -> None:
        """
        Set crontab content.
        
        Args:
            content: New crontab content
            
        Raises:
            PlatformSchedulerError: If crontab update fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "crontab", "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=content.encode())
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                raise PlatformSchedulerError(f"Failed to set crontab: {error_msg}")
                
        except FileNotFoundError:
            raise PlatformSchedulerError("crontab command not found")
        except Exception as e:
            raise PlatformSchedulerError(f"Failed to set crontab: {e}") from e
    
    async def _add_cron_entry(self, schedule_id: str, cron_expression: str, script_path: Path) -> None:
        """
        Add cron entry to crontab.
        
        Args:
            schedule_id: Schedule identifier
            cron_expression: Cron expression
            script_path: Path to wrapper script
        """
        # Get current crontab
        current_crontab = await self._get_crontab()
        
        # Build new entry
        comment = f"{self.cron_comment_prefix} - ID: {schedule_id}"
        cron_line = f"{cron_expression} {script_path}"
        new_entry = f"{comment}\n{cron_line}\n"
        
        # Append to crontab
        new_crontab = current_crontab.rstrip() + "\n" + new_entry if current_crontab else new_entry
        
        # Set updated crontab
        await self._set_crontab(new_crontab)
        
        self.logger.debug(f"Added cron entry for schedule {schedule_id}")
    
    async def _remove_cron_entry(self, schedule_id: str) -> None:
        """
        Remove cron entry from crontab.
        
        Args:
            schedule_id: Schedule identifier
        """
        # Get current crontab
        current_crontab = await self._get_crontab()
        
        # Remove entry
        lines = current_crontab.split('\n')
        new_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
            
            if f"ID: {schedule_id}" in line:
                skip_next = True  # Skip the next line (actual cron command)
                continue
            
            new_lines.append(line)
        
        # Set updated crontab
        new_crontab = '\n'.join(new_lines)
        await self._set_crontab(new_crontab)
        
        self.logger.debug(f"Removed cron entry for schedule {schedule_id}")
    
    async def _get_cron_entry(self, schedule_id: str) -> Optional[str]:
        """
        Get cron entry for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Optional[str]: Cron entry or None if not found
        """
        current_crontab = await self._get_crontab()
        lines = current_crontab.split('\n')
        
        for i, line in enumerate(lines):
            if f"ID: {schedule_id}" in line and i + 1 < len(lines):
                return lines[i + 1]
        
        return None
    
    async def _get_last_run_time(self, schedule_id: str) -> Optional[datetime]:
        """
        Get last run time from log file.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Optional[datetime]: Last run time or None if not available
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
