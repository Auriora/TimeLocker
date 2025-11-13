"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from TimeLocker.selection_manager import SelectionManager, SelectionError
from TimeLocker.selection_template_manager import (
    SelectionTemplateManager,
    TemplateNotFoundError,
    TemplateAlreadyExistsError,
    TemplateValidationError,
    TemplateImportError,
    TemplateExportError
)
from TimeLocker.selection_models import (
    SelectionConfig,
    SelectionTemplate,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig,
    PrecedenceStrategy,
    ConflictResolution
)

logger = logging.getLogger(__name__)
SUPPORTED_SERIALIZATION_FORMATS = ("json", "yaml")

# Create selections sub-app
selections_app = typer.Typer(
        help="Data selection template management",
        no_args_is_help=True
)


def _get_console() -> Console:
    """Get a console instance that cooperates with Typer's test runner."""
    import typer
    try:
        return Console(file=typer.get_text_stream("stdout"), width=100)
    except Exception:
        return Console(width=100)


def _get_selection_manager() -> SelectionManager:
    """Get or create a SelectionManager instance"""
    return SelectionManager()


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _show_success(title: str, message: str) -> None:
    """Display a success message"""
    console = _get_console()
    console.print(Panel(
            f"✓ {message}",
            title=f"[bold green]{title}[/bold green]",
            border_style="green"
    ))


def _show_error(title: str, message: str, help_text: Optional[str] = None) -> None:
    """Display an error message"""
    console = _get_console()
    body = f"✗ {message}"
    if help_text:
        body = f"{body}\n\n[dim]{help_text}[/dim]"
    console.print(Panel(
            body,
            title=f"[bold red]{title}[/bold red]",
            border_style="red"
    ))


def _show_info(title: str, message: str) -> None:
    """Display an info message"""
    console = _get_console()
    console.print(Panel(
            f"ℹ {message}",
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan"
    ))


