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

from ..helpers.display import (
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
)
from ..helpers.logging_setup import setup_logging
from ..helpers.service_helpers import (
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_configuration_module,
)

# Import ConfigService, RepositoryResolver, and ServiceFacade
from ..services.config_service import ConfigService
from ..services.repository_resolver import RepositoryResolver
from TimeLocker.utils.service_facade import ServiceFacade, create_service_facade

# Import CommandRegistry
from ..command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
    get_command_registry,
)
from ..registry_integration import (
    register_core_commands,
    register_optional_commands,
    register_all_commands,
)


def _create_service_facade(config_dir: Optional[Path] = None, 
                           service_manager: Optional[Any] = None) -> ServiceFacade:
    """
    Factory for ServiceFacade.
    
    This provides simplified service access for all CLI commands,
    reducing code duplication and providing consistent error handling.
    
    Args:
        config_dir: Optional configuration directory
        service_manager: Optional existing service manager instance
        
    Returns:
        ServiceFacade: Configured facade instance
    """
    return create_service_facade(config_dir=config_dir, service_manager=service_manager)


def _create_config_service(config_dir: Optional[Path] = None) -> ConfigService:
    """
    Factory for ConfigService.
    
    This provides centralized configuration access for all CLI commands,
    replacing direct ConfigurationModule usage.
    
    Args:
        config_dir: Optional configuration directory
        
    Returns:
        ConfigService: Configured service instance
    """
    return ConfigService(config_dir=config_dir)


def _create_repository_resolver(config_dir: Optional[Path] = None) -> RepositoryResolver:
    """
    Factory for RepositoryResolver.
    
    This provides centralized repository resolution for all CLI commands,
    replacing repeated repository lookup patterns.
    
    Args:
        config_dir: Optional configuration directory
        
    Returns:
        RepositoryResolver: Configured resolver instance
    """
    return RepositoryResolver(config_dir=config_dir)

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
            Tuple of (service_manager, config_service)
        """
        setup_logging(verbose, config_dir)
        service_manager = _get_service_manager_for_command(config_dir)
        config_service = _create_config_service(config_dir)
        return service_manager, config_service
    
    @staticmethod
    def setup_with_facade(verbose: bool = False, config_dir: Optional[Path] = None):
        """
        Modern setup for commands using ServiceFacade.
        
        This is the recommended setup method for new commands and refactored commands.
        It provides simplified service access through the ServiceFacade.
        
        Args:
            verbose: Enable verbose logging
            config_dir: Optional configuration directory
            
        Returns:
            ServiceFacade: Configured service facade instance
        """
        setup_logging(verbose, config_dir)
        service_manager = _get_service_manager_for_command(config_dir)
        return _create_service_facade(config_dir=config_dir, service_manager=service_manager)
    
    @staticmethod
    def setup_legacy(verbose: bool = False, config_dir: Optional[Path] = None):
        """
        Legacy setup for commands not yet migrated to ConfigService.
        
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
        
    Note:
        This function is deprecated. Use validation.validate_required_string instead.
    """
    from ..validation import validate_required_string
    return validate_required_string(value, field_name)


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
        
    Note:
        This function is deprecated. Use validation.validate_path instead.
    """
    from ..validation import validate_path
    return validate_path(path, must_exist=must_exist, must_not_exist=not must_exist)


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
    app.info.options_metavar = "<OPTIONS>"
    return app


# Import output formatting utilities
try:
    from ..helpers.output_formatter import (
        OutputFormatter,
        OutputFormat,
        ExitCode,
        create_formatter,
        format_success_json,
        format_error_json,
    )
    from ..helpers.non_interactive import (
        require_parameter,
        validate_parameters,
        with_non_interactive_check,
        exit_with_code,
        handle_operation_result,
        NonInteractiveError,
        ensure_interactive_or_fail,
    )
    from ..helpers.output_filtering import (
        OutputFilter,
        Paginator,
        PaginationInfo,
        QuietMode,
        create_filter,
        create_paginator,
        apply_filters_and_pagination,
        filter_sensitive_fields,
    )
except ImportError:
    # Fallback if modules are not available
    OutputFormatter = None
    OutputFormat = None
    ExitCode = None
    create_formatter = None
    format_success_json = None
    format_error_json = None
    require_parameter = None
    validate_parameters = None
    with_non_interactive_check = None
    exit_with_code = None
    handle_operation_result = None
    NonInteractiveError = None
    ensure_interactive_or_fail = None
    OutputFilter = None
    Paginator = None
    PaginationInfo = None
    QuietMode = None
    create_filter = None
    create_paginator = None
    apply_filters_and_pagination = None
    filter_sensitive_fields = None


# Common type annotations for reuse
from typing import Annotated

VerboseOption = Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")]
JsonOption = Annotated[bool, typer.Option("--json", help="Output in JSON format")]
FormatOption = Annotated[Optional[str], typer.Option("--format", help="Output format (json)")]
QuietOption = Annotated[bool, typer.Option("--quiet", "-q", help="Suppress non-essential output")]
NonInteractiveOption = Annotated[bool, typer.Option("--non-interactive", help="Run in non-interactive mode")]
YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Confirm without prompt")]
ConfigDirOption = Annotated[Optional[Path], typer.Option("--config-dir", help="Configuration directory")]
DryRunOption = Annotated[bool, typer.Option("--dry-run", help="Preview without executing")]
FieldsOption = Annotated[Optional[str], typer.Option("--fields", help="Comma-separated list of fields to include")]
ExcludeFieldsOption = Annotated[Optional[str], typer.Option("--exclude", help="Comma-separated list of fields to exclude")]
PageOption = Annotated[int, typer.Option("--page", help="Page number for pagination")]
PageSizeOption = Annotated[int, typer.Option("--page-size", help="Number of items per page")]


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
    '_create_config_service',
    '_create_repository_resolver',
    'ConfigService',
    'RepositoryResolver',
    'CommandRegistry',
    'CommandMetadata',
    'CommandCategory',
    'get_command_registry',
    'register_core_commands',
    'register_optional_commands',
    'register_all_commands',
    'VerboseOption',
    'JsonOption',
    'FormatOption',
    'QuietOption',
    'NonInteractiveOption',
    'YesOption',
    'ConfigDirOption',
    'DryRunOption',
    'FieldsOption',
    'ExcludeFieldsOption',
    'PageOption',
    'PageSizeOption',
    'OutputFormatter',
    'OutputFormat',
    'ExitCode',
    'create_formatter',
    'format_success_json',
    'format_error_json',
    'require_parameter',
    'validate_parameters',
    'with_non_interactive_check',
    'exit_with_code',
    'handle_operation_result',
    'NonInteractiveError',
    'ensure_interactive_or_fail',
    'OutputFilter',
    'Paginator',
    'PaginationInfo',
    'QuietMode',
    'create_filter',
    'create_paginator',
    'apply_filters_and_pagination',
    'filter_sensitive_fields',
]
