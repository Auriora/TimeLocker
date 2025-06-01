# TimeLocker Recovery Operations Implementation

## Overview

This document describes the implementation of Phase 3 recovery operations for TimeLocker, focusing on snapshot management and restore functionality as specified
in requirements FR-RC-001 (Full restore operations) and FR-RC-002 (Simple snapshot selection).

## Architecture

The recovery operations are implemented using three main components:

### 1. SnapshotManager (`src/TimeLocker/snapshot_manager.py`)

Manages snapshot listing, filtering, and selection operations.

**Key Features:**

- **Snapshot Listing**: Retrieve all available snapshots from repository
- **Advanced Filtering**: Filter by tags, date ranges, paths, and result limits
- **Snapshot Selection**: Get snapshots by ID (exact or partial match)
- **Caching**: Intelligent caching with TTL to improve performance
- **Latest Snapshot**: Quick access to most recent snapshot

**Core Classes:**

- `SnapshotFilter`: Fluent API for building filter criteria
- `SnapshotManager`: Main management class with caching and filtering

### 2. RestoreManager (`src/TimeLocker/restore_manager.py`)

Handles restore operations with comprehensive error handling and verification.

**Key Features:**

- **Full Restore Operations**: Complete snapshot restoration with verification
- **Flexible Options**: Configurable restore behavior via `RestoreOptions`
- **Conflict Resolution**: Handle file conflicts (skip, overwrite, keep both)
- **Pre-restore Validation**: Space checks, permission validation, conflict detection
- **Progress Tracking**: Optional progress callbacks for UI integration
- **Dry Run Mode**: Test restore operations without actual file operations

**Core Classes:**

- `RestoreOptions`: Fluent configuration API for restore operations
- `RestoreResult`: Comprehensive result reporting with statistics and errors
- `ConflictResolution`: Enum for file conflict handling strategies
- `RestoreManager`: Main restore orchestration class

### 3. Recovery Errors (`src/TimeLocker/recovery_errors.py`)

Custom exception hierarchy for recovery operations.

**Exception Types:**

- `RecoveryError`: Base exception for all recovery operations
- `SnapshotNotFoundError`: Snapshot ID not found
- `RestoreError`: Base for restore-specific errors
- `RestoreTargetError`: Issues with restore destination
- `RestorePermissionError`: Permission-related failures
- `RestoreVerificationError`: Post-restore verification failures
- `FileConflictError`: File conflicts during restore
- `InsufficientSpaceError`: Disk space issues

## Implementation Details

### Snapshot Management

```python
# Basic snapshot listing
manager = SnapshotManager(repository)
snapshots = manager.list_snapshots()

# Advanced filtering
filter_criteria = (SnapshotFilter()
                  .with_tags(["full"])
                  .with_date_range(datetime.now() - timedelta(days=30))
                  .with_max_results(10))
filtered_snapshots = manager.list_snapshots(filter_criteria)

# Get specific snapshot
snapshot = manager.get_snapshot_by_id("abc123")
latest = manager.get_latest_snapshot()
```

### Restore Operations

```python
# Basic restore
restore_manager = RestoreManager(repository)
options = RestoreOptions().with_target_path("/restore/path")
result = restore_manager.restore_snapshot("abc123", options)

# Advanced restore with options
options = (RestoreOptions()
          .with_target_path("/restore/path")
          .with_verification(True)
          .with_conflict_resolution(ConflictResolution.OVERWRITE)
          .with_include_paths(["/important/files"])
          .with_progress_callback(progress_handler))

result = restore_manager.restore_snapshot("abc123", options)
```

### Error Handling

The implementation provides comprehensive error handling:

1. **Pre-restore Validation**: Checks target path, available space, permissions
2. **Operation Errors**: Handles repository failures, network issues
3. **Post-restore Verification**: Validates restored files
4. **Graceful Degradation**: Continues operation when possible, reports issues

## Testing

### Test Coverage

- **37 unit tests** covering all major functionality
- **Mock repository** for isolated testing
- **Edge case testing** for error scenarios
- **Integration testing** with temporary file systems

### Test Structure

```
tests/TimeLocker/recovery/
├── __init__.py
├── mock_recovery_repository.py     # Mock implementation for testing
├── test_snapshot_manager.py        # SnapshotManager tests (18 tests)
└── test_restore_manager.py         # RestoreManager tests (19 tests)
```

### Running Tests

```bash
# Run all recovery tests
PYTHONPATH=src python3 -m pytest tests/TimeLocker/recovery/ -v

# Run specific test files
PYTHONPATH=src python3 -m pytest tests/TimeLocker/recovery/test_snapshot_manager.py -v
PYTHONPATH=src python3 -m pytest tests/TimeLocker/recovery/test_restore_manager.py -v
```

## Demo and Examples

### Recovery Operations Demo

A comprehensive demo script showcases all functionality:

```bash
PYTHONPATH=src python3 examples/recovery_operations_demo.py
```

**Demo Features:**

- Snapshot listing and filtering examples
- Various restore operation scenarios
- Error handling demonstrations
- Advanced features like caching and progress tracking

## Integration with Existing Codebase

The recovery operations integrate seamlessly with existing TimeLocker components:

1. **BackupRepository**: Uses existing repository abstraction
2. **BackupSnapshot**: Extends existing snapshot functionality
3. **Error Patterns**: Follows established error handling conventions
4. **Logging**: Uses existing logging infrastructure
5. **Command Builder**: Compatible with restic command patterns

## Key Benefits

1. **Comprehensive**: Covers all major recovery scenarios
2. **Robust**: Extensive error handling and validation
3. **Flexible**: Configurable options for different use cases
4. **Testable**: High test coverage with mock implementations
5. **Extensible**: Clean architecture for future enhancements
6. **User-Friendly**: Clear error messages and progress tracking

## Future Enhancements

Potential areas for future development:

1. **Partial File Restore**: Restore specific files from snapshots
2. **Incremental Restore**: Restore only changed files
3. **Restore Scheduling**: Automated restore operations
4. **GUI Integration**: Progress bars and user interaction
5. **Restore Profiles**: Saved restore configurations
6. **Performance Optimization**: Parallel restore operations

## Requirements Fulfillment

### FR-RC-001: Full Restore Operations ✅

- Complete snapshot restoration functionality
- Verification of restored files
- Comprehensive error handling
- Progress tracking and reporting

### FR-RC-002: Simple Snapshot Selection ✅

- List all available snapshots
- Filter by various criteria (tags, dates, paths)
- Select snapshots by ID (exact and partial matching)
- Get latest snapshot functionality

The implementation successfully fulfills both requirements with additional features for robustness and usability.
