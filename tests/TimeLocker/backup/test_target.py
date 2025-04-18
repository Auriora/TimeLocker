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

from unittest.mock import Mock

import pytest

from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType


def test_create_backup_target(selection):
    """Test creating a basic backup target"""
    target = BackupTarget(selection)
    assert isinstance(target.selection, FileSelection)
    assert target.tags == []

def test_create_backup_target_with_tags(selection):
    """Test creating a backup target with tags"""
    tags = ["daily", "important"]
    target = BackupTarget(selection, tags=tags)
    assert target.tags == tags

def test_init_with_none_selection():
    """Test initializing BackupTarget with None as the selection argument."""
    with pytest.raises(AttributeError):
        BackupTarget(None)

def test_init_with_none_tags():
    """Test initializing BackupTarget with None as the tags argument."""
    selection = FileSelection()
    target = BackupTarget(selection, None)
    assert target.tags == []

def test_init_with_selection_and_tags():
    """Test the initialization of BackupTarget with a FileSelection and tags."""
    selection = FileSelection()
    tags = ["important", "daily"]
    target = BackupTarget(selection, tags)
    assert target.selection == selection
    assert target.tags == tags

def test_validate_requires_folder(selection, test_dir, test_file):
    """Test that validation requires at least one folder"""
    target = BackupTarget(selection)

    # Should raise error when no folders are included
    selection.add_path(test_file)
    with pytest.raises(ValueError):
        target.validate()

    # Should pass when a folder is included
    selection = FileSelection()  # Reset selection
    selection.add_path(test_dir)
    target = BackupTarget(selection)
    assert target.validate()

def test_validate_raises_value_error():
    """Test that validate() method raises ValueError when the selection configuration is invalid."""
    mock_selection = Mock(spec=FileSelection)
    mock_selection.validate.side_effect = ValueError("Invalid selection")
    backup_target = BackupTarget(selection=mock_selection)
    with pytest.raises(ValueError):
        backup_target.validate()

def test_validate_returns_true_for_valid_selection():
    """Test that the validate method returns True when the selection is valid."""
    mock_selection = FileSelection()
    mock_selection.validate = lambda: True
    backup_target = BackupTarget(selection=mock_selection)
    assert backup_target.validate() == True

def test_backup_target_with_patterns(selection, test_dir):
    """Test backup target with include/exclude patterns"""
    selection.add_path(test_dir)  # Add required folder
    selection.add_pattern("*.txt")
    selection.add_pattern("*.tmp", selection_type=SelectionType.EXCLUDE)

    target = BackupTarget(selection)
    assert target.validate()
    assert "*.txt" in target.selection.include_patterns
    assert "*.tmp" in target.selection.exclude_patterns

def test_backup_target_with_pattern_group(selection, test_dir):
    """Test backup target with pattern groups"""
    selection.add_path(test_dir)  # Add required folder
    selection.add_pattern_group("office_documents")

    target = BackupTarget(selection)
    assert target.validate()
    assert "*.doc" in target.selection.include_patterns
    assert "*.pdf" in target.selection.include_patterns

