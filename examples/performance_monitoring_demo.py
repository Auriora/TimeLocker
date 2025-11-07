#!/usr/bin/env python3
"""
Performance Monitoring Demo for TimeLocker

This script demonstrates the performance monitoring, concurrency management,
and caching features for repository operations.
"""

import asyncio
import logging
from datetime import datetime

from TimeLocker.services import (
    RepositoryPerformanceMonitor,
    RepositoryConcurrencyManager,
    RepositoryCacheManager,
    LazyRepositoryLoader,
    PerformanceThresholds
)
from TimeLocker.interfaces.repository_management_models import (
    Repository,
    RepositoryConfig,
    RepositoryStatus,
    BackupEngine,
    RepositoryType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_performance_monitoring():
    """Demonstrate performance monitoring capabilities."""
    logger.info("=== Performance Monitoring Demo ===")
    
    # Create performance monitor with custom thresholds
    thresholds = PerformanceThresholds(
        validation_network=10.0,  # 10 seconds for network
        validation_local=2.0,     # 2 seconds for local
        listing=1.5,              # 1.5 seconds for listing
        configuration_update=0.5   # 0.5 seconds for updates
    )
    monitor = RepositoryPerformanceMonitor(thresholds)
    
    # Simulate some operations
    async def slow_validation():
        """Simulate a slow validation operation."""
        await asyncio.sleep(3.0)  # Exceeds local threshold
        return "validation_complete"
    
    async def fast_listing():
        """Simulate a fast listing operation."""
        await asyncio.sleep(0.5)
        return ["repo1", "repo2", "repo3"]
    
    # Create a mock repository
    repo = Repository(
        config=RepositoryConfig(
            name="test-repo",
            uri="/tmp/test-repo",
            engine=BackupEngine.RESTIC,
            type=RepositoryType.LOCAL,
            description="Test repository",
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_default=False,
            engine_config={}
        ),
        status=RepositoryStatus.ACTIVE
    )
    
    # Monitor operations
    logger.info("Running monitored validation (will exceed threshold)...")
    result = await monitor.monitor_operation(
        'validation',
        slow_validation,
        repository=repo
    )
    logger.info(f"Validation result: {result}")
    
    logger.info("Running monitored listing...")
    repos = await monitor.monitor_operation(
        'listing',
        fast_listing
    )
    logger.info(f"Listing result: {repos}")
    
    # Get statistics
    stats = monitor.get_statistics()
    logger.info(f"Performance statistics: {stats}")
    
    # Get warnings
    warnings = monitor.get_warnings()
    logger.info(f"Performance warnings: {len(warnings)}")
    for warning in warnings:
        logger.warning(str(warning))
    
    # Get recent performance summary
    summary = monitor.get_recent_performance_summary(minutes=5)
    logger.info(f"Recent performance summary: {summary}")


async def demo_concurrency_management():
    """Demonstrate concurrency management capabilities."""
    logger.info("\n=== Concurrency Management Demo ===")
    
    # Create concurrency manager
    manager = RepositoryConcurrencyManager(max_concurrent_validations=3)
    
    # Demonstrate exclusive locking
    logger.info("Testing exclusive repository locks...")
    
    async def locked_operation(repo_name: str, duration: float):
        """Simulate an operation that requires exclusive lock."""
        async with manager.acquire_repository_lock(repo_name, "test_operation"):
            logger.info(f"Lock acquired for {repo_name}")
            await asyncio.sleep(duration)
            logger.info(f"Lock released for {repo_name}")
    
    # Run concurrent operations on different repositories
    await asyncio.gather(
        locked_operation("repo1", 1.0),
        locked_operation("repo2", 1.0),
        locked_operation("repo3", 1.0)
    )
    
    # Demonstrate validation concurrency limiting
    logger.info("\nTesting concurrent validation limits...")
    
    async def mock_validation(repo_num: int):
        """Mock validation operation."""
        async with manager.limit_concurrent_validations(f"repo{repo_num}"):
            logger.info(f"Validating repo{repo_num}")
            await asyncio.sleep(1.0)
            logger.info(f"Completed repo{repo_num}")
            return f"result_{repo_num}"
    
    # Try to run 5 validations (only 3 will run concurrently)
    logger.info("Starting 5 validations (max 3 concurrent)...")
    results = await asyncio.gather(*[mock_validation(i) for i in range(1, 6)])
    logger.info(f"All validations complete: {results}")
    
    # Get statistics
    stats = manager.get_statistics()
    logger.info(f"Concurrency statistics: {stats}")
    
    # Get health status
    health = manager.get_health_status()
    logger.info(f"Health status: {health}")


async def demo_caching():
    """Demonstrate caching capabilities."""
    logger.info("\n=== Caching Demo ===")
    
    # Create cache manager
    cache = RepositoryCacheManager(
        default_ttl=10.0,  # 10 seconds TTL
        max_cache_size=100
    )
    
    # Start cleanup task
    await cache.start_cleanup_task()
    
    # Basic cache operations
    logger.info("Testing basic cache operations...")
    
    cache.set("repo1:metadata", {"name": "repo1", "size": 1024})
    cache.set("repo2:metadata", {"name": "repo2", "size": 2048})
    
    value1 = cache.get("repo1:metadata")
    logger.info(f"Retrieved from cache: {value1}")
    
    value2 = cache.get("nonexistent")
    logger.info(f"Cache miss: {value2}")
    
    # Demonstrate lazy loading
    logger.info("\nTesting lazy loading...")
    
    lazy_loader = LazyRepositoryLoader(cache)
    
    async def expensive_load():
        """Simulate expensive data loading."""
        logger.info("Loading expensive data...")
        await asyncio.sleep(2.0)
        return {"details": "expensive_data", "loaded_at": datetime.utcnow().isoformat()}
    
    # First call - will load
    logger.info("First call (will load)...")
    data1 = await lazy_loader.load_repository_details("repo3", expensive_load)
    logger.info(f"Loaded: {data1}")
    
    # Second call - will use cache
    logger.info("Second call (will use cache)...")
    data2 = await lazy_loader.load_repository_details("repo3", expensive_load)
    logger.info(f"From cache: {data2}")
    
    # Get cache statistics
    stats = cache.get_statistics()
    logger.info(f"Cache statistics: {stats}")
    
    # Get hot entries
    hot_entries = cache.get_hot_entries(limit=5)
    logger.info(f"Hot cache entries: {hot_entries}")
    
    # Cleanup
    await cache.stop_cleanup_task()


async def demo_integrated_usage():
    """Demonstrate integrated usage of all components."""
    logger.info("\n=== Integrated Usage Demo ===")
    
    # Create all components
    monitor = RepositoryPerformanceMonitor()
    concurrency = RepositoryConcurrencyManager(max_concurrent_validations=3)
    cache = RepositoryCacheManager()
    
    await cache.start_cleanup_task()
    
    # Simulate repository operations with all features
    async def validate_repository_with_features(repo_name: str):
        """Validate repository using all optimization features."""
        
        # Check cache first
        cache_key = f"{repo_name}:validation"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Using cached validation for {repo_name}")
            return cached_result
        
        # Perform validation with concurrency limit and performance monitoring
        async def do_validation():
            async with concurrency.limit_concurrent_validations(repo_name):
                async with concurrency.acquire_repository_lock(repo_name, "validation"):
                    logger.info(f"Validating {repo_name}...")
                    await asyncio.sleep(1.0)  # Simulate validation
                    return {"status": "valid", "timestamp": datetime.utcnow().isoformat()}
        
        result = await monitor.monitor_operation(
            'validation',
            do_validation
        )
        
        # Cache the result
        cache.set(cache_key, result, ttl=60.0)
        
        return result
    
    # Validate multiple repositories
    logger.info("Validating multiple repositories with all features...")
    repos = ["repo1", "repo2", "repo3", "repo4", "repo5"]
    
    results = await asyncio.gather(*[
        validate_repository_with_features(repo)
        for repo in repos
    ])
    
    logger.info(f"Validation results: {len(results)} repositories validated")
    
    # Show statistics from all components
    logger.info("\n=== Final Statistics ===")
    logger.info(f"Performance: {monitor.get_statistics()}")
    logger.info(f"Concurrency: {concurrency.get_statistics()}")
    logger.info(f"Cache: {cache.get_statistics()}")
    
    await cache.stop_cleanup_task()


async def main():
    """Run all demos."""
    try:
        await demo_performance_monitoring()
        await demo_concurrency_management()
        await demo_caching()
        await demo_integrated_usage()
        
        logger.info("\n=== All demos completed successfully! ===")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
