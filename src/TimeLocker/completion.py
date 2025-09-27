"""
Auto-completion support for TimeLocker CLI commands.

This module provides intelligent auto-completion for:
- Repository names from configuration
- Snapshot IDs from repositories
- Target names from configuration
- URI paths for repositories
- Command-specific parameters
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from functools import wraps
import typer

from .config import ConfigurationModule
from .utils.repository_resolver import resolve_repository_uri, list_available_repositories
from .backup_manager import BackupManager
from .snapshot_manager import SnapshotManager


@contextmanager
def suppress_completion_logging():
    """
    Context manager to suppress logging during completion operations.

    This prevents log messages from interfering with shell completion output.
    """
    # Store original log levels
    original_levels = {}
    loggers_to_suppress = [
            'TimeLocker',
            'restic',
            'urllib3',
            'requests',
            'root'
    ]

    try:
        # Suppress logging for completion
        for logger_name in loggers_to_suppress:
            logger = logging.getLogger(logger_name)
            original_levels[logger_name] = logger.level
            logger.setLevel(logging.CRITICAL)

        yield

    finally:
        # Restore original log levels
        for logger_name, original_level in original_levels.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(original_level)


def suppress_logging_for_completion(func):
    """
    Decorator to suppress logging during completion function execution.

    Args:
        func: Completion function to wrap

    Returns:
        Wrapped function with logging suppression
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with suppress_completion_logging():
            return func(*args, **kwargs)

    return wrapper


def complete_repository_names(incomplete: str) -> List[str]:
    """
    Complete repository names from configuration.
    
    Args:
        incomplete: Partial repository name being typed
        
    Returns:
        List of matching repository names
    """
    try:
        repositories = list_available_repositories()
        return [name for name in repositories.keys() if name.startswith(incomplete)]
    except Exception:
        return []


def complete_target_names(incomplete: str) -> List[str]:
    """
    Complete backup target names from configuration.
    
    Args:
        incomplete: Partial target name being typed
        
    Returns:
        List of matching target names
    """
    try:
        config_module = ConfigurationModule()
        config = config_module.get_config()
        return [name for name in config.backup_targets.keys() if name.startswith(incomplete)]
    except Exception:
        return []


@suppress_logging_for_completion
def complete_snapshot_ids(incomplete: str, repository: Optional[str] = None) -> List[str]:
    """
    Complete snapshot IDs from repository.
    
    Args:
        incomplete: Partial snapshot ID being typed
        repository: Repository name or URI (if None, uses default)
        
    Returns:
        List of matching snapshot IDs (first 12 characters)
    """
    try:
        # Resolve repository URI
        if repository:
            repository_uri = resolve_repository_uri(repository)
        else:
            # Try to get default repository
            from .utils.repository_resolver import get_default_repository
            default_repo = get_default_repository()
            if not default_repo:
                return []
            repository_uri = resolve_repository_uri(default_repo)

        # Get password from environment
        password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
        if not password:
            return []  # Can't complete without password

        # Connect to repository and get snapshots
        backup_manager = BackupManager()
        repo = backup_manager.from_uri(repository_uri, password=password)
        snapshot_manager = SnapshotManager(repo)
        snapshots = snapshot_manager.list_snapshots()

        # Return matching snapshot IDs (first 12 chars)
        snapshot_ids = [snap.id[:12] for snap in snapshots]
        return [sid for sid in snapshot_ids if sid.startswith(incomplete)]

    except Exception:
        return []


def complete_repository_uris(incomplete: str) -> List[str]:
    """
    Complete repository URIs with common patterns.
    
    Args:
        incomplete: Partial URI being typed
        
    Returns:
        List of matching URI patterns
    """
    completions = []

    # File URI completions (only when explicitly requested)
    if incomplete.startswith("file://"):
        path_part = incomplete[7:]  # Remove "file://" prefix

        # Complete file paths
        try:
            if path_part:
                base_path = Path(path_part).parent if "/" in path_part else Path(".")
                name_part = Path(path_part).name
            else:
                base_path = Path(".")
                name_part = ""

            if base_path.exists():
                for item in base_path.iterdir():
                    if item.is_dir() and item.name.startswith(name_part):
                        completions.append(f"file://{item.absolute()}")
        except Exception:
            pass

    # S3 URI completions
    elif incomplete.startswith("s3:"):
        s3_patterns = [
                "s3:s3.amazonaws.com/bucket-name",
                "s3:s3.us-east-1.amazonaws.com/bucket-name",
                "s3:s3.us-west-2.amazonaws.com/bucket-name",
                "s3:s3.eu-west-1.amazonaws.com/bucket-name",
        ]
        completions.extend([uri for uri in s3_patterns if uri.startswith(incomplete)])

    # SFTP URI completions
    elif incomplete.startswith("sftp:"):
        sftp_patterns = [
                "sftp:user@hostname:/path/to/backup",
                "sftp:backup@server.example.com:/backups",
        ]
        completions.extend([uri for uri in sftp_patterns if uri.startswith(incomplete)])

    # REST server completions
    elif incomplete.startswith("rest:"):
        rest_patterns = [
                "rest:http://localhost:8000/",
                "rest:https://backup.example.com/",
        ]
        completions.extend([uri for uri in rest_patterns if uri.startswith(incomplete)])

    # If no specific protocol, suggest common patterns
    elif not incomplete:
        completions.extend([
                "file://",
                "s3:",
                "sftp:",
                "rest:",
        ])

    return completions


