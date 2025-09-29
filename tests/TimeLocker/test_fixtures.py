"""
Enhanced test fixtures for reliable resource management and test isolation.
"""

import os
import gc
import shutil
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import patch
from contextlib import contextmanager

import pytest


class ResourceManager:
    """Manages test resources and ensures proper cleanup"""
    
    def __init__(self):
        self.temp_dirs: List[Path] = []
        self.processes: List[subprocess.Popen] = []
        self.patches: List[Any] = []
        self.original_env: Dict[str, str] = {}
        self.cleanup_callbacks: List[callable] = []
    
    def create_temp_dir(self, prefix: str = "timelocker_test_") -> Path:
        """Create a temporary directory that will be automatically cleaned up"""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def run_subprocess(self, *args, timeout: int = 30, **kwargs) -> subprocess.CompletedProcess:
        """Run subprocess with automatic timeout and cleanup"""
        kwargs.setdefault('timeout', timeout)
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        
        return subprocess.run(*args, **kwargs)
    
    def start_background_process(self, *args, **kwargs) -> subprocess.Popen:
        """Start background process with automatic cleanup tracking"""
        process = subprocess.Popen(*args, **kwargs)
        self.processes.append(process)
        return process
    
    def set_env_var(self, key: str, value: str) -> None:
        """Set environment variable with automatic restoration"""
        if key not in self.original_env:
            self.original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    def add_patch(self, patch_obj) -> Any:
        """Add patch with automatic cleanup"""
        started_patch = patch_obj.start()
        self.patches.append(patch_obj)
        return started_patch
    
    def add_cleanup_callback(self, callback: callable) -> None:
        """Add custom cleanup callback"""
        self.cleanup_callbacks.append(callback)
    
    def cleanup(self) -> None:
        """Comprehensive cleanup of all resources"""
        # Stop background processes
        for process in self.processes:
            try:
                if process.poll() is None:  # Still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception:
                pass  # Best effort cleanup
        
        # Stop patches
        for patch_obj in reversed(self.patches):
            try:
                patch_obj.stop()
            except Exception:
                pass
        
        # Restore environment variables
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        
        # Run custom cleanup callbacks
        for callback in reversed(self.cleanup_callbacks):
            try:
                callback()
            except Exception:
                pass
        
        # Remove temporary directories
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        
        # Force garbage collection
        gc.collect()
        
        # Clear all lists
        self.temp_dirs.clear()
        self.processes.clear()
        self.patches.clear()
        self.original_env.clear()
        self.cleanup_callbacks.clear()


@pytest.fixture(scope="session", autouse=True)
def session_cleanup():
    """Session-level cleanup to ensure no resources leak between test sessions"""
    yield
    
    # Force cleanup of any remaining resources
    gc.collect()
    
    # Clean up any remaining temporary files
    temp_base = Path(tempfile.gettempdir())
    for item in temp_base.glob("timelocker_test_*"):
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def resource_manager():
    """Automatic resource management for each test"""
    manager = ResourceManager()
    
    yield manager
    
    # Cleanup after test
    manager.cleanup()


@pytest.fixture(autouse=True)
def isolate_environment(resource_manager):
    """Isolate test environment to prevent state pollution"""
    # Save current working directory
    original_cwd = os.getcwd()
    
    # Save important environment variables
    important_env_vars = [
        'RESTIC_PASSWORD', 'TIMELOCKER_PASSWORD', 'HOME', 'USER',
        'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME'
    ]
    
    for var in important_env_vars:
        if var in os.environ:
            resource_manager.original_env[var] = os.environ[var]
    
    yield
    
    # Restore working directory
    try:
        os.chdir(original_cwd)
    except Exception:
        pass


@pytest.fixture
def safe_temp_dir(resource_manager):
    """Provide a safe temporary directory that will be automatically cleaned up"""
    return resource_manager.create_temp_dir()


@pytest.fixture
def safe_subprocess(resource_manager):
    """Provide a safe subprocess runner with automatic timeout and cleanup"""
    return resource_manager.run_subprocess


@pytest.fixture
def mock_restic_executable(resource_manager):
    """Mock restic executable to prevent actual restic calls during tests"""
    mock_patch = patch('TimeLocker.restic.restic_repository.ResticRepository._verify_restic_executable')
    mock_verify = resource_manager.add_patch(mock_patch)
    mock_verify.return_value = "0.18.0"
    return mock_verify


@pytest.fixture
def mock_subprocess_run(resource_manager):
    """Mock subprocess.run to prevent external process calls"""
    mock_patch = patch('subprocess.run')
    mock_run = resource_manager.add_patch(mock_patch)
    
    # Default successful response
    mock_result = type('MockResult', (), {
        'returncode': 0,
        'stdout': '{"message_type": "summary", "files_new": 5, "files_changed": 0}',
        'stderr': ''
    })()
    mock_run.return_value = mock_result
    
    return mock_run


@contextmanager
def timeout_context(seconds: int = 30):
    """Context manager for test timeouts"""
    def timeout_handler():
        raise TimeoutError(f"Test timed out after {seconds} seconds")
    
    timer = threading.Timer(seconds, timeout_handler)
    timer.start()
    
    try:
        yield
    finally:
        timer.cancel()


# Enhanced version of the original conftest fixtures with proper cleanup
@pytest.fixture
def selection():
    """File selection fixture with automatic cleanup"""
    from src.TimeLocker.file_selections import FileSelection
    return FileSelection()


@pytest.fixture
@pytest.mark.unit
def test_dir():
    """Mock test directory"""
    from unittest.mock import Mock
    from pathlib import Path
    
    test_dir = Mock(spec=Path)
    test_dir.is_dir.return_value = True
    test_dir.__str__ = lambda x: "/test/dir"
    return test_dir


@pytest.fixture
@pytest.mark.unit
def test_file():
    """Mock test file"""
    from unittest.mock import Mock
    from pathlib import Path
    
    test_file = Mock(spec=Path)
    test_file.is_dir.return_value = False
    test_file.__str__ = lambda x: "/test/file.txt"
    return test_file
