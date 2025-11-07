"""
Repository Cache Manager for TimeLocker

This module provides caching for repository metadata and status information
with TTL support and lazy loading for desktop optimization.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Callable, Awaitable, TypeVar, Generic
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL support."""
    key: str
    value: T
    created_at: datetime
    ttl_seconds: float
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def access(self) -> T:
        """Access cache entry and update statistics."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value


@dataclass
class CacheStatistics:
    """Statistics about cache usage."""
    total_hits: int = 0
    total_misses: int = 0
    total_sets: int = 0
    total_evictions: int = 0
    total_expirations: int = 0
    current_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.total_hits + self.total_misses
        if total == 0:
            return 0.0
        return self.total_hits / total


class RepositoryCacheManager:
    """
    Manages caching for repository metadata and status information.
    
    Provides:
    - TTL-based caching for frequently accessed data
    - Lazy loading for repository details
    - Cache statistics and monitoring
    - Automatic cache cleanup and eviction
    """
    
    def __init__(
        self,
        default_ttl: float = 300.0,  # 5 minutes
        max_cache_size: int = 1000,
        cleanup_interval: float = 60.0  # 1 minute
    ):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default TTL in seconds for cache entries
            max_cache_size: Maximum number of entries in cache
            cleanup_interval: Interval in seconds for automatic cleanup
        """
        self._default_ttl = default_ttl
        self._max_cache_size = max_cache_size
        self._cleanup_interval = cleanup_interval
        
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStatistics()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.debug(
            f"RepositoryCacheManager initialized with "
            f"default_ttl={default_ttl}s, max_size={max_cache_size}"
        )
    
    async def start_cleanup_task(self) -> None:
        """Start automatic cache cleanup task."""
        if self._cleanup_task is not None:
            logger.warning("Cleanup task already running")
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.debug("Cache cleanup task started")
    
    async def stop_cleanup_task(self) -> None:
        """Stop automatic cache cleanup task."""
        if self._cleanup_task is None:
            return
        
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        
        self._cleanup_task = None
        logger.debug("Cache cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Automatic cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats.total_misses += 1
            return None
        
        if entry.is_expired():
            self._remove_entry(key)
            self._stats.total_misses += 1
            self._stats.total_expirations += 1
            return None
        
        self._stats.total_hits += 1
        return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds (uses default if not provided)
        """
        # Check cache size and evict if necessary
        if len(self._cache) >= self._max_cache_size and key not in self._cache:
            self._evict_lru()
        
        ttl_seconds = ttl if ttl is not None else self._default_ttl
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.utcnow(),
            ttl_seconds=ttl_seconds
        )
        
        self._cache[key] = entry
        self._stats.total_sets += 1
        self._stats.current_size = len(self._cache)
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Awaitable[T]],
        ttl: Optional[float] = None
    ) -> T:
        """
        Get value from cache or compute if not found.
        
        This is useful for lazy loading - the value is only computed
        if it's not in the cache.
        
        Args:
            key: Cache key
            compute_func: Async function to compute value if not cached
            ttl: Optional TTL in seconds
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Compute value
        value = await compute_func()
        
        # Store in cache
        self.set(key, value, ttl)
        
        return value
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            bool: True if entry was removed, False if not found
        """
        return self._remove_entry(key)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (simple prefix matching)
            
        Returns:
            int: Number of entries invalidated
        """
        keys_to_remove = [
            key for key in self._cache.keys()
            if key.startswith(pattern)
        ]
        
        for key in keys_to_remove:
            self._remove_entry(key)
        
        return len(keys_to_remove)
    
    def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache."""
        if key in self._cache:
            del self._cache[key]
            self._stats.current_size = len(self._cache)
            return True
        return False
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        self._remove_entry(lru_key)
        self._stats.total_evictions += 1
        
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            int: Number of entries removed
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
            self._stats.total_expirations += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._stats.current_size = 0
        logger.debug(f"Cleared {count} cache entries")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return {
            'total_hits': self._stats.total_hits,
            'total_misses': self._stats.total_misses,
            'total_sets': self._stats.total_sets,
            'total_evictions': self._stats.total_evictions,
            'total_expirations': self._stats.total_expirations,
            'current_size': self._stats.current_size,
            'max_size': self._max_cache_size,
            'hit_rate': self._stats.hit_rate,
            'default_ttl_seconds': self._default_ttl
        }
    
    def reset_statistics(self) -> None:
        """Reset cache statistics (but keep cached data)."""
        self._stats = CacheStatistics(current_size=len(self._cache))
        logger.debug("Cache statistics reset")
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Dict[str, Any]]: Entry information if found
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        
        age = (datetime.utcnow() - entry.created_at).total_seconds()
        time_to_expiry = entry.ttl_seconds - age
        
        return {
            'key': entry.key,
            'created_at': entry.created_at.isoformat(),
            'last_accessed': entry.last_accessed.isoformat(),
            'access_count': entry.access_count,
            'age_seconds': age,
            'ttl_seconds': entry.ttl_seconds,
            'time_to_expiry_seconds': time_to_expiry,
            'is_expired': entry.is_expired()
        }
    
    def get_all_entries_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all cache entries.
        
        Returns:
            List[Dict[str, Any]]: List of entry information
        """
        return [
            self.get_entry_info(key)
            for key in self._cache.keys()
        ]
    
    def get_hot_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed cache entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List[Dict[str, Any]]: List of hot entries
        """
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda item: item[1].access_count,
            reverse=True
        )
        
        return [
            self.get_entry_info(key)
            for key, _ in sorted_entries[:limit]
        ]
    
    def set_default_ttl(self, ttl_seconds: float) -> None:
        """
        Set default TTL for cache entries.
        
        Args:
            ttl_seconds: TTL in seconds
        """
        self._default_ttl = ttl_seconds
        logger.debug(f"Default TTL set to {ttl_seconds}s")
    
    def set_max_cache_size(self, max_size: int) -> None:
        """
        Set maximum cache size.
        
        If the new size is smaller than current size, LRU entries will be evicted.
        
        Args:
            max_size: Maximum number of cache entries
        """
        self._max_cache_size = max_size
        
        # Evict entries if necessary
        while len(self._cache) > max_size:
            self._evict_lru()
        
        logger.debug(f"Maximum cache size set to {max_size}")


class LazyRepositoryLoader:
    """
    Provides lazy loading for repository details.
    
    Repository details are only loaded when accessed, minimizing startup time.
    """
    
    def __init__(self, cache_manager: RepositoryCacheManager):
        """
        Initialize lazy loader.
        
        Args:
            cache_manager: Cache manager for storing loaded data
        """
        self._cache_manager = cache_manager
        self._loading_locks: Dict[str, asyncio.Lock] = {}
        
        logger.debug("LazyRepositoryLoader initialized")
    
    async def load_repository_details(
        self,
        repository_name: str,
        loader_func: Callable[[], Awaitable[Any]],
        ttl: Optional[float] = None
    ) -> Any:
        """
        Load repository details with lazy loading and caching.
        
        Multiple concurrent requests for the same repository will only
        trigger one load operation.
        
        Args:
            repository_name: Repository name
            loader_func: Async function to load repository details
            ttl: Optional TTL for cached data
            
        Returns:
            Repository details
        """
        cache_key = f"repo_details:{repository_name}"
        
        # Get or create lock for this repository
        if repository_name not in self._loading_locks:
            self._loading_locks[repository_name] = asyncio.Lock()
        
        lock = self._loading_locks[repository_name]
        
        async with lock:
            # Try to get from cache
            cached_details = self._cache_manager.get(cache_key)
            if cached_details is not None:
                return cached_details
            
            # Load details
            logger.debug(f"Loading details for repository '{repository_name}'")
            details = await loader_func()
            
            # Cache details
            self._cache_manager.set(cache_key, details, ttl)
            
            return details
    
    def invalidate_repository_details(self, repository_name: str) -> bool:
        """
        Invalidate cached repository details.
        
        Args:
            repository_name: Repository name
            
        Returns:
            bool: True if cache was invalidated
        """
        cache_key = f"repo_details:{repository_name}"
        return self._cache_manager.invalidate(cache_key)
    
    async def preload_repositories(
        self,
        repository_names: List[str],
        loader_func: Callable[[str], Awaitable[Any]],
        ttl: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Preload multiple repositories concurrently.
        
        This can be used to warm up the cache during startup.
        
        Args:
            repository_names: List of repository names to preload
            loader_func: Async function to load repository details (takes repository name)
            ttl: Optional TTL for cached data
            
        Returns:
            Dict[str, Any]: Dictionary of repository name to details
        """
        async def load_single(name: str) -> tuple[str, Any]:
            """Load single repository."""
            details = await self.load_repository_details(
                name,
                lambda: loader_func(name),
                ttl
            )
            return name, details
        
        # Load all repositories concurrently
        tasks = [load_single(name) for name in repository_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        loaded = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to preload repository: {result}")
                continue
            
            name, details = result
            loaded[name] = details
        
        logger.info(f"Preloaded {len(loaded)}/{len(repository_names)} repositories")
        return loaded
