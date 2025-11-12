"""
Tests for enhanced ErrorContext system in utils.error_handling.

This module tests the error context tracking, call stack preservation,
user-friendly error formatting, and recovery suggestions.
"""

import pytest
from TimeLocker.utils.error_handling import (
    ErrorContext,
    ErrorHandler,
    error_handler,
    format_error_with_context,
    suggest_recovery,
    with_error_handling
)


class TestErrorContext:
    """Test ErrorContext functionality"""

    def test_error_context_creation(self):
        """Test creating error context with basic information"""
        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            param1="value1",
            param2="value2"
        )

        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.metadata["param1"] == "value1"
        assert context.metadata["param2"] == "value2"
        assert context.error_id is not None
        assert context.timestamp is not None

    def test_add_context(self):
        """Test adding context information dynamically"""
        context = ErrorContext("test_op", "test_comp")

        context.add_context("key1", "value1")
        context.add_context("key2", 123)

        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"] == 123

    def test_add_recovery_suggestion(self):
        """Test adding recovery suggestions"""
        context = ErrorContext("test_op", "test_comp")

        context.add_recovery_suggestion("Try action 1")
        context.add_recovery_suggestion("Try action 2")

        suggestions = context.get_recovery_suggestions()
        assert len(suggestions) == 2
        assert "Try action 1" in suggestions
        assert "Try action 2" in suggestions

    def test_recovery_suggestion_deduplication(self):
        """Test that duplicate suggestions are not added"""
        context = ErrorContext("test_op", "test_comp")

        context.add_recovery_suggestion("Try action 1")
        context.add_recovery_suggestion("Try action 1")  # Duplicate

        suggestions = context.get_recovery_suggestions()
        assert len(suggestions) == 1

    def test_context_stack_tracking(self):
        """Test that context stack is tracked through nested contexts"""
        with ErrorContext("outer_op", "outer_comp") as outer:
            outer.add_context("level", "outer")

            with ErrorContext("inner_op", "inner_comp") as inner:
                inner.add_context("level", "inner")

                # Inner context should have outer as parent
                assert inner.parent_context is outer
                assert inner.parent_context.metadata["level"] == "outer"

    def test_get_context_with_parent(self):
        """Test getting context including parent context chain"""
        with ErrorContext("outer_op", "outer_comp") as outer:
            with ErrorContext("inner_op", "inner_comp") as inner:
                context_dict = inner.get_context()

                assert context_dict["operation"] == "inner_op"
                assert "parent_context" in context_dict
                assert context_dict["parent_context"]["operation"] == "outer_op"

    def test_recovery_suggestions_from_parent(self):
        """Test that recovery suggestions include parent suggestions"""
        with ErrorContext("outer_op", "outer_comp") as outer:
            outer.add_recovery_suggestion("Outer suggestion")

            with ErrorContext("inner_op", "inner_comp") as inner:
                inner.add_recovery_suggestion("Inner suggestion")

                suggestions = inner.get_recovery_suggestions()
                assert len(suggestions) == 2
                assert "Inner suggestion" in suggestions
                assert "Outer suggestion" in suggestions

    def test_format_error_basic(self):
        """Test basic error formatting"""
        context = ErrorContext("backup", "BackupService", repo="test-repo")
        error = ValueError("Invalid backup configuration")

        formatted = context.format_error(error)

        assert "ValueError" in formatted
        assert "Invalid backup configuration" in formatted
        assert "BackupService" in formatted
        assert "backup" in formatted
        assert "test-repo" in formatted

    def test_format_error_with_parent_context(self):
        """Test error formatting with parent context chain"""
        with ErrorContext("outer_op", "OuterService") as outer:
            with ErrorContext("inner_op", "InnerService") as inner:
                error = RuntimeError("Test error")
                formatted = inner.format_error(error)

                assert "RuntimeError" in formatted
                assert "InnerService" in formatted
                assert "inner_op" in formatted
                assert "Call Stack" in formatted
                assert "OuterService" in formatted

    def test_format_error_with_recovery_suggestions(self):
        """Test error formatting includes recovery suggestions"""
        context = ErrorContext("backup", "BackupService")
        context.add_recovery_suggestion("Check repository configuration")
        context.add_recovery_suggestion("Verify credentials")

        error = ValueError("Configuration error")
        formatted = context.format_error(error)

        assert "Suggested Actions" in formatted
        assert "Check repository configuration" in formatted
        assert "Verify credentials" in formatted

    def test_to_dict(self):
        """Test converting context to dictionary"""
        context = ErrorContext("test_op", "test_comp", key1="value1")
        context.add_recovery_suggestion("Suggestion 1")

        context_dict = context.to_dict()

        assert context_dict["operation"] == "test_op"
        assert context_dict["component"] == "test_comp"
        assert context_dict["metadata"]["key1"] == "value1"
        assert "error_id" in context_dict
        assert "timestamp" in context_dict
        assert "Suggestion 1" in context_dict["recovery_suggestions"]


