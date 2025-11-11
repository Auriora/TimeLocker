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

"""
CLI Monitoring Integration

This module provides monitoring data access and display capabilities for CLI operations.
It integrates with the monitoring service to provide status feedback, log filtering,
and monitoring information display through the CLI.

Requirements addressed:
- 8.1: CLI-based monitoring data access and display
- 8.2: CLI-based log filtering and searching capabilities
- 8.3: CLI status feedback and monitoring information display
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..monitoring.monitoring_service import MonitoringService, HealthStatus, MonitoringSummary
from ..monitoring.activity_logger import ActivityLogger, LogLevel, LogEntry
from ..monitoring.backup_history import BackupHistory, BackupRecord, HistoryFilters, BackupStatus
from ..monitoring.status_reporter import StatusReporter, OperationStatus, StatusLevel
from ..monitoring.storage_monitor import StorageMonitor
from ..monitoring.performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


@dataclass
class CLIMonitoringFilters:
    """Filters for CLI monitoring queries"""
    hours: Optional[int] = None
    days: Optional[int] = None
    repository_id: Optional[str] = None
    operation_type: Optional[str] = None
    status: Optional[str] = None
    log_level: Optional[str] = None
    limit: Optional[int] = None


class CLIMonitoringIntegration:
    """
    CLI integration for monitoring operations.
    
    This class provides a bridge between the CLI and the monitoring service,
    offering methods for accessing monitoring data, filtering logs, and
    displaying monitoring information in a CLI-friendly format.
    
    Responsibilities:
    - Monitoring data access for CLI commands
    - Log filtering and searching
    - Status feedback formatting
    - Monitoring information display
    - Integration with monitoring service
    """

    def __init__(self, monitoring_service: Optional[MonitoringService] = None, config_dir: Optional[Path] = None):
        """
        Initialize CLI monitoring integration.
        
        Args:
            monitoring_service: Optional monitoring service instance (will create if not provided)
            config_dir: Optional configuration directory
        """
        if monitoring_service is None:
            if config_dir is None:
                from ..config.configuration_path_resolver import ConfigurationPathResolver
                config_dir = ConfigurationPathResolver.get_config_directory()
            
            self.monitoring_service = MonitoringService(config_dir / "monitoring")
        else:
            self.monitoring_service = monitoring_service
        
        # Direct access to monitoring components for CLI operations
        self.activity_logger = self.monitoring_service.activity_logger
        self.backup_history = self.monitoring_service.backup_history
        self.status_reporter = self.monitoring_service.status_reporter
        self.storage_monitor = self.monitoring_service.storage_monitor
        self.performance_tracker = self.monitoring_service.performance_tracker
        
        logger.debug("CLI monitoring integration initialized")

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status for CLI display.
        
        Returns:
            Dict containing system status information
            
        Requirements: 8.1, 8.3
        """
        try:
            health_status = self.monitoring_service.get_system_health()
            current_operations = self.status_reporter.get_current_operations()
            
            # Get recent operation summary
            recent_ops = self.status_reporter.get_operation_history(days=1)
            
            # Count operations by status
            status_counts = {
                'success': sum(1 for op in recent_ops if op.status == StatusLevel.SUCCESS),
                'warning': sum(1 for op in recent_ops if op.status == StatusLevel.WARNING),
                'error': sum(1 for op in recent_ops if op.status == StatusLevel.ERROR),
                'critical': sum(1 for op in recent_ops if op.status == StatusLevel.CRITICAL)
            }
            
            return {
                'health_status': health_status.value,
                'current_operations': len(current_operations),
                'recent_operations_24h': len(recent_ops),
                'status_counts': status_counts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'health_status': 'unknown',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_current_operations(self) -> List[Dict[str, Any]]:
        """
        Get currently running operations for CLI display.
        
        Returns:
            List of current operation dictionaries
            
        Requirements: 8.1, 8.3
        """
        try:
            operations = self.status_reporter.get_current_operations()
            
            return [
                {
                    'operation_id': op.operation_id,
                    'operation_type': op.operation_type,
                    'status': op.status.value,
                    'message': op.message,
                    'repository_id': op.repository_id,
                    'progress': op.progress_percentage,
                    'files_processed': op.files_processed,
                    'total_files': op.total_files,
                    'timestamp': op.timestamp.isoformat()
                }
                for op in operations
            ]
            
        except Exception as e:
            logger.error(f"Failed to get current operations: {e}")
            return []

    def get_recent_logs(self, filters: Optional[CLIMonitoringFilters] = None) -> List[Dict[str, Any]]:
        """
        Get recent log entries with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of log entry dictionaries
            
        Requirements: 8.1, 8.2
        """
        if filters is None:
            filters = CLIMonitoringFilters()
        
        try:
            # Determine time range
            hours = filters.hours or (filters.days * 24 if filters.days else 24)
            
            # Get logs from activity logger
            log_level = LogLevel(filters.log_level) if filters.log_level else None
            logs = self.activity_logger.get_recent_logs(hours=hours, level=log_level)
            
            # Apply additional filters
            if filters.repository_id:
                logs = [log for log in logs if log.repository_id == filters.repository_id]
            
            if filters.operation_type:
                logs = [log for log in logs if log.operation_type == filters.operation_type]
            
            # Apply limit
            if filters.limit:
                logs = logs[:filters.limit]
            
            # Convert to dictionaries
            return [log.to_dict() for log in logs]
            
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return []

    def search_logs(self, query: str, filters: Optional[CLIMonitoringFilters] = None) -> List[Dict[str, Any]]:
        """
        Search logs for specific text.
        
        Args:
            query: Search query string
            filters: Optional filters to apply
            
        Returns:
            List of matching log entry dictionaries
            
        Requirements: 8.2
        """
        if filters is None:
            filters = CLIMonitoringFilters()
        
        try:
            # Get logs with filters
            logs = self.get_recent_logs(filters)
            
            # Search in message and details
            query_lower = query.lower()
            matching_logs = []
            
            for log in logs:
                # Search in message
                if query_lower in log.get('message', '').lower():
                    matching_logs.append(log)
                    continue
                
                # Search in details
                details = log.get('details', {})
                if any(query_lower in str(v).lower() for v in details.values()):
                    matching_logs.append(log)
                    continue
            
            return matching_logs
            
        except Exception as e:
            logger.error(f"Failed to search logs: {e}")
            return []

    def get_backup_history(self, filters: Optional[CLIMonitoringFilters] = None) -> List[Dict[str, Any]]:
        """
        Get backup history with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of backup record dictionaries
            
        Requirements: 8.1
        """
        if filters is None:
            filters = CLIMonitoringFilters()
        
        try:
            # Convert CLI filters to history filters
            history_filters = HistoryFilters()
            
            if filters.days:
                history_filters.start_date = datetime.now() - timedelta(days=filters.days)
            
            if filters.repository_id:
                history_filters.repository_id = filters.repository_id
            
            if filters.status:
                try:
                    history_filters.status = BackupStatus(filters.status)
                except ValueError:
                    logger.warning(f"Invalid status filter: {filters.status}")
            
            if filters.limit:
                history_filters.limit = filters.limit
            
            # Get backup history
            records = self.backup_history.get_backup_history(history_filters)
            
            # Convert to dictionaries
            return [
                {
                    'operation_id': record.operation_id,
                    'repository_id': record.repository_id,
                    'start_time': record.start_time.isoformat(),
                    'end_time': record.end_time.isoformat(),
                    'status': record.status.value,
                    'files_processed': record.files_processed,
                    'bytes_transferred': record.bytes_transferred,
                    'bytes_transferred_formatted': record.bytes_transferred_formatted,
                    'duration': record.duration_formatted,
                    'throughput_mbps': f"{record.throughput_mbps:.2f}",
                    'snapshot_id': record.snapshot_id,
                    'error_message': record.error_message
                }
                for record in records
            ]
            
        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []

    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific operation.
        
        Args:
            operation_id: Operation ID to query
            
        Returns:
            Operation status dictionary or None if not found
            
        Requirements: 8.1, 8.3
        """
        try:
            status = self.status_reporter.get_operation_status(operation_id)
            
            if status is None:
                return None
            
            return {
                'operation_id': status.operation_id,
                'operation_type': status.operation_type,
                'status': status.status.value,
                'message': status.message,
                'repository_id': status.repository_id,
                'progress': status.progress_percentage,
                'files_processed': status.files_processed,
                'total_files': status.total_files,
                'bytes_processed': status.bytes_processed,
                'total_bytes': status.total_bytes,
                'estimated_completion': status.estimated_completion.isoformat() if status.estimated_completion else None,
                'timestamp': status.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get operation status: {e}")
            return None

    def get_storage_status(self, repository_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get storage status for repositories.
        
        Args:
            repository_id: Optional specific repository to query
            
        Returns:
            List of storage status dictionaries
            
        Requirements: 8.1
        """
        try:
            if repository_id:
                # Get specific repository storage
                usage = self.storage_monitor.get_repository_usage(repository_id)
                if usage:
                    return [self._format_storage_usage(usage)]
                return []
            else:
                # Get all repository storage
                all_usage = self.storage_monitor.get_all_repository_usage()
                return [self._format_storage_usage(usage) for usage in all_usage]
            
        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return []

    def get_performance_summary(self, repository_id: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """
        Get performance summary for backups.
        
        Args:
            repository_id: Optional specific repository to query
            days: Number of days to analyze
            
        Returns:
            Performance summary dictionary
            
        Requirements: 8.1
        """
        try:
            if repository_id:
                summary = self.performance_tracker.get_performance_summary(repository_id, days)
            else:
                # Get overall performance summary
                summary = self.performance_tracker.get_overall_performance_summary(days)
            
            return {
                'period_days': days,
                'total_backups': summary.total_backups,
                'average_duration_seconds': summary.average_duration_seconds,
                'average_throughput_mbps': summary.average_throughput_mbps,
                'total_bytes_transferred': summary.total_bytes_transferred,
                'fastest_backup_duration': summary.fastest_backup_duration,
                'slowest_backup_duration': summary.slowest_backup_duration
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {
                'period_days': days,
                'error': str(e)
            }

    def format_log_entry_cli(self, log_entry: Dict[str, Any], verbose: bool = False) -> str:
        """
        Format a log entry for CLI display.
        
        Args:
            log_entry: Log entry dictionary
            verbose: Whether to include verbose details
            
        Returns:
            Formatted string for CLI display
            
        Requirements: 8.3
        """
        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(log_entry['timestamp'])
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format level with color indicators
            level = log_entry['level'].upper()
            level_indicators = {
                'DEBUG': '[D]',
                'INFO': '[I]',
                'WARNING': '[W]',
                'ERROR': '[E]',
                'CRITICAL': '[C]'
            }
            level_indicator = level_indicators.get(level, '[?]')
            
            # Build basic line
            lines = [f"{level_indicator} {timestamp_str} - {log_entry['message']}"]
            
            if verbose:
                # Add repository and operation info
                if log_entry.get('repository_id'):
                    lines.append(f"    Repository: {log_entry['repository_id']}")
                if log_entry.get('operation_id'):
                    lines.append(f"    Operation: {log_entry['operation_id']}")
                
                # Add details
                if log_entry.get('details'):
                    lines.append("    Details:")
                    for key, value in log_entry['details'].items():
                        lines.append(f"      {key}: {value}")
                
                # Add troubleshooting suggestions
                if log_entry.get('troubleshooting_suggestions'):
                    lines.append("    Suggestions:")
                    for i, suggestion in enumerate(log_entry['troubleshooting_suggestions'], 1):
                        lines.append(f"      {i}. {suggestion}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to format log entry: {e}")
            return f"[Error formatting log entry: {e}]"

    def format_operation_status_cli(self, status: Dict[str, Any]) -> str:
        """
        Format operation status for CLI display.
        
        Args:
            status: Operation status dictionary
            
        Returns:
            Formatted string for CLI display
            
        Requirements: 8.3
        """
        try:
            lines = [
                f"Operation: {status['operation_id']}",
                f"Type: {status['operation_type']}",
                f"Status: {status['status']}",
                f"Message: {status['message']}"
            ]
            
            if status.get('repository_id'):
                lines.append(f"Repository: {status['repository_id']}")
            
            if status.get('progress') is not None:
                lines.append(f"Progress: {status['progress']}%")
            
            if status.get('files_processed') and status.get('total_files'):
                lines.append(f"Files: {status['files_processed']}/{status['total_files']}")
            
            if status.get('estimated_completion'):
                completion = datetime.fromisoformat(status['estimated_completion'])
                lines.append(f"Estimated Completion: {completion.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to format operation status: {e}")
            return f"[Error formatting operation status: {e}]"

    def _format_storage_usage(self, usage) -> Dict[str, Any]:
        """
        Format storage usage for CLI display.
        
        Args:
            usage: StorageUsage object
            
        Returns:
            Formatted storage usage dictionary
        """
        return {
            'repository_id': usage.repository_id,
            'used_bytes': usage.used_bytes,
            'available_bytes': usage.available_bytes,
            'total_bytes': usage.total_bytes,
            'usage_percentage': f"{usage.usage_percentage:.1f}%",
            'deduplication_ratio': f"{usage.deduplication_ratio:.2f}" if usage.deduplication_ratio else None,
            'compression_ratio': f"{usage.compression_ratio:.2f}" if usage.compression_ratio else None,
            'last_updated': usage.last_updated.isoformat()
        }

    def get_monitoring_service(self) -> MonitoringService:
        """
        Get the underlying monitoring service instance.
        
        Returns:
            MonitoringService instance
        """
        return self.monitoring_service
