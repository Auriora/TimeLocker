"""
Performance tracking for backup operations with user-friendly metrics and trends.

This module extends the existing performance tracking infrastructure to provide
backup-specific performance monitoring, trend analysis, and optimization recommendations.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance level indicators"""
    EXCELLENT = "excellent"
    GOOD = "good"
    NORMAL = "normal"
    SLOW = "slow"
    VERY_SLOW = "very_slow"


@dataclass
class BackupPerformanceMetrics:
    """
    Comprehensive performance metrics for backup operations.
    
    Extends basic metrics with backup-specific information and user-friendly formatting.
    """
    operation_id: str
    repository_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    files_processed: int
    bytes_processed: int
    files_per_second: float
    throughput_mbps: float
    average_file_size_mb: float
    performance_level: PerformanceLevel
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['start_time'] = self.start_time.isoformat()
        result['end_time'] = self.end_time.isoformat()
        result['performance_level'] = self.performance_level.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupPerformanceMetrics':
        """Create from dictionary"""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        data['performance_level'] = PerformanceLevel(data['performance_level'])
        return cls(**data)
    
    def get_user_friendly_summary(self) -> str:
        """Get user-friendly performance summary"""
        duration_str = self._format_duration(self.duration_seconds)
        size_str = self._format_bytes(self.bytes_processed)
        throughput_str = f"{self.throughput_mbps:.1f} MB/s"
        
        return (
            f"Completed in {duration_str}, processed {self.files_processed:,} files "
            f"({size_str}) at {throughput_str}"
        )
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in user-friendly format"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    @staticmethod
    def _format_bytes(bytes_count: int) -> str:
        """Format bytes in user-friendly format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"


@dataclass
class PerformanceTrend:
    """Performance trend analysis over time"""
    repository_id: str
    period_days: int
    operation_count: int
    average_duration_seconds: float
    average_throughput_mbps: float
    average_files_per_second: float
    trend_direction: str  # improving, stable, degrading
    trend_percentage: float  # percentage change
    slowest_operation: Optional[BackupPerformanceMetrics] = None
    fastest_operation: Optional[BackupPerformanceMetrics] = None
    
    def get_trend_description(self) -> str:
        """Get user-friendly trend description"""
        if self.trend_direction == "improving":
            return f"Performance is improving by {abs(self.trend_percentage):.1f}%"
        elif self.trend_direction == "degrading":
            return f"Performance is degrading by {abs(self.trend_percentage):.1f}%"
        else:
            return "Performance is stable"


@dataclass
class PerformanceSummary:
    """Summary of performance metrics for display"""
    repository_id: str
    last_backup_duration: Optional[str] = None
    last_backup_throughput: Optional[str] = None
    average_duration: Optional[str] = None
    average_throughput: Optional[str] = None
    performance_level: Optional[PerformanceLevel] = None
    trend: Optional[PerformanceTrend] = None
    total_operations: int = 0


class PerformanceTracker:
    """
    Tracks backup performance with user-friendly metrics and trend analysis.
    
    Responsibilities:
    - Track backup operation performance metrics
    - Analyze performance trends over time
    - Provide user-friendly performance summaries
    - Detect performance anomalies
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize performance tracker.
        
        Args:
            config_dir: Directory for performance data storage
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            import os
            
            xdg_state_home = os.environ.get('XDG_STATE_HOME')
            if xdg_state_home:
                state_dir = Path(xdg_state_home) / "timelocker"
            else:
                state_dir = Path.home() / ".local" / "state" / "timelocker"
            
            config_dir = state_dir / "performance"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage for performance metrics
        self._metrics_cache: Dict[str, List[BackupPerformanceMetrics]] = {}
        self._load_metrics()
    
    def record_backup_performance(
        self,
        operation_id: str,
        repository_id: str,
        start_time: datetime,
        end_time: datetime,
        files_processed: int,
        bytes_processed: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BackupPerformanceMetrics:
        """
        Record performance metrics for a completed backup operation.
        
        Args:
            operation_id: Unique operation identifier
            repository_id: Repository identifier
            start_time: Operation start time
            end_time: Operation end time
            files_processed: Number of files processed
            bytes_processed: Bytes processed
            metadata: Additional metadata
            
        Returns:
            BackupPerformanceMetrics: Recorded metrics
        """
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Calculate performance metrics
        files_per_second = files_processed / duration_seconds if duration_seconds > 0 else 0
        throughput_mbps = (bytes_processed / 1024 / 1024) / duration_seconds if duration_seconds > 0 else 0
        average_file_size_mb = (bytes_processed / 1024 / 1024) / files_processed if files_processed > 0 else 0
        
        # Determine performance level
        performance_level = self._calculate_performance_level(
            throughput_mbps, files_per_second, repository_id
        )
        
        metrics = BackupPerformanceMetrics(
            operation_id=operation_id,
            repository_id=repository_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            files_processed=files_processed,
            bytes_processed=bytes_processed,
            files_per_second=files_per_second,
            throughput_mbps=throughput_mbps,
            average_file_size_mb=average_file_size_mb,
            performance_level=performance_level,
            metadata=metadata or {}
        )
        
        # Store metrics
        if repository_id not in self._metrics_cache:
            self._metrics_cache[repository_id] = []
        self._metrics_cache[repository_id].append(metrics)
        
        # Persist metrics
        self._save_metrics(repository_id)
        
        logger.info(
            f"Recorded performance for {operation_id}: {metrics.get_user_friendly_summary()}"
        )
        
        return metrics
    
    def get_performance_summary(self, repository_id: str) -> PerformanceSummary:
        """
        Get performance summary for a repository.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            PerformanceSummary: Performance summary
        """
        metrics_list = self._metrics_cache.get(repository_id, [])
        
        if not metrics_list:
            return PerformanceSummary(
                repository_id=repository_id,
                total_operations=0
            )
        
        # Get last backup metrics
        last_metrics = metrics_list[-1]
        
        # Calculate averages
        avg_duration = statistics.mean([m.duration_seconds for m in metrics_list])
        avg_throughput = statistics.mean([m.throughput_mbps for m in metrics_list])
        
        # Get trend analysis
        trend = self.get_performance_trends(repository_id, days=30)
        
        return PerformanceSummary(
            repository_id=repository_id,
            last_backup_duration=BackupPerformanceMetrics._format_duration(
                last_metrics.duration_seconds
            ),
            last_backup_throughput=f"{last_metrics.throughput_mbps:.1f} MB/s",
            average_duration=BackupPerformanceMetrics._format_duration(avg_duration),
            average_throughput=f"{avg_throughput:.1f} MB/s",
            performance_level=last_metrics.performance_level,
            trend=trend,
            total_operations=len(metrics_list)
        )
    
    def get_performance_trends(
        self,
        repository_id: str,
        days: int = 30
    ) -> Optional[PerformanceTrend]:
        """
        Analyze performance trends over specified period.
        
        Args:
            repository_id: Repository identifier
            days: Number of days to analyze
            
        Returns:
            PerformanceTrend: Trend analysis or None if insufficient data
        """
        metrics_list = self._metrics_cache.get(repository_id, [])
        
        if len(metrics_list) < 2:
            return None
        
        # Filter to specified period
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_metrics = [
            m for m in metrics_list
            if m.start_time >= cutoff_date
        ]
        
        if len(recent_metrics) < 2:
            return None
        
        # Calculate averages
        avg_duration = statistics.mean([m.duration_seconds for m in recent_metrics])
        avg_throughput = statistics.mean([m.throughput_mbps for m in recent_metrics])
        avg_files_per_sec = statistics.mean([m.files_per_second for m in recent_metrics])
        
        # Analyze trend by comparing first half vs second half
        midpoint = len(recent_metrics) // 2
        first_half = recent_metrics[:midpoint]
        second_half = recent_metrics[midpoint:]
        
        first_half_throughput = statistics.mean([m.throughput_mbps for m in first_half])
        second_half_throughput = statistics.mean([m.throughput_mbps for m in second_half])
        
        # Calculate trend
        if first_half_throughput > 0:
            trend_percentage = ((second_half_throughput - first_half_throughput) / 
                              first_half_throughput * 100)
        else:
            trend_percentage = 0
        
        # Determine trend direction (5% threshold for significance)
        if trend_percentage > 5:
            trend_direction = "improving"
        elif trend_percentage < -5:
            trend_direction = "degrading"
        else:
            trend_direction = "stable"
        
        # Find slowest and fastest operations
        slowest = min(recent_metrics, key=lambda m: m.throughput_mbps)
        fastest = max(recent_metrics, key=lambda m: m.throughput_mbps)
        
        return PerformanceTrend(
            repository_id=repository_id,
            period_days=days,
            operation_count=len(recent_metrics),
            average_duration_seconds=avg_duration,
            average_throughput_mbps=avg_throughput,
            average_files_per_second=avg_files_per_sec,
            trend_direction=trend_direction,
            trend_percentage=trend_percentage,
            slowest_operation=slowest,
            fastest_operation=fastest
        )
    
    def get_recent_operations(
        self,
        repository_id: str,
        limit: int = 10
    ) -> List[BackupPerformanceMetrics]:
        """
        Get recent backup operations for a repository.
        
        Args:
            repository_id: Repository identifier
            limit: Maximum number of operations to return
            
        Returns:
            List of recent performance metrics
        """
        metrics_list = self._metrics_cache.get(repository_id, [])
        return metrics_list[-limit:] if metrics_list else []
    
    def compare_performance(
        self,
        operation_id1: str,
        operation_id2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare performance between two operations.
        
        Args:
            operation_id1: First operation ID
            operation_id2: Second operation ID
            
        Returns:
            Comparison results or None if operations not found
        """
        # Find operations
        op1 = None
        op2 = None
        
        for metrics_list in self._metrics_cache.values():
            for metrics in metrics_list:
                if metrics.operation_id == operation_id1:
                    op1 = metrics
                if metrics.operation_id == operation_id2:
                    op2 = metrics
        
        if not op1 or not op2:
            return None
        
        # Calculate differences
        duration_diff = op2.duration_seconds - op1.duration_seconds
        throughput_diff = op2.throughput_mbps - op1.throughput_mbps
        
        return {
            'operation1': op1.to_dict(),
            'operation2': op2.to_dict(),
            'duration_difference_seconds': duration_diff,
            'duration_difference_percentage': (duration_diff / op1.duration_seconds * 100) 
                if op1.duration_seconds > 0 else 0,
            'throughput_difference_mbps': throughput_diff,
            'throughput_difference_percentage': (throughput_diff / op1.throughput_mbps * 100)
                if op1.throughput_mbps > 0 else 0,
        }
    
    def detect_performance_anomalies(
        self,
        repository_id: str,
        threshold_std_dev: float = 2.0
    ) -> List[BackupPerformanceMetrics]:
        """
        Detect performance anomalies (operations significantly slower than normal).
        
        Args:
            repository_id: Repository identifier
            threshold_std_dev: Number of standard deviations for anomaly detection
            
        Returns:
            List of anomalous operations
        """
        metrics_list = self._metrics_cache.get(repository_id, [])
        
        if len(metrics_list) < 5:  # Need sufficient data
            return []
        
        # Calculate mean and standard deviation of throughput
        throughputs = [m.throughput_mbps for m in metrics_list]
        mean_throughput = statistics.mean(throughputs)
        
        try:
            std_dev = statistics.stdev(throughputs)
        except statistics.StatisticsError:
            return []
        
        # Find anomalies (operations with throughput below threshold)
        threshold = mean_throughput - (threshold_std_dev * std_dev)
        anomalies = [
            m for m in metrics_list
            if m.throughput_mbps < threshold
        ]
        
        return anomalies
    
    def _calculate_performance_level(
        self,
        throughput_mbps: float,
        files_per_second: float,
        repository_id: str
    ) -> PerformanceLevel:
        """
        Calculate performance level based on metrics and historical data.
        
        Args:
            throughput_mbps: Current throughput
            files_per_second: Current files per second
            repository_id: Repository identifier
            
        Returns:
            PerformanceLevel: Calculated performance level
        """
        metrics_list = self._metrics_cache.get(repository_id, [])
        
        if len(metrics_list) < 3:
            # Not enough historical data, use absolute thresholds
            if throughput_mbps >= 50:
                return PerformanceLevel.EXCELLENT
            elif throughput_mbps >= 20:
                return PerformanceLevel.GOOD
            elif throughput_mbps >= 5:
                return PerformanceLevel.NORMAL
            elif throughput_mbps >= 1:
                return PerformanceLevel.SLOW
            else:
                return PerformanceLevel.VERY_SLOW
        
        # Use historical data for relative performance
        avg_throughput = statistics.mean([m.throughput_mbps for m in metrics_list])
        
        if throughput_mbps >= avg_throughput * 1.5:
            return PerformanceLevel.EXCELLENT
        elif throughput_mbps >= avg_throughput * 1.1:
            return PerformanceLevel.GOOD
        elif throughput_mbps >= avg_throughput * 0.8:
            return PerformanceLevel.NORMAL
        elif throughput_mbps >= avg_throughput * 0.5:
            return PerformanceLevel.SLOW
        else:
            return PerformanceLevel.VERY_SLOW
    
    def _save_metrics(self, repository_id: str):
        """Save metrics for a repository to disk"""
        metrics_file = self.config_dir / f"{repository_id}_performance.json"
        
        try:
            import json
            metrics_list = self._metrics_cache.get(repository_id, [])
            
            # Keep only last 100 operations to prevent file growth
            metrics_to_save = metrics_list[-100:]
            
            data = {
                'repository_id': repository_id,
                'metrics': [m.to_dict() for m in metrics_to_save]
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
    
    def _load_metrics(self):
        """Load all metrics from disk"""
        try:
            import json
            
            for metrics_file in self.config_dir.glob("*_performance.json"):
                try:
                    with open(metrics_file, 'r') as f:
                        data = json.load(f)
                    
                    repository_id = data.get('repository_id')
                    if not repository_id:
                        continue
                    
                    metrics_list = [
                        BackupPerformanceMetrics.from_dict(m)
                        for m in data.get('metrics', [])
                    ]
                    
                    self._metrics_cache[repository_id] = metrics_list
                    
                except Exception as e:
                    logger.warning(f"Failed to load metrics from {metrics_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load performance metrics: {e}")
