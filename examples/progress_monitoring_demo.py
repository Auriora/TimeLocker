#!/usr/bin/env python3
"""
Progress Monitoring Demo

Demonstrates the real-time progress monitoring capabilities for backup operations.
Shows how to:
- Start progress monitoring with 5-second update intervals
- Update progress data during backup operations
- Collect performance metrics
- Generate progress reports
- Integrate with StatusReporter for unified reporting
"""

import time
import random
from pathlib import Path
from datetime import datetime

from TimeLocker.monitoring import (
    ProgressMonitor,
    ProgressData,
    ProgressState,
    StatusReporter
)


def simulate_backup_operation(progress_monitor: ProgressMonitor, job_id: str):
    """
    Simulate a backup operation with progress updates.
    
    Args:
        progress_monitor: ProgressMonitor instance
        job_id: Job identifier
    """
    print(f"\n{'='*60}")
    print(f"Simulating backup operation: {job_id}")
    print(f"{'='*60}\n")
    
    # Simulate backup parameters
    total_files = 1000
    total_bytes = 5 * 1024 * 1024 * 1024  # 5 GB
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=job_id,
        repository_id="demo-repo",
        estimated_size=total_bytes,
        estimated_files=total_files,
        metadata={'backup_type': 'full', 'compression': 'auto'}
    )
    
    print(f"✓ Progress monitoring started for job: {job_id}")
    print(f"  Estimated: {total_files} files, {total_bytes / (1024**3):.2f} GB\n")
    
    # Simulate backup progress
    files_processed = 0
    bytes_processed = 0
    
    # Simulate processing files in batches
    batch_size = 50
    batches = total_files // batch_size
    
    for batch in range(batches):
        # Simulate processing a batch of files
        files_in_batch = min(batch_size, total_files - files_processed)
        bytes_in_batch = random.randint(1024 * 1024, 10 * 1024 * 1024)  # 1-10 MB per batch
        
        files_processed += files_in_batch
        bytes_processed += bytes_in_batch
        
        # Calculate transfer rate (simulate varying speeds)
        transfer_rate = random.uniform(5 * 1024 * 1024, 50 * 1024 * 1024)  # 5-50 MB/s
        
        # Create progress data
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=files_processed,
            total_files=total_files,
            bytes_processed=bytes_processed,
            total_bytes=total_bytes,
            current_file=f"/path/to/file_{files_processed}.dat",
            transfer_rate=transfer_rate
        )
        
        # Update progress
        progress_monitor.update_progress(job_id, progress_data)
        
        # Print progress update
        if batch % 4 == 0:  # Print every 4 batches
            report = progress_monitor.get_progress_report(job_id)
            if report:
                print(f"Progress Update:")
                print(f"  Files: {report.progress_data.files_processed}/{report.progress_data.total_files}")
                print(f"  Bytes: {report.progress_data.bytes_processed / (1024**3):.2f}/"
                      f"{report.progress_data.total_bytes / (1024**3):.2f} GB")
                print(f"  Progress: {report.progress_data.progress_percentage}%")
                print(f"  Transfer Rate: {report.progress_data.transfer_rate / (1024**2):.2f} MB/s")
                if report.estimated_completion:
                    print(f"  ETA: {report.estimated_completion.strftime('%H:%M:%S')}")
                print()
        
        # Simulate processing time
        time.sleep(0.1)
    
    # Complete monitoring
    progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
    print(f"✓ Backup operation completed: {job_id}\n")


def demonstrate_progress_callbacks(progress_monitor: ProgressMonitor):
    """
    Demonstrate progress callbacks for real-time notifications.
    
    Args:
        progress_monitor: ProgressMonitor instance
    """
    print(f"\n{'='*60}")
    print("Demonstrating Progress Callbacks")
    print(f"{'='*60}\n")
    
    # Define a callback function
    def progress_callback(report):
        """Callback to handle progress updates"""
        if report.progress_data.progress_percentage and report.progress_data.progress_percentage % 25 == 0:
            print(f"[CALLBACK] Job {report.job_id}: {report.progress_data.progress_percentage}% complete")
    
    # Add callback
    progress_monitor.add_progress_callback(progress_callback)
    print("✓ Progress callback registered\n")
    
    # Simulate a quick backup
    job_id = "callback-demo-job"
    progress_monitor.start_monitoring(
        job_id=job_id,
        estimated_size=100 * 1024 * 1024,  # 100 MB
        estimated_files=100
    )
    
    # Simulate progress in 25% increments
    for progress in [25, 50, 75, 100]:
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=progress,
            total_files=100,
            bytes_processed=progress * 1024 * 1024,
            total_bytes=100 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024  # 10 MB/s
        )
        progress_monitor.update_progress(job_id, progress_data)
        time.sleep(0.5)
    
    progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
    
    # Remove callback
    progress_monitor.remove_progress_callback(progress_callback)
    print("\n✓ Progress callback demonstration complete\n")


