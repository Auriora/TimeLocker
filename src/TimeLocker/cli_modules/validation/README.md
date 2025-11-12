# Validation Framework

The ValidationFramework provides a comprehensive, reusable validation system for CLI commands. It eliminates validation code duplication across 40+ commands and provides consistent error messages and validation patterns.

## Overview

The framework consists of:

- **Base Classes**: Core validation infrastructure (`Validator`, `ValidationResult`, `ValidationError`)
- **Common Validators**: Reusable validators for typical patterns (paths, names, emails, URLs, etc.)
- **Config Validators**: Specialized validators for TimeLocker configuration objects
- **Validation Context**: State management for complex validation scenarios
- **Composition Support**: Combine validators with AND/OR logic

## Quick Start

### Basic Validation

```python
from TimeLocker.cli_modules.validation import PathValidator, ValidationResult

# Validate a path
validator = PathValidator(must_exist=True, must_be_directory=True)
result = validator.validate("/path/to/directory")

if result.valid:
    print("Path is valid!")
else:
    for error in result.get_errors():
        print(f"Error: {error.message}")
```

### Composing Validators

```python
from TimeLocker.cli_modules.validation import (
    NameValidator,
    StringLengthValidator,
    CompositeValidator
)

# Combine validators with AND logic
name_validator = NameValidator(allow_spaces=False)
length_validator = StringLengthValidator(min_length=3, max_length=50)

# Using the & operator
combined = name_validator & length_validator
result = combined.validate("my-repository")

# Or explicitly
combined = CompositeValidator([name_validator, length_validator], require_all=True)
```

### Optional Validation

```python
from TimeLocker.cli_modules.validation import OptionalValidator, EmailValidator

# Email is optional, but if provided must be valid
email_validator = OptionalValidator(EmailValidator())
result = email_validator.validate(None)  # Valid (None is allowed)
result = email_validator.validate("invalid")  # Invalid (bad format)
result = email_validator.validate("user@example.com")  # Valid
```

### Conditional Validation

```python
from TimeLocker.cli_modules.validation import ConditionalValidator, PathValidator

# Only validate path if it's a local repository
def is_local_repo(value, context):
    return context and context.get('repo_type') == 'local'

validator = ConditionalValidator(
    PathValidator(must_exist=True),
    condition=is_local_repo
)

context = {'repo_type': 'local'}
result = validator.validate("/path/to/repo", context)
```

## Available Validators

### Common Validators

#### PathValidator
Validates file system paths with options for existence, type, and permissions.

```python
PathValidator(
    must_exist=False,           # Path must exist
    must_not_exist=False,       # Path must not exist
    must_be_file=False,         # Must be a file
    must_be_directory=False,    # Must be a directory
    must_be_readable=False,     # Must be readable
    must_be_writable=False,     # Must be writable
    allow_relative=True,        # Allow relative paths
    field_name="path"
)
```

#### NameValidator
Validates names (repository names, policy names, etc.) with naming conventions.

```python
NameValidator(
    min_length=1,               # Minimum name length
    max_length=255,             # Maximum name length
    allow_spaces=False,         # Allow spaces in names
    allow_special_chars=False,  # Allow special characters
    pattern=None,               # Optional regex pattern
    reserved_names=None,        # Set of reserved names
    field_name="name"
)
```

#### EmailValidator
Validates email addresses.

```python
EmailValidator(field_name="email")
```

#### URLValidator
Validates URLs with scheme and format checking.

```python
URLValidator(
    allowed_schemes=None,       # List of allowed schemes (e.g., ['http', 'https'])
    require_scheme=True,        # Require URL to have a scheme
    field_name="url"
)
```

#### PortValidator
Validates network port numbers.

```python
PortValidator(
    min_port=1,                 # Minimum valid port
    max_port=65535,             # Maximum valid port
    field_name="port"
)
```

#### CronValidator
Validates cron expressions.

```python
CronValidator(field_name="cron_expression")
```

#### IntegerRangeValidator
Validates integer values within a range.

```python
IntegerRangeValidator(
    min_value=None,             # Minimum value (inclusive)
    max_value=None,             # Maximum value (inclusive)
    field_name="value"
)
```

#### StringLengthValidator
Validates string length.

```python
StringLengthValidator(
    min_length=None,            # Minimum length
    max_length=None,            # Maximum length
    field_name="value"
)
```

#### RegexValidator
Validates values against a regex pattern.

```python
RegexValidator(
    pattern=r"^[a-z]+$",        # Regex pattern
    error_message=None,         # Custom error message
    field_name="value"
)
```

#### EnumValidator
Validates enum values.

```python
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

EnumValidator(
    enum_class=Status,
    field_name="status"
)
```

### Config Validators

#### RepositoryConfigValidator
Validates repository configurations.

```python
RepositoryConfigValidator(field_name="repository")
```

#### BackupTargetConfigValidator
Validates backup target configurations.

```python
BackupTargetConfigValidator(field_name="backup_target")
```

#### ConfigValidator
Validates complete TimeLocker configuration.

```python
ConfigValidator(field_name="config")
```

## Validation Results

### ValidationResult

The `ValidationResult` class provides comprehensive validation feedback:

```python
result = ValidationResult()

# Add issues
result.add_error("field", "Error message", "ERROR_CODE")
result.add_warning("field", "Warning message", "WARNING_CODE")
result.add_info("field", "Info message", "INFO_CODE")

# Check status
if result.valid:
    print("Validation passed")

if result.has_errors():
    print("Has errors")

if result.has_warnings():
    print("Has warnings")

# Get issues by severity
errors = result.get_errors()
warnings = result.get_warnings()
info = result.get_info()

# Merge results
other_result = some_validator.validate(value)
result.merge(other_result)

# Convert to dict
data = result.to_dict()
```

