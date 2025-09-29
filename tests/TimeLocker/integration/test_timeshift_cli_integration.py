"""
Integration tests for Timeshift CLI import command
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from src.TimeLocker.cli import app


class TestTimeshiftCLIIntegration:
    """Test Timeshift CLI import integration"""

    def setup_method(self):
        """Set up test environment"""
        # Set wider terminal width to prevent help text truncation in CI
        self.runner = CliRunner(env={'COLUMNS': '200'})

        # Create sample Timeshift configuration
        self.timeshift_config = {
                "backup_device_uuid": "test-uuid-1234",
                "btrfs_mode":         "false",
                "exclude":            [
                        "/home/*/.cache",
                        "/tmp",
                        "/var/tmp"
                ],
                "exclude-apps":       [
                        "/home/*/.mozilla/firefox/*/Cache"
                ],
                "schedule_daily":     "true",
                "count_daily":        "7"
        }

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_dry_run(self):
        """Test Timeshift import in dry-run mode"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.timeshift_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--repo-path", "/test/backup/path",
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            assert "Import from Timeshift" in result.stdout
            assert "Timeshift Configuration Found" in result.stdout
            assert "Repository Configuration" in result.stdout
            assert "Backup Target Configuration" in result.stdout
            assert "Dry run mode - no changes made" in result.stdout
            assert "timeshift_imported" in result.stdout
            assert "timeshift_system" in result.stdout

        finally:
            config_file.unlink()

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_help(self):
        """Test Timeshift import help command"""
        result = self.runner.invoke(app, [
                "config", "import", "timeshift", "--help"
        ])

        assert result.exit_code == 0
        assert "Import configuration from Timeshift backup tool" in result.stdout
        assert "--config-file" in result.stdout
        assert "--repo-name" in result.stdout
        assert "--target-name" in result.stdout
        assert "--repo-path" in result.stdout
        assert "--dry-run" in result.stdout

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_missing_config(self):
        """Test Timeshift import with missing config file"""
        result = self.runner.invoke(app, [
                "config", "import", "timeshift",
                "--config-file", "/nonexistent/file.json",
                "--yes"
        ])

        assert result.exit_code == 1
        assert "Timeshift Configuration Not Found" in result.stdout

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_invalid_json(self):
        """Test Timeshift import with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--yes"
            ])

            assert result.exit_code == 1
            assert "Invalid Timeshift Configuration" in result.stdout

        finally:
            config_file.unlink()

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_custom_names(self):
        """Test Timeshift import with custom repository and target names"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.timeshift_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--repo-name", "custom_repo",
                    "--target-name", "custom_target",
                    "--repo-path", "/custom/path",
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            assert "custom_repo" in result.stdout
            assert "custom_target" in result.stdout
            assert "/custom/path" in result.stdout

        finally:
            config_file.unlink()

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_custom_paths(self):
        """Test Timeshift import with custom backup paths"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.timeshift_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--paths", "/home",
                    "--paths", "/etc",
                    "--repo-path", "/backup",
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            assert "/home, /etc" in result.stdout

        finally:
            config_file.unlink()

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_verbose(self):
        """Test Timeshift import with verbose output"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.timeshift_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--repo-path", "/test/path",
                    "--verbose",
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            # Verbose mode should show the same output but with debug logging enabled
            assert "Import from Timeshift" in result.stdout

        finally:
            config_file.unlink()

    @patch('src.TimeLocker.importers.timeshift_importer.subprocess.run')
    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_uuid_resolution(self, mock_subprocess):
        """Test Timeshift import with UUID resolution"""
        # Mock successful UUID resolution
        mock_subprocess.side_effect = [
                MagicMock(returncode=0, stdout="/dev/sdb1\n"),  # blkid
                MagicMock(returncode=0, stdout="/mnt/backup\n")  # findmnt
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.timeshift_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            assert "/mnt/backup/timeshift" in result.stdout

        finally:
            config_file.unlink()

    @pytest.mark.config
    @pytest.mark.integration
    def test_timeshift_import_btrfs_warning(self):
        """Test Timeshift import with BTRFS mode warning"""
        btrfs_config = self.timeshift_config.copy()
        btrfs_config["btrfs_mode"] = "true"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(btrfs_config, f)
            config_file = Path(f.name)

        try:
            result = self.runner.invoke(app, [
                    "config", "import", "timeshift",
                    "--config-file", str(config_file),
                    "--repo-path", "/test/path",
                    "--dry-run",
                    "--yes"
            ])

            assert result.exit_code == 0
            assert "BTRFS Mode" in result.stdout
            assert "Yes" in result.stdout  # BTRFS mode should be detected

        finally:
            config_file.unlink()
