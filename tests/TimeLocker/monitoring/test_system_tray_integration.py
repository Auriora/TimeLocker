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
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from TimeLocker.monitoring.system_tray_integration import (
    PACKAGED_TRAY_ICON_PATH,
    PACKAGED_TRAY_STATUS_ICON_PATHS,
    LinuxSystemTray,
    SystemTrayError,
    SystemTrayIntegration,
    TrayStatus,
    TrayStatusInfo,
    _linux_tray_icon_path,
    _load_linux_tray_modules,
)


class TestTrayStatusInfo:
    """Test suite for TrayStatusInfo dataclass"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_tray_status_info_creation(self):
        """Test creating a TrayStatusInfo instance"""
        info = TrayStatusInfo(
            status=TrayStatus.SUCCESS,
            tooltip="Last backup: 2 hours ago",
            backend_available=True,
            last_successful_backup_time=datetime.now(),
            latest_backup_status="success",
            active_operations=0,
        )

        assert info.status == TrayStatus.SUCCESS
        assert info.backend_available is True
        assert info.active_operations == 0


class TestSystemTrayIntegration:
    """Test suite for SystemTrayIntegration"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    @patch("TimeLocker.monitoring.system_tray_integration.sys.platform", "linux")
    def test_initialization(self, monkeypatch):
        """Test SystemTrayIntegration initialization"""
        monkeypatch.setenv("DISPLAY", ":0")
        with patch(
            "TimeLocker.monitoring.system_tray_integration.LinuxSystemTray"
        ) as linux_tray:
            tray = SystemTrayIntegration(app_name="TestApp")

            assert tray.app_name == "TestApp"
            assert tray.current_status == TrayStatus.CONNECTING
            assert tray.is_available() is True
            linux_tray.assert_called_once_with(
                "TestApp",
                frozenset(
                    {
                        "backup_now",
                        "retention_now",
                        "quit",
                    }
                ),
            )

    @pytest.mark.monitoring
    @pytest.mark.unit
    @patch("TimeLocker.monitoring.system_tray_integration.sys.platform", "linux")
    def test_headless_linux_skips_native_tray_initialization(self, monkeypatch):
        """A service without a display must not enter GTK/AppIndicator code."""
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        with patch(
            "TimeLocker.monitoring.system_tray_integration.LinuxSystemTray"
        ) as linux_tray:
            tray = SystemTrayIntegration(app_name="HeadlessService")

        assert tray.is_available() is False
        linux_tray.assert_not_called()

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_tray_status_enum(self):
        """Test TrayStatus enum values"""
        assert TrayStatus.CONNECTING.value == "connecting"
        assert TrayStatus.IDLE.value == "idle"
        assert TrayStatus.RUNNING.value == "running"
        assert TrayStatus.SUCCESS.value == "success"
        assert TrayStatus.WARNING.value == "warning"
        assert TrayStatus.ERROR.value == "error"


class TestLinuxSystemTray:
    """Linux namespace selection and non-fatal availability behavior."""

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_prefers_ayatana_appindicator(self):
        gi = Mock()
        gtk = Mock()
        ayatana = Mock()

        with patch.dict("sys.modules", {"gi": gi}):
            with patch(
                "TimeLocker.monitoring.system_tray_integration.importlib.import_module",
                side_effect=[gtk, ayatana],
            ):
                modules = _load_linux_tray_modules()

        assert modules == (gtk, ayatana, "AyatanaAppIndicator3")
        gi.require_version.assert_any_call("AyatanaAppIndicator3", "0.1")

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_falls_back_to_legacy_appindicator(self):
        gi = Mock()
        gtk = Mock()
        legacy = Mock()

        def require_version(namespace, version):
            if namespace == "AyatanaAppIndicator3":
                raise ValueError("namespace unavailable")

        gi.require_version.side_effect = require_version
        with patch.dict("sys.modules", {"gi": gi}):
            with patch(
                "TimeLocker.monitoring.system_tray_integration.importlib.import_module",
                side_effect=[gtk, legacy],
            ):
                modules = _load_linux_tray_modules()

        assert modules == (gtk, legacy, "AppIndicator3")
        gi.require_version.assert_any_call("AppIndicator3", "0.1")

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_uses_packaged_status_icons_for_initial_and_updated_status(self):
        gtk = Mock()
        indicator_module = Mock()
        indicator = indicator_module.Indicator.new.return_value

        with patch(
            "TimeLocker.monitoring.system_tray_integration._load_linux_tray_modules",
            return_value=(gtk, indicator_module, "AyatanaAppIndicator3"),
        ):
            tray = LinuxSystemTray("TimeLocker")
            tray.update_icon(TrayStatus.ERROR)

        indicator_module.Indicator.new.assert_called_once_with(
            "TimeLocker",
            str(PACKAGED_TRAY_STATUS_ICON_PATHS[TrayStatus.CONNECTING]),
            indicator_module.IndicatorCategory.APPLICATION_STATUS,
        )
        indicator.set_icon.assert_called_once_with(
            str(PACKAGED_TRAY_STATUS_ICON_PATHS[TrayStatus.ERROR])
        )

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_status_icon_falls_back_to_base_logo(self):
        with patch.object(
            type(PACKAGED_TRAY_ICON_PATH),
            "is_file",
            side_effect=(False, True),
        ):
            icon = _linux_tray_icon_path(TrayStatus.ERROR)

        assert icon == str(PACKAGED_TRAY_ICON_PATH)

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_linux_menu_shows_last_backup_in_local_time(self):
        gtk = Mock()
        indicator_module = Mock()
        status_items = [Mock() for _ in range(3)]
        backup_item = Mock()
        quit_item = Mock()
        gtk.MenuItem.side_effect = [
            *status_items,
            backup_item,
            quit_item,
        ]

        with patch(
            "TimeLocker.monitoring.system_tray_integration._load_linux_tray_modules",
            return_value=(gtk, indicator_module, "AyatanaAppIndicator3"),
        ):
            backup_time = datetime(2026, 7, 26, 12, 34, tzinfo=UTC)
            tray = LinuxSystemTray(
                "TimeLocker",
                frozenset({"backup_now", "quit"}),
            )
            tray.update_status_rows(
                TrayStatusInfo(
                    status=TrayStatus.SUCCESS,
                    tooltip="TimeLocker",
                    health="Healthy",
                    activity="Idle",
                    backend_available=True,
                    last_successful_backup_time=backup_time,
                    latest_backup_status="Backup completed successfully.",
                )
            )

        assert all(
            call.kwargs.get("label") not in {"Open TimeLocker", "View Status"}
            for call in gtk.MenuItem.call_args_list
        )
        for status_item in status_items:
            status_item.set_sensitive.assert_called_once_with(False)
        expected_time = backup_time.astimezone().strftime("%Y-%m-%d %H:%M %Z")
        status_items[2].set_label.assert_called_once_with(
            f"Last Backup: {expected_time}".rstrip()
        )

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_missing_indicator_namespaces_is_non_fatal_to_facade(self):
        with patch(
            "TimeLocker.monitoring.system_tray_integration._load_linux_tray_modules",
            side_effect=SystemTrayError("no indicator"),
        ):
            tray = SystemTrayIntegration("TestApp")

        assert tray.is_available() is False
