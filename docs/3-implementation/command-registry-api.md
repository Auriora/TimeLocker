# CommandRegistry API Documentation

## Overview

The CommandRegistry provides centralized command metadata management for the TimeLocker CLI. It enables dynamic command registration, discovery, and plugin support, making the CLI extensible and maintainable.

## Architecture

The CommandRegistry consists of:

1. **CommandRegistry**: Main registry class for managing commands
2. **CommandMetadata**: Metadata describing a command
3. **PluginMetadata**: Metadata describing a plugin
4. **CommandCategory**: Enum for categorizing commands

## Core Components

### CommandRegistry

Main class for managing CLI commands and plugins.

```python
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
    get_command_registry,
)

# Get global registry instance
registry = get_command_registry()

# Or create a new registry
registry = CommandRegistry()
```

**Key Features:**
- Command registration and discovery
- Alias management
- Plugin support
- Command search and filtering
- Metadata validation
- Statistics and reporting

### CommandMetadata

Describes a CLI command with its properties and requirements.

```python
import typer
from TimeLocker.cli_modules.command_registry import CommandMetadata, CommandCategory

app = typer.Typer(help="Backup operations")

metadata = CommandMetadata(
    name="backup-create",
    category=CommandCategory.BACKUP,
    description="Create a new backup",
    app=app,
    aliases=["bc", "create-backup"],
    hidden=False,
    deprecated=False,
    requires_config=True,
    requires_repository=True,
    tags={"backup", "create"}
)
```

**Fields:**
- `name`: Command name (required)
- `category`: Command category (required)
- `description`: Short description (required)
- `app`: Typer app instance (required)
- `callback`: Optional command callback function
- `aliases`: Alternative names for the command
- `hidden`: Whether to hide from help
- `deprecated`: Whether the command is deprecated
- `deprecation_message`: Message for deprecated commands
- `requires_config`: Whether command requires configuration
- `requires_repository`: Whether command requires a repository
- `plugin_name`: Name of plugin providing this command
- `version`: Command version (for plugins)
- `tags`: Additional tags for filtering/searching

### CommandCategory

Enum for organizing commands into categories.

```python
from TimeLocker.cli_modules.command_registry import CommandCategory

# Available categories
CommandCategory.BACKUP        # Backup operations
CommandCategory.RESTORE       # Restore operations
CommandCategory.REPOSITORY    # Repository management
CommandCategory.SNAPSHOT      # Snapshot operations
CommandCategory.CONFIGURATION # Configuration management
CommandCategory.SECURITY      # Security operations
CommandCategory.MONITORING    # Monitoring and reporting
CommandCategory.SCHEDULING    # Scheduling and automation
CommandCategory.POLICY        # Policy management
CommandCategory.SELECTION     # File selection
CommandCategory.UTILITY       # Utility commands
CommandCategory.PLUGIN        # Plugin commands
```

### PluginMetadata

Describes a plugin that provides additional commands.

```python
from TimeLocker.cli_modules.command_registry import PluginMetadata

plugin = PluginMetadata(
    name="backup-plugin",
    version="1.0.0",
    author="Plugin Author",
    description="Custom backup plugin",
    commands=["custom-backup", "custom-restore"],
    enabled=True,
    path=Path("/path/to/plugin")
)
```

## API Reference

### Registering Commands

#### register_command()

Register a command with the registry.

```python
registry.register_command(metadata, allow_override=False)
```

**Parameters:**
- `metadata`: CommandMetadata instance
- `allow_override`: Whether to allow overriding existing commands

**Raises:**
- `CommandAlreadyRegisteredError`: If command already exists and override not allowed
- `ValueError`: If metadata is invalid

**Example:**
```python
import typer
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
)

registry = CommandRegistry()
app = typer.Typer(help="Backup command")

metadata = CommandMetadata(
    name="backup",
    category=CommandCategory.BACKUP,
    description="Backup operations",
    app=app,
    aliases=["bak", "b"]
)

registry.register_command(metadata)
```

#### unregister_command()

Unregister a command from the registry.

```python
registry.unregister_command(name)
```

**Parameters:**
- `name`: Command name to unregister

**Raises:**
- `CommandNotFoundError`: If command doesn't exist

### Querying Commands

#### get_command()

Get command metadata by name or alias.

```python
metadata = registry.get_command(name)
```

**Parameters:**
- `name`: Command name or alias

**Returns:**
- CommandMetadata instance

**Raises:**
- `CommandNotFoundError`: If command doesn't exist

**Example:**
```python
# Get by name
metadata = registry.get_command("backup")

# Get by alias
metadata = registry.get_command("bak")
```

#### has_command()

Check if a command exists.

```python
exists = registry.has_command(name)
```

**Parameters:**
- `name`: Command name or alias

