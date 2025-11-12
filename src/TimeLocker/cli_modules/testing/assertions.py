"""
Assertion helpers for CLI command testing.

Provides specialized assertion functions for validating CLI command
behavior, output, and service interactions.
"""

from typing import Any, Optional, List
from unittest.mock import Mock


class CLIAssertions:
    """
    Collection of assertion helpers for CLI testing.
    
    This class provides methods for common CLI test assertions,
    making tests more readable and maintainable.
    """
    
    @staticmethod
    def assert_success(result, message: Optional[str] = None):
        """Assert command succeeded with exit code 0."""
        assert_cli_success(result, message)
    
    @staticmethod
    def assert_error(result, exit_code: int = 1, message: Optional[str] = None):
        """Assert command failed with specific exit code."""
        assert_cli_error(result, exit_code, message)
    
    @staticmethod
    def assert_output_contains(result, expected: str, case_sensitive: bool = False):
        """Assert output contains expected text."""
        assert_cli_output_contains(result, expected, case_sensitive)
    
    @staticmethod
    def assert_output_not_contains(result, unexpected: str, case_sensitive: bool = False):
        """Assert output does not contain unexpected text."""
        output = _get_combined_output(result)
        if not case_sensitive:
            output = output.lower()
            unexpected = unexpected.lower()
        
        if unexpected in output:
            raise AssertionError(
                f"Unexpected text '{unexpected}' found in output:\n{output}"
            )
    
    @staticmethod
    def assert_help_quality(result, command_name: str):
        """Assert help output meets quality standards."""
        assert_cli_help_quality(result, command_name)
    
    @staticmethod
    def assert_service_called(mock_service: Mock, method_name: str, times: Optional[int] = None):
        """Assert service method was called."""
        assert_service_called(mock_service, method_name, times)
    
    @staticmethod
    def assert_service_not_called(mock_service: Mock, method_name: str):
        """Assert service method was not called."""
        assert_service_not_called(mock_service, method_name)
    
    @staticmethod
    def assert_service_called_with(
        mock_service: Mock,
        method_name: str,
        *args,
        **kwargs
    ):
        """Assert service method was called with specific arguments."""
        method = getattr(mock_service, method_name)
        method.assert_called_with(*args, **kwargs)
    
    @staticmethod
    def assert_json_output(result, expected_keys: Optional[List[str]] = None):
        """Assert output is valid JSON with expected keys."""
        import json
        
        output = _get_combined_output(result)
        
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Output is not valid JSON: {e}\nOutput: {output}")
        
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    raise AssertionError(
                        f"Expected key '{key}' not found in JSON output:\n{data}"
                    )
        
        return data


def assert_cli_success(result, message: Optional[str] = None):
    """
    Assert CLI command succeeded with exit code 0.
    
    Args:
        result: CliRunner result object
        message: Optional custom error message
    
    Raises:
        AssertionError: If exit code is not 0
    """
    if result.exit_code != 0:
        output = _get_combined_output(result)
        error_msg = (
            f"Expected exit code 0, got {result.exit_code}\n"
            f"Output: {output}"
        )
        if message:
            error_msg = f"{message}\n{error_msg}"
        
        # Include exception info if available
        if hasattr(result, 'exception') and result.exception:
            error_msg += f"\nException: {result.exception}"
        
        raise AssertionError(error_msg)


def assert_cli_error(
    result,
    exit_code: int = 1,
    message: Optional[str] = None
):
    """
    Assert CLI command failed with specific exit code.
    
    Args:
        result: CliRunner result object
        exit_code: Expected exit code (default: 1)
        message: Optional custom error message
    
    Raises:
        AssertionError: If exit code doesn't match expected
    """
    if result.exit_code != exit_code:
        output = _get_combined_output(result)
        error_msg = (
            f"Expected exit code {exit_code}, got {result.exit_code}\n"
            f"Output: {output}"
        )
        if message:
            error_msg = f"{message}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_cli_output_contains(
    result,
    expected: str,
    case_sensitive: bool = False
):
    """
    Assert CLI output contains expected text.
    
    Args:
        result: CliRunner result object
        expected: Text that should be in output
        case_sensitive: Whether to perform case-sensitive matching
    
    Raises:
        AssertionError: If expected text not found in output
    """
    output = _get_combined_output(result)
    
    if not case_sensitive:
        output = output.lower()
        expected = expected.lower()
    
    if expected not in output:
        raise AssertionError(
            f"Expected text '{expected}' not found in output:\n{output}"
        )


