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
from .storage_monitor import StorageMonitor, StorageUsage, CapacityWarning, StorageTrends, OptimizationRecommendation
from .integrity_checker import IntegrityChecker, IntegrityStatus, IntegrityLevel, CheckInterval
from .performance_tracker import PerformanceTracker, BackupPerformanceMetrics, PerformanceSummary
from .performance_optimizer import PerformanceOptimizer, PerformanceRecommendation
from .troubleshooting_service import (
    TroubleshootingService,
    BackupFailure,
    TroubleshootingReport,
    EventCorrelation,
    ProactiveRecommendation,
    DetectedIssue
)
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

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        notification_service: Optional[NotificationService] = None,
    ):
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
        self.notifier = notification_service or NotificationService(config_dir / "notifications")
        self.activity_logger = ActivityLogger(config_dir)
        self.backup_history = BackupHistory(config_dir / "history")
        self.storage_monitor = StorageMonitor(config_dir / "storage")
        self.integrity_checker = IntegrityChecker(config_dir / "integrity")
        self.performance_tracker = PerformanceTracker(config_dir / "performance")
        self.performance_optimizer = PerformanceOptimizer(self.performance_tracker)
        
        # Initialize troubleshooting service with configuration integration
        config_module = None
        try:
            from ..config import ConfigurationModule
            config_module = ConfigurationModule(self.config_dir.parent)
        except Exception as e:
            logger.warning(f"Could not initialize configuration module for troubleshooting: {e}")
        
        self.troubleshooting_service = TroubleshootingService(
            config_dir / "troubleshooting",
            config_module=config_module
        )
        
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
            'monitoring_preferences',
            'performance_tracking',
            'performance_optimization',
            'troubleshooting',
            'event_correlation',
            'proactive_issue_detection'
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
                
                # Record performance metrics for completed backups
                if (event.event_type.endswith('_completed') and 
                    event.repository_id and
                    event.details.get('start_time') and
                    event.details.get('end_time')):
                    try:
                        start_time = datetime.fromisoformat(event.details['start_time'])
                        end_time = datetime.fromisoformat(event.details['end_time'])
                        
                        self.performance_tracker.record_backup_performance(
                            operation_id=event.operation_id,
                            repository_id=event.repository_id,
                            start_time=start_time,
                            end_time=end_time,
                            files_processed=event.details.get('files_processed', 0),
                            bytes_processed=event.details.get('bytes_processed', 0),
                            metadata=event.details
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record performance metrics: {e}")
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

    def get_storage_monitor(self) -> StorageMonitor:
        """
        Get the storage monitor instance.
        
        Returns:
            StorageMonitor: Storage monitor instance
        """
        return self.storage_monitor

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

    def schedule_integrity_check(self, repository_id: str, interval: CheckInterval) -> None:
        """
        Schedule periodic integrity checks for a repository.
        
        Args:
            repository_id: Repository to schedule checks for
            interval: Check interval (daily, weekly, etc.)
            
        Requirements: 5.1
        """
        try:
            self.integrity_checker.schedule_integrity_check(repository_id, interval)
            logger.info(f"Scheduled {interval.value} integrity checks for repository {repository_id}")
        except Exception as e:
            logger.error(f"Failed to schedule integrity check: {e}")
            raise
    
    def run_integrity_check(self, repository, snapshot_id: Optional[str] = None) -> 'IntegrityCheckResult':
        """
        Run integrity check for a repository.
        
        Args:
            repository: Repository instance to verify
            snapshot_id: Specific snapshot to verify (optional)
            
        Returns:
            IntegrityCheckResult: Result of the integrity check
            
        Requirements: 5.1, 5.3, 5.4
        """
        try:
            # Run the integrity check
            result = self.integrity_checker.run_integrity_check(repository, snapshot_id)
            
            # Log the check result as an operation status
            status_level = StatusLevel.INFO if result.status == IntegrityLevel.HEALTHY else StatusLevel.ERROR
            operation_status = OperationStatus(
                operation_id=result.check_id,
                operation_type="integrity_check",
                status=status_level,
                message=f"Integrity check {result.status.value}: {len(result.issues_found)} issues found",
                timestamp=result.check_time,
                repository_id=result.repository_id,
                metadata={
                    'check_id': result.check_id,
                    'snapshots_checked': result.snapshots_checked,
                    'duration_seconds': result.duration.total_seconds()
                }
            )
            self.activity_logger.log_backup_event(operation_status)
            
            # Send notification if issues found
            if result.issues_found:
                from .notification_service import NotificationEventType
                
                status = OperationStatus(
                    operation_id=result.check_id,
                    operation_type="integrity_check",
                    status=StatusLevel.ERROR if result.status == IntegrityLevel.ERROR else StatusLevel.WARNING,
                    message=f"Integrity check found {len(result.issues_found)} issue(s)",
                    timestamp=result.check_time,
                    repository_id=result.repository_id,
                    metadata={
                        'issues_count': len(result.issues_found),
                        'status': result.status.value
                    }
                )
                
                # Check if integrity check events are enabled
                event_type = NotificationEventType.INTEGRITY_CHECK_FAILED.value
                if self.notifier.is_event_type_enabled(event_type):
                    self.notifier.send_notification(status)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to run integrity check: {e}")
            raise
    
    def get_integrity_status(self, repository_id: str) -> IntegrityStatus:
        """
        Get current integrity status for a repository.
        
        Args:
            repository_id: Repository to get status for
            
        Returns:
            IntegrityStatus: Current integrity status
            
        Requirements: 5.3
        """
        try:
            return self.integrity_checker.get_integrity_status(repository_id)
        except Exception as e:
            logger.error(f"Failed to get integrity status: {e}")
            raise
    
    def get_remediation_guidance(self, repository_id: str) -> Optional['RemediationGuide']:
        """
        Get user-friendly remediation guidance for integrity issues.
        
        Args:
            repository_id: Repository to get guidance for
            
        Returns:
            RemediationGuide: Remediation guidance or None if no issues
            
        Requirements: 5.2, 5.5
        """
        try:
            # Get recent check results
            recent_checks = self.integrity_checker.get_recent_checks(repository_id, limit=1)
            
            if not recent_checks:
                return None
            
            latest_check = recent_checks[0]
            
            if not latest_check.issues_found:
                return None
            
            # Get remediation guidance
            guidance = self.integrity_checker.get_remediation_guidance(latest_check.issues_found)
            
            return guidance
            
        except Exception as e:
            logger.error(f"Failed to get remediation guidance: {e}")
            raise
    
    def get_repositories_needing_integrity_check(self) -> List[str]:
        """
        Get list of repositories that need integrity checks.
        
        Returns:
            List of repository IDs that need checking
        """
        try:
            return self.integrity_checker.get_repositories_needing_check()
        except Exception as e:
            logger.error(f"Failed to get repositories needing check: {e}")
            return []
    
    def record_backup_performance(
        self,
        operation_id: str,
        repository_id: str,
        start_time: datetime,
        end_time: datetime,
        files_processed: int,
        bytes_processed: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BackupPerformanceMetrics:
        """
        Record performance metrics for a completed backup operation.
        
        Args:
            operation_id: Unique operation identifier
            repository_id: Repository identifier
            start_time: Operation start time
            end_time: Operation end time
            files_processed: Number of files processed
            bytes_processed: Bytes processed
            metadata: Additional metadata
            
        Returns:
            BackupPerformanceMetrics: Recorded metrics
            
        Requirements: 6.1, 6.2
        """
        try:
            return self.performance_tracker.record_backup_performance(
                operation_id=operation_id,
                repository_id=repository_id,
                start_time=start_time,
                end_time=end_time,
                files_processed=files_processed,
                bytes_processed=bytes_processed,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to record backup performance: {e}")
            raise
    
    def get_performance_summary(self, repository_id: str) -> PerformanceSummary:
        """
        Get performance summary for a repository.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            PerformanceSummary: Performance summary
            
        Requirements: 6.1, 6.2, 6.3
        """
        try:
            return self.performance_tracker.get_performance_summary(repository_id)
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            raise
    
    def get_performance_trends(
        self,
        repository_id: str,
        days: int = 30
    ) -> Optional['PerformanceTrend']:
        """
        Analyze performance trends over specified period.
        
        Args:
            repository_id: Repository identifier
            days: Number of days to analyze
            
        Returns:
            PerformanceTrend: Trend analysis or None if insufficient data
            
        Requirements: 6.3
        """
        try:
            return self.performance_tracker.get_performance_trends(repository_id, days)
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            raise
    
    def get_performance_recommendations(
        self,
        repository_id: str
    ) -> List[PerformanceRecommendation]:
        """
        Get performance optimization recommendations for a repository.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            List of performance recommendations
            
        Requirements: 6.4, 6.5
        """
        try:
            return self.performance_optimizer.get_optimization_recommendations(repository_id)
        except Exception as e:
            logger.error(f"Failed to get performance recommendations: {e}")
            raise
    
    def analyze_slow_backup(
        self,
        operation_id: str
    ) -> Optional['PerformanceIssue']:
        """
        Analyze a slow backup operation and provide detailed diagnosis.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            PerformanceIssue with analysis or None if operation not found
            
        Requirements: 6.5
        """
        try:
            return self.performance_optimizer.analyze_slow_backup(operation_id)
        except Exception as e:
            logger.error(f"Failed to analyze slow backup: {e}")
            raise
    
    def compare_backup_performance(
        self,
        operation_id1: str,
        operation_id2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare performance between two backup operations.
        
        Args:
            operation_id1: First operation ID
            operation_id2: Second operation ID
            
        Returns:
            Comparison results with suggestions or None if operations not found
            
        Requirements: 6.4
        """
        try:
            return self.performance_optimizer.compare_and_suggest(operation_id1, operation_id2)
        except Exception as e:
            logger.error(f"Failed to compare backup performance: {e}")
            raise
    
    def get_performance_tracker(self) -> PerformanceTracker:
        """
        Get the performance tracker instance.
        
        Returns:
            PerformanceTracker: Performance tracker instance
        """
        return self.performance_tracker
    
    def analyze_backup_failure(
        self,
        operation_id: str,
        error_message: str,
        repository_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TroubleshootingReport:
        """
        Analyze a backup failure and provide troubleshooting guidance.
        
        Args:
            operation_id: Failed operation identifier
            error_message: Error message from the failure
            repository_id: Repository identifier (optional)
            metadata: Additional failure metadata (optional)
            
        Returns:
            Complete troubleshooting report
            
        Requirements: 9.1, 9.2
        """
        try:
            # Create BackupFailure object
            failure = BackupFailure(
                operation_id=operation_id,
                repository_id=repository_id,
                timestamp=datetime.now(),
                error_message=error_message,
                metadata=metadata or {}
            )
            
            # Get recent events for context
            recent_events = self.status_reporter.get_operation_history(days=7)
            
            # Analyze the failure
            report = self.troubleshooting_service.analyze_backup_failure(failure, recent_events)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to analyze backup failure: {e}")
            raise
    
    def correlate_events(
        self,
        time_window: Optional[timedelta] = None
    ) -> List[EventCorrelation]:
        """
        Correlate recent events to identify patterns.
        
        Args:
            time_window: Time window for correlation (default: 24 hours)
            
        Returns:
            List of event correlations
            
        Requirements: 9.1
        """
        try:
            # Get recent events
            days = (time_window.days if time_window else 1) or 1
            recent_events = self.status_reporter.get_operation_history(days=days)
            
            # Correlate events
            correlations = self.troubleshooting_service.correlate_events(recent_events, time_window)
            
            return correlations
            
        except Exception as e:
            logger.error(f"Failed to correlate events: {e}")
            return []
    
    def detect_proactive_issues(
        self,
        time_window: timedelta = timedelta(days=7)
    ) -> List[ProactiveRecommendation]:
        """
        Detect potential issues before they cause failures.
        
        Args:
            time_window: Time window for analysis (default: 7 days)
            
        Returns:
            List of proactive recommendations
            
        Requirements: 9.2, 9.3
        """
        try:
            # Get recent events
            recent_events = self.status_reporter.get_operation_history(days=time_window.days)
            
            # Detect proactive issues
            recommendations = self.troubleshooting_service.detect_proactive_issues(
                recent_events,
                time_window
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to detect proactive issues: {e}")
            return []
    
    def get_detected_issues(
        self,
        time_window: timedelta = timedelta(days=7)
    ) -> List[DetectedIssue]:
        """
        Get list of detected issues from recent events.
        
        Args:
            time_window: Time window for analysis (default: 7 days)
            
        Returns:
            List of detected issues
            
        Requirements: 9.1, 9.2
        """
        try:
            # Get recent events
            recent_events = self.status_reporter.get_operation_history(days=time_window.days)
            
            # Detect issues
            issues = self.troubleshooting_service.issue_detector.detect_issues(
                recent_events,
                time_window
            )
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to get detected issues: {e}")
            return []
    
    def get_troubleshooting_service(self) -> TroubleshootingService:
        """
        Get the troubleshooting service instance.
        
        Returns:
            TroubleshootingService: Troubleshooting service instance
        """
        return self.troubleshooting_service
    
    def validate_configuration(self) -> List[Any]:
        """
        Validate configuration and identify issues.
        
        Returns:
            List of configuration issues
            
        Requirements: 9.4
        """
        try:
            return self.troubleshooting_service.validate_configuration()
        except Exception as e:
            logger.error(f"Failed to validate configuration: {e}")
            return []
    
    def get_configuration_troubleshooting_guide(
        self,
        issue_type: str
    ) -> Optional['TroubleshootingGuide']:
        """
        Get troubleshooting guide for configuration issues.
        
        Args:
            issue_type: Type of configuration issue
            
        Returns:
            Troubleshooting guide or None if not available
            
        Requirements: 9.4, 9.5
        """
        try:
            return self.troubleshooting_service.get_configuration_troubleshooting_guide(issue_type)
        except Exception as e:
            logger.error(f"Failed to get configuration troubleshooting guide: {e}")
            return None
    
    def get_setup_recommendations(self) -> List[ProactiveRecommendation]:
        """
        Get proactive recommendations for configuration setup.
        
        Returns:
            List of setup recommendations
            
        Requirements: 9.4, 9.5
        """
        try:
            return self.troubleshooting_service.get_setup_recommendations()
        except Exception as e:
            logger.error(f"Failed to get setup recommendations: {e}")
            return []
