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

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .status_reporter import OperationStatus, StatusLevel

logger = logging.getLogger(__name__)


# Forward declaration for type hints
if False:  # TYPE_CHECKING
    from .configuration_troubleshooter import ConfigurationTroubleshooter


class IssueType(Enum):
    """Types of issues that can be detected"""
    BACKUP_FAILURE = "backup_failure"
    RECOVERY_FAILURE = "recovery_failure"
    STORAGE_FULL = "storage_full"
    INTEGRITY_FAILURE = "integrity_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    REPOSITORY_LOCKED = "repository_locked"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Severity levels for detected issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectedIssue:
    """Represents a detected issue"""
    issue_id: str
    issue_type: IssueType
    severity: IssueSeverity
    title: str
    description: str
    affected_operations: List[str]
    first_occurrence: datetime
    last_occurrence: datetime
    occurrence_count: int
    repository_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TroubleshootingStep:
    """A single troubleshooting step"""
    step_number: int
    description: str
    command: Optional[str] = None
    expected_result: Optional[str] = None
    additional_info: Optional[str] = None


@dataclass
class TroubleshootingGuide:
    """Complete troubleshooting guide for an issue"""
    issue_type: IssueType
    title: str
    description: str
    possible_causes: List[str]
    steps: List[TroubleshootingStep]
    additional_resources: List[str] = field(default_factory=list)
    prevention_tips: List[str] = field(default_factory=list)


@dataclass
class EventCorrelation:
    """Represents correlated events that may indicate a pattern"""
    correlation_id: str
    event_ids: List[str]
    pattern_type: str
    description: str
    confidence: float  # 0.0 to 1.0
    first_event_time: datetime
    last_event_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProactiveRecommendation:
    """Proactive recommendation to prevent issues"""
    recommendation_id: str
    title: str
    description: str
    priority: IssueSeverity
    action_items: List[str]
    estimated_impact: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupFailure:
    """Represents a backup failure for analysis"""
    operation_id: str
    repository_id: Optional[str]
    timestamp: datetime
    error_message: str
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TroubleshootingReport:
    """Complete troubleshooting report for a failure"""
    failure: BackupFailure
    detected_issues: List[DetectedIssue]
    root_cause_analysis: str
    troubleshooting_guide: TroubleshootingGuide
    related_events: List[EventCorrelation]
    recommendations: List[ProactiveRecommendation]
    generated_at: datetime


class EventCorrelator:
    """
    Correlates events to identify patterns and relationships.
    
    Responsibilities:
    - Identify related events across operations
    - Detect common failure patterns
    - Calculate correlation confidence
    """
    
    def __init__(self):
        """Initialize event correlator"""
        self.correlation_window = timedelta(hours=24)
        self.min_pattern_occurrences = 2
    
    def correlate_events(
        self,
        events: List[OperationStatus],
        time_window: Optional[timedelta] = None
    ) -> List[EventCorrelation]:
        """
        Correlate events to identify patterns.
        
        Args:
            events: List of operation statuses to analyze
            time_window: Time window for correlation (default: 24 hours)
            
        Returns:
            List of event correlations
            
        Requirements: 9.1
        """
        if not events:
            return []
        
        window = time_window or self.correlation_window
        correlations = []
        
        # Group events by repository
        repo_events = defaultdict(list)
        for event in events:
            if event.repository_id:
                repo_events[event.repository_id].append(event)
        
        # Analyze patterns within each repository
        for repo_id, repo_event_list in repo_events.items():
            # Sort by timestamp
            sorted_events = sorted(repo_event_list, key=lambda e: e.timestamp)
            
            # Find repeated failure patterns
            failure_events = [e for e in sorted_events if e.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]]
            
            if len(failure_events) >= self.min_pattern_occurrences:
                # Check if failures occur within time window
                first_failure = failure_events[0]
                last_failure = failure_events[-1]
                
                if last_failure.timestamp - first_failure.timestamp <= window:
                    # Create correlation
                    correlation = EventCorrelation(
                        correlation_id=f"corr_{repo_id}_{first_failure.timestamp.isoformat()}",
                        event_ids=[e.operation_id for e in failure_events],
                        pattern_type="repeated_failures",
                        description=f"Repeated failures detected in repository {repo_id}",
                        confidence=min(1.0, len(failure_events) / 5.0),  # Higher confidence with more failures
                        first_event_time=first_failure.timestamp,
                        last_event_time=last_failure.timestamp,
                        metadata={
                            'repository_id': repo_id,
                            'failure_count': len(failure_events),
                            'error_messages': [e.message for e in failure_events[:3]]  # First 3 messages
                        }
                    )
                    correlations.append(correlation)
        
        # Detect time-based patterns (e.g., failures at specific times)
        correlations.extend(self._detect_temporal_patterns(events, window))
        
        return correlations
    
    def _detect_temporal_patterns(
        self,
        events: List[OperationStatus],
        window: timedelta
    ) -> List[EventCorrelation]:
        """
        Detect temporal patterns in events.
        
        Args:
            events: Events to analyze
            window: Time window for analysis
            
        Returns:
            List of temporal correlations
        """
        correlations = []
        
        # Group failures by hour of day
        hour_failures = defaultdict(list)
        for event in events:
            if event.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]:
                hour = event.timestamp.hour
                hour_failures[hour].append(event)
        
        # Find hours with multiple failures
        for hour, failures in hour_failures.items():
            if len(failures) >= self.min_pattern_occurrences:
                correlation = EventCorrelation(
                    correlation_id=f"temporal_hour_{hour}",
                    event_ids=[e.operation_id for e in failures],
                    pattern_type="temporal_pattern",
                    description=f"Multiple failures occurring around hour {hour}:00",
                    confidence=min(1.0, len(failures) / 3.0),
                    first_event_time=min(f.timestamp for f in failures),
                    last_event_time=max(f.timestamp for f in failures),
                    metadata={
                        'hour_of_day': hour,
                        'failure_count': len(failures)
                    }
                )
                correlations.append(correlation)
        
        return correlations


