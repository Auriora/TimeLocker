# ServiceFacade Implementation

**Status**: Implemented  
**Version**: 1.0.0  
**Last Updated**: 2025-11-12

## Overview

The ServiceFacade provides a simplified interface for accessing TimeLocker services from CLI commands. It reduces code duplication, provides consistent error handling, and simplifies service initialization.

## Purpose

The ServiceFacade addresses several pain points in CLI command development:

1. **Code Duplication**: Commands repeatedly initialize and access services
2. **Inconsistent Error Handling**: Different commands handle service errors differently
3. **Complex Initialization**: Service initialization requires multiple steps and checks
4. **Fallback Logic**: Commands need to handle fallbacks when services aren't available
5. **Service Discovery**: Commands need to know which services are available

## Architecture

```
┌─────────────────────────────────────────┐
│         CLI Commands                     │
│  (backup, restore, repository, etc.)    │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         ServiceFacade                    │
│  - Lazy initialization                   │
│  - Service caching                       │
│  - Error handling                        │
│  - Health checking                       │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      CLIServiceManager                   │
│  - Service orchestration                 │
│  - Dependency injection                  │
│  - Event bus integration                 │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│      Individual Services                 │
│  (Repository, Snapshot, Config, etc.)   │
└─────────────────────────────────────────┘
```

## Key Features

### 1. Simplified Service Access

**Before (without ServiceFacade):**
```python
def my_command(config_dir: Optional[Path] = None):
    # Multiple initialization steps
    setup_logging(verbose, config_dir)
    service_manager = _get_service_manager_for_command(config_dir)
    
    # Check if service manager exists
    if not service_manager:
        show_error_panel("Error", "Service manager not available")
        raise typer.Exit(1)
    
    # Initialize services
    if hasattr(service_manager, 'initialize_services'):
        service_manager.initialize_services()
    
    # Get repository service with error checking
    if not hasattr(service_manager, 'repository_service'):
        show_error_panel("Error", "Repository service not available")
        raise typer.Exit(1)
    
    repo_service = service_manager.repository_service
    if repo_service is None:
        show_error_panel("Error", "Repository service not initialized")
        raise typer.Exit(1)
    
    # Finally use the service
    result = repo_service.check_repository(repo)
```

**After (with ServiceFacade):**
```python
def my_command(config_dir: Optional[Path] = None):
    try:
        # Single line setup
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Direct access with automatic error handling
        repo_service = facade.get_repository_service()
        result = repo_service.check_repository(repo)
        
    except ServiceAccessError as e:
        show_error_panel("Service Error", str(e))
        raise typer.Exit(1)
```

### 2. Lazy Initialization

Services are only initialized when first accessed:

```python
facade = ServiceFacade(config_dir=config_dir)

# Service manager not created yet
# ...

# Service manager created and initialized on first access
repo_service = facade.get_repository_service()

# Subsequent calls use cached service
repo_service2 = facade.get_repository_service()  # Returns cached instance
```

### 3. Consistent Error Handling

ServiceFacade provides specific exception types:

- `ServiceInitializationError`: Service initialization failed
- `ServiceAccessError`: Service access failed
- `ServiceFacadeError`: Base exception for all facade errors

```python
try:
    facade = ServiceFacade(config_dir=config_dir)
    service = facade.get_backup_service()
except ServiceInitializationError as e:
    # Handle initialization errors
    logger.error(f"Failed to initialize services: {e}")
except ServiceAccessError as e:
    # Handle service access errors
    logger.error(f"Failed to access service: {e}")
```

### 4. Automatic Fallbacks

ServiceFacade handles fallbacks automatically:

```python
# Tries configuration_service first, falls back to config_module
config_service = facade.get_configuration_service()

# Tries restore_service, then recovery_orchestrator
restore_service = facade.get_restore_service()
```

### 5. Health Checking

```python
facade = ServiceFacade(config_dir=config_dir)

# Check health of all services
health_status = facade.health_check()
# Returns: {'repository': True, 'snapshot': True, 'configuration': True}

# Get detailed status
status = facade.get_service_status()
# Returns detailed information about each service
```

## API Reference

### ServiceFacade Class

#### Constructor

```python
ServiceFacade(
    service_manager: Optional[Any] = None,
    config_dir: Optional[Path] = None
)
```

**Parameters:**
- `service_manager`: Optional CLIServiceManager instance
- `config_dir`: Optional configuration directory path

#### Service Access Methods

