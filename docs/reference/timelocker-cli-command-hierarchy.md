# TimeLocker CLI Command Hierarchy Specification (Updated)

## Overview

This document defines the updated TimeLocker CLI command hierarchy after merging repository and target commands for better organization.

## Design Philosophy

TimeLocker now uses a **simplified command organization**:

- **Repository operations**: All under `repos` - both configuration and operational commands
- **Target operations**: All under `targets` - both configuration and operational commands
- **Cleaner hierarchy**: Eliminated artificial singular/plural separation

## Root Command: `timelocker` (alias: `tl`)

**Description**: TimeLocker - Beautiful backup operations with Rich terminal output  
**Framework**: Built with Typer and Rich for beautiful terminal output

## Complete Command Tree Structure

```
timelocker/ (alias: tl)
├── backup/
│   ├── create [paths...]           # Create backup (default action)
│   └── verify [--snapshot]         # Verify backup integrity (defaults to latest)
├── snapshots/                      # All snapshot operations
│   ├── list|ls                     # List snapshots from all configured repos
│   ├── show <id>                   # Show snapshot details
│   ├── contents <id>               # List contents of specific snapshot
│   ├── restore <id> <target>       # Restore from snapshot
│   ├── mount <id> <path>           # Mount snapshot as filesystem
│   ├── umount <id>                 # Unmount snapshot
│   ├── find-in <id> <pattern>      # Search within specific snapshot
│   ├── forget <id>                 # Remove specific snapshot
│   ├── prune                       # Remove old snapshots across repos
│   ├── diff <id1> <id2>            # Compare two snapshots
│   └── find <pattern>              # Search across all snapshots
├── repos/                          # Repository operations
│   ├── list|ls                     # List all repositories
│   ├── add <n> <uri>            # Add repository to config
│   ├── remove|rm <n>            # Remove repository from config
│   ├── show <n>                 # Show repository config details
│   ├── default <n>              # Set default repository
│   ├── init <n>                 # Initialize repository
│   ├── check <n>                # Check repository integrity
│   ├── stats <n>                # Show repository statistics
│   ├── unlock <n>               # Remove locks from repository
│   ├── migrate <n>              # Migrate repository format
│   ├── forget <n>               # Apply retention policy to repo
│   ├── check-all                   # Check all repositories
│   └── stats-all                   # Show stats for all repositories
├── targets/                        # Backup target operations
│   ├── list|ls                     # List all backup targets
│   ├── add <n> <paths...>       # Add new backup target
│   ├── show <n>                 # Show target details
│   ├── edit <n>                 # Edit target configuration
│   └── remove|rm <n>            # Remove backup target
├── config/                         # Configuration management
│   ├── show                        # Show configuration info and validation status
│   ├── setup                       # Interactive setup wizard
│   └── import/
│       └── restic                  # Import from restic environment
├── credentials/                    # Credential management
│   ├── unlock                      # Unlock credential manager
│   ├── set <repo>               # Set repository password
│   └── remove <repo>            # Remove repository password
└── version                         # Show version info
```

## Command Aliases

### Global Alias

- `tl` → `timelocker`

### Command Aliases

- `repos` → `repositories`
- `ls` → `list`
- `rm` → `remove`

## Key Changes from Previous Hierarchy

### Repository Commands Merged

**Before:**

- `tl repo <name> <command>` - Single repository operations
- `tl repos <command>` - Multiple repository operations
- `tl config repositories <command>` - Repository configuration

**After:**

- `tl repos <command>` - All repository operations (both single and multiple)

### Target Commands Moved

**Before:**

- `tl config target <name> <command>` - Single target operations
- `tl config targets <command>` - Multiple target operations

**After:**

- `tl targets <command>` - All target operations

### Benefits

1. **Simpler Discovery**: Related commands grouped under logical namespaces
2. **Consistent Organization**: No artificial singular/plural separation
3. **Fewer Command Levels**: Reduced nesting for common operations
4. **Intuitive Grouping**: Repository and target operations clearly separated

## Migration Guide

### Repository Commands

| Old Command                   | New Command                 |
|-------------------------------|-----------------------------|
| `tl repo myrepo init`         | `tl repos init myrepo`      |
| `tl repo myrepo check`        | `tl repos check myrepo`     |
| `tl repos list`               | `tl repos list` (unchanged) |
| `tl config repositories add`  | `tl repos add`              |
| `tl config repositories show` | `tl repos show`             |

