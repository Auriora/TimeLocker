# Module-Specific Imports Reference

This document lists all the specific imports needed for each command module after extraction.

## Security Module (`security.py`)

```python
# Security-specific imports
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    AccessManager,
    RepositoryInfo,
    RepositoryMode,
    ConfirmationDialogs
)

# Completion
from TimeLocker.completion import repository_completer

# Additional
from datetime import datetime, timedelta
```

**Used in commands**:
- `security_status` - SecurityService, CredentialManager, AccessManager
- `security_logs` - SecurityService
- `security_notifications` - SecurityService
- `security_sessions` - AccessManager
- `security_cleanup` - SecurityService, AccessManager
- `security_config` - SecurityService

---

## Credentials Module (`credentials.py`)

```python
# Credential management
from TimeLocker.security.credential_manager import (
    CredentialManager,
    CredentialManagerError
)

# Repository management
from TimeLocker.config.configuration_manager import ConfigurationManager

# Completion
from TimeLocker.completion import repository_name_completer

# Additional
from getpass import getpass
```

**Used in commands**:
- `credentials_unlock` - CredentialManager
- `credentials_store` - CredentialManager, ConfigurationManager
- `credentials_set` - CredentialManager
- `credentials_list` - CredentialManager
- `credentials_remove` - CredentialManager
- `credentials_show` - CredentialManager
- `credentials_lock` - CredentialManager
- `credentials_change_password` - CredentialManager

---

## Snapshots Module (`snapshots.py`)

```python
# Snapshot management
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager

# Repository management
from TimeLocker.backup_manager import BackupManager

# Configuration
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)

# Interfaces
from TimeLocker.interfaces.exceptions import ConfigurationError

# Completion
from TimeLocker.completion import (
    snapshot_id_completer,
    repository_completer,
    file_path_completer
)

# Utils
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri,
    get_default_repository
)
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format

# Additional
from datetime import datetime
import subprocess
```

**Used in commands**:
- `snapshots_list` - SnapshotManager, validate_repository_name_or_uri
- `snapshots_show` - SnapshotManager, validate_snapshot_id_format
- `snapshots_restore` - RestoreManager, validate_repository_name_or_uri
- `snapshots_contents` - SnapshotManager
- `snapshots_mount` - SnapshotManager, subprocess
- `snapshots_umount` - SnapshotManager, subprocess
- `snapshots_forget` - SnapshotManager
- `snapshots_find` - SnapshotManager
- `snapshots_find_in` - SnapshotManager
- `snapshots_prune` - SnapshotManager
- `snapshots_diff` - SnapshotManager

---

## Repositories Module (`repositories.py`)

```python
# Repository management
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.services.repository_factory import RepositoryFactory

# Configuration
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config import ConfigurationModule

# Security
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    RepositoryInfo,
    RepositoryMode
)

# Backup management
from TimeLocker.backup_manager import BackupManager

# Completion
from TimeLocker.completion import (
    repository_name_completer,
    repository_completer,
    repository_uri_completer
)

# Utils
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri
)

# CLI helpers
from TimeLocker.cli_helpers import store_backend_credentials as store_backend_credentials_helper

# Additional
from urllib.parse import urlparse
import re
```

**Used in commands**:
- `repos_list` - ConfigurationManager, RepositoryService
- `repos_add` - ConfigurationManager, validate_repository_name_or_uri, urlparse
- `repos_show` - ConfigurationManager, RepositoryService
- `repos_remove` - ConfigurationManager, SecurityService
- `repos_update` - ConfigurationManager
- `repos_default` - ConfigurationManager
- `repos_clear_default` - ConfigurationManager
- `repos_lock` - SecurityService, RepositoryInfo
- `repos_unlock` - SecurityService, RepositoryInfo
- `repos_mode` - SecurityService, RepositoryMode
- `repos_protection_status` - SecurityService
- `repos_init` - BackupManager, RepositoryFactory
- `repos_migrate` - BackupManager
- `repos_forget` - BackupManager
- `repos_check` - BackupManager
- `repos_stats` - BackupManager
- `repos_check_all` - ConfigurationManager, BackupManager
- `repos_stats_all` - ConfigurationManager, BackupManager
- `repos_credentials_set` - CredentialManager, store_backend_credentials_helper
- `repos_credentials_remove` - CredentialManager
- `repos_credentials_show` - CredentialManager

