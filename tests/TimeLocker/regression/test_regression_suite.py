"""
Regression Testing Suite for TimeLocker v1.0.0

This module contains regression tests to ensure that previously fixed bugs
and issues do not reoccur in future releases.
"""

import pytest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.security import CredentialManager, SecurityService


class TestRegressionSuite:
    """Regression testing suite for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup regression test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_data_dir = self.temp_dir / "test_data"
        self.test_data_dir.mkdir(parents=True)

    def teardown_method(self):
        """Cleanup regression test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.regression
    def test_unicode_filename_handling_regression(self):
        """
        Regression test for unicode filename handling
        
        Previously, unicode filenames could cause encoding errors
        during file traversal and pattern matching.
        """
        # Create files with various unicode characters
        unicode_files = [
                "файл.txt",  # Cyrillic
                "文件.txt",  # Chinese
                "ファイル.txt",  # Japanese
                "café.txt",  # Accented characters
                "naïve.txt",  # More accented characters
                "résumé.txt",  # French accents
                "niño.txt",  # Spanish characters
                "🎉emoji.txt"  # Emoji (if supported)
        ]

        created_files = []
        for filename in unicode_files:
            try:
                file_path = self.test_data_dir / filename
                file_path.write_text(f"Content for {filename}", encoding='utf-8')
                created_files.append(file_path)
            except (UnicodeError, OSError):
                # Skip files that can't be created on this platform
                continue

        if not created_files:
            pytest.skip("No unicode files could be created on this platform")

        # Test file selection with unicode files
        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)

        # This should not raise encoding errors
        effective_paths = file_selection.get_effective_paths()
        size_stats = file_selection.estimate_backup_size()

        # Validate results
        assert len(effective_paths['included']) >= len(created_files)
        assert size_stats['file_count'] >= len(created_files)

    @pytest.mark.regression
    def test_empty_directory_handling_regression(self):
        """
        Regression test for empty directory handling
        
        Previously, empty directories could cause issues during
        file traversal and size estimation.
        """
        # Create nested empty directories
        empty_dirs = [
                self.test_data_dir / "empty1",
                self.test_data_dir / "empty2" / "nested_empty",
                self.test_data_dir / "empty3" / "deeply" / "nested" / "empty"
        ]

        for empty_dir in empty_dirs:
            empty_dir.mkdir(parents=True, exist_ok=True)

        # Create one file to ensure we have something to find
        test_file = self.test_data_dir / "test.txt"
        test_file.write_text("Test content")

        # Test file selection with empty directories
        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)

        # This should handle empty directories gracefully
        effective_paths = file_selection.get_effective_paths()
        size_stats = file_selection.estimate_backup_size()

        # Should find the test file
        assert len(effective_paths['included']) >= 1
        assert size_stats['file_count'] >= 1

    @pytest.mark.regression
    def test_large_pattern_list_regression(self):
        """
        Regression test for large pattern lists
        
        Previously, having many patterns could cause performance
        issues or memory problems.
        """
        # Create test files
        for i in range(100):
            test_file = self.test_data_dir / f"test_{i:03d}.txt"
            test_file.write_text(f"Test file {i}")

        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)

        # Add many patterns (this used to cause issues)
        for i in range(200):
            pattern = f"*{i:03d}*"
            file_selection.add_pattern(pattern, SelectionType.INCLUDE)

        # This should complete without performance issues
        start_time = time.perf_counter()
        effective_paths = file_selection.get_effective_paths()
        duration = time.perf_counter() - start_time

        # Should complete in reasonable time
        assert duration < 10.0, f"Pattern matching took {duration:.2f}s, too slow"
        assert len(effective_paths['included']) > 0

    @pytest.mark.regression
    def test_special_character_paths_regression(self):
        """
        Regression test for special characters in paths
        
        Previously, paths with special characters could cause
        issues with pattern matching and file operations.
        """
        # Create directories and files with special characters
        special_chars_data = [
                ("spaces in name", "file with spaces.txt"),
                ("dots.in.name", "file.with.dots.txt"),
                ("dashes-in-name", "file-with-dashes.txt"),
                ("underscores_in_name", "file_with_underscores.txt"),
                ("parentheses(in)name", "file(with)parentheses.txt"),
                ("brackets[in]name", "file[with]brackets.txt")
        ]

        created_paths = []
        for dir_name, file_name in special_chars_data:
            try:
                dir_path = self.test_data_dir / dir_name
                dir_path.mkdir(exist_ok=True)

                file_path = dir_path / file_name
                file_path.write_text(f"Content for {file_name}")
                created_paths.append(file_path)
            except OSError:
                # Skip paths that can't be created on this platform
                continue

        if not created_paths:
            pytest.skip("No special character paths could be created")

        # Test file selection with special character paths
        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)

        # This should handle special characters correctly
        effective_paths = file_selection.get_effective_paths()
        size_stats = file_selection.estimate_backup_size()

        # Should find the created files
        assert len(effective_paths['included']) >= len(created_paths)
        assert size_stats['file_count'] >= len(created_paths)

    @pytest.mark.regression
    def test_concurrent_access_regression(self):
        """
        Regression test for concurrent access issues
        
        Previously, concurrent access to file selection objects
        could cause race conditions or inconsistent results.
        """
        import threading

        # Create test files
        for i in range(50):
            test_file = self.test_data_dir / f"concurrent_{i:02d}.txt"
            test_file.write_text(f"Concurrent test file {i}")

        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)

        results = []
        errors = []

        def concurrent_operation(thread_id):
            """Perform file selection operations concurrently"""
            try:
                for _ in range(10):
                    effective_paths = file_selection.get_effective_paths()
                    size_stats = file_selection.estimate_backup_size()

                    # Validate results are consistent
                    assert len(effective_paths['included']) == 50
                    assert size_stats['file_count'] == 50

                results.append(f"Thread {thread_id} completed successfully")
            except Exception as e:
                errors.append(f"Thread {thread_id} failed: {e}")

        # Run concurrent operations
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)

        # Validate no errors occurred
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 5, f"Not all threads completed: {results}"

    @pytest.mark.regression
    def test_memory_leak_regression(self):
        """
        Regression test for memory leaks
        
        Previously, repeated operations could cause memory leaks
        due to improper cleanup of internal data structures.
        """
        import gc
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create test data
        for i in range(100):
            test_file = self.test_data_dir / f"memory_test_{i:03d}.txt"
            test_file.write_text(f"Memory test file {i}" * 100)

        # Perform many operations that could leak memory
        for iteration in range(50):
            file_selection = FileSelection()
            file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)

            # Add patterns
            for i in range(10):
                file_selection.add_pattern(f"*{i}*", SelectionType.INCLUDE)

            # Perform operations
            effective_paths = file_selection.get_effective_paths()
            size_stats = file_selection.estimate_backup_size()

            # Validate results
            assert len(effective_paths['included']) > 0
            assert size_stats['file_count'] > 0

            # Force garbage collection every 10 iterations
            if iteration % 10 == 0:
                gc.collect()

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, possible leak"

    @pytest.mark.regression
    def test_pattern_edge_cases_regression(self):
        """
        Regression test for pattern matching edge cases
        
        Previously, certain pattern combinations could cause
        incorrect matching or performance issues.
        """
        # Create files for edge case testing
        edge_case_files = [
                "file.txt",
                "file.txt.bak",
                "file.backup.txt",
                ".hidden.txt",
                "..double.dot.txt",
                "file..double.extension.txt",
                "file.TXT",  # Different case
                "FILE.txt",  # Different case
                "file",  # No extension
                "file.",  # Trailing dot
                ".file",  # Leading dot only
        ]

        for filename in edge_case_files:
            try:
                file_path = self.test_data_dir / filename
                file_path.write_text(f"Content for {filename}")
            except OSError:
                # Skip files that can't be created
                continue

        # Test various edge case patterns
        edge_case_patterns = [
                ("*.txt", "Should match .txt files"),
                ("*.*", "Should match files with extensions"),
                (".*", "Should match hidden files"),
                ("file*", "Should match files starting with 'file'"),
                ("*file*", "Should match files containing 'file'"),
                ("*.TXT", "Should match .TXT files (case sensitive)"),
                ("*.", "Should match files ending with dot"),
                ("file", "Should match exact filename"),
                ("", "Empty pattern should match nothing"),
                ("*", "Wildcard should match all")
        ]

        for pattern, description in edge_case_patterns:
            file_selection = FileSelection()
            file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)

            if pattern:  # Skip empty pattern
                file_selection.add_pattern(pattern, SelectionType.INCLUDE)

            # This should not raise exceptions
            try:
                effective_paths = file_selection.get_effective_paths()
                size_stats = file_selection.estimate_backup_size()

                # Results should be consistent
                assert isinstance(effective_paths, dict)
                assert isinstance(size_stats, dict)
                assert len(effective_paths['included']) == size_stats['file_count']

            except Exception as e:
                pytest.fail(f"Pattern '{pattern}' ({description}) caused error: {e}")

    @pytest.mark.regression
    def test_security_service_initialization_regression(self):
        """
        Regression test for security service initialization
        
        Previously, security service initialization could fail
        under certain conditions or with specific configurations.
        """
        config_dir = self.temp_dir / "security_config"

        # Test initialization with non-existent directory
        credential_manager = CredentialManager(config_dir=config_dir)
        security_service = SecurityService(
                credential_manager=credential_manager,
                config_dir=config_dir
        )

        # Should create necessary directories and files
        assert config_dir.exists()
        assert security_service.audit_log_file.exists()

        # Test multiple initializations (should not conflict)
        security_service2 = SecurityService(
                credential_manager=credential_manager,
                config_dir=config_dir
        )

        # Both should work correctly
        assert security_service2.audit_log_file.exists()

    @pytest.mark.regression
    def test_backup_target_validation_regression(self):
        """
        Regression test for backup target validation
        
        Previously, backup target validation could accept
        invalid configurations or fail on valid ones.
        """
        # Test with valid file selection
        file_selection = FileSelection()
        file_selection.add_path(self.test_data_dir, SelectionType.INCLUDE)

        backup_target = BackupTarget(
                selection=file_selection,
                tags=["regression_test"]
        )

        # Should validate successfully
        assert backup_target.validate() is True

        # Test with empty file selection (should still be valid)
        empty_selection = FileSelection()
        empty_target = BackupTarget(
                selection=empty_selection,
                tags=["empty_test"]
        )

        # Should handle empty selection gracefully
        assert empty_target.validate() is True

    @pytest.mark.regression
    def test_configuration_persistence_regression(self):
        """
        Regression test for configuration persistence
        
        Previously, configuration could be lost or corrupted
        during save/load operations.
        """
        from TimeLocker.config import ConfigurationManager

        config_manager = ConfigurationManager(config_dir=self.temp_dir)

        # Create test configuration
        test_config = {
                "repositories":   {
                        "test_repo": {
                                "type":       "local",
                                "path":       str(self.temp_dir / "repo"),
                                "encryption": True
                        }
                },
                "backup_targets": {
                        "test_target": {
                                "paths":    [str(self.test_data_dir)],
                                "patterns": {
                                        "include": ["*.txt", "*.log"],
                                        "exclude": ["*.tmp", "*.bak"]
                                }
                        }
                },
                "settings":       {
                        "default_repository": "test_repo",
                        "notification_level": "normal"
                }
        }

        # Save configuration
        config_file = self.temp_dir / "test_config.json"
        config_manager.save_configuration(test_config, str(config_file))

        # Load configuration
        loaded_config = config_manager.load_configuration(str(config_file))

        # Should be identical
        assert loaded_config == test_config

        # Test with unicode content
        unicode_config = {
                "test": {
                        "unicode_string": "Test with unicode: café, naïve, résumé",
                        "unicode_path":   str(self.test_data_dir / "файл.txt")
                }
        }

        unicode_file = self.temp_dir / "unicode_config.json"
        config_manager.save_configuration(unicode_config, str(unicode_file))
        loaded_unicode = config_manager.load_configuration(str(unicode_file))

        assert loaded_unicode == unicode_config