class IssueDetector:
    """
    Detects and classifies issues from events and system state.
    
    Responsibilities:
    - Classify error types
    - Detect issue patterns
    - Track issue occurrences
    - Calculate issue severity
    """
    
    def __init__(self):
        """Initialize issue detector"""
        self.detected_issues: Dict[str, DetectedIssue] = {}
        self.issue_patterns = self._initialize_issue_patterns()
    
    def _initialize_issue_patterns(self) -> Dict[IssueType, List[str]]:
        """
        Initialize patterns for issue detection.
        
        Returns:
            Mapping of issue types to error message patterns
        """
        return {
            IssueType.STORAGE_FULL: [
                'no space left',
                'disk full',
                'storage capacity',
                'quota exceeded'
            ],
            IssueType.NETWORK_ERROR: [
                'connection refused',
                'network unreachable',
                'timeout',
                'connection reset',
                'dns resolution failed'
            ],
            IssueType.PERMISSION_ERROR: [
                'permission denied',
                'access denied',
                'forbidden',
                'unauthorized'
            ],
            IssueType.REPOSITORY_LOCKED: [
                'repository locked',
                'lock file exists',
                'already locked',
                'unable to acquire lock'
            ],
            IssueType.CONFIGURATION_ERROR: [
                'invalid configuration',
                'configuration error',
                'missing required',
                'invalid repository'
            ]
        }
    
    def detect_issues(
        self,
        events: List[OperationStatus],
        time_window: timedelta = timedelta(days=7)
    ) -> List[DetectedIssue]:
        """
        Detect issues from recent events.
        
        Args:
            events: Events to analyze
            time_window: Time window for analysis
            
        Returns:
            List of detected issues
            
        Requirements: 9.1, 9.2
        """
        cutoff_time = datetime.now() - time_window
        recent_events = [e for e in events if e.timestamp >= cutoff_time]
        
        # Analyze each error event
        for event in recent_events:
            if event.status in [StatusLevel.ERROR, StatusLevel.CRITICAL]:
                issue_type = self._classify_error(event.message)
                self._record_issue_occurrence(event, issue_type)
        
        # Return all detected issues
        return list(self.detected_issues.values())
    
    def _classify_error(self, error_message: str) -> IssueType:
        """
        Classify error based on message content.
        
        Args:
            error_message: Error message to classify
            
        Returns:
            Classified issue type
        """
        error_lower = error_message.lower()
        
        for issue_type, patterns in self.issue_patterns.items():
            for pattern in patterns:
                if pattern in error_lower:
                    return issue_type
        
        # Check for specific operation types
        if 'backup' in error_lower:
            return IssueType.BACKUP_FAILURE
        elif 'recovery' in error_lower or 'restore' in error_lower:
            return IssueType.RECOVERY_FAILURE
        elif 'integrity' in error_lower or 'verify' in error_lower:
            return IssueType.INTEGRITY_FAILURE
        
        return IssueType.UNKNOWN
    
    def _record_issue_occurrence(
        self,
        event: OperationStatus,
        issue_type: IssueType
    ) -> None:
        """
        Record an issue occurrence.
        
        Args:
            event: Event that triggered the issue
            issue_type: Type of issue detected
        """
        # Create issue key based on type and repository
        issue_key = f"{issue_type.value}_{event.repository_id or 'global'}"
        
        if issue_key in self.detected_issues:
            # Update existing issue
            issue = self.detected_issues[issue_key]
            issue.affected_operations.append(event.operation_id)
            issue.last_occurrence = event.timestamp
            issue.occurrence_count += 1
            
            # Update severity based on frequency
            if issue.occurrence_count >= 10:
                issue.severity = IssueSeverity.CRITICAL
            elif issue.occurrence_count >= 5:
                issue.severity = IssueSeverity.HIGH
            elif issue.occurrence_count >= 3:
                issue.severity = IssueSeverity.MEDIUM
        else:
            # Create new issue
            severity = IssueSeverity.HIGH if event.status == StatusLevel.CRITICAL else IssueSeverity.MEDIUM
            
            issue = DetectedIssue(
                issue_id=issue_key,
                issue_type=issue_type,
                severity=severity,
                title=self._generate_issue_title(issue_type),
                description=event.message,
                affected_operations=[event.operation_id],
                first_occurrence=event.timestamp,
                last_occurrence=event.timestamp,
                occurrence_count=1,
                repository_id=event.repository_id,
                metadata={'latest_error': event.message}
            )
            
            self.detected_issues[issue_key] = issue
    
    def _generate_issue_title(self, issue_type: IssueType) -> str:
        """
        Generate user-friendly title for issue type.
        
        Args:
            issue_type: Type of issue
            
        Returns:
            User-friendly title
        """
        titles = {
            IssueType.BACKUP_FAILURE: "Backup Operation Failures",
            IssueType.RECOVERY_FAILURE: "Recovery Operation Failures",
            IssueType.STORAGE_FULL: "Storage Capacity Issues",
            IssueType.INTEGRITY_FAILURE: "Data Integrity Problems",
            IssueType.PERFORMANCE_DEGRADATION: "Performance Degradation",
            IssueType.CONFIGURATION_ERROR: "Configuration Problems",
            IssueType.NETWORK_ERROR: "Network Connectivity Issues",
            IssueType.PERMISSION_ERROR: "Permission or Access Issues",
            IssueType.REPOSITORY_LOCKED: "Repository Lock Issues",
            IssueType.UNKNOWN: "Unclassified Issues"
        }
        return titles.get(issue_type, "Unknown Issue")


