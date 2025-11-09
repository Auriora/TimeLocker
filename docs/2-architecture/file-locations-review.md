---
title: "Architecture Decision Record: TimeLocker File Locations Review"
id: "adr-file-locations"
type: [ architecture ]
status: accepted
owner: "Architecture Team"
last_reviewed: "09-11-2025"
tags: [ architecture, adr, xdg, file-paths, test-isolation ]
links:
    tooling: [ pytest ]
---

# Architecture Decision Record: TimeLocker File Locations Review

- **Owner**: Architecture Team
- **Status**: Accepted
- **Created Date**: 09-11-2025
- **Last Updated**: 09-11-2025
- **Audience**: Engineering Teams, Developers

## 1. Context

This document reviews all system and user file locations used by TimeLocker and their compliance with XDG Base Directory Specification and platform best practices.

The XDG Base Directory Specification defines standard locations for user-specific files:

- **XDG_CONFIG_HOME**: User-specific configuration files (default: `~/.config`)
- **XDG_DATA_HOME**: User-specific data files (default: `~/.local/share`)
- **XDG_CACHE_HOME**: User-specific cache files (default: `~/.cache`)
- **XDG_RUNTIME_DIR**: User-specific runtime files (no default, typically `/run/user/$UID`)
- **XDG_STATE_HOME**: User-specific state data (default: `~/.local/state`)

## 2. Decision

TimeLocker will fully adopt XDG Base Directory Specification for all file locations on Linux, with appropriate platform-specific equivalents for macOS and Windows.

### Current Implementation Status

#### ✅ COMPLIANT: Core Configuration Paths

**Module:** `src/TimeLocker/config/configuration_path_resolver.py`

This module correctly implements XDG standards:

| Purpose | Linux Path | XDG Compliant | Notes |
|---------|-----------|---------------|-------|
| User Config | `$XDG_CONFIG_HOME/timelocker` or `~/.config/timelocker` | ✅ Yes | Correct |
| Cache | `$XDG_CACHE_HOME/timelocker` or `~/.cache/timelocker` | ✅ Yes | Correct |
| Runtime | `$XDG_RUNTIME_DIR/timelocker` or `/tmp/timelocker-$UID` | ✅ Yes | Correct fallback |
| System Config | `/etc/timelocker` or `/etc/xdg/timelocker` | ✅ Yes | Correct |

**Also handles:**
- Project-level config: `./.timelocker/` (correct for project-specific settings)
- Legacy migration from `~/.timelocker/` (good backward compatibility)

#### ✅ COMPLIANT: Platform Compatibility Module

**Module:** `src/TimeLocker/cli_modules/helpers/platform_compat.py`

Correctly implements platform-specific paths:
- Linux: Uses XDG environment variables with proper fallbacks
- macOS: Uses `~/Library/Application Support/TimeLocker`
- Windows: Uses `%APPDATA%\TimeLocker`

#### ⚠️ NON-COMPLIANT: Hardcoded Paths

The following modules use hardcoded paths instead of the centralized path resolver:

1. **Selection Template Manager** (`src/TimeLocker/selection_template_manager.py:114-115`)
   - Issue: Hardcoded `~/.config/timelocker`, ignores `XDG_CONFIG_HOME`
   
2. **Notification Service** (`src/TimeLocker/monitoring/notification_service.py:87`)
   - Issue: Uses legacy `~/.timelocker/` path
   
3. **Status Reporter** (`src/TimeLocker/monitoring/status_reporter.py:91`)
   - Issue: Uses legacy `~/.timelocker/` path
   
4. **Credential Manager** (`src/TimeLocker/security/credential_manager.py:68`)
   - Issue: Uses legacy `~/.timelocker/` path
   
5. **Pattern Group Manager** (`src/TimeLocker/pattern_group_manager.py:57`)
   - Issue: Uses legacy `~/.timelocker/` path
   
6. **Backup Notification Service** (`src/TimeLocker/services/backup_notification_service.py:96`)
   - Issue: Uses legacy `~/.timelocker/` path

7. **Shell Completion Files** (`src/TimeLocker/cli.py:607-624`)
   - Issue: Bash and Zsh completions use home directory instead of XDG paths
   - Note: Fish completion is correct (`~/.config/fish/completions/`)

### Recommended Directory Structure

#### Linux (XDG Compliant)

