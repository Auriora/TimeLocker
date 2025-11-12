# CLI Testing Utilities

This module provides comprehensive testing utilities for CLI commands, including fixtures, mocks, test data generators, and assertion helpers.

## Overview

The testing utilities are designed to:
- Reduce code duplication in CLI tests
- Provide consistent test patterns across all CLI commands
- Simplify mock creation and configuration
- Generate realistic test data
- Offer specialized assertions for CLI testing

## Components

### Fixtures (`fixtures.py`)

Provides reusable test data structures and fixture factories.

```python
from TimeLocker.cli_modules.testing import (
    CLITestFixtures,
    create_test_repository,
    create_test_snapshot,
    create_test_target,
)

# Use the fixtures container
fixtures = CLITestFixtures()
repo = fixtures.get_test_repository()
snapshot = fixtures.get_test_snapshot()

# Or use factory functions directly
repo = create_test_repository(name="my-repo", backend="s3")
snapshot = create_test_snapshot(snapshot_id="abc123", repository="my-repo")
```

### Mocks (`mocks.py`)

Factory functions for creating properly configured mock services.

```python
from TimeLocker.cli_modules.testing import (
    MockServiceFactory,
    create_mock_service_manager,
    create_mock_config_service,
)

# Use the factory class
factory = MockServiceFactory()
service_manager = factory.create_service_manager(
    repositories=[repo1, repo2],
    snapshots=[snap1, snap2]
)

# Or use factory functions directly
service_manager = create_mock_service_manager()
config_service = create_mock_config_service(config={'version': '1.0'})
```

### Generators (`generators.py`)

Generate realistic test data for various scenarios.

```python
from TimeLocker.cli_modules.testing import (
    TestDataGenerator,
    generate_snapshot_data,
    generate_repository_data,
)

# Use the generator class
generator = TestDataGenerator(seed=42)  # Reproducible data
snapshots = generator.generate_snapshots(count=10, repository="test-repo")
repositories = generator.generate_repositories(count=5, backend="local")

# Or use generator functions directly
snapshot = generate_snapshot_data(repository="my-repo")
repository = generate_repository_data(name="my-repo", backend="s3")
```

### Assertions (`assertions.py`)

Specialized assertion functions for CLI testing.

```python
from TimeLocker.cli_modules.testing import (
    CLIAssertions,
    assert_cli_success,
    assert_cli_output_contains,
    assert_service_called,
)

# Use the assertions class
assertions = CLIAssertions()
assertions.assert_success(result)
assertions.assert_output_contains(result, "Success")
assertions.assert_service_called(mock_service, "list_repositories")

# Or use assertion functions directly
assert_cli_success(result)
assert_cli_output_contains(result, "Success", case_sensitive=False)
assert_service_called(mock_service, "list_repositories", times=1)
```

### Runners (`runners.py`)

Enhanced CLI test runners with additional features.

```python
from TimeLocker.cli_modules.testing import (
    CLITestRunner,
    get_test_runner,
    run_cli_command,
)

# Use the runner class
runner = CLITestRunner(columns=200)
result = runner.invoke(app, ["repos", "list"])
result = runner.invoke_interactive(app, ["repos", "add"], inputs=["name", "uri"])

# Or use convenience functions
runner = get_test_runner()
exit_code, output = run_cli_command(app, ["repos", "list"])
```

## Usage Examples

### Basic Test with Fixtures and Assertions

```python
import pytest
from TimeLocker.cli import app
from TimeLocker.cli_modules.testing import (
    get_test_runner,
    create_test_repository,
    assert_cli_success,
    assert_cli_output_contains,
)

def test_repos_list():
    """Test repos list command."""
    runner = get_test_runner()
    result = runner.invoke(app, ["repos", "list"])
    
    assert_cli_success(result)
    assert_cli_output_contains(result, "repositories")
```

### Test with Mock Services

```python
import pytest
from unittest.mock import patch
from TimeLocker.cli import app
from TimeLocker.cli_modules.testing import (
    get_test_runner,
    create_mock_service_manager,
    create_test_repository,
    assert_cli_success,
    assert_service_called,
)

@patch('TimeLocker.cli.get_cli_service_manager')
def test_repos_add(mock_get_manager):
    """Test repos add command."""
    # Setup mock
    repo = create_test_repository(name="test-repo")
    mock_manager = create_mock_service_manager(repositories=[repo])
    mock_get_manager.return_value = mock_manager
    
    # Run command
    runner = get_test_runner()
    result = runner.invoke(app, [
        "repos", "add", "test-repo", "file:///tmp/test-repo"
    ])
    
    # Assertions
    assert_cli_success(result)
    assert_service_called(mock_manager, "add_repository", times=1)
```

### Test with Generated Data

```python
import pytest
from TimeLocker.cli_modules.testing import (
    TestDataGenerator,
    get_test_runner,
    assert_cli_success,
)

def test_snapshots_list_many():
    """Test listing many snapshots."""
    # Generate test data
    generator = TestDataGenerator(seed=42)
    snapshots = generator.generate_snapshots(count=100, repository="test-repo")
    
    # Setup mock with generated data
    mock_manager = create_mock_service_manager(snapshots=snapshots)
    
    # Test command handles large dataset
    runner = get_test_runner()
    result = runner.invoke(app, ["snapshots", "list", "test-repo"])
    
    assert_cli_success(result)
```

### Test with Interactive Input

```python
import pytest
from TimeLocker.cli_modules.testing import (
    get_test_runner,
    assert_cli_success,
)

def test_repos_add_interactive():
    """Test repos add with interactive prompts."""
    runner = get_test_runner()
    
    # Provide inputs for prompts
    result = runner.invoke_interactive(
        app,
        ["repos", "add"],
        inputs=["test-repo", "file:///tmp/test-repo", "Test description"]
    )
    
    assert_cli_success(result)
```

## Best Practices

1. **Use Fixtures for Consistency**: Always use the provided fixtures instead of creating test data manually.

2. **Mock at the Right Level**: Mock service managers and services, not internal implementation details.

3. **Generate Realistic Data**: Use the data generators for tests that need realistic or large datasets.

4. **Use Specialized Assertions**: Use the CLI-specific assertions instead of generic assert statements.

5. **Isolate Tests**: Use the test runner's environment isolation features to prevent test interference.

6. **Test Both Success and Failure**: Test both successful operations and error conditions.

## Integration with Existing Tests

The testing utilities are designed to work alongside existing test patterns. You can gradually migrate tests to use these utilities:

```python
# Old pattern
from tests.TimeLocker.cli.test_utils import get_cli_runner, assert_success

# New pattern (compatible)
from TimeLocker.cli_modules.testing import get_test_runner, assert_cli_success

# Both work the same way
runner = get_test_runner()  # or get_cli_runner()
result = runner.invoke(app, ["repos", "list"])
assert_cli_success(result)  # or assert_success(result)
```

## Contributing

When adding new testing utilities:

1. Follow the existing patterns and naming conventions
2. Add comprehensive docstrings
3. Include usage examples in docstrings
4. Update this README with new utilities
5. Add tests for the utilities themselves

## See Also

- [CLI Refactoring Design](../../../../.kiro/specs/cli-refactoring/design.md)
- [CLI Refactoring Tasks](../../../../.kiro/specs/cli-refactoring/tasks.md)
- [Existing Test Utils](../../../../tests/TimeLocker/cli/test_utils.py)
