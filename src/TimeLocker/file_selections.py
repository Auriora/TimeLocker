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
from typing import Dict, List, Set, Union, Optional, Any
from functools import lru_cache

from .utils import (
    profile_operation,
    start_operation_tracking,
    update_operation_tracking,
    complete_operation_tracking
)
from .selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    SelectionConfig,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution,
    RuleMatch
)
from .pattern_engine import PatternEngine, CompiledPattern
from .precedence_resolver import PrecedenceResolver


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
            ],
            "sensitive_files": [
                    "*tax*", "*bank*", "*financial*", "*invoice*", "*receipt*", "*.qif", "*.ofx",
                    "*passport*", "*ssn*", "*social*security*", "*birth*certificate*", "*medical*",
                    "*.key", "*.pem", "*.p12", "*.pfx", "*password*", "*credential*", "*.keychain",
                    "*cookies*", "*history*", "*bookmarks*", "*login*data*", "*web*data*"
            ],
            "privacy_exclude": [
                    "*.tmp", "*.temp", "~*", "*.bak", "*.swp", "*.cache",
                    "__pycache__/*", "*.pyc", "node_modules/*",
                    "*.key", "*.pem", "*.p12", "*.pfx", "*password*", "*credential*",
                    "*cookies*", "*history*", "*login*data*", "*web*data*"
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

    def __init__(self, selection_config: Optional[SelectionConfig] = None, use_new_engine: bool = True):
        """
        Initialize file selection
        
        Args:
            selection_config: Optional SelectionConfig to initialize from
            use_new_engine: Whether to use the new pattern engine and precedence resolver (default: True)
        """
        self._pattern_groups: Dict[str, PatternGroup] = {}  # Named pattern groups
        self._includes: Set[Path] = set()  # Explicit path includes
        self._excludes: Set[Path] = set()  # Explicit path excludes
        self._include_patterns: Set[str] = set()  # Pattern includes
        self._exclude_patterns: Set[str] = set()  # Pattern excludes

        # New data model support
        self._include_pattern_rules: List[PatternRule] = []  # Advanced pattern rules for inclusion
        self._exclude_pattern_rules: List[PatternRule] = []  # Advanced pattern rules for exclusion
        self._precedence_config: PrecedenceConfig = PrecedenceConfig()  # Precedence configuration
        self._selection_config: Optional[SelectionConfig] = selection_config  # Full selection config

        # Performance optimization: cache compiled regex patterns (legacy)
        self._compiled_include_patterns: Optional[List[re.Pattern]] = None
        self._compiled_exclude_patterns: Optional[List[re.Pattern]] = None
        self._patterns_dirty = True
        
        # New architecture integration
        self._use_new_engine = use_new_engine
        self._pattern_engine: Optional[PatternEngine] = PatternEngine() if use_new_engine else None
        self._precedence_resolver: Optional[PrecedenceResolver] = PrecedenceResolver(self._precedence_config) if use_new_engine else None
        self._compiled_pattern_cache: Optional[Any] = None  # Cache for compiled patterns from new engine
        
        # Initialize from config if provided
        if selection_config:
            self._initialize_from_config(selection_config)

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
        
        # Also create a PatternRule for the new engine
        if self._use_new_engine:
            rule = PatternRule(
                pattern=pattern,
                syntax=PatternSyntax.GLOB,
                case_sensitive=False,
                applies_to=PathComponent.FULL_PATH,
                priority=100,
                metadata={}
            )
            target_list = self._include_pattern_rules if selection_type == SelectionType.INCLUDE else self._exclude_pattern_rules
            target_list.append(rule)
            self._compiled_pattern_cache = None  # Invalidate cache

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
        
        # Also remove from PatternRules for the new engine
        if self._use_new_engine:
            target_list = self._include_pattern_rules if selection_type == SelectionType.INCLUDE else self._exclude_pattern_rules
            # Remove all rules with matching pattern
            self._include_pattern_rules = [r for r in self._include_pattern_rules if r.pattern != pattern] if selection_type == SelectionType.INCLUDE else self._include_pattern_rules
            self._exclude_pattern_rules = [r for r in self._exclude_pattern_rules if r.pattern != pattern] if selection_type == SelectionType.EXCLUDE else self._exclude_pattern_rules
            self._compiled_pattern_cache = None  # Invalidate cache

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
        path_obj = Path(file_path)
        
        # Use new engine only if we have non-GLOB patterns or need advanced precedence
        use_new_engine = False
        if self._use_new_engine:
            # Check if we have any non-GLOB patterns that require the new engine
            for rule in self._include_pattern_rules + self._exclude_pattern_rules:
                if rule.syntax != PatternSyntax.GLOB:
                    use_new_engine = True
                    break
            
            # Check if precedence config is non-default (requires new engine)
            if not use_new_engine and self._precedence_config.default_strategy != PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE:
                use_new_engine = True
        
        if use_new_engine:
            return self._should_include_file_new_engine(path_obj)
        
        # Fall back to legacy implementation
        return self._should_include_file_legacy(path_obj)
    
    def _should_include_file_new_engine(self, path_obj: Path) -> bool:
        """
        Determine file inclusion using the new pattern engine and precedence resolver.
        
        Args:
            path_obj: Path to evaluate
            
        Returns:
            bool: True if file should be included
        """
        # Compile patterns if needed
        if self._compiled_pattern_cache is None and self._pattern_engine:
            try:
                self._compiled_pattern_cache = self._pattern_engine.compile_patterns(
                    self._include_pattern_rules + self._exclude_pattern_rules
                )
            except Exception as e:
                logging.warning(f"Failed to compile patterns with new engine: {e}. Falling back to legacy.")
                return self._should_include_file_legacy(path_obj)
        
        # Collect all matching rules
        include_matches: List[RuleMatch] = []
        exclude_matches: List[RuleMatch] = []
        
        # Check explicit paths first
        if path_obj in self._excludes:
            exclude_matches.append(RuleMatch(
                rule=PatternRule("", PatternSyntax.LITERAL, True, PathComponent.FULL_PATH, 200, {}),
                matched_component=str(path_obj),
                specificity=1.0,
                is_include=False
            ))
        
        if path_obj in self._includes:
            include_matches.append(RuleMatch(
                rule=PatternRule("", PatternSyntax.LITERAL, True, PathComponent.FULL_PATH, 200, {}),
                matched_component=str(path_obj),
                specificity=1.0,
                is_include=True
            ))
        
        # Check if path is under any excluded/included directory
        for exclude_path in self._excludes:
            try:
                path_obj.relative_to(exclude_path)
                exclude_matches.append(RuleMatch(
                    rule=PatternRule("", PatternSyntax.LITERAL, True, PathComponent.FULL_PATH, 150, {}),
                    matched_component=str(exclude_path),
                    specificity=0.8,
                    is_include=False
                ))
            except ValueError:
                continue
        
        for include_path in self._includes:
            try:
                path_obj.relative_to(include_path)
                include_matches.append(RuleMatch(
                    rule=PatternRule("", PatternSyntax.LITERAL, True, PathComponent.FULL_PATH, 150, {}),
                    matched_component=str(include_path),
                    specificity=0.8,
                    is_include=True
                ))
            except ValueError:
                continue
        
        # Check pattern rules using the pattern engine
        if self._pattern_engine and self._compiled_pattern_cache:
            # Match against all compiled patterns
            match_result = self._pattern_engine.match_path(path_obj, self._compiled_pattern_cache)
            
            if match_result.matched:
                # Determine which patterns matched and whether they're include or exclude
                for compiled_pattern in match_result.matching_patterns:
                    original_rule = compiled_pattern.original_rule
                    
                    # Determine if this is an include or exclude rule
                    is_include = original_rule in self._include_pattern_rules
                    
                    # Calculate specificity based on pattern type and path component
                    specificity = 0.5  # Base specificity for pattern matches
                    if original_rule.applies_to == PathComponent.FULL_PATH:
                        specificity = 0.6
                    elif original_rule.applies_to == PathComponent.FILENAME:
                        specificity = 0.5
                    elif original_rule.applies_to == PathComponent.DIRECTORY:
                        specificity = 0.4
                    
                    match_entry = RuleMatch(
                        rule=original_rule,
                        matched_component=str(path_obj),
                        specificity=specificity,
                        is_include=is_include
                    )
                    
                    if is_include:
                        include_matches.append(match_entry)
                    else:
                        exclude_matches.append(match_entry)
        
        # If no matches at all, file is not included
        if not include_matches and not exclude_matches:
            return False
        
        # If only includes, file is included
        if include_matches and not exclude_matches:
            return True
        
        # If only excludes, file is excluded
        if exclude_matches and not include_matches:
            return False
        
        # Resolve conflicts using precedence resolver
        if self._precedence_resolver:
            try:
                decision = self._precedence_resolver.resolve_selection_conflicts(
                    path_obj,
                    include_matches + exclude_matches
                )
                return decision.include
            except Exception as e:
                logging.warning(f"Precedence resolution failed: {e}. Using default strategy.")
        
        # Default: exclude wins over include
        return False
    
    def _should_include_file_legacy(self, path_obj: Path) -> bool:
        """
        Legacy implementation of file inclusion logic.
        
        Args:
            path_obj: Path to evaluate
            
        Returns:
            bool: True if file should be included
        """
        # Ensure patterns are compiled
        self._compile_patterns()

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
        if self._compiled_exclude_patterns and self._matches_compiled_patterns(path_obj, self._compiled_exclude_patterns):
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
            return self._matches_compiled_patterns(path_obj, self._compiled_include_patterns)

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

    def apply_privacy_exclusions(self, privacy_level: str = "medium") -> None:
        """
        Apply privacy-based exclusions to protect sensitive data
        
        Args:
            privacy_level: Level of privacy protection ("low", "medium", "high")
        """
        if privacy_level == "low":
            # Only exclude temporary files
            self.add_pattern_group("temporary_files", SelectionType.EXCLUDE)
        elif privacy_level == "medium":
            # Exclude temporary files and common privacy-sensitive patterns
            self.add_pattern_group("privacy_exclude", SelectionType.EXCLUDE)
        elif privacy_level == "high":
            # Exclude all sensitive file patterns
            self.add_pattern_group("sensitive_files", SelectionType.EXCLUDE)
            self.add_pattern_group("temporary_files", SelectionType.EXCLUDE)

    def get_privacy_analysis(self) -> Dict[str, Any]:
        """
        Analyze the current selection for privacy implications
        
        Returns:
            Dict containing privacy analysis results
        """
        analysis = {
            "sensitive_patterns_included": [],
            "privacy_recommendations": [],
            "estimated_sensitive_files": 0,
            "privacy_level": "unknown"
        }

        # Check if sensitive file patterns are excluded
        sensitive_excluded = False
        temp_excluded = False
        
        for pattern in self._exclude_patterns:
            if any(sens_pattern in pattern.lower() for sens_pattern in 
                   ["*password*", "*credential*", "*.key", "*cookies*", "*history*"]):
                sensitive_excluded = True
            if any(temp_pattern in pattern.lower() for temp_pattern in 
                   ["*.tmp", "*.temp", "*.cache", "*.bak"]):
                temp_excluded = True

        # Determine privacy level
        if sensitive_excluded and temp_excluded:
            analysis["privacy_level"] = "high"
        elif temp_excluded:
            analysis["privacy_level"] = "medium"
        else:
            analysis["privacy_level"] = "low"

        # Generate recommendations
        if not temp_excluded:
            analysis["privacy_recommendations"].append({
                "type": "exclude_temporary",
                "description": "Consider excluding temporary files to protect cached sensitive data",
                "action": "Add temporary file exclusion patterns"
            })

        if not sensitive_excluded:
            analysis["privacy_recommendations"].append({
                "type": "exclude_sensitive",
                "description": "Consider excluding sensitive files like credentials and browser data",
                "action": "Add sensitive file exclusion patterns"
            })

        return analysis

    def get_sensitive_file_count_estimate(self) -> int:
        """
        Estimate the number of potentially sensitive files in the selection
        
        Returns:
            int: Estimated count of sensitive files
        """
        sensitive_count = 0
        
        # Sample files to estimate sensitive file count
        for include_path in self._includes:
            if include_path.exists() and include_path.is_dir():
                file_count = 0
                for file_path in include_path.rglob("*"):
                    if file_path.is_file() and file_count < 1000:  # Limit sampling
                        filename = file_path.name.lower()
                        path_str = str(file_path).lower()
                        
                        # Check for sensitive patterns
                        sensitive_indicators = [
                            "password", "credential", "key", "certificate",
                            "cookies", "history", "login", "bank", "tax",
                            "financial", "medical", "passport", "ssn"
                        ]
                        
                        if any(indicator in filename or indicator in path_str 
                               for indicator in sensitive_indicators):
                            sensitive_count += 1
                        
                        file_count += 1

        return sensitive_count

    def _initialize_from_config(self, config: SelectionConfig) -> None:
        """
        Initialize file selection from a SelectionConfig
        
        Args:
            config: SelectionConfig to initialize from
        """
        # Set paths
        for path in config.include_paths:
            self.add_path(path, SelectionType.INCLUDE)
        for path in config.exclude_paths:
            self.add_path(path, SelectionType.EXCLUDE)
        
        # Set pattern rules
        self._include_pattern_rules = config.include_patterns.copy()
        self._exclude_pattern_rules = config.exclude_patterns.copy()
        
        # Convert pattern rules to legacy patterns for backward compatibility
        for rule in config.include_patterns:
            if rule.syntax == PatternSyntax.GLOB:
                self._include_patterns.add(rule.pattern)
        for rule in config.exclude_patterns:
            if rule.syntax == PatternSyntax.GLOB:
                self._exclude_patterns.add(rule.pattern)
        
        # Set precedence config
        self._precedence_config = config.precedence_config
        
        # Apply pattern groups
        for group_name in config.pattern_groups:
            try:
                self.add_pattern_group(group_name, SelectionType.INCLUDE)
            except KeyError:
                # Skip unknown pattern groups
                pass
        
        self._patterns_dirty = True

    def add_pattern_rule(self, rule: PatternRule, selection_type: SelectionType = SelectionType.INCLUDE) -> None:
        """
        Add a PatternRule to the selection
        
        Args:
            rule: PatternRule to add
            selection_type: Whether to include or exclude
        """
        target_list = self._include_pattern_rules if selection_type == SelectionType.INCLUDE else self._exclude_pattern_rules
        target_list.append(rule)
        
        # Also add to legacy patterns if it's a GLOB pattern for backward compatibility
        # But don't use add_pattern() to avoid creating duplicate PatternRules
        if rule.syntax == PatternSyntax.GLOB:
            target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
            target_set.add(rule.pattern)
        
        self._patterns_dirty = True
        self._compiled_pattern_cache = None

    def remove_pattern_rule(self, rule: PatternRule, selection_type: SelectionType = SelectionType.INCLUDE) -> None:
        """
        Remove a PatternRule from the selection
        
        Args:
            rule: PatternRule to remove
            selection_type: Whether to remove from includes or excludes
        """
        target_list = self._include_pattern_rules if selection_type == SelectionType.INCLUDE else self._exclude_pattern_rules
        if rule in target_list:
            target_list.remove(rule)
            
            # Also remove from legacy patterns if it's a GLOB pattern
            # But don't use remove_pattern() to avoid modifying PatternRules list while iterating
            if rule.syntax == PatternSyntax.GLOB:
                target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
                target_set.discard(rule.pattern)
            
            self._patterns_dirty = True
            self._compiled_pattern_cache = None

    def get_pattern_rules(self, selection_type: SelectionType = SelectionType.INCLUDE) -> List[PatternRule]:
        """
        Get the list of PatternRules
        
        Args:
            selection_type: Whether to get include or exclude rules
            
        Returns:
            List of PatternRules
        """
        return (self._include_pattern_rules if selection_type == SelectionType.INCLUDE 
                else self._exclude_pattern_rules).copy()

    def set_precedence_config(self, config: PrecedenceConfig) -> None:
        """
        Set the precedence configuration
        
        Args:
            config: PrecedenceConfig to set
        """
        self._precedence_config = config
        
        # Update precedence resolver if using new engine
        if self._use_new_engine and self._precedence_resolver:
            self._precedence_resolver.configure_precedence_rules(config)

    def get_precedence_config(self) -> PrecedenceConfig:
        """
        Get the current precedence configuration
        
        Returns:
            Current PrecedenceConfig
        """
        return self._precedence_config

    def to_selection_config(self) -> SelectionConfig:
        """
        Convert the current FileSelection to a SelectionConfig
        
        Returns:
            SelectionConfig representing the current selection
        """
        return SelectionConfig(
            include_paths=list(self._includes),
            exclude_paths=list(self._excludes),
            include_patterns=self._include_pattern_rules.copy(),
            exclude_patterns=self._exclude_pattern_rules.copy(),
            pattern_groups=list(self._pattern_groups.keys()),
            precedence_config=self._precedence_config,
            case_sensitive=False,  # Default value
            performance_hints={}
        )

    @classmethod
    def from_selection_config(cls, config: SelectionConfig) -> 'FileSelection':
        """
        Create a FileSelection from a SelectionConfig
        
        Args:
            config: SelectionConfig to create from
            
        Returns:
            New FileSelection instance
        """
        return cls(selection_config=config)

    def supports_pattern_syntax(self, syntax: PatternSyntax) -> bool:
        """
        Check if a pattern syntax is supported
        
        Args:
            syntax: PatternSyntax to check
            
        Returns:
            True if syntax is supported
        """
        # With new engine, support all syntaxes; legacy only supports GLOB and LITERAL
        if self._use_new_engine:
            return syntax in (PatternSyntax.GLOB, PatternSyntax.LITERAL, PatternSyntax.REGEX)
        return syntax in (PatternSyntax.GLOB, PatternSyntax.LITERAL)

    def get_supported_pattern_syntaxes(self) -> List[PatternSyntax]:
        """
        Get list of supported pattern syntaxes
        
        Returns:
            List of supported PatternSyntax values
        """
        if self._use_new_engine:
            return [PatternSyntax.GLOB, PatternSyntax.LITERAL, PatternSyntax.REGEX]
        return [PatternSyntax.GLOB, PatternSyntax.LITERAL]

    def enable_new_engine(self) -> None:
        """
        Enable the new pattern engine and precedence resolver.
        
        This method allows runtime switching to the new architecture.
        """
        if not self._use_new_engine:
            self._use_new_engine = True
            self._pattern_engine = PatternEngine()
            self._precedence_resolver = PrecedenceResolver(self._precedence_config)
            self._compiled_pattern_cache = None
            
            # Migrate existing patterns to pattern rules
            self._migrate_legacy_patterns_to_rules()
    
    def disable_new_engine(self) -> None:
        """
        Disable the new pattern engine and fall back to legacy implementation.
        
        This method allows runtime switching back to the legacy architecture.
        """
        if self._use_new_engine:
            self._use_new_engine = False
            self._pattern_engine = None
            self._precedence_resolver = None
            self._compiled_pattern_cache = None
    
    def is_using_new_engine(self) -> bool:
        """
        Check if the new pattern engine is enabled.
        
        Returns:
            True if using new engine, False if using legacy
        """
        return self._use_new_engine
    
    def _migrate_legacy_patterns_to_rules(self) -> None:
        """
        Migrate legacy pattern strings to PatternRule objects.
        
        This ensures backward compatibility when switching to the new engine.
        """
        # Migrate include patterns
        for pattern in self._include_patterns:
            # Check if rule already exists
            if not any(r.pattern == pattern and r.syntax == PatternSyntax.GLOB for r in self._include_pattern_rules):
                rule = PatternRule(
                    pattern=pattern,
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FULL_PATH,
                    priority=100,
                    metadata={"migrated_from_legacy": True}
                )
                self._include_pattern_rules.append(rule)
        
        # Migrate exclude patterns
        for pattern in self._exclude_patterns:
            # Check if rule already exists
            if not any(r.pattern == pattern and r.syntax == PatternSyntax.GLOB for r in self._exclude_pattern_rules):
                rule = PatternRule(
                    pattern=pattern,
                    syntax=PatternSyntax.GLOB,
                    case_sensitive=False,
                    applies_to=PathComponent.FULL_PATH,
                    priority=100,
                    metadata={"migrated_from_legacy": True}
                )
                self._exclude_pattern_rules.append(rule)
    
    def get_pattern_engine(self) -> Optional[PatternEngine]:
        """
        Get the pattern engine instance if using new architecture.
        
        Returns:
            PatternEngine instance or None if using legacy
        """
        return self._pattern_engine
    
    def get_precedence_resolver(self) -> Optional[PrecedenceResolver]:
        """
        Get the precedence resolver instance if using new architecture.
        
        Returns:
            PrecedenceResolver instance or None if using legacy
        """
        return self._precedence_resolver
    
    def apply_template(self, template_config: SelectionConfig, merge: bool = False) -> None:
        """
        Apply a selection template to this FileSelection.
        
        Args:
            template_config: SelectionConfig from a template
            merge: If True, merge with existing selection; if False, replace
        """
        if not merge:
            # Clear existing selection
            self._includes.clear()
            self._excludes.clear()
            self._include_patterns.clear()
            self._exclude_patterns.clear()
            self._include_pattern_rules.clear()
            self._exclude_pattern_rules.clear()
            self._pattern_groups.clear()
        
        # Apply template configuration
        for path in template_config.include_paths:
            self.add_path(path, SelectionType.INCLUDE)
        for path in template_config.exclude_paths:
            self.add_path(path, SelectionType.EXCLUDE)
        
        for rule in template_config.include_patterns:
            self.add_pattern_rule(rule, SelectionType.INCLUDE)
        for rule in template_config.exclude_patterns:
            self.add_pattern_rule(rule, SelectionType.EXCLUDE)
        
        for group_name in template_config.pattern_groups:
            try:
                self.add_pattern_group(group_name, SelectionType.INCLUDE)
            except KeyError:
                logging.warning(f"Pattern group '{group_name}' not found, skipping")
        
        # Update precedence config
        self.set_precedence_config(template_config.precedence_config)
        
        # Mark patterns as dirty
        self._patterns_dirty = True
        self._compiled_pattern_cache = None
    
    def apply_preset(self, preset_name: str, platform: Optional[str] = None) -> None:
        """
        Apply an application preset to this FileSelection.
        
        Args:
            preset_name: Name of the preset to apply
            platform: Optional platform-specific configuration (e.g., "windows", "linux")
        
        Raises:
            ValueError: If preset is not found
        """
        # Import here to avoid circular dependency
        try:
            from .application_preset_manager import ApplicationPresetManager
            
            preset_manager = ApplicationPresetManager()
            preset = preset_manager.get_preset(preset_name)
            
            if preset is None:
                raise ValueError(f"Preset '{preset_name}' not found")
            
            # Use platform-specific config if available
            if platform and platform in preset.platform_specific:
                config = preset.platform_specific[platform]
            else:
                config = preset.selection_template.selection_config
            
            # Apply the preset configuration
            self.apply_template(config, merge=False)
            
        except ImportError:
            logging.warning("ApplicationPresetManager not available, cannot apply preset")
            raise ValueError("Preset system not available")
    
    def optimize_for_performance(self, estimated_file_count: Optional[int] = None) -> None:
        """
        Optimize the selection for better performance.
        
        This method uses the new pattern engine's optimization capabilities
        to improve pattern matching performance.
        
        Args:
            estimated_file_count: Optional estimate of files to process
        """
        if not self._use_new_engine or not self._pattern_engine:
            logging.warning("Performance optimization requires new engine to be enabled")
            return
        
        # Optimize pattern order for early termination
        if self._include_pattern_rules:
            self._include_pattern_rules = self._pattern_engine.optimize_pattern_order(
                self._include_pattern_rules
            )
        
        if self._exclude_pattern_rules:
            self._exclude_pattern_rules = self._pattern_engine.optimize_pattern_order(
                self._exclude_pattern_rules
            )
        
        # Invalidate cache to force recompilation with optimized patterns
        self._compiled_pattern_cache = None
        
        logging.info("Selection patterns optimized for performance")
    
    def validate_patterns(self) -> Dict[str, Any]:
        """
        Validate all patterns in the selection.
        
        Returns:
            Dict with validation results including errors and warnings
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "pattern_count": len(self._include_pattern_rules) + len(self._exclude_pattern_rules)
        }
        
        if not self._use_new_engine or not self._pattern_engine:
            # Legacy validation - just check if patterns compile
            try:
                self._compile_patterns()
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"Pattern compilation failed: {e}")
            return results
        
        # Use new engine for validation
        all_rules = self._include_pattern_rules + self._exclude_pattern_rules
        
        for rule in all_rules:
            try:
                validation_result = self._pattern_engine.validate_pattern_syntax(
                    rule.pattern,
                    rule.syntax
                )
                
                if not validation_result.is_valid:
                    results["valid"] = False
                    for error in validation_result.errors:
                        results["errors"].append(f"Pattern '{rule.pattern}': {error.message}")
                
                for warning in validation_result.warnings:
                    results["warnings"].append(f"Pattern '{rule.pattern}': {warning.message}")
                    
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"Pattern '{rule.pattern}' validation failed: {e}")
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the selection.
        
        Returns:
            Dict with performance metrics
        """
        stats = {
            "using_new_engine": self._use_new_engine,
            "include_paths": len(self._includes),
            "exclude_paths": len(self._excludes),
            "include_patterns": len(self._include_patterns),
            "exclude_patterns": len(self._exclude_patterns),
            "include_pattern_rules": len(self._include_pattern_rules),
            "exclude_pattern_rules": len(self._exclude_pattern_rules),
            "pattern_groups": len(self._pattern_groups),
            "patterns_compiled": not self._patterns_dirty,
            "cache_valid": self._compiled_pattern_cache is not None
        }
        
        if self._use_new_engine and self._pattern_engine and self._compiled_pattern_cache:
            try:
                pattern_stats = self._pattern_engine.get_pattern_statistics(
                    self._compiled_pattern_cache
                )
                stats["pattern_statistics"] = {
                    "total_patterns": pattern_stats.total_patterns,
                    "glob_patterns": pattern_stats.glob_count,
                    "regex_patterns": pattern_stats.regex_count,
                    "literal_patterns": pattern_stats.literal_count,
                    "average_complexity": pattern_stats.average_complexity
                }
            except Exception as e:
                logging.debug(f"Could not get pattern statistics: {e}")
        
        return stats
    
    def __repr__(self) -> str:
        engine_status = "new_engine" if self._use_new_engine else "legacy"
        return (f"<FileSelection includes={self._includes}, "
                f"excludes={self._excludes}, "
                f"include_patterns={self._include_patterns}, "
                f"exclude_patterns={self._exclude_patterns}, "
                f"pattern_rules={len(self._include_pattern_rules) + len(self._exclude_pattern_rules)}, "
                f"engine={engine_status}>")