**Returns:**
- `True` if command exists, `False` otherwise

#### list_commands()

List registered commands with optional filtering.

```python
commands = registry.list_commands(
    category=None,
    include_hidden=False,
    include_deprecated=True,
    plugin_name=None
)
```

**Parameters:**
- `category`: Filter by category
- `include_hidden`: Include hidden commands
- `include_deprecated`: Include deprecated commands
- `plugin_name`: Filter by plugin name

**Returns:**
- List of CommandMetadata instances (sorted by name)

**Example:**
```python
# List all commands
all_commands = registry.list_commands()

# List backup commands only
backup_commands = registry.list_commands(category=CommandCategory.BACKUP)

# List visible commands only
visible_commands = registry.list_commands(include_hidden=False)

# List plugin commands
plugin_commands = registry.list_commands(plugin_name="my-plugin")
```

#### search_commands()

Search for commands by name, description, aliases, or tags.

```python
results = registry.search_commands(
    query,
    search_aliases=True,
    search_tags=True
)
```

**Parameters:**
- `query`: Search query string
- `search_aliases`: Include aliases in search
- `search_tags`: Include tags in search

**Returns:**
- List of matching CommandMetadata instances

**Example:**
```python
# Search by name
results = registry.search_commands("backup")

# Search by description
results = registry.search_commands("create")

# Search by tag
results = registry.search_commands("snapshot")
```

### Category Operations

#### list_categories()

List all command categories that have registered commands.

```python
categories = registry.list_categories()
```

**Returns:**
- List of CommandCategory enums

#### get_commands_by_category()

Get all commands in a specific category.

```python
commands = registry.get_commands_by_category(category)
```

**Parameters:**
- `category`: CommandCategory enum

**Returns:**
- List of CommandMetadata instances

### Plugin Operations

#### register_plugin()

Register a plugin with the registry.

```python
registry.register_plugin(plugin_metadata)
```

**Parameters:**
- `plugin_metadata`: PluginMetadata instance

**Raises:**
- `PluginValidationError`: If plugin validation fails

**Example:**
```python
from TimeLocker.cli_modules.command_registry import PluginMetadata

plugin = PluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="Author Name",
    description="My custom plugin"
)

registry.register_plugin(plugin)
```

#### unregister_plugin()

Unregister a plugin and all its commands.

```python
registry.unregister_plugin(plugin_name)
```

**Parameters:**
- `plugin_name`: Plugin name

#### get_plugin()

Get plugin metadata.

```python
plugin = registry.get_plugin(plugin_name)
```

**Parameters:**
- `plugin_name`: Plugin name

**Returns:**
- PluginMetadata instance

**Raises:**
- `CommandRegistryError`: If plugin not found

#### list_plugins()

List registered plugins.

```python
plugins = registry.list_plugins(enabled_only=False)
```

**Parameters:**
- `enabled_only`: Only include enabled plugins

**Returns:**
- List of PluginMetadata instances

### Validation

#### validate_command()

Validate command metadata.

```python
errors = registry.validate_command(metadata)
```

**Parameters:**
- `metadata`: CommandMetadata to validate

**Returns:**
- List of validation error messages (empty if valid)

**Example:**
```python
metadata = CommandMetadata(
    name="test-command",
    category=CommandCategory.UTILITY,
    description="Test command",
    app=app
)

errors = registry.validate_command(metadata)
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

### Utility Methods

#### clear()

Clear all registered commands and plugins.

```python
registry.clear()
```

#### get_statistics()

Get registry statistics.

```python
stats = registry.get_statistics()
```

**Returns:**
- Dictionary with statistics:
  - `total_commands`: Total number of commands
  - `total_aliases`: Total number of aliases
  - `total_plugins`: Total number of plugins
  - `categories`: Commands per category
  - `hidden_commands`: Number of hidden commands
  - `deprecated_commands`: Number of deprecated commands
  - `plugin_commands`: Number of plugin commands

**Example:**
```python
stats = registry.get_statistics()
print(f"Total commands: {stats['total_commands']}")
print(f"Total plugins: {stats['total_plugins']}")
print(f"Categories: {stats['categories']}")
```

## Usage Patterns

### Basic Command Registration

```python
import typer
from TimeLocker.cli_modules.command_registry import (
    get_command_registry,
    CommandMetadata,
    CommandCategory,
)

# Get global registry
registry = get_command_registry()

# Create command app
app = typer.Typer(help="Backup operations")

@app.command()
def create(name: str):
    """Create a backup."""
    print(f"Creating backup: {name}")

# Register command
metadata = CommandMetadata(
    name="backup",
    category=CommandCategory.BACKUP,
    description="Backup operations",
    app=app,
    aliases=["bak"]
)

