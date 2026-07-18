# ValidationFramework Documentation

## Overview

The ValidationFramework provides a comprehensive, composable validation system for CLI commands and configuration. It enables consistent validation patterns across the TimeLocker codebase with reusable validators, clear error messages, and flexible composition.

## Architecture

The ValidationFramework consists of three main layers:

1. **Base Layer** (`validation/base.py`): Core validation classes and interfaces
2. **Common Validators** (`validation/common.py`): Reusable validators for common patterns
3. **Custom Validators**: Application-specific validators built on the base layer

## Core Components

### ValidationResult

Represents the result of a validation operation with support for errors, warnings, and informational messages.

```python
from TimeLocker.cli_modules.validation.base import ValidationResult, ValidationSeverity

result = ValidationResult()
result.add_error("field_name", "Error message", "ERROR_CODE")
result.add_warning("field_name", "Warning message", "WARNING_CODE")
result.add_info("field_name", "Info message", "INFO_CODE")

# Check validation status
if result.valid:
    print("Validation passed")
else:
    for error in result.get_errors():
        print(f"{error.field}: {error.message}")
```

**Key Features:**
- Supports multiple severity levels (ERROR, WARNING, INFO)
- Errors invalidate the result, warnings and info do not
- Can merge multiple validation results
- Provides filtering by severity level
- Converts to dictionary for serialization

### Validator Base Class

Abstract base class for all validators. Validators implement the `validate()` method to check if a value meets specific criteria.

```python
from TimeLocker.cli_modules.validation.base import Validator, ValidationResult
from typing import Any, Optional, Dict

class CustomValidator(Validator):
    def __init__(self, field_name: str = "value"):
        super().__init__(field_name)
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        result = ValidationResult()
        
        # Perform validation
        if not self._is_valid(value):
            result.add_error(
                self.field_name,
                "Validation failed",
                "CUSTOM_ERROR",
                context={"value": value}
            )
        
        return result
```

**Key Features:**
- Abstract base class for all validators
- Supports optional validation context
- Can be called as a function: `validator(value)`
- Supports composition with `&` (AND) and `|` (OR) operators

### CompositeValidator

Combines multiple validators with AND or OR logic.

```python
from TimeLocker.cli_modules.validation.common import NameValidator, PathValidator
from TimeLocker.cli_modules.validation.base import CompositeValidator

# AND logic: all validators must pass
name_validator = NameValidator(min_length=3, max_length=50)
no_spaces_validator = NameValidator(allow_spaces=False)
composite = CompositeValidator([name_validator, no_spaces_validator], require_all=True)

# OR logic: at least one validator must pass
composite_or = CompositeValidator([validator1, validator2], require_all=False)

# Using operators
combined = name_validator & no_spaces_validator  # AND
combined = validator1 | validator2  # OR
```

### OptionalValidator

Wraps another validator and only applies it if the value is not None or empty.

```python
from TimeLocker.cli_modules.validation.base import OptionalValidator
from TimeLocker.cli_modules.validation.common import PathValidator

path_validator = PathValidator(must_exist=True)
optional_path = OptionalValidator(path_validator, allow_empty=True)

# None and empty strings pass validation
result = optional_path.validate(None)  # Valid
result = optional_path.validate("")    # Valid
result = optional_path.validate("/path")  # Validated by inner validator
```

### ConditionalValidator

Applies validation only if a condition is met.

```python
from TimeLocker.cli_modules.validation.base import ConditionalValidator
from TimeLocker.cli_modules.validation.common import PathValidator

path_validator = PathValidator(must_exist=True)
conditional = ConditionalValidator(
    path_validator,
    condition=lambda value, context: context and context.get('validate_path', False)
)

# Only validates if context['validate_path'] is True
result = conditional.validate("/path", {'validate_path': True})  # Validated
result = conditional.validate("/path", {'validate_path': False})  # Skipped
```

## Common Validators

### PathValidator

Validates file system paths with support for existence, type, and permissions checks.

```python
from TimeLocker.cli_modules.validation.common import PathValidator

# Basic path validation
validator = PathValidator()
result = validator.validate("/tmp")

# Path must exist
validator = PathValidator(must_exist=True)

# Path must be a directory
validator = PathValidator(must_exist=True, must_be_directory=True)

# Path must be writable
validator = PathValidator(must_exist=True, must_be_writable=True)

# Only absolute paths allowed
validator = PathValidator(allow_relative=False)
```

