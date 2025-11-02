---
inclusion: fileMatch
fileMatchPattern: 'tests/**'
---

# Testing Conventions

**Priority**: 25  
**Scope**: tests/**  
**Description**: Standardized testing format and policy for all projects.

## Testing Guidelines

- **Test File Placement**: Always place tests next to the code they exercise when practical (e.g., `src/module/__tests__/` or `tests/module.test.py`).
- **Consistent Test File Naming**: Prefer `test_*.py` for Python projects following the existing project conventions.
- **Preferred Test Runner**: Use the repository's designated test runner (pytest for this project).

## Test Organization

- Unit tests for `src/TimeLocker/module.py` → `tests/TimeLocker/test_module.py` (follow repo convention)
- Integration tests that exercise multiple modules → `tests/TimeLocker/integration/test_feature-name.py`
- Place test utilities and fixtures in appropriate `conftest.py` files

## PR Checklist Additions

When making changes that affect tests, ensure the following are considered:

-   [ ] Added/updated unit tests for changed behavior
-   [ ] Added/updated minimal integration or smoke tests if public behavior changed
-   [ ] Verified all tests pass with the changes
-   [ ] Updated test documentation if test structure or approach changed

## Testing Best Practices

- Write tests that focus on behavior, not implementation details
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert pattern for test structure
- Mock external dependencies appropriately
- Ensure tests are deterministic and can run in any order