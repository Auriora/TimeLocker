"""
Interactive prompt utilities for CLI commands.

This module provides smart prompts for missing parameters, parameter validation,
and default value suggestions for interactive CLI operations.

This module now uses PromptService for consistent prompt handling.

Requirements addressed:
- 3.1: Interactive mode with prompts for missing required parameters
- 3.3: Display current configuration values during edit operations
"""

import sys
import re
from typing import Optional, List, Dict, Any, Callable, TypeVar, Union
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from TimeLocker.utils import PromptService, PromptError

console = Console(width=100)
_prompt_service = PromptService(console=console)

T = TypeVar('T')


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def is_interactive() -> bool:
    """
    Check if running in interactive mode.
    
    Returns:
        bool: True if stdin is a TTY (interactive terminal)
    """
    return _prompt_service.is_interactive()


def prompt_for_value(
    prompt_text: str,
    default: Optional[str] = None,
    current_value: Optional[str] = None,
    required: bool = True,
    password: bool = False,
    validator: Optional[Callable[[str], bool]] = None,
    error_message: Optional[str] = None,
    choices: Optional[List[str]] = None
) -> Optional[str]:
    """
    Prompt user for a value with validation and default handling.
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default value if user provides no input
        current_value: Current value to display (for edit operations)
        required: Whether the value is required
        password: Whether to hide input (for passwords)
        validator: Optional validation function
        error_message: Custom error message for validation failures
        choices: Optional list of valid choices
        
    Returns:
        User input or default value, None if not required and no input
        
    Raises:
        ValidationError: If validation fails in non-interactive mode
    """
    try:
        if choices:
            return _prompt_service.prompt_choice(
                message=prompt_text,
                choices=choices,
                default=default,
                required=required,
                current_value=current_value
            )
        else:
            return _prompt_service.prompt_text(
                message=prompt_text,
                default=default,
                required=required,
                password=password,
                validator=validator,
                error_message=error_message,
                current_value=current_value
            )
    except PromptError as e:
        raise ValidationError(str(e))


def prompt_for_int(
    prompt_text: str,
    default: Optional[int] = None,
    current_value: Optional[int] = None,
    required: bool = True,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> Optional[int]:
    """
    Prompt user for an integer value with validation.
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default value if user provides no input
        current_value: Current value to display (for edit operations)
        required: Whether the value is required
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        User input as integer or default value
        
    Raises:
        ValidationError: If validation fails in non-interactive mode
    """
    try:
        return _prompt_service.prompt_int(
            message=prompt_text,
            default=default,
            required=required,
            min_value=min_value,
            max_value=max_value,
            current_value=current_value
        )
    except PromptError as e:
        raise ValidationError(str(e))


def prompt_for_bool(
    prompt_text: str,
    default: bool = False,
    current_value: Optional[bool] = None
) -> bool:
    """
    Prompt user for a yes/no confirmation.
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default value if user provides no input
        current_value: Current value to display (for edit operations)
        
    Returns:
        User's boolean choice
    """
    return _prompt_service.prompt_confirm(
        message=prompt_text,
        default=default,
        current_value=current_value
    )


def prompt_for_path(
    prompt_text: str,
    default: Optional[Path] = None,
    current_value: Optional[Path] = None,
    required: bool = True,
    must_exist: bool = False,
    must_be_dir: bool = False,
    must_be_file: bool = False
) -> Optional[Path]:
    """
    Prompt user for a file system path with validation.
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default path if user provides no input
        current_value: Current path to display (for edit operations)
        required: Whether the path is required
        must_exist: Whether the path must exist
        must_be_dir: Whether the path must be a directory
        must_be_file: Whether the path must be a file
        
    Returns:
        User input as Path or default value
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return _prompt_service.prompt_path(
            message=prompt_text,
            default=default,
            required=required,
            must_exist=must_exist,
            must_be_dir=must_be_dir,
            must_be_file=must_be_file,
            current_value=current_value
        )
    except PromptError as e:
        raise ValidationError(str(e))


def prompt_for_list(
    prompt_text: str,
    default: Optional[List[str]] = None,
    current_value: Optional[List[str]] = None,
    separator: str = ",",
    required: bool = False
) -> List[str]:
    """
    Prompt user for a list of values (comma-separated by default).
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default list if user provides no input
        current_value: Current list to display (for edit operations)
        separator: Character to split input on
        required: Whether at least one value is required
        
    Returns:
        List of user input values
    """
    return _prompt_service.prompt_list(
        message=prompt_text,
        default=default,
        separator=separator,
        required=required,
        current_value=current_value
    )


def display_current_config(title: str, config: Dict[str, Any]) -> None:
    """
    Display current configuration values in a formatted table.
    
    Args:
        title: Title for the configuration display
        config: Dictionary of configuration key-value pairs
    """
    if not config:
        return
    
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Current Value", style="green")
    
    for key, value in config.items():
        # Format the key nicely
        display_key = key.replace('_', ' ').title()
        
        # Format the value
        if isinstance(value, bool):
            display_value = "Yes" if value else "No"
        elif isinstance(value, (list, tuple)):
            display_value = ", ".join(str(v) for v in value) if value else "(none)"
        elif value is None:
            display_value = "(not set)"
        else:
            display_value = str(value)
        
        table.add_row(display_key, display_value)
    
    console.print(table)
    console.print()


def prompt_to_keep_or_change(field_name: str, current_value: Any) -> bool:
    """
    Ask user if they want to keep the current value or change it.
    
    Uses PromptService for consistent prompt handling.
    
    Args:
        field_name: Name of the field being edited
        current_value: Current value of the field
        
    Returns:
        True if user wants to change the value, False to keep current
    """
    return _prompt_service.prompt_to_change(field_name, current_value)


def validate_repository_name(name: str) -> bool:
    """
    Validate repository name format.
    
    Args:
        name: Repository name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or not name.strip():
        return False
    
    # Repository names should be alphanumeric with dashes, underscores, or dots
    pattern = r'^[a-zA-Z0-9._-]+$'
    if not re.match(pattern, name):
        console.print("[yellow]Repository name must contain only letters, numbers, dashes, underscores, or dots[/yellow]")
        return False
    
    return True


def validate_uri(uri: str) -> bool:
    """
    Validate repository URI format.
    
    Args:
        uri: URI to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not uri or not uri.strip():
        return False
    
    # Check for common URI patterns
    valid_prefixes = ['file://', 's3://', 'b2://', 'azure://', 'gs://', 'rest://', 'rclone://', '/']
    
    if not any(uri.startswith(prefix) for prefix in valid_prefixes):
        console.print(f"[yellow]URI must start with one of: {', '.join(valid_prefixes)}[/yellow]")
        return False
    
    return True


def show_help_text(text: str) -> None:
    """
    Display help text in a formatted panel.
    
    Args:
        text: Help text to display
    """
    panel = Panel(
        text,
        title="[bold blue]Help[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)


__all__ = [
    'is_interactive',
    'prompt_for_value',
    'prompt_for_int',
    'prompt_for_bool',
    'prompt_for_path',
    'prompt_for_list',
    'display_current_config',
    'prompt_to_keep_or_change',
    'validate_repository_name',
    'validate_uri',
    'show_help_text',
    'ValidationError',
]
