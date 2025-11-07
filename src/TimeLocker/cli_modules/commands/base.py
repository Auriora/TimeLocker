"""
Base classes and utilities for CLI commands.

This module provides common functionality for all CLI command modules,
including error handling, setup, and shared patterns.
"""

import sys
import logging
from typing import Optional, Callable, Any
from pathlib import Path
from functools import wraps

import typer
import click

# Import from parent cli.py during transition
from TimeLocker import cli as _cli_module

# Common display functions
show_success_panel = _cli_module.show_success_panel
show_error_panel = _cli_module.show_error_panel
show_info_panel = _cli_module.show_info_panel
setup_logging = _cli_module.setup_logging
console = _cli_module.console

# Common service helpers
_get_service_method = _cli_module._get_service_method
_call_service_method = _cli_module._call_service_method
_get_service_manager_for_command = _cli_module._get_service_manager_for_command
_create_configuration_module = _cli_module._create_configuration_module

# CLI context settings
CLI_CONTEXT_SETTINGS = {"max_content_width": 110}


class CommandBase:
    """
    Base class for CLI commands providing common functionality.
    
    This class provides:
    - Logging setup
    - Error handling
    - Configuration management
    - Service manager access
    """
    
    @staticmethod
    def setup(verbose: bool = False, config_dir: Optional[Path] = None):
        """
        Common setup for all commands.
        
        Args:
            verbose: Enable verbose logging
            config_dir: Optional configuration directory
            
        Returns:
            Tuple of (service_manager, config_module)
        """
        setup_logging(verbose, config_dir)
        service_manager = _get_service_manager_for_command(config_dir)
        config_module = _create_configuration_module(config_dir)
        return service_manager, config_module
    
    @staticmethod
    def handle_error(e: Exception, verbose: bool, title: str, exit_code: int = 1):
        """
        Common error handling for all commands.
        
        Args:
            e: The exception that occurred
            verbose: Whether to show full traceback
            title: Error panel title
            exit_code: Exit code to use
        """
        show_error_panel(title, str(e))
        if verbose:
            console.print_exception()
        raise typer.Exit(exit_code)
    
    @staticmethod
    def is_interactive() -> bool:
        """Check if running in interactive mode."""
        return sys.stdin.isatty()


def with_error_handling(
    title: str = "Command Error",
    exit_code: int = 1,
    handle_keyboard_interrupt: bool = True
):
    """
    Decorator to add consistent error handling to commands.
    
    Args:
        title: Error panel title
        exit_code: Exit code for general errors
        handle_keyboard_interrupt: Whether to handle Ctrl+C
        
    Example:
        @with_error_handling("Backup Error")
        def backup_create(...):
            # Command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                if handle_keyboard_interrupt:
                    show_error_panel("Operation Cancelled", f"{func.__name__} was cancelled by user")
                    raise typer.Exit(130)
                raise
            except click.exceptions.Exit:
                # Let typer exits pass through
                raise
            except Exception as e:
                verbose = kwargs.get('verbose', False)
                show_error_panel(title, f"An unexpected error occurred: {e}")
                if verbose:
                    console.print_exception()
                raise typer.Exit(exit_code)
        return wrapper
    return decorator


def with_logging(func: Callable) -> Callable:
    """
    Decorator to automatically setup logging for commands.
    
    Looks for 'verbose' and 'config_dir' parameters and calls setup_logging.
    
    Example:
        @with_logging
        def my_command(verbose: bool = False, config_dir: Optional[Path] = None):
            # Logging is already set up
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        verbose = kwargs.get('verbose', False)
        config_dir = kwargs.get('config_dir', None)
        setup_logging(verbose, config_dir)
        return func(*args, **kwargs)
    return wrapper


def with_service_manager(func: Callable) -> Callable:
    """
    Decorator to inject service manager into command.
    
    Adds 'service_manager' to kwargs before calling the function.
    
    Example:
        @with_service_manager
        def my_command(service_manager=None, **kwargs):
            # service_manager is available
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        config_dir = kwargs.get('config_dir', None)
        service_manager = _get_service_manager_for_command(config_dir)
        kwargs['service_manager'] = service_manager
        return func(*args, **kwargs)
    return wrapper


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_not_empty(value: Optional[str], field_name: str) -> str:
    """
    Validate that a string value is not empty.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is None or empty
    """
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty")
    return value.strip()


def validate_path_exists(path: Path, must_exist: bool = True) -> Path:
    """
    Validate that a path exists (or doesn't exist).
    
    Args:
        path: Path to validate
        must_exist: Whether the path must exist
        
    Returns:
        The validated path
        
    Raises:
        ValidationError: If validation fails
    """
    if must_exist and not path.exists():
        raise ValidationError(f"Path does not exist: {path}")
    if not must_exist and path.exists():
        raise ValidationError(f"Path already exists: {path}")
    return path


def create_typer_app(
    name: str,
    help_text: str,
    no_args_is_help: bool = True
) -> typer.Typer:
    """
    Create a Typer app with standard settings.
    
    Args:
        name: App name
        help_text: Help text
        no_args_is_help: Show help when no args provided
        
    Returns:
        Configured Typer app
    """
    app = typer.Typer(
        name=name,
        help=help_text,
        no_args_is_help=no_args_is_help,
        context_settings=CLI_CONTEXT_SETTINGS
    )
    app.info.options_metavar = "⟨OPTIONS⟩"
    return app


# Common type annotations for reuse
from typing import Annotated

VerboseOption = Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")]
JsonOption = Annotated[bool, typer.Option("--json", help="Output in JSON format")]
YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Confirm without prompt")]
ConfigDirOption = Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")]
DryRunOption = Annotated[bool, typer.Option("--dry-run", help="Preview without executing")]


__all__ = [
    'CommandBase',
    'with_error_handling',
    'with_logging',
    'with_service_manager',
    'ValidationError',
    'validate_not_empty',
    'validate_path_exists',
    'create_typer_app',
    'CLI_CONTEXT_SETTINGS',
    'show_success_panel',
    'show_error_panel',
    'show_info_panel',
    'setup_logging',
    'console',
    '_get_service_method',
    '_call_service_method',
    '_get_service_manager_for_command',
    '_create_configuration_module',
    'VerboseOption',
    'JsonOption',
    'YesOption',
    'ConfigDirOption',
    'DryRunOption',
]
