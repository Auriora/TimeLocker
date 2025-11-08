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

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable, List
from enum import Enum

from .status_reporter import StatusReporter, OperationStatus, StatusLevel

logger = logging.getLogger(__name__)


class ProgressState(Enum):
    """Progress monitoring states"""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressData:
    """Real-time progress data for backup operations"""
    job_id: str
    files_processed: int = 0
    total_files: Optional[int] = None
    bytes_processed: int = 0
    total_bytes: Optional[int] = None
    current_file: Optional[str] = None
    transfer_rate: float = 0.0  # bytes per second
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> Optional[int]:
        """Calculate progress percentage based on bytes or files"""
        if self.total_bytes and self.total_bytes > 0:
            return min(100, int((self.bytes_processed / self.total_bytes) * 100))
        elif self.total_files and self.total_files > 0:
            return min(100, int((self.files_processed / self.total_files) * 100))
        return None
    
    @property
    def estimated_completion(self) -> Optional[datetime]:
        """Estimate completion time based on current transfer rate"""
        if self.transfer_rate > 0 and self.total_bytes:
            remaining_bytes = self.total_bytes - self.bytes_processed
            if remaining_bytes > 0:
                remaining_seconds = remaining_bytes / self.transfer_rate
                return datetime.now() + timedelta(seconds=remaining_seconds)
        return None


@dataclass
class PerformanceMetrics:
    """Performance metrics collected during backup operations"""
    job_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    peak_transfer_rate: float = 0.0  # bytes per second
    average_transfer_rate: float = 0.0  # bytes per second
    total_bytes_transferred: int = 0
    total_files_processed: int = 0
    cpu_usage_samples: List[float] = field(default_factory=list)
    memory_usage_samples: List[int] = field(default_factory=list)
    disk_io_samples: List[Dict[str, int]] = field(default_factory=list)
    network_io_samples: List[Dict[str, int]] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate operation duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return datetime.now() - self.start_time
    
    @property
    def throughput_mbps(self) -> float:
        """Calculate throughput in MB/s"""
        if self.average_transfer_rate > 0:
            return self.average_transfer_rate / (1024 * 1024)
        return 0.0


@dataclass
class ProgressReport:
    """Comprehensive progress report for a backup job"""
    job_id: str
    state: ProgressState
    progress_data: ProgressData
    performance_metrics: PerformanceMetrics
    start_time: datetime
    last_update: datetime
    estimated_completion: Optional[datetime] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'job_id': self.job_id,
            'state': self.state.value,
            'progress_percentage': self.progress_data.progress_percentage,
            'files_processed': self.progress_data.files_processed,
            'total_files': self.progress_data.total_files,
            'bytes_processed': self.progress_data.bytes_processed,
            'total_bytes': self.progress_data.total_bytes,
            'transfer_rate_mbps': self.progress_data.transfer_rate / (1024 * 1024),
            'current_file': self.progress_data.current_file,
            'start_time': self.start_time.isoformat(),
            'last_update': self.last_update.isoformat(),
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'duration_seconds': (self.last_update - self.start_time).total_seconds(),
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors),
            'performance': {
                'peak_transfer_rate_mbps': self.performance_metrics.peak_transfer_rate / (1024 * 1024),
                'average_transfer_rate_mbps': self.performance_metrics.average_transfer_rate / (1024 * 1024),
                'throughput_mbps': self.performance_metrics.throughput_mbps
            }
        }


