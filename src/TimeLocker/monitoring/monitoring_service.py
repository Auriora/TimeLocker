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

from .status_reporter import StatusReporter, OperationStatus, StatusLevel
from .notification_service import NotificationService
from .activity_logger import ActivityLogger, LogLevel as ActivityLogLevel
from .backup_history import BackupHistory, BackupRecord, BackupStatus
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Overall system health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class BackupEvent:
    """Represents a backup-related event"""
    event_id: str
    event_type: str
    timestamp: datetime
    repository_id: Optional[str]
    operation_id: str
    message: str
    details: Dict[str, Any]
    severity: StatusLevel


@dataclass
class RecoveryEvent:
    """Represents a recovery-related event"""
    event_id: str
    event_type: str
    timestamp: datetime
    repository_id: Optional[str]
    operation_id: str
    message: str
    details: Dict[str, Any]
    severity: StatusLevel


@dataclass
class MonitoringSummary:
    """Comprehensive monitoring summary for UI display"""
    health_status: HealthStatus
    current_operations: List[OperationStatus]
    recent_operations: List[OperationStatus]
    repository_statuses: Dict[str, Dict[str, Any]]
    last_backup_dates: Dict[str, datetime]
    issues_requiring_attention: List[Dict[str, Any]]
    generated_at: datetime


@dataclass
class MonitoringPreferences:
    """User preferences for monitoring behavior"""
    log_level: str = "INFO"
    log_retention_days: int = 7
    log_rotation_size_mb: int = 10
    status_retention_days: int = 30
    enable_desktop_notifications: bool = True
    enable_email_notifications: bool = False
    notify_on_success: bool = True
    notify_on_warning: bool = True
    notify_on_error: bool = True
    notify_on_critical: bool = True
    min_operation_duration_seconds: int = 60


