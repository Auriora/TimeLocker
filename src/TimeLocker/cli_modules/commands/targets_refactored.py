"""
Backup target management commands (Phase 3 refactored).

This module demonstrates the Phase 3 refactoring with base classes and decorators.
"""

import sys
from typing import Optional, List, Annotated
from pathlib import Path

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

# Import from base module
from .base import (
    CommandBase,
    with_error_handling,
    with_logging,
    create_typer_app,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    VerboseOption,
    JsonOption,
    YesOption,
    validate_not_empty,
)

# Import from TimeLocker package
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.completion import target_name_completer, file_path_completer

# Create Typer app using helper
targets_app = create_typer_app(
    name="targets",
    help_text="Backup target operations"
)


@targets_app.command("list")
@with_error_handling("List Error")
@with_logging
def targets_list(
        verbose: VerboseOption = False,
        json_output: JsonOption = False,
) -> None:
    """List configured backup targets."""
    manager = get_cli_service_manager()
    list_method = _get_service_method(manager, "list_backup_targets")
    if not list_method:
        show_error_panel("Not Implemented", "Target listing is not available in this build.")
        raise typer.Exit(1)

    targets = list_method() or []
    normalized: List[dict] = []
    for target in targets:
        if isinstance(target, dict):
            normalized.append(target)
        elif hasattr(target, "__dict__"):
            normalized.append({k: v for k, v in target.__dict__.items() if not k.startswith("_")})
        else:
            normalized.append({"name": str(target)})

    if json_output:
        console.print_json(data=normalized)
        return

    if not normalized:
        show_info_panel("No Targets", "No backup targets configured. Add one with 'tl targets add'.")
        return

    table = Table(title="Configured Backup Targets")
    table.add_column("Name", style="cyan")
    table.add_column("Paths", overflow="fold")
    table.add_column("Tags", style="magenta")
    table.add_column("Description", overflow="fold")

    for target in normalized:
        name = str(target.get("name", "unknown"))
        paths = target.get("paths") or target.get("path") or []
        if isinstance(paths, (list, tuple)):
            path_text = ", ".join(str(p) for p in paths)
        else:
            path_text = str(paths)
        tags = target.get("tags", [])
        if isinstance(tags, (list, tuple)):
            tag_text = ", ".join(str(t) for t in tags)
        else:
            tag_text = str(tags)
        description = str(target.get("description", ""))
        table.add_row(name, path_text, tag_text or "None", description)

    console.print(table)
    show_success_panel("List Completed", f"Found {len(normalized)} backup targets.")


@targets_app.command("add")
@with_error_handling("Target Add Error")
@with_logging
def targets_add(
        name: Annotated[Optional[str], typer.Argument(help="Target name")] = None,
        paths: Annotated[Optional[List[Path]], typer.Option("--path", "-p", help="Paths to include", autocompletion=file_path_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", help="Include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", help="Exclude patterns")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Target tags")] = None,
        verbose: VerboseOption = False,
) -> None:
    """Add a new backup target."""
    interactive = CommandBase.is_interactive()
    
    # Validate name
    if not name:
        if interactive:
            name = Prompt.ask("Target name")
        else:
            show_error_panel("Missing Parameter", "Target name is required in non-interactive mode")
            raise typer.Exit(2)
    
    name = validate_not_empty(name, "Target name")

    # Validate paths
    if not paths or len(paths) == 0:
        if interactive:
            user_path = Prompt.ask("Path to include", default="")
            if user_path:
                paths = [Path(user_path)]
        if not paths or len(paths) == 0:
            show_error_panel("Missing Parameter", "At least one --path must be provided")
            raise typer.Exit(2)

    # Execute add operation
    str_paths = [str(p) for p in paths]
    manager = get_cli_service_manager()
    add_method = _get_service_method(manager, "add_backup_target")
    if not add_method:
        show_error_panel("Not Implemented", "Target creation is not available in this build.")
        raise typer.Exit(1)

    result = _call_service_method(
            add_method,
            name=name,
            target_name=name,
            paths=str_paths,
            include_patterns=include or [],
            exclude_patterns=exclude or [],
            description=description,
            tags=tags or [],
    )
    
    success = getattr(result, "success", True)
    if success:
        show_success_panel(
                "Target Added",
                f"Backup target '{name}' added successfully.",
                {
                        "Paths":   ", ".join(str_paths),
                        "Include": ", ".join(include or []) or "None",
                        "Exclude": ", ".join(exclude or []) or "None",
                        "Tags":    ", ".join(tags or []) or "None",
                },
        )
    else:
        show_error_panel("Target Add Failed", f"Failed to add target '{name}'.")
        raise typer.Exit(1)


