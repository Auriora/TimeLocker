"""
Tests for CommandRegistry.

This module tests the command registry functionality including:
- Command registration and discovery
- Command metadata management
- Plugin support
- Command validation
"""

import pytest
from pathlib import Path
from typing import List

import typer

from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    PluginMetadata,
    CommandCategory,
    CommandRegistryError,
    CommandAlreadyRegisteredError,
    CommandNotFoundError,
    PluginValidationError,
    get_command_registry,
    reset_command_registry,
)


@pytest.fixture
def registry():
    """Create a fresh command registry for each test."""
    return CommandRegistry()


@pytest.fixture
def sample_app():
    """Create a sample Typer app for testing."""
    app = typer.Typer(help="Sample command")
    
    @app.command()
    def test_command():
        """Test command."""
        pass
    
    return app


@pytest.fixture
def sample_metadata(sample_app):
    """Create sample command metadata."""
    return CommandMetadata(
        name="test-command",
        category=CommandCategory.UTILITY,
        description="Test command for testing",
        app=sample_app,
        aliases=["tc", "test"],
        tags={"test", "sample"}
    )


class TestCommandMetadata:
    """Tests for CommandMetadata."""
    
    def test_create_metadata(self, sample_app):
        """Test creating command metadata."""
        metadata = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup operations",
            app=sample_app
        )
        
        assert metadata.name == "backup"
        assert metadata.category == CommandCategory.BACKUP
        assert metadata.description == "Backup operations"
        assert metadata.app == sample_app
        assert metadata.aliases == []
        assert not metadata.hidden
        assert not metadata.deprecated
    
    def test_metadata_with_aliases(self, sample_app):
        """Test metadata with aliases."""
        metadata = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup operations",
            app=sample_app,
            aliases=["bak", "b"]
        )
        
        assert metadata.aliases == ["bak", "b"]
    
    def test_metadata_validation_empty_name(self, sample_app):
        """Test that empty name raises error."""
        with pytest.raises(ValueError, match="Command name cannot be empty"):
            CommandMetadata(
                name="",
                category=CommandCategory.BACKUP,
                description="Test",
                app=sample_app
            )
    
    def test_metadata_validation_empty_description(self, sample_app):
        """Test that empty description raises error."""
        with pytest.raises(ValueError, match="Command description cannot be empty"):
            CommandMetadata(
                name="test",
                category=CommandCategory.BACKUP,
                description="",
                app=sample_app
            )
    
    def test_metadata_validation_invalid_app(self):
        """Test that invalid app raises error."""
        with pytest.raises(ValueError, match="Command app must be a Typer instance"):
            CommandMetadata(
                name="test",
                category=CommandCategory.BACKUP,
                description="Test",
                app="not a typer app"
            )


