# TimeLocker File Locations Review

## Overview

This document reviews all system and user file locations used by TimeLocker and their compliance with XDG Base Directory Specification and platform best practices.

**Review Date:** 2025-11-09  
**Status:** In Progress

---

## XDG Base Directory Specification (Linux)

The XDG Base Directory Specification defines standard locations for user-specific files:

- **XDG_CONFIG_HOME**: User-specific configuration files (default: `~/.config`)
- **XDG_DATA_HOME**: User-specific data files (default: `~/.local/share`)
- **XDG_CACHE_HOME**: User-specific cache files (default: `~/.cache`)
- **XDG_RUNTIME_DIR**: User-specific runtime files (no default, typically `/run/user/$UID`)
- **XDG_STATE_HOME**: User-specific state data (default: `~/.local/state`)

---

## Current Implementation Status

### ✅ COMPLIANT: Core Configuration Paths

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

### ✅ COMPLIANT: Platform Compatibility Module

**Module:** `src/TimeLocker/cli_modules/helpers/platform_compat.py`

Correctly implements platform-specific paths:
- Linux: Uses XDG environment variables with proper fallbacks
- macOS: Uses `~/Library/Application Support/TimeLocker`
- Windows: Uses `%APPDATA%\TimeLocker`

---

## ⚠️ NON-COMPLIANT: Hardcoded Paths

The following modules use hardcoded paths instead of the centralized path resolver:

### 1. Selection Template Manager

**File:** `src/TimeLocker/selection_template_manager.py:114-115`

```python
# CURRENT (NON-COMPLIANT)
config_home = Path.home() / ".config" / "timelocker"
storage_dir = config_home / "templates"
```

**Issue:** Hardcoded `~/.config/timelocker`, ignores `XDG_CONFIG_HOME`

**Recommendation:**
```python
from ..config.configuration_path_resolver import ConfigurationPathResolver
config_dir = ConfigurationPathResolver.get_config_directory()
storage_dir = config_dir / "templates"
```

---

### 2. Notification Service

**File:** `src/TimeLocker/monitoring/notification_service.py:87`

```python
# CURRENT (NON-COMPLIANT)
config_dir = Path.home() / ".timelocker" / "notifications"
```

**Issue:** Uses legacy `~/.timelocker/` path

**Recommendation:**
```python
from ..config.configuration_path_resolver import ConfigurationPathResolver
config_dir = ConfigurationPathResolver.get_config_directory() / "notifications"
```

---

### 3. Status Reporter

**File:** `src/TimeLocker/monitoring/status_reporter.py:91`

```python
# CURRENT (NON-COMPLIANT)
config_dir = Path.home() / ".timelocker" / "status"
```

**Issue:** Uses legacy `~/.timelocker/` path

**Recommendation:**
```python
from ..config.configuration_path_resolver import ConfigurationPathResolver
config_dir = ConfigurationPathResolver.get_config_directory() / "status"
```

---

### 4. Credential Manager

**File:** `src/TimeLocker/security/credential_manager.py:68`

```python
# CURRENT (NON-COMPLIANT)
config_dir = Path.home() / ".timelocker" / "credentials"
```

**Issue:** Uses legacy `~/.timelocker/` path

**Recommendation:**
```python
from ..config.configuration_path_resolver import ConfigurationPathResolver
config_dir = ConfigurationPathResolver.get_config_directory() / "credentials"
```

---

### 5. Pattern Group Manager

**File:** `src/TimeLocker/pattern_group_manager.py:57`

```python
# CURRENT (NON-COMPLIANT)
self.config_path = config_path or Path.home() / ".timelocker" / "pattern_groups.json"
```

**Issue:** Uses legacy `~/.timelocker/` path

**Recommendation:**
```python
from .config.configuration_path_resolver import ConfigurationPathResolver
self.config_path = config_path or ConfigurationPathResolver.get_config_directory() / "pattern_groups.json"
```

---

### 6. Backup Notification Service

**File:** `src/TimeLocker/services/backup_notification_service.py:96`

```python
# CURRENT (NON-COMPLIANT)
config_dir = Path.home() / ".timelocker" / "backup_notifications"
```

**Issue:** Uses legacy `~/.timelocker/` path

