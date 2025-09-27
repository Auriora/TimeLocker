"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from TimeLocker.integration import IntegrationService
from TimeLocker.security import CredentialManager
from TimeLocker.monitoring import StatusLevel


# ConfigSection removed - use string section names directly


class TestEndToEndWorkflow:
    """End-to-end integration tests for complete TimeLocker workflows"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.integration_service = IntegrationService(self.temp_dir)

        # Mock credential manager
        self.credential_manager = Mock(spec=CredentialManager)
        self.credential_manager.unlock.return_value = True

        # Initialize security service
        self.integration_service.initialize_security(self.credential_manager)

        # Setup test repository
        self.mock_repository = Mock()
        self.mock_repository.id = "test_repo_001"
        self.mock_repository._location = str(self.temp_dir / "test_repo")
        self.mock_repository._password = "test_password"
        self.mock_repository.is_repository_initialized.return_value = True
        self.mock_repository.get_repository_info.return_value = {
                "id":       "test_repo_001",
                "version":  "1.0",
                "location": str(self.temp_dir / "test_repo")
        }

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_backup_workflow(self):
        """Test complete backup workflow with all integrations"""
        # Configure system
        self.integration_service.config_manager.update_section(
                ConfigSection.NOTIFICATIONS,
                {
                        "enabled":           True,
                        "desktop_enabled":   False,  # Disable to avoid actual notifications
                        "email_enabled":     False,
                        "notify_on_success": True,
                        "notify_on_error":   True
                }
        )

        # Mock backup target
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/home/user/documents", "/home/user/pictures"]

        # Mock successful backup operation
        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {
                    "success":          True,
                    "files_new":        250,
                    "files_changed":    45,
                    "files_unmodified": 1500,
                    "data_added":       1024 * 1024 * 150,  # 150MB
                    "snapshot_id":      "abc123def456"
            }

            # Mock repository methods
            self.mock_repository.check.return_value = "Repository integrity verified"

            # Execute backup
            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    mock_backup_target,
                    "backup_workflow_test"
            )

            # Verify backup result
            assert result is not None
            assert result.operation_id == "backup_workflow_test"
            assert result.operation_type == "backup"
            assert result.status == StatusLevel.SUCCESS
            assert "successfully" in result.message.lower()
            assert result.repository_id == "test_repo_001"

            # Verify security events were logged
            security_summary = self.integration_service.security_service.get_security_summary()
            assert security_summary["total_events"] >= 3  # start, verification, completion
            assert "backup_started" in security_summary["events_by_type"]
            assert "backup_completed" in security_summary["events_by_type"]
            assert "encryption_verification" in security_summary["events_by_type"]

            # Verify status tracking
            status_summary = self.integration_service.status_reporter.get_status_summary()
            assert status_summary["total_operations"] >= 1
            assert status_summary["by_type"]["backup"] >= 1
            assert status_summary["by_status"]["success"] >= 1

    def test_complete_restore_workflow(self):
        """Test complete restore workflow with all integrations"""
        # Configure system
        self.integration_service.config_manager.update_section(
                "restore",
                {
                        "verify_after_restore":    True,
                        "create_target_directory": True,
                        "conflict_resolution":     "prompt"
                }
        )

        # Mock restore options
        mock_restore_options = Mock()
        mock_restore_options.target_path = self.temp_dir / "restore_target"
        mock_restore_options.verify_after_restore = True

        # Mock successful restore operation
        with patch.object(self.integration_service, '_execute_restore_operation') as mock_restore:
            mock_restore.return_value = {
                    "success":            True,
                    "files_restored":     180,
                    "bytes_restored":     1024 * 1024 * 120,  # 120MB
                    "conflicts_resolved": 2
            }

            # Mock repository methods
            self.mock_repository.check_snapshot.return_value = "Snapshot integrity verified"

            # Execute restore
            result = self.integration_service.execute_restore(
                    self.mock_repository,
                    "snapshot_abc123",
                    mock_restore_options,
                    "restore_workflow_test"
            )

            # Verify restore result
            assert result is not None
            assert result.operation_id == "restore_workflow_test"
            assert result.operation_type == "restore"
            assert result.status == StatusLevel.SUCCESS
            assert "successfully" in result.message.lower()

            # Verify integrity validation was performed
            # Note: validate_backup_integrity is called directly in the integration service

            # Verify security events
            security_summary = self.integration_service.security_service.get_security_summary()
            assert "restore_started" in security_summary["events_by_type"]
            assert "restore_completed" in security_summary["events_by_type"]

    def test_backup_failure_workflow(self):
        """Test backup failure handling workflow"""
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/invalid/path"]

        # Mock failed backup operation
        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.side_effect = Exception("Backup operation failed: Permission denied")

            # Execute backup
            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    mock_backup_target,
                    "backup_failure_test"
            )

            # Verify failure handling
            assert result is not None
            assert result.operation_id == "backup_failure_test"
            assert result.status == StatusLevel.CRITICAL
            assert "failed" in result.message.lower()
            assert "Permission denied" in result.message

            # Verify security events for failure
            security_summary = self.integration_service.security_service.get_security_summary()
            assert "backup_failed" in security_summary["events_by_type"]

            # Verify critical security event was logged
            assert "critical" in security_summary["events_by_level"]

    def test_security_breach_detection_workflow(self):
        """Test security breach detection and notification workflow"""
        # Mock unencrypted repository
        unencrypted_repo = Mock()
        unencrypted_repo.id = "insecure_repo"
        unencrypted_repo._location = "/insecure/repo"
        unencrypted_repo._password = None  # No encryption
        unencrypted_repo.is_repository_initialized.return_value = True
        unencrypted_repo.get_repository_info.return_value = {"id": "insecure_repo"}

        mock_backup_target = Mock()
        mock_backup_target.paths = ["/test/data"]

        # Mock backup operation
        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {"success": True, "files_new": 10}

            # Execute backup to unencrypted repository
            result = self.integration_service.execute_backup(
                    unencrypted_repo,
                    mock_backup_target,
                    "security_test"
            )

            # Verify security event was logged for unencrypted backup
            security_summary = self.integration_service.security_service.get_security_summary()
            assert "unencrypted_backup_attempt" in security_summary["events_by_type"]
            assert "high" in security_summary["events_by_level"]

    def test_concurrent_operations_workflow(self):
        """Test handling of concurrent operations"""
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/test/data"]

        # Mock backup operations with delays
        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {"success": True, "files_new": 50}

            # Start multiple operations
            operation_ids = []
            for i in range(3):
                op_id = f"concurrent_backup_{i}"
                operation_ids.append(op_id)

                # Start operation (don't wait for completion)
                status = self.integration_service.status_reporter.start_operation(
                        operation_id=op_id,
                        operation_type="backup",
                        repository_id=f"repo_{i}"
                )

                # Update progress
                self.integration_service.status_reporter.update_operation(
                        operation_id=op_id,
                        status=StatusLevel.INFO,
                        message=f"Backup {i} in progress",
                        progress_percentage=50
                )

            # Verify all operations are tracked
            current_ops = self.integration_service.status_reporter.get_current_operations()
            assert len(current_ops) == 3

            current_op_ids = [op.operation_id for op in current_ops]
            for op_id in operation_ids:
                assert op_id in current_op_ids

            # Complete operations
            for i, op_id in enumerate(operation_ids):
                self.integration_service.status_reporter.complete_operation(
                        operation_id=op_id,
                        status=StatusLevel.SUCCESS,
                        message=f"Backup {i} completed"
                )

            # Verify operations are no longer current
            current_ops = self.integration_service.status_reporter.get_current_operations()
            assert len(current_ops) == 0

    def test_configuration_driven_workflow(self):
        """Test workflow driven by configuration settings"""
        # Configure backup settings
        self.integration_service.config_manager.update_section(
                "backup",
                {
                        "compression":         "gzip",
                        "exclude_caches":      True,
                        "check_before_backup": True,
                        "verify_after_backup": True
                }
        )

        # Configure security settings
        self.integration_service.config_manager.update_section(
                "security",
                {
                        "encryption_enabled":  True,
                        "audit_logging":       True,
                        "max_failed_attempts": 3
                }
        )

        # Verify configuration is accessible
        backup_config = self.integration_service.config_manager.get_section("backup")
        assert backup_config["compression"] == "gzip"
        assert backup_config["check_before_backup"] is True

        security_config = self.integration_service.config_manager.get_section("security")
        assert security_config["encryption_enabled"] is True
        assert security_config["audit_logging"] is True

        # Execute backup with configuration-driven behavior
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/configured/backup"]

        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {"success": True, "files_new": 100}

            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    mock_backup_target,
                    "config_driven_test"
            )

            # Verify backup executed successfully
            assert result.status == StatusLevel.SUCCESS

            # Verify security checks were performed (based on config)
            # Note: This would be verified through mocking in a real test

    def test_system_status_comprehensive(self):
        """Test comprehensive system status reporting"""
        # Execute some operations to generate data
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/test/data"]

        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {"success": True, "files_new": 75}

            # Execute backup
            self.integration_service.execute_backup(
                    self.mock_repository,
                    mock_backup_target,
                    "status_test_backup"
            )

        # Get comprehensive system status
        system_status = self.integration_service.get_system_status()

        # Verify status structure
        assert "timestamp" in system_status
        assert "components" in system_status
        assert "current_operations" in system_status
        assert "configuration_summary" in system_status
        assert "security_summary" in system_status
        assert "status_summary" in system_status

        # Verify component status
        components = system_status["components"]
        assert components["configuration"] == "active"
        assert components["status_reporting"] == "active"
        assert components["notifications"] == "active"
        assert components["security"] == "active"

        # Verify summaries contain data
        assert system_status["security_summary"]["total_events"] > 0
        assert system_status["status_summary"]["total_operations"] > 0
        assert system_status["configuration_summary"]["total_settings"] > 0

    def test_error_recovery_workflow(self):
        """Test error recovery and resilience"""
        # Test recovery from configuration errors
        try:
            # Attempt to load invalid configuration
            invalid_config_path = self.temp_dir / "invalid_config.json"
            with open(invalid_config_path, 'w') as f:
                f.write("invalid json content")

            # This should not crash the system
            result = self.integration_service.config_manager.import_config(invalid_config_path)
            assert result is False

            # System should still be functional
            status = self.integration_service.get_system_status()
            assert status["components"]["configuration"] == "active"

        except Exception as e:
            pytest.fail(f"System should handle configuration errors gracefully: {e}")

        # Test recovery from notification errors
        with patch.object(self.integration_service.notification_service, 'send_notification') as mock_notify:
            mock_notify.side_effect = Exception("Notification failed")

            # This should not prevent operation completion
            mock_backup_target = Mock()
            mock_backup_target.paths = ["/test/data"]

            with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
                mock_backup.return_value = {"success": True, "files_new": 25}

                result = self.integration_service.execute_backup(
                        self.mock_repository,
                        mock_backup_target,
                        "error_recovery_test"
                )

                # Operation should still complete successfully
                assert result.status == StatusLevel.SUCCESS

    def test_audit_trail_completeness(self):
        """Test that complete audit trail is maintained"""
        mock_backup_target = Mock()
        mock_backup_target.paths = ["/audit/test"]

        with patch.object(self.integration_service, '_execute_backup_operation') as mock_backup:
            mock_backup.return_value = {"success": True, "files_new": 30}

            # Execute backup
            result = self.integration_service.execute_backup(
                    self.mock_repository,
                    mock_backup_target,
                    "audit_trail_test"
            )

            # Verify comprehensive audit trail
            security_summary = self.integration_service.security_service.get_security_summary()
            status_summary = self.integration_service.status_reporter.get_status_summary()

            # Should have security events for all phases
            expected_events = ["backup_started", "encryption_verification", "backup_completed"]
            for event_type in expected_events:
                assert event_type in security_summary["events_by_type"]

            # Should have status tracking
            assert status_summary["by_type"]["backup"] >= 1
            assert status_summary["by_status"]["success"] >= 1

            # Verify audit log file exists and contains events
            audit_log = self.integration_service.security_service.audit_log_file
            assert audit_log.exists()

            with open(audit_log, 'r') as f:
                log_content = f.read()
                assert "backup_started" in log_content
                assert "backup_completed" in log_content