@suppress_logging_for_completion
def complete_repositories(incomplete: str) -> List[str]:
    """
    Complete repository names and URIs, prioritizing configured repository names.

    Args:
        incomplete: Partial repository name or URI being typed

    Returns:
        List of matching repository names and URI patterns
    """
    completions = []

    # First, try to complete with configured repository names
    try:
        repositories = list_available_repositories()
        repo_names = [name for name in repositories.keys() if name.startswith(incomplete)]
        completions.extend(repo_names)
    except Exception:
        pass

    # If user is typing a URI pattern, also provide URI completions
    if (incomplete.startswith(("file://", "s3:", "sftp:", "rest:")) or
            "://" in incomplete):
        uri_completions = complete_repository_uris(incomplete)
        completions.extend(uri_completions)

    # If no matches and no incomplete text, only show configured repository names
    elif not incomplete:
        try:
            repositories = list_available_repositories()
            # Only add repo names if we haven't already added them
            if not completions:
                completions.extend(repositories.keys())
        except Exception:
            pass
    return completions


def complete_file_paths(incomplete: str) -> List[str]:
    """
    Complete file and directory paths.
    
    Args:
        incomplete: Partial path being typed
        
    Returns:
        List of matching file/directory paths
    """
    try:
        if incomplete:
            path = Path(incomplete)
            if path.is_absolute():
                base_path = path.parent
                name_part = path.name
            else:
                base_path = Path.cwd() / path.parent if path.parent != Path(".") else Path.cwd()
                name_part = path.name
        else:
            base_path = Path.cwd()
            name_part = ""

        completions = []
        if base_path.exists():
            for item in base_path.iterdir():
                if item.name.startswith(name_part):
                    if item.is_dir():
                        completions.append(f"{item}/")
                    else:
                        completions.append(str(item))

        return completions
    except Exception:
        return []


# Typer completion functions for specific parameters
def repository_name_completer(incomplete: str) -> List[str]:
    """Typer completer for repository names."""
    return complete_repository_names(incomplete)


def target_name_completer(incomplete: str) -> List[str]:
    """Typer completer for target names."""
    return complete_target_names(incomplete)


def snapshot_id_completer(incomplete: str) -> List[str]:
    """Typer completer for snapshot IDs."""
    return complete_snapshot_ids(incomplete)


def repository_uri_completer(incomplete: str) -> List[str]:
    """Typer completer for repository URIs."""
    return complete_repository_uris(incomplete)


def repository_completer(incomplete: str) -> List[str]:
    """Typer completer for repositories (names and URIs)."""
    return complete_repositories(incomplete)


def file_path_completer(incomplete: str) -> List[str]:
    """Typer completer for file paths."""
    return complete_file_paths(incomplete)


# Special completers for context-aware completion
class ContextAwareCompleters:
    """Context-aware completers that can access command context."""

    @staticmethod
    def snapshot_id_with_repo_context(ctx: typer.Context, incomplete: str) -> List[str]:
        """
        Complete snapshot IDs with repository context from command.
        
        Args:
            ctx: Typer context containing command parameters
            incomplete: Partial snapshot ID being typed
            
        Returns:
            List of matching snapshot IDs
        """
        # Try to get repository from context
        repository = None
        if hasattr(ctx, 'params') and 'repository' in ctx.params:
            repository = ctx.params['repository']

        return complete_snapshot_ids(incomplete, repository)


# Export completion functions for use in CLI
__all__ = [
        'complete_repository_names',
        'complete_target_names',
        'complete_snapshot_ids',
        'complete_repository_uris',
        'complete_repositories',
        'complete_file_paths',
        'repository_name_completer',
        'target_name_completer',
        'snapshot_id_completer',
        'repository_uri_completer',
        'repository_completer',
        'file_path_completer',
        'ContextAwareCompleters',
]
