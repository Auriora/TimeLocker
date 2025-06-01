"""
Performance benchmarks for TimeLocker operations
"""

import tempfile
import shutil
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from ..file_selections import FileSelection, SelectionType
from .profiler import PerformanceProfiler
from .metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class PerformanceBenchmarks:
    """Performance benchmarks for TimeLocker operations"""

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp(prefix="timelocker_bench_"))
        self.profiler = PerformanceProfiler()
        self.metrics = PerformanceMetrics()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_files(self, num_files: int = 1000, file_size: int = 1024,
                          num_dirs: int = 10) -> Path:
        """Create test files for benchmarking"""
        test_dir = self.temp_dir / "test_files"
        test_dir.mkdir(exist_ok=True)

        # Create directory structure
        for i in range(num_dirs):
            dir_path = test_dir / f"dir_{i:03d}"
            dir_path.mkdir(exist_ok=True)

            # Create files in each directory
            files_per_dir = num_files // num_dirs
            for j in range(files_per_dir):
                file_path = dir_path / f"file_{j:04d}.txt"
                with open(file_path, 'w') as f:
                    f.write('x' * file_size)

        # Create some additional files with different extensions
        for ext in ['.log', '.tmp', '.bak', '.py', '.js']:
            for i in range(10):
                file_path = test_dir / f"test_{i}{ext}"
                with open(file_path, 'w') as f:
                    f.write('test content' * 10)

        return test_dir

    def benchmark_file_selection_patterns(self, test_dir: Path,
                                          num_patterns: int = 100) -> Dict[str, Any]:
        """Benchmark file selection pattern matching performance"""
        logger.info(f"Benchmarking file selection with {num_patterns} patterns")

        selection = FileSelection()
        selection.add_path(test_dir, SelectionType.INCLUDE)

        # Add various patterns
        patterns = [
                "*.txt", "*.log", "*.tmp", "*.bak", "*.py", "*.js",
                "dir_*/*", "*/file_*", "**/test_*", "**/*.txt"
        ]

        # Extend patterns to reach desired count
        extended_patterns = patterns * (num_patterns // len(patterns) + 1)
        for pattern in extended_patterns[:num_patterns]:
            selection.add_pattern(pattern, SelectionType.EXCLUDE)

        # Benchmark pattern compilation
        start_time = time.perf_counter()
        selection._compile_patterns()
        compile_time = time.perf_counter() - start_time

        # Benchmark file matching
        test_files = list(test_dir.rglob("*"))
        test_files = [f for f in test_files if f.is_file()][:1000]  # Limit for benchmark

        # Test legacy pattern matching
        start_time = time.perf_counter()
        legacy_matches = 0
        for file_path in test_files:
            if selection.matches_pattern(file_path, selection._exclude_patterns):
                legacy_matches += 1
        legacy_time = time.perf_counter() - start_time

        # Test optimized pattern matching
        start_time = time.perf_counter()
        optimized_matches = 0
        for file_path in test_files:
            if selection._matches_compiled_patterns(file_path, selection._compiled_exclude_patterns):
                optimized_matches += 1
        optimized_time = time.perf_counter() - start_time

        return {
                'num_patterns':         num_patterns,
                'num_test_files':       len(test_files),
                'pattern_compile_time': compile_time,
                'legacy_match_time':    legacy_time,
                'optimized_match_time': optimized_time,
                'speedup_factor':       legacy_time / optimized_time if optimized_time > 0 else 0,
                'legacy_matches':       legacy_matches,
                'optimized_matches':    optimized_matches,
                'matches_consistent':   legacy_matches == optimized_matches
        }

    def benchmark_file_traversal(self, test_dir: Path) -> Dict[str, Any]:
        """Benchmark file traversal performance"""
        logger.info("Benchmarking file traversal performance")

        selection = FileSelection()
        selection.add_path(test_dir, SelectionType.INCLUDE)
        selection.add_pattern("*.tmp", SelectionType.EXCLUDE)
        selection.add_pattern("*.bak", SelectionType.EXCLUDE)

        # Benchmark get_effective_paths
        start_time = time.perf_counter()
        effective_paths = selection.get_effective_paths()
        traversal_time = time.perf_counter() - start_time

        # Benchmark estimate_backup_size
        start_time = time.perf_counter()
        size_stats = selection.estimate_backup_size()
        size_estimation_time = time.perf_counter() - start_time

        return {
                'traversal_time':           traversal_time,
                'size_estimation_time':     size_estimation_time,
                'files_included':           len(effective_paths['included']),
                'files_excluded':           len(effective_paths['excluded']),
                'total_size_bytes':         size_stats['total_size'],
                'file_count':               size_stats['file_count'],
                'directory_count':          size_stats['directory_count'],
                'throughput_files_per_sec': size_stats['file_count'] / traversal_time if traversal_time > 0 else 0
        }

    def benchmark_large_directory_scan(self, num_files: int = 10000) -> Dict[str, Any]:
        """Benchmark performance with large directory structures"""
        logger.info(f"Benchmarking large directory scan with {num_files} files")

        # Create large test directory
        test_dir = self.create_test_files(num_files=num_files, num_dirs=100)

        selection = FileSelection()
        selection.add_path(test_dir, SelectionType.INCLUDE)

        # Add complex patterns
        patterns = [
                "*.tmp", "*.log", "*.bak", "**/cache/*", "**/temp/*",
                "**/__pycache__/*", "**/node_modules/*", "**/.git/*"
        ]
        for pattern in patterns:
            selection.add_pattern(pattern, SelectionType.EXCLUDE)

        # Benchmark with profiling
        start_time = time.perf_counter()
        effective_paths = selection.get_effective_paths()
        traversal_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        size_stats = selection.estimate_backup_size()
        size_time = time.perf_counter() - start_time

        return {
                'num_files_created':        num_files,
                'traversal_time':           traversal_time,
                'size_estimation_time':     size_time,
                'files_included':           len(effective_paths['included']),
                'total_size_bytes':         size_stats['total_size'],
                'throughput_files_per_sec': size_stats['file_count'] / (traversal_time + size_time) if (traversal_time + size_time) > 0 else 0
        }

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks"""
        logger.info("Running all performance benchmarks")

        results = {}

        # Create test files
        test_dir = self.create_test_files(num_files=1000, num_dirs=20)

        # Run benchmarks
        results['pattern_matching'] = self.benchmark_file_selection_patterns(test_dir, num_patterns=50)
        results['file_traversal'] = self.benchmark_file_traversal(test_dir)
        results['large_directory'] = self.benchmark_large_directory_scan(num_files=5000)

        # Get profiler summary
        results['profiler_summary'] = self.profiler.get_metrics_summary()

        return results

    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable performance report"""
        report = []
        report.append("TimeLocker Performance Benchmark Report")
        report.append("=" * 50)
        report.append("")

        # Pattern matching results
        pm = results.get('pattern_matching', {})
        if pm:
            report.append("Pattern Matching Performance:")
            report.append(f"  Patterns tested: {pm.get('num_patterns', 0)}")
            report.append(f"  Test files: {pm.get('num_test_files', 0)}")
            report.append(f"  Pattern compile time: {pm.get('pattern_compile_time', 0):.4f}s")
            report.append(f"  Legacy matching time: {pm.get('legacy_match_time', 0):.4f}s")
            report.append(f"  Optimized matching time: {pm.get('optimized_match_time', 0):.4f}s")
            report.append(f"  Speedup factor: {pm.get('speedup_factor', 0):.2f}x")
            report.append(f"  Results consistent: {pm.get('matches_consistent', False)}")
            report.append("")

        # File traversal results
        ft = results.get('file_traversal', {})
        if ft:
            report.append("File Traversal Performance:")
            report.append(f"  Traversal time: {ft.get('traversal_time', 0):.4f}s")
            report.append(f"  Size estimation time: {ft.get('size_estimation_time', 0):.4f}s")
            report.append(f"  Files included: {ft.get('files_included', 0)}")
            report.append(f"  Total size: {ft.get('total_size_bytes', 0):,} bytes")
            report.append(f"  Throughput: {ft.get('throughput_files_per_sec', 0):.1f} files/sec")
            report.append("")

        # Large directory results
        ld = results.get('large_directory', {})
        if ld:
            report.append("Large Directory Performance:")
            report.append(f"  Files created: {ld.get('num_files_created', 0):,}")
            report.append(f"  Traversal time: {ld.get('traversal_time', 0):.4f}s")
            report.append(f"  Size estimation time: {ld.get('size_estimation_time', 0):.4f}s")
            report.append(f"  Files included: {ld.get('files_included', 0):,}")
            report.append(f"  Throughput: {ld.get('throughput_files_per_sec', 0):.1f} files/sec")
            report.append("")

        return "\n".join(report)
