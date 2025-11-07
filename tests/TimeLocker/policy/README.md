# Policy Management Test Suite

This directory contains comprehensive tests for the TimeLocker policy management system.

## Test Coverage

### Unit Tests

#### PolicyValidator Tests (`test_validator.py`)
- **23 tests** covering validation logic for backup and retention policies
- Tests for required field validation
- Backup tool compatibility checking
- Repository compatibility validation
- Policy assignment validation
- Retention rule validation
- Schedule and compliance requirement validation

#### PolicyEngine Tests (`test_engine.py`)
- **17 tests** covering policy enforcement operations
- Retention rule evaluation with various retention types
- Snapshot pruning operations (dry-run and actual)
- Compliance validation
- Enforcement record creation and history tracking
- Error handling during enforcement

#### PolicyManager Tests (`test_manager.py`)
- **25 tests** covering policy management operations
- CRUD operations for backup and retention policies
- Policy assignment and unassignment
- Policy duplication and template creation
- Default policy application
- Effective policy resolution with priority handling
- Full policy lifecycle integration test

### Integration Tests (`test_integration.py`)
- **9 tests** covering component interactions
- Policy enforcement with different backup tools (restic, borg)
- Simulation accuracy verification
- Policy conflict resolution scenarios
- Error handling with invalid configurations
- Compliance period enforcement
- Policy template creation and reuse

### Performance Tests (`test_performance.py`)
- **8 tests** verifying performance characteristics
- Large-scale policy creation (100 policies)
- Large-scale policy assignment (100 assignments)
- Large snapshot retention evaluation (1000 snapshots)
- Policy lookup performance (500 policies)
- Assignment query performance (1000 assignments)
- Effective policy resolution performance
- Memory efficiency tests

## Test Statistics

- **Total Tests**: 82
- **Test Files**: 5
- **Test Classes**: 15
- **All Tests Passing**: ✓

## Running Tests

### Run all policy tests:
```bash
pytest tests/TimeLocker/policy/ -v
```

### Run specific test file:
```bash
pytest tests/TimeLocker/policy/test_validator.py -v
pytest tests/TimeLocker/policy/test_engine.py -v
pytest tests/TimeLocker/policy/test_manager.py -v
pytest tests/TimeLocker/policy/test_integration.py -v
pytest tests/TimeLocker/policy/test_performance.py -v
```

### Run with coverage:
```bash
pytest tests/TimeLocker/policy/ --cov=src/TimeLocker/policy --cov-report=html
```

### Run performance tests only:
```bash
pytest tests/TimeLocker/policy/test_performance.py -v
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:
- `sample_retention_rule`: Basic retention rule
- `sample_retention_policy`: Complete retention policy
- `sample_backup_policy`: Complete backup policy
- `sample_policy_assignment`: Policy assignment
- `mock_repository`: Mock backup repository
- `sample_snapshots`: Set of test snapshots
- `mock_repository_manager`: Mock repository manager
- `mock_config_manager`: Mock configuration manager
- `mock_policy_store`: Mock policy storage

## Test Categories

### Functional Tests
- Policy creation and validation
- Policy assignment and enforcement
- Retention rule evaluation
- Snapshot pruning operations

### Error Handling Tests
- Invalid policy configurations
- Missing required fields
- Incompatible backup tools
- Repository access issues

### Integration Tests
- Multi-component workflows
- Different backup tool compatibility
- Policy conflict resolution
- Compliance validation

### Performance Tests
- Large-scale operations
- Query performance
- Memory efficiency
- Enforcement speed

## Requirements Coverage

All requirements from the policy management specification are validated:

### Requirement 1 (Policy Creation)
- ✓ Backup policy creation with validation
- ✓ Retention policy creation with time-based rules
- ✓ Policy compatibility validation
- ✓ Policy templates and duplication
- ✓ Default retention policy application

### Requirement 2 (Policy Assignment and Enforcement)
- ✓ Policy assignment to repositories
- ✓ Assignment validation and compatibility checking
- ✓ Retention policy enforcement
- ✓ Snapshot pruning coordination
- ✓ Enforcement audit logging

### Requirement 3 (Validation and Preview)
- ✓ Policy configuration validation
- ✓ Repository existence and accessibility checks
- ✓ Policy preview capabilities (simulation)
- ✓ Retention policy compatibility validation
- ✓ Validation error reporting

### Requirement 4 (Audit and Monitoring)
- ✓ Enforcement record creation
- ✓ Enforcement history tracking
- ✓ Compliance status validation
- ✓ Policy status reporting
- ✓ Error logging and alerting

## Notes

- Tests use mocking to avoid dependencies on actual backup tools
- Performance tests verify operations complete within acceptable time limits
- Integration tests verify component interactions work correctly
- All tests follow the project's testing conventions and patterns
