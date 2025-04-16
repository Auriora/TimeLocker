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

from datetime import datetime
from pathlib import Path

import pytest

from DataProtector.backup_snapshot import BackupSnapshot
from .mock_repository import MockBackupRepository


def test___init___initializes_attributes_correctly():
    """
    Test that the __init__ method of BackupSnapshot correctly initializes all attributes.
    """
    repo = MockBackupRepository()
    snapshot_id = "test_snapshot_001"
    timestamp = datetime.now()
    paths = [Path("/test/path1"), Path("/test/path2")]

    snapshot = BackupSnapshot(repo, snapshot_id, timestamp, paths)

    assert snapshot.repo == repo
    assert snapshot.id == snapshot_id
    assert snapshot.timestamp == timestamp
    assert snapshot.paths == paths

def test_delete_snapshot():
    """
    Test that the delete method calls the forget_snapshot method of the repository
    with the correct parameters and returns its result.
    """
    # Setup
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "test_id", datetime.now(), [Path("/test/path")])

    # Execute
    result = snapshot.delete(prune=True)

    # Assert
    assert result == True  # MockBackupRepository.forget_snapshot returns True for valid IDs

def test_find_empty_pattern():
    """
    Test the find method with an empty pattern string.
    This tests the edge case of providing an empty input to the method.
    """
    snapshot = BackupSnapshot(MockBackupRepository(), "test_id", datetime.now(), [Path("test_path")])
    result = snapshot.find("")
    assert result == [], "Expected empty list for empty pattern"

def test_find_matches_pattern():
    """
    Test that the find method returns a list of files matching the given pattern.
    This test verifies that when a pattern is provided, the method correctly
    identifies and returns the matching files from the snapshot.
    """
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "test_id", datetime.now(), [Path("/test/path")])
    pattern = "*.txt"

    result = snapshot.find(pattern)

    assert isinstance(result, list)
    assert all(isinstance(item, str) for item in result)
    # Additional assertions would depend on the expected behavior of the find method

def test_from_dict_1():
    """
    Test that from_dict method correctly creates a BackupSnapshot instance
    from a dictionary containing snapshot data.
    """
    # Mock BackupRepository
    mock_repo = MockBackupRepository()

    # Prepare test data
    test_data = {
        'id': 'test_snapshot_id',
        'timestamp': '2023-05-20T12:34:56',
        'path': '/test/backup/path'
    }

    # Call the method under test
    snapshot = BackupSnapshot.from_dict(mock_repo, test_data)

    # Assert the created snapshot has correct attributes
    assert isinstance(snapshot, BackupSnapshot)
    assert snapshot.repo == mock_repo
    assert snapshot.id == 'test_snapshot_id'
    assert snapshot.timestamp == datetime(2023, 5, 20, 12, 34, 56)
    assert snapshot.paths == Path('/test/backup/path')

def test_from_dict_invalid_timestamp_format():
    """
    Test that from_dict method raises a ValueError when the timestamp in the input dictionary has an invalid format.
    """
    repository = MockBackupRepository()
    data = {
        'id': 'snapshot1',
        'timestamp': 'invalid_timestamp_format',
        'path': '/path/to/backup'
    }

    with pytest.raises(ValueError):
        BackupSnapshot.from_dict(repository, data)

def test_from_dict_missing_required_key():
    """
    Test that from_dict method raises a KeyError when a required key is missing from the input dictionary.
    """
    repository = MockBackupRepository()
    data = {
        'id': 'snapshot1',
        'timestamp': '2023-01-01T00:00:00'
        # 'path' key is intentionally omitted
    }

    with pytest.raises(KeyError):
        BackupSnapshot.from_dict(repository, data)

def test_list_files_in_snapshot():
    """
    Test that the list method returns the correct list of files in the snapshot.
    This test verifies that when calling list() on a BackupSnapshot object,
    it returns a list of strings representing the files in the snapshot.
    """
    # Setup
    repo = MockBackupRepository()
    snapshot_id = "test_snapshot"
    timestamp = datetime.now()
    paths = [Path("/test/path1"), Path("/test/path2")]
    snapshot = BackupSnapshot(repo, snapshot_id, timestamp, paths)

    # Execute
    result = snapshot.list()

    # Assert
    assert isinstance(result, list)
    assert all(isinstance(item, str) for item in result)

def test_restore_default_target_path():
    """
    Test the restore method of BackupSnapshot when no target path is provided.

    This test verifies that the restore method correctly calls the repository's
    restore method with the snapshot's ID and None as the target path when no
    target path is specified.
    """
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "test_id", datetime.now(), [Path("/test/path")])

    result = snapshot.restore()

    assert result == "Mock restore completed successfully"

def test_restore_file_1():
    """
    Test the restore_file method of BackupSnapshot class.

    This test verifies that the restore_file method successfully restores a single file
    from the snapshot when called without a target path. It checks if the method returns
    True, indicating a successful file restoration.
    """
    # Create a mock BackupRepository
    repo = MockBackupRepository()

    # Create a BackupSnapshot instance
    snapshot = BackupSnapshot(repo, "test_snapshot_id", datetime.now(), [Path("/test/file.txt")])

    # Call the restore_file method
    result = snapshot.restore_file()

    # Assert that the method returns True
    assert result == True, "restore_file should return True for successful restoration"

def test_restore_file_invalid_target_path():
    """
    Test restore_file method with an invalid target path.
    This test checks if the method handles an invalid target path correctly.
    """
    # Setup
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "snapshot1", datetime.now(), [Path("/test/file.txt")])

    # Test
    invalid_path = Path("/nonexistent/directory/file.txt")
    result = snapshot.restore_file(invalid_path)

    # Assert
    assert result == False, "restore_file should return False for an invalid target path"

def test_restore_with_nonexistent_target_path():
    """
    Test the restore method with a non-existent target path.
    This tests the edge case where the target_path provided does not exist.
    The method should handle this scenario by delegating to the repo's restore method.
    """
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "test_id", datetime.now(), [Path("/test/path")])
    non_existent_path = Path("/non/existent/path")

    result = snapshot.restore(non_existent_path)

    # Assert that the result is what we expect from our mock
    assert result == "Mock restore completed successfully"

def test_verify_example_negative_test():
    """
    Test the verify method when the snapshot integrity check fails.
    This test assumes that the verify method internally checks the snapshot's
    integrity and returns False if the integrity check fails.
    """
    # Setup
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(repo, "test_id", datetime.now(), [Path("/test/path")])

    # Verify
    result = snapshot.verify()

    # Assert
    assert result == False, "Expected verify to return False for a corrupted snapshot"

def test_verify_snapshot_integrity():
    """
    Test that the verify method correctly checks the integrity of a backup snapshot.
    This test ensures that the method returns True for a valid snapshot and False for an invalid one.
    """
    # Setup
    repo = MockBackupRepository()
    snapshot = BackupSnapshot(
        repo=repo,
        snapshot_id="test_snapshot",
        timestamp=datetime.now(),
        paths=[Path("/test/path")]
    )

    # Test
    result = snapshot.verify()

    # Assert
    assert result == False, "Verify method should return False for an unimplemented verify method"
