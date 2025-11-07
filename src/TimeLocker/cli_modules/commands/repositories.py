"""
Repository operations.

This module contains CLI commands for repository operations.
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

# Module-specific imports
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config import ConfigurationModule
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    RepositoryInfo,
    RepositoryMode
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.completion import (
    repository_name_completer,
    repository_completer,
    repository_uri_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri
)
from TimeLocker.cli_helpers import store_backend_credentials as store_backend_credentials_helper
from urllib.parse import urlparse
import re

# Create Typer app
repos_app = create_typer_app(
    name="repos",
    help_text="Repository operations"
)



# Commands

@repos_app.command("list")
@with_error_handling("List Error")
@with_logging
def repos_list(
        verbose: VerboseOption = False,
        json_output: JsonOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """List repository configurations and their URIs."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        list_method = _get_service_method(manager, "list_repositories")
        repositories = []
        if list_method:
            try:
                repositories = list_method() or []
            except Exception as exc:
                logging.getLogger(__name__).debug("Service repository listing failed: %s", exc)
                raise
        if json_output:
            import json
            console.print(json.dumps(repositories, indent=2))
            return
        if not repositories:
            show_info_panel("No Repositories", "No repositories configured. Add one with 'tl repos add'.")
            return
        table = Table(title="Configured Repositories")
        table.add_column("Name", style="cyan")
        table.add_column("URI", style="magenta")
        table.add_column("Description", overflow="fold")
        if verbose:
            table.add_column("Type", style="yellow")
            table.add_column("Engine", style="green")
        table.add_column("Default", justify="center")
        
        for repo in repositories:
            if isinstance(repo, dict):
                name = str(repo.get("name", "unknown"))
                uri = str(repo.get("uri", repo.get("location", "unknown")))
                description = str(repo.get("description", ""))
                is_default = repo.get("is_default", False)
                repo_type = str(repo.get("type", "N/A"))
                repo_engine = str(repo.get("engine", "N/A"))
            else:
                name = str(getattr(repo, "name", "unknown"))
                uri = str(getattr(repo, "uri", getattr(repo, "location", "unknown")))
                description = str(getattr(repo, "description", ""))
                is_default = getattr(repo, "is_default", False)
                repo_type = str(getattr(repo, "type", "N/A"))
                repo_engine = str(getattr(repo, "engine", "N/A"))
            
            # Add default indicator
            default_indicator = "✓" if is_default else ""
            
            if verbose:
                table.add_row(name, uri, description, repo_type, repo_engine, default_indicator)
            else:
                table.add_row(name, uri, description, default_indicator)
        console.print(table)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "List operation was cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("List Error", f"Failed to list repositories: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("add")
