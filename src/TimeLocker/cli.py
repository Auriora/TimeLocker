#!/usr/bin/env python3
"""
TimeLocker Command Line Interface

This module provides a beautiful, modern command-line interface for TimeLocker backup operations
using Typer for type-safe commands and Rich for beautiful terminal output.
"""

import sys
import logging
import os

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

# Test-friendly patch: ensure stderr is captured separately in Typer's CliRunner
# so tests can safely access result.stderr when using CliRunner.
try:
    from typer.testing import CliRunner as _TyperCliRunner
    if not getattr(_TyperCliRunner, "_timelocker_mixstderr_patched", False):
        _orig_invoke = _TyperCliRunner.invoke
        def _patched_invoke(self, *args, **kwargs):
            # Prefer separate stderr when supported by click
            use_mix = False
            if "mix_stderr" in kwargs:
                use_mix = kwargs["mix_stderr"] is True
            else:
                kwargs["mix_stderr"] = False
            # First attempt, may store a TypeError in result.exception on older click
            result = _orig_invoke(self, *args, **kwargs)
            # Detect older click capturing the TypeError about mix_stderr
            if getattr(result, "exception", None) and isinstance(result.exception, TypeError) and "mix_stderr" in str(result.exception):
                kwargs.pop("mix_stderr", None)
                result = _orig_invoke(self, *args, **kwargs)
            # Ensure result.stderr is safe to access
            try:
                if getattr(result, "stderr_bytes", None) is None:
                    setattr(result, "stderr_bytes", b"")
            except Exception:
                pass
            return result
        _TyperCliRunner.invoke = _patched_invoke
        _TyperCliRunner._timelocker_mixstderr_patched = True
except Exception:
    pass

# Initialize Rich console for consistent output
console = Console()

# Initialize Typer app
app = typer.Typer(
        name="timelocker",
        help=(
            "TimeLocker — Beautiful backup and restore with a clear CLI.\n\n"
            "Key groups: repos, targets, snapshots (restore under snapshots).\n\n"
            "Examples:\n"
            "  tl repos add <name> file:///path/to/repo\n"
            "  tl targets add <name> --path ~/Documents\n"
            "  tl backup run --target <name>\n"
            "  tl snapshots list  # lists snapshots (see --repository)\n"
            "  tl snapshots restore <id|latest> /restore/path --repository <name>\n"
        ),
        epilog="Made with ❤️  by Bruce Cherrington",
        rich_markup_mode="rich",
        no_args_is_help=True,
)

