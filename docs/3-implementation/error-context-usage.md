# ErrorContext Usage Guide

## Overview

The ErrorContext system provides enhanced error handling for TimeLocker CLI commands with:
- Automatic context tracking through the call stack
- User-friendly error formatting
- Recovery suggestions based on error type
- Consistent error reporting across all commands

## Basic Usage

### Using the Decorator

The simplest way to add ErrorContext to a command is using the `@with_cli_error_context` decorator:

```python
from TimeLocker.cli_modules.helpers import with_cli_error_context

@with_cli_error_context("backup_create", "BackupCommand")
def backup_create(sources, repository, ...):
    # Command implementation
    # Errors are automatically caught and formatted with context
    pass
```

### Manual Context Management

For more control, use ErrorContext directly:

```python
from TimeLocker.utils.error_handling import ErrorContext
from TimeLocker.cli_modules.helpers import show_cli_error

def my_command(...):
    try:
        with ErrorContext("my_operation", "MyCommand") as ctx:
            ctx.add_context("param1", value1)
            ctx.add_context("param2", value2)
            
            # Perform operation
            result = perform_operation()
            
    except Exception as e:
        show_cli_error(e, ctx)
        raise typer.Exit(1)
```

## Nested Operations

ErrorContext automatically tracks nested operations:

```python
def outer_operation():
    with ErrorContext("outer_op", "OuterService") as outer:
        outer.add_context("config", config_path)
        
        # Inner operation
        with ErrorContext("inner_op", "InnerService") as inner:
            inner.add_context("data", data_path)
            
            # If error occurs here, both contexts are preserved
            process_data()
```

When an error occurs in the inner operation, the error message will show:
- The inner operation context
- The outer operation context (call stack)
- All metadata from both contexts

## Recovery Suggestions

### Automatic Suggestions

ErrorContext provides automatic recovery suggestions for common error types:

```python
# FileNotFoundError automatically gets suggestions like:
# - Check that the file path is correct
# - Verify that the file exists
# - Ensure you have read permissions

# PermissionError automatically gets suggestions like:
# - Check file/directory permissions
# - Ensure you have necessary access rights
# - Try running with appropriate privileges
```

### Custom Suggestions

Add custom recovery suggestions for specific errors:

```python
with ErrorContext("backup", "BackupService") as ctx:
    ctx.add_recovery_suggestion("Check repository configuration")
    ctx.add_recovery_suggestion("Verify credentials are correct")
    ctx.add_recovery_suggestion("Ensure repository is accessible")
    
    # Perform backup
    create_backup()
```

### Common Suggestion Patterns

Use helper functions for common error types:

```python
from TimeLocker.cli_modules.helpers import add_common_recovery_suggestions

with ErrorContext("config_load", "ConfigService") as ctx:
    # Add standard config error suggestions
    add_common_recovery_suggestions(ctx, "config")
    
    load_configuration()
```

Available suggestion types:
- `"config"` - Configuration-related errors
- `"repository"` - Repository access errors
- `"network"` - Network connectivity errors
- `"permission"` - Permission/access errors
- `"validation"` - Input validation errors

## Error Formatting

### Formatted Error Output

ErrorContext provides user-friendly error formatting:

```
❌ ValueError: Invalid backup configuration

📍 Context:
  Component: BackupService
  Operation: backup_create
  Details:
    • repository: my-repo
    • sources: /home/user/data

📚 Call Stack:
  ↳ ConfigService:load_config
    ↳ RepositoryResolver:resolve_repository

💡 Suggested Actions:
  1. Check repository configuration
  2. Verify credentials are correct
  3. Ensure repository is accessible
```

### Display Error with Context

Use the helper function to display formatted errors:

```python
from TimeLocker.cli_modules.helpers import show_cli_error

try:
    with ErrorContext("operation", "Service") as ctx:
        perform_operation()
except Exception as e:
    show_cli_error(e, ctx)
    raise typer.Exit(1)
```

## Best Practices

### 1. Use Descriptive Operation Names

```python
# Good
with ErrorContext("backup_create", "BackupService"):
    ...

# Bad
with ErrorContext("op", "Service"):
    ...
```

### 2. Add Relevant Context

