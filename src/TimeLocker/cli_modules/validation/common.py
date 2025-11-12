"""
Common validators for typical validation patterns.

This module provides reusable validators for common validation scenarios
like paths, names, emails, URLs, ports, cron expressions, and more.
"""

import re
from pathlib import Path
from typing import Any, Optional, Dict, List, Set
from enum import Enum

from .base import Validator, ValidationResult


class PathValidator(Validator):
    """
    Validator for file system paths.
    
    Supports validation for existence, type (file/directory), permissions,
    and path format.
    """
    
    def __init__(
        self,
        must_exist: bool = False,
        must_not_exist: bool = False,
        must_be_file: bool = False,
        must_be_directory: bool = False,
        must_be_readable: bool = False,
        must_be_writable: bool = False,
        allow_relative: bool = True,
        field_name: str = "path"
    ):
        """
        Initialize path validator.
        
        Args:
            must_exist: Path must exist
            must_not_exist: Path must not exist
            must_be_file: Path must be a file
            must_be_directory: Path must be a directory
            must_be_readable: Path must be readable
            must_be_writable: Path must be writable
            allow_relative: Allow relative paths
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.must_exist = must_exist
        self.must_not_exist = must_not_exist
        self.must_be_file = must_be_file
        self.must_be_directory = must_be_directory
        self.must_be_readable = must_be_readable
        self.must_be_writable = must_be_writable
        self.allow_relative = allow_relative
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate path."""
        result = ValidationResult()
        
        if not value:
            result.add_error(self.field_name, "Path cannot be empty", "EMPTY_PATH")
            return result
        
        try:
            path = Path(value)
        except (ValueError, TypeError) as e:
            result.add_error(
                self.field_name,
                f"Invalid path format: {e}",
                "INVALID_PATH_FORMAT"
            )
            return result
        
        # Check if relative paths are allowed
        if not self.allow_relative and not path.is_absolute():
            result.add_error(
                self.field_name,
                "Path must be absolute",
                "RELATIVE_PATH_NOT_ALLOWED",
                {"path": str(path)}
            )
        
        # Check existence
        if self.must_exist and not path.exists():
            result.add_error(
                self.field_name,
                f"Path does not exist: {path}",
                "PATH_NOT_FOUND",
                {"path": str(path)}
            )
            return result
        
        if self.must_not_exist and path.exists():
            result.add_error(
                self.field_name,
                f"Path already exists: {path}",
                "PATH_ALREADY_EXISTS",
                {"path": str(path)}
            )
            return result
        
        # Check type (only if path exists)
        if path.exists():
            if self.must_be_file and not path.is_file():
                result.add_error(
                    self.field_name,
                    f"Path is not a file: {path}",
                    "NOT_A_FILE",
                    {"path": str(path)}
                )
            
            if self.must_be_directory and not path.is_dir():
                result.add_error(
                    self.field_name,
                    f"Path is not a directory: {path}",
                    "NOT_A_DIRECTORY",
                    {"path": str(path)}
                )
            
            # Check permissions
            if self.must_be_readable:
                try:
                    path.stat()
                except PermissionError:
                    result.add_error(
                        self.field_name,
                        f"Path is not readable: {path}",
                        "NOT_READABLE",
                        {"path": str(path)}
                    )
            
            if self.must_be_writable:
                if path.is_dir():
                    test_file = path / ".write_test"
                    try:
                        test_file.touch()
                        test_file.unlink()
                    except (PermissionError, OSError):
                        result.add_error(
                            self.field_name,
                            f"Path is not writable: {path}",
                            "NOT_WRITABLE",
                            {"path": str(path)}
                        )
                else:
                    try:
                        with open(path, 'a'):
                            pass
                    except (PermissionError, OSError):
                        result.add_error(
                            self.field_name,
                            f"Path is not writable: {path}",
                            "NOT_WRITABLE",
                            {"path": str(path)}
                        )
        
        return result


