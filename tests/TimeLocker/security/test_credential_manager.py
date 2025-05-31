"""
Tests for credential management functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from TimeLocker.security import CredentialManager, CredentialManagerError


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

    def test_initialization(self):
        """Test credential manager initialization"""
        assert self.credential_manager.config_dir == self.temp_dir
        assert self.credential_manager.is_locked()
        assert self.temp_dir.exists()

    def test_unlock_with_new_password(self):
        """Test unlocking with a new master password"""
        result = self.credential_manager.unlock(self.master_password)
        assert result is True
        assert not self.credential_manager.is_locked()

    def test_unlock_with_wrong_password(self):
        """Test unlocking with wrong password after setting one"""
        # First, set up credentials with correct password
        self.credential_manager.unlock(self.master_password)
        self.credential_manager.store_repository_password("test_repo", "test_pass")
        self.credential_manager.lock()

        # Try to unlock with wrong password
        with pytest.raises(CredentialManagerError):
            self.credential_manager.unlock("wrong_password")

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

    def test_get_nonexistent_credentials(self):
        """Test retrieving non-existent credentials"""
        self.credential_manager.unlock(self.master_password)

        # Non-existent repository password
        password = self.credential_manager.get_repository_password("nonexistent")
        assert password is None

        # Non-existent backend credentials
        credentials = self.credential_manager.get_backend_credentials("nonexistent")
        assert credentials == {}

    def test_empty_credentials_handling(self):
        """Test handling of empty credential dictionaries"""
        self.credential_manager.unlock(self.master_password)

        # Store empty backend credentials
        self.credential_manager.store_backend_credentials("empty_backend", {})

        # Retrieve empty credentials
        credentials = self.credential_manager.get_backend_credentials("empty_backend")
        assert credentials == {}
