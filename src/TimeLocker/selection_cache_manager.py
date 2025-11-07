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

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .pattern_engine import CompiledPatternSet
from .selection_models import (
    PatternRule,
    SelectionConfig,
    SelectionDecision,
    SelectionTemplate
)

logger = logging.getLogger(__name__)


@dataclass
class CacheStatistics:
    """
    Statistics for cache operations.
    
    Attributes:
        total_requests: Total number of cache requests
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of cache evictions
        hit_ratio: Cache hit ratio (0.0-1.0)
        average_hit_time_ms: Average time for cache hits
        average_miss_time_ms: Average time for cache misses
    """
    total_requests: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    hit_ratio: float = 0.0
    average_hit_time_ms: float = 0.0
    average_miss_time_ms: float = 0.0
    
    def record_hit(self, operation_type: str, time_ms: float = 0.0) -> None:
        """Record a cache hit"""
        self.total_requests += 1
        self.hits += 1
        self._update_hit_ratio()
        if time_ms > 0:
            self._update_average_hit_time(time_ms)
    
    def record_miss(self, operation_type: str, time_ms: float = 0.0) -> None:
        """Record a cache miss"""
        self.total_requests += 1
        self.misses += 1
        self._update_hit_ratio()
        if time_ms > 0:
            self._update_average_miss_time(time_ms)
    
    def record_eviction(self) -> None:
        """Record a cache eviction"""
        self.evictions += 1
    
    def _update_hit_ratio(self) -> None:
        """Update the hit ratio"""
        if self.total_requests > 0:
            self.hit_ratio = self.hits / self.total_requests
    
    def _update_average_hit_time(self, time_ms: float) -> None:
        """Update average hit time"""
        if self.hits > 1:
            self.average_hit_time_ms = (
                (self.average_hit_time_ms * (self.hits - 1) + time_ms) / self.hits
            )
        else:
            self.average_hit_time_ms = time_ms
    
    def _update_average_miss_time(self, time_ms: float) -> None:
        """Update average miss time"""
        if self.misses > 1:
            self.average_miss_time_ms = (
                (self.average_miss_time_ms * (self.misses - 1) + time_ms) / self.misses
            )
        else:
            self.average_miss_time_ms = time_ms


