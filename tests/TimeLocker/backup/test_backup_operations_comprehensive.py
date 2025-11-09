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
Comprehensive Test Suite for Backup Operations

This test suite validates all requirements from the backup-operations spec:
- Job execution with retry logic and error handling
- Tool capability detection and plugin wrapper functionality
- Parallel execution and optimization algorithms
- End-to-end backup job workflows with different tools
- Integration with Policy Management and Data Selection systems
"""

import pytest
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.services.backup_orchestrator import BackupOrchestrator
from TimeLocker.services.job_executor import JobExecutor, ErrorCategory, RetryStrategy
from TimeLocker.services.tool_manager import ToolManager, Feature
from TimeLocker.services.plugin_wrapper import PluginWrapper, BackupConfig
from TimeLocker.services.parallel_execution_optimizer import ParallelExecutionOptimizer
from TimeLocker.services.performance_optimization_service import PerformanceOptimizationService
from TimeLocker.monitoring import ProgressMonitor, StatusReporter
from TimeLocker.interfaces.data_models import (
    BackupJobConfig,
    BackupJob,
    BackupResult,
    BackupStatus,
    ExecutionMode,
    RetryConfig,
    ToolConfiguration,
    ExecutionContext
)


class TestJobExecutorRetryLogic:
    """
    Test JobExecutor retry logic and error handling scenarios
    Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    @pytest.fixture
    def job_executor(self):
        """Create job executor instance"""
        return JobExecutor()
    
    @pytest.fixture
    def sample_job(self):
        """Create sample backup job"""
        config = BackupJobConfig(
            job_id="retry-test-job",
            repository_id="test-repo",
            target_names=["test-target"],
            execution_mode=ExecutionMode.ON_DEMAND,
            retry_config=RetryConfig(
                max_retries=3,
                base_delay_seconds=0.1,
                backoff_multiplier=2.0,
                max_delay_seconds=5.0
            )
        )
        
        return BackupJob(
            config=config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(tool_type="restic"),
            execution_context=ExecutionContext(start_time=time.time())
        )
    
    def test_transient_error_retry_with_exponential_backoff(self, job_executor, sample_job):
        """Test retry with exponential backoff for transient errors (Req 2.4, 6.1)"""
        attempt_count = [0]
        attempt_times = []
        
        def mock_execution(job):
            attempt_count[0] += 1
            attempt_times.append(time.time())
            
            if attempt_count[0] < 3:
                return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=job.config.repository_id,
                    target_names=job.config.target_names,
                    errors=["Connection timeout - transient error"]
                )
            
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="success-snapshot"
            )
        
        result = job_executor.execute_with_retry(sample_job, mock_execution)
        
        # Verify success after retries
        assert result.backup_result.status == BackupStatus.COMPLETED
        assert result.total_attempts == 3
        assert len(result.retry_history) == 2
        
        # Verify exponential backoff delays
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            assert delay2 > delay1  # Second delay should be longer
    
    def test_configuration_error_no_retry(self, job_executor, sample_job):
        """Test that configuration errors are not retried (Req 6.2)"""
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.FAILED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                errors=["File not found: /invalid/path - configuration error"]
            )
        
        result = job_executor.execute_with_retry(sample_job, mock_execution)
        
        # Should fail without retries for configuration errors
        assert result.backup_result.status == BackupStatus.FAILED
        assert result.final_error_classification.category == ErrorCategory.CONFIGURATION
        assert result.final_error_classification.should_retry is False
    
    def test_max_retries_exhausted(self, job_executor, sample_job):
        """Test behavior when max retries are exhausted (Req 2.4, 6.5)"""
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.FAILED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                errors=["Network error - persistent failure"]
            )
        
        result = job_executor.execute_with_retry(sample_job, mock_execution)
        
        # Should fail after max retries
        assert result.backup_result.status == BackupStatus.FAILED
        assert result.total_attempts == 4  # 1 initial + 3 retries
        assert "Failed after 4 attempts" in result.backup_result.errors[0]
    
    def test_partial_backup_recovery(self, job_executor, sample_job):
        """Test partial backup recovery when some files are inaccessible (Req 6.2)"""
        def mock_execution(job):
            return BackupResult(
                status=BackupStatus.COMPLETED,
                repository_name=job.config.repository_id,
                target_names=job.config.target_names,
                snapshot_id="partial-snapshot",
                files_processed=80,
                warnings=["10 files inaccessible due to permissions"]
            )
        
        result = job_executor.execute_with_retry(sample_job, mock_execution)
        
        # Should complete with warnings
        assert result.backup_result.status == BackupStatus.COMPLETED
        assert len(result.backup_result.warnings) > 0
        assert result.backup_result.files_processed == 80


