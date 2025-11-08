# Backup Notification and Error Reporting Enhancement

**Date**: 2025-11-08  
**Status**: Completed  
**Related Spec**: `.kiro/specs/backup-operations/tasks.md` - Task 9

## Overview

Enhanced the backup operations system with comprehensive notification and error reporting capabilities. This implementation provides detailed error classification, remediation guidance, notification filtering, and backup-specific notification templates.

## Changes Made

### 1. Backup Error Reporter (`src/TimeLocker/services/backup_error_reporter.py`)

Created a comprehensive error reporting system that:

- **Error Classification**: Automatically classifies errors into categories:
  - Transient errors (temporary issues, retryable)
  - Configuration errors (invalid settings, missing credentials)
  - Tool-specific errors (backup tool issues)
  - Resource errors (disk space, memory)
  - Network errors (connectivity, timeouts)
  - Permission errors (access denied)
  - Data integrity errors (corruption, checksum failures)

- **Severity Assessment**: Determines error severity (LOW, MEDIUM, HIGH, CRITICAL)

- **Remediation Guidance**: Provides actionable remediation steps for each error category:
  - Step-by-step instructions
  - Command examples where applicable
  - Documentation links
  - Automated vs manual indicators

- **Warning Management**: Creates warnings with suggestions for non-critical issues

**Key Classes**:
- `BackupError`: Detailed error information with remediation steps
- `BackupWarning`: Non-critical warnings with suggestions
- `BackupErrorReporter`: Main service for error classification and reporting
- `ErrorCategory`: Enum for error categories
- `ErrorSeverity`: Enum for severity levels
- `RemediationStep`: Structured remediation guidance

### 2. Backup Notification Service (`src/TimeLocker/services/backup_notification_service.py`)

Created a backup-specific notification service that extends the base notification system:

- **Event-Based Notifications**: Supports multiple backup event types:
  - Backup started/progress/completed/failed
  - Integrity check events
  - Retry attempts
  - Repository errors
  - Warnings

- **Notification Filtering**: Intelligent filtering based on:
  - Minimum operation duration (avoid spam for quick operations)
  - Progress update intervals (configurable, default 5 minutes)
  - Event type (warnings, errors, success)
  - Error severity levels
  - Excluded event types

- **Notification Templates**: Pre-configured templates for each event type:
  - Customizable title and message formats
  - Optional statistics inclusion
  - Optional remediation steps
  - Emoji indicators for visual clarity

- **Integration**: Seamlessly integrates with:
  - Base `NotificationService` for delivery
  - `StatusReporter` for operation tracking
  - `BackupErrorReporter` for error details

**Key Classes**:
- `BackupNotificationService`: Main notification service
- `BackupEventType`: Enum for backup events
- `NotificationFilter`: Configuration for filtering
- `BackupNotificationTemplate`: Template structure

### 3. Backup Orchestrator Integration

Updated `BackupOrchestrator` to integrate notification and error reporting:

- **Lifecycle Notifications**: Sends notifications at key points:
  - Backup started
  - Backup completed (with statistics)
  - Backup failed (with error details and remediation)

- **Error Handling**: Enhanced error handling with:
  - Automatic error classification
  - Remediation step generation
  - Detailed error context
  - Error notification with guidance

- **Statistics Tracking**: Includes comprehensive statistics in notifications:
  - Files processed
  - Bytes transferred
  - Duration
  - Snapshot ID
  - Progress percentage

### 4. Example and Documentation

Created comprehensive demonstration (`examples/backup_notification_demo.py`):
- Error classification examples
- Warning creation with suggestions
- Notification filtering configuration
- Backup lifecycle notifications
- Error notifications with remediation
- Template showcase

## Requirements Addressed

### Requirement 5.4: Notification for Backup Events
✅ Implemented comprehensive notification system for all backup events including success, failure, and warning conditions.

### Requirement 5.5: Detailed Error Messages and Remediation
✅ Provided detailed error messages with suggested remediation steps for all error categories.

### Requirement 6.4: Configurable Error Handling Policies
✅ Implemented notification filtering based on operation duration, significance, and error severity.

### Requirement 6.5: Error Preservation and Recovery
✅ Error details are preserved in backup results metadata and can be used for manual retry or recovery.

## Technical Details

### Error Classification Algorithm

The error reporter uses pattern matching to classify errors:

