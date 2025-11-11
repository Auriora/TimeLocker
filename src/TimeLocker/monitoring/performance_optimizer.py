"""
Performance optimization recommendations for backup operations.

This module provides user-friendly performance recommendations, anomaly detection,
and optimization suggestions based on backup performance analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .performance_tracker import (
    PerformanceTracker,
    BackupPerformanceMetrics,
    PerformanceLevel,
    PerformanceTrend
)

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of performance recommendations"""
    TIMING = "timing"
    SETTINGS = "settings"
    STORAGE = "storage"
    NETWORK = "network"
    SYSTEM = "system"
    GENERAL = "general"


class RecommendationPriority(Enum):
    """Priority levels for recommendations"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class PerformanceRecommendation:
    """
    A performance optimization recommendation.
    
    Provides user-friendly guidance for improving backup performance.
    """
    recommendation_type: RecommendationType
    priority: RecommendationPriority
    title: str
    description: str
    rationale: str
    suggested_actions: List[str]
    estimated_improvement: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'type': self.recommendation_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'rationale': self.rationale,
            'suggested_actions': self.suggested_actions,
            'estimated_improvement': self.estimated_improvement
        }


@dataclass
class PerformanceIssue:
    """
    Detected performance issue with analysis.
    """
    issue_type: str
    severity: str
    description: str
    affected_operations: List[str]
    possible_causes: List[str]
    recommendations: List[PerformanceRecommendation]


class PerformanceOptimizer:
    """
    Provides performance optimization recommendations and issue detection.
    
    Responsibilities:
    - Analyze backup performance patterns
    - Detect performance issues and anomalies
    - Generate user-friendly optimization recommendations
    - Suggest optimal backup timing and settings
    """
    
    def __init__(self, performance_tracker: PerformanceTracker):
        """
        Initialize performance optimizer.
        
        Args:
            performance_tracker: Performance tracker instance
        """
        self.tracker = performance_tracker
    
    def get_optimization_recommendations(
        self,
        repository_id: str
    ) -> List[PerformanceRecommendation]:
        """
        Get performance optimization recommendations for a repository.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            List of performance recommendations
        """
        recommendations = []
        
        # Get performance data
        summary = self.tracker.get_performance_summary(repository_id)
        trend = self.tracker.get_performance_trends(repository_id, days=30)
        recent_ops = self.tracker.get_recent_operations(repository_id, limit=10)
        
        if not recent_ops:
            return recommendations
        
        # Check for timing optimization opportunities
        timing_recs = self._analyze_timing_patterns(repository_id, recent_ops)
        recommendations.extend(timing_recs)
        
        # Check for performance degradation
        if trend and trend.trend_direction == "degrading":
            degradation_recs = self._analyze_performance_degradation(trend)
            recommendations.extend(degradation_recs)
        
        # Check for slow operations
        if summary.performance_level in [PerformanceLevel.SLOW, PerformanceLevel.VERY_SLOW]:
            slow_recs = self._analyze_slow_performance(repository_id, recent_ops)
            recommendations.extend(slow_recs)
        
        # Check for anomalies
        anomalies = self.tracker.detect_performance_anomalies(repository_id)
        if anomalies:
            anomaly_recs = self._analyze_anomalies(anomalies)
            recommendations.extend(anomaly_recs)
        
        # General optimization recommendations
        general_recs = self._get_general_recommendations(recent_ops)
        recommendations.extend(general_recs)
        
        # Sort by priority
        priority_order = {
            RecommendationPriority.HIGH: 0,
            RecommendationPriority.MEDIUM: 1,
            RecommendationPriority.LOW: 2,
            RecommendationPriority.INFO: 3
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    def analyze_slow_backup(
        self,
        operation_id: str
    ) -> Optional[PerformanceIssue]:
        """
        Analyze a slow backup operation and provide detailed diagnosis.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            PerformanceIssue with analysis or None if operation not found
        """
        # Find the operation
        operation = None
        repository_id = None
        
        for repo_id, metrics_list in self.tracker._metrics_cache.items():
            for metrics in metrics_list:
                if metrics.operation_id == operation_id:
                    operation = metrics
                    repository_id = repo_id
                    break
            if operation:
                break
        
        if not operation:
            return None
        
        # Analyze the slow operation
        possible_causes = []
        recommendations = []
        
        # Compare with average performance
        summary = self.tracker.get_performance_summary(repository_id)
        recent_ops = self.tracker.get_recent_operations(repository_id, limit=10)
        
        if len(recent_ops) > 1:
            import statistics
            avg_throughput = statistics.mean([
                m.throughput_mbps for m in recent_ops if m.operation_id != operation_id
            ])
            
            if operation.throughput_mbps < avg_throughput * 0.5:
                possible_causes.append(
                    "Throughput is significantly lower than average for this repository"
                )
        
        # Check for large number of small files
        if operation.average_file_size_mb < 0.1:  # Less than 100KB average
            possible_causes.append(
                "Backup contains many small files, which can slow down operations"
            )
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.SETTINGS,
                priority=RecommendationPriority.MEDIUM,
                title="Optimize for small files",
                description="Consider adjusting backup settings for small file optimization",
                rationale="Many small files can cause overhead in backup operations",
                suggested_actions=[
                    "Use file grouping or archiving for small files",
                    "Exclude temporary or cache directories with many small files",
                    "Consider using compression to reduce file count"
                ],
                estimated_improvement="20-40% faster backups"
            ))
        
        # Check time of day
        hour = operation.start_time.hour
        if 9 <= hour <= 17:  # Business hours
            possible_causes.append(
                "Backup ran during business hours when system may be under heavy use"
            )
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.TIMING,
                priority=RecommendationPriority.HIGH,
                title="Schedule backups during off-peak hours",
                description="Run backups during off-peak hours for better performance",
                rationale="System resources are more available during off-peak times",
                suggested_actions=[
                    "Schedule backups for late evening or early morning",
                    "Avoid backup times that coincide with heavy system usage",
                    "Consider running backups overnight (e.g., 2-4 AM)"
                ],
                estimated_improvement="30-50% faster backups"
            ))
        
        # Check for network-based repository
        if 'remote' in operation.metadata.get('repository_type', '').lower():
            possible_causes.append(
                "Network latency or bandwidth limitations may be affecting performance"
            )
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.NETWORK,
                priority=RecommendationPriority.MEDIUM,
                title="Check network connectivity",
                description="Verify network connection quality to backup destination",
                rationale="Network issues can significantly impact backup performance",
                suggested_actions=[
                    "Test network speed to backup destination",
                    "Check for network congestion during backup times",
                    "Consider using a wired connection instead of WiFi",
                    "Verify firewall or VPN settings aren't limiting bandwidth"
                ],
                estimated_improvement="Variable, depends on network improvements"
            ))
        
        # Determine severity
        if operation.performance_level == PerformanceLevel.VERY_SLOW:
            severity = "high"
        elif operation.performance_level == PerformanceLevel.SLOW:
            severity = "medium"
        else:
            severity = "low"
        
        return PerformanceIssue(
            issue_type="slow_backup",
            severity=severity,
            description=f"Backup operation completed in {operation.duration_seconds:.1f} seconds "
                       f"with throughput of {operation.throughput_mbps:.1f} MB/s",
            affected_operations=[operation_id],
            possible_causes=possible_causes if possible_causes else [
                "Performance is within normal range but could be optimized"
            ],
            recommendations=recommendations
        )
    
    def compare_and_suggest(
        self,
        operation_id1: str,
        operation_id2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compare two operations and suggest improvements.
        
        Args:
            operation_id1: First operation ID
            operation_id2: Second operation ID
            
        Returns:
            Comparison with suggestions or None if operations not found
        """
        comparison = self.tracker.compare_performance(operation_id1, operation_id2)
        
        if not comparison:
            return None
        
        suggestions = []
        
        # Analyze differences
        throughput_diff_pct = comparison['throughput_difference_percentage']
        
        if abs(throughput_diff_pct) > 20:
            if throughput_diff_pct < 0:
                # Second operation was slower
                suggestions.append(
                    "The second backup was significantly slower. "
                    "Check if system resources were constrained or if backup timing differed."
                )
            else:
                # Second operation was faster
                suggestions.append(
                    "The second backup was significantly faster. "
                    "Consider what conditions led to better performance and replicate them."
                )
        
        comparison['suggestions'] = suggestions
        return comparison
    
    def _analyze_timing_patterns(
        self,
        repository_id: str,
        recent_ops: List[BackupPerformanceMetrics]
    ) -> List[PerformanceRecommendation]:
        """Analyze timing patterns and suggest optimal backup times"""
        recommendations = []
        
        if len(recent_ops) < 5:
            return recommendations
        
        # Analyze performance by hour of day
        hour_performance: Dict[int, List[float]] = {}
        for op in recent_ops:
            hour = op.start_time.hour
            if hour not in hour_performance:
                hour_performance[hour] = []
            hour_performance[hour].append(op.throughput_mbps)
        
        if len(hour_performance) >= 3:
            # Find best performing hours
            import statistics
            avg_by_hour = {
                hour: statistics.mean(throughputs)
                for hour, throughputs in hour_performance.items()
            }
            
            best_hour = max(avg_by_hour, key=avg_by_hour.get)
            best_throughput = avg_by_hour[best_hour]
            
            # Check if there's significant variation
            overall_avg = statistics.mean([t for throughputs in hour_performance.values() 
                                          for t in throughputs])
            
            if best_throughput > overall_avg * 1.2:
                recommendations.append(PerformanceRecommendation(
                    recommendation_type=RecommendationType.TIMING,
                    priority=RecommendationPriority.MEDIUM,
                    title="Optimal backup timing identified",
                    description=f"Backups perform best around {best_hour:02d}:00",
                    rationale="Analysis shows better performance at specific times",
                    suggested_actions=[
                        f"Schedule backups to run around {best_hour:02d}:00",
                        "Monitor system load at different times to confirm pattern",
                        "Adjust backup schedule to align with optimal performance window"
                    ],
                    estimated_improvement=f"{((best_throughput / overall_avg - 1) * 100):.0f}% faster"
                ))
        
        return recommendations
    
    def _analyze_performance_degradation(
        self,
        trend: PerformanceTrend
    ) -> List[PerformanceRecommendation]:
        """Analyze performance degradation and provide recommendations"""
        recommendations = []
        
        if trend.trend_percentage < -10:  # More than 10% degradation
            priority = RecommendationPriority.HIGH
        else:
            priority = RecommendationPriority.MEDIUM
        
        recommendations.append(PerformanceRecommendation(
            recommendation_type=RecommendationType.GENERAL,
            priority=priority,
            title="Performance degradation detected",
            description=f"Backup performance has degraded by {abs(trend.trend_percentage):.1f}% "
                       f"over the past {trend.period_days} days",
            rationale="Gradual performance decline may indicate system issues",
            suggested_actions=[
                "Check available disk space on backup source and destination",
                "Verify no background processes are consuming resources",
                "Review recent system changes or updates",
                "Consider running system maintenance (disk cleanup, defragmentation)",
                "Check for malware or unwanted software"
            ],
            estimated_improvement="Restore to previous performance levels"
        ))
        
        return recommendations
    
    def _analyze_slow_performance(
        self,
        repository_id: str,
        recent_ops: List[BackupPerformanceMetrics]
    ) -> List[PerformanceRecommendation]:
        """Analyze consistently slow performance"""
        recommendations = []
        
        avg_throughput = sum(op.throughput_mbps for op in recent_ops) / len(recent_ops)
        
        if avg_throughput < 5:  # Less than 5 MB/s
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.SYSTEM,
                priority=RecommendationPriority.HIGH,
                title="Consistently slow backup performance",
                description=f"Average throughput is {avg_throughput:.1f} MB/s, which is below optimal",
                rationale="Slow backups may indicate system or configuration issues",
                suggested_actions=[
                    "Check disk I/O performance on source and destination",
                    "Verify sufficient RAM is available during backups",
                    "Close unnecessary applications during backup",
                    "Check if antivirus is scanning backup files (add exclusions if needed)",
                    "Consider upgrading hardware if consistently slow"
                ],
                estimated_improvement="2-5x faster with proper optimization"
            ))
        
        return recommendations
    
    def _analyze_anomalies(
        self,
        anomalies: List[BackupPerformanceMetrics]
    ) -> List[PerformanceRecommendation]:
        """Analyze performance anomalies"""
        recommendations = []
        
        if len(anomalies) > 0:
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.GENERAL,
                priority=RecommendationPriority.MEDIUM,
                title="Performance anomalies detected",
                description=f"Found {len(anomalies)} backup(s) with unusual performance",
                rationale="Occasional slow backups may indicate intermittent issues",
                suggested_actions=[
                    "Review system logs for errors during slow backups",
                    "Check if slow backups coincide with other system activities",
                    "Monitor system resources during next backup",
                    "Consider if specific file types or locations cause slowdowns"
                ],
                estimated_improvement="Prevent future anomalies"
            ))
        
        return recommendations
    
    def _get_general_recommendations(
        self,
        recent_ops: List[BackupPerformanceMetrics]
    ) -> List[PerformanceRecommendation]:
        """Get general optimization recommendations"""
        recommendations = []
        
        if not recent_ops:
            return recommendations
        
        # Check average file size
        avg_file_size = sum(op.average_file_size_mb for op in recent_ops) / len(recent_ops)
        
        if avg_file_size < 0.1:  # Less than 100KB average
            recommendations.append(PerformanceRecommendation(
                recommendation_type=RecommendationType.SETTINGS,
                priority=RecommendationPriority.LOW,
                title="Many small files detected",
                description="Backups contain many small files which can impact performance",
                rationale="Small files have higher overhead per byte",
                suggested_actions=[
                    "Review backup selections to exclude unnecessary small files",
                    "Consider excluding cache and temporary directories",
                    "Use file grouping or compression where appropriate"
                ],
                estimated_improvement="10-30% faster backups"
            ))
        
        # General best practices
        recommendations.append(PerformanceRecommendation(
            recommendation_type=RecommendationType.GENERAL,
            priority=RecommendationPriority.INFO,
            title="General performance best practices",
            description="Follow these practices for optimal backup performance",
            rationale="Consistent good practices ensure reliable performance",
            suggested_actions=[
                "Keep backup software and system updated",
                "Regularly clean up old or unnecessary files",
                "Monitor disk space on both source and destination",
                "Schedule backups during low-activity periods",
                "Test restore operations periodically"
            ]
        ))
        
        return recommendations
