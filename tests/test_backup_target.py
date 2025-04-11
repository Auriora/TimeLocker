import unittest
from pathlib import Path
from src.backup_target import BackupTarget
from src.file_selections import FileSelection, SelectionType


class TestBackupTarget(unittest.TestCase):
    def setUp(self):
        self.selection = FileSelection()
        self.test_dir = Path("/test/dir")
        self.test_file = Path("/test/file.txt")

    def test_create_backup_target(self):
        target = BackupTarget(self.selection)
        self.assertIsInstance(target.selection, FileSelection)
        self.assertEqual(target.tags, [])

    def test_create_backup_target_with_tags(self):
        tags = ["daily", "important"]
        target = BackupTarget(self.selection, tags=tags)
        self.assertEqual(target.tags, tags)

    def test_validate_requires_folder(self):
        target = BackupTarget(self.selection)
        
        # Should raise error when no folders are included
        self.selection.add_path(self.test_file)
        with self.assertRaises(ValueError):
            target.validate()

        # Should pass when a folder is included
        self.selection = FileSelection()  # Reset selection
        self.selection.add_path(self.test_dir)
        target = BackupTarget(self.selection)
        self.assertTrue(target.validate())

    def test_backup_target_with_patterns(self):
        self.selection.add_path(self.test_dir)  # Add required folder
        self.selection.add_pattern("*.txt")
        self.selection.add_pattern("*.tmp", selection_type=SelectionType.EXCLUDE)
        
        target = BackupTarget(self.selection)
        self.assertTrue(target.validate())
        self.assertIn("*.txt", target.selection.include_patterns)
        self.assertIn("*.tmp", target.selection.exclude_patterns)

    def test_backup_target_with_pattern_group(self):
        self.selection.add_path(self.test_dir)  # Add required folder
        self.selection.add_pattern_group("office_documents")
        
        target = BackupTarget(self.selection)
        self.assertTrue(target.validate())
        self.assertIn("*.doc", target.selection.include_patterns)
        self.assertIn("*.pdf", target.selection.include_patterns)


if __name__ == '__main__':
    unittest.main()

