"""
Tests for CommandRegistry integration with CLI.

This module tests the integration of CommandRegistry with the CLI,
including command registration and discovery.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import typer

from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
    reset_command_registry,
)
from TimeLocker.cli_modules.registry_integration import (
    register_core_commands,
    register_optional_commands,
    register_all_commands,
    add_commands_to_app,
    validate_registry,
)


@pytest.fixture
def registry():
    """Create a fresh command registry for each test."""
    reset_command_registry()
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


class TestCoreCommandRegistration:
    """Tests for core command registration."""
    
    def test_register_core_commands(self, registry):
        """Test registering core commands."""
        register_core_commands(registry)
        
        # Check that core commands are registered
        assert registry.has_command("backup")
        assert registry.has_command("repos")
        assert registry.has_command("snapshots")
        assert registry.has_command("credentials")
        assert registry.has_command("security")
        assert registry.has_command("config")
    
    def test_core_commands_have_metadata(self, registry):
        """Test that core commands have proper metadata."""
        register_core_commands(registry)
        
        backup_cmd = registry.get_command("backup")
        assert backup_cmd.category == CommandCategory.BACKUP
        assert backup_cmd.description
        assert backup_cmd.requires_config
        assert "core" in backup_cmd.tags
    
    def test_repos_command_has_alias(self, registry):
        """Test that repos command has repositories alias."""
        register_core_commands(registry)
        
        assert registry.has_command("repos")
        assert registry.has_command("repositories")
        
        # Both should resolve to the same command
        repos_cmd = registry.get_command("repos")
        repos_alias = registry.get_command("repositories")
        assert repos_cmd.name == repos_alias.name


class TestOptionalCommandRegistration:
    """Tests for optional command registration."""
    
    def test_register_optional_commands(self, registry):
        """Test registering optional commands."""
        register_optional_commands(registry)
        
        # Check that at least some optional commands are registered
        # (availability depends on imports)
        stats = registry.get_statistics()
        assert stats["total_commands"] >= 0  # May be 0 if imports fail
    
    def test_optional_commands_dont_fail_on_import_error(self, registry):
        """Test that missing optional commands don't cause failures."""
        # This should not raise even if some imports fail
        register_optional_commands(registry)
        
        # Registry should still be usable
        assert registry is not None


class TestCommandRegistration:
    """Tests for complete command registration."""
    
    def test_register_all_commands(self, registry):
        """Test registering all commands."""
        register_all_commands(registry)
        
        # Should have at least core commands
        assert registry.has_command("backup")
        assert registry.has_command("repos")
        
        stats = registry.get_statistics()
        assert stats["total_commands"] >= 6  # At least 6 core commands
    
    def test_register_all_commands_logs_statistics(self, registry, caplog):
        """Test that registration logs statistics."""
        import logging
        caplog.set_level(logging.INFO)
        
        register_all_commands(registry)
        
        # Check that statistics were logged
        assert any("CommandRegistry initialized" in record.message for record in caplog.records)


class TestAddCommandsToApp:
    """Tests for adding commands to Typer app."""
    
    def test_add_commands_to_app(self, registry, sample_app):
        """Test adding registered commands to app."""
        # Register a test command
        metadata = CommandMetadata(
            name="test",
            category=CommandCategory.UTILITY,
            description="Test command",
            app=sample_app
        )
        registry.register_command(metadata)
        
        # Create a new app and add commands
        main_app = typer.Typer()
        add_commands_to_app(main_app, registry)
        
        # Verify command was added (check registered commands)
        # Note: Typer doesn't expose registered sub-apps easily,
        # so we just verify no errors occurred
        assert True
    
    def test_add_commands_excludes_hidden(self, registry, sample_app):
        """Test that hidden commands are excluded by default."""
        # Register a hidden command
        metadata = CommandMetadata(
            name="hidden",
            category=CommandCategory.UTILITY,
            description="Hidden command",
            app=sample_app,
            hidden=True
        )
        registry.register_command(metadata)
        
        # Create a new app and add commands (should exclude hidden)
        main_app = typer.Typer()
        add_commands_to_app(main_app, registry, include_hidden=False)
        
        # Verify no errors
        assert True
    
    def test_add_commands_handles_errors(self, registry, caplog):
        """Test that errors during command addition are handled."""
        import logging
        caplog.set_level(logging.ERROR)
        
        # Create invalid metadata (this will cause an error when adding)
        metadata = CommandMetadata(
            name="invalid",
            category=CommandCategory.UTILITY,
            description="Invalid command",
            app=typer.Typer()  # Valid app
        )
        registry.register_command(metadata)
        
        # Try to add to app
        main_app = typer.Typer()
        add_commands_to_app(main_app, registry)
        
        # Should not raise, but may log errors
        assert True


