#!/usr/bin/env python3
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
Demo script for Selection Performance Optimization features.

This script demonstrates:
1. SelectionPerformanceOptimizer for dataset size optimization
2. StreamingEvaluator for memory-efficient processing
3. Performance benchmarking
4. Optimization recommendations
5. SelectionCacheManager for intelligent caching
6. DirectoryTraversalOptimizer for efficient traversal
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.pattern_engine import PatternEngine
from TimeLocker.selection_models import (
    PatternRule,
    PatternSyntax,
    PathComponent,
    SelectionConfig,
    PrecedenceConfig
)
from TimeLocker.selection_performance_optimizer import (
    SelectionPerformanceOptimizer,
    StreamingEvaluator
)
from TimeLocker.selection_cache_manager import (
    SelectionCacheManager,
    DirectoryTraversalOptimizer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_performance_optimizer():
    """Demonstrate SelectionPerformanceOptimizer"""
    print("\n" + "="*80)
    print("DEMO: Selection Performance Optimizer")
    print("="*80)
    
    # Create pattern engine and optimizer
    pattern_engine = PatternEngine()
    optimizer = SelectionPerformanceOptimizer(pattern_engine)
    
    # Create a selection configuration
    config = SelectionConfig(
        include_paths=[Path("/home/user")],
        exclude_paths=[Path("/home/user/.cache")],
        include_patterns=[
            PatternRule("*.py", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[
            PatternRule("*.pyc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 200),
            PatternRule("__pycache__/*", PatternSyntax.GLOB, True, PathComponent.FULL_PATH, 200),
            PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 150),
        ]
    )
    
    # Test optimization for different dataset sizes
    dataset_sizes = [1000, 10000, 100000, 1000000]
    
    for size in dataset_sizes:
        print(f"\n--- Optimizing for {size:,} files ---")
        
        # Run optimization
        optimized = asyncio.run(
            optimizer.optimize_selection_for_size(config, size)
        )
        
        print(f"Optimizations applied: {', '.join(optimized.optimization_applied)}")
        print(f"Estimated performance gain: {optimized.estimated_performance_gain:.1f}x")
        print(f"Cache strategy: {optimized.cache_strategy}")
        print(f"Streaming recommended: {optimized.streaming_recommended}")
        print(f"Batch size: {optimized.batch_size}")
    
    # Get optimization recommendations
    print("\n--- Optimization Recommendations ---")
    hints = optimizer.get_optimization_recommendations(config, estimated_file_count=50000)
    
    for hint in hints:
        print(f"\n{hint.hint_type.upper()} (Impact: {hint.impact})")
        print(f"  Message: {hint.message}")
        print(f"  Implementation: {hint.implementation}")
    
    # Get optimizer statistics
    print("\n--- Optimizer Statistics ---")
    stats = optimizer.get_optimization_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


async def demo_streaming_evaluator():
    """Demonstrate StreamingEvaluator"""
    print("\n" + "="*80)
    print("DEMO: Streaming Evaluator")
    print("="*80)
    
    # Create pattern engine and compile patterns
    pattern_engine = PatternEngine()
    
    patterns = [
        PatternRule("*.py", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
    ]
    
    compiled_patterns = pattern_engine.compile_patterns(patterns)
    
    # Create precedence resolver
    from TimeLocker.precedence_resolver import PrecedenceResolver
    precedence_config = PrecedenceConfig()
    precedence_resolver = PrecedenceResolver(precedence_config)
    
    # Create streaming evaluator
    evaluator = StreamingEvaluator(
        compiled_patterns=compiled_patterns,
        precedence_resolver=precedence_resolver,
        batch_size=100
    )
    
    # Create async path stream
    async def path_generator() -> AsyncIterator[Path]:
        """Generate test paths"""
        test_paths = [
            Path("/home/user/file1.py"),
            Path("/home/user/file2.txt"),
            Path("/home/user/file3.log"),
            Path("/home/user/docs/readme.md"),
            Path("/home/user/src/main.py"),
        ] * 20  # Repeat to simulate larger dataset
        
        for path in test_paths:
            yield path
            await asyncio.sleep(0.001)  # Simulate I/O delay
    
    # Evaluate paths
    print("\n--- Streaming Evaluation ---")
    result_count = 0
    included_count = 0
    excluded_count = 0
    
    async for result in evaluator.evaluate_path_stream(path_generator()):
        result_count += 1
        included_count += len(result.included_paths)
        excluded_count += len(result.excluded_paths)
    
    print(f"Total results: {result_count}")
    print(f"Included paths: {included_count}")
    print(f"Excluded paths: {excluded_count}")
    
    # Get evaluation statistics
    print("\n--- Evaluation Statistics ---")
    stats = evaluator.get_evaluation_statistics()
    print(f"Paths processed: {stats.paths_processed}")
    print(f"Paths included: {stats.paths_included}")
    print(f"Paths excluded: {stats.paths_excluded}")
    print(f"Processing rate: {stats.get_processing_rate():.0f} paths/sec")
    print(f"Elapsed time: {stats.get_elapsed_time():.2f} seconds")
    
    # Get cache statistics
    print("\n--- Cache Statistics ---")
    cache_stats = evaluator.get_cache_statistics()
    for key, value in cache_stats.items():
        print(f"  {key}: {value}")


async def demo_performance_benchmark():
    """Demonstrate performance benchmarking"""
    print("\n" + "="*80)
    print("DEMO: Performance Benchmarking")
    print("="*80)
    
    # Create pattern engine and optimizer
    pattern_engine = PatternEngine()
    optimizer = SelectionPerformanceOptimizer(pattern_engine)
    
    # Create test configuration
    config = SelectionConfig(
        include_patterns=[
            PatternRule("*.py", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
            PatternRule("*.md", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        ],
        exclude_patterns=[
            PatternRule("*.pyc", PatternSyntax.GLOB, False, PathComponent.FILENAME, 200),
            PatternRule("*.log", PatternSyntax.GLOB, False, PathComponent.FILENAME, 150),
        ]
    )
    
    # Generate test paths
    test_paths = []
    extensions = ['.py', '.txt', '.md', '.pyc', '.log', '.json', '.yaml']
    for i in range(1000):
        ext = extensions[i % len(extensions)]
        test_paths.append(Path(f"/test/file{i}{ext}"))
    
    # Run benchmark
    print("\n--- Running Benchmark ---")
    benchmark = await optimizer.benchmark_selection_performance(config, test_paths)
    
    print(f"Files per second: {benchmark.files_per_second:.0f}")
    print(f"Memory usage: {benchmark.memory_usage_mb:.2f} MB")
    print(f"Cache hit ratio: {benchmark.cache_hit_ratio:.2%}")
    print(f"Test duration: {benchmark.test_duration_seconds:.3f} seconds")
    print(f"Test file count: {benchmark.test_file_count}")
    
    if benchmark.bottlenecks:
        print("\n--- Identified Bottlenecks ---")
        for bottleneck in benchmark.bottlenecks:
            print(f"  - {bottleneck}")
    
    if benchmark.optimization_opportunities:
        print("\n--- Optimization Opportunities ---")
        for opportunity in benchmark.optimization_opportunities:
            print(f"  - {opportunity}")


def demo_cache_manager():
    """Demonstrate SelectionCacheManager"""
    print("\n" + "="*80)
    print("DEMO: Selection Cache Manager")
    print("="*80)
    
    # Create cache manager
    cache_manager = SelectionCacheManager(
        pattern_cache_size=100,
        path_cache_size=1000,
        template_cache_size=50,
        directory_cache_size=500
    )
    
    # Create test patterns
    patterns = [
        PatternRule("*.py", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
        PatternRule("*.txt", PatternSyntax.GLOB, False, PathComponent.FILENAME, 100),
    ]
    
    # Test pattern caching
    print("\n--- Pattern Caching ---")
    
    # First access (cache miss)
    result1 = cache_manager.get_cached_pattern_compilation(patterns)
    print(f"First access: {'HIT' if result1 else 'MISS'}")
    
    # Cache the patterns
    from TimeLocker.pattern_engine import PatternEngine
    pattern_engine = PatternEngine()
    compiled = pattern_engine.compile_patterns(patterns)
    cache_manager.cache_pattern_compilation(patterns, compiled)
    
    # Second access (cache hit)
    result2 = cache_manager.get_cached_pattern_compilation(patterns)
    print(f"Second access: {'HIT' if result2 else 'MISS'}")
    
    # Test directory caching
    print("\n--- Directory Caching ---")
    
    test_dir = Path("/test/directory")
    test_contents = [Path("/test/directory/file1.txt"), Path("/test/directory/file2.py")]
    
    # Cache directory contents
    cache_manager.cache_directory_contents(test_dir, test_contents)
    
    # Retrieve from cache
    cached_contents = cache_manager.get_cached_directory_contents(test_dir)
    print(f"Cached contents retrieved: {cached_contents is not None}")
    if cached_contents:
        print(f"  Contents: {[p.name for p in cached_contents]}")
    
    # Get cache statistics
    print("\n--- Cache Statistics ---")
    stats = cache_manager.get_cache_statistics()
    
    print(f"\nPattern Cache:")
    print(f"  Size: {stats['pattern_cache']['size']}/{stats['pattern_cache']['maxsize']}")
    print(f"  Utilization: {stats['pattern_cache']['utilization']:.1%}")
    print(f"  Hit ratio: {stats['pattern_cache']['statistics']['hit_ratio']:.1%}")
    
    print(f"\nPath Evaluation Cache:")
    print(f"  Size: {stats['path_evaluation_cache']['size']}/{stats['path_evaluation_cache']['maxsize']}")
    print(f"  Utilization: {stats['path_evaluation_cache']['utilization']:.1%}")
    
    print(f"\nDirectory Cache:")
    print(f"  Size: {stats['directory_cache']['size']}/{stats['directory_cache']['maxsize']}")
    print(f"  Utilization: {stats['directory_cache']['utilization']:.1%}")
    print(f"  Hit ratio: {stats['directory_cache']['statistics']['hit_ratio']:.1%}")
    
    print(f"\nOverall:")
    print(f"  Total cache size: {stats['overall']['total_cache_size']}")
    print(f"  Total evictions: {stats['overall']['total_evictions']}")
    
    # Test cache optimization
    print("\n--- Cache Size Optimization ---")
    recommendations = cache_manager.optimize_cache_sizes(stats)
    if recommendations:
        print("Recommendations:")
        for cache_name, recommended_size in recommendations.items():
            print(f"  {cache_name}: {recommended_size}")
    else:
        print("No optimization recommendations at this time")


def demo_directory_traversal_optimizer():
    """Demonstrate DirectoryTraversalOptimizer"""
    print("\n" + "="*80)
    print("DEMO: Directory Traversal Optimizer")
    print("="*80)
    
    # Create cache manager and traversal optimizer
    cache_manager = SelectionCacheManager()
    traversal_optimizer = DirectoryTraversalOptimizer(cache_manager)
    
    # Add directories to skip
    print("\n--- Adding Skip Directories ---")
    skip_dirs = [
        Path("/home/user/.cache"),
        Path("/home/user/node_modules"),
        Path("/home/user/.git"),
    ]
    
    for skip_dir in skip_dirs:
        traversal_optimizer.add_skip_directory(skip_dir)
        print(f"Added to skip list: {skip_dir}")
    
    # Test skip detection
    print("\n--- Testing Skip Detection ---")
    test_dirs = [
        Path("/home/user/documents"),
        Path("/home/user/.cache/temp"),
        Path("/home/user/node_modules/package"),
        Path("/home/user/projects"),
    ]
    
    for test_dir in test_dirs:
        should_skip = traversal_optimizer.should_skip_directory(test_dir)
        print(f"{test_dir}: {'SKIP' if should_skip else 'PROCESS'}")
    
    # Get traversal statistics
    print("\n--- Traversal Statistics ---")
    stats = traversal_optimizer.get_traversal_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("SELECTION PERFORMANCE OPTIMIZATION DEMO")
    print("="*80)
    
    # Run demos
    demo_performance_optimizer()
    asyncio.run(demo_streaming_evaluator())
    asyncio.run(demo_performance_benchmark())
    demo_cache_manager()
    demo_directory_traversal_optimizer()
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
