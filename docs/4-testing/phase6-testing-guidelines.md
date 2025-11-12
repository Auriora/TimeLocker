# Phase 6 Testing Guidelines

## Overview

This document provides testing guidelines for Phase 6 components: ValidationFramework, ErrorContext, and CommandRegistry. These guidelines ensure consistent, comprehensive testing across all CLI refactoring components.

## Testing Strategy

### Test Levels

1. **Unit Tests**: Test individual validators, error contexts, and registry operations
2. **Integration Tests**: Test component interactions and end-to-end workflows
3. **Performance Tests**: Verify performance characteristics and scalability
4. **Regression Tests**: Ensure no functional regressions

### Test Coverage Goals

- Unit test coverage: >90%
- Integration test coverage: >80%
- Critical path coverage: 100%

## ValidationFramework Testing

### Unit Testing Validators

#### Basic Validator Tests

```python
import pytest
from TimeLocker.cli_modules.validation.common import NameValidator

class TestNameValidator:
    """Test NameValidator functionality."""
    
    def test_valid_name(self):
        """Test validation of valid name."""
        validator = NameValidator(min_length=3, max_length=50)
        result = validator.validate("my-repository")
        assert result.valid is True
    
    def test_empty_name(self):
        """Test validation of empty name."""
        validator = NameValidator()
        result = validator.validate("")
        assert result.valid is False
        assert any("empty" in e.message.lower() for e in result.get_errors())
    
    def test_min_length(self):
        """Test minimum length validation."""
        validator = NameValidator(min_length=5)
        
        result = validator.validate("ab")
        assert result.valid is False
        assert any("at least 5" in e.message for e in result.get_errors())
        
        result = validator.validate("abcde")
        assert result.valid is True
    
    def test_reserved_names(self):
        """Test reserved names validation."""
        validator = NameValidator(reserved_names={"default", "system"})
        
        result = validator.validate("default")
        assert result.valid is False
        assert any("reserved" in e.message.lower() for e in result.get_errors())
        
        result = validator.validate("myrepo")
        assert result.valid is True
```

#### Composite Validator Tests

```python
from TimeLocker.cli_modules.validation.base import CompositeValidator
from TimeLocker.cli_modules.validation.common import NameValidator

class TestCompositeValidator:
    """Test CompositeValidator functionality."""
    
    def test_and_logic_all_pass(self):
        """Test AND logic when all validators pass."""
        v1 = NameValidator(min_length=3)
        v2 = NameValidator(allow_spaces=False)
        
        composite = CompositeValidator([v1, v2], require_all=True)
        result = composite.validate("valid-name")
        
        assert result.valid is True
    
    def test_and_logic_one_fails(self):
        """Test AND logic when one validator fails."""
        v1 = NameValidator(min_length=3)
        v2 = NameValidator(allow_spaces=False)
        
        composite = CompositeValidator([v1, v2], require_all=True)
        result = composite.validate("ab")  # Too short
        
        assert result.valid is False
    
    def test_or_logic_one_passes(self):
        """Test OR logic when one validator passes."""
        v1 = NameValidator(min_length=10)  # Will fail
        v2 = NameValidator(min_length=3)   # Will pass
        
        composite = CompositeValidator([v1, v2], require_all=False)
        result = composite.validate("short")
        
        assert result.valid is True
```

#### Optional Validator Tests

```python
from TimeLocker.cli_modules.validation.base import OptionalValidator
from TimeLocker.cli_modules.validation.common import PathValidator

class TestOptionalValidator:
    """Test OptionalValidator functionality."""
    
    def test_none_value(self):
        """Test that None values pass validation."""
        inner = PathValidator(must_exist=True)
        validator = OptionalValidator(inner)
        
        result = validator.validate(None)
        assert result.valid is True
    
    def test_empty_string_allowed(self):
        """Test that empty strings pass when allowed."""
        inner = PathValidator(must_exist=True)
        validator = OptionalValidator(inner, allow_empty=True)
        
        result = validator.validate("")
        assert result.valid is True
    
    def test_present_value_validated(self):
        """Test that present values are validated."""
        inner = PathValidator(must_exist=True)
        validator = OptionalValidator(inner)
        
        result = validator.validate("/nonexistent/path")
        assert result.valid is False
```

