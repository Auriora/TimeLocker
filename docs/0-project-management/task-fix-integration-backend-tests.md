# Prompt: Fix Integration/Multi-Backend Tests (5 failures + 6 errors)

## Copy this prompt to start a new conversation:

---

I need help fixing integration tests for multi-backend repository management and MinIO integration in the TimeLocker project.

## Failing Tests

### Multi-Backend Tests (5 failures)
**File:** `tests/TimeLocker/integration/test_repository_multi_backend_integration.py`

1. `test_s3_repository_management` - RepositoryAlreadyExistsError
2. `test_b2_repository_management` - RepositoryAlreadyExistsError  
3. `test_mixed_backend_repository_listing` - AttributeError: 'method' object has no attribute 'return_value'
4. `test_plugin_registry_initialization` - Plugin assertion failure

### MinIO Tests (6 errors)
**File:** `tests/TimeLocker/integration/test_s3_minio.py`

All 6 tests error with: `RuntimeError: MinIO not available: MinIO not reachable`

### Integration Service Test (1 failure)
**File:** `tests/TimeLocker/integration/test_integration_service.py`

1. `test_configuration_integration` - Assertion failure

## Issue Analysis

### Issue 1: RepositoryAlreadyExistsError (2 tests)

```python
src.TimeLocker.interfaces.repository_management_models.RepositoryAlreadyExistsError
```

**Root Cause:** Tests are trying to create repositories that already exist from previous test runs.

**Solutions:**
1. Clean up repositories in test teardown
2. Use unique repository names per test run (e.g., with UUID or timestamp)
3. Check if repository exists before creating
4. Use pytest fixtures with proper cleanup

**Fix pattern:**
```python
@pytest.fixture
def unique_repo_name():
    """Generate unique repository name for each test."""
    import uuid
    return f"test-repo-{uuid.uuid4().hex[:8]}"

def test_s3_repository_management(unique_repo_name):
    # Use unique_repo_name instead of hardcoded "test-repo"
    repo_manager.create_repository(unique_repo_name, ...)
```

### Issue 2: Mock AttributeError (1 test)

```python
AttributeError: 'method' object has no attribute 'return_value'
```

**Root Cause:** Trying to set `return_value` on a method instead of a Mock object.

**Common mistake:**
```python
# Wrong - trying to mock a method directly
mock_obj.some_method.return_value = "value"  # If some_method is not a Mock

# Right - need to mock it first
mock_obj.some_method = Mock(return_value="value")
```

**Fix pattern:**
```python
# Before (failing)
mock_manager.list_repositories.return_value = [...]  # Fails if not a Mock

# After (fixed)
from unittest.mock import Mock
mock_manager.list_repositories = Mock(return_value=[...])
```

### Issue 3: Plugin Registry Assertion (1 test)

```python
AssertionError: assert (<BackupEngine.RESTIC: 'restic'> in [<BackupEngine.R...
```

**Root Cause:** Plugin registry not returning expected engines.

**Investigation needed:**
1. Check if plugins are properly registered
2. Verify plugin initialization order
3. Check if test is using correct assertion

### Issue 4: MinIO Not Available (6 errors)

```python
RuntimeError: MinIO not available: MinIO not reachable: <urlopen error [Errno -2] Name or service not found>
```

**Root Cause:** Tests require MinIO server running locally, but it's not available.

**Solutions:**

**Option 1: Skip tests when MinIO unavailable (Recommended)**
```python
import pytest
import socket

def is_minio_available():
    """Check if MinIO is reachable."""
    try:
        socket.create_connection(("localhost", 9000), timeout=1)
        return True
    except (socket.error, socket.timeout):
        return False

@pytest.mark.skipif(not is_minio_available(), reason="MinIO not available")
def test_s3_repository_initialization():
    ...
```

**Option 2: Add pytest marker for integration tests**
```python
# In pytest.ini
[pytest]
markers =
    minio: tests requiring MinIO server (deselect with '-m "not minio"')

# In test file
@pytest.mark.minio
def test_s3_repository_initialization():
    ...

# Run without MinIO tests
pytest -m "not minio"
```

**Option 3: Use moto for S3 mocking**
```python
import pytest
from moto import mock_s3

@mock_s3
def test_s3_repository_initialization():
    # Uses mocked S3 instead of real MinIO
    ...
```

## Tasks

### Task 1: Fix RepositoryAlreadyExistsError (2 tests)

1. **Add cleanup fixtures:**
   ```python
   @pytest.fixture
   def clean_test_repos():
       """Clean up test repositories before and after tests."""
       repo_names = []
       yield repo_names
       # Cleanup
       for name in repo_names:
           try:
               repo_manager.delete_repository(name)
           except:
               pass
   ```

