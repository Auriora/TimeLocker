"""
Repository operations.

This module contains CLI commands for repository operations.
Extracted from cli.py using automation script.
"""

import sys
import os
import logging
import logging.handlers
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
    _create_config_service,
    ConfigService,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Module-specific imports
from TimeLocker.services.repository_manager import RepositoryManager

# Validation imports
from ..validation import validate_repository_name, validate_required_string, ValidationError
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.interfaces.exceptions import ConfigurationError
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
from TimeLocker.utils import get_progress_service, ProgressTemplates
from TimeLocker.cli_helpers import store_backend_credentials as store_backend_credentials_helper
from urllib.parse import urlparse
import re

# Create Typer app
repos_app = create_typer_app(
    name="repos",
    help_text="Repository operations"
)


# Helper functions

def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes is None:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _determine_backend_from_uri(uri: Optional[str]) -> Optional[str]:
    """Determine repository backend based on URI."""
    if not uri:
        return None
    normalized = uri.lower()
    if normalized.startswith(("s3://", "s3:")):
        return "s3"
    if normalized.startswith(("b2://", "b2:")):
        return "b2"
    if normalized.startswith(("azure:", "azure://")):
        return "azure"
    if normalized.startswith(("gs://", "gcs:", "gcs://")):
        return "gcs"
    return None


def _backend_display_name(backend: str) -> str:
    """Return user-facing backend name."""
    mapping = {
        "s3": "AWS",
        "b2": "Backblaze B2",
        "azure": "Azure",
        "gcs": "Google Cloud Storage"
    }
    return mapping.get(backend, backend.upper())


def _repository_config_to_dict(repository_obj, name: str) -> Dict[str, Any]:
    """Convert repository configuration object or mapping to dictionary."""
    if repository_obj is None:
        return {"name": name}
    if hasattr(repository_obj, "to_dict"):
        maybe_dict = repository_obj.to_dict()
        data = dict(maybe_dict) if isinstance(maybe_dict, dict) else {"name": name}
    elif isinstance(repository_obj, dict):
        data = dict(repository_obj)
    else:
        data = {"name": name}
        for attr in ("uri", "location", "description", "tags", "password", "has_backend_credentials"):
            if hasattr(repository_obj, attr):
                value = getattr(repository_obj, attr)
                if value is not None:
                    key = "uri" if attr == "location" else attr
                    data[key] = value
    data.setdefault("name", name)
    # Normalise location/uri fields
    if "uri" not in data and "location" in data:
        data["uri"] = data.pop("location")
    return data


def _create_credential_manager(config_dir: Optional[Path] = None):
    """Instantiate credential manager respecting configuration directory."""
    return CredentialManager()


def _create_security_manager(config_dir: Optional[Path] = None):
    """Create security manager with access manager integration."""
    from TimeLocker.security import AccessManager
    
    credential_manager = CredentialManager(config_dir=config_dir)
    security_service = SecurityService(credential_manager, config_dir=config_dir)
    access_manager = AccessManager(config_dir=config_dir)
    
    return security_service, access_manager


def _validate_session_for_operation(access_manager: 'AccessManager', operation: str, 
                                   repository_id: Optional[str] = None) -> bool:
    """
    Validate session for operation and create if needed.
    
    Args:
        access_manager: AccessManager instance
        operation: Operation being performed
        repository_id: Optional repository ID
        
    Returns:
        True if session is valid for operation
    """
    try:
        # Get or create session
        active_sessions = access_manager.get_active_sessions()
        session_id = None
        
        if active_sessions:
            # Use the most recent valid session
            for session in sorted(active_sessions, key=lambda s: s.last_accessed, reverse=True):
                if session.is_valid():
                    session_id = session.session_id
                    break
        
        if not session_id:
            # Create new session
            import os
            user_id = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
            from TimeLocker.security.access_manager import UserCredentials
            credentials = UserCredentials(user_id=user_id)
            
            auth_result = access_manager.authenticate_user(credentials)
            if auth_result.success:
                session_id = auth_result.session_id
            else:
                return False
        
        if not session_id:
            return False
            
        # Validate session for operation
        if not access_manager.validate_session(session_id):
            return False
            
        # Extend session
        access_manager.extend_session(session_id)
        
        return True
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Session validation error: {e}")
        return False


def setup_logging(verbose: bool = False, config_dir: Optional[Path] = None) -> None:
    """Set up logging configuration."""
    from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
    
    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO
    
    # Get appropriate XDG directory for log files
    log_dir = ConfigurationPathResolver.get_cache_directory() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file logging
    log_file = log_dir / "timelocker.log"
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root_logger.handlers):
            root_logger.addHandler(file_handler)
    except (OSError, PermissionError) as exc:
        logging.getLogger(__name__).debug("File logging disabled: %s", exc)


# Commands

