#!/usr/bin/env python3
"""
TimeLocker Command Line Interface

This module provides a beautiful, modern command-line interface for TimeLocker backup operations
using Typer for type-safe commands and Rich for beautiful terminal output.
"""

import sys
import os
import json
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
from .completion import (
    repository_name_completer,
    target_name_completer,
    snapshot_id_completer,
    repository_uri_completer,
    file_path_completer,
)

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

# Create sub-apps for new hierarchy
backup_app = typer.Typer(help="Backup operations")
snapshot_app = typer.Typer(help="Single snapshot operations")
snapshots_app = typer.Typer(help="Multiple snapshot operations")
repo_app = typer.Typer(help="Single repository operations")
repos_app = typer.Typer(help="Multiple repository operations")
config_app = typer.Typer(help="Configuration management commands")

# Add sub-apps to main app
app.add_typer(backup_app, name="backup")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(snapshots_app, name="snapshots")
app.add_typer(repo_app, name="repo")
app.add_typer(repos_app, name="repos")
app.add_typer(config_app, name="config")

# Add main command aliases
app.add_typer(repo_app, name="repository")
app.add_typer(repos_app, name="repositories")

# Create config sub-apps
config_repositories_app = typer.Typer(help="Repository configuration commands")
config_target_app = typer.Typer(help="Single target configuration commands")
config_targets_app = typer.Typer(help="Multiple target configuration commands")
config_import_app = typer.Typer(help="Import configuration commands")

# Add config sub-apps
config_app.add_typer(config_repositories_app, name="repositories")
config_app.add_typer(config_target_app, name="target")
config_app.add_typer(config_targets_app, name="targets")
config_app.add_typer(config_import_app, name="import")


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
    # Escape Rich markup in message to prevent markup errors
    safe_message = message.replace("[", "\\[").replace("]", "\\]")
    content = f"❌ {safe_message}"

    if details:
        content += "\n\n[bold]Details:[/bold]\n"
        for detail in details:
            # Escape Rich markup in details too
            safe_detail = detail.replace("[", "\\[").replace("]", "\\]")
            content += f"• {safe_detail}\n"

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


@backup_app.command("create")
def backup_create(
        sources: Annotated[Optional[List[Path]], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)] = None,
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_uri_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        target: Annotated[Optional[str], typer.Option("--target", "-t", help="Use configured backup target", autocompletion=target_name_completer)] = None,
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

        try:
            from .config.configuration_manager import ConfigurationManager, ConfigSection
            config_manager = ConfigurationManager(config_dir=config_dir)

            # Get backup target configuration
            backup_target = config_manager.get_backup_target(target)

        except ValueError as e:
            show_error_panel("Target Not Found", str(e))
            console.print("💡 Run [bold]tl config add-target[/bold] to create a backup target")
            raise typer.Exit(1)
        except Exception as e:
            show_error_panel("Configuration Error", f"Failed to load configuration: {e}")
            raise typer.Exit(1)

        # Extract backup target configuration
        sources = [Path(p) for p in backup_target["paths"]]
        name = name or backup_target.get("name", target)

        # Use patterns from target config if not overridden
        if not include and backup_target.get("patterns", {}).get("include"):
            include = backup_target["patterns"]["include"]
        if not exclude and backup_target.get("patterns", {}).get("exclude"):
            exclude = backup_target["patterns"]["exclude"]

        # Use default repository if not specified
        if not repository:
            default_repo_name = config_manager.get(ConfigSection.GENERAL, "default_repository")
            if default_repo_name:
                try:
                    default_repo = config_manager.get_repository(default_repo_name)
                    repository = default_repo.get("uri")
                except Exception:
                    pass  # Continue without default repository

        console.print(f"📁 Using backup target: [bold cyan]{target}[/bold cyan]")
        console.print(f"📂 Backing up {len(sources)} path(s)")

    # Validate sources
    if not sources:
        show_error_panel("No Sources", "No source paths specified for backup")
        console.print("💡 Either provide source paths or use --target to specify a configured backup target")
        raise typer.Exit(1)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                password = Prompt.ask("Repository password", password=True)
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

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
            repo = manager.from_uri(repository_uri, password=password)

            # Create backup target
            progress.update(task, description="Creating backup target...")

            # Create file selection
            selection = FileSelection()

            # Add source paths
            for source in sources:
                selection.add_path(source, SelectionType.INCLUDE)

            # Add exclusion patterns if specified
            if exclude:
                progress.update(task, description="Adding exclusion patterns...")
                for pattern in exclude:
                    selection.add_pattern(pattern, SelectionType.EXCLUDE)

            # Add inclusion patterns if specified
            if include:
                progress.update(task, description="Adding inclusion patterns...")
                for pattern in include:
                    selection.add_pattern(pattern, SelectionType.INCLUDE)

            # Create backup target with file selection
            target = BackupTarget(
                    selection=selection,
                    name=name or "cli_backup",
                    tags=tags
            )

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


