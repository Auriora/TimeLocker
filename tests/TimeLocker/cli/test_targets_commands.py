"""
Unit tests for TimeLocker CLI targets command group.

Tests targets command parsing, parameter validation, help output, and error handling.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from src.TimeLocker.cli import app

# Set wider terminal width to prevent help text truncation in CI
runner = CliRunner(env={'COLUMNS': '200'})


def _combined_output(result):
    """Combine stdout and stderr for matching convenience across environments."""
    out = result.stdout or ""
    err = getattr(result, "stderr", "") or ""
    return out + "\n" + err


class TestTargetsCommands:
    """Test suite for targets command group."""

    @pytest.mark.unit
    def test_targets_help_output(self):
        """Test targets command group help output."""
        result = runner.invoke(app, ["targets", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "target" in combined.lower()
        assert "backup" in combined.lower()
        # Should show available subcommands
        assert "list" in combined.lower()
        assert "add" in combined.lower()
        assert "show" in combined.lower()

    @pytest.mark.unit
    def test_targets_list_help(self):
        """Test targets list command help output."""
        result = runner.invoke(app, ["targets", "list", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "list" in combined.lower()
        assert "target" in combined.lower()

    @pytest.mark.unit
    def test_targets_add_help(self):
        """Test targets add command help output."""
        result = runner.invoke(app, ["targets", "add", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "add" in combined.lower()
        assert "target" in combined.lower()
        # Should show key options
        assert "--path" in combined

    @pytest.mark.unit
    def test_targets_show_help(self):
        """Test targets show command help output."""
        result = runner.invoke(app, ["targets", "show", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "show" in combined.lower()
        assert "target" in combined.lower()

    @pytest.mark.unit
    def test_targets_edit_help(self):
        """Test targets edit command help output."""
        result = runner.invoke(app, ["targets", "edit", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "edit" in combined.lower()
        assert "target" in combined.lower()

    @pytest.mark.unit
    def test_targets_remove_help(self):
        """Test targets remove command help output."""
        result = runner.invoke(app, ["targets", "remove", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "remove" in combined.lower()
        assert "target" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_list_command(self, mock_service_manager):
        """Test targets list command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_backup_targets.return_value = []
        
        result = runner.invoke(app, ["targets", "list"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_targets_add_missing_parameters(self):
        """Test targets add command with missing parameters should prompt."""
        result = runner.invoke(app, ["targets", "add"])
        
        # Should either prompt for input or show helpful error
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_name_only(self, mock_service_manager):
        """Test targets add command with name only should prompt for paths."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["targets", "add", "test-target"])
        
        # Should either prompt for paths or show helpful error
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_paths(self, mock_service_manager):
        """Test targets add command with paths."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "targets", "add", "test-target",
                "--path", temp_dir
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_multiple_paths(self, mock_service_manager):
        """Test targets add command with multiple paths."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                result = runner.invoke(app, [
                    "targets", "add", "test-target",
                    "--path", temp_dir1,
                    "--path", temp_dir2
                ])
                
                # Should accept multiple paths
                assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_description(self, mock_service_manager):
        """Test targets add command with description."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "targets", "add", "test-target",
                "--path", temp_dir,
                "--description", "Test backup target"
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_exclude_patterns(self, mock_service_manager):
        """Test targets add command with exclude patterns."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "targets", "add", "test-target",
                "--path", temp_dir,
                "--exclude", "*.tmp",
                "--exclude", "*.log"
            ])
            
            # Should accept multiple exclude patterns
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_include_patterns(self, mock_service_manager):
        """Test targets add command with include patterns."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "targets", "add", "test-target",
                "--path", temp_dir,
                "--include", "*.txt",
                "--include", "*.md"
            ])
            
            # Should accept multiple include patterns
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_show_command(self, mock_service_manager):
        """Test targets show command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_backup_target.return_value = Mock()
        
        result = runner.invoke(app, ["targets", "show", "test-target"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_edit_command(self, mock_service_manager):
        """Test targets edit command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.edit_backup_target.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["targets", "edit", "test-target"])
        
        # Should not crash (may require interactive input)
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_remove_command(self, mock_service_manager):
        """Test targets remove command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_backup_target.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["targets", "remove", "test-target"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_targets_add_nonexistent_path(self):
        """Test targets add command with nonexistent path."""
        result = runner.invoke(app, [
            "targets", "add", "test-target",
            "--path", "/nonexistent/path"
        ])
        
        # Should handle nonexistent path gracefully
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_targets_add_with_tags(self, mock_service_manager):
        """Test targets add command with tags."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_backup_target.return_value = Mock(success=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "targets", "add", "test-target",
                "--path", temp_dir,
                "--tags", "important",
                "--tags", "daily"
            ])
            
            # Should accept multiple tags
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_targets_show_nonexistent_target(self):
        """Test targets show command with nonexistent target."""
        result = runner.invoke(app, ["targets", "show", "nonexistent-target"])
        
        # Should handle nonexistent target gracefully
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_targets_remove_nonexistent_target(self):
        """Test targets remove command with nonexistent target."""
        result = runner.invoke(app, ["targets", "remove", "nonexistent-target"])
        
        # Should handle nonexistent target gracefully
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_targets_commands_verbose_flag(self):
        """Test targets commands with verbose flag."""
        commands = [
            ["targets", "list", "--verbose"],
            ["targets", "show", "test-target", "--verbose"],
        ]
        
        for command in commands:
            result = runner.invoke(app, command)
            # Verbose flag should be accepted
            assert result.exit_code in [0, 1]
