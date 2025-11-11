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

Systemd Adapter

This module provides systemd timer integration for Linux systems.
"""

import asyncio
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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


class SystemdAdapter(PlatformAdapter):
    """
    Systemd timer adapter for Linux systems.
    
    This adapter creates and manages systemd user service and timer units
    for scheduled backup operations.
    
    Features:
    - Systemd service and timer unit generation
    - User service management via systemctl
    - Status monitoring and error reporting
    - Integration with journald logging
    """
    
    def __init__(self):
        """Initialize systemd adapter."""
        super().__init__()
        self.systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
        self.systemd_user_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Create systemd service and timer units.
        
        Args:
            config: Schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule creation
            
        Raises:
            PlatformSchedulerError: If schedule creation fails
        """
        try:
            self.logger.info(f"Creating systemd schedule for {config.schedule_id}")
            
            # Validate configuration
            validation = self.validate_schedule_config(config)
            if not validation.is_valid:
                raise PlatformSchedulerError(
                    f"Invalid schedule configuration: {', '.join(validation.errors)}"
                )
            
            # Generate service and timer unit files
            service_content = self._generate_service_unit(config)
            timer_content = self._generate_timer_unit(config)
            
            # Write unit files
            service_file = self.systemd_user_dir / f"timelocker-{config.schedule_id}.service"
            timer_file = self.systemd_user_dir / f"timelocker-{config.schedule_id}.timer"
            
            service_file.write_text(service_content)
            timer_file.write_text(timer_content)
            
            self.logger.debug(f"Created unit files: {service_file}, {timer_file}")
            
            # Reload systemd daemon
            await self._systemctl_command(["--user", "daemon-reload"])
            
            # Enable and start timer if schedule is enabled
            if config.enabled:
                await self._systemctl_command(["--user", "enable", timer_file.name])
                await self._systemctl_command(["--user", "start", timer_file.name])
            
            # Get next run time
            next_run = await self._get_next_run_time(config.schedule_id)
            
            platform_id = f"timelocker-{config.schedule_id}.timer"
            self._log_operation("create", config.schedule_id, True, f"Platform ID: {platform_id}")
            
            return PlatformScheduleResult(
                success=True,
                platform_id=platform_id,
                next_run=next_run
            )
            
        except Exception as e:
            self._log_operation("create", config.schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to create systemd schedule: {e}",
                details={"schedule_id": config.schedule_id}
            ) from e
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Update an existing systemd timer.
        
        Args:
            schedule_id: Unique identifier for the schedule
            config: Updated schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule update
            
        Raises:
            PlatformSchedulerError: If schedule update fails
        """
        try:
            self.logger.info(f"Updating systemd schedule {schedule_id}")
            
            # Stop and disable existing timer
            timer_name = f"timelocker-{schedule_id}.timer"
            try:
                await self._systemctl_command(["--user", "stop", timer_name])
                await self._systemctl_command(["--user", "disable", timer_name])
            except PlatformSchedulerError:
                # Timer might not exist or already stopped
                self.logger.warning(f"Could not stop existing timer {timer_name}")
            
            # Create new schedule (which will overwrite existing files)
            result = await self.create_schedule(config)
            
            self._log_operation("update", schedule_id, True)
            return result
            
        except Exception as e:
            self._log_operation("update", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to update systemd schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Remove a systemd timer.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            PlatformSchedulerError: If schedule deletion fails
        """
        try:
            self.logger.info(f"Deleting systemd schedule {schedule_id}")
            
            timer_name = f"timelocker-{schedule_id}.timer"
            service_name = f"timelocker-{schedule_id}.service"
            
            # Stop and disable timer
            try:
                await self._systemctl_command(["--user", "stop", timer_name])
                await self._systemctl_command(["--user", "disable", timer_name])
            except PlatformSchedulerError:
                self.logger.warning(f"Timer {timer_name} was not running")
            
            # Remove unit files
            timer_file = self.systemd_user_dir / timer_name
            service_file = self.systemd_user_dir / service_name
            
            if timer_file.exists():
                timer_file.unlink()
            if service_file.exists():
                service_file.unlink()
            
            # Reload daemon
            await self._systemctl_command(["--user", "daemon-reload"])
            
            self._log_operation("delete", schedule_id, True)
            return True
            
        except Exception as e:
            self._log_operation("delete", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to delete systemd schedule: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """
        Get systemd timer status.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            PlatformScheduleStatus: Current status of the schedule
            
        Raises:
            PlatformSchedulerError: If status retrieval fails
        """
        try:
            timer_name = f"timelocker-{schedule_id}.timer"
            platform_id = timer_name
            
            # Get timer status
            is_active = await self._is_timer_active(timer_name)
            
            # Get last and next run times
            last_run = await self._get_last_run_time(schedule_id)
            next_run = await self._get_next_run_time(schedule_id)
            
            # Get additional status information
            status_output = await self._get_timer_status_output(timer_name)
            
            return PlatformScheduleStatus(
                platform_id=platform_id,
                is_active=is_active,
                last_run_time=last_run,
                next_run_time=next_run,
                platform_specific_data={"status_output": status_output}
            )
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to get systemd schedule status: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """
        List all systemd timers.
        
        Returns:
            List[PlatformScheduleInfo]: List of all scheduled tasks
            
        Raises:
            PlatformSchedulerError: If listing fails
        """
        try:
            schedules = []
            
            # Find all TimeLocker timer files
            for timer_file in self.systemd_user_dir.glob("timelocker-*.timer"):
                # Extract schedule_id from filename
                match = re.match(r"timelocker-(.+)\.timer", timer_file.name)
                if not match:
                    continue
                
                schedule_id = match.group(1)
                
                # Get status for this timer
                is_active = await self._is_timer_active(timer_file.name)
                next_run = await self._get_next_run_time(schedule_id)
                
                schedules.append(PlatformScheduleInfo(
                    platform_id=timer_file.name,
                    schedule_id=schedule_id,
                    is_active=is_active,
                    next_run_time=next_run
                ))
            
            return schedules
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to list systemd schedules: {e}"
            ) from e
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration for systemd compatibility.
        
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
        
        # Validate schedule_id format (must be valid for systemd unit names)
        if config.schedule_id and not re.match(r'^[a-zA-Z0-9_-]+$', config.schedule_id):
            result.add_error("schedule_id must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate schedule pattern
        if config.schedule_pattern.pattern_type == SchedulePatternType.CRON:
            if not config.schedule_pattern.cron_expression:
                result.add_error("cron_expression is required for CRON pattern type")
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
        return "systemd"
    
    # Private helper methods
    
    def _generate_service_unit(self, config: ScheduleConfig) -> str:
        """
        Generate systemd service unit content.
        
        Args:
            config: Schedule configuration
            
        Returns:
            str: Service unit file content
        """
        timeout = config.execution_timeout or 3600
        
        service_content = f"""[Unit]
Description=TimeLocker Scheduled Backup: {config.name}
Documentation=https://github.com/redjoy12/TimeLocker
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/env timelocker backup execute --policy-id {config.policy_id} --scheduled
TimeoutStartSec={timeout}
StandardOutput=journal
StandardError=journal
SyslogIdentifier=timelocker-{config.schedule_id}

[Install]
WantedBy=default.target
"""
        return service_content
    
    def _generate_timer_unit(self, config: ScheduleConfig) -> str:
        """
        Generate systemd timer unit content.
        
        Args:
            config: Schedule configuration
            
        Returns:
            str: Timer unit file content
        """
        pattern = config.schedule_pattern
        
        # Generate OnCalendar or OnUnitActiveSec based on pattern type
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            interval_seconds = pattern.interval_minutes * 60
            timer_spec = f"OnUnitActiveSec={interval_seconds}s"
            # Add initial delay
            timer_spec += f"\nOnBootSec={interval_seconds}s"
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            # Convert calendar config to systemd calendar format
            timer_spec = self._calendar_to_systemd_format(pattern.calendar_config)
        else:  # CRON
            # Convert cron expression to systemd calendar format
            timer_spec = self._cron_to_systemd_format(pattern.cron_expression)
        
        # Add randomized delay if configured
        randomized_delay = ""
        if pattern.randomize_delay_minutes > 0:
            randomized_delay = f"RandomizedDelaySec={pattern.randomize_delay_minutes * 60}s"
        
        timer_content = f"""[Unit]
Description=Timer for TimeLocker Scheduled Backup: {config.name}
Documentation=https://github.com/redjoy12/TimeLocker

[Timer]
{timer_spec}
{randomized_delay}
Persistent=true

[Install]
WantedBy=timers.target
"""
        return timer_content
    
    def _calendar_to_systemd_format(self, calendar_config) -> str:
        """
        Convert CalendarConfig to systemd OnCalendar format.
        
        Args:
            calendar_config: Calendar configuration
            
        Returns:
            str: OnCalendar specification
        """
        # Convert days of week (0=Mon to 6=Sun) to systemd format (Mon-Sun)
        days_map = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days = ",".join(days_map[d] for d in sorted(calendar_config.days_of_week))
        
        # Format time
        time_str = calendar_config.time_of_day.strftime("%H:%M:%S")
        
        # Build OnCalendar string
        calendar_str = f"{days} *-*-* {time_str}"
        
        return f"OnCalendar={calendar_str}"
    
    def _cron_to_systemd_format(self, cron_expression: str) -> str:
        """
        Convert cron expression to systemd OnCalendar format.
        
        Args:
            cron_expression: Cron expression (5 or 6 fields)
            
        Returns:
            str: OnCalendar specification
        """
        # This is a simplified conversion - full cron syntax is complex
        # For now, support basic patterns
        parts = cron_expression.split()
        
        if len(parts) < 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        minute, hour, day, month, weekday = parts[:5]
        
        # Build systemd calendar format: DayOfWeek Year-Month-Day Hour:Minute:Second
        calendar_parts = []
        
        # Weekday
        if weekday != "*":
            calendar_parts.append(weekday)
        
        # Date
        year = "*"
        date_part = f"{year}-{month if month != '*' else '*'}-{day if day != '*' else '*'}"
        calendar_parts.append(date_part)
        
        # Time
        time_part = f"{hour if hour != '*' else '*'}:{minute if minute != '*' else '*'}:00"
        calendar_parts.append(time_part)
        
        return f"OnCalendar={' '.join(calendar_parts)}"
    
    async def _systemctl_command(self, args: List[str]) -> str:
        """
        Execute systemctl command.
        
        Args:
            args: Command arguments
            
        Returns:
            str: Command output
            
        Raises:
            PlatformSchedulerError: If command fails
        """
        try:
            cmd = ["systemctl"] + args
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
                    f"systemctl command failed: {error_msg}",
                    details={"command": " ".join(cmd), "returncode": process.returncode}
                )
            
            return stdout.decode().strip()
            
        except FileNotFoundError:
            raise PlatformSchedulerError(
                "systemctl command not found - systemd may not be installed"
            )
        except Exception as e:
            if isinstance(e, PlatformSchedulerError):
                raise
            raise PlatformSchedulerError(f"Failed to execute systemctl: {e}") from e
    
    async def _is_timer_active(self, timer_name: str) -> bool:
        """
        Check if a timer is active.
        
        Args:
            timer_name: Name of the timer unit
            
        Returns:
            bool: True if timer is active
        """
        try:
            output = await self._systemctl_command(["--user", "is-active", timer_name])
            return output.strip() == "active"
        except PlatformSchedulerError:
            return False
    
    async def _get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        """
        Get next scheduled run time for a timer.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Optional[datetime]: Next run time or None if not available
        """
        try:
            timer_name = f"timelocker-{schedule_id}.timer"
            output = await self._systemctl_command(
                ["--user", "list-timers", "--all", timer_name]
            )
            
            # Parse output to extract next run time
            # Format: NEXT                         LEFT     LAST                         PASSED  UNIT                    ACTIVATES
            lines = output.split('\n')
            for line in lines:
                if timer_name in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        # First column is NEXT time
                        next_time_str = f"{parts[0]} {parts[1]}"
                        try:
                            # Parse systemd date format
                            return datetime.strptime(next_time_str, "%a %Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # Try alternative format
                            pass
            
            return None
            
        except Exception:
            return None
    
    async def _get_last_run_time(self, schedule_id: str) -> Optional[datetime]:
        """
        Get last run time for a timer.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Optional[datetime]: Last run time or None if not available
        """
        try:
            timer_name = f"timelocker-{schedule_id}.timer"
            output = await self._systemctl_command(
                ["--user", "list-timers", "--all", timer_name]
            )
            
            # Parse output to extract last run time
            lines = output.split('\n')
            for line in lines:
                if timer_name in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Fourth column is LAST time
                        last_time_str = f"{parts[2]} {parts[3]}"
                        try:
                            return datetime.strptime(last_time_str, "%a %Y-%m-%d %H:%M:%S")
                        except ValueError:
                            pass
            
            return None
            
        except Exception:
            return None
    
    async def _get_timer_status_output(self, timer_name: str) -> str:
        """
        Get detailed status output for a timer.
        
        Args:
            timer_name: Name of the timer unit
            
        Returns:
            str: Status output
        """
        try:
            return await self._systemctl_command(["--user", "status", timer_name])
        except PlatformSchedulerError:
            return "Status unavailable"