---

## Config Module (`config.py`)

```python
# Configuration management
from TimeLocker.config import (
    ConfigurationModule,
    ConfigurationValidator
)
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager,
    BackupReason
)
from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver

# Importers
from TimeLocker.importers.timeshift_importer import (
    TimeshiftConfigParser,
    TimeshiftToTimeLockerMapper
)

# Interfaces
from TimeLocker.interfaces.exceptions import ConfigurationError

# Additional
from datetime import datetime
import json
from difflib import unified_diff
```

**Used in commands**:
- `config_show` - ConfigurationModule, ConfigurationValidator
- `config_setup` - ConfigurationModule
- `config_validate` - ConfigurationValidator, ConfigurationModule
- `config_diff` - ConfigurationModule, unified_diff
- `config_health_check` - ConfigurationModule, ConfigurationManager
- `config_backup_list` - ConfigurationBackupManager, ConfigurationPathResolver
- `config_backup_create` - ConfigurationBackupManager, BackupReason, ConfigurationPathResolver
- `config_backup_restore` - ConfigurationBackupManager, ConfigurationPathResolver
- `config_backup_compare` - ConfigurationBackupManager, ConfigurationPathResolver
- `config_lock_status` - ConfigurationPathResolver
- `config_lock_cleanup` - ConfigurationPathResolver
- `config_performance` - ConfigurationModule
- `config_import_restic` - ConfigurationModule (via service manager)
- `config_import_timeshift` - TimeshiftConfigParser, TimeshiftToTimeLockerMapper, ConfigurationModule

---

## Backup Module (`backup.py`) - Already Extracted

**Current imports** (for reference):
```python
from TimeLocker.cli_services import get_cli_service_manager, CLIBackupRequest
from TimeLocker.completion import (
    file_path_completer,
    repository_completer,
    target_name_completer,
    snapshot_id_completer,
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import RepositoryNotFoundError
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.utils.repository_resolver import validate_repository_name_or_uri
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format
```

---

## Targets Module (`targets.py`) - Already Extracted

**Current imports** (for reference):
```python
from TimeLocker.cli_services import get_cli_service_manager
from TimeLocker.completion import target_name_completer, file_path_completer
```

---

## Common Imports (Already in base.py)

These are available to all modules through `from .base import ...`:

```python
# Base functionality
from .base import (
    CommandBase,
    create_typer_app,
    with_error_handling,
    with_logging,
    with_service_manager,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    _get_service_method,
    _call_service_method,
    _get_service_manager_for_command,
    _create_configuration_module,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
    ValidationError,
    validate_not_empty,
    validate_path_exists,
)

# Standard library (already imported in base)
import sys
import logging
from typing import Optional, List, Annotated, Dict, Any
from pathlib import Path

# Typer and Rich (already imported in base)
import typer
import click
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# CLI module reference (for transition)
from TimeLocker import cli as _cli_module
from TimeLocker.cli_services import get_cli_service_manager
```

---

## Import Template for Each Module

### Security Module Template

```python
"""Security management commands."""

# Base imports (Phase 3 patterns)
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    console,
    VerboseOption,
    ConfigDirOption,
)

# Standard library
from datetime import datetime, timedelta

# TimeLocker imports
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    AccessManager,
    RepositoryInfo,
    RepositoryMode,
    ConfirmationDialogs
)
from TimeLocker.completion import repository_completer

# Create app
security_app = create_typer_app("security", "Security management commands")
```

### Credentials Module Template

```python
"""Credential management commands."""

# Base imports
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    console,
    VerboseOption,
    ConfigDirOption,
)

# Standard library
from getpass import getpass

# TimeLocker imports
from TimeLocker.security.credential_manager import (
    CredentialManager,
    CredentialManagerError
)
from TimeLocker.config.configuration_manager import ConfigurationManager
from TimeLocker.completion import repository_name_completer

# Create app
credentials_app = create_typer_app("credentials", "Credential management commands")
```

