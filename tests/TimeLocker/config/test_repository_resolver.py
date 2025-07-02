"""
Tests for repository resolver functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError,
    RepositoryAlreadyExistsError
)
from TimeLocker.utils.repository_resolver import (
    resolve_repository_uri,
    get_repository_info,
    list_available_repositories,
    get_default_repository
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary configuration directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a configuration manager with test data."""
    manager = ConfigurationManager(config_dir=temp_config_dir)

    # Add test repositories
    manager.add_repository(
            name="production",
            uri="s3:s3.af-south-1.amazonaws.com/prod-backup",
            description="Production backup repository"
    )
    manager.add_repository(
            name="local-test",
            uri="/tmp/test-backup",
            description="Local test repository"
    )
    manager.set_default_repository("production")

    return manager


class TestConfigurationManagerRepositoryMethods:
    """Test repository management methods in ConfigurationManager."""

    def test_add_repository(self, temp_config_dir):
        """Test adding a new repository."""
        manager = ConfigurationManager(config_dir=temp_config_dir)

        manager.add_repository(
                name="test-repo",
                uri="s3://bucket/path",
                description="Test repository"
        )

        repo = manager.get_repository("test-repo")
        assert repo["uri"] == "s3://bucket/path"
        assert repo["description"] == "Test repository"
        assert repo["type"] == "s3"
        assert "created" in repo

    def test_add_duplicate_repository(self, config_manager):
        """Test adding a repository with existing name raises error."""
        with pytest.raises(RepositoryAlreadyExistsError):
            config_manager.add_repository("production", "s3://other/path")

    def test_remove_repository(self, config_manager):
        """Test removing a repository."""
        config_manager.remove_repository("local-test")

        with pytest.raises(RepositoryNotFoundError):
            config_manager.get_repository("local-test")

    def test_remove_default_repository(self, config_manager):
        """Test removing default repository clears default setting."""
        config_manager.remove_repository("production")

        assert config_manager.get_default_repository() is None

    def test_remove_nonexistent_repository(self, config_manager):
        """Test removing non-existent repository raises error."""
        with pytest.raises(RepositoryNotFoundError):
            config_manager.remove_repository("nonexistent")

    def test_set_default_repository(self, config_manager):
        """Test setting default repository."""
        config_manager.set_default_repository("local-test")

        assert config_manager.get_default_repository() == "local-test"

    def test_set_nonexistent_default_repository(self, config_manager):
        """Test setting non-existent repository as default raises error."""
        with pytest.raises(RepositoryNotFoundError):
            config_manager.set_default_repository("nonexistent")

    def test_resolve_repository_by_name(self, config_manager):
        """Test resolving repository by name."""
        uri = config_manager.resolve_repository("production")
        assert uri == "s3:s3.af-south-1.amazonaws.com/prod-backup"

    def test_resolve_repository_by_uri(self, config_manager):
        """Test resolving repository by URI (passthrough)."""
        uri = config_manager.resolve_repository("s3://direct/uri")
        assert uri == "s3://direct/uri"

    def test_resolve_repository_default(self, config_manager):
        """Test resolving empty repository uses default."""
        uri = config_manager.resolve_repository("")
        assert uri == "s3:s3.af-south-1.amazonaws.com/prod-backup"

    def test_resolve_repository_no_default(self, temp_config_dir):
        """Test resolving empty repository with no default raises error."""
        manager = ConfigurationManager(config_dir=temp_config_dir)

        with pytest.raises(RepositoryNotFoundError):
            manager.resolve_repository("")


class TestRepositoryResolver:
    """Test repository resolver utility functions."""

    def test_resolve_repository_uri_by_name(self, config_manager, temp_config_dir):
        """Test resolving repository URI by name."""
        uri = resolve_repository_uri("production", config_dir=temp_config_dir)
        assert uri == "s3:s3.af-south-1.amazonaws.com/prod-backup"

    def test_resolve_repository_uri_by_uri(self, temp_config_dir):
        """Test resolving repository URI by direct URI."""
        uri = resolve_repository_uri("s3://direct/uri", config_dir=temp_config_dir)
        assert uri == "s3://direct/uri"

    def test_resolve_repository_uri_default(self, config_manager, temp_config_dir):
        """Test resolving repository URI using default."""
        uri = resolve_repository_uri(None, config_dir=temp_config_dir)
        assert uri == "s3:s3.af-south-1.amazonaws.com/prod-backup"

    def test_resolve_repository_uri_not_found(self, temp_config_dir):
        """Test resolving non-existent repository provides helpful error."""
        with pytest.raises(RepositoryNotFoundError) as exc_info:
            resolve_repository_uri("nonexistent", config_dir=temp_config_dir)

        assert "No repositories configured" in str(exc_info.value)

    def test_get_repository_info_named(self, config_manager, temp_config_dir):
        """Test getting repository info for named repository."""
        info = get_repository_info("production", config_dir=temp_config_dir)

        assert info["uri"] == "s3:s3.af-south-1.amazonaws.com/prod-backup"
        assert info["name"] == "production"
        assert info["description"] == "Production backup repository"
        assert info["type"] == "s3"
        assert info["is_named"] is True

    def test_get_repository_info_uri(self, temp_config_dir):
        """Test getting repository info for direct URI."""
        info = get_repository_info("s3://direct/uri", config_dir=temp_config_dir)

        assert info["uri"] == "s3://direct/uri"
        assert info["is_named"] is False
        assert "name" not in info

    def test_list_available_repositories(self, config_manager, temp_config_dir):
        """Test listing available repositories."""
        repos = list_available_repositories(config_dir=temp_config_dir)

        assert "production" in repos
        assert "local-test" in repos
        assert repos["production"]["uri"] == "s3:s3.af-south-1.amazonaws.com/prod-backup"

    def test_get_default_repository(self, config_manager, temp_config_dir):
        """Test getting default repository."""
        default = get_default_repository(config_dir=temp_config_dir)
        assert default == "production"


class TestRepositoryTypeDetection:
    """Test automatic repository type detection."""

    def test_s3_uri_detection(self, temp_config_dir):
        """Test S3 URI type detection."""
        manager = ConfigurationManager(config_dir=temp_config_dir)

        manager.add_repository("s3-test", "s3://bucket/path")
        repo = manager.get_repository("s3-test")
        assert repo["type"] == "s3"

        manager.add_repository("s3-restic", "s3:host/bucket")
        repo = manager.get_repository("s3-restic")
        assert repo["type"] == "s3"

    def test_local_uri_detection(self, temp_config_dir):
        """Test local URI type detection."""
        manager = ConfigurationManager(config_dir=temp_config_dir)

        manager.add_repository("local-test", "/path/to/repo")
        repo = manager.get_repository("local-test")
        assert repo["type"] == "local"

    def test_sftp_uri_detection(self, temp_config_dir):
        """Test SFTP URI type detection."""
        manager = ConfigurationManager(config_dir=temp_config_dir)

        manager.add_repository("sftp-test", "sftp://user@host/path")
        repo = manager.get_repository("sftp-test")
        assert repo["type"] == "sftp"
