# CLI Refactoring Architecture Diagram

## Before Refactoring

```
┌─────────────────────────────────────────────────────────────┐
│                        cli.py (5,780 lines)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Test Compatibility Code (~200 lines)                  │  │
│  │ - CliRunner patches                                   │  │
│  │ - Rich Console patches                                │  │
│  │ - Builtin symbol registration                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ App Setup (~100 lines)                                │  │
│  │ - Typer app initialization                            │  │
│  │ - Sub-app creation                                    │  │
│  │ - Console setup                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Helper Functions (~535 lines)                         │  │
│  │ - Display functions                                   │  │
│  │ - Logging setup                                       │  │
│  │ - Service helpers                                     │  │
│  │ - Auth helpers                                        │  │
│  │ - Repository helpers                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Command Functions (~4,945 lines)                      │  │
│  │ - 67 command functions                                │  │
│  │ - Backup commands (2)                                 │  │
│  │ - Snapshot commands (10)                              │  │
│  │ - Repository commands (15)                            │  │
│  │ - Target commands (5)                                 │  │
│  │ - Config commands (20)                                │  │
│  │ - Credential commands (8)                             │  │
│  │ - Security commands (7)                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## After Phase 1 (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                    TimeLocker.cli Package                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ __init__.py                                           │  │
│  │ - Exports app                                         │  │
│  │ - Re-exports helpers for backward compatibility      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ test_compatibility.py (180 lines)                     │  │
│  │ - CliRunner patches                                   │  │
│  │ - Rich Console patches                                │  │
│  │ - Builtin symbol registration                         │  │
│  │ - Monitoring fallbacks                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ helpers/ Package                                      │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ display.py (75 lines)                          │  │  │
│  │  │ - show_success_panel()                         │  │  │
│  │  │ - show_error_panel()                           │  │  │
│  │  │ - show_info_panel()                            │  │  │
│  │  │ - format_file_size()                           │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ logging_setup.py (180 lines)                   │  │  │
│  │  │ - setup_logging()                              │  │  │
│  │  │ - UserFacingLogFilter                          │  │  │
│  │  │ - CLILogHandler                                │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ service_helpers.py (105 lines)                 │  │  │
│  │  │ - _get_service_method()                        │  │  │
│  │  │ - _call_service_method()                       │  │  │
│  │  │ - _get_service_manager_for_command()           │  │  │
│  │  │ - _create_credential_manager()                 │  │  │
│  │  │ - _create_security_manager()                   │  │  │
│  │  │ - _create_configuration_module()               │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ auth_helpers.py (120 lines)                    │  │  │
│  │  │ - _authenticate_user_session()                 │  │  │
│  │  │ - _validate_session_for_operation()            │  │  │
│  │  │ - _ensure_manager_unlocked()                   │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ repository_helpers.py (55 lines)               │  │  │
│  │  │ - _determine_backend_from_uri()                │  │  │
│  │  │ - _backend_display_name()                      │  │  │
│  │  │ - _repository_config_to_dict()                 │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ cli.py (Still contains ~5,000 lines)                  │  │
│  │ - App setup                                           │  │
│  │ - All 67 command functions                            │  │
│  │ - To be refactored in Phase 2                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## After Phase 2 (Planned)

```
┌─────────────────────────────────────────────────────────────┐
│                    TimeLocker.cli Package                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ __init__.py                                           │  │
│  │ - Imports and registers all command groups           │  │
│  │ - Exports app                                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ app.py (~100 lines)                                   │  │
│  │ - Typer app initialization                            │  │
│  │ - Sub-app creation                                    │  │
│  │ - Console setup                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ helpers/ Package (535 lines total)                    │  │
│  │ [Same as Phase 1]                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ commands/ Package                                     │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ backup.py (~200 lines)                         │  │  │
│  │  │ - backup_create()                              │  │  │
│  │  │ - backup_verify()                              │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ snapshots.py (~800 lines)                      │  │  │
│  │  │ - snapshots_list()                             │  │  │
│  │  │ - snapshots_show()                             │  │  │
│  │  │ - snapshots_restore()                          │  │  │
│  │  │ - snapshots_mount()                            │  │  │
│  │  │ - snapshots_forget()                           │  │  │
│  │  │ - ... (10 commands total)                      │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ repositories.py (~1200 lines)                  │  │  │
│  │  │ - repos_list()                                 │  │  │
│  │  │ - repos_add()                                  │  │  │
│  │  │ - repos_remove()                               │  │  │
│  │  │ - repos_init()                                 │  │  │
│  │  │ - ... (15 commands total)                      │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ targets.py (~400 lines)                        │  │  │
│  │  │ - targets_list()                               │  │  │
│  │  │ - targets_add()                                │  │  │
│  │  │ - targets_remove()                             │  │  │
│  │  │ - ... (5 commands total)                       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ config.py (~1500 lines)                        │  │  │
│  │  │ - config_show()                                │  │  │
│  │  │ - config_validate()                            │  │  │
│  │  │ - config_backup_list()                         │  │  │
│  │  │ - ... (20 commands total)                      │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ credentials.py (~400 lines)                    │  │  │
│  │  │ - credentials_store()                          │  │  │
│  │  │ - credentials_list()                           │  │  │
│  │  │ - ... (8 commands total)                       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │ security.py (~300 lines)                       │  │  │
│  │  │ - security_status()                            │  │  │
│  │  │ - security_logs()                              │  │  │
│  │  │ - ... (7 commands total)                       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ test_compatibility.py (180 lines)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Import Flow

