"""
Recovery Progress Monitoring Demo

This example demonstrates the progress monitoring and notification capabilities
for recovery operations in TimeLocker.
"""

import time
from datetime import datetime
from pathlib import Path

from TimeLocker.monitoring import (
    ProgressMonitor,
    ProgressData,
    ProgressReport,
    ProgressState,
    RecoveryProgressNotifier,
    NotificationService,
    StatusReporter
)


def progress_callback(report: ProgressReport):
    """Callback function for progress updates"""
    print(f"\n=== Progress Update ===")
    print(f"Operation: {report.job_id}")
    print(f"State: {report.state.value}")
    print(f"Progress: {report.progress_data.progress_percentage:.1f}%")
    print(f"Files: {report.progress_data.files_processed}/{report.progress_data.total_files}")
    print(f"Bytes: {report.progress_data.bytes_processed}/{report.progress_data.total_bytes}")
    if report.estimated_completion:
        print(f"ETA: {report.estimated_completion.strftime('%H:%M:%S')}")
    print("=" * 40)


def demo_basic_progress_monitoring():
    """Demonstrate basic progress monitoring for recovery operations"""
    print("\n" + "=" * 60)
    print("Demo 1: Basic Progress Monitoring")
    print("=" * 60)
    
    # Initialize components
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter)
    
    # Start monitoring a recovery operation
    operation_id = "recovery-001"
    snapshot_id = "snapshot-abc123"
    
    print(f"\nStarting monitoring for operation: {operation_id}")
    
    progress_monitor.start_monitoring(
        job_id=operation_id,
        repository_id=snapshot_id,
        estimated_size=1024 * 1024 * 1024,  # 1 GB
        estimated_files=1000,
        metadata={
            'recovery_type': 'full',
            'target_path': '/restore/path'
        }
    )
    
    # Simulate progress updates
    for i in range(5):
        time.sleep(1)
        
        # Update progress
        progress_data = ProgressData(
            job_id=operation_id,
            files_processed=i * 200 + 100,
            total_files=1000,
            bytes_processed=i * 200 * 1024 * 1024 + 100 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            current_file=f"/path/to/file_{i}.txt",
            transfer_rate=10 * 1024 * 1024  # 10 MB/s
        )
        
        progress_monitor.update_progress(operation_id, progress_data)
        
        # Get current status
        status = progress_monitor.get_progress_status(operation_id)
        if status:
            print(f"Progress: {status.progress_percentage:.1f}% - {status.current_file}")
    
    # Get estimated completion time
    eta = progress_monitor.estimate_completion_time(operation_id)
    if eta:
        print(f"\nEstimated completion: {eta.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Stop monitoring
    progress_monitor.stop_monitoring(operation_id, ProgressState.COMPLETED)
    print(f"\nMonitoring stopped for operation: {operation_id}")


def demo_progress_callbacks():
    """Demonstrate progress callbacks for real-time updates"""
    print("\n" + "=" * 60)
    print("Demo 2: Progress Callbacks")
    print("=" * 60)
    
    # Initialize components
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter)
    
    # Register a callback for a specific operation
    operation_id = "recovery-002"
    
    print(f"\nRegistering callback for operation: {operation_id}")
    progress_monitor.register_progress_callback(operation_id, progress_callback)
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=operation_id,
        repository_id="snapshot-xyz789",
        estimated_size=500 * 1024 * 1024,  # 500 MB
        estimated_files=500
    )
    
    # Simulate progress updates (callbacks will be triggered)
    for i in range(3):
        time.sleep(2)
        
        progress_data = ProgressData(
            job_id=operation_id,
            files_processed=(i + 1) * 150,
            total_files=500,
            bytes_processed=(i + 1) * 150 * 1024 * 1024,
            total_bytes=500 * 1024 * 1024,
            current_file=f"/restore/file_{i}.dat",
            transfer_rate=15 * 1024 * 1024  # 15 MB/s
        )
        
        progress_monitor.update_progress(operation_id, progress_data)
    
    # Stop monitoring
    progress_monitor.stop_monitoring(operation_id, ProgressState.COMPLETED)
    print(f"\nCallback demo completed")