##### get_backup_service()
```python
def get_backup_service() -> Any
```
Returns the backup orchestrator service.

**Raises:**
- `ServiceAccessError`: If backup service cannot be accessed

##### get_restore_service()
```python
def get_restore_service() -> Any
```
Returns the restore/recovery service.

**Raises:**
- `ServiceAccessError`: If restore service cannot be accessed

##### get_repository_service()
```python
def get_repository_service() -> Any
```
Returns the repository service.

**Raises:**
- `ServiceAccessError`: If repository service cannot be accessed

##### get_snapshot_service()
```python
def get_snapshot_service() -> Any
```
Returns the snapshot service.

**Raises:**
- `ServiceAccessError`: If snapshot service cannot be accessed

##### get_configuration_service()
```python
def get_configuration_service() -> Any
```
Returns the configuration service (with fallback to config_module).

**Raises:**
- `ServiceAccessError`: If configuration service cannot be accessed

##### get_repository_factory()
```python
def get_repository_factory() -> Any
```
Returns the repository factory.

**Raises:**
- `ServiceAccessError`: If repository factory cannot be accessed

##### get_monitoring_service()
```python
def get_monitoring_service() -> Optional[Any]
```
Returns the monitoring service (optional, returns None if not available).

##### get_security_service()
```python
def get_security_service() -> Any
```
Returns the security service.

**Raises:**
- `ServiceAccessError`: If security service cannot be accessed

#### Management Methods

##### initialize_services()
```python
def initialize_services() -> bool
```
Explicitly initialize all services.

**Returns:** True if initialization successful

**Raises:**
- `ServiceInitializationError`: If initialization fails

##### health_check()
```python
def health_check() -> Dict[str, bool]
```
Check health status of all services.

**Returns:** Dictionary mapping service names to health status

##### get_service_status()
```python
def get_service_status() -> Dict[str, Dict[str, Any]]
```
Get comprehensive status information for all services.

**Returns:** Dictionary with detailed service status information

##### shutdown_services()
```python
def shutdown_services() -> None
```
Shutdown all services and clean up resources.

#### Properties

##### service_manager
```python
@property
def service_manager(self) -> Any
```
Get the underlying service manager (for backward compatibility).

##### config_dir
```python
@property
def config_dir(self) -> Optional[Path]
```
Get the configuration directory.

### Factory Function

```python
def create_service_facade(
    config_dir: Optional[Path] = None,
    service_manager: Optional[Any] = None
) -> ServiceFacade
```

Factory function to create a ServiceFacade instance.

## Usage Examples

### Example 1: Basic Service Access

```python
from TimeLocker.utils.service_facade import ServiceFacade

def check_repository(repository_name: str, config_dir: Optional[Path] = None):
    """Check repository health using ServiceFacade."""
    try:
        # Create facade
        facade = ServiceFacade(config_dir=config_dir)
        
        # Get services
        repo_service = facade.get_repository_service()
        repo_factory = facade.get_repository_factory()
        
        # Create repository instance
        repo = repo_factory.create_repository(repository_name)
        
        # Check repository
        result = repo_service.check_repository(repo)
        
        return result
        
    except ServiceAccessError as e:
        logger.error(f"Failed to access service: {e}")
        raise
```

### Example 2: Using CommandBase Helper

```python
from .base import CommandBase

@repos_app.command("check")
def check_repository(
    repository: str,
    verbose: bool = False,
    config_dir: Optional[Path] = None
):
    """Check repository using ServiceFacade."""
    try:
        # Use CommandBase helper for setup
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Access services directly
        repo_service = facade.get_repository_service()
        repo_factory = facade.get_repository_factory()
        
        # Perform operation
        repo = repo_factory.create_repository(repository)
        result = repo_service.check_repository(repo)
        
        # Display results
        if result['status'] == 'success':
            show_success_panel("Check Complete", f"Repository {repository} is healthy")
        else:
            show_error_panel("Check Failed", f"Repository {repository} has errors")
            
    except ServiceAccessError as e:
        show_error_panel("Service Error", str(e))
        raise typer.Exit(1)
```

### Example 3: Health Monitoring

