"""
Performance profiling utilities for TimeLocker operations
"""

import time
import cProfile
import pstats
import io
import psutil
import threading
from functools import wraps
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    operation_name: str
    duration_seconds: float
    memory_usage_mb: float
    peak_memory_mb: float
    cpu_percent: float
    file_count: Optional[int] = None
    bytes_processed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
                'operation_name':           self.operation_name,
                'duration_seconds':         self.duration_seconds,
                'memory_usage_mb':          self.memory_usage_mb,
                'peak_memory_mb':           self.peak_memory_mb,
                'cpu_percent':              self.cpu_percent,
                'file_count':               self.file_count,
                'bytes_processed':          self.bytes_processed,
                'throughput_files_per_sec': self.file_count / self.duration_seconds if self.file_count and self.duration_seconds > 0 else None,
                'throughput_mb_per_sec':    (
                                                    self.bytes_processed / 1024 / 1024) / self.duration_seconds if self.bytes_processed and self.duration_seconds > 0 else None
        }


class PerformanceProfiler:
    """Performance profiler for TimeLocker operations"""

    def __init__(self):
        self.metrics_history: Dict[str, list] = {}
        self._monitoring = False
        self._monitor_thread = None
        self._current_metrics = None

    def profile_operation(self, operation_name: str, enable_cprofile: bool = False):
        """Decorator to profile an operation"""

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._profile_function(func, operation_name, enable_cprofile, *args, **kwargs)

            return wrapper

        return decorator

    def _profile_function(self, func: Callable, operation_name: str, enable_cprofile: bool, *args, **kwargs):
        """Profile a function execution"""
        # Start monitoring
        start_time = time.perf_counter()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Start memory monitoring thread
        peak_memory = initial_memory
        self._monitoring = True

        def monitor_memory():
            nonlocal peak_memory
            while self._monitoring:
                try:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)
                    time.sleep(0.1)  # Check every 100ms
                except:
                    break

        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()

        # Execute function with optional cProfile
        if enable_cprofile:
            profiler = cProfile.Profile()
            profiler.enable()

        try:
            result = func(*args, **kwargs)
        finally:
            # Stop monitoring
            self._monitoring = False
            monitor_thread.join(timeout=1.0)

            if enable_cprofile:
                profiler.disable()
                self._save_cprofile_stats(profiler, operation_name)

        # Calculate metrics
        end_time = time.perf_counter()
        duration = end_time - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration_seconds=duration,
                memory_usage_mb=final_memory - initial_memory,
                peak_memory_mb=peak_memory,
                cpu_percent=cpu_percent
        )

        # Store metrics
        if operation_name not in self.metrics_history:
            self.metrics_history[operation_name] = []
        self.metrics_history[operation_name].append(metrics)

        logger.info(f"Performance metrics for {operation_name}: {metrics.to_dict()}")

        return result

    def _save_cprofile_stats(self, profiler: cProfile.Profile, operation_name: str):
        """Save cProfile statistics to file"""
        stats_dir = Path("performance_stats")
        stats_dir.mkdir(exist_ok=True)

        # Save binary stats
        stats_file = stats_dir / f"{operation_name}_{int(time.time())}.prof"
        profiler.dump_stats(str(stats_file))

        # Save human-readable stats
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions

        text_file = stats_dir / f"{operation_name}_{int(time.time())}.txt"
        with open(text_file, 'w') as f:
            f.write(s.getvalue())

    def get_metrics_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        if operation_name:
            if operation_name not in self.metrics_history:
                return {}
            metrics_list = self.metrics_history[operation_name]
        else:
            metrics_list = []
            for op_metrics in self.metrics_history.values():
                metrics_list.extend(op_metrics)

        if not metrics_list:
            return {}

        durations = [m.duration_seconds for m in metrics_list]
        memory_usage = [m.memory_usage_mb for m in metrics_list]
        peak_memory = [m.peak_memory_mb for m in metrics_list]

        return {
                'operation_count':        len(metrics_list),
                'avg_duration_seconds':   sum(durations) / len(durations),
                'min_duration_seconds':   min(durations),
                'max_duration_seconds':   max(durations),
                'avg_memory_usage_mb':    sum(memory_usage) / len(memory_usage),
                'max_peak_memory_mb':     max(peak_memory),
                'total_duration_seconds': sum(durations)
        }


# Global profiler instance
_global_profiler = PerformanceProfiler()


def profile_operation(operation_name: str, enable_cprofile: bool = False):
    """Decorator to profile an operation using the global profiler"""
    return _global_profiler.profile_operation(operation_name, enable_cprofile)


def get_performance_summary(operation_name: Optional[str] = None) -> Dict[str, Any]:
    """Get performance summary from global profiler"""
    return _global_profiler.get_metrics_summary(operation_name)
