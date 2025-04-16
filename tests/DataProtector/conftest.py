import pytest
from unittest.mock import Mock
from pathlib import Path

from DataProtector.file_selections import FileSelection


# from file_selections import FileSelection

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