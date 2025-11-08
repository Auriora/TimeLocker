# TimeLocker CLI Module

**Last Updated**: 2025-11-08  
**Status**: Active Development  
**Related**: [CLI Refactoring Plan](../guides/cli-refactoring-plan.md), [Phase 1 Implementation](../updates/2025-11-07-cli-refactoring-phase1.md)

Modular command-line interface for TimeLocker backup operations.

## Structure

```
cli_modules/
├── __init__.py              # Main entry point, exports app
├── app.py                   # Typer app setup (to be created in Phase 2)
├── helpers/                 # Reusable utility functions
│   ├── __init__.py          # Helper exports
│   ├── display.py           # Panel display functions
│   ├── logging_setup.py     # Logging configuration
│   ├── service_helpers.py   # Service layer integration
│   ├── auth_helpers.py      # Authentication helpers
│   └── repository_helpers.py # Repository utilities
├── commands/                # Command group modules (Phase 2)
│   ├── __init__.py
│   ├── backup.py
│   ├── snapshots.py
│   ├── repositories.py
│   ├── targets.py
│   ├── config.py
│   ├── credentials.py
│   └── security.py
└── test_compatibility.py    # Test patches and fallbacks
```

## Usage

### Importing the CLI App

```python
from TimeLocker.cli import app

# Run the CLI
app()
```

### Using Helpers

```python
from TimeLocker.cli.helpers import (
    show_success_panel,
    show_error_panel,
    show_info_panel,
    setup_logging,
)

# Display success message
show_success_panel("Operation Complete", "Backup created successfully")

# Display error with details
show_error_panel("Backup Failed", "Could not connect to repository", 
                 ["Check network connection", "Verify credentials"])

# Setup logging
setup_logging(verbose=True)
```

### Creating New Commands

```python
from typing import Annotated, Optional
from pathlib import Path
import typer
from TimeLocker.cli.helpers import (
    show_success_panel,
    show_error_panel,
    setup_logging,
)

# Create command group
my_app = typer.Typer(help="My command group")

@my_app.command("mycommand")
def my_command(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    config_dir: Annotated[Optional[Path], typer.Option("--config-dir")] = None,
) -> None:
    """My command description."""
    setup_logging(verbose, config_dir)
    
    try:
        # Command implementation
        show_success_panel("Success", "Operation completed")
    except Exception as e:
        show_error_panel("Error", str(e))
        raise typer.Exit(1)
```

## Helper Modules

### display.py

Display utilities for consistent CLI output.

**Functions**:
- `show_success_panel(title, message, details=None)` - Green success panel
- `show_error_panel(title, message, details=None)` - Red error panel
- `show_info_panel(title, message)` - Blue info panel
- `format_file_size(size_bytes)` - Human-readable file sizes

**Example**:
```python
from TimeLocker.cli.helpers import show_success_panel, format_file_size

size = format_file_size(1024 * 1024 * 500)  # "500.0 MB"
show_success_panel("Backup Complete", f"Backed up {size}")
```

### logging_setup.py

Logging configuration with file output and user-facing CLI messages.

**Functions**:
- `setup_logging(verbose=False, config_dir=None)` - Configure logging

**Classes**:
- `UserFacingLogFilter` - Filter user-relevant log messages
- `CLILogHandler` - Rich panel formatting for logs

**Example**:
```python
from TimeLocker.cli.helpers import setup_logging

# Enable verbose logging
setup_logging(verbose=True)

# Logs go to ~/.cache/timelocker/logs/timelocker.log
```

### service_helpers.py

Service layer integration utilities.

**Functions**:
- `_get_service_method(manager, method_name)` - Get service method
- `_call_service_method(method, **kwargs)` - Call with parameter filtering
- `_resolve_config_dir(config_dir)` - Normalize config directory
- `_get_service_manager_for_command(config_dir)` - Get service manager
- `_create_credential_manager(config_dir)` - Create credential manager
- `_create_security_manager(config_dir)` - Create security manager
- `_create_configuration_module(config_dir)` - Create config module

**Example**:
```python
from TimeLocker.cli.helpers import _get_service_manager_for_command

manager = _get_service_manager_for_command(config_dir)
result = manager.list_repositories()
```

### auth_helpers.py

Authentication and session management.

**Functions**:
- `_authenticate_user_session(access_manager, user_id)` - Authenticate user
- `_validate_session_for_operation(access_manager, operation, repository_id)` - Validate session
- `_ensure_manager_unlocked(manager, master_password, interactive)` - Unlock credential manager

**Example**:
```python
from TimeLocker.cli.helpers import _ensure_manager_unlocked

manager = _create_credential_manager()
_ensure_manager_unlocked(manager, None, interactive=True)
```

### repository_helpers.py

Repository-related utilities.

**Functions**:
- `_determine_backend_from_uri(uri)` - Detect backend type from URI
- `_backend_display_name(backend)` - User-friendly backend name
- `_repository_config_to_dict(repository_obj, name)` - Convert repo config to dict

**Example**:
```python
from TimeLocker.cli.helpers import _determine_backend_from_uri, _backend_display_name

backend = _determine_backend_from_uri("s3://my-bucket/repo")  # "s3"
display = _backend_display_name(backend)  # "AWS"
```

## Testing

### Running Tests

```bash
# Run all CLI tests
pytest tests/test_cli.py -v

# Run with coverage
pytest tests/test_cli.py --cov=src/TimeLocker/cli --cov-report=html

# Run specific helper tests
pytest tests/cli/test_helpers_display.py -v
```

### Test Compatibility

The `test_compatibility.py` module provides patches for testing:

```python
from TimeLocker.cli.test_compatibility import setup_test_compatibility

# Setup all test patches
setup_test_compatibility()
```

## Development Guidelines

### Adding New Commands

1. Create command function with proper type hints
2. Use `setup_logging()` at the start
3. Use helper functions for display
4. Handle errors with try/except
5. Use `typer.Exit(code)` for exit codes

### Code Style

- Follow PEP 8
- Use type hints for all parameters and return values
- Add docstrings to all functions
- Keep functions focused (Single Responsibility)
- Use helper functions to avoid duplication (DRY)

### Error Handling

```python
try:
    # Command implementation
    show_success_panel("Success", "Operation completed")
except KeyboardInterrupt:
    show_error_panel("Cancelled", "Operation cancelled by user")
    raise typer.Exit(130)
except Exception as e:
    show_error_panel("Error", str(e))
    if verbose:
        console.print_exception()
    raise typer.Exit(1)
```

## Refactoring Status

- ✅ **Phase 1**: Helper extraction complete
- 🔄 **Phase 2**: Command group separation (in progress)
- 📋 **Phase 3**: Pattern consolidation (planned)

See [CLI Refactoring Plan](../guides/cli-refactoring-plan.md) for details.

## Contributing

When adding new commands or helpers:

1. Follow the existing structure
2. Add type hints and docstrings
3. Write tests for new functionality
4. Update this documentation
5. Run full test suite before committing

## Resources

- [CLI Refactoring Plan](../guides/cli-refactoring-plan.md)
- [Phase 1 Implementation](../updates/2025-11-07-cli-refactoring-phase1.md)
- [Coding Standards](../../.kiro/steering/coding-standards.md)
