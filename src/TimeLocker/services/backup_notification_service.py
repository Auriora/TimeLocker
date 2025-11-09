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
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..monitoring.notification_service import NotificationService, NotificationType
from ..monitoring.status_reporter import OperationStatus, StatusLevel, StatusReporter
from .backup_error_reporter import BackupError, BackupWarning, ErrorSeverity

logger = logging.getLogger(__name__)


class BackupEventType(Enum):
    """Types of backup events that can trigger notifications"""
    BACKUP_STARTED = "backup_started"
    BACKUP_PROGRESS = "backup_progress"
    BACKUP_COMPLETED = "backup_completed"
    BACKUP_FAILED = "backup_failed"
    BACKUP_WARNING = "backup_warning"
    INTEGRITY_CHECK_STARTED = "integrity_check_started"
    INTEGRITY_CHECK_COMPLETED = "integrity_check_completed"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    RETRY_ATTEMPT = "retry_attempt"
    REPOSITORY_ERROR = "repository_error"


@dataclass
class NotificationFilter:
    """Configuration for filtering notifications"""
    min_duration_seconds: int = 60
    notify_on_progress: bool = False
    progress_interval_seconds: int = 300  # 5 minutes
    notify_on_warnings: bool = True
    notify_on_errors: bool = True
    notify_on_success: bool = True
    min_severity: ErrorSeverity = ErrorSeverity.LOW
    excluded_event_types: List[BackupEventType] = None
    
    def __post_init__(self):
        if self.excluded_event_types is None:
            self.excluded_event_types = []


@dataclass
class BackupNotificationTemplate:
    """Template for backup-specific notifications"""
    event_type: BackupEventType
    title_template: str
    message_template: str
    include_remediation: bool = False
    include_statistics: bool = True


