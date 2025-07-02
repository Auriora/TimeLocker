# TimeLocker CLI Command Hierarchy Documentation

## Overview

This document provides a comprehensive hierarchical documentation of all TimeLocker CLI commands with detailed explanations of each command's purpose,
arguments, options, and usage patterns. This serves as a reference for restructuring the command hierarchy and adding new commands.

## Root Command: `timelocker`

**Description**: TimeLocker - Beautiful backup operations with Rich terminal output  
**Entry Point**: `src/TimeLocker/cli.py`  
**Framework**: Built with Typer and Rich for beautiful terminal output

---

## Main Commands (Direct under `timelocker`)

### 1. `timelocker backup`

**Purpose**: Create a backup of specified sources  
**Arguments**:

- `sources` (optional): Source paths to backup (List[Path])

**Options**:

- `--repository, -r`: Repository name or URI
- `--password, -p`: Repository password
- `--target, -t`: Use configured backup target
- `--name, -n`: Backup target name
- `--exclude, -e`: Exclude pattern (multiple allowed)
- `--include, -i`: Include pattern (multiple allowed)
- `--dry-run`: Preview backup without executing
- `--confirm`: Skip confirmation prompts
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker backup /home/user --repository myrepo
timelocker backup --target documents --repository myrepo
timelocker backup /home/user/Documents --exclude "*.tmp" --dry-run
```

---

### 2. `timelocker restore`

**Purpose**: Restore files from a backup snapshot  
**Arguments**:

- `target`: Target path for restore (required)

**Options**:

- `--repository, -r`: Repository name or URI
- `--password, -p`: Repository password
- `--snapshot, -s`: Snapshot ID to restore (or 'latest')
- `--exclude, -e`: Exclude pattern (multiple allowed)
- `--include, -i`: Include pattern (multiple allowed)
- `--preview`: Preview restore without executing
- `--confirm`: Skip confirmation prompts
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker restore /restore/path --repository myrepo --snapshot latest
timelocker restore /restore/path --repository myrepo --snapshot abc123
timelocker restore /restore/path --preview --include "*.pdf"
```

---

### 3. `timelocker list`

**Purpose**: List snapshots in repository with a beautiful table
**Arguments**: None

**Options**:

- `--repository, -r`: Repository name or URI
- `--password, -p`: Repository password
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker list --repository myrepo
timelocker list -r s3://bucket/path
```

---

### 4. `timelocker init`

**Purpose**: Initialize a new backup repository
**Arguments**: None

**Options**:

- `--repository, -r`: Repository name or URI
- `--password, -p`: Repository password
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker init --repository /path/to/repo --password mypassword
timelocker init --repository s3://bucket/path --password mypassword
```

---

### 5. `timelocker verify`

**Purpose**: Verify backup integrity
**Arguments**: None

**Options**:

- `--repository, -r`: Repository name or URI
- `--password, -p`: Repository password
- `--snapshot, -s`: Specific snapshot to verify
- `--latest`: Verify latest snapshot
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker verify --repository myrepo --latest
timelocker verify --repository myrepo --snapshot abc123
```

---

### 6. `timelocker version`

**Purpose**: Show version information with beautiful formatting  
**Arguments**: None  
**Options**: None

**Usage Examples**:

```bash
timelocker version
```

---

## Configuration Commands (Under `timelocker config`)

### 7. `timelocker config setup`

**Purpose**: Interactive configuration setup wizard  
**Arguments**: None

**Options**:

- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config setup
timelocker config setup --config-dir /custom/path
```

---

### 8. `timelocker config list`

**Purpose**: List current configuration
**Arguments**: None

**Options**:

- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config list
```

---

### 9. `timelocker config import-restic`

**Purpose**: Import configuration from existing restic environment
**Arguments**: None

**Options**:

- `--config-dir`: Configuration directory
- `--name, -n`: Name for the imported repository (default: "imported_restic")
- `--target, -t`: Name for the backup target (default: "imported_backup")
- `--paths, -p`: Backup paths (multiple allowed)
- `--dry-run`: Show what would be imported without making changes
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config import-restic --name myrepo --target mydocs
timelocker config import-restic --dry-run
```

---

### 10. `timelocker config list-repos`

**Purpose**: List configured repositories
**Arguments**: None

**Options**:

- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config list-repos
```

---

### 11. `timelocker config add-repo`

**Purpose**: Add a new repository to configuration
**Arguments**:

- `name`: Repository name (required)
- `uri`: Repository URI (required)

**Options**:

- `--description, -d`: Repository description
- `--set-default`: Set as default repository
- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config add-repo myrepo /path/to/repo --description "My backup repo"
timelocker config add-repo s3repo s3://bucket/path --set-default
```

---

### 12. `timelocker config remove-repo`

**Purpose**: Remove a repository from configuration
**Arguments**:

- `name`: Repository name to remove (required)

