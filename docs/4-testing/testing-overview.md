# Testing Guide

This document provides comprehensive guidance for testing the TimeLocker project, including testing approaches, frameworks, and best practices.

## Testing Documentation Structure

The TimeLocker testing documentation consists of the following components:

1. **Testing Guide** (this document): Provides an overview of testing approaches, frameworks, and best practices for the TimeLocker project.

2. **[Test Plan](timelocker-test-plan.md)**: Outlines the testing strategy, objectives, scope, and resource requirements for the TimeLocker project.

3. **Test Cases**: Detailed test cases for each functional area of the application:
    - [Repository Management Test Cases](repository-management-test-cases.md)
    - [Backup Operations Test Cases](backup-operations-test-cases.md)
    - [Recovery Operations Test Cases](recovery-operations-test-cases.md)
    - [Security Operations Test Cases](security-operations-test-cases.md)

4**Acceptance Tests**: Behavior-driven development (BDD) style acceptance tests for each functional area:

- [Repository Management](RepositoryManagement.t.md)
- [Backup Operations](BackupOperations.t.md)
- [Recovery Operations](RecoveryOperations.t.md)
- [Security Operations](SecurityOperations.t.md)

5. **[Test Results](timelocker-test-results.md)**: Documents the results of test execution, including defects found and recommendations.

### How to Use This Documentation

- **For Developers**: Start with the Testing Guide to understand the testing approach, then refer to the Test Cases and Acceptance Tests for detailed
  requirements.
- **For QA Engineers**: Use the Test Plan to understand the testing strategy, then execute the Test Cases and document results in the Test Results.
- **For Project Managers**: Review the Test Plan and Test Results to track testing progress and quality metrics.
- **For New Team Members**: Begin with the Testing Guide to get an overview, then explore other documents as needed for your role.

## Testing Overview

TimeLocker uses a multi-layered testing approach to ensure code quality and functionality:

- **Unit Testing**: Tests individual components in isolation
- **Integration Testing**: Tests interactions between components
- **Functional Testing**: Tests complete features from a user perspective
- **Performance Testing**: Tests system performance under various conditions
- **Security Testing**: Tests for security vulnerabilities

## Testing Framework

TimeLocker uses pytest as its primary testing framework:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/TimeLocker/backup/test_backup_manager.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src
```

## Test Structure

Tests are organized to mirror the source code structure:

```
tests/
├── TimeLocker/           # Tests for main package
│   ├── backup/           # Tests for backup functionality
│   ├── command_builder/  # Tests for command-line builder utilities
│   ├── restic/           # Tests for Restic-specific implementations
│   └── conftest.py       # Common test fixtures
├── json2command_definition/ # Tests for JSON converter
└── man2json/             # Tests for man page converter
```

## Writing Tests

### Test File Naming

Test files should be named with a `test_` prefix followed by the name of the module being tested:

```
test_backup_manager.py  # Tests for backup_manager.py
test_file_selections.py # Tests for file_selections.py
```

### Test Function Naming

Test functions should be named descriptively to indicate what they're testing:

```python
def test_backup_creation_with_valid_parameters():
    # Test code here

def test_backup_fails_with_invalid_path():
    # Test code here
```

### Test Fixtures

Common test fixtures are defined in `conftest.py` files:

```python
@pytest.fixture
def selection():
    return FileSelection()

@pytest.fixture
def test_dir():
    test_dir = Mock(spec=Path)
    test_dir.is_dir.return_value = True
    test_dir.__str__ = lambda x: "/test/dir"
    return test_dir
```

### Mocking

Use the `unittest.mock` module for mocking dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mocked_dependency():
    with patch('module.dependency') as mock_dep:
        mock_dep.return_value = 'mocked result'
        # Test code here
```

## Test Coverage

Aim for high test coverage, especially for critical components:

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Continuous Integration

Tests are automatically run on each commit through the CI pipeline:

