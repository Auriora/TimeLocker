# Test Fixes - Master Index

This directory contains prompts and documentation for fixing the remaining test failures in the TimeLocker project.

## Current Test Status

**Total Tests:** 1,727  
**Passing:** 1,629 (94.3%)  
**Failing:** 84 (4.9%)  
**Skipped:** 8 (0.5%)  
**Errors:** 6 (0.3%)

## Available Fix Prompts

Each prompt file contains both a detailed version and a shorter version for starting a new conversation.

### 1. Configuration Tests (13 failures)
**File:** `PROMPT-fix-configuration-tests.md`  
**Priority:** HIGH - Affects core functionality  
**Effort:** Medium-High  
**Impact:** +13 passing tests

**Summary:** Fix TypeError and AttributeError issues in configuration model tests.

**Key Issues:**
- `BackupConfig.__init__()` unexpected keyword arguments
- `GeneralConfig.__init__()` unexpected keyword arguments
- Serialization format mismatches
- Count/limit expectation mismatches

---

### 4. Store Backend Credentials (3 failures)
**File:** `PROMPT-fix-store-credentials-tests.md`  
**Priority:** MEDIUM - Credential management  
**Effort:** Low-Medium  
**Impact:** +3 passing tests

**Summary:** Fix NoneType errors and exception handling in credential storage tests.

**Key Issues:**
- `TypeError: 'NoneType' object is not subscriptable`
- Exit code mismatch in exception handling
- Missing credential manager initialization

---

### 5. Integration/Backend Tests (11 failures/errors)
**File:** `PROMPT-fix-integration-backend-tests.md`  
**Priority:** LOW - External dependencies  
**Effort:** Low (mostly skipping)  
**Impact:** +5 passing tests, 6 properly skipped

**Summary:** Fix multi-backend tests and handle MinIO dependency.

**Key Issues:**
- RepositoryAlreadyExistsError (need cleanup)
- Mock AttributeError
- MinIO not available (should skip gracefully)

---

## Recommended Fix Order

### Phase 1: Quick Wins (25 tests, ~2-4 hours)
1. **Targets → Selections** (22 tests) - Straightforward renaming
2. **Store Credentials** (3 tests) - Simple null checks

### Phase 2: Core Functionality (13 tests, ~3-5 hours)
3. **Configuration Tests** (13 tests) - Important for system stability

### Phase 3: Complex Issues (5 tests, ~4-6 hours)
4. **CLI Integration** (5 tests) - Complex mocking, may need rewrites

### Phase 4: External Dependencies (11 tests, ~1-2 hours)
5. **Integration/Backend** (11 tests) - Mostly adding skip decorators

## Expected Results

After completing all fixes:

| Phase | Tests Fixed | New Pass Rate | Cumulative |
|-------|-------------|---------------|------------|
| Current | - | 94.3% | 1,629/1,727 |
| Phase 1 | +25 | 95.8% | 1,654/1,727 |
| Phase 2 | +13 | 96.5% | 1,667/1,727 |
| Phase 3 | +5 | 96.8% | 1,672/1,727 |
| Phase 4 | +5 | 97.1% | 1,677/1,727 |
| **Final** | **+48** | **97.1%** | **1,677/1,727** |

*Note: 6 MinIO tests will be properly skipped, not counted as failures*

## How to Use These Prompts

1. **Choose a prompt file** based on priority and available time
2. **Open the file** and copy either:
   - The detailed prompt (recommended for thorough work)
   - The shorter prompt (for quick iteration)
3. **Start a new conversation** with the AI assistant
4. **Paste the prompt** to begin working on that specific set of tests
5. **Follow the investigation steps** and implement fixes
6. **Run tests** to verify fixes work
7. **Move to next prompt** once tests pass

## Additional Resources

### Technical Documentation
- Project test suite: `tests/TimeLocker/`
- Test utilities: `tests/TimeLocker/cli/test_utils.py`

### Running Tests

```bash
# Run all tests
pytest tests/TimeLocker/ -v

# Run specific category
pytest tests/TimeLocker/cli/test_selections_commands.py -v
pytest tests/TimeLocker/config/ -v
pytest tests/TimeLocker/integration/ -v

# Run without stopping on failures
pytest tests/TimeLocker/ --maxfail=1000 -q

# Get test count
pytest tests/TimeLocker/ --co -q | tail -3
```

### Test Markers

```bash
# Skip MinIO tests
pytest -m "not minio"

# Run only unit tests
pytest -m "unit"

# Run only integration tests
pytest -m "integration"
```

## Contributing

When fixing tests:

1. **Document changes** - Update this README if you complete a category
2. **Commit logically** - One commit per test file or logical group
3. **Update status** - Mark completed prompts in this file
4. **Add notes** - Document any unexpected issues or solutions

## Status Tracking

- [ ] Targets → Selections (22 tests)
- [ ] CLI Integration (5 tests)
- [ ] Configuration (13 tests)
- [ ] Store Credentials (3 tests)
- [ ] Integration/Backend (11 tests)

## Notes

- Some tests may be interdependent - fixing one category might affect others
- Always run full test suite after major changes
- Consider running tests in parallel: `pytest -n auto`
- Keep test execution time reasonable (< 5 minutes for full suite)

## Questions or Issues?

If you encounter issues not covered in the prompts:
1. Check test output carefully for error messages
2. Review recent changes to related source files
3. Check if there are migration guides in `docs/`
4. Consider asking for help with specific error messages

---

Last Updated: 2025-11-08  
Test Suite Version: 1,727 tests  
Pass Rate: 94.3% → Target: 97.1%