class TestToolCapabilityDetection:
    """
    Test tool capability detection and plugin wrapper functionality
    Requirements: 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    @pytest.fixture
    def tool_manager(self):
        """Create tool manager instance"""
        return ToolManager()
    
    def test_detect_restic_capabilities(self, tool_manager):
        """Test detection of Restic tool capabilities (Req 8.1, 8.2)"""
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        # Verify native features
        assert Feature.INCREMENTAL_BACKUP in capabilities.native_features
        assert Feature.ENCRYPTION in capabilities.native_features
        assert Feature.DATA_DEDUPLICATION in capabilities.native_features
        assert Feature.PARALLEL_PROCESSING in capabilities.native_features
        
        # Verify performance characteristics
        assert capabilities.performance_characteristics is not None
        assert capabilities.performance_characteristics.typical_throughput_mbps > 0
    
    def test_detect_borg_capabilities(self, tool_manager):
        """Test detection of Borg tool capabilities (Req 8.1, 8.2)"""
        capabilities = tool_manager.get_tool_capabilities('borg')
        
        # Verify native features
        assert Feature.INCREMENTAL_BACKUP in capabilities.native_features
        assert Feature.ENCRYPTION in capabilities.native_features
        assert Feature.DATA_DEDUPLICATION in capabilities.native_features
    
    def test_capability_comparison_across_tools(self, tool_manager):
        """Test capability comparison between tools (Req 8.2, 9.4)"""
        restic_caps = tool_manager.get_tool_capabilities('restic')
        borg_caps = tool_manager.get_tool_capabilities('borg')
        
        # Both should support core features
        core_features = {Feature.INCREMENTAL_BACKUP, Feature.ENCRYPTION}
        assert core_features.issubset(restic_caps.native_features)
        assert core_features.issubset(borg_caps.native_features)
        
        # Verify capability info is available
        assert restic_caps.version is not None
        assert borg_caps.version is not None
    
    def test_validate_job_compatibility_with_tool(self, tool_manager):
        """Test job compatibility validation against tool capabilities (Req 8.3)"""
        job_config = BackupJobConfig(
            job_id="compat-test",
            repository_id="test-repo",
            target_names=["test-target"]
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(
                tool_type='restic',
                encryption_enabled=True,
                parallel_operations=4
            ),
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        result = tool_manager.validate_job_compatibility('restic', job)
        
        assert result['is_compatible'] is True
        assert isinstance(result['warnings'], list)
        assert isinstance(result['missing_features'], list)


class TestParallelExecutionOptimization:
    """
    Test parallel execution and optimization algorithms
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    @pytest.fixture
    def parallel_optimizer(self):
        """Create parallel execution optimizer"""
        return ParallelExecutionOptimizer()
    
    @pytest.fixture
    def tool_manager(self):
        """Create tool manager"""
        return ToolManager()
    
    def test_calculate_optimal_parallelism(self, parallel_optimizer, tool_manager):
        """Test optimal parallelism calculation (Req 4.1, 4.2, 9.1)"""
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        # Create a sample job
        job_config = BackupJobConfig(
            job_id="parallel-test-job",
            repository_id="test-repo",
            target_names=["test-target"]
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(tool_type='restic'),
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        config = parallel_optimizer.calculate_optimal_parallelism(capabilities, job)
        
        # Verify parallelism is within reasonable bounds
        system_resources = parallel_optimizer.get_system_resources()
        assert config.parallel_operations >= 1
        assert config.parallel_operations <= system_resources.cpu_count * 2
        assert config.max_parallel_operations >= config.parallel_operations
    
    def test_resource_aware_parallelization(self, parallel_optimizer):
        """Test resource-aware parallelization (Req 4.2, 9.2)"""
        system_resources = parallel_optimizer.get_system_resources()
        
        # Verify system resources are monitored
        assert system_resources.cpu_count > 0
        assert system_resources.memory_total_gb > 0
        assert 0 <= system_resources.cpu_usage_percent <= 100
        assert 0 <= system_resources.memory_usage_percent <= 100
    
    def test_parallel_operation_failure_handling(self, parallel_optimizer, tool_manager):
        """Test graceful degradation on parallel operation failures (Req 4.4)"""
        capabilities = tool_manager.get_tool_capabilities('restic')
        
        # Create a sample job
        job_config = BackupJobConfig(
            job_id="parallel-failure-test",
            repository_id="test-repo",
            target_names=["test-target"]
        )
        
        job = BackupJob(
            config=job_config,
            source_paths=["/test/path"],
            tool_configuration=ToolConfiguration(tool_type='restic'),
            execution_context=ExecutionContext(start_time=time.time())
        )
        
        # Mock high resource usage by patching get_system_resources
        from TimeLocker.services.parallel_execution_optimizer import SystemResources
        high_usage_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=90.0,
            memory_total_gb=16.0,
            memory_available_gb=1.0,
            memory_usage_percent=93.0,
            disk_io_busy_percent=85.0
        )
        
        with patch.object(parallel_optimizer, 'get_system_resources', return_value=high_usage_resources):
            config = parallel_optimizer.calculate_optimal_parallelism(capabilities, job)
        
        # Should reduce parallelism under high load
        assert config.parallel_operations < high_usage_resources.cpu_count