def demo_recovery_notifications():
    """Demonstrate recovery-specific notifications"""
    print("\n" + "=" * 60)
    print("Demo 3: Recovery Progress Notifications")
    print("=" * 60)
    
    # Initialize components
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter)
    
    # Create recovery progress notifier
    notifier = RecoveryProgressNotifier(
        notification_service,
        status_reporter,
        progress_monitor
    )
    
    # Set custom milestones
    notifier.set_milestone_percentages([10, 25, 50, 75, 90, 100])
    
    operation_id = "recovery-003"
    snapshot_id = "snapshot-milestone"
    
    # Notify recovery started
    print(f"\nNotifying recovery started...")
    notifier.notify_recovery_started(
        operation_id=operation_id,
        snapshot_id=snapshot_id,
        target_path="/restore/milestone",
        recovery_type="selective"
    )
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=operation_id,
        repository_id=snapshot_id,
        estimated_size=2 * 1024 * 1024 * 1024,  # 2 GB
        estimated_files=2000
    )
    
    # Simulate progress with milestone notifications
    for progress_pct in [0, 15, 30, 55, 80, 95, 100]:
        time.sleep(0.5)
        
        files_processed = int(2000 * progress_pct / 100)
        bytes_processed = int(2 * 1024 * 1024 * 1024 * progress_pct / 100)
        
        progress_data = ProgressData(
            job_id=operation_id,
            files_processed=files_processed,
            total_files=2000,
            bytes_processed=bytes_processed,
            total_bytes=2 * 1024 * 1024 * 1024,
            current_file=f"/restore/file_{files_processed}.txt",
            transfer_rate=20 * 1024 * 1024  # 20 MB/s
        )
        
        progress_monitor.update_progress(operation_id, progress_data)
        
        # Get progress report and notify
        report = progress_monitor.get_progress_report(operation_id)
        if report:
            notifier.notify_recovery_progress(operation_id, report)
    
    # Notify completion
    print(f"\nNotifying recovery completed...")
    notifier.notify_recovery_completed(
        operation_id=operation_id,
        snapshot_id=snapshot_id,
        files_restored=2000,
        bytes_restored=2 * 1024 * 1024 * 1024,
        duration_seconds=120.5,
        validation_passed=True
    )
    
    # Stop monitoring
    progress_monitor.stop_monitoring(operation_id, ProgressState.COMPLETED)
    
    # Generate final report
    print(f"\nGenerating final progress report...")
    final_report = notifier.generate_progress_report(operation_id)
    if final_report:
        print(f"Final Report:")
        print(f"  - State: {final_report['state']}")
        print(f"  - Progress: {final_report['progress_percentage']}%")
        print(f"  - Files: {final_report['files_processed']}/{final_report['total_files']}")
        print(f"  - Duration: {final_report['duration_seconds']:.1f}s")
        print(f"  - Milestones reached: {final_report['milestones_reached']}")


def demo_error_notifications():
    """Demonstrate error and warning notifications"""
    print("\n" + "=" * 60)
    print("Demo 4: Error and Warning Notifications")
    print("=" * 60)
    
    # Initialize components
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter)
    
    notifier = RecoveryProgressNotifier(
        notification_service,
        status_reporter,
        progress_monitor
    )
    
    operation_id = "recovery-004"
    
    # Notify warning
    print(f"\nSending warning notification...")
    notifier.notify_recovery_warning(
        operation_id=operation_id,
        warning_message="Some files were skipped due to permissions",
        warning_type="permission_warning",
        context={'skipped_files': 5}
    )
    
    # Notify recoverable error
    print(f"\nSending recoverable error notification...")
    notifier.notify_recovery_error(
        operation_id=operation_id,
        error_message="Network timeout during file transfer",
        error_type="network_error",
        failed_files=["/path/to/file1.txt", "/path/to/file2.txt"],
        is_recoverable=True
    )
    
    # Notify critical error
    print(f"\nSending critical error notification...")
    notifier.notify_recovery_error(
        operation_id=operation_id,
        error_message="Snapshot corruption detected",
        error_type="corruption_error",
        failed_files=["/path/to/corrupted.dat"],
        is_recoverable=False
    )


def demo_milestone_logging():
    """Demonstrate milestone logging for detailed tracking"""
    print("\n" + "=" * 60)
    print("Demo 5: Milestone Logging")
    print("=" * 60)
    
    # Initialize components
    notification_service = NotificationService()
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter)
    
    notifier = RecoveryProgressNotifier(
        notification_service,
        status_reporter,
        progress_monitor
    )
    
    operation_id = "recovery-005"
    
    # Log various milestones
    milestones = [
        ("validation_started", {"files_to_validate": 1000}),
        ("first_file_restored", {"file_path": "/restore/first.txt"}),
        ("halfway_complete", {"files_restored": 500, "time_elapsed": 60}),
        ("validation_completed", {"validation_passed": True}),
        ("cleanup_started", {"temp_files": 10})
    ]
    
    for milestone_name, milestone_data in milestones:
        print(f"\nLogging milestone: {milestone_name}")
        notifier.log_recovery_milestone(
            operation_id=operation_id,
            milestone_name=milestone_name,
            milestone_data=milestone_data
        )
        time.sleep(0.5)


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("Recovery Progress Monitoring Demo")
    print("=" * 60)
    
    try:
        demo_basic_progress_monitoring()
        demo_progress_callbacks()
        demo_recovery_notifications()
        demo_error_notifications()
        demo_milestone_logging()
        
        print("\n" + "=" * 60)
        print("All demos completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running demos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
