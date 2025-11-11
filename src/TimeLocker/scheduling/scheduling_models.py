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

Scheduling Data Models

This module defines type-safe data models for the scheduling system
using dataclasses for clear structure and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, date, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any


class SchedulePatternType(Enum):
    """Type of schedule pattern."""
    CRON = "cron"
    INTERVAL = "interval"
    CALENDAR = "calendar"


class ExecutionTrigger(Enum):
    """How a backup execution was triggered."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    RETRY = "retry"
    TEST = "test"


class ExecutionStatus(Enum):
    """Status of a backup execution."""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ScheduleHealthStatus(Enum):
    """Health status of a scheduled backup."""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class CalendarConfig:
    """Calendar-based scheduling configuration."""
    days_of_week: List[int]  # 0=Monday, 6=Sunday
    time_of_day: time
    weeks_of_month: Optional[List[int]] = None  # 1-4, None=all weeks
    months_of_year: Optional[List[int]] = None  # 1-12, None=all months
    
    def __post_init__(self):
        """Validate calendar configuration."""
        if not self.days_of_week or not all(0 <= d <= 6 for d in self.days_of_week):
            raise ValueError("days_of_week must contain values 0-6")
        
        if self.weeks_of_month and not all(1 <= w <= 4 for w in self.weeks_of_month):
            raise ValueError("weeks_of_month must contain values 1-4")
        
        if self.months_of_year and not all(1 <= m <= 12 for m in self.months_of_year):
            raise ValueError("months_of_year must contain values 1-12")


@dataclass
class BackupWindow:
    """Defines allowed backup execution time windows."""
    start_time: time
    end_time: time
    excluded_dates: List[date] = field(default_factory=list)
    timezone: str = "UTC"


@dataclass
class SchedulePattern:
    """Defines when a backup should be executed."""
    pattern_type: SchedulePatternType
    cron_expression: Optional[str] = None  # For cron-style scheduling
    interval_minutes: Optional[int] = None  # For interval-based scheduling
    calendar_config: Optional[CalendarConfig] = None  # For calendar-based scheduling
    randomize_delay_minutes: int = 0  # Random delay to distribute load
    backup_window: Optional[BackupWindow] = None
    
    def __post_init__(self):
        """Validate schedule pattern configuration."""
        if self.pattern_type == SchedulePatternType.CRON and not self.cron_expression:
            raise ValueError("cron_expression required for CRON pattern type")
        
        if self.pattern_type == SchedulePatternType.INTERVAL and not self.interval_minutes:
            raise ValueError("interval_minutes required for INTERVAL pattern type")
        
        if self.pattern_type == SchedulePatternType.CALENDAR and not self.calendar_config:
            raise ValueError("calendar_config required for CALENDAR pattern type")
        
        if self.randomize_delay_minutes < 0:
            raise ValueError("randomize_delay_minutes must be non-negative")


@dataclass
class RetryConfig:
    """Retry configuration for failed backup executions."""
    max_attempts: int = 3
    initial_delay_minutes: int = 5
    backoff_multiplier: float = 2.0
    max_delay_minutes: int = 60
    
    def __post_init__(self):
        """Validate retry configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay_minutes < 1:
            raise ValueError("initial_delay_minutes must be at least 1")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be at least 1.0")
        if self.max_delay_minutes < self.initial_delay_minutes:
            raise ValueError("max_delay_minutes must be >= initial_delay_minutes")


@dataclass
class MonitoringConfig:
    """Monitoring integration configuration."""
    webhook_url: Optional[str] = None
    health_check_url: Optional[str] = None
    notification_on_success: bool = True
    notification_on_failure: bool = True
    notification_on_retry: bool = False


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled backup."""
    schedule_id: str
    name: str
    description: Optional[str]
    policy_id: str
    schedule_pattern: SchedulePattern
    enabled: bool
    execution_timeout: Optional[int] = None  # seconds
    retry_config: Optional[RetryConfig] = None
    monitoring_config: Optional[MonitoringConfig] = None
    platform_specific_config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""


@dataclass
class ExecutionContext:
    """Context information for backup execution."""
    execution_id: str
    schedule_id: str
    triggered_by: ExecutionTrigger
    start_time: datetime
    platform: str
    user_context: str
    environment_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of a scheduled backup execution."""
    execution_id: str
    schedule_id: str
    status: ExecutionStatus
    backup_result: Optional[Any] = None  # BackupResult from backup operations
    execution_time: timedelta = field(default_factory=timedelta)
    error_details: Optional[List[str]] = None
    retry_count: int = 0
    next_retry_time: Optional[datetime] = None


@dataclass
class PlatformScheduleStatus:
    """Platform-specific schedule status."""
    platform_id: str
    is_active: bool
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    platform_specific_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleStatus:
    """Current status of a scheduled backup."""
    schedule_id: str
    enabled: bool
    last_execution: Optional[ExecutionResult]
    next_execution_time: Optional[datetime]
    platform_status: PlatformScheduleStatus
    health_status: ScheduleHealthStatus
    execution_history: List[ExecutionResult] = field(default_factory=list)


@dataclass
class PlatformScheduleResult:
    """Result of platform scheduler operation."""
    success: bool
    platform_id: str
    next_run: Optional[datetime] = None
    error_message: Optional[str] = None
    platform_specific_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformScheduleInfo:
    """Information about a platform-scheduled task."""
    platform_id: str
    schedule_id: str
    is_active: bool
    next_run_time: Optional[datetime] = None
    platform_specific_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleRequest:
    """Request to create a new scheduled backup."""
    name: str
    description: Optional[str]
    policy_id: str
    schedule_pattern: SchedulePattern
    enabled: bool = True
    execution_timeout: Optional[int] = None
    retry_config: Optional[RetryConfig] = None
    monitoring_config: Optional[MonitoringConfig] = None
    platform_specific_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduleUpdates:
    """Updates to apply to an existing schedule."""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_pattern: Optional[SchedulePattern] = None
    enabled: Optional[bool] = None
    execution_timeout: Optional[int] = None
    retry_config: Optional[RetryConfig] = None
    monitoring_config: Optional[MonitoringConfig] = None
    platform_specific_config: Optional[Dict[str, Any]] = None


@dataclass
class ScheduleFilters:
    """Filters for listing scheduled backups."""
    enabled_only: bool = False
    policy_id: Optional[str] = None
    health_status: Optional[ScheduleHealthStatus] = None
    name_pattern: Optional[str] = None


@dataclass
class ScheduleInfo:
    """Summary information about a scheduled backup."""
    schedule_id: str
    name: str
    description: Optional[str]
    policy_id: str
    enabled: bool
    next_execution_time: Optional[datetime]
    health_status: ScheduleHealthStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)