```python
@monitor_app.command("health")
def health_check(
    verbose: bool = False,
    config_dir: Optional[Path] = None
):
    """Check health of all services."""
    try:
        facade = CommandBase.setup_with_facade(verbose, config_dir)
        
        # Get health status
        health_status = facade.health_check()
        
        # Display results
        table = Table(title="Service Health Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        
        for service_name, is_healthy in health_status.items():
            status = "✓ Healthy" if is_healthy else "✗ Unhealthy"
            style = "green" if is_healthy else "red"
            table.add_row(service_name, f"[{style}]{status}[/{style}]")
        
        console.print(table)
        
    except ServiceInitializationError as e:
        show_error_panel("Initialization Error", str(e))
        raise typer.Exit(1)
```

## Benefits

### Code Reduction

ServiceFacade reduces service access code by approximately **120 lines** across 50+ commands:

- **Before**: ~15-20 lines per command for service initialization and access
- **After**: ~3-5 lines per command using ServiceFacade

### Consistency

All commands use the same pattern for service access:

```python
facade = CommandBase.setup_with_facade(verbose, config_dir)
service = facade.get_<service_name>()
```

### Error Handling

Specific exception types make error handling more precise:

```python
try:
    facade = ServiceFacade(config_dir=config_dir)
    service = facade.get_backup_service()
except ServiceInitializationError:
    # Handle initialization errors
    pass
except ServiceAccessError:
    # Handle service access errors
    pass
```

### Maintainability

Changes to service initialization only need to be made in ServiceFacade, not in every command.

## Testing

ServiceFacade includes comprehensive unit tests:

```bash
pytest tests/TimeLocker/utils/test_service_facade.py -v
```

Test coverage includes:
- Service initialization
- Service access and caching
- Error handling
- Health checking
- Fallback mechanisms
- Service shutdown

## Migration Guide

### Step 1: Update Imports

```python
# Add ServiceFacade import
from TimeLocker.utils.service_facade import ServiceFacade, ServiceAccessError
```

### Step 2: Replace Setup Code

**Before:**
```python
setup_logging(verbose, config_dir)
service_manager = _get_service_manager_for_command(config_dir)
```

**After:**
```python
facade = CommandBase.setup_with_facade(verbose, config_dir)
```

### Step 3: Replace Service Access

**Before:**
```python
if not service_manager:
    show_error_panel("Error", "Service manager not available")
    raise typer.Exit(1)

if hasattr(service_manager, 'repository_service'):
    repo_service = service_manager.repository_service
else:
    show_error_panel("Error", "Repository service not available")
    raise typer.Exit(1)
```

**After:**
```python
try:
    repo_service = facade.get_repository_service()
except ServiceAccessError as e:
    show_error_panel("Service Error", str(e))
    raise typer.Exit(1)
```

### Step 4: Update Error Handling

Add specific exception handling for ServiceFacade exceptions:

```python
try:
    facade = CommandBase.setup_with_facade(verbose, config_dir)
    service = facade.get_repository_service()
    # ... use service
except ServiceInitializationError as e:
    show_error_panel("Initialization Error", str(e))
    raise typer.Exit(1)
except ServiceAccessError as e:
    show_error_panel("Service Error", str(e))
    raise typer.Exit(1)
```

## Performance Considerations

### Service Caching

Services are cached after first access, reducing overhead:

```python
facade = ServiceFacade(config_dir=config_dir)

# First call: creates and caches service
service1 = facade.get_repository_service()  # ~5ms

# Subsequent calls: returns cached service
service2 = facade.get_repository_service()  # <1ms
```

### Lazy Initialization

Service manager is only created when first service is accessed:

```python
# No overhead yet
facade = ServiceFacade(config_dir=config_dir)

# Service manager created on first access
service = facade.get_repository_service()
```

## Requirements Addressed

The ServiceFacade implementation addresses the following requirements from the CLI Refactoring specification:

- **Requirement 3.1**: ServiceFacade provides simplified access to all TimeLocker services
- **Requirement 3.2**: ServiceFacade initializes services lazily and provides health checking
- **Requirement 3.3**: ServiceFacade reduces service access code by at least 120 lines
- **Requirement 3.4**: ServiceFacade maintains backward compatibility with direct service manager access
- **Requirement 3.5**: ServiceFacade provides detailed error context and recovery options

## Future Enhancements

Potential future improvements:

1. **Service Discovery**: Automatic discovery of available services
2. **Service Metrics**: Track service access patterns and performance
3. **Service Mocking**: Built-in support for testing with mock services
4. **Service Validation**: Validate service compatibility and versions
5. **Service Lifecycle**: More granular control over service lifecycle

## Related Documentation

- [Active CLI Consolidation Spec](../specs/001-cli-consolidation-stabilization/requirements.md)
