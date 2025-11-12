# OutputFormatter Implementation Guide

## Overview

The `OutputFormatter` class provides a centralized, consistent way to format and display output in TimeLocker CLI commands. It supports multiple output formats (Rich formatted, JSON, and plain text) and handles graceful degradation when formatting fails.

## Location

- **Module**: `src/TimeLocker/utils/output_formatter.py`
- **Exports**: `OutputFormatter`, `OutputFormat`, `get_output_formatter`

## Features

- **Multiple Output Formats**: Rich (default), JSON, and Plain text
- **Consistent Styling**: Standardized colors and formatting across all commands
- **Graceful Degradation**: Falls back to plain text if Rich formatting fails
- **JSON Support**: All formatted data can be output as JSON for machine-readable consumption
- **Type Safety**: Full type hints for all methods

## Basic Usage

### Getting an OutputFormatter Instance

```python
from TimeLocker.utils import get_output_formatter, OutputFormat
from rich.console import Console

# Get default formatter (Rich format)
formatter = get_output_formatter()

# Get formatter with specific console
console = Console()
formatter = get_output_formatter(console=console)

# Get formatter with JSON output
formatter = get_output_formatter(output_format=OutputFormat.JSON)
```

### Formatting Tables

```python
# Prepare data as list of dictionaries
data = [
    {"Name": "repo1", "URI": "file:///backup/repo1", "Status": "active"},
    {"Name": "repo2", "URI": "s3://bucket/repo2", "Status": "active"},
]

# Format and display table
formatter.format_table(
    data=data,
    columns=["Name", "URI", "Status"],  # Optional, auto-detected if None
    title="Configured Repositories",
    show_header=True,
    show_lines=False
)
```

### Formatting Messages

```python
# Success message
formatter.format_success(
    title="Operation Complete",
    message="Repository created successfully",
    details={"name": "myrepo", "uri": "file:///backup/myrepo"}
)

# Error message
formatter.format_error(
    title="Operation Failed",
    message="Failed to create repository",
    details=["Invalid URI format", "Permission denied"],
    exception=some_exception  # Optional
)

# Warning message
formatter.format_warning(
    title="Warning",
    message="Repository already exists",
    details=["Using existing repository"]
)

# Info message
formatter.format_info(
    title="Information",
    message="Repository is ready",
    details={"snapshots": 10, "size": "1.2 GB"}
)
```

### Formatting Panels

```python
# Custom panel
formatter.format_panel(
    content="This is custom content",
    title="Custom Panel",
    style="white",
    border_style="blue",
    expand=False
)
```

### Formatting Trees

```python
# Hierarchical data
data = {
    "repository": {
        "name": "myrepo",
        "snapshots": [
            {"id": "abc123", "date": "2024-01-01"},
            {"id": "def456", "date": "2024-01-02"}
        ]
    }
}

formatter.format_tree(
    root_label="Repository Structure",
    data=data,
    guide_style="blue"
)
```

### JSON Output

```python
# Any data structure
formatter.format_json({"status": "success", "data": [1, 2, 3]})
```

## Migrating Existing Code

### Before (Direct Rich Usage)

```python
from rich.table import Table
from rich.panel import Panel

# Create table
table = Table(title="Repositories")
table.add_column("Name", style="cyan")
table.add_column("URI", style="green")

for repo in repositories:
    table.add_row(repo["name"], repo["uri"])

console.print(table)

# Create panel
panel = Panel(
    "✅ Success message",
    title="[bold green]Success[/bold green]",
    border_style="green"
)
console.print(panel)
```

### After (Using OutputFormatter)

```python
from TimeLocker.utils import get_output_formatter

formatter = get_output_formatter(console=console)

# Format table
table_data = [
    {"Name": repo["name"], "URI": repo["uri"]}
    for repo in repositories
]
formatter.format_table(
    data=table_data,
    columns=["Name", "URI"],
    title="Repositories"
)

# Format success message
formatter.format_success(
    title="Success",
    message="Success message"
)
```

## Helper Functions in cli.py

The following helper functions in `cli.py` now use `OutputFormatter` internally:

```python
def show_success_panel(title: str, message: str, details: Optional[dict] = None) -> None:
    """Display a success panel with optional details."""
    formatter = get_output_formatter(console=console)
    formatter.format_success(title, message, details)

def show_error_panel(title: str, message: str, details: Optional[List[str]] = None) -> None:
    """Display an error panel with optional details."""
    formatter = get_output_formatter(console=console)
    formatter.format_error(title, message, details)

def show_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    formatter = get_output_formatter(console=console)
    formatter.format_info(title, message)
```

These functions remain available for backward compatibility, but new code should use `OutputFormatter` directly.

## Output Format Modes

### Rich Format (Default)

- Colorful, styled output using Rich library
- Tables with borders and styling
- Panels with icons and colors
- Best for interactive terminal use

### JSON Format

- Machine-readable JSON output
- All data structures serialized to JSON
- Suitable for scripting and automation
- Set via `formatter.set_format(OutputFormat.JSON)`

### Plain Text Format

- Simple text output without styling
- Automatic fallback when Rich formatting fails
- Compatible with all terminals
- Set via `formatter.set_format(OutputFormat.PLAIN)`

## Benefits

1. **Consistency**: All commands use the same formatting patterns
2. **Maintainability**: Changes to formatting only need to be made in one place
3. **Flexibility**: Easy to switch between output formats
4. **Robustness**: Graceful degradation when formatting fails
5. **Code Reduction**: Eliminates ~70 lines of duplicated formatting code across 35+ commands

## Requirements Addressed

- **Requirement 5.1**: Standardized formatting for tables, panels, JSON, and error messages
- **Requirement 5.2**: Consistent styling and formatting rules
- **Requirement 5.3**: JSON output support for all formatted data structures
- **Requirement 5.4**: Reduces output formatting code by at least 70 lines across 35 commands
- **Requirement 5.5**: Gracefully degrades to plain text output on formatting failures

## Testing

### Unit Tests

**Location**: `tests/TimeLocker/cli/test_output_formatting.py`

**Test Categories**:
1. Formatter creation and configuration
2. JSON output formatting
3. Non-interactive mode handling
4. Output filtering
5. Pagination
6. Sensitive field filtering
7. Exit codes

**Results**: All tests passing

### Integration Tests

**Location**: `tests/TimeLocker/integration/test_ux_components_integration.py`

**Integration Test Categories**:
1. Table formatting workflows
2. JSON output consistency
3. Panel formatting for various message types
4. Success/error/warning/info message formatting
5. Tree formatting for hierarchical data
6. Format switching (RICH/JSON/PLAIN)
7. Graceful degradation
8. Complete workflows with multiple components

**Results**: 11 integration tests, all passing

### Example Tests

```python
# Test basic functionality
from TimeLocker.utils.output_formatter import OutputFormatter, OutputFormat

formatter = OutputFormatter()

# Test table formatting
formatter.format_table(
    data=[{"col1": "val1", "col2": "val2"}],
    title="Test Table"
)

# Test JSON mode
formatter.set_format(OutputFormat.JSON)
formatter.format_success("Test", "Success message")

# Test error handling
formatter.format_error("Error", "Error message", ["Detail 1"])
```

## Future Enhancements

- Support for custom themes
- Progress bar integration
- Streaming output for large datasets
- Export to file formats (CSV, HTML)
- Internationalization support
