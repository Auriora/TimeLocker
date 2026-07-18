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
Tests for Error Integration Module

This module tests the integration between error propagation system and
service architecture, including decorators and utilities.
"""

import pytest
import time
from unittest.mock import Mock, patch

from TimeLocker.integration.error_integration import (
    ServiceErrorHandler,
    ServiceInterfaceErrorMixin,
    with_service_error_handling,
    service_error_context,
    create_service_with_error_handling,
    handle_configuration_error,
    handle_network_error,
    handle_authentication_error
)
from TimeLocker.integration.error_propagation import (
    ErrorPropagationSystem,
    ErrorSeverity,
    ErrorCategory
)
from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.interfaces.integration_data_models import ServiceContext


class TestServiceErrorHandler:
    """Test ServiceErrorHandler functionality"""
    
    def test_service_error_handler_initialization(self):
        """Test service error handler initialization"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        assert handler.service_name == "TestService"
        assert handler.error_system == error_system
        assert handler._operation_context == {}
    
    def test_operation_context_management(self):
        """Test operation context management"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        # Set context
        handler.set_operation_context(user_id="123", session_id="abc")
        assert handler._operation_context["user_id"] == "123"
        assert handler._operation_context["session_id"] == "abc"
        
        # Clear context
        handler.clear_operation_context()
        assert handler._operation_context == {}
    
    def test_handle_service_error(self):
        """Test handling service errors"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        # Set operation context
        handler.set_operation_context(user_id="123")
        
        # Handle an error
        exception = ValueError("Test error")
        propagated_error = handler.handle_service_error(
            exception=exception,
            operation="test_operation",
            component="test_component",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.VALIDATION
        )
        
        assert propagated_error.original_exception == exception
        assert propagated_error.context.operation == "test_operation"
        assert propagated_error.context.component == "test_component"
        assert propagated_error.context.service_name == "TestService"
        assert propagated_error.context.severity == ErrorSeverity.HIGH
        assert propagated_error.context.category == ErrorCategory.VALIDATION
        assert propagated_error.context.technical_details["user_id"] == "123"
    
    def test_error_handling_decorator(self):
        """Test error handling decorator"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        # Mock recovery to return a value
        def mock_recovery(exception, context):
            return "recovered_value"
        
        error_system.recovery_manager.register_recovery_strategy(ValueError, mock_recovery)
        
        @handler.with_error_handling("test_operation", attempt_recovery=True, reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        # Should return recovery value instead of raising
        result = test_function()
        assert result == "recovered_value"
    
    def test_retry_decorator(self):
        """Test retry decorator"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        # Configure retry for ValueError
        error_system.recovery_manager.configure_retry(ValueError, max_retries=2, delay=0.01)
        
        call_count = 0
        
        @handler.with_retry("test_operation", max_retries=2)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"
        
        # Should succeed after retries
        result = test_function()
        assert result == "success"
        assert call_count == 3  # Initial call + 2 retries
    
    def test_retry_decorator_failure(self):
        """Test retry decorator when all retries fail"""
        error_system = ErrorPropagationSystem()
        handler = ServiceErrorHandler("TestService", error_system)
        
        # Configure retry for ValueError
        error_system.recovery_manager.configure_retry(ValueError, max_retries=1, delay=0.01)
        
        call_count = 0
        
        @handler.with_retry("test_operation", max_retries=1)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")
        
        # Should raise after all retries fail
        with pytest.raises(ValueError):
            test_function()
        
        assert call_count == 2  # Initial call + 1 retry


