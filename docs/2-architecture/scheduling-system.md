---
title: "Architecture Document: Scheduling System"
id: "arch-scheduling-system"
type: [ architecture ]
status: [ approved ]
owner: "Architecture Team"
last_reviewed: "13-11-2025"
tags: [architecture, scheduling, automation, platform-integration]
links:
    tooling: []
---

# Architecture Document: Scheduling System

- **Owner**: Architecture Team
- **Status**: Approved
- **Created Date**: 13-11-2025
- **Last Updated**: 13-11-2025
- **Audience**: Engineering Teams, Platform Integration Developers

## 1. Context

The Scheduling System provides comprehensive automated backup scheduling capabilities for TimeLocker through platform-appropriate system schedulers. It enables
unattended backup operations by integrating with native OS scheduling systems (systemd timers, cron, Windows Task Scheduler, launchd) while coordinating with
Policy Management, Data Selection, Repository Management, and Monitoring systems.

The design emphasizes cross-platform compatibility, secure credential management, and seamless integration with existing TimeLocker architecture. The system
automatically detects the appropriate platform scheduler and generates native configurations while maintaining consistent behavior across all supported
platforms.

## 2. Architecture

### 2.1 Component Overview

The Scheduling System consists of four primary layers:

1. **Schedule Manager**: Central orchestrator for all scheduling operations
2. **Platform Adapters**: Platform-specific scheduling implementations
3. **Script Generator**: Generates platform-specific wrapper scripts
4. **Automation Engine**: Handles execution of scheduled backups

### 2.2 Implementation Location

- **Base Directory**: `/src/TimeLocker/scheduling/`
- **CLI Integration**: `/src/TimeLocker/cli_modules/commands/schedule.py`

### 2.3 Core Components

#### Schedule Manager (`schedule_manager.py`)

Central manager for backup scheduling operations with responsibilities:

- Schedule creation and management
- Platform adapter coordination
- Integration with TimeLocker systems
- Audit trail maintenance

**Key Methods**:

- `create_scheduled_backup()` - Create new scheduled backup from policy
- `update_scheduled_backup()` - Update existing schedule configuration
- `delete_scheduled_backup()` - Remove schedule and cleanup platform scheduler
- `list_scheduled_backups()` - List all scheduled backups with filtering
- `get_schedule_status()` - Get current status and next run time

#### Platform Adapters

Platform-specific scheduling implementations with unified interface:

- **systemd Adapter** (`systemd_adapter.py`) - systemd timer adapter for Linux
- **Cron Adapter** (`cron_adapter.py`) - cron adapter for Unix-like systems
- **Windows Task Scheduler Adapter** (`windows_adapter.py`) - Windows scheduled task adapter
- **launchd Adapter** (`launchd_adapter.py`) - launchd adapter for macOS

**Common Interface**:

- `create_schedule()` - Create platform-specific scheduled task
- `update_schedule()` - Update existing scheduled task
- `delete_schedule()` - Remove scheduled task
- `get_schedule_status()` - Get platform-specific status
- `list_schedules()` - List all scheduled tasks

#### Platform Detection (`platform_detector.py`)

Detects platform capabilities and selects appropriate scheduler:

- Automatic detection of best available scheduler
- Capability checking (systemd, cron, Task Scheduler, launchd)
- Fallback mechanism for unsupported platforms

#### Script Generator (`script_generator.py`)

Generates platform-specific wrapper scripts with:

- Environment setup and credential loading
- Error handling and logging integration
- Monitoring integration
- Retry logic and timeout handling

#### Automation Engine (`automation_engine.py`)

Handles execution of scheduled backup operations:

- Backup execution coordination
- Integration with all TimeLocker systems
- Error handling and retry logic
- Monitoring and audit logging

### 2.4 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Scheduling System                        │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Schedule        │  │ Platform       │  │ Script       │ │
│  │ Manager         │  │ Adapters       │  │ Generator    │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Automation      │  │ Credential     │  │ Audit        │ │
│  │ Engine          │  │ Integration    │  │ Logger       │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                Platform Schedulers                          │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ systemd Timers  │  │ Cron           │  │ Task         │ │
│  │ (Linux)         │  │ (Unix-like)    │  │ Scheduler    │ │
│  └─────────────────┘  └────────────────┘  │ (Windows)    │ │
│                                            └──────────────┘ │
│  ┌─────────────────┐                                        │
│  │ launchd         │                                        │
│  │ (macOS)         │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              TimeLocker Core Systems                        │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Policy          │  │ Data           │  │ Repository   │ │
│  │ Management      │  │ Selection      │  │ Management   │ │
│  └─────────────────┘  └────────────────┘  └──────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌────────────────┐                   │
│  │ Backup          │  │ Monitoring &   │                   │
│  │ Operations      │  │ Reporting      │                   │
│  └─────────────────┘  └────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## 3. Data Models

### Core Models (`scheduling_models.py`)

**ScheduleConfig**: Configuration for a scheduled backup

- schedule_id, name, description
- policy_id reference
- schedule_pattern (cron, interval, calendar)
- enabled flag, timeouts, retry config
- monitoring configuration
- platform-specific settings

