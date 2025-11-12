# CLI Refactoring Design

## Architecture Overview

The CLI refactoring introduces a layered architecture to reduce duplication and improve maintainability:

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Commands                          │
│  (backup, restore, repository, selections, etc.)        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Service Layer (Phase 4)                 │
│  ConfigService │ RepositoryResolver │ ServiceFacade     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                UX Components (Phase 5)                   │
│  PromptService │ OutputFormatter │ ProgressService      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           Quality Infrastructure (Phase 6)               │
│  ValidationFramework │ ErrorContext │ CommandRegistry   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Core Services (Existing)                    │
│  ServiceManager │ ConfigManager │ RepositoryManager     │
└─────────────────────────────────────────────────────────┘
```

## Component Design

See tasks.md for detailed implementation tasks.

### Phase 4: Service Layer

#### ConfigService

**Purpose**: Centralize configuration access and eliminate duplication

**Interface**:
```python
class ConfigService:
    def get_config(self) -> Config
    def get_repository_config(self, name: str) -> RepositoryConfig
    def get_policy_config(self, name: str) -> PolicyConfig
    def validate_config(self) -> ValidationResult
    def reload_config(self) -> None
```

**Benefits**:
- Single source of truth for configuration
- Consistent validation
- Configuration caching
- Change notifications

**Impact**: ~150 lines saved across 40+ commands

#### RepositoryResolver

**Purpose**: Centralize repository resolution and credential handling

**Interface**:
```python
class RepositoryResolver:
    def resolve_repository(self, name_or_path: str) -> Repository
    def resolve_credentials(self, repository: Repository) -> Credentials
    def detect_backend(self, path: str) -> BackendType
    def validate_repository(self, repository: Repository) -> ValidationResult
```

**Benefits**:
- Unified resolution logic
- Credential chain handling
- Backend detection
- Repository caching

**Impact**: ~180 lines saved across 30+ commands

#### ServiceFacade

**Purpose**: Simplify service manager access

**Interface**:
```python
class ServiceFacade:
    def get_backup_service(self) -> BackupService
    def get_restore_service(self) -> RestoreService
    def get_repository_service(self) -> RepositoryService
    def initialize_services(self) -> None
    def health_check(self) -> HealthStatus
```

**Benefits**:
- Simplified service access
- Consistent error handling
- Service initialization helpers
- Health checking

**Impact**: ~120 lines saved across 50+ commands

### Phase 5: UX Components

#### PromptService

**Purpose**: Centralize interactive prompts

**Interface**:
```python
class PromptService:
    def prompt_text(self, message: str, default: str = None) -> str
    def prompt_choice(self, message: str, choices: List[str]) -> str
    def prompt_confirm(self, message: str, default: bool = False) -> bool
    def prompt_password(self, message: str) -> str
```

**Benefits**:
- Consistent prompts
- Non-interactive handling
- Validation patterns
- Reusable templates

**Impact**: ~80 lines saved across 25+ commands

#### OutputFormatter

**Purpose**: Standardize output formatting

**Interface**:
```python
class OutputFormatter:
    def format_table(self, data: List[Dict], columns: List[str]) -> str
    def format_panel(self, title: str, content: str) -> str
    def format_json(self, data: Any) -> str
    def format_error(self, error: Exception) -> str
```

**Benefits**:
- Consistent styling
- JSON output support
- Output templates
- Error formatting

**Impact**: ~70 lines saved across 35+ commands

#### ProgressService

**Purpose**: Centralize progress tracking

**Interface**:
```python
class ProgressService:
    def create_progress(self, total: int, description: str) -> Progress
    def update_progress(self, progress: Progress, advance: int) -> None
    def complete_progress(self, progress: Progress) -> None
    def with_progress(self, total: int, description: str) -> ContextManager
```

**Benefits**:
- Consistent display
- Progress context management
- Operation templates
- Nested progress support

**Impact**: ~70 lines saved across 20+ commands

### Phase 6: Quality Infrastructure

#### ValidationFramework

**Purpose**: Provide reusable validators

**Interface**:
```python
class Validator:
    def validate(self, value: Any) -> ValidationResult

