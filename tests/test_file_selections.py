import unittest
from unittest.mock import Mock
from pathlib import Path
from src.file_selections import FileSelection, SelectionType, PatternGroup


class TestFileSelection(unittest.TestCase):
    def setUp(self):
        self.selection = FileSelection()
        # Create mock Path objects
        self.test_dir = Mock(spec=Path)
        self.test_dir.is_dir.return_value = True
        self.test_dir.__str__ = lambda x: "/test/dir"
        
        self.test_file = Mock(spec=Path)
        self.test_file.is_dir.return_value = False
        self.test_file.__str__ = lambda x: "/test/file.txt"

    def test_add_include_path(self):
        self.selection.add_path(self.test_dir)
        self.assertIn(self.test_dir, self.selection.includes)
        self.assertNotIn(self.test_dir, self.selection.excludes)

    def test_add_exclude_path(self):
        self.selection.add_path(self.test_dir, SelectionType.EXCLUDE)
        self.assertIn(self.test_dir, self.selection.excludes)
        self.assertNotIn(self.test_dir, self.selection.includes)

    def test_remove_path(self):
        self.selection.add_path(self.test_dir)
        self.selection.remove_path(self.test_dir)
        self.assertNotIn(self.test_dir, self.selection.includes)

    def test_add_pattern(self):
        pattern = "*.txt"
        self.selection.add_pattern(pattern)
        self.assertIn(pattern, self.selection.include_patterns)

    def test_remove_pattern(self):
        pattern = "*.txt"
        self.selection.add_pattern(pattern)
        self.selection.remove_pattern(pattern)
        self.assertNotIn(pattern, self.selection.include_patterns)

    def test_add_common_pattern_group(self):
        self.selection.add_pattern_group("office_documents")
        self.assertIn("*.doc", self.selection.include_patterns)
        self.assertIn("*.pdf", self.selection.include_patterns)

    def test_add_custom_pattern_group(self):
        custom_group = PatternGroup("custom", ["*.custom", "*.test"])
        self.selection.add_pattern_group(custom_group)
        self.assertIn("*.custom", self.selection.include_patterns)
        self.assertIn("*.test", self.selection.include_patterns)

    def test_remove_pattern_group(self):
        self.selection.add_pattern_group("office_documents")
        self.selection.remove_pattern_group("office_documents")
        self.assertNotIn("*.doc", self.selection.include_patterns)
        self.assertNotIn("*.pdf", self.selection.include_patterns)

    def test_validate_requires_folder(self):
        # Should raise error when no folders are included
        self.selection.add_path(self.test_file)
        with self.assertRaises(ValueError):
            self.selection.validate()

        # Should pass when a folder is included
        self.selection.add_path(self.test_dir)
        self.assertTrue(self.selection.validate())

    def test_invalid_common_group(self):
        with self.assertRaises(KeyError):
            self.selection.add_pattern_group("non_existent_group")

    def test_pattern_group_exclusion(self):
        self.selection.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
        self.assertIn("*.tmp", self.selection.exclude_patterns)
        self.assertNotIn("*.tmp", self.selection.include_patterns)


if __name__ == '__main__':
    unittest.main()

