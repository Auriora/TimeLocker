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

from .status_reporter import StatusReporter, OperationStatus, StatusLevel
from .notification_service import (
    NotificationService, 
    NotificationError, 
    NotificationType,
    NotificationEventType,
    NotificationPreferences,
    NotificationConfig
)
from .system_tray_integration import (
    SystemTrayIntegration,
    SystemTrayError,
    TrayStatus,
    TrayStatusInfo
)
from .progress_monitor import (
    ProgressMonitor,
    ProgressData,
    ProgressReport,
    ProgressState,
    PerformanceMetrics
)
from .recovery_progress_notifier import RecoveryProgressNotifier
from .monitoring_service import (
    MonitoringService,
    HealthStatus,
    BackupEvent,
    RecoveryEvent,
    MonitoringSummary,
    MonitoringPreferences
)
from .activity_logger import ActivityLogger, LogLevel, LogEntry
from .backup_history import (
    BackupHistory,
    BackupRecord,
    BackupStatus,
    HistoryFilters,
    PerformanceTrends
)
from .storage_monitor import (
    StorageMonitor,
    StorageUsage,
    CapacityWarning,
    StorageTrends,
    OptimizationRecommendation,
    WarningLevel
)
from .integrity_checker import (
    IntegrityChecker,
    IntegrityLevel,
    IntegrityStatus,
    IntegrityCheckResult,
    IntegrityIssue,
    RemediationGuide,
    CheckInterval
)
from .performance_tracker import (
    PerformanceTracker,
    BackupPerformanceMetrics,
    PerformanceTrend,
    PerformanceSummary,
    PerformanceLevel
)
from .performance_optimizer import (
    PerformanceOptimizer,
    PerformanceRecommendation,
    PerformanceIssue,
    RecommendationType,
    RecommendationPriority
)
from .troubleshooting_service import (
    TroubleshootingService,
    IssueType,
    IssueSeverity,
    DetectedIssue,
    TroubleshootingStep,
    TroubleshootingGuide,
    EventCorrelation,
    ProactiveRecommendation,
    BackupFailure,
    TroubleshootingReport,
    EventCorrelator,
    IssueDetector
)
from .configuration_troubleshooter import (
    ConfigurationTroubleshooter,
    ConfigurationIssue
)
from .monitoring_dashboard import (
    MonitoringDashboard,
    WidgetType,
    HealthOverviewWidget,
    BackupHistoryWidget,
    StorageUsageWidget,
    PerformanceTrendsWidget,
    TroubleshootingWidget
)
from .webhook_handler import (
    WebhookHandler,
    WebhookConfig,
    WebhookResult,
    WebhookError,
    PayloadFormat,
    RetryHandler
)
from .health_check_integration import (
    HealthCheckIntegration,
    HealthCheckConfig,
    HealthCheckServiceConfig,
    HealthCheckServiceType,
    HealthStatus as HealthCheckHealthStatus,
    PingResult,
    HealthCheckError
)

__all__ = [
        'StatusReporter', 'OperationStatus', 'StatusLevel',
        'NotificationService', 'NotificationError', 'NotificationType', 
        'NotificationEventType', 'NotificationPreferences', 'NotificationConfig',
        'SystemTrayIntegration', 'SystemTrayError', 'TrayStatus', 'TrayStatusInfo',
        'ProgressMonitor', 'ProgressData', 'ProgressReport', 'ProgressState', 'PerformanceMetrics',
        'RecoveryProgressNotifier',
        'MonitoringService', 'HealthStatus', 'BackupEvent', 'RecoveryEvent', 
        'MonitoringSummary', 'MonitoringPreferences',
        'ActivityLogger', 'LogLevel', 'LogEntry',
        'BackupHistory', 'BackupRecord', 'BackupStatus', 'HistoryFilters', 'PerformanceTrends',
        'StorageMonitor', 'StorageUsage', 'CapacityWarning', 'StorageTrends', 
        'OptimizationRecommendation', 'WarningLevel',
        'IntegrityChecker', 'IntegrityLevel', 'IntegrityStatus', 'IntegrityCheckResult',
        'IntegrityIssue', 'RemediationGuide', 'CheckInterval',
        'PerformanceTracker', 'BackupPerformanceMetrics', 'PerformanceTrend', 
        'PerformanceSummary', 'PerformanceLevel',
        'PerformanceOptimizer', 'PerformanceRecommendation', 'PerformanceIssue',
        'RecommendationType', 'RecommendationPriority',
        'TroubleshootingService', 'IssueType', 'IssueSeverity', 'DetectedIssue',
        'TroubleshootingStep', 'TroubleshootingGuide', 'EventCorrelation',
        'ProactiveRecommendation', 'BackupFailure', 'TroubleshootingReport',
        'EventCorrelator', 'IssueDetector',
        'ConfigurationTroubleshooter', 'ConfigurationIssue',
        'MonitoringDashboard', 'WidgetType', 'HealthOverviewWidget',
        'BackupHistoryWidget', 'StorageUsageWidget', 'PerformanceTrendsWidget',
        'TroubleshootingWidget',
        'WebhookHandler', 'WebhookConfig', 'WebhookResult', 'WebhookError',
        'PayloadFormat', 'RetryHandler',
        'HealthCheckIntegration', 'HealthCheckConfig', 'HealthCheckServiceConfig',
        'HealthCheckServiceType', 'HealthCheckHealthStatus', 'PingResult', 'HealthCheckError'
]
