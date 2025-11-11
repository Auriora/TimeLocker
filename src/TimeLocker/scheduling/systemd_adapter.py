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
from .scheduling_exceptions import PlatformSchedulerError


class SystemdAdapter(PlatformAdapter):
    """
    Systemd timer adapter for Linux systems.
    
    This adapter creates and manages systemd user service and timer units
    for scheduled backup operations.
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
        """
        # Implementation will be added in task 3.1
        raise NotImplementedError("SystemdAdapter.create_schedule will be implemented in task 3.1")
    
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """Update an existing systemd timer."""
        # Implementation will be added in task 3.1
        raise NotImplementedError("SystemdAdapter.update_schedule will be implemented in task 3.1")
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Remove a systemd timer."""
        # Implementation will be added in task 3.1
        raise NotImplementedError("SystemdAdapter.delete_schedule will be implemented in task 3.1")
    
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """Get systemd timer status."""
        # Implementation will be added in task 3.1
        raise NotImplementedError("SystemdAdapter.get_schedule_status will be implemented in task 3.1")
    
    async def list_schedules(self) -> List[PlatformScheduleInfo]:
        """List all systemd timers."""
        # Implementation will be added in task 3.1
        raise NotImplementedError("SystemdAdapter.list_schedules will be implemented in task 3.1")
    
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """Validate schedule configuration for systemd compatibility."""
        result = ValidationResult(is_valid=True)
        
        # Basic validation - detailed implementation in task 3.1
        if not config.schedule_id:
            result.add_error("schedule_id is required")
        
        return result
    
    def get_platform_name(self) -> str:
        """Get platform adapter name."""
        return "systemd"