def demonstrate_performance_metrics(progress_monitor: ProgressMonitor):
    """
    Demonstrate performance metrics collection.
    
    Args:
        progress_monitor: ProgressMonitor instance
    """
    print(f"\n{'='*60}")
    print("Demonstrating Performance Metrics Collection")
    print(f"{'='*60}\n")
    
    job_id = "performance-demo-job"
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=job_id,
        estimated_size=1024 * 1024 * 1024,  # 1 GB
        estimated_files=500
    )
    
    # Simulate backup with varying transfer rates
    total_bytes = 1024 * 1024 * 1024
    bytes_processed = 0
    files_processed = 0
    
    print("Simulating backup with varying transfer rates...\n")
    
    while bytes_processed < total_bytes:
        # Simulate varying transfer rates
        transfer_rate = random.uniform(10 * 1024 * 1024, 100 * 1024 * 1024)  # 10-100 MB/s
        batch_size = min(50 * 1024 * 1024, total_bytes - bytes_processed)  # 50 MB batches
        
        bytes_processed += batch_size
        files_processed += 25
        
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=files_processed,
            total_files=500,
            bytes_processed=bytes_processed,
            total_bytes=total_bytes,
            transfer_rate=transfer_rate
        )
        
        progress_monitor.update_progress(job_id, progress_data)
        time.sleep(0.2)
    
    # Stop monitoring and get performance summary
    progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
    
    # Get performance summary
    summary = progress_monitor.get_performance_summary(job_id)
    if summary:
        print("Performance Summary:")
        print(f"  Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"  Total Bytes: {summary['total_bytes_transferred'] / (1024**3):.2f} GB")
        print(f"  Total Files: {summary['total_files_processed']}")
        print(f"  Peak Transfer Rate: {summary['peak_transfer_rate_mbps']:.2f} MB/s")
        print(f"  Average Transfer Rate: {summary['average_transfer_rate_mbps']:.2f} MB/s")
        print(f"  Throughput: {summary['throughput_mbps']:.2f} MB/s")
        print()


def demonstrate_multiple_concurrent_jobs(progress_monitor: ProgressMonitor):
    """
    Demonstrate monitoring multiple concurrent backup jobs.
    
    Args:
        progress_monitor: ProgressMonitor instance
    """
    print(f"\n{'='*60}")
    print("Demonstrating Multiple Concurrent Jobs")
    print(f"{'='*60}\n")
    
    # Start multiple jobs
    jobs = [
        ("job-1", 100 * 1024 * 1024, 100),  # 100 MB, 100 files
        ("job-2", 200 * 1024 * 1024, 200),  # 200 MB, 200 files
        ("job-3", 150 * 1024 * 1024, 150),  # 150 MB, 150 files
    ]
    
    for job_id, size, files in jobs:
        progress_monitor.start_monitoring(
            job_id=job_id,
            estimated_size=size,
            estimated_files=files
        )
        print(f"✓ Started monitoring: {job_id}")
    
    print(f"\nActive jobs: {progress_monitor.get_active_jobs()}\n")
    
    # Simulate progress for all jobs
    for i in range(10):
        for job_id, size, files in jobs:
            progress = (i + 1) * 10  # 10%, 20%, ..., 100%
            progress_data = ProgressData(
                job_id=job_id,
                files_processed=int(files * progress / 100),
                total_files=files,
                bytes_processed=int(size * progress / 100),
                total_bytes=size,
                transfer_rate=random.uniform(5 * 1024 * 1024, 20 * 1024 * 1024)
            )
            progress_monitor.update_progress(job_id, progress_data)
        
        time.sleep(0.3)
    
    # Stop all jobs
    for job_id, _, _ in jobs:
        progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
        print(f"✓ Completed: {job_id}")
    
    print()


def demonstrate_pause_resume(progress_monitor: ProgressMonitor):
    """
    Demonstrate pausing and resuming progress monitoring.
    
    Args:
        progress_monitor: ProgressMonitor instance
    """
    print(f"\n{'='*60}")
    print("Demonstrating Pause/Resume Functionality")
    print(f"{'='*60}\n")
    
    job_id = "pause-resume-demo"
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=job_id,
        estimated_size=500 * 1024 * 1024,
        estimated_files=250
    )
    
    print(f"✓ Started monitoring: {job_id}\n")
    
    # Simulate progress to 30%
    for progress in range(10, 40, 10):
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=int(250 * progress / 100),
            total_files=250,
            bytes_processed=int(500 * 1024 * 1024 * progress / 100),
            total_bytes=500 * 1024 * 1024,
            transfer_rate=20 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        print(f"Progress: {progress}%")
        time.sleep(0.3)
    
    # Pause monitoring
    print("\n⏸ Pausing monitoring...")
    progress_monitor.pause_monitoring(job_id)
    time.sleep(1)
    
    # Resume monitoring
    print("▶ Resuming monitoring...\n")
    progress_monitor.resume_monitoring(job_id)
    
    # Continue to 100%
    for progress in range(40, 110, 10):
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=min(250, int(250 * progress / 100)),
            total_files=250,
            bytes_processed=min(500 * 1024 * 1024, int(500 * 1024 * 1024 * progress / 100)),
            total_bytes=500 * 1024 * 1024,
            transfer_rate=20 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        print(f"Progress: {min(100, progress)}%")
        time.sleep(0.3)
    
    progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
    print(f"\n✓ Completed: {job_id}\n")


