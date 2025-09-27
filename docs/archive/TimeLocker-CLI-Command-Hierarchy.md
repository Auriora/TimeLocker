# TimeLocker CLI Command Hierarchy Specification

## Overview

This document defines the complete TimeLocker CLI command hierarchy using a consistent singular/plural pattern. This serves as the specification for the
restructured command interface.

## Design Philosophy

TimeLocker uses a **singular/plural pattern** for intuitive command organization:

- **Singular commands**: `snapshot <id>`, `repo <name>`, `target <name>` - operate on a specific item
- **Plural commands**: `snapshots`, `repos`, `targets` - operate on multiple/all items

## Root Command: `timelocker` (alias: `tl`)

**Description**: TimeLocker - Beautiful backup operations with Rich terminal output
**Framework**: Built with Typer and Rich for beautiful terminal output

## Complete Command Tree Structure

```
timelocker/ (alias: tl)
├── backup/
│   ├── create [paths...]           # Create backup (default action)
│   └── verify [--snapshot]         # Verify backup integrity (defaults to latest)
├── snapshot/ <id>                  # Single snapshot operations
│   ├── show                        # Show snapshot details
│   ├── list                        # List contents of snapshot
│   ├── restore <target>            # Restore from this snapshot
│   ├── mount <path>                # Mount this snapshot as filesystem
│   ├── umount                      # Unmount this snapshot
│   ├── find <pattern>              # Search within this snapshot
│   └── forget                      # Remove this specific snapshot
├── snapshots/                      # Multiple snapshot operations
│   ├── list|ls                     # List snapshots from all configured repos
│   ├── prune                       # Remove old snapshots across repos
│   ├── diff <id1> <id2>            # Compare two snapshots
│   └── find <pattern>              # Search across all snapshots
├── repo/ <name>                    # Single repository operations
│   ├── init                        # Initialize this repository
│   ├── check                       # Check this repository integrity
│   ├── stats                       # Show this repository statistics
│   ├── unlock                      # Remove locks from this repository
│   ├── migrate                     # Migrate this repository format
│   └── forget                      # Apply retention policy to this repo
├── repos/                          # Multiple repository operations
│   ├── list|ls                     # List all repositories
│   ├── check                       # Check all repositories
│   ├── default <name>          # Set default repository
│   └── stats                       # Show stats for all repositories
├── config/                         # Configuration management
│   ├── show                        # Show configuration settings
│   ├── setup                       # Interactive setup wizard
│   ├── import/
│   │   └── restic                  # Import from restic environment
│   ├── repositories/
│   │   ├── list|ls                 # List configured repositories
│   │   ├── add <name> <uri>        # Add repository to config
│   │   ├── remove|rm <name>        # Remove repository from config

│   │   └── show <name>             # Show repository config details
│   ├── target/ <name>              # Single target operations
│   │   ├── show                    # Show target details
│   │   ├── edit                    # Edit target configuration
│   │   └── remove|rm               # Remove this target
│   └── targets/                    # Multiple target operations
│       ├── list|ls                 # List all targets
│       └── add <name> <paths...>   # Add new target
└── version                         # Show version info
```

## Command Aliases

### Global Alias

- `tl` → `timelocker`

### Command Aliases

- `repo` → `repository`
- `repos` → `repositories`
- `ls` → `list`
- `rm` → `remove`

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

Use `--repository` to target a specific repository:

```bash
# List snapshots from specific repository only
tl snapshots list --repository myrepo

# Search in specific repository only
tl snapshots find "*.pdf" --repository local-backup
```

## Key Command Examples

### Backup Operations

```bash
# Create backup
tl backup create /home/user/documents --target mydocs

# Verify backup integrity
tl backup verify
```

### Single Snapshot Operations

```bash
# Show snapshot details
tl snapshot abc123def show

# List files in snapshot
tl snapshot abc123def list

# Restore from snapshot
tl snapshot abc123def restore /restore/path

# Mount snapshot for browsing
tl snapshot abc123def mount /mnt/snapshot

# Search within specific snapshot
tl snapshot abc123def find "*.pdf"

# Remove specific snapshot
tl snapshot abc123def forget
```

### Multiple Snapshot Operations

```bash
# List all snapshots across repositories
tl snapshots list

# Compare two snapshots
tl snapshots diff abc123def xyz789abc

# Search across all snapshots
tl snapshots find "important.doc"

# Prune old snapshots
tl snapshots prune --keep-daily 7 --keep-weekly 4
```

### Repository Operations

```bash
# Initialize new repository
tl repo myrepo init --repository file:///backup/repo

# Check repository integrity
tl repo myrepo check

# Show repository statistics
tl repo myrepo stats

# Apply retention policy to repository
tl repo myrepo forget --keep-daily 7
```

### Configuration Management

```bash
# Add repository to configuration
tl config repositories add myrepo file:///backup/repo --default

# Add backup target
tl config targets add documents /home/user/Documents

# Show target details
tl config target documents show

# Edit target configuration
tl config target documents edit
```

## URI Standardization

- **File repositories**: Must use `file://` prefix (e.g., `file:///backup/repo`)
- **S3 repositories**: Must use `s3://` prefix (e.g., `s3://bucket/path`)
- **Repository names**: Can be used via `--repository` option for configured repos
- **Legacy support**: Non-URI formats supported via `--repository-path` option

## Environment Variables

- `TIMELOCKER_PASSWORD`: Repository password (preferred)
- `RESTIC_PASSWORD`: Fallback repository password
- Standard restic environment variables for repository configuration

---

*This specification defines the complete restructured TimeLocker CLI with consistent singular/plural patterns and intuitive command organization.*
