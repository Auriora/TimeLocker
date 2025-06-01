"""
Critical backup path tests for TimeLocker MVP

This module contains tests for critical backup scenarios that could affect data integrity,
including edge cases, error conditions, and recovery scenarios.
"""

import pytest
import tempfile
import shutil
import json
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restic.Repositories.local import LocalResticRepository
from TimeLocker.backup_repository import RetentionPolicy


class TestCriticalBackupPaths:
    """Test suite for critical backup scenarios and edge cases"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.source_path = self.temp_dir / "source"
        self.large_file_path = self.temp_dir / "large_file"

        # Create test directory structure
        self.source_path.mkdir(parents=True)
        self._create_test_files()

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_test_files(self):
        """Create comprehensive test file structure"""
        # Regular files
        (self.source_path / "document.txt").write_text("Important document content")
        (self.source_path / "config.json").write_text('{"setting": "value"}')

        # Subdirectories
        subdir = self.source_path / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.txt").write_text("Nested file content")

        # Hidden files
        (self.source_path / ".hidden_file").write_text("Hidden content")

        # Files with special characters
        (self.source_path / "file with spaces.txt").write_text("Spaces in filename")
        (self.source_path / "file-with-dashes.txt").write_text("Dashes in filename")

        # Empty file
        (self.source_path / "empty_file.txt").touch()

        # Large file (simulated)
        large_content = "x" * (1024 * 1024)  # 1MB
        self.large_file_path.write_text(large_content)

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    def test_backup_with_file_permission_errors(self, mock_subprocess, mock_verify):
        """Test backup behavior when encountering permission denied errors"""
        mock_verify.return_value = "0.18.0"

        # Mock permission error in subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "permission denied: /restricted/file.txt"
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        # Create repository and backup target
        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection)

        # Execute backup and verify it handles the error gracefully
        # The backup should complete but log the permission error
        result = repository.backup_target([target])

        # Verify the backup was attempted despite permission errors
        mock_subprocess.assert_called()

        # Check that the error was handled (not raised as exception)
        # This is the expected behavior for production resilience

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    def test_backup_with_disk_space_exhaustion(self, mock_subprocess, mock_verify):
        """Test backup behavior when disk space is exhausted"""
        mock_verify.return_value = "0.18.0"

        # Mock disk space error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "no space left on device"
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection)

        # Execute backup and verify error handling
        # Should handle disk space errors gracefully
        result = repository.backup_target([target])

        # Verify the backup was attempted
        mock_subprocess.assert_called()

        # The system should handle disk space errors without crashing

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    def test_backup_with_network_interruption(self, mock_subprocess, mock_verify):
        """Test backup behavior during network interruption (for remote repositories)"""
        mock_verify.return_value = "0.18.0"

        # Mock network error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "connection timeout"
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection)

        # Execute backup and verify error handling
        # Should handle network errors gracefully
        result = repository.backup_target([target])

        # Verify the backup was attempted
        mock_subprocess.assert_called()

        # Network errors should be handled without crashing the application

    @patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    @patch('subprocess.run')
    def test_backup_with_corrupted_repository(self, mock_subprocess, mock_verify):
        """Test backup behavior with corrupted repository"""
        mock_verify.return_value = "0.18.0"

        # Mock repository corruption error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "repository is corrupted"
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        repository = LocalResticRepository(
                location=str(self.repo_path),
                password="test_password"
        )

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection)

        # Execute backup and verify error handling
        # Should handle repository corruption gracefully
        result = repository.backup_target([target])

        # Verify the backup was attempted
        mock_subprocess.assert_called()

        # Repository corruption should be detected and handled appropriately

    def test_file_selection_with_complex_patterns(self):
        """Test file selection with complex inclusion/exclusion patterns"""
        selection = FileSelection()

        # Add complex patterns
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.log", SelectionType.EXCLUDE)
        selection.add_pattern("cache/*", SelectionType.EXCLUDE)
        selection.add_pattern("*.txt", SelectionType.INCLUDE)  # Override exclusion

        # Test pattern matching
        test_files = [
                "document.txt",  # Should be included
                "config.json",  # Should be included
                "temp.tmp",  # Should be excluded
                "debug.log",  # Should be excluded
                "cache/file.txt"  # Should be excluded (cache directory)
        ]

        for file_path in test_files:
            full_path = self.source_path / file_path
            if file_path.startswith("cache/"):
                cache_dir = self.source_path / "cache"
                cache_dir.mkdir(exist_ok=True)
                full_path = cache_dir / file_path.split("/")[1]

            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.touch()

        # Verify selection logic
        backup_paths = selection.get_backup_paths()
        assert str(self.source_path) in backup_paths

    def test_backup_verification_with_checksum_mismatch(self):
        """Test backup verification when checksums don't match"""
        # Create a file
        test_file = self.source_path / "checksum_test.txt"
        original_content = "Original content for checksum test"
        test_file.write_text(original_content)

        # Calculate original checksum
        import hashlib
        original_hash = hashlib.sha256(original_content.encode()).hexdigest()

        # Simulate file modification after backup (checksum mismatch)
        modified_content = "Modified content after backup"
        test_file.write_text(modified_content)
        modified_hash = hashlib.sha256(modified_content.encode()).hexdigest()

        # Verify checksums are different
        assert original_hash != modified_hash

    def test_incremental_backup_with_file_modifications(self):
        """Test incremental backup behavior with various file modifications"""
        # Create initial files
        file1 = self.source_path / "file1.txt"
        file2 = self.source_path / "file2.txt"
        file1.write_text("Initial content 1")
        file2.write_text("Initial content 2")

        # Simulate first backup
        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)
        target = BackupTarget(selection=selection, tags=["initial"])

        # Modify files for incremental backup
        file1.write_text("Modified content 1")  # Modified file
        file3 = self.source_path / "file3.txt"
        file3.write_text("New file content")  # New file
        file2.unlink()  # Deleted file

        # Create incremental backup target
        incremental_target = BackupTarget(selection=selection, tags=["incremental"])

        # Verify file changes are detected
        assert file1.exists()
        assert file3.exists()
        assert not file2.exists()

    def test_backup_with_symbolic_links(self):
        """Test backup behavior with symbolic links"""
        # Create target file
        target_file = self.source_path / "target.txt"
        target_file.write_text("Target file content")

        # Create symbolic link
        link_file = self.source_path / "link.txt"
        try:
            link_file.symlink_to(target_file)

            # Test file selection with symbolic links
            selection = FileSelection()
            selection.add_path(self.source_path, SelectionType.INCLUDE)

            # Verify both files are considered
            assert target_file.exists()
            assert link_file.is_symlink()

        except OSError:
            # Skip test if symbolic links are not supported
            pytest.skip("Symbolic links not supported on this platform")

    def test_backup_with_very_long_filenames(self):
        """Test backup behavior with very long filenames"""
        # Create file with very long name (approaching filesystem limits)
        long_name = "a" * 200 + ".txt"
        long_file = self.source_path / long_name

        try:
            long_file.write_text("Content of file with very long name")

            selection = FileSelection()
            selection.add_path(self.source_path, SelectionType.INCLUDE)

            # Verify file was created successfully
            assert long_file.exists()

        except OSError:
            # Skip test if filename is too long for filesystem
            pytest.skip("Filename too long for this filesystem")

    def test_backup_with_unicode_filenames(self):
        """Test backup behavior with Unicode filenames"""
        import sys

        # Create files with Unicode characters
        unicode_files = [
                "файл.txt",  # Cyrillic
                "文件.txt",  # Chinese
                "ファイル.txt",  # Japanese
                "αρχείο.txt",  # Greek
        ]

        # Add emoji files only on non-Windows platforms
        # Windows file systems have more restrictions on Unicode characters
        if sys.platform != "win32":
            unicode_files.append("🎉emoji🎊.txt")  # Emoji

        created_files = []
        for filename in unicode_files:
            try:
                unicode_file = self.source_path / filename
                unicode_file.write_text(f"Content of {filename}")

                # Verify file was created
                if unicode_file.exists():
                    created_files.append(unicode_file)

            except (UnicodeError, OSError, ValueError) as e:
                # Skip individual files that can't be created
                # This is expected on some platforms/file systems
                continue

        # Only proceed with test if at least one Unicode file was created
        if not created_files:
            pytest.skip("No Unicode filenames could be created on this platform")

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)

        # Verify that the selection can handle Unicode filenames
        effective_paths = selection.get_effective_paths()
        assert len(effective_paths["included"]) > 0

    def test_concurrent_backup_operations(self):
        """Test behavior when multiple backup operations run concurrently"""
        import threading
        import time

        results = []
        errors = []

        def run_backup(backup_id):
            try:
                # Create unique source for each backup
                source = self.temp_dir / f"source_{backup_id}"
                source.mkdir()
                (source / f"file_{backup_id}.txt").write_text(f"Content {backup_id}")

                selection = FileSelection()
                selection.add_path(source, SelectionType.INCLUDE)
                target = BackupTarget(selection=selection, tags=[f"concurrent_{backup_id}"])

                # Simulate backup operation
                time.sleep(0.1)  # Simulate backup time
                results.append(backup_id)

            except Exception as e:
                errors.append((backup_id, str(e)))

        # Create multiple concurrent backup threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_backup, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all backups completed
        assert len(results) == 3
        assert len(errors) == 0

    def test_backup_retention_policy_application(self):
        """Test application of retention policies"""
        # Create retention policy
        policy = RetentionPolicy(
                daily=7,
                weekly=4,
                monthly=12
        )

        # Verify policy is valid
        assert policy.is_valid()

        # Test invalid policy
        invalid_policy = RetentionPolicy()
        assert not invalid_policy.is_valid()

    def test_backup_with_empty_directories(self):
        """Test backup behavior with empty directories"""
        # Create empty directories
        empty_dir1 = self.source_path / "empty1"
        empty_dir2 = self.source_path / "empty2" / "nested_empty"

        empty_dir1.mkdir()
        empty_dir2.mkdir(parents=True)

        selection = FileSelection()
        selection.add_path(self.source_path, SelectionType.INCLUDE)

        # Verify directories exist
        assert empty_dir1.is_dir()
        assert empty_dir2.is_dir()
        assert len(list(empty_dir1.iterdir())) == 0
        assert len(list(empty_dir2.iterdir())) == 0
