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
import logging.handlers
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
from rich.logging import RichHandler

from . import __version__
from .backup_manager import BackupManager
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType
from .restore_manager import RestoreManager
from .snapshot_manager import SnapshotManager
from .config import ConfigurationModule
from .cli_services import get_cli_service_manager, CLIBackupRequest
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
credentials_app = typer.Typer(help="Credential management commands")

# Add sub-apps to main app
app.add_typer(backup_app, name="backup")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(snapshots_app, name="snapshots")
app.add_typer(repo_app, name="repo")
app.add_typer(repos_app, name="repos")
app.add_typer(config_app, name="config")
app.add_typer(credentials_app, name="credentials")

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


class UserFacingLogFilter(logging.Filter):
    """Filter to identify user-facing log messages that should be displayed in CLI."""

    def filter(self, record):
        # Only show messages that are relevant to users
        # This includes configuration errors, validation failures, and user action failures

        # Always show CRITICAL errors
        if record.levelno >= logging.CRITICAL:
            return True

        # For ERROR and WARNING levels, be selective
        if record.levelno >= logging.WARNING:
            # Check if this is a user-relevant message based on logger name and message content
            logger_name = record.name.lower()
            message = record.getMessage().lower()

            # User-relevant loggers (TimeLocker specific, not third-party libraries)
            user_relevant_loggers = [
                    'timelocker',
                    'src.timelocker',
                    '__main__'
            ]

            # Check if it's from a user-relevant logger
            is_user_logger = any(logger_name.startswith(prefix.lower()) for prefix in user_relevant_loggers)

            # User-relevant message patterns
            user_relevant_patterns = [
                    'configuration',
                    'config',
                    'repository',
                    'backup',
                    'restore',
                    'snapshot',
                    'target',
                    'validation',
                    'permission denied',
                    'not found',
                    'failed to',
                    'unable to',
                    'invalid',
                    'missing',
                    'authentication',
                    'password'
            ]

            # Check if message contains user-relevant keywords
            has_user_keywords = any(pattern in message for pattern in user_relevant_patterns)

            # Filter out misleading warnings that aren't helpful during normal operations
            misleading_warnings = [
                    'no repositories configured',  # Don't show during repository add operations
            ]

            # Skip misleading warnings
            if any(warning in message for warning in misleading_warnings):
                return False

            # Show message if it's from a user-relevant logger AND contains user-relevant keywords
            return is_user_logger and has_user_keywords

        return False


class CLILogHandler(RichHandler):
    """Custom log handler that formats user-facing messages as Rich panels."""

    def __init__(self, console: Console):
        super().__init__(console=console, show_time=False, show_path=False)
        self.console = console

    def emit(self, record):
        try:
            # Format the message
            message = self.format(record)

            # Determine panel style based on log level
            if record.levelno >= logging.CRITICAL:
                title = "Critical Error"
                style = "red"
                icon = "💥"
            elif record.levelno >= logging.ERROR:
                title = "Error"
                style = "red"
                icon = "❌"
            elif record.levelno >= logging.WARNING:
                title = "Warning"
                style = "yellow"
                icon = "⚠️"
            else:
                # For INFO and below, use simple console output
                self.console.print(f"ℹ️  {message}", style="blue")
                return

            # Create and display panel for errors/warnings
            panel = Panel(
                    f"{icon} {message}",
                    title=f"[bold {style}]{title}[/bold {style}]",
                    border_style=style,
                    padding=(0, 1)
            )
            self.console.print(panel)

        except Exception:
            self.handleError(record)


