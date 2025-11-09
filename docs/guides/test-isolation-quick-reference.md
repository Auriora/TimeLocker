# Test Isolation Quick Reference

**For TimeLocker Developers**

---

## Overview

All tests now run in complete isolation and cannot modify user files. This is achieved through automatic environment variable overrides in the test fixtures.

---

## How It Works

When you run tests, the `isolate_environment` fixture automatically:

1. Creates temporary directories for each test
2. Overrides all XDG environment variables to point to temp directories
3. Sets `TIMELOCKER_TEST_MODE=1`
4. Restores everything after the test completes

**Result:** Tests use `/tmp/pytest-*/` instead of `~/.config/timelocker/`

---

## Writing Tests

### ✅ Good - Explicit config_dir

```python
def test_credential_manager(tmp_path):
    """Test with explicit config directory"""
    config_dir = tmp_path / "credentials"
    cm = CredentialManager(config_dir=config_dir)
    
    # All operations use tmp_path
    cm.unlock("test_password")
    cm.store_credential("repo", "user", "pass")
    
    # Verify isolation
    assert cm.config_dir == config_dir
    assert str(cm.config_dir).startswith(str(tmp_path))
```

### ✅ Good - Rely on environment override

```python
def test_notification_service():
    """Test relies on automatic environment isolation"""
    # No config_dir parameter - uses environment variables
    ns = NotificationService()
    
    # Will use /tmp/pytest-*/config/timelocker/notifications
    # because XDG_CONFIG_HOME is overridden
    assert "tmp" in str(ns.config_dir) or "temp" in str(ns.config_dir).lower()
```

### ❌ Bad - Hardcoded paths

```python
def test_bad_example():
    """DON'T DO THIS - bypasses isolation"""
    # This would try to use real user directory
    config_dir = Path.home() / ".timelocker"  # ❌ BAD
    cm = CredentialManager(config_dir=config_dir)
```

---

## Verifying Isolation

### Check Test Logs

Tests should show `/tmp/` paths in logs:

```bash
python -m pytest tests/TimeLocker/security/test_credential_manager.py -v -s
```

Look for:
```
Initialized security log file: /tmp/pytest-*/security/security_events.jsonl
```

### Verify User Files Unchanged

```bash
# Before tests
stat ~/.timelocker/credentials/*

# Run tests
python -m pytest tests/TimeLocker/security/ -v

# After tests - timestamps should be unchanged
stat ~/.timelocker/credentials/*
```

---

## Environment Variables Set by Tests

The `isolate_environment` fixture sets:

| Variable | Test Value | Purpose |
|----------|------------|---------|
| `XDG_CONFIG_HOME` | `/tmp/pytest-*/config` | Configuration files |
| `XDG_DATA_HOME` | `/tmp/pytest-*/data` | User data files |
| `XDG_CACHE_HOME` | `/tmp/pytest-*/cache` | Cache files |
| `XDG_STATE_HOME` | `/tmp/pytest-*/state` | State/log files |
| `XDG_RUNTIME_DIR` | `/tmp/pytest-*/runtime` | Runtime files |
| `HOME` | `/tmp/pytest-*/home` | Home directory |
| `TIMELOCKER_TEST_MODE` | `1` | Enables test mode |
| `TIMELOCKER_CONFIG_DIR` | `/tmp/pytest-*/config/timelocker` | Config override |

---

## Common Patterns

### Pattern 1: Component with Default Paths

```python
def test_component_default_paths():
    """Component uses default paths - automatically isolated"""
    component = MyComponent()  # No config_dir parameter
    
    # Component will use /tmp/pytest-*/ paths
    # because environment variables are overridden
    assert "tmp" in str(component.config_dir).lower()
```

### Pattern 2: Component with Explicit Paths

```python
def test_component_explicit_paths(tmp_path):
    """Component with explicit config_dir"""
    config_dir = tmp_path / "my_component"
    component = MyComponent(config_dir=config_dir)
    
    # Component uses our explicit path
    assert component.config_dir == config_dir
```

### Pattern 3: Integration Test

```python
def test_integration_workflow(tmp_path):
    """Integration test with multiple components"""
    # Create isolated directory structure
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    
    # Initialize components
    cm = CredentialManager(config_dir=config_dir / "credentials")
    ns = NotificationService(config_dir=config_dir / "notifications")
    
    # Run workflow...
    
    # Verify all files in tmp_path
    all_files = list(tmp_path.rglob("*"))
    assert all(str(f).startswith(str(tmp_path)) for f in all_files)
```

---

## Debugging

### Test Creates Files in Wrong Location

If a test creates files in `~/.config/timelocker/`:

1. **Check if component accepts config_dir parameter**
   - If yes: Pass explicit `tmp_path` parameter
   - If no: Component should use `ConfigurationPathResolver`

2. **Check if component uses hardcoded paths**
   - Look for `Path.home()` or `~/.timelocker` in code
   - Should use `ConfigurationPathResolver.get_config_directory()`

3. **Check if test disables isolation**
   - Look for `@pytest.mark.no_isolation` (if implemented)
   - Check if test modifies environment variables

### Test Fails with "Permission Denied"

If test fails accessing `/tmp/`:

1. Check `/tmp/` permissions: `ls -la /tmp/`
2. Check if `/tmp/` is full: `df -h /tmp/`
3. Try setting `TMPDIR`: `export TMPDIR=/var/tmp`

---

## CI/CD Integration

Tests automatically work in CI because:

1. Environment isolation is automatic
2. No user directories exist in CI
3. All paths use `/tmp/` or equivalent

**No special CI configuration needed!**

---

## FAQ

### Q: Do I need to do anything special in my tests?

**A:** No! Isolation is automatic. Just write normal tests.

### Q: Can I still test with real user directories?

**A:** Not recommended. If absolutely necessary, mark test with `@pytest.mark.no_isolation` (to be implemented).

### Q: What if I need to test migration from legacy paths?

**A:** Create the legacy structure in `tmp_path`:
```python
def test_legacy_migration(tmp_path):
    legacy_dir = tmp_path / "home" / ".timelocker"
    legacy_dir.mkdir(parents=True)
    # Test migration...
```

### Q: How do I test XDG variable handling?

**A:** Use `monkeypatch` to override specific variables:
```python
def test_custom_xdg_path(tmp_path, monkeypatch):
    custom_config = tmp_path / "custom_config"
    monkeypatch.setenv('XDG_CONFIG_HOME', str(custom_config))
    # Test...
```

---

## Related Documentation

- [Test Isolation Strategy](../architecture/test-isolation-strategy.md) - Full implementation details
- [File Locations Review](../architecture/file-locations-review.md) - Path analysis
- [Update Log](../updates/2025-11-09-test-isolation-and-xdg-compliance.md) - What changed

---

## Summary

✅ **Tests are automatically isolated**  
✅ **No user files can be modified**  
✅ **No special test code needed**  
✅ **Works in CI/CD automatically**  

Just write your tests normally and isolation happens automatically!
