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
Integration Testing Support

This module provides integration testing support with real service implementations
and controlled test environments, supporting requirement 9.2 of the integration architecture.
"""

import logging
import tempfile
import shutil
from typing import Dict, Any, Type, TypeVar, Optional, List, Callable, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
import threading
import time

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import (
    ServiceIntegrationError,
    IntegrationTestError
)
from .service_manager import ServiceManager
from .service_mocking import MockingContext, MockServiceInterface
from .event_bus import EventBus

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


@dataclass
class TestEnvironmentConfig:
    """
    Configuration for integration test environment.
    
    This class defines the configuration for setting up controlled
    test environments for integration testing.
    """
    
    # Test environment name
    name: str = "default_test_env"
    
    # Temporary directory for test data
    temp_dir: Optional[Path] = None
    
    # Whether to use real services or mocks
    use_real_services: bool = True
    
    # Services to mock (even when use_real_services is True)
    mock_services: Set[Type[ServiceInterface]] = field(default_factory=set)
    
    # Services to exclude from testing
    exclude_services: Set[Type[ServiceInterface]] = field(default_factory=set)
    
    # Test timeout in seconds
    timeout_seconds: float = 30.0
    
    # Whether to cleanup after test
    cleanup_after_test: bool = True
    
    # Event bus persistence for testing
    persist_events: bool = True
    
    # Performance monitoring during tests
    monitor_performance: bool = True
    
    # Security integration during tests
    enable_security: bool = False


@dataclass
class IntegrationTestResult:
    """
    Result of an integration test execution.
    
    This class contains the results and metrics from running
    integration tests.
    """
    
    test_name: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Service results
    services_tested: List[str] = field(default_factory=list)
    services_passed: List[str] = field(default_factory=list)
    services_failed: List[str] = field(default_factory=list)
    
    # Error information
    errors: List[str] = field(default_factory=list)
    exceptions: List[Exception] = field(default_factory=list)
    
    # Performance metrics
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Event information
    events_published: int = 0
    events_processed: int = 0
    
    # Test artifacts
    log_files: List[Path] = field(default_factory=list)
    data_files: List[Path] = field(default_factory=list)


class IntegrationTestEnvironment:
    """
    Controlled environment for integration testing.
    
    This class provides a controlled environment for running integration
    tests with real service implementations and proper isolation.
    """
    
    def __init__(self, config: TestEnvironmentConfig):
        """
        Initialize integration test environment.
        
        Args:
            config: Test environment configuration
        """
        self.config = config
        self.temp_dir: Optional[Path] = None
        self.service_manager: Optional[ServiceManager] = None
        self.event_bus: Optional[EventBus] = None
        self.mocking_context: Optional[MockingContext] = None
        
        # Test tracking
        self.test_results: List[IntegrationTestResult] = []
        self.current_test: Optional[IntegrationTestResult] = None
        
        # Performance monitoring
        self.performance_data: Dict[str, List[float]] = {}
        
        logger.info(f"Created integration test environment: {config.name}")
    
    def setup(self) -> None:
        """
        Setup the test environment.
        
        This method initializes the temporary directory, service manager,
        and other components needed for integration testing.
        
        Raises:
            IntegrationTestError: If setup fails
        """
        try:
            # Create temporary directory
            if self.config.temp_dir is None:
                self.temp_dir = Path(tempfile.mkdtemp(prefix=f"timelocker_test_{self.config.name}_"))
            else:
                self.temp_dir = self.config.temp_dir
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Test environment directory: {self.temp_dir}")
            
            # Setup event bus
            event_persistence_path = None
            if self.config.persist_events:
                event_persistence_path = self.temp_dir / "events"
            
            self.event_bus = EventBus(persistence_path=event_persistence_path)
            
            # Create service context
            from ..config import ConfigurationModule
            config_manager = ConfigurationModule(self.temp_dir / "config")
            
            # Create a temporary service registry for the context
            from .service_manager import ServiceRegistry
            temp_registry = ServiceRegistry()
            
            service_context = ServiceContext(
                config_manager=config_manager,
                event_bus=self.event_bus,
                service_registry=temp_registry
            )
            
            # Initialize service manager
            self.service_manager = ServiceManager(service_context, self.event_bus)
            
            # Update the service context to use the service manager's registry
            service_context.service_registry = self.service_manager._registry
            
            # Setup mocking context
            self.mocking_context = MockingContext(self.service_manager)
            
            logger.info("Integration test environment setup complete")
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            raise IntegrationTestError(f"Environment setup failed: {e}") from e
    
    def teardown(self) -> None:
        """
        Teardown the test environment.
        
        This method cleans up resources and removes temporary files
        if configured to do so.
        """
        try:
            # Shutdown service manager
            if self.service_manager is not None:
                try:
                    self.service_manager.shutdown_services()
                except Exception as e:
                    logger.warning(f"Error shutting down services: {e}")
            
            # Shutdown event bus
            if self.event_bus is not None:
                try:
                    self.event_bus.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down event bus: {e}")
            
            # Cleanup temporary directory
            if self.config.cleanup_after_test and self.temp_dir is not None:
                try:
                    shutil.rmtree(self.temp_dir)
                    logger.info(f"Cleaned up test directory: {self.temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup test directory: {e}")
            
            logger.info("Integration test environment teardown complete")
            
        except Exception as e:
            logger.error(f"Error during test environment teardown: {e}")
    
    def register_service(self, 
                        service_type: Type[T], 
                        service_instance: T = None,
                        dependencies: List[Type[ServiceInterface]] = None,
                        use_mock: bool = None) -> T:
        """
        Register a service for testing.
        
        Args:
            service_type: Type of service to register
            service_instance: Service instance (creates one if None)
            dependencies: Service dependencies
            use_mock: Whether to use mock (overrides config)
            
        Returns:
            Registered service instance
            
        Raises:
            IntegrationTestError: If registration fails
        """
        if self.service_manager is None:
            raise IntegrationTestError("Test environment not setup")
        
        # Determine if we should use mock
        should_mock = (
            use_mock if use_mock is not None 
            else (not self.config.use_real_services or service_type in self.config.mock_services)
        )
        
        try:
            if should_mock:
                # Use mock service
                from .service_mocking import ServiceMockFactory
                mock_service = ServiceMockFactory.create_basic_mock(service_type)
                self.mocking_context.mock_service(service_type, mock_service)
                return mock_service
            else:
                # Use real service
                if service_instance is None:
                    # Try to create instance (this may fail for some services)
                    try:
                        service_instance = service_type()
                    except Exception as e:
                        logger.warning(f"Could not create {service_type.__name__} instance: {e}")
                        # Fall back to mock
                        from .service_mocking import ServiceMockFactory
                        mock_service = ServiceMockFactory.create_basic_mock(service_type)
                        self.mocking_context.mock_service(service_type, mock_service)
                        return mock_service
                
                self.service_manager.register_service(service_type, service_instance, dependencies)
                return service_instance
                
        except Exception as e:
            logger.error(f"Failed to register service {service_type.__name__}: {e}")
            raise IntegrationTestError(f"Service registration failed: {e}") from e
    
    def initialize_services(self) -> bool:
        """
        Initialize all registered services.
        
        Returns:
            True if all services initialized successfully
            
        Raises:
            IntegrationTestError: If initialization fails
        """
        if self.service_manager is None:
            raise IntegrationTestError("Test environment not setup")
        
        try:
            return self.service_manager.initialize_services()
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise IntegrationTestError(f"Service initialization failed: {e}") from e
    
    def run_test(self, 
                test_name: str, 
                test_function: Callable[['IntegrationTestEnvironment'], None],
                timeout_seconds: float = None) -> IntegrationTestResult:
        """
        Run an integration test in this environment.
        
        Args:
            test_name: Name of the test
            test_function: Test function to execute
            timeout_seconds: Test timeout (uses config default if None)
            
        Returns:
            Test result
        """
        timeout = timeout_seconds or self.config.timeout_seconds
        start_time = datetime.now()
        
        # Create test result
        result = IntegrationTestResult(
            test_name=test_name,
            success=False,
            start_time=start_time,
            end_time=start_time,  # Will be updated
            duration_seconds=0.0
        )
        
        self.current_test = result
        
        try:
            # Run test with timeout
            test_thread = threading.Thread(target=test_function, args=(self,))
            test_thread.daemon = True
            test_thread.start()
            test_thread.join(timeout)
            
            if test_thread.is_alive():
                # Test timed out
                result.errors.append(f"Test timed out after {timeout} seconds")
                logger.error(f"Test {test_name} timed out")
            else:
                # Test completed
                result.success = True
                logger.info(f"Test {test_name} completed successfully")
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.exceptions.append(e)
            logger.error(f"Test {test_name} failed: {e}")
        
        finally:
            # Update result timing
            end_time = datetime.now()
            result.end_time = end_time
            result.duration_seconds = (end_time - start_time).total_seconds()
            
            # Collect performance metrics
            if self.config.monitor_performance:
                result.performance_metrics = self._collect_performance_metrics()
            
            # Collect event statistics
            if self.event_bus is not None:
                stats = self.event_bus.get_statistics()
                result.events_published = stats.get('events_published', 0)
                result.events_processed = stats.get('events_processed', 0)
            
            # Collect service status
            if self.service_manager is not None:
                service_status = self.service_manager.get_service_status()
                for service_name, status in service_status.items():
                    result.services_tested.append(service_name)
                    if status.get('healthy', False):
                        result.services_passed.append(service_name)
                    else:
                        result.services_failed.append(service_name)
            
            self.test_results.append(result)
            self.current_test = None
        
        return result
    
    def get_service(self, service_type: Type[T]) -> T:
        """
        Get a service instance for testing.
        
        Args:
            service_type: Type of service to get
            
        Returns:
            Service instance
            
        Raises:
            IntegrationTestError: If service not available
        """
        if self.service_manager is None:
            raise IntegrationTestError("Test environment not setup")
        
        try:
            return self.service_manager.get_service(service_type)
        except Exception as e:
            raise IntegrationTestError(f"Service not available: {e}") from e
    
    def publish_test_event(self, event: Event) -> None:
        """
        Publish an event for testing.
        
        Args:
            event: Event to publish
        """
        if self.event_bus is not None:
            self.event_bus.publish_event(event)
    
    def wait_for_events(self, 
                       event_count: int, 
                       timeout_seconds: float = 5.0,
                       event_type_pattern: str = None) -> List[Event]:
        """
        Wait for a specific number of events to be processed.
        
        Args:
            event_count: Number of events to wait for
            timeout_seconds: Maximum time to wait
            event_type_pattern: Optional pattern to filter events
            
        Returns:
            List of events that were processed
            
        Raises:
            IntegrationTestError: If timeout occurs
        """
        if self.event_bus is None:
            raise IntegrationTestError("Event bus not available")
        
        collected_events = []
        start_time = time.time()
        
        def event_collector(event: Event):
            if event_type_pattern is None or event.event_type.startswith(event_type_pattern):
                collected_events.append(event)
        
        # Subscribe to events first
        subscription_id = self.event_bus.subscribe_event(
            event_type_pattern=event_type_pattern or ".*",
            handler=event_collector
        )
        
        try:
            # Wait for events
            while len(collected_events) < event_count:
                if time.time() - start_time > timeout_seconds:
                    raise IntegrationTestError(
                        f"Timeout waiting for {event_count} events "
                        f"(got {len(collected_events)} in {timeout_seconds}s)"
                    )
                time.sleep(0.1)
            
            return collected_events[:event_count]
            
        finally:
            # Cleanup subscription
            self.event_bus.unsubscribe_event(subscription_id)
    
    def assert_service_healthy(self, service_type: Type[ServiceInterface]) -> None:
        """
        Assert that a service is healthy.
        
        Args:
            service_type: Type of service to check
            
        Raises:
            IntegrationTestError: If service is not healthy
        """
        if self.service_manager is None:
            raise IntegrationTestError("Test environment not setup")
        
        health_status = self.service_manager.health_check()
        service_name = service_type.__name__
        
        if service_name not in health_status:
            raise IntegrationTestError(f"Service {service_name} not found in health check")
        
        if not health_status[service_name]:
            raise IntegrationTestError(f"Service {service_name} is not healthy")
    
    def assert_event_published(self, 
                              event_type: str, 
                              timeout_seconds: float = 5.0) -> Event:
        """
        Assert that an event of a specific type was published.
        
        Args:
            event_type: Type of event to wait for
            timeout_seconds: Maximum time to wait
            
        Returns:
            The published event
            
        Raises:
            IntegrationTestError: If event is not published within timeout
        """
        events = self.wait_for_events(1, timeout_seconds, event_type)
        if not events:
            raise IntegrationTestError(f"Event {event_type} was not published within {timeout_seconds}s")
        return events[0]
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """
        Collect performance metrics from services.
        
        Returns:
            Dictionary of performance metrics
        """
        metrics = {}
        
        if self.service_manager is not None:
            try:
                # Get optimization statistics if available
                if hasattr(self.service_manager, 'get_optimization_statistics'):
                    metrics['optimization'] = self.service_manager.get_optimization_statistics()
                
                # Get error statistics if available
                if hasattr(self.service_manager, 'get_error_statistics'):
                    metrics['errors'] = self.service_manager.get_error_statistics()
                
            except Exception as e:
                logger.warning(f"Failed to collect performance metrics: {e}")
        
        return metrics
    
    def get_test_summary(self) -> Dict[str, Any]:
        """
        Get summary of all tests run in this environment.
        
        Returns:
            Dictionary with test summary information
        """
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(result.duration_seconds for result in self.test_results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0.0
        
        return {
            'environment_name': self.config.name,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0.0,
            'total_duration_seconds': total_duration,
            'average_duration_seconds': avg_duration,
            'test_results': [
                {
                    'name': result.test_name,
                    'success': result.success,
                    'duration_seconds': result.duration_seconds,
                    'services_tested': len(result.services_tested),
                    'errors': len(result.errors)
                }
                for result in self.test_results
            ]
        }


@contextmanager
def integration_test_environment(config: TestEnvironmentConfig = None):
    """
    Context manager for integration test environment.
    
    Args:
        config: Test environment configuration
        
    Yields:
        IntegrationTestEnvironment instance
    """
    if config is None:
        config = TestEnvironmentConfig()
    
    env = IntegrationTestEnvironment(config)
    
    try:
        env.setup()
        yield env
    finally:
        env.teardown()


class IntegrationTestSuite:
    """
    Suite for running multiple integration tests.
    
    This class provides a framework for organizing and running
    multiple integration tests with different configurations.
    """
    
    def __init__(self, name: str = "Integration Test Suite"):
        """
        Initialize test suite.
        
        Args:
            name: Name of the test suite
        """
        self.name = name
        self.tests: List[tuple] = []  # (test_name, test_function, config)
        self.results: List[IntegrationTestResult] = []
    
    def add_test(self, 
                test_name: str, 
                test_function: Callable[[IntegrationTestEnvironment], None],
                config: TestEnvironmentConfig = None) -> None:
        """
        Add a test to the suite.
        
        Args:
            test_name: Name of the test
            test_function: Test function to execute
            config: Test environment configuration
        """
        if config is None:
            config = TestEnvironmentConfig(name=f"{test_name}_env")
        
        self.tests.append((test_name, test_function, config))
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all tests in the suite.
        
        Returns:
            Summary of all test results
        """
        logger.info(f"Running integration test suite: {self.name}")
        
        self.results.clear()
        
        for test_name, test_function, config in self.tests:
            logger.info(f"Running test: {test_name}")
            
            with integration_test_environment(config) as env:
                result = env.run_test(test_name, test_function)
                self.results.append(result)
                
                if result.success:
                    logger.info(f"✓ Test {test_name} passed ({result.duration_seconds:.2f}s)")
                else:
                    logger.error(f"✗ Test {test_name} failed ({result.duration_seconds:.2f}s)")
                    for error in result.errors:
                        logger.error(f"  Error: {error}")
        
        return self.get_suite_summary()
    
    def get_suite_summary(self) -> Dict[str, Any]:
        """
        Get summary of test suite results.
        
        Returns:
            Dictionary with suite summary information
        """
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(result.duration_seconds for result in self.results)
        
        return {
            'suite_name': self.name,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0.0,
            'total_duration_seconds': total_duration,
            'results': [
                {
                    'test_name': result.test_name,
                    'success': result.success,
                    'duration_seconds': result.duration_seconds,
                    'services_tested': result.services_tested,
                    'services_passed': result.services_passed,
                    'services_failed': result.services_failed,
                    'errors': result.errors,
                    'performance_metrics': result.performance_metrics
                }
                for result in self.results
            ]
        }


