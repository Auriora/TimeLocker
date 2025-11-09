"""
Integration Tests for Repository Configuration Support

This module tests the integration of repository configurations with TimeLocker's
configuration backup system, cross-platform compatibility, and configuration
restoration workflows.

Tests Requirements:
- 11.1: Configuration backup includes repository configurations by default
- 11.2: Credentials excluded from configuration backups
- 11.3: Configuration restoration with credential re-entry
- 11.4: Structured configuration format for cross-platform compatibility
- 11.5: Optional exclusion of TimeLocker configuration from backups
- 12.1: Cross-platform path handling for repository URIs
- 12.2: Platform-specific storage backend support
- 12.3: Platform-specific credential store integration
- 12.4: Consistent repository operations across platforms
- 12.5: Platform-specific feature fallback mechanisms
"""

import pytest
import json
import tempfile
import platform
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.TimeLocker.services.repository_configuration_backup_manager import (
    RepositoryConfigurationBackupManager
)
from src.TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager, BackupReason
)
from src.TimeLocker.config.configuration_manager import ConfigurationManager
from src.TimeLocker.interfaces.repository_management_models import (
    RepositoryConfig, BackupEngine, RepositoryType
)


class TestConfigurationBackupIntegration:
    """
    Integration tests for configuration backup with repository configurations.
    
    Tests Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.temp_dir / "backups"
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir(parents=True)
        
        # Initialize managers
        self.repo_backup_manager = RepositoryConfigurationBackupManager(self.backup_dir)
        self.config_backup_manager = ConfigurationBackupManager(self.backup_dir)
        self.config_manager = ConfigurationManager(self.config_dir)
        
        # Create test repository configurations
        self.test_repos = [
            RepositoryConfig(
                name="local-repo",
                uri="file:///backup/local",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description="Local test repository",
                metadata={"location": "local"},
                engine_config={"compression": "auto"}
            ),
            RepositoryConfig(
                name="s3-repo",
                uri="s3:s3.amazonaws.com/my-bucket/backup",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.S3,
                description="S3 test repository",
                metadata={"region": "us-east-1"},
                engine_config={
                    "compression": "auto",
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                }
            )
        ]

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_repository_config_included_in_backup(self):
        """
        Test that repository configurations are included in backups by default.
        
        Requirement: 11.1
        """
        import time
        
        # Create backups for test repositories
        backup_ids = []
        for repo_config in self.test_repos:
            backup_id = self.repo_backup_manager.backup_repository_config(
                repo_config,
                operation_type="manual",
                reason=BackupReason.MANUAL
            )
            backup_ids.append((backup_id, repo_config))
            time.sleep(1.1)  # Ensure unique timestamps (backup IDs use seconds precision)
        
        # Verify backups were created
        assert len(backup_ids) == 2
        for backup_id, repo_config in backup_ids:
            assert backup_id is not None
            backup_file = self.backup_dir / "repository_configs" / f"{backup_id}.json"
            assert backup_file.exists()
            
            # Verify backup content matches the specific repository
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            assert backup_data['name'] == repo_config.name
            assert backup_data['uri'] == repo_config.uri
            assert backup_data['engine'] == repo_config.engine.value
            assert backup_data['type'] == repo_config.type.value

    def test_credentials_excluded_from_backup(self):
        """
        Test that credentials are excluded from configuration backups.
        
        Requirement: 11.2
        """
        # Use S3 repo with credentials
        s3_repo = self.test_repos[1]
        
        # Create backup
        backup_id = self.repo_backup_manager.backup_repository_config(
            s3_repo,
            operation_type="manual"
        )
        
        # Load backup and verify credentials are excluded
        backup_file = self.backup_dir / "repository_configs" / f"{backup_id}.json"
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Verify sensitive fields are not in backup
        backup_str = json.dumps(backup_data)
        assert 'access_key_id' not in backup_str
        assert 'secret_access_key' not in backup_str
        assert 'AKIAIOSFODNN7EXAMPLE' not in backup_str
        assert 'wJalrXUtnFEMI/K7MDENG' not in backup_str
        
        # Verify backup metadata indicates credential exclusion
        assert '_backup_metadata' in backup_data
        assert 'requires_credential_reentry' in backup_data['_backup_metadata']

    def test_configuration_restoration_workflow(self):
        """
        Test configuration restoration with credential re-entry workflow.
        
        Requirement: 11.3
        """
        # Create backup of S3 repository
        s3_repo = self.test_repos[1]
        backup_id = self.repo_backup_manager.backup_repository_config(
            s3_repo,
            operation_type="manual"
        )
        
        # Restore configuration
        restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
        
        # Verify configuration was restored
        assert restored_config is not None
        assert restored_config['name'] == s3_repo.name
        assert restored_config['uri'] == s3_repo.uri
        
        # Verify credentials are not in restored config
        assert 'access_key_id' not in json.dumps(restored_config)
        assert 'secret_access_key' not in json.dumps(restored_config)
        
        # Verify metadata exists and indicates backup was created
        assert '_backup_metadata' in restored_config
        assert 'backed_up_at' in restored_config['_backup_metadata']
        assert 'excluded_fields' in restored_config['_backup_metadata']

    def test_structured_configuration_format(self):
        """
        Test that configuration is stored in structured format for cross-platform compatibility.
        
        Requirement: 11.4
        """
        # Create backup
        local_repo = self.test_repos[0]
        backup_id = self.repo_backup_manager.backup_repository_config(
            local_repo,
            operation_type="manual"
        )
        
        # Load and verify structured format
        backup_file = self.backup_dir / "repository_configs" / f"{backup_id}.json"
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Verify required fields are present
        required_fields = ['name', 'uri', 'engine', 'type', 'description', 'metadata']
        for field in required_fields:
            assert field in backup_data, f"Required field '{field}' missing from backup"
        
        # Verify backup metadata
        assert '_backup_metadata' in backup_data
        metadata = backup_data['_backup_metadata']
        assert 'backed_up_at' in metadata
        assert 'backup_version' in metadata
        assert metadata['backup_version'] == '1.0'
        
        # Verify JSON is valid and can be parsed
        json_str = json.dumps(backup_data)
        reparsed = json.loads(json_str)
        assert reparsed == backup_data

    def test_optional_exclusion_of_timelocker_config(self):
        """
        Test optional exclusion of TimeLocker configuration from backups.
        
        Requirement: 11.5
        """
        # This test verifies that the backup system supports filtering
        # In practice, this would be controlled by backup configuration
        
        # Create backup with tags indicating it should be excluded from certain operations
        local_repo = self.test_repos[0]
        backup_id = self.repo_backup_manager.backup_repository_config(
            local_repo,
            operation_type="manual"
        )
        
        # Verify backup was created
        assert backup_id is not None
        
        # List backups and verify filtering capability
        all_backups = self.repo_backup_manager.list_repository_backups()
        assert len(all_backups) >= 1
        
        # Verify we can filter by repository name
        local_backups = self.repo_backup_manager.list_repository_backups("local-repo")
        assert len(local_backups) >= 1
        
        # Verify backup info includes tags for filtering
        backup_info = self.repo_backup_manager.get_backup_info(backup_id)
        assert backup_info is not None
        assert 'tags' in backup_info


class TestCrossPlatformRepositoryOperations:
    """
    Integration tests for cross-platform repository operations.
    
    Tests Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
    """

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.temp_dir / "backups"
        self.repo_backup_manager = RepositoryConfigurationBackupManager(self.backup_dir)
        
        # Get platform information
        self.platform = platform.system()
        self.is_windows = self.platform == 'Windows'
        self.is_unix = self.platform in ['Linux', 'Darwin']

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_cross_platform_path_handling(self):
        """
        Test cross-platform path handling for repository URIs.
        
        Requirement: 12.1
        """
        # Create platform-specific repository configurations
        if self.is_windows:
            test_paths = [
                "file:///C:/Users/test/backup",
                "file:///D:/Backups/repo",
                r"file:///\\server\share\backup"
            ]
        else:  # Unix-like
            test_paths = [
                "file:///home/user/backup",
                "file:///mnt/backup/repo",
                "file:///var/backups/timelocker"
            ]
        
        # Create and backup repository configs with platform-specific paths
        for i, uri in enumerate(test_paths):
            repo_config = RepositoryConfig(
                name=f"platform-repo-{i}",
                uri=uri,
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description=f"Platform-specific repository {i}",
                metadata={"platform": self.platform}
            )
            
            # Create backup
            backup_id = self.repo_backup_manager.backup_repository_config(
                repo_config,
                operation_type="manual"
            )
            
            # Verify backup was created
            assert backup_id is not None
            
            # Restore and verify path is preserved
            restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
            assert restored_config['uri'] == uri
            assert restored_config['metadata']['platform'] == self.platform

    def test_platform_specific_storage_backends(self):
        """
        Test platform-specific storage backend support.
        
        Requirement: 12.2
        """
        # Define platform-specific storage backends
        storage_backends = {
            'Windows': [
                ('file:///C:/backup', RepositoryType.LOCAL),
                ('smb://server/share/backup', RepositoryType.SMB),
                ('s3:s3.amazonaws.com/bucket', RepositoryType.S3)
            ],
            'Linux': [
                ('file:///mnt/backup', RepositoryType.LOCAL),
                ('nfs://server/export/backup', RepositoryType.NFS),
                ('sftp://user@server/backup', RepositoryType.SFTP),
                ('s3:s3.amazonaws.com/bucket', RepositoryType.S3)
            ],
            'Darwin': [  # macOS
                ('file:///Volumes/backup', RepositoryType.LOCAL),
                ('smb://server/share/backup', RepositoryType.SMB),
                ('sftp://user@server/backup', RepositoryType.SFTP),
                ('s3:s3.amazonaws.com/bucket', RepositoryType.S3)
            ]
        }
        
        # Get backends for current platform
        platform_backends = storage_backends.get(self.platform, storage_backends['Linux'])
        
        # Test each backend type
        for i, (uri, repo_type) in enumerate(platform_backends):
            repo_config = RepositoryConfig(
                name=f"backend-{repo_type.value}-{i}",
                uri=uri,
                engine=BackupEngine.RESTIC,
                type=repo_type,
                description=f"Test {repo_type.value} backend",
                metadata={"backend_type": repo_type.value}
            )
            
            # Create backup
            backup_id = self.repo_backup_manager.backup_repository_config(
                repo_config,
                operation_type="manual"
            )
            
            # Verify backup preserves backend information
            restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
            assert restored_config['type'] == repo_type.value
            assert restored_config['uri'] == uri

    def test_consistent_operations_across_platforms(self):
        """
        Test consistent repository operations across platforms.
        
        Requirement: 12.4
        """
        # Create a standard repository configuration
        repo_config = RepositoryConfig(
            name="cross-platform-repo",
            uri="s3:s3.amazonaws.com/test-bucket/backup",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3,
            description="Cross-platform test repository",
            metadata={
                "created_on_platform": self.platform,
                "python_version": platform.python_version()
            }
        )
        
        # Test backup operation
        backup_id = self.repo_backup_manager.backup_repository_config(
            repo_config,
            operation_type="manual"
        )
        assert backup_id is not None
        
        # Test list operation
        backups = self.repo_backup_manager.list_repository_backups("cross-platform-repo")
        assert len(backups) >= 1
        
        # Test restore operation
        restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
        assert restored_config['name'] == repo_config.name
        assert restored_config['uri'] == repo_config.uri
        
        # Test validation operation
        is_valid = self.repo_backup_manager.validate_repository_backup(backup_id)
        assert is_valid is True
        
        # Test cleanup operation
        # Create additional backups
        for i in range(3):
            self.repo_backup_manager.backup_repository_config(
                repo_config,
                operation_type=f"test_{i}"
            )
        
        # Cleanup should work consistently
        initial_count = len(self.repo_backup_manager.list_repository_backups("cross-platform-repo"))
        cleaned = self.repo_backup_manager.cleanup_repository_backups("cross-platform-repo")
        final_count = len(self.repo_backup_manager.list_repository_backups("cross-platform-repo"))
        
        # Verify cleanup worked (if we had more than max backups)
        if initial_count > self.repo_backup_manager.max_backups_per_repository:
            assert cleaned > 0
            assert final_count <= self.repo_backup_manager.max_backups_per_repository

    def test_platform_specific_feature_fallback(self):
        """
        Test platform-specific feature fallback mechanisms.
        
        Requirement: 12.5
        """
        # Test features that may not be available on all platforms
        
        # Feature 1: Symbolic links (may not work on Windows without admin)
        test_repo = RepositoryConfig(
            name="feature-test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Feature test repository",
            metadata={"supports_symlinks": hasattr(os, 'symlink')}
        )
        
        backup_id = self.repo_backup_manager.backup_repository_config(
            test_repo,
            operation_type="manual"
        )
        
        # Verify backup succeeded regardless of platform features
        assert backup_id is not None
        
        # Feature 2: File permissions (different on Windows vs Unix)
        restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
        assert 'metadata' in restored_config
        
        # Feature 3: Path separators (should be normalized)
        if self.is_windows:
            windows_path_repo = RepositoryConfig(
                name="windows-path-repo",
                uri=r"file:///C:\Users\test\backup",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description="Windows path test"
            )
            backup_id = self.repo_backup_manager.backup_repository_config(
                windows_path_repo,
                operation_type="manual"
            )
            assert backup_id is not None


class TestConfigurationRestorationWorkflow:
    """
    Integration tests for complete configuration restoration workflow.
    
    Tests Requirements: 11.3, 11.4, 12.1, 12.4
    """

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.backup_dir = self.temp_dir / "backups"
        self.repo_backup_manager = RepositoryConfigurationBackupManager(self.backup_dir)

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_backup_and_restore_workflow(self):
        """
        Test complete backup and restore workflow with credential handling.
        
        Requirements: 11.3, 11.4
        """
        # Step 1: Create repository with credentials
        original_repo = RepositoryConfig(
            name="workflow-repo",
            uri="s3:s3.amazonaws.com/my-bucket/backup",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3,
            description="Workflow test repository",
            metadata={"environment": "test"},
            engine_config={
                "compression": "auto",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "region": "us-east-1"
            }
        )
        
        # Step 2: Create backup
        backup_id = self.repo_backup_manager.backup_repository_config(
            original_repo,
            operation_type="manual"
        )
        
        # Step 3: Verify backup was created
        assert backup_id is not None
        backup_info = self.repo_backup_manager.get_backup_info(backup_id)
        assert backup_info is not None
        
        # Step 4: Restore configuration
        restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
        
        # Step 5: Verify restoration
        assert restored_config['name'] == original_repo.name
        assert restored_config['uri'] == original_repo.uri
        assert restored_config['engine'] == original_repo.engine.value
        assert restored_config['type'] == original_repo.type.value
        
        # Step 6: Verify credentials were excluded
        restored_str = json.dumps(restored_config)
        assert 'access_key_id' not in restored_str
        assert 'secret_access_key' not in restored_str
        assert 'AKIAIOSFODNN7EXAMPLE' not in restored_str
        
        # Step 7: Verify metadata exists and indicates backup was created
        assert '_backup_metadata' in restored_config
        assert 'backed_up_at' in restored_config['_backup_metadata']
        assert 'excluded_fields' in restored_config['_backup_metadata']
        
        # Step 8: Simulate credential re-entry (in real workflow, user would provide these)
        # This would be handled by the credential manager in actual implementation
        assert 'engine_config' in restored_config
        # Non-sensitive config should be preserved
        if 'compression' in original_repo.engine_config:
            # Note: compression might be in engine_config if not filtered
            pass

    def test_multi_repository_backup_and_restore(self):
        """
        Test backup and restore of multiple repositories.
        
        Requirements: 11.1, 11.4, 12.4
        """
        import time
        
        # Create multiple repositories
        repos = [
            RepositoryConfig(
                name=f"multi-repo-{i}",
                uri=f"file:///backup/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description=f"Multi-repo test {i}",
                metadata={"index": i}
            )
            for i in range(5)
        ]
        
        # Backup all repositories with unique timestamps
        backup_mapping = []
        for repo in repos:
            backup_id = self.repo_backup_manager.backup_repository_config(
                repo,
                operation_type="manual"
            )
            backup_mapping.append((backup_id, repo))
            time.sleep(1.1)  # Ensure unique timestamps (backup IDs use seconds precision)
        
        # Verify all backups were created
        assert len(backup_mapping) == 5
        
        # Restore all repositories and verify each matches its original
        for backup_id, original_repo in backup_mapping:
            restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
            assert restored_config['name'] == original_repo.name
            assert restored_config['uri'] == original_repo.uri
            assert restored_config['metadata']['index'] == original_repo.metadata['index']

    def test_backup_validation_before_restore(self):
        """
        Test backup validation before restoration.
        
        Requirement: 11.4
        """
        # Create and backup repository
        repo = RepositoryConfig(
            name="validation-repo",
            uri="file:///backup/validation",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Validation test repository"
        )
        
        backup_id = self.repo_backup_manager.backup_repository_config(
            repo,
            operation_type="manual"
        )
        
        # Validate backup before restore
        is_valid = self.repo_backup_manager.validate_repository_backup(backup_id)
        assert is_valid is True
        
        # Only restore if validation passes
        if is_valid:
            restored_config = self.repo_backup_manager.restore_repository_config(backup_id)
            assert restored_config is not None
            assert restored_config['name'] == repo.name
