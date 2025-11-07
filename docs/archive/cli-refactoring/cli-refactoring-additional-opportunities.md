# Additional CLI Refactoring Opportunities

**Date**: 2025-11-07  
**Status**: Recommendations for Future Work

## Overview

Beyond the three-phase refactoring already implemented/planned, there are additional opportunities to improve the CLI codebase. This document outlines further refactoring suggestions.

## Completed So Far

✅ **Phase 1**: Helper extraction (752 lines)  
✅ **Phase 3**: Pattern consolidation (base classes, decorators)  
🔄 **Phase 2**: Command extraction (10.4% complete - 7/67 commands)

## Additional Refactoring Opportunities

### 1. Configuration Management Consolidation

**Current State**: Configuration logic scattered across multiple places
- `_create_configuration_module()` in helpers
- Direct ConfigurationManager usage in commands
- Multiple ways to access config

**Recommendation**: Create unified configuration service

```python
# cli_modules/services/config_service.py
class ConfigService:
    """Unified configuration access for CLI."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir
        self._config_module = None
        self._config_manager = None
    
    @property
    def config_module(self):
        if not self._config_module:
            self._config_module = _create_configuration_module(self.config_dir)
        return self._config_module
    
    @property
    def config_manager(self):
        if not self._config_manager:
            self._config_manager = ConfigurationManager(self.config_dir)
        return self._config_manager
    
    def get_repository(self, name: str):
        """Get repository by name with fallback logic."""
        # Unified repository lookup
        pass
    
    def get_default_repository(self):
        """Get default repository with fallback logic."""
        # Unified default repo lookup
        pass
```

**Benefits**:
- Single source of truth for config access
- Consistent error handling
- Easier to mock in tests
- Clearer API

**Estimated Impact**: Simplify 20+ config access points

---

### 2. Repository Resolution Service

**Current State**: Repository resolution logic duplicated in multiple commands
- URI resolution scattered
- Password resolution inconsistent
- Backend detection repeated

**Recommendation**: Create dedicated repository resolver

```python
# cli_modules/services/repository_resolver.py
class RepositoryResolver:
    """Resolve repository names, URIs, and credentials."""
    
    def resolve(
        self,
        repository: Optional[str],
        password: Optional[str] = None,
        use_default: bool = True
    ) -> ResolvedRepository:
        """
        Resolve repository with full credential chain.
        
        Returns:
            ResolvedRepository with uri, name, password, backend
        """
        pass
    
    def validate(self, repository: str) -> bool:
        """Validate repository name or URI."""
        pass
    
    def get_backend(self, uri: str) -> str:
        """Detect backend from URI."""
        pass
```

**Benefits**:
- Eliminate duplication in backup, restore, snapshot commands
- Consistent credential resolution
- Single place to update resolution logic
- Better error messages

**Estimated Impact**: Remove ~200 lines of duplicated code

---

### 3. Interactive Prompt Service

**Current State**: Prompts scattered throughout commands
- Inconsistent prompt styles
- Repeated confirmation logic
- No centralized prompt history

**Recommendation**: Create prompt service

```python
# cli_modules/services/prompt_service.py
class PromptService:
    """Centralized interactive prompts."""
    
    def __init__(self, interactive: bool = None):
        self.interactive = interactive if interactive is not None else sys.stdin.isatty()
    
    def ask(self, prompt: str, default: Optional[str] = None) -> str:
        """Ask for text input."""
        if not self.interactive:
            raise NonInteractiveError(f"Cannot prompt in non-interactive mode: {prompt}")
        return Prompt.ask(prompt, default=default)
    
    def confirm(self, prompt: str, default: bool = False) -> bool:
        """Ask for confirmation."""
        if not self.interactive:
            return default
        return Confirm.ask(prompt, default=default)
    
    def password(self, prompt: str = "Password") -> str:
        """Ask for password."""
        if not self.interactive:
            raise NonInteractiveError("Cannot prompt for password in non-interactive mode")
        return Prompt.ask(prompt, password=True)
    
    def select(self, prompt: str, choices: List[str]) -> str:
        """Select from choices."""
        # Implementation
        pass
```

**Benefits**:
- Consistent prompt behavior
- Easy to mock for testing
- Centralized non-interactive handling
- Better UX with consistent styling

**Estimated Impact**: Simplify 30+ prompt locations

