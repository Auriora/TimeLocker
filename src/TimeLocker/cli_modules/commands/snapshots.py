"""
Snapshot operations.

This module contains CLI commands for snapshot operations.
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

# Import setup_logging from cli module
setup_logging = _cli_module.setup_logging

# Module-specific imports
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
    target_name_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri,
    get_default_repository
)
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format
from datetime import datetime
import subprocess

# Create Typer app
snapshots_app = create_typer_app(
    name="snapshots",
    help_text="Snapshot operations"
)



# Commands

@snapshots_app.command("restore")
@with_error_handling("Restore Error")
@with_logging
def snapshots_restore(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        target: Annotated[Path, typer.Argument(help="Target path for restore", autocompletion=file_path_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        preview: Annotated[bool, typer.Option("--preview", help="Preview restore without executing")] = False,
        confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompts")] = False,
        verbose: VerboseOption = False,
) -> None:
    """Restore files from this snapshot."""
    setup_logging(verbose)
    interactive = sys.stdin.isatty()

    # Validate inputs early
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)

    try:
        service_manager = get_cli_service_manager()
    except Exception:
        service_manager = None

    if service_manager:
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
                    success_flag = getattr(restore_result, "is_successful", restore_result if isinstance(restore_result, bool) else False)
                if bool(success_flag):
                    show_success_panel("Restore Completed", "Snapshot restored successfully.")
                    return
            except click.exceptions.Exit:
                raise
            except Exception as exc:
                logging.getLogger(__name__).debug("Service restore failed, falling back to local flow: %s", exc)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri, get_default_repository

        # Get the actual repository name (for credential manager)
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                if interactive:
                    password = Prompt.ask("Repository password", password=True)
                else:
                    show_error_panel("Repository Error",
                                     "Repository password is required; provide --password or set RESTIC_PASSWORD when running non-interactively.")
                    raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

    # Use the provided snapshot_id directly
    snapshot = snapshot_id
    if snapshot == "latest":
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Finding latest snapshot...", total=None)
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password, repository_name=actual_repository_name)
            snapshot_manager = SnapshotManager(repo)
            snapshots = snapshot_manager.list_snapshots()

            if not snapshots:
                show_error_panel("No Snapshots", "No snapshots found in repository")
                raise typer.Exit(1)

            snapshot = snapshots[0].id  # Assuming first is latest
            console.print(f"📸 Using latest snapshot: [bold cyan]{snapshot[:12]}[/bold cyan]")
            progress.remove_task(task)

    if not snapshot:
        if interactive:
            snapshot = Prompt.ask("Snapshot ID to restore")
        else:
            show_error_panel("Missing Parameter", "Snapshot ID is required when running non-interactively.")
            raise typer.Exit(1)

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

    # Confirm destructive operation (unless --confirm flag is used)
    if not confirm:
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
            repo = backup_manager.from_uri(repository_uri, password=password, repository_name=actual_repository_name)

            # Initialize restore manager with repository
            restore_manager = RestoreManager(repo)

            # Create restore options (simplified for CLI)
            progress.update(task, description="Preparing restore options...")
            from .restore_manager import RestoreOptions
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
                    "Target path":    str(target),
                    "Duration":       f"{getattr(result, 'duration_seconds', 0):.1f}s"
            }
            if hasattr(result, 'files_skipped') and result.files_skipped > 0:
                details["Files skipped"] = f"{result.files_skipped:,}"

            show_success_panel("Restore Completed", "Files restored successfully!", details)
        else:
            error_details = getattr(result, 'errors', []) if hasattr(result, 'errors') else []
            show_error_panel("Restore Failed", f"Restore operation failed: {getattr(result, 'error', 'Unknown error')}", error_details)
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Restore operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Restore Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("list")
@with_error_handling("List Error")
@with_logging
def snapshots_list(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """List snapshots in repository with a beautiful table."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()

    repository_input = repository or ""
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

        table = Table(title=f"Snapshots ({len(service_snapshots)})")
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
        return

    try:
        if repository_input:
            validate_repository_name_or_uri(repository_input)
    except ValueError as ve:
        show_error_panel("Invalid Repository", str(ve))
        raise typer.Exit(1)

    try:
        from .utils.repository_resolver import resolve_repository_uri, get_repository_info, get_default_repository

        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        repo_info = get_repository_info(actual_repository_name or repository_uri)

        if verbose or not repository:
            if repo_info.get("is_named"):
                console.print(f"[dim]Using repository: {repo_info.get('name')} ({repository_uri})[/dim]")
            else:
                console.print(f"[dim]Using repository: {repository_uri}[/dim]")

        backup_manager = BackupManager()
        repo = backup_manager.from_uri(repository_uri, password=password, repository_name=actual_repository_name)

        resolved_password = repo.password()
        if not resolved_password:
            if repo_info.get("is_named"):
                console.print(f"[yellow]Repository '{repo_info.get('name')}' requires a password.[/yellow]")
                console.print(f"[dim]💡 Store password permanently: tl repos add {repo_info.get('name')} {repository_uri}[/dim]")
            else:
                console.print(f"[yellow]Repository {repository_uri} requires a password.[/yellow]")

            if interactive:
                resolved_password = Prompt.ask("Repository password", password=True)
            else:
                show_error_panel(
                        "Repository Error",
                        "Repository password is required; provide --password or set RESTIC_PASSWORD when running non-interactively."
                )
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
                title=f"📸 Found {len(snapshots)} snapshots",
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

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "List operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("List Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("show")
@with_error_handling("Show Error")
@with_logging
def snapshots_show(
        snapshot_id: Annotated[Optional[str], typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)] = None,
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        verbose: VerboseOption = False,
) -> None:
    """Display snapshot details including metadata and paths."""
    setup_logging(verbose)
    try:
        if snapshot_id is None:
            show_error_panel("Missing Parameter", "Missing required snapshot ID parameter")
            raise typer.Exit(2)
        if repository:
            validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)

        manager = get_cli_service_manager()
        details_method = _get_service_method(manager, "get_snapshot_details")
        if not details_method:
            show_error_panel("Not Implemented", "Snapshot 'show' command is not implemented yet")
            raise typer.Exit(1)

        details = _call_service_method(
                details_method,
                snapshot_id=snapshot_id,
                repository=repository
        )

        if details is None:
            show_info_panel("Snapshot Details", "No details available for this snapshot.")
            return

        if isinstance(details, dict):
            detail_map = dict(details)
        else:
            detail_map = {
                    "ID":        getattr(details, "id", snapshot_id),
                    "Timestamp": getattr(details, "time", getattr(details, "timestamp", "unknown")),
                    "Hostname":  getattr(details, "hostname", "unknown"),
                    "Username":  getattr(details, "username", "unknown"),
                    "Paths":     getattr(details, "paths", []),
                    "Tags":      getattr(details, "tags", []),
            }

        rendered_lines = []
        for key, value in detail_map.items():
            if isinstance(value, (list, tuple, set)):
                try:
                    display_value = ", ".join(str(item) for item in value)
                except TypeError:
                    display_value = str(value)
            else:
                display_value = str(value)
            rendered_lines.append(f"[bold]{key}:[/bold] {display_value}")

        console.print(Panel("\n".join(rendered_lines), title=f"Snapshot {snapshot_id}", border_style="blue"))
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Snapshot Error", f"Failed to retrieve snapshot details: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("contents")
@with_error_handling("Contents Error")
@with_logging
def snapshots_contents(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        path: Annotated[Optional[str], typer.Option("--path", help="Filter contents to a specific path prefix")] = None,
        verbose: VerboseOption = False,
) -> None:
    setup_logging(verbose)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)

        manager = get_cli_service_manager()
        contents_method = _get_service_method(manager, "list_snapshot_contents")
        if not contents_method:
            show_error_panel("Not Implemented", "Snapshot 'contents' command is not implemented yet")
            raise typer.Exit(1)

        contents = _call_service_method(
                contents_method,
                snapshot_id=snapshot_id,
                repository=repository,
                path=path,
                path_filter=path
        ) or []

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

        table = Table(title=f"Contents of {snapshot_id}")
        table.add_column("Type", style="cyan")
        table.add_column("Size", style="green")
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

            table.add_row(str(entry_type), str(size), str(path_value))

        console.print(table)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Snapshot Error", f"Failed to list snapshot contents: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("mount")