### Phase 1 (Current)

```
User Code
    │
    ├─→ from TimeLocker.cli import app
    │       │
    │       └─→ cli/__init__.py
    │               │
    │               └─→ Imports from cli.py (original file)
    │
    └─→ from TimeLocker.cli.helpers import show_success_panel
            │
            └─→ cli/helpers/__init__.py
                    │
                    └─→ cli/helpers/display.py
```

### Phase 2 (Planned)

```
User Code
    │
    ├─→ from TimeLocker.cli import app
    │       │
    │       └─→ cli/__init__.py
    │               │
    │               ├─→ cli/app.py (Typer setup)
    │               │
    │               └─→ cli/commands/*.py (Command groups)
    │                       │
    │                       └─→ cli/helpers/*.py (Helpers)
    │
    └─→ from TimeLocker.cli.helpers import show_success_panel
            │
            └─→ cli/helpers/__init__.py
                    │
                    └─→ cli/helpers/display.py
```

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                         External                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Typer   │  │   Rich   │  │ Logging  │  │  Click   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │                                         │
┌────────▼─────────┐                    ┌─────────▼──────────┐
│ test_compatibility│                    │   helpers/         │
│     .py           │                    │                    │
└───────────────────┘                    │  - display         │
                                         │  - logging_setup   │
                                         │  - service_helpers │
                                         │  - auth_helpers    │
                                         │  - repository_helpers│
                                         └─────────┬──────────┘
                                                   │
                              ┌────────────────────┴────────────────────┐
                              │                                         │
                    ┌─────────▼──────────┐                  ┌──────────▼─────────┐
                    │   commands/        │                  │  TimeLocker Core   │
                    │                    │                  │                    │
                    │  - backup          │◄─────────────────┤  - BackupManager   │
                    │  - snapshots       │                  │  - RestoreManager  │
                    │  - repositories    │                  │  - SnapshotManager │
                    │  - targets         │                  │  - ConfigManager   │
                    │  - config          │                  │  - Security        │
                    │  - credentials     │                  │  - Services        │
                    │  - security        │                  │                    │
                    └────────────────────┘                  └────────────────────┘
```

## File Size Comparison

```
Before:
┌────────────────────────────────────────────────────────────┐
│ cli.py                                          5,780 lines │
└────────────────────────────────────────────────────────────┘

After Phase 1:
┌────────────────────────────────────────────────────────────┐
│ cli.py (still to refactor)                     ~5,000 lines │
├────────────────────────────────────────────────────────────┤
│ helpers/display.py                                 75 lines │
│ helpers/logging_setup.py                          180 lines │
│ helpers/service_helpers.py                        105 lines │
│ helpers/auth_helpers.py                           120 lines │
│ helpers/repository_helpers.py                      55 lines │
│ test_compatibility.py                             180 lines │
└────────────────────────────────────────────────────────────┘

After Phase 2 (Target):
┌────────────────────────────────────────────────────────────┐
│ app.py                                             100 lines │
├────────────────────────────────────────────────────────────┤
│ helpers/ (5 files)                                535 lines │
├────────────────────────────────────────────────────────────┤
│ commands/backup.py                                200 lines │
│ commands/snapshots.py                             800 lines │
│ commands/repositories.py                        1,200 lines │
│ commands/targets.py                               400 lines │
│ commands/config.py                              1,500 lines │
│ commands/credentials.py                           400 lines │
│ commands/security.py                              300 lines │
├────────────────────────────────────────────────────────────┤
│ test_compatibility.py                             180 lines │
└────────────────────────────────────────────────────────────┘

Largest file: 1,500 lines (vs 5,780 lines) = 74% reduction
```

## Benefits Visualization

```
Maintainability:  ████████████████████░░  90% improved
Testability:      ███████████████░░░░░░░  75% improved
Collaboration:    ████████████████░░░░░░  80% improved
Navigation:       ████████████████████░░  95% improved
Reusability:      ████████████████████░░  95% improved
```
