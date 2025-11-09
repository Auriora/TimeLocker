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
Snapshot Browser for TimeLocker Recovery Operations

This module provides browsing and exploration capabilities for snapshot contents
with support for different backup tool formats, pagination, searching, and comparison.
"""

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from threading import Lock

from .backup_repository import BackupRepository
from .snapshot_manager import SnapshotManager
from .interfaces.recovery_models import (
    FileEntry,
    FileType,
    SnapshotListing,
    PaginationInfo,
    SelectionCriteria,
    SizeRange,
    DateRange
)
from .recovery_errors import SnapshotNotFoundError, RecoveryError
from .command_builder import CommandBuilder
from .restic.restic_command_definition import restic_command_def

logger = logging.getLogger(__name__)


class PaginationOptions:
    """
    Options for paginating large directory listings.
    
    Attributes:
        page: Page number (1-indexed)
        page_size: Number of entries per page
    """
    
    def __init__(self, page: int = 1, page_size: int = 100):
        """
        Initialize pagination options.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of entries per page
            
        Raises:
            ValueError: If page or page_size are invalid
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        
        self.page = page
        self.page_size = page_size


class SearchCriteria:
    """
    Criteria for searching files within snapshots.
    
    Attributes:
        name_pattern: Pattern to match against file names (supports wildcards)
        path_pattern: Pattern to match against full paths
        file_types: List of file types to include
        size_range: Optional size range filter
        date_range: Optional modification date range filter
        case_sensitive: Whether pattern matching is case-sensitive
    """
    
    def __init__(
        self,
        name_pattern: Optional[str] = None,
        path_pattern: Optional[str] = None,
        file_types: Optional[List[FileType]] = None,
        size_range: Optional[SizeRange] = None,
        date_range: Optional[DateRange] = None,
        case_sensitive: bool = False
    ):
        """Initialize search criteria."""
        self.name_pattern = name_pattern
        self.path_pattern = path_pattern
        self.file_types = file_types or []
        self.size_range = size_range
        self.date_range = date_range
        self.case_sensitive = case_sensitive


class FileMetadata:
    """
    Detailed metadata for a specific file in a snapshot.
    
    Attributes:
        file_entry: Basic file entry information
        inode: File inode number
        links: Number of hard links
        device_id: Device ID
        user: File owner username
        group: File group name
        extended_attributes: Dictionary of extended attributes
    """
    
    def __init__(
        self,
        file_entry: FileEntry,
        inode: Optional[int] = None,
        links: Optional[int] = None,
        device_id: Optional[int] = None,
        user: Optional[str] = None,
        group: Optional[str] = None,
        extended_attributes: Optional[Dict[str, str]] = None
    ):
        """Initialize file metadata."""
        self.file_entry = file_entry
        self.inode = inode
        self.links = links
        self.device_id = device_id
        self.user = user
        self.group = group
        self.extended_attributes = extended_attributes or {}


class SnapshotComparison:
    """
    Results of comparing multiple snapshots.
    
    Attributes:
        snapshot_ids: List of snapshot IDs being compared
        path: Path being compared
        added_files: Files added in later snapshots
        removed_files: Files removed in later snapshots
        modified_files: Files modified between snapshots
        unchanged_files: Files unchanged across snapshots
    """
    
    def __init__(
        self,
        snapshot_ids: List[str],
        path: str,
        added_files: List[FileEntry],
        removed_files: List[FileEntry],
        modified_files: List[Tuple[FileEntry, FileEntry]],
        unchanged_files: List[FileEntry]
    ):
        """Initialize snapshot comparison."""
        self.snapshot_ids = snapshot_ids
        self.path = path
        self.added_files = added_files
        self.removed_files = removed_files
        self.modified_files = modified_files
        self.unchanged_files = unchanged_files


