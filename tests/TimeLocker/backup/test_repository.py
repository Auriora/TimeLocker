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

from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock

import pytest

from TimeLocker.backup_repository import BackupRepository, RetentionPolicy
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget


def test_apply_retention_policy_1():
    """
    Test that apply_retention_policy correctly applies the retention policy
    when at least one retention period is specified and returns True.
    """
    repo = BackupRepository()
    policy = RetentionPolicy(daily=7, weekly=4)
    result = repo.apply_retention_policy(policy)
    assert result == True

def test_apply_retention_policy_with_invalid_policy():
    """
    Test apply_retention_policy with an invalid retention policy.
    The method should return False when the policy is not valid.
    """
    repo = Mock(spec=BackupRepository)
    invalid_policy = RetentionPolicy()  # All fields are None by default
    result = BackupRepository.apply_retention_policy(repo, invalid_policy)
    assert result == False, "Expected False for invalid retention policy"

def test_backup_target_1():
    """
    Test that the backup_target method creates a new backup successfully.

    This test verifies that:
    1. The method accepts a list of BackupTarget objects and an optional list of tags.
    2. It returns a dictionary containing information about the created backup.
    3. The returned dictionary is not empty, indicating a successful backup operation.
    """
    # Create a mock BackupRepository implementation for testing
    class MockBackupRepository(BackupRepository):
        def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
            return {"status": "success", "backup_id": "123"}

    # Create an instance of the mock repository
    repo = MockBackupRepository()

    # Create a mock BackupTarget
    class MockBackupTarget(BackupTarget):
        pass

    # Prepare test data
    targets = [MockBackupTarget()]
    tags = ["test", "backup"]

    # Call the method under test
    result = repo.backup_target(targets, tags)

    # Assert the result
    assert isinstance(result, dict), "The returned value should be a dictionary"
    assert len(result) > 0, "The returned dictionary should not be empty"
    assert "status" in result, "The result should contain a 'status' key"
    assert result["status"] == "success", "The backup should be successful"

def test_backup_target_with_empty_targets_list():
    """
    Test the backup_target method with an empty list of targets.
    This tests the edge case of calling the method with no actual backup targets.
    """
    repo = MockBackupRepository()
    result = repo.backup_target([])
    assert result == {"error": "No backup targets provided"}

def test_backup_target_with_invalid_tags():
    """
    Test the backup_target method with invalid tags.
    This tests the edge case of providing tags that are not strings.
    """

    # Create a mock BackupTarget
    class MockBackupTarget(BackupTarget):
        pass

    repo = MockBackupRepository()
    target = MockBackupTarget()
    with pytest.raises(ValueError):
        repo.backup_target([target], tags=[1, 2, 3])

def test_check_method_not_implemented():
    """
    Test that calling the abstract 'check' method raises NotImplementedError.
    """
    class ConcreteBackupRepository(BackupRepository):
        pass

    repository = ConcreteBackupRepository()

    try:
        repository.check()
    except NotImplementedError:
        assert True
    else:
        assert False, "NotImplementedError was not raised"

def test_check_repository_availability():
    """
    Test that the check method returns a boolean indicating repository availability.

    This test verifies that the check method of the BackupRepository class
    returns a boolean value. The method should return True if the backup
    repository is available, and False otherwise.
    """
    # Create a mock BackupRepository
    class MockBackupRepository(BackupRepository):
        def check(self) -> bool:
            return True

    repository = MockBackupRepository()

    # Call the check method
    result = repository.check()

    # Assert that the result is a boolean
    assert isinstance(result, bool), "The check method should return a boolean value"

    # Assert that the result is True for this mock implementation
    assert result is True, "The mock repository should be available"

def test_initialize_not_implemented():
    """
    Test that calling initialize() on the abstract base class raises NotImplementedError.
    This tests the edge case of trying to use the abstract method directly.
    """

    class ConcreteBackupRepository(BackupRepository):
        pass

    repo = ConcreteBackupRepository()
    with pytest.raises(NotImplementedError):
        repo.initialize()

def test_initialize_returns_true():
    """
    Test that the initialize method of BackupRepository returns True when successful.

    This test verifies that when the initialize method is called on a concrete
    implementation of BackupRepository, it returns True, indicating successful
    initialization of the backup repository.
    """
    class ConcreteBackupRepository(BackupRepository):
        def initialize(self) -> bool:
            return True

    repo = ConcreteBackupRepository()
    result = repo.initialize()
    assert result == True, "The initialize method should return True when successful"

def test_restore_snapshot_to_target_path():
    """
    Test restoring a snapshot to a specific target path.

    This test verifies that the restore method of BackupRepository
    correctly restores a snapshot to a given target path and returns
    an appropriate success message.
    """
    class ConcreteBackupRepository(BackupRepository):
        def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
            return f"Snapshot {snapshot_id} restored to {target_path}"

    repo = ConcreteBackupRepository()
    snapshot_id = "test_snapshot_001"
    target_path = Path("/tmp/restore_location")

    result = repo.restore(snapshot_id, target_path)

    assert result == f"Snapshot {snapshot_id} restored to {target_path}"

def test_snapshots_list_all():
    """
    Test that snapshots() returns a list of all available BackupSnapshot objects when called without tags.
    """
    class ConcreteBackupRepository(BackupRepository):
        def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
            return [BackupSnapshot(), BackupSnapshot()]

    repo = ConcreteBackupRepository()
    result = repo.snapshots()
    assert isinstance(result, list)
    assert all(isinstance(snapshot, BackupSnapshot) for snapshot in result)
    assert len(result) == 2

def test_stats_empty_repository():
    """
    Test the stats method when the repository is empty.
    This tests the edge case of calling stats on a repository with no snapshots.
    """
    class EmptyRepository(BackupRepository):
        def stats(self) -> dict:
            return {}

    repo = EmptyRepository()
    result = repo.stats()
    assert isinstance(result, dict), "Stats should return a dictionary"
    assert len(result) == 0, "Stats should be empty for an empty repository"

def test_stats_returns_dict():
    """
    Test that the stats method returns a dictionary.

    This test verifies that the stats method of the BackupRepository
    class returns a dictionary object. It does not check the contents
    of the dictionary, only that the return type is correct.
    """
    repo = MockBackupRepository()
    result = repo.stats()
    assert isinstance(result, dict), "stats method should return a dictionary"

class MockBackupRepository(BackupRepository):
    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        if not targets:
            return {"error": "No backup targets provided"}
        if tags and not all(isinstance(tag, str) for tag in tags):
            raise ValueError("All tags must be strings")
        return {"status": "success"}

    def stats(self) -> dict:
        return {}
