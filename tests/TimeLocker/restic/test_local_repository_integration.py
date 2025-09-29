"""
Integration tests for LocalResticRepository with credential management
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import Mock, patch

from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.restic.errors import RepositoryError
from TimeLocker.security import CredentialManager


class TestLocalResticRepositoryIntegration:
    """Integration tests for LocalResticRepository"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.credential_dir = self.temp_dir / "credentials"
        self.credential_manager = CredentialManager(config_dir=self.credential_dir)
        self.master_password = "test_master_123"
        self.repo_password = "repo_password_456"

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_creation_with_credential_manager(self, mock_verify):
        """Test creating a repository with credential manager integration"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Create repository with credential manager
        repo = LocalResticRepository(
                location=str(self.repo_path),
                password=self.repo_password,
                credential_manager=self.credential_manager
        )

        # Verify repository properties
        assert repo.location() == str(self.repo_path)
        assert repo.password() == self.repo_password
        assert repo.repository_id() is not None
        assert len(repo.repository_id()) == 16  # SHA256 hash truncated to 16 chars

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_password_storage_and_retrieval(self, mock_verify):
        """Test storing and retrieving passwords via credential manager"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Create repository
        repo = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Store password
        result = repo.store_password(self.repo_password)
        assert result is True

        # Verify password is retrievable
        assert repo.password() == self.repo_password

        # Create new repository instance (simulating restart)
        repo2 = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Password should be retrieved from credential manager
        assert repo2.password() == self.repo_password

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_password_priority_order(self, mock_verify):
        """Test password priority: explicit > credential manager > environment"""
        mock_verify.return_value = "0.18.0"

        # Set environment variable
        os.environ["RESTIC_PASSWORD"] = "env_password"

        try:
            # Unlock credential manager and store password
            self.credential_manager.unlock(self.master_password)

            # Create repository with explicit password
            repo = LocalResticRepository(
                    location=str(self.repo_path),
                    password="explicit_password",
                    credential_manager=self.credential_manager
            )

            # Store different password in credential manager
            repo.store_password("stored_password")

            # Explicit password should take priority
            assert repo.password() == "explicit_password"

            # Create repository without explicit password
            repo2 = LocalResticRepository(
                    location=str(self.repo_path),
                    credential_manager=self.credential_manager
            )

            # Credential manager password should take priority over environment
            assert repo2.password() == "stored_password"

            # Create repository without credential manager
            repo3 = LocalResticRepository(location=str(self.repo_path))

            # Environment variable should be used
            assert repo3.password() == "env_password"

        finally:
            # Clean up environment
            if "RESTIC_PASSWORD" in os.environ:
                del os.environ["RESTIC_PASSWORD"]

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_validation_new_directory(self, mock_verify):
        """Test validation when repository directory doesn't exist"""
        mock_verify.return_value = "0.18.0"

        # Ensure parent directory exists
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)

        # Repository directory doesn't exist yet
        assert not self.repo_path.exists()

        # Should not raise error - directory will be created during init
        repo = LocalResticRepository(location=str(self.repo_path))

        # Create the directory
        result = repo.create_repository_directory()
        assert result is True
        assert self.repo_path.exists()
        assert self.repo_path.is_dir()

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_validation_existing_directory(self, mock_verify):
        """Test validation when repository directory already exists"""
        mock_verify.return_value = "0.18.0"

        # Create repository directory
        self.repo_path.mkdir(parents=True)

        # Should not raise error
        repo = LocalResticRepository(location=str(self.repo_path))

        # Directory creation should be idempotent
        result = repo.create_repository_directory()
        assert result is True

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_validation_existing_restic_repo(self, mock_verify):
        """Test validation when directory contains existing restic repository"""
        mock_verify.return_value = "0.18.0"

        # Create repository directory with config file (simulating existing restic repo)
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        # Should not raise error and should detect existing repository
        repo = LocalResticRepository(location=str(self.repo_path))
        assert repo.location() == str(self.repo_path)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_validation_invalid_parent(self, mock_verify):
        """Test validation when parent directory doesn't exist"""
        mock_verify.return_value = "0.18.0"

        # Use path with non-existent parent
        invalid_path = self.temp_dir / "nonexistent" / "repo"

        # Should raise RepositoryError
        with pytest.raises(RepositoryError, match="Parent directory does not exist"):
            LocalResticRepository(location=str(invalid_path))

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_validation_file_instead_of_directory(self, mock_verify):
        """Test validation when path points to a file instead of directory"""
        mock_verify.return_value = "0.18.0"

        # Create a file at the repository path
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        self.repo_path.touch()

        # Should raise RepositoryError
        with pytest.raises(RepositoryError, match="Path exists but is not a directory"):
            LocalResticRepository(location=str(self.repo_path))

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_repository_id_consistency(self, mock_verify):
        """Test that repository ID is consistent for the same location"""
        mock_verify.return_value = "0.18.0"

        # Create two repository instances with same location
        repo1 = LocalResticRepository(location=str(self.repo_path))
        repo2 = LocalResticRepository(location=str(self.repo_path))

        # Repository IDs should be identical
        assert repo1.repository_id() == repo2.repository_id()

        # Create repository with different location
        other_path = self.temp_dir / "other_repo"
        repo3 = LocalResticRepository(location=str(other_path))

        # Repository ID should be different
        assert repo1.repository_id() != repo3.repository_id()

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_credential_manager_locked_behavior(self, mock_verify):
        """Test behavior when credential manager is locked"""
        mock_verify.return_value = "0.18.0"

        # Don't unlock credential manager
        repo = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Storing password should fail gracefully
        result = repo.store_password(self.repo_password)
        assert result is False

        # Password retrieval should fall back to environment/explicit
        assert repo.password() is None  # No fallback available
