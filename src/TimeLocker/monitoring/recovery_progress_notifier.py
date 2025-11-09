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
Recovery Progress Notifier for TimeLocker Recovery Operations

This module provides progress notification and reporting capabilities specifically
for recovery operations, integrating with the existing notification service.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

from .notification_service import NotificationService, NotificationType
from .status_reporter import StatusReporter, OperationStatus, StatusLevel
from .progress_monitor import ProgressMonitor, ProgressReport, ProgressState

logger = logging.getLogger(__name__)


class RecoveryProgressNotifier:
    """
    Provides progress notification and reporting integration for recovery operations.
    
    This class integrates with the existing notification service to send progress
    updates, milestone notifications, and error reports for recovery operations.
    It supports detailed progress logging and configurable notification preferences.
    """
    
    # Milestone percentages for progress notifications
    DEFAULT_MILESTONES = [25, 50, 75, 100]
    
    def __init__(
        self,
        notification_service: Optional[NotificationService] = None,
        status_reporter: Optional[StatusReporter] = None,
        progress_monitor: Optional[ProgressMonitor] = None
    ):
        """
        Initialize the RecoveryProgressNotifier.
        
        Args:
            notification_service: Optional NotificationService instance
            status_reporter: Optional StatusReporter instance
            progress_monitor: Optional ProgressMonitor instance
        """
        self.notification_service = notification_service or NotificationService()
        self.status_reporter = status_reporter or StatusReporter()
        self.progress_monitor = progress_monitor or ProgressMonitor(self.status_reporter)
        
        # Track milestone notifications sent per operation
        self._milestone_tracker: Dict[str, Set[int]] = {}
        
        # Track last notification time per operation to avoid spam
        self._last_notification_time: Dict[str, datetime] = {}
        
        # Minimum time between notifications (seconds)
        self._min_notification_interval = 30
        
        logger.info("RecoveryProgressNotifier initialized")
    
    def notify_recovery_started(
        self,
        operation_id: str,
        snapshot_id: str,
        target_path: str,
        recovery_type: str
    ) -> None:
        """
        Send notification when recovery operation starts.
        
        Args:
            operation_id: ID of the recovery operation
            snapshot_id: ID of the snapshot being restored
            target_path: Destination path for restored files
            recovery_type: Type of recovery (full or selective)
        """
        try:
            # Create operation status
            status = OperationStatus(
                operation_id=operation_id,
                operation_type="recovery",
                status=StatusLevel.INFO,
                message=f"Started {recovery_type} recovery from snapshot {snapshot_id}",
                timestamp=datetime.now(),
                repository_id=snapshot_id,
                metadata={
                    'recovery_type': recovery_type,
                    'target_path': target_path,
                    'snapshot_id': snapshot_id
                }
            )
            
            # Send notification
            self.notification_service.send_notification(status)
            
            # Initialize milestone tracker
            self._milestone_tracker[operation_id] = set()
            self._last_notification_time[operation_id] = datetime.now()
            
            logger.info(f"Sent recovery started notification for operation {operation_id}")
            
        except Exception as e:
            logger.error(f"Failed to send recovery started notification: {e}")
    
    def notify_recovery_progress(
        self,
        operation_id: str,
        progress_report: ProgressReport,
        force: bool = False
    ) -> None:
        """
        Send progress notification for recovery operation.
        
        This method sends notifications at milestone percentages and respects
        minimum notification intervals to avoid spam.
        
        Args:
            operation_id: ID of the recovery operation
            progress_report: Current progress report
            force: Force notification regardless of interval
        """
        try:
            # Check if enough time has passed since last notification
            if not force and operation_id in self._last_notification_time:
                time_since_last = (datetime.now() - self._last_notification_time[operation_id]).total_seconds()
                if time_since_last < self._min_notification_interval:
                    return
            
            # Calculate progress percentage
            progress_pct = progress_report.progress_data.progress_percentage
            
            if progress_pct is None:
                return
            
            # Check if this is a milestone
            milestone_reached = self._check_milestone(operation_id, progress_pct)
            
            if not milestone_reached and not force:
                return
            
            # Create operation status
            status = OperationStatus(
                operation_id=operation_id,
                operation_type="recovery",
                status=StatusLevel.INFO,
                message=f"Recovery progress: {progress_pct:.1f}% complete",
                timestamp=datetime.now(),
                progress_percentage=int(progress_pct),
                files_processed=progress_report.progress_data.files_processed,
                total_files=progress_report.progress_data.total_files,
                bytes_processed=progress_report.progress_data.bytes_processed,
                total_bytes=progress_report.progress_data.total_bytes,
                estimated_completion=progress_report.estimated_completion,
                metadata={
                    'current_file': progress_report.progress_data.current_file,
                    'transfer_rate_mbps': progress_report.progress_data.transfer_rate / (1024 * 1024)
                }
            )
            
            # Send notification
            self.notification_service.send_notification(status)
            
            # Update last notification time
            self._last_notification_time[operation_id] = datetime.now()
            
            logger.info(
                f"Sent recovery progress notification for operation {operation_id}: "
                f"{progress_pct:.1f}%"
            )
            
        except Exception as e:
            logger.error(f"Failed to send recovery progress notification: {e}")
    
    def notify_recovery_completed(
        self,
        operation_id: str,
        snapshot_id: str,
        files_restored: int,
        bytes_restored: int,
        duration_seconds: float,
        validation_passed: bool = True
    ) -> None:
        """
        Send notification when recovery operation completes successfully.
        
        Args:
            operation_id: ID of the recovery operation
            snapshot_id: ID of the snapshot that was restored
            files_restored: Number of files restored
            bytes_restored: Number of bytes restored
            duration_seconds: Duration of the operation in seconds
            validation_passed: Whether post-recovery validation passed
        """
        try:
            # Create operation status
            status = OperationStatus(
                operation_id=operation_id,
                operation_type="recovery",
                status=StatusLevel.SUCCESS if validation_passed else StatusLevel.WARNING,
                message=f"Recovery completed: {files_restored} files restored ({bytes_restored / (1024**3):.2f} GB)",
                timestamp=datetime.now(),
                repository_id=snapshot_id,
                progress_percentage=100,
                files_processed=files_restored,
                total_files=files_restored,
                bytes_processed=bytes_restored,
                total_bytes=bytes_restored,
                metadata={
                    'duration_seconds': duration_seconds,
                    'validation_passed': validation_passed,
                    'snapshot_id': snapshot_id
                }
            )
            
            # Send notification
            self.notification_service.send_notification(status)
            
            # Clean up tracking data
            self._milestone_tracker.pop(operation_id, None)
            self._last_notification_time.pop(operation_id, None)
            
            logger.info(f"Sent recovery completed notification for operation {operation_id}")
            
        except Exception as e:
            logger.error(f"Failed to send recovery completed notification: {e}")
    
    def notify_recovery_error(
        self,
        operation_id: str,
        error_message: str,
        error_type: str,
        failed_files: Optional[List[str]] = None,
        is_recoverable: bool = False
    ) -> None:
        """
        Send notification when recovery operation encounters an error.
        
        Args:
            operation_id: ID of the recovery operation
            error_message: Human-readable error message
            error_type: Type of error
            failed_files: Optional list of files that failed
            is_recoverable: Whether the error is recoverable
        """
        try:
            # Determine severity based on recoverability
            status_level = StatusLevel.WARNING if is_recoverable else StatusLevel.ERROR
            
            # Create operation status
            status = OperationStatus(
                operation_id=operation_id,
                operation_type="recovery",
                status=status_level,
                message=f"Recovery error: {error_message}",
                timestamp=datetime.now(),
                metadata={
                    'error_type': error_type,
                    'failed_files_count': len(failed_files) if failed_files else 0,
                    'is_recoverable': is_recoverable,
                    'failed_files': failed_files[:10] if failed_files else []  # Limit to first 10
                }
            )
            
            # Send notification
            self.notification_service.send_notification(status)
            
            logger.info(
                f"Sent recovery error notification for operation {operation_id}: "
                f"{error_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send recovery error notification: {e}")
    
    def notify_recovery_warning(
        self,
        operation_id: str,
        warning_message: str,
        warning_type: str,
        context: Optional[Dict] = None
    ) -> None:
        """
        Send notification for recovery operation warnings.
        
        Args:
            operation_id: ID of the recovery operation
            warning_message: Human-readable warning message
            warning_type: Type of warning
            context: Optional additional context
        """
        try:
            # Create operation status
            status = OperationStatus(
                operation_id=operation_id,
                operation_type="recovery",
                status=StatusLevel.WARNING,
                message=f"Recovery warning: {warning_message}",
                timestamp=datetime.now(),
                metadata={
                    'warning_type': warning_type,
                    'context': context or {}
                }
            )
            
            # Send notification
            self.notification_service.send_notification(status)
            
            logger.info(
                f"Sent recovery warning notification for operation {operation_id}: "
                f"{warning_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send recovery warning notification: {e}")
    
    def log_recovery_milestone(
        self,
        operation_id: str,
        milestone_name: str,
        milestone_data: Dict
    ) -> None:
        """
        Log a recovery milestone for detailed progress tracking.
        
        This method provides detailed logging of recovery milestones such as
        "validation started", "first file restored", "halfway complete", etc.
        
        Args:
            operation_id: ID of the recovery operation
            milestone_name: Name of the milestone
            milestone_data: Additional data about the milestone
        """
        try:
            # Log to status reporter
            self.status_reporter.update_operation(
                operation_id=operation_id,
                status=StatusLevel.INFO,
                message=f"Milestone: {milestone_name}",
                metadata={
                    'milestone_name': milestone_name,
                    'milestone_data': milestone_data,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(
                f"Logged recovery milestone for operation {operation_id}: "
                f"{milestone_name}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log recovery milestone: {e}")
    
    def generate_progress_report(
        self,
        operation_id: str,
        include_performance_metrics: bool = True
    ) -> Optional[Dict]:
        """
        Generate a detailed progress report for a recovery operation.
        
        This method creates a comprehensive report including progress statistics,
        performance metrics, and operation details.
        
        Args:
            operation_id: ID of the recovery operation
            include_performance_metrics: Whether to include performance metrics
            
        Returns:
            Dictionary containing the progress report, or None if operation not found
        """
        try:
            # Get progress report from monitor
            progress_report = self.progress_monitor.get_progress_report(operation_id)
            
            if not progress_report:
                logger.warning(f"No progress report available for operation {operation_id}")
                return None
            
            # Build report dictionary
            report = progress_report.to_dict()
            
            # Add notification tracking info
            report['milestones_reached'] = list(
                self._milestone_tracker.get(operation_id, set())
            )
            
            # Add performance summary if requested
            if include_performance_metrics:
                perf_summary = self.progress_monitor.get_performance_summary(operation_id)
                if perf_summary:
                    report['performance'] = perf_summary
            
            logger.debug(f"Generated progress report for operation {operation_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate progress report: {e}")
            return None
    
    def _check_milestone(self, operation_id: str, progress_pct: float) -> bool:
        """
        Check if a milestone has been reached and not yet notified.
        
        Args:
            operation_id: ID of the operation
            progress_pct: Current progress percentage
            
        Returns:
            True if a new milestone was reached, False otherwise
        """
        if operation_id not in self._milestone_tracker:
            self._milestone_tracker[operation_id] = set()
        
        reached_milestones = self._milestone_tracker[operation_id]
        
        for milestone in self.DEFAULT_MILESTONES:
            if progress_pct >= milestone and milestone not in reached_milestones:
                reached_milestones.add(milestone)
                return True
        
        return False
    
    def set_milestone_percentages(self, milestones: List[int]) -> None:
        """
        Set custom milestone percentages for progress notifications.
        
        Args:
            milestones: List of percentage values (0-100) for milestones
            
        Raises:
            ValueError: If milestone values are invalid
        """
        if not all(0 <= m <= 100 for m in milestones):
            raise ValueError("Milestone percentages must be between 0 and 100")
        
        self.DEFAULT_MILESTONES = sorted(milestones)
        logger.info(f"Set custom milestone percentages: {self.DEFAULT_MILESTONES}")
    
    def set_notification_interval(self, seconds: int) -> None:
        """
        Set minimum interval between progress notifications.
        
        Args:
            seconds: Minimum seconds between notifications
            
        Raises:
            ValueError: If interval is negative
        """
        if seconds < 0:
            raise ValueError("Notification interval cannot be negative")
        
        self._min_notification_interval = seconds
        logger.info(f"Set notification interval to {seconds} seconds")
    
    def cleanup_operation(self, operation_id: str) -> None:
        """
        Clean up tracking data for a completed operation.
        
        Args:
            operation_id: ID of the operation to clean up
        """
        self._milestone_tracker.pop(operation_id, None)
        self._last_notification_time.pop(operation_id, None)
        logger.debug(f"Cleaned up tracking data for operation {operation_id}")
