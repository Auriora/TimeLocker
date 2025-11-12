"""
Command Registry for centralized command metadata management.

This module provides a registry system for CLI commands, enabling:
- Command registration and discovery
- Command metadata management
- Plugin foundation for third-party extensions
- Command validation and conflict detection
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from pathlib import Path
from enum import Enum
import inspect

import typer

logger = logging.getLogger(__name__)


class CommandCategory(str, Enum):
    """Categories for organizing commands."""
    BACKUP = "backup"
    RESTORE = "restore"
    REPOSITORY = "repository"
    SNAPSHOT = "snapshot"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    MONITORING = "monitoring"
    SCHEDULING = "scheduling"
    POLICY = "policy"
    SELECTION = "selection"
    UTILITY = "utility"
    PLUGIN = "plugin"


@dataclass
class CommandMetadata:
    """
    Metadata for a registered command.
    
    Attributes:
        name: Command name (e.g., "backup", "restore")
        category: Command category for organization
        description: Short description of the command
        app: Typer app instance for the command
        callback: Optional command callback function
        aliases: Alternative names for the command
        hidden: Whether the command should be hidden from help
        deprecated: Whether the command is deprecated
        deprecation_message: Message to show for deprecated commands
        requires_config: Whether the command requires configuration
        requires_repository: Whether the command requires a repository
        plugin_name: Name of the plugin providing this command (if any)
        version: Version of the command (for plugins)
        tags: Additional tags for filtering/searching
    """
    name: str
    category: CommandCategory
    description: str
    app: typer.Typer
    callback: Optional[Callable] = None
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    requires_config: bool = True
    requires_repository: bool = False
    plugin_name: Optional[str] = None
    version: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """Validate metadata after initialization."""
        if not self.name:
            raise ValueError("Command name cannot be empty")
        if not self.description:
            raise ValueError("Command description cannot be empty")
        if not isinstance(self.app, typer.Typer):
            raise ValueError("Command app must be a Typer instance")


@dataclass
class PluginMetadata:
    """
    Metadata for a registered plugin.
    
    Attributes:
        name: Plugin name
        version: Plugin version
        author: Plugin author
        description: Plugin description
        commands: List of command names provided by this plugin
        enabled: Whether the plugin is enabled
        path: Path to the plugin module
    """
    name: str
    version: str
    author: str
    description: str
    commands: List[str] = field(default_factory=list)
    enabled: bool = True
    path: Optional[Path] = None


class CommandRegistryError(Exception):
    """Base exception for command registry errors."""
    pass


class CommandAlreadyRegisteredError(CommandRegistryError):
    """Raised when attempting to register a command that already exists."""
    pass


class CommandNotFoundError(CommandRegistryError):
    """Raised when attempting to access a command that doesn't exist."""
    pass


class PluginValidationError(CommandRegistryError):
    """Raised when plugin validation fails."""
    pass


