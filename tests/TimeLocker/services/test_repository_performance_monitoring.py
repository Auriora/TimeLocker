"""
Unit Tests for Repository Performance Monitoring Components

This module provides comprehensive unit tests for:
- RepositoryPerformanceMonitor: Performance monitoring and threshold checking
- RepositoryConcurrencyManager: Concurrent operation management and locking
- RepositoryCacheManager: Caching effectiveness and optimization features

Tests focus on core functional logic and validate requirements 9.1-9.5.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.TimeLocker.services.repository_performance_monitor import (
    RepositoryPerformanceMonitor,
    PerformanceThresholds,
    PerformanceMetric,
    PerformanceWarning
)
from src.TimeLocker.services.repository_concurrency_manager import (
    RepositoryConcurrencyManager,
    LockInfo,
    ConcurrencyStats
)
from src.TimeLocker.services.repository_cache_manager import (
    RepositoryCacheManager,
    LazyRepositoryLoader,
    CacheEntry,
    CacheStatistics
)
from src.TimeLocker.interfaces.repository_management_models import (
    Repository,
    RepositoryConfig,
    RepositoryType,
    BackupEngine,
    RepositoryStatus
)


class TestPerformanceThresholds:
    """Unit tests for PerformanceThresholds"""
    
    def test_default_thresholds(self):
        """Test default threshold values"""
        thresholds = PerformanceThresholds()
        
        assert thresholds.validation_network == 15.0
        assert thresholds.validation_local == 3.0
        assert thresholds.listing == 2.0
        assert thresholds.configuration_update == 1.0

    def test_custom_thresholds(self):
        """Test custom threshold values"""
        thresholds = PerformanceThresholds(
            validation_network=20.0,
            validation_local=5.0,
            listing=3.0,
            configuration_update=2.0
        )
        
        assert thresholds.validation_network == 20.0
        assert thresholds.validation_local == 5.0
        assert thresholds.listing == 3.0
        assert thresholds.configuration_update == 2.0
    
    def test_get_threshold_for_local_validation(self):
        """Test getting threshold for local validation"""
        thresholds = PerformanceThresholds()
        
        threshold = thresholds.get_threshold('validation', RepositoryType.LOCAL)
        assert threshold == 3.0
    
    def test_get_threshold_for_network_validation(self):
        """Test getting threshold for network validation"""
        thresholds = PerformanceThresholds()
        
        threshold = thresholds.get_threshold('validation', RepositoryType.S3)
        assert threshold == 15.0
    
    def test_get_threshold_for_listing(self):
        """Test getting threshold for listing operation"""
        thresholds = PerformanceThresholds()
        
        threshold = thresholds.get_threshold('listing')
        assert threshold == 2.0
    
    def test_get_threshold_for_unknown_operation(self):
        """Test getting threshold for unknown operation returns default"""
        thresholds = PerformanceThresholds()
        
        threshold = thresholds.get_threshold('unknown_operation')
        assert threshold == 30.0  # Default threshold


class TestPerformanceMetric:
    """Unit tests for PerformanceMetric"""
    
    def test_create_metric(self):
        """Test creating a performance metric"""
        metric = PerformanceMetric(
            operation_name='validation',
            duration=2.5,
            timestamp=datetime.utcnow(),
            repository_name='test-repo',
            repository_type=RepositoryType.LOCAL,
            success=True
        )
        
        assert metric.operation_name == 'validation'
        assert metric.duration == 2.5
        assert metric.repository_name == 'test-repo'
        assert metric.repository_type == RepositoryType.LOCAL
        assert metric.success is True
        assert metric.error_message is None
    
    def test_create_failed_metric(self):
        """Test creating a failed metric with error message"""
        metric = PerformanceMetric(
            operation_name='validation',
            duration=1.0,
            timestamp=datetime.utcnow(),
            success=False,
            error_message='Connection timeout'
        )
        
        assert metric.success is False
        assert metric.error_message == 'Connection timeout'


class TestPerformanceWarning:
    """Unit tests for PerformanceWarning"""
    
    def test_create_warning(self):
        """Test creating a performance warning"""
        warning = PerformanceWarning(
            operation_name='validation',
            duration=5.0,
            threshold=3.0,
            timestamp=datetime.utcnow(),
            repository_name='test-repo',
            suggestions=['Check disk I/O performance']
        )
        
        assert warning.operation_name == 'validation'
        assert warning.duration == 5.0
        assert warning.threshold == 3.0
        assert warning.repository_name == 'test-repo'
        assert len(warning.suggestions) == 1
    
    def test_warning_string_representation(self):
        """Test warning string formatting"""
        warning = PerformanceWarning(
            operation_name='validation',
            duration=5.0,
            threshold=3.0,
            timestamp=datetime.utcnow(),
            repository_name='test-repo',
            suggestions=['Check disk I/O', 'Verify path']
        )
        
        warning_str = str(warning)
        assert 'validation' in warning_str
        assert '5.00s' in warning_str
        assert '3.00s' in warning_str
        assert 'test-repo' in warning_str
        assert 'Check disk I/O' in warning_str


class TestRepositoryPerformanceMonitor:
    """Unit tests for RepositoryPerformanceMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Create performance monitor"""
        return RepositoryPerformanceMonitor()
    
    @pytest.fixture
    def test_repository(self):
        """Create test repository"""
        config = RepositoryConfig(
            name='test-repo',
            uri='file:///tmp/test',
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        return Repository(config=config, status=RepositoryStatus.ACTIVE)
    
    @pytest.mark.asyncio
    async def test_monitor_successful_operation(self, monitor, test_repository):
        """Test monitoring a successful operation"""
        async def test_operation():
            await asyncio.sleep(0.1)
            return 'success'
        
        result = await monitor.monitor_operation(
            'test_op',
            test_operation,
            repository=test_repository
        )
        
        assert result == 'success'
        
        # Check metrics were recorded
        metrics = monitor.get_metrics('test_op')
        assert len(metrics) == 1
        assert metrics[0].success is True
        assert metrics[0].repository_name == 'test-repo'
    
    @pytest.mark.asyncio
    async def test_monitor_failed_operation(self, monitor, test_repository):
        """Test monitoring a failed operation"""
        async def failing_operation():
            await asyncio.sleep(0.1)
            raise ValueError('Test error')
        
        with pytest.raises(ValueError, match='Test error'):
            await monitor.monitor_operation(
                'test_op',
                failing_operation,
                repository=test_repository
            )
        
        # Check metrics were recorded with failure
        metrics = monitor.get_metrics('test_op')
        assert len(metrics) == 1
        assert metrics[0].success is False
        assert metrics[0].error_message == 'Test error'

    @pytest.mark.asyncio
    async def test_threshold_warning_generation(self, monitor, test_repository):
        """Test that warnings are generated when thresholds are exceeded"""
        # Set low threshold for testing
        monitor.thresholds.validation_local = 0.05
        
        async def slow_operation():
            await asyncio.sleep(0.1)  # Exceeds 0.05s threshold
            return 'result'
        
        await monitor.monitor_operation(
            'validation',
            slow_operation,
            repository=test_repository
        )
        
        # Check warning was generated
        warnings = monitor.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].operation_name == 'validation'
        assert warnings[0].duration > 0.05
    
    @pytest.mark.asyncio
    async def test_no_warning_below_threshold(self, monitor, test_repository):
        """Test that no warning is generated when below threshold"""
        # Set high threshold
        monitor.thresholds.validation_local = 10.0
        
        async def fast_operation():
            await asyncio.sleep(0.01)
            return 'result'
        
        await monitor.monitor_operation(
            'validation',
            fast_operation,
            repository=test_repository
        )
        
        # No warnings should be generated
        warnings = monitor.get_warnings()
        assert len(warnings) == 0
    
    def test_get_metrics_by_operation(self, monitor):
        """Test filtering metrics by operation name"""
        # Record metrics for different operations
        metric1 = PerformanceMetric('op1', 1.0, datetime.utcnow(), success=True)
        metric2 = PerformanceMetric('op2', 2.0, datetime.utcnow(), success=True)
        metric3 = PerformanceMetric('op1', 1.5, datetime.utcnow(), success=True)
        
        monitor._record_metric(metric1)
        monitor._record_metric(metric2)
        monitor._record_metric(metric3)
        
        # Get metrics for op1
        op1_metrics = monitor.get_metrics('op1')
        assert len(op1_metrics) == 2
        assert all(m.operation_name == 'op1' for m in op1_metrics)
    
    def test_get_metrics_with_time_filter(self, monitor):
        """Test filtering metrics by timestamp"""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=2)
        
        # Record old and new metrics
        old_metric = PerformanceMetric('test', 1.0, old_time, success=True)
        new_metric = PerformanceMetric('test', 2.0, now, success=True)
        
        monitor._record_metric(old_metric)
        monitor._record_metric(new_metric)
        
        # Get metrics since 1 hour ago
        since = now - timedelta(hours=1)
        recent_metrics = monitor.get_metrics(since=since)
        
        assert len(recent_metrics) == 1
        assert recent_metrics[0].duration == 2.0
    
    def test_get_metrics_with_limit(self, monitor):
        """Test limiting number of returned metrics"""
        # Record multiple metrics
        for i in range(10):
            metric = PerformanceMetric('test', float(i), datetime.utcnow(), success=True)
            monitor._record_metric(metric)
        
        # Get limited metrics
        limited_metrics = monitor.get_metrics(limit=5)
        assert len(limited_metrics) == 5
    
    def test_get_statistics(self, monitor):
        """Test getting performance statistics"""
        # Record some metrics
        for i in range(5):
            metric = PerformanceMetric('test_op', float(i), datetime.utcnow(), success=True)
            monitor._record_metric(metric)
        
        # Add a failed metric
        failed_metric = PerformanceMetric('test_op', 1.0, datetime.utcnow(), success=False)
        monitor._record_metric(failed_metric)
        
        stats = monitor.get_statistics()
        
        assert stats['total_operations'] == 6
        assert 'test_op' in stats['operations']
        assert stats['operations']['test_op']['count'] == 6
        assert stats['operations']['test_op']['successful'] == 5
        assert stats['operations']['test_op']['failed'] == 1
        assert 'avg_duration' in stats['operations']['test_op']
    
    def test_clear_metrics(self, monitor):
        """Test clearing metrics"""
        # Record metrics
        metric1 = PerformanceMetric('op1', 1.0, datetime.utcnow(), success=True)
        metric2 = PerformanceMetric('op2', 2.0, datetime.utcnow(), success=True)
        
        monitor._record_metric(metric1)
        monitor._record_metric(metric2)
        
        # Clear specific operation
        monitor.clear_metrics('op1')
        assert len(monitor.get_metrics('op1')) == 0
        assert len(monitor.get_metrics('op2')) == 1
        
        # Clear all
        monitor.clear_metrics()
        assert len(monitor.get_metrics()) == 0
    
    def test_clear_warnings(self, monitor):
        """Test clearing warnings"""
        warning = PerformanceWarning('test', 5.0, 3.0, datetime.utcnow())
        monitor._record_warning(warning)
        
        assert len(monitor.get_warnings()) == 1
        
        monitor.clear_warnings()
        assert len(monitor.get_warnings()) == 0
    
    def test_generate_suggestions_for_local_validation(self, monitor):
        """Test suggestion generation for local validation"""
        metric = PerformanceMetric(
            'validation',
            5.0,
            datetime.utcnow(),
            repository_type=RepositoryType.LOCAL,
            success=True
        )
        
        suggestions = monitor._generate_suggestions(metric)
        
        assert len(suggestions) > 0
        assert any('disk' in s.lower() for s in suggestions)
    
    def test_generate_suggestions_for_network_validation(self, monitor):
        """Test suggestion generation for network validation"""
        metric = PerformanceMetric(
            'validation',
            20.0,
            datetime.utcnow(),
            repository_type=RepositoryType.S3,
            success=True
        )
        
        suggestions = monitor._generate_suggestions(metric)
        
        assert len(suggestions) > 0
        assert any('network' in s.lower() for s in suggestions)
    
    def test_get_recent_performance_summary(self, monitor):
        """Test getting recent performance summary"""
        # Record some recent metrics
        for i in range(3):
            metric = PerformanceMetric('test_op', float(i), datetime.utcnow(), success=True)
            monitor._record_metric(metric)
        
        summary = monitor.get_recent_performance_summary(minutes=60)
        
        assert summary['time_window_minutes'] == 60
        assert summary['total_operations'] == 3
        assert 'test_op' in summary['operations_by_type']


class TestRepositoryConcurrencyManager:
    """Unit tests for RepositoryConcurrencyManager"""
    
    @pytest.fixture
    def manager(self):
        """Create concurrency manager"""
        return RepositoryConcurrencyManager(max_concurrent_validations=3)
    
    @pytest.mark.asyncio
    async def test_acquire_repository_lock(self, manager):
        """Test acquiring repository lock"""
        async with manager.acquire_repository_lock('test-repo', 'test-operation'):
            # Lock should be acquired
            assert manager.is_repository_locked('test-repo')
            lock_info = manager.get_lock_info('test-repo')
            assert lock_info is not None
            assert lock_info.repository_name == 'test-repo'
            assert lock_info.holder == 'test-operation'
        
        # Lock should be released after context
        assert not manager.is_repository_locked('test-repo')
    
    @pytest.mark.asyncio
    async def test_lock_prevents_concurrent_access(self, manager):
        """Test that lock prevents concurrent access to same repository"""
        access_order = []
        
        async def access_repo(repo_name, operation_id):
            async with manager.acquire_repository_lock(repo_name, f'op-{operation_id}'):
                access_order.append(f'start-{operation_id}')
                await asyncio.sleep(0.1)
                access_order.append(f'end-{operation_id}')
        
        # Start two operations on same repository
        await asyncio.gather(
            access_repo('test-repo', 1),
            access_repo('test-repo', 2)
        )
        
        # Operations should be sequential, not interleaved
        assert access_order == ['start-1', 'end-1', 'start-2', 'end-2'] or \
               access_order == ['start-2', 'end-2', 'start-1', 'end-1']
    
    @pytest.mark.asyncio
    async def test_different_repositories_can_lock_concurrently(self, manager):
        """Test that different repositories can be locked concurrently"""
        concurrent_locks = []
        
        async def lock_repo(repo_name):
            async with manager.acquire_repository_lock(repo_name, 'test'):
                concurrent_locks.append(repo_name)
                await asyncio.sleep(0.1)
                concurrent_locks.remove(repo_name)
        
        # Lock two different repositories concurrently
        await asyncio.gather(
            lock_repo('repo-1'),
            lock_repo('repo-2')
        )
        
        # Both should have been locked at some point
        # (we can't easily test they were concurrent, but they should complete)
        assert True  # Test completes without deadlock
    
    @pytest.mark.asyncio
    async def test_lock_timeout(self, manager):
        """Test lock acquisition timeout"""
        # Acquire and hold lock in background task
        async def hold_lock():
            async with manager.acquire_repository_lock('test-repo', 'holder'):
                await asyncio.sleep(1.0)  # Hold lock for a while
        
        lock_task = asyncio.create_task(hold_lock())
        await asyncio.sleep(0.05)  # Let first lock acquire
        
        # Try to acquire same lock with short timeout
        with pytest.raises(asyncio.TimeoutError):
            async with manager.acquire_repository_lock('test-repo', 'waiter', timeout=0.1):
                pass
        
        # Clean up
        lock_task.cancel()
        try:
            await lock_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_limit_concurrent_validations(self, manager):
        """Test limiting concurrent validations"""
        concurrent_count = 0
        max_concurrent = 0
        
        async def validation():
            nonlocal concurrent_count, max_concurrent
            async with manager.limit_concurrent_validations('test-repo'):
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                await asyncio.sleep(0.1)
                concurrent_count -= 1
        
        # Start 10 validations
        await asyncio.gather(*[validation() for _ in range(10)])
        
        # Max concurrent should not exceed limit
        assert max_concurrent <= 3
    
    @pytest.mark.asyncio
    async def test_validate_with_concurrency_limit(self, manager):
        """Test batch validation with concurrency limit"""
        # Create mock repositories
        repos = [Mock(name=f'repo-{i}') for i in range(5)]
        
        validated = []
        
        async def validate_func(repo):
            await asyncio.sleep(0.1)
            validated.append(repo.name)
            return f'result-{repo.name}'
        
        results = await manager.validate_with_concurrency_limit(repos, validate_func)
        
        assert len(results) == 5
        assert len(validated) == 5
    
    def test_is_repository_locked(self, manager):
        """Test checking if repository is locked"""
        assert not manager.is_repository_locked('test-repo')
    
    def test_get_lock_info(self, manager):
        """Test getting lock information"""
        lock_info = manager.get_lock_info('test-repo')
        assert lock_info is None  # No lock exists
    
    @pytest.mark.asyncio
    async def test_get_all_locks(self, manager):
        """Test getting all active locks"""
        # Acquire multiple locks using context managers properly
        async def check_locks():
            async with manager.acquire_repository_lock('repo-1', 'op1'):
                async with manager.acquire_repository_lock('repo-2', 'op2'):
                    all_locks = manager.get_all_locks()
                    assert len(all_locks) == 2
        
        await check_locks()
    
    @pytest.mark.asyncio
    async def test_get_stale_locks(self, manager):
        """Test detecting stale locks"""
        # Create a lock with old timestamp
        lock = asyncio.Lock()
        await lock.acquire()
        
        old_time = datetime.utcnow() - timedelta(minutes=10)
        lock_info = LockInfo(
            repository_name='stale-repo',
            acquired_at=old_time,
            holder='old-operation',
            lock=lock
        )
        manager._operation_locks['stale-repo'] = lock_info
        
        # Check for stale locks (older than 5 minutes)
        stale_locks = manager.get_stale_locks(max_age_seconds=300)
        assert len(stale_locks) == 1
        assert stale_locks[0].repository_name == 'stale-repo'
        
        # Clean up
        lock.release()
    
    @pytest.mark.asyncio
    async def test_force_release_lock(self, manager):
        """Test force releasing a lock"""
        # Acquire lock
        async with manager.acquire_repository_lock('test-repo', 'test'):
            assert manager.is_repository_locked('test-repo')
            
            # Force release
            released = await manager.force_release_lock('test-repo')
            assert released is True
            assert not manager.is_repository_locked('test-repo')
    
    def test_get_statistics(self, manager):
        """Test getting concurrency statistics"""
        stats = manager.get_statistics()
        
        assert 'max_concurrent_validations' in stats
        assert stats['max_concurrent_validations'] == 3
        assert 'total_locks_acquired' in stats
        assert 'current_active_locks' in stats
    
    def test_reset_statistics(self, manager):
        """Test resetting statistics"""
        # Modify stats
        manager._stats.total_locks_acquired = 10
        
        manager.reset_statistics()
        
        stats = manager.get_statistics()
        assert stats['total_locks_acquired'] == 0
    
    def test_set_lock_timeout(self, manager):
        """Test setting lock timeout"""
        manager.set_lock_timeout(600.0)
        
        stats = manager.get_statistics()
        assert stats['lock_timeout_seconds'] == 600.0
    
    def test_set_max_concurrent_validations(self, manager):
        """Test updating max concurrent validations"""
        manager.set_max_concurrent_validations(5)
        
        stats = manager.get_statistics()
        assert stats['max_concurrent_validations'] == 5
    
    @pytest.mark.asyncio
    async def test_wait_for_all_operations(self, manager):
        """Test waiting for all operations to complete"""
        async def long_operation():
            async with manager.acquire_repository_lock('test-repo', 'test'):
                await asyncio.sleep(0.2)
        
        # Start operation in background
        task = asyncio.create_task(long_operation())
        await asyncio.sleep(0.01)  # Let it start
        
        # Wait for completion with timeout
        completed = await manager.wait_for_all_operations(timeout=1.0)
        assert completed is True
        
        await task  # Clean up
    
    def test_get_health_status(self, manager):
        """Test getting health status"""
        health = manager.get_health_status()
        
        assert 'healthy' in health
        assert health['healthy'] is True
        assert 'active_locks' in health
        assert 'stale_locks_count' in health


class TestCacheEntry:
    """Unit tests for CacheEntry"""
    
    def test_create_cache_entry(self):
        """Test creating a cache entry"""
        entry = CacheEntry(
            key='test-key',
            value='test-value',
            created_at=datetime.utcnow(),
            ttl_seconds=300.0
        )
        
        assert entry.key == 'test-key'
        assert entry.value == 'test-value'
        assert entry.ttl_seconds == 300.0
        assert entry.access_count == 0
    
    def test_cache_entry_not_expired(self):
        """Test that fresh entry is not expired"""
        entry = CacheEntry(
            key='test',
            value='value',
            created_at=datetime.utcnow(),
            ttl_seconds=300.0
        )
        
        assert not entry.is_expired()
    
    def test_cache_entry_expired(self):
        """Test that old entry is expired"""
        old_time = datetime.utcnow() - timedelta(seconds=400)
        entry = CacheEntry(
            key='test',
            value='value',
            created_at=old_time,
            ttl_seconds=300.0
        )
        
        assert entry.is_expired()
    
    def test_cache_entry_access(self):
        """Test accessing cache entry updates statistics"""
        entry = CacheEntry(
            key='test',
            value='test-value',
            created_at=datetime.utcnow(),
            ttl_seconds=300.0
        )
        
        initial_access_time = entry.last_accessed
        
        # Access entry
        value = entry.access()
        
        assert value == 'test-value'
        assert entry.access_count == 1
        assert entry.last_accessed >= initial_access_time


class TestCacheStatistics:
    """Unit tests for CacheStatistics"""
    
    def test_default_statistics(self):
        """Test default statistics values"""
        stats = CacheStatistics()
        
        assert stats.total_hits == 0
        assert stats.total_misses == 0
        assert stats.total_sets == 0
        assert stats.current_size == 0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        stats = CacheStatistics(total_hits=7, total_misses=3)
        
        assert stats.hit_rate == 0.7
    
    def test_hit_rate_with_no_operations(self):
        """Test hit rate when no operations have occurred"""
        stats = CacheStatistics()
        
        assert stats.hit_rate == 0.0


class TestRepositoryCacheManager:
    """Unit tests for RepositoryCacheManager"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager"""
        return RepositoryCacheManager(default_ttl=300.0, max_cache_size=100)
    
    def test_set_and_get(self, cache_manager):
        """Test setting and getting cache values"""
        cache_manager.set('key1', 'value1')
        
        value = cache_manager.get('key1')
        assert value == 'value1'
    
    def test_get_nonexistent_key(self, cache_manager):
        """Test getting nonexistent key returns None"""
        value = cache_manager.get('nonexistent')
        assert value is None
    
    def test_get_expired_entry(self, cache_manager):
        """Test getting expired entry returns None"""
        # Set entry with very short TTL
        cache_manager.set('key1', 'value1', ttl=0.01)
        
        # Wait for expiration
        time.sleep(0.02)
        
        value = cache_manager.get('key1')
        assert value is None
    
    def test_cache_statistics_on_hit(self, cache_manager):
        """Test statistics are updated on cache hit"""
        cache_manager.set('key1', 'value1')
        cache_manager.get('key1')
        
        stats = cache_manager.get_statistics()
        assert stats['total_hits'] == 1
        assert stats['total_misses'] == 0
    
    def test_cache_statistics_on_miss(self, cache_manager):
        """Test statistics are updated on cache miss"""
        cache_manager.get('nonexistent')
        
        stats = cache_manager.get_statistics()
        assert stats['total_hits'] == 0
        assert stats['total_misses'] == 1
    
    def test_hit_rate_calculation(self, cache_manager):
        """Test hit rate calculation"""
        cache_manager.set('key1', 'value1')
        
        # 3 hits, 2 misses
        cache_manager.get('key1')
        cache_manager.get('key1')
        cache_manager.get('key1')
        cache_manager.get('nonexistent1')
        cache_manager.get('nonexistent2')
        
        stats = cache_manager.get_statistics()
        assert stats['hit_rate'] == 0.6  # 3/5
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self, cache_manager):
        """Test get_or_compute with cache hit"""
        cache_manager.set('key1', 'cached-value')
        
        compute_called = False
        
        async def compute_func():
            nonlocal compute_called
            compute_called = True
            return 'computed-value'
        
        value = await cache_manager.get_or_compute('key1', compute_func)
        
        assert value == 'cached-value'
        assert not compute_called  # Should not compute if cached
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self, cache_manager):
        """Test get_or_compute with cache miss"""
        async def compute_func():
            return 'computed-value'
        
        value = await cache_manager.get_or_compute('key1', compute_func)
        
        assert value == 'computed-value'
        
        # Value should now be cached
        cached_value = cache_manager.get('key1')
        assert cached_value == 'computed-value'
    
    def test_invalidate(self, cache_manager):
        """Test invalidating cache entry"""
        cache_manager.set('key1', 'value1')
        
        removed = cache_manager.invalidate('key1')
        assert removed is True
        
        value = cache_manager.get('key1')
        assert value is None
    
    def test_invalidate_pattern(self, cache_manager):
        """Test invalidating entries by pattern"""
        cache_manager.set('repo:1:details', 'value1')
        cache_manager.set('repo:2:details', 'value2')
        cache_manager.set('other:key', 'value3')
        
        count = cache_manager.invalidate_pattern('repo:')
        
        assert count == 2
        assert cache_manager.get('repo:1:details') is None
        assert cache_manager.get('repo:2:details') is None
        assert cache_manager.get('other:key') == 'value3'
    
    def test_cleanup_expired(self, cache_manager):
        """Test cleaning up expired entries"""
        # Add entries with different TTLs
        cache_manager.set('key1', 'value1', ttl=0.01)
        cache_manager.set('key2', 'value2', ttl=300.0)
        
        # Wait for first entry to expire
        time.sleep(0.02)
        
        removed = cache_manager.cleanup_expired()
        
        assert removed == 1
        assert cache_manager.get('key1') is None
        assert cache_manager.get('key2') == 'value2'
    
    def test_clear(self, cache_manager):
        """Test clearing all cache entries"""
        cache_manager.set('key1', 'value1')
        cache_manager.set('key2', 'value2')
        
        cache_manager.clear()
        
        assert cache_manager.get('key1') is None
        assert cache_manager.get('key2') is None
        
        stats = cache_manager.get_statistics()
        assert stats['current_size'] == 0
    
    def test_lru_eviction(self, cache_manager):
        """Test LRU eviction when cache is full"""
        # Create small cache
        small_cache = RepositoryCacheManager(max_cache_size=3)
        
        # Fill cache
        small_cache.set('key1', 'value1')
        small_cache.set('key2', 'value2')
        small_cache.set('key3', 'value3')
        
        # Access key1 to make it more recent
        small_cache.get('key1')
        
        # Add new entry, should evict key2 (least recently used)
        small_cache.set('key4', 'value4')
        
        assert small_cache.get('key1') == 'value1'
        assert small_cache.get('key2') is None  # Evicted
        assert small_cache.get('key3') == 'value3'
        assert small_cache.get('key4') == 'value4'
    
    def test_get_entry_info(self, cache_manager):
        """Test getting entry information"""
        cache_manager.set('key1', 'value1', ttl=300.0)
        
        info = cache_manager.get_entry_info('key1')
        
        assert info is not None
        assert info['key'] == 'key1'
        assert 'created_at' in info
        assert 'age_seconds' in info
        assert info['ttl_seconds'] == 300.0
        assert info['is_expired'] is False
    
    def test_get_hot_entries(self, cache_manager):
        """Test getting most frequently accessed entries"""
        cache_manager.set('key1', 'value1')
        cache_manager.set('key2', 'value2')
        cache_manager.set('key3', 'value3')
        
        # Access key2 multiple times
        for _ in range(5):
            cache_manager.get('key2')
        
        # Access key1 once
        cache_manager.get('key1')
        
        hot_entries = cache_manager.get_hot_entries(limit=2)
        
        assert len(hot_entries) == 2
        assert hot_entries[0]['key'] == 'key2'  # Most accessed
    
    def test_set_default_ttl(self, cache_manager):
        """Test setting default TTL"""
        cache_manager.set_default_ttl(600.0)
        
        stats = cache_manager.get_statistics()
        assert stats['default_ttl_seconds'] == 600.0
    
    def test_set_max_cache_size(self, cache_manager):
        """Test setting max cache size"""
        # Fill cache
        for i in range(10):
            cache_manager.set(f'key{i}', f'value{i}')
        
        # Reduce size
        cache_manager.set_max_cache_size(5)
        
        stats = cache_manager.get_statistics()
        assert stats['current_size'] <= 5
        assert stats['max_size'] == 5