class SnapshotBrowser:
    """
    Provides browsing and exploration capabilities for snapshot contents
    with support for different backup tool formats.
    
    This class enables users to explore snapshot file structures, search for
    specific files, compare versions across snapshots, and retrieve detailed
    file metadata. It supports lazy loading and pagination for efficient
    handling of large snapshots.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        snapshot_manager: Optional[SnapshotManager] = None
    ):
        """
        Initialize the SnapshotBrowser.
        
        Args:
            repository: BackupRepository instance for accessing snapshots
            snapshot_manager: Optional SnapshotManager instance
        """
        self.repository = repository
        self.snapshot_manager = snapshot_manager or SnapshotManager(repository)
        
        # Cache for snapshot contents to improve performance
        self._listing_cache: Dict[str, SnapshotListing] = {}
        self._metadata_cache: Dict[str, FileMetadata] = {}
        self._cache_lock = Lock()
        
        logger.info("SnapshotBrowser initialized")
    
    def list_snapshot_contents(
        self,
        snapshot_id: str,
        path: str = "/",
        pagination: Optional[PaginationOptions] = None
    ) -> SnapshotListing:
        """
        Lists files and directories in a snapshot path.
        
        This method provides browsing capabilities for snapshot contents with
        optional pagination for large directories.
        
        Args:
            snapshot_id: ID of the snapshot to browse
            path: Path within the snapshot to list (default: root)
            pagination: Optional pagination options for large listings
            
        Returns:
            SnapshotListing containing file entries and pagination info
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RecoveryError: For other browsing errors
        """
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Check cache
        cache_key = f"{snapshot_id}:{path}"
        with self._cache_lock:
            if cache_key in self._listing_cache and pagination is None:
                logger.debug(f"Returning cached listing for {cache_key}")
                return self._listing_cache[cache_key]
        
        try:
            # Use restic ls command to list snapshot contents
            entries = self._list_snapshot_path(snapshot_id, path)
            
            # Apply pagination if requested
            total_entries = len(entries)
            pagination_info = None
            
            if pagination:
                start_idx = (pagination.page - 1) * pagination.page_size
                end_idx = start_idx + pagination.page_size
                
                paginated_entries = entries[start_idx:end_idx]
                
                total_pages = (total_entries + pagination.page_size - 1) // pagination.page_size
                
                pagination_info = PaginationInfo(
                    current_page=pagination.page,
                    page_size=pagination.page_size,
                    total_pages=total_pages,
                    total_entries=total_entries,
                    has_next=pagination.page < total_pages,
                    has_previous=pagination.page > 1
                )
                
                entries = paginated_entries
            
            listing = SnapshotListing(
                path=path,
                entries=entries,
                total_entries=total_entries,
                pagination_info=pagination_info
            )
            
            # Cache the result (only cache non-paginated listings)
            if pagination is None:
                with self._cache_lock:
                    self._listing_cache[cache_key] = listing
            
            logger.info(f"Listed {len(entries)} entries from snapshot {snapshot_id} at path {path}")
            return listing
            
        except Exception as e:
            logger.error(f"Failed to list snapshot contents: {e}")
            raise RecoveryError(f"Failed to browse snapshot {snapshot_id}: {e}") from e
    
    def search_snapshot_files(
        self,
        snapshot_id: str,
        search_criteria: SearchCriteria
    ) -> List[FileEntry]:
        """
        Searches for files within a snapshot using patterns and filters.
        
        This method enables finding specific files across the entire snapshot
        using various search criteria including name patterns, file types,
        size ranges, and modification dates.
        
        Args:
            snapshot_id: ID of the snapshot to search
            search_criteria: Criteria for file selection
            
        Returns:
            List of FileEntry objects matching the criteria
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RecoveryError: For other search errors
        """
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        try:
            # Get all files from snapshot
            all_entries = self._list_snapshot_path(snapshot_id, "/", recursive=True)
            
            # Apply search filters
            matching_entries = self._apply_search_filters(all_entries, search_criteria)
            
            logger.info(
                f"Found {len(matching_entries)} files matching search criteria "
                f"in snapshot {snapshot_id}"
            )
            return matching_entries
            
        except Exception as e:
            logger.error(f"Failed to search snapshot: {e}")
            raise RecoveryError(f"Failed to search snapshot {snapshot_id}: {e}") from e
    
    def compare_snapshots(
        self,
        snapshot_ids: List[str],
        path: str = "/"
    ) -> SnapshotComparison:
        """
        Compares file versions across multiple snapshots.
        
        This method identifies files that have been added, removed, or modified
        between snapshots, enabling version comparison and change tracking.
        
        Args:
            snapshot_ids: List of snapshot IDs to compare (chronological order)
            path: Path within snapshots to compare (default: root)
            
        Returns:
            SnapshotComparison object with comparison results
            
        Raises:
            SnapshotNotFoundError: If any snapshot doesn't exist
            RecoveryError: For other comparison errors
            ValueError: If fewer than 2 snapshots provided
        """
        if len(snapshot_ids) < 2:
            raise ValueError("At least 2 snapshots required for comparison")
        
        # Validate all snapshots exist
        for snapshot_id in snapshot_ids:
            try:
                self.snapshot_manager.get_snapshot_by_id(snapshot_id)
            except Exception as e:
                logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
                raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        try:
            # Get file listings for all snapshots
            snapshot_listings = []
            for snapshot_id in snapshot_ids:
                entries = self._list_snapshot_path(snapshot_id, path, recursive=True)
                snapshot_listings.append(entries)
            
            # Compare snapshots
            comparison = self._compare_file_listings(
                snapshot_ids,
                path,
                snapshot_listings
            )
            
            logger.info(
                f"Compared {len(snapshot_ids)} snapshots: "
                f"{len(comparison.added_files)} added, "
                f"{len(comparison.removed_files)} removed, "
                f"{len(comparison.modified_files)} modified"
            )
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare snapshots: {e}")
            raise RecoveryError(f"Failed to compare snapshots: {e}") from e
    
    def get_file_metadata(
        self,
        snapshot_id: str,
        file_path: str
    ) -> FileMetadata:
        """
        Retrieves detailed metadata for a specific file.
        
        This method provides comprehensive information about a file including
        ownership, permissions, extended attributes, and other metadata.
        
        Args:
            snapshot_id: ID of the snapshot containing the file
            file_path: Path to the file within the snapshot
            
        Returns:
            FileMetadata object with detailed file information
            
        Raises:
            SnapshotNotFoundError: If the snapshot doesn't exist
            RecoveryError: If the file doesn't exist or metadata retrieval fails
        """
        # Validate snapshot exists
        try:
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise SnapshotNotFoundError(f"Snapshot {snapshot_id} not found") from e
        
        # Check cache
        cache_key = f"{snapshot_id}:{file_path}"
        with self._cache_lock:
            if cache_key in self._metadata_cache:
                logger.debug(f"Returning cached metadata for {cache_key}")
                return self._metadata_cache[cache_key]
        
        try:
            # Get file metadata using restic ls with long format
            metadata = self._get_file_metadata_from_snapshot(snapshot_id, file_path)
            
            # Cache the result
            with self._cache_lock:
                self._metadata_cache[cache_key] = metadata
            
            logger.debug(f"Retrieved metadata for {file_path} in snapshot {snapshot_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise RecoveryError(
                f"Failed to retrieve metadata for {file_path} in snapshot {snapshot_id}: {e}"
            ) from e
    
    def clear_cache(self) -> None:
        """Clear all cached snapshot listings and metadata."""
        with self._cache_lock:
            self._listing_cache.clear()
            self._metadata_cache.clear()
        logger.info("Snapshot browser cache cleared")
    
    def _list_snapshot_path(
        self,
        snapshot_id: str,
        path: str,
        recursive: bool = False
    ) -> List[FileEntry]:
        """
        List files in a snapshot path using restic ls command.
        
        Args:
            snapshot_id: Snapshot ID to list
            path: Path within snapshot
            recursive: Whether to list recursively
            
        Returns:
            List of FileEntry objects
        """
        try:
            # Build restic ls command
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", self.repository.uri())
            command = command.command("ls")
            
            if recursive:
                command = command.param("recursive")
            
            # Build command and add snapshot ID and path
            command_list = command.build()
            command_list.append(snapshot_id)
            if path and path != "/":
                command_list.append(path)
            
            # Execute command
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=self.repository.to_env(),
                check=True
            )
            
            # Parse JSON output
            entries = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        data = json.loads(line)
                        entry = self._parse_file_entry(data)
                        if entry:
                            entries.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON line: {e}")
                        continue
            
            return entries
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list snapshot path: {e.stderr}")
            raise RecoveryError(f"Failed to list snapshot contents: {e.stderr}") from e
        except Exception as e:
            logger.error(f"Failed to list snapshot path: {e}")
            raise
    
    def _parse_file_entry(self, data: Dict) -> Optional[FileEntry]:
        """
        Parse file entry from restic ls JSON output.
        
        Args:
            data: JSON data from restic ls
            
        Returns:
            FileEntry object or None if parsing fails
        """
        try:
            # Determine file type
            struct_type = data.get("struct_type", "")
            if struct_type == "node":
                node_type = data.get("type", "file")
                if node_type == "dir":
                    file_type = FileType.DIRECTORY
                elif node_type == "symlink":
                    file_type = FileType.SYMLINK
                else:
                    file_type = FileType.FILE
            else:
                # Default to file if type not specified
                file_type = FileType.FILE
            
            # Parse path and name
            full_path = data.get("path", "")
            name = data.get("name", Path(full_path).name)
            
            # Parse size
            size = data.get("size", 0)
            
            # Parse modification time
            mtime_str = data.get("mtime", "")
            if mtime_str:
                try:
                    modification_time = datetime.fromisoformat(
                        mtime_str.replace('Z', '+00:00')
                    )
                except ValueError:
                    modification_time = datetime.now()
            else:
                modification_time = datetime.now()
            
            # Parse permissions
            mode = data.get("mode", 0)
            permissions = self._format_permissions(mode)
            
            # Get checksum if available
            checksum = None
            if "content" in data and data["content"]:
                # Use first content ID as checksum
                checksum = data["content"][0] if isinstance(data["content"], list) else None
            
            return FileEntry(
                path=full_path,
                name=name,
                type=file_type,
                size=size,
                modification_time=modification_time,
                permissions=permissions,
                checksum=checksum
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse file entry: {e}")
            return None
    
    def _format_permissions(self, mode: int) -> str:
        """
        Format Unix file mode as permission string.
        
        Args:
            mode: Unix file mode integer
            
        Returns:
            Permission string (e.g., "rwxr-xr-x")
        """
        perms = []
        
        # Owner permissions
        perms.append('r' if mode & 0o400 else '-')
        perms.append('w' if mode & 0o200 else '-')
        perms.append('x' if mode & 0o100 else '-')
        
        # Group permissions
        perms.append('r' if mode & 0o040 else '-')
        perms.append('w' if mode & 0o020 else '-')
        perms.append('x' if mode & 0o010 else '-')
        
        # Other permissions
        perms.append('r' if mode & 0o004 else '-')
        perms.append('w' if mode & 0o002 else '-')
        perms.append('x' if mode & 0o001 else '-')
        
        return ''.join(perms)
    
    def _apply_search_filters(
        self,
        entries: List[FileEntry],
        criteria: SearchCriteria
    ) -> List[FileEntry]:
        """
        Apply search criteria filters to file entries.
        
        Args:
            entries: List of file entries to filter
            criteria: Search criteria to apply
            
        Returns:
            Filtered list of file entries
        """
        filtered = entries
        
        # Filter by name pattern
        if criteria.name_pattern:
            pattern = self._wildcard_to_regex(criteria.name_pattern)
            flags = 0 if criteria.case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            filtered = [e for e in filtered if regex.search(e.name)]
        
        # Filter by path pattern
        if criteria.path_pattern:
            pattern = self._wildcard_to_regex(criteria.path_pattern)
            flags = 0 if criteria.case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            filtered = [e for e in filtered if regex.search(e.path)]
        
        # Filter by file types
        if criteria.file_types:
            filtered = [e for e in filtered if e.type in criteria.file_types]
        
        # Filter by size range
        if criteria.size_range:
            if criteria.size_range.min_size is not None:
                filtered = [e for e in filtered if e.size >= criteria.size_range.min_size]
            if criteria.size_range.max_size is not None:
                filtered = [e for e in filtered if e.size <= criteria.size_range.max_size]
        
        # Filter by date range
        if criteria.date_range:
            if criteria.date_range.start_date is not None:
                filtered = [
                    e for e in filtered 
                    if e.modification_time >= criteria.date_range.start_date
                ]
            if criteria.date_range.end_date is not None:
                filtered = [
                    e for e in filtered 
                    if e.modification_time <= criteria.date_range.end_date
                ]
        
        return filtered
    
    def _wildcard_to_regex(self, pattern: str) -> str:
        """
        Convert wildcard pattern to regex pattern.
        
        Args:
            pattern: Wildcard pattern (* and ? supported)
            
        Returns:
            Regex pattern string
        """
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        # Convert wildcards to regex
        regex = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        return regex
    
    def _compare_file_listings(
        self,
        snapshot_ids: List[str],
        path: str,
        listings: List[List[FileEntry]]
    ) -> SnapshotComparison:
        """
        Compare file listings from multiple snapshots.
        
        Args:
            snapshot_ids: List of snapshot IDs
            path: Path being compared
            listings: List of file entry lists for each snapshot
            
        Returns:
            SnapshotComparison object
        """
        # Build file maps for each snapshot
        file_maps = []
        for entries in listings:
            file_map = {entry.path: entry for entry in entries}
            file_maps.append(file_map)
        
        # Compare first and last snapshot
        first_files = file_maps[0]
        last_files = file_maps[-1]
        
        added_files = []
        removed_files = []
        modified_files = []
        unchanged_files = []
        
        # Find added and modified files
        for path, last_entry in last_files.items():
            if path not in first_files:
                added_files.append(last_entry)
            else:
                first_entry = first_files[path]
                if self._files_differ(first_entry, last_entry):
                    modified_files.append((first_entry, last_entry))
                else:
                    unchanged_files.append(last_entry)
        
        # Find removed files
        for path, first_entry in first_files.items():
            if path not in last_files:
                removed_files.append(first_entry)
        
        return SnapshotComparison(
            snapshot_ids=snapshot_ids,
            path=path,
            added_files=added_files,
            removed_files=removed_files,
            modified_files=modified_files,
            unchanged_files=unchanged_files
        )
    
    def _files_differ(self, entry1: FileEntry, entry2: FileEntry) -> bool:
        """
        Check if two file entries represent different versions.
        
        Args:
            entry1: First file entry
            entry2: Second file entry
            
        Returns:
            True if files differ, False otherwise
        """
        # Compare by size and modification time
        if entry1.size != entry2.size:
            return True
        
        if entry1.modification_time != entry2.modification_time:
            return True
        
        # Compare checksums if available
        if entry1.checksum and entry2.checksum:
            return entry1.checksum != entry2.checksum
        
        return False
    
    def _get_file_metadata_from_snapshot(
        self,
        snapshot_id: str,
        file_path: str
    ) -> FileMetadata:
        """
        Get detailed file metadata from snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            file_path: Path to file
            
        Returns:
            FileMetadata object
        """
        # Get basic file entry
        entries = self._list_snapshot_path(snapshot_id, file_path, recursive=False)
        
        if not entries:
            raise RecoveryError(f"File not found: {file_path}")
        
        # Find matching entry
        file_entry = None
        for entry in entries:
            if entry.path == file_path or entry.path.endswith(file_path):
                file_entry = entry
                break
        
        if not file_entry:
            raise RecoveryError(f"File not found: {file_path}")
        
        # Create metadata object with basic information
        # Extended attributes would require additional restic commands
        metadata = FileMetadata(
            file_entry=file_entry,
            user=None,  # Not available from basic ls
            group=None  # Not available from basic ls
        )
        
        return metadata
