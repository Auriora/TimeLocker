"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
Recovery Operations Data Models for TimeLocker

This module provides data models for recovery operations including snapshot
browsing, file restoration, integrity verification, and progress monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class RecoveryType(Enum):
    """Type of recovery operation"""
    FULL = "full"
    SELECTIVE = "selective"


class OperationStatus(Enum):
    """Status of recovery operation"""
    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class FileType(Enum):
    """Type of file entry in snapshot"""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class FailureType(Enum):
    """Type of validation failure"""
    CHECKSUM_MISMATCH = "checksum_mismatch"
    FILE_MISSING = "file_missing"
    PERMISSION_ERROR = "permission_error"
    CORRUPTION = "corruption"
    INCOMPLETE = "incomplete"


class ConflictResolution(Enum):
    """Strategy for handling file conflicts"""
    OVERWRITE = "overwrite"
    SKIP = "skip"
    RENAME = "rename"
    PROMPT = "prompt"


@dataclass
class FileEntry:
    """
    Represents a file or directory within a snapshot.
    
    Attributes:
        path: Full path of the file within the snapshot
        name: Name of the file or directory
        type: Type of entry (FILE, DIRECTORY, SYMLINK)
        size: Size in bytes
        modification_time: Last modification timestamp
        permissions: File permissions string (e.g., "rwxr-xr-x")
        checksum: Optional checksum for integrity verification
    """
    path: str
    name: str
    type: FileType
    size: int
    modification_time: datetime
    permissions: str
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Validate file entry after initialization"""
        if not self.path:
            raise ValueError("File path cannot be empty")
        if not self.name:
            raise ValueError("File name cannot be empty")
        if self.size < 0:
            raise ValueError("File size cannot be negative")


@dataclass
class PaginationInfo:
    """
    Pagination information for large listings.
    
    Attributes:
        current_page: Current page number (1-indexed)
        page_size: Number of entries per page
        total_pages: Total number of pages
        total_entries: Total number of entries across all pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """
    current_page: int
    page_size: int
    total_pages: int
    total_entries: int
    has_next: bool
    has_previous: bool
    
    def __post_init__(self):
        """Validate pagination info"""
        if self.current_page < 1:
            raise ValueError("current_page must be >= 1")
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")
        if self.total_pages < 0:
            raise ValueError("total_pages cannot be negative")
        if self.total_entries < 0:
            raise ValueError("total_entries cannot be negative")


@dataclass
class SnapshotListing:
    """
    Represents the contents of a snapshot directory.
    
    Attributes:
        path: Path within the snapshot being listed
        entries: List of file entries in this directory
        total_entries: Total number of entries (may exceed len(entries) if paginated)
        pagination_info: Optional pagination information for large listings
    """
    path: str
    entries: List[FileEntry]
    total_entries: int
    pagination_info: Optional[PaginationInfo] = None
    
    def __post_init__(self):
        """Validate snapshot listing"""
        if self.total_entries < 0:
            raise ValueError("total_entries cannot be negative")
        if self.total_entries < len(self.entries):
            raise ValueError("total_entries cannot be less than number of entries")


@dataclass
class SizeRange:
    """
    Range for file size filtering.
    
    Attributes:
        min_size: Minimum file size in bytes (inclusive)
        max_size: Maximum file size in bytes (inclusive)
    """
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    
    def __post_init__(self):
        """Validate size range"""
        if self.min_size is not None and self.min_size < 0:
            raise ValueError("min_size cannot be negative")
        if self.max_size is not None and self.max_size < 0:
            raise ValueError("max_size cannot be negative")
        if (self.min_size is not None and self.max_size is not None and 
            self.min_size > self.max_size):
            raise ValueError("min_size cannot be greater than max_size")


@dataclass
class DateRange:
    """
    Range for date filtering.
    
    Attributes:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate date range"""
        if (self.start_date is not None and self.end_date is not None and 
            self.start_date > self.end_date):
            raise ValueError("start_date cannot be after end_date")


@dataclass
class SelectionCriteria:
    """
    Defines criteria for selective recovery operations.
    
    Attributes:
        include_patterns: List of patterns for files to include
        exclude_patterns: List of patterns for files to exclude
        file_types: List of file types to include
        size_range: Optional size range filter
        date_range: Optional date range filter
        selection_template_id: Optional ID of selection template to apply
    """
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    file_types: List[FileType] = field(default_factory=list)
    size_range: Optional[SizeRange] = None
    date_range: Optional[DateRange] = None
    selection_template_id: Optional[str] = None


@dataclass
class NotificationPreferences:
    """
    Notification preferences for recovery operations.
    
    Attributes:
        notify_on_start: Send notification when recovery starts
        notify_on_completion: Send notification when recovery completes
        notify_on_error: Send notification on errors
        notify_on_milestone: Send notifications at progress milestones
        milestone_percentage: Percentage intervals for milestone notifications
        notification_channels: List of notification channels to use
    """
    notify_on_start: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True
    notify_on_milestone: bool = False
    milestone_percentage: int = 25
    notification_channels: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate notification preferences"""
        if not 1 <= self.milestone_percentage <= 100:
            raise ValueError("milestone_percentage must be between 1 and 100")


@dataclass
class RecoveryOptions:
    """
    Configuration options for recovery operations.
    
    Attributes:
        overwrite_existing: Whether to overwrite existing files
        preserve_permissions: Whether to preserve file permissions
        preserve_timestamps: Whether to preserve file timestamps
        verify_integrity: Whether to verify file integrity after restoration
        continue_on_error: Whether to continue on individual file errors
        max_retries: Maximum number of retry attempts for failed operations
        notification_preferences: Notification configuration
        conflict_resolution: Strategy for handling file conflicts
    """
    overwrite_existing: bool = False
    preserve_permissions: bool = True
    preserve_timestamps: bool = True
    verify_integrity: bool = True
    continue_on_error: bool = True
    max_retries: int = 3
    notification_preferences: NotificationPreferences = field(
        default_factory=NotificationPreferences
    )
    conflict_resolution: ConflictResolution = ConflictResolution.PROMPT
    
    def __post_init__(self):
        """Validate recovery options"""
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")


