"""
Advanced Snapshot Service for TimeLocker

This service provides high-level snapshot operations with proper error handling,
validation, and integration with the service-oriented architecture.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import logging

from ..interfaces.data_models import SnapshotInfo, SnapshotResult, OperationStatus, SnapshotDiffResult
from ..backup_repository import BackupRepository
from ..interfaces.snapshot_interface import ISnapshotService
from ..interfaces.exceptions import TimeLockerInterfaceError
from .validation_service import ValidationService
from ..utils.performance_utils import PerformanceModule

logger = logging.getLogger(__name__)


@dataclass
class SnapshotSearchResult:
    """Result of snapshot search operation"""
    snapshot_id: str
    file_path: str
    match_type: str  # 'name', 'content', 'path'
    line_number: Optional[int] = None
    context: Optional[str] = None


class SnapshotService(ISnapshotService):
    """Advanced snapshot management service"""

    def __init__(self, validation_service: ValidationService, performance_module: PerformanceModule):
        self.validation_service = validation_service
        self.performance_module = performance_module
        self._mounted_snapshots: Dict[str, Path] = {}  # snapshot_id -> mount_path

    def get_snapshot_details(self, repository: BackupRepository, snapshot_id: str) -> SnapshotInfo:
        """
        Get detailed information about a specific snapshot
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to examine
            
        Returns:
            SnapshotInfo: Detailed snapshot information
            
        Raises:
            TimeLockerInterfaceError: If snapshot cannot be found or accessed
        """
        with self.performance_module.track_operation("get_snapshot_details"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id)

                # Get snapshot from repository
                snapshots = repository.list_snapshots()
                snapshot = next((s for s in snapshots if s.id.startswith(snapshot_id)), None)

                if not snapshot:
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id} not found in repository")

                # Get detailed stats
                stats = self._get_snapshot_stats(repository, snapshot)

                return SnapshotInfo(
                        id=snapshot.id,
                        timestamp=snapshot.timestamp,
                        paths=snapshot.paths,
                        tags=getattr(snapshot, 'tags', []),
                        hostname=getattr(snapshot, 'hostname', 'unknown'),
                        username=getattr(snapshot, 'username', 'unknown'),
                        size=stats.get('total_size', 0),
                        file_count=stats.get('file_count', 0),
                        directory_count=stats.get('directory_count', 0),
                        repository_name=repository.name if hasattr(repository, 'name') else 'unknown'
                )

            except Exception as e:
                logger.error(f"Failed to get snapshot details for {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to get snapshot details: {e}")

    def list_snapshot_contents(self, repository: BackupRepository, snapshot_id: str,
                               path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List contents of a snapshot
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to list
            path: Optional path within snapshot to list (defaults to root)
            
        Returns:
            List of file/directory information dictionaries
            
        Raises:
            TimeLockerInterfaceError: If snapshot cannot be accessed or listed
        """
        with self.performance_module.track_operation("list_snapshot_contents"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id)

                # Use restic ls command to list snapshot contents
                cmd = ['restic', '-r', repository.location(), 'ls', snapshot_id]
                if path:
                    cmd.append(path)

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode != 0:
                    raise TimeLockerInterfaceError(f"Failed to list snapshot contents: {result.stderr}")

                # Parse output into structured format
                contents = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Parse restic ls output format
                        parts = line.split()
                        if len(parts) >= 4:
                            contents.append({
                                    'type':        'file' if parts[0].startswith('-') else 'directory',
                                    'permissions': parts[0],
                                    'size':        int(parts[1]) if parts[1].isdigit() else 0,
                                    'modified':    ' '.join(parts[2:4]),
                                    'path':        ' '.join(parts[4:]) if len(parts) > 4 else parts[-1]
                            })

                return contents

            except Exception as e:
                logger.error(f"Failed to list snapshot contents for {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to list snapshot contents: {e}")

    def mount_snapshot(self, repository: BackupRepository, snapshot_id: str,
                       mount_path: Path) -> SnapshotResult:
        """
        Mount a snapshot as a filesystem
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to mount
            mount_path: Path where to mount the snapshot
            
        Returns:
            SnapshotResult: Result of mount operation
            
        Raises:
            TimeLockerInterfaceError: If snapshot cannot be mounted
        """
        with self.performance_module.track_operation("mount_snapshot"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id)
                self.validation_service.validate_path(mount_path)

                # Check if mount path exists and is empty
                if mount_path.exists() and any(mount_path.iterdir()):
                    raise TimeLockerInterfaceError(f"Mount path {mount_path} is not empty")

                # Create mount path if it doesn't exist
                mount_path.mkdir(parents=True, exist_ok=True)

                # Check if snapshot is already mounted
                if snapshot_id in self._mounted_snapshots:
                    existing_mount = self._mounted_snapshots[snapshot_id]
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id} is already mounted at {existing_mount}")

                # Mount using restic mount command
                cmd = ['restic', '-r', repository.location(), 'mount', str(mount_path), '--snapshot-template', snapshot_id]

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                # Start mount process in background
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Give it a moment to start
                import time
                time.sleep(2)

                # Check if mount was successful
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    raise TimeLockerInterfaceError(f"Failed to mount snapshot: {stderr.decode()}")

                # Verify mount is accessible
                if not mount_path.exists() or not any(mount_path.iterdir()):
                    raise TimeLockerInterfaceError(f"Mount appears to have failed - {mount_path} is empty")

                # Track mounted snapshot
                self._mounted_snapshots[snapshot_id] = mount_path

                logger.info(f"Successfully mounted snapshot {snapshot_id} at {mount_path}")

                return SnapshotResult(
                        status=OperationStatus.SUCCESS,
                        snapshot_id=snapshot_id,
                        message=f"Snapshot mounted at {mount_path}",
                        details={'mount_path': str(mount_path), 'process_id': process.pid}
                )

            except Exception as e:
                logger.error(f"Failed to mount snapshot {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to mount snapshot: {e}")

    def unmount_snapshot(self, snapshot_id: str) -> SnapshotResult:
        """
        Unmount a previously mounted snapshot
        
        Args:
            snapshot_id: ID of the snapshot to unmount
            
        Returns:
            SnapshotResult: Result of unmount operation
            
        Raises:
            TimeLockerInterfaceError: If snapshot cannot be unmounted
        """
        with self.performance_module.track_operation("unmount_snapshot"):
            try:
                # Check if snapshot is mounted
                if snapshot_id not in self._mounted_snapshots:
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id} is not currently mounted")

                mount_path = self._mounted_snapshots[snapshot_id]

                # Unmount using fusermount
                cmd = ['fusermount', '-u', str(mount_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    # Try alternative unmount methods
                    cmd = ['umount', str(mount_path)]
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        raise TimeLockerInterfaceError(f"Failed to unmount snapshot: {result.stderr}")

                # Remove from tracking
                del self._mounted_snapshots[snapshot_id]

                logger.info(f"Successfully unmounted snapshot {snapshot_id} from {mount_path}")

                return SnapshotResult(
                        status=OperationStatus.SUCCESS,
                        snapshot_id=snapshot_id,
                        message=f"Snapshot unmounted from {mount_path}",
                        details={'mount_path': str(mount_path)}
                )

            except Exception as e:
                logger.error(f"Failed to unmount snapshot {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to unmount snapshot: {e}")

    def search_in_snapshot(self, repository: BackupRepository, snapshot_id: str,
                           pattern: str, search_type: str = 'name') -> List[SnapshotSearchResult]:
        """
        Search for files/content within a snapshot
        
        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to search
            pattern: Search pattern (glob for names, regex for content)
            search_type: Type of search ('name', 'content', 'path')
            
        Returns:
            List of search results
            
        Raises:
            TimeLockerInterfaceError: If search cannot be performed
        """
        with self.performance_module.track_operation("search_in_snapshot"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id)

                results = []

                if search_type == 'name':
                    # Search by filename using restic find
                    cmd = ['restic', '-r', repository.location(), 'find', pattern, '--snapshot', snapshot_id]

                    # Set environment for repository access
                    env = os.environ.copy()
                    if hasattr(repository, 'password'):
                        password = repository.password()
                        if password:
                            env['RESTIC_PASSWORD'] = password

                    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                results.append(SnapshotSearchResult(
                                        snapshot_id=snapshot_id,
                                        file_path=line,
                                        match_type='name'
                                ))

                elif search_type in ['content', 'path']:
                    # For content/path search, we need to mount and search
                    # This is a simplified implementation
                    logger.warning(f"Search type '{search_type}' requires mounting - not fully implemented")

                return results

            except Exception as e:
                logger.error(f"Failed to search in snapshot {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to search in snapshot: {e}")

    def forget_snapshot(self, repository: BackupRepository, snapshot_id: str) -> SnapshotResult:
        """
        Remove a specific snapshot from the repository

        Args:
            repository: Repository containing the snapshot
            snapshot_id: ID of the snapshot to remove

        Returns:
            SnapshotResult: Result of the forget operation

        Raises:
            TimeLockerInterfaceError: If snapshot cannot be found or removed
        """
        with self.performance_monitor.track_operation("forget_snapshot"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id)

                # Check if snapshot exists
                snapshots = repository.list_snapshots()
                snapshot = next((s for s in snapshots if s.id.startswith(snapshot_id)), None)

                if not snapshot:
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id} not found in repository")

                # Check if snapshot is currently mounted
                if snapshot_id in self._mounted_snapshots:
                    raise TimeLockerInterfaceError(f"Cannot remove mounted snapshot {snapshot_id}. Unmount it first.")

                # Use restic forget command to remove the snapshot
                cmd = ['restic', '-r', repository.location(), 'forget', snapshot.id]

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode != 0:
                    raise TimeLockerInterfaceError(f"Failed to remove snapshot: {result.stderr}")

                logger.info(f"Successfully removed snapshot {snapshot_id}")

                return SnapshotResult(
                        status=OperationStatus.SUCCESS,
                        snapshot_id=snapshot_id,
                        message=f"Snapshot {snapshot_id} removed successfully",
                        details={'removed_snapshot_id': snapshot.id}
                )

            except Exception as e:
                logger.error(f"Failed to remove snapshot {snapshot_id}: {e}")
                raise TimeLockerInterfaceError(f"Failed to remove snapshot: {e}")

    def diff_snapshots(self, repository: BackupRepository, snapshot_id1: str, snapshot_id2: str,
                       include_metadata: bool = False) -> SnapshotDiffResult:
        """
        Compare two snapshots and show differences

        Args:
            repository: Repository containing the snapshots
            snapshot_id1: ID of the first snapshot
            snapshot_id2: ID of the second snapshot
            include_metadata: Whether to include metadata changes

        Returns:
            SnapshotDiffResult: Detailed comparison results

        Raises:
            TimeLockerInterfaceError: If comparison cannot be performed
        """
        with self.performance_module.track_operation("diff_snapshots"):
            try:
                # Validate inputs
                self.validation_service.validate_snapshot_id(snapshot_id1)
                self.validation_service.validate_snapshot_id(snapshot_id2)

                # Verify both snapshots exist
                snapshots = repository.snapshots()
                snapshot1 = next((s for s in snapshots if s.id.startswith(snapshot_id1)), None)
                snapshot2 = next((s for s in snapshots if s.id.startswith(snapshot_id2)), None)

                if not snapshot1:
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id1} not found in repository")
                if not snapshot2:
                    raise TimeLockerInterfaceError(f"Snapshot {snapshot_id2} not found in repository")

                # Use restic diff command to compare snapshots
                cmd = ['restic', '-r', repository.location(), 'diff', snapshot1.id, snapshot2.id]

                if include_metadata:
                    cmd.append('--metadata')

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode != 0:
                    raise TimeLockerInterfaceError(f"Failed to compare snapshots: {result.stderr}")

                # Parse restic diff output
                diff_result = self._parse_diff_output(result.stdout)

                logger.info(f"Successfully compared snapshots {snapshot_id1} and {snapshot_id2}")

                return diff_result

            except Exception as e:
                logger.error(f"Failed to compare snapshots {snapshot_id1} and {snapshot_id2}: {e}")
                raise TimeLockerInterfaceError(f"Failed to compare snapshots: {e}")

    def search_across_snapshots(self, repository: BackupRepository, pattern: str,
                                search_type: str = 'name', host: Optional[str] = None,
                                tags: Optional[List[str]] = None) -> List[SnapshotSearchResult]:
        """
        Search for files/content across all snapshots in repository

        Args:
            repository: Repository to search in
            pattern: Search pattern (glob for names, regex for content)
            search_type: Type of search ('name', 'content', 'path')
            host: Optional host filter
            tags: Optional tag filters

        Returns:
            List of search results across all snapshots

        Raises:
            TimeLockerInterfaceError: If search cannot be performed
        """
        with self.performance_module.track_operation("search_across_snapshots"):
            try:
                results = []

                if search_type == 'name':
                    # Search by filename using restic find across all snapshots
                    cmd = ['restic', '-r', repository.location(), 'find', pattern]

                    # Add optional filters
                    if host:
                        cmd.extend(['--host', host])

                    if tags:
                        for tag in tags:
                            cmd.extend(['--tag', tag])

                    # Set environment for repository access
                    env = os.environ.copy()
                    if hasattr(repository, 'password'):
                        password = repository.password()
                        if password:
                            env['RESTIC_PASSWORD'] = password

                    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                    if result.returncode == 0:
                        # Parse output - restic find shows snapshot_id:path format
                        for line in result.stdout.strip().split('\n'):
                            if line and ':' in line:
                                try:
                                    snapshot_id, file_path = line.split(':', 1)
                                    results.append(SnapshotSearchResult(
                                            snapshot_id=snapshot_id.strip(),
                                            file_path=file_path.strip(),
                                            match_type='name'
                                    ))
                                except ValueError:
                                    # Skip malformed lines
                                    continue
                    elif result.returncode != 0 and result.stderr:
                        # Only raise error if there's actual stderr content
                        if "no matching files found" not in result.stderr.lower():
                            raise TimeLockerInterfaceError(f"Search failed: {result.stderr}")

                elif search_type in ['content', 'path']:
                    # For content/path search across all snapshots, we need to:
                    # 1. Get all snapshots
                    # 2. Search in each one individually
                    logger.info(f"Performing {search_type} search across all snapshots")

                    snapshots = repository.snapshots()
                    for snapshot in snapshots:
                        try:
                            snapshot_results = self.search_in_snapshot(
                                    repository, snapshot.id, pattern, search_type
                            )
                            results.extend(snapshot_results)
                        except Exception as e:
                            logger.warning(f"Failed to search in snapshot {snapshot.id}: {e}")
                            continue

                logger.info(f"Found {len(results)} matches for pattern '{pattern}' across all snapshots")
                return results

            except Exception as e:
                logger.error(f"Failed to search across snapshots: {e}")
                raise TimeLockerInterfaceError(f"Failed to search across snapshots: {e}")

    def _parse_diff_output(self, diff_output: str) -> SnapshotDiffResult:
        """Parse restic diff command output into structured result"""
        added_files = []
        removed_files = []
        modified_files = []
        unchanged_files = []
        size_changes = {}
        metadata_changes = {}

        lines = diff_output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse different types of changes
            if line.startswith('+'):
                # Added file
                file_path = line[1:].strip()
                added_files.append(file_path)
            elif line.startswith('-'):
                # Removed file
                file_path = line[1:].strip()
                removed_files.append(file_path)
            elif line.startswith('M'):
                # Modified file
                file_path = line[1:].strip()
                modified_files.append(file_path)
            elif line.startswith('T'):
                # Type change (treat as modified)
                file_path = line[1:].strip()
                modified_files.append(file_path)
            elif 'size' in line.lower() and '->' in line:
                # Size change information
                try:
                    parts = line.split()
                    if len(parts) >= 3:
                        file_path = parts[0]
                        # Extract size information if available
                        size_info = line.split('size')[1] if 'size' in line else ''
                        if '->' in size_info:
                            old_size, new_size = size_info.split('->')
                            size_changes[file_path] = {
                                    'old': int(old_size.strip().replace('B', '').replace(',', '')),
                                    'new': int(new_size.strip().replace('B', '').replace(',', ''))
                            }
                except (ValueError, IndexError):
                    # Skip if we can't parse size information
                    pass

        return SnapshotDiffResult(
                added_files=added_files,
                removed_files=removed_files,
                modified_files=modified_files,
                unchanged_files=unchanged_files,
                size_changes=size_changes,
                metadata_changes=metadata_changes
        )

    def _get_snapshot_stats(self, repository: BackupRepository, snapshot) -> Dict[str, Any]:
        """Get detailed statistics for a snapshot"""
        try:
            # This would typically call restic stats command
            # For now, return basic info
            return {
                    'total_size':      getattr(snapshot, 'size', 0),
                    'file_count':      0,  # Would be calculated from restic stats
                    'directory_count': 0,  # Would be calculated from restic stats
            }
        except Exception as e:
            logger.warning(f"Failed to get snapshot stats: {e}")
            return {'total_size': 0, 'file_count': 0, 'directory_count': 0}
