"""
Test data generators for CLI command testing.

Provides functions for generating realistic test data for various
CLI command scenarios.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path


class TestDataGenerator:
    """
    Generator for creating realistic test data.
    
    This class provides methods for generating various types of test data
    with realistic values and relationships.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the test data generator.
        
        Args:
            seed: Random seed for reproducible data generation
        """
        if seed is not None:
            random.seed(seed)
        
        self._snapshot_counter = 0
        self._repository_counter = 0
    
    def generate_snapshot_id(self) -> str:
        """Generate a realistic snapshot ID."""
        return ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    def generate_repository_name(self) -> str:
        """Generate a repository name."""
        self._repository_counter += 1
        return f"repo-{self._repository_counter:03d}"
    
    def generate_snapshot(self, **overrides) -> Dict[str, Any]:
        """Generate a snapshot with realistic data."""
        return generate_snapshot_data(**overrides)
    
    def generate_repository(self, **overrides) -> Dict[str, Any]:
        """Generate a repository with realistic data."""
        return generate_repository_data(**overrides)
    
    def generate_snapshots(
        self,
        count: int,
        repository: str = "test-repo",
        start_date: Optional[datetime] = None,
        interval_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple snapshots with sequential timestamps.
        
        Args:
            count: Number of snapshots to generate
            repository: Repository name
            start_date: Starting date for snapshots
            interval_hours: Hours between snapshots
        
        Returns:
            List of snapshot dictionaries
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=count)
        
        snapshots = []
        for i in range(count):
            timestamp = start_date + timedelta(hours=i * interval_hours)
            snapshot = self.generate_snapshot(
                repository=repository,
                time=timestamp.isoformat() + 'Z'
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def generate_repositories(
        self,
        count: int,
        backend: str = "local"
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple repositories.
        
        Args:
            count: Number of repositories to generate
            backend: Backend type for all repositories
        
        Returns:
            List of repository dictionaries
        """
        repositories = []
        for _ in range(count):
            name = self.generate_repository_name()
            repository = self.generate_repository(
                name=name,
                backend=backend
            )
            repositories.append(repository)
        
        return repositories


def generate_snapshot_data(
    snapshot_id: Optional[str] = None,
    repository: str = "test-repo",
    time: Optional[str] = None,
    hostname: Optional[str] = None,
    username: Optional[str] = None,
    paths: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate realistic snapshot data.
    
    Args:
        snapshot_id: Snapshot ID (generated if not provided)
        repository: Repository name
        time: Snapshot timestamp
        hostname: Hostname
        username: Username
        paths: Backed up paths
        tags: Snapshot tags
        **kwargs: Additional properties
    
    Returns:
        Snapshot data dictionary
    """
    if snapshot_id is None:
        snapshot_id = ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    if time is None:
        time = datetime.now().isoformat() + 'Z'
    
    if hostname is None:
        hostname = f"host-{random.randint(1, 100)}"
    
    if username is None:
        username = f"user{random.randint(1, 10)}"
    
    if paths is None:
        paths = [f"/home/{username}"]
    
    if tags is None:
        tags = []
    
    snapshot = {
        'id': snapshot_id,
        'short_id': snapshot_id[:8],
        'repository': repository,
        'time': time,
        'hostname': hostname,
        'username': username,
        'paths': paths,
        'tags': tags,
        'tree': ''.join(random.choices(string.hexdigits.lower(), k=12)),
        'parent': None,
        **kwargs
    }
    
    return snapshot


def generate_repository_data(
    name: Optional[str] = None,
    backend: str = "local",
    uri: Optional[str] = None,
    initialized: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate realistic repository data.
    
    Args:
        name: Repository name (generated if not provided)
        backend: Backend type
        uri: Repository URI (generated if not provided)
        initialized: Whether repository is initialized
        **kwargs: Additional properties
    
    Returns:
        Repository data dictionary
    """
    if name is None:
        name = f"repo-{random.randint(1, 1000):03d}"
    
    if uri is None:
        if backend == "local":
            uri = f"file:///tmp/{name}"
        elif backend == "s3":
            uri = f"s3:s3.amazonaws.com/bucket-{random.randint(1, 100)}/{name}"
        elif backend == "b2":
            uri = f"b2:bucket-{random.randint(1, 100)}:{name}"
        else:
            uri = f"{backend}://test/{name}"
    
    repository = {
        'name': name,
        'uri': uri,
        'backend': backend,
        'initialized': initialized,
        'locked': False,
        'description': f'Repository {name}',
        'created_at': datetime.now().isoformat() + 'Z',
        'last_checked': datetime.now().isoformat() + 'Z' if initialized else None,
        **kwargs
    }
    
    return repository


def generate_backup_data(
    repository: Optional[str] = None,
    paths: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate realistic backup operation data.
    
    Args:
        repository: Repository name
        paths: Paths to backup
        exclude_patterns: Exclude patterns
        include_patterns: Include patterns
        tags: Backup tags
        **kwargs: Additional properties
    
    Returns:
        Backup data dictionary
    """
    if repository is None:
        repository = f"repo-{random.randint(1, 100)}"
    
    if paths is None:
        paths = ["/home/user/Documents", "/home/user/Pictures"]
    
    if exclude_patterns is None:
        exclude_patterns = ["*.tmp", "*.log", ".cache/*"]
    
    if include_patterns is None:
        include_patterns = []
    
    if tags is None:
        tags = ["backup", f"date-{datetime.now().strftime('%Y%m%d')}"]
    
    backup = {
        'repository': repository,
        'paths': paths,
        'exclude_patterns': exclude_patterns,
        'include_patterns': include_patterns,
        'tags': tags,
        'dry_run': False,
        **kwargs
    }
    
    return backup


def generate_restore_data(
    repository: Optional[str] = None,
    snapshot_id: Optional[str] = None,
    target_path: Optional[str] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate realistic restore operation data.
    
    Args:
        repository: Repository name
        snapshot_id: Snapshot to restore
        target_path: Restore target path
        include_patterns: Include patterns
        exclude_patterns: Exclude patterns
        **kwargs: Additional properties
    
    Returns:
        Restore data dictionary
    """
    if repository is None:
        repository = f"repo-{random.randint(1, 100)}"
    
    if snapshot_id is None:
        snapshot_id = ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    if target_path is None:
        target_path = "/tmp/restore"
    
    if include_patterns is None:
        include_patterns = []
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    restore = {
        'repository': repository,
        'snapshot_id': snapshot_id,
        'target_path': target_path,
        'include_patterns': include_patterns,
        'exclude_patterns': exclude_patterns,
        'verify': True,
        **kwargs
    }
    
    return restore


def generate_file_tree(
    root: Path,
    depth: int = 3,
    files_per_dir: int = 5,
    dirs_per_dir: int = 3
) -> List[Path]:
    """
    Generate a realistic file tree structure.
    
    Args:
        root: Root directory path
        depth: Maximum depth of directory tree
        files_per_dir: Number of files per directory
        dirs_per_dir: Number of subdirectories per directory
    
    Returns:
        List of all generated file paths
    """
    all_files = []
    
    def create_level(current_path: Path, current_depth: int):
        if current_depth > depth:
            return
        
        # Create files in current directory
        for i in range(files_per_dir):
            ext = random.choice(['.txt', '.md', '.log', '.tmp', '.dat'])
            file_path = current_path / f"file_{i}{ext}"
            all_files.append(file_path)
        
        # Create subdirectories
        if current_depth < depth:
            for i in range(dirs_per_dir):
                dir_path = current_path / f"dir_{i}"
                create_level(dir_path, current_depth + 1)
    
    create_level(root, 0)
    return all_files