def assert_cli_help_quality(result, command_name: str):
    """
    Assert CLI help output meets quality standards.
    
    Args:
        result: CliRunner result object from --help command
        command_name: Name of the command being tested
    
    Raises:
        AssertionError: If help output doesn't meet quality standards
    """
    # Help should succeed
    assert_cli_success(result, f"Help for '{command_name}' should succeed")
    
    output = _get_combined_output(result)
    
    # Check for basic help structure
    if "Usage:" not in output:
        raise AssertionError(f"Help for '{command_name}' should show usage")
    
    if "Options" not in output and "Arguments" not in output:
        raise AssertionError(
            f"Help for '{command_name}' should show options/arguments"
        )
    
    # Check for substantial content
    if len(output.strip()) <= 50:
        raise AssertionError(
            f"Help for '{command_name}' should be substantial (got {len(output)} chars)"
        )
    
    # Check that help doesn't contain error indicators
    error_indicators = ["error", "failed", "exception", "traceback"]
    output_lower = output.lower()
    for indicator in error_indicators:
        if indicator in output_lower:
            raise AssertionError(
                f"Help for '{command_name}' should not contain '{indicator}'"
            )


def assert_service_called(
    mock_service: Mock,
    method_name: str,
    times: Optional[int] = None
):
    """
    Assert service method was called.
    
    Args:
        mock_service: Mock service object
        method_name: Name of the method to check
        times: Expected number of calls (None = at least once)
    
    Raises:
        AssertionError: If method was not called as expected
    """
    if not hasattr(mock_service, method_name):
        raise AssertionError(
            f"Service does not have method '{method_name}'"
        )
    
    method = getattr(mock_service, method_name)
    
    if times is None:
        # Check called at least once
        if not method.called:
            raise AssertionError(
                f"Service method '{method_name}' was not called"
            )
    else:
        # Check called exact number of times
        actual_calls = method.call_count
        if actual_calls != times:
            raise AssertionError(
                f"Service method '{method_name}' was called {actual_calls} times, "
                f"expected {times}"
            )


def assert_service_not_called(mock_service: Mock, method_name: str):
    """
    Assert service method was not called.
    
    Args:
        mock_service: Mock service object
        method_name: Name of the method to check
    
    Raises:
        AssertionError: If method was called
    """
    if not hasattr(mock_service, method_name):
        # Method doesn't exist, so it wasn't called
        return
    
    method = getattr(mock_service, method_name)
    
    if method.called:
        raise AssertionError(
            f"Service method '{method_name}' was called {method.call_count} times, "
            f"expected 0"
        )


def assert_exit_code_in_range(
    result,
    valid_codes: List[int],
    message: Optional[str] = None
):
    """
    Assert CLI exit code is in valid range.
    
    Useful for commands that may have multiple valid exit codes
    depending on configuration or environment.
    
    Args:
        result: CliRunner result object
        valid_codes: List of valid exit codes
        message: Optional custom error message
    
    Raises:
        AssertionError: If exit code not in valid range
    """
    if result.exit_code not in valid_codes:
        output = _get_combined_output(result)
        error_msg = (
            f"Expected exit code in {valid_codes}, got {result.exit_code}\n"
            f"Output: {output}"
        )
        if message:
            error_msg = f"{message}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_output_matches_pattern(
    result,
    pattern: str,
    case_sensitive: bool = False
):
    """
    Assert CLI output matches regex pattern.
    
    Args:
        result: CliRunner result object
        pattern: Regex pattern to match
        case_sensitive: Whether to perform case-sensitive matching
    
    Raises:
        AssertionError: If output doesn't match pattern
    """
    import re
    
    output = _get_combined_output(result)
    
    flags = 0 if case_sensitive else re.IGNORECASE
    
    if not re.search(pattern, output, flags):
        raise AssertionError(
            f"Output does not match pattern '{pattern}':\n{output}"
        )


def _get_combined_output(result) -> str:
    """
    Get combined stdout and stderr from CLI result.
    
    Args:
        result: CliRunner result object
    
    Returns:
        Combined output string
    """
    stdout = result.stdout or ""
    stderr = getattr(result, "stderr", "") or ""
    return stdout + "\n" + stderr
