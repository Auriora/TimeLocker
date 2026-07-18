# Service Layer Integration Guide

**Document Type**: Implementation Guide  
**Status**: Active  
**Last Updated**: 2025-11-12  
**Related Spec**: [CLI Consolidation Stabilization](../specs/001-cli-consolidation-stabilization/requirements.md)

## Overview

The Service Layer provides centralized access to TimeLocker services, configuration, and repository resolution for CLI commands. This layer reduces code duplication and provides consistent error handling across all CLI commands.

## Components

### ConfigurationService

**Purpose**: Centralized configuration access with validation and caching

**Location**: `src/TimeLocker/services/configuration_service.py`

**Key Features**:
- Single source of truth for configuration
- Automatic validation on load/save
- Configuration caching for performance
- Support for repositories and backup targets

**Usage Example**:

```python
from TimeLocker.services.configuration_service import ConfigurationService
from pathlib import Path

# Initialize service
config_service = ConfigurationService(config_path=Path("config.json"))

# Get configuration values
app_name = config_service.get_config_value("general.app_name")
log_level = config_service.get_config_value("general.log_level", default="INFO")

# Get repositories
repos = config_service.get_repositories()
for repo in repos:
    print(f"{repo['name']}: {repo['location']}")

# Add a repository
config_service.add_repository({
    "name": "my-repo",
    "uri": "s3:bucket/path",
    "location": "s3:bucket/path",
    "description": "My S3 repository"
})

# Save configuration
config_service.save_configuration(config_service._config_data)
```

**API Reference**:

- `load_configuration(config_path)` - Load configuration from file
- `save_configuration(config, config_path)` - Save configuration to file
- `get_config_value(key, default)` - Get configuration value by key (supports dot notation)
- `set_config_value(key, value)` - Set configuration value
- `get_repositories()` - Get list of all repositories
- `get_repository_by_name(name)` - Get specific repository
- `add_repository(config)` - Add new repository
- `remove_repository(name)` - Remove repository
- `validate_configuration(config)` - Validate configuration structure

**Performance**:
- Configuration loading: < 100ms for 100 repositories
- Cached access: < 1ms per operation
- Validation overhead: < 10ms

### RepositoryResolver

**Purpose**: Centralized repository resolution and URI handling

**Location**: `src/TimeLocker/utils/repository_resolver.py`

**Key Features**:
- Resolves repository names to URIs
- Supports direct URI passthrough
- URI normalization (standard to restic format)
- Backend type detection
- Validation of repository identifiers

**Usage Example**:

```python
from TimeLocker.utils.repository_resolver import (
    resolve_repository_uri,
    get_repository_info,
    normalize_repository_uri,
    validate_repository_name_or_uri
)
from pathlib import Path

# Resolve repository name to URI
uri = resolve_repository_uri("production", config_dir=Path("/etc/timelocker"))
# Returns: "s3:s3.amazonaws.com/prod-bucket"

# Direct URI passthrough
uri = resolve_repository_uri("s3://bucket/path")
# Returns: "s3://bucket/path"

# Get repository information
info = get_repository_info("production", config_dir=Path("/etc/timelocker"))
# Returns: {
#     "uri": "s3:...",
#     "name": "production",
#     "description": "Production repository",
#     "type": "s3",
#     "is_named": True
# }

# Normalize URI format
normalized = normalize_repository_uri("s3://minio.lan/bucket")
# Returns: "s3:minio.lan/bucket"

# Validate repository identifier
validate_repository_name_or_uri("s3://bucket/path")  # OK
validate_repository_name_or_uri("/tmp/repo")  # Raises ValueError
```

**API Reference**:

- `resolve_repository_uri(name_or_uri, config_dir)` - Resolve name to URI or passthrough
- `get_repository_info(name_or_uri, config_dir)` - Get repository metadata
- `list_available_repositories(config_dir)` - List all named repositories
- `get_default_repository(config_dir)` - Get default repository name
- `normalize_repository_uri(uri)` - Convert standard URI to restic format
- `validate_repository_name_or_uri(value)` - Validate repository identifier

**URI Formats**:

Supported URI schemes:
- `file:///path/to/repo` - Local filesystem
- `s3:host/bucket` or `s3://host/bucket` - AWS S3 / MinIO
- `b2:bucket/path` or `b2://bucket/path` - Backblaze B2
- `sftp://user@host:/path` - SFTP
- `rest://host:port/path` - REST server
- `rclone:remote:path` - Rclone backend
- `azure://container/path` - Azure Blob Storage
- `gs://bucket/path` - Google Cloud Storage
- `swift:container/path` - OpenStack Swift

