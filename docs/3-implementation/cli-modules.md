# TimeLocker CLI Module

**Last Updated**: 2025-11-13
**Status**: Active Development
**Related**: [CLI Refactoring Plan](../archive/cli-refactoring/cli-refactoring-plan.md), [Command Registry API](command-registry-api.md)

Modular command-line interface for TimeLocker backup operations.

## Structure

```
cli_modules/
├── __init__.py                    # Main entry point, exports app
├── command_registry.py            # Command registration system
├── registry_integration.py        # Registry integration with CLI
├── monitoring_integration.py      # Monitoring integration
├── test_compatibility.py          # Test patches and fallbacks
├── README.md                      # CLI modules overview
├── README_COMMAND_REGISTRY.md     # Command registry documentation
├── commands/                      # Command group modules
│   ├── __init__.py
│   ├── base.py                    # Base command functionality
│   ├── backup.py                  # Backup operations
│   ├── snapshots.py               # Snapshot management
│   ├── repositories.py            # Repository management
│   ├── selections.py              # Data selection (replaces targets)
│   ├── restore.py                 # Restore operations
│   ├── policy.py                  # Policy management
│   ├── schedule.py                # Scheduling commands
│   ├── monitor.py                 # Monitoring commands
│   ├── monitoring.py              # Additional monitoring features
│   ├── config.py                  # Configuration management
│   ├── credentials.py             # Credential management
│   ├── security.py                # Security operations
│   ├── example_enhanced_command.py
│   ├── example_error_context_command.py
│   └── example_service_facade_usage.py
├── helpers/                       # Reusable utility functions
│   ├── __init__.py                # Helper exports
│   ├── display.py                 # Panel display functions
│   ├── logging_setup.py           # Logging configuration
│   ├── service_helpers.py         # Service layer integration
│   ├── auth_helpers.py            # Authentication helpers
│   ├── repository_helpers.py      # Repository utilities
│   ├── backup_cli_handler.py      # Backup CLI operations
│   ├── command_integration.py     # Command integration utilities
│   ├── error_context_helpers.py   # Error context handling
│   ├── interactive.py             # Interactive mode utilities
│   ├── non_interactive.py         # Non-interactive mode utilities
│   ├── output_formatter.py        # Output formatting
│   ├── output_filtering.py        # Output filtering
│   ├── performance.py             # Performance utilities
│   ├── platform_compat.py         # Platform compatibility
│   ├── aliases.py                 # Command aliases
│   ├── wizards.py                 # Interactive wizards
│   ├── INTEGRATION_GUIDE.md
│   ├── OUTPUT_FORMATTING_GUIDE.md
│   └── README_BACKUP_CLI_HANDLER.md
├── services/                      # CLI service layer
│   ├── __init__.py
│   ├── config_service.py          # Configuration service
│   └── repository_resolver.py     # Repository resolution
├── testing/                       # Testing utilities
│   ├── __init__.py
│   ├── assertions.py              # Test assertions
│   ├── fixtures.py                # Test fixtures
│   ├── generators.py              # Test data generators
│   ├── mocks.py                   # Mock objects
│   ├── runners.py                 # Test runners
│   └── README.md
└── validation/                    # Validation framework
    ├── __init__.py
    ├── base.py                    # Base validators
    ├── common.py                  # Common validations
    ├── config.py                  # Config validators
    ├── context.py                 # Validation context
    ├── helpers.py                 # Validation helpers
    └── README.md
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

## Command Modules

### Core Commands

- **backup.py** - Backup operations and job execution
- **snapshots.py** - Snapshot browsing and management
- **repositories.py** - Repository configuration and management
- **selections.py** - Data selection patterns and templates (replaces deprecated `targets` command)
- **restore.py** - Full restore namespace with file/directory recovery operations
- **config.py** - Configuration management (import/export/migration)
- **credentials.py** - Credential storage and management
- **security.py** - Security operations and access control

### Advanced Commands

- **policy.py** - Policy management and enforcement
- **schedule.py** - Job scheduling and automation
- **monitor.py** - System monitoring and status
- **monitoring.py** - Additional monitoring features

### Infrastructure

- **base.py** - Base command functionality and shared utilities
- **command_registry.py** - Dynamic command registration system for plugins
- **registry_integration.py** - Integration between command registry and CLI
- **monitoring_integration.py** - Integration of monitoring features into CLI

See [Command Registry API](command-registry-api.md) for details on the plugin system.

## Services Layer

The `services/` directory provides CLI-specific services:

- **config_service.py** - Configuration service with validation and defaults
- **repository_resolver.py** - Repository name/URI resolution with credential integration

## Validation Framework

The `validation/` directory provides a comprehensive validation framework:

- **base.py** - Base validator classes and interfaces
- **common.py** - Common validation rules (paths, URIs, formats)
- **config.py** - Configuration-specific validators
- **context.py** - Validation context for error reporting
- **helpers.py** - Validation helper functions

## Testing Infrastructure

The `testing/` directory provides testing utilities:

- **assertions.py** - Custom assertions for CLI tests
- **fixtures.py** - Reusable test fixtures
- **generators.py** - Test data generators
- **mocks.py** - Mock objects for testing
- **runners.py** - Test execution utilities

## Refactoring Status

- ✅ **Phase 1**: Helper extraction complete
- ✅ **Phase 2**: Command group separation complete
- ✅ **Phase 3**: Command registry and plugin system implemented
- ✅ **Infrastructure**: Services, validation, and testing frameworks added

See [CLI Refactoring Plan](../archive/cli-refactoring/cli-refactoring-plan.md) for historical details.

## Contributing

When adding new commands or helpers:

1. Follow the existing structure
2. Add type hints and docstrings
3. Write tests for new functionality
4. Update this documentation
5. Run full test suite before committing

## Resources

- [CLI Refactoring Plan](../archive/cli-refactoring/cli-refactoring-plan.md)
- [Phase 1 Implementation](../updates/2025-11-07-093135-cli-refactoring-phase1.md)
- [Coding Standards](../../.kiro/steering/coding-standards.md)
