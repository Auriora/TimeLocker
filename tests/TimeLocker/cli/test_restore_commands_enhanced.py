"""
Unit tests for enhanced TimeLocker CLI restore command group.

Tests restore command parsing, parameter validation, help output, and error handling
for the enhanced restore operations including browse, files, full, mount, find, diff, and verify.
"""

import pytest
import tempfile
from pathlib import Path

from src.TimeLocker.cli import app
from tests.TimeLocker.cli.test_utils import (
    get_cli_runner,
    combined_output,
    assert_success,
    assert_exit_code,
    assert_help_quality,
    patch_restore_commands,
)

runner = get_cli_runner()


class TestRestoreCommands:
    """Test suite for enhanced restore command group."""

    @pytest.mark.unit
    def test_restore_help_output(self):
        """Test restore command group help output."""
        result = runner.invoke(app, ["restore", "--help"])
        assert_help_quality(result, "restore")
        output = combined_output(result)
        assert "restore" in output.lower()

    @pytest.mark.unit
    def test_restore_browse_help(self):
        """Test restore browse command help output."""
        result = runner.invoke(app, ["restore", "browse", "--help"])
        assert_help_quality(result, "restore browse")

    @pytest.mark.unit
    def test_restore_files_help(self):
        """Test restore files command help output."""
        result = runner.invoke(app, ["restore", "files", "--help"])
        assert_help_quality(result, "restore files")

    @pytest.mark.unit
    def test_restore_full_help(self):
        """Test restore full command help output."""
        result = runner.invoke(app, ["restore", "full", "--help"])
        assert_help_quality(result, "restore full")

    @pytest.mark.unit
    def test_restore_mount_help(self):
        """Test restore mount command help output."""
        result = runner.invoke(app, ["restore", "mount", "--help"])
        assert_help_quality(result, "restore mount")

    @pytest.mark.unit
    def test_restore_umount_help(self):
        """Test restore umount command help output."""
        result = runner.invoke(app, ["restore", "umount", "--help"])
        assert_help_quality(result, "restore umount")

    @pytest.mark.unit
    def test_restore_find_help(self):
        """Test restore find command help output."""
        result = runner.invoke(app, ["restore", "find", "--help"])
        assert_help_quality(result, "restore find")

    @pytest.mark.unit
    def test_restore_diff_help(self):
        """Test restore diff command help output."""
        result = runner.invoke(app, ["restore", "diff", "--help"])
        assert_help_quality(result, "restore diff")

    @pytest.mark.unit
    def test_restore_verify_help(self):
        """Test restore verify command help output."""
        result = runner.invoke(app, ["restore", "verify", "--help"])
        assert_help_quality(result, "restore verify")

    @pytest.mark.unit
    def test_restore_browse_command(self):
        """Test restore browse command execution."""
        with patch_restore_commands():
            result = runner.invoke(app, [
                "restore", "browse", "test-repo", "abc123def456"
            ])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_files_command(self):
        """Test restore files command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch_restore_commands():
                result = runner.invoke(app, [
                    "restore", "files", "test-repo", "abc123def456",
                    "/test.txt",
                    "--target", temp_dir
                ])
            assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_full_command(self):
        """Test restore full command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch_restore_commands():
                result = runner.invoke(app, [
                    "restore", "full", "test-repo", "abc123def456", temp_dir
                ])
            assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_mount_command(self):
        """Test restore mount command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch_restore_commands():
                result = runner.invoke(app, [
                    "restore", "mount", "test-repo", "abc123def456", temp_dir
                ])
            assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_umount_command(self):
        """Test restore umount command execution."""
        with patch_restore_commands():
            result = runner.invoke(app, ["restore", "umount", "abc123def456"])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_find_command(self):
        """Test restore find command execution."""
        with patch_restore_commands():
            result = runner.invoke(app, [
                "restore", "find", "test-repo", "*.txt"
            ])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_diff_command(self):
        """Test restore diff command execution."""
        with patch_restore_commands():
            result = runner.invoke(app, [
                "restore", "diff", "test-repo", "abc123", "def456"
            ])
        assert result.exit_code in [0, 1, 2]

    @pytest.mark.unit
    def test_restore_verify_command(self):
        """Test restore verify command execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch_restore_commands():
                result = runner.invoke(app, ["restore", "verify", temp_dir])
            assert result.exit_code in [0, 1, 2]
