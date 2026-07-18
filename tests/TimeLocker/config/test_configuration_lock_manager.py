"""
Unit tests for ConfigurationLockManager.

Tests concurrent access scenarios, lock timeout handling, stale lock cleanup,
and cross-platform locking mechanisms.
"""

import os
import time
import tempfile
import threading
import multiprocessing
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest

from TimeLocker.config.configuration_lock_manager import ConfigurationLockManager, LockFileData
from TimeLocker.interfaces.exceptions import (
    ConfigurationLockError,
    ConfigurationLockTimeoutError,
    ConfigurationLockNotHeldError,
    ConfigurationStaleLockError
)


class TestConfigurationLockManager:
    """Test suite for ConfigurationLockManager"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.lock_manager = ConfigurationLockManager(self.temp_dir)
        self.test_resource = Path("/test/config/file.json")

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_manager_initialization(self):
        """Test lock manager initialization"""
        assert self.lock_manager.lock_directory == self.temp_dir
        assert self.temp_dir.exists()
        assert len(self.lock_manager._held_locks) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_acquire_and_release_lock(self):
        """Test basic lock acquisition and release"""
        # Acquire lock
        result = self.lock_manager.acquire_lock(self.test_resource, timeout=5)
        assert result is True
        
        # Verify lock is held
        assert self.lock_manager.is_locked(self.test_resource) is True
        
        # Get lock info
        lock_info = self.lock_manager.get_lock_info(self.test_resource)
        assert lock_info is not None
        assert lock_info.process_id == os.getpid()
        
        # Release lock
        self.lock_manager.release_lock(self.test_resource)
        
        # Verify lock is released
        assert self.lock_manager.is_locked(self.test_resource) is False
        assert self.lock_manager.get_lock_info(self.test_resource) is None

    @pytest.mark.config
    @pytest.mark.unit
    def test_concurrent_lock_acquisition(self):
        """Test concurrent lock acquisition from multiple threads"""
        results = []
        errors = []
        concurrency_state = {'active': 0, 'max': 0}
        concurrency_lock = threading.Lock()

        def acquire_lock_worker(worker_id):
            try:
                acquired = self.lock_manager.acquire_lock(self.test_resource, timeout=5)
                results.append((worker_id, acquired))
                if acquired:
                    with concurrency_lock:
                        concurrency_state['active'] += 1
                        concurrency_state['max'] = max(
                                concurrency_state['max'],
                                concurrency_state['active']
                        )
                    # Hold the lock briefly to force contention
                    time.sleep(0.1)
                    with concurrency_lock:
                        concurrency_state['active'] -= 1
                    self.lock_manager.release_lock(self.test_resource)
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Start multiple threads trying to acquire the same lock simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=acquire_lock_worker, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Every thread should eventually acquire the lock, but never concurrently
        assert len(errors) == 0
        assert all(acquired for _, acquired in results)
        assert concurrency_state['max'] == 1

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_timeout(self):
        """Test lock acquisition timeout"""
        # Acquire lock in first manager
        result = self.lock_manager.acquire_lock(self.test_resource, timeout=5)
        assert result is True
        
        # Try to acquire same lock with second manager (should timeout)
        second_manager = ConfigurationLockManager(self.temp_dir)
        
        start_time = time.time()
        with pytest.raises(ConfigurationLockTimeoutError):
            second_manager.acquire_lock(self.test_resource, timeout=1)
        
        elapsed_time = time.time() - start_time
        assert 0.9 <= elapsed_time <= 1.5  # Should timeout around 1 second

    @pytest.mark.config
    @pytest.mark.unit
    def test_release_unheld_lock(self):
        """Test releasing a lock that is not held"""
        with pytest.raises(ConfigurationLockNotHeldError):
            self.lock_manager.release_lock(self.test_resource)

    @pytest.mark.config
    @pytest.mark.unit
    def test_stale_lock_cleanup(self):
        """Test cleanup of stale locks"""
        # Create a fake stale lock file
        lock_file_path = self.lock_manager._get_lock_file_path(self.test_resource)
        
        # Create lock data with old timestamp and non-existent process
        stale_lock_data = LockFileData(
            lock_id="stale_lock_123",
            process_id=99999,  # Non-existent process ID
            acquired_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            expires_at=(datetime.now() - timedelta(minutes=30)).isoformat(),
            operation="test_operation",
            sections=["test_section"],
            hostname="test_host"
        )
        
        # Write stale lock file
        import json
        from dataclasses import asdict
        with open(lock_file_path, 'w') as f:
            json.dump(asdict(stale_lock_data), f)
        
        # Verify lock file exists
        assert lock_file_path.exists()
        
        # Run cleanup
        cleaned_count = self.lock_manager.cleanup_stale_locks(max_age=300)
        
        # Verify stale lock was cleaned up
        assert cleaned_count == 1
        assert not lock_file_path.exists()

    @pytest.mark.config
    @pytest.mark.unit
    def test_list_active_locks(self):
        """Test listing active locks"""
        # Initially no active locks
        active_locks = self.lock_manager.list_active_locks()
        assert len(active_locks) == 0
        
        # Acquire a lock
        self.lock_manager.acquire_lock(self.test_resource, timeout=5)
        
        # Should now have one active lock
        active_locks = self.lock_manager.list_active_locks()
        assert len(active_locks) == 1
        assert active_locks[0].process_id == os.getpid()
        
        # Release lock
        self.lock_manager.release_lock(self.test_resource)
        
        # Should be no active locks again
        active_locks = self.lock_manager.list_active_locks()
        assert len(active_locks) == 0

    @pytest.mark.config
    @pytest.mark.unit
    def test_force_release_lock(self):
        """Test force releasing a lock"""
        # Acquire lock
        self.lock_manager.acquire_lock(self.test_resource, timeout=5)
        assert self.lock_manager.is_locked(self.test_resource) is True
        
        # Force release lock
        result = self.lock_manager.force_release_lock(self.test_resource)
        assert result is True
        
        # Verify lock is released
        assert self.lock_manager.is_locked(self.test_resource) is False

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_file_path_generation(self):
        """Test lock file path generation"""
        test_paths = [
            Path("/config/test.json"),
            Path("C:\\config\\test.json"),
            Path("/very/long/path/to/config/file.json")
        ]
        
        for path in test_paths:
            lock_file_path = self.lock_manager._get_lock_file_path(path)
            assert lock_file_path.parent == self.temp_dir
            assert lock_file_path.suffix == ".lock"
            assert lock_file_path.exists() is False

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_id_generation(self):
        """Test lock ID generation"""
        lock_id1 = self.lock_manager._generate_lock_id(self.test_resource)
        lock_id2 = self.lock_manager._generate_lock_id(self.test_resource)
        
        # Lock IDs should be unique
        assert lock_id1 != lock_id2
        
        # Should contain process ID
        assert str(os.getpid()) in lock_id1
        assert str(os.getpid()) in lock_id2

    @pytest.mark.config
    @pytest.mark.unit
    def test_process_validation(self):
        """Test process validation for lock ownership"""
        # Current process should be alive
        assert self.lock_manager._is_process_alive(os.getpid()) is True
        
        # Non-existent process should not be alive
        assert self.lock_manager._is_process_alive(99999) is False

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_expiration(self):
        """Test lock expiration handling"""
        # Create an expired lock file
        lock_file_path = self.lock_manager._get_lock_file_path(self.test_resource)
        
        expired_lock_data = LockFileData(
            lock_id="expired_lock_123",
            process_id=os.getpid(),  # Current process
            acquired_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            expires_at=(datetime.now() - timedelta(minutes=1)).isoformat(),  # Expired
            operation="test_operation",
            sections=["test_section"],
            hostname="test_host"
        )
        
        # Write expired lock file
        import json
        from dataclasses import asdict
        with open(lock_file_path, 'w') as f:
            json.dump(asdict(expired_lock_data), f)
        
        # Check if lock is valid (should be False due to expiration)
        is_valid = self.lock_manager._is_lock_file_valid(lock_file_path)
        assert is_valid is False
        
        # Lock file should be cleaned up automatically
        assert not lock_file_path.exists()

    @pytest.mark.config
    @pytest.mark.unit
    def test_invalid_lock_file_handling(self):
        """Test handling of invalid lock files"""
        lock_file_path = self.lock_manager._get_lock_file_path(self.test_resource)
        
        # Create invalid JSON file
        with open(lock_file_path, 'w') as f:
            f.write("invalid json content")
        
        # Should handle invalid file gracefully
        lock_data = self.lock_manager._read_lock_file(lock_file_path)
        assert lock_data is None
        
        # Should not consider it a valid lock
        is_valid = self.lock_manager._is_lock_file_valid(lock_file_path)
        assert is_valid is False

    @pytest.mark.config
    @pytest.mark.unit
    def test_multiple_resource_locking(self):
        """Test locking multiple different resources"""
        resource1 = Path("/config/file1.json")
        resource2 = Path("/config/file2.json")
        resource3 = Path("/config/file3.json")
        
        # Acquire locks on multiple resources
        assert self.lock_manager.acquire_lock(resource1, timeout=5) is True
        assert self.lock_manager.acquire_lock(resource2, timeout=5) is True
        assert self.lock_manager.acquire_lock(resource3, timeout=5) is True
        
        # All should be locked
        assert self.lock_manager.is_locked(resource1) is True
        assert self.lock_manager.is_locked(resource2) is True
        assert self.lock_manager.is_locked(resource3) is True
        
        # List active locks should show all three
        active_locks = self.lock_manager.list_active_locks()
        assert len(active_locks) == 3
        
        # Release all locks
        self.lock_manager.release_lock(resource1)
        self.lock_manager.release_lock(resource2)
        self.lock_manager.release_lock(resource3)
        
        # All should be unlocked
        assert self.lock_manager.is_locked(resource1) is False
        assert self.lock_manager.is_locked(resource2) is False
        assert self.lock_manager.is_locked(resource3) is False

    @pytest.mark.config
    @pytest.mark.unit
    def test_lock_manager_with_custom_directory(self):
        """Test lock manager with custom lock directory"""
        custom_dir = self.temp_dir / "custom_locks"
        custom_manager = ConfigurationLockManager(custom_dir)
        
        assert custom_manager.lock_directory == custom_dir
        assert custom_dir.exists()
        
        # Should work normally with custom directory
        result = custom_manager.acquire_lock(self.test_resource, timeout=5)
        assert result is True
        
        custom_manager.release_lock(self.test_resource)

    @pytest.mark.config
    @pytest.mark.unit
    @patch('TimeLocker.config.configuration_lock_manager.psutil')
    def test_fallback_process_check(self, mock_psutil):
        """Test fallback process checking when psutil is not available"""
        # Make psutil.pid_exists raise an exception
        mock_psutil.pid_exists.side_effect = Exception("psutil not available")
        
        # Should fall back to os.kill method
        with patch('os.kill') as mock_kill:
            mock_kill.side_effect = ProcessLookupError()
            result = self.lock_manager._is_process_alive(12345)
            assert result is False
            mock_kill.assert_called_once_with(12345, 0)

    @pytest.mark.config
    @pytest.mark.unit
    def test_cleanup_with_mixed_lock_states(self):
        """Test cleanup with a mix of valid and stale locks"""
        # Create multiple lock files with different states
        
        # Valid lock (current process, not expired)
        valid_lock_path = self.temp_dir / "valid_lock.lock"
        valid_lock_data = LockFileData(
            lock_id="valid_lock",
            process_id=os.getpid(),
            acquired_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            operation="test",
            sections=[],
            hostname="test"
        )
        
        # Stale lock (non-existent process)
        stale_lock_path = self.temp_dir / "stale_lock.lock"
        stale_lock_data = LockFileData(
            lock_id="stale_lock",
            process_id=99999,
            acquired_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat(),
            operation="test",
            sections=[],
            hostname="test"
        )
        
        # Expired lock
        expired_lock_path = self.temp_dir / "expired_lock.lock"
        expired_lock_data = LockFileData(
            lock_id="expired_lock",
            process_id=os.getpid(),
            acquired_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            expires_at=(datetime.now() - timedelta(minutes=1)).isoformat(),
            operation="test",
            sections=[],
            hostname="test"
        )
        
        # Write lock files
        import json
        from dataclasses import asdict
        
        for lock_path, lock_data in [
            (valid_lock_path, valid_lock_data),
            (stale_lock_path, stale_lock_data),
            (expired_lock_path, expired_lock_data)
        ]:
            with open(lock_path, 'w') as f:
                json.dump(asdict(lock_data), f)
        
        # Run cleanup
        cleaned_count = self.lock_manager.cleanup_stale_locks(max_age=300)
        
        # Should clean up stale and expired locks, but not valid lock
        assert cleaned_count == 2
        assert valid_lock_path.exists()
        assert not stale_lock_path.exists()
        assert not expired_lock_path.exists()
