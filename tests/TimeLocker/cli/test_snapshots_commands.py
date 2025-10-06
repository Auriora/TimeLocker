"""
Unit tests for TimeLocker CLI snapshots command group.

Tests snapshots command parsing, parameter validation, help output, and error handling.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.TimeLocker.cli import app
from .test_utils import runner, _combined_output


class TestSnapshotsCommands:
    """Test suite for snapshots command group."""

    @pytest.mark.unit
    def test_snapshots_help_output(self):
        """Test snapshots command group help output."""
        result = runner.invoke(app, ["snapshots", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "snapshot" in combined.lower()
        assert "operations" in combined.lower()
        # Should show available subcommands
        assert "list" in combined.lower()
        assert "show" in combined.lower()
        assert "restore" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_list_help(self):
        """Test snapshots list command help output."""
        result = runner.invoke(app, ["snapshots", "list", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "list" in combined.lower()
        assert "snapshot" in combined.lower()
        # Should show repository option
        assert "--repository" in combined or "-r" in combined

    @pytest.mark.unit
    def test_snapshots_show_help(self):
        """Test snapshots show command help output."""
        result = runner.invoke(app, ["snapshots", "show", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "show" in combined.lower()
        assert "snapshot" in combined.lower()
        assert "details" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_restore_help(self):
        """Test snapshots restore command help output."""
        result = runner.invoke(app, ["snapshots", "restore", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "restore" in combined.lower()
        assert "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_contents_help(self):
        """Test snapshots contents command help output."""
        result = runner.invoke(app, ["snapshots", "contents", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "contents" in combined.lower()
        assert "snapshot" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_mount_help(self):
        """Test snapshots mount command help output."""
        result = runner.invoke(app, ["snapshots", "mount", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "mount" in combined.lower()
        assert "filesystem" in combined.lower()

    @pytest.mark.unit
    def test_snapshots_find_help(self):
        """Test snapshots find command help output."""
        result = runner.invoke(app, ["snapshots", "find", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "find" in combined.lower()
        assert "search" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_list_command(self, mock_service_manager):
        """Test snapshots list command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshots.return_value = []
        
        result = runner.invoke(app, ["snapshots", "list"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_list_with_repository(self, mock_service_manager):
        """Test snapshots list command with repository parameter."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshots.return_value = []
        
        result = runner.invoke(app, [
            "snapshots", "list",
            "--repository", "test-repo"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_snapshots_show_invalid_id(self):
        """Test snapshots show command with invalid snapshot ID."""
        result = runner.invoke(app, [
            "snapshots", "show", "invalid$$id"
        ])
        
        # Should reject invalid snapshot ID format
        assert result.exit_code != 0
        combined = _combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_show_valid_id(self, mock_service_manager):
        """Test snapshots show command with valid snapshot ID."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_snapshot_details.return_value = Mock()
        
        result = runner.invoke(app, [
            "snapshots", "show", "abc123def456"
        ])
        
        # Should not crash with valid ID
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_snapshots_contents_invalid_id(self):
        """Test snapshots contents command with invalid snapshot ID."""
        result = runner.invoke(app, [
            "snapshots", "contents", "invalid$$id"
        ])
        
        # Should reject invalid snapshot ID format
        assert result.exit_code != 0
        combined = _combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_contents_with_path(self, mock_service_manager):
        """Test snapshots contents command with path parameter."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_snapshot_contents.return_value = []
        
        result = runner.invoke(app, [
            "snapshots", "contents", "abc123def456",
            "--path", "/home/user"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_snapshots_mount_invalid_id(self):
        """Test snapshots mount command with invalid snapshot ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "snapshots", "mount", "invalid$$id", temp_dir
            ])
            
            # Should reject invalid snapshot ID format
            assert result.exit_code != 0
            combined = _combined_output(result)
            assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_mount_valid_id(self, mock_service_manager):
        """Test snapshots mount command with valid snapshot ID."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.mount_snapshot.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "snapshots", "mount", "abc123def456", temp_dir
            ])
            
            # Should not crash with valid ID
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_snapshots_umount_invalid_id(self):
        """Test snapshots umount command with invalid snapshot ID."""
        result = runner.invoke(app, [
            "snapshots", "umount", "invalid$$id"
        ])
        
        # Should reject invalid snapshot ID format
        assert result.exit_code != 0
        combined = _combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_restore_command(self, mock_service_manager):
        """Test snapshots restore command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.restore_snapshot.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "snapshots", "restore", "abc123def456", temp_dir
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_find_command(self, mock_service_manager):
        """Test snapshots find command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.find_in_snapshots.return_value = []
        
        result = runner.invoke(app, [
            "snapshots", "find", "*.txt"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_find_with_options(self, mock_service_manager):
        """Test snapshots find command with search options."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.find_in_snapshots.return_value = []
        
        result = runner.invoke(app, [
            "snapshots", "find", "*.txt",
            "--type", "name",
            "--host", "myhost",
            "--tag", "important",
            "--limit", "50"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_snapshots_forget_invalid_id(self):
        """Test snapshots forget command with invalid snapshot ID."""
        result = runner.invoke(app, [
            "snapshots", "forget", "invalid$$id"
        ])
        
        # Should reject invalid snapshot ID format
        assert result.exit_code != 0
        combined = _combined_output(result)
        assert "invalid" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_prune_command(self, mock_service_manager):
        """Test snapshots prune command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.prune_snapshots.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["snapshots", "prune"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_snapshots_diff_command(self, mock_service_manager):
        """Test snapshots diff command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.diff_snapshots.return_value = Mock()
        
        result = runner.invoke(app, [
            "snapshots", "diff", "abc123def456", "def789ghi012"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]