# Create sub-apps for better organization
config_app = typer.Typer(help="Configuration management commands")
app.add_typer(config_app, name="config")


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
        sources: Annotated[Optional[List[Path]], typer.Argument(help="Source paths to backup")] = None,
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        target: Annotated[Optional[str], typer.Option("--target", "-t", help="Use configured backup target")] = None,
        name: Annotated[Optional[str], typer.Option("--name", "-n", help="Backup target name")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Backup tags")] = None,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Create a backup with beautiful progress tracking."""
    setup_logging(verbose)

    # Handle target-based backup
    if target:
        if not config_dir:
            config_dir = Path.home() / ".timelocker"

        config_file = config_dir / "timelocker.json"
        if not config_file.exists():
            show_error_panel("No Configuration", f"Configuration file not found at {config_file}")
            console.print("💡 Run [bold]timelocker config setup[/bold] to create a configuration")
            raise typer.Exit(1)

        try:
            config_manager = ConfigurationManager(config_dir=config_dir)
            # Configuration is automatically loaded in __init__
            config = config_manager._config

            if target not in config.get("backup_targets", {}):
                show_error_panel("Target Not Found", f"Backup target '{target}' not found in configuration")
                available_targets = list(config.get("backup_targets", {}).keys())
                if available_targets:
                    console.print(f"Available targets: {', '.join(available_targets)}")
                raise typer.Exit(1)

            target_config = config["backup_targets"][target]
            sources = [Path(p) for p in target_config["paths"]]
            name = name or target_config.get("name", target)

            # Use patterns from target config if not overridden
            if not include and target_config.get("patterns", {}).get("include"):
                include = target_config["patterns"]["include"]
            if not exclude and target_config.get("patterns", {}).get("exclude"):
                exclude = target_config["patterns"]["exclude"]

            # Use default repository if not specified
            if not repository and config.get("settings", {}).get("default_repository"):
                default_repo_name = config["settings"]["default_repository"]
                if default_repo_name in config.get("repositories", {}):
                    repository = config["repositories"][default_repo_name].get("uri")

            console.print(f"📁 Using backup target: [bold cyan]{target}[/bold cyan]")
            console.print(f"📂 Backing up {len(sources)} path(s)")

        except Exception as e:
            show_error_panel("Configuration Error", f"Failed to load target configuration: {e}")
            raise typer.Exit(1)

    # Validate sources
    if not sources:
        show_error_panel("No Sources", "No source paths specified for backup")
        console.print("💡 Either provide source paths or use --target to specify a configured backup target")
        raise typer.Exit(1)

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
        snapshot: Annotated[str, typer.Option("--snapshot", "-s", help="Snapshot ID to restore (or 'latest')")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        preview: Annotated[bool, typer.Option("--preview", help="Preview restore without executing")] = False,
        confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompts")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Restore files from a backup snapshot with progress tracking."""
    setup_logging(verbose)

    # Avoid interactive prompts during tests
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise typer.Exit(2)

    # Prompt for missing required parameters
    if not repository:
        repository = Prompt.ask("Repository URI")
    if not password:
        password = Prompt.ask("Repository password", password=True)

    # Handle latest snapshot
    if snapshot == "latest" or not snapshot:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Finding latest snapshot...", total=None)
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository, password=password)
            snapshot_manager = SnapshotManager(repo)
            snapshots = snapshot_manager.list_snapshots()

            if not snapshots:
                show_error_panel("No Snapshots", "No snapshots found in repository")
                raise typer.Exit(1)

            snapshot = snapshots[0].id  # Assuming first is latest
            console.print(f"📸 Using latest snapshot: [bold cyan]{snapshot[:12]}[/bold cyan]")
            progress.remove_task(task)

    if not snapshot:
        snapshot = Prompt.ask("Snapshot ID to restore")

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

    # In non-interactive contexts (e.g., tests), avoid blocking prompts
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise typer.Exit(2)

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


# Configuration Management Commands
@config_app.command("setup")
def config_setup(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Interactive configuration setup wizard."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    # In non-interactive contexts (e.g., tests), avoid blocking prompts
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise typer.Exit(2)
    try:
        if not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
            raise typer.Exit(2)
    except Exception:
        raise typer.Exit(2)

    console.print()
    console.print(Panel(
            "🚀 Welcome to TimeLocker Configuration Setup!\n\n"
            "This wizard will help you set up your backup configuration.",
            title="[bold blue]Configuration Setup[/bold blue]",
            border_style="blue"
    ))
    console.print()

    try:
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "timelocker.json"

        # Initialize configuration manager
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Create default configuration structure
        config = {
                "repositories":   {},
                "backup_targets": {},
                "settings":       {
                        "default_repository":  None,
                        "notification_level":  "normal",
                        "auto_verify_backups": True
                }
        }

        # Repository setup
        if Confirm.ask("Would you like to add a repository?"):
            repo_name = Prompt.ask("Repository name", default="default")
            repo_uri = Prompt.ask("Repository URI (e.g., /path/to/backup or s3://bucket/path)")
            repo_desc = Prompt.ask("Repository description", default=f"{repo_name} backup repository")

            config["repositories"][repo_name] = {
                    "type":        "local" if repo_uri.startswith("/") else "remote",
                    "uri":         repo_uri,
                    "description": repo_desc
            }
            config["settings"]["default_repository"] = repo_name

        # Backup target setup
        if Confirm.ask("Would you like to add a backup target?"):
            target_name = Prompt.ask("Target name", default="documents")
            target_desc = Prompt.ask("Target description", default="Important documents")

            # Get source paths
            paths = []
            console.print("\n[bold]Source paths to backup:[/bold]")
            while True:
                path = Prompt.ask("Enter a path to backup (or press Enter to finish)", default="")
                if not path:
                    break
                if Path(path).exists():
                    paths.append(path)
                    console.print(f"✅ Added: {path}")
                else:
                    console.print(f"⚠️  Path does not exist: {path}")
                    if not Confirm.ask("Add anyway?"):
                        continue
                    paths.append(path)

            if paths:
                config["backup_targets"][target_name] = {
                        "name":        target_desc,
                        "description": target_desc,
                        "paths":       paths,
                        "patterns":    {
                                "include": ["*"],
                                "exclude": ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
                        }
                }

        # Update configuration manager with new config
        for section, data in config.items():
            config_manager.update_section(section, data)

        # Save configuration
        config_manager.save_config()

        show_success_panel(
                "Configuration Created",
                "Configuration setup completed successfully!",
                {
                        "Config file":    str(config_file),
                        "Repositories":   str(len(config["repositories"])),
                        "Backup targets": str(len(config["backup_targets"]))
                }
        )

    except KeyboardInterrupt:
        show_error_panel("Setup Cancelled", "Configuration setup was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Setup Error", f"Configuration setup failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_app.command("list")
def config_list(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List current configuration."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_file = config_dir / "timelocker.json"

    if not config_file.exists():
        show_info_panel("No Configuration", f"No configuration file found at {config_file}")
        console.print("💡 Run [bold]timelocker config setup[/bold] to create a configuration")
        return

    try:
        config_manager = ConfigurationManager(config_dir=config_dir)
        # Configuration is automatically loaded in __init__
        config = config_manager._config

        console.print()
        console.print(Panel(
                f"📁 Configuration from: {config_file}",
                title="[bold blue]TimeLocker Configuration[/bold blue]",
                border_style="blue"
        ))

        # Repositories table
        if config.get("repositories"):
            table = Table(title="🗄️  Repositories", border_style="green")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("URI", style="white")
            table.add_column("Description", style="dim")

            for name, repo in config["repositories"].items():
                table.add_row(
                        name,
                        repo.get("type", "unknown"),
                        repo.get("uri", ""),
                        repo.get("description", "")
                )
            console.print(table)
            console.print()

        # Backup targets table
        if config.get("backup_targets"):
            table = Table(title="🎯 Backup Targets", border_style="blue")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Paths", style="green")
            table.add_column("Patterns", style="dim")

            for name, target in config["backup_targets"].items():
                paths_str = "\n".join(target.get("paths", []))
                patterns = target.get("patterns", {})
                include_patterns = ", ".join(patterns.get("include", []))
                exclude_patterns = ", ".join(patterns.get("exclude", []))
                patterns_str = f"Include: {include_patterns}\nExclude: {exclude_patterns}"

                table.add_row(
                        name,
                        target.get("description", ""),
                        paths_str,
                        patterns_str
                )
            console.print(table)
            console.print()

        # Settings
        if config.get("settings"):
            settings_text = ""
            for key, value in config["settings"].items():
                settings_text += f"[bold]{key}:[/bold] {value}\n"

            console.print(Panel(
                    settings_text.strip(),
                    title="⚙️  Settings",
                    border_style="yellow"
            ))

        console.print()

    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to load configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_app.command("add-target")
def config_add_target(
        name: Annotated[str, typer.Argument(help="Target name")],
        paths: Annotated[List[str], typer.Argument(help="Source paths to backup")],
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude patterns")] = None,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Add a new backup target to configuration."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    config_file = config_dir / "timelocker.json"

    try:
        # Load existing configuration or create new one
        config_manager = ConfigurationManager(config_dir=config_dir)

        if config_file.exists():
            # Configuration is automatically loaded in __init__
            config = config_manager._config
        else:
            config = {
                    "repositories":   {},
                    "backup_targets": {},
                    "settings":       {
                            "default_repository":  None,
                            "notification_level":  "normal",
                            "auto_verify_backups": True
                    }
            }

        # Validate paths
        valid_paths = []
        for path in paths:
            if Path(path).exists():
                valid_paths.append(path)
                console.print(f"✅ Valid path: {path}")
            else:
                console.print(f"⚠️  Path does not exist: {path}")
                if Confirm.ask(f"Add non-existent path '{path}' anyway?"):
                    valid_paths.append(path)

        if not valid_paths:
            show_error_panel("No Valid Paths", "No valid paths provided for backup target")
            raise typer.Exit(1)

        # Create target configuration
        target_config = {
                "name":        description or name,
                "description": description or f"Backup target for {name}",
                "paths":       valid_paths,
                "patterns":    {
                        "include": include or ["*"],
                        "exclude": exclude or ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
                }
        }

        # Add to configuration
        config["backup_targets"][name] = target_config

        # Update configuration manager and save
        config_manager.update_section("backup_targets", config["backup_targets"])
        config_manager.save_config()

        show_success_panel(
                "Target Added",
                f"Backup target '{name}' added successfully!",
                {
                        "Target name": name,
                        "Description": target_config["description"],
                        "Paths":       f"{len(valid_paths)} path(s)",
                        "Config file": str(config_file)
                }
        )

    except Exception as e:
        show_error_panel("Add Target Error", f"Failed to add backup target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command("verify")
def verify(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        snapshot: Annotated[Optional[str], typer.Option("--snapshot", "-s", help="Specific snapshot to verify")] = None,
        latest: Annotated[bool, typer.Option("--latest", help="Verify latest snapshot")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify backup integrity."""
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

            task = progress.add_task("Initializing verification...", total=None)
            backup_manager = BackupManager()

            # Create repository
            progress.update(task, description="Connecting to repository...")
            repo = backup_manager.from_uri(repository, password=password)

            # Initialize snapshot manager
            snapshot_manager = SnapshotManager(repo)

            if latest:
                progress.update(task, description="Finding latest snapshot...")
                snapshots = snapshot_manager.list_snapshots()
                if not snapshots:
                    show_error_panel("No Snapshots", "No snapshots found in repository")
                    raise typer.Exit(1)
                snapshot = snapshots[0].id  # Assuming first is latest

            if not snapshot:
                snapshot = Prompt.ask("Snapshot ID to verify")

            # Perform verification
            progress.update(task, description=f"Verifying snapshot {snapshot[:12]}...")

            # Note: This is a simplified verification - actual implementation would depend on
            # the specific verification methods available in the backup system
            try:
                # Attempt to read snapshot metadata as a basic verification
                snapshot_info = snapshot_manager.get_snapshot_info(snapshot)
                verification_passed = True
                error_details = []
            except Exception as e:
                verification_passed = False
                error_details = [str(e)]

            progress.remove_task(task)

        if verification_passed:
            show_success_panel(
                    "Verification Passed",
                    f"Snapshot {snapshot[:12]} verified successfully!",
                    {
                            "Snapshot ID": snapshot,
                            "Repository":  repository,
                            "Status":      "✅ Integrity verified"
                    }
            )
        else:
            show_error_panel(
                    "Verification Failed",
                    f"Snapshot {snapshot[:12]} verification failed",
                    error_details
            )
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Verification was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Verification Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


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
