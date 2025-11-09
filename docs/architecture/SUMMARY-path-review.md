# Path Review Summary

**Date:** 2025-11-09  
**Reviewer:** AI Assistant  
**Status:** Review Complete - Action Required

---

## Executive Summary

Reviewed all system and user file locations in TimeLocker for XDG Base Directory Specification compliance and test isolation safety.

**Key Findings:**
- ✅ Core path resolver is XDG-compliant
- ⚠️ 6 modules bypass the resolver with hardcoded paths
- ⚠️ Tests can currently modify real user files (CRITICAL RISK)
- ⚠️ Shell completions don't follow XDG standards

---

## Critical Issue: Test Isolation

**Problem:** Tests inherit user's actual XDG paths and can modify real configuration files.

**Risk Level:** HIGH - Tests could corrupt user data, credentials, or configuration.

**Solution:** Implement multi-layer test isolation:
1. Override XDG environment variables in test fixtures
2. Add test mode detection to path resolver
3. Always use explicit `config_dir` parameters in tests
4. Add automatic verification that no user files are created

**See:** [Test Isolation Strategy](./test-isolation-strategy.md)

---

## Compliance Status

### ✅ Compliant Components

| Component | Status | Notes |
|-----------|--------|-------|
| `ConfigurationPathResolver` | ✅ Compliant | Correctly uses XDG variables |
| `platform_compat.py` | ✅ Compliant | Proper platform-specific paths |
| Core config paths | ✅ Compliant | `~/.config/timelocker/` |
| Cache paths | ✅ Compliant | `~/.cache/timelocker/` |
| Runtime paths | ✅ Compliant | `$XDG_RUNTIME_DIR/timelocker/` |

### ⚠️ Non-Compliant Components

| Component | Issue | Impact | Priority |
|-----------|-------|--------|----------|
| `selection_template_manager.py` | Hardcoded `~/.config/timelocker` | Ignores `XDG_CONFIG_HOME` | High |
| `notification_service.py` | Uses legacy `~/.timelocker/` | Wrong location | High |
| `status_reporter.py` | Uses legacy `~/.timelocker/` | Wrong location | High |
| `credential_manager.py` | Uses legacy `~/.timelocker/` | Wrong location | High |
| `pattern_group_manager.py` | Uses legacy `~/.timelocker/` | Wrong location | High |
| `backup_notification_service.py` | Uses legacy `~/.timelocker/` | Wrong location | High |
| Shell completions (bash/zsh) | Uses `~/` instead of XDG | Wrong location | Medium |

---

## Recommended Directory Structure

### Current (Mixed)
```
~/.timelocker/                    # LEGACY - being used by some modules
~/.config/timelocker/             # CORRECT - used by core
~/.cache/timelocker/              # CORRECT
```

### Proposed (XDG Compliant)
```
~/.config/timelocker/             # XDG_CONFIG_HOME - configuration
~/.local/share/timelocker/        # XDG_DATA_HOME - templates, data
~/.local/state/timelocker/        # XDG_STATE_HOME - logs, state
~/.cache/timelocker/              # XDG_CACHE_HOME - cache
/run/user/$UID/timelocker/        # XDG_RUNTIME_DIR - runtime files
```

---

## Action Plan

### Phase 1: Test Safety (CRITICAL - Do First)
**Timeline:** 1-2 days

1. Update `test_fixtures.py` to override XDG variables
2. Add `TIMELOCKER_TEST_MODE` environment variable
3. Add test mode detection to `ConfigurationPathResolver`
4. Add verification fixture to ensure no user files created
5. Run test suite to verify isolation

**Why First:** Prevents tests from corrupting user data during development.

### Phase 2: Fix Hardcoded Paths
**Timeline:** 2-3 days

1. Update 6 modules to use `ConfigurationPathResolver`
2. Add backward compatibility for legacy paths
3. Update tests to use explicit `config_dir` parameters
4. Verify all tests pass

### Phase 3: XDG Enhancement
**Timeline:** 3-5 days

1. Add `XDG_STATE_HOME` support for logs
2. Add `XDG_DATA_HOME` support for templates
3. Update shell completion paths
4. Create migration script for legacy paths
5. Update documentation

### Phase 4: Validation
**Timeline:** 1-2 days

1. Test on Linux with custom XDG variables
2. Test on macOS and Windows
3. Add CI checks for path isolation
4. Update user documentation

---

## Quick Fixes

### For Immediate Test Safety

Add to `tests/TimeLocker/test_fixtures.py`:

```python
@pytest.fixture(autouse=True)
def isolate_environment(resource_manager, tmp_path):
    """Isolate test environment - prevents touching user files"""
    test_env = {
        'XDG_CONFIG_HOME': str(tmp_path / "config"),
        'XDG_DATA_HOME': str(tmp_path / "data"),
        'XDG_CACHE_HOME': str(tmp_path / "cache"),
        'XDG_STATE_HOME': str(tmp_path / "state"),
        'HOME': str(tmp_path / "home"),
        'TIMELOCKER_TEST_MODE': '1',
    }
    
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value
```

### For Path Resolver

Add to `src/TimeLocker/config/configuration_path_resolver.py`:

```python
@staticmethod
def is_test_mode() -> bool:
    """Check if running in test mode."""
    return os.environ.get('TIMELOCKER_TEST_MODE') == '1'

@staticmethod
def get_config_directory() -> Path:
    """Get appropriate configuration directory based on context."""
    # Test mode override
    if ConfigurationPathResolver.is_test_mode():
        test_config = os.environ.get('TIMELOCKER_CONFIG_DIR')
        if test_config:
            return Path(test_config)
    
    # ... rest of existing code
```

---

## Documentation

Created:
- ✅ `docs/architecture/file-locations-review.md` - Complete path analysis
- ✅ `docs/architecture/test-isolation-strategy.md` - Test isolation implementation
- ✅ `docs/architecture/SUMMARY-path-review.md` - This summary

---

## Next Steps

1. **Review this summary** with the team
2. **Prioritize test isolation** - implement Phase 1 immediately
3. **Create GitHub issues** for each phase
4. **Assign owners** for each component update
5. **Set timeline** for completion

---

## Questions to Consider

1. Should we maintain backward compatibility with `~/.timelocker/`?
2. When should we migrate existing user installations?
3. Should we add a configuration option to override paths?
4. How do we handle the shell completion file migration?

---

## References

- [file-locations-review.md](./file-locations-review.md) - Detailed analysis
- [test-isolation-strategy.md](./test-isolation-strategy.md) - Implementation guide
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
