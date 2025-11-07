# Performance Optimization Guide

## Overview

TimeLocker includes comprehensive performance monitoring, concurrency management, and caching features optimized for desktop usage. These features ensure responsive repository operations while managing up to 20 repositories efficiently.

## Components

### 1. Repository Performance Monitor

The `RepositoryPerformanceMonitor` tracks operation durations, checks against thresholds, and provides performance warnings with specific suggestions.

#### Features

- **Operation Tracking**: Records duration and success/failure for all operations
- **Threshold Checking**: Compares operations against desktop-appropriate thresholds
- **Performance Warnings**: Generates warnings with specific improvement suggestions
- **Statistics**: Provides detailed performance metrics and trends

#### Performance Thresholds

Default thresholds optimized for desktop usage:

- **Network Validation**: 15 seconds
- **Local Validation**: 3 seconds
- **Repository Listing**: 2 seconds
- **Configuration Update**: 1 second

#### Usage Example

```python
from TimeLocker.services import RepositoryPerformanceMonitor

# Create monitor
monitor = RepositoryPerformanceMonitor()

# Monitor an operation
async def my_operation():
    # Your operation code
    pass

result = await monitor.monitor_operation(
    'validation',
    my_operation,
    repository=repository
)

# Get statistics
stats = monitor.get_statistics()
print(f"Average duration: {stats['operations']['validation']['avg_duration']}")

# Get warnings
warnings = monitor.get_warnings()
for warning in warnings:
    print(warning)
```

### 2. Repository Concurrency Manager

The `RepositoryConcurrencyManager` manages concurrent operations with semaphore-based limiting and exclusive locking.

#### Features

- **Exclusive Locking**: Prevents concurrent modification of repository configurations
- **Validation Limiting**: Limits parallel validations (default: 3 concurrent)
- **Lock Timeout**: Prevents deadlocks with configurable timeouts
- **Stale Lock Detection**: Identifies and recovers from stuck operations

#### Usage Example

```python
from TimeLocker.services import RepositoryConcurrencyManager

# Create manager
manager = RepositoryConcurrencyManager(max_concurrent_validations=3)

# Acquire exclusive lock
async with manager.acquire_repository_lock("my-repo", "backup"):
    # Perform repository operation
    pass

# Limit concurrent validations
async with manager.limit_concurrent_validations("my-repo"):
    # Perform validation
    pass

# Batch validate with concurrency limit
results = await manager.validate_with_concurrency_limit(
    repositories,
    validation_func
)
```

### 3. Repository Cache Manager

The `RepositoryCacheManager` provides TTL-based caching for repository metadata and status information.

#### Features

- **TTL-Based Caching**: Automatic expiration of stale data
- **LRU Eviction**: Removes least recently used entries when cache is full
- **Lazy Loading**: Load data only when needed
- **Cache Statistics**: Track hit rates and performance

#### Usage Example

```python
from TimeLocker.services import RepositoryCacheManager, LazyRepositoryLoader

# Create cache manager
cache = RepositoryCacheManager(
    default_ttl=300.0,  # 5 minutes
    max_cache_size=1000
)

# Start automatic cleanup
await cache.start_cleanup_task()

# Basic caching
cache.set("repo:metadata", metadata, ttl=600.0)
metadata = cache.get("repo:metadata")

# Lazy loading
lazy_loader = LazyRepositoryLoader(cache)

async def load_details():
    # Expensive operation
    return await fetch_repository_details()

details = await lazy_loader.load_repository_details(
    "my-repo",
    load_details
)

# Get statistics
stats = cache.get_statistics()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

## Integration with Repository Manager

The `RepositoryManager` automatically uses all three components:

```python
from TimeLocker.services import RepositoryManager

# Create repository manager (components are created automatically)
manager = RepositoryManager()

# Initialize
manager.initialize(context)