**Options**:

- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config remove-repo myrepo
```

---

### 13. `timelocker config set-default-repo`

**Purpose**: Set the default repository
**Arguments**:

- `name`: Repository name to set as default (required)

**Options**:

- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config set-default-repo myrepo
```

---

### 14. `timelocker config add-target`

**Purpose**: Add a new backup target configuration
**Arguments**:

- `name`: Target name (required)
- `paths`: Source paths to backup (required, multiple allowed)

**Options**:

- `--description, -d`: Target description
- `--include, -i`: Include patterns (multiple allowed)
- `--exclude, -e`: Exclude patterns (multiple allowed)
- `--config-dir`: Configuration directory
- `--verbose, -v`: Enable verbose output

**Usage Examples**:

```bash
timelocker config add-target documents /home/user/Documents /home/user/Work
timelocker config add-target photos /home/user/Pictures --exclude "*.tmp"
```

---

## Revised Command Tree Structure (Singular/Plural Pattern)

```
timelocker/ (alias: tl)
├── backup/
│   ├── create [paths...]           # Create backup (default action)
│   └── verify [--snapshot]         # Verify backup integrity
├── snapshot/ <id>                  # Single snapshot operations
│   ├── show                        # Show snapshot details
│   ├── list                        # List contents of snapshot (NEW!)
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
│   │   ├── default <name>          # Set default repository
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

## Command Aliases and Shortcuts

### Global Alias

- `tl` → `timelocker` (already exists)

### Command Aliases

- `repo` → `repository`
- `repos` → `repositories`
- `ls` → `list`
- `rm` → `remove`

### Common Usage Shortcuts

```bash
# List snapshots from all configured repositories
tl snapshots ls

# List snapshots from specific repository
tl snapshots ls --repository myrepo

# Show details of specific snapshot
tl snapshot abc123def show

# List contents of specific snapshot
tl snapshot abc123def list

# Configuration shortcuts
tl config repositories ls
tl config targets ls
```

## Singular/Plural Command Pattern

### Design Philosophy

TimeLocker uses a consistent **singular/plural pattern** to distinguish between operations on single items vs. multiple items:

- **Singular commands**: `snapshot`, `repo`, `target` - operate on a specific item
- **Plural commands**: `snapshots`, `repos`, `targets` - operate on multiple/all items

### Pattern Examples

#### Snapshots

```bash
# Single snapshot operations (require snapshot ID)
tl snapshot <id> show           # Show THIS snapshot's details
tl snapshot <id> list           # List THIS snapshot's contents
tl snapshot <id> restore <path> # Restore from THIS snapshot
tl snapshot <id> mount <path>   # Mount THIS snapshot
tl snapshot <id> find <pattern> # Search within THIS snapshot

# Multiple snapshot operations (work across all/multiple)
tl snapshots list               # List ALL snapshots
tl snapshots prune              # Prune old snapshots across repos
tl snapshots find <pattern>     # Search across ALL snapshots
tl snapshots diff <id1> <id2>   # Compare two snapshots
```

#### Repositories

```bash
# Single repository operations (require repo name)
tl repo <name> init             # Initialize THIS repository
tl repo <name> check            # Check THIS repository
tl repo <name> stats            # Stats for THIS repository

# Multiple repository operations
tl repos list                   # List ALL repositories
tl repos check                  # Check ALL repositories
tl repos stats                  # Stats for ALL repositories
```

#### Configuration Targets

```bash
# Single target operations (require target name)
tl config target <name> show    # Show THIS target's details
tl config target <name> edit    # Edit THIS target
tl config target <name> remove  # Remove THIS target

# Multiple target operations
tl config targets list          # List ALL targets
tl config targets add <name>    # Add new target
```

### Commands Available in Multiple Locations

Some commands appear in both singular and plural forms where relevant:

- **`find`**: Available as both `snapshot <id> find` (search within one) and `snapshots find` (search across all)
- **`list`**: `snapshot <id> list` (contents) vs `snapshots list` (all snapshots)
- **`show`**: Available for individual items (`snapshot <id> show`, `repo <name> show`, etc.)

## Default Behavior for Snapshot Operations

### Multi-Repository Default

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
tl snapshots list -r s3://bucket/backup

# Search in specific repository only
tl snapshots find "*.pdf" --repository local-backup

# Prune specific repository only
tl snapshots prune --repository myrepo --keep-daily 7
```

### Output Format for Multi-Repository Operations

When operating across multiple repositories, output clearly indicates the source:

```
Repository: local-backup (file:///backup/local)
  abc123def  2024-01-15 10:30  documents/
  def456ghi  2024-01-14 10:30  documents/

Repository: remote-backup (s3://bucket/backup)
  ghi789jkl  2024-01-15 11:00  documents/
  jkl012mno  2024-01-14 11:00  documents/
```

## Commands to Implement

Based on your restructuring decisions and typical backup tool functionality, the following commands need to be implemented:

