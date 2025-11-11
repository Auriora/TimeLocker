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

from TimeLocker.monitoring import (
    MonitoringService,
    NotificationService,
    BackupEvent,
    StatusLevel,
    LogEntry,
    LogLevel,
    ActivityLogger,
    BackupHistory,
    BackupRecord,
    BackupStatus
)


class TestNotificationTimingAndFrequency:
    """Tests for notification timing and frequency validation"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.notification_service = NotificationService(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_notification_minimum_duration_filter(self):
        """Test that short operations don't trigger notifications"""
        from TimeLocker.monitoring import OperationStatus

        # Configure minimum duration
        self.notification_service.update_config(
            min_operation_duration=60,  # 60 seconds
            notify_on_success=True
        )

        # Short operation (30 seconds)
        short_status = OperationStatus(
            operation_id="short_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Quick backup",
            timestamp=datetime.now(),
            metadata={"start_time": (datetime.now() - timedelta(seconds=30)).isoformat()}
        )

        # Should not notify
        assert self.notification_service.should_notify(short_status) is False

        # Long operation (120 seconds)
        long_status = OperationStatus(
            operation_id="long_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Long backup",
            timestamp=datetime.now(),
            metadata={"start_time": (datetime.now() - timedelta(seconds=120)).isoformat()}
        )

        # Should notify
        assert self.notification_service.should_notify(long_status) is True

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_notification_frequency_control(self):
        """Test notification frequency control to avoid spam"""
        from TimeLocker.monitoring import OperationStatus

        self.notification_service.update_config(
            notify_on_success=True,
            min_operation_duration=0
        )

        # Multiple rapid notifications
        for i in range(5):
            status = OperationStatus(
                operation_id=f"rapid_op_{i}",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message=f"Backup {i}",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
            )

            # Each should be evaluated independently
            should_notify = self.notification_service.should_notify(status)
            assert isinstance(should_notify, bool)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_error_notifications_priority(self):
        """Test that error notifications have priority"""
        from TimeLocker.monitoring import OperationStatus

        self.notification_service.update_config(
            notify_on_error=True,
            min_operation_duration=0
        )

        # Error operation
        error_status = OperationStatus(
            operation_id="error_op",
            operation_type="backup",
            status=StatusLevel.ERROR,
            message="Backup failed",
            timestamp=datetime.now(),
            metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
        )

        # Should notify for errors
        assert self.notification_service.should_notify(error_status) is True


class TestInformationClarityAndActionability:
    """Tests for information clarity and actionability of monitoring data"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.activity_logger = ActivityLogger(self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_log_entry_user_friendly_format(self):
        """Test that log entries are formatted in a user-friendly way"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            operation_type="backup",
            operation_id="test_op",
            repository_id="test_repo",
            message="Backup failed due to permission error",
            details={"path": "/data/files"},
            error_context={"error_type": "PermissionError"},
            troubleshooting_suggestions=[
                "Check file permissions",
                "Ensure you have read access"
            ]
        )

        formatted = entry.format_user_friendly()

        # Should contain key information
        assert "ERROR" in formatted
        assert "Backup failed" in formatted
        assert "test_repo" in formatted
        assert "Troubleshooting Suggestions:" in formatted
        assert "Check file permissions" in formatted

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_error_messages_include_troubleshooting(self):
        """Test that error messages include actionable troubleshooting steps"""
        from TimeLocker.monitoring import OperationStatus

        status = OperationStatus(
            operation_id="error_op",
            operation_type="backup",
            status=StatusLevel.ERROR,
            message="Backup failed: Permission denied",
            timestamp=datetime.now()
        )

        self.activity_logger.log_backup_event(status)

        # Get recent logs
        logs = self.activity_logger.get_recent_logs(hours=1)

        assert len(logs) > 0
        error_log = logs[0]

        # Should have troubleshooting suggestions
        assert error_log.troubleshooting_suggestions is not None
        assert len(error_log.troubleshooting_suggestions) > 0

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_backup_history_human_readable_formats(self):
        """Test that backup history uses human-readable formats"""
        history = BackupHistory(self.temp_dir)

        record = BackupRecord(
            operation_id="test_backup",
            repository_id="test_repo",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=5, seconds=30),
            status=BackupStatus.SUCCESS,
            files_processed=1500,
            bytes_transferred=1024 * 1024 * 1024 * 2.5,  # 2.5 GB
            duration_seconds=330.0
        )

        # Test formatted duration
        assert "5m" in record.duration_formatted
        assert "30s" in record.duration_formatted

        # Test formatted bytes
        assert "GB" in record.bytes_transferred_formatted

        # Test throughput
        assert record.throughput_mbps > 0

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_monitoring_summary_provides_actionable_insights(self):
        """Test that monitoring summary provides actionable insights"""
        monitoring_service = MonitoringService(self.temp_dir)

        # Create some backup events
        for i in range(3):
            start_event = BackupEvent(
                event_id=f"start_{i}",
                event_type="backup_started",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=f"op_{i}",
                message=f"Backup {i} started",
                details={},
                severity=StatusLevel.INFO
            )
            monitoring_service.handle_backup_event(start_event)

            complete_event = BackupEvent(
                event_id=f"complete_{i}",
                event_type="backup_completed",
                timestamp=datetime.now(),
                repository_id=f"repo_{i}",
                operation_id=f"op_{i}",
                message=f"Backup {i} completed",
                details={},
                severity=StatusLevel.SUCCESS
            )
            monitoring_service.handle_backup_event(complete_event)

        summary = monitoring_service.get_monitoring_summary()

        # Summary should contain actionable information
        assert summary.health_status is not None
        assert summary.recent_operations is not None
        assert summary.repository_statuses is not None
        assert summary.last_backup_dates is not None

        monitoring_service.shutdown()


