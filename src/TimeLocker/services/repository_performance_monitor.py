"""
Repository Performance Monitor for TimeLocker

This module provides performance monitoring for repository operations with
desktop-appropriate thresholds and performance warnings.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field

from ..interfaces.repository_management_models import Repository, RepositoryType

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric for a single operation."""
    operation_name: str
    duration: float
    timestamp: datetime
    repository_name: Optional[str] = None
    repository_type: Optional[RepositoryType] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class PerformanceThresholds:
    """Performance thresholds for repository operations."""
    validation_network: float = 15.0  # seconds
    validation_local: float = 3.0     # seconds
    listing: float = 2.0              # seconds
    configuration_update: float = 1.0  # seconds
    
    def get_threshold(self, operation_name: str, repository_type: Optional[RepositoryType] = None) -> float:
        """
        Get threshold for an operation.
        
        Args:
            operation_name: Name of the operation
            repository_type: Type of repository (for validation operations)
            
        Returns:
            float: Threshold in seconds
        """
        if operation_name == 'validation':
            if repository_type == RepositoryType.LOCAL:
                return self.validation_local
            return self.validation_network
        
        return getattr(self, operation_name, 30.0)  # Default 30s threshold


@dataclass
class PerformanceWarning:
    """Performance warning with suggestions."""
    operation_name: str
    duration: float
    threshold: float
    timestamp: datetime
    repository_name: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Format warning as string."""
        msg = (
            f"Performance warning: {self.operation_name} took {self.duration:.2f}s "
            f"(threshold: {self.threshold:.2f}s)"
        )
        if self.repository_name:
            msg += f" for repository '{self.repository_name}'"
        if self.suggestions:
            msg += f"\nSuggestions: {', '.join(self.suggestions)}"
        return msg


class RepositoryPerformanceMonitor:
    """
    Monitors repository operation performance for desktop optimization.
    
    Tracks operation durations, checks against thresholds, and provides
    performance warnings with specific suggestions for improvements.
    """
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        """
        Initialize performance monitor.
        
        Args:
            thresholds: Performance thresholds (uses defaults if not provided)
        """
        self.thresholds = thresholds or PerformanceThresholds()
        self._operation_metrics: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        self._warnings: List[PerformanceWarning] = []
        self._max_metrics_per_operation = 100  # Keep last 100 metrics per operation
        self._max_warnings = 50  # Keep last 50 warnings
        
        logger.debug("RepositoryPerformanceMonitor initialized")
    
    async def monitor_operation(
        self,
        operation_name: str,
        operation_func: Callable[..., Awaitable[Any]],
        *args,
        repository: Optional[Repository] = None,
        **kwargs
    ) -> Any:
        """
        Monitor operation performance and provide warnings.
        
        Args:
            operation_name: Name of the operation being monitored
            operation_func: Async function to execute and monitor
            *args: Positional arguments for operation_func
            repository: Optional repository being operated on
            **kwargs: Keyword arguments for operation_func
            
        Returns:
            Result from operation_func
            
        Raises:
            Any exception raised by operation_func
        """
        start_time = time.time()
        error_message = None
        success = True
        
        try:
            result = await operation_func(*args, **kwargs)
            return result
            
        except Exception as e:
            error_message = str(e)
            success = False
            raise
            
        finally:
            duration = time.time() - start_time
            
            # Record metric
            metric = PerformanceMetric(
                operation_name=operation_name,
                duration=duration,
                timestamp=datetime.utcnow(),
                repository_name=repository.name if repository else None,
                repository_type=repository.config.type if repository else None,
                success=success,
                error_message=error_message
            )
            self._record_metric(metric)
            
            # Check threshold and generate warning if needed
            if success:
                await self._check_threshold(metric)
    
    def _record_metric(self, metric: PerformanceMetric) -> None:
        """
        Record a performance metric.
        
        Args:
            metric: Performance metric to record
        """
        metrics = self._operation_metrics[metric.operation_name]
        metrics.append(metric)
        
        # Keep only the most recent metrics
        if len(metrics) > self._max_metrics_per_operation:
            self._operation_metrics[metric.operation_name] = metrics[-self._max_metrics_per_operation:]
    
    async def _check_threshold(self, metric: PerformanceMetric) -> None:
        """
        Check if metric exceeds threshold and generate warning.
        
        Args:
            metric: Performance metric to check
        """
        threshold = self.thresholds.get_threshold(
            metric.operation_name,
            metric.repository_type
        )
        
        if metric.duration > threshold:
            suggestions = self._generate_suggestions(metric)
            warning = PerformanceWarning(
                operation_name=metric.operation_name,
                duration=metric.duration,
                threshold=threshold,
                timestamp=metric.timestamp,
                repository_name=metric.repository_name,
                suggestions=suggestions
            )
            
            self._record_warning(warning)
            logger.warning(str(warning))
    
    def _generate_suggestions(self, metric: PerformanceMetric) -> List[str]:
        """
        Generate performance improvement suggestions based on metric.
        
        Args:
            metric: Performance metric
            
        Returns:
            List[str]: List of suggestions
        """
        suggestions = []
        
        if metric.operation_name == 'validation':
            if metric.repository_type == RepositoryType.LOCAL:
                suggestions.extend([
                    "Check disk I/O performance",
                    "Verify repository path is accessible",
                    "Consider running repository integrity check"
                ])
            else:
                suggestions.extend([
                    "Check network connectivity",
                    "Consider increasing timeout settings",
                    "Verify repository endpoint is accessible",
                    "Check for network congestion or firewall issues"
                ])
        
        elif metric.operation_name == 'listing':
            suggestions.extend([
                "Consider reducing number of repositories",
                "Check configuration file size",
                "Verify disk performance",
                "Enable repository metadata caching"
            ])
        
        elif metric.operation_name == 'configuration_update':
            suggestions.extend([
                "Check disk write performance",
                "Verify configuration file is not locked",
                "Consider reducing configuration complexity"
            ])
        
        else:
            suggestions.append("Check system performance and resource availability")
        
        return suggestions
    
    def _record_warning(self, warning: PerformanceWarning) -> None:
        """
        Record a performance warning.
        
        Args:
            warning: Performance warning to record
        """
        self._warnings.append(warning)
        
        # Keep only the most recent warnings
        if len(self._warnings) > self._max_warnings:
            self._warnings = self._warnings[-self._max_warnings:]
    
    def get_metrics(
        self,
        operation_name: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceMetric]:
        """
        Get recorded performance metrics.
        
        Args:
            operation_name: Optional filter by operation name
            since: Optional filter by timestamp (metrics after this time)
            limit: Optional limit on number of metrics to return
            
        Returns:
            List[PerformanceMetric]: List of performance metrics
        """
        if operation_name:
            metrics = self._operation_metrics.get(operation_name, [])
        else:
            metrics = []
            for op_metrics in self._operation_metrics.values():
                metrics.extend(op_metrics)
        
        # Filter by timestamp if provided
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        # Sort by timestamp (most recent first)
        metrics = sorted(metrics, key=lambda m: m.timestamp, reverse=True)
        
        # Apply limit if provided
        if limit:
            metrics = metrics[:limit]
        
        return metrics
    
    def get_warnings(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceWarning]:
        """
        Get recorded performance warnings.
        
        Args:
            since: Optional filter by timestamp (warnings after this time)
            limit: Optional limit on number of warnings to return
            
        Returns:
            List[PerformanceWarning]: List of performance warnings
        """
        warnings = self._warnings
        
        # Filter by timestamp if provided
        if since:
            warnings = [w for w in warnings if w.timestamp >= since]
        
        # Sort by timestamp (most recent first)
        warnings = sorted(warnings, key=lambda w: w.timestamp, reverse=True)
        
        # Apply limit if provided
        if limit:
            warnings = warnings[:limit]
        
        return warnings
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dict[str, Any]: Performance statistics including averages and counts
        """
        stats = {
            'total_operations': sum(len(metrics) for metrics in self._operation_metrics.values()),
            'total_warnings': len(self._warnings),
            'operations': {}
        }
        
        for operation_name, metrics in self._operation_metrics.items():
            if not metrics:
                continue
            
            successful_metrics = [m for m in metrics if m.success]
            failed_metrics = [m for m in metrics if not m.success]
            
            durations = [m.duration for m in successful_metrics]
            
            op_stats = {
                'count': len(metrics),
                'successful': len(successful_metrics),
                'failed': len(failed_metrics),
            }
            
            if durations:
                op_stats.update({
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'threshold': self.thresholds.get_threshold(operation_name)
                })
            
            stats['operations'][operation_name] = op_stats
        
        return stats
    
    def clear_metrics(self, operation_name: Optional[str] = None) -> None:
        """
        Clear recorded metrics.
        
        Args:
            operation_name: Optional operation name to clear (clears all if not provided)
        """
        if operation_name:
            self._operation_metrics.pop(operation_name, None)
        else:
            self._operation_metrics.clear()
        
        logger.debug(f"Cleared metrics for {operation_name or 'all operations'}")
    
    def clear_warnings(self) -> None:
        """Clear recorded warnings."""
        self._warnings.clear()
        logger.debug("Cleared all warnings")
    
    def get_recent_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Get performance summary for recent operations.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            Dict[str, Any]: Performance summary
        """
        since = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = self.get_metrics(since=since)
        recent_warnings = self.get_warnings(since=since)
        
        return {
            'time_window_minutes': minutes,
            'total_operations': len(recent_metrics),
            'total_warnings': len(recent_warnings),
            'operations_by_type': self._count_by_operation(recent_metrics),
            'warnings_by_operation': self._count_warnings_by_operation(recent_warnings),
            'average_durations': self._calculate_average_durations(recent_metrics)
        }
    
    def _count_by_operation(self, metrics: List[PerformanceMetric]) -> Dict[str, int]:
        """Count metrics by operation type."""
        counts = defaultdict(int)
        for metric in metrics:
            counts[metric.operation_name] += 1
        return dict(counts)
    
    def _count_warnings_by_operation(self, warnings: List[PerformanceWarning]) -> Dict[str, int]:
        """Count warnings by operation type."""
        counts = defaultdict(int)
        for warning in warnings:
            counts[warning.operation_name] += 1
        return dict(counts)
    
    def _calculate_average_durations(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate average durations by operation type."""
        durations_by_op = defaultdict(list)
        for metric in metrics:
            if metric.success:
                durations_by_op[metric.operation_name].append(metric.duration)
        
        averages = {}
        for op_name, durations in durations_by_op.items():
            if durations:
                averages[op_name] = sum(durations) / len(durations)
        
        return averages
