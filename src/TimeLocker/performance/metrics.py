"""
Performance metrics collection and analysis for TimeLocker
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class OperationMetrics:
    """Metrics for a single operation"""
    operation_id: str
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    files_processed: int = 0
    bytes_processed: int = 0
    errors_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self):
        """Mark operation as complete and calculate duration"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
                'operation_id':             self.operation_id,
                'operation_type':           self.operation_type,
                'start_time':               self.start_time.isoformat() if self.start_time else None,
                'end_time':                 self.end_time.isoformat() if self.end_time else None,
                'duration_seconds':         self.duration_seconds,
                'files_processed':          self.files_processed,
                'bytes_processed':          self.bytes_processed,
                'errors_count':             self.errors_count,
                'throughput_files_per_sec': self.files_processed / self.duration_seconds if self.duration_seconds and self.duration_seconds > 0 else None,
                'throughput_mb_per_sec':    (
                                                    self.bytes_processed / 1024 / 1024) / self.duration_seconds if self.duration_seconds and self.duration_seconds > 0 else None,
                'metadata':                 self.metadata
        }


class PerformanceMetrics:
    """Centralized performance metrics collection"""

    def __init__(self, metrics_file: Optional[Path] = None):
        self.metrics_file = metrics_file or Path("performance_metrics.json")
        self._operations: Dict[str, OperationMetrics] = {}
        self._completed_operations: List[OperationMetrics] = []
        self._lock = threading.Lock()

        # Load existing metrics if file exists
        self._load_metrics()

    def start_operation(self, operation_id: str, operation_type: str, metadata: Optional[Dict[str, Any]] = None) -> OperationMetrics:
        """Start tracking a new operation"""
        with self._lock:
            metrics = OperationMetrics(
                    operation_id=operation_id,
                    operation_type=operation_type,
                    start_time=datetime.now(),
                    metadata=metadata or {}
            )
            self._operations[operation_id] = metrics
            return metrics

    def update_operation(self, operation_id: str, files_processed: Optional[int] = None,
                         bytes_processed: Optional[int] = None, errors_count: Optional[int] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Update operation metrics"""
        with self._lock:
            if operation_id not in self._operations:
                return

            metrics = self._operations[operation_id]
            if files_processed is not None:
                metrics.files_processed = files_processed
            if bytes_processed is not None:
                metrics.bytes_processed = bytes_processed
            if errors_count is not None:
                metrics.errors_count = errors_count
            if metadata:
                metrics.metadata.update(metadata)

    def complete_operation(self, operation_id: str) -> Optional[OperationMetrics]:
        """Complete an operation and move to completed list"""
        with self._lock:
            if operation_id not in self._operations:
                return None

            metrics = self._operations.pop(operation_id)
            metrics.complete()
            self._completed_operations.append(metrics)

            # Save metrics to file
            self._save_metrics()

            return metrics

    def get_operation_metrics(self, operation_id: str) -> Optional[OperationMetrics]:
        """Get metrics for a specific operation"""
        with self._lock:
            return self._operations.get(operation_id)

    def get_completed_operations(self, operation_type: Optional[str] = None,
                                 limit: Optional[int] = None) -> List[OperationMetrics]:
        """Get completed operations, optionally filtered by type"""
        with self._lock:
            operations = self._completed_operations

            if operation_type:
                operations = [op for op in operations if op.operation_type == operation_type]

            # Sort by start time, most recent first
            operations = sorted(operations, key=lambda x: x.start_time, reverse=True)

            if limit:
                operations = operations[:limit]

            return operations

    def get_performance_summary(self, operation_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary statistics"""
        operations = self.get_completed_operations(operation_type)

        if not operations:
            return {}

        durations = [op.duration_seconds for op in operations if op.duration_seconds]
        files_processed = [op.files_processed for op in operations]
        bytes_processed = [op.bytes_processed for op in operations]
        throughputs = [op.files_processed / op.duration_seconds
                       for op in operations
                       if op.duration_seconds and op.duration_seconds > 0]

        summary = {
                'operation_count':        len(operations),
                'operation_type':         operation_type or 'all',
                'total_files_processed':  sum(files_processed),
                'total_bytes_processed':  sum(bytes_processed),
                'total_duration_seconds': sum(durations) if durations else 0,
        }

        if durations:
            summary.update({
                    'avg_duration_seconds': sum(durations) / len(durations),
                    'min_duration_seconds': min(durations),
                    'max_duration_seconds': max(durations),
            })

        if throughputs:
            summary.update({
                    'avg_throughput_files_per_sec': sum(throughputs) / len(throughputs),
                    'max_throughput_files_per_sec': max(throughputs),
            })

        return summary

    def _load_metrics(self):
        """Load metrics from file"""
        if not self.metrics_file.exists():
            return

        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)

            for op_data in data.get('completed_operations', []):
                metrics = OperationMetrics(
                        operation_id=op_data['operation_id'],
                        operation_type=op_data['operation_type'],
                        start_time=datetime.fromisoformat(op_data['start_time']),
                        end_time=datetime.fromisoformat(op_data['end_time']) if op_data.get('end_time') else None,
                        duration_seconds=op_data.get('duration_seconds'),
                        files_processed=op_data.get('files_processed', 0),
                        bytes_processed=op_data.get('bytes_processed', 0),
                        errors_count=op_data.get('errors_count', 0),
                        metadata=op_data.get('metadata', {})
                )
                self._completed_operations.append(metrics)

        except Exception as e:
            # If we can't load metrics, start fresh
            pass

    def _save_metrics(self):
        """Save metrics to file"""
        try:
            data = {
                    'completed_operations': [op.to_dict() for op in self._completed_operations]
            }

            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            # Fail silently to avoid disrupting operations
            pass


# Global metrics instance
_global_metrics = PerformanceMetrics()


def start_operation_tracking(operation_id: str, operation_type: str, metadata: Optional[Dict[str, Any]] = None) -> OperationMetrics:
    """Start tracking an operation using global metrics"""
    return _global_metrics.start_operation(operation_id, operation_type, metadata)


def update_operation_tracking(operation_id: str, files_processed: Optional[int] = None,
                              bytes_processed: Optional[int] = None, errors_count: Optional[int] = None,
                              metadata: Optional[Dict[str, Any]] = None):
    """Update operation tracking using global metrics"""
    return _global_metrics.update_operation(operation_id, files_processed, bytes_processed, errors_count, metadata)


def complete_operation_tracking(operation_id: str) -> Optional[OperationMetrics]:
    """Complete operation tracking using global metrics"""
    return _global_metrics.complete_operation(operation_id)


def get_global_performance_summary(operation_type: Optional[str] = None) -> Dict[str, Any]:
    """Get performance summary from global metrics"""
    return _global_metrics.get_performance_summary(operation_type)


# Alias for backward compatibility
PerformanceMonitor = PerformanceMetrics