1. **Linting**: Checks code style and quality
2. **Unit Tests**: Runs all unit tests
3. **Integration Tests**: Runs integration tests
4. **Coverage Report**: Generates and archives test coverage report

## Test-Driven Development

TimeLocker encourages test-driven development (TDD):

1. Write a failing test for the functionality you want to implement
2. Implement the minimum code needed to make the test pass
3. Refactor the code while keeping the tests passing

## Testing Best Practices

1. **Isolation**: Tests should be independent and not rely on the state from other tests
2. **Deterministic**: Tests should produce the same results each time they run
3. **Fast**: Tests should run quickly to encourage frequent testing
4. **Readable**: Tests should be easy to understand and maintain
5. **Comprehensive**: Tests should cover normal cases, edge cases, and error conditions

## Acceptance Testing

Acceptance tests verify that the system meets the requirements specified in the SRS:

1. Each requirement should have at least one acceptance test
2. Acceptance tests should be written from a user perspective
3. Acceptance tests should verify both functional and non-functional requirements

### Acceptance Test Structure

TimeLocker's acceptance tests are organized in a behavior-driven development (BDD) style format and stored in the `Writerside/topics/testing/` directory. Each
file represents a functional area of the application:

- **BackupOperations.t.md**: Tests for backup creation, validation, scheduling, and error handling
- **RecoveryOperations.t.md**: Tests for snapshot restoration, partial recovery, conflict resolution, and error handling
- **RepositoryManagement.t.md**: Tests for repository registration, GDPR compliance, editing, and removal
- **SecurityOperations.t.md**: Tests for personal data export, erasure, and security-related error handling

### Test Organization

Each acceptance test file follows a consistent structure:

1. **Test Suites (S1, S2, etc.)**: Logical groupings of related test cases
2. **Test Cases (C1, C2, etc.)**: Individual scenarios to test specific functionality
3. **Tags**: Metadata for categorizing and filtering tests
4. **Steps**: Detailed sequence of actions and verification points

Example test case format:

```
* C1 Create Full Backup
Tags: full-backup, basic
    * Open TimeLocker application
    * Select a configured repository
    * Click "Create Backup" button
    * ...
    * Verify backup completes successfully
    * Verify snapshot is created in the repository
```

### Running Acceptance Tests

Acceptance tests can be executed using the dedicated test runner:

```bash
# Run all acceptance tests
pytest tests/acceptance

# Run tests for a specific functional area
pytest tests/acceptance/test_backup_operations.py

# Run tests with specific tags
pytest tests/acceptance -m "basic or critical"
```

### Acceptance Test Coverage

The current acceptance test suite covers the following key functional areas:

1. **Backup Operations**:
    - Manual backup creation (full and incremental)
    - Backup validation and integrity checking
    - Scheduled backups
    - Error handling during backup

2. **Recovery Operations**:
    - Full snapshot restoration
    - Partial file and folder recovery
    - Conflict resolution (overwrite, rename, skip)
    - Error handling during recovery

3. **Repository Management**:
    - Repository registration for different storage backends
    - GDPR region compliance
    - Repository configuration editing
    - Repository removal

4. **Security Operations**:
    - Personal data export (GDPR data portability)
    - Personal data erasure (right to be forgotten)
    - Security-related error handling

## Performance Testing

Performance tests verify that the system meets performance requirements:

1. **Load Testing**: Tests system behavior under normal and peak loads
2. **Stress Testing**: Tests system behavior under extreme conditions
3. **Endurance Testing**: Tests system behavior over extended periods

## Security Testing

Security tests verify that the system is secure:

1. **Vulnerability Scanning**: Identifies known vulnerabilities
2. **Penetration Testing**: Attempts to exploit vulnerabilities
3. **Security Code Review**: Reviews code for security issues

## Conclusion

Testing is a critical part of the TimeLocker development process. By following these guidelines, we can ensure that TimeLocker is reliable, secure, and meets
all requirements.
