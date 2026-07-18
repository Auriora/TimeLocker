"""
Tests for Repository Manager Named Repository Management

This module tests the named repository management functionality including
repository aliases, name validation, default repository management, and
metadata storage and retrieval.

Tests Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    RepositoryNotFoundError
)
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.interfaces.integration_data_models import ServiceContext


class TestRepositoryAliasSystem:
    """
    Test repository alias system and name validation.
    
    Requirements: 6.1, 6.4, 6.5
    """
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager for testing"""
        return RepositoryManager()
    
    def test_validate_repository_name_valid_names(self, repository_manager):
        """
        Test validation of valid repository names.
        
        Valid names should:
        - Be between 1 and 64 characters
        - Contain only alphanumeric, hyphens, underscores, and dots
        - Start and end with alphanumeric characters
        
        Requirement: 6.1 - Repository name validation
        """
        valid_names = [
            "test-repo",
            "my_backup",
            "repo.2024",
            "backup-1",
            "a",
            "test_repo_123",
            "MyRepo",
            "repo123",
            "backup.test-2024_v1"
        ]
        
        for name in valid_names:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is True, f"Name '{name}' should be valid but got errors: {result.errors}"
            assert len(result.errors) == 0
    
    def test_validate_repository_name_invalid_names(self, repository_manager):
        """
        Test validation of invalid repository names.
        
        Invalid names include:
        - Empty strings
        - Names over 64 characters
        - Names starting/ending with special characters
        - Names with consecutive special characters
        - Names with invalid characters
        
        Requirement: 6.1 - Repository name validation
        """
        invalid_cases = [
            ("", "empty name"),
            ("a" * 65, "name too long"),
            ("-test", "starts with hyphen"),
            ("test-", "ends with hyphen"),
            ("_test", "starts with underscore"),
            ("test_", "ends with underscore"),
            (".test", "starts with dot"),
            ("test.", "ends with dot"),
            ("test--repo", "consecutive hyphens"),
            ("test..repo", "consecutive dots"),
            ("test__repo", "consecutive underscores"),
            ("test repo", "contains space"),
            ("test@repo", "contains invalid character"),
            ("test#repo", "contains hash"),
            ("test$repo", "contains dollar sign"),
        ]
        
        for name, description in invalid_cases:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is False, f"Name '{name}' ({description}) should be invalid"
            assert len(result.errors) > 0, f"Name '{name}' should have validation errors"
    
    def test_validate_repository_name_reserved_names(self, repository_manager):
        """
        Test that reserved names are rejected.
        
        Reserved names: default, all, none, null, system, config
        
        Requirement: 6.1 - Repository name validation
        """
        reserved_names = ["default", "all", "none", "null", "system", "config"]
        
        for name in reserved_names:
            result = repository_manager.validate_repository_name(name)
            assert result.is_valid is False, f"Reserved name '{name}' should be invalid"
            assert any("reserved" in error.lower() for error in result.errors), \
                f"Reserved name '{name}' should have 'reserved' in error message"
            
            # Test case-insensitive
            result_upper = repository_manager.validate_repository_name(name.upper())
            assert result_upper.is_valid is False, f"Reserved name '{name.upper()}' should be invalid"
    
    def test_check_repository_name_uniqueness(self, repository_manager):
        """
        Test repository name uniqueness checking.
        
        Requirement: 6.1 - Repository name uniqueness
        """
        # Initially, all names should be unique
        assert repository_manager.check_repository_name_uniqueness("new-repo") is True
        
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
        assert repository_manager.check_repository_name_uniqueness("existing-repo") is False, \
            "Existing repository name should not be unique"
        assert repository_manager.check_repository_name_uniqueness("new-repo") is True, \
            "New repository name should be unique"
        assert repository_manager.check_repository_name_uniqueness("another-repo") is True, \
            "Another new repository name should be unique"
    
    def test_get_repository_by_uri(self, repository_manager):
        """
        Test finding repository by URI.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns
        """
        # Add test repositories with different URIs
        test_repos = [
            ("local-repo", "file:///tmp/local"),
            ("s3-repo", "s3:https://s3.amazonaws.com/bucket/path"),
            ("b2-repo", "b2:bucket:path/to/repo"),
        ]
        
        for name, uri in test_repos:
            config = RepositoryConfig(
                name=name,
                uri=uri,
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repository_manager._repositories[name] = repository
        
        # Test finding by URI
        for name, uri in test_repos:
            found_repo = repository_manager.get_repository_by_uri(uri)
            assert found_repo is not None, f"Should find repository with URI '{uri}'"
            assert found_repo.config.name == name, f"Found repository should have name '{name}'"
        
        # Test non-existent URI
        not_found = repository_manager.get_repository_by_uri("file:///tmp/nonexistent")
        assert not_found is None, "Should return None for non-existent URI"
    
    def test_resolve_repository_name_by_name(self, repository_manager):
        """
        Test resolving repository by direct name lookup.
        
        Requirement: 6.1 - Named repository support with user-defined aliases
        """
        # Add test repository
        config = RepositoryConfig(
            name="my-backup",
            uri="file:///tmp/backup",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["my-backup"] = repository
        
        # Test direct name resolution
        result = repository_manager.resolve_repository_name("my-backup")
        assert result == "my-backup", "Should resolve repository by direct name"
        
        # Test non-existent name
        result = repository_manager.resolve_repository_name("nonexistent")
        assert result is None, "Should return None for non-existent repository"
    
    def test_resolve_repository_name_by_uri(self, repository_manager):
        """
        Test resolving repository by URI lookup.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns
        """
        # Add test repository
        config = RepositoryConfig(
            name="s3-backup",
            uri="s3:https://s3.amazonaws.com/my-bucket/backup",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["s3-backup"] = repository
        
        # Test URI resolution
        result = repository_manager.resolve_repository_name("s3:https://s3.amazonaws.com/my-bucket/backup")
        assert result == "s3-backup", "Should resolve repository by URI"
        
        # Test non-existent URI
        result = repository_manager.resolve_repository_name("s3:https://s3.amazonaws.com/other-bucket/backup")
        assert result is None, "Should return None for non-existent URI"


class TestDefaultRepositoryManagement:
    """
    Test default repository selection and management.
    
    Requirements: 6.3
    """
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with test repositories"""
        manager = RepositoryManager()
        manager._save_repositories = Mock()  # Mock save to avoid file I/O
        
        # Add test repositories
        for i in range(3):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file:///tmp/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description=f"Test repository {i}"
            )
            repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
            manager._repositories[f"repo-{i}"] = repository
        
        return manager
    
    @pytest.mark.asyncio
    async def test_set_default_repository(self, repository_manager):
        """
        Test setting a repository as default.
        
        Requirement: 6.3 - Support setting and changing default repositories
        """
        # Initially no default
        default_repo = repository_manager.get_default_repository()
        assert default_repo is None, "Initially should have no default repository"
        
        # Set default
        result = await repository_manager.set_default_repository("repo-1")
        assert result is True, "Setting default repository should succeed"
        
        # Verify default is set
        default_repo = repository_manager.get_default_repository()
        assert default_repo is not None, "Should have a default repository"
        assert default_repo.config.name == "repo-1", "Default should be repo-1"
        assert default_repo.config.is_default is True, "Default flag should be True"
        
        # Verify other repositories are not default
        for name, repo in repository_manager._repositories.items():
            if name != "repo-1":
                assert repo.config.is_default is False, f"Repository {name} should not be default"
        
        # Verify save was called
        repository_manager._save_repositories.assert_called()
    
    @pytest.mark.asyncio
    async def test_change_default_repository(self, repository_manager):
        """
        Test changing the default repository.
        
        Requirement: 6.3 - Support setting and changing default repositories
        """
        # Set first default
        await repository_manager.set_default_repository("repo-0")
        assert repository_manager.get_default_repository().config.name == "repo-0"
        
        # Change default to another repository
        await repository_manager.set_default_repository("repo-2")
        default_repo = repository_manager.get_default_repository()
        assert default_repo.config.name == "repo-2", "Default should be changed to repo-2"
        
        # Verify old default is cleared
        old_default = repository_manager._repositories["repo-0"]
        assert old_default.config.is_default is False, "Old default should be cleared"
        
        # Verify only one default exists
        default_count = sum(1 for repo in repository_manager._repositories.values() if repo.config.is_default)
        assert default_count == 1, "Should have exactly one default repository"
    
    @pytest.mark.asyncio
    async def test_clear_default_repository(self, repository_manager):
        """
        Test clearing the default repository setting.
        
        Requirement: 6.3 - Support setting and changing default repositories
        """
        # Set default
        await repository_manager.set_default_repository("repo-1")
        assert repository_manager.get_default_repository() is not None
        
        # Clear default
        result = await repository_manager.clear_default_repository()
        assert result is True, "Clearing default should succeed"
        
        # Verify no default
        default_repo = repository_manager.get_default_repository()
        assert default_repo is None, "Should have no default repository after clearing"
        
        # Verify all repositories have is_default = False
        for repo in repository_manager._repositories.values():
            assert repo.config.is_default is False, "All repositories should have is_default = False"
        
        # Verify save was called
        repository_manager._save_repositories.assert_called()
    
    @pytest.mark.asyncio
    async def test_set_default_repository_nonexistent(self, repository_manager):
        """
        Test setting a non-existent repository as default raises error.
        
        Requirement: 6.3 - Default repository management
        """
        with pytest.raises(RepositoryNotFoundError):
            await repository_manager.set_default_repository("nonexistent-repo")
    
    def test_resolve_repository_name_default_keyword(self, repository_manager):
        """
        Test resolving repository using 'default' keyword.
        
        Requirement: 6.3 - Default repository for simplified command usage
        """
        # Set default
        asyncio.run(repository_manager.set_default_repository("repo-0"))
        
        # Resolve using 'default' keyword
        result = repository_manager.resolve_repository_name("default")
        assert result == "repo-0", "Should resolve 'default' keyword to default repository"
        
        # Test case-insensitive
        result = repository_manager.resolve_repository_name("DEFAULT")
        assert result == "repo-0", "Should resolve 'DEFAULT' keyword (case-insensitive)"
    
    def test_resolve_repository_name_empty_string(self, repository_manager):
        """
        Test resolving repository using empty string returns default.
        
        Requirement: 6.3 - Default repository for simplified command usage
        """
        # Set default
        asyncio.run(repository_manager.set_default_repository("repo-2"))
        
        # Resolve using empty string
        result = repository_manager.resolve_repository_name("")
        assert result == "repo-2", "Should resolve empty string to default repository"
        
        # Resolve using None
        result = repository_manager.resolve_repository_name(None)
        assert result == "repo-2", "Should resolve None to default repository"
    
    def test_resolve_repository_name_no_default(self, repository_manager):
        """
        Test resolving default when no default is set returns None.
        
        Requirement: 6.3 - Default repository management
        """
        # Ensure no default is set
        asyncio.run(repository_manager.clear_default_repository())
        
        # Try to resolve default
        result = repository_manager.resolve_repository_name("default")
        assert result is None, "Should return None when no default is set"
        
        result = repository_manager.resolve_repository_name("")
        assert result is None, "Should return None for empty string when no default is set"


class TestRepositoryMetadataManagement:
    """
    Test repository metadata storage and retrieval.
    
    Requirements: 6.2, 6.5
    """
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager for testing"""
        manager = RepositoryManager()
        manager._save_repositories = Mock()  # Mock save to avoid file I/O
        return manager
    
    @pytest.fixture
    def repository_with_metadata(self):
        """Create repository with metadata"""
        config = RepositoryConfig(
            name="metadata-repo",
            uri="file:///tmp/metadata-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Repository with metadata",
            metadata={
                "owner": "test-user",
                "environment": "production",
                "backup_frequency": "daily",
                "retention_days": 30
            }
        )
        return Repository(config=config, status=RepositoryStatus.ACTIVE)
    
    def test_repository_description_storage(self, repository_manager, repository_with_metadata):
        """
        Test storing and retrieving repository descriptions.
        
        Requirement: 6.2 - Optional descriptions and metadata
        """
        # Add repository
        repository_manager._repositories["metadata-repo"] = repository_with_metadata
        
        # Retrieve and verify description
        repo = asyncio.run(repository_manager.get_repository("metadata-repo"))
        assert repo.config.description == "Repository with metadata", \
            "Should retrieve repository description"
    
    def test_repository_custom_metadata_storage(self, repository_manager, repository_with_metadata):
        """
        Test storing and retrieving custom metadata.
        
        Requirement: 6.2 - Optional descriptions and metadata
        """
        # Add repository
        repository_manager._repositories["metadata-repo"] = repository_with_metadata
        
        # Retrieve and verify metadata
        repo = asyncio.run(repository_manager.get_repository("metadata-repo"))
        assert repo.config.metadata is not None, "Should have metadata"
        assert repo.config.metadata["owner"] == "test-user", "Should retrieve owner metadata"
        assert repo.config.metadata["environment"] == "production", "Should retrieve environment metadata"
        assert repo.config.metadata["backup_frequency"] == "daily", "Should retrieve backup_frequency metadata"
        assert repo.config.metadata["retention_days"] == 30, "Should retrieve retention_days metadata"
    
    @pytest.mark.asyncio
    async def test_update_repository_description(self, repository_manager, repository_with_metadata):
        """
        Test updating repository description.
        
        Requirement: 6.2 - Metadata persistence in structured format
        """
        # Add repository
        repository_manager._repositories["metadata-repo"] = repository_with_metadata
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager._backup_configuration = AsyncMock(return_value="backup-id")
        
        # Update description
        updated_repo = await repository_manager.update_repository(
            "metadata-repo",
            {"description": "Updated description"}
        )
        
        assert updated_repo.config.description == "Updated description", \
            "Description should be updated"
        assert updated_repo.config.updated_at is not None, "Updated timestamp should be set"
        
        # Verify save was called
        repository_manager._save_repositories.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_repository_metadata(self, repository_manager, repository_with_metadata):
        """
        Test updating repository custom metadata.
        
        Requirement: 6.2 - Metadata persistence in structured format
        """
        # Add repository
        repository_manager._repositories["metadata-repo"] = repository_with_metadata
        
        # Mock validation
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager._backup_configuration = AsyncMock(return_value="backup-id")
        
        # Update metadata
        new_metadata = {
            "owner": "new-user",
            "environment": "staging",
            "backup_frequency": "hourly",
            "retention_days": 60,
            "new_field": "new_value"
        }
        
        updated_repo = await repository_manager.update_repository(
            "metadata-repo",
            {"metadata": new_metadata}
        )
        
        assert updated_repo.config.metadata == new_metadata, "Metadata should be updated"
        assert updated_repo.config.metadata["owner"] == "new-user", "Owner should be updated"
        assert updated_repo.config.metadata["new_field"] == "new_value", "New field should be added"
        
        # Verify save was called
        repository_manager._save_repositories.assert_called()
    
    def test_repository_metadata_in_listing(self, repository_manager):
        """
        Test that metadata is included in repository listings.
        
        Requirement: 6.5 - Persist configuration in structured format and allow listing with status
        """
        # Add repositories with different metadata
        repos_data = [
            ("prod-repo", "Production repository", {"environment": "production"}),
            ("dev-repo", "Development repository", {"environment": "development"}),
            ("test-repo", "Test repository", {"environment": "test"}),
        ]
        
        for name, description, metadata in repos_data:
            config = RepositoryConfig(
                name=name,
                uri=f"file:///tmp/{name}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description=description,
                metadata=metadata
            )
            repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repository_manager._repositories[name] = repository
        
        # List repositories
        repositories = asyncio.run(repository_manager.list_repositories())
        
        assert len(repositories) == 3, "Should list all repositories"
        
        # Verify metadata is present in listing
        for repo in repositories:
            assert repo.config.description is not None, "Description should be present"
            assert repo.config.metadata is not None, "Metadata should be present"
            assert "environment" in repo.config.metadata, "Environment metadata should be present"
    
    def test_repository_empty_metadata(self, repository_manager):
        """
        Test repository with no metadata.
        
        Requirement: 6.2 - Optional descriptions and metadata
        """
        # Create repository without metadata
        config = RepositoryConfig(
            name="no-metadata-repo",
            uri="file:///tmp/no-metadata",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["no-metadata-repo"] = repository
        
        # Retrieve repository
        repo = asyncio.run(repository_manager.get_repository("no-metadata-repo"))
        
        # Verify optional fields
        assert repo.config.description is None or repo.config.description == "", \
            "Description should be None or empty"
        assert repo.config.metadata == {} or repo.config.metadata is None, \
            "Metadata should be empty or None"


class TestRepositoryTypeDetection:
    """
    Test automatic repository type detection from URI patterns.
    
    Requirements: 6.4
    """
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager for testing"""
        return RepositoryManager()
    
    def test_detect_local_repository_type(self, repository_manager):
        """
        Test detecting local repository types from various URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns
        """
        local_uris = [
            ("file:///tmp/backup", "file:// scheme"),
            ("/tmp/backup", "absolute path"),
            ("~/backup", "home directory path"),
            ("C:\\backup", "Windows path"),
            ("/var/backups/repo", "absolute Unix path"),
        ]
        
        for uri, description in local_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.LOCAL, \
                f"URI '{uri}' ({description}) should be detected as LOCAL"
    
    def test_detect_s3_repository_type(self, repository_manager):
        """
        Test detecting S3 repository types from URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns (s3)
        """
        s3_uris = [
            ("s3:https://s3.amazonaws.com/bucket/path", "S3 with https"),
            ("s3:s3.amazonaws.com/bucket/path", "S3 without protocol"),
            ("s3:https://s3.us-west-2.amazonaws.com/my-bucket/backup", "S3 with region"),
        ]
        
        for uri, description in s3_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.S3, \
                f"URI '{uri}' ({description}) should be detected as S3"
    
    def test_detect_b2_repository_type(self, repository_manager):
        """
        Test detecting B2 repository types from URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns (b2)
        """
        b2_uris = [
            ("b2:bucket-name:path/to/repo", "B2 standard format"),
            ("b2:my-bucket:backup/data", "B2 with path"),
        ]
        
        for uri, description in b2_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.B2, \
                f"URI '{uri}' ({description}) should be detected as B2"
    
    def test_detect_sftp_repository_type(self, repository_manager):
        """
        Test detecting SFTP repository types from URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns (sftp)
        """
        sftp_uris = [
            ("sftp://user@host/path", "SFTP with user"),
            ("sftp://host:22/path", "SFTP with port"),
            ("sftp://user@host:2222/backup/repo", "SFTP with user and port"),
        ]
        
        for uri, description in sftp_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.SFTP, \
                f"URI '{uri}' ({description}) should be detected as SFTP"
    
    def test_detect_smb_repository_type(self, repository_manager):
        """
        Test detecting SMB repository types from URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns
        """
        smb_uris = [
            ("smb://server/share/path", "SMB standard format"),
            ("smb://192.168.1.100/backup", "SMB with IP address"),
        ]
        
        for uri, description in smb_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.SMB, \
                f"URI '{uri}' ({description}) should be detected as SMB"
    
    def test_detect_nfs_repository_type(self, repository_manager):
        """
        Test detecting NFS repository types from URI patterns.
        
        Requirement: 6.4 - Automatic repository type detection from URI patterns
        """
        nfs_uris = [
            ("nfs://server/export/path", "NFS standard format"),
            ("nfs://192.168.1.100/backup", "NFS with IP address"),
        ]
        
        for uri, description in nfs_uris:
            repo_type = repository_manager._detect_repository_type(uri)
            assert repo_type == RepositoryType.NFS, \
                f"URI '{uri}' ({description}) should be detected as NFS"
    
    def test_detect_repository_type_empty_uri(self, repository_manager):
        """
        Test detecting repository type for empty URI defaults to LOCAL.
        
        Requirement: 6.4 - Automatic repository type detection
        """
        repo_type = repository_manager._detect_repository_type("")
        assert repo_type == RepositoryType.LOCAL, "Empty URI should default to LOCAL"
        
        repo_type = repository_manager._detect_repository_type(None)
        assert repo_type == RepositoryType.LOCAL, "None URI should default to LOCAL"


class TestNamedRepositoryPersistence:
    """
    Test named repository configuration persistence.
    
    Requirements: 6.5
    """
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with mocked config manager"""
        mock_config_manager = Mock()
        mock_config_manager.get_config = Mock(return_value=Mock(repositories={}))
        mock_config_manager.save_config = Mock()
        
        manager = RepositoryManager(config_manager=mock_config_manager)
        return manager
    
    def test_save_repositories_with_metadata(self, repository_manager):
        """
        Test saving repositories with metadata to configuration.
        
        Requirement: 6.5 - Persist configuration in structured format
        """
        # Add repository with metadata
        config = RepositoryConfig(
            name="persist-repo",
            uri="file:///tmp/persist",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Repository for persistence test",
            metadata={"key": "value"},
            is_default=True
        )
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        repository_manager._repositories["persist-repo"] = repository
        
        # Save repositories
        repository_manager._save_repositories()
        
        # Verify save was called
        repository_manager._config_manager.save_config.assert_called_once()
    
    def test_load_repositories_with_metadata(self, repository_manager):
        """
        Test loading repositories with metadata from configuration.
        
        Requirement: 6.5 - Persist configuration in structured format
        """
        # Mock configuration with repository data
        mock_repo_config = Mock()
        mock_repo_config.location = "file:///tmp/loaded"
        mock_repo_config.uri = "file:///tmp/loaded"
        mock_repo_config.description = "Loaded repository"
        
        mock_config = Mock()
        mock_config.repositories = {"loaded-repo": mock_repo_config}
        repository_manager._config_manager.get_config.return_value = mock_config
        
        # Load repositories
        repository_manager._load_repositories()
        
        # Verify repository was loaded
        assert "loaded-repo" in repository_manager._repositories, \
            "Repository should be loaded from configuration"
        
        loaded_repo = repository_manager._repositories["loaded-repo"]
        assert loaded_repo.config.name == "loaded-repo", "Repository name should match"
        assert loaded_repo.config.uri == "file:///tmp/loaded", "Repository URI should match"


# Import asyncio for async test helpers
import asyncio
