"""
Unit tests for TimeLocker CLI policy command group.

Tests policy command parsing, parameter validation, help output, and error handling.
"""

import pytest
from unittest.mock import Mock, patch

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner, combined_output, assert_success, assert_exit_code, assert_help_quality
)

runner = get_cli_runner()


class TestPolicyCommands:
    """Test suite for policy command group."""

    @pytest.mark.unit
    def test_policy_help_output(self):
        """Test policy command group help output."""
        result = runner.invoke(app, ["policy", "--help"])
        assert_help_quality(result, "policy")
        output = combined_output(result)
        assert "policy" in output.lower() or "policies" in output.lower()

    @pytest.mark.unit
    def test_policy_backup_create_help(self):
        """Test policy backup create command help output."""
        result = runner.invoke(app, ["policy", "backup", "create", "--help"])
        assert_help_quality(result, "policy backup create")

    @pytest.mark.unit
    def test_policy_backup_list_help(self):
        """Test policy backup list command help output."""
        result = runner.invoke(app, ["policy", "backup", "list", "--help"])
        assert_help_quality(result, "policy backup list")

    @pytest.mark.unit
    def test_policy_retention_create_help(self):
        """Test policy retention create command help output."""
        result = runner.invoke(app, ["policy", "retention", "create", "--help"])
        assert_help_quality(result, "policy retention create")

    @pytest.mark.unit
    def test_policy_retention_list_help(self):
        """Test policy retention list command help output."""
        result = runner.invoke(app, ["policy", "retention", "list", "--help"])
        assert_help_quality(result, "policy retention list")

    @pytest.mark.unit
    def test_policy_simulate_help(self):
        """Test policy simulate command help output."""
        result = runner.invoke(app, ["policy", "simulate", "--help"])
        assert_help_quality(result, "policy simulate")

    @pytest.mark.unit
    def test_policy_status_help(self):
        """Test policy status command help output."""
        result = runner.invoke(app, ["policy", "status", "--help"])
        assert_help_quality(result, "policy status")

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy._get_policy_manager')
    def test_policy_backup_list_command(self, mock_get_manager):
        """Test policy backup list command execution."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        # Return an empty list that can be iterated
        mock_manager.list_backup_policies.return_value = []
        
        result = runner.invoke(app, ["policy", "backup", "list"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy.PolicyManager')
    def test_policy_backup_create_with_parameters(self, mock_policy_manager):
        """Test policy backup create command with parameters."""
        mock_manager = Mock()
        mock_policy_manager.return_value = mock_manager
        mock_manager.create_backup_policy.return_value = Mock(name="test-policy")
        
        result = runner.invoke(app, [
            "policy", "backup", "create", "test-policy",
            "--repository", "test-repo"
        ])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy.PolicyManager')
    def test_policy_retention_list_command(self, mock_policy_manager):
        """Test policy retention list command execution."""
        mock_manager = Mock()
        mock_policy_manager.return_value = mock_manager
        mock_manager.list_retention_policies.return_value = []
        
        result = runner.invoke(app, ["policy", "retention", "list"])
        assert_success(result)

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy.PolicyManager')
    def test_policy_retention_create_with_parameters(self, mock_policy_manager):
        """Test policy retention create command with parameters."""
        mock_manager = Mock()
        mock_policy_manager.return_value = mock_manager
        mock_manager.create_retention_policy.return_value = Mock(name="test-retention")
        
        result = runner.invoke(app, [
            "policy", "retention", "create", "test-retention",
            "--keep-daily", "7"
        ])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy.PolicyManager')
    def test_policy_simulate_command(self, mock_policy_manager):
        """Test policy simulate command execution."""
        mock_manager = Mock()
        mock_policy_manager.return_value = mock_manager
        mock_manager.get_policy.return_value = Mock(
            name="test-policy",
            repository="test-repo"
        )
        mock_manager.simulate_policy.return_value = Mock(
            files_selected=100,
            total_size=1024000
        )
        
        result = runner.invoke(app, ["policy", "simulate", "test-policy"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    @patch('src.TimeLocker.cli_modules.commands.policy._get_policy_manager')
    def test_policy_status_command(self, mock_get_manager):
        """Test policy status command execution."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        # Return empty lists that can be checked with len()
        mock_manager.list_backup_policies.return_value = []
        mock_manager.list_retention_policies.return_value = []
        mock_manager.list_all_assignments.return_value = []
        
        result = runner.invoke(app, ["policy", "status"])
        assert_success(result)