class CommandRegistry:
    """
    Registry for managing CLI commands and plugins.
    
    This class provides centralized command management, enabling:
    - Dynamic command registration
    - Command metadata management
    - Plugin support for third-party extensions
    - Command discovery and validation
    
    Example:
        >>> registry = CommandRegistry()
        >>> metadata = CommandMetadata(
        ...     name="backup",
        ...     category=CommandCategory.BACKUP,
        ...     description="Backup operations",
        ...     app=backup_app
        ... )
        >>> registry.register_command(metadata)
        >>> commands = registry.list_commands()
    """
    
    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, CommandMetadata] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command_name
        self._plugins: Dict[str, PluginMetadata] = {}
        self._categories: Dict[CommandCategory, List[str]] = {
            category: [] for category in CommandCategory
        }
        logger.debug("CommandRegistry initialized")
    
    def register_command(
        self,
        metadata: CommandMetadata,
        allow_override: bool = False
    ) -> None:
        """
        Register a command with the registry.
        
        Args:
            metadata: Command metadata
            allow_override: Whether to allow overriding existing commands
            
        Raises:
            CommandAlreadyRegisteredError: If command already exists and override not allowed
            ValueError: If metadata is invalid
        """
        # Validate command name
        if not metadata.name:
            raise ValueError("Command name cannot be empty")
        
        # Check for existing command
        if metadata.name in self._commands and not allow_override:
            raise CommandAlreadyRegisteredError(
                f"Command '{metadata.name}' is already registered"
            )
        
        # Check for alias conflicts
        for alias in metadata.aliases:
            if alias in self._aliases and not allow_override:
                existing_cmd = self._aliases[alias]
                raise CommandAlreadyRegisteredError(
                    f"Alias '{alias}' is already used by command '{existing_cmd}'"
                )
        
        # Register the command
        self._commands[metadata.name] = metadata
        
        # Register aliases
        for alias in metadata.aliases:
            self._aliases[alias] = metadata.name
        
        # Add to category
        if metadata.name not in self._categories[metadata.category]:
            self._categories[metadata.category].append(metadata.name)
        
        logger.info(
            f"Registered command '{metadata.name}' "
            f"(category: {metadata.category.value}, "
            f"aliases: {metadata.aliases})"
        )
    
    def unregister_command(self, name: str) -> None:
        """
        Unregister a command from the registry.
        
        Args:
            name: Command name to unregister
            
        Raises:
            CommandNotFoundError: If command doesn't exist
        """
        if name not in self._commands:
            raise CommandNotFoundError(f"Command '{name}' not found")
        
        metadata = self._commands[name]
        
        # Remove aliases
        for alias in metadata.aliases:
            self._aliases.pop(alias, None)
        
        # Remove from category
        if name in self._categories[metadata.category]:
            self._categories[metadata.category].remove(name)
        
        # Remove command
        del self._commands[name]
        
        logger.info(f"Unregistered command '{name}'")
    
    def get_command(self, name: str) -> CommandMetadata:
        """
        Get command metadata by name or alias.
        
        Args:
            name: Command name or alias
            
        Returns:
            Command metadata
            
        Raises:
            CommandNotFoundError: If command doesn't exist
        """
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        
        if name not in self._commands:
            raise CommandNotFoundError(f"Command '{name}' not found")
        
        return self._commands[name]
    
    def has_command(self, name: str) -> bool:
        """
        Check if a command exists.
        
        Args:
            name: Command name or alias
            
        Returns:
            True if command exists, False otherwise
        """
        return name in self._commands or name in self._aliases
    
    def list_commands(
        self,
        category: Optional[CommandCategory] = None,
        include_hidden: bool = False,
        include_deprecated: bool = True,
        plugin_name: Optional[str] = None
    ) -> List[CommandMetadata]:
        """
        List registered commands with optional filtering.
        
        Args:
            category: Filter by category
            include_hidden: Include hidden commands
            include_deprecated: Include deprecated commands
            plugin_name: Filter by plugin name
            
        Returns:
            List of command metadata
        """
        commands = list(self._commands.values())
        
        # Filter by category
        if category is not None:
            commands = [cmd for cmd in commands if cmd.category == category]
        
        # Filter hidden commands
        if not include_hidden:
            commands = [cmd for cmd in commands if not cmd.hidden]
        
        # Filter deprecated commands
        if not include_deprecated:
            commands = [cmd for cmd in commands if not cmd.deprecated]
        
        # Filter by plugin
        if plugin_name is not None:
            commands = [cmd for cmd in commands if cmd.plugin_name == plugin_name]
        
        return sorted(commands, key=lambda c: c.name)
    
    def list_categories(self) -> List[CommandCategory]:
        """
        List all command categories that have registered commands.
        
        Returns:
            List of categories with commands
        """
        return [
            category for category, commands in self._categories.items()
            if commands
        ]
    
    def get_commands_by_category(
        self,
        category: CommandCategory
    ) -> List[CommandMetadata]:
        """
        Get all commands in a specific category.
        
        Args:
            category: Command category
            
        Returns:
            List of command metadata
        """
        return self.list_commands(category=category)
    
    def search_commands(
        self,
        query: str,
        search_aliases: bool = True,
        search_tags: bool = True
    ) -> List[CommandMetadata]:
        """
        Search for commands by name, description, aliases, or tags.
        
        Args:
            query: Search query
            search_aliases: Include aliases in search
            search_tags: Include tags in search
            
        Returns:
            List of matching command metadata
        """
        query_lower = query.lower()
        results = []
        
        for metadata in self._commands.values():
            # Search in name
            if query_lower in metadata.name.lower():
                results.append(metadata)
                continue
            
            # Search in description
            if query_lower in metadata.description.lower():
                results.append(metadata)
                continue
            
            # Search in aliases
            if search_aliases:
                if any(query_lower in alias.lower() for alias in metadata.aliases):
                    results.append(metadata)
                    continue
            
            # Search in tags
            if search_tags:
                if any(query_lower in tag.lower() for tag in metadata.tags):
                    results.append(metadata)
                    continue
        
        return sorted(results, key=lambda c: c.name)
    
    def register_plugin(self, plugin_metadata: PluginMetadata) -> None:
        """
        Register a plugin with the registry.
        
        Args:
            plugin_metadata: Plugin metadata
            
        Raises:
            PluginValidationError: If plugin validation fails
        """
        if not plugin_metadata.name:
            raise PluginValidationError("Plugin name cannot be empty")
        
        if plugin_metadata.name in self._plugins:
            logger.warning(f"Plugin '{plugin_metadata.name}' is already registered")
        
        self._plugins[plugin_metadata.name] = plugin_metadata
        logger.info(
            f"Registered plugin '{plugin_metadata.name}' "
            f"(version: {plugin_metadata.version}, "
            f"commands: {len(plugin_metadata.commands)})"
        )
    
    def unregister_plugin(self, plugin_name: str) -> None:
        """
        Unregister a plugin and all its commands.
        
        Args:
            plugin_name: Plugin name
        """
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' not found")
            return
        
        # Unregister all commands from this plugin
        plugin_commands = [
            name for name, metadata in self._commands.items()
            if metadata.plugin_name == plugin_name
        ]
        
        for cmd_name in plugin_commands:
            try:
                self.unregister_command(cmd_name)
            except CommandNotFoundError:
                pass
        
        # Remove plugin
        del self._plugins[plugin_name]
        logger.info(f"Unregistered plugin '{plugin_name}'")
    
    def get_plugin(self, plugin_name: str) -> PluginMetadata:
        """
        Get plugin metadata.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin metadata
            
        Raises:
            CommandRegistryError: If plugin not found
        """
        if plugin_name not in self._plugins:
            raise CommandRegistryError(f"Plugin '{plugin_name}' not found")
        
        return self._plugins[plugin_name]
    
    def list_plugins(self, enabled_only: bool = False) -> List[PluginMetadata]:
        """
        List registered plugins.
        
        Args:
            enabled_only: Only include enabled plugins
            
        Returns:
            List of plugin metadata
        """
        plugins = list(self._plugins.values())
        
        if enabled_only:
            plugins = [p for p in plugins if p.enabled]
        
        return sorted(plugins, key=lambda p: p.name)
    
    def validate_command(self, metadata: CommandMetadata) -> List[str]:
        """
        Validate command metadata.
        
        Args:
            metadata: Command metadata to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not metadata.name:
            errors.append("Command name is required")
        
        if not metadata.description:
            errors.append("Command description is required")
        
        if not isinstance(metadata.app, typer.Typer):
            errors.append("Command app must be a Typer instance")
        
        # Check for conflicts
        if metadata.name in self._commands:
            errors.append(f"Command '{metadata.name}' already exists")
        
        for alias in metadata.aliases:
            if alias in self._aliases:
                existing = self._aliases[alias]
                errors.append(
                    f"Alias '{alias}' conflicts with command '{existing}'"
                )
        
        # Validate deprecation
        if metadata.deprecated and not metadata.deprecation_message:
            errors.append("Deprecated commands must have a deprecation message")
        
        return errors
    
    def discover_commands(self, module_path: str) -> List[CommandMetadata]:
        """
        Discover commands from a module.
        
        This method scans a module for Typer apps and creates command metadata.
        
        Args:
            module_path: Python module path (e.g., "TimeLocker.cli_modules.commands")
            
        Returns:
            List of discovered command metadata
            
        Note:
            This is a basic implementation. More sophisticated discovery
            can be added based on specific needs.
        """
        discovered = []
        
        try:
            import importlib
            module = importlib.import_module(module_path)
            
            # Look for Typer apps in the module
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, typer.Typer):
                    # Create basic metadata
                    metadata = CommandMetadata(
                        name=name.replace("_app", "").replace("_", "-"),
                        category=CommandCategory.UTILITY,
                        description=obj.info.help or "No description",
                        app=obj
                    )
                    discovered.append(metadata)
                    logger.debug(f"Discovered command '{metadata.name}' in {module_path}")
        
        except Exception as e:
            logger.error(f"Error discovering commands from {module_path}: {e}")
        
        return discovered
    
    def clear(self) -> None:
        """Clear all registered commands and plugins."""
        self._commands.clear()
        self._aliases.clear()
        self._plugins.clear()
        for category in self._categories:
            self._categories[category].clear()
        logger.info("Command registry cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_commands": len(self._commands),
            "total_aliases": len(self._aliases),
            "total_plugins": len(self._plugins),
            "categories": {
                category.value: len(commands)
                for category, commands in self._categories.items()
                if commands
            },
            "hidden_commands": sum(
                1 for cmd in self._commands.values() if cmd.hidden
            ),
            "deprecated_commands": sum(
                1 for cmd in self._commands.values() if cmd.deprecated
            ),
            "plugin_commands": sum(
                1 for cmd in self._commands.values() if cmd.plugin_name
            )
        }


# Global registry instance
_global_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """
    Get the global command registry instance.
    
    Returns:
        Global CommandRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandRegistry()
    return _global_registry


def reset_command_registry() -> None:
    """Reset the global command registry (primarily for testing)."""
    global _global_registry
    _global_registry = None


__all__ = [
    "CommandRegistry",
    "CommandMetadata",
    "PluginMetadata",
    "CommandCategory",
    "CommandRegistryError",
    "CommandAlreadyRegisteredError",
    "CommandNotFoundError",
    "PluginValidationError",
    "get_command_registry",
    "reset_command_registry",
]
