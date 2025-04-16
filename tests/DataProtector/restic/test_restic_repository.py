from DataProtector.backup_repository import RetentionPolicy
from DataProtector.backup_snapshot import BackupSnapshot
from DataProtector.backup_target import BackupTarget
from packaging import version
from pathlib import Path
from DataProtector.restic.errors import RepositoryError
from DataProtector.restic.errors import ResticError
from DataProtector.restic.restic_repository import ResticRepository, RESTIC_MIN_VERSION
from unittest.mock import Mock
from unittest.mock import patch, MagicMock
import builtins
import io
import json
import os
import pytest
import sys

class TestResticRepository:

    def test___init___1(self):
        """
        Test initializing a ResticRepository with valid parameters.

        This test verifies that a ResticRepository object can be successfully
        created with a valid location, and that the object's attributes are
        correctly set based on the input parameters.
        """
        location = "/path/to/backup"
        tags = ["test", "backup"]
        password = "secure_password"

        repo = ResticRepository(location, tags=tags, password=password)

        assert repo._location == location
        assert repo._explicit_password == password
        assert repo._restic_version >= RESTIC_MIN_VERSION
        assert repo._command is not None
        assert repo._cached_env is None

    def test__handle_restic_output_1(self):
        """
        Test that _handle_restic_output correctly handles 'summary' message type.
        It should call _on_backup_summary with the input dictionary when message_type is 'summary'.
        """
        repo = ResticRepository(location="test_location")
        repo._on_backup_summary = Mock()

        test_output = {"message_type": "summary", "data": "test_summary_data"}
        repo._handle_restic_output(test_output)

        repo._on_backup_summary.assert_called_once_with(test_output)

    def test__handle_restic_output_2(self):
        """
        Test the _handle_restic_output method when the message_type is "status".
        This test verifies that the _on_backup_status method is called with the correct
        output when the input dictionary has a message_type of "status".
        """
        # Create a mock ResticRepository instance
        repo = Mock(spec=ResticRepository)

        # Create a sample output dictionary with message_type "status"
        output = {"message_type": "status", "status_data": "test_status"}

        # Call the method under test
        ResticRepository._handle_restic_output(repo, output)

        # Assert that _on_backup_status was called with the correct argument
        repo._on_backup_status.assert_called_once_with(output)

        # Assert that _on_backup_summary was not called
        repo._on_backup_summary.assert_not_called()

    def test__handle_restic_output_3(self):
        """
        Test the _handle_restic_output method when the message_type is neither "summary" nor "status".
        This test ensures that the method correctly handles other message types without raising exceptions.
        """
        repo = ResticRepository(location="test_location")
        output = {"message_type": "other_type", "data": "test_data"}

        with patch.object(repo, '_on_backup_summary') as mock_summary, \
             patch.object(repo, '_on_backup_status') as mock_status:

            repo._handle_restic_output(output)

            mock_summary.assert_not_called()
            mock_status.assert_not_called()

    def test__on_backup_status_prints_status(self):
        """
        Test that _on_backup_status method prints the backup status correctly.
        """
        repo = ResticRepository(location="test_location")
        status = {"message_type": "status", "percent_done": 50}

        # Capture the printed output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        repo._on_backup_status(status)

        # Reset redirect.
        sys.stdout = sys.__stdout__

        # Assert that the correct message was printed
        assert captured_output.getvalue().strip() == f"Backup Status: {status}"

    def test__on_backup_status_with_empty_dict(self):
        """
        Test the _on_backup_status method with an empty dictionary.
        This tests the edge case of receiving an empty status update.
        """
        repo = ResticRepository("dummy_location")

        # Capture the printed output
        captured_output = []
        def mock_print(output):
            captured_output.append(output)

        # Temporarily replace the built-in print function
        original_print = builtins.print
        builtins.print = mock_print

        try:
            repo._on_backup_status({})

            # Assert that the method handled the empty dict without raising an exception
            assert len(captured_output) == 1
            assert captured_output[0] == "Backup Status: {}"
        finally:
            # Restore the original print function
            builtins.print = original_print

    def test__on_backup_summary_prints_summary(self):
        """
        Test that _on_backup_summary method prints the backup summary correctly.
        This test verifies that the method prints the received summary dictionary.
        """
        repo = ResticRepository(location="test_location")
        summary = {"files": 100, "dirs": 10, "size": 1024}

        # Capture printed output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        repo._on_backup_summary(summary)

        sys.stdout = sys.__stdout__

        expected_output = f"Backup Summary: {summary}\n"
        assert captured_output.getvalue() == expected_output

    def test__on_backup_summary_with_empty_dict(self):
        """
        Test the _on_backup_summary method with an empty dictionary as input.
        This tests the edge case of receiving an empty summary, which is handled
        by the current implementation by simply printing it.
        """
        repo = ResticRepository("dummy_location")

        # Capture stdout to verify the print output
        with pytest.raises(SystemExit) as excinfo:
            repo._on_backup_summary({})

        # Assert that the method prints the empty dictionary
        assert "Backup Summary: {}" in str(excinfo.value)

    def test__verify_restic_executable_2(self):
        """
        Test that _verify_restic_executable returns the restic version when it meets the minimum version requirement.
        """
        mock_command = MagicMock()
        mock_command.param.return_value.run.return_value = json.dumps({"version": "0.18.1"})

        repo = ResticRepository("test_location")
        repo._command = mock_command

        result = repo._verify_restic_executable("0.18.0")

        assert result == "0.18.1"
        mock_command.param.assert_called_once_with("version")
        mock_command.param.return_value.run.assert_called_once()

    def test__verify_restic_executable_not_found(self):
        """
        Test the _verify_restic_executable method when the restic executable is not found.
        """
        mock_command = Mock()
        mock_command.param.return_value.run.side_effect = FileNotFoundError()

        repo = ResticRepository("test_location")
        repo._command = mock_command

        with pytest.raises(ResticError) as exc_info:
            repo._verify_restic_executable("0.18.0")

        assert "restic executable not found" in str(exc_info.value)

    def test__verify_restic_executable_older_version(self):
        """
        Test that _verify_restic_executable raises ResticError when the installed restic version
        is older than the required minimum version.
        """
        min_version = "0.10.0"
        older_version = "0.9.6"

        mock_command = Mock()
        mock_command.param.return_value.run.return_value = json.dumps({"version": older_version})

        repository = ResticRepository("test_location")
        repository._command = mock_command

        with patch('packaging.version.parse', side_effect=version.parse):
            with self.assertRaises(ResticError) as context:
                repository._verify_restic_executable(min_version)

        self.assertIn(f"restic version {older_version} is below the required minimum version {min_version}", str(context.exception))

    def test__verify_restic_executable_version_below_minimum(self):
        """
        Test the _verify_restic_executable method when the detected restic version
        is below the required minimum version.
        """
        mock_command = Mock()
        mock_command.param.return_value.run.return_value = json.dumps({"version": "0.9.0"})

        repo = ResticRepository("test_location")
        repo._command = mock_command

        with pytest.raises(ResticError) as exc_info:
            repo._verify_restic_executable("0.10.0")

        assert "restic version 0.9.0 is below the required minimum version 0.10.0" in str(exc_info.value)

    def test_apply_retention_policy_2(self):
        """
        Test that apply_retention_policy returns False when the command execution fails and prune is False.

        This test verifies that:
        1. The method correctly constructs the command without the --prune flag.
        2. When the command execution fails (returncode != 0), the method returns False.
        3. An error message is logged when the command fails.
        """
        repo = ResticRepository("test_location")
        policy = RetentionPolicy()

        mock_command = Mock()
        mock_command.param.return_value = mock_command
        mock_command.run.return_value = Mock(returncode=1, stderr="Command failed")

        repo._command = mock_command

        with patch('restic.restic_repository.logger') as mock_logger:
            result = repo.apply_retention_policy(policy, prune=False)

        assert result == False
        mock_command.param.assert_called_once_with("forget")
        mock_command.run.assert_called_once_with(repo.to_env())
        mock_logger.error.assert_called_once_with("Failed to implement Retention Policy: {result.stderr}")

    def test_apply_retention_policy_3(self):
        """
        Test that apply_retention_policy returns True when prune is True and the command execution is successful.
        """
        repository = ResticRepository(location="test_location")
        policy = RetentionPolicy()

        # Mock the _command.param().run() method to return a successful result
        repository._command.param().run = lambda env: type('Result', (), {'returncode': 0})()

        result = repository.apply_retention_policy(policy, prune=True)

        assert result == True

    def test_apply_retention_policy_failure(self):
        """
        Test the apply_retention_policy method when the restic command fails.
        This test verifies that the method returns False and logs an error
        when the restic command returns a non-zero exit code.
        """
        # Mock ResticRepository
        repo = ResticRepository("dummy_location")

        # Mock the run method to simulate a command failure
        def mock_run(env):
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stderr = "Command failed"
            return MockResult()

        repo._command.run = mock_run

        # Create a dummy RetentionPolicy
        policy = RetentionPolicy()

        # Mock logger to capture the error message
        with pytest.raises(Exception) as exc_info:
            result = repo.apply_retention_policy(policy)

        assert not result
        assert "Failed to implement Retention Policy" in str(exc_info.value)

    def test_apply_retention_policy_when_prune_is_true_and_command_fails(self):
        """
        Test apply_retention_policy when prune is True and the command execution fails.

        This test verifies that the method returns False when the restic command fails
        (i.e., returns a non-zero exit code) while applying the retention policy with pruning.
        """
        repo = ResticRepository("test_location")
        policy = RetentionPolicy()

        mock_command = MagicMock()
        mock_run = MagicMock()
        mock_run.returncode = 1
        mock_run.stderr = "Error occurred"
        mock_command.run.return_value = mock_run

        repo._command = MagicMock()
        repo._command.param.return_value = mock_command

        with patch('restic.restic_repository.logger') as mock_logger:
            result = repo.apply_retention_policy(policy, prune=True)

        assert result is False
        mock_logger.error.assert_called_once()
        mock_command.param.assert_called_with("--prune")

    def test_backup_target_1(self):
        """
        Test that backup_target method calls the correct command with the right environment.

        This test verifies that:
        1. The 'backup' parameter is added to the command.
        2. The command is run with the correct environment.
        3. The method returns the result of running the command.
        """
        # Arrange
        mock_command = Mock()
        mock_command.param.return_value = mock_command
        mock_command.run.return_value = "Backup successful"

        mock_env = {"RESTIC_PASSWORD": "test_password"}

        repository = ResticRepository(location="test_location")
        repository._command = mock_command
        repository.to_env = Mock(return_value=mock_env)

        targets = [BackupTarget("test_path")]

        # Act
        result = repository.backup_target(targets)

        # Assert
        mock_command.param.assert_called_once_with("backup")
        mock_command.run.assert_called_once_with(mock_env)
        assert result == "Backup successful"

    def test_backup_target_no_targets(self):
        """
        Test backup_target method with an empty list of targets.
        This tests the edge case where no backup targets are provided.
        """
        repo = ResticRepository("test_location")
        with pytest.raises(ValueError):
            repo.backup_target([])

    def test_backup_target_none_targets(self):
        """
        Test backup_target method with None as targets.
        This tests the edge case where targets is None instead of a list.
        """
        repo = ResticRepository("test_location")
        with pytest.raises(TypeError):
            repo.backup_target(None)

    def test_check_no_password(self):
        """
        Test the check method when no password is provided, either explicitly or in the environment.
        This should raise a RepositoryError.
        """
        repo = ResticRepository(location="test_location")

        # Ensure RESTIC_PASSWORD is not set in the environment
        if "RESTIC_PASSWORD" in os.environ:
            del os.environ["RESTIC_PASSWORD"]

        with pytest.raises(RepositoryError, match="RESTIC_PASSWORD must be set explicitly or in the environment."):
            repo.check()

    def test_check_repository_availability(self):
        """
        Test that the check method returns the result of running the 'check' command
        with the repository's environment.
        """
        mock_command = Mock()
        mock_command.param.return_value = mock_command
        mock_command.run.return_value = "Repository check successful"

        with patch.object(ResticRepository, '_command', mock_command):
            with patch.object(ResticRepository, 'to_env', return_value={"RESTIC_PASSWORD": "test_password"}):
                repo = ResticRepository("test_location")
                result = repo.check()

        mock_command.param.assert_called_once_with("check")
        mock_command.run.assert_called_once_with({"RESTIC_PASSWORD": "test_password"})
        assert result == "Repository check successful"

    def test_forget_snapshot_failure(self):
        """
        Test the forget_snapshot method when the command execution fails.
        This test verifies that the method returns False when the command
        execution results in a non-zero return code.
        """
        repo = ResticRepository("test_location")
        repo._command = MagicMock()
        repo._command.param.return_value = repo._command
        repo._command.run.return_value = MagicMock(returncode=1, stderr="Error message")

        with patch.object(repo, 'to_env', return_value={}):
            result = repo.forget_snapshot("test_snapshot_id")

        assert result == False

    def test_forget_snapshot_with_prune_and_error(self):
        """
        Test forget_snapshot method when prune is True and the command execution fails.

        This test verifies that:
        1. The forget_snapshot method correctly constructs the command with the 'forget' parameter,
           the provided snapshot ID, and the '--prune' flag.
        2. The method returns False when the command execution fails (returncode != 0).
        3. An error message is logged when the command fails.
        """
        mock_repo = ResticRepository(location="mock_location")
        mock_repo._command = MagicMock()
        mock_repo.to_env = MagicMock(return_value={})

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Mock error"

        mock_repo._command.param.return_value.param.return_value.run.return_value = mock_result

        with patch('restic.restic_repository.logger') as mock_logger:
            result = mock_repo.forget_snapshot("mock_snapshot_id", prune=True)

        self.assertFalse(result)
        mock_repo._command.param.assert_called_with("forget")
        mock_repo._command.param.return_value.param.assert_called_with("mock_snapshot_id")
        mock_repo._command.param.return_value.param.return_value.param.assert_called_with("--prune")
        mock_logger.error.assert_called_once_with("Failed to initialize repository: {result.stderr}")

    def test_handle_restic_output_invalid_message_type(self):
        """
        Test the _handle_restic_output method with an invalid message type.
        This tests the edge case where the input dictionary has an unrecognized message_type.
        """
        repo = ResticRepository("dummy_location")
        output = {"message_type": "invalid_type"}

        # Since the method doesn't explicitly handle invalid types, we expect it to do nothing
        # We can verify this by ensuring it doesn't raise an exception
        repo._handle_restic_output(output)

    def test_handle_restic_output_missing_message_type(self):
        """
        Test the _handle_restic_output method with a missing message_type key.
        This tests the edge case where the input dictionary doesn't contain a message_type key.
        """
        repo = ResticRepository("dummy_location")
        output = {}

        # The method should handle this case gracefully without raising an exception
        repo._handle_restic_output(output)

    def test_initialize_2(self):
        """
        Test that the initialize method returns True when the command execution is successful.

        This test case verifies that when the command execution returns a zero return code,
        the initialize method returns True, indicating successful initialization of the repository.
        """
        # Create a mock ResticRepository instance
        repo = ResticRepository("test_location")

        # Mock the _command.param().run() method to return a result with returncode 0
        mock_result = Mock()
        mock_result.returncode = 0
        repo._command.param.return_value.run.return_value = mock_result

        # Call the initialize method
        result = repo.initialize()

        # Assert that the method returns True
        self.assertTrue(result)

        # Verify that the command was called with the correct parameters
        repo._command.param.assert_called_once_with("init")
        repo._command.param.return_value.run.assert_called_once_with(repo.to_env())

    def test_initialize_failure(self):
        """
        Test the initialize method when the command execution fails.
        This test verifies that the method returns False and logs an error
        when the command execution results in a non-zero return code.
        """
        mock_repo = ResticRepository("test_location")
        mock_command = MagicMock()
        mock_command.run.return_value = MagicMock(returncode=1, stderr="Error message")
        mock_repo._command = mock_command

        with patch('restic.restic_repository.logger') as mock_logger:
            result = mock_repo.initialize()

        assert result == False
        mock_logger.error.assert_called_once_with("Failed to initialize repository: {result.stderr}")

    def test_initialize_failure_2(self):
        """
        Test that initialize() returns False when the command execution fails.
        This test verifies the behavior when the restic init command returns a non-zero exit code.
        """
        # Mock the CommandBuilder and its methods
        with patch('restic.restic_repository.CommandBuilder') as mock_command_builder:
            mock_command = MagicMock()
            mock_command_builder.return_value.param.return_value = mock_command
            mock_command.run.return_value.returncode = 1
            mock_command.run.return_value.stderr = "Error initializing repository"

            # Create a ResticRepository instance
            repo = ResticRepository("test_location")

            # Mock the to_env method
            repo.to_env = MagicMock(return_value={})

            # Call the initialize method
            result = repo.initialize()

            # Assert that the method returns False
            assert result is False

            # Verify that the command was called with the correct parameters
            mock_command.run.assert_called_once_with({})

    def test_location_returns_private_attribute(self):
        """
        Test that the location method returns the private _location attribute.
        This is not a true negative test, but it's the only relevant test
        based on the current implementation of the location method.
        """
        repo = ResticRepository("/path/to/repo")
        assert repo.location() == "/path/to/repo"

    def test_location_returns_repository_path(self):
        """
        Test that the location method returns the correct repository path.

        This test verifies that the location method of ResticRepository
        correctly returns the value of self._location, which represents
        the path to the repository.
        """
        # Arrange
        expected_location = "/path/to/repository"
        repository = ResticRepository(expected_location)

        # Act
        actual_location = repository.location()

        # Assert
        assert actual_location == expected_location, f"Expected location {expected_location}, but got {actual_location}"

    def test_password_no_explicit_password_no_env_variable(self):
        """
        Test the password method when no explicit password is set and the RESTIC_PASSWORD
        environment variable is not present. This should return None.
        """
        repo = ResticRepository(location="test_location")
        if "RESTIC_PASSWORD" in os.environ:
            del os.environ["RESTIC_PASSWORD"]

        result = repo.password()

        assert result is None, "Expected None when no explicit password and no environment variable are set"

    def test_password_returns_explicit_password_when_set(self):
        """
        Test that the password method returns the explicit password when it is set.
        """
        repo = ResticRepository(location="test_location", password="test_password")
        assert repo.password() == "test_password"

    def test_prune_data_removes_unreferenced_data(self):
        """
        Test that prune_data method removes unreferenced data from the repository.

        This test verifies that the prune_data method calls the underlying command
        with the correct parameters and returns the expected result.
        """
        # Create a mock ResticRepository instance
        repo = ResticRepository("test_location")

        # Mock the _command and to_env methods
        repo._command = MagicMock()
        repo._command.param.return_value = repo._command
        repo.to_env = MagicMock(return_value={"RESTIC_PASSWORD": "test_password"})

        # Set up the expected return value
        expected_result = "Pruning completed successfully"
        repo._command.run.return_value = expected_result

        # Call the method under test
        result = repo.prune_data()

        # Assert that the command was called with the correct parameters
        repo._command.param.assert_called_once_with("prune")
        repo._command.run.assert_called_once_with({"RESTIC_PASSWORD": "test_password"})

        # Assert that the method returns the expected result
        assert result == expected_result

    def test_prune_data_repository_error(self):
        """
        Test that prune_data raises a RepositoryError when the RESTIC_PASSWORD is not set.
        """
        repo = ResticRepository(location="test_location")

        # Simulate the scenario where the password is not set
        with patch.object(repo, 'password', return_value=None):
            with pytest.raises(RepositoryError, match="RESTIC_PASSWORD must be set explicitly or in the environment."):
                repo.prune_data()

    def test_restore_snapshot_with_target_path(self):
        """
        Test the restore method of ResticRepository with a snapshot ID and target path.
        This test verifies that the restore command is correctly constructed and executed
        with the provided snapshot ID and target path.
        """
        # Mock the ResticRepository and its dependencies
        repo = ResticRepository("test_location")
        repo._command = MagicMock()
        repo.to_env = MagicMock(return_value={})

        # Set up the mock chain
        mock_chain = MagicMock()
        repo._command.param.return_value = mock_chain
        mock_chain.param.return_value = mock_chain
        mock_chain.run.return_value = "Restore completed successfully"

        # Call the restore method
        snapshot_id = "abc123"
        target_path = Path("/restore/target")
        result = repo.restore(snapshot_id, target_path)

        # Assert that the command was constructed correctly
        repo._command.param.assert_called_once_with("restore")
        mock_chain.param.assert_any_call(snapshot_id)
        mock_chain.param.assert_any_call("target", target_path)

        # Assert that run was called with the correct environment
        mock_chain.run.assert_called_once_with(repo.to_env())

        # Assert the result
        assert result == "Restore completed successfully"

    def test_restore_with_empty_snapshot_id(self):
        """
        Test the restore method with an empty snapshot_id.
        This should trigger an error as the snapshot_id is a required parameter.
        """
        repo = ResticRepository("test_location")
        with pytest.raises(Exception):  # The exact exception type is not specified in the implementation
            repo.restore("")

    def test_restore_with_none_snapshot_id(self):
        """
        Test the restore method with None as snapshot_id.
        This should trigger an error as the snapshot_id is a required parameter and cannot be None.
        """
        repo = ResticRepository("test_location")
        with pytest.raises(Exception):  # The exact exception type is not specified in the implementation
            repo.restore(None)

    def test_snapshots_1(self):
        """
        Test that the snapshots method correctly returns a list of BackupSnapshot objects
        when given valid snapshot data from the _command.run() call.
        """
        # Mock the ResticRepository instance
        repo = MagicMock(spec=ResticRepository)

        # Mock the _command.param().run() call
        mock_run = MagicMock()
        mock_run.return_value = json.dumps([
            {"short_id": "abc123", "time": "2023-05-01T12:00:00Z", "paths": ["/path/to/backup"]},
            {"short_id": "def456", "time": "2023-05-02T12:00:00Z", "paths": ["/another/path"]}
        ])
        repo._command.param.return_value.run.return_value = mock_run.return_value

        # Call the snapshots method
        result = ResticRepository.snapshots(repo)

        # Assert that the result is a list of BackupSnapshot objects
        assert isinstance(result, list)
        assert all(isinstance(snap, BackupSnapshot) for snap in result)
        assert len(result) == 2

        # Check the properties of the returned BackupSnapshot objects
        assert result[0].snapshot_id == "abc123"
        assert result[0].timestamp == "2023-05-01T12:00:00Z"
        assert result[0].paths == ["/path/to/backup"]
        assert result[1].snapshot_id == "def456"
        assert result[1].timestamp == "2023-05-02T12:00:00Z"
        assert result[1].paths == ["/another/path"]

        # Verify that the _command.param().run() method was called with the correct arguments
        repo._command.param.assert_called_once_with("snapshots")
        repo._command.param.return_value.run.assert_called_once_with(repo.to_env())

    def test_snapshots_empty_list(self):
        """
        Test the snapshots method when the command returns an empty list.
        This tests the edge case of no snapshots being available.
        """
        mock_repo = Mock(spec=ResticRepository)
        mock_repo._command.param.return_value.run.return_value = "[]"
        mock_repo.to_env.return_value = {}

        result = ResticRepository.snapshots(mock_repo)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_snapshots_json_decode_error(self):
        """
        Test the snapshots method when the command output is not valid JSON.
        This tests the error handling for json.loads() which is explicitly used in the method.
        """
        mock_repo = Mock(spec=ResticRepository)
        mock_repo._command.param.return_value.run.return_value = "Invalid JSON"
        mock_repo.to_env.return_value = {}

        with patch('json.loads', side_effect=json.JSONDecodeError("Mocked error", "doc", 0)):
            with self.assertRaises(json.JSONDecodeError):
                ResticRepository.snapshots(mock_repo)

    def test_snapshots_missing_required_fields(self):
        """
        Test the snapshots method when the JSON output is missing required fields.
        This tests the error handling for accessing dictionary keys that might not exist.
        """
        mock_repo = Mock(spec=ResticRepository)
        mock_repo._command.param.return_value.run.return_value = '[{"incomplete": "data"}]'
        mock_repo.to_env.return_value = {}

        with self.assertRaises(KeyError):
            ResticRepository.snapshots(mock_repo)

    def test_stats_command_execution_error(self):
        """
        Test that the stats method handles errors during command execution.
        """
        repo = ResticRepository("test_location")
        repo._cached_env = {"RESTIC_PASSWORD": "test_password"}  # Set up a valid environment

        mock_run = Mock(side_effect=Exception("Command execution failed"))
        repo._command.param("stats").run = mock_run

        with self.assertRaises(Exception):
            repo.stats()

    def test_stats_environment_error(self):
        """
        Test that the stats method raises a RepositoryError when the environment
        is not properly set up (i.e., no RESTIC_PASSWORD).
        """
        repo = ResticRepository("test_location")
        repo._cached_env = None  # Reset cached environment
        repo._explicit_password = None  # Ensure no explicit password is set

        with patch.dict('os.environ', clear=True):  # Clear all environment variables
            with self.assertRaises(RepositoryError):
                repo.stats()

    def test_stats_invalid_json_response(self):
        """
        Test that the stats method handles invalid JSON responses.
        """
        repo = ResticRepository("test_location")
        repo._cached_env = {"RESTIC_PASSWORD": "test_password"}  # Set up a valid environment

        mock_run = Mock(return_value="Invalid JSON")
        repo._command.param("stats").run = mock_run

        with self.assertRaises(json.JSONDecodeError):
            repo.stats()

    def test_stats_returns_json_loaded_output(self):
        """
        Test that the stats method returns the JSON-loaded output of the command execution.
        """
        mock_command = Mock()
        mock_command.param.return_value = mock_command
        mock_command.run.return_value = '{"total_size": 1000, "total_file_count": 100}'

        repo = ResticRepository("test_location")
        repo._command = mock_command

        with patch.object(repo, 'to_env', return_value={}):
            result = repo.stats()

        assert result == {"total_size": 1000, "total_file_count": 100}
        mock_command.param.assert_called_once_with("stats")
        mock_command.run.assert_called_once_with({})

    def test_to_env_2(self):
        """
        Test the to_env method when _cached_env is not set and password is not provided.

        This test verifies that the method raises a RepositoryError when the password
        is not set explicitly or in the environment.
        """
        repo = ResticRepository(location="test_location")

        # Ensure _cached_env is not set
        repo._cached_env = None

        # Ensure password is not set
        repo._explicit_password = None

        with pytest.raises(RepositoryError, match="RESTIC_PASSWORD must be set explicitly or in the environment."):
            repo.to_env()

    def test_to_env_3(self):
        """
        Test that to_env() returns the correct environment dictionary when _cached_env is None
        and a password is set explicitly.
        """
        repository = ResticRepository(location="test_location", password="test_password")

        with patch.object(repository, 'backend_env', return_value={"BACKEND_VAR": "value"}):
            result = repository.to_env()

        expected_env = {
            "RESTIC_PASSWORD": "test_password",
            "BACKEND_VAR": "value"
        }

        assert result == expected_env
        assert repository._cached_env == expected_env

    def test_to_env_cached_env(self):
        """
        Test that to_env() returns the cached environment when it exists.

        This test verifies that when self._cached_env is not None,
        the to_env() method returns the cached environment without
        reconstructing it.
        """
        # Create a mock ResticRepository instance
        repo = MagicMock(spec=ResticRepository)

        # Set up the _cached_env attribute
        cached_env = {"RESTIC_PASSWORD": "test_password", "TEST_KEY": "test_value"}
        repo._cached_env = cached_env

        # Call the to_env method
        result = ResticRepository.to_env(repo)

        # Assert that the result is the same as the cached environment
        assert result == cached_env, "to_env() should return the cached environment"

        # Verify that backend_env() was not called
        repo.backend_env.assert_not_called()

    def test_to_env_missing_password(self):
        """
        Test the to_env method when no password is set (either explicitly or in environment).
        This should raise a RepositoryError.
        """
        repo = ResticRepository(location="test_location")

        # Ensure both explicit password and environment variable are not set
        repo._explicit_password = None
        if "RESTIC_PASSWORD" in repo.to_env():
            del repo.to_env()["RESTIC_PASSWORD"]

        with pytest.raises(RepositoryError, match="RESTIC_PASSWORD must be set explicitly or in the environment."):
            repo.to_env()

    def test_uri_returns_location(self):
        """
        Test that the uri method returns the _location attribute as-is.
        This is the only behavior explicitly implemented in the uri method.
        """
        repo = ResticRepository(location="/path/to/repo")
        assert repo.uri() == "/path/to/repo"

    def test_uri_returns_location_2(self):
        """
        Test that the uri method returns the correct location string.
        This test verifies that the uri method of ResticRepository
        returns a string that matches the _location attribute.
        """
        location = "/path/to/repository"
        repo = ResticRepository(location)
        assert repo.uri() == location

    def test_validate_missing_password(self):
        """
        Test that validate() raises a RepositoryError when the password is missing.
        """
        repo = ResticRepository("test_location")
        repo.password = MagicMock(return_value=None)

        with self.assertRaises(RepositoryError):
            repo.validate()

    def test_validate_repository_configuration(self):
        """
        Test that the validate method correctly calls the 'validate' command
        and returns its output.
        """
        mock_command = Mock()
        mock_command.param.return_value = mock_command
        mock_command.run.return_value = "Repository validated successfully"

        with patch('restic.restic_repository.CommandBuilder', return_value=mock_command):
            repo = ResticRepository(location="test_location")
            repo._command = mock_command
            repo.to_env = Mock(return_value={})

            result = repo.validate()

            mock_command.param.assert_called_once_with("validate")
            mock_command.run.assert_called_once_with({})
            assert result == "Repository validated successfully"