def setup_logging(verbose: bool = False, config_dir: Optional[Path] = None) -> None:
    """Set up logging configuration with file output and user-facing CLI messages."""
    from .config.configuration_path_resolver import ConfigurationPathResolver

    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO

    # Get appropriate XDG directory for log files (cache directory)
    # Logs are temporary/cache data, not configuration or persistent data
    log_dir = ConfigurationPathResolver.get_cache_directory() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set up file logging for all messages
    log_file = log_dir / "timelocker.log"
    file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Set up CLI logging for user-facing messages only
    cli_handler = CLILogHandler(console)
    cli_handler.setLevel(logging.WARNING)  # Only show warnings and errors to users
    cli_handler.addFilter(UserFacingLogFilter())

    # Configure root logger
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(cli_handler)

    # Log the logging setup
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured - Level: {logging.getLevelName(level)}, Log file: {log_file}")

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


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
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be backed up without actually performing backup")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Create a backup with beautiful progress tracking."""
    setup_logging(verbose, config_dir)

    # Handle target-based backup
    if target:
        try:
            from .config import ConfigurationModule
            config_module = ConfigurationModule(config_dir=config_dir)

            # Get backup target configuration
            backup_target = config_module.get_backup_target(target)

        except ValueError as e:
            show_error_panel("Target Not Found", str(e))
            console.print("💡 Run [bold]tl config add-target[/bold] to create a backup target")
            raise typer.Exit(1)
        except Exception as e:
            show_error_panel("Configuration Error", f"Failed to load configuration: {e}")
            raise typer.Exit(1)

        # Extract backup target configuration
        with open("/tmp/cli_debug.log", "a") as f:
            f.write(f"DEBUG: backup_target type: {type(backup_target)}\n")
            f.write(f"DEBUG: backup_target content: {backup_target}\n")
        sources = [Path(p) for p in backup_target.paths]
        name = name or backup_target.name or target

        # Use patterns from target config if not overridden
        if not include and backup_target.include_patterns:
            include = backup_target.include_patterns
        if not exclude and backup_target.exclude_patterns:
            exclude = backup_target.exclude_patterns

        # Use default repository if not specified
        if not repository:
            default_repo_name = config_module.get_default_repository()
            if default_repo_name:
                try:
                    default_repo = config_module.get_repository(default_repo_name)
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
        print(f"DEBUG: Starting backup execution with repository_uri: {repository_uri}", file=sys.stderr)
        with open("/tmp/cli_debug.log", "a") as f:
            f.write(f"DEBUG: Starting backup execution with repository_uri: {repository_uri}\n")
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console,
        ) as progress:

            # Initialize service manager
            task = progress.add_task("Initializing backup...", total=None)
            print(f"DEBUG: About to call get_cli_service_manager()", file=sys.stderr)
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: About to call get_cli_service_manager()\n")
            service_manager = get_cli_service_manager()
            print(f"DEBUG: Service manager created: {type(service_manager)}", file=sys.stderr)
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: Service manager created: {type(service_manager)}\n")

            # Create backup request
            progress.update(task, description="Preparing backup request...")
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: Creating CLIBackupRequest with sources={sources}, repository_uri={repository_uri}, target_name={target}\n")
            backup_request = CLIBackupRequest(
                    sources=sources,
                    repository_uri=repository_uri,
                    password=password,
                    target_name=target,
                    backup_name=name,
                    tags=tags or [],
                    include_patterns=include or [],
                    exclude_patterns=exclude or [],
                    dry_run=dry_run
            )
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: CLIBackupRequest created successfully\n")

            # Execute backup using modern orchestrator
            progress.update(task, description="Executing backup...")
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: About to call execute_backup_from_cli with repository_uri: {backup_request.repository_uri}\n")
            result = service_manager.execute_backup_from_cli(backup_request)
            with open("/tmp/cli_debug.log", "a") as f:
                f.write(f"DEBUG: Backup result: {result.status}\n")

            progress.remove_task(task)

        # Display results using new BackupResult data model
        if result.is_successful:
            details = {
                    "Snapshot ID":     result.snapshot_id or "Unknown",
                    "Files processed": f"{result.files_processed:,}",
                    "Data processed":  f"{result.bytes_processed:,} bytes" if result.bytes_processed else "Unknown",
                    "Duration":        f"{result.duration:.1f}s" if result.duration else "Unknown"
            }

            success_msg = "Backup operation completed successfully!"
            if result.has_warnings:
                success_msg += f" ({len(result.warnings)} warnings)"

            show_success_panel("Backup Completed", success_msg, details)

            # Show warnings if any
            if result.has_warnings:
                for warning in result.warnings:
                    console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
        else:
            error_msg = "Backup operation failed"
            if result.errors:
                error_msg += f": {'; '.join(result.errors)}"

            show_error_panel("Backup Failed", error_msg)
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
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
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

    # Confirm repository creation unless --yes flag is used
    if not yes and not Confirm.ask(f"Initialize new repository at [bold]{repository_uri}[/bold]?"):
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
    setup_logging(verbose, config_dir)

    console.print()
    console.print(Panel(
            "🚀 Welcome to TimeLocker Configuration Setup!\n\n"
            "This wizard will help you set up your backup configuration.",
            title="[bold blue]Configuration Setup[/bold blue]",
            border_style="blue"
    ))
    console.print()

    try:
        # Initialize configuration module (will use appropriate path resolution)
        from .config import ConfigurationModule
        config_module = ConfigurationModule(config_dir=config_dir)

        # Show configuration information
        config_info = config_module.get_config_info()
        console.print(f"📁 Configuration directory: {config_info['current_config_dir']}")
        if config_info['migration_marker_exists']:
            console.print("✅ Configuration migrated from legacy location")
        console.print()

        # Repository setup
        if Confirm.ask("Would you like to add a repository?"):
            repo_name = Prompt.ask("Repository name", default="default")
            repo_uri = Prompt.ask("Repository URI (e.g., /path/to/backup or s3://bucket/path)")
            repo_desc = Prompt.ask("Repository description", default=f"{repo_name} backup repository")

            # Add repository using ConfigurationModule
            config_manager.add_repository(repo_name, repo_uri, repo_desc)
            config_manager.set_default_repository(repo_name)

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
                # Add backup target using ConfigurationModule
                target_config = {
                        "name":             target_name,
                        "paths":            paths,
                        "description":      target_desc,
                        "include_patterns": ["*"],
                        "exclude_patterns": ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
                }
                config_manager.add_backup_target(target_config)

        # Configuration is automatically saved by ConfigurationModule methods

        # Get counts for display
        repositories = config_manager.get_repositories()
        backup_targets = config_manager.get_backup_targets()

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
    setup_logging(verbose, config_dir)

    try:
        from .config import ConfigurationModule
        config_module = ConfigurationModule(config_dir=config_dir)
        # Configuration is automatically loaded in __init__
        config = config_module.get_config()
        config_file = config_module.config_file

        console.print()
        console.print(Panel(
                f"📁 Configuration from: {config_file}",
                title="[bold blue]TimeLocker Configuration[/bold blue]",
                border_style="blue"
        ))

        # Repositories table
        if config.repositories:
            table = Table(title="🗄️  Repositories", border_style="green")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("URI", style="white")
            table.add_column("Description", style="dim")

            for name, repo in config.repositories.items():
                table.add_row(
                        name,
                        getattr(repo, "type", "unknown"),
                        getattr(repo, "uri", ""),
                        getattr(repo, "description", "")
                )
            console.print(table)
            console.print()

        # Backup targets table
        if config.backup_targets:
            table = Table(title="🎯 Backup Targets", border_style="blue")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Paths", style="green")
            table.add_column("Patterns", style="dim")

            for name, target in config.backup_targets.items():
                paths_str = "\n".join(getattr(target, "paths", []))
                include_patterns = ", ".join(getattr(target, "include_patterns", []))
                exclude_patterns = ", ".join(getattr(target, "exclude_patterns", []))
                patterns_str = f"Include: {include_patterns}\nExclude: {exclude_patterns}"

                table.add_row(
                        name,
                        getattr(target, "description", ""),
                        paths_str,
                        patterns_str
                )
            console.print(table)
            console.print()

        # Settings (General configuration)
        settings_text = ""
        if config.general.default_repository:
            settings_text += f"[bold]default_repository:[/bold] {config.general.default_repository}\n"
        if config.general.max_concurrent_operations:
            settings_text += f"[bold]max_concurrent_operations:[/bold] {config.general.max_concurrent_operations}\n"

        if settings_text:
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


