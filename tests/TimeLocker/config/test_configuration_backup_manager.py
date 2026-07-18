"""
Unit tests for ConfigurationBackupManager.

Tests backup creation, restoration, comparison, validation, and cleanup
with various scenarios and edge cases.
"""

import copy
import json
import time
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pytest

from TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager,
    ConfigurationBackupMetadata,
    BackupReason
)
from TimeLocker.config.configuration_validator import ConfigurationValidator, ValidationResult
from TimeLocker.interfaces.exceptions import ConfigurationBackupError


class TestConfigurationBackupManager:
    """Test suite for ConfigurationBackupManager"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.temp_dir / "backups"
        self.config_file = self.temp_dir / "config.json"
        
        # Create test configuration file
        self.test_config = {
            "general": {
                "app_name": "TimeLocker",
                "version": "1.0.0",
                "log_level": "INFO"
            },
            "backup": {
                "compression": "auto",
                "exclude_caches": True
            },
            "repositories": {
                "default": {
                    "location": "/backup/repo",
                    "password": "secret123"
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f, indent=2)
        
        # Create backup manager
        self.validator = ConfigurationValidator()
        self.backup_manager = ConfigurationBackupManager(self.backup_dir, self.validator)

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.config
    @pytest.mark.unit
    def test_backup_manager_initialization(self):
        """Test backup manager initialization"""
        assert self.backup_manager.backup_directory == self.backup_dir
        assert self.backup_dir.exists()
        assert self.backup_manager._validator is not None

    @pytest.mark.config
    @pytest.mark.unit
    def test_create_backup(self):
        """Test creating a configuration backup"""
        # Create backup
        backup_id = self.backup_manager.create_backup(
            self.config_file,
            BackupReason.MANUAL,
            tags=["test", "manual"]
        )
        
        assert backup_id is not None
        assert backup_id.startswith("backup_")
        assert "manual" in backup_id
        
        # Verify backup file exists
        backup_file = self.backup_dir / f"{backup_id}.json"
        assert backup_file.exists()
        
        # Verify backup content
        with open(backup_file, 'r') as f:
            backup_content = json.load(f)
        assert backup_content == self.test_config
        
        # Verify metadata was created
        backups = self.backup_manager.list_backups()
        assert len(backups) == 1
        assert backups[0]['backup_id'] == backup_id
        assert backups[0]['reason'] == BackupReason.MANUAL.value
        assert "test" in backups[0]['tags']
        assert "manual" in backups[0]['tags']

    @pytest.mark.config
    @pytest.mark.unit
    def test_create_backup_nonexistent_file(self):
        """Test creating backup of non-existent file"""
        nonexistent_file = self.temp_dir / "nonexistent.json"
        
        with pytest.raises(ConfigurationBackupError) as exc_info:
            self.backup_manager.create_backup(nonexistent_file, BackupReason.MANUAL)
        
        assert "does not exist" in str(exc_info.value)

    @pytest.mark.config
    @pytest.mark.unit
    def test_list_backups(self):
        """Test listing backups with filtering"""
        # Create multiple backups with different reasons
        backup1 = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        backup2 = self.backup_manager.create_backup(self.config_file, BackupReason.AUTOMATIC)
        backup3 = self.backup_manager.create_backup(self.config_file, BackupReason.PRE_UPDATE)
        
        # List all backups
        all_backups = self.backup_manager.list_backups()
        assert len(all_backups) == 3
        
        # List with limit
        limited_backups = self.backup_manager.list_backups(limit=2)
        assert len(limited_backups) == 2
        
        # List with reason filter
        manual_backups = self.backup_manager.list_backups(reason_filter=BackupReason.MANUAL)
        assert len(manual_backups) == 1
        assert manual_backups[0]['backup_id'] == backup1
        
        # Verify sorting (newest first)
        assert all_backups[0]['backup_id'] == backup3  # Most recent

    @pytest.mark.config
    @pytest.mark.unit
    def test_restore_backup(self):
        """Test restoring configuration from backup"""
        # Create backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Modify original file
        modified_config = copy.deepcopy(self.test_config)
        modified_config["general"]["version"] = "2.0.0"
        modified_config["new_section"] = {"new_key": "new_value"}
        
        with open(self.config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        # Restore from backup
        result = self.backup_manager.restore_backup(backup_id, self.config_file)
        assert result is True
        
        # Verify restoration
        with open(self.config_file, 'r') as f:
            restored_config = json.load(f)
        assert restored_config == self.test_config
        assert restored_config["general"]["version"] == "1.0.0"  # Should be original version
        assert "new_section" not in restored_config

    @pytest.mark.config
    @pytest.mark.unit
    def test_restore_nonexistent_backup(self):
        """Test restoring from non-existent backup"""
        with pytest.raises(ConfigurationBackupError) as exc_info:
            self.backup_manager.restore_backup("nonexistent_backup", self.config_file)
        
        assert "not found" in str(exc_info.value)

    @pytest.mark.config
    @pytest.mark.unit
    def test_restore_corrupted_backup(self):
        """Test restoring from corrupted backup"""
        # Create backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Corrupt the backup file
        backup_file = self.backup_dir / f"{backup_id}.json"
        with open(backup_file, 'w') as f:
            f.write("corrupted content")
        
        # Attempt to restore should fail due to checksum mismatch
        with pytest.raises(ConfigurationBackupError) as exc_info:
            self.backup_manager.restore_backup(backup_id, self.config_file)
        
        assert "checksum mismatch" in str(exc_info.value)

    @pytest.mark.config
    @pytest.mark.unit
    def test_compare_backups(self):
        """Test comparing two backups"""
        # Create first backup
        backup1_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Modify configuration
        modified_config = copy.deepcopy(self.test_config)
        modified_config["general"]["version"] = "2.0.0"
        modified_config["general"]["new_setting"] = "new_value"
        del modified_config["backup"]["exclude_caches"]
        
        with open(self.config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        # Create second backup
        backup2_id = self.backup_manager.create_backup(self.config_file, BackupReason.AUTOMATIC)
        
        # Compare backups
        comparison = self.backup_manager.compare_backups(backup1_id, backup2_id)
        
        assert comparison['identical'] is False
        assert len(comparison['differences']) > 0
        
        # Check for expected differences
        differences = comparison['differences']
        version_changes = [d for d in differences if 'version' in d.get('path', '')]
        assert len(version_changes) > 0
        
        # Verify backup metadata in comparison
        assert comparison['backup1']['id'] == backup1_id
        assert comparison['backup2']['id'] == backup2_id

    @pytest.mark.config
    @pytest.mark.unit
    def test_compare_identical_backups(self):
        """Test comparing identical backups"""
        # Create two identical backups
        backup1_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        backup2_id = self.backup_manager.create_backup(self.config_file, BackupReason.AUTOMATIC)
        
        # Compare backups
        comparison = self.backup_manager.compare_backups(backup1_id, backup2_id)
        
        assert comparison['identical'] is True
        assert len(comparison['differences']) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_restore_section(self):
        """Test restoring a specific section from backup"""
        # Create backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Modify only the general section
        modified_config = copy.deepcopy(self.test_config)
        modified_config["general"] = {
            "app_name": "Modified TimeLocker",
            "version": "3.0.0",
            "log_level": "DEBUG"
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        # Restore only the general section
        result = self.backup_manager.restore_section(backup_id, "general", self.config_file)
        assert result is True
        
        # Verify only general section was restored
        with open(self.config_file, 'r') as f:
            restored_config = json.load(f)
        
        assert restored_config["general"] == self.test_config["general"]
        assert restored_config["backup"] == modified_config["backup"]  # Unchanged
        assert restored_config["repositories"] == modified_config["repositories"]  # Unchanged

    @pytest.mark.config
    @pytest.mark.unit
    def test_restore_nonexistent_section(self):
        """Test restoring non-existent section from backup"""
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        with pytest.raises(ConfigurationBackupError) as exc_info:
            self.backup_manager.restore_section(backup_id, "nonexistent_section", self.config_file)
        
        assert "not found in backup" in str(exc_info.value)

    @pytest.mark.config
    @pytest.mark.unit
    def test_cleanup_old_backups(self):
        """Test cleaning up old backups"""
        # Create multiple backups with slight delays to ensure unique timestamps
        backup_ids = []
        for i in range(7):
            backup_id = self.backup_manager.create_backup(
                self.config_file,
                BackupReason.AUTOMATIC,
                tags=["cleanup_test"]
            )
            backup_ids.append(backup_id)
            time.sleep(0.01)  # Small delay to ensure unique timestamps
        
        # Verify all backups exist
        all_backups = self.backup_manager.list_backups()
        assert len(all_backups) == 7
        
        # Cleanup keeping only 3 most recent
        cleaned_count = self.backup_manager.cleanup_old_backups(keep_count=3)
        
        # Should have cleaned up 4 backups
        assert cleaned_count == 4
        
        # Should have 3 backups remaining
        remaining_backups = self.backup_manager.list_backups()
        assert len(remaining_backups) == 3

    @pytest.mark.config
    @pytest.mark.unit
    def test_cleanup_with_protected_tags(self):
        """Test cleanup respecting protected tags"""
        # Create backups with different tags
        regular_backup = self.backup_manager.create_backup(
            self.config_file, BackupReason.AUTOMATIC, tags=["regular"]
        )
        critical_backup = self.backup_manager.create_backup(
            self.config_file, BackupReason.MANUAL, tags=["critical"]
        )
        milestone_backup = self.backup_manager.create_backup(
            self.config_file, BackupReason.MANUAL, tags=["milestone"]
        )
        manual_backup = self.backup_manager.create_backup(
            self.config_file, BackupReason.MANUAL, tags=["manual"]
        )
        
        # Cleanup keeping only 1 backup
        cleaned_count = self.backup_manager.cleanup_old_backups(keep_count=1)
        
        # Should only clean up the regular backup
        # Protected backups (critical, milestone, manual) should remain
        remaining_backups = self.backup_manager.list_backups()
        remaining_ids = [b['backup_id'] for b in remaining_backups]
        
        assert regular_backup not in remaining_ids
        assert critical_backup in remaining_ids
        assert milestone_backup in remaining_ids
        assert manual_backup in remaining_ids

    @pytest.mark.config
    @pytest.mark.unit
    def test_cleanup_by_age(self):
        """Test cleanup by maximum age"""
        # Create backup and artificially age it
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.AUTOMATIC)
        
        # Modify metadata to make backup appear old
        metadata_dict = self.backup_manager._load_backup_metadata()
        old_metadata = metadata_dict[backup_id]
        old_metadata.created_at = datetime.now() - timedelta(days=10)
        self.backup_manager._save_backup_metadata(old_metadata)
        
        # Cleanup backups older than 5 days
        cleaned_count = self.backup_manager.cleanup_old_backups(keep_count=10, max_age_days=5)
        
        # Should have cleaned up the old backup
        assert cleaned_count == 1
        assert len(self.backup_manager.list_backups()) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_validate_backup(self):
        """Test backup validation"""
        # Create valid backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Validate backup
        result = self.backup_manager.validate_backup(backup_id)
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_validate_corrupted_backup(self):
        """Test validation of corrupted backup"""
        # Create backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Corrupt backup file
        backup_file = self.backup_dir / f"{backup_id}.json"
        with open(backup_file, 'w') as f:
            f.write("invalid json")
        
        # Validate backup
        result = self.backup_manager.validate_backup(backup_id)
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("Invalid JSON" in error for error in result.errors)

    @pytest.mark.config
    @pytest.mark.unit
    def test_validate_nonexistent_backup(self):
        """Test validation of non-existent backup"""
        result = self.backup_manager.validate_backup("nonexistent_backup")
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("not found" in error for error in result.errors)

    @pytest.mark.config
    @pytest.mark.unit
    def test_backup_metadata_persistence(self):
        """Test backup metadata persistence across manager instances"""
        # Create backup
        backup_id = self.backup_manager.create_backup(
            self.config_file,
            BackupReason.MANUAL,
            tags=["persistence_test"]
        )
        
        # Create new manager instance
        new_manager = ConfigurationBackupManager(self.backup_dir, self.validator)
        
        # Should be able to list the backup
        backups = new_manager.list_backups()
        assert len(backups) == 1
        assert backups[0]['backup_id'] == backup_id
        assert "persistence_test" in backups[0]['tags']

    @pytest.mark.config
    @pytest.mark.unit
    def test_checksum_calculation(self):
        """Test checksum calculation and verification"""
        # Create backup
        backup_id = self.backup_manager.create_backup(self.config_file, BackupReason.MANUAL)
        
        # Get backup metadata
        metadata = self.backup_manager._get_backup_metadata(backup_id)
        assert metadata is not None
        assert metadata.checksum is not None
        
        # Verify checksum matches file content
        backup_file = self.backup_dir / f"{backup_id}.json"
        calculated_checksum = self.backup_manager._calculate_checksum(backup_file)
        assert calculated_checksum == metadata.checksum

    @pytest.mark.config
    @pytest.mark.unit
    def test_backup_with_invalid_config(self):
        """Test backup creation with invalid configuration"""
        # Create a mock validator that will fail validation
        mock_validator = Mock()
        mock_result = Mock()
        mock_result.is_valid = False
        mock_result.errors = ["Invalid configuration structure"]
        mock_validator.validate_config.return_value = mock_result
        
        # Create backup manager with mock validator
        backup_manager_with_mock = ConfigurationBackupManager(
            self.backup_dir,
            mock_validator
        )
        
        # Create invalid config file
        invalid_config = {"invalid": "structure", "missing": "required_fields"}
        invalid_config_file = self.temp_dir / "invalid_config.json"
        
        with open(invalid_config_file, 'w') as f:
            json.dump(invalid_config, f)
        
        # Should still create backup but mark as invalid
        backup_id = backup_manager_with_mock.create_backup(invalid_config_file, BackupReason.MANUAL)
        
        # Backup should exist
        backups = backup_manager_with_mock.list_backups()
        assert len(backups) == 1
        
        # Validation status should indicate issues
        backup_info = backups[0]
        assert "invalid" in backup_info['validation_status']

    @pytest.mark.config
    @pytest.mark.unit
    def test_section_extraction(self):
        """Test configuration section extraction"""
        sections = self.backup_manager._extract_sections(self.config_file)
        expected_sections = ["general", "backup", "repositories"]
        
        assert set(sections) == set(expected_sections)

    @pytest.mark.config
    @pytest.mark.unit
    def test_backup_reason_enum(self):
        """Test backup reason enumeration"""
        # Test all backup reasons
        reasons = [
            BackupReason.MANUAL,
            BackupReason.AUTOMATIC,
            BackupReason.PRE_UPDATE,
            BackupReason.PRE_MIGRATION,
            BackupReason.SCHEDULED,
            BackupReason.ERROR_RECOVERY
        ]
        
        for reason in reasons:
            backup_id = self.backup_manager.create_backup(self.config_file, reason)
            backups = self.backup_manager.list_backups(reason_filter=reason)
            assert len(backups) >= 1
            assert backups[0]['reason'] == reason.value

    @pytest.mark.config
    @pytest.mark.unit
    def test_metadata_serialization(self):
        """Test backup metadata serialization and deserialization"""
        # Create metadata
        metadata = ConfigurationBackupMetadata(
            backup_id="test_backup",
            created_at=datetime.now(),
            reason=BackupReason.MANUAL,
            size_bytes=1024,
            sections=["general", "backup"],
            validation_status="valid",
            checksum="abc123",
            retention_policy="default",
            source_file="/test/config.json",
            tags=["test", "serialization"]
        )
        
        # Serialize to dict
        metadata_dict = metadata.to_dict()
        assert isinstance(metadata_dict['created_at'], str)
        assert metadata_dict['reason'] == BackupReason.MANUAL.value
        
        # Deserialize from dict
        restored_metadata = ConfigurationBackupMetadata.from_dict(metadata_dict)
        assert restored_metadata.backup_id == metadata.backup_id
        assert restored_metadata.reason == metadata.reason
        assert restored_metadata.tags == metadata.tags
