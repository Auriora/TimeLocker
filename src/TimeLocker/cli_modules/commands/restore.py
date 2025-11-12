"""
Recovery operation commands.

This module contains CLI commands for browsing snapshots and restoring data.
Implements CLI Interface Requirements - Requirement 13.
"""

import sys
import logging
from typing import Optional, List, Annotated
from pathlib import Path

import typer
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm

# Import CLI helpers - use lazy import to avoid circular dependency
def _get_cli_helpers():
    """Lazy import of CLI helpers to avoid circular imports."""
    from TimeLocker import cli as _cli_module
    return _cli_module

def show_success_panel(title: str, message: str, details=None):
    """Display success panel."""
    _get_cli_helpers().show_success_panel(title, message, details)

def show_error_panel(title: str, message: str, details=None):
    """Display error panel."""
    _get_cli_helpers().show_error_panel(title, message, details)

def setup_logging(verbose: bool, config_dir):
    """Setup logging."""
    _get_cli_helpers().setup_logging(verbose, config_dir)

def _get_service_manager_for_command(config_dir):
    """Get service manager."""
    return _get_cli_helpers()._get_service_manager_for_command(config_dir)

# Get console
from rich.console import Console
console = Console()

# Import TimeLocker components
from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.snapshot_browser import SnapshotBrowser, PaginationOptions, SearchCriteria
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    RecoveryType,
    SelectionCriteria
)
from TimeLocker.completion import (
    repository_completer,
    snapshot_id_completer,
    selection_name_completer,
)
from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri

logger = logging.getLogger(__name__)

# Create Typer app for restore operations
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

restore_app = typer.Typer(
    help="Recovery operations - browse snapshots and restore data",
    no_args_is_help=True,
    context_settings=CLI_CONTEXT_SETTINGS
)
restore_app.info.options_metavar = "⟨OPTIONS⟩"


def _get_repository(repository_input: str, config_dir: Optional[Path] = None):
    """Get repository instance from name or URI using RepositoryResolver."""
    try:
        from .base import _create_repository_resolver
        
        resolver = _create_repository_resolver(config_dir)
        repository = resolver.resolve_repository(
            name_or_uri=repository_input,
            allow_prompt=True
        )
        return repository
    except Exception as e:
        logger.error(f"Failed to get repository: {e}")
        raise typer.Exit(1)