@targets_app.command("show")
@with_error_handling("Target Show Error")
@with_logging
def targets_show(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        verbose: VerboseOption = False,
) -> None:
    """Show details for a backup target."""
    manager = get_cli_service_manager()
    show_method = _get_service_method(manager, "get_backup_target_by_name")
    target_info = None
    if show_method:
        target_info = _call_service_method(show_method, name=name, target_name=name)

    if target_info is None:
        show_error_panel("Target Not Found", f"Backup target '{name}' not found.")
        raise typer.Exit(1)

    if isinstance(target_info, tuple):
        target_info = list(target_info)

    if isinstance(target_info, list):
        console.print(target_info)
        return

    if hasattr(target_info, "__dict__"):
        target_info = {k: v for k, v in target_info.__dict__.items() if not k.startswith("_")}
    elif not isinstance(target_info, dict):
        target_info = {"name": name, "details": str(target_info)}

    target_info.setdefault("name", name)
    panel_lines = []
    for key, value in sorted(target_info.items()):
        panel_lines.append(f"[bold]{key}:[/bold] {value}")
    console.print(Panel("\n".join(panel_lines), title=f"[bold blue]Target: {name}[/bold blue]", border_style="blue"))


@targets_app.command("edit")
@with_error_handling("Target Edit Error")
@with_logging
def targets_edit(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        paths: Annotated[Optional[List[Path]], typer.Option("--path", "-p", help="Override paths", autocompletion=file_path_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", help="Replace include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", help="Replace exclude patterns")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Replace tags")] = None,
        verbose: VerboseOption = False,
) -> None:
    """Edit an existing backup target."""
    manager = get_cli_service_manager()
    edit_method = _get_service_method(manager, "edit_backup_target")
    if not edit_method:
        show_error_panel("Not Implemented", "Target editing is not available in this build.")
        raise typer.Exit(1)

    payload = {
            "name":        name,
            "target_name": name,
    }
    if paths is not None:
        payload["paths"] = [str(p) for p in paths]
    if description is not None:
        payload["description"] = description
    if include is not None:
        payload["include_patterns"] = include
    if exclude is not None:
        payload["exclude_patterns"] = exclude
    if tags is not None:
        payload["tags"] = tags

    result = _call_service_method(edit_method, **payload)
    success = getattr(result, "success", True)
    if success:
        show_success_panel("Target Updated", f"Backup target '{name}' updated successfully.")
    else:
        show_error_panel("Edit Failed", f"Failed to update target '{name}'.")
        raise typer.Exit(1)


@targets_app.command("remove")
@with_error_handling("Target Remove Error")
@with_logging
def targets_remove(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        yes: YesOption = False,
        verbose: VerboseOption = False,
) -> None:
    """Remove a backup target."""
    interactive = CommandBase.is_interactive()
    confirmed = yes
    if not confirmed and interactive:
        confirmed = Confirm.ask(f"Remove backup target '{name}'?", default=False)
        if not confirmed:
            show_info_panel("Operation Cancelled", "Target removal cancelled.")
            raise typer.Exit(0)

    manager = get_cli_service_manager()
    remove_method = _get_service_method(manager, "remove_backup_target")
    if not remove_method:
        show_error_panel("Not Implemented", "Target removal is not available in this build.")
        raise typer.Exit(1)

    result = _call_service_method(remove_method, name=name, target_name=name)
    success = getattr(result, "success", True)
    if success:
        show_success_panel("Target Removed", f"Backup target '{name}' removed successfully.")
    else:
        show_error_panel("Remove Failed", f"Failed to remove target '{name}'.")
        raise typer.Exit(1)
