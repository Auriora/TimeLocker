"""
Stress Testing for TimeLocker v1.0.0

This module contains stress tests to validate TimeLocker performance and stability
under extreme conditions and edge cases.
"""

import pytest
import tempfile
import shutil
import threading
import time
import psutil
import gc
from pathlib import Path
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.security import CredentialManager, SecurityService


class TestStressTesting:
    """Stress testing for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup stress test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.stress_data_dir = self.temp_dir / "stress_data"
        self.stress_data_dir.mkdir(parents=True)

        # Stress test parameters
        self.stress_params = {
                'max_files':          5000,
                'max_directories':    500,
                'max_file_size':      10 * 1024 * 1024,  # 10MB
                'max_memory_mb':      1000,  # 1GB
                'max_concurrent_ops': 20,
                'max_test_duration':  300  # 5 minutes
        }

    def teardown_method(self):
        """Cleanup stress test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_stress_dataset(self, num_files=1000, num_dirs=100):
        """Create large dataset for stress testing"""
        files_created = 0

        for dir_num in range(num_dirs):
            dir_path = self.stress_data_dir / f"stress_dir_{dir_num:04d}"
            dir_path.mkdir(exist_ok=True)

            files_per_dir = num_files // num_dirs
            for file_num in range(files_per_dir):
                file_path = dir_path / f"stress_file_{file_num:06d}.dat"

                # Create files with varying sizes
                file_size = (file_num % 100 + 1) * 1024  # 1KB to 100KB
                content = b"X" * file_size
                file_path.write_bytes(content)
                files_created += 1

                # Create some larger files occasionally
                if file_num % 50 == 0:
                    large_file = dir_path / f"large_file_{file_num:06d}.dat"
                    large_content = b"L" * (1024 * 1024)  # 1MB
                    large_file.write_bytes(large_content)
                    files_created += 1

        return files_created

    @pytest.mark.stress
    @pytest.mark.slow
    def test_large_file_set_stress(self):
        """Stress test with very large file sets"""
        # Create large dataset
        num_files = self._create_stress_dataset(
                num_files=self.stress_params['max_files'],
                num_dirs=self.stress_params['max_directories']
        )

        assert num_files >= self.stress_params['max_files']

        # Monitor memory during stress test
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory

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
            # Perform stress operations
            file_selection = FileSelection()
            file_selection.add_path(self.stress_data_dir, SelectionType.INCLUDE)

            # Add complex patterns
            patterns = [
                    "*.dat", "*.txt", "*.log", "*.tmp", "*.bak",
                    "*stress*", "*large*", "*test*", "*file*",
                    "stress_dir_*/*", "*/large_*", "*/stress_file_*"
            ]

            for pattern in patterns:
                file_selection.add_pattern(pattern, SelectionType.INCLUDE)

            # Stress test file traversal
            start_time = time.perf_counter()
            effective_paths = file_selection.get_effective_paths()
            traversal_time = time.perf_counter() - start_time

            # Stress test size estimation
            start_time = time.perf_counter()
            size_stats = file_selection.estimate_backup_size()
            estimation_time = time.perf_counter() - start_time

            # Validate results
            assert len(effective_paths['included']) >= num_files * 0.8  # At least 80% found
            assert size_stats['file_count'] >= num_files * 0.8
            assert size_stats['total_size'] > 0

            # Performance validation
            assert traversal_time < 60.0, f"Traversal took {traversal_time:.2f}s, too slow"
            assert estimation_time < 30.0, f"Estimation took {estimation_time:.2f}s, too slow"

        finally:
            # Stop memory monitoring
            monitor_memory.running = False
            monitor_thread.join(timeout=1.0)

        # Memory validation
        memory_increase = peak_memory - initial_memory
        assert memory_increase < self.stress_params['max_memory_mb'], \
            f"Memory usage increased by {memory_increase:.2f}MB, exceeds limit"

    @pytest.mark.stress
    def test_concurrent_operations_stress(self):
        """Stress test with many concurrent operations"""

        def stress_operation(operation_id):
            """Perform stress operation"""
            try:
                # Create operation-specific dataset
                op_dir = self.temp_dir / f"stress_op_{operation_id}"
                op_dir.mkdir(exist_ok=True)

                # Create files for this operation
                for i in range(100):
                    file_path = op_dir / f"op_{operation_id}_file_{i:03d}.txt"
                    content = f"Stress operation {operation_id} file {i}\n" * (i + 1)
                    file_path.write_text(content)

                # Perform file selection operations
                file_selection = FileSelection()
                file_selection.add_path(op_dir, SelectionType.INCLUDE)
                file_selection.add_pattern("*.txt", SelectionType.INCLUDE)

                # Multiple operations to stress the system
                for _ in range(5):
                    effective_paths = file_selection.get_effective_paths()
                    size_stats = file_selection.estimate_backup_size()

                    # Validate results
                    assert len(effective_paths['included']) == 100
                    assert size_stats['file_count'] == 100

                return {
                        'operation_id':    operation_id,
                        'success':         True,
                        'files_processed': 100
                }

            except Exception as e:
                return {
                        'operation_id': operation_id,
                        'success':      False,
                        'error':        str(e)
                }

        # Execute many concurrent operations
        num_operations = self.stress_params['max_concurrent_ops']

        with ThreadPoolExecutor(max_workers=num_operations) as executor:
            # Submit all operations
            futures = []
            for i in range(num_operations):
                future = executor.submit(stress_operation, i)
                futures.append(future)

            # Collect results with timeout
            results = []
            for future in as_completed(futures, timeout=self.stress_params['max_test_duration']):
                result = future.result()
                results.append(result)

        # Validate all operations completed successfully
        successful_ops = [r for r in results if r['success']]
        assert len(successful_ops) == num_operations, \
            f"Only {len(successful_ops)}/{num_operations} operations succeeded"

        # Validate no errors occurred
        failed_ops = [r for r in results if not r['success']]
        if failed_ops:
            for failed_op in failed_ops:
                print(f"Operation {failed_op['operation_id']} failed: {failed_op.get('error', 'Unknown error')}")
            pytest.fail(f"{len(failed_ops)} operations failed")

    @pytest.mark.stress
    def test_memory_pressure_handling(self):
        """Test behavior under memory pressure"""
        # Create dataset that could cause memory pressure
        large_dataset_files = self._create_stress_dataset(num_files=2000, num_dirs=200)

        # Monitor memory usage
        process = psutil.Process()
        memory_samples = []

        def collect_memory_samples():
            while getattr(collect_memory_samples, 'running', True):
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
                time.sleep(0.5)

        # Start memory monitoring
        collect_memory_samples.running = True
        memory_thread = threading.Thread(target=collect_memory_samples, daemon=True)
        memory_thread.start()

        try:
            # Perform operations that could use significant memory
            file_selection = FileSelection()
            file_selection.add_path(self.stress_data_dir, SelectionType.INCLUDE)

            # Add many patterns to increase memory usage
            for i in range(100):
                file_selection.add_pattern(f"*{i:03d}*", SelectionType.INCLUDE)

            # Perform multiple operations without cleanup
            results = []
            for iteration in range(10):
                effective_paths = file_selection.get_effective_paths()
                size_stats = file_selection.estimate_backup_size()
                results.append((effective_paths, size_stats))

                # Force garbage collection periodically
                if iteration % 3 == 0:
                    gc.collect()

            # Validate operations completed
            assert len(results) == 10
            for effective_paths, size_stats in results:
                assert len(effective_paths['included']) > 0
                assert size_stats['file_count'] > 0

        finally:
            # Stop memory monitoring
            collect_memory_samples.running = False
            memory_thread.join(timeout=1.0)

        # Analyze memory usage patterns
        if memory_samples:
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            avg_memory = sum(memory_samples) / len(memory_samples)

            print(f"Memory usage - Min: {min_memory:.1f}MB, Max: {max_memory:.1f}MB, Avg: {avg_memory:.1f}MB")

            # Memory should not grow excessively
            memory_growth = max_memory - min_memory
            assert memory_growth < 500, f"Memory grew by {memory_growth:.1f}MB, too much"

    @pytest.mark.stress
    def test_pattern_complexity_stress(self):
        """Stress test with very complex pattern matching"""
        # Create diverse file structure
        self._create_stress_dataset(num_files=1000, num_dirs=50)

        # Create files with complex naming patterns
        complex_dir = self.stress_data_dir / "complex_patterns"
        complex_dir.mkdir(exist_ok=True)

        complex_files = [
                "file.with.many.dots.txt",
                "file-with-many-dashes.log",
                "file_with_many_underscores.dat",
                "UPPERCASE_FILE.TXT",
                "MixedCase_File.Log",
                "file with spaces.txt",
                "file(with)parentheses.dat",
                "file[with]brackets.txt",
                "file{with}braces.log",
                "file@with#special$chars%.dat"
        ]

        for filename in complex_files:
            try:
                file_path = complex_dir / filename
                file_path.write_text(f"Content for {filename}")
            except OSError:
                # Skip files that can't be created on this platform
                continue

        # Create file selection with many complex patterns
        file_selection = FileSelection()
        file_selection.add_path(self.stress_data_dir, SelectionType.INCLUDE)

        # Add many complex patterns
        complex_patterns = [
                "*.txt", "*.log", "*.dat", "*.tmp", "*.bak",
                "*stress*", "*file*", "*test*", "*large*",
                "stress_dir_*/*", "*/stress_file_*", "*/large_file_*",
                "*with*", "*many*", "*dots*", "*dashes*",
                "UPPERCASE*", "MixedCase*", "*spaces*",
                "*parentheses*", "*brackets*", "*braces*",
                "file.*", "*.with.*", "*_*", "*-*",
                "stress_dir_[0-9]*/*", "*/stress_file_[0-9]*",
                "*{[0-9][0-9][0-9]}*", "*file_[0-9][0-9][0-9][0-9][0-9][0-9]*"
        ]

        # Measure pattern compilation time
        start_time = time.perf_counter()
        for pattern in complex_patterns:
            file_selection.add_pattern(pattern, SelectionType.INCLUDE)
        pattern_time = time.perf_counter() - start_time

        # Measure matching time
        start_time = time.perf_counter()
        effective_paths = file_selection.get_effective_paths()
        matching_time = time.perf_counter() - start_time

        # Validate performance
        assert pattern_time < 5.0, f"Pattern compilation took {pattern_time:.2f}s, too slow"
        assert matching_time < 30.0, f"Pattern matching took {matching_time:.2f}s, too slow"

        # Validate results
        assert len(effective_paths['included']) > 0
        print(f"Complex pattern matching: {len(effective_paths['included'])} files matched")

    @pytest.mark.stress
    def test_long_running_operations(self):
        """Test stability during long-running operations"""
        # Create dataset for long-running test
        self._create_stress_dataset(num_files=1500, num_dirs=150)

        file_selection = FileSelection()
        file_selection.add_path(self.stress_data_dir, SelectionType.INCLUDE)
        file_selection.add_pattern("*.dat", SelectionType.INCLUDE)

        # Perform operations repeatedly for extended period
        start_time = time.time()
        max_duration = 60  # 1 minute of continuous operations
        iteration_count = 0

        while (time.time() - start_time) < max_duration:
            # Perform file operations
            effective_paths = file_selection.get_effective_paths()
            size_stats = file_selection.estimate_backup_size()

            # Validate each iteration
            assert len(effective_paths['included']) > 0
            assert size_stats['file_count'] > 0

            iteration_count += 1

            # Brief pause to prevent overwhelming the system
            time.sleep(0.1)

        # Validate long-running stability
        assert iteration_count > 100, f"Only {iteration_count} iterations completed"
        print(f"Long-running test: {iteration_count} iterations in {max_duration}s")

    @pytest.mark.stress
    def test_resource_cleanup_stress(self):
        """Test proper resource cleanup under stress"""
        initial_fd_count = len(psutil.Process().open_files())

        # Perform many operations that could leak resources
        for iteration in range(100):
            # Create temporary file selection
            file_selection = FileSelection()
            file_selection.add_path(self.stress_data_dir, SelectionType.INCLUDE)
            file_selection.add_pattern(f"*{iteration % 10}*", SelectionType.INCLUDE)

            # Perform operations
            effective_paths = file_selection.get_effective_paths()
            size_stats = file_selection.estimate_backup_size()

            # Validate results
            assert isinstance(effective_paths, dict)
            assert isinstance(size_stats, dict)

            # Force cleanup every 10 iterations
            if iteration % 10 == 0:
                gc.collect()

        # Check for resource leaks
        final_fd_count = len(psutil.Process().open_files())
        fd_increase = final_fd_count - initial_fd_count

        # Should not have significant file descriptor leaks
        assert fd_increase < 10, f"File descriptor count increased by {fd_increase}"

        print(f"Resource cleanup test: FD increase = {fd_increase}")
