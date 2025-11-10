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

"""
Integration tests for recovery operations enhancements.

Tests the integration between RestoreManager, SnapshotManager, and the new
recovery architecture components (RecoveryValidator, ProgressMonitor, SnapshotBrowser).
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from tempfile import TemporaryDirectory

from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager, RestoreOptions
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.snapshot_browser import SnapshotBrowser


class TestRecoveryIntegration:
    """Test integration between existing and new recovery components."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.uri = MagicMock(return_value="mock://repository")
        repo.location = MagicMock(return_value="/mock/repo")
        repo.is_repository_initialized = MagicMock(return_value=True)
        repo._password = "test_password"
        return repo
    
    @pytest.fixture
    def mock_snapshots(self):
        """Create mock snapshots."""
        snapshots = []
        for i in range(3):
            snapshot = Mock(spec=BackupSnapshot)
            snapshot.id = f"snapshot{i}"
            snapshot.timestamp = datetime(2024, 1, i + 1)
            snapshot.paths = [Path(f"/backup/path{i}")]
            snapshot.tags = [f"tag{i}"]
            snapshot.size = 1000 * (i + 1)
            snapshot.verify.return_value = True
            snapshot.get_stats.return_value = {
                'total_size': 1000 * (i + 1),
                'files_changed': 10 * (i + 1)
            }
            snapshot.repo = Mock()
            snapshot.repo.location.return_value = "/mock/repo"
            snapshots.append(snapshot)
        return snapshots
    
    @pytest.fixture
    def snapshot_manager(self, mock_repository, mock_snapshots):
        """Create a SnapshotManager with mocked data."""
        manager = SnapshotManager(mock_repository)
        mock_repository.snapshots.return_value = mock_snapshots
        return manager
    
    @pytest.fixture
    def recovery_validator(self, mock_repository, snapshot_manager):
        """Create a RecoveryValidator."""
        return RecoveryValidator(mock_repository, snapshot_manager)
    
    @pytest.fixture
    def snapshot_browser(self, mock_repository, snapshot_manager):
        """Create a SnapshotBrowser."""
        return SnapshotBrowser(mock_repository, snapshot_manager)
    
    def test_restore_manager_with_recovery_validator(
        self, 
        mock_repository, 
        snapshot_manager,
        recovery_validator,
        mock_snapshots
    ):
        """Test RestoreManager with RecoveryValidator integration."""
        # Create RestoreManager with recovery validator
        restore_manager = RestoreManager(
            mock_repository,
            snapshot_manager,
            recovery_validator=recovery_validator
        )
        
        # Verify enhanced mode is enabled
        assert restore_manager.is_enhanced_mode()
        assert restore_manager.get_recovery_validator() is recovery_validator
        
        # Mock snapshot restore
        mock_snapshots[0].restore.return_value = "Restore completed"
        
        with TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "restore_target"
            
            # Create restore options
            options = RestoreOptions()
            options.target_path = target_path
            options.create_target_directory = True
            options.verify_after_restore = True
            
            # Perform restore
            result = restore_manager.restore_snapshot("snapshot0", options)
            
            # Verify result
            assert result.success
            assert result.snapshot_id == "snapshot0"
    
    def test_restore_manager_backward_compatibility(
        self,
        mock_repository,
        snapshot_manager,
        mock_snapshots
    ):
        """Test RestoreManager maintains backward compatibility without new components."""
        # Create RestoreManager without recovery components
        restore_manager = RestoreManager(mock_repository, snapshot_manager)
        
        # Verify enhanced mode is disabled
        assert not restore_manager.is_enhanced_mode()
        assert restore_manager.get_recovery_validator() is None
        
        # Mock snapshot restore
        mock_snapshots[0].restore.return_value = "Restore completed"
        
        with TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "restore_target"
            
            # Create restore options
            options = RestoreOptions()
            options.target_path = target_path
            options.create_target_directory = True
            
            # Perform restore
            result = restore_manager.restore_snapshot("snapshot0", options)
            
            # Verify result
            assert result.success
            assert result.snapshot_id == "snapshot0"
    
    def test_snapshot_manager_with_browser(
        self,
        mock_repository,
        snapshot_manager,
        snapshot_browser,
        mock_snapshots
    ):
        """Test SnapshotManager with SnapshotBrowser integration."""
        # Set snapshot browser
        snapshot_manager.set_snapshot_browser(snapshot_browser)
        
        # Get recovery metadata
        metadata = snapshot_manager.get_recovery_metadata("snapshot0")
        
        # Verify metadata
        assert metadata['snapshot_id'] == "snapshot0"
        assert metadata['total_size'] == 1000
        assert metadata['file_count'] == 10
        assert 'browsable' in metadata
    
    def test_snapshot_manager_recovery_verification(
        self,
        mock_repository,
        snapshot_manager,
        mock_snapshots
    ):
        """Test snapshot verification for recovery operations."""
        # Verify snapshot
        result = snapshot_manager.verify_snapshot_for_recovery("snapshot0")
        
        # Check verification result
        assert 'verified' in result
        assert 'can_recover' in result
        assert 'issues' in result
        assert 'warnings' in result
        assert result['can_recover']
    
    def test_snapshot_manager_list_for_recovery(
        self,
        mock_repository,
        snapshot_manager,
        mock_snapshots
    ):
        """Test listing snapshots with recovery information."""
        # List snapshots for recovery
        recovery_snapshots = snapshot_manager.list_snapshots_for_recovery(
            include_metadata=True
        )
        
        # Verify results
        assert len(recovery_snapshots) == 3
        for snapshot_info in recovery_snapshots:
            assert 'id' in snapshot_info
            assert 'timestamp' in snapshot_info
            assert 'recovery_metadata' in snapshot_info
    
    def test_snapshot_manager_contents_summary(
        self,
        mock_repository,
        snapshot_manager,
        mock_snapshots
    ):
        """Test getting snapshot contents summary."""
        # Get contents summary
        summary = snapshot_manager.get_snapshot_contents_summary("snapshot0")
        
        # Verify summary
        assert 'id' in summary  # get_snapshot_summary uses 'id' not 'snapshot_id'
        assert 'timestamp' in summary
        assert 'content_summary' in summary
    
    def test_restore_manager_set_components(
        self,
        mock_repository,
        snapshot_manager,
        recovery_validator
    ):
        """Test setting recovery components after initialization."""
        # Create RestoreManager without components
        restore_manager = RestoreManager(mock_repository, snapshot_manager)
        assert not restore_manager.is_enhanced_mode()
        
        # Set recovery validator
        restore_manager.set_recovery_validator(recovery_validator)
        assert restore_manager.is_enhanced_mode()
        assert restore_manager.get_recovery_validator() is recovery_validator
        
        # Disable recovery validator
        restore_manager.set_recovery_validator(None)
        assert not restore_manager.is_enhanced_mode()
    
    def test_snapshot_manager_recovery_cache(
        self,
        mock_repository,
        snapshot_manager,
        mock_snapshots
    ):
        """Test recovery metadata caching."""
        # Get metadata (should cache)
        metadata1 = snapshot_manager.get_recovery_metadata("snapshot0")
        
        # Get metadata again (should use cache)
        metadata2 = snapshot_manager.get_recovery_metadata("snapshot0")
        
        # Verify same object returned
        assert metadata1 == metadata2
        
        # Clear cache
        snapshot_manager.clear_recovery_cache()
        
        # Get metadata again (should fetch fresh)
        metadata3 = snapshot_manager.get_recovery_metadata("snapshot0")
        assert metadata3 == metadata1  # Same content but fresh fetch


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
