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

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from TimeLocker.file_selections import FileSelection


# from file_selections import FileSelection

@pytest.fixture(autouse=True)
def mock_desktop_notifications(request):
    """Automatically mock desktop notifications to prevent popup alerts during tests"""
    # Skip mocking for notification service tests that specifically test desktop notifications
    if 'test_notification_service.py' in str(request.fspath) and any(
            test_name in request.node.name for test_name in [
                    'test_send_linux_notification',
                    'test_send_macos_notification',
                    'test_send_windows_notification'
            ]
    ):
        yield None
    else:
        with patch('TimeLocker.monitoring.notification_service.NotificationService._send_desktop_notification') as mock_desktop:
            # Make desktop notifications do nothing during tests
            mock_desktop.return_value = None
            yield mock_desktop


@pytest.fixture
def selection():
    return FileSelection()


@pytest.fixture
def test_dir():
    test_dir = Mock(spec=Path)
    test_dir.is_dir.return_value = True
    test_dir.__str__ = lambda x: "/test/dir"
    return test_dir


@pytest.fixture
def test_file():
    test_file = Mock(spec=Path)
    test_file.is_dir.return_value = False
    test_file.__str__ = lambda x: "/test/file.txt"
    return test_file