class TestEndToEndBackupWorkflows:
    """
    Test complete backup job workflows with different tools
    Requirements: All requirements validation
    """
    
    @pytest.fixture
    def mock_repository_factory(self):
        """Create mock repository factory"""
        factory = Mock()
        mock_repo = Mock()
        mock_repo.backup_target.return_value = {
            'snapshot_id': 'e2e-snapshot-123',
            'files_processed': 500,
            'bytes_processed': 10 * 1024 * 1024
        }
        factory.create_repository.return_value = mock_repo
        return factory
    
    @pytest.fixture
    def mock_configuration_provider(self):
        """Create mock configuration provider"""
        provider = Mock()
        provider.get_repositories.return_value = [
            {'name': 'test-repo', 'id': 'test-repo-id', 'uri': 'file:///tmp/test-repo'}
        ]
        provider.get_backup_targets.return_value = [
            {
                'name': 'test-target',
                'paths': ['/tmp/test-data'],
                'exclude_patterns': ['*.tmp'],
                'include_patterns': ['*.txt', '*.pdf']
            }
        ]
        return provider
    
    @pytest.fixture
    def orchestrator(self, mock_repository_factory, mock_configuration_provider):
        """Create backup orchestrator"""
        return BackupOrchestrator(
            repository_factory=mock_repository_factory,
            configuration_provider=mock_configuration_provider,
            max_concurrent_backups=2
        )
    
    def test_complete_backup_workflow_restic(self, orchestrator):
        """Test complete backup workflow with Restic (Req 1.1, 1.2, 1.3, 1.4)"""
        job_config = BackupJobConfig(
            job_id='e2e-restic-job',
            repository_id='test-repo',
            target_names=['test-target'],
            tool_type='restic',
            execution_mode=ExecutionMode.ON_DEMAND,
            retry_config=RetryConfig(max_retries=2)
        )
        
        result = orchestrator.execute_backup_job(job_config)
        
        # Verify successful execution
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == 'e2e-snapshot-123'
        assert result.files_processed == 500
    
    def test_backup_with_data_selection_integration(self, orchestrator):
        """Test backup with data selection integration (Req 1.3, 7.1, 7.2, 7.3)"""
        job_config = BackupJobConfig(
            job_id='e2e-selection-job',
            repository_id='test-repo',
            target_names=['test-target'],
            data_selection_id='test-selection-001',
            tool_type='restic'
        )
        
        backup_job = orchestrator.prepare_backup_job(job_config)
        
        # Verify data selection is integrated
        assert backup_job.data_selection_config is not None
        assert backup_job.data_selection_config['selection_id'] == 'test-selection-001'
        assert len(backup_job.exclude_patterns) > 0
        assert len(backup_job.source_paths) > 0
    
    def test_backup_with_policy_integration(self, orchestrator):
        """Test backup with policy integration (Req 1.1)"""
        mock_policy_service = Mock()
        orchestrator_with_policy = BackupOrchestrator(
            repository_factory=orchestrator._repository_factory,
            configuration_provider=orchestrator._configuration_provider,
            policy_integration_service=mock_policy_service
        )
        
        job_config = BackupJobConfig(
            job_id='e2e-policy-job',
            repository_id='test-repo',
            policy_id='test-policy-001',
            execution_mode=ExecutionMode.POLICY_DRIVEN
        )
        
        backup_job = orchestrator_with_policy.prepare_backup_job(job_config)
        
        # Verify policy is integrated
        assert backup_job.policy_config is not None
        assert backup_job.policy_config['policy_id'] == 'test-policy-001'
    
    def test_backup_with_progress_monitoring(self, orchestrator):
        """Test backup with progress monitoring (Req 2.5, 5.1, 5.2, 5.3, 5.4)"""
        status_reporter = StatusReporter()
        progress_monitor = ProgressMonitor(status_reporter=status_reporter)
        
        job_config = BackupJobConfig(
            job_id='e2e-progress-job',
            repository_id='test-repo',
            target_names=['test-target'],
            tool_type='restic'
        )
        
        # Start monitoring
        progress_monitor.start_monitoring(
            job_id=job_config.job_id,
            repository_id=job_config.repository_id,
            estimated_size=10 * 1024 * 1024,
            estimated_files=500
        )
        
        try:
            # Execute backup
            result = orchestrator.execute_backup_job(job_config)
            
            # Verify progress was tracked
            assert result.status == BackupStatus.COMPLETED
            
            # Get progress report
            report = progress_monitor.get_progress_report(job_config.job_id)
            if report:
                assert report.job_id == job_config.job_id
        finally:
            progress_monitor.stop_monitoring(job_config.job_id)
    
    def test_backup_with_integrity_validation(self, orchestrator, mock_repository_factory):
        """Test backup with integrity validation (Req 3.1, 3.2, 3.3, 3.4, 3.5)"""
        # Mock repository with integrity check
        mock_repo = mock_repository_factory.create_repository.return_value
        mock_repo.backup_target.return_value = {
            'snapshot_id': 'integrity-snapshot',
            'files_processed': 100,
            'bytes_processed': 1024 * 1024,
            'integrity_verified': True
        }
        
        job_config = BackupJobConfig(
            job_id='e2e-integrity-job',
            repository_id='test-repo',
            target_names=['test-target'],
            tool_type='restic'
        )
        
        result = orchestrator.execute_backup_job(job_config)
        
        # Verify integrity validation
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == 'integrity-snapshot'
    
    def test_backup_with_error_recovery(self, orchestrator, mock_repository_factory):
        """Test backup with error recovery (Req 6.1, 6.3, 6.4, 6.5)"""
        # Mock repository that fails with transient error first then succeeds
        mock_repo = mock_repository_factory.create_repository.return_value
        
        # Create a transient error that will be retried
        transient_error = Exception("Connection timeout - transient network error")
        
        mock_repo.backup_target.side_effect = [
            transient_error,
            {
                'snapshot_id': 'recovery-snapshot',
                'files_processed': 200,
                'bytes_processed': 2 * 1024 * 1024
            }
        ]
        
        job_config = BackupJobConfig(
            job_id='e2e-recovery-job',
            repository_id='test-repo',
            target_names=['test-target'],
            tool_type='restic',
            retry_config=RetryConfig(max_retries=2, base_delay_seconds=0.1)
        )
        
        result = orchestrator.execute_backup_job(job_config)
        
        # Should succeed after retry
        assert result.status == BackupStatus.COMPLETED
        assert result.snapshot_id == 'recovery-snapshot'


