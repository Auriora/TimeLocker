from src.backup_manager import BackupManager, BackupManagerError
from backup_repository import BackupRepository
from typing import Dict, List, Optional, Type
from urllib.parse import urlparse
import io
import logging
import pytest
import sys

class TestBackupManager:

    def test___init___empty_repository_factories(self):
        """
        Test that the _repository_factories attribute is initialized as an empty dictionary.
        This is the only verifiable behavior of the __init__ method based on its current implementation.
        """
        backup_manager = BackupManager()
        assert isinstance(backup_manager._repository_factories, dict)
        assert len(backup_manager._repository_factories) == 0

    def test_from_uri_2(self):
        """
        Test the from_uri method when the scheme is supported.

        This test verifies that when a valid URI with a supported scheme is provided,
        the from_uri method correctly parses the URI and calls the appropriate
        repository class's from_parsed_uri method with the parsed URI and password.
        """
        uri = "s3://test-bucket/backup"
        password = "test-password"

        # Mock the repo_classes dictionary
        BackupManager.from_uri.__func__.repo_classes = {
            's3': MockS3Repository
        }

        result = BackupManager.from_uri(uri, password)

        assert isinstance(result, MockS3Repository)
        assert result.parsed_uri == urlparse(uri)
        assert result.password == password

    def test_from_uri_unsupported_scheme(self):
        """
        Test that from_uri raises a BackupManagerError when given an unsupported scheme.
        This test verifies that when a URI with an unsupported scheme is provided,
        the method raises a BackupManagerError with an appropriate error message.
        """
        unsupported_uri = "unsupported://example.com/path"
        with pytest.raises(BackupManagerError) as excinfo:
            BackupManager.from_uri(unsupported_uri)
        assert str(excinfo.value) == "Unsupported repository scheme: unsupported"

    def test_get_repository_factory_nonexistent_name(self):
        """
        Test get_repository_factory with a nonexistent name.
        This tests the edge case where the name is not in the _repository_factories dictionary.
        """
        manager = BackupManager()
        result = manager.get_repository_factory("nonexistent", "some_type")
        assert result is None

    def test_get_repository_factory_nonexistent_type(self):
        """
        Test get_repository_factory with an existing name but nonexistent repo_type.
        This tests the edge case where the name exists in _repository_factories but the repo_type does not.
        """
        manager = BackupManager()
        manager.register_repository_factory("existing", "existing_type", BackupRepository)
        result = manager.get_repository_factory("existing", "nonexistent_type")
        assert result is None

    def test_get_repository_factory_returns_none_for_nonexistent_entry(self):
        """
        Test that get_repository_factory returns None when the requested
        name and repo_type combination does not exist in _repository_factories.
        """
        backup_manager = BackupManager()
        result = backup_manager.get_repository_factory("nonexistent_name", "nonexistent_type")
        assert result is None

    def test_init_creates_empty_repository_factories(self):
        """
        Test that the __init__ method of BackupManager creates an empty dictionary
        for _repository_factories.
        """
        manager = BackupManager()
        assert isinstance(manager._repository_factories, dict)
        assert len(manager._repository_factories) == 0

    def test_list_registered_backends_1(self):
        """
        Test that list_registered_backends returns a dictionary of registered backends
        with their supported repository types.
        """
        # Create a BackupManager instance
        manager = BackupManager()

        # Register some mock repository factories
        manager.register_repository_factory("backend1", "type1", BackupRepository)
        manager.register_repository_factory("backend1", "type2", BackupRepository)
        manager.register_repository_factory("backend2", "type3", BackupRepository)

        # Call the method under test
        result = manager.list_registered_backends()

        # Assert the expected output
        expected = {
            "backend1": ["type1", "type2"],
            "backend2": ["type3"]
        }
        assert result == expected, f"Expected {expected}, but got {result}"

    def test_list_registered_backends_empty(self):
        """
        Test the list_registered_backends method when no backends are registered.
        This is an edge case where the internal _repository_factories dictionary is empty.
        """
        manager = BackupManager()
        result = manager.list_registered_backends()
        assert isinstance(result, dict), "Result should be a dictionary"
        assert len(result) == 0, "Result should be an empty dictionary when no backends are registered"

    def test_redact_sensitive_info_no_username(self):
        """
        Test redact_sensitive_info method with a URL that doesn't contain a username.
        This is an edge case explicitly handled in the method implementation.
        """
        uri = "https://example.com/path"
        result = BackupManager.redact_sensitive_info(uri)
        assert result == uri, "URL without username should not be modified"

    def test_redact_sensitive_info_with_username(self):
        """
        Test that redact_sensitive_info correctly redacts the username and password
        when they are present in the URI.
        """
        uri = "https://username:password@example.com/path"
        expected_result = "https://example.com[:*****]/path"
        result = BackupManager.redact_sensitive_info(uri)
        assert result == expected_result, f"Expected {expected_result}, but got {result}"

    def test_redact_sensitive_info_with_username_2(self):
        """
        Test redact_sensitive_info method with a URL that contains a username.
        This tests the primary functionality of the method.
        """
        uri = "https://user@example.com/path"
        expected = "https://example.com[:*****]/path"
        result = BackupManager.redact_sensitive_info(uri)
        assert result == expected, "URL with username should have redacted credentials"

    def test_register_repository_factory_1(self):
        """
        Test registering a repository factory when the name is not in self._repository_factories
        and the repo_type is in self._repository_factories[name].
        Verifies that:
        1. A new entry is created for the name in self._repository_factories
        2. The repository class is correctly registered for the given name and repo_type
        3. A warning is printed about overwriting the existing repository class
        """
        backup_manager = BackupManager()
        name = "test_name"
        repo_type = "test_type"
        repository_class = Type[BackupRepository]

        # Pre-populate _repository_factories with an entry for the name
        backup_manager._repository_factories[name] = {repo_type: Type[BackupRepository]}

        # Capture print output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        backup_manager.register_repository_factory(name, repo_type, repository_class)

        # Reset stdout
        sys.stdout = sys.__stdout__

        assert name in backup_manager._repository_factories
        assert repo_type in backup_manager._repository_factories[name]
        assert backup_manager._repository_factories[name][repo_type] == repository_class
        assert "Warning: Overwriting existing repository class for test_name/test_type" in captured_output.getvalue()

    def test_register_repository_factory_2(self):
        """
        Test registering a repository factory when the name already exists
        and the repo_type is already registered for that name.
        This should overwrite the existing repository class.
        """
        backup_manager = BackupManager()

        # First registration
        backup_manager.register_repository_factory("test_name", "test_type", BackupRepository)

        # Second registration with the same name and repo_type
        class MockRepository(BackupRepository):
            pass

        backup_manager.register_repository_factory("test_name", "test_type", MockRepository)

        # Verify that the new repository class overwrote the previous one
        assert backup_manager._repository_factories["test_name"]["test_type"] == MockRepository

    def test_register_repository_factory_3(self):
        """
        Test registering a new repository factory when the name is not in self._repository_factories
        and the repo_type is not in self._repository_factories[name].

        This test verifies that:
        1. A new entry is created for the name in self._repository_factories
        2. The repository class is correctly associated with the name and repo_type
        3. No warning is printed about overwriting existing repository class
        """
        backup_manager = BackupManager()
        name = "new_name"
        repo_type = "new_type"
        repository_class = Type[BackupRepository]

        backup_manager.register_repository_factory(name, repo_type, repository_class)

        assert name in backup_manager._repository_factories
        assert repo_type in backup_manager._repository_factories[name]
        assert backup_manager._repository_factories[name][repo_type] == repository_class

    def test_register_repository_factory_overwrite_warning(self, capfd):
        """
        Test that a warning is printed when overwriting an existing repository class.
        """
        manager = BackupManager()

        # Register initial repository
        manager.register_repository_factory("test", "repo_type", BackupRepository)

        # Overwrite the existing repository
        manager.register_repository_factory("test", "repo_type", BackupRepository)

        captured = capfd.readouterr()
        assert "Warning: Overwriting existing repository class for test/repo_type" in captured.out

    def test_unsupported_scheme(self):
        """
        Test that the from_uri method raises a BackupManagerError when given a URI with an unsupported scheme.
        This tests the explicit error handling in the focal method for unsupported repository schemes.
        """
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


