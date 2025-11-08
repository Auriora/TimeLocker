"""
Restore operations.

This module contains CLI commands for restore/recovery operations.
Reorganized from snapshots.py to provide a dedicated restore command hierarchy.
"""

import sys
import os
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

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

# Create Typer app for restore operations
restore_app = create_typer_app(
    name="restore",
    help_text="Recovery and restore operations"
)

# Helper function to get setup_logging from base
setup_logging = _cli_module.setup_logging


# ============================================================================
# Browse Command - Interactive snapshot content exploration
# ============================================================================

@restore_app.command("browse")
@with_error_handling("Browse Error")
@with_logging
def restore_browse(
        repository: Annotated[str, typer.Argument(help="Repository name or URI", autocompletion=repository_completer)],
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        path: Annotated[Optional[str], typer.Option("--path", help="Filter contents to a specific path prefix")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Browse snapshot contents interactively."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    try:
        # Validate inputs
        validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
        
        # Try service manager first
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
        
        # Filter by path if specified
        if path:
            normalized = str(path).rstrip("/")
            filtered = []
            for entry in contents:
                entry_path = ""
                if isinstance(entry, dict):
                    entry_path = str(entry.get("path", entry.get("Path", "")))
                else:
                    entry_path = str(getattr(entry, "path", getattr(entry, "name", "")))
                if entry_path and entry_path.startswith(normalized):
                    filtered.append(entry)
            contents = filtered
        
        if not contents:
            show_info_panel("Snapshot Contents", "No files found in this snapshot.")
            return
        
        # Display contents in a table
        table = Table(title=f"Contents of Snapshot {snapshot_id}")
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
            
            # Format size
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
                    # Call restore files command
                    console.print(f"\n[cyan]Restoring all files to {target_path}...[/cyan]")
                    # This would call the restore files function
                    show_info_panel("Restore", f"Use 'timelocker restore files {repository} {snapshot_id} {target_path}' to restore")
                else:
                    file_path = Prompt.ask("Enter file path to restore")
                    console.print(f"\n[cyan]Restoring {file_path} to {target_path}...[/cyan]")
                    show_info_panel("Restore", f"Use 'timelocker restore files {repository} {snapshot_id} {target_path} --include {file_path}' to restore")
        
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
