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
    repository_completer,
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

snapshots_app = typer.Typer(help="Snapshot operations")
repos_app = typer.Typer(help="Repository operations")
targets_app = typer.Typer(help="Backup target operations")
config_app = typer.Typer(help="Configuration management commands")
credentials_app = typer.Typer(help="Credential management commands")

# Add sub-apps to main app
app.add_typer(backup_app, name="backup")

app.add_typer(snapshots_app, name="snapshots")
app.add_typer(repos_app, name="repos")
app.add_typer(targets_app, name="targets")
app.add_typer(config_app, name="config")
app.add_typer(credentials_app, name="credentials")

# Create config sub-apps (only import remains under config)
config_import_app = typer.Typer(help="Import configuration commands")

# Add config sub-apps
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
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
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
        logger = logging.getLogger(__name__)
        logger.debug(f"backup_target type: {type(backup_target)}")
        logger.debug(f"backup_target content: {backup_target}")
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

        # Create repository instance to leverage full password resolution chain
        # (explicit password → credential manager → environment → prompt)
        backup_manager = BackupManager()
        repo = backup_manager.from_uri(repository_uri, password=password)

        # Get password from repository (uses full resolution chain)
        resolved_password = repo.password()
        if not resolved_password:
            # Only prompt if repository couldn't resolve password
            resolved_password = Prompt.ask("Repository password", password=True)

        password = resolved_password
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

    try:
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting backup execution with repository_uri: {repository_uri}")
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console,
        ) as progress:

            # Initialize service manager
            task = progress.add_task("Initializing backup...", total=None)
            logger.debug("About to call get_cli_service_manager()")
            service_manager = get_cli_service_manager()
            logger.debug(f"Service manager created: {type(service_manager)}")

            # Create backup request
            progress.update(task, description="Preparing backup request...")
            logger.debug(f"Creating CLIBackupRequest with sources={sources}, repository_uri={repository_uri}, target_name={target}")
            logger.debug(f"CLI collected password: {'***' if password else 'None'}")
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
            logger.debug("CLIBackupRequest created successfully")
            logger.debug(f"CLIBackupRequest password field: {'***' if backup_request.password else 'None'}")

            # Execute backup using modern orchestrator
            progress.update(task, description="Executing backup...")
            logger.debug(f"About to call execute_backup_from_cli with repository_uri: {backup_request.repository_uri}")
            result = service_manager.execute_backup_from_cli(backup_request)
            logger.debug(f"Backup result: {result.status}")

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


