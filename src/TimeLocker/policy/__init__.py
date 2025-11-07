"""
Policy Management Module for TimeLocker.

This module provides centralized configuration and enforcement of backup
and retention policies within the TimeLocker platform.
"""

from .exceptions import (
    PolicyError,
    PolicyValidationError,
    PolicyCompatibilityError,
    PolicyEnforcementError,
    ComplianceViolationError,
    PolicyNotFoundError,
    PolicyAssignmentError,
    PolicyStorageError,
    PolicySerializationError,
)
from .models import (
    BackupPolicy,
    RetentionPolicy,
    RetentionRule,
    PolicyAssignment,
    EnforcementRecord,
    SimulationResult,
    ComplianceStatus,
    ComplianceViolation,
    RequiredAction,
    StorageImpact,
    SnapshotInfo,
    PolicyConflict,
    ScheduleConfig,
    ComplianceRule,
    TagBasedRule,
)
from .types import (
    PolicyType,
    TargetType,
    EnforcementType,
    RetentionType,
    PolicyStatus,
    ConflictResolution,
)
from .validator import (
    PolicyValidator,
    ValidationResult,
    ValidationIssue,
    CompatibilityResult,
)
from .engine import (
    PolicyEngine,
    RetentionDecision,
    PruneResult,
)
from .manager import PolicyManager
from .simulator import PolicySimulator
from .storage import (
    IPolicyStore,
    PolicySerializer,
    FileSystemPolicyStore,
)
from .integration import PolicyIntegrationService

__all__ = [
    # Exceptions
    'PolicyError',
    'PolicyValidationError',
    'PolicyCompatibilityError',
    'PolicyEnforcementError',
    'ComplianceViolationError',
    'PolicyNotFoundError',
    'PolicyAssignmentError',
    'PolicyStorageError',
    'PolicySerializationError',
    # Models
    'BackupPolicy',
    'RetentionPolicy',
    'RetentionRule',
    'PolicyAssignment',
    'EnforcementRecord',
    'SimulationResult',
    'ComplianceStatus',
    'ComplianceViolation',
    'RequiredAction',
    'StorageImpact',
    'SnapshotInfo',
    'PolicyConflict',
    'ScheduleConfig',
    'ComplianceRule',
    'TagBasedRule',
    # Types
    'PolicyType',
    'TargetType',
    'EnforcementType',
    'RetentionType',
    'PolicyStatus',
    'ConflictResolution',
    # Validator
    'PolicyValidator',
    'ValidationResult',
    'ValidationIssue',
    'CompatibilityResult',
    # Engine
    'PolicyEngine',
    'RetentionDecision',
    'PruneResult',
    # Manager
    'PolicyManager',
    # Simulator
    'PolicySimulator',
    # Storage
    'IPolicyStore',
    'PolicySerializer',
    'FileSystemPolicyStore',
    # Integration
    'PolicyIntegrationService',
]
