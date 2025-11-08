"""
Example enhanced command demonstrating JSON output, non-interactive mode, and filtering.

This module serves as a reference implementation showing how to use the new
output formatting, non-interactive mode, and filtering capabilities.
"""

from typing import Optional, List
from pathlib import Path

import typer
from rich.table import Table

from .base import (
    create_typer_app,
    VerboseOption,
    JsonOption,
    QuietOption,
    NonInteractiveOption,
    ConfigDirOption,
    FieldsOption,
    ExcludeFieldsOption,
    PageOption,
    PageSizeOption,
    setup_logging,
    console,
    create_formatter,
    create_filter,
    create_paginator,
    apply_filters_and_pagination,
    require_parameter,
    ExitCode,
)

# Create example app
example_app = create_typer_app(
    name="example",
    help_text="Example commands demonstrating enhanced CLI features"
)


@example_app.command("list")
def example_list(
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    quiet: QuietOption = False,
    fields: FieldsOption = None,
    exclude: ExcludeFieldsOption = None,
    page: PageOption = 1,
    page_size: PageSizeOption = 20,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example list command with JSON output, filtering, and pagination.
    
    This command demonstrates:
    - JSON output format (--json)
    - Quiet mode (--quiet)
    - Field filtering (--fields, --exclude)
    - Pagination (--page, --page-size)
    """
    setup_logging(verbose, config_dir)
    
    # Create output formatter
    formatter = create_formatter(json_output=json_output, quiet=quiet, console=console)
    
    try:
        # Example data (in real command, this would come from service layer)
        items = [
            {"name": "item1", "status": "active", "size": 1024, "description": "First item"},
            {"name": "item2", "status": "inactive", "size": 2048, "description": "Second item"},
            {"name": "item3", "status": "active", "size": 512, "description": "Third item"},
            {"name": "item4", "status": "active", "size": 4096, "description": "Fourth item"},
            {"name": "item5", "status": "inactive", "size": 1536, "description": "Fifth item"},
        ]
        
        # Apply filtering
        output_filter = create_filter(fields=fields, exclude=exclude)
        
        # Apply pagination
        paginator = create_paginator(page_size=page_size)
        
        # Process data
        result = apply_filters_and_pagination(
            data=items,
            filter=output_filter,
            paginator=paginator,
            page=page
        )
        
        # Output results
        if formatter.is_json_mode():
            formatter.data(result, command="example list")
        else:
            # Human-readable table output
            if not quiet:
                table = Table(title="Example Items")
                
                # Determine columns from first item
                if result["items"]:
                    columns = list(result["items"][0].keys())
                    for col in columns:
                        table.add_column(col.replace("_", " ").title(), style="cyan")
                    
                    for item in result["items"]:
                        table.add_row(*[str(item.get(col, "")) for col in columns])
                    
                    console.print(table)
                    
                    # Show pagination info
                    if "pagination" in result:
                        pagination = result["pagination"]
                        console.print(
                            f"\nPage {pagination['page']} of {pagination['total_pages']} "
                            f"({pagination['total_items']} total items)"
                        )
                else:
                    formatter.info("No items found")
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except KeyboardInterrupt:
        formatter.error("Operation cancelled by user", title="Cancelled")
        raise typer.Exit(ExitCode.CANCELLED.value)
    except Exception as e:
        formatter.error(
            f"Failed to list items: {e}",
            error_type="OperationError",
            title="List Error"
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(ExitCode.ERROR.value)


@example_app.command("create")
def example_create(
    name: Optional[str] = typer.Argument(None, help="Item name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Item description"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    quiet: QuietOption = False,
    non_interactive: NonInteractiveOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example create command with non-interactive mode support.
    
    This command demonstrates:
    - Non-interactive mode (--non-interactive)
    - Required parameter validation
    - JSON output for operation results
    """
    setup_logging(verbose, config_dir)
    
    # Create output formatter
    formatter = create_formatter(json_output=json_output, quiet=quiet, console=console)
    
    try:
        # Validate required parameters in non-interactive mode
        if non_interactive:
            name = require_parameter(name, "name", formatter, allow_interactive=False)
        else:
            # Interactive prompting
            if name is None:
                from rich.prompt import Prompt
                name = Prompt.ask("Item name")
            
            if description is None:
                from rich.prompt import Prompt
                description = Prompt.ask("Description", default="")
        
        # Simulate creation (in real command, this would call service layer)
        result = {
            "name": name,
            "description": description or "",
            "status": "created",
            "id": "example-123"
        }
        
        # Output success
        formatter.success(
            f"Successfully created item '{name}'",
            data=result,
            command="example create"
        )
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except KeyboardInterrupt:
        formatter.error("Operation cancelled by user", title="Cancelled")
        raise typer.Exit(ExitCode.CANCELLED.value)
    except typer.Exit:
        raise
    except Exception as e:
        formatter.error(
            f"Failed to create item: {e}",
            error_type="OperationError",
            title="Create Error"
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(ExitCode.ERROR.value)


@example_app.command("status")
def example_status(
    name: str = typer.Argument(..., help="Item name"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    quiet: QuietOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example status command showing structured output.
    
    This command demonstrates:
    - Structured data output
    - Consistent JSON schema
    - Human-readable panels
    """
    setup_logging(verbose, config_dir)
    
    # Create output formatter
    formatter = create_formatter(json_output=json_output, quiet=quiet, console=console)
    
    try:
        # Simulate status retrieval
        status_data = {
            "name": name,
            "status": "active",
            "created": "2024-01-01T12:00:00Z",
            "last_modified": "2024-01-15T14:30:00Z",
            "size": 2048,
            "items_count": 42
        }
        
        # Output status
        if formatter.is_json_mode():
            formatter.data(status_data, command="example status")
        else:
            if not quiet:
                from rich.panel import Panel
                content = "\n".join([
                    f"[bold]Name:[/bold] {status_data['name']}",
                    f"[bold]Status:[/bold] {status_data['status']}",
                    f"[bold]Created:[/bold] {status_data['created']}",
                    f"[bold]Last Modified:[/bold] {status_data['last_modified']}",
                    f"[bold]Size:[/bold] {status_data['size']} bytes",
                    f"[bold]Items:[/bold] {status_data['items_count']}",
                ])
                panel = Panel(
                    content,
                    title=f"[bold blue]Status: {name}[/bold blue]",
                    border_style="blue"
                )
                console.print(panel)
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except KeyboardInterrupt:
        formatter.error("Operation cancelled by user", title="Cancelled")
        raise typer.Exit(ExitCode.CANCELLED.value)
    except Exception as e:
        formatter.error(
            f"Failed to get status: {e}",
            error_type="OperationError",
            title="Status Error"
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(ExitCode.ERROR.value)


# Export the app
__all__ = ["example_app"]
