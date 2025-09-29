"""
Tests for backup operations functionality
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.restic.errors import RepositoryError


class TestBackupOperations:
    """Test cases for backup operations"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.source_path = self.temp_dir / "source"

        # Create source directory with test files
        self.source_path.mkdir(parents=True)
        (self.source_path / "file1.txt").write_text("Test content 1")
        (self.source_path / "file2.txt").write_text("Test content 2")
        (self.source_path / "subdir").mkdir()
        (self.source_path / "subdir" / "file3.txt").write_text("Test content 3")

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_to_restic_args(self, mock_verify):
        """Test FileSelection conversion to restic arguments"""
        mock_verify.return_value = "0.18.0"

        # Create file selection
        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.log", SelectionType.EXCLUDE)
        selection.add_path(self.source_path / "subdir", SelectionType.EXCLUDE)

        # Test backup paths
        backup_paths = selection.get_backup_paths()
        assert str(self.source_path) in backup_paths

        # Test exclude arguments
        exclude_args = selection.get_exclude_args()
        assert "--exclude" in exclude_args
        assert "*.tmp" in exclude_args
        assert "*.log" in exclude_args
        assert str(self.source_path / "subdir") in exclude_args

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_target_success(self, mock_subprocess, mock_verify):
        """Test successful backup operation"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "abc123def456",
                "files_new":        5,
                "files_changed":    2,
                "files_unmodified": 10,
                "data_added":       1024
        })
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Create repository and backup target
        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        target = BackupTarget(
                selection=selection,
                tags=["test", "automated"]
        )

        # Execute backup
        result = repository.backup_target([target])

        # Verify results
        assert result["message_type"] == "summary"
        assert result["snapshot_id"] == "abc123def456"
        assert result["files_new"] == 5
        assert result["files_changed"] == 2
        assert result["files_unmodified"] == 10
        assert result["data_added"] == 1024

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        command_list = call_args[0][0]

        # Check that restic backup command was built correctly
        assert "restic" in command_list[0]
        assert "backup" in command_list
        assert "--exclude" in command_list
        assert "*.tmp" in command_list
        assert "--tag" in command_list
        assert str(self.source_path) in command_list

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_target_with_multiple_targets(self, mock_subprocess, mock_verify):
        """Test backup with multiple targets"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "multi123",
                "files_new":        8,
                "files_changed":    3,
                "files_unmodified": 15,
                "data_added":       2048
        })
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Create repository
        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Create multiple targets
        selection1 = FileSelection()
        selection1.add_path(self.source_path, SelectionType.INCLUDE)
        selection1.add_pattern("*.tmp", SelectionType.EXCLUDE)

        selection2 = FileSelection()
        selection2.add_path(self.source_path / "subdir", SelectionType.INCLUDE)
        selection2.add_pattern("*.log", SelectionType.EXCLUDE)

        target1 = BackupTarget(
                selection=selection1,
                tags=["documents"]
        )

        target2 = BackupTarget(
                selection=selection2,
                tags=["subdirectory"]
        )

        # Execute backup with multiple targets
        result = repository.backup_target([target1, target2], tags=["multi-target"])

        # Verify results
        assert result["snapshot_id"] == "multi123"

        # Verify command included paths from both targets
        call_args = mock_subprocess.call_args
        command_list = call_args[0][0]

        assert str(self.source_path) in command_list
        assert str(self.source_path / "subdir") in command_list
        assert "*.tmp" in command_list
        assert "*.log" in command_list

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_target_no_targets(self, mock_verify):
        """Test backup with no targets raises error"""
        mock_verify.return_value = "0.18.0"

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Should raise error with empty targets list
        with pytest.raises(RepositoryError, match="At least one backup target must be specified"):
            repository.backup_target([])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_target_command_failure(self, mock_subprocess, mock_verify):
        """Test backup failure handling"""
        mock_verify.return_value = "0.18.0"

        # Mock failed backup
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(
                returncode=1,
                cmd=["restic", "backup"],
                stderr="Repository not found"
        )

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)

        target = BackupTarget(
                selection=selection
        )

        # Should raise RepositoryError
        with pytest.raises(RepositoryError, match="Backup failed"):
            repository.backup_target([target])

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_verification_success(self, mock_subprocess, mock_verify):
        """Test successful backup verification"""
        mock_verify.return_value = "0.18.0"

        # Mock successful verification
        mock_result = Mock()
        mock_result.stdout = "using temporary cache in /tmp/restic-check-cache-123\nno errors were found\n"
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Test verification without specific snapshot
        result = repository.verify_backup()
        assert result is True

        # Test verification with specific snapshot
        result = repository.verify_backup("abc123def456")
        assert result is True

        # Verify subprocess calls
        assert mock_subprocess.call_count == 2

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_verification_failure(self, mock_subprocess, mock_verify):
        """Test backup verification failure"""
        mock_verify.return_value = "0.18.0"

        # Mock failed verification
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(
                returncode=1,
                cmd=["restic", "check"],
                stderr="repository contains errors"
        )

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Verification should return False on failure
        result = repository.verify_backup()
        assert result is False

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_with_tags(self, mock_subprocess, mock_verify):
        """Test backup with tags"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "tagged123",
                "files_new":        3,
                "files_changed":    1,
                "files_unmodified": 5,
                "data_added":       512
        })
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)

        target = BackupTarget(
                selection=selection,
                tags=["important", "daily"]
        )

        # Execute backup with additional tags
        result = repository.backup_target([target], tags=["manual", "test"])

        # Verify command included all tags
        call_args = mock_subprocess.call_args
        command_list = call_args[0][0]

        # Should contain --tag parameter with combined tags
        tag_index = command_list.index("--tag")
        tag_value = command_list[tag_index + 1]

        # All tags should be included (sorted)
        expected_tags = sorted(["important", "daily", "manual", "test"])
        assert tag_value == ",".join(expected_tags)
