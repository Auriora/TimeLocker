#!/usr/bin/env python3
"""
Full Recovery Workflow Demo

This example demonstrates a complete full recovery workflow including:
- Repository validation and snapshot selection
- Full snapshot restoration with all options
- Progress monitoring and status tracking
- Post-recovery verification
- Error handling and recovery strategies

Copyright © Bruce Cherrington
Licensed under GPL v3
"""

import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.snapshot_browser import SnapshotBrowser
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    NotificationPreferences,
    ConflictResolution,
    OperationStatus
)
from TimeLocker.backup_repository import BackupRepository


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_full_recovery_workflow():
    """Demonstrate complete full recovery workflow"""
    print_section("Full Recovery Workflow Demo")
    
    # Step 1: Initialize components
    print("Step 1: Initializing recovery components...")
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    browser = SnapshotBrowser(repository)
    validator = RecoveryValidator(repository)
    print("✓ Components initialized")
    
    # Step 2: Browse and select snapshot
    print("\nStep 2: Browsing available snapshots...")
    try:
        # List recent snapshots
        snapshots = repository.snapshots()
        if not snapshots:
            print("✗ No snapshots found in repository")
            return
        
        print(f"✓ Found {len(snapshots)} snapshots")
        
        # Display snapshot information
        print("\nAvailable snapshots:")
        for i, snapshot in enumerate(snapshots[:5], 1):
            print(f"  {i}. ID: {snapshot.id}")
            print(f"     Timestamp: {snapshot.timestamp}")
            print(f"     Tags: {getattr(snapshot, 'tags', [])}")
            print(f"     Size: {getattr(snapshot, 'size', 0):,} bytes")
            print()
        
        # Select latest snapshot for recovery
        selected_snapshot = snapshots[0]
        print(f"✓ Selected snapshot: {selected_snapshot.id}")
        
    except Exception as e:
        print(f"✗ Error browsing snapshots: {e}")
        return
    
    # Step 3: Preview snapshot contents
    print("\nStep 3: Previewing snapshot contents...")
    try:
        listing = browser.list_snapshot_contents(
            selected_snapshot.id,
            path="/"
        )
        
        print(f"✓ Snapshot contains {listing.total_entries} entries")
        print("\nSample contents:")
        for entry in listing.entries[:10]:
            type_icon = "📁" if entry.type.value == "directory" else "📄"
            print(f"  {type_icon} {entry.name}")
        
    except Exception as e:
        print(f"✗ Error previewing snapshot: {e}")
        return
    
    # Step 4: Pre-recovery validation
    print("\nStep 4: Performing pre-recovery validation...")
    temp_dir = Path(tempfile.mkdtemp())
    target_path = temp_dir / "full_restore"
    
    try:
        validation_result = validator.validate_pre_recovery(
            selected_snapshot.id,
            str(target_path)
        )
        
        if validation_result.is_valid:
            print("✓ Pre-recovery validation passed")
        else:
            print("✗ Pre-recovery validation failed:")
            for failure in validation_result.failed_validations:
                print(f"  - {failure.error_message}")
            return
        
        if validation_result.warnings:
            print("\nWarnings:")
            for warning in validation_result.warnings:
                print(f"  ⚠ {warning.message}")
        
    except Exception as e:
        print(f"✗ Error during pre-recovery validation: {e}")
        return
    
    # Step 5: Configure recovery options
    print("\nStep 5: Configuring recovery options...")
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
            notify_on_milestone=True,
            milestone_percentage=25
        ),
        conflict_resolution=ConflictResolution.RENAME
    )
    print("✓ Recovery options configured")
    print(f"  - Verify integrity: {options.verify_integrity}")
    print(f"  - Preserve permissions: {options.preserve_permissions}")
    print(f"  - Conflict resolution: {options.conflict_resolution.value}")
    print(f"  - Max retries: {options.max_retries}")
    
    # Step 6: Initiate full recovery
    print("\nStep 6: Initiating full recovery operation...")
    try:
        operation = orchestrator.initiate_full_recovery(
            snapshot_id=selected_snapshot.id,
            target_path=str(target_path),
            options=options
        )
        
        print(f"✓ Recovery operation started")
        print(f"  Operation ID: {operation.operation_id}")
        print(f"  Status: {operation.status.value}")
        print(f"  Start time: {operation.start_time}")
        
    except Exception as e:
        print(f"✗ Error initiating recovery: {e}")
        shutil.rmtree(temp_dir)
        return
    
    # Step 7: Monitor recovery progress
    print("\nStep 7: Monitoring recovery progress...")
    try:
        import time
        
        while True:
            status = orchestrator.get_recovery_status(operation.operation_id)
            
            if not status:
                print("✗ Unable to retrieve operation status")
                break
            
            progress = status.progress
            if progress:
                pct = (progress.files_processed / progress.total_files * 100 
                       if progress.total_files > 0 else 0)
                
                print(f"\r  Progress: {pct:.1f}% "
                      f"({progress.files_processed}/{progress.total_files} files, "
                      f"{progress.bytes_transferred:,}/{progress.total_bytes:,} bytes)",
                      end='', flush=True)
                
                if progress.current_file:
                    print(f"\n  Current: {progress.current_file}", end='')
            
            if status.status in [OperationStatus.COMPLETED, 
                                OperationStatus.FAILED, 
                                OperationStatus.CANCELLED]:
                print()  # New line after progress
                break
            
            time.sleep(1)
        
        print(f"\n✓ Recovery operation {status.status.value}")
        
    except Exception as e:
        print(f"\n✗ Error monitoring progress: {e}")
    
    # Step 8: Post-recovery validation
    print("\nStep 8: Performing post-recovery validation...")
    try:
        validation_result = validator.validate_post_recovery(
            operation.operation_id
        )
        
        print(f"✓ Validation completed")
        print(f"  Files validated: {validation_result.validated_files}")
        print(f"  Validation status: {'PASSED' if validation_result.is_valid else 'FAILED'}")
        
        if validation_result.failed_validations:
            print(f"\n  Failed validations: {len(validation_result.failed_validations)}")
            for failure in validation_result.failed_validations[:5]:
                print(f"    - {failure.file_path}: {failure.error_message}")
        
        if validation_result.warnings:
            print(f"\n  Warnings: {len(validation_result.warnings)}")
            for warning in validation_result.warnings[:5]:
                print(f"    ⚠ {warning.message}")
        
    except Exception as e:
        print(f"✗ Error during post-recovery validation: {e}")
    
    # Step 9: Verify restored files
    print("\nStep 9: Verifying restored files...")
    try:
        if target_path.exists():
            restored_files = list(target_path.rglob("*"))
            print(f"✓ Found {len(restored_files)} restored items")
            
            # Show sample of restored files
            print("\nSample restored files:")
            for file_path in restored_files[:10]:
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  📄 {file_path.name} ({size:,} bytes)")
                elif file_path.is_dir():
                    print(f"  📁 {file_path.name}/")
        else:
            print("✗ Target path does not exist")
        
    except Exception as e:
        print(f"✗ Error verifying restored files: {e}")
    
    # Step 10: Cleanup
    print("\nStep 10: Cleaning up...")
    try:
        shutil.rmtree(temp_dir)
        print(f"✓ Temporary directory cleaned up: {temp_dir}")
    except Exception as e:
        print(f"⚠ Warning: Could not clean up temporary directory: {e}")
    
    # Summary
    print_section("Recovery Workflow Summary")
    print("✓ Repository validated and snapshot selected")
    print("✓ Snapshot contents previewed")
    print("✓ Pre-recovery validation completed")
    print("✓ Recovery options configured")
    print("✓ Full recovery operation executed")
    print("✓ Progress monitored in real-time")
    print("✓ Post-recovery validation performed")
    print("✓ Restored files verified")
    print("✓ Cleanup completed")
    print("\nFull recovery workflow completed successfully!")


def main():
    """Run the full recovery workflow demo"""
    print("\n" + "=" * 80)
    print("  TimeLocker Full Recovery Workflow Demo")
    print("=" * 80)
    print("\nThis demo demonstrates a complete end-to-end full recovery workflow")
    print("including validation, monitoring, and verification.\n")
    
    try:
        demo_full_recovery_workflow()
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