class TestCommandRegistry:
    """Tests for CommandRegistry."""
    
    def test_create_registry(self):
        """Test creating a command registry."""
        registry = CommandRegistry()
        assert registry is not None
        assert len(registry.list_commands()) == 0
    
    def test_register_command(self, registry, sample_metadata):
        """Test registering a command."""
        registry.register_command(sample_metadata)
        
        assert registry.has_command("test-command")
        assert len(registry.list_commands()) == 1
    
    def test_register_command_with_aliases(self, registry, sample_metadata):
        """Test that aliases are registered."""
        registry.register_command(sample_metadata)
        
        assert registry.has_command("test-command")
        assert registry.has_command("tc")
        assert registry.has_command("test")
    
    def test_register_duplicate_command(self, registry, sample_metadata):
        """Test that registering duplicate command raises error."""
        registry.register_command(sample_metadata)
        
        with pytest.raises(CommandAlreadyRegisteredError):
            registry.register_command(sample_metadata)
    
    def test_register_duplicate_command_with_override(self, registry, sample_metadata):
        """Test that override allows duplicate registration."""
        registry.register_command(sample_metadata)
        registry.register_command(sample_metadata, allow_override=True)
        
        assert len(registry.list_commands()) == 1
    
    def test_register_conflicting_alias(self, registry, sample_app):
        """Test that conflicting alias raises error."""
        metadata1 = CommandMetadata(
            name="command1",
            category=CommandCategory.UTILITY,
            description="Command 1",
            app=sample_app,
            aliases=["c"]
        )
        
        metadata2 = CommandMetadata(
            name="command2",
            category=CommandCategory.UTILITY,
            description="Command 2",
            app=sample_app,
            aliases=["c"]
        )
        
        registry.register_command(metadata1)
        
        with pytest.raises(CommandAlreadyRegisteredError, match="Alias 'c' is already used"):
            registry.register_command(metadata2)
    
    def test_unregister_command(self, registry, sample_metadata):
        """Test unregistering a command."""
        registry.register_command(sample_metadata)
        assert registry.has_command("test-command")
        
        registry.unregister_command("test-command")
        assert not registry.has_command("test-command")
        assert not registry.has_command("tc")
    
    def test_unregister_nonexistent_command(self, registry):
        """Test that unregistering nonexistent command raises error."""
        with pytest.raises(CommandNotFoundError):
            registry.unregister_command("nonexistent")
    
    def test_get_command(self, registry, sample_metadata):
        """Test getting a command."""
        registry.register_command(sample_metadata)
        
        metadata = registry.get_command("test-command")
        assert metadata.name == "test-command"
    
    def test_get_command_by_alias(self, registry, sample_metadata):
        """Test getting a command by alias."""
        registry.register_command(sample_metadata)
        
        metadata = registry.get_command("tc")
        assert metadata.name == "test-command"
    
    def test_get_nonexistent_command(self, registry):
        """Test that getting nonexistent command raises error."""
        with pytest.raises(CommandNotFoundError):
            registry.get_command("nonexistent")
    
    def test_has_command(self, registry, sample_metadata):
        """Test checking if command exists."""
        assert not registry.has_command("test-command")
        
        registry.register_command(sample_metadata)
        assert registry.has_command("test-command")
        assert registry.has_command("tc")
    
    def test_list_commands(self, registry, sample_app):
        """Test listing commands."""
        metadata1 = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup",
            app=sample_app
        )
        
        metadata2 = CommandMetadata(
            name="restore",
            category=CommandCategory.RESTORE,
            description="Restore",
            app=sample_app
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        commands = registry.list_commands()
        assert len(commands) == 2
        assert commands[0].name == "backup"
        assert commands[1].name == "restore"
    
    def test_list_commands_by_category(self, registry, sample_app):
        """Test listing commands by category."""
        metadata1 = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup",
            app=sample_app
        )
        
        metadata2 = CommandMetadata(
            name="restore",
            category=CommandCategory.RESTORE,
            description="Restore",
            app=sample_app
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        backup_commands = registry.list_commands(category=CommandCategory.BACKUP)
        assert len(backup_commands) == 1
        assert backup_commands[0].name == "backup"
    
    def test_list_commands_exclude_hidden(self, registry, sample_app):
        """Test that hidden commands are excluded by default."""
        metadata1 = CommandMetadata(
            name="visible",
            category=CommandCategory.UTILITY,
            description="Visible",
            app=sample_app
        )
        
        metadata2 = CommandMetadata(
            name="hidden",
            category=CommandCategory.UTILITY,
            description="Hidden",
            app=sample_app,
            hidden=True
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        commands = registry.list_commands(include_hidden=False)
        assert len(commands) == 1
        assert commands[0].name == "visible"
        
        commands_with_hidden = registry.list_commands(include_hidden=True)
        assert len(commands_with_hidden) == 2
    
    def test_list_commands_exclude_deprecated(self, registry, sample_app):
        """Test filtering deprecated commands."""
        metadata1 = CommandMetadata(
            name="current",
            category=CommandCategory.UTILITY,
            description="Current",
            app=sample_app
        )
        
        metadata2 = CommandMetadata(
            name="old",
            category=CommandCategory.UTILITY,
            description="Old",
            app=sample_app,
            deprecated=True,
            deprecation_message="Use 'current' instead"
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        commands = registry.list_commands(include_deprecated=False)
        assert len(commands) == 1
        assert commands[0].name == "current"
    
    def test_list_categories(self, registry, sample_app):
        """Test listing categories."""
        metadata1 = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup",
            app=sample_app
        )
        
        metadata2 = CommandMetadata(
            name="restore",
            category=CommandCategory.RESTORE,
            description="Restore",
            app=sample_app
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        categories = registry.list_categories()
        assert CommandCategory.BACKUP in categories
        assert CommandCategory.RESTORE in categories
    
    def test_get_commands_by_category(self, registry, sample_app):
        """Test getting commands by category."""
        metadata1 = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup",
            app=sample_app
        )
        
        registry.register_command(metadata1)
        
        commands = registry.get_commands_by_category(CommandCategory.BACKUP)
        assert len(commands) == 1
        assert commands[0].name == "backup"
    
    def test_search_commands_by_name(self, registry, sample_metadata):
        """Test searching commands by name."""
        registry.register_command(sample_metadata)
        
        results = registry.search_commands("test")
        assert len(results) == 1
        assert results[0].name == "test-command"
    
    def test_search_commands_by_description(self, registry, sample_metadata):
        """Test searching commands by description."""
        registry.register_command(sample_metadata)
        
        results = registry.search_commands("testing")
        assert len(results) == 1
    
    def test_search_commands_by_alias(self, registry, sample_metadata):
        """Test searching commands by alias."""
        registry.register_command(sample_metadata)
        
        results = registry.search_commands("tc")
        assert len(results) == 1
    
    def test_search_commands_by_tag(self, registry, sample_metadata):
        """Test searching commands by tag."""
        registry.register_command(sample_metadata)
        
        results = registry.search_commands("sample")
        assert len(results) == 1
    
    def test_validate_command(self, registry, sample_metadata):
        """Test command validation."""
        errors = registry.validate_command(sample_metadata)
        assert len(errors) == 0
    
    def test_validate_command_missing_name(self, registry, sample_app):
        """Test validation with missing name."""
        # This should raise during construction
        with pytest.raises(ValueError, match="Command name cannot be empty"):
            metadata = CommandMetadata(
                name="",
                category=CommandCategory.UTILITY,
                description="Test",
                app=sample_app
            )
    
    def test_validate_command_conflict(self, registry, sample_metadata, sample_app):
        """Test validation with name conflict."""
        registry.register_command(sample_metadata)
        
        # Create new metadata with same name
        new_metadata = CommandMetadata(
            name="test-command",
            category=CommandCategory.UTILITY,
            description="Another test",
            app=sample_app
        )
        
        errors = registry.validate_command(new_metadata)
        assert len(errors) > 0
        assert any("already exists" in error for error in errors)
    
    def test_clear_registry(self, registry, sample_metadata):
        """Test clearing the registry."""
        registry.register_command(sample_metadata)
        assert len(registry.list_commands()) == 1
        
        registry.clear()
        assert len(registry.list_commands()) == 0
    
    def test_get_statistics(self, registry, sample_app):
        """Test getting registry statistics."""
        metadata1 = CommandMetadata(
            name="backup",
            category=CommandCategory.BACKUP,
            description="Backup",
            app=sample_app,
            aliases=["bak"]
        )
        
        metadata2 = CommandMetadata(
            name="hidden",
            category=CommandCategory.UTILITY,
            description="Hidden",
            app=sample_app,
            hidden=True
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        
        stats = registry.get_statistics()
        assert stats["total_commands"] == 2
        assert stats["total_aliases"] == 1
        assert stats["hidden_commands"] == 1


class TestPluginSupport:
    """Tests for plugin support."""
    
    def test_register_plugin(self, registry):
        """Test registering a plugin."""
        plugin = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin"
        )
        
        registry.register_plugin(plugin)
        
        retrieved = registry.get_plugin("test-plugin")
        assert retrieved.name == "test-plugin"
        assert retrieved.version == "1.0.0"
    
    def test_register_plugin_empty_name(self, registry):
        """Test that empty plugin name raises error."""
        plugin = PluginMetadata(
            name="",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        
        with pytest.raises(PluginValidationError):
            registry.register_plugin(plugin)
    
    def test_unregister_plugin(self, registry, sample_app):
        """Test unregistering a plugin and its commands."""
        plugin = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        
        registry.register_plugin(plugin)
        
        # Register a command from the plugin
        metadata = CommandMetadata(
            name="plugin-command",
            category=CommandCategory.PLUGIN,
            description="Plugin command",
            app=sample_app,
            plugin_name="test-plugin"
        )
        
        registry.register_command(metadata)
        
        # Unregister plugin
        registry.unregister_plugin("test-plugin")
        
        # Plugin and its commands should be gone
        with pytest.raises(CommandRegistryError):
            registry.get_plugin("test-plugin")
        
        assert not registry.has_command("plugin-command")
    
    def test_list_plugins(self, registry):
        """Test listing plugins."""
        plugin1 = PluginMetadata(
            name="plugin1",
            version="1.0.0",
            author="Author1",
            description="Plugin 1"
        )
        
        plugin2 = PluginMetadata(
            name="plugin2",
            version="2.0.0",
            author="Author2",
            description="Plugin 2",
            enabled=False
        )
        
        registry.register_plugin(plugin1)
        registry.register_plugin(plugin2)
        
        all_plugins = registry.list_plugins()
        assert len(all_plugins) == 2
        
        enabled_plugins = registry.list_plugins(enabled_only=True)
        assert len(enabled_plugins) == 1
        assert enabled_plugins[0].name == "plugin1"
    
    def test_list_commands_by_plugin(self, registry, sample_app):
        """Test listing commands from a specific plugin."""
        plugin = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        
        registry.register_plugin(plugin)
        
        metadata1 = CommandMetadata(
            name="plugin-cmd1",
            category=CommandCategory.PLUGIN,
            description="Plugin command 1",
            app=sample_app,
            plugin_name="test-plugin"
        )
        
        metadata2 = CommandMetadata(
            name="plugin-cmd2",
            category=CommandCategory.PLUGIN,
            description="Plugin command 2",
            app=sample_app,
            plugin_name="test-plugin"
        )
        
        metadata3 = CommandMetadata(
            name="core-cmd",
            category=CommandCategory.UTILITY,
            description="Core command",
            app=sample_app
        )
        
        registry.register_command(metadata1)
        registry.register_command(metadata2)
        registry.register_command(metadata3)
        
        plugin_commands = registry.list_commands(plugin_name="test-plugin")
        assert len(plugin_commands) == 2


class TestGlobalRegistry:
    """Tests for global registry functions."""
    
    def test_get_global_registry(self):
        """Test getting global registry."""
        reset_command_registry()
        
        registry1 = get_command_registry()
        registry2 = get_command_registry()
        
        assert registry1 is registry2
    
    def test_reset_global_registry(self, sample_metadata):
        """Test resetting global registry."""
        reset_command_registry()
        
        registry = get_command_registry()
        registry.register_command(sample_metadata)
        
        assert len(registry.list_commands()) == 1
        
        reset_command_registry()
        new_registry = get_command_registry()
        
        assert len(new_registry.list_commands()) == 0