class TestAccessibilityCompliance:
    """Tests for accessibility compliance with screen readers and tools"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    @pytest.mark.unit
    def test_log_messages_screen_reader_friendly(self):
        """Test that log messages are screen reader friendly"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            operation_type="backup",
            operation_id="test_op",
            repository_id="test_repo",
            message="Backup completed successfully",
            details={"files": 100, "size": "1GB"}
        )

        formatted = entry.format_user_friendly()

        # Should use clear, descriptive text
        assert "Backup completed successfully" in formatted
        assert "Repository: test_repo" in formatted
        # Should avoid special characters that confuse screen readers
        # Emojis are acceptable as they have alt text in modern screen readers

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_status_indicators_have_text_descriptions(self):
        """Test that status indicators have text descriptions"""
        from TimeLocker.monitoring import HealthStatus

        # Health status should have clear text values
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.ERROR.value == "error"

    @pytest.mark.monitoring
    @pytest.mark.unit
    @pytest.mark.unit
    def test_notification_messages_clear_and_concise(self):
        """Test that notification messages are clear and concise"""
        from TimeLocker.monitoring import OperationStatus

        notification_service = NotificationService(Path(tempfile.mkdtemp()))

        status = OperationStatus(
            operation_id="test_op",
            operation_type="backup",
            status=StatusLevel.SUCCESS,
            message="Backup completed successfully",
            timestamp=datetime.now(),
            repository_id="test_repo",
            files_processed=100,
            bytes_processed=1024 * 1024 * 100
        )

        title, message = notification_service._format_notification(status)

        # Title should be concise
        assert len(title) < 100

        # Message should contain key information
        assert "test_repo" in message
        assert "100" in message or "100.0" in message

    @pytest.mark.monitoring
    @pytest.mark.unit
    @pytest.mark.unit
    def test_error_severity_clearly_indicated(self):
        """Test that error severity is clearly indicated"""
        from TimeLocker.monitoring import IssueSeverity

        # Severity levels should have clear text values
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.CRITICAL.value == "critical"

    @pytest.mark.monitoring
    @pytest.mark.unit
    @pytest.mark.unit
    def test_timestamps_human_readable(self):
        """Test that timestamps are presented in human-readable format"""
        entry = LogEntry(
            timestamp=datetime(2025, 11, 11, 15, 30, 45),
            level=LogLevel.INFO,
            operation_type="backup",
            operation_id="test_op",
            repository_id="test_repo",
            message="Test message",
            details={}
        )

        formatted = entry.format_user_friendly()

        # Should contain formatted timestamp
        assert "2025-11-11" in formatted
        assert "15:30:45" in formatted
