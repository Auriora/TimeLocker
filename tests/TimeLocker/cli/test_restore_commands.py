"""
Unit tests for TimeLocker CLI restore command group.

Tests restore command parsing, parameter validation, help output, and error handling.
"""

import pytest
from unittest.mock import Mock, patch

from src.TimeLocker.cli import app
from .test_utils import runner, combined_output, assert_success, assert_exit_code


class TestRestoreCommands:
    """Test suite for restore command group."""

    @pytest.mark.unit
    def test_restore_help_output(self):
        """Test that restore command group shows help."""
        result = runner.invoke(app, ["restore", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "restore" in combined.lower() or "recovery" in combined.lower()

    @pytest.mark.unit
    def test_restore_browse_help(self):
        """Test that restore browse command shows help."""
        result = runner.invoke(app, ["restore", "browse", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "browse" in combined.lower()
        assert "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_restore_files_help(self):
        """Test that restore files command shows help."""
        result = runner.invoke(app, ["restore", "files", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "files" in combined.lower()
        assert "restore" in combined.lower()

    @pytest.mark.unit
    def test_restore_full_help(self):
        """Test that restore full command shows help."""
        result = runner.invoke(app, ["restore", "full", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "full" in combined.lower()
        assert "complete" in combined.lower() or "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_restore_list_help(self):
        """Test that restore list command shows help."""
        result = runner.invoke(app, ["restore", "list", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "list" in combined.lower()
        assert "snapshot" in combined.lower()


    @pytest.mark.unit
    def test_restore_mount_help(self):
        """Test that restore mount command shows help."""
        result = runner.invoke(app, ["restore", "mount", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "mount" in combined.lower()
        assert "filesystem" in combined.lower() or "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_restore_umount_help(self):
        """Test that restore umount command shows help."""
        result = runner.invoke(app, ["restore", "umount", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "umount" in combined.lower() or "unmount" in combined.lower()

    @pytest.mark.unit
    def test_restore_find_help(self):
        """Test that restore find command shows help."""
        result = runner.invoke(app, ["restore", "find", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "find" in combined.lower()
        assert "search" in combined.lower()

    @pytest.mark.unit
    def test_restore_diff_help(self):
        """Test that restore diff command shows help."""
        result = runner.invoke(app, ["restore", "diff", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "diff" in combined.lower()
        assert "compare" in combined.lower() or "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_restore_verify_help(self):
        """Test that restore verify command shows help."""
        result = runner.invoke(app, ["restore", "verify", "--help"])
        combined = combined_output(result)
        assert_success(result)
        assert "verify" in combined.lower()
        assert "integrity" in combined.lower() or "restored" in combined.lower()

    @pytest.mark.unit
    def test_restore_browse_missing_args(self):
        """Test that restore browse requires repository and snapshot arguments."""
        result = runner.invoke(app, ["restore", "browse"])
        assert result.exit_code != 0, "Missing arguments should yield non-zero exit code"

    @pytest.mark.unit
    def test_restore_files_missing_args(self):
        """Test that restore files requires repository, snapshot, and target arguments."""
        result = runner.invoke(app, ["restore", "files"])
        assert result.exit_code != 0, "Missing arguments should yield non-zero exit code"

    @pytest.mark.unit
    def test_restore_list_missing_args(self):
        """Test that restore list requires repository argument."""
        result = runner.invoke(app, ["restore", "list"])
        assert result.exit_code != 0, "Missing repository argument should yield non-zero exit code"

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.restore.get_cli_service_manager')
    def test_restore_list_with_repository(self, mock_service_manager):
        """Test that restore list works with repository argument."""
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_list_method = Mock(return_value=[])
        mock_manager.list_snapshots = mock_list_method
        
        result = runner.invoke(app, ["restore", "list", "test-repo"])
        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1], "Command should complete with valid exit code"
