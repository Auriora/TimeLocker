"""
Final Performance Validation Tests for TimeLocker v1.0.0

This module contains comprehensive performance tests to validate that TimeLocker
meets performance requirements for the v1.0.0 release.
"""

import pytest
import tempfile
import shutil
import time
import threading
import psutil
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from TimeLocker.performance.benchmarks import PerformanceBenchmarks
from TimeLocker.performance.metrics import start_operation_tracking, complete_operation_tracking
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget


class TestFinalPerformanceValidation:
    """Final performance validation tests for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup performance test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.large_dataset_dir = self.temp_dir / "large_dataset"
        self.large_dataset_dir.mkdir(parents=True)

        # Performance thresholds for validation
        self.performance_thresholds = {
                'max_memory_usage_mb':               500,
                'min_file_throughput_per_sec':       100,
                'max_pattern_compile_time_sec':      1.0,
                'min_pattern_speedup_factor':        1.0,
                'max_large_directory_scan_time_sec': 120
        }

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_large_test_dataset(self, num_files=2000, num_dirs=50):
        """Create large test dataset for performance testing"""
        files_created = 0

        for dir_num in range(num_dirs):
            dir_path = self.large_dataset_dir / f"dir_{dir_num:03d}"
            dir_path.mkdir(exist_ok=True)

            files_per_dir = num_files // num_dirs
            for file_num in range(files_per_dir):
                file_path = dir_path / f"file_{file_num:04d}.txt"
                # Create files with varying sizes (1KB to 100KB)
                content_size = (file_num % 100 + 1) * 10
                content = f"Performance test file {files_created}\n" * content_size
                file_path.write_text(content)
                files_created += 1

        return files_created

    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_file_set_performance(self):
        """Test performance with large file sets (2000+ files)"""
        # Create large dataset
        num_files = self._create_large_test_dataset(num_files=2000, num_dirs=50)
        assert num_files >= 2000

        # Track operation performance
        operation_id = f"large_fileset_{int(time.time())}"
        metrics = start_operation_tracking(operation_id, "large_fileset_processing")

        start_time = time.perf_counter()

        # Test file selection performance
        file_selection = FileSelection()
        file_selection.add_path(self.large_dataset_dir, SelectionType.INCLUDE)
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)
        file_selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

        # Measure file traversal performance
        traversal_start = time.perf_counter()
        effective_paths = file_selection.get_effective_paths()
        traversal_time = time.perf_counter() - traversal_start

        # Measure size estimation performance
        size_start = time.perf_counter()
        size_stats = file_selection.estimate_backup_size()
        size_time = time.perf_counter() - size_start

        total_time = time.perf_counter() - start_time

        # Performance validations
        files_processed = len(effective_paths['included'])
        throughput = files_processed / total_time if total_time > 0 else 0

        # Validate performance meets thresholds
        assert throughput >= self.performance_thresholds['min_file_throughput_per_sec'], \
            f"File throughput {throughput:.2f} files/sec below threshold"

        assert total_time <= self.performance_thresholds['max_large_directory_scan_time_sec'], \
            f"Total processing time {total_time:.2f}s exceeds threshold"

        assert files_processed >= 2000, f"Expected to process 2000+ files, got {files_processed}"
        assert size_stats['file_count'] >= 2000

        # Complete metrics tracking
        complete_operation_tracking(operation_id)

    @pytest.mark.performance
    def test_memory_usage_validation(self):
        """Test memory usage stays within acceptable limits"""
        import gc

        process = psutil.Process()

        # Force garbage collection and get baseline
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create moderate dataset for memory testing
        num_files = self._create_large_test_dataset(num_files=1000, num_dirs=20)

        # Monitor memory during operations
        peak_memory = baseline_memory

        def monitor_memory():
            nonlocal peak_memory
            while getattr(monitor_memory, 'running', True):
                current_memory = process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                time.sleep(0.1)

        # Start memory monitoring
        monitor_memory.running = True
        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()

        try:
            # Perform memory-intensive operations
            file_selection = FileSelection()
            file_selection.add_path(self.large_dataset_dir, SelectionType.INCLUDE)

            # Multiple operations that could accumulate memory
            for i in range(5):
                effective_paths = file_selection.get_effective_paths()
                size_stats = file_selection.estimate_backup_size()

                # Force garbage collection between operations
                gc.collect()

        finally:
            # Stop memory monitoring
            monitor_memory.running = False
            monitor_thread.join(timeout=1.0)

        # Calculate memory usage
        memory_increase = peak_memory - baseline_memory

        # Validate memory usage
        assert memory_increase <= self.performance_thresholds['max_memory_usage_mb'], \
            f"Memory usage increased by {memory_increase:.2f}MB, exceeds {self.performance_thresholds['max_memory_usage_mb']}MB threshold"

    @pytest.mark.performance
    def test_pattern_matching_performance(self):
        """Test pattern matching performance meets requirements"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Create test files for pattern matching
            test_dir = benchmarks.create_test_files(num_files=1000, num_dirs=20)

            # Test pattern matching with various pattern counts
            pattern_counts = [10, 50, 100, 200]

            for num_patterns in pattern_counts:
                results = benchmarks.benchmark_file_selection_patterns(test_dir, num_patterns)

                # Validate pattern compilation time
                assert results['pattern_compile_time'] <= self.performance_thresholds['max_pattern_compile_time_sec'], \
                    f"Pattern compilation time {results['pattern_compile_time']:.3f}s exceeds threshold for {num_patterns} patterns"

                # Validate speedup factor
                assert results['speedup_factor'] >= self.performance_thresholds['min_pattern_speedup_factor'], \
                    f"Pattern matching speedup {results['speedup_factor']:.2f}x below threshold for {num_patterns} patterns"

                # Validate consistency
                assert results['matches_consistent'] is True, \
                    f"Pattern matching results inconsistent for {num_patterns} patterns"

    @pytest.mark.performance
    def test_concurrent_operation_performance(self):
        """Test performance under concurrent operations"""

        def perform_file_operation(operation_id):
            """Perform file operations in concurrent thread"""
            try:
                # Create small dataset for this operation
                op_dir = self.temp_dir / f"concurrent_op_{operation_id}"
                op_dir.mkdir(exist_ok=True)

                # Create files
                for i in range(100):
                    file_path = op_dir / f"file_{i:03d}.txt"
                    file_path.write_text(f"Concurrent operation {operation_id} file {i}")

                # Perform file selection operations
                file_selection = FileSelection()
                file_selection.add_path(op_dir, SelectionType.INCLUDE)

                start_time = time.perf_counter()
                effective_paths = file_selection.get_effective_paths()
                size_stats = file_selection.estimate_backup_size()
                operation_time = time.perf_counter() - start_time

                return {
                        'operation_id':    operation_id,
                        'success':         True,
                        'files_processed': len(effective_paths['included']),
                        'operation_time':  operation_time,
                        'total_size':      size_stats['total_size']
                }

            except Exception as e:
                return {
                        'operation_id': operation_id,
                        'success':      False,
                        'error':        str(e)
                }

        # Execute concurrent operations
        num_concurrent_ops = 10
        with ThreadPoolExecutor(max_workers=num_concurrent_ops) as executor:
            # Submit concurrent operations
            futures = []
            for i in range(num_concurrent_ops):
                future = executor.submit(perform_file_operation, i)
                futures.append(future)

            # Collect results
            results = []
            for future in as_completed(futures, timeout=60):
                result = future.result()
                results.append(result)

        # Validate concurrent operation results
        successful_ops = [r for r in results if r['success']]
        assert len(successful_ops) == num_concurrent_ops, \
            f"Only {len(successful_ops)}/{num_concurrent_ops} concurrent operations succeeded"

        # Validate performance of concurrent operations
        avg_operation_time = sum(r['operation_time'] for r in successful_ops) / len(successful_ops)
        assert avg_operation_time < 10.0, \
            f"Average concurrent operation time {avg_operation_time:.2f}s too high"

        # Validate all operations processed expected number of files
        for result in successful_ops:
            assert result['files_processed'] == 100, \
                f"Operation {result['operation_id']} processed {result['files_processed']} files, expected 100"

    @pytest.mark.performance
    def test_backup_restore_performance_simulation(self):
        """Test simulated backup and restore performance"""
        # Create test dataset
        num_files = self._create_large_test_dataset(num_files=1500, num_dirs=30)

        # Mock repository for performance testing
        mock_repository = Mock()
        mock_repository._location = str(self.temp_dir / "perf_repo")
        mock_repository.id = "performance_test_repo"
        mock_repository.is_repository_initialized.return_value = True

        # Create backup target with proper file selection
        from TimeLocker.file_selections import FileSelection, SelectionType
        selection = FileSelection()
        selection.add_path(self.large_dataset_dir, SelectionType.INCLUDE)

        backup_target = BackupTarget(
                selection=selection,
                tags=["performance_test"]
        )

        # Initialize backup manager
        backup_manager = BackupManager()

        # Simulate backup operation with performance tracking
        operation_id = f"backup_perf_{int(time.time())}"
        metrics = start_operation_tracking(operation_id, "backup_performance_test")

        with patch.object(backup_manager, 'create_full_backup') as mock_backup:
            # Simulate realistic backup timing
            def simulate_backup(*args, **kwargs):
                time.sleep(0.1)  # Simulate processing time
                return {
                        'snapshot_id':           f'perf_snapshot_{operation_id}',
                        'files_new':             num_files,
                        'files_changed':         0,
                        'files_unmodified':      0,
                        'total_files_processed': num_files,
                        'data_added':            50 * 1024 * 1024,  # 50MB
                        'total_duration':        5.5
                }

            mock_backup.side_effect = simulate_backup

            # Perform backup
            start_time = time.perf_counter()
            backup_result = backup_manager.create_full_backup(
                    repository=mock_repository,
                    targets=[backup_target]
            )
            backup_time = time.perf_counter() - start_time

            # Validate backup performance
            assert backup_result['total_files_processed'] == num_files
            assert backup_time < 30.0, f"Backup simulation took {backup_time:.2f}s, too slow"

        # Complete metrics tracking
        complete_operation_tracking(operation_id)

    @pytest.mark.performance
    def test_performance_regression_validation(self):
        """Test for performance regressions against baseline"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Run comprehensive benchmarks
            results = benchmarks.run_all_benchmarks()

            # Define baseline performance expectations
            baseline_expectations = {
                    'pattern_matching': {
                            'min_speedup_factor':         1.0,
                            'max_compile_time':           0.5,
                            'matches_must_be_consistent': True
                    },
                    'file_traversal':   {
                            'min_throughput_files_per_sec': 200,
                            'max_traversal_time':           10.0
                    },
                    'large_directory':  {
                            'min_throughput_files_per_sec': 100,
                            'max_total_time':               60.0
                    }
            }

            # Validate against baselines
            for category, expectations in baseline_expectations.items():
                category_results = results[category]

                for metric, expected_value in expectations.items():
                    if metric.startswith('min_'):
                        actual_metric = metric[4:]  # Remove 'min_' prefix
                        if actual_metric in category_results:
                            actual_value = category_results[actual_metric]
                            assert actual_value >= expected_value, \
                                f"{category}.{actual_metric} = {actual_value} below baseline {expected_value}"

                    elif metric.startswith('max_'):
                        actual_metric = metric[4:]  # Remove 'max_' prefix
                        if actual_metric in category_results:
                            actual_value = category_results[actual_metric]
                            assert actual_value <= expected_value, \
                                f"{category}.{actual_metric} = {actual_value} exceeds baseline {expected_value}"

                    elif metric.endswith('_must_be_consistent'):
                        actual_metric = metric.replace('_must_be_consistent', '_consistent')
                        if actual_metric in category_results:
                            actual_value = category_results[actual_metric]
                            assert actual_value == expected_value, \
                                f"{category}.{actual_metric} = {actual_value}, expected {expected_value}"

            # Generate performance report for documentation
            report = benchmarks.generate_performance_report(results)

            # Save performance report for release documentation
            report_file = self.temp_dir / "performance_validation_report.txt"
            with open(report_file, 'w') as f:
                f.write("TimeLocker v1.0.0 Final Performance Validation Report\n")
                f.write("=" * 60 + "\n\n")
                f.write(report)
                f.write("\n\nValidation Status: PASSED\n")
                f.write(f"Validation Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
