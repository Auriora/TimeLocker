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
from datetime import datetime
from unittest.mock import Mock, patch

from TimeLocker.monitoring import (
    SystemTrayIntegration,
    TrayStatus,
    TrayStatusInfo,
    SystemTrayError
)
from TimeLocker.monitoring.system_tray_integration import (
    LinuxSystemTray,
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
            last_backup_time=datetime.now(),
            last_backup_status="success",
            repository_count=3,
            active_operations=0
        )

        assert info.status == TrayStatus.SUCCESS
        assert info.repository_count == 3
        assert info.active_operations == 0


class TestSystemTrayIntegration:
    """Test suite for SystemTrayIntegration"""

    @pytest.mark.monitoring
    @pytest.mark.unit
    @patch('TimeLocker.monitoring.system_tray_integration.sys.platform', 'linux')
    def test_initialization(self):
        """Test SystemTrayIntegration initialization"""
        with patch('TimeLocker.monitoring.system_tray_integration.LinuxSystemTray'):
            tray = SystemTrayIntegration(app_name="TestApp")
            
            assert tray.app_name == "TestApp"
            assert tray.current_status == TrayStatus.IDLE

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_tray_status_enum(self):
        """Test TrayStatus enum values"""
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

        with patch.dict('sys.modules', {'gi': gi}):
            with patch(
                'TimeLocker.monitoring.system_tray_integration.importlib.import_module',
                side_effect=[gtk, ayatana],
            ):
                modules = _load_linux_tray_modules()

        assert modules == (gtk, ayatana, 'AyatanaAppIndicator3')
        gi.require_version.assert_any_call('AyatanaAppIndicator3', '0.1')

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_falls_back_to_legacy_appindicator(self):
        gi = Mock()
        gtk = Mock()
        legacy = Mock()

        def require_version(namespace, version):
            if namespace == 'AyatanaAppIndicator3':
                raise ValueError('namespace unavailable')

        gi.require_version.side_effect = require_version
        with patch.dict('sys.modules', {'gi': gi}):
            with patch(
                'TimeLocker.monitoring.system_tray_integration.importlib.import_module',
                side_effect=[gtk, legacy],
            ):
                modules = _load_linux_tray_modules()

        assert modules == (gtk, legacy, 'AppIndicator3')
        gi.require_version.assert_any_call('AppIndicator3', '0.1')

    @pytest.mark.monitoring
    @pytest.mark.unit
    def test_missing_indicator_namespaces_is_non_fatal_to_facade(self):
        with patch(
            'TimeLocker.monitoring.system_tray_integration._load_linux_tray_modules',
            side_effect=SystemTrayError('no indicator'),
        ):
            tray = SystemTrayIntegration('TestApp')

        assert tray.is_available() is False
