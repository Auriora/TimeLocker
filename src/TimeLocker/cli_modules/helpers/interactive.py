"""
Interactive prompt utilities for CLI commands.

This module provides smart prompts for missing parameters, parameter validation,
and default value suggestions for interactive CLI operations.

Requirements addressed:
- 3.1: Interactive mode with prompts for missing required parameters
- 3.3: Display current configuration values during edit operations
"""

import sys
import re
from typing import Optional, List, Dict, Any, Callable, TypeVar, Union
from pathlib import Path

from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(width=100)

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
    return sys.stdin.isatty()


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
    if not is_interactive():
        if required and default is None and current_value is None:
            raise ValidationError(f"{prompt_text} is required in non-interactive mode")
        return default or current_value
    
    # Build prompt with current value display
    full_prompt = prompt_text
    if current_value is not None:
        full_prompt = f"{prompt_text} (current: {current_value})"
    
    # Add choices to prompt if provided
    if choices:
        full_prompt = f"{full_prompt} [{'/'.join(choices)}]"
    
    while True:
        try:
            if password:
                value = Prompt.ask(full_prompt, password=True, default=default or "")
            else:
                value = Prompt.ask(full_prompt, default=default or "")
            
            # Handle empty input
            if not value or not value.strip():
                if required and current_value is None:
                    console.print("[yellow]This field is required. Please provide a value.[/yellow]")
                    continue
                return current_value if current_value is not None else None
            
            value = value.strip()
            
            # Validate choices
            if choices and value not in choices:
                console.print(f"[yellow]Invalid choice. Please select from: {', '.join(choices)}[/yellow]")
                continue
            
            # Run custom validator
            if validator:
                try:
                    if not validator(value):
                        msg = error_message or "Invalid input. Please try again."
                        console.print(f"[yellow]{msg}[/yellow]")
                        continue
                except Exception as e:
                    console.print(f"[yellow]Validation error: {e}[/yellow]")
                    continue
            
            return value
            
        except KeyboardInterrupt:
            raise
        except EOFError:
            if required and current_value is None:
                raise ValidationError(f"{prompt_text} is required")
            return current_value


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
    if not is_interactive():
        if required and default is None and current_value is None:
            raise ValidationError(f"{prompt_text} is required in non-interactive mode")
        return default or current_value
    
    # Build prompt with current value display
    full_prompt = prompt_text
    if current_value is not None:
        full_prompt = f"{prompt_text} (current: {current_value})"
    
    while True:
        try:
            value = IntPrompt.ask(full_prompt, default=default or current_value)
            
            # Validate range
            if min_value is not None and value < min_value:
                console.print(f"[yellow]Value must be at least {min_value}[/yellow]")
                continue
            if max_value is not None and value > max_value:
                console.print(f"[yellow]Value must be at most {max_value}[/yellow]")
                continue
            
            return value
            
        except KeyboardInterrupt:
            raise
        except EOFError:
            if required and current_value is None:
                raise ValidationError(f"{prompt_text} is required")
            return current_value


def prompt_for_bool(
    prompt_text: str,
    default: bool = False,
    current_value: Optional[bool] = None
) -> bool:
    """
    Prompt user for a yes/no confirmation.
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default value if user provides no input
        current_value: Current value to display (for edit operations)
        
    Returns:
        User's boolean choice
    """
    if not is_interactive():
        return current_value if current_value is not None else default
    
    # Build prompt with current value display
    full_prompt = prompt_text
    if current_value is not None:
        full_prompt = f"{prompt_text} (current: {'yes' if current_value else 'no'})"
    
    return Confirm.ask(full_prompt, default=current_value if current_value is not None else default)


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
    def validate_path(path_str: str) -> bool:
        path = Path(path_str).expanduser()
        
        if must_exist and not path.exists():
            console.print(f"[yellow]Path does not exist: {path}[/yellow]")
            return False
        
        if must_be_dir and path.exists() and not path.is_dir():
            console.print(f"[yellow]Path must be a directory: {path}[/yellow]")
            return False
        
        if must_be_file and path.exists() and not path.is_file():
            console.print(f"[yellow]Path must be a file: {path}[/yellow]")
            return False
        
        return True
    
    default_str = str(default) if default else None
    current_str = str(current_value) if current_value else None
    
    result = prompt_for_value(
        prompt_text,
        default=default_str,
        current_value=current_str,
        required=required,
        validator=validate_path
    )
    
    return Path(result).expanduser() if result else None


def prompt_for_list(
    prompt_text: str,
    default: Optional[List[str]] = None,
    current_value: Optional[List[str]] = None,
    separator: str = ",",
    required: bool = False
) -> List[str]:
    """
    Prompt user for a list of values (comma-separated by default).
    
    Args:
        prompt_text: Text to display in the prompt
        default: Default list if user provides no input
        current_value: Current list to display (for edit operations)
        separator: Character to split input on
        required: Whether at least one value is required
        
    Returns:
        List of user input values
    """
    default_str = separator.join(default) if default else None
    current_str = separator.join(current_value) if current_value else None
    
    result = prompt_for_value(
        f"{prompt_text} (separate with '{separator}')",
        default=default_str,
        current_value=current_str,
        required=required
    )
    
    if not result:
        return current_value or default or []
    
    return [item.strip() for item in result.split(separator) if item.strip()]


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
    
    Args:
        field_name: Name of the field being edited
        current_value: Current value of the field
        
    Returns:
        True if user wants to change the value, False to keep current
    """
    if not is_interactive():
        return False
    
    display_value = str(current_value) if current_value is not None else "(not set)"
    return Confirm.ask(
        f"Change {field_name} (currently: {display_value})?",
        default=False
    )


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
