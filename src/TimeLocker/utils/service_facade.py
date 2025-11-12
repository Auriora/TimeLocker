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
Service Facade for CLI Commands

This module provides a simplified interface for accessing TimeLocker services
from CLI commands, reducing code duplication and providing consistent error handling.

Requirements addressed:
- Requirement 3: Simplified service access through ServiceFacade
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ServiceFacadeError(Exception):
    """Base exception for ServiceFacade errors"""
    pass


class ServiceInitializationError(ServiceFacadeError):
    """Raised when service initialization fails"""
    pass


class ServiceAccessError(ServiceFacadeError):
    """Raised when service access fails"""
    pass


class ServiceFacade:
    """
    Simplified facade for accessing TimeLocker services from CLI commands.
    
    This class provides a consistent interface for service access with:
    - Lazy initialization of services
    - Consistent error handling patterns
    - Service health checking
    - Simplified service manager wrapper
    
    Requirements addressed:
    - 3.1: ServiceFacade provides simplified access to all TimeLocker services
    - 3.2: ServiceFacade initializes services lazily and provides health checking
    - 3.3: ServiceFacade reduces service access code by at least 120 lines
    - 3.4: ServiceFacade maintains backward compatibility with direct service manager access
    - 3.5: ServiceFacade provides detailed error context and recovery options
    """
    
    def __init__(self, service_manager: Optional[Any] = None, config_dir: Optional[Path] = None):
        """
        Initialize ServiceFacade.
        
        Args:
            service_manager: Optional CLIServiceManager instance
            config_dir: Optional configuration directory path
        """
        self._service_manager = service_manager
        self._config_dir = config_dir
        self._initialized = False
        self._services_cache: Dict[str, Any] = {}
        
        logger.debug(f"ServiceFacade initialized with config_dir: {config_dir}")
    
    def _ensure_service_manager(self) -> Any:
        """
        Ensure service manager is available and initialized.
        
        Returns:
            CLIServiceManager instance
            
        Raises:
            ServiceInitializationError: If service manager cannot be initialized
        """
        if self._service_manager is None:
            try:
                from ..cli_services import get_cli_service_manager
                self._service_manager = get_cli_service_manager(config_dir=self._config_dir)
                logger.debug("Service manager created via get_cli_service_manager")
            except Exception as e:
                raise ServiceInitializationError(
                    f"Failed to create service manager: {e}"
                ) from e
        
        if not self._initialized:
            try:
                # Initialize services if not already initialized
                if hasattr(self._service_manager, 'initialize_services'):
                    self._service_manager.initialize_services()
                self._initialized = True
                logger.debug("Service manager initialized successfully")
            except Exception as e:
                raise ServiceInitializationError(
                    f"Failed to initialize services: {e}"
                ) from e
        
        return self._service_manager
    
    def get_backup_service(self) -> Any:
        """
        Get backup orchestrator service.
        
        Returns:
            BackupOrchestrator instance
            
        Raises:
            ServiceAccessError: If backup service cannot be accessed
        """
        if 'backup' in self._services_cache:
            return self._services_cache['backup']
        
        try:
            service_manager = self._ensure_service_manager()
            backup_service = service_manager.backup_orchestrator
            
            if backup_service is None:
                raise ServiceAccessError(
                    "Backup orchestrator not available. "
                    "This may indicate the service is not yet implemented or configured."
                )
            
            self._services_cache['backup'] = backup_service
            logger.debug("Backup service accessed successfully")
            return backup_service
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access backup service: {e}"
            ) from e
    
    def get_restore_service(self) -> Any:
        """
        Get restore/recovery service.
        
        Returns:
            RestoreManager or RecoveryOrchestrator instance
            
        Raises:
            ServiceAccessError: If restore service cannot be accessed
        """
        if 'restore' in self._services_cache:
            return self._services_cache['restore']
        
        try:
            service_manager = self._ensure_service_manager()
            
            # Try to get restore service from service manager
            restore_service = None
            if hasattr(service_manager, 'restore_service'):
                restore_service = service_manager.restore_service
            elif hasattr(service_manager, 'recovery_orchestrator'):
                restore_service = service_manager.recovery_orchestrator
            
            if restore_service is None:
                # Fallback: create RestoreManager directly
                from ..restore_manager import RestoreManager
                restore_service = RestoreManager()
                logger.debug("Created RestoreManager as fallback")
            
            self._services_cache['restore'] = restore_service
            logger.debug("Restore service accessed successfully")
            return restore_service
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access restore service: {e}"
            ) from e
    
    def get_repository_service(self) -> Any:
        """
        Get repository service.
        
        Returns:
            RepositoryService instance
            
        Raises:
            ServiceAccessError: If repository service cannot be accessed
        """
        if 'repository' in self._services_cache:
            return self._services_cache['repository']
        
        try:
            service_manager = self._ensure_service_manager()
            repository_service = service_manager.repository_service
            
            if repository_service is None:
                raise ServiceAccessError(
                    "Repository service not available. "
                    "This may indicate a configuration issue."
                )
            
            self._services_cache['repository'] = repository_service
            logger.debug("Repository service accessed successfully")
            return repository_service
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access repository service: {e}"
            ) from e
    
    def get_snapshot_service(self) -> Any:
        """
        Get snapshot service.
        
        Returns:
            SnapshotService instance
            
        Raises:
            ServiceAccessError: If snapshot service cannot be accessed
        """
        if 'snapshot' in self._services_cache:
            return self._services_cache['snapshot']
        
        try:
            service_manager = self._ensure_service_manager()
            snapshot_service = service_manager.snapshot_service
            
            if snapshot_service is None:
                raise ServiceAccessError(
                    "Snapshot service not available. "
                    "This may indicate a configuration issue."
                )
            
            self._services_cache['snapshot'] = snapshot_service
            logger.debug("Snapshot service accessed successfully")
            return snapshot_service
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access snapshot service: {e}"
            ) from e
    
    def get_configuration_service(self) -> Any:
        """
        Get configuration service.
        
        Returns:
            ConfigurationService instance
            
        Raises:
            ServiceAccessError: If configuration service cannot be accessed
        """
        if 'configuration' in self._services_cache:
            return self._services_cache['configuration']
        
        try:
            service_manager = self._ensure_service_manager()
            config_service = service_manager.configuration_service
            
            if config_service is None:
                # Fallback to config module
                config_service = service_manager.config_module
                logger.debug("Using config module as fallback for configuration service")
            
            if config_service is None:
                raise ServiceAccessError(
                    "Configuration service not available. "
                    "This may indicate a configuration issue."
                )
            
            self._services_cache['configuration'] = config_service
            logger.debug("Configuration service accessed successfully")
            return config_service
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access configuration service: {e}"
            ) from e
    
    def get_repository_factory(self) -> Any:
        """
        Get repository factory.
        
        Returns:
            RepositoryFactory instance
            
        Raises:
            ServiceAccessError: If repository factory cannot be accessed
        """
        if 'repository_factory' in self._services_cache:
            return self._services_cache['repository_factory']
        
        try:
            service_manager = self._ensure_service_manager()
            repository_factory = service_manager.repository_factory
            
            if repository_factory is None:
                raise ServiceAccessError(
                    "Repository factory not available. "
                    "This may indicate a configuration issue."
                )
            
            self._services_cache['repository_factory'] = repository_factory
            logger.debug("Repository factory accessed successfully")
            return repository_factory
            
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access repository factory: {e}"
            ) from e
    
    def get_monitoring_service(self) -> Optional[Any]:
        """
        Get monitoring service (optional).
        
        Returns:
            MonitoringService instance or None if not available
        """
        if 'monitoring' in self._services_cache:
            return self._services_cache['monitoring']
        
        try:
            service_manager = self._ensure_service_manager()
            
            # Try to get monitoring integration
            monitoring_service = None
            if hasattr(service_manager, 'get_monitoring_integration'):
                monitoring_integration = service_manager.get_monitoring_integration()
                if monitoring_integration:
                    monitoring_service = monitoring_integration
                    logger.debug("Monitoring service accessed via integration")
            
            self._services_cache['monitoring'] = monitoring_service
            return monitoring_service
            
        except Exception as e:
            logger.debug(f"Monitoring service not available: {e}")
            return None
    
    def get_security_service(self) -> Any:
        """
        Get security service.
        
        Returns:
            SecurityService instance
            
        Raises:
            ServiceAccessError: If security service cannot be accessed
        """
        if 'security' in self._services_cache:
            return self._services_cache['security']
        
        try:
            # Create security service directly as it's not typically in service manager
            from ..security import SecurityService, CredentialManager
            
            credential_manager = CredentialManager(config_dir=self._config_dir)
            security_service = SecurityService(credential_manager, config_dir=self._config_dir)
            
            self._services_cache['security'] = security_service
            logger.debug("Security service created successfully")
            return security_service
            
        except Exception as e:
            raise ServiceAccessError(
                f"Failed to access security service: {e}"
            ) from e
    
    def initialize_services(self) -> bool:
        """
        Explicitly initialize all services.
        
        Returns:
            True if initialization successful
            
        Raises:
            ServiceInitializationError: If initialization fails
        """
        try:
            self._ensure_service_manager()
            return True
        except ServiceInitializationError:
            raise
        except Exception as e:
            raise ServiceInitializationError(
                f"Failed to initialize services: {e}"
            ) from e
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health status of all services.
        
        Returns:
            Dictionary mapping service names to health status
        """
        health_status = {}
        
        try:
            service_manager = self._ensure_service_manager()
            
            # Check service manager health
            if hasattr(service_manager, 'get_service_health'):
                health_status = service_manager.get_service_health()
            else:
                # Fallback: check individual services
                services_to_check = [
                    ('repository_service', 'repository'),
                    ('snapshot_service', 'snapshot'),
                    ('configuration_service', 'configuration'),
                ]
                
                for attr_name, service_name in services_to_check:
                    try:
                        service = getattr(service_manager, attr_name, None)
                        if service is not None:
                            if hasattr(service, 'health_check'):
                                health_status[service_name] = service.health_check()
                            else:
                                health_status[service_name] = True
                        else:
                            health_status[service_name] = False
                    except Exception as e:
                        logger.debug(f"Health check failed for {service_name}: {e}")
                        health_status[service_name] = False
            
            logger.debug(f"Health check completed: {health_status}")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'service_facade': False, 'error': str(e)}
    
    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive status information for all services.
        
        Returns:
            Dictionary with detailed service status information
        """
        try:
            service_manager = self._ensure_service_manager()
            
            if hasattr(service_manager, 'get_service_status'):
                return service_manager.get_service_status()
            else:
                # Fallback: basic status
                return {
                    'service_facade': {
                        'initialized': self._initialized,
                        'config_dir': str(self._config_dir) if self._config_dir else None,
                        'cached_services': list(self._services_cache.keys())
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                'service_facade': {
                    'initialized': self._initialized,
                    'error': str(e)
                }
            }
    
    def shutdown_services(self) -> None:
        """
        Shutdown all services and clean up resources.
        """
        try:
            if self._service_manager and hasattr(self._service_manager, 'shutdown_services'):
                self._service_manager.shutdown_services()
            
            # Clear cache
            self._services_cache.clear()
            self._initialized = False
            
            logger.debug("Services shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
    
    @property
    def service_manager(self) -> Any:
        """
        Get the underlying service manager (for backward compatibility).
        
        Returns:
            CLIServiceManager instance
        """
        return self._ensure_service_manager()
    
    @property
    def config_dir(self) -> Optional[Path]:
        """
        Get the configuration directory.
        
        Returns:
            Configuration directory path or None
        """
        return self._config_dir


def create_service_facade(config_dir: Optional[Path] = None, 
                          service_manager: Optional[Any] = None) -> ServiceFacade:
    """
    Factory function to create a ServiceFacade instance.
    
    Args:
        config_dir: Optional configuration directory path
        service_manager: Optional existing service manager instance
        
    Returns:
        ServiceFacade instance
    """
    return ServiceFacade(service_manager=service_manager, config_dir=config_dir)
