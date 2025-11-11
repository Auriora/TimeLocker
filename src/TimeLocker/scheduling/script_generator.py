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

Script Generator for Scheduled Backups

This module provides platform-specific wrapper script generation for
scheduled backup execution with comprehensive error handling, environment
setup, and monitoring integration.
"""

import platform
import stat
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .scheduling_models import ScheduleConfig
from .scheduling_exceptions import SchedulingError, UnsupportedPlatformError

logger = logging.getLogger(__name__)


class ScriptGenerator:
    """
    Generates platform-specific wrapper scripts for scheduled backups.
    
    Responsibilities:
    - Platform-appropriate script generation (bash, PowerShell)
    - Environment setup and credential loading
    - Error handling and logging integration
    - Monitoring integration
    - Timeout and retry logic
    
    The generator creates self-contained scripts that can be executed
    by platform schedulers with proper error handling and reporting.
    """
    
    def __init__(self, platform_name: Optional[str] = None):
        """
        Initialize script generator.
        
        Args:
            platform_name: Platform name override (default: auto-detect)
                          Valid values: 'linux', 'darwin', 'windows'
        """
        self.platform = platform_name or platform.system().lower()
        self.logger = logging.getLogger(f"{__name__}.ScriptGenerator")
        self.logger.info(f"Initialized ScriptGenerator for platform: {self.platform}")
        
        # Platform-specific script directories
        self._script_dirs = {
            'linux': Path.home() / ".local" / "bin",
            'darwin': Path.home() / "Library" / "Application Support" / "TimeLocker" / "Scripts",
            'windows': Path.home() / "AppData" / "Local" / "TimeLocker" / "Scripts"
        }
        
        # Platform-specific log directories
        self._log_dirs = {
            'linux': Path.home() / ".local" / "share" / "timelocker" / "logs",
            'darwin': Path.home() / "Library" / "Logs" / "TimeLocker",
            'windows': Path.home() / "AppData" / "Local" / "TimeLocker" / "Logs"
        }
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure script and log directories exist."""
        try:
            script_dir = self._script_dirs.get(self.platform)
            log_dir = self._log_dirs.get(self.platform)
            
            if script_dir:
                script_dir.mkdir(parents=True, exist_ok=True)
            if log_dir:
                log_dir.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            self.logger.warning(f"Failed to create directories: {e}")
    
    async def generate_wrapper_script(self, config: ScheduleConfig) -> Path:
        """
        Generate platform-specific wrapper script.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated script
            
        Raises:
            UnsupportedPlatformError: If platform is not supported
            SchedulingError: If script generation fails
        """
        try:
            if self.platform in ['linux', 'darwin']:
                return await self._generate_bash_script(config)
            elif self.platform == 'windows':
                return await self._generate_powershell_script(config)
            else:
                raise UnsupportedPlatformError(f"Platform {self.platform} not supported")
                
        except Exception as e:
            self.logger.error(f"Failed to generate wrapper script: {e}")
            raise SchedulingError(f"Script generation failed: {e}") from e
    
    async def _generate_bash_script(self, config: ScheduleConfig) -> Path:
        """
        Generate bash wrapper script for Unix-like systems.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated bash script
        """
        script_dir = self._script_dirs[self.platform]
        log_dir = self._log_dirs[self.platform]
        
        script_path = script_dir / f"timelocker-{config.schedule_id}.sh"
        log_file = log_dir / f"timelocker-{config.schedule_id}.log"
        
        # Get TimeLocker executable path
        timelocker_executable = self._get_timelocker_executable()
        
        # Get timeout and retry configuration
        timeout = config.execution_timeout or 3600
        max_retries = config.retry_config.max_attempts if config.retry_config else 3
        initial_delay = config.retry_config.initial_delay_minutes if config.retry_config else 5
        
        # Get monitoring configuration
        webhook_url = config.monitoring_config.webhook_url if config.monitoring_config else ""
        
        script_content = self._get_bash_template().format(
            schedule_id=config.schedule_id,
            policy_id=config.policy_id,
            schedule_name=config.name,
            timelocker_executable=timelocker_executable,
            log_file=log_file,
            timeout_seconds=timeout,
            max_retries=max_retries,
            initial_delay_minutes=initial_delay,
            webhook_url=webhook_url
        )
        
        # Write script file
        await self._write_script_file(script_path, script_content, executable=True)
        
        self.logger.info(f"Generated bash wrapper script: {script_path}")
        return script_path
    
    async def _generate_powershell_script(self, config: ScheduleConfig) -> Path:
        """
        Generate PowerShell wrapper script for Windows.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Path: Path to generated PowerShell script
        """
        script_dir = self._script_dirs['windows']
        log_dir = self._log_dirs['windows']
        
        script_path = script_dir / f"timelocker-{config.schedule_id}.ps1"
        log_file = log_dir / f"timelocker-{config.schedule_id}.log"
        
        # Get TimeLocker executable path
        timelocker_executable = self._get_timelocker_executable()
        
        # Get timeout and retry configuration
        timeout = config.execution_timeout or 3600
        max_retries = config.retry_config.max_attempts if config.retry_config else 3
        initial_delay = config.retry_config.initial_delay_minutes if config.retry_config else 5
        
        # Get monitoring configuration
        webhook_url = config.monitoring_config.webhook_url if config.monitoring_config else ""
        
        script_content = self._get_powershell_template().format(
            schedule_id=config.schedule_id,
            policy_id=config.policy_id,
            schedule_name=config.name,
            timelocker_executable=timelocker_executable,
            log_file=log_file,
            timeout_seconds=timeout,
            max_retries=max_retries,
            initial_delay_minutes=initial_delay,
            webhook_url=webhook_url
        )
        
        # Write script file
        await self._write_script_file(script_path, script_content, executable=False)
        
        self.logger.info(f"Generated PowerShell wrapper script: {script_path}")
        return script_path
    
    def _get_timelocker_executable(self) -> str:
        """
        Get path to TimeLocker executable.
        
        Returns:
            str: Path to timelocker executable
        """
        # Try to find timelocker in PATH
        import shutil
        timelocker_path = shutil.which('timelocker')
        
        if timelocker_path:
            return timelocker_path
        
        # Fallback to python module execution
        python_executable = sys.executable
        return f"{python_executable} -m TimeLocker.cli"
    
    async def _write_script_file(self, path: Path, content: str, executable: bool = False) -> None:
        """
        Write script file with appropriate permissions.
        
        Args:
            path: Path to script file
            content: Script content
            executable: Whether to make file executable (Unix only)
        """
        try:
            # Write script content
            path.write_text(content, encoding='utf-8')
            
            # Make executable on Unix-like systems
            if executable and self.platform in ['linux', 'darwin']:
                current_mode = path.stat().st_mode
                path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            
            self.logger.debug(f"Wrote script file: {path}")
            
        except Exception as e:
            raise SchedulingError(f"Failed to write script file {path}: {e}") from e
    
    def _get_bash_template(self) -> str:
        """
        Get bash script template.
        
        Returns:
            str: Bash script template with placeholders
        """
        return '''#!/bin/bash
# TimeLocker Scheduled Backup Wrapper Script
# Generated by TimeLocker Scheduling System
#
# Schedule ID: {schedule_id}
# Schedule Name: {schedule_name}
# Policy ID: {policy_id}
#
# This script is automatically generated and should not be edited manually.
# Changes will be overwritten when the schedule is updated.

set -euo pipefail

# Configuration
SCHEDULE_ID="{schedule_id}"
POLICY_ID="{policy_id}"
TIMELOCKER_EXEC="{timelocker_executable}"
LOG_FILE="{log_file}"
TIMEOUT_SECONDS={timeout_seconds}
MAX_RETRIES={max_retries}
INITIAL_DELAY_MINUTES={initial_delay_minutes}
WEBHOOK_URL="{webhook_url}"

# Execution tracking
EXECUTION_ID="$(date +%Y%m%d-%H%M%S)-$$"
START_TIME=$(date +%s)
RETRY_COUNT=0

# Logging function
log_message() {{
    local level="$1"
    shift
    local message="$*"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}}

# Send webhook notification
send_webhook() {{
    local status="$1"
    local message="$2"
    
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST "$WEBHOOK_URL" \\
            -H "Content-Type: application/json" \\
            -d "{{
                \\"schedule_id\\": \\"$SCHEDULE_ID\\",
                \\"execution_id\\": \\"$EXECUTION_ID\\",
                \\"status\\": \\"$status\\",
                \\"message\\": \\"$message\\",
                \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\"
            }}" \\
            --max-time 10 \\
            --silent \\
            --show-error \\
            >> "$LOG_FILE" 2>&1 || true
    fi
}}

# Cleanup function
cleanup() {{
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    if [ $exit_code -eq 0 ]; then
        log_message "INFO" "Backup completed successfully in ${{duration}}s"
        send_webhook "success" "Backup completed successfully"
    else
        log_message "ERROR" "Backup failed with exit code $exit_code after ${{duration}}s"
        send_webhook "failure" "Backup failed with exit code $exit_code"
    fi
    
    exit $exit_code
}}

trap cleanup EXIT

# Main execution with retry logic
execute_backup() {{
    log_message "INFO" "Starting scheduled backup execution"
    log_message "INFO" "Execution ID: $EXECUTION_ID"
    log_message "INFO" "Schedule ID: $SCHEDULE_ID"
    log_message "INFO" "Policy ID: $POLICY_ID"
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if [ $RETRY_COUNT -gt 0 ]; then
            local delay=$((INITIAL_DELAY_MINUTES * (2 ** (RETRY_COUNT - 1))))
            log_message "WARN" "Retry attempt $RETRY_COUNT after ${{delay}} minutes"
            sleep $((delay * 60))
        fi
        
        log_message "INFO" "Executing backup (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
        
        # Execute backup with timeout
        if timeout "$TIMEOUT_SECONDS" "$TIMELOCKER_EXEC" backup execute --policy "$POLICY_ID" --non-interactive >> "$LOG_FILE" 2>&1; then
            log_message "INFO" "Backup execution successful"
            return 0
        else
            local exit_code=$?
            log_message "ERROR" "Backup execution failed with exit code $exit_code"
            RETRY_COUNT=$((RETRY_COUNT + 1))
            
            if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                log_message "ERROR" "Maximum retry attempts reached"
                return $exit_code
            fi
        fi
    done
    
    return 1
}}

# Execute backup
execute_backup
'''
    
    def _get_powershell_template(self) -> str:
        """
        Get PowerShell script template.
        
        Returns:
            str: PowerShell script template with placeholders
        """
        return '''# TimeLocker Scheduled Backup Wrapper Script
# Generated by TimeLocker Scheduling System
#
# Schedule ID: {schedule_id}
# Schedule Name: {schedule_name}
# Policy ID: {policy_id}
#
# This script is automatically generated and should not be edited manually.
# Changes will be overwritten when the schedule is updated.

$ErrorActionPreference = "Stop"

# Configuration
$ScheduleId = "{schedule_id}"
$PolicyId = "{policy_id}"
$TimeLockerExec = "{timelocker_executable}"
$LogFile = "{log_file}"
$TimeoutSeconds = {timeout_seconds}
$MaxRetries = {max_retries}
$InitialDelayMinutes = {initial_delay_minutes}
$WebhookUrl = "{webhook_url}"

# Execution tracking
$ExecutionId = "$(Get-Date -Format 'yyyyMMdd-HHmmss')-$PID"
$StartTime = Get-Date
$RetryCount = 0

# Logging function
function Write-Log {{
    param(
        [string]$Level,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Output $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}}

# Send webhook notification
function Send-Webhook {{
    param(
        [string]$Status,
        [string]$Message
    )
    
    if ($WebhookUrl) {{
        try {{
            $body = @{{
                schedule_id = $ScheduleId
                execution_id = $ExecutionId
                status = $Status
                message = $Message
                timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            }} | ConvertTo-Json
            
            Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction SilentlyContinue
        }} catch {{
            Write-Log "WARN" "Failed to send webhook notification: $_"
        }}
    }}
}}

# Main execution with retry logic
function Execute-Backup {{
    Write-Log "INFO" "Starting scheduled backup execution"
    Write-Log "INFO" "Execution ID: $ExecutionId"
    Write-Log "INFO" "Schedule ID: $ScheduleId"
    Write-Log "INFO" "Policy ID: $PolicyId"
    
    while ($RetryCount -lt $MaxRetries) {{
        if ($RetryCount -gt 0) {{
            $delay = $InitialDelayMinutes * [Math]::Pow(2, $RetryCount - 1)
            Write-Log "WARN" "Retry attempt $RetryCount after $delay minutes"
            Start-Sleep -Seconds ($delay * 60)
        }}
        
        Write-Log "INFO" "Executing backup (attempt $($RetryCount + 1)/$MaxRetries)"
        
        try {{
            # Execute backup with timeout
            $job = Start-Job -ScriptBlock {{
                param($exec, $policy, $log)
                & $exec backup execute --policy $policy --non-interactive 2>&1 | Out-File -Append -FilePath $log
            }} -ArgumentList $TimeLockerExec, $PolicyId, $LogFile
            
            $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
            
            if ($completed) {{
                $result = Receive-Job -Job $job
                Remove-Job -Job $job
                
                if ($LASTEXITCODE -eq 0) {{
                    Write-Log "INFO" "Backup execution successful"
                    return 0
                }} else {{
                    Write-Log "ERROR" "Backup execution failed with exit code $LASTEXITCODE"
                    $script:RetryCount++
                }}
            }} else {{
                Stop-Job -Job $job
                Remove-Job -Job $job
                Write-Log "ERROR" "Backup execution timed out after $TimeoutSeconds seconds"
                $script:RetryCount++
            }}
        }} catch {{
            Write-Log "ERROR" "Backup execution failed: $_"
            $script:RetryCount++
        }}
        
        if ($RetryCount -ge $MaxRetries) {{
            Write-Log "ERROR" "Maximum retry attempts reached"
            return 1
        }}
    }}
    
    return 1
}}

# Execute backup and handle results
try {{
    $exitCode = Execute-Backup
    $endTime = Get-Date
    $duration = ($endTime - $StartTime).TotalSeconds
    
    if ($exitCode -eq 0) {{
        Write-Log "INFO" "Backup completed successfully in ${{duration}}s"
        Send-Webhook "success" "Backup completed successfully"
    }} else {{
        Write-Log "ERROR" "Backup failed after ${{duration}}s"
        Send-Webhook "failure" "Backup failed"
    }}
    
    exit $exitCode
}} catch {{
    Write-Log "ERROR" "Unexpected error: $_"
    Send-Webhook "failure" "Unexpected error: $_"
    exit 1
}}
'''
    
    def get_script_path(self, schedule_id: str) -> Path:
        """
        Get path to wrapper script for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Path: Path to wrapper script
        """
        script_dir = self._script_dirs.get(self.platform)
        if not script_dir:
            raise UnsupportedPlatformError(f"Platform {self.platform} not supported")
        
        if self.platform == 'windows':
            return script_dir / f"timelocker-{schedule_id}.ps1"
        else:
            return script_dir / f"timelocker-{schedule_id}.sh"
    
    def get_log_path(self, schedule_id: str) -> Path:
        """
        Get path to log file for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Path: Path to log file
        """
        log_dir = self._log_dirs.get(self.platform)
        if not log_dir:
            raise UnsupportedPlatformError(f"Platform {self.platform} not supported")
        
        return log_dir / f"timelocker-{schedule_id}.log"
    
    async def delete_wrapper_script(self, schedule_id: str) -> bool:
        """
        Delete wrapper script for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            script_path = self.get_script_path(schedule_id)
            
            if script_path.exists():
                script_path.unlink()
                self.logger.info(f"Deleted wrapper script: {script_path}")
                return True
            else:
                self.logger.warning(f"Wrapper script not found: {script_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete wrapper script: {e}")
            return False
