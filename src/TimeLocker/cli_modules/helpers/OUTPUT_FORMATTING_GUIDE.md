# Output Formatting Guide

This guide explains how to use the new output formatting, non-interactive mode, and filtering capabilities in TimeLocker CLI commands.

## Overview

The CLI now supports:
- **JSON Output**: Machine-readable JSON format for all commands
- **Non-Interactive Mode**: Batch operation support with proper exit codes
- **Quiet Mode**: Suppressed non-essential output
- **Field Filtering**: Select or exclude specific fields from output
- **Pagination**: Handle large datasets efficiently

## JSON Output

### Basic Usage

Add the `--json` flag to any command to get JSON output:

```bash
timelocker repos list --json
```

### JSON Response Schema

All JSON responses follow a consistent schema:

```json
{
  "success": true,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "repos list",
  "data": {
    "items": [...],
    "total_count": 10
  }
}
```

### Error Response Schema

```json
{
  "success": false,
  "timestamp": "2024-01-01T12:00:00Z",
  "command": "repos create",
  "error": {
    "type": "ValidationError",
    "message": "Repository name is required",
    "details": ["Parameter 'name' is required in non-interactive mode"],
    "code": "MISSING_PARAMETER"
  }
}
```

### Implementation

```python
from .base import create_formatter, JsonOption

@command_app.command("list")
def list_items(
    json_output: JsonOption = False,
    # ... other parameters
):
    formatter = create_formatter(json_output=json_output)
    
    # Get data from service
    items = service.list_items()
    
    # Output with formatter
    formatter.table(items, command="items list")
```

## Non-Interactive Mode

### Basic Usage

Use `--non-interactive` flag for batch operations:

```bash
timelocker repos create myrepo --uri file:///backup --non-interactive
```

### Exit Codes

- `0`: Success
- `1`: Warning or operation error
- `2`: Validation error (missing parameters, invalid input)
- `130`: User cancellation (Ctrl+C)

### Parameter Validation

```python
from .base import (
    require_parameter,
    validate_parameters,
    NonInteractiveOption,
    ExitCode
)

@command_app.command("create")
def create_item(
    name: Optional[str] = None,
    non_interactive: NonInteractiveOption = False,
):
    formatter = create_formatter()
    
    # Validate required parameters
    if non_interactive:
        name = require_parameter(name, "name", formatter, allow_interactive=False)
    else:
        # Interactive prompting
        if name is None:
            name = Prompt.ask("Item name")
    
    # ... rest of implementation
```

### Batch Validation

```python
from .base import validate_parameters

# Validate multiple parameters at once
validate_parameters({
    'name': name,
    'uri': uri,
    'description': description
}, formatter=formatter, allow_interactive=not non_interactive)
```

## Quiet Mode

### Basic Usage

Suppress non-essential output with `--quiet`:

```bash
timelocker repos list --quiet
```

### Implementation

```python
from .base import QuietOption

@command_app.command("list")
def list_items(
    quiet: QuietOption = False,
):
    formatter = create_formatter(quiet=quiet)
    
    # Formatter automatically handles quiet mode
    formatter.info("Processing items...")  # Suppressed in quiet mode
    formatter.success("Operation complete")  # Shown in quiet mode
```

## Field Filtering

### Basic Usage

Select specific fields:

```bash
timelocker repos list --fields name,status,uri
```

Exclude specific fields:

```bash
timelocker repos list --exclude password,credentials
```

### Implementation

```python
from .base import (
    FieldsOption,
    ExcludeFieldsOption,
    create_filter,
    apply_filters_and_pagination
)

@command_app.command("list")
def list_items(
    fields: FieldsOption = None,
    exclude: ExcludeFieldsOption = None,
):
    # Get data
    items = service.list_items()
    
    # Create filter
    output_filter = create_filter(fields=fields, exclude=exclude)
    
    # Apply filtering
    result = apply_filters_and_pagination(
        data=items,
        filter=output_filter
    )
    
    # Output
    formatter.table(result["items"])
```

## Pagination

### Basic Usage

```bash
timelocker repos list --page 2 --page-size 10
```

### Implementation

```python
from .base import (
    PageOption,
    PageSizeOption,
    create_paginator,
    apply_filters_and_pagination
)

@command_app.command("list")
def list_items(
    page: PageOption = 1,
    page_size: PageSizeOption = 20,
):
    # Get data
    items = service.list_items()
    
    # Create paginator
    paginator = create_paginator(page_size=page_size)
    
    # Apply pagination
    result = apply_filters_and_pagination(
        data=items,
        paginator=paginator,
        page=page
    )
    
    # Output includes pagination metadata
    formatter.data(result)
```

## Complete Example

Here's a complete command implementation using all features:

