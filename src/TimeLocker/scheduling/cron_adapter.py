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

from pathlib import Path
from typing import List

from .platform_adapter import PlatformAdapter
from .scheduling_models import (
    ScheduleConfig,
    PlatformScheduleResult,
    PlatformScheduleStatus,
    PlatformScheduleInfo,
    ValidationResult
)


class CronAdapter(PlatformAdapter):
    """
    Cron adapter for Unix-like systems.
    
    This adapter creates and manages cron jobs for scheduled backup operations.
    """
    
    def __init__(self):
        """Initialize cron adapter."""
        super().__init__()
        self.cron_comment_prefix = "# TimeLocker Scheduled Backup"
        self.wrapper_script_dir = Path.home() / ".local" / "bin"
        self.wrapper_script_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """Create cron job and wrapper script."""
        # Implementation will be added in task 3.2
        raise NotImplementedError("CronAdapter.create_schedule will be implemented in task 3.2")
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """Update an existing cron job."""
        # Implementation will be added in task 3.2
        raise NotImplementedError("CronAdapter.update_schedule will be implemented in task 3.2")
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Remove a cron job."""
        # Implementation will be added in task 3.2
        raise NotImplementedError("CronAdapter.delete_schedule will be implemented in task 3.2")
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """Get cron job status."""
        # Implementation will be added in task 3.2
        raise NotImplementedError("CronAdapter.get_schedule_status will be implemented in task 3.2")
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """List all cron jobs."""
        # Implementation will be added in task 3.2
        raise NotImplementedError("CronAdapter.list_schedules will be implemented in task 3.2")
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """Validate schedule configuration for cron compatibility."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation - detailed implementation in task 3.2
        if not config.schedule_id:
            result.add_error("schedule_id is required")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "cron"
