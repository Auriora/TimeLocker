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
Integration Diagnostics and Suggested Fixes

This module provides detailed diagnostic information and suggested fixes when
integration issues are detected, supporting requirement 9.5 of the integration architecture.
"""

import logging
import traceback
from typing import Dict, Any, Type, TypeVar, Optional, List, Callable, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import inspect
import sys
import platform

from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext, Event
from ..interfaces.integration_exceptions import (
    ServiceIntegrationError,
    DiagnosticError
)
from .service_health_checks import HealthCheckResult, HealthStatus
from .integration_monitoring import IntegrationAlert, AlertSeverity

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=ServiceInterface)


class DiagnosticSeverity(Enum):
    """Severity levels for diagnostic issues."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticCategory(Enum):
    """Categories of diagnostic issues."""
    
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance"
    SECURITY = "security"
    RESOURCE = "resource"
    COMPATIBILITY = "compatibility"
    DATA_INTEGRITY = "data_integrity"


@dataclass
class DiagnosticFinding:
    """
    A single diagnostic finding with details and suggested fixes.
    
    This class represents an issue discovered during diagnostic analysis
    along with recommended actions to resolve it.
    """
    
    finding_id: str
    severity: DiagnosticSeverity
    category: DiagnosticCategory
    title: str
    description: str
    timestamp: datetime
    
    # Source information
    component: str = ""
    service_name: str = ""
    
    # Technical details
    technical_details: Dict[str, Any] = field(default_factory=dict)
    error_trace: Optional[str] = None
    
    # Suggested fixes
    suggested_fixes: List[str] = field(default_factory=list)
    fix_commands: List[str] = field(default_factory=list)
    
    # Additional context
    related_findings: List[str] = field(default_factory=list)
    documentation_links: List[str] = field(default_factory=list)
    
    # Resolution tracking
    resolved: bool = False
    resolution_notes: str = ""
    resolved_timestamp: Optional[datetime] = None


@dataclass
class SystemDiagnosticReport:
    """
    Comprehensive diagnostic report for the integration system.
    
    This class contains a complete analysis of system health,
    issues, and recommended actions.
    """
    
    report_id: str
    timestamp: datetime
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    # Findings summary
    total_findings: int = 0
    critical_findings: int = 0
    error_findings: int = 0
    warning_findings: int = 0
    info_findings: int = 0
    
    # Findings by category
    findings: List[DiagnosticFinding] = field(default_factory=list)
    findings_by_category: Dict[DiagnosticCategory, List[DiagnosticFinding]] = field(default_factory=dict)
    
    # Service analysis
    services_analyzed: List[str] = field(default_factory=list)
    healthy_services: List[str] = field(default_factory=list)
    problematic_services: List[str] = field(default_factory=list)
    
    # Integration points analysis
    integration_points_checked: int = 0
    healthy_integration_points: int = 0
    problematic_integration_points: int = 0
    
    # Recommendations
    immediate_actions: List[str] = field(default_factory=list)
    preventive_measures: List[str] = field(default_factory=list)
    
    # Performance analysis
    performance_summary: Dict[str, Any] = field(default_factory=dict)