class ProgressMonitor:
    """
    Real-time progress monitoring for backup operations.
    
    Provides 5-second update intervals, progress estimation, and performance
    metrics collection. Integrates with StatusReporter for unified reporting.
    """
    
    UPDATE_INTERVAL_SECONDS = 5.0
    
    def __init__(self, status_reporter: Optional[StatusReporter] = None):
        """
        Initialize progress monitor.
        
        Args:
            status_reporter: Optional StatusReporter for unified progress reporting
        """
        self._status_reporter = status_reporter or StatusReporter()
        
        # Active monitoring sessions
        self._active_monitors: Dict[str, Dict[str, Any]] = {}
        self._monitor_threads: Dict[str, threading.Thread] = {}
        self._monitor_locks: Dict[str, threading.Lock] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        
        # Progress data storage
        self._progress_data: Dict[str, ProgressData] = {}
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
        
        # Progress update callbacks
        self._progress_callbacks: List[Callable[[ProgressReport], None]] = []
        
        # Global lock for thread-safe operations
        self._global_lock = threading.Lock()
        
        logger.debug("ProgressMonitor initialized")
    
    def add_progress_callback(self, callback: Callable[[ProgressReport], None]) -> None:
        """
        Add a callback to be notified of progress updates.
        
        Args:
            callback: Function to call with ProgressReport on updates
        """
        with self._global_lock:
            self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[ProgressReport], None]) -> None:
        """
        Remove a progress callback.
        
        Args:
            callback: Callback function to remove
        """
        with self._global_lock:
            if callback in self._progress_callbacks:
                self._progress_callbacks.remove(callback)
    
    def start_monitoring(self, 
                        job_id: str,
                        repository_id: Optional[str] = None,
                        estimated_size: Optional[int] = None,
                        estimated_files: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Start monitoring progress for a backup job.
        
        Args:
            job_id: Unique identifier for the backup job
            repository_id: Optional repository identifier
            estimated_size: Optional estimated total size in bytes
            estimated_files: Optional estimated total file count
            metadata: Optional additional metadata
        """
        logger.info(f"Starting progress monitoring for job: {job_id}")
        
        with self._global_lock:
            if job_id in self._active_monitors:
                logger.warning(f"Progress monitoring already active for job: {job_id}")
                return
            
            # Initialize progress data
            self._progress_data[job_id] = ProgressData(
                job_id=job_id,
                total_bytes=estimated_size,
                total_files=estimated_files,
                metadata=metadata or {}
            )
            
            # Initialize performance metrics
            self._performance_metrics[job_id] = PerformanceMetrics(
                job_id=job_id,
                start_time=datetime.now()
            )
            
            # Create monitoring session
            self._active_monitors[job_id] = {
                'repository_id': repository_id,
                'start_time': datetime.now(),
                'state': ProgressState.INITIALIZING,
                'last_update': datetime.now()
            }
            
            # Create thread synchronization objects
            self._monitor_locks[job_id] = threading.Lock()
            self._stop_events[job_id] = threading.Event()
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                args=(job_id,),
                daemon=True,
                name=f"ProgressMonitor-{job_id}"
            )
            self._monitor_threads[job_id] = monitor_thread
            monitor_thread.start()
            
            # Report to StatusReporter
            self._status_reporter.start_operation(
                operation_id=job_id,
                operation_type="backup",
                repository_id=repository_id,
                metadata=metadata
            )
            
            logger.info(f"Progress monitoring started for job: {job_id}")
    
    def update_progress(self, job_id: str, progress_data: ProgressData) -> None:
        """
        Update progress information for active job.
        
        Args:
            job_id: Job identifier
            progress_data: Updated progress data
        """
        if job_id not in self._active_monitors:
            logger.warning(f"Cannot update progress for inactive job: {job_id}")
            return
        
        with self._monitor_locks[job_id]:
            # Update progress data
            self._progress_data[job_id] = progress_data
            self._active_monitors[job_id]['last_update'] = datetime.now()
            self._active_monitors[job_id]['state'] = ProgressState.RUNNING
            
            # Update performance metrics
            metrics = self._performance_metrics[job_id]
            metrics.total_bytes_transferred = progress_data.bytes_processed
            metrics.total_files_processed = progress_data.files_processed
            
            # Update transfer rate metrics
            if progress_data.transfer_rate > metrics.peak_transfer_rate:
                metrics.peak_transfer_rate = progress_data.transfer_rate
            
            # Calculate average transfer rate
            duration = (datetime.now() - metrics.start_time).total_seconds()
            if duration > 0:
                metrics.average_transfer_rate = progress_data.bytes_processed / duration
    
    def stop_monitoring(self, 
                       job_id: str,
                       final_state: ProgressState = ProgressState.COMPLETED,
                       error_message: Optional[str] = None) -> None:
        """
        Stop monitoring progress for a backup job.
        
        Args:
            job_id: Job identifier
            final_state: Final state of the job
            error_message: Optional error message if job failed
        """
        logger.info(f"Stopping progress monitoring for job: {job_id}, state: {final_state.value}")
        
        if job_id not in self._active_monitors:
            logger.warning(f"Cannot stop monitoring for inactive job: {job_id}")
            return
        
        # Signal monitoring thread to stop
        if job_id in self._stop_events:
            self._stop_events[job_id].set()
        
        # Wait for monitoring thread to finish
        if job_id in self._monitor_threads:
            thread = self._monitor_threads[job_id]
            thread.join(timeout=2.0)
        
        with self._global_lock:
            # Update final state
            self._active_monitors[job_id]['state'] = final_state
            
            # Finalize performance metrics
            if job_id in self._performance_metrics:
                self._performance_metrics[job_id].end_time = datetime.now()
            
            # Report final status to StatusReporter
            status_level = self._map_state_to_status_level(final_state)
            message = error_message if error_message else f"Job {final_state.value}"
            
            self._status_reporter.complete_operation(
                operation_id=job_id,
                status=status_level,
                message=message
            )
            
            # Clean up
            self._active_monitors.pop(job_id, None)
            self._monitor_threads.pop(job_id, None)
            self._monitor_locks.pop(job_id, None)
            self._stop_events.pop(job_id, None)
            
            logger.info(f"Progress monitoring stopped for job: {job_id}")
    
    def get_progress_report(self, job_id: str) -> Optional[ProgressReport]:
        """
        Get comprehensive progress report for job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            ProgressReport if job is being monitored, None otherwise
        """
        if job_id not in self._active_monitors:
            return None
        
        with self._monitor_locks.get(job_id, threading.Lock()):
            monitor_info = self._active_monitors[job_id]
            progress_data = self._progress_data.get(job_id)
            performance_metrics = self._performance_metrics.get(job_id)
            
            if not progress_data or not performance_metrics:
                return None
            
            return ProgressReport(
                job_id=job_id,
                state=monitor_info['state'],
                progress_data=progress_data,
                performance_metrics=performance_metrics,
                start_time=monitor_info['start_time'],
                last_update=monitor_info['last_update'],
                estimated_completion=progress_data.estimated_completion
            )
    
    def get_active_jobs(self) -> List[str]:
        """
        Get list of jobs currently being monitored.
        
        Returns:
            List of job IDs
        """
        with self._global_lock:
            return list(self._active_monitors.keys())
    
    def _monitoring_loop(self, job_id: str) -> None:
        """
        Background monitoring loop for a job.
        
        Runs every UPDATE_INTERVAL_SECONDS to report progress and collect metrics.
        
        Args:
            job_id: Job identifier
        """
        logger.debug(f"Monitoring loop started for job: {job_id}")
        
        stop_event = self._stop_events[job_id]
        
        while not stop_event.is_set():
            try:
                # Generate and report progress
                report = self.get_progress_report(job_id)
                if report:
                    self._report_progress(report)
                
                # Collect performance metrics
                self._collect_performance_metrics(job_id)
                
                # Wait for next update interval or stop signal
                stop_event.wait(timeout=self.UPDATE_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop for job {job_id}: {e}")
                # Continue monitoring despite errors
        
        logger.debug(f"Monitoring loop stopped for job: {job_id}")
    
    def _report_progress(self, report: ProgressReport) -> None:
        """
        Report progress to StatusReporter and callbacks.
        
        Args:
            report: Progress report to send
        """
        try:
            # Update StatusReporter
            self._status_reporter.update_operation(
                operation_id=report.job_id,
                status=self._map_state_to_status_level(report.state),
                message=f"Processing: {report.progress_data.current_file or 'files'}",
                progress_percentage=report.progress_data.progress_percentage,
                files_processed=report.progress_data.files_processed,
                total_files=report.progress_data.total_files,
                bytes_processed=report.progress_data.bytes_processed,
                total_bytes=report.progress_data.total_bytes
            )
            
            # Notify callbacks
            with self._global_lock:
                callbacks = self._progress_callbacks.copy()
            
            for callback in callbacks:
                try:
                    callback(report)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        except Exception as e:
            logger.error(f"Error reporting progress: {e}")
    
    def _collect_performance_metrics(self, job_id: str) -> None:
        """
        Collect performance metrics for a job.
        
        Args:
            job_id: Job identifier
        """
        try:
            if job_id not in self._performance_metrics:
                return
            
            metrics = self._performance_metrics[job_id]
            
            # Collect system metrics (simplified - could be enhanced with psutil)
            # For now, we'll just track what we have from progress data
            
            # Note: In a production system, you would use psutil or similar
            # to collect actual CPU, memory, disk I/O, and network I/O metrics
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics for job {job_id}: {e}")
    
    def _map_state_to_status_level(self, state: ProgressState) -> StatusLevel:
        """
        Map ProgressState to StatusLevel for StatusReporter.
        
        Args:
            state: Progress state
            
        Returns:
            Corresponding StatusLevel
        """
        mapping = {
            ProgressState.NOT_STARTED: StatusLevel.INFO,
            ProgressState.INITIALIZING: StatusLevel.INFO,
            ProgressState.RUNNING: StatusLevel.INFO,
            ProgressState.PAUSED: StatusLevel.WARNING,
            ProgressState.COMPLETED: StatusLevel.SUCCESS,
            ProgressState.FAILED: StatusLevel.ERROR,
            ProgressState.CANCELLED: StatusLevel.WARNING
        }
        return mapping.get(state, StatusLevel.INFO)
    
    def pause_monitoring(self, job_id: str) -> bool:
        """
        Pause progress monitoring for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if paused successfully, False otherwise
        """
        if job_id not in self._active_monitors:
            return False
        
        with self._monitor_locks[job_id]:
            self._active_monitors[job_id]['state'] = ProgressState.PAUSED
            logger.info(f"Progress monitoring paused for job: {job_id}")
            return True
    
    def resume_monitoring(self, job_id: str) -> bool:
        """
        Resume progress monitoring for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if resumed successfully, False otherwise
        """
        if job_id not in self._active_monitors:
            return False
        
        with self._monitor_locks[job_id]:
            if self._active_monitors[job_id]['state'] == ProgressState.PAUSED:
                self._active_monitors[job_id]['state'] = ProgressState.RUNNING
                logger.info(f"Progress monitoring resumed for job: {job_id}")
                return True
            return False
    
    def get_performance_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance summary for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with performance summary or None if not found
        """
        if job_id not in self._performance_metrics:
            return None
        
        metrics = self._performance_metrics[job_id]
        
        return {
            'job_id': job_id,
            'duration_seconds': metrics.duration.total_seconds() if metrics.duration else 0,
            'total_bytes_transferred': metrics.total_bytes_transferred,
            'total_files_processed': metrics.total_files_processed,
            'peak_transfer_rate_mbps': metrics.peak_transfer_rate / (1024 * 1024),
            'average_transfer_rate_mbps': metrics.average_transfer_rate / (1024 * 1024),
            'throughput_mbps': metrics.throughput_mbps,
            'start_time': metrics.start_time.isoformat(),
            'end_time': metrics.end_time.isoformat() if metrics.end_time else None
        }
