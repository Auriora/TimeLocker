# CommandRegistry Documentation

## Overview

The CommandRegistry provides centralized command metadata management for the TimeLocker CLI. It enables:

- Dynamic command registration and discovery
- Command metadata management (categories, aliases, tags)
- Plugin foundation for third-party extensions
- Command validation and conflict detection

## Architecture

```
┌─────────────────────────────────────────┐
│         CommandRegistry                  │
│  - Command metadata storage              │
│  - Alias resolution                      │
│  - Category management                   │
│  - Plugin support                        │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      Registry Integration                │
│  - Core command registration             │
│  - Optional command registration         │
│  - Plugin discovery                      │
│  - Typer app integration                 │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         CLI Commands                     │
│  - backup, restore, repos, etc.          │
│  - Plugin commands                       │
└─────────────────────────────────────────┘
```

## Core Components

### CommandRegistry

The main registry class that manages command metadata.

**Key Features:**
- Command registration with metadata
- Alias management
- Category-based organization
- Search and filtering
- Plugin support
- Validation

**Example:**
```python
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
)

# Create registry
registry = CommandRegistry()

# Register a command
metadata = CommandMetadata(
    name="backup",
    category=CommandCategory.BACKUP,
    description="Backup operations",
    app=backup_app,
    aliases=["bak"],
    tags={"core", "backup"}
)
registry.register_command(metadata)

# Get command
cmd = registry.get_command("backup")
# Also works with alias
cmd = registry.get_command("bak")

# List commands
all_commands = registry.list_commands()
backup_commands = registry.list_commands(category=CommandCategory.BACKUP)

# Search commands
results = registry.search_commands("backup")
```

### CommandMetadata

Dataclass containing command metadata.

**Fields:**
- `name`: Command name (required)
- `category`: Command category (required)
- `description`: Short description (required)
- `app`: Typer app instance (required)
- `callback`: Optional command callback
- `aliases`: Alternative names
- `hidden`: Whether hidden from help
- `deprecated`: Whether deprecated
- `deprecation_message`: Message for deprecated commands
- `requires_config`: Whether requires configuration
- `requires_repository`: Whether requires repository
- `plugin_name`: Plugin providing this command
- `version`: Command version
- `tags`: Additional tags for filtering

### CommandCategory

Enum defining command categories:

- `BACKUP`: Backup operations
- `RESTORE`: Restore operations
- `REPOSITORY`: Repository management
- `SNAPSHOT`: Snapshot operations
- `CONFIGURATION`: Configuration management
- `SECURITY`: Security operations
- `MONITORING`: Monitoring and reporting
- `SCHEDULING`: Scheduling operations
- `POLICY`: Policy management
- `SELECTION`: File selection management
- `UTILITY`: Utility commands
- `PLUGIN`: Plugin commands

## Integration

### Registering Core Commands

```python
from TimeLocker.cli_modules.registry_integration import register_core_commands

# Register all core commands
register_core_commands()
```

### Registering Optional Commands

```python
from TimeLocker.cli_modules.registry_integration import register_optional_commands

# Register optional commands (policy, selections, schedule, etc.)
register_optional_commands()
```

### Registering All Commands

```python
from TimeLocker.cli_modules.registry_integration import register_all_commands

# Register both core and optional commands
register_all_commands()
```

### Adding Commands to Typer App

```python
from TimeLocker.cli_modules.registry_integration import add_commands_to_app
import typer

# Create main app
app = typer.Typer()

# Add all registered commands
add_commands_to_app(app)
```

## Plugin Support

### Creating a Plugin Command

```python
import typer
from TimeLocker.cli_modules.command_registry import (
    CommandMetadata,
    CommandCategory,
    get_command_registry,
)

# Create plugin command
plugin_app = typer.Typer(help="My plugin command")

@plugin_app.command()
def hello():
    """Say hello."""
    print("Hello from plugin!")

# Register with registry
registry = get_command_registry()
metadata = CommandMetadata(
    name="myplugin",
    category=CommandCategory.PLUGIN,
    description="My custom plugin",
    app=plugin_app,
    plugin_name="my-plugin",
    version="1.0.0",
    tags={"plugin", "custom"}
)
registry.register_command(metadata)
```

### Discovering Plugin Commands

```python
from pathlib import Path
from TimeLocker.cli_modules.registry_integration import discover_plugin_commands

# Discover plugins from directory
plugin_dir = Path("~/.timelocker/plugins").expanduser()
discovered = discover_plugin_commands(plugin_dir)

print(f"Discovered {len(discovered)} plugin commands")
```

### Plugin Metadata

