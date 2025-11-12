"""
Integration module for CommandRegistry with the CLI.

This module provides utilities to register commands with the CommandRegistry
and integrate it with the main Typer application.
"""

import logging
from pathlib import Path
from typing import Optional, List
import importlib.util

import typer

from .command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
    get_command_registry,
)

logger = logging.getLogger(__name__)


def register_core_commands(registry: Optional[CommandRegistry] = None) -> None:
    """
    Register all core TimeLocker commands with the registry.
    
    This function discovers and registers all built-in commands from the
    cli_modules.commands package.
    
    Args:
        registry: Optional registry instance (uses global if not provided)
    """
    if registry is None:
        registry = get_command_registry()
    
    # Import command modules
    try:
        from .commands import (
            backup_app,
            repos_app,
            snapshots_app,
            credentials_app,
            security_app,
            config_app,
        )
        
        # Register backup commands
        registry.register_command(
            CommandMetadata(
                name="backup",
                category=CommandCategory.BACKUP,
                description="Backup operations and management",
                app=backup_app,
                requires_config=True,
                tags={"core", "backup"}
            ),
            allow_override=True
        )
        
        # Register repository commands
        registry.register_command(
            CommandMetadata(
                name="repos",
                category=CommandCategory.REPOSITORY,
                description="Repository management commands",
                app=repos_app,
                aliases=["repositories"],
                requires_config=True,
                tags={"core", "repository"}
            ),
            allow_override=True
        )
        
        # Register snapshot commands
        registry.register_command(
            CommandMetadata(
                name="snapshots",
                category=CommandCategory.SNAPSHOT,
                description="Snapshot browsing and management",
                app=snapshots_app,
                requires_config=True,
                requires_repository=True,
                tags={"core", "snapshot"}
            ),
            allow_override=True
        )
        
        # Register credentials commands
        registry.register_command(
            CommandMetadata(
                name="credentials",
                category=CommandCategory.SECURITY,
                description="Credential management commands",
                app=credentials_app,
                requires_config=True,
                tags={"core", "security", "credentials"}
            ),
            allow_override=True
        )
        
        # Register security commands
        registry.register_command(
            CommandMetadata(
                name="security",
                category=CommandCategory.SECURITY,
                description="Security management commands",
                app=security_app,
                requires_config=True,
                tags={"core", "security"}
            ),
            allow_override=True
        )
        
        # Register config commands
        registry.register_command(
            CommandMetadata(
                name="config",
                category=CommandCategory.CONFIGURATION,
                description="Configuration management commands",
                app=config_app,
                requires_config=False,  # Config commands can work without existing config
                tags={"core", "configuration"}
            ),
            allow_override=True
        )
        
        logger.info("Registered core commands with CommandRegistry")
        
    except ImportError as e:
        logger.error(f"Failed to import core commands: {e}")


def register_optional_commands(registry: Optional[CommandRegistry] = None) -> None:
    """
    Register optional TimeLocker commands with the registry.
    
    This function attempts to import and register optional command modules
    that may not be available in all installations.
    
    Args:
        registry: Optional registry instance (uses global if not provided)
    """
    if registry is None:
        registry = get_command_registry()
    
    # Try to register policy commands
    try:
        from .commands.policy import policy_app
        
        registry.register_command(
            CommandMetadata(
                name="policy",
                category=CommandCategory.POLICY,
                description="Policy management commands",
                app=policy_app,
                requires_config=True,
                tags={"optional", "policy"}
            ),
            allow_override=True
        )
        logger.debug("Registered policy commands")
    except ImportError as e:
        logger.debug(f"Policy commands not available: {e}")
    
    # Try to register selections commands
    try:
        from .commands.selections import selections_app
        
        registry.register_command(
            CommandMetadata(
                name="selections",
                category=CommandCategory.SELECTION,
                description="File selection management commands",
                app=selections_app,
                requires_config=True,
                tags={"optional", "selection"}
            ),
            allow_override=True
        )
        logger.debug("Registered selections commands")
    except ImportError as e:
        logger.debug(f"Selections commands not available: {e}")
    
    # Try to register schedule commands
    try:
        from .commands.schedule import schedule_app
        
        registry.register_command(
            CommandMetadata(
                name="schedule",
                category=CommandCategory.SCHEDULING,
                description="Backup scheduling commands",
                app=schedule_app,
                requires_config=True,
                tags={"optional", "scheduling"}
            ),
            allow_override=True
        )
        logger.debug("Registered schedule commands")
    except ImportError as e:
        logger.debug(f"Schedule commands not available: {e}")
    
    # Try to register monitoring commands
    try:
        from .commands.monitoring import monitor_app, logs_app, reports_app
        
        registry.register_command(
            CommandMetadata(
                name="monitor",
                category=CommandCategory.MONITORING,
                description="Monitoring and status commands",
                app=monitor_app,
                requires_config=True,
                tags={"optional", "monitoring"}
            ),
            allow_override=True
        )
        
        registry.register_command(
            CommandMetadata(
                name="logs",
                category=CommandCategory.MONITORING,
                description="Log viewing commands",
                app=logs_app,
                requires_config=True,
                tags={"optional", "monitoring", "logs"}
            ),
            allow_override=True
        )
        
        registry.register_command(
            CommandMetadata(
                name="reports",
                category=CommandCategory.MONITORING,
                description="Report generation commands",
                app=reports_app,
                requires_config=True,
                tags={"optional", "monitoring", "reports"}
            ),
            allow_override=True
        )
        logger.debug("Registered monitoring commands")
    except ImportError as e:
        logger.debug(f"Monitoring commands not available: {e}")
    
    # Try to register restore commands
    try:
        from .commands.restore import restore_app
        
        registry.register_command(
            CommandMetadata(
                name="restore",
                category=CommandCategory.RESTORE,
                description="Restore operations and management",
                app=restore_app,
                requires_config=True,
                requires_repository=True,
                tags={"optional", "restore"}
            ),
            allow_override=True
        )
        logger.debug("Registered restore commands")
    except ImportError as e:
        logger.debug(f"Restore commands not available: {e}")