---

### 4. Output Formatting Service

**Current State**: Table/panel creation duplicated
- Similar table structures repeated
- Inconsistent column widths
- Repeated formatting logic

**Recommendation**: Create output formatter

```python
# cli_modules/services/output_formatter.py
class OutputFormatter:
    """Standardized output formatting."""
    
    def table(
        self,
        title: str,
        columns: List[ColumnDef],
        rows: List[Dict],
        style: str = "default"
    ) -> Table:
        """Create standardized table."""
        pass
    
    def list_table(
        self,
        title: str,
        items: List[Dict],
        columns: Optional[List[str]] = None
    ) -> Table:
        """Create list table with auto-detected columns."""
        pass
    
    def detail_panel(
        self,
        title: str,
        data: Dict[str, Any],
        style: str = "blue"
    ) -> Panel:
        """Create detail panel."""
        pass
    
    def json_output(self, data: Any) -> None:
        """Output JSON."""
        console.print_json(data=data)
```

**Benefits**:
- Consistent table styling
- Easier to change output format globally
- Reduce duplication
- Better accessibility

**Estimated Impact**: Simplify 40+ table/panel creations

---

### 5. Service Manager Facade

**Current State**: Direct service manager calls throughout
- Inconsistent method calling
- Repeated error handling
- No centralized service access

**Recommendation**: Create service facade

```python
# cli_modules/services/service_facade.py
class ServiceFacade:
    """Simplified interface to service manager."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.service_manager = get_cli_service_manager(config_dir)
    
    def list_targets(self) -> List[BackupTarget]:
        """List backup targets with error handling."""
        method = _get_service_method(self.service_manager, "list_backup_targets")
        if not method:
            raise ServiceNotAvailableError("Target listing not available")
        return method() or []
    
    def get_target(self, name: str) -> BackupTarget:
        """Get target by name with fallback logic."""
        # Try multiple methods with fallback
        pass
    
    def add_target(self, target: BackupTarget) -> bool:
        """Add target with validation."""
        pass
    
    # Similar methods for repos, snapshots, etc.
```

**Benefits**:
- Cleaner command code
- Consistent error handling
- Single place for service method resolution
- Easier to mock

**Estimated Impact**: Simplify all command implementations

---

### 6. Validation Framework

**Current State**: Validation scattered and inconsistent
- Some commands validate, others don't
- Inconsistent error messages
- Repeated validation logic

**Recommendation**: Create validation framework

```python
# cli_modules/validation/validators.py
class Validator:
    """Base validator."""
    
    def validate(self, value: Any) -> ValidationResult:
        raise NotImplementedError

class RepositoryNameValidator(Validator):
    """Validate repository names."""
    pass

class SnapshotIdValidator(Validator):
    """Validate snapshot IDs."""
    pass

class PathValidator(Validator):
    """Validate file paths."""
    pass

# cli_modules/validation/validation_chain.py
class ValidationChain:
    """Chain multiple validators."""
    
    def __init__(self):
        self.validators = []
    
    def add(self, validator: Validator) -> 'ValidationChain':
        self.validators.append(validator)
        return self
    
    def validate(self, value: Any) -> ValidationResult:
        for validator in self.validators:
            result = validator.validate(value)
            if not result.is_valid:
                return result
        return ValidationResult(True)
```

**Benefits**:
- Consistent validation across commands
- Reusable validators
- Better error messages
- Easier to test

**Estimated Impact**: Improve validation in 50+ locations

---

### 7. Progress Tracking Service

**Current State**: Progress bars created ad-hoc
- Inconsistent progress display
- Repeated Progress context manager setup
- No centralized progress tracking

**Recommendation**: Create progress service

```python
# cli_modules/services/progress_service.py
class ProgressService:
    """Centralized progress tracking."""
    
    def __init__(self, console: Console = console):
        self.console = console
        self._progress = None
    
    def __enter__(self):
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console,
        )
        self._progress.__enter__()
        return self
    
    def __exit__(self, *args):
        if self._progress:
            self._progress.__exit__(*args)
    
    def task(self, description: str, total: Optional[int] = None):
        """Add a task."""
        return self._progress.add_task(description, total=total)
    
    def update(self, task_id, **kwargs):
        """Update task."""
        self._progress.update(task_id, **kwargs)
```

