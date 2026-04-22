"""CLI helper functions extracted for direct unit testing.

This module currently provides a helper for storing backend credentials for a repository.
Previously, the logic lived as a nested function inside the `repos add` command. Extracting it
allows targeted unit tests without invoking Typer CLI flows.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Protocol

try:  # Optional import; only catch import-related failures
    from rich.console import Console as RichConsole
except (ImportError, ModuleNotFoundError):  # pragma: no cover - fallback minimal console
    RichConsole = None


class ConsoleLike(Protocol):
    """Minimal console surface used by CLI helpers."""

    print: Callable[..., None]


class CredentialStore(Protocol):
    """Credential manager behavior required by store_backend_credentials."""

    def is_locked(self) -> bool:
        ...

    def ensure_unlocked(self, allow_prompt: bool = True) -> bool:
        ...

    def store_repository_backend_credentials(
            self,
            repository_id: str,
            backend_type: str,
            credentials_dict: Mapping[str, object],
    ) -> None:
        ...


class RepositoryConfigStore(Protocol):
    """Configuration manager behavior required by store_backend_credentials."""

    def update_repository(
            self,
            repository_name: str,
            repository_config: dict[str, object],
    ) -> None:
        ...


class _FallbackConsole:
    """Minimal console implementation used when Rich is unavailable."""

    def print(self, *args: object, **kwargs: object) -> None:
        _ = kwargs.pop("style", None)
        print(*args)


def _create_console() -> ConsoleLike:
    """Create the default console implementation for helper output."""
    if RichConsole is not None:
        return RichConsole()
    return _FallbackConsole()


# Lazy type hints to avoid circular imports at runtime
def store_backend_credentials(
        *,
        repository_name: str,
        backend_type: str,
        backend_name: str,
        credentials_dict: Mapping[str, object],
        cred_mgr: CredentialStore,
        config_manager: RepositoryConfigStore,
        repository_config: dict[str, object],
        console: ConsoleLike | None = None,
        logger: logging.Logger | None = None,
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
    console = console or _create_console()
    logger = logger or logging.getLogger(__name__)

    # Ensure credential manager is unlocked
    if cred_mgr.is_locked():
        if not cred_mgr.ensure_unlocked(allow_prompt=allow_prompt):
            console.print(
                    f"[yellow]⚠️  Could not unlock credential manager. {backend_name} credentials not stored.[/yellow]"
            )
            return False

    # Store credentials (may raise and bubble up; callers decide handling policy)
    cred_mgr.store_repository_backend_credentials(
            repository_name,
            backend_type,
            dict(credentials_dict),
    )

    # Update repository config
    repository_config['has_backend_credentials'] = True
    config_manager.update_repository(repository_name, repository_config)

    logger.info(f"{backend_name} credentials stored for repository '{repository_name}'")
    return True
