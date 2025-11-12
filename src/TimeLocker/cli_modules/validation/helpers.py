"""
Validation helpers for CLI commands.

This module provides convenient helper functions that wrap the ValidationFramework
for easy use in CLI commands. These helpers handle common validation scenarios
and provide consistent error handling.
"""

from pathlib import Path
from typing import Optional, Set, List
import typer

from .base import ValidationError as BaseValidationError
from .common import (
    PathValidator,
    NameValidator,
    EmailValidator,
    URLValidator,
    PortValidator,
    CronValidator,
    IntegerRangeValidator,
    StringLengthValidator,
)


class ValidationError(Exception):
    """
    CLI validation error.
    
    This exception is raised when validation fails in CLI commands.
    It's compatible with the existing ValidationError in base.py but
    provides a simpler interface for CLI usage.
    """
    pass


def validate_required_string(
    value: Optional[str],
    field_name: str = "value",
    min_length: int = 1
) -> str:
    """
    Validate that a string is not empty.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        min_length: Minimum length (default: 1)
        
    Returns:
        The validated and stripped value
        
    Raises:
        ValidationError: If value is None or empty
    """
    if not value or not value.strip():
        raise ValidationError(f"{field_name} cannot be empty")
    
    stripped = value.strip()
    if len(stripped) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    
    return stripped


def validate_path(
    path: Path,
    must_exist: bool = False,
    must_not_exist: bool = False,
    must_be_file: bool = False,
    must_be_directory: bool = False,
    must_be_readable: bool = False,
    must_be_writable: bool = False,
    field_name: str = "path"
) -> Path:
    """
    Validate a file system path.
    
    Args:
        path: Path to validate
        must_exist: Path must exist
        must_not_exist: Path must not exist
        must_be_file: Path must be a file
        must_be_directory: Path must be a directory
        must_be_readable: Path must be readable
        must_be_writable: Path must be writable
        field_name: Name of the field for error messages
        
    Returns:
        The validated path
        
    Raises:
        ValidationError: If validation fails
    """
    validator = PathValidator(
        must_exist=must_exist,
        must_not_exist=must_not_exist,
        must_be_file=must_be_file,
        must_be_directory=must_be_directory,
        must_be_readable=must_be_readable,
        must_be_writable=must_be_writable,
        field_name=field_name
    )
    
    result = validator.validate(path)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return path


def validate_name(
    name: str,
    field_name: str = "name",
    min_length: int = 1,
    max_length: int = 255,
    allow_spaces: bool = False,
    allow_special_chars: bool = False,
    reserved_names: Optional[Set[str]] = None
) -> str:
    """
    Validate a name (repository, policy, etc.).
    
    Args:
        name: Name to validate
        field_name: Name of the field for error messages
        min_length: Minimum name length
        max_length: Maximum name length
        allow_spaces: Allow spaces in names
        allow_special_chars: Allow special characters
        reserved_names: Set of reserved names
        
    Returns:
        The validated name
        
    Raises:
        ValidationError: If validation fails
    """
    validator = NameValidator(
        min_length=min_length,
        max_length=max_length,
        allow_spaces=allow_spaces,
        allow_special_chars=allow_special_chars,
        reserved_names=reserved_names,
        field_name=field_name
    )
    
    result = validator.validate(name)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return name


def validate_repository_name(name: str) -> str:
    """
    Validate a repository name.
    
    Repository names must:
    - Be 1-255 characters
    - Contain only letters, numbers, hyphens, underscores, and dots
    - Not be empty or whitespace
    
    Args:
        name: Repository name to validate
        
    Returns:
        The validated repository name
        
    Raises:
        ValidationError: If validation fails
    """
    # First check if empty
    if not name or not name.strip():
        raise ValidationError("Repository name cannot be empty or whitespace")
    
    # Use NameValidator with pattern for repository names
    validator = NameValidator(
        min_length=1,
        max_length=255,
        allow_spaces=False,
        allow_special_chars=True,  # We'll use pattern to control which chars
        pattern=r"^[A-Za-z0-9._-]+$",
        field_name="repository name"
    )
    
    result = validator.validate(name.strip())
    
    if not result.valid:
        # Provide more specific error message
        raise ValidationError(
            "Repository name contains unsupported characters. "
            "Use letters, numbers, dashes, underscores, or dots."
        )
    
    return name.strip()


def validate_email(email: str, field_name: str = "email") -> str:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated email address
        
    Raises:
        ValidationError: If validation fails
    """
    validator = EmailValidator(field_name=field_name)
    result = validator.validate(email)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return email


def validate_url(
    url: str,
    allowed_schemes: Optional[List[str]] = None,
    require_scheme: bool = True,
    field_name: str = "url"
) -> str:
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes
        require_scheme: Require URL to have a scheme
        field_name: Name of the field for error messages
        
    Returns:
        The validated URL
        
    Raises:
        ValidationError: If validation fails
    """
    validator = URLValidator(
        allowed_schemes=allowed_schemes,
        require_scheme=require_scheme,
        field_name=field_name
    )
    
    result = validator.validate(url)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return url


def validate_port(port: int, field_name: str = "port") -> int:
    """
    Validate a network port.
    
    Args:
        port: Port number to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated port number
        
    Raises:
        ValidationError: If validation fails
    """
    validator = PortValidator(field_name=field_name)
    result = validator.validate(port)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return port


def validate_cron(cron_expression: str, field_name: str = "cron expression") -> str:
    """
    Validate a cron expression.
    
    Args:
        cron_expression: Cron expression to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated cron expression
        
    Raises:
        ValidationError: If validation fails
    """
    validator = CronValidator(field_name=field_name)
    result = validator.validate(cron_expression)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return cron_expression


def validate_integer_range(
    value: int,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    field_name: str = "value"
) -> int:
    """
    Validate an integer is within a range.
    
    Args:
        value: Integer value to validate
        min_value: Minimum valid value
        max_value: Maximum valid value
        field_name: Name of the field for error messages
        
    Returns:
        The validated integer
        
    Raises:
        ValidationError: If validation fails
    """
    validator = IntegerRangeValidator(
        min_value=min_value,
        max_value=max_value,
        field_name=field_name
    )
    
    result = validator.validate(value)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return value


def validate_string_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "value"
) -> str:
    """
    Validate string length.
    
    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length
        field_name: Name of the field for error messages
        
    Returns:
        The validated string
        
    Raises:
        ValidationError: If validation fails
    """
    validator = StringLengthValidator(
        min_length=min_length,
        max_length=max_length,
        field_name=field_name
    )
    
    result = validator.validate(value)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(errors[0] if len(errors) == 1 else "; ".join(errors))
    
    return value


# Backward compatibility aliases
validate_path_exists = validate_path
validate_non_empty_string = validate_required_string