### Integration Testing

#### Configuration Validation

```python
from TimeLocker.cli_modules.validation.common import (
    NameValidator,
    PathValidator,
    EmailValidator,
    PortValidator,
)

class TestConfigurationValidation:
    """Test configuration validation workflows."""
    
    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        validators = {
            'repository_name': NameValidator(min_length=3, allow_spaces=False),
            'backup_path': PathValidator(must_exist=False, allow_relative=False),
            'email': EmailValidator(),
            'port': PortValidator(min_port=1, max_port=65535),
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
        
        assert len(validation_errors) == 0
    
    def test_invalid_configuration(self):
        """Test validation of invalid configuration."""
        validators = {
            'repository_name': NameValidator(min_length=3),
            'email': EmailValidator(),
        }
        
        config = {
            'repository_name': 'ab',  # Too short
            'email': 'invalid-email',  # Invalid format
        }
        
        validation_errors = []
        
        for field, validator in validators.items():
            result = validator.validate(config[field])
            if not result.valid:
                validation_errors.extend(result.get_errors())
        
        assert len(validation_errors) == 2
```

## ErrorContext Testing

### Unit Testing

#### Basic Context Tests

```python
from TimeLocker.utils.error_handling import ErrorContext

class TestErrorContext:
    """Test ErrorContext functionality."""
    
    def test_context_creation(self):
        """Test creating error context with basic information."""
        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            param1="value1"
        )
        
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.metadata["param1"] == "value1"
    
    def test_add_context(self):
        """Test adding context information dynamically."""
        context = ErrorContext("test_op", "test_comp")
        
        context.add_context("key1", "value1")
        context.add_context("key2", 123)
        
        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"] == 123
    
    def test_recovery_suggestions(self):
        """Test adding recovery suggestions."""
        context = ErrorContext("test_op", "test_comp")
        
        context.add_recovery_suggestion("Try action 1")
        context.add_recovery_suggestion("Try action 2")
        
        suggestions = context.get_recovery_suggestions()
        assert len(suggestions) == 2
        assert "Try action 1" in suggestions
```

#### Nested Context Tests

```python
class TestNestedErrorContext:
    """Test nested error context functionality."""
    
    def test_context_stack_tracking(self):
        """Test that context stack is tracked through nested contexts."""
        with ErrorContext("outer_op", "outer_comp") as outer:
            outer.add_context("level", "outer")
            
            with ErrorContext("inner_op", "inner_comp") as inner:
                inner.add_context("level", "inner")
                
                # Inner context should have outer as parent
                assert inner.parent_context is outer
                assert inner.parent_context.metadata["level"] == "outer"
    
    def test_recovery_suggestions_from_parent(self):
        """Test that recovery suggestions include parent suggestions."""
        with ErrorContext("outer_op", "outer_comp") as outer:
            outer.add_recovery_suggestion("Outer suggestion")
            
            with ErrorContext("inner_op", "inner_comp") as inner:
                inner.add_recovery_suggestion("Inner suggestion")
                
                suggestions = inner.get_recovery_suggestions()
                assert len(suggestions) == 2
                assert "Inner suggestion" in suggestions
                assert "Outer suggestion" in suggestions
```

### Integration Testing

#### Error Context with Validation

```python
from TimeLocker.utils.error_handling import ErrorContext
from TimeLocker.cli_modules.validation.common import NameValidator

class TestErrorContextIntegration:
    """Test error context integration with validation."""
    
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
```

## CommandRegistry Testing

### Unit Testing

#### Basic Registry Tests

