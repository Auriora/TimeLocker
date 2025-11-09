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

"""
Performance Optimization Service for Backup Operations

This module provides comprehensive performance optimization capabilities including:
- Performance optimization algorithms for backup tool configuration
- Performance comparison system between different backup tools
- Bottleneck identification and automatic configuration adjustment suggestions
- Integration with existing performance monitoring infrastructure
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict

from ..interfaces.data_models import BackupJob, BackupResult, ToolConfiguration
from ..performance.metrics import PerformanceMetrics, OperationMetrics
from .tool_manager import ToolManager, ToolCapabilities, Feature
from .parallel_execution_optimizer import (
    ParallelExecutionOptimizer,
    SystemResources,
    ResourceConstraintLevel
)

logger = logging.getLogger(__name__)


class BottleneckType(Enum):
    """Types of performance bottlenecks"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK = "network"
    TOOL_LIMITATION = "tool_limitation"
    CONFIGURATION = "configuration"
    PARALLELISM = "parallelism"
    COMPRESSION = "compression"


class OptimizationPriority(Enum):
    """Priority levels for optimization recommendations"""
    CRITICAL = "critical"  # Severe performance impact
    HIGH = "high"  # Significant performance impact
    MEDIUM = "medium"  # Moderate performance impact
    LOW = "low"  # Minor performance impact


@dataclass
class PerformanceBottleneck:
    """
    Represents an identified performance bottleneck.
    
    Attributes:
        bottleneck_type: Type of bottleneck
        severity: Severity level (0.0-1.0, higher is worse)
        description: Human-readable description
        impact_estimate: Estimated performance impact
        detected_at: When bottleneck was detected
        metrics: Related performance metrics
    """
    bottleneck_type: BottleneckType
    severity: float
    description: str
    impact_estimate: str
    detected_at: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationRecommendation:
    """
    Represents a performance optimization recommendation.
    
    Attributes:
        priority: Recommendation priority
        category: Category of optimization
        recommendation: Recommendation text
        expected_improvement: Expected performance improvement
        implementation_complexity: Implementation complexity (low, medium, high)
        configuration_changes: Suggested configuration changes
        related_bottlenecks: Related bottlenecks this addresses
    """
    priority: OptimizationPriority
    category: str
    recommendation: str
    expected_improvement: str
    implementation_complexity: str = "medium"
    configuration_changes: Dict[str, Any] = field(default_factory=dict)
    related_bottlenecks: List[BottleneckType] = field(default_factory=list)


@dataclass
class ToolPerformanceComparison:
    """
    Comparison of performance between different backup tools.
    
    Attributes:
        tool_name: Name of the tool
        avg_throughput_mbps: Average throughput in MB/s
        avg_duration_seconds: Average operation duration
        parallel_efficiency: Parallel execution efficiency
        resource_usage: Average resource usage
        reliability_score: Reliability score (0.0-1.0)
        feature_score: Feature completeness score (0.0-1.0)
        overall_score: Overall performance score (0.0-1.0)
        sample_count: Number of operations in sample
    """
    tool_name: str
    avg_throughput_mbps: float
    avg_duration_seconds: float
    parallel_efficiency: float
    resource_usage: Dict[str, float]
    reliability_score: float
    feature_score: float
    overall_score: float
    sample_count: int


@dataclass
class PerformanceOptimizationReport:
    """
    Comprehensive performance optimization report.
    
    Attributes:
        operation_id: Operation identifier
        tool_type: Backup tool type
        current_performance: Current performance metrics
        identified_bottlenecks: List of identified bottlenecks
        recommendations: List of optimization recommendations
        tool_comparison: Comparison with other tools
        estimated_improvement: Estimated overall improvement
        generated_at: Report generation timestamp
    """
    operation_id: str
    tool_type: str
    current_performance: Dict[str, Any]
    identified_bottlenecks: List[PerformanceBottleneck]
    recommendations: List[OptimizationRecommendation]
    tool_comparison: Optional[List[ToolPerformanceComparison]]
    estimated_improvement: str
    generated_at: datetime = field(default_factory=datetime.now)


