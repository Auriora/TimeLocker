"""
Error path and validation tests for TimeLocker CLI.

Tests common error scenarios, parameter validation failures, and error message quality.
"""

import pytest
import tempfile
import re
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import get_cli_runner, combined_output

# Set wider terminal width to prevent help text truncation in CI
runner = get_cli_runner()


class TestCLIErrorHandling:
    """Test suite for CLI error handling and validation."""

    @pytest.mark.unit
    def test_invalid_command_error(self):
        """Test error handling for invalid commands."""
        result = runner.invoke(app, ["invalid-command"])
        combined = combined_output(result)

        assert result.exit_code != 0
        # Should show helpful error message
        assert len(combined) > 10
        # Should not crash with stack trace
        assert "traceback" not in combined.lower()

    @pytest.mark.unit
    def test_invalid_subcommand_error(self):
        """Test error handling for invalid subcommands."""
        invalid_subcommands = [
            ["backup", "invalid-subcmd"],
            ["snapshots", "invalid-subcmd"],
            ["repos", "invalid-subcmd"],
            ["targets", "invalid-subcmd"],
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
        """Test error handling for missing required arguments."""
        missing_arg_commands = [
            ["snapshots", "show"],           # Missing snapshot ID
            ["snapshots", "contents"],       # Missing snapshot ID
            ["snapshots", "mount"],          # Missing snapshot ID and path
            ["snapshots", "restore"],        # Missing snapshot ID and target
            ["repos", "init"],               # Missing repository name
            ["repos", "show"],               # Missing repository name
            ["repos", "check"],              # Missing repository name
            ["repos", "stats"],              # Missing repository name
            ["targets", "show"],             # Missing target name
            ["targets", "remove"],           # Missing target name
            ["credentials", "set"],          # Missing repository name
            ["credentials", "remove"]        # Missing repository name
        ]
        
        for cmd in missing_arg_commands:
            result = runner.invoke(app, cmd)
            combined = combined_output(result)

            assert result.exit_code != 0, f"Missing args should fail: {' '.join(cmd)}"
            assert len(combined) > 10, f"Should show error message for: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_invalid_snapshot_id_validation(self):
        """Test validation of snapshot ID format."""
        invalid_snapshot_ids = [
            "bad$$id",           # Invalid characters
            "short",             # Too short
            "spaces in id",      # Spaces
            "special!@#chars",   # Special characters
            "",                  # Empty
            "123"                # Too short
        ]
        
        snapshot_commands = [
            "show", "contents", "mount", "restore", "forget", "umount"
        ]
        
        for snapshot_id in invalid_snapshot_ids:
            for cmd in snapshot_commands:
                if cmd == "mount":
                    # Mount needs additional path argument
                    result = runner.invoke(app, ["snapshots", cmd, snapshot_id, "/tmp"])
                elif cmd == "restore":
                    # Restore needs additional target argument
                    result = runner.invoke(app, ["snapshots", cmd, snapshot_id, "/tmp"])
                else:
                    result = runner.invoke(app, ["snapshots", cmd, snapshot_id])

                combined = combined_output(result)

                assert result.exit_code != 0, f"Invalid snapshot ID should fail: {snapshot_id} in {cmd}"
                # Should mention invalid format
                assert re.search(r"invalid.*format", combined, re.IGNORECASE), \
                    f"Should mention invalid format for {snapshot_id} in {cmd}"

    @pytest.mark.unit
    def test_invalid_repository_uri_validation(self):
        """Test validation of repository URI format."""
        invalid_uris = [
            "not-a-uri",                    # No scheme
            "invalid://bad-scheme",         # Invalid scheme
            "file://relative/path",         # Relative path for file scheme
            "s3://",                        # Empty path
            "http://example.com/repo",      # Unsupported scheme
            ""                              # Empty URI
        ]
        
        for uri in invalid_uris:
            result = runner.invoke(app, [
                "repos", "add", "test-repo", uri
            ])
            combined = combined_output(result)

            # Should fail validation (exit code != 0)
            assert result.exit_code != 0, f"Invalid URI should fail: {uri}"

    @pytest.mark.unit
    def test_nonexistent_file_paths(self):
        """Test handling of nonexistent file paths."""
        nonexistent_paths = [
            "/nonexistent/path",
            "/tmp/does/not/exist",
            "~/nonexistent/directory"
        ]
        
        for path in nonexistent_paths:
            # Test backup create with nonexistent path
            result = runner.invoke(app, [
                "backup", "create", path, "--dry-run"
            ])
            # Should handle gracefully (may warn but not crash)
            assert result.exit_code in [0, 1], f"Should handle nonexistent path gracefully: {path}"

    @pytest.mark.unit
    def test_permission_denied_simulation(self):
        """Test handling of permission denied scenarios."""
        # Test with paths that would typically cause permission issues
        restricted_paths = [
            "/root/restricted",
            "/etc/shadow",
            "/proc/1/mem"
        ]
        
        for path in restricted_paths:
            result = runner.invoke(app, [
                "backup", "create", path, "--dry-run"
            ])
            # Should handle gracefully
            assert result.exit_code in [0, 1], f"Should handle restricted path gracefully: {path}"

    @pytest.mark.unit
    @patch('src.TimeLocker.cli.get_cli_service_manager')
    def test_service_manager_exceptions(self, mock_service_manager):
        """Test handling of service manager exceptions."""
        # Mock service manager to raise various exceptions
        mock_manager = Mock()
        mock_service_manager.return_value = mock_manager
        
        # Test different types of exceptions
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
            assert len(combined) > 10, f"Should show error message for: {type(exception).__name__}"
            # Should not show full stack trace to user
            assert "traceback" not in combined.lower(), f"Should not show traceback for: {type(exception).__name__}"

            # Reset mock for next iteration to ensure test isolation
            mock_manager.reset_mock()

    @pytest.mark.unit
    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupts (Ctrl+C)."""
        with patch('src.TimeLocker.cli.get_cli_service_manager') as mock_service_manager:
            mock_manager = Mock()
            mock_service_manager.return_value = mock_manager
            mock_manager.execute_backup.side_effect = KeyboardInterrupt()
            
            result = runner.invoke(app, [
                "backup", "create", "/tmp", "--dry-run"
            ])
            
            # Should handle KeyboardInterrupt gracefully
            assert result.exit_code == 130, "Should exit with code 130 for KeyboardInterrupt"

    @pytest.mark.unit
    def test_invalid_option_values(self):
        """Test handling of invalid option values."""
        invalid_option_scenarios = [
            # Invalid limit values
            ["snapshots", "find", "*.txt", "--limit", "-1"],
            ["snapshots", "find", "*.txt", "--limit", "not-a-number"],
            
            # Invalid search types
            ["snapshots", "find", "*.txt", "--type", "invalid-type"],
            
            # Invalid verbose values (if applicable)
            ["backup", "create", "/tmp", "--verbose", "invalid"]
        ]
        
        for cmd in invalid_option_scenarios:
            result = runner.invoke(app, cmd)
            combined = combined_output(result)

            # Should fail with invalid option values
            assert result.exit_code != 0, f"Invalid option should fail: {' '.join(cmd)}"
            assert len(combined) > 10, f"Should show error message for: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_conflicting_options(self):
        """Test handling of conflicting command options."""
        conflicting_scenarios = [
            # Backup with both target and direct paths
            ["backup", "create", "/tmp", "--target", "test-target"],
            
            # Verify with both snapshot and latest
            ["backup", "verify", "--snapshot", "abc123", "--latest"]
        ]
        
        for cmd in conflicting_scenarios:
            result = runner.invoke(app, cmd)
            # Should handle conflicting options gracefully
            assert result.exit_code in [0, 1], f"Should handle conflicting options: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_empty_input_handling(self):
        """Test handling of empty or whitespace-only inputs."""
        empty_input_scenarios = [
            ["repos", "add", "", "file:///tmp/repo"],      # Empty name
            ["repos", "add", "   ", "file:///tmp/repo"],   # Whitespace name
            ["targets", "add", "", "--path", "/tmp"],       # Empty target name
            ["snapshots", "find", ""],                      # Empty search pattern
            ["snapshots", "find", "   "]                   # Whitespace pattern
        ]
        
        for cmd in empty_input_scenarios:
            result = runner.invoke(app, cmd)
            combined = combined_output(result)

            # Should handle empty inputs gracefully
            assert result.exit_code in [0, 1], f"Should handle empty input: {' '.join(cmd)}"

    @pytest.mark.unit
    def test_very_long_input_handling(self):
        """Test handling of very long input values."""
        very_long_string = "a" * 1000  # 1000 character string
        
        long_input_scenarios = [
            ["repos", "add", very_long_string, "file:///tmp/repo"],
            ["targets", "add", very_long_string, "--path", "/tmp"],
            ["snapshots", "find", very_long_string]
        ]
        
        for cmd in long_input_scenarios:
            result = runner.invoke(app, cmd)
            # Should handle long inputs without crashing
            assert result.exit_code in [0, 1], f"Should handle long input: {cmd[0]} {cmd[1]} [long-string]"

    @pytest.mark.unit
    def test_unicode_input_handling(self):
        """Test handling of unicode and special characters in inputs."""
        unicode_inputs = [
            "测试仓库",           # Chinese characters
            "тест",              # Cyrillic characters
            "🚀backup",          # Emoji
            "café-repo",         # Accented characters
            "repo/with\\slashes" # Path separators
        ]
        
        for unicode_input in unicode_inputs:
            result = runner.invoke(app, [
                "repos", "add", unicode_input, "file:///tmp/repo"
            ])
            # Should handle unicode gracefully
            assert result.exit_code in [0, 1], f"Should handle unicode input: {unicode_input}"

    @pytest.mark.unit
    def test_error_message_quality(self):
        """Test that error messages are helpful and user-friendly."""
        # Test scenarios that should produce good error messages
        error_scenarios = [
            {
                "command": ["snapshots", "show"],
                "expected_keywords": ["missing", "required", "snapshot"]
            },
            {
                "command": ["repos", "add", "test", "invalid-uri"],
                "expected_keywords": ["invalid", "uri", "format"]
            },
            {
                "command": ["snapshots", "show", "bad$$id"],
                "expected_keywords": ["invalid", "snapshot", "format"]
            }
        ]
        
        for scenario in error_scenarios:
            result = runner.invoke(app, scenario["command"])
            combined = combined_output(result)

            assert result.exit_code != 0, f"Should fail: {' '.join(scenario['command'])}"

            # Check that error message contains expected keywords
            combined_lower = combined.lower()
            for keyword in scenario["expected_keywords"]:
                assert keyword in combined_lower, \
                    f"Error message should contain '{keyword}' for command: {' '.join(scenario['command'])}"
            
            # Error message should be substantial but not too verbose
            assert 10 < len(combined) < 1000, \
                f"Error message should be reasonable length for: {' '.join(scenario['command'])}"

    @pytest.mark.unit
    def test_graceful_degradation(self):
        """Test graceful degradation when optional features fail."""
        with patch('src.TimeLocker.cli.get_cli_service_manager') as mock_service_manager:
            # Mock service manager initialization to fail
            mock_service_manager.side_effect = Exception("Service manager unavailable")
            
            # Commands should still show help even if service manager fails
            result = runner.invoke(app, ["--help"])
            assert result.exit_code == 0, "Help should work even if service manager fails"
            
            result = runner.invoke(app, ["backup", "--help"])
            assert result.exit_code == 0, "Command help should work even if service manager fails"
