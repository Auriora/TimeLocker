# UX Guidelines for CLI Development

**Status**: ✅ Complete  
**Date**: 2025-11-12  
**Audience**: Developers

## Overview

This document provides guidelines for using the UX components (PromptService, OutputFormatter, and ProgressService) to create consistent, user-friendly CLI commands in TimeLocker.

## Core Principles

### 1. Consistency

All commands should provide a consistent user experience:
- Use the same prompt patterns
- Use the same output formatting
- Use the same progress indicators
- Use the same error messages

### 2. Clarity

All user interactions should be clear and unambiguous:
- Use descriptive prompt messages
- Provide helpful error messages
- Show progress for long-running operations
- Display results in an easy-to-read format

### 3. Robustness

All commands should handle errors gracefully:
- Validate user input
- Provide helpful error messages
- Suggest recovery actions
- Degrade gracefully on failures

### 4. Flexibility

All commands should support multiple modes:
- Interactive mode for manual use
- Non-interactive mode for scripting
- JSON output for machine consumption
- Quiet mode for minimal output

## Using PromptService

### When to Use

Use PromptService for all user input:
- Repository names, paths, URIs
- Configuration values
- Confirmations
- Passwords and credentials
- Selections from lists

### Basic Pattern

```python
from TimeLocker.utils import get_prompt_service, PromptError

prompt_service = get_prompt_service()

try:
    # Prompt for required value
    name = prompt_service.prompt_text(
        "Enter repository name",
        required=True
    )
except PromptError:
    console.print("[red]Error: Repository name required[/red]")
    console.print("[yellow]Hint: Use --name option in non-interactive mode[/yellow]")
    raise typer.Exit(1)
```

### Prompt Messages

**Good prompt messages**:
- Clear and concise
- Indicate what is expected
- Use consistent terminology

```python
# Good
"Enter repository name"
"Select backup policy"
"Confirm deletion of repository 'myrepo'"

# Bad
"Name?"
"Pick one"
"Are you sure?"
```

### Defaults and Current Values

**Always provide defaults for non-interactive mode**:

```python
# Good - works in both modes
backend = prompt_service.prompt_choice(
    "Select backend type",
    choices=["local", "s3", "b2"],
    default="local"
)

# Bad - fails in non-interactive mode
backend = prompt_service.prompt_choice(
    "Select backend type",
    choices=["local", "s3", "b2"]
)
```

**Use current values for configuration updates**:

```python
# Good - preserves current value
name = prompt_service.prompt_text(
    "Repository name",
    current_value=config["name"],
    required=True
)

# Bad - loses current value
name = prompt_service.prompt_text(
    "Repository name",
    default="new-repo",
    required=True
)
```

### Confirmations

**Use confirmations for destructive operations**:

```python
# Confirm before deletion
confirmed = prompt_service.prompt_confirm(
    f"Delete repository '{repo_name}'? This cannot be undone.",
    default=False  # Default to safe option
)

if not confirmed:
    console.print("[yellow]Operation cancelled[/yellow]")
    raise typer.Exit(0)
```

### Password Prompts

**Handle password prompts carefully**:

```python
try:
    password = prompt_service.prompt_password(
        "Enter repository password",
        required=True
    )
except PromptError:
    # Password cannot be provided in non-interactive mode
    console.print("[red]Error: Password required[/red]")
    console.print("[yellow]Hint: Use environment variable or credential store[/yellow]")
    raise typer.Exit(1)
```

## Using OutputFormatter

### When to Use

Use OutputFormatter for all output:
- Tables of data
- Success/error/warning/info messages
- Structured data display
- JSON output

### Basic Pattern

```python
from TimeLocker.utils import get_output_formatter, OutputFormat

# Get formatter (respects --json flag)
formatter = get_output_formatter(
    console=console,
    output_format=OutputFormat.JSON if json_output else OutputFormat.RICH
)

# Display results
formatter.format_success(
    title="Operation Complete",
    message="Repository created successfully",
    details={"name": repo_name, "uri": repo_uri}
)
```

### Success Messages

**Use for successful operations**:

```python
formatter.format_success(
    title="Backup Complete",
    message="Backup completed successfully",
    details={
        "Repository": repo_name,
        "Snapshot ID": snapshot_id,
        "Files": f"{file_count:,}",
        "Size": format_size(total_size)
    }
)
```

### Error Messages

**Use for operation failures**:

```python
formatter.format_error(
    title="Backup Failed",
    message="Failed to connect to repository",
    details=[
        "Repository not found at specified path",
        "Check repository path and permissions",
        "Verify repository is initialized"
    ],
    exception=e  # Optional, for debugging
)
```

### Warning Messages

**Use for non-fatal issues**:

```python
formatter.format_warning(
    title="Configuration Warning",
    message="Some settings are using default values",
    details=[
        "retention_days not set, using default: 30",
        "compression not set, using default: auto"
    ]
)
```

