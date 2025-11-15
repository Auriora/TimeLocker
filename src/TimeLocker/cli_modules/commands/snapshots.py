"""
Snapshot operations backed by the CLI service manager.

The legacy implementation embedded full repository orchestration logic directly
inside the CLI.  That made the commands hard to maintain and, after the service
facade refactor, most of them started bailing out with deprecation warnings.
This module keeps the familiar `tl snapshots …` surface while delegating the
heavy work to `CLIServiceManager.snapshot_service`, which is exactly how the
tests exercise these commands (they patch the service manager with mocks).
"""

from __future__ import annotations

from typing import Any, List, Optional
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from .base import (
    create_typer_app,
    console,
    show_error_panel,
    show_success_panel,
    setup_logging,
    _get_service_manager_for_command,
    ConfigDirOption,
)

try:  # pragma: no cover - prefer src layout during development
    from src.TimeLocker import cli as _cli_module  # type: ignore
    from src.TimeLocker import cli_services as cli_services  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for installed package
    from TimeLocker import cli as _cli_module  # type: ignore
    import TimeLocker.cli_services as cli_services  # type: ignore
from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format

snapshots_app = create_typer_app(
        name="snapshots",
        help_text="Snapshot operations"
)


def _snapshot_service(config_dir: Optional[Path] = None):
    """Return the configured snapshot service or exit with a helpful error."""
    manager = _get_service_manager_for_command(config_dir)
    if manager is None:
        show_error_panel("Service Error", "Snapshot service manager is unavailable")
        raise typer.Exit(1)

    service = getattr(manager, "snapshot_service", None)
    if service is None:
        show_error_panel("Service Error", "Snapshot service is not configured")
        raise typer.Exit(1)

    return service


def _normalize_repository(repository: Optional[str]) -> Optional[str]:
    if repository:
        try:
            validate_repository_name_or_uri(repository)
        except ValueError as exc:
            show_error_panel("Invalid Repository", str(exc))
            raise typer.Exit(1)
    return repository


def _validate_snapshot_id(snapshot_id: str, *, allow_latest: bool = False, strict: bool = True) -> None:
    if not strict:
        return
    try:
        validate_snapshot_id_format(snapshot_id, allow_latest=allow_latest)
    except ValueError as exc:
        show_error_panel("Invalid Snapshot ID", str(exc))
        raise typer.Exit(1)


def _evaluate_success(result: Any) -> bool:
    if isinstance(result, bool):
        return result
    return bool(getattr(result, "success", getattr(result, "is_successful", False)))


def _render_snapshot_table(snapshots: List[Any]) -> None:
    table = Table(title="Snapshots")
    table.add_column("Snapshot ID", style="cyan")
    table.add_column("Time", style="green")
    table.add_column("Host", style="magenta")
    table.add_column("Tags", style="yellow")

    for snapshot in snapshots:
        snapshot_id = getattr(snapshot, "id", "?")
        time_value = getattr(snapshot, "time", "")
        host = getattr(snapshot, "hostname", getattr(snapshot, "host", ""))
        tags = getattr(snapshot, "tags", []) or []
        tags = getattr(snapshot, "tags", None)
        if tags:
            try:
                tags_list = list(tags)
            except TypeError:
                tags_list = [str(tags)]
        else:
            tags_list = []

        table.add_row(
                str(snapshot_id),
                str(time_value),
                str(host) if host else "N/A",
                ", ".join(str(tag) for tag in tags_list) if tags_list else "—",
        )

    console.print(table)


