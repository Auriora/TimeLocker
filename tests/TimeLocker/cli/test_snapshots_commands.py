"""
Unit tests for TimeLocker CLI snapshots command group.

Tests snapshots command parsing, parameter validation, help output, and error handling.
"""

import pytest
import tempfile
from unittest.mock import Mock, patch

from src.TimeLocker.cli import app
from .test_utils import runner, combined_output, assert_success, assert_exit_code


class TestSnapshotsCommands:
    """Test suite for snapshots command group."""

    @pytest.mark.unit
    def test_snapshots_help_output(self):
        result = runner.invoke(app, ["snapshots", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "snapshot" in combined.lower()
        assert "operations" in combined.lower()
        assert "list" in combined.lower()
        assert "show" in combined.lower()
        assert "restore" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_list_help(self):
        result = runner.invoke(app, ["snapshots", "list", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "list" in combined.lower()
        assert "snapshot" in combined.lower()
        assert "--repository" in combined or "-r" in combined

    @pytest.mark.unit
    def test_snapshots_show_help(self):
        result = runner.invoke(app, ["snapshots", "show", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "show" in combined.lower()
        assert "snapshot" in combined.lower()
        assert "details" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_restore_help(self):
        result = runner.invoke(app, ["snapshots", "restore", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "restore" in combined.lower()
        assert "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_contents_help(self):
        result = runner.invoke(app, ["snapshots", "contents", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "contents" in combined.lower()
        assert "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_mount_help(self):
        result = runner.invoke(app, ["snapshots", "mount", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "mount" in combined.lower()
        assert "filesystem" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_find_help(self):
        result = runner.invoke(app, ["snapshots", "find", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "find" in combined.lower()
        assert "search" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_list_command(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshots.return_value = []
        result = runner.invoke(app, ["snapshots", "list"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_list_with_repository(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshots.return_value = []
        result = runner.invoke(app, ["snapshots", "list", "--repository", "test-repo"])
        assert_success(result)

    @pytest.mark.unit
    def test_snapshots_show_invalid_id(self):
        result = runner.invoke(app, ["snapshots", "show", "invalid$$id"])
        assert result.exit_code != 0, "Invalid snapshot ID should yield non-zero exit code"
        combined = combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_show_valid_id(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_snapshot_details.return_value = Mock()
        result = runner.invoke(app, ["snapshots", "show", "abc123def456"])
        assert_success(result)

    @pytest.mark.unit
    def test_snapshots_contents_invalid_id(self):
        result = runner.invoke(app, ["snapshots", "contents", "invalid$$id"])
        assert result.exit_code != 0
        combined = combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_contents_with_path(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshot_contents.return_value = []
        result = runner.invoke(app, ["snapshots", "contents", "abc123def456", "--path", "/home/user"])
        assert_success(result)

    @pytest.mark.unit
    def test_snapshots_mount_invalid_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, ["snapshots", "mount", "invalid$$id", temp_dir])
            assert result.exit_code != 0
            combined = combined_output(result)
            assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_mount_valid_id(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.mount_snapshot.return_value = Mock(success=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, ["snapshots", "mount", "abc123def456", temp_dir])
            assert_success(result)

    @pytest.mark.unit
    def test_snapshots_umount_invalid_id(self):
        result = runner.invoke(app, ["snapshots", "umount", "invalid$$id"])
        assert result.exit_code != 0
        combined = combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_restore_command(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.restore_snapshot.return_value = Mock(success=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, ["snapshots", "restore", "abc123def456", temp_dir])
            assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_find_command(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.find_in_snapshots.return_value = []
        result = runner.invoke(app, ["snapshots", "find", "*.txt"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_find_with_options(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.find_in_snapshots.return_value = []
        result = runner.invoke(app, ["snapshots", "find", "*.txt", "--type", "name", "--host", "myhost", "--tag", "important", "--limit", "50"])
        assert_success(result)

    @pytest.mark.unit
    def test_snapshots_forget_invalid_id(self):
        result = runner.invoke(app, ["snapshots", "forget", "invalid$$id"])
        assert result.exit_code != 0
        combined = combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_prune_command(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.prune_snapshots.return_value = Mock(success=True)
        result = runner.invoke(app, ["snapshots", "prune"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_diff_command(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.diff_snapshots.return_value = Mock()
        result = runner.invoke(app, ["snapshots", "diff", "abc123def456", "def789ghi012"])
        assert_success(result)
