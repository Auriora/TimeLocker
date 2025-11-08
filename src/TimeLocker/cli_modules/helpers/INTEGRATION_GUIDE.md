# Interactive Mode and Configuration Branching Integration Guide

This guide demonstrates how to integrate interactive prompts, configuration wizards, and configuration branching into CLI commands.

## Overview

The interactive mode and configuration branching features provide:

1. **Smart prompts** for missing required parameters
2. **Configuration wizards** for complex entity creation
3. **Configuration branching** - creating dependencies during setup
4. **Current value display** during edit operations

## Components

### Interactive Prompts (`interactive.py`)

Provides smart prompts with validation:

```python
from TimeLocker.cli_modules.helpers import (
    prompt_for_value,
    prompt_for_int,
    prompt_for_bool,
    prompt_for_path,
    prompt_for_list,
    display_current_config,
    is_interactive
)

# Simple value prompt
name = prompt_for_value(
    "Repository name",
    required=True,
    validator=validate_repository_name
)

# Integer prompt with range validation
port = prompt_for_int(
    "Port number",
    default=8080,
    min_value=1024,
    max_value=65535
)

# Boolean confirmation
enabled = prompt_for_bool(
    "Enable feature?",
    default=True
)

# Path prompt with validation
backup_path = prompt_for_path(
    "Backup directory",
    must_exist=True,
    must_be_dir=True
)

# List of values
tags = prompt_for_list(
    "Tags",
    separator=",",
    required=False
)
```

### Configuration Wizards (`wizards.py`)

Step-by-step wizards for complex configurations:

```python
from TimeLocker.cli_modules.helpers import (
    repository_creation_wizard,
    policy_creation_wizard,
    schedule_creation_wizard,
    WizardCancelled
)

try:
    # Repository creation wizard
    repo_config = repository_creation_wizard(
        config_module=config_module,
        credential_manager=credential_manager,
        name=name,  # Optional pre-filled values
        uri=uri
    )
    
    # Policy creation wizard (with repository branching)
    policy_config = policy_creation_wizard(
        config_module=config_module,
        name=policy_name,
        repository_name=repo_name  # Can be None - wizard will prompt
    )
    
    # Schedule creation wizard (with policy branching)
    schedule_config = schedule_creation_wizard(
        config_module=config_module,
        name=schedule_name,
        policy_name=policy_name  # Can be None - wizard will prompt
    )
    
except WizardCancelled:
    show_info_panel("Cancelled", "Operation cancelled by user")
    raise typer.Exit(0)
```

### Command Integration (`command_integration.py`)

Utilities for integrating interactive features into commands:

```python
from TimeLocker.cli_modules.helpers import (
    with_interactive_fallback,
    ensure_repository_exists,
    ensure_policy_exists,
    validate_configuration_dependencies,
    prompt_for_missing_parameters
)

# Automatic wizard fallback for missing parameters
config = with_interactive_fallback(
    wizard_func=repository_creation_wizard,
    required_params={"name": name, "uri": uri},
    config_module=config_module,
    credential_manager=credential_manager
)

# Ensure repository exists (with creation option)
repo_name = ensure_repository_exists(
    repository_name=repo_name,
    config_module=config_module,
    credential_manager=credential_manager,
    allow_creation=True
)

# Validate all dependencies
validated_config = validate_configuration_dependencies(
    config={"repository": repo_name, "policy": policy_name},
    config_module=config_module,
    required_dependencies={
        "repository": "repository",
        "policy": "policy"
    }
)
```

## Integration Examples

### Example 1: Repository Add Command with Wizard

```python
@repos_app.command("add")
def repos_add(
    name: Optional[str] = None,
    uri: Optional[str] = None,
    description: Optional[str] = None,
    verbose: bool = False,
    config_dir: Optional[Path] = None,
):
    """Add a new repository."""
    setup_logging(verbose, config_dir)
    config_module = _create_configuration_module(config_dir)
    credential_manager = _create_credential_manager(config_dir)
    
    try:
        # Use wizard if parameters are missing
        repo_config = with_interactive_fallback(
            wizard_func=repository_creation_wizard,
            required_params={"name": name, "uri": uri},
            config_module=config_module,
            credential_manager=credential_manager
        )
        
        # Create repository with collected configuration
        # ... repository creation logic ...
        
        show_success_panel(
            "Repository Added",
            f"Repository '{repo_config['name']}' added successfully"
        )
        
    except WizardCancelled:
        show_info_panel("Cancelled", "Repository creation cancelled")
        raise typer.Exit(0)
    except ValidationError as e:
        show_error_panel("Validation Error", str(e))
        raise typer.Exit(2)
```

### Example 2: Policy Create with Repository Branching

