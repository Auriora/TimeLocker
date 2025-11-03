#!/usr/bin/env python3
"""
Security Integration Demo for TimeLocker Service Architecture

This example demonstrates the security integration capabilities for service
communication including authentication, authorization, audit logging, and
service isolation.

Requirements demonstrated:
- 8.1: Secure inter-service communication
- 8.2: Service authentication and authorization
- 8.3: Audit logging for service interactions
- 8.4: Service isolation preventing unauthorized access
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from TimeLocker.integration import (
    ServiceManager, ServiceRegistry, SecurityServiceIntegration,
    ServiceSecurityManager, ServiceCredentials, ServiceAuthorizationRule,
    ServicePermission, ServiceAuthenticationMethod
)
from TimeLocker.interfaces.integration_exceptions import ServiceIntegrationError
from TimeLocker.interfaces.integration_data_models import ServiceContext
from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.security.security_service import SecurityService
from TimeLocker.security.credential_manager import CredentialManager
from TimeLocker.config.configuration_manager import ConfigurationManager


class MockConfigurationManager:
    """Mock configuration manager for demo purposes"""
    
    def __init__(self):
        self.config_dir = Path("/tmp/timelocker_demo")
        self.config_dir.mkdir(exist_ok=True)
    
    def get_config_directory(self):
        return self.config_dir


class MockBackupService(ServiceInterface):
    """Mock backup service for demonstration"""
    
    def __init__(self):
        self._initialized = False
        self._context = None
    
    def initialize(self, context: ServiceContext) -> bool:
        self._context = context
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        self._initialized = False
        self._context = None
    
    def health_check(self) -> bool:
        return self._initialized
    
    def get_capabilities(self) -> list:
        return ['backup', 'restore', 'snapshot_management']
    
    def get_service_name(self) -> str:
        return "BackupService"
    
    def create_backup(self, source_path: str, repository_id: str) -> dict:
        """Create a backup (sensitive operation)"""
        return {
            "backup_id": "backup_123",
            "source_path": source_path,
            "repository_id": repository_id,
            "timestamp": datetime.now().isoformat(),
            "status": "completed"
        }
    
    def list_backups(self, repository_id: str) -> list:
        """List backups (read operation)"""
        return [
            {"backup_id": "backup_123", "timestamp": "2024-01-01T10:00:00"},
            {"backup_id": "backup_124", "timestamp": "2024-01-02T10:00:00"}
        ]


class MockRepositoryService(ServiceInterface):
    """Mock repository service for demonstration"""
    
    def __init__(self):
        self._initialized = False
        self._context = None
    
    def initialize(self, context: ServiceContext) -> bool:
        self._context = context
        self._initialized = True
        return True
    
    def shutdown(self) -> None:
        self._initialized = False
        self._context = None
    
    def health_check(self) -> bool:
        return self._initialized
    
    def get_capabilities(self) -> list:
        return ['repository_management', 'credential_storage']
    
    def get_service_name(self) -> str:
        return "RepositoryService"
    
    def get_credentials(self, repository_id: str) -> dict:
        """Get repository credentials (sensitive operation)"""
        return {
            "repository_id": repository_id,
            "username": "user123",
            "password": "secret_password",
            "endpoint": "s3://bucket/path"
        }
    
    def list_repositories(self) -> list:
        """List repositories (read operation)"""
        return [
            {"repository_id": "repo_1", "name": "Primary Backup"},
            {"repository_id": "repo_2", "name": "Archive Storage"}
        ]


def demonstrate_security_integration():
    """Demonstrate security integration capabilities"""
    
    print("=== TimeLocker Security Integration Demo ===\n")
    
    # 1. Setup basic services
    print("1. Setting up services...")
    
    config_manager = MockConfigurationManager()
    credential_manager = CredentialManager()
    security_service = SecurityService(credential_manager, config_manager.config_dir)
    
    # Initialize ServiceManager first
    # Create a temporary service context for ServiceManager initialization
    temp_registry = object()  # Placeholder
    service_context = ServiceContext(
        config_manager=config_manager,
        event_bus=None,  # Will be set by ServiceManager
        service_registry=temp_registry
    )
    
    service_manager = ServiceManager(service_context)
    
    # Update context with actual registry and event bus
    service_context.service_registry = service_manager._registry
    service_context.event_bus = service_manager._event_bus
    
    print("✓ Basic services initialized")
    
    # 2. Enable security integration
    print("\n2. Enabling security integration...")
    
    # Register SecurityService with integration wrapper
    security_integration = SecurityServiceIntegration(security_service)
    service_manager.register_service(SecurityServiceIntegration, security_integration)
    
    # Enable security integration
    service_manager.enable_security_integration(security_service)
    
    print("✓ Security integration enabled")
    
    # 3. Register mock services
    print("\n3. Registering mock services...")
    
    backup_service = MockBackupService()
    repository_service = MockRepositoryService()
    
    service_manager.register_service(MockBackupService, backup_service)
    service_manager.register_service(MockRepositoryService, repository_service)
    
    print("✓ Mock services registered")
    
    # 4. Initialize all services
    print("\n4. Initializing services...")
    
    success = service_manager.initialize_services()
    if not success:
        print("✗ Service initialization failed")
        return
    
    print("✓ All services initialized")
    
    # 5. Configure security settings
    print("\n5. Configuring security settings...")
    
    # Configure security requirements
    service_manager.configure_service_security(
        require_authentication=True,
        require_authorization=True,
        audit_all_interactions=True,
        audit_sensitive_only=False
    )
    
    # Register service credentials
    service_manager.register_service_credentials("CLIService", {
        "method": "token",
        "token": "cli_token_123",
        "expires_at": datetime.now() + timedelta(hours=24)
    })
    
    service_manager.register_service_credentials("BackupService", {
        "method": "shared_secret",
        "shared_secret": "backup_secret_456"
    })
    
    # Add authorization rules
    service_manager.add_service_authorization_rule(
        source_service="CLIService",
        target_service="BackupService", 
        operation="*",
        permission="write"
    )
    
    service_manager.add_service_authorization_rule(
        source_service="CLIService",
        target_service="RepositoryService",
        operation="list_repositories",
        permission="read"
    )
    
    service_manager.add_service_authorization_rule(
        source_service="BackupService",
        target_service="RepositoryService",
        operation="get_credentials",
        permission="read"
    )
    
    print("✓ Security settings configured")
    
    # 6. Demonstrate secure service access
    print("\n6. Demonstrating secure service access...")
    
    try:
        # Get secure service proxy
        secure_backup = service_manager.get_secure_service(MockBackupService, "CLIService")
        
        # Perform authorized operations
        print("   Performing authorized backup operation...")
        backup_result = secure_backup.create_backup("/home/user/documents", "repo_1")
        print(f"   ✓ Backup created: {backup_result['backup_id']}")
        
        # Perform read operation
        print("   Performing authorized list operation...")
        backups = secure_backup.list_backups("repo_1")
        print(f"   ✓ Found {len(backups)} backups")
        
    except Exception as e:
        print(f"   ✗ Secure operation failed: {e}")
    
    # 7. Demonstrate service isolation
    print("\n7. Demonstrating service isolation...")
    
    # Isolate the repository service
    service_manager.isolate_service("RepositoryService")
    
    try:
        # Try to access isolated service
        secure_repo = service_manager.get_secure_service(MockRepositoryService, "CLIService")
        print("   ✗ Should not be able to access isolated service")
    except ServiceIntegrationError as e:
        print(f"   ✓ Access to isolated service correctly denied: {e}")
    
    # Remove isolation
    service_manager.remove_service_isolation("RepositoryService")
    print("   ✓ Service isolation removed")
    
    # 8. Demonstrate unauthorized access
    print("\n8. Demonstrating unauthorized access...")
    
    try:
        # Try to access service without proper authorization
        secure_repo = service_manager.get_secure_service(MockRepositoryService, "UnauthorizedService")
        credentials = secure_repo.get_credentials("repo_1")
        print("   ✗ Should not be able to access without authorization")
    except ServiceIntegrationError as e:
        print(f"   ✓ Unauthorized access correctly denied: {e}")
    
    # 9. Show audit records
    print("\n9. Reviewing audit records...")
    
    audit_records = service_manager.get_service_audit_records(hours=1)
    print(f"   Found {len(audit_records)} audit records:")
    
    for record in audit_records[-3:]:  # Show last 3 records
        status = "SUCCESS" if record["success"] else "FAILED"
        sensitive = " (SENSITIVE)" if record["sensitive_data"] else ""
        print(f"   - {record['source_service']} -> {record['target_service']}.{record['operation']}: {status}{sensitive}")
    
    # 10. Show security status
    print("\n10. Security status summary...")
    
    security_status = service_manager.get_service_security_status()
    print(f"   Security enabled: {security_status['security_enabled']}")
    print(f"   Active credentials: {security_status['active_credentials']}")
    print(f"   Authorization rules: {security_status['authorization_rules']}")
    print(f"   Isolated services: {security_status['isolated_services']}")
    print(f"   Recent interactions (24h): {security_status['recent_interactions_24h']}")
    
    # 11. Cleanup
    print("\n11. Cleaning up...")
    
    try:
        service_manager.shutdown_services()
        print("✓ Services shut down successfully")
    except Exception as e:
        print(f"✗ Shutdown error: {e}")
    
    print("\n=== Demo completed successfully ===")


def demonstrate_security_violations():
    """Demonstrate security violation detection and handling"""
    
    print("\n=== Security Violations Demo ===\n")
    
    # This would demonstrate:
    # - Failed authentication attempts
    # - Authorization violations
    # - Suspicious access patterns
    # - Emergency lockdown procedures
    
    print("Security violations demo would show:")
    print("- Failed authentication logging")
    print("- Authorization violation alerts")
    print("- Suspicious pattern detection")
    print("- Emergency lockdown procedures")
    print("- Security incident response")


if __name__ == "__main__":
    try:
        demonstrate_security_integration()
        demonstrate_security_violations()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()