### ValidationError

Exception raised when validation fails:

```python
from TimeLocker.cli_modules.validation import ValidationError

try:
    if not result.valid:
        raise ValidationError(
            "Validation failed",
            result=result,
            field="repository_name"
        )
except ValidationError as e:
    print(f"Error: {e}")
    for msg in e.get_error_messages():
        print(f"  - {msg}")
```

## Validation Context

Use `ValidationContext` to pass state between validators:

```python
from TimeLocker.cli_modules.validation import ValidationContext

context = ValidationContext(
    config=config_object,
    repositories={"repo1": repo_config},
    strict_mode=True
)

# Add custom data
context.set("repo_type", "local")

# Use in validation
result = validator.validate(value, context.to_dict())
```

## Usage in CLI Commands

### Example: Validating Repository Name

```python
from TimeLocker.cli_modules.validation import NameValidator, ValidationError

def add_repository(name: str, location: str):
    # Validate repository name
    name_validator = NameValidator(
        min_length=1,
        max_length=100,
        allow_spaces=False,
        reserved_names={"default", "system"}
    )
    
    result = name_validator.validate(name)
    
    if not result.valid:
        errors = [issue.message for issue in result.get_errors()]
        raise ValidationError(f"Invalid repository name: {'; '.join(errors)}")
    
    # Proceed with adding repository
    ...
```

### Example: Validating Multiple Fields

```python
from TimeLocker.cli_modules.validation import (
    NameValidator,
    PathValidator,
    ValidationResult
)

def validate_backup_target(name: str, paths: List[str]) -> ValidationResult:
    result = ValidationResult()
    
    # Validate name
    name_validator = NameValidator()
    name_result = name_validator.validate(name)
    result.merge(name_result)
    
    # Validate paths
    path_validator = PathValidator(must_exist=True)
    for idx, path in enumerate(paths):
        path_result = path_validator.validate(path)
        # Prefix field names with index
        for issue in path_result.issues:
            issue.field = f"paths[{idx}]"
        result.merge(path_result)
    
    return result
```

### Example: Using in Typer Commands

```python
import typer
from TimeLocker.cli_modules.validation import PathValidator, ValidationError

app = typer.Typer()

@app.command()
def backup(
    repository: str,
    path: str = typer.Argument(..., help="Path to backup")
):
    """Backup a path to repository."""
    
    # Validate path
    validator = PathValidator(
        must_exist=True,
        must_be_readable=True
    )
    
    result = validator.validate(path)
    
    if not result.valid:
        for error in result.get_errors():
            typer.echo(f"Error: {error.message}", err=True)
        raise typer.Exit(1)
    
    # Proceed with backup
    ...
```

## Best Practices

1. **Reuse Validators**: Create validator instances once and reuse them across commands
2. **Compose Validators**: Use composition to build complex validation logic from simple validators
3. **Provide Context**: Use ValidationContext for validators that need access to configuration or state
4. **Handle Results Properly**: Always check `result.valid` and handle errors appropriately
5. **Use Appropriate Severity**: Use errors for validation failures, warnings for potential issues, and info for helpful messages
6. **Consistent Field Names**: Use consistent field names across validators for better error reporting
7. **Custom Error Messages**: Provide clear, actionable error messages that help users fix issues

## Error Codes

The framework uses consistent error codes for programmatic error handling:

- `EMPTY_*`: Value is empty when it shouldn't be
- `INVALID_*_TYPE`: Value has wrong type
- `INVALID_*_FORMAT`: Value has invalid format
- `*_NOT_FOUND`: Required resource not found
- `*_ALREADY_EXISTS`: Resource already exists when it shouldn't
- `*_TOO_SHORT`: Value is too short
- `*_TOO_LONG`: Value is too long
- `*_OUT_OF_RANGE`: Value is outside valid range
- `PATTERN_MISMATCH`: Value doesn't match required pattern
- `RESERVED_NAME`: Name is reserved and cannot be used

## Testing

Example test for a validator:

```python
import pytest
from TimeLocker.cli_modules.validation import NameValidator

def test_name_validator():
    validator = NameValidator(min_length=3, max_length=10)
    
    # Valid name
    result = validator.validate("myrepo")
    assert result.valid
    
    # Too short
    result = validator.validate("ab")
    assert not result.valid
    assert any("at least 3" in e.message for e in result.get_errors())
    
    # Too long
    result = validator.validate("verylongname")
    assert not result.valid
    assert any("at most 10" in e.message for e in result.get_errors())
```

## Migration from Existing Validation

To migrate existing validation code:

1. Identify validation patterns in commands
2. Replace with appropriate validators from the framework
3. Update error handling to use ValidationResult
4. Remove duplicated validation code
5. Update tests to use validators

Example migration:

```python
# Before
if not name or len(name) < 3:
    raise ValueError("Name must be at least 3 characters")
if not re.match(r'^[a-zA-Z0-9_-]+$', name):
    raise ValueError("Name can only contain letters, numbers, hyphens, and underscores")

# After
from TimeLocker.cli_modules.validation import NameValidator, ValidationError

validator = NameValidator(min_length=3)
result = validator.validate(name)
if not result.valid:
    errors = [e.message for e in result.get_errors()]
    raise ValidationError("; ".join(errors))
```

## Performance

The ValidationFramework is designed for minimal overhead:

- Validators are lightweight and can be reused
- Validation results are efficient dataclasses
- No unnecessary object creation
- Lazy evaluation where possible

Typical validation overhead: < 1ms per validation operation

## Future Enhancements

Potential future additions:

- Async validators for I/O-heavy validation
- Validation caching for expensive operations
- Custom validator registration system
- Validation schema DSL
- Integration with configuration schema validation
