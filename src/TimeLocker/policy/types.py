"""
Policy-specific enums and type definitions.

This module defines the enumeration types used throughout the policy
management system for type safety and consistency.
"""

from enum import Enum


class PolicyType(Enum):
    """Types of policies supported by the system."""
    BACKUP = "backup"
    RETENTION = "retention"
    COMBINED = "combined"  # Backup policy with embedded retention rules


class TargetType(Enum):
    """Types of targets that policies can be assigned to."""
    REPOSITORY = "repository"
    BACKUP_JOB = "backup_job"
    BACKUP_TARGET = "backup_target"
    SYSTEM = "system"  # System-wide default policy


class EnforcementType(Enum):
    """Types of policy enforcement operations."""
    SCHEDULED = "scheduled"  # Automatic scheduled enforcement
    MANUAL = "manual"  # User-triggered enforcement
    BACKUP_TRIGGERED = "backup_triggered"  # Triggered after backup completion
    MAINTENANCE = "maintenance"  # Maintenance window enforcement
    SIMULATION = "simulation"  # Dry-run simulation


class RetentionType(Enum):
    """Types of retention rules for snapshot lifecycle management."""
    LAST = "last"  # Keep N most recent snapshots
    HOURLY = "hourly"  # Keep N hourly snapshots
    DAILY = "daily"  # Keep N daily snapshots
    WEEKLY = "weekly"  # Keep N weekly snapshots
    MONTHLY = "monthly"  # Keep N monthly snapshots
    YEARLY = "yearly"  # Keep N yearly snapshots
    TAG_BASED = "tag_based"  # Keep based on snapshot tags


class PolicyStatus(Enum):
    """Status of a policy."""
    ACTIVE = "active"  # Policy is active and enforced
    INACTIVE = "inactive"  # Policy exists but not enforced
    DRAFT = "draft"  # Policy is being configured
    ARCHIVED = "archived"  # Policy is archived and read-only
    ERROR = "error"  # Policy has validation or enforcement errors


class ConflictResolution(Enum):
    """Strategies for resolving policy conflicts."""
    PRIORITY = "priority"  # Use policy with highest priority
    MOST_RESTRICTIVE = "most_restrictive"  # Apply most restrictive rules
    LEAST_RESTRICTIVE = "least_restrictive"  # Apply least restrictive rules
    MERGE = "merge"  # Merge compatible rules
    FAIL = "fail"  # Fail on conflict