def register_all_commands(registry: Optional[CommandRegistry] = None) -> None:
    """
    Register all available commands with the registry.
    
    This is a convenience function that registers both core and optional commands.
    
    Args:
        registry: Optional registry instance (uses global if not provided)
    """
    if registry is None:
        registry = get_command_registry()
    
    register_core_commands(registry)
    register_optional_commands(registry)
    
    stats = registry.get_statistics()
    logger.info(
        f"CommandRegistry initialized with {stats['total_commands']} commands "
        f"across {len(stats['categories'])} categories"
    )


def add_commands_to_app(
    app: typer.Typer,
    registry: Optional[CommandRegistry] = None,
    include_hidden: bool = False
) -> None:
    """
    Add registered commands to a Typer application.
    
    This function takes commands from the registry and adds them to the
    provided Typer app instance.
    
    Args:
        app: Typer application to add commands to
        registry: Optional registry instance (uses global if not provided)
        include_hidden: Whether to include hidden commands
    """
    if registry is None:
        registry = get_command_registry()
    
    commands = registry.list_commands(include_hidden=include_hidden)
    
    for metadata in commands:
        try:
            app.add_typer(metadata.app, name=metadata.name)
            logger.debug(f"Added command '{metadata.name}' to app")
        except Exception as e:
            logger.error(f"Failed to add command '{metadata.name}': {e}")


def discover_plugin_commands(
    plugin_dir: Path,
    registry: Optional[CommandRegistry] = None
) -> List[CommandMetadata]:
    """
    Discover and register commands from a plugin directory.
    
    This function scans a directory for Python modules that define Typer apps
    and registers them as plugin commands.
    
    Args:
        plugin_dir: Directory containing plugin modules
        registry: Optional registry instance (uses global if not provided)
        
    Returns:
        List of discovered command metadata
    """
    if registry is None:
        registry = get_command_registry()
    
    discovered = []
    
    if not plugin_dir.exists() or not plugin_dir.is_dir():
        logger.warning(f"Plugin directory does not exist: {plugin_dir}")
        return discovered
    
    # Scan for Python files
    for plugin_file in plugin_dir.glob("*.py"):
        if plugin_file.name.startswith("_"):
            continue
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"plugin.{plugin_file.stem}",
                plugin_file
            )
            if spec is None or spec.loader is None:
                continue
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for Typer apps
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                
                attr = getattr(module, attr_name)
                if isinstance(attr, typer.Typer):
                    # Create metadata for the plugin command
                    command_name = attr_name.replace("_app", "").replace("_", "-")
                    
                    metadata = CommandMetadata(
                        name=command_name,
                        category=CommandCategory.PLUGIN,
                        description=attr.info.help or f"Plugin command: {command_name}",
                        app=attr,
                        plugin_name=plugin_file.stem,
                        tags={"plugin"}
                    )
                    
                    registry.register_command(metadata, allow_override=True)
                    discovered.append(metadata)
                    
                    logger.info(
                        f"Discovered plugin command '{command_name}' "
                        f"from {plugin_file.name}"
                    )
        
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_file}: {e}")
    
    return discovered


def validate_registry(registry: Optional[CommandRegistry] = None) -> List[str]:
    """
    Validate the command registry for common issues.
    
    Args:
        registry: Optional registry instance (uses global if not provided)
        
    Returns:
        List of validation warnings/errors
    """
    if registry is None:
        registry = get_command_registry()
    
    issues = []
    
    # Check for commands without descriptions
    for metadata in registry.list_commands():
        if not metadata.description or metadata.description == "No description":
            issues.append(f"Command '{metadata.name}' has no description")
    
    # Check for deprecated commands
    deprecated = registry.list_commands(include_deprecated=True)
    deprecated = [cmd for cmd in deprecated if cmd.deprecated]
    if deprecated:
        issues.append(
            f"Found {len(deprecated)} deprecated commands: "
            f"{', '.join(cmd.name for cmd in deprecated)}"
        )
    
    # Check for hidden commands
    hidden = registry.list_commands(include_hidden=True)
    hidden = [cmd for cmd in hidden if cmd.hidden]
    if hidden:
        logger.debug(
            f"Found {len(hidden)} hidden commands: "
            f"{', '.join(cmd.name for cmd in hidden)}"
        )
    
    return issues


__all__ = [
    "register_core_commands",
    "register_optional_commands",
    "register_all_commands",
    "add_commands_to_app",
    "discover_plugin_commands",
    "validate_registry",
]
