# Platform Adapters Implementation

**Date**: 2025-11-11  
**Status**: Complete  
**Related Spec**: `.kiro/specs/scheduling-automation/`  
**Task**: 3. Create platform-specific scheduler adapters

## Overview

Implemented comprehensive platform-specific scheduler adapters for the TimeLocker Scheduling & Automation system. This implementation provides native integration with operating system schedulers across Linux, Unix, Windows, and macOS platforms.

## Implementation Summary

### 3.1 SystemdAdapter for Linux Systems

**File**: `src/TimeLocker/scheduling/systemd_adapter.py`

Implemented full systemd timer integration with the following features:

- **Service and Timer Unit Generation**: Creates systemd service and timer unit files with proper configuration
- **systemctl Command Integration**: Manages user services via systemctl (daemon-reload, enable, start, stop, disable)
- **Status Monitoring**: Retrieves timer status, next run times, and last run times from systemd
- **Error Reporting**: Comprehensive error handling with detailed logging through journald
- **Schedule Pattern Support**: Converts CRON, INTERVAL, and CALENDAR patterns to systemd OnCalendar format
- **Validation**: Validates schedule configurations for systemd compatibility

Key Methods:
- `create_schedule()`: Creates systemd service and timer units
- `update_schedule()`: Updates existing timers by recreating them
- `delete_schedule()`: Stops, disables, and removes timer units
- `get_schedule_status()`: Retrieves current timer status and run times
- `list_schedules()`: Lists all TimeLocker systemd timers
- `validate_schedule_config()`: Validates configuration for systemd

### 3.2 CronAdapter for Unix-like Systems

**File**: `src/TimeLocker/scheduling/cron_adapter.py`

Implemented full cron integration with the following features:

- **Cron Job Management**: Creates and manages cron jobs via crontab manipulation
- **Cron Expression Validation**: Validates cron expressions and converts from other pattern types
- **Next-Run Calculation**: Calculates next execution time from cron expressions
- **Wrapper Script Generation**: Creates bash wrapper scripts with timeout and logging
- **Error Handling**: Comprehensive error handling with log file tracking
- **Schedule Pattern Support**: Converts INTERVAL and CALENDAR patterns to cron expressions

Key Methods:
- `create_schedule()`: Creates cron job and wrapper script
- `update_schedule()`: Updates cron job by removing and recreating
- `delete_schedule()`: Removes cron job and wrapper script
- `get_schedule_status()`: Retrieves cron job status and calculates next run
- `list_schedules()`: Lists all TimeLocker cron jobs
- `validate_schedule_config()`: Validates configuration for cron compatibility

### 3.3 WindowsTaskSchedulerAdapter for Windows

**File**: `src/TimeLocker/scheduling/windows_adapter.py`

Implemented full Windows Task Scheduler integration with the following features:

- **Task XML Generation**: Creates Windows Task Scheduler XML with complex scheduling
- **schtasks Command Integration**: Manages tasks via schtasks command
- **PowerShell Script Creation**: Generates PowerShell wrapper scripts with timeout and error handling
- **Status Reporting**: Retrieves task status, next run times, and last run times
- **Error Handling**: Windows-specific error handling and logging
- **Schedule Pattern Support**: Converts CRON, INTERVAL, and CALENDAR patterns to Windows triggers

Key Methods:
- `create_schedule()`: Creates Windows scheduled task from XML
- `update_schedule()`: Updates task by deleting and recreating
- `delete_schedule()`: Removes scheduled task and PowerShell script
- `get_schedule_status()`: Retrieves task status and run times
- `list_schedules()`: Lists all TimeLocker scheduled tasks
- `validate_schedule_config()`: Validates configuration for Windows Task Scheduler

### 3.4 LaunchdAdapter for macOS

**File**: `src/TimeLocker/scheduling/launchd_adapter.py`

Implemented full launchd integration with the following features:

- **Plist Generation**: Creates launchd plist files with proper scheduling configuration
- **launchctl Command Integration**: Manages jobs via launchctl (load, unload, list)
- **Wrapper Script Generation**: Creates bash wrapper scripts with timeout and logging
- **Status Monitoring**: Retrieves job status and calculates next run times
- **Error Handling**: macOS-specific error handling and logging
- **Schedule Pattern Support**: Converts CRON, INTERVAL, and CALENDAR patterns to launchd format

Key Methods:
- `create_schedule()`: Creates launchd plist and wrapper script
- `update_schedule()`: Updates job by unloading and recreating
- `delete_schedule()`: Unloads job and removes plist and script
- `get_schedule_status()`: Retrieves job status and run times
- `list_schedules()`: Lists all TimeLocker launchd jobs
- `validate_schedule_config()`: Validates configuration for launchd

