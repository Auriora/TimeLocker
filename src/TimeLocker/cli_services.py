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
CLI Service Integration Layer

This module provides a service layer that integrates the new service-oriented
architecture with the CLI, maintaining backward compatibility while leveraging
modern SOLID principles and the new integration architecture.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Type
from dataclasses import dataclass

from .interfaces import (
    IRepositoryFactory,
    IConfigurationProvider,
    IBackupOrchestrator,
    BackupResult,
    BackupStatus,
    ConfigurationError
)
from .interfaces.service_interface import ServiceInterface
from .interfaces.integration_data_models import ServiceContext, Event
from .interfaces.integration_exceptions import (
    ServiceInitializationError,
    ServiceDiscoveryError,
    DependencyResolutionError
)
from .services import (
    RepositoryFactory,
    # ConfigurationService,  # TODO: Does not exist, needs to be implemented
    # BackupOrchestrator,  # TODO: Does not exist, needs to be implemented
    ValidationService
)
from .services.snapshot_service import SnapshotService
from .services.repository_service import RepositoryService
from .utils.performance_utils import PerformanceModule
from .config.configuration_module import ConfigurationModule
from .config.configuration_path_resolver import ConfigurationPathResolver
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType
from .security.credential_manager import CredentialManagerError
from .integration.service_manager import ServiceManager, ServiceRegistry
from .integration.dependency_injector import DependencyInjector
from .integration.event_bus import EventBus
from .cli_modules.monitoring_integration import CLIMonitoringIntegration

logger = logging.getLogger(__name__)


