"""Display utilities for CLI output."""

from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel

# Initialize Rich console for consistent output
console = Console(width=100)


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
            padding=(1, 2),
            width=100
    )
    console.print(panel)

    summary = f"{title}: {message}"
    if details:
        summary += " | " + " | ".join(details)
    typer.echo(summary)


def show_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    panel = Panel(
            f"ℹ️  {message}",
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
            padding=(1, 2)
    )
    console.print(panel)
