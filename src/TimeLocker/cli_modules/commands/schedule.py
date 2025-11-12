"""
Scheduling automation operations.

This module contains CLI commands for scheduling automation including
schedule creation, management, and platform-specific script generation.
"""

import sys
import logging
import json
import platform
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path
from datetime import datetime, time

import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.tree import Tree

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
    _create_config_service,
    ConfigService,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import completion functions
from TimeLocker.completion import schedule_name_completer, policy_name_completer

# Create Typer app
schedule_app = create_typer_app(
    name="schedule",
    help_text="Scheduling automation operations"
)


# Helper functions

def _get_schedule_storage_dir(config_dir: Optional[Path] = None) -> Path:
    """Get schedule storage directory."""
    from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
    
    schedule_dir = ConfigurationPathResolver.get_data_directory() / "schedules"
    schedule_dir.mkdir(parents=True, exist_ok=True)
    return schedule_dir


def _load_schedules(config_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load all schedules from storage."""
    schedule_dir = _get_schedule_storage_dir(config_dir)
    schedules_file = schedule_dir / "schedules.json"
    
    if not schedules_file.exists():
        return {}
    
    with open(schedules_file, 'r') as f:
        return json.load(f)


def _save_schedules(schedules: Dict[str, Dict[str, Any]], config_dir: Optional[Path] = None) -> None:
    """Save schedules to storage."""
    schedule_dir = _get_schedule_storage_dir(config_dir)
    schedules_file = schedule_dir / "schedules.json"
    
    with open(schedules_file, 'w') as f:
        json.dump(schedules, f, indent=2)


def _format_schedule_table(schedules: Dict[str, Dict[str, Any]]) -> Table:
    """Format schedules as a Rich table."""
    table = Table(title="Backup Schedules")
    table.add_column("Name", style="cyan")
    table.add_column("Policy", style="green")
    table.add_column("Frequency", style="yellow")
    table.add_column("Next Run", style="white")
    table.add_column("Enabled", style="magenta")
    
    for name, schedule in schedules.items():
        enabled = "✓" if schedule.get('enabled', False) else "✗"
        next_run = schedule.get('next_run', 'N/A')
        frequency = schedule.get('frequency', 'N/A')
        policy = schedule.get('policy', 'N/A')
        
        table.add_row(name, policy, frequency, next_run, enabled)
    
    return table


def _interactive_schedule_configuration(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Interactively configure a schedule."""
    console.print("\n[bold]Schedule Configuration[/bold]\n")
    
    # Select or create policy
    console.print("[bold]1. Select Backup Policy[/bold]")
    
    # Try to list existing policies
    try:
        from TimeLocker.cli_modules.commands.policy import _get_policy_manager
        policy_manager = _get_policy_manager(config_dir)
        policies = policy_manager.list_backup_policies()
        
        if policies:
            console.print("\nExisting policies:")
            for i, policy in enumerate(policies, 1):
                console.print(f"  {i}. {policy.name} (ID: {policy.id[:8]})")
            
            choice = Prompt.ask(
                "\nSelect policy number or enter 'new' to create one",
                default="1"
            )
            
            if choice.lower() == 'new':
                policy_name = Prompt.ask("New policy name")
                console.print(f"[yellow]Note: Create policy '{policy_name}' using 'timelocker policy backup create' first[/yellow]")
            else:
                try:
                    idx = int(choice) - 1
                    policy_name = policies[idx].name
                except (ValueError, IndexError):
                    policy_name = choice
        else:
            policy_name = Prompt.ask("Policy name")
    except Exception:
        policy_name = Prompt.ask("Policy name")
    
    # Configure frequency
    console.print("\n[bold]2. Configure Frequency[/bold]")
    console.print("  1. Hourly")
    console.print("  2. Daily")
    console.print("  3. Weekly")
    console.print("  4. Monthly")
    console.print("  5. Custom (cron expression)")
    
    freq_choice = Prompt.ask("Select frequency", default="2")
    
    frequency_map = {
        "1": "hourly",
        "2": "daily",
        "3": "weekly",
        "4": "monthly",
        "5": "custom"
    }
    
    frequency = frequency_map.get(freq_choice, "daily")
    cron_expression = None
    
    if frequency == "custom":
        cron_expression = Prompt.ask("Enter cron expression (e.g., '0 2 * * *')")
    elif frequency == "daily":
        hour = IntPrompt.ask("Hour (0-23)", default=2)
        minute = IntPrompt.ask("Minute (0-59)", default=0)
        cron_expression = f"{minute} {hour} * * *"
    elif frequency == "weekly":
        day = IntPrompt.ask("Day of week (0=Sunday, 6=Saturday)", default=0)
        hour = IntPrompt.ask("Hour (0-23)", default=2)
        minute = IntPrompt.ask("Minute (0-59)", default=0)
        cron_expression = f"{minute} {hour} * * {day}"
    elif frequency == "monthly":
        day = IntPrompt.ask("Day of month (1-31)", default=1)
        hour = IntPrompt.ask("Hour (0-23)", default=2)
        minute = IntPrompt.ask("Minute (0-59)", default=0)
        cron_expression = f"{minute} {hour} {day} * *"
    elif frequency == "hourly":
        minute = IntPrompt.ask("Minute (0-59)", default=0)
        cron_expression = f"{minute} * * * *"
    
    # Additional options
    console.print("\n[bold]3. Additional Options[/bold]")
    enabled = Confirm.ask("Enable schedule immediately?", default=True)
    
    return {
        "policy": policy_name,
        "frequency": frequency,
        "cron_expression": cron_expression,
        "enabled": enabled,
        "created_at": datetime.now().isoformat(),
        "next_run": "Calculated on enable"
    }


def _generate_cron_script(schedule_name: str, schedule: Dict[str, Any], config_dir: Optional[Path] = None) -> str:
    """Generate cron script for Linux/macOS."""
    policy = schedule.get('policy', '')
    cron_expr = schedule.get('cron_expression', '0 2 * * *')
    
    # Get timelocker executable path
    import shutil
    timelocker_path = shutil.which('timelocker') or 'timelocker'
    
    script = f"""#!/bin/bash
# TimeLocker Backup Schedule: {schedule_name}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Policy: {policy}
# Frequency: {schedule.get('frequency', 'custom')}

# Cron expression: {cron_expr}
# Add this line to your crontab (crontab -e):
# {cron_expr} {timelocker_path} backup create --policy {policy} --non-interactive >> /var/log/timelocker/{schedule_name}.log 2>&1

# Or run this script directly:
{timelocker_path} backup create --policy {policy} --non-interactive
"""
    return script


def _generate_systemd_script(schedule_name: str, schedule: Dict[str, Any], config_dir: Optional[Path] = None) -> tuple[str, str]:
    """Generate systemd service and timer files for Linux."""
    policy = schedule.get('policy', '')
    cron_expr = schedule.get('cron_expression', '0 2 * * *')
    
    # Convert cron to systemd OnCalendar
    # This is a simplified conversion
    parts = cron_expr.split()
    if len(parts) == 5:
        minute, hour, day, month, weekday = parts
        if day == '*' and month == '*' and weekday == '*':
            # Daily
            oncalendar = f"*-*-* {hour}:{minute}:00"
        elif day == '*' and month == '*':
            # Weekly
            days_map = {'0': 'Sun', '1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu', '5': 'Fri', '6': 'Sat'}
            day_name = days_map.get(weekday, 'Mon')
            oncalendar = f"{day_name} *-*-* {hour}:{minute}:00"
        else:
            # Monthly or custom
            oncalendar = f"*-*-{day} {hour}:{minute}:00"
    else:
        oncalendar = "daily"
    
    # Get timelocker executable path
    import shutil
    timelocker_path = shutil.which('timelocker') or '/usr/local/bin/timelocker'
    
    service = f"""[Unit]
Description=TimeLocker Backup - {schedule_name}
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={timelocker_path} backup create --policy {policy} --non-interactive
StandardOutput=journal
StandardError=journal
SyslogIdentifier=timelocker-{schedule_name}

[Install]
WantedBy=multi-user.target
"""
    
    timer = f"""[Unit]
Description=TimeLocker Backup Timer - {schedule_name}
Requires=timelocker-{schedule_name}.service

[Timer]
OnCalendar={oncalendar}
Persistent=true

[Install]
WantedBy=timers.target
"""
    
    return service, timer


def _generate_windows_script(schedule_name: str, schedule: Dict[str, Any], config_dir: Optional[Path] = None) -> str:
    """Generate Windows Task Scheduler script."""
    policy = schedule.get('policy', '')
    cron_expr = schedule.get('cron_expression', '0 2 * * *')
    
    # Parse cron for Windows schedule
    parts = cron_expr.split()
    if len(parts) == 5:
        minute, hour, day, month, weekday = parts
        
        if day == '*' and month == '*' and weekday == '*':
            trigger = f"/SC DAILY /ST {hour}:{minute}"
        elif day == '*' and month == '*':
            days_map = {'0': 'SUN', '1': 'MON', '2': 'TUE', '3': 'WED', '4': 'THU', '5': 'FRI', '6': 'SAT'}
            day_name = days_map.get(weekday, 'MON')
            trigger = f"/SC WEEKLY /D {day_name} /ST {hour}:{minute}"
        else:
            trigger = f"/SC MONTHLY /D {day} /ST {hour}:{minute}"
    else:
        trigger = "/SC DAILY /ST 02:00"
    
    script = f"""@echo off
REM TimeLocker Backup Schedule: {schedule_name}
REM Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
REM Policy: {policy}

REM Create scheduled task
schtasks /CREATE /TN "TimeLocker\\{schedule_name}" {trigger} /TR "timelocker backup create --policy {policy} --non-interactive" /F

echo Scheduled task created: TimeLocker\\{schedule_name}
echo Run 'schtasks /Query /TN "TimeLocker\\{schedule_name}"' to verify
"""
    return script


# Schedule Commands

@schedule_app.command("create")
@with_error_handling("Schedule Creation Error")
@with_logging
def schedule_create(
    name: Annotated[str, typer.Argument(help="Schedule name")],
    policy: Annotated[Optional[str], typer.Argument(help="Policy name", autocompletion=policy_name_completer)] = None,
    frequency: Annotated[Optional[str], typer.Option("--frequency", "-f", help="Frequency (hourly, daily, weekly, monthly)")] = None,
    cron: Annotated[Optional[str], typer.Option("--cron", help="Custom cron expression")] = None,
    enabled: Annotated[bool, typer.Option("--enabled/--disabled", help="Enable schedule immediately")] = True,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Use interactive configuration")] = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Create a new backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        # Check if schedule already exists
        if name in schedules:
            show_error_panel("Schedule Exists", f"Schedule '{name}' already exists. Use 'schedule edit' to modify it.")
            raise typer.Exit(1)
        
        # Interactive configuration
        if interactive and CommandBase.is_interactive():
            schedule_config = _interactive_schedule_configuration(config_dir)
        else:
            # Command-line configuration
            if not policy:
                show_error_panel("Missing Policy", "Policy name is required. Use --interactive or provide policy name.")
                raise typer.Exit(1)
            
            if not frequency and not cron:
                show_error_panel("Missing Frequency", "Either --frequency or --cron must be specified.")
                raise typer.Exit(1)
            
            cron_expression = cron
            if frequency and not cron:
                # Generate cron from frequency
                if frequency == "hourly":
                    cron_expression = "0 * * * *"
                elif frequency == "daily":
                    cron_expression = "0 2 * * *"
                elif frequency == "weekly":
                    cron_expression = "0 2 * * 0"
                elif frequency == "monthly":
                    cron_expression = "0 2 1 * *"
                else:
                    show_error_panel("Invalid Frequency", f"Unknown frequency: {frequency}")
                    raise typer.Exit(1)
            
            schedule_config = {
                "policy": policy,
                "frequency": frequency or "custom",
                "cron_expression": cron_expression,
                "enabled": enabled,
                "created_at": datetime.now().isoformat(),
                "next_run": "Calculated on enable"
            }
        
        # Save schedule
        schedules[name] = schedule_config
        _save_schedules(schedules, config_dir)
        
        show_success_panel(
            "Schedule Created",
            f"Created backup schedule '{name}'",
            details={
                "Name": name,
                "Policy": schedule_config['policy'],
                "Frequency": schedule_config['frequency'],
                "Cron": schedule_config['cron_expression'],
                "Enabled": "Yes" if schedule_config['enabled'] else "No",
            }
        )
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Creation Error")


@schedule_app.command("list")
@with_error_handling("Schedule List Error")
@with_logging
def schedule_list(
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """List all backup schedules."""
    try:
        schedules = _load_schedules(config_dir)
        
        if json_output:
            console.print(json.dumps(schedules, indent=2))
        else:
            if not schedules:
                show_info_panel("No Schedules", "No backup schedules found.")
                return
            
            table = _format_schedule_table(schedules)
            console.print(table)
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule List Error")


@schedule_app.command("show")
@with_error_handling("Schedule Show Error")
@with_logging
def schedule_show(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Show details of a backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedule = schedules[name]
        
        if json_output:
            console.print(json.dumps({name: schedule}, indent=2))
        else:
            enabled_status = "[green]Enabled[/green]" if schedule.get('enabled', False) else "[red]Disabled[/red]"
            
            console.print(Panel(
                f"[bold]Name:[/bold] {name}\n"
                f"[bold]Policy:[/bold] {schedule.get('policy', 'N/A')}\n"
                f"[bold]Frequency:[/bold] {schedule.get('frequency', 'N/A')}\n"
                f"[bold]Cron Expression:[/bold] {schedule.get('cron_expression', 'N/A')}\n"
                f"[bold]Status:[/bold] {enabled_status}\n"
                f"[bold]Next Run:[/bold] {schedule.get('next_run', 'N/A')}\n"
                f"[bold]Created:[/bold] {schedule.get('created_at', 'N/A')}",
                title=f"[bold cyan]Schedule: {name}[/bold cyan]",
                border_style="cyan"
            ))
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Show Error")


@schedule_app.command("edit")
@with_error_handling("Schedule Edit Error")
@with_logging
def schedule_edit(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    policy: Annotated[Optional[str], typer.Option("--policy", "-p", help="New policy name", autocompletion=policy_name_completer)] = None,
    frequency: Annotated[Optional[str], typer.Option("--frequency", "-f", help="New frequency")] = None,
    cron: Annotated[Optional[str], typer.Option("--cron", help="New cron expression")] = None,
    enabled: Annotated[Optional[bool], typer.Option("--enabled/--disabled", help="Enable/disable schedule")] = None,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Edit an existing backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedule = schedules[name]
        
        # Update fields
        if policy is not None:
            schedule['policy'] = policy
        if frequency is not None:
            schedule['frequency'] = frequency
        if cron is not None:
            schedule['cron_expression'] = cron
        if enabled is not None:
            schedule['enabled'] = enabled
        
        schedule['updated_at'] = datetime.now().isoformat()
        
        # Save schedules
        schedules[name] = schedule
        _save_schedules(schedules, config_dir)
        
        show_success_panel("Schedule Updated", f"Updated backup schedule '{name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Edit Error")


@schedule_app.command("delete")
@with_error_handling("Schedule Delete Error")
@with_logging
def schedule_delete(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    yes: YesOption = False,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Delete a backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        if not yes and CommandBase.is_interactive():
            confirmed = Confirm.ask(f"Delete schedule '{name}'?", default=False)
            if not confirmed:
                show_info_panel("Operation Cancelled", "Schedule deletion cancelled.")
                return
        
        del schedules[name]
        _save_schedules(schedules, config_dir)
        
        show_success_panel("Schedule Deleted", f"Deleted backup schedule '{name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Delete Error")


@schedule_app.command("enable")
@with_error_handling("Schedule Enable Error")
@with_logging
def schedule_enable(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Enable a backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedules[name]['enabled'] = True
        schedules[name]['updated_at'] = datetime.now().isoformat()
        _save_schedules(schedules, config_dir)
        
        show_success_panel("Schedule Enabled", f"Enabled backup schedule '{name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Enable Error")


@schedule_app.command("disable")
@with_error_handling("Schedule Disable Error")
@with_logging
def schedule_disable(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Disable a backup schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedules[name]['enabled'] = False
        schedules[name]['updated_at'] = datetime.now().isoformat()
        _save_schedules(schedules, config_dir)
        
        show_success_panel("Schedule Disabled", f"Disabled backup schedule '{name}'")
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Disable Error")


@schedule_app.command("generate-scripts")
@with_error_handling("Script Generation Error")
@with_logging
def schedule_generate_scripts(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    output_dir: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output directory for scripts")] = None,
    platform_type: Annotated[Optional[str], typer.Option("--platform", "-p", help="Platform (cron, systemd, windows)")] = None,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Generate platform-specific automation scripts for a schedule."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedule = schedules[name]
        
        # Determine output directory
        if output_dir is None:
            output_dir = Path.cwd() / "timelocker_scripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine platform
        if platform_type is None:
            system = platform.system().lower()
            if system == "windows":
                platform_type = "windows"
            elif system == "linux":
                platform_type = "systemd"
            else:
                platform_type = "cron"
        
        platform_type = platform_type.lower()
        
        # Generate scripts
        if platform_type == "cron":
            script = _generate_cron_script(name, schedule, config_dir)
            script_file = output_dir / f"{name}_cron.sh"
            with open(script_file, 'w') as f:
                f.write(script)
            script_file.chmod(0o755)
            
            show_success_panel(
                "Cron Script Generated",
                f"Generated cron script for '{name}'",
                details={
                    "Script": str(script_file),
                    "Platform": "Linux/macOS (cron)",
                }
            )
            console.print(f"\n[cyan]To install:[/cyan] Add the cron line from {script_file} to your crontab")
            
        elif platform_type == "systemd":
            service, timer = _generate_systemd_script(name, schedule, config_dir)
            service_file = output_dir / f"timelocker-{name}.service"
            timer_file = output_dir / f"timelocker-{name}.timer"
            
            with open(service_file, 'w') as f:
                f.write(service)
            with open(timer_file, 'w') as f:
                f.write(timer)
            
            show_success_panel(
                "Systemd Scripts Generated",
                f"Generated systemd service and timer for '{name}'",
                details={
                    "Service": str(service_file),
                    "Timer": str(timer_file),
                    "Platform": "Linux (systemd)",
                }
            )
            console.print(f"\n[cyan]To install:[/cyan]")
            console.print(f"  sudo cp {service_file} {timer_file} /etc/systemd/system/")
            console.print(f"  sudo systemctl daemon-reload")
            console.print(f"  sudo systemctl enable --now timelocker-{name}.timer")
            
        elif platform_type == "windows":
            script = _generate_windows_script(name, schedule, config_dir)
            script_file = output_dir / f"{name}_windows.bat"
            with open(script_file, 'w') as f:
                f.write(script)
            
            show_success_panel(
                "Windows Script Generated",
                f"Generated Windows Task Scheduler script for '{name}'",
                details={
                    "Script": str(script_file),
                    "Platform": "Windows (Task Scheduler)",
                }
            )
            console.print(f"\n[cyan]To install:[/cyan] Run {script_file} as Administrator")
            
        else:
            show_error_panel("Invalid Platform", f"Unknown platform: {platform_type}")
            raise typer.Exit(1)
            
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Script Generation Error")


@schedule_app.command("test")
@with_error_handling("Schedule Test Error")
@with_logging
def schedule_test(
    name: Annotated[str, typer.Argument(help="Schedule name", autocompletion=schedule_name_completer)],
    dry_run: DryRunOption = True,
    verbose: VerboseOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """Test a schedule configuration and dependencies."""
    try:
        schedules = _load_schedules(config_dir)
        
        if name not in schedules:
            show_error_panel("Schedule Not Found", f"Schedule '{name}' does not exist.")
            raise typer.Exit(1)
        
        schedule = schedules[name]
        policy_name = schedule.get('policy')
        
        console.print(f"\n[bold]Testing Schedule: {name}[/bold]\n")
        
        # Test 1: Check policy exists
        console.print("[cyan]1. Checking policy...[/cyan]")
        try:
            from TimeLocker.cli_modules.commands.policy import _get_policy_manager
            policy_manager = _get_policy_manager(config_dir)
            policies = policy_manager.list_backup_policies()
            policy_exists = any(p.name == policy_name for p in policies)
            
            if policy_exists:
                console.print(f"   [green]✓[/green] Policy '{policy_name}' exists")
            else:
                console.print(f"   [red]✗[/red] Policy '{policy_name}' not found")
        except Exception as e:
            console.print(f"   [yellow]⚠[/yellow] Could not verify policy: {e}")
        
        # Test 2: Validate cron expression
        console.print("\n[cyan]2. Validating cron expression...[/cyan]")
        cron_expr = schedule.get('cron_expression')
        if cron_expr:
            parts = cron_expr.split()
            if len(parts) == 5:
                console.print(f"   [green]✓[/green] Valid cron expression: {cron_expr}")
            else:
                console.print(f"   [red]✗[/red] Invalid cron expression: {cron_expr}")
        else:
            console.print(f"   [red]✗[/red] No cron expression defined")
        
        # Test 3: Check schedule status
        console.print("\n[cyan]3. Checking schedule status...[/cyan]")
        enabled = schedule.get('enabled', False)
        if enabled:
            console.print(f"   [green]✓[/green] Schedule is enabled")
        else:
            console.print(f"   [yellow]⚠[/yellow] Schedule is disabled")
        
        console.print(f"\n[bold green]Schedule test complete[/bold green]")
        
    except Exception as e:
        CommandBase.handle_error(e, verbose, "Schedule Test Error")


__all__ = ['schedule_app']
