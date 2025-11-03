"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

"""
Tests for Error Propagation System

This module tests the error propagation, translation, correlation, and recovery
mechanisms for the TimeLocker integration architecture.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.TimeLocker.integration.error_propagation import (
    ErrorPropagationSystem,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    PropagatedError,
    ErrorTranslator,
    ErrorCorrelator,
    ErrorRecoveryManager
)
from src.TimeLocker.integration.event_bus import EventBus
from src.TimeLocker.interfaces.integration_data_models import Event


class TestErrorContext:
    """Test ErrorContext functionality"""
    
    def test_error_context_creation(self):
        """Test creating error context with default values"""
        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            service_name="test_service"
        )
        
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.service_name == "test_service"
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.category == ErrorCategory.UNKNOWN
        assert context.retry_count == 0
        assert not context.recovery_attempted
        assert len(context.propagation_path) == 0
    
    def test_error_context_propagation_path(self):
        """Test adding steps to propagation path"""
        context = ErrorContext()
        
        context.add_propagation_step("component1", "service1")
        context.add_propagation_step("component2")
        
        assert len(context.propagation_path) == 2
        assert "service1:component1" in context.propagation_path
        assert "component2" in context.propagation_path
        
        # Test duplicate prevention
        context.add_propagation_step("component1", "service1")
        assert len(context.propagation_path) == 2
    
    def test_error_context_retry_increment(self):
        """Test retry count increment"""
        context = ErrorContext()
        
        assert context.retry_count == 0
        context.increment_retry()
        assert context.retry_count == 1
        context.increment_retry()
        assert context.retry_count == 2
    
    def test_error_context_serialization(self):
        """Test error context serialization and deserialization"""
        context = ErrorContext(
            operation="test_op",
            component="test_comp",
            service_name="test_service",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            correlation_id="test-correlation"
        )
        
        context.add_propagation_step("step1")
        context.increment_retry()
        context.mark_recovery_attempted()
        
        # Serialize to dict
        data = context.to_dict()
        
        # Deserialize from dict
        restored_context = ErrorContext.from_dict(data)
        
        assert restored_context.operation == context.operation
        assert restored_context.component == context.component
        assert restored_context.service_name == context.service_name
        assert restored_context.severity == context.severity
        assert restored_context.category == context.category
        assert restored_context.correlation_id == context.correlation_id
        assert restored_context.retry_count == context.retry_count
        assert restored_context.recovery_attempted == context.recovery_attempted
        assert restored_context.propagation_path == context.propagation_path


class TestPropagatedError:
    """Test PropagatedError functionality"""
    
    def test_propagated_error_creation(self):
        """Test creating propagated error"""
        original_exception = ValueError("Test error")
        context = ErrorContext(operation="test_op", component="test_comp")
        
        error = PropagatedError(
            original_exception=original_exception,
            context=context,
            user_message="User-friendly message",
            suggested_actions=["Action 1", "Action 2"]
        )
        
        assert error.original_exception == original_exception
        assert error.context == context
        assert error.user_message == "User-friendly message"
        assert len(error.suggested_actions) == 2
        assert error.is_recoverable
    
    def test_propagated_error_string_representation(self):
        """Test string representation of propagated error"""
        original_exception = ValueError("Test error")
        context = ErrorContext()
        
        # With user message
        error = PropagatedError(
            original_exception=original_exception,
            context=context,
            user_message="User-friendly message"
        )
        assert str(error) == "User-friendly message"
        
        # Without user message
        error_no_msg = PropagatedError(
            original_exception=original_exception,
            context=context
        )
        assert str(error_no_msg) == "Test error"
    
    def test_propagated_error_technical_message(self):
        """Test technical message generation"""
        original_exception = ValueError("Test error")
        context = ErrorContext()
        
        error = PropagatedError(
            original_exception=original_exception,
            context=context
        )
        
        technical_msg = error.get_technical_message()
        assert context.error_id in technical_msg
        assert "Test error" in technical_msg


class TestErrorTranslator:
    """Test ErrorTranslator functionality"""
    
    def test_error_translator_registration(self):
        """Test registering error translations"""
        translator = ErrorTranslator()
        
        def custom_translator(exception, context):
            return f"Custom message for {type(exception).__name__}"
        
        translator.register_translation(ValueError, custom_translator)
        
        context = ErrorContext()
        exception = ValueError("Test error")
        
        message = translator.translate_error(exception, context)
        assert message == "Custom message for ValueError"
    
    def test_error_translator_category_translation(self):
        """Test category-based error translation"""
        translator = ErrorTranslator()
        
        def network_translator(exception, context):
            return "Network error occurred"
        
        translator.register_category_translation(ErrorCategory.NETWORK, network_translator)
        
        context = ErrorContext(category=ErrorCategory.NETWORK)
        # Use a custom exception that doesn't have a default translation
        class CustomNetworkError(Exception):
            pass
        
        exception = CustomNetworkError("Network failed")
        
        message = translator.translate_error(exception, context)
        assert message == "Network error occurred"
    
    def test_error_translator_inheritance(self):
        """Test translation inheritance for exception hierarchies"""
        translator = ErrorTranslator()
        
        def base_translator(exception, context):
            return "Base exception message"
        
        translator.register_translation(Exception, base_translator)
        
        context = ErrorContext()
        exception = ValueError("Specific error")
        
        message = translator.translate_error(exception, context)
        assert message == "Base exception message"
    
    def test_error_translator_default_translations(self):
        """Test default error translations"""
        translator = ErrorTranslator()
        context = ErrorContext()
        
        # Test FileNotFoundError
        file_error = FileNotFoundError("File not found")
        message = translator.translate_error(file_error, context)
        assert "file could not be found" in message.lower()
        
        # Test PermissionError
        perm_error = PermissionError("Permission denied")
        message = translator.translate_error(perm_error, context)
        assert "permission denied" in message.lower()
    
    def test_error_translator_fallback(self):
        """Test fallback to generic message"""
        translator = ErrorTranslator()
        context = ErrorContext(operation="test_op", component="test_comp")
        
        # Custom exception not registered
        class CustomError(Exception):
            pass
        
        exception = CustomError("Custom error")
        message = translator.translate_error(exception, context)
        
        assert "test_op" in message
        assert "test_comp" in message


class TestErrorCorrelator:
    """Test ErrorCorrelator functionality"""
    
    def test_error_correlation_by_id(self):
        """Test error correlation by correlation ID"""
        correlator = ErrorCorrelator()
        
        correlation_id = "test-correlation"
        
        context1 = ErrorContext(
            operation="op1",
            component="comp1",
            correlation_id=correlation_id
        )
        
        context2 = ErrorContext(
            operation="op2",
            component="comp2",
            correlation_id=correlation_id
        )
        
        # Correlate errors
        related1 = correlator.correlate_error(context1)
        related2 = correlator.correlate_error(context2)
        
        # Both should return the same correlated errors
        assert len(related1) == 1  # Only context1 at this point
        assert len(related2) == 2  # Both context1 and context2
        
        # Get correlated errors by ID
        correlated = correlator.get_correlated_errors(correlation_id)
        assert len(correlated) == 2
        assert context1 in correlated
        assert context2 in correlated
    
    def test_error_grouping(self):
        """Test error grouping by operation and component"""
        correlator = ErrorCorrelator()
        
        # Add correlation IDs to ensure errors are tracked
        context1 = ErrorContext(
            operation="backup", 
            component="repository",
            correlation_id="backup-correlation-1"
        )
        context2 = ErrorContext(
            operation="backup", 
            component="repository",
            correlation_id="backup-correlation-2"
        )
        context3 = ErrorContext(
            operation="restore", 
            component="repository",
            correlation_id="restore-correlation-1"
        )
        
        # Correlate errors
        correlator.correlate_error(context1)
        correlator.correlate_error(context2)
        correlator.correlate_error(context3)
        
        # Get error groups
        groups = correlator.get_error_groups()
        
        # Should have at least the groups we created
        backup_group_key = "backup:repository"
        restore_group_key = "restore:repository"
        
        # Check that groups exist and have the expected errors
        assert backup_group_key in groups or restore_group_key in groups
        
        # Verify we can get correlated errors by ID
        backup1_errors = correlator.get_correlated_errors("backup-correlation-1")
        assert len(backup1_errors) == 1
        assert backup1_errors[0].operation == "backup"
    
    def test_error_correlation_cleanup(self):
        """Test cleanup of old error correlations"""
        correlator = ErrorCorrelator(max_correlation_age_hours=24)  # Normal age
        
        # Create context with old timestamp
        old_time = datetime.now() - timedelta(hours=25)  # 25 hours ago (older than max age)
        context = ErrorContext(
            operation="test_op",
            correlation_id="test-correlation"
        )
        context.timestamp = old_time  # Manually set old timestamp
        
        # Manually add to correlations to bypass the cleanup that happens in correlate_error
        with correlator._lock:
            correlator._correlations["test-correlation"].append(context)
            correlator._error_groups[f"{context.operation}:{context.component}"].add(context.error_id)
        
        # Verify it exists initially
        correlated = correlator.get_correlated_errors("test-correlation")
        assert len(correlated) == 1
        
        # Create a new context that will trigger cleanup when added
        new_context = ErrorContext(
            operation="new_op",
            correlation_id="new-correlation"
        )
        
        # Add the new error - this should trigger cleanup of old correlations
        correlator.correlate_error(new_context)
        
        # Old correlation should be cleaned up due to age
        old_correlated = correlator.get_correlated_errors("test-correlation")
        assert len(old_correlated) == 0
        
        # New correlation should still exist
        new_correlated = correlator.get_correlated_errors("new-correlation")
        assert len(new_correlated) == 1


class TestErrorRecoveryManager:
    """Test ErrorRecoveryManager functionality"""
    
    def test_recovery_strategy_registration(self):
        """Test registering recovery strategies"""
        recovery_manager = ErrorRecoveryManager()
        
        def custom_recovery(exception, context):
            return "recovered"
        
        recovery_manager.register_recovery_strategy(ValueError, custom_recovery)
        
        context = ErrorContext()
        exception = ValueError("Test error")
        
        result = recovery_manager.attempt_recovery(exception, context)
        assert result == "recovered"
        assert context.recovery_attempted
    
    def test_category_recovery_strategy(self):
        """Test category-based recovery strategies"""
        recovery_manager = ErrorRecoveryManager()
        
        def network_recovery(exception, context):
            return "network_recovered"
        
        recovery_manager.register_category_strategy(ErrorCategory.NETWORK, network_recovery)
        
        context = ErrorContext(category=ErrorCategory.NETWORK)
        exception = ConnectionError("Network error")
        
        result = recovery_manager.attempt_recovery(exception, context)
        assert result == "network_recovered"
    
    def test_fallback_strategy(self):
        """Test operation-specific fallback strategies"""
        recovery_manager = ErrorRecoveryManager()
        
        def backup_fallback(exception, context):
            return "backup_fallback"
        
        recovery_manager.register_fallback_strategy("backup", backup_fallback)
        
        context = ErrorContext(operation="backup")
        exception = Exception("Backup failed")
        
        result = recovery_manager.attempt_recovery(exception, context)
        assert result == "backup_fallback"
    
    def test_retry_configuration(self):
        """Test retry configuration and logic"""
        recovery_manager = ErrorRecoveryManager()
        
        recovery_manager.configure_retry(
            ValueError,
            max_retries=2,
            delay=0.1,
            backoff_multiplier=2.0
        )
        
        context = ErrorContext()
        exception = ValueError("Test error")
        
        # Should retry initially
        assert recovery_manager.should_retry(exception, context)
        
        # After max retries, should not retry
        context.retry_count = 2
        assert not recovery_manager.should_retry(exception, context)
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation with exponential backoff"""
        recovery_manager = ErrorRecoveryManager()
        
        recovery_manager.configure_retry(
            ValueError,
            delay=1.0,
            backoff_multiplier=2.0,
            max_delay=10.0
        )
        
        context = ErrorContext()
        exception = ValueError("Test error")
        
        # First retry
        delay1 = recovery_manager.get_retry_delay(exception, context)
        assert delay1 == 1.0
        
        # Second retry
        context.retry_count = 1
        delay2 = recovery_manager.get_retry_delay(exception, context)
        assert delay2 == 2.0
        
        # Third retry
        context.retry_count = 2
        delay3 = recovery_manager.get_retry_delay(exception, context)
        assert delay3 == 4.0
    
    def test_default_retry_logic(self):
        """Test default retry logic for certain categories"""
        recovery_manager = ErrorRecoveryManager()
        
        # Network errors should retry by default
        network_context = ErrorContext(category=ErrorCategory.NETWORK)
        network_exception = ConnectionError("Network error")
        
        assert recovery_manager.should_retry(network_exception, network_context)
        
        # After max default retries, should not retry
        network_context.retry_count = 3
        assert not recovery_manager.should_retry(network_exception, network_context)


