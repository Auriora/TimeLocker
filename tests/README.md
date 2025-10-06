# TimeLocker Test Suite

This directory contains the comprehensive test suite for TimeLocker.

## Test Organization

```
tests/
├── TimeLocker/
│   ├── backup/          # Backup operation tests
│   ├── cli/             # CLI command tests
│   ├── config/          # Configuration management tests
│   ├── integration/     # Integration tests (including S3/MinIO)
│   ├── monitoring/      # Monitoring and notification tests
│   ├── performance/     # Performance and benchmark tests
│   ├── platform/        # Cross-platform compatibility tests
│   ├── recovery/        # Recovery and restore tests
│   ├── regression/      # Regression tests
│   ├── restic/          # Restic backend tests
│   ├── retention/       # Retention policy tests
│   └── security/        # Security and credential tests
└── README.md           # This file
```

## Test Types

### Unit Tests
Fast, isolated tests for individual components.

```bash
pytest -m unit
```

### Integration Tests
Tests that verify component interactions, including S3/MinIO integration.

```bash
pytest -m integration
```

### Network Tests
Tests requiring network access (e.g., S3/MinIO).

```bash
pytest -m network
```

### Performance Tests
Benchmark and performance tests.

```bash
pytest -m performance
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/TimeLocker/integration/test_s3_minio.py -v
```

### Specific Test Function
```bash
pytest tests/TimeLocker/integration/test_s3_minio.py::test_s3_backup_and_restore -v
```

### By Marker
```bash
# Integration tests only
pytest -m integration

# Unit tests only
pytest -m unit

# Exclude slow tests
pytest -m "not slow"

# Multiple markers
pytest -m "integration and network"
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
```

## S3/MinIO Integration Tests

### Setup

1. **Start MinIO**:
   ```bash
   ./scripts/setup_minio_test.sh
   ```

2. **Verify MinIO is running**:
   ```bash
   curl http://localhost:9000/minio/health/live
   ```

3. **Run S3 integration tests**:
   ```bash
   pytest tests/TimeLocker/integration/test_s3_minio.py -v
   ```

### Configuration

S3/MinIO tests use environment variables:

```bash
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export MINIO_BUCKET="timelocker-test"
export AWS_S3_ENDPOINT="http://localhost:9000"
```

Or use the `.env.test` file:

```bash
cp .env.test.example .env.test
# Edit .env.test as needed
source .env.test
```

### Cleanup

```bash
# Stop MinIO
docker-compose down

# Remove all data
docker-compose down -v
```

## Test Markers

Available pytest markers (defined in `pyproject.toml`):

- `unit` - Unit tests for individual components
- `integration` - Integration tests for component interactions
- `security` - Security-focused tests
- `performance` - Performance and benchmark tests
- `critical` - Critical path tests that must pass
- `slow` - Tests that take a long time to run
- `network` - Tests that require network access
- `filesystem` - Tests that interact with the filesystem
- `backup` - Tests related to backup operations
- `restore` - Tests related to restore operations
- `config` - Tests related to configuration management
- `monitoring` - Tests related to monitoring and notifications
- `e2e` - End-to-end validation tests
- `platform` - Cross-platform compatibility tests
- `regression` - Regression tests for previously fixed issues
- `stress` - Stress tests for high-load scenarios

## Writing Tests

### Test Structure

```python
import pytest
from TimeLocker.restic.Repositories.s3 import S3ResticRepository

@pytest.mark.integration
@pytest.mark.network
def test_s3_feature(s3_repository):
    """Test description."""
    # Arrange
    # ...
    
    # Act
    result = s3_repository.some_method()
    
    # Assert
    assert result is not None
```

### Fixtures

Common fixtures are defined in:
- `tests/TimeLocker/conftest.py` - Global fixtures
- `tests/TimeLocker/test_fixtures.py` - Enhanced fixtures
- Individual test files - Test-specific fixtures

### Best Practices

1. **Use descriptive test names**: `test_s3_backup_with_multiple_files`
2. **Add docstrings**: Explain what the test verifies
3. **Use appropriate markers**: Mark tests with relevant markers
4. **Clean up resources**: Use fixtures with teardown
5. **Isolate tests**: Each test should be independent
6. **Mock external dependencies**: For unit tests
7. **Use real services**: For integration tests (e.g., MinIO)

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Scheduled runs

See `.github/workflows/` for CI configuration.

## Troubleshooting

### Tests Skipped

If integration tests are skipped:

1. Check MinIO is running: `docker-compose ps`
2. Verify boto3 is installed: `pip install boto3`
3. Check network connectivity: `curl http://localhost:9000`

### Slow Tests

Run with parallel execution:

```bash
pytest -n auto
```

### Debug Mode

Run with verbose output and no capture:

```bash
pytest -vv -s
```

### Failed Tests

View detailed output:

```bash
pytest --tb=long
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [MinIO Testing Guide](../docs/MINIO_TESTING.md)
- [TimeLocker Documentation](../docs/)