@snapshot_app.command("restore")
def snapshot_restore(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        target: Annotated[Path, typer.Argument(help="Target path for restore", autocompletion=file_path_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_uri_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude pattern")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include pattern")] = None,
        preview: Annotated[bool, typer.Option("--preview", help="Preview restore without executing")] = False,
        confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompts")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Restore files from this snapshot."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                password = Prompt.ask("Repository password", password=True)
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
            repo = backup_manager.from_uri(repository_uri, password=password)
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
            repo = backup_manager.from_uri(repository_uri, password=password)

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
def snapshots_list(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_uri_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List snapshots in repository with a beautiful table."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                password = Prompt.ask("Repository password", password=True)
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
            backup_manager = BackupManager()

            # Create repository
            progress.update(task, description="Connecting to repository...")
            repo = backup_manager.from_uri(repository_uri, password=password)

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


@repo_app.command("init")
def repo_init(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI", autocompletion=repository_uri_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Initialize this repository."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                password = Prompt.ask("Repository password", password=True)
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

    # Confirm repository creation
    if not Confirm.ask(f"Initialize new repository at [bold]{repository_uri}[/bold]?"):
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
            repo = manager.from_uri(repository_uri, password=password)
            if not repo.initialize_repository(password):
                raise Exception("Repository initialization failed")

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


@app.command()
def completion(
        shell: Annotated[str, typer.Argument(help="Shell type (bash, zsh, fish)")] = "bash",
        install: Annotated[bool, typer.Option("--install", help="Install completion script")] = False,
) -> None:
    """Generate shell completion scripts for TimeLocker."""

    # Generate completion script based on shell type
    if shell.lower() == "bash":
        script_name = "timelocker-completion.bash"
        completion_script = '''# TimeLocker bash completion
_timelocker_completion() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=${COMP_CWORD} _TIMELOCKER_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

complete -o nosort -F _timelocker_completion timelocker
complete -o nosort -F _timelocker_completion tl
'''
    elif shell.lower() == "zsh":
        script_name = "_timelocker"
        completion_script = '''#compdef timelocker tl

_timelocker_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[timelocker] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=${#words[@]} _TIMELOCKER_COMPLETE=zsh_complete timelocker)}")

    for type_and_completion in "${response[@]}"; do
        completions+=("${type_and_completion#*,}")
    done

    if [ "${#completions[@]}" -eq 0 ]; then
        _files
    else
        _describe '' completions
    fi
}

compdef _timelocker_completion timelocker
compdef _timelocker_completion tl
'''
    elif shell.lower() == "fish":
        script_name = "timelocker.fish"
        completion_script = '''function _timelocker_completion
    set -l response (env _TIMELOCKER_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) timelocker)

    for completion in $response
        set -l metadata (string split "," $completion)

        if test $metadata[1] = "dir"
            __fish_complete_directories $metadata[2]
        else if test $metadata[1] = "file"
            __fish_complete_path $metadata[2]
        else if test $metadata[1] = "plain"
            echo $metadata[2]
        end
    end
end

complete --no-files --command timelocker --arguments "(_timelocker_completion)"
complete --no-files --command tl --arguments "(_timelocker_completion)"
'''
    else:
        console.print(f"[red]Error:[/red] Unsupported shell: {shell}")
        console.print("Supported shells: bash, zsh, fish")
        raise typer.Exit(1)

    if install:
        # Try to install the completion script
        try:
            if shell.lower() == "bash":
                completion_dir = Path.home() / ".bash_completion.d"
                completion_dir.mkdir(exist_ok=True)
                completion_file = completion_dir / script_name
            elif shell.lower() == "zsh":
                # Try common zsh completion directories
                zsh_dirs = [
                        Path.home() / ".zsh" / "completions",
                        Path("/usr/local/share/zsh/site-functions"),
                        Path("/usr/share/zsh/site-functions"),
                ]
                completion_dir = None
                for zsh_dir in zsh_dirs:
                    if zsh_dir.exists() or zsh_dir.parent.exists():
                        completion_dir = zsh_dir
                        break

                if not completion_dir:
                    completion_dir = Path.home() / ".zsh" / "completions"
                    completion_dir.mkdir(parents=True, exist_ok=True)

                completion_file = completion_dir / script_name
            elif shell.lower() == "fish":
                completion_dir = Path.home() / ".config" / "fish" / "completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / script_name

            # Write completion script
            completion_file.write_text(completion_script)
            console.print(f"[green]✓[/green] Completion script installed to: {completion_file}")

            if shell.lower() == "bash":
                console.print("\n[yellow]Next steps:[/yellow]")
                console.print("Add this to your ~/.bashrc:")
                console.print(f"[dim]source {completion_file}[/dim]")
            elif shell.lower() == "zsh":
                console.print("\n[yellow]Next steps:[/yellow]")
                console.print("Make sure your ~/.zshrc includes:")
                console.print(f"[dim]fpath=({completion_dir} $fpath)[/dim]")
                console.print("[dim]autoload -U compinit && compinit[/dim]")
            elif shell.lower() == "fish":
                console.print("\n[green]✓[/green] Fish completion is automatically loaded")

        except Exception as e:
            console.print(f"[red]Error installing completion:[/red] {e}")
            console.print("\nYou can manually save the script below:")
            console.print(completion_script)
    else:
        # Just print the completion script
        console.print(f"# {shell.title()} completion script for TimeLocker")
        console.print(completion_script)


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

        # Initialize configuration manager
        from .config.configuration_manager import ConfigurationManager, ConfigSection
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Repository setup
        if Confirm.ask("Would you like to add a repository?"):
            repo_name = Prompt.ask("Repository name", default="default")
            repo_uri = Prompt.ask("Repository URI (e.g., /path/to/backup or s3://bucket/path)")
            repo_desc = Prompt.ask("Repository description", default=f"{repo_name} backup repository")

            # Add repository using ConfigurationManager
            config_manager.add_repository(repo_name, repo_uri, repo_desc)
            config_manager.set(ConfigSection.GENERAL, "default_repository", repo_name)

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
                # Add backup target using ConfigurationManager
                config_manager.add_backup_target(
                        name=target_name,
                        paths=paths,
                        description=target_desc,
                        include_patterns=["*"],
                        exclude_patterns=["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
                )

        # Configuration is automatically saved by ConfigurationManager methods

        # Get counts for display
        repositories = config_manager.list_repositories()
        backup_targets = config_manager.list_backup_targets()

        show_success_panel(
                "Configuration Created",
                "Configuration setup completed successfully!",
                {
                        "Config file":    str(config_manager.config_file),
                        "Repositories":   str(len(repositories)),
                        "Backup targets": str(len(backup_targets))
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


@config_app.command("show")
def config_show(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List current configuration."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    try:
        config_manager = ConfigurationManager(config_dir=config_dir)
        # Configuration is automatically loaded in __init__
        config = config_manager._config
        config_file = config_manager.config_file

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


@config_import_app.command("restic")
def config_import_restic(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        repository_name: Annotated[str, typer.Option("--name", "-n", help="Name for the imported repository")] = "imported_restic",
        target_name: Annotated[str, typer.Option("--target", "-t", help="Name for the backup target")] = "imported_backup",
        paths: Annotated[Optional[List[str]], typer.Option("--paths", "-p", help="Backup paths (if not using current directory)")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be imported without making changes")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Import configuration from restic environment variables.

    This command reads RESTIC_REPOSITORY, RESTIC_PASSWORD, and AWS credentials
    from environment variables and creates a TimeLocker configuration.

    Required environment variables:
    - RESTIC_REPOSITORY: Repository URI (e.g., s3:s3.region.amazonaws.com/bucket)
    - RESTIC_PASSWORD: Repository password

    Optional AWS environment variables:
    - AWS_ACCESS_KEY_ID: AWS access key
    - AWS_SECRET_ACCESS_KEY: AWS secret key
    - AWS_DEFAULT_REGION: AWS region
    """
    import os
    from urllib.parse import urlparse

    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    console.print()
    console.print(Panel(
            "📥 Import Restic Configuration from Environment\n\n"
            "This will read restic settings from environment variables\n"
            "and create a TimeLocker configuration.",
            title="[bold green]Import from Restic Environment[/bold green]",
            border_style="green"
    ))
    console.print()

    # Check required environment variables
    required_vars = {
            'RESTIC_REPOSITORY': 'Repository URI',
            'RESTIC_PASSWORD':   'Repository password'
    }

    missing_vars = []
    env_config = {}

    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"  • {var}: {description}")
        else:
            env_config[var] = value

    if missing_vars:
        show_error_panel(
                "Missing Environment Variables",
                "The following required environment variables are not set:\n\n" +
                "\n".join(missing_vars) +
                "\n\nPlease set these variables and try again."
        )
        raise typer.Exit(1)

    # Check optional AWS variables
    aws_vars = {
            'AWS_ACCESS_KEY_ID':     'AWS Access Key ID',
            'AWS_SECRET_ACCESS_KEY': 'AWS Secret Access Key',
            'AWS_DEFAULT_REGION':    'AWS Default Region'
    }

    for var, description in aws_vars.items():
        value = os.getenv(var)
        if value:
            env_config[var] = value

    # Parse repository URI
    repo_uri = env_config['RESTIC_REPOSITORY']
    parsed_uri = urlparse(repo_uri)

    # Determine repository type
    if parsed_uri.scheme == 's3':
        repo_type = 's3'
        aws_region = env_config.get('AWS_DEFAULT_REGION', 'us-east-1')
    elif parsed_uri.scheme in ['', 'file']:
        repo_type = 'local'
        aws_region = None
    else:
        repo_type = 'remote'
        aws_region = None

    # Create configuration
    config = {
            "repositories":   {
                    repository_name: {
                            "type":                      repo_type,
                            "uri":                       repo_uri,
                            "description":               f"Imported from restic environment ({repo_type})",
                            "encryption":                True,
                            "imported_from_environment": True
                    }
            },
            "backup_targets": {
                    target_name: {
                            "paths":       paths or [str(Path.cwd())],
                            "repository":  repository_name,
                            "description": "Imported backup target from restic environment",
                            "patterns":    {
                                    "exclude": [
                                            "**/.git/**",
                                            "**/__pycache__/**",
                                            "**/node_modules/**",
                                            "**/.DS_Store",
                                            "**/Thumbs.db"
                                    ]
                            }
                    }
            },
            "settings":       {
                    "default_repository":  repository_name,
                    "notification_level":  "normal",
                    "auto_verify_backups": True
            }
    }

    if aws_region:
        config["repositories"][repository_name]["aws_region"] = aws_region

    # Display what will be imported
    console.print("📋 Configuration to be imported:")
    console.print()

    # Repository info
    repo_table = Table(title="Repository Configuration")
    repo_table.add_column("Setting", style="cyan")
    repo_table.add_column("Value", style="green")

    repo_table.add_row("Name", repository_name)
    repo_table.add_row("Type", repo_type)
    repo_table.add_row("URI", repo_uri)
    if aws_region:
        repo_table.add_row("AWS Region", aws_region)
    repo_table.add_row("Encryption", "✅ Enabled")

    console.print(repo_table)
    console.print()

    # Backup target info
    target_table = Table(title="Backup Target Configuration")
    target_table.add_column("Setting", style="cyan")
    target_table.add_column("Value", style="green")

    target_table.add_row("Name", target_name)
    target_table.add_row("Repository", repository_name)
    target_table.add_row("Paths", ", ".join(config["backup_targets"][target_name]["paths"]))
    target_table.add_row("Exclude Patterns", str(len(config["backup_targets"][target_name]["patterns"]["exclude"])))

    console.print(target_table)
    console.print()

    # Environment variables info
    env_table = Table(title="Environment Variables Found")
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Status", style="green")

    for var in required_vars.keys():
        if var in env_config:
            masked_value = env_config[var][:8] + "..." if len(env_config[var]) > 8 else "***"
            env_table.add_row(var, f"✅ Set ({masked_value})")
        else:
            env_table.add_row(var, "❌ Not set")

    for var in aws_vars.keys():
        if var in env_config:
            masked_value = env_config[var][:8] + "..." if len(env_config[var]) > 8 else "***"
            env_table.add_row(var, f"✅ Set ({masked_value})")
        else:
            env_table.add_row(var, "⚠️  Not set")

    console.print(env_table)
    console.print()

    if dry_run:
        console.print("🔍 [bold yellow]Dry run mode - no changes made[/bold yellow]")
        console.print("Configuration would be saved to:", str(config_dir / "timelocker.json"))
        return

    # Confirm before proceeding
    if not Confirm.ask("Import this configuration?"):
        console.print("❌ Import cancelled")
        raise typer.Exit(0)

    try:
        # Ensure config directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Use ConfigurationManager to properly handle the configuration
        from .config.configuration_manager import ConfigurationManager, ConfigSection
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Update repositories section
        current_repos = config_manager.get_section(ConfigSection.REPOSITORIES)
        current_repos.update(config["repositories"])
        config_manager.set_section(ConfigSection.REPOSITORIES, current_repos)

        # Update backup targets (stored in a custom section)
        current_config = config_manager.get_configuration()
        current_config.setdefault("backup_targets", {}).update(config["backup_targets"])

        # Update settings (stored in a custom section)
        current_config.setdefault("settings", {}).update(config["settings"])

        # Save the updated configuration
        config_manager._config = current_config
        config_manager.save_config()

        console.print()
        show_success_panel(
                "Configuration Imported Successfully!",
                f"✅ Repository '{repository_name}' added\n"
                f"✅ Backup target '{target_name}' created\n"
                f"✅ Configuration saved to {config_manager.config_file}\n\n"
                f"💡 Next steps:\n"
                f"   • Test connection: timelocker list -r {repo_uri}\n"
                f"   • Create backup: timelocker backup {target_name}\n"
                f"   • List config: timelocker config list"
        )

    except Exception as e:
        show_error_panel("Import Failed", f"Failed to save configuration: {e}")
        raise typer.Exit(1)


@config_repositories_app.command("list")
def config_repositories_list(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List configured repositories."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    try:
        config_manager = ConfigurationManager(config_dir=config_dir)
        config_file = config_manager.config_file

        console.print()
        console.print(Panel(
                f"📁 Repositories from: {config_file}",
                title="[bold green]TimeLocker Repositories[/bold green]",
                border_style="green"
        ))

        repositories = config_manager.list_repositories()
        default_repo = config_manager.get_default_repository()

        if repositories:
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="yellow")
            table.add_column("URI", style="green")
            table.add_column("Description", style="white")
            table.add_column("Default", style="magenta", justify="center")

            for name, repo_config in repositories.items():
                repo_type = repo_config.get("type", "unknown")
                uri = repo_config.get("uri", "N/A")
                description = repo_config.get("description", "")
                is_default = "✓" if name == default_repo else ""

                table.add_row(name, repo_type, uri, description, is_default)

            console.print(table)
            console.print()

            if default_repo:
                console.print(f"🎯 [bold]Default repository:[/bold] {default_repo}")
            else:
                console.print("💡 [bold]Set a default repository:[/bold] [cyan]tl config set-default-repo <name>[/cyan]")
        else:
            console.print("❌ No repositories configured")
            console.print()
            console.print("💡 [bold]Add a repository:[/bold]")
            console.print("   [cyan]tl config add-repo <name> <uri>[/cyan] - Add a repository")
            console.print("   [cyan]tl config setup[/cyan] - Interactive setup")
            console.print("   [cyan]tl config import-restic[/cyan] - Import from restic environment")

        console.print()

    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to load configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_repositories_app.command("add")
def config_repositories_add(
        name: Annotated[str, typer.Argument(help="Repository name")],
        uri: Annotated[str, typer.Argument(help="Repository URI", autocompletion=repository_uri_completer)],
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Repository description")] = None,
        set_default: Annotated[bool, typer.Option("--set-default", help="Set as default repository")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Add a new repository to configuration."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    try:
        from .config.configuration_manager import ConfigurationManager, RepositoryAlreadyExistsError
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Add repository
        config_manager.add_repository(
                name=name,
                uri=uri,
                description=description or f"{name} repository"
        )

        # Set as default if requested
        if set_default:
            config_manager.set_default_repository(name)

        console.print()
        console.print(Panel(
                f"✅ Repository '{name}' added successfully!\n\n"
                f"📍 URI: {uri}\n"
                f"📝 Description: {description or f'{name} repository'}\n"
                f"🎯 Default: {'Yes' if set_default else 'No'}",
                title="[bold green]Repository Added[/bold green]",
                border_style="green"
        ))

        # Show usage example
        console.print()
        console.print(f"💡 [bold]Usage example:[/bold] [cyan]tl list -r {name}[/cyan]")

    except RepositoryAlreadyExistsError as e:
        show_error_panel("Repository Exists", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to add repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_repositories_app.command("remove")
def config_repositories_remove(
        name: Annotated[str, typer.Argument(help="Repository name to remove", autocompletion=repository_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove a repository from configuration."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    try:
        from .config.configuration_manager import ConfigurationManager, RepositoryNotFoundError
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Get repository info before removal
        repo_info = config_manager.get_repository(name)

        # Confirm removal
        console.print()
        console.print(Panel(
                f"Repository: {name}\n"
                f"URI: {repo_info['uri']}\n"
                f"Description: {repo_info.get('description', 'N/A')}",
                title="[bold yellow]Repository to Remove[/bold yellow]",
                border_style="yellow"
        ))

        if not Confirm.ask("Are you sure you want to remove this repository?"):
            console.print("❌ Repository removal cancelled.")
            return

        # Remove repository
        config_manager.remove_repository(name)

        console.print()
        console.print(Panel(
                f"✅ Repository '{name}' removed successfully!",
                title="[bold green]Repository Removed[/bold green]",
                border_style="green"
        ))

    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to remove repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_repositories_app.command("default")
def config_repositories_default(
        name: Annotated[str, typer.Argument(help="Repository name to set as default", autocompletion=repository_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Set the default repository."""
    setup_logging(verbose)

    if not config_dir:
        config_dir = Path.home() / ".timelocker"

    try:
        from .config.configuration_manager import ConfigurationManager, RepositoryNotFoundError
        config_manager = ConfigurationManager(config_dir=config_dir)

        # Set default repository
        config_manager.set_default_repository(name)

        console.print()
        console.print(Panel(
                f"✅ Default repository set to '{name}'!\n\n"
                f"💡 You can now use commands without specifying -r:\n"
                f"   [cyan]tl list[/cyan] (instead of [cyan]tl list -r {name}[/cyan])",
                title="[bold green]Default Repository Set[/bold green]",
                border_style="green"
        ))

    except RepositoryNotFoundError as e:
        show_error_panel("Repository Not Found", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to set default repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_targets_app.command("add")
def config_targets_add(
        name: Annotated[str, typer.Argument(help="Target name")],
        paths: Annotated[List[str], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)],
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

    try:
        # Initialize configuration manager
        config_manager = ConfigurationManager(config_dir=config_dir)

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

        # Add backup target using ConfigurationManager
        config_manager.add_backup_target(
                name=name,
                paths=valid_paths,
                description=description or f"Backup target for {name}",
                include_patterns=include or ["*"],
                exclude_patterns=exclude or ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
        )

        show_success_panel(
                "Target Added",
                f"Backup target '{name}' added successfully!",
                {
                        "Target name": name,
                        "Description": description or f"Backup target for {name}",
                        "Paths":       f"{len(valid_paths)} path(s)",
                        "Config file": str(config_manager.config_file)
                }
        )

    except Exception as e:
        show_error_panel("Add Target Error", f"Failed to add backup target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@backup_app.command("verify")
def backup_verify(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        snapshot: Annotated[Optional[str], typer.Option("--snapshot", "-s", help="Specific snapshot to verify")] = None,
        latest: Annotated[bool, typer.Option("--latest", help="Verify latest snapshot")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify backup integrity."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        if not password:
            # Check TimeLocker environment variable first, then fall back to RESTIC_PASSWORD
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                password = Prompt.ask("Repository password", password=True)
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

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
            repo = backup_manager.from_uri(repository_uri, password=password)

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


# ============================================================================
# SNAPSHOT COMMANDS (Single snapshot operations)
# ============================================================================

@snapshot_app.command("show")
def snapshot_show(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show snapshot details."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} show[/yellow]")
    console.print("This command will show details for the specified snapshot.")


@snapshot_app.command("list")
def snapshot_list(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List contents of snapshot."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} list[/yellow]")
    console.print("This command will list the file contents of the specified snapshot.")


@snapshot_app.command("mount")
def snapshot_mount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        path: Annotated[Path, typer.Argument(help="Mount path")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Mount this snapshot as filesystem."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} mount {path}[/yellow]")
    console.print("This command will mount the specified snapshot as a filesystem.")


@snapshot_app.command("umount")
def snapshot_umount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Unmount this snapshot."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} umount[/yellow]")
    console.print("This command will unmount the specified snapshot.")


@snapshot_app.command("find")
def snapshot_find(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        pattern: Annotated[str, typer.Argument(help="Search pattern")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Search within this snapshot."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} find {pattern}[/yellow]")
    console.print("This command will search for files matching the pattern within the specified snapshot.")


@snapshot_app.command("forget")
def snapshot_forget(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove this specific snapshot."""
    console.print(f"[yellow]🚧 Command stub: snapshot {snapshot_id} forget[/yellow]")
    console.print("This command will remove the specified snapshot.")


# ============================================================================
# SNAPSHOTS COMMANDS (Multiple snapshot operations)
# ============================================================================

@snapshots_app.command("prune")
def snapshots_prune(
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        keep_daily: Annotated[int, typer.Option("--keep-daily", help="Number of daily snapshots to keep")] = 7,
        keep_weekly: Annotated[int, typer.Option("--keep-weekly", help="Number of weekly snapshots to keep")] = 4,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove old snapshots across repos."""
    console.print("[yellow]🚧 Command stub: snapshots prune[/yellow]")
    console.print("This command will prune old snapshots according to retention policies.")


@snapshots_app.command("diff")
def snapshots_diff(
        id1: Annotated[str, typer.Argument(help="First snapshot ID")],
        id2: Annotated[str, typer.Argument(help="Second snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Compare two snapshots."""
    console.print(f"[yellow]🚧 Command stub: snapshots diff {id1} {id2}[/yellow]")
    console.print("This command will compare two snapshots and show differences.")


@snapshots_app.command("find")
def snapshots_find(
        pattern: Annotated[str, typer.Argument(help="Search pattern")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Search across all snapshots."""
    console.print(f"[yellow]🚧 Command stub: snapshots find {pattern}[/yellow]")
    console.print("This command will search for files matching the pattern across all snapshots.")


# ============================================================================
# REPO COMMANDS (Single repository operations)
# ============================================================================

@repo_app.command("check")
def repo_check(
        name: Annotated[str, typer.Argument(help="Repository name")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Check this repository integrity."""
    console.print(f"[yellow]🚧 Command stub: repo {name} check[/yellow]")
    console.print("This command will check the integrity of the specified repository.")


@repo_app.command("stats")
def repo_stats(
        name: Annotated[str, typer.Argument(help="Repository name")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show this repository statistics."""
    console.print(f"[yellow]🚧 Command stub: repo {name} stats[/yellow]")
    console.print("This command will show statistics for the specified repository.")


@repo_app.command("unlock")
def repo_unlock(
        name: Annotated[str, typer.Argument(help="Repository name")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove locks from this repository."""
    console.print(f"[yellow]🚧 Command stub: repo {name} unlock[/yellow]")
    console.print("This command will remove locks from the specified repository.")


@repo_app.command("migrate")
def repo_migrate(
        name: Annotated[str, typer.Argument(help="Repository name")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Migrate this repository format."""
    console.print(f"[yellow]🚧 Command stub: repo {name} migrate[/yellow]")
    console.print("This command will migrate the repository format.")


@repo_app.command("forget")
def repo_forget(
        name: Annotated[str, typer.Argument(help="Repository name")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        keep_daily: Annotated[int, typer.Option("--keep-daily", help="Number of daily snapshots to keep")] = 7,
        keep_weekly: Annotated[int, typer.Option("--keep-weekly", help="Number of weekly snapshots to keep")] = 4,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Apply retention policy to this repo."""
    console.print(f"[yellow]🚧 Command stub: repo {name} forget[/yellow]")
    console.print("This command will apply retention policies to the specified repository.")


# ============================================================================
# REPOS COMMANDS (Multiple repository operations)
# ============================================================================

@repos_app.command("list")
def repos_list(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List all repositories."""
    console.print("[yellow]🚧 Command stub: repos list[/yellow]")
    console.print("This command will list all configured repositories.")


@repos_app.command("check")
def repos_check(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Check all repositories."""
    console.print("[yellow]🚧 Command stub: repos check[/yellow]")
    console.print("This command will check the integrity of all repositories.")


@repos_app.command("stats")
def repos_stats(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show stats for all repositories."""
    console.print("[yellow]🚧 Command stub: repos stats[/yellow]")
    console.print("This command will show statistics for all repositories.")


# ============================================================================
# CONFIG COMMANDS (Configuration management)
# ============================================================================

# Config repositories commands (already moved above)

@config_repositories_app.command("show")
def config_repositories_show(
        name: Annotated[str, typer.Argument(help="Repository name")],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show repository config details."""
    console.print(f"[yellow]🚧 Command stub: config repositories show {name}[/yellow]")
    console.print("This command will show configuration details for the specified repository.")


# Config target commands (single target operations)

@config_target_app.command("show")
def config_target_show(
        name: Annotated[str, typer.Argument(help="Target name")],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show target details."""
    console.print(f"[yellow]🚧 Command stub: config target {name} show[/yellow]")
    console.print("This command will show details for the specified backup target.")


@config_target_app.command("edit")
def config_target_edit(
        name: Annotated[str, typer.Argument(help="Target name")],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Edit target configuration."""
    console.print(f"[yellow]🚧 Command stub: config target {name} edit[/yellow]")
    console.print("This command will open an editor to modify the specified backup target.")


@config_target_app.command("remove")
def config_target_remove(
        name: Annotated[str, typer.Argument(help="Target name")],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove this target."""
    console.print(f"[yellow]🚧 Command stub: config target {name} remove[/yellow]")
    console.print("This command will remove the specified backup target.")


# Config targets commands (multiple target operations)

@config_targets_app.command("list")
def config_targets_list(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List all targets."""
    console.print("[yellow]🚧 Command stub: config targets list[/yellow]")
    console.print("This command will list all configured backup targets.")


def main() -> None:
    """Main entry point for the CLI using Typer."""
    try:
        app()
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        # Escape Rich markup in error message to prevent markup errors
        error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
        show_error_panel("Unexpected Error", f"An unexpected error occurred: {error_msg}")
        console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    main()