**SchedulePattern**: Defines when backup should execute

- pattern_type (cron, interval, calendar)
- cron_expression, interval_minutes
- calendar_config for day/time scheduling
- backup_window for time restrictions

**ExecutionContext**: Context information for backup execution

- execution_id, schedule_id
- triggered_by (scheduled, manual, retry, test)
- start_time, platform, user_context

**ExecutionResult**: Result of scheduled backup execution

- execution_id, schedule_id, status
- backup_result, execution_time
- error_details, retry information

## 4. Security Features

### Credential Management (`credential_integration.py`)

Integrates with platform-specific credential stores:

- **Windows**: Windows Credential Manager + DPAPI
- **macOS**: Keychain Services
- **Linux**: Secret Service API (libsecret)
- **Fallback**: Encrypted file-based storage

### Audit Logging (`audit_logger.py`)

Comprehensive audit trails for compliance:

- Schedule creation/modification/deletion events
- Execution start/completion/failure events
- Credential access events
- Platform scheduler interactions

## 5. Testing and Validation

### Testing Components

**Schedule Testing** (`schedule_testing.py`):

- Schedule validation testing
- Execution simulation
- Platform adapter testing

**Integration Testing** (`integration_testing.py`):

- End-to-end scheduling workflow
- Cross-platform compatibility
- TimeLocker system integration
- External integration client testing

### Validation (`schedule_validator.py`)

Validates schedule configurations:

- Schedule pattern validation
- Policy compatibility checks
- Platform capability verification
- Conflict detection

## 6. Configuration

### Scheduling Configuration (`scheduling_configuration.py`)

Master configuration for scheduling system:

- Platform preferences and defaults
- Retry configuration defaults
- Monitoring configuration defaults
- Audit retention settings
- Execution limits and timeouts

## 7. Error Handling

### Exception Hierarchy (`scheduling_exceptions.py`)

- `SchedulingError` - Base exception
- `PlatformSchedulerError` - Platform operation failed
- `PolicyValidationError` - Policy validation failed
- `DataSelectionValidationError` - Selection validation failed
- `RepositoryValidationError` - Repository access failed
- `CredentialAccessError` - Credential access failed
- `ExecutionTimeoutError` - Execution timeout
- `ScheduleConflictError` - Schedule conflict detected

### Recovery Strategies

1. **Platform Scheduler Failures**: Retry with exponential backoff
2. **Credential Access Failures**: Secure retry with user notification
3. **Validation Failures**: Skip execution with detailed logging
4. **Repository Access Failures**: Retry with backoff
5. **Execution Timeouts**: Graceful termination with cleanup
6. **Schedule Conflicts**: Automatic rescheduling

## 8. Performance Considerations

### Schedule Storage (`schedule_storage.py`)

Efficient storage and retrieval:

- JSON-based configuration storage
- XDG-compliant directory structure
- Indexed schedule lookups
- Efficient list operations

### Utilities (`schedule_utilities.py`)

Performance-optimized utilities:

- Schedule pattern parsing
- Next run time calculation
- Time window validation
- Conflict detection algorithms

## 9. Monitoring and Compliance

### Compliance Reporting (`compliance_reporter.py`)

Generates compliance reports:

- Execution history tracking
- Success/failure rate analysis
- SLA compliance monitoring
- Audit trail export

### Integration with Monitoring System

Deep integration with TimeLocker monitoring:

- Real-time execution status
- Performance metrics collection
- Alert generation for failures
- Dashboard integration

## 10. CLI Integration

Accessible through `schedule` command namespace:

```bash
# Create schedule from policy
timelocker schedule create --policy-id <id> --pattern "0 2 * * *"

# List schedules
timelocker schedule list

# Get schedule status
timelocker schedule status <schedule-id>

# Enable/disable schedule
timelocker schedule enable <schedule-id>
timelocker schedule disable <schedule-id>

# Delete schedule
timelocker schedule delete <schedule-id>

# Test schedule execution
timelocker schedule test <schedule-id> --dry-run
```

## 11. Design Principles

- **Platform Native**: Leverage native OS scheduling for reliability
- **Security First**: Secure credential management throughout
- **Integration Focused**: Deep integration with TimeLocker systems
- **Audit Compliant**: Comprehensive audit trails
- **Failure Resilient**: Robust error handling and recovery
- **Performance Aware**: Minimal overhead and efficient operations

## 12. Future Enhancements

1. **Advanced Scheduling**: Complex calendar-based patterns
2. **Load Balancing**: Intelligent distribution of scheduled tasks
3. **Central Management**: Remote schedule management for enterprise
4. **Advanced Monitoring**: Predictive failure detection
5. **Multi-Repository**: Schedule coordination across repositories

## References

- [Scheduling & Automation Design](.kiro/specs/scheduling-automation/design.md)
- [CLI Schedule Commands](../3-implementation/cli-modules.md)
- [Policy Management](policy-management.md)
- [Monitoring & Reporting](monitoring-reporting.md)