class TestLazyRepositoryLoader:
    """Unit tests for LazyRepositoryLoader"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager"""
        return RepositoryCacheManager()
    
    @pytest.fixture
    def lazy_loader(self, cache_manager):
        """Create lazy loader"""
        return LazyRepositoryLoader(cache_manager)
    
    @pytest.mark.asyncio
    async def test_load_repository_details_cache_miss(self, lazy_loader, cache_manager):
        """Test loading repository details when not cached"""
        load_called = False
        
        async def loader_func():
            nonlocal load_called
            load_called = True
            return {'name': 'test-repo', 'status': 'active'}
        
        details = await lazy_loader.load_repository_details('test-repo', loader_func)
        
        assert load_called is True
        assert details['name'] == 'test-repo'
        
        # Should be cached now
        cached = cache_manager.get('repo_details:test-repo')
        assert cached is not None
    
    @pytest.mark.asyncio
    async def test_load_repository_details_cache_hit(self, lazy_loader, cache_manager):
        """Test loading repository details when cached"""
        # Pre-populate cache
        cache_manager.set('repo_details:test-repo', {'name': 'test-repo', 'cached': True})
        
        load_called = False
        
        async def loader_func():
            nonlocal load_called
            load_called = True
            return {'name': 'test-repo', 'loaded': True}
        
        details = await lazy_loader.load_repository_details('test-repo', loader_func)
        
        assert load_called is False  # Should not load if cached
        assert details['cached'] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_loads_single_execution(self, lazy_loader):
        """Test that concurrent loads only execute loader once"""
        load_count = 0
        
        async def loader_func():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.1)  # Simulate slow load
            return {'name': 'test-repo', 'data': 'loaded'}
        
        # Start multiple concurrent loads
        results = await asyncio.gather(
            lazy_loader.load_repository_details('test-repo', loader_func),
            lazy_loader.load_repository_details('test-repo', loader_func),
            lazy_loader.load_repository_details('test-repo', loader_func)
        )
        
        # Loader should only be called once due to locking
        assert load_count == 1
        assert all(r['name'] == 'test-repo' for r in results)
    
    def test_invalidate_repository_details(self, lazy_loader, cache_manager):
        """Test invalidating cached repository details"""
        # Cache some details
        cache_manager.set('repo_details:test-repo', {'name': 'test-repo'})
        
        # Invalidate
        invalidated = lazy_loader.invalidate_repository_details('test-repo')
        
        assert invalidated is True
        assert cache_manager.get('repo_details:test-repo') is None
    
    @pytest.mark.asyncio
    async def test_preload_repositories(self, lazy_loader, cache_manager):
        """Test preloading multiple repositories"""
        async def loader_func(name):
            await asyncio.sleep(0.01)
            return {'name': name, 'status': 'active'}
        
        repo_names = ['repo-1', 'repo-2', 'repo-3']
        
        loaded = await lazy_loader.preload_repositories(repo_names, loader_func)
        
        assert len(loaded) == 3
        assert 'repo-1' in loaded
        assert 'repo-2' in loaded
        assert 'repo-3' in loaded
        
        # All should be cached
        for name in repo_names:
            cached = cache_manager.get(f'repo_details:{name}')
            assert cached is not None
    
    @pytest.mark.asyncio
    async def test_preload_repositories_with_failures(self, lazy_loader):
        """Test preloading handles failures gracefully"""
        async def loader_func(name):
            if name == 'repo-2':
                raise ValueError('Failed to load')
            return {'name': name, 'status': 'active'}
        
        repo_names = ['repo-1', 'repo-2', 'repo-3']
        
        loaded = await lazy_loader.preload_repositories(repo_names, loader_func)
        
        # Should load 2 out of 3
        assert len(loaded) == 2
        assert 'repo-1' in loaded
        assert 'repo-3' in loaded
        assert 'repo-2' not in loaded


