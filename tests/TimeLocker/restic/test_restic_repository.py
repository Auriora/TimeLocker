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
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from packaging import version

from TimeLocker.restic.errors import ResticError
from TimeLocker.restic.restic_repository import RESTIC_MIN_VERSION, ResticRepository


class ConcreteResticRepository(ResticRepository):
    """Concrete implementation of ResticRepository for testing"""

    def backend_env(self):
        return {"TEST_ENV": "test_value"}

    def validate(self):
        # Override validate to prevent actual validation during testing
        pass

    def _verify_restic_executable(self, min_version: str) -> str:
        # Override to prevent actual restic executable verification during testing
        return "0.18.0"


@pytest.mark.unit
@pytest.mark.parametrize("overwrite", ["never", "always"])
def test_restore_passes_explicit_overwrite_policy(overwrite):
    repo = ConcreteResticRepository("test_location")
    command = MagicMock()
    command.param.return_value = command
    repo._command = MagicMock()
    repo._command.command.return_value = command
    command.run.return_value = "restore complete"

    result = repo.restore("snapshot-1", overwrite=overwrite)

    assert result == "restore complete"
    command.param.assert_any_call("target", None)
    command.param.assert_any_call("overwrite", overwrite)
    command.run.assert_called_once_with(
        repo.to_env(),
        synopsis_values={"snapshotID": "snapshot-1"},
    )


@pytest.mark.unit
def test_restore_rejects_unknown_overwrite_policy():
    repo = ConcreteResticRepository("test_location")

    with pytest.raises(ValueError, match="overwrite must be"):
        repo.restore("snapshot-1", overwrite="if-newer")


@pytest.mark.unit
def test_restore_passes_include_and_exclude_paths():
    repo = ConcreteResticRepository("test_location")
    command = MagicMock()
    command.param.return_value = command
    repo._command = MagicMock()
    repo._command.command.return_value = command
    command.run.return_value = "restore complete"

    repo.restore(
        "snapshot-1",
        include_paths=[Path("/etc/hostname")],
        exclude_paths=[Path("/etc/shadow")],
    )

    command.param.assert_any_call("include", Path("/etc/hostname"))
    command.param.assert_any_call("exclude", Path("/etc/shadow"))


@pytest.mark.unit
def test___init___1():
    location = "/path/to/backup"
    tags = ["test", "backup"]
    password = "secure_password"

    repo = ConcreteResticRepository(location, tags=tags, password=password)

    assert repo._location == location
    assert repo._explicit_password == password
    assert repo._restic_version >= RESTIC_MIN_VERSION
    assert repo._command is not None
    assert repo._cached_env is None

@pytest.mark.unit
def test__handle_restic_output_1():
    repo = ConcreteResticRepository(location="test_location")
    repo._on_backup_summary = Mock()

    test_output = {"message_type": "summary", "data": "test_summary_data"}
    repo._handle_restic_output(test_output)

    repo._on_backup_summary.assert_called_once_with(test_output)

@pytest.mark.unit
def test__handle_restic_output_2():
    repo = Mock(spec=ResticRepository)

    output = {"message_type": "status", "status_data": "test_status"}

    ResticRepository._handle_restic_output(repo, output)

    repo._on_backup_status.assert_called_once_with(output)
    repo._on_backup_summary.assert_not_called()

@pytest.mark.unit
def test__handle_restic_output_3():
    repo = ConcreteResticRepository(location="test_location")
    output = {"message_type": "other_type", "data": "test_data"}

    with patch.object(repo, '_on_backup_summary') as mock_summary, \
            patch.object(repo, '_on_backup_status') as mock_status:
        repo._handle_restic_output(output)

        mock_summary.assert_not_called()
        mock_status.assert_not_called()