**Performance**:
- Resolution time: < 5ms per operation
- Bulk resolution (50 repos): < 200ms

### ServiceFacade

**Purpose**: Simplified interface for accessing TimeLocker services

**Location**: `src/TimeLocker/utils/service_facade.py`

**Key Features**:
- Lazy initialization of services
- Service caching for performance
- Consistent error handling
- Health checking
- Backward compatibility with direct service manager access

**Usage Example**:

```python
from TimeLocker.utils.service_facade import ServiceFacade, create_service_facade
from pathlib import Path

# Create facade
facade = create_service_facade(config_dir=Path("/etc/timelocker"))

# Or with existing service manager
from TimeLocker.cli_services import get_cli_service_manager
service_manager = get_cli_service_manager()
facade = ServiceFacade(service_manager=service_manager)

# Access services
backup_service = facade.get_backup_service()
restore_service = facade.get_restore_service()
repo_service = facade.get_repository_service()
snapshot_service = facade.get_snapshot_service()
config_service = facade.get_configuration_service()
security_service = facade.get_security_service()

# Optional services
monitoring_service = facade.get_monitoring_service()  # Returns None if not available

# Health check
health = facade.health_check()
# Returns: {'repository': True, 'snapshot': True, 'configuration': True}

# Service status
status = facade.get_service_status()

# Cleanup
facade.shutdown_services()
```

**API Reference**:

- `get_backup_service()` - Get backup orchestrator
- `get_restore_service()` - Get restore/recovery service
- `get_repository_service()` - Get repository service
- `get_snapshot_service()` - Get snapshot service
- `get_configuration_service()` - Get configuration service
- `get_repository_factory()` - Get repository factory
- `get_security_service()` - Get security service
- `get_monitoring_service()` - Get monitoring service (optional)
- `initialize_services()` - Explicitly initialize all services
- `health_check()` - Check health of all services
- `get_service_status()` - Get detailed service status
- `shutdown_services()` - Shutdown and cleanup

**Error Handling**:

```python
from TimeLocker.utils.service_facade import (
    ServiceFacadeError,
    ServiceInitializationError,
    ServiceAccessError
)

try:
    facade = ServiceFacade()
    service = facade.get_repository_service()
except ServiceInitializationError as e:
    # Service manager initialization failed
    print(f"Initialization error: {e}")
except ServiceAccessError as e:
    # Service not available or access failed
    print(f"Access error: {e}")
```

**Performance**:
- Service access overhead: < 5ms per operation
- Cached access: < 1ms per operation
- Initialization time: < 50ms

## Integration Patterns

### CLI Command Integration

```python
from typer import Typer
from TimeLocker.utils.service_facade import create_service_facade
from TimeLocker.utils.repository_resolver import resolve_repository_uri

app = Typer()

@app.command()
def backup(repository: str, paths: list[str]):
    """Backup files to repository"""
    # Create service facade
    facade = create_service_facade()
    
    try:
        # Resolve repository
        repo_uri = resolve_repository_uri(repository)
        
        # Get services
        backup_service = facade.get_backup_service()
        config_service = facade.get_configuration_service()
        
        # Perform backup
        result = backup_service.backup(repo_uri, paths)
        
        print(f"Backup completed: {result}")
        
    except Exception as e:
        print(f"Backup failed: {e}")
    finally:
        facade.shutdown_services()
```

### Configuration Management

```python
from TimeLocker.services.configuration_service import ConfigurationService
from pathlib import Path

def manage_repositories(config_dir: Path):
    """Manage repository configuration"""
    config_service = ConfigurationService(config_path=config_dir / "config.json")
    
    # List repositories
    repos = config_service.get_repositories()
    for repo in repos:
        print(f"- {repo['name']}: {repo['location']}")
    
    # Add repository
    config_service.add_repository({
        "name": "new-repo",
        "uri": "s3:bucket/path",
        "location": "s3:bucket/path",
        "description": "New repository"
    })
    
    # Save changes
    config_service.save_configuration(config_service._config_data)
```

### Error Handling Pattern