```python
from TimeLocker.cli_modules.command_registry import PluginMetadata

# Create plugin metadata
plugin = PluginMetadata(
    name="my-plugin",
    version="1.0.0",
    author="John Doe",
    description="My custom plugin",
    commands=["myplugin"],
    enabled=True
)

# Register plugin
registry.register_plugin(plugin)

# List plugins
plugins = registry.list_plugins()
enabled_plugins = registry.list_plugins(enabled_only=True)
```

## Command Discovery

### Searching Commands

```python
# Search by name
results = registry.search_commands("backup")

# Search in descriptions
results = registry.search_commands("repository")

# Search in aliases
results = registry.search_commands("bak")

# Search in tags
results = registry.search_commands("core")
```

### Filtering Commands

```python
# Get commands by category
backup_commands = registry.list_commands(category=CommandCategory.BACKUP)

# Include hidden commands
all_commands = registry.list_commands(include_hidden=True)

# Exclude deprecated commands
current_commands = registry.list_commands(include_deprecated=False)

# Get plugin commands
plugin_commands = registry.list_commands(plugin_name="my-plugin")
```

## Validation

### Validating Commands

```python
# Validate command metadata before registration
errors = registry.validate_command(metadata)
if errors:
    print(f"Validation errors: {errors}")
else:
    registry.register_command(metadata)
```

### Validating Registry

```python
from TimeLocker.cli_modules.registry_integration import validate_registry

# Validate entire registry
issues = validate_registry()
if issues:
    print("Registry issues:")
    for issue in issues:
        print(f"  - {issue}")
```

## Statistics

```python
# Get registry statistics
stats = registry.get_statistics()

print(f"Total commands: {stats['total_commands']}")
print(f"Total aliases: {stats['total_aliases']}")
print(f"Total plugins: {stats['total_plugins']}")
print(f"Categories: {stats['categories']}")
print(f"Hidden commands: {stats['hidden_commands']}")
print(f"Deprecated commands: {stats['deprecated_commands']}")
print(f"Plugin commands: {stats['plugin_commands']}")
```

## Global Registry

The module provides a global registry instance for convenience:

```python
from TimeLocker.cli_modules.command_registry import get_command_registry

# Get global registry
registry = get_command_registry()

# Use registry
registry.register_command(metadata)
```

For testing, you can reset the global registry:

```python
from TimeLocker.cli_modules.command_registry import reset_command_registry

# Reset global registry
reset_command_registry()
```

## Error Handling

The registry defines several exception types:

- `CommandRegistryError`: Base exception
- `CommandAlreadyRegisteredError`: Command already exists
- `CommandNotFoundError`: Command not found
- `PluginValidationError`: Plugin validation failed

```python
from TimeLocker.cli_modules.command_registry import (
    CommandAlreadyRegisteredError,
    CommandNotFoundError,
)

try:
    registry.register_command(metadata)
except CommandAlreadyRegisteredError:
    print("Command already registered")

try:
    cmd = registry.get_command("nonexistent")
except CommandNotFoundError:
    print("Command not found")
```

## Best Practices

1. **Use Categories**: Organize commands by category for better discoverability
2. **Add Aliases**: Provide convenient aliases for frequently used commands
3. **Tag Commands**: Use tags for flexible filtering and searching
4. **Validate Metadata**: Always validate command metadata before registration
5. **Document Commands**: Provide clear descriptions for all commands
6. **Handle Deprecation**: Mark deprecated commands and provide migration messages
7. **Plugin Isolation**: Keep plugin commands separate from core commands
8. **Test Registration**: Test command registration in your test suite

## Migration Guide

### From Direct Typer Registration

**Before:**
```python
app = typer.Typer()
app.add_typer(backup_app, name="backup")
app.add_typer(restore_app, name="restore")
```

**After:**
```python
from TimeLocker.cli_modules.registry_integration import (
    register_all_commands,
    add_commands_to_app,
)

app = typer.Typer()
register_all_commands()
add_commands_to_app(app)
```

### Benefits

- Centralized command management
- Better command discovery
- Plugin support
- Metadata-driven architecture
- Easier testing and validation

## Future Enhancements

Potential future enhancements to the CommandRegistry:

1. **Dynamic Loading**: Load commands on-demand
2. **Command Dependencies**: Define dependencies between commands
3. **Permission System**: Role-based command access
4. **Command Versioning**: Support multiple versions of commands
5. **Command Hooks**: Pre/post execution hooks
6. **Command Metrics**: Track command usage statistics
7. **Command Documentation**: Auto-generate documentation from metadata
8. **Command Testing**: Built-in command testing utilities

## See Also

- [CLI consolidation requirements](../../../docs/specs/001-cli-consolidation-stabilization/requirements.md)
- [CLI consolidation tasks](../../../docs/specs/001-cli-consolidation-stabilization/tasks.md)
- [CLI command hierarchy](../../../docs/reference/timelocker-cli-command-hierarchy.md)