### Info Messages

**Use for informational output**:

```python
formatter.format_info(
    title="Repository Information",
    message="Repository details",
    details={
        "Location": repo_path,
        "Backend": backend_type,
        "Snapshots": snapshot_count,
        "Total Size": format_size(total_size)
    }
)
```

### Tables

**Use for lists of data**:

```python
# Prepare data as list of dictionaries
repositories = [
    {"Name": "repo1", "Backend": "local", "Status": "active"},
    {"Name": "repo2", "Backend": "s3", "Status": "active"},
]

formatter.format_table(
    data=repositories,
    columns=["Name", "Backend", "Status"],
    title="Configured Repositories",
    show_header=True
)
```

### JSON Output

**Support JSON output for all commands**:

```python
# Set format based on --json flag
formatter = get_output_formatter(
    output_format=OutputFormat.JSON if json_output else OutputFormat.RICH
)

# All format methods automatically handle JSON output
formatter.format_table(data=repositories)
formatter.format_success("Success", "Operation complete")
```

## Using ProgressService

### When to Use

Use ProgressService for long-running operations:
- Backup operations
- Restore operations
- Repository operations (prune, check)
- Batch processing
- Validation operations

### Basic Pattern

```python
from TimeLocker.utils import get_progress_service

progress_service = get_progress_service(console=console)

with progress_service.spinner("Initializing backup...") as progress:
    # Perform operation
    initialize_backup()
    
    # Update description
    progress.update(description="Scanning files...")
    scan_files()
```

### Spinner Progress

**Use for indeterminate operations**:

```python
with progress_service.spinner("Connecting to repository...") as progress:
    connect_to_repository()
    
    progress.update(description="Verifying repository...")
    verify_repository()
```

### Bar Progress

**Use for determinate operations**:

```python
with progress_service.bar("Backing up files", total=file_count) as progress:
    for file in files:
        backup_file(file)
        progress.update(advance=1)
```

### Nested Progress

**Use for multi-step operations**:

```python
steps = ["Scan files", "Calculate checksums", "Upload data"]
with progress_service.nested("Backup Operation", steps) as (parent, children):
    for child in children:
        # Perform step
        perform_step(child.description)
        
        # Complete child and update parent
        child.complete()
        parent.update(advance=1)
```

### Progress Templates

**Use templates for common operations**:

```python
from TimeLocker.utils import ProgressTemplates

# Backup operation
with ProgressTemplates.backup_operation(progress_service, repo_name) as progress:
    perform_backup()

# Restore operation
with ProgressTemplates.restore_operation(progress_service, snapshot_id, target) as progress:
    perform_restore()

# Repository operation
with ProgressTemplates.repository_operation(progress_service, "check", repo_name) as progress:
    check_repository()

# Batch operation
with ProgressTemplates.batch_operation(progress_service, "Processing", total) as progress:
    for item in items:
        process_item(item)
        progress.update(advance=1)
```

### Disabling Progress

**Disable for non-interactive mode or quiet mode**:

```python
# Disable based on flags
progress_service = get_progress_service(
    console=console,
    enabled=not quiet and sys.stdin.isatty()
)

# Progress contexts will be no-ops when disabled
with progress_service.spinner("Working...") as progress:
    # No progress displayed, but code works the same
    do_work()
```

## Complete Command Example

Here's a complete example showing all UX components:

```python
import typer
from rich.console import Console
from TimeLocker.utils import (
    get_prompt_service,
    get_output_formatter,
    get_progress_service,
    PromptError,
    OutputFormat,
    ProgressTemplates
)

console = Console()

@app.command()
def backup(
    repository: Optional[str] = typer.Option(None, "--repository", "-r"),
    target: Optional[str] = typer.Option(None, "--target", "-t"),
    json_output: bool = typer.Option(False, "--json"),
    quiet: bool = typer.Option(False, "--quiet", "-q"),
    yes: bool = typer.Option(False, "--yes", "-y")
):
    """Perform a backup operation."""
    
    # Initialize services
    prompt_service = get_prompt_service()
    formatter = get_output_formatter(
        console=console,
        output_format=OutputFormat.JSON if json_output else OutputFormat.RICH
    )
    progress_service = get_progress_service(
        console=console,
        enabled=not quiet
    )
    
    try:
        # Prompt for repository if not provided
        if repository is None:
            try:
                repository = prompt_service.prompt_text(
                    "Enter repository name",
                    required=True
                )
            except PromptError:
                formatter.format_error(
                    title="Missing Parameter",
                    message="Repository name required",
                    details=["Use --repository option in non-interactive mode"]
                )
                raise typer.Exit(1)
        
        # Prompt for target if not provided
        if target is None:
            try:
                target = prompt_service.prompt_text(
                    "Enter backup target path",
                    default=".",
                    required=True
                )
            except PromptError:
                formatter.format_error(
                    title="Missing Parameter",
                    message="Target path required",
                    details=["Use --target option in non-interactive mode"]
                )
                raise typer.Exit(1)
        
        # Confirm operation
        if not yes:
            confirmed = prompt_service.prompt_confirm(
                f"Backup '{target}' to repository '{repository}'?",
                default=True
            )
            if not confirmed:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0)
        
        # Perform backup with progress
        with ProgressTemplates.backup_operation(progress_service, repository) as progress:
            # Initialize backup
            progress.update(description=f"Initializing backup to {repository}...")
            backup_id = initialize_backup(repository, target)
            
            # Scan files
            progress.update(description="Scanning files...")
            files = scan_files(target)
            
            # Backup files
            progress.update(description=f"Backing up {len(files)} files...")
            snapshot_id = backup_files(repository, files)
        
        # Display success
        formatter.format_success(
            title="Backup Complete",
            message="Backup completed successfully",
            details={
                "Repository": repository,
                "Target": target,
                "Snapshot ID": snapshot_id,
                "Files": f"{len(files):,}",
                "Size": format_size(calculate_size(files))
            }
        )
        
    except Exception as e:
        # Display error
        formatter.format_error(
            title="Backup Failed",
            message=str(e),
            details=[
                "Check repository configuration",
                "Verify target path exists",
                "Check available disk space"
            ],
            exception=e
        )
        raise typer.Exit(1)
```