**Recommendation:**
```python
from ..config.configuration_path_resolver import ConfigurationPathResolver
config_dir = ConfigurationPathResolver.get_config_directory() / "backup_notifications"
```

---

### 7. Shell Completion Files

**File:** `src/TimeLocker/cli.py:607-624`

```python
# CURRENT (PARTIALLY NON-COMPLIANT)
"bash": {
    "completion_file": home / ".timelocker-complete.bash",
    "rc_file": home / ".bashrc",
    ...
},
"zsh": {
    "completion_file": home / ".timelocker-complete.zsh",
    "rc_file": home / ".zshrc",
    ...
},
"fish": {
    "completion_file": home / ".config" / "fish" / "completions" / "timelocker.fish",
    ...
}
```

**Issue:** Bash and Zsh completions use home directory instead of XDG paths

**Recommendation:**
```python
"bash": {
    "completion_file": PathHandler.get_data_dir() / "bash-completion" / "completions" / "timelocker",
    # Or for user-specific: ~/.local/share/bash-completion/completions/timelocker
    ...
},
"zsh": {
    "completion_file": PathHandler.get_data_dir() / "zsh" / "site-functions" / "_timelocker",
    # Or for user-specific: ~/.local/share/zsh/site-functions/_timelocker
    ...
}
```

**Note:** Fish completion is correct (`~/.config/fish/completions/`)

---

## Missing XDG Directories

### XDG_DATA_HOME Usage

**Current Status:** Not fully utilized

**Recommendation:** Use `$XDG_DATA_HOME/timelocker` (default: `~/.local/share/timelocker`) for:
- Application state that should persist
- User-generated data files
- Templates and pattern groups
- Completion scripts

**Implementation:**
```python
# Add to ConfigurationPathResolver
@staticmethod
def get_data_directory() -> Path:
    """Get data directory following XDG specification."""
    if ConfigurationPathResolver.is_system_context():
        if os.name == "nt":
            program_data = os.environ.get('PROGRAMDATA', r'C:\\ProgramData')
            return Path(program_data) / "timelocker" / "data"
        else:
            return Path("/usr/share/timelocker")
    else:
        xdg_data_home = os.environ.get('XDG_DATA_HOME')
        if xdg_data_home:
            return Path(xdg_data_home) / "timelocker"
        else:
            return Path.home() / ".local" / "share" / "timelocker"
```

### XDG_STATE_HOME Usage

**Current Status:** Not implemented

**Recommendation:** Use `$XDG_STATE_HOME/timelocker` (default: `~/.local/state/timelocker`) for:
- Operation logs and history
- Status tracking
- Audit logs
- Notification history

---

## Recommended Directory Structure

### Linux (XDG Compliant)

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

### Legacy Path Migration

```
~/.timelocker/                     # LEGACY (to be migrated)
└── (all files should migrate to XDG locations)
```

---

## Security Considerations

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

---

## Test Isolation

**Critical:** Tests must never access or modify real user files.

See [Test Isolation Strategy](./test-isolation-strategy.md) for complete implementation details.

### Quick Summary

Tests should be isolated using:

1. **Environment variable override** - Set `TIMELOCKER_TEST_MODE=1` and override all XDG variables
2. **Test mode detection** - Add `is_test_mode()` to `ConfigurationPathResolver`
3. **Explicit config_dir** - Always pass `config_dir=tmp_path` in tests
4. **Automatic verification** - Add fixture to verify no user files created

**Example:**
```python
def test_something(tmp_path):
    config_dir = tmp_path / "config"
    cm = CredentialManager(config_dir=config_dir)
    # Test uses tmp_path, never touches ~/.timelocker/
```

---

## Action Items

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

---

## Testing Checklist

- [ ] Test with `XDG_CONFIG_HOME` set
- [ ] Test with `XDG_CACHE_HOME` set
- [ ] Test with `XDG_DATA_HOME` set
- [ ] Test with `XDG_RUNTIME_DIR` set
- [ ] Test with `XDG_STATE_HOME` set
- [ ] Test legacy migration
- [ ] Test system context (root)
- [ ] Test Windows paths
- [ ] Test macOS paths
- [ ] Test permission handling

---

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [macOS File System Programming Guide](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/)
- [Windows Known Folders](https://docs.microsoft.com/en-us/windows/win32/shell/known-folders)
