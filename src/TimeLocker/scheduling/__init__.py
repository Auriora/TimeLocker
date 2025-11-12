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

TimeLocker Scheduling & Automation Module

This module provides comprehensive automated backup scheduling capabilities
through platform-appropriate system schedulers (systemd, cron, Windows Task
Scheduler, launchd).

Key Components:
- ScheduleManager: Central orchestrator for scheduling operations
- PlatformAdapter: Abstract base for platform-specific implementations
- PlatformDetector: Automatic platform and scheduler detection
- SchedulingConfiguration: Configuration management with validation
- Data Models: Type-safe scheduling configuration models

Usage:
    from TimeLocker.scheduling import ScheduleManager, PlatformDetector
    
    # Detect best scheduler for current platform
    adapter_class = PlatformDetector.detect_best_scheduler()
    
    # Create schedule manager
    schedule_manager = ScheduleManager()
    
    # Create scheduled backup
    result = await schedule_manager.create_scheduled_backup(schedule_request)
"""

# Core scheduling components
from .schedule_manager import ScheduleManager
from .platform_detector import PlatformDetector
from .platform_adapter import PlatformAdapter

# Platform-specific adapters
from .systemd_adapter import SystemdAdapter
from .cron_adapter import CronAdapter
from .windows_adapter import WindowsTaskSchedulerAdapter
from .launchd_adapter import LaunchdAdapter

# Configuration
from .scheduling_configuration import (
    SchedulingConfiguration,
    SchedulingConfigurationValidator
)

# Data models
from .scheduling_models import (
    ScheduleConfig,
    SchedulePattern,
    SchedulePatternType,
    CalendarConfig,
    BackupWindow,
    RetryConfig,
    MonitoringConfig,
    ExecutionContext,
    ExecutionTrigger,
    ExecutionResult,
    ExecutionStatus,
    ScheduleStatus,
    ScheduleHealthStatus,
    PlatformScheduleResult,
    PlatformScheduleStatus,
    PlatformScheduleInfo,
    ScheduleRequest,
    ScheduleUpdates,
    ScheduleFilters,
    ScheduleInfo,
    ValidationResult
)

# Exceptions
from .scheduling_exceptions import (
    SchedulingError,
    PlatformSchedulerError,
    PolicyValidationError,
    DataSelectionValidationError,
    RepositoryValidationError,
    CredentialAccessError,
    ExecutionTimeoutError,
    ScheduleConflictError,
    UnsupportedPlatformError
)

# Integration clients
from .integration_clients import (
    PolicyManagementClient,
    DataSelectionClient,
    RepositoryManagementClient,
    MonitoringClient
)

# Audit logging
from .audit_logger import SchedulingAuditLogger, AuditEventType, AuditEntry

# Storage
from .schedule_storage import ScheduleStorage

# Script generation
from .script_generator import ScriptGenerator

# Credential integration
from .credential_integration import (
    PlatformCredentialStore,
    SchedulingCredentialManager,
    SecureEnvironmentHandler
)

# Automation engine
from .automation_engine import AutomationEngine, ErrorSeverity

__all__ = [
    # Core components
    'ScheduleManager',
    'PlatformDetector',
    'PlatformAdapter',
    
    # Platform adapters
    'SystemdAdapter',
    'CronAdapter',
    'WindowsTaskSchedulerAdapter',
    'LaunchdAdapter',
    
    # Configuration
    'SchedulingConfiguration',
    'SchedulingConfigurationValidator',
    
    # Data models
    'ScheduleConfig',
    'SchedulePattern',
    'SchedulePatternType',
    'CalendarConfig',
    'BackupWindow',
    'RetryConfig',
    'MonitoringConfig',
    'ExecutionContext',
    'ExecutionTrigger',
    'ExecutionResult',
    'ExecutionStatus',
    'ScheduleStatus',
    'ScheduleHealthStatus',
    'PlatformScheduleResult',
    'PlatformScheduleStatus',
    'PlatformScheduleInfo',
    'ScheduleRequest',
    'ScheduleUpdates',
    'ScheduleFilters',
    'ScheduleInfo',
    'ValidationResult',
    
    # Exceptions
    'SchedulingError',
    'PlatformSchedulerError',
    'PolicyValidationError',
    'DataSelectionValidationError',
    'RepositoryValidationError',
    'CredentialAccessError',
    'ExecutionTimeoutError',
    'ScheduleConflictError',
    'UnsupportedPlatformError',
    
    # Integration clients
    'PolicyManagementClient',
    'DataSelectionClient',
    'RepositoryManagementClient',
    'MonitoringClient',
    
    # Audit logging
    'SchedulingAuditLogger',
    'AuditEventType',
    'AuditEntry',
    
    # Storage
    'ScheduleStorage',
    
    # Script generation
    'ScriptGenerator',
    
    # Credential integration
    'PlatformCredentialStore',
    'SchedulingCredentialManager',
    'SecureEnvironmentHandler',
    
    # Automation engine
    'AutomationEngine',
    'ErrorSeverity'
]
