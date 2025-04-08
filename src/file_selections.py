from pathlib import Path
from typing import Optional, List, Union

class FileSelections:
    """Represents paths and files to include in backup"""
    paths: List[Path]
    files: List[str]

    def __init__(self, paths: List[Union[Path, str]] = None, files: List[str] = None):
        # Paths can be directories or specific files
        self.paths = [Path(p) if isinstance(p, str) else p for p in (paths or [])]
        # Files are filename patterns (e.g., "*.txt", "doc.*")
        self.files = files or []

    def add_path(self, path: str):
        if path not in self.paths:
            self.paths.append(path)

    def remove_path(self, path: str):
        if path in self.paths:
            self.paths.remove(path)

    def __iter__(self):
        return iter(self.paths)

    def __repr__(self):
        return f"<Selection paths={self.paths}>"
