"""
Repository resolution utilities for TimeLocker.

This module provides utilities for resolving repository names to URIs,
supporting both named repositories from configuration and direct URI usage.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

from ..config import ConfigurationModule
from ..interfaces.exceptions import ConfigurationError
from ..config.configuration_manager import RepositoryNotFoundError

logger = logging.getLogger(__name__)


def _is_valid_uri_format(uri: str) -> bool:
    """
    Check if a string looks like a valid repository URI.

    Args:
        uri: String to validate

    Returns:
        True if it looks like a valid URI, False otherwise
    """
    # Check for common URI schemes
    valid_schemes = [
            "file://",
            "s3://", "s3:",
            "b2://", "b2:",
            "sftp://",
            "rest://",
            "rclone:",
            "azure://",
            "gs://",
            "swift:",
    ]

    # Check if it starts with a valid scheme
    for scheme in valid_schemes:
        if uri.startswith(scheme):
            return True

    # Check if it's an absolute path (starts with /)
    if uri.startswith("/"):
        return True

    # Check if it contains :// (generic URI format)
    if "://" in uri:
        return True

    return False


def _detect_type(uri: str) -> str:
    """Infer repository type from URI for display/testing convenience."""
    if uri.startswith(("s3://", "s3:")):
        return "s3"
    if uri.startswith(("sftp://", "sftp:")):
        return "sftp"
    if uri.startswith("file://") or uri.startswith("/"):
        return "local"
    return "local"


def normalize_repository_uri(uri: str) -> str:
    """
    Normalize repository URI to restic format.

    Converts standard URI formats (e.g., s3://host/bucket) to restic formats (e.g., s3:host/bucket)
    for consistent storage in configuration.

    Args:
        uri: Repository URI to normalize

    Returns:
        Normalized URI in restic format

    Examples:
        normalize_repository_uri("s3://minio.local/bucket") -> "s3:minio.local/bucket"
        normalize_repository_uri("s3:minio.local/bucket") -> "s3:minio.local/bucket"
        normalize_repository_uri("b2://bucket/path") -> "b2:bucket/path"
        normalize_repository_uri("file:///path/to/repo") -> "file:///path/to/repo"
    """
    from urllib.parse import urlparse

    if not uri:
        return uri

    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()

    # S3: Convert s3://host/bucket to s3:host/bucket
    if scheme == 's3' and parsed.netloc:
        bucket = parsed.netloc
        path = parsed.path.lstrip("/")
        return f"s3:{bucket}/{path}" if path else f"s3:{bucket}/"

    # B2: Convert b2://bucket/path to b2:bucket/path
    elif scheme == 'b2' and parsed.netloc:
        bucket = parsed.netloc
        path = parsed.path.lstrip("/")
        return f"b2:{bucket}/{path}" if path else f"b2:{bucket}/"

    # For other schemes or already in restic format, return as-is
    return uri


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

        # Validate if it looks like a valid URI before treating as literal
        if not _is_valid_uri_format(name_or_uri):
            # Not a valid URI and not a configured repository name
            repo_names = list(config.repositories.keys())
            if repo_names:
                raise RepositoryNotFoundError(
                        f"Repository '{name_or_uri}' not found. "
                        f"Available repositories: {', '.join(repo_names)}. "
                        f"Or provide a valid URI (e.g., file:///path, s3://bucket/path)."
                )
            else:
                raise RepositoryNotFoundError(
                        f"Repository '{name_or_uri}' not found. "
                        f"No repositories configured. "
                        f"Use 'tl config repositories add' to add repositories, "
                        f"or provide a valid URI (e.g., file:///path, s3://bucket/path)."
                )

        # If not found, treat as literal URI
        return name_or_uri

    except ConfigurationError as e:
        # Provide helpful error message with available repositories
        try:
            config = config_module.get_config()
            if config.repositories:
                repo_names = list(config.repositories.keys())
                raise RepositoryNotFoundError(
                        f"{e}. Available repositories: {', '.join(repo_names)}"
                )
            else:
                raise RepositoryNotFoundError(
                        f"{e}. No repositories configured. Use 'tl config add-repo' to add one."
                )
        except:
            raise RepositoryNotFoundError(str(e))


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
            uri = repo_config.location or ""
            return {
                    "uri":         uri,
                    "name":        name_or_uri,
                    "description": repo_config.description or "",
                    "type":        _detect_type(uri),
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


# ------------------------------
# Validation helpers
# ------------------------------


def validate_repository_name_or_uri(value: str) -> None:
    """
    Validate user-provided repository identifier.

    Rules:
    - Allowed: configured name (no path separators), or a URI with a scheme (e.g., file://, s3://, s3:, b2:, rclone:, swift:, azure://, gs://, rest:).
    - Disallowed: local filesystem paths without an explicit file:// scheme (absolute or relative), including Windows drive paths.

    Raises:
        ValueError: if the value looks like a local path but lacks the required file:// scheme
    """
    if not value:
        return

    v = value.strip()

    # Accept explicit schemes
    if "://" in v or v.startswith((
        "s3:", "b2:", "rclone:", "rest:", "sftp:", "swift:",
    )):
        return

    # Windows drive path: C:\path or C:/path
    if re.match(r"^[A-Za-z]:[\\/]", v):
        raise ValueError(
            f"Local paths must use file:// prefix (e.g., file:///C:/backups). Received: {value}"
        )

    # UNC path \\server\share
    if v.startswith("\\\\"):
        raise ValueError(
            f"UNC paths must use file:// prefix (e.g., file://server/share). Received: {value}"
        )

    # Unix absolute path
    if v.startswith("/"):
        raise ValueError(
            f"Local paths must use file:// prefix (e.g., file:///var/backups). Received: {value}"
        )

    # Relative path containing separators
    if ("/" in v) or ("\\" in v):
        raise ValueError(
            f"Local paths must use file:// prefix (e.g., file://{os.path.abspath(v)}). Received: {value}"
        )

    # Otherwise treat as a name and allow
    return