class TroubleshootingService:
    """
    Provides event correlation and troubleshooting support.
    
    Responsibilities:
    - Event correlation and pattern analysis
    - Root cause analysis for common issues
    - User-friendly troubleshooting guidance
    - Proactive issue detection and recommendations
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    def __init__(self, config_dir: Optional[Path] = None, config_module=None):
        """
        Initialize troubleshooting service.
        
        Args:
            config_dir: Directory for troubleshooting data storage
            config_module: Optional ConfigurationModule for configuration troubleshooting
        """
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "troubleshooting"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.event_correlator = EventCorrelator()
        self.issue_detector = IssueDetector()
        
        # Configuration troubleshooting integration
        self.config_module = config_module
        self.config_troubleshooter: Optional['ConfigurationTroubleshooter'] = None
        if config_module:
            try:
                from .configuration_troubleshooter import ConfigurationTroubleshooter
                self.config_troubleshooter = ConfigurationTroubleshooter(config_module)
            except Exception as e:
                logger.warning(f"Failed to initialize configuration troubleshooter: {e}")
        
        # Cache for troubleshooting guides
        self.guide_cache: Dict[IssueType, TroubleshootingGuide] = {}
        
        logger.info("TroubleshootingService initialized")
    
    def analyze_backup_failure(
        self,
        failure: BackupFailure,
        recent_events: Optional[List[OperationStatus]] = None
    ) -> TroubleshootingReport:
        """
        Analyze backup failure and provide troubleshooting guidance.
        
        Args:
            failure: Backup failure to analyze
            recent_events: Recent operation events for context
            
        Returns:
            Complete troubleshooting report
            
        Requirements: 9.1, 9.2
        """
        try:
            # Detect issues from the failure
            issue_type = self.issue_detector._classify_error(failure.error_message)
            
            # Create detected issue
            detected_issue = DetectedIssue(
                issue_id=f"failure_{failure.operation_id}",
                issue_type=issue_type,
                severity=IssueSeverity.HIGH,
                title=self.issue_detector._generate_issue_title(issue_type),
                description=failure.error_message,
                affected_operations=[failure.operation_id],
                first_occurrence=failure.timestamp,
                last_occurrence=failure.timestamp,
                occurrence_count=1,
                repository_id=failure.repository_id,
                metadata=failure.metadata
            )
            
            # Correlate with recent events if provided
            related_events = []
            if recent_events:
                related_events = self.event_correlator.correlate_events(recent_events)
            
            # Get troubleshooting guide
            guide = self.get_troubleshooting_guide(issue_type)
            
            # Perform root cause analysis
            root_cause = self._analyze_root_cause(failure, issue_type, related_events)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(issue_type, detected_issue, related_events)
            
            return TroubleshootingReport(
                failure=failure,
                detected_issues=[detected_issue],
                root_cause_analysis=root_cause,
                troubleshooting_guide=guide,
                related_events=related_events,
                recommendations=recommendations,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze backup failure: {e}")
            raise
    
    def correlate_events(
        self,
        events: List[OperationStatus],
        time_window: Optional[timedelta] = None
    ) -> List[EventCorrelation]:
        """
        Correlate related events to identify patterns.
        
        Args:
            events: Events to correlate
            time_window: Time window for correlation
            
        Returns:
            List of event correlations
            
        Requirements: 9.1
        """
        try:
            return self.event_correlator.correlate_events(events, time_window)
        except Exception as e:
            logger.error(f"Failed to correlate events: {e}")
            return []
    
    def detect_proactive_issues(
        self,
        events: List[OperationStatus],
        time_window: timedelta = timedelta(days=7)
    ) -> List[ProactiveRecommendation]:
        """
        Detect potential issues before they cause failures.
        
        Args:
            events: Recent events to analyze
            time_window: Time window for analysis
            
        Returns:
            List of proactive recommendations
            
        Requirements: 9.2, 9.3
        """
        try:
            recommendations = []
            
            # Detect issues
            detected_issues = self.issue_detector.detect_issues(events, time_window)
            
            # Generate proactive recommendations for detected issues
            for issue in detected_issues:
                if issue.occurrence_count >= 2:  # Issue is recurring
                    recommendation = ProactiveRecommendation(
                        recommendation_id=f"proactive_{issue.issue_id}",
                        title=f"Address Recurring {issue.title}",
                        description=f"This issue has occurred {issue.occurrence_count} times. "
                                  f"Taking action now can prevent future failures.",
                        priority=issue.severity,
                        action_items=self._get_proactive_actions(issue.issue_type),
                        estimated_impact=f"Prevent {issue.occurrence_count} similar failures",
                        metadata={
                            'issue_type': issue.issue_type.value,
                            'occurrence_count': issue.occurrence_count
                        }
                    )
                    recommendations.append(recommendation)
            
            # Check for warning-level events that might escalate
            warning_events = [e for e in events if e.status == StatusLevel.WARNING]
            if len(warning_events) >= 5:
                recommendation = ProactiveRecommendation(
                    recommendation_id="proactive_warnings",
                    title="Multiple Warnings Detected",
                    description=f"{len(warning_events)} warnings detected in the past {time_window.days} days. "
                              "Review and address these warnings to prevent potential failures.",
                    priority=IssueSeverity.MEDIUM,
                    action_items=[
                        "Review warning messages in activity logs",
                        "Address any configuration or setup issues",
                        "Monitor for escalation to errors"
                    ],
                    estimated_impact="Prevent warnings from escalating to failures"
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to detect proactive issues: {e}")
            return []
    
    def get_troubleshooting_guide(self, issue_type: IssueType) -> TroubleshootingGuide:
        """
        Get step-by-step troubleshooting guide for issue type.
        
        Args:
            issue_type: Type of issue
            
        Returns:
            Troubleshooting guide
            
        Requirements: 9.4, 9.5
        """
        # Check cache first
        if issue_type in self.guide_cache:
            return self.guide_cache[issue_type]
        
        # Generate guide based on issue type
        guide = self._generate_troubleshooting_guide(issue_type)
        
        # Cache the guide
        self.guide_cache[issue_type] = guide
        
        return guide
    
    def _analyze_root_cause(
        self,
        failure: BackupFailure,
        issue_type: IssueType,
        correlations: List[EventCorrelation]
    ) -> str:
        """
        Analyze root cause of failure.
        
        Args:
            failure: Backup failure
            issue_type: Classified issue type
            correlations: Related event correlations
            
        Returns:
            Root cause analysis description
        """
        analysis_parts = []
        
        # Basic classification
        analysis_parts.append(f"The failure has been classified as: {issue_type.value.replace('_', ' ').title()}")
        
        # Error message analysis
        if failure.error_message:
            analysis_parts.append(f"Error message: {failure.error_message}")
        
        # Pattern analysis
        if correlations:
            pattern_count = len(correlations)
            analysis_parts.append(
                f"This failure is part of a pattern with {pattern_count} related event(s). "
                "This suggests a systemic issue rather than an isolated incident."
            )
        
        # Issue-specific analysis
        if issue_type == IssueType.STORAGE_FULL:
            analysis_parts.append(
                "Root cause: Insufficient storage space. "
                "The backup repository or target location has run out of available space."
            )
        elif issue_type == IssueType.NETWORK_ERROR:
            analysis_parts.append(
                "Root cause: Network connectivity issue. "
                "The backup system cannot reach the repository location."
            )
        elif issue_type == IssueType.PERMISSION_ERROR:
            analysis_parts.append(
                "Root cause: Permission or access issue. "
                "The backup system lacks necessary permissions to access the repository or files."
            )
        elif issue_type == IssueType.REPOSITORY_LOCKED:
            analysis_parts.append(
                "Root cause: Repository lock conflict. "
                "Another backup operation may be in progress or a previous operation did not clean up properly."
            )
        elif issue_type == IssueType.CONFIGURATION_ERROR:
            analysis_parts.append(
                "Root cause: Configuration problem. "
                "The backup configuration contains invalid or missing settings."
            )
        
        return " ".join(analysis_parts)
    
    def _generate_recommendations(
        self,
        issue_type: IssueType,
        issue: DetectedIssue,
        correlations: List[EventCorrelation]
    ) -> List[ProactiveRecommendation]:
        """
        Generate proactive recommendations based on issue analysis.
        
        Args:
            issue_type: Type of issue
            issue: Detected issue details
            correlations: Related event correlations
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Generate issue-specific recommendations
        action_items = self._get_proactive_actions(issue_type)
        
        if action_items:
            recommendation = ProactiveRecommendation(
                recommendation_id=f"rec_{issue.issue_id}",
                title=f"Resolve {issue.title}",
                description=f"Take action to resolve this {issue.severity.value} severity issue.",
                priority=issue.severity,
                action_items=action_items,
                estimated_impact="Prevent future failures of this type"
            )
            recommendations.append(recommendation)
        
        # Add pattern-based recommendations
        if correlations:
            recommendation = ProactiveRecommendation(
                recommendation_id=f"pattern_{issue.issue_id}",
                title="Address Recurring Pattern",
                description="Multiple related failures detected. Addressing the root cause will prevent future occurrences.",
                priority=IssueSeverity.HIGH,
                action_items=[
                    "Review all related failures for common factors",
                    "Implement systematic fix rather than addressing individual failures",
                    "Monitor for pattern recurrence after fix"
                ],
                estimated_impact=f"Prevent {len(correlations)} related failures"
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _get_proactive_actions(self, issue_type: IssueType) -> List[str]:
        """
        Get proactive action items for issue type.
        
        Args:
            issue_type: Type of issue
            
        Returns:
            List of action items
        """
        actions = {
            IssueType.STORAGE_FULL: [
                "Check available storage space on backup repository",
                "Run retention policy to remove old backups",
                "Consider expanding storage capacity",
                "Review backup size and frequency settings"
            ],
            IssueType.NETWORK_ERROR: [
                "Verify network connectivity to repository",
                "Check firewall and security settings",
                "Test repository URL accessibility",
                "Review network logs for connection issues"
            ],
            IssueType.PERMISSION_ERROR: [
                "Verify file and directory permissions",
                "Check user account has necessary access rights",
                "Review repository access credentials",
                "Ensure backup service has required privileges"
            ],
            IssueType.REPOSITORY_LOCKED: [
                "Check for running backup operations",
                "Remove stale lock files if no operations are active",
                "Verify only one backup process accesses repository",
                "Review backup scheduling to prevent conflicts"
            ],
            IssueType.CONFIGURATION_ERROR: [
                "Review backup configuration settings",
                "Validate repository configuration",
                "Check for missing required parameters",
                "Verify configuration file syntax"
            ],
            IssueType.BACKUP_FAILURE: [
                "Review backup logs for detailed error information",
                "Verify source files are accessible",
                "Check backup tool installation and version",
                "Test backup with minimal dataset"
            ],
            IssueType.RECOVERY_FAILURE: [
                "Verify snapshot exists and is accessible",
                "Check target restore location permissions",
                "Review recovery logs for specific errors",
                "Test recovery with single file first"
            ],
            IssueType.INTEGRITY_FAILURE: [
                "Run repository integrity check",
                "Review integrity check logs",
                "Consider repository repair if supported",
                "Verify backup data is not corrupted"
            ]
        }
        
        return actions.get(issue_type, [
            "Review error logs for detailed information",
            "Check system resources and connectivity",
            "Verify configuration settings",
            "Contact support if issue persists"
        ])
    
    def _generate_troubleshooting_guide(self, issue_type: IssueType) -> TroubleshootingGuide:
        """
        Generate comprehensive troubleshooting guide for issue type.
        
        Args:
            issue_type: Type of issue
            
        Returns:
            Complete troubleshooting guide
        """
        guides = {
            IssueType.STORAGE_FULL: self._create_storage_full_guide(),
            IssueType.NETWORK_ERROR: self._create_network_error_guide(),
            IssueType.PERMISSION_ERROR: self._create_permission_error_guide(),
            IssueType.REPOSITORY_LOCKED: self._create_repository_locked_guide(),
            IssueType.CONFIGURATION_ERROR: self._create_configuration_error_guide(),
            IssueType.BACKUP_FAILURE: self._create_backup_failure_guide(),
            IssueType.RECOVERY_FAILURE: self._create_recovery_failure_guide(),
            IssueType.INTEGRITY_FAILURE: self._create_integrity_failure_guide()
        }
        
        return guides.get(issue_type, self._create_generic_guide())
    
    def _create_storage_full_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for storage full issues"""
        return TroubleshootingGuide(
            issue_type=IssueType.STORAGE_FULL,
            title="Storage Capacity Issues",
            description="The backup repository or target location has insufficient storage space.",
            possible_causes=[
                "Backup repository is full",
                "Retention policy not removing old backups",
                "Unexpected growth in backup size",
                "Disk quota exceeded"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Check available storage space",
                    command="df -h <repository_path>",
                    expected_result="Shows available space on the repository volume"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Review current backup size",
                    command="timelocker repository stats <repository_name>",
                    expected_result="Displays repository size and statistics"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Apply retention policy to remove old backups",
                    command="timelocker retention apply <repository_name>",
                    expected_result="Removes old backups according to retention policy"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="If space is still insufficient, expand storage or adjust backup settings",
                    additional_info="Consider reducing backup frequency or excluding unnecessary files"
                )
            ],
            additional_resources=[
                "Storage monitoring documentation",
                "Retention policy configuration guide"
            ],
            prevention_tips=[
                "Configure appropriate retention policies",
                "Monitor storage usage regularly",
                "Set up storage capacity alerts",
                "Review backup selection to exclude unnecessary files"
            ]
        )
    
    def _create_network_error_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for network errors"""
        return TroubleshootingGuide(
            issue_type=IssueType.NETWORK_ERROR,
            title="Network Connectivity Issues",
            description="The backup system cannot establish or maintain connection to the repository.",
            possible_causes=[
                "Network connectivity problems",
                "Firewall blocking connections",
                "Repository server is down",
                "DNS resolution failure",
                "Incorrect repository URL"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Test basic network connectivity",
                    command="ping <repository_host>",
                    expected_result="Successful ping responses"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Verify repository URL is correct",
                    additional_info="Check repository configuration for typos or incorrect URLs"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Test repository accessibility",
                    command="timelocker repository check <repository_name>",
                    expected_result="Repository is accessible and responding"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Check firewall and security settings",
                    additional_info="Ensure required ports are open and not blocked by firewall"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="Review network logs for connection issues",
                    additional_info="Check system logs for network-related errors"
                )
            ],
            additional_resources=[
                "Network troubleshooting guide",
                "Repository connectivity documentation"
            ],
            prevention_tips=[
                "Use reliable network connections for backups",
                "Configure network monitoring",
                "Set up connection retry policies",
                "Consider local repository for critical backups"
            ]
        )
    
    def _create_permission_error_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for permission errors"""
        return TroubleshootingGuide(
            issue_type=IssueType.PERMISSION_ERROR,
            title="Permission and Access Issues",
            description="The backup system lacks necessary permissions to access files or repository.",
            possible_causes=[
                "Insufficient file permissions",
                "Incorrect user account",
                "Repository access credentials invalid",
                "SELinux or AppArmor restrictions"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Verify file and directory permissions",
                    command="ls -la <path>",
                    expected_result="Shows current permissions on files and directories"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Check backup service is running with correct user",
                    additional_info="Verify the user account has read access to source files"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Verify repository credentials",
                    command="timelocker credentials show <repository_name>",
                    expected_result="Displays configured credentials (masked)"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Test repository access",
                    command="timelocker repository check <repository_name>",
                    expected_result="Successfully connects to repository"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="Check for SELinux or AppArmor restrictions",
                    additional_info="Review security policy logs for denials"
                )
            ],
            additional_resources=[
                "Permission configuration guide",
                "Security policy documentation"
            ],
            prevention_tips=[
                "Use appropriate service accounts for backups",
                "Regularly audit file permissions",
                "Document required permissions",
                "Test permissions after system changes"
            ]
        )
    
    def _create_repository_locked_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for repository lock issues"""
        return TroubleshootingGuide(
            issue_type=IssueType.REPOSITORY_LOCKED,
            title="Repository Lock Issues",
            description="The repository is locked by another operation or stale lock file.",
            possible_causes=[
                "Another backup operation is running",
                "Previous operation did not clean up lock",
                "Concurrent access from multiple systems",
                "System crash during backup"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Check for running backup operations",
                    command="timelocker status",
                    expected_result="Shows any currently running operations"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="If no operations are running, check for stale locks",
                    command="timelocker repository unlock <repository_name>",
                    expected_result="Removes stale lock files",
                    additional_info="Only use if you're certain no operations are running"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Verify backup scheduling to prevent conflicts",
                    additional_info="Ensure backup schedules don't overlap"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Check for multiple systems accessing same repository",
                    additional_info="Coordinate backup schedules across systems"
                )
            ],
            additional_resources=[
                "Repository locking documentation",
                "Backup scheduling guide"
            ],
            prevention_tips=[
                "Avoid concurrent backups to same repository",
                "Configure appropriate backup timeouts",
                "Monitor backup completion",
                "Use separate repositories for different systems"
            ]
        )
    
    def _create_configuration_error_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for configuration errors"""
        return TroubleshootingGuide(
            issue_type=IssueType.CONFIGURATION_ERROR,
            title="Configuration Problems",
            description="The backup configuration contains invalid or missing settings.",
            possible_causes=[
                "Invalid configuration syntax",
                "Missing required parameters",
                "Incorrect repository settings",
                "Configuration file corruption"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Validate configuration file",
                    command="timelocker config validate",
                    expected_result="Reports any configuration errors"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Review configuration for missing parameters",
                    command="timelocker config show",
                    expected_result="Displays current configuration"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Check repository configuration",
                    command="timelocker repository list",
                    expected_result="Shows configured repositories"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="If configuration is corrupted, restore from backup",
                    additional_info="Configuration backups are stored in the config directory"
                )
            ],
            additional_resources=[
                "Configuration reference documentation",
                "Configuration examples"
            ],
            prevention_tips=[
                "Validate configuration after changes",
                "Keep configuration backups",
                "Use configuration management tools",
                "Document configuration changes"
            ]
        )
    
    def _create_backup_failure_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for general backup failures"""
        return TroubleshootingGuide(
            issue_type=IssueType.BACKUP_FAILURE,
            title="Backup Operation Failures",
            description="Backup operations are failing to complete successfully.",
            possible_causes=[
                "Source files are inaccessible",
                "Repository connectivity issues",
                "Insufficient resources",
                "Backup tool errors"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Review backup logs for detailed error information",
                    command="timelocker logs --operation-type backup --level error",
                    expected_result="Shows recent backup errors"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Verify source files are accessible",
                    additional_info="Check that source paths exist and are readable"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Test repository connectivity",
                    command="timelocker repository check <repository_name>",
                    expected_result="Repository is accessible"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Check system resources",
                    additional_info="Verify sufficient CPU, memory, and disk I/O available"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="Test backup with minimal dataset",
                    additional_info="Try backing up a small test directory to isolate the issue"
                )
            ],
            additional_resources=[
                "Backup troubleshooting guide",
                "Log analysis documentation"
            ],
            prevention_tips=[
                "Monitor backup completion regularly",
                "Set up backup failure alerts",
                "Test backups periodically",
                "Keep backup tool updated"
            ]
        )
    
    def _create_recovery_failure_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for recovery failures"""
        return TroubleshootingGuide(
            issue_type=IssueType.RECOVERY_FAILURE,
            title="Recovery Operation Failures",
            description="Recovery or restore operations are failing.",
            possible_causes=[
                "Snapshot not found or corrupted",
                "Target location permissions",
                "Insufficient disk space",
                "Repository connectivity issues"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Verify snapshot exists",
                    command="timelocker snapshots list <repository_name>",
                    expected_result="Shows available snapshots"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Check target restore location",
                    additional_info="Verify target path exists and has write permissions"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Verify sufficient disk space",
                    command="df -h <target_path>",
                    expected_result="Shows available space at target location"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Test recovery with single file",
                    additional_info="Try restoring one file to verify basic functionality"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="Review recovery logs",
                    command="timelocker logs --operation-type recovery --level error",
                    expected_result="Shows recovery error details"
                )
            ],
            additional_resources=[
                "Recovery operations guide",
                "Snapshot management documentation"
            ],
            prevention_tips=[
                "Test recovery procedures regularly",
                "Verify backup integrity periodically",
                "Document recovery procedures",
                "Maintain sufficient space for recovery"
            ]
        )
    
    def _create_integrity_failure_guide(self) -> TroubleshootingGuide:
        """Create troubleshooting guide for integrity check failures"""
        return TroubleshootingGuide(
            issue_type=IssueType.INTEGRITY_FAILURE,
            title="Data Integrity Problems",
            description="Integrity checks are detecting issues with backup data.",
            possible_causes=[
                "Data corruption in repository",
                "Storage hardware issues",
                "Incomplete backup operations",
                "Repository consistency problems"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Run comprehensive integrity check",
                    command="timelocker integrity check <repository_name> --thorough",
                    expected_result="Detailed integrity check results"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Review integrity check logs",
                    additional_info="Identify specific files or snapshots with issues"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Check storage hardware health",
                    additional_info="Run disk diagnostics to rule out hardware issues"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="If supported, attempt repository repair",
                    command="timelocker repository repair <repository_name>",
                    expected_result="Repairs repository consistency issues",
                    additional_info="Create backup before attempting repair"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="If issues persist, consider re-running affected backups",
                    additional_info="Fresh backups may be needed for corrupted data"
                )
            ],
            additional_resources=[
                "Integrity checking documentation",
                "Repository maintenance guide"
            ],
            prevention_tips=[
                "Run regular integrity checks",
                "Monitor storage hardware health",
                "Use reliable storage media",
                "Maintain multiple backup copies"
            ]
        )
    
    def _create_generic_guide(self) -> TroubleshootingGuide:
        """Create generic troubleshooting guide"""
        return TroubleshootingGuide(
            issue_type=IssueType.UNKNOWN,
            title="General Troubleshooting",
            description="General troubleshooting steps for backup issues.",
            possible_causes=[
                "Various system or configuration issues",
                "Temporary resource constraints",
                "External service problems"
            ],
            steps=[
                TroubleshootingStep(
                    step_number=1,
                    description="Review error logs for detailed information",
                    command="timelocker logs --level error --recent 24h",
                    expected_result="Shows recent errors"
                ),
                TroubleshootingStep(
                    step_number=2,
                    description="Check system resources",
                    additional_info="Verify CPU, memory, disk space, and network are available"
                ),
                TroubleshootingStep(
                    step_number=3,
                    description="Verify configuration",
                    command="timelocker config validate",
                    expected_result="Configuration is valid"
                ),
                TroubleshootingStep(
                    step_number=4,
                    description="Test with minimal operation",
                    additional_info="Try a simple operation to verify basic functionality"
                ),
                TroubleshootingStep(
                    step_number=5,
                    description="If issue persists, contact support",
                    additional_info="Provide error logs and system information"
                )
            ],
            additional_resources=[
                "General troubleshooting documentation",
                "Support contact information"
            ],
            prevention_tips=[
                "Keep system and software updated",
                "Monitor system health regularly",
                "Maintain good backup practices",
                "Document any custom configurations"
            ]
        )
    
    def validate_configuration(self) -> List[Any]:
        """
        Validate configuration and identify issues.
        
        Returns:
            List of configuration issues
            
        Requirements: 9.4
        """
        if not self.config_troubleshooter:
            logger.warning("Configuration troubleshooter not available")
            return []
        
        try:
            return self.config_troubleshooter.validate_configuration()
        except Exception as e:
            logger.error(f"Failed to validate configuration: {e}")
            return []
    
    def get_configuration_troubleshooting_guide(self, issue_type: str) -> Optional[TroubleshootingGuide]:
        """
        Get troubleshooting guide for configuration issues.
        
        Args:
            issue_type: Type of configuration issue
            
        Returns:
            Troubleshooting guide or None if not available
            
        Requirements: 9.4, 9.5
        """
        if not self.config_troubleshooter:
            logger.warning("Configuration troubleshooter not available")
            return None
        
        try:
            return self.config_troubleshooter.get_configuration_troubleshooting_guide(issue_type)
        except Exception as e:
            logger.error(f"Failed to get configuration troubleshooting guide: {e}")
            return None
    
    def get_setup_recommendations(self) -> List[ProactiveRecommendation]:
        """
        Get proactive recommendations for configuration setup.
        
        Returns:
            List of setup recommendations
            
        Requirements: 9.4, 9.5
        """
        if not self.config_troubleshooter:
            logger.warning("Configuration troubleshooter not available")
            return []
        
        try:
            return self.config_troubleshooter.get_setup_recommendations()
        except Exception as e:
            logger.error(f"Failed to get setup recommendations: {e}")
            return []
