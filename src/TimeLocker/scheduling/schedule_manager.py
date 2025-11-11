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

Schedule Manager

This module provides the central orchestrator for scheduling operations,
coordinating between platform adapters and TimeLocker components.
"""

import logging
from typing import Optional, List
from pathlib import Path

from .platform_detector import PlatformDetector
from .platform_adapter import PlatformAdapter
from .scheduling_configuration import SchedulingConfiguration
from .scheduling_models import (
    ScheduleRequest,
    ScheduleConfig,
    ScheduleInfo,
    ScheduleStatus,
    ScheduleUpdates,
    ScheduleFilters
)
from .scheduling_exceptions import SchedulingError

logger = logging.getLogger(__name__)


class ScheduleManager:
    """
    Central orchestrator for scheduling operations.
    
    This class coordinates between platform-specific adapters and
    TimeLocker components to provide unified scheduling functionality.
    """
    
    def __init__(
        self,
        config: Optional[SchedulingConfiguration] = None,
        adapter: Optional[PlatformAdapter] = None
    ):
        """
        Initialize schedule manager.
        
        Args:
            config: Optional scheduling configuration (loads default if not provided)
            adapter: Optional platform adapter (auto-detects if not provided)
        """
        self.logger = logging.getLogger(f"{__name__}.ScheduleManager")
        
        # Load or use provided configuration
        if config is None:
            config_path = SchedulingConfiguration().get_default_config_path()
            if config_path.exists():
                self.config = SchedulingConfiguration.load_from_file(config_path)
            else:
                self.config = SchedulingConfiguration()
                self.logger.info("Using default scheduling configuration")
        else:
            self.config = config
        
        # Detect or use provided platform adapter
        if adapter is None:
            adapter_class = PlatformDetector.detect_best_scheduler()
            self.adapter = adapter_class()
            self.logger.info(f"Auto-detected platform adapter: {self.adapter.get_platform_name()}")
        else:
            self.adapter = adapter
            self.logger.info(f"Using provided platform adapter: {self.adapter.get_platform_name()}")
    
    async def create_scheduled_backup(self, request: ScheduleRequest) -> ScheduleInfo:
        """
        Create a new scheduled backup.
        
        Args:
            request: Schedule creation request
            
        Returns:
            ScheduleInfo: Information about the created schedule
            
        Raises:
            SchedulingError: If schedule creation fails
        """
        # Implementation will be added in task 2
        raise NotImplementedError("ScheduleManager.create_scheduled_backup will be implemented in task 2")
    
    async def update_scheduled_backup(
        self,
        schedule_id: str,
        updates: ScheduleUpdates
    ) -> ScheduleInfo:
        """
        Update an existing scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            updates: Updates to apply
            
        Returns:
            ScheduleInfo: Updated schedule information
            
        Raises:
            SchedulingError: If update fails
        """
        # Implementation will be added in task 2
        raise NotImplementedError("ScheduleManager.update_scheduled_backup will be implemented in task 2")
    
    async def delete_scheduled_backup(self, schedule_id: str) -> bool:
        """
        Delete a scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            SchedulingError: If deletion fails
        """
        # Implementation will be added in task 2
        raise NotImplementedError("ScheduleManager.delete_scheduled_backup will be implemented in task 2")
    
    async def get_schedule_status(self, schedule_id: str) -> ScheduleStatus:
        """
        Get current status of a scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            ScheduleStatus: Current schedule status
            
        Raises:
            SchedulingError: If status retrieval fails
        """
        # Implementation will be added in task 2
        raise NotImplementedError("ScheduleManager.get_schedule_status will be implemented in task 2")
    
    async def list_scheduled_backups(
        self,
        filters: Optional[ScheduleFilters] = None
    ) -> List[ScheduleInfo]:
        """
        List all scheduled backups with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[ScheduleInfo]: List of scheduled backups
            
        Raises:
            SchedulingError: If listing fails
        """
        # Implementation will be added in task 2
        raise NotImplementedError("ScheduleManager.list_scheduled_backups will be implemented in task 2")
    
    def get_platform_name(self) -> str:
        """
        Get the name of the current platform adapter.
        
        Returns:
            str: Platform adapter name
        """
        return self.adapter.get_platform_name()
