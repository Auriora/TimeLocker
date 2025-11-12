# CLI Service Layer Migration Guide

**Document Type**: Developer Guide  
**Audience**: TimeLocker Developers  
**Status**: Active  
**Last Updated**: 2025-11-12

## Overview

This guide helps developers migrate existing CLI commands to use the new service layer components introduced in Phase 4 of the CLI refactoring project.

## What Changed

The CLI refactoring introduces three new components:

1. **ConfigurationService** - Centralized configuration access
2. **RepositoryResolver** - Unified repository resolution
3. **ServiceFacade** - Simplified service access

These components reduce code duplication and provide consistent patterns across all CLI commands.

## Migration Steps

### Step 1: Update Imports

**Before**:
```python
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.config import ConfigurationModule
```

**After**:
```python
from TimeLocker.utils.service_facade import create_service_facade
from TimeLocker.utils.repository_resolver import resolve_repository_uri
```

### Step 2: Replace Service Manager Access

**Before**:
```python
def my_command():
    service_manager = get_cli_service_manager()
    service_manager.initialize_services()
    
    repo_service = service_manager.repository_service
    snapshot_service = service_manager.snapshot_service
    
    # Use services...
    
    service_manager.shutdown_services()
```

**After**:
```python
def my_command():
    facade = create_service_facade()
    
    try:
        repo_service = facade.get_repository_service()
        snapshot_service = facade.get_snapshot_service()
        
        # Use services...
        
    finally:
        facade.shutdown_services()
```

### Step 3: Replace Configuration Access

**Before**:
```python
def get_repository_config(name: str):
    config_module = ConfigurationModule()
    config = config_module.get_config()
    
    if name in config.repositories:
        return config.repositories[name]
    else:
        raise ValueError(f"Repository '{name}' not found")
```

**After**:
```python
def get_repository_config(name: str):
    facade = create_service_facade()
    config_service = facade.get_configuration_service()
    
    return config_service.get_repository_by_name(name)
```

### Step 4: Replace Repository Resolution

**Before**:
```python
def resolve_repo(name_or_uri: str):
    config_module = ConfigurationModule()
    config = config_module.get_config()
    
    # Check if it's a URI
    if "://" in name_or_uri or name_or_uri.startswith("/"):
        return name_or_uri
    
    # Try to resolve as name
    if name_or_uri in config.repositories:
        return config.repositories[name_or_uri].location
    
    # Assume it's a URI
    return name_or_uri
```

**After**:
```python
def resolve_repo(name_or_uri: str):
    return resolve_repository_uri(name_or_uri)
```

## Common Patterns

### Pattern 1: Command with Repository Access

**Before**:
```python
@app.command()
def list_snapshots(repository: str):
    """List snapshots in repository"""
    service_manager = get_cli_service_manager()
    service_manager.initialize_services()
    
    try:
        # Resolve repository
        config_module = ConfigurationModule()
        config = config_module.get_config()
        
        if repository in config.repositories:
            repo_uri = config.repositories[repository].location
        else:
            repo_uri = repository
        
        # Get service
        snapshot_service = service_manager.snapshot_service
        
        # List snapshots
        snapshots = snapshot_service.list_snapshots(repo_uri)
        
        for snapshot in snapshots:
            print(f"{snapshot.id}: {snapshot.time}")
            
    finally:
        service_manager.shutdown_services()
```

**After**:
```python
@app.command()
def list_snapshots(repository: str):
    """List snapshots in repository"""
    facade = create_service_facade()
    
    try:
        # Resolve repository
        repo_uri = resolve_repository_uri(repository)
        
        # Get service
        snapshot_service = facade.get_snapshot_service()
        
        # List snapshots
        snapshots = snapshot_service.list_snapshots(repo_uri)
        
        for snapshot in snapshots:
            print(f"{snapshot.id}: {snapshot.time}")
            
    finally:
        facade.shutdown_services()
```

**Benefits**:
- 8 lines reduced to 3 lines for repository resolution
- Consistent error handling
- Cleaner code

### Pattern 2: Configuration Management

**Before**:
```python
@app.command()
def add_repository(name: str, uri: str, description: str = ""):
    """Add a new repository"""
    config_module = ConfigurationModule()
    config = config_module.get_config()
    
    # Check if exists
    if name in config.repositories:
        raise ValueError(f"Repository '{name}' already exists")
    
    # Add repository
    from TimeLocker.config.configuration_schema import RepositoryConfig
    repo_config = RepositoryConfig(
        location=uri,
        description=description
    )
    config.repositories[name] = repo_config
    
    # Save configuration
    config_module.save_config(config)
    
    print(f"Repository '{name}' added successfully")
```

**After**:
```python
@app.command()
def add_repository(name: str, uri: str, description: str = ""):
    """Add a new repository"""
    facade = create_service_facade()
    config_service = facade.get_configuration_service()
    
    try:
        # Add repository
        config_service.add_repository({
            "name": name,
            "uri": uri,
            "location": uri,
            "description": description
        })
        
        # Save configuration
        config_service.save_configuration(config_service._config_data)
        
        print(f"Repository '{name}' added successfully")
        
    except Exception as e:
        print(f"Failed to add repository: {e}")
    finally:
        facade.shutdown_services()
```

