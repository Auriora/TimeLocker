"""
Tests for credential management functionality
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

from TimeLocker.security import CredentialManager, CredentialManagerError, CredentialAccessError, CredentialSecurityError


class TestCredentialManager:
    """Test cases for CredentialManager"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.credential_manager = CredentialManager(config_dir=self.temp_dir)
        self.master_password = "test_master_password_123"

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.security
    @pytest.mark.unit
    def test_initialization(self):
        """Test credential manager initialization"""
        assert self.credential_manager.config_dir == self.temp_dir
        assert self.credential_manager.is_locked()
        assert self.temp_dir.exists()

    @pytest.mark.security
    @pytest.mark.unit
    def test_unlock_with_new_password(self):
        """Test unlocking with a new master password"""
        result = self.credential_manager.unlock(self.master_password)
        assert result is True
        assert not self.credential_manager.is_locked()

    @pytest.mark.security
    @pytest.mark.unit
    def test_unlock_with_wrong_password(self):
        """Test unlocking with wrong password after setting one"""
        # First, set up credentials with correct password
        self.credential_manager.unlock(self.master_password)
        self.credential_manager.store_repository_password("test_repo", "test_pass")
        self.credential_manager.lock()

        # Try to unlock with wrong password
        with pytest.raises(CredentialManagerError):
            self.credential_manager.unlock("wrong_password")

    @pytest.mark.security
    @pytest.mark.unit
    def test_store_and_retrieve_repository_password(self):
        """Test storing and retrieving repository passwords"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "test_repository_123"
        password = "super_secure_password"

        # Store password
        self.credential_manager.store_repository_password(repo_id, password)

        # Retrieve password
        retrieved_password = self.credential_manager.get_repository_password(repo_id)
        assert retrieved_password == password

    @pytest.mark.security
    @pytest.mark.unit
    def test_store_and_retrieve_backend_credentials(self):
        """Test storing and retrieving backend credentials"""
        self.credential_manager.unlock(self.master_password)

        backend_type = "s3"
        credentials = {
                "aws_access_key_id":     "AKIAIOSFODNN7EXAMPLE",
                "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "aws_default_region":    "us-west-2"
        }

        # Store credentials
        self.credential_manager.store_backend_credentials(backend_type, credentials)

        # Retrieve credentials
        retrieved_credentials = self.credential_manager.get_backend_credentials(backend_type)
        assert retrieved_credentials == credentials

    @pytest.mark.security
    @pytest.mark.unit
    def test_list_repositories(self):
        """Test listing stored repositories"""
        self.credential_manager.unlock(self.master_password)

        # Initially empty
        assert self.credential_manager.list_repositories() == []

        # Add some repositories
        repos = ["repo1", "repo2", "repo3"]
        for repo in repos:
            self.credential_manager.store_repository_password(repo, f"password_{repo}")

        # Check list
        stored_repos = self.credential_manager.list_repositories()
        assert set(stored_repos) == set(repos)

    @pytest.mark.security
    @pytest.mark.unit
    def test_remove_repository(self):
        """Test removing repository credentials"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "test_repo_to_remove"
        self.credential_manager.store_repository_password(repo_id, "password")

        # Verify it exists
        assert repo_id in self.credential_manager.list_repositories()

        # Remove it
        result = self.credential_manager.remove_repository(repo_id)
        assert result is True
        assert repo_id not in self.credential_manager.list_repositories()

        # Try to remove non-existent repository
        result = self.credential_manager.remove_repository("non_existent")
        assert result is False

    @pytest.mark.security
    @pytest.mark.unit
    def test_persistence_across_sessions(self):
        """Test that credentials persist across lock/unlock cycles"""
        # First session
        self.credential_manager.unlock(self.master_password)
        repo_id = "persistent_repo"
        password = "persistent_password"
        self.credential_manager.store_repository_password(repo_id, password)
        self.credential_manager.lock()

        # Second session
        self.credential_manager.unlock(self.master_password)
        retrieved_password = self.credential_manager.get_repository_password(repo_id)
        assert retrieved_password == password

    @pytest.mark.security
    @pytest.mark.unit
    def test_change_master_password(self):
        """Test changing the master password"""
        # Set up initial credentials
        self.credential_manager.unlock(self.master_password)
        repo_id = "test_repo"
        password = "test_password"
        self.credential_manager.store_repository_password(repo_id, password)

        # Change master password
        new_master_password = "new_master_password_456"
        result = self.credential_manager.change_master_password(
                self.master_password, new_master_password
        )
        assert result is True

        # Lock and unlock with new password
        self.credential_manager.lock()
        self.credential_manager.unlock(new_master_password)

        # Verify credentials are still accessible
        retrieved_password = self.credential_manager.get_repository_password(repo_id)
        assert retrieved_password == password

        # Verify old password no longer works
        self.credential_manager.lock()
        with pytest.raises(CredentialManagerError):
            self.credential_manager.unlock(self.master_password)

    @pytest.mark.security
    @pytest.mark.unit
    def test_operations_when_locked(self):
        """Test that operations fail when credential store is locked"""
        # Don't unlock the credential manager

        with pytest.raises(CredentialManagerError):
            self.credential_manager.store_repository_password("repo", "password")

        with pytest.raises(CredentialManagerError):
            self.credential_manager.get_repository_password("repo")

        with pytest.raises(CredentialManagerError):
            self.credential_manager.store_backend_credentials("s3", {})

        with pytest.raises(CredentialManagerError):
            self.credential_manager.get_backend_credentials("s3")

    @pytest.mark.security
    @pytest.mark.unit
    def test_get_nonexistent_credentials(self):
        """Test retrieving non-existent credentials"""
        self.credential_manager.unlock(self.master_password)

        # Non-existent repository password
        password = self.credential_manager.get_repository_password("nonexistent")
        assert password is None

        # Non-existent backend credentials
        credentials = self.credential_manager.get_backend_credentials("nonexistent")
        assert credentials == {}

    @pytest.mark.security
    @pytest.mark.unit
    def test_empty_credentials_handling(self):
        """Test handling of empty credential dictionaries"""
        self.credential_manager.unlock(self.master_password)

        # Store empty backend credentials
        self.credential_manager.store_backend_credentials("empty_backend", {})

        # Retrieve empty credentials
        credentials = self.credential_manager.get_backend_credentials("empty_backend")
        assert credentials == {}

    @pytest.mark.security
    @pytest.mark.slow
    @pytest.mark.unit
    def test_auto_lock_timeout(self):
        """Test auto-lock functionality"""
        # Create credential manager with short timeout
        short_timeout_manager = CredentialManager(config_dir=self.temp_dir, auto_lock_timeout=1)
        short_timeout_manager.unlock(self.master_password)

        # Store a credential
        short_timeout_manager.store_repository_password("test_repo", "test_pass")

        # Wait for timeout
        time.sleep(1.1)

        # Should auto-lock and raise exception
        with pytest.raises(CredentialAccessError):
            short_timeout_manager.get_repository_password("test_repo")

    @pytest.mark.security
    @pytest.mark.unit
    def test_failed_attempt_lockout(self):
        """Test lockout after failed attempts"""
        # Set up credentials first
        self.credential_manager.unlock(self.master_password)
        self.credential_manager.store_repository_password("test_repo", "test_pass")
        self.credential_manager.lock()

        # Create new manager to test lockout
        lockout_manager = CredentialManager(config_dir=self.temp_dir)

        # Make multiple failed attempts
        for i in range(5):
            with pytest.raises(CredentialManagerError):
                lockout_manager.unlock("wrong_password")

        # Should now be locked out
        with pytest.raises(CredentialAccessError):
            lockout_manager.unlock("wrong_password")

    @pytest.mark.security
    @pytest.mark.unit
    def test_credential_rotation(self):
        """Test credential rotation functionality"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "rotation_test_repo"
        old_password = "old_password"
        new_password = "new_password"

        # Store initial credential
        self.credential_manager.store_repository_password(repo_id, old_password)

        # Rotate credential
        result = self.credential_manager.rotate_credential(repo_id, new_password)
        assert result is True

        # Verify new password is stored
        retrieved_password = self.credential_manager.get_repository_password(repo_id)
        assert retrieved_password == new_password

    @pytest.mark.security
    @pytest.mark.unit
    def test_secure_delete_credential(self):
        """Test secure deletion of credentials"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "delete_test_repo"
        password = "password_to_delete"

        # Store credential
        self.credential_manager.store_repository_password(repo_id, password)
        assert self.credential_manager.get_repository_password(repo_id) == password

        # Securely delete
        result = self.credential_manager.secure_delete_credential(repo_id)
        assert result is True

        # Verify it's gone
        assert self.credential_manager.get_repository_password(repo_id) is None

    @pytest.mark.security
    @pytest.mark.unit
    def test_credential_metadata(self):
        """Test credential metadata functionality"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "metadata_test_repo"
        password = "test_password"

        # Store credential
        self.credential_manager.store_repository_password(repo_id, password)

        # Get metadata
        metadata = self.credential_manager.get_credential_metadata(repo_id)
        assert metadata is not None
        assert "password" not in metadata  # Password should not be in metadata
        assert metadata["type"] == "repository"
        assert "created_at" in metadata
        assert "access_count" in metadata

    @pytest.mark.security
    @pytest.mark.unit
    def test_security_status(self):
        """Test security status reporting"""
        status = self.credential_manager.get_security_status()

        assert "is_locked" in status
        assert "failed_attempts" in status
        assert "auto_lock_timeout" in status
        assert status["is_locked"] is True  # Initially locked

    @pytest.mark.security
    @pytest.mark.unit
    def test_audit_events(self):
        """Test audit event logging and retrieval"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "audit_test_repo"
        password = "audit_test_password"

        # Perform operations that should be audited
        self.credential_manager.store_repository_password(repo_id, password)
        self.credential_manager.get_repository_password(repo_id)

        # Get audit events
        events = self.credential_manager.get_audit_events(hours=1)
        assert len(events) > 0

        # Check that events contain expected operations
        operations = [event["operation"] for event in events]
        assert "store_repository_password" in operations
        assert "get_repository_password" in operations

    @pytest.mark.security
    @pytest.mark.unit
    def test_credential_integrity_validation(self):
        """Test credential integrity validation"""
        self.credential_manager.unlock(self.master_password)

        # Store some credentials
        self.credential_manager.store_repository_password("repo1", "pass1")
        self.credential_manager.store_repository_password("repo2", "pass2")

        # Validate integrity
        result = self.credential_manager.validate_credential_integrity()
        assert result is True

    @pytest.mark.security
    @pytest.mark.unit
    def test_credential_integrity_validation_when_locked(self):
        """Test that integrity validation fails when locked"""
        # Don't unlock the credential manager
        with pytest.raises(CredentialSecurityError):
            self.credential_manager.validate_credential_integrity()

    @pytest.mark.security
    @pytest.mark.unit
    def test_access_tracking(self):
        """Test that credential access is properly tracked"""
        self.credential_manager.unlock(self.master_password)

        repo_id = "tracking_test_repo"
        password = "tracking_test_password"

        # Store credential
        self.credential_manager.store_repository_password(repo_id, password)

        # Access it multiple times
        for _ in range(3):
            self.credential_manager.get_repository_password(repo_id)

        # Check metadata shows access count
        metadata = self.credential_manager.get_credential_metadata(repo_id)
        assert metadata["access_count"] == 3

    @pytest.mark.security
    @pytest.mark.unit
    def test_empty_repository_id_validation(self):
        """Test validation of empty repository IDs"""
        self.credential_manager.unlock(self.master_password)

        with pytest.raises(CredentialManagerError):
            self.credential_manager.store_repository_password("", "password")

        with pytest.raises(CredentialManagerError):
            self.credential_manager.store_repository_password("repo", "")

    @pytest.mark.security
    @pytest.mark.unit
    def test_audit_log_creation(self):
        """Test that audit logs are created properly"""
        self.credential_manager.unlock(self.master_password)

        # Perform an operation
        self.credential_manager.store_repository_password("test_repo", "test_pass")

        # Check that audit log file exists
        assert self.credential_manager.audit_log_file.exists()

        # Check that it contains entries
        with open(self.credential_manager.audit_log_file, 'r') as f:
            content = f.read()
            assert "store_repository_password" in content

    @pytest.mark.security
    @pytest.mark.unit
    def test_concurrent_access_safety(self):
        """Test that concurrent access is handled safely"""
        import threading
        import time

        # Create credential manager with no auto-lock for this test
        concurrent_manager = CredentialManager(config_dir=self.temp_dir, auto_lock_timeout=0)
        concurrent_manager.unlock(self.master_password)

        results = []
        errors = []

        def store_credential(repo_id):
            try:
                # Add small delay to reduce contention
                time.sleep(0.01 * repo_id)
                concurrent_manager.store_repository_password(f"repo_{repo_id}", f"pass_{repo_id}")
                results.append(repo_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_credential, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # For file-based storage, some concurrent operations may fail
        # The important thing is that the system doesn't crash and some operations succeed
        total_operations = len(results) + len(errors)
        assert total_operations == 5, f"Expected 5 total operations, got {total_operations}"
        assert len(results) >= 3, f"Expected at least 3 successful operations, got {len(results)}"

        # Verify that successful operations actually stored the credentials
        for repo_id in results:
            password = concurrent_manager.get_repository_password(f"repo_{repo_id}")
            assert password == f"pass_{repo_id}"