**Benefits**:
- Consistent progress display
- Easier to customize globally
- Better for testing (can disable)
- Cleaner command code

**Estimated Impact**: Simplify 10+ progress bar usages

---

### 8. Error Context Manager

**Current State**: Error handling improved by Phase 3, but could be better
- Some errors lose context
- Stack traces not always helpful
- Error recovery not standardized

**Recommendation**: Create error context manager

```python
# cli_modules/error_handling/context.py
class ErrorContext:
    """Provide context for errors."""
    
    def __init__(self, operation: str):
        self.operation = operation
        self.context = {}
    
    def add(self, key: str, value: Any):
        """Add context information."""
        self.context[key] = value
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Add context to exception
            if hasattr(exc_val, 'add_note'):
                exc_val.add_note(f"Operation: {self.operation}")
                for key, value in self.context.items():
                    exc_val.add_note(f"{key}: {value}")
        return False

# Usage
with ErrorContext("backup creation").add("repository", repo_name).add("target", target_name):
    # operation
    pass
```

**Benefits**:
- Better error messages
- Easier debugging
- Context preserved through call stack
- Consistent error reporting

**Estimated Impact**: Improve error handling in all commands

---

### 9. Command Registry Pattern

**Current State**: Commands registered manually
- No centralized command list
- Hard to discover all commands
- No metadata about commands

**Recommendation**: Create command registry

```python
# cli_modules/registry/command_registry.py
class CommandRegistry:
    """Central registry of all commands."""
    
    def __init__(self):
        self.commands = {}
    
    def register(
        self,
        name: str,
        func: Callable,
        group: str,
        description: str,
        tags: List[str] = None
    ):
        """Register a command."""
        self.commands[name] = CommandInfo(
            name=name,
            func=func,
            group=group,
            description=description,
            tags=tags or []
        )
    
    def get_by_tag(self, tag: str) -> List[CommandInfo]:
        """Get commands by tag."""
        return [cmd for cmd in self.commands.values() if tag in cmd.tags]
    
    def get_by_group(self, group: str) -> List[CommandInfo]:
        """Get commands by group."""
        return [cmd for cmd in self.commands.values() if cmd.group == group]

# Usage with decorator
@command_registry.register(group="targets", tags=["management", "list"])
@targets_app.command("list")
def targets_list(...):
    pass
```

**Benefits**:
- Centralized command metadata
- Easy to generate documentation
- Command discovery
- Plugin system foundation

**Estimated Impact**: Enable future extensibility

---

### 10. Testing Utilities

**Current State**: Tests likely duplicate setup code
- No shared test fixtures
- Repeated mocking
- Inconsistent test patterns

**Recommendation**: Create test utilities

```python
# cli_modules/testing/fixtures.py
class CLITestFixture:
    """Base fixture for CLI tests."""
    
    def __init__(self):
        self.runner = CliRunner()
        self.mock_service_manager = Mock()
        self.mock_config = Mock()
    
    def invoke(self, command: List[str], **kwargs):
        """Invoke command with standard setup."""
        return self.runner.invoke(app, command, **kwargs)
    
    def assert_success(self, result):
        """Assert command succeeded."""
        assert result.exit_code == 0
    
    def assert_error(self, result, message: str = None):
        """Assert command failed."""
        assert result.exit_code != 0
        if message:
            assert message in result.output

# cli_modules/testing/mocks.py
class MockServiceManager:
    """Mock service manager for testing."""
    pass

class MockRepository:
    """Mock repository for testing."""
    pass
```

**Benefits**:
- Faster test writing
- Consistent test patterns
- Easier to maintain tests
- Better test coverage

**Estimated Impact**: Improve test suite maintainability

---

### 11. Async Command Support

**Current State**: All commands synchronous
- Long operations block
- No cancellation support
- Poor UX for slow operations

**Recommendation**: Add async support

```python
# cli_modules/commands/async_base.py
class AsyncCommandBase(CommandBase):
    """Base for async commands."""
    
    @staticmethod
    async def async_setup(verbose: bool = False, config_dir: Optional[Path] = None):
        """Async setup."""
        pass

def async_command(func):
    """Decorator to run async commands."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

# Usage
@backup_app.command("create")
@async_command
async def backup_create_async(...):
    async with ProgressService() as progress:
        await backup_service.create_backup(...)
```