@with_error_handling("Add Error")
@with_logging
def repos_add(
        name: Annotated[Optional[str], typer.Argument(help="Repository name")] = None,
        uri: Annotated[Optional[str], typer.Argument(help="Repository URI", autocompletion=repository_uri_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Repository description")] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        set_default: Annotated[bool, typer.Option("--set-default", help="Set as default repository")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        if not name:
            if interactive:
                name = Prompt.ask("Repository name")
            else:
                show_error_panel("Missing Parameter", "Repository name is required in non-interactive mode")
                raise typer.Exit(2)
        if not name.strip():
            show_error_panel("Invalid Repository Name", "Repository name cannot be empty or whitespace")
            raise typer.Exit(2)
        if not re.match(r"^[A-Za-z0-9._-]+$", name):
            show_error_panel("Invalid Repository Name", "Repository name contains unsupported characters. Use letters, numbers, dashes, underscores, or dots.")
            raise typer.Exit(1)
        if not uri:
            if interactive:
                uri = Prompt.ask("Repository URI")
            else:
                show_error_panel("Missing Parameter", "Repository URI is required in non-interactive mode")
                raise typer.Exit(2)
        if not uri.strip():
            show_error_panel("Invalid Repository URI", "Repository URI cannot be empty or whitespace")
            raise typer.Exit(1)
        if "::" in uri or ("://" not in uri and not uri.startswith(("s3:", "b2:", "rclone:", "rest:", "/"))):
            show_error_panel("Invalid Repository URI", f"Invalid repository URI format: '{uri}'.")
            raise typer.Exit(1)
        if "://" in uri:
            parsed = urlparse(uri)
            scheme = (parsed.scheme or "").lower()
            allowed_schemes = {"file", "s3", "b2", "azure", "gs", "swift", "rest", "rclone", "sftp"}
            if scheme not in allowed_schemes:
                show_error_panel("Invalid Repository URI", f"Unsupported repository URI scheme: '{scheme or 'unknown'}'.")
                raise typer.Exit(1)
            if scheme == "file":
                if parsed.netloc not in ("", None, "localhost"):
                    show_error_panel("Invalid Repository URI", f"Invalid file URI host component in '{uri}'. Use file:///absolute/path.")
                    raise typer.Exit(1)
                if parsed.path:
                    try:
                        if not Path(parsed.path).is_absolute():
                            show_error_panel("Invalid Repository URI", f"File URI must use an absolute path: '{uri}'.")
                            raise typer.Exit(1)
                    except Exception:
                        show_error_panel("Invalid Repository URI", f"Invalid file path in URI: '{uri}'.")
                        raise typer.Exit(1)
            else:
                if not parsed.netloc:
                    show_error_panel("Invalid Repository URI", f"Repository URI '{uri}' is missing required host or bucket component.")
                    raise typer.Exit(1)

        manager = _get_service_manager_for_command(config_dir)
        backend_type = _determine_backend_from_uri(uri)

        add_method = _get_service_method(manager, "add_repository")
        payload = {
                "name":        name,
                "uri":         uri,
                "description": description or f"{name} repository",
        }
        if password:
            payload["password"] = password
        if add_method:
            _call_service_method(add_method, **payload)
        else:
            config_manager = ConfigurationManager(config_dir=config_dir)
            config_manager.add_repository(name, uri, description)
        if set_default:
            default_method = _get_service_method(manager, "set_default_repository")
            if default_method:
                _call_service_method(default_method, name=name, repository=name, repository_name=name)
            else:
                config_manager = ConfigurationManager(config_dir=config_dir)
                config_manager.set_default_repository(name)

        config_module_for_credentials = None
        try:
            config_module_for_credentials = _create_configuration_module(config_dir)
            try:
                config_module_for_credentials.get_repository(name)
            except Exception:
                try:
                    repo_payload = {
                            "name":        name,
                            "location":    uri,
                            "description": description or f"{name} repository",
                    }
                    if password:
                        repo_payload["password"] = password
                    config_module_for_credentials.add_repository(repo_payload)
                except Exception as repo_exc:
                    logging.getLogger(__name__).debug("Failed to persist repository via configuration module: %s", repo_exc)
        except Exception as module_exc:
            logging.getLogger(__name__).debug("Configuration module unavailable for repository persistence: %s", module_exc)

        if backend_type == "s3":
            try:
                store_credentials = Confirm.ask(
                        f"Store {_backend_display_name(backend_type)} credentials for '{name}' now?",
                        default=True
                )
            except (EOFError, RuntimeError):
                store_credentials = False
            if store_credentials:
                try:
                    repository_obj = None
                    if config_module_for_credentials and hasattr(config_module_for_credentials, "get_repository"):
                        try:
                            repository_obj = config_module_for_credentials.get_repository(name)
                        except Exception as repo_exc:
                            logging.getLogger(__name__).debug("Failed to load repository for credential storage: %s", repo_exc)
                    if config_module_for_credentials is None:
                        logging.getLogger(__name__).debug("Skipping credential storage; configuration module unavailable.")
                        raise RuntimeError("Configuration module unavailable for credential storage")

                    repository_config = _repository_config_to_dict(repository_obj, name)

                    credential_manager = _create_credential_manager(config_dir)
                    try:
                        access_key = Prompt.ask("AWS Access Key ID")
                        secret_key = Prompt.ask("AWS Secret Access Key", password=True)
                        region = Prompt.ask("AWS Region", default="")
                        insecure_tls = Confirm.ask("Allow insecure TLS (skip certificate verification)?", default=False)
                    except (EOFError, RuntimeError):
                        console.print("[yellow]⚠️  Skipping credential storage; no interactive input available.[/yellow]")
                        raise

                    credentials_payload = {
                            "access_key_id":     access_key,
                            "secret_access_key": secret_key,
                    }
                    if region:
                        credentials_payload["region"] = region
                    if insecure_tls:
                        credentials_payload["insecure_tls"] = True

                    storage_success = store_backend_credentials_helper(
                            repository_name=name,
                            backend_type=backend_type,
                            backend_name=_backend_display_name(backend_type),
                            credentials_dict=credentials_payload,
                            cred_mgr=credential_manager,
                            config_manager=config_module_for_credentials,
                            repository_config=repository_config,
                            console=console,
                            logger=logging.getLogger(__name__),
                            allow_prompt=interactive,
                    )

                    if storage_success:
                        console.print(f"[green]{_backend_display_name(backend_type)} credentials stored[/green]")
                except Exception as credential_exc:
                    if isinstance(credential_exc, EOFError):
                        logging.getLogger(__name__).debug("Skipping credential storage due to non-interactive input: %s", credential_exc)
                    else:
                        logging.getLogger(__name__).debug("Credential storage during repos add failed: %s", credential_exc)
                        raise

        # Attempt to persist repository password automatically for future operations.
        def _normalized_password(value: Optional[str]) -> Optional[str]:
            if isinstance(value, str):
                trimmed = value.strip()
                return trimmed or None
            return value

        password_sources = [
                _normalized_password(password),
                _normalized_password(os.getenv("TIMELOCKER_PASSWORD")),
                _normalized_password(os.getenv("RESTIC_PASSWORD")),
        ]
        auto_password = next((p for p in password_sources if p), None)
        if auto_password and manager:
            try:
                result = manager.set_repository_password(name, auto_password)
                stored = getattr(result, "success", None)
                if stored is None:
                    stored = bool(result)
                if stored:
                    console.print("🔐 [green]Repository password stored in credential manager.[/green]")
            except Exception as exc:
                logging.getLogger(__name__).debug("Automatic repository password storage failed: %s", exc)
                console.print("⚠️  [yellow]Unable to store repository password automatically; use 'tl credentials store' if needed.[/yellow]")

        show_success_panel("Repository Added", f"Repository '{name}' added successfully.")
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Repository add cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to add repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("show")
@with_error_handling("Show Error")
@with_logging
def repos_show(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        show_method = _get_service_method(manager, "get_repository_by_name")
        repository_info = None
        if show_method:
            try:
                repository_info = _call_service_method(show_method, name=name, repository_name=name, repository=name)
            except Exception as exc:
                logging.getLogger(__name__).debug("Service repository lookup failed: %s", exc)
                repository_info = None
        if repository_info is None:
            config_manager = ConfigurationManager(config_dir=config_dir)
            repository_info = config_manager.get_repository(name)
        # Extract repository information
        if isinstance(repository_info, dict):
            repo_name = repository_info.get("name", name)
            repo_uri = repository_info.get("uri", repository_info.get("location", "N/A"))
            repo_description = repository_info.get("description", "")
            repo_metadata = repository_info.get("metadata", {})
            is_default = repository_info.get("is_default", False)
            repo_type = repository_info.get("type", "N/A")
            repo_engine = repository_info.get("engine", "N/A")
            created_at = repository_info.get("created_at", "N/A")
            updated_at = repository_info.get("updated_at", "N/A")
        else:
            repo_name = getattr(repository_info, "name", name)
            repo_uri = getattr(repository_info, "uri", getattr(repository_info, "location", "N/A"))
            repo_description = getattr(repository_info, "description", "")
            repo_metadata = getattr(repository_info, "metadata", {})
            is_default = getattr(repository_info, "is_default", False)
            repo_type = getattr(repository_info, "type", "N/A")
            repo_engine = getattr(repository_info, "engine", "N/A")
            created_at = getattr(repository_info, "created_at", "N/A")
            updated_at = getattr(repository_info, "updated_at", "N/A")
        
        # Build display content
        panel_lines = []
        panel_lines.append(f"[bold]Name:[/bold] {repo_name}")
        panel_lines.append(f"[bold]URI:[/bold] {repo_uri}")
        if repo_description:
            panel_lines.append(f"[bold]Description:[/bold] {repo_description}")
        panel_lines.append(f"[bold]Type:[/bold] {repo_type}")
        panel_lines.append(f"[bold]Engine:[/bold] {repo_engine}")
        panel_lines.append(f"[bold]Default:[/bold] {'Yes' if is_default else 'No'}")
        panel_lines.append(f"[bold]Created:[/bold] {created_at}")
        panel_lines.append(f"[bold]Updated:[/bold] {updated_at}")
        
        # Display custom metadata if present
        if repo_metadata and isinstance(repo_metadata, dict):
            panel_lines.append("\n[bold]Custom Metadata:[/bold]")
            for key, value in repo_metadata.items():
                panel_lines.append(f"  [cyan]{key}:[/cyan] {value}")
        
        console.print(Panel("\n".join(panel_lines), title=f"Repository: {name}", border_style="blue"))
    except ConfigurationError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Show operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Show Error", f"Failed to show repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("remove")
@with_error_handling("Remove Error")
@with_logging
def repos_remove(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    setup_logging(verbose, config_dir)
    try:
        # Get repository information for confirmation
        config_manager = ConfigurationManager(config_dir=config_dir)
        
        try:
            repo_config = config_manager.get_repository(name)
        except ConfigurationError:
            show_error_panel("Repository Not Found", f"Repository '{name}' not found in configuration.")
            raise typer.Exit(1)

        # Create repository info for confirmation
        repository_info = {
            'repository_id': name,
            'name': name,
            'location': repo_config.get('uri', 'Unknown'),
            'mode': 'read_write'  # Default mode
        }

        # Initialize security service for confirmation
        security_service, access_manager = _create_security_manager(config_dir)

        # Validate session for repository operations
        if not _validate_session_for_operation(access_manager, "repository_delete", name):
            show_error_panel("Authentication Required", 
                           "Session authentication failed. Please ensure you have proper access.")
            raise typer.Exit(1)

        # Check if repository is locked
        if security_service.is_repository_locked(name):
            show_error_panel("Repository Locked", 
                           f"Repository '{name}' is currently locked and cannot be removed. "
                           f"Please unlock it first using 'timelocker repos unlock {name}'.")
            raise typer.Exit(1)

        # Use enhanced confirmation for repository deletion
        if not yes:
            try:
                confirmed = security_service.confirm_destructive_operation(
                    "delete_repository", repository_info, force=False
                )
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Repository removal cancelled.")
                    raise typer.Exit(0)
            except Exception as e:
                # Fallback to simple confirmation if security service fails
                logger.warning(f"Security confirmation failed, using simple confirmation: {e}")
                interactive = sys.stdin.isatty()
                if interactive:
                    confirmed = Confirm.ask(f"Remove repository '{name}' from configuration?", default=False)
                    if not confirmed:
                        show_info_panel("Operation Cancelled", "Repository removal cancelled.")
                        raise typer.Exit(0)

        # Proceed with removal
        manager = _get_service_manager_for_command(config_dir)
        remove_method = _get_service_method(manager, "remove_repository")
        if remove_method:
            _call_service_method(remove_method, name=name, repository=name, repository_name=name)
        else:
            config_manager.remove_repository(name)
        
        show_success_panel("Repository Removed", f"Repository '{name}' removed successfully.")
        
    except ConfigurationError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Removal cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Remove Error", f"Failed to remove repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("update")
@with_error_handling("Update Error")
@with_logging
def repos_update(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Update repository description")] = None,
        metadata: Annotated[Optional[List[str]], typer.Option("--metadata", "-m", help="Add/update metadata (format: key=value)")] = None,
        clear_metadata: Annotated[bool, typer.Option("--clear-metadata", help="Clear all custom metadata")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Update repository metadata and configuration."""
    setup_logging(verbose, config_dir)
    try:
        config_manager = ConfigurationManager(config_dir=config_dir)
        
        # Get existing repository configuration
        try:
            repo_config = config_manager.get_repository(name)
        except ConfigurationError:
            show_error_panel("Repository Not Found", f"Repository '{name}' not found in configuration.")
            raise typer.Exit(1)
        
        # Track what was updated
        updates = []
        
        # Update description if provided
        if description is not None:
            if hasattr(repo_config, 'description'):
                repo_config.description = description
            elif isinstance(repo_config, dict):
                repo_config['description'] = description
            updates.append(f"description")
        
        # Handle metadata updates
        if clear_metadata:
            if hasattr(repo_config, 'metadata'):
                repo_config.metadata = {}
            elif isinstance(repo_config, dict):
                repo_config['metadata'] = {}
            updates.append("cleared metadata")
        
        if metadata:
            # Parse metadata key=value pairs
            metadata_dict = {}
            for item in metadata:
                if '=' not in item:
                    show_error_panel("Invalid Metadata Format", 
                                   f"Metadata must be in format 'key=value', got: {item}")
                    raise typer.Exit(1)
                key, value = item.split('=', 1)
                metadata_dict[key.strip()] = value.strip()
            
            # Update metadata
            if hasattr(repo_config, 'metadata'):
                if not repo_config.metadata:
                    repo_config.metadata = {}
                repo_config.metadata.update(metadata_dict)
            elif isinstance(repo_config, dict):
                if 'metadata' not in repo_config:
                    repo_config['metadata'] = {}
                repo_config['metadata'].update(metadata_dict)
            
            updates.append(f"metadata ({len(metadata_dict)} items)")
        
        if not updates:
            show_info_panel("No Updates", "No updates specified. Use --description or --metadata to update repository.")
            raise typer.Exit(0)
        
        # Save updated configuration
        config = config_manager.get_config()
        if config and hasattr(config, 'repositories'):
            config.repositories[name] = repo_config
            config_manager.save_config(config)
        
        updates_str = ", ".join(updates)
        show_success_panel("Repository Updated", 
                         f"Repository '{name}' updated successfully.\nUpdated: {updates_str}")
        
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Update cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Update Error", f"Failed to update repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("default")
@with_error_handling("Default Error")
@with_logging
def repos_default(
        name: Annotated[str, typer.Argument(help="Repository name to set as default", autocompletion=repository_name_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        default_method = _get_service_method(manager, "set_default_repository")
        if default_method:
            _call_service_method(default_method, name=name, repository=name, repository_name=name)
        else:
            config_manager = ConfigurationManager(config_dir=config_dir)
            config_manager.set_default_repository(name)
        show_success_panel("Default Repository Set", f"Default repository set to '{name}'.")
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Default Error", f"Failed to set default repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("lock")
@with_error_handling("Lock Error")
@with_logging
def repos_lock(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        operation: Annotated[str, typer.Option("--operation", help="Operation requiring the lock")] = "manual_lock",
        timeout: Annotated[Optional[int], typer.Option("--timeout", help="Lock timeout in minutes")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Lock repository to prevent accidental modifications."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security service
        security_service, access_manager = _create_security_manager(config_dir)

        # Validate session for repository operations
        if not _validate_session_for_operation(access_manager, "repository_lock", name):
            show_error_panel("Authentication Required", 
                           "Session authentication failed. Please ensure you have proper access.")
            raise typer.Exit(1)

        # Get current user
        import os
        current_user = os.getenv('USER', os.getenv('USERNAME', 'system'))

        # Lock repository
        lock_id = security_service.lock_repository(name, operation, current_user, timeout)
        
        timeout_str = f" (timeout: {timeout} minutes)" if timeout else ""
        show_success_panel("Repository Locked", 
                         f"Repository '{name}' locked for operation '{operation}'{timeout_str}.\n"
                         f"Lock ID: {lock_id}")
        
    except Exception as e:
        show_error_panel("Lock Error", f"Failed to lock repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("unlock")
@with_error_handling("Unlock Error")
@with_logging
def repos_unlock(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        lock_id: Annotated[Optional[str], typer.Option("--lock-id", help="Specific lock ID to remove")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Unlock repository."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security service
        security_service, access_manager = _create_security_manager(config_dir)

        # Validate session for repository operations
        if not _validate_session_for_operation(access_manager, "repository_unlock", name):
            show_error_panel("Authentication Required", 
                           "Session authentication failed. Please ensure you have proper access.")
            raise typer.Exit(1)

        # Get current user
        import os
        current_user = os.getenv('USER', os.getenv('USERNAME', 'system'))

        # Unlock repository
        success = security_service.unlock_repository(name, lock_id, current_user)
        
        if success:
            show_success_panel("Repository Unlocked", f"Repository '{name}' unlocked successfully.")
        else:
            show_error_panel("Unlock Failed", f"Failed to unlock repository '{name}'. Repository may not be locked.")
            raise typer.Exit(1)
        
    except Exception as e:
        show_error_panel("Unlock Error", f"Failed to unlock repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("mode")
@with_error_handling("Mode Error")
@with_logging
def repos_mode(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        mode: Annotated[Optional[str], typer.Argument(help="Repository mode (read_write, read_only, locked)")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Get or set repository access mode."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security service
        security_service, access_manager = _create_security_manager(config_dir)

        # Validate session for repository operations (only if setting mode)
        if mode is not None:
            if not _validate_session_for_operation(access_manager, "repository_mode_change", name):
                show_error_panel("Authentication Required", 
                               "Session authentication failed. Please ensure you have proper access.")
                raise typer.Exit(1)

        if mode is None:
            # Get current mode
            current_mode = security_service.get_repository_mode(name)
            mode_display = current_mode.replace("_", " ").title()
            
            # Check if locked
            is_locked = security_service.is_repository_locked(name)
            lock_status = " (Currently Locked)" if is_locked else ""
            
            show_info_panel("Repository Mode", f"Repository '{name}' is in {mode_display} mode{lock_status}.")
        else:
            # Validate mode
            valid_modes = ["read_write", "read_only", "locked"]
            if mode not in valid_modes:
                show_error_panel("Invalid Mode", f"Mode must be one of: {', '.join(valid_modes)}")
                raise typer.Exit(1)

            # Get current user
            import os
            current_user = os.getenv('USER', os.getenv('USERNAME', 'system'))

            # Set mode
            success = security_service.set_repository_mode(name, mode, current_user)
            
            if success:
                mode_display = mode.replace("_", " ").title()
                show_success_panel("Mode Changed", f"Repository '{name}' mode set to {mode_display}.")
            else:
                show_error_panel("Mode Change Failed", f"Failed to change repository mode for '{name}'.")
                raise typer.Exit(1)
        
    except Exception as e:
        show_error_panel("Mode Error", f"Failed to manage repository mode for '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("init")
@with_error_handling("Init Error")
@with_logging
def repos_init(
        name: Annotated[str, typer.Argument(help="Repository name to initialize", autocompletion=repository_name_completer)],
        repository: Annotated[
            Optional[str], typer.Option("--repository", "-r", help="Repository URI override", autocompletion=repository_uri_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Initialize a repository location."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        if not yes:
            if interactive:
                if not Confirm.ask(f"Initialize repository '{name}'?", default=True):
                    show_info_panel("Operation Cancelled", "Repository initialization cancelled.")
                    raise typer.Exit(0)
            else:
                show_error_panel("Confirmation Required", "Use --yes to confirm initialization in non-interactive mode.")
                raise typer.Exit(2)

        manager = _get_service_manager_for_command(config_dir)
        init_method = _get_service_method(manager, "initialize_repository")
        if not init_method:
            show_error_panel("Not Implemented", "Repository initialization is not available in this build.")
            raise typer.Exit(1)

        result = _call_service_method(
                init_method,
                name=name,
                repository=repository or name,
                repository_uri=repository,
                repository_name=name,
                password=password
        )

        already_initialized = False
        success = True
        errors = None
        if isinstance(result, dict):
            success = result.get("success", True)
            already_initialized = result.get("already_initialized", False)
            errors = result.get("errors")
        else:
            success = bool(result)

        if success and already_initialized:
            message = f"Repository '{name}' is already initialized."
            show_info_panel("Already Initialized", message)
            return

        if success:
            show_success_panel("Repository Initialized", f"Repository '{name}' initialized successfully.")
        else:
            detail_list = errors if isinstance(errors, list) else [errors] if errors else None
            show_error_panel("Initialization Failed", f"Failed to initialize repository '{name}'.", detail_list)
            raise typer.Exit(1)
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Initialization cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Init Error", f"Failed to initialize repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("unlock")
@with_error_handling("Unlock Error")
@with_logging
def repos_unlock(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[
            Optional[str], typer.Option("--repository", "-r", help="Repository URI override", autocompletion=repository_uri_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password if required")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Remove any existing locks from a repository."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        unlock_method = _get_service_method(manager, "unlock_repository")
        if not unlock_method:
            show_error_panel("Not Implemented", "Repository unlock is not available in this build.")
            raise typer.Exit(1)
        result = _call_service_method(
                unlock_method,
                name=name,
                repository=repository or name,
                repository_uri=repository,
                repository_name=name,
                password=password
        )
        success = bool(result if isinstance(result, bool) else getattr(result, "success", True))
        if success:
            show_success_panel("Repository Unlocked", f"Repository '{name}' unlocked successfully.")
        else:
            show_error_panel("Unlock Failed", f"Failed to unlock repository '{name}'.")
            raise typer.Exit(1)
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Unlock cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unlock Error", f"Failed to unlock repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("migrate")
@with_error_handling("Migrate Error")
@with_logging
def repos_migrate(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        migration: Annotated[Optional[str], typer.Option("--migration", "-m", help="Migration name to apply")] = None,
        repository: Annotated[
            Optional[str], typer.Option("--repository", "-r", help="Repository URI override", autocompletion=repository_uri_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password if required")] = None,
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Run repository format migration."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        confirmed = yes
        if not confirmed:
            if interactive:
                confirmed = Confirm.ask(f"Migrate repository '{name}'?", default=False)
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Migration cancelled.")
                    raise typer.Exit(0)
            else:
                confirmed = True

        manager = _get_service_manager_for_command(config_dir)
        migrate_method = _get_service_method(manager, "migrate_repository")
        if not migrate_method:
            show_error_panel("Not Implemented", "Repository migration is not available in this build.")
            raise typer.Exit(1)
        result = _call_service_method(
                migrate_method,
                name=name,
                repository=repository or name,
                repository_uri=repository,
                repository_name=name,
                migration=migration,
                password=password
        )
        success = bool(result if isinstance(result, bool) else getattr(result, "success", True))
        if success:
            show_success_panel("Migration Complete", f"Repository '{name}' migrated successfully.")
        else:
            show_error_panel("Migration Failed", f"Repository '{name}' migration failed.")
            raise typer.Exit(1)
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Migration cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Migration Error", f"Failed to migrate repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("forget")
@with_error_handling("Forget Error")
@with_logging
def repos_forget(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        keep_daily: Annotated[int, typer.Option("--keep-daily", help="Number of daily snapshots to keep")] = 7,
        keep_weekly: Annotated[int, typer.Option("--keep-weekly", help="Number of weekly snapshots to keep")] = 4,
        keep_monthly: Annotated[int, typer.Option("--keep-monthly", help="Number of monthly snapshots to keep")] = 12,
        keep_yearly: Annotated[int, typer.Option("--keep-yearly", help="Number of yearly snapshots to keep")] = 3,
        dry_run: DryRunOption = False,
        prune: Annotated[bool, typer.Option("--prune/--no-prune", help="Prune repository after forgetting snapshots", rich_help_panel=None)] = False,
        repository: Annotated[
            Optional[str], typer.Option("--repository", "-r", help="Repository URI override", autocompletion=repository_uri_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password if required")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Apply retention policy to repository snapshots."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        retention_method = _get_service_method(manager, "apply_retention_policy")
        if not retention_method:
            show_error_panel("Not Implemented", "Repository retention policy is not available in this build.")
            raise typer.Exit(1)

        result = _call_service_method(
                retention_method,
                name=name,
                repository=repository or name,
                repository_uri=repository,
                repository_name=name,
                keep_daily=keep_daily,
                keep_weekly=keep_weekly,
                keep_monthly=keep_monthly,
                keep_yearly=keep_yearly,
                dry_run=dry_run,
                password=password
        )

        errors = None
        success = True
        removed = []
        if isinstance(result, dict):
            success = result.get("status") in (None, "success", "ok", True)
            errors = result.get("errors")
            removed = result.get("removed_snapshots", [])
        else:
            success = getattr(result, "success", True)

        if not success:
            detail_list = errors if isinstance(errors, list) else [errors] if errors else None
            show_error_panel("Retention Failed", f"Retention policy failed for repository '{name}'.", detail_list)
            raise typer.Exit(1)

        summary = f"Retention policy applied to '{name}'."
        if removed:
            summary += f" Removed {len(removed)} snapshot(s)."
        if dry_run:
            summary += " (dry run)"
        show_success_panel("Retention Applied", summary.strip())

        if prune and not dry_run:
            prune_method = _get_service_method(manager, "prune_repository")
            if prune_method:
                prune_result = _call_service_method(
                        prune_method,
                        name=name,
                        repository=repository or name,
                        repository_uri=repository,
                        repository_name=name,
                        password=password
                )
                prune_success = True
                prune_errors = None
                if isinstance(prune_result, dict):
                    prune_success = prune_result.get("status") in (None, "success", "ok", True)
                    prune_errors = prune_result.get("errors")
                else:
                    prune_success = getattr(prune_result, "success", True)
                if prune_success:
                    show_success_panel("Prune Complete", f"Repository '{name}' pruned successfully.")
                else:
                    detail_list = prune_errors if isinstance(prune_errors, list) else [prune_errors] if prune_errors else None
                    show_error_panel("Prune Failed", f"Prune operation failed for repository '{name}'.", detail_list)
                    raise typer.Exit(1)
            else:
                show_error_panel("Not Implemented", "Repository prune is not available in this build.")
                raise typer.Exit(1)
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Retention operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Retention Error", f"Failed to apply retention policy: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("check")
@with_error_handling("Check Error")
@with_logging
def repos_check(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Verify repository integrity using restic check."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        check_method = _get_service_method(manager, "check_repository")
        if not check_method:
            show_error_panel("Not Implemented", "Repository check is not available in this build.")
            raise typer.Exit(1)
        result = _call_service_method(check_method, name=name, repository=name, repository_name=name)
        errors = None
        success = True
        if isinstance(result, dict):
            status = result.get("status")
            success = status in (None, "success", "ok", True)
            errors = result.get("errors")
        else:
            success = getattr(result, "success", True)
            errors = getattr(result, "errors", None)
        if success:
            show_success_panel("Repository Check", "Repository integrity check passed successfully.")
        else:
            detail_list = errors if isinstance(errors, list) else [errors] if errors else None
            show_error_panel("Check Failed", "Repository integrity verification failed.", detail_list)
            raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Check cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Check Error", f"Failed to check repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@repos_app.command("stats")
@with_error_handling("Stats Error")
@with_logging
def repos_stats(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Display repository statistics such as size and snapshot counts."""
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        stats_method = _get_service_method(manager, "get_repository_stats")
        if not stats_method:
            show_error_panel("Not Implemented", "Repository stats are not available in this build.")
            raise typer.Exit(1)
        stats = _call_service_method(stats_method, name=name, repository=name, repository_name=name) or {}
        if not isinstance(stats, dict):
            stats = getattr(stats, "__dict__", {}) or {}
        table = Table(title=f"Repository Stats: {name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in stats.items():
            table.add_row(str(key), str(value))
        console.print(table)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Stats cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Stats Error", f"Failed to get repository stats: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


