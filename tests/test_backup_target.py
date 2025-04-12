import pytest
from backup_target import BackupTarget
from file_selections import SelectionType, FileSelection


class TestBackupTargetCreation:
    def test_create_backup_target(self, selection):
        """Test creating a basic backup target"""
        target = BackupTarget(selection)
        assert isinstance(target.selection, FileSelection)
        assert target.tags == []

    def test_create_backup_target_with_tags(self, selection):
        """Test creating a backup target with tags"""
        tags = ["daily", "important"]
        target = BackupTarget(selection, tags=tags)
        assert target.tags == tags

class TestBackupTargetValidation:
    def test_validate_requires_folder(self, selection, test_dir, test_file):
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

class TestBackupTargetPatterns:
    def test_backup_target_with_patterns(self, selection, test_dir):
        """Test backup target with include/exclude patterns"""
        selection.add_path(test_dir)  # Add required folder
        selection.add_pattern("*.txt")
        selection.add_pattern("*.tmp", selection_type=SelectionType.EXCLUDE)
        
        target = BackupTarget(selection)
        assert target.validate()
        assert "*.txt" in target.selection.include_patterns
        assert "*.tmp" in target.selection.exclude_patterns

    def test_backup_target_with_pattern_group(self, selection, test_dir):
        """Test backup target with pattern groups"""
        selection.add_path(test_dir)  # Add required folder
        selection.add_pattern_group("office_documents")
        
        target = BackupTarget(selection)
        assert target.validate()
        assert "*.doc" in target.selection.include_patterns
        assert "*.pdf" in target.selection.include_patterns

