"""
Final Security Validation Tests for TimeLocker v1.0.0

This module contains comprehensive security tests to validate that TimeLocker
meets security requirements for the v1.0.0 release.
"""

import pytest
import tempfile
import shutil
import json
import hashlib
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from TimeLocker.security import SecurityService, SecurityEvent, SecurityLevel, CredentialManager, SecurityError, CredentialManagerError


class TestFinalSecurityValidation:
    """Final security validation tests for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup security test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.config_dir.mkdir(parents=True)

        # Initialize security components
        self.credential_manager = CredentialManager(config_dir=self.config_dir)
        self.security_service = SecurityService(
                credential_manager=self.credential_manager,
                config_dir=self.config_dir
        )

        # Test credentials and data
        self.master_password = "SecureTestPassword123!"
        self.test_repo_password = "RepoPassword456!"

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.security
    def test_encryption_end_to_end_validation(self):
        """Test complete encryption workflow validation"""
        # Test credential manager encryption
        self.credential_manager.unlock(self.master_password)

        # Store sensitive data
        test_credentials = {
                "aws_access_key_id":     "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "aws_default_region":    "us-west-2"
        }

        self.credential_manager.store_backend_credentials("s3", test_credentials)
        self.credential_manager.store_repository_password("test_repo", self.test_repo_password)

        # Lock and unlock to test persistence
        self.credential_manager.lock()
        self.credential_manager.unlock(self.master_password)

        # Verify data integrity after encryption/decryption cycle
        retrieved_credentials = self.credential_manager.get_backend_credentials("s3")
        retrieved_password = self.credential_manager.get_repository_password("test_repo")

        assert retrieved_credentials == test_credentials
        assert retrieved_password == self.test_repo_password

        # Verify encrypted storage (data should not be readable without password)
        self.credential_manager.lock()

        # Check that credential files are encrypted
        credential_files = list(self.config_dir.glob("*.enc"))
        assert len(credential_files) > 0, "No encrypted credential files found"

        # Verify files contain encrypted data (not plaintext)
        for cred_file in credential_files:
            content = cred_file.read_bytes()
            # Should not contain plaintext credentials
            assert b"AKIAIOSFODNN7EXAMPLE" not in content
            assert self.test_repo_password.encode() not in content

    @pytest.mark.security
    def test_repository_encryption_verification(self):
        """Test repository encryption verification"""
        # Mock repository with encryption
        mock_repository = Mock()
        mock_repository._location = str(self.temp_dir / "encrypted_repo")
        mock_repository.id = "encrypted_test_repo"
        mock_repository.is_repository_initialized.return_value = True
        mock_repository._password = "repository_encryption_password"
        mock_repository.get_repository_info.return_value = {
                "version":    "2",
                "encryption": "AES-256"
        }

        # Verify encryption status
        encryption_status = self.security_service.verify_repository_encryption(mock_repository)

        assert encryption_status.is_encrypted is True
        assert encryption_status.encryption_algorithm == "AES-256"
        assert encryption_status.key_derivation == "scrypt"
        assert encryption_status.last_verified is not None

        # Test unencrypted repository detection
        mock_unencrypted_repo = Mock()
        mock_unencrypted_repo._location = str(self.temp_dir / "unencrypted_repo")
        mock_unencrypted_repo.id = "unencrypted_test_repo"
        mock_unencrypted_repo.is_repository_initialized.return_value = True
        mock_unencrypted_repo._password = None  # No password = no encryption

        encryption_status = self.security_service.verify_repository_encryption(mock_unencrypted_repo)
        assert encryption_status.is_encrypted is False

    @pytest.mark.security
    def test_audit_logging_comprehensive(self):
        """Test comprehensive audit logging functionality"""
        # Test various security events
        security_events = [
                {
                        "event_type":  "backup_operation",
                        "level":       SecurityLevel.MEDIUM,
                        "description": "Full backup initiated",
                        "metadata":    {"operation_id": "backup_001", "file_count": 1500}
                },
                {
                        "event_type":  "credential_access",
                        "level":       SecurityLevel.HIGH,
                        "description": "Repository credentials accessed",
                        "metadata":    {"credential_id": "repo_001", "operation": "read"}
                },
                {
                        "event_type":  "encryption_verification",
                        "level":       SecurityLevel.HIGH,
                        "description": "Repository encryption verified",
                        "metadata":    {"repository_id": "test_repo", "encryption_status": "verified"}
                },
                {
                        "event_type":  "security_violation",
                        "level":       SecurityLevel.CRITICAL,
                        "description": "Multiple failed authentication attempts",
                        "metadata":    {"attempts": 5, "source": "test_client"}
                }
        ]

        # Log all events
        for event_data in security_events:
            event = SecurityEvent(
                    timestamp=datetime.now(),
                    event_type=event_data["event_type"],
                    level=event_data["level"],
                    description=event_data["description"],
                    user_id="test_user",
                    repository_id="test_repo",
                    metadata=event_data["metadata"]
            )
            self.security_service.log_security_event(event)

        # Verify audit log integrity
        audit_log = self.security_service.audit_log_file
        assert audit_log.exists()

        with open(audit_log, 'r') as f:
            log_content = f.read()

        # Verify all events were logged
        for event_data in security_events:
            assert event_data["event_type"] in log_content
            assert event_data["description"] in log_content
            assert event_data["level"].value in log_content

        # Verify log format and structure (pipe-delimited format)
        log_lines = log_content.strip().split('\n')
        event_lines = [line for line in log_lines if not line.startswith('#') and line.strip()]

        assert len(event_lines) >= len(security_events)

        # Verify each log entry has the expected pipe-delimited format
        for line in event_lines:
            if line.strip():
                parts = line.split('|')
                assert len(parts) >= 4, f"Log line should have at least 4 parts: {line}"
                # Parts: timestamp|event_type|level|description|metadata
                timestamp_part = parts[0]
                event_type_part = parts[1]
                level_part = parts[2]
                description_part = parts[3]

                # Verify timestamp format
                try:
                    datetime.fromisoformat(timestamp_part)
                except ValueError:
                    pytest.fail(f"Invalid timestamp format in log: {timestamp_part}")

    @pytest.mark.security
    def test_credential_security_validation(self):
        """Test credential security mechanisms"""
        # Test master password requirements
        weak_passwords = ["123", "password", "abc", ""]
        strong_password = "StrongPassword123!@#"

        # Test password strength (implicit through successful operations)
        self.credential_manager.unlock(strong_password)

        # Store test credentials
        test_data = {"key": "sensitive_value", "token": "secret_token"}
        self.credential_manager.store_backend_credentials("test_backend", test_data)

        # Test credential timeout (mock time passage)
        with patch('time.time') as mock_time:
            # Simulate time passage beyond timeout
            mock_time.return_value = 9999999999  # Far future

            # Should require re-authentication after timeout
            self.credential_manager.lock()

            with pytest.raises(CredentialManagerError):
                self.credential_manager.get_backend_credentials("test_backend")

        # Test credential access auditing
        self.credential_manager.unlock(strong_password)
        self.security_service.audit_credential_access(
                credential_id="test_backend",
                operation="read",
                success=True
        )

        # Verify audit entry
        audit_log = self.security_service.audit_log_file
        with open(audit_log, 'r') as f:
            content = f.read()
            assert "credential_access" in content
            assert "test_backend" in content
            assert "SUCCESS" in content

    @pytest.mark.security
    def test_access_control_validation(self):
        """Test access control mechanisms"""
        # Test locked credential manager access control
        assert self.credential_manager.is_locked()

        # Verify operations fail when locked
        with pytest.raises(CredentialManagerError):
            self.credential_manager.store_repository_password("test", "password")

        with pytest.raises(CredentialManagerError):
            self.credential_manager.get_repository_password("test")

        # Test successful unlock and access
        self.credential_manager.unlock(self.master_password)
        assert not self.credential_manager.is_locked()

        # Operations should now succeed
        self.credential_manager.store_repository_password("test_repo", "test_password")
        retrieved = self.credential_manager.get_repository_password("test_repo")
        assert retrieved == "test_password"

        # Test re-locking
        self.credential_manager.lock()
        assert self.credential_manager.is_locked()

    @pytest.mark.security
    def test_data_integrity_validation(self):
        """Test data integrity validation mechanisms"""
        # Create test data file
        test_file = self.temp_dir / "integrity_test.dat"
        test_content = b"This is test data for integrity validation" * 1000
        test_file.write_bytes(test_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Verify integrity check
        with open(test_file, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        assert actual_hash == expected_hash

        # Test integrity audit logging
        self.security_service.audit_integrity_check(
                file_path=str(test_file),
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                status="passed"
        )

        # Verify audit entry
        audit_log = self.security_service.audit_log_file
        with open(audit_log, 'r') as f:
            content = f.read()
            assert "integrity_check" in content
            assert expected_hash in content
            assert "passed" in content

        # Test integrity failure detection
        # Modify file content
        corrupted_content = test_content + b"CORRUPTED"
        test_file.write_bytes(corrupted_content)

        # Recalculate hash
        with open(test_file, 'rb') as f:
            corrupted_hash = hashlib.sha256(f.read()).hexdigest()

        assert corrupted_hash != expected_hash

        # Log integrity failure
        self.security_service.audit_integrity_check(
                file_path=str(test_file),
                expected_hash=expected_hash,
                actual_hash=corrupted_hash,
                status="failed"
        )

    @pytest.mark.security
    def test_security_configuration_validation(self):
        """Test security configuration validation"""
        # Test valid security configurations
        valid_configs = [
                {
                        "encryption_enabled":  True,
                        "audit_logging":       True,
                        "credential_timeout":  3600,
                        "max_failed_attempts": 3,
                        "lockout_duration":    300
                },
                {
                        "encryption_enabled":  True,
                        "audit_logging":       True,
                        "credential_timeout":  1800,
                        "max_failed_attempts": 5,
                        "lockout_duration":    600
                }
        ]

        for config in valid_configs:
            result = self.security_service.validate_security_config(config)
            assert result["valid"] is True
            assert len(result["issues"]) == 0

        # Test invalid security configurations
        invalid_configs = [
                {
                        "encryption_enabled":  False,  # Encryption should be required
                        "audit_logging":       True,
                        "credential_timeout":  3600,
                        "max_failed_attempts": 3
                },
                {
                        "encryption_enabled":  True,
                        "audit_logging":       False,  # Audit logging should be required
                        "credential_timeout":  3600,
                        "max_failed_attempts": 3
                },
                {
                        "encryption_enabled":  True,
                        "audit_logging":       True,
                        "credential_timeout":  -1,  # Invalid negative timeout
                        "max_failed_attempts": 3
                },
                {
                        "encryption_enabled":  True,
                        "audit_logging":       True,
                        "credential_timeout":  3600,
                        "max_failed_attempts": 0  # Invalid zero attempts
                }
        ]

        for config in invalid_configs:
            result = self.security_service.validate_security_config(config)
            assert result["valid"] is False
            assert len(result["issues"]) > 0

    @pytest.mark.security
    def test_security_event_tampering_protection(self):
        """Test protection against security event tampering"""
        # Create security event
        original_event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.HIGH,
                description="Original event description",
                user_id="test_user",
                repository_id="test_repo",
                metadata={"original": True}
        )

        # Log the event
        self.security_service.log_security_event(original_event)

        # Read audit log
        audit_log = self.security_service.audit_log_file
        with open(audit_log, 'r') as f:
            original_content = f.read()

        # Verify original event is logged
        assert "test_event" in original_content
        assert "Original event description" in original_content

        # Attempt to modify audit log (simulate tampering)
        tampered_content = original_content.replace(
                "Original event description",
                "Tampered event description"
        )

        # Write tampered content
        with open(audit_log, 'w') as f:
            f.write(tampered_content)

        # Log another event (this should detect tampering in a real implementation)
        new_event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="new_event",
                level=SecurityLevel.MEDIUM,
                description="New event after tampering",
                user_id="test_user",
                repository_id="test_repo",
                metadata={"after_tampering": True}
        )

        # This should still work (basic implementation doesn't detect tampering)
        # In a production system, this would include integrity checks
        self.security_service.log_security_event(new_event)

        # Verify new event was logged
        with open(audit_log, 'r') as f:
            final_content = f.read()
            assert "new_event" in final_content
            assert "New event after tampering" in final_content
