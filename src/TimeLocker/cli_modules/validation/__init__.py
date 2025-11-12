"""
Validation Framework for CLI Commands

This module provides a comprehensive validation framework for CLI commands,
including base validator classes, common validation patterns, validation
composition, and consistent error reporting.
"""

from .base import (
    Validator,
    ValidationResult,
    ValidationError as BaseValidationError,
    CompositeValidator,
    OptionalValidator,
    ConditionalValidator,
)
from .common import (
    PathValidator,
    NameValidator,
    EmailValidator,
    URLValidator,
    PortValidator,
    CronValidator,
    IntegerRangeValidator,
    StringLengthValidator,
    RegexValidator,
    EnumValidator,
)
from .config import (
    ConfigValidator,
    RepositoryConfigValidator,
    BackupTargetConfigValidator,
)
from .context import ValidationContext
from .helpers import (
    ValidationError,
    validate_required_string,
    validate_path,
    validate_name,
    validate_repository_name,
    validate_email,
    validate_url,
    validate_port,
    validate_cron,
    validate_integer_range,
    validate_string_length,
    # Backward compatibility
    validate_path_exists,
    validate_non_empty_string,
)

__all__ = [
    # Base classes
    "Validator",
    "ValidationResult",
    "BaseValidationError",
    "ValidationError",
    "CompositeValidator",
    "OptionalValidator",
    "ConditionalValidator",
    # Common validators
    "PathValidator",
    "NameValidator",
    "EmailValidator",
    "URLValidator",
    "PortValidator",
    "CronValidator",
    "IntegerRangeValidator",
    "StringLengthValidator",
    "RegexValidator",
    "EnumValidator",
    # Config validators
    "ConfigValidator",
    "RepositoryConfigValidator",
    "BackupTargetConfigValidator",
    # Context
    "ValidationContext",
    # Helper functions
    "validate_required_string",
    "validate_path",
    "validate_name",
    "validate_repository_name",
    "validate_email",
    "validate_url",
    "validate_port",
    "validate_cron",
    "validate_integer_range",
    "validate_string_length",
    # Backward compatibility
    "validate_path_exists",
    "validate_non_empty_string",
]
