---
title: "Reference: TimeLocker CLI Command Hierarchy"
id: "ref-cli-hierarchy"
type: [ reference ]
status: [ approved ]
owner: "CLI Team"
last_reviewed: "01-11-2025"
tags: [reference, cli, command-structure]
links:
  tooling: []
---

# Reference: TimeLocker CLI Command Hierarchy

- **Owner**: CLI Team
- **Status**: Approved
- **Created Date**: 15-12-2024
- **Last Updated**: 01-11-2025
- **Audience**: Developers, Technical Writers, Support Engineers

## 1. Purpose

Document the authoritative command hierarchy for the `timelocker` (`tl`) CLI, including namespace organization, aliases, and migration notes for legacy
commands. Use this reference to maintain CLI documentation, implement shell completions, and verify command routing.

## 2. Specification

### 2.1 Design Philosophy

- Repository operations consolidated under `repos` (configuration + actions).
- Data selection operations unified under `selections` (replaces deprecated `targets`).
- Snapshot lifecycle management under `snapshots` (list, forget, prune).
- Recovery operations under `restore` (browse, restore, verify) - separate from snapshot management.
- Configuration, credentials, and version info exposed via dedicated namespaces.

### 2.2 Root Command Summary

- **Root**: `timelocker` (alias `tl`)
- **Description**: TimeLocker – backup orchestration with Rich terminal output
- **Framework**: Typer + Rich

### 2.3 Command Tree

```
timelocker/ (alias: tl)
├── backup/
│   ├── create [paths...]           # Create backup (default action)
│   └── verify [--snapshot]         # Verify backup integrity (defaults to latest)
├── snapshots/
│   ├── list|ls                     # List snapshots from configured repos
│   ├── show <id>                   # Show snapshot details
│   ├── forget <id>                 # Remove snapshot
│   ├── prune                       # Apply retention policies
│   ├── diff <id1> <id2>            # Compare snapshots
│   └── find <pattern>              # Search across repositories
├── restore/
│   ├── list <repository>           # List available snapshots for restoration
│   ├── browse <repository> <id>    # Explore snapshot contents
│   ├── files <repository> <id> <paths> # Restore specific files
│   ├── full <repository> <id> <target> # Restore complete snapshot
│   ├── mount <repository> <id> <mountpoint> # Mount snapshot as filesystem
│   ├── umount <id>                 # Unmount snapshot
│   ├── find <repository> <query>   # Search files for recovery
│   ├── diff <repository> <id1> <id2> # Compare snapshots for recovery
│   └── verify <target>             # Verify restored data integrity
├── repos/
│   ├── list|ls                     # List repositories
│   ├── add <name> <uri>            # Add repository configuration
│   ├── remove|rm <name>            # Remove repository configuration
│   ├── show <name>                 # Show repository details
│   ├── default <name>              # Set default repository
│   ├── init <name>                 # Initialize repository
│   ├── check <name>                # Check repository integrity
│   ├── stats <name>                # Repository statistics
│   ├── unlock <name>               # Clear repository locks
│   ├── migrate <name>              # Migrate repository format
│   ├── forget <name>               # Apply retention policy
│   ├── check-all                   # Check all repositories
│   └── stats-all                   # Stats across repositories
├── selections/
│   ├── list|ls                     # List data selection templates
│   ├── create <name>               # Create selection template
│   ├── show <name>                 # Show selection details
│   ├── edit <name>                 # Edit selection template
│   ├── delete <name>               # Delete selection template
│   ├── test <name> [path]          # Test selection against path
│   ├── export <name>               # Export selection template
│   └── import <file>               # Import selection template
├── config/
│   ├── show                        # Configuration info and validation
│   ├── setup                       # Interactive setup wizard
│   └── import/
│       └── restic                  # Import restic environment
├── credentials/
│   ├── unlock                      # Unlock credential manager
│   ├── set <repo>                  # Store repository password
│   └── remove <repo>               # Remove repository password
└── version                         # Show CLI version information
```

### 2.4 Command Aliases

- Global alias: `tl` → `timelocker`
- Namespace aliases: `repos` ↔ `repositories`, `ls` ↔ `list`, `rm` ↔ `remove`.

### 2.5 Migration Guide

| Legacy Command                          | Current Command                     |
|-----------------------------------------|-------------------------------------|
| `tl repo myrepo init`                   | `tl repos init myrepo`              |
| `tl repo myrepo check`                  | `tl repos check myrepo`             |
| `tl config repositories add`            | `tl repos add`                      |
| `tl snapshot abc123 show`               | `tl snapshots show abc123`          |
| `tl snapshot abc123 forget`             | `tl snapshots forget abc123`        |
| `tl snapshot abc123 restore /path`      | `tl restore files myrepo abc123 /path` |
| `tl snapshot abc123 mount /mnt`         | `tl restore mount myrepo abc123 /mnt` |
| `tl snapshots find "*.pdf"`             | `tl snapshots find "*.pdf"` OR `tl restore find myrepo "*.pdf"` |

### 2.6 Examples

- Repository list: `tl repos list`
- Initialize repository: `tl repos init myrepo`
- Create selection: `tl selections create documents --include '~/Documents/**' --exclude '*/temp/*'`
- Backup create: `tl backup create --selection documents --repository myrepo`
- List snapshots: `tl snapshots list` (all repos) or `tl restore list myrepo` (specific repo)
- Browse snapshot: `tl restore browse myrepo abc123`
- Restore files: `tl restore files myrepo abc123 /path/to/file1 /path/to/file2 --target ~/restored`
- Restore full: `tl restore full myrepo abc123 ~/restored`
- Verify restore: `tl restore verify ~/restored --repository myrepo --snapshot abc123`
- Snapshot search: `tl snapshots find "*.pdf"` (management) or `tl restore find myrepo "*.pdf"` (recovery)
- Credential storage: `tl credentials set myrepo`

## 3. Usage Notes

- **Snapshot Management** (`snapshots`): Use for lifecycle operations (list, forget, prune, search).
- **Recovery Operations** (`restore`): Use for data restoration (browse, restore, verify, mount).
- All `restore` commands require explicit `<repository>` parameter for clarity in multi-repository environments.
- Snapshot commands in `snapshots` namespace default to **all** repositories; use `restore list <repository>` for repository-specific listing.
- Retention (`prune`, `forget`) respects repository-level retention policies; use `tl repos forget` for repo-specific policies.
- Shell completion generators consume this hierarchy; update completion scripts when modifying command namespaces.
- The `targets` command has been deprecated and replaced by `selections` for more flexible data selection patterns.
- When migrating documentation or support scripts, map legacy `targets` commands to `selections` commands.

## 4. Change Log

- 11-11-2025: **Major restructure** - Separated `restore` namespace from `snapshots` for proper separation of concerns. Removed `restore`, `mount`, `umount`, `contents`, `find-in` from `snapshots`. Added complete `restore` namespace with 9 commands per CLI Interface Requirements. Updated to align with Recovery Operations architecture.
- 11-11-2025: Removed deprecated `targets` command; replaced with `selections` for data selection management.
- 01-11-2025: Applied reference template; reorganized sections and clarified aliases.
- 15-12-2024: Documented merged `repos`/`targets` namespaces and default behaviors.

# References

- TimeLocker user documentation (`docs/guides/user/repository-management-guide.md`)
- Shell completion reference (`docs/guides/user/auto-completion-guide.md`)
