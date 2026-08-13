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
import importlib
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PACKAGED_TRAY_ICON_PATH = (
    Path(__file__).resolve().parents[1]
    / "system_control"
    / "assets"
    / "timelocker-icon.png"
)


def _linux_graphical_session_available() -> bool:
    """Return whether a Linux process has a desktop display connection."""
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _load_linux_tray_modules():
    """Load GTK and the first supported AppIndicator namespace."""
    try:
        import gi
    except ImportError as exc:
        raise SystemTrayError("PyGObject is not installed") from exc

    try:
        gi.require_version("Gtk", "3.0")
        gtk = importlib.import_module("gi.repository.Gtk")
    except (ImportError, ValueError) as exc:
        raise SystemTrayError("GTK 3 is not available") from exc

    errors = []
    for namespace in ("AyatanaAppIndicator3", "AppIndicator3"):
        try:
            gi.require_version(namespace, "0.1")
            indicator = importlib.import_module(f"gi.repository.{namespace}")
            return gtk, indicator, namespace
        except (ImportError, ValueError) as exc:
            errors.append(f"{namespace}: {exc}")

    raise SystemTrayError(
        "Neither AyatanaAppIndicator3 nor AppIndicator3 is available ("
        + "; ".join(errors)
        + ")"
    )


class SystemTrayError(Exception):
    """Base exception for system tray errors"""

    pass


class TrayStatus(Enum):
    """System tray status indicators"""

    CONNECTING = "connecting"
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


PACKAGED_TRAY_STATUS_ICON_PATHS = {
    status: PACKAGED_TRAY_ICON_PATH.with_name(
        f"timelocker-icon-{status.value}.png"
    )
    for status in TrayStatus
}


def _linux_tray_icon_path(status: TrayStatus) -> str:
    """Return the packaged status icon, then the base logo, then a theme icon."""
    status_path = PACKAGED_TRAY_STATUS_ICON_PATHS[status]
    if status_path.is_file():
        return str(status_path)
    if PACKAGED_TRAY_ICON_PATH.is_file():
        return str(PACKAGED_TRAY_ICON_PATH)
    return "dialog-information"


@dataclass
class TrayStatusInfo:
    """Information displayed in system tray"""

    status: TrayStatus
    tooltip: str
    health: str = "Unknown"
    activity: str = "Connecting"
    backend_available: bool = False
    last_successful_backup_time: Optional[datetime] = None
    latest_backup_status: Optional[str] = None
    latest_retention_status: Optional[str] = None
    next_backup_time: Optional[datetime] = None
    next_retention_time: Optional[datetime] = None
    active_operations: int = 0


def _format_local_time(value: datetime | None, *, missing: str) -> str:
    if value is None:
        return missing
    return value.astimezone().strftime("%Y-%m-%d %H:%M %Z").rstrip()


def _status_menu_labels(status_info: TrayStatusInfo) -> tuple[str, ...]:
    """Return platform-neutral, non-actionable status menu labels."""
    return (
        f"State: {status_info.health}",
        f"Activity: {status_info.activity}",
        "Last Backup: "
        + _format_local_time(
            status_info.last_successful_backup_time,
            missing="Never",
        ),
    )