## Technical Details

### Common Features Across All Adapters

1. **Async/Await Pattern**: All adapters use async methods for non-blocking I/O operations
2. **Comprehensive Logging**: Detailed logging at debug, info, warning, and error levels
3. **Error Handling**: Proper exception handling with PlatformSchedulerError
4. **Validation**: Configuration validation before schedule creation
5. **Wrapper Scripts**: Platform-specific wrapper scripts for proper execution environment
6. **Status Tracking**: Retrieval of last run time, next run time, and active status
7. **Pattern Conversion**: Conversion between CRON, INTERVAL, and CALENDAR patterns

### Schedule Pattern Conversions

Each adapter implements conversion logic for the three pattern types:

- **CRON**: Direct use or conversion to platform-native format
- **INTERVAL**: Converted to platform-specific interval scheduling
- **CALENDAR**: Converted to platform-specific calendar scheduling

### Wrapper Script Features

All wrapper scripts include:
- Proper shebang and execution permissions
- Logging to platform-appropriate locations
- Timeout handling
- Error code propagation
- Timestamp tracking
- Environment setup

### Platform-Specific Considerations

**SystemdAdapter**:
- Uses user systemd units (~/.config/systemd/user/)
- Integrates with journald for logging
- Supports RandomizedDelaySec for load distribution
- Persistent timers survive reboots

**CronAdapter**:
- Manages user crontab entries
- Uses comment markers for identification
- Logs to ~/.local/share/timelocker/logs/
- Supports standard cron expressions

**WindowsTaskSchedulerAdapter**:
- Creates tasks in \TimeLocker folder
- Uses PowerShell for execution
- Logs to %LOCALAPPDATA%\TimeLocker\Logs\
- Supports complex XML-based scheduling

**LaunchdAdapter**:
- Creates plists in ~/Library/LaunchAgents/
- Uses launchctl for job management
- Logs to ~/Library/Logs/TimeLocker/
- Supports StartInterval and StartCalendarInterval

## Requirements Satisfied

This implementation satisfies the following requirements from the design document:

- **Requirement 1.1**: Platform scheduler detection and automatic selection
- **Requirement 1.4**: Platform-appropriate configuration generation and logging integration

All adapters implement the complete PlatformAdapter interface:
- `create_schedule()`: Create platform-specific scheduled task
- `update_schedule()`: Update existing scheduled task
- `delete_schedule()`: Remove scheduled task
- `get_schedule_status()`: Get current status
- `list_schedules()`: List all scheduled tasks
- `validate_schedule_config()`: Validate configuration
- `get_platform_name()`: Return platform identifier

## Testing Recommendations

1. **Unit Tests**: Test each adapter method with mock subprocess calls
2. **Integration Tests**: Test on actual platforms with real schedulers
3. **Cross-Platform Tests**: Verify behavior across Linux, Windows, and macOS
4. **Error Scenarios**: Test failure conditions and recovery
5. **Pattern Conversion**: Test all schedule pattern type conversions
6. **Status Retrieval**: Test status monitoring and next-run calculations

## Next Steps

With platform adapters complete, the next tasks in the scheduling implementation are:

- Task 4: Develop script generation system (already partially implemented in adapters)
- Task 5: Build automation execution engine
- Task 6: Develop validation and testing capabilities
- Task 7: Create audit and compliance system
- Task 8: Build configuration and management interfaces
- Task 9: Integrate with TimeLocker systems and finalize

## Files Modified

- `src/TimeLocker/scheduling/systemd_adapter.py`: Full implementation
- `src/TimeLocker/scheduling/cron_adapter.py`: Full implementation
- `src/TimeLocker/scheduling/windows_adapter.py`: Full implementation
- `src/TimeLocker/scheduling/launchd_adapter.py`: Full implementation

## Dependencies

All adapters depend on:
- `scheduling_models.py`: Data models for scheduling
- `scheduling_exceptions.py`: Exception classes
- `platform_adapter.py`: Abstract base class
- Standard library: `asyncio`, `subprocess`, `pathlib`, `datetime`, `re`
- Platform-specific: `plistlib` (macOS), `xml.etree.ElementTree` (Windows)

## Notes

- All implementations follow SOLID principles and DRY
- Comprehensive docstrings for all classes and methods
- Type hints for all parameters and return values
- Proper error handling with context
- Platform-specific optimizations where appropriate
- Security considerations for credential handling (to be integrated with script generation system)
