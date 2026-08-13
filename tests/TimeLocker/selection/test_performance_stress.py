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

import pytest
import asyncio
import tempfile
import time
import psutil
import os
from pathlib import Path
from typing import AsyncIterator, List

from TimeLocker.selection_manager import SelectionManager
from TimeLocker.selection_template_manager import SelectionTemplateManager
from TimeLocker.pattern_engine import PatternEngine
from TimeLocker.selection_validation_service import SelectionValidationService
from TimeLocker.selection_performance_optimizer import SelectionPerformanceOptimizer
from TimeLocker.selection_testing_harness import PerformanceBaseline
from TimeLocker.selection_models import (
    SelectionConfig,
    PatternRule,
    PatternSyntax,
    PathComponent,
    PrecedenceConfig
)


class TestPerformanceBaselineContract:
    """Deterministic tests for the shared timing-threshold contract."""

    def test_accepts_observations_at_or_below_tolerance(self):
        baseline = PerformanceBaseline("selection", 1.0, 2.0)

        assert baseline.accepts(0.5)
        assert baseline.accepts(2.0)
        assert not baseline.accepts(2.01)

    @pytest.mark.parametrize(
        ("seconds_per_operation", "tolerance_multiplier"),
        [(0.0, 2.0), (float("inf"), 2.0), (1.0, 0.99), (1.0, float("nan"))],
    )
    def test_rejects_invalid_thresholds(
        self,
        seconds_per_operation,
        tolerance_multiplier,
    ):
        with pytest.raises(ValueError):
            PerformanceBaseline(
                "selection",
                seconds_per_operation,
                tolerance_multiplier,
            )


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for template storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def selection_manager(temp_storage_dir):
    """Create a SelectionManager instance for testing."""
    template_manager = SelectionTemplateManager(storage_dir=temp_storage_dir)
    pattern_engine = PatternEngine()
    validation_service = SelectionValidationService(pattern_engine=pattern_engine)
    performance_optimizer = SelectionPerformanceOptimizer(pattern_engine=pattern_engine)
    
    return SelectionManager(
        template_manager=template_manager,
        pattern_engine=pattern_engine,
        validation_service=validation_service,
        performance_optimizer=performance_optimizer
    )


