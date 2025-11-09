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
Recovery Orchestrator Demo

This example demonstrates the usage of the RecoveryOrchestrator component
for coordinating full and selective recovery operations with state management.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    SelectionCriteria,
    NotificationPreferences,
    OperationStatus
)
from TimeLocker.backup_repository import BackupRepository


def demo_full_recovery():
    """Demonstrate full recovery operation."""
    print("=" * 80)
    print("Full Recovery Operation Demo")
    print("=" * 80)
    
    # Create a mock repository (in real usage, this would be a real repository)
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    
    # Initialize the orchestrator
    orchestrator = RecoveryOrchestrator(repository)
    
    # Configure recovery options
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
            notify_on_error=True
        )
    )
    
    # Initiate full recovery
    print("\n1. Initiating full recovery operation...")
    try:
        operation = orchestrator.initiate_full_recovery(
            snapshot_id="abc123",
            target_path="/tmp/restore_target",
            options=options
        )
        
        print(f"   Operation ID: {operation.operation_id}")
        print(f"   Snapshot ID: {operation.snapshot_id}")
        print(f"   Recovery Type: {operation.recovery_type.value}")
        print(f"   Target Path: {operation.target_path}")
        print(f"   Status: {operation.status.value}")
        print(f"   Start Time: {operation.start_time}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check operation status
    print("\n2. Checking operation status...")
    status = orchestrator.get_recovery_status(operation.operation_id)
    if status:
        print(f"   Status: {status.status.value}")
        print(f"   Files Processed: {status.progress.files_processed}/{status.progress.total_files}")
        print(f"   Bytes Transferred: {status.progress.bytes_transferred}/{status.progress.total_bytes}")
        
        if status.error_details:
            print(f"   Error: {status.error_details.error_message}")
    
    # List all operations
    print("\n3. Listing all operations...")
    operations = orchestrator.list_operations()
    print(f"   Total operations: {len(operations)}")
    for op in operations:
        print(f"   - {op.operation_id}: {op.status.value} ({op.recovery_type.value})")


def demo_selective_recovery():
    """Demonstrate selective recovery operation."""
    print("\n" + "=" * 80)
    print("Selective Recovery Operation Demo")
    print("=" * 80)
    
    # Create a mock repository
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    
    # Initialize the orchestrator
    orchestrator = RecoveryOrchestrator(repository)
    
    # Configure selection criteria
    selection_criteria = SelectionCriteria(
        include_patterns=[
            "/home/user/documents/*.pdf",
            "/home/user/photos/*.jpg"
        ],
        exclude_patterns=[
            "*/temp/*",
            "*/.cache/*"
        ]
    )
    
    # Configure recovery options
    options = RecoveryOptions(
        overwrite_existing=False,
        preserve_permissions=True,
        verify_integrity=True
    )
    
    # Initiate selective recovery
    print("\n1. Initiating selective recovery operation...")
    try:
        operation = orchestrator.initiate_selective_recovery(
            snapshot_id="def456",
            selection_criteria=selection_criteria,
            target_path="/tmp/selective_restore",
            options=options
        )
        
        print(f"   Operation ID: {operation.operation_id}")
        print(f"   Snapshot ID: {operation.snapshot_id}")
        print(f"   Recovery Type: {operation.recovery_type.value}")
        print(f"   Target Path: {operation.target_path}")
        print(f"   Status: {operation.status.value}")
        print(f"   Include Patterns: {len(selection_criteria.include_patterns)}")
        print(f"   Exclude Patterns: {len(selection_criteria.exclude_patterns)}")
        
    except Exception as e:
        print(f"   Error: {e}")


def demo_operation_management():
    """Demonstrate operation management features."""
    print("\n" + "=" * 80)
    print("Operation Management Demo")
    print("=" * 80)
    
    # Create a mock repository
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    
    # Initialize the orchestrator
    orchestrator = RecoveryOrchestrator(repository)
    
    # Create a test operation
    print("\n1. Creating test operation...")
    try:
        operation = orchestrator.initiate_full_recovery(
            snapshot_id="test123",
            target_path="/tmp/test_restore",
            options=RecoveryOptions()
        )
        print(f"   Created operation: {operation.operation_id}")
        
        # Cancel the operation
        print("\n2. Cancelling operation...")
        cancelled = orchestrator.cancel_recovery(operation.operation_id)
        print(f"   Cancelled: {cancelled}")
        
        # Check status after cancellation
        status = orchestrator.get_recovery_status(operation.operation_id)
        if status:
            print(f"   Status after cancellation: {status.status.value}")
        
        # Clean up the operation
        print("\n3. Cleaning up operation...")
        cleaned = orchestrator.cleanup_operation(operation.operation_id)
        print(f"   Cleaned up: {cleaned}")
        
        # Verify cleanup
        status = orchestrator.get_recovery_status(operation.operation_id)
        print(f"   Operation exists after cleanup: {status is not None}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Demonstrate cleanup of old operations
    print("\n4. Cleaning up old operations...")
    cleaned_count = orchestrator.cleanup_old_operations(days=30)
    print(f"   Cleaned up {cleaned_count} old operations")


def demo_state_persistence():
    """Demonstrate state persistence and recovery."""
    print("\n" + "=" * 80)
    print("State Persistence Demo")
    print("=" * 80)
    
    # Create a mock repository
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    
    # Initialize the orchestrator
    print("\n1. Creating orchestrator and operation...")
    orchestrator1 = RecoveryOrchestrator(repository)
    
    try:
        operation = orchestrator1.initiate_full_recovery(
            snapshot_id="persist123",
            target_path="/tmp/persist_restore",
            options=RecoveryOptions()
        )
        print(f"   Created operation: {operation.operation_id}")
        print(f"   Status: {operation.status.value}")
        
        # Simulate application restart by creating new orchestrator
        print("\n2. Simulating application restart...")
        orchestrator2 = RecoveryOrchestrator(repository)
        
        # Check if operation was loaded
        loaded_operation = orchestrator2.get_recovery_status(operation.operation_id)
        if loaded_operation:
            print(f"   Operation loaded after restart: {loaded_operation.operation_id}")
            print(f"   Status: {loaded_operation.status.value}")
        else:
            print("   Operation not found after restart")
        
    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run all demos."""
    print("\nRecovery Orchestrator Component Demo")
    print("=" * 80)
    print("\nThis demo showcases the RecoveryOrchestrator component which coordinates")
    print("recovery operations with state management and persistence.\n")
    
    try:
        demo_full_recovery()
        demo_selective_recovery()
        demo_operation_management()
        demo_state_persistence()
        
        print("\n" + "=" * 80)
        print("Demo completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
