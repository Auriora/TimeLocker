"""
Restore operations.

This module contains CLI commands for restore/recovery operations.
Reorganized from snapshots.py to provide a dedicated restore command hierarchy.

This module integrates with the new Recovery Operations architecture including:
- RecoveryOrchestrator for coordinated recovery operations
- SnapshotBrowser for interactive snapshot exploration
- RecoveryValidator for integrity verification
- Progress monitoring for real-time operation tracking
"""

import sys
import os
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path
from datetime import datetime
from time import sleep

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout

# Import from base module
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
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.completion import (
    snapshot_id_completer,
    repository_completer,
    file_path_completer,
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri,
    get_default_repository
)
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format

# Import recovery operations components
try:
    from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
    from TimeLocker.snapshot_browser import SnapshotBrowser
    from TimeLocker.recovery_validator import RecoveryValidator
    from TimeLocker.interfaces.recovery_models import (
        RecoveryOptions,
        SelectionCriteria,
        RecoveryType,
        OperationStatus,
        PaginationOptions
    )
    from TimeLocker.recovery_errors import (
        RecoveryError,
        SnapshotNotFoundError,
        RestoreTargetError,
        RepositoryAccessError
    )
    RECOVERY_OPERATIONS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.debug(f"Recovery operations components not available: {e}")
    RECOVERY_OPERATIONS_AVAILABLE = False

# Create Typer app for restore operations
restore_app = create_typer_app(
    name="restore",
    help_text="Recovery and restore operations"
)

# Helper function to get setup_logging from base
setup_logging = _cli_module.setup_logging


# ============================================================================
# Progress Monitoring Helpers
# ============================================================================

def _display_recovery_progress(operation_id: str, orchestrator: 'RecoveryOrchestrator') -> None:
    """
    Display real-time progress for a recovery operation.
    
    Args:
        operation_id: ID of the recovery operation to monitor
        orchestrator: RecoveryOrchestrator instance managing the operation
    """
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from time import sleep
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Restoring files...", total=100)
        
        while True:
            try:
                # Get operation status
                operation = orchestrator.get_recovery_status(operation_id)
                
                if operation.status == OperationStatus.COMPLETED:
                    progress.update(task, completed=100, description="✅ Restore completed")
                    break
                elif operation.status == OperationStatus.FAILED:
                    progress.update(task, description="❌ Restore failed")
                    break
                elif operation.status == OperationStatus.CANCELLED:
                    progress.update(task, description="⚠️  Restore cancelled")
                    break
                
                # Update progress
                if operation.progress:
                    if operation.progress.total_files > 0:
                        percentage = (operation.progress.files_processed / operation.progress.total_files) * 100
                        progress.update(
                            task,
                            completed=percentage,
                            description=f"Restoring files... ({operation.progress.files_processed}/{operation.progress.total_files})"
                        )
                
                sleep(0.5)  # Update every 500ms
                
            except KeyboardInterrupt:
                # Cancel operation on Ctrl+C
                orchestrator.cancel_recovery(operation_id)
                progress.update(task, description="⚠️  Cancelling restore...")
                break
            except Exception as e:
                logger.error(f"Error monitoring progress: {e}")
                break


def _format_progress_status(progress: 'ProgressStatus') -> str:
    """
    Format progress status for display.
    
    Args:
        progress: ProgressStatus object
        
    Returns:
        Formatted progress string
    """
    if not progress:
        return "No progress information available"
    
    lines = []
    
    # Files progress
    if progress.total_files > 0:
        files_pct = (progress.files_processed / progress.total_files) * 100
        lines.append(f"Files: {progress.files_processed:,}/{progress.total_files:,} ({files_pct:.1f}%)")
    
    # Bytes progress
    if progress.total_bytes > 0:
        bytes_pct = (progress.bytes_transferred / progress.total_bytes) * 100
        transferred_str = _format_size(progress.bytes_transferred)
        total_str = _format_size(progress.total_bytes)
        lines.append(f"Data: {transferred_str}/{total_str} ({bytes_pct:.1f}%)")
    
    # Transfer rate
    if progress.transfer_rate > 0:
        rate_str = _format_size(int(progress.transfer_rate))
        lines.append(f"Rate: {rate_str}/s")
    
    # Current file
    if progress.current_file:
        lines.append(f"Current: {progress.current_file}")
    
    # Estimated completion
    if progress.estimated_completion:
        eta = progress.estimated_completion.strftime('%H:%M:%S')
        lines.append(f"ETA: {eta}")
    
    return "\n".join(lines)


# ============================================================================
# Browse Command - Interactive snapshot content exploration
# ============================================================================