class LRUCache:
    """
    Least Recently Used (LRU) cache implementation.
    
    Provides efficient caching with automatic eviction of least recently
    used items when the cache reaches its maximum size.
    """
    
    def __init__(self, maxsize: int = 1000):
        """
        Initialize LRU cache.
        
        Args:
            maxsize: Maximum number of items to cache
        """
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._access_times: Dict[str, float] = {}
        self._eviction_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._access_times[key] = time.time()
            return self._cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """
        Put item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self._cache:
            # Update existing item
            self._cache.move_to_end(key)
        else:
            # Add new item
            if len(self._cache) >= self.maxsize:
                # Evict least recently used item
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                del self._access_times[evicted_key]
                self._eviction_count += 1
            
            self._cache[key] = value
        
        self._access_times[key] = time.time()
    
    def clear(self) -> None:
        """Clear the cache"""
        self._cache.clear()
        self._access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)
    
    def get_eviction_count(self) -> int:
        """Get number of evictions"""
        return self._eviction_count
    
    def get_access_time(self, key: str) -> Optional[float]:
        """Get last access time for a key"""
        return self._access_times.get(key)


class SelectionCacheManager:
    """
    Intelligent caching manager for selection operations.
    
    Provides multi-level caching for patterns, path evaluations, and templates
    with automatic cache management and performance optimization.
    """
    
    # Default cache sizes
    PATTERN_CACHE_SIZE = 1000
    PATH_EVALUATION_CACHE_SIZE = 10000
    TEMPLATE_CACHE_SIZE = 100
    DIRECTORY_CACHE_SIZE = 5000
    
    def __init__(
        self,
        pattern_cache_size: Optional[int] = None,
        path_cache_size: Optional[int] = None,
        template_cache_size: Optional[int] = None,
        directory_cache_size: Optional[int] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            pattern_cache_size: Size of pattern compilation cache
            path_cache_size: Size of path evaluation cache
            template_cache_size: Size of template cache
            directory_cache_size: Size of directory traversal cache
        """
        # Initialize caches
        self.pattern_cache = LRUCache(
            maxsize=pattern_cache_size or self.PATTERN_CACHE_SIZE
        )
        self.path_evaluation_cache = LRUCache(
            maxsize=path_cache_size or self.PATH_EVALUATION_CACHE_SIZE
        )
        self.template_cache = LRUCache(
            maxsize=template_cache_size or self.TEMPLATE_CACHE_SIZE
        )
        self.directory_cache = LRUCache(
            maxsize=directory_cache_size or self.DIRECTORY_CACHE_SIZE
        )
        
        # Statistics
        self.pattern_stats = CacheStatistics()
        self.path_stats = CacheStatistics()
        self.template_stats = CacheStatistics()
        self.directory_stats = CacheStatistics()
        
        logger.info(
            f"Initialized cache manager: "
            f"patterns={self.pattern_cache.maxsize}, "
            f"paths={self.path_evaluation_cache.maxsize}, "
            f"templates={self.template_cache.maxsize}, "
            f"directories={self.directory_cache.maxsize}"
        )
    
    def get_cached_pattern_compilation(
        self,
        patterns: List[PatternRule]
    ) -> Optional[CompiledPatternSet]:
        """
        Get cached compiled patterns.
        
        Args:
            patterns: List of pattern rules
            
        Returns:
            Cached CompiledPatternSet or None
        """
        start_time = time.time()
        cache_key = self._generate_pattern_cache_key(patterns)
        
        compiled_patterns = self.pattern_cache.get(cache_key)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if compiled_patterns:
            self.pattern_stats.record_hit('pattern_compilation', elapsed_ms)
            logger.debug(f"Pattern cache hit for key {cache_key[:8]}...")
        else:
            self.pattern_stats.record_miss('pattern_compilation', elapsed_ms)
        
        return compiled_patterns
    
    def cache_pattern_compilation(
        self,
        patterns: List[PatternRule],
        compiled_patterns: CompiledPatternSet
    ) -> None:
        """
        Cache compiled patterns.
        
        Args:
            patterns: List of pattern rules
            compiled_patterns: Compiled pattern set to cache
        """
        cache_key = self._generate_pattern_cache_key(patterns)
        self.pattern_cache.put(cache_key, compiled_patterns)
        logger.debug(f"Cached pattern compilation with key {cache_key[:8]}...")
    
    def get_cached_path_evaluation(
        self,
        path: Path,
        config_hash: str
    ) -> Optional[SelectionDecision]:
        """
        Get cached path evaluation result.
        
        Args:
            path: Path that was evaluated
            config_hash: Hash of the selection configuration
            
        Returns:
            Cached SelectionDecision or None
        """
        start_time = time.time()
        cache_key = self._generate_path_cache_key(path, config_hash)
        
        decision = self.path_evaluation_cache.get(cache_key)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if decision:
            self.path_stats.record_hit('path_evaluation', elapsed_ms)
        else:
            self.path_stats.record_miss('path_evaluation', elapsed_ms)
        
        return decision
    
    def cache_path_evaluation(
        self,
        path: Path,
        config_hash: str,
        decision: SelectionDecision
    ) -> None:
        """
        Cache path evaluation result.
        
        Args:
            path: Path that was evaluated
            config_hash: Hash of the selection configuration
            decision: Selection decision to cache
        """
        cache_key = self._generate_path_cache_key(path, config_hash)
        self.path_evaluation_cache.put(cache_key, decision)
    
    def get_cached_template(self, template_id: str) -> Optional[SelectionTemplate]:
        """
        Get cached selection template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Cached SelectionTemplate or None
        """
        start_time = time.time()
        
        template = self.template_cache.get(template_id)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if template:
            self.template_stats.record_hit('template', elapsed_ms)
        else:
            self.template_stats.record_miss('template', elapsed_ms)
        
        return template
    
    def cache_template(self, template: SelectionTemplate) -> None:
        """
        Cache selection template.
        
        Args:
            template: Selection template to cache
        """
        self.template_cache.put(template.id, template)
        logger.debug(f"Cached template {template.id}")
    
    def get_cached_directory_contents(
        self,
        directory: Path
    ) -> Optional[List[Path]]:
        """
        Get cached directory contents.
        
        Args:
            directory: Directory path
            
        Returns:
            Cached list of paths or None
        """
        start_time = time.time()
        cache_key = str(directory)
        
        contents = self.directory_cache.get(cache_key)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        if contents:
            self.directory_stats.record_hit('directory', elapsed_ms)
        else:
            self.directory_stats.record_miss('directory', elapsed_ms)
        
        return contents
    
    def cache_directory_contents(
        self,
        directory: Path,
        contents: List[Path]
    ) -> None:
        """
        Cache directory contents.
        
        Args:
            directory: Directory path
            contents: List of paths in the directory
        """
        cache_key = str(directory)
        self.directory_cache.put(cache_key, contents)
    
    def invalidate_path_cache(self, path: Optional[Path] = None) -> None:
        """
        Invalidate path evaluation cache.
        
        Args:
            path: Optional specific path to invalidate (invalidates all if None)
        """
        if path is None:
            self.path_evaluation_cache.clear()
            logger.info("Cleared entire path evaluation cache")
        else:
            # In a real implementation, we would need to track which cache keys
            # correspond to which paths. For now, we just clear the entire cache.
            self.path_evaluation_cache.clear()
            logger.info(f"Invalidated path cache for {path}")
    
    def invalidate_directory_cache(self, directory: Optional[Path] = None) -> None:
        """
        Invalidate directory contents cache.
        
        Args:
            directory: Optional specific directory to invalidate (invalidates all if None)
        """
        if directory is None:
            self.directory_cache.clear()
            logger.info("Cleared entire directory cache")
        else:
            cache_key = str(directory)
            # Remove from cache if present
            if self.directory_cache.get(cache_key) is not None:
                self.directory_cache.clear()  # Simplified - clear all
                logger.info(f"Invalidated directory cache for {directory}")
    
    def clear_all_caches(self) -> None:
        """Clear all caches"""
        self.pattern_cache.clear()
        self.path_evaluation_cache.clear()
        self.template_cache.clear()
        self.directory_cache.clear()
        logger.info("Cleared all caches")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'pattern_cache': {
                'size': self.pattern_cache.size(),
                'maxsize': self.pattern_cache.maxsize,
                'utilization': self.pattern_cache.size() / self.pattern_cache.maxsize,
                'evictions': self.pattern_cache.get_eviction_count(),
                'statistics': {
                    'total_requests': self.pattern_stats.total_requests,
                    'hits': self.pattern_stats.hits,
                    'misses': self.pattern_stats.misses,
                    'hit_ratio': self.pattern_stats.hit_ratio,
                    'average_hit_time_ms': self.pattern_stats.average_hit_time_ms,
                    'average_miss_time_ms': self.pattern_stats.average_miss_time_ms
                }
            },
            'path_evaluation_cache': {
                'size': self.path_evaluation_cache.size(),
                'maxsize': self.path_evaluation_cache.maxsize,
                'utilization': self.path_evaluation_cache.size() / self.path_evaluation_cache.maxsize,
                'evictions': self.path_evaluation_cache.get_eviction_count(),
                'statistics': {
                    'total_requests': self.path_stats.total_requests,
                    'hits': self.path_stats.hits,
                    'misses': self.path_stats.misses,
                    'hit_ratio': self.path_stats.hit_ratio,
                    'average_hit_time_ms': self.path_stats.average_hit_time_ms,
                    'average_miss_time_ms': self.path_stats.average_miss_time_ms
                }
            },
            'template_cache': {
                'size': self.template_cache.size(),
                'maxsize': self.template_cache.maxsize,
                'utilization': self.template_cache.size() / self.template_cache.maxsize,
                'evictions': self.template_cache.get_eviction_count(),
                'statistics': {
                    'total_requests': self.template_stats.total_requests,
                    'hits': self.template_stats.hits,
                    'misses': self.template_stats.misses,
                    'hit_ratio': self.template_stats.hit_ratio,
                    'average_hit_time_ms': self.template_stats.average_hit_time_ms,
                    'average_miss_time_ms': self.template_stats.average_miss_time_ms
                }
            },
            'directory_cache': {
                'size': self.directory_cache.size(),
                'maxsize': self.directory_cache.maxsize,
                'utilization': self.directory_cache.size() / self.directory_cache.maxsize,
                'evictions': self.directory_cache.get_eviction_count(),
                'statistics': {
                    'total_requests': self.directory_stats.total_requests,
                    'hits': self.directory_stats.hits,
                    'misses': self.directory_stats.misses,
                    'hit_ratio': self.directory_stats.hit_ratio,
                    'average_hit_time_ms': self.directory_stats.average_hit_time_ms,
                    'average_miss_time_ms': self.directory_stats.average_miss_time_ms
                }
            },
            'overall': {
                'total_cache_size': (
                    self.pattern_cache.size() +
                    self.path_evaluation_cache.size() +
                    self.template_cache.size() +
                    self.directory_cache.size()
                ),
                'total_maxsize': (
                    self.pattern_cache.maxsize +
                    self.path_evaluation_cache.maxsize +
                    self.template_cache.maxsize +
                    self.directory_cache.maxsize
                ),
                'total_evictions': (
                    self.pattern_cache.get_eviction_count() +
                    self.path_evaluation_cache.get_eviction_count() +
                    self.template_cache.get_eviction_count() +
                    self.directory_cache.get_eviction_count()
                )
            }
        }
    
    def optimize_cache_sizes(self, usage_stats: Dict[str, Any]) -> Dict[str, int]:
        """
        Optimize cache sizes based on usage statistics.
        
        Args:
            usage_stats: Usage statistics from cache operations
            
        Returns:
            Dictionary with recommended cache sizes
        """
        recommendations = {}
        
        # Analyze pattern cache usage
        pattern_utilization = self.pattern_cache.size() / self.pattern_cache.maxsize
        if pattern_utilization > 0.9 and self.pattern_stats.evictions > 100:
            # High utilization and many evictions - increase size
            recommendations['pattern_cache'] = int(self.pattern_cache.maxsize * 1.5)
        elif pattern_utilization < 0.3:
            # Low utilization - decrease size
            recommendations['pattern_cache'] = int(self.pattern_cache.maxsize * 0.7)
        
        # Analyze path evaluation cache usage
        path_utilization = self.path_evaluation_cache.size() / self.path_evaluation_cache.maxsize
        if path_utilization > 0.9 and self.path_stats.evictions > 1000:
            recommendations['path_evaluation_cache'] = int(self.path_evaluation_cache.maxsize * 1.5)
        elif path_utilization < 0.3:
            recommendations['path_evaluation_cache'] = int(self.path_evaluation_cache.maxsize * 0.7)
        
        # Analyze template cache usage
        template_utilization = self.template_cache.size() / self.template_cache.maxsize
        if template_utilization > 0.9:
            recommendations['template_cache'] = int(self.template_cache.maxsize * 1.5)
        elif template_utilization < 0.2:
            recommendations['template_cache'] = int(self.template_cache.maxsize * 0.7)
        
        # Analyze directory cache usage
        directory_utilization = self.directory_cache.size() / self.directory_cache.maxsize
        if directory_utilization > 0.9 and self.directory_stats.evictions > 500:
            recommendations['directory_cache'] = int(self.directory_cache.maxsize * 1.5)
        elif directory_utilization < 0.3:
            recommendations['directory_cache'] = int(self.directory_cache.maxsize * 0.7)
        
        if recommendations:
            logger.info(f"Cache size optimization recommendations: {recommendations}")
        
        return recommendations
    
    def _generate_pattern_cache_key(self, patterns: List[PatternRule]) -> str:
        """
        Generate cache key for pattern list.
        
        Args:
            patterns: List of pattern rules
            
        Returns:
            Cache key string
        """
        # Create deterministic key based on pattern content
        pattern_strings = []
        for pattern in sorted(patterns, key=lambda p: (p.pattern, p.syntax.value, p.priority)):
            pattern_strings.append(
                f"{pattern.syntax.value}:{pattern.pattern}:"
                f"{pattern.case_sensitive}:{pattern.applies_to.value}:{pattern.priority}"
            )
        
        key_data = '|'.join(pattern_strings).encode('utf-8')
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def _generate_path_cache_key(self, path: Path, config_hash: str) -> str:
        """
        Generate cache key for path evaluation.
        
        Args:
            path: Path being evaluated
            config_hash: Hash of the selection configuration
            
        Returns:
            Cache key string
        """
        key_data = f"{str(path)}:{config_hash}".encode('utf-8')
        return hashlib.sha256(key_data).hexdigest()[:16]
    
    def _generate_config_hash(self, config: SelectionConfig) -> str:
        """
        Generate hash for selection configuration.
        
        Args:
            config: Selection configuration
            
        Returns:
            Configuration hash string
        """
        # Create deterministic hash based on configuration content
        config_parts = []
        
        # Include paths
        for path in sorted(config.include_paths, key=str):
            config_parts.append(f"include:{path}")
        for path in sorted(config.exclude_paths, key=str):
            config_parts.append(f"exclude:{path}")
        
        # Include patterns
        for pattern in sorted(config.include_patterns, key=lambda p: p.pattern):
            config_parts.append(f"include_pattern:{pattern.pattern}:{pattern.syntax.value}")
        for pattern in sorted(config.exclude_patterns, key=lambda p: p.pattern):
            config_parts.append(f"exclude_pattern:{pattern.pattern}:{pattern.syntax.value}")
        
        # Include precedence config
        config_parts.append(f"precedence:{config.precedence_config.default_strategy.value}")
        
        config_data = '|'.join(config_parts).encode('utf-8')
        return hashlib.sha256(config_data).hexdigest()[:16]


