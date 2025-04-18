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
from unittest.mock import MagicMock, Mock, patch

import pytest
from packaging import version

from TimeLocker.restic.errors import ResticError
from TimeLocker.restic.restic_repository import RESTIC_MIN_VERSION, ResticRepository


def test___init___1():
    location = "/path/to/backup"
    tags = ["test", "backup"]
    password = "secure_password"

    repo = ResticRepository(location, tags=tags, password=password)

    assert repo._location == location
    assert repo._explicit_password == password
    assert repo._restic_version >= RESTIC_MIN_VERSION
    assert repo._command is not None
    assert repo._cached_env is None

def test__handle_restic_output_1():
    repo = ResticRepository(location="test_location")
    repo._on_backup_summary = Mock()

    test_output = {"message_type": "summary", "data": "test_summary_data"}
    repo._handle_restic_output(test_output)

    repo._on_backup_summary.assert_called_once_with(test_output)

def test__handle_restic_output_2():
    repo = Mock(spec=ResticRepository)

    output = {"message_type": "status", "status_data": "test_status"}

    ResticRepository._handle_restic_output(repo, output)

    repo._on_backup_status.assert_called_once_with(output)
    repo._on_backup_summary.assert_not_called()

def test__handle_restic_output_3():
    repo = ResticRepository(location="test_location")
    output = {"message_type": "other_type", "data": "test_data"}

    with patch.object(repo, '_on_backup_summary') as mock_summary, \
            patch.object(repo, '_on_backup_status') as mock_status:
        repo._handle_restic_output(output)

        mock_summary.assert_not_called()
        mock_status.assert_not_called()

def test__on_backup_status_prints_status(capsys):
    repo = ResticRepository(location="test_location")
    status = {"message_type": "status", "percent_done": 50}

    repo._on_backup_status(status)

    captured = capsys.readouterr()
    assert captured.out.strip() == f"Backup Status: {status}"

def test__on_backup_status_with_empty_dict(capsys):
    repo = ResticRepository("dummy_location")

    repo._on_backup_status({})

    captured = capsys.readouterr()
    assert captured.out.strip() == "Backup Status: {}"

def test__on_backup_summary_prints_summary(capsys):
    repo = ResticRepository(location="test_location")
    summary = {"files": 100, "dirs": 10, "size": 1024}

    repo._on_backup_summary(summary)

    captured = capsys.readouterr()
    assert captured.out.strip() == f"Backup Summary: {summary}"

def test__on_backup_summary_with_empty_dict(self, capsys):
    repo = ResticRepository("dummy_location")

    with pytest.raises(SystemExit):
        repo._on_backup_summary({})

    captured = capsys.readouterr()
    assert "Backup Summary: {}" in captured.out

def test__verify_restic_executable_2():
    mock_command = MagicMock()
    mock_command.param.return_value.run.return_value = json.dumps({"version": "0.18.1"})

    repo = ResticRepository("test_location")
    repo._command = mock_command

    result = repo._verify_restic_executable("0.18.0")

    assert result == "0.18.1"
    mock_command.param.assert_called_once_with("version")
    mock_command.param.return_value.run.assert_called_once()

def test__verify_restic_executable_not_found():
    mock_command = Mock()
    mock_command.param.return_value.run.side_effect = FileNotFoundError()

    repo = ResticRepository("test_location")
    repo._command = mock_command

    with pytest.raises(ResticError) as exc_info:
        repo._verify_restic_executable("0.18.0")

    assert "restic executable not found" in str(exc_info.value)

def test_verify_restic_executable_older_version():
    min_version = "0.10.0"
    older_version = "0.9.6"

    mock_command = Mock()
    mock_command.param.return_value.run.return_value = json.dumps({"version": older_version})

    repository = ResticRepository("test_location")
    repository._command = mock_command

    with patch("packaging.version.parse", side_effect=version.parse):
        with pytest.raises(ResticError) as exc_info:
            repository._verify_restic_executable(min_version)

    assert f"restic version {older_version} is below the required minimum version {min_version}" in str(exc_info.value)

def test__verify_restic_executable_version_below_minimum():
    mock_command = Mock()
    mock_command.param.return_value.run.return_value = json.dumps({"version": "0.9.0"})

    repo = ResticRepository("test_location")
    repo._command = mock_command

    with pytest.raises(ResticError) as exc_info:
        repo._verify_restic_executable("0.10.0")

    assert "restic version 0.9.0 is below the required minimum version 0.10.0" in str(exc_info.value)