@repos_app.command("list")
@with_error_handling("List Error")
@with_logging
def repos_list(
        show_status: Annotated[bool, typer.Option("--status", help="Show repository status indicators")] = True,
        show_performance: Annotated[bool, typer.Option("--performance", help="Show performance information")] = False,
        filter_status: Annotated[Optional[str], typer.Option("--filter-status", help="Filter by status (active, inactive, error)")] = None,
        filter_engine: Annotated[Optional[str], typer.Option("--filter-engine", help="Filter by engine (restic, rsync, rclone)")] = None,
        verbose: VerboseOption = False,
        json_output: JsonOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    List repository configurations with status indicators and performance information.
    
    Displays a comprehensive list of all configured repositories with:
    - Repository name, URI, and description
    - Repository type and backup engine
    - Status indicators (active, inactive, error)
    - Default repository marker
    - Performance metrics (with --performance flag)
    
    Examples:
        # List all repositories
        tl repos list
        
        # List with detailed information
        tl repos list --verbose
        
        # List with status and performance info
        tl repos list --status --performance
        
        # Filter by status
        tl repos list --filter-status active
        
        # Filter by engine
        tl repos list --filter-engine restic
        
        # JSON output
        tl repos list --json
    """
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        list_method = _get_service_method(manager, "list_repositories")
        repositories = []
        if list_method:
            try:
                # Build filter dictionary
                filters = {}
                if filter_status:
                    filters['status'] = filter_status
                if filter_engine:
                    filters['engine'] = filter_engine
                
                repositories = list_method(filters=filters if filters else None) or []
            except Exception as exc:
                logging.getLogger(__name__).debug("Service repository listing failed: %s", exc)
                raise
        
        if json_output:
            import json
            console.print(json.dumps(repositories, indent=2, default=str))
            return
        
        if not repositories:
            if filter_status or filter_engine:
                show_info_panel("No Matching Repositories", 
                              f"No repositories found matching the specified filters.")
            else:
                show_info_panel("No Repositories", "No repositories configured. Add one with 'tl repos add'.")
            return
        
        # Build table with appropriate columns
        table = Table(title="Configured Repositories")
        table.add_column("Name", style="cyan")
        
        if show_status:
            table.add_column("Status", justify="center")
        
        table.add_column("URI", style="magenta", overflow="fold")
        table.add_column("Description", overflow="fold")
        
        if verbose:
            table.add_column("Type", style="yellow")
            table.add_column("Engine", style="green")
        
        if show_performance:
            table.add_column("Last Validated", style="blue")
        
        table.add_column("Default", justify="center")
        
        # Populate table
        for repo in repositories:
            if isinstance(repo, dict):
                name = str(repo.get("name", "unknown"))
                uri = str(repo.get("uri", repo.get("location", "unknown")))
                description = str(repo.get("description", ""))
                is_default = repo.get("is_default", False)
                repo_type = str(repo.get("type", "N/A"))
                repo_engine = str(repo.get("engine", "N/A"))
                repo_status = str(repo.get("status", "unknown"))
                last_validated = repo.get("last_validated", "Never")
            else:
                name = str(getattr(repo, "name", "unknown"))
                uri = str(getattr(repo, "uri", getattr(repo, "location", "unknown")))
                description = str(getattr(repo, "description", ""))
                is_default = getattr(repo, "is_default", False)
                repo_type = str(getattr(repo, "type", "N/A"))
                repo_engine = str(getattr(repo, "engine", "N/A"))
                repo_status = str(getattr(repo, "status", "unknown"))
                last_validated = getattr(repo, "last_validated", "Never")
            
            # Build row data
            row_data = [name]
            
            # Add status indicator
            if show_status:
                status_icons = {
                    "active": "[green]●[/green]",
                    "inactive": "[yellow]●[/yellow]",
                    "error": "[red]●[/red]",
                    "validating": "[blue]●[/blue]"
                }
                status_str = repo_status.lower()
                status_icon = status_icons.get(status_str, "[white]●[/white]")
                row_data.append(status_icon)
            
            row_data.extend([uri, description])
            
            # Add verbose columns
            if verbose:
                row_data.extend([repo_type, repo_engine])
            
            # Add performance column
            if show_performance:
                row_data.append(str(last_validated))
            
            # Add default indicator
            default_indicator = "✓" if is_default else ""
            row_data.append(default_indicator)
            
            table.add_row(*row_data)
        
        console.print(table)
        
        # Show summary
        console.print(f"\n[dim]Total: {len(repositories)} repositories[/dim]")
        
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
        engine: Annotated[Optional[str], typer.Option("--engine", "-e", help="Backup engine (restic, rsync, rclone)")] = "restic",
        set_default: Annotated[bool, typer.Option("--set-default", help="Set as default repository")] = False,
        connect_existing: Annotated[bool, typer.Option("--connect-existing", help="Connect to existing repository if found")] = False,
        reinitialize: Annotated[bool, typer.Option("--reinitialize", help="Re-initialize existing repository (DESTRUCTIVE)")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Add a new repository with existing repository detection and handling.
    
    This command will:
    1. Validate the repository name and URI
    2. Check if a repository already exists at the specified location
    3. If existing repository found:
       - Offer to connect to it (preserves data)
       - Offer to re-initialize it (DESTROYS ALL DATA)
       - Or cancel the operation
    4. If no existing repository, create a new one
    
    Examples:
        # Add a new local repository
        tl repos add myrepo file:///path/to/repo
        
        # Add S3 repository with engine selection
        tl repos add s3repo s3:s3.amazonaws.com/bucket/path --engine restic
        
        # Connect to existing repository
        tl repos add existing file:///existing/repo --connect-existing
        
        # Re-initialize existing repository (DANGEROUS!)
        tl repos add reinit file:///old/repo --reinitialize
    """
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        # Validate repository name
        if not name:
            if interactive:
                name = Prompt.ask("Repository name")
            else:
                show_error_panel("Missing Parameter", "Repository name is required in non-interactive mode")
                raise typer.Exit(2)
        try:
            name = validate_repository_name(name)
        except ValidationError as e:
            show_error_panel("Invalid Repository Name", str(e))
            raise typer.Exit(2)
        
        # Validate repository URI
        if not uri:
            if interactive:
                uri = Prompt.ask("Repository URI")
            else:
                show_error_panel("Missing Parameter", "Repository URI is required in non-interactive mode")
                raise typer.Exit(2)
        try:
            uri = validate_required_string(uri, "Repository URI")
        except ValidationError as e:
            show_error_panel("Invalid Repository URI", str(e))
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
        
        # Validate engine selection
        valid_engines = ["restic", "rsync", "rclone"]
        if engine and engine.lower() not in valid_engines:
            show_error_panel("Invalid Engine", f"Engine must be one of: {', '.join(valid_engines)}")
            raise typer.Exit(1)

        manager = _get_service_manager_for_command(config_dir)
        backend_type = _determine_backend_from_uri(uri)
        
        # Check for existing repository at URI
        existing_repo_info = None
        detect_method = _get_service_method(manager, "detect_existing_repository")
        if detect_method:
            try:
                existing_repo_info = _call_service_method(detect_method, uri=uri)
                if existing_repo_info:
                    console.print(f"\n[yellow]⚠️  Existing repository detected at {uri}[/yellow]")
                    
                    # Display existing repository information
                    if isinstance(existing_repo_info, dict):
                        engine_type = existing_repo_info.get("engine_type", "unknown")
                        requires_creds = existing_repo_info.get("requires_credentials", False)
                        last_modified = existing_repo_info.get("last_modified", "unknown")
                        estimated_size = existing_repo_info.get("estimated_size")
                    else:
                        engine_type = getattr(existing_repo_info, "engine_type", "unknown")
                        requires_creds = getattr(existing_repo_info, "requires_credentials", False)
                        last_modified = getattr(existing_repo_info, "last_modified", "unknown")
                        estimated_size = getattr(existing_repo_info, "estimated_size", None)
                    
                    console.print(f"  Engine: {engine_type}")
                    console.print(f"  Last Modified: {last_modified}")
                    if estimated_size:
                        console.print(f"  Estimated Size: {_format_size(estimated_size)}")
                    if requires_creds:
                        console.print("  [yellow]Requires credentials to access[/yellow]")
                    
                    # Handle existing repository based on options
                    if reinitialize and connect_existing:
                        show_error_panel("Conflicting Options", 
                                       "Cannot use both --connect-existing and --reinitialize. Choose one.")
                        raise typer.Exit(1)
                    
                    if reinitialize:
                        # Require explicit confirmation for re-initialization
                        console.print("\n[red bold]⚠️  WARNING: REPOSITORY RE-INITIALIZATION WILL PERMANENTLY DELETE ALL DATA ⚠️[/red bold]")
                        console.print(f"[red]Repository URI: {uri}[/red]")
                        console.print(f"[red]Engine: {engine_type}[/red]")
                        if estimated_size:
                            console.print(f"[red]Size: {_format_size(estimated_size)}[/red]")
                        console.print(f"[red]Last modified: {last_modified}[/red]")
                        console.print("\n[red]This action cannot be undone. All backup data will be permanently lost.[/red]\n")
                        
                        if interactive:
                            confirmation = Prompt.ask(
                                "[red bold]Type 'DELETE ALL DATA' to confirm re-initialization[/red bold]"
                            )
                            if confirmation != "DELETE ALL DATA":
                                show_info_panel("Operation Cancelled", "Repository re-initialization cancelled.")
                                raise typer.Exit(0)
                        else:
                            show_error_panel("Confirmation Required", 
                                           "Re-initialization requires interactive confirmation. "
                                           "Type 'DELETE ALL DATA' when prompted.")
                            raise typer.Exit(1)
                        
                        console.print("[yellow]Proceeding with re-initialization...[/yellow]")
                        # Continue with creation (will reinitialize)
                        
                    elif connect_existing:
                        # Connect to existing repository
                        console.print("[cyan]Connecting to existing repository...[/cyan]")
                        
                        # Prompt for credentials if required
                        if requires_creds and not password:
                            if interactive:
                                password = Prompt.ask("Repository password", password=True)
                            else:
                                show_error_panel("Credentials Required", 
                                               "Existing repository requires password. Use --password option.")
                                raise typer.Exit(1)
                        
                        # Continue with connection
                        
                    else:
                        # Interactive choice
                        if interactive:
                            console.print("\n[bold]What would you like to do?[/bold]")
                            console.print("  1. Connect to existing repository (preserves data)")
                            console.print("  2. Re-initialize repository (DESTROYS ALL DATA)")
                            console.print("  3. Cancel operation")
                            
                            choice = Prompt.ask("Enter choice", choices=["1", "2", "3"], default="3")
                            
                            if choice == "3":
                                show_info_panel("Operation Cancelled", "Repository add cancelled.")
                                raise typer.Exit(0)
                            elif choice == "2":
                                # Require explicit confirmation
                                console.print("\n[red bold]⚠️  WARNING: REPOSITORY RE-INITIALIZATION WILL PERMANENTLY DELETE ALL DATA ⚠️[/red bold]")
                                confirmation = Prompt.ask(
                                    "[red bold]Type 'DELETE ALL DATA' to confirm[/red bold]"
                                )
                                if confirmation != "DELETE ALL DATA":
                                    show_info_panel("Operation Cancelled", "Repository re-initialization cancelled.")
                                    raise typer.Exit(0)
                                reinitialize = True
                            else:  # choice == "1"
                                connect_existing = True
                                if requires_creds and not password:
                                    password = Prompt.ask("Repository password", password=True)
                        else:
                            show_error_panel("Existing Repository", 
                                           f"Repository already exists at {uri}. "
                                           "Use --connect-existing to connect or --reinitialize to re-initialize.")
                            raise typer.Exit(1)
            except Exception as e:
                logging.getLogger(__name__).debug(f"Existing repository detection failed: {e}")
                # Continue with normal creation if detection fails

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

        config_service = None
        try:
            config_service = _create_config_service(config_dir)
            try:
                config_service.get_repository(name)
            except Exception:
                try:
                    from TimeLocker.config.configuration_schema import RepositoryConfig
                    repo_config = RepositoryConfig(
                        name=name,
                        location=uri,
                        description=description or f"{name} repository",
                        password=password if password else None
                    )
                    config_service.add_repository(repo_config)
                except Exception as repo_exc:
                    logging.getLogger(__name__).debug("Failed to persist repository via ConfigService: %s", repo_exc)
        except Exception as module_exc:
            logging.getLogger(__name__).debug("ConfigService unavailable for repository persistence: %s", module_exc)

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
                    if config_service:
                        try:
                            repository_obj = config_service.get_repository(name)
                        except Exception as repo_exc:
                            logging.getLogger(__name__).debug("Failed to load repository for credential storage: %s", repo_exc)
                    if config_service is None:
                        logging.getLogger(__name__).debug("Skipping credential storage; ConfigService unavailable.")
                        raise RuntimeError("ConfigService unavailable for credential storage")

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
                            config_manager=config_service.get_legacy_config_module(),
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
        show_status: Annotated[bool, typer.Option("--status", help="Show repository status and validation results")] = True,
        show_performance: Annotated[bool, typer.Option("--performance", help="Show performance metrics")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Display detailed repository information including status and metadata.
    
    Shows comprehensive information about a repository including:
    - Basic configuration (name, URI, description)
    - Repository type and backup engine
    - Default repository status
    - Validation status and last validation time
    - Custom metadata
    - Performance metrics (with --performance flag)
    
    Examples:
        # Show basic repository information
        tl repos show myrepo
        
        # Show with performance metrics
        tl repos show myrepo --performance
        
        # Show without status information
        tl repos show myrepo --no-status
    """
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        show_method = _get_service_method(manager, "get_repository_by_name")
        repository_info = None
        service_error = None
        if show_method:
            try:
                repository_info = _call_service_method(show_method, name=name, repository_name=name, repository=name)
            except Exception as exc:
                logging.getLogger(__name__).debug("Service repository lookup failed: %s", exc)
                service_error = exc
                repository_info = None
        if repository_info is None:
            config_manager = ConfigurationManager(config_dir=config_dir)
            try:
                repository_info = config_manager.get_repository(name)
            except ConfigurationError:
                repository_info = None
        
        if repository_info is None:
            if service_error:
                not_found_message = f"Repository '{name}' lookup failed: {service_error}"
            else:
                not_found_message = f"Repository '{name}' was not found in configuration or services."
            show_error_panel("Repository Not Found", not_found_message)
            raise typer.Exit(1)
        
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
            repo_status = repository_info.get("status", "unknown")
            last_validated = repository_info.get("last_validated", "Never")
            validation_result = repository_info.get("validation_result", {})
            usage_stats = repository_info.get("usage_stats", {})
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
            repo_status = getattr(repository_info, "status", "unknown")
            last_validated = getattr(repository_info, "last_validated", "Never")
            validation_result = getattr(repository_info, "validation_result", {})
            usage_stats = getattr(repository_info, "usage_stats", {})
        
        # Build display content
        panel_lines = []
        
        # Basic information
        panel_lines.append("[bold cyan]Basic Information[/bold cyan]")
        panel_lines.append(f"[bold]Name:[/bold] {repo_name}")
        panel_lines.append(f"[bold]URI:[/bold] {repo_uri}")
        if repo_description:
            panel_lines.append(f"[bold]Description:[/bold] {repo_description}")
        panel_lines.append(f"[bold]Type:[/bold] {repo_type}")
        panel_lines.append(f"[bold]Engine:[/bold] {repo_engine}")
        panel_lines.append(f"[bold]Default:[/bold] {'✓ Yes' if is_default else 'No'}")
        
        # Status information
        if show_status:
            panel_lines.append("\n[bold cyan]Status Information[/bold cyan]")
            
            # Color-code status
            status_colors = {
                "active": "green",
                "inactive": "yellow",
                "error": "red",
                "validating": "blue"
            }
            status_str = str(repo_status).lower()
            status_color = status_colors.get(status_str, "white")
            panel_lines.append(f"[bold]Status:[/bold] [{status_color}]{repo_status}[/{status_color}]")
            panel_lines.append(f"[bold]Last Validated:[/bold] {last_validated}")
            
            # Show validation results if available
            if validation_result:
                if isinstance(validation_result, dict):
                    val_success = validation_result.get("success", False)
                    connectivity = validation_result.get("connectivity_status", "unknown")
                    integrity = validation_result.get("integrity_status", "unknown")
                else:
                    val_success = getattr(validation_result, "success", False)
                    connectivity = getattr(validation_result, "connectivity_status", "unknown")
                    integrity = getattr(validation_result, "integrity_status", "unknown")
                
                val_color = "green" if val_success else "red"
                panel_lines.append(f"[bold]Validation:[/bold] [{val_color}]{'Passed' if val_success else 'Failed'}[/{val_color}]")
                panel_lines.append(f"  Connectivity: {connectivity}")
                panel_lines.append(f"  Integrity: {integrity}")
        
        # Timestamps
        panel_lines.append("\n[bold cyan]Timestamps[/bold cyan]")
        panel_lines.append(f"[bold]Created:[/bold] {created_at}")
        panel_lines.append(f"[bold]Updated:[/bold] {updated_at}")
        
        # Performance metrics
        if show_performance and validation_result:
            if isinstance(validation_result, dict):
                perf_metrics = validation_result.get("performance_metrics", {})
            else:
                perf_metrics = getattr(validation_result, "performance_metrics", {})
            
            if perf_metrics:
                panel_lines.append("\n[bold cyan]Performance Metrics[/bold cyan]")
                for metric, value in perf_metrics.items():
                    if isinstance(value, float):
                        panel_lines.append(f"[bold]{metric}:[/bold] {value:.2f}s")
                    else:
                        panel_lines.append(f"[bold]{metric}:[/bold] {value}")
        
        # Usage statistics
        if usage_stats and isinstance(usage_stats, dict) and usage_stats:
            panel_lines.append("\n[bold cyan]Usage Statistics[/bold cyan]")
            for key, value in usage_stats.items():
                panel_lines.append(f"[bold]{key}:[/bold] {value}")
        
        # Custom metadata
        if repo_metadata and isinstance(repo_metadata, dict) and repo_metadata:
            panel_lines.append("\n[bold cyan]Custom Metadata[/bold cyan]")
            for key, value in repo_metadata.items():
                panel_lines.append(f"[bold]{key}:[/bold] {value}")
        
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
    logger = logging.getLogger(__name__)
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
        remove_metadata: Annotated[Optional[List[str]], typer.Option("--remove-metadata", help="Remove specific metadata keys")] = None,
        clear_metadata: Annotated[bool, typer.Option("--clear-metadata", help="Clear all custom metadata")] = False,
        set_default: Annotated[bool, typer.Option("--set-default", help="Set as default repository")] = False,
        unset_default: Annotated[bool, typer.Option("--unset-default", help="Remove default repository status")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Update repository metadata and configuration.
    
    Allows updating various repository properties including:
    - Description
    - Custom metadata (add, update, or remove)
    - Default repository status
    
    Examples:
        # Update description
        tl repos update myrepo --description "Production backup repository"
        
        # Add/update metadata
        tl repos update myrepo --metadata owner=admin --metadata env=production
        
        # Remove specific metadata
        tl repos update myrepo --remove-metadata owner --remove-metadata env
        
        # Clear all metadata
        tl repos update myrepo --clear-metadata
        
        # Set as default repository
        tl repos update myrepo --set-default
        
        # Remove default status
        tl repos update myrepo --unset-default
    """
    setup_logging(verbose, config_dir)
    try:
        # Validate conflicting options
        if set_default and unset_default:
            show_error_panel("Conflicting Options", 
                           "Cannot use both --set-default and --unset-default. Choose one.")
            raise typer.Exit(1)
        
        config_manager = ConfigurationManager(config_dir=config_dir)
        manager = _get_service_manager_for_command(config_dir)
        
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
            updates.append("description")
        
        # Handle metadata updates
        if clear_metadata:
            if hasattr(repo_config, 'metadata'):
                repo_config.metadata = {}
            elif isinstance(repo_config, dict):
                repo_config['metadata'] = {}
            updates.append("cleared all metadata")
        
        # Remove specific metadata keys
        if remove_metadata:
            removed_keys = []
            for key in remove_metadata:
                if hasattr(repo_config, 'metadata') and repo_config.metadata:
                    if key in repo_config.metadata:
                        del repo_config.metadata[key]
                        removed_keys.append(key)
                elif isinstance(repo_config, dict) and 'metadata' in repo_config:
                    if key in repo_config['metadata']:
                        del repo_config['metadata'][key]
                        removed_keys.append(key)
            
            if removed_keys:
                updates.append(f"removed metadata keys: {', '.join(removed_keys)}")
        
        # Add/update metadata
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
            
            updates.append(f"added/updated metadata ({len(metadata_dict)} items)")
        
        # Handle default repository status
        if set_default:
            default_method = _get_service_method(manager, "set_default_repository")
            if default_method:
                _call_service_method(default_method, name=name, repository=name, repository_name=name)
            else:
                config_manager.set_default_repository(name)
            updates.append("set as default repository")
        
        if unset_default:
            # Check if this is the default repository
            is_default = False
            if hasattr(repo_config, 'is_default'):
                is_default = repo_config.is_default
            elif isinstance(repo_config, dict):
                is_default = repo_config.get('is_default', False)
            
            if is_default:
                clear_default_method = _get_service_method(manager, "clear_default_repository")
                if clear_default_method:
                    _call_service_method(clear_default_method)
                else:
                    # Clear default flag
                    if hasattr(repo_config, 'is_default'):
                        repo_config.is_default = False
                    elif isinstance(repo_config, dict):
                        repo_config['is_default'] = False
                updates.append("removed default repository status")
            else:
                console.print(f"[yellow]Repository '{name}' is not the default repository.[/yellow]")
        
        if not updates:
            show_info_panel("No Updates", 
                          "No updates specified. Use --description, --metadata, --set-default, or other options to update repository.")
            raise typer.Exit(0)
        
        # Save updated configuration
        config = config_manager.get_config()
        if config and hasattr(config, 'repositories'):
            config.repositories[name] = repo_config
            config_manager.save_config(config)
        
        # Display update summary
        updates_str = "\n  • ".join(updates)
        show_success_panel("Repository Updated", 
                         f"Repository '{name}' updated successfully.\n\nUpdates:\n  • {updates_str}")
        
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




@repos_app.command("edit")
@with_error_handling("Edit Error")
@with_logging
def repos_edit(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        uri: Annotated[Optional[str], typer.Option("--uri", help="Update repository URI")] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Update repository description")] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Update repository password")] = None,
        update_credentials: Annotated[bool, typer.Option("--update-credentials", help="Update backend credentials interactively")] = False,
        interactive: Annotated[bool, typer.Option("--interactive/--no-interactive", help="Enable interactive mode for all fields")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Edit repository configuration with interactive prompts.
    
    This command allows you to modify repository settings including:
    - Repository URI
    - Description
    - Password
    - Backend credentials (for cloud repositories)
    
    In interactive mode (default when no options provided), the command will:
    - Display current values for all settings
    - Prompt for new values (press Enter to keep current value)
    - Allow credential management for cloud backends
    
    Examples:
        # Interactive edit (shows current values, prompts for changes)
        tl repos edit myrepo
        
        # Update specific fields non-interactively
        tl repos edit myrepo --description "Updated description"
        
        # Update URI
        tl repos edit myrepo --uri s3:s3.amazonaws.com/new-bucket/path
        
        # Update credentials for cloud repository
        tl repos edit myrepo --update-credentials
        
        # Force interactive mode even with options
        tl repos edit myrepo --description "New desc" --interactive
    """
    setup_logging(verbose, config_dir)
    is_interactive = sys.stdin.isatty() if interactive is None else interactive
    
    try:
        config_manager = ConfigurationManager(config_dir=config_dir)
        manager = _get_service_manager_for_command(config_dir)
        
        # Get existing repository configuration
        try:
            repo_config = config_manager.get_repository(name)
        except ConfigurationError:
            show_error_panel("Repository Not Found", f"Repository '{name}' not found in configuration.")
            raise typer.Exit(1)
        
        # Extract current values
        if isinstance(repo_config, dict):
            current_uri = repo_config.get('uri') or repo_config.get('location', '')
            current_description = repo_config.get('description', '')
            current_password = repo_config.get('password')
            has_backend_creds = repo_config.get('has_backend_credentials', False)
        else:
            current_uri = getattr(repo_config, 'uri', None) or getattr(repo_config, 'location', '')
            current_description = getattr(repo_config, 'description', '')
            current_password = getattr(repo_config, 'password', None)
            has_backend_creds = getattr(repo_config, 'has_backend_credentials', False)
        
        # Determine backend type
        backend_type = _determine_backend_from_uri(current_uri)
        
        # Track what was updated
        updates = []
        
        # Interactive mode: show current values and prompt for changes
        if is_interactive and not any([uri, description, password, update_credentials]):
            console.print(f"\n[bold cyan]Editing Repository: {name}[/bold cyan]\n")
            console.print("[dim]Press Enter to keep current value, or type new value[/dim]\n")
            
            # Display and prompt for URI
            console.print(f"[bold]Current URI:[/bold] {current_uri}")
            new_uri = Prompt.ask("New URI", default="")
            if new_uri and new_uri != current_uri:
                uri = new_uri
            
            # Display and prompt for description
            console.print(f"\n[bold]Current Description:[/bold] {current_description or '(none)'}")
            new_description = Prompt.ask("New Description", default="")
            if new_description and new_description != current_description:
                description = new_description
            
            # Display and prompt for password
            if current_password:
                console.print(f"\n[bold]Current Password:[/bold] ••••••••")
            else:
                console.print(f"\n[bold]Current Password:[/bold] (none)")
            
            update_password = Confirm.ask("Update password?", default=False)
            if update_password:
                password = Prompt.ask("New Password", password=True)
            
            # Prompt for credential management if cloud backend
            if backend_type in ["s3", "b2", "azure", "gcs"]:
                console.print(f"\n[bold]Backend Credentials:[/bold] {_backend_display_name(backend_type)}")
                if has_backend_creds:
                    console.print("[green]Credentials stored[/green]")
                else:
                    console.print("[yellow]No credentials stored[/yellow]")
                
                update_credentials = Confirm.ask("Update backend credentials?", default=False)
        
        # Update URI if provided
        if uri and uri != current_uri:
            # Validate new URI
            try:
                uri = validate_required_string(uri, "Repository URI")
            except ValidationError as e:
                show_error_panel("Invalid URI", str(e))
                raise typer.Exit(1)
            
            # Validate URI format
            if "://" in uri:
                parsed = urlparse(uri)
                scheme = (parsed.scheme or "").lower()
                allowed_schemes = {"file", "s3", "b2", "azure", "gs", "swift", "rest", "rclone", "sftp"}
                if scheme not in allowed_schemes:
                    show_error_panel("Invalid URI", f"Unsupported URI scheme: '{scheme}'")
                    raise typer.Exit(1)
            
            if isinstance(repo_config, dict):
                repo_config['uri'] = uri
                repo_config.pop('location', None)  # Remove old location field if exists
            else:
                repo_config.uri = uri
            
            updates.append(f"URI updated to: {uri}")
            
            # Update backend type if changed
            new_backend_type = _determine_backend_from_uri(uri)
            if new_backend_type != backend_type:
                backend_type = new_backend_type
                updates.append(f"Backend type changed to: {_backend_display_name(backend_type) if backend_type else 'local'}")
        
        # Update description if provided
        if description is not None and description != current_description:
            if isinstance(repo_config, dict):
                repo_config['description'] = description
            else:
                repo_config.description = description
            updates.append("Description updated")
        
        # Update password if provided
        if password is not None:
            if isinstance(repo_config, dict):
                repo_config['password'] = password
            else:
                repo_config.password = password
            updates.append("Password updated")
        
        # Save configuration if any updates were made
        if updates:
            config = config_manager.get_config()
            if config and hasattr(config, 'repositories'):
                config.repositories[name] = repo_config
                config_manager.save_config(config)
        
        # Handle credential updates
        if update_credentials:
            if not backend_type or backend_type not in ["s3", "b2", "azure", "gcs"]:
                show_info_panel("No Backend Credentials", 
                              "This repository type does not support backend credential storage.")
            else:
                console.print(f"\n[cyan]Updating {_backend_display_name(backend_type)} credentials...[/cyan]")
                
                credential_manager = _create_credential_manager(config_dir)
                
                # Prompt for credentials based on backend type
                if backend_type == "s3":
                    access_key = Prompt.ask("AWS Access Key ID")
                    secret_key = Prompt.ask("AWS Secret Access Key", password=True)
                    region = Prompt.ask("AWS Region", default="")
                    insecure_tls = Confirm.ask("Allow insecure TLS?", default=False)
                    
                    credentials_payload = {
                        "access_key_id": access_key,
                        "secret_access_key": secret_key,
                    }
                    if region:
                        credentials_payload["region"] = region
                    if insecure_tls:
                        credentials_payload["insecure_tls"] = True
                    
                    # Store credentials
                    success = store_backend_credentials_helper(
                        repository_name=name,
                        backend_type=backend_type,
                        backend_name=_backend_display_name(backend_type),
                        credentials_dict=credentials_payload,
                        cred_mgr=credential_manager,
                        config_manager=config_manager,
                        repository_config=_repository_config_to_dict(repo_config, name),
                        console=console,
                        logger=logging.getLogger(__name__),
                        allow_prompt=is_interactive,
                    )
                    
                    if success:
                        updates.append(f"{_backend_display_name(backend_type)} credentials updated")
                    else:
                        show_error_panel("Credential Update Failed", 
                                       f"Failed to update {_backend_display_name(backend_type)} credentials")
                        raise typer.Exit(1)
                else:
                    show_info_panel("Not Implemented", 
                                  f"Credential management for {_backend_display_name(backend_type)} is not yet implemented.")
        
        # Display results
        if not updates:
            show_info_panel("No Changes", 
                          "No changes were made to the repository configuration.")
            raise typer.Exit(0)
        
        updates_str = "\n  • ".join(updates)
        show_success_panel("Repository Updated", 
                         f"Repository '{name}' updated successfully.\n\nChanges:\n  • {updates_str}")
        
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Edit operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Edit Error", f"Failed to edit repository '{name}': {e}")
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

        # Get repository configuration to check URI
        manager = _get_service_manager_for_command(config_dir)
        config_manager = ConfigurationManager(config_dir=config_dir)
        
        try:
            repo_config = config_manager.get_repository(name)
            repo_uri = repository or repo_config.get("uri")
        except Exception as e:
            show_error_panel("Configuration Error", f"Repository '{name}' not found in configuration.")
            raise typer.Exit(1)
        
        # Check if directory exists for file:// URIs
        if repo_uri and repo_uri.startswith("file://"):
            repo_path = Path(repo_uri.replace("file://", ""))
            if not repo_path.exists():
                show_error_panel(
                    "Directory Not Found",
                    f"Repository directory does not exist: {repo_path}\n\n"
                    f"Create it with: mkdir -p {repo_path}"
                )
                raise typer.Exit(1)
            if not os.access(repo_path, os.W_OK):
                show_error_panel(
                    "Permission Denied",
                    f"No write permission for directory: {repo_path}\n\n"
                    f"Check permissions with: ls -la {repo_path.parent}"
                )
                raise typer.Exit(1)
        
        # Prompt for password if not provided and in interactive mode
        if not password and interactive:
            from rich.prompt import Prompt
            password = Prompt.ask("Enter password for repository", password=True)
            password_confirm = Prompt.ask("Confirm password", password=True)
            if password != password_confirm:
                show_error_panel("Password Mismatch", "Passwords do not match.")
                raise typer.Exit(1)
        elif not password and not interactive:
            show_error_panel("Password Required", "Password must be provided with --password in non-interactive mode.")
            raise typer.Exit(1)

        init_method = _get_service_method(manager, "initialize_repository")
        if not init_method:
            show_error_panel("Not Implemented", "Repository initialization is not available in this build.")
            raise typer.Exit(1)

        try:
            result = _call_service_method(
                    init_method,
                    name=name,
                    repository=repository or name,
                    repository_uri=repository,
                    repository_name=name,
                    password=password
            )
        except Exception as e:
            # Capture the actual error from the service
            error_msg = str(e)
            if verbose:
                console.print_exception()
            show_error_panel(
                "Initialization Failed",
                f"Failed to initialize repository '{name}'.",
                [error_msg]
            )
            raise typer.Exit(1)

        already_initialized = False
        success = True
        errors = None
        error_message = None
        
        # Log the raw result for debugging
        if verbose:
            console.print(f"[dim]Debug: init result = {result}[/dim]")
            console.print(f"[dim]Debug: result type = {type(result)}[/dim]")
        
        if isinstance(result, dict):
            success = result.get("success", True)
            already_initialized = result.get("already_initialized", False)
            errors = result.get("errors")
            error_message = result.get("error") or result.get("message")
            
            if verbose:
                console.print(f"[dim]Debug: success = {success}[/dim]")
                console.print(f"[dim]Debug: errors = {errors}[/dim]")
                console.print(f"[dim]Debug: error_message = {error_message}[/dim]")
        else:
            success = bool(result)

        if success and already_initialized:
            message = f"Repository '{name}' is already initialized."
            show_info_panel("Already Initialized", message)
            return

        if success:
            show_success_panel("Repository Initialized", f"Repository '{name}' initialized successfully.")
        else:
            # Build detailed error message
            details = []
            if errors:
                if isinstance(errors, list):
                    details.extend(errors)
                else:
                    details.append(str(errors))
            if error_message and error_message not in details:
                details.append(str(error_message))
            
            # If still no details, add a helpful message
            if not details:
                details.append("The repository location may not be accessible.")
                details.append("Check that the directory exists and you have write permissions.")
                details.append("For remote repositories, verify network connectivity and credentials.")
            
            show_error_panel("Initialization Failed", f"Failed to initialize repository '{name}'.", details)
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
            success = result.get("status") in (None, "success", "OK", True)
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
                    prune_success = prune_result.get("status") in (None, "success", "OK", True)
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
            success = status in (None, "success", "OK", True)
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


@repos_app.command("prune")
@with_error_handling("Prune Error")
@with_logging
def repos_prune(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        dry_run: DryRunOption = False,
        repository: Annotated[
            Optional[str], typer.Option("--repository", "-r", help="Repository URI override", autocompletion=repository_uri_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password if required")] = None,
        max_unused: Annotated[Optional[str], typer.Option("--max-unused", help="Maximum unused data to keep (e.g., '5%', '10G')")] = None,
        max_repack_size: Annotated[Optional[str], typer.Option("--max-repack-size", help="Maximum size to repack (e.g., '1G')")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Optimize repository storage by removing unreferenced data.
    
    This command performs repository maintenance by:
    - Removing unreferenced data blocks
    - Repacking repository data for better compression
    - Optimizing storage usage
    - Reclaiming disk space
    
    The prune operation is safe and will not remove any data that is still
    referenced by existing snapshots. Use --dry-run to preview what would
    be removed without making actual changes.
    
    Examples:
        # Prune repository (preview mode)
        tl repos prune myrepo --dry-run
        
        # Prune repository and reclaim space
        tl repos prune myrepo
        
        # Prune with size limits
        tl repos prune myrepo --max-unused 5% --max-repack-size 1G
        
        # Verbose output with progress
        tl repos prune myrepo --verbose
    """
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        prune_method = _get_service_method(manager, "prune_repository")
        
        if not prune_method:
            show_error_panel("Not Implemented", "Repository prune is not available in this build.")
            raise typer.Exit(1)
        
        # Show what we're doing
        if dry_run:
            console.print(f"[cyan]Analyzing repository '{name}' (dry run)...[/cyan]")
        else:
            console.print(f"[cyan]Pruning repository '{name}'...[/cyan]")
        
        # Execute prune with progress indicator
        progress_service = get_progress_service(console=console)
        with progress_service.spinner("Pruning..." if not dry_run else "Analyzing..."):
            
            # Build prune parameters
            prune_params = {
                "name": name,
                "repository": repository or name,
                "repository_uri": repository,
                "repository_name": name,
                "dry_run": dry_run,
                "password": password
            }
            
            if max_unused:
                prune_params["max_unused"] = max_unused
            if max_repack_size:
                prune_params["max_repack_size"] = max_repack_size
            
            # Call prune method
            result = _call_service_method(prune_method, **prune_params)
        
        # Parse result
        if isinstance(result, dict):
            success = result.get("success", True)
            space_freed = result.get("space_freed", 0)
            packs_removed = result.get("packs_removed", 0)
            errors = result.get("errors")
            warnings = result.get("warnings", [])
        else:
            success = getattr(result, "success", True)
            space_freed = getattr(result, "space_freed", 0)
            packs_removed = getattr(result, "packs_removed", 0)
            errors = getattr(result, "errors", None)
            warnings = getattr(result, "warnings", [])
        
        # Display results
        if success:
            # Build success message
            message_lines = []
            message_lines.append(f"[bold]Repository:[/bold] {name}")
            
            if dry_run:
                message_lines.append(f"[bold]Mode:[/bold] Dry run (no changes made)")
            else:
                message_lines.append(f"[bold]Mode:[/bold] Prune completed")
            
            if space_freed:
                message_lines.append(f"[bold]Space Freed:[/bold] {_format_size(space_freed)}")
            
            if packs_removed:
                message_lines.append(f"[bold]Packs Removed:[/bold] {packs_removed}")
            
            # Show warnings if any
            if warnings:
                message_lines.append("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in warnings:
                    message_lines.append(f"  • {warning}")
            
            title = "Prune Analysis Complete" if dry_run else "Prune Complete"
            show_success_panel(title, "\n".join(message_lines))
        else:
            # Build error message
            error_details = errors if isinstance(errors, list) else [errors] if errors else None
            show_error_panel("Prune Failed", f"Failed to prune repository '{name}'.", error_details)
            raise typer.Exit(1)
            
    except ConfigurationError as e:
        show_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Prune operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Prune Error", f"Failed to prune repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_app.command("validate")
@with_error_handling("Validation Error")
@with_logging
def repos_validate(
        name: Annotated[str, typer.Argument(help="Repository name to validate", autocompletion=repository_name_completer)],
        check_connectivity: Annotated[bool, typer.Option("--connectivity/--no-connectivity", help="Check repository connectivity")] = True,
        check_integrity: Annotated[bool, typer.Option("--integrity/--no-integrity", help="Check repository integrity")] = True,
        show_metrics: Annotated[bool, typer.Option("--metrics", help="Show performance metrics")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Validate repository connectivity and integrity.
    
    This command performs comprehensive validation of a repository including:
    - Connectivity testing (network/local access)
    - Integrity verification (repository structure and data)
    - Performance metrics (validation duration, response times)
    - Recommendations for improvements
    
    Examples:
        # Full validation with all checks
        tl repos validate myrepo
        
        # Connectivity check only
        tl repos validate myrepo --no-integrity
        
        # Show detailed performance metrics
        tl repos validate myrepo --metrics --verbose
    """
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        validate_method = _get_service_method(manager, "validate_repository")
        
        if not validate_method:
            show_error_panel("Not Implemented", "Repository validation is not available in this build.")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Validating repository '{name}'...[/cyan]")
        
        progress_service = get_progress_service(console=console)
        with progress_service.spinner("Validating..."):
            # Call validation method
            result = _call_service_method(
                validate_method,
                name=name,
                repository=name,
                repository_name=name,
                check_connectivity=check_connectivity,
                check_integrity=check_integrity
            )
        
        # Parse validation result
        if isinstance(result, dict):
            success = result.get("success", False)
            connectivity_status = result.get("connectivity_status", "unknown")
            integrity_status = result.get("integrity_status", "unknown")
            error_details = result.get("error_details", [])
            performance_metrics = result.get("performance_metrics", {})
            recommendations = result.get("recommendations", [])
        else:
            success = getattr(result, "success", False)
            connectivity_status = getattr(result, "connectivity_status", "unknown")
            integrity_status = getattr(result, "integrity_status", "unknown")
            error_details = getattr(result, "error_details", [])
            performance_metrics = getattr(result, "performance_metrics", {})
            recommendations = getattr(result, "recommendations", [])
        
        # Display results
        if success:
            # Build success message
            status_lines = []
            status_lines.append(f"[bold]Repository:[/bold] {name}")
            status_lines.append(f"[bold]Status:[/bold] [green]Valid[/green]")
            
            if check_connectivity:
                status_lines.append(f"[bold]Connectivity:[/bold] [green]{connectivity_status}[/green]")
            
            if check_integrity:
                status_lines.append(f"[bold]Integrity:[/bold] [green]{integrity_status}[/green]")
            
            # Show performance metrics if requested
            if show_metrics and performance_metrics:
                status_lines.append("\n[bold]Performance Metrics:[/bold]")
                for metric, value in performance_metrics.items():
                    if isinstance(value, float):
                        status_lines.append(f"  {metric}: {value:.2f}s")
                    else:
                        status_lines.append(f"  {metric}: {value}")
            
            # Show recommendations if any
            if recommendations:
                status_lines.append("\n[bold yellow]Recommendations:[/bold yellow]")
                for rec in recommendations:
                    status_lines.append(f"  • {rec}")
            
            show_success_panel("Validation Successful", "\n".join(status_lines))
        else:
            # Build error message
            error_lines = []
            error_lines.append(f"[bold]Repository:[/bold] {name}")
            error_lines.append(f"[bold]Status:[/bold] [red]Invalid[/red]")
            
            if check_connectivity:
                status_color = "red" if connectivity_status.lower() in ["disconnected", "failed", "error"] else "yellow"
                error_lines.append(f"[bold]Connectivity:[/bold] [{status_color}]{connectivity_status}[/{status_color}]")
            
            if check_integrity:
                status_color = "red" if integrity_status.lower() in ["corrupted", "failed", "error"] else "yellow"
                error_lines.append(f"[bold]Integrity:[/bold] [{status_color}]{integrity_status}[/{status_color}]")
            
            if error_details:
                error_lines.append("\n[bold]Issues Found:[/bold]")
                for error in error_details:
                    error_lines.append(f"  • {error}")
            
            if recommendations:
                error_lines.append("\n[bold yellow]Recommendations:[/bold yellow]")
                for rec in recommendations:
                    error_lines.append(f"  • {rec}")
            
            show_error_panel("Validation Failed", "\n".join(error_lines))
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Validation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Validation Error", f"Failed to validate repository '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_app.command("validate-all")
@with_error_handling("Validation Error")
@with_logging
def repos_validate_all(
        check_connectivity: Annotated[bool, typer.Option("--connectivity/--no-connectivity", help="Check repository connectivity")] = True,
        check_integrity: Annotated[bool, typer.Option("--integrity/--no-integrity", help="Check repository integrity")] = True,
        show_metrics: Annotated[bool, typer.Option("--metrics", help="Show performance metrics")] = False,
        continue_on_error: Annotated[bool, typer.Option("--continue-on-error", help="Continue validation even if some repositories fail")] = True,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Validate all configured repositories with batch processing and progress reporting.
    
    This command validates all repositories concurrently (up to 3 parallel validations)
    and provides a comprehensive report of validation results.
    
    Examples:
        # Validate all repositories
        tl repos validate-all
        
        # Validate connectivity only for all repositories
        tl repos validate-all --no-integrity
        
        # Show detailed metrics for all repositories
        tl repos validate-all --metrics --verbose
        
        # Stop on first failure
        tl repos validate-all --no-continue-on-error
    """
    setup_logging(verbose, config_dir)
    try:
        manager = _get_service_manager_for_command(config_dir)
        
        # Get list of repositories
        list_method = _get_service_method(manager, "list_repositories")
        if not list_method:
            show_error_panel("Not Implemented", "Repository listing is not available in this build.")
            raise typer.Exit(1)
        
        repositories = list_method() or []
        
        if not repositories:
            show_info_panel("No Repositories", "No repositories configured to validate.")
            return
        
        console.print(f"[cyan]Validating {len(repositories)} repositories...[/cyan]\n")
        
        # Validate repositories with progress tracking
        validate_method = _get_service_method(manager, "batch_validate_repositories")
        
        results = {}
        failed_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            if validate_method:
                # Use batch validation if available
                task = progress.add_task("Validating repositories...", total=len(repositories))
                
                repo_names = [r.get("name") if isinstance(r, dict) else getattr(r, "name") for r in repositories]
                batch_results = _call_service_method(
                    validate_method,
                    repository_names=repo_names,
                    check_connectivity=check_connectivity,
                    check_integrity=check_integrity
                )
                
                if isinstance(batch_results, dict):
                    results = batch_results
                
                progress.update(task, completed=len(repositories))
            else:
                # Fall back to individual validation
                validate_single = _get_service_method(manager, "validate_repository")
                if not validate_single:
                    show_error_panel("Not Implemented", "Repository validation is not available in this build.")
                    raise typer.Exit(1)
                
                task = progress.add_task("Validating repositories...", total=len(repositories))
                
                for repo in repositories:
                    repo_name = repo.get("name") if isinstance(repo, dict) else getattr(repo, "name")
                    
                    try:
                        result = _call_service_method(
                            validate_single,
                            name=repo_name,
                            repository=repo_name,
                            repository_name=repo_name,
                            check_connectivity=check_connectivity,
                            check_integrity=check_integrity
                        )
                        results[repo_name] = result
                        
                        if isinstance(result, dict):
                            success = result.get("success", False)
                        else:
                            success = getattr(result, "success", False)
                        
                        if not success:
                            failed_count += 1
                            if not continue_on_error:
                                break
                    except Exception as e:
                        logging.getLogger(__name__).error(f"Validation failed for {repo_name}: {e}")
                        results[repo_name] = {"success": False, "error_details": [str(e)]}
                        failed_count += 1
                        if not continue_on_error:
                            break
                    
                    progress.update(task, advance=1)
        
        # Display results summary
        console.print("\n[bold]Validation Results:[/bold]\n")
        
        table = Table(title="Repository Validation Summary")
        table.add_column("Repository", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Connectivity", justify="center")
        table.add_column("Integrity", justify="center")
        if show_metrics:
            table.add_column("Duration", justify="right")
        
        for repo_name, result in results.items():
            if isinstance(result, dict):
                success = result.get("success", False)
                connectivity = result.get("connectivity_status", "unknown")
                integrity = result.get("integrity_status", "unknown")
                metrics = result.get("performance_metrics", {})
            else:
                success = getattr(result, "success", False)
                connectivity = getattr(result, "connectivity_status", "unknown")
                integrity = getattr(result, "integrity_status", "unknown")
                metrics = getattr(result, "performance_metrics", {})
            
            status_icon = "✓" if success else "✗"
            status_color = "green" if success else "red"
            
            row_data = [
                repo_name,
                f"[{status_color}]{status_icon}[/{status_color}]",
                connectivity,
                integrity
            ]
            
            if show_metrics:
                duration = metrics.get("validation_duration", 0)
                row_data.append(f"{duration:.2f}s" if isinstance(duration, (int, float)) else str(duration))
            
            table.add_row(*row_data)
        
        console.print(table)
        
        # Summary statistics
        total = len(results)
        passed = total - failed_count
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total: {total}")
        console.print(f"  [green]Passed: {passed}[/green]")
        if failed_count > 0:
            console.print(f"  [red]Failed: {failed_count}[/red]")
        
        if failed_count > 0:
            raise typer.Exit(1)
        else:
            show_success_panel("All Validations Passed", f"Successfully validated {total} repositories.")
            
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Batch validation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Validation Error", f"Failed to validate repositories: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