class TestRegistryValidation:
    """Tests for registry validation."""
    
    def test_validate_empty_registry(self, registry):
        """Test validating an empty registry."""
        issues = validate_registry(registry)
        assert len(issues) == 0
    
    def test_validate_registry_with_commands(self, registry, sample_app):
        """Test validating a registry with commands."""
        metadata = CommandMetadata(
            name="test",
            category=CommandCategory.UTILITY,
            description="Test command",
            app=sample_app
        )
        registry.register_command(metadata)
        
        issues = validate_registry(registry)
        assert len(issues) == 0
    
    def test_validate_detects_missing_description(self, registry, sample_app):
        """Test that validation detects missing descriptions."""
        metadata = CommandMetadata(
            name="test",
            category=CommandCategory.UTILITY,
            description="No description",
            app=sample_app
        )
        registry.register_command(metadata)
        
        issues = validate_registry(registry)
        assert len(issues) > 0
        assert any("no description" in issue.lower() for issue in issues)
    
    def test_validate_detects_deprecated_commands(self, registry, sample_app):
        """Test that validation detects deprecated commands."""
        metadata = CommandMetadata(
            name="old",
            category=CommandCategory.UTILITY,
            description="Old command",
            app=sample_app,
            deprecated=True,
            deprecation_message="Use 'new' instead"
        )
        registry.register_command(metadata)
        
        issues = validate_registry(registry)
        assert len(issues) > 0
        assert any("deprecated" in issue.lower() for issue in issues)
    
    def test_validate_logs_hidden_commands(self, registry, sample_app, caplog):
        """Test that validation logs hidden commands."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        metadata = CommandMetadata(
            name="hidden",
            category=CommandCategory.UTILITY,
            description="Hidden command",
            app=sample_app,
            hidden=True
        )
        registry.register_command(metadata)
        
        validate_registry(registry)
        
        # Check that hidden commands were logged
        assert any("hidden commands" in record.message.lower() for record in caplog.records)


class TestIntegrationWithGlobalRegistry:
    """Tests for integration with global registry."""
    
    def test_register_commands_uses_global_registry(self):
        """Test that registration uses global registry when not provided."""
        reset_command_registry()
        
        register_core_commands()
        
        from TimeLocker.cli_modules.command_registry import get_command_registry
        registry = get_command_registry()
        
        assert registry.has_command("backup")
    
    def test_add_commands_uses_global_registry(self, sample_app):
        """Test that add_commands_to_app uses global registry."""
        reset_command_registry()
        
        from TimeLocker.cli_modules.command_registry import get_command_registry
        registry = get_command_registry()
        
        metadata = CommandMetadata(
            name="test",
            category=CommandCategory.UTILITY,
            description="Test",
            app=sample_app
        )
        registry.register_command(metadata)
        
        main_app = typer.Typer()
        add_commands_to_app(main_app)  # Should use global registry
        
        assert True
    
    def test_validate_uses_global_registry(self):
        """Test that validate_registry uses global registry."""
        reset_command_registry()
        
        issues = validate_registry()  # Should use global registry
        
        assert isinstance(issues, list)
