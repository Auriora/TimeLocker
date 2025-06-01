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

import fnmatch
import logging
import os
import re
from enum import auto, Enum
from pathlib import Path
from typing import Dict, List, Set, Union, Optional
from functools import lru_cache

try:
    from .performance.profiler import profile_operation
    from .performance.metrics import start_operation_tracking, update_operation_tracking, complete_operation_tracking
except ImportError:
    # Fallback for when performance module is not available
    def profile_operation(name):
        def decorator(func):
            return func

        return decorator


    def start_operation_tracking(operation_id, operation_type, metadata=None):
        return None


    def update_operation_tracking(operation_id, files_processed=None, bytes_processed=None, errors_count=None, metadata=None):
        pass


    def complete_operation_tracking(operation_id):
        return None


class SelectionType(Enum):
    """Defines whether the selection is for inclusion or exclusion"""
    INCLUDE = auto()
    EXCLUDE = auto()


class PatternGroup:
    """Represents a named group of file patterns"""

    # Common pattern groups that can be reused
    COMMON_GROUPS = {
            "office_documents": [
                    "*.doc", "*.docx", "*.xls", "*.xlsx", "*.ppt", "*.pptx",
                    "*.odt", "*.ods", "*.odp", "*.pdf"
            ],
            "temporary_files":  [
                    "*.tmp", "*.temp", "~*", "*.bak", "*.swp", "*.cache",
                    "__pycache__/*", "*.pyc", "node_modules/*"
            ],
            "media_files":      [
                    "*.jpg", "*.jpeg", "*.png", "*.gif", "*.mp3", "*.mp4",
                    "*.avi", "*.mov", "*.wav"
            ],
            "source_code":      [
                    "*.py", "*.java", "*.cpp", "*.h", "*.js", "*.ts",
                    "*.html", "*.css", "*.sql"
            ]
    }

    def __init__(self, name: str, patterns: List[str]):
        """
        Initialize a pattern group
        
        Args:
            name: Name of the pattern group
            patterns: List of file patterns in the group
        """
        self.name = name
        self.patterns = set(patterns)

    @classmethod
    def get_common_group(cls, group_name: str) -> 'PatternGroup':
        """
        Get a predefined common pattern group
        
        Args:
            group_name: Name of the common group to retrieve
            
        Returns:
            PatternGroup instance for the requested group
            
        Raises:
            KeyError: If group_name is not found in COMMON_GROUPS
        """
        if group_name not in cls.COMMON_GROUPS:
            raise KeyError(f"Pattern group '{group_name}' not found in common groups")
        return cls(group_name, cls.COMMON_GROUPS[group_name])


