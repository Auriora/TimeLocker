"""
Tests for Timeshift configuration importer
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.TimeLocker.importers.timeshift_importer import (
    TimeshiftConfigParser,
    TimeshiftToTimeLockerMapper,
    TimeshiftImportResult
)


class TestTimeshiftConfigParser:
    """Test Timeshift configuration parser"""

    def test_parse_valid_config(self):
        """Test parsing valid Timeshift configuration"""
        config_data = {
                "backup_device_uuid": "12345678-1234-1234-1234-123456789abc",
                "btrfs_mode":         "false",
                "exclude":            [
                        "/home/user/.cache",
                        "/tmp",
                        "/var/tmp"
                ],
                "schedule_daily":     "true",
                "count_daily":        "7",
                "schedule_weekly":    "false"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            parser = TimeshiftConfigParser()
            parsed_config = parser.parse_config(config_file)

            assert parsed_config == config_data
            assert parser.get_backup_device_uuid() == "12345678-1234-1234-1234-123456789abc"
            assert not parser.is_btrfs_mode()
            assert parser.get_exclude_patterns() == ["/home/user/.cache", "/tmp", "/var/tmp"]

            schedule_info = parser.get_schedule_info()
            assert schedule_info["daily"] is True
            assert schedule_info["daily_count"] == 7
            assert schedule_info["weekly"] is False

        finally:
            config_file.unlink()

    def test_parse_missing_file(self):
        """Test parsing non-existent file"""
        parser = TimeshiftConfigParser()

        with pytest.raises(FileNotFoundError):
            parser.parse_config(Path("/nonexistent/file.json"))

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            config_file = Path(f.name)

        try:
            parser = TimeshiftConfigParser()

            with pytest.raises(json.JSONDecodeError):
                parser.parse_config(config_file)

        finally:
            config_file.unlink()

    def test_get_summary(self):
        """Test configuration summary generation"""
        config_data = {
                "backup_device_uuid": "test-uuid",
                "btrfs_mode":         "true",
                "exclude":            ["/tmp", "/var/cache"]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = Path(f.name)

        try:
            parser = TimeshiftConfigParser()
            parser.parse_config(config_file)

            summary = parser.get_summary()

            assert summary["backup_device_uuid"] == "test-uuid"
            assert summary["btrfs_mode"] is True
            assert summary["exclude_patterns"] == ["/tmp", "/var/cache"]
            assert "config_file" in summary
            assert "raw_config_keys" in summary

        finally:
            config_file.unlink()


class TestTimeshiftToTimeLockerMapper:
    """Test Timeshift to TimeLocker configuration mapper"""

    def test_map_exclude_patterns(self):
        """Test exclude pattern mapping"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_excludes = [
                "/home/user/.cache",
                "/tmp",
                "/var/log/old"
        ]

        mapped = mapper.map_exclude_patterns(timeshift_excludes)

        expected = [
                "**/home/user/.cache",
                "**/home/user/.cache/**",
                "**/tmp",
                "**/tmp/**",
                "**/var/log/old",
                "**/var/log/old/**"
        ]

        assert mapped == expected

    @patch('subprocess.run')
    def test_resolve_device_uuid_success(self, mock_run):
        """Test successful UUID to path resolution"""
        # Mock blkid command
        mock_run.side_effect = [
                MagicMock(returncode=0, stdout="/dev/sdb1\n"),  # blkid result
                MagicMock(returncode=0, stdout="/mnt/backup\n")  # findmnt result
        ]

        mapper = TimeshiftToTimeLockerMapper()
        result = mapper.resolve_device_uuid_to_path("test-uuid")

        assert result == "/mnt/backup/timeshift"
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_resolve_device_uuid_failure(self, mock_run):
        """Test failed UUID to path resolution"""
        # Mock failed blkid command
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        mapper = TimeshiftToTimeLockerMapper()
        result = mapper.resolve_device_uuid_to_path("invalid-uuid")

        assert result is None

    def test_create_repository_config(self):
        """Test repository configuration creation"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_config = {
                "backup_device_uuid": "test-uuid"
        }

        repo_config = mapper.create_repository_config(
                timeshift_config,
                repository_name="test_repo",
                manual_path="/custom/path"
        )

        assert repo_config["name"] == "test_repo"
        assert repo_config["location"] == "file:///custom/path"
        assert repo_config["_display_type"] == "local"
        assert repo_config["_display_original_uuid"] == "test-uuid"
        assert "Imported from Timeshift" in repo_config["description"]

    def test_create_backup_target_config(self):
        """Test backup target configuration creation"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_config = {
                "exclude": ["/tmp", "/var/cache"]
        }

        target_config = mapper.create_backup_target_config(
                timeshift_config,
                target_name="test_target",
                repository_name="test_repo",
                backup_paths=["/etc", "/home"]
        )

        assert target_config["name"] == "test_target"
        assert target_config["_display_repository"] == "test_repo"
        assert target_config["paths"] == ["/etc", "/home"]
        assert "**/tmp" in target_config["exclude_patterns"]
        assert "**/var/cache" in target_config["exclude_patterns"]
        assert "**/proc/**" in target_config["exclude_patterns"]  # Default exclude

    def test_create_backup_target_config_default_paths(self):
        """Test backup target configuration with default paths (root filesystem)"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_config = {
                "exclude": ["/tmp", "/var/cache"]
        }

        # Test without providing backup_paths - should default to ["/"]
        target_config = mapper.create_backup_target_config(
                timeshift_config,
                target_name="test_target",
                repository_name="test_repo"
        )

        assert target_config["name"] == "test_target"
        assert target_config["_display_repository"] == "test_repo"
        assert target_config["paths"] == ["/"]  # Should default to root filesystem
        assert "**/tmp" in target_config["exclude_patterns"]
        assert "**/var/cache" in target_config["exclude_patterns"]
        assert "**/proc/**" in target_config["exclude_patterns"]  # Default exclude
        assert "full system backup" in target_config["description"]

        # Check that appropriate warning is generated
        assert len(mapper.warnings) > 0
        assert any("full system backup" in warning for warning in mapper.warnings)

    def test_import_configuration_success(self):
        """Test successful configuration import"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_config = {
                "backup_device_uuid": "test-uuid",
                "btrfs_mode":         "false",
                "exclude":            ["/tmp"]
        }

        result = mapper.import_configuration(
                timeshift_config,
                repository_name="imported_repo",
                target_name="imported_target",
                manual_repository_path="/backup/path"
        )

        assert result.success is True
        assert result.repository_config is not None
        assert result.backup_target_config is not None
        assert result.repository_config["name"] == "imported_repo"
        assert result.backup_target_config["name"] == "imported_target"
        assert result.backup_target_config["paths"] == ["/"]  # Should default to root filesystem
        assert len(result.warnings) > 0  # Should have warnings about differences

    def test_import_configuration_btrfs_warning(self):
        """Test BTRFS mode warning"""
        mapper = TimeshiftToTimeLockerMapper()

        timeshift_config = {
                "backup_device_uuid": "test-uuid",
                "btrfs_mode":         "true"
        }

        result = mapper.import_configuration(timeshift_config)

        assert result.success is True
        assert any("BTRFS" in warning for warning in result.warnings)


class TestTimeshiftImportResult:
    """Test TimeshiftImportResult dataclass"""

    def test_default_initialization(self):
        """Test default initialization"""
        result = TimeshiftImportResult(success=True)

        assert result.success is True
        assert result.repository_config is None
        assert result.backup_target_config is None
        assert result.warnings == []
        assert result.errors == []

    def test_with_data(self):
        """Test initialization with data"""
        repo_config = {"name": "test"}
        target_config = {"name": "target"}
        warnings = ["warning1"]
        errors = ["error1"]

        result = TimeshiftImportResult(
                success=True,
                repository_config=repo_config,
                backup_target_config=target_config,
                warnings=warnings,
                errors=errors
        )

        assert result.success is True
        assert result.repository_config == repo_config
        assert result.backup_target_config == target_config
        assert result.warnings == warnings
        assert result.errors == errors