registry.register_command(metadata)
```

### Plugin Development

```python
from TimeLocker.cli_modules.command_registry import (
    get_command_registry,
    CommandMetadata,
    PluginMetadata,
    CommandCategory,
)
import typer

# Register plugin
registry = get_command_registry()

plugin = PluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="Plugin Author",
    description="Custom plugin"
)

registry.register_plugin(plugin)

# Create plugin command
app = typer.Typer(help="Plugin command")

@app.command()
def custom_action():
    """Custom action from plugin."""
    print("Executing custom action")

# Register plugin command
metadata = CommandMetadata(
    name="custom-action",
    category=CommandCategory.PLUGIN,
    description="Custom action from plugin",
    app=app,
    plugin_name="my-plugin"
)

registry.register_command(metadata)
```

### Command Discovery

```python
from TimeLocker.cli_modules.command_registry import get_command_registry

registry = get_command_registry()

# List all backup commands
backup_commands = registry.list_commands(category=CommandCategory.BACKUP)
for cmd in backup_commands:
    print(f"{cmd.name}: {cmd.description}")

# Search for commands
results = registry.search_commands("backup")
for cmd in results:
    print(f"Found: {cmd.name}")

# Get command by alias
metadata = registry.get_command("bak")  # Gets "backup" command
```

### Dynamic Command Loading

```python
from TimeLocker.cli_modules.command_registry import get_command_registry

registry = get_command_registry()

# Discover commands from module
discovered = registry.discover_commands("TimeLocker.cli_modules.commands")

for metadata in discovered:
    print(f"Discovered: {metadata.name}")
    registry.register_command(metadata)
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good: Clear, descriptive name
metadata = CommandMetadata(
    name="backup-create",
    description="Create a new backup"
)

# Avoid: Ambiguous names
metadata = CommandMetadata(
    name="bc",
    description="Create backup"
)
```

### 2. Provide Useful Aliases

```python
# Good: Common abbreviations
metadata = CommandMetadata(
    name="backup-create",
    aliases=["bc", "create-backup"]
)

# Avoid: Too many aliases
metadata = CommandMetadata(
    name="backup-create",
    aliases=["bc", "bak-create", "create-bak", "cb", "backup-c"]
)
```

### 3. Categorize Commands Appropriately

```python
# Good: Correct category
metadata = CommandMetadata(
    name="backup-create",
    category=CommandCategory.BACKUP
)

# Avoid: Wrong category
metadata = CommandMetadata(
    name="backup-create",
    category=CommandCategory.UTILITY
)
```

### 4. Mark Deprecated Commands

```python
metadata = CommandMetadata(
    name="old-backup",
    category=CommandCategory.BACKUP,
    description="Old backup command",
    app=app,
    deprecated=True,
    deprecation_message="Use 'backup-create' instead"
)
```

### 5. Use Tags for Better Discovery

```python
metadata = CommandMetadata(
    name="backup-create",
    category=CommandCategory.BACKUP,
    description="Create a new backup",
    app=app,
    tags={"backup", "create", "snapshot", "incremental"}
)
```

## Error Handling

### CommandAlreadyRegisteredError

Raised when attempting to register a command that already exists.

```python
try:
    registry.register_command(metadata)
except CommandAlreadyRegisteredError as e:
    print(f"Command already registered: {e}")
    # Use allow_override=True to replace
    registry.register_command(metadata, allow_override=True)
```

### CommandNotFoundError

Raised when attempting to access a command that doesn't exist.

```python
try:
    metadata = registry.get_command("nonexistent")
except CommandNotFoundError as e:
    print(f"Command not found: {e}")
```

### PluginValidationError

Raised when plugin validation fails.

```python
try:
    registry.register_plugin(plugin)
except PluginValidationError as e:
    print(f"Plugin validation failed: {e}")
```

## Testing

### Unit Testing

```python
import pytest
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
)

def test_register_command():
    registry = CommandRegistry()
    app = typer.Typer()
    
    metadata = CommandMetadata(
        name="test",
        category=CommandCategory.UTILITY,
        description="Test command",
        app=app
    )
    
    registry.register_command(metadata)
    assert registry.has_command("test")

def test_command_aliases():
    registry = CommandRegistry()
    app = typer.Typer()
    
    metadata = CommandMetadata(
        name="backup",
        category=CommandCategory.BACKUP,
        description="Backup",
        app=app,
        aliases=["bak"]
    )
    
    registry.register_command(metadata)
    assert registry.has_command("backup")
    assert registry.has_command("bak")
    
    # Both should return same metadata
    assert registry.get_command("backup") == registry.get_command("bak")
```

## See Also

- [ValidationFramework Documentation](validation-framework.md)
- [ErrorContext Documentation](error-context-usage.md)
- [CLI Architecture](../2-architecture/system-architecture.md)
