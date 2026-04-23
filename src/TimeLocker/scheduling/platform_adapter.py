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

Platform Adapter Base Class

This module defines the abstract base class for platform-specific
scheduling adapters, providing a unified interface for all schedulers.
"""

from abc import ABC, abstractmethod
import logging

from .scheduling_models import (
    ScheduleConfig,
    PlatformScheduleResult,
    PlatformScheduleStatus,
    PlatformScheduleInfo,
    ValidationResult
)

logger: logging.Logger = logging.getLogger(__name__)


class PlatformAdapter(ABC):
    """
    Abstract base class for platform-specific scheduling adapters.
    
    This class defines the interface that all platform adapters must implement
    to provide consistent scheduling functionality across different platforms.
    
    Implementations must provide:
    - Schedule creation and management
    - Status monitoring
    - Platform-specific configuration validation
    """
    
    def __init__(self):
        """Initialize the platform adapter."""
        self.logger: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.logger.info(f"Initializing {self.__class__.__name__}")
    
    @abstractmethod
    async def create_schedule(self, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Create a platform-specific scheduled task.
        
        Args:
            config: Schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule creation
            
        Raises:
            PlatformSchedulerError: If schedule creation fails
        """
        pass
    
    @abstractmethod
    async def update_schedule(self, schedule_id: str, config: ScheduleConfig) -> PlatformScheduleResult:
        """
        Update an existing platform-specific scheduled task.
        
        Args:
            schedule_id: Unique identifier for the schedule
            config: Updated schedule configuration
            
        Returns:
            PlatformScheduleResult: Result of schedule update
            
        Raises:
            PlatformSchedulerError: If schedule update fails
        """
        pass
    
    @abstractmethod
    async def delete_schedule(self, schedule_id: str) -> bool:
        """
        Remove a platform-specific scheduled task.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            PlatformSchedulerError: If schedule deletion fails
        """
        pass
    
    @abstractmethod
    async def get_schedule_status(self, schedule_id: str) -> PlatformScheduleStatus:
        """
        Get platform-specific schedule status.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            PlatformScheduleStatus: Current status of the schedule
            
        Raises:
            PlatformSchedulerError: If status retrieval fails
        """
        pass
    
    @abstractmethod
    async def list_schedules(self) -> list[PlatformScheduleInfo]:
        """
        List all platform-specific scheduled tasks.
        
        Returns:
            List[PlatformScheduleInfo]: List of all scheduled tasks
            
        Raises:
            PlatformSchedulerError: If listing fails
        """
        pass
    
    @abstractmethod
    def validate_schedule_config(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration for platform compatibility.
        
        Args:
            config: Schedule configuration to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get the name of this platform adapter.
        
        Returns:
            str: Platform adapter name (e.g., "systemd", "cron", "windows_task_scheduler")
        """
        pass
    
    def _log_operation(self, operation: str, schedule_id: str, success: bool, details: str = "") -> None:
        """
        Log a platform adapter operation.
        
        Args:
            operation: Operation name (e.g., "create", "update", "delete")
            schedule_id: Schedule identifier
            success: Whether operation succeeded
            details: Additional details about the operation
        """
        level = logging.INFO if success else logging.ERROR
        status = "succeeded" if success else "failed"
        message = f"{operation.capitalize()} operation {status} for schedule {schedule_id}"
        if details:
            message += f": {details}"
        self.logger.log(level, message)