@with_error_handling("Mount Error")
@with_logging
def snapshots_mount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        mount_point: Annotated[Path, typer.Argument(help="Mount point", autocompletion=file_path_completer)],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        verbose: VerboseOption = False,
) -> None:
    """Mount a snapshot as a read-only filesystem for browsing."""
    setup_logging(verbose)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)

        manager = get_cli_service_manager()
        mount_method = _get_service_method(manager, "mount_snapshot")
        if not mount_method:
            show_error_panel("Not Implemented", "Snapshot 'mount' command is not implemented yet")
            raise typer.Exit(1)

        result = _call_service_method(
                mount_method,
                snapshot_id=snapshot_id,
                mount_path=mount_point,
                repository=repository
        )
        success = getattr(result, "success", True)
        if success:
            show_success_panel("Snapshot Mounted", f"Snapshot '{snapshot_id}' mounted at {mount_point}.")
        else:
            show_error_panel("Mount Failed", f"Failed to mount snapshot '{snapshot_id}'.")
            raise typer.Exit(1)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Mount Error", f"Failed to mount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("umount")
@with_error_handling("Umount Error")
@with_logging
def snapshots_umount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        verbose: VerboseOption = False,
) -> None:
    setup_logging(verbose)
    try:
        validate_snapshot_id_format(snapshot_id, allow_latest=True)
        manager = get_cli_service_manager()
        umount_method = _get_service_method(manager, "unmount_snapshot")
        if not umount_method:
            show_error_panel("Not Implemented", "Snapshot 'umount' command is not implemented yet")
            raise typer.Exit(1)

        result = _call_service_method(umount_method, snapshot_id=snapshot_id)
        success = getattr(result, "success", True)
        if success:
            show_success_panel("Snapshot Unmounted", f"Snapshot '{snapshot_id}' unmounted successfully.")
        else:
            show_error_panel("Unmount Failed", f"Failed to unmount snapshot '{snapshot_id}'.")
            raise typer.Exit(1)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unmount Error", f"Failed to unmount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("forget")
