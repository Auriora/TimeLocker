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
Dependency Injection System for TimeLocker Integration Architecture

This module provides dependency injection capabilities for the TimeLocker service
architecture, including service registration, dependency resolution, and circular
dependency detection with support for optional dependencies.
"""

import logging
from typing import Dict, List, Type, TypeVar, Optional, Set, Any, Callable
from threading import Lock
from dataclasses import dataclass
from enum import Enum

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_exceptions import (
    DependencyResolutionError,
    ServiceRegistrationError,
    ServiceInitializationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


class DependencyType(Enum):
    """Types of dependencies that can be registered"""
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass
class ServiceRegistration:
    """
    Registration information for a service in the dependency injection container.
    
    This class holds all the metadata needed to manage service dependencies,
    including the service type, implementation, dependencies, and lifecycle hooks.
    """
    
    service_type: Type[ServiceInterface]
    """The service interface type"""
    
    implementation_type: Type[ServiceInterface]
    """The concrete implementation type"""
    
    instance: Optional[ServiceInterface] = None
    """Cached service instance (for singleton services)"""
    
    dependencies: List[Type[ServiceInterface]] = None
    """List of required dependencies"""
    
    optional_dependencies: List[Type[ServiceInterface]] = None
    """List of optional dependencies"""
    
    is_singleton: bool = True
    """Whether this service should be treated as a singleton"""
    
    factory_function: Optional[Callable[[], ServiceInterface]] = None
    """Optional factory function for creating service instances"""
    
    initialization_priority: int = 0
    """Priority for initialization order (higher = earlier)"""
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.dependencies is None:
            self.dependencies = []
        if self.optional_dependencies is None:
            self.optional_dependencies = []


class DependencyInjector:
    """
    Dependency injection container for TimeLocker services.
    
    This class manages service registration, dependency resolution, and provides
    dependency injection capabilities with support for circular dependency detection
    and optional dependencies with graceful degradation.
    
    Requirements addressed:
    - 1.3: Dependency injection for CLI components accessing backend services
    - 5.1: Dependency resolution ensuring services are initialized in correct order
    - 5.2: Circular dependency detection with clear error messages
    - 5.3: Optional dependencies allowing components to function with reduced capability
    - 5.5: Graceful degradation and service recovery mechanisms
    """
    
    def __init__(self):
        """Initialize the dependency injection container"""
        self._registrations: Dict[Type[ServiceInterface], ServiceRegistration] = {}
        self._instances: Dict[Type[ServiceInterface], ServiceInterface] = {}
        self._resolution_cache: Dict[Type[ServiceInterface], List[Type[ServiceInterface]]] = {}
        self._lock = Lock()
        self._is_resolving: Set[Type[ServiceInterface]] = set()
        
        logger.info("DependencyInjector initialized")
    
    def register_service(self, 
                        service_type: Type[T], 
                        implementation_type: Type[T] = None,
                        dependencies: List[Type[ServiceInterface]] = None,
                        optional_dependencies: List[Type[ServiceInterface]] = None,
                        is_singleton: bool = True,
                        factory_function: Optional[Callable[[], T]] = None,
                        initialization_priority: int = 0) -> None:
        """
        Register a service with the dependency injection container.
        
        Args:
            service_type: The service interface type to register
            implementation_type: The concrete implementation (defaults to service_type)
            dependencies: List of required service dependencies
            optional_dependencies: List of optional service dependencies
            is_singleton: Whether to treat as singleton (default: True)
            factory_function: Optional factory function for creating instances
            initialization_priority: Priority for initialization order (higher = earlier)
            
        Raises:
            ServiceRegistrationError: If registration fails or service already registered
        """
        with self._lock:
            if service_type in self._registrations:
                raise ServiceRegistrationError(
                    service_type.__name__,
                    f"Service type {service_type.__name__} is already registered"
                )
            
            # Use service_type as implementation if not specified
            if implementation_type is None:
                implementation_type = service_type
            
            # Validate that implementation implements the service interface
            if not issubclass(implementation_type, service_type):
                raise ServiceRegistrationError(
                    service_type.__name__,
                    f"Implementation {implementation_type.__name__} does not implement {service_type.__name__}"
                )
            
            # Validate dependencies exist or will be registered
            all_dependencies = (dependencies or []) + (optional_dependencies or [])
            for dep_type in all_dependencies:
                if not issubclass(dep_type, ServiceInterface):
                    raise ServiceRegistrationError(
                        service_type.__name__,
                        f"Dependency {dep_type.__name__} does not implement ServiceInterface"
                    )
            
            registration = ServiceRegistration(
                service_type=service_type,
                implementation_type=implementation_type,
                dependencies=dependencies or [],
                optional_dependencies=optional_dependencies or [],
                is_singleton=is_singleton,
                factory_function=factory_function,
                initialization_priority=initialization_priority
            )
            
            self._registrations[service_type] = registration
            
            # Clear resolution cache since dependencies may have changed
            self._resolution_cache.clear()
            
            logger.info(f"Registered service: {service_type.__name__} -> {implementation_type.__name__}")
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register a pre-created service instance.
        
        Args:
            service_type: The service interface type
            instance: The service instance to register
            
        Raises:
            ServiceRegistrationError: If registration fails
        """
        with self._lock:
            if not isinstance(instance, service_type):
                raise ServiceRegistrationError(
                    service_type.__name__,
                    f"Instance does not implement {service_type.__name__}"
                )
            
            # Register as singleton with existing instance
            registration = ServiceRegistration(
                service_type=service_type,
                implementation_type=type(instance),
                instance=instance,
                is_singleton=True
            )
            
            self._registrations[service_type] = registration
            self._instances[service_type] = instance
            
            # Clear resolution cache
            self._resolution_cache.clear()
            
            logger.info(f"Registered service instance: {service_type.__name__}")
    
    def resolve_service(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance with all its dependencies.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance with dependencies injected
            
        Raises:
            DependencyResolutionError: If resolution fails
        """
        with self._lock:
            return self._resolve_service_internal(service_type)
    
    def resolve_dependencies(self) -> Dict[Type[ServiceInterface], ServiceInterface]:
        """
        Resolve all registered services and their dependencies.
        
        Returns:
            Dictionary mapping service types to resolved instances
            
        Raises:
            DependencyResolutionError: If resolution fails for any service
        """
        # Get initialization order first (this acquires and releases lock)
        initialization_order = self.get_dependency_order()
        
        with self._lock:
            resolved_services = {}
            
            # Resolve services in dependency order
            for service_type in initialization_order:
                if service_type not in resolved_services:
                    try:
                        instance = self._resolve_service_internal(service_type)
                        resolved_services[service_type] = instance
                    except Exception as e:
                        logger.error(f"Failed to resolve service {service_type.__name__}: {e}")
                        raise DependencyResolutionError(
                            service_type.__name__,
                            missing_dependencies=[str(e)]
                        ) from e
            
            logger.info(f"Successfully resolved {len(resolved_services)} services")
            return resolved_services
    
    def get_dependency_order(self) -> List[Type[ServiceInterface]]:
        """
        Calculate the dependency initialization order for all registered services.
        
        Returns:
            List of service types in dependency order (dependencies first)
            
        Raises:
            DependencyResolutionError: If circular dependencies are detected
        """
        with self._lock:
            if not self._registrations:
                return []
            
            # Use cached result if available
            cache_key = tuple(sorted(self._registrations.keys(), key=lambda x: x.__name__))
            if cache_key in self._resolution_cache:
                return self._resolution_cache[cache_key].copy()
            
            # Perform topological sort with cycle detection
            visited = set()
            temp_visited = set()
            result = []
            
            def visit(service_type: Type[ServiceInterface], path: List[str] = None):
                if path is None:
                    path = []
                
                if service_type in temp_visited:
                    # Circular dependency detected
                    cycle_start = path.index(service_type.__name__)
                    cycle = path[cycle_start:] + [service_type.__name__]
                    raise DependencyResolutionError(
                        service_type.__name__,
                        circular_dependencies=cycle
                    )
                
                if service_type in visited:
                    return
                
                temp_visited.add(service_type)
                current_path = path + [service_type.__name__]
                
                # Visit required dependencies first
                registration = self._registrations.get(service_type)
                if registration:
                    for dep_type in registration.dependencies:
                        if dep_type not in self._registrations:
                            raise DependencyResolutionError(
                                service_type.__name__,
                                missing_dependencies=[dep_type.__name__]
                            )
                        visit(dep_type, current_path)
                    
                    # Visit optional dependencies if they are registered
                    for dep_type in registration.optional_dependencies:
                        if dep_type in self._registrations:
                            visit(dep_type, current_path)
                
                temp_visited.remove(service_type)
                visited.add(service_type)
                result.append(service_type)
            
            # Sort services by initialization priority first
            services_by_priority = sorted(
                self._registrations.keys(),
                key=lambda s: self._registrations[s].initialization_priority,
                reverse=True  # Higher priority first
            )
            
            # Visit all services
            for service_type in services_by_priority:
                if service_type not in visited:
                    visit(service_type)
            
            # Cache the result
            self._resolution_cache[cache_key] = result.copy()
            
            logger.debug(f"Calculated dependency order: {[s.__name__ for s in result]}")
            return result
    
    def get_optional_dependencies(self, service_type: Type[ServiceInterface]) -> List[Type[ServiceInterface]]:
        """
        Get the optional dependencies for a service type.
        
        Args:
            service_type: The service type to check
            
        Returns:
            List of optional dependency types
        """
        with self._lock:
            registration = self._registrations.get(service_type)
            if registration:
                return registration.optional_dependencies.copy()
            return []
    
    def get_available_optional_dependencies(self, service_type: Type[ServiceInterface]) -> List[Type[ServiceInterface]]:
        """
        Get the optional dependencies that are actually available (registered).
        
        Args:
            service_type: The service type to check
            
        Returns:
            List of available optional dependency types
        """
        with self._lock:
            registration = self._registrations.get(service_type)
            if not registration:
                return []
            
            available = []
            for dep_type in registration.optional_dependencies:
                if dep_type in self._registrations:
                    available.append(dep_type)
            
            return available
    
    def is_service_registered(self, service_type: Type[ServiceInterface]) -> bool:
        """
        Check if a service type is registered.
        
        Args:
            service_type: The service type to check
            
        Returns:
            True if service is registered, False otherwise
        """
        with self._lock:
            return service_type in self._registrations
    
    def get_registered_services(self) -> List[Type[ServiceInterface]]:
        """
        Get all registered service types.
        
        Returns:
            List of registered service types
        """
        with self._lock:
            return list(self._registrations.keys())
    
    def unregister_service(self, service_type: Type[ServiceInterface]) -> bool:
        """
        Unregister a service from the container.
        
        Args:
            service_type: The service type to unregister
            
        Returns:
            True if service was unregistered, False if not found
        """
        with self._lock:
            if service_type in self._registrations:
                del self._registrations[service_type]
                self._instances.pop(service_type, None)
                self._resolution_cache.clear()
                
                logger.info(f"Unregistered service: {service_type.__name__}")
                return True
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached instances and resolution cache"""
        with self._lock:
            self._instances.clear()
            self._resolution_cache.clear()
            logger.debug("Cleared dependency injection cache")
    
    def _resolve_service_internal(self, service_type: Type[T]) -> T:
        """
        Internal method to resolve a service instance.
        
        Args:
            service_type: The service type to resolve
            
        Returns:
            Service instance
            
        Raises:
            DependencyResolutionError: If resolution fails
        """
        # Check for circular resolution
        if service_type in self._is_resolving:
            raise DependencyResolutionError(
                service_type.__name__,
                circular_dependencies=[s.__name__ for s in self._is_resolving] + [service_type.__name__]
            )
        
        # Return cached instance if available
        if service_type in self._instances:
            return self._instances[service_type]
        
        # Get registration
        registration = self._registrations.get(service_type)
        if not registration:
            raise DependencyResolutionError(
                service_type.__name__,
                missing_dependencies=[service_type.__name__]
            )
        
        # Mark as resolving
        self._is_resolving.add(service_type)
        
        try:
            # Resolve required dependencies first
            resolved_dependencies = {}
            for dep_type in registration.dependencies:
                resolved_dependencies[dep_type] = self._resolve_service_internal(dep_type)
            
            # Resolve available optional dependencies
            for dep_type in registration.optional_dependencies:
                if dep_type in self._registrations:
                    try:
                        resolved_dependencies[dep_type] = self._resolve_service_internal(dep_type)
                        logger.debug(f"Resolved optional dependency {dep_type.__name__} for {service_type.__name__}")
                    except Exception as e:
                        logger.warning(f"Failed to resolve optional dependency {dep_type.__name__} for {service_type.__name__}: {e}")
                        # Continue without optional dependency (graceful degradation)
                else:
                    logger.debug(f"Optional dependency {dep_type.__name__} not available for {service_type.__name__}")
            
            # Create service instance
            if registration.factory_function:
                instance = registration.factory_function()
            else:
                try:
                    instance = registration.implementation_type()
                except Exception as e:
                    raise ServiceInitializationError(
                        service_type.__name__,
                        f"Failed to create instance: {e}"
                    ) from e
            
            # Inject dependencies if the instance supports it
            if hasattr(instance, 'inject_dependencies'):
                try:
                    instance.inject_dependencies(resolved_dependencies)
                except Exception as e:
                    logger.warning(f"Failed to inject dependencies for {service_type.__name__}: {e}")
                    # Continue without dependency injection
            
            # Cache instance if singleton
            if registration.is_singleton:
                self._instances[service_type] = instance
            
            logger.debug(f"Resolved service: {service_type.__name__}")
            return instance
            
        finally:
            # Remove from resolving set
            self._is_resolving.discard(service_type)
    
    def get_service_info(self, service_type: Type[ServiceInterface]) -> Dict[str, Any]:
        """
        Get detailed information about a registered service.
        
        Args:
            service_type: The service type to get info for
            
        Returns:
            Dictionary with service information
        """
        with self._lock:
            registration = self._registrations.get(service_type)
            if not registration:
                return {}
            
            # Calculate available optional dependencies without calling external method
            available_optional = []
            for dep_type in registration.optional_dependencies:
                if dep_type in self._registrations:
                    available_optional.append(dep_type.__name__)
            
            return {
                'service_type': service_type.__name__,
                'implementation_type': registration.implementation_type.__name__,
                'is_singleton': registration.is_singleton,
                'has_instance': service_type in self._instances,
                'dependencies': [dep.__name__ for dep in registration.dependencies],
                'optional_dependencies': [dep.__name__ for dep in registration.optional_dependencies],
                'available_optional_dependencies': available_optional,
                'initialization_priority': registration.initialization_priority,
                'has_factory': registration.factory_function is not None
            }