class LegacyServiceWrapper(ServiceInterface):
    """
    Wrapper class to integrate legacy services with the new ServiceInterface.
    
    This wrapper allows existing services to participate in the new integration
    architecture without requiring immediate refactoring of the legacy code.
    """
    
    def __init__(self, legacy_service: Any, service_name: str, capabilities: List[str]):
        """
        Initialize the legacy service wrapper.
        
        Args:
            legacy_service: The legacy service instance to wrap
            service_name: Name for the service
            capabilities: List of capabilities provided by the service
        """
        self._legacy_service = legacy_service
        self._service_name = service_name
        self._capabilities = capabilities
        self._initialized = False
    
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the legacy service.
        
        Args:
            context: Service context (may not be used by legacy services)
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Most legacy services don't have explicit initialization
            # Just mark as initialized if the service exists
            if self._legacy_service is not None:
                self._initialized = True
                logger.debug(f"Legacy service {self._service_name} initialized")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize legacy service {self._service_name}: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the legacy service."""
        try:
            # Most legacy services don't have explicit shutdown
            # Just mark as not initialized
            self._initialized = False
            logger.debug(f"Legacy service {self._service_name} shut down")
        except Exception as e:
            logger.error(f"Error shutting down legacy service {self._service_name}: {e}")
    
    def health_check(self) -> bool:
        """
        Check health of the legacy service.
        
        Returns:
            bool: True if service is healthy
        """
        try:
            # Basic health check - service exists and is initialized
            return self._legacy_service is not None and self._initialized
        except Exception as e:
            logger.error(f"Health check failed for legacy service {self._service_name}: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Get capabilities provided by the legacy service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        return self._capabilities.copy()
    
    def get_service_name(self) -> str:
        """
        Get the service name.
        
        Returns:
            str: Service name
        """
        return self._service_name
    
    def get_service_version(self) -> str:
        """
        Get the service version.
        
        Returns:
            str: Service version
        """
        return "legacy-1.0.0"
    
    def get_legacy_service(self) -> Any:
        """
        Get the wrapped legacy service instance.
        
        Returns:
            Any: The original legacy service
        """
        return self._legacy_service


@dataclass
class CLIBackupRequest:
    """Represents a backup request from the CLI"""
    sources: List[Path]
    repository_uri: str
    password: Optional[str] = None
    target_name: Optional[str] = None
    backup_name: Optional[str] = None
    tags: List[str] = None
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    dry_run: bool = False

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.include_patterns is None:
            self.include_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


class CLIServiceManager:
    """
    Enhanced service manager for CLI operations that integrates with the new service architecture.
    
    This class provides a unified interface for CLI operations while leveraging the new
    ServiceManager, DependencyInjector, and EventBus for service orchestration, dependency
    management, and event-driven communication.
    
    Requirements addressed:
    - 1.1: CLI Service Manager that orchestrates all backend services
    - 1.2: Service discovery allowing CLI to locate and connect to services
    - 1.3: Dependency injection for CLI components accessing backend services
    - 6.1: Service context containing configuration and runtime state
    - 6.2: Context inheritance for child operations
    - 6.3: Context validation for required information
    - 6.4: Context cleanup mechanisms
    - 6.5: Fallback mechanisms and clear error reporting
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize CLI service manager with enhanced integration architecture"""
        import sys
        self._config_dir = Path(config_dir) if config_dir is not None else None
        self._is_initialized = False
        self._service_context: Optional[ServiceContext] = None
        
        # Initialize configuration (legacy system for compatibility)
        self._config_module = ConfigurationModule(config_dir=self._config_dir)
        
        # Initialize legacy services for backward compatibility
        self._validation_service = ValidationService()
        self._repository_factory = RepositoryFactory(validation_service=self._validation_service)
        self._performance_module = PerformanceModule()
        
        # Initialize modern config service
        # TODO: ConfigurationService does not exist yet, needs to be implemented
        # try:
        #     self._config_service = ConfigurationService(
        #             config_path=self._config_module.config_file,
        #             validation_service=self._validation_service
        #     )
        # except Exception as e:
        #     logger.warning(f"Configuration service failed to initialize: {e}")
        #     self._config_service = None
        self._config_service = None  # Placeholder until ConfigurationService is implemented

        # Initialize legacy services
        self._snapshot_service = SnapshotService(
                validation_service=self._validation_service,
                performance_module=self._performance_module
        )

        self._repository_service = RepositoryService(
                validation_service=self._validation_service,
                performance_module=self._performance_module
        )
        self._configure_repository_factory_credentials()

        # Initialize BackupOrchestrator with proper dependencies
        try:
            from .services.backup_orchestrator import BackupOrchestrator
            from .services.configuration_service import ConfigurationService
            
            # Create configuration service as provider
            config_provider = ConfigurationService(
                config_path=self._config_module.config_file
            )
            
            self._backup_orchestrator = BackupOrchestrator(
                configuration_provider=config_provider,
                repository_factory=self._repository_factory
            )
            logger.debug("BackupOrchestrator initialized successfully")
        except Exception as e:
            logger.warning(f"BackupOrchestrator failed to initialize: {e}")
            self._backup_orchestrator = None
        
        # Initialize new integration architecture components
        self._service_registry = ServiceRegistry()
        self._dependency_injector = DependencyInjector()
        self._event_bus: Optional[EventBus] = None
        self._service_manager: Optional[ServiceManager] = None
        
        # Initialize monitoring integration for CLI
        self._monitoring_integration: Optional[CLIMonitoringIntegration] = None
        
        # Initialize the integration architecture
        self._initialize_integration_architecture()

        logger.debug("Enhanced CLIServiceManager initialized")

    def _configure_repository_factory_credentials(self) -> None:
        """Ensure repository factory uses credential storage aligned with config directory."""
        try:
            from .security.credential_manager import CredentialManager  # lazy import to avoid cycles

            credential_manager = CredentialManager()
            try:
                credential_manager.ensure_unlocked(allow_prompt=False)
            except Exception as exc:  # pragma: no cover - best effort
                logger.debug("Credential manager pre-unlock failed: %s", exc)
            self._repository_factory._credential_manager = credential_manager
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug("Falling back to default credential manager: %s", exc)
    
    def _initialize_integration_architecture(self) -> None:
        """
        Initialize the new integration architecture components.
        
        This method sets up the ServiceManager, DependencyInjector, and EventBus
        for enhanced service orchestration and dependency management.
        
        Raises:
            ServiceInitializationError: If integration architecture initialization fails
        """
        try:
            # Create EventBus with persistence
            persistence_path = None
            if self._config_dir:
                persistence_path = self._config_dir / "events"
            
            self._event_bus = EventBus(persistence_path=persistence_path)
            
            # Create service context
            self._service_context = ServiceContext(
                config_manager=self._config_module,
                event_bus=self._event_bus,
                service_registry=self._service_registry,
                user_context=None
            )
            
            # Create ServiceManager with context and event bus
            self._service_manager = ServiceManager(
                context=self._service_context,
                event_bus=self._event_bus
            )
            
            # Integrate DependencyInjector with ServiceManager
            self._service_manager.set_dependency_injector(self._dependency_injector)
            
            # Register existing services with the new architecture
            self._register_legacy_services()
            
            # Initialize monitoring integration
            try:
                from .monitoring.monitoring_service import MonitoringService
                monitoring_service = MonitoringService(self._config_dir / "monitoring" if self._config_dir else None)
                self._monitoring_integration = CLIMonitoringIntegration(
                    monitoring_service=monitoring_service,
                    config_dir=self._config_dir
                )
                logger.info("CLI monitoring integration initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize monitoring integration: {e}")
                self._monitoring_integration = None
            
            logger.info("Integration architecture initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize integration architecture: {e}")
            raise ServiceInitializationError("CLIServiceManager", str(e), e)
    
    def _register_legacy_services(self) -> None:
        """
        Register existing legacy services with the new integration architecture.
        
        This method creates service wrappers for existing services to integrate
        them with the new ServiceManager and dependency injection system.
        """
        try:
            # Register ValidationService (no dependencies)
            if self._validation_service:
                wrapper = LegacyServiceWrapper(
                    self._validation_service,
                    "ValidationService",
                    ["validation", "schema_validation"]
                )
                self._dependency_injector.register_instance(ServiceInterface, wrapper)
            
            # Register ConfigurationService (depends on ValidationService)
            if self._config_service:
                wrapper = LegacyServiceWrapper(
                    self._config_service,
                    "ConfigurationService", 
                    ["configuration", "config_management"]
                )
                self._dependency_injector.register_instance(ServiceInterface, wrapper)
            
            # Register RepositoryFactory (depends on ValidationService)
            if self._repository_factory:
                wrapper = LegacyServiceWrapper(
                    self._repository_factory,
                    "RepositoryFactory",
                    ["repository_creation", "repository_management"]
                )
                self._dependency_injector.register_instance(ServiceInterface, wrapper)
            
            # Register BackupOrchestrator (depends on RepositoryFactory and ConfigurationService)
            if self._backup_orchestrator:
                wrapper = LegacyServiceWrapper(
                    self._backup_orchestrator,
                    "BackupOrchestrator",
                    ["backup", "orchestration"]
                )
                self._dependency_injector.register_instance(ServiceInterface, wrapper)
            
            logger.debug("Legacy services registered with integration architecture")
            
        except Exception as e:
            logger.warning(f"Failed to register some legacy services: {e}")
    
    def initialize_services(self) -> bool:
        """
        Initialize all services using the new integration architecture.
        
        This method initializes services through the ServiceManager with proper
        dependency resolution and error handling.
        
        Returns:
            bool: True if all services initialized successfully
            
        Raises:
            ServiceInitializationError: If service initialization fails
        """
        if self._is_initialized:
            return True
        
        try:
            if self._service_manager is None:
                raise ServiceInitializationError(
                    "CLIServiceManager",
                    "ServiceManager not initialized. Call _initialize_integration_architecture() first."
                )
            
            # Initialize services through ServiceManager
            success = self._service_manager.initialize_services_with_injector()
            
            if success:
                self._is_initialized = True
                logger.info("All CLI services initialized successfully")
                
                # Publish service initialization event
                if self._event_bus:
                    event = Event(
                        event_type="cli.services.initialized",
                        source="CLIServiceManager",
                        timestamp=datetime.now(),
                        data={
                            "config_dir": str(self._config_dir) if self._config_dir else None,
                            "service_count": len(self._service_manager.get_service_status())
                        }
                    )
                    self._event_bus.publish_event(event)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to initialize CLI services: {e}")
            raise ServiceInitializationError("CLIServiceManager", str(e), e)
    
    def shutdown_services(self) -> None:
        """
        Shutdown all services using the new integration architecture.
        
        This method performs clean shutdown of all services with proper
        cleanup and resource management.
        """
        try:
            if self._service_manager and self._is_initialized:
                # Publish shutdown event before shutting down
                if self._event_bus:
                    event = Event(
                        event_type="cli.services.shutting_down",
                        source="CLIServiceManager",
                        timestamp=datetime.now(),
                        data={"config_dir": str(self._config_dir) if self._config_dir else None}
                    )
                    self._event_bus.publish_event(event)
                
                # Shutdown services through ServiceManager
                self._service_manager.shutdown_services()
                self._is_initialized = False
                
                logger.info("All CLI services shut down successfully")
            
            # Clean up service context
            if self._service_context:
                self._service_context.cleanup()
                self._service_context = None
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
            # Don't raise exception during shutdown to avoid masking other errors
    
    def get_service_health(self) -> Dict[str, bool]:
        """
        Get health status of all services.
        
        Returns:
            Dict[str, bool]: Service name to health status mapping
        """
        if not self._service_manager or not self._is_initialized:
            return {"CLIServiceManager": False}
        
        try:
            return self._service_manager.health_check()
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"CLIServiceManager": False}
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive status information for all services.
        
        Returns:
            Dict[str, Dict[str, Any]]: Detailed service status information
        """
        if not self._service_manager:
            return {
                "CLIServiceManager": {
                    "initialized": self._is_initialized,
                    "error": "ServiceManager not available"
                }
            }
        
        try:
            status = self._service_manager.get_service_status()
            status["CLIServiceManager"] = {
                "initialized": self._is_initialized,
                "config_dir": str(self._config_dir) if self._config_dir else None,
                "integration_architecture": True
            }
            return status
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "CLIServiceManager": {
                    "initialized": self._is_initialized,
                    "error": str(e)
                }
            }
    
    def create_operation_context(self, operation_name: str, **kwargs) -> ServiceContext:
        """
        Create a new service context for a CLI operation.
        
        This method creates a child context from the base service context,
        supporting context inheritance and operation-specific configuration.
        
        Args:
            operation_name: Name of the operation being performed
            **kwargs: Additional context values
            
        Returns:
            ServiceContext: New operation context
            
        Raises:
            ServiceInitializationError: If base context is not available
        """
        if not self._service_context:
            raise ServiceInitializationError(
                "CLIServiceManager",
                "Base service context not available. Initialize services first."
            )
        
        # Create child context with operation-specific metadata
        operation_context = self._service_context.create_child_context(
            metadata={
                "operation_name": operation_name,
                "created_at": time.time(),
                **kwargs
            }
        )
        
        logger.debug(f"Created operation context for: {operation_name}")
        return operation_context
    
    def cleanup_operation_context(self, context: ServiceContext) -> None:
        """
        Clean up an operation context and its resources.
        
        Args:
            context: ServiceContext to clean up
        """
        try:
            context.cleanup()
            logger.debug("Operation context cleaned up successfully")
        except Exception as e:
            logger.warning(f"Error cleaning up operation context: {e}")
    
    def publish_cli_event(self, event_type: str, data: Dict[str, Any], 
                         correlation_id: Optional[str] = None) -> None:
        """
        Publish an event from CLI operations.
        
        Args:
            event_type: Type of event to publish
            data: Event data
            correlation_id: Optional correlation ID for event linking
        """
        if not self._event_bus:
            logger.warning("EventBus not available, cannot publish event")
            return
        
        try:
            event = Event(
                event_type=event_type,
                source="CLIServiceManager",
                timestamp=datetime.now(),
                data=data,
                correlation_id=correlation_id
            )
            self._event_bus.publish_event(event)
            logger.debug(f"Published CLI event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish CLI event {event_type}: {e}")
    
    def subscribe_to_events(self, event_type_pattern: str, 
                           handler: callable, subscriber_name: str = "CLI") -> str:
        """
        Subscribe to events from the event bus.
        
        Args:
            event_type_pattern: Pattern for event types to subscribe to
            handler: Function to handle matching events
            subscriber_name: Name of the subscriber
            
        Returns:
            str: Subscription ID for unsubscribing
        """
        if not self._event_bus:
            raise ServiceInitializationError(
                "CLIServiceManager",
                "EventBus not available for event subscription"
            )
        
        try:
            subscription_id = self._event_bus.subscribe_event(
                event_type_pattern=event_type_pattern,
                handler=handler,
                subscriber_name=subscriber_name
            )
            logger.debug(f"Subscribed to events: {event_type_pattern}")
            return subscription_id
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")
            raise

    @property
    def repository_factory(self) -> IRepositoryFactory:
        """Get repository factory instance"""
        return self._repository_factory

    @property
    def snapshot_service(self) -> SnapshotService:
        """Get snapshot service instance"""
        return self._snapshot_service

    @property
    def repository_service(self) -> RepositoryService:
        """Get repository service instance"""
        return self._repository_service

    @property
    def configuration_service(self) -> IConfigurationProvider:
        """Get configuration service instance"""
        return self._config_service

    @property
    def backup_orchestrator(self) -> IBackupOrchestrator:
        """Get backup orchestrator instance"""
        return self._backup_orchestrator

    @property
    def config_module(self) -> ConfigurationModule:
        """Get configuration module"""
        return self._config_module

    @property
    def config_dir(self) -> Optional[Path]:
        """Return configuration directory used by this manager."""
        return self._config_dir

    def resolve_repository_uri(self, repository_input: str) -> str:
        """
        Resolve repository input to URI.
        
        Args:
            repository_input: Repository name or URI
            
        Returns:
            Resolved repository URI
            
        Raises:
            ConfigurationError: If repository cannot be resolved
        """
        # Check if it's already a URI (contains scheme)
        if "://" in repository_input or repository_input.startswith("/"):
            return repository_input

        # Try to resolve as repository name from configuration
        try:
            if self._config_service is not None:
                repositories = self._config_service.get_repositories()
                for repo in repositories:
                    if repo['name'] == repository_input:
                        return repo['uri']

            # Fallback to configuration module
            repo_config = self._config_module.get_repository(repository_input)
            return repo_config.location

        except Exception:
            # If not found in configuration, treat as local path
            if not repository_input.startswith("file://"):
                return f"file://{repository_input}"
            return repository_input

    def _find_repository_name_by_uri(self, repository_uri: str) -> str:
        """
        Find repository name that matches the given URI.

        Args:
            repository_uri: Repository URI to find name for

        Returns:
            Repository name if found, otherwise the URI itself
        """
        try:
            # Try modern config service first
            if self._config_service is not None:
                repositories = self._config_service.get_repositories()
                for repo in repositories:
                    repo_uri = repo.get('uri')
                    if repo_uri == repository_uri:
                        return repo['name']

            # Fallback to configuration module
            config = self._config_module.get_config()
            logger.debug(f"Found {len(config.repositories)} repositories in config module")
            for repo_name, repo_config in config.repositories.items():
                repo_uri = getattr(repo_config, 'uri', None) or getattr(repo_config, 'location', None)
                logger.debug(f"Checking repo '{repo_name}' with URI '{repo_uri}'")
                if repo_uri == repository_uri:
                    logger.debug(f"Found matching repository name: {repo_name}")
                    return repo_name

        except Exception as e:
            logger.debug(f"Could not find repository name for URI {repository_uri}: {e}")

        # If no name found, return the URI itself as fallback
        logger.debug(f"No matching repository found, returning URI as fallback: {repository_uri}")
        return repository_uri

    @staticmethod
    def _looks_like_uri(candidate: str) -> bool:
        """Heuristically determine if candidate string represents a repository URI."""
        if not candidate:
            return False
        if "://" in candidate:
            return True
        prefixes = ("s3:", "b2:", "gs:", "azure:", "rest:", "rclone:", "local:", "minio:", "swift:", "/")
        return candidate.startswith(prefixes)

    def _create_repository_instance(self,
                                    name: Optional[str] = None,
                                    repository: Optional[str] = None,
                                    repository_uri: Optional[str] = None,
                                    password: Optional[str] = None) -> tuple:
        """
        Create repository instance for operations, resolving configuration as needed.

        Returns:
            Tuple of (repository_object, resolved_name, resolved_uri)
        """
        resolved_name = name
        resolved_uri = repository_uri

        candidate = repository
        if resolved_uri is None and candidate:
            if self._looks_like_uri(candidate):
                resolved_uri = candidate
            else:
                resolved_name = candidate

        if resolved_uri is None:
            if not resolved_name:
                raise ConfigurationError("Repository name or URI must be provided")
            repo_info = self.get_repository_by_name(resolved_name)
            if isinstance(repo_info, dict):
                resolved_uri = repo_info.get('uri') or repo_info.get('location')
                if password is None:
                    password = repo_info.get('password')
            else:
                resolved_uri = getattr(repo_info, 'uri', None) or getattr(repo_info, 'location', None)

        if not resolved_uri:
            raise ConfigurationError("Repository URI could not be resolved from configuration")

        if not resolved_name:
            resolved_name = self._find_repository_name_by_uri(resolved_uri)

        repository_instance = self._repository_factory.create_repository(
                resolved_uri,
                password=password,
                repository_name=resolved_name
        )
        return repository_instance, resolved_name, resolved_uri

    def initialize_repository(self,
                              name: str,
                              repository: Optional[str] = None,
                              repository_uri: Optional[str] = None,
                              repository_name: Optional[str] = None,
                              password: Optional[str] = None,
                              **_) -> Dict[str, Any]:
        """Initialize repository (idempotent) and persist password if provided."""
        repo, resolved_name, resolved_uri = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        already_initialized = False
        if hasattr(repo, "is_repository_initialized"):
            try:
                already_initialized = bool(repo.is_repository_initialized())
            except Exception:
                already_initialized = False

        if already_initialized:
            return {"success": True, "already_initialized": True, "uri": resolved_uri}

        try:
            if hasattr(repo, "initialize_repository"):
                success = bool(repo.initialize_repository(password))
            else:
                success = bool(repo.initialize())
        except Exception as exc:
            # Capture initialization errors
            error_msg = str(exc)
            logger.error(f"Repository initialization failed for {resolved_name}: {error_msg}")
            return {
                "success": False,
                "already_initialized": False,
                "uri": resolved_uri,
                "error": error_msg,
                "errors": [error_msg]
            }

        if success and password and hasattr(repo, "store_password"):
            try:
                repo.store_password(password)
            except Exception as exc:  # pragma: no cover - best effort storage
                logger.debug("Credential storage after init failed for %s: %s", resolved_name, exc)

        return {"success": success, "already_initialized": already_initialized, "uri": resolved_uri}

    def check_repository(self,
                         name: str,
                         repository: Optional[str] = None,
                         repository_uri: Optional[str] = None,
                         repository_name: Optional[str] = None,
                         password: Optional[str] = None,
                         **_) -> Dict[str, Any]:
        """Run repository integrity check."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.check_repository(repo)

    def get_repository_stats(self,
                             name: str,
                             repository: Optional[str] = None,
                             repository_uri: Optional[str] = None,
                             repository_name: Optional[str] = None,
                             password: Optional[str] = None,
                             **_) -> Dict[str, Any]:
        """Collect repository statistics."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.get_repository_stats(repo)

    def unlock_repository(self,
                          name: str,
                          repository: Optional[str] = None,
                          repository_uri: Optional[str] = None,
                          repository_name: Optional[str] = None,
                          password: Optional[str] = None,
                          **_) -> bool:
        """Remove repository locks."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.unlock_repository(repo)

    def migrate_repository(self,
                           name: str,
                           repository: Optional[str] = None,
                           repository_uri: Optional[str] = None,
                           repository_name: Optional[str] = None,
                           migration: Optional[str] = None,
                           password: Optional[str] = None,
                           **_) -> bool:
        """Execute repository migration."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        migration_name = migration or "upgrade_repo_v2"
        return self._repository_service.migrate_repository(repo, migration_name=migration_name)

    def apply_retention_policy(self,
                               name: str,
                               repository: Optional[str] = None,
                               repository_uri: Optional[str] = None,
                               repository_name: Optional[str] = None,
                               keep_daily: int = 7,
                               keep_weekly: int = 4,
                               keep_monthly: int = 12,
                               keep_yearly: int = 3,
                               dry_run: bool = False,
                               password: Optional[str] = None,
                               **_) -> Dict[str, Any]:
        """Apply forget/retention policy to repository."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.apply_retention_policy(
                repo,
                keep_daily=keep_daily,
                keep_weekly=keep_weekly,
                keep_monthly=keep_monthly,
                keep_yearly=keep_yearly,
                dry_run=dry_run
        )

    def prune_repository(self,
                         name: str,
                         repository: Optional[str] = None,
                         repository_uri: Optional[str] = None,
                         repository_name: Optional[str] = None,
                         password: Optional[str] = None,
                         **_) -> Dict[str, Any]:
        """Prune unreferenced data from repository."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.prune_repository(repo)

    def check_all_repositories(self, **_) -> Dict[str, Any]:
        """Run integrity checks for all configured repositories."""
        results: Dict[str, Any] = {}
        overall_success = True
        for repo in self.list_repositories() or []:
            repo_name = repo.get('name') if isinstance(repo, dict) else getattr(repo, 'name', None)
            repo_uri = repo.get('uri') if isinstance(repo, dict) else getattr(repo, 'uri', None)
            if not repo_name:
                repo_name = self._find_repository_name_by_uri(repo_uri or "")
            try:
                check_result = self.check_repository(repo_name, repository=repo_uri, repository_name=repo_name)
                results[repo_name] = check_result
                status = None
                if isinstance(check_result, dict):
                    status = check_result.get('status')
                elif hasattr(check_result, 'success'):
                    status = 'success' if getattr(check_result, 'success', False) else 'failed'
                if status not in (None, 'success', 'OK', True):
                    overall_success = False
            except Exception as exc:
                results[repo_name] = {'status': 'failed', 'errors': [str(exc)]}
                overall_success = False
        return {'success': overall_success, 'results': results}

    def get_all_repository_stats(self, **_) -> List[Dict[str, Any]]:
        """Collect statistics for all configured repositories."""
        stats: List[Dict[str, Any]] = []
        for repo in self.list_repositories() or []:
            repo_name = repo.get('name') if isinstance(repo, dict) else getattr(repo, 'name', None)
            repo_uri = repo.get('uri') if isinstance(repo, dict) else getattr(repo, 'uri', None)
            try:
                repo_stats = self.get_repository_stats(repo_name, repository=repo_uri, repository_name=repo_name)
                if isinstance(repo_stats, dict):
                    repo_stats = {**repo_stats, 'name': repo_name}
                stats.append(repo_stats)
            except Exception as exc:
                stats.append({'name': repo_name, 'error': str(exc)})
        return stats

    def execute_backup_from_cli(self, request: CLIBackupRequest) -> BackupResult:
        """
        Execute backup from CLI request using modern orchestrator.

        Args:
            request: CLI backup request

        Returns:
            BackupResult with operation details
        """
        logger = logging.getLogger(__name__)
        logger.debug(f"execute_backup_from_cli called with repository_uri: {request.repository_uri}")
        logger.debug(f"CLI service received password: {'***' if request.password else 'None'}")
        try:
            # Resolve repository URI
            repository_uri = self.resolve_repository_uri(request.repository_uri)
            logger.debug(f"Resolved repository URI: {repository_uri}")

            # Find repository name that matches this URI
            repository_name = self._find_repository_name_by_uri(repository_uri)
            logger.debug(f"Using repository name for backup: {repository_name}")

            # If using a configured target, get it from configuration
            logger.debug(f"Checking if target_name exists: {request.target_name}")
            if request.target_name:
                logger.debug(f"Target name found: {request.target_name}")
                target_names = [request.target_name]

                # Ensure target exists in configuration
                logger.debug("About to call get_backup_targets()")
                targets = self._config_service.get_backup_targets()
                logger.debug(f"get_backup_targets() returned {len(targets)} targets")

                logger.debug(f"Looking for target '{request.target_name}'")
                logger.debug(f"Available targets: {[t.get('name', 'NO_NAME') for t in targets]}")

                if not any(t['name'] == request.target_name for t in targets):
                    logger.debug(f"Target '{request.target_name}' not found, creating temporary target")
                    # Create temporary target configuration
                    target_config = {
                            'name':             request.target_name,
                            'paths':            [str(p) for p in request.sources],
                            'include_patterns': request.include_patterns,
                            'exclude_patterns': request.exclude_patterns
                    }
                    self._config_service.add_backup_target(target_config)
                else:
                    logger.debug(f"Target '{request.target_name}' found in configuration")

                logger.debug(f"About to call backup orchestrator with repository_name='{repository_name}', target_names={target_names}")

                return self._backup_orchestrator.execute_backup(
                        repository_name=repository_name,
                        target_names=target_names,
                        tags=request.tags,
                        dry_run=request.dry_run,
                        password=request.password
                )
            else:
                # Create ad-hoc backup target
                return self._execute_adhoc_backup(request, repository_uri, repository_name)

        except Exception as e:
            logger.debug(f"Exception caught in CLI service: {e}")
            logger.debug(f"Exception type: {type(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            logger.error(f"CLI backup execution failed: {e}")
            # Return failed result
            return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=request.repository_uri,
                    target_names=[request.target_name or "adhoc"],
                    errors=[str(e)]
            )

    def _execute_adhoc_backup(self, request: CLIBackupRequest, repository_uri: str, repository_name: str) -> BackupResult:
        """Execute backup for ad-hoc sources without configured targets"""
        # Create temporary target name
        target_name = request.backup_name or f"cli_backup_{int(time.time())}"

        # Create temporary target configuration
        target_config = {
                'name':             target_name,
                'paths':            [str(p) for p in request.sources],
                'include_patterns': request.include_patterns,
                'exclude_patterns': request.exclude_patterns
        }

        # Add to configuration temporarily
        self._config_service.add_backup_target(target_config)

        try:
            # Execute backup
            return self._backup_orchestrator.execute_backup(
                    repository_name=repository_name,
                    target_names=[target_name],
                    tags=request.tags,
                    dry_run=request.dry_run,
                    password=request.password
            )
        finally:
            # Clean up temporary target
            self._config_service.remove_backup_target(target_name)

    def verify_backup_integrity(self,
                                repository_input: str,
                                snapshot_id: Optional[str] = None) -> bool:
        """
        Verify backup integrity using modern orchestrator.

        Args:
            repository_input: Repository name or URI
            snapshot_id: Optional specific snapshot to verify

        Returns:
            True if verification successful
        """
        try:
            repository_uri = self.resolve_repository_uri(repository_input)
            return self._backup_orchestrator.verify_backup_integrity(
                    repository_name=repository_uri,
                    snapshot_id=snapshot_id
            )
        except Exception as e:
            logger.debug(f"Backup verification failed: {e}")  # Use debug instead of error to avoid duplicate error panels
            return False

    def list_repositories(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all configured repositories with optional filtering.

        Args:
            filters: Optional dictionary of filters to apply
                    - status: Filter by status (active, inactive, error)
                    - engine: Filter by engine (restic, rsync, rclone)

        Returns:
            List of repository configurations
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                repos = self._config_service.get_repositories()
            except Exception:
                # Fallback to configuration module
                repos = self._config_module.get_repositories()
        else:
            # Use configuration module
            repos = self._config_module.get_repositories()
        
        # Apply filters if provided
        if filters:
            if 'status' in filters:
                status_filter = filters['status'].lower()
                repos = [r for r in repos if r.get('status', '').lower() == status_filter]
            
            if 'engine' in filters:
                engine_filter = filters['engine'].lower()
                repos = [r for r in repos if r.get('engine', '').lower() == engine_filter]
        
        return repos

    def get_repository_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific repository configuration by name.

        Args:
            name: Repository name

        Returns:
            Repository configuration dictionary

        Raises:
            ConfigurationError: If repository is not found
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_repository_by_name(name)
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        try:
            repo_config = self._config_module.get_repository(name)
            # Convert to dictionary format
            if hasattr(repo_config, '__dict__'):
                return {**repo_config.__dict__, 'name': name}
            else:
                return {'name': name, **repo_config}
        except Exception as e:
            raise ConfigurationError(f"Repository '{name}' not found: {e}")

    def list_backup_targets(self) -> List[Dict[str, Any]]:
        """
        List all configured backup targets.

        Returns:
            List of backup target configurations
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_backup_targets()
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        targets = self._config_module.get_backup_targets()
        return targets

    def get_backup_target_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific backup target configuration by name.

        Args:
            name: Backup target name

        Returns:
            Backup target configuration dictionary

        Raises:
            ConfigurationError: If backup target is not found
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_backup_target_by_name(name)
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        try:
            target_config = self._config_module.get_backup_target(name)
            # Convert to dictionary format
            if hasattr(target_config, '__dict__'):
                return {**target_config.__dict__, 'name': name}
            else:
                return {'name': name, **target_config}
        except Exception as e:
            raise ConfigurationError(f"Backup target '{name}' not found: {e}")

    def add_repository(self, name: str, uri: str, description: str = "", password: Optional[str] = None) -> None:
        """
        Add a new repository configuration.
        
        Args:
            name: Repository name
            uri: Repository URI
            description: Optional description
        """
        repo_config = {
                'name':        name,
                'uri':         uri,
                'description': description,
                'type':        'auto'  # Auto-detect type from URI
        }
        if password:
            repo_config['password'] = password

        if self._config_service is not None:
            try:
                # Try modern configuration service first
                self._config_service.add_repository(repo_config)
                return
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        self._config_module.add_repository({
                "name":        name,
                "location":    uri,
                "description": description
        })

    def set_repository_password(self,
                                repository: str,
                                password: str,
                                master_password: Optional[str] = None) -> Dict[str, Any]:
        """
        Persist repository password into the credential manager.

        Args:
            repository: Repository name or URI.
            password: Repository password to store.
            master_password: Optional master password for unlocking credentials.

        Returns:
            Dictionary describing operation outcome.
        """
        if not password:
            raise ConfigurationError("Repository password cannot be empty")

        credential_manager = self._repository_factory.get_credential_manager()
        if credential_manager is None:
            raise ConfigurationError("Credential manager is not available")

        # Ensure credential store is unlocked for non-interactive flows.
        if credential_manager.is_locked():
            unlock_error: Optional[Exception] = None
            try:
                if not credential_manager.ensure_unlocked(allow_prompt=False):
                    unlock_error = CredentialManagerError("Credential manager remains locked")
            except Exception as exc:  # pragma: no cover - defensive
                unlock_error = exc

            if unlock_error:
                if master_password:
                    if not credential_manager.unlock(master_password):
                        raise ConfigurationError("Failed to unlock credential manager with provided master password")
                else:
                    raise ConfigurationError(f"Credential manager locked: {unlock_error}")

        repo_instance, resolved_name, resolved_uri = self._create_repository_instance(
                name=repository,
                repository=repository,
                password=password
        )

        if not hasattr(repo_instance, "store_password"):
            raise ConfigurationError("Repository backend does not support password storage")

        try:
            store_result = repo_instance.store_password(password)
        except CredentialManagerError as exc:
            raise ConfigurationError(f"Failed to store repository password: {exc}") from exc

        if store_result is False:
            raise ConfigurationError("Credential manager declined storing the repository password")

        # Remove plaintext password from configuration to avoid duplication.
        try:
            repo_config = self._config_module.get_repository(resolved_name)
            if hasattr(repo_config, "password"):
                repo_config.password = None
                self._config_module.update_repository(resolved_name, repo_config)
        except Exception:
            logger.debug("Failed to clear plaintext password from configuration for '%s'", resolved_name)

        return {
                "success":    True,
                "repository": resolved_name,
                "uri":        resolved_uri
        }

    def add_backup_target(self,
                          name: str,
                          paths: List[str],
                          include_patterns: List[str] = None,
                          exclude_patterns: List[str] = None) -> None:
        """
        Add a new backup target configuration.
        
        Args:
            name: Target name
            paths: List of paths to backup
            include_patterns: Optional include patterns
            exclude_patterns: Optional exclude patterns
        """
        target_config = {
                'name':             name,
                'paths':            paths,
                'include_patterns': include_patterns or [],
                'exclude_patterns': exclude_patterns or []
        }

        if self._config_service is not None:
            try:
                # Try modern configuration service first
                self._config_service.add_backup_target(target_config)
                return
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        self._config_module.add_backup_target(
                name=name,
                paths=paths,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns
        )

    def get_backup_history(self,
                           repository_name: Optional[str] = None,
                           limit: int = 100) -> List[BackupResult]:
        """
        Get backup operation history.
        
        Args:
            repository_name: Optional repository name to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of BackupResult objects from history
        """
        return self._backup_orchestrator.get_backup_history(repository_name, limit)

    def estimate_backup_size(self,
                             repository_input: str,
                             target_names: List[str]) -> Dict[str, Any]:
        """
        Estimate backup size and duration.
        
        Args:
            repository_input: Repository name or URI
            target_names: Names of backup targets
            
        Returns:
            Dictionary with size and time estimates
        """
        repository_uri = self.resolve_repository_uri(repository_input)
        return self._backup_orchestrator.estimate_backup_size(repository_uri, target_names)

    def get_repository_service(self) -> RepositoryService:
        """Backward-compatible accessor used by CLI commands expecting a method."""
        return self._repository_service
    
    def remove_repository(self, name: str, **kwargs) -> None:
        """
        Remove a repository configuration.
        
        This method provides backward compatibility for CLI commands that expect
        a remove_repository method on the service manager.
        
        Args:
            name: Repository name to remove
            **kwargs: Additional parameters (for compatibility)
        """
        try:
            # Use the configuration module to remove the repository
            self._config_module.remove_repository(name)
            
            # Publish event about repository removal
            if self._event_bus:
                self.publish_cli_event(
                    "repository.removed",
                    {"repository_name": name},
                    correlation_id=f"repo-remove-{name}"
                )
            
            logger.info(f"Repository '{name}' removed successfully via CLI service manager")
            
        except Exception as e:
            logger.error(f"Failed to remove repository '{name}': {e}")
            raise
    
    # Monitoring Integration Methods (Requirements 8.1, 8.2, 8.3)
    
    def get_monitoring_integration(self) -> Optional[CLIMonitoringIntegration]:
        """
        Get the CLI monitoring integration instance.
        
        Returns:
            CLIMonitoringIntegration instance or None if not available
            
        Requirements: 8.1
        """
        return self._monitoring_integration
    
    def get_system_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current system monitoring status for CLI display.
        
        Returns:
            Dict containing system monitoring status
            
        Requirements: 8.1, 8.3
        """
        if not self._monitoring_integration:
            return {
                'error': 'Monitoring integration not available',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            return self._monitoring_integration.get_system_status()
        except Exception as e:
            logger.error(f"Failed to get system monitoring status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_cli_monitoring_logs(self, hours: Optional[int] = None, days: Optional[int] = None,
                                repository_id: Optional[str] = None, log_level: Optional[str] = None,
                                limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get monitoring logs for CLI display with filtering.
        
        Args:
            hours: Number of hours to look back
            days: Number of days to look back
            repository_id: Optional filter by repository
            log_level: Optional filter by log level
            limit: Optional limit on number of results
            
        Returns:
            List of log entry dictionaries
            
        Requirements: 8.1, 8.2
        """
        if not self._monitoring_integration:
            logger.warning("Monitoring integration not available")
            return []
        
        try:
            from .cli_modules.monitoring_integration import CLIMonitoringFilters
            
            filters = CLIMonitoringFilters(
                hours=hours,
                days=days,
                repository_id=repository_id,
                log_level=log_level,
                limit=limit
            )
            
            return self._monitoring_integration.get_recent_logs(filters)
        except Exception as e:
            logger.error(f"Failed to get monitoring logs: {e}")
            return []
    
    def search_monitoring_logs(self, query: str, hours: Optional[int] = None, days: Optional[int] = None,
                               repository_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search monitoring logs for specific text.
        
        Args:
            query: Search query string
            hours: Number of hours to look back
            days: Number of days to look back
            repository_id: Optional filter by repository
            limit: Optional limit on number of results
            
        Returns:
            List of matching log entry dictionaries
            
        Requirements: 8.2
        """
        if not self._monitoring_integration:
            logger.warning("Monitoring integration not available")
            return []
        
        try:
            from .cli_modules.monitoring_integration import CLIMonitoringFilters
            
            filters = CLIMonitoringFilters(
                hours=hours,
                days=days,
                repository_id=repository_id,
                limit=limit
            )
            
            return self._monitoring_integration.search_logs(query, filters)
        except Exception as e:
            logger.error(f"Failed to search monitoring logs: {e}")
            return []
    
    def get_cli_backup_history(self, days: Optional[int] = None, repository_id: Optional[str] = None,
                                status: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get backup history for CLI display with filtering.
        
        Args:
            days: Number of days to look back
            repository_id: Optional filter by repository
            status: Optional filter by status
            limit: Optional limit on number of results
            
        Returns:
            List of backup record dictionaries
            
        Requirements: 8.1
        """
        if not self._monitoring_integration:
            logger.warning("Monitoring integration not available")
            return []
        
        try:
            from .cli_modules.monitoring_integration import CLIMonitoringFilters
            
            filters = CLIMonitoringFilters(
                days=days,
                repository_id=repository_id,
                status=status,
                limit=limit
            )
            
            return self._monitoring_integration.get_backup_history(filters)
        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []
    
    def get_cli_current_operations(self) -> List[Dict[str, Any]]:
        """
        Get currently running operations for CLI display.
        
        Returns:
            List of current operation dictionaries
            
        Requirements: 8.1, 8.3
        """
        if not self._monitoring_integration:
            logger.warning("Monitoring integration not available")
            return []
        
        try:
            return self._monitoring_integration.get_current_operations()
        except Exception as e:
            logger.error(f"Failed to get current operations: {e}")
            return []
    
    def get_cli_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific operation for CLI display.
        
        Args:
            operation_id: Operation ID to query
            
        Returns:
            Operation status dictionary or None if not found
            
        Requirements: 8.1, 8.3
        """
        if not self._monitoring_integration:
            logger.warning("Monitoring integration not available")
            return None
        
        try:
            return self._monitoring_integration.get_operation_status(operation_id)
        except Exception as e:
            logger.error(f"Failed to get operation status: {e}")
            return None


# Global CLI service manager instance
_cli_service_manager: Optional[CLIServiceManager] = None


def get_cli_service_manager(config_dir: Optional[Path] = None) -> CLIServiceManager:
    """
    Get global CLI service manager instance (singleton pattern).
    
    This function ensures that the CLI service manager is properly initialized
    with the integration architecture and returns the same instance for
    consistent service access across the application.
    
    Args:
        config_dir: Optional configuration directory path
        
    Returns:
        CLIServiceManager: Enhanced CLI service manager instance
    """
    global _cli_service_manager
    if _cli_service_manager is None:
        _cli_service_manager = CLIServiceManager(config_dir=config_dir)
        # Initialize services on first access
        try:
            _cli_service_manager.initialize_services()
        except Exception as e:
            logger.warning(f"Failed to initialize services on first access: {e}")
    else:
        if config_dir is not None:
            desired_dir = Path(config_dir)
            current_dir = _cli_service_manager.config_dir
            if current_dir is None or Path(current_dir) != desired_dir:
                # Shutdown existing manager before creating new one
                try:
                    _cli_service_manager.shutdown_services()
                except Exception as e:
                    logger.warning(f"Error shutting down previous service manager: {e}")
                
                _cli_service_manager = CLIServiceManager(config_dir=desired_dir)
                # Initialize services for new manager
                try:
                    _cli_service_manager.initialize_services()
                except Exception as e:
                    logger.warning(f"Failed to initialize services for new config dir: {e}")
    
    return _cli_service_manager


def reset_cli_service_manager() -> None:
    """
    Reset global CLI service manager (used after configuration changes).
    
    This function properly shuts down the existing service manager and
    clears the global reference, ensuring clean state for the next access.
    """
    global _cli_service_manager
    if _cli_service_manager is not None:
        try:
            _cli_service_manager.shutdown_services()
        except Exception as e:
            logger.warning(f"Error shutting down service manager during reset: {e}")
    
    _cli_service_manager = None