# Convenience functions for common integration testing scenarios

def create_basic_integration_test(services_to_test: List[Type[ServiceInterface]]) -> Callable:
    """
    Create a basic integration test that initializes and health checks services.
    
    Args:
        services_to_test: List of service types to test
        
    Returns:
        Test function that can be used with IntegrationTestEnvironment
    """
    def test_function(env: IntegrationTestEnvironment):
        # Register services
        for service_type in services_to_test:
            env.register_service(service_type)
        
        # Initialize services
        success = env.initialize_services()
        if not success:
            raise IntegrationTestError("Failed to initialize services")
        
        # Check health of all services
        for service_type in services_to_test:
            env.assert_service_healthy(service_type)
    
    return test_function


def create_event_flow_test(publisher_service: Type[ServiceInterface],
                          subscriber_service: Type[ServiceInterface],
                          event_type: str) -> Callable:
    """
    Create an integration test that verifies event flow between services.
    
    Args:
        publisher_service: Service type that publishes events
        subscriber_service: Service type that subscribes to events
        event_type: Type of event to test
        
    Returns:
        Test function that can be used with IntegrationTestEnvironment
    """
    def test_function(env: IntegrationTestEnvironment):
        # Register and initialize services
        env.register_service(publisher_service)
        env.register_service(subscriber_service)
        env.initialize_services()
        
        # Publish test event
        test_event = Event(
            event_type=event_type,
            source=publisher_service.__name__,
            timestamp=datetime.now(),
            data={'test': True}
        )
        env.publish_test_event(test_event)
        
        # Wait for event to be processed
        env.assert_event_published(event_type, timeout_seconds=5.0)
    
    return test_function