class FileSelection:
    """
    Unified class for managing file selections for backup operations.
    Handles both inclusions and exclusions of files and directories.
    Optimized for performance with pattern caching and efficient algorithms.
    """

    def __init__(self):
        """Initialize empty file selection"""
        self._pattern_groups: Dict[str, PatternGroup] = {}  # Named pattern groups
        self._includes: Set[Path] = set()  # Explicit path includes
        self._excludes: Set[Path] = set()  # Explicit path excludes
        self._include_patterns: Set[str] = set()  # Pattern includes
        self._exclude_patterns: Set[str] = set()  # Pattern excludes

        # Performance optimization: cache compiled regex patterns
        self._compiled_include_patterns: Optional[List[re.Pattern]] = None
        self._compiled_exclude_patterns: Optional[List[re.Pattern]] = None
        self._patterns_dirty = True

    def add_path(self, path: Union[str, Path], selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Add a path to either includes or excludes
        
        Args:
            path: Path to add
            selection_type: Whether to include or exclude the path
        """
        path_obj = Path(path) if isinstance(path, str) else path
        target_set = self._includes if selection_type == SelectionType.INCLUDE else self._excludes
        target_set.add(path_obj)

    def remove_path(self, path: Union[str, Path], selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Remove a path from either includes or excludes
        
        Args:
            path: Path to remove
            selection_type: Whether to remove from includes or excludes
        """
        path_obj = Path(path) if isinstance(path, str) else path
        target_set = self._includes if selection_type == SelectionType.INCLUDE else self._excludes
        target_set.discard(path_obj)

    def add_pattern(self, pattern: str, selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Add a file pattern to either includes or excludes

        Args:
            pattern: File pattern to add (e.g., "*.txt")
            selection_type: Whether to include or exclude the pattern
        """
        target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
        target_set.add(pattern)
        self._patterns_dirty = True  # Mark patterns as needing recompilation

    def remove_pattern(self, pattern: str, selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Remove a file pattern from either includes or excludes

        Args:
            pattern: File pattern to remove
            selection_type: Whether to remove from includes or excludes
        """
        target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
        target_set.discard(pattern)
        self._patterns_dirty = True  # Mark patterns as needing recompilation

    def add_pattern_group(self, group: Union[PatternGroup, str], selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Add a pattern group or a common group by name

        Args:
            group: PatternGroup instance or name of a common group
            selection_type: Whether to include or exclude the patterns
        """
        if isinstance(group, str):
            group = PatternGroup.get_common_group(group)

        self._pattern_groups[group.name] = group
        target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
        target_set.update(group.patterns)
        self._patterns_dirty = True  # Mark patterns as needing recompilation

    def remove_pattern_group(self, group_name: str, selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Remove a pattern group

        Args:
            group_name: Name of the group to remove
            selection_type: Whether to remove from includes or excludes
        """
        if group_name in self._pattern_groups:
            group = self._pattern_groups[group_name]
            target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
            target_set.difference_update(group.patterns)
            del self._pattern_groups[group_name]
            self._patterns_dirty = True  # Mark patterns as needing recompilation

    def validate(self) -> bool:
        """
        Validate the selection configuration
        
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            ValueError: If no folders are included in the backup selection
        """

        # Check if path exists and is a directory, or if it looks like a directory path
        def is_directory_path(path: Path) -> bool:
            # If path exists, check if it's a directory
            if path.exists():
                return path.is_dir()
            # Otherwise check if it looks like a directory path (no file extension)
            return path.suffix == '' or path.name.endswith('/')

        has_folder = any(is_directory_path(path) for path in self._includes)
        if not has_folder:
            raise ValueError("At least one folder must be included in the backup selection")
        return True

    @property
    def includes(self) -> Set[Path]:
        """Get the set of included paths"""
        return self._includes.copy()

    @property
    def excludes(self) -> Set[Path]:
        """Get the set of excluded paths"""
        return self._excludes.copy()

    @property
    def include_patterns(self) -> Set[str]:
        """Get the set of inclusion patterns"""
        return self._include_patterns.copy()

    @property
    def exclude_patterns(self) -> Set[str]:
        """Get the set of exclusion patterns"""
        return self._exclude_patterns.copy()

    def to_restic_args(self) -> List[str]:
        """
        Convert file selection to restic command arguments

        Returns:
            List[str]: List of command line arguments for restic backup command
        """
        args = []

        # Add include paths (these are positional arguments for restic backup)
        for path in self._includes:
            args.append(str(path))

        # Add exclude patterns
        for pattern in self._exclude_patterns:
            args.extend(["--exclude", pattern])

        # Add exclude paths
        for path in self._excludes:
            args.extend(["--exclude", str(path)])

        # Add include patterns (if any - restic doesn't have explicit include patterns,
        # but we can use them to filter the included paths)
        # Note: Restic backup works by specifying paths to backup, then excluding patterns

        return args

    def get_backup_paths(self) -> List[str]:
        """
        Get the list of paths to backup (for restic positional arguments)

        Returns:
            List[str]: List of paths to include in backup
        """
        return [str(path) for path in self._includes]

    def get_exclude_args(self) -> List[str]:
        """
        Get exclude arguments for restic command

        Returns:
            List[str]: List of --exclude arguments
        """
        args = []

        # Add exclude patterns
        for pattern in self._exclude_patterns:
            args.extend(["--exclude", pattern])

        # Add exclude paths
        for path in self._excludes:
            args.extend(["--exclude", str(path)])

        return args

    def _compile_patterns(self):
        """Compile patterns to regex for better performance"""
        if not self._patterns_dirty:
            return

        def fnmatch_to_regex(pattern: str) -> re.Pattern:
            """Convert fnmatch pattern to compiled regex"""
            # Convert fnmatch pattern to regex pattern
            regex_pattern = fnmatch.translate(pattern)
            return re.compile(regex_pattern, re.IGNORECASE)

        self._compiled_include_patterns = [fnmatch_to_regex(p) for p in self._include_patterns]
        self._compiled_exclude_patterns = [fnmatch_to_regex(p) for p in self._exclude_patterns]
        self._patterns_dirty = False

    def matches_pattern(self, file_path: Union[str, Path], patterns: Set[str]) -> bool:
        """
        Check if a file path matches any of the given patterns (legacy method)

        Args:
            file_path: Path to check
            patterns: Set of patterns to match against

        Returns:
            bool: True if path matches any pattern
        """
        path_str = str(file_path)
        path_name = os.path.basename(path_str)

        for pattern in patterns:
            # Check both full path and filename
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path_name, pattern):
                return True
        return False

    def _matches_compiled_patterns(self, file_path: Union[str, Path], compiled_patterns: List[re.Pattern]) -> bool:
        """
        Check if a file path matches any compiled regex patterns (optimized)

        Args:
            file_path: Path to check
            compiled_patterns: List of compiled regex patterns

        Returns:
            bool: True if path matches any pattern
        """
        path_str = str(file_path)
        path_name = os.path.basename(path_str)

        for pattern in compiled_patterns:
            # Check both full path and filename
            if pattern.match(path_str) or pattern.match(path_name):
                return True
        return False

    def should_include_file(self, file_path: Union[str, Path]) -> bool:
        """
        Determine if a file should be included in the backup based on selection rules
        Optimized version using compiled patterns for better performance.

        Args:
            file_path: Path to evaluate

        Returns:
            bool: True if file should be included
        """
        # Ensure patterns are compiled
        self._compile_patterns()

        path_obj = Path(file_path)

        # Check if path is explicitly excluded
        if path_obj in self._excludes:
            return False

        # Check if path is under any excluded directory
        for exclude_path in self._excludes:
            try:
                path_obj.relative_to(exclude_path)
                return False  # Path is under an excluded directory
            except ValueError:
                continue

        # Check if path matches exclude patterns (optimized)
        if self._compiled_exclude_patterns and self._matches_compiled_patterns(file_path, self._compiled_exclude_patterns):
            return False

        # Check if path is explicitly included
        if path_obj in self._includes:
            return True

        # Check if path is under any included directory
        for include_path in self._includes:
            try:
                path_obj.relative_to(include_path)
                return True  # File is under an included directory
            except ValueError:
                continue

        # Check if path matches include patterns (if any) (optimized)
        if self._compiled_include_patterns:
            return self._matches_compiled_patterns(file_path, self._compiled_include_patterns)

        return False

    @profile_operation("get_effective_paths")
    def get_effective_paths(self) -> Dict[str, List[Path]]:
        """
        Get the effective paths that will be included/excluded after pattern resolution
        Optimized version with performance tracking.

        Returns:
            Dict with 'included' and 'excluded' lists of resolved paths
        """
        operation_id = f"get_effective_paths_{id(self)}"
        metrics = start_operation_tracking(operation_id, "get_effective_paths")

        result = {"included": [], "excluded": []}
        files_processed = 0

        try:
            # Start with explicitly included paths
            for path in self._includes:
                if path.exists():
                    if path.is_dir():
                        # Add all files in directory that match criteria
                        for root, dirs, files in os.walk(path):
                            # Optimize: skip directories that are explicitly excluded
                            root_path = Path(root)
                            if root_path in self._excludes:
                                dirs.clear()  # Don't recurse into excluded directories
                                continue

                            for file in files:
                                file_path = root_path / file
                                files_processed += 1
                                if self.should_include_file(file_path):
                                    result["included"].append(file_path)

                                # Update metrics periodically
                                if files_processed % 1000 == 0:
                                    update_operation_tracking(operation_id, files_processed=files_processed)
                    else:
                        # Single file
                        files_processed += 1
                        if self.should_include_file(path):
                            result["included"].append(path)

            # Add explicitly excluded paths
            result["excluded"] = list(self._excludes)

            update_operation_tracking(operation_id, files_processed=files_processed)
            return result

        finally:
            complete_operation_tracking(operation_id)

    @profile_operation("estimate_backup_size")
    def estimate_backup_size(self) -> Dict[str, int]:
        """
        Estimate the total size of files that would be backed up
        Optimized version with performance tracking and early termination.

        Returns:
            Dict with size statistics in bytes
        """
        operation_id = f"estimate_backup_size_{id(self)}"
        metrics = start_operation_tracking(operation_id, "estimate_backup_size")

        stats = {"total_size": 0, "file_count": 0, "directory_count": 0}
        visited_dirs = set()
        files_processed = 0

        try:
            # Start with explicitly included paths
            for path in self._includes:
                if path.exists():
                    if path.is_dir():
                        # Walk through directory and count files that would be included
                        for root, dirs, files in os.walk(path):
                            root_path = Path(root)

                            # Optimize: skip directories that are explicitly excluded
                            if root_path in self._excludes:
                                dirs.clear()  # Don't recurse into excluded directories
                                continue

                            # Count this directory if we haven't seen it
                            if root_path not in visited_dirs:
                                visited_dirs.add(root_path)
                                stats["directory_count"] += 1

                            # Check each file
                            for file in files:
                                file_path = root_path / file
                                files_processed += 1

                                if self.should_include_file(file_path):
                                    try:
                                        file_size = file_path.stat().st_size
                                        stats["total_size"] += file_size
                                        stats["file_count"] += 1

                                        # Update metrics with bytes processed
                                        update_operation_tracking(operation_id,
                                                                  files_processed=files_processed,
                                                                  bytes_processed=stats["total_size"])
                                    except (OSError, PermissionError):
                                        # Skip files we can't access
                                        continue

                                # Update metrics periodically
                                if files_processed % 1000 == 0:
                                    update_operation_tracking(operation_id, files_processed=files_processed)
                    else:
                        # Single file
                        files_processed += 1
                        if self.should_include_file(path):
                            try:
                                file_size = path.stat().st_size
                                stats["total_size"] += file_size
                                stats["file_count"] += 1
                                update_operation_tracking(operation_id,
                                                          files_processed=files_processed,
                                                          bytes_processed=stats["total_size"])
                            except (OSError, PermissionError):
                                continue

            return stats

        finally:
            complete_operation_tracking(operation_id)

    def __repr__(self) -> str:
        return (f"<FileSelection includes={self._includes}, "
                f"excludes={self._excludes}, "
                f"include_patterns={self._include_patterns}, "
                f"exclude_patterns={self._exclude_patterns}>")
