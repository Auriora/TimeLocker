"""
Comprehensive integration tests for Phase 6 components.

This module tests the integration of ValidationFramework, ErrorContext,
and CommandRegistry with end-to-end validation scenarios.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any

import typer

from TimeLocker.cli_modules.validation.base import (
    Validator,
    ValidationResult,
    CompositeValidator,
    OptionalValidator,
)
from TimeLocker.cli_modules.validation.common import (
    PathValidator,
    NameValidator,
    EmailValidator,
    IntegerRangeValidator,
)
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    PluginMetadata,
    CommandCategory,
    get_command_registry,
    reset_command_registry,
)
from TimeLocker.utils.error_handling import (
    ErrorContext,
    ErrorHandler,
    format_error_with_context,
)


class TestValidationFrameworkIntegration:
    """Integration tests for ValidationFramework with various validators."""
    
    def test_composite_validator_with_multiple_validators(self):
        """Test composite validator combining multiple validators."""
        # Create validators that work on the same type of data
        name_validator1 = NameValidator(min_length=3, max_length=20)
        name_validator2 = NameValidator(allow_spaces=False)
        
        # Combine with AND logic
        composite = name_validator1 & name_validator2
        
        # Test with valid name
        result = composite.validate("valid-name")
        assert result.valid is True
        
        # Test with invalid name (too short)
        result = composite.validate("ab")
        assert result.valid is False
    
    def test_optional_validator_with_path(self):
        """Test optional validator with path validation."""
        path_validator = PathValidator(must_exist=True)
        optional_path = OptionalValidator(path_validator)
        
        # None should pass
        result = optional_path.validate(None)
        assert result.valid is True
        
        # Empty string should pass
        result = optional_path.validate("")
        assert result.valid is True
        
        # Invalid path should fail
        result = optional_path.validate("/nonexistent/path/12345")
        assert result.valid is False
    
    def test_validator_composition_complex(self):
        """Test complex validator composition."""
        # Create validators for a repository configuration
        name_validator = NameValidator(
            min_length=3,
            max_length=50,
            allow_spaces=False,
            reserved_names={"default", "system"}
        )
        
        path_validator = PathValidator(
            must_exist=False,
            allow_relative=False
        )
        
        # Combine validators
        repo_name_validator = name_validator
        repo_path_validator = OptionalValidator(path_validator)
        
        # Test valid repository name
        result = repo_name_validator.validate("my-backup-repo")
        assert result.valid is True
        
        # Test reserved name
        result = repo_name_validator.validate("default")
        assert result.valid is False
        
        # Test optional path
        result = repo_path_validator.validate(None)
        assert result.valid is True
    
    def test_validation_with_context(self):
        """Test validation with context information."""
        class ContextAwareValidator(Validator):
            def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
                result = ValidationResult()
                if context and context.get('strict_mode'):
                    if len(value) < 10:
                        result.add_error(
                            self.field_name,
                            "In strict mode, value must be at least 10 characters",
                            "STRICT_LENGTH_ERROR"
                        )
                return result
        
        validator = ContextAwareValidator()
        
        # Without strict mode
        result = validator.validate("short", {'strict_mode': False})
        assert result.valid is True
        
        # With strict mode
        result = validator.validate("short", {'strict_mode': True})
        assert result.valid is False
    
    def test_validation_error_aggregation(self):
        """Test aggregating validation errors from multiple validators."""
        name_validator = NameValidator(min_length=5, max_length=10)
        email_validator = EmailValidator()
        
        # Create a composite that validates both
        composite = CompositeValidator([name_validator, email_validator], require_all=True)
        
        # Test with invalid input for both
        result = composite.validate("ab")  # Too short for name, invalid email
        assert result.valid is False
        assert len(result.get_errors()) >= 2  # Should have errors from both validators


class TestErrorContextIntegration:
    """Integration tests for ErrorContext with various scenarios."""
    
    def test_error_context_with_validation(self):
        """Test error context integration with validation."""
        with ErrorContext("validate_config", "ConfigValidator") as ctx:
            ctx.add_context("config_file", "/path/to/config.json")
            
            validator = NameValidator(min_length=5)
            result = validator.validate("ab")
            
            if not result.valid:
                ctx.add_recovery_suggestion("Provide a name with at least 5 characters")
                error = ValueError("Validation failed")
                formatted = ctx.format_error(error)
                
                assert "ConfigValidator" in formatted
                assert "validate_config" in formatted
                assert "at least 5 characters" in formatted
    
    def test_nested_error_context_with_validation(self):
        """Test nested error contexts with validation."""
        with ErrorContext("outer_operation", "OuterService") as outer:
            outer.add_context("operation_id", "12345")
            
            with ErrorContext("validate_input", "ValidationService") as inner:
                inner.add_context("input_field", "repository_name")
                
                validator = NameValidator(reserved_names={"system"})
                result = validator.validate("system")
                
                if not result.valid:
                    inner.add_recovery_suggestion("Choose a different repository name")
                    
                    # Get context including parent
                    context_dict = inner.get_context()
                    assert "parent_context" in context_dict
                    # Check that parent context exists and has the right operation
                    assert context_dict["parent_context"]["operation"] == "outer_operation"
                    # Check metadata contains operation_id
                    assert context_dict["parent_context"]["metadata"]["operation_id"] == "12345"
    
    def test_error_context_with_command_execution(self):
        """Test error context during command execution simulation."""
        def simulate_command_execution():
            with ErrorContext("execute_backup", "BackupCommand") as ctx:
                ctx.add_context("repository", "my-repo")
                ctx.add_context("sources", ["/data", "/home"])
                
                # Simulate validation
                validator = PathValidator(must_exist=True)
                result = validator.validate("/nonexistent/path")
                
                if not result.valid:
                    ctx.add_recovery_suggestion("Verify the path exists")
                    ctx.add_recovery_suggestion("Check file permissions")
                    raise FileNotFoundError("Path not found")
        
        with pytest.raises(FileNotFoundError):
            simulate_command_execution()
    
    def test_error_recovery_suggestions_from_validation(self):
        """Test generating recovery suggestions from validation errors."""
        with ErrorContext("create_repository", "RepositoryCommand") as ctx:
            validator = NameValidator(
                min_length=3,
                max_length=50,
                allow_spaces=False
            )
            
            result = validator.validate("my repo")  # Has space
            
            if not result.valid:
                # Add recovery suggestions based on validation errors
                for error in result.get_errors():
                    if "spaces" in error.message.lower():
                        ctx.add_recovery_suggestion("Remove spaces from the repository name")
                        ctx.add_recovery_suggestion("Use hyphens or underscores instead")
                
                suggestions = ctx.get_recovery_suggestions()
                assert len(suggestions) >= 2
                assert any("spaces" in s.lower() for s in suggestions)


class TestCommandRegistryIntegration:
    """Integration tests for CommandRegistry with validation and error handling."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return CommandRegistry()
    
    @pytest.fixture
    def sample_app(self):
        """Create a sample Typer app."""
        app = typer.Typer(help="Sample command")
        
        @app.command()
        def test_command():
            """Test command."""
            pass
        
        return app
    
    def test_command_registration_with_validation(self, registry, sample_app):
        """Test command registration with validation."""
        # Create metadata with validation
        name_validator = NameValidator(min_length=3, allow_spaces=False)
        
        command_name = "backup-create"
        result = name_validator.validate(command_name)
        assert result.valid is True
        
        metadata = CommandMetadata(
            name=command_name,
            category=CommandCategory.BACKUP,
            description="Create a backup",
            app=sample_app
        )
        
        # Validate before registration
        errors = registry.validate_command(metadata)
        assert len(errors) == 0
        
        # Register
        registry.register_command(metadata)
        assert registry.has_command(command_name)
    
    def test_command_registration_with_error_context(self, registry, sample_app):
        """Test command registration with error context."""
        with ErrorContext("register_command", "CommandRegistry") as ctx:
            ctx.add_context("command_name", "test-command")
            
            try:
                metadata = CommandMetadata(
                    name="test-command",
                    category=CommandCategory.UTILITY,
                    description="Test command",
                    app=sample_app
                )
                
                registry.register_command(metadata)
                
                # Try to register again (should fail)
                registry.register_command(metadata)
            except Exception as e:
                ctx.add_recovery_suggestion("Use a different command name")
                ctx.add_recovery_suggestion("Use allow_override=True to replace existing command")
                
                formatted = ctx.format_error(e)
                assert "CommandRegistry" in formatted
    
    def test_plugin_registration_with_validation(self, registry, sample_app):
        """Test plugin registration with validation."""
        # Validate plugin metadata
        name_validator = NameValidator(min_length=3, allow_spaces=False)
        
        plugin_name = "my-plugin"
        result = name_validator.validate(plugin_name)
        assert result.valid is True
        
        plugin = PluginMetadata(
            name=plugin_name,
            version="1.0.0",
            author="Test Author",
            description="Test plugin"
        )
        
        registry.register_plugin(plugin)
        
        # Register commands from plugin
        metadata = CommandMetadata(
            name="plugin-command",
            category=CommandCategory.PLUGIN,
            description="Command from plugin",
            app=sample_app,
            plugin_name=plugin_name
        )
        
        registry.register_command(metadata)
        
        # Verify plugin commands
        plugin_commands = registry.list_commands(plugin_name=plugin_name)
        assert len(plugin_commands) == 1
    
    def test_command_search_with_validation(self, registry, sample_app):
        """Test command search with validation."""
        # Register multiple commands
        commands = [
            ("backup-create", CommandCategory.BACKUP, "Create backup"),
            ("backup-list", CommandCategory.BACKUP, "List backups"),
            ("restore-files", CommandCategory.RESTORE, "Restore files"),
        ]
        
        for name, category, description in commands:
            metadata = CommandMetadata(
                name=name,
                category=category,
                description=description,
                app=sample_app
            )
            registry.register_command(metadata)
        
        # Search for backup commands
        results = registry.search_commands("backup")
        assert len(results) == 2
        
        # Search by category
        backup_commands = registry.list_commands(category=CommandCategory.BACKUP)
        assert len(backup_commands) == 2