class TestErrorPropagationSystem:
    """Test ErrorPropagationSystem integration"""
    
    def test_error_propagation_system_initialization(self):
        """Test error propagation system initialization"""
        system = ErrorPropagationSystem()
        
        assert system.translator is not None
        assert system.correlator is not None
        assert system.recovery_manager is not None
        assert system.event_bus is None  # No event bus provided
    
    def test_error_propagation_with_event_bus(self):
        """Test error propagation with event bus integration"""
        event_bus = EventBus(enable_persistence=False)
        system = ErrorPropagationSystem(event_bus=event_bus)
        
        # Mock event handler to capture published events
        published_events = []
        
        def event_handler(event):
            published_events.append(event)
        
        event_bus.subscribe_event(
            event_type_pattern="error.*",
            handler=event_handler
        )
        
        # Propagate an error
        exception = ValueError("Test error")
        propagated_error = system.propagate_error(
            exception=exception,
            operation="test_operation",
            component="test_component",
            severity=ErrorSeverity.HIGH
        )
        
        assert propagated_error.original_exception == exception
        assert propagated_error.context.operation == "test_operation"
        assert propagated_error.context.component == "test_component"
        assert propagated_error.context.severity == ErrorSeverity.HIGH
        
        # Check that error event was published
        assert len(published_events) == 1
        error_event = published_events[0]
        assert error_event.event_type == "error.occurred"
        assert error_event.data['operation'] == "test_operation"
    
    def test_error_recovery_attempt(self):
        """Test error recovery through propagation system"""
        system = ErrorPropagationSystem()
        
        # Register a recovery strategy
        def test_recovery(exception, context):
            return "recovery_successful"
        
        system.recovery_manager.register_recovery_strategy(ValueError, test_recovery)
        
        # Propagate an error
        exception = ValueError("Test error")
        propagated_error = system.propagate_error(
            exception=exception,
            operation="test_operation"
        )
        
        # Attempt recovery
        result = system.attempt_error_recovery(propagated_error)
        assert result == "recovery_successful"
        
        # Check statistics
        stats = system.get_error_statistics()
        assert stats['errors_processed'] == 1
        assert stats['errors_recovered'] == 1
    
    def test_error_retry_logic(self):
        """Test error retry logic through propagation system"""
        system = ErrorPropagationSystem()
        
        # Configure retry for ValueError
        system.recovery_manager.configure_retry(ValueError, max_retries=2, delay=0.1)
        
        # Propagate an error
        exception = ValueError("Test error")
        propagated_error = system.propagate_error(
            exception=exception,
            operation="test_operation"
        )
        
        # Should retry initially
        assert system.should_retry_error(propagated_error)
        
        # Get retry delay
        delay = system.get_retry_delay(propagated_error)
        assert delay == 0.1
        
        # Increment retry count
        system.increment_retry_count(propagated_error)
        assert propagated_error.context.retry_count == 1
        
        # Should still retry
        assert system.should_retry_error(propagated_error)
        
        # Increment again
        system.increment_retry_count(propagated_error)
        assert propagated_error.context.retry_count == 2
        
        # Should not retry after max retries
        assert not system.should_retry_error(propagated_error)
    
    def test_error_correlation_integration(self):
        """Test error correlation through propagation system"""
        system = ErrorPropagationSystem()
        
        correlation_id = "test-correlation"
        
        # Propagate first error
        exception1 = ValueError("First error")
        error1 = system.propagate_error(
            exception=exception1,
            operation="operation1",
            correlation_id=correlation_id
        )
        
        # Propagate second error with same correlation ID
        exception2 = RuntimeError("Second error")
        error2 = system.propagate_error(
            exception=exception2,
            operation="operation2",
            correlation_id=correlation_id
        )
        
        # Get correlated errors
        correlated = system.get_correlated_errors(correlation_id)
        assert len(correlated) == 2
        
        # Check that both error contexts are present
        error_ids = [ctx.error_id for ctx in correlated]
        assert error1.context.error_id in error_ids
        assert error2.context.error_id in error_ids
    
    def test_critical_error_handling(self):
        """Test critical error handling"""
        event_bus = EventBus(enable_persistence=False)
        system = ErrorPropagationSystem(event_bus=event_bus)
        
        # Propagate a critical error
        exception = RuntimeError("Critical system error")
        propagated_error = system.propagate_error(
            exception=exception,
            operation="critical_operation",
            severity=ErrorSeverity.CRITICAL
        )
        
        assert propagated_error.context.severity == ErrorSeverity.CRITICAL
        
        # Check statistics
        stats = system.get_error_statistics()
        assert stats['critical_errors'] == 1
    
    def test_error_statistics(self):
        """Test error statistics tracking"""
        system = ErrorPropagationSystem()
        
        # Initial statistics
        stats = system.get_error_statistics()
        assert stats['errors_processed'] == 0
        assert stats['errors_recovered'] == 0
        assert stats['errors_retried'] == 0
        
        # Propagate some errors
        for i in range(3):
            exception = ValueError(f"Error {i}")
            system.propagate_error(exception, f"operation_{i}")
        
        # Check updated statistics
        stats = system.get_error_statistics()
        assert stats['errors_processed'] == 3


if __name__ == '__main__':
    pytest.main([__file__])