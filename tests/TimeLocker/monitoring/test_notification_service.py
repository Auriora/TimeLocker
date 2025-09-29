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
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.monitoring import NotificationService, NotificationType, OperationStatus, StatusLevel


class TestNotificationService:
    """Test suite for NotificationService"""

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
    def test_initialization(self):
        """Test notification service initialization"""
        assert self.notification_service.config_dir.exists()
        assert self.notification_service.config is not None
        assert self.notification_service.config.enabled is True

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_default_configuration(self):
        """Test default configuration values"""
        config = self.notification_service.config

        assert config.enabled is True
        assert config.desktop_enabled is True
        assert config.email_enabled is False
        assert config.notify_on_success is True
        assert config.notify_on_error is True
        assert config.min_operation_duration == 60

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_configuration_persistence(self):
        """Test configuration save and load"""
        # Update configuration
        self.notification_service.update_config(
                desktop_enabled=False,
                email_enabled=True,
                email_smtp_server="smtp.example.com",
                email_to=["test@example.com"]
        )

        # Create new service (simulating restart)
        new_service = NotificationService(self.temp_dir)

        # Verify configuration was loaded
        assert new_service.config.desktop_enabled is False
        assert new_service.config.email_enabled is True
        assert new_service.config.email_smtp_server == "smtp.example.com"
        assert "test@example.com" in new_service.config.email_to

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_should_notify_success(self):
        """Test notification decision for success status"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
        )

        # Should notify for success (default config)
        assert self.notification_service.should_notify(status) is True

        # Disable success notifications
        self.notification_service.update_config(notify_on_success=False)
        assert self.notification_service.should_notify(status) is False

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_should_notify_error(self):
        """Test notification decision for error status"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.ERROR,
                message="Backup failed",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
        )

        # Should notify for error (default config)
        assert self.notification_service.should_notify(status) is True

        # Disable error notifications
        self.notification_service.update_config(notify_on_error=False)
        assert self.notification_service.should_notify(status) is False

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_should_notify_duration_filter(self):
        """Test notification filtering based on operation duration"""
        # Short operation (less than minimum duration)
        short_status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Quick backup",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(seconds=30)).isoformat()}
        )

        # Should not notify for short operations
        assert self.notification_service.should_notify(short_status) is False

        # Long operation (exceeds minimum duration)
        long_status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Long backup",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
        )

        # Should notify for long operations
        assert self.notification_service.should_notify(long_status) is True

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_should_notify_disabled(self):
        """Test notification when service is disabled"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed",
                timestamp=datetime.now()
        )

        # Disable notifications
        self.notification_service.update_config(enabled=False)

        # Should not notify when disabled
        assert self.notification_service.should_notify(status) is False

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_format_notification(self):
        """Test notification formatting"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed successfully",
                timestamp=datetime.now(),
                repository_id="test_repo",
                progress_percentage=100,
                files_processed=150,
                total_files=150,
                bytes_processed=1024 * 1024 * 50  # 50MB
        )

        title, message = self.notification_service._format_notification(status)

        # Verify title
        assert "TimeLocker Backup" in title
        assert "✅" in title  # Success emoji

        # Verify message content
        assert "Backup completed successfully" in message
        assert "test_repo" in message
        assert "100%" in message
        assert "150/150" in message
        assert "50.0 MB" in message

    @patch('subprocess.run')
    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_send_linux_notification(self, mock_subprocess):
        """Test Linux desktop notification"""
        mock_subprocess.return_value = None

        with patch('sys.platform', 'linux'):
            self.notification_service._send_desktop_notification(
                    "Test Title", "Test Message", StatusLevel.SUCCESS
            )

        # Verify notify-send was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "notify-send" in call_args
        assert "Test Title" in call_args
        assert "Test Message" in call_args

    @patch('subprocess.run')
    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_send_macos_notification(self, mock_subprocess):
        """Test macOS desktop notification"""
        mock_subprocess.return_value = None

        with patch('sys.platform', 'darwin'):
            self.notification_service._send_desktop_notification(
                    "Test Title", "Test Message", StatusLevel.SUCCESS
            )

        # Verify osascript was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "osascript" in call_args

    @patch('subprocess.run')
    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_send_windows_notification(self, mock_subprocess):
        """Test Windows desktop notification"""
        mock_subprocess.return_value = None

        with patch('sys.platform', 'win32'):
            self.notification_service._send_desktop_notification(
                    "Test Title", "Test Message", StatusLevel.SUCCESS
            )

        # Verify PowerShell was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "powershell" in call_args

    @patch('smtplib.SMTP')
    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_send_email_notification(self, mock_smtp_class):
        """Test email notification"""
        # Setup email configuration
        self.notification_service.update_config(
                email_enabled=True,
                email_smtp_server="smtp.example.com",
                email_smtp_port=587,
                email_username="test@example.com",
                email_password="password",
                email_from="test@example.com",
                email_to=["recipient@example.com"]
        )

        # Mock SMTP
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed",
                timestamp=datetime.now()
        )

        title, message = self.notification_service._format_notification(status)

        # Send email notification
        self.notification_service._send_email_notification(title, message, status)

        # Verify SMTP was used
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("test@example.com", "password")
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_create_email_html(self):
        """Test HTML email creation"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed successfully",
                timestamp=datetime.now(),
                repository_id="test_repo",
                progress_percentage=100
        )

        html = self.notification_service._create_email_html(status, "Test message")

        # Verify HTML content
        assert "<html>" in html
        assert "TimeLocker Backup" in html
        assert "Backup completed successfully" in html
        assert "test_repo" in html
        assert "100%" in html
        assert "#28a745" in html  # Success color

    @patch.object(NotificationService, '_send_desktop_notification')
    @patch.object(NotificationService, '_send_email_notification')
    @pytest.mark.integration
    @pytest.mark.monitoring
    def test_send_notification_integration(self, mock_email, mock_desktop):
        """Test integrated notification sending"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed",
                timestamp=datetime.now(),
                metadata={"start_time": (datetime.now() - timedelta(minutes=2)).isoformat()}
        )

        # Configure for both desktop and email
        self.notification_service.update_config(
                desktop_enabled=True,
                email_enabled=True,
                email_to=["test@example.com"]
        )

        # Send notification
        self.notification_service.send_notification(status)

        # Verify both methods were called
        mock_desktop.assert_called_once()
        mock_email.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_send_notification_filtering(self):
        """Test notification filtering"""
        # Create status that should not trigger notification
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.INFO,  # Info level not configured for notification
                message="Backup in progress",
                timestamp=datetime.now()
        )

        with patch.object(self.notification_service, '_send_desktop_notification') as mock_desktop:
            self.notification_service.send_notification(status)

            # Should not send notification for INFO level
            mock_desktop.assert_not_called()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_test_notifications(self):
        """Test notification testing functionality"""
        with patch.object(self.notification_service, '_send_desktop_notification') as mock_desktop, \
                patch.object(self.notification_service, '_send_email_notification') as mock_email:
            # Configure for testing
            self.notification_service.update_config(
                    desktop_enabled=True,
                    email_enabled=True,
                    email_to=["test@example.com"]
            )

            # Test notifications
            results = self.notification_service.test_notifications()

            # Verify test results
            assert "desktop" in results
            assert "email" in results
            assert results["desktop"] is True
            assert results["email"] is True

            # Verify test methods were called
            mock_desktop.assert_called_once()
            mock_email.assert_called_once()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_notification_logging(self):
        """Test notification logging"""
        status = OperationStatus(
                operation_id="test",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Backup completed",
                timestamp=datetime.now()
        )

        title, message = self.notification_service._format_notification(status)

        # Log notification
        self.notification_service._log_notification(title, message, status)

        # Verify log file was created
        log_file = self.notification_service.config_dir / "notifications.log"
        assert log_file.exists()

        # Verify log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            # Check for the title (may be Unicode encoded in JSON)
            assert "TimeLocker Backup" in log_content
            # Check for the main message content (newlines are escaped in JSON)
            assert "Backup completed" in log_content

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_notification_config_dataclass(self):
        """Test NotificationConfig dataclass"""
        from TimeLocker.monitoring.notification_service import NotificationConfig

        # Test default values
        config = NotificationConfig()
        assert config.enabled is True
        assert config.desktop_enabled is True
        assert config.email_enabled is False
        assert config.email_to == []

        # Test custom values
        config = NotificationConfig(
                enabled=False,
                email_enabled=True,
                email_to=["test@example.com"]
        )
        assert config.enabled is False
        assert config.email_enabled is True
        assert config.email_to == ["test@example.com"]