class DiagnosticAnalyzer:
    """
    Analyzer for detecting and diagnosing integration issues.
    
    This class provides comprehensive analysis capabilities to identify
    problems in service integration and suggest appropriate fixes.
    """
    
    def __init__(self):
        """Initialize diagnostic analyzer."""
        self.diagnostic_rules: List[Callable] = []
        self.findings: List[DiagnosticFinding] = []
        
        # Register built-in diagnostic rules
        self._register_builtin_rules()
        
        logger.debug("Created diagnostic analyzer")
    
    def analyze_service_health(self, 
                             service: ServiceInterface,
                             health_result: HealthCheckResult) -> List[DiagnosticFinding]:
        """
        Analyze service health and identify issues.
        
        Args:
            service: Service to analyze
            health_result: Health check result
            
        Returns:
            List of diagnostic findings
        """
        findings = []
        
        # Analyze health status
        if health_result.status == HealthStatus.CRITICAL:
            finding = DiagnosticFinding(
                finding_id=f"health_critical_{service.get_service_name()}",
                severity=DiagnosticSeverity.CRITICAL,
                category=DiagnosticCategory.DEPENDENCY,
                title=f"Service {service.get_service_name()} is in critical state",
                description=f"Health check failed: {health_result.message}",
                timestamp=datetime.now(),
                component="ServiceHealth",
                service_name=service.get_service_name(),
                technical_details={
                    "health_status": health_result.status.value,
                    "error_message": health_result.error_message,
                    "response_time_ms": health_result.response_time_ms
                }
            )
            
            # Add suggested fixes based on error type
            if health_result.error:
                finding.error_trace = str(health_result.error)
                finding.suggested_fixes.extend(self._suggest_health_fixes(health_result.error))
            else:
                finding.suggested_fixes = [
                    "Check service configuration and dependencies",
                    "Verify service initialization completed successfully",
                    "Review service logs for error details",
                    "Restart the service if configuration is correct"
                ]
            
            findings.append(finding)
        
        elif health_result.status == HealthStatus.UNHEALTHY:
            finding = DiagnosticFinding(
                finding_id=f"health_unhealthy_{service.get_service_name()}",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.DEPENDENCY,
                title=f"Service {service.get_service_name()} is unhealthy",
                description=f"Service health check indicates problems: {health_result.message}",
                timestamp=datetime.now(),
                component="ServiceHealth",
                service_name=service.get_service_name(),
                technical_details={
                    "health_status": health_result.status.value,
                    "response_time_ms": health_result.response_time_ms
                },
                suggested_fixes=[
                    "Check service dependencies are available and healthy",
                    "Verify service configuration is correct",
                    "Check for resource constraints (CPU, memory, disk)",
                    "Review service logs for warnings or errors"
                ]
            )
            findings.append(finding)
        
        # Analyze performance
        if health_result.response_time_ms > 1000:  # More than 1 second
            severity = DiagnosticSeverity.WARNING
            if health_result.response_time_ms > 5000:  # More than 5 seconds
                severity = DiagnosticSeverity.ERROR
            
            finding = DiagnosticFinding(
                finding_id=f"performance_slow_{service.get_service_name()}",
                severity=severity,
                category=DiagnosticCategory.PERFORMANCE,
                title=f"Slow response time for {service.get_service_name()}",
                description=f"Response time ({health_result.response_time_ms:.1f}ms) exceeds acceptable threshold",
                timestamp=datetime.now(),
                component="ServicePerformance",
                service_name=service.get_service_name(),
                technical_details={
                    "response_time_ms": health_result.response_time_ms,
                    "threshold_ms": 1000.0
                },
                suggested_fixes=[
                    "Check system resource usage (CPU, memory, I/O)",
                    "Review service implementation for performance bottlenecks",
                    "Consider connection pooling or caching optimizations",
                    "Monitor for external dependency latency",
                    "Check for database or network connectivity issues"
                ]
            )
            findings.append(finding)
        
        return findings
    
    def analyze_service_dependencies(self, 
                                   service: ServiceInterface,
                                   dependencies: List[ServiceInterface]) -> List[DiagnosticFinding]:
        """
        Analyze service dependencies for issues.
        
        Args:
            service: Service to analyze
            dependencies: List of service dependencies
            
        Returns:
            List of diagnostic findings
        """
        findings = []
        
        # Check if dependencies are healthy
        unhealthy_deps = []
        for dep in dependencies:
            try:
                if not dep.health_check():
                    unhealthy_deps.append(dep.get_service_name())
            except Exception as e:
                unhealthy_deps.append(f"{dep.get_service_name()} (error: {e})")
        
        if unhealthy_deps:
            finding = DiagnosticFinding(
                finding_id=f"dependency_unhealthy_{service.get_service_name()}",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.DEPENDENCY,
                title=f"Unhealthy dependencies for {service.get_service_name()}",
                description=f"Service has {len(unhealthy_deps)} unhealthy dependencies",
                timestamp=datetime.now(),
                component="DependencyAnalysis",
                service_name=service.get_service_name(),
                technical_details={
                    "unhealthy_dependencies": unhealthy_deps,
                    "total_dependencies": len(dependencies)
                },
                suggested_fixes=[
                    "Check the health of dependent services",
                    "Verify dependency initialization order",
                    "Review service configuration for correct dependency references",
                    "Consider implementing graceful degradation for optional dependencies"
                ]
            )
            findings.append(finding)
        
        # Check for circular dependencies (basic check)
        service_name = service.get_service_name()
        for dep in dependencies:
            dep_capabilities = dep.get_capabilities()
            if service_name.lower() in [cap.lower() for cap in dep_capabilities]:
                finding = DiagnosticFinding(
                    finding_id=f"circular_dependency_{service_name}_{dep.get_service_name()}",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.DEPENDENCY,
                    title=f"Potential circular dependency detected",
                    description=f"Service {service_name} may have circular dependency with {dep.get_service_name()}",
                    timestamp=datetime.now(),
                    component="DependencyAnalysis",
                    service_name=service.get_service_name(),
                    technical_details={
                        "service": service_name,
                        "dependency": dep.get_service_name(),
                        "dependency_capabilities": dep_capabilities
                    },
                    suggested_fixes=[
                        "Review service architecture to eliminate circular dependencies",
                        "Consider using event-driven communication instead of direct dependencies",
                        "Implement dependency injection with proper lifecycle management",
                        "Refactor services to have cleaner separation of concerns"
                    ]
                )
                findings.append(finding)
        
        return findings
    
    def analyze_integration_alert(self, alert: IntegrationAlert) -> List[DiagnosticFinding]:
        """
        Analyze an integration alert and provide diagnostic insights.
        
        Args:
            alert: Integration alert to analyze
            
        Returns:
            List of diagnostic findings
        """
        findings = []
        
        # Convert alert to diagnostic finding
        severity_mapping = {
            AlertSeverity.INFO: DiagnosticSeverity.INFO,
            AlertSeverity.WARNING: DiagnosticSeverity.WARNING,
            AlertSeverity.ERROR: DiagnosticSeverity.ERROR,
            AlertSeverity.CRITICAL: DiagnosticSeverity.CRITICAL
        }
        
        # Determine category based on alert content
        category = DiagnosticCategory.PERFORMANCE  # Default
        if "health" in alert.title.lower() or "unhealthy" in alert.title.lower():
            category = DiagnosticCategory.DEPENDENCY
        elif "connectivity" in alert.title.lower() or "connection" in alert.title.lower():
            category = DiagnosticCategory.CONNECTIVITY
        elif "security" in alert.title.lower():
            category = DiagnosticCategory.SECURITY
        elif "resource" in alert.title.lower() or "memory" in alert.title.lower() or "cpu" in alert.title.lower():
            category = DiagnosticCategory.RESOURCE
        
        finding = DiagnosticFinding(
            finding_id=f"alert_analysis_{alert.alert_id}",
            severity=severity_mapping[alert.severity],
            category=category,
            title=f"Alert Analysis: {alert.title}",
            description=f"Analysis of alert: {alert.description}",
            timestamp=datetime.now(),
            component="AlertAnalysis",
            service_name=alert.source_service,
            technical_details={
                "original_alert_id": alert.alert_id,
                "alert_timestamp": alert.timestamp.isoformat(),
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold_value": alert.threshold_value,
                "alert_tags": alert.tags
            }
        )
        
        # Add specific suggested fixes based on alert type
        finding.suggested_fixes = self._suggest_alert_fixes(alert)
        
        findings.append(finding)
        
        return findings
    
    def analyze_system_configuration(self, service_manager) -> List[DiagnosticFinding]:
        """
        Analyze system configuration for potential issues.
        
        Args:
            service_manager: ServiceManager to analyze
            
        Returns:
            List of diagnostic findings
        """
        findings = []
        
        try:
            # Check service registration
            service_status = service_manager.get_service_status()
            
            # Look for services that are registered but not initialized
            uninitialized_services = [
                name for name, status in service_status.items()
                if status.get('registered', False) and not status.get('initialized', False)
            ]
            
            if uninitialized_services:
                finding = DiagnosticFinding(
                    finding_id="config_uninitialized_services",
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.CONFIGURATION,
                    title="Services registered but not initialized",
                    description=f"{len(uninitialized_services)} services are registered but not initialized",
                    timestamp=datetime.now(),
                    component="ConfigurationAnalysis",
                    technical_details={
                        "uninitialized_services": uninitialized_services,
                        "total_services": len(service_status)
                    },
                    suggested_fixes=[
                        "Call initialize_services() on the ServiceManager",
                        "Check for dependency resolution issues preventing initialization",
                        "Review service registration order and dependencies",
                        "Verify service context is properly configured"
                    ]
                )
                findings.append(finding)
            
            # Check for services with no capabilities
            no_capability_services = [
                name for name, status in service_status.items()
                if not status.get('capabilities', [])
            ]
            
            if no_capability_services:
                finding = DiagnosticFinding(
                    finding_id="config_no_capabilities",
                    severity=DiagnosticSeverity.INFO,
                    category=DiagnosticCategory.CONFIGURATION,
                    title="Services with no declared capabilities",
                    description=f"{len(no_capability_services)} services have no declared capabilities",
                    timestamp=datetime.now(),
                    component="ConfigurationAnalysis",
                    technical_details={
                        "services_without_capabilities": no_capability_services
                    },
                    suggested_fixes=[
                        "Review service implementations to ensure capabilities are properly declared",
                        "Update get_capabilities() method to return appropriate capability identifiers",
                        "Consider if these services should declare capabilities for service discovery"
                    ]
                )
                findings.append(finding)
            
        except Exception as e:
            finding = DiagnosticFinding(
                finding_id="config_analysis_error",
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.CONFIGURATION,
                title="Configuration analysis failed",
                description=f"Unable to analyze system configuration: {str(e)}",
                timestamp=datetime.now(),
                component="ConfigurationAnalysis",
                error_trace=traceback.format_exc(),
                suggested_fixes=[
                    "Check ServiceManager is properly initialized",
                    "Verify system is in a stable state for analysis",
                    "Review system logs for underlying issues"
                ]
            )
            findings.append(finding)
        
        return findings
    
    def generate_comprehensive_report(self, 
                                    service_manager,
                                    health_results: List[HealthCheckResult] = None,
                                    alerts: List[IntegrationAlert] = None) -> SystemDiagnosticReport:
        """
        Generate a comprehensive diagnostic report.
        
        Args:
            service_manager: ServiceManager to analyze
            health_results: Optional health check results
            alerts: Optional integration alerts
            
        Returns:
            Comprehensive diagnostic report
        """
        import uuid
        
        report_id = f"diagnostic_report_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now()
        
        # Collect system information
        system_info = self._collect_system_info()
        
        # Initialize report
        report = SystemDiagnosticReport(
            report_id=report_id,
            timestamp=timestamp,
            system_info=system_info
        )
        
        all_findings = []
        
        # Analyze system configuration
        config_findings = self.analyze_system_configuration(service_manager)
        all_findings.extend(config_findings)
        
        # Analyze health results if provided
        if health_results:
            for health_result in health_results:
                try:
                    service = service_manager.get_service_by_name(health_result.service_name)
                    health_findings = self.analyze_service_health(service, health_result)
                    all_findings.extend(health_findings)
                except Exception as e:
                    logger.warning(f"Could not analyze health for {health_result.service_name}: {e}")
        
        # Analyze alerts if provided
        if alerts:
            for alert in alerts:
                alert_findings = self.analyze_integration_alert(alert)
                all_findings.extend(alert_findings)
        
        # Organize findings
        report.findings = all_findings
        report.total_findings = len(all_findings)
        
        # Count by severity
        for finding in all_findings:
            if finding.severity == DiagnosticSeverity.CRITICAL:
                report.critical_findings += 1
            elif finding.severity == DiagnosticSeverity.ERROR:
                report.error_findings += 1
            elif finding.severity == DiagnosticSeverity.WARNING:
                report.warning_findings += 1
            else:
                report.info_findings += 1
        
        # Group by category
        for finding in all_findings:
            if finding.category not in report.findings_by_category:
                report.findings_by_category[finding.category] = []
            report.findings_by_category[finding.category].append(finding)
        
        # Analyze services
        try:
            service_status = service_manager.get_service_status()
            report.services_analyzed = list(service_status.keys())
            
            for service_name, status in service_status.items():
                if status.get('healthy', False):
                    report.healthy_services.append(service_name)
                else:
                    report.problematic_services.append(service_name)
        except Exception as e:
            logger.warning(f"Could not analyze services: {e}")
        
        # Generate recommendations
        report.immediate_actions = self._generate_immediate_actions(all_findings)
        report.preventive_measures = self._generate_preventive_measures(all_findings)
        
        # Performance summary
        report.performance_summary = self._generate_performance_summary(health_results or [])
        
        return report
    
    def _register_builtin_rules(self) -> None:
        """Register built-in diagnostic rules."""
        # This could be expanded with more sophisticated rule-based analysis
        pass
    
    def _suggest_health_fixes(self, error: Exception) -> List[str]:
        """
        Suggest fixes based on health check error.
        
        Args:
            error: Exception from health check
            
        Returns:
            List of suggested fixes
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        fixes = []
        
        if "connection" in error_message or "timeout" in error_message:
            fixes.extend([
                "Check network connectivity to dependent services",
                "Verify service endpoints are accessible",
                "Increase timeout values if appropriate",
                "Check firewall and security group settings"
            ])
        
        elif "permission" in error_message or "access" in error_message or "auth" in error_message:
            fixes.extend([
                "Verify service has proper authentication credentials",
                "Check file and directory permissions",
                "Review security policies and access controls",
                "Ensure service account has necessary privileges"
            ])
        
        elif "memory" in error_message or "resource" in error_message:
            fixes.extend([
                "Check system memory usage and availability",
                "Review service memory configuration",
                "Consider increasing memory limits",
                "Check for memory leaks in service implementation"
            ])
        
        elif "config" in error_message or "setting" in error_message:
            fixes.extend([
                "Review service configuration files",
                "Verify all required configuration parameters are set",
                "Check configuration file syntax and format",
                "Ensure configuration values are within valid ranges"
            ])
        
        else:
            fixes.extend([
                "Review service logs for detailed error information",
                "Check service dependencies and prerequisites",
                "Verify service installation and setup",
                "Consider restarting the service"
            ])
        
        return fixes
    
    def _suggest_alert_fixes(self, alert: IntegrationAlert) -> List[str]:
        """
        Suggest fixes based on alert content.
        
        Args:
            alert: Integration alert
            
        Returns:
            List of suggested fixes
        """
        fixes = []
        
        alert_text = f"{alert.title} {alert.description}".lower()
        
        if "performance" in alert_text or "slow" in alert_text or "response time" in alert_text:
            fixes.extend([
                "Monitor system resource usage (CPU, memory, I/O)",
                "Check for performance bottlenecks in service implementation",
                "Consider implementing caching or connection pooling",
                "Review database query performance if applicable",
                "Check network latency to external dependencies"
            ])
        
        elif "health" in alert_text or "unhealthy" in alert_text:
            fixes.extend([
                "Check service health and restart if necessary",
                "Verify service dependencies are available",
                "Review service configuration and logs",
                "Check system resources and capacity"
            ])
        
        elif "connectivity" in alert_text or "connection" in alert_text:
            fixes.extend([
                "Verify network connectivity between services",
                "Check service endpoints and ports",
                "Review firewall and security settings",
                "Test DNS resolution for service names"
            ])
        
        elif "memory" in alert_text or "cpu" in alert_text or "resource" in alert_text:
            fixes.extend([
                "Monitor system resource usage trends",
                "Consider scaling up resources if needed",
                "Check for resource leaks in applications",
                "Review resource allocation and limits"
            ])
        
        else:
            fixes.extend([
                "Review alert details and system logs",
                "Check related system components",
                "Monitor the situation for patterns",
                "Consider escalating if issue persists"
            ])
        
        return fixes
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """
        Collect system information for diagnostic context.
        
        Returns:
            Dictionary with system information
        """
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat(),
            "timezone": str(datetime.now().astimezone().tzinfo)
        }
    
    def _generate_immediate_actions(self, findings: List[DiagnosticFinding]) -> List[str]:
        """
        Generate immediate action recommendations.
        
        Args:
            findings: List of diagnostic findings
            
        Returns:
            List of immediate actions
        """
        actions = []
        
        # Critical findings require immediate attention
        critical_findings = [f for f in findings if f.severity == DiagnosticSeverity.CRITICAL]
        if critical_findings:
            actions.append(f"Address {len(critical_findings)} critical issues immediately")
            
            # Add specific actions for critical findings
            for finding in critical_findings[:3]:  # Top 3 critical issues
                if finding.suggested_fixes:
                    actions.append(f"For {finding.title}: {finding.suggested_fixes[0]}")
        
        # Error findings
        error_findings = [f for f in findings if f.severity == DiagnosticSeverity.ERROR]
        if error_findings:
            actions.append(f"Investigate and resolve {len(error_findings)} error conditions")
        
        # Service-specific actions
        problematic_services = set(f.service_name for f in findings 
                                 if f.service_name and f.severity in [DiagnosticSeverity.CRITICAL, DiagnosticSeverity.ERROR])
        if problematic_services:
            actions.append(f"Focus on services with issues: {', '.join(list(problematic_services)[:5])}")
        
        return actions
    
    def _generate_preventive_measures(self, findings: List[DiagnosticFinding]) -> List[str]:
        """
        Generate preventive measure recommendations.
        
        Args:
            findings: List of diagnostic findings
            
        Returns:
            List of preventive measures
        """
        measures = []
        
        # Category-based recommendations
        categories = set(f.category for f in findings)
        
        if DiagnosticCategory.PERFORMANCE in categories:
            measures.append("Implement continuous performance monitoring and alerting")
            measures.append("Establish performance baselines and SLA thresholds")
        
        if DiagnosticCategory.DEPENDENCY in categories:
            measures.append("Implement health checks for all service dependencies")
            measures.append("Design services with graceful degradation capabilities")
        
        if DiagnosticCategory.CONFIGURATION in categories:
            measures.append("Implement configuration validation and testing")
            measures.append("Use infrastructure as code for consistent deployments")
        
        if DiagnosticCategory.CONNECTIVITY in categories:
            measures.append("Implement circuit breakers and retry mechanisms")
            measures.append("Monitor network connectivity and latency")
        
        # General recommendations
        measures.extend([
            "Establish regular health check schedules",
            "Implement comprehensive logging and monitoring",
            "Create runbooks for common issues and recovery procedures",
            "Conduct regular system health reviews"
        ])
        
        return measures
    
    def _generate_performance_summary(self, health_results: List[HealthCheckResult]) -> Dict[str, Any]:
        """
        Generate performance summary from health results.
        
        Args:
            health_results: List of health check results
            
        Returns:
            Performance summary dictionary
        """
        if not health_results:
            return {}
        
        response_times = [r.response_time_ms for r in health_results if r.response_time_ms > 0]
        
        if not response_times:
            return {}
        
        return {
            "total_checks": len(health_results),
            "average_response_time_ms": sum(response_times) / len(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "slow_responses_count": len([t for t in response_times if t > 1000]),
            "healthy_checks": len([r for r in health_results if r.status == HealthStatus.HEALTHY]),
            "unhealthy_checks": len([r for r in health_results if r.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]])
        }


class DiagnosticReportGenerator:
    """
    Generator for formatted diagnostic reports.
    
    This class provides various output formats for diagnostic reports
    including text, JSON, and structured formats.
    """
    
    def __init__(self):
        """Initialize report generator."""
        pass
    
    def generate_text_report(self, report: SystemDiagnosticReport) -> str:
        """
        Generate a human-readable text report.
        
        Args:
            report: Diagnostic report to format
            
        Returns:
            Formatted text report
        """
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append(f"TIMELOCKER INTEGRATION DIAGNOSTIC REPORT")
        lines.append(f"Report ID: {report.report_id}")
        lines.append(f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Findings: {report.total_findings}")
        lines.append(f"  Critical: {report.critical_findings}")
        lines.append(f"  Error: {report.error_findings}")
        lines.append(f"  Warning: {report.warning_findings}")
        lines.append(f"  Info: {report.info_findings}")
        lines.append("")
        lines.append(f"Services Analyzed: {len(report.services_analyzed)}")
        lines.append(f"  Healthy: {len(report.healthy_services)}")
        lines.append(f"  Problematic: {len(report.problematic_services)}")
        lines.append("")
        
        # Immediate Actions
        if report.immediate_actions:
            lines.append("IMMEDIATE ACTIONS REQUIRED")
            lines.append("-" * 40)
            for i, action in enumerate(report.immediate_actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")
        
        # Findings by Severity
        for severity in [DiagnosticSeverity.CRITICAL, DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING]:
            severity_findings = [f for f in report.findings if f.severity == severity]
            if severity_findings:
                lines.append(f"{severity.value.upper()} FINDINGS")
                lines.append("-" * 40)
                
                for finding in severity_findings:
                    lines.append(f"• {finding.title}")
                    lines.append(f"  Service: {finding.service_name or 'System'}")
                    lines.append(f"  Category: {finding.category.value}")
                    lines.append(f"  Description: {finding.description}")
                    
                    if finding.suggested_fixes:
                        lines.append("  Suggested Fixes:")
                        for fix in finding.suggested_fixes[:3]:  # Top 3 fixes
                            lines.append(f"    - {fix}")
                    lines.append("")
        
        # Performance Summary
        if report.performance_summary:
            lines.append("PERFORMANCE SUMMARY")
            lines.append("-" * 40)
            perf = report.performance_summary
            lines.append(f"Total Health Checks: {perf.get('total_checks', 0)}")
            lines.append(f"Average Response Time: {perf.get('average_response_time_ms', 0):.1f}ms")
            lines.append(f"Slow Responses: {perf.get('slow_responses_count', 0)}")
            lines.append(f"Healthy Checks: {perf.get('healthy_checks', 0)}")
            lines.append(f"Unhealthy Checks: {perf.get('unhealthy_checks', 0)}")
            lines.append("")
        
        # Preventive Measures
        if report.preventive_measures:
            lines.append("PREVENTIVE MEASURES")
            lines.append("-" * 40)
            for i, measure in enumerate(report.preventive_measures, 1):
                lines.append(f"{i}. {measure}")
            lines.append("")
        
        # System Information
        lines.append("SYSTEM INFORMATION")
        lines.append("-" * 40)
        for key, value in report.system_info.items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("End of Report")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_json_report(self, report: SystemDiagnosticReport) -> str:
        """
        Generate a JSON report.
        
        Args:
            report: Diagnostic report to format
            
        Returns:
            JSON formatted report
        """
        import json
        from dataclasses import asdict
        
        # Convert report to dictionary, handling circular references
        def safe_asdict(obj):
            """Safely convert dataclass to dict, handling circular references"""
            if hasattr(obj, '__dataclass_fields__'):
                result = {}
                for field_name, field_value in obj.__dict__.items():
                    if isinstance(field_value, datetime):
                        result[field_name] = field_value.isoformat()
                    elif hasattr(field_value, '__dataclass_fields__'):
                        # Skip nested dataclasses to avoid circular references
                        result[field_name] = str(field_value)
                    elif isinstance(field_value, (list, tuple)):
                        result[field_name] = [
                            safe_asdict(item) if hasattr(item, '__dataclass_fields__') else item
                            for item in field_value
                        ]
                    elif isinstance(field_value, dict):
                        result[field_name] = {
                            k: safe_asdict(v) if hasattr(v, '__dataclass_fields__') else v
                            for k, v in field_value.items()
                        }
                    else:
                        result[field_name] = field_value
                return result
            return obj
        
        report_dict = safe_asdict(report)
        
        # Convert datetime objects to strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        
        return json.dumps(report_dict, indent=2, default=convert_datetime)
    
    def generate_summary_report(self, report: SystemDiagnosticReport) -> str:
        """
        Generate a brief summary report.
        
        Args:
            report: Diagnostic report to summarize
            
        Returns:
            Brief summary text
        """
        lines = []
        
        lines.append(f"Diagnostic Summary - {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Findings: {report.total_findings} total ({report.critical_findings} critical, {report.error_findings} errors)")
        lines.append(f"Services: {len(report.healthy_services)}/{len(report.services_analyzed)} healthy")
        
        if report.immediate_actions:
            lines.append(f"Immediate Actions: {len(report.immediate_actions)} required")
        
        return " | ".join(lines)


# Convenience functions for diagnostic analysis

def diagnose_service_health(service: ServiceInterface, 
                          health_result: HealthCheckResult) -> List[DiagnosticFinding]:
    """
    Diagnose service health issues and provide suggestions.
    
    Args:
        service: Service to diagnose
        health_result: Health check result
        
    Returns:
        List of diagnostic findings
    """
    analyzer = DiagnosticAnalyzer()
    return analyzer.analyze_service_health(service, health_result)


def generate_system_diagnostic_report(service_manager,
                                    include_health_checks: bool = True,
                                    include_alerts: bool = True) -> SystemDiagnosticReport:
    """
    Generate a comprehensive system diagnostic report.
    
    Args:
        service_manager: ServiceManager to analyze
        include_health_checks: Whether to perform health checks
        include_alerts: Whether to include alert analysis
        
    Returns:
        Comprehensive diagnostic report
    """
    analyzer = DiagnosticAnalyzer()
    
    health_results = []
    alerts = []
    
    # Collect health check results if requested
    if include_health_checks:
        try:
            from .service_health_checks import ServiceHealthChecker
            service_status = service_manager.get_service_status()
            
            for service_name, status in service_status.items():
                if status.get('initialized', False):
                    try:
                        service = service_manager.get_service_by_name(service_name)
                        checker = ServiceHealthChecker(service)
                        health_result = checker.perform_basic_check()
                        health_results.append(health_result)
                    except Exception as e:
                        logger.warning(f"Could not check health for {service_name}: {e}")
        except Exception as e:
            logger.warning(f"Could not perform health checks: {e}")
    
    # Collect alerts if requested
    if include_alerts:
        try:
            # This would integrate with the alert manager if available
            pass
        except Exception as e:
            logger.warning(f"Could not collect alerts: {e}")
    
    return analyzer.generate_comprehensive_report(service_manager, health_results, alerts)