```
~/.config/timelocker/              # XDG_CONFIG_HOME
├── config.json                    # Main configuration
├── config_backups/                # Configuration backups
└── security/                      # Security configuration
    ├── privacy_config.json
    └── security_events.jsonl

~/.local/share/timelocker/         # XDG_DATA_HOME
├── templates/                     # Selection templates
├── pattern_groups.json            # Pattern groups
├── bash-completion/               # Bash completions
└── zsh/                          # Zsh completions

~/.local/state/timelocker/         # XDG_STATE_HOME
├── status/                        # Status tracking
│   ├── operations.log
│   └── current_operations.json
├── notifications/                 # Notification history
├── audit/                        # Audit logs
│   ├── credential_audit.log
│   └── access.log
└── backup_notifications/         # Backup notification logs

~/.cache/timelocker/               # XDG_CACHE_HOME
└── temp/                         # Temporary files

/run/user/$UID/timelocker/         # XDG_RUNTIME_DIR
└── (runtime files)               # Sockets, PIDs, etc.
```

#### Legacy Path Migration

```
~/.timelocker/                     # LEGACY (to be migrated)
└── (all files should migrate to XDG locations)
```

## 3. Consequences

### Positive Outcomes

- **Standards Compliance**: Full XDG compliance on Linux
- **Better Organization**: Clear separation of config, data, cache, and state
- **User Expectations**: Follows platform conventions users expect
- **Backup Friendly**: Config and data in separate locations
- **Test Isolation**: Easier to isolate tests with environment variables

### Negative Consequences

- **Migration Required**: Existing users need to migrate from `~/.timelocker/`
- **Code Changes**: 6 modules need updates to use centralized path resolver
- **Testing Updates**: All tests need explicit `config_dir` parameters
- **Documentation**: User documentation needs updates

## 4. Alternatives Considered

### Option A: Keep Legacy `~/.timelocker/` Path

- Pros: No migration needed, simpler for existing users
- Cons: Not XDG compliant, doesn't follow platform standards, harder to backup

### Option B: Partial XDG Adoption (Config Only)

- Pros: Smaller migration, less code changes
- Cons: Inconsistent, still not fully compliant, confusing for users

### Option C: Full XDG Adoption with Automatic Migration (CHOSEN)

- Pros: Full standards compliance, clear organization, better user experience
- Cons: Requires migration script, more code changes, testing overhead

## 5. Security Considerations

### Sensitive Data Locations

| Data Type | Current Location | Recommended | Security Level |
|-----------|-----------------|-------------|----------------|
| Credentials | `~/.timelocker/credentials/` | `~/.config/timelocker/credentials/` | High - Encrypted |
| Audit Logs | `~/.timelocker/credentials/` | `~/.local/state/timelocker/audit/` | High - Sensitive |
| Security Events | `~/.config/timelocker/security/` | ✅ Correct | High - Sensitive |
| Config Files | `~/.config/timelocker/` | ✅ Correct | Medium |

**Permissions:**
- Config directory: `700` (rwx------)
- Credential files: `600` (rw-------)
- Audit logs: `600` (rw-------)

## 6. Test Isolation

**Critical:** Tests must never access or modify real user files.

See [test-isolation-strategy.md](./test-isolation-strategy.md) for complete implementation details.

### Quick Summary

Tests should be isolated using:

1. **Environment variable override** - Set `TIMELOCKER_TEST_MODE=1` and override all XDG variables
2. **Test mode detection** - Add `is_test_mode()` to `ConfigurationPathResolver`
3. **Explicit config_dir** - Always pass `config_dir=tmp_path` in tests
4. **Automatic verification** - Add fixture to verify no user files created

## 7. Action Items

### High Priority

1. ✅ **ConfigurationPathResolver** - Already compliant
2. ⚠️ **Test isolation** - Implement environment override and verification (CRITICAL)
3. ⚠️ **Update hardcoded paths** - 6 modules need updates
4. ⚠️ **Shell completion paths** - Bash/Zsh need XDG compliance
5. ⚠️ **Add XDG_STATE_HOME support** - For logs and state data

### Medium Priority

6. **Add XDG_DATA_HOME usage** - For templates and user data
7. **Update all tests** - Add explicit config_dir parameters
8. **Update documentation** - Document all path locations
9. **Migration script** - Automated migration from legacy paths

### Low Priority

10. **Test on all platforms** - Verify Windows/macOS paths
11. **Add path validation** - Ensure permissions are correct
12. **Add configuration option** - Allow users to override paths

# References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [macOS File System Programming Guide](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/)
- [Windows Known Folders](https://docs.microsoft.com/en-us/windows/win32/shell/known-folders)
- [test-isolation-strategy.md](./test-isolation-strategy.md)
- [path-review-summary.md](./path-review-summary.md)
