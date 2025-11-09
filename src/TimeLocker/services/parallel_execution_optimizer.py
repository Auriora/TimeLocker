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
Parallel Execution Optimization for Backup Operations

This module provides parallel execution optimization capabilities that consider
backup tool capabilities, system constraints, and resource availability to
determine optimal parallelization settings for backup operations.
"""

import logging
import os
import psutil
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from ..interfaces.data_models import BackupJob, ToolConfiguration

if TYPE_CHECKING:
    from .tool_manager import ToolCapabilities, Feature

logger = logging.getLogger(__name__)


class ResourceConstraintLevel(Enum):
    """Level of resource constraint on the system"""
    LOW = "low"  # Plenty of resources available
    MEDIUM = "medium"  # Moderate resource usage
    HIGH = "high"  # High resource usage, need to be conservative
    CRITICAL = "critical"  # Critical resource shortage


@dataclass
class SystemResources:
    """
    Current system resource availability.
    
    Attributes:
        cpu_count: Number of CPU cores
        cpu_usage_percent: Current CPU usage percentage
        memory_total_gb: Total system memory in GB
        memory_available_gb: Available memory in GB
        memory_usage_percent: Current memory usage percentage
        disk_io_busy_percent: Disk I/O busy percentage
        network_bandwidth_mbps: Available network bandwidth in Mbps
    """
    cpu_count: int
    cpu_usage_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_usage_percent: float
    disk_io_busy_percent: float = 0.0
    network_bandwidth_mbps: Optional[float] = None
    
    def get_constraint_level(self) -> ResourceConstraintLevel:
        """
        Determine overall resource constraint level.
        
        Returns:
            ResourceConstraintLevel based on current resource usage
        """
        # Check for critical constraints
        if (self.cpu_usage_percent > 90 or 
            self.memory_usage_percent > 90 or 
            self.disk_io_busy_percent > 90):
            return ResourceConstraintLevel.CRITICAL
        
        # Check for high constraints
        if (self.cpu_usage_percent > 75 or 
            self.memory_usage_percent > 75 or 
            self.disk_io_busy_percent > 75):
            return ResourceConstraintLevel.HIGH
        
        # Check for medium constraints
        if (self.cpu_usage_percent > 50 or 
            self.memory_usage_percent > 50 or 
            self.disk_io_busy_percent > 50):
            return ResourceConstraintLevel.MEDIUM
        
        return ResourceConstraintLevel.LOW


@dataclass
class ParallelizationConfig:
    """
    Configuration for parallel execution.
    
    Attributes:
        parallel_operations: Number of parallel operations to use
        max_parallel_operations: Maximum allowed parallel operations
        resource_constraint_level: Current resource constraint level
        optimization_reason: Reason for the chosen parallelization level
        degradation_applied: Whether graceful degradation was applied
        recommendations: List of optimization recommendations
    """
    parallel_operations: int
    max_parallel_operations: int
    resource_constraint_level: ResourceConstraintLevel
    optimization_reason: str
    degradation_applied: bool = False
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ParallelExecutionMetrics:
    """
    Metrics for parallel execution monitoring.
    
    Attributes:
        operation_id: Unique operation identifier
        configured_parallelism: Configured parallelism level
        actual_parallelism: Actual parallelism achieved
        parallel_efficiency: Efficiency of parallel operations (0.0-1.0)
        resource_usage: Resource usage during execution
        bottlenecks: Identified bottlenecks
        degradation_events: Number of times degradation was applied
    """
    operation_id: str
    configured_parallelism: int
    actual_parallelism: int = 0
    parallel_efficiency: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    bottlenecks: List[str] = field(default_factory=list)
    degradation_events: int = 0


class ParallelExecutionOptimizer:
    """
    Optimizes parallel execution based on tool capabilities and system resources.
    
    This class provides:
    - Resource-aware parallelization configuration
    - Dynamic adjustment based on system constraints
    - Graceful degradation when resources are limited
    - Performance monitoring and bottleneck identification
    """
    
    def __init__(self, 
                 enable_dynamic_adjustment: bool = True,
                 min_parallel_operations: int = 1,
                 max_parallel_operations: int = 16):
        """
        Initialize parallel execution optimizer.
        
        Args:
            enable_dynamic_adjustment: Enable dynamic parallelism adjustment
            min_parallel_operations: Minimum parallel operations
            max_parallel_operations: Maximum parallel operations
        """
        self.enable_dynamic_adjustment = enable_dynamic_adjustment
        self.min_parallel_operations = min_parallel_operations
        self.max_parallel_operations = max_parallel_operations
        
        # Track execution metrics
        self._execution_metrics: Dict[str, ParallelExecutionMetrics] = {}
        
        logger.debug(
            f"ParallelExecutionOptimizer initialized: "
            f"dynamic_adjustment={enable_dynamic_adjustment}, "
            f"min={min_parallel_operations}, max={max_parallel_operations}"
        )
    
    def calculate_optimal_parallelism(
        self,
        capabilities: 'ToolCapabilities',
        job: BackupJob,
        system_resources: Optional[SystemResources] = None
    ) -> ParallelizationConfig:
        """
        Calculate optimal parallelization configuration.
        
        This method analyzes tool capabilities, job requirements, and system
        resources to determine the optimal number of parallel operations.
        
        Args:
            capabilities: Backup tool capabilities
            job: Backup job to optimize for
            system_resources: Optional system resource information
            
        Returns:
            ParallelizationConfig with optimization details
        """
        logger.debug(f"Calculating optimal parallelism for job {job.config.job_id}")
        
        # Import Feature here to avoid circular import
        from .tool_manager import Feature
        
        # Get current system resources if not provided
        if system_resources is None:
            system_resources = self.get_system_resources()
        
        # Check if tool supports parallel processing
        if not capabilities.has_feature(Feature.PARALLEL_PROCESSING):
            logger.info(
                f"Tool {capabilities.tool_name} does not support parallel processing"
            )
            return ParallelizationConfig(
                parallel_operations=1,
                max_parallel_operations=1,
                resource_constraint_level=system_resources.get_constraint_level(),
                optimization_reason="Tool does not support parallel processing",
                recommendations=[
                    "Consider using a tool with parallel processing support for better performance"
                ]
            )
        
        # Get tool-specific limits
        tool_max_parallel = capabilities.configuration_options.get('max_parallel_files', 8)
        tool_efficiency = capabilities.performance_characteristics.parallel_efficiency
        
        # Start with base calculation
        base_parallelism = self._calculate_base_parallelism(
            system_resources,
            tool_efficiency
        )
        
        # Apply tool-specific adjustments
        adjusted_parallelism = self._apply_tool_adjustments(
            base_parallelism,
            capabilities,
            job
        )
        
        # Apply resource constraints
        final_parallelism, degradation_applied = self._apply_resource_constraints(
            adjusted_parallelism,
            system_resources,
            tool_max_parallel
        )
        
        # Ensure within bounds
        final_parallelism = max(
            self.min_parallel_operations,
            min(final_parallelism, self.max_parallel_operations, tool_max_parallel)
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            final_parallelism,
            system_resources,
            capabilities,
            job
        )
        
        config = ParallelizationConfig(
            parallel_operations=final_parallelism,
            max_parallel_operations=tool_max_parallel,
            resource_constraint_level=system_resources.get_constraint_level(),
            optimization_reason=self._generate_optimization_reason(
                final_parallelism,
                base_parallelism,
                system_resources,
                capabilities
            ),
            degradation_applied=degradation_applied,
            recommendations=recommendations
        )
        
        logger.info(
            f"Optimal parallelism calculated: {final_parallelism} "
            f"(base={base_parallelism}, constraint={system_resources.get_constraint_level().value})"
        )
        
        return config
    
    def get_system_resources(self) -> SystemResources:
        """
        Get current system resource availability.
        
        Returns:
            SystemResources with current resource information
        """
        try:
            # Get CPU information
            cpu_count = psutil.cpu_count(logical=True) or 1
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Get memory information
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024 ** 3)
            memory_available_gb = memory.available / (1024 ** 3)
            memory_usage_percent = memory.percent
            
            # Get disk I/O information
            disk_io_busy = 0.0
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    # Simplified disk busy calculation
                    # In production, this would track I/O over time
                    disk_io_busy = min(50.0, cpu_usage * 0.5)  # Rough estimate
            except Exception as e:
                logger.debug(f"Could not get disk I/O stats: {e}")
            
            resources = SystemResources(
                cpu_count=cpu_count,
                cpu_usage_percent=cpu_usage,
                memory_total_gb=memory_total_gb,
                memory_available_gb=memory_available_gb,
                memory_usage_percent=memory_usage_percent,
                disk_io_busy_percent=disk_io_busy
            )
            
            logger.debug(
                f"System resources: CPU={cpu_usage:.1f}%, "
                f"Memory={memory_usage_percent:.1f}%, "
                f"Available={memory_available_gb:.1f}GB"
            )
            
            return resources
            
        except Exception as e:
            logger.warning(f"Could not get system resources: {e}")
            # Return conservative defaults
            return SystemResources(
                cpu_count=2,
                cpu_usage_percent=50.0,
                memory_total_gb=4.0,
                memory_available_gb=2.0,
                memory_usage_percent=50.0
            )
    
    def start_execution_monitoring(
        self,
        operation_id: str,
        configured_parallelism: int
    ) -> ParallelExecutionMetrics:
        """
        Start monitoring parallel execution.
        
        Args:
            operation_id: Unique operation identifier
            configured_parallelism: Configured parallelism level
            
        Returns:
            ParallelExecutionMetrics for tracking
        """
        metrics = ParallelExecutionMetrics(
            operation_id=operation_id,
            configured_parallelism=configured_parallelism
        )
        
        self._execution_metrics[operation_id] = metrics
        
        logger.debug(
            f"Started execution monitoring for {operation_id} "
            f"with parallelism={configured_parallelism}"
        )
        
        return metrics
    
    def update_execution_metrics(
        self,
        operation_id: str,
        actual_parallelism: Optional[int] = None,
        resource_usage: Optional[Dict[str, float]] = None,
        bottleneck: Optional[str] = None
    ) -> None:
        """
        Update execution metrics during operation.
        
        Args:
            operation_id: Operation identifier
            actual_parallelism: Actual parallelism achieved
            resource_usage: Current resource usage
            bottleneck: Identified bottleneck
        """
        if operation_id not in self._execution_metrics:
            logger.warning(f"No metrics found for operation {operation_id}")
            return
        
        metrics = self._execution_metrics[operation_id]
        
        if actual_parallelism is not None:
            metrics.actual_parallelism = actual_parallelism
            # Calculate efficiency
            if metrics.configured_parallelism > 0:
                metrics.parallel_efficiency = (
                    actual_parallelism / metrics.configured_parallelism
                )
        
        if resource_usage is not None:
            metrics.resource_usage.update(resource_usage)
        
        if bottleneck is not None and bottleneck not in metrics.bottlenecks:
            metrics.bottlenecks.append(bottleneck)
            logger.info(f"Bottleneck identified for {operation_id}: {bottleneck}")
    
    def apply_graceful_degradation(
        self,
        operation_id: str,
        current_parallelism: int,
        reason: str
    ) -> int:
        """
        Apply graceful degradation to reduce parallelism.
        
        This method reduces parallelism when resource constraints are detected
        or parallel operations are failing.
        
        Args:
            operation_id: Operation identifier
            current_parallelism: Current parallelism level
            reason: Reason for degradation
            
        Returns:
            New reduced parallelism level
        """
        # Reduce by 50% but not below minimum
        new_parallelism = max(
            self.min_parallel_operations,
            current_parallelism // 2
        )
        
        logger.warning(
            f"Applying graceful degradation for {operation_id}: "
            f"{current_parallelism} -> {new_parallelism}. Reason: {reason}"
        )
        
        # Update metrics
        if operation_id in self._execution_metrics:
            metrics = self._execution_metrics[operation_id]
            metrics.degradation_events += 1
            metrics.bottlenecks.append(f"Degradation: {reason}")
        
        return new_parallelism
    
    def get_execution_metrics(self, operation_id: str) -> Optional[ParallelExecutionMetrics]:
        """
        Get execution metrics for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            ParallelExecutionMetrics if found, None otherwise
        """
        return self._execution_metrics.get(operation_id)
    
    def _calculate_base_parallelism(
        self,
        resources: SystemResources,
        tool_efficiency: float
    ) -> int:
        """
        Calculate base parallelism from system resources.
        
        Args:
            resources: System resources
            tool_efficiency: Tool parallel efficiency (0.0-1.0)
            
        Returns:
            Base parallelism level
        """
        # Start with CPU count as base
        base = resources.cpu_count
        
        # Adjust for tool efficiency
        # High efficiency tools can use more parallelism
        if tool_efficiency > 0.8:
            base = int(base * 1.5)
        elif tool_efficiency < 0.5:
            base = max(1, int(base * 0.5))
        
        # Adjust for available memory
        # Assume each parallel operation needs ~500MB
        memory_based_limit = int(resources.memory_available_gb * 2)
        base = min(base, memory_based_limit)
        
        return max(1, base)
    
    def _apply_tool_adjustments(
        self,
        base_parallelism: int,
        capabilities: 'ToolCapabilities',
        job: BackupJob
    ) -> int:
        """
        Apply tool-specific adjustments to parallelism.
        
        Args:
            base_parallelism: Base parallelism level
            capabilities: Tool capabilities
            job: Backup job
            
        Returns:
            Adjusted parallelism level
        """
        adjusted = base_parallelism
        
        # Adjust based on job priority
        if job.config.priority > 7:
            # High priority jobs get more parallelism
            adjusted = int(adjusted * 1.5)
        elif job.config.priority < 3:
            # Low priority jobs get less parallelism
            adjusted = max(1, int(adjusted * 0.5))
        
        # Adjust based on compression overhead
        compression_overhead = capabilities.performance_characteristics.compression_overhead
        if compression_overhead == "high":
            # High compression overhead reduces effective parallelism
            adjusted = max(1, int(adjusted * 0.75))
        
        return adjusted
    
    def _apply_resource_constraints(
        self,
        parallelism: int,
        resources: SystemResources,
        tool_max: int
    ) -> tuple[int, bool]:
        """
        Apply resource constraints to parallelism.
        
        Args:
            parallelism: Desired parallelism level
            resources: System resources
            tool_max: Tool maximum parallelism
            
        Returns:
            Tuple of (constrained_parallelism, degradation_applied)
        """
        original = parallelism
        degradation_applied = False
        
        constraint_level = resources.get_constraint_level()
        
        if constraint_level == ResourceConstraintLevel.CRITICAL:
            # Critical constraints - use minimum parallelism
            parallelism = self.min_parallel_operations
            degradation_applied = True
            logger.warning("Critical resource constraints - using minimum parallelism")
        
        elif constraint_level == ResourceConstraintLevel.HIGH:
            # High constraints - reduce by 50%
            parallelism = max(self.min_parallel_operations, parallelism // 2)
            degradation_applied = True
            logger.info("High resource constraints - reducing parallelism by 50%")
        
        elif constraint_level == ResourceConstraintLevel.MEDIUM:
            # Medium constraints - reduce by 25%
            parallelism = max(self.min_parallel_operations, int(parallelism * 0.75))
            if parallelism < original:
                degradation_applied = True
                logger.info("Medium resource constraints - reducing parallelism by 25%")
        
        # Ensure within tool limits
        parallelism = min(parallelism, tool_max)
        
        return parallelism, degradation_applied
    
    def _generate_recommendations(
        self,
        final_parallelism: int,
        resources: SystemResources,
        capabilities: 'ToolCapabilities',
        job: BackupJob
    ) -> List[str]:
        """
        Generate optimization recommendations.
        
        Args:
            final_parallelism: Final parallelism level
            resources: System resources
            capabilities: Tool capabilities
            job: Backup job
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check if we're limited by resources
        if resources.get_constraint_level() in [
            ResourceConstraintLevel.HIGH,
            ResourceConstraintLevel.CRITICAL
        ]:
            recommendations.append(
                "System resources are constrained. Consider running backups "
                "during off-peak hours for better performance."
            )
        
        # Check if tool efficiency is low
        if capabilities.performance_characteristics.parallel_efficiency < 0.6:
            recommendations.append(
                f"Tool {capabilities.tool_name} has low parallel efficiency. "
                "Consider using a tool with better parallel performance for large datasets."
            )
        
        # Check if parallelism is very low
        if final_parallelism <= 2 and resources.cpu_count > 4:
            recommendations.append(
                "Parallelism is limited. Check system resources and tool configuration "
                "to enable higher parallelism."
            )
        
        # Check memory availability
        if resources.memory_available_gb < 2.0:
            recommendations.append(
                "Low memory available. Consider freeing memory or adding more RAM "
                "for better backup performance."
            )
        
        return recommendations
    
    def _generate_optimization_reason(
        self,
        final_parallelism: int,
        base_parallelism: int,
        resources: SystemResources,
        capabilities: 'ToolCapabilities'
    ) -> str:
        """
        Generate human-readable optimization reason.
        
        Args:
            final_parallelism: Final parallelism level
            base_parallelism: Base parallelism level
            resources: System resources
            capabilities: Tool capabilities
            
        Returns:
            Optimization reason string
        """
        constraint_level = resources.get_constraint_level()
        
        if final_parallelism == base_parallelism:
            return (
                f"Using base parallelism of {final_parallelism} based on "
                f"{resources.cpu_count} CPU cores and tool efficiency of "
                f"{capabilities.performance_characteristics.parallel_efficiency:.2f}"
            )
        elif final_parallelism < base_parallelism:
            return (
                f"Reduced from {base_parallelism} to {final_parallelism} due to "
                f"{constraint_level.value} resource constraints "
                f"(CPU: {resources.cpu_usage_percent:.1f}%, "
                f"Memory: {resources.memory_usage_percent:.1f}%)"
            )
        else:
            return (
                f"Increased from {base_parallelism} to {final_parallelism} based on "
                f"tool capabilities and available resources"
            )
