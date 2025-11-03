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
Service Interface for TimeLocker Integration Architecture

This module defines the base interface that all TimeLocker services must implement
to participate in the integrated service architecture. It provides standardized
lifecycle management, health checking, and capability discovery.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .integration_data_models import ServiceContext


class ServiceInterface(ABC):
    """
    Base interface for all TimeLocker services.
    
    This interface defines the standard contract that all services must implement
    to participate in the TimeLocker service architecture. It provides lifecycle
    management, health monitoring, and capability discovery.
    
    Requirements addressed:
    - 2.1: Standardized service interfaces for all major components
    - 2.2: Interface contracts with method signatures and validation
    - 2.4: Interface documentation and validation tools
    """

    @abstractmethod
    def initialize(self, context: 'ServiceContext') -> bool:
        """
        Initialize the service with the provided context.
        
        This method is called during service startup to provide the service
        with its runtime context including configuration, event bus, and
        service registry access.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
            
        Raises:
            ServiceInitializationError: If initialization fails due to invalid
                configuration or missing dependencies
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown the service and clean up resources.
        
        This method is called during service shutdown to allow the service
        to clean up resources, close connections, and perform any necessary
        cleanup operations. The service should be in a clean state after
        this method completes.
        
        Raises:
            ServiceShutdownError: If shutdown fails or resources cannot be cleaned up
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check the health status of the service.
        
        This method performs a health check to determine if the service is
        functioning correctly and is ready to handle requests. It should
        return quickly and not perform expensive operations.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        This method returns a list of capability identifiers that describe
        what functionality this service provides. This is used for service
        discovery and dependency resolution.
        
        Returns:
            List[str]: List of capability identifiers (e.g., ['backup', 'restore'])
        """
        pass

    def get_service_name(self) -> str:
        """
        Get the name of this service.
        
        Returns the service name for identification and logging purposes.
        Default implementation returns the class name.
        
        Returns:
            str: Service name identifier
        """
        return self.__class__.__name__

    def get_service_version(self) -> str:
        """
        Get the version of this service.
        
        Returns the service version for compatibility checking and debugging.
        Default implementation returns "1.0.0".
        
        Returns:
            str: Service version string
        """
        return "1.0.0"

    def validate_context(self, context: 'ServiceContext') -> bool:
        """
        Validate that the provided context contains required information.
        
        This method can be overridden by services to perform custom validation
        of the service context before initialization. Default implementation
        performs basic validation.
        
        Args:
            context: ServiceContext to validate
            
        Returns:
            bool: True if context is valid, False otherwise
        """
        if context is None:
            return False
        
        # Basic validation - ensure required components are present
        required_components = ['config_manager', 'event_bus', 'service_registry']
        for component in required_components:
            if not hasattr(context, component) or getattr(context, component) is None:
                return False
        
        return True