class SystemTrayIntegration:
    """
    System tray integration for TimeLocker
    Provides always-visible status information and quick actions

    Features:
    - Application icon with status details
    - Tooltip with last backup status
    - Context menu with quick actions
    """

    def __init__(
        self,
        app_name: str = "TimeLocker",
        menu_actions: set[str] | frozenset[str] | None = None,
    ):
        """
        Initialize system tray integration

        Args:
            app_name: Application name for tray icon
        """
        self.app_name = app_name
        self.menu_actions = frozenset(
            menu_actions
            if menu_actions is not None
            else {"backup_now", "retention_now", "quit"}
        )
        self.current_status = TrayStatus.CONNECTING
        self.status_info = TrayStatusInfo(
            status=TrayStatus.CONNECTING,
            tooltip="TimeLocker - Connecting",
        )

        # Platform-specific implementation
        self._tray_impl: Optional[Any] = None
        self._initialized = False
        self._lock = threading.Lock()

        # Callbacks
        self._on_click_callback: Optional[Callable] = None
        self._on_menu_action_callback: Optional[Callable[[str], None]] = None

        # Initialize platform-specific tray
        self._initialize_platform_tray()

    def _initialize_platform_tray(self):
        """Initialize platform-specific system tray implementation"""
        try:
            if sys.platform == "linux":
                if not _linux_graphical_session_available():
                    logger.info(
                        "System tray disabled because no Linux graphical session is available"
                    )
                    return
                self._tray_impl = LinuxSystemTray(self.app_name, self.menu_actions)
            elif sys.platform == "darwin":
                self._tray_impl = MacOSSystemTray(self.app_name, self.menu_actions)
            elif sys.platform == "win32":
                self._tray_impl = WindowsSystemTray(self.app_name, self.menu_actions)
            else:
                logger.warning(f"System tray not supported on {sys.platform}")
                return

            self._initialized = True
            logger.info(f"System tray initialized for {sys.platform}")

        except Exception as e:
            logger.warning(f"Failed to initialize system tray: {e}")
            self._initialized = False

    def is_available(self) -> bool:
        """
        Check if system tray is available

        Returns:
            bool: True if system tray is available
        """
        return self._initialized and self._tray_impl is not None

    def update_status(self, status: TrayStatus, tooltip: Optional[str] = None):
        """
        Update system tray status

        Args:
            status: New status
            tooltip: Optional tooltip text
        """
        if not self.is_available():
            logger.debug("System tray not available, skipping status update")
            return

        with self._lock:
            self.current_status = status
            self.status_info.status = status

            if tooltip:
                self.status_info.tooltip = tooltip

            try:
                self._tray_impl.update_icon(status)
                self._tray_impl.update_tooltip(self.status_info.tooltip)
            except Exception as e:
                logger.error(f"Failed to update system tray status: {e}")

    def update_status_info(self, status_info: TrayStatusInfo):
        """
        Update complete status information

        Args:
            status_info: Complete status information
        """
        if not self.is_available():
            return

        with self._lock:
            self.status_info = status_info
            self.current_status = status_info.status

            try:
                self._tray_impl.update_icon(status_info.status)
                self._tray_impl.update_tooltip(self._format_tooltip(status_info))
                update_rows = getattr(self._tray_impl, "update_status_rows", None)
                if update_rows is not None:
                    update_rows(status_info)
            except Exception as e:
                logger.error(f"Failed to update system tray info: {e}")

    def _format_tooltip(self, status_info: TrayStatusInfo) -> str:
        """
        Format tooltip text from status info

        Args:
            status_info: Status information

        Returns:
            str: Formatted tooltip text
        """
        lines = [f"{self.app_name} - {status_info.status.value.title()}"]
        lines.extend(_status_menu_labels(status_info))
        return "\n".join(lines)

    def set_on_click_callback(self, callback: Callable):
        """
        Set callback for tray icon click

        Args:
            callback: Function to call when icon is clicked
        """
        self._on_click_callback = callback
        if self.is_available():
            self._tray_impl.set_on_click(callback)

    def update_last_backup_time(self, backup_time: datetime | None) -> None:
        """Compatibility helper for callers not yet using complete status info."""
        if not self.is_available():
            return

        self.status_info.last_successful_backup_time = backup_time
        update_rows = getattr(self._tray_impl, "update_status_rows", None)
        if update_rows is not None:
            update_rows(self.status_info)

    def set_on_menu_action_callback(self, callback: Callable[[str], None]):
        """
        Set callback for menu actions

        Args:
            callback: Function to call with action name
        """
        self._on_menu_action_callback = callback
        if self.is_available():
            self._tray_impl.set_on_menu_action(callback)

    def show_context_menu(self):
        """Show context menu with quick actions"""
        if not self.is_available():
            return

        try:
            self._tray_impl.show_menu()
        except Exception as e:
            logger.error(f"Failed to show context menu: {e}")

    def process_events(self) -> None:
        """Process pending platform UI events without blocking the tray client."""
        if not self.is_available():
            return
        process_events = getattr(self._tray_impl, "process_events", None)
        if process_events is not None:
            process_events()

    def shutdown(self):
        """Shutdown system tray integration"""
        if self.is_available():
            try:
                self._tray_impl.shutdown()
                self._initialized = False
                logger.info("System tray shutdown completed")
            except Exception as e:
                logger.error(f"Error during system tray shutdown: {e}")


