"""
Backup operation commands.

This module contains CLI commands for creating and verifying backups.
"""

import logging
import sys
import asyncio
from typing import Optional, List, Annotated, TypeAlias, cast
from pathlib import Path

import typer
import click

from ..helpers.display import show_success_panel, show_error_panel, console
from ..helpers.logging_setup import setup_logging
from ..helpers.service_helpers import (
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
)

# Import from TimeLocker package
from TimeLocker.cli_services import CLIBackupRequest
from TimeLocker.completion import (
    file_path_completer,
    repository_completer,
    selection_name_completer,
    snapshot_id_completer,
)
from TimeLocker.config.configuration_manager import RepositoryNotFoundError
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.cli_modules.helpers.backup_cli_handler import (
    BackupCLIHandler,
    BackupCLIHandlerError,
    InvalidSelectionConfigError,
    SelectionTemplateNotFoundError,
)
from TimeLocker.interfaces.backup_orchestrator import BackupOrchestratorError
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format
from TimeLocker.utils import get_progress_service

from ..services import RepositoryResolver

# Create Typer app for backup operations
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

backup_app = typer.Typer(
    help="Backup operations",
    no_args_is_help=True,
    context_settings=CLI_CONTEXT_SETTINGS
)
backup_app.info.options_metavar = "<OPTIONS>"

BackupDisplayValue: TypeAlias = str | int | float | bool | list[object] | dict[str, object] | tuple[object, ...]


def _get_selection_handler_for_command(service_manager: object) -> object:
    """Return the focused handler, retaining legacy facade compatibility."""
    handler = getattr(service_manager, "selection_handler", None)
    if isinstance(handler, BackupCLIHandler):
        return handler
    return service_manager


def _safe_backup_attr(
        obj: object,
        attr: str,
        default: BackupDisplayValue | None = None,
) -> BackupDisplayValue | None:
    """Read simple result attributes without leaking unknown service result types."""
    try:
        value = cast(object, getattr(obj, attr))
    except AttributeError:
        return default
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    if isinstance(value, tuple):
        return cast(tuple[object, ...], value)
    return default


def _safe_backup_sequence(obj: object, attr: str) -> list[object] | tuple[object, ...]:
    """Return list-like result attributes for display loops."""
    value = _safe_backup_attr(obj, attr, [])
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return value
    return []


