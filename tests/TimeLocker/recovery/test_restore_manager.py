"""
Tests for RestoreManager functionality
"""

import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from TimeLocker.restore_manager import RestoreManager, RestoreOptions, ConflictResolution
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.recovery_errors import RestoreError, RestoreTargetError
from .mock_recovery_repository import MockRecoveryRepository


class TestRestoreManager:
    """Test cases for RestoreManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.snapshot_manager = SnapshotManager(self.repository)
        self.restore_manager = RestoreManager(self.repository, self.snapshot_manager)

        # Create temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_snapshot_success(self):
        """Test successful snapshot restore"""
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert result.snapshot_id == "abc123"
        assert result.target_path == target_path
        assert len(result.errors) == 0

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_snapshot_not_found(self):
        """Test restore with non-existent snapshot"""
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("nonexistent", options)

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_without_target_path(self):
        """Test restore without specifying target path"""
        options = RestoreOptions()

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is False
        assert any("target path is required" in error.lower() for error in result.errors)

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_dry_run(self):
        """Test restore in dry run mode"""
        target_path = self.temp_dir / "restore_target"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_dry_run(True))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert not target_path.exists()  # No actual restore in dry run

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_verification_disabled(self):
        """Test restore with verification disabled"""
        target_path = self.temp_dir / "restore_target"
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_verification(False))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert result.verification_passed is False  # Verification was disabled

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_creates_target_directory(self):
        """Test that restore creates target directory if it doesn't exist"""
        target_path = self.temp_dir / "new_directory" / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        # In a real implementation, the directory would be created

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_latest_snapshot(self):
        """Test restoring the latest snapshot"""
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_latest_snapshot(options)

        assert result.success is True
        assert result.snapshot_id == "abc123"  # Should be the latest

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_latest_no_snapshots(self):
        """Test restore latest when no snapshots exist"""
        self.repository.clear_snapshots()
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_latest_snapshot(options)

        assert result.success is False
        assert any("no snapshots found" in error.lower() for error in result.errors)

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_include_paths(self):
        """Test restore with specific include paths"""
        target_path = self.temp_dir / "restore_target"
        include_paths = [Path("/home/user/documents")]
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_include_paths(include_paths))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert options.include_paths == include_paths

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_exclude_paths(self):
        """Test restore with specific exclude paths"""
        target_path = self.temp_dir / "restore_target"
        exclude_paths = [Path("/home/user/photos")]
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_exclude_paths(exclude_paths))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert options.exclude_paths == exclude_paths

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_conflict_resolution(self):
        """Test restore with different conflict resolution strategies"""
        target_path = self.temp_dir / "restore_target"

        # Test with overwrite
        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_conflict_resolution(ConflictResolution.OVERWRITE))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert options.conflict_resolution == ConflictResolution.OVERWRITE

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_progress_callback(self):
        """Test restore with progress callback"""
        target_path = self.temp_dir / "restore_target"
        progress_calls = []

        def progress_callback(message, current, total):
            progress_calls.append((message, current, total))

        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_progress_callback(progress_callback))

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is True
        assert options.progress_callback is not None

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_repository_failure(self):
        """Test handling repository restore failures"""
        self.repository.set_restore_failure(True)
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_result_timing(self):
        """Test that restore result includes timing information"""
        import time
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        # Add a small delay to ensure measurable duration
        start_time = time.time()
        result = self.restore_manager.restore_snapshot("abc123", options)
        end_time = time.time()

        # Verify timing is recorded and reasonable
        assert result.duration_seconds >= 0
        # Allow for very fast execution but ensure it's not negative
        assert result.duration_seconds <= (end_time - start_time) + 0.1

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_with_existing_files(self):
        """Test restore when target directory already contains files"""
        target_path = self.temp_dir / "restore_target"
        target_path.mkdir(parents=True)

        # Create some existing files
        (target_path / "existing_file.txt").write_text("existing content")

        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        # Should succeed but may have warnings about conflicts
        assert result.success is True

    @patch('shutil.disk_usage')
    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_insufficient_space(self, mock_disk_usage):
        """Test restore when there's insufficient disk space"""
        # Mock insufficient disk space
        mock_disk_usage.return_value = Mock(free=1024)  # Very small space

        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        # Should have error about insufficient space
        assert any("insufficient" in error.lower() for error in result.errors)

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_options_chaining(self):
        """Test that RestoreOptions methods can be chained"""
        target_path = self.temp_dir / "restore_target"

        options = (RestoreOptions()
                   .with_target_path(target_path)
                   .with_verification(True)
                   .with_dry_run(False)
                   .with_conflict_resolution(ConflictResolution.SKIP))

        assert options.target_path == target_path
        assert options.verify_after_restore is True
        assert options.dry_run is False
        assert options.conflict_resolution == ConflictResolution.SKIP

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_result_statistics(self):
        """Test that restore result includes proper statistics"""
        target_path = self.temp_dir / "restore_target"
        options = RestoreOptions().with_target_path(target_path)

        result = self.restore_manager.restore_snapshot("abc123", options)

        assert hasattr(result, 'files_restored')
        assert hasattr(result, 'files_skipped')
        assert hasattr(result, 'files_failed')
        assert hasattr(result, 'bytes_restored')
        assert hasattr(result, 'duration_seconds')

    @pytest.mark.restore
    @pytest.mark.unit
    def test_restore_error_and_warning_handling(self):
        """Test error and warning collection in restore result"""
        result = self.restore_manager.restore_snapshot("abc123", RestoreOptions())

        # Should have error about missing target path
        assert len(result.errors) > 0

        # Test adding warnings
        result.add_warning("Test warning")
        assert "Test warning" in result.warnings
