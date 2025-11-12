"""
Configuration management commands.

This module contains CLI commands for configuration management commands.
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
    _create_config_service,
    ConfigService,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Import from TimeLocker package
from TimeLocker import cli as _cli_module
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.cli import setup_logging

# Module-specific imports
from TimeLocker.config import (
    ConfigurationModule,
    ConfigurationValidator
)
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager,
    BackupReason
)
from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
from TimeLocker.importers.timeshift_importer import (
    TimeshiftConfigParser,
    TimeshiftToTimeLockerMapper
)
from TimeLocker.interfaces.exceptions import ConfigurationError
from datetime import datetime
import json
from difflib import unified_diff

# Validation imports
from ..validation import validate_path, ValidationError

# Create Typer app
config_app = create_typer_app(
    name="config",
    help_text="Configuration management commands"
)



# Commands

@config_app.command("show")
@with_error_handling("Show Error")
@with_logging
def config_show(
        config_dir: ConfigDirOption = None,
        json_output: JsonOption = False,
        verbose: VerboseOption = False,
) -> None:
    """Display TimeLocker configuration details."""
    setup_logging(verbose, config_dir)
    try:
        # Use ConfigService for centralized configuration access
        config_service = _create_config_service(config_dir)
        config = config_service.get_config()
        config_dict = config_service.get_config_dict()
        validation_result = None
        validation_errors: List[str] = []
        validation_warnings: List[str] = []

        try:
            validator = ConfigurationValidator()
            validate_method = getattr(validator, "validate_configuration", None)
            validation_input = config_dict or config

            if callable(validate_method):
                validation_result = validate_method(validation_input)
            elif hasattr(validator, "validate_config"):
                validation_result = validator.validate_config(validation_input)

            if validation_result is not None:
                validation_errors = list(getattr(validation_result, "errors", []))
                validation_warnings = list(getattr(validation_result, "warnings", []))
        except Exception as validation_error:
            logging.getLogger(__name__).debug("Configuration validation failed: %s", validation_error)
            validation_errors = [f"Validation failed: {validation_error}"]

        if json_output:
            console.print_json(data=config_dict)
            return

        table = Table(title="Configuration Overview")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        default_repo = getattr(getattr(config, "general", None), "default_repository", None)
        table.add_row("Config File", str(config_service.config_file))
        table.add_row("Repositories", str(len(getattr(config, "repositories", {}))))
        table.add_row("Backup Targets", str(len(getattr(config, "backup_targets", {}))))
        table.add_row("Default Repository", default_repo or "Not set")
        console.print(table)

        if validation_result is not None:
            is_valid = bool(getattr(validation_result, "is_valid", bool(validation_result)))
            if is_valid and not validation_errors:
                success_message = "Configuration validation passed."
                if validation_warnings:
                    success_message += f" ({len(validation_warnings)} warnings)"
                show_success_panel("Configuration Validation", success_message)
            else:
                error_details = validation_errors or ["Unknown validation failure."]
                show_error_panel("Configuration Validation Failed", "Configuration contains errors.", error_details)
        elif validation_errors:
            show_error_panel("Validation Error", validation_errors[0], validation_errors[1:])

        for warning in validation_warnings:
            console.print(f"⚠️  [yellow]Warning:[/yellow] {warning}")
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Configuration Error", f"Failed to load configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@config_app.command("setup")
@with_error_handling("Setup Error")
@with_logging
def config_setup(
        config_dir: ConfigDirOption = None,
        verbose: VerboseOption = False,
) -> None:
    """Launch the interactive configuration wizard."""
    setup_logging(verbose, config_dir)
    interactive = sys.stdin.isatty()
    try:
        if not interactive:
            show_info_panel("Interactive Setup Required", "Run this command in an interactive terminal to configure TimeLocker.")
            raise typer.Exit(2)

        show_info_panel(
                "Configuration Wizard",
                "Interactive configuration is not yet automated. Update your configuration file manually or use 'timelocker config show --json' to view current settings."
        )
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Configuration setup cancelled by user")
        raise typer.Exit(130)
    except click.exceptions.Exit:
        raise
    except Exception as e:
        show_error_panel("Setup Error", f"Failed to run configuration setup: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@config_app.command("performance")
@with_error_handling("Performance Error")
@with_logging
def config_performance(
        config_dir: ConfigDirOption = None,
        json_output: JsonOption = False,
        recommendations: Annotated[bool, typer.Option("--recommendations", help="Show optimization recommendations")] = False,
        verbose: VerboseOption = False,
) -> None:
    """Show configuration system performance metrics."""
    setup_logging(verbose, config_dir)
    try:
        from .config.configuration_performance_monitor import ConfigurationPerformanceMonitor
        
        # Create performance monitor (this would normally be a singleton in the actual system)
        monitor = ConfigurationPerformanceMonitor()
        
        # Get performance metrics
        metrics = monitor.get_performance_metrics()
        cache_stats = monitor.get_cache_statistics()
        
        if json_output:
            data = {
                'performance_metrics': metrics,
                'cache_statistics': cache_stats,
                'recommendations': monitor.get_recommendations() if recommendations else []
            }
            console.print_json(data=data)
            return
        
        # Display performance metrics
        console.rule("Configuration Performance Metrics")
        
        # System info
        uptime_hours = metrics.get('uptime_seconds', 0) / 3600
        console.print(f"[bold]System Status:[/bold]")
        console.print(f"  Monitoring: {'✅ Enabled' if metrics.get('monitoring_enabled') else '❌ Disabled'}")
        console.print(f"  Uptime: {uptime_hours:.1f} hours")
        console.print(f"  Performance Alerts: {metrics.get('performance_alerts', 0)}")
        
        # Operation metrics
        operation_metrics = metrics.get('operation_metrics', {})
        if operation_metrics:
            console.print(f"\n[bold]Operation Performance:[/bold]")
            
            table = Table()
            table.add_column("Operation", style="cyan")
            table.add_column("Calls", style="yellow")
            table.add_column("Avg Duration", style="green")
            table.add_column("Max Duration", style="red")
            table.add_column("Error Rate", style="magenta")
            
            for op_name, op_stats in operation_metrics.items():
                error_rate = f"{op_stats['error_rate']:.1%}" if op_stats['error_rate'] > 0 else "0%"
                table.add_row(
                    op_name,
                    str(op_stats['total_calls']),
                    f"{op_stats['average_duration']:.3f}s",
                    f"{op_stats['max_duration']:.3f}s",
                    error_rate
                )
            
            console.print(table)
        
        # Cache metrics
        console.print(f"\n[bold]Cache Performance:[/bold]")
        console.print(f"  Hit Ratio: {cache_stats.get('hit_ratio', 0):.1%}")
        console.print(f"  Total Requests: {cache_stats.get('total_requests', 0)}")
        console.print(f"  Cache Size: {cache_stats.get('current_size', 0)} / {cache_stats.get('max_size', 0)}")
        console.print(f"  Utilization: {cache_stats.get('utilization_percent', 0):.1f}%")
        console.print(f"  Efficiency Score: {cache_stats.get('efficiency_score', 0):.1f}/100")
        
        # Show recommendations if requested
        if recommendations:
            recs = monitor.get_recommendations()
            if recs:
                console.print(f"\n[bold yellow]Optimization Recommendations:[/bold yellow]")
                for i, rec in enumerate(recs, 1):
                    console.print(f"  {i}. {rec}")
            else:
                console.print(f"\n[green]No optimization recommendations at this time.[/green]")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Performance check cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Performance Check Error", f"Failed to get configuration performance metrics: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@config_app.command("validate")
@with_error_handling("Validate Error")
@with_logging
def config_validate(
        config_dir: ConfigDirOption = None,
        config_file: Annotated[Optional[Path], typer.Option("--config-file", help="Specific configuration file to validate")] = None,
        json_output: JsonOption = False,
        detailed: Annotated[bool, typer.Option("--detailed", help="Show detailed validation results")] = False,
        verbose: VerboseOption = False,
) -> None:
    """Validate configuration with detailed error reporting."""
    setup_logging(verbose, config_dir)
    try:
        from .config.configuration_validator import ConfigurationValidator
        from .config.configuration_path_resolver import ConfigurationPathResolver
        import json
        
        # Get configuration file path
        if config_file:
            target_file = Path(config_file)
        else:
            resolver = ConfigurationPathResolver(config_dir)
            target_file = resolver.get_config_file()
        
        try:
            validate_path(target_file, must_exist=True, must_be_file=True, field_name="configuration file")
        except ValidationError as e:
            show_error_panel("Configuration Not Found", str(e))
            raise typer.Exit(1)
        
        # Load configuration
        try:
            with open(target_file, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            show_error_panel("Invalid JSON", f"Configuration file contains invalid JSON: {e}")
            raise typer.Exit(1)
        
        # Create validator and validate
        validator = ConfigurationValidator()
        result = validator.validate_config(config_data)
        
        if json_output:
            data = {
                'configuration_file': str(target_file),
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings,
                'validation_timestamp': datetime.now().isoformat()
            }
            console.print_json(data=data)
            return
        
        # Display validation results
        console.rule("Configuration Validation")
        console.print(f"[bold]Configuration File:[/bold] {target_file}")
        console.print(f"[bold]Validation Time:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if result.is_valid and not result.errors:
            status_color = "green"
            status_icon = "✅"
            status_text = "VALID"
        else:
            status_color = "red"
            status_icon = "❌"
            status_text = "INVALID"
        
        console.print(f"\n[bold {status_color}]{status_icon} Status: {status_text}[/bold {status_color}]")
        
        # Show errors
        if result.errors:
            console.print(f"\n[bold red]Errors ({len(result.errors)}):[/bold red]")
            for i, error in enumerate(result.errors, 1):
                console.print(f"  {i}. {error}")
        
        # Show warnings
        if result.warnings:
            console.print(f"\n[bold yellow]Warnings ({len(result.warnings)}):[/bold yellow]")
            for i, warning in enumerate(result.warnings, 1):
                console.print(f"  {i}. {warning}")
        
        # Show detailed information if requested
        if detailed and hasattr(result, 'details'):
            console.print(f"\n[bold]Detailed Validation Results:[/bold]")
            for section, details in result.details.items():
                console.print(f"  [cyan]{section}:[/cyan] {details}")
        
        # Summary
        if result.is_valid and not result.errors:
            show_success_panel("Validation Complete", "Configuration is valid and ready to use.")
        else:
            show_error_panel("Validation Failed", f"Configuration has {len(result.errors)} errors that must be fixed.")
            raise typer.Exit(1)
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Configuration validation cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Validation Error", f"Failed to validate configuration: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)




@config_app.command("diff")
@with_error_handling("Diff Error")
@with_logging
def config_diff(
        config_dir: ConfigDirOption = None,
        file1: Annotated[Optional[Path], typer.Option("--file1", help="First configuration file to compare")] = None,
        file2: Annotated[Optional[Path], typer.Option("--file2", help="Second configuration file to compare")] = None,
        backup_id: Annotated[Optional[str], typer.Option("--backup", help="Compare current config with backup ID")] = None,
        section: Annotated[Optional[str], typer.Option("--section", help="Compare only specific section")] = None,
        json_output: JsonOption = False,
        verbose: VerboseOption = False,
) -> None:
    """Compare configuration files or sections."""
    setup_logging(verbose, config_dir)
    try:
        from .config.configuration_backup_manager import ConfigurationBackupManager
        from .config.configuration_path_resolver import ConfigurationPathResolver
        import json
        
        resolver = ConfigurationPathResolver(config_dir)
        
        # Determine what to compare
        if backup_id:
            # Compare current config with backup
            current_file = resolver.get_config_file()
            backup_dir = resolver.get_config_directory() / "backups"
            backup_file = backup_dir / f"{backup_id}.json"
            
            try:
                validate_path(current_file, must_exist=True, must_be_file=True, field_name="current configuration file")
            except ValidationError as e:
                show_error_panel("Configuration Not Found", str(e))
                raise typer.Exit(1)
            
            try:
                validate_path(backup_file, must_exist=True, must_be_file=True, field_name="backup file")
            except ValidationError as e:
                show_error_panel("Backup Not Found", str(e))
                raise typer.Exit(1)
            
            file1, file2 = current_file, backup_file
            comparison_title = f"Current vs Backup {backup_id}"
            
        elif file1 and file2:
            # Compare two specific files
            file1, file2 = Path(file1), Path(file2)
            
            try:
                validate_path(file1, must_exist=True, must_be_file=True, field_name="first configuration file")
            except ValidationError as e:
                show_error_panel("File Not Found", str(e))
                raise typer.Exit(1)
            
            try:
                validate_path(file2, must_exist=True, must_be_file=True, field_name="second configuration file")
            except ValidationError as e:
                show_error_panel("File Not Found", str(e))
                raise typer.Exit(1)
            
            comparison_title = f"{file1.name} vs {file2.name}"
            
        else:
            show_error_panel("Missing Parameters", "Specify either --backup ID or both --file1 and --file2")
            raise typer.Exit(2)
        
        # Load configurations
        with open(file1, 'r') as f:
            config1 = json.load(f)
        with open(file2, 'r') as f:
            config2 = json.load(f)
        
        # Filter by section if specified
        if section:
            config1 = {section: config1.get(section, {})}
            config2 = {section: config2.get(section, {})}
        
        # Compare configurations using backup manager's comparison logic
        backup_manager = ConfigurationBackupManager(resolver.get_config_directory() / "backups")
        differences = backup_manager._compare_configurations(config1, config2)
        
        if json_output:
            data = {
                'file1': str(file1),
                'file2': str(file2),
                'section_filter': section,
                'identical': len(differences) == 0,
                'differences': differences,
                'comparison_timestamp': datetime.now().isoformat()
            }
            console.print_json(data=data)
            return
        
        # Display comparison results
        console.rule(f"Configuration Diff: {comparison_title}")
        
        if section:
            console.print(f"[bold]Section Filter:[/bold] {section}")
        
        console.print(f"[bold]File 1:[/bold] {file1}")
        console.print(f"[bold]File 2:[/bold] {file2}")
        
        if len(differences) == 0:
            show_success_panel("Comparison Result", "The configurations are identical.")
        else:
            console.print(f"\n[bold red]Found {len(differences)} differences:[/bold red]")
            
            # Group differences by type
            changes = {'added': [], 'removed': [], 'modified': [], 'type_changed': []}
            
            for diff in differences:
                diff_type = diff['type']
                if diff_type == 'added':
                    changes['added'].append(diff)
                elif diff_type == 'removed':
                    changes['removed'].append(diff)
                elif diff_type == 'value_change':
                    changes['modified'].append(diff)
                elif diff_type == 'type_change':
                    changes['type_changed'].append(diff)
            
            # Display grouped differences
            for change_type, change_list in changes.items():
                if not change_list:
                    continue
                
                if change_type == 'added':
                    console.print(f"\n[bold green]Added ({len(change_list)}):[/bold green]")
                    for diff in change_list[:5]:  # Show first 5
                        console.print(f"  + {diff['path']}: {diff['new_value']}")
                elif change_type == 'removed':
                    console.print(f"\n[bold red]Removed ({len(change_list)}):[/bold red]")
                    for diff in change_list[:5]:  # Show first 5
                        console.print(f"  - {diff['path']}: {diff['old_value']}")
                elif change_type == 'modified':
                    console.print(f"\n[bold yellow]Modified ({len(change_list)}):[/bold yellow]")
                    for diff in change_list[:5]:  # Show first 5
                        console.print(f"  ~ {diff['path']}: '{diff['old_value']}' → '{diff['new_value']}'")
                elif change_type == 'type_changed':
                    console.print(f"\n[bold magenta]Type Changed ({len(change_list)}):[/bold magenta]")
                    for diff in change_list[:5]:  # Show first 5
                        console.print(f"  ! {diff['path']}: {diff['old_type']} → {diff['new_type']}")
                
                if len(change_list) > 5:
                    console.print(f"    ... and {len(change_list) - 5} more")
        
    except KeyboardInterrupt:
        show_error_panel("Operation Cancelled", "Configuration diff cancelled by user")
        raise typer.Exit(130)
    except Exception as e:
        show_error_panel("Diff Error", f"Failed to compare configurations: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


