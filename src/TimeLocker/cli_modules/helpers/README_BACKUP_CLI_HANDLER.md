# Backup CLI Handler

## Overview

The `BackupCLIHandler` provides CLI-specific integration between backup operations and the data selection system. It handles template resolution, validation, and translation to backup job configurations.

## Purpose

This handler serves as the bridge between CLI commands and the backup orchestration system, with special focus on:

- Selection template resolution and validation
- CLI parameter translation to backup job configuration
- User-friendly error handling and messaging
- Help text generation and consistency

## Usage

```python
from TimeLocker.cli_modules.helpers import BackupCLIHandler
from TimeLocker.selection_manager import SelectionManager
from TimeLocker.interfaces.backup_orchestrator import IBackupOrchestrator

# Initialize dependencies
selection_manager = SelectionManager()
backup_orchestrator = BackupOrchestrator(...)

# Create handler
handler = BackupCLIHandler(selection_manager, backup_orchestrator)

# Execute backup with selection template
result = await handler.execute_backup_with_selection(
    selection_name="my-template",
    repository="my-repo",
    tags=["daily", "important"],
    dry_run=False
)
```

## Key Methods

### `validate_selection_exists(selection_name: str) -> bool`

Check if a selection template exists.

### `get_selection_summary(selection_name: str) -> str`

Get a human-readable summary of a selection template.

### `execute_backup_with_selection(...) -> BackupResult`

Execute a backup using a named data selection template. This is the main method that:
1. Validates the template exists
2. Validates the template configuration
3. Translates the template to a backup job configuration
4. Executes the backup job

### `get_available_templates() -> List[str]`

Get a list of all available selection template names.

### `suggest_template_creation(selection_name: str) -> str`

Generate a helpful message suggesting how to create a missing template.

## Error Handling

The handler provides specific exceptions for different error scenarios:

- `SelectionTemplateNotFoundError`: Raised when a template doesn't exist
- `InvalidSelectionConfigError`: Raised when a template configuration is invalid
- `BackupCLIHandlerError`: Base exception for general handler errors

All error messages include helpful suggestions for resolution.

## Integration with Requirements

This implementation satisfies the following requirements from the backup-operations spec:

- **Requirement 10.1**: Provides CLI command support for creating backups using data selection templates
- **Requirement 10.2**: Retrieves templates from SelectionManager when specified by name
- **Requirement 10.3**: Translates data selection template rules into backup tool-specific parameters
- **Requirement 10.4**: Provides clear error messages with suggestions when templates don't exist

## Testing

Comprehensive tests are available in `tests/TimeLocker/cli_modules/helpers/test_backup_cli_handler.py`.

Run tests with:
```bash
pytest tests/TimeLocker/cli_modules/helpers/test_backup_cli_handler.py -v
```

## Future Enhancements

- Support for template parameter overrides from CLI
- Template validation caching for performance
- Integration with backup history for template usage tracking
