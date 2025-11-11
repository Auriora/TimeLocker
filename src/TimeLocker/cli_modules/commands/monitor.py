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

"""
CLI Monitoring Commands

This module provides CLI commands for viewing logs, status, and monitoring information.
It integrates with the Integration Architecture to provide monitoring data to the CLI
service manager.

Requirements addressed:
- 8.1: CLI commands for viewing logs, status, and monitoring information
- 8.2: Integration with Integration Architecture for monitoring data
- 8.4: Fallback mechanisms and error reporting for CLI monitoring operations
- 8.5: CLI status feedback and monitoring information display
"""

import logging
from typing import Optional, Annotated
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()

# Create monitor app
monitor_app = typer.Typer(
    help="Monitoring and status commands",
    no_args_is_help=True
)


def _get_service_manager():
    """Get CLI service manager instance with fallback error handling."""
    try:
        from ...cli_services import get_cli_service_manager
        return get_cli_service_manager()
    except Exception as e:
        console.print(f"[red]Error: Failed to initialize service manager: {e}[/red]")
        raise typer.Exit(1)


def _format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_timestamp


@monitor_app.command("status")
def monitor_status(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed status information")] = False
):
    """
    Show current system monitoring status.
    
    Displays overall system health, current operations, and recent activity summary.
    
    Examples:
        timelocker monitor status
        timelocker monitor status --verbose
    
    Requirements: 8.1, 8.3, 8.5
    """
    try:
        service_manager = _get_service_manager()
        
        # Get system status
        status = service_manager.get_system_monitoring_status()
        
        if 'error' in status:
            console.print(f"[red]Error getting system status: {status['error']}[/red]")
            raise typer.Exit(1)
        
        # Display health status
        health = status.get('health_status', 'unknown')
        health_colors = {
            'healthy': 'green',
            'warning': 'yellow',
            'error': 'red',
            'unknown': 'dim'
        }
        health_color = health_colors.get(health, 'dim')
        
        console.print(Panel(
            f"[{health_color}]System Health: {health.upper()}[/{health_color}]",
            title="TimeLocker Monitoring Status",
            border_style=health_color
        ))
        
        # Display current operations
        current_ops = status.get('current_operations', 0)
        if current_ops > 0:
            console.print(f"\n[yellow]⚡ {current_ops} operation(s) currently running[/yellow]")
        else:
            console.print("\n[dim]No operations currently running[/dim]")
        
        # Display recent activity
        recent_ops = status.get('recent_operations_24h', 0)
        console.print(f"\n📊 Recent Activity (24 hours): {recent_ops} operations")
        
        # Display status counts
        if verbose:
            status_counts = status.get('status_counts', {})
            if status_counts:
                console.print("\n[bold]Operation Status Breakdown:[/bold]")
                
                table = Table(show_header=True, header_style="bold")
                table.add_column("Status", style="cyan")
                table.add_column("Count", justify="right")
                
                status_display = {
                    'success': ('✅ Success', 'green'),
                    'warning': ('⚠️  Warning', 'yellow'),
                    'error': ('❌ Error', 'red'),
                    'critical': ('🚨 Critical', 'red bold')
                }
                
                for status_key, (label, style) in status_display.items():
                    count = status_counts.get(status_key, 0)
                    table.add_row(f"[{style}]{label}[/{style}]", str(count))
                
                console.print(table)
        
        # Display timestamp
        timestamp = status.get('timestamp', '')
        if timestamp:
            console.print(f"\n[dim]Last updated: {_format_timestamp(timestamp)}[/dim]")
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("operations")
def monitor_operations(
    operation_id: Annotated[Optional[str], typer.Argument(help="Specific operation ID to query")] = None
):
    """
    Show currently running operations or details of a specific operation.
    
    Examples:
        timelocker monitor operations
        timelocker monitor operations abc123
    
    Requirements: 8.1, 8.3, 8.5
    """
    try:
        service_manager = _get_service_manager()
        
        if operation_id:
            # Show specific operation
            status = service_manager.get_cli_operation_status(operation_id)
            
            if not status:
                console.print(f"[yellow]Operation '{operation_id}' not found[/yellow]")
                raise typer.Exit(1)
            
            # Display operation details
            console.print(Panel(
                f"[bold]{status['operation_type'].upper()}[/bold]",
                title=f"Operation: {operation_id}",
                border_style="cyan"
            ))
            
            console.print(f"\n[bold]Status:[/bold] {status['status']}")
            console.print(f"[bold]Message:[/bold] {status['message']}")
            
            if status.get('repository_id'):
                console.print(f"[bold]Repository:[/bold] {status['repository_id']}")
            
            if status.get('progress') is not None:
                progress = status['progress']
                console.print(f"\n[bold]Progress:[/bold] {progress}%")
                
                # Show progress bar
                bar_width = 40
                filled = int(bar_width * progress / 100)
                bar = "█" * filled + "░" * (bar_width - filled)
                console.print(f"[cyan]{bar}[/cyan]")
            
            if status.get('files_processed') and status.get('total_files'):
                console.print(f"[bold]Files:[/bold] {status['files_processed']}/{status['total_files']}")
            
            if status.get('estimated_completion'):
                completion = _format_timestamp(status['estimated_completion'])
                console.print(f"[bold]Estimated Completion:[/bold] {completion}")
            
            timestamp = _format_timestamp(status['timestamp'])
            console.print(f"\n[dim]Last updated: {timestamp}[/dim]")
            
        else:
            # Show all current operations
            operations = service_manager.get_cli_current_operations()
            
            if not operations:
                console.print("[dim]No operations currently running[/dim]")
                return
            
            console.print(f"\n[bold]Current Operations ({len(operations)}):[/bold]\n")
            
            for op in operations:
                status_colors = {
                    'success': 'green',
                    'warning': 'yellow',
                    'error': 'red',
                    'critical': 'red bold',
                    'info': 'cyan'
                }
                status_color = status_colors.get(op['status'], 'dim')
                
                console.print(f"[{status_color}]●[/{status_color}] {op['operation_id']}")
                console.print(f"  Type: {op['operation_type']}")
                console.print(f"  Status: {op['status']}")
                console.print(f"  Message: {op['message']}")
                
                if op.get('progress') is not None:
                    console.print(f"  Progress: {op['progress']}%")
                
                if op.get('repository_id'):
                    console.print(f"  Repository: {op['repository_id']}")
                
                console.print()
        
    except Exception as e:
        logger.error(f"Failed to get operations: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("logs")
def monitor_logs(
    hours: Annotated[Optional[int], typer.Option("--hours", "-h", help="Number of hours to look back")] = None,
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of days to look back")] = 1,
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
    level: Annotated[Optional[str], typer.Option("--level", "-l", help="Filter by log level (info, warning, error)")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Limit number of results")] = 50,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed log information")] = False
):
    """
    View monitoring logs with filtering options.
    
    Examples:
        timelocker monitor logs
        timelocker monitor logs --hours 6
        timelocker monitor logs --days 7 --level error
        timelocker monitor logs --repository myrepo --verbose
    
    Requirements: 8.1, 8.2
    """
    try:
        service_manager = _get_service_manager()
        
        # Get logs with filters
        logs = service_manager.get_cli_monitoring_logs(
            hours=hours,
            days=days,
            repository_id=repository,
            log_level=level,
            limit=limit
        )
        
        if not logs:
            console.print("[dim]No logs found matching the specified filters[/dim]")
            return
        
        console.print(f"\n[bold]Monitoring Logs ({len(logs)} entries):[/bold]\n")
        
        # Get monitoring integration for formatting
        monitoring_integration = service_manager.get_monitoring_integration()
        
        for log in logs:
            if monitoring_integration:
                formatted = monitoring_integration.format_log_entry_cli(log, verbose=verbose)
                console.print(formatted)
            else:
                # Fallback formatting
                timestamp = _format_timestamp(log['timestamp'])
                level_str = log['level'].upper()
                console.print(f"[{level_str}] {timestamp} - {log['message']}")
            
            console.print()
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("search")
def monitor_search(
    query: Annotated[str, typer.Argument(help="Search query string")],
    hours: Annotated[Optional[int], typer.Option("--hours", "-h", help="Number of hours to look back")] = None,
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of days to look back")] = 7,
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Limit number of results")] = 50
):
    """
    Search monitoring logs for specific text.
    
    Examples:
        timelocker monitor search "backup failed"
        timelocker monitor search "error" --days 7
        timelocker monitor search "permission" --repository myrepo
    
    Requirements: 8.2
    """
    try:
        service_manager = _get_service_manager()
        
        # Search logs
        logs = service_manager.search_monitoring_logs(
            query=query,
            hours=hours,
            days=days,
            repository_id=repository,
            limit=limit
        )
        
        if not logs:
            console.print(f"[dim]No logs found matching '{query}'[/dim]")
            return
        
        console.print(f"\n[bold]Search Results for '{query}' ({len(logs)} matches):[/bold]\n")
        
        # Get monitoring integration for formatting
        monitoring_integration = service_manager.get_monitoring_integration()
        
        for log in logs:
            if monitoring_integration:
                formatted = monitoring_integration.format_log_entry_cli(log, verbose=True)
                console.print(formatted)
            else:
                # Fallback formatting
                timestamp = _format_timestamp(log['timestamp'])
                level_str = log['level'].upper()
                console.print(f"[{level_str}] {timestamp} - {log['message']}")
            
            console.print()
        
    except Exception as e:
        logger.error(f"Failed to search logs: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("history")
def monitor_history(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of days to look back")] = 7,
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter by status (success, failed, partial)")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="Limit number of results")] = 20
):
    """
    View backup operation history.
    
    Examples:
        timelocker monitor history
        timelocker monitor history --days 30
        timelocker monitor history --repository myrepo --status failed
    
    Requirements: 8.1
    """
    try:
        service_manager = _get_service_manager()
        
        # Get backup history
        history = service_manager.get_cli_backup_history(
            days=days,
            repository_id=repository,
            status=status,
            limit=limit
        )
        
        if not history:
            console.print("[dim]No backup history found matching the specified filters[/dim]")
            return
        
        console.print(f"\n[bold]Backup History ({len(history)} operations):[/bold]\n")
        
        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Repository")
        table.add_column("Status")
        table.add_column("Files", justify="right")
        table.add_column("Data", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Throughput", justify="right")
        
        for record in history:
            # Format status with color
            status_val = record['status']
            status_colors = {
                'success': 'green',
                'partial': 'yellow',
                'failed': 'red',
                'cancelled': 'dim'
            }
            status_color = status_colors.get(status_val, 'dim')
            status_display = f"[{status_color}]{status_val}[/{status_color}]"
            
            # Format timestamp
            start_time = _format_timestamp(record['start_time'])
            
            table.add_row(
                start_time,
                record['repository_id'],
                status_display,
                str(record['files_processed']),
                record['bytes_transferred_formatted'],
                record['duration'],
                f"{record['throughput_mbps']} MB/s"
            )
        
        console.print(table)
        
    except Exception as e:
        logger.error(f"Failed to get backup history: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# Export the app
__all__ = ['monitor_app']
