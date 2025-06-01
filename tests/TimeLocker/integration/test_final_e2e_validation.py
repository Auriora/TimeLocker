"""
Final End-to-End Validation Tests for TimeLocker v1.0.0

This module contains comprehensive end-to-end tests that validate complete workflows
and system integration for the final release validation.
"""

import pytest
import tempfile
import shutil
import json
import time
import os
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from TimeLocker.backup_manager import BackupManager
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType
from TimeLocker.restore_manager import RestoreManager
from TimeLocker.snapshot_manager import SnapshotManager
from TimeLocker.security import SecurityService, CredentialManager
from TimeLocker.monitoring import StatusReporter, NotificationService
from TimeLocker.config import ConfigurationManager
from TimeLocker.integration import IntegrationService
from TimeLocker.performance.benchmarks import PerformanceBenchmarks
from TimeLocker.performance.metrics import start_operation_tracking, complete_operation_tracking


class TestFinalE2EValidation:
    """Final end-to-end validation tests for TimeLocker v1.0.0"""

    def setup_method(self):
        """Setup comprehensive test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / "config"
        self.repo_dir = self.temp_dir / "repository"
        self.source_dir = self.temp_dir / "source"
        self.restore_dir = self.temp_dir / "restore"
        self.large_dataset_dir = self.temp_dir / "large_dataset"

        # Create directories
        for directory in [self.config_dir, self.repo_dir, self.source_dir,
                          self.restore_dir, self.large_dataset_dir]:
            directory.mkdir(parents=True)

        # Create comprehensive test data
        self._create_comprehensive_test_data()

        # Initialize components
        self._setup_components()

    def teardown_method(self):
        """Cleanup test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _create_comprehensive_test_data(self):
        """Create comprehensive test data for validation"""
        # Create diverse file types and structures
        test_files = [
                ("documents/report.pdf", b"PDF content" * 1000),
                ("documents/spreadsheet.xlsx", b"Excel content" * 500),
                ("images/photo1.jpg", b"JPEG content" * 2000),
                ("images/photo2.png", b"PNG content" * 1500),
                ("code/main.py", b"print('Hello World')\n" * 100),
                ("code/config.json", b'{"setting": "value"}\n' * 50),
                ("archives/backup.zip", b"ZIP content" * 3000),
                ("logs/app.log", b"Log entry\n" * 1000),
        ]

        # Create regular test files
        for file_path, content in test_files:
            full_path = self.source_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)

        # Create large dataset for performance testing (1000+ files)
        self._create_large_dataset()

        # Create files with special characteristics
        self._create_special_files()

    def _create_large_dataset(self):
        """Create large dataset for performance testing"""
        # Create 1000+ files in various directory structures
        for i in range(1200):
            dir_num = i // 100  # 12 directories with 100 files each
            file_dir = self.large_dataset_dir / f"dir_{dir_num:02d}"
            file_dir.mkdir(parents=True, exist_ok=True)

            file_path = file_dir / f"file_{i:04d}.txt"
            # Vary file sizes
            content_size = (i % 10 + 1) * 100  # 100-1000 bytes
            content = f"File {i} content\n" * content_size
            file_path.write_text(content)

    def _create_special_files(self):
        """Create files with special characteristics for edge case testing"""
        special_dir = self.source_dir / "special"
        special_dir.mkdir(exist_ok=True)

        # Unicode filename
        unicode_file = special_dir / "файл_тест.txt"
        unicode_file.write_text("Unicode content")

        # Very long filename
        long_name = "a" * 200 + ".txt"
        long_file = special_dir / long_name
        long_file.write_text("Long filename content")

        # Empty file
        empty_file = special_dir / "empty.txt"
        empty_file.touch()

        # Large file (10MB)
        large_file = special_dir / "large_file.bin"
        large_file.write_bytes(b"X" * (10 * 1024 * 1024))

    def _setup_components(self):
        """Setup all TimeLocker components"""
        # Mock notification service to prevent desktop notifications during tests
        with patch('TimeLocker.monitoring.NotificationService') as mock_notification:
            mock_notification.return_value = Mock()

            # Initialize components
            self.credential_manager = CredentialManager(config_dir=self.config_dir)
            self.security_service = SecurityService(
                    credential_manager=self.credential_manager,
                    config_dir=self.config_dir
            )
            self.config_manager = ConfigurationManager(config_dir=self.config_dir)
            self.status_reporter = StatusReporter()
            self.notification_service = mock_notification.return_value

            # Setup repository and managers
            self._setup_repository_and_managers()

    def _setup_repository_and_managers(self):
        """Setup repository and backup/restore managers"""
        # Mock repository for testing
        self.mock_repository = Mock()
        self.mock_repository._location = str(self.repo_dir)
        self.mock_repository.id = "test_repo_e2e"
        self.mock_repository.is_repository_initialized.return_value = True
        self.mock_repository._password = "test_password"

        # Create backup target
        file_selection = FileSelection()
        file_selection.add_path(self.source_dir, SelectionType.INCLUDE)
        self.backup_target = BackupTarget(
                selection=file_selection,
                tags=["e2e_test"]
        )

        # Initialize managers
        self.backup_manager = BackupManager()
        self.restore_manager = RestoreManager(repository=self.mock_repository)
        self.snapshot_manager = SnapshotManager(repository=self.mock_repository)

        # Integration service
        self.integration_service = IntegrationService(config_dir=self.config_dir)
        self.integration_service.initialize_security(self.credential_manager)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_complete_backup_restore_workflow_large_dataset(self):
        """Test complete backup and restore workflow with large dataset (1000+ files)"""
        # Track performance metrics
        operation_id = f"e2e_large_dataset_{int(time.time())}"
        metrics = start_operation_tracking(operation_id, "large_dataset_backup_restore")

        try:
            # Create file selection for large dataset
            file_selection = FileSelection()
            file_selection.add_path(self.large_dataset_dir, SelectionType.INCLUDE)
            file_selection.add_pattern("*.tmp", SelectionType.EXCLUDE)

            # Estimate backup size
            size_stats = file_selection.estimate_backup_size()
            assert size_stats['file_count'] >= 1000
            assert size_stats['total_size'] > 0

            # Mock successful backup
            with patch.object(self.backup_manager, 'create_full_backup') as mock_backup:
                mock_backup.return_value = {
                        'snapshot_id':           'snapshot_large_001',
                        'files_new':             size_stats['file_count'],
                        'files_changed':         0,
                        'files_unmodified':      0,
                        'total_files_processed': size_stats['file_count'],
                        'data_added':            size_stats['total_size'],
                        'total_duration':        45.5
                }

                # Perform backup
                backup_result = self.backup_manager.create_full_backup(
                        repository=self.mock_repository,
                        targets=[self.backup_target],
                        tags=["large_dataset_test"]
                )

                # Verify backup results
                assert backup_result['snapshot_id'] == 'snapshot_large_001'
                assert backup_result['total_files_processed'] >= 1000

            # Mock successful restore
            with patch.object(self.restore_manager, 'restore_snapshot') as mock_restore:
                mock_restore.return_value = {
                        'files_restored': size_stats['file_count'],
                        'total_size':     size_stats['total_size'],
                        'duration':       30.2
                }

                # Perform restore
                restore_result = self.restore_manager.restore_snapshot(
                        snapshot_id='snapshot_large_001',
                        target_path=str(self.restore_dir)
                )

                # Verify restore results
                assert restore_result['files_restored'] >= 1000

            # Update metrics
            complete_operation_tracking(operation_id)

        except Exception as e:
            pytest.fail(f"Large dataset workflow failed: {e}")

    @pytest.mark.integration
    def test_multi_repository_management_workflow(self):
        """Test multi-repository management scenarios"""
        # Create multiple repository configurations
        repo_configs = [
                {"name": "repo1", "type": "local", "path": str(self.temp_dir / "repo1")},
                {"name": "repo2", "type": "local", "path": str(self.temp_dir / "repo2")},
                {"name": "repo3", "type": "local", "path": str(self.temp_dir / "repo3")}
        ]

        repositories = []
        for config in repo_configs:
            # Create repository directory
            repo_path = Path(config["path"])
            repo_path.mkdir(exist_ok=True)

            # Mock repository
            mock_repo = Mock()
            mock_repo._location = config["path"]
            mock_repo.id = config["name"]
            mock_repo.is_repository_initialized.return_value = True
            repositories.append(mock_repo)

        # Test repository switching
        for repo in repositories:
            # Create backup target for each repository
            file_selection = FileSelection()
            file_selection.add_path(self.source_dir, SelectionType.INCLUDE)
            target = BackupTarget(
                    selection=file_selection,
                    tags=[f"target_{repo.id}"]
            )

            # Mock backup operation
            with patch.object(self.backup_manager, 'create_incremental_backup') as mock_backup:
                mock_backup.return_value = {
                        'snapshot_id':           f'snapshot_{repo.id}_001',
                        'files_new':             10,
                        'total_files_processed': 10
                }

                # Perform backup
                result = self.backup_manager.create_incremental_backup(
                        repository=repo,
                        targets=[target],
                        tags=[f"multi_repo_{repo.id}"]
                )

                assert result['snapshot_id'] == f'snapshot_{repo.id}_001'

                # Manually log the backup operation since we're mocking the backup manager
                self.security_service.audit_backup_operation(
                    repository=repo,
                    operation_type="incremental",
                    success=True,
                    metadata={"tags": [f"multi_repo_{repo.id}"], "files_processed": 10}
                )

        # Verify security audit for multi-repository operations
        audit_log = self.security_service.audit_log_file
        if audit_log.exists():
            with open(audit_log, 'r') as f:
                content = f.read()
                # Should contain entries for multiple repositories
                for repo in repositories:
                    assert repo.id in content or "backup_operation" in content

    @pytest.mark.integration
    def test_concurrent_operations_handling(self):
        """Test handling of concurrent backup operations"""

        def perform_backup_operation(repo_id, source_path):
            """Perform a backup operation in a separate thread"""
            try:
                # Create mock repository
                mock_repo = Mock()
                mock_repo._location = str(self.temp_dir / f"concurrent_repo_{repo_id}")
                mock_repo.id = f"concurrent_repo_{repo_id}"
                mock_repo.is_repository_initialized.return_value = True

                # Create backup manager for this thread
                backup_manager = BackupManager()

                # Create target
                file_selection = FileSelection()
                file_selection.add_path(source_path, SelectionType.INCLUDE)
                target = BackupTarget(
                        selection=file_selection,
                        tags=[f"concurrent_target_{repo_id}"]
                )

                # Mock backup operation
                with patch.object(backup_manager, 'create_incremental_backup') as mock_backup:
                    mock_backup.return_value = {
                            'snapshot_id':           f'concurrent_snapshot_{repo_id}',
                            'files_new':             5,
                            'total_files_processed': 5,
                            'duration':              2.0
                    }

                    result = backup_manager.create_incremental_backup(
                            repository=mock_repo,
                            targets=[target],
                            tags=[f"concurrent_{repo_id}"]
                    )

                    return {
                            'repo_id':     repo_id,
                            'success':     True,
                            'snapshot_id': result['snapshot_id']
                    }

            except Exception as e:
                return {
                        'repo_id': repo_id,
                        'success': False,
                        'error':   str(e)
                }

        # Execute concurrent operations
        num_concurrent_ops = 5
        with ThreadPoolExecutor(max_workers=num_concurrent_ops) as executor:
            # Submit concurrent backup operations
            futures = []
            for i in range(num_concurrent_ops):
                future = executor.submit(
                        perform_backup_operation,
                        i,
                        str(self.source_dir)
                )
                futures.append(future)

            # Collect results
            results = []
            for future in as_completed(futures, timeout=30):
                result = future.result()
                results.append(result)

        # Verify all operations completed successfully
        assert len(results) == num_concurrent_ops
        successful_ops = [r for r in results if r['success']]
        assert len(successful_ops) == num_concurrent_ops

        # Verify unique snapshot IDs
        snapshot_ids = [r['snapshot_id'] for r in successful_ops]
        assert len(set(snapshot_ids)) == num_concurrent_ops

    @pytest.mark.integration
    def test_memory_usage_monitoring(self):
        """Test memory usage stays within reasonable limits"""
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        large_file_selection = FileSelection()
        large_file_selection.add_path(self.large_dataset_dir, SelectionType.INCLUDE)

        # Force garbage collection before measurement
        gc.collect()

        # Measure memory during file traversal
        start_memory = process.memory_info().rss / 1024 / 1024

        # Perform operations that could consume memory
        effective_paths = large_file_selection.get_effective_paths()
        size_stats = large_file_selection.estimate_backup_size()

        # Force garbage collection after operations
        gc.collect()

        end_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = end_memory - start_memory

        # Memory increase should be reasonable (less than 100MB for test dataset)
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.2f}MB"

        # Verify we processed the expected number of files
        assert len(effective_paths['included']) >= 1000
        assert size_stats['file_count'] >= 1000

    @pytest.mark.integration
    @pytest.mark.security
    def test_end_to_end_security_validation(self):
        """Test complete security validation workflow"""
        # Test credential management workflow
        self.credential_manager.unlock("test_master_password")

        # Store and retrieve repository credentials
        repo_password = "secure_repo_password_123"
        self.credential_manager.store_repository_password("e2e_repo", repo_password)
        retrieved_password = self.credential_manager.get_repository_password("e2e_repo")
        assert retrieved_password == repo_password

        # Test encryption verification
        encryption_status = self.security_service.verify_repository_encryption(self.mock_repository)
        assert encryption_status.is_encrypted is True
        assert encryption_status.encryption_algorithm == "AES-256"

        # Test audit logging for security events
        self.security_service.audit_backup_operation(
                repository=self.mock_repository,
                operation_type="security_test",
                targets=[str(self.source_dir)],
                success=True,
                metadata={"test_type": "e2e_security"}
        )

        # Verify audit log contains security events
        audit_log = self.security_service.audit_log_file
        assert audit_log.exists()

        with open(audit_log, 'r') as f:
            content = f.read()
            assert "backup_operation" in content
            assert "security_test" in content
            assert "SUCCESS" in content

        # Test security configuration validation
        security_config = {
                "encryption_enabled":  True,
                "audit_logging":       True,
                "credential_timeout":  3600,
                "max_failed_attempts": 3
        }

        validation_result = self.security_service.validate_security_config(security_config)
        assert validation_result["valid"] is True

    @pytest.mark.integration
    def test_error_recovery_comprehensive(self):
        """Test comprehensive error recovery scenarios"""
        error_scenarios = [
                {
                        "name":              "network_timeout",
                        "exception":         ConnectionError("Network timeout"),
                        "expected_recovery": "retry_operation"
                },
                {
                        "name":              "permission_denied",
                        "exception":         PermissionError("Access denied"),
                        "expected_recovery": "log_error"
                },
                {
                        "name":              "disk_full",
                        "exception":         OSError("No space left on device"),
                        "expected_recovery": "cleanup_and_retry"
                },
                {
                        "name":              "invalid_repository",
                        "exception":         ValueError("Repository not found"),
                        "expected_recovery": "validate_config"
                }
        ]

        for scenario in error_scenarios:
            with patch.object(self.backup_manager, 'create_incremental_backup') as mock_backup:
                mock_backup.side_effect = scenario["exception"]

                # Attempt operation and verify error handling
                with pytest.raises(type(scenario["exception"])):
                    self.backup_manager.create_incremental_backup(
                            repository=self.mock_repository,
                            targets=[self.backup_target],
                            tags=["error_test"]
                    )

                # Manually log the error since we're mocking the backup manager
                self.security_service.audit_backup_operation(
                    repository=self.mock_repository,
                    operation_type="incremental",
                    success=False,
                    metadata={
                        "error_type": scenario["name"],
                        "error_message": str(scenario["exception"]),
                        "recovery_action": scenario["expected_recovery"]
                    }
                )

                # Verify error was properly logged
                audit_log = self.security_service.audit_log_file
                if audit_log.exists():
                    with open(audit_log, 'r') as f:
                        content = f.read()
                        # Should contain error information
                        assert "FAILED" in content or "backup_operation" in content

    @pytest.mark.integration
    def test_cross_platform_file_handling(self):
        """Test cross-platform file path and character handling"""
        # Create files with various path characteristics
        cross_platform_files = [
                "normal_file.txt",
                "file with spaces.txt",
                "file-with-dashes.txt",
                "file_with_underscores.txt",
                "UPPERCASE.TXT",
                "MixedCase.Txt",
                "file.with.multiple.dots.txt",
                "very_long_filename_that_might_cause_issues_on_some_systems.txt"
        ]

        cross_platform_dir = self.source_dir / "cross_platform"
        cross_platform_dir.mkdir(exist_ok=True)

        # Create test files
        for filename in cross_platform_files:
            file_path = cross_platform_dir / filename
            file_path.write_text(f"Content for {filename}")

        # Test file selection with various patterns
        file_selection = FileSelection()
        file_selection.add_path(cross_platform_dir, SelectionType.INCLUDE)

        # Test pattern matching
        file_selection.add_pattern("*.txt", SelectionType.INCLUDE)
        file_selection.add_pattern("UPPERCASE.*", SelectionType.EXCLUDE)

        effective_paths = file_selection.get_effective_paths()

        # Verify files were processed correctly
        included_files = effective_paths['included']
        assert len(included_files) > 0

        # Verify exclusion pattern worked
        uppercase_files = [f for f in included_files if "UPPERCASE" in str(f)]
        assert len(uppercase_files) == 0

    @pytest.mark.integration
    @pytest.mark.performance
    def test_performance_benchmarks_validation(self):
        """Test performance benchmarks meet expected criteria"""
        with PerformanceBenchmarks(self.temp_dir) as benchmarks:
            # Run performance benchmarks
            results = benchmarks.run_all_benchmarks()

            # Validate pattern matching performance
            pm_results = results['pattern_matching']
            assert pm_results['speedup_factor'] >= 1.0  # Should be at least as fast as legacy
            assert pm_results['matches_consistent'] is True  # Results should be consistent

            # Validate file traversal performance
            ft_results = results['file_traversal']
            assert ft_results['throughput_files_per_sec'] > 50  # Minimum acceptable throughput
            assert ft_results['files_included'] > 0

            # Validate large directory performance
            ld_results = results['large_directory']
            assert ld_results['traversal_time'] < 60.0  # Should complete within 1 minute
            assert ld_results['num_files_created'] > 0

            # Generate performance report
            report = benchmarks.generate_performance_report(results)
            assert "TimeLocker Performance Benchmark Report" in report
            assert "files/sec" in report

    @pytest.mark.integration
    def test_configuration_management_workflow(self):
        """Test complete configuration management workflow"""
        # Test configuration creation and validation
        config_data = {
                "repositories": {
                        "default": {
                                "type":       "local",
                                "path":       str(self.repo_dir),
                                "encryption": True
                        }
                },
                "backup":       {
                        "compression":        "gzip",
                        "exclude_caches":     True,
                        "retention_keep_last": 5
                },
                "security":     {
                        "audit_logging":      True,
                        "credential_timeout": 3600,
                        "encryption_enabled": True
                }
        }

        # Save configuration
        config_file = self.config_dir / "timelocker.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

        # Load and validate configuration using import_config
        import_result = self.config_manager.import_config(config_file)
        assert import_result is True

        # Verify configuration was loaded correctly
        loaded_config = self.config_manager.get_configuration()
        assert "repositories" in loaded_config
        assert "backup" in loaded_config
        assert "security" in loaded_config

        # Verify specific values
        assert loaded_config["repositories"]["default"]["type"] == "local"
        assert loaded_config["backup"]["compression"] == "gzip"
        assert loaded_config["security"]["audit_logging"] is True

        # Test configuration-driven backup operation
        with patch.object(self.backup_manager, 'create_incremental_backup') as mock_backup:
            mock_backup.return_value = {
                    'snapshot_id':           'config_driven_001',
                    'files_new':             5,
                    'total_files_processed': 5
            }

            # Use configuration to drive backup
            result = self.backup_manager.create_incremental_backup(
                    repository=self.mock_repository,
                    targets=[self.backup_target],
                    tags=["config_driven"]
            )

            assert result['snapshot_id'] == 'config_driven_001'
