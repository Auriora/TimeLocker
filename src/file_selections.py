from pathlib import Path
from typing import List, Union, Dict, Set
from enum import Enum, auto


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
        "temporary_files": [
            "*.tmp", "*.temp", "~*", "*.bak", "*.swp", "*.cache",
            "__pycache__/*", "*.pyc", "node_modules/*"
        ],
        "media_files": [
            "*.jpg", "*.jpeg", "*.png", "*.gif", "*.mp3", "*.mp4",
            "*.avi", "*.mov", "*.wav"
        ],
        "source_code": [
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
    """

    def __init__(self):
        """Initialize empty file selection"""
        self._includes: Set[Path] = set()  # Explicit path includes
        self._excludes: Set[Path] = set()  # Explicit path excludes
        self._include_patterns: Set[str] = set()  # Pattern includes
        self._exclude_patterns: Set[str] = set()  # Pattern excludes
        self._pattern_groups: Dict[str, PatternGroup] = {}  # Named pattern groups

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

    def remove_pattern(self, pattern: str, selection_type: SelectionType = SelectionType.INCLUDE):
        """
        Remove a file pattern from either includes or excludes
        
        Args:
            pattern: File pattern to remove
            selection_type: Whether to remove from includes or excludes
        """
        target_set = self._include_patterns if selection_type == SelectionType.INCLUDE else self._exclude_patterns
        target_set.discard(pattern)

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

    def __repr__(self) -> str:
        return (f"<FileSelection includes={self._includes}, "
                f"excludes={self._excludes}, "
                f"include_patterns={self._include_patterns}, "
                f"exclude_patterns={self._exclude_patterns}>")