class NameValidator(Validator):
    """
    Validator for names (repository names, policy names, etc.).
    
    Validates naming conventions and restrictions.
    """
    
    def __init__(
        self,
        min_length: int = 1,
        max_length: int = 255,
        allow_spaces: bool = False,
        allow_special_chars: bool = False,
        pattern: Optional[str] = None,
        reserved_names: Optional[Set[str]] = None,
        field_name: str = "name"
    ):
        """
        Initialize name validator.
        
        Args:
            min_length: Minimum name length
            max_length: Maximum name length
            allow_spaces: Allow spaces in names
            allow_special_chars: Allow special characters
            pattern: Optional regex pattern for validation
            reserved_names: Set of reserved names that cannot be used
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.min_length = min_length
        self.max_length = max_length
        self.allow_spaces = allow_spaces
        self.allow_special_chars = allow_special_chars
        self.pattern = re.compile(pattern) if pattern else None
        self.reserved_names = reserved_names or set()
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate name."""
        result = ValidationResult()
        
        if not value:
            result.add_error(self.field_name, "Name cannot be empty", "EMPTY_NAME")
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "Name must be a string",
                "INVALID_NAME_TYPE"
            )
            return result
        
        name = value.strip()
        
        # Check length
        if len(name) < self.min_length:
            result.add_error(
                self.field_name,
                f"Name must be at least {self.min_length} characters",
                "NAME_TOO_SHORT",
                {"min_length": self.min_length, "actual_length": len(name)}
            )
        
        if len(name) > self.max_length:
            result.add_error(
                self.field_name,
                f"Name must be at most {self.max_length} characters",
                "NAME_TOO_LONG",
                {"max_length": self.max_length, "actual_length": len(name)}
            )
        
        # Check for spaces
        if not self.allow_spaces and ' ' in name:
            result.add_error(
                self.field_name,
                "Name cannot contain spaces",
                "SPACES_NOT_ALLOWED"
            )
        
        # Check for special characters
        if not self.allow_special_chars:
            # Build pattern based on whether spaces are allowed
            if self.allow_spaces:
                pattern = r'^[a-zA-Z0-9_\- ]+$'
            else:
                pattern = r'^[a-zA-Z0-9_-]+$'
            
            if not re.match(pattern, name):
                if self.allow_spaces:
                    result.add_error(
                        self.field_name,
                        "Name can only contain letters, numbers, hyphens, underscores, and spaces",
                        "INVALID_CHARACTERS"
                    )
                else:
                    result.add_error(
                        self.field_name,
                        "Name can only contain letters, numbers, hyphens, and underscores",
                        "INVALID_CHARACTERS"
                    )
        
        # Check custom pattern
        if self.pattern and not self.pattern.match(name):
            result.add_error(
                self.field_name,
                f"Name does not match required pattern",
                "PATTERN_MISMATCH"
            )
        
        # Check reserved names
        if name.lower() in {n.lower() for n in self.reserved_names}:
            result.add_error(
                self.field_name,
                f"Name '{name}' is reserved and cannot be used",
                "RESERVED_NAME",
                {"reserved_names": list(self.reserved_names)}
            )
        
        return result


class EmailValidator(Validator):
    """Validator for email addresses."""
    
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def __init__(self, field_name: str = "email"):
        """Initialize email validator."""
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate email address."""
        result = ValidationResult()
        
        if not value:
            result.add_error(self.field_name, "Email cannot be empty", "EMPTY_EMAIL")
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "Email must be a string",
                "INVALID_EMAIL_TYPE"
            )
            return result
        
        if not self.EMAIL_PATTERN.match(value):
            result.add_error(
                self.field_name,
                f"Invalid email address: {value}",
                "INVALID_EMAIL_FORMAT"
            )
        
        return result


class URLValidator(Validator):
    """Validator for URLs."""
    
    def __init__(
        self,
        allowed_schemes: Optional[List[str]] = None,
        require_scheme: bool = True,
        field_name: str = "url"
    ):
        """
        Initialize URL validator.
        
        Args:
            allowed_schemes: List of allowed URL schemes (e.g., ['http', 'https'])
            require_scheme: Require URL to have a scheme
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.allowed_schemes = allowed_schemes
        self.require_scheme = require_scheme
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate URL."""
        result = ValidationResult()
        
        if not value:
            result.add_error(self.field_name, "URL cannot be empty", "EMPTY_URL")
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "URL must be a string",
                "INVALID_URL_TYPE"
            )
            return result
        
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(value)
        except Exception as e:
            result.add_error(
                self.field_name,
                f"Invalid URL format: {e}",
                "INVALID_URL_FORMAT"
            )
            return result
        
        # Check scheme
        if self.require_scheme and not parsed.scheme:
            result.add_error(
                self.field_name,
                "URL must include a scheme (e.g., http://)",
                "MISSING_SCHEME"
            )
        
        if self.allowed_schemes and parsed.scheme not in self.allowed_schemes:
            result.add_error(
                self.field_name,
                f"URL scheme must be one of: {', '.join(self.allowed_schemes)}",
                "INVALID_SCHEME",
                {"allowed_schemes": self.allowed_schemes, "actual_scheme": parsed.scheme}
            )
        
        return result


class PortValidator(Validator):
    """Validator for network ports."""
    
    def __init__(
        self,
        min_port: int = 1,
        max_port: int = 65535,
        field_name: str = "port"
    ):
        """
        Initialize port validator.
        
        Args:
            min_port: Minimum valid port number
            max_port: Maximum valid port number
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.min_port = min_port
        self.max_port = max_port
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate port number."""
        result = ValidationResult()
        
        if value is None:
            result.add_error(self.field_name, "Port cannot be empty", "EMPTY_PORT")
            return result
        
        try:
            port = int(value)
        except (ValueError, TypeError):
            result.add_error(
                self.field_name,
                "Port must be a number",
                "INVALID_PORT_TYPE"
            )
            return result
        
        if port < self.min_port or port > self.max_port:
            result.add_error(
                self.field_name,
                f"Port must be between {self.min_port} and {self.max_port}",
                "PORT_OUT_OF_RANGE",
                {"min_port": self.min_port, "max_port": self.max_port, "actual_port": port}
            )
        
        return result


class CronValidator(Validator):
    """Validator for cron expressions."""
    
    CRON_PATTERN = re.compile(
        r'^(\*|[0-5]?\d)(\s+(\*|[01]?\d|2[0-3]))(\s+(\*|[12]?\d|3[01]))(\s+(\*|[1-9]|1[0-2]))(\s+(\*|[0-6]))$'
    )
    
    def __init__(self, field_name: str = "cron_expression"):
        """Initialize cron validator."""
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate cron expression."""
        result = ValidationResult()
        
        if not value:
            result.add_error(
                self.field_name,
                "Cron expression cannot be empty",
                "EMPTY_CRON"
            )
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "Cron expression must be a string",
                "INVALID_CRON_TYPE"
            )
            return result
        
        # Check format
        parts = value.strip().split()
        if len(parts) not in {5, 6}:
            result.add_error(
                self.field_name,
                "Cron expression must have 5 or 6 fields",
                "INVALID_CRON_FORMAT",
                {"expected_fields": "5 or 6", "actual_fields": len(parts)}
            )
            return result
        
        if not self.CRON_PATTERN.match(value.strip()):
            result.add_error(
                self.field_name,
                f"Invalid cron expression format: {value}",
                "INVALID_CRON_SYNTAX"
            )
        
        return result