class PerformanceOptimizationService:
    """
    Service for performance optimization and monitoring of backup operations.
    
    This service provides:
    - Performance optimization algorithms for backup tool configuration
    - Performance comparison between different backup tools
    - Bottleneck identification and analysis
    - Automatic configuration adjustment suggestions
    - Integration with performance monitoring infrastructure
    """
    
    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        parallel_optimizer: Optional[ParallelExecutionOptimizer] = None,
        performance_metrics: Optional[PerformanceMetrics] = None
    ):
        """
        Initialize performance optimization service.
        
        Args:
            tool_manager: Tool manager for capability information
            parallel_optimizer: Parallel execution optimizer
            performance_metrics: Performance metrics collector
        """
        self._tool_manager = tool_manager or ToolManager()
        self._parallel_optimizer = parallel_optimizer or ParallelExecutionOptimizer()
        self._performance_metrics = performance_metrics or PerformanceMetrics()
        
        # Track optimization history
        self._optimization_history: Dict[str, List[PerformanceOptimizationReport]] = defaultdict(list)
        
        logger.debug("PerformanceOptimizationService initialized")
    
    def optimize_tool_configuration(
        self,
        job: BackupJob,
        historical_metrics: Optional[List[OperationMetrics]] = None
    ) -> ToolConfiguration:
        """
        Optimize backup tool configuration based on job requirements and historical data.
        
        This method analyzes the job requirements, tool capabilities, system resources,
        and historical performance data to create an optimized tool configuration.
        
        Args:
            job: Backup job to optimize for
            historical_metrics: Optional historical performance metrics
            
        Returns:
            Optimized ToolConfiguration
        """
        logger.info(f"Optimizing tool configuration for job {job.config.job_id}")
        
        # Get tool capabilities
        capabilities = self._tool_manager.get_tool_capabilities(job.config.tool_type)
        
        # Get current system resources
        system_resources = self._parallel_optimizer.get_system_resources()
        
        # Start with base configuration
        config = job.tool_configuration or ToolConfiguration(tool_type=job.config.tool_type)
        
        # Optimize parallelism
        config = self._optimize_parallelism(config, capabilities, job, system_resources)
        
        # Optimize compression
        config = self._optimize_compression(config, capabilities, job, historical_metrics)
        
        # Optimize I/O settings
        config = self._optimize_io_settings(config, capabilities, system_resources)
        
        # Optimize memory usage
        config = self._optimize_memory_settings(config, capabilities, system_resources)
        
        # Add tool-specific optimizations
        config = self._apply_tool_specific_optimizations(
            config,
            capabilities,
            job,
            historical_metrics
        )
        
        logger.info(
            f"Configuration optimized: parallel={config.parallel_operations}, "
            f"compression={config.compression_level}"
        )
        
        return config
    
    def identify_bottlenecks(
        self,
        operation_id: str,
        metrics: OperationMetrics,
        system_resources: Optional[SystemResources] = None
    ) -> List[PerformanceBottleneck]:
        """
        Identify performance bottlenecks for an operation.
        
        Args:
            operation_id: Operation identifier
            metrics: Operation performance metrics
            system_resources: Optional system resource information
            
        Returns:
            List of identified bottlenecks
        """
        logger.debug(f"Identifying bottlenecks for operation {operation_id}")
        
        bottlenecks = []
        
        # Get system resources if not provided
        if system_resources is None:
            system_resources = self._parallel_optimizer.get_system_resources()
        
        # Check for CPU bottleneck
        if system_resources.cpu_usage_percent > 85:
            bottlenecks.append(PerformanceBottleneck(
                bottleneck_type=BottleneckType.CPU,
                severity=min(1.0, system_resources.cpu_usage_percent / 100),
                description=f"High CPU usage: {system_resources.cpu_usage_percent:.1f}%",
                impact_estimate="20-40% throughput reduction",
                metrics={'cpu_usage': system_resources.cpu_usage_percent}
            ))
        
        # Check for memory bottleneck
        if system_resources.memory_usage_percent > 85:
            bottlenecks.append(PerformanceBottleneck(
                bottleneck_type=BottleneckType.MEMORY,
                severity=min(1.0, system_resources.memory_usage_percent / 100),
                description=f"High memory usage: {system_resources.memory_usage_percent:.1f}%",
                impact_estimate="30-50% throughput reduction due to swapping",
                metrics={'memory_usage': system_resources.memory_usage_percent}
            ))
        
        # Check for disk I/O bottleneck
        if system_resources.disk_io_busy_percent > 80:
            bottlenecks.append(PerformanceBottleneck(
                bottleneck_type=BottleneckType.DISK_IO,
                severity=min(1.0, system_resources.disk_io_busy_percent / 100),
                description=f"High disk I/O: {system_resources.disk_io_busy_percent:.1f}%",
                impact_estimate="40-60% throughput reduction",
                metrics={'disk_io_busy': system_resources.disk_io_busy_percent}
            ))
        
        # Check for low throughput
        if metrics.duration_seconds and metrics.duration_seconds > 0:
            throughput_mbps = (metrics.bytes_processed / (1024 * 1024)) / metrics.duration_seconds
            
            # Expected minimum throughput: 10 MB/s for local, 5 MB/s for network
            expected_min_throughput = 10.0
            
            if throughput_mbps < expected_min_throughput:
                severity = 1.0 - (throughput_mbps / expected_min_throughput)
                bottlenecks.append(PerformanceBottleneck(
                    bottleneck_type=BottleneckType.CONFIGURATION,
                    severity=severity,
                    description=f"Low throughput: {throughput_mbps:.2f} MB/s",
                    impact_estimate=f"Operating at {(throughput_mbps/expected_min_throughput)*100:.0f}% of expected performance",
                    metrics={'throughput_mbps': throughput_mbps}
                ))
        
        # Check parallel execution metrics if available
        parallel_metrics = self._parallel_optimizer.get_execution_metrics(operation_id)
        if parallel_metrics:
            if parallel_metrics.parallel_efficiency < 0.6:
                bottlenecks.append(PerformanceBottleneck(
                    bottleneck_type=BottleneckType.PARALLELISM,
                    severity=1.0 - parallel_metrics.parallel_efficiency,
                    description=f"Low parallel efficiency: {parallel_metrics.parallel_efficiency:.2f}",
                    impact_estimate="Parallel operations not scaling effectively",
                    metrics={
                        'configured_parallelism': parallel_metrics.configured_parallelism,
                        'actual_parallelism': parallel_metrics.actual_parallelism,
                        'efficiency': parallel_metrics.parallel_efficiency
                    }
                ))
        
        logger.info(f"Identified {len(bottlenecks)} bottlenecks for operation {operation_id}")
        
        return bottlenecks
    
    def generate_optimization_recommendations(
        self,
        job: BackupJob,
        metrics: OperationMetrics,
        bottlenecks: List[PerformanceBottleneck]
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on identified bottlenecks.
        
        Args:
            job: Backup job
            metrics: Operation metrics
            bottlenecks: Identified bottlenecks
            
        Returns:
            List of optimization recommendations
        """
        logger.debug(f"Generating optimization recommendations for job {job.config.job_id}")
        
        recommendations = []
        capabilities = self._tool_manager.get_tool_capabilities(job.config.tool_type)
        
        # Process each bottleneck
        for bottleneck in bottlenecks:
            if bottleneck.bottleneck_type == BottleneckType.CPU:
                recommendations.extend(self._recommend_cpu_optimizations(
                    bottleneck, job, capabilities
                ))
            
            elif bottleneck.bottleneck_type == BottleneckType.MEMORY:
                recommendations.extend(self._recommend_memory_optimizations(
                    bottleneck, job, capabilities
                ))
            
            elif bottleneck.bottleneck_type == BottleneckType.DISK_IO:
                recommendations.extend(self._recommend_io_optimizations(
                    bottleneck, job, capabilities
                ))
            
            elif bottleneck.bottleneck_type == BottleneckType.PARALLELISM:
                recommendations.extend(self._recommend_parallelism_optimizations(
                    bottleneck, job, capabilities
                ))
            
            elif bottleneck.bottleneck_type == BottleneckType.CONFIGURATION:
                recommendations.extend(self._recommend_configuration_optimizations(
                    bottleneck, job, capabilities, metrics
                ))
        
        # Add general recommendations
        recommendations.extend(self._recommend_general_optimizations(
            job, capabilities, metrics
        ))
        
        # Sort by priority
        recommendations.sort(key=lambda r: (
            ['critical', 'high', 'medium', 'low'].index(r.priority.value)
        ))
        
        logger.info(f"Generated {len(recommendations)} optimization recommendations")
        
        return recommendations
    
    def compare_tool_performance(
        self,
        days: int = 30,
        min_samples: int = 3
    ) -> List[ToolPerformanceComparison]:
        """
        Compare performance between different backup tools.
        
        This method analyzes historical performance data to compare different
        backup tools across multiple dimensions including throughput, reliability,
        and feature completeness.
        
        Args:
            days: Number of days of history to analyze
            min_samples: Minimum number of samples required for comparison
            
        Returns:
            List of tool performance comparisons
        """
        logger.info(f"Comparing tool performance over last {days} days")
        
        comparisons = []
        
        # Get supported tools
        supported_tools = self._tool_manager.get_supported_tools()
        
        for tool_info in supported_tools:
            if not tool_info.is_available:
                continue
            
            # Get historical metrics for this tool
            tool_metrics = self._performance_metrics.get_completed_operations(
                operation_type='backup'
            )
            
            # Filter by tool type and time range
            cutoff_date = datetime.now() - timedelta(days=days)
            tool_metrics = [
                m for m in tool_metrics
                if m.metadata.get('tool_type') == tool_info.tool_name
                and m.start_time >= cutoff_date
            ]
            
            if len(tool_metrics) < min_samples:
                logger.debug(
                    f"Insufficient samples for {tool_info.tool_name}: "
                    f"{len(tool_metrics)} < {min_samples}"
                )
                continue
            
            # Calculate performance metrics
            comparison = self._calculate_tool_comparison(
                tool_info.tool_name,
                tool_metrics
            )
            
            comparisons.append(comparison)
        
        # Sort by overall score
        comparisons.sort(key=lambda c: c.overall_score, reverse=True)
        
        logger.info(f"Compared {len(comparisons)} tools")
        
        return comparisons
    
    def generate_performance_report(
        self,
        operation_id: str,
        job: BackupJob,
        result: BackupResult,
        include_tool_comparison: bool = True
    ) -> PerformanceOptimizationReport:
        """
        Generate comprehensive performance optimization report.
        
        Args:
            operation_id: Operation identifier
            job: Backup job
            result: Backup result
            include_tool_comparison: Whether to include tool comparison
            
        Returns:
            PerformanceOptimizationReport with analysis and recommendations
        """
        logger.info(f"Generating performance report for operation {operation_id}")
        
        # Get operation metrics
        metrics = self._performance_metrics.get_operation_metrics(operation_id)
        if not metrics:
            # Create metrics from result
            metrics = OperationMetrics(
                operation_id=operation_id,
                operation_type='backup',
                start_time=datetime.fromtimestamp(result.start_time),
                end_time=datetime.fromtimestamp(result.end_time) if result.end_time else None,
                duration_seconds=result.duration,
                files_processed=result.files_processed,
                bytes_processed=result.bytes_processed,
                errors_count=len(result.errors),
                metadata={'tool_type': job.config.tool_type}
            )
        
        # Get system resources
        system_resources = self._parallel_optimizer.get_system_resources()
        
        # Identify bottlenecks
        bottlenecks = self.identify_bottlenecks(operation_id, metrics, system_resources)
        
        # Generate recommendations
        recommendations = self.generate_optimization_recommendations(
            job, metrics, bottlenecks
        )
        
        # Get tool comparison if requested
        tool_comparison = None
        if include_tool_comparison:
            tool_comparison = self.compare_tool_performance()
        
        # Calculate current performance
        current_performance = {
            'throughput_mbps': (
                (metrics.bytes_processed / (1024 * 1024)) / metrics.duration_seconds
                if metrics.duration_seconds and metrics.duration_seconds > 0
                else 0
            ),
            'duration_seconds': metrics.duration_seconds,
            'files_per_second': (
                metrics.files_processed / metrics.duration_seconds
                if metrics.duration_seconds and metrics.duration_seconds > 0
                else 0
            ),
            'resource_usage': {
                'cpu_percent': system_resources.cpu_usage_percent,
                'memory_percent': system_resources.memory_usage_percent,
                'disk_io_percent': system_resources.disk_io_busy_percent
            }
        }
        
        # Estimate potential improvement
        estimated_improvement = self._estimate_improvement(
            bottlenecks, recommendations
        )
        
        report = PerformanceOptimizationReport(
            operation_id=operation_id,
            tool_type=job.config.tool_type,
            current_performance=current_performance,
            identified_bottlenecks=bottlenecks,
            recommendations=recommendations,
            tool_comparison=tool_comparison,
            estimated_improvement=estimated_improvement
        )
        
        # Store in history
        self._optimization_history[operation_id].append(report)
        
        logger.info(
            f"Performance report generated: {len(bottlenecks)} bottlenecks, "
            f"{len(recommendations)} recommendations"
        )
        
        return report
    
    def apply_automatic_adjustments(
        self,
        job: BackupJob,
        report: PerformanceOptimizationReport
    ) -> ToolConfiguration:
        """
        Apply automatic configuration adjustments based on optimization report.
        
        This method automatically applies safe, high-priority optimizations
        to the tool configuration.
        
        Args:
            job: Backup job
            report: Performance optimization report
            
        Returns:
            Adjusted ToolConfiguration
        """
        logger.info(f"Applying automatic adjustments for job {job.config.job_id}")
        
        config = job.tool_configuration or ToolConfiguration(tool_type=job.config.tool_type)
        adjustments_applied = []
        
        # Apply high-priority recommendations with low implementation complexity
        for recommendation in report.recommendations:
            if (recommendation.priority in [OptimizationPriority.CRITICAL, OptimizationPriority.HIGH]
                and recommendation.implementation_complexity == "low"):
                
                # Apply configuration changes
                for key, value in recommendation.configuration_changes.items():
                    if hasattr(config, key):
                        old_value = getattr(config, key)
                        setattr(config, key, value)
                        adjustments_applied.append(
                            f"{key}: {old_value} -> {value}"
                        )
                        logger.info(f"Applied adjustment: {key} = {value}")
                    elif key in config.tool_specific_options:
                        old_value = config.tool_specific_options[key]
                        config.tool_specific_options[key] = value
                        adjustments_applied.append(
                            f"{key}: {old_value} -> {value}"
                        )
                        logger.info(f"Applied tool-specific adjustment: {key} = {value}")
        
        if adjustments_applied:
            logger.info(
                f"Applied {len(adjustments_applied)} automatic adjustments: "
                f"{', '.join(adjustments_applied)}"
            )
        else:
            logger.info("No automatic adjustments applied")
        
        return config
    
    def _optimize_parallelism(
        self,
        config: ToolConfiguration,
        capabilities: ToolCapabilities,
        job: BackupJob,
        system_resources: SystemResources
    ) -> ToolConfiguration:
        """Optimize parallelism settings"""
        if capabilities.has_feature(Feature.PARALLEL_PROCESSING):
            parallel_config = self._parallel_optimizer.calculate_optimal_parallelism(
                capabilities, job, system_resources
            )
            config.parallel_operations = parallel_config.parallel_operations
            
            # Store optimization details
            config.tool_specific_options['parallel_optimization'] = {
                'reason': parallel_config.optimization_reason,
                'recommendations': parallel_config.recommendations
            }
        
        return config
    
    def _optimize_compression(
        self,
        config: ToolConfiguration,
        capabilities: ToolCapabilities,
        job: BackupJob,
        historical_metrics: Optional[List[OperationMetrics]]
    ) -> ToolConfiguration:
        """Optimize compression settings"""
        if not capabilities.has_feature(Feature.COMPRESSION):
            return config
        
        # Analyze historical data if available
        if historical_metrics:
            # Find optimal compression level based on throughput vs size tradeoff
            compression_analysis = self._analyze_compression_performance(
                historical_metrics
            )
            if compression_analysis:
                config.compression_level = compression_analysis['optimal_level']
                return config
        
        # Use heuristics based on job priority and tool characteristics
        overhead = capabilities.performance_characteristics.compression_overhead
        
        if job.config.priority > 7:
            # High priority: favor speed
            config.compression_level = 1 if overhead == "high" else 3
        elif job.config.priority < 3:
            # Low priority: favor compression
            config.compression_level = 7 if overhead == "low" else 5
        else:
            # Balanced
            config.compression_level = 4 if overhead == "low" else 3
        
        return config
    
    def _optimize_io_settings(
        self,
        config: ToolConfiguration,
        capabilities: ToolCapabilities,
        system_resources: SystemResources
    ) -> ToolConfiguration:
        """Optimize I/O settings"""
        # Adjust based on disk I/O load
        if system_resources.disk_io_busy_percent > 70:
            # High I/O load: reduce I/O intensity
            config.tool_specific_options['io_priority'] = 'low'
            config.tool_specific_options['read_ahead'] = False
        else:
            # Normal I/O load: optimize for throughput
            config.tool_specific_options['io_priority'] = 'normal'
            config.tool_specific_options['read_ahead'] = True
        
        return config
    
    def _optimize_memory_settings(
        self,
        config: ToolConfiguration,
        capabilities: ToolCapabilities,
        system_resources: SystemResources
    ) -> ToolConfiguration:
        """Optimize memory settings"""
        # Adjust buffer sizes based on available memory
        available_gb = system_resources.memory_available_gb
        
        if available_gb > 8:
            # Plenty of memory: use larger buffers
            config.tool_specific_options['buffer_size_mb'] = 256
        elif available_gb > 4:
            # Moderate memory: balanced buffers
            config.tool_specific_options['buffer_size_mb'] = 128
        else:
            # Limited memory: smaller buffers
            config.tool_specific_options['buffer_size_mb'] = 64
        
        return config
    
    def _apply_tool_specific_optimizations(
        self,
        config: ToolConfiguration,
        capabilities: ToolCapabilities,
        job: BackupJob,
        historical_metrics: Optional[List[OperationMetrics]]
    ) -> ToolConfiguration:
        """Apply tool-specific optimizations"""
        tool_name = capabilities.tool_name
        
        if tool_name == "restic":
            # Restic-specific optimizations
            config.tool_specific_options['pack_size'] = 128  # MB
            config.tool_specific_options['exclude_caches'] = True
            
            if capabilities.configuration_options.get('supports_read_concurrency'):
                # Optimize read concurrency based on parallelism
                config.tool_specific_options['read_concurrency'] = min(
                    config.parallel_operations * 2,
                    16
                )
        
        elif tool_name == "borg":
            # Borg-specific optimizations
            config.tool_specific_options['compression'] = 'lz4'  # Fast compression
            
            if capabilities.configuration_options.get('supports_checkpoint_interval'):
                # Set checkpoint interval for large backups
                config.tool_specific_options['checkpoint_interval'] = 300  # seconds
        
        elif tool_name == "duplicity":
            # Duplicity-specific optimizations
            if capabilities.configuration_options.get('supports_volsize'):
                config.tool_specific_options['volsize'] = 200  # MB
        
        return config
    
    def _recommend_cpu_optimizations(
        self,
        bottleneck: PerformanceBottleneck,
        job: BackupJob,
        capabilities: ToolCapabilities
    ) -> List[OptimizationRecommendation]:
        """Generate CPU optimization recommendations"""
        recommendations = []
        
        if bottleneck.severity > 0.9:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.CRITICAL,
                category="CPU",
                recommendation="Reduce compression level to decrease CPU usage",
                expected_improvement="20-40% CPU reduction, 10-20% throughput increase",
                implementation_complexity="low",
                configuration_changes={'compression_level': 1},
                related_bottlenecks=[BottleneckType.CPU]
            ))
        
        if capabilities.has_feature(Feature.PARALLEL_PROCESSING):
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.HIGH,
                category="CPU",
                recommendation="Reduce parallel operations to lower CPU contention",
                expected_improvement="15-30% CPU reduction",
                implementation_complexity="low",
                configuration_changes={
                    'parallel_operations': max(1, job.tool_configuration.parallel_operations // 2)
                },
                related_bottlenecks=[BottleneckType.CPU]
            ))
        
        return recommendations
    
    def _recommend_memory_optimizations(
        self,
        bottleneck: PerformanceBottleneck,
        job: BackupJob,
        capabilities: ToolCapabilities
    ) -> List[OptimizationRecommendation]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        recommendations.append(OptimizationRecommendation(
            priority=OptimizationPriority.HIGH,
            category="Memory",
            recommendation="Reduce buffer sizes to decrease memory usage",
            expected_improvement="30-50% memory reduction",
            implementation_complexity="low",
            configuration_changes={'buffer_size_mb': 64},
            related_bottlenecks=[BottleneckType.MEMORY]
        ))
        
        if capabilities.has_feature(Feature.PARALLEL_PROCESSING):
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.HIGH,
                category="Memory",
                recommendation="Reduce parallel operations to lower memory usage",
                expected_improvement="20-40% memory reduction",
                implementation_complexity="low",
                configuration_changes={
                    'parallel_operations': max(1, job.tool_configuration.parallel_operations // 2)
                },
                related_bottlenecks=[BottleneckType.MEMORY]
            ))
        
        return recommendations
    
    def _recommend_io_optimizations(
        self,
        bottleneck: PerformanceBottleneck,
        job: BackupJob,
        capabilities: ToolCapabilities
    ) -> List[OptimizationRecommendation]:
        """Generate I/O optimization recommendations"""
        recommendations = []
        
        recommendations.append(OptimizationRecommendation(
            priority=OptimizationPriority.HIGH,
            category="I/O",
            recommendation="Schedule backups during off-peak hours to reduce I/O contention",
            expected_improvement="40-60% throughput increase during off-peak",
            implementation_complexity="medium",
            configuration_changes={},
            related_bottlenecks=[BottleneckType.DISK_IO]
        ))
        
        recommendations.append(OptimizationRecommendation(
            priority=OptimizationPriority.MEDIUM,
            category="I/O",
            recommendation="Consider using faster storage (SSD) for backup cache",
            expected_improvement="50-100% throughput increase",
            implementation_complexity="high",
            configuration_changes={},
            related_bottlenecks=[BottleneckType.DISK_IO]
        ))
        
        return recommendations
    
    def _recommend_parallelism_optimizations(
        self,
        bottleneck: PerformanceBottleneck,
        job: BackupJob,
        capabilities: ToolCapabilities
    ) -> List[OptimizationRecommendation]:
        """Generate parallelism optimization recommendations"""
        recommendations = []
        
        efficiency = bottleneck.metrics.get('efficiency', 0.0)
        
        if efficiency < 0.5:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.HIGH,
                category="Parallelism",
                recommendation="Reduce parallel operations due to poor scaling efficiency",
                expected_improvement="Better resource utilization, 10-20% throughput increase",
                implementation_complexity="low",
                configuration_changes={
                    'parallel_operations': max(1, job.tool_configuration.parallel_operations // 2)
                },
                related_bottlenecks=[BottleneckType.PARALLELISM]
            ))
        
        return recommendations
    
    def _recommend_configuration_optimizations(
        self,
        bottleneck: PerformanceBottleneck,
        job: BackupJob,
        capabilities: ToolCapabilities,
        metrics: OperationMetrics
    ) -> List[OptimizationRecommendation]:
        """Generate configuration optimization recommendations"""
        recommendations = []
        
        throughput = bottleneck.metrics.get('throughput_mbps', 0.0)
        
        if throughput < 5.0:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.CRITICAL,
                category="Configuration",
                recommendation="Review and optimize backup tool configuration for better throughput",
                expected_improvement="50-100% throughput increase",
                implementation_complexity="medium",
                configuration_changes={},
                related_bottlenecks=[BottleneckType.CONFIGURATION]
            ))
        
        return recommendations
    
    def _recommend_general_optimizations(
        self,
        job: BackupJob,
        capabilities: ToolCapabilities,
        metrics: OperationMetrics
    ) -> List[OptimizationRecommendation]:
        """Generate general optimization recommendations"""
        recommendations = []
        
        # Check if tool has low parallel efficiency
        if capabilities.performance_characteristics.parallel_efficiency < 0.6:
            recommendations.append(OptimizationRecommendation(
                priority=OptimizationPriority.MEDIUM,
                category="Tool Selection",
                recommendation=f"Consider switching to a tool with better parallel performance for large datasets",
                expected_improvement="30-50% throughput increase",
                implementation_complexity="high",
                configuration_changes={},
                related_bottlenecks=[BottleneckType.TOOL_LIMITATION]
            ))
        
        return recommendations
    
    def _calculate_tool_comparison(
        self,
        tool_name: str,
        metrics: List[OperationMetrics]
    ) -> ToolPerformanceComparison:
        """Calculate performance comparison for a tool"""
        # Calculate average throughput
        throughputs = []
        durations = []
        
        for m in metrics:
            if m.duration_seconds and m.duration_seconds > 0:
                throughput = (m.bytes_processed / (1024 * 1024)) / m.duration_seconds
                throughputs.append(throughput)
                durations.append(m.duration_seconds)
        
        avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0.0
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate reliability score (based on error rate)
        total_ops = len(metrics)
        failed_ops = sum(1 for m in metrics if m.errors_count > 0)
        reliability_score = 1.0 - (failed_ops / total_ops) if total_ops > 0 else 0.0
        
        # Get tool capabilities for feature score
        capabilities = self._tool_manager.get_tool_capabilities(tool_name)
        feature_score = len(capabilities.all_features) / 20.0  # Normalize to 0-1
        
        # Get parallel efficiency
        parallel_efficiency = capabilities.performance_characteristics.parallel_efficiency
        
        # Calculate overall score (weighted average)
        overall_score = (
            avg_throughput * 0.3 +  # Throughput weight
            reliability_score * 100 * 0.3 +  # Reliability weight
            parallel_efficiency * 100 * 0.2 +  # Parallel efficiency weight
            feature_score * 100 * 0.2  # Feature completeness weight
        ) / 100
        
        return ToolPerformanceComparison(
            tool_name=tool_name,
            avg_throughput_mbps=avg_throughput,
            avg_duration_seconds=avg_duration,
            parallel_efficiency=parallel_efficiency,
            resource_usage={
                'cpu': capabilities.performance_characteristics.cpu_usage,
                'memory': capabilities.performance_characteristics.memory_usage
            },
            reliability_score=reliability_score,
            feature_score=feature_score,
            overall_score=overall_score,
            sample_count=len(metrics)
        )
    
    def _analyze_compression_performance(
        self,
        metrics: List[OperationMetrics]
    ) -> Optional[Dict[str, Any]]:
        """Analyze compression performance from historical data"""
        # Group metrics by compression level
        by_compression = defaultdict(list)
        
        for m in metrics:
            compression_level = m.metadata.get('compression_level')
            if compression_level is not None and m.duration_seconds:
                throughput = (m.bytes_processed / (1024 * 1024)) / m.duration_seconds
                by_compression[compression_level].append(throughput)
        
        if not by_compression:
            return None
        
        # Find optimal compression level (best throughput)
        optimal_level = None
        best_throughput = 0.0
        
        for level, throughputs in by_compression.items():
            avg_throughput = sum(throughputs) / len(throughputs)
            if avg_throughput > best_throughput:
                best_throughput = avg_throughput
                optimal_level = level
        
        return {
            'optimal_level': optimal_level,
            'best_throughput': best_throughput,
            'analysis': by_compression
        }
    
    def _estimate_improvement(
        self,
        bottlenecks: List[PerformanceBottleneck],
        recommendations: List[OptimizationRecommendation]
    ) -> str:
        """Estimate potential performance improvement"""
        if not bottlenecks:
            return "No significant bottlenecks identified"
        
        # Calculate severity score
        total_severity = sum(b.severity for b in bottlenecks)
        avg_severity = total_severity / len(bottlenecks)
        
        # Count high-priority recommendations
        high_priority_count = sum(
            1 for r in recommendations
            if r.priority in [OptimizationPriority.CRITICAL, OptimizationPriority.HIGH]
        )
        
        if avg_severity > 0.8 and high_priority_count > 2:
            return "50-100% potential improvement with recommended optimizations"
        elif avg_severity > 0.6 and high_priority_count > 1:
            return "30-50% potential improvement with recommended optimizations"
        elif avg_severity > 0.4:
            return "15-30% potential improvement with recommended optimizations"
        else:
            return "10-15% potential improvement with recommended optimizations"
