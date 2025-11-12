"""
Async test helpers for handling coroutines in tests.

This module provides utilities for working with async functions in tests,
including awaiting coroutines, creating async-compatible mocks, and detecting
unawaited coroutines.
"""

import asyncio
import inspect
from typing import Any
from unittest.mock import Mock


def await_if_coroutine(result: Any) -> Any:
    """
    Await result if it's a coroutine, otherwise return as-is.
    
    This is useful for tests that may call both sync and async functions
    and need to handle the result uniformly.
    
    Args:
        result: The value to check and potentially await.
        
    Returns:
        The awaited result if it was a coroutine, otherwise the original value.
        
    Example:
        >>> result = await_if_coroutine(some_function())
        >>> assert result == expected_value
    """
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result


def make_async_mock(return_value: Any) -> Mock:
    """
    Create a mock that returns an awaitable.
    
    This creates a mock object whose return value is a coroutine that
    resolves to the specified value. Useful for mocking async functions.
    
    Args:
        return_value: The value the async mock should return when awaited.
        
    Returns:
        A Mock object configured to return an awaitable.
        
    Example:
        >>> mock_service = Mock()
        >>> mock_service.async_method = make_async_mock({'success': True})
        >>> result = await mock_service.async_method()
        >>> assert result == {'success': True}
    """
    async def async_return():
        return return_value
    
    mock = Mock()
    mock.return_value = async_return()
    return mock


def assert_not_coroutine(value: Any, message: str = "") -> None:
    """
    Assert that a value is not an unawaited coroutine.
    
    This helps catch common async mistakes in tests where a coroutine
    is returned but not awaited, leading to confusing test failures.
    
    Args:
        value: The value to check.
        message: Optional custom error message prefix.
        
    Raises:
        AssertionError: If the value is an unawaited coroutine.
        
    Example:
        >>> result = handler.validate_selection_exists("template")
        >>> assert_not_coroutine(result, "validate_selection_exists")
        >>> # Will raise if result is a coroutine object
    """
    if inspect.iscoroutine(value):
        error_msg = f"{message}\n" if message else ""
        error_msg += (
            f"Value is an unawaited coroutine: {value}\n"
            f"Did you forget to await or use @pytest.mark.asyncio?\n"
            f"Coroutine type: {type(value)}"
        )
        raise AssertionError(error_msg)