@dataclass
class ProgressStatus:
    """
    Tracks progress of recovery operations.
    
    Attributes:
        files_processed: Number of files processed so far
        total_files: Total number of files to process
        bytes_transferred: Number of bytes transferred so far
        total_bytes: Total number of bytes to transfer
        current_file: Path of file currently being processed
        estimated_completion: Estimated completion time
        transfer_rate: Current transfer rate in bytes per second
    """
    files_processed: int
    total_files: int
    bytes_transferred: int
    total_bytes: int
    current_file: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    transfer_rate: float = 0.0
    
    def __post_init__(self):
        """Validate progress status"""
        if self.files_processed < 0:
            raise ValueError("files_processed cannot be negative")
        if self.total_files < 0:
            raise ValueError("total_files cannot be negative")
        if self.bytes_transferred < 0:
            raise ValueError("bytes_transferred cannot be negative")
        if self.total_bytes < 0:
            raise ValueError("total_bytes cannot be negative")
        if self.transfer_rate < 0:
            raise ValueError("transfer_rate cannot be negative")
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage based on files processed"""
        if self.total_files == 0:
            return 0.0
        return (self.files_processed / self.total_files) * 100.0
    
    @property
    def bytes_progress_percentage(self) -> float:
        """Calculate progress percentage based on bytes transferred"""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_transferred / self.total_bytes) * 100.0


@dataclass
class ErrorDetails:
    """
    Details about errors encountered during recovery.
    
    Attributes:
        error_type: Type of error
        error_message: Human-readable error message
        failed_files: List of files that failed to restore
        timestamp: When the error occurred
        is_recoverable: Whether the error is recoverable
        suggested_action: Suggested action to resolve the error
    """
    error_type: str
    error_message: str
    failed_files: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_recoverable: bool = False
    suggested_action: Optional[str] = None


@dataclass
class ValidationFailure:
    """
    Details of a validation failure.
    
    Attributes:
        file_path: Path of the file that failed validation
        expected_checksum: Expected checksum value
        actual_checksum: Actual checksum value
        failure_type: Type of validation failure
        error_message: Detailed error message
    """
    file_path: str
    expected_checksum: str
    actual_checksum: str
    failure_type: FailureType
    error_message: str
    
    def __post_init__(self):
        """Validate failure details"""
        if not self.file_path:
            raise ValueError("file_path cannot be empty")


@dataclass
class ValidationWarning:
    """
    Warning generated during validation.
    
    Attributes:
        warning_type: Type of warning
        message: Warning message
        context: Additional context information
        severity: Severity level (low, medium, high)
    """
    warning_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"
    
    def __post_init__(self):
        """Validate warning"""
        if self.severity not in ("low", "medium", "high"):
            raise ValueError("severity must be 'low', 'medium', or 'high'")


@dataclass
class ValidationResult:
    """
    Results of recovery validation operations.
    
    Attributes:
        is_valid: Whether validation passed
        validated_files: Number of files validated
        failed_validations: List of validation failures
        warnings: List of validation warnings
        validation_time: When validation was performed
    """
    is_valid: bool
    validated_files: int
    failed_validations: List[ValidationFailure] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    validation_time: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate result"""
        if self.validated_files < 0:
            raise ValueError("validated_files cannot be negative")
    
    def add_failure(self, failure: ValidationFailure) -> None:
        """Add a validation failure"""
        self.failed_validations.append(failure)
        self.is_valid = False
    
    def add_warning(self, warning: ValidationWarning) -> None:
        """Add a validation warning"""
        self.warnings.append(warning)


@dataclass
class RecoveryOperation:
    """
    Represents an active or completed recovery operation.
    
    Attributes:
        operation_id: Unique identifier for the operation
        snapshot_id: ID of the snapshot being restored
        recovery_type: Type of recovery (FULL or SELECTIVE)
        target_path: Destination path for restored files
        status: Current status of the operation
        start_time: When the operation started
        completion_time: When the operation completed (if finished)
        progress: Current progress status
        validation_result: Result of validation (if performed)
        error_details: Details of any errors encountered
    """
    operation_id: str
    snapshot_id: str
    recovery_type: RecoveryType
    target_path: str
    status: OperationStatus
    start_time: datetime
    completion_time: Optional[datetime] = None
    progress: Optional[ProgressStatus] = None
    validation_result: Optional[ValidationResult] = None
    error_details: Optional[ErrorDetails] = None
    
    def __post_init__(self):
        """Validate recovery operation"""
        if not self.operation_id:
            raise ValueError("operation_id cannot be empty")
        if not self.snapshot_id:
            raise ValueError("snapshot_id cannot be empty")
        if not self.target_path:
            raise ValueError("target_path cannot be empty")
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration in seconds"""
        if self.completion_time:
            return (self.completion_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.status in (
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED
        )
    
    @property
    def is_active(self) -> bool:
        """Check if operation is currently active"""
        return self.status in (
            OperationStatus.PENDING,
            OperationStatus.VALIDATING,
            OperationStatus.RUNNING
        )
    
    @property
    def is_successful(self) -> bool:
        """Check if operation completed successfully"""
        return (
            self.status == OperationStatus.COMPLETED and
            self.error_details is None
        )