```python
import typer
from TimeLocker.cli_modules.command_registry import (
    CommandRegistry,
    CommandMetadata,
    CommandCategory,
)

class TestCommandRegistry:
    """Test CommandRegistry functionality."""
    
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
    
    def test_register_command(self, registry, sample_app):
        """Test registering a command."""
        metadata = CommandMetadata(
            name="test-command",
            category=CommandCategory.UTILITY,
            description="Test command",
            app=sample_app
        )
        
        registry.register_command(metadata)
        
        assert registry.has_command("test-command")
        assert len(registry.list_commands()) == 1
    
    def test_command_aliases(self, registry, sample_app):
        """Test that aliases are registered."""
        metadata = CommandMetadata(
            name="test-command",
            category=CommandCategory.UTILITY,
            description="Test command",
            app=sample_app,
            aliases=["tc", "test"]
        )
        
        registry.register_command(metadata)
        
        assert registry.has_command("test-command")
        assert registry.has_command("tc")
        assert registry.has_command("test")
    
    def test_search_commands(self, registry, sample_app):
        """Test searching commands."""
        metadata = CommandMetadata(
            name="backup-create",
            category=CommandCategory.BACKUP,
            description="Create a backup",
            app=sample_app,
            tags={"backup", "create"}
        )
        
        registry.register_command(metadata)
        
        # Search by name
        results = registry.search_commands("backup")
        assert len(results) == 1
        
        # Search by tag
        results = registry.search_commands("create")
        assert len(results) == 1
```

#### Plugin Tests

```python
from TimeLocker.cli_modules.command_registry import PluginMetadata

class TestPluginSupport:
    """Test plugin support functionality."""
    
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
    
    def test_plugin_commands(self, registry, sample_app):
        """Test plugin command registration."""
        plugin = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        
        registry.register_plugin(plugin)
        
        metadata = CommandMetadata(
            name="plugin-command",
            category=CommandCategory.PLUGIN,
            description="Plugin command",
            app=sample_app,
            plugin_name="test-plugin"
        )
        
        registry.register_command(metadata)
        
        # Verify plugin commands
        plugin_commands = registry.list_commands(plugin_name="test-plugin")
        assert len(plugin_commands) == 1
```

### Integration Testing

#### End-to-End Workflow

```python
class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_complete_command_workflow(self):
        """Test complete command workflow with validation and error handling."""
        from TimeLocker.cli_modules.command_registry import (
            get_command_registry,
            reset_command_registry,
        )
        from TimeLocker.utils.error_handling import ErrorContext
        from TimeLocker.cli_modules.validation.common import NameValidator
        
        reset_command_registry()
        registry = get_command_registry()
        
        # Create command with validation
        app = typer.Typer(help="Backup command")
        
        @app.command()
        def create(name: str):
            """Create a backup repository."""
            with ErrorContext("create_repository", "BackupCommand") as ctx:
                ctx.add_context("name", name)
                
                # Validate name
                validator = NameValidator(min_length=3, allow_spaces=False)
                result = validator.validate(name)
                
                if not result.valid:
                    ctx.add_recovery_suggestion("Choose a valid repository name")
                    raise ValueError("Invalid repository name")
                
                return {"name": name}
        
        # Register command
        metadata = CommandMetadata(
            name="backup-create",
            category=CommandCategory.BACKUP,
            description="Create a backup repository",
            app=app
        )
        
        registry.register_command(metadata)
        
        # Verify registration
        assert registry.has_command("backup-create")
        
        # Get command
        cmd = registry.get_command("backup-create")
        assert cmd.name == "backup-create"
```

## Performance Testing

### Validator Performance

```python
import pytest
from TimeLocker.cli_modules.validation.common import NameValidator

class TestValidatorPerformance:
    """Test validator performance."""
    
    def test_validator_performance(self, benchmark):
        """Test validator performance with benchmark."""
        validator = NameValidator(min_length=3, max_length=50)
        
        result = benchmark(validator.validate, "test-name")
        assert result.valid is True
    
    def test_composite_validator_performance(self, benchmark):
        """Test composite validator performance."""
        validators = [
            NameValidator(min_length=3),
            NameValidator(max_length=50),
            NameValidator(allow_spaces=False),
        ]
        
        composite = CompositeValidator(validators, require_all=True)
        
        result = benchmark(composite.validate, "test-name")
        assert result.valid is True
```

### Registry Performance

