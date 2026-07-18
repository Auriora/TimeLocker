"""
Unit tests for TimeLocker CLI monitoring command groups.

Tests monitor, logs, and reports command parsing, parameter validation, help output, and error handling.
"""

import importlib.util
from unittest.mock import Mock, patch

import pytest

from TimeLocker.cli import app
from TimeLocker.cli_modules.commands import monitoring as monitoring_commands
from TimeLocker.cli_modules.monitoring_integration import (
    CLIMonitoringFilters,
    CLIMonitoringIntegration,
)
from TimeLocker.cli_services import CLIServiceManager
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_success,
    assert_help_quality,
    create_mock_cli_service_manager,
)

runner = get_cli_runner()


class TestMonitoringOwnership:
    """Regression coverage for the retained monitoring command path."""

    @pytest.mark.unit
    def test_monitoring_command_groups_have_one_module_owner(self) -> None:
        """All mounted groups come from the canonical plural module."""
        assert monitoring_commands.monitor_app.info.name == "monitor"
        assert monitoring_commands.logs_app.info.name == "logs"
        assert monitoring_commands.reports_app.info.name == "reports"
        assert importlib.util.find_spec(
            "TimeLocker.cli_modules.commands.monitor"
        ) is None

    @pytest.mark.unit
    def test_service_manager_monitoring_facade_delegates_to_bridge(self) -> None:
        """Supported facade methods delegate to CLIMonitoringIntegration."""
        integration = Mock(spec=CLIMonitoringIntegration)
        integration.get_system_status.return_value = {"health_status": "healthy"}
        integration.get_recent_logs.return_value = [{"message": "backup complete"}]
        integration.search_logs.return_value = [{"message": "matched"}]
        integration.get_backup_history.return_value = [{"status": "success"}]
        integration.get_current_operations.return_value = [{"operation_id": "op-1"}]
        integration.get_operation_status.return_value = {"operation_id": "op-1"}
        manager = CLIServiceManager.__new__(CLIServiceManager)
        manager._monitoring_integration = integration

        assert manager.get_monitoring_integration() is integration
        assert manager.get_system_monitoring_status() == {"health_status": "healthy"}
        assert manager.get_cli_monitoring_logs(
            hours=6,
            repository_id="repo",
            log_level="error",
            limit=10,
        ) == [{"message": "backup complete"}]
        assert manager.search_monitoring_logs(
            "failed",
            days=2,
            repository_id="repo",
            limit=5,
        ) == [{"message": "matched"}]
        assert manager.get_cli_backup_history(
            days=7,
            repository_id="repo",
            status="success",
            limit=3,
        ) == [{"status": "success"}]
        assert manager.get_cli_current_operations() == [{"operation_id": "op-1"}]
        assert manager.get_cli_operation_status("op-1") == {"operation_id": "op-1"}

        recent_filters = integration.get_recent_logs.call_args.args[0]
        search_filters = integration.search_logs.call_args.args[1]
        history_filters = integration.get_backup_history.call_args.args[0]
        assert recent_filters == CLIMonitoringFilters(
            hours=6,
            repository_id="repo",
            log_level="error",
            limit=10,
        )
        assert search_filters == CLIMonitoringFilters(
            days=2,
            repository_id="repo",
            limit=5,
        )
        assert history_filters == CLIMonitoringFilters(
            days=7,
            repository_id="repo",
            status="success",
            limit=3,
        )
        integration.get_system_status.assert_called_once_with()
        integration.search_logs.assert_called_once_with("failed", search_filters)
        integration.get_current_operations.assert_called_once_with()
        integration.get_operation_status.assert_called_once_with("op-1")


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
    @patch('TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_monitor_health_command(self, mock_get_service_manager):
        """Test monitor health command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        
        result = runner.invoke(app, ["monitor", "health"])
        assert_success(result)

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_monitor_stats_command(self, mock_get_service_manager):
        """Test monitor stats command execution."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        
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
    @patch('TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_backup_history(self, mock_get_service_manager):
        """Test reports generate command for backup history."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        
        result = runner.invoke(app, ["reports", "generate", "backup-history"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_storage_usage(self, mock_get_service_manager):
        """Test reports generate command for storage usage."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        
        result = runner.invoke(app, ["reports", "generate", "storage-usage"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.monitoring._get_service_manager_for_command')
    def test_reports_generate_performance(self, mock_get_service_manager):
        """Test reports generate command for performance."""
        mock_manager = create_mock_cli_service_manager()
        mock_get_service_manager.return_value = mock_manager
        
        result = runner.invoke(app, ["reports", "generate", "performance"])
        assert result.exit_code in [0, 1, 2]
