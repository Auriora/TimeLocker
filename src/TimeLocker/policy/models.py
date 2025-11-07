"""
Core policy data models.

This module defines the data models for backup policies, retention policies,
policy assignments, and related structures using dataclasses for type safety
and consistency with the TimeLocker architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .types import (
    PolicyType,
    TargetType,
    EnforcementType,
    RetentionType,
    PolicyStatus,
    ConflictResolution,
)


@dataclass
class ScheduleConfig:
    """Configuration for scheduled policy operations."""
    
    cron_expression: Optional[str] = None  # Cron expression for scheduling
    enabled: bool = True
    timezone: str = "UTC"
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'cron_expression': self.cron_expression,
            'enabled': self.enabled,
            'timezone': self.timezone,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'last_run': self.last_run.isoformat() if self.last_run else None,
        }


@dataclass
class ComplianceRule:
    """Compliance requirement definition."""
    
    rule_id: str
    description: str
    minimum_retention_days: Optional[int] = None
    required_tags: List[str] = field(default_factory=list)
    immutable_period_days: Optional[int] = None  # Period during which snapshots cannot be deleted
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'rule_id': self.rule_id,
            'description': self.description,
            'minimum_retention_days': self.minimum_retention_days,
            'required_tags': self.required_tags,
            'immutable_period_days': self.immutable_period_days,
        }


@dataclass
class TagBasedRule:
    """Tag-based retention rule."""
    
    tag_filters: Dict[str, str]  # Tag key-value pairs to match
    retention_days: Optional[int] = None
    keep_count: Optional[int] = None
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'tag_filters': self.tag_filters,
            'retention_days': self.retention_days,
            'keep_count': self.keep_count,
            'priority': self.priority,
        }


@dataclass
class RetentionRule:
    """Individual retention rule specification."""
    
    type: RetentionType
    count: int  # Number to retain
    minimum_age: Optional[timedelta] = None  # Minimum age before eligible for pruning
    tag_filters: Optional[Dict[str, str]] = None  # Apply rule only to matching tags
    
    def __post_init__(self):
        """Validate retention rule configuration."""
        if self.count < 0:
            raise ValueError(f"Retention count must be non-negative, got {self.count}")
        if self.minimum_age is not None and self.minimum_age.total_seconds() < 0:
            raise ValueError("Minimum age must be non-negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'type': self.type.value,
            'count': self.count,
            'minimum_age': self.minimum_age.total_seconds() if self.minimum_age else None,
            'tag_filters': self.tag_filters,
        }


@dataclass
class BackupPolicy:
    """Defines comprehensive backup operation configuration."""
    
    id: str
    name: str
    description: str
    data_selection_refs: List[str]  # References to data selection configurations
    target_repositories: List[str]  # Repository identifiers
    backup_tool: str  # Tool identifier (restic, borg, etc.)
    schedule: Optional[ScheduleConfig] = None
    execution_params: Dict[str, Any] = field(default_factory=dict)
    retention_policy_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    compliance_requirements: List[ComplianceRule] = field(default_factory=list)
    status: PolicyStatus = PolicyStatus.DRAFT
    priority: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'data_selection_refs': self.data_selection_refs,
            'target_repositories': self.target_repositories,
            'backup_tool': self.backup_tool,
            'schedule': self.schedule.to_dict() if self.schedule else None,
            'execution_params': self.execution_params,
            'retention_policy_id': self.retention_policy_id,
            'tags': self.tags,
            'compliance_requirements': [cr.to_dict() for cr in self.compliance_requirements],
            'status': self.status.value,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


@dataclass
class RetentionPolicy:
    """Defines snapshot lifecycle and retention rules."""
    
    id: str
    name: str
    description: str
    rules: List[RetentionRule] = field(default_factory=list)
    compliance_period: Optional[timedelta] = None
    tag_based_rules: List[TagBasedRule] = field(default_factory=list)
    priority: int = 0
    status: PolicyStatus = PolicyStatus.DRAFT
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rules': [rule.to_dict() for rule in self.rules],
            'compliance_period': self.compliance_period.total_seconds() if self.compliance_period else None,
            'tag_based_rules': [tbr.to_dict() for tbr in self.tag_based_rules],
            'priority': self.priority,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


@dataclass
class PolicyAssignment:
    """Associates policies with specific targets."""
    
    id: str
    policy_id: str
    policy_type: PolicyType
    target_type: TargetType
    target_id: str
    priority: int = 0
    active: bool = True
    conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.assigned_at is None:
            self.assigned_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'policy_id': self.policy_id,
            'policy_type': self.policy_type.value,
            'target_type': self.target_type.value,
            'target_id': self.target_id,
            'priority': self.priority,
            'active': self.active,
            'conflict_resolution': self.conflict_resolution.value,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'assigned_by': self.assigned_by,
            'metadata': self.metadata,
        }


@dataclass
class SnapshotInfo:
    """Information about a snapshot for policy operations."""
    
    snapshot_id: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    size_bytes: Optional[int] = None
    repository_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'size_bytes': self.size_bytes,
            'repository_id': self.repository_id,
        }


@dataclass
class StorageImpact:
    """Storage impact analysis for policy operations."""
    
    snapshots_to_remove: int
    estimated_space_freed_bytes: int
    snapshots_to_retain: int
    total_retained_size_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'snapshots_to_remove': self.snapshots_to_remove,
            'estimated_space_freed_bytes': self.estimated_space_freed_bytes,
            'snapshots_to_retain': self.snapshots_to_retain,
            'total_retained_size_bytes': self.total_retained_size_bytes,
        }


@dataclass
class PolicyConflict:
    """Represents a conflict between policies."""
    
    policy_id_1: str
    policy_id_2: str
    conflict_type: str
    description: str
    resolution_strategy: Optional[ConflictResolution] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'policy_id_1': self.policy_id_1,
            'policy_id_2': self.policy_id_2,
            'conflict_type': self.conflict_type,
            'description': self.description,
            'resolution_strategy': self.resolution_strategy.value if self.resolution_strategy else None,
        }


@dataclass
class SimulationResult:
    """Results from policy simulation."""
    
    policy_id: str
    target_id: str
    simulation_time: datetime
    snapshots_to_prune: List[SnapshotInfo] = field(default_factory=list)
    snapshots_to_retain: List[SnapshotInfo] = field(default_factory=list)
    storage_impact: Optional[StorageImpact] = None
    compliance_warnings: List[str] = field(default_factory=list)
    conflicts: List[PolicyConflict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'policy_id': self.policy_id,
            'target_id': self.target_id,
            'simulation_time': self.simulation_time.isoformat(),
            'snapshots_to_prune': [s.to_dict() for s in self.snapshots_to_prune],
            'snapshots_to_retain': [s.to_dict() for s in self.snapshots_to_retain],
            'storage_impact': self.storage_impact.to_dict() if self.storage_impact else None,
            'compliance_warnings': self.compliance_warnings,
            'conflicts': [c.to_dict() for c in self.conflicts],
        }


@dataclass
class ComplianceViolation:
    """Represents a compliance rule violation."""
    
    rule_id: str
    description: str
    severity: str  # "warning", "error", "critical"
    snapshot_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'rule_id': self.rule_id,
            'description': self.description,
            'severity': self.severity,
            'snapshot_ids': self.snapshot_ids,
        }


@dataclass
class RequiredAction:
    """Represents a required action for policy compliance."""
    
    action_type: str
    description: str
    due_date: Optional[datetime] = None
    priority: str = "normal"  # "low", "normal", "high", "critical"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'action_type': self.action_type,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
        }


@dataclass
class ComplianceStatus:
    """Policy compliance assessment."""
    
    policy_id: str
    target_id: str
    compliant: bool
    violations: List[ComplianceViolation] = field(default_factory=list)
    next_required_action: Optional[RequiredAction] = None
    assessment_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.assessment_time is None:
            self.assessment_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'policy_id': self.policy_id,
            'target_id': self.target_id,
            'compliant': self.compliant,
            'violations': [v.to_dict() for v in self.violations],
            'next_required_action': self.next_required_action.to_dict() if self.next_required_action else None,
            'assessment_time': self.assessment_time.isoformat() if self.assessment_time else None,
        }


@dataclass
class EnforcementRecord:
    """Records policy enforcement execution."""
    
    id: str
    policy_id: str
    target_id: str
    enforcement_type: EnforcementType
    execution_time: datetime
    success: bool
    snapshots_affected: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'policy_id': self.policy_id,
            'target_id': self.target_id,
            'enforcement_type': self.enforcement_type.value,
            'execution_time': self.execution_time.isoformat(),
            'success': self.success,
            'snapshots_affected': self.snapshots_affected,
            'errors': self.errors,
            'metadata': self.metadata,
        }


@dataclass
class PolicyTarget:
    """Represents a target for policy operations."""
    
    target_type: TargetType
    target_id: str
    repository_uri: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'target_type': self.target_type.value,
            'target_id': self.target_id,
            'repository_uri': self.repository_uri,
            'metadata': self.metadata,
        }
