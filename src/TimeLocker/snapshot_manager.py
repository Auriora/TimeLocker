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

from .backup_repository import BackupRepository
from .backup_snapshot import BackupSnapshot
from .recovery_errors import SnapshotNotFoundError, RecoveryError

# Type hints for forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .snapshot_browser import SnapshotBrowser

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
    """
    Manages snapshot listing, filtering, and selection operations.
    
    This class provides comprehensive snapshot management capabilities including
    listing, filtering, and recovery-specific metadata retrieval. It integrates
    with the recovery operations architecture to support snapshot browsing and
    validation for recovery workflows.
    """

    def __init__(
        self, 
        repository: BackupRepository,
        snapshot_browser: Optional['SnapshotBrowser'] = None
    ):
        """
        Initialize SnapshotManager
        
        Args:
            repository: BackupRepository instance to work with
            snapshot_browser: Optional SnapshotBrowser for recovery operations
        """
        self.repository = repository
        self._cached_snapshots: Optional[List[BackupSnapshot]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
        
        # Recovery operations integration
        self.snapshot_browser = snapshot_browser
        self._recovery_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._recovery_cache_lock = None
        
        # Initialize lock for thread-safe cache access
        try:
            from threading import Lock
            self._recovery_cache_lock = Lock()
        except ImportError:
            pass

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
        if snapshot_id == "latest":
            snapshot = self.get_latest_snapshot()
            if snapshot is None:
                raise SnapshotNotFoundError("No snapshots are available")
            return snapshot

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
    
    def get_recovery_metadata(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Get recovery-specific metadata for a snapshot.
        
        This method retrieves detailed metadata needed for recovery operations
        including file counts, total size, and verification information.
        
        Args:
            snapshot_id: ID of the snapshot to get metadata for
            
        Returns:
            Dictionary with recovery-specific metadata
            
        Raises:
            SnapshotNotFoundError: If snapshot is not found
        """
        # Check cache first
        if self._recovery_cache_lock:
            with self._recovery_cache_lock:
                if snapshot_id in self._recovery_metadata_cache:
                    logger.debug(f"Returning cached recovery metadata for {snapshot_id}")
                    return self._recovery_metadata_cache[snapshot_id]
        
        try:
            # Get snapshot
            snapshot = self.get_snapshot_by_id(snapshot_id)
            
            # Get basic stats
            stats = snapshot.get_stats()
            
            # Build recovery metadata
            metadata = {
                'snapshot_id': snapshot_id,
                'timestamp': snapshot.timestamp,
                'paths': [str(p) for p in snapshot.paths],
                'tags': getattr(snapshot, 'tags', []),
                'total_size': stats.get('total_size', 0),
                'file_count': stats.get('files_changed', 0),
                'repository': snapshot.repo.location(),
                'hostname': getattr(snapshot, 'hostname', 'unknown'),
                'username': getattr(snapshot, 'username', 'unknown'),
                'verified': False,  # Will be updated by verification
                'browsable': self.snapshot_browser is not None
            }
            
            # Add browsing support info if available
            if self.snapshot_browser:
                try:
                    # Test if we can browse this snapshot
                    listing = self.snapshot_browser.list_snapshot_contents(
                        snapshot_id, 
                        path="/",
                        pagination=None
                    )
                    metadata['browsable'] = True
                    metadata['root_entry_count'] = listing.total_entries
                except Exception as e:
                    logger.warning(f"Snapshot browsing not available for {snapshot_id}: {e}")
                    metadata['browsable'] = False
            
            # Cache the metadata
            if self._recovery_cache_lock:
                with self._recovery_cache_lock:
                    self._recovery_metadata_cache[snapshot_id] = metadata
            
            logger.info(f"Retrieved recovery metadata for snapshot {snapshot_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get recovery metadata for {snapshot_id}: {e}")
            raise RecoveryError(f"Failed to retrieve recovery metadata: {e}") from e
    
    def verify_snapshot_for_recovery(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Verify that a snapshot is suitable for recovery operations.
        
        This method performs comprehensive checks to ensure the snapshot
        can be used for recovery, including integrity verification and
        accessibility checks.
        
        Args:
            snapshot_id: ID of the snapshot to verify
            
        Returns:
            Dictionary with verification results:
                - verified: Boolean indicating if snapshot is verified
                - issues: List of any issues found
                - warnings: List of warnings
                - can_recover: Boolean indicating if recovery is possible
        """
        result = {
            'verified': False,
            'issues': [],
            'warnings': [],
            'can_recover': True
        }
        
        try:
            # Get snapshot
            snapshot = self.get_snapshot_by_id(snapshot_id)
            
            # Verify snapshot integrity
            try:
                if hasattr(snapshot, 'verify') and callable(snapshot.verify):
                    if not snapshot.verify():
                        result['warnings'].append("Snapshot verification returned false")
                        result['verified'] = False
                    else:
                        result['verified'] = True
                else:
                    result['warnings'].append("Snapshot verification not available")
            except Exception as e:
                result['issues'].append(f"Verification failed: {str(e)}")
                result['verified'] = False
            
            # Check if snapshot has paths
            if not snapshot.paths:
                result['issues'].append("Snapshot has no paths")
                result['can_recover'] = False
            
            # Check if repository is accessible
            try:
                if not self.repository.is_repository_initialized():
                    result['issues'].append("Repository is not initialized")
                    result['can_recover'] = False
            except Exception as e:
                result['issues'].append(f"Repository check failed: {str(e)}")
                result['can_recover'] = False
            
            # Check if snapshot is too old (optional warning)
            age_days = (datetime.now() - snapshot.timestamp).days
            if age_days > 365:
                result['warnings'].append(
                    f"Snapshot is {age_days} days old - verify data is still relevant"
                )
            
            logger.info(
                f"Snapshot verification for {snapshot_id}: "
                f"verified={result['verified']}, can_recover={result['can_recover']}, "
                f"issues={len(result['issues'])}, warnings={len(result['warnings'])}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to verify snapshot {snapshot_id}: {e}")
            result['issues'].append(f"Verification error: {str(e)}")
            result['can_recover'] = False
            return result
    
    def list_snapshots_for_recovery(
        self, 
        filter_criteria: Optional[SnapshotFilter] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List snapshots with recovery-specific information.
        
        This method provides an enhanced snapshot listing that includes
        recovery metadata and verification status for each snapshot.
        
        Args:
            filter_criteria: Optional filter to apply
            include_metadata: Whether to include full recovery metadata
            
        Returns:
            List of dictionaries with snapshot and recovery information
        """
        try:
            # Get snapshots using standard listing
            snapshots = self.list_snapshots(filter_criteria)
            
            # Enhance with recovery information
            recovery_snapshots = []
            for snapshot in snapshots:
                snapshot_info = {
                    'id': snapshot.id,
                    'timestamp': snapshot.timestamp,
                    'paths': [str(p) for p in snapshot.paths],
                    'tags': getattr(snapshot, 'tags', [])
                }
                
                # Add recovery metadata if requested
                if include_metadata:
                    try:
                        metadata = self.get_recovery_metadata(snapshot.id)
                        snapshot_info['recovery_metadata'] = metadata
                    except Exception as e:
                        logger.warning(f"Failed to get recovery metadata for {snapshot.id}: {e}")
                        snapshot_info['recovery_metadata'] = None
                
                recovery_snapshots.append(snapshot_info)
            
            logger.info(f"Listed {len(recovery_snapshots)} snapshots for recovery")
            return recovery_snapshots
            
        except Exception as e:
            logger.error(f"Failed to list snapshots for recovery: {e}")
            raise RecoveryError(f"Failed to list recovery snapshots: {e}") from e
    
    def get_snapshot_contents_summary(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Get a summary of snapshot contents for recovery planning.
        
        This method provides a high-level overview of what's in the snapshot
        to help users plan recovery operations.
        
        Args:
            snapshot_id: ID of the snapshot to summarize
            
        Returns:
            Dictionary with content summary
        """
        try:
            # Get basic snapshot info
            snapshot = self.get_snapshot_by_id(snapshot_id)
            summary = self.get_snapshot_summary(snapshot)
            
            # Add recovery-specific content information if browser is available
            if self.snapshot_browser:
                try:
                    # Get root directory listing
                    listing = self.snapshot_browser.list_snapshot_contents(
                        snapshot_id,
                        path="/",
                        pagination=None
                    )
                    
                    # Count file types
                    file_count = sum(1 for e in listing.entries if e.type.value == "file")
                    dir_count = sum(1 for e in listing.entries if e.type.value == "directory")
                    symlink_count = sum(1 for e in listing.entries if e.type.value == "symlink")
                    
                    summary['content_summary'] = {
                        'total_entries': listing.total_entries,
                        'files': file_count,
                        'directories': dir_count,
                        'symlinks': symlink_count,
                        'browsable': True
                    }
                except Exception as e:
                    logger.warning(f"Failed to get content summary for {snapshot_id}: {e}")
                    summary['content_summary'] = {
                        'browsable': False,
                        'error': str(e)
                    }
            else:
                summary['content_summary'] = {
                    'browsable': False,
                    'message': 'Snapshot browser not available'
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get snapshot contents summary: {e}")
            raise RecoveryError(f"Failed to get contents summary: {e}") from e
    
    def set_snapshot_browser(self, browser: Optional['SnapshotBrowser']) -> None:
        """
        Set or update the snapshot browser for recovery operations.
        
        Args:
            browser: SnapshotBrowser instance or None to disable
        """
        self.snapshot_browser = browser
        logger.info(f"Snapshot browser {'enabled' if browser else 'disabled'}")
    
    def clear_recovery_cache(self) -> None:
        """Clear the recovery metadata cache."""
        if self._recovery_cache_lock:
            with self._recovery_cache_lock:
                self._recovery_metadata_cache.clear()
        else:
            self._recovery_metadata_cache.clear()
        logger.debug("Recovery metadata cache cleared")
