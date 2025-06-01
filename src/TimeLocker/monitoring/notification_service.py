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

import json
import logging
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .status_reporter import OperationStatus, StatusLevel

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Base exception for notification-related errors"""
    pass


class NotificationType(Enum):
    """Types of notifications"""
    DESKTOP = "desktop"
    EMAIL = "email"
    LOG = "log"


@dataclass
class NotificationConfig:
    """Configuration for notifications"""
    enabled: bool = True
    desktop_enabled: bool = True
    email_enabled: bool = False
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = None
    notify_on_success: bool = True
    notify_on_warning: bool = True
    notify_on_error: bool = True
    notify_on_critical: bool = True
    min_operation_duration: int = 60  # Only notify for operations longer than this (seconds)

    def __post_init__(self):
        if self.email_to is None:
            self.email_to = []


class NotificationService:
    """
    Notification service for TimeLocker operations
    Supports desktop notifications and email alerts
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize notification service
        
        Args:
            config_dir: Directory for notification configuration
        """
        if config_dir is None:
            config_dir = Path.home() / ".timelocker" / "notifications"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "notification_config.json"
        self.config = self._load_config()

    def _load_config(self) -> NotificationConfig:
        """Load notification configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return NotificationConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load notification config: {e}")

        # Return default config
        return NotificationConfig()

    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                # Convert dataclass to dict, handling the email_to list
                config_dict = {
                        'enabled':                self.config.enabled,
                        'desktop_enabled':        self.config.desktop_enabled,
                        'email_enabled':          self.config.email_enabled,
                        'email_smtp_server':      self.config.email_smtp_server,
                        'email_smtp_port':        self.config.email_smtp_port,
                        'email_username':         self.config.email_username,
                        'email_password':         self.config.email_password,
                        'email_from':             self.config.email_from,
                        'email_to':               self.config.email_to,
                        'notify_on_success':      self.config.notify_on_success,
                        'notify_on_warning':      self.config.notify_on_warning,
                        'notify_on_error':        self.config.notify_on_error,
                        'notify_on_critical':     self.config.notify_on_critical,
                        'min_operation_duration': self.config.min_operation_duration
                }
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save notification config: {e}")
            raise NotificationError(f"Failed to save notification config: {e}")

    def update_config(self, **kwargs):
        """Update notification configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save_config()

    def should_notify(self, status: OperationStatus) -> bool:
        """
        Determine if a notification should be sent for the given status
        
        Args:
            status: Operation status to check
            
        Returns:
            bool: True if notification should be sent
        """
        if not self.config.enabled:
            return False

        # Check if we should notify for this status level
        status_checks = {
                StatusLevel.SUCCESS:  self.config.notify_on_success,
                StatusLevel.WARNING:  self.config.notify_on_warning,
                StatusLevel.ERROR:    self.config.notify_on_error,
                StatusLevel.CRITICAL: self.config.notify_on_critical,
                StatusLevel.INFO:     False  # Don't notify for info messages
        }

        if not status_checks.get(status.status, False):
            return False

        # Check minimum operation duration if we have start time
        if status.metadata and 'start_time' in status.metadata:
            try:
                start_time = datetime.fromisoformat(status.metadata['start_time'])
                duration = (status.timestamp - start_time).total_seconds()
                if duration < self.config.min_operation_duration:
                    return False
            except (ValueError, KeyError):
                pass

        return True

    def send_notification(self, status: OperationStatus, notification_types: Optional[List[NotificationType]] = None):
        """
        Send notification for an operation status
        
        Args:
            status: Operation status to notify about
            notification_types: Types of notifications to send (default: all enabled)
        """
        if not self.should_notify(status):
            return

        if notification_types is None:
            notification_types = []
            if self.config.desktop_enabled:
                notification_types.append(NotificationType.DESKTOP)
            if self.config.email_enabled:
                notification_types.append(NotificationType.EMAIL)

        title, message = self._format_notification(status)

        for notification_type in notification_types:
            try:
                if notification_type == NotificationType.DESKTOP:
                    self._send_desktop_notification(title, message, status.status)
                elif notification_type == NotificationType.EMAIL:
                    self._send_email_notification(title, message, status)
                elif notification_type == NotificationType.LOG:
                    self._log_notification(title, message, status)
            except Exception as e:
                logger.error(f"Failed to send {notification_type.value} notification: {e}")

    def _format_notification(self, status: OperationStatus) -> tuple[str, str]:
        """Format notification title and message"""
        # Create title
        status_emoji = {
                StatusLevel.SUCCESS:  "✅",
                StatusLevel.WARNING:  "⚠️",
                StatusLevel.ERROR:    "❌",
                StatusLevel.CRITICAL: "🚨",
                StatusLevel.INFO:     "ℹ️"
        }

        emoji = status_emoji.get(status.status, "")
        title = f"{emoji} TimeLocker {status.operation_type.title()}"

        # Create message
        message_parts = [status.message]

        if status.repository_id:
            message_parts.append(f"Repository: {status.repository_id}")

        if status.progress_percentage is not None:
            message_parts.append(f"Progress: {status.progress_percentage}%")

        if status.files_processed is not None and status.total_files is not None:
            message_parts.append(f"Files: {status.files_processed}/{status.total_files}")

        if status.bytes_processed is not None:
            size_mb = status.bytes_processed / (1024 * 1024)
            message_parts.append(f"Data: {size_mb:.1f} MB")

        message_parts.append(f"Time: {status.timestamp.strftime('%H:%M:%S')}")

        return title, "\n".join(message_parts)

    def _send_desktop_notification(self, title: str, message: str, status_level: StatusLevel):
        """Send desktop notification"""
        try:
            # Try different notification systems based on platform
            if sys.platform == "linux":
                self._send_linux_notification(title, message, status_level)
            elif sys.platform == "darwin":
                self._send_macos_notification(title, message)
            elif sys.platform == "win32":
                self._send_windows_notification(title, message)
            else:
                logger.warning(f"Desktop notifications not supported on {sys.platform}")
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")

    def _send_linux_notification(self, title: str, message: str, status_level: StatusLevel):
        """Send notification on Linux using notify-send"""
        urgency_map = {
                StatusLevel.SUCCESS:  "normal",
                StatusLevel.WARNING:  "normal",
                StatusLevel.ERROR:    "critical",
                StatusLevel.CRITICAL: "critical",
                StatusLevel.INFO:     "low"
        }

        urgency = urgency_map.get(status_level, "normal")

        subprocess.run([
                "notify-send",
                "--urgency", urgency,
                "--app-name", "TimeLocker",
                title,
                message
        ], check=True)

    def _send_macos_notification(self, title: str, message: str):
        """Send notification on macOS using osascript"""
        script = f'''
        display notification "{message}" with title "{title}" sound name "default"
        '''
        subprocess.run(["osascript", "-e", script], check=True)

    def _send_windows_notification(self, title: str, message: str):
        """Send notification on Windows using PowerShell"""
        # Escape quotes and special characters for PowerShell
        escaped_title = title.replace('"', '""').replace("'", "''")
        escaped_message = message.replace('"', '""').replace("'", "''")

        # Use a more robust PowerShell approach with proper error handling
        script = f'''
        try {{
            Add-Type -AssemblyName System.Windows.Forms
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = "{escaped_title}"
            $notification.BalloonTipText = "{escaped_message}"
            $notification.Visible = $true
            $notification.ShowBalloonTip(5000)
            Start-Sleep -Seconds 1
            $notification.Dispose()
        }} catch {{
            Write-Error "Failed to show notification: $_"
            exit 1
        }}
        '''
        subprocess.run(["powershell", "-Command", script], check=True)

    def _send_email_notification(self, title: str, message: str, status: OperationStatus):
        """Send email notification"""
        if not self.config.email_enabled or not self.config.email_to:
            return

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from or self.config.email_username
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = title

            # Create HTML body
            html_body = self._create_email_html(status, message)
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                server.starttls()
                if self.config.email_username and self.config.email_password:
                    server.login(self.config.email_username, self.config.email_password)
                server.send_message(msg)

            logger.info(f"Email notification sent to {', '.join(self.config.email_to)}")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            raise NotificationError(f"Failed to send email notification: {e}")

    def _create_email_html(self, status: OperationStatus, message: str) -> str:
        """Create HTML email body"""
        status_colors = {
                StatusLevel.SUCCESS:  "#28a745",
                StatusLevel.WARNING:  "#ffc107",
                StatusLevel.ERROR:    "#dc3545",
                StatusLevel.CRITICAL: "#dc3545",
                StatusLevel.INFO:     "#17a2b8"
        }

        color = status_colors.get(status.status, "#6c757d")

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    TimeLocker {status.operation_type.title()} - {status.status.value.title()}
                </h2>
                <p><strong>Message:</strong> {status.message}</p>
                <p><strong>Time:</strong> {status.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                {f'<p><strong>Repository:</strong> {status.repository_id}</p>' if status.repository_id else ''}
                {f'<p><strong>Progress:</strong> {status.progress_percentage}%</p>' if status.progress_percentage is not None else ''}
                {f'<p><strong>Files Processed:</strong> {status.files_processed}/{status.total_files}</p>' if status.files_processed is not None and status.total_files is not None else ''}
            </div>
            <hr style="margin: 20px 0;">
            <p style="color: #6c757d; font-size: 12px;">
                This notification was sent by TimeLocker backup system.
            </p>
        </body>
        </html>
        """

    def _log_notification(self, title: str, message: str, status: OperationStatus):
        """Log notification to file"""
        log_entry = {
                "timestamp": datetime.now().isoformat(),
                "title":     title,
                "message":   message,
                "status":    status.to_dict()
        }

        notification_log = self.config_dir / "notifications.log"
        try:
            with open(notification_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")

    def test_notifications(self) -> Dict[str, bool]:
        """
        Test notification systems
        
        Returns:
            Dict with test results for each notification type
        """
        results = {}

        test_status = OperationStatus(
                operation_id="test",
                operation_type="test",
                status=StatusLevel.SUCCESS,
                message="This is a test notification from TimeLocker",
                timestamp=datetime.now()
        )

        # Test desktop notification
        if self.config.desktop_enabled:
            try:
                title, message = self._format_notification(test_status)
                self._send_desktop_notification(title, message, test_status.status)
                results['desktop'] = True
            except Exception as e:
                logger.error(f"Desktop notification test failed: {e}")
                results['desktop'] = False

        # Test email notification
        if self.config.email_enabled:
            try:
                title, message = self._format_notification(test_status)
                self._send_email_notification(title, message, test_status)
                results['email'] = True
            except Exception as e:
                logger.error(f"Email notification test failed: {e}")
                results['email'] = False

        return results
