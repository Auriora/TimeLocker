"""
Tests for Repository Error Handling and Recovery

This module tests error handling and recovery scenarios for repository management
including network failures, credential errors, and configuration issues.

UPDATED: 2025-11-11 - Rewritten to use actual public API instead of non-existent private methods.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ConnectivityStatus, IntegrityStatus, RepositoryCreationOptions
)
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.validation_service import ValidationService
from TimeLocker.services.repository_credential_manager import RepositoryCredentialManager
from TimeLocker.interfaces.repository_management_models import (
    RepositoryError, RepositoryValidationError, BackendError
)
from TimeLocker.interfaces.exceptions import CredentialError


class TestNetworkFailureScenarios:
    """Test network failure scenarios and timeout handling"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service"""
        return ValidationService()
    
    @pytest.fixture
    def repository_config(self):
        """Create network repository configuration"""
        return RepositoryConfig(
            name="network-repo",
            uri="s3://test-bucket/path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
    
    @pytest.mark.asyncio
    async def test_network_timeout_during_validation(self, validation_service, repository_config):
        """Test handling of network timeout during repository validation"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock network timeout
        with patch.object(validation_service, '_test_repository_connectivity', 
                         side_effect=asyncio.TimeoutError("Connection timeout")):
            result = await validation_service.validate_connectivity(repo)
            
            # Should handle timeout gracefully
            assert result.success is False
            assert result.status == ConnectivityStatus.TIMEOUT
            assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_network_connection_refused(self, validation_service, repository_config):
        """Test handling of connection refused errors"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock connection refused
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=ConnectionRefusedError("Connection refused")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            assert result.status == ConnectivityStatus.UNREACHABLE
            assert "refused" in result.error_message.lower() or "unreachable" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_network_dns_resolution_failure(self, validation_service, repository_config):
        """Test handling of DNS resolution failures"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock DNS failure
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=OSError("Name or service not known")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            assert result.status == ConnectivityStatus.UNREACHABLE
    
    @pytest.mark.asyncio
    async def test_network_ssl_certificate_error(self, validation_service, repository_config):
        """Test handling of SSL certificate errors"""
        repo = Repository(config=repository_config, status=RepositoryStatus.ACTIVE)
        
        # Mock SSL certificate error
        import ssl
        with patch.object(validation_service, '_test_repository_connectivity',
                         side_effect=ssl.SSLError("Certificate verification failed")):
            result = await validation_service.validate_connectivity(repo)
            
            assert result.success is False
            # Should provide helpful recommendations
            assert len(result.recommendations) > 0


class TestCredentialErrorRecovery:
    """Test credential error handling and recovery"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def credential_manager(self, temp_dir):
        """Create credential manager for testing"""
        from TimeLocker.security import SecurityService, CredentialManager
        
        cred_mgr = CredentialManager(config_dir=temp_dir)
        assert cred_mgr.unlock("test-master-password") is True
        security_service = Mock(spec=SecurityService)
        security_service.credential_manager = cred_mgr
        security_service.log_security_event = Mock()
        
        return RepositoryCredentialManager(security_service)
    
    @pytest.mark.asyncio
    async def test_credential_not_found_returns_none(self, credential_manager):
        """Test that missing credentials return None gracefully"""
        # Try to retrieve non-existent credentials
        credentials = await credential_manager.retrieve_credentials("nonexistent-repo")
        
        # Should return None, not raise exception
        assert credentials is None
    
    @pytest.mark.asyncio
    async def test_credential_storage_and_retrieval(self, credential_manager):
        """Test basic credential storage and retrieval"""
        repo_id = "test-repo"
        test_credentials = {'password': 'test-password', 'backend_type': 's3'}
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, test_credentials)
        assert result is True
        
        # Retrieve credentials
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved is not None
        assert retrieved['password'] == 'test-password'


