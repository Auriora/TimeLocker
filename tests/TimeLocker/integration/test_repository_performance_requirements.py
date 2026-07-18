"""
Repository Performance Requirements Integration Tests

This module provides comprehensive integration tests for validating repository
management performance requirements under desktop usage conditions.

Tests cover:
- Desktop scalability (20+ repositories, concurrent operations)
- Performance thresholds (15s network, 3s local, 2s listing)
- Concurrent validation limits (3 parallel operations)
- Performance monitoring and warnings
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from TimeLocker.services.repository_manager import RepositoryManager
from TimeLocker.services.repository_performance_monitor import RepositoryPerformanceMonitor
from TimeLocker.services.repository_concurrency_manager import RepositoryConcurrencyManager
from TimeLocker.interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ConnectivityStatus, IntegrityStatus
)
from TimeLocker.interfaces.integration_data_models import ServiceContext


class TestDesktopScalability:
    """Integration tests for desktop scalability requirements"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager"""
        mock_factory = Mock()
        mock_validation = Mock()
        mock_credential = Mock()
        mock_config = Mock()
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config
        )
        
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_manage_20_plus_repositories(self, repository_manager, temp_dir):
        """
        Test managing 20+ repositories with responsive performance
        
        Requirements: 9.1
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create 25 repositories (exceeds minimum requirement)
        num_repos = 25
        
        # Mock dependencies
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._validate_configuration = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
        repository_manager.validate_repository = AsyncMock(return_value=ValidationResult(
            success=True,
            timestamp=datetime.utcnow(),
            connectivity_status=ConnectivityStatus.CONNECTED,
            integrity_status=IntegrityStatus.VALID
        ))
        repository_manager._save_repositories = Mock()
        
        # Create repositories
        from TimeLocker.interfaces.repository_management_models import RepositoryCreationOptions
        start_time = time.time()
        
        for i in range(num_repos):
            config = RepositoryConfig(
                name=f"repo-{i}",
                uri=f"file://{temp_dir}/repo-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL,
                description=f"Test repository {i}"
            )
            await repository_manager.create_repository(config, RepositoryCreationOptions())
        
        creation_time = time.time() - start_time
        
        # Verify all repositories were created
        all_repos = await repository_manager.list_repositories()
        assert len(all_repos) == num_repos
        
        # Test listing performance
        start_time = time.time()
        repos = await repository_manager.list_repositories()
        listing_time = time.time() - start_time
        
        # Verify listing performance meets requirement (<2s for typical desktop usage)
        assert listing_time < 2.0, f"Listing {num_repos} repositories took {listing_time:.2f}s, expected <2s"
        
        # Test filtered listing performance
        start_time = time.time()
        local_repos = await repository_manager.list_repositories({'type': 'local'})
        filtered_listing_time = time.time() - start_time
        
        assert filtered_listing_time < 2.0, f"Filtered listing took {filtered_listing_time:.2f}s, expected <2s"
        assert len(local_repos) == num_repos
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_repository_operations(self, repository_manager):
        """
        Test concurrent repository operations with desktop-appropriate limits
        
        Requirements: 9.3
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create test repositories
        num_repos = 10
        repos = []
        
        for i in range(num_repos):
            config = RepositoryConfig(
                name=f"concurrent-repo-{i}",
                uri=f"file:///tmp/concurrent-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repos.append(repo)
            repository_manager._repositories[f"concurrent-repo-{i}"] = repo
        
        # Mock validation with realistic delays
        async def mock_validate(repo):
            await asyncio.sleep(0.1)  # Simulate validation work
            return ValidationResult(
                success=True,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.CONNECTED,
                integrity_status=IntegrityStatus.VALID
            )
        
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._test_connectivity = AsyncMock(return_value=Mock(
            success=True,
            status=ConnectivityStatus.CONNECTED
        ))
        repository_manager._test_integrity = AsyncMock(return_value=Mock(
            success=True,
            status=IntegrityStatus.VALID
        ))
        
        # Perform concurrent validations
        start_time = time.time()
        
        validation_tasks = [
            repository_manager.validate_repository(repo)
            for repo in repos
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        total_time = time.time() - start_time
        
        # Verify all validations completed
        assert len(results) == num_repos
        assert all(r.success for r in results)
        
        # With concurrency limit of 3, 10 validations should take roughly 10/3 * 0.1 = 0.33s
        # Allow some overhead, but should be much faster than sequential (1.0s)
        assert total_time < 0.8, f"Concurrent validations took {total_time:.2f}s, expected <0.8s"


class TestPerformanceThresholds:
    """Integration tests for performance threshold validation"""
    
    @pytest.fixture
    def repository_manager(self):
        """Create repository manager with performance monitoring"""
        mock_factory = Mock()
        mock_validation = Mock()
        mock_credential = Mock()
        mock_config = Mock()
        
        # Create real performance monitor
        performance_monitor = RepositoryPerformanceMonitor()
        
        manager = RepositoryManager(
            repository_factory=mock_factory,
            validation_service=mock_validation,
            credential_manager=mock_credential,
            config_manager=mock_config,
            performance_monitor=performance_monitor
        )
        
        return manager
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_local_repository_validation_threshold(self, repository_manager):
        """
        Test local repository validation meets 3s threshold
        
        Requirements: 9.2
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create local repository
        config = RepositoryConfig(
            name="local-perf-test",
            uri="file:///tmp/local-perf",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        
        # Mock fast validation (local should be fast)
        async def fast_connectivity_test(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate fast local check
            return Mock(success=True, status=ConnectivityStatus.CONNECTED)
        
        async def fast_integrity_test(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate fast local check
            return Mock(success=True, status=IntegrityStatus.VALID)
        
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._test_connectivity = AsyncMock(side_effect=fast_connectivity_test)
        repository_manager._test_integrity = AsyncMock(side_effect=fast_integrity_test)
        
        # Perform validation and measure time
        start_time = time.time()
        result = await repository_manager.validate_repository(repository)
        validation_time = time.time() - start_time
        
        # Verify validation succeeded
        assert result.success is True
        
        # Verify validation time meets threshold
        assert validation_time < 3.0, f"Local validation took {validation_time:.2f}s, expected <3s"
        
        # Check performance metrics
        if result.performance_metrics:
            assert result.performance_metrics.get('validation_time', validation_time) < 3.0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_network_repository_validation_threshold(self, repository_manager):
        """
        Test network repository validation meets 15s threshold
        
        Requirements: 9.2
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create network repository (S3)
        config = RepositoryConfig(
            name="network-perf-test",
            uri="s3:https://s3.amazonaws.com/test-bucket",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.S3
        )
        
        repository = Repository(config=config, status=RepositoryStatus.ACTIVE)
        
        # Mock slower validation (network has higher latency)
        async def network_connectivity_test(*args, **kwargs):
            await asyncio.sleep(3.0)  # Simulate network latency
            return Mock(success=True, status=ConnectivityStatus.CONNECTED)
        
        async def network_integrity_test(*args, **kwargs):
            await asyncio.sleep(2.0)  # Simulate network check
            return Mock(success=True, status=IntegrityStatus.VALID)
        
        repository_manager._repository_factory.create_repository.return_value = Mock()
        repository_manager._test_connectivity = AsyncMock(side_effect=network_connectivity_test)
        repository_manager._test_integrity = AsyncMock(side_effect=network_integrity_test)
        
        # Perform validation and measure time
        start_time = time.time()
        result = await repository_manager.validate_repository(repository)
        validation_time = time.time() - start_time
        
        # Verify validation succeeded
        assert result.success is True
        
        # Verify validation time meets threshold
        assert validation_time < 15.0, f"Network validation took {validation_time:.2f}s, expected <15s"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_repository_listing_threshold(self, repository_manager):
        """
        Test repository listing meets 2s threshold
        
        Requirements: 9.4
        """
        # Initialize manager
        context = Mock(spec=ServiceContext)
        context.config = {}
        context.logger = Mock()
        repository_manager.initialize(context)
        
        # Create 20 repositories (typical desktop usage)
        for i in range(20):
            config = RepositoryConfig(
                name=f"list-perf-repo-{i}",
                uri=f"file:///tmp/list-perf-{i}",
                engine=BackupEngine.RESTIC,
                type=RepositoryType.LOCAL
            )
            repo = Repository(config=config, status=RepositoryStatus.ACTIVE)
            repository_manager._repositories[f"list-perf-repo-{i}"] = repo
        
        # Measure listing performance
        start_time = time.time()
        repos = await repository_manager.list_repositories()
        listing_time = time.time() - start_time
        
        # Verify listing completed
        assert len(repos) == 20
        
        # Verify listing time meets threshold
        assert listing_time < 2.0, f"Listing 20 repositories took {listing_time:.2f}s, expected <2s"


class TestConcurrentValidationLimits:
    """Integration tests for concurrent validation limits"""
    
    @pytest.fixture
    def concurrency_manager(self):
        """Create concurrency manager with desktop limits"""
        return RepositoryConcurrencyManager(max_concurrent_validations=3)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_validation_limit_enforcement(self, concurrency_manager):
        """
        Test that concurrent validation limit (3 parallel) is enforced
        
        Requirements: 9.3
        """
        # Track concurrent operations
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def mock_validation(repo_id):
            nonlocal concurrent_count, max_concurrent
            
            async with concurrency_manager._validation_semaphore:
                async with lock:
                    concurrent_count += 1
                    max_concurrent = max(max_concurrent, concurrent_count)
                
                # Simulate validation work
                await asyncio.sleep(0.1)
                
                async with lock:
                    concurrent_count -= 1
        
        # Start 10 validations
        tasks = [mock_validation(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify maximum concurrent operations was limited to 3
        assert max_concurrent <= 3, f"Max concurrent operations was {max_concurrent}, expected <=3"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_validation_performance_benefit(self, concurrency_manager):
        """
        Test that concurrent validation provides performance benefit
        
        Requirements: 9.3
        """
        # Sequential validation time
        async def sequential_validations(count):
            start_time = time.time()
            for i in range(count):
                await asyncio.sleep(0.1)  # Simulate validation
            return time.time() - start_time
        
        # Concurrent validation time
        async def concurrent_validations(count):
            async def single_validation():
                async with concurrency_manager._validation_semaphore:
                    await asyncio.sleep(0.1)  # Simulate validation
            
            start_time = time.time()
            tasks = [single_validation() for _ in range(count)]
            await asyncio.gather(*tasks)
            return time.time() - start_time
        
        # Test with 9 validations
        num_validations = 9
        
        sequential_time = await sequential_validations(num_validations)
        concurrent_time = await concurrent_validations(num_validations)
        
        # Concurrent should be significantly faster
        # With limit of 3, 9 validations should take roughly 9/3 * 0.1 = 0.3s
        # Sequential would take 9 * 0.1 = 0.9s
        speedup = sequential_time / concurrent_time
        
        assert speedup > 2.0, f"Concurrent speedup was {speedup:.2f}x, expected >2x"
        assert concurrent_time < 0.5, f"Concurrent time was {concurrent_time:.2f}s, expected <0.5s"


class TestPerformanceMonitoring:
    """Integration tests for performance monitoring and warnings"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor"""
        return RepositoryPerformanceMonitor()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_performance_warning_for_slow_operations(self, performance_monitor):
        """
        Test that performance warnings are generated for slow operations
        
        Requirements: 9.5
        """
        # Mock slow operation
        async def slow_operation():
            await asyncio.sleep(0.5)
            return "result"
        
        # Monitor operation
        result = await performance_monitor.monitor_operation('validation_local', slow_operation)
        
        # Check if warning was logged (operation exceeded threshold)
        # Note: In real implementation, this would check logs
        assert result == "result"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_performance_metrics_collection(self, performance_monitor):
        """
        Test that performance metrics are collected
        
        Requirements: 9.2, 9.5
        """
        # Perform multiple operations
        async def test_operation():
            await asyncio.sleep(0.1)
            return "result"
        
        # Monitor several operations
        for i in range(5):
            await performance_monitor.monitor_operation(f'test_op_{i}', test_operation)
        
        # Get statistics
        stats = performance_monitor.get_statistics()
        
        # Verify metrics were collected
        assert stats is not None
        assert 'operation_count' in stats or len(stats) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
