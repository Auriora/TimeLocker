---
title: "Architecture Decision Record: Test Isolation Strategy"
id: "adr-test-isolation"
type: [ architecture ]
status: accepted
owner: "Testing Team"
last_reviewed: "09-11-2025"
tags: [ architecture, adr, testing, isolation, pytest ]
links:
    tooling: [ pytest ]
---

# Architecture Decision Record: Test Isolation Strategy for TimeLocker

- **Owner**: Testing Team
- **Status**: Accepted
- **Created Date**: 09-11-2025
- **Last Updated**: 09-11-2025
- **Audience**: Engineering Teams, Developers

## 1. Context

Tests may inadvertently access or modify real user files because:

1. **XDG variables are saved but not overridden** - Tests inherit the user's actual XDG paths
2. **Some modules use hardcoded paths** - Bypassing the centralized path resolver
3. **No test-specific path prefix** - Tests use the same directory structure as production

**Risk:** Tests could corrupt user data, credentials, or configuration files.

## 2. Decision

Implement multi-layer test isolation to ensure tests never modify actual user configuration files, credentials, or data.

### Layer 1: Environment Variable Override (Highest Priority)

Override all XDG and path-related environment variables to point to test-specific temporary directories.

**Implementation in `tests/TimeLocker/test_fixtures.py`:**

```python
@pytest.fixture(autouse=True)
def isolate_environment(resource_manager, tmp_path):
    """Isolate test environment to prevent state pollution"""
    # Save current working directory
    original_cwd = os.getcwd()
    
    # Create test-specific directories
    test_config_home = tmp_path / "config"
    test_data_home = tmp_path / "data"
    test_cache_home = tmp_path / "cache"
    test_state_home = tmp_path / "state"
    test_runtime_dir = tmp_path / "runtime"
    
    # Create directories
    for directory in [test_config_home, test_data_home, test_cache_home, 
                      test_state_home, test_runtime_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Override XDG environment variables
    test_env = {
        # XDG Base Directory Specification
        'XDG_CONFIG_HOME': str(test_config_home),
        'XDG_DATA_HOME': str(test_data_home),
        'XDG_CACHE_HOME': str(test_cache_home),
        'XDG_STATE_HOME': str(test_state_home),
        'XDG_RUNTIME_DIR': str(test_runtime_dir),
        
        # Windows paths
        'APPDATA': str(test_config_home),
        'LOCALAPPDATA': str(test_data_home),
        'PROGRAMDATA': str(test_data_home / "ProgramData"),
        
        # macOS paths (HOME will be used)
        'HOME': str(tmp_path / "home"),
        
        # TimeLocker-specific
        'TIMELOCKER_CONFIG_DIR': str(test_config_home / "timelocker"),
        'TIMELOCKER_TEST_MODE': '1',
        
        # Prevent actual password prompts
        'RESTIC_PASSWORD': 'test_password_12345',
        'TIMELOCKER_PASSWORD': 'test_password_12345',
    }
    
    # Save original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Create HOME directory structure
    home_dir = Path(test_env['HOME'])
    home_dir.mkdir(parents=True, exist_ok=True)
    (home_dir / ".config").mkdir(exist_ok=True)
    (home_dir / ".local" / "share").mkdir(parents=True, exist_ok=True)
    (home_dir / ".cache").mkdir(exist_ok=True)
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
    
    # Restore working directory
    try:
        os.chdir(original_cwd)
    except Exception:
        pass
```

### Layer 2: ConfigurationPathResolver Enhancement

Add test mode detection to the path resolver.

**Add to `src/TimeLocker/config/configuration_path_resolver.py`:**

```python
@staticmethod
def is_test_mode() -> bool:
    """
    Check if running in test mode.
    
    Returns:
        bool: True if running in test mode
    """
    return os.environ.get('TIMELOCKER_TEST_MODE') == '1'

@staticmethod
def get_config_directory() -> Path:
    """
    Get appropriate configuration directory based on context.
    
    Returns:
        Path: Configuration directory to use
    """
    # Test mode override
    if ConfigurationPathResolver.is_test_mode():
        test_config = os.environ.get('TIMELOCKER_CONFIG_DIR')
        if test_config:
            return Path(test_config)
    
    if ConfigurationPathResolver.is_system_context():
        return ConfigurationPathResolver.get_system_config_directory()
    else:
        return ConfigurationPathResolver.get_user_config_directory()
```

### Layer 3: Explicit config_dir Parameters in Tests

Always pass explicit `config_dir` parameters when instantiating components in tests.

**Example Test Pattern:**

