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
Integration Architecture Exceptions for TimeLocker

This module defines exceptions specific to the TimeLocker integration
architecture, including service lifecycle, context management, and
event system errors.
"""

from .exceptions import TimeLockerInterfaceError


class ServiceIntegrationError(TimeLockerInterfaceError):
    """Base exception for service integration errors"""
    pass


class ServiceInitializationError(ServiceIntegrationError):
    """Raised when service initialization fails"""
    
    def __init__(self, service_name: str, message: str, cause: Exception = None):
        """
        Initialize service initialization error.
        
        Args:
            service_name: Name of the service that failed to initialize
            message: Error message describing the failure
            cause: Optional underlying exception that caused the failure
        """
        self.service_name = service_name
        self.cause = cause
        
        full_message = f"Service '{service_name}' initialization failed: {message}"
        if cause:
            full_message += f" (caused by: {cause})"
        
        super().__init__(full_message)


class ServiceShutdownError(ServiceIntegrationError):
    """Raised when service shutdown fails"""
    
    def __init__(self, service_name: str, message: str, cause: Exception = None):
        """
        Initialize service shutdown error.
        
        Args:
            service_name: Name of the service that failed to shutdown
            message: Error message describing the failure
            cause: Optional underlying exception that caused the failure
        """
        self.service_name = service_name
        self.cause = cause
        
        full_message = f"Service '{service_name}' shutdown failed: {message}"
        if cause:
            full_message += f" (caused by: {cause})"
        
        super().__init__(full_message)


class ServiceContextError(ServiceIntegrationError):
    """Base exception for service context errors"""
    pass


class ServiceContextValidationError(ServiceContextError):
    """Raised when service context validation fails"""
    
    def __init__(self, missing_components: list = None, invalid_components: list = None):
        """
        Initialize service context validation error.
        
        Args:
            missing_components: List of missing required components
            invalid_components: List of invalid components
        """
        self.missing_components = missing_components or []
        self.invalid_components = invalid_components or []
        
        message_parts = []
        if self.missing_components:
            message_parts.append(f"Missing components: {', '.join(self.missing_components)}")
        if self.invalid_components:
            message_parts.append(f"Invalid components: {', '.join(self.invalid_components)}")
        
        message = "Service context validation failed"
        if message_parts:
            message += f": {'; '.join(message_parts)}"
        
        super().__init__(message)


class ServiceContextInheritanceError(ServiceContextError):
    """Raised when service context inheritance fails"""
    pass


class EventSystemError(ServiceIntegrationError):
    """Base exception for event system errors"""
    pass


class EventValidationError(EventSystemError):
    """Raised when event validation fails"""
    
    def __init__(self, event_data: dict = None, validation_errors: list = None):
        """
        Initialize event validation error.
        
        Args:
            event_data: Event data that failed validation
            validation_errors: List of validation error messages
        """
        self.event_data = event_data
        self.validation_errors = validation_errors or []
        
        message = "Event validation failed"
        if self.validation_errors:
            message += f": {'; '.join(self.validation_errors)}"
        
        super().__init__(message)


class EventCorrelationError(EventSystemError):
    """Raised when event correlation operations fail"""
    pass


class ServiceDiscoveryError(ServiceIntegrationError):
    """Raised when service discovery operations fail"""
    
    def __init__(self, service_type: str = None, message: str = None):
        """
        Initialize service discovery error.
        
        Args:
            service_type: Type of service that could not be discovered
            message: Error message
        """
        self.service_type = service_type
        
        if not message:
            if service_type:
                message = f"Could not discover service of type: {service_type}"
            else:
                message = "Service discovery failed"
        
        super().__init__(message)


class ServiceRegistrationError(ServiceIntegrationError):
    """Raised when service registration operations fail"""
    
    def __init__(self, service_name: str = None, message: str = None):
        """
        Initialize service registration error.
        
        Args:
            service_name: Name of service that could not be registered
            message: Error message
        """
        self.service_name = service_name
        
        if not message:
            if service_name:
                message = f"Could not register service: {service_name}"
            else:
                message = "Service registration failed"
        
        super().__init__(message)


class DependencyResolutionError(ServiceIntegrationError):
    """Raised when dependency resolution fails"""
    
    def __init__(self, service_name: str = None, missing_dependencies: list = None, 
                 circular_dependencies: list = None):
        """
        Initialize dependency resolution error.
        
        Args:
            service_name: Name of service with dependency issues
            missing_dependencies: List of missing dependencies
            circular_dependencies: List of services involved in circular dependency
        """
        self.service_name = service_name
        self.missing_dependencies = missing_dependencies or []
        self.circular_dependencies = circular_dependencies or []
        
        message_parts = []
        if self.missing_dependencies:
            message_parts.append(f"Missing dependencies: {', '.join(self.missing_dependencies)}")
        if self.circular_dependencies:
            message_parts.append(f"Circular dependencies: {' -> '.join(self.circular_dependencies)}")
        
        message = "Dependency resolution failed"
        if service_name:
            message += f" for service '{service_name}'"
        if message_parts:
            message += f": {'; '.join(message_parts)}"
        
        super().__init__(message)