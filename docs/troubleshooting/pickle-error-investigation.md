# Investigation: "cannot pickle '_thread.RLock' object" Error in Repository Initialization

## Problem Statement

When running `tl repos init <name> --yes --password <password>`, the command fails with:
```
Repository initialization failed: cannot pickle '_thread.RLock' object
```

However, running the underlying `restic init` command directly works perfectly:
```bash
RESTIC_PASSWORD=test123 restic -r /var/data/tl-test/ init
# Works fine - repository created successfully
```

## Environment

- **OS**: Linux (Ubuntu 24.04)
- **Python**: 3.12
- **Restic**: 0.18.0 compiled with go1.24.1 on linux/amd64
- **TimeLocker**: 1.0.0

## What We Know

### 1. The Error Flow

The error occurs in this call chain:

```
CLI Command (repos_init)
  ↓
cli_services.py: initialize_repository()
  ↓
local.py: LocalResticRepository.initialize_repository()
  ↓
restic_repository.py: ResticRepository.initialize()
  ↓
CommandBuilder.run() → subprocess execution
  ↓
ERROR: "cannot pickle '_thread.RLock' object"
```

### 2. Code Locations

**File**: `src/TimeLocker/cli_services.py` (lines 794-835)
```python
def initialize_repository(self, name: str, ...) -> Dict[str, Any]:
    repo, resolved_name, resolved_uri = self._create_repository_instance(...)
    
    try:
        if hasattr(repo, "initialize_repository"):
            success = bool(repo.initialize_repository(password))
        else:
            success = bool(repo.initialize())
    except Exception as exc:
        error_msg = str(exc)  # Converts exception to string
        return {
            "success": False,
            "error": error_msg,
            "errors": [error_msg]
        }
```

**File**: `src/TimeLocker/restic/Repositories/local.py` (lines 103-145)
```python
def initialize_repository(self, password: Optional[str] = None) -> bool:
    # Ensure directory exists
    if not self.create_repository_directory():
        raise Exception(f"Failed to create repository directory: {self._location}")
    
    # Set password temporarily
    if password:
        original_password = self._explicit_password
        self._explicit_password = password
        self._cached_env = None
    
    try:
        # Check if already initialized
        if self.is_repository_initialized():
            return True
        
        # Initialize the repository (this raises exception on failure)
        result = self.initialize()  # Calls parent class method
        
        if result and password:
            self.store_password(password)
        
        return result
    finally:
        # Restore original password
        if password:
            self._explicit_password = original_password
            self._cached_env = None
```

**File**: `src/TimeLocker/restic/restic_repository.py` (lines 186-227)
```python
def initialize(self) -> bool:
    try:
        result = self._command.command("init").run(self.to_env())
        logger.info("Repository initialized successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to initialize repository: {e}")
        logger.error(f"Command: {e.cmd}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        
        # Parse JSON error from restic
        error_message = "Repository initialization failed"
        if e.stderr:
            try:
                error_data = json.loads(e.stderr)
                if "message" in error_data:
                    error_message = error_data["message"]
            except (json.JSONDecodeError, KeyError):
                error_message = e.stderr.strip()
        
        raise Exception(error_message)
    except subprocess.CalledProcessError:
        raise
    except Exception as e:
        error_str = str(e)
        logger.error(f"Failed to initialize repository: {error_str}")
        raise Exception(f"Repository initialization failed: {error_str}")
```

### 3. What the Error Means

The error "cannot pickle '_thread.RLock' object" indicates that Python is trying to serialize (pickle) an object that contains a threading lock (`_thread.RLock`), which cannot be pickled.

**Possible sources of RLock objects:**
- Python's `logging` module uses locks internally
- `subprocess` module may use locks
- Any custom threading or multiprocessing code
- Cached objects that contain locks

### 4. What We've Tried

1. ✅ **Improved error handling** - Now captures and displays actual error messages
2. ✅ **String conversion** - Converting exceptions to strings with `str(exc)`
3. ✅ **Pre-flight checks** - Added directory existence and permission checks
4. ❌ **Direct restic execution** - Works fine, so restic itself is not the issue

### 5. Observations

- **Restic works directly**: `RESTIC_PASSWORD=test123 restic -r /path init` succeeds
- **Error is consistent**: Happens every time with fresh repositories
- **Already initialized repos work**: If restic has already initialized the repo, TimeLocker recognizes it correctly
- **No explicit pickling**: The codebase doesn't use `pickle` or `multiprocessing` explicitly

### 6. Debug Output

When running with `--verbose`, we see:
```
Debug: init result = {
    'success': False, 
    'already_initialized': False, 
    'uri': 'file:///var/data/tl-test/', 
    'error': "cannot pickle '_thread.RLock' object", 
    'errors': ["cannot pickle '_thread.RLock' object"]
}
```

## Investigation Tasks

### 1. Check CommandBuilder.run() Implementation

The error likely originates in the `CommandBuilder.run()` method. Need to examine:
- How it executes subprocess commands
- Whether it uses any threading or multiprocessing
- How it handles exceptions
- Whether it caches any objects with locks

