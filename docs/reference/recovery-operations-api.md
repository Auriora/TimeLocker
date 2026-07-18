# Recovery Operations API Reference

**Status**: Active  
**Last Updated**: 2025-11-10  

## Overview

The Recovery Operations API provides comprehensive interfaces for restoring data from backup snapshots with flexible options for full or selective restoration. This document describes the core components, data models, usage patterns, and best practices for the recovery system.

## Table of Contents

- [Core Components](#core-components)
  - [RecoveryOrchestrator](#recoveryorchestrator)
  - [SnapshotBrowser](#snapshotbrowser)
  - [RecoveryValidator](#recoveryvalidator)
  - [ProgressMonitor](#progressmonitor)
- [Data Models](#data-models)
- [Usage Patterns](#usage-patterns)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Core Components

### RecoveryOrchestrator

The central component that coordinates all recovery operations including full and selective restoration.

#### Class Definition

```python
class RecoveryOrchestrator:
    """
    Orchestrates recovery operations across different backup tools.
    
    This class serves as the main entry point for recovery operations,
    coordinating operation validation, execution, state management, and
    integration with other TimeLocker services.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        validator: Optional[RecoveryValidator] = None,
        progress_monitor: Optional[ProgressMonitor] = None
    ):
        """
        Initialize the recovery orchestrator.
        
        Args:
            repository: Repository containing backup snapshots
            validator: Optional validator for recovery operations
            progress_monitor: Optional monitor for tracking progress
        """
```

#### Methods

##### initiate_full_recovery

```python
def initiate_full_recovery(
    self,
    snapshot_id: str,
    target_path: str,
    options: RecoveryOptions
) -> RecoveryOperation:
    """
    Initiate a full snapshot restoration.
    
    Restores all files from a snapshot to the specified target location
    with comprehensive validation and progress monitoring.
    
    Args:
        snapshot_id: ID of the snapshot to restore
        target_path: Destination path for restored files
        options: Configuration options for the recovery operation
        
    Returns:
        RecoveryOperation object tracking the operation
        
    Raises:
        SnapshotNotFoundError: If snapshot does not exist
        ValidationError: If pre-recovery validation fails
        PermissionError: If target path is not writable
        
    Example:
        >>> orchestrator = RecoveryOrchestrator(repository)
        >>> options = RecoveryOptions(
        ...     verify_integrity=True,
        ...     preserve_permissions=True
        ... )
        >>> operation = orchestrator.initiate_full_recovery(
        ...     snapshot_id="abc123",
        ...     target_path="/restore/backup",
        ...     options=options
        ... )
        >>> print(f"Operation ID: {operation.operation_id}")
    """
```

##### initiate_selective_recovery

```python
def initiate_selective_recovery(
    self,
    snapshot_id: str,
    selection_criteria: SelectionCriteria,
    target_path: str,
    options: RecoveryOptions
) -> RecoveryOperation:
    """
    Initiate a selective file restoration.
    
    Restores only files matching the selection criteria from a snapshot
    to the specified target location.
    
    Args:
        snapshot_id: ID of the snapshot to restore from
        selection_criteria: Criteria for selecting files to restore
        target_path: Destination path for restored files
        options: Configuration options for the recovery operation
        
    Returns:
        RecoveryOperation object tracking the operation
        
    Raises:
        SnapshotNotFoundError: If snapshot does not exist
        ValidationError: If selection criteria or validation fails
        PermissionError: If target path is not writable
        
    Example:
        >>> criteria = SelectionCriteria(
        ...     include_patterns=["*.pdf", "*.docx"],
        ...     exclude_patterns=["*/temp/*"]
        ... )
        >>> operation = orchestrator.initiate_selective_recovery(
        ...     snapshot_id="abc123",
        ...     selection_criteria=criteria,
        ...     target_path="/restore/documents",
        ...     options=options
        ... )
    """
```

##### get_recovery_status

```python
def get_recovery_status(
    self,
    operation_id: str
) -> Optional[RecoveryOperation]:
    """
    Retrieve current status of a recovery operation.
    
    Args:
        operation_id: ID of the recovery operation
        
    Returns:
        RecoveryOperation with current status, or None if not found
        
    Example:
        >>> status = orchestrator.get_recovery_status("recovery-001")
        >>> if status:
        ...     print(f"Status: {status.status.value}")
        ...     print(f"Progress: {status.progress.progress_percentage:.1f}%")
    """
```

##### cancel_recovery

```python
def cancel_recovery(
    self,
    operation_id: str
) -> bool:
    """
    Cancel an ongoing recovery operation.
    
    Attempts to gracefully stop a recovery operation, cleaning up
    partial progress and releasing resources.
    
    Args:
        operation_id: ID of the recovery operation to cancel
        
    Returns:
        True if cancellation was successful, False otherwise
        
    Example:
        >>> if orchestrator.cancel_recovery("recovery-001"):
        ...     print("Recovery cancelled successfully")
    """
```

##### list_operations

```python
def list_operations(
    self,
    status_filter: Optional[OperationStatus] = None
) -> List[RecoveryOperation]:
    """
    List all recovery operations, optionally filtered by status.
    
    Args:
        status_filter: Optional status to filter operations
        
    Returns:
        List of RecoveryOperation objects
        
    Example:
        >>> # List all running operations
        >>> running = orchestrator.list_operations(
        ...     status_filter=OperationStatus.RUNNING
        ... )
        >>> for op in running:
        ...     print(f"{op.operation_id}: {op.progress.progress_percentage:.1f}%")
    """
```

### SnapshotBrowser

Component for exploring and navigating snapshot contents before restoration.

#### Class Definition

```python
class SnapshotBrowser:
    """
    Provides browsing and exploration capabilities for snapshot contents.
    
    Supports listing directories, searching for files, comparing snapshots,
    and retrieving detailed file metadata with efficient caching.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        cache_enabled: bool = True
    ):
        """
        Initialize the snapshot browser.
        
        Args:
            repository: Repository containing snapshots
            cache_enabled: Whether to enable caching for performance
        """
```

#### Methods

##### list_snapshot_contents

```python
def list_snapshot_contents(
    self,
    snapshot_id: str,
    path: str = "/",
    pagination: Optional[PaginationOptions] = None
) -> SnapshotListing:
    """
    List files and directories in a snapshot path.
    
    Args:
        snapshot_id: ID of the snapshot to browse
        path: Path within the snapshot to list (default: root)
        pagination: Optional pagination for large directories
        
    Returns:
        SnapshotListing containing entries and pagination info
        
    Example:
        >>> browser = SnapshotBrowser(repository)
        >>> listing = browser.list_snapshot_contents(
        ...     snapshot_id="abc123",
        ...     path="/home/user/documents"
        ... )
        >>> for entry in listing.entries:
        ...     print(f"{entry.name}: {entry.size} bytes")
    """
```

##### search_snapshot_files

```python
def search_snapshot_files(
    self,
    snapshot_id: str,
    search_criteria: SearchCriteria
) -> List[FileEntry]:
    """
    Search for files within a snapshot using patterns and filters.
    
    Args:
        snapshot_id: ID of the snapshot to search
        search_criteria: Criteria for searching files
        
    Returns:
        List of FileEntry objects matching the criteria
        
    Example:
        >>> criteria = SearchCriteria(
        ...     name_pattern="*.pdf",
        ...     size_range=SizeRange(min_size=1024, max_size=10485760),
        ...     date_range=DateRange(start_date=datetime.now() - timedelta(days=30))
        ... )
        >>> results = browser.search_snapshot_files("abc123", criteria)
        >>> print(f"Found {len(results)} matching files")
    """
```

##### compare_snapshots

```python
def compare_snapshots(
    self,
    snapshot_ids: List[str],
    path: str = "/"
) -> SnapshotComparison:
    """
    Compare file versions across multiple snapshots.
    
    Args:
        snapshot_ids: List of snapshot IDs to compare
        path: Path within snapshots to compare (default: root)
        
    Returns:
        SnapshotComparison showing differences between snapshots
        
    Example:
        >>> comparison = browser.compare_snapshots(
        ...     snapshot_ids=["snap1", "snap2"],
        ...     path="/home/user"
        ... )
        >>> print(f"Added: {len(comparison.added_files)}")
        >>> print(f"Removed: {len(comparison.removed_files)}")
        >>> print(f"Modified: {len(comparison.modified_files)}")
    """
```

##### get_file_metadata

```python
def get_file_metadata(
    self,
    snapshot_id: str,
    file_path: str
) -> FileMetadata:
    """
    Retrieve detailed metadata for a specific file.
    
    Args:
        snapshot_id: ID of the snapshot
        file_path: Path to the file within the snapshot
        
    Returns:
        FileMetadata with detailed file information
        
    Example:
        >>> metadata = browser.get_file_metadata(
        ...     snapshot_id="abc123",
        ...     file_path="/home/user/document.pdf"
        ... )
        >>> print(f"Size: {metadata.file_entry.size}")
        >>> print(f"Modified: {metadata.file_entry.modification_time}")
        >>> print(f"Checksum: {metadata.file_entry.checksum}")
    """
```

### RecoveryValidator

Component for validating recovery operations and ensuring data integrity.

#### Class Definition

```python
class RecoveryValidator:
    """
    Validates recovery operations and ensures data integrity.
    
    Provides pre-recovery validation, real-time validation during recovery,
    and comprehensive post-recovery verification with checksum validation.
    """
    
    def __init__(
        self,
        repository: BackupRepository
    ):
        """
        Initialize the recovery validator.
        
        Args:
            repository: Repository for validation operations
        """
```

#### Methods

##### validate_pre_recovery

```python
def validate_pre_recovery(
    self,
    snapshot_id: str,
    target_path: str,
    selection_criteria: Optional[SelectionCriteria] = None
) -> ValidationResult:
    """
    Validate conditions before starting recovery.
    
    Checks snapshot existence, target path accessibility, space availability,
    and selection criteria validity.
    
    Args:
        snapshot_id: ID of the snapshot to validate
        target_path: Target path for restoration
        selection_criteria: Optional selection criteria to validate
        
    Returns:
        ValidationResult indicating validation status
        
    Example:
        >>> validator = RecoveryValidator(repository)
        >>> result = validator.validate_pre_recovery(
        ...     snapshot_id="abc123",
        ...     target_path="/restore/backup"
        ... )
        >>> if not result.is_valid:
        ...     for failure in result.failed_validations:
        ...         print(f"Error: {failure.error_message}")
    """
```

##### validate_during_recovery

```python
def validate_during_recovery(
    self,
    operation_id: str
) -> ValidationResult:
    """
    Perform real-time validation during recovery.
    
    Validates files as they are restored, checking for corruption
    and integrity issues.
    
    Args:
        operation_id: ID of the recovery operation
        
    Returns:
        ValidationResult with current validation status
        
    Example:
        >>> result = validator.validate_during_recovery("recovery-001")
        >>> if result.warnings:
        ...     print(f"Warnings: {len(result.warnings)}")
    """
```

##### validate_post_recovery

```python
def validate_post_recovery(
    self,
    operation_id: str
) -> ValidationReport:
    """
    Comprehensive validation after recovery completion.
    
    Performs thorough validation of all restored files including
    checksum verification, permission checks, and completeness validation.
    
    Args:
        operation_id: ID of the completed recovery operation
        
    Returns:
        ValidationReport with detailed validation results
        
    Example:
        >>> report = validator.validate_post_recovery("recovery-001")
        >>> print(f"Files validated: {report.validated_files}")
        >>> print(f"Status: {'PASSED' if report.is_valid else 'FAILED'}")
        >>> if report.failed_validations:
        ...     print(f"Failures: {len(report.failed_validations)}")
    """
```

##### verify_file_integrity

```python
def verify_file_integrity(
    self,
    restored_file_path: str,
    expected_checksum: str
) -> bool:
    """
    Verify individual file integrity using checksums.
    
    Args:
        restored_file_path: Path to the restored file
        expected_checksum: Expected checksum from snapshot metadata
        
    Returns:
        True if file integrity is verified, False otherwise
        
    Example:
        >>> is_valid = validator.verify_file_integrity(
        ...     restored_file_path="/restore/file.txt",
        ...     expected_checksum="sha256:abc123..."
        ... )
        >>> if not is_valid:
        ...     print("File integrity check failed")
    """
```

### ProgressMonitor

Component for tracking and reporting recovery operation progress.

#### Class Definition

```python
class ProgressMonitor:
    """
    Monitors and reports progress for recovery operations.
    
    Provides real-time progress updates, completion estimates,
    and callback registration for progress notifications.
    """
    
    def __init__(self):
        """Initialize the progress monitor."""
```

#### Methods

##### start_monitoring

```python
def start_monitoring(
    self,
    operation_id: str
) -> None:
    """
    Begin monitoring a recovery operation.
    
    Args:
        operation_id: ID of the operation to monitor
        
    Example:
        >>> monitor = ProgressMonitor()
        >>> monitor.start_monitoring("recovery-001")
    """
```

##### get_progress_status

```python
def get_progress_status(
    self,
    operation_id: str
) -> Optional[ProgressStatus]:
    """
    Retrieve current progress information.
    
    Args:
        operation_id: ID of the operation
        
    Returns:
        ProgressStatus with current progress, or None if not found
        
    Example:
        >>> status = monitor.get_progress_status("recovery-001")
        >>> if status:
        ...     pct = status.progress_percentage
        ...     print(f"Progress: {pct:.1f}%")
        ...     print(f"Transfer rate: {status.transfer_rate / (1024*1024):.2f} MB/s")
    """
```

##### estimate_completion_time

```python
def estimate_completion_time(
    self,
    operation_id: str
) -> Optional[datetime]:
    """
    Estimate recovery completion time based on current progress.
    
    Args:
        operation_id: ID of the operation
        
    Returns:
        Estimated completion datetime, or None if cannot estimate
        
    Example:
        >>> completion = monitor.estimate_completion_time("recovery-001")
        >>> if completion:
        ...     remaining = completion - datetime.now()
        ...     print(f"Estimated time remaining: {remaining}")
    """
```

##### register_progress_callback

```python
def register_progress_callback(
    self,
    operation_id: str,
    callback: Callable[[ProgressStatus], None]
) -> None:
    """
    Register callback for progress updates.
    
    Args:
        operation_id: ID of the operation
        callback: Function to call with progress updates
        
    Example:
        >>> def progress_callback(status: ProgressStatus):
        ...     print(f"Progress: {status.progress_percentage:.1f}%")
        >>> 
        >>> monitor.register_progress_callback("recovery-001", progress_callback)
    """
```

## Data Models

### RecoveryOperation

Represents an active or completed recovery operation.

```python
@dataclass
class RecoveryOperation:
    """Recovery operation tracking."""
    operation_id: str
    snapshot_id: str
    recovery_type: RecoveryType  # FULL or SELECTIVE
    target_path: str
    status: OperationStatus
    start_time: datetime
    completion_time: Optional[datetime] = None
    progress: Optional[ProgressStatus] = None
    validation_result: Optional[ValidationResult] = None
    error_details: Optional[ErrorDetails] = None
    
    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.completion_time:
            return (self.completion_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.status in [
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED
        ]
```

### SelectionCriteria

Defines criteria for selective recovery operations.

```python
@dataclass
class SelectionCriteria:
    """Criteria for selective file recovery."""
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    file_types: List[FileType] = field(default_factory=list)
    size_range: Optional[SizeRange] = None
    date_range: Optional[DateRange] = None
    selection_template_id: Optional[str] = None
```

### RecoveryOptions

Configuration options for recovery operations.

```python
@dataclass
class RecoveryOptions:
    """Configuration options for recovery operations."""
    overwrite_existing: bool = False
    preserve_permissions: bool = True
    preserve_timestamps: bool = True
    verify_integrity: bool = True
    continue_on_error: bool = True
    max_retries: int = 3
    notification_preferences: NotificationPreferences = field(
        default_factory=NotificationPreferences
    )
    conflict_resolution: ConflictResolution = ConflictResolution.RENAME
```

For complete data model reference, see [Recovery Operations Models Reference](recovery-operations-models-reference.md).

## Usage Patterns

### Basic Full Recovery

```python
from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.interfaces.recovery_models import RecoveryOptions
from TimeLocker.backup_repository import BackupRepository

# Initialize components
repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
orchestrator = RecoveryOrchestrator(repository)

# Configure recovery options
options = RecoveryOptions(
    verify_integrity=True,
    preserve_permissions=True,
    max_retries=3
)

# Initiate full recovery
operation = orchestrator.initiate_full_recovery(
    snapshot_id="abc123",
    target_path="/restore/backup",
    options=options
)

# Monitor progress
while not operation.is_complete:
    status = orchestrator.get_recovery_status(operation.operation_id)
    if status and status.progress:
        print(f"Progress: {status.progress.progress_percentage:.1f}%")
    time.sleep(1)

print(f"Recovery {status.status.value}")
```

### Selective Recovery with Patterns

```python
from TimeLocker.interfaces.recovery_models import SelectionCriteria

# Define selection criteria
criteria = SelectionCriteria(
    include_patterns=["*.pdf", "*.docx", "**/*.xlsx"],
    exclude_patterns=["*/temp/*", "*/.cache/*", "*.tmp"]
)

# Initiate selective recovery
operation = orchestrator.initiate_selective_recovery(
    snapshot_id="abc123",
    selection_criteria=criteria,
    target_path="/restore/documents",
    options=options
)
```

### Browsing Snapshots Before Recovery

```python
from TimeLocker.snapshot_browser import SnapshotBrowser, SearchCriteria
from TimeLocker.interfaces.recovery_models import SizeRange, DateRange
from datetime import datetime, timedelta

# Initialize browser
browser = SnapshotBrowser(repository)

# List snapshot contents
listing = browser.list_snapshot_contents(
    snapshot_id="abc123",
    path="/home/user/documents"
)

print(f"Found {listing.total_entries} entries")
for entry in listing.entries:
    print(f"{entry.name}: {entry.size:,} bytes")

# Search for specific files
criteria = SearchCriteria(
    name_pattern="*.pdf",
    size_range=SizeRange(min_size=1024, max_size=10485760),
    date_range=DateRange(start_date=datetime.now() - timedelta(days=30))
)

results = browser.search_snapshot_files("abc123", criteria)
print(f"Found {len(results)} matching files")
```

### Recovery with Validation

```python
from TimeLocker.recovery_validator import RecoveryValidator

# Initialize validator
validator = RecoveryValidator(repository)

# Pre-recovery validation
pre_result = validator.validate_pre_recovery(
    snapshot_id="abc123",
    target_path="/restore/backup"
)

if not pre_result.is_valid:
    print("Pre-recovery validation failed:")
    for failure in pre_result.failed_validations:
        print(f"  - {failure.error_message}")
    exit(1)

# Perform recovery
operation = orchestrator.initiate_full_recovery(
    snapshot_id="abc123",
    target_path="/restore/backup",
    options=options
)

# Wait for completion
while not operation.is_complete:
    time.sleep(1)

# Post-recovery validation
post_result = validator.validate_post_recovery(operation.operation_id)

print(f"Validation: {'PASSED' if post_result.is_valid else 'FAILED'}")
print(f"Files validated: {post_result.validated_files}")

if post_result.failed_validations:
    print(f"Failed validations: {len(post_result.failed_validations)}")
    for failure in post_result.failed_validations[:5]:
        print(f"  - {failure.file_path}: {failure.error_message}")
```

### Progress Monitoring with Callbacks

```python
from TimeLocker.interfaces.recovery_models import ProgressStatus

def progress_callback(status: ProgressStatus):
    """Custom progress callback"""
    pct = status.progress_percentage
    rate_mb = status.transfer_rate / (1024 * 1024)
    
    print(f"Progress: {pct:.1f}% - "
          f"{status.files_processed}/{status.total_files} files - "
          f"{rate_mb:.2f} MB/s")
    
    if status.estimated_completion:
        remaining = status.estimated_completion - datetime.now()
        print(f"Estimated time remaining: {remaining}")

# Register callback
monitor = ProgressMonitor()
monitor.register_progress_callback(operation.operation_id, progress_callback)
```

## Best Practices

### Pre-Recovery Validation

Always validate before starting recovery operations:

```python
# Validate snapshot exists and is accessible
validator = RecoveryValidator(repository)
result = validator.validate_pre_recovery(snapshot_id, target_path)

if not result.is_valid:
    # Handle validation failures
    for failure in result.failed_validations:
        logger.error(f"Validation failed: {failure.error_message}")
    return

# Check warnings
if result.warnings:
    for warning in result.warnings:
        logger.warning(f"Validation warning: {warning.message}")
```

### Error Handling

Implement comprehensive error handling:

```python
from TimeLocker.recovery_errors import (
    SnapshotNotFoundError,
    ValidationError,
    RestoreError
)

try:
    operation = orchestrator.initiate_full_recovery(
        snapshot_id=snapshot_id,
        target_path=target_path,
        options=options
    )
except SnapshotNotFoundError as e:
    logger.error(f"Snapshot not found: {e}")
    # Handle missing snapshot
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    # Handle validation failure
except PermissionError as e:
    logger.error(f"Permission denied: {e}")
    # Handle permission issues
except RestoreError as e:
    logger.error(f"Restore failed: {e}")
    # Handle restore failure
```

### Resource Management

Properly manage resources during recovery:

```python
import shutil

# Check available space before recovery
target_parent = Path(target_path).parent
stat = shutil.disk_usage(target_parent)
available_gb = stat.free / (1024**3)

if available_gb < required_space_gb:
    raise ValueError(f"Insufficient space: {available_gb:.2f} GB available, "
                    f"{required_space_gb:.2f} GB required")

# Monitor disk space during recovery
def check_space_callback(status: ProgressStatus):
    stat = shutil.disk_usage(target_parent)
    if stat.free < 1024**3:  # Less than 1 GB
        logger.warning("Low disk space during recovery")
```

### Performance Optimization

Optimize recovery performance:

```python
# Use pagination for large directories
pagination = PaginationOptions(page=1, page_size=100)
listing = browser.list_snapshot_contents(
    snapshot_id=snapshot_id,
    path=path,
    pagination=pagination
)

# Enable caching for repeated browsing
browser = SnapshotBrowser(repository, cache_enabled=True)

# Use selective recovery for specific files
criteria = SelectionCriteria(
    include_patterns=["specific/path/**"],
    file_types=[FileType.FILE]
)
```

### Verification Best Practices

Ensure data integrity:

```python
# Enable integrity verification
options = RecoveryOptions(
    verify_integrity=True,
    continue_on_error=True  # Continue even if some files fail
)

# Perform post-recovery validation
post_result = validator.validate_post_recovery(operation.operation_id)

# Log validation results
if post_result.failed_validations:
    for failure in post_result.failed_validations:
        logger.error(f"Integrity check failed: {failure.file_path}")
        logger.error(f"  Expected: {failure.expected_checksum}")
        logger.error(f"  Actual: {failure.actual_checksum}")
        
        # Optionally retry failed files
        if failure.failure_type == FailureType.CHECKSUM_MISMATCH:
            # Retry restoration for this file
            pass
```

## Troubleshooting

### Common Issues

#### Snapshot Not Found

**Problem**: `SnapshotNotFoundError` when initiating recovery

**Solution**:
```python
# Verify snapshot exists
snapshots = repository.snapshots()
snapshot_ids = [s.id for s in snapshots]

if snapshot_id not in snapshot_ids:
    print(f"Snapshot {snapshot_id} not found")
    print(f"Available snapshots: {snapshot_ids}")
```

#### Permission Denied

**Problem**: `PermissionError` when writing to target path

**Solution**:
```python
# Check target path permissions
target = Path(target_path)
if not target.parent.exists():
    target.parent.mkdir(parents=True, exist_ok=True)

# Verify write permissions
if not os.access(target.parent, os.W_OK):
    print(f"No write permission for {target.parent}")
```

#### Validation Failures

**Problem**: Pre-recovery validation fails

**Solution**:
```python
result = validator.validate_pre_recovery(snapshot_id, target_path)

if not result.is_valid:
    for failure in result.failed_validations:
        if failure.failure_type == FailureType.FILE_MISSING:
            print(f"Snapshot incomplete: {failure.file_path}")
        elif failure.failure_type == FailureType.PERMISSION_ERROR:
            print(f"Permission issue: {failure.file_path}")
```

#### Slow Recovery Performance

**Problem**: Recovery operation is slower than expected

**Solutions**:
```python
# 1. Use selective recovery instead of full recovery
criteria = SelectionCriteria(
    include_patterns=["specific/files/**"]
)

# 2. Enable caching for browsing
browser = SnapshotBrowser(repository, cache_enabled=True)

# 3. Monitor transfer rate
status = orchestrator.get_recovery_status(operation_id)
if status.progress.transfer_rate < expected_rate:
    print("Transfer rate below expected")
    # Check network, disk I/O, etc.
```

### Debugging

Enable detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable recovery operation logging
logger = logging.getLogger('TimeLocker.recovery_orchestrator')
logger.setLevel(logging.DEBUG)
```

## See Also

- [Recovery Operations Models Reference](recovery-operations-models-reference.md)
- [Full Recovery Workflow Demo](../../examples/full_recovery_workflow_demo.py)
- [Selective Recovery Demo](../../examples/selective_recovery_demo.py)
- [Recovery Verification and Monitoring Demo](../../examples/recovery_verification_monitoring_demo.py)
- [User Guide: Recovery Operations](../guides/user/recovery-operations-guide.md)