class DirectoryTraversalOptimizer:
    """
    Optimizer for directory traversal operations.
    
    Provides intelligent directory traversal with early termination,
    skip lists, and performance monitoring.
    """
    
    def __init__(self, cache_manager: SelectionCacheManager):
        """
        Initialize directory traversal optimizer.
        
        Args:
            cache_manager: Cache manager for directory caching
        """
        self.cache_manager = cache_manager
        self._skip_directories: Set[Path] = set()
        self._traversal_stats = {
            'directories_visited': 0,
            'directories_skipped': 0,
            'files_found': 0,
            'cache_hits': 0
        }
    
    def add_skip_directory(self, directory: Path) -> None:
        """
        Add directory to skip list.
        
        Args:
            directory: Directory to skip during traversal
        """
        self._skip_directories.add(directory)
        logger.debug(f"Added {directory} to skip list")
    
    def should_skip_directory(self, directory: Path) -> bool:
        """
        Check if directory should be skipped.
        
        Args:
            directory: Directory to check
            
        Returns:
            True if directory should be skipped
        """
        # Check if directory is in skip list
        if directory in self._skip_directories:
            self._traversal_stats['directories_skipped'] += 1
            return True
        
        # Check if any parent directory is in skip list
        for skip_dir in self._skip_directories:
            try:
                if directory.is_relative_to(skip_dir):
                    self._traversal_stats['directories_skipped'] += 1
                    return True
            except (ValueError, AttributeError):
                # is_relative_to not available in older Python versions
                if str(directory).startswith(str(skip_dir)):
                    self._traversal_stats['directories_skipped'] += 1
                    return True
        
        return False
    
    def get_directory_contents(
        self,
        directory: Path,
        use_cache: bool = True
    ) -> List[Path]:
        """
        Get directory contents with caching.
        
        Args:
            directory: Directory to list
            use_cache: Whether to use cache
            
        Returns:
            List of paths in the directory
        """
        # Check cache first
        if use_cache:
            cached_contents = self.cache_manager.get_cached_directory_contents(directory)
            if cached_contents is not None:
                self._traversal_stats['cache_hits'] += 1
                return cached_contents
        
        # List directory
        try:
            contents = list(directory.iterdir())
            self._traversal_stats['directories_visited'] += 1
            self._traversal_stats['files_found'] += len([p for p in contents if p.is_file()])
            
            # Cache results
            if use_cache:
                self.cache_manager.cache_directory_contents(directory, contents)
            
            return contents
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access directory {directory}: {e}")
            return []
    
    def get_traversal_statistics(self) -> Dict[str, Any]:
        """
        Get directory traversal statistics.
        
        Returns:
            Dictionary with traversal statistics
        """
        return self._traversal_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset traversal statistics"""
        self._traversal_stats = {
            'directories_visited': 0,
            'directories_skipped': 0,
            'files_found': 0,
            'cache_hits': 0
        }
