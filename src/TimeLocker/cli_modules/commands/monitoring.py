"""
Monitoring and reporting operations.

This module contains CLI commands for system monitoring, health checks,
statistics, logging, and report generation.
"""

import sys
import logging
import json
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import from base module
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_manager_for_command,
    _create_configuration_module,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Create Typer apps
monitor_app = create_typer_app(
    name="monitor",
    help_text="System monitoring operations"
)

logs_app = create_typer_app(
    name="logs",
    help_text="Log viewing and management"
)

reports_app = create_typer_app(
    name="reports",
    help_text="Report generation"
)


# Helper functions

def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _get_system_health_data(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Get system health data."""
    try:
        service_manager = _get_service_manager_for_command(config_dir)
        config_module = _create_configuration_module(config_dir)
        
        # Get repositories
        repositories = config_module.list_repositories()
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "repositories": {
                "total": len(repositories),
                "healthy": 0,
                "warning": 0,
                "error": 0,
            },
            "recent_backups": {
                "successful": 0,
                "failed": 0,
                "last_24h": 0,
            },
            "storage": {
                "total_size": 0,
                "repositories": []
            }
        }
        
        # Check repository health
        for repo in repositories:
            repo_name = repo.get('name', '')
            try:
                # Try to get repository stats
                stats = service_manager.get_repository_stats(repo_name)
                if stats:
                    health_data["repositories"]["healthy"] += 1
                    health_data["storage"]["total_size"] += stats.get('total_size', 0)
                    health_data["storage"]["repositories"].append({
                        "name": repo_name,
                        "size": stats.get('total_size', 0),
                        "snapshots": stats.get('snapshots_count', 0)
                    })
                else:
                    health_data["repositories"]["warning"] += 1
            except Exception:
                health_data["repositories"]["error"] += 1
        
        return health_data
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to get system health data: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# Monitor Commands

@monitor_app.command("health")
@with_error_handling("Health Check Error")
@with_logging
def monitor_health(
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Check system health and connectivity across all repositories."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking system health...", total=None)
            health_data = _get_system_health_data(config_dir)
            progress.update(task, completed=True)
        
        if json_output:
            console.print(json.dumps(health_data, indent=2))
        else:
            if "error" in health_data:
                show_error_panel("Health Check Failed", health_data["error"])
                raise typer.Exit(1)
            
            # Display health summary
            repos = health_data.get("repositories", {})
            total = repos.get("total", 0)
            healthy = repos.get("healthy", 0)
            warning = repos.get("warning", 0)
            error = repos.get("error", 0)
            
            # Determine overall status
            if error > 0:
                status = "[red]Degraded[/red]"
                status_icon = "⚠️"
            elif warning > 0:
                status = "[yellow]Warning[/yellow]"
                status_icon = "⚠️"
            else:
                status = "[green]Healthy[/green]"
                status_icon = "✓"
            
            console.print(Panel(
                f"{status_icon} [bold]Overall Status:[/bold] {status}\n\n"
                f"[bold]Repositories:[/bold]\n"
                f"  Total: {total}\n"
                f"  [green]Healthy:[/green] {healthy}\n"
                f"  [yellow]Warning:[/yellow] {warning}\n"
                f"  [red]Error:[/red] {error}\n\n"
                f"[bold]Storage:[/bold]\n"
                f"  Total Size: {_format_size(health_data.get('storage', {}).get('total_size', 0))}",
                title="[bold cyan]System Health[/bold cyan]",
                border_style="cyan"
            ))
            
            if verbose and health_data.get("storage", {}).get("repositories"):
                console.print("\n[bold]Repository Details:[/bold]")
                table = Table()
                table.add_column("Repository", style="cyan")
                table.add_column("Size", style="green")
                table.add_column("Snapshots", style="yellow")
                
                for repo in health_data["storage"]["repositories"]:
                    table.add_row(
                        repo["name"],
                        _format_size(repo["size"]),
                        str(repo["snapshots"])
                    )
                
                console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Health Check Error")


@monitor_app.command("stats")
@with_error_handling("Statistics Error")
@with_logging
def monitor_stats(
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Display statistics summary across all repositories."""
    try:
        service_manager = _get_service_manager_for_command(config_dir)
        config_module = _create_configuration_module(config_dir)
        
        if repository:
            # Get stats for specific repository
            stats = service_manager.get_repository_stats(repository)
            
            if json_output:
                console.print(json.dumps(stats, indent=2, default=str))
            else:
                console.print(Panel(
                    f"[bold]Repository:[/bold] {repository}\n"
                    f"[bold]Total Size:[/bold] {_format_size(stats.get('total_size', 0))}\n"
                    f"[bold]Snapshots:[/bold] {stats.get('snapshots_count', 0)}\n"
                    f"[bold]Total Files:[/bold] {stats.get('total_files', 0)}\n"
                    f"[bold]Total Blobs:[/bold] {stats.get('total_blobs', 0)}\n"
                    f"[bold]Compression Ratio:[/bold] {stats.get('compression_ratio', 0):.2f}",
                    title=f"[bold green]Repository Statistics: {repository}[/bold green]",
                    border_style="green"
                ))
        else:
            # Get stats for all repositories
            repositories = config_module.list_repositories()
            
            if json_output:
                all_stats = {}
                for repo in repositories:
                    repo_name = repo.get('name', '')
                    try:
                        all_stats[repo_name] = service_manager.get_repository_stats(repo_name)
                    except Exception as e:
                        all_stats[repo_name] = {"error": str(e)}
                console.print(json.dumps(all_stats, indent=2, default=str))
            else:
                if not repositories:
                    show_info_panel("No Repositories", "No repositories configured.")
                    return
                
                table = Table(title="Repository Statistics")
                table.add_column("Repository", style="cyan")
                table.add_column("Size", style="green")
                table.add_column("Snapshots", style="yellow")
                table.add_column("Files", style="white")
                table.add_column("Status", style="magenta")
                
                for repo in repositories:
                    repo_name = repo.get('name', '')
                    try:
                        stats = service_manager.get_repository_stats(repo_name)
                        table.add_row(
                            repo_name,
                            _format_size(stats.get('total_size', 0)),
                            str(stats.get('snapshots_count', 0)),
                            str(stats.get('total_files', 0)),
                            "[green]✓[/green]"
                        )
                    except Exception as e:
                        table.add_row(
                            repo_name,
                            "N/A",
                            "N/A",
                            "N/A",
                            "[red]✗[/red]"
                        )
                
                console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Statistics Error")


# Logs Commands

@logs_app.command("view")
@with_error_handling("Log View Error")
@with_logging
def logs_view(
    lines: Annotated[int, typer.Option("--lines", "-n", help="Number of lines to show")] = 50,
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow log output")] = False,
    level: Annotated[Optional[str], typer.Option("--level", "-l", help="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")] = None,
    component: Annotated[Optional[str], typer.Option("--component", "-c", help="Filter by component")] = None,
    since: Annotated[Optional[str], typer.Option("--since", help="Show logs since time (e.g., '1h', '30m', '2024-01-01')")] = None,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """View TimeLocker logs with filtering options."""
    try:
        from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
        
        # Get log file path
        log_dir = ConfigurationPathResolver.get_cache_directory() / "logs"
        log_file = log_dir / "timelocker.log"
        
        if not log_file.exists():
            show_info_panel("No Logs", f"Log file not found: {log_file}")
            return
        
        # Read log file
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        # Filter by level
        if level:
            level = level.upper()
            log_lines = [line for line in log_lines if level in line]
        
        # Filter by component
        if component:
            log_lines = [line for line in log_lines if component in line]
        
        # Filter by time
        if since:
            # Parse since parameter
            now = datetime.now()
            if since.endswith('h'):
                hours = int(since[:-1])
                since_time = now - timedelta(hours=hours)
            elif since.endswith('m'):
                minutes = int(since[:-1])
                since_time = now - timedelta(minutes=minutes)
            elif since.endswith('d'):
                days = int(since[:-1])
                since_time = now - timedelta(days=days)
            else:
                try:
                    since_time = datetime.fromisoformat(since)
                except ValueError:
                    show_error_panel("Invalid Time Format", f"Invalid time format: {since}")
                    raise typer.Exit(1)
            
            # Filter lines by timestamp
            filtered_lines = []
            for line in log_lines:
                try:
                    # Extract timestamp from log line (assuming format: YYYY-MM-DD HH:MM:SS)
                    timestamp_str = line[:19]
                    line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    if line_time >= since_time:
                        filtered_lines.append(line)
                except (ValueError, IndexError):
                    # If we can't parse timestamp, include the line
                    filtered_lines.append(line)
            log_lines = filtered_lines
        
        # Get last N lines
        log_lines = log_lines[-lines:]
        
        # Display logs
        console.print(f"[bold]TimeLocker Logs[/bold] (showing last {len(log_lines)} lines)\n")
        
        for line in log_lines:
            # Color code by level
            if 'ERROR' in line or 'CRITICAL' in line:
                console.print(f"[red]{line.rstrip()}[/red]")
            elif 'WARNING' in line:
                console.print(f"[yellow]{line.rstrip()}[/yellow]")
            elif 'DEBUG' in line:
                console.print(f"[dim]{line.rstrip()}[/dim]")
            else:
                console.print(line.rstrip())
        
        if follow:
            console.print("\n[cyan]Following log output (Ctrl+C to stop)...[/cyan]")
            # Note: Real follow implementation would require tail -f equivalent
            show_info_panel("Follow Mode", "Follow mode not yet implemented. Use 'tail -f' on the log file directly.")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Log View Error")


@logs_app.command("clear")
@with_error_handling("Log Clear Error")
@with_logging
def logs_clear(
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Clear TimeLocker logs."""
    try:
        from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
        
        # Get log file path
        log_dir = ConfigurationPathResolver.get_cache_directory() / "logs"
        log_file = log_dir / "timelocker.log"
        
        if not log_file.exists():
            show_info_panel("No Logs", "No log file to clear.")
            return
        
        if not yes and CommandBase.is_interactive():
            confirmed = Confirm.ask("Clear all TimeLocker logs?", default=False)
            if not confirmed:
                show_info_panel("Operation Cancelled", "Log clearing cancelled.")
                return
        
        # Clear log file
        with open(log_file, 'w') as f:
            f.write('')
        
        show_success_panel("Logs Cleared", "TimeLocker logs have been cleared.")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Log Clear Error")


# Reports Commands

@reports_app.command("generate")
@with_error_handling("Report Generation Error")
@with_logging
def reports_generate(
    report_type: Annotated[str, typer.Argument(help="Report type (backup-history, storage-usage, performance)")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (json, html, text)")] = "text",
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days to include")] = 30,
    repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Generate backup history, storage usage, or performance reports."""
    try:
        service_manager = _get_service_manager_for_command(config_dir)
        config_module = _create_configuration_module(config_dir)
        
        report_type = report_type.lower()
        
        if report_type not in ['backup-history', 'storage-usage', 'performance']:
            show_error_panel("Invalid Report Type", f"Unknown report type: {report_type}")
            raise typer.Exit(1)
        
        console.print(f"\n[bold]Generating {report_type} report...[/bold]\n")
        
        # Generate report data
        report_data = {
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "repository_filter": repository,
        }
        
        if report_type == "backup-history":
            # Get backup history
            repositories = [repository] if repository else [r.get('name') for r in config_module.list_repositories()]
            
            history = []
            for repo_name in repositories:
                try:
                    snapshots = service_manager.snapshot_service.list_snapshots(repo_name)
                    # Filter by date
                    cutoff_date = datetime.now() - timedelta(days=days)
                    recent_snapshots = [
                        s for s in snapshots
                        if datetime.fromisoformat(s.get('time', '1970-01-01')) >= cutoff_date
                    ]
                    history.append({
                        "repository": repo_name,
                        "snapshots": len(recent_snapshots),
                        "total_size": sum(s.get('size', 0) for s in recent_snapshots)
                    })
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to get history for {repo_name}: {e}")
            
            report_data["backup_history"] = history
            
        elif report_type == "storage-usage":
            # Get storage usage
            repositories = [repository] if repository else [r.get('name') for r in config_module.list_repositories()]
            
            usage = []
            for repo_name in repositories:
                try:
                    stats = service_manager.get_repository_stats(repo_name)
                    usage.append({
                        "repository": repo_name,
                        "total_size": stats.get('total_size', 0),
                        "snapshots": stats.get('snapshots_count', 0),
                        "files": stats.get('total_files', 0),
                        "compression_ratio": stats.get('compression_ratio', 0)
                    })
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Failed to get usage for {repo_name}: {e}")
            
            report_data["storage_usage"] = usage
            
        elif report_type == "performance":
            # Get performance metrics
            try:
                from TimeLocker.performance.metrics import PerformanceMetrics
                metrics = PerformanceMetrics()
                report_data["performance_metrics"] = metrics.get_summary()
            except Exception as e:
                report_data["performance_metrics"] = {"error": str(e)}
        
        # Output report
        if format == "json":
            output_text = json.dumps(report_data, indent=2, default=str)
        elif format == "html":
            # Simple HTML report
            output_text = f"""<!DOCTYPE html>
<html>
<head>
    <title>TimeLocker Report - {report_type}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>TimeLocker Report: {report_type}</h1>
    <p>Generated: {report_data['generated_at']}</p>
    <p>Period: {days} days</p>
    <pre>{json.dumps(report_data, indent=2, default=str)}</pre>
</body>
</html>"""
        else:
            # Text format
            output_text = f"TimeLocker Report: {report_type}\n"
            output_text += f"Generated: {report_data['generated_at']}\n"
            output_text += f"Period: {days} days\n"
            output_text += "\n" + json.dumps(report_data, indent=2, default=str)
        
        # Save or display
        if output:
            with open(output, 'w') as f:
                f.write(output_text)
            show_success_panel(
                "Report Generated",
                f"Report saved to {output}",
                details={
                    "Type": report_type,
                    "Format": format,
                    "Period": f"{days} days",
                }
            )
        else:
            console.print(output_text)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Report Generation Error")


__all__ = ['monitor_app', 'logs_app', 'reports_app']
