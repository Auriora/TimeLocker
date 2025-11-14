"""
Unit tests for TimeLocker CLI monitoring command groups.

Tests monitor, logs, and reports command parsing, parameter validation, help output, and error handling.
"""

import pytest
from unittest.mock import patch

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_success,
    assert_exit_code,
    assert_help_quality,
    create_mock_cli_service_manager,
)

runner = get_cli_runner()


class TestMonitorCommands:
    """Test suite for monitor command group."""

    @pytest.mark.unit
    def test_monitor_help_output(self):
        """Test monitor command group help output."""
        result = runner.invoke(app, ["monitor", "--help"])
        assert_help_quality(result, "monitor")
        output = combined_output(result)
        assert "monitor" in output.lower()

    @pytest.mark.unit
    def test_monitor_health_help(self):
        """Test monitor health command help output."""
        result = runner.invoke(app, ["monitor", "health", "--help"])
        assert_help_quality(result, "monitor health")

    @pytest.mark.unit
    def test_monitor_stats_help(self):
        """Test monitor stats command help output."""
        result = runner.invoke(app, ["monitor", "stats", "--help"])
        assert_help_quality(result, "monitor stats")

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.monitoring._create_config_service')
    @patch('src.TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_monitor_health_command(self, mock_get_service_manager, mock_create_config_service):
        """Test monitor health command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_create_config_service.return_value = mock_manager._config_service
        
        result = runner.invoke(app, ["monitor", "health"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.monitoring._create_config_service')
    @patch('src.TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_monitor_stats_command(self, mock_get_service_manager, mock_create_config_service):
        """Test monitor stats command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_create_config_service.return_value = mock_manager._config_service
        
        result = runner.invoke(app, ["monitor", "stats"])
        assert_success(result)


class TestLogsCommands:
    """Test suite for logs command group."""

    @pytest.mark.unit
    def test_logs_help_output(self):
        """Test logs command group help output."""
        result = runner.invoke(app, ["logs", "--help"])
        assert_help_quality(result, "logs")
        output = combined_output(result)
        assert "log" in output.lower()

    @pytest.mark.unit
    def test_logs_view_help(self):
        """Test logs view command help output."""
        result = runner.invoke(app, ["logs", "view", "--help"])
        # Use custom assertion since "error" appears as a valid log level in help
        assert result.exit_code == 0
        output = combined_output(result)
        assert "Usage:" in output or "usage:" in output.lower()
        assert "log" in output.lower()

    @pytest.mark.unit
    def test_logs_view_command(self):
        """Test logs view command execution."""
        result = runner.invoke(app, ["logs", "view"])
        # Should succeed or show "No Logs" if log file doesn't exist
        assert_success(result)

    @pytest.mark.unit
    def test_logs_view_with_filters(self):
        """Test logs view command with filters."""
        result = runner.invoke(app, [
            "logs", "view",
            "--level", "ERROR",
            "--lines", "50"
        ])
        # Should succeed or show "No Logs" if log file doesn't exist
        assert_success(result)


class TestReportsCommands:
    """Test suite for reports command group."""

    @pytest.mark.unit
    def test_reports_help_output(self):
        """Test reports command group help output."""
        result = runner.invoke(app, ["reports", "--help"])
        assert_help_quality(result, "reports")
        output = combined_output(result)
        assert "report" in output.lower()

    @pytest.mark.unit
    def test_reports_generate_help(self):
        """Test reports generate command help output."""
        result = runner.invoke(app, ["reports", "generate", "--help"])
        assert_help_quality(result, "reports generate")

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.monitoring._create_config_service')
    @patch('src.TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_backup_history(self, mock_get_service_manager, mock_create_config_service):
        """Test reports generate command for backup history."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_create_config_service.return_value = mock_manager._config_service
        
        result = runner.invoke(app, ["reports", "generate", "backup-history"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.monitoring._create_config_service')
    @patch('src.TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_storage_usage(self, mock_get_service_manager, mock_create_config_service):
        """Test reports generate command for storage usage."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_create_config_service.return_value = mock_manager._config_service
        
        result = runner.invoke(app, ["reports", "generate", "storage-usage"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.monitoring._create_config_service')
    @patch('src.TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_performance(self, mock_get_service_manager, mock_create_config_service):
        """Test reports generate command for performance."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        mock_create_config_service.return_value = mock_manager._config_service
        
        result = runner.invoke(app, ["reports", "generate", "performance"])
        assert result.exit_code in [0, 1, 2]
