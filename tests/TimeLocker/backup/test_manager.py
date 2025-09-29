"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Type
from urllib.parse import urlparse
from unittest.mock import Mock, patch

import pytest

from TimeLocker.backup_manager import BackupManager, BackupManagerError
from TimeLocker.backup_repository import BackupRepository


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_init_creates_empty_repository_factories():
    """Test that __init__ creates an empty repository factories dictionary"""
    manager = BackupManager()
    assert isinstance(manager._repository_factories, dict)
    assert len(manager._repository_factories) == 0


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_redact_sensitive_info_no_username():
    """Test redacting sensitive info from URL without username"""
    uri = "https://example.com/path"
    result = BackupManager.redact_sensitive_info(uri)
    assert result == uri, "URL without username should not be modified"


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_redact_sensitive_info_with_username():
    """Test redacting username and password from URL"""
    uri = "https://username:password@example.com/path"
    expected_result = "https://example.com[:*****]/path"
    result = BackupManager.redact_sensitive_info(uri)
    assert result == expected_result


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_get_repository_factory_nonexistent():
    """Test getting nonexistent repository factory"""
    manager = BackupManager()
    result = manager.get_repository_factory("nonexistent", "some_type")
    assert result is None


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_get_repository_factory_nonexistent_type():
    """Test getting nonexistent repository type from existing factory"""
    manager = BackupManager()
    manager.register_repository_factory("existing", "existing_type", BackupRepository)
    result = manager.get_repository_factory("existing", "nonexistent_type")
    assert result is None


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_register_repository_factory():
    """Test registering a new repository factory"""
    manager = BackupManager()
    name = "test_name"
    repo_type = "test_type"
    repository_class = Type[BackupRepository]

    # First registration
    manager.register_repository_factory(name, repo_type, repository_class)
    assert name in manager._repository_factories
    assert repo_type in manager._repository_factories[name]
    assert manager._repository_factories[name][repo_type] == repository_class

    # Second registration (overwrite)
    class MockRepository(BackupRepository):
        pass

    manager.register_repository_factory(name, repo_type, MockRepository)
    assert manager._repository_factories[name][repo_type] == MockRepository


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_register_repository_factory_overwrite_warning(capfd):
    """Test warning when overwriting existing repository factory"""
    manager = BackupManager()
    manager.register_repository_factory("test", "repo_type", BackupRepository)
    manager.register_repository_factory("test", "repo_type", BackupRepository)
    captured = capfd.readouterr()
    assert "Warning: Overwriting existing repository class for test/repo_type" in captured.out


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_list_registered_backends():
    """Test listing registered backends and their types"""
    manager = BackupManager()
    manager.register_repository_factory("backend1", "type1", BackupRepository)
    manager.register_repository_factory("backend1", "type2", BackupRepository)
    manager.register_repository_factory("backend2", "type3", BackupRepository)

    result = manager.list_registered_backends()
    expected = {
            "backend1": ["type1", "type2"],
            "backend2": ["type3"]
    }
    assert result == expected


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_list_registered_backends_empty():
    """Test listing backends when none are registered"""
    manager = BackupManager()
    result = manager.list_registered_backends()
    assert isinstance(result, dict)
    assert len(result) == 0


@patch('TimeLocker.restic.Repositories.s3.client')
@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_from_uri_supported_scheme(mock_boto_client):
    """Test creating repository from supported URI scheme"""
    # Mock the S3 client to avoid AWS authentication
    mock_s3_client = Mock()
    mock_s3_client.head_bucket.return_value = {}  # Successful bucket validation
    mock_boto_client.return_value = mock_s3_client

    uri = "s3://test-bucket/backup"
    password = "test-password"

    result = BackupManager.from_uri(uri, password)

    # Should create an S3ResticRepository instance
    from TimeLocker.restic.Repositories.s3 import S3ResticRepository
    assert isinstance(result, S3ResticRepository)
    assert result._location == "s3:test-bucket/backup"

    # Verify S3 client was called for validation
    mock_boto_client.assert_called_with('s3')
    mock_s3_client.head_bucket.assert_called_with(Bucket='test-bucket')

    # The main goal is that we can create an S3 repository without AWS errors
    # The password handling is tested in the S3ResticRepository tests


@pytest.mark.backup
@pytest.mark.filesystem
@pytest.mark.unit
def test_from_uri_unsupported_scheme():
    """Test error when using unsupported URI scheme"""
    unsupported_uri = "unsupported://example.com/path"
    with pytest.raises(BackupManagerError) as excinfo:
        BackupManager.from_uri(unsupported_uri)
    assert str(excinfo.value) == "Unsupported repository scheme: unsupported"


class MockS3Repository:
    def __init__(self, parsed_uri, password):
        self.parsed_uri = parsed_uri
        self.password = password

    @classmethod
    def from_parsed_uri(cls, parsed_uri, password):
        return cls(parsed_uri, password)