### Repository Operations (Under `timelocker repository`)

1. **`timelocker repo prune`** - Remove old snapshots according to retention policies
2. **`timelocker repo check`** - Check repository consistency and integrity
3. **`timelocker repo unlock`** - Remove repository locks
4. **`timelocker repo migrate`** - Migrate repository format
5. **`timelocker repo stats`** - Show repository statistics
6. **`timelocker repo forget`** - Remove specific snapshots
7. **`timelocker repo diff`** - Show differences between snapshots
8. **`timelocker repo find`** - Search for files in snapshots
9. **`timelocker repo mount`** - Mount repository as filesystem
10. **`timelocker repo umount`** - Unmount repository filesystem

### Configuration Target Management (Under `timelocker config targets`)

11. **`timelocker config targets remove`** - Remove backup target
12. **`timelocker config targets edit`** - Edit backup target configuration
13. **`timelocker config targets show`** - Show detailed target information

### Command Restructuring (Existing commands to move)

14. **Move** `timelocker list` → `timelocker repository snapshots list`
15. **Move** `timelocker init` → `timelocker repository init`
16. **Move** `timelocker verify` → `timelocker backup verify`
17. **Restructure** config commands as outlined in your changes

## Configuration and Environment

### Configuration File Structure

TimeLocker uses a configuration file located at `~/.timelocker/config.json` (configurable) that stores:

- **Repository definitions**: name, URI, description
- **Backup target definitions**: name, paths, include/exclude patterns
- **Default repository setting**: which repository to use by default
- **General settings**: application-wide configuration

### Environment Variables

- `TIMELOCKER_PASSWORD`: Repository password (preferred over `RESTIC_PASSWORD`)
- `RESTIC_PASSWORD`: Fallback repository password for restic based repositories
- Standard restic environment variables for repository configuration

### Key Terms and Concepts

- **Repository**: A backup storage location (local path, S3, Backblaze B2, etc.)
- **Snapshot**: A point-in-time backup containing file data and metadata
- **Target**: A configured set of paths and patterns for backup operations
- **Configuration**: Stored settings for repositories, targets, and application preferences

## Implementation Notes

### Current Architecture

- **Single CLI file**: All commands defined in `src/TimeLocker/cli.py`
- **Flat structure**: Main app with one sub-app (config)
- **Framework**: Built with Typer for CLI and Rich for beautiful terminal output
- **Backend**: Uses restic as the underlying backup engine

### Restructuring Implementation Plan

1. **Separate operational vs configuration commands**:
    - `timelocker repository` for using/managing repositories
    - `timelocker config repositories` for configuring repository settings
2. **Add missing standard commands**: Implement repository operations like prune, check, stats, etc.
3. **Improve command organization**: Split large CLI file into focused modules by command group
4. **Enhanced configuration management**: Add granular target management commands
5. **Implement URI validation**: Require proper URI formats (file://, s3://, etc.)
6. **Add command aliases**: Provide shortcuts while maintaining full command clarity

## Usage Patterns

### Quick Start Workflow (Proposed Structure)

```bash
# 1. Initialize repository
tl repo myrepo init --repository file:///backup/repo --password mypass

# 2. Add repository to config
tl config repositories add myrepo file:///backup/repo --default

# 3. Create backup target
tl config targets add documents /home/user/Documents

# 4. Create backup
tl backup create --target documents

# 5. List snapshots (shows all configured repositories by default)
tl snapshots list

# 6. Show details of specific snapshot
tl snapshot abc123def show

# 7. List contents of specific snapshot
tl snapshot abc123def list

# 8. Restore from specific snapshot
tl snapshot abc123def restore /restore/path
```

### Advanced Configuration (Proposed Structure)

```bash
# Import existing restic setup
tl config import restic --name imported --target myfiles

# Add multiple repositories with proper URI formats
tl config repos add local file:///backup/local
tl config repos add remote s3://bucket/backup

# Configure complex backup targets
tl config targets add photos /home/user/Pictures \
  --include "*.jpg" --include "*.png" --exclude "thumbnails/"

# Manage targets
tl config targets ls
tl config targets show photos
tl config targets edit photos
tl config targets rm old-target

# Repository operations
tl repo check --repository local
tl repo stats --repository remote
tl repo prune --repository local --keep-daily 7 --keep-weekly 4
```

## URI Standardization Requirements

- **File repositories**: Must use `file://` prefix (e.g., `file:///backup/repo`)
- **S3 repositories**: Must use `s3://` prefix (e.g., `s3://bucket/path`)
- **Other cloud providers**: Must use appropriate URI schemes
- **Repository names**: Can be used via `--repository-name` option for configured repos
- **Legacy support**: Non-URI formats supported via separate `--repository-path` option

---

*This documentation serves as a foundation for planning command hierarchy restructuring and new command additions to the TimeLocker CLI.*
