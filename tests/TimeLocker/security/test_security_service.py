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
from unittest.mock import Mock, patch
from datetime import datetime

from TimeLocker.security import SecurityService, SecurityEvent, SecurityLevel, CredentialManager


class TestSecurityService:
    """Test suite for SecurityService"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Mock credential manager
        self.credential_manager = Mock(spec=CredentialManager)
        self.credential_manager.unlock.return_value = True

        # Create security service
        self.security_service = SecurityService(
                self.credential_manager,
                self.temp_dir / "security"
        )

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test security service initialization"""
        assert self.security_service.credential_manager == self.credential_manager
        assert self.security_service.config_dir.exists()
        assert self.security_service.audit_log_file.exists()

    def test_audit_log_initialization(self):
        """Test audit log file initialization"""
        # Check that audit log was created with proper headers
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "TimeLocker Security Audit Log" in content
            assert "Initialized:" in content
            assert "Format:" in content

    def test_log_security_event(self):
        """Test security event logging"""
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.MEDIUM,
                description="Test security event",
                user_id="test_user",
                repository_id="test_repo",
                metadata={"key": "value"}
        )

        # Log the event
        self.security_service.log_security_event(event)

        # Verify event was logged
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert event.event_type in content
            assert event.description in content
            assert event.level.value in content

    def test_event_handlers(self):
        """Test security event handlers"""
        handler_called = False
        received_event = None

        def test_handler(event):
            nonlocal handler_called, received_event
            handler_called = True
            received_event = event

        # Add handler
        self.security_service.add_event_handler(test_handler)

        # Create and log event
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.HIGH,
                description="Test event for handler"
        )

        self.security_service.log_security_event(event)

        # Verify handler was called
        assert handler_called
        assert received_event == event

        # Test handler removal
        self.security_service.remove_event_handler(test_handler)
        handler_called = False

        self.security_service.log_security_event(event)
        assert not handler_called

    def test_verify_repository_encryption_encrypted(self):
        """Test repository encryption verification for encrypted repository"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.is_repository_initialized.return_value = True
        mock_repository._password = "test_password"
        mock_repository.get_repository_info.return_value = {
                "id":      "test_repo",
                "version": "1.0"
        }
        mock_repository._location = "/test/repo"

        # Verify encryption
        status = self.security_service.verify_repository_encryption(mock_repository)

        # Check results
        assert status.is_encrypted is True
        assert status.encryption_algorithm == "AES-256"
        assert status.key_derivation == "scrypt"
        assert status.last_verified is not None
        assert status.verification_hash is not None

    def test_verify_repository_encryption_unencrypted(self):
        """Test repository encryption verification for unencrypted repository"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.is_repository_initialized.return_value = True
        mock_repository._password = None
        mock_repository.get_repository_info.return_value = {
                "id":      "test_repo",
                "version": "1.0"
        }
        mock_repository._location = "/test/repo"

        # Verify encryption
        status = self.security_service.verify_repository_encryption(mock_repository)

        # Check results
        assert status.is_encrypted is False
        assert status.encryption_algorithm is None
        assert status.key_derivation is None

    def test_verify_repository_encryption_uninitialized(self):
        """Test repository encryption verification for uninitialized repository"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.is_repository_initialized.return_value = False

        # Verify encryption
        status = self.security_service.verify_repository_encryption(mock_repository)

        # Check results
        assert status.is_encrypted is False

    def test_validate_backup_integrity_success(self):
        """Test successful backup integrity validation"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.check.return_value = "Repository integrity check passed"
        mock_repository._location = "/test/repo"

        # Validate integrity
        result = self.security_service.validate_backup_integrity(mock_repository)

        # Check results
        assert result is True
        mock_repository.check.assert_called_once()

    def test_validate_backup_integrity_failure(self):
        """Test failed backup integrity validation"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.check.return_value = "Error: Repository corruption detected"
        mock_repository._location = "/test/repo"

        # Validate integrity
        result = self.security_service.validate_backup_integrity(mock_repository)

        # Check results
        assert result is False
        mock_repository.check.assert_called_once()

    def test_validate_backup_integrity_specific_snapshot(self):
        """Test backup integrity validation for specific snapshot"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.check_snapshot.return_value = "Snapshot integrity check passed"
        mock_repository._location = "/test/repo"

        # Validate integrity for specific snapshot
        result = self.security_service.validate_backup_integrity(mock_repository, "snapshot123")

        # Check results
        assert result is True
        mock_repository.check_snapshot.assert_called_once_with("snapshot123")

    def test_validate_backup_integrity_exception(self):
        """Test backup integrity validation with exception"""
        # Mock repository
        mock_repository = Mock()
        mock_repository.check.side_effect = Exception("Check failed")
        mock_repository._location = "/test/repo"

        # Validate integrity
        result = self.security_service.validate_backup_integrity(mock_repository)

        # Check results
        assert result is False

    def test_audit_credential_access(self):
        """Test credential access auditing"""
        # Audit credential access
        self.security_service.audit_credential_access(
                credential_id="test_cred",
                operation="read",
                success=True
        )

        # Verify event was logged
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "credential_access" in content
            assert "test_cred" in content
            assert "read" in content
            assert "SUCCESS" in content

    def test_get_security_summary(self):
        """Test security summary generation"""
        # Log some test events
        events = [
                SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="backup_started",
                        level=SecurityLevel.MEDIUM,
                        description="Backup started"
                ),
                SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="encryption_verification",
                        level=SecurityLevel.HIGH,
                        description="Encryption verified"
                ),
                SecurityEvent(
                        timestamp=datetime.now(),
                        event_type="backup_completed",
                        level=SecurityLevel.MEDIUM,
                        description="Backup completed"
                )
        ]

        for event in events:
            self.security_service.log_security_event(event)

        # Get summary
        summary = self.security_service.get_security_summary(days=7)

        # Verify summary structure
        assert "period_days" in summary
        assert "total_events" in summary
        assert "events_by_type" in summary
        assert "events_by_level" in summary
        assert "generated_at" in summary

        # Verify summary content
        assert summary["period_days"] == 7
        assert summary["total_events"] >= 3  # At least our test events
        assert "backup_started" in summary["events_by_type"]
        assert "medium" in summary["events_by_level"]

    def test_security_event_creation(self):
        """Test SecurityEvent dataclass"""
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.CRITICAL,
                description="Test event",
                user_id="user123",
                repository_id="repo456",
                metadata={"test": "data"}
        )

        assert event.event_type == "test_event"
        assert event.level == SecurityLevel.CRITICAL
        assert event.description == "Test event"
        assert event.user_id == "user123"
        assert event.repository_id == "repo456"
        assert event.metadata["test"] == "data"

    def test_encryption_status_creation(self):
        """Test EncryptionStatus dataclass"""
        from TimeLocker.security.security_service import EncryptionStatus

        status = EncryptionStatus(
                is_encrypted=True,
                encryption_algorithm="AES-256",
                key_derivation="scrypt",
                last_verified=datetime.now(),
                verification_hash="abc123"
        )

        assert status.is_encrypted is True
        assert status.encryption_algorithm == "AES-256"
        assert status.key_derivation == "scrypt"
        assert status.verification_hash == "abc123"

    def test_error_handling_in_event_logging(self):
        """Test error handling in security event logging"""

        # Create event with handler that raises exception
        def failing_handler(event):
            raise Exception("Handler failed")

        self.security_service.add_event_handler(failing_handler)

        # This should not raise an exception
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.MEDIUM,
                description="Test event"
        )

        # Should complete without raising exception
        self.security_service.log_security_event(event)

        # Event should still be logged despite handler failure
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "test_event" in content