```python
# Network errors
['connection', 'timeout', 'network', 'unreachable', 'dns']

# Permission errors
['permission', 'denied', 'access', 'forbidden', 'unauthorized']

# Resource errors
['disk space', 'memory', 'quota', 'no space', 'out of memory']

# Configuration errors
['config', 'invalid', 'not found', 'missing', 'credential']

# Data integrity errors
['corrupt', 'checksum', 'integrity', 'verification failed']

# Transient errors
['temporary', 'retry', 'busy', 'locked']
```

### Notification Filtering Logic

Notifications are filtered based on multiple criteria:

1. **Event Type Filter**: Check if event type is excluded
2. **Severity Filter**: Check if error/warning meets minimum severity
3. **Duration Filter**: For completion events, check minimum duration
4. **Interval Filter**: For progress events, check time since last notification
5. **Configuration Filter**: Check notify_on_warnings, notify_on_errors, notify_on_success flags

### Remediation Step Structure

Each remediation step includes:
- **Description**: Human-readable instruction
- **Command**: Optional command to execute
- **Documentation URL**: Optional link to docs
- **Automated**: Flag indicating if step can be automated

## Usage Examples

### Basic Error Reporting

```python
from TimeLocker.services.backup_error_reporter import BackupErrorReporter

error_reporter = BackupErrorReporter()

# Classify an error
error = error_reporter.classify_error(
    Exception("Connection timeout"),
    context={
        'operation_id': 'backup-001',
        'repository_id': 'prod-repo',
        'tool_name': 'restic'
    }
)

# Access error details
print(f"Category: {error.category.value}")
print(f"Severity: {error.severity.value}")

# Get remediation steps
for step in error.remediation_steps:
    print(f"- {step.description}")
    if step.command:
        print(f"  Command: {step.command}")
```

### Notification Configuration

```python
from TimeLocker.services.backup_notification_service import BackupNotificationService

# Configure filtering
backup_notification_service.update_filter(
    min_duration_seconds=60,  # Only notify for operations > 1 minute
    notify_on_progress=True,
    progress_interval_seconds=300,  # Progress updates every 5 minutes
    notify_on_warnings=True,
    notify_on_errors=True,
    notify_on_success=True,
    min_severity=ErrorSeverity.LOW
)
```

### Sending Notifications

```python
# Backup completed notification
backup_notification_service.notify_backup_event(
    event_type=BackupEventType.BACKUP_COMPLETED,
    operation_id="backup-001",
    repository_id="prod-repo",
    statistics={
        'files_processed': 500,
        'bytes_processed': 1024 * 1024 * 350,
        'duration': timedelta(seconds=120)
    }
)

# Error notification with remediation
backup_notification_service.notify_backup_error(
    operation_id="backup-002",
    error=classified_error,
    repository_id="prod-repo"
)
```

## Testing

Run the demonstration to see the system in action:

```bash
python examples/backup_notification_demo.py
```

The demo showcases:
1. Error classification for different error types
2. Warning creation with suggestions
3. Notification filtering configuration
4. Backup lifecycle notifications
5. Error notifications with remediation steps
6. Available notification templates

## Integration Points

### With Existing Systems

- **NotificationService**: Base notification delivery (desktop, email, log)
- **StatusReporter**: Operation status tracking and history
- **BackupOrchestrator**: Backup execution and coordination
- **JobExecutor**: Retry logic and error handling

### Future Enhancements

1. **Machine Learning**: Learn from error patterns to improve classification
2. **Automated Remediation**: Execute automated remediation steps
3. **Notification Channels**: Add Slack, Teams, webhook integrations
4. **Error Analytics**: Track error trends and patterns
5. **Custom Templates**: User-defined notification templates

## Benefits

1. **Improved User Experience**: Clear, actionable error messages
2. **Faster Problem Resolution**: Remediation guidance reduces troubleshooting time
3. **Reduced Notification Fatigue**: Intelligent filtering prevents spam
4. **Better Monitoring**: Comprehensive event tracking and reporting
5. **Consistent Interface**: Standardized notification format across all backup events

## Notes

- Notification filtering is configurable per installation
- Error classification patterns can be extended for custom error types
- Remediation steps are context-aware and tool-specific where applicable
- All notifications integrate with existing notification channels (desktop, email)
- Error details are preserved in backup results for audit and analysis

## Related Files

- `src/TimeLocker/services/backup_error_reporter.py`
- `src/TimeLocker/services/backup_notification_service.py`
- `src/TimeLocker/services/backup_orchestrator.py`
- `examples/backup_notification_demo.py`
- `.kiro/specs/backup-operations/requirements.md`
- `.kiro/specs/backup-operations/design.md`