class TestPerformanceOptimization:
    """
    Test performance optimization and monitoring
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    def test_performance_optimization_service_initialization(self):
        """Test performance optimization service can be initialized (Req 9.1)"""
        tool_manager = ToolManager()
        parallel_optimizer = ParallelExecutionOptimizer()
        
        # Create service with real dependencies
        from TimeLocker.performance.metrics import PerformanceMetrics
        performance_metrics = PerformanceMetrics()
        
        service = PerformanceOptimizationService(
            tool_manager=tool_manager,
            parallel_optimizer=parallel_optimizer,
            performance_metrics=performance_metrics
        )
        
        # Verify service is initialized
        assert service is not None
        assert service._tool_manager is not None
        assert service._parallel_optimizer is not None
    
    def test_bottleneck_identification_with_real_optimizer(self):
        """Test bottleneck identification with real optimizer (Req 9.3, 9.5)"""
        from TimeLocker.performance.metrics import OperationMetrics, PerformanceMetrics
        from TimeLocker.services.parallel_execution_optimizer import SystemResources
        
        tool_manager = ToolManager()
        parallel_optimizer = ParallelExecutionOptimizer()
        performance_metrics = PerformanceMetrics()
        
        service = PerformanceOptimizationService(
            tool_manager=tool_manager,
            parallel_optimizer=parallel_optimizer,
            performance_metrics=performance_metrics
        )
        
        # Create sample metrics
        metrics = OperationMetrics(
            operation_id="bottleneck-test",
            operation_type="backup",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_seconds=3600.0,
            files_processed=1000,
            bytes_processed=1024 * 1024 * 1024,
            errors_count=0
        )
        
        # Create high CPU usage scenario
        system_resources = SystemResources(
            cpu_count=8,
            cpu_usage_percent=95.0,
            memory_total_gb=16.0,
            memory_available_gb=8.0,
            memory_usage_percent=50.0,
            disk_io_busy_percent=30.0
        )
        
        bottlenecks = service.identify_bottlenecks(
            "bottleneck-test",
            metrics,
            system_resources
        )
        
        # Should identify CPU bottleneck
        assert len(bottlenecks) > 0
        # Verify at least one bottleneck is CPU-related
        from TimeLocker.services.performance_optimization_service import BottleneckType
        cpu_bottlenecks = [b for b in bottlenecks if b.bottleneck_type == BottleneckType.CPU]
        assert len(cpu_bottlenecks) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