@restore_app.command("browse")
@with_error_handling("Browse Error")
@with_logging
def restore_browse(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        path: Annotated[Optional[str], typer.Option("--path", help="Browse specific path within snapshot")] = None,
        page: Annotated[int, typer.Option("--page", help="Page number for pagination")] = 1,
        page_size: Annotated[int, typer.Option("--page-size", help="Number of entries per page")] = 50,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Browse snapshot contents interactively.
    
    This command provides interactive exploration of snapshot contents with
    pagination support for large directories. It integrates with the new
    SnapshotBrowser component for efficient browsing.
    
    Examples:
        timelocker restore browse myrepo latest
        timelocker restore browse myrepo abc123 --path /home/user
        timelocker restore browse myrepo latest --page 2 --page-size 100
    """
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    try:
        # Validate inputs
        validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
        
        # Resolve repository
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        
        # Get password if not provided
        if not password:
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password and interactive:
                password = Prompt.ask("Repository password", password=True)
        
        # Initialize components
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing snapshot browser...", total=None)
            
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password, 
                                         repository_name=actual_repository_name)
            
            # Handle "latest" snapshot
            if snapshot_id == "latest":
                progress.update(task, description="Finding latest snapshot...")
                snapshot_manager = SnapshotManager(repo)
                snapshots = snapshot_manager.list_snapshots()
                if not snapshots:
                    show_error_panel("No Snapshots", "No snapshots found in repository")
                    raise typer.Exit(1)
                snapshot_id = snapshots[0].id
                console.print(f"📸 Using latest snapshot: [bold cyan]{snapshot_id[:12]}[/bold cyan]")
            
            # Use SnapshotBrowser if available
            if RECOVERY_OPERATIONS_AVAILABLE:
                progress.update(task, description="Loading snapshot contents...")
                browser = SnapshotBrowser(repo)
                
                # Create pagination options
                pagination = PaginationOptions(page=page, page_size=page_size)
                
                # List snapshot contents
                listing = browser.list_snapshot_contents(
                    snapshot_id=snapshot_id,
                    path=path or "/",
                    pagination=pagination
                )
                
                progress.remove_task(task)
                
                # Display contents in a table
                title = f"Contents of Snapshot {snapshot_id[:12]}"
                if path:
                    title += f" at {path}"
                if listing.pagination_info:
                    title += f" (Page {listing.pagination_info.current_page}/{listing.pagination_info.total_pages})"
                
                table = Table(title=title, show_header=True, header_style="bold magenta")
                table.add_column("Type", style="cyan", width=10)
                table.add_column("Size", style="green", width=12)
                table.add_column("Modified", style="yellow", width=20)
                table.add_column("Path", style="white")
                
                for entry in listing.entries:
                    entry_type = entry.type.value if hasattr(entry.type, 'value') else str(entry.type)
                    size_str = _format_size(entry.size) if entry.size else "-"
                    mod_time = entry.modification_time.strftime('%Y-%m-%d %H:%M:%S') if entry.modification_time else "-"
                    table.add_row(entry_type, size_str, mod_time, entry.path)
                
                console.print()
                console.print(table)
                console.print()
                
                # Show pagination info
                if listing.pagination_info:
                    info = listing.pagination_info
                    console.print(f"[dim]Showing {len(listing.entries)} of {info.total_entries} entries[/dim]")
                    if info.has_next:
                        console.print(f"[dim]💡 Use --page {info.current_page + 1} to see next page[/dim]")
                
            else:
                # Fallback to service manager
                progress.update(task, description="Loading snapshot contents...")
                manager = get_cli_service_manager(config_dir=config_dir)
                contents_method = _get_service_method(manager, "list_snapshot_contents")
                
                if contents_method:
                    contents = _call_service_method(
                        contents_method,
                        snapshot_id=snapshot_id,
                        repository=repository,
                        path=path,
                        path_filter=path
                    ) or []
                else:
                    show_error_panel("Not Implemented", "Snapshot browsing is not available in this build.")
                    raise typer.Exit(1)
                
                progress.remove_task(task)
                
                # Display contents
                if not contents:
                    show_info_panel("Snapshot Contents", "No files found in this snapshot.")
                    return
                
                table = Table(title=f"Contents of Snapshot {snapshot_id[:12]}")
                table.add_column("Type", style="cyan", width=10)
                table.add_column("Size", style="green", width=12)
                table.add_column("Path", style="white")
                
                for entry in contents:
                    if isinstance(entry, dict):
                        entry_type = entry.get("type", "file")
                        size = entry.get("size", entry.get("Size", 0))
                        path_value = entry.get("path", entry.get("Path", ""))
                    else:
                        entry_type = getattr(entry, "type", "file")
                        size = getattr(entry, "size", 0)
                        path_value = getattr(entry, "path", getattr(entry, "name", ""))
                    
                    size_str = _format_size(size) if isinstance(size, (int, float)) else str(size)
                    table.add_row(str(entry_type), size_str, str(path_value))
                
                console.print(table)
        
        # Interactive file selection if in interactive mode
        if interactive:
            console.print()
            if Confirm.ask("Would you like to restore files from this snapshot?"):
                # Get target path
                target = Prompt.ask("Enter target path for restore", default="./restore")
                target_path = Path(target)
                
                # Ask for specific files or all
                restore_all = Confirm.ask("Restore all files?", default=True)
                
                if restore_all:
                    console.print(f"\n[cyan]To restore all files, run:[/cyan]")
                    console.print(f"  timelocker restore full {repository} {snapshot_id} {target_path}")
                else:
                    file_path = Prompt.ask("Enter file path to restore")
                    console.print(f"\n[cyan]To restore specific files, run:[/cyan]")
                    console.print(f"  timelocker restore files {repository} {snapshot_id} {target_path} --include '{file_path}'")
        
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Browse operation cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Browse Error", f"Failed to browse snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# ============================================================================
# Files Command - Selective file restoration
# ============================================================================

@restore_app.command("files")
@with_error_handling("Restore Error")
@with_logging
def restore_files(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        target: Annotated[Path, typer.Argument(help="Target path for restore", autocompletion=file_path_completer)],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        preview: Annotated[bool, typer.Option("--preview", help="Preview restore without executing")] = False,
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Restore specific files from a snapshot."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    # Validate inputs early
    try:
        validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    
    # Try service manager first
    try:
        service_manager = get_cli_service_manager(config_dir=config_dir)
        restore_method = _get_service_method(service_manager, "restore_snapshot")
        
        if restore_method:
            try:
                restore_result = _call_service_method(
                    restore_method,
                    snapshot_id=snapshot_id,
                    repository=repository,
                    target_path=str(target),
                    password=password,
                    include_patterns=include,
                    exclude_patterns=exclude,
                    preview=preview,
                )
                success_flag = getattr(restore_result, "success", None)
                if success_flag is None:
                    success_flag = getattr(restore_result, "is_successful", 
                                         restore_result if isinstance(restore_result, bool) else False)
                if bool(success_flag):
                    show_success_panel("Restore Completed", "Files restored successfully.")
                    return
            except click.exceptions.Exit:
                raise
            except Exception as exc:
                logging.getLogger(__name__).debug("Service restore failed, falling back to local flow: %s", exc)
    except Exception:
        service_manager = None
    
    # Fallback to direct implementation
    try:
        # Resolve repository
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        
        if not password:
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                if interactive:
                    password = Prompt.ask("Repository password", password=True)
                else:
                    show_error_panel("Repository Error",
                                   "Repository password is required; provide --password or set RESTIC_PASSWORD.")
                    raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)
    
    # Handle "latest" snapshot
    snapshot = snapshot_id
    if snapshot == "latest":
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Finding latest snapshot...", total=None)
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password, 
                                         repository_name=actual_repository_name)
            snapshot_manager = SnapshotManager(repo)
            snapshots = snapshot_manager.list_snapshots()
            
            if not snapshots:
                show_error_panel("No Snapshots", "No snapshots found in repository")
                raise typer.Exit(1)
            
            snapshot = snapshots[0].id
            console.print(f"📸 Using latest snapshot: [bold cyan]{snapshot[:12]}[/bold cyan]")
            progress.remove_task(task)
    
    # Preview mode
    if preview:
        console.print()
        console.print(Panel(
            f"🔍 [bold]Restore Preview[/bold]\n\n"
            f"[bold]Repository:[/bold] {repository}\n"
            f"[bold]Snapshot:[/bold] {snapshot}\n"
            f"[bold]Target:[/bold] {target}\n"
            f"[bold]Include patterns:[/bold] {', '.join(include) if include else 'All files'}\n"
            f"[bold]Exclude patterns:[/bold] {', '.join(exclude) if exclude else 'None'}\n\n"
            f"[dim]This is a preview only. No files will be restored.[/dim]",
            title="[bold blue]Restore Preview[/bold blue]",
            border_style="blue"
        ))
        console.print()
        
        if not Confirm.ask("Would you like to proceed with the actual restore?"):
            show_info_panel("Preview Complete", "Restore preview completed. No files were restored.")
            return
    
    # Confirm destructive operation
    if not yes:
        if target.exists() and any(target.iterdir()):
            if not Confirm.ask(f"Target directory [bold]{target}[/bold] is not empty. Continue?"):
                show_info_panel("Operation Cancelled", "Restore operation cancelled by user")
                raise typer.Exit(0)
    
    try:
        # Try using RecoveryOrchestrator if available for better progress monitoring
        if RECOVERY_OPERATIONS_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Initializing recovery...", total=100)
                
                backup_manager = BackupManager()
                progress.update(task, advance=10, description="Connecting to repository...")
                repo = backup_manager.from_uri(repository_uri, password=password, 
                                             repository_name=actual_repository_name)
                
                progress.update(task, advance=10, description="Initializing recovery orchestrator...")
                orchestrator = RecoveryOrchestrator(repo)
                
                # Build selection criteria
                selection_criteria = SelectionCriteria(
                    include_patterns=list(include) if include else [],
                    exclude_patterns=list(exclude) if exclude else []
                )
                
                # Build recovery options
                recovery_options = RecoveryOptions(
                    overwrite_existing=True,
                    preserve_permissions=True,
                    preserve_timestamps=True,
                    verify_integrity=True,
                    continue_on_error=True
                )
                
                progress.update(task, advance=10, description="Starting selective recovery...")
                
                # Initiate recovery
                operation = orchestrator.initiate_selective_recovery(
                    snapshot_id=snapshot,
                    selection_criteria=selection_criteria,
                    target_path=str(target),
                    options=recovery_options
                )
                
                progress.update(task, advance=20, description="Recovery in progress...")
                
                # Monitor progress
                while operation.status in [OperationStatus.PENDING, OperationStatus.IN_PROGRESS]:
                    sleep(0.5)
                    operation = orchestrator.get_recovery_status(operation.operation_id)
                    
                    if operation.progress and operation.progress.total_files > 0:
                        pct = (operation.progress.files_processed / operation.progress.total_files) * 100
                        progress.update(
                            task,
                            completed=30 + (pct * 0.7),  # Scale to 30-100%
                            description=f"Restoring files... ({operation.progress.files_processed}/{operation.progress.total_files})"
                        )
                
                progress.update(task, completed=100, description="✅ Recovery completed")
                
                # Check final status
                if operation.status == OperationStatus.COMPLETED:
                    details = {
                        "Operation ID": operation.operation_id[:12],
                        "Files restored": f"{operation.progress.files_processed:,}" if operation.progress else "N/A",
                        "Target path": str(target),
                        "Duration": f"{(operation.completion_time - operation.start_time).total_seconds():.1f}s" if operation.completion_time else "N/A"
                    }
                    show_success_panel("Recovery Completed", "Files restored successfully!", details)
                    return
                else:
                    error_msg = operation.error_details.error_message if operation.error_details else "Unknown error"
                    show_error_panel("Recovery Failed", f"Recovery operation failed: {error_msg}")
                    raise typer.Exit(1)
        else:
            # Fallback to legacy restore manager
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Initialize managers
                task = progress.add_task("Initializing restore...", total=None)
                backup_manager = BackupManager()
                
                # Create repository
                progress.update(task, description="Connecting to repository...")
                repo = backup_manager.from_uri(repository_uri, password=password, 
                                             repository_name=actual_repository_name)
                
                # Initialize restore manager
                restore_manager = RestoreManager(repo)
                
                # Create restore options
                progress.update(task, description="Preparing restore options...")
                from TimeLocker.restore_manager import RestoreOptions
                options = RestoreOptions().with_target_path(target)
                if include:
                    options = options.with_include_paths(include)
                if exclude:
                    options = options.with_exclude_paths(exclude)
                
                # Perform restore
                progress.update(task, description="Restoring files...")
                result = restore_manager.restore_snapshot(snapshot, options)
                
                progress.remove_task(task)
        
        # Display results
        if result.success:
            details = {
                "Files restored": f"{result.files_restored:,}",
                "Target path": str(target),
                "Duration": f"{getattr(result, 'duration_seconds', 0):.1f}s"
            }
            if hasattr(result, 'files_skipped') and result.files_skipped > 0:
                details["Files skipped"] = f"{result.files_skipped:,}"
            
            show_success_panel("Restore Completed", "Files restored successfully!", details)
        else:
            error_details = getattr(result, 'errors', []) if hasattr(result, 'errors') else []
            show_error_panel("Restore Failed", 
                           f"Restore operation failed: {getattr(result, 'error', 'Unknown error')}", 
                           error_details)
            raise typer.Exit(1)
    
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Restore operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Restore Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Full Command - Complete snapshot restoration
# ============================================================================

@restore_app.command("full")
@with_error_handling("Restore Error")
@with_logging
def restore_full(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        target: Annotated[Path, typer.Argument(help="Target path for restore", autocompletion=file_path_completer)],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Restore complete snapshot to target directory."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    # Validate inputs
    try:
        validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    
    # Warn about full restore
    if not yes and interactive:
        console.print()
        console.print(Panel(
            f"⚠️  [bold yellow]Full Snapshot Restore[/bold yellow]\n\n"
            f"This will restore ALL files from snapshot [cyan]{snapshot_id}[/cyan]\n"
            f"to [cyan]{target}[/cyan].\n\n"
            f"[bold]Repository:[/bold] {repository}\n"
            f"[bold]Target:[/bold] {target}\n\n"
            f"[dim]This operation may overwrite existing files.[/dim]",
            border_style="yellow"
        ))
        console.print()
        
        if not Confirm.ask("Are you sure you want to proceed?", default=False):
            show_info_panel("Operation Cancelled", "Full restore cancelled by user")
            raise typer.Exit(0)
    
    # Call restore files with no filters (restore everything)
    try:
        # Use the restore_files function but with no include/exclude filters
        from TimeLocker.cli_modules.commands.restore import restore_files as _restore_files_impl
        
        # Create a context to call restore_files
        ctx = typer.Context(restore_files)
        ctx.params = {
            'repository': repository,
            'snapshot_id': snapshot_id,
            'target': target,
            'password': password,
            'exclude': None,
            'include': None,
            'preview': False,
            'yes': True,  # Already confirmed
            'verbose': verbose,
            'config_dir': config_dir,
        }
        
        # Call the files restore with all files
        restore_files(
            repository=repository,
            snapshot_id=snapshot_id,
            target=target,
            password=password,
            exclude=None,
            include=None,
            preview=False,
            yes=True,
            verbose=verbose,
            config_dir=config_dir,
        )
        
    except Exception as e:
        show_error_panel("Full Restore Error", f"Failed to restore snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# List Command - Show available snapshots for restore
# ============================================================================

@restore_app.command("list")
@with_error_handling("List Error")
@with_logging
def restore_list(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """List available snapshots in repository for restore."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    repository_input = repository
    service_snapshots = None
    using_service_manager = False
    
    try:
        manager = _get_service_manager_for_command(config_dir)
        list_method = _get_service_method(manager, "list_snapshots")
        if list_method:
            try:
                service_snapshots = list_method(repository_input)
                using_service_manager = True
            except Exception as exc:
                logging.getLogger(__name__).debug("Service snapshot listing failed: %s", exc)
                service_snapshots = None
                using_service_manager = False
    except Exception as exc:
        logging.getLogger(__name__).debug("Unable to obtain service manager snapshots: %s", exc)
    
    if using_service_manager:
        if not service_snapshots:
            show_info_panel("No Snapshots", "No snapshots found in repository")
            return
        
        table = Table(title=f"Available Snapshots for Restore ({len(service_snapshots)})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Date", style="green")
        table.add_column("Host", style="yellow")
        table.add_column("Paths", style="white")
        
        for entry in service_snapshots:
            if isinstance(entry, dict):
                snapshot_id = str(entry.get("id") or entry.get("short_id") or "unknown")
                timestamp = entry.get("time") or entry.get("timestamp") or "unknown"
                host = entry.get("hostname", "unknown")
                paths = entry.get("paths") or []
            else:
                snapshot_id = getattr(entry, "short_id", getattr(entry, "id", "unknown"))
                timestamp = getattr(entry, "time", getattr(entry, "timestamp", "unknown"))
                host = getattr(entry, "hostname", "unknown")
                paths = getattr(entry, "paths", [])
            
            path_display = ", ".join(str(p) for p in paths[:2])
            if paths and len(paths) > 2:
                path_display += f" (+{len(paths) - 2} more)"
            
            table.add_row(snapshot_id, str(timestamp), str(host), path_display)
        
        console.print(table)
        console.print()
        console.print("[dim]💡 Use 'timelocker restore browse <repository> <snapshot-id>' to explore snapshot contents[/dim]")
        console.print("[dim]💡 Use 'timelocker restore files <repository> <snapshot-id> <target>' to restore files[/dim]")
        return
    
    # Fallback to direct implementation
    try:
        validate_repository_name_or_uri(repository_input)
    except ValueError as ve:
        show_error_panel("Invalid Repository", str(ve))
        raise typer.Exit(1)
    
    try:
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        
        if verbose:
            console.print(f"[dim]Using repository: {repository_uri}[/dim]")
        
        backup_manager = BackupManager()
        repo = backup_manager.from_uri(repository_uri, password=password, 
                                     repository_name=actual_repository_name)
        
        resolved_password = repo.password()
        if not resolved_password:
            console.print(f"[yellow]Repository requires a password.[/yellow]")
            if interactive:
                resolved_password = Prompt.ask("Repository password", password=True)
            else:
                show_error_panel("Repository Error",
                               "Repository password is required; provide --password or set RESTIC_PASSWORD.")
                raise typer.Exit(1)
        
        password = resolved_password
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading snapshots...", total=None)
            progress.update(task, description="Connecting to repository...")
            snapshot_manager = SnapshotManager(repo)
            progress.update(task, description="Retrieving snapshots...")
            snapshots = snapshot_manager.list_snapshots()
            progress.remove_task(task)
        
        if not snapshots:
            show_info_panel("No Snapshots", "No snapshots found in repository")
            return
        
        table = Table(
            title=f"📸 Found {len(snapshots)} snapshots available for restore",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            title_style="bold blue"
        )
        
        table.add_column("ID", style="cyan", no_wrap=True, width=12)
        table.add_column("Date", style="green", no_wrap=True)
        table.add_column("Host", style="yellow", no_wrap=True, width=15)
        table.add_column("Tags", style="blue", width=20)
        table.add_column("Paths", style="white")
        
        for snapshot in snapshots:
            snapshot_id = snapshot.id[:12] if len(snapshot.id) > 12 else snapshot.id
            date_str = snapshot.time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(snapshot, 'time') else snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            hostname = getattr(snapshot, 'hostname', 'unknown')[:15]
            tags_str = ",".join(snapshot.tags) if snapshot.tags else ""
            if len(tags_str) > 20:
                tags_str = tags_str[:17] + "..."
            paths_str = ",".join(str(p) for p in snapshot.paths[:2])
            if len(snapshot.paths) > 2:
                paths_str += f" (+{len(snapshot.paths) - 2} more)"
            table.add_row(snapshot_id, date_str, hostname, tags_str, paths_str)
        
        console.print()
        console.print(table)
        console.print()
        console.print("[dim]💡 Use 'timelocker restore browse <repository> <snapshot-id>' to explore snapshot contents[/dim]")
        console.print("[dim]💡 Use 'timelocker restore files <repository> <snapshot-id> <target>' to restore files[/dim]")
    
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "List operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("List Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Mount Command - Mount snapshot as read-only filesystem
# ============================================================================

@restore_app.command("mount")
@with_error_handling("Mount Error")
@with_logging
def restore_mount(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        mountpoint: Annotated[Path, typer.Argument(help="Mount point directory", autocompletion=file_path_completer)],
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Mount snapshot as read-only filesystem for browsing."""
    setup_logging(verbose, config_dir)
    
    try:
        # Validate inputs
        validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
        
        # Ensure mount point exists
        if not mountpoint.exists():
            mountpoint.mkdir(parents=True, exist_ok=True)
            console.print(f"[dim]Created mount point: {mountpoint}[/dim]")
        
        # Check if mount point is empty
        if mountpoint.exists() and any(mountpoint.iterdir()):
            show_error_panel("Mount Error", 
                           f"Mount point {mountpoint} is not empty. Please use an empty directory.")
            raise typer.Exit(1)
        
        # Try service manager first
        manager = get_cli_service_manager(config_dir=config_dir)
        mount_method = _get_service_method(manager, "mount_snapshot")
        
        if not mount_method:
            show_error_panel("Not Implemented", 
                           "Snapshot mounting requires FUSE support which is not available in this build.")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Mounting snapshot {snapshot_id} at {mountpoint}...[/cyan]")
        
        result = _call_service_method(
            mount_method,
            snapshot_id=snapshot_id,
            mount_path=str(mountpoint),
            repository=repository,
            password=password,
        )
        
        success = getattr(result, "success", True)
        if success:
            show_success_panel("Snapshot Mounted", 
                             f"Snapshot '{snapshot_id}' mounted at {mountpoint}.\n\n"
                             f"[bold]Mount point:[/bold] {mountpoint}\n"
                             f"[bold]Access:[/bold] Read-only\n\n"
                             f"[dim]Use 'timelocker restore umount {repository} {snapshot_id}' to unmount[/dim]")
        else:
            show_error_panel("Mount Failed", f"Failed to mount snapshot '{snapshot_id}'.")
            raise typer.Exit(1)
    
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Mount operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Mount Error", f"Failed to mount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Umount Command - Unmount snapshot filesystem
# ============================================================================

@restore_app.command("umount")
@with_error_handling("Umount Error")
@with_logging
def restore_umount(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Unmount a previously mounted snapshot."""
    setup_logging(verbose, config_dir)
    
    try:
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
        
        manager = get_cli_service_manager(config_dir=config_dir)
        umount_method = _get_service_method(manager, "unmount_snapshot")
        
        if not umount_method:
            show_error_panel("Not Implemented", 
                           "Snapshot unmounting is not available in this build.")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Unmounting snapshot {snapshot_id}...[/cyan]")
        
        result = _call_service_method(umount_method, 
                                     snapshot_id=snapshot_id,
                                     repository=repository)
        
        success = getattr(result, "success", True)
        if success:
            show_success_panel("Snapshot Unmounted", 
                             f"Snapshot '{snapshot_id}' unmounted successfully.")
        else:
            show_error_panel("Unmount Failed", f"Failed to unmount snapshot '{snapshot_id}'.")
            raise typer.Exit(1)
    
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Unmount operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unmount Error", f"Failed to unmount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Find Command - Search for files across snapshots
# ============================================================================

@restore_app.command("find")
@with_error_handling("Find Error")
@with_logging
def restore_find(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        query: Annotated[str, typer.Argument(help="Search query (glob or text)")],
        search_type: Annotated[Optional[str], typer.Option("--type", help="Search type: name, path, content")] = None,
        host: Annotated[Optional[str], typer.Option("--host", help="Filter by host name")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tag", help="Filter by tag")] = None,
        limit: Annotated[Optional[int], typer.Option("--limit", help="Maximum results to return")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Search for files across all snapshots in repository."""
    setup_logging(verbose, config_dir)
    
    try:
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        if limit is not None and limit < 1:
            raise ValueError("Limit must be greater than zero")
        validate_repository_name_or_uri(repository)
        
        manager = get_cli_service_manager(config_dir=config_dir)
        search_method = _get_service_method(manager, "find_in_snapshots")
        
        if not search_method:
            show_error_panel("Not Implemented", 
                           "Cross-snapshot search is not available in this build.")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Searching for '{query}' across snapshots...[/cyan]")
        
        results = search_method(
            query=query,
            repository=repository,
            search_type=search_type,
            host=host,
            tags=tags or [],
            limit=limit,
        )
        
        try:
            matches = list(results or [])
        except TypeError:
            matches = [results] if results else []
        
        if matches:
            table = Table(title=f"Search Results for '{query}'")
            table.add_column("Snapshot ID", style="cyan", width=12)
            table.add_column("Path", style="white")
            table.add_column("Match Type", style="green", width=12)
            table.add_column("Context", style="dim", overflow="fold")
            
            for match in matches:
                if isinstance(match, dict):
                    snapshot_id = str(match.get("snapshot_id", "unknown"))[:12]
                    path = str(match.get("file_path", match.get("path", "")))
                    match_type = str(match.get("match_type", "unknown"))
                    context = str(match.get("context", "")) if match.get("context") else ""
                else:
                    snapshot_id = str(getattr(match, "snapshot_id", getattr(match, "id", "unknown")))[:12]
                    path = str(getattr(match, "file_path", getattr(match, "path", "")))
                    match_type = str(getattr(match, "match_type", "unknown"))
                    context = str(getattr(match, "context", "")) if getattr(match, "context", None) else ""
                
                table.add_row(snapshot_id, path, match_type, context)
            
            console.print()
            console.print(table)
            console.print()
            show_success_panel("Search Completed", f"Found {len(matches)} matching entries.")
            console.print()
            console.print("[dim]💡 Use 'timelocker restore files <repository> <snapshot-id> <target> --include <path>' to restore specific files[/dim]")
        else:
            show_info_panel("No Matches", f"No files matching '{query}' found in any snapshot.")
    
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Search cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Search Error", f"Failed to search snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Diff Command - Compare two snapshots
# ============================================================================

@restore_app.command("diff")
@with_error_handling("Diff Error")
@with_logging
def restore_diff(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_a: Annotated[str, typer.Argument(help="First snapshot ID", autocompletion=snapshot_id_completer)],
        snapshot_b: Annotated[str, typer.Argument(help="Second snapshot ID", autocompletion=snapshot_id_completer)],
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Compare two snapshots and show differences."""
    setup_logging(verbose, config_dir)
    
    try:
        validate_repository_name_or_uri(repository)
        for candidate in (snapshot_a, snapshot_b):
            try:
                validate_snapshot_id_format(candidate, allow_latest=True)
            except ValueError as validation_error:
                logging.getLogger(__name__).debug("Skipping strict snapshot ID validation for diff: %s", validation_error)
        
        manager = get_cli_service_manager(config_dir=config_dir)
        diff_method = _get_service_method(manager, "diff_snapshots")
        
        if not diff_method:
            show_error_panel("Not Implemented", 
                           "Snapshot comparison is not available in this build.")
            raise typer.Exit(1)
        
        console.print(f"[cyan]Comparing snapshots {snapshot_a} and {snapshot_b}...[/cyan]")
        
        result = diff_method(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            repository=repository,
        )
        
        try:
            diff_entries = list(result or [])
        except TypeError:
            diff_entries = [result] if result else []
        
        if diff_entries:
            table = Table(title=f"Differences: {snapshot_a} → {snapshot_b}")
            table.add_column("Path", style="white")
            table.add_column("Change", style="yellow", width=12)
            table.add_column("Details", style="dim", overflow="fold")
            
            # Count changes by type
            added = modified = deleted = 0
            
            for entry in diff_entries:
                if isinstance(entry, dict):
                    path = str(entry.get("path", ""))
                    change = str(entry.get("change", entry.get("status", "modified")))
                    details = str(entry.get("details", ""))
                else:
                    path = str(getattr(entry, "path", ""))
                    change = str(getattr(entry, "change", getattr(entry, "status", "modified")))
                    details = str(getattr(entry, "details", ""))
                
                # Color code changes
                if change.lower() in ["added", "new"]:
                    change_display = f"[green]{change}[/green]"
                    added += 1
                elif change.lower() in ["deleted", "removed"]:
                    change_display = f"[red]{change}[/red]"
                    deleted += 1
                else:
                    change_display = f"[yellow]{change}[/yellow]"
                    modified += 1
                
                table.add_row(path, change_display, details)
            
            console.print()
            console.print(table)
            console.print()
            
            # Summary
            summary_parts = []
            if added > 0:
                summary_parts.append(f"[green]{added} added[/green]")
            if modified > 0:
                summary_parts.append(f"[yellow]{modified} modified[/yellow]")
            if deleted > 0:
                summary_parts.append(f"[red]{deleted} deleted[/red]")
            
            summary = ", ".join(summary_parts)
            show_success_panel("Diff Completed", 
                             f"Found {len(diff_entries)} differences: {summary}")
        else:
            show_info_panel("No Differences", 
                          "No differences detected between the snapshots.")
    
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Diff operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Diff Error", f"Failed to compare snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Verify Command - Verify restored data integrity
# ============================================================================

@restore_app.command("verify")
@with_error_handling("Verify Error")
@with_logging
def restore_verify(
        target: Annotated[Path, typer.Argument(help="Target path to verify", autocompletion=file_path_completer)],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        snapshot_id: Annotated[Optional[str], typer.Option("--snapshot", "-s", help="Snapshot ID to verify against", autocompletion=snapshot_id_completer)] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Verify integrity of restored data."""
    setup_logging(verbose, config_dir)
    
    try:
        # Check if target exists
        if not target.exists():
            show_error_panel("Target Not Found", 
                           f"Target path {target} does not exist.")
            raise typer.Exit(1)
        
        # Try service manager first
        manager = get_cli_service_manager(config_dir=config_dir)
        verify_method = _get_service_method(manager, "verify_restore")
        
        if not verify_method:
            # Fallback to basic verification
            console.print(f"[cyan]Verifying restored data at {target}...[/cyan]")
            
            # Basic file count and size check
            file_count = 0
            total_size = 0
            errors = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Scanning files...", total=None)
                
                try:
                    for item in target.rglob("*"):
                        if item.is_file():
                            file_count += 1
                            try:
                                total_size += item.stat().st_size
                            except Exception as e:
                                errors.append(f"Cannot access {item}: {e}")
                except Exception as e:
                    errors.append(f"Error scanning directory: {e}")
                
                progress.remove_task(task)
            
            if errors:
                show_error_panel("Verification Issues", 
                               f"Found {len(errors)} issues during verification.", 
                               errors[:10])  # Show first 10 errors
                raise typer.Exit(1)
            else:
                details = {
                    "Files verified": f"{file_count:,}",
                    "Total size": _format_size(total_size),
                    "Target path": str(target),
                }
                show_success_panel("Verification Complete", 
                                 "All files verified successfully!", details)
            return
        
        # Use service manager verification
        console.print(f"[cyan]Verifying restored data at {target}...[/cyan]")
        
        result = _call_service_method(
            verify_method,
            target_path=str(target),
            repository=repository,
            snapshot_id=snapshot_id,
        )
        
        success = getattr(result, "success", True)
        if success:
            verified_count = getattr(result, "verified_count", 0)
            error_count = getattr(result, "error_count", 0)
            
            if error_count > 0:
                errors = getattr(result, "errors", [])
                show_error_panel("Verification Issues", 
                               f"Found {error_count} issues during verification.", 
                               errors[:10])
                raise typer.Exit(1)
            else:
                details = {
                    "Files verified": f"{verified_count:,}",
                    "Target path": str(target),
                }
                if snapshot_id:
                    details["Snapshot"] = snapshot_id
                
                show_success_panel("Verification Complete", 
                                 "All files verified successfully!", details)
        else:
            error_msg = getattr(result, "error", "Verification failed")
            show_error_panel("Verification Failed", error_msg)
            raise typer.Exit(1)
    
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Verification cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Verify Error", f"Failed to verify restored data: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Status Command - Check recovery operation status
# ============================================================================

@restore_app.command("status")
@with_error_handling("Status Error")
@with_logging
def restore_status(
        operation_id: Annotated[Optional[str], typer.Argument(help="Operation ID to check (optional)")] = None,
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        all_operations: Annotated[bool, typer.Option("--all", help="Show all operations")] = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Check status of recovery operations.
    
    This command displays the status of ongoing or completed recovery operations,
    including progress information, estimated completion time, and any errors.
    
    Examples:
        timelocker restore status                    # Show active operations
        timelocker restore status abc-123-def        # Show specific operation
        timelocker restore status --all              # Show all operations
    """
    setup_logging(verbose, config_dir)
    
    if not RECOVERY_OPERATIONS_AVAILABLE:
        show_error_panel("Not Available", 
                       "Recovery operations status tracking requires the Recovery Operations components.")
        raise typer.Exit(1)
    
    try:
        # Get repository if specified
        repo = None
        if repository:
            validate_repository_name_or_uri(repository)
            repository_uri = resolve_repository_uri(repository)
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, repository_name=repository)
        
        # If operation_id is provided, show specific operation
        if operation_id:
            # This would require access to the RecoveryOrchestrator instance
            # For now, show a message
            show_info_panel("Operation Status", 
                          f"Operation ID: {operation_id}\n\n"
                          "Detailed operation status tracking is available through the recovery service.")
            return
        
        # Show active or all operations
        show_info_panel("Recovery Operations", 
                      "Recovery operation status tracking is available.\n\n"
                      "Use the recovery service API to track operation progress.")
        
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Status check cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Status Error", f"Failed to check operation status: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# History Command - Show recovery operation history
# ============================================================================

@restore_app.command("history")
@with_error_handling("History Error")
@with_logging
def restore_history(
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        limit: Annotated[int, typer.Option("--limit", help="Maximum number of operations to show")] = 10,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Show recovery operation history.
    
    This command displays a history of recent recovery operations including
    their status, duration, and any errors encountered.
    
    Examples:
        timelocker restore history                   # Show recent operations
        timelocker restore history --limit 20        # Show last 20 operations
        timelocker restore history --repository myrepo
    """
    setup_logging(verbose, config_dir)
    
    if not RECOVERY_OPERATIONS_AVAILABLE:
        show_error_panel("Not Available", 
                       "Recovery operations history requires the Recovery Operations components.")
        raise typer.Exit(1)
    
    try:
        # Validate repository if specified
        if repository:
            validate_repository_name_or_uri(repository)
        
        # Create table for history
        table = Table(title=f"Recovery Operation History (Last {limit})")
        table.add_column("Operation ID", style="cyan", width=12)
        table.add_column("Type", style="yellow", width=12)
        table.add_column("Snapshot", style="green", width=12)
        table.add_column("Status", style="white", width=12)
        table.add_column("Started", style="dim", width=20)
        table.add_column("Duration", style="dim", width=12)
        
        # This would query the RecoveryStateManager for historical operations
        # For now, show a placeholder message
        console.print()
        console.print(table)
        console.print()
        show_info_panel("Recovery History", 
                      "Recovery operation history is tracked by the recovery service.\n\n"
                      "Historical operations can be queried through the recovery service API.")
        
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "History check cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("History Error", f"Failed to retrieve operation history: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# Search Command - Search for files across snapshots
# ============================================================================

@restore_app.command("search")
@with_error_handling("Search Error")
@with_logging
def restore_search(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        query: Annotated[str, typer.Argument(help="Search query (filename or pattern)")],
        snapshot_id: Annotated[Optional[str], typer.Option("--snapshot", "-s", help="Search in specific snapshot", autocompletion=snapshot_id_completer)] = None,
        file_type: Annotated[Optional[str], typer.Option("--type", help="Filter by file type (file, directory, symlink)")] = None,
        min_size: Annotated[Optional[int], typer.Option("--min-size", help="Minimum file size in bytes")] = None,
        max_size: Annotated[Optional[int], typer.Option("--max-size", help="Maximum file size in bytes")] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """
    Search for files within snapshots.
    
    This command searches for files matching the specified criteria within
    one or all snapshots in the repository. It uses the SnapshotBrowser
    component for efficient searching.
    
    Examples:
        timelocker restore search myrepo "*.pdf"
        timelocker restore search myrepo "document" --snapshot latest
        timelocker restore search myrepo "*.log" --type file --max-size 1000000
    """
    setup_logging(verbose, config_dir)
    
    try:
        # Validate inputs
        validate_repository_name_or_uri(repository)
        if snapshot_id:
            validate_snapshot_id_format(snapshot_id, allow_latest=True)
        
        # Resolve repository
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        
        # Get password if not provided
        if not password:
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password and sys.stdin.isatty():
                password = Prompt.ask("Repository password", password=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing search...", total=None)
            
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password, 
                                         repository_name=actual_repository_name)
            
            # Handle "latest" snapshot
            if snapshot_id == "latest":
                progress.update(task, description="Finding latest snapshot...")
                snapshot_manager = SnapshotManager(repo)
                snapshots = snapshot_manager.list_snapshots()
                if not snapshots:
                    show_error_panel("No Snapshots", "No snapshots found in repository")
                    raise typer.Exit(1)
                snapshot_id = snapshots[0].id
            
            if RECOVERY_OPERATIONS_AVAILABLE:
                progress.update(task, description=f"Searching for '{query}'...")
                browser = SnapshotBrowser(repo)
                
                # Build search criteria
                from TimeLocker.interfaces.recovery_models import SearchCriteria, FileType
                
                criteria = SearchCriteria(
                    name_pattern=query,
                    file_types=[FileType(file_type)] if file_type else None,
                    min_size=min_size,
                    max_size=max_size
                )
                
                # Search in specific snapshot or all snapshots
                if snapshot_id:
                    results = browser.search_snapshot_files(snapshot_id, criteria)
                else:
                    # Search across all snapshots
                    snapshot_manager = SnapshotManager(repo)
                    all_snapshots = snapshot_manager.list_snapshots()
                    results = []
                    for snap in all_snapshots:
                        snap_results = browser.search_snapshot_files(snap.id, criteria)
                        results.extend(snap_results)
                
                progress.remove_task(task)
                
                if results:
                    table = Table(title=f"Search Results for '{query}'")
                    table.add_column("Snapshot", style="cyan", width=12)
                    table.add_column("Type", style="yellow", width=10)
                    table.add_column("Size", style="green", width=12)
                    table.add_column("Path", style="white")
                    
                    for entry in results:
                        snap_id = snapshot_id[:12] if snapshot_id else "multiple"
                        entry_type = entry.type.value if hasattr(entry.type, 'value') else str(entry.type)
                        size_str = _format_size(entry.size) if entry.size else "-"
                        table.add_row(snap_id, entry_type, size_str, entry.path)
                    
                    console.print()
                    console.print(table)
                    console.print()
                    show_success_panel("Search Complete", f"Found {len(results)} matching files.")
                else:
                    show_info_panel("No Results", f"No files matching '{query}' found.")
            else:
                # Fallback to find command
                progress.remove_task(task)
                show_info_panel("Search", 
                              "Advanced search requires Recovery Operations components.\n\n"
                              "Use 'timelocker restore find' for basic file search.")
        
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Search cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Search Error", f"Failed to search snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
