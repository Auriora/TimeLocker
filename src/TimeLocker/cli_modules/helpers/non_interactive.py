"""
Non-interactive mode utilities for CLI commands.

This module provides utilities for handling non-interactive mode,
including parameter validation and exit code management.
"""

import sys
from typing import Any, Optional, Callable
from functools import wraps

import typer

from .output_formatter import ExitCode, OutputFormatter


def is_interactive() -> bool:
    """
    Check if running in interactive mode.
    
    Returns:
        True if stdin is a TTY (interactive terminal)
    """
    return sys.stdin.isatty()


def require_parameter(
    value: Optional[Any],
    parameter_name: str,
    formatter: Optional[OutputFormatter] = None,
    allow_interactive: bool = True
) -> Any:
    """
    Require a parameter value in non-interactive mode.
    
    Args:
        value: Parameter value (may be None)
        parameter_name: Name of the parameter for error messages
        formatter: Output formatter for error messages
        allow_interactive: Whether to allow interactive prompting
        
    Returns:
        The parameter value if provided
        
    Raises:
        typer.Exit: If parameter is missing in non-interactive mode
    """
    if value is None:
        interactive = is_interactive() and allow_interactive
        
        if not interactive:
            error_msg = f"Missing required parameter: {parameter_name}"
            
            if formatter and formatter.is_json_mode():
                formatter.error(
                    message=error_msg,
                    error_type="ValidationError",
                    code="MISSING_PARAMETER",
                    title="Missing Parameter"
                )
            else:
                from .display import show_error_panel
                show_error_panel(
                    "Missing Parameter",
                    f"{error_msg}. This parameter is required in non-interactive mode."
                )
            
            raise typer.Exit(ExitCode.VALIDATION_ERROR.value)
    
    return value


def validate_parameters(
    parameters: dict,
    formatter: Optional[OutputFormatter] = None,
    allow_interactive: bool = True
) -> None:
    """
    Validate that all required parameters are provided in non-interactive mode.
    
    Args:
        parameters: Dictionary of parameter_name -> value
        formatter: Output formatter for error messages
        allow_interactive: Whether to allow interactive prompting
        
    Raises:
        typer.Exit: If any required parameter is missing in non-interactive mode
    """
    interactive = is_interactive() and allow_interactive
    
    if not interactive:
        missing = [name for name, value in parameters.items() if value is None]
        
        if missing:
            error_msg = f"Missing required parameters: {', '.join(missing)}"
            
            if formatter and formatter.is_json_mode():
                formatter.error(
                    message=error_msg,
                    error_type="ValidationError",
                    details=[f"Parameter '{p}' is required" for p in missing],
                    code="MISSING_PARAMETERS",
                    title="Missing Parameters"
                )
            else:
                from .display import show_error_panel
                show_error_panel(
                    "Missing Parameters",
                    error_msg,
                    details=[f"Parameter '{p}' is required in non-interactive mode" for p in missing]
                )
            
            raise typer.Exit(ExitCode.VALIDATION_ERROR.value)


def with_non_interactive_check(
    required_params: Optional[list] = None
):
    """
    Decorator to add non-interactive parameter validation to commands.
    
    Args:
        required_params: List of parameter names that are required
        
    Example:
        @with_non_interactive_check(required_params=['name', 'uri'])
        def create_repository(name: Optional[str] = None, uri: Optional[str] = None):
            # Command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if non-interactive mode is explicitly requested
            non_interactive = kwargs.get('non_interactive', False)
            
            # If non-interactive flag is set, validate required parameters
            if non_interactive and required_params:
                missing = []
                for param in required_params:
                    if param in kwargs and kwargs[param] is None:
                        missing.append(param)
                
                if missing:
                    from .display import show_error_panel
                    show_error_panel(
                        "Missing Parameters",
                        f"Missing required parameters: {', '.join(missing)}",
                        details=[f"Parameter '{p}' is required in non-interactive mode" for p in missing]
                    )
                    raise typer.Exit(ExitCode.VALIDATION_ERROR.value)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def exit_with_code(
    code: ExitCode,
    formatter: Optional[OutputFormatter] = None,
    message: Optional[str] = None
) -> None:
    """
    Exit with appropriate exit code.
    
    Args:
        code: Exit code to use
        formatter: Output formatter for final message
        message: Optional exit message
    """
    if message and formatter:
        if code == ExitCode.SUCCESS:
            formatter.success(message)
        elif code == ExitCode.WARNING:
            formatter.warning(message)
        else:
            formatter.error(message)
    
    raise typer.Exit(code.value)


def handle_operation_result(
    success: bool,
    formatter: OutputFormatter,
    success_message: str,
    error_message: str,
    warning: bool = False,
    data: Optional[dict] = None,
    error_details: Optional[list] = None
) -> None:
    """
    Handle operation result and exit with appropriate code.
    
    Args:
        success: Whether operation was successful
        formatter: Output formatter
        success_message: Message to show on success
        error_message: Message to show on error
        warning: Whether to treat success as warning
        data: Optional data to include in output
        error_details: Optional error details
    """
    if success:
        if warning:
            formatter.warning(success_message)
            raise typer.Exit(ExitCode.WARNING.value)
        else:
            formatter.success(success_message, data=data)
            raise typer.Exit(ExitCode.SUCCESS.value)
    else:
        formatter.error(error_message, details=error_details)
        raise typer.Exit(ExitCode.ERROR.value)


class NonInteractiveError(Exception):
    """Raised when interactive input is required but not available."""
    
    def __init__(self, parameter_name: str, message: Optional[str] = None):
        self.parameter_name = parameter_name
        self.message = message or f"Parameter '{parameter_name}' is required in non-interactive mode"
        super().__init__(self.message)


def ensure_interactive_or_fail(
    parameter_name: str,
    formatter: Optional[OutputFormatter] = None
) -> None:
    """
    Ensure interactive mode is available or fail with appropriate error.
    
    Args:
        parameter_name: Name of parameter that requires interactive input
        formatter: Output formatter for error messages
        
    Raises:
        typer.Exit: If not in interactive mode
    """
    if not is_interactive():
        error_msg = f"Parameter '{parameter_name}' is required but not provided"
        
        if formatter and formatter.is_json_mode():
            formatter.error(
                message=error_msg,
                error_type="NonInteractiveError",
                code="INTERACTIVE_REQUIRED",
                details=[f"Cannot prompt for '{parameter_name}' in non-interactive mode"]
            )
        else:
            from .display import show_error_panel
            show_error_panel(
                "Interactive Mode Required",
                error_msg,
                details=[
                    f"Parameter '{parameter_name}' requires interactive input",
                    "Provide the parameter value or run in interactive mode"
                ]
            )
        
        raise typer.Exit(ExitCode.VALIDATION_ERROR.value)


__all__ = [
    "is_interactive",
    "require_parameter",
    "validate_parameters",
    "with_non_interactive_check",
    "exit_with_code",
    "handle_operation_result",
    "NonInteractiveError",
    "ensure_interactive_or_fail",
]
