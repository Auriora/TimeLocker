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
Integration Test Suite for Integration Architecture

This module provides comprehensive integration tests for the integration architecture
covering CLI service orchestration, performance optimization, security integration,
and end-to-end service interaction scenarios.

Requirements tested:
- 1.1: CLI Service Manager orchestration
- 7.1: Service communication performance optimization
- 8.1: Secure service communication
- 9.2: Integration testing support
"""

import pytest
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.TimeLocker.integration import (
    ServiceManager,
    DependencyInjector,
    EventBus
)
from src.TimeLocker.interfaces import (
    ServiceInterface,
    ServiceContext,
    ServiceInitializationError
)


# Test service implementations for integration testing
class MockRepositoryService(ServiceInterface):
    """Mock repository service for testing"""
    
    def __init__(self):
        self.initialized = False
        self.operations_count = 0
        self.init_time = None
        
    def initialize(self, context: ServiceContext) -> bool:
        self.init_time = time.time()
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> list:
        return ['repository_management', 'backup', 'restore']
    
    def list_repositories(self):
        """Mock repository listing"""
        self.operations_count += 1
        return ['repo1', 'repo2']
    
    def get_repository(self, name: str):
        """Mock repository retrieval"""
        self.operations_count += 1
        return {'name': name, 'uri': f'file:///tmp/{name}'}


class MockSecurityService(ServiceInterface):
    """Mock security service for testing"""
    
    def __init__(self):
        self.initialized = False
        self.auth_checks = 0
        self.init_time = None
        
    def initialize(self, context: ServiceContext) -> bool:
        self.init_time = time.time()
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> list:
        return ['authentication', 'authorization', 'encryption']
    
    def authenticate(self, credentials: dict) -> bool:
        """Mock authentication"""
        self.auth_checks += 1
        return credentials.get('valid', False)
    
    def authorize(self, operation: str, resource: str) -> bool:
        """Mock authorization"""
        self.auth_checks += 1
        return True


class MockBackupService(ServiceInterface):
    """Mock backup service for testing"""
    
    def __init__(self):
        self.initialized = False
        self.backups_created = 0
        self.init_time = None
        
    def initialize(self, context: ServiceContext) -> bool:
        self.init_time = time.time()
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> list:
        return ['backup_creation', 'backup_verification']
    
    def create_backup(self, paths: list, repository: str) -> dict:
        """Mock backup creation"""
        self.backups_created += 1
        return {
            'success': True,
            'snapshot_id': f'snapshot_{self.backups_created}',
            'files_backed_up': len(paths)
        }


class TestCLIServiceOrchestration:
    """
    Test CLI service orchestration workflows
    
    Requirements: 1.1 - CLI Service Manager orchestration
    """
    
    @pytest.fixture
    def service_context(self):
        """Create service context for testing"""
        return ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
    
    def test_cli_service_initialization_workflow(self, service_context):
        """Test complete CLI service initialization workflow"""
        # Create service manager
        manager = ServiceManager(service_context)
        
        # Register services in dependency order
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(
            MockRepositoryService, 
            repository_service,
            dependencies=[MockSecurityService]
        )
        manager.register_service(
            MockBackupService,
            backup_service,
            dependencies=[MockRepositoryService, MockSecurityService]
        )
        
        # Initialize all services
        result = manager.initialize_services()
        assert result is True
        
        # Verify initialization order (security first, then repository, then backup)
        assert security_service.init_time < repository_service.init_time
        assert repository_service.init_time < backup_service.init_time
        
        # Verify all services are accessible
        assert manager.get_service(MockSecurityService) is security_service
        assert manager.get_service(MockRepositoryService) is repository_service
        assert manager.get_service(MockBackupService) is backup_service
    
    def test_cli_command_service_coordination(self, service_context):
        """Test CLI command coordinating multiple services"""
        manager = ServiceManager(service_context)
        
        # Register and initialize services
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(MockRepositoryService, repository_service)
        manager.register_service(MockBackupService, backup_service)
        manager.initialize_services()
        
        # Simulate CLI backup command workflow
        # 1. Authenticate user
        auth_result = security_service.authenticate({'valid': True})
        assert auth_result is True
        
        # 2. Get repository
        repo = repository_service.get_repository('test-repo')
        assert repo['name'] == 'test-repo'
        
        # 3. Authorize backup operation
        auth_result = security_service.authorize('backup', repo['uri'])
        assert auth_result is True
        
        # 4. Create backup
        backup_result = backup_service.create_backup(['/tmp/test'], repo['uri'])
        assert backup_result['success'] is True
        
        # Verify service interactions
        assert security_service.auth_checks == 2  # authenticate + authorize
        assert repository_service.operations_count == 1  # get_repository
        assert backup_service.backups_created == 1
    
    def test_cli_service_error_handling(self, service_context):
        """Test CLI service error handling and recovery"""
        manager = ServiceManager(service_context)
        
        # Create service that fails initialization
        class FailingService(ServiceInterface):
            def initialize(self, context):
                raise RuntimeError("Service initialization failed")
            def shutdown(self): pass
            def health_check(self): return False
            def get_capabilities(self): return []
        
        failing_service = FailingService()
        manager.register_service(FailingService, failing_service)
        
        # Initialization should fail gracefully
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
    
    def test_cli_service_lifecycle_management(self, service_context):
        """Test complete service lifecycle through CLI operations"""
        manager = ServiceManager(service_context)
        
        # Register services
        repository_service = MockRepositoryService()
        manager.register_service(MockRepositoryService, repository_service)
        
        # Initialize
        manager.initialize_services()
        assert repository_service.initialized is True
        
        # Use service
        repos = repository_service.list_repositories()
        assert len(repos) == 2
        
        # Shutdown
        manager.shutdown_services()
        assert repository_service.initialized is False


class TestServiceCommunicationPerformance:
    """
    Test service communication performance and optimization
    
    Requirements: 7.1 - Service communication performance optimization
    """
    
    @pytest.fixture
    def service_context(self):
        """Create service context for testing"""
        return ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
    
    def test_service_initialization_performance(self, service_context):
        """Test service initialization completes within performance requirements"""
        manager = ServiceManager(service_context)
        
        # Register multiple services
        services = []
        for i in range(5):
            service = MockRepositoryService()
            services.append(service)
            manager.register_service(type(f'Service{i}', (MockRepositoryService,), {}), service)
        
        # Measure initialization time
        start_time = time.time()
        manager.initialize_services()
        init_time = time.time() - start_time
        
        # Should complete within 100ms for local operations (requirement 7.1)
        assert init_time < 0.1, f"Initialization took {init_time}s, expected < 0.1s"
    
    def test_service_call_performance(self, service_context):
        """Test service calls complete within performance requirements"""
        manager = ServiceManager(service_context)
        
        repository_service = MockRepositoryService()
        manager.register_service(MockRepositoryService, repository_service)
        manager.initialize_services()
        
        service = manager.get_service(MockRepositoryService)
        
        # Measure service call time
        start_time = time.time()
        for _ in range(100):
            service.list_repositories()
        call_time = (time.time() - start_time) / 100
        
        # Each call should complete within 10ms for local operations (requirement 7.1)
        assert call_time < 0.01, f"Average call took {call_time}s, expected < 0.01s"
    
    def test_service_connection_pooling(self, service_context):
        """Test service connection pooling and reuse"""
        manager = ServiceManager(service_context)
        
        repository_service = MockRepositoryService()
        manager.register_service(MockRepositoryService, repository_service)
        manager.initialize_services()
        
        # Get service multiple times
        service1 = manager.get_service(MockRepositoryService)
        service2 = manager.get_service(MockRepositoryService)
        service3 = manager.get_service(MockRepositoryService)
        
        # Should return same instance (connection pooling)
        assert service1 is service2
        assert service2 is service3
        
        # Should only initialize once
        assert repository_service.operations_count == 0  # No operations yet
    
    def test_concurrent_service_access_performance(self, service_context):
        """Test concurrent service access performance"""
        manager = ServiceManager(service_context)
        
        repository_service = MockRepositoryService()
        manager.register_service(MockRepositoryService, repository_service)
        manager.initialize_services()
        
        service = manager.get_service(MockRepositoryService)
        
        # Concurrent access from multiple threads
        def access_service():
            for _ in range(10):
                service.list_repositories()
        
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=access_service)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # 50 total operations (5 threads * 10 operations) should complete quickly
        assert total_time < 0.5, f"Concurrent access took {total_time}s, expected < 0.5s"
        assert repository_service.operations_count == 50
    
    def test_service_health_check_performance(self, service_context):
        """Test service health check performance"""
        manager = ServiceManager(service_context)
        
        # Register multiple services
        for i in range(10):
            service = MockRepositoryService()
            manager.register_service(type(f'Service{i}', (MockRepositoryService,), {}), service)
        
        manager.initialize_services()
        
        # Measure health check time
        start_time = time.time()
        health_status = manager.health_check()
        health_check_time = time.time() - start_time
        
        # Health check should be fast
        assert health_check_time < 0.05, f"Health check took {health_check_time}s, expected < 0.05s"
        assert len(health_status) == 10


class TestSecurityIntegration:
    """
    Test security integration for service authentication and authorization
    
    Requirements: 8.1 - Secure service communication
    """
    
    @pytest.fixture
    def service_context(self):
        """Create service context for testing"""
        return ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
    
    def test_service_authentication(self, service_context):
        """Test service authentication for sensitive operations"""
        manager = ServiceManager(service_context)
        
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(
            MockRepositoryService,
            repository_service,
            dependencies=[MockSecurityService]
        )
        manager.initialize_services()
        
        # Test authentication
        security = manager.get_service(MockSecurityService)
        
        # Valid credentials
        assert security.authenticate({'valid': True}) is True
        
        # Invalid credentials
        assert security.authenticate({'valid': False}) is False
        
        assert security.auth_checks == 2
    
    def test_service_authorization(self, service_context):
        """Test service authorization for operations"""
        manager = ServiceManager(service_context)
        
        security_service = MockSecurityService()
        manager.register_service(MockSecurityService, security_service)
        manager.initialize_services()
        
        security = manager.get_service(MockSecurityService)
        
        # Test authorization for different operations
        assert security.authorize('backup', '/tmp/repo') is True
        assert security.authorize('restore', '/tmp/repo') is True
        assert security.authorize('delete', '/tmp/repo') is True
        
        assert security.auth_checks == 3
    
    def test_secure_service_communication(self, service_context):
        """Test secure communication between services"""
        manager = ServiceManager(service_context)
        
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(
            MockRepositoryService,
            repository_service,
            dependencies=[MockSecurityService]
        )
        manager.register_service(
            MockBackupService,
            backup_service,
            dependencies=[MockSecurityService, MockRepositoryService]
        )
        manager.initialize_services()
        
        # Simulate secure workflow
        security = manager.get_service(MockSecurityService)
        repository = manager.get_service(MockRepositoryService)
        backup = manager.get_service(MockBackupService)
        
        # 1. Authenticate
        assert security.authenticate({'valid': True}) is True
        
        # 2. Get repository (requires authentication)
        repo = repository.get_repository('secure-repo')
        
        # 3. Authorize backup operation
        assert security.authorize('backup', repo['uri']) is True
        
        # 4. Create backup
        result = backup.create_backup(['/tmp/data'], repo['uri'])
        assert result['success'] is True
    
    def test_service_isolation(self, service_context):
        """Test service isolation preventing unauthorized access"""
        manager = ServiceManager(service_context)
        
        # Create distinct service types for isolation testing
        class Service1(MockRepositoryService):
            pass
        
        class Service2(MockRepositoryService):
            pass
        
        # Register services with different security contexts
        service1 = Service1()
        service2 = Service2()
        
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        manager.initialize_services()
        
        # Services should be isolated
        retrieved1 = manager.get_service(Service1)
        retrieved2 = manager.get_service(Service2)
        
        assert retrieved1 is not retrieved2
        assert retrieved1 is service1
        assert retrieved2 is service2


class TestEndToEndServiceInteraction:
    """
    Test complete end-to-end service interaction scenarios
    
    Requirements: 9.2 - Integration testing support
    """
    
    @pytest.fixture
    def service_context(self):
        """Create service context for testing"""
        return ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
    
    def test_complete_backup_workflow(self, service_context):
        """Test complete backup workflow from CLI to backend"""
        manager = ServiceManager(service_context)
        
        # Register all required services
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(MockRepositoryService, repository_service)
        manager.register_service(MockBackupService, backup_service)
        manager.initialize_services()
        
        # Complete workflow
        security = manager.get_service(MockSecurityService)
        repository = manager.get_service(MockRepositoryService)
        backup = manager.get_service(MockBackupService)
        
        # 1. User authentication
        auth_result = security.authenticate({'valid': True, 'user': 'testuser'})
        assert auth_result is True
        
        # 2. List available repositories
        repos = repository.list_repositories()
        assert len(repos) == 2
        
        # 3. Select repository
        repo = repository.get_repository(repos[0])
        assert repo['name'] == repos[0]
        
        # 4. Authorize backup operation
        auth_result = security.authorize('backup', repo['uri'])
        assert auth_result is True
        
        # 5. Create backup
        backup_result = backup.create_backup(['/tmp/data1', '/tmp/data2'], repo['uri'])
        assert backup_result['success'] is True
        assert backup_result['files_backed_up'] == 2
        
        # Verify all services were used
        assert security.auth_checks == 2
        assert repository.operations_count == 2
        assert backup.backups_created == 1
    
    def test_multi_repository_backup_workflow(self, service_context):
        """Test backup workflow across multiple repositories"""
        manager = ServiceManager(service_context)
        
        security_service = MockSecurityService()
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockSecurityService, security_service)
        manager.register_service(MockRepositoryService, repository_service)
        manager.register_service(MockBackupService, backup_service)
        manager.initialize_services()
        
        security = manager.get_service(MockSecurityService)
        repository = manager.get_service(MockRepositoryService)
        backup = manager.get_service(MockBackupService)
        
        # Authenticate once
        security.authenticate({'valid': True})
        
        # Backup to multiple repositories
        repos = repository.list_repositories()
        for repo_name in repos:
            repo = repository.get_repository(repo_name)
            security.authorize('backup', repo['uri'])
            result = backup.create_backup(['/tmp/data'], repo['uri'])
            assert result['success'] is True
        
        # Verify multiple backups created
        assert backup.backups_created == 2
        assert repository.operations_count == 3  # list + 2 gets
    
    def test_service_failure_recovery_workflow(self, service_context):
        """Test service failure and recovery workflow"""
        manager = ServiceManager(service_context)
        
        # Create service that can fail and recover
        class RecoverableService(ServiceInterface):
            def __init__(self):
                self.initialized = False
                self.failure_count = 0
                self.max_failures = 2
                
            def initialize(self, context):
                if self.failure_count < self.max_failures:
                    self.failure_count += 1
                    raise RuntimeError("Temporary failure")
                self.initialized = True
                return True
            
            def shutdown(self):
                self.initialized = False
            
            def health_check(self):
                return self.initialized
            
            def get_capabilities(self):
                return ['recoverable']
        
        recoverable_service = RecoverableService()
        manager.register_service(RecoverableService, recoverable_service)
        
        # First attempt should fail
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
        
        # Second attempt should fail
        with pytest.raises(ServiceInitializationError):
            manager.initialize_services()
        
        # Third attempt should succeed
        result = manager.initialize_services()
        assert result is True
        assert recoverable_service.initialized is True
    
    def test_event_driven_service_coordination(self, service_context):
        """Test event-driven coordination between services"""
        event_bus = EventBus(enable_persistence=False)
        service_context.event_bus = event_bus
        
        manager = ServiceManager(service_context)
        
        backup_service = MockBackupService()
        manager.register_service(MockBackupService, backup_service)
        manager.initialize_services()
        
        # Track events
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        event_bus.subscribe_event(
            event_type_pattern="backup.*",
            handler=event_handler
        )
        
        # Simulate backup operation that publishes events
        from src.TimeLocker.interfaces.integration_data_models import Event
        
        backup = manager.get_service(MockBackupService)
        
        # Publish backup started event
        event_bus.publish_event(Event(
            event_type="backup.started",
            source="backup_service",
            timestamp=datetime.now(),
            data={'repository': 'test-repo'}
        ))
        
        # Create backup
        result = backup.create_backup(['/tmp/data'], 'test-repo')
        
        # Publish backup completed event
        event_bus.publish_event(Event(
            event_type="backup.completed",
            source="backup_service",
            timestamp=datetime.now(),
            data={'snapshot_id': result['snapshot_id']}
        ))
        
        # Verify events were received
        assert len(events_received) == 2
        assert events_received[0].event_type == "backup.started"
        assert events_received[1].event_type == "backup.completed"
    
    def test_service_health_monitoring_workflow(self, service_context):
        """Test continuous service health monitoring"""
        manager = ServiceManager(service_context)
        
        # Create distinct service types
        class Service0(MockRepositoryService):
            pass
        
        class Service1(MockRepositoryService):
            pass
        
        class Service2(MockRepositoryService):
            pass
        
        # Register multiple services
        service0 = Service0()
        service1 = Service1()
        service2 = Service2()
        
        manager.register_service(Service0, service0)
        manager.register_service(Service1, service1)
        manager.register_service(Service2, service2)
        
        manager.initialize_services()
        
        # Initial health check - all healthy
        health_status = manager.health_check()
        assert all(health_status.values())
        
        # Simulate service failure
        service1.initialized = False
        
        # Health check should detect failure
        health_status = manager.health_check()
        assert health_status['Service0'] is True
        assert health_status['Service1'] is False
        assert health_status['Service2'] is True
        
        # Recover service
        service1.initialized = True
        
        # Health check should show recovery
        health_status = manager.health_check()
        assert all(health_status.values())


class TestIntegrationTestingSupport:
    """
    Test integration testing support features
    
    Requirements: 9.2 - Integration testing support
    """
    
    def test_service_mocking_capabilities(self):
        """Test service mocking for isolated testing"""
        # Create mock service
        mock_service = MockRepositoryService()
        
        # Verify mock capabilities
        assert mock_service.health_check() is False  # Not initialized
        
        # Initialize mock
        context = ServiceContext(
            config_manager=Mock(),
            event_bus=Mock(),
            service_registry=Mock()
        )
        mock_service.initialize(context)
        
        assert mock_service.health_check() is True
        assert mock_service.get_capabilities() == ['repository_management', 'backup', 'restore']
    
    def test_integration_test_isolation(self):
        """Test isolation between integration tests"""
        # Create separate service managers for isolation
        context1 = ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
        
        context2 = ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
        
        manager1 = ServiceManager(context1)
        manager2 = ServiceManager(context2)
        
        # Register services in both managers
        service1 = MockRepositoryService()
        service2 = MockRepositoryService()
        
        manager1.register_service(MockRepositoryService, service1)
        manager2.register_service(MockRepositoryService, service2)
        
        manager1.initialize_services()
        manager2.initialize_services()
        
        # Services should be isolated
        retrieved1 = manager1.get_service(MockRepositoryService)
        retrieved2 = manager2.get_service(MockRepositoryService)
        
        assert retrieved1 is service1
        assert retrieved2 is service2
        assert retrieved1 is not retrieved2
    
    def test_integration_validation_tools(self):
        """Test integration validation and monitoring tools"""
        context = ServiceContext(
            config_manager=Mock(),
            event_bus=EventBus(enable_persistence=False),
            service_registry=Mock()
        )
        
        manager = ServiceManager(context)
        
        # Register services
        repository_service = MockRepositoryService()
        backup_service = MockBackupService()
        
        manager.register_service(MockRepositoryService, repository_service)
        manager.register_service(MockBackupService, backup_service)
        manager.initialize_services()
        
        # Get service status
        status = manager.get_service_status()
        
        # Verify status information
        assert 'MockRepositoryService' in status
        assert 'MockBackupService' in status
        
        assert status['MockRepositoryService']['initialized'] is True
        assert status['MockRepositoryService']['healthy'] is True
        assert status['MockBackupService']['initialized'] is True
        assert status['MockBackupService']['healthy'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
