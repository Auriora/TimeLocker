# TimeLocker Backup Engine Plugins

This directory contains the built-in backup engine plugins for TimeLocker.

## Overview

The plugin system provides an extensible architecture for supporting multiple backup engines with different capabilities and strategies. Each plugin implements the `BackupEnginePlugin` interface defined in `src/TimeLocker/interfaces/backup_engine_plugin.py`.

## Built-in Plugins

### Restic Plugin (`restic_plugin.py`)

**Capabilities:**
- ✓ Encryption
- ✓ Deduplication
- ✓ Compression
- ✓ Snapshots
- ✓ Incremental backups
- ✓ Verification
- ✓ Retention policies
- ✓ Tags

**Supported Storage Backends:**
- Local filesystem
- Amazon S3
- Backblaze B2
- SFTP
- REST server

**Configuration Options:**
- `compression`: Compression level (auto, off, max)
- `pack_size`: Target pack size in bytes
- `cache_dir`: Custom cache directory
- `exclude_caches`: Exclude cache directories
- `one_file_system`: Stay within one filesystem

### Rsync Plugin (`rsync_plugin.py`)

**Capabilities:**
- ✗ Encryption
- ✗ Deduplication
- ✓ Compression
- ✗ Snapshots
- ✓ Incremental backups
- ✓ Verification
- ✗ Retention policies
- ✗ Tags

**Supported Storage Backends:**
- Local filesystem
- SSH/Remote hosts
- Rsync daemon

**Configuration Options:**
- `archive_mode`: Enable archive mode
- `compress`: Compress during transfer
- `delete_excluded`: Delete excluded files
- `preserve_permissions`: Preserve file permissions
- `preserve_times`: Preserve modification times
- `dry_run`: Trial run without changes

### Rclone Plugin (`rclone_plugin.py`)

**Capabilities:**
- ✓ Encryption (via crypt remote)
- ✗ Deduplication
- ✗ Compression
- ✗ Snapshots
- ✓ Incremental backups
- ✓ Verification
- ✗ Retention policies
- ✗ Tags

**Supported Storage Backends:**
- Local filesystem
- Amazon S3
- Backblaze B2
- Microsoft Azure
- Google Cloud Storage
- Dropbox
- OneDrive
- SFTP
- FTP
- WebDAV
- Google Drive
- Box
- Mega
- pCloud
- OpenStack Swift
- And many more...

**Configuration Options:**
- `config_file`: Path to rclone config file
- `transfers`: Number of parallel transfers
- `checkers`: Number of parallel checkers
- `buffer_size`: Buffer size for transfers
- `use_mmap`: Use memory mapped files

## Usage

### Basic Plugin Usage

```python
from TimeLocker.interfaces.backup_engine_plugin import BackupEngine
from TimeLocker.services import get_plugin_registry

# Get the plugin registry
registry = get_plugin_registry()

# Get a specific plugin
restic_plugin = registry.get_plugin(BackupEngine.RESTIC)

# Check if engine is available
if restic_plugin.is_available():
    print(f"Restic version: {restic_plugin.engine_version}")
    
    # Get capabilities
    caps = restic_plugin.get_capabilities()
    print(f"Supports encryption: {caps.supports_encryption}")
    
    # Validate a URI
    result = restic_plugin.validate_uri("s3:s3.amazonaws.com/my-bucket")
    if result.is_valid:
        print("URI is valid")
```

### Using with RepositoryFactory

```python
from TimeLocker.interfaces.backup_engine_plugin import BackupEngine
from TimeLocker.services import RepositoryFactory

factory = RepositoryFactory()

# Create repository with specific engine
repository = factory.create_repository_with_engine(
    uri="/path/to/backup",
    engine=BackupEngine.RESTIC,
    password="my-secure-password"
)

# Check which engines support a storage type
engines = factory.get_engines_for_storage_type('s3')
print(f"Engines supporting S3: {[e.value for e in engines]}")
```

### Checking Engine Availability

```python
from TimeLocker.services import (
    initialize_plugins,
    check_engine_availability,
    get_available_engines_info
)
from TimeLocker.interfaces.backup_engine_plugin import BackupEngine

# Initialize plugins
initialize_plugins()

# Check specific engine
if check_engine_availability(BackupEngine.RESTIC):
    print("Restic is available")

# Get info about all engines
info = get_available_engines_info()
for engine_name, engine_info in info.items():
    print(f"{engine_name}: {engine_info['available']}")
```

## Creating Custom Plugins

To create a custom backup engine plugin:

1. Create a new Python file in this directory
2. Import the base class: `from ...interfaces.backup_engine_plugin import BackupEnginePlugin`
3. Implement all abstract methods
4. Register your plugin with the registry

Example:

```python
from ...interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    ValidationResult,
    EngineCapabilities
)

class MyCustomEnginePlugin(BackupEnginePlugin):
    @property
    def engine_name(self) -> str:
        return "mycustom"
    
    @property
    def engine_type(self) -> BackupEngine:
        # Add new enum value to BackupEngine
        return BackupEngine.CUSTOM
    
    # Implement other required methods...
```

Then register it:

```python
from TimeLocker.services import get_plugin_registry
from .my_custom_plugin import MyCustomEnginePlugin

registry = get_plugin_registry()
registry.register_plugin(MyCustomEnginePlugin)
```

## Testing

Run the demo script to test plugin functionality:

```bash
python3 examples/plugin_system_demo.py
```

Or use the quick check script:

```bash
python3 scripts/check_backup_engines.py
```

## Architecture

The plugin system follows these design principles:

- **Open/Closed Principle**: Open for extension (new plugins), closed for modification
- **Dependency Inversion**: Depend on abstractions (plugin interface), not concrete implementations
- **Single Responsibility**: Each plugin handles one backup engine
- **Interface Segregation**: Clean, focused interface for plugins

## Requirements

Each plugin requires its corresponding backup engine to be installed:

- **Restic**: Install from https://restic.net/
- **Rsync**: Usually pre-installed on Unix systems
- **Rclone**: Install from https://rclone.org/

The plugin system gracefully handles missing engines by reporting them as unavailable.
