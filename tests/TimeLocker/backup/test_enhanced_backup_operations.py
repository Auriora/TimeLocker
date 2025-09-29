"""
Tests for enhanced backup operations functionality
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.backup_manager import BackupManager, BackupManagerError
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.restic.errors import RepositoryError


class TestEnhancedBackupOperations:
    """Test cases for enhanced backup operations"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.source_path = self.temp_dir / "source"

        # Create source directory with test files
        self.source_path.mkdir(parents=True)
        (self.source_path / "file1.txt").write_text("Test content 1")
        (self.source_path / "file2.log").write_text("Log content")
        (self.source_path / "file3.tmp").write_text("Temp content")
        (self.source_path / "document.pdf").write_text("PDF content")

        # Create subdirectory
        subdir = self.source_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested content")
        (subdir / "cache.tmp").write_text("Cache content")

        self.manager = BackupManager()

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_pattern_matching(self):
        """Test enhanced pattern matching in FileSelection"""
        selection = FileSelection()

        # Test pattern matching
        assert selection.matches_pattern("test.txt", {"*.txt"})
        assert selection.matches_pattern("/path/to/test.txt", {"*.txt"})
        assert not selection.matches_pattern("test.log", {"*.txt"})

        # Test multiple patterns
        patterns = {"*.txt", "*.log", "temp*"}
        assert selection.matches_pattern("file.txt", patterns)
        assert selection.matches_pattern("file.log", patterns)
        assert selection.matches_pattern("tempfile", patterns)
        assert not selection.matches_pattern("file.pdf", patterns)

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_should_include_file(self):
        """Test file inclusion logic"""
        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.log", SelectionType.EXCLUDE)

        # Test file inclusion/exclusion
        assert selection.should_include_file(self.source_path / "file1.txt")
        assert not selection.should_include_file(self.source_path / "file2.log")
        assert not selection.should_include_file(self.source_path / "file3.tmp")
        assert selection.should_include_file(self.source_path / "document.pdf")

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_effective_paths(self):
        """Test effective path resolution"""
        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        effective_paths = selection.get_effective_paths()

        # Check that included files are present
        included_files = [p.name for p in effective_paths["included"]]
        assert "file1.txt" in included_files
        assert "document.pdf" in included_files
        assert "nested.txt" in included_files

        # Check that excluded files are not present
        assert "file3.tmp" not in included_files
        assert "cache.tmp" not in included_files

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_estimate_backup_size(self):
        """Test backup size estimation"""
        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)

        stats = selection.estimate_backup_size()

        assert stats["total_size"] > 0
        assert stats["file_count"] > 0
        assert stats["directory_count"] >= 1

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_with_retry_success_first_attempt(self, mock_subprocess, mock_verify):
        """Test successful backup on first attempt"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "retry123",
                "files_new":        3,
                "files_changed":    0,
                "files_unmodified": 0,
                "data_added":       1024
        })
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["test"])

        # Execute backup with retry
        result = self.manager.execute_backup_with_retry(repository, [target])

        # Verify results
        assert result["snapshot_id"] == "retry123"
        assert mock_subprocess.call_count == 2  # backup + verification

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_with_retry_success_after_failure(self, mock_subprocess, mock_verify):
        """Test successful backup after initial failure"""
        mock_verify.return_value = "0.18.0"

        # Mock first attempt failure, second attempt success
        from subprocess import CalledProcessError

        def side_effect(*args, **kwargs):
            if mock_subprocess.call_count == 1:
                raise CalledProcessError(1, ["restic", "backup"], stderr="Temporary failure")
            else:
                mock_result = Mock()
                mock_result.stdout = json.dumps({
                        "message_type":     "summary",
                        "snapshot_id":      "retry456",
                        "files_new":        3,
                        "files_changed":    0,
                        "files_unmodified": 0,
                        "data_added":       1024
                })
                mock_result.returncode = 0
                return mock_result

        mock_subprocess.side_effect = side_effect

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["test"])

        # Execute backup with retry
        result = self.manager.execute_backup_with_retry(
                repository, [target], max_retries=2, retry_delay=0.1
        )

        # Verify results
        assert result["snapshot_id"] == "retry456"
        assert mock_subprocess.call_count >= 2

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_with_retry_all_attempts_fail(self, mock_subprocess, mock_verify):
        """Test backup failure after all retry attempts"""
        mock_verify.return_value = "0.18.0"

        # Mock all attempts failing
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(
                1, ["restic", "backup"], stderr="Persistent failure"
        )

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["test"])

        # Should raise BackupManagerError after all retries
        with pytest.raises(BackupManagerError, match="Backup failed after .* attempts"):
            self.manager.execute_backup_with_retry(
                    repository, [target], max_retries=2, retry_delay=0.1
            )

        assert mock_subprocess.call_count == 3  # Initial + 2 retries

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_create_full_backup(self, mock_subprocess, mock_verify):
        """Test full backup creation"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "full123",
                "files_new":        5,
                "files_changed":    0,
                "files_unmodified": 0,
                "data_added":       2048
        })
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["documents"])

        # Create full backup
        result = self.manager.create_full_backup(repository, [target], tags=["manual"])

        # Verify results
        assert result["snapshot_id"] == "full123"

        # Check that backup command included correct tags
        call_args = mock_subprocess.call_args_list[0]  # First call is the backup
        command_list = call_args[0][0]

        # Should contain full and manual tags
        tag_index = command_list.index("--tag")
        tag_value = command_list[tag_index + 1]
        assert "full" in tag_value
        assert "manual" in tag_value
        assert "documents" in tag_value

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_create_incremental_backup(self, mock_subprocess, mock_verify):
        """Test incremental backup creation"""
        mock_verify.return_value = "0.18.0"

        # Mock successful backup result
        mock_result = Mock()
        mock_result.stdout = json.dumps({
                "message_type":     "summary",
                "snapshot_id":      "incr123",
                "files_new":        1,
                "files_changed":    2,
                "files_unmodified": 10,
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
        target = BackupTarget(selection=selection, tags=["documents"])

        # Create incremental backup
        result = self.manager.create_incremental_backup(
                repository, [target], parent_snapshot_id="parent123", tags=["auto"]
        )

        # Verify results
        assert result["snapshot_id"] == "incr123"

        # Check that backup command included correct tags
        call_args = mock_subprocess.call_args_list[0]  # First call is the backup
        command_list = call_args[0][0]

        # Should contain incremental and parent tags
        tag_index = command_list.index("--tag")
        tag_value = command_list[tag_index + 1]
        assert "incremental" in tag_value
        assert "parent:parent123" in tag_value
        assert "auto" in tag_value
        assert "documents" in tag_value

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_comprehensive_verification_success(self, mock_subprocess, mock_verify):
        """Test comprehensive backup verification success"""
        mock_verify.return_value = "0.18.0"

        # Mock successful verification commands
        def subprocess_side_effect(*args, **kwargs):
            command = args[0]
            if "check" in command:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "no errors were found"
                return mock_result
            elif "stats" in command:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({
                        "total_size":       1024,
                        "total_file_count": 5
                })
                return mock_result
            elif "snapshots" in command:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps([{
                        "short_id": "test123",
                        "time":     "2023-01-01T00:00:00Z",
                        "paths":    ["/test/path"]
                }])
                return mock_result

        mock_subprocess.side_effect = subprocess_side_effect

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Test comprehensive verification
        result = repository.verify_backup_comprehensive("test123")

        # Verify results
        assert result["success"] is True
        assert "repository_structure" in result["checks_performed"]
        assert "statistics" in result["checks_performed"]
        assert "snapshot_integrity" in result["checks_performed"]
        assert "consistency" in result["checks_performed"]
        assert len(result["errors"]) == 0

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_comprehensive_verification_failure(self, mock_subprocess, mock_verify):
        """Test comprehensive backup verification failure"""
        mock_verify.return_value = "0.18.0"

        # Mock failed verification
        from subprocess import CalledProcessError
        mock_subprocess.side_effect = CalledProcessError(
                1, ["restic", "check"], stderr="Repository corrupted"
        )

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Test comprehensive verification
        result = repository.verify_backup_comprehensive("test123")

        # Verify results
        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "Basic repository check failed" in result["errors"]

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_comprehensive_verification_with_warnings(self, mock_subprocess, mock_verify):
        """Test comprehensive verification with warnings"""
        mock_verify.return_value = "0.18.0"

        # Mock mixed results - basic check passes, but stats fail
        def subprocess_side_effect(*args, **kwargs):
            command = args[0]
            if "check" in command and "--read-data" not in command:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "no errors were found"
                return mock_result
            elif "stats" in command:
                raise Exception("Stats unavailable")
            elif "snapshots" in command:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps([{
                        "short_id": "test123",
                        "time":     "2023-01-01T00:00:00Z",
                        "paths":    ["/test/path"]
                }])
                return mock_result
            elif "check" in command and "--read-data" in command:
                # Simulate timeout for data verification
                import subprocess
                raise subprocess.TimeoutExpired(command, 300)

        mock_subprocess.side_effect = subprocess_side_effect

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        # Test comprehensive verification
        result = repository.verify_backup_comprehensive("test123")

        # Verify results
        assert result["success"] is True  # Should still succeed despite warnings
        assert len(result["warnings"]) > 0
        assert any("Could not gather statistics" in w for w in result["warnings"])
        assert any("Data verification timed out" in w for w in result["warnings"])

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_backup_manager_verify_backup_integrity(self):
        """Test backup manager verification method"""
        # Mock repository with verify_backup method
        mock_repo = Mock()
        mock_repo.verify_backup.return_value = True

        # Test verification
        result = self.manager.verify_backup_integrity(mock_repo, "test123")
        assert result is True
        mock_repo.verify_backup.assert_called_once_with("test123")

        # Test with repository that doesn't have verify_backup method
        mock_repo_no_verify = Mock()
        del mock_repo_no_verify.verify_backup
        mock_repo_no_verify.check.return_value = True

        result = self.manager.verify_backup_integrity(mock_repo_no_verify)
        assert result is True
        mock_repo_no_verify.check.assert_called_once()

    @pytest.mark.backup
    @pytest.mark.filesystem
    @pytest.mark.unit
    def test_file_selection_validation_enhanced(self):
        """Test enhanced file selection validation"""
        selection = FileSelection()

        # Should raise error with no included paths
        with pytest.raises(ValueError, match="At least one folder must be included"):
            selection.validate()

        # Should pass with directory path
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        assert selection.validate() is True

        # Should pass with file that looks like directory (no extension)
        selection2 = FileSelection()
        selection2.add_path(Path("/some/directory"), SelectionType.INCLUDE)
        assert selection2.validate() is True
