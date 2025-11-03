"""
Tests for Repository Manager Core functionality

This module tests the core repository management functionality including
CRUD operations, state management, and existing repository handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ExistingRepositoryInfo, RepositoryCreationOptions,
    ConnectivityStatus, IntegrityStatus
)
from src.TimeLocker.services.repository_manager import RepositoryManager
from src.TimeLocker.services.repository_state_manager import RepositoryStateManager
from src.TimeLocker.services.existing_repository_handler import ExistingRepositoryHandler
from src.TimeLocker.interfaces.integration_data_models import ServiceContext


class TestRepositoryManagerCore:
    """Test Repository Manager core functionality"""
    
    @pytest.fixture
    def mock_service_context(self):
        """Create mock service context"""
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        return context
    
    @pytest.fixture
    def repository_config(self):
        """Create test repository configuration"""
        return RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Test repository"
        )
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with mocked dependencies"""
        # Mock dependencies
        mock_factory = Mock()
        mock_validation = Mock()
        mock_credential = Mock()
        mock_config = Mock()
        mock_state = Mock(spec=RepositoryStateManager)
        mock_existing = Mock(spec=ExistingRepositoryHandler)
        
        # Setup async methods
        mock_state.transition_state = AsyncMock()
        mock_existing.detect_existing_repository = AsyncMock(return_value=None)
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config,
            state_manager=mock_state,
            existing_repo_handler=mock_existing
        )
        
        return manager
    
    @pytest.mark.asyncio
    async def test_repository_manager_initialization(self, repository_manager, mock_service_context):
        """Test repository manager initialization"""
        # Test initialization
        result = repository_manager.initialize(mock_service_context)
        assert result is True
        assert repository_manager._initialized is True
        
        # Test health check
        assert repository_manager.health_check() is True
        
        # Test capabilities
        capabilities = repository_manager.get_capabilities()
        assert 'repository_create' in capabilities
        assert 'repository_validate' in capabilities
        assert 'existing_repository_detection' in capabilities
    
    @pytest.mark.asyncio
    async def test_create_repository_new(self, repository_manager, repository_config, mock_service_context):
        """Test creating a new repository"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Mock no existing repository
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = None
        
        # Mock repository factory
        mock_repo_instance = Mock()
        mock_repo_instance.init = Mock()
        repository_manager._repository_factory.create_repository.return_value = mock_repo_instance
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        ))
        
        # Mock save
        repository_manager._save_repositories = Mock()
        
        # Create repository
        options = RepositoryCreationOptions()
        repository = await repository_manager.create_repository(repository_config, options)
        
        # Verify repository was created
        assert repository is not None
        assert repository.config.name == "test-repo"
        assert repository.status == RepositoryStatus.ACTIVE
        
        # Verify repository was stored
        assert "test-repo" in repository_manager._repositories
    
    @pytest.mark.asyncio
    async def test_detect_existing_repository(self, repository_manager):
        """Test existing repository detection"""
        # Mock existing repository info
        existing_info = ExistingRepositoryInfo(
            uri="file:///tmp/existing-repo",
            engine_type=BackupEngine.RESTIC,
            requires_credentials=True,
            metadata={'snapshot_count': 5}
        )
        
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_info
        
        # Test detection
        result = await repository_manager.detect_existing_repository("file:///tmp/existing-repo")
        
        assert result is not None
        assert result.uri == "file:///tmp/existing-repo"
        assert result.engine_type == BackupEngine.RESTIC
        assert result.metadata['snapshot_count'] == 5
    
    @pytest.mark.asyncio
    async def test_repository_validation(self, repository_manager, repository_config, mock_service_context):
        """Test repository validation"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Create test repository
        repository = Repository(
            config=repository_config,
            status=RepositoryStatus.INACTIVE
        )
        
        # Mock repository factory and validation methods
        mock_repo_instance = Mock()
        repository_manager._repository_factory.create_repository.return_value = mock_repo_instance
        
        repository_manager._test_connectivity = AsyncMock(return_value=Mock(
            success=True,
            status=ConnectivityStatus.CONNECTED,
            error_message=None
        ))
        
        repository_manager._test_integrity = AsyncMock(return_value=Mock(
            success=True,
            status=IntegrityStatus.VALID
        ))
        
        # Test validation
        result = await repository_manager.validate_repository(repository)
        
        assert result.success is True
        assert result.connectivity_status == ConnectivityStatus.CONNECTED
        assert result.integrity_status == IntegrityStatus.VALID
        assert repository.last_validated is not None
    
    @pytest.mark.asyncio
    async def test_repository_crud_operations(self, repository_manager, repository_config, mock_service_context):
        """Test basic CRUD operations"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Create repository manually for testing
        repository = Repository(
            config=repository_config,
            status=RepositoryStatus.ACTIVE
        )
        repository_manager._repositories["test-repo"] = repository
        
        # Test get repository
        retrieved = await repository_manager.get_repository("test-repo")
        assert retrieved.config.name == "test-repo"
        
        # Test list repositories
        repositories = await repository_manager.list_repositories()
        assert len(repositories) == 1
        assert repositories[0].config.name == "test-repo"
        
        # Test list with filters
        filtered = await repository_manager.list_repositories({'status': 'active'})
        assert len(filtered) == 1
        
        # Test update repository
        repository_manager._save_repositories = Mock()
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager._backup_configuration = AsyncMock(return_value="backup-id")
        
        updated = await repository_manager.update_repository("test-repo", {'description': 'Updated description'})
        assert updated.config.description == 'Updated description'
        
        # Test delete repository
        result = await repository_manager.delete_repository("test-repo")
        assert result is True
        assert "test-repo" not in repository_manager._repositories


class TestRepositoryStateManager:
    """Test Repository State Manager functionality"""
    
    @pytest.fixture
    def state_manager(self):
        """Create repository state manager"""
        return RepositoryStateManager()
    
    @pytest.fixture
    def test_repository(self):
        """Create test repository"""
        config = RepositoryConfig(
            name="test-repo",
            uri="file:///tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        return Repository(config=config, status=RepositoryStatus.INACTIVE)
    
    @pytest.mark.asyncio
    async def test_valid_state_transitions(self, state_manager, test_repository):
        """Test valid state transitions"""
        # INACTIVE -> VALIDATING
        result = await state_manager.transition_state(test_repository, RepositoryStatus.VALIDATING)
        assert result is True
        assert test_repository.status == RepositoryStatus.VALIDATING
        
        # VALIDATING -> ACTIVE (with successful validation)
        test_repository.validation_result = ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        )
        
        result = await state_manager.transition_state(test_repository, RepositoryStatus.ACTIVE)
        assert result is True
        assert test_repository.status == RepositoryStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, state_manager, test_repository):
        """Test invalid state transition"""
        from src.TimeLocker.interfaces.repository_management_models import RepositoryStateError
        
        # Try invalid transition (INACTIVE -> ACTIVE without validation)
        with pytest.raises(RepositoryStateError):
            await state_manager.transition_state(test_repository, RepositoryStatus.ACTIVE)
    
    def test_state_history_tracking(self, state_manager, test_repository):
        """Test state history tracking"""
        # Initially no history
        history = state_manager.get_state_history("test-repo")
        assert len(history) == 0
        
        # After transition, history should be recorded
        asyncio.run(state_manager.transition_state(test_repository, RepositoryStatus.VALIDATING))
        
        history = state_manager.get_state_history("test-repo")
        assert len(history) == 1
        assert history[0].from_state == RepositoryStatus.INACTIVE
        assert history[0].to_state == RepositoryStatus.VALIDATING


if __name__ == "__main__":
    pytest.main([__file__])