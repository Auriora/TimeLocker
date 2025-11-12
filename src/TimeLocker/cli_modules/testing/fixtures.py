"""
Test fixtures for CLI command testing.

Provides reusable test data structures and fixture factories for creating
consistent test data across all CLI tests.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class CLITestFixtures:
    """
    Container for common test fixtures used across CLI tests.
    
    This class provides a centralized way to access common test data
    and ensures consistency across different test modules.
    """
    
    # Default test values
    default_repository_name: str = "test-repo"
    default_repository_uri: str = "file:///tmp/test-repo"
    default_snapshot_id: str = "abc123def456"
    default_target_name: str = "test-target"
    default_policy_name: str = "test-policy"
    default_password: str = "test_password_12345"
    
    # Test paths
    test_source_path: Path = field(default_factory=lambda: Path("/test/source"))
    test_dest_path: Path = field(default_factory=lambda: Path("/test/dest"))
    test_config_path: Path = field(default_factory=lambda: Path("/test/config"))
    
    # Test timestamps
    test_timestamp: datetime = field(default_factory=lambda: datetime(2024, 1, 1, 12, 0, 0))
    
    def get_test_repository(self, name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get a test repository fixture."""
        return create_test_repository(
            name=name or self.default_repository_name,
            **kwargs
        )
    
    def get_test_snapshot(self, snapshot_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get a test snapshot fixture."""
        return create_test_snapshot(
            snapshot_id=snapshot_id or self.default_snapshot_id,
            **kwargs
        )
    
    def get_test_target(self, name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get a test target fixture."""
        return create_test_target(
            name=name or self.default_target_name,
            **kwargs
        )
    
    def get_test_config(self, **kwargs) -> Dict[str, Any]:
        """Get a test configuration fixture."""
        return create_test_config(**kwargs)


def create_test_config(
    repositories: Optional[List[Dict[str, Any]]] = None,
    targets: Optional[List[Dict[str, Any]]] = None,
    policies: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test configuration object.
    
    Args:
        repositories: List of repository configurations
        targets: List of backup target configurations
        policies: List of policy configurations
        **kwargs: Additional configuration properties
    
    Returns:
        Test configuration dictionary
    """
    config = {
        'version': '1.0',
        'repositories': repositories or [],
        'targets': targets or [],
        'policies': policies or [],
        'settings': {
            'default_repository': None,
            'log_level': 'INFO',
            'cache_dir': '/tmp/timelocker/cache',
        },
        **kwargs
    }
    return config


def create_test_repository(
    name: str = "test-repo",
    uri: Optional[str] = None,
    backend: str = "local",
    initialized: bool = True,
    locked: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test repository object.
    
    Args:
        name: Repository name
        uri: Repository URI (auto-generated if not provided)
        backend: Backend type (local, s3, b2, etc.)
        initialized: Whether repository is initialized
        locked: Whether repository is locked
        **kwargs: Additional repository properties
    
    Returns:
        Test repository dictionary
    """
    if uri is None:
        if backend == "local":
            uri = f"file:///tmp/{name}"
        elif backend == "s3":
            uri = f"s3:s3.amazonaws.com/bucket/{name}"
        elif backend == "b2":
            uri = f"b2:bucket-name:{name}"
        else:
            uri = f"{backend}://test/{name}"
    
    repository = {
        'name': name,
        'uri': uri,
        'backend': backend,
        'initialized': initialized,
        'locked': locked,
        'description': f'Test repository {name}',
        'created_at': '2024-01-01T12:00:00Z',
        'last_checked': '2024-01-01T12:00:00Z' if initialized else None,
        **kwargs
    }
    return repository


def create_test_snapshot(
    snapshot_id: str = "abc123def456",
    repository: str = "test-repo",
    time: Optional[str] = None,
    hostname: str = "test-host",
    username: str = "test-user",
    paths: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test snapshot object.
    
    Args:
        snapshot_id: Snapshot identifier
        repository: Repository name
        time: Snapshot timestamp (ISO format)
        hostname: Hostname where backup was created
        username: Username who created backup
        paths: List of backed up paths
        tags: List of snapshot tags
        **kwargs: Additional snapshot properties
    
    Returns:
        Test snapshot dictionary
    """
    if time is None:
        time = '2024-01-01T12:00:00Z'
    
    if paths is None:
        paths = ['/home/user']
    
    if tags is None:
        tags = []
    
    snapshot = {
        'id': snapshot_id,
        'short_id': snapshot_id[:8] if len(snapshot_id) >= 8 else snapshot_id,
        'repository': repository,
        'time': time,
        'hostname': hostname,
        'username': username,
        'paths': paths,
        'tags': tags,
        'tree': 'tree123abc',
        'parent': None,
        **kwargs
    }
    return snapshot


def create_test_target(
    name: str = "test-target",
    paths: Optional[List[str]] = None,
    repository: str = "test-repo",
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test backup target object.
    
    Args:
        name: Target name
        paths: List of paths to backup
        repository: Repository name
        exclude_patterns: List of exclude patterns
        include_patterns: List of include patterns
        tags: List of tags to apply
        **kwargs: Additional target properties
    
    Returns:
        Test target dictionary
    """
    if paths is None:
        paths = ['/home/user/Documents']
    
    if exclude_patterns is None:
        exclude_patterns = []
    
    if include_patterns is None:
        include_patterns = []
    
    if tags is None:
        tags = []
    
    target = {
        'name': name,
        'paths': paths,
        'repository': repository,
        'exclude_patterns': exclude_patterns,
        'include_patterns': include_patterns,
        'tags': tags,
        'description': f'Test target {name}',
        'enabled': True,
        **kwargs
    }
    return target


def create_test_policy(
    name: str = "test-policy",
    repository: str = "test-repo",
    keep_last: int = 7,
    keep_daily: int = 7,
    keep_weekly: int = 4,
    keep_monthly: int = 12,
    keep_yearly: int = 5,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test retention policy object.
    
    Args:
        name: Policy name
        repository: Repository name
        keep_last: Number of last snapshots to keep
        keep_daily: Number of daily snapshots to keep
        keep_weekly: Number of weekly snapshots to keep
        keep_monthly: Number of monthly snapshots to keep
        keep_yearly: Number of yearly snapshots to keep
        **kwargs: Additional policy properties
    
    Returns:
        Test policy dictionary
    """
    policy = {
        'name': name,
        'repository': repository,
        'keep_last': keep_last,
        'keep_daily': keep_daily,
        'keep_weekly': keep_weekly,
        'keep_monthly': keep_monthly,
        'keep_yearly': keep_yearly,
        'description': f'Test policy {name}',
        'enabled': True,
        **kwargs
    }
    return policy


def create_test_selection(
    name: str = "test-selection",
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test file selection object.
    
    Args:
        name: Selection name
        include_patterns: List of include patterns
        exclude_patterns: List of exclude patterns
        **kwargs: Additional selection properties
    
    Returns:
        Test selection dictionary
    """
    if include_patterns is None:
        include_patterns = ['*.txt', '*.md']
    
    if exclude_patterns is None:
        exclude_patterns = ['*.tmp', '*.log']
    
    selection = {
        'name': name,
        'include_patterns': include_patterns,
        'exclude_patterns': exclude_patterns,
        'description': f'Test selection {name}',
        **kwargs
    }
    return selection
