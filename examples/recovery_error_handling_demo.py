"""
Recovery Error Handling Demonstration

This example demonstrates the recovery error handling and retry logic
capabilities of the TimeLocker recovery operations system.

Copyright ©  Bruce Cherrington
Licensed under GNU General Public License v3.0
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.recovery_error_handler import (
    RecoveryErrorHandler,
    RetryPolicy,
    RecoveryContext,
    ErrorCategory,
    ErrorSeverity,
    RecoveryAction
)
from TimeLocker.recovery_network_handler import (
    NetworkInterruptionHandler,
    ResumePoint
)
from TimeLocker.recovery_filesystem_handler import (
    FileSystemErrorHandler,
    AlternativePath
)
from TimeLocker.recovery_errors import (
    RestoreInterruptedError,
    NetworkInterruptionError,
    InsufficientSpaceError,
    RestorePermissionError,
    FileSystemFullError,
    PathTooLongError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_recovery_error_handler():
    """Demonstrate the RecoveryErrorHandler capabilities."""
    print("\n" + "=" * 80)
    print("Recovery Error Handler Demo")
    print("=" * 80)
    
    # Create error handler with custom retry policy
    retry_policy = RetryPolicy(
        max_retries=3,
        initial_delay=1.0,
        backoff_multiplier=2.0,
        max_delay=10.0
    )
    
    error_handler = RecoveryErrorHandler(retry_policy=retry_policy)
    
    # Create recovery context
    context = RecoveryContext(
        operation_id="demo-op-001",
        snapshot_id="snapshot-123",
        target_path="/tmp/restore",
        current_file="/tmp/restore/data/file.txt",
        files_processed=50,
        total_files=100,
        retry_count=0
    )
    
    print("\n1. Handling Transient Error (Interrupted Restore)")
    print("-" * 80)
    
    try:
        raise RestoreInterruptedError("Network connection lost during restore")
    except RestoreInterruptedError as e:
        result = error_handler.handle_recovery_error(e, context)
        print(f"   Error: {e}")
        print(f"   Action: {result.action.value}")
        print(f"   Should Retry: {result.should_retry}")
        print(f"   Retry Delay: {result.retry_delay:.1f}s")
    
    print("\n2. Handling Resource Error (Insufficient Space)")
    print("-" * 80)
    
    try:
        raise InsufficientSpaceError("Not enough disk space for restore")
    except InsufficientSpaceError as e:
        result = error_handler.handle_recovery_error(e, context)
        print(f"   Error: {e}")
        print(f"   Action: {result.action.value}")
        print(f"   Should Retry: {result.should_retry}")
        print(f"   Message: {result.error_message}")
    
    print("\n3. Handling Permission Error")
    print("-" * 80)
    
    context.current_file = "/tmp/restore/protected/file.txt"
    
    try:
        raise RestorePermissionError("Permission denied for file")
    except RestorePermissionError as e:
        result = error_handler.handle_recovery_error(e, context)
        print(f"   Error: {e}")
        print(f"   Action: {result.action.value}")
        print(f"   Should Retry: {result.should_retry}")
        print(f"   Message: {result.error_message}")
    
    print("\n4. Testing Retry Logic")
    print("-" * 80)
    
    for attempt in range(4):
        context.retry_count = attempt
        should_retry = error_handler.should_retry(
            RestoreInterruptedError("Transient error"),
            attempt
        )
        print(f"   Attempt {attempt + 1}: Should retry = {should_retry}")
    
    print("\n5. Error Statistics")
    print("-" * 80)
    
    stats = error_handler.get_error_statistics()
    print(f"   Total Errors: {stats['total_errors']}")
    print(f"   Errors by Category: {stats['errors_by_category']}")
    print(f"   Errors by Severity: {stats['errors_by_severity']}")
    print(f"   Escalated Errors: {stats['escalated_errors']}")
    
    print("\n6. Error Escalation")
    print("-" * 80)
    
    try:
        raise InsufficientSpaceError("Critical space shortage")
    except InsufficientSpaceError as e:
        error_handler.escalate_error(
            e,
            context,
            reason="Cannot proceed without additional disk space"
        )
        print(f"   Error escalated: {e}")
        print(f"   Check logs for escalation details")


def demo_network_interruption_handler():
    """Demonstrate the NetworkInterruptionHandler capabilities."""
    print("\n" + "=" * 80)
    print("Network Interruption Handler Demo")
    print("=" * 80)
    
    # Create network handler
    network_handler = NetworkInterruptionHandler(
        max_retries=3,
        initial_retry_delay=1.0,
        max_retry_delay=10.0
    )
    
    print("\n1. Checking Network Connectivity")
    print("-" * 80)
    
    is_connected = network_handler.check_network_connectivity()
    print(f"   Network Connected: {is_connected}")
    
    network_state = network_handler.get_network_state()
    print(f"   Consecutive Failures: {network_state.consecutive_failures}")
    print(f"   Last Check: {network_state.last_check}")
    
    print("\n2. Saving Resume Point")
    print("-" * 80)
    
    network_handler.save_resume_point(
        operation_id="demo-op-001",
        snapshot_id="snapshot-123",
        last_completed_file="/data/file50.txt",
        files_completed=50,
        bytes_transferred=1024 * 1024 * 500  # 500 MB
    )
    print("   Resume point saved")
    
    resume_point = network_handler.get_resume_point("demo-op-001")
    if resume_point:
        print(f"   Operation ID: {resume_point.operation_id}")
        print(f"   Last Completed File: {resume_point.last_completed_file}")
        print(f"   Files Completed: {resume_point.files_completed}")
        print(f"   Bytes Transferred: {resume_point.bytes_transferred / (1024**2):.1f} MB")
    
    print("\n3. Simulating Network Error Handling")
    print("-" * 80)
    
    # Simulate a network error
    try:
        raise NetworkInterruptionError("Connection timeout")
    except NetworkInterruptionError as e:
        print(f"   Network Error: {e}")
        
        # Note: In real usage, this would retry the operation
        # For demo, we just show the decision
        should_retry = network_handler.handle_network_error(
            e,
            operation_id="demo-op-001",
            retry_count=0
        )
        print(f"   Should Retry: {should_retry}")
    
    print("\n4. Network Health Check")
    print("-" * 80)
    
    is_healthy = network_handler.is_network_healthy()
    print(f"   Network Healthy: {is_healthy}")
    
    # Clear resume point
    network_handler.clear_resume_point("demo-op-001")
    print("   Resume point cleared")


def demo_filesystem_error_handler():
    """Demonstrate the FileSystemErrorHandler capabilities."""
    print("\n" + "=" * 80)
    print("File System Error Handler Demo")
    print("=" * 80)
    
    # Create filesystem handler with alternative paths
    fs_handler = FileSystemErrorHandler(
        min_free_space_mb=100,
        max_path_length=255,
        alternative_base_paths=["/tmp/alt1", "/tmp/alt2"]
    )
    
    print("\n1. Checking File System Space")
    print("-" * 80)
    
    target_path = "/tmp/restore"
    required_bytes = 1024 * 1024 * 100  # 100 MB
    
    try:
        has_space = fs_handler.check_filesystem_space(target_path, required_bytes)
        print(f"   Target Path: {target_path}")
        print(f"   Required: {required_bytes / (1024**2):.1f} MB")
        print(f"   Has Sufficient Space: {has_space}")
    except Exception as e:
        print(f"   Error checking space: {e}")
    
    print("\n2. Getting File System Info")
    print("-" * 80)
    
    try:
        fs_info = fs_handler.get_filesystem_info("/tmp")
        print(f"   Path: {fs_info.path}")
        print(f"   Total Space: {fs_info.total_space / (1024**3):.2f} GB")
        print(f"   Free Space: {fs_info.free_space / (1024**3):.2f} GB")
        print(f"   Used Space: {fs_info.used_space / (1024**3):.2f} GB")
        print(f"   Writable: {fs_info.is_writable}")
        print(f"   Readable: {fs_info.is_readable}")
        print(f"   Mount Point: {fs_info.mount_point}")
    except Exception as e:
        print(f"   Error getting filesystem info: {e}")
    
    print("\n3. Validating Path Length")
    print("-" * 80)
    
    # Test with a normal path
    normal_path = "/tmp/restore/data/file.txt"
    is_valid, truncated = fs_handler.validate_path_length(normal_path)
    print(f"   Path: {normal_path}")
    print(f"   Length: {len(normal_path)}")
    print(f"   Valid: {is_valid}")
    
    # Test with a very long path
    long_path = "/tmp/restore/" + "a" * 300 + ".txt"
    is_valid, truncated = fs_handler.validate_path_length(long_path)
    print(f"\n   Long Path Length: {len(long_path)}")
    print(f"   Valid: {is_valid}")
    if truncated:
        print(f"   Truncated Path: {truncated}")
        print(f"   Truncated Length: {len(truncated)}")
    
    print("\n4. Handling Permission Error")
    print("-" * 80)
    
    test_path = "/tmp/restore/test_file.txt"
    success, result = fs_handler.handle_permission_error(test_path, "write")
    print(f"   Target Path: {test_path}")
    print(f"   Success: {success}")
    if result:
        if success:
            print(f"   Alternative Path: {result}")
        else:
            print(f"   Error: {result}")
    
    print("\n5. Alternative Paths Used")
    print("-" * 80)
    
    alt_paths = fs_handler.get_alternative_paths()
    if alt_paths:
        for i, alt in enumerate(alt_paths, 1):
            print(f"   {i}. Original: {alt.original_path}")
            print(f"      Alternative: {alt.alternative_path}")
            print(f"      Reason: {alt.reason}")
    else:
        print("   No alternative paths used")


def demo_integrated_error_handling():
    """Demonstrate integrated error handling across all handlers."""
    print("\n" + "=" * 80)
    print("Integrated Error Handling Demo")
    print("=" * 80)
    
    # Create all handlers
    error_handler = RecoveryErrorHandler()
    network_handler = NetworkInterruptionHandler()
    fs_handler = FileSystemErrorHandler()
    
    # Create recovery context
    context = RecoveryContext(
        operation_id="integrated-op-001",
        snapshot_id="snapshot-456",
        target_path="/tmp/restore",
        files_processed=25,
        total_files=100
    )
    
    print("\n1. Simulating Recovery Operation with Multiple Error Types")
    print("-" * 80)
    
    # Simulate various errors during recovery
    errors_to_handle = [
        (RestoreInterruptedError("Network timeout"), "Network interruption"),
        (FileSystemFullError("Disk full"), "File system full"),
        (PathTooLongError("Path exceeds limit"), "Path too long"),
        (RestorePermissionError("Access denied"), "Permission denied")
    ]
    
    for error, description in errors_to_handle:
        print(f"\n   Handling: {description}")
        print(f"   Error: {error}")
        
        # Handle with error handler
        result = error_handler.handle_recovery_error(error, context)
        print(f"   Action: {result.action.value}")
        print(f"   Should Retry: {result.should_retry}")
        
        # Update context for next iteration
        context.retry_count += 1
    
    print("\n2. Final Error Statistics")
    print("-" * 80)
    
    stats = error_handler.get_error_statistics()
    print(f"   Total Errors Handled: {stats['total_errors']}")
    print(f"   Errors by Category:")
    for category, count in stats['errors_by_category'].items():
        print(f"      {category}: {count}")
    print(f"   Errors by Severity:")
    for severity, count in stats['errors_by_severity'].items():
        print(f"      {severity}: {count}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 80)
    print("TimeLocker Recovery Error Handling Demonstration")
    print("=" * 80)
    
    try:
        demo_recovery_error_handler()
        demo_network_interruption_handler()
        demo_filesystem_error_handler()
        demo_integrated_error_handling()
        
        print("\n" + "=" * 80)
        print("All demonstrations completed successfully!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Error during demonstration: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
