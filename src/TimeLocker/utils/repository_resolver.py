"""
Repository resolution utilities for TimeLocker.

This module provides utilities for resolving repository names to URIs,
supporting both named repositories from configuration and direct URI usage.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import ConfigurationModule
from ..interfaces.exceptions import ConfigurationError

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
    config_module = ConfigurationModule(config_dir)

    try:
        config = config_module.get_config()

        # If name_or_uri is None, try to get default repository
        if not name_or_uri:
            if not config.repositories:
                raise ConfigurationError("No repositories configured")
            # Use first repository as default
            name_or_uri = list(config.repositories.keys())[0]

        # Check if it's already a URI (contains :// or starts with /)
        if "://" in name_or_uri or name_or_uri.startswith("/"):
            return name_or_uri

        # Try to resolve as repository name
        if name_or_uri in config.repositories:
            repo_config = config.repositories[name_or_uri]
            return repo_config.location or ""

        # If not found, treat as literal URI
        return name_or_uri

    except ConfigurationError as e:
        # Provide helpful error message with available repositories
        try:
            config = config_module.get_config()
            if config.repositories:
                repo_names = list(config.repositories.keys())
                raise ConfigurationError(
                        f"{e}. Available repositories: {', '.join(repo_names)}"
                )
            else:
                raise ConfigurationError(
                        f"{e}. No repositories configured. Use 'tl config add-repo' to add one."
                )
        except:
            raise ConfigurationError(str(e))


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
    config_module = ConfigurationModule(config_dir)

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
        config = config_module.get_config()
        if name_or_uri in config.repositories:
            repo_config = config.repositories[name_or_uri]
            return {
                    "uri":         repo_config.location or "",
                    "name":        name_or_uri,
                    "description": repo_config.description or "",
                    "is_named":    True
            }
        else:
            # Assume it's a URI if not found as name
            return {
                    "uri":      name_or_uri,
                    "is_named": False
            }
    except ConfigurationError:
        # Assume it's a URI if config error
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
    config_module = ConfigurationModule(config_dir)
    try:
        config = config_module.get_config()
        return {name: {
                "uri":         repo.location or "",
                "description": repo.description or "",
        } for name, repo in config.repositories.items()}
    except ConfigurationError:
        return {}


def get_default_repository(config_dir: Optional[Path] = None) -> Optional[str]:
    """
    Get the default repository name.

    Args:
        config_dir: Configuration directory path. If None, uses default.

    Returns:
        Default repository name or None if not set
    """
    config_module = ConfigurationModule(config_dir)
    try:
        config = config_module.get_config()
        if config.repositories:
            # Return first repository as default
            return list(config.repositories.keys())[0]
        return None
    except ConfigurationError:
        return None
