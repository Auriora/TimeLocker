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


class TestIntegrationService:
    """Test suite for IntegrationService"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.integration_service = IntegrationService(self.temp_dir)

        # Mock credential manager
        self.credential_manager = Mock(spec=CredentialManager)
        self.credential_manager.unlock.return_value = True

        # Initialize security service
        self.integration_service.initialize_security(self.credential_manager)

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test integration service initialization"""
        assert self.integration_service.config_manager is not None
        assert self.integration_service.status_reporter is not None
        assert self.integration_service.notification_service is not None
        assert self.integration_service.security_service is not None

    def test_security_initialization(self):
        """Test security service initialization"""
        # Create new service without security
        service = IntegrationService(self.temp_dir / "test2")
        assert service.security_service is None

        # Initialize security
        service.initialize_security(self.credential_manager)
        assert service.security_service is not None

    @patch('TimeLocker.integration.integration_service.IntegrationService._execute_backup_operation')
    def test_execute_backup_success(self, mock_backup):
        """Test successful backup execution"""
        # Setup mocks
        mock_repository = Mock()
        mock_repository.id = "test_repo"
        mock_repository._location = "/test/repo"

        mock_backup_target = Mock()
        mock_backup_target.paths = ["/test/path"]

        mock_backup.return_value = {
                "success":       True,
                "files_new":     100,
                "files_changed": 10,
                "data_added":    1024 * 1024
        }

        # Mock security service methods
        self.integration_service.security_service.verify_repository_encryption = Mock()
        self.integration_service.security_service.verify_repository_encryption.return_value = Mock(is_encrypted=True)

        # Execute backup
        result = self.integration_service.execute_backup(mock_repository, mock_backup_target)

        # Verify results
        assert result is not None
        assert result.status == StatusLevel.SUCCESS
        assert "successfully" in result.message.lower()
        assert result.operation_type == "backup"

        # Verify security logging was called
        assert self.integration_service.security_service.log_security_event.called

    @patch('TimeLocker.integration.integration_service.IntegrationService._execute_backup_operation')
    def test_execute_backup_failure(self, mock_backup):
        """Test backup execution failure"""
        # Setup mocks
        mock_repository = Mock()
        mock_repository.id = "test_repo"
        mock_repository._location = "/test/repo"

        mock_backup_target = Mock()
        mock_backup_target.paths = ["/test/path"]

        mock_backup.side_effect = Exception("Backup failed")

        # Mock security service methods
        self.integration_service.security_service.verify_repository_encryption = Mock()
        self.integration_service.security_service.verify_repository_encryption.return_value = Mock(is_encrypted=True)

        # Execute backup
        result = self.integration_service.execute_backup(mock_repository, mock_backup_target)

        # Verify results
        assert result is not None
        assert result.status == StatusLevel.CRITICAL
        assert "failed" in result.message.lower()
        assert result.operation_type == "backup"

    @patch('TimeLocker.integration.integration_service.IntegrationService._execute_restore_operation')
    def test_execute_restore_success(self, mock_restore):
        """Test successful restore execution"""
        # Setup mocks
        mock_repository = Mock()
        mock_repository.id = "test_repo"
        mock_repository._location = "/test/repo"

        mock_restore_options = Mock()
        mock_restore_options.target_path = "/restore/path"

        mock_restore.return_value = {
                "success":        True,
                "files_restored": 95,
                "bytes_restored": 1024 * 1024
        }

        # Mock security service methods
        self.integration_service.security_service.validate_backup_integrity = Mock(return_value=True)

        # Execute restore
        result = self.integration_service.execute_restore(
                mock_repository, "snapshot123", mock_restore_options
        )

        # Verify results
        assert result is not None
        assert result.status == StatusLevel.SUCCESS
        assert "successfully" in result.message.lower()
        assert result.operation_type == "restore"

        # Verify security validation was called
        self.integration_service.security_service.validate_backup_integrity.assert_called_once()

    @patch('TimeLocker.integration.integration_service.IntegrationService._execute_restore_operation')
    def test_execute_restore_integrity_failure(self, mock_restore):
        """Test restore execution with integrity failure"""
        # Setup mocks
        mock_repository = Mock()
        mock_repository.id = "test_repo"
        mock_repository._location = "/test/repo"

        mock_restore_options = Mock()
        mock_restore_options.target_path = "/restore/path"

        # Mock security service methods - integrity check fails
        self.integration_service.security_service.validate_backup_integrity = Mock(return_value=False)

        # Execute restore
        result = self.integration_service.execute_restore(
                mock_repository, "snapshot123", mock_restore_options
        )

        # Verify results
        assert result is not None
        assert result.status == StatusLevel.CRITICAL
        assert "failed" in result.message.lower()
        assert result.operation_type == "restore"

    def test_status_update_handling(self):
        """Test status update handling and notification integration"""
        # Create a mock status
        from TimeLocker.monitoring import OperationStatus

        status = OperationStatus(
                operation_id="test_op",
                operation_type="backup",
                status=StatusLevel.SUCCESS,
                message="Test operation completed",
                timestamp=datetime.now()
        )

        # Mock notification service
        with patch.object(self.integration_service.notification_service, 'send_notification') as mock_notify:
            # Trigger status update
            self.integration_service._handle_status_update(status)

            # Verify notification was sent
            mock_notify.assert_called_once_with(status)

    def test_security_event_handling(self):
        """Test security event handling"""
        from TimeLocker.security import SecurityEvent, SecurityLevel

        # Create a critical security event
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.CRITICAL,
                description="Test critical security event",
                repository_id="test_repo"
        )

        # Mock notification service
        with patch.object(self.integration_service.notification_service, 'send_notification') as mock_notify:
            # Trigger security event
            self.integration_service._handle_security_event(event)

            # Verify notification was sent
            mock_notify.assert_called_once()

            # Verify the status created for the notification
            call_args = mock_notify.call_args[0][0]
            assert call_args.operation_type == "security"
            assert call_args.status == StatusLevel.CRITICAL

    def test_get_system_status(self):
        """Test system status retrieval"""
        status = self.integration_service.get_system_status()

        # Verify status structure
        assert "timestamp" in status
        assert "components" in status
        assert "current_operations" in status
        assert "configuration_summary" in status
        assert "security_summary" in status
        assert "status_summary" in status

        # Verify component status
        components = status["components"]
        assert components["configuration"] == "active"
        assert components["status_reporting"] == "active"
        assert components["notifications"] == "active"
        assert components["security"] == "active"

    def test_configuration_integration(self):
        """Test configuration integration with other components"""
        # Update notification configuration
        self.integration_service.config_manager.update_section(
                "notifications",
                {
                        "enabled":         True,
                        "desktop_enabled": False,
                        "email_enabled":   True
                }
        )

        # Verify configuration is accessible
        notification_config = self.integration_service.config_manager.get("notifications")
        assert notification_config["enabled"] is True
        assert notification_config["desktop_enabled"] is False
        assert notification_config["email_enabled"] is True

    def test_operation_tracking(self):
        """Test operation tracking across components"""
        # Start an operation
        operation_id = "test_operation_123"
        status = self.integration_service.status_reporter.start_operation(
                operation_id=operation_id,
                operation_type="test",
                repository_id="test_repo"
        )

        assert status.operation_id == operation_id
        assert status.operation_type == "test"

        # Update operation
        updated_status = self.integration_service.status_reporter.update_operation(
                operation_id=operation_id,
                status=StatusLevel.INFO,
                message="Operation in progress",
                progress_percentage=50
        )

        assert updated_status.progress_percentage == 50
        assert updated_status.message == "Operation in progress"

        # Complete operation
        final_status = self.integration_service.status_reporter.complete_operation(
                operation_id=operation_id,
                status=StatusLevel.SUCCESS,
                message="Operation completed"
        )

        assert final_status.status == StatusLevel.SUCCESS
        assert final_status.message == "Operation completed"

        # Verify operation is no longer in current operations
        current_ops = self.integration_service.status_reporter.get_current_operations()
        assert not any(op.operation_id == operation_id for op in current_ops)

    def test_error_handling(self):
        """Test error handling in integration scenarios"""
        # Test with invalid repository
        mock_repository = None
        mock_backup_target = Mock()

        # This should handle the error gracefully
        result = self.integration_service.execute_backup(mock_repository, mock_backup_target)

        # Verify error was handled
        assert result is not None
        assert result.status == StatusLevel.CRITICAL
