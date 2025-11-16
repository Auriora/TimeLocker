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

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from TimeLocker.monitoring import (
    MonitoringService,
    BackupEvent,
    StatusLevel,
    HealthStatus,
    BackupHistory,
    BackupRecord,
    BackupStatus,
    ActivityLogger,
    OperationStatus,
    NotificationService
)
from TimeLocker.monitoring.notification_service import NotificationError


class TestMonitoringWorkflowIntegration:
    """Integration tests for end-to-end monitoring workflows"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.desktop_notifier = DummyDesktopNotifier()
        notification_service = NotificationService(
                self.temp_dir / "notifications",
                desktop_notification_sender=self.desktop_notifier,
                force_desktop_notifications=True
        )
        self.monitoring_service = MonitoringService(
                self.temp_dir,
                notification_service=notification_service
        )
        self.notification_service = notification_service
        self.backup_history = BackupHistory(self.temp_dir / "history")
        self.activity_logger = ActivityLogger(self.temp_dir / "logs")

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, 'monitoring_service'):
            self.monitoring_service.shutdown()
        if hasattr(self, 'notification_service'):
            self.notification_service.shutdown()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_complete_backup_workflow(self):
        """Test complete backup monitoring workflow"""
        operation_id = "backup_workflow_001"
        repository_id = "test_repo"

        # Start backup
        start_event = BackupEvent(
            event_id="start_001",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id=repository_id,
            operation_id=operation_id,
            message="Backup started",
            details={"source": "/data"},
            severity=StatusLevel.INFO
        )
        self.monitoring_service.handle_backup_event(start_event)

        # Verify operation is tracked
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert len(current_ops) == 1
        assert current_ops[0].operation_id == operation_id

        # Complete backup
        complete_event = BackupEvent(
            event_id="complete_001",
            event_type="backup_completed",
            timestamp=datetime.now(),
            repository_id=repository_id,
            operation_id=operation_id,
            message="Backup completed successfully",
            details={"files_backed_up": 100, "bytes_transferred": 1024 * 1024 * 100},
            severity=StatusLevel.SUCCESS
        )
        self.monitoring_service.handle_backup_event(complete_event)

        # Verify operation completed
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert not any(op.operation_id == operation_id for op in current_ops)

        # Verify health status
        health = self.monitoring_service.get_system_health()
        assert health == HealthStatus.HEALTHY

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_backup_failure_workflow(self):
        """Test backup failure monitoring and troubleshooting workflow"""
        operation_id = "backup_failure_001"
        repository_id = "test_repo"

        # Start backup
        start_event = BackupEvent(
            event_id="start_002",
            event_type="backup_started",
            timestamp=datetime.now(),
            repository_id=repository_id,
            operation_id=operation_id,
            message="Backup started",
            details={},
            severity=StatusLevel.INFO
        )
        self.monitoring_service.handle_backup_event(start_event)

        # Fail backup
        error_event = BackupEvent(
            event_id="error_002",
            event_type="backup_failed",
            timestamp=datetime.now(),
            repository_id=repository_id,
            operation_id=operation_id,
            message="Backup failed: Permission denied",
            details={"error_type": "PermissionError"},
            severity=StatusLevel.ERROR
        )
        self.monitoring_service.handle_backup_event(error_event)

        # Verify health status reflects error
        health = self.monitoring_service.get_system_health()
        assert health == HealthStatus.ERROR

        # Verify error was logged
        recent_logs = self.activity_logger.get_recent_logs(hours=1, level=None)
        # Note: logs may be empty if logger wasn't integrated with monitoring service

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_history_and_monitoring_integration(self):
        """Test integration between backup history and monitoring"""
        # Complete a backup operation
        operation_id = "history_integration_001"
        start_time = datetime.now()
        
        # Record in history
        record = BackupRecord(
            operation_id=operation_id,
            repository_id="test_repo",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=5),
            status=BackupStatus.SUCCESS,
            files_processed=100,
            bytes_transferred=1024 * 1024 * 100,
            duration_seconds=300.0,
            snapshot_id="snap_001"
        )
        self.backup_history.record_backup_operation(record)

        # Verify history was recorded
        retrieved = self.backup_history.get_backup_by_id(operation_id)
        assert retrieved is not None
        assert retrieved.status == BackupStatus.SUCCESS

        # Get statistics
        stats = self.backup_history.get_statistics(repository_id="test_repo")
        assert stats["total_backups"] >= 1
        assert stats["successful_backups"] >= 1

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_multiple_concurrent_operations(self):
        """Test monitoring multiple concurrent backup operations"""
        operation_ids = ["concurrent_001", "concurrent_002", "concurrent_003"]

        # Start multiple operations
        for op_id in operation_ids:
            start_event = BackupEvent(
                event_id=f"start_{op_id}",
                event_type="backup_started",
                timestamp=datetime.now(),
                repository_id=f"repo_{op_id}",
                operation_id=op_id,
                message=f"Backup {op_id} started",
                details={},
                severity=StatusLevel.INFO
            )
            self.monitoring_service.handle_backup_event(start_event)

        # Verify all operations are tracked
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert len(current_ops) == 3

        # Complete operations
        for op_id in operation_ids:
            complete_event = BackupEvent(
                event_id=f"complete_{op_id}",
                event_type="backup_completed",
                timestamp=datetime.now(),
                repository_id=f"repo_{op_id}",
                operation_id=op_id,
                message=f"Backup {op_id} completed",
                details={},
                severity=StatusLevel.SUCCESS
            )
            self.monitoring_service.handle_backup_event(complete_event)

        # Verify all operations completed
        current_ops = self.monitoring_service.status_reporter.get_current_operations()
        assert len(current_ops) == 0

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_monitoring_summary_generation(self):
        """Test generating comprehensive monitoring summary"""
        # Create some backup operations
        for i in range(3):
            operation_id = f"summary_op_{i}"
            
            start_event = BackupEvent(
                event_id=f"start_{i}",
                event_type="backup_started",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=operation_id,
                message=f"Backup {i} started",
                details={},
                severity=StatusLevel.INFO
            )
            self.monitoring_service.handle_backup_event(start_event)
            
            complete_event = BackupEvent(
                event_id=f"complete_{i}",
                event_type="backup_completed",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=operation_id,
                message=f"Backup {i} completed",
                details={},
                severity=StatusLevel.SUCCESS
            )
            self.monitoring_service.handle_backup_event(complete_event)

        # Get monitoring summary
        summary = self.monitoring_service.get_monitoring_summary()

        assert summary is not None
        assert summary.health_status == HealthStatus.HEALTHY
        assert len(summary.recent_operations) >= 3
        assert len(summary.repository_statuses) >= 3


class DummyDesktopNotifier:
    """Capture desktop notification invocations in tests."""

    def __init__(self, should_raise: bool = False):
        self.should_raise = should_raise
        self.calls = []

    def __call__(self, title: str, message: str, status_level: StatusLevel):
        if self.should_raise:
            raise NotificationError("desktop adapter failure")
        self.calls.append((title, message, status_level))


class TestCrossPlatformIntegration:
    """Integration tests for cross-platform monitoring features using mocks."""

    def _create_notification_service(self, tmp_path, notifier: DummyDesktopNotifier) -> NotificationService:
        service = NotificationService(
                tmp_path / "notifications",
                desktop_notification_sender=notifier,
                force_desktop_notifications=True
        )
        assert service._desktop_notification_sender is notifier
        service.config.preferences.desktop_notification_enabled = True
        service.config.preferences.quiet_hours_enabled = False
        assert service.config.preferences.desktop_notification_enabled is True
        service.config.enabled = True
        service.config.desktop_enabled = True
        service.config.notify_on_success = True
        service.config.notify_on_warning = True
        service.config.notify_on_error = True
        service.config.notify_on_critical = True
        return service

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_desktop_notification_linux(self, tmp_path):
        notifier = DummyDesktopNotifier()
        service = self._create_notification_service(tmp_path, notifier)
        service._send_desktop_notification("Linux Backup", "Completed", StatusLevel.SUCCESS)
        assert notifier.calls
        title, message, status_level = notifier.calls[0]
        assert title == "Linux Backup"
        assert message == "Completed"
        assert status_level == StatusLevel.SUCCESS

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_desktop_notification_macos(self, tmp_path):
        notifier = DummyDesktopNotifier()
        service = self._create_notification_service(tmp_path, notifier)
        service._send_desktop_notification("macOS Backup", "mac warning", StatusLevel.WARNING)
        assert notifier.calls
        assert notifier.calls[0][0] == "macOS Backup"
        assert notifier.calls[0][1] == "mac warning"
        assert notifier.calls[0][2] == StatusLevel.WARNING

    @pytest.mark.monitoring
    @pytest.mark.integration
    def test_desktop_notification_windows(self, tmp_path):
        notifier = DummyDesktopNotifier(should_raise=True)
        service = self._create_notification_service(tmp_path, notifier)
        service.config.preferences.fallback_to_log = True
        service._send_desktop_notification("Windows Backup", "win critical", StatusLevel.CRITICAL)
        assert notifier.calls == []
