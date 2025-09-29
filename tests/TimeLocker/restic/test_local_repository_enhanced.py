"""
Enhanced tests for LocalResticRepository implementation

Tests the new methods for repository initialization, configuration management,
error handling, and credential integration.
"""

import pytest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.restic.errors import RepositoryError
from TimeLocker.security import CredentialManager


class TestLocalResticRepositoryEnhanced:
    """Test cases for enhanced LocalResticRepository functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.credential_path = self.temp_dir / "credentials"
        self.repo_password = "test_repo_password_123"
        self.master_password = "test_master_password_456"

        # Create credential manager
        self.credential_manager = CredentialManager(config_dir=self.credential_path)

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_success(self, mock_verify):
        """Test successful repository initialization"""
        mock_verify.return_value = "0.18.0"

        # Create repository
        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock the initialize method to return success
        with patch.object(repo, 'initialize', return_value=True):
            result = repo.initialize_repository(self.repo_password)

        assert result is True
        assert self.repo_path.exists()
        assert self.repo_path.is_dir()

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_with_credential_storage(self, mock_verify):
        """Test repository initialization with credential storage"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Create repository with credential manager
        repo = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Mock the initialize method and store_password
        with patch.object(repo, 'initialize', return_value=True), \
                patch.object(repo, 'store_password', return_value=True) as mock_store:
            result = repo.initialize_repository(self.repo_password)

        assert result is True
        mock_store.assert_called_once_with(self.repo_password)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_already_initialized(self, mock_verify):
        """Test initialization when repository is already initialized"""
        mock_verify.return_value = "0.18.0"

        # Create repository directory and config file
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        repo = LocalResticRepository(location=str(self.repo_path))

        result = repo.initialize_repository(self.repo_password)

        assert result is True  # Should return True for already initialized repo

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_directory_creation_fails(self, mock_verify):
        """Test initialization when directory creation fails"""
        mock_verify.return_value = "0.18.0"

        # Use a path that cannot be created (e.g., under a file)
        invalid_parent = self.temp_dir / "file_not_dir"
        invalid_parent.touch()  # Create as file
        invalid_repo_path = invalid_parent / "repo"

        repo = LocalResticRepository(location=str(invalid_repo_path))

        result = repo.initialize_repository(self.repo_password)

        assert result is False

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_is_repository_initialized(self, mock_verify):
        """Test repository initialization status checking"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Initially not initialized
        assert repo.is_repository_initialized() is False

        # Create directory and config file
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        # Now should be initialized
        assert repo.is_repository_initialized() is True

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_repository_info_basic(self, mock_verify):
        """Test getting basic repository information"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        info = repo.get_repository_info()

        assert info["location"] == str(self.repo_path)
        assert info["type"] == "local"
        assert info["repository_id"] == repo.repository_id()
        assert info["initialized"] is False
        assert info["directory_exists"] is False
        assert info["writable"] is False
        assert info["size_bytes"] == 0
        assert info["config"] == {}

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_repository_info_with_directory(self, mock_verify):
        """Test getting repository information with existing directory"""
        mock_verify.return_value = "0.18.0"

        # Create repository directory with some files
        self.repo_path.mkdir(parents=True)
        test_file = self.repo_path / "test.txt"
        test_file.write_text("test content")

        repo = LocalResticRepository(location=str(self.repo_path))

        info = repo.get_repository_info()

        assert info["directory_exists"] is True
        assert info["writable"] is True
        assert info["size_bytes"] > 0

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_repository_info_with_config(self, mock_verify):
        """Test getting repository information with config file"""
        mock_verify.return_value = "0.18.0"

        # Create repository directory with config
        self.repo_path.mkdir(parents=True)
        config_data = {"version": 2, "id": "test-repo-id"}
        config_file = self.repo_path / "config"
        config_file.write_text(json.dumps(config_data))

        repo = LocalResticRepository(location=str(self.repo_path))

        info = repo.get_repository_info()

        assert info["initialized"] is True
        assert info["config"] == config_data

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_validate_repository_health_healthy(self, mock_verify):
        """Test repository health validation for healthy repository"""
        mock_verify.return_value = "0.18.0"

        # Create healthy repository
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        repo = LocalResticRepository(
                location=str(self.repo_path),
                password=self.repo_password
        )

        # Mock the check method to return success
        with patch.object(repo, 'check', return_value=True):
            health = repo.validate_repository_health()

        assert health["healthy"] is True
        assert len(health["issues"]) == 0
        assert health["checks"]["directory_exists"] is True
        assert health["checks"]["directory_writable"] is True
        assert health["checks"]["repository_initialized"] is True
        assert health["checks"]["password_available"] is True
        assert health["checks"]["restic_accessible"] is True

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_validate_repository_health_unhealthy(self, mock_verify):
        """Test repository health validation for unhealthy repository"""
        mock_verify.return_value = "0.18.0"

        # Repository with no directory and no password
        repo = LocalResticRepository(location=str(self.repo_path))

        health = repo.validate_repository_health()

        assert health["healthy"] is False
        assert len(health["issues"]) > 0
        assert "Repository directory does not exist" in health["issues"]
        assert "No repository password available" in health["issues"]

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_setup_repository_with_credentials_success(self, mock_verify):
        """Test complete repository setup with credentials"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock necessary methods
        with patch.object(repo, 'initialize', return_value=True), \
                patch.object(repo, 'check', return_value=True):
            result = repo.setup_repository_with_credentials(
                    self.repo_password,
                    self.credential_manager
            )

        assert result is True
        assert repo._credential_manager == self.credential_manager

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_setup_repository_with_credentials_initialization_fails(self, mock_verify):
        """Test repository setup when initialization fails"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock initialize to fail
        with patch.object(repo, 'initialize_repository', return_value=False):
            result = repo.setup_repository_with_credentials(self.repo_password)

        assert result is False

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_common_repository_issues(self, mock_verify):
        """Test getting common repository issues and solutions"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        issues = repo.get_common_repository_issues()

        assert isinstance(issues, dict)
        assert len(issues) > 0
        assert "Permission denied" in issues
        assert "Repository not initialized" in issues
        assert "Password not available" in issues

        # Check that all values are strings (solutions)
        for issue, solution in issues.items():
            assert isinstance(issue, str)
            assert isinstance(solution, str)
            assert len(solution) > 0

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_password_restoration(self, mock_verify):
        """Test that original password is restored after temporary password use"""
        mock_verify.return_value = "0.18.0"

        original_password = "original_password"
        temp_password = "temp_password"

        repo = LocalResticRepository(
                location=str(self.repo_path),
                password=original_password
        )

        # Mock initialize to succeed
        with patch.object(repo, 'initialize', return_value=True):
            repo.initialize_repository(temp_password)

        # Original password should be restored
        assert repo._explicit_password == original_password
        assert repo.password() == original_password

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_validate_repository_health_with_check_failure(self, mock_verify):
        """Test health validation when repository check fails"""
        mock_verify.return_value = "0.18.0"

        # Create initialized repository
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        repo = LocalResticRepository(
                location=str(self.repo_path),
                password=self.repo_password
        )

        # Mock check to fail
        with patch.object(repo, 'check', return_value=False):
            health = repo.validate_repository_health()

        assert health["healthy"] is False
        assert health["checks"]["restic_accessible"] is False
        assert any("Repository check failed" in issue for issue in health["issues"])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_validate_repository_health_with_exception(self, mock_verify):
        """Test health validation when check raises exception"""
        mock_verify.return_value = "0.18.0"

        # Create initialized repository
        self.repo_path.mkdir(parents=True)
        (self.repo_path / "config").touch()

        repo = LocalResticRepository(
                location=str(self.repo_path),
                password=self.repo_password
        )

        # Mock check to raise exception
        with patch.object(repo, 'check', side_effect=Exception("Test error")):
            health = repo.validate_repository_health()

        assert health["healthy"] is False
        assert any("Repository accessibility check failed" in issue for issue in health["issues"])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_setup_repository_health_check_fails(self, mock_verify):
        """Test repository setup when health check fails"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock initialize to succeed but health check to fail
        with patch.object(repo, 'initialize_repository', return_value=True), \
                patch.object(repo, 'validate_repository_health',
                             return_value={"healthy": False, "issues": ["Test issue"]}):
            result = repo.setup_repository_with_credentials(self.repo_password)

        assert result is False

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_repository_info_with_permission_error(self, mock_verify):
        """Test repository info gathering with permission errors"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock os.walk to raise permission error (this is where the size calculation happens)
        with patch('os.walk', side_effect=PermissionError("Access denied")):
            info = repo.get_repository_info()

        # Should handle error gracefully
        assert info["location"] == str(self.repo_path)
        assert info["type"] == "local"
        assert info["size_bytes"] == 0  # Should default to 0 on error

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_is_repository_initialized_with_exception(self, mock_verify):
        """Test initialization check with exception handling"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock os.path.exists to raise exception
        with patch('os.path.exists', side_effect=OSError("Test error")):
            result = repo.is_repository_initialized()

        assert result is False

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_get_repository_info_config_parsing_error(self, mock_verify):
        """Test repository info with invalid config file"""
        mock_verify.return_value = "0.18.0"

        # Create repository with invalid config
        self.repo_path.mkdir(parents=True)
        config_file = self.repo_path / "config"
        config_file.write_text("invalid json content")

        repo = LocalResticRepository(location=str(self.repo_path))

        info = repo.get_repository_info()

        assert info["initialized"] is True
        assert "raw" in info["config"]
        assert info["config"]["raw"] == "invalid json content"

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_validate_repository_health_password_exception(self, mock_verify):
        """Test health validation when password access raises exception"""
        mock_verify.return_value = "0.18.0"

        # Create directory
        self.repo_path.mkdir(parents=True)

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock password method to raise exception
        with patch.object(repo, 'password', side_effect=Exception("Password error")):
            health = repo.validate_repository_health()

        assert health["healthy"] is False
        assert health["checks"]["password_available"] is False
        assert any("Error accessing password" in issue for issue in health["issues"])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.unit
    def test_initialize_repository_exception_handling(self, mock_verify):
        """Test repository initialization with exception handling"""
        mock_verify.return_value = "0.18.0"

        repo = LocalResticRepository(location=str(self.repo_path))

        # Mock create_repository_directory to raise exception
        with patch.object(repo, 'create_repository_directory', side_effect=Exception("Test error")):
            result = repo.initialize_repository(self.repo_password)

        assert result is False
