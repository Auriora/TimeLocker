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

from .integration_service import IntegrationService, IntegrationError
from .service_manager import ServiceManager, ServiceRegistry
from .dependency_injector import DependencyInjector, ServiceRegistration, DependencyType
from .event_bus import EventBus, EventFilter, EventSubscription, EventPersistence, DeadLetterQueue
from .error_propagation import (
    ErrorPropagationSystem, ErrorSeverity, ErrorCategory, ErrorContext, 
    PropagatedError, ErrorTranslator, ErrorCorrelator, ErrorRecoveryManager,
    error_propagation_system, propagate_error, attempt_recovery
)
from .error_integration import (
    ServiceErrorHandler, ServiceInterfaceErrorMixin, 
    with_service_error_handling, service_error_context,
    create_service_with_error_handling,
    handle_configuration_error, handle_network_error, handle_authentication_error
)
from .service_optimization import (
    ServiceOptimizationManager, ServiceConnectionPool, AsyncServiceOperationManager,
    ServicePerformanceMonitor, ServiceConnectionMetrics, PerformanceThreshold
)
from .optimized_service_context import (
    OptimizedServiceContext, AsyncServiceOperationContext, ServiceOperationContext,
    optimized_service, create_async_operation
)
from .security_integration import (
    ServiceSecurityManager, SecureServiceProxy, ServiceCredentials, 
    ServiceAuthorizationRule, ServiceInteractionAudit, ServicePermission,
    ServiceAuthenticationMethod
)
from .security_service_integration import SecurityServiceIntegration

# Integration Testing and Validation Support (Requirement 9.1-9.5)
from .service_mocking import (
    MockServiceInterface, ServiceMockFactory, MockingContext, MockBehavior,
    create_mock_service_context, mock_service_method, verify_service_calls
)
from .integration_testing import (
    IntegrationTestEnvironment, TestEnvironmentConfig, IntegrationTestSuite,
    integration_test_environment, create_basic_integration_test, create_event_flow_test
)
from .service_health_checks import (
    ServiceHealthChecker, IntegrationPointValidator, HealthMonitor,
    HealthStatus, HealthCheckType, HealthCheckConfig, HealthCheckResult,
    create_basic_health_check, validate_service_integration, monitor_services_temporarily
)
from .integration_monitoring import (
    IntegrationMonitor, MonitoringLevel, MetricsCollector, AlertManager,
    AlertSeverity, MonitoringMetric, IntegrationAlert, SystemHealthSnapshot,
    create_basic_integration_monitor, monitor_integration_temporarily
)
from .integration_diagnostics import (
    DiagnosticAnalyzer, DiagnosticSeverity, DiagnosticCategory, DiagnosticFinding,
    SystemDiagnosticReport, DiagnosticReportGenerator,
    diagnose_service_health, generate_system_diagnostic_report
)

# Legacy global alias for tests referencing bare ConfigSection without imports
try:
    import builtins  # type: ignore
    from ..config import ConfigSection as _ConfigSection
    if not hasattr(builtins, 'ConfigSection'):
        setattr(builtins, 'ConfigSection', _ConfigSection)
except Exception:
    pass


__all__ = [
    'IntegrationService', 'IntegrationError', 'ServiceManager', 'ServiceRegistry', 
    'DependencyInjector', 'ServiceRegistration', 'DependencyType',
    'EventBus', 'EventFilter', 'EventSubscription', 'EventPersistence', 'DeadLetterQueue',
    'ErrorPropagationSystem', 'ErrorSeverity', 'ErrorCategory', 'ErrorContext', 
    'PropagatedError', 'ErrorTranslator', 'ErrorCorrelator', 'ErrorRecoveryManager',
    'error_propagation_system', 'propagate_error', 'attempt_recovery',
    'ServiceErrorHandler', 'ServiceInterfaceErrorMixin', 
    'with_service_error_handling', 'service_error_context',
    'create_service_with_error_handling',
    'handle_configuration_error', 'handle_network_error', 'handle_authentication_error',
    'ServiceOptimizationManager', 'ServiceConnectionPool', 'AsyncServiceOperationManager',
    'ServicePerformanceMonitor', 'ServiceConnectionMetrics', 'PerformanceThreshold',
    'OptimizedServiceContext', 'AsyncServiceOperationContext', 'ServiceOperationContext',
    'optimized_service', 'create_async_operation',
    'ServiceSecurityManager', 'SecureServiceProxy', 'ServiceCredentials', 
    'ServiceAuthorizationRule', 'ServiceInteractionAudit', 'ServicePermission',
    'ServiceAuthenticationMethod', 'SecurityServiceIntegration',
    # Integration Testing and Validation Support
    'MockServiceInterface', 'ServiceMockFactory', 'MockingContext', 'MockBehavior',
    'create_mock_service_context', 'mock_service_method', 'verify_service_calls',
    'IntegrationTestEnvironment', 'TestEnvironmentConfig', 'IntegrationTestSuite',
    'integration_test_environment', 'create_basic_integration_test', 'create_event_flow_test',
    'ServiceHealthChecker', 'IntegrationPointValidator', 'HealthMonitor',
    'HealthStatus', 'HealthCheckType', 'HealthCheckConfig', 'HealthCheckResult',
    'create_basic_health_check', 'validate_service_integration', 'monitor_services_temporarily',
    'IntegrationMonitor', 'MonitoringLevel', 'MetricsCollector', 'AlertManager',
    'AlertSeverity', 'MonitoringMetric', 'IntegrationAlert', 'SystemHealthSnapshot',
    'create_basic_integration_monitor', 'monitor_integration_temporarily',
    'DiagnosticAnalyzer', 'DiagnosticSeverity', 'DiagnosticCategory', 'DiagnosticFinding',
    'SystemDiagnosticReport', 'DiagnosticReportGenerator',
    'diagnose_service_health', 'generate_system_diagnostic_report'
]
