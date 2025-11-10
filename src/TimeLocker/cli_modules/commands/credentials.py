"""
Credential management commands.

This module contains CLI commands for credential management commands.
Extracted from cli.py using automation script.
"""

import sys
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Import from base module (Phase 3 patterns)
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_configuration_module,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import from TimeLocker package
from TimeLocker import cli as _cli_module
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.cli import setup_logging, _create_credential_manager, _ensure_manager_unlocked

# Module-specific imports
from TimeLocker.security.credential_manager import (
    CredentialManager,
    CredentialManagerError
)
from TimeLocker.config.configuration_manager import ConfigurationManager
from TimeLocker.completion import repository_name_completer
from getpass import getpass

# Create Typer app
credentials_app = create_typer_app(
    name="credentials",
    help_text="Credential management commands"
)



# Commands

@credentials_app.command("unlock")
@with_error_handling("Unlock Error")
@with_logging
def credentials_unlock(
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Master password to unlock the credential manager")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Unlock the credential manager using the master password."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        try:
            service_manager = get_cli_service_manager()
        except Exception:
            service_manager = None

        if service_manager:
            unlock_method = _get_service_method(service_manager, "unlock_credential_manager")
            if unlock_method:
                try:
                    result = _call_service_method(unlock_method, password=password)
                    success = getattr(result, "success", None)
                    if success is None:
                        success = bool(result)
                    if success:
                        show_success_panel("Credentials Unlocked", "Credential manager unlocked successfully.")
                        return
                except click.exceptions.Exit:
                    raise
                except Exception as exc:
                    logging.getLogger(__name__).debug("Service credential unlock failed, falling back to local unlock: %s", exc)

        if not password:
            if interactive:
                password = Prompt.ask("Master password", password=True)
            else:
                show_error_panel("Missing Parameter", "Master password is required in non-interactive mode")
                raise typer.Exit(2)

        manager = _create_credential_manager(config_dir)
        if manager.unlock(password):
            show_success_panel("Credentials Unlocked", "Credential manager unlocked successfully.")
        else:
            show_error_panel("Unlock Failed", "Unable to unlock credential manager with the provided password.")
            raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Unlock operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unlock Error", f"Failed to unlock credential manager: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@credentials_app.command("store")
@with_error_handling("Store Error")
@with_logging
def credentials_store(
        repository: Annotated[str, typer.Argument(help="Repository name to associate with the password")],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password to store")] = None,
        master_password: Annotated[
            Optional[str], typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Store repository password in the credential manager."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        try:
            service_manager = get_cli_service_manager()
        except Exception:
            service_manager = None

        if not password:
            if interactive:
                password = Prompt.ask("Repository password", password=True)
            else:
                show_error_panel("Missing Parameter", "Repository password is required in non-interactive mode")
                raise typer.Exit(2)

        if service_manager:
            set_method = _get_service_method(service_manager, "set_repository_password")
            if set_method:
                try:
                    result = _call_service_method(set_method, repository=repository, password=password, master_password=master_password)
                    success = getattr(result, "success", None)
                    if success is None:
                        success = bool(result)
                    if success:
                        show_success_panel("Password Stored", f"Stored password for repository '{repository}'.")
                        return
                except click.exceptions.Exit:
                    raise
                except Exception as exc:
                    logging.getLogger(__name__).debug("Service password store failed, falling back to credential manager: %s", exc)

        manager = _create_credential_manager(config_dir)
        _ensure_manager_unlocked(manager, master_password, interactive)

        result = manager.store_repository_password(repository, password)
        if result is False:
            show_error_panel("Store Failed", f"Credential manager declined storing password for '{repository}'.")
            raise typer.Exit(1)

        show_success_panel("Password Stored", f"Stored password for repository '{repository}'.")
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential storage cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Store Error", f"Failed to store repository password: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@credentials_app.command("set")
@with_error_handling("Set Error")
@with_logging
def credentials_set(
        repository: Annotated[str, typer.Argument(help="Repository name to associate with the password")],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password to store")] = None,
        master_password: Annotated[
            Optional[str], typer.Option("--master-password", "-m", help="Master password to unlock the credential manager if locked")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Alias for credentials store."""
    credentials_store(repository, password, master_password, verbose, config_dir)




@credentials_app.command("list")
@with_error_handling("List Error")
@with_logging
def credentials_list(
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Master password to unlock the credential manager if locked")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """List repositories with stored credentials."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        manager = _create_credential_manager(config_dir)
        _ensure_manager_unlocked(manager, password, interactive)

        repositories = manager.list_repositories() if hasattr(manager, "list_repositories") else []

        if not repositories:
            show_info_panel("No Credentials", "No stored repository credentials found.")
            return

        table = Table(title="Stored Repository Credentials")
        table.add_column("Repository", style="cyan")
        for entry in repositories:
            if isinstance(entry, dict):
                repo_name = entry.get("name") or entry.get("repository") or "unknown"
            else:
                repo_name = str(entry)
            table.add_row(repo_name)
        console.print(table)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Listing credentials cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("List Error", f"Failed to list repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@credentials_app.command("remove")
@with_error_handling("Remove Error")
@with_logging
def credentials_remove(
        repository: Annotated[str, typer.Argument(help="Repository name to remove credentials for")],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Master password to unlock the credential manager if locked")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Remove stored credentials for a repository."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        try:
            service_manager = get_cli_service_manager()
        except Exception:
            service_manager = None

        if service_manager:
            remove_method = _get_service_method(service_manager, "remove_repository_password")
            if remove_method:
                try:
                    result = _call_service_method(remove_method, repository=repository)
                    success = getattr(result, "success", None)
                    if success is None:
                        success = bool(result)
                    if success:
                        show_success_panel("Credentials Removed", f"Removed stored credentials for '{repository}'.")
                        return
                except click.exceptions.Exit:
                    raise
                except Exception as exc:
                    logging.getLogger(__name__).debug("Service credential removal failed, falling back to local removal: %s", exc)

        manager = _create_credential_manager(config_dir)
        _ensure_manager_unlocked(manager, password, interactive)

        result = manager.remove_repository(repository)
        if result:
            show_success_panel("Credentials Removed", f"Removed stored credentials for '{repository}'.")
        else:
            show_info_panel("No Credentials Found", f"No stored credentials found for '{repository}'.")
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Credential removal cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Remove Error", f"Failed to remove repository credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