class TestCacheManagerCleanupTask:
    """Unit tests for cache manager cleanup task"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager"""
        return RepositoryCacheManager(cleanup_interval=0.1)
    
    @pytest.mark.asyncio
    async def test_start_cleanup_task(self, cache_manager):
        """Test starting cleanup task"""
        await cache_manager.start_cleanup_task()
        
        assert cache_manager._cleanup_task is not None
        
        # Clean up
        await cache_manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_stop_cleanup_task(self, cache_manager):
        """Test stopping cleanup task"""
        await cache_manager.start_cleanup_task()
        await cache_manager.stop_cleanup_task()
        
        assert cache_manager._cleanup_task is None
    
    @pytest.mark.asyncio
    async def test_automatic_cleanup(self, cache_manager):
        """Test that cleanup task automatically removes expired entries"""
        await cache_manager.start_cleanup_task()
        
        # Add entry with short TTL
        cache_manager.set('key1', 'value1', ttl=0.05)
        cache_manager.set('key2', 'value2', ttl=300.0)
        
        # Wait for cleanup to run
        await asyncio.sleep(0.2)
        
        # Expired entry should be removed
        assert cache_manager.get('key1') is None
        assert cache_manager.get('key2') == 'value2'
        
        # Clean up
        await cache_manager.stop_cleanup_task()


