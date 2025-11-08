"""
Security management commands.

This module contains CLI commands for security management commands.
Extracted from cli.py using automation script.
"""

import sys
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Import from base module (Phase 3 patterns)
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_configuration_module,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import from TimeLocker package
from TimeLocker import cli as _cli_module
from TimeLocker.cli_services import get_cli_service_manager

# Module-specific imports
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    AccessManager,
    RepositoryInfo,
    RepositoryMode,
    ConfirmationDialogs
)
from TimeLocker.completion import repository_completer
from datetime import datetime, timedelta

# Create Typer app
security_app = create_typer_app(
    name="security",
    help_text="Security management commands"
)



# Commands

@security_app.command("audit")
@with_error_handling("Audit Error")
@with_logging
def security_audit(
        days: Annotated[int, typer.Option("--days", "-d", help="Number of days to audit")] = 30,
        repository: Annotated[Optional[str], typer.Option("--repository", "-r", help="Filter by repository")] = None,
        event_type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by event type")] = None,
        json_output: JsonOption = False,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """Show security audit trail and compliance information."""
    try:
        # Initialize security service
        from TimeLocker.security import CredentialManager
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(credential_manager, config_dir=config_dir)

        # Get audit data
        audit_data = security_service.get_security_audit(
            days=days,
            repository_id=repository,
            event_type=event_type
        )

        if json_output:
            import json
            console.print(json.dumps(audit_data, indent=2, default=str))
        else:
            # Display audit summary
            console.print(Panel(
                f"[bold]Audit Period:[/bold] Last {days} days\n"
                f"[bold]Total Events:[/bold] {audit_data.get('total_events', 0)}\n"
                f"[bold]Critical Events:[/bold] {audit_data.get('critical_events', 0)}\n"
                f"[bold]Failed Access Attempts:[/bold] {audit_data.get('failed_access_attempts', 0)}\n"
                f"[bold]Repositories Accessed:[/bold] {audit_data.get('repositories_accessed', 0)}",
                title="[bold green]Security Audit Summary[/bold green]",
                border_style="green"
            ))

            # Display event breakdown
            events_by_type = audit_data.get('events_by_type', {})
            if events_by_type:
                console.print("\n[bold]Events by Type:[/bold]")
                table = Table()
                table.add_column("Event Type", style="cyan")
                table.add_column("Count", style="green")
                
                for event_type, count in sorted(events_by_type.items(), key=lambda x: x[1], reverse=True):
                    table.add_row(event_type.replace('_', ' ').title(), str(count))
                
                console.print(table)

            # Display compliance status
            compliance = audit_data.get('compliance_status', {})
            if compliance:
                console.print("\n[bold]Compliance Status:[/bold]")
                for check, status in compliance.items():
                    status_icon = "✓" if status else "✗"
                    status_color = "green" if status else "red"
                    console.print(f"  [{status_color}]{status_icon}[/{status_color}] {check.replace('_', ' ').title()}")

    except Exception as e:
        CommandBase.handle_error(e, verbose, "Security Audit Error")


@security_app.command("status")
@with_error_handling("Status Error")
@with_logging
def security_status(
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """Display security status and summary."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security components
        from .security import CredentialManager, AccessManager
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(credential_manager, config_dir=config_dir)
        access_manager = AccessManager(config_dir=config_dir)

        # Get security status
        security_status_info = security_service.get_security_summary(days=7)
        access_status = access_manager.get_security_status()
        protection_status = security_service.get_repository_protection_status()

        # Display status table
        table = Table(title="Security Status Overview")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")

        # Access Manager Status
        active_sessions = access_status.get('active_sessions', 0)
        locked_users = access_status.get('locked_users', 0)
        session_status = "Active" if active_sessions > 0 else "Idle"
        session_color = "green" if locked_users == 0 else "yellow"
        table.add_row(
            "Session Management",
            f"[{session_color}]{session_status}[/{session_color}]",
            f"{active_sessions} active sessions, {locked_users} locked users"
        )

        # Security Events
        total_events = security_status_info.get('total_events', 0)
        events_by_level = security_status_info.get('events_by_level', {})
        critical_events = events_by_level.get('critical', 0)
        high_events = events_by_level.get('high', 0)
        
        event_status = "Normal"
        event_color = "green"
        if critical_events > 0:
            event_status = "Critical Issues"
            event_color = "red"
        elif high_events > 0:
            event_status = "Warnings"
            event_color = "yellow"

        table.add_row(
            "Security Events (7 days)",
            f"[{event_color}]{event_status}[/{event_color}]",
            f"{total_events} total events, {critical_events} critical, {high_events} high"
        )

        # Repository Protection
        protected_repos = protection_status.get('protected_repositories', 0)
        locked_repos = protection_status.get('locked_repositories', 0)
        protection_color = "green" if locked_repos == 0 else "yellow"
        table.add_row(
            "Repository Protection",
            f"[{protection_color}]Active[/{protection_color}]",
            f"{protected_repos} protected, {locked_repos} locked"
        )

        console.print(table)

        if verbose:
            # Show detailed information
            console.print("\n[bold]Detailed Security Information[/bold]")
            
            # Access Manager Details
            console.print(f"\n[cyan]Access Manager:[/cyan]")
            console.print(f"  Session Timeout: {access_status.get('session_timeout_minutes', 30)} minutes")
            console.print(f"  Max Failed Attempts: {access_status.get('max_failed_attempts', 3)}")
            console.print(f"  Lockout Duration: {access_status.get('lockout_duration_minutes', 15)} minutes")
            console.print(f"  Config Directory: {access_status.get('config_directory', 'Unknown')}")

            # Recent Events by Type
            events_by_type = security_status_info.get('events_by_type', {})
            if events_by_type:
                console.print(f"\n[cyan]Recent Security Events by Type:[/cyan]")
                for event_type, count in events_by_type.items():
                    console.print(f"  {event_type}: {count}")

    except Exception as e:
        show_error_panel("Security Status Error", f"Failed to get security status: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@security_app.command("logs")
@with_error_handling("Logs Error")
@with_logging
def security_logs(
        days: Annotated[int, typer.Option("--days", "-d", help="Number of days to show")] = 7,
        event_type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by event type")] = None,
        level: Annotated[Optional[str], typer.Option("--level", "-l", help="Filter by security level")] = None,
        limit: Annotated[Optional[int], typer.Option("--limit", help="Maximum number of entries")] = 50,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """View security logs with filtering options."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security service
        from .security import CredentialManager
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(credential_manager, config_dir=config_dir)

        # Get security logs
        logs = security_service.get_security_logs(
            days=days,
            event_type=event_type,
            level=level,
            limit=limit
        )

        if not logs:
            show_info_panel("Security Logs", f"No security events found in the last {days} days.")
            return

        # Display logs in a table
        table = Table(title=f"Security Logs (Last {days} days)")
        table.add_column("Timestamp", style="cyan", no_wrap=True)
        table.add_column("Level", style="yellow", width=8)
        table.add_column("Type", style="blue", width=15)
        table.add_column("Description", style="white")
        
        if verbose:
            table.add_column("Repository", style="green", width=12)
            table.add_column("User", style="magenta", width=10)

        for log_entry in logs:
            timestamp = log_entry.get('timestamp', '')
            if timestamp:
                # Format timestamp for display
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp_str = dt.strftime('%m-%d %H:%M:%S')
                except:
                    timestamp_str = timestamp[:16]  # Fallback
            else:
                timestamp_str = 'Unknown'

            level_str = log_entry.get('level', 'unknown').upper()
            event_type_str = log_entry.get('event_type', 'unknown').replace('_', ' ').title()
            description = log_entry.get('description', '')

            # Color code levels
            level_colors = {
                'CRITICAL': 'red',
                'HIGH': 'yellow', 
                'MEDIUM': 'blue',
                'LOW': 'green'
            }
            level_color = level_colors.get(level_str, 'white')
            level_display = f"[{level_color}]{level_str}[/{level_color}]"

            if verbose:
                repository_id = log_entry.get('repository_id', '')[:12] if log_entry.get('repository_id') else ''
                user_id = log_entry.get('user_id', '')[:10] if log_entry.get('user_id') else ''
                table.add_row(timestamp_str, level_display, event_type_str, description, repository_id, user_id)
            else:
                table.add_row(timestamp_str, level_display, event_type_str, description)

        console.print(table)
        console.print(f"\n[dim]Showing {len(logs)} of {len(logs)} events[/dim]")

    except Exception as e:
        show_error_panel("Security Logs Error", f"Failed to retrieve security logs: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@security_app.command("notifications")
@with_error_handling("Notifications Error")
@with_logging
def security_notifications(
        hours: Annotated[int, typer.Option("--hours", "-h", help="Number of hours to show")] = 24,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """View recent security notifications."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize security service
        from .security import CredentialManager
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(credential_manager, config_dir=config_dir)

        # Get security notifications
        notifications = security_service.get_security_notifications(hours=hours)

        if not notifications:
            show_info_panel("Security Notifications", f"No security notifications in the last {hours} hours.")
            return

        # Display notifications
        console.print(f"[bold]Security Notifications (Last {hours} hours)[/bold]\n")

        for notification in notifications:
            timestamp = notification.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = timestamp

            level = notification.get('level', 'medium').upper()
            message = notification.get('message', '')
            details = notification.get('details', '')

            # Color code by level
            level_colors = {
                'CRITICAL': 'red',
                'HIGH': 'yellow',
                'MEDIUM': 'blue', 
                'LOW': 'green'
            }
            level_color = level_colors.get(level, 'white')

            console.print(f"[{level_color}]●[/{level_color}] [{level_color}]{level}[/{level_color}] - {time_str}")
            console.print(f"  {message}")
            if details and verbose:
                console.print(f"  [dim]{details}[/dim]")
            console.print()

    except Exception as e:
        show_error_panel("Security Notifications Error", f"Failed to retrieve security notifications: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@security_app.command("sessions")
@with_error_handling("Sessions Error")
@with_logging
def security_sessions(
        user_id: Annotated[Optional[str], typer.Option("--user", "-u", help="Filter by user ID")] = None,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """View active security sessions."""
    setup_logging(verbose, config_dir)
    try:
        # Initialize access manager
        from .security import AccessManager
        access_manager = AccessManager(config_dir=config_dir)

        # Get active sessions
        sessions = access_manager.get_active_sessions(user_id=user_id)

        if not sessions:
            if user_id:
                show_info_panel("Active Sessions", f"No active sessions found for user '{user_id}'.")
            else:
                show_info_panel("Active Sessions", "No active sessions found.")
            return

        # Display sessions in a table
        table = Table(title="Active Security Sessions")
        table.add_column("Session ID", style="cyan", width=12)
        table.add_column("User ID", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("Last Accessed", style="blue")
        table.add_column("Expires", style="red")

        for session in sessions:
            session_id = session.session_id[:12] if len(session.session_id) > 12 else session.session_id
            created_str = session.created_at.strftime('%m-%d %H:%M')
            accessed_str = session.last_accessed.strftime('%m-%d %H:%M')
            expires_str = session.expires_at.strftime('%m-%d %H:%M')

            table.add_row(
                session_id,
                session.user_id,
                created_str,
                accessed_str,
                expires_str
            )

        console.print(table)

        if verbose:
            console.print(f"\n[dim]Total active sessions: {len(sessions)}[/dim]")
            
            # Show session details
            for session in sessions:
                console.print(f"\n[cyan]Session {session.session_id}:[/cyan]")
                console.print(f"  User: {session.user_id}")
                console.print(f"  Created: {session.created_at}")
                console.print(f"  Last Accessed: {session.last_accessed}")
                console.print(f"  Expires: {session.expires_at}")
                console.print(f"  Valid: {session.is_valid()}")
                if session.metadata:
                    console.print(f"  Metadata: {session.metadata}")

    except Exception as e:
        show_error_panel("Security Sessions Error", f"Failed to retrieve security sessions: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@security_app.command("cleanup")
@with_error_handling("Cleanup Error")
@with_logging
def security_cleanup(
        logs: Annotated[bool, typer.Option("--logs", help="Clean up old security logs")] = False,
        sessions: Annotated[bool, typer.Option("--sessions", help="Clean up expired sessions")] = False,
        temp_files: Annotated[bool, typer.Option("--temp-files", help="Clean up temporary files")] = False,
        all_items: Annotated[bool, typer.Option("--all", help="Clean up all items")] = False,
        max_age_hours: Annotated[Optional[int], typer.Option("--max-age", help="Maximum age in hours for cleanup")] = None,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """Clean up security data (logs, sessions, temporary files)."""
    setup_logging(verbose, config_dir)
    
    if not any([logs, sessions, temp_files, all_items]):
        show_error_panel("Cleanup Options", "Please specify what to clean up: --logs, --sessions, --temp-files, or --all")
        raise typer.Exit(1)

    try:
        # Initialize security components
        from .security import CredentialManager, AccessManager
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(credential_manager, config_dir=config_dir)
        access_manager = AccessManager(config_dir=config_dir)

        cleanup_results = {}

        # Clean up security logs
        if logs or all_items:
            console.print("🧹 Cleaning up security logs...")
            success = security_service.cleanup_security_logs()
            cleanup_results['logs'] = success
            if success:
                console.print("  ✅ Security logs cleaned up")
            else:
                console.print("  ❌ Failed to clean up security logs")

        # Clean up expired sessions
        if sessions or all_items:
            console.print("🧹 Cleaning up expired sessions...")
            cleaned_sessions = access_manager.cleanup_expired_sessions()
            cleanup_results['sessions'] = cleaned_sessions
            console.print(f"  ✅ Cleaned up {cleaned_sessions} expired sessions")

        # Clean up temporary files
        if temp_files or all_items:
            console.print("🧹 Cleaning up temporary files...")
            temp_stats = security_service.cleanup_temporary_files(max_age_hours=max_age_hours)
            cleanup_results['temp_files'] = temp_stats
            
            registered_deleted = temp_stats.get('registered_files_deleted', 0)
            old_deleted = temp_stats.get('old_files_deleted', 0)
            errors = temp_stats.get('errors', 0)
            
            console.print(f"  ✅ Deleted {registered_deleted} registered temporary files")
            console.print(f"  ✅ Deleted {old_deleted} old temporary files")
            if errors > 0:
                console.print(f"  ⚠️  {errors} errors occurred during cleanup")

        # Clean up repository protection data
        if all_items:
            console.print("🧹 Cleaning up repository protection data...")
            protection_stats = security_service.cleanup_repository_protection()
            cleanup_results['repository_protection'] = protection_stats
            
            expired_locks = protection_stats.get('expired_locks_cleaned', 0)
            console.print(f"  ✅ Cleaned up {expired_locks} expired repository locks")

        # Summary
        console.print("\n[bold green]Cleanup Summary:[/bold green]")
        total_cleaned = 0
        
        if 'logs' in cleanup_results:
            status = "✅" if cleanup_results['logs'] else "❌"
            console.print(f"  {status} Security logs cleanup")
            
        if 'sessions' in cleanup_results:
            sessions_cleaned = cleanup_results['sessions']
            console.print(f"  ✅ {sessions_cleaned} expired sessions removed")
            total_cleaned += sessions_cleaned
            
        if 'temp_files' in cleanup_results:
            temp_stats = cleanup_results['temp_files']
            files_cleaned = temp_stats.get('registered_files_deleted', 0) + temp_stats.get('old_files_deleted', 0)
            console.print(f"  ✅ {files_cleaned} temporary files removed")
            total_cleaned += files_cleaned
            
        if 'repository_protection' in cleanup_results:
            locks_cleaned = cleanup_results['repository_protection'].get('expired_locks_cleaned', 0)
            console.print(f"  ✅ {locks_cleaned} expired locks removed")
            total_cleaned += locks_cleaned

        if total_cleaned > 0:
            show_success_panel("Cleanup Complete", f"Successfully cleaned up {total_cleaned} items.")
        else:
            show_info_panel("Cleanup Complete", "No items needed cleanup.")

    except Exception as e:
        show_error_panel("Security Cleanup Error", f"Failed to perform security cleanup: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@security_app.command("config")
@with_error_handling("Config Error")
@with_logging
def security_config(
        show: Annotated[bool, typer.Option("--show", help="Show current security configuration")] = False,
        validate: Annotated[bool, typer.Option("--validate", help="Validate security configuration")] = False,
        export_path: Annotated[Optional[str], typer.Option("--export", help="Export configuration to file")] = None,
        import_path: Annotated[Optional[str], typer.Option("--import", help="Import configuration from file")] = None,
        reset: Annotated[bool, typer.Option("--reset", help="Reset to default configuration")] = False,
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """Manage security configuration settings."""
    setup_logging(verbose, config_dir)
    
    if not any([show, validate, export_path, import_path, reset]):
        show_error_panel("Configuration Options", "Please specify an action: --show, --validate, --export, --import, or --reset")
        raise typer.Exit(1)

    try:
        # Initialize security configuration CLI
        from .security.security_configuration_cli import SecurityConfigurationCLI
        from .config import ConfigurationModule
        
        config_module = ConfigurationModule(config_dir=config_dir)
        security_cli = SecurityConfigurationCLI(config_module=config_module)

        # Show configuration
        if show:
            security_cli.show_security_summary(format_type="table")

        # Validate configuration
        if validate:
            security_cli.validate_security_config(level="moderate", fix=False)

        # Export configuration
        if export_path:
            security_cli.export_security_configuration(export_path, include_sensitive=False)

        # Import configuration
        if import_path:
            security_cli.import_security_configuration(import_path, validate=True)

        # Reset configuration
        if reset:
            interactive = sys.stdin.isatty()
            if interactive:
                confirmed = Confirm.ask("Reset security configuration to defaults? This cannot be undone.", default=False)
                if not confirmed:
                    show_info_panel("Reset Cancelled", "Security configuration reset cancelled.")
                    return
            security_cli.reset_security_configuration(confirm=True)

    except Exception as e:
        show_error_panel("Security Configuration Error", f"Failed to manage security configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)
