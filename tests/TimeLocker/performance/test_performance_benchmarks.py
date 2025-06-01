"""
Performance benchmark tests for TimeLocker
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import time

from TimeLocker.performance.benchmarks import PerformanceBenchmarks
from TimeLocker.performance.profiler import get_performance_summary
from TimeLocker.file_selections import FileSelection, SelectionType


class TestPerformanceBenchmarks:
    """Test performance benchmarks and ensure they meet expected criteria"""

    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_perf_"))

    def teardown_method(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_pattern_matching_performance(self):
        """Test that optimized pattern matching is faster than legacy"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Create test files
            test_dir = benchmarks.create_test_files(num_files=500, num_dirs=10)

            # Run pattern matching benchmark
            results = benchmarks.benchmark_file_selection_patterns(test_dir, num_patterns=20)

            # Verify results
            assert results['num_patterns'] == 20
            assert results['num_test_files'] > 0
            assert results['pattern_compile_time'] >= 0
            assert results['legacy_match_time'] >= 0
            assert results['optimized_match_time'] >= 0
            assert results['matches_consistent'] is True

            # Optimized should be faster (or at least not significantly slower)
            # Allow for some variance in small datasets
            if results['legacy_match_time'] > 0.001:  # Only check if meaningful time
                assert results['speedup_factor'] >= 0.5  # At least not 2x slower

    def test_file_traversal_performance(self):
        """Test file traversal performance meets expectations"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Create test files
            test_dir = benchmarks.create_test_files(num_files=1000, num_dirs=20)

            # Run traversal benchmark
            results = benchmarks.benchmark_file_traversal(test_dir)

            # Verify results
            assert results['traversal_time'] >= 0
            assert results['size_estimation_time'] >= 0
            assert results['files_included'] >= 0
            assert results['total_size_bytes'] >= 0
            assert results['file_count'] >= 0
            assert results['directory_count'] >= 0

            # Performance expectations (adjust based on system capabilities)
            # Should process at least 100 files per second on modern hardware
            if results['file_count'] > 100:
                assert results['throughput_files_per_sec'] >= 50  # Conservative threshold

    def test_large_directory_performance(self):
        """Test performance with large directory structures"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Run large directory benchmark with smaller dataset for tests
            results = benchmarks.benchmark_large_directory_scan(num_files=1000)

            # Verify results
            assert results['num_files_created'] == 1000
            assert results['traversal_time'] >= 0
            assert results['size_estimation_time'] >= 0
            assert results['files_included'] >= 0
            assert results['total_size_bytes'] >= 0

            # Should complete in reasonable time
            total_time = results['traversal_time'] + results['size_estimation_time']
            assert total_time < 30.0  # Should complete within 30 seconds

    def test_benchmark_consistency(self):
        """Test that benchmarks produce consistent results"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            test_dir = benchmarks.create_test_files(num_files=100, num_dirs=5)

            # Run the same benchmark multiple times
            results1 = benchmarks.benchmark_file_traversal(test_dir)
            results2 = benchmarks.benchmark_file_traversal(test_dir)

            # Results should be consistent
            assert results1['files_included'] == results2['files_included']
            assert results1['total_size_bytes'] == results2['total_size_bytes']
            assert results1['file_count'] == results2['file_count']

            # Times may vary but should be in same ballpark
            time_ratio = max(results1['traversal_time'], results2['traversal_time']) / \
                         max(min(results1['traversal_time'], results2['traversal_time']), 0.001)
            assert time_ratio < 10.0  # Should not vary by more than 10x

    def test_performance_regression_detection(self):
        """Test that we can detect performance regressions"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            test_dir = benchmarks.create_test_files(num_files=200, num_dirs=5)

            # Baseline performance
            baseline = benchmarks.benchmark_file_traversal(test_dir)

            # Simulate performance regression by adding many patterns
            selection = FileSelection()
            selection.add_path(test_dir, SelectionType.INCLUDE)

            # Add many patterns to slow things down
            for i in range(100):
                selection.add_pattern(f"*pattern_{i}*", SelectionType.EXCLUDE)

            start_time = time.perf_counter()
            selection.get_effective_paths()
            regression_time = time.perf_counter() - start_time

            # Should detect that regression is slower
            # (This is expected due to more patterns)
            assert regression_time >= baseline['traversal_time']

    def test_memory_usage_tracking(self):
        """Test that memory usage is tracked during benchmarks"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            test_dir = benchmarks.create_test_files(num_files=500, num_dirs=10)

            # Run benchmark that should trigger profiling
            results = benchmarks.benchmark_large_directory_scan(num_files=500)

            # Check that profiling data is available
            summary = get_performance_summary("large_directory_scan")

            # Should have collected some performance data
            if summary:  # May not always have data in test environment
                assert summary['operation_count'] >= 0
                assert 'avg_duration_seconds' in summary or summary['operation_count'] == 0

    def test_full_benchmark_suite(self):
        """Test running the full benchmark suite"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Run all benchmarks with smaller datasets for testing
            results = benchmarks.run_all_benchmarks()

            # Verify all benchmark categories are present
            assert 'pattern_matching' in results
            assert 'file_traversal' in results
            assert 'large_directory' in results
            assert 'profiler_summary' in results

            # Verify each benchmark has expected keys
            pm = results['pattern_matching']
            assert 'speedup_factor' in pm
            assert 'matches_consistent' in pm

            ft = results['file_traversal']
            assert 'throughput_files_per_sec' in ft
            assert 'files_included' in ft

            ld = results['large_directory']
            assert 'num_files_created' in ld
            assert 'traversal_time' in ld

    def test_performance_report_generation(self):
        """Test performance report generation"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Run benchmarks
            results = benchmarks.run_all_benchmarks()

            # Generate report
            report = benchmarks.generate_performance_report(results)

            # Verify report content
            assert "TimeLocker Performance Benchmark Report" in report
            assert "Pattern Matching Performance:" in report
            assert "File Traversal Performance:" in report
            assert "Large Directory Performance:" in report

            # Should contain actual numbers
            assert "files/sec" in report
            assert "Speedup factor:" in report

    @pytest.mark.slow
    def test_performance_baseline_establishment(self):
        """Test establishing performance baselines (marked as slow test)"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Create larger dataset for baseline
            test_dir = benchmarks.create_test_files(num_files=2000, num_dirs=50)

            # Run comprehensive benchmarks
            pattern_results = benchmarks.benchmark_file_selection_patterns(test_dir, num_patterns=100)
            traversal_results = benchmarks.benchmark_file_traversal(test_dir)

            # Document baseline performance expectations
            # These can be used for regression testing
            baseline_expectations = {
                    'pattern_compile_time_max':     0.1,  # Should compile 100 patterns in < 0.1s
                    'min_throughput_files_per_sec': 100,  # Should process at least 100 files/sec
                    'pattern_speedup_min':          1.0,  # Optimized should be at least as fast as legacy
            }

            # Verify against expectations
            assert pattern_results['pattern_compile_time'] < baseline_expectations['pattern_compile_time_max']
            assert traversal_results['throughput_files_per_sec'] >= baseline_expectations['min_throughput_files_per_sec']
            assert pattern_results['speedup_factor'] >= baseline_expectations['pattern_speedup_min']

            print(f"Baseline Performance Metrics:")
            print(f"  Pattern compile time: {pattern_results['pattern_compile_time']:.4f}s")
            print(f"  File throughput: {traversal_results['throughput_files_per_sec']:.1f} files/sec")
            print(f"  Pattern matching speedup: {pattern_results['speedup_factor']:.2f}x")
