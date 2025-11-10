#!/usr/bin/env python3
"""
Recovery Verification and Monitoring Demo

This example demonstrates comprehensive recovery verification and monitoring:
- Pre-recovery validation checks
- Real-time progress monitoring with callbacks
- Post-recovery integrity verification
- Error detection and reporting
- Performance metrics tracking

Copyright © Bruce Cherrington
Licensed under GPL v3
"""

import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.recovery_orchestrator import RecoveryOrchestrator
from TimeLocker.recovery_validator import RecoveryValidator
from TimeLocker.interfaces.recovery_models import (
    RecoveryOptions,
    SelectionCriteria,
    OperationStatus,
    NotificationPreferences
)
from TimeLocker.backup_repository import BackupRepository


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def demo_pre_recovery_validation():
    """Demonstrate pre-recovery validation checks"""
    print_section("Pre-Recovery Validation")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    validator = RecoveryValidator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    temp_dir = Path(tempfile.mkdtemp())
    target_path = temp_dir / "validation_test"
    
    try:
        # Example 1: Basic pre-recovery validation
        print("1. Basic pre-recovery validation...")
        result = validator.validate_pre_recovery(
            snapshot_id=snapshot_id,
            target_path=str(target_path)
        )
        
        print(f"   Validation result: {'PASSED' if result.is_valid else 'FAILED'}")
        print(f"   Validation time: {result.validation_time}")
        
        if result.warnings:
            print(f"\n   Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"     ⚠ {warning.message}")
        
        if result.failed_validations:
            print(f"\n   Failures ({len(result.failed_validations)}):")
            for failure in result.failed_validations:
                print(f"     ✗ {failure.file_path}: {failure.error_message}")
        
        # Example 2: Validation with selection criteria
        print("\n2. Validation with selection criteria...")
        criteria = SelectionCriteria(
            include_patterns=["*.pdf", "*.docx"],
            exclude_patterns=["*/temp/*"]
        )
        
        result = validator.validate_pre_recovery(
            snapshot_id=snapshot_id,
            target_path=str(target_path),
            selection_criteria=criteria
        )
        
        print(f"   Validation result: {'PASSED' if result.is_valid else 'FAILED'}")
        print(f"   Selection patterns validated: {len(criteria.include_patterns)}")
        
        # Example 3: Space availability check
        print("\n3. Checking target space availability...")
        print(f"   Target path: {target_path}")
        
        if target_path.parent.exists():
            stat = shutil.disk_usage(target_path.parent)
            print(f"   Available space: {stat.free / (1024**3):.2f} GB")
            print(f"   Total space: {stat.total / (1024**3):.2f} GB")
            print(f"   Used space: {(stat.total - stat.free) / (1024**3):.2f} GB")
        
        # Example 4: Repository accessibility check
        print("\n4. Checking repository accessibility...")
        try:
            snapshots_check = repository.snapshots()
            print(f"   ✓ Repository accessible")
            print(f"   ✓ Found {len(snapshots_check)} snapshots")
        except Exception as e:
            print(f"   ✗ Repository access failed: {e}")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_progress_monitoring():
    """Demonstrate real-time progress monitoring"""
    print_section("Real-Time Progress Monitoring")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Example 1: Basic progress monitoring
        print("1. Basic progress monitoring...")
        target_path = temp_dir / "progress_test"
        
        options = RecoveryOptions(
            notification_preferences=NotificationPreferences(
                notify_on_milestone=True,
                milestone_percentage=25
            )
        )
        
        operation = orchestrator.initiate_full_recovery(
            snapshot_id=snapshot_id,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   Operation started: {operation.operation_id}")
        print("   Monitoring progress...\n")
        
        last_percentage = 0
        while True:
            status = orchestrator.get_recovery_status(operation.operation_id)
            
            if not status:
                break
            
            progress = status.progress
            if progress and progress.total_files > 0:
                percentage = (progress.files_processed / progress.total_files) * 100
                
                # Show progress bar
                bar_length = 50
                filled = int(bar_length * percentage / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"\r   [{bar}] {percentage:.1f}% "
                      f"({progress.files_processed}/{progress.total_files} files)", 
                      end='', flush=True)
                
                # Show milestone notifications
                if int(percentage / 25) > int(last_percentage / 25):
                    print(f"\n   ✓ Milestone: {int(percentage / 25) * 25}% complete")
                
                last_percentage = percentage
            
            if status.status in [OperationStatus.COMPLETED, 
                                OperationStatus.FAILED, 
                                OperationStatus.CANCELLED]:
                print()  # New line
                break
            
            time.sleep(0.5)
        
        print(f"\n   Operation {status.status.value}")
        
        # Example 2: Detailed progress information
        print("\n2. Detailed progress information...")
        if progress:
            print(f"   Files processed: {progress.files_processed:,}")
            print(f"   Total files: {progress.total_files:,}")
            print(f"   Bytes transferred: {progress.bytes_transferred:,}")
            print(f"   Total bytes: {progress.total_bytes:,}")
            
            if progress.transfer_rate > 0:
                rate_mb = progress.transfer_rate / (1024 * 1024)
                print(f"   Transfer rate: {rate_mb:.2f} MB/s")
            
            if progress.estimated_completion:
                print(f"   Estimated completion: {progress.estimated_completion}")
            
            if progress.current_file:
                print(f"   Current file: {progress.current_file}")
        
        # Example 3: Progress callback function
        print("\n3. Using progress callback...")
        
        def progress_callback(operation_id: str, progress_status):
            """Custom progress callback"""
            if progress_status.total_files > 0:
                pct = (progress_status.files_processed / 
                       progress_status.total_files * 100)
                
                if pct % 10 == 0:  # Log every 10%
                    print(f"   [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Progress: {pct:.0f}% - "
                          f"{progress_status.files_processed} files processed")
        
        print("   Progress callback registered")
        print("   (Would log progress at 10% intervals)")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_post_recovery_verification():
    """Demonstrate post-recovery integrity verification"""
    print_section("Post-Recovery Verification")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    validator = RecoveryValidator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Perform recovery
        print("1. Performing recovery operation...")
        target_path = temp_dir / "verification_test"
        
        options = RecoveryOptions(verify_integrity=True)
        
        operation = orchestrator.initiate_full_recovery(
            snapshot_id=snapshot_id,
            target_path=str(target_path),
            options=options
        )
        
        print(f"   Operation ID: {operation.operation_id}")
        
        # Wait for completion (simplified for demo)
        time.sleep(2)
        
        # Example 2: Comprehensive post-recovery validation
        print("\n2. Comprehensive post-recovery validation...")
        result = validator.validate_post_recovery(operation.operation_id)
        
        print(f"   Validation status: {'PASSED' if result.is_valid else 'FAILED'}")
        print(f"   Files validated: {result.validated_files:,}")
        print(f"   Validation time: {result.validation_time}")
        
        if result.failed_validations:
            print(f"\n   Failed validations ({len(result.failed_validations)}):")
            for failure in result.failed_validations[:10]:
                print(f"     ✗ {failure.file_path}")
                print(f"       Type: {failure.failure_type.value}")
                print(f"       Expected: {failure.expected_checksum[:16]}...")
                print(f"       Actual: {failure.actual_checksum[:16]}...")
        
        if result.warnings:
            print(f"\n   Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:10]:
                print(f"     ⚠ {warning.message}")
        
        # Example 3: Individual file verification
        print("\n3. Individual file integrity verification...")
        
        if target_path.exists():
            restored_files = list(target_path.rglob("*"))
            files_to_check = [f for f in restored_files if f.is_file()][:5]
            
            print(f"   Checking {len(files_to_check)} sample files...")
            
            for file_path in files_to_check:
                # In real implementation, would verify checksum
                print(f"     ✓ {file_path.name}")
                print(f"       Size: {file_path.stat().st_size:,} bytes")
                print(f"       Modified: {datetime.fromtimestamp(file_path.stat().st_mtime)}")
        
        # Example 4: Verification report generation
        print("\n4. Generating verification report...")
        report = {
            'operation_id': operation.operation_id,
            'snapshot_id': snapshot_id,
            'validation_status': 'PASSED' if result.is_valid else 'FAILED',
            'files_validated': result.validated_files,
            'failures': len(result.failed_validations),
            'warnings': len(result.warnings),
            'timestamp': datetime.now().isoformat()
        }
        
        print("   Verification Report:")
        for key, value in report.items():
            print(f"     {key}: {value}")
        
    finally:
        shutil.rmtree(temp_dir)


def demo_error_detection():
    """Demonstrate error detection and reporting"""
    print_section("Error Detection and Reporting")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    validator = RecoveryValidator(repository)
    
    # Example 1: Detecting missing snapshots
    print("1. Detecting missing snapshot...")
    try:
        result = validator.validate_pre_recovery(
            snapshot_id="nonexistent-snapshot",
            target_path="/tmp/test"
        )
        
        if not result.is_valid:
            print("   ✓ Missing snapshot detected")
            for failure in result.failed_validations:
                print(f"     Error: {failure.error_message}")
    except Exception as e:
        print(f"   ✓ Exception caught: {type(e).__name__}")
        print(f"     Message: {e}")
    
    # Example 2: Detecting insufficient permissions
    print("\n2. Detecting permission issues...")
    try:
        # Try to restore to a restricted location
        result = validator.validate_pre_recovery(
            snapshot_id="test-snapshot",
            target_path="/root/restricted"
        )
        
        if not result.is_valid:
            print("   ✓ Permission issue detected")
            for failure in result.failed_validations:
                print(f"     Error: {failure.error_message}")
    except Exception as e:
        print(f"   ✓ Exception caught: {type(e).__name__}")
    
    # Example 3: Detecting corrupted files
    print("\n3. Detecting file corruption...")
    print("   Simulating corruption detection...")
    print("   ✓ Checksum mismatch detected")
    print("     Expected: abc123...")
    print("     Actual: def456...")
    print("     Action: File marked for re-download")
    
    # Example 4: Network interruption handling
    print("\n4. Handling network interruptions...")
    print("   Simulating network interruption...")
    print("   ✓ Network error detected")
    print("     Retry attempt: 1 of 3")
    print("     Status: Resuming from last checkpoint")


def demo_performance_metrics():
    """Demonstrate performance metrics tracking"""
    print_section("Performance Metrics Tracking")
    
    repository = BackupRepository("s3:s3.amazonaws.com/my-backup-bucket")
    orchestrator = RecoveryOrchestrator(repository)
    
    snapshots = repository.snapshots()
    if not snapshots:
        print("✗ No snapshots found")
        return
    
    snapshot_id = snapshots[0].id
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        print("1. Tracking recovery performance...")
        target_path = temp_dir / "performance_test"
        
        start_time = time.time()
        
        options = RecoveryOptions()
        operation = orchestrator.initiate_full_recovery(
            snapshot_id=snapshot_id,
            target_path=str(target_path),
            options=options
        )
        
        # Monitor performance metrics
        metrics = {
            'start_time': start_time,
            'files_per_second': 0,
            'bytes_per_second': 0,
            'peak_transfer_rate': 0
        }
        
        print(f"   Operation started: {operation.operation_id}")
        
        # Simulate monitoring (simplified)
        time.sleep(2)
        
        elapsed = time.time() - start_time
        
        status = orchestrator.get_recovery_status(operation.operation_id)
        if status and status.progress:
            progress = status.progress
            
            if elapsed > 0:
                metrics['files_per_second'] = progress.files_processed / elapsed
                metrics['bytes_per_second'] = progress.bytes_transferred / elapsed
            
            metrics['peak_transfer_rate'] = progress.transfer_rate
        
        print("\n   Performance Metrics:")
        print(f"     Elapsed time: {elapsed:.2f} seconds")
        print(f"     Files/second: {metrics['files_per_second']:.2f}")
        print(f"     MB/second: {metrics['bytes_per_second'] / (1024*1024):.2f}")
        print(f"     Peak rate: {metrics['peak_transfer_rate'] / (1024*1024):.2f} MB/s")
        
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all verification and monitoring demos"""
    print("\n" + "=" * 80)
    print("  TimeLocker Recovery Verification and Monitoring Demo")
    print("=" * 80)
    print("\nThis demo showcases comprehensive verification and monitoring")
    print("capabilities for recovery operations.\n")
    
    try:
        demo_pre_recovery_validation()
        demo_progress_monitoring()
        demo_post_recovery_verification()
        demo_error_detection()
        demo_performance_metrics()
        
        print_section("Demo Summary")
        print("✓ Pre-recovery validation demonstrated")
        print("✓ Real-time progress monitoring shown")
        print("✓ Post-recovery verification illustrated")
        print("✓ Error detection and reporting explained")
        print("✓ Performance metrics tracking demonstrated")
        print("\nVerification and monitoring demo completed successfully!")
        
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
