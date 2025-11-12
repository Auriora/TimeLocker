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

Compliance Reporter for Scheduling System

This module provides compliance reporting capabilities for scheduled backups,
including policy adherence analysis, violation detection, and compliance
report generation.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .audit_logger import SchedulingAuditLogger, AuditEventType
from .integration_clients import PolicyManagementClient

logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    """Compliance status levels."""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    UNKNOWN = "unknown"


class ViolationType(Enum):
    """Types of compliance violations."""
    MISSED_EXECUTION = "missed_execution"
    EXECUTION_FAILURE = "execution_failure"
    POLICY_MISMATCH = "policy_mismatch"
    SCHEDULE_DISABLED = "schedule_disabled"
    VALIDATION_FAILURE = "validation_failure"
    PLATFORM_ERROR = "platform_error"


@dataclass
class ComplianceViolation:
    """Represents a compliance violation."""
    violation_type: ViolationType
    schedule_id: str
    timestamp: datetime
    severity: str  # "low", "medium", "high", "critical"
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_type': self.violation_type.value,
            'schedule_id': self.schedule_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'description': self.description,
            'details': self.details
        }


@dataclass
class ScheduleComplianceStatus:
    """Compliance status for a single schedule."""
    schedule_id: str
    schedule_name: str
    policy_id: str
    compliance_status: ComplianceStatus
    last_successful_execution: Optional[datetime]
    missed_executions: int
    failed_executions: int
    violations: List[ComplianceViolation]
    next_expected_execution: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'schedule_id': self.schedule_id,
            'schedule_name': self.schedule_name,
            'policy_id': self.policy_id,
            'compliance_status': self.compliance_status.value,
            'last_successful_execution': self.last_successful_execution.isoformat() 
                if self.last_successful_execution else None,
            'missed_executions': self.missed_executions,
            'failed_executions': self.failed_executions,
            'violations': [v.to_dict() for v in self.violations],
            'next_expected_execution': self.next_expected_execution.isoformat()
                if self.next_expected_execution else None
        }


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    report_id: str
    generated_at: datetime
    report_period_start: datetime
    report_period_end: datetime
    total_schedules: int
    compliant_schedules: int
    warning_schedules: int
    violation_schedules: int
    total_violations: int
    schedule_statuses: List[ScheduleComplianceStatus]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'report_period_start': self.report_period_start.isoformat(),
            'report_period_end': self.report_period_end.isoformat(),
            'total_schedules': self.total_schedules,
            'compliant_schedules': self.compliant_schedules,
            'warning_schedules': self.warning_schedules,
            'violation_schedules': self.violation_schedules,
            'total_violations': self.total_violations,
            'schedule_statuses': [s.to_dict() for s in self.schedule_statuses],
            'summary': self.summary
        }


