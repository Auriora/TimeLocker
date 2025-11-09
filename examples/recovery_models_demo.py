#!/usr/bin/env python3
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
Recovery Operations Data Models Demo

This example demonstrates the usage of recovery operations data models
including RecoveryOperation, SnapshotListing, FileEntry, SelectionCriteria,
RecoveryOptions, ProgressStatus, and ValidationResult.
"""

from datetime import datetime, timedelta
from TimeLocker.interfaces.recovery_models import (
    RecoveryOperation,
    SnapshotListing,
    FileEntry,
    SelectionCriteria,
    RecoveryOptions,
    ProgressStatus,
    ValidationResult,
    ValidationFailure,
    ValidationWarning,
    ErrorDetails,
    PaginationInfo,
    SizeRange,
    DateRange,
    NotificationPreferences,
    RecoveryType,
    OperationStatus,
    FileType,
    FailureType,
    ConflictResolution
)


def demo_file_entry():
    """Demonstrate FileEntry creation and usage"""
    print("=" * 60)
    print("FileEntry Demo")
    print("=" * 60)
    
    # Create a file entry
    file_entry = FileEntry(
        path="/backup/documents/report.pdf",
        name="report.pdf",
        type=FileType.FILE,
        size=2048576,  # 2 MB
        modification_time=datetime.now(),
        permissions="rw-r--r--",
        checksum="sha256:abc123def456"
    )
    
    print(f"File: {file_entry.name}")
    print(f"Path: {file_entry.path}")
    print(f"Type: {file_entry.type.value}")
    print(f"Size: {file_entry.size:,} bytes")
    print(f"Permissions: {file_entry.permissions}")
    print(f"Checksum: {file_entry.checksum}")
    print()


def demo_snapshot_listing():
    """Demonstrate SnapshotListing with pagination"""
    print("=" * 60)
    print("SnapshotListing Demo")
    print("=" * 60)
    
    # Create sample file entries
    entries = [
        FileEntry(
            path=f"/backup/data/file{i}.txt",
            name=f"file{i}.txt",
            type=FileType.FILE,
            size=1024 * i,
            modification_time=datetime.now(),
            permissions="rw-r--r--"
        )
        for i in range(1, 11)
    ]
    
    # Create pagination info
    pagination = PaginationInfo(
        current_page=1,
        page_size=10,
        total_pages=5,
        total_entries=50,
        has_next=True,
        has_previous=False
    )
    
    # Create snapshot listing
    listing = SnapshotListing(
        path="/backup/data",
        entries=entries,
        total_entries=50,
        pagination_info=pagination
    )
    
    print(f"Listing path: {listing.path}")
    print(f"Entries on this page: {len(listing.entries)}")
    print(f"Total entries: {listing.total_entries}")
    print(f"Page {pagination.current_page} of {pagination.total_pages}")
    print(f"Has next page: {pagination.has_next}")
    print()


def demo_selection_criteria():
    """Demonstrate SelectionCriteria for selective recovery"""
    print("=" * 60)
    print("SelectionCriteria Demo")
    print("=" * 60)
    
    # Create size range filter
    size_range = SizeRange(
        min_size=1024,  # 1 KB
        max_size=10485760  # 10 MB
    )
    
    # Create date range filter
    date_range = DateRange(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    # Create selection criteria
    criteria = SelectionCriteria(
        include_patterns=["*.pdf", "*.docx", "*.txt"],
        exclude_patterns=["*.tmp", "*.bak"],
        file_types=[FileType.FILE],
        size_range=size_range,
        date_range=date_range,
        selection_template_id="documents-template"
    )
    
    print("Include patterns:")
    for pattern in criteria.include_patterns:
        print(f"  - {pattern}")
    
    print("\nExclude patterns:")
    for pattern in criteria.exclude_patterns:
        print(f"  - {pattern}")
    
    print(f"\nSize range: {size_range.min_size:,} - {size_range.max_size:,} bytes")
    print(f"Date range: {date_range.start_date.date()} to {date_range.end_date.date()}")
    print(f"Template ID: {criteria.selection_template_id}")
    print()


def demo_recovery_options():
    """Demonstrate RecoveryOptions configuration"""
    print("=" * 60)
    print("RecoveryOptions Demo")
    print("=" * 60)
    
    # Create notification preferences
    notifications = NotificationPreferences(
        notify_on_start=True,
        notify_on_completion=True,
        notify_on_error=True,
        notify_on_milestone=True,
        milestone_percentage=25,
        notification_channels=["email", "slack"]
    )
    
    # Create recovery options
    options = RecoveryOptions(
        overwrite_existing=False,
        preserve_permissions=True,
        preserve_timestamps=True,
        verify_integrity=True,
        continue_on_error=True,
        max_retries=3,
        notification_preferences=notifications,
        conflict_resolution=ConflictResolution.RENAME
    )
    
    print(f"Overwrite existing: {options.overwrite_existing}")
    print(f"Preserve permissions: {options.preserve_permissions}")
    print(f"Preserve timestamps: {options.preserve_timestamps}")
    print(f"Verify integrity: {options.verify_integrity}")
    print(f"Continue on error: {options.continue_on_error}")
    print(f"Max retries: {options.max_retries}")
    print(f"Conflict resolution: {options.conflict_resolution.value}")
    print(f"\nNotification channels: {', '.join(notifications.notification_channels)}")
    print(f"Milestone notifications: Every {notifications.milestone_percentage}%")
    print()


def demo_progress_status():
    """Demonstrate ProgressStatus tracking"""
    print("=" * 60)
    print("ProgressStatus Demo")
    print("=" * 60)
    
    # Create progress status
    progress = ProgressStatus(
        files_processed=750,
        total_files=1000,
        bytes_transferred=7516192768,  # ~7 GB
        total_bytes=10737418240,  # 10 GB
        current_file="/backup/data/large_file.zip",
        estimated_completion=datetime.now() + timedelta(minutes=15),
        transfer_rate=8388608  # 8 MB/s
    )
    
    print(f"Files: {progress.files_processed} / {progress.total_files}")
    print(f"Progress: {progress.progress_percentage:.1f}%")
    print(f"Bytes: {progress.bytes_transferred:,} / {progress.total_bytes:,}")
    print(f"Bytes progress: {progress.bytes_progress_percentage:.1f}%")
    print(f"Current file: {progress.current_file}")
    print(f"Transfer rate: {progress.transfer_rate / 1024 / 1024:.2f} MB/s")
    print(f"Estimated completion: {progress.estimated_completion.strftime('%H:%M:%S')}")
    print()


def demo_validation_result():
    """Demonstrate ValidationResult with failures and warnings"""
    print("=" * 60)
    print("ValidationResult Demo")
    print("=" * 60)
    
    # Create validation failures
    failures = [
        ValidationFailure(
            file_path="/restore/data/corrupted.dat",
            expected_checksum="sha256:abc123",
            actual_checksum="sha256:def456",
            failure_type=FailureType.CHECKSUM_MISMATCH,
            error_message="File checksum does not match expected value"
        ),
        ValidationFailure(
            file_path="/restore/data/missing.txt",
            expected_checksum="sha256:xyz789",
            actual_checksum="",
            failure_type=FailureType.FILE_MISSING,
            error_message="File was not restored"
        )
    ]
    
    # Create validation warnings
    warnings = [
        ValidationWarning(
            warning_type="permission_mismatch",
            message="File permissions differ from original",
            context={"file": "/restore/data/script.sh"},
            severity="low"
        )
    ]
    
    # Create validation result
    validation = ValidationResult(
        is_valid=False,
        validated_files=998,
        failed_validations=failures,
        warnings=warnings,
        validation_time=datetime.now()
    )
    
    print(f"Validation status: {'PASSED' if validation.is_valid else 'FAILED'}")
    print(f"Files validated: {validation.validated_files}")
    print(f"Failed validations: {len(validation.failed_validations)}")
    print(f"Warnings: {len(validation.warnings)}")
    
    print("\nFailures:")
    for failure in validation.failed_validations:
        print(f"  - {failure.file_path}")
        print(f"    Type: {failure.failure_type.value}")
        print(f"    Message: {failure.error_message}")
    
    print("\nWarnings:")
    for warning in validation.warnings:
        print(f"  - [{warning.severity.upper()}] {warning.message}")
    print()


def demo_recovery_operation():
    """Demonstrate complete RecoveryOperation"""
    print("=" * 60)
    print("RecoveryOperation Demo")
    print("=" * 60)
    
    # Create progress status
    progress = ProgressStatus(
        files_processed=1000,
        total_files=1000,
        bytes_transferred=10737418240,
        total_bytes=10737418240,
        transfer_rate=0.0
    )
    
    # Create validation result
    validation = ValidationResult(
        is_valid=True,
        validated_files=1000,
        validation_time=datetime.now()
    )
    
    # Create recovery operation
    start_time = datetime.now() - timedelta(hours=1)
    operation = RecoveryOperation(
        operation_id="recovery-20231109-001",
        snapshot_id="snapshot-abc123",
        recovery_type=RecoveryType.SELECTIVE,
        target_path="/restore/documents",
        status=OperationStatus.COMPLETED,
        start_time=start_time,
        completion_time=datetime.now(),
        progress=progress,
        validation_result=validation
    )
    
    print(f"Operation ID: {operation.operation_id}")
    print(f"Snapshot ID: {operation.snapshot_id}")
    print(f"Recovery type: {operation.recovery_type.value}")
    print(f"Target path: {operation.target_path}")
    print(f"Status: {operation.status.value}")
    print(f"Duration: {operation.duration:.2f} seconds")
    print(f"Is complete: {operation.is_complete}")
    print(f"Is successful: {operation.is_successful}")
    print(f"\nProgress: {operation.progress.progress_percentage:.1f}%")
    print(f"Validation: {'PASSED' if operation.validation_result.is_valid else 'FAILED'}")
    print()


def demo_error_handling():
    """Demonstrate error handling with ErrorDetails"""
    print("=" * 60)
    print("Error Handling Demo")
    print("=" * 60)
    
    # Create error details
    error = ErrorDetails(
        error_type="network_timeout",
        error_message="Connection to repository timed out after 30 seconds",
        failed_files=[
            "/backup/data/large_file1.zip",
            "/backup/data/large_file2.zip"
        ],
        timestamp=datetime.now(),
        is_recoverable=True,
        suggested_action="Retry the operation or check network connectivity"
    )
    
    # Create recovery operation with error
    operation = RecoveryOperation(
        operation_id="recovery-20231109-002",
        snapshot_id="snapshot-def456",
        recovery_type=RecoveryType.FULL,
        target_path="/restore/backup",
        status=OperationStatus.FAILED,
        start_time=datetime.now() - timedelta(minutes=5),
        completion_time=datetime.now(),
        error_details=error
    )
    
    print(f"Operation ID: {operation.operation_id}")
    print(f"Status: {operation.status.value}")
    print(f"Error type: {error.error_type}")
    print(f"Error message: {error.error_message}")
    print(f"Is recoverable: {error.is_recoverable}")
    print(f"Failed files: {len(error.failed_files)}")
    print(f"Suggested action: {error.suggested_action}")
    print()


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("Recovery Operations Data Models Demo")
    print("=" * 60 + "\n")
    
    demo_file_entry()
    demo_snapshot_listing()
    demo_selection_criteria()
    demo_recovery_options()
    demo_progress_status()
    demo_validation_result()
    demo_recovery_operation()
    demo_error_handling()
    
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
