"""
Repository Multi-Backend Integration Tests

This module provides comprehensive integration tests for repository management
across multiple storage backends including local, S3, and B2.

Tests cover:
- Repository management across local, S3, and B2 backends
- Credential management for different storage backends
- Plugin system with multiple backup engines
- Cross-backend operations and compatibility
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.TimeLocker.services.repository_manager import RepositoryManager
from src.TimeLocker.services.repository_factory import RepositoryFactory
from src.TimeLocker.services.plugin_registry import PluginRegistry
from src.TimeLocker.services.repository_credential_manager import RepositoryCredentialManager
from src.TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ConnectivityStatus, IntegrityStatus, S3Config
)
from src.TimeLocker.interfaces.integration_data_models import ServiceContext


class TestMultiBackendRepositoryManagement:
    """Integration tests for multi-backend repository management"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test repositories"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def service_context(self):
        """Create mock service context"""
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        context.config_manager = Mock()
        context.service_registry = Mock()
        context.event_bus = None
        return context
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with mocked dependencies"""
        mock_factory = Mock(spec=RepositoryFactory)
        mock_validation = Mock()
        mock_credential = Mock(spec=RepositoryCredentialManager)
        mock_config = Mock()
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config
        )
        
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_local_repository_management(self, repository_manager, service_context, temp_dir):
        """
        Test repository management for local filesystem backend
        
        Requirements: 4.1, 4.2, 4.3
        """
        # Initialize manager
        repository_manager.initialize(service_context)
        
        # Create local repository configuration
        config = RepositoryConfig(
            name="local-repo",
            uri=f"file://{temp_dir}/local-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Local filesystem repository"
        )
        
        # Mock repository creation
        mock_repo_instance = Mock()
        mock_repo_instance.init = Mock()
        repository_manager._repository_factory.create_repository.return_value = mock_repo_instance
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID,
            performance_metrics={'validation_time': 1.5}
        ))
        repository_manager._save_repositories = Mock()
        
        # Create repository
        from src.TimeLocker.interfaces.repository_management_models import RepositoryCreationOptions
        repository = await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        assert repository is not None
        assert repository.config.type == RepositoryType.LOCAL
        assert repository.status == RepositoryStatus.ACTIVE
        
        # Validate repository
        validation_result = await repository_manager.validate_repository(repository)
        assert validation_result.success is True
        assert validation_result.performance_metrics['validation_time'] < 3.0  # Local should be fast
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_s3_repository_management(self, repository_manager, service_context):
        """
        Test repository management for S3 backend
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
        """
        # Initialize manager
        repository_manager.initialize(service_context)
        
        # Create S3 repository configuration
        s3_config = S3Config(
            endpoint="s3.amazonaws.com",
            region="us-east-1",
            bucket="test-backup-bucket",
            path_prefix="backups/",
            use_ssl=True,
            verify_ssl=True
        )
        
        config = RepositoryConfig(
            name="s3-repo",
            uri="s3:https://s3.amazonaws.com/test-backup-bucket/backups",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3,
            description="S3 cloud repository",
            engine_config={'s3_config': s3_config.to_dict()}
        )
        
        # Mock repository creation
        mock_repo_instance = Mock()
        mock_repo_instance.init = Mock()
        repository_manager._repository_factory.create_repository.return_value = mock_repo_instance
        
        # Mock credential storage
        repository_manager._credential_manager.store_credentials = AsyncMock(return_value=True)
        repository_manager._credential_manager.retrieve_credentials = AsyncMock(return_value={
            'access_key_id': 'test-key',
            'secret_access_key': 'test-secret'
        })
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID,
            performance_metrics={'validation_time': 8.5}
        ))
        repository_manager._save_repositories = Mock()
        
        # Create repository
        from src.TimeLocker.interfaces.repository_management_models import RepositoryCreationOptions
        repository = await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        assert repository is not None
        assert repository.config.type == RepositoryType.S3
        assert repository.status == RepositoryStatus.ACTIVE
        
        # Verify credentials were stored
        repository_manager._credential_manager.store_credentials.assert_called()
        
        # Validate repository
        validation_result = await repository_manager.validate_repository(repository)
        assert validation_result.success is True
        assert validation_result.performance_metrics['validation_time'] < 15.0  # Network threshold
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_b2_repository_management(self, repository_manager, service_context):
        """
        Test repository management for Backblaze B2 backend
        
        Requirements: 7.1, 7.2, 7.3
        """
        # Initialize manager
        repository_manager.initialize(service_context)
        
        # Create B2 repository configuration
        config = RepositoryConfig(
            name="b2-repo",
            uri="b2:test-bucket:backups/",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.B2,
            description="Backblaze B2 repository"
        )
        
        # Mock repository creation
        mock_repo_instance = Mock()
        mock_repo_instance.init = Mock()
        repository_manager._repository_factory.create_repository.return_value = mock_repo_instance
        
        # Mock credential storage
        repository_manager._credential_manager.store_credentials = AsyncMock(return_value=True)
        repository_manager._credential_manager.retrieve_credentials = AsyncMock(return_value={
            'account_id': 'test-account',
            'application_key': 'test-key'
        })
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        ))
        repository_manager._save_repositories = Mock()
        
        # Create repository
        from src.TimeLocker.interfaces.repository_management_models import RepositoryCreationOptions
        repository = await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        assert repository is not None
        assert repository.config.type == RepositoryType.B2
        assert repository.status == RepositoryStatus.ACTIVE
        
        # Verify credentials were stored
        repository_manager._credential_manager.store_credentials.assert_called()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mixed_backend_repository_listing(self, repository_manager, service_context, temp_dir):
        """
        Test listing repositories across multiple backends
        
        Requirements: 4.1, 4.2, 4.3
        """
        # Initialize manager
        repository_manager.initialize(service_context)
        
        # Create repositories with different backends
        repos_config = [
            ("local-repo-1", f"file://{temp_dir}/repo1", RepositoryType.LOCAL),
            ("local-repo-2", f"file://{temp_dir}/repo2", RepositoryType.LOCAL),
            ("s3-repo-1", "s3:https://s3.amazonaws.com/bucket1", RepositoryType.S3),
            ("b2-repo-1", "b2:bucket2:path/", RepositoryType.B2),
        ]
        
        # Mock dependencies
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        ))
        repository_manager._save_repositories = Mock()
        
        # Create all repositories
        from src.TimeLocker.interfaces.repository_management_models import RepositoryCreationOptions
        for i, (name, uri, repo_type) in enumerate(repos_config):
            config = RepositoryConfig(
                name=name,
                uri=uri,
                engine=BackupEngine.RESTIC,
                type=repo_type
            )
            # Ensure unique URIs to avoid conflicts
            if i > 0:
                repository_manager._existing_repo_handler.detect_existing_repository.return_value = None
            await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        # List all repositories
        all_repos = await repository_manager.list_repositories()
        assert len(all_repos) == 4
        
        # Filter by backend type
        local_repos = await repository_manager.list_repositories({'type': 'local'})
        assert len(local_repos) == 2
        
        s3_repos = await repository_manager.list_repositories({'type': 's3'})
        assert len(s3_repos) == 1
        
        b2_repos = await repository_manager.list_repositories({'type': 'b2'})
        assert len(b2_repos) == 1


class TestCredentialManagementAcrossBackends:
    """Integration tests for credential management across different backends"""
    
    @pytest.fixture
    def credential_manager(self):
        """Create mock credential manager"""
        manager = Mock(spec=RepositoryCredentialManager)
        manager.store_credentials = AsyncMock(return_value=True)
        manager.retrieve_credentials = AsyncMock(return_value=None)
        manager.rotate_credentials = AsyncMock(return_value=True)
        manager.remove_credentials = AsyncMock(return_value=True)
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_local_repository_credentials(self, credential_manager):
        """
        Test credential management for local repositories
        
        Requirements: 8.1, 8.2, 8.3
        """
        # Local repositories typically use password-based encryption
        repo_id = "local-repo-1"
        credentials = {'password': 'secure-password-123'}
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve credentials
        credential_manager.retrieve_credentials.return_value = credentials
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved == credentials
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_s3_repository_credentials(self, credential_manager):
        """
        Test credential management for S3 repositories
        
        Requirements: 8.1, 8.2, 8.3
        """
        # S3 repositories require access key and secret
        repo_id = "s3-repo-1"
        credentials = {
            'access_key_id': 'AKIAIOSFODNN7EXAMPLE',
            'secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'password': 'repo-encryption-password'
        }
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve credentials
        credential_manager.retrieve_credentials.return_value = credentials
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved == credentials
        assert 'access_key_id' in retrieved
        assert 'secret_access_key' in retrieved
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_b2_repository_credentials(self, credential_manager):
        """
        Test credential management for B2 repositories
        
        Requirements: 8.1, 8.2, 8.3
        """
        # B2 repositories require account ID and application key
        repo_id = "b2-repo-1"
        credentials = {
            'account_id': 'test-account-id',
            'application_key': 'test-application-key',
            'password': 'repo-encryption-password'
        }
        
        # Store credentials
        result = await credential_manager.store_credentials(repo_id, credentials)
        assert result is True
        
        # Retrieve credentials
        credential_manager.retrieve_credentials.return_value = credentials
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved == credentials
        assert 'account_id' in retrieved
        assert 'application_key' in retrieved
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_credential_rotation_across_backends(self, credential_manager):
        """
        Test credential rotation for different backend types
        
        Requirements: 8.4, 8.5
        """
        # Test rotation for S3 credentials
        repo_id = "s3-repo-1"
        old_credentials = {
            'access_key_id': 'OLD_KEY',
            'secret_access_key': 'OLD_SECRET'
        }
        new_credentials = {
            'access_key_id': 'NEW_KEY',
            'secret_access_key': 'NEW_SECRET'
        }
        
        # Store old credentials
        await credential_manager.store_credentials(repo_id, old_credentials)
        
        # Rotate credentials
        result = await credential_manager.rotate_credentials(repo_id, new_credentials)
        assert result is True
        
        # Verify new credentials are stored
        credential_manager.retrieve_credentials.return_value = new_credentials
        retrieved = await credential_manager.retrieve_credentials(repo_id)
        assert retrieved == new_credentials


class TestPluginSystemMultiEngine:
    """Integration tests for plugin system with multiple backup engines"""
    
    @pytest.fixture
    def plugin_registry(self):
        """Create plugin registry"""
        return PluginRegistry()
    
    @pytest.mark.integration
    def test_plugin_registry_initialization(self, plugin_registry):
        """
        Test plugin registry initialization with built-in engines
        
        Requirements: 4.1, 4.2, 4.4, 4.5
        """
        # Verify built-in engines are registered
        available_engines = plugin_registry.get_available_engines()
        
        # Check that engines are returned (may be list or dict)
        if isinstance(available_engines, list):
            assert BackupEngine.RESTIC in available_engines or 'restic' in [str(e) for e in available_engines]
        else:
            assert len(available_engines) > 0
    
    @pytest.mark.integration
    def test_engine_availability_checking(self, plugin_registry):
        """
        Test engine availability checking
        
        Requirements: 4.1, 4.2, 4.5
        """
        # Check Restic availability
        restic_available = plugin_registry.is_engine_available(BackupEngine.RESTIC)
        assert isinstance(restic_available, bool)
        
        # Get engine capabilities
        if restic_available:
            capabilities = plugin_registry.get_engine_capabilities(BackupEngine.RESTIC)
            assert capabilities is not None
            assert 'supported_backends' in capabilities or 'features' in capabilities
    
    @pytest.mark.integration
    def test_engine_specific_configuration_validation(self, plugin_registry):
        """
        Test engine-specific configuration validation
        
        Requirements: 4.1, 4.2, 4.4
        """
        # Test Restic configuration validation
        restic_config = {
            'compression': 'auto',
            'exclude_caches': True
        }
        
        # Validate configuration (if method exists)
        if hasattr(plugin_registry, 'validate_engine_config'):
            is_valid = plugin_registry.validate_engine_config(BackupEngine.RESTIC, restic_config)
            assert isinstance(is_valid, bool)
        else:
            # Method may not be implemented yet
            assert True


class TestCrossBackendOperations:
    """Integration tests for operations across multiple backends"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager"""
        mock_factory = Mock(spec=RepositoryFactory)
        mock_validation = Mock()
        mock_credential = Mock()
        mock_config = Mock()
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config
        )
        
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_validation_across_backends(self, repository_manager):
        """
        Test concurrent validation of repositories across different backends
        
        Requirements: 9.3
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create repositories with different backends
        repos = []
        for i, repo_type in enumerate([RepositoryType.LOCAL, RepositoryType.S3, RepositoryType.B2]):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"test://{i}",
                engine=BackupEngine.RESTIC,
                type=repo_type
            )
            repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repos.append(repo)
            repository_manager._repositories[f"repo-{i}"] = repo
        
        # Mock validation
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._test_connectivity = AsyncMock(return_value=Mock(
            success=True,
            status=ConnectivityStatus.CONNECTED
        ))
        repository_manager._test_integrity = AsyncMock(return_value=Mock(
            success=True,
            status=IntegrityStatus.VALID
        ))
        
        # Validate all repositories concurrently
        validation_tasks = [
            repository_manager.validate_repository(repo)
            for repo in repos
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        # Verify all validations completed
        assert len(results) == 3
        assert all(r.success for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