```python
@policy_app.command("create")
def policy_create(
    name: Optional[str] = None,
    repository: Optional[str] = None,
    selection: Optional[str] = None,
    verbose: bool = False,
    config_dir: Optional[Path] = None,
):
    """Create a new backup policy."""
    setup_logging(verbose, config_dir)
    config_module = _create_configuration_module(config_dir)
    credential_manager = _create_credential_manager(config_dir)
    
    try:
        # Prompt for missing parameters
        params = prompt_for_missing_parameters(
            command_name="policy create",
            parameters={"name": name},
            parameter_prompts={"name": "Policy name"},
            parameter_validators={"name": validate_repository_name}
        )
        
        # Ensure repository exists (with creation option)
        repo_name = ensure_repository_exists(
            repository_name=repository,
            config_module=config_module,
            credential_manager=credential_manager,
            allow_creation=True
        )
        
        # Create policy with validated dependencies
        # ... policy creation logic ...
        
        show_success_panel(
            "Policy Created",
            f"Policy '{params['name']}' created successfully"
        )
        
    except WizardCancelled:
        show_info_panel("Cancelled", "Policy creation cancelled")
        raise typer.Exit(0)
    except ValidationError as e:
        show_error_panel("Validation Error", str(e))
        raise typer.Exit(2)
```

### Example 3: Edit Command with Current Values

```python
@repos_app.command("edit")
def repos_edit(
    name: str,
    verbose: bool = False,
    config_dir: Optional[Path] = None,
):
    """Edit an existing repository."""
    setup_logging(verbose, config_dir)
    config_module = _create_configuration_module(config_dir)
    
    try:
        # Get current configuration
        current_repo = config_module.get_repository(name)
        current_config = {
            "name": name,
            "uri": current_repo.uri,
            "description": current_repo.description or ""
        }
        
        # Display current configuration
        display_current_config("Current Repository Configuration", current_config)
        
        # Prompt for changes with current values
        new_description = prompt_for_value(
            "Description",
            current_value=current_config["description"],
            required=False
        )
        
        # Update only if changed
        if new_description != current_config["description"]:
            # ... update logic ...
            show_success_panel("Updated", f"Repository '{name}' updated")
        else:
            show_info_panel("No Changes", "No changes made")
        
    except Exception as e:
        show_error_panel("Edit Error", str(e))
        raise typer.Exit(1)
```

### Example 4: Schedule Create with Policy Branching

```python
@schedule_app.command("create")
def schedule_create(
    name: Optional[str] = None,
    policy: Optional[str] = None,
    frequency: Optional[str] = None,
    verbose: bool = False,
    config_dir: Optional[Path] = None,
):
    """Create a new backup schedule."""
    setup_logging(verbose, config_dir)
    config_module = _create_configuration_module(config_dir)
    
    try:
        # Use wizard for complete configuration
        schedule_config = with_interactive_fallback(
            wizard_func=schedule_creation_wizard,
            required_params={"name": name, "policy": policy},
            config_module=config_module
        )
        
        # Validate policy exists (with creation option)
        policy_name = ensure_policy_exists(
            policy_name=schedule_config["policy"],
            config_module=config_module,
            allow_creation=True
        )
        
        # Create schedule
        # ... schedule creation logic ...
        
        show_success_panel(
            "Schedule Created",
            f"Schedule '{schedule_config['name']}' created successfully"
        )
        
    except WizardCancelled:
        show_info_panel("Cancelled", "Schedule creation cancelled")
        raise typer.Exit(0)
    except ValidationError as e:
        show_error_panel("Validation Error", str(e))
        raise typer.Exit(2)
```

## Best Practices

1. **Always check for interactive mode** before prompting
2. **Provide clear error messages** in non-interactive mode
3. **Display current values** during edit operations
4. **Validate input** with helpful error messages
5. **Handle cancellation gracefully** (Ctrl+C, wizard cancellation)
6. **Use configuration branching** to simplify complex workflows
7. **Show summaries** before committing changes
8. **Provide help text** in wizards to guide users

## Testing Interactive Features

When testing commands with interactive features:

```python
from typer.testing import CliRunner

runner = CliRunner()

# Test with all parameters (non-interactive)
result = runner.invoke(app, ["repos", "add", "myrepo", "file:///path"])
assert result.exit_code == 0

# Test with missing parameters (simulated interactive)
result = runner.invoke(
    app,
    ["repos", "add"],
    input="myrepo\nfile:///path\n\n"  # Simulated user input
)
assert result.exit_code == 0

# Test wizard cancellation
result = runner.invoke(
    app,
    ["repos", "add"],
    input="\x03"  # Ctrl+C
)
assert result.exit_code == 130
```

## Migration Path

To migrate existing commands to use interactive features:

1. **Identify commands** that would benefit from interactive mode
2. **Add wizard support** for complex configurations
3. **Implement parameter prompts** for missing required values
4. **Add configuration branching** where dependencies exist
5. **Update edit commands** to display current values
6. **Test both interactive and non-interactive modes**
7. **Update documentation** with examples

## Requirements Addressed

- **3.1**: Interactive mode with prompts for missing required parameters
- **3.2**: Configuration wizards for complex entity creation
- **3.3**: Display current configuration values during edit operations
- **3.4**: Non-interactive mode with proper exit codes
- **18.1**: Allow creating repositories during policy configuration
- **18.2**: Allow creating selections during policy configuration
- **18.3**: Guided configuration flows with help text and examples
- **18.4**: Allow creating policies during schedule configuration
- **18.5**: Validate relationships and offer to create missing dependencies