@snapshots_app.command("restore")
def snapshots_restore(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID", autocompletion=snapshot_id_completer)],
        target: Annotated[Path, typer.Argument(help="Target path for restore", autocompletion=file_path_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
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
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List snapshots in repository with a beautiful table."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri, get_repository_info, get_default_repository

        # Get the actual repository name (for default case)
        actual_repository_name = repository or get_default_repository()
        repository_uri = resolve_repository_uri(repository)
        repo_info = get_repository_info(actual_repository_name or repository_uri)

        # Show which repository is being used if verbose or no repository specified
        if verbose or not repository:
            if repo_info.get("is_named"):
                console.print(f"[dim]Using repository: {repo_info.get('name')} ({repository_uri})[/dim]")
            else:
                console.print(f"[dim]Using repository: {repository_uri}[/dim]")

        # Create repository instance to leverage full password resolution chain
        # (explicit password → credential manager → environment → prompt)
        backup_manager = BackupManager()
        repo = backup_manager.from_uri(repository_uri, password=password)

        # Get password from repository (uses full resolution chain)
        resolved_password = repo.password()
        if not resolved_password:
            # Provide helpful context about which repository needs a password
            repo_display = repo_info.get('name', repository_uri) if repo_info.get("is_named") else repository_uri

            # Check if this is a named repository without stored credentials
            if repo_info.get("is_named"):
                console.print(f"[yellow]Repository '{repo_info.get('name')}' requires a password.[/yellow]")
                console.print(f"[dim]💡 Store password permanently: tl repos add {repo_info.get('name')} {repository_uri}[/dim]")
            else:
                console.print(f"[yellow]Repository {repository_uri} requires a password.[/yellow]")

            # Only prompt if repository couldn't resolve password
            resolved_password = Prompt.ask("Repository password", password=True)

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

            # Repository already created above, just update progress
            progress.update(task, description="Connecting to repository...")

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


@repos_app.command("init")
def repo_init(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Initialize this repository."""
    setup_logging(verbose)

    try:
        # Resolve repository name to URI
        from .utils.repository_resolver import resolve_repository_uri
        repository_uri = resolve_repository_uri(repository or name)

        # Create repository instance to leverage full password resolution chain
        # (explicit password → credential manager → environment → prompt)
        manager = BackupManager()
        repo = manager.from_uri(repository_uri, password=password)

        # Get password from repository (uses full resolution chain)
        resolved_password = repo.password()
        if not resolved_password:
            # Only prompt if repository couldn't resolve password
            resolved_password = Prompt.ask("Repository password", password=True)

        password = resolved_password
    except Exception as e:
        show_error_panel("Repository Error", str(e))
        raise typer.Exit(1)

    # Confirm repository creation unless --yes flag is used
    if not yes and not Confirm.ask(f"Initialize new repository at [bold]{repository_uri}[/bold]?"):
        show_info_panel("Operation Cancelled", "Repository initialization cancelled by user")
        raise typer.Exit(0)

    try:
        # Check if repository already exists before showing progress
        if repo.is_repository_initialized():
            show_info_panel(
                    "Repository Already Exists",
                    f"Repository at {repository_uri} is already initialized and ready to use."
            )
            return

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:

            task = progress.add_task("Initializing repository...", total=None)

            # Initialize repository (repo instance already created above)
            if not repo.initialize_repository(password):
                raise Exception("Repository initialization failed")

            progress.remove_task(task)

        show_success_panel(
                "Repository Initialized",
                "Repository created successfully!",
                {"Repository URI": repository_uri}
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
    """Show configuration information and validation status."""
    setup_logging(verbose, config_dir)

    try:
        from .config import ConfigurationModule, ConfigurationValidator
        config_module = ConfigurationModule(config_dir=config_dir)
        config = config_module.get_config()
        config_file = config_module.config_file
        config_info = config_module.get_config_info()

        console.print()
        console.print(Panel(
                f"📁 Configuration from: {config_file}",
                title="[bold blue]TimeLocker Configuration[/bold blue]",
                border_style="blue"
        ))

        # Configuration paths table
        table = Table(title="📂 Configuration Paths", border_style="green")
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white")
        table.add_column("Status", style="yellow")

        # Current configuration
        table.add_row(
                "Config Directory",
                config_info['current_config_dir'],
                "✅ Active" if config_info['config_file_exists'] else "❌ Missing"
        )

        table.add_row(
                "Config File",
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

        console.print(table)
        console.print()

        # Configuration validation
        console.print(Panel(
                "🔍 Running configuration validation...",
                title="[bold yellow]Configuration Validation[/bold yellow]",
                border_style="yellow"
        ))

        validator = ConfigurationValidator()
        validation_result = validator.validate_config(config)

        if validation_result.is_valid:
            console.print(Panel(
                    "✅ Configuration validation passed successfully!\n"
                    "All settings are valid and properly configured.",
                    title="[bold green]Validation Successful[/bold green]",
                    border_style="green"
            ))
        else:
            # Show validation errors
            if validation_result.errors:
                error_text = "\n".join([f"❌ {error}" for error in validation_result.errors])
                console.print(Panel(
                        error_text,
                        title="[bold red]Validation Errors[/bold red]",
                        border_style="red"
                ))

        # Show validation warnings
        if validation_result.warnings:
            warning_text = "\n".join([f"⚠️  {warning}" for warning in validation_result.warnings])
            console.print(Panel(
                    warning_text,
                    title="[bold yellow]Validation Warnings[/bold yellow]",
                    border_style="yellow"
            ))

        # General settings summary
        settings_text = ""
        if hasattr(config.general, 'app_name') and config.general.app_name:
            settings_text += f"[bold]App Name:[/bold] {config.general.app_name}\n"
        if hasattr(config.general, 'default_repository') and config.general.default_repository:
            settings_text += f"[bold]Default Repository:[/bold] {config.general.default_repository}\n"
        if hasattr(config.general, 'max_concurrent_operations') and config.general.max_concurrent_operations:
            settings_text += f"[bold]Max Concurrent Operations:[/bold] {config.general.max_concurrent_operations}\n"
        if hasattr(config.general, 'log_level') and config.general.log_level:
            settings_text += f"[bold]Log Level:[/bold] {config.general.log_level}\n"

        # Repository and target counts
        repo_count = len(config.repositories) if config.repositories else 0
        target_count = len(config.backup_targets) if config.backup_targets else 0
        settings_text += f"[bold]Repositories:[/bold] {repo_count} configured\n"
        settings_text += f"[bold]Backup Targets:[/bold] {target_count} configured\n"

        if settings_text:
            console.print(Panel(
                    settings_text.strip(),
                    title="⚙️  Configuration Summary",
                    border_style="blue"
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


@repos_app.command("list")
def repos_list(
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


@repos_app.command("add")
def repos_add(
        name: Annotated[Optional[str], typer.Argument(help="Repository name")] = None,
        uri: Annotated[Optional[str], typer.Argument(help="Repository URI", autocompletion=repository_uri_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Repository description")] = None,
        password: Annotated[Optional[str], typer.Option("--password", "-p", help="Repository password")] = None,
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
        from .security.credential_manager import CredentialManager
        from .backup_manager import BackupManager
        import logging
        logger = logging.getLogger(__name__)
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Add repository configuration
        repository_config = {
                'name':        name,
                'location':    uri,
                'description': description or f"{name} repository"
        }
        config_manager.add_repository(repository_config)

        # Handle password storage for the repository
        password_stored = False
        if not password:
            # Check environment variables first
            password = os.getenv("TIMELOCKER_PASSWORD") or os.getenv("RESTIC_PASSWORD")
            if not password:
                # Ask user if they want to store a password for this repository
                if Confirm.ask(f"Would you like to store a password for repository '{name}'?"):
                    password = Prompt.ask(f"Password for repository '{name}'", password=True)

        # Store password if provided
        if password:
            try:
                # Create repository instance to get proper repository ID
                # Note: This may fail if repository doesn't exist yet, which is OK
                backup_manager = BackupManager()
                repo = backup_manager.from_uri(uri, password=password)

                # Store password using repository's store_password method
                if repo.store_password(password, allow_prompt=False):
                    password_stored = True
                    logger.info(f"Password stored for repository '{name}' (ID: {repo.repository_id()})")
                else:
                    # Store password temporarily in repository configuration for later use during init
                    repository_config['password'] = password
                    config_manager.update_repository(name, repository_config)
                    logger.debug(f"Password stored temporarily in configuration for repository '{name}'")
            except Exception as e:
                # Repository creation failed (e.g., doesn't exist yet) - that's OK
                # Store password temporarily in repository configuration for later use during init
                repository_config['password'] = password
                config_manager.update_repository(name, repository_config)
                logger.debug(f"Password stored temporarily in configuration for repository '{name}': {e}")

        # Set as default if requested
        if set_default:
            config_manager.set_default_repository(name)

        # Build success message
        success_details = [
                f"📍 URI: {uri}",
                f"📝 Description: {description or f'{name} repository'}",
                f"🎯 Default: {'Yes' if set_default else 'No'}",
        ]

        if password_stored:
            success_details.append("🔐 Password: Stored securely")
        elif password:
            success_details.append("🔐 Password: Provided (will be stored during initialization)")
        else:
            success_details.append("🔐 Password: Not provided")

        console.print()
        console.print(Panel(
                f"✅ Repository '{name}' added successfully!\n\n" + "\n".join(success_details),
                title="[bold green]Repository Added[/bold green]",
                border_style="green"
        ))

        # Show usage example
        console.print()
        console.print(f"💡 [bold]Usage example:[/bold] [cyan]tl list -r {name}[/cyan]")

        if password_stored:
            console.print(f"🔒 [bold]Password stored:[/bold] Repository operations will work without prompts")
        elif password:
            console.print(f"💡 [bold]Next step:[/bold] Run [cyan]tl repo init {name}[/cyan] to initialize and store password")

    except RepositoryAlreadyExistsError as e:
        show_error_panel("Repository Exists", str(e))
        raise typer.Exit(1)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to add repository: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_app.command("remove")
def repos_remove(
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


@repos_app.command("default")
def repos_default(
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


@targets_app.command("add")
def targets_add(
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

@snapshots_app.command("show")
def snapshots_show(
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


@snapshots_app.command("contents")
def snapshots_contents(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        path: Annotated[str, typer.Option("--path", help="Path within snapshot to list")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """List contents of a specific snapshot."""
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


@snapshots_app.command("mount")
def snapshots_mount(
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


@snapshots_app.command("umount")
def snapshots_umount(
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


@snapshots_app.command("find-in")
def snapshots_find_in(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        pattern: Annotated[str, typer.Argument(help="Search pattern")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        search_type: Annotated[str, typer.Option("--type", help="Search type: name, content, path")] = "name",
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Search within a specific snapshot."""
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


@snapshots_app.command("forget")
def snapshots_forget(
        snapshot_id: Annotated[str, typer.Argument(help="Snapshot ID")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Remove this specific snapshot."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Resolve repository
        if not repository:
            repository = service_manager.config_module.get_default_repository_name()
            if not repository:
                show_error_panel("Repository Required", "No repository specified and no default repository configured")
                raise typer.Exit(1)

        repository_uri = service_manager.resolve_repository_uri(repository)

        # Get repository instance
        repo = service_manager.repository_factory.create_repository(repository_uri)

        # Get snapshot details for confirmation
        try:
            snapshot_info = service_manager.snapshot_service.get_snapshot_details(repo, snapshot_id)

            # Show snapshot details
            table = Table(title=f"Snapshot to Remove: {snapshot_id}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Snapshot ID", snapshot_info.id)
            table.add_row("Created", snapshot_info.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            table.add_row("Hostname", snapshot_info.hostname)
            table.add_row("Username", snapshot_info.username)
            table.add_row("Paths", ", ".join(snapshot_info.paths))
            table.add_row("Size", f"{snapshot_info.size:,} bytes" if snapshot_info.size else "Unknown")

            console.print()
            console.print(table)
            console.print()

        except Exception as e:
            show_error_panel("Snapshot Not Found", f"Could not find snapshot {snapshot_id}: {e}")
            raise typer.Exit(1)

        # Confirmation prompt
        if not yes:
            console.print("[red]⚠️  WARNING: This operation cannot be undone![/red]")
            if not Confirm.ask(f"Are you sure you want to remove snapshot {snapshot_id}?"):
                show_info_panel("Operation Cancelled", "Snapshot removal cancelled by user")
                raise typer.Exit(0)

        # Remove the snapshot
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Removing snapshot...", total=None)

            result = service_manager.snapshot_service.forget_snapshot(repo, snapshot_id)

            progress.remove_task(task)

        # Show success message
        show_success_panel(
                "Snapshot Removed Successfully!",
                f"✅ Snapshot {snapshot_id} has been removed from the repository\n"
                f"📍 Repository: {repository_uri}\n"
                f"🗑️  Operation completed successfully"
        )

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Snapshot removal was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Snapshot Removal Error", f"Failed to remove snapshot: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


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
        metadata: Annotated[bool, typer.Option("--metadata", help="Include metadata changes")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Compare two snapshots."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get repository
        if repository:
            try:
                repo = service_manager.get_repository_by_name(repository)
            except Exception as e:
                show_error_panel("Repository Not Found", f"Repository '{repository}' not found: {e}")
                raise typer.Exit(1)
        else:
            # Use default repository if available
            repos = service_manager.list_repositories()
            if not repos:
                show_error_panel("No Repositories", "No repositories configured. Use 'tl repos add' to add one.")
                raise typer.Exit(1)
            repo = repos[0]  # Use first repository as default
            if verbose:
                console.print(f"[dim]Using default repository: {repo.get('name', 'unnamed')}[/dim]")

        # Get snapshot service
        snapshot_service = service_manager.get_snapshot_service()

        # Perform snapshot comparison
        try:
            diff_result = snapshot_service.diff_snapshots(repo, id1, id2, include_metadata=metadata)
        except Exception as e:
            show_error_panel("Comparison Failed", f"Failed to compare snapshots: {e}")
            raise typer.Exit(1)

        # Display results
        console.print()
        console.print(f"[bold cyan]Snapshot Comparison: {id1} → {id2}[/bold cyan]")
        console.print()

        # Summary statistics
        summary_table = Table(title="Comparison Summary")
        summary_table.add_column("Category", style="cyan", no_wrap=True)
        summary_table.add_column("Count", style="white", justify="right")

        summary_table.add_row("Added Files", f"[green]+{len(diff_result.added_files)}[/green]")
        summary_table.add_row("Removed Files", f"[red]-{len(diff_result.removed_files)}[/red]")
        summary_table.add_row("Modified Files", f"[yellow]~{len(diff_result.modified_files)}[/yellow]")
        summary_table.add_row("Unchanged Files", f"[dim]{len(diff_result.unchanged_files)}[/dim]")

        console.print(summary_table)
        console.print()

        # Show detailed changes if any exist
        if diff_result.added_files or diff_result.removed_files or diff_result.modified_files:

            # Added files
            if diff_result.added_files:
                console.print("[bold green]Added Files:[/bold green]")
                for file_path in diff_result.added_files[:20]:  # Limit to first 20
                    console.print(f"  [green]+[/green] {file_path}")
                if len(diff_result.added_files) > 20:
                    console.print(f"  [dim]... and {len(diff_result.added_files) - 20} more[/dim]")
                console.print()

            # Removed files
            if diff_result.removed_files:
                console.print("[bold red]Removed Files:[/bold red]")
                for file_path in diff_result.removed_files[:20]:  # Limit to first 20
                    console.print(f"  [red]-[/red] {file_path}")
                if len(diff_result.removed_files) > 20:
                    console.print(f"  [dim]... and {len(diff_result.removed_files) - 20} more[/dim]")
                console.print()

            # Modified files
            if diff_result.modified_files:
                console.print("[bold yellow]Modified Files:[/bold yellow]")
                for file_path in diff_result.modified_files[:20]:  # Limit to first 20
                    size_info = ""
                    if file_path in diff_result.size_changes:
                        old_size = diff_result.size_changes[file_path]['old']
                        new_size = diff_result.size_changes[file_path]['new']
                        size_change = new_size - old_size
                        if size_change > 0:
                            size_info = f" [green](+{size_change:,} bytes)[/green]"
                        elif size_change < 0:
                            size_info = f" [red]({size_change:,} bytes)[/red]"
                        else:
                            size_info = f" [dim](no size change)[/dim]"
                    console.print(f"  [yellow]~[/yellow] {file_path}{size_info}")
                if len(diff_result.modified_files) > 20:
                    console.print(f"  [dim]... and {len(diff_result.modified_files) - 20} more[/dim]")
                console.print()
        else:
            console.print("[dim]No differences found between snapshots.[/dim]")

        # Show metadata changes if requested and available
        if metadata and diff_result.metadata_changes:
            console.print("[bold blue]Metadata Changes:[/bold blue]")
            for key, value in diff_result.metadata_changes.items():
                console.print(f"  [blue]•[/blue] {key}: {value}")
            console.print()

        # Verbose output
        if verbose:
            # Size change summary
            if diff_result.size_changes:
                total_size_change = sum(
                        change['new'] - change['old']
                        for change in diff_result.size_changes.values()
                )

                size_panel_content = []
                size_panel_content.append(f"Total size change: {total_size_change:+,} bytes")
                size_panel_content.append(f"Files with size changes: {len(diff_result.size_changes)}")

                # Show largest changes
                sorted_changes = sorted(
                        diff_result.size_changes.items(),
                        key=lambda x: abs(x[1]['new'] - x[1]['old']),
                        reverse=True
                )

                if sorted_changes:
                    size_panel_content.append("\nLargest changes:")
                    for file_path, change in sorted_changes[:5]:
                        size_diff = change['new'] - change['old']
                        size_panel_content.append(f"  {file_path}: {size_diff:+,} bytes")

                size_panel = Panel(
                        "\n".join(size_panel_content),
                        title="Size Analysis",
                        border_style="blue"
                )
                console.print(size_panel)

            # Repository information
            repo_info = [
                    f"Repository: {repo.get('name', 'unnamed')}",
                    f"Location: {repo.get('location', 'unknown')}",
                    f"Snapshot 1: {id1}",
                    f"Snapshot 2: {id2}",
                    f"Metadata included: {'Yes' if metadata else 'No'}"
            ]

            repo_panel = Panel(
                    "\n".join(repo_info),
                    title="Comparison Details",
                    border_style="dim"
            )
            console.print(repo_panel)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Snapshot comparison was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Comparison Error", f"Failed to compare snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@snapshots_app.command("find")
def snapshots_find(
        pattern: Annotated[str, typer.Argument(help="Search pattern")],
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI")] = None,
        search_type: Annotated[str, typer.Option("--type", help="Search type: name, content, path")] = "name",
        host: Annotated[str, typer.Option("--host", help="Filter by host")] = None,
        tags: Annotated[List[str], typer.Option("--tag", help="Filter by tags (can be specified multiple times)")] = None,
        limit: Annotated[int, typer.Option("--limit", help="Limit number of results")] = 100,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Search across all snapshots."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get repository
        if repository:
            try:
                repo = service_manager.get_repository_by_name(repository)
            except Exception as e:
                show_error_panel("Repository Not Found", f"Repository '{repository}' not found: {e}")
                raise typer.Exit(1)
        else:
            # Use default repository if available
            repos = service_manager.list_repositories()
            if not repos:
                show_error_panel("No Repositories", "No repositories configured. Use 'tl repos add' to add one.")
                raise typer.Exit(1)
            repo = repos[0]  # Use first repository as default
            if verbose:
                console.print(f"[dim]Using default repository: {repo.get('name', 'unnamed')}[/dim]")

        # Get snapshot service
        snapshot_service = service_manager.get_snapshot_service()

        # Perform search across all snapshots
        console.print(f"[cyan]Searching for pattern '[bold]{pattern}[/bold]' across all snapshots...[/cyan]")

        try:
            search_results = snapshot_service.search_across_snapshots(
                    repo, pattern, search_type=search_type, host=host, tags=tags
            )
        except Exception as e:
            show_error_panel("Search Failed", f"Failed to search across snapshots: {e}")
            raise typer.Exit(1)

        # Display results
        if not search_results:
            console.print()
            console.print("[yellow]No matches found.[/yellow]")
            console.print(f"[dim]Searched for pattern '{pattern}' using {search_type} search[/dim]")
            if host:
                console.print(f"[dim]Host filter: {host}[/dim]")
            if tags:
                console.print(f"[dim]Tag filters: {', '.join(tags)}[/dim]")
            return

        # Limit results if requested
        total_results = len(search_results)
        if limit and total_results > limit:
            search_results = search_results[:limit]
            truncated = True
        else:
            truncated = False

        # Group results by snapshot for better display
        results_by_snapshot = {}
        for result in search_results:
            snapshot_id = result.snapshot_id
            if snapshot_id not in results_by_snapshot:
                results_by_snapshot[snapshot_id] = []
            results_by_snapshot[snapshot_id].append(result)

        console.print()
        console.print(f"[bold green]Found {total_results} matches in {len(results_by_snapshot)} snapshots[/bold green]")
        if truncated:
            console.print(f"[yellow]Showing first {limit} results (use --limit to adjust)[/yellow]")
        console.print()

        # Create results table
        table = Table(title=f"Search Results for '{pattern}'")
        table.add_column("Snapshot", style="cyan", no_wrap=True, width=12)
        table.add_column("File Path", style="white")
        table.add_column("Match Type", style="green", no_wrap=True)

        # Add results to table
        for snapshot_id in sorted(results_by_snapshot.keys()):
            snapshot_results = results_by_snapshot[snapshot_id]

            # Show snapshot ID only for first result in each snapshot
            first_result = True
            for result in snapshot_results:
                snapshot_display = snapshot_id[:12] if first_result else ""
                table.add_row(
                        snapshot_display,
                        result.file_path,
                        result.match_type
                )
                first_result = False

        console.print(table)

        # Show summary statistics
        if verbose or len(results_by_snapshot) > 1:
            console.print()

            # Snapshot summary
            snapshot_summary = Table(title="Results by Snapshot")
            snapshot_summary.add_column("Snapshot ID", style="cyan", no_wrap=True)
            snapshot_summary.add_column("Matches", style="white", justify="right")
            snapshot_summary.add_column("Sample Files", style="dim")

            for snapshot_id in sorted(results_by_snapshot.keys()):
                snapshot_results = results_by_snapshot[snapshot_id]
                sample_files = [r.file_path for r in snapshot_results[:3]]
                sample_text = ", ".join(sample_files)
                if len(snapshot_results) > 3:
                    sample_text += f", ... (+{len(snapshot_results) - 3} more)"

                snapshot_summary.add_row(
                        snapshot_id[:12],
                        str(len(snapshot_results)),
                        sample_text
                )

            console.print(snapshot_summary)

        # Verbose output
        if verbose:
            console.print()

            # Search details
            search_details = [
                    f"Pattern: {pattern}",
                    f"Search type: {search_type}",
                    f"Total results: {total_results}",
                    f"Snapshots searched: {len(results_by_snapshot)}",
                    f"Repository: {repo.get('name', 'unnamed')}"
            ]

            if host:
                search_details.append(f"Host filter: {host}")
            if tags:
                search_details.append(f"Tag filters: {', '.join(tags)}")
            if truncated:
                search_details.append(f"Results limited to: {limit}")

            search_panel = Panel(
                    "\n".join(search_details),
                    title="Search Details",
                    border_style="blue"
            )
            console.print(search_panel)

            # File type analysis
            if search_type == 'name':
                file_extensions = {}
                for result in search_results:
                    path = result.file_path
                    if '.' in path:
                        ext = path.split('.')[-1].lower()
                        file_extensions[ext] = file_extensions.get(ext, 0) + 1

                if file_extensions:
                    ext_summary = []
                    for ext, count in sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
                        ext_summary.append(f".{ext}: {count}")

                    ext_panel = Panel(
                            "\n".join(ext_summary),
                            title="File Types Found",
                            border_style="green"
                    )
                    console.print(ext_panel)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Search operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Search Error", f"Failed to search across snapshots: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# REPO COMMANDS (Single repository operations)
# ============================================================================

@repos_app.command("check")
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


@repos_app.command("stats")
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


@repos_app.command("unlock")
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


@repos_app.command("migrate")
def repo_migrate(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        migration: Annotated[str, typer.Option("--migration", "-m", help="Migration name to apply")] = "upgrade_repo_v2",
        list_migrations: Annotated[bool, typer.Option("--list", help="List available migrations")] = False,
        force: Annotated[bool, typer.Option("--force", "-f", help="Force migration without confirmation")] = False,
        check_first: Annotated[bool, typer.Option("--check/--no-check", help="Check repository integrity before migration")] = True,
        prune_after: Annotated[bool, typer.Option("--prune/--no-prune", help="Run prune after migration to compress metadata")] = True,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Migrate repository format to newer version."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get repository
        try:
            repo = service_manager.get_repository_by_name(name)
        except Exception as e:
            show_error_panel("Repository Not Found", f"Repository '{name}' not found: {e}")
            raise typer.Exit(1)

        # Get repository service
        repository_service = service_manager.get_repository_service()

        # List available migrations if requested
        if list_migrations:
            console.print(f"[cyan]Checking available migrations for repository '[bold]{name}[/bold]'...[/cyan]")

            try:
                available_migrations = repository_service.list_available_migrations(repo)
            except Exception as e:
                show_error_panel("Migration Check Failed", f"Failed to check available migrations: {e}")
                raise typer.Exit(1)

            if not available_migrations:
                console.print()
                console.print("[green]✅ No migrations available - repository is up to date[/green]")
                return

            # Display available migrations
            console.print()
            console.print(f"[bold green]Available migrations for repository '{name}':[/bold green]")

            migrations_table = Table(title="Available Migrations")
            migrations_table.add_column("Migration Name", style="cyan", no_wrap=True)
            migrations_table.add_column("Description", style="white")

            for migration_name in available_migrations:
                description = ""
                if migration_name == "upgrade_repo_v2":
                    description = "Upgrade to repository format version 2 (enables compression)"
                else:
                    description = "Repository format migration"

                migrations_table.add_row(migration_name, description)

            console.print(migrations_table)

            if verbose:
                console.print()
                migration_info = [
                        "Migration Information:",
                        "• upgrade_repo_v2: Upgrades to repository format version 2",
                        "• Enables compression for new backups",
                        "• Requires restic 0.14.0 or newer to access repository",
                        "• Run 'prune' after migration to compress existing metadata",
                        "• Use 'prune --repack-uncompressed' to compress all data"
                ]

                info_panel = Panel(
                        "\n".join(migration_info),
                        title="Migration Details",
                        border_style="blue"
                )
                console.print(info_panel)

            return

        # Check repository integrity first if requested
        if check_first:
            console.print(f"[cyan]Checking repository integrity before migration...[/cyan]")

            try:
                check_results = repository_service.check_repository(repo)
                if check_results['status'] != 'success':
                    show_error_panel(
                            "Repository Check Failed",
                            f"Repository integrity check failed. Migration cannot proceed.\n"
                            f"Errors: {', '.join(check_results.get('errors', []))}"
                    )
                    raise typer.Exit(1)

                console.print("[green]✅ Repository integrity check passed[/green]")

            except Exception as e:
                show_error_panel("Repository Check Failed", f"Failed to check repository integrity: {e}")
                raise typer.Exit(1)

        # Get available migrations to validate the requested migration
        try:
            available_migrations = repository_service.list_available_migrations(repo)
        except Exception as e:
            show_error_panel("Migration Check Failed", f"Failed to check available migrations: {e}")
            raise typer.Exit(1)

        if not available_migrations:
            console.print()
            console.print("[green]✅ No migrations available - repository is already up to date[/green]")
            return

        if migration not in available_migrations:
            show_error_panel(
                    "Invalid Migration",
                    f"Migration '{migration}' is not available.\n"
                    f"Available migrations: {', '.join(available_migrations)}\n"
                    f"Use --list to see all available migrations."
            )
            raise typer.Exit(1)

        # Show migration information and get confirmation
        if not force:
            console.print()
            console.print(f"[bold yellow]⚠️  Repository Migration Warning[/bold yellow]")
            console.print()

            warning_info = [
                    f"Repository: {name}",
                    f"Migration: {migration}",
                    "",
                    "⚠️  IMPORTANT WARNINGS:",
                    "• This will upgrade the repository format",
                    "• Older restic versions may not be able to access the repository",
                    "• This operation cannot be easily undone",
                    "• Make sure you have a backup of your repository",
                    "",
                    "📋 Recommended steps after migration:",
                    "• Run 'prune' to compress repository metadata",
                    "• Test repository access with your restic version",
                    "• Update any scripts or tools that access this repository"
            ]

            warning_panel = Panel(
                    "\n".join(warning_info),
                    title="Migration Information",
                    border_style="yellow"
            )
            console.print(warning_panel)

            if not typer.confirm("\nDo you want to proceed with the migration?"):
                console.print("[yellow]Migration cancelled by user[/yellow]")
                raise typer.Exit(0)

        # Perform the migration
        console.print()
        console.print(f"[cyan]Migrating repository '[bold]{name}[/bold]' using migration '[bold]{migration}[/bold]'...[/cyan]")

        try:
            success = repository_service.migrate_repository(repo, migration)

            if not success:
                show_error_panel("Migration Failed", f"Failed to migrate repository '{name}'")
                raise typer.Exit(1)

            console.print(f"[bold green]✅ Repository migration completed successfully![/bold green]")

        except Exception as e:
            show_error_panel("Migration Failed", f"Failed to migrate repository: {e}")
            raise typer.Exit(1)

        # Run prune after migration if requested
        if prune_after:
            console.print()
            console.print("[cyan]Running prune to compress repository metadata...[/cyan]")

            try:
                prune_success = repository_service.prune_repository(repo)

                if prune_success:
                    console.print("[green]✅ Repository pruning completed successfully[/green]")
                else:
                    console.print("[yellow]⚠️  Repository pruning failed, but migration was successful[/yellow]")

            except Exception as e:
                console.print(f"[yellow]⚠️  Failed to prune repository: {e}[/yellow]")
                console.print("[dim]Migration was successful, but pruning failed[/dim]")

        # Show final summary
        console.print()

        summary_info = [
                f"✅ Migration '{migration}' completed successfully",
                f"📁 Repository: {name}",
                f"🔧 Migration applied: {migration}",
        ]

        if prune_after:
            summary_info.append("🗜️  Metadata compression: Completed")

        summary_info.extend([
                "",
                "📋 Next steps:",
                "• Test repository access with your restic version",
                "• Consider running 'prune --repack-uncompressed' to compress all data",
                "• Update any scripts or automation that access this repository"
        ])

        summary_panel = Panel(
                "\n".join(summary_info),
                title="Migration Summary",
                border_style="green"
        )
        console.print(summary_panel)

        # Verbose output
        if verbose:
            console.print()

            verbose_info = [
                    f"Repository location: {repo.location}",
                    f"Migration type: {migration}",
                    f"Integrity check: {'Performed' if check_first else 'Skipped'}",
                    f"Post-migration prune: {'Performed' if prune_after else 'Skipped'}",
                    f"Force mode: {'Enabled' if force else 'Disabled'}"
            ]

            verbose_panel = Panel(
                    "\n".join(verbose_info),
                    title="Migration Details",
                    border_style="blue"
            )
            console.print(verbose_panel)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Migration operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Migration Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_app.command("forget")
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


@repos_app.command("check-all")
def repos_check_all(
        parallel: Annotated[bool, typer.Option("--parallel", "-p", help="Check repositories in parallel")] = True,
        max_workers: Annotated[int, typer.Option("--max-workers", help="Maximum number of parallel workers")] = 4,
        continue_on_error: Annotated[bool, typer.Option("--continue-on-error", help="Continue checking other repositories if one fails")] = True,
        summary_only: Annotated[bool, typer.Option("--summary-only", help="Show only summary, not detailed results")] = False,
        filter_status: Annotated[str, typer.Option("--filter", help="Filter by status: all, failed, passed")] = "all",
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Check integrity of all configured repositories."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get all repositories
        try:
            repositories = service_manager.list_repositories()
        except Exception as e:
            show_error_panel("Repository List Error", f"Failed to list repositories: {e}")
            raise typer.Exit(1)

        if not repositories:
            console.print("[yellow]No repositories configured to check[/yellow]")
            return

        console.print(f"[cyan]Checking integrity of {len(repositories)} repositories...[/cyan]")
        console.print()

        # Get repository service
        repository_service = service_manager.get_repository_service()

        # Track results
        check_results = []
        failed_repos = []
        passed_repos = []

        if parallel and len(repositories) > 1:
            # Parallel checking
            import concurrent.futures
            import threading

            console.print(f"[dim]Using parallel checking with {min(max_workers, len(repositories))} workers[/dim]")
            console.print()

            # Create a lock for console output
            console_lock = threading.Lock()

            def check_single_repository(repo_config):
                """Check a single repository and return results"""
                repo_name = repo_config['name']
                repo_uri = repo_config.get('uri', repo_config.get('location', ''))

                try:
                    # Create repository instance
                    repo = service_manager.repository_factory.create_repository(repo_uri)

                    # Perform check
                    with console_lock:
                        console.print(f"[cyan]Checking repository '[bold]{repo_name}[/bold]'...[/cyan]")

                    check_result = repository_service.check_repository(repo)
                    check_result['repository_name'] = repo_name
                    check_result['repository_uri'] = repo_uri

                    with console_lock:
                        if check_result['status'] == 'success':
                            console.print(f"[green]✅ {repo_name}: Check passed[/green]")
                        else:
                            console.print(f"[red]❌ {repo_name}: Check failed[/red]")

                    return check_result

                except Exception as e:
                    error_result = {
                            'repository_name': repo_name,
                            'repository_uri':  repo_uri,
                            'status':          'error',
                            'errors':          [str(e)],
                            'warnings':        [],
                            'statistics':      {}
                    }

                    with console_lock:
                        console.print(f"[red]❌ {repo_name}: Error - {e}[/red]")

                    return error_result

            # Execute parallel checks
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(repositories))) as executor:
                future_to_repo = {executor.submit(check_single_repository, repo): repo for repo in repositories}

                for future in concurrent.futures.as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        result = future.result()
                        check_results.append(result)

                        if result['status'] == 'success':
                            passed_repos.append(result)
                        else:
                            failed_repos.append(result)

                    except Exception as e:
                        if continue_on_error:
                            console.print(f"[red]❌ {repo['name']}: Unexpected error - {e}[/red]")
                            failed_repos.append({
                                    'repository_name': repo['name'],
                                    'status':          'error',
                                    'errors':          [str(e)]
                            })
                        else:
                            show_error_panel("Repository Check Failed", f"Failed to check repository {repo['name']}: {e}")
                            raise typer.Exit(1)

        else:
            # Sequential checking
            console.print("[dim]Using sequential checking[/dim]")
            console.print()

            for repo_config in repositories:
                repo_name = repo_config['name']
                repo_uri = repo_config.get('uri', repo_config.get('location', ''))

                try:
                    console.print(f"[cyan]Checking repository '[bold]{repo_name}[/bold]'...[/cyan]")

                    # Create repository instance
                    repo = service_manager.repository_factory.create_repository(repo_uri)

                    # Perform check
                    check_result = repository_service.check_repository(repo)
                    check_result['repository_name'] = repo_name
                    check_result['repository_uri'] = repo_uri

                    check_results.append(check_result)

                    if check_result['status'] == 'success':
                        console.print(f"[green]✅ {repo_name}: Check passed[/green]")
                        passed_repos.append(check_result)
                    else:
                        console.print(f"[red]❌ {repo_name}: Check failed[/red]")
                        failed_repos.append(check_result)

                        if not continue_on_error:
                            show_error_panel("Repository Check Failed", f"Repository {repo_name} failed integrity check")
                            raise typer.Exit(1)

                    console.print()

                except Exception as e:
                    console.print(f"[red]❌ {repo_name}: Error - {e}[/red]")
                    console.print()

                    failed_repos.append({
                            'repository_name': repo_name,
                            'repository_uri':  repo_uri,
                            'status':          'error',
                            'errors':          [str(e)]
                    })

                    if not continue_on_error:
                        show_error_panel("Repository Check Failed", f"Failed to check repository {repo_name}: {e}")
                        raise typer.Exit(1)

        # Display results summary
        console.print()
        console.print("[bold]Repository Check Summary[/bold]")
        console.print()

        # Create summary table
        summary_table = Table(title="Check Results Summary")
        summary_table.add_column("Repository", style="cyan", no_wrap=True)
        summary_table.add_column("Status", style="white")
        summary_table.add_column("Issues", style="yellow")
        summary_table.add_column("Details", style="dim")

        # Filter results based on filter_status
        filtered_results = check_results
        if filter_status == "failed":
            filtered_results = failed_repos
        elif filter_status == "passed":
            filtered_results = passed_repos

        for result in filtered_results:
            repo_name = result['repository_name']
            status = result['status']

            # Status display
            if status == 'success':
                status_display = "[green]✅ Passed[/green]"
            elif status == 'failed':
                status_display = "[red]❌ Failed[/red]"
            else:
                status_display = "[yellow]⚠️  Error[/yellow]"

            # Issues count
            error_count = len(result.get('errors', []))
            warning_count = len(result.get('warnings', []))
            issues = f"{error_count} errors, {warning_count} warnings"

            # Details
            details = ""
            if not summary_only and result.get('errors'):
                details = result['errors'][0][:50] + "..." if len(result['errors'][0]) > 50 else result['errors'][0]

            summary_table.add_row(repo_name, status_display, issues, details)

        console.print(summary_table)

        # Overall statistics
        console.print()
        total_repos = len(repositories)
        passed_count = len(passed_repos)
        failed_count = len(failed_repos)

        stats_info = [
                f"Total repositories: {total_repos}",
                f"✅ Passed: {passed_count}",
                f"❌ Failed: {failed_count}",
                f"Success rate: {(passed_count / total_repos) * 100:.1f}%" if total_repos > 0 else "Success rate: 0%"
        ]

        if failed_count == 0:
            stats_panel = Panel(
                    "\n".join(stats_info),
                    title="✅ All Repositories Healthy",
                    border_style="green"
            )
        else:
            stats_panel = Panel(
                    "\n".join(stats_info),
                    title="⚠️  Some Repositories Have Issues",
                    border_style="yellow"
            )

        console.print(stats_panel)

        # Detailed error information if not summary only
        if not summary_only and failed_repos:
            console.print()
            console.print("[bold red]Failed Repository Details:[/bold red]")

            for failed_repo in failed_repos:
                console.print()

                error_info = [
                        f"Repository: {failed_repo['repository_name']}",
                        f"URI: {failed_repo.get('repository_uri', 'N/A')}",
                        f"Status: {failed_repo['status']}",
                ]

                if failed_repo.get('errors'):
                    error_info.append("")
                    error_info.append("Errors:")
                    for error in failed_repo['errors']:
                        error_info.append(f"  • {error}")

                if failed_repo.get('warnings'):
                    error_info.append("")
                    error_info.append("Warnings:")
                    for warning in failed_repo['warnings']:
                        error_info.append(f"  • {warning}")

                error_panel = Panel(
                        "\n".join(error_info),
                        title=f"❌ {failed_repo['repository_name']}",
                        border_style="red"
                )
                console.print(error_panel)

        # Verbose output
        if verbose and not summary_only:
            console.print()

            verbose_info = [
                    f"Check method: {'Parallel' if parallel and len(repositories) > 1 else 'Sequential'}",
                    f"Max workers: {max_workers}" if parallel else "Workers: 1",
                    f"Continue on error: {'Yes' if continue_on_error else 'No'}",
                    f"Filter applied: {filter_status}",
                    f"Total execution time: Available in performance logs"
            ]

            verbose_panel = Panel(
                    "\n".join(verbose_info),
                    title="Check Configuration",
                    border_style="blue"
            )
            console.print(verbose_panel)

        # Exit with appropriate code
        if failed_count > 0:
            raise typer.Exit(1)  # Some repositories failed
        else:
            raise typer.Exit(0)  # All repositories passed

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Repository check operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Repository Check Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@repos_app.command("stats-all")
def repos_stats_all(
        parallel: Annotated[bool, typer.Option("--parallel", "-p", help="Gather statistics in parallel")] = True,
        max_workers: Annotated[int, typer.Option("--max-workers", help="Maximum number of parallel workers")] = 4,
        continue_on_error: Annotated[bool, typer.Option("--continue-on-error", help="Continue gathering stats from other repositories if one fails")] = True,
        summary_only: Annotated[bool, typer.Option("--summary-only", help="Show only aggregated summary, not individual repository details")] = False,
        sort_by: Annotated[str, typer.Option("--sort-by", help="Sort repositories by: name, size, snapshots, age")] = "name",
        format_output: Annotated[str, typer.Option("--format", help="Output format: table, json, csv")] = "table",
        include_totals: Annotated[bool, typer.Option("--totals/--no-totals", help="Include aggregate totals across all repositories")] = True,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show comprehensive statistics for all configured repositories."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get all repositories
        try:
            repositories = service_manager.list_repositories()
        except Exception as e:
            show_error_panel("Repository List Error", f"Failed to list repositories: {e}")
            raise typer.Exit(1)

        if not repositories:
            console.print("[yellow]No repositories configured to analyze[/yellow]")
            return

        console.print(f"[cyan]Gathering statistics from {len(repositories)} repositories...[/cyan]")
        console.print()

        # Get repository service
        repository_service = service_manager.get_repository_service()

        # Track results
        stats_results = []
        failed_repos = []
        successful_repos = []

        if parallel and len(repositories) > 1:
            # Parallel statistics gathering
            import concurrent.futures
            import threading

            console.print(f"[dim]Using parallel processing with {min(max_workers, len(repositories))} workers[/dim]")
            console.print()

            # Create a lock for console output
            console_lock = threading.Lock()

            def get_single_repository_stats(repo_config):
                """Get statistics for a single repository and return results"""
                repo_name = repo_config['name']
                repo_uri = repo_config.get('uri', repo_config.get('location', ''))

                try:
                    # Create repository instance
                    repo = service_manager.repository_factory.create_repository(repo_uri)

                    # Gather statistics
                    with console_lock:
                        console.print(f"[cyan]Analyzing repository '[bold]{repo_name}[/bold]'...[/cyan]")

                    stats = repository_service.get_repository_stats(repo)
                    stats['repository_name'] = repo_name
                    stats['repository_uri'] = repo_uri
                    stats['status'] = 'success'

                    with console_lock:
                        console.print(f"[green]✅ {repo_name}: Statistics gathered[/green]")

                    return stats

                except Exception as e:
                    error_result = {
                            'repository_name': repo_name,
                            'repository_uri':  repo_uri,
                            'status':          'error',
                            'error':           str(e),
                            'total_size':      0,
                            'snapshots_count': 0
                    }

                    with console_lock:
                        console.print(f"[red]❌ {repo_name}: Error - {e}[/red]")

                    return error_result

            # Execute parallel statistics gathering
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(repositories))) as executor:
                future_to_repo = {executor.submit(get_single_repository_stats, repo): repo for repo in repositories}

                for future in concurrent.futures.as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        result = future.result()
                        stats_results.append(result)

                        if result['status'] == 'success':
                            successful_repos.append(result)
                        else:
                            failed_repos.append(result)

                    except Exception as e:
                        if continue_on_error:
                            console.print(f"[red]❌ {repo['name']}: Unexpected error - {e}[/red]")
                            failed_repos.append({
                                    'repository_name': repo['name'],
                                    'status':          'error',
                                    'error':           str(e),
                                    'total_size':      0,
                                    'snapshots_count': 0
                            })
                        else:
                            show_error_panel("Repository Stats Failed", f"Failed to get statistics for repository {repo['name']}: {e}")
                            raise typer.Exit(1)

        else:
            # Sequential statistics gathering
            console.print("[dim]Using sequential processing[/dim]")
            console.print()

            for repo_config in repositories:
                repo_name = repo_config['name']
                repo_uri = repo_config.get('uri', repo_config.get('location', ''))

                try:
                    console.print(f"[cyan]Analyzing repository '[bold]{repo_name}[/bold]'...[/cyan]")

                    # Create repository instance
                    repo = service_manager.repository_factory.create_repository(repo_uri)

                    # Gather statistics
                    stats = repository_service.get_repository_stats(repo)
                    stats['repository_name'] = repo_name
                    stats['repository_uri'] = repo_uri
                    stats['status'] = 'success'

                    stats_results.append(stats)
                    successful_repos.append(stats)

                    console.print(f"[green]✅ {repo_name}: Statistics gathered[/green]")
                    console.print()

                except Exception as e:
                    console.print(f"[red]❌ {repo_name}: Error - {e}[/red]")
                    console.print()

                    error_result = {
                            'repository_name': repo_name,
                            'repository_uri':  repo_uri,
                            'status':          'error',
                            'error':           str(e),
                            'total_size':      0,
                            'snapshots_count': 0
                    }

                    stats_results.append(error_result)
                    failed_repos.append(error_result)

                    if not continue_on_error:
                        show_error_panel("Repository Stats Failed", f"Failed to get statistics for repository {repo_name}: {e}")
                        raise typer.Exit(1)

        # Sort results
        if sort_by == "size":
            stats_results.sort(key=lambda x: x.get('total_size', 0), reverse=True)
        elif sort_by == "snapshots":
            stats_results.sort(key=lambda x: x.get('snapshots_count', 0), reverse=True)
        elif sort_by == "age":
            stats_results.sort(key=lambda x: x.get('oldest_snapshot', 0))
        else:  # sort by name (default)
            stats_results.sort(key=lambda x: x.get('repository_name', ''))

        # Display results
        console.print()
        console.print("[bold]Repository Statistics Summary[/bold]")
        console.print()

        if format_output == "json":
            # JSON output
            import json
            output_data = {
                    'repositories': stats_results,
                    'summary':      {
                            'total_repositories': len(repositories),
                            'successful':         len(successful_repos),
                            'failed':             len(failed_repos)
                    }
            }
            console.print(json.dumps(output_data, indent=2))

        elif format_output == "csv":
            # CSV output
            console.print("Repository,Status,Total Size (bytes),Snapshots,Files,Oldest Snapshot,Newest Snapshot,Error")
            for result in stats_results:
                repo_name = result.get('repository_name', 'Unknown')
                status = result.get('status', 'unknown')
                total_size = result.get('total_size', 0)
                snapshots = result.get('snapshots_count', 0)
                files = result.get('total_file_count', 0)
                oldest = result.get('oldest_snapshot', '')
                newest = result.get('newest_snapshot', '')
                error = result.get('error', '')

                console.print(f"{repo_name},{status},{total_size},{snapshots},{files},{oldest},{newest},{error}")

        else:
            # Table output (default)
            if not summary_only:
                # Individual repository details
                stats_table = Table(title="Repository Statistics")
                stats_table.add_column("Repository", style="cyan", no_wrap=True)
                stats_table.add_column("Status", style="white")
                stats_table.add_column("Size", style="green", justify="right")
                stats_table.add_column("Snapshots", style="blue", justify="right")
                stats_table.add_column("Files", style="yellow", justify="right")
                stats_table.add_column("Age (days)", style="magenta", justify="right")
                stats_table.add_column("Details", style="dim")

                def format_bytes(bytes_value):
                    """Format bytes in human readable format"""
                    if bytes_value == 0:
                        return "0 B"

                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if bytes_value < 1024.0:
                            return f"{bytes_value:.1f} {unit}"
                        bytes_value /= 1024.0
                    return f"{bytes_value:.1f} PB"

                for result in stats_results:
                    repo_name = result.get('repository_name', 'Unknown')
                    status = result.get('status', 'unknown')

                    # Status display
                    if status == 'success':
                        status_display = "[green]✅ Success[/green]"
                    else:
                        status_display = "[red]❌ Error[/red]"

                    # Size formatting
                    total_size = result.get('total_size', 0)
                    size_display = format_bytes(total_size)

                    # Snapshot count
                    snapshots_count = result.get('snapshots_count', 0)

                    # File count
                    file_count = result.get('total_file_count', 0)

                    # Age calculation
                    age_display = "N/A"
                    if result.get('time_span_days'):
                        age_display = f"{result['time_span_days']:.1f}"

                    # Details
                    details = ""
                    if status == 'error':
                        error_msg = result.get('error', 'Unknown error')
                        details = error_msg[:40] + "..." if len(error_msg) > 40 else error_msg
                    elif result.get('compression_ratio'):
                        details = f"Compression: {result['compression_ratio']:.1%}"

                    stats_table.add_row(
                            repo_name, status_display, size_display,
                            str(snapshots_count), str(file_count), age_display, details
                    )

                console.print(stats_table)

            # Aggregate totals
            if include_totals and successful_repos:
                console.print()

                total_size = sum(repo.get('total_size', 0) for repo in successful_repos)
                total_snapshots = sum(repo.get('snapshots_count', 0) for repo in successful_repos)
                total_files = sum(repo.get('total_file_count', 0) for repo in successful_repos)

                def format_bytes(bytes_value):
                    """Format bytes in human readable format"""
                    if bytes_value == 0:
                        return "0 B"

                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if bytes_value < 1024.0:
                            return f"{bytes_value:.1f} {unit}"
                        bytes_value /= 1024.0
                    return f"{bytes_value:.1f} PB"

                totals_info = [
                        f"Total repositories analyzed: {len(repositories)}",
                        f"✅ Successful: {len(successful_repos)}",
                        f"❌ Failed: {len(failed_repos)}",
                        "",
                        f"Combined storage used: {format_bytes(total_size)}",
                        f"Total snapshots: {total_snapshots:,}",
                        f"Total files backed up: {total_files:,}",
                ]

                # Calculate average repository size
                if successful_repos:
                    avg_size = total_size / len(successful_repos)
                    totals_info.append(f"Average repository size: {format_bytes(avg_size)}")

                totals_panel = Panel(
                        "\n".join(totals_info),
                        title="📊 Aggregate Statistics",
                        border_style="blue"
                )
                console.print(totals_panel)

        # Error details if any failures occurred
        if failed_repos and not summary_only and format_output == "table":
            console.print()
            console.print("[bold red]Failed Repository Details:[/bold red]")

            for failed_repo in failed_repos:
                console.print()

                error_info = [
                        f"Repository: {failed_repo['repository_name']}",
                        f"URI: {failed_repo.get('repository_uri', 'N/A')}",
                        f"Error: {failed_repo.get('error', 'Unknown error')}",
                ]

                error_panel = Panel(
                        "\n".join(error_info),
                        title=f"❌ {failed_repo['repository_name']}",
                        border_style="red"
                )
                console.print(error_panel)

        # Verbose output
        if verbose and format_output == "table":
            console.print()

            verbose_info = [
                    f"Processing method: {'Parallel' if parallel and len(repositories) > 1 else 'Sequential'}",
                    f"Max workers: {max_workers}" if parallel else "Workers: 1",
                    f"Continue on error: {'Yes' if continue_on_error else 'No'}",
                    f"Sort order: {sort_by}",
                    f"Output format: {format_output}",
                    f"Include totals: {'Yes' if include_totals else 'No'}",
                    f"Total execution time: Available in performance logs"
            ]

            verbose_panel = Panel(
                    "\n".join(verbose_info),
                    title="Statistics Configuration",
                    border_style="blue"
            )
            console.print(verbose_panel)

        # Exit with appropriate code
        if failed_repos:
            raise typer.Exit(1)  # Some repositories failed
        else:
            raise typer.Exit(0)  # All repositories processed successfully

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Repository statistics operation was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Repository Stats Error", f"An unexpected error occurred: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# ============================================================================
# CONFIG COMMANDS (Configuration management)
# ============================================================================

# Config repositories commands (already moved above)

@repos_app.command("show")
def repos_show(
        name: Annotated[str, typer.Argument(help="Repository name", autocompletion=repository_name_completer)],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show repository config details."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get repository configuration
        try:
            repo_config = service_manager.get_repository_by_name(name)
        except Exception as e:
            show_error_panel("Repository Not Found", f"Repository '{name}' not found: {e}")
            raise typer.Exit(1)

        # Create detailed information table
        table = Table(title=f"Repository Configuration: {name}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Basic information
        table.add_row("Name", repo_config.get('name', 'N/A'))

        # Location/URI (handle both modern 'uri' and legacy 'location' fields)
        location = repo_config.get('uri', repo_config.get('location', 'N/A'))
        table.add_row("Location/URI", location)

        # Repository type
        repo_type = repo_config.get('type', 'auto')
        table.add_row("Type", repo_type)

        # Description
        description = repo_config.get('description', 'No description')
        table.add_row("Description", description)

        # Status information
        enabled = repo_config.get('enabled', True)
        table.add_row("Enabled", "✅ Yes" if enabled else "❌ No")

        read_only = repo_config.get('read_only', False)
        table.add_row("Read Only", "🔒 Yes" if read_only else "✏️  No")

        # Security information
        has_password = bool(repo_config.get('password') or repo_config.get('password_file') or repo_config.get('password_command'))
        table.add_row("Password Configured", "🔐 Yes" if has_password else "⚠️  No")

        # Advanced settings
        if repo_config.get('cache_dir'):
            table.add_row("Cache Directory", repo_config['cache_dir'])

        if repo_config.get('compression'):
            table.add_row("Compression", repo_config['compression'])

        if repo_config.get('pack_size'):
            table.add_row("Pack Size", f"{repo_config['pack_size']} MB")

        # Tags
        tags = repo_config.get('tags', [])
        if tags:
            table.add_row("Tags", ", ".join(tags))

        # Creation info
        if repo_config.get('created'):
            table.add_row("Created", repo_config['created'])

        console.print()
        console.print(table)

        # Show additional details if verbose
        if verbose:
            console.print()

            # Password configuration details
            password_panel_content = []
            if repo_config.get('password'):
                password_panel_content.append("🔑 Direct password: Configured")
            if repo_config.get('password_file'):
                password_panel_content.append(f"📄 Password file: {repo_config['password_file']}")
            if repo_config.get('password_command'):
                password_panel_content.append(f"⚙️  Password command: {repo_config['password_command']}")

            if password_panel_content:
                password_panel = Panel(
                        "\n".join(password_panel_content),
                        title="Password Configuration",
                        border_style="blue"
                )
                console.print(password_panel)

            # Raw configuration (for debugging)
            console.print()
            raw_config_text = json.dumps(repo_config, indent=2, default=str)
            raw_panel = Panel(
                    raw_config_text,
                    title="Raw Configuration (Debug)",
                    border_style="dim"
            )
            console.print(raw_panel)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Repository configuration display was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to show repository configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


# Config target commands (single target operations)

@targets_app.command("list")
def targets_list(
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
            console.print("💡 Use [bold]tl targets add[/bold] to create a backup target")
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
        table.add_column("Status", style="white", no_wrap=True)

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

            # Validate target and determine status
            from TimeLocker.services.validation_service import validation_service
            target_with_name = {**target, 'name': name}
            validation_result = validation_service.validate_backup_target_config(target_with_name, strict_path_validation=False)

            if validation_result.has_errors():
                status = "❌ Error"
            elif validation_result.has_warnings():
                status = "⚠️  Warning"
            else:
                status = "✅ OK"

            table.add_row(
                    name,
                    target.get("description", "No description"),
                    paths_str,
                    patterns_str,
                    status
            )

        console.print()
        console.print(table)
        console.print()

    except Exception as e:
        show_error_panel("List Targets Error", f"Failed to list backup targets: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("show")
def targets_show(
        name: Annotated[str, typer.Argument(help="Target name")],
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show target details."""
    setup_logging(verbose)

    try:
        service_manager = get_cli_service_manager()

        # Get backup target configuration
        try:
            target_config = service_manager.get_backup_target_by_name(name)
        except Exception as e:
            show_error_panel("Target Not Found", f"Backup target '{name}' not found: {e}")
            raise typer.Exit(1)

        # Create detailed information table
        table = Table(title=f"Backup Target Configuration: {name}")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        # Basic information
        table.add_row("Name", target_config.get('name', 'N/A'))

        # Description
        description = target_config.get('description', 'No description')
        table.add_row("Description", description)

        # Paths
        paths = target_config.get('paths', [])
        if paths:
            paths_text = "\n".join(f"• {path}" for path in paths)
            table.add_row("Backup Paths", paths_text)
        else:
            table.add_row("Backup Paths", "⚠️  No paths configured")

        # Repository
        repository = target_config.get('repository', 'Not specified')
        table.add_row("Repository", repository)

        # Status
        enabled = target_config.get('enabled', True)
        table.add_row("Enabled", "✅ Yes" if enabled else "❌ No")

        # Include patterns
        include_patterns = target_config.get('include_patterns', [])
        if include_patterns:
            patterns_text = "\n".join(f"• {pattern}" for pattern in include_patterns)
            table.add_row("Include Patterns", patterns_text)

        # Exclude patterns
        exclude_patterns = target_config.get('exclude_patterns', [])
        if exclude_patterns:
            patterns_text = "\n".join(f"• {pattern}" for pattern in exclude_patterns)
            table.add_row("Exclude Patterns", patterns_text)

        # Exclude files
        exclude_files = target_config.get('exclude_files', [])
        if exclude_files:
            files_text = "\n".join(f"• {file}" for file in exclude_files)
            table.add_row("Exclude Files", files_text)

        # Tags
        tags = target_config.get('tags', [])
        if tags:
            table.add_row("Tags", ", ".join(tags))

        # Schedule
        schedule = target_config.get('schedule')
        if schedule:
            table.add_row("Schedule", f"📅 {schedule}")

        # Retention policy
        retention_policy = target_config.get('retention_policy')
        if retention_policy:
            retention_text = []
            for key, value in retention_policy.items():
                retention_text.append(f"{key}: {value}")
            table.add_row("Retention Policy", "\n".join(retention_text))

        # Scripts
        pre_script = target_config.get('pre_backup_script')
        if pre_script:
            table.add_row("Pre-backup Script", f"🔧 {pre_script}")

        post_script = target_config.get('post_backup_script')
        if post_script:
            table.add_row("Post-backup Script", f"🔧 {post_script}")

        console.print()
        console.print(table)

        # Validate target configuration and show warnings/errors
        from TimeLocker.services.validation_service import validation_service
        target_with_name = {**target_config, 'name': name}
        validation_result = validation_service.validate_backup_target_config(target_with_name, strict_path_validation=True)

        if validation_result.has_errors():
            console.print()
            error_panel = Panel(
                    "\n".join(f"❌ {error}" for error in validation_result.errors),
                    title="[bold red]Configuration Errors[/bold red]",
                    border_style="red"
            )
            console.print(error_panel)

        if validation_result.has_warnings():
            console.print()
            warning_panel = Panel(
                    "\n".join(f"⚠️  {warning}" for warning in validation_result.warnings),
                    title="[bold yellow]Configuration Warnings[/bold yellow]",
                    border_style="yellow"
            )
            console.print(warning_panel)

        # Show additional details if verbose
        if verbose:
            console.print()

            # Path analysis
            if paths:
                path_panel_content = []
                for path in paths:
                    path_obj = Path(path)
                    if path_obj.exists():
                        if path_obj.is_dir():
                            path_panel_content.append(f"📁 {path} (directory exists)")
                        else:
                            path_panel_content.append(f"📄 {path} (file exists)")
                    else:
                        path_panel_content.append(f"❌ {path} (does not exist)")

                if path_panel_content:
                    path_panel = Panel(
                            "\n".join(path_panel_content),
                            title="Path Analysis",
                            border_style="blue"
                    )
                    console.print(path_panel)

            # Pattern validation
            pattern_issues = []
            for pattern in include_patterns + exclude_patterns:
                try:
                    # Basic pattern validation
                    import re
                    re.compile(pattern)
                except re.error as e:
                    pattern_issues.append(f"❌ Invalid pattern '{pattern}': {e}")

            if pattern_issues:
                pattern_panel = Panel(
                        "\n".join(pattern_issues),
                        title="Pattern Validation Issues",
                        border_style="red"
                )
                console.print(pattern_panel)

            # Raw configuration (for debugging)
            console.print()
            raw_config_text = json.dumps(target_config, indent=2, default=str)
            raw_panel = Panel(
                    raw_config_text,
                    title="Raw Configuration (Debug)",
                    border_style="dim"
            )
            console.print(raw_panel)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Target configuration display was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to show target configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("edit")
def targets_edit(
        name: Annotated[str, typer.Argument(help="Target name")],
        description: Annotated[str, typer.Option("--description", help="New description for the target")] = None,
        repository: Annotated[str, typer.Option("--repository", help="New repository for the target")] = None,
        add_paths: Annotated[List[str], typer.Option("--add-path", help="Add backup paths (can be used multiple times)")] = None,
        remove_paths: Annotated[List[str], typer.Option("--remove-path", help="Remove backup paths (can be used multiple times)")] = None,
        add_excludes: Annotated[List[str], typer.Option("--add-exclude", help="Add exclude patterns (can be used multiple times)")] = None,
        remove_excludes: Annotated[List[str], typer.Option("--remove-exclude", help="Remove exclude patterns (can be used multiple times)")] = None,
        add_includes: Annotated[List[str], typer.Option("--add-include", help="Add include patterns (can be used multiple times)")] = None,
        remove_includes: Annotated[List[str], typer.Option("--remove-include", help="Remove include patterns (can be used multiple times)")] = None,
        interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Interactive editing mode")] = False,
        config_dir: Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Edit backup target configuration.

    You can edit target configuration in two ways:
    1. Use command-line options to make specific changes
    2. Use --interactive mode for guided editing

    Examples:
        # Change description
        tl targets edit myTarget --description "New description"

        # Add backup paths
        tl targets edit myTarget --add-path /home/user/docs --add-path /home/user/photos

        # Change repository
        tl targets edit myTarget --repository newRepo

        # Interactive editing
        tl targets edit myTarget --interactive
    """
    setup_logging(verbose)

    try:
        from .config.configuration_module import ConfigurationModule
        config_manager = ConfigurationModule(config_dir=config_dir)

        # Get current target configuration
        try:
            target_config_obj = config_manager.get_backup_target(name)
            target_config = target_config_obj.to_dict()
        except Exception as e:
            show_error_panel("Target Not Found", f"Backup target '{name}' not found: {e}")
            raise typer.Exit(1)

        console.print(f"[cyan]Editing backup target '[bold]{name}[/bold]'[/cyan]")
        console.print()

        # Store original configuration for comparison
        original_config = target_config.copy()
        modified_config = target_config.copy()
        changes_made = []

        if interactive:
            # Interactive editing mode
            console.print("[bold]Interactive Target Configuration Editor[/bold]")
            console.print()

            # Show current configuration
            current_table = Table(title="Current Configuration")
            current_table.add_column("Field", style="cyan")
            current_table.add_column("Current Value", style="white")

            current_table.add_row("Description", target_config.get('description', 'N/A'))
            current_table.add_row("Repository", target_config.get('repository', 'N/A'))
            current_table.add_row("Paths", ', '.join(target_config.get('paths', [])))

            excludes = target_config.get('exclude_patterns', [])
            includes = target_config.get('include_patterns', [])
            current_table.add_row("Exclude Patterns", ', '.join(excludes) if excludes else 'None')
            current_table.add_row("Include Patterns", ', '.join(includes) if includes else 'None')

            console.print(current_table)
            console.print()

            # Interactive field editing
            if Confirm.ask("Edit description?"):
                new_description = Prompt.ask("New description", default=target_config.get('description', ''))
                if new_description != target_config.get('description'):
                    modified_config['description'] = new_description
                    changes_made.append(f"Description: '{target_config.get('description', 'N/A')}' → '{new_description}'")

            if Confirm.ask("Edit repository?"):
                # Get available repositories
                try:
                    repositories = config_manager.list_repositories()
                    repo_names = [repo['name'] for repo in repositories]

                    if repo_names:
                        console.print(f"Available repositories: {', '.join(repo_names)}")

                    new_repository = Prompt.ask("New repository", default=target_config.get('repository', ''))
                    if new_repository != target_config.get('repository'):
                        modified_config['repository'] = new_repository
                        changes_made.append(f"Repository: '{target_config.get('repository', 'N/A')}' → '{new_repository}'")
                except Exception:
                    new_repository = Prompt.ask("New repository", default=target_config.get('repository', ''))
                    if new_repository != target_config.get('repository'):
                        modified_config['repository'] = new_repository
                        changes_made.append(f"Repository: '{target_config.get('repository', 'N/A')}' → '{new_repository}'")

            if Confirm.ask("Edit backup paths?"):
                current_paths = target_config.get('paths', [])
                console.print(f"Current paths: {', '.join(current_paths) if current_paths else 'None'}")

                # Add paths
                while Confirm.ask("Add a backup path?"):
                    new_path = Prompt.ask("Path to add")
                    if new_path:
                        if 'paths' not in modified_config:
                            modified_config['paths'] = current_paths.copy()
                        if new_path not in modified_config['paths']:
                            modified_config['paths'].append(new_path)
                            changes_made.append(f"Added path: '{new_path}'")
                        else:
                            console.print(f"[yellow]Path '{new_path}' already exists[/yellow]")

                # Remove paths
                if current_paths and Confirm.ask("Remove any backup paths?"):
                    for path in current_paths:
                        if Confirm.ask(f"Remove path '{path}'?"):
                            if 'paths' not in modified_config:
                                modified_config['paths'] = current_paths.copy()
                            if path in modified_config['paths']:
                                modified_config['paths'].remove(path)
                                changes_made.append(f"Removed path: '{path}'")

            if Confirm.ask("Edit exclude patterns?"):
                current_excludes = target_config.get('exclude_patterns', [])
                console.print(f"Current exclude patterns: {', '.join(current_excludes) if current_excludes else 'None'}")

                # Add excludes
                while Confirm.ask("Add an exclude pattern?"):
                    new_exclude = Prompt.ask("Exclude pattern to add")
                    if new_exclude:
                        if 'exclude_patterns' not in modified_config:
                            modified_config['exclude_patterns'] = current_excludes.copy()
                        if new_exclude not in modified_config['exclude_patterns']:
                            modified_config['exclude_patterns'].append(new_exclude)
                            changes_made.append(f"Added exclude pattern: '{new_exclude}'")
                        else:
                            console.print(f"[yellow]Exclude pattern '{new_exclude}' already exists[/yellow]")

                # Remove excludes
                if current_excludes and Confirm.ask("Remove any exclude patterns?"):
                    for exclude in current_excludes:
                        if Confirm.ask(f"Remove exclude pattern '{exclude}'?"):
                            if 'exclude_patterns' not in modified_config:
                                modified_config['exclude_patterns'] = current_excludes.copy()
                            if exclude in modified_config['exclude_patterns']:
                                modified_config['exclude_patterns'].remove(exclude)
                                changes_made.append(f"Removed exclude pattern: '{exclude}'")

            if Confirm.ask("Edit include patterns?"):
                current_includes = target_config.get('include_patterns', [])
                console.print(f"Current include patterns: {', '.join(current_includes) if current_includes else 'None'}")

                # Add includes
                while Confirm.ask("Add an include pattern?"):
                    new_include = Prompt.ask("Include pattern to add")
                    if new_include:
                        if 'include_patterns' not in modified_config:
                            modified_config['include_patterns'] = current_includes.copy()
                        if new_include not in modified_config['include_patterns']:
                            modified_config['include_patterns'].append(new_include)
                            changes_made.append(f"Added include pattern: '{new_include}'")
                        else:
                            console.print(f"[yellow]Include pattern '{new_include}' already exists[/yellow]")

                # Remove includes
                if current_includes and Confirm.ask("Remove any include patterns?"):
                    for include in current_includes:
                        if Confirm.ask(f"Remove include pattern '{include}'?"):
                            if 'include_patterns' not in modified_config:
                                modified_config['include_patterns'] = current_includes.copy()
                            if include in modified_config['include_patterns']:
                                modified_config['include_patterns'].remove(include)
                                changes_made.append(f"Removed include pattern: '{include}'")

        else:
            # Command-line option editing mode
            if description is not None:
                modified_config['description'] = description
                changes_made.append(f"Description: '{target_config.get('description', 'N/A')}' → '{description}'")

            if repository is not None:
                modified_config['repository'] = repository
                changes_made.append(f"Repository: '{target_config.get('repository', 'N/A')}' → '{repository}'")

            # Handle path modifications
            current_paths = target_config.get('paths', []).copy()

            if add_paths:
                for path in add_paths:
                    if path not in current_paths:
                        current_paths.append(path)
                        changes_made.append(f"Added path: '{path}'")
                    else:
                        console.print(f"[yellow]Path '{path}' already exists, skipping[/yellow]")
                modified_config['paths'] = current_paths

            if remove_paths:
                for path in remove_paths:
                    if path in current_paths:
                        current_paths.remove(path)
                        changes_made.append(f"Removed path: '{path}'")
                    else:
                        console.print(f"[yellow]Path '{path}' not found, skipping[/yellow]")
                modified_config['paths'] = current_paths

            # Handle pattern modifications
            if add_excludes or remove_excludes or add_includes or remove_includes:
                # Handle excludes
                current_excludes = modified_config.get('exclude_patterns', []).copy()

                if add_excludes:
                    for exclude in add_excludes:
                        if exclude not in current_excludes:
                            current_excludes.append(exclude)
                            changes_made.append(f"Added exclude pattern: '{exclude}'")
                        else:
                            console.print(f"[yellow]Exclude pattern '{exclude}' already exists, skipping[/yellow]")
                    modified_config['exclude_patterns'] = current_excludes

                if remove_excludes:
                    for exclude in remove_excludes:
                        if exclude in current_excludes:
                            current_excludes.remove(exclude)
                            changes_made.append(f"Removed exclude pattern: '{exclude}'")
                        else:
                            console.print(f"[yellow]Exclude pattern '{exclude}' not found, skipping[/yellow]")
                    modified_config['exclude_patterns'] = current_excludes

                # Handle includes
                current_includes = modified_config.get('include_patterns', []).copy()

                if add_includes:
                    for include in add_includes:
                        if include not in current_includes:
                            current_includes.append(include)
                            changes_made.append(f"Added include pattern: '{include}'")
                        else:
                            console.print(f"[yellow]Include pattern '{include}' already exists, skipping[/yellow]")
                    modified_config['include_patterns'] = current_includes

                if remove_includes:
                    for include in remove_includes:
                        if include in current_includes:
                            current_includes.remove(include)
                            changes_made.append(f"Removed include pattern: '{include}'")
                        else:
                            console.print(f"[yellow]Include pattern '{include}' not found, skipping[/yellow]")
                    modified_config['include_patterns'] = current_includes

        # Check if any changes were made
        if not changes_made:
            console.print("[yellow]No changes were made to the target configuration[/yellow]")
            return

        # Display changes summary
        console.print()
        console.print("[bold]Summary of Changes:[/bold]")
        changes_table = Table()
        changes_table.add_column("Change", style="cyan")

        for change in changes_made:
            changes_table.add_row(change)

        console.print(changes_table)
        console.print()

        # Validate the modified configuration
        validation_errors = []

        # Check paths exist
        if 'paths' in modified_config:
            for path in modified_config['paths']:
                if not Path(path).exists():
                    validation_errors.append(f"Path does not exist: {path}")

        # Check repository exists
        if 'repository' in modified_config:
            try:
                repositories = config_manager.list_repositories()
                repo_names = [repo['name'] for repo in repositories]
                if modified_config['repository'] not in repo_names:
                    validation_errors.append(f"Repository '{modified_config['repository']}' not found in configuration")
            except Exception:
                pass  # Skip repository validation if we can't list repositories

        if validation_errors:
            console.print()
            console.print("[bold red]Validation Warnings:[/bold red]")
            for error in validation_errors:
                console.print(f"[yellow]⚠️  {error}[/yellow]")
            console.print()

            if not yes and not Confirm.ask("Continue with these warnings?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Confirm changes
        if not yes:
            if not Confirm.ask(f"Apply these changes to target '{name}'?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Apply changes
        try:
            config_manager.update_backup_target(name, modified_config)
            console.print(f"[green]✅ Target '{name}' updated successfully[/green]")

            # Show updated configuration summary
            console.print()
            updated_table = Table(title="Updated Configuration")
            updated_table.add_column("Field", style="cyan")
            updated_table.add_column("Value", style="white")

            updated_table.add_row("Description", modified_config.get('description', 'N/A'))
            updated_table.add_row("Repository", modified_config.get('repository', 'N/A'))
            updated_table.add_row("Paths", ', '.join(modified_config.get('paths', [])))

            excludes = modified_config.get('exclude_patterns', [])
            includes = modified_config.get('include_patterns', [])
            updated_table.add_row("Exclude Patterns", ', '.join(excludes) if excludes else 'None')
            updated_table.add_row("Include Patterns", ', '.join(includes) if includes else 'None')

            console.print(updated_table)

        except Exception as e:
            show_error_panel("Update Failed", f"Failed to update target configuration: {e}")
            raise typer.Exit(1)

    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Target editing was cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Target Edit Error", f"Failed to edit target configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("remove")
def targets_remove(
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