```python
from TimeLocker.utils.service_facade import ServiceFacade, ServiceAccessError
from TimeLocker.utils.repository_resolver import resolve_repository_uri
from TimeLocker.interfaces import ConfigurationError

def safe_operation(repository_name: str):
    """Perform operation with proper error handling"""
    facade = None
    
    try:
        # Create facade
        facade = ServiceFacade()
        
        # Resolve repository
        try:
            repo_uri = resolve_repository_uri(repository_name)
        except ConfigurationError as e:
            print(f"Repository not found: {e}")
            return False
        
        # Access service
        try:
            service = facade.get_repository_service()
        except ServiceAccessError as e:
            print(f"Service not available: {e}")
            return False
        
        # Perform operation
        result = service.some_operation(repo_uri)
        return True
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        if facade:
            facade.shutdown_services()
```

## Migration Guide

### From Direct Service Manager Access

**Before**:
```python
from TimeLocker.cli_services import get_cli_service_manager

service_manager = get_cli_service_manager()
service_manager.initialize_services()
repo_service = service_manager.repository_service
```

**After**:
```python
from TimeLocker.utils.service_facade import create_service_facade

facade = create_service_facade()
repo_service = facade.get_repository_service()
```

### From Direct Configuration Access

**Before**:
```python
from TimeLocker.config import ConfigurationModule

config_module = ConfigurationModule()
config = config_module.get_config()
repos = config.repositories
```

**After**:
```python
from TimeLocker.services.configuration_service import ConfigurationService

config_service = ConfigurationService()
repos = config_service.get_repositories()
```

### From Manual Repository Resolution

**Before**:
```python
from TimeLocker.config import ConfigurationModule

config_module = ConfigurationModule()
config = config_module.get_config()

if repository_name in config.repositories:
    repo_uri = config.repositories[repository_name].location
else:
    repo_uri = repository_name  # Assume it's a URI
```

**After**:
```python
from TimeLocker.utils.repository_resolver import resolve_repository_uri

repo_uri = resolve_repository_uri(repository_name)
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import Mock
from TimeLocker.utils.service_facade import ServiceFacade

def test_service_facade():
    """Test ServiceFacade with mocked service manager"""
    mock_service_manager = Mock()
    mock_service_manager.repository_service = Mock()
    mock_service_manager.initialize_services = Mock()
    
    facade = ServiceFacade(service_manager=mock_service_manager)
    
    service = facade.get_repository_service()
    
    assert service is mock_service_manager.repository_service
    mock_service_manager.initialize_services.assert_called_once()
```

### Integration Testing

```python
import pytest
from pathlib import Path
from TimeLocker.services.configuration_service import ConfigurationService

def test_configuration_integration(tmp_path):
    """Test ConfigurationService with real files"""
    config_file = tmp_path / "config.json"
    
    # Create service
    config_service = ConfigurationService(config_path=config_file)
    
    # Add repository
    config_service.add_repository({
        "name": "test",
        "uri": "file:///tmp/test",
        "location": "file:///tmp/test",
        "description": "Test"
    })
    
    # Save and reload
    config_service.save_configuration(config_service._config_data, config_file)
    
    new_service = ConfigurationService(config_path=config_file)
    repo = new_service.get_repository_by_name("test")
    
    assert repo['name'] == "test"
    assert repo['location'] == "file:///tmp/test"
```

## Performance Considerations

### Service Layer Overhead

The service layer adds minimal overhead:
- ConfigurationService: < 5ms per operation
- RepositoryResolver: < 5ms per resolution
- ServiceFacade: < 5ms per service access

### Caching Strategy

All components implement caching:
- ConfigurationService caches loaded configuration
- ServiceFacade caches service instances
- RepositoryResolver benefits from ConfigurationModule caching

### Best Practices

1. **Reuse ServiceFacade instances** - Create once per command execution
2. **Use cached access** - Repeated service access uses cache
3. **Cleanup resources** - Always call `shutdown_services()` when done
4. **Lazy initialization** - Services are only initialized when accessed

## Troubleshooting

### Common Issues

**Issue**: `ServiceInitializationError: Failed to create service manager`

**Solution**: Ensure configuration directory exists and is accessible

**Issue**: `ServiceAccessError: Repository service not available`

**Solution**: Check that service manager is properly initialized and service is configured

**Issue**: `ConfigurationError: Repository 'name' not found`

**Solution**: Verify repository name exists in configuration or use direct URI

**Issue**: `ValueError: Local paths must use file:// prefix`

**Solution**: Use `file:///path/to/repo` instead of `/path/to/repo`

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('TimeLocker')
logger.setLevel(logging.DEBUG)
```

## See Also

- [Service Facade Implementation](./service-facade.md)
- [CLI Consolidation Stabilization](../specs/001-cli-consolidation-stabilization/requirements.md)