@backup_app.command("create")
def backup_create(
        sources: Annotated[Optional[List[Path]], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)] = None,
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        selection: Annotated[Optional[str], typer.Option("--selection", "-s", help="Use configured data selection template", autocompletion=selection_name_completer)] = None,
        name: Annotated[Optional[str], typer.Option("--name", "-n", help="Backup name")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Backup tags")] = None,
        compression: Annotated[Optional[str], typer.Option(
            "--compression",
            help="Restic compression mode: auto, off, or max",
            click_type=click.Choice(["auto", "off", "max"], case_sensitive=False),
        )] = None,
        one_file_system: Annotated[bool, typer.Option(
            "--one-file-system/--cross-filesystems",
            help="Do not cross filesystem boundaries while backing up",
        )] = False,
        exclude_file: Annotated[Optional[List[Path]], typer.Option("--exclude-file", help="Restic exclusion file (repeatable)")] = None,
        exclude_caches: Annotated[bool, typer.Option("--exclude-caches", help="Exclude directories marked with CACHEDIR.TAG")] = False,
        backend_option: Annotated[Optional[List[str]], typer.Option("--backend-option", help="Allowlisted Restic backend option (repeatable)")] = None,
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
            from .base import _create_config_service
            
            logger = logging.getLogger(__name__)
            logger.debug(f"Using selection template: {selection}")
            
            config_service = _create_config_service(config_dir)
            service_manager = _get_service_manager_for_command(config_dir)
            selection_handler = _get_selection_handler_for_command(service_manager)
            
            try:
                if isinstance(selection_handler, BackupCLIHandler):
                    template_exists = asyncio.run(
                        selection_handler.validate_selection_exists(selection)
                    )
                else:
                    template_exists = service_manager.selection_template_exists(selection)
            except BackupOrchestratorError as exc:
                logger.error("Backup orchestrator unavailable: %s", exc)
                initialization_message = "\n".join(
                    [
                        "Backup orchestrator is not available.",
                        "",
                        "This may be due to a configuration issue. Please check your configuration:",
                        "  tl config show",
                    ]
                )
                show_error_panel(
                    "Service Initialization Error",
                    initialization_message
                )
                raise typer.Exit(1)
            except Exception as exc:
                logger.error("Failed to verify selection template: %s", exc)
                show_error_panel(
                    "Selection Error",
                    f"Could not verify selection template '{selection}': {exc}"
                )
                raise typer.Exit(1)
            
            if not template_exists:
                if isinstance(selection_handler, BackupCLIHandler):
                    error_msg = selection_handler.suggest_template_creation(selection)
                else:
                    error_msg = service_manager.suggest_selection_creation(selection)
                show_error_panel("Selection Template Not Found", error_msg)
                raise typer.Exit(1)
            
            # Get default repository if not specified
            if not repository:
                default_repo_name: object = None
                default_method = _get_service_method(service_manager, "get_default_repository")
                if default_method:
                    try:
                        default_repo_name = cast(object, _call_service_method(default_method))
                    except Exception as exc:
                        logger.debug("Service default repository lookup failed: %s", exc)
                
                if not default_repo_name:
                    try:
                        default_repo_name = cast(object, config_service.get_default_repository())
                    except Exception as exc:
                        logger.debug("ConfigService default repository lookup failed: %s", exc)
                
                if isinstance(default_repo_name, Path):
                    default_repo_name = str(default_repo_name)
                if isinstance(default_repo_name, str) and default_repo_name.strip():
                    repository = default_repo_name
                else:
                    repository_message = "\n".join(
                        [
                            "No repository specified and no default repository configured.",
                            "",
                            "💡 Specify a repository with --repository or set a default:",
                            "   tl repos set-default <name>",
                        ]
                    )
                    show_error_panel(
                        "Repository Required",
                        repository_message
                    )
                    raise typer.Exit(1)
            
            # Display selection info
            console.print(f"📁 Using selection template: [bold cyan]{selection}[/bold cyan]")
            try:
                if isinstance(selection_handler, BackupCLIHandler):
                    summary = asyncio.run(
                        selection_handler.get_selection_summary(selection)
                    )
                else:
                    summary = service_manager.get_selection_summary(selection)
                if summary:
                    console.print(f"[dim]{summary}[/dim]")
            except SelectionTemplateNotFoundError as exc:
                logger.debug("Template summary unavailable: %s", exc)
            except Exception as e:
                logger.debug(f"Could not get selection summary: {e}")
            
            # Execute backup using BackupCLIHandler
            cli_options = {
                'tool_type': 'restic',
                'max_retries': 3,
                'notify_on_success': True,
                'notify_on_failure': True,
                'notifications_enabled': True,
                'priority': 0,
                'compression': compression,
                'one_file_system': one_file_system,
                'exclude_files': exclude_file or [],
                'exclude_caches': exclude_caches,
                'backend_options': backend_option or [],
            }
            
            try:
                if isinstance(selection_handler, BackupCLIHandler):
                    result = asyncio.run(
                        selection_handler.execute_backup_with_selection(
                            selection_name=selection,
                            repository=repository,
                            tags=tags,
                            dry_run=dry_run,
                            **cli_options,
                        )
                    )
                else:
                    result = service_manager.run_selection_backup(
                        selection_name=selection,
                        repository=repository,
                        tags=tags,
                        dry_run=dry_run,
                        cli_options=cli_options
                    )
            except SelectionTemplateNotFoundError as exc:
                show_error_panel("Selection Template Not Found", str(exc))
                raise typer.Exit(1)
            except InvalidSelectionConfigError as exc:
                show_error_panel("Invalid Selection Configuration", str(exc))
                raise typer.Exit(1)
            except BackupCLIHandlerError as exc:
                logger.error("Backup execution failed: %s", exc)
                show_error_panel("Backup Error", f"Failed to execute selection-based backup: {exc}")
                raise typer.Exit(1)
            except BackupOrchestratorError as exc:
                logger.error("Backup orchestrator error: %s", exc)
                show_error_panel("Service Initialization Error", str(exc))
                raise typer.Exit(1)
            except Exception as exc:
                logger.error("Unexpected error during selection backup: %s", exc)
                show_error_panel("Backup Error", f"Failed to execute selection-based backup: {exc}")
                raise typer.Exit(1)
            
            # Display results
            if result.status.value in ['completed', 'success']:
                details = {
                    "Snapshot ID": result.snapshot_id or "Unknown",
                    "Files processed": f"{result.files_processed:,}",
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

    invalid_sources = [str(source) for source in sources if not source.exists()]
    if invalid_sources:
        show_error_panel(
            "Invalid Sources",
            "The following backup source paths do not exist:",
            invalid_sources,
        )
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
            if actual_repository_name is None:
                raise RepositoryNotFoundError("No repository specified and no default repository configured")
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
    repository_uri = repository_uri or fallback_repository_uri

    try:
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting backup execution with repository_uri: {repository_uri}")
        progress_service = get_progress_service(console=console)
        with progress_service.spinner("Initializing backup...") as progress:

            # Initialize service manager
            logger.debug("About to create service manager for backup command")
            service_manager = _get_service_manager_for_command(config_dir)
            logger.debug(f"Service manager created: {type(service_manager)}")

            # Create backup request
            progress.update(description="Preparing backup request...")
            logger.debug(f"Creating CLIBackupRequest with sources={sources}, repository_uri={repository_uri}")
            logger.debug(f"CLI collected password: {'***' if password else 'None'}")
            backup_request = CLIBackupRequest(
                    sources=sources or [],
                    repository_uri=repository_uri,
                    password=password,
                    target_name=None,  # No longer using backup targets
                    backup_name=name,
                    tags=tags or [],
                    include_patterns=include or [],
                    exclude_patterns=exclude or [],
                    compression=compression,
                    one_file_system=one_file_system,
                    exclude_files=exclude_file or [],
                    exclude_caches=exclude_caches,
                    backend_options=backend_option or [],
                    dry_run=dry_run
            )
            logger.debug("CLIBackupRequest created successfully")
            logger.debug(f"CLIBackupRequest password field: {'***' if backup_request.password else 'None'}")

            # Execute backup using modern orchestrator
            progress.update(description="Executing backup...")
            # Prefer legacy execute_backup when available (for tests mocking this method)
            legacy_execute_backup = getattr(service_manager, "execute_backup", None)
            if callable(legacy_execute_backup):
                logger.debug("Calling service_manager.execute_backup (legacy API)")
                result = legacy_execute_backup(backup_request)
            else:
                logger.debug("Calling service_manager.execute_backup_from_cli (new API)")
                result = service_manager.execute_backup_from_cli(backup_request)
            logger.debug(f"Backup result: {getattr(result, 'status', 'unknown')}")

        # Display results using new BackupResult data model
        is_successful = _safe_backup_attr(result, "is_successful", None)
        if is_successful is None:
            is_successful = _safe_backup_attr(result, "success", False)
        if bool(is_successful):
            files_processed = _safe_backup_attr(result, "files_processed", 0)
            bytes_processed = _safe_backup_attr(result, "bytes_processed", 0)
            duration_value = _safe_backup_attr(result, "duration", None)
            snapshot_id_raw = _safe_backup_attr(result, "snapshot_id", "Unknown")
            snapshot_id_value = snapshot_id_raw if isinstance(snapshot_id_raw, str) and snapshot_id_raw else "Unknown"

            details = {
                    "Snapshot ID":     snapshot_id_value,
                    "Files processed": f"{files_processed:,}" if isinstance(files_processed, (int, float)) else "Unknown",
                    "Data processed":  f"{bytes_processed:,} bytes" if isinstance(bytes_processed, (int, float)) and bytes_processed else "Unknown",
                    "Duration":        f"{duration_value:.1f}s" if isinstance(duration_value, (int, float)) and duration_value else "Unknown"
            }

            success_msg = "Backup operation completed successfully!"
            warnings = _safe_backup_sequence(result, "warnings")
            if warnings:
                success_msg += f" ({len(warnings)} warnings)"

            show_success_panel("Backup Completed", success_msg, details)

            # Show warnings if any
            for warning in warnings:
                console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
        else:
            error_msg = "Backup operation failed"
            errors = _safe_backup_sequence(result, "errors")
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
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify backup integrity for a repository or a specific snapshot."""
    setup_logging(verbose, config_dir)

    # Validate inputs early (but only when provided so --help still works with exit 0)
    try:
        if repository:
            RepositoryResolver.validate_repository_name_or_uri(repository)
        if latest and snapshot:
            raise ValueError("Use either --snapshot or --latest, not both.")
        if snapshot:
            validate_snapshot_id_format(snapshot, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)

    try:
        service_manager = _get_service_manager_for_command(config_dir)

        snapshot_id = "latest" if latest else snapshot

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
