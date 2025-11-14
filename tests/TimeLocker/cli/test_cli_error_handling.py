"""
Error path and validation tests for TimeLocker CLI.

Tests common error scenarios, parameter validation failures, and error message quality.

Exit code expectations:
- Usage/Click parsing errors -> exit code 2
- Handled application validation / operational errors -> exit code 1
- Success -> exit code 0
- KeyboardInterrupt -> exit code 130
Some environment-dependent scenarios (e.g., restricted paths) may yield 1 (handled error)
or 2 (usage/permission abstraction) depending on local filesystem semantics; these are
explicitly documented where a range is allowed.
"""

import pytest
import tempfile
import re
from pathlib import Path
from unittest.mock import Mock, patch

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
        get_cli_runner,
        combined_output,
        assert_success,
        assert_exit_code,
        patch_restore_commands,
)

# Set wider terminal width to prevent help text truncation in CI
runner = get_cli_runner()


class TestCLIErrorHandling:
    """Test suite for CLI error handling and validation."""

    @pytest.mark.unit
    def test_invalid_command_error(self):
        result = runner.invoke(app, ["invalid-command"])
        combined = combined_output(result)
        assert result.exit_code != 0
        assert len(combined) > 10
        assert "traceback" not in combined.lower()

    @pytest.mark.unit
    def test_invalid_subcommand_error(self):
        invalid_subcommands = [
                ["backup", "invalid-subcmd"],
                ["snapshots", "invalid-subcmd"],
                ["repos", "invalid-subcmd"],
                ["selections", "invalid-subcmd"],
                ["config", "invalid-subcmd"],
                ["credentials", "invalid-subcmd"]
        ]
        for cmd in invalid_subcommands:
            result = runner.invoke(app, cmd)
            combined = combined_output(result)
            assert result.exit_code != 0, f"Invalid subcommand should fail: {' '.join(cmd)}"
            assert len(combined) > 10, f"Should show error message for: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_missing_required_arguments(self):
        missing_arg_commands = [
                ["snapshots", "show"],
                ["restore", "browse"],
                ["restore", "mount"],
                ["restore", "full"],
                ["repos", "init"],
                ["repos", "show"],
                ["repos", "check"],
                ["repos", "stats"],
                ["selections", "show"],
                ["selections", "delete"],
                ["credentials", "store"],
                ["credentials", "remove"]
        ]
        for cmd in missing_arg_commands:
            result = runner.invoke(app, cmd)
            combined = combined_output(result)
            # Click usage error expected -> exit code 2
            assert_exit_code(result, 2, f"Missing args should yield usage error: {' '.join(cmd)}")
            assert len(combined) > 10

    @pytest.mark.unit
    def test_invalid_snapshot_id_validation(self):
        invalid_snapshot_ids = [
                "bad$$id",
                "short",
                "spaces in id",
                "special!@#chars",
                "",
                "123"
        ]
        snapshot_commands = ["show", "forget"]
        with patch_restore_commands(mode="invalid_snapshot"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                mount_path = Path(tmp_dir) / "mount"
                mount_path.mkdir()
                target_path = Path(tmp_dir) / "target"
                target_path.mkdir()

                for snapshot_id in invalid_snapshot_ids:
                    for cmd in snapshot_commands:
                        result = runner.invoke(app, ["snapshots", cmd, snapshot_id])
                        combined = combined_output(result)
                        assert result.exit_code != 0, f"Invalid snapshot ID should fail: {snapshot_id} in snapshots {cmd}"
                        assert re.search(r"invalid.*format", combined, re.IGNORECASE), f"Should mention invalid format for {snapshot_id} in snapshots {cmd}"

                    restore_commands = [
                            ["restore", "browse", "test-repo", snapshot_id],
                            ["restore", "full", "test-repo", snapshot_id, str(target_path)],
                            ["restore", "files", "test-repo", snapshot_id, "/var/log/syslog", "--target", str(target_path)],
                            ["restore", "mount", "test-repo", snapshot_id, str(mount_path)],
                    ]
                    if snapshot_id.strip():
                        restore_commands.append(
                                ["restore", "find", "test-repo", "*.txt", "--snapshot", snapshot_id]
                        )
                    for command in restore_commands:
                        result = runner.invoke(app, command)
                        combined = combined_output(result)
                        assert result.exit_code != 0, f"Invalid snapshot ID should fail: {' '.join(command)}"
                        assert "invalid snapshot id" in combined.lower(), f"Should mention invalid snapshot ID for {' '.join(command)}"

    @pytest.mark.unit
    def test_invalid_repository_uri_validation(self):
        invalid_uris = [
                "not-a-uri",
                "invalid://bad-scheme",
                "file://relative/path",
                "s3://",
                "http://example.com/repo",
                ""
        ]
        for uri in invalid_uris:
            result = runner.invoke(app, ["repos", "add", "test-repo", uri])
            assert result.exit_code != 0, f"Invalid URI should fail: {uri}"

    @pytest.mark.unit
    def test_nonexistent_file_paths(self):
        nonexistent_paths = [
                "/nonexistent/path",
                "/tmp/does/not/exist",
                "~/nonexistent/directory"
        ]
        for path in nonexistent_paths:
            result = runner.invoke(app, ["backup", "create", path, "--dry-run"])
            # Handled error -> exit code 1
            assert_exit_code(result, 1, f"Should handle nonexistent path with handled error: {path}")

    @pytest.mark.unit
    def test_permission_denied_simulation(self):
        restricted_paths = [
                "/root/restricted",
                "/etc/shadow",
                "/proc/1/mem"
        ]
        for path in restricted_paths:
            result = runner.invoke(app, ["backup", "create", path, "--dry-run"])
            # Expected handled error (1) but some platforms may surface as usage/permission (2)
            assert result.exit_code in (1, 2), f"Restricted path should yield handled or usage error: {path} (got {result.exit_code})"

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_service_manager_exceptions(self, mock_service_manager):
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        exceptions_to_test = [
                Exception("Generic error"),
                ValueError("Invalid value"),
                FileNotFoundError("File not found"),
                PermissionError("Permission denied"),
                ConnectionError("Network error")
        ]
        for exception in exceptions_to_test:
            mock_manager.list_repositories.side_effect = exception
            result = runner.invoke(app, ["repos", "list"])
            combined = combined_output(result)
            assert result.exit_code != 0, f"Should fail on exception: {type(exception).__name__}"
            assert len(combined) > 10
            assert "traceback" not in combined.lower()
            mock_manager.reset_mock()

    @pytest.mark.unit
    @pytest.mark.skip(reason="Test needs refactoring - backup command architecture has changed and mocking strategy no longer works. KeyboardInterrupt handling is implemented but test needs to be rewritten to properly inject the interrupt.")
    def test_keyboard_interrupt_handling(self):
        # TODO: Rewrite this test to properly test KeyboardInterrupt handling
        # The backup create command now has a complex initialization path that makes
        # it difficult to inject KeyboardInterrupt via mocking. Consider:
        # 1. Testing KeyboardInterrupt at a lower level (service layer)
        # 2. Using a simpler command for testing interrupt handling
        # 3. Refactoring backup command to make it more testable
        with patch('TimeLocker.cli_services.get_cli_service_manager') as mock_get_service:
            with patch('TimeLocker.cli._get_service_manager_for_command') as mock_get_for_command:
                mock_manager = Mock()
                mock_config_service = Mock()
                mock_manager._config_service = mock_config_service
                mock_get_service.return_value = mock_manager
                mock_get_for_command.return_value = mock_manager
                # Make execute_backup raise KeyboardInterrupt
                mock_manager.execute_backup.side_effect = KeyboardInterrupt()
                # Also make execute_backup_from_cli raise KeyboardInterrupt in case that's called
                mock_manager.execute_backup_from_cli.side_effect = KeyboardInterrupt()
                result = runner.invoke(app, ["backup", "create", "/tmp", "--dry-run"])
                assert_exit_code(result, 130, "KeyboardInterrupt should map to exit code 130")

    @pytest.mark.unit
    def test_invalid_option_values(self):
        invalid_option_scenarios = [
                ["snapshots", "find", "*.txt", "--limit", "-1"],
                ["snapshots", "find", "*.txt", "--limit", "not-a-number"],
                ["snapshots", "find", "*.txt", "--type", "invalid-type"],
                ["backup", "create", "/tmp", "--verbose", "invalid"]
        ]
        for cmd in invalid_option_scenarios:
            result = runner.invoke(app, cmd)
            assert result.exit_code != 0, f"Invalid option should fail: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_conflicting_options(self):
        conflicting_scenarios = [
                ["backup", "create"],  # missing sources or selection should fail
                ["backup", "verify", "--snapshot", "abc123", "--latest"]  # hypothetical conflict -> expect non-zero
        ]
        for cmd in conflicting_scenarios:
            result = runner.invoke(app, cmd)
            # Expect non-zero due to conflict / invalid combination
            assert result.exit_code != 0, f"Conflicting options should fail: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_empty_input_handling(self):
        empty_input_scenarios = [
                ["repos", "add", "", "file:///tmp/repo"],
                ["repos", "add", "   ", "file:///tmp/repo"],
                ["selections", "create", "", "--paths", "/tmp"],
                ["snapshots", "find", ""],
                ["snapshots", "find", "   "]
        ]
        for cmd in empty_input_scenarios:
            result = runner.invoke(app, cmd)
            # Empty inputs should be validation or usage errors (1 or 2); treat any non-zero as acceptable
            assert result.exit_code != 0, f"Empty input should not succeed: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_very_long_input_handling(self):
        very_long_string = "a" * 1000
        long_input_scenarios = [
                ["repos", "add", very_long_string, "file:///tmp/repo"],
                ["selections", "create", very_long_string, "--paths", "/tmp"],
                ["snapshots", "find", very_long_string]
        ]
        for cmd in long_input_scenarios:
            result = runner.invoke(app, cmd)
            # Long inputs should not crash; success (0) or handled error (1/2) acceptable? We require non-crash
            assert result.exit_code in (0, 1, 2), f"Long input produced unexpected exit: {cmd[:2]}"

    @pytest.mark.unit
    def test_unicode_input_handling(self):
        unicode_inputs = [
                "测试仓库",
                "тест",
                "🚀backup",
                "cafre-repo",  # intentionally malformed accent sequence
                "repo/with\\slashes"
        ]
        for unicode_input in unicode_inputs:
            result = runner.invoke(app, ["repos", "add", unicode_input, "file:///tmp/repo"])
            # Expect non-zero (interactive password prompt may cause EOF) but no crash/traceback
            assert result.exit_code != 0, f"Unicode input should not silently succeed: {unicode_input}"

    @pytest.mark.unit
    def test_error_message_quality(self):
        error_scenarios = [
                {"command": ["snapshots", "show"], "expected_keywords": ["missing", "argument", "snapshot"]},
                {"command": ["repos", "add", "test", "invalid-uri"], "expected_keywords": ["invalid", "uri", "format"]},
                {"command": ["snapshots", "show", "bad$$id"], "expected_keywords": ["invalid", "snapshot", "format"]}
        ]
        for scenario in error_scenarios:
            result = runner.invoke(app, scenario["command"])
            combined = combined_output(result)
            assert result.exit_code != 0, f"Should fail: {' '.join(scenario['command'])}"
            combined_lower = combined.lower()
            for keyword in scenario["expected_keywords"]:
                assert keyword in combined_lower, f"Missing keyword '{keyword}' in error output"
            assert 10 < len(combined) < 1000

    @pytest.mark.unit
    def test_graceful_degradation(self):
        with patch('src.TimeLocker.cli.get_cli_service_manager') as mock_service_manager:
            mock_service_manager.side_effect = Exception("Service manager unavailable")
            result = runner.invoke(app, ["--help"])
            assert_success(result, "Help should work even if service manager fails")
            result = runner.invoke(app, ["backup", "--help"])
            assert_success(result, "Command help should work even if service manager fails")
