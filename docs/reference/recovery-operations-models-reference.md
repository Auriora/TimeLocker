# Recovery Operations Models Reference

**Module**: `TimeLocker.interfaces.recovery_models`  
**Status**: Implemented  
**Version**: 1.0.0

## Quick Import

```python
from TimeLocker.interfaces import (
    RecoveryOperation,
    SnapshotListing,
    FileEntry,
    SelectionCriteria,
    RecoveryOptions,
    ProgressStatus,
    ValidationResult,
    ValidationFailure,
    RecoveryType,
    OperationStatus,
    FileType
)
```

## Core Models

### RecoveryOperation

Represents an active or completed recovery operation.

```python
operation = RecoveryOperation(
    operation_id="recovery-001",
    snapshot_id="snap-abc123",
    recovery_type=RecoveryType.SELECTIVE,
    target_path="/restore/path",
    status=OperationStatus.RUNNING,
    start_time=datetime.now()
)

# Properties
duration = operation.duration  # seconds
is_complete = operation.is_complete  # bool
is_successful = operation.is_successful  # bool
```

### FileEntry

Represents a file or directory within a snapshot.

```python
file_entry = FileEntry(
    path="/backup/data/file.txt",
    name="file.txt",
    type=FileType.FILE,
    size=1024,
    modification_time=datetime.now(),
    permissions="rw-r--r--",
    checksum="sha256:abc123"
)
```

### SnapshotListing

Represents the contents of a snapshot directory.

```python
listing = SnapshotListing(
    path="/backup/data",
    entries=[file_entry1, file_entry2],
    total_entries=100,
    pagination_info=PaginationInfo(
        current_page=1,
        page_size=50,
        total_pages=2,
        total_entries=100,
        has_next=True,
        has_previous=False
    )
)
```

### SelectionCriteria

Defines criteria for selective recovery operations.

```python
criteria = SelectionCriteria(
    include_patterns=["*.pdf", "*.docx"],
    exclude_patterns=["*.tmp"],
    file_types=[FileType.FILE],
    size_range=SizeRange(min_size=1024, max_size=10485760),
    date_range=DateRange(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    ),
    selection_template_id="documents-template"
)
```

### RecoveryOptions

Configuration options for recovery operations.

```python
options = RecoveryOptions(
    overwrite_existing=False,
    preserve_permissions=True,
    preserve_timestamps=True,
    verify_integrity=True,
    continue_on_error=True,
    max_retries=3,
    notification_preferences=NotificationPreferences(
        notify_on_start=True,
        notify_on_completion=True,
        notify_on_error=True,
        notification_channels=["email", "slack"]
    ),
    conflict_resolution=ConflictResolution.RENAME
)
```

### ProgressStatus

Tracks progress of recovery operations.

```python
progress = ProgressStatus(
    files_processed=50,
    total_files=100,
    bytes_transferred=5242880,
    total_bytes=10485760,
    current_file="/backup/data/current.txt",
    estimated_completion=datetime.now() + timedelta(minutes=5),
    transfer_rate=1048576  # bytes per second
)

# Properties
progress_pct = progress.progress_percentage  # 50.0
bytes_pct = progress.bytes_progress_percentage  # 50.0
```

### ValidationResult

Results of recovery validation operations.

```python
validation = ValidationResult(
    is_valid=True,
    validated_files=100,
    failed_validations=[],
    warnings=[],
    validation_time=datetime.now()
)

# Add failures dynamically
validation.add_failure(ValidationFailure(
    file_path="/restore/corrupted.txt",
    expected_checksum="abc123",
    actual_checksum="def456",
    failure_type=FailureType.CHECKSUM_MISMATCH,
    error_message="Checksum mismatch"
))

# Add warnings dynamically
validation.add_warning(ValidationWarning(
    warning_type="permission_mismatch",
    message="Permissions differ from original",
    severity="low"
))
```

## Enumerations

### RecoveryType

```python
class RecoveryType(Enum):
    FULL = "full"
    SELECTIVE = "selective"
```

### OperationStatus

```python
class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
```

### FileType

```python
class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
```

### FailureType

```python
class FailureType(Enum):
    CHECKSUM_MISMATCH = "checksum_mismatch"
    FILE_MISSING = "file_missing"
    PERMISSION_ERROR = "permission_error"
    CORRUPTION = "corruption"
    INCOMPLETE = "incomplete"
```

### ConflictResolution

```python
class ConflictResolution(Enum):
    OVERWRITE = "overwrite"
    SKIP = "skip"
    RENAME = "rename"
    PROMPT = "prompt"
```

## Supporting Models

### ErrorDetails