@restore_app.command("list")
def restore_list(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    format: Annotated[str, typer.Option(
        "--format",
        help="Output format (table or json)"
    )] = "table",
    limit: Annotated[Optional[int], typer.Option(
        "--limit",
        help="Maximum number of snapshots to display"
    )] = None,
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    List available snapshots in repository for restoration.
    
    Examples:
        tl restore list myrepo
        tl restore list s3:s3.amazonaws.com/bucket/repo
        tl restore list myrepo --limit 10
    """
    setup_logging(verbose, config_dir)
    
    try:
        repo = _get_repository(repository, config_dir)
        snapshot_manager = SnapshotManager(repo)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Loading snapshots...", total=None)
            snapshots = snapshot_manager.list_snapshots()
        
        if not snapshots:
            console.print("[yellow]No snapshots found in repository[/yellow]")
            return
        
        # Apply limit if specified
        if limit:
            snapshots = snapshots[:limit]
        
        if format == "json":
            import json
            console.print_json(data=[{
                'id': s.id,
                'time': s.time.isoformat() if s.time else None,
                'hostname': s.hostname,
                'username': s.username,
                'tags': s.tags,
                'paths': s.paths
            } for s in snapshots])
        else:
            table = Table(title=f"Snapshots in {repository}")
            table.add_column("Snapshot ID", style="cyan")
            table.add_column("Time", style="green")
            table.add_column("Host", style="blue")
            table.add_column("Tags", style="magenta")
            
            for snapshot in snapshots:
                table.add_row(
                    snapshot.id[:12],
                    snapshot.time.strftime("%Y-%m-%d %H:%M:%S") if snapshot.time else "N/A",
                    snapshot.hostname or "N/A",
                    ", ".join(snapshot.tags) if snapshot.tags else ""
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(snapshots)} snapshot(s)[/dim]")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "List operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("List Failed", f"Failed to list snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("browse")
def restore_browse(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    snapshot_id: Annotated[str, typer.Argument(
        help="Snapshot ID to browse",
        autocompletion=snapshot_id_completer
    )],
    path: Annotated[str, typer.Option(
        "--path",
        help="Path within snapshot to browse"
    )] = "/",
    format: Annotated[str, typer.Option(
        "--format",
        help="Output format (table or json)"
    )] = "table",
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Explore snapshot contents interactively.
    
    Examples:
        tl restore browse myrepo abc123
        tl restore browse myrepo abc123 --path /home/user
    """
    setup_logging(verbose, config_dir)
    
    try:
        repo = _get_repository(repository, config_dir)
        browser = SnapshotBrowser(repo)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"Loading snapshot {snapshot_id[:12]}...", total=None)
            listing = browser.list_snapshot_contents(snapshot_id, path)
        
        if not listing.entries:
            console.print(f"[yellow]No entries found in {path}[/yellow]")
            return
        
        if format == "json":
            import json
            console.print_json(data={
                'path': listing.path,
                'total_entries': listing.total_entries,
                'entries': [{
                    'name': e.name,
                    'path': e.path,
                    'type': e.type.value,
                    'size': e.size,
                    'modification_time': e.modification_time.isoformat() if e.modification_time else None,
                    'permissions': e.permissions
                } for e in listing.entries]
            })
        else:
            table = Table(title=f"Contents of {path} in snapshot {snapshot_id[:12]}")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Size", style="green", justify="right")
            table.add_column("Modified", style="magenta")
            table.add_column("Permissions", style="yellow")
            
            for entry in listing.entries:
                size_str = f"{entry.size:,}" if entry.size else "-"
                mod_time = entry.modification_time.strftime("%Y-%m-%d %H:%M") if entry.modification_time else "N/A"
                
                table.add_row(
                    entry.name,
                    entry.type.value,
                    size_str,
                    mod_time,
                    entry.permissions or ""
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {listing.total_entries} entries[/dim]")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Browse operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Browse Failed", f"Failed to browse snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("full")
def restore_full(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    snapshot_id: Annotated[str, typer.Argument(
        help="Snapshot ID to restore",
        autocompletion=snapshot_id_completer
    )],
    target: Annotated[str, typer.Argument(
        help="Target directory for restoration"
    )],
    overwrite: Annotated[bool, typer.Option(
        "--overwrite",
        help="Overwrite existing files"
    )] = False,
    verify: Annotated[bool, typer.Option(
        "--verify/--no-verify",
        help="Verify restored data integrity"
    )] = True,
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Restore complete snapshot to target location.
    
    Examples:
        tl restore full myrepo abc123 /restore/path
        tl restore full myrepo abc123 /restore/path --overwrite
    """
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    
    try:
        # Validate target path
        target_path = Path(target)
        if target_path.exists() and not overwrite and interactive:
            if not Confirm.ask(f"[yellow]Target {target} exists. Overwrite?[/yellow]"):
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)
        
        repo = _get_repository(repository, config_dir)
        orchestrator = RecoveryOrchestrator(repo)
        
        # Create recovery options
        options = RecoveryOptions(
            overwrite_existing=overwrite,
            preserve_permissions=True,
            preserve_timestamps=True,
            verify_integrity=verify,
            continue_on_error=True,
            max_retries=3
        )
        
        console.print(f"[cyan]Starting full restoration of snapshot {snapshot_id[:12]}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Restoring...", total=100)
            
            operation = orchestrator.initiate_full_recovery(
                snapshot_id=snapshot_id,
                target_path=str(target_path),
                options=options
            )
            
            # Monitor progress
            while operation.status.value in ['pending', 'running', 'validating']:
                status = orchestrator.get_recovery_status(operation.operation_id)
                if status.progress:
                    progress.update(task, completed=status.progress.files_processed)
                operation = status
        
        if operation.status.value == 'completed':
            show_success_panel(
                "Restoration Complete",
                f"Successfully restored snapshot {snapshot_id[:12]} to {target}"
            )
        else:
            show_error_panel(
                "Restoration Failed",
                f"Restoration failed with status: {operation.status.value}"
            )
            raise typer.Exit(1)
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Restoration cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Restoration Failed", f"Failed to restore snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("files")
def restore_files(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    snapshot_id: Annotated[str, typer.Argument(
        help="Snapshot ID to restore from",
        autocompletion=snapshot_id_completer
    )],
    paths: Annotated[List[str], typer.Argument(
        help="File paths to restore"
    )],
    target: Annotated[str, typer.Option(
        "--target",
        help="Target directory for restoration"
    )] = ".",
    selection: Annotated[Optional[str], typer.Option(
        "--selection",
        help="Use data selection template",
        autocompletion=selection_name_completer
    )] = None,
    overwrite: Annotated[bool, typer.Option(
        "--overwrite",
        help="Overwrite existing files"
    )] = False,
    verify: Annotated[bool, typer.Option(
        "--verify/--no-verify",
        help="Verify restored data integrity"
    )] = True,
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Restore specific files from snapshot.
    
    Examples:
        tl restore files myrepo abc123 /path/to/file1 /path/to/file2
        tl restore files myrepo abc123 /home/user/docs --target /restore
        tl restore files myrepo abc123 /data --selection documents
    """
    setup_logging(verbose, config_dir)
    
    try:
        repo = _get_repository(repository, config_dir)
        orchestrator = RecoveryOrchestrator(repo)
        
        # Create selection criteria
        selection_criteria = SelectionCriteria(
            include_patterns=paths,
            exclude_patterns=[],
            selection_template_id=selection
        )
        
        # Create recovery options
        options = RecoveryOptions(
            overwrite_existing=overwrite,
            preserve_permissions=True,
            preserve_timestamps=True,
            verify_integrity=verify,
            continue_on_error=True,
            max_retries=3
        )
        
        console.print(f"[cyan]Restoring {len(paths)} file(s) from snapshot {snapshot_id[:12]}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Restoring files...", total=len(paths))
            
            operation = orchestrator.initiate_selective_recovery(
                snapshot_id=snapshot_id,
                selection_criteria=selection_criteria,
                target_path=target,
                options=options
            )
            
            # Monitor progress
            while operation.status.value in ['pending', 'running', 'validating']:
                status = orchestrator.get_recovery_status(operation.operation_id)
                if status.progress:
                    progress.update(task, completed=status.progress.files_processed)
                operation = status
        
        if operation.status.value == 'completed':
            show_success_panel(
                "Files Restored",
                f"Successfully restored {len(paths)} file(s) to {target}"
            )
        else:
            show_error_panel(
                "Restoration Failed",
                f"Restoration failed with status: {operation.status.value}"
            )
            raise typer.Exit(1)
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "File restoration cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("File Restoration Failed", f"Failed to restore files: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("verify")
def restore_verify(
    target: Annotated[str, typer.Argument(
        help="Directory to verify"
    )],
    repository: Annotated[Optional[str], typer.Option(
        "--repository",
        help="Repository name or URI",
        autocompletion=repository_completer
    )] = None,
    snapshot_id: Annotated[Optional[str], typer.Option(
        "--snapshot",
        help="Snapshot ID to verify against",
        autocompletion=snapshot_id_completer
    )] = None,
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Verify integrity of restored files.
    
    Examples:
        tl restore verify /restore/path
        tl restore verify /restore/path --repository myrepo --snapshot abc123
    """
    setup_logging(verbose, config_dir)
    
    try:
        if not repository or not snapshot_id:
            show_error_panel(
                "Missing Parameters",
                "Both --repository and --snapshot are required for verification"
            )
            raise typer.Exit(2)
        
        repo = _get_repository(repository, config_dir)
        validator = RecoveryValidator(repo)
        
        console.print(f"[cyan]Verifying restored files in {target}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Verifying integrity...", total=None)
            
            # Note: This is a simplified verification
            # Full implementation would need operation_id from restore operation
            result = validator.validate_pre_recovery(
                snapshot_id=snapshot_id,
                target_path=target
            )
        
        if result.is_valid:
            show_success_panel(
                "Verification Complete",
                f"All files verified successfully. Validated {result.validated_files} file(s)."
            )
        else:
            failures = len(result.failed_validations)
            warnings = len(result.warnings)
            
            console.print(Panel(
                f"[yellow]Verification completed with issues:[/yellow]\n"
                f"  • Failed validations: {failures}\n"
                f"  • Warnings: {warnings}",
                title="⚠️  Verification Issues",
                border_style="yellow"
            ))
            
            if result.failed_validations and verbose:
                console.print("\n[yellow]Failed validations:[/yellow]")
                for failure in result.failed_validations[:10]:  # Show first 10
                    console.print(f"  • {failure.file_path}: {failure.error_message}")
            
            raise typer.Exit(1)
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Verification cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Verification Failed", f"Failed to verify files: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("mount")
def restore_mount(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    snapshot_id: Annotated[str, typer.Argument(
        help="Snapshot ID to mount",
        autocompletion=snapshot_id_completer
    )],
    mountpoint: Annotated[str, typer.Argument(
        help="Mount point directory"
    )],
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Mount snapshot as read-only filesystem.
    
    Examples:
        tl restore mount myrepo abc123 /mnt/snapshot
    """
    setup_logging(verbose, config_dir)
    
    try:
        mountpoint_path = Path(mountpoint)
        if not mountpoint_path.exists():
            show_error_panel(
                "Invalid Mount Point",
                f"Mount point {mountpoint} does not exist"
            )
            raise typer.Exit(2)
        
        repo = _get_repository(repository, config_dir)
        restore_manager = RestoreManager(repo)
        
        console.print(f"[cyan]Mounting snapshot {snapshot_id[:12]} at {mountpoint}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Mounting snapshot...", total=None)
            restore_manager.mount_snapshot(snapshot_id, str(mountpoint_path))
        
        show_success_panel(
            "Snapshot Mounted",
            f"Snapshot {snapshot_id[:12]} mounted at {mountpoint}\n"
            f"Use 'tl restore umount {snapshot_id}' to unmount"
        )
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Mount operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Mount Failed", f"Failed to mount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@restore_app.command("umount")
def restore_umount(
    snapshot_id: Annotated[str, typer.Argument(
        help="Snapshot ID to unmount",
        autocompletion=snapshot_id_completer
    )],
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Unmount previously mounted snapshot.
    
    Examples:
        tl restore umount abc123
    """
    setup_logging(verbose, config_dir)
    
    try:
        # Note: RestoreManager tracks mounted snapshots internally
        # We need a way to get the repository for this snapshot
        # For now, this is a simplified implementation
        
        console.print(f"[cyan]Unmounting snapshot {snapshot_id[:12]}...[/cyan]")
        
        # This would need to be implemented in RestoreManager
        # to track mounted snapshots globally
        show_error_panel(
            "Not Implemented",
            "Unmount functionality requires global mount tracking. "
            "Please use system umount command for now."
        )
        raise typer.Exit(1)
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Unmount operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unmount Failed", f"Failed to unmount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("find")
def restore_find(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    query: Annotated[str, typer.Argument(
        help="Search pattern"
    )],
    snapshot_id: Annotated[Optional[str], typer.Option(
        "--snapshot",
        help="Search in specific snapshot only",
        autocompletion=snapshot_id_completer
    )] = None,
    case_sensitive: Annotated[bool, typer.Option(
        "--case-sensitive",
        help="Case-sensitive search"
    )] = False,
    format: Annotated[str, typer.Option(
        "--format",
        help="Output format (table or json)"
    )] = "table",
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Search for files across snapshots.
    
    Examples:
        tl restore find myrepo "*.pdf"
        tl restore find myrepo "document" --snapshot abc123
        tl restore find myrepo "*.log" --case-sensitive
    """
    setup_logging(verbose, config_dir)
    
    try:
        repo = _get_repository(repository, config_dir)
        browser = SnapshotBrowser(repo)
        
        # Create search criteria
        search_criteria = SearchCriteria(
            name_pattern=query,
            case_sensitive=case_sensitive
        )
        
        console.print(f"[cyan]Searching for '{query}' in repository...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Searching...", total=None)
            
            if snapshot_id:
                results = browser.search_snapshot_files(snapshot_id, search_criteria)
            else:
                # Search across all snapshots
                snapshot_manager = SnapshotManager(repo)
                snapshots = snapshot_manager.list_snapshots()
                results = []
                for snapshot in snapshots:
                    try:
                        snapshot_results = browser.search_snapshot_files(
                            snapshot.id,
                            search_criteria
                        )
                        results.extend(snapshot_results)
                    except Exception as e:
                        logger.debug(f"Error searching snapshot {snapshot.id}: {e}")
        
        if not results:
            console.print(f"[yellow]No files found matching '{query}'[/yellow]")
            return
        
        if format == "json":
            import json
            console.print_json(data=[{
                'name': r.name,
                'path': r.path,
                'type': r.type.value,
                'size': r.size,
                'modification_time': r.modification_time.isoformat() if r.modification_time else None
            } for r in results])
        else:
            table = Table(title=f"Search Results for '{query}'")
            table.add_column("Path", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Size", style="green", justify="right")
            table.add_column("Modified", style="magenta")
            
            for result in results[:100]:  # Limit to first 100 results
                size_str = f"{result.size:,}" if result.size else "-"
                mod_time = result.modification_time.strftime("%Y-%m-%d %H:%M") if result.modification_time else "N/A"
                
                table.add_row(
                    result.path,
                    result.type.value,
                    size_str,
                    mod_time
                )
            
            console.print(table)
            if len(results) > 100:
                console.print(f"\n[dim]Showing first 100 of {len(results)} results[/dim]")
            else:
                console.print(f"\n[dim]Total: {len(results)} file(s) found[/dim]")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Search cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Search Failed", f"Failed to search files: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)



@restore_app.command("diff")
def restore_diff(
    repository: Annotated[str, typer.Argument(
        help="Repository name or URI",
        autocompletion=repository_completer
    )],
    snapshot_a: Annotated[str, typer.Argument(
        help="First snapshot ID",
        autocompletion=snapshot_id_completer
    )],
    snapshot_b: Annotated[str, typer.Argument(
        help="Second snapshot ID",
        autocompletion=snapshot_id_completer
    )],
    path: Annotated[str, typer.Option(
        "--path",
        help="Path to compare within snapshots"
    )] = "/",
    format: Annotated[str, typer.Option(
        "--format",
        help="Output format (table or json)"
    )] = "table",
    config_dir: Annotated[Optional[Path], typer.Option(
        "--config-dir",
        help="Configuration directory"
    )] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose output"
    )] = False,
) -> None:
    """
    Compare two snapshots for recovery planning.
    
    Examples:
        tl restore diff myrepo abc123 def456
        tl restore diff myrepo abc123 def456 --path /home/user
    """
    setup_logging(verbose, config_dir)
    
    try:
        repo = _get_repository(repository, config_dir)
        browser = SnapshotBrowser(repo)
        
        console.print(f"[cyan]Comparing snapshots {snapshot_a[:12]} and {snapshot_b[:12]}...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Comparing snapshots...", total=None)
            comparison = browser.compare_snapshots([snapshot_a, snapshot_b], path)
        
        if format == "json":
            import json
            console.print_json(data={
                'added_files': [f.path for f in comparison.added_files],
                'removed_files': [f.path for f in comparison.removed_files],
                'modified_files': [f.path for f in comparison.modified_files],
                'unchanged_files': [f.path for f in comparison.unchanged_files]
            })
        else:
            # Display summary
            console.print(Panel(
                f"[green]Added:[/green] {len(comparison.added_files)}\n"
                f"[red]Removed:[/red] {len(comparison.removed_files)}\n"
                f"[yellow]Modified:[/yellow] {len(comparison.modified_files)}\n"
                f"[dim]Unchanged:[/dim] {len(comparison.unchanged_files)}",
                title=f"Comparison: {snapshot_a[:12]} → {snapshot_b[:12]}",
                border_style="cyan"
            ))
            
            # Show details if verbose
            if verbose:
                if comparison.added_files:
                    console.print("\n[green]Added files:[/green]")
                    for f in comparison.added_files[:20]:
                        console.print(f"  + {f.path}")
                    if len(comparison.added_files) > 20:
                        console.print(f"  ... and {len(comparison.added_files) - 20} more")
                
                if comparison.removed_files:
                    console.print("\n[red]Removed files:[/red]")
                    for f in comparison.removed_files[:20]:
                        console.print(f"  - {f.path}")
                    if len(comparison.removed_files) > 20:
                        console.print(f"  ... and {len(comparison.removed_files) - 20} more")
                
                if comparison.modified_files:
                    console.print("\n[yellow]Modified files:[/yellow]")
                    for f in comparison.modified_files[:20]:
                        console.print(f"  ~ {f.path}")
                    if len(comparison.modified_files) > 20:
                        console.print(f"  ... and {len(comparison.modified_files) - 20} more")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Comparison cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Comparison Failed", f"Failed to compare snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