@config_app.command("info")
def config_info(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show configuration directory information and migration status."""
    setup_logging(verbose, config_dir)

    try:
        # Initialize configuration manager (will use appropriate path resolution)
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)
        config_info = config_manager.get_config_info()

        console.print()
        console.print(Panel(
                "📁 Configuration Directory Information",
                title="[bold blue]TimeLocker Configuration Info[/bold blue]",
                border_style="blue"
        ))

        # Configuration paths table
        table = Table(title="📂 Configuration Paths", border_style="green")
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white")
        table.add_column("Status", style="yellow")

        # Current configuration
        table.add_row(
                "Current Config Directory",
                config_info['current_config_dir'],
                "✅ Active" if config_info['config_file_exists'] else "❌ Missing"
        )

        table.add_row(
                "Current Config File",
                config_info['current_config_file'],
                "✅ Exists" if config_info['config_file_exists'] else "❌ Missing"
        )

        # System context
        table.add_row(
                "System Context",
                "Root/System" if config_info['is_system_context'] else "User",
                "🔒 System" if config_info['is_system_context'] else "👤 User"
        )

        # XDG information
        table.add_row(
                "XDG Config Home",
                config_info['xdg_config_home'],
                "📁 Standard"
        )

        # Legacy configuration
        table.add_row(
                "Legacy Config Directory",
                config_info['legacy_config_dir'],
                "✅ Found" if config_info['legacy_config_exists'] else "❌ Not Found"
        )

        # Migration status
        migration_status = "✅ Migrated" if config_info['migration_marker_exists'] else (
                "⚠️ Available" if config_info['legacy_config_exists'] else "➖ N/A"
        )
        table.add_row(
                "Migration Status",
                "From legacy location" if config_info['migration_marker_exists'] else "No migration needed",
                migration_status
        )

        # Backup information
        table.add_row(
                "Backup Directory",
                config_info['backup_dir'],
                f"📦 {config_info['backup_count']} backups"
        )

        console.print(table)
        console.print()

        # Migration information if applicable
        if config_info['migration_marker_exists']:
            console.print(Panel(
                    "✅ Configuration was successfully migrated from legacy location\n"
                    f"   Legacy: {config_info['legacy_config_dir']}\n"
                    f"   Current: {config_info['current_config_dir']}\n\n"
                    "💡 Your configuration is now following XDG Base Directory Specification",
                    title="[bold green]Migration Complete[/bold green]",
                    border_style="green"
            ))
        elif config_info['legacy_config_exists'] and not config_info['config_file_exists']:
            console.print(Panel(
                    "⚠️ Legacy configuration detected but not migrated\n"
                    f"   Legacy: {config_info['legacy_config_dir']}\n"
                    f"   Target: {config_info['current_config_dir']}\n\n"
                    "💡 Run 'tl config setup' to migrate your configuration",
                    title="[bold yellow]Migration Available[/bold yellow]",
                    border_style="yellow"
            ))

        console.print()

    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to get configuration info: {e}")
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
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
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

    # Confirm before proceeding unless --yes flag is used
    if not yes and not Confirm.ask("Import this configuration?"):
        console.print("❌ Import cancelled")
        raise typer.Exit(0)

    try:
        # Configuration import is no longer supported with the new configuration system
        raise NotImplementedError(
                "Configuration import is not supported with the new configuration system. "
                "Please manually recreate your repositories and backup targets using the CLI commands."
        )

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

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)
        config_file = config_manager.config_file

        console.print()
        console.print(Panel(
                f"📁 Repositories from: {config_file}",
                title="[bold green]TimeLocker Repositories[/bold green]",
                border_style="green"
        ))

        repositories = config_manager.get_repositories()
        default_repo = config_manager.get_default_repository()

        if repositories:
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="yellow")
            table.add_column("URI", style="green")
            table.add_column("Description", style="white")
            table.add_column("Default", style="magenta", justify="center")

            for repo_config in repositories:
                name = repo_config.get("name", "unknown")
                repo_type = repo_config.get("type", "unknown")
                uri = repo_config.get("uri", repo_config.get("location", "N/A"))
                description = repo_config.get("description", "")
                is_default = "✓" if name == default_repo else ""

                table.add_row(name, repo_type, uri, description, is_default)

            console.print(table)
            console.print()

            if default_repo:
                console.print(f"🎯 [bold]Default repository:[/bold] {default_repo}")
            else:
                console.print("💡 [bold]Set a default repository:[/bold] [cyan]tl config repositories default <name>[/cyan]")
        else:
            console.print("❌ No repositories configured")
            console.print()
            console.print("💡 [bold]Add a repository:[/bold]")
            console.print("   [cyan]tl config repositories add <name> <uri>[/cyan] - Add a repository")
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
        name: Annotated[Optional[str], typer.Argument(help="Repository name")] = None,
        uri: Annotated[Optional[str], typer.Argument(help="Repository URI", autocompletion=repository_uri_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Repository description")] = None,
        set_default: Annotated[bool, typer.Option("--set-default", help="Set as default repository")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Add a new repository to configuration."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not name:
        name = Prompt.ask("Repository name")

    if not uri:
        uri = Prompt.ask("Repository URI")

    try:
        from .config.configuration_module import ConfigurationModule
        from .interfaces.exceptions import RepositoryAlreadyExistsError
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Add repository
        repository_config = {
                'name':        name,
                'location':    uri,
                'description': description or f"{name} repository"
        }
        config_manager.add_repository(repository_config)

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
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Remove a repository from configuration."""
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        from .interfaces.exceptions import RepositoryNotFoundError
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get repository info before removal
        repo_info = config_manager.get_repository(name)

        # Confirm removal unless --yes flag is used
        if not yes:
            console.print()
            console.print(Panel(
                    f"Repository: {name}\n"
                    f"Location: {getattr(repo_info, 'location', None) or getattr(repo_info, 'uri', None) or 'N/A'}\n"
                    f"Description: {getattr(repo_info, 'description', None) or 'N/A'}",
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

    try:
        from .config.configuration_module import ConfigurationModule
        from .interfaces.exceptions import RepositoryNotFoundError
        config_manager = ConfigurationModule(config_dir=config_dir)

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
        name: Annotated[Optional[str], typer.Argument(help="Target name")] = None,
        paths: Annotated[Optional[List[str]], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", "-i", help="Include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", "-e", help="Exclude patterns")] = None,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Add a new backup target to configuration."""
    setup_logging(verbose)

    # Prompt for missing required parameters
    if not name:
        name = Prompt.ask("Target name")

    if not paths:
        paths_input = Prompt.ask("Source paths to backup (comma-separated)")
        paths = [path.strip() for path in paths_input.split(",") if path.strip()]

    if not paths:
        show_error_panel("No Paths Provided", "At least one source path is required for backup target")
        raise typer.Exit(1)

    try:
        # Initialize configuration manager
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

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

        # Add backup target using ConfigurationModule
        target_config = {
                "name":             name,
                "paths":            valid_paths,
                "description":      description or f"Backup target for {name}",
                "include_patterns": include or ["*"],
                "exclude_patterns": exclude or ["*.tmp", "*.log", "Thumbs.db", ".DS_Store"]
        }
        config_manager.add_backup_target(target_config)

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
            service_manager = get_cli_service_manager()

            # Handle latest snapshot resolution if needed
            if latest:
                progress.update(task, description="Finding latest snapshot...")
                # Use legacy manager for snapshot listing until we have snapshot service
                backup_manager = BackupManager()
                repo = backup_manager.from_uri(repository_uri, password=password)
                snapshot_manager = SnapshotManager(repo)
                snapshots = snapshot_manager.list_snapshots()
                if not snapshots:
                    show_error_panel("No Snapshots", "No snapshots found in repository")
                    raise typer.Exit(1)
                snapshot = snapshots[0].id  # Assuming first is latest

            if not snapshot:
                snapshot = Prompt.ask("Snapshot ID to verify")

            # Perform verification using modern service
            progress.update(task, description=f"Verifying snapshot {snapshot[:12]}...")
            verification_passed = service_manager.verify_backup_integrity(
                    repository_input=repository_uri,
                    snapshot_id=snapshot,
                    password=password
            )

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
                    f"Snapshot {snapshot[:12]} verification failed"
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
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Get snapshot details using service
        snapshot_info = service_manager.snapshot_service.get_snapshot_details(repo, snapshot_id)

        # Create detailed display
        table = Table(title=f"Snapshot Details: {snapshot_info.id[:12]}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Format timestamp
        from datetime import datetime
        timestamp_str = datetime.fromtimestamp(snapshot_info.timestamp).strftime("%Y-%m-%d %H:%M:%S")

        # Format size
        size_str = f"{snapshot_info.size:,} bytes" if snapshot_info.size else "Unknown"

        table.add_row("Snapshot ID", snapshot_info.id)
        table.add_row("Short ID", snapshot_info.id[:12])
        table.add_row("Timestamp", timestamp_str)
        table.add_row("Hostname", snapshot_info.hostname)
        table.add_row("Username", snapshot_info.username)
        table.add_row("Repository", snapshot_info.repository_name)
        table.add_row("Size", size_str)
        table.add_row("File Count", str(snapshot_info.file_count))
        table.add_row("Directory Count", str(snapshot_info.directory_count))
        table.add_row("Tags", ", ".join(snapshot_info.tags) if snapshot_info.tags else "None")

        console.print(table)

        # Show paths
        if snapshot_info.paths:
            paths_table = Table(title="Backup Paths")
            paths_table.add_column("Path", style="green")
            for path in snapshot_info.paths:
                paths_table.add_row(path)
            console.print(paths_table)

    except Exception as e:
        show_error_panel("Snapshot Show Error", f"Failed to show snapshot details: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@snapshot_app.command("list")
def snapshot_list(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        path: Annotated[str, typer.Option("--path", help="Path within snapshot to list")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List contents of snapshot."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # List snapshot contents
        contents = service_manager.snapshot_service.list_snapshot_contents(repo, snapshot_id, path)

        if not contents:
            console.print(f"[yellow]No contents found in snapshot {snapshot_id[:12]}[/yellow]")
            return

        # Create table for contents
        table = Table(title=f"Snapshot Contents: {snapshot_id[:12]}" + (f" - {path}" if path else ""))
        table.add_column("Type", style="blue", no_wrap=True)
        table.add_column("Permissions", style="cyan", no_wrap=True)
        table.add_column("Size", style="green", justify="right")
        table.add_column("Modified", style="yellow")
        table.add_column("Path", style="white")

        for item in contents:
            # Format size
            size = item.get('size', 0)
            size_str = f"{size:,}" if size > 0 else "-"

            table.add_row(
                    "📁" if item.get('type') == 'directory' else "📄",
                    item.get('permissions', ''),
                    size_str,
                    item.get('modified', ''),
                    item.get('path', '')
            )

        console.print(table)
        console.print(f"\n[dim]Total items: {len(contents)}[/dim]")

    except Exception as e:
        show_error_panel("Snapshot List Error", f"Failed to list snapshot contents: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@snapshot_app.command("mount")
def snapshot_mount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        path: Annotated[Path, typer.Argument(help="Mount path")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Mount this snapshot as filesystem."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Mount snapshot
        with console.status(f"[bold green]Mounting snapshot {snapshot_id[:12]} at {path}..."):
            result = service_manager.snapshot_service.mount_snapshot(repo, snapshot_id, path)

        if result.status.value == "success":
            console.print(f"[green]✓[/green] {result.message}")
            console.print(f"[dim]Mount path: {path}[/dim]")
            console.print(f"[dim]Process ID: {result.details.get('process_id', 'unknown')}[/dim]")
        else:
            show_error_panel("Mount Failed", result.error_message or "Unknown error")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Snapshot Mount Error", f"Failed to mount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@snapshot_app.command("umount")
def snapshot_umount(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Unmount this snapshot."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Unmount snapshot
        with console.status(f"[bold yellow]Unmounting snapshot {snapshot_id[:12]}..."):
            result = service_manager.snapshot_service.unmount_snapshot(snapshot_id)

        if result.status.value == "success":
            console.print(f"[green]✓[/green] {result.message}")
            console.print(f"[dim]Mount path: {result.details.get('mount_path', 'unknown')}[/dim]")
        else:
            show_error_panel("Unmount Failed", result.error_message or "Unknown error")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Snapshot Unmount Error", f"Failed to unmount snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@snapshot_app.command("find")
def snapshot_find(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        pattern: Annotated[str, typer.Argument(help="Search pattern")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        search_type: Annotated[str, typer.Option("--type", help="Search type: name, content, path")] = "name",
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Search within this snapshot."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Search in snapshot
        with console.status(f"[bold blue]Searching for '{pattern}' in snapshot {snapshot_id[:12]}..."):
            results = service_manager.snapshot_service.search_in_snapshot(repo, snapshot_id, pattern, search_type)

        if not results:
            console.print(f"[yellow]No matches found for pattern '{pattern}' in snapshot {snapshot_id[:12]}[/yellow]")
            return

        # Display results
        table = Table(title=f"Search Results: '{pattern}' in {snapshot_id[:12]}")
        table.add_column("Match Type", style="blue", no_wrap=True)
        table.add_column("File Path", style="white")
        table.add_column("Context", style="dim")

        for result in results:
            context = ""
            if hasattr(result, 'line_number') and result.line_number:
                context = f"Line {result.line_number}"
            if hasattr(result, 'context') and result.context:
                context += f": {result.context[:50]}..." if len(result.context) > 50 else f": {result.context}"

            table.add_row(
                    result.match_type.title(),
                    result.file_path,
                    context
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(results)} matches[/dim]")

    except Exception as e:
        show_error_panel("Snapshot Find Error", f"Failed to search in snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


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
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be deleted without actually deleting")] = False,
        keep_last: Annotated[int, typer.Option("--keep-last", help="Number of most recent snapshots to keep")] = 10,
        keep_daily: Annotated[int, typer.Option("--keep-daily", help="Number of daily snapshots to keep")] = 7,
        keep_weekly: Annotated[int, typer.Option("--keep-weekly", help="Number of weekly snapshots to keep")] = 4,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Remove old snapshots across repos."""
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

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:

            task = progress.add_task("Initializing prune operation...", total=None)

            # For now, use legacy backup manager for snapshot operations
            # TODO: Implement snapshot service in Phase 4
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password)
            snapshot_manager = SnapshotManager(repo)

            progress.update(task, description="Analyzing snapshots...")
            snapshots = snapshot_manager.list_snapshots()

            if not snapshots:
                progress.remove_task(task)
                console.print("[yellow]No snapshots found to prune[/yellow]")
                return

            # Simple retention logic (this would be enhanced in a full implementation)
            snapshots_to_keep = snapshots[:keep_last]  # Keep most recent
            snapshots_to_remove = snapshots[keep_last:]

            progress.remove_task(task)

        if not snapshots_to_remove:
            console.print("[green]No snapshots need to be pruned[/green]")
            return

        # Display what will be removed
        table = Table(title=f"Snapshots to {'Remove (Dry Run)' if dry_run else 'Remove'}")
        table.add_column("Snapshot ID", style="red")
        table.add_column("Date", style="yellow")
        table.add_column("Hostname", style="blue")

        for snapshot in snapshots_to_remove:
            table.add_row(
                    snapshot.id[:12],
                    snapshot.time.strftime("%Y-%m-%d %H:%M:%S"),
                    snapshot.hostname
            )

        console.print(table)

        if dry_run:
            console.print(f"[yellow]Dry run: Would remove {len(snapshots_to_remove)} snapshots[/yellow]")
        else:
            if not yes and not Confirm.ask(f"Remove {len(snapshots_to_remove)} snapshots?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

            # TODO: Implement actual snapshot removal
            console.print("[yellow]🚧 Actual snapshot removal not yet implemented[/yellow]")
            console.print("This would remove the selected snapshots from the repository.")

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Prune operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Prune Error", f"Failed to prune snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


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
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Check this repository integrity."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository or name)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Check repository
        with console.status(f"[bold blue]Checking repository integrity for {name}..."):
            check_results = service_manager.repository_service.check_repository(repo)

        # Display results
        if check_results['status'] == 'success':
            console.print(f"[green]✓[/green] Repository {name} integrity check passed")

            # Show statistics if available
            if check_results.get('statistics'):
                stats = check_results['statistics']
                table = Table(title="Check Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="white")

                for key, value in stats.items():
                    if key != 'message_type':
                        table.add_row(key.replace('_', ' ').title(), str(value))

                console.print(table)
        else:
            console.print(f"[red]✗[/red] Repository {name} integrity check failed")
            for error in check_results.get('errors', []):
                console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Repository Check Error", f"Failed to check repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repo_app.command("stats")
def repo_stats(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show this repository statistics."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository or name)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Get repository statistics
        with console.status(f"[bold blue]Gathering statistics for repository {name}..."):
            stats = service_manager.repository_service.get_repository_stats(repo)

        # Display statistics
        table = Table(title=f"Repository Statistics: {name}")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Format and display key statistics
        if 'total_size' in stats:
            size_mb = stats['total_size'] / (1024 * 1024)
            table.add_row("Total Size", f"{size_mb:.2f} MB ({stats['total_size']:,} bytes)")

        if 'total_file_count' in stats:
            table.add_row("Total Files", f"{stats['total_file_count']:,}")

        if 'snapshot_count' in stats:
            table.add_row("Snapshots", f"{stats['snapshot_count']:,}")

        if 'compression_ratio' in stats and stats['compression_ratio'] > 0:
            table.add_row("Compression Ratio", f"{stats['compression_ratio']:.2f}")

        if 'time_span_days' in stats:
            table.add_row("Time Span", f"{stats['time_span_days']:.1f} days")

        if 'oldest_snapshot' in stats:
            from datetime import datetime
            oldest = datetime.fromtimestamp(stats['oldest_snapshot']).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("Oldest Snapshot", oldest)

        if 'newest_snapshot' in stats:
            from datetime import datetime
            newest = datetime.fromtimestamp(stats['newest_snapshot']).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("Newest Snapshot", newest)

        console.print(table)

    except Exception as e:
        show_error_panel("Repository Stats Error", f"Failed to get repository statistics: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repo_app.command("unlock")
def repo_unlock(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove locks from this repository."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository or name)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Unlock repository
        with console.status(f"[bold yellow]Unlocking repository {name}..."):
            success = service_manager.repository_service.unlock_repository(repo)

        if success:
            console.print(f"[green]✓[/green] Repository {name} unlocked successfully")
        else:
            console.print(f"[red]✗[/red] Failed to unlock repository {name}")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Repository Unlock Error", f"Failed to unlock repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repo_app.command("migrate")
def repo_migrate(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Migrate this repository format."""
    console.print(f"[yellow]🚧 Command stub: repo {name} migrate[/yellow]")
    console.print("This command will migrate the repository format.")


@repo_app.command("forget")
def repo_forget(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI")] = None,
        keep_daily: Annotated[int, typer.Option("--keep-daily", help="Number of daily snapshots to keep")] = 7,
        keep_weekly: Annotated[int, typer.Option("--keep-weekly", help="Number of weekly snapshots to keep")] = 4,
        keep_monthly: Annotated[int, typer.Option("--keep-monthly", help="Number of monthly snapshots to keep")] = 12,
        keep_yearly: Annotated[int, typer.Option("--keep-yearly", help="Number of yearly snapshots to keep")] = 3,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be removed without actually removing")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Apply retention policy to this repo."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository or name)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Apply retention policy
        action = "Analyzing" if dry_run else "Applying"
        with console.status(f"[bold blue]{action} retention policy for repository {name}..."):
            results = service_manager.repository_service.apply_retention_policy(
                    repo, keep_daily, keep_weekly, keep_monthly, keep_yearly, dry_run
            )

        # Display results
        if results['status'] == 'success':
            removed_count = len(results.get('removed_snapshots', []))
            kept_count = len(results.get('kept_snapshots', []))

            if dry_run:
                console.print(f"[yellow]Dry run:[/yellow] Would remove {removed_count} snapshots, keep {kept_count}")
            else:
                console.print(f"[green]✓[/green] Retention policy applied: removed {removed_count} snapshots, kept {kept_count}")

            # Show policy details
            table = Table(title="Retention Policy")
            table.add_column("Period", style="cyan")
            table.add_column("Keep", style="white")

            table.add_row("Daily", str(keep_daily))
            table.add_row("Weekly", str(keep_weekly))
            table.add_row("Monthly", str(keep_monthly))
            table.add_row("Yearly", str(keep_yearly))

            console.print(table)

            if removed_count > 0 and verbose:
                # Show removed snapshots
                removed_table = Table(title="Snapshots to Remove" if dry_run else "Removed Snapshots")
                removed_table.add_column("Snapshot ID", style="red")

                for snapshot_id in results.get('removed_snapshots', [])[:10]:  # Show first 10
                    removed_table.add_row(snapshot_id[:12])

                if len(results.get('removed_snapshots', [])) > 10:
                    removed_table.add_row(f"... and {len(results['removed_snapshots']) - 10} more")

                console.print(removed_table)
        else:
            console.print(f"[red]✗[/red] Failed to apply retention policy to repository {name}")
            for error in results.get('errors', []):
                console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Repository Forget Error", f"Failed to apply retention policy: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# REPOS COMMANDS (Multiple repository operations)
# ============================================================================

@repos_app.command("list")
def repos_list(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List all repositories."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()
        repositories = service_manager.list_repositories()

        if not repositories:
            console.print("[yellow]No repositories configured[/yellow]")
            return

        # Create table for repository listing
        table = Table(title="Configured Repositories")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("URI", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Description", style="white")

        for repo in repositories:
            repo_type = repo.get('type', 'auto')
            description = repo.get('description', '')
            # Handle both 'uri' (modern) and 'location' (legacy) fields
            location = repo.get('uri', repo.get('location', 'N/A'))
            table.add_row(
                    repo['name'],
                    location,
                    repo_type,
                    description
            )

        console.print(table)

    except Exception as e:
        show_error_panel("Repository List Error", f"Failed to list repositories: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
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
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show repository config details."""
    console.print(f"[yellow]🚧 Command stub: config repositories show {name}[/yellow]")
    console.print("This command will show configuration details for the specified repository.")


# Config target commands (single target operations)

@config_target_app.command("list")
def config_target_list(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List all backup targets."""
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get all backup targets
        targets = config_manager.get_backup_targets()

        if not targets:
            console.print("[yellow]No backup targets configured[/yellow]")
            console.print("💡 Use [bold]tl config targets add[/bold] to create a backup target")
            return

        # Create table for targets
        table = Table(
                title="🎯 Backup Targets",
                show_header=True,
                header_style="bold blue",
                border_style="blue"
        )

        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Paths", style="green")
        table.add_column("Patterns", style="yellow")

        for target in targets:
            name = target.get("name", "unknown")
            paths_str = "\n".join(target.get("paths", []))

            # Handle patterns - they might be in different formats
            patterns = target.get("patterns", {})
            if isinstance(patterns, dict):
                include_patterns = patterns.get("include", [])
                exclude_patterns = patterns.get("exclude", [])
            else:
                include_patterns = target.get("include_patterns", [])
                exclude_patterns = target.get("exclude_patterns", [])

            patterns_info = []
            if include_patterns and include_patterns != ["*"]:
                patterns_info.append(f"Include: {', '.join(include_patterns[:3])}")
                if len(include_patterns) > 3:
                    patterns_info.append(f"... +{len(include_patterns) - 3} more")

            if exclude_patterns:
                patterns_info.append(f"Exclude: {', '.join(exclude_patterns[:2])}")
                if len(exclude_patterns) > 2:
                    patterns_info.append(f"... +{len(exclude_patterns) - 2} more")

            patterns_str = "\n".join(patterns_info) if patterns_info else "Default"

            table.add_row(
                    name,
                    target.get("description", "No description"),
                    paths_str,
                    patterns_str
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        show_error_panel("List Targets Error", f"Failed to list backup targets: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


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
        name: Annotated[str, typer.Argument(help="Target name to remove", autocompletion=target_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Remove this target."""
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get target info before removal
        target_info = config_manager.get_backup_target(name)

        # Confirm removal unless --yes flag is used
        if not yes:
            console.print()
            console.print(Panel(
                    f"Target: {name}\n"
                    f"Description: {getattr(target_info, 'description', None) or 'N/A'}\n"
                    f"Paths: {', '.join(getattr(target_info, 'paths', []))}\n"
                    f"Include patterns: {', '.join(getattr(target_info, 'include_patterns', []))}\n"
                    f"Exclude patterns: {', '.join(getattr(target_info, 'exclude_patterns', []))}",
                    title="[bold yellow]Target to Remove[/bold yellow]",
                    border_style="yellow"
            ))

            if not Confirm.ask("Are you sure you want to remove this backup target?"):
                console.print("❌ Target removal cancelled.")
                return

        # Remove target
        config_manager.remove_backup_target(name)

        console.print()
        console.print(Panel(
                f"✅ Backup target '{name}' removed successfully!",
                title="[bold green]Target Removed[/bold green]",
                border_style="green"
        ))

    except ValueError as e:
        show_error_panel("Target Not Found", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to remove backup target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Config targets commands (multiple target operations)

@config_targets_app.command("list")
def config_targets_list(
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List all targets."""
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get all backup targets
        targets = config_manager.get_backup_targets()

        if not targets:
            console.print("[yellow]No backup targets configured[/yellow]")
            console.print("💡 Use [bold]tl config targets add[/bold] to create a backup target")
            return

        # Create table for target listing
        table = Table(
                title="🎯 Configured Backup Targets",
                show_header=True,
                header_style="bold blue",
                border_style="blue"
        )
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Paths", style="green")
        table.add_column("Include Patterns", style="blue")
        table.add_column("Exclude Patterns", style="red")

        for target in targets:
            name = target.get("name", "unknown")
            paths = "\n".join(target.get('paths', []))

            # Handle patterns - they might be in different formats
            patterns = target.get("patterns", {})
            if isinstance(patterns, dict):
                include_patterns = patterns.get("include", [])
                exclude_patterns = patterns.get("exclude", [])
            else:
                include_patterns = target.get("include_patterns", [])
                exclude_patterns = target.get("exclude_patterns", [])

            include_str = "\n".join(include_patterns) if include_patterns else "Default (*)"
            exclude_str = "\n".join(exclude_patterns) if exclude_patterns else "None"

            table.add_row(
                    name,
                    target.get("description", "No description"),
                    paths,
                    include_str,
                    exclude_str
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        show_error_panel("Target List Error", f"Failed to list backup targets: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@config_targets_app.command("remove")
def config_targets_remove(
        name: Annotated[str, typer.Argument(help="Target name to remove", autocompletion=target_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Remove a backup target from configuration."""
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get target info before removal
        target_info = config_manager.get_backup_target(name)

        # Confirm removal unless --yes flag is used
        if not yes:
            console.print()
            console.print(Panel(
                    f"Target: {name}\n"
                    f"Description: {getattr(target_info, 'description', None) or 'N/A'}\n"
                    f"Paths: {', '.join(getattr(target_info, 'paths', []))}\n"
                    f"Include patterns: {', '.join(getattr(target_info, 'include_patterns', []))}\n"
                    f"Exclude patterns: {', '.join(getattr(target_info, 'exclude_patterns', []))}",
                    title="[bold yellow]Target to Remove[/bold yellow]",
                    border_style="yellow"
            ))

            if not Confirm.ask("Are you sure you want to remove this backup target?"):
                console.print("❌ Target removal cancelled.")
                return

        # Remove target
        config_manager.remove_backup_target(name)

        console.print()
        console.print(Panel(
                f"✅ Backup target '{name}' removed successfully!",
                title="[bold green]Target Removed[/bold green]",
                border_style="green"
        ))

    except ValueError as e:
        show_error_panel("Target Not Found", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to remove backup target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Credential management commands

@credentials_app.command("unlock")
def credentials_unlock(
        master_password: Annotated[str, typer.Option("--password", "-p", help="Master password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Unlock the credential manager with master password."""
    setup_logging(verbose)

    try:
        from .security.credential_manager import CredentialManager

        credential_manager = CredentialManager()

        if not master_password:
            master_password = Prompt.ask("Master password", password=True)

        if credential_manager.unlock(master_password):
            console.print("[green]✅ Credential manager unlocked successfully[/green]")
        else:
            console.print("[red]❌ Failed to unlock credential manager[/red]")
            raise typer.Exit(1)

    except Exception as e:
        show_error_panel("Credential Unlock Error", f"Failed to unlock credential manager: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@credentials_app.command("lock")
def credentials_lock(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Lock the credential manager."""
    setup_logging(verbose)

    try:
        from .security.credential_manager import CredentialManager

        credential_manager = CredentialManager()
        credential_manager.lock()
        console.print("[yellow]🔒 Credential manager locked[/yellow]")

    except Exception as e:
        show_error_panel("Credential Lock Error", f"Failed to lock credential manager: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@credentials_app.command("store")
def credentials_store(
        repository_name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        master_password: Annotated[str, typer.Option("--master-password", "-m", help="Master password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Store encrypted password for a repository."""
    setup_logging(verbose)

    try:
        from .security.credential_manager import CredentialManager

        credential_manager = CredentialManager()

        # Unlock credential manager if needed
        if credential_manager.is_locked():
            if not master_password:
                master_password = Prompt.ask("Master password", password=True)

            if not credential_manager.unlock(master_password):
                console.print("[red]❌ Failed to unlock credential manager[/red]")
                raise typer.Exit(1)

        # Get repository password if not provided
        if not password:
            password = Prompt.ask(f"Password for repository '{repository_name}'", password=True)

        # Store the password
        credential_manager.store_repository_password(repository_name, password)
        console.print(f"[green]✅ Password stored for repository '{repository_name}'[/green]")

    except Exception as e:
        show_error_panel("Credential Store Error", f"Failed to store password: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@credentials_app.command("list")
def credentials_list(
        master_password: Annotated[str, typer.Option("--password", "-p", help="Master password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List stored repository credentials."""
    setup_logging(verbose)

    try:
        from .security.credential_manager import CredentialManager

        credential_manager = CredentialManager()

        # Unlock credential manager if needed
        if credential_manager.is_locked():
            if not master_password:
                master_password = Prompt.ask("Master password", password=True)

            if not credential_manager.unlock(master_password):
                console.print("[red]❌ Failed to unlock credential manager[/red]")
                raise typer.Exit(1)

        # List repositories
        repositories = credential_manager.list_repositories()

        if not repositories:
            console.print("[yellow]No stored credentials found[/yellow]")
            console.print("💡 Use [bold]tl credentials store[/bold] to store repository passwords")
            return

        # Create table for credential listing
        table = Table(
                title="🔐 Stored Repository Credentials",
                show_header=True,
                header_style="bold blue",
                border_style="blue"
        )
        table.add_column("Repository", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")

        for repo_name in repositories:
            table.add_row(repo_name, "✅ Stored")

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        show_error_panel("Credential List Error", f"Failed to list credentials: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@credentials_app.command("remove")
def credentials_remove(
        repository_name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        master_password: Annotated[str, typer.Option("--password", "-p", help="Master password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove stored password for a repository."""
    setup_logging(verbose)

    try:
        from .security.credential_manager import CredentialManager

        credential_manager = CredentialManager()

        # Unlock credential manager if needed
        if credential_manager.is_locked():
            if not master_password:
                master_password = Prompt.ask("Master password", password=True)

            if not credential_manager.unlock(master_password):
                console.print("[red]❌ Failed to unlock credential manager[/red]")
                raise typer.Exit(1)

        # Remove the password
        if credential_manager.remove_repository(repository_name):
            console.print(f"[green]✅ Password removed for repository '{repository_name}'[/green]")
        else:
            console.print(f"[yellow]⚠️ No stored password found for repository '{repository_name}'[/yellow]")

    except Exception as e:
        show_error_panel("Credential Remove Error", f"Failed to remove password: {e}")
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
        # Escape Rich markup in error message to prevent markup errors
        error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
        show_error_panel("Unexpected Error", f"An unexpected error occurred: {error_msg}")
        console.print_exception()
        raise typer.Exit(1)


if __name__ == "__main__":
    main()
