"""
Cross-Platform Validation Tests for TimeLocker v1.0.0

This module contains tests to validate TimeLocker functionality across different
platforms and Python versions.
"""

import pytest
import tempfile
import shutil
import os
import sys
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.monitoring import NotificationService
from TimeLocker.config import ConfigurationManager


class TestCrossPlatformValidation:
    """Cross-platform validation tests for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup cross-platform test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_files_dir = self.temp_dir / "test_files"
        self.test_files_dir.mkdir(parents=True)

        # Platform information
        self.platform_info = {
                'system':              platform.system(),
                'release':             platform.release(),
                'version':             platform.version(),
                'machine':             platform.machine(),
                'processor':           platform.processor(),
                'python_version':      sys.version,
                'python_version_info': sys.version_info
        }

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_platform_specific_files(self):
        """Create files with platform-specific characteristics"""
        test_files = []

        # Common files that should work on all platforms
        common_files = [
                "simple.txt",
                "document.pdf",
                "image.jpg",
                "data.json",
                "script.py"
        ]

        for filename in common_files:
            file_path = self.test_files_dir / filename
            file_path.write_text(f"Content for {filename}")
            test_files.append(file_path)

        # Platform-specific file characteristics
        if self.platform_info['system'] == 'Windows':
            # Windows-specific files
            windows_files = [
                    "file with spaces.txt",
                    "UPPERCASE.TXT",
                    "file.with.dots.txt",
                    "very_long_filename_that_tests_windows_path_limits.txt"
            ]
            for filename in windows_files:
                file_path = self.test_files_dir / filename
                file_path.write_text(f"Windows content for {filename}")
                test_files.append(file_path)

        elif self.platform_info['system'] in ['Linux', 'Darwin']:
            # Unix-like system files
            unix_files = [
                    "file with spaces.txt",
                    "file-with-dashes.txt",
                    "file_with_underscores.txt",
                    ".hidden_file.txt",
                    "executable_file.sh"
            ]
            for filename in unix_files:
                file_path = self.test_files_dir / filename
                file_path.write_text(f"Unix content for {filename}")
                test_files.append(file_path)

                # Make shell script executable on Unix systems
                if filename.endswith('.sh'):
                    file_path.chmod(0o755)

        # Unicode filenames (should work on modern systems)
        try:
            unicode_files = [
                    "файл.txt",  # Cyrillic
                    "文件.txt",  # Chinese
                    "ファイル.txt",  # Japanese
                    "café.txt"  # Accented characters
            ]
            for filename in unicode_files:
                file_path = self.test_files_dir / filename
                file_path.write_text(f"Unicode content for {filename}")
                test_files.append(file_path)
        except (UnicodeError, OSError):
            # Skip unicode files if not supported on this platform
            pass

        return test_files

    @pytest.mark.integration
    def test_python_version_compatibility(self):
        """Test compatibility with supported Python versions"""
        # Verify we're running on a supported Python version
        min_version = (3, 12)
        max_version = (3, 13)

        current_version = sys.version_info[:2]

        assert current_version >= min_version, \
            f"Python {current_version} below minimum supported version {min_version}"

        assert current_version <= max_version, \
            f"Python {current_version} above maximum tested version {max_version}"

        # Test Python version-specific features
        if current_version >= (3, 12):
            # Test features available in Python 3.12+
            from pathlib import Path
            assert hasattr(Path, 'walk'), "Path.walk() should be available in Python 3.12+"

    @pytest.mark.integration
    def test_file_path_handling_cross_platform(self):
        """Test file path handling across platforms"""
        # Create platform-specific test files
        test_files = self._create_platform_specific_files()
        assert len(test_files) > 0

        # Test file selection with various path patterns
        file_selection = FileSelection()
        file_selection.add_path(self.test_files_dir, SelectionType.INCLUDE)

        # Test pattern matching across platforms
        patterns_to_test = [
                "*.txt",
                "*.pdf",
                "*.jpg",
                "*with*",
                "file*",
                "*.py"
        ]

        for pattern in patterns_to_test:
            file_selection.add_pattern(pattern, SelectionType.INCLUDE)

        # Get effective paths
        effective_paths = file_selection.get_effective_paths()
        included_files = effective_paths['included']

        # Verify files were found
        assert len(included_files) > 0, "No files found with cross-platform patterns"

        # Verify path handling
        for file_path in included_files:
            # Path should be absolute
            assert Path(file_path).is_absolute(), f"Path {file_path} is not absolute"

            # File should exist
            assert Path(file_path).exists(), f"File {file_path} does not exist"

    @pytest.mark.integration
    def test_notification_system_cross_platform(self):
        """Test notification system across platforms"""
        # Mock notification service to prevent actual notifications during tests
        with patch('TimeLocker.monitoring.NotificationService') as mock_notification_class:
            mock_notification = Mock()
            mock_notification_class.return_value = mock_notification

            notification_service = NotificationService()

            # Test different notification types
            notification_types = [
                    ("info", "Test info notification"),
                    ("warning", "Test warning notification"),
                    ("error", "Test error notification"),
                    ("success", "Test success notification")
            ]

            for notification_type, message in notification_types:
                # This should not raise an exception on any platform
                try:
                    if hasattr(notification_service, f'notify_{notification_type}'):
                        getattr(notification_service, f'notify_{notification_type}')(message)
                    else:
                        notification_service.notify(message, notification_type)
                except Exception as e:
                    pytest.fail(f"Notification failed on {self.platform_info['system']}: {e}")

    @pytest.mark.integration
    def test_configuration_file_handling_cross_platform(self):
        """Test configuration file handling across platforms"""
        config_manager = ConfigurationManager(config_dir=self.temp_dir)

        # Test configuration with platform-specific paths
        if self.platform_info['system'] == 'Windows':
            test_paths = [
                    "C:\\Users\\test\\Documents",
                    "D:\\Backup\\Data",
                    "\\\\server\\share\\folder"
            ]
        else:
            test_paths = [
                    "/home/test/documents",
                    "/var/backup/data",
                    "/mnt/external/backup"
            ]

        config_data = {
                "repositories":   {
                        "local": {
                                "type": "local",
                                "path": str(self.temp_dir / "repo")
                        }
                },
                "backup_targets": {
                        "test_target": {
                                "paths":    test_paths,
                                "patterns": {
                                        "include": ["*.txt", "*.pdf"],
                                        "exclude": ["*.tmp", "*.log"]
                                }
                        }
                }
        }

        # Save configuration
        config_file = self.temp_dir / "test_config.json"
        config_manager.save_configuration(config_data, str(config_file))

        # Verify file was created
        assert config_file.exists()

        # Load configuration
        loaded_config = config_manager.load_configuration(str(config_file))

        # Verify configuration was loaded correctly
        assert "repositories" in loaded_config
        assert "backup_targets" in loaded_config
        assert loaded_config["backup_targets"]["test_target"]["paths"] == test_paths

    @pytest.mark.integration
    def test_file_permissions_cross_platform(self):
        """Test file permission handling across platforms"""
        # Create test files with different permissions
        test_file = self.test_files_dir / "permission_test.txt"
        test_file.write_text("Permission test content")

        if self.platform_info['system'] != 'Windows':
            # Unix-like systems support detailed permissions

            # Test readable file
            test_file.chmod(0o644)  # rw-r--r--
            assert test_file.is_file()
            assert os.access(test_file, os.R_OK)

            # Test executable file
            executable_file = self.test_files_dir / "executable_test.sh"
            executable_file.write_text("#!/bin/bash\necho 'test'")
            executable_file.chmod(0o755)  # rwxr-xr-x
            assert os.access(executable_file, os.X_OK)

            # Test file selection with permission considerations
            file_selection = FileSelection()
            file_selection.add_path(self.test_files_dir, SelectionType.INCLUDE)

            effective_paths = file_selection.get_effective_paths()
            included_files = effective_paths['included']

            # Both files should be included
            file_paths = [str(f) for f in included_files]
            assert str(test_file) in file_paths
            assert str(executable_file) in file_paths

        else:
            # Windows has different permission model
            # Just verify basic file access
            assert test_file.is_file()
            assert os.access(test_file, os.R_OK)

    @pytest.mark.integration
    def test_large_path_handling_cross_platform(self):
        """Test handling of long file paths across platforms"""
        # Create nested directory structure
        base_dir = self.test_files_dir / "long_path_test"
        base_dir.mkdir()

        # Create progressively deeper directory structure
        current_dir = base_dir
        path_components = []

        # Build a long path (but within reasonable limits)
        for i in range(10):
            dir_name = f"very_long_directory_name_level_{i:02d}_with_descriptive_text"
            path_components.append(dir_name)
            current_dir = current_dir / dir_name
            current_dir.mkdir()

        # Create a file in the deep directory
        deep_file = current_dir / "deep_file.txt"
        deep_file.write_text("Content in deeply nested file")

        # Test file selection with deep paths
        file_selection = FileSelection()
        file_selection.add_path(base_dir, SelectionType.INCLUDE)

        effective_paths = file_selection.get_effective_paths()
        included_files = effective_paths['included']

        # Verify deep file was found
        deep_file_found = any(str(deep_file) in str(f) for f in included_files)
        assert deep_file_found, "Deep file not found in file selection"

    @pytest.mark.integration
    def test_special_characters_in_paths_cross_platform(self):
        """Test handling of special characters in file paths"""
        # Characters that might cause issues on different platforms
        if self.platform_info['system'] == 'Windows':
            # Windows has more restrictions on filename characters
            special_chars = [' ', '-', '_', '.', '(', ')', '[', ']']
        else:
            # Unix-like systems are more permissive
            special_chars = [' ', '-', '_', '.', '(', ')', '[', ']', '&', '$', '@']

        special_files = []
        for i, char in enumerate(special_chars):
            try:
                filename = f"file{char}with{char}special{char}chars_{i}.txt"
                file_path = self.test_files_dir / filename
                file_path.write_text(f"Content with special character: {char}")
                special_files.append(file_path)
            except (OSError, ValueError):
                # Skip characters that aren't supported on this platform
                continue

        # Test file selection with special character files
        if special_files:
            file_selection = FileSelection()
            file_selection.add_path(self.test_files_dir, SelectionType.INCLUDE)
            file_selection.add_pattern("*special*", SelectionType.INCLUDE)

            effective_paths = file_selection.get_effective_paths()
            included_files = effective_paths['included']

            # Verify at least some special character files were found
            special_files_found = sum(1 for f in included_files
                                      if "special" in str(f))
            assert special_files_found > 0, "No special character files found"

    @pytest.mark.integration
    def test_platform_specific_optimizations(self):
        """Test platform-specific optimizations and features"""
        # Test file system performance characteristics
        file_selection = FileSelection()
        file_selection.add_path(self.test_files_dir, SelectionType.INCLUDE)

        # Create some test files for performance testing
        for i in range(100):
            test_file = self.test_files_dir / f"perf_test_{i:03d}.txt"
            test_file.write_text(f"Performance test file {i}")

        # Measure file traversal performance
        import time
        start_time = time.perf_counter()
        effective_paths = file_selection.get_effective_paths()
        traversal_time = time.perf_counter() - start_time

        # Performance should be reasonable on all platforms
        assert traversal_time < 10.0, f"File traversal took {traversal_time:.2f}s, too slow"
        assert len(effective_paths['included']) >= 100

        # Platform-specific performance expectations
        if self.platform_info['system'] == 'Windows':
            # Windows might be slower due to antivirus scanning
            max_expected_time = 5.0
        else:
            # Unix-like systems typically faster for file operations
            max_expected_time = 2.0

        if traversal_time > max_expected_time:
            # Log warning but don't fail (performance can vary)
            print(f"Warning: File traversal on {self.platform_info['system']} "
                  f"took {traversal_time:.2f}s, expected < {max_expected_time}s")

    @pytest.mark.integration
    def test_environment_variable_handling_cross_platform(self):
        """Test environment variable handling across platforms"""
        # Test common environment variables
        if self.platform_info['system'] == 'Windows':
            common_env_vars = ['USERPROFILE', 'APPDATA', 'TEMP', 'PATH']
        else:
            common_env_vars = ['HOME', 'USER', 'TMPDIR', 'PATH']

        # Verify environment variables are accessible
        for env_var in common_env_vars:
            value = os.environ.get(env_var)
            if value is not None:
                # Environment variable should be a valid path or value
                assert isinstance(value, str)
                assert len(value) > 0

        # Test path expansion with environment variables
        if self.platform_info['system'] == 'Windows':
            test_path = "%USERPROFILE%\\Documents"
            expanded = os.path.expandvars(test_path)
            assert expanded != test_path  # Should be expanded
            assert "Documents" in expanded
        else:
            test_path = "$HOME/Documents"
            expanded = os.path.expandvars(test_path)
            assert expanded != test_path  # Should be expanded
            assert "Documents" in expanded