2. **Use unique names:**
   ```python
   import uuid
   repo_name = f"test-s3-{uuid.uuid4().hex[:8]}"
   ```

3. **Add existence check:**
   ```python
   if repo_manager.repository_exists(repo_name):
       repo_manager.delete_repository(repo_name)
   repo_manager.create_repository(repo_name, ...)
   ```

### Task 2: Fix Mock AttributeError (1 test)

1. **Find the failing line:**
   ```bash
   pytest tests/TimeLocker/integration/test_repository_multi_backend_integration.py::TestMultiBackendRepositoryManagement::test_mixed_backend_repository_listing -xvs
   ```

2. **Fix the mock:**
   ```python
   # Change from:
   mock_obj.method.return_value = value
   
   # To:
   from unittest.mock import Mock
   mock_obj.method = Mock(return_value=value)
   ```

### Task 3: Fix Plugin Registry Test (1 test)

1. **Check plugin initialization:**
   ```python
   from TimeLocker.services.plugin_registry import get_plugin_registry
   registry = get_plugin_registry()
   available = registry.get_available_engines()
   print(f"Available engines: {available}")
   ```

2. **Update test assertion:**
   - Check what engines are actually available
   - Update test to match reality

### Task 4: Handle MinIO Tests (6 errors)

**Recommended: Skip when unavailable**

1. **Add skip decorator:**
   ```python
   import pytest
   
   def check_minio():
       try:
           import socket
           socket.create_connection(("localhost", 9000), timeout=1)
           return True
       except:
           return False
   
   pytestmark = pytest.mark.skipif(
       not check_minio(),
       reason="MinIO server not available on localhost:9000"
   )
   ```

2. **Or add to pytest.ini:**
   ```ini
   [pytest]
   markers =
       minio: requires MinIO server running
   ```

3. **Document in README:**
   ```markdown
   ## Running MinIO Tests
   
   MinIO tests require a local MinIO server:
   ```bash
   # Start MinIO
   docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
   
   # Run all tests including MinIO
   pytest tests/TimeLocker/integration/
   
   # Skip MinIO tests
   pytest tests/TimeLocker/integration/ -m "not minio"
   ```
   ```

### Task 5: Fix Integration Service Test (1 test)

1. **Run with verbose output:**
   ```bash
   pytest tests/TimeLocker/integration/test_integration_service.py::TestIntegrationService::test_configuration_integration -xvs
   ```

2. **Check assertion:**
   - See what's being compared
   - Update test or fix implementation

## Success Criteria

- [ ] RepositoryAlreadyExistsError tests fixed with cleanup or unique names
- [ ] Mock AttributeError fixed
- [ ] Plugin registry test passes or has correct assertions
- [ ] MinIO tests properly skipped when MinIO unavailable
- [ ] MinIO tests documented in README
- [ ] Integration service test passes
- [ ] All tests can run without external dependencies (except when explicitly marked)

## Files to Review

- `tests/TimeLocker/integration/test_repository_multi_backend_integration.py`
- `tests/TimeLocker/integration/test_s3_minio.py`
- `tests/TimeLocker/integration/test_integration_service.py`
- `src/TimeLocker/services/repository_manager.py`
- `src/TimeLocker/services/plugin_registry.py`

## Testing Commands

```bash
# Run multi-backend tests
pytest tests/TimeLocker/integration/test_repository_multi_backend_integration.py -xvs

# Run without MinIO tests
pytest tests/TimeLocker/integration/ -k "not minio" -v

# Check if MinIO is running
curl http://localhost:9000/minio/health/live
```

---

## Shorter Version:

---

Fix 11 integration/backend tests:

**Issue 1: RepositoryAlreadyExistsError (2 tests)**
- Add cleanup in teardown or use unique repo names with UUID
- `repo_name = f"test-{uuid.uuid4().hex[:8]}"`

**Issue 2: Mock AttributeError (1 test)**
- Change `mock.method.return_value = x` to `mock.method = Mock(return_value=x)`

**Issue 3: Plugin Registry (1 test)**
- Check what engines are actually available
- Update assertion to match

**Issue 4: MinIO Not Available (6 errors)**
- Add skip decorator: `@pytest.mark.skipif(not check_minio(), reason="MinIO not available")`
- Or mark with `@pytest.mark.minio` and document how to skip

**Issue 5: Integration Service (1 test)**
- Run with `-xvs` to see assertion details
- Fix test or implementation

**Files:**
- `tests/TimeLocker/integration/test_repository_multi_backend_integration.py`
- `tests/TimeLocker/integration/test_s3_minio.py`

---
