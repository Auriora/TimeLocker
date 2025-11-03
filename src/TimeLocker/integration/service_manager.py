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
Service Manager for TimeLocker Integration Architecture

This module provides the core ServiceManager class that orchestrates service
lifecycle, discovery, and health monitoring across the TimeLocker system.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Optional, List, Set
from threading import Lock
from datetime import datetime

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import (
    ServiceInitializationError,
    ServiceShutdownError,
    ServiceDiscoveryError,
    ServiceRegistrationError,
    DependencyResolutionError
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


class ServiceRegistry:
    """
    Registry for managing service instances and metadata.
    
    This class maintains the registry of services, their types, and metadata
    for service discovery and lifecycle management.
    """
    
    def __init__(self):
        """Initialize empty service registry"""
        self._services: Dict[Type[ServiceInterface], ServiceInterface] = {}
        self._service_metadata: Dict[Type[ServiceInterface], Dict[str, Any]] = {}
        self._lock = Lock()
    
    def register(self, service_type: Type[T], service_instance: T, metadata: Dict[str, Any] = None) -> None:
        """
        Register a service instance with the registry.
        
        Args:
            service_type: Type of the service interface
            service_instance: Instance of the service
            metadata: Optional metadata about the service
            
        Raises:
            ServiceRegistrationError: If registration fails
        """
        with self._lock:
            if service_type in self._services:
                raise ServiceRegistrationError(
                    service_type.__name__,
                    f"Service type {service_type.__name__} is already registered"
                )
            
            self._services[service_type] = service_instance
            self._service_metadata[service_type] = metadata or {}
            
            logger.debug(f"Registered service: {service_type.__name__}")
    
    def get(self, service_type: Type[T]) -> Optional[T]:
        """
        Get a service instance by type.
        
        Args:
            service_type: Type of the service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        with self._lock:
            return self._services.get(service_type)
    
    def unregister(self, service_type: Type[ServiceInterface]) -> bool:
        """
        Unregister a service from the registry.
        
        Args:
            service_type: Type of the service to unregister
            
        Returns:
            True if service was unregistered, False if not found
        """
        with self._lock:
            if service_type in self._services:
                del self._services[service_type]
                self._service_metadata.pop(service_type, None)
                logger.debug(f"Unregistered service: {service_type.__name__}")
                return True
            return False
    
    def get_all_services(self) -> Dict[Type[ServiceInterface], ServiceInterface]:
        """
        Get all registered services.
        
        Returns:
            Dictionary of service types to instances
        """
        with self._lock:
            return self._services.copy()
    
    def get_service_metadata(self, service_type: Type[ServiceInterface]) -> Dict[str, Any]:
        """
        Get metadata for a service.
        
        Args:
            service_type: Type of the service
            
        Returns:
            Service metadata dictionary
        """
        with self._lock:
            return self._service_metadata.get(service_type, {}).copy()
    
    def get_services_by_capability(self, capability: str) -> List[ServiceInterface]:
        """
        Get services that provide a specific capability.
        
        Args:
            capability: Capability identifier to search for
            
        Returns:
            List of services that provide the capability
        """
        matching_services = []
        with self._lock:
            for service in self._services.values():
                try:
                    if capability in service.get_capabilities():
                        matching_services.append(service)
                except Exception as e:
                    logger.warning(f"Error checking capabilities for {service.get_service_name()}: {e}")
        
        return matching_services


class ServiceManager:
    """
    Central service manager for TimeLocker integration architecture.
    
    This class provides service lifecycle management, discovery, registration,
    and health monitoring capabilities for the TimeLocker system.
    
    Requirements addressed:
    - 1.1: CLI Service Manager that orchestrates all backend services
    - 1.2: Service discovery allowing CLI to locate and connect to services
    - 1.4: Service lifecycle management ensuring services are available
    - 5.1: Dependency resolution ensuring services are initialized in correct order
    - 5.4: Dependency health checking to ensure required services remain available
    """
    
    def __init__(self, context: ServiceContext):
        """
        Initialize the service manager.
        
        Args:
            context: Service context containing configuration and runtime information
            
        Raises:
            ServiceInitializationError: If initialization fails
        """
        if not isinstance(context, ServiceContext):
            raise ServiceInitializationError(
                "ServiceManager",
                "Invalid service context provided"
            )
        
        self._context = context
        self._registry = ServiceRegistry()
        self._initialized_services: Set[Type[ServiceInterface]] = set()
        self._shutdown_order: List[Type[ServiceInterface]] = []
        self._lock = Lock()
        self._is_shutting_down = False
        
        logger.info("ServiceManager initialized")
    
    def register_service(self, service_type: Type[T], service_instance: T, 
                        dependencies: List[Type[ServiceInterface]] = None) -> None:
        """
        Register a service with the service manager.
        
        Args:
            service_type: Type of the service interface
            service_instance: Instance of the service to register
            dependencies: List of service types this service depends on
            
        Raises:
            ServiceRegistrationError: If registration fails
        """
        if self._is_shutting_down:
            raise ServiceRegistrationError(
                service_type.__name__,
                "Cannot register services during shutdown"
            )
        
        if not isinstance(service_instance, ServiceInterface):
            raise ServiceRegistrationError(
                service_type.__name__,
                f"Service must implement ServiceInterface"
            )
        
        # Validate service context compatibility
        if not service_instance.validate_context(self._context):
            raise ServiceRegistrationError(
                service_type.__name__,
                "Service failed context validation"
            )
        
        metadata = {
            'dependencies': dependencies or [],
            'registered_at': datetime.now(),
            'service_name': service_instance.get_service_name(),
            'service_version': service_instance.get_service_version(),
            'capabilities': service_instance.get_capabilities()
        }
        
        self._registry.register(service_type, service_instance, metadata)
        
        logger.info(f"Registered service: {service_type.__name__}")
    
    def get_service(self, service_type: Type[T]) -> T:
        """
        Get a service instance by type.
        
        Args:
            service_type: Type of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            ServiceDiscoveryError: If service is not found or not initialized
        """
        service = self._registry.get(service_type)
        if service is None:
            raise ServiceDiscoveryError(
                service_type.__name__,
                f"Service {service_type.__name__} is not registered"
            )
        
        # Check if service is initialized
        if service_type not in self._initialized_services:
            raise ServiceDiscoveryError(
                service_type.__name__,
                f"Service {service_type.__name__} is not initialized"
            )
        
        return service
    
    def initialize_services(self) -> bool:
        """
        Initialize all registered services in dependency order.
        
        Returns:
            True if all services initialized successfully, False otherwise
            
        Raises:
            ServiceInitializationError: If initialization fails
        """
        with self._lock:
            if self._is_shutting_down:
                raise ServiceInitializationError(
                    "ServiceManager",
                    "Cannot initialize services during shutdown"
                )
            
            # Get initialization order based on dependencies
            try:
                initialization_order = self._resolve_initialization_order()
            except DependencyResolutionError as e:
                raise ServiceInitializationError("ServiceManager", str(e), e)
            
            # Initialize services in order
            initialized_count = 0
            for service_type in initialization_order:
                service = self._registry.get(service_type)
                if service is None:
                    continue
                
                try:
                    logger.info(f"Initializing service: {service_type.__name__}")
                    
                    # Create service-specific context if needed
                    service_context = self._create_service_context(service_type)
                    
                    # Initialize the service
                    success = service.initialize(service_context)
                    if not success:
                        raise ServiceInitializationError(
                            service_type.__name__,
                            "Service initialization returned False"
                        )
                    
                    self._initialized_services.add(service_type)
                    self._shutdown_order.insert(0, service_type)  # Reverse order for shutdown
                    initialized_count += 1
                    
                    logger.info(f"Successfully initialized service: {service_type.__name__}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize service {service_type.__name__}: {e}")
                    # Shutdown any services that were already initialized
                    self._shutdown_initialized_services()
                    raise ServiceInitializationError(service_type.__name__, str(e), e)
            
            logger.info(f"Successfully initialized {initialized_count} services")
            return True
    
    def shutdown_services(self) -> None:
        """
        Shutdown all initialized services in reverse initialization order.
        
        Raises:
            ServiceShutdownError: If shutdown fails for any service
        """
        with self._lock:
            self._is_shutting_down = True
            
            shutdown_errors = []
            
            # Shutdown services in reverse order
            for service_type in self._shutdown_order:
                if service_type not in self._initialized_services:
                    continue
                
                service = self._registry.get(service_type)
                if service is None:
                    continue
                
                try:
                    logger.info(f"Shutting down service: {service_type.__name__}")
                    service.shutdown()
                    self._initialized_services.discard(service_type)
                    logger.info(f"Successfully shut down service: {service_type.__name__}")
                    
                except Exception as e:
                    error_msg = f"Failed to shutdown service {service_type.__name__}: {e}"
                    logger.error(error_msg)
                    shutdown_errors.append(error_msg)
            
            self._shutdown_order.clear()
            
            if shutdown_errors:
                raise ServiceShutdownError(
                    "ServiceManager",
                    f"Shutdown completed with errors: {'; '.join(shutdown_errors)}"
                )
            
            logger.info("All services shut down successfully")
    
    def health_check(self) -> Dict[str, bool]:
        """
        Perform health checks on all initialized services.
        
        Returns:
            Dictionary mapping service names to health status (True = healthy)
        """
        health_status = {}
        
        for service_type in self._initialized_services:
            service = self._registry.get(service_type)
            if service is None:
                health_status[service_type.__name__] = False
                continue
            
            try:
                is_healthy = service.health_check()
                health_status[service_type.__name__] = is_healthy
                
                if not is_healthy:
                    logger.warning(f"Service {service_type.__name__} failed health check")
                
            except Exception as e:
                logger.error(f"Health check failed for service {service_type.__name__}: {e}")
                health_status[service_type.__name__] = False
        
        return health_status
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive status information for all services.
        
        Returns:
            Dictionary with detailed service status information
        """
        status = {}
        
        all_services = self._registry.get_all_services()
        for service_type, service in all_services.items():
            service_name = service_type.__name__
            metadata = self._registry.get_service_metadata(service_type)
            
            status[service_name] = {
                'registered': True,
                'initialized': service_type in self._initialized_services,
                'healthy': False,
                'service_name': service.get_service_name(),
                'service_version': service.get_service_version(),
                'capabilities': service.get_capabilities(),
                'registered_at': metadata.get('registered_at'),
                'dependencies': [dep.__name__ for dep in metadata.get('dependencies', [])]
            }
            
            # Check health if initialized
            if service_type in self._initialized_services:
                try:
                    status[service_name]['healthy'] = service.health_check()
                except Exception as e:
                    status[service_name]['healthy'] = False
                    status[service_name]['health_error'] = str(e)
        
        return status
    
    def find_services_by_capability(self, capability: str) -> List[ServiceInterface]:
        """
        Find services that provide a specific capability.
        
        Args:
            capability: Capability identifier to search for
            
        Returns:
            List of initialized services that provide the capability
        """
        matching_services = []
        
        for service_type in self._initialized_services:
            service = self._registry.get(service_type)
            if service is None:
                continue
            
            try:
                if capability in service.get_capabilities():
                    matching_services.append(service)
            except Exception as e:
                logger.warning(f"Error checking capabilities for {service.get_service_name()}: {e}")
        
        return matching_services
    
    def _resolve_initialization_order(self) -> List[Type[ServiceInterface]]:
        """
        Resolve service initialization order based on dependencies.
        
        Returns:
            List of service types in initialization order
            
        Raises:
            DependencyResolutionError: If circular dependencies are detected
        """
        all_services = self._registry.get_all_services()
        if not all_services:
            return []
        
        # Build dependency graph
        dependencies = {}
        for service_type in all_services.keys():
            metadata = self._registry.get_service_metadata(service_type)
            dependencies[service_type] = metadata.get('dependencies', [])
        
        # Topological sort with cycle detection
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(service_type):
            if service_type in temp_visited:
                # Circular dependency detected
                cycle_path = list(temp_visited) + [service_type]
                cycle_names = [s.__name__ for s in cycle_path]
                raise DependencyResolutionError(
                    service_type.__name__,
                    circular_dependencies=cycle_names
                )
            
            if service_type in visited:
                return
            
            temp_visited.add(service_type)
            
            # Visit dependencies first
            for dep_type in dependencies.get(service_type, []):
                if dep_type not in all_services:
                    raise DependencyResolutionError(
                        service_type.__name__,
                        missing_dependencies=[dep_type.__name__]
                    )
                visit(dep_type)
            
            temp_visited.remove(service_type)
            visited.add(service_type)
            result.append(service_type)
        
        # Visit all services
        for service_type in all_services.keys():
            if service_type not in visited:
                visit(service_type)
        
        return result
    
    def _create_service_context(self, service_type: Type[ServiceInterface]) -> ServiceContext:
        """
        Create service-specific context for initialization.
        
        Args:
            service_type: Type of service to create context for
            
        Returns:
            ServiceContext for the service
        """
        # For now, return the base context
        # In the future, this could be customized per service
        return self._context
    
    def _shutdown_initialized_services(self) -> None:
        """Shutdown services that have been initialized (used during error recovery)"""
        for service_type in reversed(self._shutdown_order):
            if service_type not in self._initialized_services:
                continue
            
            service = self._registry.get(service_type)
            if service is None:
                continue
            
            try:
                logger.info(f"Emergency shutdown of service: {service_type.__name__}")
                service.shutdown()
                self._initialized_services.discard(service_type)
            except Exception as e:
                logger.error(f"Error during emergency shutdown of {service_type.__name__}: {e}")
        
        self._shutdown_order.clear()