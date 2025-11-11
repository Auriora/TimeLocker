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
- Snapshot commands standardized under `snapshots`.
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
│   ├── contents <id>               # List contents of snapshot
│   ├── restore <id> <target>       # Restore snapshot
│   ├── mount <id> <path>           # Mount snapshot
│   ├── umount <id>                 # Unmount snapshot
│   ├── find-in <id> <pattern>      # Search within a snapshot
│   ├── forget <id>                 # Remove snapshot
│   ├── prune                       # Retention across repositories
│   ├── diff <id1> <id2>            # Compare snapshots
│   └── find <pattern>              # Search across repositories
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
| `tl targets add mytarget /path`         | `tl selections create mytarget --include '/path/**'` |
| `tl targets list`                       | `tl selections list`                |
| `tl targets show mytarget`              | `tl selections show mytarget`       |
| `tl snapshot abc123 show`               | `tl snapshots show abc123`          |
| `tl snapshot abc123 list`               | `tl snapshots contents abc123`      |
| `tl snapshot abc123 restore /path`      | `tl snapshots restore abc123 /path` |
| `tl snapshot abc123 mount /mnt`         | `tl snapshots mount abc123 /mnt`    |
| `tl snapshot abc123 forget`             | `tl snapshots forget abc123`        |
| `tl snapshots find "*.pdf"` (unchanged) | `tl snapshots find "*.pdf"`         |

### 2.6 Examples

- Repository list: `tl repos list`
- Initialize repository: `tl repos init myrepo`
- Create selection: `tl selections create documents --include '~/Documents/**' --exclude '*/temp/*'`
- Backup create: `tl backup create --selection documents --repository myrepo`
- Snapshot search: `tl snapshots find "*.pdf" --repository archive`
- Credential storage: `tl credentials set myrepo`

## 3. Usage Notes

- Snapshot commands default to **all** repositories; specify `--repository` to scope to one repository.
- Retention (`prune`, `forget`) respects repository-level retention policies; use `tl repos forget` for repo-specific policies.
- Shell completion generators consume this hierarchy; update completion scripts when modifying command namespaces.
- The `targets` command has been deprecated and replaced by `selections` for more flexible data selection patterns.
- When migrating documentation or support scripts, map legacy `targets` commands to `selections` commands.

## 4. Change Log

- 11-11-2025: Removed deprecated `targets` command; replaced with `selections` for data selection management.
- 01-11-2025: Applied reference template; reorganized sections and clarified aliases.
- 15-12-2024: Documented merged `repos`/`targets` namespaces and default behaviors.

# References

- TimeLocker user documentation (`docs/guides/user/repository-management-guide.md`)
- Shell completion reference (`docs/guides/user/auto-completion-guide.md`)
