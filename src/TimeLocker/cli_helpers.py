"""CLI helper functions extracted for direct unit testing.

This module currently provides a helper for storing backend credentials for a repository.
Previously, the logic lived as a nested function inside the `repos add` command. Extracting it
allows targeted unit tests without invoking Typer CLI flows.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import logging

try:  # Optional import; only catch import-related failures
    from rich.console import Console
except (ImportError, ModuleNotFoundError):  # pragma: no cover - fallback minimal console
    class Console:  # type: ignore
        def print(self, *args, **kwargs):  # noqa: D401
            print(*args)


# Lazy type hints to avoid circular imports at runtime
def store_backend_credentials(
        *,
        repository_name: str,
        backend_type: str,
        backend_name: str,
        credentials_dict: Dict[str, Any],  # accept non-string values (e.g., booleans)
        cred_mgr,
        config_manager,
        repository_config: Dict[str, Any],
        console: Optional[Console] = None,
        logger: Optional[logging.Logger] = None,
        allow_prompt: bool = True,
) -> bool:
    """Store backend credentials with proper credential manager unlocking & config update.

    Args:
        repository_name: Name of the repository being configured.
        backend_type: Backend identifier (e.g. 's3', 'b2').
        backend_name: Human readable backend name (e.g. 'AWS', 'B2') used in messages.
        credentials_dict: Mapping of credentials to store. Values may be strings or other
            JSON-serialisable primitives (e.g., booleans like insecure_tls=True).
        cred_mgr: CredentialManager instance (duck-typed for testability).
        config_manager: Configuration manager used to persist repository_config updates.
        repository_config: Mutable repository configuration dict; will be updated in-place
            with has_backend_credentials=True on success.
        console: Rich Console (or compatible) for user-facing output.
        logger: Logger for audit/info messages.
        allow_prompt: Whether unlocking is allowed to prompt (passed to ensure_unlocked).

    Returns:
        True if credentials stored successfully, False if unlock failed.

    Raises:
        Any exception raised by cred_mgr.store_repository_backend_credentials will propagate.
    """
    console = console or Console()
    logger = logger or logging.getLogger(__name__)

    # Ensure credential manager is unlocked
    if cred_mgr.is_locked():
        if not cred_mgr.ensure_unlocked(allow_prompt=allow_prompt):
            console.print(
                    f"[yellow]⚠️  Could not unlock credential manager. {backend_name} credentials not stored.[/yellow]"
            )
            return False

    # Store credentials (may raise and bubble up; callers decide handling policy)
    cred_mgr.store_repository_backend_credentials(repository_name, backend_type, credentials_dict)

    # Update repository config
    repository_config['has_backend_credentials'] = True
    config_manager.update_repository(repository_name, repository_config)

    logger.info(f"{backend_name} credentials stored for repository '{repository_name}'")
    return True