```python
from typing import Optional
from .base import (
    create_typer_app,
    VerboseOption,
    JsonOption,
    QuietOption,
    NonInteractiveOption,
    FieldsOption,
    ExcludeFieldsOption,
    PageOption,
    PageSizeOption,
    create_formatter,
    create_filter,
    create_paginator,
    apply_filters_and_pagination,
    require_parameter,
    ExitCode,
)

app = create_typer_app("mycommand", "My command description")

@app.command("list")
def list_items(
    filter_status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    quiet: QuietOption = False,
    fields: FieldsOption = None,
    exclude: ExcludeFieldsOption = None,
    page: PageOption = 1,
    page_size: PageSizeOption = 20,
):
    """List items with filtering and pagination."""
    
    # Create formatter
    formatter = create_formatter(json_output=json_output, quiet=quiet)
    
    try:
        # Get data from service
        items = service.list_items(status=filter_status)
        
        # Apply filtering and pagination
        output_filter = create_filter(fields=fields, exclude=exclude)
        paginator = create_paginator(page_size=page_size)
        
        result = apply_filters_and_pagination(
            data=items,
            filter=output_filter,
            paginator=paginator,
            page=page
        )
        
        # Output
        formatter.table(result["items"], command="mycommand list")
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except Exception as e:
        formatter.error(f"Failed to list items: {e}")
        raise typer.Exit(ExitCode.ERROR.value)

@app.command("create")
def create_item(
    name: Optional[str] = typer.Argument(None, help="Item name"),
    description: Optional[str] = typer.Option(None, "--description", help="Description"),
    verbose: VerboseOption = False,
    json_output: JsonOption = False,
    non_interactive: NonInteractiveOption = False,
):
    """Create a new item."""
    
    formatter = create_formatter(json_output=json_output)
    
    try:
        # Validate required parameters
        if non_interactive:
            name = require_parameter(name, "name", formatter, allow_interactive=False)
        else:
            if name is None:
                name = Prompt.ask("Item name")
        
        # Create item
        result = service.create_item(name=name, description=description)
        
        # Output success
        formatter.success(
            f"Created item '{name}'",
            data=result,
            command="mycommand create"
        )
        
        raise typer.Exit(ExitCode.SUCCESS.value)
        
    except typer.Exit:
        raise
    except Exception as e:
        formatter.error(f"Failed to create item: {e}")
        raise typer.Exit(ExitCode.ERROR.value)
```

## Best Practices

1. **Always use OutputFormatter**: Don't mix formatter output with direct console.print()
2. **Consistent exit codes**: Use ExitCode enum for all exits
3. **Validate early**: Check required parameters before doing work
4. **Handle cancellation**: Always catch KeyboardInterrupt
5. **Provide context**: Include command name in JSON output
6. **Filter sensitive data**: Use filter_sensitive_fields() for credentials
7. **Test both modes**: Test commands in both interactive and non-interactive modes
8. **Document options**: Add clear help text for all options

## Testing

### Testing JSON Output

```python
from typer.testing import CliRunner
import json

def test_json_output():
    runner = CliRunner()
    result = runner.invoke(app, ["list", "--json"])
    
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert "data" in data
```

### Testing Non-Interactive Mode

```python
def test_non_interactive_missing_param():
    runner = CliRunner()
    result = runner.invoke(app, ["create", "--non-interactive"])
    
    assert result.exit_code == 2  # Validation error
    assert "Missing required parameter" in result.stdout
```

### Testing Pagination

```python
def test_pagination():
    runner = CliRunner()
    result = runner.invoke(app, ["list", "--page", "2", "--page-size", "10", "--json"])
    
    data = json.loads(result.stdout)
    assert data["data"]["pagination"]["page"] == 2
    assert data["data"]["pagination"]["page_size"] == 10
```

## Migration Guide

### Updating Existing Commands

1. Import new utilities:
```python
from .base import (
    create_formatter,
    JsonOption,
    QuietOption,
    NonInteractiveOption,
)
```

2. Add options to command signature:
```python
def my_command(
    json_output: JsonOption = False,
    quiet: QuietOption = False,
    non_interactive: NonInteractiveOption = False,
):
```

3. Replace output calls:
```python
# Old
show_success_panel("Success", "Operation complete")

# New
formatter = create_formatter(json_output=json_output, quiet=quiet)
formatter.success("Operation complete")
```

4. Add parameter validation:
```python
# Old
if name is None:
    name = Prompt.ask("Name")

# New
if non_interactive:
    name = require_parameter(name, "name", formatter, allow_interactive=False)
else:
    if name is None:
        name = Prompt.ask("Name")
```

5. Use proper exit codes:
```python
# Old
raise typer.Exit(1)

# New
raise typer.Exit(ExitCode.ERROR.value)
```
