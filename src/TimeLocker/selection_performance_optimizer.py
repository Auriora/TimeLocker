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

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from .pattern_engine import PatternEngine, CompiledPatternSet
from .precedence_resolver import PrecedenceResolver
from .selection_models import (
    PatternRule,
    SelectionConfig,
    SelectionDecision,
    SelectionResult,
    EvaluationStats,
    PerformanceMetrics,
    PerformanceEstimate,
    RuleMatch
)

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Strategy for caching selection evaluations"""
    NONE = "none"
    PATTERN_ONLY = "pattern_only"
    PATH_EVALUATION = "path_evaluation"
    AGGRESSIVE = "aggressive"


@dataclass
class OptimizedSelection:
    """
    Optimized selection configuration.
    
    Attributes:
        original_config: The original selection configuration
        optimized_patterns: Optimized pattern rules
        optimization_applied: List of optimizations that were applied
        estimated_performance_gain: Estimated performance improvement (multiplier)
        cache_strategy: Caching strategy to use
        streaming_recommended: Whether streaming evaluation is recommended
        batch_size: Recommended batch size for processing
        metadata: Additional optimization metadata
    """
    original_config: SelectionConfig
    optimized_patterns: List[PatternRule]
    optimization_applied: List[str] = field(default_factory=list)
    estimated_performance_gain: float = 1.0
    cache_strategy: str = CacheStrategy.PATTERN_ONLY
    streaming_recommended: bool = False
    batch_size: int = 1000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationStatistics:
    """
    Statistics for streaming evaluation.
    
    Attributes:
        paths_processed: Number of paths processed
        paths_included: Number of paths included
        paths_excluded: Number of paths excluded
        start_time: Start time of evaluation
        last_update_time: Last update time
        cancelled: Whether evaluation was cancelled
        errors: List of errors encountered
    """
    paths_processed: int = 0
    paths_included: int = 0
    paths_excluded: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    cancelled: bool = False
    errors: List[str] = field(default_factory=list)
    
    def update_progress(self, count: int) -> None:
        """Update progress statistics"""
        self.paths_processed += count
        self.last_update_time = time.time()
    
    def should_cancel(self) -> bool:
        """Check if evaluation should be cancelled"""
        return self.cancelled
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    def get_processing_rate(self) -> float:
        """Get processing rate in paths per second"""
        elapsed = self.get_elapsed_time()
        return self.paths_processed / elapsed if elapsed > 0 else 0.0


@dataclass
class PerformanceBenchmark:
    """
    Performance benchmark results.
    
    Attributes:
        files_per_second: Processing rate
        memory_usage_mb: Memory usage in MB
        cache_hit_ratio: Cache hit ratio
        optimization_opportunities: List of optimization suggestions
        bottlenecks: Identified bottlenecks
        test_duration_seconds: Duration of benchmark test
        test_file_count: Number of files in benchmark
    """
    files_per_second: float
    memory_usage_mb: float
    cache_hit_ratio: float
    optimization_opportunities: List[str] = field(default_factory=list)
    bottlenecks: List[str] = field(default_factory=list)
    test_duration_seconds: float = 0.0
    test_file_count: int = 0


@dataclass
class OptimizationHint:
    """
    Hint for optimizing selection performance.
    
    Attributes:
        hint_type: Type of optimization hint
        message: Description of the hint
        impact: Expected impact (low, medium, high)
        implementation: How to implement the hint
    """
    hint_type: str
    message: str
    impact: str
    implementation: str


class StreamingEvaluator:
    """
    Memory-efficient streaming evaluator for large file systems.
    
    Processes paths in batches to minimize memory usage while maintaining
    high performance through pattern caching and optimized evaluation.
    """
    
    def __init__(
        self,
        compiled_patterns: CompiledPatternSet,
        precedence_resolver: PrecedenceResolver,
        batch_size: int = 1000
    ):
        """
        Initialize streaming evaluator.
        
        Args:
            compiled_patterns: Compiled pattern set for matching
            precedence_resolver: Resolver for precedence conflicts
            batch_size: Number of paths to process in each batch
        """
        self.compiled_patterns = compiled_patterns
        self.precedence_resolver = precedence_resolver
        self.batch_size = batch_size
        self.statistics = EvaluationStatistics()
        self._path_cache: Dict[str, SelectionDecision] = {}
        self._cache_size_limit = 10000
    
    async def evaluate_path_stream(
        self,
        path_stream: AsyncIterator[Path]
    ) -> AsyncIterator[SelectionResult]:
        """
        Evaluate paths from an async stream.
        
        Args:
            path_stream: Async iterator of paths to evaluate
            
        Yields:
            SelectionResult for each evaluated path
        """
        batch = []
        
        async for path in path_stream:
            if self.statistics.should_cancel():
                logger.info("Streaming evaluation cancelled")
                break
            
            batch.append(path)
            
            if len(batch) >= self.batch_size:
                # Process batch
                async for result in self._evaluate_batch(batch):
                    yield result
                
                # Update statistics
                self.statistics.update_progress(len(batch))
                batch.clear()
                
                # Log progress
                if self.statistics.paths_processed % 10000 == 0:
                    rate = self.statistics.get_processing_rate()
                    logger.info(
                        f"Processed {self.statistics.paths_processed} paths "
                        f"({rate:.0f} paths/sec)"
                    )
        
        # Process remaining paths
        if batch:
            async for result in self._evaluate_batch(batch):
                yield result
            self.statistics.update_progress(len(batch))
    
    async def _evaluate_batch(self, paths: List[Path]) -> AsyncIterator[SelectionResult]:
        """
        Evaluate a batch of paths.
        
        Args:
            paths: List of paths to evaluate
            
        Yields:
            SelectionResult for each path
        """
        for path in paths:
            try:
                # Check cache first
                path_str = str(path)
                if path_str in self._path_cache:
                    decision = self._path_cache[path_str]
                else:
                    # Evaluate path
                    decision = await self._evaluate_single_path(path)
                    
                    # Cache result (with size limit)
                    if len(self._path_cache) < self._cache_size_limit:
                        self._path_cache[path_str] = decision
                
                # Update statistics
                if decision.include:
                    self.statistics.paths_included += 1
                else:
                    self.statistics.paths_excluded += 1
                
                # Create result
                result = SelectionResult(
                    included_paths=[path] if decision.include else [],
                    excluded_paths=[path] if not decision.include else [],
                    warnings=decision.warnings
                )
                
                yield result
                
            except Exception as e:
                logger.error(f"Error evaluating path {path}: {e}")
                self.statistics.errors.append(str(e))
    
    async def _evaluate_single_path(self, path: Path) -> SelectionDecision:
        """
        Evaluate a single path against patterns.
        
        Args:
            path: Path to evaluate
            
        Returns:
            SelectionDecision for the path
        """
        # This is a simplified implementation
        # In a real implementation, this would use the pattern engine
        # and precedence resolver to make the decision
        
        # For now, return a default decision
        return SelectionDecision(
            include=True,
            confidence=1.0,
            applied_rules=[],
            precedence_explanation="Default inclusion"
        )
    
    def get_evaluation_statistics(self) -> EvaluationStatistics:
        """
        Get current evaluation statistics.
        
        Returns:
            EvaluationStatistics object
        """
        return self.statistics
    
    async def cancel_evaluation(self) -> bool:
        """
        Cancel the ongoing evaluation.
        
        Returns:
            True if cancellation was successful
        """
        self.statistics.cancelled = True
        logger.info("Evaluation cancellation requested")
        return True
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'cache_size': len(self._path_cache),
            'cache_limit': self._cache_size_limit,
            'cache_utilization': len(self._path_cache) / self._cache_size_limit
        }


class SelectionPerformanceOptimizer:
    """
    Performance optimization system for selection operations.
    
    Provides streaming evaluation, memory-efficient batch processing,
    performance benchmarking, and optimization recommendations for
    large file system operations.
    """
    
    # Performance thresholds
    LARGE_DATASET_THRESHOLD = 10000
    VERY_LARGE_DATASET_THRESHOLD = 100000
    MEMORY_LIMIT_MB = 512
    
    def __init__(self, pattern_engine: PatternEngine):
        """
        Initialize performance optimizer.
        
        Args:
            pattern_engine: PatternEngine instance for pattern operations
        """
        self.pattern_engine = pattern_engine
        self._benchmark_cache: Dict[str, PerformanceBenchmark] = {}
        self._optimization_stats = {
            'total_optimizations': 0,
            'streaming_recommendations': 0,
            'cache_optimizations': 0
        }
    
    async def optimize_selection_for_size(
        self,
        selection_config: SelectionConfig,
        estimated_file_count: int
    ) -> OptimizedSelection:
        """
        Optimize selection configuration based on estimated dataset size.
        
        Args:
            selection_config: Original selection configuration
            estimated_file_count: Estimated number of files to process
            
        Returns:
            OptimizedSelection with optimizations applied
        """
        start_time = time.time()
        optimizations_applied = []
        
        # Combine all patterns
        all_patterns = (
            selection_config.include_patterns +
            selection_config.exclude_patterns
        )
        
        # Optimize pattern order
        optimized_patterns = self.pattern_engine.optimize_pattern_order(all_patterns)
        optimizations_applied.append("pattern_order_optimization")
        
        # Determine cache strategy
        if estimated_file_count < self.LARGE_DATASET_THRESHOLD:
            cache_strategy = CacheStrategy.AGGRESSIVE
            optimizations_applied.append("aggressive_caching")
        elif estimated_file_count < self.VERY_LARGE_DATASET_THRESHOLD:
            cache_strategy = CacheStrategy.PATH_EVALUATION
            optimizations_applied.append("path_evaluation_caching")
        else:
            cache_strategy = CacheStrategy.PATTERN_ONLY
            optimizations_applied.append("pattern_only_caching")
        
        # Determine if streaming is recommended
        streaming_recommended = estimated_file_count >= self.VERY_LARGE_DATASET_THRESHOLD
        if streaming_recommended:
            optimizations_applied.append("streaming_evaluation")
        
        # Calculate batch size
        if estimated_file_count < self.LARGE_DATASET_THRESHOLD:
            batch_size = 500
        elif estimated_file_count < self.VERY_LARGE_DATASET_THRESHOLD:
            batch_size = 1000
        else:
            batch_size = 2000
        
        optimizations_applied.append(f"batch_size_{batch_size}")
        
        # Estimate performance gain
        base_gain = 1.0
        if "pattern_order_optimization" in optimizations_applied:
            base_gain *= 1.2
        if streaming_recommended:
            base_gain *= 1.5
        if cache_strategy == CacheStrategy.AGGRESSIVE:
            base_gain *= 1.3
        
        optimization_time = time.time() - start_time
        
        # Update statistics
        self._optimization_stats['total_optimizations'] += 1
        if streaming_recommended:
            self._optimization_stats['streaming_recommendations'] += 1
        if cache_strategy != CacheStrategy.NONE:
            self._optimization_stats['cache_optimizations'] += 1
        
        logger.info(
            f"Optimized selection for {estimated_file_count} files in "
            f"{optimization_time*1000:.2f}ms (estimated gain: {base_gain:.1f}x)"
        )
        
        return OptimizedSelection(
            original_config=selection_config,
            optimized_patterns=optimized_patterns,
            optimization_applied=optimizations_applied,
            estimated_performance_gain=base_gain,
            cache_strategy=cache_strategy,
            streaming_recommended=streaming_recommended,
            batch_size=batch_size,
            metadata={
                'estimated_file_count': estimated_file_count,
                'optimization_time_ms': optimization_time * 1000
            }
        )
    
    def create_streaming_evaluator(
        self,
        selection_config: SelectionConfig,
        batch_size: Optional[int] = None
    ) -> StreamingEvaluator:
        """
        Create a streaming evaluator for memory-efficient processing.
        
        Args:
            selection_config: Selection configuration
            batch_size: Optional batch size (uses default if not specified)
            
        Returns:
            StreamingEvaluator instance
        """
        # Compile patterns
        all_patterns = (
            selection_config.include_patterns +
            selection_config.exclude_patterns
        )
        compiled_patterns = self.pattern_engine.compile_patterns(all_patterns)
        
        # Create precedence resolver
        from .precedence_resolver import PrecedenceResolver
        precedence_resolver = PrecedenceResolver(selection_config.precedence_config)
        
        # Determine batch size
        if batch_size is None:
            batch_size = 1000
        
        logger.info(f"Created streaming evaluator with batch size {batch_size}")
        
        return StreamingEvaluator(
            compiled_patterns=compiled_patterns,
            precedence_resolver=precedence_resolver,
            batch_size=batch_size
        )
    
    async def benchmark_selection_performance(
        self,
        selection_config: SelectionConfig,
        test_paths: List[Path]
    ) -> PerformanceBenchmark:
        """
        Benchmark selection performance with test paths.
        
        Args:
            selection_config: Selection configuration to benchmark
            test_paths: List of test paths to use
            
        Returns:
            PerformanceBenchmark with results
        """
        start_time = time.time()
        
        # Compile patterns
        all_patterns = (
            selection_config.include_patterns +
            selection_config.exclude_patterns
        )
        compiled_patterns = self.pattern_engine.compile_patterns(all_patterns)
        
        # Evaluate test paths
        match_results = self.pattern_engine.batch_match_paths(test_paths, compiled_patterns)
        
        # Calculate metrics
        duration = time.time() - start_time
        files_per_second = len(test_paths) / duration if duration > 0 else 0
        
        # Get cache statistics
        cache_stats = self.pattern_engine.get_cache_statistics()
        cache_hit_ratio = cache_stats.get('hit_ratio', 0.0)
        
        # Estimate memory usage (simplified)
        memory_usage_mb = len(test_paths) * 0.001  # Rough estimate
        
        # Identify optimization opportunities
        opportunities = []
        bottlenecks = []
        
        if files_per_second < 1000:
            bottlenecks.append("low_processing_rate")
            opportunities.append("Consider optimizing pattern complexity")
        
        if cache_hit_ratio < 0.5:
            bottlenecks.append("low_cache_hit_ratio")
            opportunities.append("Increase cache size or improve pattern reuse")
        
        if memory_usage_mb > self.MEMORY_LIMIT_MB:
            bottlenecks.append("high_memory_usage")
            opportunities.append("Use streaming evaluation for large datasets")
        
        # Check pattern complexity
        pattern_stats = self.pattern_engine.get_pattern_statistics(compiled_patterns)
        if pattern_stats.average_complexity > 50:
            bottlenecks.append("high_pattern_complexity")
            opportunities.append("Simplify patterns or use more literal patterns")
        
        logger.info(
            f"Benchmark completed: {files_per_second:.0f} files/sec, "
            f"{memory_usage_mb:.1f}MB memory, {cache_hit_ratio:.2%} cache hit ratio"
        )
        
        return PerformanceBenchmark(
            files_per_second=files_per_second,
            memory_usage_mb=memory_usage_mb,
            cache_hit_ratio=cache_hit_ratio,
            optimization_opportunities=opportunities,
            bottlenecks=bottlenecks,
            test_duration_seconds=duration,
            test_file_count=len(test_paths)
        )
    
    def get_optimization_recommendations(
        self,
        selection_config: SelectionConfig,
        estimated_file_count: Optional[int] = None
    ) -> List[OptimizationHint]:
        """
        Get optimization recommendations for a selection configuration.
        
        Args:
            selection_config: Selection configuration to analyze
            estimated_file_count: Optional estimated file count
            
        Returns:
            List of OptimizationHint objects
        """
        hints = []
        
        # Analyze pattern count
        total_patterns = (
            len(selection_config.include_patterns) +
            len(selection_config.exclude_patterns)
        )
        
        if total_patterns > 50:
            hints.append(OptimizationHint(
                hint_type="pattern_count",
                message=f"Large number of patterns ({total_patterns}) may impact performance",
                impact="medium",
                implementation="Consider using pattern groups to organize related patterns"
            ))
        
        # Analyze pattern complexity
        all_patterns = (
            selection_config.include_patterns +
            selection_config.exclude_patterns
        )
        
        if all_patterns:
            compiled_patterns = self.pattern_engine.compile_patterns(all_patterns)
            pattern_stats = self.pattern_engine.get_pattern_statistics(compiled_patterns)
            
            if pattern_stats.average_complexity > 50:
                hints.append(OptimizationHint(
                    hint_type="pattern_complexity",
                    message=f"High average pattern complexity ({pattern_stats.average_complexity:.1f})",
                    impact="high",
                    implementation="Simplify complex patterns or use GLOB instead of REGEX where possible"
                ))
            
            if pattern_stats.regex_patterns > pattern_stats.glob_patterns:
                hints.append(OptimizationHint(
                    hint_type="pattern_syntax",
                    message="More REGEX patterns than GLOB patterns",
                    impact="medium",
                    implementation="GLOB patterns are faster - use them when possible"
                ))
        
        # Analyze dataset size
        if estimated_file_count:
            if estimated_file_count >= self.VERY_LARGE_DATASET_THRESHOLD:
                hints.append(OptimizationHint(
                    hint_type="dataset_size",
                    message=f"Very large dataset ({estimated_file_count} files)",
                    impact="high",
                    implementation="Use streaming evaluation to minimize memory usage"
                ))
            elif estimated_file_count >= self.LARGE_DATASET_THRESHOLD:
                hints.append(OptimizationHint(
                    hint_type="dataset_size",
                    message=f"Large dataset ({estimated_file_count} files)",
                    impact="medium",
                    implementation="Consider batch processing with optimized cache strategy"
                ))
        
        # Analyze path configuration
        if len(selection_config.include_paths) == 0:
            hints.append(OptimizationHint(
                hint_type="path_configuration",
                message="No explicit include paths specified",
                impact="low",
                implementation="Specify base paths to limit traversal scope"
            ))
        
        return hints
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """
        Get optimization statistics.
        
        Returns:
            Dictionary with optimization statistics
        """
        return self._optimization_stats.copy()
