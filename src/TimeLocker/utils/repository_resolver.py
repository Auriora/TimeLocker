"""
Repository resolution utilities for TimeLocker.

This module provides utilities for resolving repository names to URIs,
supporting both named repositories from configuration and direct URI usage.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config.configuration_manager import ConfigurationManager, RepositoryNotFoundError

logger = logging.getLogger(__name__)


def resolve_repository_uri(name_or_uri: Optional[str],
                           config_dir: Optional[Path] = None) -> str:
    """
    Resolve repository name to URI, supporting both names and direct URIs.
    
    Args:
        name_or_uri: Repository name or URI string. If None, tries to use default repository.
        config_dir: Configuration directory path. If None, uses default.
        
    Returns:
        Resolved repository URI string
        
    Raises:
        RepositoryNotFoundError: If repository name cannot be resolved
        
    Examples:
        # Using repository name
        uri = resolve_repository_uri("production")  # -> "s3:s3.region.amazonaws.com/bucket"
        
        # Using direct URI (passthrough)
        uri = resolve_repository_uri("s3://bucket/path")  # -> "s3://bucket/path"
        
        # Using default repository
        uri = resolve_repository_uri(None)  # -> URI of default repository
    """
    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_manager = ConfigurationManager(config_dir=config_dir)

    try:
        return config_manager.resolve_repository(name_or_uri or "")
    except RepositoryNotFoundError as e:
        # Provide helpful error message with available repositories
        repositories = config_manager.list_repositories()
        if repositories:
            repo_names = list(repositories.keys())
            raise RepositoryNotFoundError(
                    f"{e}. Available repositories: {', '.join(repo_names)}"
            )
        else:
            raise RepositoryNotFoundError(
                    f"{e}. No repositories configured. Use 'tl config add-repo' to add one."
            )


def get_repository_info(name_or_uri: str,
                        config_dir: Optional[Path] = None) -> dict:
    """
    Get repository information including metadata if it's a named repository.
    
    Args:
        name_or_uri: Repository name or URI string
        config_dir: Configuration directory path. If None, uses default.
        
    Returns:
        Dictionary with repository information:
        - uri: Repository URI
        - name: Repository name (if named repository)
        - description: Repository description (if available)
        - type: Repository type (if available)
        - is_named: Boolean indicating if this is a named repository
        
    Examples:
        info = get_repository_info("production")
        # -> {"uri": "s3:...", "name": "production", "description": "...", "is_named": True}
        
        info = get_repository_info("s3://bucket/path")
        # -> {"uri": "s3://bucket/path", "is_named": False}
    """
    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_manager = ConfigurationManager(config_dir=config_dir)

    # Check if it's a URI (contains :// or starts with known schemes)
    if ("://" in name_or_uri or
            name_or_uri.startswith("s3:") or
            name_or_uri.startswith("b2:") or
            name_or_uri.startswith("/") or
            name_or_uri.startswith("sftp:")):
        return {
                "uri":      name_or_uri,
                "is_named": False
        }

    # Try to get as named repository
    try:
        repo_config = config_manager.get_repository(name_or_uri)
        return {
                "uri":         repo_config["uri"],
                "name":        name_or_uri,
                "description": repo_config.get("description", ""),
                "type":        repo_config.get("type", "unknown"),
                "created":     repo_config.get("created", ""),
                "is_named":    True
        }
    except RepositoryNotFoundError:
        # Assume it's a URI if not found as name
        return {
                "uri":      name_or_uri,
                "is_named": False
        }


def list_available_repositories(config_dir: Optional[Path] = None) -> dict:
    """
    List all available named repositories.
    
    Args:
        config_dir: Configuration directory path. If None, uses default.
        
    Returns:
        Dictionary mapping repository names to their configurations
    """
    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_manager = ConfigurationManager(config_dir=config_dir)
    return config_manager.list_repositories()


def get_default_repository(config_dir: Optional[Path] = None) -> Optional[str]:
    """
    Get the default repository name.
    
    Args:
        config_dir: Configuration directory path. If None, uses default.
        
    Returns:
        Default repository name or None if not set
    """
    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_manager = ConfigurationManager(config_dir=config_dir)
    return config_manager.get_default_repository()
