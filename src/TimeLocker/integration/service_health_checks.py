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
Service Health Checks for Integration Points

This module implements service health checks for validating integration points
during testing and production, supporting requirement 9.3 of the integration architecture.
"""

import logging
import time
from typing import Dict, Any, Type, TypeVar, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import (
    ServiceHealthCheckError,
    IntegrationPointValidationError
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


class HealthStatus(Enum):
    """Health status levels for services and integration points."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CRITICAL = "critical"


class HealthCheckType(Enum):
    """Types of health checks that can be performed."""
    
    BASIC = "basic"                    # Basic service health check
    CONNECTIVITY = "connectivity"      # Check service connectivity
    DEPENDENCY = "dependency"          # Check service dependencies
    PERFORMANCE = "performance"        # Check service performance
    INTEGRATION = "integration"        # Check integration points
    END_TO_END = "end_to_end"         # End-to-end workflow check


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation.
    
    This class contains the results and metrics from performing
    health checks on services and integration points.
    """
    
    check_name: str
    check_type: HealthCheckType
    status: HealthStatus
    timestamp: datetime
    duration_ms: float
    
    # Service information
    service_name: str = ""
    service_type: str = ""
    
    # Check details
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error: Optional[Exception] = None
    error_message: str = ""
    
    # Performance metrics
    response_time_ms: float = 0.0
    throughput_ops_per_sec: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)


@dataclass
class HealthCheckConfig:
    """
    Configuration for health check operations.
    
    This class defines how health checks should be performed,
    including timeouts, intervals, and thresholds.
    """
    
    # Check intervals
    check_interval_seconds: float = 30.0
    
    # Timeouts
    timeout_seconds: float = 5.0
    
    # Performance thresholds
    max_response_time_ms: float = 1000.0
    min_throughput_ops_per_sec: float = 1.0
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Failure thresholds
    consecutive_failures_threshold: int = 3
    failure_rate_threshold: float = 0.2  # 20%
    
    # Resource usage thresholds
    max_cpu_usage_percent: float = 80.0
    max_memory_usage_percent: float = 80.0
    
    # Whether to perform deep checks
    deep_checks_enabled: bool = True
    
    # Whether to check dependencies
    check_dependencies: bool = True


class ServiceHealthChecker:
    """
    Health checker for individual services.
    
    This class provides comprehensive health checking capabilities
    for individual services including basic health, connectivity,
    performance, and dependency checks.
    """
    
    def __init__(self, service: ServiceInterface, config: HealthCheckConfig = None):
        """
        Initialize service health checker.
        
        Args:
            service: Service to monitor
            config: Health check configuration
        """
        self.service = service
        self.config = config or HealthCheckConfig()
        
        # Health tracking
        self.last_check_time: Optional[datetime] = None
        self.last_status = HealthStatus.UNKNOWN
        self.consecutive_failures = 0
        self.failure_history: List[datetime] = []
        
        # Performance tracking
        self.response_times: List[float] = []
        self.throughput_measurements: List[float] = []
        
        logger.debug(f"Created health checker for {service.get_service_name()}")
    
    def perform_basic_check(self) -> HealthCheckResult:
        """
        Perform basic health check on the service.
        
        Returns:
            Health check result
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Call service health check method
            is_healthy = self.service.health_check()
            
            duration_ms = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
            
            result = HealthCheckResult(
                check_name="basic_health_check",
                check_type=HealthCheckType.BASIC,
                status=status,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Basic health check completed",
                response_time_ms=duration_ms
            )
            
            # Update tracking
            self._update_health_tracking(result)
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="basic_health_check",
                check_type=HealthCheckType.BASIC,
                status=HealthStatus.CRITICAL,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Health check failed with exception",
                error=e,
                error_message=str(e),
                response_time_ms=duration_ms
            )
            
            self._update_health_tracking(result)
            
            return result
    
    def perform_connectivity_check(self) -> HealthCheckResult:
        """
        Perform connectivity check to verify service is reachable.
        
        Returns:
            Health check result
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Try to get service capabilities (lightweight operation)
            capabilities = self.service.get_capabilities()
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="connectivity_check",
                check_type=HealthCheckType.CONNECTIVITY,
                status=HealthStatus.HEALTHY,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Service is reachable",
                details={"capabilities": capabilities},
                response_time_ms=duration_ms
            )
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="connectivity_check",
                check_type=HealthCheckType.CONNECTIVITY,
                status=HealthStatus.CRITICAL,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Service is not reachable",
                error=e,
                error_message=str(e),
                response_time_ms=duration_ms
            )
            
            return result
    
    def perform_performance_check(self) -> HealthCheckResult:
        """
        Perform performance check to measure service responsiveness.
        
        Returns:
            Health check result
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Perform multiple quick operations to measure performance
            operation_times = []
            
            for _ in range(5):
                op_start = time.time()
                self.service.health_check()
                op_time = (time.time() - op_start) * 1000
                operation_times.append(op_time)
            
            duration_ms = (time.time() - start_time) * 1000
            avg_response_time = sum(operation_times) / len(operation_times)
            throughput = len(operation_times) / (duration_ms / 1000)
            
            # Determine status based on performance thresholds
            status = HealthStatus.HEALTHY
            recommendations = []
            
            if avg_response_time > self.config.max_response_time_ms:
                status = HealthStatus.DEGRADED
                recommendations.append(f"Response time ({avg_response_time:.1f}ms) exceeds threshold ({self.config.max_response_time_ms}ms)")
            
            if throughput < self.config.min_throughput_ops_per_sec:
                status = HealthStatus.DEGRADED
                recommendations.append(f"Throughput ({throughput:.1f} ops/sec) below threshold ({self.config.min_throughput_ops_per_sec} ops/sec)")
            
            result = HealthCheckResult(
                check_name="performance_check",
                check_type=HealthCheckType.PERFORMANCE,
                status=status,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Performance check completed",
                details={
                    "operation_times_ms": operation_times,
                    "average_response_time_ms": avg_response_time,
                    "operations_performed": len(operation_times)
                },
                response_time_ms=avg_response_time,
                throughput_ops_per_sec=throughput,
                recommendations=recommendations
            )
            
            # Update performance tracking
            self.response_times.extend(operation_times)
            self.throughput_measurements.append(throughput)
            
            # Keep only recent measurements
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
            if len(self.throughput_measurements) > 20:
                self.throughput_measurements = self.throughput_measurements[-20:]
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="performance_check",
                check_type=HealthCheckType.PERFORMANCE,
                status=HealthStatus.CRITICAL,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=self.service.get_service_name(),
                service_type=type(self.service).__name__,
                message="Performance check failed",
                error=e,
                error_message=str(e),
                response_time_ms=duration_ms
            )
            
            return result
    
    def perform_comprehensive_check(self) -> List[HealthCheckResult]:
        """
        Perform comprehensive health check including all check types.
        
        Returns:
            List of health check results
        """
        results = []
        
        # Basic health check
        results.append(self.perform_basic_check())
        
        # Connectivity check
        results.append(self.perform_connectivity_check())
        
        # Performance check (if basic checks pass)
        if results[-1].status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            results.append(self.perform_performance_check())
        
        return results
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get summary of service health status.
        
        Returns:
            Dictionary with health summary information
        """
        return {
            'service_name': self.service.get_service_name(),
            'service_type': type(self.service).__name__,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'last_status': self.last_status.value,
            'consecutive_failures': self.consecutive_failures,
            'failure_rate': self._calculate_failure_rate(),
            'average_response_time_ms': sum(self.response_times) / len(self.response_times) if self.response_times else 0.0,
            'average_throughput_ops_per_sec': sum(self.throughput_measurements) / len(self.throughput_measurements) if self.throughput_measurements else 0.0,
            'total_checks_performed': len(self.failure_history) + max(0, len(self.response_times) - self.consecutive_failures)
        }
    
    def _update_health_tracking(self, result: HealthCheckResult) -> None:
        """
        Update health tracking based on check result.
        
        Args:
            result: Health check result
        """
        self.last_check_time = result.timestamp
        self.last_status = result.status
        
        if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            self.consecutive_failures += 1
            self.failure_history.append(result.timestamp)
        else:
            self.consecutive_failures = 0
        
        # Keep only recent failure history (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.failure_history = [t for t in self.failure_history if t > cutoff_time]
    
    def _calculate_failure_rate(self) -> float:
        """
        Calculate failure rate over recent history.
        
        Returns:
            Failure rate as a percentage (0.0 to 1.0)
        """
        if not self.failure_history:
            return 0.0
        
        # Calculate failure rate over last hour
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_failures = len([t for t in self.failure_history if t > cutoff_time])
        
        # Estimate total checks (assuming regular interval)
        total_checks = max(1, int(3600 / self.config.check_interval_seconds))
        
        return min(1.0, recent_failures / total_checks)


class IntegrationPointValidator:
    """
    Validator for integration points between services.
    
    This class provides validation capabilities for integration points
    to ensure services can communicate and interact properly.
    """
    
    def __init__(self, config: HealthCheckConfig = None):
        """
        Initialize integration point validator.
        
        Args:
            config: Health check configuration
        """
        self.config = config or HealthCheckConfig()
        self.validation_results: List[HealthCheckResult] = []
        
        logger.debug("Created integration point validator")
    
    def validate_service_communication(self, 
                                     source_service: ServiceInterface,
                                     target_service: ServiceInterface) -> HealthCheckResult:
        """
        Validate communication between two services.
        
        Args:
            source_service: Source service
            target_service: Target service
            
        Returns:
            Validation result
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Check that both services are healthy
            source_healthy = source_service.health_check()
            target_healthy = target_service.health_check()
            
            if not source_healthy:
                raise IntegrationPointValidationError(f"Source service {source_service.get_service_name()} is not healthy")
            
            if not target_healthy:
                raise IntegrationPointValidationError(f"Target service {target_service.get_service_name()} is not healthy")
            
            # Check capability compatibility
            source_capabilities = set(source_service.get_capabilities())
            target_capabilities = set(target_service.get_capabilities())
            
            # Look for complementary capabilities (this is a simple heuristic)
            compatible = len(source_capabilities.intersection(target_capabilities)) > 0
            
            duration_ms = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY if compatible else HealthStatus.DEGRADED
            message = "Services can communicate" if compatible else "Services have no compatible capabilities"
            
            result = HealthCheckResult(
                check_name="service_communication",
                check_type=HealthCheckType.INTEGRATION,
                status=status,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=f"{source_service.get_service_name()} -> {target_service.get_service_name()}",
                message=message,
                details={
                    "source_service": source_service.get_service_name(),
                    "target_service": target_service.get_service_name(),
                    "source_capabilities": list(source_capabilities),
                    "target_capabilities": list(target_capabilities),
                    "compatible_capabilities": list(source_capabilities.intersection(target_capabilities))
                },
                response_time_ms=duration_ms
            )
            
            if not compatible:
                result.recommendations.append("Review service capabilities for compatibility")
            
            self.validation_results.append(result)
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="service_communication",
                check_type=HealthCheckType.INTEGRATION,
                status=HealthStatus.CRITICAL,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=f"{source_service.get_service_name()} -> {target_service.get_service_name()}",
                message="Service communication validation failed",
                error=e,
                error_message=str(e),
                response_time_ms=duration_ms
            )
            
            self.validation_results.append(result)
            return result
    
    def validate_dependency_chain(self, services: List[ServiceInterface]) -> List[HealthCheckResult]:
        """
        Validate a chain of service dependencies.
        
        Args:
            services: List of services in dependency order
            
        Returns:
            List of validation results
        """
        results = []
        
        # Validate each service individually
        for service in services:
            checker = ServiceHealthChecker(service, self.config)
            basic_result = checker.perform_basic_check()
            results.append(basic_result)
        
        # Validate communication between adjacent services
        for i in range(len(services) - 1):
            comm_result = self.validate_service_communication(services[i], services[i + 1])
            results.append(comm_result)
        
        return results
    
    def validate_event_flow(self, 
                           publisher_service: ServiceInterface,
                           subscriber_service: ServiceInterface,
                           event_bus) -> HealthCheckResult:
        """
        Validate event flow between services through event bus.
        
        Args:
            publisher_service: Service that publishes events
            subscriber_service: Service that subscribes to events
            event_bus: Event bus for communication
            
        Returns:
            Validation result
        """
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Create test event
            test_event = Event(
                event_type="health_check.test_event",
                source=publisher_service.get_service_name(),
                timestamp=datetime.now(),
                data={"test": True, "validation_id": f"validation_{int(time.time())}"}
            )
            
            # Track if event is received
            event_received = threading.Event()
            received_event = None
            
            def event_handler(event: Event):
                nonlocal received_event
                if event.data.get("validation_id") == test_event.data["validation_id"]:
                    received_event = event
                    event_received.set()
            
            # Subscribe to test events
            subscription_id = event_bus.subscribe_event(
                event_type_pattern="health_check\\..*",
                handler=event_handler
            )
            
            try:
                # Publish test event
                event_bus.publish_event(test_event)
                
                # Wait for event to be received
                if event_received.wait(timeout=self.config.timeout_seconds):
                    duration_ms = (time.time() - start_time) * 1000
                    
                    result = HealthCheckResult(
                        check_name="event_flow_validation",
                        check_type=HealthCheckType.INTEGRATION,
                        status=HealthStatus.HEALTHY,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                        service_name=f"{publisher_service.get_service_name()} -> EventBus -> {subscriber_service.get_service_name()}",
                        message="Event flow validation successful",
                        details={
                            "publisher": publisher_service.get_service_name(),
                            "subscriber": subscriber_service.get_service_name(),
                            "event_type": test_event.event_type,
                            "event_received": received_event is not None
                        },
                        response_time_ms=duration_ms
                    )
                else:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    result = HealthCheckResult(
                        check_name="event_flow_validation",
                        check_type=HealthCheckType.INTEGRATION,
                        status=HealthStatus.UNHEALTHY,
                        timestamp=timestamp,
                        duration_ms=duration_ms,
                        service_name=f"{publisher_service.get_service_name()} -> EventBus -> {subscriber_service.get_service_name()}",
                        message="Event flow validation failed - timeout",
                        details={
                            "publisher": publisher_service.get_service_name(),
                            "subscriber": subscriber_service.get_service_name(),
                            "event_type": test_event.event_type,
                            "timeout_seconds": self.config.timeout_seconds
                        },
                        response_time_ms=duration_ms,
                        recommendations=["Check event bus configuration and subscriber setup"]
                    )
            
            finally:
                # Cleanup subscription
                event_bus.unsubscribe_event(subscription_id)
            
            self.validation_results.append(result)
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                check_name="event_flow_validation",
                check_type=HealthCheckType.INTEGRATION,
                status=HealthStatus.CRITICAL,
                timestamp=timestamp,
                duration_ms=duration_ms,
                service_name=f"{publisher_service.get_service_name()} -> EventBus -> {subscriber_service.get_service_name()}",
                message="Event flow validation failed with exception",
                error=e,
                error_message=str(e),
                response_time_ms=duration_ms
            )
            
            self.validation_results.append(result)
            return result
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get summary of all validation results.
        
        Returns:
            Dictionary with validation summary
        """
        total_validations = len(self.validation_results)
        if total_validations == 0:
            return {"total_validations": 0}
        
        healthy_count = sum(1 for r in self.validation_results if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in self.validation_results if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in self.validation_results if r.status == HealthStatus.UNHEALTHY)
        critical_count = sum(1 for r in self.validation_results if r.status == HealthStatus.CRITICAL)
        
        avg_response_time = sum(r.response_time_ms for r in self.validation_results) / total_validations
        
        return {
            "total_validations": total_validations,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "unhealthy_count": unhealthy_count,
            "critical_count": critical_count,
            "health_rate": healthy_count / total_validations,
            "average_response_time_ms": avg_response_time,
            "validation_results": [
                {
                    "check_name": r.check_name,
                    "status": r.status.value,
                    "service_name": r.service_name,
                    "response_time_ms": r.response_time_ms,
                    "message": r.message
                }
                for r in self.validation_results
            ]
        }


class HealthMonitor:
    """
    Continuous health monitoring for services and integration points.
    
    This class provides continuous monitoring capabilities that run
    health checks at regular intervals and track health trends.
    """
    
    def __init__(self, config: HealthCheckConfig = None):
        """
        Initialize health monitor.
        
        Args:
            config: Health check configuration
        """
        self.config = config or HealthCheckConfig()
        self.service_checkers: Dict[str, ServiceHealthChecker] = {}
        self.integration_validator = IntegrationPointValidator(config)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Results storage
        self.health_history: List[HealthCheckResult] = []
        self.alert_callbacks: List[Callable[[HealthCheckResult], None]] = []
        
        logger.info("Created health monitor")
    
    def add_service(self, service: ServiceInterface) -> None:
        """
        Add a service to monitor.
        
        Args:
            service: Service to monitor
        """
        service_name = service.get_service_name()
        self.service_checkers[service_name] = ServiceHealthChecker(service, self.config)
        logger.info(f"Added service to health monitoring: {service_name}")
    
    def remove_service(self, service_name: str) -> bool:
        """
        Remove a service from monitoring.
        
        Args:
            service_name: Name of service to remove
            
        Returns:
            True if service was removed, False if not found
        """
        if service_name in self.service_checkers:
            del self.service_checkers[service_name]
            logger.info(f"Removed service from health monitoring: {service_name}")
            return True
        return False
    
    def add_alert_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """
        Add callback for health alerts.
        
        Args:
            callback: Function to call when health issues are detected
        """
        self.alert_callbacks.append(callback)
    
    def start_monitoring(self) -> None:
        """
        Start continuous health monitoring.
        """
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Started continuous health monitoring")
    
    def stop_monitoring(self) -> None:
        """
        Stop continuous health monitoring.
        """
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitor_thread is not None:
            self.monitor_thread.join(timeout=5.0)
        
        self.executor.shutdown(wait=True)
        
        logger.info("Stopped continuous health monitoring")
    
    def perform_immediate_check(self) -> Dict[str, List[HealthCheckResult]]:
        """
        Perform immediate health check on all monitored services.
        
        Returns:
            Dictionary mapping service names to health check results
        """
        results = {}
        
        # Submit all health checks concurrently
        futures = {}
        for service_name, checker in self.service_checkers.items():
            future = self.executor.submit(checker.perform_comprehensive_check)
            futures[service_name] = future
        
        # Collect results
        for service_name, future in futures.items():
            try:
                service_results = future.result(timeout=self.config.timeout_seconds)
                results[service_name] = service_results
                
                # Store in history
                self.health_history.extend(service_results)
                
                # Check for alerts
                for result in service_results:
                    self._check_for_alerts(result)
                    
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                
                # Create error result
                error_result = HealthCheckResult(
                    check_name="comprehensive_check",
                    check_type=HealthCheckType.BASIC,
                    status=HealthStatus.CRITICAL,
                    timestamp=datetime.now(),
                    duration_ms=self.config.timeout_seconds * 1000,
                    service_name=service_name,
                    message="Health check execution failed",
                    error=e,
                    error_message=str(e)
                )
                
                results[service_name] = [error_result]
                self.health_history.append(error_result)
                self._check_for_alerts(error_result)
        
        # Cleanup old history
        self._cleanup_history()
        
        return results
    
    def get_health_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive health dashboard data.
        
        Returns:
            Dictionary with health dashboard information
        """
        # Get current status for all services
        current_status = {}
        for service_name, checker in self.service_checkers.items():
            current_status[service_name] = checker.get_health_summary()
        
        # Calculate overall statistics
        total_services = len(self.service_checkers)
        healthy_services = sum(1 for summary in current_status.values() 
                             if summary['last_status'] == HealthStatus.HEALTHY.value)
        
        # Get recent health trends
        recent_results = [r for r in self.health_history 
                         if r.timestamp > datetime.now() - timedelta(hours=1)]
        
        avg_response_time = (sum(r.response_time_ms for r in recent_results) / len(recent_results) 
                           if recent_results else 0.0)
        
        return {
            "monitoring_active": self.monitoring_active,
            "total_services": total_services,
            "healthy_services": healthy_services,
            "health_rate": healthy_services / total_services if total_services > 0 else 0.0,
            "average_response_time_ms": avg_response_time,
            "total_checks_performed": len(self.health_history),
            "recent_checks": len(recent_results),
            "service_status": current_status,
            "integration_validation": self.integration_validator.get_validation_summary()
        }
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop that runs health checks at regular intervals.
        """
        logger.info("Health monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Perform health checks
                self.perform_immediate_check()
                
                # Wait for next interval
                time.sleep(self.config.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(1.0)  # Brief pause before retrying
        
        logger.info("Health monitoring loop stopped")
    
    def _check_for_alerts(self, result: HealthCheckResult) -> None:
        """
        Check if a health check result should trigger alerts.
        
        Args:
            result: Health check result to evaluate
        """
        # Trigger alerts for unhealthy or critical status
        if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            for callback in self.alert_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
        
        # Trigger alerts for performance degradation
        if (result.check_type == HealthCheckType.PERFORMANCE and 
            result.response_time_ms > self.config.max_response_time_ms):
            for callback in self.alert_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    def _cleanup_history(self) -> None:
        """
        Cleanup old health check history to prevent memory growth.
        """
        # Keep only last 24 hours of history
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_history = [r for r in self.health_history if r.timestamp > cutoff_time]
        
        # Keep maximum of 10000 records
        if len(self.health_history) > 10000:
            self.health_history = self.health_history[-10000:]


# Convenience functions for common health checking scenarios

def create_basic_health_check(service: ServiceInterface) -> HealthCheckResult:
    """
    Create and execute a basic health check for a service.
    
    Args:
        service: Service to check
        
    Returns:
        Health check result
    """
    checker = ServiceHealthChecker(service)
    return checker.perform_basic_check()


def validate_service_integration(services: List[ServiceInterface]) -> List[HealthCheckResult]:
    """
    Validate integration between multiple services.
    
    Args:
        services: List of services to validate
        
    Returns:
        List of validation results
    """
    validator = IntegrationPointValidator()
    return validator.validate_dependency_chain(services)


def monitor_services_temporarily(services: List[ServiceInterface], 
                                duration_seconds: float = 60.0) -> Dict[str, Any]:
    """
    Monitor services for a temporary period and return results.
    
    Args:
        services: List of services to monitor
        duration_seconds: How long to monitor
        
    Returns:
        Monitoring results summary
    """
    monitor = HealthMonitor()
    
    # Add services
    for service in services:
        monitor.add_service(service)
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Wait for monitoring period
        time.sleep(duration_seconds)
        
        # Get final dashboard
        return monitor.get_health_dashboard()
        
    finally:
        # Stop monitoring
        monitor.stop_monitoring()