**Options:**
- `must_exist`: Path must exist
- `must_not_exist`: Path must not exist
- `must_be_file`: Path must be a file
- `must_be_directory`: Path must be a directory
- `must_be_readable`: Path must be readable
- `must_be_writable`: Path must be writable
- `allow_relative`: Allow relative paths

### NameValidator

Validates names (repository names, policy names, etc.) with naming conventions and restrictions.

```python
from TimeLocker.cli_modules.validation.common import NameValidator

# Basic name validation
validator = NameValidator(min_length=3, max_length=50)

# No spaces allowed
validator = NameValidator(allow_spaces=False)

# Reserved names
validator = NameValidator(reserved_names={"default", "system"})

# Custom pattern
validator = NameValidator(pattern=r'^[a-z][a-z0-9-]*$')
```

**Options:**
- `min_length`: Minimum name length
- `max_length`: Maximum name length
- `allow_spaces`: Allow spaces in names
- `allow_special_chars`: Allow special characters
- `pattern`: Custom regex pattern
- `reserved_names`: Set of reserved names

### EmailValidator

Validates email addresses.

```python
from TimeLocker.cli_modules.validation.common import EmailValidator

validator = EmailValidator()
result = validator.validate("user@example.com")
```

### URLValidator

Validates URLs with scheme and format checking.

```python
from TimeLocker.cli_modules.validation.common import URLValidator

# Basic URL validation
validator = URLValidator()

# Require specific schemes
validator = URLValidator(allowed_schemes=["https"])

# Optional scheme
validator = URLValidator(require_scheme=False)
```

### PortValidator

Validates network port numbers.

```python
from TimeLocker.cli_modules.validation.common import PortValidator

# Default range: 1-65535
validator = PortValidator()

# Custom range
validator = PortValidator(min_port=8000, max_port=9000)
```

### IntegerRangeValidator

Validates integer values within a range.

```python
from TimeLocker.cli_modules.validation.common import IntegerRangeValidator

validator = IntegerRangeValidator(min_value=0, max_value=100)
result = validator.validate(50)
```

### StringLengthValidator

Validates string length.

```python
from TimeLocker.cli_modules.validation.common import StringLengthValidator

validator = StringLengthValidator(min_length=3, max_length=255)
result = validator.validate("hello")
```

### RegexValidator

Validates values against a regex pattern.

```python
from TimeLocker.cli_modules.validation.common import RegexValidator

validator = RegexValidator(
    pattern=r'^[a-z][a-z0-9-]*$',
    error_message="Must start with lowercase letter and contain only lowercase letters, numbers, and hyphens"
)
```

## Usage Patterns

### Basic Validation

```python
from TimeLocker.cli_modules.validation.common import NameValidator

validator = NameValidator(min_length=3, max_length=50, allow_spaces=False)
result = validator.validate("my-repository")

if result.valid:
    print("Valid name")
else:
    for error in result.get_errors():
        print(f"Error: {error.message}")
```

### Composite Validation

```python
from TimeLocker.cli_modules.validation.common import NameValidator
from TimeLocker.cli_modules.validation.base import CompositeValidator

# Combine multiple validators
validators = [
    NameValidator(min_length=3, max_length=50),
    NameValidator(allow_spaces=False),
    NameValidator(reserved_names={"system", "default"}),
]

composite = CompositeValidator(validators, require_all=True)
result = composite.validate("my-repo")
```

### Optional Validation

```python
from TimeLocker.cli_modules.validation.base import OptionalValidator
from TimeLocker.cli_modules.validation.common import EmailValidator

email_validator = EmailValidator()
optional_email = OptionalValidator(email_validator)

# None is valid
result = optional_email.validate(None)  # Valid

# Valid email is validated
result = optional_email.validate("user@example.com")  # Validated
```

### Context-Aware Validation

```python
from TimeLocker.cli_modules.validation.base import Validator, ValidationResult

class ContextAwareValidator(Validator):
    def validate(self, value, context=None):
        result = ValidationResult()
        
        # Use context for conditional validation
        if context and context.get('strict_mode'):
            if len(value) < 10:
                result.add_error(
                    self.field_name,
                    "In strict mode, value must be at least 10 characters",
                    "STRICT_LENGTH_ERROR"
                )
        
        return result

validator = ContextAwareValidator()
result = validator.validate("short", {'strict_mode': True})
```

### Configuration Validation

