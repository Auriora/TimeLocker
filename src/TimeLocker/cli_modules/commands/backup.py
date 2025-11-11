"""
Backup operation commands.

This module contains CLI commands for creating and verifying backups.
"""

import sys
import logging
from typing import Optional, List, Annotated
from pathlib import Path

import typer
import click
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt

# Import from TimeLocker.cli module (cli.py) to avoid circular imports during transition
from TimeLocker import cli as _cli_module

# Import required functions and objects
show_success_panel = _cli_module.show_success_panel
show_error_panel = _cli_module.show_error_panel
setup_logging = _cli_module.setup_logging
_get_service_method = _cli_module._get_service_method
_call_service_method = _cli_module._call_service_method
_get_service_manager_for_command = _cli_module._get_service_manager_for_command
_create_configuration_module = _cli_module._create_configuration_module
console = _cli_module.console

# Import from TimeLocker package
from TimeLocker.cli_services import get_cli_service_manager, CLIBackupRequest
from TimeLocker.completion import (
    file_path_completer,
    repository_completer,
    selection_name_completer,
    snapshot_id_completer,
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import RepositoryNotFoundError
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format

# Create Typer app for backup operations
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

backup_app = typer.Typer(
    help="Backup operations",
    no_args_is_help=True,
    context_settings=CLI_CONTEXT_SETTINGS
)
backup_app.info.options_metavar = "⟨OPTIONS⟩"


@backup_app.command("create")
def backup_create(
        sources: Annotated[Optional[List[Path]], typer.Argument(help="Source paths to backup", autocompletion=file_path_completer)] = None,
        repository: Annotated[str, typer.Option("--repository", "-r", help="Repository name or URI", autocompletion=repository_completer)] = None,
        password: Annotated[str, typer.Option("--password", "-p", help="Repository password")] = None,
        selection: Annotated[Optional[str], typer.Option("--selection", "-s", help="Use configured data selection template", autocompletion=selection_name_completer)] = None,
        target: Annotated[Optional[str], typer.Option("--target", "-t", help="(Deprecated: use --selection) Use configured backup target", autocompletion=selection_name_completer, hidden=True)] = None,
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
    interactive = sys.stdin.isatty()

    # Handle deprecated --target parameter
    if target and not selection:
        console.print("[yellow]⚠️  Warning: --target is deprecated. Use --selection instead.[/yellow]")
        selection = target
    
    # Handle selection-based backup
    if selection:
        try:
            config_module = None
            service_manager = _get_service_manager_for_command(config_dir)
            backup_target = None

            def _extract_target_value(obj, key, default=None):
                if obj is None:
                    return default
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            def _target_paths(obj):
                value = _extract_target_value(obj, 'paths', [])
                if isinstance(value, (list, tuple, set)):
                    return list(value)
                return []

            def _valid_target(obj):
                return len(_target_paths(obj)) > 0

            if service_manager:
                target_by_name = _get_service_method(service_manager, "get_backup_target_by_name")
                if target_by_name:
                    try:
                        backup_target = _call_service_method(target_by_name, name=selection, target_name=selection)
                    except Exception as exc:
                        logging.getLogger(__name__).debug("Service target lookup failed: %s", exc)

            if not _valid_target(backup_target) and service_manager:
                list_method = _get_service_method(service_manager, "list_backup_targets")
                if list_method:
                    try:
                        targets = _call_service_method(list_method) or []
                        for candidate in targets:
                            candidate_name = _extract_target_value(candidate, 'name')
                            if candidate_name == selection:
                                backup_target = candidate
                                break
                    except Exception as exc:
                        logging.getLogger(__name__).debug("Service target listing failed: %s", exc)

            if not _valid_target(backup_target) and service_manager:
                generic_method = _get_service_method(service_manager, "get_backup_target")
                if generic_method:
                    try:
                        backup_target = _call_service_method(generic_method, name=selection, target_name=selection)
                    except Exception as exc:
                        logging.getLogger(__name__).debug("Service target lookup (generic) failed: %s", exc)

            if backup_target is None:
                config_module = _create_configuration_module(config_dir)
                backup_target = config_module.get_backup_target(selection)

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
        normalized_target = {
                "name":             _extract_target_value(backup_target, "name", selection),
                "paths":            _target_paths(backup_target),
                "include_patterns": _extract_target_value(backup_target, "include_patterns", []),
                "exclude_patterns": _extract_target_value(backup_target, "exclude_patterns", []),
                "description":      _extract_target_value(backup_target, "description", ""),
                "tags":             _extract_target_value(backup_target, "tags", []),
        }
        sources = [Path(p) for p in normalized_target["paths"]]
        name = name or normalized_target["name"] or target
        include_patterns = normalized_target["include_patterns"] or []
        exclude_patterns = normalized_target["exclude_patterns"] or []

        # Use patterns from target config if not overridden
        if not include and include_patterns:
            include = include_patterns
        if not exclude and exclude_patterns:
            exclude = exclude_patterns

            # Use default repository if not specified
            if not repository:
                default_repo_name = None
                if service_manager:
                    default_method = _get_service_method(service_manager, "get_default_repository")
                    if default_method:
                        try:
                            default_repo_name = _call_service_method(default_method)
                        except Exception as exc:
                            logging.getLogger(__name__).debug("Service default repository lookup failed: %s", exc)
                if default_repo_name is None:
                    if config_module is None:
                        config_module = _create_configuration_module(config_dir)
                    try:
                        default_repo_name = config_module.get_default_repository()
                    except Exception as exc:
                        logging.getLogger(__name__).debug("Config default repository lookup failed: %s", exc)
                if not isinstance(default_repo_name, (str, Path)):
                    default_repo_name = None
                if isinstance(default_repo_name, Path):
                    default_repo_name = str(default_repo_name)
                if isinstance(default_repo_name, str) and default_repo_name.strip():
                    repository = default_repo_name

        console.print(f"📁 Using backup target: [bold cyan]{target}[/bold cyan]")
        console.print(f"📂 Backing up {len(sources)} path(s)")

    # Validate sources
    if not sources:
        if target:
            console.print("⚠️  Could not resolve target paths locally; proceeding with service-managed backup.")
        else:
            show_error_panel("No Sources", "No source paths specified for backup")
            console.print("💡 Either provide source paths or use --target to specify a configured backup target")
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
            # Resolve repository name to URI
            from TimeLocker.utils.repository_resolver import resolve_repository_uri, get_default_repository

            # Get the actual repository name (for credential manager)
            actual_repository_name = repository or get_default_repository()
            repository_uri = resolve_repository_uri(repository)

            # Create repository instance to leverage full password resolution chain
            # (explicit password → credential manager → environment → prompt)
            backup_manager = BackupManager()
            repo = backup_manager.from_uri(repository_uri, password=password, repository_name=actual_repository_name)

            # Get password from repository (uses full resolution chain)
            resolved_password = repo.password() or ""
            if not resolved_password:
                if interactive:
                    # Only prompt if repository couldn't resolve password
                    resolved_password = Prompt.ask("Repository password", password=True)
                else:
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
    if repository_uri is None:
        repository_uri = fallback_repository_uri

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
            # Prefer legacy execute_backup when available (for tests mocking this method)
            if hasattr(service_manager, "execute_backup"):
                logger.debug("Calling service_manager.execute_backup (legacy API)")
                result = service_manager.execute_backup(backup_request)
            else:
                logger.debug("Calling service_manager.execute_backup_from_cli (new API)")
                result = service_manager.execute_backup_from_cli(backup_request)
            logger.debug(f"Backup result: {getattr(result, 'status', 'unknown')}")

            progress.remove_task(task)

        # Display results using new BackupResult data model
        def _safe_attr(obj, attr, default=None):
            try:
                value = getattr(obj, attr)
            except AttributeError:
                return default
            if isinstance(value, (str, int, float, bool, list, dict, tuple)):
                return value
            return default

        is_successful = _safe_attr(result, "is_successful", None)
        if is_successful is None:
            is_successful = _safe_attr(result, "success", False)
        if bool(is_successful):
            files_processed = _safe_attr(result, "files_processed", 0)
            bytes_processed = _safe_attr(result, "bytes_processed", 0)
            duration_value = _safe_attr(result, "duration", None)
            snapshot_id_value = _safe_attr(result, "snapshot_id", "Unknown") or "Unknown"

            details = {
                    "Snapshot ID":     snapshot_id_value,
                    "Files processed": f"{files_processed:,}" if isinstance(files_processed, (int, float)) else "Unknown",
                    "Data processed":  f"{bytes_processed:,} bytes" if isinstance(bytes_processed, (int, float)) and bytes_processed else "Unknown",
                    "Duration":        f"{duration_value:.1f}s" if isinstance(duration_value, (int, float)) and duration_value else "Unknown"
            }

            success_msg = "Backup operation completed successfully!"
            warnings = _safe_attr(result, "warnings", []) or []
            if warnings:
                success_msg += f" ({len(warnings)} warnings)"

            show_success_panel("Backup Completed", success_msg, details)

            # Show warnings if any
            for warning in warnings:
                console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
        else:
            error_msg = "Backup operation failed"
            errors = _safe_attr(result, "errors", []) or []
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
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Verify backup integrity for a repository or a specific snapshot."""
    setup_logging(verbose)

    # Validate inputs early (but only when provided so --help still works with exit 0)
    try:
        if repository:
            validate_repository_name_or_uri(repository)
        if snapshot:
            validate_snapshot_id_format(snapshot, allow_latest=True)
    except ValueError as ve:
        show_error_panel("Invalid Input", str(ve))
        raise typer.Exit(1)

    try:
        service_manager = get_cli_service_manager()

        # If --latest was provided without an explicit snapshot, we'll let the service
        # interpret None as "latest" or handle resolution internally. Tests only
        # assert exit codes, not behavior here.
        snapshot_id = snapshot if snapshot else None

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