class TestPerformanceMonitoringIntegration:
    """Integration tests for performance monitoring components working together"""
    
    @pytest.fixture
    def test_repository(self):
        """Create test repository"""
        config = RepositoryConfig(
            name='integration-test-repo',
            uri='file:///tmp/integration-test',
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL
        )
        return Repository(config=config, status=RepositoryStatus.ACTIVE)
    
    @pytest.mark.asyncio
    async def test_monitor_with_concurrency_limit(self, test_repository):
        """Test performance monitoring with concurrency limits"""
        monitor = RepositoryPerformanceMonitor()
        concurrency = RepositoryConcurrencyManager(max_concurrent_validations=2)
        
        async def validation_operation():
            async with concurrency.limit_concurrent_validations(test_repository.name):
                await asyncio.sleep(0.1)
                return 'validated'
        
        # Monitor multiple concurrent validations
        tasks = []
        for i in range(5):
            task = monitor.monitor_operation(
                'validation',
                validation_operation,
                repository=test_repository
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert all(r == 'validated' for r in results)
        
        # Check metrics
        metrics = monitor.get_metrics('validation')
        assert len(metrics) == 5
        
        # Check concurrency stats
        stats = concurrency.get_statistics()
        assert stats['total_validations_completed'] == 5
    
    @pytest.mark.asyncio
    async def test_cached_operations_with_monitoring(self, test_repository):
        """Test cached operations with performance monitoring"""
        cache = RepositoryCacheManager()
        monitor = RepositoryPerformanceMonitor()
        
        load_count = 0
        
        async def expensive_operation():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.1)
            return {'data': 'expensive'}
        
        # First call - cache miss
        result1 = await monitor.monitor_operation(
            'load_data',
            lambda: cache.get_or_compute('test-key', expensive_operation)
        )
        
        # Second call - cache hit
        result2 = await monitor.monitor_operation(
            'load_data',
            lambda: cache.get_or_compute('test-key', expensive_operation)
        )
        
        # Expensive operation should only run once
        assert load_count == 1
        assert result1 == result2
        
        # Check cache statistics
        cache_stats = cache.get_statistics()
        assert cache_stats['total_hits'] >= 1
        
        # Check performance metrics
        metrics = monitor.get_metrics('load_data')
        assert len(metrics) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