```python
error = ErrorDetails(
    error_type="network_timeout",
    error_message="Connection timed out",
    failed_files=["/path/to/file1.txt"],
    timestamp=datetime.now(),
    is_recoverable=True,
    suggested_action="Retry the operation"
)
```

### PaginationInfo

```python
pagination = PaginationInfo(
    current_page=1,
    page_size=50,
    total_pages=10,
    total_entries=500,
    has_next=True,
    has_previous=False
)
```

### SizeRange

```python
size_range = SizeRange(
    min_size=1024,      # 1 KB
    max_size=10485760   # 10 MB
)
```

### DateRange

```python
date_range = DateRange(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 12, 31)
)
```

### NotificationPreferences

```python
notifications = NotificationPreferences(
    notify_on_start=True,
    notify_on_completion=True,
    notify_on_error=True,
    notify_on_milestone=True,
    milestone_percentage=25,
    notification_channels=["email", "slack", "webhook"]
)
```

## Common Patterns

### Creating a Recovery Operation

```python
from datetime import datetime
from TimeLocker.interfaces import (
    RecoveryOperation,
    RecoveryType,
    OperationStatus,
    RecoveryOptions,
    ProgressStatus
)

# Create recovery options
options = RecoveryOptions(
    verify_integrity=True,
    max_retries=3
)

# Create recovery operation
operation = RecoveryOperation(
    operation_id="recovery-20251109-001",
    snapshot_id="snapshot-abc123",
    recovery_type=RecoveryType.FULL,
    target_path="/restore/backup",
    status=OperationStatus.PENDING,
    start_time=datetime.now()
)

# Update progress
operation.progress = ProgressStatus(
    files_processed=10,
    total_files=100,
    bytes_transferred=1048576,
    total_bytes=10485760,
    transfer_rate=524288
)
```

### Browsing Snapshot Contents

```python
from TimeLocker.interfaces import (
    SnapshotListing,
    FileEntry,
    FileType,
    PaginationInfo
)

# Create file entries
entries = [
    FileEntry(
        path=f"/backup/file{i}.txt",
        name=f"file{i}.txt",
        type=FileType.FILE,
        size=1024 * i,
        modification_time=datetime.now(),
        permissions="rw-r--r--"
    )
    for i in range(1, 51)
]

# Create listing with pagination
listing = SnapshotListing(
    path="/backup",
    entries=entries,
    total_entries=500,
    pagination_info=PaginationInfo(
        current_page=1,
        page_size=50,
        total_pages=10,
        total_entries=500,
        has_next=True,
        has_previous=False
    )
)
```

### Validating Recovery Results

```python
from TimeLocker.interfaces import (
    ValidationResult,
    ValidationFailure,
    ValidationWarning,
    FailureType
)

# Create validation result
validation = ValidationResult(
    is_valid=True,
    validated_files=100,
    validation_time=datetime.now()
)

# Add failure if checksum doesn't match
if actual_checksum != expected_checksum:
    validation.add_failure(ValidationFailure(
        file_path="/restore/file.txt",
        expected_checksum=expected_checksum,
        actual_checksum=actual_checksum,
        failure_type=FailureType.CHECKSUM_MISMATCH,
        error_message="File integrity check failed"
    ))

# Add warning for permission differences
if permissions_differ:
    validation.add_warning(ValidationWarning(
        warning_type="permission_mismatch",
        message="File permissions differ from original",
        context={"file": "/restore/file.txt"},
        severity="low"
    ))
```

## Validation Rules

All models include validation in their `__post_init__` methods:

- **RecoveryOperation**: operation_id, snapshot_id, and target_path cannot be empty
- **FileEntry**: path and name cannot be empty, size cannot be negative
- **ProgressStatus**: All counts and sizes must be non-negative
- **ValidationResult**: validated_files cannot be negative
- **SizeRange**: min_size cannot be greater than max_size
- **DateRange**: start_date cannot be after end_date
- **PaginationInfo**: page numbers and sizes must be positive

## Error Handling

Models raise `ValueError` with descriptive messages for invalid data:

```python
try:
    progress = ProgressStatus(
        files_processed=-1,  # Invalid!
        total_files=100,
        bytes_transferred=0,
        total_bytes=1000
    )
except ValueError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: files_processed cannot be negative
```

## See Also

- [Recovery Operations Design](../2-architecture/recovery-operations-design.md)
- [Recovery Operations Requirements](../1-requirements/recovery-operations-requirements.md)
- [Recovery Models Demo](../../examples/recovery_models_demo.py)
- [Recovery Operations Specification](.kiro/specs/recovery-operations/)