class MonitoringService(ServiceInterface):
    """
    Central monitoring service that coordinates all monitoring activities.
    
    This service acts as the orchestrator for monitoring operations, integrating
    StatusReporter, NotificationService, and other monitoring components to provide
    comprehensive monitoring capabilities.
    
    Responsibilities:
    - Event collection and distribution
    - Integration with core TimeLocker systems
    - Coordination of monitoring components
    - Health status management
    - Configuration management for monitoring preferences
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize monitoring service.
        
        Args:
            config_dir: Directory for monitoring configuration and data
        """
        if config_dir is None:
            # Use centralized path resolver for XDG compliance
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "monitoring"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize core monitoring components
        self.status_reporter = StatusReporter(config_dir / "status")
        self.notifier = NotificationService(config_dir / "notifications")
        self.activity_logger = ActivityLogger(config_dir)
        self.backup_history = BackupHistory(config_dir / "history")
        
        # Load monitoring preferences
        self.preferences = self._load_preferences()
        
        # Register status reporter handler to trigger notifications and logging
        self.status_reporter.add_status_handler(self._handle_status_update)
        
        # ServiceInterface implementation
        self._context: Optional[ServiceContext] = None
        self._initialized = False

        logger.info("MonitoringService initialized")

    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the monitoring service with the provided context.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to MonitoringService")
                return False
            
            self._context = context
            
            # Initialize sub-services
            if not self.notifier.initialize(context):
                logger.warning("NotificationService initialization failed, continuing without notifications")
            
            logger.info("MonitoringService initialized successfully with context")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MonitoringService: {e}")
            return False

    def shutdown(self) -> None:
        """
        Shutdown the monitoring service and clean up resources.
        """
        try:
            # Save preferences
            self._save_preferences()
            
            # Shutdown sub-services
            if hasattr(self.notifier, 'shutdown'):
                self.notifier.shutdown()
            
            # Clean up resources
            self._context = None
            self._initialized = False
            logger.info("MonitoringService shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during MonitoringService shutdown: {e}")

    def health_check(self) -> bool:
        """
        Check the health status of the monitoring service.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        try:
            # Check if service is initialized
            if not self._initialized:
                return False
            
            # Check if config directory is accessible
            if not self.config_dir.exists():
                return False
            
            # Check sub-services
            if not self.notifier.health_check():
                logger.warning("NotificationService health check failed")
                # Don't fail overall health check for notification issues
            
            return True
            
        except Exception as e:
            logger.error(f"MonitoringService health check failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        return [
            'event_monitoring',
            'status_reporting',
            'notifications',
            'health_monitoring',
            'operation_tracking',
            'monitoring_preferences'
        ]

    def handle_backup_event(self, event: BackupEvent) -> None:
        """
        Handle backup-related events from backup operations.
        
        Args:
            event: BackupEvent containing event details
        """
        try:
            # Convert BackupEvent to OperationStatus for status reporter
            status = OperationStatus(
                operation_id=event.operation_id,
                operation_type=event.event_type,
                status=event.severity,
                message=event.message,
                timestamp=event.timestamp,
                repository_id=event.repository_id,
                files_processed=event.details.get('files_processed'),
                bytes_processed=event.details.get('bytes_processed'),
                metadata=event.details
            )
            
            # Update or start operation tracking
            if event.event_type.endswith('_started'):
                self.status_reporter.start_operation(
                    operation_id=event.operation_id,
                    operation_type='backup',
                    repository_id=event.repository_id,
                    metadata=event.details
                )
            elif event.event_type.endswith('_completed') or event.event_type.endswith('_failed'):
                # Update with final metrics before completing
                self.status_reporter.update_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    files_processed=event.details.get('files_processed'),
                    bytes_processed=event.details.get('bytes_processed'),
                    metadata=event.details
                )
                self.status_reporter.complete_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    metadata=event.details
                )
            else:
                # Progress update
                self.status_reporter.update_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    files_processed=event.details.get('files_processed'),
                    bytes_processed=event.details.get('bytes_processed'),
                    metadata=event.details
                )
            
            logger.debug(f"Handled backup event: {event.event_type} for operation {event.operation_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle backup event: {e}")

    def handle_recovery_event(self, event: RecoveryEvent) -> None:
        """
        Handle recovery-related events from recovery operations.
        
        Args:
            event: RecoveryEvent containing event details
        """
        try:
            # Convert RecoveryEvent to OperationStatus for status reporter
            status = OperationStatus(
                operation_id=event.operation_id,
                operation_type=event.event_type,
                status=event.severity,
                message=event.message,
                timestamp=event.timestamp,
                repository_id=event.repository_id,
                files_processed=event.details.get('files_processed'),
                bytes_processed=event.details.get('bytes_processed'),
                metadata=event.details
            )
            
            # Update or start operation tracking
            if event.event_type.endswith('_started'):
                self.status_reporter.start_operation(
                    operation_id=event.operation_id,
                    operation_type='recovery',
                    repository_id=event.repository_id,
                    metadata=event.details
                )
            elif event.event_type.endswith('_completed') or event.event_type.endswith('_failed'):
                # Update with final metrics before completing
                self.status_reporter.update_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    files_processed=event.details.get('files_processed'),
                    bytes_processed=event.details.get('bytes_processed'),
                    metadata=event.details
                )
                self.status_reporter.complete_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    metadata=event.details
                )
            else:
                # Progress update
                self.status_reporter.update_operation(
                    operation_id=event.operation_id,
                    status=event.severity,
                    message=event.message,
                    files_processed=event.details.get('files_processed'),
                    bytes_processed=event.details.get('bytes_processed'),
                    metadata=event.details
                )
            
            logger.debug(f"Handled recovery event: {event.event_type} for operation {event.operation_id}")
            
        except Exception as e:
            logger.error(f"Failed to handle recovery event: {e}")

    def get_system_health(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Returns:
            HealthStatus: Current system health status
        """
        try:
            # Check for current operations with errors
            current_ops = self.status_reporter.get_current_operations()
            
            # Check recent operation history
            recent_ops = self.status_reporter.get_operation_history(days=1)
            
            # Determine health based on recent operations
            has_critical = any(op.status == StatusLevel.CRITICAL for op in recent_ops)
            has_errors = any(op.status == StatusLevel.ERROR for op in recent_ops)
            has_warnings = any(op.status == StatusLevel.WARNING for op in recent_ops)
            
            if has_critical:
                return HealthStatus.ERROR
            elif has_errors:
                return HealthStatus.ERROR
            elif has_warnings:
                return HealthStatus.WARNING
            elif recent_ops:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
                
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return HealthStatus.UNKNOWN

    def get_monitoring_summary(self) -> MonitoringSummary:
        """
        Get comprehensive monitoring summary for UI display.
        
        Returns:
            MonitoringSummary: Complete monitoring summary
        """
        try:
            # Get current operations
            current_operations = self.status_reporter.get_current_operations()
            
            # Get recent operations (last 7 days)
            recent_operations = self.status_reporter.get_operation_history(days=7)
            
            # Build repository statuses
            repository_statuses = {}
            last_backup_dates = {}
            
            for op in recent_operations:
                if op.repository_id and op.operation_type == 'backup':
                    if op.repository_id not in last_backup_dates:
                        last_backup_dates[op.repository_id] = op.timestamp
                    
                    if op.repository_id not in repository_statuses:
                        repository_statuses[op.repository_id] = {
                            'last_status': op.status.value,
                            'last_message': op.message,
                            'last_update': op.timestamp.isoformat()
                        }
            
            # Identify issues requiring attention
            issues = []
            for op in recent_operations:
                if op.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]:
                    issues.append({
                        'operation_id': op.operation_id,
                        'operation_type': op.operation_type,
                        'severity': op.status.value,
                        'message': op.message,
                        'timestamp': op.timestamp.isoformat(),
                        'repository_id': op.repository_id
                    })
            
            return MonitoringSummary(
                health_status=self.get_system_health(),
                current_operations=current_operations,
                recent_operations=recent_operations[:20],  # Limit to 20 most recent
                repository_statuses=repository_statuses,
                last_backup_dates=last_backup_dates,
                issues_requiring_attention=issues[:10],  # Limit to 10 most recent issues
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get monitoring summary: {e}")
            # Return minimal summary on error
            return MonitoringSummary(
                health_status=HealthStatus.UNKNOWN,
                current_operations=[],
                recent_operations=[],
                repository_statuses={},
                last_backup_dates={},
                issues_requiring_attention=[],
                generated_at=datetime.now()
            )

    def update_preferences(self, preferences: MonitoringPreferences) -> None:
        """
        Update monitoring preferences.
        
        Args:
            preferences: New monitoring preferences
        """
        try:
            self.preferences = preferences
            self._save_preferences()
            
            # Update notification service configuration
            self.notifier.update_config(
                enabled=preferences.enable_desktop_notifications or preferences.enable_email_notifications,
                desktop_enabled=preferences.enable_desktop_notifications,
                email_enabled=preferences.enable_email_notifications,
                notify_on_success=preferences.notify_on_success,
                notify_on_warning=preferences.notify_on_warning,
                notify_on_error=preferences.notify_on_error,
                notify_on_critical=preferences.notify_on_critical,
                min_operation_duration=preferences.min_operation_duration_seconds
            )
            
            logger.info("Monitoring preferences updated")
            
        except Exception as e:
            logger.error(f"Failed to update monitoring preferences: {e}")
            raise

    def get_preferences(self) -> MonitoringPreferences:
        """
        Get current monitoring preferences.
        
        Returns:
            MonitoringPreferences: Current preferences
        """
        return self.preferences

    def get_activity_logger(self) -> ActivityLogger:
        """
        Get the activity logger instance.
        
        Returns:
            ActivityLogger: Activity logger instance
        """
        return self.activity_logger

    def get_backup_history(self) -> BackupHistory:
        """
        Get the backup history instance.
        
        Returns:
            BackupHistory: Backup history instance
        """
        return self.backup_history

    def _handle_status_update(self, status: OperationStatus) -> None:
        """
        Handle status updates from StatusReporter.
        
        This method is called whenever the StatusReporter updates an operation status.
        It triggers notifications, logging, and history recording based on the status.
        
        Args:
            status: Updated operation status
        """
        try:
            # Log the event
            self.activity_logger.log_backup_event(status)
            
            # Send notification if appropriate
            if self.notifier.should_notify(status):
                self.notifier.send_notification(status)
            
            # Record in history if operation is complete
            if status.progress_percentage == 100 or status.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]:
                self._record_in_history(status)
                
        except Exception as e:
            logger.error(f"Failed to handle status update: {e}")

    def _record_in_history(self, status: OperationStatus) -> None:
        """
        Record completed operation in backup history.
        
        Args:
            status: Operation status to record
        """
        try:
            # Only record backup operations
            if status.operation_type not in ['backup', 'backup_started', 'backup_completed', 'backup_failed']:
                return
            
            # Extract timing information
            start_time = status.timestamp
            end_time = status.timestamp
            duration_seconds = 0.0
            
            if status.metadata:
                if 'start_time' in status.metadata:
                    start_time = datetime.fromisoformat(status.metadata['start_time'])
                if 'end_time' in status.metadata:
                    end_time = datetime.fromisoformat(status.metadata['end_time'])
                if 'duration' in status.metadata:
                    duration_seconds = float(status.metadata['duration'])
                else:
                    duration_seconds = (end_time - start_time).total_seconds()
            
            # Map status to BackupStatus
            status_map = {
                StatusLevel.SUCCESS: BackupStatus.SUCCESS,
                StatusLevel.WARNING: BackupStatus.PARTIAL,
                StatusLevel.ERROR: BackupStatus.FAILED,
                StatusLevel.CRITICAL: BackupStatus.FAILED,
                StatusLevel.INFO: BackupStatus.SUCCESS
            }
            
            backup_status = status_map.get(status.status, BackupStatus.FAILED)
            
            # Create backup record
            record = BackupRecord(
                operation_id=status.operation_id,
                repository_id=status.repository_id or 'unknown',
                start_time=start_time,
                end_time=end_time,
                status=backup_status,
                files_processed=status.files_processed or 0,
                bytes_transferred=status.bytes_processed or 0,
                duration_seconds=duration_seconds,
                snapshot_id=status.metadata.get('snapshot_id') if status.metadata else None,
                error_message=status.message if status.status in [StatusLevel.ERROR, StatusLevel.CRITICAL] else None,
                warnings=status.metadata.get('warnings') if status.metadata else None,
                metadata=status.metadata
            )
            
            self.backup_history.record_backup_operation(record)
            
        except Exception as e:
            logger.error(f"Failed to record operation in history: {e}")

    def _load_preferences(self) -> MonitoringPreferences:
        """
        Load monitoring preferences from configuration.
        
        Returns:
            MonitoringPreferences: Loaded preferences or defaults
        """
        import json
        
        preferences_file = self.config_dir / "preferences.json"
        
        try:
            if preferences_file.exists():
                with open(preferences_file, 'r') as f:
                    data = json.load(f)
                    return MonitoringPreferences(**data)
        except Exception as e:
            logger.warning(f"Failed to load monitoring preferences: {e}")
        
        # Return default preferences
        return MonitoringPreferences()

    def _save_preferences(self) -> None:
        """Save monitoring preferences to configuration."""
        import json
        from dataclasses import asdict
        
        preferences_file = self.config_dir / "preferences.json"
        
        try:
            with open(preferences_file, 'w') as f:
                json.dump(asdict(self.preferences), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save monitoring preferences: {e}")