@snapshots_app.command("list")
def snapshots_list(
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
        config_dir: ConfigDirOption = None,
) -> None:
    """List snapshots in a repository."""
    setup_logging(verbose, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    snapshots = service.list_snapshots(repo)

    if not snapshots:
        console.print("[yellow]No snapshots found.[/yellow]")
        return

    _render_snapshot_table(snapshots)
    show_success_panel("Snapshots Listed", f"{len(snapshots)} snapshot(s) found.")


@snapshots_app.command("show")
def snapshots_show(
        snapshot_id: str = typer.Argument(..., help="Snapshot ID"),
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        config_dir: ConfigDirOption = None,
) -> None:
    """Display snapshot details."""
    _validate_snapshot_id(snapshot_id, allow_latest=True)
    setup_logging(False, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    snapshot = service.get_snapshot(snapshot_id, repository=repo)

    if not snapshot:
        show_error_panel("Snapshot Not Found", f"Snapshot '{snapshot_id}' was not found.")
        raise typer.Exit(1)

    tags = getattr(snapshot, "tags", None)
    if tags:
        try:
            tags_list = list(tags)
        except TypeError:
            tags_list = [str(tags)]
    else:
        tags_list = []

    details = Panel.fit(
            f"[bold]ID:[/bold] {getattr(snapshot, 'id', snapshot_id)}\n"
            f"[bold]Time:[/bold] {getattr(snapshot, 'time', 'unknown')}\n"
            f"[bold]Host:[/bold] {getattr(snapshot, 'hostname', getattr(snapshot, 'host', 'N/A'))}\n"
            f"[bold]Tags:[/bold] {', '.join(str(tag) for tag in tags_list) if tags_list else '—'}",
            title="Snapshot Details",
            border_style="green",
    )
    console.print(details)


@snapshots_app.command("find")
def snapshots_find(
        expression: str = typer.Argument(..., help="Search expression"),
        search_type: str = typer.Option(
                "path",
                "--type",
                help="Search type (path|name)",
        ),
        host: Optional[str] = typer.Option(None, "--host", help="Filter by host name"),
        tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
        limit: Optional[int] = typer.Option(None, "--limit", help="Maximum results"),
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        config_dir: ConfigDirOption = None,
) -> None:
    """Search snapshots for matching files."""
    setup_logging(False, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    results = service.find_snapshots(
            expression,
            search_type=search_type,
            host=host,
            tag=tag,
            limit=limit,
            repository=repo,
    )

    count = len(results or [])
    show_success_panel("Search Complete", f"Found {count} matching entr{'y' if count == 1 else 'ies'}.")


@snapshots_app.command("forget")
def snapshots_forget(
        snapshot_id: str = typer.Argument(..., help="Snapshot ID to remove"),
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        config_dir: ConfigDirOption = None,
) -> None:
    """Forget (delete) a snapshot."""
    _validate_snapshot_id(snapshot_id, allow_latest=False)
    setup_logging(False, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    result = service.delete_snapshot(snapshot_id, repository=repo)
    if _evaluate_success(result):
        show_success_panel("Snapshot Deleted", f"Snapshot {snapshot_id[:12]} removed.")
        return
    show_error_panel("Delete Failed", "Snapshot could not be removed.")
    raise typer.Exit(1)


@snapshots_app.command("prune")
def snapshots_prune(
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        config_dir: ConfigDirOption = None,
) -> None:
    """Prune unused snapshot data."""
    setup_logging(False, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    result = getattr(service, "prune_snapshots", None)
    if result is None:
        show_error_panel("Prune Error", "Snapshot prune is not available.")
        raise typer.Exit(1)
    outcome = result(repository=repo)
    if _evaluate_success(outcome):
        show_success_panel("Prune Completed", "Repository data has been pruned.")
        return
    show_error_panel("Prune Failed", "Snapshot prune did not succeed.")
    raise typer.Exit(1)


@snapshots_app.command("diff")
def snapshots_diff(
        first_snapshot: str = typer.Argument(..., help="First snapshot ID"),
        second_snapshot: str = typer.Argument(..., help="Second snapshot ID"),
        repository: Optional[str] = typer.Option(
                None,
                "--repository",
                "-r",
                help="Repository name or URI",
        ),
        config_dir: ConfigDirOption = None,
) -> None:
    """Show differences between two snapshots."""
    _validate_snapshot_id(first_snapshot, allow_latest=True, strict=False)
    _validate_snapshot_id(second_snapshot, allow_latest=True, strict=False)
    setup_logging(False, config_dir)
    service = _snapshot_service(config_dir)
    repo = _normalize_repository(repository)
    diff_method = getattr(service, "diff_snapshots", None)
    if diff_method is None:
        show_error_panel("Diff Error", "Snapshot diff is not available.")
        raise typer.Exit(1)

    diff_method(first_snapshot, second_snapshot, repository=repo)
    show_success_panel(
            "Diff Complete",
            f"Compared {first_snapshot[:12]} to {second_snapshot[:12]}."
    )
