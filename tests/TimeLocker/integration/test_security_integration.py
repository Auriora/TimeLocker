"""
Tests for Security Integration in TimeLocker Service Architecture

This module tests the security integration capabilities including authentication,
authorization, audit logging, and service isolation for inter-service communication.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from TimeLocker.integration.security_integration import (
    ServiceSecurityManager, SecureServiceProxy, ServiceCredentials,
    ServiceAuthorizationRule, ServiceInteractionAudit, ServicePermission,
    ServiceAuthenticationMethod
)
from TimeLocker.integration.security_service_integration import SecurityServiceIntegration
from TimeLocker.security.security_service import SecurityService, SecurityEvent, SecurityLevel
from TimeLocker.interfaces.service_interface import ServiceInterface
from TimeLocker.interfaces.integration_data_models import ServiceContext


class MockSecurityService:
    """Mock SecurityService for testing"""
    
    def __init__(self):
        self.events = []
        self._initialized = False
    
    def initialize(self, context):
        self._initialized = True
        return True
    
    def shutdown(self):
        self._initialized = False
    
    def health_check(self):
        return self._initialized
    
    def get_capabilities(self):
        return ['encryption_verification', 'audit_logging']
    
    def log_security_event(self, event):
        self.events.append(event)


class MockService(ServiceInterface):
    """Mock service for testing"""
    
    def __init__(self, name="MockService"):
        self.name = name
        self._initialized = False
    
    def initialize(self, context):
        self._initialized = True
        return True
    
    def shutdown(self):
        self._initialized = False
    
    def health_check(self):
        return self._initialized
    
    def get_capabilities(self):
        return ['mock_capability']
    
    def get_service_name(self):
        return self.name
    
    def sensitive_operation(self, data):
        """Mock sensitive operation"""
        return f"processed: {data}"
    
    def read_operation(self):
        """Mock read operation"""
        return "read_result"


class TestServiceCredentials:
    """Test ServiceCredentials functionality"""
    
    def test_token_credentials_valid(self):
        """Test valid token credentials"""
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token_123"
        )
        
        assert credentials.is_valid()
        assert not credentials.is_expired()
    
    def test_expired_credentials(self):
        """Test expired credentials"""
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token_123",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        assert not credentials.is_valid()
        assert credentials.is_expired()
    
    def test_invalid_credentials(self):
        """Test invalid credentials"""
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token=None  # Missing required token
        )
        
        assert not credentials.is_valid()


class TestServiceAuthorizationRule:
    """Test ServiceAuthorizationRule functionality"""
    
    def test_exact_match(self):
        """Test exact rule matching"""
        rule = ServiceAuthorizationRule(
            source_service="ServiceA",
            target_service="ServiceB",
            operation="read",
            permission=ServicePermission.READ
        )
        
        assert rule.matches("ServiceA", "ServiceB", "read")
        assert not rule.matches("ServiceA", "ServiceB", "write")
        assert not rule.matches("ServiceC", "ServiceB", "read")
    
    def test_wildcard_match(self):
        """Test wildcard rule matching"""
        rule = ServiceAuthorizationRule(
            source_service="*",
            target_service="ServiceB",
            operation="*",
            permission=ServicePermission.READ
        )
        
        assert rule.matches("ServiceA", "ServiceB", "read")
        assert rule.matches("ServiceC", "ServiceB", "write")
        assert not rule.matches("ServiceA", "ServiceC", "read")
    
    def test_conditional_match(self):
        """Test conditional rule matching"""
        rule = ServiceAuthorizationRule(
            source_service="ServiceA",
            target_service="ServiceB",
            operation="read",
            permission=ServicePermission.READ,
            conditions={"environment": "production"}
        )
        
        # Should match with correct conditions
        assert rule.matches("ServiceA", "ServiceB", "read", {"environment": "production"})
        
        # Should not match with incorrect conditions
        assert not rule.matches("ServiceA", "ServiceB", "read", {"environment": "development"})
        
        # Should not match without conditions
        assert not rule.matches("ServiceA", "ServiceB", "read")


class TestServiceSecurityManager:
    """Test ServiceSecurityManager functionality"""
    
    @pytest.fixture
    def security_service(self):
        return MockSecurityService()
    
    @pytest.fixture
    def security_manager(self, security_service):
        return ServiceSecurityManager(security_service)
    
    def test_initialization(self, security_manager):
        """Test security manager initialization"""
        assert security_manager.security_service is not None
        assert security_manager._require_authentication
        assert security_manager._require_authorization
    
    def test_configure_security(self, security_manager):
        """Test security configuration"""
        security_manager.configure_security(
            require_authentication=False,
            require_authorization=True,
            audit_all_interactions=False
        )
        
        assert not security_manager._require_authentication
        assert security_manager._require_authorization
        assert not security_manager._audit_all_interactions
    
    def test_register_credentials(self, security_manager):
        """Test credential registration"""
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token"
        )
        
        security_manager.register_service_credentials(credentials)
        
        # Verify credentials are stored
        assert "TestService" in security_manager._credentials
        assert security_manager._credentials["TestService"] == credentials
    
    def test_authenticate_service_success(self, security_manager):
        """Test successful service authentication"""
        # Register credentials
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token"
        )
        security_manager.register_service_credentials(credentials)
        
        # Test authentication
        result = security_manager.authenticate_service("TestService", {"token": "test_token"})
        assert result
    
    def test_authenticate_service_failure(self, security_manager):
        """Test failed service authentication"""
        # Register credentials
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token"
        )
        security_manager.register_service_credentials(credentials)
        
        # Test authentication with wrong token
        result = security_manager.authenticate_service("TestService", {"token": "wrong_token"})
        assert not result
    
    def test_authorization_success(self, security_manager):
        """Test successful service authorization"""
        # Add authorization rule
        rule = ServiceAuthorizationRule(
            source_service="ServiceA",
            target_service="ServiceB",
            operation="read",
            permission=ServicePermission.READ
        )
        security_manager.add_authorization_rule(rule)
        
        # Test authorization
        result = security_manager.authorize_service_operation("ServiceA", "ServiceB", "read")
        assert result
    
    def test_authorization_failure(self, security_manager):
        """Test failed service authorization"""
        # Add authorization rule for different operation
        rule = ServiceAuthorizationRule(
            source_service="ServiceA",
            target_service="ServiceB",
            operation="read",
            permission=ServicePermission.READ
        )
        security_manager.add_authorization_rule(rule)
        
        # Test authorization for unauthorized operation
        result = security_manager.authorize_service_operation("ServiceA", "ServiceB", "write")
        assert not result
    
    def test_service_isolation(self, security_manager):
        """Test service isolation functionality"""
        # Isolate service
        security_manager.isolate_service("TestService")
        assert security_manager.is_service_isolated("TestService")
        
        # Remove isolation
        security_manager.remove_service_isolation("TestService")
        assert not security_manager.is_service_isolated("TestService")
    
    def test_audit_interaction(self, security_manager):
        """Test service interaction auditing"""
        audit_record = ServiceInteractionAudit(
            interaction_id=str(uuid.uuid4()),
            source_service="ServiceA",
            target_service="ServiceB",
            operation="test_operation",
            timestamp=datetime.now(),
            success=True,
            duration_ms=100.0,
            sensitive_data=True
        )
        
        security_manager.audit_service_interaction(audit_record)
        
        # Verify audit record is stored
        records = security_manager.get_audit_records(hours=1)
        assert len(records) == 1
        assert records[0].interaction_id == audit_record.interaction_id
    
    def test_cleanup_expired_credentials(self, security_manager):
        """Test cleanup of expired credentials"""
        # Add expired credentials
        expired_credentials = ServiceCredentials(
            service_name="ExpiredService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="expired_token",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        security_manager.register_service_credentials(expired_credentials)
        
        # Add valid credentials
        valid_credentials = ServiceCredentials(
            service_name="ValidService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="valid_token"
        )
        security_manager.register_service_credentials(valid_credentials)
        
        # Cleanup expired credentials
        expired_count = security_manager.cleanup_expired_credentials()
        
        assert expired_count == 1
        assert "ExpiredService" not in security_manager._credentials
        assert "ValidService" in security_manager._credentials


class TestSecureServiceProxy:
    """Test SecureServiceProxy functionality"""
    
    @pytest.fixture
    def security_service(self):
        return MockSecurityService()
    
    @pytest.fixture
    def security_manager(self, security_service):
        manager = ServiceSecurityManager(security_service)
        
        # Add authorization rule
        rule = ServiceAuthorizationRule(
            source_service="ClientService",
            target_service="MockService",
            operation="*",
            permission=ServicePermission.WRITE
        )
        manager.add_authorization_rule(rule)
        
        return manager
    
    @pytest.fixture
    def target_service(self):
        return MockService()
    
    @pytest.fixture
    def secure_proxy(self, target_service, security_manager):
        return SecureServiceProxy(target_service, security_manager, "ClientService")
    
    def test_authorized_operation(self, secure_proxy):
        """Test authorized operation through proxy"""
        result = secure_proxy.read_operation()
        assert result == "read_result"
    
    def test_sensitive_operation_detection(self, secure_proxy):
        """Test detection of sensitive operations"""
        # This should be detected as sensitive and audited
        result = secure_proxy.sensitive_operation("test_data")
        assert result == "processed: test_data"
    
    def test_isolated_service_access(self, secure_proxy, security_manager):
        """Test access to isolated service"""
        # Isolate the target service
        security_manager.isolate_service("MockService")
        
        # Should raise exception when trying to access isolated service
        with pytest.raises(Exception):
            secure_proxy.read_operation()
    
    def test_unauthorized_operation(self, target_service, security_manager):
        """Test unauthorized operation"""
        # Create proxy with unauthorized source service
        unauthorized_proxy = SecureServiceProxy(
            target_service, security_manager, "UnauthorizedService"
        )
        
        # Should raise exception for unauthorized access
        with pytest.raises(Exception):
            unauthorized_proxy.read_operation()


class TestSecurityServiceIntegration:
    """Test SecurityServiceIntegration functionality"""
    
    @pytest.fixture
    def security_service(self):
        return MockSecurityService()
    
    @pytest.fixture
    def security_integration(self, security_service):
        return SecurityServiceIntegration(security_service)
    
    @pytest.fixture
    def service_context(self):
        mock_config = Mock()
        mock_registry = Mock()
        return ServiceContext(
            config_manager=mock_config,
            event_bus=None,
            service_registry=mock_registry
        )
    
    def test_initialization(self, security_integration, service_context):
        """Test security service integration initialization"""
        result = security_integration.initialize(service_context)
        assert result
        assert security_integration._initialized
    
    def test_health_check(self, security_integration, service_context):
        """Test health check functionality"""
        security_integration.initialize(service_context)
        assert security_integration.health_check()
    
    def test_capabilities(self, security_integration):
        """Test capability reporting"""
        capabilities = security_integration.get_capabilities()
        
        expected_capabilities = [
            'service_authentication',
            'service_authorization', 
            'service_audit_logging',
            'service_isolation',
            'secure_communication',
            'credential_management',
            'security_monitoring'
        ]
        
        for capability in expected_capabilities:
            assert capability in capabilities
    
    def test_audit_service_interaction(self, security_integration, service_context):
        """Test service interaction auditing"""
        security_integration.initialize(service_context)
        
        security_integration.audit_service_interaction(
            source_service="ServiceA",
            target_service="ServiceB",
            operation="test_operation",
            success=True,
            duration_ms=150.0,
            sensitive_data=True
        )
        
        # Verify event was logged to underlying security service
        assert len(security_integration.security_service.events) == 1
        event = security_integration.security_service.events[0]
        assert event.event_type == "service_interaction"
        assert event.level == SecurityLevel.HIGH  # Because sensitive_data=True
    
    def test_log_security_violation(self, security_integration, service_context):
        """Test security violation logging"""
        security_integration.initialize(service_context)
        
        security_integration.log_security_violation(
            violation_type="unauthorized_access",
            source_service="MaliciousService",
            target_service="SecureService",
            details="Attempted to access without proper credentials"
        )
        
        # Verify violation was logged
        assert len(security_integration.security_service.events) == 1
        event = security_integration.security_service.events[0]
        assert event.event_type == "security_violation"
        assert event.level == SecurityLevel.CRITICAL
    
    def test_delegation_to_security_service(self, security_integration):
        """Test delegation of unknown methods to underlying SecurityService"""
        # Test that unknown methods are delegated to the security service
        capabilities = security_integration.get_capabilities()
        assert 'encryption_verification' in capabilities  # From MockSecurityService
    
    def test_shutdown(self, security_integration, service_context):
        """Test shutdown functionality"""
        security_integration.initialize(service_context)
        security_integration.shutdown()
        
        assert not security_integration._initialized
        assert not security_integration.security_service._initialized


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def test_complete_security_workflow(self):
        """Test complete security workflow from registration to audit"""
        # Setup
        security_service = MockSecurityService()
        security_manager = ServiceSecurityManager(security_service)
        
        # 1. Register credentials
        credentials = ServiceCredentials(
            service_name="TestService",
            authentication_method=ServiceAuthenticationMethod.TOKEN,
            token="test_token"
        )
        security_manager.register_service_credentials(credentials)
        
        # 2. Add authorization rule
        rule = ServiceAuthorizationRule(
            source_service="ClientService",
            target_service="TestService",
            operation="read",
            permission=ServicePermission.READ
        )
        security_manager.add_authorization_rule(rule)
        
        # 3. Authenticate service
        auth_result = security_manager.authenticate_service("TestService", {"token": "test_token"})
        assert auth_result
        
        # 4. Authorize operation
        authz_result = security_manager.authorize_service_operation("ClientService", "TestService", "read")
        assert authz_result
        
        # 5. Audit interaction
        audit_record = ServiceInteractionAudit(
            interaction_id=str(uuid.uuid4()),
            source_service="ClientService",
            target_service="TestService",
            operation="read",
            timestamp=datetime.now(),
            success=True,
            duration_ms=50.0
        )
        security_manager.audit_service_interaction(audit_record)
        
        # 6. Verify audit trail
        records = security_manager.get_audit_records(hours=1)
        assert len(records) == 1
        
        # 7. Check security events
        assert len(security_service.events) >= 3  # Registration, auth, authz events
    
    def test_security_violation_scenario(self):
        """Test security violation detection and response"""
        security_service = MockSecurityService()
        security_manager = ServiceSecurityManager(security_service)
        
        # Try to authenticate with invalid credentials
        auth_result = security_manager.authenticate_service("UnknownService", {"token": "invalid"})
        assert not auth_result
        
        # Try unauthorized operation
        authz_result = security_manager.authorize_service_operation("UnauthorizedService", "SecureService", "admin")
        assert not authz_result
        
        # Verify security events were logged
        auth_events = [e for e in security_service.events if e.event_type == "service_authentication"]
        authz_events = [e for e in security_service.events if e.event_type == "service_authorization"]
        
        assert len(auth_events) == 1
        assert len(authz_events) == 1
        
        # Both should be high/critical level due to failures
        assert auth_events[0].level == SecurityLevel.HIGH
        assert authz_events[0].level == SecurityLevel.HIGH