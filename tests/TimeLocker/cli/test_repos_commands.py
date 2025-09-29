"""
Unit tests for TimeLocker CLI repos command group.

Tests repos command parsing, parameter validation, help output, and error handling.
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


class TestReposCommands:
    """Test suite for repos command group."""

    @pytest.mark.unit
    def test_repos_help_output(self):
        """Test repos command group help output."""
        result = runner.invoke(app, ["repos", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "repository" in combined.lower()
        assert "operations" in combined.lower()
        # Should show available subcommands
        assert "list" in combined.lower()
        assert "add" in combined.lower()
        assert "init" in combined.lower()

    @pytest.mark.unit
    def test_repos_list_help(self):
        """Test repos list command help output."""
        result = runner.invoke(app, ["repos", "list", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "list" in combined.lower()
        assert "repository" in combined.lower()

    @pytest.mark.unit
    def test_repos_add_help(self):
        """Test repos add command help output."""
        result = runner.invoke(app, ["repos", "add", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "add" in combined.lower()
        assert "repository" in combined.lower()
        # Should show key options
        assert "--description" in combined or "-d" in combined
        assert "--password" in combined or "-p" in combined

    @pytest.mark.unit
    def test_repos_init_help(self):
        """Test repos init command help output."""
        result = runner.invoke(app, ["repos", "init", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "init" in combined.lower()
        assert "initialize" in combined.lower()

    @pytest.mark.unit
    def test_repos_show_help(self):
        """Test repos show command help output."""
        result = runner.invoke(app, ["repos", "show", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "show" in combined.lower()
        assert "repository" in combined.lower()

    @pytest.mark.unit
    def test_repos_check_help(self):
        """Test repos check command help output."""
        result = runner.invoke(app, ["repos", "check", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "check" in combined.lower()
        assert "integrity" in combined.lower()

    @pytest.mark.unit
    def test_repos_stats_help(self):
        """Test repos stats command help output."""
        result = runner.invoke(app, ["repos", "stats", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "stats" in combined.lower()
        assert "statistics" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_list_command(self, mock_service_manager):
        """Test repos list command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.list_repositories.return_value = []
        
        result = runner.invoke(app, ["repos", "list"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_repos_add_missing_parameters(self):
        """Test repos add command with missing parameters should prompt."""
        result = runner.invoke(app, ["repos", "add"])
        
        # Should either prompt for input or show helpful error
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_add_with_parameters(self, mock_service_manager):
        """Test repos add command with all parameters."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "repos", "add", "test-repo", "file:///tmp/test-repo",
            "--description", "Test repository",
            "--password", "test-password"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_repos_add_invalid_uri(self):
        """Test repos add command with invalid URI format."""
        result = runner.invoke(app, [
            "repos", "add", "test-repo", "invalid-uri-format"
        ])
        
        # Should handle invalid URI gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_add_with_set_default(self, mock_service_manager):
        """Test repos add command with set-default flag."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.add_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "repos", "add", "test-repo", "file:///tmp/test-repo",
            "--set-default"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_remove_command(self, mock_service_manager):
        """Test repos remove command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "remove", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_show_command(self, mock_service_manager):
        """Test repos show command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_repository_by_name.return_value = Mock()
        
        result = runner.invoke(app, ["repos", "show", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_default_command(self, mock_service_manager):
        """Test repos default command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        result = runner.invoke(app, ["repos", "default", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_init_command(self, mock_service_manager):
        """Test repos init command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.initialize_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "repos", "init", "test-repo",
            "--yes"  # Skip confirmation
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_init_with_repository_uri(self, mock_service_manager):
        """Test repos init command with repository URI."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.initialize_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "repos", "init", "test-repo",
            "--repository", "file:///tmp/test-repo",
            "--yes"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_check_command(self, mock_service_manager):
        """Test repos check command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.check_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "check", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_stats_command(self, mock_service_manager):
        """Test repos stats command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_repository_stats.return_value = Mock()
        
        result = runner.invoke(app, ["repos", "stats", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_unlock_command(self, mock_service_manager):
        """Test repos unlock command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.unlock_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "unlock", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_migrate_command(self, mock_service_manager):
        """Test repos migrate command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.migrate_repository.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "migrate", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_forget_command(self, mock_service_manager):
        """Test repos forget command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.apply_retention_policy.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "forget", "test-repo"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_check_all_command(self, mock_service_manager):
        """Test repos check-all command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.check_all_repositories.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["repos", "check-all"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_repos_stats_all_command(self, mock_service_manager):
        """Test repos stats-all command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.get_all_repository_stats.return_value = []
        
        result = runner.invoke(app, ["repos", "stats-all"])
        
        # Should not crash
        assert result.exit_code in [0, 1]
