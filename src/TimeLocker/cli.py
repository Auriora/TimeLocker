#!/usr/bin/env python3
"""
TimeLocker Command Line Interface

This module provides a beautiful, modern command-line interface for TimeLocker backup operations
using Typer for type-safe commands and Rich for beautiful terminal output.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List, Annotated
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.text import Text
from rich.tree import Tree
from rich import print as rprint

from . import __version__
from .backup_manager import BackupManager
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType
from .restore_manager import RestoreManager
from .snapshot_manager import SnapshotManager
from .config import ConfigurationManager

# Initialize Rich console for consistent output
console = Console()

# Initialize Typer app
app = typer.Typer(
        name="timelocker",
        help="TimeLocker - Beautiful backup operations with Rich terminal output",
        epilog="Made with ❤️  by Bruce Cherrington",
        rich_markup_mode="rich",
        no_args_is_help=True,
)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration with Rich integration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Configure logging to work well with Rich
    logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[logging.StreamHandler()]
    )


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def show_success_panel(title: str, message: str, details: Optional[dict] = None) -> None:
    """Display a success panel with optional details."""
    content = f"✅ {message}"
    if details:
        content += "\n\n"
        for key, value in details.items():
            content += f"[bold]{key}:[/bold] {value}\n"

    panel = Panel(
            content.strip(),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            padding=(1, 2)
    )
    console.print(panel)


def show_error_panel(title: str, message: str, details: Optional[List[str]] = None) -> None:
    """Display an error panel with optional details."""
    content = f"❌ {message}"
    if details:
        content += "\n\n[bold]Details:[/bold]\n"
        for detail in details:
            content += f"• {detail}\n"

    panel = Panel(
            content.strip(),
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
            padding=(1, 2)
    )
    console.print(panel)


def show_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    panel = Panel(
            f"ℹ️  {message}",
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
            padding=(1, 2)
    )
    console.print(panel)


@app.command()
def backup(
        sources: Annotated[List[Path], typer.Argument(help="Source paths to backup")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        name: Annotated[Optional[str], typer.Option("--name", "-n", help="Backup target name")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", "-t", help="Backup tags")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Create a backup with beautiful progress tracking."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not repository:
        repository = Prompt.ask("Repository URI")
    if not password:
        password = Prompt.ask("Repository password", password=True)

    try:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console,
        ) as progress:

            # Initialize backup manager
            task = progress.add_task("Initializing backup...", total=None)
            manager = BackupManager()

            # Create repository
            progress.update(task, description="Connecting to repository...")
            repo = manager.from_uri(repository, password=password)

            # Create backup target
            progress.update(task, description="Creating backup target...")
            target = BackupTarget(
                    name=name or "cli_backup",
                    source_paths=[str(p) for p in sources],
                    repository_uri=repository,
                    password=password
            )

            # Add file selections if specified
            if exclude:
                progress.update(task, description="Adding exclusion patterns...")
                for pattern in exclude:
                    target.add_file_selection(FileSelection(
                            pattern=pattern,
                            selection_type=SelectionType.EXCLUDE
                    ))

            if include:
                progress.update(task, description="Adding inclusion patterns...")
                for pattern in include:
                    target.add_file_selection(FileSelection(
                            pattern=pattern,
                            selection_type=SelectionType.INCLUDE
                    ))

            # Perform backup
            progress.update(task, description="Executing backup...")
            result = manager.execute_backup_with_retry(repo, [target], tags)

            progress.remove_task(task)

        # Display results
        if result and "snapshot_id" in result:
            details = {
                    "Snapshot ID":     result.get("snapshot_id", "Unknown"),
                    "Files processed": f"{result.get('files_new', 0) + result.get('files_changed', 0) + result.get('files_unmodified', 0):,}",
                    "Data added":      result.get("data_added_formatted", "Unknown"),
                    "Duration":        f"{result.get('duration_seconds', 0):.1f}s"
            }
            show_success_panel("Backup Completed", "Backup operation completed successfully!", details)
        else:
            error_msg = result.get("error", "Unknown error") if isinstance(result, dict) else "Backup failed"
            show_error_panel("Backup Failed", f"Backup operation failed: {error_msg}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Backup operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Backup Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def restore(
        target: Annotated[Path, typer.Argument(help="Target path for restore")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        snapshot: Annotated[str, typer.Option("--snapshot", "-s", help="Snapshot ID to restore")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Restore files from a backup snapshot with progress tracking."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not repository:
        repository = Prompt.ask("Repository URI")
    if not password:
        password = Prompt.ask("Repository password", password=True)
    if not snapshot:
        snapshot = Prompt.ask("Snapshot ID to restore")

    # Confirm destructive operation
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
            repo = backup_manager.from_uri(repository, password=password)

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


@app.command("list")
def list_snapshots(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List snapshots in repository with a beautiful table."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not repository:
        repository = Prompt.ask("Repository URI")
    if not password:
        password = Prompt.ask("Repository password", password=True)

    try:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:

            task = progress.add_task("Loading snapshots...", total=None)
            backup_manager = BackupManager()

            # Create repository
            progress.update(task, description="Connecting to repository...")
            repo = backup_manager.from_uri(repository, password=password)

            # Initialize snapshot manager with repository
            snapshot_manager = SnapshotManager(repo)

            # List snapshots
            progress.update(task, description="Retrieving snapshots...")
            snapshots = snapshot_manager.list_snapshots()

            progress.remove_task(task)

        if not snapshots:
            show_info_panel("No Snapshots", "No snapshots found in repository")
            return

        # Create beautiful table
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
            # Format snapshot data
            snapshot_id = snapshot.id[:12] if len(snapshot.id) > 12 else snapshot.id
            date_str = snapshot.time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(snapshot, 'time') else snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            hostname = getattr(snapshot, 'hostname', 'unknown')[:15]

            # Format tags
            tags_str = ",".join(snapshot.tags) if snapshot.tags else ""
            if len(tags_str) > 20:
                tags_str = tags_str[:17] + "..."

            # Format paths
            paths_str = ",".join(str(p) for p in snapshot.paths[:2])
            if len(snapshot.paths) > 2:
                paths_str += f" (+{len(snapshot.paths) - 2} more)"

            table.add_row(
                    snapshot_id,
                    date_str,
                    hostname,
                    tags_str,
                    paths_str
            )

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


@app.command()
def init(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Initialize a new backup repository."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not repository:
        repository = Prompt.ask("Repository URI")
    if not password:
        password = Prompt.ask("Repository password", password=True)

    # Confirm repository creation
    if not Confirm.ask(f"Initialize new repository at [bold]{repository}[/bold]?"):
        show_info_panel("Operation Cancelled", "Repository initialization cancelled by user")
        raise typer.Exit(0)

    try:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:

            task = progress.add_task("Initializing repository...", total=None)
            manager = BackupManager()

            # Initialize repository
            repo = manager.from_uri(repository, password=password)
            repo.init()

            progress.remove_task(task)

        show_success_panel(
                "Repository Initialized",
                "Repository created successfully!",
                {"Repository URI": repository}
        )

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Repository initialization was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Initialization Error", f"Failed to initialize repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information with beautiful formatting."""

    # Create version info panel
    version_info = f"""[bold cyan]TimeLocker[/bold cyan] [green]v{__version__}[/green]

[dim]High-level Python interface for backup operations using Restic[/dim]

[bold]Author:[/bold] Bruce Cherrington
[bold]License:[/bold] GNU General Public License v3.0
[bold]Repository:[/bold] https://github.com/Auriora/TimeLocker

[italic]Made with ❤️  and powered by Rich + Typer[/italic]"""

    panel = Panel(
            version_info,
            title="[bold blue]📦 TimeLocker Version Info[/bold blue]",
            border_style="blue",
            padding=(1, 2),
            expand=False
    )

    console.print()
    console.print(panel)
    console.print()


def main() -> None:
    """Main entry point for the CLI using Typer."""
    try:
        app()
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Unexpected Error", f"An unexpected error occurred: {e}")
        console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    main()