class PathValidator(Validator):
    def validate(self, path: str) -> ValidationResult

class NameValidator(Validator):
    def validate(self, name: str) -> ValidationResult

class CompositeValidator(Validator):
    def __init__(self, validators: List[Validator])
    def validate(self, value: Any) -> ValidationResult
```

**Benefits**:
- Reusable validation logic
- Composable validators
- Consistent error messages
- Better code quality

**Impact**: Eliminates duplication in 40+ commands

#### ErrorContext

**Purpose**: Improve error messages with context

**Interface**:
```python
class ErrorContext:
    def add_context(self, key: str, value: Any) -> None
    def get_context(self) -> Dict[str, Any]
    def format_error(self, error: Exception) -> str
    def suggest_recovery(self, error: Exception) -> List[str]
```

**Benefits**:
- Context preservation
- Better error messages
- Recovery suggestions
- Debugging support

**Impact**: Better debugging experience

#### CommandRegistry

**Purpose**: Enable command discovery and plugins

**Interface**:
```python
class CommandRegistry:
    def register_command(self, command: Command) -> None
    def get_command(self, name: str) -> Command
    def list_commands(self) -> List[Command]
    def discover_plugins(self) -> List[Plugin]
```

**Benefits**:
- Command metadata management
- Dynamic discovery
- Plugin foundation
- Extensibility

**Impact**: Plugin-ready architecture

#### TestingUtilities

**Purpose**: Simplify test creation

**Interface**:
```python
class TestFixtures:
    def create_mock_config(self) -> Config
    def create_mock_repository(self) -> Repository
    def create_mock_service_manager(self) -> ServiceManager

class TestAssertions:
    def assert_command_success(self, result: Result) -> None
    def assert_command_error(self, result: Result, error_type: Type) -> None
```

**Benefits**:
- Shared test fixtures
- Mock factories
- Test data generators
- Assertion helpers

**Impact**: Easier testing

### Phase 7: Advanced Features (Optional)

#### Async Support

**Purpose**: Enable concurrent operations

**Interface**:
```python
class AsyncCommandBase(CommandBase):
    async def execute_async(self, **kwargs) -> Result

class AsyncProgressService:
    async def with_progress_async(self, total: int) -> AsyncContextManager
```

**Benefits**:
- Concurrent operations
- Better I/O performance
- Cancellation support
- Future scalability

**Impact**: Performance improvements for I/O-heavy operations

#### Plugin System

**Purpose**: Allow third-party commands

**Interface**:
```python
class CommandPlugin:
    def get_name(self) -> str
    def get_commands(self) -> List[Command]
    def initialize(self, context: PluginContext) -> None

class PluginLoader:
    def discover_plugins(self, path: str) -> List[Plugin]
    def load_plugin(self, plugin: Plugin) -> None
    def validate_plugin(self, plugin: Plugin) -> ValidationResult
```

**Benefits**:
- Third-party extensibility
- Plugin validation
- Sandboxing
- Lifecycle management

**Impact**: Complete plugin ecosystem

## Migration Strategy

### Incremental Approach

1. **Create New Components**: Build alongside existing code
2. **Update Commands Incrementally**: One command at a time
3. **Parallel Testing**: Run old and new side-by-side
4. **Remove Old Patterns**: After validation

### Backward Compatibility

- All existing commands work unchanged
- Configuration files remain compatible
- CLI interface stays stable
- Error messages backward compatible

### Testing Strategy

- Unit tests for each component
- Integration tests for interactions
- Performance benchmarks
- User acceptance tests

## Performance Considerations

### Service Layer Overhead
- Target: < 5ms per operation
- Caching for repeated operations
- Lazy initialization where possible

### Memory Usage
- No significant increase
- Efficient caching strategies
- Resource cleanup

### Startup Time
- No degradation
- Lazy loading of services
- Optimized imports

## Security Considerations

- No new security risks introduced
- Credential handling remains secure
- Plugin sandboxing (Phase 7)
- Audit logging maintained
