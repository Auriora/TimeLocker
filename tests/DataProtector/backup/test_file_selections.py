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

import pytest

from DataProtector.file_selections import PatternGroup, SelectionType


def test_add_include_path(selection, test_dir):
    """Test adding a path to include list"""
    selection.add_path(test_dir)
    assert test_dir in selection.includes
    assert test_dir not in selection.excludes

def test_add_exclude_path(selection, test_dir):
    """Test adding a path to exclude list"""
    selection.add_path(test_dir, SelectionType.EXCLUDE)
    assert test_dir in selection.excludes
    assert test_dir not in selection.includes

def test_remove_path(selection, test_dir):
    """Test removing a path from selections"""
    selection.add_path(test_dir)
    selection.remove_path(test_dir)
    assert test_dir not in selection.includes

def test_add_pattern(selection):
    """Test adding a single pattern"""
    pattern = "*.txt"
    selection.add_pattern(pattern)
    assert pattern in selection.include_patterns

def test_remove_pattern(selection):
    """Test removing a single pattern"""
    pattern = "*.txt"
    selection.add_pattern(pattern)
    selection.remove_pattern(pattern)
    assert pattern not in selection.include_patterns

def test_pattern_group_exclusion(selection):
    """Test adding patterns as exclusions"""
    selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
    assert "*.tmp" in selection.exclude_patterns
    assert "*.tmp" not in selection.include_patterns

def test_add_common_pattern_group(selection):
    """Test adding a predefined pattern group"""
    selection.add_pattern_group("office_documents")
    assert "*.doc" in selection.include_patterns
    assert "*.pdf" in selection.include_patterns

def test_add_custom_pattern_group(selection):
    """Test adding a custom pattern group"""
    custom_group = PatternGroup("custom", ["*.custom", "*.test"])
    selection.add_pattern_group(custom_group)
    assert "*.custom" in selection.include_patterns
    assert "*.test" in selection.include_patterns

def test_remove_pattern_group(selection):
    """Test removing a pattern group"""
    selection.add_pattern_group("office_documents")
    selection.remove_pattern_group("office_documents")
    assert "*.doc" not in selection.include_patterns
    assert "*.pdf" not in selection.include_patterns

def test_validate_requires_folder(selection, test_dir, test_file):
    """Test that validation requires at least one folder"""
    # Should raise error when no folders are included
    selection.add_path(test_file)
    with pytest.raises(ValueError):
        selection.validate()

    # Should pass when a folder is included
    selection.add_path(test_dir)
    assert selection.validate()