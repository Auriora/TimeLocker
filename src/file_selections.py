from pathlib import Path
from typing import List, Union


class FileSelections:
    """Represents paths and files to include in backup"""
    paths: List[Path]
    files: List[str]

    def __init__(self, paths: List[Union[Path, str]] = None, files: List[str] = None):
        # Paths can be directories or specific files
        self.paths = [Path(p) if isinstance(p, str) else p for p in (paths or [])]
        # Files are filename patterns (e.g., "*.txt", "doc.*")
        self.files = files or []

    def add_path(self, path: Path):
        if path not in self.paths:
            self.paths.append(path)

    def remove_path(self, path: Path):
        if path in self.paths:
            self.paths.remove(path)

    def __iter__(self):
        return iter(self.paths)

    def __repr__(self):
        return f"<Selection paths={self.paths}>"

class FileExclusions:
    """Represents paths and patterns to exclude from backup"""

    def __init__(self, paths: List[Path], patterns: List[str]):
        self.paths = paths
        self.patterns = patterns

    def add_pattern(self, pattern: str):
        if pattern not in self.patterns:
            self.patterns.append(pattern)

    def remove_pattern(self, pattern: str):
        if pattern in self.patterns:
            self.patterns.remove(pattern)

    def __iter__(self):
        return iter(self.patterns)

    def __repr__(self):
        return f"<Exclusion patterns={self.patterns}>"
