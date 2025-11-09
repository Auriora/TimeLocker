---
title: "Architecture Decision Record: Path Review Summary"
id: "adr-path-review-summary"
type: [ architecture ]
status: accepted
owner: "Architecture Team"
last_reviewed: "09-11-2025"
tags: [ architecture, adr, xdg, summary, test-isolation ]
links:
    tooling: [ pytest ]
---

# Architecture Decision Record: Path Review Summary

- **Owner**: Architecture Team
- **Status**: Accepted
- **Created Date**: 09-11-2025
- **Last Updated**: 09-11-2025
- **Audience**: Engineering Teams, Stakeholders

## 1. Context

This document summarizes the review of all system and user file locations in TimeLocker for XDG Base Directory Specification compliance and test isolation safety.

## 2. Decision

Implement full XDG compliance with multi-phase rollout focusing on test isolation first, then path standardization, then enhancement.

### Key Findings

- ✅ Core path resolver is XDG-compliant
- ⚠️ 6 modules bypass the resolver with hardcoded paths
- ⚠️ Tests can currently modify real user files (CRITICAL RISK)
- ⚠️ Shell completions don't follow XDG standards

### Critical Issue: Test Isolation

**Problem:** Tests inherit user's actual XDG paths and can modify real configuration files.

**Risk Level:** HIGH - Tests could corrupt user data, credentials, or configuration.

**Solution:** Implement multi-layer test isolation:
1. Override XDG environment variables in test fixtures
2. Add test mode detection to path resolver
3. Always use explicit `config_dir` parameters in tests
4. Add automatic verification that no user files are created

## 3. Consequences

### Positive Outcomes

- **Safety**: Tests can never corrupt user data
- **Standards Compliance**: Full XDG compliance on Linux
- **Better Organization**: Clear separation of concerns
- **Reproducibility**: Tests run in clean, isolated environments

### Negative Consequences

- **Migration Required**: Existing users need path migration
- **Code Changes**: Multiple modules need updates
- **Testing Overhead**: All tests need explicit parameters
- **Documentation**: Extensive documentation updates needed

## 4. Alternatives Considered

### Option A: Minimal Changes (Test Isolation Only)

- Pros: Quick fix, addresses critical issue
- Cons: Doesn't solve XDG compliance, technical debt remains

### Option B: Full Rewrite

- Pros: Clean slate, perfect compliance
- Cons: High risk, long timeline, breaks existing installations

### Option C: Phased Approach (CHOSEN)

- Pros: Addresses critical issues first, manageable risk, incremental value
- Cons: Takes longer overall, requires coordination

## 5. Compliance Status

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

## 6. Recommended Directory Structure

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

## 7. Action Plan

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

# References

- [file-locations-review.md](./file-locations-review.md) - Detailed analysis
- [test-isolation-strategy.md](./test-isolation-strategy.md) - Implementation guide
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