```python
from TimeLocker.cli_modules.validation.common import (
    NameValidator,
    PathValidator,
    EmailValidator,
    PortValidator,
)

# Define validators for configuration fields
validators = {
    'repository_name': NameValidator(min_length=3, allow_spaces=False),
    'backup_path': PathValidator(must_exist=False, allow_relative=False),
    'email': EmailValidator(),
    'port': PortValidator(min_port=1, max_port=65535),
}

# Validate configuration
config = {
    'repository_name': 'my-repo',
    'backup_path': '/backup',
    'email': 'admin@example.com',
    'port': 8080,
}

validation_errors = []

for field, validator in validators.items():
    if field in config:
        result = validator.validate(config[field])
        if not result.valid:
            validation_errors.extend(result.get_errors())

if validation_errors:
    print("Configuration validation failed:")
    for error in validation_errors:
        print(f"  {error.field}: {error.message}")
```

## Best Practices

### 1. Use Appropriate Validators

Choose the most specific validator for your use case:

```python
# Good: Use specific validator
validator = EmailValidator()

# Avoid: Using regex for common patterns
validator = RegexValidator(pattern=r'^[^@]+@[^@]+\.[^@]+$')
```

### 2. Provide Clear Error Messages

```python
validator = NameValidator(
    min_length=3,
    max_length=50,
    reserved_names={"system", "default"}
)

result = validator.validate("ab")
# Error message: "Name must be at least 3 characters"
```

### 3. Use Composition for Complex Validation

```python
# Combine validators instead of creating complex custom validators
name_validator = NameValidator(min_length=3, max_length=50)
no_spaces = NameValidator(allow_spaces=False)
no_reserved = NameValidator(reserved_names={"system"})

composite = name_validator & no_spaces & no_reserved
```

### 4. Add Context to Errors

```python
result.add_error(
    "repository_name",
    "Repository name is reserved",
    "RESERVED_NAME",
    context={
        "name": "system",
        "reserved_names": ["system", "default"]
    }
)
```

### 5. Use Optional Validators for Optional Fields

```python
# For optional configuration fields
email_validator = EmailValidator()
optional_email = OptionalValidator(email_validator)

# None is valid, but if provided, must be valid email
result = optional_email.validate(config.get('email'))
```

## Testing Guidelines

### Unit Testing Validators

```python
import pytest
from TimeLocker.cli_modules.validation.common import NameValidator

def test_name_validator_valid():
    validator = NameValidator(min_length=3, max_length=50)
    result = validator.validate("my-repository")
    assert result.valid is True

def test_name_validator_too_short():
    validator = NameValidator(min_length=3)
    result = validator.validate("ab")
    assert result.valid is False
    assert any("at least 3" in e.message for e in result.get_errors())

def test_name_validator_reserved():
    validator = NameValidator(reserved_names={"system"})
    result = validator.validate("system")
    assert result.valid is False
    assert any("reserved" in e.message.lower() for e in result.get_errors())
```

### Integration Testing

```python
def test_configuration_validation():
    validators = {
        'name': NameValidator(min_length=3),
        'path': PathValidator(must_exist=False),
    }
    
    config = {'name': 'my-repo', 'path': '/backup'}
    
    for field, validator in validators.items():
        result = validator.validate(config[field])
        assert result.valid is True
```

## Error Codes

Common error codes used by validators:

- `EMPTY_VALUE`: Value is empty or None
- `INVALID_TYPE`: Value is not the expected type
- `PATTERN_MISMATCH`: Value doesn't match required pattern
- `VALUE_TOO_SMALL`: Numeric value below minimum
- `VALUE_TOO_LARGE`: Numeric value above maximum
- `STRING_TOO_SHORT`: String length below minimum
- `STRING_TOO_LONG`: String length above maximum
- `PATH_NOT_FOUND`: Path doesn't exist
- `PATH_ALREADY_EXISTS`: Path already exists
- `NOT_A_FILE`: Path is not a file
- `NOT_A_DIRECTORY`: Path is not a directory
- `NOT_READABLE`: Path is not readable
- `NOT_WRITABLE`: Path is not writable
- `RESERVED_NAME`: Name is reserved
- `INVALID_EMAIL_FORMAT`: Email format is invalid
- `INVALID_URL_FORMAT`: URL format is invalid
- `PORT_OUT_OF_RANGE`: Port number out of valid range

## See Also

- [ErrorContext Documentation](error-context-usage.md)
- [CommandRegistry Documentation](command-registry-api.md)
- [Testing Quick Start](../4-testing/quickstart-testing.md)