## Error Handling Patterns

### Validation Errors

```python
try:
    validate_repository(repo_name)
except ValidationError as e:
    formatter.format_error(
        title="Validation Failed",
        message=str(e),
        details=[
            "Check repository name format",
            "Verify repository exists"
        ]
    )
    raise typer.Exit(1)
```

### Connection Errors

```python
try:
    connect_to_repository(repo_uri)
except ConnectionError as e:
    formatter.format_error(
        title="Connection Failed",
        message="Failed to connect to repository",
        details=[
            "Check repository URI",
            "Verify network connectivity",
            "Check credentials"
        ],
        exception=e
    )
    raise typer.Exit(1)
```

### Permission Errors

```python
try:
    write_to_repository(repo_path, data)
except PermissionError as e:
    formatter.format_error(
        title="Permission Denied",
        message="Insufficient permissions to write to repository",
        details=[
            "Check file permissions",
            "Verify user has write access",
            "Run with appropriate privileges"
        ],
        exception=e
    )
    raise typer.Exit(1)
```

## Testing Guidelines

### Unit Tests

Test each component in isolation:

```python
def test_prompt_service():
    """Test prompt service with various inputs."""
    service = PromptService(force_interactive=False)
    
    # Test with default
    result = service.prompt_text("Test", default="default")
    assert result == "default"
    
    # Test required without default
    with pytest.raises(PromptError):
        service.prompt_text("Test", required=True)
```

### Integration Tests

Test components working together:

```python
def test_complete_workflow():
    """Test complete workflow with all UX components."""
    prompt_service = PromptService(force_interactive=False)
    formatter = OutputFormatter(output_format=OutputFormat.RICH)
    progress_service = ProgressService(enabled=True)
    
    # Prompt for input
    name = prompt_service.prompt_text("Name", default="test")
    
    # Show progress
    with progress_service.spinner("Working..."):
        do_work()
    
    # Display result
    formatter.format_success("Success", "Operation complete")
```

## Best Practices Summary

### Do's

✅ Use PromptService for all user input  
✅ Use OutputFormatter for all output  
✅ Use ProgressService for long-running operations  
✅ Provide defaults for non-interactive mode  
✅ Use current values for configuration updates  
✅ Handle PromptError gracefully  
✅ Support JSON output  
✅ Show progress for operations > 1 second  
✅ Use appropriate prompt types (int, float, Path)  
✅ Provide helpful error messages  

### Don'ts

❌ Don't use Rich directly for prompts  
❌ Don't use Rich directly for output formatting  
❌ Don't use Rich Progress directly  
❌ Don't forget defaults for non-interactive mode  
❌ Don't ignore PromptError  
❌ Don't forget to support JSON output  
❌ Don't show progress for quick operations  
❌ Don't use text prompts for numeric values  
❌ Don't provide vague error messages  

## Related Documentation

- [PromptService Implementation](../../3-implementation/prompt-service.md)
- [OutputFormatter Implementation](../../3-implementation/output-formatter.md)
- [ProgressService Implementation](../../3-implementation/progress-service.md)
- [CLI Consolidation Stabilization](../../specs/001-cli-consolidation-stabilization/requirements.md)

## Conclusion

Following these UX guidelines ensures a consistent, user-friendly experience across all TimeLocker CLI commands. The UX components (PromptService, OutputFormatter, and ProgressService) provide the building blocks for creating robust, maintainable CLI commands that work well in both interactive and non-interactive modes.