# Operations automatically use performance monitoring, concurrency management, and caching
repositories = await manager.list_repositories()  # Monitored and cached
result = await manager.validate_repository(repo)  # Monitored and concurrency-limited

# Get comprehensive statistics
stats = manager.get_repository_statistics()
print(stats['performance_monitoring'])
print(stats['concurrency_management'])
print(stats['cache_statistics'])
```

## Desktop Optimization Guidelines

### Repository Count

- **Target**: Up to 20 repositories
- **Maximum**: 1000 repositories (with degraded performance)
- **Recommendation**: Use repository groups for large deployments

### Performance Targets

- **Listing**: < 2 seconds for 20 repositories
- **Validation**: < 15 seconds for network, < 3 seconds for local
- **Configuration Updates**: < 1 second

### Concurrency Limits

- **Validations**: 3 parallel operations (desktop-appropriate)
- **Locks**: Unlimited (but operations are serialized per repository)

### Caching Strategy

- **Metadata TTL**: 5 minutes (default)
- **Validation Results**: 1 minute (recommended)
- **Repository Lists**: 30 seconds (recommended)

## Monitoring and Troubleshooting

### Performance Warnings

When operations exceed thresholds, the system generates warnings with suggestions:

```
Performance warning: validation took 18.45s (threshold: 15.00s) for repository 'my-repo'
Suggestions: Check network connectivity, Consider increasing timeout settings, Verify repository endpoint is accessible
```

### Stale Lock Detection

The concurrency manager can detect stale locks:

```python
# Check for stale locks (held > 5 minutes)
stale_locks = manager._concurrency_manager.get_stale_locks(max_age_seconds=300.0)

for lock in stale_locks:
    print(f"Stale lock: {lock.repository_name} held by {lock.holder}")
    
    # Force release if necessary
    await manager._concurrency_manager.force_release_lock(lock.repository_name)
```

### Cache Effectiveness

Monitor cache hit rates to ensure effective caching:

```python
stats = cache.get_statistics()
hit_rate = stats['hit_rate']

if hit_rate < 0.5:  # Less than 50% hit rate
    print("Consider increasing cache TTL or size")
```

## Best Practices

1. **Use Lazy Loading**: Load repository details only when needed
2. **Cache Validation Results**: Avoid repeated validations of the same repository
3. **Monitor Performance**: Regularly check performance statistics
4. **Adjust Thresholds**: Customize thresholds based on your environment
5. **Limit Concurrent Operations**: Use the concurrency manager for all repository operations
6. **Handle Warnings**: Act on performance warnings to maintain responsiveness

## Example: Complete Integration

```python
import asyncio
from TimeLocker.services import RepositoryManager
from TimeLocker.interfaces.integration_data_models import ServiceContext

async def main():
    # Create and initialize repository manager
    manager = RepositoryManager()
    context = ServiceContext(config={}, runtime_info={})
    manager.initialize(context)
    
    # List repositories (cached and monitored)
    repos = await manager.list_repositories()
    print(f"Found {len(repos)} repositories")
    
    # Batch validate with concurrency limits
    results = await manager.batch_validate_repositories()
    
    for repo_name, result in results.items():
        if result.success:
            print(f"✓ {repo_name}: Valid")
        else:
            print(f"✗ {repo_name}: {result.error_details}")
    
    # Get comprehensive statistics
    stats = manager.get_repository_statistics()
    
    print("\nPerformance Statistics:")
    print(f"  Total operations: {stats['performance_monitoring']['total_operations']}")
    print(f"  Cache hit rate: {stats['cache_statistics']['hit_rate']:.2%}")
    print(f"  Active validations: {stats['concurrency_management']['current_active_validations']}")
    
    # Cleanup
    manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

- [Repository Management Guide](../user/repository-management-guide.md)
- [Performance Monitoring Demo](../../../examples/performance_monitoring_demo.py)
- [API Reference](../../2-architecture/api-reference.md)
