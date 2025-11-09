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
Tests for Performance Optimization Service

This module tests the performance optimization service functionality including:
- Performance optimization algorithms for backup tool configuration
- Performance comparison between different backup tools
- Bottleneck identification and analysis
- Automatic configuration adjustment suggestions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.services.performance_optimization_service import (
    PerformanceOptimizationService,
    BottleneckType,
    OptimizationPriority,
    PerformanceBottleneck,
    OptimizationRecommendation,
    ToolPerformanceComparison,
    PerformanceOptimizationReport
)
from TimeLocker.services.tool_manager import ToolManager, ToolCapabilities, Feature, PerformanceProfile
from TimeLocker.services.parallel_execution_optimizer import (
    ParallelExecutionOptimizer,
    SystemResources,
    ResourceConstraintLevel
)
from TimeLocker.performance.metrics import PerformanceMetrics, OperationMetrics
from TimeLocker.interfaces.data_models import (
    BackupJob,
    BackupJobConfig,
    BackupResult,
    BackupStatus,
    ToolConfiguration,
    ExecutionMode,
    ExecutionContext,
    RetryConfig
)


class TestPerformanceOptimizationService:
    """Test suite for performance optimization service"""
    
    @pytest.fixture
    def mock_tool_manager(self):
        """Create mock tool manager"""
        tool_manager = Mock(spec=ToolManager)
        
        # Mock capabilities
        capabilities = ToolCapabilities(
            tool_name="restic",
            version="0.16.0",
            native_features={
                Feature.PARALLEL_PROCESSING,
                Feature.COMPRESSION,
                Feature.ENCRYPTION
            },
            performance_characteristics=PerformanceProfile(
                typical_throughput_mbps=100.0,
                cpu_usage="medium",
                memory_usage="medium",
                parallel_efficiency=0.85,
                compression_overhead="low"
            ),
            configuration_options={
                'max_parallel_files': 8,
                'compression_levels': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            }
        )
        
        tool_manager.get_tool_capabilities.return_value = capabilities
        tool_manager.get_supported_tools.return_value = []
        
        return tool_manager
    
    @pytest.fixture
    def mock_parallel_optimizer(self):
        """Create mock parallel optimizer"""
        optimizer = Mock(spec=ParallelExecutionOptimizer)
        
        # Mock system resources
        system_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=45.0,
            memory_total_gb=16.0,
            memory_available_gb=8.0,
            memory_usage_percent=50.0,
            disk_io_busy_percent=30.0
        )
        
        optimizer.get_system_resources.return_value = system_resources
        optimizer.get_execution_metrics.return_value = None
        
        return optimizer
    
    @pytest.fixture
    def mock_performance_metrics(self):
        """Create mock performance metrics"""
        metrics = Mock(spec=PerformanceMetrics)
        metrics.get_operation_metrics.return_value = None
        metrics.get_completed_operations.return_value = []
        return metrics
    
    @pytest.fixture
    def optimization_service(self, mock_tool_manager, mock_parallel_optimizer, mock_performance_metrics):
        """Create performance optimization service"""
        return PerformanceOptimizationService(
            tool_manager=mock_tool_manager,
            parallel_optimizer=mock_parallel_optimizer,
            performance_metrics=mock_performance_metrics
        )
    
    @pytest.fixture
    def sample_job(self):
        """Create sample backup job"""
        config = BackupJobConfig(
            job_id="test-job-1",
            repository_id="test-repo",
            tool_type="restic",
            execution_mode=ExecutionMode.ON_DEMAND,
            retry_config=RetryConfig(max_retries=3),
            priority=5,
            target_names=["test-target"]
        )
        
        return BackupJob(
            config=config,
            tool_configuration=ToolConfiguration(
                tool_type="restic",
                parallel_operations=4,
                compression_level=5
            ),
            execution_context=ExecutionContext(
                start_time=datetime.now().timestamp(),
                attempt_number=1
            )
        )
    
    @pytest.fixture
    def sample_metrics(self):
        """Create sample operation metrics"""
        return OperationMetrics(
            operation_id="test-op-1",
            operation_type="backup",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_seconds=3600.0,
            files_processed=10000,
            bytes_processed=10 * 1024 * 1024 * 1024,  # 10 GB
            errors_count=0,
            metadata={'tool_type': 'restic'}
        )
    
    def test_optimize_tool_configuration(self, optimization_service, sample_job, mock_parallel_optimizer):
        """Test tool configuration optimization"""
        # Mock parallel config
        from TimeLocker.services.parallel_execution_optimizer import ParallelizationConfig
        
        parallel_config = ParallelizationConfig(
            parallel_operations=6,
            max_parallel_operations=8,
            resource_constraint_level=ResourceConstraintLevel.LOW,
            optimization_reason="Optimized for available resources"
        )
        
        mock_parallel_optimizer.calculate_optimal_parallelism.return_value = parallel_config
        
        # Optimize configuration
        optimized_config = optimization_service.optimize_tool_configuration(sample_job)
        
        # Verify optimization
        assert optimized_config.parallel_operations == 6
        assert optimized_config.compression_level is not None
        assert 'parallel_optimization' in optimized_config.tool_specific_options
    
    def test_identify_bottlenecks_cpu(self, optimization_service, sample_metrics):
        """Test CPU bottleneck identification"""
        # Create high CPU usage scenario
        system_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=92.0,
            memory_total_gb=16.0,
            memory_available_gb=8.0,
            memory_usage_percent=50.0,
            disk_io_busy_percent=30.0
        )
        
        bottlenecks = optimization_service.identify_bottlenecks(
            "test-op-1",
            sample_metrics,
            system_resources
        )
        
        # Should identify CPU bottleneck
        assert len(bottlenecks) > 0
        assert any(b.bottleneck_type == BottleneckType.CPU for b in bottlenecks)
        
        cpu_bottleneck = next(b for b in bottlenecks if b.bottleneck_type == BottleneckType.CPU)
        assert cpu_bottleneck.severity > 0.9
    
    def test_identify_bottlenecks_memory(self, optimization_service, sample_metrics):
        """Test memory bottleneck identification"""
        # Create high memory usage scenario
        system_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=45.0,
            memory_total_gb=16.0,
            memory_available_gb=1.0,
            memory_usage_percent=93.0,
            disk_io_busy_percent=30.0
        )
        
        bottlenecks = optimization_service.identify_bottlenecks(
            "test-op-1",
            sample_metrics,
            system_resources
        )
        
        # Should identify memory bottleneck
        assert any(b.bottleneck_type == BottleneckType.MEMORY for b in bottlenecks)
    
    def test_identify_bottlenecks_disk_io(self, optimization_service, sample_metrics):
        """Test disk I/O bottleneck identification"""
        # Create high disk I/O scenario
        system_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=45.0,
            memory_total_gb=16.0,
            memory_available_gb=8.0,
            memory_usage_percent=50.0,
            disk_io_busy_percent=88.0
        )
        
        bottlenecks = optimization_service.identify_bottlenecks(
            "test-op-1",
            sample_metrics,
            system_resources
        )
        
        # Should identify disk I/O bottleneck
        assert any(b.bottleneck_type == BottleneckType.DISK_IO for b in bottlenecks)
    
    def test_generate_optimization_recommendations(self, optimization_service, sample_job, sample_metrics):
        """Test optimization recommendation generation"""
        # Create bottlenecks
        bottlenecks = [
            PerformanceBottleneck(
                bottleneck_type=BottleneckType.CPU,
                severity=0.95,
                description="High CPU usage",
                impact_estimate="30% throughput reduction"
            )
        ]
        
        recommendations = optimization_service.generate_optimization_recommendations(
            sample_job,
            sample_metrics,
            bottlenecks
        )
        
        # Should generate recommendations
        assert len(recommendations) > 0
        
        # Should have high-priority recommendations for critical bottleneck
        assert any(r.priority == OptimizationPriority.CRITICAL for r in recommendations)
    
    def test_compare_tool_performance(self, optimization_service, mock_performance_metrics, mock_tool_manager):
        """Test tool performance comparison"""
        # Mock tool info
        from TimeLocker.services.tool_manager import ToolInfo
        
        mock_tool_manager.get_supported_tools.return_value = [
            ToolInfo(
                tool_name="restic",
                version="0.16.0",
                is_available=True,
                feature_count=15,
                native_feature_count=14,
                wrapper_feature_count=1
            )
        ]
        
        # Mock historical metrics
        metrics = [
            OperationMetrics(
                operation_id=f"op-{i}",
                operation_type="backup",
                start_time=datetime.now() - timedelta(days=i),
                end_time=datetime.now() - timedelta(days=i) + timedelta(hours=1),
                duration_seconds=3600.0,
                files_processed=10000,
                bytes_processed=10 * 1024 * 1024 * 1024,
                errors_count=0,
                metadata={'tool_type': 'restic'}
            )
            for i in range(5)
        ]
        
        mock_performance_metrics.get_completed_operations.return_value = metrics
        
        comparisons = optimization_service.compare_tool_performance(days=30, min_samples=3)
        
        # Should have comparison for restic
        assert len(comparisons) > 0
        assert comparisons[0].tool_name == "restic"
        assert comparisons[0].sample_count == 5
    
    def test_generate_performance_report(self, optimization_service, sample_job, sample_metrics):
        """Test performance report generation"""
        # Create sample result
        result = BackupResult(
            status=BackupStatus.COMPLETED,
            repository_name="test-repo",
            target_names=["test-target"],
            start_time=sample_metrics.start_time.timestamp(),
            end_time=sample_metrics.end_time.timestamp(),
            files_processed=sample_metrics.files_processed,
            bytes_processed=sample_metrics.bytes_processed
        )
        
        report = optimization_service.generate_performance_report(
            "test-op-1",
            sample_job,
            result,
            include_tool_comparison=False
        )
        
        # Verify report structure
        assert report.operation_id == "test-op-1"
        assert report.tool_type == "restic"
        assert 'throughput_mbps' in report.current_performance
        assert isinstance(report.identified_bottlenecks, list)
        assert isinstance(report.recommendations, list)
    
    def test_apply_automatic_adjustments(self, optimization_service, sample_job):
        """Test automatic configuration adjustments"""
        # Create report with high-priority recommendations
        report = PerformanceOptimizationReport(
            operation_id="test-op-1",
            tool_type="restic",
            current_performance={'throughput_mbps': 50.0},
            identified_bottlenecks=[],
            recommendations=[
                OptimizationRecommendation(
                    priority=OptimizationPriority.HIGH,
                    category="Parallelism",
                    recommendation="Increase parallel operations",
                    expected_improvement="20% throughput increase",
                    implementation_complexity="low",
                    configuration_changes={'parallel_operations': 8}
                )
            ],
            tool_comparison=None,
            estimated_improvement="20% improvement"
        )
        
        adjusted_config = optimization_service.apply_automatic_adjustments(sample_job, report)
        
        # Should apply the adjustment
        assert adjusted_config.parallel_operations == 8
    
    def test_optimization_with_historical_data(self, optimization_service, sample_job, mock_performance_metrics):
        """Test optimization using historical performance data"""
        # Mock historical metrics with different compression levels
        historical_metrics = [
            OperationMetrics(
                operation_id=f"op-{i}",
                operation_type="backup",
                start_time=datetime.now() - timedelta(days=i),
                end_time=datetime.now() - timedelta(days=i) + timedelta(hours=1),
                duration_seconds=3600.0 + (i * 100),  # Varying durations
                files_processed=10000,
                bytes_processed=10 * 1024 * 1024 * 1024,
                errors_count=0,
                metadata={'tool_type': 'restic', 'compression_level': i % 10}
            )
            for i in range(10)
        ]
        
        optimized_config = optimization_service.optimize_tool_configuration(
            sample_job,
            historical_metrics
        )
        
        # Should optimize based on historical data
        assert optimized_config.compression_level is not None
    
    def test_bottleneck_severity_calculation(self, optimization_service, sample_metrics):
        """Test bottleneck severity calculation"""
        # Create various resource scenarios
        scenarios = [
            (50.0, 0.0),  # Low usage, no bottleneck
            (86.0, 0.85),  # High usage, should detect (threshold is > 85)
            (95.0, 0.95),  # Very high usage, critical
        ]
        
        for cpu_usage, expected_min_severity in scenarios:
            system_resources = SystemResources(
                cpu_count=8,
                cpu_usage_percent=cpu_usage,
                memory_total_gb=16.0,
                memory_available_gb=8.0,
                memory_usage_percent=50.0,
                disk_io_busy_percent=30.0
            )
            
            bottlenecks = optimization_service.identify_bottlenecks(
                "test-op",
                sample_metrics,
                system_resources
            )
            
            if expected_min_severity > 0:
                cpu_bottlenecks = [b for b in bottlenecks if b.bottleneck_type == BottleneckType.CPU]
                assert len(cpu_bottlenecks) > 0
                assert cpu_bottlenecks[0].severity >= expected_min_severity
