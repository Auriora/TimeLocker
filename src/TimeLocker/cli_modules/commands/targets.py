"""
Backup target management commands.

This module contains all CLI commands for managing backup targets,
including listing, adding, showing, editing, and removing targets.
"""

import sys
from typing import Optional, List, Annotated
from pathlib import Path

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

# Import from TimeLocker package (not from cli submodule to avoid circular imports)
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.completion import target_name_completer, file_path_completer

# Import helpers - these are in the parent cli.py for now
# Will be fully migrated once all commands are extracted
from TimeLocker import cli as _cli_module
show_success_panel = _cli_module.show_success_panel
show_error_panel = _cli_module.show_error_panel
show_info_panel = _cli_module.show_info_panel
setup_logging = _cli_module.setup_logging
_get_service_method = _cli_module._get_service_method
_call_service_method = _cli_module._call_service_method
console = _cli_module.console

# Create Typer app for targets
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}

targets_app = typer.Typer(
    help="Backup target operations",
    no_args_is_help=True,
    context_settings=CLI_CONTEXT_SETTINGS
)
targets_app.info.options_metavar = "⟨OPTIONS⟩"


@targets_app.command("list")
def targets_list(
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
        json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
) -> None:
    """List configured backup targets."""
    setup_logging(verbose)
    try:
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
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "List operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("List Error", f"Failed to list targets: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("add")
def targets_add(
        name: Annotated[Optional[str], typer.Argument(help="Target name")] = None,
        paths: Annotated[Optional[List[Path]], typer.Option("--path", "-p", help="Paths to include", autocompletion=file_path_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", help="Include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", help="Exclude patterns")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Target tags")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Add a new backup target."""
    setup_logging(verbose)
    interactive = sys.stdin.isatty()
    try:
        if not name:
            if interactive:
                name = Prompt.ask("Target name")
            else:
                show_error_panel("Missing Parameter", "Target name is required in non-interactive mode")
                raise typer.Exit(2)

        if name is not None and not name.strip():
            show_error_panel("Invalid Target Name", "Target name cannot be empty or whitespace")
            raise typer.Exit(2)

        if not paths or len(paths) == 0:
            if interactive:
                user_path = Prompt.ask("Path to include", default="")
                if user_path:
                    paths = [Path(user_path)]
            if not paths or len(paths) == 0:
                show_error_panel("Missing Parameter", "At least one --path must be provided")
                raise typer.Exit(2)

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
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Target creation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Target Add Error", f"Failed to add target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("show")
def targets_show(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Show details for a backup target."""
    setup_logging(verbose)
    try:
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
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Show operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Target Show Error", f"Failed to show target '{name}': {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("edit")
def targets_edit(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        paths: Annotated[Optional[List[Path]], typer.Option("--path", "-p", help="Override paths", autocompletion=file_path_completer)] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
        include: Annotated[Optional[List[str]], typer.Option("--include", help="Replace include patterns")] = None,
        exclude: Annotated[Optional[List[str]], typer.Option("--exclude", help="Replace exclude patterns")] = None,
        tags: Annotated[Optional[List[str]], typer.Option("--tags", help="Replace tags")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Edit an existing backup target."""
    setup_logging(verbose)
    try:
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
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Edit operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Target Edit Error", f"Failed to edit target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@targets_app.command("remove")
def targets_remove(
        name: Annotated[str, typer.Argument(help="Target name", autocompletion=target_name_completer)],
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm removal without prompt")] = False,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Remove a backup target."""
    setup_logging(verbose)
    try:
        interactive = sys.stdin.isatty()
        confirmed = yes
        if not confirmed:
            if interactive:
                confirmed = Confirm.ask(f"Remove backup target '{name}'?", default=False)
                if not confirmed:
                    show_info_panel("Operation Cancelled", "Target removal cancelled.")
                    raise typer.Exit(0)
            else:
                confirmed = True

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
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Removal operation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Target Remove Error", f"Failed to remove target: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
