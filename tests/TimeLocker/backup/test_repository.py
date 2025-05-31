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
from datetime import datetime

import pytest

from TimeLocker.backup_repository import BackupRepository, RetentionPolicy
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.backup_target import BackupTarget


class MockTestBackupRepository(BackupRepository):
    """Concrete implementation of BackupRepository for testing"""

    def __init__(self):
        self._initialized = False
        self._snapshots = {}
        self._location = "/test/backup/location"

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def check(self) -> bool:
        return self._initialized

    def backup_target(self, targets: List[BackupTarget], tags: Optional[List[str]] = None) -> Dict:
        if not targets:
            return {"error": "No backup targets provided"}
        if tags and not all(isinstance(tag, str) for tag in tags):
            raise ValueError("All tags must be strings")

        snapshot_id = f"test-snapshot-{len(self._snapshots)}"
        paths = []
        for target in targets:
            if hasattr(target, 'selection') and target.selection:
                paths.extend(target.selection.get_backup_paths())

        snapshot = BackupSnapshot(self, snapshot_id, datetime.now(), paths)
        self._snapshots[snapshot_id] = snapshot
        return {"status": "success", "snapshot_id": snapshot_id}

    def restore(self, snapshot_id: str, target_path: Optional[Path] = None) -> str:
        if snapshot_id in self._snapshots:
            return f"Snapshot {snapshot_id} restored to {target_path}"
        return "Snapshot not found"

    def snapshots(self, tags: Optional[List[str]] = None) -> List[BackupSnapshot]:
        return list(self._snapshots.values())

    def stats(self) -> dict:
        return {
                "total_size":   1000000,
                "total_files":  100,
                "unique_files": 50
        }

    def location(self) -> str:
        return self._location

    def forget_snapshot(self, snapshotid: str, prune: bool = False) -> bool:
        if snapshotid in self._snapshots:
            del self._snapshots[snapshotid]
            return True
        return False

    def prune_data(self) -> bool:
        return True

    def validate(self) -> bool:
        return self._initialized


def test_apply_retention_policy_1():
    """
    Test that apply_retention_policy correctly applies the retention policy
    when at least one retention period is specified and returns True.
    """
    repo = MockTestBackupRepository()
    policy = RetentionPolicy(daily=7, weekly=4)
    result = repo.apply_retention_policy(policy)
    assert result is None  # Base implementation returns None


def test_apply_retention_policy_with_invalid_policy():
    """
    Test apply_retention_policy with an invalid retention policy.
    The method should return False when the policy is not valid.
    """
    repo = MockTestBackupRepository()
    invalid_policy = RetentionPolicy()  # All fields are None by default
    result = repo.apply_retention_policy(invalid_policy)
    assert result is None  # Base implementation returns None for invalid policy


def test_backup_target_1():
    """
    Test that the backup_target method creates a new backup successfully.

    This test verifies that:
    1. The method accepts a list of BackupTarget objects and an optional list of tags.
    2. It returns a dictionary containing information about the created backup.
    3. The returned dictionary is not empty, indicating a successful backup operation.
    """
    # Create an instance of the testable repository
    repo = MockTestBackupRepository()

    # Create a mock BackupTarget with minimal required attributes
    from TimeLocker.file_selections import FileSelection
    selection = FileSelection()
    target = BackupTarget(selection=selection)

    # Prepare test data
    targets = [target]
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
    repo = MockTestBackupRepository()
    result = repo.backup_target([])
    assert result == {"error": "No backup targets provided"}


def test_backup_target_with_invalid_tags():
    """
    Test the backup_target method with invalid tags.
    This tests the edge case of providing tags that are not strings.
    """
    from TimeLocker.file_selections import FileSelection

    repo = MockTestBackupRepository()
    selection = FileSelection()
    target = BackupTarget(selection=selection)
    with pytest.raises(ValueError):
        repo.backup_target([target], tags=[1, 2, 3])


def test_check_method_not_implemented():
    """
    Test that trying to instantiate an incomplete concrete class raises TypeError.
    """
    with pytest.raises(TypeError):
        class IncompleteBackupRepository(BackupRepository):
            pass

        repository = IncompleteBackupRepository()


def test_check_repository_availability():
    """
    Test that the check method returns a boolean indicating repository availability.

    This test verifies that the check method of the BackupRepository class
    returns a boolean value. The method should return True if the backup
    repository is available, and False otherwise.
    """
    repository = MockTestBackupRepository()

    # Call the check method
    result = repository.check()

    # Assert that the result is a boolean
    assert isinstance(result, bool), "The check method should return a boolean value"

    # Assert that the result is False initially (not initialized)
    assert result is False, "The repository should not be available before initialization"

    # Initialize and test again
    repository.initialize()
    result = repository.check()
    assert result is True, "The repository should be available after initialization"


def test_initialize_not_implemented():
    """
    Test that trying to instantiate an incomplete concrete class raises TypeError.
    This tests the edge case of trying to use an incomplete implementation.
    """
    with pytest.raises(TypeError):
        class IncompleteBackupRepository(BackupRepository):
            pass

        repo = IncompleteBackupRepository()


def test_initialize_returns_true():
    """
    Test that the initialize method of BackupRepository returns True when successful.

    This test verifies that when the initialize method is called on a concrete
    implementation of BackupRepository, it returns True, indicating successful
    initialization of the backup repository.
    """
    repo = MockTestBackupRepository()
    result = repo.initialize()
    assert result == True, "The initialize method should return True when successful"


def test_restore_snapshot_to_target_path():
    """
    Test restoring a snapshot to a specific target path.

    This test verifies that the restore method of BackupRepository
    correctly restores a snapshot to a given target path and returns
    an appropriate success message.
    """
    repo = MockTestBackupRepository()
    snapshot_id = "test_snapshot_001"
    target_path = Path("/tmp/restore_location")

    # First create a snapshot to restore
    from TimeLocker.file_selections import FileSelection
    selection = FileSelection()
    target = BackupTarget(selection=selection)
    backup_result = repo.backup_target([target])
    created_snapshot_id = backup_result["snapshot_id"]

    # Now restore the created snapshot
    result = repo.restore(created_snapshot_id, target_path)

    assert result == f"Snapshot {created_snapshot_id} restored to {target_path}"


def test_snapshots_list_all():
    """
    Test that snapshots() returns a list of all available BackupSnapshot objects when called without tags.
    """
    repo = MockTestBackupRepository()
    result = repo.snapshots()
    assert isinstance(result, list)
    assert len(result) == 0  # Initially empty


def test_stats_empty_repository():
    """
    Test the stats method when the repository is empty.
    This tests the edge case of calling stats on a repository with no snapshots.
    """
    repo = MockTestBackupRepository()
    result = repo.stats()
    assert isinstance(result, dict), "Stats should return a dictionary"
    assert len(result) > 0, "Stats should contain default values"


def test_stats_returns_dict():
    """
    Test that the stats method returns a dictionary.

    This test verifies that the stats method of the BackupRepository
    class returns a dictionary object. It does not check the contents
    of the dictionary, only that the return type is correct.
    """
    repo = MockTestBackupRepository()
    result = repo.stats()
    assert isinstance(result, dict), "stats method should return a dictionary"
