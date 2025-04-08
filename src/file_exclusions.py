from pathlib import Path
from typing import List

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