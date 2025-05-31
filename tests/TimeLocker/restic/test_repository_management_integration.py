"""
Integration tests for complete repository management workflow

Tests the full lifecycle of repository management including:
- Repository creation and initialization
- Credential management integration
- Configuration management
- Error handling and recovery
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from unittest.mock import patch

from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.restic.errors import RepositoryError
from TimeLocker.security import CredentialManager


class TestRepositoryManagementIntegration:
    """Integration tests for repository management workflow"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "backup_repo"
        self.credential_path = self.temp_dir / "credentials"
        self.repo_password = "secure_backup_password_123"
        self.master_password = "master_password_456"

        # Create credential manager
        self.credential_manager = CredentialManager(config_dir=self.credential_path)

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_complete_repository_setup_workflow(self, mock_verify):
        """Test complete repository setup from start to finish"""
        mock_verify.return_value = "0.18.0"

        # Step 1: Unlock credential manager
        unlock_result = self.credential_manager.unlock(self.master_password)
        assert unlock_result is True

        # Step 2: Create repository instance
        repository = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Step 3: Verify initial state
        assert not repository.is_repository_initialized()
        assert not self.repo_path.exists()

        # Step 4: Setup repository with credentials
        with patch.object(repository, 'initialize', return_value=True), \
                patch.object(repository, 'check', return_value=True):
            setup_result = repository.setup_repository_with_credentials(self.repo_password)

        assert setup_result is True

        # Step 5: Verify repository state
        assert self.repo_path.exists()

        # Create config file to simulate successful initialization
        (self.repo_path / "config").touch()
        assert repository.is_repository_initialized()

        # Step 6: Verify credential storage
        stored_password = self.credential_manager.get_repository_password(repository.repository_id())
        assert stored_password == self.repo_password

        # Step 7: Verify repository info
        info = repository.get_repository_info()
        assert info["initialized"] is True
        assert info["directory_exists"] is True
        assert info["writable"] is True

        # Step 8: Verify health check
        with patch.object(repository, 'check', return_value=True):
            health = repository.validate_repository_health()

        assert health["healthy"] is True
        assert len(health["issues"]) == 0

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_repository_recovery_workflow(self, mock_verify):
        """Test repository recovery from various error conditions"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Create repository
        repository = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        # Scenario 1: Directory doesn't exist
        health = repository.validate_repository_health()
        assert not health["healthy"]
        assert "Repository directory does not exist" in health["issues"]

        # Recovery: Create directory
        created = repository.create_repository_directory()
        assert created is True
        assert self.repo_path.exists()

        # Scenario 2: Directory exists but not initialized
        health = repository.validate_repository_health()
        assert "Repository is not initialized" in health["warnings"]

        # Recovery: Initialize repository
        with patch.object(repository, 'initialize', return_value=True):
            init_result = repository.initialize_repository(self.repo_password)

        assert init_result is True

        # Create config file to simulate successful initialization
        (self.repo_path / "config").touch()

        # Scenario 3: Repository initialized but password not stored
        # Simulate password not being available
        original_password = repository._explicit_password
        repository._explicit_password = None

        # Also clear the credential manager to ensure no password is available
        if repository._credential_manager:
            repository._credential_manager.remove_repository(repository.repository_id())

        health = repository.validate_repository_health()
        assert not health["healthy"]
        assert "No repository password available" in health["issues"]

        # Recovery: Store password
        repository._explicit_password = original_password
        stored = repository.store_password(self.repo_password)
        assert stored is True

        # Final verification: Repository should be healthy
        with patch.object(repository, 'check', return_value=True):
            health = repository.validate_repository_health()

        assert health["healthy"] is True

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_multiple_repositories_management(self, mock_verify):
        """Test managing multiple repositories with credential manager"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Create multiple repositories
        repo1_path = self.temp_dir / "repo1"
        repo2_path = self.temp_dir / "repo2"

        repo1 = LocalResticRepository(
                location=str(repo1_path),
                credential_manager=self.credential_manager
        )

        repo2 = LocalResticRepository(
                location=str(repo2_path),
                credential_manager=self.credential_manager
        )

        # Setup both repositories
        password1 = "password1_123"
        password2 = "password2_456"

        with patch.object(repo1, 'initialize', return_value=True), \
                patch.object(repo1, 'check', return_value=True), \
                patch.object(repo2, 'initialize', return_value=True), \
                patch.object(repo2, 'check', return_value=True):
            setup1 = repo1.setup_repository_with_credentials(password1)
            setup2 = repo2.setup_repository_with_credentials(password2)

        assert setup1 is True
        assert setup2 is True

        # Create config files to simulate successful initialization
        (repo1_path / "config").touch()
        (repo2_path / "config").touch()

        # Verify both repositories are tracked
        stored_repos = self.credential_manager.list_repositories()
        assert len(stored_repos) == 2
        assert repo1.repository_id() in stored_repos
        assert repo2.repository_id() in stored_repos

        # Verify passwords are stored correctly
        assert self.credential_manager.get_repository_password(repo1.repository_id()) == password1
        assert self.credential_manager.get_repository_password(repo2.repository_id()) == password2

        # Verify repository info for both
        info1 = repo1.get_repository_info()
        info2 = repo2.get_repository_info()

        assert info1["repository_id"] != info2["repository_id"]
        assert info1["location"] != info2["location"]
        assert info1["initialized"] is True
        assert info2["initialized"] is True

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_repository_password_priority_workflow(self, mock_verify):
        """Test password priority handling in real workflow"""
        mock_verify.return_value = "0.18.0"

        # Unlock credential manager
        self.credential_manager.unlock(self.master_password)

        # Test 1: Explicit password takes priority
        explicit_password = "explicit_password"
        stored_password = "stored_password"
        env_password = "env_password"

        # Store password in credential manager first
        repo = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )
        repo.store_password(stored_password)

        # Set environment variable
        os.environ["RESTIC_PASSWORD"] = env_password

        try:
            # Create new repository with explicit password
            repo_with_explicit = LocalResticRepository(
                    location=str(self.repo_path),
                    password=explicit_password,
                    credential_manager=self.credential_manager
            )

            # Explicit password should take priority
            assert repo_with_explicit.password() == explicit_password

            # Test 2: Credential manager password when no explicit password
            repo_no_explicit = LocalResticRepository(
                    location=str(self.repo_path),
                    credential_manager=self.credential_manager
            )

            # Should get password from credential manager
            assert repo_no_explicit.password() == stored_password

            # Test 3: Environment password when credential manager is locked
            self.credential_manager.lock()

            repo_locked_cm = LocalResticRepository(
                    location=str(self.repo_path),
                    credential_manager=self.credential_manager
            )

            # Should fall back to environment variable
            assert repo_locked_cm.password() == env_password

        finally:
            # Clean up environment
            if "RESTIC_PASSWORD" in os.environ:
                del os.environ["RESTIC_PASSWORD"]

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_repository_error_diagnosis_workflow(self, mock_verify):
        """Test error diagnosis and solution suggestions"""
        mock_verify.return_value = "0.18.0"

        repository = LocalResticRepository(location=str(self.repo_path))

        # Get common issues and solutions
        issues = repository.get_common_repository_issues()

        # Verify we have comprehensive issue coverage
        expected_issues = [
                "Permission denied",
                "Directory not found",
                "Repository not initialized",
                "Password not available",
                "Repository locked",
                "Repository corrupted"
        ]

        for expected_issue in expected_issues:
            assert expected_issue in issues
            assert len(issues[expected_issue]) > 20  # Meaningful solution text

        # Test health validation provides actionable information
        health = repository.validate_repository_health()

        assert not health["healthy"]
        assert len(health["issues"]) > 0

        # Issues should be specific and actionable
        for issue in health["issues"]:
            assert len(issue) > 10  # Not just generic error messages
            assert any(keyword in issue.lower() for keyword in
                       ["directory", "password", "repository", "access"])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    def test_repository_configuration_persistence(self, mock_verify):
        """Test that repository configuration persists across sessions"""
        mock_verify.return_value = "0.18.0"

        # Session 1: Setup repository
        self.credential_manager.unlock(self.master_password)

        repo1 = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=self.credential_manager
        )

        with patch.object(repo1, 'initialize', return_value=True), \
                patch.object(repo1, 'check', return_value=True):
            setup_result = repo1.setup_repository_with_credentials(self.repo_password)

        assert setup_result is True

        repo_id = repo1.repository_id()

        # Create config file to simulate successful initialization
        (self.repo_path / "config").touch()

        # Lock credential manager (simulating session end)
        self.credential_manager.lock()

        # Session 2: Recreate repository and credential manager
        new_credential_manager = CredentialManager(config_dir=self.credential_path)
        new_credential_manager.unlock(self.master_password)

        repo2 = LocalResticRepository(
                location=str(self.repo_path),
                credential_manager=new_credential_manager
        )

        # Verify configuration persisted
        assert repo2.repository_id() == repo_id
        assert repo2.password() == self.repo_password
        assert repo2.is_repository_initialized() is True

        # Verify repository info is consistent
        info = repo2.get_repository_info()
        assert info["initialized"] is True
        assert info["repository_id"] == repo_id