**Benefits**:
- Automatic validation
- Consistent error messages
- Simpler API

### Pattern 3: Multiple Service Access

**Before**:
```python
@app.command()
def backup_and_verify(repository: str, paths: list[str]):
    """Backup files and verify"""
    service_manager = get_cli_service_manager()
    service_manager.initialize_services()
    
    try:
        # Resolve repository
        config_module = ConfigurationModule()
        config = config_module.get_config()
        repo_uri = config.repositories.get(repository, {}).get('location', repository)
        
        # Get services
        backup_service = service_manager.backup_orchestrator
        snapshot_service = service_manager.snapshot_service
        
        # Perform backup
        result = backup_service.backup(repo_uri, paths)
        
        # Verify
        snapshots = snapshot_service.list_snapshots(repo_uri)
        latest = snapshots[0]
        
        print(f"Backup completed: {latest.id}")
        
    finally:
        service_manager.shutdown_services()
```

**After**:
```python
@app.command()
def backup_and_verify(repository: str, paths: list[str]):
    """Backup files and verify"""
    facade = create_service_facade()
    
    try:
        # Resolve repository
        repo_uri = resolve_repository_uri(repository)
        
        # Get services
        backup_service = facade.get_backup_service()
        snapshot_service = facade.get_snapshot_service()
        
        # Perform backup
        result = backup_service.backup(repo_uri, paths)
        
        # Verify
        snapshots = snapshot_service.list_snapshots(repo_uri)
        latest = snapshots[0]
        
        print(f"Backup completed: {latest.id}")
        
    finally:
        facade.shutdown_services()
```

**Benefits**:
- Cleaner service access
- Consistent patterns
- Better error handling

## Error Handling

### Before

```python
try:
    service_manager = get_cli_service_manager()
    service_manager.initialize_services()
    repo_service = service_manager.repository_service
except Exception as e:
    print(f"Failed to initialize: {e}")
    return
```

### After

```python
from TimeLocker.utils.service_facade import ServiceInitializationError, ServiceAccessError

try:
    facade = create_service_facade()
    repo_service = facade.get_repository_service()
except ServiceInitializationError as e:
    print(f"Service initialization failed: {e}")
    return
except ServiceAccessError as e:
    print(f"Service not available: {e}")
    return
```

**Benefits**:
- Specific exception types
- Better error messages
- Easier debugging

## Testing

### Before

```python
def test_my_command(mocker):
    """Test command with mocked services"""
    mock_service_manager = mocker.Mock()
    mock_repo_service = mocker.Mock()
    mock_service_manager.repository_service = mock_repo_service
    
    mocker.patch('TimeLocker.cli_services.get_cli_service_manager', 
                 return_value=mock_service_manager)
    
    # Test command...
```

### After

```python
def test_my_command(mocker):
    """Test command with mocked services"""
    mock_facade = mocker.Mock()
    mock_repo_service = mocker.Mock()
    mock_facade.get_repository_service.return_value = mock_repo_service
    
    mocker.patch('TimeLocker.utils.service_facade.create_service_facade',
                 return_value=mock_facade)
    
    # Test command...
```

**Benefits**:
- Simpler mocking
- Consistent test patterns
- Better isolation

## Checklist

Use this checklist when migrating a command:

- [ ] Replace `get_cli_service_manager()` with `create_service_facade()`
- [ ] Replace direct service manager access with facade methods
- [ ] Replace manual repository resolution with `resolve_repository_uri()`
- [ ] Replace direct configuration access with `ConfigurationService`
- [ ] Add proper error handling with specific exception types
- [ ] Add `try/finally` block with `shutdown_services()`
- [ ] Update tests to use new mocking patterns
- [ ] Verify command still works correctly
- [ ] Check for any remaining code duplication

## Performance Impact

The service layer adds minimal overhead:

- Service access: < 5ms per operation
- Repository resolution: < 5ms per operation
- Configuration access: < 5ms per operation

Caching ensures subsequent accesses are even faster (< 1ms).

## Backward Compatibility

The service layer maintains backward compatibility:

- Old patterns still work
- No breaking changes to existing commands
- Gradual migration is supported
- Both patterns can coexist

## Examples

See these files for complete migration examples:

- `src/TimeLocker/cli_modules/commands/example_service_facade_usage.py` - ServiceFacade usage
- `tests/TimeLocker/integration/test_service_layer_integration.py` - Integration tests
- `tests/TimeLocker/utils/test_service_facade.py` - Unit tests

## Getting Help

If you encounter issues during migration:

1. Check the [Service Layer Integration Guide](../../3-implementation/service-layer-integration.md)
2. Review existing migrated commands for patterns
3. Run integration tests to verify behavior
4. Ask in the development channel

## See Also

- [Service Layer Integration Guide](../../3-implementation/service-layer-integration.md)
- [Service Facade Implementation](../../3-implementation/service-facade.md)
- [CLI Refactoring Design](../../../.kiro/specs/cli-refactoring/design.md)
