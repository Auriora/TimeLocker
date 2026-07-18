"""
Tests for Repository Manager Core functionality

This module tests the core repository management functionality including
CRUD operations, state management, and existing repository handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ExistingRepositoryInfo, RepositoryCreationOptions,
    ConnectivityStatus, IntegrityStatus
)
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_state_manager import RepositoryStateManager
from TimeLocker.services.existing_repository_handler import ExistingRepositoryHandler
from TimeLocker.interfaces.integration_data_models import ServiceContext


class TestRepositoryManagerCore:
    """Test Repository Manager core functionality"""
    
    @pytest.fixture
    def mock_service_context(self):
        """Create mock service context"""
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        context.config_manager = Mock()
        context.service_registry = Mock()
        context.event_bus = None
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
        from TimeLocker.interfaces.repository_management_models import RepositoryStateError
        
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


class TestRepositoryManagerExistingRepositoryHandling:
    """Test Repository Manager existing repository detection and handling"""
    
    @pytest.fixture
    def mock_service_context(self):
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
        mock_factory = Mock()
        mock_validation = Mock()
        mock_credential = Mock()
        mock_config = Mock()
        mock_state = Mock(spec=RepositoryStateManager)
        mock_existing = Mock(spec=ExistingRepositoryHandler)
        
        # Setup async methods
        mock_state.transition_state = AsyncMock()
        mock_existing.detect_existing_repository = AsyncMock()
        mock_existing.connect_to_existing_repository = AsyncMock()
        mock_existing.reinitialize_repository = AsyncMock()
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config,
            state_manager=mock_state,
            existing_repo_handler=mock_existing
        )
        
        return manager
    
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
    def existing_repo_info(self):
        """Create existing repository info"""
        return ExistingRepositoryInfo(
            uri="file:///tmp/existing-repo",
            engine_type=BackupEngine.RESTIC,
            requires_credentials=True,
            repository_id="test-repo-id",
            metadata={'snapshot_count': 10},
            last_modified=datetime.utcnow(),
            estimated_size=1024 * 1024 * 100  # 100 MB
        )
    
    @pytest.mark.asyncio
    async def test_create_repository_with_existing_connect(
        self, repository_manager, repository_config, existing_repo_info, mock_service_context
    ):
        """Test creating repository when existing repository found - connect option"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Mock existing repository detection
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_repo_info
        
        # Mock connect to existing
        connected_repo = Repository(
            config=repository_config,
            status=RepositoryStatus.ACTIVE
        )
        repository_manager._existing_repo_handler.connect_to_existing_repository.return_value = connected_repo
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        ))
        repository_manager._save_repositories = Mock()
        
        # Create repository with connect option
        options = RepositoryCreationOptions(connect_if_exists=True)
        repository = await repository_manager.create_repository(repository_config, options)
        
        # Verify connection was attempted
        repository_manager._existing_repo_handler.connect_to_existing_repository.assert_called_once()
        assert repository.status == RepositoryStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_create_repository_with_existing_reinitialize(
        self, repository_manager, repository_config, existing_repo_info, mock_service_context
    ):
        """Test creating repository when existing repository found - reinitialize option"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Mock existing repository detection
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_repo_info
        
        # Mock reinitialize
        reinitialized_repo = Repository(
            config=repository_config,
            status=RepositoryStatus.ACTIVE
        )
        repository_manager._existing_repo_handler.reinitialize_repository.return_value = reinitialized_repo
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager._save_repositories = Mock()
        
        # Create repository with reinitialize option and force confirmation
        options = RepositoryCreationOptions(
            reinitialize_if_exists=True,
            force_confirmation=True
        )
        repository = await repository_manager.create_repository(repository_config, options)
        
        # Verify reinitialize was attempted
        repository_manager._existing_repo_handler.reinitialize_repository.assert_called_once()
        assert repository.status == RepositoryStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_create_repository_existing_without_confirmation_raises_error(
        self, repository_manager, repository_config, existing_repo_info, mock_service_context
    ):
        """Test that reinitialize without confirmation raises error"""
        from TimeLocker.interfaces.repository_management_models import DataLossConfirmationError
        
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Mock existing repository detection
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_repo_info
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        
        # Try to reinitialize without force confirmation
        options = RepositoryCreationOptions(
            reinitialize_if_exists=True,
            require_confirmation_for_reinit=True,
            force_confirmation=False
        )
        
        with pytest.raises(DataLossConfirmationError):
            await repository_manager.create_repository(repository_config, options)
    
    @pytest.mark.asyncio
    async def test_detect_existing_repository_with_metadata(self, repository_manager, existing_repo_info):
        """Test existing repository detection returns metadata"""
        # Mock detection
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_repo_info
        
        # Test detection
        result = await repository_manager.detect_existing_repository("file:///tmp/existing-repo")
        
        assert result is not None
        assert result.uri == "file:///tmp/existing-repo"
        assert result.engine_type == BackupEngine.RESTIC
        assert result.requires_credentials is True
        assert result.metadata['snapshot_count'] == 10
        assert result.estimated_size == 1024 * 1024 * 100
    
    @pytest.mark.asyncio
    async def test_connect_to_existing_repository_with_credentials(
        self, repository_manager, repository_config, existing_repo_info, mock_service_context
    ):
        """Test connecting to existing repository with credentials"""
        # Initialize manager
        repository_manager.initialize(mock_service_context)
        
        # Mock detection
        repository_manager._existing_repo_handler.detect_existing_repository.return_value = existing_repo_info
        
        # Mock connect
        connected_repo = Repository(
            config=repository_config,
            status=RepositoryStatus.ACTIVE
        )
        repository_manager._existing_repo_handler.connect_to_existing_repository.return_value = connected_repo
        
        # Test connection with credentials
        credentials = {'password': 'test-password'}
        result = await repository_manager.connect_to_existing_repository(repository_config, credentials)
        
        assert result is not None
        assert result.status == RepositoryStatus.ACTIVE
        repository_manager._existing_repo_handler.connect_to_existing_repository.assert_called_once()


class TestRepositoryManagerNameValidation:
    """Test Repository Manager name validation and uniqueness checking"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager"""
        return RepositoryManager()
    
    def test_validate_repository_name_valid(self, repository_manager):
        """Test valid repository names"""
        valid_names = [
            "test-repo",
            "my_backup",
            "repo.2024",
            "backup-1",
            "a",
            "test_repo_123"
        ]
        
        for name in valid_names:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is True, f"Name '{name}' should be valid"
            assert len(result.errors) == 0
    
    def test_validate_repository_name_invalid(self, repository_manager):
        """Test invalid repository names"""
        invalid_names = [
            "",  # Empty
            "a" * 65,  # Too long
            "-test",  # Starts with special char
            "test-",  # Ends with special char
            "test--repo",  # Consecutive special chars
            "test..repo",  # Consecutive dots
            "test repo",  # Contains space
            "test@repo",  # Invalid character
        ]
        
        for name in invalid_names:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is False, f"Name '{name}' should be invalid"
            assert len(result.errors) > 0
    
    def test_validate_repository_name_reserved(self, repository_manager):
        """Test reserved repository names"""
        reserved_names = ["default", "all", "none", "null", "system", "config"]
        
        for name in reserved_names:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is False
            assert any("reserved" in error.lower() for error in result.errors)
    
    def test_check_repository_name_uniqueness(self, repository_manager):
        """Test repository name uniqueness checking"""
        # Add a repository
        config = RepositoryConfig(
            name="existing-repo",
            uri="file:///tmp/existing",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["existing-repo"] = repository
        
        # Check uniqueness
        assert repository_manager.check_repository_name_uniqueness("existing-repo") is False
        assert repository_manager.check_repository_name_uniqueness("new-repo") is True


class TestRepositoryManagerDefaultRepository:
    """Test Repository Manager default repository management"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with test repositories"""
        manager = RepositoryManager()
        
        # Add test repositories
        for i in range(3):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file:///tmp/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
            manager._repositories[f"repo-{i}"] = repository
        
        return manager
    
    @pytest.mark.asyncio
    async def test_set_default_repository(self, repository_manager):
        """Test setting default repository"""
        repository_manager._save_repositories = Mock()
        
        # Set default
        result = await repository_manager.set_default_repository("repo-1")
        assert result is True
        
        # Verify default is set
        default_repo = repository_manager.get_default_repository()
        assert default_repo is not None
        assert default_repo.config.name == "repo-1"
        assert default_repo.config.is_default is True
        
        # Verify other repositories are not default
        for name, repo in repository_manager._repositories.items():
            if name != "repo-1":
                assert repo.config.is_default is False
    
    @pytest.mark.asyncio
    async def test_change_default_repository(self, repository_manager):
        """Test changing default repository"""
        repository_manager._save_repositories = Mock()
        
        # Set first default
        await repository_manager.set_default_repository("repo-0")
        assert repository_manager.get_default_repository().config.name == "repo-0"
        
        # Change default
        await repository_manager.set_default_repository("repo-2")
        assert repository_manager.get_default_repository().config.name == "repo-2"
        
        # Verify old default is cleared
        assert repository_manager._repositories["repo-0"].config.is_default is False
    
    @pytest.mark.asyncio
    async def test_clear_default_repository(self, repository_manager):
        """Test clearing default repository"""
        repository_manager._save_repositories = Mock()
        
        # Set default
        await repository_manager.set_default_repository("repo-1")
        assert repository_manager.get_default_repository() is not None
        
        # Clear default
        result = await repository_manager.clear_default_repository()
        assert result is True
        
        # Verify no default
        assert repository_manager.get_default_repository() is None
    
    def test_resolve_repository_name_by_name(self, repository_manager):
        """Test resolving repository by name"""
        result = repository_manager.resolve_repository_name("repo-1")
        assert result == "repo-1"
    
    def test_resolve_repository_name_by_uri(self, repository_manager):
        """Test resolving repository by URI"""
        result = repository_manager.resolve_repository_name("file:///tmp/repo-2")
        assert result == "repo-2"
    
    @pytest.mark.asyncio
    async def test_resolve_repository_name_default(self, repository_manager):
        """Test resolving default repository"""
        repository_manager._save_repositories = Mock()
        
        # Set default
        await repository_manager.set_default_repository("repo-0")
        
        # Resolve default
        result = repository_manager.resolve_repository_name("default")
        assert result == "repo-0"
        
        result = repository_manager.resolve_repository_name("")
        assert result == "repo-0"


class TestRepositoryManagerTypeDetection:
    """Test Repository Manager automatic type detection"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager"""
        return RepositoryManager()
    
    def test_detect_local_repository_type(self, repository_manager):
        """Test detecting local repository types"""
        local_uris = [
            "file:///tmp/backup",
            "/tmp/backup",
            "~/backup",
            "C:\\backup"
        ]
        
        for uri in local_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.LOCAL, f"URI '{uri}' should be detected as LOCAL"
    
    def test_detect_s3_repository_type(self, repository_manager):
        """Test detecting S3 repository types"""
        s3_uris = [
            "s3:https://s3.amazonaws.com/bucket/path",
            "s3:s3.amazonaws.com/bucket/path"
        ]
        
        for uri in s3_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.S3, f"URI '{uri}' should be detected as S3"
    
    def test_detect_b2_repository_type(self, repository_manager):
        """Test detecting B2 repository types"""
        b2_uris = [
            "b2:bucket-name:path/to/repo"
        ]
        
        for uri in b2_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.B2, f"URI '{uri}' should be detected as B2"
    
    def test_detect_sftp_repository_type(self, repository_manager):
        """Test detecting SFTP repository types"""
        sftp_uris = [
            "sftp://user@host/path",
            "sftp://host:22/path"
        ]
        
        for uri in sftp_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.SFTP, f"URI '{uri}' should be detected as SFTP"


class TestRepositoryManagerAuditLogging:
    """Test Repository Manager audit logging functionality"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with mocked state manager"""
        mock_state = Mock(spec=RepositoryStateManager)
        mock_state.transition_state = AsyncMock()
        mock_state.get_state_history = Mock(return_value=[])
        
        manager = RepositoryManager(state_manager=mock_state)
        return manager
    
    @pytest.fixture
    def test_repository(self):
        """Create test repository"""
        config = RepositoryConfig(
            name="audit-test-repo",
            uri="file:///tmp/audit-test",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        return Repository(config=config, status=RepositoryStatus.INACTIVE)
    
    def test_get_state_history(self, repository_manager):
        """Test retrieving state history"""
        # Mock state history
        from TimeLocker.interfaces.repository_management_models import RepositoryStateTransition
        
        transitions = [
            RepositoryStateTransition(
                repository_name="audit-test-repo",
                from_state=RepositoryStatus.INACTIVE,
                to_state=RepositoryStatus.VALIDATING,
                timestamp=datetime.utcnow(),
                correlation_id="test-correlation-id",
                context={}
            )
        ]
        repository_manager._state_manager.get_state_history.return_value = transitions
        
        # Get history
        history = repository_manager.get_state_history("audit-test-repo")
        
        assert len(history) == 1
        assert history[0].repository_name == "audit-test-repo"
        assert history[0].from_state == RepositoryStatus.INACTIVE
        assert history[0].to_state == RepositoryStatus.VALIDATING
    
    def test_get_state_history_with_limit(self, repository_manager):
        """Test retrieving state history with limit"""
        # Mock state history with multiple transitions
        from TimeLocker.interfaces.repository_management_models import RepositoryStateTransition
        
        transitions = [
            RepositoryStateTransition(
                repository_name="audit-test-repo",
                from_state=RepositoryStatus.INACTIVE,
                to_state=RepositoryStatus.VALIDATING,
                timestamp=datetime.utcnow(),
                correlation_id="test-correlation-id-1",
                context={}
            ),
            RepositoryStateTransition(
                repository_name="audit-test-repo",
                from_state=RepositoryStatus.VALIDATING,
                to_state=RepositoryStatus.ACTIVE,
                timestamp=datetime.utcnow(),
                correlation_id="test-correlation-id-2",
                context={}
            )
        ]
        repository_manager._state_manager.get_state_history.return_value = transitions[:1]
        
        # Get history with limit
        history = repository_manager.get_state_history("audit-test-repo", limit=1)
        
        assert len(history) == 1
        repository_manager._state_manager.get_state_history.assert_called_with("audit-test-repo", 1)


class TestRepositoryManagerBatchOperations:
    """Test Repository Manager batch validation operations"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with test repositories"""
        manager = RepositoryManager()
        
        # Add test repositories
        for i in range(5):
            config = RepositoryConfig(
                name=f"batch-repo-{i}",
                uri=f"file:///tmp/batch-repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repository = Repository(config=config, status=RepositoryStatus.INACTIVE)
            manager._repositories[f"batch-repo-{i}"] = repository
        
        return manager
    
    @pytest.mark.asyncio
    async def test_batch_validate_all_repositories(self, repository_manager):
        """Test batch validation of all repositories"""
        # Mock validation
        async def mock_validate(repo):
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        repository_manager.validate_repository = mock_validate
        
        # Batch validate
        results = await repository_manager.batch_validate_repositories()
        
        assert len(results) == 5
        for name, result in results.items():
            assert result.success is True
            assert name.startswith("batch-repo-")
    
    @pytest.mark.asyncio
    async def test_batch_validate_specific_repositories(self, repository_manager):
        """Test batch validation of specific repositories"""
        # Mock validation
        async def mock_validate(repo):
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        repository_manager.validate_repository = mock_validate
        
        # Batch validate specific repositories
        repo_names = ["batch-repo-0", "batch-repo-2", "batch-repo-4"]
        results = await repository_manager.batch_validate_repositories(repo_names)
        
        assert len(results) == 3
        assert "batch-repo-0" in results
        assert "batch-repo-2" in results
        assert "batch-repo-4" in results
    
    @pytest.mark.asyncio
    async def test_batch_validate_with_failures(self, repository_manager):
        """Test batch validation with some failures"""
        # Mock validation with failures
        async def mock_validate(repo):
            if repo.config.name == "batch-repo-2":
                return ValidationResult(
                    success=False,
                    timestamp=datetime.utcnow(),
                    connectivity_status=ConnectivityStatus.DISCONNECTED,
                    integrity_status=IntegrityStatus.UNKNOWN,
                    error_details=["Connection failed"]
                )
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        repository_manager.validate_repository = mock_validate
        
        # Batch validate
        results = await repository_manager.batch_validate_repositories()
        
        assert len(results) == 5
        assert results["batch-repo-2"].success is False
        assert results["batch-repo-0"].success is True


class TestRepositoryManagerStatistics:
    """Test Repository Manager statistics and monitoring"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with test repositories"""
        manager = RepositoryManager()
        
        # Add repositories with different statuses
        statuses = [
            RepositoryStatus.ACTIVE,
            RepositoryStatus.ACTIVE,
            RepositoryStatus.INACTIVE,
            RepositoryStatus.ERROR,
            RepositoryStatus.VALIDATING
        ]
        
        for i, status in enumerate(statuses):
            config = RepositoryConfig(
                name=f"stats-repo-{i}",
                uri=f"file:///tmp/stats-repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repository = Repository(config=config, status=status)
            manager._repositories[f"stats-repo-{i}"] = repository
        
        return manager
    
    def test_get_repository_statistics(self, repository_manager):
        """Test getting repository statistics"""
        stats = repository_manager.get_repository_statistics()
        
        assert 'total_repositories' in stats
        assert stats['total_repositories'] == 5
        
        assert 'status_distribution' in stats
        assert stats['status_distribution']['active'] == 2
        assert stats['status_distribution']['inactive'] == 1
        assert stats['status_distribution']['error'] == 1
        assert stats['status_distribution']['validating'] == 1
        
        assert 'performance_thresholds' in stats
        assert 'state_management' in stats


if __name__ == "__main__":
    pytest.main([__file__])