**Benefits**:
- Better responsiveness
- Cancellation support
- Parallel operations
- Modern async patterns

**Estimated Impact**: Improve UX for long operations

---

### 12. Plugin System for Commands

**Current State**: Commands hardcoded
- Can't extend without modifying code
- No third-party command support
- Monolithic structure

**Recommendation**: Create command plugin system

```python
# cli_modules/plugins/command_plugin.py
class CommandPlugin:
    """Base class for command plugins."""
    
    def register_commands(self, app: typer.Typer):
        """Register commands with app."""
        raise NotImplementedError
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        raise NotImplementedError

# cli_modules/plugins/loader.py
class PluginLoader:
    """Load and register command plugins."""
    
    def load_plugins(self, plugin_dir: Path):
        """Load plugins from directory."""
        pass
    
    def register_all(self, app: typer.Typer):
        """Register all loaded plugins."""
        pass
```

**Benefits**:
- Extensible architecture
- Third-party commands
- Modular features
- Better separation

**Estimated Impact**: Enable ecosystem growth

---

## Priority Recommendations

### High Priority (Do Next)

1. **Configuration Management Consolidation** - Immediate benefit, reduces complexity
2. **Repository Resolution Service** - Eliminates major duplication
3. **Service Manager Facade** - Simplifies all commands

### Medium Priority (After Phase 2)

4. **Interactive Prompt Service** - Improves consistency
5. **Output Formatting Service** - Better UX
6. **Validation Framework** - Improves reliability

### Low Priority (Future)

7. **Progress Tracking Service** - Nice to have
8. **Error Context Manager** - Incremental improvement
9. **Command Registry Pattern** - Enables future features
10. **Testing Utilities** - Improves test maintainability
11. **Async Command Support** - Modern architecture
12. **Plugin System** - Long-term extensibility

## Estimated Impact

| Refactoring | Lines Saved | Complexity Reduced | Maintainability Gain |
|-------------|-------------|-------------------|---------------------|
| Config Consolidation | ~100 | High | High |
| Repository Resolver | ~200 | High | High |
| Service Facade | ~150 | Medium | High |
| Prompt Service | ~80 | Medium | Medium |
| Output Formatter | ~120 | Medium | Medium |
| Validation Framework | ~100 | Medium | High |
| **Total** | **~750** | **High** | **High** |

## Implementation Strategy

### Phase 4: Service Layer (Recommended Next)

1. Create ConfigService
2. Create RepositoryResolver
3. Create ServiceFacade
4. Update commands to use new services

**Estimated Time**: 2-3 days  
**Estimated Savings**: ~450 lines, significant complexity reduction

### Phase 5: UX Improvements

1. Create PromptService
2. Create OutputFormatter
3. Create ProgressService
4. Update commands to use new services

**Estimated Time**: 2 days  
**Estimated Savings**: ~220 lines, better UX

### Phase 6: Quality & Extensibility

1. Create ValidationFramework
2. Create ErrorContext
3. Create CommandRegistry
4. Create TestingUtilities

**Estimated Time**: 2-3 days  
**Benefits**: Better quality, easier testing

### Phase 7: Advanced Features (Optional)

1. Async support
2. Plugin system

**Estimated Time**: 3-5 days  
**Benefits**: Modern architecture, extensibility

## Total Potential Impact

**Current Refactoring** (Phases 1-3):
- Lines saved: ~1,770
- Modules created: 8
- Patterns established: Base classes, decorators

**Additional Refactoring** (Phases 4-7):
- Additional lines saved: ~750-1,000
- Additional complexity reduction: High
- New capabilities: Services, validation, plugins

**Combined Total**:
- **~2,500-2,770 lines saved** (43-48% reduction)
- **Significantly reduced complexity**
- **Modern, extensible architecture**
- **Better testing and maintainability**

## Conclusion

The three-phase refactoring provides a solid foundation, but there are significant additional opportunities to:

1. **Reduce duplication** through service layers
2. **Improve consistency** through centralized services
3. **Enhance UX** through better prompts and output
4. **Increase quality** through validation and error handling
5. **Enable extensibility** through plugins and registries

Recommend implementing **Phase 4 (Service Layer)** next for maximum immediate benefit.

---

**Next Steps**: Review and prioritize these recommendations based on project needs and timeline.
