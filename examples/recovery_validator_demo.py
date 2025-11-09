#!/usr/bin/env python3
"""
Recovery Validator Demo

This example demonstrates the RecoveryValidator component for integrity
verification during recovery operations.

Copyright © Bruce Cherrington
Licensed under GPL-3.0
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.restic.restic_repository import ResticRepository
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.snapshot_browser import SnapshotBrowser
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.interfaces.recovery_models import (
    SelectionCriteria,
    FileEntry,
    FileType,
    ValidationResult
)


def create_demo_repository():
    """Create a demo repository for examples (may not be functional)"""
    try:
        # Try to create a restic repository
        # Note: This will fail if restic is not installed or repository doesn't exist
        return ResticRepository(
            location="s3:s3.amazonaws.com/demo-bucket",
            password="demo-password"
        )
    except Exception as e:
        print(f"Note: Could not create real repository ({e})")
        print("Continuing with demonstration using mock data...")
        # Return None and handle gracefully in demos
        return None


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}\n")


def print_validation_result(result: ValidationResult):
    """Print validation result details"""
    print(f"Valid: {result.is_valid}")
    print(f"Validated Files: {result.validated_files}")
    print(f"Failures: {len(result.failed_validations)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Validation Time: {result.validation_time}")
    
    if result.failed_validations:
        print("\nFailures:")
        for failure in result.failed_validations:
            print(f"  - {failure.file_path}: {failure.error_message}")
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - [{warning.severity}] {warning.message}")


def demo_pre_recovery_validation():
    """Demonstrate pre-recovery validation"""
    print_section("Pre-Recovery Validation Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        print("Skipping pre-recovery validation demo (no repository available)")
        return
    
    # Create validator
    validator = RecoveryValidator(repository)
    
    print("Validating recovery prerequisites...")
    
    # Validate pre-recovery conditions
    result = validator.validate_pre_recovery(
        snapshot_id="abc123",
        target_path="/tmp/restore",
        selection_criteria=None
    )
    
    print_validation_result(result)
    
    if result.is_valid:
        print("\n✓ Recovery can proceed")
    else:
        print("\n✗ Recovery cannot proceed - fix issues first")


def demo_file_integrity_verification():
    """Demonstrate file integrity verification"""
    print_section("File Integrity Verification Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        print("Note: Demonstrating file integrity verification without repository")
        # Create a minimal validator for demonstration
        from unittest.mock import Mock
        repository = Mock()
        repository.uri = Mock(return_value="demo://repository")
        repository.to_env = Mock(return_value={})
    
    validator = RecoveryValidator(repository)
    
    # Example: Verify a single file
    print("Verifying single file integrity...")
    
    # In a real scenario, you would have the actual file and checksum
    test_file = "/tmp/test_file.txt"
    expected_checksum = "abc123def456"  # Example checksum
    
    try:
        # Create a test file for demonstration
        Path(test_file).write_text("Test content")
        
        # Compute actual checksum
        actual_checksum = validator._compute_file_checksum(Path(test_file))
        print(f"File: {test_file}")
        print(f"Checksum: {actual_checksum}")
        
        # Verify integrity (will fail since checksums don't match)
        is_valid = validator.verify_file_integrity(test_file, expected_checksum)
        print(f"Integrity Check: {'✓ PASSED' if is_valid else '✗ FAILED'}")
        
        # Clean up
        Path(test_file).unlink()
        
    except Exception as e:
        print(f"Error: {e}")


def demo_corruption_detection():
    """Demonstrate corruption detection"""
    print_section("Corruption Detection Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        from unittest.mock import Mock
        repository = Mock()
        repository.uri = Mock(return_value="demo://repository")
        repository.to_env = Mock(return_value={})
    
    validator = RecoveryValidator(repository)
    
    # Create test file
    test_file = "/tmp/test_corruption.txt"
    test_content = "This is test content for corruption detection"
    Path(test_file).write_text(test_content)
    
    expected_size = len(test_content.encode())
    expected_checksum = validator._compute_file_checksum(Path(test_file))
    
    print(f"Testing file: {test_file}")
    print(f"Expected size: {expected_size} bytes")
    print(f"Expected checksum: {expected_checksum}")
    
    # Detect corruption (should pass)
    result = validator.detect_corruption(
        test_file,
        expected_size,
        expected_checksum
    )
    
    print(f"\nCorruption detected: {result['corrupted']}")
    print(f"Severity: {result['severity']}")
    if result['issues']:
        print("Issues:")
        for issue in result['issues']:
            print(f"  - {issue}")
    else:
        print("✓ No corruption detected")
    
    # Clean up
    Path(test_file).unlink()


def demo_batch_verification():
    """Demonstrate batch file verification"""
    print_section("Batch File Verification Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        from unittest.mock import Mock
        repository = Mock()
        repository.uri = Mock(return_value="demo://repository")
        repository.to_env = Mock(return_value={})
    
    validator = RecoveryValidator(repository)
    
    # Create test files
    test_dir = Path("/tmp/batch_verify_test")
    test_dir.mkdir(exist_ok=True)
    
    file_checksums = {}
    
    # Create multiple test files
    for i in range(3):
        file_path = test_dir / f"file_{i}.txt"
        content = f"Test content for file {i}"
        file_path.write_text(content)
        
        # Compute checksum
        checksum = validator._compute_file_checksum(file_path)
        file_checksums[str(file_path)] = checksum
    
    print(f"Created {len(file_checksums)} test files")
    print("Performing batch verification...")
    
    # Verify all files
    result = validator.batch_verify_files(file_checksums)
    
    print_validation_result(result)
    
    # Clean up
    for file_path in file_checksums.keys():
        Path(file_path).unlink()
    test_dir.rmdir()


def demo_validation_report():
    """Demonstrate validation report generation"""
    print_section("Validation Report Generation Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        from unittest.mock import Mock
        repository = Mock()
        repository.uri = Mock(return_value="demo://repository")
        repository.to_env = Mock(return_value={})
    
    validator = RecoveryValidator(repository)
    
    # Create a sample validation result
    from TimeLocker.interfaces.recovery_models import (
        ValidationFailure,
        ValidationWarning,
        FailureType
    )
    
    result = ValidationResult(
        is_valid=False,
        validated_files=10,
        validation_time=datetime.now()
    )
    
    # Add some failures
    result.add_failure(ValidationFailure(
        file_path="/path/to/file1.txt",
        expected_checksum="abc123",
        actual_checksum="def456",
        failure_type=FailureType.CHECKSUM_MISMATCH,
        error_message="Checksum does not match"
    ))
    
    result.add_failure(ValidationFailure(
        file_path="/path/to/file2.txt",
        expected_checksum="",
        actual_checksum="",
        failure_type=FailureType.FILE_MISSING,
        error_message="File not found"
    ))
    
    # Add some warnings
    result.add_warning(ValidationWarning(
        warning_type="disk_space",
        message="Low disk space remaining",
        severity="medium"
    ))
    
    # Generate report
    print("Generating validation report...")
    report = validator.generate_verification_report(result)
    
    print("\n" + report)


def demo_validated_file_list():
    """Demonstrate validating a list of restored files"""
    print_section("Validated File List Demo")
    
    repository = create_demo_repository()
    
    if repository is None:
        from unittest.mock import Mock
        repository = Mock()
        repository.uri = Mock(return_value="demo://repository")
        repository.to_env = Mock(return_value={})
    
    validator = RecoveryValidator(repository)
    
    # Create test directory and files
    test_dir = Path("/tmp/validated_files_test")
    test_dir.mkdir(exist_ok=True)
    
    # Create file entries
    file_entries = []
    
    for i in range(3):
        file_path = test_dir / f"file_{i}.txt"
        content = f"Test content {i}"
        file_path.write_text(content)
        
        # Compute checksum
        checksum = validator._compute_file_checksum(file_path)
        
        # Create file entry
        entry = FileEntry(
            path=f"file_{i}.txt",
            name=f"file_{i}.txt",
            type=FileType.FILE,
            size=len(content.encode()),
            modification_time=datetime.now(),
            permissions="rw-r--r--",
            checksum=checksum
        )
        file_entries.append(entry)
    
    print(f"Created {len(file_entries)} test files")
    print("Validating restored files...")
    
    # Validate the files
    result = validator.validate_restored_files(
        snapshot_id="test-snapshot",
        target_path=str(test_dir),
        file_list=file_entries
    )
    
    print_validation_result(result)
    
    # Clean up
    for entry in file_entries:
        (test_dir / entry.name).unlink()
    test_dir.rmdir()


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("RECOVERY VALIDATOR DEMONSTRATION")
    print("=" * 80)
    
    try:
        demo_pre_recovery_validation()
        demo_file_integrity_verification()
        demo_corruption_detection()
        demo_batch_verification()
        demo_validation_report()
        demo_validated_file_list()
        
        print_section("Demo Complete")
        print("All recovery validator demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
