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
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .status_reporter import OperationStatus, StatusLevel
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Base exception for notification-related errors"""

    pass


class NotificationType(Enum):
    """Types of notifications"""

    DESKTOP = "desktop"
    EMAIL = "email"
    LOG = "log"


class NotificationEventType(Enum):
    """Types of events that can trigger notifications"""

    BACKUP_STARTED = "backup_started"
    BACKUP_COMPLETED = "backup_completed"
    BACKUP_FAILED = "backup_failed"
    RESTORE_STARTED = "restore_started"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    INTEGRITY_CHECK_PASSED = "integrity_check_passed"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    STORAGE_WARNING = "storage_warning"
    STORAGE_CRITICAL = "storage_critical"


@dataclass
class NotificationPreferences:
    """User preferences for notifications"""

    enabled_event_types: List[str] = None
    desktop_notification_enabled: bool = True
    desktop_notification_sound: bool = True
    desktop_notification_persistence: int = 5  # seconds
    email_notification_enabled: bool = False
    fallback_to_log: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"

    def __post_init__(self):
        if self.enabled_event_types is None:
            # Default to all event types
            self.enabled_event_types = [e.value for e in NotificationEventType]


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
    min_operation_duration: int = (
        60  # Only notify for operations longer than this (seconds)
    )
    preferences: Optional[NotificationPreferences] = None

    def __post_init__(self):
        if self.email_to is None:
            self.email_to = []
        if self.preferences is None:
            self.preferences = NotificationPreferences()


class NotificationService(ServiceInterface):
    """
    Notification service for TimeLocker operations
    Supports desktop notifications and email alerts
    """

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        desktop_notification_sender: Optional[
            Callable[[str, str, StatusLevel], None]
        ] = None,
        force_desktop_notifications: bool = False,
    ) -> None:
        """
        Initialize notification service

        Args:
            config_dir: Directory for notification configuration
        """
        if config_dir is None:
            # Use centralized path resolver for XDG compliance
            from ..config.configuration_path_resolver import ConfigurationPathResolver

            config_dir = (
                ConfigurationPathResolver.get_config_directory() / "notifications"
            )

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "notification_config.json"
        self.config = self._load_config()
        self._desktop_notification_sender = (
            desktop_notification_sender or self._platform_desktop_notification_sender
        )
        self._force_desktop_notifications = force_desktop_notifications

        # ServiceInterface implementation
        self._context: Optional[ServiceContext] = None
        self._initialized = False

    # ServiceInterface implementation
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the notification service with the provided context.

        Args:
            context: ServiceContext containing configuration and runtime information

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to NotificationService")
                return False

            self._context = context

            # Initialize any context-dependent components
            logger.info("NotificationService initialized successfully")
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize NotificationService: {e}")
            return False

    def shutdown(self) -> None:
        """
        Shutdown the notification service and clean up resources.
        """
        try:
            # Save current configuration
            try:
                self.save_config()
            except Exception as e:
                logger.warning(
                    f"Failed to save notification config during shutdown: {e}"
                )

            # Clean up resources
            self._context = None
            self._initialized = False
            logger.info("NotificationService shutdown completed")

        except Exception as e:
            logger.error(f"Error during NotificationService shutdown: {e}")

    def health_check(self) -> bool:
        """
        Check the health status of the notification service.

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

            # Check if configuration is valid
            if not self.config:
                return False

            return True

        except Exception as e:
            logger.error(f"NotificationService health check failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.

        Returns:
            List[str]: List of capability identifiers
        """
        return [
            "desktop_notifications",
            "email_notifications",
            "log_notifications",
            "notification_testing",
            "notification_config",
        ]

    def _load_config(self) -> NotificationConfig:
        """Load notification configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    # Handle preferences separately
                    if "preferences" in data and isinstance(data["preferences"], dict):
                        data["preferences"] = NotificationPreferences(
                            **data["preferences"]
                        )
                    return NotificationConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load notification config: {e}")

        # Return default config
        return NotificationConfig()

    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                # Convert dataclass to dict, handling the email_to list and preferences
                config_dict = {
                    "enabled": self.config.enabled,
                    "desktop_enabled": self.config.desktop_enabled,
                    "email_enabled": self.config.email_enabled,
                    "email_smtp_server": self.config.email_smtp_server,
                    "email_smtp_port": self.config.email_smtp_port,
                    "email_username": self.config.email_username,
                    "email_password": self.config.email_password,
                    "email_from": self.config.email_from,
                    "email_to": self.config.email_to,
                    "notify_on_success": self.config.notify_on_success,
                    "notify_on_warning": self.config.notify_on_warning,
                    "notify_on_error": self.config.notify_on_error,
                    "notify_on_critical": self.config.notify_on_critical,
                    "min_operation_duration": self.config.min_operation_duration,
                    "preferences": {
                        "enabled_event_types": self.config.preferences.enabled_event_types,
                        "desktop_notification_enabled": self.config.preferences.desktop_notification_enabled,
                        "desktop_notification_sound": self.config.preferences.desktop_notification_sound,
                        "desktop_notification_persistence": self.config.preferences.desktop_notification_persistence,
                        "email_notification_enabled": self.config.preferences.email_notification_enabled,
                        "fallback_to_log": self.config.preferences.fallback_to_log,
                        "quiet_hours_enabled": self.config.preferences.quiet_hours_enabled,
                        "quiet_hours_start": self.config.preferences.quiet_hours_start,
                        "quiet_hours_end": self.config.preferences.quiet_hours_end,
                    },
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

    def update_preferences(self, **kwargs):
        """
        Update notification preferences

        Args:
            **kwargs: Preference key-value pairs to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config.preferences, key):
                setattr(self.config.preferences, key, value)
        self.save_config()

    def is_event_type_enabled(self, event_type: str) -> bool:
        """
        Check if a specific event type is enabled for notifications

        Args:
            event_type: Event type to check

        Returns:
            bool: True if event type is enabled
        """
        return event_type in self.config.preferences.enabled_event_types

    def is_in_quiet_hours(self) -> bool:
        """
        Check if current time is within quiet hours

        Returns:
            bool: True if in quiet hours
        """
        if not self.config.preferences.quiet_hours_enabled:
            return False

        try:
            now = datetime.now().time()
            start = datetime.strptime(
                self.config.preferences.quiet_hours_start, "%H:%M"
            ).time()
            end = datetime.strptime(
                self.config.preferences.quiet_hours_end, "%H:%M"
            ).time()

            # Handle quiet hours that span midnight
            if start <= end:
                return start <= now <= end
            else:
                return now >= start or now <= end
        except Exception as e:
            logger.warning(f"Failed to check quiet hours: {e}")
            return False

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
            StatusLevel.SUCCESS: self.config.notify_on_success,
            StatusLevel.WARNING: self.config.notify_on_warning,
            StatusLevel.ERROR: self.config.notify_on_error,
            StatusLevel.CRITICAL: self.config.notify_on_critical,
            StatusLevel.INFO: False,  # Don't notify for info messages
        }

        if not status_checks.get(status.status, False):
            return False

        # Check minimum operation duration if we have start time
        if status.metadata and "start_time" in status.metadata:
            try:
                start_time = datetime.fromisoformat(status.metadata["start_time"])
                duration = (status.timestamp - start_time).total_seconds()
                if duration < self.config.min_operation_duration:
                    return False
            except (ValueError, KeyError):
                pass

        return True

    def send_notification(
        self,
        status: OperationStatus,
        notification_types: Optional[List[NotificationType]] = None,
    ):
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
                logger.error(
                    f"Failed to send {notification_type.value} notification: {e}"
                )

    def _format_notification(self, status: OperationStatus) -> tuple[str, str]:
        """Format notification title and message"""
        # Create title
        status_emoji = {
            StatusLevel.SUCCESS: "✅",
            StatusLevel.WARNING: "⚠️",
            StatusLevel.ERROR: "❌",
            StatusLevel.CRITICAL: "🚨",
            StatusLevel.INFO: "ℹ️",
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
            message_parts.append(
                f"Files: {status.files_processed}/{status.total_files}"
            )

        if status.bytes_processed is not None:
            size_mb = status.bytes_processed / (1024 * 1024)
            message_parts.append(f"Data: {size_mb:.1f} MB")

        message_parts.append(f"Time: {status.timestamp.strftime('%H:%M:%S')}")

        return title, "\n".join(message_parts)

    def _send_desktop_notification(
        self, title: str, message: str, status_level: StatusLevel
    ):
        """
        Send desktop notification with fallback mechanisms

        Args:
            title: Notification title
            message: Notification message
            status_level: Status level for urgency
        """
        # Check if desktop notifications are enabled in preferences
        if not (
            self.config.preferences.desktop_notification_enabled
            or self._force_desktop_notifications
        ):
            logger.debug("Desktop notifications disabled in preferences")
            if self.config.preferences.fallback_to_log:
                self._fallback_to_log(title, message, status_level)
            return

        # Check quiet hours (skip when forced for test adapters)
        if (
            self.config.preferences.quiet_hours_enabled
            and not self._force_desktop_notifications
        ):
            if self.is_in_quiet_hours():
                logger.debug("Skipping notification during quiet hours")
                if self.config.preferences.fallback_to_log:
                    self._fallback_to_log(title, message, status_level)
                return

        try:
            self._desktop_notification_sender(title, message, status_level)
        except NotificationError as e:
            logger.error(f"Failed to send desktop notification: {e}")
            if self.config.preferences.fallback_to_log:
                self._fallback_to_log(title, message, status_level)
        except Exception as e:
            logger.error(f"Unexpected desktop notification error: {e}")
            if self.config.preferences.fallback_to_log:
                self._fallback_to_log(title, message, status_level)

    def _platform_desktop_notification_sender(
        self, title: str, message: str, status_level: StatusLevel
    ) -> None:
        """Send notifications using platform-specific mechanisms."""
        try:
            if sys.platform == "linux":
                self._send_linux_notification(title, message, status_level)
            elif sys.platform == "darwin":
                self._send_macos_notification(title, message)
            elif sys.platform == "win32":
                self._send_windows_notification(title, message)
            else:
                raise NotificationError(
                    f"Desktop notifications not supported on {sys.platform}"
                )
        except NotificationError:
            raise
        except Exception as exc:
            raise NotificationError(str(exc)) from exc

    def _fallback_to_log(self, title: str, message: str, status_level: StatusLevel):
        """
        Fallback mechanism when desktop notifications are unavailable

        Args:
            title: Notification title
            message: Notification message
            status_level: Status level
        """
        log_level_map = {
            StatusLevel.SUCCESS: logging.INFO,
            StatusLevel.WARNING: logging.WARNING,
            StatusLevel.ERROR: logging.ERROR,
            StatusLevel.CRITICAL: logging.CRITICAL,
            StatusLevel.INFO: logging.INFO,
        }

        log_level = log_level_map.get(status_level, logging.INFO)
        logger.log(log_level, f"[NOTIFICATION] {title}: {message}")

    def _send_linux_notification(
        self, title: str, message: str, status_level: StatusLevel
    ):
        """
        Send notification on Linux using notify-send

        Args:
            title: Notification title
            message: Notification message
            status_level: Status level for urgency
        """
        urgency_map = {
            StatusLevel.SUCCESS: "normal",
            StatusLevel.WARNING: "normal",
            StatusLevel.ERROR: "critical",
            StatusLevel.CRITICAL: "critical",
            StatusLevel.INFO: "low",
        }

        urgency = urgency_map.get(status_level, "normal")

        # Build command with preferences
        cmd = [
            "notify-send",
            "--urgency",
            urgency,
            "--app-name",
            "TimeLocker",
            "--expire-time",
            str(
                self.config.preferences.desktop_notification_persistence * 1000
            ),  # milliseconds
        ]

        # Try to use TimeLocker logo icon first, fallback to system icons
        logo_path = (
            Path(__file__).parent.parent.parent.parent
            / "resources"
            / "images"
            / "TimeLocker-Logo-Icon-Color-White.png"
        )
        if logo_path.exists():
            cmd.extend(["--icon", str(logo_path)])
        else:
            # Fallback to system icons based on status
            icon_map = {
                StatusLevel.SUCCESS: "dialog-information",
                StatusLevel.WARNING: "dialog-warning",
                StatusLevel.ERROR: "dialog-error",
                StatusLevel.CRITICAL: "dialog-error",
                StatusLevel.INFO: "dialog-information",
            }
            cmd.extend(["--icon", icon_map.get(status_level, "dialog-information")])

        cmd.extend([title, message])

        subprocess.run(cmd, check=True)

    def _send_macos_notification(self, title: str, message: str):
        """
        Send notification on macOS using osascript

        Args:
            title: Notification title
            message: Notification message
        """
        # Escape quotes for AppleScript
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')

        # Note: macOS notifications use the app bundle icon automatically
        # For terminal-run scripts, we can't easily set a custom icon via osascript
        # The icon would need to be set at the app bundle level or via a native app

        # Build script with sound preference
        if self.config.preferences.desktop_notification_sound:
            script = f'''display notification "{escaped_message}" with title "{escaped_title}" sound name "default"'''
        else:
            script = f'''display notification "{escaped_message}" with title "{escaped_title}"'''

        subprocess.run(["osascript", "-e", script], check=True)

    def _send_windows_notification(self, title: str, message: str):
        """Send notification on Windows using PowerShell"""
        try:
            # Escape quotes and special characters for PowerShell
            escaped_title = title.replace('"', '""').replace("'", "''")
            escaped_message = message.replace('"', '""').replace("'", "''")

            # Get logo path
            logo_path = (
                Path(__file__).parent.parent.parent.parent
                / "resources"
                / "images"
                / "TimeLocker-Logo-Icon-Color-White.png"
            )
            escaped_logo_path = str(logo_path).replace("\\", "\\\\").replace('"', '""')

            # Use a more robust PowerShell approach with proper error handling and custom icon
            script = f'''
            try {{
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                $notification = New-Object System.Windows.Forms.NotifyIcon
                
                # Try to load custom icon, fallback to system icon
                $iconPath = "{escaped_logo_path}"
                if (Test-Path $iconPath) {{
                    try {{
                        $notification.Icon = New-Object System.Drawing.Icon($iconPath)
                    }} catch {{
                        $notification.Icon = [System.Drawing.SystemIcons]::Information
                    }}
                }} else {{
                    $notification.Icon = [System.Drawing.SystemIcons]::Information
                }}
                
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

            # Run PowerShell with additional error handling
            result = subprocess.run(
                ["powershell", "-Command", script],
                check=False,  # Don't raise exception on non-zero exit
                capture_output=True,
                text=True,
                timeout=10,  # 10 second timeout
            )

            if result.returncode != 0:
                logger.warning(f"PowerShell notification failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.warning("Windows notification timed out")
        except FileNotFoundError:
            logger.warning("PowerShell not found - Windows notifications unavailable")
        except Exception as e:
            logger.warning(f"Windows notification failed: {e}")

    def _send_email_notification(
        self, title: str, message: str, status: OperationStatus
    ):
        """Send email notification"""
        if not self.config.email_enabled or not self.config.email_to:
            return

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.config.email_from or self.config.email_username
            msg["To"] = ", ".join(self.config.email_to)
            msg["Subject"] = title

            # Create HTML body
            html_body = self._create_email_html(status, message)
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            with smtplib.SMTP(
                self.config.email_smtp_server, self.config.email_smtp_port
            ) as server:
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
            StatusLevel.SUCCESS: "#28a745",
            StatusLevel.WARNING: "#ffc107",
            StatusLevel.ERROR: "#dc3545",
            StatusLevel.CRITICAL: "#dc3545",
            StatusLevel.INFO: "#17a2b8",
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
                <p><strong>Time:</strong> {status.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                {f"<p><strong>Repository:</strong> {status.repository_id}</p>" if status.repository_id else ""}
                {f"<p><strong>Progress:</strong> {status.progress_percentage}%</p>" if status.progress_percentage is not None else ""}
                {f"<p><strong>Files Processed:</strong> {status.files_processed}/{status.total_files}</p>" if status.files_processed is not None and status.total_files is not None else ""}
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
            "title": title,
            "message": message,
            "status": status.to_dict(),
        }

        notification_log = self.config_dir / "notifications.log"
        try:
            with open(notification_log, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
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
            timestamp=datetime.now(),
        )

        # Test desktop notification
        if self.config.desktop_enabled:
            try:
                title, message = self._format_notification(test_status)
                self._send_desktop_notification(title, message, test_status.status)
                results["desktop"] = True
            except Exception as e:
                logger.error(f"Desktop notification test failed: {e}")
                results["desktop"] = False

        # Test email notification
        if self.config.email_enabled:
            try:
                title, message = self._format_notification(test_status)
                self._send_email_notification(title, message, test_status)
                results["email"] = True
            except Exception as e:
                logger.error(f"Email notification test failed: {e}")
                results["email"] = False

        return results

    def notify(self, title: str, message: str, level: str = "info") -> bool:
        """
        Simple notification method for backward compatibility

        Args:
            title: Notification title
            message: Notification message
            level: Notification level (info, success, warning, error, critical)

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Map string level to StatusLevel
            level_map = {
                "info": StatusLevel.INFO,
                "success": StatusLevel.SUCCESS,
                "warning": StatusLevel.WARNING,
                "error": StatusLevel.ERROR,
                "critical": StatusLevel.CRITICAL,
            }

            status_level = level_map.get(level.lower(), StatusLevel.INFO)

            # Create a simple OperationStatus for the notification
            status = OperationStatus(
                operation_id="manual_notification",
                operation_type="notification",
                status=status_level,
                message=message,
                timestamp=datetime.now(),
            )

            self.send_notification(status)
            return True

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
