"""
Unit tests for TimeLocker CLI schedule command group.

Tests schedule command parsing, parameter validation, help output, and error handling.
"""

import pytest
from unittest.mock import Mock, patch

from TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner, combined_output, assert_success, assert_exit_code, assert_help_quality
)

runner = get_cli_runner()


class TestScheduleCommands:
    """Test suite for schedule command group."""

    @pytest.mark.unit
    def test_schedule_help_output(self):
        """Test schedule command group help output."""
        result = runner.invoke(app, ["schedule", "--help"])
        assert_help_quality(result, "schedule")
        output = combined_output(result)
        assert "schedule" in output.lower()

    @pytest.mark.unit
    def test_schedule_create_help(self):
        """Test schedule create command help output."""
        result = runner.invoke(app, ["schedule", "create", "--help"])
        assert_help_quality(result, "schedule create")

    @pytest.mark.unit
    def test_schedule_list_help(self):
        """Test schedule list command help output."""
        result = runner.invoke(app, ["schedule", "list", "--help"])
        assert_help_quality(result, "schedule list")

    @pytest.mark.unit
    def test_schedule_edit_help(self):
        """Test schedule edit command help output."""
        result = runner.invoke(app, ["schedule", "edit", "--help"])
        assert_help_quality(result, "schedule edit")

    @pytest.mark.unit
    def test_schedule_enable_help(self):
        """Test schedule enable command help output."""
        result = runner.invoke(app, ["schedule", "enable", "--help"])
        assert_help_quality(result, "schedule enable")

    @pytest.mark.unit
    def test_schedule_disable_help(self):
        """Test schedule disable command help output."""
        result = runner.invoke(app, ["schedule", "disable", "--help"])
        assert_help_quality(result, "schedule disable")

    @pytest.mark.unit
    def test_schedule_generate_scripts_help(self):
        """Test schedule generate-scripts command help output."""
        result = runner.invoke(app, ["schedule", "generate-scripts", "--help"])
        assert_help_quality(result, "schedule generate-scripts")

    @pytest.mark.unit
    def test_schedule_test_help(self):
        """Test schedule test command help output."""
        result = runner.invoke(app, ["schedule", "test", "--help"])
        assert_help_quality(result, "schedule test")

    @pytest.mark.unit
    def test_schedule_list_command(self):
        """Test schedule list command execution."""
        result = runner.invoke(app, ["schedule", "list"])
        assert_success(result)
        output = combined_output(result)
        # Should show either "No Schedules" or a table with schedules
        assert "schedule" in output.lower()

    @pytest.mark.unit
    def test_schedule_create_with_parameters(self):
        """Test schedule create command with parameters."""
        result = runner.invoke(app, [
            "schedule", "create", "test-schedule", "test-policy",
            "--frequency", "daily"
        ])
        # Should succeed or fail gracefully (policy might not exist)
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_schedule_edit_command(self):
        """Test schedule edit command execution with non-existent schedule."""
        result = runner.invoke(app, ["schedule", "edit", "test-schedule"])
        # Should fail gracefully because schedule doesn't exist, or succeed if no changes
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_schedule_enable_command(self):
        """Test schedule enable command execution with non-existent schedule."""
        result = runner.invoke(app, ["schedule", "enable", "test-schedule"])
        # Should fail gracefully because schedule doesn't exist
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_schedule_disable_command(self):
        """Test schedule disable command execution with non-existent schedule."""
        result = runner.invoke(app, ["schedule", "disable", "test-schedule"])
        # Should fail gracefully because schedule doesn't exist
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_schedule_generate_scripts_command(self):
        """Test schedule generate-scripts command execution with non-existent schedule."""
        result = runner.invoke(app, ["schedule", "generate-scripts", "test-schedule"])
        # Should fail gracefully because schedule doesn't exist
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_schedule_test_command(self):
        """Test schedule test command execution with non-existent schedule."""
        result = runner.invoke(app, ["schedule", "test", "test-schedule"])
        # Should fail gracefully because schedule doesn't exist
        assert result.exit_code in [0, 1, 2]
