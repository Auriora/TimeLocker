"""
Tests for RepositoryConfigurationBackupManager

This module tests the repository-specific configuration backup functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from TimeLocker.services.repository_configuration_backup_manager import (
    RepositoryConfigurationBackupManager, RepositoryBackupMetadata
)
from TimeLocker.config.configuration_backup_manager import BackupReason
from TimeLocker.interfaces.repository_management_models import (
    RepositoryConfig, BackupEngine, RepositoryType
)


class TestRepositoryConfigurationBackupManager:
    """Test repository configuration backup functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_manager = RepositoryConfigurationBackupManager(self.temp_dir)
        
        # Create test repository configuration
        self.test_config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Test repository for backup testing",
            metadata={"test": "value"},
            engine_config={"compression": "auto"}
        )

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_backup_repository_config(self):
        """Test basic repository configuration backup"""
        backup_id = self.backup_manager.backup_repository_config(
            self.test_config, 
            operation_type="manual"
        )
        
        assert backup_id is not None
        assert backup_id.startswith("backup_")
        
        # Verify backup file exists
        backup_file = self.backup_manager.backup_directory / f"{backup_id}.json"
        assert backup_file.exists()
        
        # Verify backup content
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        assert backup_data['name'] == self.test_config.name
        assert backup_data['uri'] == self.test_config.uri
        assert backup_data['engine'] == self.test_config.engine.value
        assert '_backup_metadata' in backup_data

    def test_backup_before_risky_operation(self):
        """Test automatic backup before risky operations"""
        # Test risky operation that should trigger backup
        backup_id = self.backup_manager.backup_before_risky_operation(
            self.test_config, 
            "reinitialize"
        )
        
        assert backup_id is not None
        assert backup_id != ""
        
        # Test non-risky operation that should not trigger backup
        backup_id = self.backup_manager.backup_before_risky_operation(
            self.test_config, 
            "list"
        )
        
        assert backup_id == ""

    def test_prepare_config_for_backup_excludes_sensitive_data(self):
        """Test that sensitive data is excluded from backups"""
        # Add some sensitive data to engine config
        self.test_config.engine_config.update({
            'password': 'secret123',
            'access_key': 'AKIAIOSFODNN7EXAMPLE',
            'secret_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        })
        
        safe_config = self.backup_manager._prepare_config_for_backup(self.test_config)
        
        # Verify sensitive data is excluded
        assert 'password' not in str(safe_config)
        assert 'access_key' not in str(safe_config)
        assert 'secret_key' not in str(safe_config)
        
        # Verify backup metadata is added
        assert '_backup_metadata' in safe_config
        assert 'backed_up_at' in safe_config['_backup_metadata']
        assert 'requires_credential_reentry' in safe_config['_backup_metadata']

    def test_list_repository_backups(self):
        """Test listing repository backups"""
        # Create a backup for test-repo
        backup_id1 = self.backup_manager.backup_repository_config(
            self.test_config, 
            operation_type="manual"
        )
        
        # List all repository backups
        all_backups = self.backup_manager.list_repository_backups()
        assert len(all_backups) >= 1
        
        # List backups for specific repository
        test_repo_backups = self.backup_manager.list_repository_backups("test-repo")
        assert len(test_repo_backups) >= 1
        
        # Verify the backup exists
        assert backup_id1 is not None

    def test_restore_repository_config(self):
        """Test restoring repository configuration from backup"""
        # Create backup
        backup_id = self.backup_manager.backup_repository_config(
            self.test_config, 
            operation_type="manual"
        )
        
        # Restore configuration
        restored_config = self.backup_manager.restore_repository_config(backup_id)
        
        assert restored_config is not None
        assert restored_config['name'] == self.test_config.name
        assert restored_config['uri'] == self.test_config.uri
        assert '_backup_metadata' in restored_config

    def test_cleanup_repository_backups(self):
        """Test cleanup of old repository backups"""
        import time
        
        # Create more backups than the limit
        backup_ids = []
        for i in range(7):  # More than max_backups_per_repository (5)
            backup_id = self.backup_manager.backup_repository_config(
                self.test_config, 
                operation_type=f"test_{i}"
            )
            backup_ids.append(backup_id)
            # Small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Get initial count
        initial_backups = self.backup_manager.list_repository_backups("test-repo")
        initial_count = len(initial_backups)
        
        # Cleanup backups for this repository
        cleaned_count = self.backup_manager.cleanup_repository_backups("test-repo")
        
        # Verify some cleanup occurred if we had more than the limit
        if initial_count > self.backup_manager.max_backups_per_repository:
            assert cleaned_count > 0
        
        # Verify remaining backups
        remaining_backups = self.backup_manager.list_repository_backups("test-repo")
        assert len(remaining_backups) <= self.backup_manager.max_backups_per_repository

    def test_validate_repository_backup(self):
        """Test validation of repository backup"""
        # Create backup
        backup_id = self.backup_manager.backup_repository_config(
            self.test_config, 
            operation_type="manual"
        )
        
        # Validate backup
        is_valid = self.backup_manager.validate_repository_backup(backup_id)
        assert is_valid is True
        
        # Test validation of non-existent backup
        is_valid = self.backup_manager.validate_repository_backup("nonexistent")
        assert is_valid is False

    def test_get_backup_info(self):
        """Test getting backup information"""
        # Create backup
        backup_id = self.backup_manager.backup_repository_config(
            self.test_config, 
            operation_type="manual"
        )
        
        # Get backup info
        backup_info = self.backup_manager.get_backup_info(backup_id)
        
        assert backup_info is not None
        assert backup_info['backup_id'] == backup_id
        assert 'created_at' in backup_info
        assert 'tags' in backup_info
        
        # Test getting info for non-existent backup
        backup_info = self.backup_manager.get_backup_info("nonexistent")
        assert backup_info is None

    def test_repository_backup_metadata(self):
        """Test repository-specific backup metadata"""
        metadata = RepositoryBackupMetadata(
            backup_id="test_backup",
            created_at=datetime.utcnow(),
            reason=BackupReason.MANUAL,
            size_bytes=1024,
            sections=["config"],
            validation_status="valid",
            checksum="abc123",
            retention_policy="default",
            source_file="/tmp/test",
            repository_name="test-repo",
            repository_uri="file:///tmp/repo",
            engine_type="restic",
            operation_type="manual"
        )
        
        # Test serialization
        data = metadata.to_dict()
        assert data['repository_name'] == "test-repo"
        assert data['repository_uri'] == "file:///tmp/repo"
        assert data['engine_type'] == "restic"
        assert data['operation_type'] == "manual"
        
        # Test deserialization
        restored_metadata = RepositoryBackupMetadata.from_dict(data)
        assert restored_metadata.repository_name == metadata.repository_name
        assert restored_metadata.repository_uri == metadata.repository_uri
        assert restored_metadata.engine_type == metadata.engine_type
        assert restored_metadata.operation_type == metadata.operation_type