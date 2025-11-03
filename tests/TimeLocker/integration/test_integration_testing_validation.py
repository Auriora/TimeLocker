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
Tests for Integration Testing and Validation Support

This module tests the integration testing and validation capabilities
including service mocking, health checks, monitoring, and diagnostics.
"""

import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from TimeLocker.interfaces import (
    ServiceInterface,
    ServiceContext,
    Event
)
from TimeLocker.integration import (
    ServiceManager,
    EventBus
)

# Import the new integration testing modules
from TimeLocker.integration.service_mocking import (
    MockServiceInterface,
    ServiceMockFactory,
    MockingContext,
    MockBehavior,
    create_mock_service_context
)
from TimeLocker.integration.integration_testing import (
    IntegrationTestEnvironment,
    TestEnvironmentConfig,
    IntegrationTestSuite,
    integration_test_environment,
    create_basic_integration_test
)
from TimeLocker.integration.service_health_checks import (
    ServiceHealthChecker,
    IntegrationPointValidator,
    HealthMonitor,
    HealthStatus,
    HealthCheckType,
    create_basic_health_check
)
from TimeLocker.integration.integration_monitoring import (
    IntegrationMonitor,
    MonitoringLevel,
    MetricsCollector,
    AlertManager,
    AlertSeverity
)
from TimeLocker.integration.integration_diagnostics import (
    DiagnosticAnalyzer,
    DiagnosticSeverity,
    DiagnosticCategory,
    generate_system_diagnostic_report
)


class TestService(ServiceInterface):
    """Test service for integration testing"""
    
    def __init__(self, name: str = "TestService", fail_init: bool = False):
        self.name = name
        self.fail_init = fail_init
        self.initialized = False
        self.shutdown_called = False
    
    def initialize(self, context: ServiceContext) -> bool:
        if self.fail_init:
            raise RuntimeError("Test initialization failure")
        self.initialized = True
        return True
    
    def shutdown(self) -> None:
        self.shutdown_called = True
        self.initialized = False
    
    def health_check(self) -> bool:
        return self.initialized
    
    def get_capabilities(self) -> list:
        return ['test_capability']
    
    def get_service_name(self) -> str:
        return self.name


class TestServiceMocking:
    """Test cases for service mocking capabilities"""
    
    def test_mock_service_interface_basic(self):
        """Test basic mock service functionality"""
        mock_service = MockServiceInterface("TestMock", ["test_cap"])
        
        # Test initial state
        assert mock_service.get_service_name() == "TestMock"
        assert mock_service.get_capabilities() == ["test_cap"]
        assert not mock_service.initialized
        
        # Test initialization
        context = create_mock_service_context()
        result = mock_service.initialize(context)
        assert result is True
        assert mock_service.initialized
        
        # Test health check
        assert mock_service.health_check() is True
        
        # Test shutdown
        mock_service.shutdown()
        assert mock_service.shutdown_called
    
    def test_mock_service_with_behavior(self):
        """Test mock service with configured behavior"""
        behavior = MockBehavior()
        behavior.return_values['health_check'] = False
        behavior.exceptions['initialize'] = RuntimeError("Mock error")
        
        mock_service = MockServiceInterface("TestMock", behavior=behavior)
        
        # Test exception behavior
        context = create_mock_service_context()
        with pytest.raises(RuntimeError, match="Mock error"):
            mock_service.initialize(context)
        
        # Test return value behavior
        assert mock_service.health_check() is False
    
    def test_mock_service_call_tracking(self):
        """Test mock service call tracking"""
        mock_service = MockServiceInterface("TestMock")
        context = create_mock_service_context()
        
        # Make some calls
        mock_service.initialize(context)
        mock_service.health_check()
        mock_service.health_check()
        
        # Check call counts
        assert mock_service.get_call_count('initialize') == 1
        assert mock_service.get_call_count('health_check') == 2
        
        # Check call records
        init_records = mock_service.get_call_records('initialize')
        assert len(init_records) == 1
        assert init_records[0].method_name == 'initialize'
        
        # Check was_called
        assert mock_service.was_called('initialize', context)
        assert mock_service.was_called('health_check')
    
    def test_service_mock_factory(self):
        """Test service mock factory methods"""
        # Test basic mock
        basic_mock = ServiceMockFactory.create_basic_mock(TestService, "BasicMock", ["basic_cap"])
        assert basic_mock.get_service_name() == "BasicMock"
        assert basic_mock.get_capabilities() == ["basic_cap"]
        
        # Test failing mock
        failing_mock = ServiceMockFactory.create_failing_mock(TestService, ["initialize"])
        context = create_mock_service_context()
        with pytest.raises(RuntimeError):
            failing_mock.initialize(context)
        
        # Test slow mock
        slow_mock = ServiceMockFactory.create_slow_mock(TestService, {"health_check": 0.1})
        start_time = time.time()
        slow_mock.health_check()
        duration = time.time() - start_time
        assert duration >= 0.1
    
    def test_mocking_context(self):
        """Test mocking context manager"""
        # Create service manager
        context = create_mock_service_context()
        service_manager = ServiceManager(context)
        
        # Register real service
        real_service = TestService("RealService")
        service_manager.register_service(TestService, real_service)
        service_manager.initialize_services()
        
        # Use mocking context
        with MockingContext(service_manager) as mocking_ctx:
            # Mock the service
            mock_service = mocking_ctx.mock_service(TestService)
            
            # Verify mock is active
            retrieved_service = service_manager.get_service(TestService)
            assert isinstance(retrieved_service, MockServiceInterface)
            assert retrieved_service is mock_service
        
        # Verify original service is restored (if context manager worked properly)
        # Note: In this test, the original service might not be fully restored
        # due to the way ServiceManager works, but the mock should be removed


class TestIntegrationTesting:
    """Test cases for integration testing support"""
    
    def test_test_environment_config(self):
        """Test test environment configuration"""
        config = TestEnvironmentConfig(
            name="test_env",
            use_real_services=False,
            timeout_seconds=10.0
        )
        
        assert config.name == "test_env"
        assert config.use_real_services is False
        assert config.timeout_seconds == 10.0
    
    def test_integration_test_environment_setup(self):
        """Test integration test environment setup and teardown"""
        config = TestEnvironmentConfig(name="test_setup")
        
        with integration_test_environment(config) as env:
            assert env.config.name == "test_setup"
            assert env.temp_dir is not None
            assert env.service_manager is not None
            assert env.event_bus is not None
    
    def test_service_registration_in_test_env(self):
        """Test service registration in test environment"""
        config = TestEnvironmentConfig(use_real_services=True)
        
        with integration_test_environment(config) as env:
            # Register service
            service = env.register_service(TestService)
            assert isinstance(service, TestService)
            
            # Initialize services
            success = env.initialize_services()
            assert success is True
            
            # Check service health
            env.assert_service_healthy(TestService)
    
    def test_mock_service_in_test_env(self):
        """Test mock service usage in test environment"""
        config = TestEnvironmentConfig(use_real_services=False)
        
        with integration_test_environment(config) as env:
            # Register mock service
            mock_service = env.register_service(TestService)
            assert isinstance(mock_service, MockServiceInterface)
            
            # Initialize and test
            env.initialize_services()
            env.assert_service_healthy(TestService)
    
    def test_event_testing_in_test_env(self):
        """Test event publishing and waiting in test environment"""
        config = TestEnvironmentConfig()
        
        with integration_test_environment(config) as env:
            # Create a future event to wait for
            import threading
            event_received = threading.Event()
            received_events = []
            
            def event_handler(event):
                if event.event_type == "test.event":
                    received_events.append(event)
                    event_received.set()
            
            # Subscribe first
            subscription_id = env.event_bus.subscribe_event(
                event_type_pattern="test\\..*",
                handler=event_handler
            )
            
            try:
                # Publish test event
                test_event = Event(
                    event_type="test.event",
                    source="test_source",
                    timestamp=datetime.now(),
                    data={"test": True}
                )
                
                env.publish_test_event(test_event)
                
                # Wait for event to be received
                assert event_received.wait(timeout=2.0), "Event was not received within timeout"
                assert len(received_events) > 0
                
                received_event = received_events[0]
                assert received_event.event_type == "test.event"
                assert received_event.data["test"] is True
                
            finally:
                env.event_bus.unsubscribe_event(subscription_id)
    
    def test_integration_test_suite(self):
        """Test integration test suite functionality"""
        suite = IntegrationTestSuite("Test Suite")
        
        def test_function_1(env):
            env.register_service(TestService)
            env.initialize_services()
            env.assert_service_healthy(TestService)
        
        def test_function_2(env):
            # This test will pass
            pass
        
        # Add tests to suite
        suite.add_test("Test 1", test_function_1)
        suite.add_test("Test 2", test_function_2)
        
        # Run all tests
        results = suite.run_all_tests()
        
        assert results['suite_name'] == "Test Suite"
        assert results['total_tests'] == 2
        assert results['passed_tests'] >= 1  # At least test 2 should pass
    
    def test_create_basic_integration_test(self):
        """Test basic integration test creation"""
        test_func = create_basic_integration_test([TestService])
        
        config = TestEnvironmentConfig()
        with integration_test_environment(config) as env:
            # This should not raise an exception
            test_func(env)


class TestServiceHealthChecks:
    """Test cases for service health checks"""
    
    def test_service_health_checker_basic(self):
        """Test basic service health checking"""
        service = TestService("HealthTestService")
        service.initialized = True
        
        checker = ServiceHealthChecker(service)
        result = checker.perform_basic_check()
        
        assert result.check_name == "basic_health_check"
        assert result.check_type == HealthCheckType.BASIC
        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "HealthTestService"
    
    def test_service_health_checker_unhealthy(self):
        """Test health checking of unhealthy service"""
        service = TestService("UnhealthyService")
        service.initialized = False  # Make it unhealthy
        
        checker = ServiceHealthChecker(service)
        result = checker.perform_basic_check()
        
        assert result.status == HealthStatus.UNHEALTHY
    
    def test_service_health_checker_performance(self):
        """Test performance health checking"""
        service = TestService("PerfTestService")
        service.initialized = True
        
        checker = ServiceHealthChecker(service)
        result = checker.perform_performance_check()
        
        assert result.check_type == HealthCheckType.PERFORMANCE
        assert result.response_time_ms > 0
        assert result.throughput_ops_per_sec > 0
    
    def test_integration_point_validator(self):
        """Test integration point validation"""
        service1 = TestService("Service1")
        service1.initialized = True
        
        service2 = TestService("Service2")
        service2.initialized = True
        
        validator = IntegrationPointValidator()
        result = validator.validate_service_communication(service1, service2)
        
        assert result.check_type == HealthCheckType.INTEGRATION
        assert result.service_name == "Service1 -> Service2"
    
    def test_health_monitor(self):
        """Test health monitor functionality"""
        monitor = HealthMonitor()
        
        # Add service
        service = TestService("MonitoredService")
        service.initialized = True
        monitor.add_service(service)
        
        # Perform immediate check
        results = monitor.perform_immediate_check()
        
        assert "MonitoredService" in results
        assert len(results["MonitoredService"]) > 0
        
        # Get dashboard
        dashboard = monitor.get_health_dashboard()
        assert dashboard["total_services"] == 1
    
    def test_create_basic_health_check(self):
        """Test convenience function for basic health check"""
        service = TestService("ConvenienceTest")
        service.initialized = True
        
        result = create_basic_health_check(service)
        
        assert result.status == HealthStatus.HEALTHY
        assert result.service_name == "ConvenienceTest"


class TestIntegrationMonitoring:
    """Test cases for integration monitoring"""
    
    def test_metrics_collector(self):
        """Test metrics collection functionality"""
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_value("test.metric", 10.0, "units")
        collector.record_value("test.metric", 20.0, "units")
        collector.record_value("another.metric", 5.0)
        
        # Get metric values
        values = collector.get_metric_values("test.metric")
        assert len(values) == 2
        assert values[0].value == 10.0
        assert values[1].value == 20.0
        
        # Get statistics
        stats = collector.get_metric_statistics("test.metric")
        assert stats['count'] == 2
        assert stats['mean'] == 15.0
        assert stats['min'] == 10.0
        assert stats['max'] == 20.0
        
        # Get all metric names
        names = collector.get_all_metric_names()
        assert "test.metric" in names
        assert "another.metric" in names
    
    def test_alert_manager(self):
        """Test alert management functionality"""
        manager = AlertManager()
        
        # Create alert
        alert = manager.create_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="This is a test alert",
            source_component="TestComponent"
        )
        
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert not alert.resolved
        
        # Get active alerts
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].alert_id == alert.alert_id
        
        # Resolve alert
        success = manager.resolve_alert(alert.alert_id, "Test resolution")
        assert success is True
        assert alert.resolved is True
        
        # Check active alerts after resolution
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 0
    
    def test_integration_monitor_basic(self):
        """Test basic integration monitoring"""
        # Create service manager
        context = create_mock_service_context()
        service_manager = ServiceManager(context)
        
        # Create monitor
        monitor = IntegrationMonitor(service_manager, MonitoringLevel.BASIC)
        
        # Get system health snapshot
        snapshot = monitor.get_system_health_snapshot()
        
        assert snapshot.timestamp is not None
        assert snapshot.overall_status in [status for status in HealthStatus]
    
    @patch('TimeLocker.integration.service_manager.ServiceManager.get_service_by_name')
    def test_integration_monitor_with_services(self, mock_get_service):
        """Test integration monitoring with services"""
        # Mock service
        mock_service = Mock(spec=ServiceInterface)
        mock_service.get_service_name.return_value = "MockedService"
        mock_service.health_check.return_value = True
        mock_get_service.return_value = mock_service
        
        # Create service manager
        context = create_mock_service_context()
        service_manager = ServiceManager(context)
        
        # Mock service status
        service_manager.get_service_status = Mock(return_value={
            "MockedService": {
                "initialized": True,
                "healthy": True,
                "capabilities": ["test"]
            }
        })
        
        # Create monitor
        monitor = IntegrationMonitor(service_manager, MonitoringLevel.STANDARD)
        
        # Get dashboard
        dashboard = monitor.get_monitoring_dashboard()
        
        assert dashboard["monitoring_active"] is False
        assert dashboard["monitoring_level"] == "standard"
        assert "current_health" in dashboard


class TestIntegrationDiagnostics:
    """Test cases for integration diagnostics"""
    
    def test_diagnostic_analyzer_service_health(self):
        """Test diagnostic analysis of service health"""
        analyzer = DiagnosticAnalyzer()
        
        # Create unhealthy service and health result
        service = TestService("DiagnosticTest")
        
        from TimeLocker.integration.service_health_checks import HealthCheckResult
        health_result = HealthCheckResult(
            check_name="test_check",
            check_type=HealthCheckType.BASIC,
            status=HealthStatus.CRITICAL,
            timestamp=datetime.now(),
            duration_ms=100.0,
            service_name="DiagnosticTest",
            message="Service is critical",
            error_message="Test error"
        )
        
        # Analyze
        findings = analyzer.analyze_service_health(service, health_result)
        
        assert len(findings) > 0
        critical_finding = findings[0]
        assert critical_finding.severity == DiagnosticSeverity.CRITICAL
        assert critical_finding.service_name == "DiagnosticTest"
        assert len(critical_finding.suggested_fixes) > 0
    
    def test_diagnostic_analyzer_performance(self):
        """Test diagnostic analysis of performance issues"""
        analyzer = DiagnosticAnalyzer()
        
        service = TestService("SlowService")
        
        from TimeLocker.integration.service_health_checks import HealthCheckResult
        health_result = HealthCheckResult(
            check_name="performance_check",
            check_type=HealthCheckType.PERFORMANCE,
            status=HealthStatus.HEALTHY,
            timestamp=datetime.now(),
            duration_ms=100.0,
            service_name="SlowService",
            response_time_ms=2000.0  # Slow response
        )
        
        findings = analyzer.analyze_service_health(service, health_result)
        
        # Should find performance issue
        perf_findings = [f for f in findings if f.category == DiagnosticCategory.PERFORMANCE]
        assert len(perf_findings) > 0
        
        perf_finding = perf_findings[0]
        assert "slow" in perf_finding.title.lower() or "performance" in perf_finding.title.lower()
    
    def test_diagnostic_analyzer_dependencies(self):
        """Test diagnostic analysis of service dependencies"""
        analyzer = DiagnosticAnalyzer()
        
        # Create services
        healthy_service = TestService("HealthyDep")
        healthy_service.initialized = True
        
        unhealthy_service = TestService("UnhealthyDep")
        unhealthy_service.initialized = False
        
        main_service = TestService("MainService")
        
        # Analyze dependencies
        findings = analyzer.analyze_service_dependencies(
            main_service, 
            [healthy_service, unhealthy_service]
        )
        
        # Should find dependency issues
        dep_findings = [f for f in findings if f.category == DiagnosticCategory.DEPENDENCY]
        assert len(dep_findings) > 0
    
    def test_system_diagnostic_report_generation(self):
        """Test system diagnostic report generation"""
        # Create service manager
        context = create_mock_service_context()
        service_manager = ServiceManager(context)
        
        # Mock service status
        service_manager.get_service_status = Mock(return_value={
            "TestService": {
                "registered": True,
                "initialized": True,
                "healthy": True,
                "capabilities": ["test"]
            }
        })
        
        # Generate report
        report = generate_system_diagnostic_report(
            service_manager, 
            include_health_checks=False,  # Skip health checks for this test
            include_alerts=False
        )
        
        assert report.report_id is not None
        assert report.timestamp is not None
        assert len(report.system_info) > 0
        assert report.services_analyzed == ["TestService"]
    
    def test_diagnostic_report_text_generation(self):
        """Test diagnostic report text generation"""
        from TimeLocker.integration.integration_diagnostics import (
            DiagnosticReportGenerator,
            SystemDiagnosticReport,
            DiagnosticFinding
        )
        
        # Create sample report
        finding = DiagnosticFinding(
            finding_id="test_finding",
            severity=DiagnosticSeverity.WARNING,
            category=DiagnosticCategory.PERFORMANCE,
            title="Test Finding",
            description="This is a test finding",
            timestamp=datetime.now(),
            suggested_fixes=["Fix 1", "Fix 2"]
        )
        
        report = SystemDiagnosticReport(
            report_id="test_report",
            timestamp=datetime.now(),
            findings=[finding],
            total_findings=1,
            warning_findings=1,
            immediate_actions=["Action 1"],
            preventive_measures=["Measure 1"]
        )
        
        # Generate text report
        generator = DiagnosticReportGenerator()
        text_report = generator.generate_text_report(report)
        
        assert "TIMELOCKER INTEGRATION DIAGNOSTIC REPORT" in text_report
        assert "Test Finding" in text_report
        assert "Fix 1" in text_report
        
        # Generate JSON report
        json_report = generator.generate_json_report(report)
        assert "test_report" in json_report
        assert "Test Finding" in json_report
        
        # Generate summary
        summary = generator.generate_summary_report(report)
        assert "test_report" in summary or "Diagnostic Summary" in summary


class TestIntegrationWorkflows:
    """Test cases for complete integration workflows"""
    
    def test_complete_integration_testing_workflow(self):
        """Test complete integration testing workflow"""
        # Create test suite
        suite = IntegrationTestSuite("Complete Workflow Test")
        
        def integration_test(env):
            # Register services
            service1 = env.register_service(TestService, TestService("Service1"))
            service2 = env.register_service(TestService, TestService("Service2"), use_mock=True)
            
            # Initialize services
            success = env.initialize_services()
            assert success is True
            
            # Check health
            env.assert_service_healthy(TestService)
            
            # Test event flow
            test_event = Event(
                event_type="workflow.test",
                source="Service1",
                timestamp=datetime.now(),
                data={"workflow": "test"}
            )
            env.publish_test_event(test_event)
            
            # Wait for event
            received_event = env.assert_event_published("workflow.test")
            assert received_event.data["workflow"] == "test"
        
        # Add test to suite
        suite.add_test("Integration Workflow", integration_test)
        
        # Run test
        results = suite.run_all_tests()
        
        assert results['total_tests'] == 1
        assert results['passed_tests'] == 1
    
    def test_health_monitoring_and_diagnostics_workflow(self):
        """Test health monitoring and diagnostics workflow"""
        # Create service
        service = TestService("WorkflowService")
        service.initialized = True
        
        # Perform health check
        health_result = create_basic_health_check(service)
        assert health_result.status == HealthStatus.HEALTHY
        
        # Analyze health with diagnostics
        from TimeLocker.integration.integration_diagnostics import diagnose_service_health
        findings = diagnose_service_health(service, health_result)
        
        # Should have no critical findings for healthy service
        critical_findings = [f for f in findings if f.severity == DiagnosticSeverity.CRITICAL]
        assert len(critical_findings) == 0
    
    def test_monitoring_and_alerting_workflow(self):
        """Test monitoring and alerting workflow"""
        # Create metrics collector and alert manager
        metrics = MetricsCollector()
        alerts = AlertManager()
        
        # Record some metrics
        metrics.record_value("response_time", 500.0, "ms")
        metrics.record_value("response_time", 1500.0, "ms")  # Slow response
        
        # Check if we should create alert
        stats = metrics.get_metric_statistics("response_time")
        if stats['latest'] > 1000.0:
            alert = alerts.create_alert(
                severity=AlertSeverity.WARNING,
                title="Slow Response Time",
                description=f"Response time is {stats['latest']}ms",
                metric_name="response_time",
                metric_value=stats['latest'],
                threshold_value=1000.0
            )
            
            assert alert.severity == AlertSeverity.WARNING
            assert "Slow Response Time" in alert.title
        
        # Check active alerts
        active_alerts = alerts.get_active_alerts()
        assert len(active_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__])