@with_error_handling("Forget Error")
@with_logging
def snapshots_forget(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        yes: YesOption = False,
        verbose: VerboseOption = False,
        config_dir: ConfigDirOption = None,
) -> None:
    """Forget (remove) a specific snapshot."""
    setup_logging(verbose, config_dir)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        validate_snapshot_id_format(snapshot_id, allow_latest=True)

        # Get repository name for confirmation
        repo_name = repository or "default"
        
        # Get repository information for confirmation
        try:
            config_manager = ConfigurationManager(config_dir=config_dir)
            if repository:
                repo_config = config_manager.get_repository(repository)
            else:
                repo_config = config_manager.get_default_repository()
                repo_name = repo_config.get('name', 'default')
        except ConfigurationError:
            repo_config = {'uri': repository or 'Unknown'}

        # Create repository info for confirmation
        repository_info = {
            'repository_id': repo_name,
            'name': repo_name,
            'location': repo_config.get('uri', 'Unknown'),
            'mode': 'read_write'  # Default mode
        }

        # Initialize security service for confirmation
        security_service, access_manager = _create_security_manager(config_dir)

        # Validate session for snapshot operations
        if not _validate_session_for_operation(access_manager, "snapshot_delete", repo_name):
            show_error_panel("Authentication Required", 
                           "Session authentication failed. Please ensure you have proper access.")
            raise typer.Exit(1)

        # Check if repository is locked
        if security_service.is_repository_locked(repo_name):
            show_error_panel("Repository Locked", 
                           f"Repository '{repo_name}' is currently locked and snapshots cannot be modified. "
                           f"Please unlock it first using 'timelocker repos unlock {repo_name}'.")
            raise typer.Exit(1)

        # Check if operation is allowed
        if not security_service.is_operation_allowed(repo_name, "delete"):
            mode = security_service.get_repository_mode(repo_name)
            show_error_panel("Operation Not Allowed", 
                           f"Repository '{repo_name}' is in {mode} mode and does not allow snapshot deletion.")
            raise typer.Exit(1)

        # Use enhanced confirmation for snapshot deletion
        if not yes:
            try:
                # Create confirmation dialogs
                confirmation_dialogs = ConfirmationDialogs()
                
                # Create repository info object
                from .security import RepositoryInfo, RepositoryMode
                repo_info = RepositoryInfo(
                    repository_id=repo_name,
                    name=repo_name,
                    location=repository_info['location'],
                    mode=RepositoryMode.READ_WRITE
                )
                
                confirmed = confirmation_dialogs.confirm_snapshot_deletion(
                    repo_info, snapshot_id, force=False
                )
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Snapshot deletion cancelled.")
                    raise typer.Exit(0)
            except Exception as e:
                # Fallback to simple confirmation if security service fails
                logger.warning(f"Security confirmation failed, using simple confirmation: {e}")
                interactive = sys.stdin.isatty()
                if interactive:
                    confirmed = Confirm.ask(f"Delete snapshot '{snapshot_id}' from repository '{repo_name}'?", default=False)
                    if not confirmed:
                        show_info_panel("Operation Cancelled", "Snapshot deletion cancelled.")
                        raise typer.Exit(0)

        # TODO: Implement actual snapshot deletion
        show_error_panel("Not Implemented", "Snapshot 'forget' command implementation is pending")
        raise typer.Exit(1)
        
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Forget Error", f"Failed to forget snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("find")
@with_error_handling("Find Error")
@with_logging
def snapshots_find(
        query: Annotated[str, typer.Argument(help="Search query (glob or text)")],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        search_type: Annotated[Optional[str], typer.Option("--type", help="Search type: name, path, content")] = None,
        host: Annotated[Optional[str], typer.Option("--host", help="Filter by host name")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tag", help="Filter by tag", autocompletion=target_name_completer)] = None,
        limit: Annotated[Optional[int], typer.Option("--limit", help="Maximum results to return")] = None,
        verbose: VerboseOption = False,
) -> None:
    """Search across snapshots for matching files or metadata."""
    setup_logging(verbose)
    try:
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        if limit is not None and limit < 1:
            raise ValueError("Limit must be greater than zero")
        if repository:
            validate_repository_name_or_uri(repository)

        manager = get_cli_service_manager()
        search_method = _get_service_method(manager, "find_in_snapshots")
        if not search_method:
            show_error_panel("Not Implemented", "Snapshot search is not available in this build.")
            raise typer.Exit(1)

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
            table = Table(title="Snapshot Search Results")
            table.add_column("Snapshot ID")
            table.add_column("Path")
            table.add_column("Match Type")
            table.add_column("Context", overflow="fold")

            for match in matches:
                if isinstance(match, dict):
                    snapshot_id = str(match.get("snapshot_id", "unknown"))
                    path = str(match.get("file_path", match.get("path", "")))
                    match_type = str(match.get("match_type", "unknown"))
                    context = str(match.get("context", "")) if match.get("context") else ""
                else:
                    snapshot_id = str(getattr(match, "snapshot_id", getattr(match, "id", "unknown")))
                    path = str(getattr(match, "file_path", getattr(match, "path", "")))
                    match_type = str(getattr(match, "match_type", "unknown"))
                    context = str(getattr(match, "context", "")) if getattr(match, "context", None) else ""
                table.add_row(snapshot_id, path, match_type, context)

            console.print(table)
            show_success_panel("Search Completed", f"Found {len(matches)} matching entries.")
        else:
            show_info_panel("No Matches", "No snapshots matched the query.")
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




@snapshots_app.command("prune")
@with_error_handling("Prune Error")
@with_logging
def snapshots_prune(
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        dry_run: DryRunOption = False,
        verbose: VerboseOption = False,
) -> None:
    """Prune unused data from repository snapshots."""
    setup_logging(verbose)
    try:
        if repository:
            validate_repository_name_or_uri(repository)

        manager = get_cli_service_manager()
        prune_method = _get_service_method(manager, "prune_snapshots")
        if not prune_method:
            show_error_panel("Not Implemented", "Snapshot pruning is not available in this build.")
            raise typer.Exit(1)

        result = prune_method(repository=repository, dry_run=dry_run)
        success = getattr(result, "success", True)

        if success:
            message = "Prune operation completed successfully."
            if dry_run:
                message = "Dry-run completed. No data was modified."
            show_success_panel("Prune Completed", message)
        else:
            errors = getattr(result, "errors", None)
            error_details = errors if isinstance(errors, list) else None
            show_error_panel("Prune Failed", "Snapshot prune operation failed.", error_details)
            raise typer.Exit(1)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Prune operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Prune Error", f"Failed to prune snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@snapshots_app.command("diff")
@with_error_handling("Diff Error")
@with_logging
def snapshots_diff(
        snapshot_a: Annotated[str, typer.Argument(help="First snapshot ID", autocompletion=snapshot_id_completer)],
        snapshot_b: Annotated[str, typer.Argument(help="Second snapshot ID", autocompletion=snapshot_id_completer)],
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        verbose: VerboseOption = False,
) -> None:
    """Show differences between two snapshots."""
    setup_logging(verbose)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        for candidate in (snapshot_a, snapshot_b):
            try:
                validate_snapshot_id_format(candidate, allow_latest=True)
            except ValueError as validation_error:
                logging.getLogger(__name__).debug("Skipping strict snapshot ID validation for diff: %s", validation_error)

        manager = get_cli_service_manager()
        diff_method = _get_service_method(manager, "diff_snapshots")
        if not diff_method:
            show_error_panel("Not Implemented", "Snapshot diff is not available in this build.")
            raise typer.Exit(1)

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
            table = Table(title=f"Diff: {snapshot_a} → {snapshot_b}")
            table.add_column("Path")
            table.add_column("Change")
            table.add_column("Details", overflow="fold")

            for entry in diff_entries:
                if isinstance(entry, dict):
                    path = str(entry.get("path", ""))
                    change = str(entry.get("change", entry.get("status", "modified")))
                    details = str(entry.get("details", ""))
                else:
                    path = str(getattr(entry, "path", ""))
                    change = str(getattr(entry, "change", getattr(entry, "status", "modified")))
                    details = str(getattr(entry, "details", ""))
                table.add_row(path, change, details)

            console.print(table)
            show_success_panel("Diff Completed", f"Displayed {len(diff_entries)} differences.")
        else:
            show_info_panel("No Differences", "No differences detected between the snapshots.")
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


# Security Commands