class ComplianceReporter:
    """
    Compliance reporting for scheduled backup operations.
    
    Responsibilities:
    - Analyze audit trails for compliance violations
    - Generate compliance reports
    - Integrate with Policy Management for policy adherence
    - Detect and report missed or failed executions
    - Provide compliance metrics and trends
    """
    
    # Thresholds for compliance warnings
    MAX_MISSED_EXECUTIONS_WARNING = 2
    MAX_FAILED_EXECUTIONS_WARNING = 3
    MAX_DAYS_WITHOUT_SUCCESS_WARNING = 7
    
    def __init__(
        self,
        audit_logger: SchedulingAuditLogger,
        policy_client: Optional[PolicyManagementClient] = None
    ):
        """
        Initialize compliance reporter.
        
        Args:
            audit_logger: Audit logger instance
            policy_client: Optional policy management client
        """
        self.audit_logger = audit_logger
        self.policy_client = policy_client or PolicyManagementClient()
        self.logger = logging.getLogger(f"{__name__}.ComplianceReporter")
    
    def generate_compliance_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        schedule_ids: Optional[List[str]] = None
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report.
        
        Args:
            start_date: Start of reporting period (default: 30 days ago)
            end_date: End of reporting period (default: now)
            schedule_ids: Optional list of specific schedule IDs to report on
            
        Returns:
            ComplianceReport instance
        """
        # Set default date range
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        self.logger.info(
            f"Generating compliance report for period {start_date} to {end_date}"
        )
        
        # Get all audit entries for the period
        audit_entries = self.audit_logger.get_audit_trail(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Get unique schedule IDs from audit trail
        all_schedule_ids = self._extract_schedule_ids(audit_entries)
        
        # Filter by requested schedule IDs if provided
        if schedule_ids:
            all_schedule_ids = set(schedule_ids) & all_schedule_ids
        
        # Analyze compliance for each schedule
        schedule_statuses = []
        for schedule_id in all_schedule_ids:
            status = self._analyze_schedule_compliance(
                schedule_id,
                audit_entries,
                start_date,
                end_date
            )
            schedule_statuses.append(status)
        
        # Calculate summary statistics
        compliant_count = sum(
            1 for s in schedule_statuses 
            if s.compliance_status == ComplianceStatus.COMPLIANT
        )
        warning_count = sum(
            1 for s in schedule_statuses 
            if s.compliance_status == ComplianceStatus.WARNING
        )
        violation_count = sum(
            1 for s in schedule_statuses 
            if s.compliance_status == ComplianceStatus.VIOLATION
        )
        total_violations = sum(len(s.violations) for s in schedule_statuses)
        
        # Generate summary
        summary = self._generate_summary(schedule_statuses, start_date, end_date)
        
        report = ComplianceReport(
            report_id=self._generate_report_id(),
            generated_at=datetime.utcnow(),
            report_period_start=start_date,
            report_period_end=end_date,
            total_schedules=len(schedule_statuses),
            compliant_schedules=compliant_count,
            warning_schedules=warning_count,
            violation_schedules=violation_count,
            total_violations=total_violations,
            schedule_statuses=schedule_statuses,
            summary=summary
        )
        
        self.logger.info(
            f"Compliance report generated: {compliant_count} compliant, "
            f"{warning_count} warnings, {violation_count} violations"
        )
        
        return report

    def _analyze_schedule_compliance(
        self,
        schedule_id: str,
        audit_entries: List,
        start_date: datetime,
        end_date: datetime
    ) -> ScheduleComplianceStatus:
        """
        Analyze compliance for a single schedule.
        
        Args:
            schedule_id: Schedule identifier
            audit_entries: All audit entries for the period
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            ScheduleComplianceStatus instance
        """
        # Filter entries for this schedule
        schedule_entries = [
            e for e in audit_entries 
            if e.schedule_id == schedule_id
        ]
        
        # Extract schedule information
        schedule_name = self._get_schedule_name(schedule_id, schedule_entries)
        policy_id = self._get_policy_id(schedule_id, schedule_entries)
        
        # Analyze executions
        executions = self._analyze_executions(schedule_entries)
        
        # Detect violations
        violations = self._detect_violations(
            schedule_id,
            schedule_entries,
            executions,
            start_date,
            end_date
        )
        
        # Determine overall compliance status
        compliance_status = self._determine_compliance_status(
            executions,
            violations
        )
        
        return ScheduleComplianceStatus(
            schedule_id=schedule_id,
            schedule_name=schedule_name,
            policy_id=policy_id,
            compliance_status=compliance_status,
            last_successful_execution=executions.get('last_success'),
            missed_executions=executions.get('missed_count', 0),
            failed_executions=executions.get('failed_count', 0),
            violations=violations,
            next_expected_execution=executions.get('next_expected')
        )
    
    def _extract_schedule_ids(self, audit_entries: List) -> Set[str]:
        """Extract unique schedule IDs from audit entries."""
        schedule_ids = set()
        for entry in audit_entries:
            if entry.schedule_id:
                schedule_ids.add(entry.schedule_id)
        return schedule_ids
    
    def _get_schedule_name(self, schedule_id: str, entries: List) -> str:
        """Extract schedule name from audit entries."""
        for entry in entries:
            if entry.event_type == AuditEventType.SCHEDULE_CREATED:
                return entry.details.get('name', schedule_id)
        return schedule_id
    
    def _get_policy_id(self, schedule_id: str, entries: List) -> str:
        """Extract policy ID from audit entries."""
        for entry in entries:
            if entry.event_type == AuditEventType.SCHEDULE_CREATED:
                return entry.details.get('policy_id', 'unknown')
        return 'unknown'
    
    def _analyze_executions(self, entries: List) -> Dict[str, Any]:
        """
        Analyze execution history from audit entries.
        
        Args:
            entries: Audit entries for a schedule
            
        Returns:
            Dictionary with execution analysis
        """
        analysis = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'missed_count': 0,
            'last_success': None,
            'last_failure': None,
            'next_expected': None
        }
        
        for entry in entries:
            if entry.event_type == AuditEventType.EXECUTION_STARTED:
                analysis['total_executions'] += 1
            
            elif entry.event_type == AuditEventType.EXECUTION_COMPLETED:
                status = entry.details.get('status', 'unknown')
                if status == 'success':
                    analysis['successful_executions'] += 1
                    if (analysis['last_success'] is None or 
                        entry.timestamp > analysis['last_success']):
                        analysis['last_success'] = entry.timestamp
                else:
                    analysis['failed_executions'] += 1
                    if (analysis['last_failure'] is None or 
                        entry.timestamp > analysis['last_failure']):
                        analysis['last_failure'] = entry.timestamp
            
            elif entry.event_type == AuditEventType.EXECUTION_FAILED:
                analysis['failed_executions'] += 1
                if (analysis['last_failure'] is None or 
                    entry.timestamp > analysis['last_failure']):
                    analysis['last_failure'] = entry.timestamp
        
        return analysis
    
    def _detect_violations(
        self,
        schedule_id: str,
        entries: List,
        executions: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceViolation]:
        """
        Detect compliance violations from audit entries.
        
        Args:
            schedule_id: Schedule identifier
            entries: Audit entries for the schedule
            executions: Execution analysis
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of detected violations
        """
        violations = []
        
        # Check for excessive failed executions
        if executions['failed_executions'] >= self.MAX_FAILED_EXECUTIONS_WARNING:
            violations.append(ComplianceViolation(
                violation_type=ViolationType.EXECUTION_FAILURE,
                schedule_id=schedule_id,
                timestamp=executions.get('last_failure', end_date),
                severity='high',
                description=f"Schedule has {executions['failed_executions']} failed executions",
                details={
                    'failed_count': executions['failed_executions'],
                    'threshold': self.MAX_FAILED_EXECUTIONS_WARNING
                }
            ))
        
        # Check for long period without successful execution
        if executions['last_success']:
            days_since_success = (end_date - executions['last_success']).days
            if days_since_success > self.MAX_DAYS_WITHOUT_SUCCESS_WARNING:
                violations.append(ComplianceViolation(
                    violation_type=ViolationType.MISSED_EXECUTION,
                    schedule_id=schedule_id,
                    timestamp=end_date,
                    severity='critical',
                    description=f"No successful execution in {days_since_success} days",
                    details={
                        'days_since_success': days_since_success,
                        'last_success': executions['last_success'].isoformat(),
                        'threshold': self.MAX_DAYS_WITHOUT_SUCCESS_WARNING
                    }
                ))
        elif executions['total_executions'] > 0:
            # Schedule has executions but none successful
            violations.append(ComplianceViolation(
                violation_type=ViolationType.EXECUTION_FAILURE,
                schedule_id=schedule_id,
                timestamp=end_date,
                severity='critical',
                description="Schedule has never completed successfully",
                details={
                    'total_executions': executions['total_executions'],
                    'failed_executions': executions['failed_executions']
                }
            ))
        
        # Check for schedule disabled events
        for entry in entries:
            if entry.event_type == AuditEventType.SCHEDULE_DISABLED:
                violations.append(ComplianceViolation(
                    violation_type=ViolationType.SCHEDULE_DISABLED,
                    schedule_id=schedule_id,
                    timestamp=entry.timestamp,
                    severity='medium',
                    description="Schedule was disabled",
                    details=entry.details
                ))
        
        # Check for validation failures
        validation_failures = [
            e for e in entries 
            if e.event_type == AuditEventType.VALIDATION_FAILED
        ]
        if validation_failures:
            violations.append(ComplianceViolation(
                violation_type=ViolationType.VALIDATION_FAILURE,
                schedule_id=schedule_id,
                timestamp=validation_failures[-1].timestamp,
                severity='high',
                description=f"Schedule has {len(validation_failures)} validation failures",
                details={
                    'failure_count': len(validation_failures),
                    'latest_errors': validation_failures[-1].details.get('validation_errors', [])
                }
            ))
        
        # Check for platform errors
        platform_errors = [
            e for e in entries 
            if e.event_type == AuditEventType.PLATFORM_ERROR
        ]
        if platform_errors:
            violations.append(ComplianceViolation(
                violation_type=ViolationType.PLATFORM_ERROR,
                schedule_id=schedule_id,
                timestamp=platform_errors[-1].timestamp,
                severity='high',
                description=f"Schedule has {len(platform_errors)} platform errors",
                details={
                    'error_count': len(platform_errors),
                    'latest_error': platform_errors[-1].details
                }
            ))
        
        return violations
    
    def _determine_compliance_status(
        self,
        executions: Dict[str, Any],
        violations: List[ComplianceViolation]
    ) -> ComplianceStatus:
        """
        Determine overall compliance status.
        
        Args:
            executions: Execution analysis
            violations: Detected violations
            
        Returns:
            ComplianceStatus enum value
        """
        # Check for critical violations
        critical_violations = [
            v for v in violations 
            if v.severity == 'critical'
        ]
        if critical_violations:
            return ComplianceStatus.VIOLATION
        
        # Check for high severity violations
        high_violations = [
            v for v in violations 
            if v.severity == 'high'
        ]
        if high_violations:
            return ComplianceStatus.VIOLATION
        
        # Check for medium severity violations or warnings
        if violations:
            return ComplianceStatus.WARNING
        
        # Check execution success rate
        if executions['total_executions'] > 0:
            success_rate = (
                executions['successful_executions'] / 
                executions['total_executions']
            )
            if success_rate < 0.8:  # Less than 80% success rate
                return ComplianceStatus.WARNING
        
        return ComplianceStatus.COMPLIANT
    
    def _generate_summary(
        self,
        schedule_statuses: List[ScheduleComplianceStatus],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for compliance report.
        
        Args:
            schedule_statuses: List of schedule compliance statuses
            start_date: Start of reporting period
            end_date: End of reporting period
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'reporting_period_days': (end_date - start_date).days,
            'compliance_rate': 0.0,
            'violation_types': {},
            'severity_distribution': {
                'low': 0,
                'medium': 0,
                'high': 0,
                'critical': 0
            },
            'most_common_violations': [],
            'schedules_needing_attention': []
        }
        
        if not schedule_statuses:
            return summary
        
        # Calculate compliance rate
        compliant_count = sum(
            1 for s in schedule_statuses 
            if s.compliance_status == ComplianceStatus.COMPLIANT
        )
        summary['compliance_rate'] = (
            compliant_count / len(schedule_statuses) * 100
        )
        
        # Analyze violation types and severity
        for status in schedule_statuses:
            for violation in status.violations:
                # Count violation types
                vtype = violation.violation_type.value
                summary['violation_types'][vtype] = \
                    summary['violation_types'].get(vtype, 0) + 1
                
                # Count severity distribution
                summary['severity_distribution'][violation.severity] += 1
        
        # Identify most common violations
        if summary['violation_types']:
            sorted_violations = sorted(
                summary['violation_types'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            summary['most_common_violations'] = [
                {'type': vtype, 'count': count}
                for vtype, count in sorted_violations[:5]
            ]
        
        # Identify schedules needing attention
        attention_schedules = [
            {
                'schedule_id': s.schedule_id,
                'schedule_name': s.schedule_name,
                'compliance_status': s.compliance_status.value,
                'violation_count': len(s.violations),
                'failed_executions': s.failed_executions
            }
            for s in schedule_statuses
            if s.compliance_status in [ComplianceStatus.VIOLATION, ComplianceStatus.WARNING]
        ]
        summary['schedules_needing_attention'] = sorted(
            attention_schedules,
            key=lambda x: (x['compliance_status'] == 'violation', x['violation_count']),
            reverse=True
        )[:10]
        
        return summary
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        import uuid
        return f"compliance-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    def export_compliance_report(
        self,
        report: ComplianceReport,
        output_file: Path,
        format: str = 'json'
    ) -> bool:
        """
        Export compliance report to file.
        
        Args:
            report: ComplianceReport instance
            output_file: Path to output file
            format: Output format ('json' or 'html')
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            if format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(report.to_dict(), f, indent=2)
            elif format == 'html':
                html_content = self._generate_html_report(report)
                with open(output_file, 'w') as f:
                    f.write(html_content)
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return False
            
            self.logger.info(f"Exported compliance report to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export compliance report: {e}")
            return False
    
    def _generate_html_report(self, report: ComplianceReport) -> str:
        """
        Generate HTML compliance report.
        
        Args:
            report: ComplianceReport instance
            
        Returns:
            HTML content as string
        """
        # Simple HTML template for compliance report
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report - {report.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; margin: 20px 0; }}
        .compliant {{ color: green; }}
        .warning {{ color: orange; }}
        .violation {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Compliance Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Report ID:</strong> {report.report_id}</p>
        <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Period:</strong> {report.report_period_start.strftime('%Y-%m-%d')} to {report.report_period_end.strftime('%Y-%m-%d')}</p>
        <p><strong>Total Schedules:</strong> {report.total_schedules}</p>
        <p><strong>Compliant:</strong> <span class="compliant">{report.compliant_schedules}</span></p>
        <p><strong>Warnings:</strong> <span class="warning">{report.warning_schedules}</span></p>
        <p><strong>Violations:</strong> <span class="violation">{report.violation_schedules}</span></p>
        <p><strong>Compliance Rate:</strong> {report.summary.get('compliance_rate', 0):.1f}%</p>
    </div>
    
    <h2>Schedule Status</h2>
    <table>
        <tr>
            <th>Schedule ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Violations</th>
            <th>Failed Executions</th>
            <th>Last Success</th>
        </tr>
"""
        
        for status in report.schedule_statuses:
            status_class = status.compliance_status.value
            last_success = (
                status.last_successful_execution.strftime('%Y-%m-%d %H:%M')
                if status.last_successful_execution else 'Never'
            )
            html += f"""
        <tr>
            <td>{status.schedule_id}</td>
            <td>{status.schedule_name}</td>
            <td class="{status_class}">{status.compliance_status.value.upper()}</td>
            <td>{len(status.violations)}</td>
            <td>{status.failed_executions}</td>
            <td>{last_success}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        return html
    
    def get_policy_compliance_summary(self, policy_id: str) -> Dict[str, Any]:
        """
        Get compliance summary for all schedules using a specific policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Dictionary with policy compliance summary
        """
        try:
            # Generate report for last 30 days
            report = self.generate_compliance_report()
            
            # Filter schedules by policy
            policy_schedules = [
                s for s in report.schedule_statuses
                if s.policy_id == policy_id
            ]
            
            if not policy_schedules:
                return {
                    'policy_id': policy_id,
                    'schedule_count': 0,
                    'message': 'No schedules found for this policy'
                }
            
            # Calculate policy-specific metrics
            compliant = sum(
                1 for s in policy_schedules
                if s.compliance_status == ComplianceStatus.COMPLIANT
            )
            
            summary = {
                'policy_id': policy_id,
                'schedule_count': len(policy_schedules),
                'compliant_count': compliant,
                'warning_count': sum(
                    1 for s in policy_schedules
                    if s.compliance_status == ComplianceStatus.WARNING
                ),
                'violation_count': sum(
                    1 for s in policy_schedules
                    if s.compliance_status == ComplianceStatus.VIOLATION
                ),
                'compliance_rate': (compliant / len(policy_schedules) * 100),
                'total_violations': sum(len(s.violations) for s in policy_schedules),
                'schedules': [
                    {
                        'schedule_id': s.schedule_id,
                        'schedule_name': s.schedule_name,
                        'compliance_status': s.compliance_status.value,
                        'violation_count': len(s.violations)
                    }
                    for s in policy_schedules
                ]
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get policy compliance summary: {e}")
            return {
                'policy_id': policy_id,
                'error': str(e)
            }