class IntegerRangeValidator(Validator):
    """Validator for integer values within a range."""
    
    def __init__(
        self,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        field_name: str = "value"
    ):
        """
        Initialize integer range validator.
        
        Args:
            min_value: Minimum valid value (inclusive)
            max_value: Maximum valid value (inclusive)
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate integer value."""
        result = ValidationResult()
        
        if value is None:
            result.add_error(self.field_name, "Value cannot be empty", "EMPTY_VALUE")
            return result
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            result.add_error(
                self.field_name,
                "Value must be an integer",
                "INVALID_INTEGER"
            )
            return result
        
        if self.min_value is not None and int_value < self.min_value:
            result.add_error(
                self.field_name,
                f"Value must be at least {self.min_value}",
                "VALUE_TOO_SMALL",
                {"min_value": self.min_value, "actual_value": int_value}
            )
        
        if self.max_value is not None and int_value > self.max_value:
            result.add_error(
                self.field_name,
                f"Value must be at most {self.max_value}",
                "VALUE_TOO_LARGE",
                {"max_value": self.max_value, "actual_value": int_value}
            )
        
        return result


class StringLengthValidator(Validator):
    """Validator for string length."""
    
    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        field_name: str = "value"
    ):
        """
        Initialize string length validator.
        
        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate string length."""
        result = ValidationResult()
        
        if value is None:
            result.add_error(self.field_name, "Value cannot be empty", "EMPTY_VALUE")
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "Value must be a string",
                "INVALID_STRING_TYPE"
            )
            return result
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            result.add_error(
                self.field_name,
                f"Value must be at least {self.min_length} characters",
                "STRING_TOO_SHORT",
                {"min_length": self.min_length, "actual_length": length}
            )
        
        if self.max_length is not None and length > self.max_length:
            result.add_error(
                self.field_name,
                f"Value must be at most {self.max_length} characters",
                "STRING_TOO_LONG",
                {"max_length": self.max_length, "actual_length": length}
            )
        
        return result


class RegexValidator(Validator):
    """Validator for regex pattern matching."""
    
    def __init__(
        self,
        pattern: str,
        error_message: Optional[str] = None,
        field_name: str = "value"
    ):
        """
        Initialize regex validator.
        
        Args:
            pattern: Regex pattern to match
            error_message: Custom error message
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.pattern = re.compile(pattern)
        self.error_message = error_message or f"Value does not match required pattern"
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate value against regex pattern."""
        result = ValidationResult()
        
        if not value:
            result.add_error(self.field_name, "Value cannot be empty", "EMPTY_VALUE")
            return result
        
        if not isinstance(value, str):
            result.add_error(
                self.field_name,
                "Value must be a string",
                "INVALID_STRING_TYPE"
            )
            return result
        
        if not self.pattern.match(value):
            result.add_error(
                self.field_name,
                self.error_message,
                "PATTERN_MISMATCH"
            )
        
        return result


class EnumValidator(Validator):
    """Validator for enum values."""
    
    def __init__(
        self,
        enum_class: type,
        field_name: str = "value"
    ):
        """
        Initialize enum validator.
        
        Args:
            enum_class: Enum class to validate against
            field_name: Field name for error reporting
        """
        super().__init__(field_name)
        self.enum_class = enum_class
        self.valid_values = {e.value for e in enum_class}
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate enum value."""
        result = ValidationResult()
        
        if value is None:
            result.add_error(self.field_name, "Value cannot be empty", "EMPTY_VALUE")
            return result
        
        # Check if value is already an enum instance
        if isinstance(value, self.enum_class):
            return result
        
        # Check if value matches any enum value
        if value not in self.valid_values:
            result.add_error(
                self.field_name,
                f"Value must be one of: {', '.join(str(v) for v in self.valid_values)}",
                "INVALID_ENUM_VALUE",
                {"valid_values": list(self.valid_values), "actual_value": value}
            )
        
        return result