```python
def test_credential_manager(tmp_path):
    """Test credential manager with isolated config"""
    config_dir = tmp_path / "credentials"
    config_dir.mkdir(parents=True)
    
    cm = CredentialManager(config_dir=config_dir)
    
    # Test operations...
    assert cm.config_dir == config_dir
    assert not (Path.home() / ".timelocker").exists()  # Verify no real files
```

### Layer 4: Pytest Configuration

Add pytest configuration to enforce test isolation.

**Add to `pytest.ini` or `pyproject.toml`:**

```ini
[tool.pytest.ini_options]
# Ensure tests run in isolated temporary directories
tmp_path_retention_count = 0
tmp_path_retention_policy = "none"

# Fail tests that access real user directories
markers = [
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "security: marks tests as security-related",
    "no_isolation: marks tests that intentionally access real paths (use sparingly)",
]

# Add custom warning for path access
filterwarnings = [
    "error::UserWarning",
    "ignore::DeprecationWarning",
]
```

## 3. Consequences

### Positive Outcomes

1. **Safety**: Tests can never corrupt user data
2. **Reproducibility**: Tests run in clean, isolated environments
3. **Parallelization**: Tests can run in parallel without conflicts
4. **CI/CD**: Tests work identically in CI and local environments
5. **Debugging**: Easy to inspect test artifacts in tmp directories

### Negative Consequences

1. **Test Updates Required**: All tests need explicit `config_dir` parameters
2. **Fixture Complexity**: More complex test setup
3. **Learning Curve**: Developers need to understand isolation patterns
4. **Maintenance**: Need to keep isolation patterns up to date

## 4. Alternatives Considered

### Option A: No Isolation (Current State)

- Pros: Simple, no changes needed
- Cons: HIGH RISK - tests can corrupt user data

### Option B: Manual Isolation Per Test

- Pros: Flexible, test-specific control
- Cons: Error-prone, inconsistent, easy to forget

### Option C: Multi-Layer Isolation (CHOSEN)

- Pros: Comprehensive, automatic, safe by default
- Cons: More complex setup, requires fixture updates

## 5. Implementation Checklist

### Phase 1: Core Infrastructure (High Priority)

- [ ] Update `test_fixtures.py` with enhanced `isolate_environment` fixture
- [ ] Add `is_test_mode()` to `ConfigurationPathResolver`
- [ ] Add `TIMELOCKER_TEST_MODE` environment variable support
- [ ] Update pytest configuration

### Phase 2: Fix Hardcoded Paths (High Priority)

- [ ] Update `selection_template_manager.py` to use `ConfigurationPathResolver`
- [ ] Update `notification_service.py` to use `ConfigurationPathResolver`
- [ ] Update `status_reporter.py` to use `ConfigurationPathResolver`
- [ ] Update `credential_manager.py` to use `ConfigurationPathResolver`
- [ ] Update `pattern_group_manager.py` to use `ConfigurationPathResolver`
- [ ] Update `backup_notification_service.py` to use `ConfigurationPathResolver`

### Phase 3: Test Updates (Medium Priority)

- [ ] Audit all tests to ensure they pass explicit `config_dir` parameters
- [ ] Add assertions to verify no real user files are accessed
- [ ] Add test helper to verify isolation
- [ ] Update test documentation

### Phase 4: Validation (Medium Priority)

- [ ] Run full test suite with isolation enabled
- [ ] Verify no files created in `~/.config/timelocker/`
- [ ] Verify no files created in `~/.timelocker/`
- [ ] Verify no files created in `~/.local/share/timelocker/`
- [ ] Add CI check to verify isolation

## 6. Test Helper Functions

Add to `tests/TimeLocker/test_fixtures.py`:

```python
def verify_no_user_files_created():
    """
    Verify that no files were created in actual user directories.
    
    Raises:
        AssertionError: If any user files were created
    """
    user_paths = [
        Path.home() / ".timelocker",
        Path.home() / ".config" / "timelocker",
        Path.home() / ".local" / "share" / "timelocker",
        Path.home() / ".cache" / "timelocker",
        Path.home() / ".local" / "state" / "timelocker",
    ]
    
    # Only check if not in test mode (sanity check)
    if os.environ.get('TIMELOCKER_TEST_MODE') != '1':
        return  # Skip check if somehow not in test mode
    
    for path in user_paths:
        if path.exists():
            files = list(path.rglob("*"))
            if files:
                raise AssertionError(
                    f"Test created files in real user directory: {path}\n"
                    f"Files: {files[:10]}"  # Show first 10 files
                )


@pytest.fixture(autouse=True)
def verify_isolation():
    """Automatically verify test isolation after each test"""
    yield
    verify_no_user_files_created()
```

# References

- [Pytest tmp_path fixture](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [file-locations-review.md](./file-locations-review.md)
- [path-review-summary.md](./path-review-summary.md)
