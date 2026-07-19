"""
Unit tests for TimeLocker CLI schedule command group.

Tests schedule command parsing, parameter validation, help output, and error handling.
"""

import json
import shlex
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from TimeLocker.cli import app
from TimeLocker.cli_modules.commands.schedule import (
    _build_backup_command,
    _generate_cron_script,
    _generate_systemd_script,
    _generate_windows_script,
)
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
            "schedule", "create", "test-schedule",
            "--repository", "test-repo", "--source", ".",
            "--frequency", "daily"
        ])
        # Should succeed or fail gracefully (policy might not exist)
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_generated_backup_command_parses_current_cli(self, tmp_path):
        schedule = {
            "repository": "pilot-repo",
            "sources": [str(tmp_path / "source")],
            "selection": None,
            "config_dir": str(tmp_path / "config"),
        }

        argv = shlex.split(_build_backup_command(schedule))
        result = runner.invoke(app, argv[1:] + ["--help"])

        assert_success(result)
        assert "--policy" not in argv
        assert "--non-interactive" not in argv
        assert argv[-2:] == ["--config-dir", str((tmp_path / "config").resolve())]

    @pytest.mark.unit
    def test_generated_backup_command_preserves_migration_parity_fields(self, tmp_path):
        schedule = {
            "repository": "pilot repo",
            "sources": [str(tmp_path / "source with spaces")],
            "selection": None,
            "tags": ["Bruce-5560", "tag with spaces"],
            "exclude_patterns": ["cache/*", "name;still-an-argument"],
            "compression": "max",
            "one_file_system": True,
        }

        command = _build_backup_command(schedule)
        argv = shlex.split(command)

        assert argv.count("--tags") == 2
        assert argv.count("--exclude") == 2
        assert argv[argv.index("--compression") + 1] == "max"
        assert argv.count("--one-file-system") == 1
        assert "tag with spaces" in argv
        assert "name;still-an-argument" in argv

        cron = _generate_cron_script("pilot", schedule)
        service, _ = _generate_systemd_script("pilot", {
            **schedule,
            "cron_expression": "0 2 * * *",
        })
        windows = _generate_windows_script("pilot", {
            **schedule,
            "cron_expression": "0 2 * * *",
        })
        for rendered in (cron, service, windows):
            assert "--compression max" in rendered
            assert "--one-file-system" in rendered

    @pytest.mark.unit
    def test_generated_backup_command_preserves_legacy_defaults(self, tmp_path):
        argv = shlex.split(_build_backup_command({
            "repository": "pilot-repo",
            "sources": [str(tmp_path)],
            "selection": None,
        }))

        assert "--compression" not in argv
        assert "--one-file-system" not in argv
        assert "--tags" not in argv
        assert "--exclude" not in argv

    @pytest.mark.unit
    @patch('TimeLocker.cli_modules.commands.schedule._get_schedule_storage_dir')
    def test_schedule_create_edit_show_and_list_parity_fields(
            self, mock_storage_dir: Mock, tmp_path
    ):
        """Stored schedule commands expose and update all migration fields."""
        mock_storage_dir.return_value = tmp_path
        source = tmp_path / "source"
        source.mkdir()

        create = runner.invoke(app, [
            "schedule", "create", "migration",
            "--repository", "pilot-repo",
            "--source", str(source),
            "--frequency", "daily",
            "--tags", "Bruce-5560",
            "--exclude", "cache/*",
            "--compression", "max",
            "--one-file-system",
        ])
        assert_success(create)

        stored = json.loads((tmp_path / "schedules.json").read_text())['migration']
        assert stored['tags'] == ['Bruce-5560']
        assert stored['exclude_patterns'] == ['cache/*']
        assert stored['compression'] == 'max'
        assert stored['one_file_system'] is True

        edit = runner.invoke(app, [
            "schedule", "edit", "migration",
            "--tags", "replacement",
            "--exclude", "*.tmp",
            "--compression", "off",
            "--cross-filesystems",
        ])
        assert_success(edit)
        stored = json.loads((tmp_path / "schedules.json").read_text())['migration']
        assert stored['tags'] == ['replacement']
        assert stored['exclude_patterns'] == ['*.tmp']
        assert stored['compression'] == 'off'
        assert stored['one_file_system'] is False

        shown = runner.invoke(app, ["schedule", "show", "migration"])
        listed = runner.invoke(app, ["schedule", "list"])
        assert_success(shown)
        assert_success(listed)
        assert "Compression:" in combined_output(shown)
        assert "compression=off" in combined_output(listed)

    @pytest.mark.unit
    def test_linux_renderers_reference_environment_without_secret_values(self, tmp_path):
        env_file = tmp_path / "pilot.env"
        schedule = {
            "repository": "pilot-repo",
            "selection": "protected-files",
            "sources": [],
            "environment_file": str(env_file),
            "config_dir": str(tmp_path / "config"),
            "system": True,
            "cron_expression": "0 2 * * *",
            "frequency": "daily",
        }

        cron = _generate_cron_script("pilot", schedule)
        service, timer = _generate_systemd_script("pilot", schedule)

        assert str(env_file) in cron
        assert f"EnvironmentFile={env_file}" in service
        assert "set -euo pipefail" in cron
        assert "User=root" in service
        assert "backup create --selection protected-files" in cron
        assert "--repository pilot-repo" in service
        assert "RESTIC_PASSWORD=" not in cron + service + timer

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