def demonstrate_integration_with_status_reporter():
    """
    Demonstrate integration between ProgressMonitor and StatusReporter.
    """
    print(f"\n{'='*60}")
    print("Demonstrating StatusReporter Integration")
    print(f"{'='*60}\n")
    
    # Create StatusReporter and ProgressMonitor
    status_reporter = StatusReporter()
    progress_monitor = ProgressMonitor(status_reporter=status_reporter)
    
    job_id = "integration-demo"
    
    # Start monitoring
    progress_monitor.start_monitoring(
        job_id=job_id,
        repository_id="demo-repo",
        estimated_size=200 * 1024 * 1024,
        estimated_files=100
    )
    
    print(f"✓ Started monitoring with StatusReporter integration\n")
    
    # Simulate progress
    for progress in range(0, 110, 20):
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=min(100, progress),
            total_files=100,
            bytes_processed=min(200 * 1024 * 1024, int(200 * 1024 * 1024 * progress / 100)),
            total_bytes=200 * 1024 * 1024,
            transfer_rate=15 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        # Get status from StatusReporter
        status = status_reporter.get_operation_status(job_id)
        if status:
            print(f"StatusReporter - Progress: {status.progress_percentage}%, "
                  f"Files: {status.files_processed}/{status.total_files}")
        
        time.sleep(0.5)
    
    progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
    
    # Get operation history from StatusReporter
    history = status_reporter.get_operation_history(days=1, operation_type="backup")
    print(f"\n✓ Operation history entries: {len(history)}\n")


def main():
    """Main demonstration function"""
    print("\n" + "="*60)
    print("TimeLocker Progress Monitoring Demo")
    print("="*60)
    
    # Create ProgressMonitor instance
    progress_monitor = ProgressMonitor()
    
    # Run demonstrations
    try:
        # 1. Basic backup operation simulation
        simulate_backup_operation(progress_monitor, "demo-backup-job-1")
        
        # 2. Progress callbacks
        demonstrate_progress_callbacks(progress_monitor)
        
        # 3. Performance metrics
        demonstrate_performance_metrics(progress_monitor)
        
        # 4. Multiple concurrent jobs
        demonstrate_multiple_concurrent_jobs(progress_monitor)
        
        # 5. Pause/Resume functionality
        demonstrate_pause_resume(progress_monitor)
        
        # 6. StatusReporter integration
        demonstrate_integration_with_status_reporter()
        
        print("="*60)
        print("Demo completed successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
