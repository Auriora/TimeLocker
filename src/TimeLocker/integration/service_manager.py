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
import time
from typing import Dict, Any, Type, TypeVar, Optional, List, Set, Callable
from threading import Lock
from datetime import datetime
from pathlib import Path

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import (
    ServiceInitializationError,
    ServiceShutdownError,
    ServiceDiscoveryError,
    ServiceRegistrationError,
    DependencyResolutionError,
    ServiceIntegrationError
)
from .event_bus import EventBus
from .error_propagation import (
    ErrorPropagationSystem, 
    ErrorSeverity, 
    ErrorCategory,
    propagate_error
)
from .service_optimization import ServiceOptimizationManager
from .security_integration import ServiceSecurityManager, SecureServiceProxy

# Import DependencyInjector with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .dependency_injector import DependencyInjector
    from ..security.security_service import SecurityService

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
    
    def __init__(self, context: ServiceContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the service manager.
        
        Args:
            context: Service context containing configuration and runtime information
            event_bus: Optional EventBus instance (will create one if not provided)
            
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
        
        # Initialize or use provided EventBus
        if event_bus is not None:
            self._event_bus = event_bus
        else:
            # Create EventBus with persistence if config manager provides storage path
            persistence_path = None
            if hasattr(context.config_manager, 'get_config_directory'):
                try:
                    config_dir = context.config_manager.get_config_directory()
                    if config_dir is not None:
                        persistence_path = Path(config_dir) / "events"
                except (AttributeError, TypeError):
                    # Handle cases where get_config_directory returns non-Path objects
                    pass
            
            self._event_bus = EventBus(persistence_path=persistence_path)
        
        # Update context to include the event bus
        if hasattr(context, 'event_bus') and context.event_bus is None:
            context.event_bus = self._event_bus
        
        # Initialize error propagation system with event bus
        self._error_propagation = ErrorPropagationSystem(event_bus=self._event_bus)
        
        # Initialize service optimization manager
        self._optimization_manager = ServiceOptimizationManager(
            event_bus=self._event_bus,
            max_async_workers=4
        )
        
        # Security integration (will be initialized when SecurityService is registered)
        self._security_manager: Optional[ServiceSecurityManager] = None
        self._security_enabled = False
        
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
    
    def get_service_by_name(self, service_name: str) -> ServiceInterface:
        """
        Get a service instance by name.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            ServiceDiscoveryError: If service is not found or not initialized
        """
        # Find service by name
        for service_type, service in self._registry.get_all_services().items():
            if service.get_service_name() == service_name:
                # Check if service is initialized
                if service_type not in self._initialized_services:
                    raise ServiceDiscoveryError(
                        service_name,
                        f"Service {service_name} is not initialized"
                    )
                return service
        
        raise ServiceDiscoveryError(
            service_name,
            f"Service {service_name} is not registered"
        )
    
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
                    
                    # Propagate error through error handling system
                    propagated_error = self._error_propagation.propagate_error(
                        exception=e,
                        operation="service_initialization",
                        component="ServiceManager",
                        service_name=service_type.__name__,
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.DEPENDENCY,
                        technical_details={
                            'service_type': service_type.__name__,
                            'initialization_order': [s.__name__ for s in initialization_order],
                            'initialized_count': initialized_count
                        }
                    )
                    
                    # Attempt recovery
                    recovery_result = self._error_propagation.attempt_error_recovery(propagated_error)
                    if recovery_result is None:
                        # Shutdown any services that were already initialized
                        self._shutdown_initialized_services()
                        raise ServiceInitializationError(service_type.__name__, str(e), e)
                    else:
                        logger.info(f"Recovered from service initialization error for {service_type.__name__}")
                        # Continue with initialization if recovery was successful
                        self._initialized_services.add(service_type)
                        self._shutdown_order.insert(0, service_type)
                        initialized_count += 1
            
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
                    
                    # Propagate shutdown error
                    self._error_propagation.propagate_error(
                        exception=e,
                        operation="service_shutdown",
                        component="ServiceManager",
                        service_name=service_type.__name__,
                        severity=ErrorSeverity.MEDIUM,
                        category=ErrorCategory.SYSTEM,
                        technical_details={'service_type': service_type.__name__}
                    )
                    
                    shutdown_errors.append(error_msg)
            
            self._shutdown_order.clear()
            
            # Shutdown optimization manager
            try:
                self._optimization_manager.shutdown()
                logger.info("ServiceOptimizationManager shut down successfully")
            except Exception as e:
                error_msg = f"Failed to shutdown ServiceOptimizationManager: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
            
            # Shutdown EventBus
            try:
                self._event_bus.shutdown()
                logger.info("EventBus shut down successfully")
            except Exception as e:
                error_msg = f"Failed to shutdown EventBus: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
            
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
    
    def set_dependency_injector(self, dependency_injector: 'DependencyInjector') -> None:
        """
        Set the dependency injector for advanced dependency management.
        
        This method allows the ServiceManager to use a DependencyInjector for
        more sophisticated dependency resolution, including optional dependencies
        and circular dependency detection.
        
        Args:
            dependency_injector: DependencyInjector instance to use
        """
        self._dependency_injector = dependency_injector
        logger.info("DependencyInjector integrated with ServiceManager")
    
    def register_service_with_injector(self, 
                                     service_type: Type[T], 
                                     implementation_type: Type[T] = None,
                                     dependencies: List[Type[ServiceInterface]] = None,
                                     optional_dependencies: List[Type[ServiceInterface]] = None,
                                     is_singleton: bool = True) -> None:
        """
        Register a service using the dependency injector.
        
        This method registers a service with both the ServiceManager and the
        DependencyInjector for advanced dependency management capabilities.
        
        Args:
            service_type: The service interface type to register
            implementation_type: The concrete implementation (defaults to service_type)
            dependencies: List of required service dependencies
            optional_dependencies: List of optional service dependencies
            is_singleton: Whether to treat as singleton (default: True)
            
        Raises:
            ServiceRegistrationError: If no dependency injector is set or registration fails
        """
        if not hasattr(self, '_dependency_injector'):
            raise ServiceRegistrationError(
                service_type.__name__,
                "No dependency injector configured. Call set_dependency_injector() first."
            )
        
        # Register with dependency injector
        self._dependency_injector.register_service(
            service_type=service_type,
            implementation_type=implementation_type,
            dependencies=dependencies,
            optional_dependencies=optional_dependencies,
            is_singleton=is_singleton
        )
        
        # Create instance using dependency injector
        instance = self._dependency_injector.resolve_service(service_type)
        
        # Register instance with ServiceManager
        self.register_service(service_type, instance, dependencies)
        
        logger.info(f"Registered service with dependency injection: {service_type.__name__}")
    
    def initialize_services_with_injector(self) -> bool:
        """
        Initialize services using the dependency injector for optimal ordering.
        
        This method uses the DependencyInjector to resolve all services and their
        dependencies in the correct order, then initializes them through the
        ServiceManager.
        
        Returns:
            True if all services initialized successfully, False otherwise
            
        Raises:
            ServiceInitializationError: If no dependency injector is set or initialization fails
        """
        if not hasattr(self, '_dependency_injector'):
            raise ServiceInitializationError(
                "ServiceManager",
                "No dependency injector configured. Call set_dependency_injector() first."
            )
        
        if self._is_shutting_down:
            raise ServiceInitializationError(
                "ServiceManager",
                "Cannot initialize services during shutdown"
            )
        
        try:
            # Resolve all services using dependency injector (this doesn't need the lock)
            resolved_services = self._dependency_injector.resolve_dependencies()
            
            with self._lock:
                # Register resolved services with ServiceManager if not already registered
                for service_type, instance in resolved_services.items():
                    if not self._registry.get(service_type):
                        # Get dependency info from injector
                        service_info = self._dependency_injector.get_service_info(service_type)
                        dependencies = [
                            dep_type for dep_name in service_info.get('dependencies', [])
                            for dep_type in resolved_services.keys()
                            if dep_type.__name__ == dep_name
                        ]
                        
                        self.register_service(service_type, instance, dependencies)
            
            # Initialize services using ServiceManager (this will acquire its own lock)
            return self.initialize_services()
            
        except Exception as e:
            logger.error(f"Failed to initialize services with dependency injector: {e}")
            raise ServiceInitializationError("ServiceManager", str(e), e)
    
    def get_dependency_injector(self) -> Optional['DependencyInjector']:
        """
        Get the current dependency injector instance.
        
        Returns:
            DependencyInjector instance or None if not set
        """
        return getattr(self, '_dependency_injector', None)
    
    def publish_event(self, event: Event) -> None:
        """
        Publish an event through the event bus.
        
        This method provides a convenient way for services to publish events
        through the ServiceManager without directly accessing the EventBus.
        
        Args:
            event: Event to publish
            
        Raises:
            EventPublishError: If event publishing fails
        """
        if self._is_shutting_down:
            logger.warning("Cannot publish event during shutdown")
            return
        
        try:
            self._event_bus.publish_event(event)
            logger.debug(f"Published event {event.event_id} of type {event.event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            raise
    
    def subscribe_event(self, 
                       event_type_pattern: Optional[str] = None,
                       handler: Optional[Callable[[Event], None]] = None,
                       source_pattern: Optional[str] = None,
                       min_priority: Optional[int] = None,
                       max_age_seconds: Optional[float] = None,
                       custom_filter: Optional[Callable[[Event], bool]] = None,
                       subscriber_name: Optional[str] = None) -> str:
        """
        Subscribe to events through the event bus.
        
        This method provides a convenient way for services to subscribe to events
        through the ServiceManager without directly accessing the EventBus.
        
        Args:
            event_type_pattern: Regex pattern for event types to subscribe to
            handler: Function to call when matching events are published
            source_pattern: Regex pattern for event sources
            min_priority: Minimum priority level to receive
            max_age_seconds: Maximum age for events to receive
            custom_filter: Custom filter function
            subscriber_name: Optional name for the subscriber
            
        Returns:
            Subscription ID that can be used to unsubscribe
            
        Raises:
            EventSubscriptionError: If subscription fails
        """
        if self._is_shutting_down:
            raise ServiceInitializationError("ServiceManager", "Cannot subscribe to events during shutdown")
        
        try:
            subscription_id = self._event_bus.subscribe_event(
                event_type_pattern=event_type_pattern,
                handler=handler,
                source_pattern=source_pattern,
                min_priority=min_priority,
                max_age_seconds=max_age_seconds,
                custom_filter=custom_filter,
                subscriber_name=subscriber_name
            )
            
            logger.debug(f"Created event subscription {subscription_id} for {subscriber_name or 'unknown'}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to create event subscription: {e}")
            raise
    
    def unsubscribe_event(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was removed, False if not found
        """
        try:
            result = self._event_bus.unsubscribe_event(subscription_id)
            if result:
                logger.debug(f"Removed event subscription {subscription_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove event subscription {subscription_id}: {e}")
            return False
    
    def get_event_bus(self) -> EventBus:
        """
        Get the EventBus instance.
        
        Returns:
            EventBus instance used by this ServiceManager
        """
        return self._event_bus
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get event bus statistics.
        
        Returns:
            Dictionary with event bus statistics
        """
        return self._event_bus.get_statistics()
    
    def propagate_service_error(self, 
                               exception: Exception, 
                               operation: str, 
                               service_name: str = "",
                               severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                               category: ErrorCategory = ErrorCategory.SYSTEM,
                               **kwargs) -> 'PropagatedError':
        """
        Propagate a service error through the error handling system.
        
        Args:
            exception: Exception to propagate
            operation: Operation being performed
            service_name: Name of the service where error occurred
            severity: Error severity level
            category: Error category
            **kwargs: Additional context information
            
        Returns:
            PropagatedError with full context
        """
        return self._error_propagation.propagate_error(
            exception=exception,
            operation=operation,
            component="ServiceManager",
            service_name=service_name,
            severity=severity,
            category=category,
            **kwargs
        )
    
    def attempt_service_recovery(self, propagated_error: 'PropagatedError') -> Optional[Any]:
        """
        Attempt to recover from a service error.
        
        Args:
            propagated_error: Error to attempt recovery for
            
        Returns:
            Recovery result if successful, None otherwise
        """
        return self._error_propagation.attempt_error_recovery(propagated_error)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error propagation statistics.
        
        Returns:
            Dictionary with error statistics
        """
        return self._error_propagation.get_error_statistics()
    
    def get_correlated_errors(self, correlation_id: str) -> List['ErrorContext']:
        """
        Get all errors with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of correlated error contexts
        """
        return self._error_propagation.get_correlated_errors(correlation_id)
    
    # Service Optimization Methods
    
    def create_service_connection_pool(self, 
                                     service_type: Type[ServiceInterface],
                                     min_connections: int = 1,
                                     max_connections: int = 10,
                                     max_idle_time_seconds: int = 300) -> None:
        """
        Create a connection pool for a service type to optimize performance.
        
        This method enables connection pooling for the specified service type,
        which reduces initialization overhead and improves performance for
        frequently used services.
        
        Args:
            service_type: Type of service to create pool for
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            max_idle_time_seconds: Maximum idle time before connection cleanup
            
        Requirements addressed:
        - 7.1: Service connection pooling and reuse to minimize initialization overhead
        """
        self._optimization_manager.create_connection_pool(
            service_type=service_type,
            min_connections=min_connections,
            max_connections=max_connections,
            max_idle_time_seconds=max_idle_time_seconds
        )
        
        logger.info(f"Created connection pool for {service_type.__name__}")
    
    def get_optimized_service(self, 
                            service_type: Type[T],
                            use_pooling: bool = True,
                            timeout_seconds: float = 10.0) -> T:
        """
        Get an optimized service instance with connection pooling support.
        
        This method provides an optimized way to get service instances that
        leverages connection pooling when available and tracks performance metrics.
        
        Args:
            service_type: Type of service to retrieve
            use_pooling: Whether to use connection pooling if available
            timeout_seconds: Timeout for getting connection from pool
            
        Returns:
            Optimized service instance
            
        Raises:
            ServiceDiscoveryError: If service is not registered or not initialized
            ServiceConnectionError: If unable to get connection from pool
            
        Requirements addressed:
        - 7.1: Service connection pooling and reuse to minimize initialization overhead
        - 7.3: Performance monitoring for service interactions
        """
        # Check if service is registered and initialized
        if service_type not in self._initialized_services:
            # Fall back to regular service discovery
            return self.get_service(service_type)
        
        # Use optimization manager to get service
        start_time = time.time()
        try:
            service = self._optimization_manager.get_optimized_service(
                service_type=service_type,
                context=self._context,
                use_pooling=use_pooling
            )
            
            # Record performance metrics
            operation_time = time.time() - start_time
            self._optimization_manager._performance_monitor.record_operation(
                service_name=service_type.__name__,
                operation_type='get_service',
                duration_seconds=operation_time,
                success=True
            )
            
            return service
            
        except Exception as e:
            # Record performance metrics for failed operation
            operation_time = time.time() - start_time
            self._optimization_manager._performance_monitor.record_operation(
                service_name=service_type.__name__,
                operation_type='get_service',
                duration_seconds=operation_time,
                success=False,
                error_message=str(e)
            )
            
            # Propagate error through error handling system
            propagated_error = self._error_propagation.propagate_error(
                exception=e,
                operation="get_optimized_service",
                component="ServiceManager",
                service_name=service_type.__name__,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.DEPENDENCY,
                technical_details={
                    'service_type': service_type.__name__,
                    'use_pooling': use_pooling,
                    'timeout_seconds': timeout_seconds
                }
            )
            
            raise ServiceDiscoveryError(service_type.__name__, str(e), e)
    
    def return_optimized_service(self, 
                               service: ServiceInterface,
                               operation_time: float = 0.0,
                               success: bool = True,
                               error: Optional[str] = None) -> None:
        """
        Return an optimized service instance to its pool.
        
        This method should be called when finished with a service instance
        obtained through get_optimized_service() to ensure proper cleanup
        and performance tracking.
        
        Args:
            service: Service instance to return
            operation_time: Time taken for the operation in seconds
            success: Whether the operation was successful
            error: Error message if operation failed
            
        Requirements addressed:
        - 7.1: Service connection pooling and reuse
        - 7.3: Performance monitoring for service interactions
        """
        self._optimization_manager.return_service(
            service=service,
            operation_time=operation_time,
            success=success,
            error=error
        )
    
    def submit_async_service_operation(self, 
                                     operation_id: str,
                                     operation_func: Callable,
                                     *args,
                                     progress_callback: Optional[Callable[[str, float], None]] = None,
                                     completion_callback: Optional[Callable[[str, Any], None]] = None,
                                     error_callback: Optional[Callable[[str, Exception], None]] = None,
                                     **kwargs) -> str:
        """
        Submit an asynchronous service operation for long-running tasks.
        
        This method enables asynchronous execution of service operations to
        maintain CLI responsiveness during long-running tasks.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_func: Function to execute asynchronously
            *args: Arguments for the operation function
            progress_callback: Optional callback for progress updates
            completion_callback: Optional callback for completion
            error_callback: Optional callback for errors
            **kwargs: Keyword arguments for the operation function
            
        Returns:
            Operation ID for tracking
            
        Requirements addressed:
        - 7.2: Asynchronous operation support for long-running tasks
        """
        return self._optimization_manager._async_manager.submit_async_operation(
            operation_id,
            operation_func,
            *args,
            progress_callback=progress_callback,
            completion_callback=completion_callback,
            error_callback=error_callback,
            **kwargs
        )
    
    def get_async_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Get the status of an asynchronous operation.
        
        Args:
            operation_id: ID of the operation to check
            
        Returns:
            Dictionary with operation status information
        """
        return self._optimization_manager._async_manager.get_operation_status(operation_id)
    
    def cancel_async_operation(self, operation_id: str) -> bool:
        """
        Cancel an asynchronous operation.
        
        Args:
            operation_id: ID of the operation to cancel
            
        Returns:
            True if operation was cancelled, False otherwise
        """
        return self._optimization_manager._async_manager.cancel_operation(operation_id)
    
    def set_performance_threshold(self, 
                                service_name: str,
                                operation_type: str,
                                max_duration_ms: float,
                                max_error_rate: float = 0.05,
                                min_throughput_ops_per_sec: Optional[float] = None,
                                alert_after_violations: int = 3) -> None:
        """
        Set performance threshold for service monitoring and alerts.
        
        This method configures performance thresholds that trigger alerts
        when service operations exceed acceptable performance limits.
        
        Args:
            service_name: Name of the service
            operation_type: Type of operation
            max_duration_ms: Maximum allowed duration in milliseconds
            max_error_rate: Maximum allowed error rate (0.0-1.0)
            min_throughput_ops_per_sec: Minimum required throughput
            alert_after_violations: Number of violations before alerting
            
        Requirements addressed:
        - 7.4: Performance alerts and optimization recommendations
        """
        self._optimization_manager.set_performance_threshold(
            service_name=service_name,
            operation_type=operation_type,
            max_duration_ms=max_duration_ms,
            max_error_rate=max_error_rate,
            min_throughput_ops_per_sec=min_throughput_ops_per_sec,
            alert_after_violations=alert_after_violations
        )
        
        logger.info(f"Set performance threshold for {service_name}.{operation_type}: {max_duration_ms}ms")
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive service optimization statistics.
        
        This method provides detailed statistics about connection pooling,
        asynchronous operations, performance monitoring, and bottleneck analysis.
        
        Returns:
            Dictionary with optimization statistics including:
            - Connection pool statistics
            - Active async operations
            - Performance summaries
            - Bottleneck analysis
            - Optimization recommendations
            
        Requirements addressed:
        - 7.3: Performance monitoring for service interactions with bottleneck identification
        - 7.4: Performance alerts and optimization recommendations
        """
        return self._optimization_manager.get_optimization_statistics()
    
    def get_performance_recommendations(self) -> List[str]:
        """
        Get performance optimization recommendations.
        
        Returns:
            List of optimization recommendations based on current performance data
            
        Requirements addressed:
        - 7.4: Performance alerts and optimization recommendations
        """
        stats = self.get_optimization_statistics()
        return stats.get('bottleneck_analysis', {}).get('recommendations', [])
    
    def get_service_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Get identified service bottlenecks.
        
        Returns:
            List of service bottlenecks with performance metrics
            
        Requirements addressed:
        - 7.3: Performance monitoring for service interactions with bottleneck identification
        """
        stats = self.get_optimization_statistics()
        return stats.get('bottleneck_analysis', {}).get('bottlenecks', [])
    
    # Security Integration Methods
    
    def enable_security_integration(self, security_service: 'SecurityService') -> None:
        """
        Enable security integration for service communication.
        
        This method initializes the security manager and enables authentication,
        authorization, and audit logging for all service interactions.
        
        Args:
            security_service: SecurityService instance to use for security operations
            
        Requirements addressed:
        - 8.1: Secure inter-service communication
        - 8.2: Service authentication and authorization
        - 8.3: Audit logging for service interactions
        """
        if self._security_manager is not None:
            logger.warning("Security integration already enabled")
            return
        
        self._security_manager = ServiceSecurityManager(
            security_service=security_service,
            event_bus=self._event_bus
        )
        self._security_enabled = True
        
        logger.info("Security integration enabled for service communication")
    
    def disable_security_integration(self) -> None:
        """
        Disable security integration for service communication.
        
        This method disables security checks but maintains audit logging
        for compliance purposes.
        """
        if self._security_manager is not None:
            self._security_manager.configure_security(
                require_authentication=False,
                require_authorization=False,
                audit_all_interactions=True
            )
        
        self._security_enabled = False
        logger.info("Security integration disabled (audit logging maintained)")
    
    def configure_service_security(self, 
                                 require_authentication: bool = True,
                                 require_authorization: bool = True,
                                 audit_all_interactions: bool = True,
                                 audit_sensitive_only: bool = False) -> None:
        """
        Configure security settings for service communication.
        
        Args:
            require_authentication: Whether to require service authentication
            require_authorization: Whether to require service authorization
            audit_all_interactions: Whether to audit all service interactions
            audit_sensitive_only: Whether to audit only sensitive interactions
        """
        if self._security_manager is None:
            logger.warning("Security integration not enabled")
            return
        
        self._security_manager.configure_security(
            require_authentication=require_authentication,
            require_authorization=require_authorization,
            audit_all_interactions=audit_all_interactions,
            audit_sensitive_only=audit_sensitive_only
        )
        
        logger.info("Service security configuration updated")
    
    def get_secure_service(self, service_type: Type[T], source_service_name: str = "unknown") -> T:
        """
        Get a secure service proxy that enforces security policies.
        
        This method returns a proxy that wraps the requested service with
        security checks including authentication, authorization, and audit logging.
        
        Args:
            service_type: Type of the service to retrieve
            source_service_name: Name of the service requesting access
            
        Returns:
            Secure service proxy with security enforcement
            
        Raises:
            ServiceDiscoveryError: If service is not found or not initialized
            ServiceIntegrationError: If security checks fail
            
        Requirements addressed:
        - 8.1: Secure inter-service communication
        - 8.4: Service isolation preventing unauthorized access
        """
        # Get the base service
        base_service = self.get_service(service_type)
        
        # If security is not enabled, return the base service
        if not self._security_enabled or self._security_manager is None:
            return base_service
        
        # Check if service is isolated
        target_service_name = base_service.get_service_name()
        if self._security_manager.is_service_isolated(target_service_name):
            raise ServiceIntegrationError(f"Access denied: service {target_service_name} is isolated")
        
        # Return secure proxy
        return SecureServiceProxy(
            target_service=base_service,
            security_manager=self._security_manager,
            source_service_name=source_service_name
        )
    
    def register_service_credentials(self, service_name: str, credentials: Dict[str, Any]) -> None:
        """
        Register authentication credentials for a service.
        
        Args:
            service_name: Name of the service
            credentials: Authentication credentials
            
        Requirements addressed:
        - 8.2: Service authentication and authorization
        """
        if self._security_manager is None:
            logger.warning("Security integration not enabled")
            return
        
        from .security_integration import ServiceCredentials, ServiceAuthenticationMethod
        
        # Create ServiceCredentials object
        auth_method = ServiceAuthenticationMethod(credentials.get("method", "context_based"))
        service_credentials = ServiceCredentials(
            service_name=service_name,
            authentication_method=auth_method,
            token=credentials.get("token"),
            certificate_path=credentials.get("certificate_path"),
            shared_secret=credentials.get("shared_secret"),
            expires_at=credentials.get("expires_at"),
            metadata=credentials.get("metadata", {})
        )
        
        self._security_manager.register_service_credentials(service_credentials)
        logger.info(f"Registered credentials for service: {service_name}")
    
    def add_service_authorization_rule(self, 
                                     source_service: str,
                                     target_service: str,
                                     operation: str,
                                     permission: str,
                                     conditions: Dict[str, Any] = None) -> None:
        """
        Add an authorization rule for service operations.
        
        Args:
            source_service: Source service name (use "*" for any)
            target_service: Target service name (use "*" for any)
            operation: Operation name (use "*" for any)
            permission: Permission level (read, write, admin, system)
            conditions: Optional conditions for the rule
            
        Requirements addressed:
        - 8.2: Service authentication and authorization
        """
        if self._security_manager is None:
            logger.warning("Security integration not enabled")
            return
        
        from .security_integration import ServiceAuthorizationRule, ServicePermission
        
        rule = ServiceAuthorizationRule(
            source_service=source_service,
            target_service=target_service,
            operation=operation,
            permission=ServicePermission(permission),
            conditions=conditions or {}
        )
        
        self._security_manager.add_authorization_rule(rule)
        logger.info(f"Added authorization rule: {source_service} -> {target_service}.{operation}")
    
    def isolate_service(self, service_name: str) -> None:
        """
        Isolate a service to prevent unauthorized access.
        
        Args:
            service_name: Name of the service to isolate
            
        Requirements addressed:
        - 8.4: Service isolation preventing unauthorized access
        """
        if self._security_manager is None:
            logger.warning("Security integration not enabled")
            return
        
        self._security_manager.isolate_service(service_name)
        logger.warning(f"Service isolated: {service_name}")
    
    def remove_service_isolation(self, service_name: str) -> None:
        """
        Remove isolation from a service.
        
        Args:
            service_name: Name of the service to remove isolation from
        """
        if self._security_manager is None:
            logger.warning("Security integration not enabled")
            return
        
        self._security_manager.remove_service_isolation(service_name)
        logger.info(f"Service isolation removed: {service_name}")
    
    def get_service_audit_records(self, 
                                hours: int = 24,
                                source_service: Optional[str] = None,
                                target_service: Optional[str] = None,
                                sensitive_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get audit records for service interactions.
        
        Args:
            hours: Number of hours to look back
            source_service: Filter by source service
            target_service: Filter by target service
            sensitive_only: Only return records for sensitive interactions
            
        Returns:
            List of audit records as dictionaries
            
        Requirements addressed:
        - 8.3: Audit logging for service interactions
        """
        if self._security_manager is None:
            return []
        
        records = self._security_manager.get_audit_records(
            hours=hours,
            source_service=source_service,
            target_service=target_service,
            sensitive_only=sensitive_only
        )
        
        # Convert to dictionaries for easier consumption
        return [
            {
                "interaction_id": record.interaction_id,
                "source_service": record.source_service,
                "target_service": record.target_service,
                "operation": record.operation,
                "timestamp": record.timestamp.isoformat(),
                "success": record.success,
                "duration_ms": record.duration_ms,
                "data_size_bytes": record.data_size_bytes,
                "sensitive_data": record.sensitive_data,
                "error_message": record.error_message,
                "metadata": record.metadata
            }
            for record in records
        ]
    
    def get_service_security_status(self) -> Dict[str, Any]:
        """
        Get comprehensive security status for service communication.
        
        Returns:
            Dictionary with security status information
            
        Requirements addressed:
        - 8.1: Secure inter-service communication monitoring
        """
        if self._security_manager is None:
            return {
                "security_enabled": False,
                "message": "Security integration not enabled"
            }
        
        status = self._security_manager.get_security_status()
        status["security_enabled"] = self._security_enabled
        
        return status
    
    def cleanup_security_data(self) -> Dict[str, int]:
        """
        Clean up expired security data.
        
        Returns:
            Dictionary with cleanup statistics
        """
        if self._security_manager is None:
            return {"expired_credentials": 0}
        
        expired_credentials = self._security_manager.cleanup_expired_credentials()
        
        return {
            "expired_credentials": expired_credentials
        }