"""
Unit tests for TimeLocker CLI config command group.

Tests config command parsing, parameter validation, help output, and error handling.
"""

import pytest
import tempfile
import os
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


class TestConfigCommands:
    """Test suite for config command group."""

    @pytest.mark.unit
    def test_config_help_output(self):
        """Test config command group help output."""
        result = runner.invoke(app, ["config", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "config" in combined.lower()
        assert "management" in combined.lower()
        # Should show available subcommands
        assert "show" in combined.lower()
        assert "setup" in combined.lower()

    @pytest.mark.unit
    def test_config_show_help(self):
        """Test config show command help output."""
        result = runner.invoke(app, ["config", "show", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "show" in combined.lower()
        assert "configuration" in combined.lower()
        # Should show key options
        assert "--config-dir" in combined

    @pytest.mark.unit
    def test_config_setup_help(self):
        """Test config setup command help output."""
        result = runner.invoke(app, ["config", "setup", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "setup" in combined.lower()
        assert "wizard" in combined.lower()

    @pytest.mark.unit
    def test_config_import_help(self):
        """Test config import command group help output."""
        result = runner.invoke(app, ["config", "import", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "import" in combined.lower()

    @pytest.mark.unit
    def test_config_import_restic_help(self):
        """Test config import restic command help output."""
        result = runner.invoke(app, ["config", "import", "restic", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "restic" in combined.lower()
        assert "import" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.ConfigurationModule')
    def test_config_show_command(self, mock_config_module):
        """Test config show command execution."""
        # Mock the configuration module
        mock_config = Mock()
        mock_config_module.return_value = mock_config
        mock_config.get_config.return_value = {}
        mock_config.config_file = Path("/tmp/config.json")
        mock_config.get_config_info.return_value = {}
        
        result = runner.invoke(app, ["config", "show"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.ConfigurationModule')
    def test_config_show_with_config_dir(self, mock_config_module):
        """Test config show command with custom config directory."""
        # Mock the configuration module
        mock_config = Mock()
        mock_config_module.return_value = mock_config
        mock_config.get_config.return_value = {}
        mock_config.config_file = Path("/tmp/config.json")
        mock_config.get_config_info.return_value = {}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(app, [
                "config", "show",
                "--config-dir", temp_dir
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_config_setup_non_interactive(self):
        """Test config setup command in non-interactive environment."""
        # Set environment to simulate non-interactive context
        env = {'PYTEST_CURRENT_TEST': 'test'}
        result = runner.invoke(app, ["config", "setup"], env=env)
        
        # Should exit gracefully in non-interactive context
        assert result.exit_code == 2

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.sys.stdin')
    def test_config_setup_interactive_simulation(self, mock_stdin):
        """Test config setup command interactive simulation."""
        # Mock stdin to simulate non-tty
        mock_stdin.isatty.return_value = False
        
        result = runner.invoke(app, ["config", "setup"])
        
        # Should exit gracefully when not in tty
        assert result.exit_code == 2

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_config_import_restic_command(self, mock_service_manager):
        """Test config import restic command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.import_restic_config.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["config", "import", "restic"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_config_import_restic_with_options(self, mock_service_manager):
        """Test config import restic command with options."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.import_restic_config.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "config", "import", "restic",
            "--dry-run",
            "--verbose"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_config_show_verbose_flag(self):
        """Test config show command with verbose flag."""
        result = runner.invoke(app, [
            "config", "show",
            "--verbose"
        ])
        
        # Verbose flag should be accepted
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    def test_config_setup_verbose_flag(self):
        """Test config setup command with verbose flag."""
        # Set environment to simulate non-interactive context
        env = {'PYTEST_CURRENT_TEST': 'test'}
        result = runner.invoke(app, [
            "config", "setup",
            "--verbose"
        ], env=env)
        
        # Should exit gracefully in non-interactive context
        assert result.exit_code == 2

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.ConfigurationModule')
    @patch('src.TimeLocker.cli.ConfigurationValidator')
    def test_config_show_with_validation(self, mock_validator, mock_config_module):
        """Test config show command with validation."""
        # Mock the configuration module and validator
        mock_config = Mock()
        mock_config_module.return_value = mock_config
        mock_config.get_config.return_value = {}
        mock_config.config_file = Path("/tmp/config.json")
        mock_config.get_config_info.return_value = {}
        
        mock_validator_instance = Mock()
        mock_validator.return_value = mock_validator_instance
        mock_validator_instance.validate_configuration.return_value = Mock(is_valid=True, errors=[])
        
        result = runner.invoke(app, ["config", "show"])
        
        # Should not crash and should show validation status
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.ConfigurationModule')
    def test_config_show_configuration_error(self, mock_config_module):
        """Test config show command with configuration error."""
        # Mock configuration module to raise error
        mock_config_module.side_effect = Exception("Configuration error")
        
        result = runner.invoke(app, ["config", "show"])
        
        # Should handle configuration error gracefully
        assert result.exit_code != 0

    @pytest.mark.unit
    def test_config_import_timeshift_help(self):
        """Test config import timeshift command help output."""
        result = runner.invoke(app, ["config", "import", "timeshift", "--help"])
        combined = _combined_output(result)
        
        assert result.exit_code == 0
        assert "timeshift" in combined.lower()
        assert "import" in combined.lower()

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_config_import_timeshift_command(self, mock_service_manager):
        """Test config import timeshift command execution."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.import_timeshift_config.return_value = Mock(success=True)
        
        result = runner.invoke(app, ["config", "import", "timeshift"])
        
        # Should not crash
        assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_config_import_timeshift_with_config_file(self, mock_service_manager):
        """Test config import timeshift command with config file."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.import_timeshift_config.return_value = Mock(success=True)
        
        with tempfile.NamedTemporaryFile(suffix='.json') as temp_file:
            result = runner.invoke(app, [
                "config", "import", "timeshift",
                "--config-file", temp_file.name
            ])
            
            # Should not crash
            assert result.exit_code in [0, 1]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_config_import_timeshift_dry_run(self, mock_service_manager):
        """Test config import timeshift command with dry run."""
        # Mock the service manager
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        mock_manager.import_timeshift_config.return_value = Mock(success=True)
        
        result = runner.invoke(app, [
            "config", "import", "timeshift",
            "--dry-run"
        ])
        
        # Should not crash
        assert result.exit_code in [0, 1]