```python
class TestRegistryPerformance:
    """Test registry performance."""
    
    def test_large_number_of_commands(self):
        """Test registry with large number of commands."""
        registry = CommandRegistry()
        app = typer.Typer()
        
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
```

## Test Organization

### Directory Structure

```
tests/TimeLocker/cli_modules/
├── validation/
│   ├── test_base.py              # Base validator tests
│   ├── test_common.py            # Common validator tests
│   └── test_integration.py       # Validation integration tests
├── test_command_registry.py      # Command registry tests
├── test_registry_integration.py  # Registry integration tests
└── test_phase6_integration.py    # End-to-end integration tests

tests/TimeLocker/utils/
└── test_error_context.py         # Error context tests
```

### Test Naming Conventions

- Test files: `test_<component>.py`
- Test classes: `Test<Component>`
- Test methods: `test_<functionality>`

### Fixtures

Use pytest fixtures for common test setup:

```python
@pytest.fixture
def registry():
    """Create a fresh command registry."""
    return CommandRegistry()

@pytest.fixture
def sample_app():
    """Create a sample Typer app."""
    app = typer.Typer(help="Sample command")
    return app

@pytest.fixture
def validator():
    """Create a sample validator."""
    return NameValidator(min_length=3, max_length=50)
```

## Continuous Integration

### Test Execution

Run tests with pytest:

```bash
# Run all Phase 6 tests
pytest tests/TimeLocker/cli_modules/test_phase6_integration.py -v

# Run with coverage
pytest tests/TimeLocker/cli_modules/ --cov=src/TimeLocker/cli_modules --cov-report=html

# Run performance tests
pytest tests/TimeLocker/cli_modules/ -k "performance" --benchmark-only
```

### Coverage Requirements

- Minimum coverage: 90%
- Critical paths: 100%
- New code: 95%

## Best Practices

### 1. Test One Thing at a Time

```python
# Good: Tests one specific behavior
def test_name_validator_min_length():
    validator = NameValidator(min_length=5)
    result = validator.validate("ab")
    assert result.valid is False

# Avoid: Tests multiple behaviors
def test_name_validator():
    validator = NameValidator(min_length=5, max_length=10)
    assert validator.validate("ab").valid is False
    assert validator.validate("verylongname").valid is False
    assert validator.validate("valid").valid is True
```

### 2. Use Descriptive Test Names

```python
# Good: Clear what is being tested
def test_name_validator_rejects_reserved_names():
    ...

# Avoid: Unclear test purpose
def test_validator():
    ...
```

### 3. Test Edge Cases

```python
def test_name_validator_edge_cases():
    validator = NameValidator(min_length=3, max_length=10)
    
    # Boundary values
    assert validator.validate("abc").valid is True  # Min length
    assert validator.validate("ab").valid is False  # Below min
    assert validator.validate("1234567890").valid is True  # Max length
    assert validator.validate("12345678901").valid is False  # Above max
    
    # Special cases
    assert validator.validate("").valid is False  # Empty
    assert validator.validate(None).valid is False  # None
```

### 4. Use Parametrized Tests

```python
@pytest.mark.parametrize("name,expected", [
    ("valid-name", True),
    ("ab", False),  # Too short
    ("verylongname", False),  # Too long
    ("", False),  # Empty
])
def test_name_validator_various_inputs(name, expected):
    validator = NameValidator(min_length=3, max_length=10)
    result = validator.validate(name)
    assert result.valid is expected
```

### 5. Mock External Dependencies

```python
from unittest.mock import Mock, patch

def test_path_validator_with_mock():
    """Test path validator with mocked file system."""
    with patch('pathlib.Path.exists', return_value=True):
        validator = PathValidator(must_exist=True)
        result = validator.validate("/mock/path")
        assert result.valid is True
```

## See Also

- [ValidationFramework Documentation](../3-implementation/validation-framework.md)
- [ErrorContext Documentation](../3-implementation/error-context-usage.md)
- [CommandRegistry Documentation](../3-implementation/command-registry-api.md)
- [Testing Overview](testing-overview.md)
