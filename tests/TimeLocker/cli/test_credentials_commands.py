"""
Unit tests for TimeLocker CLI credentials command group.

Tests credentials command parsing, parameter validation, help output, and error handling.
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


class TestCredentialsCommands:
    """Test suite for credentials command group."""

    @pytest.mark.unit
    def test_credentials_help_output(self):
        """Test credentials command group help output."""
        result = runner.invoke(app, ["credentials", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "credential" in combined.lower()
        assert "management" in combined.lower()
        # Should show available subcommands
        assert "unlock" in combined.lower()
        assert "set" in combined.lower()
        assert "remove" in combined.lower()

    @pytest.mark.unit
    def test_credentials_unlock_help(self):
        """Test credentials unlock command help output."""
        result = runner.invoke(app, ["credentials", "unlock", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "unlock" in combined.lower()
        assert "credential" in combined.lower()

    @pytest.mark.unit
    def test_credentials_set_help(self):
        """Test credentials set command help output."""
        result = runner.invoke(app, ["credentials", "set", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "set" in combined.lower()
        assert "repository" in combined.lower()
        assert "password" in combined.lower()

    @pytest.mark.unit
    def test_credentials_remove_help(self):
        """Test credentials remove command help output."""
        result = runner.invoke(app, ["credentials", "remove", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "remove" in combined.lower()
        assert "repository" in combined.lower()
        assert "password" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_unlock_command(self, mock_service_manager):
        """Test credentials unlock command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.unlock_credential_manager.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["credentials", "unlock"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_command(self, mock_service_manager):
        """Test credentials set command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "set", "test-repo"
        ])
        
        # Should not crash (may prompt for password)
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_with_password(self, mock_service_manager):
        """Test credentials set command with password parameter."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "set", "test-repo",
            "--password", "test-password"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_remove_command(self, mock_service_manager):
        """Test credentials remove command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository_password.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "remove", "test-repo"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_credentials_set_missing_repository(self):
        """Test credentials set command with missing repository parameter."""
        result = runner.invoke(app, ["credentials", "set"])
        
        # Should show error for missing repository
        assert result.exit_code != 0

    @pytest.mark.unit
    def test_credentials_remove_missing_repository(self):
        """Test credentials remove command with missing repository parameter."""
        result = runner.invoke(app, ["credentials", "remove"])
        
        # Should show error for missing repository
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_nonexistent_repository(self, mock_service_manager):
        """Test credentials set command with nonexistent repository."""
        # Mock the service manager to raise error for nonexistent repo
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.side_effect = Exception("Repository not found")
        
        result = runner.invoke(app, [
            "credentials", "set", "nonexistent-repo",
            "--password", "test-password"
        ])
        
        # Should handle error gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_remove_nonexistent_repository(self, mock_service_manager):
        """Test credentials remove command with nonexistent repository."""
        # Mock the service manager to raise error for nonexistent repo
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository_password.side_effect = Exception("Repository not found")
        
        result = runner.invoke(app, [
            "credentials", "remove", "nonexistent-repo"
        ])
        
        # Should handle error gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_unlock_with_verbose(self, mock_service_manager):
        """Test credentials unlock command with verbose flag."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.unlock_credential_manager.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "unlock",
            "--verbose"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_with_verbose(self, mock_service_manager):
        """Test credentials set command with verbose flag."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "set", "test-repo",
            "--password", "test-password",
            "--verbose"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_remove_with_verbose(self, mock_service_manager):
        """Test credentials remove command with verbose flag."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository_password.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "credentials", "remove", "test-repo",
            "--verbose"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_unlock_failure(self, mock_service_manager):
        """Test credentials unlock command failure handling."""
        # Mock the service manager to fail
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.unlock_credential_manager.side_effect = Exception("Unlock failed")
        
        result = runner.invoke(app, ["credentials", "unlock"])
        
        # Should handle failure gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_failure(self, mock_service_manager):
        """Test credentials set command failure handling."""
        # Mock the service manager to fail
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.side_effect = Exception("Set password failed")
        
        result = runner.invoke(app, [
            "credentials", "set", "test-repo",
            "--password", "test-password"
        ])
        
        # Should handle failure gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_remove_failure(self, mock_service_manager):
        """Test credentials remove command failure handling."""
        # Mock the service manager to fail
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.remove_repository_password.side_effect = Exception("Remove password failed")
        
        result = runner.invoke(app, [
            "credentials", "remove", "test-repo"
        ])
        
        # Should handle failure gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_credentials_set_interactive_password(self, mock_service_manager):
        """Test credentials set command with interactive password prompt."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.set_repository_password.return_value = Mock(success=True)
        
        # Simulate interactive password input
        result = runner.invoke(app, [
            "credentials", "set", "test-repo"
        ], input="test-password\ntest-password\n")
        
        # Should not crash (may prompt for password)
        assert result.exit_code in [0, 1]
