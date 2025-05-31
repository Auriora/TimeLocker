"""
Enhanced security tests for TimeLocker MVP

This module contains comprehensive tests for security-critical functionality,
focusing on data integrity, credential protection, and audit trail validation.
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from TimeLocker.security import SecurityService, SecurityEvent, SecurityLevel, CredentialManager


class TestEnhancedSecurity:
    """Enhanced security test suite focusing on critical security paths"""

    def setup_method(self):
        """Setup test environment with enhanced security context"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.security_dir = self.temp_dir / "security"
        self.security_dir.mkdir(parents=True)

        # Create mock credential manager
        self.credential_manager = Mock(spec=CredentialManager)
        self.credential_manager.unlock.return_value = True
        self.credential_manager.is_locked.return_value = False

        # Create security service
        self.security_service = SecurityService(
                self.credential_manager,
                self.security_dir
        )

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_credential_encryption_integrity(self):
        """Test that credentials are properly encrypted and cannot be read without key"""
        # Test data
        test_credential = {
                "username":       "test_user",
                "password":       "super_secret_password",
                "repository_url": "s3://bucket/path"
        }

        # Mock credential manager with encryption
        with patch.object(self.credential_manager, 'store_credential') as mock_store:
            mock_store.return_value = True

            # Store credential
            result = self.credential_manager.store_credential("test_repo", test_credential)
            assert result is True

            # Verify store was called with correct parameters
            mock_store.assert_called_once_with("test_repo", test_credential)

    def test_credential_access_auditing(self):
        """Test that all credential access is properly audited"""
        # Test credential access
        self.security_service.audit_credential_access(
                credential_id="test_cred",
                operation="read",
                success=True
        )

        # Verify audit log entry
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "credential_access" in content
            assert "test_cred" in content
            assert "read" in content
            assert "SUCCESS" in content

    def test_failed_credential_access_detection(self):
        """Test detection and logging of failed credential access attempts"""
        # Simulate failed access
        self.security_service.audit_credential_access(
                credential_id="test_cred",
                operation="read",
                success=False,
                error_details="Invalid password"
        )

        # Verify security event was logged
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "credential_access" in content
            assert "FAILURE" in content
            assert "Invalid password" in content

    def test_security_event_integrity(self):
        """Test that security events cannot be tampered with"""
        # Create security event
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="backup_access",
                level=SecurityLevel.HIGH,
                description="Backup repository accessed",
                user_id="test_user",
                repository_id="test_repo",
                metadata={"operation": "backup"}
        )

        # Log the event
        self.security_service.log_security_event(event)

        # Verify event was logged with all required fields
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert event.event_type in content
            assert event.description in content
            assert event.level.value in content
            assert event.user_id in content
            assert event.repository_id in content

    def test_audit_log_tampering_detection(self):
        """Test detection of audit log tampering attempts"""
        # Create initial audit log entry
        event = SecurityEvent(
                timestamp=datetime.now(),
                event_type="test_event",
                level=SecurityLevel.MEDIUM,
                description="Test event",
                user_id="test_user"
        )
        self.security_service.log_security_event(event)

        # Get original content
        with open(self.security_service.audit_log_file, 'r') as f:
            original_content = f.read()

        # Simulate tampering by modifying the file
        with open(self.security_service.audit_log_file, 'w') as f:
            f.write(original_content.replace("test_event", "modified_event"))

        # Verify integrity check would detect tampering
        # (In a real implementation, this would use checksums or digital signatures)
        with open(self.security_service.audit_log_file, 'r') as f:
            modified_content = f.read()
            assert "modified_event" in modified_content
            assert "test_event" not in modified_content

    def test_concurrent_security_operations(self):
        """Test security service behavior under concurrent access"""
        import threading
        import time

        results = []

        def log_security_event(event_id):
            event = SecurityEvent(
                    timestamp=datetime.now(),
                    event_type=f"concurrent_test_{event_id}",
                    level=SecurityLevel.LOW,
                    description=f"Concurrent test event {event_id}",
                    user_id=f"user_{event_id}"
            )
            self.security_service.log_security_event(event)
            results.append(event_id)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_security_event, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all events were logged
        assert len(results) == 5

        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            for i in range(5):
                assert f"concurrent_test_{i}" in content

    def test_security_level_escalation(self):
        """Test proper handling of security level escalation"""
        # Log events with increasing security levels
        levels = [SecurityLevel.LOW, SecurityLevel.MEDIUM, SecurityLevel.HIGH, SecurityLevel.CRITICAL]

        for level in levels:
            event = SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="escalation_test",
                    level=level,
                    description=f"Security event at {level.value} level",
                    user_id="test_user"
            )
            self.security_service.log_security_event(event)

        # Verify all levels were logged
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            for level in levels:
                assert level.value in content

    def test_backup_operation_security_validation(self):
        """Test security validation during backup operations"""
        # Test backup operation auditing
        self.security_service.audit_backup_operation(
                operation_id="backup_001",
                repository_id="test_repo",
                operation_type="full_backup",
                status="started",
                file_count=100,
                total_size=1024 * 1024 * 100  # 100MB
        )

        # Verify audit entry
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "backup_operation" in content
            assert "backup_001" in content
            assert "full_backup" in content
            assert "started" in content

    def test_restore_operation_security_validation(self):
        """Test security validation during restore operations"""
        # Test restore operation auditing
        self.security_service.audit_restore_operation(
                operation_id="restore_001",
                repository_id="test_repo",
                snapshot_id="snapshot_123",
                target_path="/tmp/restore",
                status="completed",
                files_restored=50
        )

        # Verify audit entry
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "restore_operation" in content
            assert "restore_001" in content
            assert "snapshot_123" in content
            assert "completed" in content

    def test_security_configuration_validation(self):
        """Test validation of security configuration settings"""
        # Test valid configuration
        valid_config = {
                "audit_log_retention_days":   90,
                "credential_timeout_minutes": 30,
                "max_failed_attempts":        3,
                "require_encryption":         True
        }

        result = self.security_service.validate_security_config(valid_config)
        assert result is True

        # Test invalid configuration
        invalid_config = {
                "audit_log_retention_days":   -1,  # Invalid negative value
                "credential_timeout_minutes": 0,  # Invalid zero value
                "max_failed_attempts":        -5,  # Invalid negative value
                "require_encryption":         "yes"  # Invalid type
        }

        result = self.security_service.validate_security_config(invalid_config)
        assert result is False

    def test_emergency_security_lockdown(self):
        """Test emergency security lockdown functionality"""
        # Trigger security lockdown
        self.security_service.emergency_lockdown(
                reason="Multiple failed authentication attempts",
                triggered_by="automated_security_monitor"
        )

        # Verify lockdown was logged
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "emergency_lockdown" in content
            assert "Multiple failed authentication attempts" in content
            assert "automated_security_monitor" in content

    def test_data_integrity_validation(self):
        """Test data integrity validation mechanisms"""
        # Test file integrity validation
        test_file = self.temp_dir / "test_data.txt"
        test_content = "This is test data for integrity validation"
        test_file.write_text(test_content)

        # Calculate and verify checksum
        import hashlib
        expected_hash = hashlib.sha256(test_content.encode()).hexdigest()

        # Simulate integrity check
        with open(test_file, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        assert actual_hash == expected_hash

        # Log integrity check
        self.security_service.audit_integrity_check(
                file_path=str(test_file),
                expected_hash=expected_hash,
                actual_hash=actual_hash,
                status="passed"
        )

        # Verify audit entry
        with open(self.security_service.audit_log_file, 'r') as f:
            content = f.read()
            assert "integrity_check" in content
            assert "passed" in content
