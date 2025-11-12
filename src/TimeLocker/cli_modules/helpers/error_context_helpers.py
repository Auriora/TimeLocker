"""
Error context helpers for CLI commands.

This module provides helper functions and decorators for using ErrorContext
in CLI commands, making it easy to add context tracking and recovery suggestions.
"""

import logging
import typer
from functools import wraps
from typing import Callable, Optional, Any
from rich.console import Console
from rich.panel import Panel

from TimeLocker.utils.error_handling import (
    ErrorContext,
    error_handler,
    format_error_with_context,
    suggest_recovery
)

logger = logging.getLogger(__name__)
console = Console()


def with_cli_error_context(operation: str, component: str = "CLI"):
    """
    Decorator for CLI commands that adds error context tracking.
    
    This decorator wraps CLI commands with ErrorContext, providing:
    - Automatic error context tracking
    - User-friendly error formatting
    - Recovery suggestions
    - Consistent error reporting
    
    Args:
        operation: Operation being performed (e.g., "backup_create", "restore")
        component: Component name (defaults to "CLI")
        
    Returns:
        Decorator function
        
    Example:
        @with_cli_error_context("backup_create", "BackupCommand")
        def backup_create(sources, repository, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorContext(operation, component) as ctx:
                # Add command parameters to context
                if kwargs:
                    for key, value in kwargs.items():
                        # Don't log sensitive information
                        if key not in ['password', 'token', 'secret', 'key']:
                            ctx.add_context(key, value)
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Format and display error with context
                    show_cli_error(e, ctx)
                    raise typer.Exit(1)
        
        return wrapper
    return decorator


def show_cli_error(exception: Exception, context: Optional[ErrorContext] = None) -> None:
    """
    Display a CLI error with context and recovery suggestions.
    
    Args:
        exception: Exception to display
        context: Optional error context
    """
    # Format error with context
    if context:
        error_msg = context.format_error(exception)
    else:
        error_msg = f"❌ {type(exception).__name__}: {str(exception)}"
    
    # Display in a panel for better visibility
    console.print(Panel(
        error_msg,
        title="[bold red]Error[/bold red]",
        border_style="red"
    ))
    
    # Log the error
    logger.error(f"CLI error: {exception}", exc_info=True)


def add_common_recovery_suggestions(context: ErrorContext, error_type: str) -> None:
    """
    Add common recovery suggestions based on error type.
    
    Args:
        context: Error context to add suggestions to
        error_type: Type of error (e.g., "config", "repository", "network")
    """
    if error_type == "config":
        context.add_recovery_suggestion("Check your configuration file for errors")
        context.add_recovery_suggestion("Run 'tl config validate' to verify configuration")
        context.add_recovery_suggestion("Review the configuration documentation")
    
    elif error_type == "repository":
        context.add_recovery_suggestion("Verify the repository path or name is correct")
        context.add_recovery_suggestion("Check repository credentials")
        context.add_recovery_suggestion("Ensure the repository is accessible")
        context.add_recovery_suggestion("Run 'tl repositories list' to see available repositories")
    
    elif error_type == "network":
        context.add_recovery_suggestion("Check your network connection")
        context.add_recovery_suggestion("Verify firewall settings")
        context.add_recovery_suggestion("Try again after a short delay")
    
    elif error_type == "permission":
        context.add_recovery_suggestion("Check file/directory permissions")
        context.add_recovery_suggestion("Ensure you have necessary access rights")
        context.add_recovery_suggestion("Try running with appropriate privileges")
    
    elif error_type == "validation":
        context.add_recovery_suggestion("Check that all required parameters are provided")
        context.add_recovery_suggestion("Verify parameter values are in correct format")
        context.add_recovery_suggestion("Review command documentation with 'tl --help'")


def handle_config_error(exception: Exception, context: ErrorContext) -> None:
    """
    Handle configuration-related errors with appropriate context.
    
    Args:
        exception: Configuration exception
        context: Error context
    """
    add_common_recovery_suggestions(context, "config")
    show_cli_error(exception, context)


def handle_repository_error(exception: Exception, context: ErrorContext) -> None:
    """
    Handle repository-related errors with appropriate context.
    
    Args:
        exception: Repository exception
        context: Error context
    """
    add_common_recovery_suggestions(context, "repository")
    show_cli_error(exception, context)


def handle_validation_error(exception: Exception, context: ErrorContext) -> None:
    """
    Handle validation errors with appropriate context.
    
    Args:
        exception: Validation exception
        context: Error context
    """
    add_common_recovery_suggestions(context, "validation")
    show_cli_error(exception, context)


# Register common error handlers
def register_cli_error_handlers() -> None:
    """Register common error handlers for CLI commands"""
    from TimeLocker.interfaces.exceptions import ConfigurationError
    from TimeLocker.config.configuration_manager import RepositoryNotFoundError
    
    # Register handlers for common exception types
    try:
        error_handler.register_error_callback(
            ConfigurationError,
            lambda exc, ctx: handle_config_error(exc, ctx) if ctx else None
        )
        
        error_handler.register_error_callback(
            RepositoryNotFoundError,
            lambda exc, ctx: handle_repository_error(exc, ctx) if ctx else None
        )
        
        error_handler.register_error_callback(
            ValueError,
            lambda exc, ctx: handle_validation_error(exc, ctx) if ctx else None
        )
    except Exception as e:
        logger.warning(f"Error registering CLI error handlers: {e}")


# Register handlers on module import
register_cli_error_handlers()