class TestRepositoryManagerErrorRecovery:
    """Test repository manager error recovery mechanisms"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def repository_manager(self, temp_dir):
        """Create repository manager with temp config directory"""
        from TimeLocker.config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager(config_dir=temp_dir)
        manager = RepositoryManager(config_manager=config_manager)
        return manager
    
    @pytest.mark.asyncio
    async def test_repository_creation_with_invalid_config(self, repository_manager):
        """Test error handling when creating repository with invalid configuration"""
        # Create invalid repository config (unsupported URI scheme)
        invalid_config = RepositoryConfig(
            name="test-repo",
            uri="invalid://repo-path",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        # Should raise validation error
        with pytest.raises(RepositoryValidationError):
            await repository_manager.create_repository(invalid_config)
    
    @pytest.mark.asyncio
    async def test_repository_name_validation(self, repository_manager):
        """Test repository name validation"""
        # Test invalid names
        invalid_names = ["", "test repo", "test@repo", "test/repo", "a" * 100]
        
        for invalid_name in invalid_names:
            result = repository_manager.validate_repository_name(invalid_name)
            assert result.is_valid is False
            assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_duplicate_repository_name_detection(self, repository_manager):
        """Test detection of duplicate repository names"""
        # Create first repository
        config1 = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test1",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repo1 = await repository_manager.create_repository(config1)
        assert repo1 is not None
        
        # Try to create second repository with same name
        config2 = RepositoryConfig(
            name="test-repo",  # Same name
            uri="file:///tmp/test2",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        # Should raise error about duplicate name
        with pytest.raises(Exception):  # Could be RepositoryAlreadyExistsError or similar
            await repository_manager.create_repository(config2)


class TestBatchOperationErrorHandling:
    """Test error handling in batch operations"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager for testing"""
        return RepositoryManager()
    
    @pytest.fixture
    def sample_repositories(self):
        """Create sample repositories for batch testing"""
        repos = []
        for i in range(3):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file:///tmp/repo{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repos.append(repo)
        return repos
    
    @pytest.mark.asyncio
    async def test_batch_validate_handles_individual_failures(self, repository_manager, sample_repositories):
        """Test that batch validation continues even if individual validations fail"""
        # Add repositories to manager
        for repo in sample_repositories:
            repository_manager._repositories[repo.config.name] = repo
        
        # Mock validation to fail for one repository
        original_validate = repository_manager.validate_repository
        
        async def mock_validate(repo):
            if repo.config.name == "repo-1":
                raise Exception("Validation failed for repo-1")
            return await original_validate(repo)
        
        with patch.object(repository_manager, 'validate_repository', side_effect=mock_validate):
            # Batch validate should handle the failure gracefully
            results = await repository_manager.batch_validate_repositories()
            
            # Should have results for all repositories
            assert len(results) == 3
            
            # Failed repository should have error in result
            assert "repo-1" in results
            assert results["repo-1"].success is False


class TestConfigurationPersistence:
    """Test configuration persistence and recovery"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def repository_manager(self, temp_dir):
        """Create repository manager with temp config directory"""
        from TimeLocker.config.configuration_manager import ConfigurationManager
        
        config_manager = ConfigurationManager(config_dir=temp_dir)
        manager = RepositoryManager(config_manager=config_manager)
        return manager
    
    @pytest.mark.asyncio
    async def test_configuration_persists_across_restarts(self, repository_manager, temp_dir):
        """Test that configuration persists across manager restarts"""
        # Create repository
        config = RepositoryConfig(
            name="persist-repo",
            uri="file:///tmp/persist",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repo = await repository_manager.create_repository(config)
        assert repo is not None
        
        # Save configuration
        repository_manager._save_repositories()
        
        # Create new manager instance (simulating restart)
        from TimeLocker.config.configuration_manager import ConfigurationManager
        new_config_manager = ConfigurationManager(config_dir=temp_dir)
        new_manager = RepositoryManager(config_manager=new_config_manager)
        new_manager._load_repositories()
        
        # Should have loaded the repository
        assert "persist-repo" in new_manager._repositories
    
    @pytest.mark.asyncio
    async def test_configuration_backup_created(self, repository_manager):
        """Test that configuration backup is created before risky operations"""
        # Create repository
        config = RepositoryConfig(
            name="backup-test-repo",
            uri="file:///tmp/backup-test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repo = await repository_manager.create_repository(config)
        
        # Perform risky operation (update)
        backup_id = await repository_manager._backup_configuration("backup-test-repo")
        
        # Should have created backup
        assert backup_id is not None
        assert len(backup_id) > 0