class TestEndToEndIntegration:
    """End-to-end integration tests combining all Phase 6 components."""
    
    def test_complete_command_workflow(self):
        """Test complete command workflow with validation, error handling, and registry."""
        reset_command_registry()
        registry = get_command_registry()
        
        # Create a command with validation
        app = typer.Typer(help="Backup command")
        
        @app.command()
        def create(
            name: str = typer.Argument(..., help="Repository name"),
            path: str = typer.Option(None, help="Repository path")
        ):
            """Create a backup repository."""
            with ErrorContext("create_repository", "BackupCommand") as ctx:
                ctx.add_context("name", name)
                ctx.add_context("path", path)
                
                # Validate name
                name_validator = NameValidator(
                    min_length=3,
                    max_length=50,
                    allow_spaces=False,
                    reserved_names={"default", "system"}
                )
                
                result = name_validator.validate(name)
                if not result.valid:
                    ctx.add_recovery_suggestion("Choose a valid repository name")
                    for error in result.get_errors():
                        ctx.add_recovery_suggestion(f"Fix: {error.message}")
                    raise ValueError("Invalid repository name")
                
                # Validate path if provided
                if path:
                    path_validator = PathValidator(allow_relative=False)
                    result = path_validator.validate(path)
                    if not result.valid:
                        ctx.add_recovery_suggestion("Provide an absolute path")
                        raise ValueError("Invalid repository path")
                
                return {"name": name, "path": path}
        
        # Register command
        metadata = CommandMetadata(
            name="backup-create",
            category=CommandCategory.BACKUP,
            description="Create a backup repository",
            app=app,
            aliases=["bc", "create-backup"]
        )
        
        registry.register_command(metadata)
        
        # Verify registration
        assert registry.has_command("backup-create")
        assert registry.has_command("bc")
        
        # Get command
        cmd = registry.get_command("backup-create")
        assert cmd.name == "backup-create"
        assert cmd.category == CommandCategory.BACKUP
    
    def test_validation_error_handling_workflow(self):
        """Test validation error handling workflow."""
        with ErrorContext("validate_configuration", "ConfigService") as ctx:
            ctx.add_context("config_file", "/etc/timelocker/config.json")
            
            # Simulate configuration validation
            validators = {
                'repository_name': NameValidator(min_length=3, allow_spaces=False),
                'backup_path': PathValidator(must_exist=False, allow_relative=False),
                'email': EmailValidator(),
                'port': IntegerRangeValidator(min_value=1, max_value=65535),
            }
            
            config = {
                'repository_name': 'my-repo',
                'backup_path': '/backup',
                'email': 'admin@example.com',
                'port': 8080,
            }
            
            validation_errors = []
            
            for field, validator in validators.items():
                if field in config:
                    result = validator.validate(config[field])
                    if not result.valid:
                        validation_errors.extend(result.get_errors())
            
            # All should be valid
            assert len(validation_errors) == 0
            
            # Test with invalid config
            invalid_config = {
                'repository_name': 'ab',  # Too short
                'backup_path': 'relative/path',  # Relative path
                'email': 'invalid-email',  # Invalid email
                'port': 70000,  # Out of range
            }
            
            validation_errors = []
            
            for field, validator in validators.items():
                if field in invalid_config:
                    result = validator.validate(invalid_config[field])
                    if not result.valid:
                        validation_errors.extend(result.get_errors())
                        ctx.add_recovery_suggestion(f"Fix {field}: {result.get_errors()[0].message}")
            
            # Should have errors
            assert len(validation_errors) == 4
            
            # Should have recovery suggestions
            suggestions = ctx.get_recovery_suggestions()
            assert len(suggestions) >= 4
    
    def test_plugin_command_with_validation(self):
        """Test plugin command registration with validation."""
        reset_command_registry()
        registry = get_command_registry()
        
        # Create plugin
        plugin = PluginMetadata(
            name="backup-plugin",
            version="1.0.0",
            author="Plugin Author",
            description="Backup plugin with custom commands"
        )
        
        registry.register_plugin(plugin)
        
        # Create plugin command with validation
        app = typer.Typer(help="Plugin command")
        
        @app.command()
        def custom_backup(name: str):
            """Custom backup command from plugin."""
            with ErrorContext("custom_backup", "BackupPlugin") as ctx:
                ctx.add_context("plugin", "backup-plugin")
                ctx.add_context("name", name)
                
                validator = NameValidator(min_length=5)
                result = validator.validate(name)
                
                if not result.valid:
                    ctx.add_recovery_suggestion("Provide a name with at least 5 characters")
                    raise ValueError("Invalid backup name")
                
                return {"name": name}
        
        # Register plugin command
        metadata = CommandMetadata(
            name="custom-backup",
            category=CommandCategory.PLUGIN,
            description="Custom backup from plugin",
            app=app,
            plugin_name="backup-plugin"
        )
        
        registry.register_command(metadata)
        
        # Verify
        assert registry.has_command("custom-backup")
        
        # Get plugin commands
        plugin_commands = registry.list_commands(plugin_name="backup-plugin")
        assert len(plugin_commands) == 1
        assert plugin_commands[0].name == "custom-backup"
    
    def test_complex_validation_with_error_recovery(self):
        """Test complex validation scenario with error recovery."""
        with ErrorContext("create_backup_job", "BackupOrchestrator") as ctx:
            ctx.add_context("job_type", "scheduled")
            
            # Validate multiple fields
            validators = {
                'name': NameValidator(min_length=3, max_length=50, allow_spaces=False),
                'repository': NameValidator(min_length=3, reserved_names={"system"}),
                'sources': PathValidator(must_exist=True),
                'schedule': IntegerRangeValidator(min_value=1, max_value=24),
            }
            
            job_config = {
                'name': 'daily-backup',
                'repository': 'my-repo',
                'sources': '/tmp',  # Exists
                'schedule': 12,
            }
            
            all_valid = True
            
            for field, validator in validators.items():
                result = validator.validate(job_config[field])
                if not result.valid:
                    all_valid = False
                    for error in result.get_errors():
                        ctx.add_recovery_suggestion(f"{field}: {error.message}")
            
            assert all_valid is True
            
            # Test with invalid config
            invalid_job = {
                'name': 'ab',  # Too short
                'repository': 'system',  # Reserved
                'sources': '/nonexistent',  # Doesn't exist
                'schedule': 30,  # Out of range
            }
            
            all_valid = True
            
            for field, validator in validators.items():
                result = validator.validate(invalid_job[field])
                if not result.valid:
                    all_valid = False
            
            assert all_valid is False


