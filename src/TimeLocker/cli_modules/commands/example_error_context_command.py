"""
Example command demonstrating ErrorContext usage in CLI commands.

This module serves as a reference implementation showing how to use the
ErrorContext system for better error handling, context tracking, and
recovery suggestions in CLI commands.
"""

from typing import Optional
from pathlib import Path

import typer
from rich.table import Table
from rich.panel import Panel

from .base import (
    create_typer_app,
    VerboseOption,
    JsonOption,
    QuietOption,
    ConfigDirOption,
    setup_logging,
    console,
    create_formatter,
    ExitCode,
)
from ..helpers import (
    with_cli_error_context,
    show_cli_error,
    add_common_recovery_suggestions,
)
from TimeLocker.utils.error_handling import ErrorContext

# Create example app
error_context_app = create_typer_app(
    name="error-context-example",
    help_text="Example commands demonstrating ErrorContext usage"
)


@error_context_app.command("simple")
@with_cli_error_context("example_simple", "ErrorContextExample")
def example_simple(
    name: str = typer.Argument(..., help="Item name"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Simple example showing automatic error context tracking.
    
    This command demonstrates:
    - Automatic error context tracking with decorator
    - User-friendly error formatting
    - Recovery suggestions
    """
    setup_logging(verbose, config_dir)
    formatter = create_formatter(json_output=json_output, quiet=False, console=console)
    
    # Simulate an operation that might fail
    if name == "fail":
        raise ValueError("Invalid item name: 'fail' is not allowed")
    
    # Success case
    formatter.success(f"Successfully processed item '{name}'")
    raise typer.Exit(ExitCode.SUCCESS.value)


@error_context_app.command("nested")
def example_nested(
    name: str = typer.Argument(..., help="Item name"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example showing nested error contexts.
    
    This command demonstrates:
    - Nested error context tracking
    - Context preservation through call stack
    - Parent context in error messages
    """
    setup_logging(verbose, config_dir)
    formatter = create_formatter(json_output=json_output, quiet=False, console=console)
    
    try:
        with ErrorContext("validate_input", "InputValidator") as ctx:
            ctx.add_context("name", name)
            
            # Simulate validation
            if not name or len(name) < 3:
                ctx.add_recovery_suggestion("Provide a name with at least 3 characters")
                raise ValueError("Name must be at least 3 characters long")
            
            # Nested operation
            with ErrorContext("process_item", "ItemProcessor") as inner_ctx:
                inner_ctx.add_context("validated_name", name)
                
                # Simulate processing
                if name == "error":
                    inner_ctx.add_recovery_suggestion("Try a different item name")
                    raise RuntimeError("Failed to process item")
                
                formatter.success(f"Successfully processed item '{name}'")
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except Exception as e:
        # Error will have full context chain
        show_cli_error(e, ctx if 'ctx' in locals() else None)
        raise typer.Exit(ExitCode.ERROR.value)


@error_context_app.command("recovery")
def example_recovery(
    operation: str = typer.Argument(..., help="Operation to perform"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example showing recovery suggestions for different error types.
    
    This command demonstrates:
    - Custom recovery suggestions
    - Error-type-specific suggestions
    - Common recovery patterns
    """
    setup_logging(verbose, config_dir)
    formatter = create_formatter(json_output=json_output, quiet=False, console=console)
    
    try:
        with ErrorContext("perform_operation", "OperationHandler") as ctx:
            ctx.add_context("operation", operation)
            
            if operation == "config":
                # Simulate config error
                add_common_recovery_suggestions(ctx, "config")
                raise ValueError("Configuration file not found")
            
            elif operation == "repository":
                # Simulate repository error
                add_common_recovery_suggestions(ctx, "repository")
                raise FileNotFoundError("Repository not accessible")
            
            elif operation == "network":
                # Simulate network error
                add_common_recovery_suggestions(ctx, "network")
                raise ConnectionError("Failed to connect to remote server")
            
            elif operation == "permission":
                # Simulate permission error
                add_common_recovery_suggestions(ctx, "permission")
                raise PermissionError("Access denied to resource")
            
            else:
                formatter.success(f"Successfully performed operation '{operation}'")
                raise typer.Exit(ExitCode.SUCCESS.value)
    
    except Exception as e:
        show_cli_error(e, ctx if 'ctx' in locals() else None)
        raise typer.Exit(ExitCode.ERROR.value)


@error_context_app.command("custom")
def example_custom(
    name: str = typer.Argument(..., help="Item name"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example showing custom error context and suggestions.
    
    This command demonstrates:
    - Custom context metadata
    - Custom recovery suggestions
    - Detailed error information
    """
    setup_logging(verbose, config_dir)
    formatter = create_formatter(json_output=json_output, quiet=False, console=console)
    
    try:
        with ErrorContext("custom_operation", "CustomHandler") as ctx:
            # Add custom context
            ctx.add_context("item_name", name)
            ctx.add_context("operation_type", "custom")
            ctx.add_context("user_input", {"name": name})
            
            # Add custom recovery suggestions
            ctx.add_recovery_suggestion("Check the item name format")
            ctx.add_recovery_suggestion("Ensure the item exists in the system")
            ctx.add_recovery_suggestion("Review the operation logs for details")
            
            # Simulate operation
            if name.startswith("invalid"):
                raise ValueError(f"Invalid item name format: {name}")
            
            formatter.success(f"Successfully processed custom operation for '{name}'")
            raise typer.Exit(ExitCode.SUCCESS.value)
    
    except Exception as e:
        show_cli_error(e, ctx if 'ctx' in locals() else None)
        raise typer.Exit(ExitCode.ERROR.value)


@error_context_app.command("multi-step")
def example_multi_step(
    name: str = typer.Argument(..., help="Item name"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    config_dir: ConfigDirOption = None,
) -> None:
    """
    Example showing multi-step operation with context tracking.
    
    This command demonstrates:
    - Multiple operation steps with context
    - Context accumulation through steps
    - Step-specific error handling
    """
    setup_logging(verbose, config_dir)
    formatter = create_formatter(json_output=json_output, quiet=False, console=console)
    
    try:
        # Step 1: Validation
        with ErrorContext("validate", "Validator") as ctx1:
            ctx1.add_context("step", 1)
            ctx1.add_context("name", name)
            
            if not name:
                ctx1.add_recovery_suggestion("Provide a valid item name")
                raise ValueError("Item name is required")
            
            console.print("[green]✓[/green] Step 1: Validation complete")
        
        # Step 2: Preparation
        with ErrorContext("prepare", "Preparer") as ctx2:
            ctx2.add_context("step", 2)
            ctx2.add_context("validated_name", name)
            
            if name == "prepare-fail":
                ctx2.add_recovery_suggestion("Check system resources")
                raise RuntimeError("Failed to prepare operation")
            
            console.print("[green]✓[/green] Step 2: Preparation complete")
        
        # Step 3: Execution
        with ErrorContext("execute", "Executor") as ctx3:
            ctx3.add_context("step", 3)
            ctx3.add_context("prepared_name", name)
            
            if name == "execute-fail":
                ctx3.add_recovery_suggestion("Retry the operation")
                ctx3.add_recovery_suggestion("Check operation logs")
                raise RuntimeError("Failed to execute operation")
            
            console.print("[green]✓[/green] Step 3: Execution complete")
        
        formatter.success(f"Successfully completed all steps for '{name}'")
        raise typer.Exit(ExitCode.SUCCESS.value)
    
    except Exception as e:
        # Error will show which step failed with full context
        show_cli_error(e, locals().get('ctx1') or locals().get('ctx2') or locals().get('ctx3'))
        raise typer.Exit(ExitCode.ERROR.value)


# Export the app
__all__ = ["error_context_app"]