@selections_app.command("create")
def create_selection(
        name: Annotated[str, typer.Argument(help="Name for the selection template")],
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="Description of the selection")] = None,
        include_path: Annotated[Optional[List[str]], typer.Option("--include-path", "-i", help="Path to include (can be specified multiple times)")] = None,
        exclude_path: Annotated[Optional[List[str]], typer.Option("--exclude-path", "-e", help="Path to exclude (can be specified multiple times)")] = None,
        include_pattern: Annotated[Optional[List[str]], typer.Option("--include", help="Include pattern (can be specified multiple times)")] = None,
        exclude_pattern: Annotated[Optional[List[str]], typer.Option("--exclude", help="Exclude pattern (can be specified multiple times)")] = None,
        pattern_group: Annotated[Optional[List[str]], typer.Option("--group", "-g", help="Pattern group to include (can be specified multiple times)")] = None,
        case_sensitive: Annotated[bool, typer.Option("--case-sensitive", help="Enable case-sensitive pattern matching")] = False,
        precedence: Annotated[str, typer.Option("--precedence", help="Precedence strategy (include_first, exclude_first, specificity)")] = "exclude_first",
        tags: Annotated[Optional[List[str]], typer.Option("--tag", "-t", help="Tags for categorization (can be specified multiple times)")] = None,
) -> None:
    """
    Create a new selection template.
    
    Selection templates define which files to include or exclude in backups using
    paths and patterns. Templates can be reused across multiple backup operations.
    
    Examples:
        # Create a simple selection for documents
        timelocker selections create documents --include-path ~/Documents
        
        # Create a selection with patterns
        timelocker selections create code \\
            --include-path ~/projects \\
            --include '*.py' --include '*.js' \\
            --exclude 'node_modules/*' --exclude '__pycache__/*'
        
        # Create a selection with pattern groups
        timelocker selections create media \\
            --include-path ~/Pictures \\
            --group media_files --group office_documents
    """
    try:
        # Parse precedence strategy
        precedence_map = {
                "include_first": PrecedenceStrategy.INCLUDE_OVERRIDES_EXCLUDE,
                "exclude_first": PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE,
                "specificity":   PrecedenceStrategy.MOST_SPECIFIC_WINS,
        }
        precedence_strategy = precedence_map.get(precedence, PrecedenceStrategy.EXCLUDE_OVERRIDES_INCLUDE)

        # Build selection configuration
        config = SelectionConfig(
                include_paths=[Path(p).expanduser() for p in (include_path or [])],
                exclude_paths=[Path(p).expanduser() for p in (exclude_path or [])],
                include_patterns=[
                        PatternRule(
                                pattern=p,
                                syntax=PatternSyntax.GLOB,
                                case_sensitive=case_sensitive,
                                applies_to=PathComponent.FULL_PATH
                        )
                        for p in (include_pattern or [])
                ],
                exclude_patterns=[
                        PatternRule(
                                pattern=p,
                                syntax=PatternSyntax.GLOB,
                                case_sensitive=case_sensitive,
                                applies_to=PathComponent.FULL_PATH
                        )
                        for p in (exclude_pattern or [])
                ],
                pattern_groups=list(pattern_group or []),
                precedence_config=PrecedenceConfig(
                        default_strategy=precedence_strategy,
                        conflict_resolution=ConflictResolution.WARN_ON_CONFLICT
                ),
                case_sensitive=case_sensitive
        )

        # Create template
        import uuid
        from datetime import datetime

        template = SelectionTemplate(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                selection_config=config,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tags=list(tags or [])
        )

        # Save template
        template_manager = SelectionTemplateManager()
        template_id = asyncio.run(template_manager.create_template(template))

        _show_success(
                "Selection Created",
                f"Selection template '{name}' created successfully\n"
                f"ID: {template_id}\n"
                f"Include paths: {len(config.include_paths)}\n"
                f"Exclude paths: {len(config.exclude_paths)}\n"
                f"Include patterns: {len(config.include_patterns)}\n"
                f"Exclude patterns: {len(config.exclude_patterns)}\n"
                f"Pattern groups: {len(config.pattern_groups)}"
        )
        typer.echo(f"Selection template '{name}' created successfully (ID: {template_id})")

    except TemplateAlreadyExistsError as e:
        _show_error("Template Exists", str(e))
        raise typer.Exit(1)
    except TemplateValidationError as e:
        _show_error("Validation Error", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Creation Failed", f"Failed to create selection template: {e}")
        logger.exception("Failed to create selection template")
        raise typer.Exit(1)


@selections_app.command("list")
def list_selections(
        tag: Annotated[Optional[str], typer.Option("--tag", "-t", help="Filter by tag")] = None,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed information")] = False,
) -> None:
    """
    List all selection templates.
    
    Examples:
        timelocker selections list
        timelocker selections list --tag documents
        timelocker selections list --verbose
    """
    try:
        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Filter by tag if specified
        if tag:
            templates = [t for t in templates if tag in t.tags]

        if not templates:
            _show_info("No Templates", "No selection templates found")
            return

        # Create table
        table = Table(title="Selection Templates", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Description")
        table.add_column("Paths", justify="right")
        table.add_column("Patterns", justify="right")

        if verbose:
            table.add_column("Tags")
            table.add_column("Created")
            table.add_column("Usage", justify="right")

        for template in templates:
            config = template.selection_config
            path_count = len(config.include_paths) + len(config.exclude_paths)
            pattern_count = len(config.include_patterns) + len(config.exclude_patterns)

            row = [
                    template.name,
                    template.description or "",
                    str(path_count),
                    str(pattern_count),
            ]

            if verbose:
                row.extend([
                        ", ".join(template.tags) if template.tags else "",
                        template.created_at.strftime("%Y-%m-%d"),
                        str(template.usage_count)
                ])

            table.add_row(*row)

        console = _get_console()
        console.print(table)
        console.print(f"\n[dim]Total: {len(templates)} template(s)[/dim]")

    except Exception as e:
        _show_error("List Failed", f"Failed to list selection templates: {e}")
        logger.exception("Failed to list selection templates")
        raise typer.Exit(1)


@selections_app.command("show")
def show_selection(
        name: Annotated[str, typer.Argument(help="Name of the selection template")],
) -> None:
    """
    Show details of a selection template.
    
    Examples:
        timelocker selections show documents
    """
    try:
        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Find template by name
        template = next((t for t in templates if t.name == name), None)
        if not template:
            _show_error("Not Found", f"Selection template '{name}' not found")
            raise typer.Exit(1)

        config = template.selection_config

        # Display template details
        console = _get_console()
        console.print(f"\n[bold cyan]Selection Template: {template.name}[/bold cyan]")
        console.print(f"ID: {template.id}")
        if template.description:
            console.print(f"Description: {template.description}")
        console.print(f"Created: {template.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Updated: {template.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Usage count: {template.usage_count}")

        if template.tags:
            console.print(f"Tags: {', '.join(template.tags)}")

        # Include paths
        if config.include_paths:
            console.print("\n[bold]Include Paths:[/bold]")
            for path in config.include_paths:
                console.print(f"  + {path}")

        # Exclude paths
        if config.exclude_paths:
            console.print("\n[bold]Exclude Paths:[/bold]")
            for path in config.exclude_paths:
                console.print(f"  - {path}")

        # Include patterns
        if config.include_patterns:
            console.print("\n[bold]Include Patterns:[/bold]")
            for pattern in config.include_patterns:
                console.print(f"  + {pattern.pattern} ({pattern.syntax.value})")

        # Exclude patterns
        if config.exclude_patterns:
            console.print("\n[bold]Exclude Patterns:[/bold]")
            for pattern in config.exclude_patterns:
                console.print(f"  - {pattern.pattern} ({pattern.syntax.value})")

        # Pattern groups
        if config.pattern_groups:
            console.print("\n[bold]Pattern Groups:[/bold]")
            for group in config.pattern_groups:
                console.print(f"  • {group}")

        # Configuration
        console.print("\n[bold]Configuration:[/bold]")
        console.print(f"  Case sensitive: {config.case_sensitive}")
        console.print(f"  Precedence strategy: {config.precedence_config.default_strategy.value}")
        console.print()

    except Exception as e:
        _show_error("Show Failed", f"Failed to show selection template: {e}")
        logger.exception("Failed to show selection template")
        raise typer.Exit(1)


@selections_app.command("edit")
def edit_selection(
        name: Annotated[str, typer.Argument(help="Name of the selection template")],
        new_name: Annotated[Optional[str], typer.Option("--name", help="New name for the template")] = None,
        description: Annotated[Optional[str], typer.Option("--description", "-d", help="New description")] = None,
        add_include_path: Annotated[Optional[List[str]], typer.Option("--add-include-path", help="Add include path")] = None,
        add_exclude_path: Annotated[Optional[List[str]], typer.Option("--add-exclude-path", help="Add exclude path")] = None,
        add_include_pattern: Annotated[Optional[List[str]], typer.Option("--add-include", help="Add include pattern")] = None,
        add_exclude_pattern: Annotated[Optional[List[str]], typer.Option("--add-exclude", help="Add exclude pattern")] = None,
        add_tag: Annotated[Optional[List[str]], typer.Option("--add-tag", help="Add tag")] = None,
) -> None:
    """
    Edit an existing selection template.
    
    Examples:
        timelocker selections edit documents --description "Updated description"
        timelocker selections edit code --add-include '*.ts' --add-exclude 'dist/*'
        timelocker selections edit media --add-tag photos
    """
    try:
        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Find template by name
        template = next((t for t in templates if t.name == name), None)
        if not template:
            _show_error("Not Found", f"Selection template '{name}' not found")
            raise typer.Exit(1)

        # Build updates dictionary
        updates = {}

        if new_name:
            updates['name'] = new_name

        if description:
            updates['description'] = description

        # Handle path additions
        if add_include_path:
            new_paths = template.selection_config.include_paths + [
                    Path(p).expanduser() for p in add_include_path
            ]
            if 'selection_config' not in updates:
                updates['selection_config'] = template.selection_config
            updates['selection_config'].include_paths = new_paths

        if add_exclude_path:
            new_paths = template.selection_config.exclude_paths + [
                    Path(p).expanduser() for p in add_exclude_path
            ]
            if 'selection_config' not in updates:
                updates['selection_config'] = template.selection_config
            updates['selection_config'].exclude_paths = new_paths

        # Handle pattern additions
        if add_include_pattern:
            new_patterns = template.selection_config.include_patterns + [
                    PatternRule(
                            pattern=p,
                            syntax=PatternSyntax.GLOB,
                            case_sensitive=template.selection_config.case_sensitive,
                            applies_to=PathComponent.FULL_PATH
                    )
                    for p in add_include_pattern
            ]
            if 'selection_config' not in updates:
                updates['selection_config'] = template.selection_config
            updates['selection_config'].include_patterns = new_patterns

        if add_exclude_pattern:
            new_patterns = template.selection_config.exclude_patterns + [
                    PatternRule(
                            pattern=p,
                            syntax=PatternSyntax.GLOB,
                            case_sensitive=template.selection_config.case_sensitive,
                            applies_to=PathComponent.FULL_PATH
                    )
                    for p in add_exclude_pattern
            ]
            if 'selection_config' not in updates:
                updates['selection_config'] = template.selection_config
            updates['selection_config'].exclude_patterns = new_patterns

        # Handle tag additions
        if add_tag:
            new_tags = list(set(template.tags + list(add_tag)))
            updates['tags'] = new_tags

        if not updates:
            _show_info("No Changes", "No updates specified")
            return

        # Update template
        updated_template = asyncio.run(template_manager.update_template(template.id, updates))

        _show_success(
                "Selection Updated",
                f"Selection template '{name}' updated successfully"
        )

    except TemplateNotFoundError as e:
        _show_error("Not Found", str(e))
        raise typer.Exit(1)
    except TemplateValidationError as e:
        _show_error("Validation Error", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Update Failed", f"Failed to update selection template: {e}")
        logger.exception("Failed to update selection template")
        raise typer.Exit(1)


@selections_app.command("delete")
def delete_selection(
        name: Annotated[str, typer.Argument(help="Name of the selection template")],
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """
    Delete a selection template.
    
    Examples:
        timelocker selections delete old-template
        timelocker selections delete old-template --yes
    """
    try:
        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Find template by name
        template = next((t for t in templates if t.name == name), None)
        if not template:
            _show_error("Not Found", f"Selection template '{name}' not found")
            raise typer.Exit(1)

        # Confirm deletion
        if not yes:
            confirm = typer.confirm(f"Delete selection template '{name}'?")
            if not confirm:
                console = _get_console()
                console.print("Deletion cancelled")
                return

        # Delete template
        asyncio.run(template_manager.delete_template(template.id))

        _show_success(
                "Selection Deleted",
                f"Selection template '{name}' deleted successfully"
        )
        typer.echo(f"Selection template '{name}' deleted successfully")

    except TemplateNotFoundError as e:
        _show_error("Not Found", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Deletion Failed", f"Failed to delete selection template: {e}")
        logger.exception("Failed to delete selection template")
        raise typer.Exit(1)


@selections_app.command("test")
def test_selection(
        name: Annotated[str, typer.Argument(help="Name of the selection template")],
        path: Annotated[str, typer.Argument(help="Path to test against")],
        limit: Annotated[int, typer.Option("--limit", "-l", help="Maximum number of files to show")] = 100,
) -> None:
    """
    Test a selection template against a path.
    
    This command evaluates the selection rules against the specified path
    and shows which files would be included or excluded.
    
    Examples:
        timelocker selections test documents ~/Documents
        timelocker selections test code ~/projects --limit 50
    """
    try:
        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Find template by name
        template = next((t for t in templates if t.name == name), None)
        if not template:
            _show_error("Not Found", f"Selection template '{name}' not found")
            raise typer.Exit(1)

        # Create selection manager and evaluate
        manager = _get_selection_manager()
        selection = asyncio.run(manager.create_selection(template.selection_config))

        test_path = Path(path).expanduser()
        if not test_path.exists():
            _show_error("Path Not Found", f"Path does not exist: {test_path}")
            raise typer.Exit(1)

        # Generate preview
        console = _get_console()
        console.print(f"\n[bold cyan]Testing selection '{name}' against {test_path}[/bold cyan]\n")

        with console.status("[bold green]Evaluating selection..."):
            preview = asyncio.run(manager.preview_selection(selection, [test_path], limit=limit))

        # Display results
        console.print(f"[bold]Preview Results:[/bold]")
        console.print(f"Total estimated files: {preview.total_estimated_files}")
        console.print(f"Preview generation time: {preview.preview_generation_time:.2f}s")

        if preview.truncated:
            console.print(f"[yellow]Results truncated to {limit} files[/yellow]")

        # Show included files
        if preview.sample_included_files:
            console.print(f"\n[bold green]Included Files ({len(preview.sample_included_files)}):[/bold green]")
            for file_path in preview.sample_included_files[:20]:  # Show first 20
                console.print(f"  + {file_path}")
            if len(preview.sample_included_files) > 20:
                console.print(f"  ... and {len(preview.sample_included_files) - 20} more")

        # Show excluded files
        if preview.sample_excluded_files:
            console.print(f"\n[bold red]Excluded Files ({len(preview.sample_excluded_files)}):[/bold red]")
            for file_path in preview.sample_excluded_files[:20]:  # Show first 20
                console.print(f"  - {file_path}")
            if len(preview.sample_excluded_files) > 20:
                console.print(f"  ... and {len(preview.sample_excluded_files) - 20} more")

        console.print()

    except TemplateNotFoundError as e:
        _show_error("Not Found", str(e))
        raise typer.Exit(1)
    except SelectionError as e:
        _show_error("Selection Error", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Test Failed", f"Failed to test selection template: {e}")
        logger.exception("Failed to test selection template")
        raise typer.Exit(1)


@selections_app.command("export")
def export_selection(
        name: Annotated[str, typer.Argument(help="Name of the selection template")],
        output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path")] = None,
        format: Annotated[str, typer.Option("--format", "-f", help="Export format (json or yaml)")] = "json",
) -> None:
    """
    Export a selection template to a file.
    
    Examples:
        timelocker selections export documents
        timelocker selections export documents --output ~/backup-config/documents.json
        timelocker selections export code --format yaml --output code-selection.yaml
    """
    try:
        format_normalized = (format or "json").lower()
        if format_normalized not in SUPPORTED_SERIALIZATION_FORMATS:
            supported = ", ".join(SUPPORTED_SERIALIZATION_FORMATS)
            _show_error(
                    "Export Failed",
                    f"Unsupported format '{format}'.",
                    f"Accepted formats: {supported}. Try --format {SUPPORTED_SERIALIZATION_FORMATS[0]} "
                    f"or --format {SUPPORTED_SERIALIZATION_FORMATS[1]}."
            )
            raise typer.Exit(1)

        template_manager = SelectionTemplateManager()
        templates = asyncio.run(template_manager.list_templates())

        # Find template by name
        template = next((t for t in templates if t.name == name), None)
        if not template:
            _show_error("Not Found", f"Selection template '{name}' not found")
            raise typer.Exit(1)

        # Determine output path
        if output is None:
            output_path = Path(f"{name}.{format_normalized}")
        else:
            output_path = Path(output)

        if not output_path.suffix:
            output_path = output_path.with_suffix(f".{format_normalized}")

        # Export template directly to file
        exported_path = asyncio.run(
                template_manager.export_template(
                        template.id,
                        output_path=output_path,
                        format=format_normalized
                )
        )

        _show_success(
                "Selection Exported",
                f"Selection template '{name}' exported to {exported_path}"
        )
        typer.echo(f"Selection template '{name}' exported to {exported_path}")

    except TemplateNotFoundError as e:
        _show_error("Not Found", str(e))
        raise typer.Exit(1)
    except TemplateExportError as e:
        _show_error("Export Error", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Export Failed", f"Failed to export selection template: {e}")
        logger.exception("Failed to export selection template")
        raise typer.Exit(1)


@selections_app.command("import")
def import_selection(
        file: Annotated[Path, typer.Argument(help="File to import from")],
        format: Annotated[str, typer.Option("--format", "-f", help="Import format (json or yaml)")] = "json",
        merge: Annotated[str, typer.Option("--merge", help="Merge strategy (skip, overwrite, rename)")] = "skip",
) -> None:
    """
    Import selection templates from a file.
    
    Examples:
        timelocker selections import documents.json
        timelocker selections import backup-config.yaml --format yaml
        timelocker selections import templates.json --merge overwrite
    """
    try:
        if not file.exists():
            _show_error("File Not Found", f"Import file does not exist: {file}")
            raise typer.Exit(1)

        format_normalized = (format or "json").lower()
        if format_normalized not in SUPPORTED_SERIALIZATION_FORMATS:
            supported = ", ".join(SUPPORTED_SERIALIZATION_FORMATS)
            _show_error(
                    "Import Error",
                    f"Unsupported format '{format}'.",
                    f"Accepted formats: {supported}. Try --format {SUPPORTED_SERIALIZATION_FORMATS[0]} "
                    f"or --format {SUPPORTED_SERIALIZATION_FORMATS[1]}."
            )
            raise typer.Exit(1)

        # Import templates (SelectionTemplateManager auto-detects based on file extension)
        template_manager = SelectionTemplateManager()
        result = asyncio.run(
                template_manager.import_template(
                        file,
                        merge_strategy=merge,
                        validate=True
                )
        )

        # Display results
        console = _get_console()
        if result.success:
            _show_success(
                    "Import Complete",
                    f"Imported {result.imported_count} template(s)\n"
                    f"Skipped: {result.skipped_count}\n"
                    f"Failed: {result.failed_count}"
            )
            typer.echo(
                    f"Imported {result.imported_count} template(s); "
                    f"skipped {result.skipped_count}; "
                    f"failed {result.failed_count}"
            )

            if result.warnings:
                console.print("\n[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")
        else:
            _show_error(
                    "Import Failed",
                    f"Failed to import templates\n"
                    f"Errors: {len(result.errors)}"
            )

            if result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in result.errors:
                    console.print(f"  • {error}")

            raise typer.Exit(1)

    except TemplateImportError as e:
        _show_error("Import Error", str(e))
        raise typer.Exit(1)
    except Exception as e:
        _show_error("Import Failed", f"Failed to import selection templates: {e}")
        logger.exception("Failed to import selection templates")
        raise typer.Exit(1)