def create_large_file_structure(base_dir: Path, file_count: int) -> List[Path]:
    """
    Create a large file structure for testing.
    
    Args:
        base_dir: Base directory to create files in
        file_count: Number of files to create
        
    Returns:
        List of created file paths
    """
    created_files = []
    
    # Create directory structure
    dirs_per_level = max(10, int((file_count / 100) ** 0.5))
    files_per_dir = max(1, file_count // dirs_per_level)
    
    for i in range(dirs_per_level):
        dir_path = base_dir / f"dir_{i}"
        dir_path.mkdir(exist_ok=True)
        
        for j in range(files_per_dir):
            if len(created_files) >= file_count:
                return created_files
                
            # Create files with various extensions
            extensions = ['.txt', '.py', '.md', '.log', '.tmp', '.json']
            ext = extensions[j % len(extensions)]
            file_path = dir_path / f"file_{j}{ext}"
            file_path.write_text(f"content_{i}_{j}")
            created_files.append(file_path)
    
    return created_files


async def generate_path_stream(paths: List[Path]) -> AsyncIterator[Path]:
    """
    Generate an async stream of paths.
    
    Args:
        paths: List of paths to stream
        
    Yields:
        Path objects
    """
    for path in paths:
        yield path
        await asyncio.sleep(0)  # Allow other tasks to run


class TestLargeFileSystemEvaluation:
    """Performance tests for large file system evaluation."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_evaluate_10k_files(self, selection_manager):
        """Test evaluation of 10,000 files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Create 10k files
            file_count = 10000
            files = create_large_file_structure(test_dir, file_count)
            
            # Create selection
            config = SelectionConfig(
                include_paths=[test_dir],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
                    PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB)
                ],
                exclude_patterns=[
                    PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB),
                    PatternRule(pattern="*.log", syntax=PatternSyntax.GLOB)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            )
            
            selection = await selection_manager.create_selection(config)
            
            # Measure evaluation time
            start_time = time.time()
            result = await selection_manager.evaluate_selection(selection, [test_dir])
            duration = time.time() - start_time
            
            # Verify performance
            assert result.evaluation_stats.files_evaluated >= file_count * 0.9
            assert result.performance_metrics.files_per_second >= 1000
            assert duration < 30  # Should complete in under 30 seconds
            
            # Verify results
            assert len(result.included_paths) > 0
            assert len(result.excluded_paths) > 0
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_evaluate_100k_files(self, selection_manager):
        """Test evaluation of 100,000 files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Create 100k files
            file_count = 100000
            files = create_large_file_structure(test_dir, file_count)
            
            # Create selection with optimization
            config = SelectionConfig(
                include_paths=[test_dir],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
                ],
                exclude_patterns=[
                    PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB)
                ],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            )
            
            selection = await selection_manager.create_selection(config)
            
            # Optimize for large dataset
            optimized = await selection_manager.optimize_selection_for_performance(
                selection,
                estimated_file_count=file_count
            )
            
            # Verify optimization was applied
            assert optimized.streaming_recommended
            assert len(optimized.optimization_applied) > 0
            
            # Measure evaluation time
            start_time = time.time()
            result = await selection_manager.evaluate_selection(selection, [test_dir])
            duration = time.time() - start_time
            
            # Verify performance (more lenient for 100k files)
            assert result.evaluation_stats.files_evaluated >= file_count * 0.8
            assert result.performance_metrics.files_per_second >= 500
            assert duration < 300  # Should complete in under 5 minutes
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_pattern_matching_performance_10k_paths(self, selection_manager):
        """Test pattern matching performance with 10,000 paths."""
        # Generate test paths
        test_paths = []
        for i in range(10000):
            extensions = ['.txt', '.py', '.md', '.log', '.tmp', '.json', '.xml', '.yaml']
            ext = extensions[i % len(extensions)]
            test_paths.append(Path(f"/test/dir_{i % 100}/file_{i}{ext}"))
        
        # Create patterns
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.md", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="test_.*\\.py", syntax=PatternSyntax.REGEX),
            PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.log", syntax=PatternSyntax.GLOB)
        ]
        
        # Compile patterns
        compiled_patterns = selection_manager.pattern_engine.compile_patterns(patterns)
        
        # Measure matching performance
        start_time = time.time()
        results = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns
        )
        duration = time.time() - start_time
        
        # Verify performance
        assert len(results) == len(test_paths)
        paths_per_second = len(test_paths) / duration
        assert paths_per_second >= 10000  # Should process at least 10k paths/sec
        assert duration < 2  # Should complete in under 2 seconds


class TestMemoryUsageAndStreaming:
    """Tests for memory usage and streaming evaluation."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_streaming_evaluation_memory_efficiency(self, selection_manager):
        """Test that streaming evaluation maintains low memory usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Create moderate file structure
            file_count = 5000
            files = create_large_file_structure(test_dir, file_count)
            
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Create selection
            config = SelectionConfig(
                include_paths=[test_dir],
                exclude_paths=[],
                include_patterns=[
                    PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
                ],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            )
            
            # Create streaming evaluator
            streaming_evaluator = selection_manager.performance_optimizer.create_streaming_evaluator(
                config,
                batch_size=500
            )
            
            # Evaluate using streaming
            path_stream = generate_path_stream(files)
            results_count = 0
            
            async for result in streaming_evaluator.evaluate_path_stream(path_stream):
                results_count += 1
            
            # Get final memory usage
            final_memory_mb = process.memory_info().rss / 1024 / 1024
            memory_increase_mb = final_memory_mb - initial_memory_mb
            
            # Verify memory efficiency
            assert memory_increase_mb < 100  # Should use less than 100MB additional memory
            assert results_count > 0
            
            # Verify statistics
            stats = streaming_evaluator.get_evaluation_statistics()
            assert stats.paths_processed >= file_count * 0.9
            assert stats.get_processing_rate() > 0
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_streaming_evaluation_cancellation(self, selection_manager):
        """Test that streaming evaluation can be cancelled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Create file structure
            file_count = 1000
            files = create_large_file_structure(test_dir, file_count)
            
            # Create selection
            config = SelectionConfig(
                include_paths=[test_dir],
                exclude_paths=[],
                include_patterns=[],
                exclude_patterns=[],
                pattern_groups=[],
                precedence_config=PrecedenceConfig(),
                case_sensitive=False
            )
            
            # Create streaming evaluator
            streaming_evaluator = selection_manager.performance_optimizer.create_streaming_evaluator(
                config,
                batch_size=100
            )
            
            # Start evaluation and cancel after processing some paths
            path_stream = generate_path_stream(files)
            results_count = 0
            
            async for result in streaming_evaluator.evaluate_path_stream(path_stream):
                results_count += 1
                if results_count >= 500:
                    await streaming_evaluator.cancel_evaluation()
            
            # Verify cancellation worked
            stats = streaming_evaluator.get_evaluation_statistics()
            assert stats.cancelled
            assert stats.paths_processed < file_count
            assert results_count >= 500
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_processing_memory_usage(self, selection_manager):
        """Test memory usage with different batch sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            
            # Create file structure
            file_count = 2000
            files = create_large_file_structure(test_dir, file_count)
            
            # Test different batch sizes
            batch_sizes = [100, 500, 1000, 2000]
            memory_usage = {}
            
            for batch_size in batch_sizes:
                # Get initial memory
                process = psutil.Process(os.getpid())
                initial_memory_mb = process.memory_info().rss / 1024 / 1024
                
                # Create selection
                config = SelectionConfig(
                    include_paths=[test_dir],
                    exclude_paths=[],
                    include_patterns=[
                        PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
                    ],
                    exclude_patterns=[],
                    pattern_groups=[],
                    precedence_config=PrecedenceConfig(),
                    case_sensitive=False
                )
                
                # Create streaming evaluator with specific batch size
                streaming_evaluator = selection_manager.performance_optimizer.create_streaming_evaluator(
                    config,
                    batch_size=batch_size
                )
                
                # Evaluate
                path_stream = generate_path_stream(files)
                async for result in streaming_evaluator.evaluate_path_stream(path_stream):
                    pass
                
                # Get final memory
                final_memory_mb = process.memory_info().rss / 1024 / 1024
                memory_usage[batch_size] = final_memory_mb - initial_memory_mb
            
            # Verify memory usage is reasonable for all batch sizes
            for batch_size, memory_mb in memory_usage.items():
                assert memory_mb < 50  # Should use less than 50MB per batch size test


class TestPatternMatchingPerformance:
    """Performance benchmarks for pattern matching."""
    
    @pytest.mark.performance
    def test_glob_pattern_performance(self, selection_manager):
        """Benchmark GLOB pattern matching performance."""
        # Generate test paths
        test_paths = [Path(f"/test/file_{i}.txt") for i in range(10000)]
        
        # Create GLOB patterns
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="file_*.txt", syntax=PatternSyntax.GLOB)
        ]
        
        # Compile patterns
        compiled_patterns = selection_manager.pattern_engine.compile_patterns(patterns)
        
        # Measure performance
        start_time = time.time()
        results = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns
        )
        duration = time.time() - start_time
        
        # Verify performance
        paths_per_second = len(test_paths) / duration
        assert paths_per_second >= 10000  # Should process at least 10k paths/sec
        assert all(r.matched for r in results)  # All should match *.txt
    
    @pytest.mark.performance
    def test_regex_pattern_performance(self, selection_manager):
        """Benchmark REGEX pattern matching performance."""
        # Generate test paths
        test_paths = [Path(f"/test/test_file_{i}.py") for i in range(10000)]
        
        # Create REGEX patterns
        patterns = [
            PatternRule(pattern="test_.*\\.py", syntax=PatternSyntax.REGEX),
            PatternRule(pattern=".*_file_\\d+\\.py", syntax=PatternSyntax.REGEX)
        ]
        
        # Compile patterns
        compiled_patterns = selection_manager.pattern_engine.compile_patterns(patterns)
        
        # Measure performance
        start_time = time.time()
        results = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns
        )
        duration = time.time() - start_time
        
        # Verify performance (REGEX is slower than GLOB)
        paths_per_second = len(test_paths) / duration
        assert paths_per_second >= 5000  # Should process at least 5k paths/sec
        assert all(r.matched for r in results)
    
    @pytest.mark.performance
    def test_literal_pattern_performance(self, selection_manager):
        """Benchmark LITERAL pattern matching performance."""
        # Generate test paths
        test_paths = [Path(f"/test/README.md") for _ in range(10000)]
        
        # Create LITERAL pattern
        patterns = [
            PatternRule(pattern="README.md", syntax=PatternSyntax.LITERAL)
        ]
        
        # Compile patterns
        compiled_patterns = selection_manager.pattern_engine.compile_patterns(patterns)
        
        # Measure performance
        start_time = time.time()
        results = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns
        )
        duration = time.time() - start_time
        
        # Verify performance (LITERAL should be fastest)
        paths_per_second = len(test_paths) / duration
        assert paths_per_second >= 20000  # Should process at least 20k paths/sec
        assert all(r.matched for r in results)
    
    @pytest.mark.performance
    def test_mixed_pattern_performance(self, selection_manager):
        """Benchmark mixed pattern type performance."""
        # Generate diverse test paths
        test_paths = []
        for i in range(10000):
            if i % 3 == 0:
                test_paths.append(Path(f"/test/file_{i}.txt"))
            elif i % 3 == 1:
                test_paths.append(Path(f"/test/test_module_{i}.py"))
            else:
                test_paths.append(Path(f"/test/README.md"))
        
        # Create mixed patterns
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="test_.*\\.py", syntax=PatternSyntax.REGEX),
            PatternRule(pattern="README.md", syntax=PatternSyntax.LITERAL)
        ]
        
        # Compile patterns
        compiled_patterns = selection_manager.pattern_engine.compile_patterns(patterns)
        
        # Measure performance
        start_time = time.time()
        results = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns
        )
        duration = time.time() - start_time
        
        # Verify performance
        paths_per_second = len(test_paths) / duration
        assert paths_per_second >= 8000  # Should process at least 8k paths/sec
        
        # Verify all paths matched
        matched_count = sum(1 for r in results if r.matched)
        assert matched_count == len(test_paths)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_pattern_caching_performance(self, selection_manager):
        """Test that pattern caching improves performance."""
        # Generate test paths
        test_paths = [Path(f"/test/file_{i}.txt") for i in range(5000)]
        
        # Create patterns
        patterns = [
            PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
            PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB)
        ]
        
        # First compilation (cold cache)
        start_time = time.time()
        compiled_patterns1 = selection_manager.pattern_engine.compile_patterns(patterns)
        first_compile_time = time.time() - start_time
        
        # First matching
        start_time = time.time()
        results1 = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns1
        )
        first_match_time = time.time() - start_time
        
        # Second compilation (warm cache)
        start_time = time.time()
        compiled_patterns2 = selection_manager.pattern_engine.compile_patterns(patterns)
        second_compile_time = time.time() - start_time
        
        # Second matching (should benefit from cache)
        start_time = time.time()
        results2 = selection_manager.pattern_engine.batch_match_paths(
            test_paths,
            compiled_patterns2
        )
        second_match_time = time.time() - start_time
        
        # Verify caching improved performance
        cache_stats = selection_manager.pattern_engine.get_cache_statistics()
        assert cache_stats['cache_hits'] > 0
        
        # Second compilation should be faster or similar
        assert second_compile_time <= first_compile_time * 1.5
        
        # Results should be identical
        assert len(results1) == len(results2)


class TestPerformanceBenchmarking:
    """Tests for performance benchmarking functionality."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_benchmark_selection_performance(self, selection_manager):
        """Test performance benchmarking functionality."""
        # Generate test paths
        test_paths = [Path(f"/test/file_{i}.txt") for i in range(5000)]
        
        # Create selection config
        config = SelectionConfig(
            include_paths=[Path("/test")],
            exclude_paths=[],
            include_patterns=[
                PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB),
                PatternRule(pattern="*.py", syntax=PatternSyntax.GLOB)
            ],
            exclude_patterns=[
                PatternRule(pattern="*.tmp", syntax=PatternSyntax.GLOB)
            ],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # Run benchmark
        benchmark = await selection_manager.performance_optimizer.benchmark_selection_performance(
            config,
            test_paths
        )
        
        # Verify benchmark results
        assert benchmark.files_per_second > 0
        assert benchmark.memory_usage_mb >= 0
        assert 0 <= benchmark.cache_hit_ratio <= 1.0
        assert benchmark.test_duration_seconds > 0
        assert benchmark.test_file_count == len(test_paths)
        
        # Verify recommendations exist
        assert isinstance(benchmark.optimization_opportunities, list)
        assert isinstance(benchmark.bottlenecks, list)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, selection_manager):
        """Test optimization recommendation generation."""
        # Create config with many patterns
        patterns = [
            PatternRule(pattern=f"*.{ext}", syntax=PatternSyntax.GLOB)
            for ext in ['txt', 'py', 'md', 'log', 'tmp', 'json', 'xml', 'yaml']
        ]
        
        config = SelectionConfig(
            include_paths=[Path("/test")],
            exclude_paths=[],
            include_patterns=patterns,
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # Get recommendations
        hints = selection_manager.performance_optimizer.get_optimization_recommendations(
            config,
            estimated_file_count=50000
        )
        
        # Verify recommendations
        assert len(hints) > 0
        for hint in hints:
            assert hint.hint_type
            assert hint.message
            assert hint.impact in ['low', 'medium', 'high']
            assert hint.implementation
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_optimization_for_different_dataset_sizes(self, selection_manager):
        """Test optimization adapts to different dataset sizes."""
        config = SelectionConfig(
            include_paths=[Path("/test")],
            exclude_paths=[],
            include_patterns=[
                PatternRule(pattern="*.txt", syntax=PatternSyntax.GLOB)
            ],
            exclude_patterns=[],
            pattern_groups=[],
            precedence_config=PrecedenceConfig(),
            case_sensitive=False
        )
        
        # Test small dataset
        small_optimized = await selection_manager.performance_optimizer.optimize_selection_for_size(
            config,
            estimated_file_count=1000
        )
        
        # Test medium dataset
        medium_optimized = await selection_manager.performance_optimizer.optimize_selection_for_size(
            config,
            estimated_file_count=50000
        )
        
        # Test large dataset
        large_optimized = await selection_manager.performance_optimizer.optimize_selection_for_size(
            config,
            estimated_file_count=500000
        )
        
        # Verify different optimizations applied
        assert not small_optimized.streaming_recommended
        assert not medium_optimized.streaming_recommended
        assert large_optimized.streaming_recommended
        
        # Verify batch sizes increase with dataset size
        assert small_optimized.batch_size <= medium_optimized.batch_size
        assert medium_optimized.batch_size <= large_optimized.batch_size
        
        # Verify cache strategies differ
        assert small_optimized.cache_strategy != large_optimized.cache_strategy