### Snapshots Module Template

```python
"""Snapshot operations."""

# Base imports
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    VerboseOption,
    JsonOption,
    ConfigDirOption,
)

# Standard library
from datetime import datetime
import subprocess

# TimeLocker imports
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.backup_manager import BackupManager
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.interfaces.exceptions import ConfigurationError
from TimeLocker.completion import (
    snapshot_id_completer,
    repository_completer,
    file_path_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri,
    get_default_repository
)
from TimeLocker.utils.snapshot_validation import validate_snapshot_id_format

# Create app
snapshots_app = create_typer_app("snapshots", "Snapshot operations")
```

### Repositories Module Template

```python
"""Repository operations."""

# Base imports
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
)

# Standard library
from urllib.parse import urlparse
import re

# TimeLocker imports
from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.services.repository_factory import RepositoryFactory
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config import ConfigurationModule
from TimeLocker.security import (
    SecurityService,
    CredentialManager,
    RepositoryInfo,
    RepositoryMode
)
from TimeLocker.backup_manager import BackupManager
from TimeLocker.completion import (
    repository_name_completer,
    repository_completer,
    repository_uri_completer
)
from TimeLocker.utils.repository_resolver import (
    validate_repository_name_or_uri,
    resolve_repository_uri
)
from TimeLocker.cli_helpers import store_backend_credentials as store_backend_credentials_helper

# Create app
repos_app = create_typer_app("repos", "Repository operations")
```

### Config Module Template

```python
"""Configuration management commands."""

# Base imports
from .base import (
    create_typer_app,
    with_error_handling,
    with_logging,
    show_success_panel,
    show_error_panel,
    show_info_panel,
    console,
    VerboseOption,
    JsonOption,
    YesOption,
    ConfigDirOption,
    DryRunOption,
)

# Standard library
from datetime import datetime
import json
from difflib import unified_diff

# TimeLocker imports
from TimeLocker.config import (
    ConfigurationModule,
    ConfigurationValidator
)
from TimeLocker.config.configuration_manager import (
    ConfigurationManager,
    RepositoryNotFoundError
)
from TimeLocker.config.configuration_backup_manager import (
    ConfigurationBackupManager,
    BackupReason
)
from TimeLocker.config.configuration_path_resolver import ConfigurationPathResolver
from TimeLocker.importers.timeshift_importer import (
    TimeshiftConfigParser,
    TimeshiftToTimeLockerMapper
)
from TimeLocker.interfaces.exceptions import ConfigurationError

# Create app
config_app = create_typer_app("config", "Configuration management commands")
```

---

## Quick Reference Table

| Module | Key Imports | Count |
|--------|-------------|-------|
| security | SecurityService, CredentialManager, AccessManager | 3 |
| credentials | CredentialManager, ConfigurationManager | 2 |
| snapshots | SnapshotManager, RestoreManager, BackupManager | 3 |
| repositories | RepositoryManager, RepositoryService, SecurityService | 3+ |
| config | ConfigurationModule, ConfigurationValidator, BackupManager | 3+ |

---

## Usage

When the extraction script generates a module with:
```python
# Module-specific imports will be added as needed
# TODO: Review and add specific imports for this module
```

Replace that section with the appropriate template from above.

---

## Verification

After adding imports, verify with:

```bash
# Check syntax
python -m py_compile src/TimeLocker/cli_modules/commands/{module}.py

# Test import
python -c "from TimeLocker.cli_modules.commands import {module}_app; print('✓ OK')"
```

---

## Notes

1. **Import from base first**: Always import common functionality from `.base`
2. **Minimize imports**: Only import what's actually used in the module
3. **Group imports**: Standard library, then TimeLocker, then third-party
4. **Use TYPE_CHECKING**: For type hints only, use `from typing import TYPE_CHECKING`
5. **Avoid circular imports**: Import from parent modules, not siblings

---

**Last Updated**: 2025-11-07  
**Status**: Complete reference for all 5 remaining modules
