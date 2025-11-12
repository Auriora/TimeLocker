"""
Centralized prompt service for CLI interactive operations.

This module provides a unified interface for interactive prompts with consistent
non-interactive mode handling, validation patterns, and reusable templates.

Requirements addressed:
- Requirement 4: Consistent interactive prompts through PromptService
- 4.1: Provide consistent interactive prompts for text, choice, confirmation, and password inputs
- 4.2: Automatically handle non-interactive mode with default values or errors
- 4.3: Support prompt validation with reusable validation patterns
- 4.4: Reduce prompt-related code by at least 80 lines across 25 commands
- 4.5: Provide clear error messages for missing required input in non-interactive mode
"""

import sys
import logging
from typing import Optional, List, Callable, Any, TypeVar, Union
from pathlib import Path

from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.console import Console

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PromptError(Exception):
    """Raised when prompt operations fail."""
    pass


class PromptService:
    """
    Centralized service for interactive prompts with consistent behavior.
    
    This service provides a unified interface for all CLI prompts, handling:
    - Interactive vs non-interactive mode detection
    - Consistent validation patterns
    - Default value handling
    - Error messaging
    - Prompt templates for common patterns
    
    Requirements addressed:
    - 4.1: Consistent interactive prompts for text, choice, confirmation, and password inputs
    - 4.2: Automatic non-interactive mode handling
    - 4.3: Prompt validation with reusable patterns
    """
    
    def __init__(self, console: Optional[Console] = None, force_interactive: Optional[bool] = None):
        """
        Initialize the prompt service.
        
        Args:
            console: Optional Rich console instance. If None, creates a new one.
            force_interactive: Optional override for interactive mode detection.
                             If None, uses stdin.isatty() to detect.
        """
        self._console = console or Console(width=100)
        self._force_interactive = force_interactive
        logger.debug("PromptService initialized")
    
    def is_interactive(self) -> bool:
        """
        Check if running in interactive mode.
        
        Returns:
            bool: True if stdin is a TTY (interactive terminal) or forced interactive
        """
        if self._force_interactive is not None:
            return self._force_interactive
        return sys.stdin.isatty()
    
    def prompt_text(
        self,
        message: str,
        default: Optional[str] = None,
        required: bool = True,
        password: bool = False,
        validator: Optional[Callable[[str], bool]] = None,
        error_message: Optional[str] = None,
        current_value: Optional[str] = None
    ) -> Optional[str]:
        """
        Prompt user for text input with validation.
        
        Args:
            message: Prompt message to display
            default: Default value if user provides no input
            required: Whether the value is required
            password: Whether to hide input (for passwords)
            validator: Optional validation function that returns True if valid
            error_message: Custom error message for validation failures
            current_value: Current value to display (for edit operations)
            
        Returns:
            User input or default value, None if not required and no input
            
        Raises:
            PromptError: If required value is missing in non-interactive mode
        
        Requirements addressed:
        - 4.1: Text input prompts
        - 4.2: Non-interactive mode handling
        - 4.3: Validation support
        """
        if not self.is_interactive():
            if required and default is None and current_value is None:
                raise PromptError(f"{message} is required in non-interactive mode")
            return default or current_value
        
        # Build prompt with current value display
        full_prompt = message
        if current_value is not None:
            full_prompt = f"{message} (current: {current_value})"
        
        while True:
            try:
                if password:
                    value = Prompt.ask(full_prompt, password=True, default=default or "", console=self._console)
                else:
                    value = Prompt.ask(full_prompt, default=default or "", console=self._console)
                
                # Handle empty input
                if not value or not value.strip():
                    if required and current_value is None:
                        self._console.print("[yellow]This field is required. Please provide a value.[/yellow]")
                        continue
                    return current_value if current_value is not None else None
                
                value = value.strip()
                
                # Run custom validator
                if validator:
                    try:
                        if not validator(value):
                            msg = error_message or "Invalid input. Please try again."
                            self._console.print(f"[yellow]{msg}[/yellow]")
                            continue
                    except Exception as e:
                        self._console.print(f"[yellow]Validation error: {e}[/yellow]")
                        continue
                
                return value
                
            except KeyboardInterrupt:
                raise
            except EOFError:
                if required and current_value is None:
                    raise PromptError(f"{message} is required")
                return current_value
    
    def prompt_choice(
        self,
        message: str,
        choices: List[str],
        default: Optional[str] = None,
        required: bool = True,
        current_value: Optional[str] = None
    ) -> Optional[str]:
        """
        Prompt user to select from a list of choices.
        
        Args:
            message: Prompt message to display
            choices: List of valid choices
            default: Default choice if user provides no input
            required: Whether a choice is required
            current_value: Current value to display (for edit operations)
            
        Returns:
            Selected choice or default value
            
        Raises:
            PromptError: If required choice is missing in non-interactive mode
        
        Requirements addressed:
        - 4.1: Choice input prompts
        - 4.2: Non-interactive mode handling
        """
        if not choices:
            raise ValueError("Choices list cannot be empty")
        
        if not self.is_interactive():
            if required and default is None and current_value is None:
                raise PromptError(f"{message} is required in non-interactive mode")
            return default or current_value
        
        # Build prompt with choices and current value
        full_prompt = message
        if current_value is not None:
            full_prompt = f"{message} (current: {current_value})"
        full_prompt = f"{full_prompt} [{'/'.join(choices)}]"
        
        while True:
            try:
                value = Prompt.ask(full_prompt, default=default or "", console=self._console)
                
                # Handle empty input
                if not value or not value.strip():
                    if required and current_value is None:
                        self._console.print("[yellow]This field is required. Please select a value.[/yellow]")
                        continue
                    return current_value if current_value is not None else None
                
                value = value.strip()
                
                # Validate choice
                if value not in choices:
                    self._console.print(f"[yellow]Invalid choice. Please select from: {', '.join(choices)}[/yellow]")
                    continue
                
                return value
                
            except KeyboardInterrupt:
                raise
            except EOFError:
                if required and current_value is None:
                    raise PromptError(f"{message} is required")
                return current_value
    
    def prompt_confirm(
        self,
        message: str,
        default: bool = False,
        current_value: Optional[bool] = None
    ) -> bool:
        """
        Prompt user for yes/no confirmation.
        
        Args:
            message: Prompt message to display
            default: Default value if user provides no input
            current_value: Current value to display (for edit operations)
            
        Returns:
            User's boolean choice
        
        Requirements addressed:
        - 4.1: Confirmation prompts
        - 4.2: Non-interactive mode handling
        """
        if not self.is_interactive():
            return current_value if current_value is not None else default
        
        # Build prompt with current value display
        full_prompt = message
        if current_value is not None:
            full_prompt = f"{message} (current: {'yes' if current_value else 'no'})"
        
        try:
            return Confirm.ask(
                full_prompt,
                default=current_value if current_value is not None else default,
                console=self._console
            )
        except (KeyboardInterrupt, EOFError):
            return current_value if current_value is not None else default
    
    def prompt_password(
        self,
        message: str,
        required: bool = True,
        validator: Optional[Callable[[str], bool]] = None,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Prompt user for password input (hidden).
        
        Args:
            message: Prompt message to display
            required: Whether the password is required
            validator: Optional validation function
            error_message: Custom error message for validation failures
            
        Returns:
            Password string or None if not required and no input
            
        Raises:
            PromptError: If required password is missing in non-interactive mode
        
        Requirements addressed:
        - 4.1: Password input prompts
        - 4.2: Non-interactive mode handling
        - 4.3: Validation support
        """
        return self.prompt_text(
            message=message,
            default=None,
            required=required,
            password=True,
            validator=validator,
            error_message=error_message
        )
    
    def prompt_int(
        self,
        message: str,
        default: Optional[int] = None,
        required: bool = True,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        current_value: Optional[int] = None
    ) -> Optional[int]:
        """
        Prompt user for integer input with validation.
        
        Args:
            message: Prompt message to display
            default: Default value if user provides no input
            required: Whether the value is required
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            current_value: Current value to display (for edit operations)
            
        Returns:
            User input as integer or default value
            
        Raises:
            PromptError: If required value is missing in non-interactive mode
        
        Requirements addressed:
        - 4.1: Integer input prompts
        - 4.2: Non-interactive mode handling
        - 4.3: Range validation
        """
        if not self.is_interactive():
            if required and default is None and current_value is None:
                raise PromptError(f"{message} is required in non-interactive mode")
            return default or current_value
        
        # Build prompt with current value display
        full_prompt = message
        if current_value is not None:
            full_prompt = f"{message} (current: {current_value})"
        
        while True:
            try:
                value = IntPrompt.ask(
                    full_prompt,
                    default=default or current_value,
                    console=self._console
                )
                
                # Validate range
                if min_value is not None and value < min_value:
                    self._console.print(f"[yellow]Value must be at least {min_value}[/yellow]")
                    continue
                if max_value is not None and value > max_value:
                    self._console.print(f"[yellow]Value must be at most {max_value}[/yellow]")
                    continue
                
                return value
                
            except KeyboardInterrupt:
                raise
            except EOFError:
                if required and current_value is None:
                    raise PromptError(f"{message} is required")
                return current_value
    
    def prompt_float(
        self,
        message: str,
        default: Optional[float] = None,
        required: bool = True,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        current_value: Optional[float] = None
    ) -> Optional[float]:
        """
        Prompt user for float input with validation.
        
        Args:
            message: Prompt message to display
            default: Default value if user provides no input
            required: Whether the value is required
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            current_value: Current value to display (for edit operations)
            
        Returns:
            User input as float or default value
            
        Raises:
            PromptError: If required value is missing in non-interactive mode
        """
        if not self.is_interactive():
            if required and default is None and current_value is None:
                raise PromptError(f"{message} is required in non-interactive mode")
            return default or current_value
        
        # Build prompt with current value display
        full_prompt = message
        if current_value is not None:
            full_prompt = f"{message} (current: {current_value})"
        
        while True:
            try:
                value = FloatPrompt.ask(
                    full_prompt,
                    default=default or current_value,
                    console=self._console
                )
                
                # Validate range
                if min_value is not None and value < min_value:
                    self._console.print(f"[yellow]Value must be at least {min_value}[/yellow]")
                    continue
                if max_value is not None and value > max_value:
                    self._console.print(f"[yellow]Value must be at most {max_value}[/yellow]")
                    continue
                
                return value
                
            except KeyboardInterrupt:
                raise
            except EOFError:
                if required and current_value is None:
                    raise PromptError(f"{message} is required")
                return current_value
    
    def prompt_path(
        self,
        message: str,
        default: Optional[Path] = None,
        required: bool = True,
        must_exist: bool = False,
        must_be_dir: bool = False,
        must_be_file: bool = False,
        current_value: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Prompt user for file system path with validation.
        
        Args:
            message: Prompt message to display
            default: Default path if user provides no input
            required: Whether the path is required
            must_exist: Whether the path must exist
            must_be_dir: Whether the path must be a directory
            must_be_file: Whether the path must be a file
            current_value: Current path to display (for edit operations)
            
        Returns:
            User input as Path or default value
            
        Raises:
            PromptError: If required path is missing in non-interactive mode
        
        Requirements addressed:
        - 4.1: Path input prompts
        - 4.3: Path validation
        """
        def validate_path(path_str: str) -> bool:
            path = Path(path_str).expanduser()
            
            if must_exist and not path.exists():
                self._console.print(f"[yellow]Path does not exist: {path}[/yellow]")
                return False
            
            if must_be_dir and path.exists() and not path.is_dir():
                self._console.print(f"[yellow]Path must be a directory: {path}[/yellow]")
                return False
            
            if must_be_file and path.exists() and not path.is_file():
                self._console.print(f"[yellow]Path must be a file: {path}[/yellow]")
                return False
            
            return True
        
        default_str = str(default) if default else None
        current_str = str(current_value) if current_value else None
        
        result = self.prompt_text(
            message=message,
            default=default_str,
            required=required,
            validator=validate_path,
            current_value=current_str
        )
        
        return Path(result).expanduser() if result else None
    
    def prompt_list(
        self,
        message: str,
        default: Optional[List[str]] = None,
        separator: str = ",",
        required: bool = False,
        current_value: Optional[List[str]] = None
    ) -> List[str]:
        """
        Prompt user for a list of values (comma-separated by default).
        
        Args:
            message: Prompt message to display
            default: Default list if user provides no input
            separator: Character to split input on
            required: Whether at least one value is required
            current_value: Current list to display (for edit operations)
            
        Returns:
            List of user input values
        
        Requirements addressed:
        - 4.1: List input prompts
        """
        default_str = separator.join(default) if default else None
        current_str = separator.join(current_value) if current_value else None
        
        result = self.prompt_text(
            message=f"{message} (separate with '{separator}')",
            default=default_str,
            required=required,
            current_value=current_str
        )
        
        if not result:
            return current_value or default or []
        
        return [item.strip() for item in result.split(separator) if item.strip()]
    
    def prompt_to_change(
        self,
        field_name: str,
        current_value: Any
    ) -> bool:
        """
        Ask user if they want to keep the current value or change it.
        
        Args:
            field_name: Name of the field being edited
            current_value: Current value of the field
            
        Returns:
            True if user wants to change the value, False to keep current
        
        Requirements addressed:
        - 4.1: Edit confirmation prompts
        """
        if not self.is_interactive():
            return False
        
        display_value = str(current_value) if current_value is not None else "(not set)"
        return self.prompt_confirm(
            f"Change {field_name} (currently: {display_value})?",
            default=False
        )


# Singleton instance for convenience
_default_prompt_service: Optional[PromptService] = None


def get_prompt_service(console: Optional[Console] = None) -> PromptService:
    """
    Get the default PromptService instance.
    
    Args:
        console: Optional Rich console instance
        
    Returns:
        PromptService instance
    """
    global _default_prompt_service
    if _default_prompt_service is None:
        _default_prompt_service = PromptService(console=console)
    return _default_prompt_service


__all__ = [
    'PromptService',
    'PromptError',
    'get_prompt_service',
]
