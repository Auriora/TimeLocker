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

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from TimeLocker.monitoring import (
    ProgressMonitor,
    ProgressData,
    ProgressState,
    ProgressReport,
    PerformanceMetrics,
    StatusReporter
)


class TestProgressData:
    """Tests for ProgressData class"""
    
    def test_progress_data_creation(self):
        """Test creating ProgressData instance"""
        data = ProgressData(
            job_id="test-job",
            files_processed=50,
            total_files=100,
            bytes_processed=500 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024
        )
        
        assert data.job_id == "test-job"
        assert data.files_processed == 50
        assert data.total_files == 100
        assert data.bytes_processed == 500 * 1024 * 1024
        assert data.total_bytes == 1024 * 1024 * 1024
        assert data.transfer_rate == 10 * 1024 * 1024
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation"""
        # Test with bytes
        data = ProgressData(
            job_id="test",
            bytes_processed=500 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024
        )
        assert data.progress_percentage == 48  # ~48%
        
        # Test with files
        data = ProgressData(
            job_id="test",
            files_processed=25,
            total_files=100
        )
        assert data.progress_percentage == 25
        
        # Test with no totals
        data = ProgressData(job_id="test")
        assert data.progress_percentage is None
    
    def test_estimated_completion(self):
        """Test estimated completion time calculation"""
        data = ProgressData(
            job_id="test",
            bytes_processed=500 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024  # 10 MB/s
        )
        
        eta = data.estimated_completion
        assert eta is not None
        assert eta > datetime.now()


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics class"""
    
    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics instance"""
        start_time = datetime.now()
        metrics = PerformanceMetrics(
            job_id="test-job",
            start_time=start_time
        )
        
        assert metrics.job_id == "test-job"
        assert metrics.start_time == start_time
        assert metrics.peak_transfer_rate == 0.0
        assert metrics.average_transfer_rate == 0.0
    
    def test_duration_calculation(self):
        """Test duration calculation"""
        start_time = datetime.now()
        metrics = PerformanceMetrics(
            job_id="test",
            start_time=start_time
        )
        
        # Without end time (ongoing)
        duration = metrics.duration
        assert duration is not None
        assert duration.total_seconds() >= 0
        
        # With end time
        metrics.end_time = start_time + timedelta(seconds=60)
        duration = metrics.duration
        assert duration.total_seconds() == 60
    
    def test_throughput_calculation(self):
        """Test throughput calculation in MB/s"""
        metrics = PerformanceMetrics(
            job_id="test",
            start_time=datetime.now(),
            average_transfer_rate=10 * 1024 * 1024  # 10 MB/s
        )
        
        assert metrics.throughput_mbps == 10.0


class TestProgressMonitor:
    """Tests for ProgressMonitor class"""
    
    @pytest.fixture
    def status_reporter(self):
        """Create a StatusReporter instance for testing"""
        return StatusReporter()
    
    @pytest.fixture
    def progress_monitor(self, status_reporter):
        """Create a ProgressMonitor instance for testing"""
        return ProgressMonitor(status_reporter=status_reporter)
    
    def test_progress_monitor_initialization(self, progress_monitor):
        """Test ProgressMonitor initialization"""
        assert progress_monitor is not None
        assert progress_monitor._status_reporter is not None
        assert len(progress_monitor._active_monitors) == 0
    
    def test_start_monitoring(self, progress_monitor):
        """Test starting progress monitoring"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(
            job_id=job_id,
            repository_id="test-repo",
            estimated_size=1024 * 1024 * 1024,
            estimated_files=1000
        )
        
        assert job_id in progress_monitor._active_monitors
        assert job_id in progress_monitor._progress_data
        assert job_id in progress_monitor._performance_metrics
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_update_progress(self, progress_monitor):
        """Test updating progress data"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        
        # Update progress
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=50,
            total_files=100,
            bytes_processed=500 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024
        )
        
        progress_monitor.update_progress(job_id, progress_data)
        
        # Verify update
        stored_data = progress_monitor._progress_data[job_id]
        assert stored_data.files_processed == 50
        assert stored_data.bytes_processed == 500 * 1024 * 1024
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_get_progress_report(self, progress_monitor):
        """Test getting progress report"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(
            job_id=job_id,
            estimated_size=1024 * 1024 * 1024,
            estimated_files=100
        )
        
        # Update progress
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=25,
            total_files=100,
            bytes_processed=256 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        # Get report
        report = progress_monitor.get_progress_report(job_id)
        
        assert report is not None
        assert report.job_id == job_id
        assert report.progress_data.files_processed == 25
        assert report.progress_data.progress_percentage == 25
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_stop_monitoring(self, progress_monitor):
        """Test stopping progress monitoring"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        assert job_id in progress_monitor._active_monitors
        
        progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
        assert job_id not in progress_monitor._active_monitors
    
    def test_get_active_jobs(self, progress_monitor):
        """Test getting list of active jobs"""
        job_ids = ["job-1", "job-2", "job-3"]
        
        for job_id in job_ids:
            progress_monitor.start_monitoring(job_id=job_id)
        
        active_jobs = progress_monitor.get_active_jobs()
        assert len(active_jobs) == 3
        assert all(job_id in active_jobs for job_id in job_ids)
        
        # Clean up
        for job_id in job_ids:
            progress_monitor.stop_monitoring(job_id)
    
    def test_progress_callbacks(self, progress_monitor):
        """Test progress callback functionality"""
        job_id = "test-job"
        callback_called = []
        
        def test_callback(report):
            callback_called.append(report.job_id)
        
        # Add callback
        progress_monitor.add_progress_callback(test_callback)
        
        # Start monitoring and update progress
        progress_monitor.start_monitoring(job_id=job_id)
        
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=50,
            total_files=100
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        # Wait for monitoring loop to process
        time.sleep(6)  # Wait for one update interval
        
        # Verify callback was called
        assert len(callback_called) > 0
        assert job_id in callback_called
        
        # Remove callback
        progress_monitor.remove_progress_callback(test_callback)
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_pause_resume_monitoring(self, progress_monitor):
        """Test pausing and resuming monitoring"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        
        # Pause
        result = progress_monitor.pause_monitoring(job_id)
        assert result is True
        assert progress_monitor._active_monitors[job_id]['state'] == ProgressState.PAUSED
        
        # Resume
        result = progress_monitor.resume_monitoring(job_id)
        assert result is True
        assert progress_monitor._active_monitors[job_id]['state'] == ProgressState.RUNNING
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_get_performance_summary(self, progress_monitor):
        """Test getting performance summary"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        
        # Update progress to generate metrics
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=100,
            total_files=100,
            bytes_processed=1024 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=50 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)
        
        # Get summary
        summary = progress_monitor.get_performance_summary(job_id)
        
        assert summary is not None
        assert summary['job_id'] == job_id
        assert summary['total_bytes_transferred'] == 1024 * 1024 * 1024
        assert summary['total_files_processed'] == 100
        assert 'duration_seconds' in summary
        assert 'average_transfer_rate_mbps' in summary
    
    def test_multiple_concurrent_jobs(self, progress_monitor):
        """Test monitoring multiple jobs concurrently"""
        job_ids = ["job-1", "job-2", "job-3"]
        
        # Start all jobs
        for job_id in job_ids:
            progress_monitor.start_monitoring(
                job_id=job_id,
                estimated_size=100 * 1024 * 1024,
                estimated_files=100
            )
        
        # Update progress for all jobs
        for job_id in job_ids:
            progress_data = ProgressData(
                job_id=job_id,
                files_processed=50,
                total_files=100,
                bytes_processed=50 * 1024 * 1024,
                total_bytes=100 * 1024 * 1024
            )
            progress_monitor.update_progress(job_id, progress_data)
        
        # Verify all jobs are active
        active_jobs = progress_monitor.get_active_jobs()
        assert len(active_jobs) == 3
        
        # Get reports for all jobs
        for job_id in job_ids:
            report = progress_monitor.get_progress_report(job_id)
            assert report is not None
            assert report.progress_data.files_processed == 50
        
        # Clean up
        for job_id in job_ids:
            progress_monitor.stop_monitoring(job_id)
    
    def test_progress_report_to_dict(self, progress_monitor):
        """Test converting progress report to dictionary"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=50,
            total_files=100,
            bytes_processed=500 * 1024 * 1024,
            total_bytes=1024 * 1024 * 1024,
            transfer_rate=10 * 1024 * 1024
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        report = progress_monitor.get_progress_report(job_id)
        report_dict = report.to_dict()
        
        assert isinstance(report_dict, dict)
        assert report_dict['job_id'] == job_id
        assert report_dict['progress_percentage'] == 48
        assert 'transfer_rate_mbps' in report_dict
        assert 'performance' in report_dict
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
    
    def test_integration_with_status_reporter(self, progress_monitor, status_reporter):
        """Test integration with StatusReporter"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(
            job_id=job_id,
            repository_id="test-repo"
        )
        
        # Verify operation was started in StatusReporter
        status = status_reporter.get_operation_status(job_id)
        assert status is not None
        assert status.operation_id == job_id
        
        # Update progress
        progress_data = ProgressData(
            job_id=job_id,
            files_processed=50,
            total_files=100
        )
        progress_monitor.update_progress(job_id, progress_data)
        
        # Wait for update to propagate
        time.sleep(6)
        
        # Verify status was updated
        status = status_reporter.get_operation_status(job_id)
        if status:  # May be None if operation completed
            assert status.files_processed == 50
        
        # Clean up
        progress_monitor.stop_monitoring(job_id, ProgressState.COMPLETED)


class TestProgressMonitorEdgeCases:
    """Tests for edge cases and error handling"""
    
    @pytest.fixture
    def progress_monitor(self):
        """Create a ProgressMonitor instance for testing"""
        return ProgressMonitor()
    
    def test_update_progress_for_nonexistent_job(self, progress_monitor):
        """Test updating progress for a job that doesn't exist"""
        progress_data = ProgressData(
            job_id="nonexistent-job",
            files_processed=50
        )
        
        # Should not raise an error, just log a warning
        progress_monitor.update_progress("nonexistent-job", progress_data)
    
    def test_stop_monitoring_nonexistent_job(self, progress_monitor):
        """Test stopping monitoring for a job that doesn't exist"""
        # Should not raise an error, just log a warning
        progress_monitor.stop_monitoring("nonexistent-job")
    
    def test_get_progress_report_nonexistent_job(self, progress_monitor):
        """Test getting progress report for nonexistent job"""
        report = progress_monitor.get_progress_report("nonexistent-job")
        assert report is None
    
    def test_pause_nonexistent_job(self, progress_monitor):
        """Test pausing a nonexistent job"""
        result = progress_monitor.pause_monitoring("nonexistent-job")
        assert result is False
    
    def test_resume_nonexistent_job(self, progress_monitor):
        """Test resuming a nonexistent job"""
        result = progress_monitor.resume_monitoring("nonexistent-job")
        assert result is False
    
    def test_get_performance_summary_nonexistent_job(self, progress_monitor):
        """Test getting performance summary for nonexistent job"""
        summary = progress_monitor.get_performance_summary("nonexistent-job")
        assert summary is None
    
    def test_start_monitoring_duplicate_job(self, progress_monitor):
        """Test starting monitoring for a job that's already being monitored"""
        job_id = "test-job"
        
        progress_monitor.start_monitoring(job_id=job_id)
        
        # Try to start again - should log warning but not fail
        progress_monitor.start_monitoring(job_id=job_id)
        
        # Clean up
        progress_monitor.stop_monitoring(job_id)
