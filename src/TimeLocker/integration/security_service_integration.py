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
Security Service Integration for TimeLocker Service Architecture

This module provides a service wrapper that integrates the SecurityService
with the TimeLocker service architecture, enabling security features to be
managed through the ServiceManager.
"""

import logging
from typing import List, Optional, Dict, Any

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext
from ..security.security_service import SecurityService
from .security_integration import ServiceSecurityManager

logger = logging.getLogger(__name__)


class SecurityServiceIntegration(ServiceInterface):
    """
    Integration wrapper for SecurityService in the service architecture.
    
    This class wraps the SecurityService to make it compatible with the
    ServiceInterface and enables it to be managed by the ServiceManager
    with full security integration capabilities.
    
    Requirements addressed:
    - 8.1: Secure inter-service communication
    - 8.2: Service authentication and authorization
    - 8.3: Audit logging for service interactions
    - 8.4: Service isolation preventing unauthorized access
    """
    
    def __init__(self, security_service: SecurityService):
        """
        Initialize security service integration.
        
        Args:
            security_service: SecurityService instance to wrap
        """
        self.security_service = security_service
        self._context: Optional[ServiceContext] = None
        self._initialized = False
        
        logger.info("SecurityServiceIntegration created")
    
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the security service integration.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to SecurityServiceIntegration")
                return False
            
            self._context = context
            
            # Initialize the underlying security service if not already initialized
            if hasattr(self.security_service, '_initialized') and not self.security_service._initialized:
                success = self.security_service.initialize(context)
                if not success:
                    logger.error("Failed to initialize underlying SecurityService")
                    return False
            
            self._initialized = True
            logger.info("SecurityServiceIntegration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SecurityServiceIntegration: {e}")
            return False
    
    def shutdown(self) -> None:
        """
        Shutdown the security service integration.
        """
        try:
            if self.security_service and hasattr(self.security_service, 'shutdown'):
                self.security_service.shutdown()
            
            self._context = None
            self._initialized = False
            logger.info("SecurityServiceIntegration shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during SecurityServiceIntegration shutdown: {e}")
    
    def health_check(self) -> bool:
        """
        Check the health status of the security service integration.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        try:
            if not self._initialized:
                return False
            
            if not self.security_service:
                return False
            
            # Check underlying security service health
            if hasattr(self.security_service, 'health_check'):
                return self.security_service.health_check()
            
            return True
            
        except Exception as e:
            logger.error(f"SecurityServiceIntegration health check failed: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        base_capabilities = [
            'service_authentication',
            'service_authorization', 
            'service_audit_logging',
            'service_isolation',
            'secure_communication',
            'credential_management',
            'security_monitoring'
        ]
        
        # Add capabilities from underlying security service
        if self.security_service and hasattr(self.security_service, 'get_capabilities'):
            try:
                security_capabilities = self.security_service.get_capabilities()
                base_capabilities.extend(security_capabilities)
            except Exception as e:
                logger.warning(f"Failed to get SecurityService capabilities: {e}")
        
        return base_capabilities
    
    def get_service_name(self) -> str:
        """
        Get the name of this service.
        
        Returns:
            str: Service name identifier
        """
        return "SecurityServiceIntegration"
    
    def get_service_version(self) -> str:
        """
        Get the version of this service.
        
        Returns:
            str: Service version string
        """
        return "1.0.0"
    
    # Security Service Integration Methods
    
    def create_security_manager(self, event_bus=None) -> ServiceSecurityManager:
        """
        Create a ServiceSecurityManager instance.
        
        Args:
            event_bus: EventBus for publishing security events
            
        Returns:
            ServiceSecurityManager instance
        """
        return ServiceSecurityManager(
            security_service=self.security_service,
            event_bus=event_bus
        )
    
    def audit_service_interaction(self, 
                                source_service: str,
                                target_service: str,
                                operation: str,
                                success: bool,
                                duration_ms: float,
                                sensitive_data: bool = False,
                                error_message: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Audit a service interaction through the security service.
        
        Args:
            source_service: Name of the source service
            target_service: Name of the target service
            operation: Operation being performed
            success: Whether the operation was successful
            duration_ms: Duration of the operation in milliseconds
            sensitive_data: Whether the operation involved sensitive data
            error_message: Error message if operation failed
            metadata: Additional metadata for the audit record
        """
        try:
            # Use the security service's audit logging capabilities
            if hasattr(self.security_service, 'log_security_event'):
                from ..security.security_service import SecurityEvent, SecurityLevel
                from datetime import datetime
                
                event = SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="service_interaction",
                    level=SecurityLevel.HIGH if sensitive_data else SecurityLevel.MEDIUM,
                    description=f"Service interaction: {source_service} -> {target_service}.{operation}",
                    metadata={
                        "source_service": source_service,
                        "target_service": target_service,
                        "operation": operation,
                        "success": success,
                        "duration_ms": duration_ms,
                        "sensitive_data": sensitive_data,
                        "error_message": error_message,
                        **(metadata or {})
                    }
                )
                
                self.security_service.log_security_event(event)
            
        except Exception as e:
            logger.error(f"Failed to audit service interaction: {e}")
    
    def verify_service_credentials(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """
        Verify service credentials.
        
        Args:
            service_name: Name of the service
            credentials: Credentials to verify
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Use the security service's credential verification if available
            if hasattr(self.security_service, 'credential_manager'):
                # This would integrate with the credential manager
                # For now, we'll do basic validation
                return credentials is not None and len(credentials) > 0
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify service credentials for {service_name}: {e}")
            return False
    
    def log_security_violation(self, 
                             violation_type: str,
                             source_service: str,
                             target_service: str,
                             details: str,
                             metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a security violation.
        
        Args:
            violation_type: Type of security violation
            source_service: Source service involved in violation
            target_service: Target service involved in violation
            details: Details about the violation
            metadata: Additional metadata
        """
        try:
            if hasattr(self.security_service, 'log_security_event'):
                from ..security.security_service import SecurityEvent, SecurityLevel
                from datetime import datetime
                
                event = SecurityEvent(
                    timestamp=datetime.now(),
                    event_type="security_violation",
                    level=SecurityLevel.CRITICAL,
                    description=f"Security violation ({violation_type}): {details}",
                    metadata={
                        "violation_type": violation_type,
                        "source_service": source_service,
                        "target_service": target_service,
                        "details": details,
                        **(metadata or {})
                    }
                )
                
                self.security_service.log_security_event(event)
            
        except Exception as e:
            logger.error(f"Failed to log security violation: {e}")
    
    def get_security_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get security summary from the underlying security service.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary with security summary information
        """
        try:
            if hasattr(self.security_service, 'get_security_summary'):
                return self.security_service.get_security_summary(days)
            
            return {"message": "Security summary not available"}
            
        except Exception as e:
            logger.error(f"Failed to get security summary: {e}")
            return {"error": str(e)}
    
    def emergency_lockdown(self, reason: str, triggered_by: str = "ServiceManager") -> bool:
        """
        Initiate emergency lockdown through the security service.
        
        Args:
            reason: Reason for the lockdown
            triggered_by: Who or what triggered the lockdown
            
        Returns:
            bool: True if lockdown was successful
        """
        try:
            if hasattr(self.security_service, 'emergency_lockdown'):
                return self.security_service.emergency_lockdown(
                    reason=reason,
                    triggered_by=triggered_by,
                    metadata={"source": "ServiceManager"}
                )
            
            logger.warning("Emergency lockdown not available in SecurityService")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initiate emergency lockdown: {e}")
            return False
    
    # Delegate methods to underlying SecurityService
    
    def __getattr__(self, name):
        """
        Delegate unknown method calls to the underlying SecurityService.
        
        This allows the integration to act as a transparent proxy for
        SecurityService methods while adding service architecture integration.
        """
        if hasattr(self.security_service, name):
            return getattr(self.security_service, name)
        
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")