class LinuxSystemTray:
    """Linux system tray implementation using GTK or Qt"""

    def __init__(
        self,
        app_name: str,
        menu_actions: frozenset[str] | None = None,
    ):
        """
        Initialize Linux system tray

        Args:
            app_name: Application name
        """
        self.app_name = app_name
        self.menu_actions = (
            menu_actions
            if menu_actions is not None
            else frozenset({"backup_now", "retention_now", "quit"})
        )
        self._icon = None
        self._menu = None
        self._on_click_callback = None
        self._on_menu_action_callback = None

        # Try to initialize with available toolkit
        self._initialize_tray()

    def _initialize_tray(self):
        """Initialize tray with available toolkit"""
        try:
            self._gtk, self._indicator_module, self._indicator_namespace = (
                _load_linux_tray_modules()
            )
            self._use_gtk = True
            self._indicator = self._indicator_module.Indicator.new(
                self.app_name,
                _linux_tray_icon_path(TrayStatus.CONNECTING),
                self._indicator_module.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(self._indicator_module.IndicatorStatus.ACTIVE)
            self._create_gtk_menu()
            logger.info(
                "Using GTK with %s for Linux system tray", self._indicator_namespace
            )
            return
        except SystemTrayError as e:
            logger.debug(f"GTK AppIndicator not available: {e}")

        # Fallback: log that tray is not available
        logger.warning("No suitable system tray toolkit found for Linux")
        raise SystemTrayError("System tray not available on this Linux system")

    def _create_gtk_menu(self):
        """Create GTK context menu"""
        try:
            Gtk = self._gtk
            self._menu = Gtk.Menu()

            # AppIndicator tooltips are not consistently available on Linux.
            self._status_items = []
            initial_status = TrayStatusInfo(
                status=TrayStatus.CONNECTING,
                tooltip="TimeLocker - Connecting",
            )
            for label in _status_menu_labels(initial_status):
                item = Gtk.MenuItem(label=label)
                item.set_sensitive(False)
                self._menu.append(item)
                self._status_items.append(item)

            # Backup now item
            backup_item = Gtk.MenuItem(label="Backup Now")
            backup_item.connect(
                "activate", lambda x: self._trigger_menu_action("backup_now")
            )
            self._menu.append(backup_item)

            # Retention now item
            if "retention_now" in self.menu_actions:
                retention_item = Gtk.MenuItem(label="Run Retention")
                retention_item.connect(
                    "activate", lambda x: self._trigger_menu_action("retention_now")
                )
                self._menu.append(retention_item)

            # Separator
            self._menu.append(Gtk.SeparatorMenuItem())

            # Quit item
            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", lambda x: self._trigger_menu_action("quit"))
            self._menu.append(quit_item)

            self._menu.show_all()
            self._indicator.set_menu(self._menu)

        except Exception as e:
            logger.error(f"Failed to create GTK menu: {e}")

    def _on_open_clicked(self, widget):
        """Handle open menu item click"""
        if self._on_click_callback:
            self._on_click_callback()

    def _trigger_menu_action(self, action: str):
        """Trigger menu action callback"""
        if self._on_menu_action_callback:
            self._on_menu_action_callback(action)

    def update_icon(self, status: TrayStatus):
        """Update tray icon based on status"""
        if not hasattr(self, "_indicator"):
            return

        try:
            self._indicator.set_icon(_linux_tray_icon_path(status))
        except Exception as e:
            logger.error(f"Failed to update icon: {e}")

    def update_tooltip(self, tooltip: str):
        """Update tooltip text"""
        # GTK AppIndicator doesn't support tooltips directly
        # Tooltip is shown through the menu
        pass

    def update_status_rows(self, status_info: TrayStatusInfo) -> None:
        """Refresh non-actionable Linux menu rows from one coherent snapshot."""
        if not hasattr(self, "_status_items"):
            return

        try:
            for item, label in zip(
                self._status_items,
                _status_menu_labels(status_info),
                strict=True,
            ):
                item.set_label(label)
        except Exception as e:
            logger.error(f"Failed to update tray status rows: {e}")

    def set_on_click(self, callback: Callable):
        """Set click callback"""
        self._on_click_callback = callback

    def set_on_menu_action(self, callback: Callable[[str], None]):
        """Set menu action callback"""
        self._on_menu_action_callback = callback

    def show_menu(self):
        """Show context menu"""
        # Menu is always visible in GTK AppIndicator
        pass

    def process_events(self) -> None:
        """Drain pending GTK events while IPC polling remains independent."""
        while self._gtk.events_pending():
            self._gtk.main_iteration_do(False)

    def shutdown(self):
        """Shutdown tray"""
        if hasattr(self, "_indicator"):
            try:
                self._indicator.set_status(
                    self._indicator_module.IndicatorStatus.PASSIVE
                )
            except Exception as e:
                logger.error(f"Failed to shutdown GTK tray: {e}")


class MacOSSystemTray:
    """macOS system tray implementation using rumps"""

    def __init__(
        self,
        app_name: str,
        menu_actions: frozenset[str] | None = None,
    ):
        """
        Initialize macOS system tray

        Args:
            app_name: Application name
        """
        self.app_name = app_name
        self.menu_actions = (
            menu_actions
            if menu_actions is not None
            else frozenset({"backup_now", "retention_now", "quit"})
        )
        self._app = None
        self._on_click_callback = None
        self._on_menu_action_callback = None

        # Try to initialize with rumps
        try:
            import rumps

            self._app = rumps.App(app_name, "…")
            self._create_menu()
            logger.info("Using rumps for macOS system tray")
        except ImportError:
            logger.warning("rumps not available for macOS system tray")
            raise SystemTrayError(
                "System tray not available on macOS (rumps not installed)"
            )

    def _create_menu(self):
        """Create macOS menu"""
        if not self._app:
            return

        try:
            import rumps

            self._status_items = [
                rumps.MenuItem(label)
                for label in _status_menu_labels(
                    TrayStatusInfo(
                        status=TrayStatus.CONNECTING,
                        tooltip="TimeLocker - Connecting",
                    )
                )
            ]
            menu = [
                *self._status_items,
                rumps.MenuItem(
                    "Backup Now",
                    callback=lambda _: self._trigger_menu_action("backup_now"),
                ),
            ]
            if "retention_now" in self.menu_actions:
                menu.append(
                    rumps.MenuItem(
                        "Run Retention",
                        callback=lambda _: self._trigger_menu_action("retention_now"),
                    )
                )
            menu.extend(
                [
                    None,
                    rumps.MenuItem(
                        "Quit", callback=lambda _: self._trigger_menu_action("quit")
                    ),
                ]
            )
            self._app.menu = menu
        except Exception as e:
            logger.error(f"Failed to create macOS menu: {e}")

    def update_status_rows(self, status_info: TrayStatusInfo) -> None:
        """Refresh non-actionable macOS menu rows."""
        if not hasattr(self, "_status_items"):
            return
        for item, label in zip(
            self._status_items,
            _status_menu_labels(status_info),
            strict=True,
        ):
            item.title = label

    def _on_open_clicked(self, sender):
        """Handle open menu item click"""
        if self._on_click_callback:
            self._on_click_callback()

    def _trigger_menu_action(self, action: str):
        """Trigger menu action callback"""
        if self._on_menu_action_callback:
            self._on_menu_action_callback(action)

    def update_icon(self, status: TrayStatus):
        """Update tray icon based on status"""
        if not self._app:
            return

        icon_map = {
            TrayStatus.CONNECTING: "…",
            TrayStatus.IDLE: "⏰",
            TrayStatus.RUNNING: "🔄",
            TrayStatus.SUCCESS: "✅",
            TrayStatus.WARNING: "⚠️",
            TrayStatus.ERROR: "❌",
        }

        icon = icon_map.get(status, "⏰")
        try:
            self._app.icon = icon
        except Exception as e:
            logger.error(f"Failed to update icon: {e}")

    def update_tooltip(self, tooltip: str):
        """Update tooltip text"""
        if not self._app:
            return

        try:
            self._app.title = tooltip
        except Exception as e:
            logger.error(f"Failed to update tooltip: {e}")

    def set_on_click(self, callback: Callable):
        """Set click callback"""
        self._on_click_callback = callback

    def set_on_menu_action(self, callback: Callable[[str], None]):
        """Set menu action callback"""
        self._on_menu_action_callback = callback

    def show_menu(self):
        """Show context menu"""
        # Menu is always visible in macOS
        pass

    def shutdown(self):
        """Shutdown tray"""
        if self._app:
            try:
                self._app.quit_button = None
            except Exception as e:
                logger.error(f"Failed to shutdown macOS tray: {e}")


class WindowsSystemTray:
    """Windows system tray implementation using pystray"""

    def __init__(
        self,
        app_name: str,
        menu_actions: frozenset[str] | None = None,
    ):
        """
        Initialize Windows system tray

        Args:
            app_name: Application name
        """
        self.app_name = app_name
        self.menu_actions = (
            menu_actions
            if menu_actions is not None
            else frozenset({"backup_now", "retention_now", "quit"})
        )
        self._icon = None
        self._on_click_callback = None
        self._on_menu_action_callback = None

        # Try to initialize with pystray
        try:
            import pystray

            # Create a simple icon
            image = self._create_icon_image()

            # Create menu
            menu = self._create_menu()

            self._icon = pystray.Icon(app_name, image, app_name, menu)

            # Start icon in background thread
            threading.Thread(target=self._icon.run, daemon=True).start()

            logger.info("Using pystray for Windows system tray")
        except ImportError:
            logger.warning("pystray not available for Windows system tray")
            raise SystemTrayError(
                "System tray not available on Windows (pystray not installed)"
            )

    def _create_icon_image(self):
        """Create icon image"""
        try:
            from PIL import Image, ImageDraw

            # Create a simple 64x64 icon
            image = Image.new("RGB", (64, 64), color="white")
            draw = ImageDraw.Draw(image)
            draw.ellipse([16, 16, 48, 48], fill="blue")
            return image
        except Exception as e:
            logger.error(f"Failed to create icon image: {e}")
            return None

    def _create_menu(self):
        """Create Windows menu"""
        try:
            import pystray
            from pystray import MenuItem as Item

            status_info = getattr(
                self,
                "_status_info",
                TrayStatusInfo(
                    status=TrayStatus.CONNECTING,
                    tooltip="TimeLocker - Connecting",
                ),
            )
            items = [
                Item(label, None, enabled=False)
                for label in _status_menu_labels(status_info)
            ]
            items.append(
                Item("Backup Now", lambda: self._trigger_menu_action("backup_now"))
            )
            if "retention_now" in self.menu_actions:
                items.append(
                    Item(
                        "Run Retention",
                        lambda: self._trigger_menu_action("retention_now"),
                    )
                )
            items.append(Item("Quit", lambda: self._trigger_menu_action("quit")))
            return pystray.Menu(*items)
        except Exception as e:
            logger.error(f"Failed to create Windows menu: {e}")
            return None

    def update_status_rows(self, status_info: TrayStatusInfo) -> None:
        """Refresh non-actionable Windows menu rows."""
        self._status_info = status_info
        if self._icon is not None:
            self._icon.menu = self._create_menu()

    def _on_open_clicked(self, icon, item):
        """Handle open menu item click"""
        if self._on_click_callback:
            self._on_click_callback()

    def _trigger_menu_action(self, action: str):
        """Trigger menu action callback"""
        if self._on_menu_action_callback:
            self._on_menu_action_callback(action)

    def update_icon(self, status: TrayStatus):
        """Update tray icon based on status"""
        if not self._icon:
            return

        # Update icon image based on status
        try:
            image = self._create_status_icon(status)
            if image:
                self._icon.icon = image
        except Exception as e:
            logger.error(f"Failed to update icon: {e}")

    def _create_status_icon(self, status: TrayStatus):
        """Create status-specific icon"""
        try:
            from PIL import Image, ImageDraw

            color_map = {
                TrayStatus.CONNECTING: "deepskyblue",
                TrayStatus.IDLE: "gray",
                TrayStatus.RUNNING: "blue",
                TrayStatus.SUCCESS: "green",
                TrayStatus.WARNING: "orange",
                TrayStatus.ERROR: "red",
            }

            color = color_map.get(status, "gray")
            image = Image.new("RGB", (64, 64), color="white")
            draw = ImageDraw.Draw(image)
            draw.ellipse([16, 16, 48, 48], fill=color)
            return image
        except Exception as e:
            logger.error(f"Failed to create status icon: {e}")
            return None

    def update_tooltip(self, tooltip: str):
        """Update tooltip text"""
        if not self._icon:
            return

        try:
            self._icon.title = tooltip
        except Exception as e:
            logger.error(f"Failed to update tooltip: {e}")

    def set_on_click(self, callback: Callable):
        """Set click callback"""
        self._on_click_callback = callback

    def set_on_menu_action(self, callback: Callable[[str], None]):
        """Set menu action callback"""
        self._on_menu_action_callback = callback

    def show_menu(self):
        """Show context menu"""
        # Menu is shown on right-click in Windows
        pass

    def shutdown(self):
        """Shutdown tray"""
        if self._icon:
            try:
                self._icon.stop()
            except Exception as e:
                logger.error(f"Failed to shutdown Windows tray: {e}")
