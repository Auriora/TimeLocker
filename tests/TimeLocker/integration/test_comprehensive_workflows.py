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

        # Core managers
        self.backup_manager = BackupManager()
        self.restore_manager = RestoreManager()
        self.snapshot_manager = SnapshotManager()

        # Integration service
        self.integration_service = IntegrationService(
                backup_manager=self.backup_manager,
                restore_manager=self.restore_manager,
                security_service=self.security_service,
                status_reporter=self.status_reporter,
                notification_service=self.notification_service,
                config_manager=self.config_manager
        )

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
        with patch.object(self.backup_manager, 'create_backup') as mock_backup:
            mock_backup.return_value = {
                    "snapshot_id":     "test_snapshot_001",
                    "status":          "success",
                    "files_backed_up": 4,
                    "total_size":      1024
            }

            backup_result = self.integration_service.execute_backup(
                    repository_id="test_repo",
                    targets=[target],
                    tags=["integration_test"]
            )

            assert backup_result["status"] == "success"
            assert "snapshot_id" in backup_result

        # Step 3: Verify backup was logged
        status = self.status_reporter.get_operation_status(backup_result["operation_id"])
        assert status["status"] == "completed"

        # Step 4: List snapshots
        with patch.object(self.snapshot_manager, 'list_snapshots') as mock_list:
            mock_snapshots = [
                    {
                            "id":        "test_snapshot_001",
                            "timestamp": datetime.now().isoformat(),
                            "tags":      ["integration_test", "documents"],
                            "files":     4,
                            "size":      1024
                    }
            ]
            mock_list.return_value = mock_snapshots

            snapshots = self.snapshot_manager.list_snapshots("test_repo")
            assert len(snapshots) == 1
            assert snapshots[0]["id"] == "test_snapshot_001"

        # Step 5: Execute restore through integration service
        with patch.object(self.restore_manager, 'restore_snapshot') as mock_restore:
            mock_restore.return_value = {
                    "status":         "success",
                    "files_restored": 4,
                    "target_path":    str(self.restore_dir)
            }

            restore_result = self.integration_service.execute_restore(
                    repository_id="test_repo",
                    snapshot_id="test_snapshot_001",
                    target_path=self.restore_dir
            )

            assert restore_result["status"] == "success"
            assert restore_result["files_restored"] == 4

        # Step 6: Verify restore was logged
        restore_status = self.status_reporter.get_operation_status(restore_result["operation_id"])
        assert restore_status["status"] == "completed"

    def test_backup_failure_and_recovery_workflow(self):
        """Test workflow when backup fails and recovery procedures"""
        # Step 1: Configure backup that will fail
        selection = FileSelection()
        selection.add_path(self.source_dir, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["failure_test"])

        # Step 2: Execute backup that fails
        with patch.object(self.backup_manager, 'create_backup') as mock_backup:
            mock_backup.side_effect = Exception("Disk space exhausted")

            with pytest.raises(Exception):
                self.integration_service.execute_backup(
                        repository_id="test_repo",
                        targets=[target]
                )

        # Step 3: Verify failure was logged
        recent_operations = self.status_reporter.get_recent_operations(hours=1)
        failed_ops = [op for op in recent_operations if op["status"] == "error"]
        assert len(failed_ops) > 0

        # Step 4: Verify security event was logged
        # (In real implementation, would check security audit log)

        # Step 5: Test recovery - retry backup
        with patch.object(self.backup_manager, 'create_backup') as mock_backup_retry:
            mock_backup_retry.return_value = {
                    "snapshot_id":     "recovery_snapshot_001",
                    "status":          "success",
                    "files_backed_up": 10,
                    "total_size":      2048
            }

            recovery_result = self.integration_service.execute_backup(
                    repository_id="test_repo",
                    targets=[target],
                    tags=["recovery_test"]
            )

            assert recovery_result["status"] == "success"

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

        with patch.object(self.backup_manager, 'create_backup') as mock_backup:
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
                    repository_id="local_repo",
                    targets=[documents_target]
            )
            backup_results.append(result1)

            # Backup config to backup repository
            result2 = self.integration_service.execute_backup(
                    repository_id="backup_repo",
                    targets=[config_target]
            )
            backup_results.append(result2)

        # Verify both backups succeeded
        assert all(result["status"] == "success" for result in backup_results)
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

        # Simulate scheduled backup execution
        with patch.object(self.integration_service, 'execute_backup') as mock_execute:
            mock_execute.return_value = {
                    "snapshot_id":  "scheduled_snapshot_001",
                    "status":       "success",
                    "operation_id": "sched_op_001"
            }

            # Execute scheduled backup
            result = self.integration_service.execute_scheduled_backup(schedule_config)
            assert result["status"] == "success"

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

        # Load and execute configuration
        with patch.object(self.integration_service, 'execute_backup') as mock_execute:
            mock_execute.return_value = {
                    "snapshot_id": "config_snapshot_001",
                    "status":      "success"
            }

            # Execute configuration-driven backup
            result = self.integration_service.execute_from_config(str(config_file))
            assert result["status"] == "success"

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

        self.notification_service.update_config(notification_config)

        # Execute backup with monitoring
        selection = FileSelection()
        selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["monitored"])

        with patch.object(self.backup_manager, 'create_backup') as mock_backup, \
                patch.object(self.notification_service, 'send_notification') as mock_notify:
            mock_backup.return_value = {
                    "snapshot_id":     "monitored_snapshot_001",
                    "status":          "success",
                    "files_backed_up": 2,
                    "total_size":      512
            }

            # Execute monitored backup
            result = self.integration_service.execute_backup(
                    repository_id="test_repo",
                    targets=[target],
                    enable_monitoring=True
            )

            assert result["status"] == "success"

            # Verify notification was sent
            mock_notify.assert_called()

    def test_security_audit_workflow(self):
        """Test security auditing throughout workflow"""
        # Execute backup with security auditing
        selection = FileSelection()
        selection.add_path(self.source_dir / "config", SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["secure"])

        with patch.object(self.backup_manager, 'create_backup') as mock_backup:
            mock_backup.return_value = {
                    "snapshot_id": "secure_snapshot_001",
                    "status":      "success"
            }

            # Execute backup with security auditing
            result = self.integration_service.execute_backup(
                    repository_id="test_repo",
                    targets=[target],
                    enable_security_audit=True
            )

            assert result["status"] == "success"

        # Verify security events were logged
        audit_log = self.security_service.audit_log_file
        if audit_log.exists():
            with open(audit_log, 'r') as f:
                content = f.read()
                assert "backup_operation" in content

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
            with patch.object(self.backup_manager, 'create_backup') as mock_backup:
                mock_backup.side_effect = Exception(error_message)

                selection = FileSelection()
                selection.add_path(self.source_dir / "documents", SelectionType.INCLUDE)
                target = BackupTarget(selection=selection, tags=[error_type])

                # Execute backup that will fail
                with pytest.raises(Exception):
                    self.integration_service.execute_backup(
                            repository_id="test_repo",
                            targets=[target]
                    )

                # Verify error was logged
                recent_operations = self.status_reporter.get_recent_operations(hours=1)
                error_ops = [op for op in recent_operations
                             if op["status"] == "error" and error_message in op.get("error", "")]
                assert len(error_ops) > 0
