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

Windows Task Scheduler Adapter

This module provides Windows Task Scheduler integration.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
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


class WindowsTaskSchedulerAdapter(PlatformAdapter):
    """
    Windows Task Scheduler adapter.
    
    This adapter creates and manages Windows scheduled tasks for
    backup operations.
    
    Features:
    - Windows Task Scheduler integration using schtasks command
    - Task XML generation for complex scheduling
    - PowerShell script creation for proper execution
    - Windows-specific error handling and status reporting
    """
    
    def __init__(self):
        """Initialize Windows Task Scheduler adapter."""
        super().__init__()
        self.task_folder = "\\TimeLocker"
        self.powershell_wrapper_dir = Path.home() / "AppData" / "Local" / "TimeLocker" / "Scripts"
        self.powershell_wrapper_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path.home() / "AppData" / "Local" / "TimeLocker" / "Logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Create Windows scheduled task.
        
        Args:
            config: Schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule creation
            
        Raises:
            PlatformSchedulerError: If schedule creation fails
        """
        try:
            self.logger.info(f"Creating Windows scheduled task for {config.schedule_id}")
            
            # Validate configuration
            validation = self.validate_schedule_config(config)
            if not validation.is_valid:
                raise PlatformSchedulerError(
                    f"Invalid schedule configuration: {', '.join(validation.errors)}"
                )
            
            # Generate PowerShell wrapper script
            script_path = await self._generate_powershell_script(config)
            
            # Generate task XML
            task_xml = self._generate_task_xml(config, script_path)
            
            # Create task using schtasks
            task_name = f"TimeLocker-{config.schedule_id}"
            await self._create_scheduled_task(task_name, task_xml)
            
            # Get next run time
            next_run = await self._get_task_next_run(task_name)
            
            platform_id = f"{self.task_folder}\\{task_name}"
            self._log_operation("create", config.schedule_id, True, f"Platform ID: {platform_id}")
            
            return PlatformScheduleResult(
                success=True,
                platform_id=platform_id,
                next_run=next_run
            )
            
        except Exception as e:
            self._log_operation("create", config.schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to create Windows scheduled task: {e}",
                details={"schedule_id": config.schedule_id}
            ) from e
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Update an existing Windows scheduled task.
        
        Args:
            schedule_id: Unique identifier for the schedule
            config: Updated schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule update
            
        Raises:
            PlatformSchedulerError: If schedule update fails
        """
        try:
            self.logger.info(f"Updating Windows scheduled task {schedule_id}")
            
            # Delete existing task
            task_name = f"TimeLocker-{schedule_id}"
            try:
                await self._delete_scheduled_task(task_name)
            except PlatformSchedulerError:
                self.logger.warning(f"Task {task_name} did not exist")
            
            # Create new task
            result = await self.create_schedule(config)
            
            self._log_operation("update", schedule_id, True)
            return result
            
        except Exception as e:
            self._log_operation("update", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to update Windows scheduled task: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Remove a Windows scheduled task.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            PlatformSchedulerError: If schedule deletion fails
        """
        try:
            self.logger.info(f"Deleting Windows scheduled task {schedule_id}")
            
            # Delete task
            task_name = f"TimeLocker-{schedule_id}"
            await self._delete_scheduled_task(task_name)
            
            # Remove PowerShell script
            script_path = self.powershell_wrapper_dir / f"timelocker-{schedule_id}.ps1"
            if script_path.exists():
                script_path.unlink()
            
            self._log_operation("delete", schedule_id, True)
            return True
            
        except Exception as e:
            self._log_operation("delete", schedule_id, False, str(e))
            raise PlatformSchedulerError(
                f"Failed to delete Windows scheduled task: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """
        Get Windows scheduled task status.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            PlatformScheduleStatus: Current status of the schedule
            
        Raises:
            PlatformSchedulerError: If status retrieval fails
        """
        try:
            task_name = f"TimeLocker-{schedule_id}"
            platform_id = f"{self.task_folder}\\{task_name}"
            
            # Get task status
            task_info = await self._get_task_info(task_name)
            
            is_active = task_info.get("status") == "Ready"
            last_run = task_info.get("last_run_time")
            next_run = task_info.get("next_run_time")
            
            return PlatformScheduleStatus(
                platform_id=platform_id,
                is_active=is_active,
                last_run_time=last_run,
                next_run_time=next_run,
                platform_specific_data=task_info
            )
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to get Windows scheduled task status: {e}",
                details={"schedule_id": schedule_id}
            ) from e
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """
        List all Windows scheduled tasks.
        
        Returns:
            List[PlatformScheduleInfo]: List of all scheduled tasks
            
        Raises:
            PlatformSchedulerError: If listing fails
        """
        try:
            schedules = []
            
            # Query all tasks in TimeLocker folder
            output = await self._schtasks_command([
                "/Query",
                "/FO", "CSV",
                "/V"
            ])
            
            # Parse CSV output
            lines = output.split('\n')
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                
                # Check if task is in TimeLocker folder
                if self.task_folder in line and "TimeLocker-" in line:
                    # Extract task name
                    match = re.search(r'TimeLocker-([^"]+)', line)
                    if match:
                        schedule_id = match.group(1)
                        task_name = f"TimeLocker-{schedule_id}"
                        
                        # Get task info
                        task_info = await self._get_task_info(task_name)
                        
                        schedules.append(PlatformScheduleInfo(
                            platform_id=f"{self.task_folder}\\{task_name}",
                            schedule_id=schedule_id,
                            is_active=task_info.get("status") == "Ready",
                            next_run_time=task_info.get("next_run_time")
                        ))
            
            return schedules
            
        except Exception as e:
            raise PlatformSchedulerError(
                f"Failed to list Windows scheduled tasks: {e}"
            ) from e
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration for Windows Task Scheduler compatibility.
        
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
        
        # Validate schedule_id format (must be valid for Windows task names)
        if config.schedule_id and not re.match(r'^[a-zA-Z0-9_-]+$', config.schedule_id):
            result.add_error("schedule_id must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate schedule pattern
        if config.schedule_pattern.pattern_type == SchedulePatternType.CRON:
            result.add_warning("CRON pattern type will be converted to Windows Task Scheduler format")
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
        return "windows_task_scheduler"
    
    # Private helper methods
    
    async def _generate_powershell_script(self, config: ScheduleConfig) -> Path:
        """
        Generate PowerShell wrapper script.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated script
        """
        script_path = self.powershell_wrapper_dir / f"timelocker-{config.schedule_id}.ps1"
        log_file = self.log_dir / f"timelocker-{config.schedule_id}.log"
        
        timeout = config.execution_timeout or 3600
        
        script_content = f"""# TimeLocker Scheduled Backup Wrapper Script
# Schedule ID: {config.schedule_id}
# Policy ID: {config.policy_id}
# Generated: {datetime.utcnow().isoformat()}

$ErrorActionPreference = "Stop"

# Logging
$LogFile = "{log_file}"
$StartTime = Get-Date

# Log function
function Write-Log {{
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -FilePath $LogFile -Append
}}

Write-Log "=== TimeLocker Backup Execution Started ==="
Write-Log "Schedule ID: {config.schedule_id}"
Write-Log "Policy ID: {config.policy_id}"

try {{
    # Execute backup with timeout
    $Job = Start-Job -ScriptBlock {{
        timelocker backup execute --policy-id {config.policy_id} --scheduled
    }}
    
    $Timeout = {timeout}
    $Completed = Wait-Job -Job $Job -Timeout $Timeout
    
    if ($Completed) {{
        $Result = Receive-Job -Job $Job
        $ExitCode = $Job.State -eq "Completed" ? 0 : 1
        
        Write-Log "Backup output: $Result"
        Write-Log "=== Backup Completed Successfully ==="
        exit 0
    }} else {{
        Stop-Job -Job $Job
        Remove-Job -Job $Job
        Write-Log "=== Backup Timed Out after $Timeout seconds ==="
        exit 1
    }}
}} catch {{
    Write-Log "=== Backup Failed: $($_.Exception.Message) ==="
    exit 1
}} finally {{
    $EndTime = Get-Date
    $Duration = ($EndTime - $StartTime).TotalSeconds
    Write-Log "Execution duration: $Duration seconds"
}}
"""
        
        # Write script
        script_path.write_text(script_content)
        
        self.logger.debug(f"Generated PowerShell script: {script_path}")
        return script_path
    
    def _generate_task_xml(self, config: ScheduleConfig, script_path: Path) -> str:
        """
        Generate Windows Task Scheduler XML.
        
        Args:
            config: Schedule configuration
            script_path: Path to PowerShell script
            
        Returns:
            str: Task XML content
        """
        pattern = config.schedule_pattern
        
        # Generate trigger XML based on pattern type
        if pattern.pattern_type == SchedulePatternType.INTERVAL:
            trigger_xml = self._generate_interval_trigger(pattern.interval_minutes)
        elif pattern.pattern_type == SchedulePatternType.CALENDAR:
            trigger_xml = self._generate_calendar_trigger(pattern.calendar_config)
        else:  # CRON
            trigger_xml = self._generate_cron_trigger(pattern.cron_expression)
        
        # Build task XML
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>TimeLocker Scheduled Backup: {config.name}</Description>
    <URI>{self.task_folder}\\TimeLocker-{config.schedule_id}</URI>
  </RegistrationInfo>
  <Triggers>
    {trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>{str(config.enabled).lower()}</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT{config.execution_timeout or 3600}S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-ExecutionPolicy Bypass -File "{script_path}"</Arguments>
    </Exec>
  </Actions>
</Task>
"""
        return task_xml
    
    def _generate_interval_trigger(self, interval_minutes: int) -> str:
        """Generate interval-based trigger XML."""
        # Convert minutes to ISO 8601 duration format
        hours = interval_minutes // 60
        minutes = interval_minutes % 60
        
        if hours > 0:
            repetition = f"PT{hours}H{minutes}M" if minutes > 0 else f"PT{hours}H"
        else:
            repetition = f"PT{minutes}M"
        
        return f"""<TimeTrigger>
      <Repetition>
        <Interval>{repetition}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>{datetime.utcnow().isoformat()}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>"""
    
    def _generate_calendar_trigger(self, calendar_config) -> str:
        """Generate calendar-based trigger XML."""
        # Convert days of week (0=Mon to 6=Sun) to Windows format
        days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_xml = "\n        ".join(f"<{days_map[d]}/>" for d in sorted(calendar_config.days_of_week))
        
        # Format start time
        start_time = datetime.combine(datetime.today(), calendar_config.time_of_day).isoformat()
        
        return f"""<CalendarTrigger>
      <StartBoundary>{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
          {days_xml}
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>"""
    
    def _generate_cron_trigger(self, cron_expression: str) -> str:
        """Generate trigger XML from cron expression."""
        # Parse cron expression and convert to Windows trigger
        # This is simplified - full cron conversion is complex
        parts = cron_expression.split()
        if len(parts) >= 5:
            minute, hour, day, month, weekday = parts[:5]
            
            # Build start time
            start_hour = int(hour) if hour.isdigit() else 0
            start_minute = int(minute) if minute.isdigit() else 0
            start_time = datetime.now().replace(hour=start_hour, minute=start_minute, second=0).isoformat()
            
            # For daily schedule
            if weekday == "*":
                return f"""<CalendarTrigger>
      <StartBoundary>{start_time}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""
        
        # Default to daily trigger
        return self._generate_interval_trigger(1440)  # 24 hours
    
    async def _schtasks_command(self, args: List[str]) -> str:
        """
        Execute schtasks command.
        
        Args:
            args: Command arguments
            
        Returns:
            str: Command output
            
        Raises:
            PlatformSchedulerError: If command fails
        """
        try:
            cmd = ["schtasks"] + args
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
                    f"schtasks command failed: {error_msg}",
                    details={"command": " ".join(cmd), "returncode": process.returncode}
                )
            
            return stdout.decode().strip()
            
        except FileNotFoundError:
            raise PlatformSchedulerError(
                "schtasks command not found - Windows Task Scheduler may not be available"
            )
        except Exception as e:
            if isinstance(e, PlatformSchedulerError):
                raise
            raise PlatformSchedulerError(f"Failed to execute schtasks: {e}") from e
    
    async def _create_scheduled_task(self, task_name: str, task_xml: str) -> None:
        """
        Create scheduled task from XML.
        
        Args:
            task_name: Name of the task
            task_xml: Task XML content
        """
        # Write XML to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(task_xml)
            xml_path = f.name
        
        try:
            # Create task
            await self._schtasks_command([
                "/Create",
                "/TN", f"{self.task_folder}\\{task_name}",
                "/XML", xml_path,
                "/F"  # Force overwrite if exists
            ])
        finally:
            # Clean up temp file
            Path(xml_path).unlink(missing_ok=True)
    
    async def _delete_scheduled_task(self, task_name: str) -> None:
        """
        Delete scheduled task.
        
        Args:
            task_name: Name of the task
        """
        await self._schtasks_command([
            "/Delete",
            "/TN", f"{self.task_folder}\\{task_name}",
            "/F"
        ])
    
    async def _get_task_info(self, task_name: str) -> dict:
        """
        Get task information.
        
        Args:
            task_name: Name of the task
            
        Returns:
            dict: Task information
        """
        try:
            output = await self._schtasks_command([
                "/Query",
                "/TN", f"{self.task_folder}\\{task_name}",
                "/FO", "LIST",
                "/V"
            ])
            
            # Parse output
            info = {}
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    # Parse datetime fields
                    if 'time' in key and value and value != "N/A":
                        try:
                            info[key] = datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
                        except ValueError:
                            info[key] = value
                    else:
                        info[key] = value
            
            return info
            
        except PlatformSchedulerError:
            return {}
    
    async def _get_task_next_run(self, task_name: str) -> Optional[datetime]:
        """
        Get next run time for task.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Optional[datetime]: Next run time or None
        """
        info = await self._get_task_info(task_name)
        return info.get("next_run_time")