```python
with ErrorContext("restore", "RestoreService") as ctx:
    # Add parameters that help debugging
    ctx.add_context("snapshot_id", snapshot_id)
    ctx.add_context("target_path", target_path)
    ctx.add_context("repository", repository_name)
    
    # Don't add sensitive information
    # ctx.add_context("password", password)  # ❌ Bad
```

### 3. Provide Actionable Suggestions

```python
# Good - Specific and actionable
ctx.add_recovery_suggestion("Run 'tl repositories list' to see available repositories")
ctx.add_recovery_suggestion("Check repository credentials with 'tl credentials show'")

# Bad - Vague and unhelpful
ctx.add_recovery_suggestion("Fix the error")
ctx.add_recovery_suggestion("Try again")
```

### 4. Use Nested Contexts for Complex Operations

```python
def complex_operation():
    with ErrorContext("complex_op", "MainService") as main_ctx:
        main_ctx.add_context("operation_id", op_id)
        
        # Step 1
        with ErrorContext("validate", "Validator") as val_ctx:
            val_ctx.add_context("step", 1)
            validate_input()
        
        # Step 2
        with ErrorContext("process", "Processor") as proc_ctx:
            proc_ctx.add_context("step", 2)
            process_data()
        
        # Step 3
        with ErrorContext("finalize", "Finalizer") as fin_ctx:
            fin_ctx.add_context("step", 3)
            finalize_operation()
```

### 5. Don't Suppress Context

```python
# Good - Preserve context when re-raising
try:
    with ErrorContext("operation", "Service") as ctx:
        perform_operation()
except ValueError as e:
    # Add more context if needed
    ctx.add_recovery_suggestion("Check input format")
    raise  # Re-raise with context preserved

# Bad - Context is lost
try:
    with ErrorContext("operation", "Service") as ctx:
        perform_operation()
except ValueError as e:
    raise ValueError("Operation failed")  # ❌ Context lost
```

## Examples

See `src/TimeLocker/cli_modules/commands/example_error_context_command.py` for complete examples demonstrating:
- Simple error context usage
- Nested contexts
- Recovery suggestions
- Custom context metadata
- Multi-step operations

## Integration with Existing Commands

To add ErrorContext to existing commands:

1. Import the helpers:
```python
from TimeLocker.cli_modules.helpers import with_cli_error_context, show_cli_error
from TimeLocker.utils.error_handling import ErrorContext
```

2. Add the decorator or use context manager:
```python
@with_cli_error_context("command_name", "CommandComponent")
def my_command(...):
    # Existing implementation
    pass
```

3. Add recovery suggestions where appropriate:
```python
with ErrorContext("operation", "Service") as ctx:
    ctx.add_recovery_suggestion("Specific action to resolve error")
    # Existing code
```

## Testing

Test error context in your command tests:

```python
def test_command_with_error_context():
    """Test that error context is properly tracked"""
    from TimeLocker.utils.error_handling import ErrorContext
    
    with ErrorContext("test_op", "TestComponent") as ctx:
        ctx.add_context("test_param", "value")
        
        # Trigger error
        with pytest.raises(ValueError):
            command_that_fails()
        
        # Verify context was captured
        assert ctx.metadata["test_param"] == "value"
```

## Migration Guide

For existing commands without ErrorContext:

### Before
```python
def backup_create(...):
    try:
        result = perform_backup()
    except Exception as e:
        show_error_panel("Backup Failed", str(e))
        raise typer.Exit(1)
```

### After
```python
@with_cli_error_context("backup_create", "BackupCommand")
def backup_create(...):
    # Error handling is automatic
    result = perform_backup()
```

Or with manual context:

```python
def backup_create(...):
    try:
        with ErrorContext("backup_create", "BackupCommand") as ctx:
            ctx.add_context("repository", repository)
            ctx.add_recovery_suggestion("Check repository configuration")
            result = perform_backup()
    except Exception as e:
        show_cli_error(e, ctx)
        raise typer.Exit(1)
```

## Requirements Addressed

This implementation addresses:
- **Requirement 8.1**: Error context preservation throughout the call stack
- **Requirement 8.2**: User-friendly error formatting with context information
- **Requirement 8.3**: Recovery suggestions based on error type and context
- **Requirement 8.4**: Integration with existing error handling
- **Requirement 8.5**: Context includes operation details, input parameters, and system state
