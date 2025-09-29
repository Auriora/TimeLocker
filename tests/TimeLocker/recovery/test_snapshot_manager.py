"""
Tests for SnapshotManager functionality
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from TimeLocker.snapshot_manager import SnapshotManager, SnapshotFilter
from TimeLocker.recovery_errors import SnapshotNotFoundError, RecoveryError
from .mock_recovery_repository import MockRecoveryRepository


class TestSnapshotManager:
    """Test cases for SnapshotManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.repository = MockRecoveryRepository()
        self.manager = SnapshotManager(self.repository)

    @pytest.mark.restore
    @pytest.mark.unit
    def test_list_snapshots_returns_all_snapshots(self):
        """Test that list_snapshots returns all available snapshots"""
        snapshots = self.manager.list_snapshots()

        assert len(snapshots) == 3
        snapshot_ids = [s.id for s in snapshots]
        assert "abc123" in snapshot_ids
        assert "def456" in snapshot_ids
        assert "ghi789" in snapshot_ids

    @pytest.mark.restore
    @pytest.mark.unit
    def test_list_snapshots_with_tag_filter(self):
        """Test filtering snapshots by tags"""
        filter_criteria = SnapshotFilter().with_tags(["full"])
        snapshots = self.manager.list_snapshots(filter_criteria)

        assert len(snapshots) == 2
        for snapshot in snapshots:
            assert "full" in snapshot.tags

    @pytest.mark.restore
    @pytest.mark.unit
    def test_list_snapshots_with_date_filter(self):
        """Test filtering snapshots by date range"""
        # Filter for recent snapshots (last 5 days)
        date_from = datetime.now() - timedelta(days=5)
        filter_criteria = SnapshotFilter().with_date_range(date_from=date_from)
        snapshots = self.manager.list_snapshots(filter_criteria)

        assert len(snapshots) == 2  # Should exclude the 7-day old snapshot
        for snapshot in snapshots:
            assert snapshot.timestamp >= date_from

    @pytest.mark.restore
    @pytest.mark.unit
    def test_list_snapshots_with_max_results(self):
        """Test limiting number of results"""
        filter_criteria = SnapshotFilter().with_max_results(2)
        snapshots = self.manager.list_snapshots(filter_criteria)

        assert len(snapshots) == 2

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_snapshot_by_id_exact_match(self):
        """Test retrieving snapshot by exact ID"""
        snapshot = self.manager.get_snapshot_by_id("abc123")

        assert snapshot.id == "abc123"
        assert "full" in snapshot.tags

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_snapshot_by_id_partial_match(self):
        """Test retrieving snapshot by partial ID"""
        snapshot = self.manager.get_snapshot_by_id("abc")

        assert snapshot.id == "abc123"

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_snapshot_by_id_not_found(self):
        """Test error when snapshot ID is not found"""
        with pytest.raises(SnapshotNotFoundError):
            self.manager.get_snapshot_by_id("nonexistent")

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_latest_snapshot(self):
        """Test retrieving the most recent snapshot"""
        latest = self.manager.get_latest_snapshot()

        assert latest is not None
        assert latest.id == "abc123"  # This should be the most recent

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_latest_snapshot_with_filter(self):
        """Test retrieving latest snapshot with filter"""
        filter_criteria = SnapshotFilter().with_tags(["incremental"])
        latest = self.manager.get_latest_snapshot(filter_criteria)

        assert latest is not None
        assert latest.id == "def456"
        assert "incremental" in latest.tags

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_latest_snapshot_no_snapshots(self):
        """Test getting latest snapshot when no snapshots exist"""
        self.repository.clear_snapshots()
        latest = self.manager.get_latest_snapshot()

        assert latest is None

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_snapshots_by_date(self):
        """Test getting snapshots near a specific date"""
        target_date = datetime.now() - timedelta(days=3)
        snapshots = self.manager.get_snapshots_by_date(target_date, tolerance_hours=48)

        assert len(snapshots) >= 1
        # Should include the snapshot from 3 days ago

    @pytest.mark.restore
    @pytest.mark.unit
    def test_snapshot_caching(self):
        """Test that snapshots are cached properly"""
        # First call should hit the repository
        snapshots1 = self.manager.list_snapshots()

        # Second call should use cache
        snapshots2 = self.manager.list_snapshots()

        assert len(snapshots1) == len(snapshots2)
        assert snapshots1[0].id == snapshots2[0].id

    @pytest.mark.restore
    @pytest.mark.unit
    def test_force_refresh_cache(self):
        """Test forcing cache refresh"""
        # Get initial snapshots
        snapshots1 = self.manager.list_snapshots()

        # Add a new snapshot to repository
        new_time = datetime.now()
        self.repository.add_test_snapshot("xyz999", new_time, [Path("/test")], ["test"])

        # Without force refresh, should get cached results
        snapshots2 = self.manager.list_snapshots()
        assert len(snapshots2) == len(snapshots1)

        # With force refresh, should get updated results
        snapshots3 = self.manager.list_snapshots(force_refresh=True)
        assert len(snapshots3) == len(snapshots1) + 1

    @pytest.mark.restore
    @pytest.mark.unit
    def test_get_snapshot_summary(self):
        """Test getting snapshot summary information"""
        snapshot = self.manager.get_snapshot_by_id("abc123")
        summary = self.manager.get_snapshot_summary(snapshot)

        assert summary["id"] == "abc123"
        assert "timestamp" in summary
        assert "paths" in summary
        assert "tags" in summary
        assert summary["repository"] == self.repository.location()

    @pytest.mark.restore
    @pytest.mark.unit
    def test_clear_cache(self):
        """Test clearing the snapshot cache"""
        # Load cache
        self.manager.list_snapshots()
        assert self.manager._cached_snapshots is not None

        # Clear cache
        self.manager.clear_cache()
        assert self.manager._cached_snapshots is None
        assert self.manager._cache_timestamp is None

    @pytest.mark.restore
    @pytest.mark.unit
    def test_list_snapshots_repository_error(self):
        """Test handling repository errors when listing snapshots"""
        self.repository.set_snapshots_failure(True)

        with pytest.raises(RecoveryError):
            self.manager.list_snapshots()

    @pytest.mark.restore
    @pytest.mark.unit
    def test_filter_by_paths(self):
        """Test filtering snapshots by paths"""
        filter_criteria = SnapshotFilter().with_paths([Path("/home/user/documents")])
        snapshots = self.manager.list_snapshots(filter_criteria)

        assert len(snapshots) >= 1
        for snapshot in snapshots:
            assert any(Path("/home/user/documents") in snapshot.paths for path in [Path("/home/user/documents")])

    @pytest.mark.restore
    @pytest.mark.unit
    def test_combined_filters(self):
        """Test using multiple filters together"""
        date_from = datetime.now() - timedelta(days=5)
        filter_criteria = (SnapshotFilter()
                           .with_tags(["documents"])
                           .with_date_range(date_from=date_from)
                           .with_max_results(1))

        snapshots = self.manager.list_snapshots(filter_criteria)

        assert len(snapshots) <= 1
        if snapshots:
            assert "documents" in snapshots[0].tags
            assert snapshots[0].timestamp >= date_from
