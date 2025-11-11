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


class WindowsTaskSchedulerAdapter(PlatformAdapter):
    """
    Windows Task Scheduler adapter.
    
    This adapter creates and manages Windows scheduled tasks for
    backup operations.
    """
    
    def __init__(self):
        """Initialize Windows Task Scheduler adapter."""
        super().__init__()
        self.task_folder = "\\TimeLocker"
        self.powershell_wrapper_dir = Path.home() / "AppData" / "Local" / "TimeLocker" / "Scripts"
        self.powershell_wrapper_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """Create Windows scheduled task."""
        # Implementation will be added in task 3.3
        raise NotImplementedError("WindowsTaskSchedulerAdapter.create_schedule will be implemented in task 3.3")
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """Update an existing Windows scheduled task."""
        # Implementation will be added in task 3.3
        raise NotImplementedError("WindowsTaskSchedulerAdapter.update_schedule will be implemented in task 3.3")
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Remove a Windows scheduled task."""
        # Implementation will be added in task 3.3
        raise NotImplementedError("WindowsTaskSchedulerAdapter.delete_schedule will be implemented in task 3.3")
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """Get Windows scheduled task status."""
        # Implementation will be added in task 3.3
        raise NotImplementedError("WindowsTaskSchedulerAdapter.get_schedule_status will be implemented in task 3.3")
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """List all Windows scheduled tasks."""
        # Implementation will be added in task 3.3
        raise NotImplementedError("WindowsTaskSchedulerAdapter.list_schedules will be implemented in task 3.3")
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """Validate schedule configuration for Windows Task Scheduler compatibility."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation - detailed implementation in task 3.3
        if not config.schedule_id:
            result.add_error("schedule_id is required")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "windows_task_scheduler"
