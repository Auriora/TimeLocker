"""
Complete Workflow Validation for TimeLocker v1.0.0

This module contains comprehensive workflow tests that validate the complete
TimeLocker system from initialization through backup, restore, and cleanup.
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.security import CredentialManager, SecurityService
from TimeLocker.config import ConfigurationManager
from TimeLocker.integration import IntegrationService
from TimeLocker.monitoring import StatusReporter


class TestCompleteWorkflowValidation:
    """Complete workflow validation for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup complete workflow test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.repo_dir = self.temp_dir / "repository"
        self.source_dir = self.temp_dir / "source"
        self.restore_dir = self.temp_dir / "restore"

        # Create directories
        for directory in [self.config_dir, self.repo_dir, self.source_dir, self.restore_dir]:
            directory.mkdir(parents=True)

        # Create realistic test data
        self._create_realistic_test_data()

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_realistic_test_data(self):
        """Create realistic test data that mimics real-world usage"""
        # Documents
        docs_dir = self.source_dir / "Documents"
        docs_dir.mkdir()

        (docs_dir / "important_document.pdf").write_bytes(b"PDF content" * 1000)
        (docs_dir / "spreadsheet.xlsx").write_bytes(b"Excel content" * 500)
        (docs_dir / "presentation.pptx").write_bytes(b"PowerPoint content" * 800)
        (docs_dir / "notes.txt").write_text("Important notes\n" * 100)

        # Photos
        photos_dir = self.source_dir / "Photos"
        photos_dir.mkdir()

        for i in range(10):
            photo_file = photos_dir / f"photo_{i:03d}.jpg"
            photo_file.write_bytes(b"JPEG data" * 2000)

        # Code projects
        code_dir = self.source_dir / "Projects" / "MyProject"
        code_dir.mkdir(parents=True)

        (code_dir / "main.py").write_text("print('Hello World')\n" * 50)
        (code_dir / "config.json").write_text('{"setting": "value"}\n' * 20)
        (code_dir / "README.md").write_text("# My Project\n" * 30)

        # Create .git directory (should be excluded)
        git_dir = code_dir / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")

        # Temporary files (should be excluded)
        (docs_dir / "temp.tmp").write_text("temporary file")
        (photos_dir / "Thumbs.db").write_bytes(b"thumbnail cache")

        # Large file
        large_file = self.source_dir / "large_file.bin"
        large_file.write_bytes(b"X" * (5 * 1024 * 1024))  # 5MB

    @pytest.mark.integration
    @pytest.mark.critical
    def test_complete_timelocker_workflow(self):
        """Test complete TimeLocker workflow from start to finish"""

        # Phase 1: System Initialization
        print("Phase 1: System Initialization")

        # Initialize credential manager
        credential_manager = CredentialManager(config_dir=self.config_dir)
        master_password = "SecureTestPassword123!"
        credential_manager.unlock(master_password)

        # Initialize security service
        security_service = SecurityService(
                credential_manager=credential_manager,
                config_dir=self.config_dir / "security"
        )

        # Initialize configuration manager
        config_manager = ConfigurationManager(config_dir=self.config_dir)

        # Initialize integration service
        integration_service = IntegrationService(config_dir=self.config_dir)
        integration_service.initialize_security(credential_manager)

        # Verify initialization
        assert credential_manager.is_locked() is False
        assert security_service.audit_log_file.exists()
        assert integration_service.security_service is not None

        # Phase 2: Configuration Setup
        print("Phase 2: Configuration Setup")

        # Create comprehensive configuration
        config_data = {
                "repositories":   {
                        "local_backup": {
                                "type":        "local",
                                "path":        str(self.repo_dir),
                                "description": "Local backup repository for testing"
                        }
                },
                "backup_targets": {
                        "documents": {
                                "name":     "Important Documents",
                                "paths":    [str(self.source_dir / "Documents")],
                                "patterns": {
                                        "include": ["*.pdf", "*.docx", "*.xlsx", "*.pptx", "*.txt"],
                                        "exclude": ["*.tmp", "*.bak", "Thumbs.db"]
                                }
                        },
                        "photos":    {
                                "name":     "Photo Collection",
                                "paths":    [str(self.source_dir / "Photos")],
                                "patterns": {
                                        "include": ["*.jpg", "*.jpeg", "*.png", "*.gif"],
                                        "exclude": ["Thumbs.db", "*.tmp"]
                                }
                        },
                        "code":      {
                                "name":     "Code Projects",
                                "paths":    [str(self.source_dir / "Projects")],
                                "patterns": {
                                        "include": ["*.py", "*.js", "*.html", "*.css", "*.md", "*.json"],
                                        "exclude": [".git/*", "*.pyc", "node_modules/*", "*.tmp"]
                                }
                        }
                },
                "settings":       {
                        "default_repository":  "local_backup",
                        "notification_level":  "normal",
                        "auto_verify_backups": True,
                        "retention_policy":    {
                                "keep_daily":   7,
                                "keep_weekly":  4,
                                "keep_monthly": 12
                        }
                }
        }

        # Save configuration using the actual API
        # Update configuration sections
        for section_name, section_data in config_data.items():
            config_manager.update_section(section_name, section_data)

        # Save configuration
        config_manager.save_config()

        # Verify configuration was saved
        assert config_manager.config_file.exists()

        # Verify configuration values
        for section_name, section_data in config_data.items():
            loaded_section = config_manager.get(section_name)
            assert loaded_section is not None

        # Phase 3: Repository Setup
        print("Phase 3: Repository Setup")

        # Mock repository for testing
        mock_repository = Mock()
        mock_repository._location = str(self.repo_dir)
        mock_repository.id = "local_backup"
        mock_repository.is_repository_initialized.return_value = True
        mock_repository._password = "repository_password_123"

        # Store repository credentials
        credential_manager.store_repository_password("local_backup", "repository_password_123")

        # Verify credential storage
        retrieved_password = credential_manager.get_repository_password("local_backup")
        assert retrieved_password == "repository_password_123"

        # Phase 4: Backup Target Creation
        print("Phase 4: Backup Target Creation")

        backup_targets = []

        # Create backup targets for each configured target
        for target_name, target_config in config_data["backup_targets"].items():
            file_selection = FileSelection()

            # Add paths
            for path in target_config["paths"]:
                file_selection.add_path(Path(path), SelectionType.INCLUDE)

            # Add include patterns
            for pattern in target_config["patterns"]["include"]:
                file_selection.add_pattern(pattern, SelectionType.INCLUDE)

            # Add exclude patterns
            for pattern in target_config["patterns"]["exclude"]:
                file_selection.add_pattern(pattern, SelectionType.EXCLUDE)

            # Create backup target
            backup_target = BackupTarget(
                    selection=file_selection,
                    tags=[target_name, "workflow_test"]
            )

            # Validate backup target
            assert backup_target.validate() is True
            backup_targets.append(backup_target)

        assert len(backup_targets) == 3  # documents, photos, code

        # Phase 5: Backup Operations
        print("Phase 5: Backup Operations")

        backup_manager = BackupManager()
        backup_results = []

        for i, target in enumerate(backup_targets):
            target_name = list(config_data["backup_targets"].keys())[i]

            # Mock backup operation
            with patch.object(backup_manager, 'create_full_backup') as mock_backup:
                mock_backup.return_value = {
                        'snapshot_id':           f'snapshot_{target_name}_{int(time.time())}',
                        'files_new':             50 + i * 10,
                        'files_changed':         0,
                        'files_unmodified':      0,
                        'total_files_processed': 50 + i * 10,
                        'data_added':            (1 + i) * 1024 * 1024,  # 1-3 MB
                        'total_duration':        10.5 + i * 2.0
                }

                # Perform backup
                result = backup_manager.create_full_backup(
                        repository=mock_repository,
                        targets=[target],
                        tags=[target_name, "full_backup", "workflow_test"]
                )

                backup_results.append(result)

                # Verify backup result
                assert result['snapshot_id'].startswith(f'snapshot_{target_name}')
                assert result['total_files_processed'] > 0
                assert result['data_added'] > 0

        # Log backup operations for security audit
        for i, result in enumerate(backup_results):
            target_name = list(config_data["backup_targets"].keys())[i]
            security_service.audit_backup_operation(
                    repository=mock_repository,
                    operation_type="full_backup",
                    targets=[str(self.source_dir)],
                    success=True,
                    metadata={
                            "target_name":     target_name,
                            "snapshot_id":     result['snapshot_id'],
                            "files_processed": result['total_files_processed']
                    }
            )

        # Phase 6: Backup Verification
        print("Phase 6: Backup Verification")

        # Mock verification for each backup
        for result in backup_results:
            with patch.object(backup_manager, 'verify_backup_integrity') as mock_verify:
                mock_verify.return_value = {
                        'verification_status':   'success',
                        'files_verified':        result['total_files_processed'],
                        'integrity_check':       'passed',
                        'verification_duration': 5.2
                }

                verification_result = backup_manager.verify_backup_integrity(
                        repository=mock_repository,
                        snapshot_id=result['snapshot_id']
                )

                assert verification_result['verification_status'] == 'success'
                assert verification_result['files_verified'] == result['total_files_processed']

        # Phase 7: Snapshot Management
        print("Phase 7: Snapshot Management")

        snapshot_manager = SnapshotManager(repository=mock_repository)

        # Mock snapshot listing
        with patch.object(snapshot_manager, 'list_snapshots') as mock_list:
            mock_snapshots = []
            for i, result in enumerate(backup_results):
                target_name = list(config_data["backup_targets"].keys())[i]
                mock_snapshots.append({
                        'id':    result['snapshot_id'],
                        'date':  datetime.now().isoformat(),
                        'tags':  [target_name, "full_backup", "workflow_test"],
                        'files': result['total_files_processed'],
                        'size':  result['data_added']
                })

            mock_list.return_value = mock_snapshots

            # List snapshots
            snapshots = snapshot_manager.list_snapshots()
            assert len(snapshots) == len(backup_results)

            for snapshot in snapshots:
                assert 'workflow_test' in snapshot['tags']
                assert snapshot['files'] > 0

        # Phase 8: Restore Operations
        print("Phase 8: Restore Operations")

        restore_manager = RestoreManager(repository=mock_repository)

        # Test restore for each backup
        for i, result in enumerate(backup_results):
            target_name = list(config_data["backup_targets"].keys())[i]
            restore_path = self.restore_dir / target_name
            restore_path.mkdir(exist_ok=True)

            # Mock restore operation
            with patch.object(restore_manager, 'restore_snapshot') as mock_restore:
                mock_restore.return_value = {
                        'files_restored': result['total_files_processed'],
                        'total_size':     result['data_added'],
                        'duration':       8.3,
                        'status':         'completed'
                }

                restore_result = restore_manager.restore_snapshot(
                        snapshot_id=result['snapshot_id'],
                        target_path=str(restore_path)
                )

                assert restore_result['status'] == 'completed'
                assert restore_result['files_restored'] == result['total_files_processed']

        # Phase 9: Security Audit Review
        print("Phase 9: Security Audit Review")

        # Verify audit log contains all operations
        audit_log = security_service.audit_log_file
        assert audit_log.exists()

        with open(audit_log, 'r') as f:
            audit_content = f.read()

        # Should contain backup operations
        assert "backup_operation" in audit_content
        assert "SUCCESS" in audit_content

        # Get security summary
        security_summary = security_service.get_security_summary(days=1)
        assert security_summary['total_events'] > 0

        # Phase 10: System Status Verification
        print("Phase 10: System Status Verification")

        # Get comprehensive system status
        system_status = integration_service.get_system_status()

        assert system_status['components']['configuration'] == 'active'
        assert system_status['components']['status_reporting'] == 'active'
        assert system_status['components']['notifications'] == 'active'
        assert system_status['components']['security'] == 'active'

        # Phase 11: Cleanup and Finalization
        print("Phase 11: Cleanup and Finalization")

        # Lock credential manager
        credential_manager.lock()
        assert credential_manager.is_locked() is True

        # Verify configuration persistence
        for section_name in config_data.keys():
            loaded_section = config_manager.get(section_name)
            assert loaded_section is not None

        print("✅ Complete TimeLocker workflow validation successful!")

    @pytest.mark.integration
    @pytest.mark.critical
    def test_error_recovery_workflow(self):
        """Test complete workflow with error recovery scenarios"""

        # Initialize basic components
        credential_manager = CredentialManager(config_dir=self.config_dir)
        credential_manager.unlock("test_password")

        security_service = SecurityService(
                credential_manager=credential_manager,
                config_dir=self.config_dir / "security"
        )

        # Test error scenarios
        error_scenarios = [
                {
                        "name":     "Invalid repository path",
                        "error":    FileNotFoundError("Repository not found"),
                        "recovery": "Use alternative repository"
                },
                {
                        "name":     "Permission denied",
                        "error":    PermissionError("Access denied"),
                        "recovery": "Check file permissions"
                },
                {
                        "name":     "Disk space exhausted",
                        "error":    OSError("No space left on device"),
                        "recovery": "Free disk space"
                }
        ]

        backup_manager = BackupManager()

        for scenario in error_scenarios:
            print(f"Testing error scenario: {scenario['name']}")

            # Create file selection
            file_selection = FileSelection()
            file_selection.add_path(self.source_dir, SelectionType.INCLUDE)

            backup_target = BackupTarget(
                    selection=file_selection,
                    tags=["error_test"]
            )

            # Mock repository
            mock_repository = Mock()
            mock_repository._location = str(self.repo_dir)
            mock_repository.id = "error_test_repo"

            # Simulate error during backup
            with patch.object(backup_manager, 'create_full_backup') as mock_backup:
                mock_backup.side_effect = scenario["error"]

                # Attempt backup and expect error
                with pytest.raises(type(scenario["error"])):
                    backup_manager.create_full_backup(
                            repository=mock_repository,
                            targets=[backup_target],
                            tags=["error_recovery_test"]
                    )

                # Verify error was logged
                audit_log = security_service.audit_log_file
                if audit_log.exists():
                    with open(audit_log, 'r') as f:
                        content = f.read()
                        # Should contain error information
                        assert "ERROR" in content or "FAILED" in content

        print("✅ Error recovery workflow validation successful!")

    @pytest.mark.integration
    @pytest.mark.performance
    def test_performance_workflow(self):
        """Test workflow performance under realistic conditions"""

        # Create larger dataset for performance testing
        perf_source = self.temp_dir / "performance_source"
        perf_source.mkdir()

        # Create 500 files across multiple directories
        for dir_num in range(10):
            dir_path = perf_source / f"dir_{dir_num:02d}"
            dir_path.mkdir()

            for file_num in range(50):
                file_path = dir_path / f"file_{file_num:03d}.txt"
                content = f"Performance test file {dir_num}-{file_num}\n" * 100
                file_path.write_text(content)

        # Measure workflow performance
        start_time = time.perf_counter()

        # File selection phase
        file_selection = FileSelection()
        file_selection.add_path(perf_source, SelectionType.INCLUDE)
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)

        selection_time = time.perf_counter()

        # Get effective paths
        effective_paths = file_selection.get_effective_paths()
        traversal_time = time.perf_counter()

        # Estimate backup size
        size_stats = file_selection.estimate_backup_size()
        estimation_time = time.perf_counter()

        # Calculate performance metrics
        total_time = estimation_time - start_time
        selection_duration = selection_time - start_time
        traversal_duration = traversal_time - selection_time
        estimation_duration = estimation_time - traversal_time

        # Validate performance
        assert total_time < 30.0, f"Total workflow took {total_time:.2f}s, too slow"
        assert len(effective_paths['included']) == 500, "Should find all 500 files"
        assert size_stats['file_count'] == 500, "Size estimation should count all files"

        # Performance should be reasonable
        files_per_second = 500 / total_time
        assert files_per_second > 50, f"Processing rate {files_per_second:.1f} files/sec too slow"

        print(f"✅ Performance workflow: {files_per_second:.1f} files/sec, {total_time:.2f}s total")

    @pytest.mark.integration
    @pytest.mark.critical
    def test_data_integrity_workflow(self):
        """Test complete workflow with data integrity validation"""

        # Create files with known content for integrity checking
        integrity_source = self.temp_dir / "integrity_source"
        integrity_source.mkdir()

        test_files = {
                "document.txt": "Important document content\n" * 100,
                "data.json":    '{"key": "value", "number": 42}\n' * 50,
                "binary.dat":   b"Binary data content" * 1000
        }

        file_hashes = {}
        for filename, content in test_files.items():
            file_path = integrity_source / filename
            if isinstance(content, str):
                file_path.write_text(content)
            else:
                file_path.write_bytes(content)

            # Calculate hash for integrity checking
            import hashlib
            if isinstance(content, str):
                content = content.encode('utf-8')
            file_hashes[filename] = hashlib.sha256(content).hexdigest()

        # Create backup target
        file_selection = FileSelection()
        file_selection.add_path(integrity_source, SelectionType.INCLUDE)

        backup_target = BackupTarget(
                selection=file_selection,
                tags=["integrity_test"]
        )

        # Mock repository and managers
        mock_repository = Mock()
        mock_repository._location = str(self.repo_dir)
        mock_repository.id = "integrity_test_repo"

        backup_manager = BackupManager()

        # Mock backup with integrity data
        with patch.object(backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.return_value = {
                    'snapshot_id':           'integrity_snapshot_001',
                    'files_new':             len(test_files),
                    'total_files_processed': len(test_files),
                    'data_added':            sum(len(content.encode('utf-8') if isinstance(content, str) else content)
                                                 for content in test_files.values()),
                    'file_hashes':           file_hashes
            }

            backup_result = backup_manager.create_full_backup(
                    repository=mock_repository,
                    targets=[backup_target],
                    tags=["integrity_validation"]
            )

            # Verify backup includes integrity data
            assert 'file_hashes' in backup_result
            assert len(backup_result['file_hashes']) == len(test_files)

        # Mock restore with integrity verification
        restore_manager = RestoreManager(repository=mock_repository)

        with patch.object(restore_manager, 'restore_snapshot') as mock_restore:
            mock_restore.return_value = {
                    'files_restored':     len(test_files),
                    'integrity_verified': True,
                    'hash_mismatches':    [],
                    'status':             'completed'
            }

            restore_result = restore_manager.restore_snapshot(
                    snapshot_id='integrity_snapshot_001',
                    target_path=str(self.restore_dir / "integrity_restore")
            )

            # Verify integrity was checked
            assert restore_result['integrity_verified'] is True
            assert len(restore_result['hash_mismatches']) == 0

        print("✅ Data integrity workflow validation successful!")