### Target Commands

| Old Command                      | New Command                |
|----------------------------------|----------------------------|
| `tl config target mytarget show` | `tl targets show mytarget` |
| `tl config target mytarget edit` | `tl targets edit mytarget` |
| `tl config targets add`          | `tl targets add`           |
| `tl config targets list`         | `tl targets list`          |

### Snapshot Commands

| Old Command                        | New Command                             |
|------------------------------------|-----------------------------------------|
| `tl snapshot abc123 show`          | `tl snapshots show abc123`              |
| `tl snapshot abc123 list`          | `tl snapshots contents abc123`          |
| `tl snapshot abc123 restore /path` | `tl snapshots restore abc123 /path`     |
| `tl snapshot abc123 mount /mnt`    | `tl snapshots mount abc123 /mnt`        |
| `tl snapshot abc123 umount`        | `tl snapshots umount abc123`            |
| `tl snapshot abc123 find "*.pdf"`  | `tl snapshots find-in abc123 "*.pdf"`   |
| `tl snapshot abc123 forget`        | `tl snapshots forget abc123`            |
| `tl snapshots list`                | `tl snapshots list` (unchanged)         |
| `tl snapshots find "*.pdf"`        | `tl snapshots find "*.pdf"` (unchanged) |

## Default Behavior

### Snapshot Operations Default to All Repositories

By default, snapshot operations work across **all configured repositories**:

```bash
# Shows snapshots from ALL configured repositories
tl snapshots list

# Searches across ALL configured repositories  
tl snapshots find "*.pdf"

# Prunes old snapshots in ALL configured repositories
tl snapshots prune --keep-daily 7
```

### Single Repository Operations

Use repository name to target a specific repository:

```bash
# List snapshots from specific repository only
tl snapshots list --repository myrepo

# Search in specific repository only
tl snapshots find "*.pdf" --repository local-backup
```

## Key Command Examples

### Repository Operations

```bash
# List all repositories
tl repos list

# Add repository to configuration
tl repos add myrepo file:///backup/repo --set-default

# Initialize repository
tl repos init myrepo

# Check repository integrity
tl repos check myrepo

# Show repository statistics
tl repos stats myrepo

# Apply retention policy to repository
tl repos forget myrepo --keep-daily 7

# Check all repositories
tl repos check-all
```

### Target Operations

```bash
# List all backup targets
tl targets list

# Add backup target
tl targets add documents /home/user/Documents

# Show target details
tl targets show documents

# Edit target configuration
tl targets edit documents

# Remove backup target
tl targets remove documents
```

### Snapshot Operations

```bash
# List all snapshots
tl snapshots list

# Show snapshot details
tl snapshots show abc123def

# List contents of specific snapshot
tl snapshots contents abc123def

# Restore from snapshot
tl snapshots restore abc123def /restore/path

# Mount snapshot as filesystem
tl snapshots mount abc123def /mnt/snapshot

# Unmount snapshot
tl snapshots umount abc123def

# Search within specific snapshot
tl snapshots find-in abc123def "*.pdf"

# Search across all snapshots
tl snapshots find "*.pdf"

# Remove specific snapshot
tl snapshots forget abc123def

# Prune old snapshots
tl snapshots prune --keep-daily 7

# Compare two snapshots
tl snapshots diff abc123 def456
```

### Configuration Management

```bash
# Show configuration info and validation status
tl config show

# Interactive setup wizard
tl config setup

# Import from restic environment
tl config import restic
```

## URI Standardization

- **File repositories**: Must use `file://` prefix (e.g., `file:///backup/repo`)
- **S3 repositories**: Must use `s3://` prefix (e.g., `s3://bucket/path`)
- **Repository names**: Can be used via repository name for configured repos
- **Legacy support**: Non-URI formats supported via `--repository-path` option

## Environment Variables

- `TIMELOCKER_PASSWORD`: Repository password (preferred)
- `RESTIC_PASSWORD`: Fallback repository password
- Standard restic environment variables for repository configuration

---

*This specification defines the updated TimeLocker CLI with merged repository and target commands for improved usability.*
