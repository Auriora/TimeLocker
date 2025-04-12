import pytest
from pathlib import Path
from src.backup_target import BackupTarget
from src.file_selections import FileSelection, SelectionType


@pytest.fixture
def selection():
    return FileSelection()

@pytest.fixture
def test_dir():
    return Path("/test/dir")

@pytest.fixture
def test_file():
    return Path("/test/file.txt")

def test_create_backup_target(selection):
    target = BackupTarget(selection)
    assert isinstance(target.selection, FileSelection)
    assert target.tags == []

def test_create_backup_target_with_tags(selection):
    tags = ["daily", "important"]
    target = BackupTarget(selection, tags=tags)
    assert target.tags == tags

def test_validate_requires_folder(selection, test_dir, test_file):
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

def test_backup_target_with_patterns(selection, test_dir):
    selection.add_path(test_dir)  # Add required folder
    selection.add_pattern("*.txt")
    selection.add_pattern("*.tmp", selection_type=SelectionType.EXCLUDE)
    
    target = BackupTarget(selection)
    assert target.validate()
    assert "*.txt" in target.selection.include_patterns
    assert "*.tmp" in target.selection.exclude_patterns

def test_backup_target_with_pattern_group(selection, test_dir):
    selection.add_path(test_dir)  # Add required folder
    selection.add_pattern_group("office_documents")
    
    target = BackupTarget(selection)
    assert target.validate()
    assert "*.doc" in target.selection.include_patterns
    assert "*.pdf" in target.selection.include_patterns