@pytest.mark.unit
def test__on_backup_status_prints_status(capsys):
    repo = ConcreteResticRepository(location="test_location")
    status = {"message_type": "status", "percent_done": 50}

    repo._on_backup_status(status)

    captured = capsys.readouterr()
    assert captured.out.strip() == f"Backup Status: {status}"

@pytest.mark.unit
def test__on_backup_status_with_empty_dict(capsys):
    repo = ConcreteResticRepository("dummy_location")

    repo._on_backup_status({})

    captured = capsys.readouterr()
    assert captured.out.strip() == "Backup Status: {}"

@pytest.mark.unit
def test__on_backup_summary_prints_summary(capsys):
    repo = ConcreteResticRepository(location="test_location")
    summary = {"files": 100, "dirs": 10, "size": 1024}

    repo._on_backup_summary(summary)

    captured = capsys.readouterr()
    assert captured.out.strip() == f"Backup Summary: {summary}"

@pytest.mark.unit
def test__on_backup_summary_with_empty_dict(capsys):
    repo = ConcreteResticRepository("dummy_location")

    repo._on_backup_summary({})

    captured = capsys.readouterr()
    assert "Backup Summary: {}" in captured.out

@pytest.mark.unit
def test__verify_restic_executable_2():
    with patch('TimeLocker.restic.restic_repository.CommandBuilder') as mock_builder:
        # Create a mock command builder instance
        mock_instance = MagicMock()
        mock_instance.param.return_value = mock_instance
        mock_instance.command.return_value = mock_instance
        mock_instance.run.return_value = json.dumps({"version": "0.18.1"})
        mock_builder.return_value = mock_instance

        repo = ConcreteResticRepository("test_location")
        # Call the parent class method directly to test the actual implementation
        result = ResticRepository._verify_restic_executable(repo, "0.18.0")

        assert result == "0.18.1"

@pytest.mark.unit
def test__verify_restic_executable_not_found():
    with patch('TimeLocker.restic.restic_repository.CommandBuilder') as mock_builder:
        # Create a mock command builder instance that raises FileNotFoundError
        mock_instance = MagicMock()
        mock_instance.param.return_value = mock_instance
        mock_instance.command.return_value = mock_instance
        mock_instance.run.side_effect = FileNotFoundError()
        mock_builder.return_value = mock_instance

        repo = ConcreteResticRepository("test_location")

        with pytest.raises(ResticError) as exc_info:
            ResticRepository._verify_restic_executable(repo, "0.18.0")

        assert "restic executable not found" in str(exc_info.value)

@pytest.mark.unit
def test_verify_restic_executable_older_version():
    min_version = "0.10.0"
    older_version = "0.9.6"

    with patch('TimeLocker.restic.restic_repository.CommandBuilder') as mock_builder:
        # Create a mock command builder instance
        mock_instance = MagicMock()
        mock_instance.param.return_value = mock_instance
        mock_instance.command.return_value = mock_instance
        mock_instance.run.return_value = json.dumps({"version": older_version})
        mock_builder.return_value = mock_instance

        repository = ConcreteResticRepository("test_location")

        with pytest.raises(ResticError) as exc_info:
            ResticRepository._verify_restic_executable(repository, min_version)

        assert f"restic version {older_version} is below the required minimum version {min_version}" in str(exc_info.value)

@pytest.mark.unit
def test__verify_restic_executable_version_below_minimum():
    with patch('TimeLocker.restic.restic_repository.CommandBuilder') as mock_builder:
        # Create a mock command builder instance
        mock_instance = MagicMock()
        mock_instance.param.return_value = mock_instance
        mock_instance.command.return_value = mock_instance
        mock_instance.run.return_value = json.dumps({"version": "0.9.0"})
        mock_builder.return_value = mock_instance

        repo = ConcreteResticRepository("test_location")

        with pytest.raises(ResticError) as exc_info:
            ResticRepository._verify_restic_executable(repo, "0.10.0")

        assert "restic version 0.9.0 is below the required minimum version 0.10.0" in str(exc_info.value)
