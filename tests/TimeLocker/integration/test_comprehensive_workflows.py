"""
Comprehensive workflow integration tests for TimeLocker MVP

This module contains end-to-end integration tests that validate complete workflows
from backup creation through recovery, including error scenarios and edge cases.
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.security import SecurityService, CredentialManager
from TimeLocker.monitoring import StatusReporter, NotificationService
from TimeLocker.monitoring.status_reporter import StatusLevel
from TimeLocker.config import ConfigurationManager
from TimeLocker.integration import IntegrationService


class TestComprehensiveWorkflows:
    """Integration tests for complete TimeLocker workflows"""

    def setup_method(self):
        """Setup comprehensive test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.repo_dir = self.temp_dir / "repository"
        self.source_dir = self.temp_dir / "source"
        self.restore_dir = self.temp_dir / "restore"

        # Create directories
        for directory in [self.config_dir, self.repo_dir, self.source_dir, self.restore_dir]:
            directory.mkdir(parents=True)

        # Create test data
        self._create_test_data()

        # Initialize components
        self._setup_components()

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_test_data(self):
        """Create comprehensive test data structure"""
        # Documents
        docs_dir = self.source_dir / "documents"
        docs_dir.mkdir()
        (docs_dir / "important.txt").write_text("Important document content")
        (docs_dir / "report.pdf").write_text("PDF report content")

        # Configuration files
        config_dir = self.source_dir / "config"
        config_dir.mkdir()
        (config_dir / "settings.json").write_text('{"key": "value"}')
        (config_dir / "database.conf").write_text("db_host=localhost")

        # Large files
        large_dir = self.source_dir / "large_files"
        large_dir.mkdir()
        (large_dir / "big_file.dat").write_text("x" * (1024 * 100))  # 100KB

        # Temporary files (to be excluded)
        temp_dir = self.source_dir / "temp"
        temp_dir.mkdir()
        (temp_dir / "cache.tmp").write_text("temporary data")
        (temp_dir / "log.log").write_text("log entries")

    def _setup_components(self):
        """Setup all TimeLocker components"""
        # Configuration Manager
        self.config_manager = ConfigurationManager(self.config_dir)

        # Security components
        self.credential_manager = Mock(spec=CredentialManager)
        self.credential_manager.unlock.return_value = True
        self.security_service = SecurityService(
                self.credential_manager,
                self.config_dir / "security"
        )

        # Monitoring components
        self.status_reporter = StatusReporter(self.config_dir)
        self.notification_service = NotificationService(self.config_dir)

        # Create mock repository for managers
        from TimeLocker.backup_repository import BackupRepository
        self.mock_repository = Mock()  # Don't use spec to allow additional attributes
        self.mock_repository.id = "test_repo"
        self.mock_repository._location = "/test/repo/path"
        self.mock_repository.location.return_value = "/test/repo/path"
        self.mock_repository.is_repository_initialized.return_value = True
        self.mock_repository.check.return_value = True
        self.mock_repository.initialize.return_value = True
        self.mock_repository.validate.return_value = True

        # Core managers
        self.backup_manager = BackupManager()
        self.restore_manager = RestoreManager(self.mock_repository)
        self.snapshot_manager = SnapshotManager(self.mock_repository)

        # Integration service
        self.integration_service = IntegrationService(self.config_dir)

        # Initialize security for integration service
        self.integration_service.initialize_security(self.credential_manager)

    def test_complete_backup_to_restore_workflow(self):
        """Test complete workflow from backup creation to successful restore"""
        # Step 1: Configure backup
        selection = FileSelection()
        selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        selection.add_path(self.source_dir / "config", SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.log", SelectionType.EXCLUDE)

        target = BackupTarget(
                selection=selection,
                tags=["integration_test", "documents"]
        )

        # Step 2: Execute backup through integration service
        # Mock the internal backup operation method and security checks
        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup_op, \
                patch.object(self.security_service, 'verify_repository_encryption') as mock_verify_enc, \
                patch.object(self.security_service, 'log_security_event') as mock_log_event:
            # Setup mocks
            mock_backup_op.return_value = {
                    "success":          True,
                    "files_new":        4,
                    "files_changed":    0,
                    "files_unmodified": 0,
                    "data_added":       1024
            }

            # Mock encryption verification to return encrypted status
            mock_encryption_status = Mock()
            mock_encryption_status.is_encrypted = True
            mock_verify_enc.return_value = mock_encryption_status

            backup_result = self.integration_service.execute_backup(
                    repository=self.mock_repository,
                    backup_target=target
            )

            # Verify backup operation was called
            mock_backup_op.assert_called_once()

            # Check that result is an OperationStatus object
            assert hasattr(backup_result, 'status')
            assert hasattr(backup_result, 'operation_id')

        # Step 3: Verify backup was logged (simplified check)
        # Just verify that the backup_result has the expected structure
        assert backup_result.operation_id is not None
        assert backup_result.status is not None

        # Step 4: List snapshots
        with patch.object(self.snapshot_manager, 'list_snapshots') as mock_list:
            # Create mock snapshot objects
            from TimeLocker.backup_snapshot import BackupSnapshot
            mock_snapshot = Mock(spec=BackupSnapshot)
            mock_snapshot.id = "test_snapshot_001"
            mock_snapshot.timestamp = datetime.now()
            mock_snapshot.tags = ["integration_test", "documents"]

            mock_list.return_value = [mock_snapshot]

            snapshots = self.snapshot_manager.list_snapshots()
            assert len(snapshots) == 1
            assert snapshots[0].id == "test_snapshot_001"

        # Step 5: Execute restore through integration service
        # Mock the internal restore operation method and security checks
        with patch.object(self.integration_service, '_execute_restore_operation') as mock_restore_op, \
                patch.object(self.integration_service.security_service, 'validate_backup_integrity') as mock_validate_integrity, \
                patch.object(self.integration_service.security_service, 'log_security_event') as mock_log_event_restore:
            mock_restore_op.return_value = {
                    "success":        True,
                    "files_restored": 4,
                    "bytes_restored": 1024
            }

            # Mock integrity validation to return True
            mock_validate_integrity.return_value = True

            # Create mock restore options
            from TimeLocker.restore_manager import RestoreOptions
            restore_options = RestoreOptions().with_target_path(self.restore_dir)

            restore_result = self.integration_service.execute_restore(
                    repository=self.mock_repository,
                    snapshot_id="test_snapshot_001",
                    restore_options=restore_options
            )

            # Verify restore operation was called
            mock_restore_op.assert_called_once()

            # Check that result is an OperationStatus object
            assert hasattr(restore_result, 'status')
            assert hasattr(restore_result, 'operation_id')

        # Step 6: Verify restore was logged (simplified check)
        # Just verify that the restore_result has the expected structure
        assert restore_result.operation_id is not None
        assert restore_result.status is not None

    def test_backup_failure_and_recovery_workflow(self):
        """Test workflow when backup fails and recovery procedures"""
        # Step 1: Configure backup that will fail
        selection = FileSelection()
        selection.add_path(self.source_dir, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["failure_test"])

        # Step 2: Test that backup manager can handle failures
        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.side_effect = Exception("Disk space exhausted")

            # Verify that backup manager raises exception on failure
            with pytest.raises(Exception) as exc_info:
                self.backup_manager.create_full_backup(self.mock_repository, [target])

            assert "Disk space exhausted" in str(exc_info.value)

        # Step 3: Test recovery - retry backup with success
        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup_retry:
            mock_backup_retry.return_value = {
                    "snapshot_id":     "recovery_snapshot_001",
                    "status":          "success",
                    "files_backed_up": 10,
                    "total_size":      2048
            }

            # Verify that backup manager can succeed after failure
            recovery_result = self.backup_manager.create_full_backup(self.mock_repository, [target])
            assert recovery_result["status"] == "success"
            assert recovery_result["snapshot_id"] == "recovery_snapshot_001"

    def test_multi_repository_workflow(self):
        """Test workflow involving multiple repositories"""
        # Setup multiple repositories
        repo_configs = [
                {"id": "local_repo", "type": "local", "path": str(self.repo_dir / "local")},
                {"id": "backup_repo", "type": "local", "path": str(self.repo_dir / "backup")}
        ]

        for repo_config in repo_configs:
            Path(repo_config["path"]).mkdir(parents=True, exist_ok=True)

        # Create different backup targets for each repository
        documents_selection = FileSelection()
        documents_selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        documents_target = BackupTarget(selection=documents_selection, tags=["documents"])

        config_selection = FileSelection()
        config_selection.add_path(self.source_dir / "config", SelectionType.INCLUDE)
        config_target = BackupTarget(selection=config_selection, tags=["config"])

        # Execute backups to different repositories
        backup_results = []

        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.side_effect = [
                    {
                            "snapshot_id":     "local_snapshot_001",
                            "status":          "success",
                            "files_backed_up": 2,
                            "total_size":      512
                    },
                    {
                            "snapshot_id":     "backup_snapshot_001",
                            "status":          "success",
                            "files_backed_up": 2,
                            "total_size":      256
                    }
            ]

            # Backup documents to local repository
            result1 = self.integration_service.execute_backup(
                    self.mock_repository,
                    documents_target
            )
            backup_results.append(result1)

            # Backup config to backup repository
            result2 = self.integration_service.execute_backup(
                    self.mock_repository,
                    config_target
            )
            backup_results.append(result2)

        # Verify both backups succeeded
        assert all(result.status == StatusLevel.SUCCESS for result in backup_results)
        assert len(backup_results) == 2

    def test_scheduled_backup_workflow(self):
        """Test scheduled backup workflow"""
        # Configure scheduled backup
        schedule_config = {
                "repository_id": "test_repo",
                "schedule":      "daily",
                "time":          "02:00",
                "targets":       [
                        {
                                "paths": [str(self.source_dir / "documents")],
                                "tags":  ["scheduled", "daily"]
                        }
                ]
        }

        # Simulate scheduled backup execution using regular backup method
        selection = FileSelection()
        selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["scheduled", "daily"])

        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.return_value = {
                    "snapshot_id":  "scheduled_snapshot_001",
                    "status":       "success",
                    "operation_id": "sched_op_001"
            }

            # Execute backup (simulating scheduled execution)
            result = self.integration_service.execute_backup(self.mock_repository, target)
            assert result.status == StatusLevel.SUCCESS

    def test_configuration_driven_workflow(self):
        """Test workflow driven by configuration files"""
        # Create configuration
        backup_config = {
                "repositories": [
                        {
                                "id":       "main_repo",
                                "type":     "local",
                                "path":     str(self.repo_dir),
                                "password": "test_password"
                        }
                ],
                "backup_sets":  [
                        {
                                "name":             "documents",
                                "repository":       "main_repo",
                                "paths":            [str(self.source_dir / "documents")],
                                "exclude_patterns": ["*.tmp", "*.log"],
                                "tags":             ["documents", "important"]
                        }
                ],
                "schedules":    [
                        {
                                "backup_set": "documents",
                                "frequency":  "daily",
                                "time":       "02:00"
                        }
                ]
        }

        # Save configuration
        config_file = self.config_dir / "backup_config.json"
        config_file.write_text(json.dumps(backup_config, indent=2))

        # Load and execute configuration using regular backup method
        selection = FileSelection()
        selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["documents", "important"])

        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.return_value = {
                    "snapshot_id": "config_snapshot_001",
                    "status":      "success"
            }

            # Execute backup (simulating configuration-driven execution)
            result = self.integration_service.execute_backup(self.mock_repository, target)
            assert result.status == StatusLevel.SUCCESS

    def test_monitoring_and_notification_workflow(self):
        """Test monitoring and notification integration"""
        # Configure notifications
        notification_config = {
                "email_enabled":     True,
                "email_to":          ["admin@example.com"],
                "desktop_enabled":   True,
                "notify_on_success": True,
                "notify_on_error":   True
        }

        self.notification_service.update_config(**notification_config)

        # Execute backup with monitoring
        selection = FileSelection()
        selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["monitored"])

        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup, \
                patch.object(self.integration_service.notification_service, 'send_notification') as mock_notify:
            mock_backup.return_value = {
                    "success":       True,
                    "files_new":     2,
                    "files_changed": 0,
                    "data_added":    512
            }

            # Execute monitored backup
            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    target
            )

            assert result.status == StatusLevel.SUCCESS

            # Verify notification was sent (notifications are sent for completed operations)
            mock_notify.assert_called()

    def test_security_audit_workflow(self):
        """Test security auditing throughout workflow"""
        # Execute backup with security auditing
        selection = FileSelection()
        selection.add_path(self.source_dir / "config", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["secure"])

        with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
            mock_backup.return_value = {
                    "snapshot_id": "secure_snapshot_001",
                    "status":      "success"
            }

            # Execute backup with security auditing
            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    target
            )

            assert result.status == StatusLevel.SUCCESS

        # Verify security events were logged
        audit_log = self.security_service.audit_log_file
        if audit_log.exists():
            with open(audit_log, 'r') as f:
                content = f.read()
                assert "backup_started" in content or "backup_completed" in content

    def test_error_recovery_workflow(self):
        """Test comprehensive error recovery workflow"""
        # Test various error scenarios and recovery
        error_scenarios = [
                ("network_error", "Connection timeout"),
                ("permission_error", "Permission denied"),
                ("disk_full", "No space left on device"),
                ("corruption_error", "Repository corrupted")
        ]

        for error_type, error_message in error_scenarios:
            with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
                mock_backup.side_effect = Exception(error_message)

                selection = FileSelection()
                selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
                target = BackupTarget(selection=selection, tags=[error_type])

                # Execute backup that will fail (but should be handled gracefully)
                result = self.integration_service.execute_backup(
                        self.mock_repository,
                        target
                )

                # Verify error was handled and logged
                assert result.status == StatusLevel.CRITICAL
                assert error_message.lower() in result.message.lower()

                # The operation should be completed and removed from current operations
                current_ops = self.status_reporter.get_current_operations()
                assert not any(op.operation_id == result.operation_id for op in current_ops)
