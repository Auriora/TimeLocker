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

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import logging

from TimeLocker.backup_repository import BackupRepository
from TimeLocker.backup_snapshot import BackupSnapshot
from TimeLocker.recovery_errors import SnapshotNotFoundError, RecoveryError

logger = logging.getLogger(__name__)


class SnapshotFilter:
    """Filter criteria for snapshot selection"""

    def __init__(self):
        self.tags: Optional[List[str]] = None
        self.date_from: Optional[datetime] = None
        self.date_to: Optional[datetime] = None
        self.paths: Optional[List[Path]] = None
        self.max_results: Optional[int] = None

    def with_tags(self, tags: List[str]) -> 'SnapshotFilter':
        """Filter by tags"""
        self.tags = tags
        return self

    def with_date_range(self, date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None) -> 'SnapshotFilter':
        """Filter by date range"""
        self.date_from = date_from
        self.date_to = date_to
        return self

    def with_paths(self, paths: List[Path]) -> 'SnapshotFilter':
        """Filter by paths contained in snapshot"""
        self.paths = paths
        return self

    def with_max_results(self, max_results: int) -> 'SnapshotFilter':
        """Limit number of results"""
        self.max_results = max_results
        return self


class SnapshotManager:
    """Manages snapshot listing, filtering, and selection operations"""

    def __init__(self, repository: BackupRepository):
        """
        Initialize SnapshotManager
        
        Args:
            repository: BackupRepository instance to work with
        """
        self.repository = repository
        self._cached_snapshots: Optional[List[BackupSnapshot]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def list_snapshots(self, filter_criteria: Optional[SnapshotFilter] = None,
                       force_refresh: bool = False) -> List[BackupSnapshot]:
        """
        List snapshots with optional filtering
        
        Args:
            filter_criteria: Optional filter to apply
            force_refresh: Force refresh of snapshot cache
            
        Returns:
            List of BackupSnapshot instances matching criteria
            
        Raises:
            RecoveryError: If unable to retrieve snapshots
        """
        try:
            # Check cache validity
            if (not force_refresh and self._cached_snapshots is not None and
                    self._cache_timestamp is not None and
                    datetime.now() - self._cache_timestamp < self._cache_ttl):
                snapshots = self._cached_snapshots
            else:
                # Refresh cache
                snapshots = self.repository.snapshots()
                self._cached_snapshots = snapshots
                self._cache_timestamp = datetime.now()
                logger.info(f"Retrieved {len(snapshots)} snapshots from repository")

            # Apply filters if provided
            if filter_criteria:
                snapshots = self._apply_filters(snapshots, filter_criteria)

            return snapshots

        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            raise RecoveryError(f"Failed to retrieve snapshots: {e}")

    def get_snapshot_by_id(self, snapshot_id: str) -> BackupSnapshot:
        """
        Get a specific snapshot by ID
        
        Args:
            snapshot_id: ID of the snapshot to retrieve
            
        Returns:
            BackupSnapshot instance
            
        Raises:
            SnapshotNotFoundError: If snapshot is not found
        """
        snapshots = self.list_snapshots()

        for snapshot in snapshots:
            if snapshot.id == snapshot_id or snapshot.id.startswith(snapshot_id):
                return snapshot

        raise SnapshotNotFoundError(f"Snapshot with ID '{snapshot_id}' not found")

    def get_latest_snapshot(self, filter_criteria: Optional[SnapshotFilter] = None) -> Optional[BackupSnapshot]:
        """
        Get the most recent snapshot
        
        Args:
            filter_criteria: Optional filter to apply before selecting latest
            
        Returns:
            Latest BackupSnapshot or None if no snapshots found
        """
        snapshots = self.list_snapshots(filter_criteria)

        if not snapshots:
            return None

        # Sort by timestamp descending and return first
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[0]

    def get_snapshots_by_date(self, target_date: datetime,
                              tolerance_hours: int = 24) -> List[BackupSnapshot]:
        """
        Get snapshots near a specific date
        
        Args:
            target_date: Target date to search around
            tolerance_hours: Hours of tolerance around target date
            
        Returns:
            List of snapshots within tolerance of target date
        """
        tolerance = timedelta(hours=tolerance_hours)
        filter_criteria = SnapshotFilter().with_date_range(
                target_date - tolerance,
                target_date + tolerance
        )

        return self.list_snapshots(filter_criteria)

    def _apply_filters(self, snapshots: List[BackupSnapshot],
                       filter_criteria: SnapshotFilter) -> List[BackupSnapshot]:
        """Apply filter criteria to snapshot list"""
        filtered = snapshots

        # Filter by tags
        if filter_criteria.tags:
            filtered = [s for s in filtered if any(tag in getattr(s, 'tags', [])
                                                   for tag in filter_criteria.tags)]

        # Filter by date range
        if filter_criteria.date_from:
            filtered = [s for s in filtered if s.timestamp >= filter_criteria.date_from]
        if filter_criteria.date_to:
            filtered = [s for s in filtered if s.timestamp <= filter_criteria.date_to]

        # Filter by paths
        if filter_criteria.paths:
            filtered = [s for s in filtered if any(path in s.paths
                                                   for path in filter_criteria.paths)]

        # Sort by timestamp descending (newest first)
        filtered = sorted(filtered, key=lambda s: s.timestamp, reverse=True)

        # Limit results
        if filter_criteria.max_results:
            filtered = filtered[:filter_criteria.max_results]

        return filtered

    def get_snapshot_summary(self, snapshot: BackupSnapshot) -> Dict[str, Any]:
        """
        Get detailed summary information for a snapshot
        
        Args:
            snapshot: Snapshot to summarize
            
        Returns:
            Dictionary with snapshot summary information
        """
        try:
            stats = snapshot.get_stats()
            return {
                    'id':         snapshot.id,
                    'timestamp':  snapshot.timestamp,
                    'paths':      [str(p) for p in snapshot.paths],
                    'tags':       getattr(snapshot, 'tags', []),
                    'size':       getattr(snapshot, 'size', 0),
                    'stats':      stats,
                    'repository': snapshot.repo.location()
            }
        except Exception as e:
            logger.warning(f"Failed to get complete summary for snapshot {snapshot.id}: {e}")
            return {
                    'id':        snapshot.id,
                    'timestamp': snapshot.timestamp,
                    'paths':     [str(p) for p in snapshot.paths],
                    'error':     str(e)
            }

    def clear_cache(self):
        """Clear the snapshot cache"""
        self._cached_snapshots = None
        self._cache_timestamp = None
        logger.debug("Snapshot cache cleared")