class TestServiceInterfaceErrorMixin:
    """Test ServiceInterfaceErrorMixin functionality"""
    
    def test_error_mixin_initialization(self):
        """Test error mixin initialization"""
        
        class TestService(ServiceInterfaceErrorMixin, ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
        
        service = TestService()
        assert service._error_handler is None
        
        # Initialize error handler
        error_system = ErrorPropagationSystem()
        service._initialize_error_handler(error_system)
        
        assert service._error_handler is not None
        assert service._error_handler.service_name == "TestService"
    
    def test_error_mixin_error_handling(self):
        """Test error handling through mixin"""
        
        class TestService(ServiceInterfaceErrorMixin, ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
            
            def test_method(self):
                exception = ValueError("Test error")
                return self._handle_service_error(exception, "test_operation")
        
        service = TestService()
        error_system = ErrorPropagationSystem()
        service._initialize_error_handler(error_system)
        
        # Handle error through mixin
        propagated_error = service.test_method()
        
        assert propagated_error.original_exception.__class__ == ValueError
        assert propagated_error.context.operation == "test_operation"
        assert propagated_error.context.service_name == "TestService"
    
    def test_error_mixin_decorators(self):
        """Test decorator access through mixin"""
        
        class TestService(ServiceInterfaceErrorMixin, ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
            
            def test_decorated_method(self):
                decorator = self._with_error_handling("test_operation", reraise=False)
                
                @decorator
                def inner_method():
                    raise ValueError("Test error")
                
                return inner_method()
        
        service = TestService()
        error_system = ErrorPropagationSystem()
        service._initialize_error_handler(error_system)
        
        # Should not raise due to reraise=False
        result = service.test_decorated_method()
        assert result is None


class TestStandaloneDecorators:
    """Test standalone decorator functions"""
    
    def test_with_service_error_handling_decorator(self):
        """Test standalone service error handling decorator"""
        
        @with_service_error_handling(
            service_name="TestService",
            operation="test_operation",
            severity=ErrorSeverity.HIGH
        )
        def test_function():
            raise ValueError("Test error")
        
        # Should raise the original exception after handling
        with pytest.raises(ValueError):
            test_function()
    
    def test_service_error_context_manager(self):
        """Test service error context manager"""
        
        with pytest.raises(ValueError):
            with service_error_context(
                service_name="TestService",
                operation="test_operation",
                severity=ErrorSeverity.HIGH
            ) as context:
                assert context.operation == "test_operation"
                assert context.service_name == "TestService"
                assert context.severity == ErrorSeverity.HIGH
                raise ValueError("Test error")


class TestServiceCreation:
    """Test service creation with error handling"""
    
    def test_create_service_with_error_handling(self):
        """Test creating service with error handling"""
        
        class TestService(ServiceInterfaceErrorMixin, ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
        
        error_system = ErrorPropagationSystem()
        service = create_service_with_error_handling(TestService, error_system)
        
        assert isinstance(service, TestService)
        assert service._error_handler is not None
        assert service._error_handler.service_name == "TestService"
    
    def test_create_service_without_error_support(self):
        """Test creating service without error handling support"""
        
        class SimpleService(ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
        
        error_system = ErrorPropagationSystem()
        service = create_service_with_error_handling(SimpleService, error_system)
        
        assert isinstance(service, SimpleService)
        # Should not have error handler since it doesn't support it
        assert not hasattr(service, '_error_handler') or service._error_handler is None


class TestConvenienceFunctions:
    """Test convenience functions for common error scenarios"""
    
    def test_handle_configuration_error(self):
        """Test configuration error handling"""
        exception = ValueError("Invalid configuration")
        
        propagated_error = handle_configuration_error(
            exception=exception,
            service_name="ConfigService",
            operation="load_config"
        )
        
        assert propagated_error.original_exception == exception
        assert propagated_error.context.service_name == "ConfigService"
        assert propagated_error.context.operation == "load_config"
        assert propagated_error.context.severity == ErrorSeverity.HIGH
        assert propagated_error.context.category == ErrorCategory.CONFIGURATION
    
    def test_handle_network_error(self):
        """Test network error handling"""
        exception = ConnectionError("Network connection failed")
        
        propagated_error = handle_network_error(
            exception=exception,
            service_name="NetworkService",
            operation="connect"
        )
        
        assert propagated_error.original_exception == exception
        assert propagated_error.context.service_name == "NetworkService"
        assert propagated_error.context.operation == "connect"
        assert propagated_error.context.severity == ErrorSeverity.MEDIUM
        assert propagated_error.context.category == ErrorCategory.NETWORK
    
    def test_handle_authentication_error(self):
        """Test authentication error handling"""
        exception = PermissionError("Authentication failed")
        
        propagated_error = handle_authentication_error(
            exception=exception,
            service_name="AuthService",
            operation="authenticate"
        )
        
        assert propagated_error.original_exception == exception
        assert propagated_error.context.service_name == "AuthService"
        assert propagated_error.context.operation == "authenticate"
        assert propagated_error.context.severity == ErrorSeverity.HIGH
        assert propagated_error.context.category == ErrorCategory.AUTHENTICATION


class TestErrorHandlingIntegration:
    """Test integration between error handling components"""
    
    def test_end_to_end_error_handling(self):
        """Test complete error handling flow"""
        
        class TestService(ServiceInterfaceErrorMixin, ServiceInterface):
            def initialize(self, context):
                return True
            
            def shutdown(self):
                pass
            
            def health_check(self):
                return True
            
            def get_capabilities(self):
                return ["test"]
            
            def risky_operation(self):
                """Method that might fail and needs error handling"""
                decorator = self._with_error_handling(
                    "risky_operation",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.SYSTEM,
                    reraise=False,
                    attempt_recovery=True
                )
                
                @decorator
                def inner_operation():
                    raise ConnectionError("Network failed")
                
                return inner_operation()
        
        # Create service with error handling
        error_system = ErrorPropagationSystem()
        service = create_service_with_error_handling(TestService, error_system)
        
        # Register recovery strategy for ConnectionError specifically
        def network_recovery(exception, context):
            return "fallback_result"
        
        error_system.recovery_manager.register_recovery_strategy(
            ConnectionError, 
            network_recovery
        )
        
        # Execute risky operation
        result = service.risky_operation()
        
        # Should get recovery result
        assert result == "fallback_result"
        
        # Check error statistics
        stats = error_system.get_error_statistics()
        assert stats['errors_processed'] == 1
        assert stats['errors_recovered'] == 1


if __name__ == '__main__':
    pytest.main([__file__])