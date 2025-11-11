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


class LaunchdAdapter(PlatformAdapter):
    """
    Launchd adapter for macOS.
    
    This adapter creates and manages launchd plists for scheduled
    backup operations.
    """
    
    def __init__(self):
        """Initialize launchd adapter."""
        super().__init__()
        self.launchd_dir = Path.home() / "Library" / "LaunchAgents"
        self.launchd_dir.mkdir(parents=True, exist_ok=True)
        self.script_dir = Path.home() / "Library" / "Application Support" / "TimeLocker" / "Scripts"
        self.script_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """Create launchd plist and wrapper script."""
        # Implementation will be added in task 3.4
        raise NotImplementedError("LaunchdAdapter.create_schedule will be implemented in task 3.4")
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """Update an existing launchd job."""
        # Implementation will be added in task 3.4
        raise NotImplementedError("LaunchdAdapter.update_schedule will be implemented in task 3.4")
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Remove a launchd job."""
        # Implementation will be added in task 3.4
        raise NotImplementedError("LaunchdAdapter.delete_schedule will be implemented in task 3.4")
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """Get launchd job status."""
        # Implementation will be added in task 3.4
        raise NotImplementedError("LaunchdAdapter.get_schedule_status will be implemented in task 3.4")
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """List all launchd jobs."""
        # Implementation will be added in task 3.4
        raise NotImplementedError("LaunchdAdapter.list_schedules will be implemented in task 3.4")
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """Validate schedule configuration for launchd compatibility."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation - detailed implementation in task 3.4
        if not config.schedule_id:
            result.add_error("schedule_id is required")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "launchd"