**Files to check:**
- `src/TimeLocker/restic/command_builder.py` or similar
- Look for the `.run()` method implementation

### 2. Check Logging Configuration

The logging module uses locks internally. Check if:
- Custom logging handlers are being used
- Logging is being configured in a way that creates serialization issues
- Log handlers are being passed around or cached

**Files to check:**
- `src/TimeLocker/restic/logging.py`
- Any logging setup in `__init__.py` files
- Custom log handlers

### 3. Check for Cached Objects

Look for any caching mechanisms that might store objects with locks:
- `self._cached_env` in repository classes
- Any `@lru_cache` or similar decorators
- Class-level caches or singletons

### 4. Check Exception Handling Chain

The error message itself is "cannot pickle '_thread.RLock' object", which suggests:
- An exception is being raised somewhere
- That exception object contains an RLock
- Something is trying to serialize that exception

**Hypothesis**: The `subprocess.CalledProcessError` exception object might contain references to objects with locks (like file handles or logging objects).

### 5. Test Isolation

Create a minimal test case:
```python
from TimeLocker.restic.Repositories.local import LocalResticRepository

repo = LocalResticRepository("/var/data/test-repo", password="test123")
try:
    result = repo.initialize_repository("test123")
    print(f"Success: {result}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
    print(f"Error dir: {dir(e)}")
```

## Potential Solutions

### Solution 1: Avoid Exception Serialization

Instead of raising exceptions with complex objects, ensure all exceptions only contain string data:

```python
except subprocess.CalledProcessError as e:
    # Extract only string data
    error_msg = f"Command failed: {' '.join(e.cmd)}"
    if e.stderr:
        error_msg += f"\nStderr: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}"
    # Raise new exception with only string data
    raise RuntimeError(error_msg)
```

### Solution 2: Check for Multiprocessing

Search for any use of `multiprocessing` or `concurrent.futures` that might be trying to serialize objects:

```bash
grep -r "multiprocessing\|ProcessPoolExecutor\|pickle" src/TimeLocker/
```

### Solution 3: Isolate Logging

Temporarily disable or simplify logging to see if that's the source:

```python
# In initialize() method, try without logging
try:
    result = self._command.command("init").run(self.to_env())
    return True
except subprocess.CalledProcessError as e:
    # Minimal error handling without logging
    raise RuntimeError(f"Init failed: {e.returncode}")
```

### Solution 4: Check CommandBuilder Implementation

The `.run()` method might be doing something that requires serialization. Need to see its implementation.

## Questions to Answer

1. **Where is CommandBuilder.run() defined?** What does it do?
2. **Is there any multiprocessing or threading in the command execution?**
3. **Are there any custom logging handlers that might contain locks?**
4. **Is the exception being passed through any serialization boundary?**
5. **Why does direct restic execution work but TimeLocker's wrapper doesn't?**

## Next Steps

1. Find and examine `CommandBuilder.run()` implementation
2. Add debug logging to trace exactly where the pickle error originates
3. Try the minimal test case to isolate the issue
4. Check if removing logging temporarily fixes the issue
5. Look for any caching or singleton patterns that might store locks

## Solution

**Root Cause**: The `CredentialManager` class contains a `threading.RLock()` object (`self._file_lock`) which cannot be pickled. When the credential manager is passed to repository instances and an exception occurs, Python attempts to serialize the exception (which may reference the repository and its credential manager), causing the pickle error.

**Fix Applied**: Added `__getstate__` and `__setstate__` methods to the `CredentialManager` class to handle pickling by excluding the RLock and recreating it after unpickling.

**File Modified**: `src/TimeLocker/security/credential_manager.py`

```python
def __getstate__(self):
    """Support for pickling by excluding non-picklable objects."""
    state = self.__dict__.copy()
    state['_file_lock'] = None  # Remove the unpicklable RLock
    return state

def __setstate__(self, state):
    """Restore state after unpickling and recreate the RLock"""
    self.__dict__.update(state)
    self._file_lock = threading.RLock()  # Recreate the RLock
```

**Verification**: Repository initialization now works correctly:
```bash
tl repos init test-repo --yes --password test123
# ✅ Repository 'test-repo' initialized successfully.
```

## Files to Investigate

Priority order:
1. `src/TimeLocker/restic/command_builder.py` - Find the `.run()` method
2. `src/TimeLocker/restic/logging.py` - Check logging setup
3. `src/TimeLocker/restic/__init__.py` - Check for module-level initialization
4. Any files with `@lru_cache` or caching decorators
5. Any files using `threading` or `multiprocessing`

## Search Commands

```bash
# Find CommandBuilder
find src/TimeLocker -name "*.py" -exec grep -l "class CommandBuilder" {} \;

# Find .run() method
grep -rn "def run(" src/TimeLocker/restic/

# Check for threading/multiprocessing
grep -rn "import threading\|import multiprocessing\|from threading\|from multiprocessing" src/TimeLocker/

# Check for pickle usage
grep -rn "import pickle\|pickle\." src/TimeLocker/

# Check for caching
grep -rn "@lru_cache\|@cache\|functools.cache" src/TimeLocker/
```
