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
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .monitoring_service import MonitoringService, HealthStatus
from .backup_history import BackupHistory, BackupStatus, HistoryFilters
from .storage_monitor import StorageMonitor
from .performance_tracker import PerformanceTracker, PerformanceLevel
from .troubleshooting_service import TroubleshootingService, DetectedIssue, IssueSeverity
from .status_reporter import StatusLevel

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    """Types of dashboard widgets"""
    HEALTH_OVERVIEW = "health_overview"
    BACKUP_HISTORY = "backup_history"
    STORAGE_USAGE = "storage_usage"
    PERFORMANCE_TRENDS = "performance_trends"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class HealthOverviewWidget:
    """
    System health overview widget data.
    
    Displays overall system health, repository status, and recent activity.
    Requirements: 7.1, 7.2, 7.3, 7.5
    """
    health_status: HealthStatus
    health_description: str
    repository_count: int
    repositories_healthy: int
    repositories_warning: int
    repositories_error: int
    current_operations: List[Dict[str, Any]]
    recent_activity_summary: str
    last_backup_times: Dict[str, str]
    issues_count: int
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'health_status': self.health_status.value,
            'health_description': self.health_description,
            'repository_count': self.repository_count,
            'repositories_healthy': self.repositories_healthy,
            'repositories_warning': self.repositories_warning,
            'repositories_error': self.repositories_error,
            'current_operations': self.current_operations,
            'recent_activity_summary': self.recent_activity_summary,
            'last_backup_times': self.last_backup_times,
            'issues_count': self.issues_count,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class BackupHistoryWidget:
    """
    Backup history widget data with filtering and search.
    
    Requirements: 7.2, 7.3
    """
    total_backups: int
    successful_backups: int
    failed_backups: int
    success_rate: float
    recent_backups: List[Dict[str, Any]]
    filters_applied: Dict[str, Any]
    total_data_backed_up: str
    average_duration: str
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'total_backups': self.total_backups,
            'successful_backups': self.successful_backups,
            'failed_backups': self.failed_backups,
            'success_rate': self.success_rate,
            'recent_backups': self.recent_backups,
            'filters_applied': self.filters_applied,
            'total_data_backed_up': self.total_data_backed_up,
            'average_duration': self.average_duration,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class StorageUsageWidget:
    """
    Storage usage visualization widget data.
    
    Requirements: 7.1, 7.3
    """
    repositories: List[Dict[str, Any]]
    total_used_bytes: int
    total_used_formatted: str
    total_available_bytes: Optional[int]
    total_available_formatted: Optional[str]
    capacity_warnings: List[Dict[str, Any]]
    storage_trends: List[Dict[str, Any]]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'repositories': self.repositories,
            'total_used_bytes': self.total_used_bytes,
            'total_used_formatted': self.total_used_formatted,
            'total_available_bytes': self.total_available_bytes,
            'total_available_formatted': self.total_available_formatted,
            'capacity_warnings': self.capacity_warnings,
            'storage_trends': self.storage_trends,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class PerformanceTrendsWidget:
    """
    Performance trends visualization widget data.
    
    Requirements: 7.3, 9.1, 9.2
    """
    repositories: List[Dict[str, Any]]
    overall_trend: str
    average_throughput: str
    average_duration: str
    performance_level: str
    anomalies_detected: int
    recommendations: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'repositories': self.repositories,
            'overall_trend': self.overall_trend,
            'average_throughput': self.average_throughput,
            'average_duration': self.average_duration,
            'performance_level': self.performance_level,
            'anomalies_detected': self.anomalies_detected,
            'recommendations': self.recommendations,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class TroubleshootingWidget:
    """
    Troubleshooting guidance panel widget data.
    
    Requirements: 9.1, 9.2
    """
    detected_issues: List[Dict[str, Any]]
    critical_issues_count: int
    high_issues_count: int
    medium_issues_count: int
    recommendations: List[Dict[str, Any]]
    quick_actions: List[str]
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display"""
        return {
            'detected_issues': self.detected_issues,
            'critical_issues_count': self.critical_issues_count,
            'high_issues_count': self.high_issues_count,
            'medium_issues_count': self.medium_issues_count,
            'recommendations': self.recommendations,
            'quick_actions': self.quick_actions,
            'generated_at': self.generated_at.isoformat()
        }


class MonitoringDashboard:
    """
    User interface for monitoring and reporting.
    
    Provides comprehensive monitoring dashboard with multiple widgets for
    system health, backup history, storage usage, performance trends, and
    troubleshooting guidance.
    
    Features:
    - System health overview
    - Recent backup history with filtering
    - Storage usage visualization
    - Performance trends analysis
    - Troubleshooting guidance
    - Easy navigation between views
    
    Requirements: 7.1, 7.2, 7.3, 7.5, 9.1, 9.2
    """
    
    def __init__(self, monitoring_service: MonitoringService):
        """
        Initialize monitoring dashboard.
        
        Args:
            monitoring_service: MonitoringService instance for data access
        """
        self.monitoring_service = monitoring_service
        self.backup_history = monitoring_service.get_backup_history()
        self.storage_monitor = monitoring_service.get_storage_monitor()
        self.performance_tracker = monitoring_service.performance_tracker
        self.troubleshooting_service = monitoring_service.troubleshooting_service
        
        logger.info("MonitoringDashboard initialized")
    
    def render_health_overview(
        self,
        repository_list: Optional[List[Any]] = None
    ) -> HealthOverviewWidget:
        """
        Render system health overview widget.
        
        Args:
            repository_list: Optional list of repository objects for detailed status
            
        Returns:
            HealthOverviewWidget: Health overview data
            
        Requirements: 7.1, 7.2, 7.3, 7.5
        """
        try:
            # Get monitoring summary
            summary = self.monitoring_service.get_monitoring_summary()
            
            # Calculate repository health statistics
            repo_count = len(summary.repository_statuses)
            repos_healthy = 0
            repos_warning = 0
            repos_error = 0
            
            for repo_id, status in summary.repository_statuses.items():
                status_level = status.get('last_status', 'unknown')
                if status_level in ['success', 'info']:
                    repos_healthy += 1
                elif status_level == 'warning':
                    repos_warning += 1
                else:
                    repos_error += 1
            
            # Generate health description
            health_desc = self._generate_health_description(
                summary.health_status,
                repos_healthy,
                repos_warning,
                repos_error
            )
            
            # Format current operations
            current_ops = [
                {
                    'operation_id': op.operation_id,
                    'operation_type': op.operation_type,
                    'status': op.status.value,
                    'message': op.message,
                    'progress': op.progress_percentage,
                    'repository_id': op.repository_id
                }
                for op in summary.current_operations
            ]
            
            # Generate recent activity summary
            activity_summary = self._generate_activity_summary(summary.recent_operations)
            
            # Format last backup times
            last_backup_times = {
                repo_id: backup_time.strftime('%Y-%m-%d %H:%M:%S')
                for repo_id, backup_time in summary.last_backup_dates.items()
            }
            
            return HealthOverviewWidget(
                health_status=summary.health_status,
                health_description=health_desc,
                repository_count=repo_count,
                repositories_healthy=repos_healthy,
                repositories_warning=repos_warning,
                repositories_error=repos_error,
                current_operations=current_ops,
                recent_activity_summary=activity_summary,
                last_backup_times=last_backup_times,
                issues_count=len(summary.issues_requiring_attention),
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to render health overview: {e}")
            # Return minimal widget on error
            return HealthOverviewWidget(
                health_status=HealthStatus.UNKNOWN,
                health_description="Unable to retrieve health status",
                repository_count=0,
                repositories_healthy=0,
                repositories_warning=0,
                repositories_error=0,
                current_operations=[],
                recent_activity_summary="No data available",
                last_backup_times={},
                issues_count=0,
                generated_at=datetime.now()
            )
    
    def render_backup_history(
        self,
        filters: Optional[HistoryFilters] = None,
        limit: int = 20
    ) -> BackupHistoryWidget:
        """
        Render backup history widget with filtering and search.
        
        Args:
            filters: Optional filters to apply
            filters: Filters to apply to history
            limit: Maximum number of records to display
            
        Returns:
            BackupHistoryWidget: Backup history data
            
        Requirements: 7.2, 7.3
        """
        try:
            # Apply default limit if not in filters
            if filters is None:
                filters = HistoryFilters(limit=limit)
            elif filters.limit is None:
                filters.limit = limit
            
            # Get backup history
            records = self.backup_history.get_backup_history(filters)
            
            # Get overall statistics
            stats = self.backup_history.get_statistics(
                repository_id=filters.repository_id if filters else None
            )
            
            # Format recent backups
            recent_backups = [
                {
                    'operation_id': record.operation_id,
                    'repository_id': record.repository_id,
                    'start_time': record.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': record.status.value,
                    'duration': record.duration_formatted,
                    'files_processed': record.files_processed,
                    'bytes_transferred': record.bytes_transferred_formatted,
                    'throughput': f"{record.throughput_mbps:.1f} MB/s",
                    'snapshot_id': record.snapshot_id or 'N/A'
                }
                for record in records
            ]
            
            # Calculate average duration
            if records:
                avg_duration_seconds = sum(r.duration_seconds for r in records) / len(records)
                avg_duration = self._format_duration(avg_duration_seconds)
            else:
                avg_duration = "N/A"
            
            # Format filters applied
            filters_applied = {}
            if filters:
                if filters.start_date:
                    filters_applied['start_date'] = filters.start_date.strftime('%Y-%m-%d')
                if filters.end_date:
                    filters_applied['end_date'] = filters.end_date.strftime('%Y-%m-%d')
                if filters.repository_id:
                    filters_applied['repository_id'] = filters.repository_id
                if filters.status:
                    filters_applied['status'] = filters.status.value
            
            return BackupHistoryWidget(
                total_backups=stats['total_backups'],
                successful_backups=stats['successful_backups'],
                failed_backups=stats['failed_backups'],
                success_rate=stats['success_rate'],
                recent_backups=recent_backups,
                filters_applied=filters_applied,
                total_data_backed_up=self._format_bytes(stats['total_data_backed_up']),
                average_duration=avg_duration,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to render backup history: {e}")
            return BackupHistoryWidget(
                total_backups=0,
                successful_backups=0,
                failed_backups=0,
                success_rate=0.0,
                recent_backups=[],
                filters_applied={},
                total_data_backed_up="0 B",
                average_duration="N/A",
                generated_at=datetime.now()
            )
    
    def render_storage_usage(
        self,
        repository_list: List[Any]
    ) -> StorageUsageWidget:
        """
        Render storage usage visualization across all repositories.
        
        Args:
            repository_list: List of repository objects to analyze
            
        Returns:
            StorageUsageWidget: Storage usage data
            
        Requirements: 7.1, 7.3
        """
        try:
            repositories_data = []
            total_used = 0
            total_available = 0
            has_available_data = False
            
            # Collect storage data for each repository
            for repo in repository_list:
                try:
                    usage = self.storage_monitor.get_repository_usage(repo)
                    
                    repo_data = {
                        'repository_id': usage.repository_id,
                        'used_bytes': usage.used_bytes,
                        'used_formatted': self._format_bytes(usage.used_bytes),
                        'available_bytes': usage.available_bytes,
                        'available_formatted': self._format_bytes(usage.available_bytes) if usage.available_bytes else 'N/A',
                        'usage_percentage': f"{usage.usage_percentage:.1%}" if usage.usage_percentage else 'N/A',
                        'deduplication_ratio': f"{usage.deduplication_ratio:.2f}x" if usage.deduplication_ratio else 'N/A',
                        'compression_ratio': f"{usage.compression_ratio:.2f}x" if usage.compression_ratio else 'N/A',
                        'last_updated': usage.last_updated.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    repositories_data.append(repo_data)
                    total_used += usage.used_bytes
                    
                    if usage.available_bytes:
                        total_available += usage.available_bytes
                        has_available_data = True
                        
                except Exception as e:
                    logger.warning(f"Failed to get storage usage for repository {repo.name}: {e}")
            
            # Check for capacity warnings
            warnings = self.storage_monitor.check_capacity_warnings(repository_list)
            capacity_warnings = [
                {
                    'repository_id': warning.repository_id,
                    'level': warning.level.value,
                    'message': warning.message,
                    'usage_percentage': f"{warning.usage_percentage:.1%}"
                }
                for warning in warnings
            ]
            
            # Get storage trends for repositories
            storage_trends = []
            for repo in repository_list[:5]:  # Limit to first 5 for performance
                try:
                    trends = self.storage_monitor.get_storage_trends(repo, days=30)
                    
                    trend_data = {
                        'repository_id': trends.repository_id,
                        'average_daily_growth': self._format_bytes(int(trends.average_daily_growth_bytes)),
                        'projected_full_date': trends.projected_full_date.strftime('%Y-%m-%d') if trends.projected_full_date else 'N/A',
                        'data_points_count': len(trends.data_points)
                    }
                    
                    storage_trends.append(trend_data)
                    
                except Exception as e:
                    logger.debug(f"Failed to get storage trends for {repo.name}: {e}")
            
            return StorageUsageWidget(
                repositories=repositories_data,
                total_used_bytes=total_used,
                total_used_formatted=self._format_bytes(total_used),
                total_available_bytes=total_available if has_available_data else None,
                total_available_formatted=self._format_bytes(total_available) if has_available_data else None,
                capacity_warnings=capacity_warnings,
                storage_trends=storage_trends,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to render storage usage: {e}")
            return StorageUsageWidget(
                repositories=[],
                total_used_bytes=0,
                total_used_formatted="0 B",
                total_available_bytes=None,
                total_available_formatted=None,
                capacity_warnings=[],
                storage_trends=[],
                generated_at=datetime.now()
            )
    
    def render_performance_trends(
        self,
        repository_list: List[Any],
        days: int = 30
    ) -> PerformanceTrendsWidget:
        """
        Render performance trends visualization for backup operations.
        
        Args:
            repository_list: List of repository objects to analyze
            days: Number of days to analyze
            
        Returns:
            PerformanceTrendsWidget: Performance trends data
            
        Requirements: 7.3, 9.1, 9.2
        """
        try:
            repositories_data = []
            all_throughputs = []
            all_durations = []
            total_anomalies = 0
            
            # Collect performance data for each repository
            for repo in repository_list:
                try:
                    summary = self.performance_tracker.get_performance_summary(repo.name)
                    trends = self.performance_tracker.get_performance_trends(repo.name, days)
                    
                    repo_data = {
                        'repository_id': repo.name,
                        'last_backup_duration': summary.last_backup_duration or 'N/A',
                        'last_backup_throughput': summary.last_backup_throughput or 'N/A',
                        'average_duration': summary.average_duration or 'N/A',
                        'average_throughput': summary.average_throughput or 'N/A',
                        'performance_level': summary.performance_level.value if summary.performance_level else 'unknown',
                        'trend_direction': trends.trend_direction if trends else 'unknown',
                        'trend_description': trends.get_trend_description() if trends else 'Insufficient data',
                        'total_operations': summary.total_operations
                    }
                    
                    repositories_data.append(repo_data)
                    
                    # Collect for overall statistics
                    if trends:
                        all_throughputs.append(trends.average_throughput_mbps)
                        all_durations.append(trends.average_duration_seconds)
                    
                    # Check for anomalies
                    anomalies = self.performance_tracker.detect_performance_anomalies(repo.name)
                    total_anomalies += len(anomalies)
                    
                except Exception as e:
                    logger.warning(f"Failed to get performance data for repository {repo.name}: {e}")
            
            # Calculate overall statistics
            if all_throughputs:
                avg_throughput = sum(all_throughputs) / len(all_throughputs)
                avg_throughput_str = f"{avg_throughput:.1f} MB/s"
            else:
                avg_throughput_str = "N/A"
            
            if all_durations:
                avg_duration = sum(all_durations) / len(all_durations)
                avg_duration_str = self._format_duration(avg_duration)
            else:
                avg_duration_str = "N/A"
            
            # Determine overall trend
            improving_count = sum(1 for r in repositories_data if r.get('trend_direction') == 'improving')
            degrading_count = sum(1 for r in repositories_data if r.get('trend_direction') == 'degrading')
            
            if improving_count > degrading_count:
                overall_trend = "improving"
            elif degrading_count > improving_count:
                overall_trend = "degrading"
            else:
                overall_trend = "stable"
            
            # Determine overall performance level
            performance_levels = [r.get('performance_level', 'unknown') for r in repositories_data]
            if 'excellent' in performance_levels or 'good' in performance_levels:
                overall_performance = "good"
            elif 'slow' in performance_levels or 'very_slow' in performance_levels:
                overall_performance = "needs_attention"
            else:
                overall_performance = "normal"
            
            # Generate recommendations
            recommendations = []
            if total_anomalies > 0:
                recommendations.append(f"Review {total_anomalies} performance anomalies detected")
            if degrading_count > 0:
                recommendations.append(f"{degrading_count} repositories showing performance degradation")
            if overall_performance == "needs_attention":
                recommendations.append("Some repositories have slow performance - review system resources")
            
            return PerformanceTrendsWidget(
                repositories=repositories_data,
                overall_trend=overall_trend,
                average_throughput=avg_throughput_str,
                average_duration=avg_duration_str,
                performance_level=overall_performance,
                anomalies_detected=total_anomalies,
                recommendations=recommendations,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to render performance trends: {e}")
            return PerformanceTrendsWidget(
                repositories=[],
                overall_trend="unknown",
                average_throughput="N/A",
                average_duration="N/A",
                performance_level="unknown",
                anomalies_detected=0,
                recommendations=[],
                generated_at=datetime.now()
            )
    
    def render_troubleshooting_panel(
        self,
        recent_events: Optional[List[Any]] = None,
        time_window_days: int = 7
    ) -> TroubleshootingWidget:
        """
        Render troubleshooting guidance panel with detected issues and recommendations.
        
        Args:
            recent_events: Optional list of recent operation events
            time_window_days: Number of days to analyze for issues
            
        Returns:
            TroubleshootingWidget: Troubleshooting data
            
        Requirements: 9.1, 9.2
        """
        try:
            # Get recent events if not provided
            if recent_events is None:
                recent_events = self.monitoring_service.status_reporter.get_operation_history(
                    days=time_window_days
                )
            
            # Detect issues
            detected_issues = self.troubleshooting_service.issue_detector.detect_issues(
                recent_events,
                timedelta(days=time_window_days)
            )
            
            # Count issues by severity
            critical_count = sum(1 for issue in detected_issues if issue.severity == IssueSeverity.CRITICAL)
            high_count = sum(1 for issue in detected_issues if issue.severity == IssueSeverity.HIGH)
            medium_count = sum(1 for issue in detected_issues if issue.severity == IssueSeverity.MEDIUM)
            
            # Format detected issues
            issues_data = [
                {
                    'issue_id': issue.issue_id,
                    'issue_type': issue.issue_type.value,
                    'severity': issue.severity.value,
                    'title': issue.title,
                    'description': issue.description[:200] + '...' if len(issue.description) > 200 else issue.description,
                    'occurrence_count': issue.occurrence_count,
                    'first_occurrence': issue.first_occurrence.strftime('%Y-%m-%d %H:%M:%S'),
                    'last_occurrence': issue.last_occurrence.strftime('%Y-%m-%d %H:%M:%S'),
                    'repository_id': issue.repository_id or 'All'
                }
                for issue in sorted(detected_issues, key=lambda x: (x.severity.value, -x.occurrence_count))[:10]
            ]
            
            # Get proactive recommendations
            proactive_recs = self.troubleshooting_service.detect_proactive_issues(
                recent_events,
                timedelta(days=time_window_days)
            )
            
            recommendations_data = [
                {
                    'recommendation_id': rec.recommendation_id,
                    'title': rec.title,
                    'description': rec.description[:200] + '...' if len(rec.description) > 200 else rec.description,
                    'priority': rec.priority.value,
                    'action_items': rec.action_items[:3],  # First 3 actions
                    'estimated_impact': rec.estimated_impact
                }
                for rec in proactive_recs[:5]  # Top 5 recommendations
            ]
            
            # Generate quick actions
            quick_actions = []
            if critical_count > 0:
                quick_actions.append("Review critical issues immediately")
            if high_count > 0:
                quick_actions.append("Address high-priority issues")
            if len(detected_issues) > 5:
                quick_actions.append("Review all detected issues for patterns")
            if not detected_issues:
                quick_actions.append("No issues detected - system is healthy")
            
            return TroubleshootingWidget(
                detected_issues=issues_data,
                critical_issues_count=critical_count,
                high_issues_count=high_count,
                medium_issues_count=medium_count,
                recommendations=recommendations_data,
                quick_actions=quick_actions,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to render troubleshooting panel: {e}")
            return TroubleshootingWidget(
                detected_issues=[],
                critical_issues_count=0,
                high_issues_count=0,
                medium_issues_count=0,
                recommendations=[],
                quick_actions=["Unable to analyze issues - check logs"],
                generated_at=datetime.now()
            )
    
    def get_navigation_links(self) -> Dict[str, str]:
        """
        Get navigation links for easy movement between dashboard views.
        
        Returns:
            Dictionary of view names to descriptions
            
        Requirements: 7.3
        """
        return {
            'health': 'System health overview and current operations',
            'history': 'Backup history with filtering and search',
            'storage': 'Storage usage across all repositories',
            'performance': 'Performance trends and optimization',
            'troubleshooting': 'Issues and troubleshooting guidance',
            'logs': 'Detailed activity logs'
        }
    
    def _generate_health_description(
        self,
        health_status: HealthStatus,
        healthy: int,
        warning: int,
        error: int
    ) -> str:
        """Generate user-friendly health description"""
        if health_status == HealthStatus.HEALTHY:
            return f"System is healthy. {healthy} repositories operating normally."
        elif health_status == HealthStatus.WARNING:
            return f"System has warnings. {warning} repositories need attention."
        elif health_status == HealthStatus.ERROR:
            return f"System has errors. {error} repositories have critical issues."
        else:
            return "System health status unknown. Check configuration."
    
    def _generate_activity_summary(self, recent_operations: List[Any]) -> str:
        """Generate recent activity summary"""
        if not recent_operations:
            return "No recent activity"
        
        success_count = sum(1 for op in recent_operations if op.status == StatusLevel.SUCCESS)
        error_count = sum(1 for op in recent_operations if op.status in [StatusLevel.ERROR, StatusLevel.CRITICAL])
        
        return f"{len(recent_operations)} operations in last 7 days: {success_count} successful, {error_count} failed"
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in user-friendly format"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format bytes in user-friendly format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