class TestErrorHandler:
    """Test ErrorHandler functionality"""

    def test_register_recovery_suggestion_provider(self):
        """Test registering custom recovery suggestion providers"""
        handler = ErrorHandler()

        def custom_provider(exc, ctx):
            return ["Custom suggestion 1", "Custom suggestion 2"]

        handler.register_recovery_suggestion_provider(ValueError, custom_provider)

        context = ErrorContext("test_op", "test_comp")
        error = ValueError("Test error")

        suggestions = handler.suggest_recovery(error, context)
        assert "Custom suggestion 1" in suggestions
        assert "Custom suggestion 2" in suggestions

    def test_default_recovery_suggestions(self):
        """Test default recovery suggestions for common exceptions"""
        handler = ErrorHandler()
        context = ErrorContext("test_op", "test_comp")

        # Test FileNotFoundError suggestions
        error = FileNotFoundError("File not found")
        suggestions = handler.suggest_recovery(error, context)
        assert len(suggestions) > 0
        assert any("file path" in s.lower() for s in suggestions)

        # Test PermissionError suggestions
        error = PermissionError("Permission denied")
        suggestions = handler.suggest_recovery(error, context)
        assert len(suggestions) > 0
        assert any("permission" in s.lower() for s in suggestions)

    def test_handle_error_adds_suggestions(self):
        """Test that handle_error adds recovery suggestions to context"""
        handler = ErrorHandler()
        context = ErrorContext("test_op", "test_comp")
        error = ValueError("Test error")

        try:
            handler.handle_error(error, context, reraise=True)
        except ValueError:
            pass  # Expected

        # Context should now have recovery suggestions
        suggestions = context.get_recovery_suggestions()
        assert len(suggestions) > 0

    def test_error_context_manager(self):
        """Test error_context context manager"""
        handler = ErrorHandler()

        try:
            with handler.error_context("test_op", "test_comp", key="value"):
                raise ValueError("Test error")
        except ValueError as e:
            assert str(e) == "Test error"

    def test_with_error_handling_decorator(self):
        """Test with_error_handling decorator"""
        handler = ErrorHandler()

        @handler.with_error_handling("test_op", "test_comp", reraise=False)
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()
        assert result is None  # Should not reraise


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_format_error_with_context_function(self):
        """Test format_error_with_context convenience function"""
        context = ErrorContext("test_op", "test_comp")
        error = ValueError("Test error")

        formatted = format_error_with_context(error, context)

        assert "ValueError" in formatted
        assert "Test error" in formatted
        assert "test_comp" in formatted

    def test_format_error_without_context(self):
        """Test format_error_with_context without context"""
        error = ValueError("Test error")

        formatted = format_error_with_context(error, None)

        assert "ValueError" in formatted
        assert "Test error" in formatted

    def test_suggest_recovery_function(self):
        """Test suggest_recovery convenience function"""
        context = ErrorContext("test_op", "test_comp")
        error = FileNotFoundError("File not found")

        suggestions = suggest_recovery(error, context)

        assert len(suggestions) > 0
        assert isinstance(suggestions, list)

    def test_with_error_handling_decorator_function(self):
        """Test with_error_handling decorator convenience function"""

        @with_error_handling("test_op", "test_comp", reraise=False)
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()
        assert result is None


class TestErrorContextIntegration:
    """Test ErrorContext integration scenarios"""

    def test_nested_operations_with_context(self):
        """Test nested operations with context tracking"""

        def inner_operation():
            with ErrorContext("inner_op", "InnerService") as ctx:
                ctx.add_context("inner_param", "inner_value")
                raise ValueError("Inner error")

        def outer_operation():
            with ErrorContext("outer_op", "OuterService") as ctx:
                ctx.add_context("outer_param", "outer_value")
                inner_operation()

        try:
            outer_operation()
        except ValueError as e:
            # Error should have been raised
            assert str(e) == "Inner error"

    def test_context_preserved_across_exception_handling(self):
        """Test that context is preserved when catching and re-raising"""

        try:
            with ErrorContext("outer_op", "OuterService") as outer:
                outer.add_recovery_suggestion("Outer suggestion")

                try:
                    with ErrorContext("inner_op", "InnerService") as inner:
                        inner.add_recovery_suggestion("Inner suggestion")
                        raise ValueError("Test error")
                except ValueError:
                    # Context should still be accessible
                    suggestions = inner.get_recovery_suggestions()
                    assert len(suggestions) == 2
                    raise
        except ValueError as e:
            # Expected - error was re-raised
            assert str(e) == "Test error"

    def test_multiple_sequential_contexts(self):
        """Test multiple sequential contexts don't interfere"""

        with ErrorContext("op1", "Service1") as ctx1:
            ctx1.add_context("key", "value1")
            assert ctx1.metadata["key"] == "value1"

        with ErrorContext("op2", "Service2") as ctx2:
            ctx2.add_context("key", "value2")
            assert ctx2.metadata["key"] == "value2"
            # Should not have parent from previous context
            assert ctx2.parent_context is None
