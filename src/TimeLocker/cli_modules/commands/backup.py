"""
Backup operation commands.

This module contains CLI commands for creating and verifying backups.
"""

import sys
import asyncio
import logging
from typing import Optional, List, Annotated
from pathlib import Path

import typer
import click
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt

# Import from TimeLocker.cli module (cli.py) to avoid circular imports during transition
from TimeLocker import cli as _cli_module

# Import required functions and objects
show_success_panel = _cli_module.show_success_panel
show_error_panel = _cli_module.show_error_panel
setup_logging = _cli_module.setup_logging
_get_service_method = _cli_module._get_service_method
_call_service_method = _cli_module._call_service_method
_get_service_manager_for_command = _cli_module._get_service_manager_for_command
_create_configuration_module = _cli_module._create_configuration_module
console = _cli_module.console

# Import from TimeLocker package
from TimeLocker.cli_services import get_cli_service_manager, CLIBackupRequest
from TimeLocker.completion import (
    file_path_completer,
    repository_completer,
    selection_name_completer,
    snapshot_id_completer,
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import RepositoryNotFoundError
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format
from TimeLocker.utils import get_progress_service, ProgressTemplates

# Create Typer app for backup operations
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

backup_app = typer.Typer(
    help="Backup operations",
    no_args_is_help=True,
    context_settings=CLI_CONTEXT_SETTINGS
)
backup_app.info.options_metavar = "⟨OPTIONS⟩"


@backup_app.command("create")
def backup_create(
        sources: Annotated[Optional[List[Path]], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)] = None,
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        selection: Annotated[Optional[str], typer.Option("--selection", "-s", help="Use configured data selection template", autocompletion=selection_name_completer)] = None,
        name: Annotated[Optional[str], typer.Option("--name", "-n", help="Backup name")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Backup tags")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be backed up without actually performing backup")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """
    Create a backup using data selection templates or direct paths.
    
    Examples:
        # Create backup using a selection template
        tl backup create --selection documents --repository myrepo
        
        # Create backup from direct paths
        tl backup create /path/to/backup --repository myrepo
        
        # Create backup with custom patterns
        tl backup create /home/user --include '*.txt' --exclude 'temp/*' --repository myrepo
    """
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    logger = logging.getLogger(__name__)
    logger.info(f"backup_create called with selection={selection}, repository={repository}")
    
    # Handle selection-based backup using BackupCLIHandler
    if selection:
        try:
            from TimeLocker.cli_modules.helpers.backup_cli_handler import (
                BackupCLIHandler,
                SelectionTemplateNotFoundError,
                InvalidSelectionConfigError
            )
            from TimeLocker.selection_manager import SelectionManager
            from TimeLocker.services.backup_orchestrator import BackupOrchestrator
            from .base import _create_config_service
            
            logger = logging.getLogger(__name__)
            logger.debug(f"Using selection template: {selection}")
            
            # Initialize required services
            config_service = _create_config_service(config_dir)
            selection_manager = SelectionManager()
            
            # Get service manager with backup orchestrator
            service_manager = _get_service_manager_for_command(config_dir)
            
            # Verify backup orchestrator is available
            if not hasattr(service_manager, '_backup_orchestrator') or service_manager._backup_orchestrator is None:
                show_error_panel(
                    "Service Initialization Error",
                    "Backup orchestrator is not available.\n\n"
                    "This may be due to a configuration issue. Please check your configuration:\n"
                    "  tl config show"
                )
                raise typer.Exit(1)
            
            # Create BackupCLIHandler with service manager's orchestrator
            cli_handler = BackupCLIHandler(
                selection_manager=selection_manager,
                backup_orchestrator=service_manager._backup_orchestrator
            )
            
            # Validate selection template exists (async)
            async def validate_template():
                return await cli_handler.validate_selection_exists(selection)
            
            if not asyncio.run(validate_template()):
                error_msg = cli_handler.suggest_template_creation(selection)
                show_error_panel("Selection Template Not Found", error_msg)
                raise typer.Exit(1)
            
            # Get default repository if not specified
            if not repository:
                default_repo_name = None
                default_method = _get_service_method(service_manager, "get_default_repository")
                if default_method:
                    try:
                        default_repo_name = _call_service_method(default_method)
                    except Exception as exc:
                        logger.debug("Service default repository lookup failed: %s", exc)
                
                if not default_repo_name:
                    try:
                        default_repo_name = config_service.get_default_repository()
                    except Exception as exc:
                        logger.debug("ConfigService default repository lookup failed: %s", exc)
                
                if isinstance(default_repo_name, Path):
                    default_repo_name = str(default_repo_name)
                if isinstance(default_repo_name, str) and default_repo_name.strip():
                    repository = default_repo_name
                else:
                    show_error_panel(
                        "Repository Required",
                        "No repository specified and no default repository configured.\n\n"
                        "💡 Specify a repository with --repository or set a default:\n"
                        "   tl repos set-default <name>"
                    )
                    raise typer.Exit(1)
            
            # Display selection info
            console.print(f"📁 Using selection template: [bold cyan]{selection}[/bold cyan]")
            try:
                async def get_summary():
                    return await cli_handler.get_selection_summary(selection)
                
                summary = asyncio.run(get_summary())
                console.print(f"[dim]{summary}[/dim]")
            except Exception as e:
                logger.debug(f"Could not get selection summary: {e}")
            
            # Execute backup using BackupCLIHandler
            cli_options = {
                'tool_type': 'restic',
                'max_retries': 3,
                'notify_on_success': True,
                'notify_on_failure': True,
                'notifications_enabled': True,
                'priority': 0
            }
            
            result = asyncio.run(cli_handler.execute_backup_with_selection(
                selection_name=selection,
                repository=repository,
                tags=tags,
                dry_run=dry_run,
                **cli_options
            ))
            
            # Display results
            if result.status.value in ['completed', 'success']:
                details = {
                    "Snapshot ID": result.snapshot_id or "Unknown",
                    "Files processed": f"{result.files_processed:,}" if result.files_processed else "Unknown",
                    "Data processed": f"{result.bytes_transferred:,} bytes" if result.bytes_transferred else "Unknown",
                    "Duration": f"{result.duration.total_seconds():.1f}s" if result.duration else "Unknown"
                }
                
                success_msg = "Backup operation completed successfully!"
                if result.warnings:
                    success_msg += f" ({len(result.warnings)} warnings)"
                
                show_success_panel("Backup Completed", success_msg, details)
                
                # Show warnings if any
                for warning in result.warnings:
                    console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
            else:
                error_msg = "Backup operation failed"
                if result.errors:
                    error_msg += f": {'; '.join(str(err) for err in result.errors)}"
                
                show_error_panel("Backup Failed", error_msg)
                raise typer.Exit(1)
            
            return
            
        except SelectionTemplateNotFoundError as e:
            show_error_panel("Selection Template Not Found", str(e))
            raise typer.Exit(1)
        except InvalidSelectionConfigError as e:
            show_error_panel("Invalid Selection Configuration", str(e))
            raise typer.Exit(1)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Selection-based backup failed: {e}", exc_info=True)
            show_error_panel("Backup Error", f"Failed to execute selection-based backup: {e}")
            raise typer.Exit(1)

    # Validate sources
    if not sources:
        show_error_panel("No Sources", "No source paths specified for backup")
        console.print("💡 Either provide source paths or use --selection to specify a data selection template")
        raise typer.Exit(1)

    repository_uri = repository
    actual_repository_name = repository
    resolved_password = password or ""
    skip_repository_setup = dry_run or not repository
    fallback_repository_uri = "dry-run://local"

    if skip_repository_setup:
        repository_uri = repository or fallback_repository_uri
        actual_repository_name = repository or "dry-run"
    else:
        try:
            # Use RepositoryResolver for unified repository resolution
            from .base import _create_repository_resolver
            
            resolver = _create_repository_resolver(config_dir)
            
            # Resolve repository name to URI
            actual_repository_name = repository or resolver.get_default_repository()
            repository_uri = resolver.resolve_repository_uri(repository)
            
            # Resolve credentials through credential chain
            resolved_password = resolver.resolve_credentials(
                repository_name=actual_repository_name,
                explicit_password=password,
                allow_prompt=interactive
            )
            
            if not resolved_password and not interactive:
                show_error_panel(
                    "Repository Error",
                    "Repository password is required; provide --password or set an environment variable when running non-interactively."
                )
                raise typer.Exit(1)
                
        except (RepositoryNotFoundError, ConfigurationError) as e:
            if dry_run:
                logger = logging.getLogger(__name__)
                logger.debug("Proceeding with dry-run backup without configured repository: %s", e)
                repository_uri = repository or fallback_repository_uri
                actual_repository_name = repository or "dry-run"
                resolved_password = password or ""
                skip_repository_setup = True
            else:
                show_error_panel("Repository Error", str(e))
                raise typer.Exit(1)
        except Exception as e:
            show_error_panel("Repository Error", str(e))
            raise typer.Exit(1)

    password = resolved_password
    if repository_uri is None:
        repository_uri = fallback_repository_uri

    try:
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting backup execution with repository_uri: {repository_uri}")
        progress_service = get_progress_service(console=console)
        with progress_service.spinner("Initializing backup...") as progress:

            # Initialize service manager
            logger.debug("About to call get_cli_service_manager()")
            service_manager = get_cli_service_manager()
            logger.debug(f"Service manager created: {type(service_manager)}")

            # Create backup request
            progress.update(description="Preparing backup request...")
            logger.debug(f"Creating CLIBackupRequest with sources={sources}, repository_uri={repository_uri}")
            logger.debug(f"CLI collected password: {'***' if password else 'None'}")
            backup_request = CLIBackupRequest(
                    sources=sources,
                    repository_uri=repository_uri,
                    password=password,
                    target_name=None,  # No longer using backup targets
                    backup_name=name,
                    tags=tags or [],
                    include_patterns=include or [],
                    exclude_patterns=exclude or [],
                    dry_run=dry_run
            )
            logger.debug("CLIBackupRequest created successfully")
            logger.debug(f"CLIBackupRequest password field: {'***' if backup_request.password else 'None'}")

            # Execute backup using modern orchestrator
            progress.update(description="Executing backup...")
            # Prefer legacy execute_backup when available (for tests mocking this method)
            if hasattr(service_manager, "execute_backup"):
                logger.debug("Calling service_manager.execute_backup (legacy API)")
                result = service_manager.execute_backup(backup_request)
            else:
                logger.debug("Calling service_manager.execute_backup_from_cli (new API)")
                result = service_manager.execute_backup_from_cli(backup_request)
            logger.debug(f"Backup result: {getattr(result, 'status', 'unknown')}")

        # Display results using new BackupResult data model
        def _safe_attr(obj, attr, default=None):
            try:
                value = getattr(obj, attr)
            except AttributeError:
                return default
            if isinstance(value, (str, int, float, bool, list, dict, tuple)):
                return value
            return default

        is_successful = _safe_attr(result, "is_successful", None)
        if is_successful is None:
            is_successful = _safe_attr(result, "success", False)
        if bool(is_successful):
            files_processed = _safe_attr(result, "files_processed", 0)
            bytes_processed = _safe_attr(result, "bytes_processed", 0)
            duration_value = _safe_attr(result, "duration", None)
            snapshot_id_value = _safe_attr(result, "snapshot_id", "Unknown") or "Unknown"

            details = {
                    "Snapshot ID":     snapshot_id_value,
                    "Files processed": f"{files_processed:,}" if isinstance(files_processed, (int, float)) else "Unknown",
                    "Data processed":  f"{bytes_processed:,} bytes" if isinstance(bytes_processed, (int, float)) and bytes_processed else "Unknown",
                    "Duration":        f"{duration_value:.1f}s" if isinstance(duration_value, (int, float)) and duration_value else "Unknown"
            }

            success_msg = "Backup operation completed successfully!"
            warnings = _safe_attr(result, "warnings", []) or []
            if warnings:
                success_msg += f" ({len(warnings)} warnings)"

            show_success_panel("Backup Completed", success_msg, details)

            # Show warnings if any
            for warning in warnings:
                console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
        else:
            error_msg = "Backup operation failed"
            errors = _safe_attr(result, "errors", []) or []
            if errors:
                try:
                    error_msg += f": {'; '.join(str(err) for err in errors)}"
                except Exception:
                    pass

            show_error_panel("Backup Failed", error_msg)
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Backup operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Backup Error", f"An unexpected error occurred: {e}")
        raise typer.Exit(1)


@backup_app.command("verify")
def backup_verify(
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        snapshot: Annotated[
            Optional[str], typer.Option("--snapshot", "-s", help="Specific snapshot ID to verify", autocompletion=snapshot_id_completer)] = None,
        latest: Annotated[bool, typer.Option("--latest", help="Verify the latest snapshot")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify backup integrity for a repository or a specific snapshot."""
    setup_logging(verbose)

    # Validate inputs early (but only when provided so --help still works with exit 0)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        if snapshot:
            validate_snapshot_id_format(snapshot, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)

    try:
        service_manager = get_cli_service_manager()

        # If --latest was provided without an explicit snapshot, we'll let the service
        # interpret None as "latest" or handle resolution internally. Tests only
        # assert exit codes, not behavior here.
        snapshot_id = snapshot if snapshot else None

        # Use empty string when repository not provided; service will handle/return False
        repo_input = repository or ""

        success = False
        try:
            success = service_manager.verify_backup_integrity(repo_input, snapshot_id=snapshot_id)
        except Exception:
            success = False

        if success:
            show_success_panel("Verification Completed", "Backup integrity verified successfully.")
            raise typer.Exit(0)
        else:
            show_error_panel("Verification Failed", "Backup integrity verification failed.")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Verification was cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Verification Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