class TestPerformanceAndScalability:
    """Test performance and scalability of Phase 6 components."""
    
    def test_large_number_of_commands(self):
        """Test registry with large number of commands."""
        reset_command_registry()
        registry = get_command_registry()
        
        app = typer.Typer(help="Test command")
        
        # Register 100 commands
        for i in range(100):
            metadata = CommandMetadata(
                name=f"command-{i}",
                category=CommandCategory.UTILITY,
                description=f"Command {i}",
                app=app
            )
            registry.register_command(metadata)
        
        # Verify all registered
        assert len(registry.list_commands()) == 100
        
        # Test search performance
        results = registry.search_commands("command-50")
        assert len(results) >= 1
        
        # Test statistics
        stats = registry.get_statistics()
        assert stats["total_commands"] == 100
    
    def test_complex_validator_composition(self):
        """Test performance of complex validator composition."""
        # Create a complex validator chain
        validators = [
            NameValidator(min_length=3, max_length=50),
            NameValidator(allow_spaces=False),
            NameValidator(reserved_names={"system", "default"}),
        ]
        
        composite = CompositeValidator(validators, require_all=True)
        
        # Test with valid input
        result = composite.validate("valid-name")
        assert result.valid is True
        
        # Test with invalid input
        result = composite.validate("system")
        assert result.valid is False
    
    def test_nested_error_context_depth(self):
        """Test deeply nested error contexts."""
        def level_5():
            with ErrorContext("level_5", "Service5") as ctx:
                ctx.add_context("level", 5)
                raise ValueError("Error at level 5")
        
        def level_4():
            with ErrorContext("level_4", "Service4") as ctx:
                ctx.add_context("level", 4)
                level_5()
        
        def level_3():
            with ErrorContext("level_3", "Service3") as ctx:
                ctx.add_context("level", 3)
                level_4()
        
        def level_2():
            with ErrorContext("level_2", "Service2") as ctx:
                ctx.add_context("level", 2)
                level_3()
        
        def level_1():
            with ErrorContext("level_1", "Service1") as ctx:
                ctx.add_context("level", 1)
                level_2()
        
        with pytest.raises(ValueError):
            level_1()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
