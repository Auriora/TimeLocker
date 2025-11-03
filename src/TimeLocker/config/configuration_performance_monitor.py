"""
Configuration performance monitor for TimeLocker.

This module provides performance monitoring and optimization capabilities
for configuration operations, following the Single Responsibility Principle
by focusing solely on performance tracking and optimization.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a specific operation type"""
    operation_name: str
    total_calls: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    last_called: Optional[datetime] = None
    
    @property
    def average_duration(self) -> float:
        """Calculate average duration"""
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def recent_average_duration(self) -> float:
        """Calculate recent average duration"""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class ConfigurationPerformanceMonitor:
    """
    Configuration performance monitor.
    
    Provides operation timing, cache monitoring, and performance optimization
    recommendations for configuration operations.
    """

    def __init__(self, enable_detailed_tracking: bool = True):
        """
        Initialize the performance monitor.
        
        Args:
            enable_detailed_tracking: Enable detailed operation tracking
        """
        self.enable_detailed_tracking = enable_detailed_tracking
        
        # Operation metrics
        self._operation_metrics: Dict[str, OperationMetrics] = {}
        self._metrics_lock = threading.RLock()
        
        # Cache metrics
        self._cache_metrics = CacheMetrics()
        self._cache_lock = threading.RLock()
        
        # Performance thresholds (in seconds)
        self.slow_operation_threshold = 0.5
        self.very_slow_operation_threshold = 2.0
        
        # Monitoring state
        self._monitoring_enabled = True
        self._start_time = datetime.now()
        
        # Performance alerts
        self._performance_alerts: List[Dict[str, Any]] = []
        self._alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def track_operation(self, operation: str, duration: float, success: bool = True) -> None:
        """
        Track an operation's performance.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
            success: Whether the operation was successful
        """
        if not self._monitoring_enabled or not self.enable_detailed_tracking:
            return
        
        try:
            with self._metrics_lock:
                if operation not in self._operation_metrics:
                    self._operation_metrics[operation] = OperationMetrics(operation)
                
                metrics = self._operation_metrics[operation]
                metrics.total_calls += 1
                metrics.last_called = datetime.now()
                
                if success:
                    metrics.total_duration += duration
                    metrics.min_duration = min(metrics.min_duration, duration)
                    metrics.max_duration = max(metrics.max_duration, duration)
                    metrics.recent_durations.append(duration)
                else:
                    metrics.error_count += 1
                
                # Check for performance issues
                self._check_performance_thresholds(operation, duration)
                
        except Exception as e:
            logger.warning(f"Failed to track operation {operation}: {e}")

    def time_operation(self, operation_name: str):
        """
        Decorator to automatically time operations.
        
        Args:
            operation_name: Name of the operation to track
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise e
                finally:
                    duration = time.time() - start_time
                    self.track_operation(operation_name, duration, success)
            return wrapper
        return decorator

    def track_cache_hit(self) -> None:
        """Track a cache hit"""
        with self._cache_lock:
            self._cache_metrics.hits += 1

    def track_cache_miss(self) -> None:
        """Track a cache miss"""
        with self._cache_lock:
            self._cache_metrics.misses += 1

    def track_cache_eviction(self) -> None:
        """Track a cache eviction"""
        with self._cache_lock:
            self._cache_metrics.evictions += 1

    def update_cache_size(self, current_size: int, max_size: int) -> None:
        """
        Update cache size metrics.
        
        Args:
            current_size: Current cache size
            max_size: Maximum cache size
        """
        with self._cache_lock:
            self._cache_metrics.size = current_size
            self._cache_metrics.max_size = max_size

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            with self._metrics_lock:
                operation_stats = {}
                for op_name, metrics in self._operation_metrics.items():
                    operation_stats[op_name] = {
                        'total_calls': metrics.total_calls,
                        'average_duration': metrics.average_duration,
                        'recent_average_duration': metrics.recent_average_duration,
                        'min_duration': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                        'max_duration': metrics.max_duration,
                        'error_count': metrics.error_count,
                        'error_rate': metrics.error_count / metrics.total_calls if metrics.total_calls > 0 else 0,
                        'last_called': metrics.last_called.isoformat() if metrics.last_called else None
                    }
            
            with self._cache_lock:
                cache_stats = {
                    'hits': self._cache_metrics.hits,
                    'misses': self._cache_metrics.misses,
                    'hit_ratio': self._cache_metrics.hit_ratio,
                    'evictions': self._cache_metrics.evictions,
                    'current_size': self._cache_metrics.size,
                    'max_size': self._cache_metrics.max_size,
                    'utilization': self._cache_metrics.size / self._cache_metrics.max_size if self._cache_metrics.max_size > 0 else 0
                }
            
            uptime = datetime.now() - self._start_time
            
            return {
                'monitoring_enabled': self._monitoring_enabled,
                'uptime_seconds': uptime.total_seconds(),
                'operation_metrics': operation_stats,
                'cache_metrics': cache_stats,
                'performance_alerts': len(self._performance_alerts),
                'slow_operation_threshold': self.slow_operation_threshold,
                'very_slow_operation_threshold': self.very_slow_operation_threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        with self._cache_lock:
            return {
                'hits': self._cache_metrics.hits,
                'misses': self._cache_metrics.misses,
                'total_requests': self._cache_metrics.hits + self._cache_metrics.misses,
                'hit_ratio': self._cache_metrics.hit_ratio,
                'miss_ratio': 1.0 - self._cache_metrics.hit_ratio,
                'evictions': self._cache_metrics.evictions,
                'current_size': self._cache_metrics.size,
                'max_size': self._cache_metrics.max_size,
                'utilization_percent': (self._cache_metrics.size / self._cache_metrics.max_size * 100) if self._cache_metrics.max_size > 0 else 0,
                'efficiency_score': self._calculate_cache_efficiency()
            }

    def optimize_cache(self) -> Dict[str, Any]:
        """
        Analyze cache performance and provide optimization recommendations.
        
        Returns:
            Optimization recommendations
        """
        cache_stats = self.get_cache_statistics()
        recommendations = []
        
        # Analyze hit ratio
        if cache_stats['hit_ratio'] < 0.7:
            recommendations.append({
                'type': 'cache_size',
                'priority': 'high',
                'message': f"Low cache hit ratio ({cache_stats['hit_ratio']:.2%}). Consider increasing cache size.",
                'current_value': cache_stats['max_size'],
                'suggested_value': cache_stats['max_size'] * 2
            })
        
        # Analyze utilization
        if cache_stats['utilization_percent'] > 90:
            recommendations.append({
                'type': 'cache_pressure',
                'priority': 'medium',
                'message': f"High cache utilization ({cache_stats['utilization_percent']:.1f}%). Frequent evictions may occur.",
                'current_value': cache_stats['utilization_percent'],
                'suggested_action': 'Monitor eviction rate and consider cache size increase'
            })
        
        # Analyze eviction rate
        total_requests = cache_stats['total_requests']
        if total_requests > 0:
            eviction_rate = cache_stats['evictions'] / total_requests
            if eviction_rate > 0.1:
                recommendations.append({
                    'type': 'eviction_rate',
                    'priority': 'high',
                    'message': f"High eviction rate ({eviction_rate:.2%}). Cache may be too small for workload.",
                    'current_value': eviction_rate,
                    'suggested_action': 'Increase cache size or implement better eviction policy'
                })
        
        return {
            'cache_statistics': cache_stats,
            'recommendations': recommendations,
            'optimization_score': self._calculate_optimization_score(cache_stats),
            'timestamp': datetime.now().isoformat()
        }

    def get_recommendations(self) -> List[str]:
        """
        Get performance optimization recommendations.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        try:
            metrics = self.get_performance_metrics()
            
            # Analyze operation performance
            for op_name, op_stats in metrics.get('operation_metrics', {}).items():
                if op_stats['average_duration'] > self.very_slow_operation_threshold:
                    recommendations.append(
                        f"Operation '{op_name}' is very slow (avg: {op_stats['average_duration']:.3f}s). "
                        f"Consider optimization or caching."
                    )
                elif op_stats['average_duration'] > self.slow_operation_threshold:
                    recommendations.append(
                        f"Operation '{op_name}' is slow (avg: {op_stats['average_duration']:.3f}s). "
                        f"Monitor for performance degradation."
                    )
                
                if op_stats['error_rate'] > 0.05:  # 5% error rate
                    recommendations.append(
                        f"Operation '{op_name}' has high error rate ({op_stats['error_rate']:.1%}). "
                        f"Investigate error causes."
                    )
            
            # Analyze cache performance
            cache_stats = metrics.get('cache_metrics', {})
            if cache_stats.get('hit_ratio', 0) < 0.8:
                recommendations.append(
                    f"Cache hit ratio is low ({cache_stats.get('hit_ratio', 0):.1%}). "
                    f"Consider increasing cache size or improving cache strategy."
                )
            
            # Check for performance alerts
            if len(self._performance_alerts) > 0:
                recommendations.append(
                    f"There are {len(self._performance_alerts)} active performance alerts. "
                    f"Review alerts for specific issues."
                )
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to monitoring error.")
        
        return recommendations

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback for performance alerts.
        
        Args:
            callback: Function to call when performance alerts are triggered
        """
        self._alert_callbacks.append(callback)

    def clear_metrics(self) -> None:
        """Clear all performance metrics"""
        with self._metrics_lock:
            self._operation_metrics.clear()
        
        with self._cache_lock:
            self._cache_metrics = CacheMetrics()
        
        self._performance_alerts.clear()
        self._start_time = datetime.now()

    def enable_monitoring(self) -> None:
        """Enable performance monitoring"""
        self._monitoring_enabled = True

    def disable_monitoring(self) -> None:
        """Disable performance monitoring"""
        self._monitoring_enabled = False

    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled"""
        return self._monitoring_enabled

    # Private helper methods

    def _check_performance_thresholds(self, operation: str, duration: float) -> None:
        """Check if operation duration exceeds performance thresholds"""
        if duration > self.very_slow_operation_threshold:
            alert = {
                'type': 'very_slow_operation',
                'operation': operation,
                'duration': duration,
                'threshold': self.very_slow_operation_threshold,
                'timestamp': datetime.now(),
                'severity': 'high'
            }
            self._add_performance_alert(alert)
        elif duration > self.slow_operation_threshold:
            alert = {
                'type': 'slow_operation',
                'operation': operation,
                'duration': duration,
                'threshold': self.slow_operation_threshold,
                'timestamp': datetime.now(),
                'severity': 'medium'
            }
            self._add_performance_alert(alert)

    def _add_performance_alert(self, alert: Dict[str, Any]) -> None:
        """Add a performance alert"""
        self._performance_alerts.append(alert)
        
        # Keep only recent alerts (last 100)
        if len(self._performance_alerts) > 100:
            self._performance_alerts = self._performance_alerts[-50:]
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.warning(f"Performance alert callback failed: {e}")

    def _calculate_cache_efficiency(self) -> float:
        """Calculate cache efficiency score (0-100)"""
        hit_ratio = self._cache_metrics.hit_ratio
        utilization = self._cache_metrics.size / self._cache_metrics.max_size if self._cache_metrics.max_size > 0 else 0
        
        # Efficiency is based on hit ratio and reasonable utilization
        # Optimal utilization is around 70-80%
        utilization_score = 1.0 - abs(utilization - 0.75) / 0.75
        utilization_score = max(0, min(1, utilization_score))
        
        # Combine hit ratio (70%) and utilization score (30%)
        efficiency = (hit_ratio * 0.7) + (utilization_score * 0.3)
        return efficiency * 100

    def _calculate_optimization_score(self, cache_stats: Dict[str, Any]) -> float:
        """Calculate overall optimization score (0-100)"""
        hit_ratio_score = cache_stats['hit_ratio'] * 100
        utilization_score = min(cache_stats['utilization_percent'], 100)
        
        # Penalize high eviction rates
        eviction_penalty = 0
        if cache_stats['total_requests'] > 0:
            eviction_rate = cache_stats['evictions'] / cache_stats['total_requests']
            eviction_penalty = min(eviction_rate * 100, 50)  # Max 50 point penalty
        
        # Combine scores
        score = (hit_ratio_score * 0.5) + (utilization_score * 0.3) + (20 - eviction_penalty * 0.2)
        return max(0, min(100, score))