class BackupNotificationService:
    """
    Enhanced notification service specifically for backup operations.
    
    Provides backup-specific notification templates, filtering based on
    operation duration and significance, and integration with error reporting.
    """
    
    def __init__(self, notification_service: NotificationService,
                 status_reporter: StatusReporter,
                 config_dir: Optional[Path] = None):
        """
        Initialize backup notification service.
        
        Args:
            notification_service: Base notification service
            status_reporter: Status reporter for operation tracking
            config_dir: Configuration directory
        """
        self.notification_service = notification_service
        self.status_reporter = status_reporter
        
        if config_dir is None:
            # Use centralized path resolver for XDG compliance
            # Notification logs are state data, so use XDG_STATE_HOME
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            import os
            
            xdg_state_home = os.environ.get('XDG_STATE_HOME')
            if xdg_state_home:
                state_dir = Path(xdg_state_home) / "timelocker"
            else:
                state_dir = Path.home() / ".local" / "state" / "timelocker"
            
            config_dir = state_dir / "backup_notifications"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.filter = NotificationFilter()
        self.templates = self._initialize_templates()
        
        # Track last notification times to avoid spam
        self._last_notification_times: Dict[str, datetime] = {}
    
    def notify_backup_event(self, event_type: BackupEventType,
                           operation_id: str,
                           repository_id: Optional[str] = None,
                           message: Optional[str] = None,
                           error: Optional[BackupError] = None,
                           warning: Optional[BackupWarning] = None,
                           statistics: Optional[Dict[str, Any]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send notification for a backup event.
        
        Args:
            event_type: Type of backup event
            operation_id: Operation identifier
            repository_id: Repository identifier
            message: Custom message (optional)
            error: Backup error details (optional)
            warning: Backup warning details (optional)
            statistics: Backup statistics (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            bool: True if notification was sent
        """
        # Check if notification should be filtered
        if not self._should_notify(event_type, operation_id, error, warning):
            return False
        
        # Get or create template
        template = self.templates.get(event_type)
        if not template:
            logger.warning(f"No template found for event type: {event_type}")
            return False
        
        # Format notification
        title, formatted_message = self._format_notification(
            template, operation_id, repository_id, message,
            error, warning, statistics, metadata
        )
        
        # Determine status level
        status_level = self._determine_status_level(event_type, error, warning)
        
        # Create operation status for notification
        status = OperationStatus(
            operation_id=operation_id,
            operation_type="backup",
            status=status_level,
            message=formatted_message,
            timestamp=datetime.now(),
            repository_id=repository_id,
            metadata=metadata or {}
        )
        
        # Add statistics to status if available
        if statistics:
            status.files_processed = statistics.get('files_processed')
            status.total_files = statistics.get('total_files')
            status.bytes_processed = statistics.get('bytes_processed')
            status.total_bytes = statistics.get('total_bytes')
            status.progress_percentage = statistics.get('progress_percentage')
        
        # Send notification
        try:
            self.notification_service.send_notification(status)
            self._last_notification_times[operation_id] = datetime.now()
            logger.info(f"Sent backup notification: {event_type.value} for {operation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send backup notification: {e}")
            return False
    
    def notify_backup_error(self, operation_id: str, error: BackupError,
                           repository_id: Optional[str] = None) -> bool:
        """
        Send notification for a backup error with remediation steps.
        
        Args:
            operation_id: Operation identifier
            error: Backup error details
            repository_id: Repository identifier
            
        Returns:
            bool: True if notification was sent
        """
        return self.notify_backup_event(
            event_type=BackupEventType.BACKUP_FAILED,
            operation_id=operation_id,
            repository_id=repository_id or error.repository_id,
            error=error
        )
    
    def notify_backup_warning(self, operation_id: str, warning: BackupWarning,
                             repository_id: Optional[str] = None) -> bool:
        """
        Send notification for a backup warning.
        
        Args:
            operation_id: Operation identifier
            warning: Backup warning details
            repository_id: Repository identifier
            
        Returns:
            bool: True if notification was sent
        """
        return self.notify_backup_event(
            event_type=BackupEventType.BACKUP_WARNING,
            operation_id=operation_id,
            repository_id=repository_id or warning.repository_id,
            warning=warning
        )
    
    def notify_backup_progress(self, operation_id: str, repository_id: str,
                              statistics: Dict[str, Any]) -> bool:
        """
        Send progress notification for a backup operation.
        
        Args:
            operation_id: Operation identifier
            repository_id: Repository identifier
            statistics: Current backup statistics
            
        Returns:
            bool: True if notification was sent
        """
        return self.notify_backup_event(
            event_type=BackupEventType.BACKUP_PROGRESS,
            operation_id=operation_id,
            repository_id=repository_id,
            statistics=statistics
        )
    
    def _should_notify(self, event_type: BackupEventType, operation_id: str,
                      error: Optional[BackupError] = None,
                      warning: Optional[BackupWarning] = None) -> bool:
        """Determine if notification should be sent based on filters"""
        # Check if event type is excluded
        if event_type in self.filter.excluded_event_types:
            return False
        
        # Check severity filter for errors
        if error and error.severity.value < self.filter.min_severity.value:
            return False
        
        # Check severity filter for warnings
        if warning and warning.severity.value < self.filter.min_severity.value:
            return False
        
        # Check event type filters
        if event_type == BackupEventType.BACKUP_WARNING and not self.filter.notify_on_warnings:
            return False
        
        if event_type in [BackupEventType.BACKUP_FAILED, BackupEventType.REPOSITORY_ERROR]:
            if not self.filter.notify_on_errors:
                return False
        
        if event_type == BackupEventType.BACKUP_COMPLETED and not self.filter.notify_on_success:
            return False
        
        # Check progress notification interval
        if event_type == BackupEventType.BACKUP_PROGRESS:
            if not self.filter.notify_on_progress:
                return False
            
            last_time = self._last_notification_times.get(operation_id)
            if last_time:
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < self.filter.progress_interval_seconds:
                    return False
        
        # Check minimum duration for completion notifications
        if event_type == BackupEventType.BACKUP_COMPLETED:
            status = self.status_reporter.get_operation_status(operation_id)
            if status and status.metadata:
                start_time_str = status.metadata.get('start_time')
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        duration = (datetime.now() - start_time).total_seconds()
                        if duration < self.filter.min_duration_seconds:
                            return False
                    except (ValueError, TypeError):
                        pass
        
        return True
    
    def _format_notification(self, template: BackupNotificationTemplate,
                            operation_id: str,
                            repository_id: Optional[str],
                            message: Optional[str],
                            error: Optional[BackupError],
                            warning: Optional[BackupWarning],
                            statistics: Optional[Dict[str, Any]],
                            metadata: Optional[Dict[str, Any]]) -> tuple[str, str]:
        """Format notification title and message using template"""
        # Format title
        title = template.title_template.format(
            repository_id=repository_id or "Unknown",
            operation_id=operation_id
        )
        
        # Start with base message
        message_parts = []
        
        if message:
            message_parts.append(message)
        elif error:
            message_parts.append(f"Error: {error.message}")
        elif warning:
            message_parts.append(f"Warning: {warning.message}")
        else:
            message_parts.append(template.message_template.format(
                repository_id=repository_id or "Unknown",
                operation_id=operation_id
            ))
        
        # Add statistics if requested
        if template.include_statistics and statistics:
            stats_parts = []
            
            if 'files_processed' in statistics and 'total_files' in statistics:
                stats_parts.append(
                    f"Files: {statistics['files_processed']}/{statistics['total_files']}"
                )
            
            if 'bytes_processed' in statistics:
                size_mb = statistics['bytes_processed'] / (1024 * 1024)
                stats_parts.append(f"Data: {size_mb:.1f} MB")
            
            if 'progress_percentage' in statistics:
                stats_parts.append(f"Progress: {statistics['progress_percentage']}%")
            
            if 'duration' in statistics:
                duration = statistics['duration']
                if isinstance(duration, timedelta):
                    duration_str = str(duration).split('.')[0]  # Remove microseconds
                    stats_parts.append(f"Duration: {duration_str}")
            
            if stats_parts:
                message_parts.append("\n" + "\n".join(stats_parts))
        
        # Add remediation steps for errors
        if template.include_remediation and error and error.remediation_steps:
            message_parts.append("\n\nRemediation Steps:")
            for i, step in enumerate(error.remediation_steps[:3], 1):  # Limit to 3 steps
                message_parts.append(f"{i}. {step.description}")
                if step.command:
                    message_parts.append(f"   Command: {step.command}")
        
        # Add warning suggestions
        if warning and warning.suggestions:
            message_parts.append("\n\nSuggestions:")
            for suggestion in warning.suggestions[:3]:  # Limit to 3 suggestions
                message_parts.append(f"• {suggestion}")
        
        formatted_message = "\n".join(message_parts)
        return title, formatted_message
    
    def _determine_status_level(self, event_type: BackupEventType,
                                error: Optional[BackupError],
                                warning: Optional[BackupWarning]) -> StatusLevel:
        """Determine status level for notification"""
        if error:
            if error.severity == ErrorSeverity.CRITICAL:
                return StatusLevel.CRITICAL
            elif error.severity == ErrorSeverity.HIGH:
                return StatusLevel.ERROR
            else:
                return StatusLevel.WARNING
        
        if warning:
            return StatusLevel.WARNING
        
        if event_type in [BackupEventType.BACKUP_FAILED, BackupEventType.REPOSITORY_ERROR]:
            return StatusLevel.ERROR
        
        if event_type == BackupEventType.BACKUP_WARNING:
            return StatusLevel.WARNING
        
        if event_type == BackupEventType.BACKUP_COMPLETED:
            return StatusLevel.SUCCESS
        
        return StatusLevel.INFO
    
    def _initialize_templates(self) -> Dict[BackupEventType, BackupNotificationTemplate]:
        """Initialize notification templates for backup events"""
        return {
            BackupEventType.BACKUP_STARTED: BackupNotificationTemplate(
                event_type=BackupEventType.BACKUP_STARTED,
                title_template="Backup Started - {repository_id}",
                message_template="Backup operation started for repository {repository_id}",
                include_statistics=False
            ),
            BackupEventType.BACKUP_PROGRESS: BackupNotificationTemplate(
                event_type=BackupEventType.BACKUP_PROGRESS,
                title_template="Backup Progress - {repository_id}",
                message_template="Backup in progress for repository {repository_id}",
                include_statistics=True
            ),
            BackupEventType.BACKUP_COMPLETED: BackupNotificationTemplate(
                event_type=BackupEventType.BACKUP_COMPLETED,
                title_template="✅ Backup Completed - {repository_id}",
                message_template="Backup completed successfully for repository {repository_id}",
                include_statistics=True
            ),
            BackupEventType.BACKUP_FAILED: BackupNotificationTemplate(
                event_type=BackupEventType.BACKUP_FAILED,
                title_template="❌ Backup Failed - {repository_id}",
                message_template="Backup failed for repository {repository_id}",
                include_remediation=True,
                include_statistics=True
            ),
            BackupEventType.BACKUP_WARNING: BackupNotificationTemplate(
                event_type=BackupEventType.BACKUP_WARNING,
                title_template="⚠️ Backup Warning - {repository_id}",
                message_template="Warning during backup for repository {repository_id}",
                include_statistics=False
            ),
            BackupEventType.INTEGRITY_CHECK_STARTED: BackupNotificationTemplate(
                event_type=BackupEventType.INTEGRITY_CHECK_STARTED,
                title_template="Integrity Check Started - {repository_id}",
                message_template="Integrity validation started for repository {repository_id}",
                include_statistics=False
            ),
            BackupEventType.INTEGRITY_CHECK_COMPLETED: BackupNotificationTemplate(
                event_type=BackupEventType.INTEGRITY_CHECK_COMPLETED,
                title_template="✅ Integrity Check Passed - {repository_id}",
                message_template="Integrity validation completed successfully for repository {repository_id}",
                include_statistics=True
            ),
            BackupEventType.INTEGRITY_CHECK_FAILED: BackupNotificationTemplate(
                event_type=BackupEventType.INTEGRITY_CHECK_FAILED,
                title_template="❌ Integrity Check Failed - {repository_id}",
                message_template="Integrity validation failed for repository {repository_id}",
                include_remediation=True,
                include_statistics=False
            ),
            BackupEventType.RETRY_ATTEMPT: BackupNotificationTemplate(
                event_type=BackupEventType.RETRY_ATTEMPT,
                title_template="Retry Attempt - {repository_id}",
                message_template="Retrying backup operation for repository {repository_id}",
                include_statistics=False
            ),
            BackupEventType.REPOSITORY_ERROR: BackupNotificationTemplate(
                event_type=BackupEventType.REPOSITORY_ERROR,
                title_template="❌ Repository Error - {repository_id}",
                message_template="Repository error for {repository_id}",
                include_remediation=True,
                include_statistics=False
            )
        }
    
    def update_filter(self, **kwargs):
        """Update notification filter settings"""
        for key, value in kwargs.items():
            if hasattr(self.filter, key):
                setattr(self.filter, key, value)
        
        logger.info(f"Updated notification filter: {kwargs}")
    
    def get_filter_config(self) -> Dict[str, Any]:
        """Get current filter configuration"""
        return {
            'min_duration_seconds': self.filter.min_duration_seconds,
            'notify_on_progress': self.filter.notify_on_progress,
            'progress_interval_seconds': self.filter.progress_interval_seconds,
            'notify_on_warnings': self.filter.notify_on_warnings,
            'notify_on_errors': self.filter.notify_on_errors,
            'notify_on_success': self.filter.notify_on_success,
            'min_severity': self.filter.min_severity.value,
            'excluded_event_types': [et.value for et in self.filter.excluded_event_types]
        }
