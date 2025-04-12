import pytest
from unittest.mock import Mock
from pathlib import Path
from src.file_selections import FileSelection, SelectionType, PatternGroup

@pytest.fixture
def selection():
    return FileSelection()

@pytest.fixture
def test_dir():
    test_dir = Mock(spec=Path)
    test_dir.is_dir.return_value = True
    test_dir.__str__ = lambda x: "/test/dir"
    return test_dir

@pytest.fixture
def test_file():
    test_file = Mock(spec=Path)
    test_file.is_dir.return_value = False
    test_file.__str__ = lambda x: "/test/file.txt"
    return test_file

def test_add_include_path(selection, test_dir):
    selection.add_path(test_dir)
    assert test_dir in selection.includes
    assert test_dir not in selection.excludes

def test_add_exclude_path(selection, test_dir):
    selection.add_path(test_dir, SelectionType.EXCLUDE)
    assert test_dir in selection.excludes
    assert test_dir not in selection.includes

def test_remove_path(selection, test_dir):
    selection.add_path(test_dir)
    selection.remove_path(test_dir)
    assert test_dir not in selection.includes

def test_add_pattern(selection):
    pattern = "*.txt"
    selection.add_pattern(pattern)
    assert pattern in selection.include_patterns

def test_remove_pattern(selection):
    pattern = "*.txt"
    selection.add_pattern(pattern)
    selection.remove_pattern(pattern)
    assert pattern not in selection.include_patterns

def test_add_common_pattern_group(selection):
    selection.add_pattern_group("office_documents")
    assert "*.doc" in selection.include_patterns
    assert "*.pdf" in selection.include_patterns

def test_add_custom_pattern_group(selection):
    custom_group = PatternGroup("custom", ["*.custom", "*.test"])
    selection.add_pattern_group(custom_group)
    assert "*.custom" in selection.include_patterns
    assert "*.test" in selection.include_patterns

def test_remove_pattern_group(selection):
    selection.add_pattern_group("office_documents")
    selection.remove_pattern_group("office_documents")
    assert "*.doc" not in selection.include_patterns
    assert "*.pdf" not in selection.include_patterns

def test_validate_requires_folder(selection, test_dir, test_file):
    # Should raise error when no folders are included
    selection.add_path(test_file)
    with pytest.raises(ValueError):
        selection.validate()

    # Should pass when a folder is included
    selection.add_path(test_dir)
    assert selection.validate()

def test_pattern_group_exclusion(selection):
    selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
    assert "*.tmp" in selection.exclude_patterns
    assert "*.tmp" not in selection.include_patterns