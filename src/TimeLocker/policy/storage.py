"""
Policy storage and persistence layer.

This module provides storage interfaces and implementations for policy data,
including policies, assignments, and audit trails. It integrates with the
existing TimeLocker configuration management patterns.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    BackupPolicy,
    RetentionPolicy,
    PolicyAssignment,
    EnforcementRecord,
    ScheduleConfig,
    ComplianceRule,
    TagBasedRule,
    RetentionRule,
)
from .types import (
    PolicyType,
    TargetType,
    EnforcementType,
    RetentionType,
    PolicyStatus,
    ConflictResolution,
)
from .exceptions import (
    PolicyStorageError,
    PolicyNotFoundError,
    PolicySerializationError,
)

logger = logging.getLogger(__name__)


class IPolicyStore:
    """Interface for policy storage operations."""
    
    def save_backup_policy(self, policy: BackupPolicy) -> bool:
        """Save a backup policy."""
        raise NotImplementedError
    
    def load_backup_policy(self, policy_id: str) -> Optional[BackupPolicy]:
        """Load a backup policy by ID."""
        raise NotImplementedError
    
    def delete_backup_policy(self, policy_id: str) -> bool:
        """Delete a backup policy."""
        raise NotImplementedError
    
    def list_backup_policies(self) -> List[BackupPolicy]:
        """List all backup policies."""
        raise NotImplementedError
    
    def save_retention_policy(self, policy: RetentionPolicy) -> bool:
        """Save a retention policy."""
        raise NotImplementedError
    
    def load_retention_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Load a retention policy by ID."""
        raise NotImplementedError
    
    def delete_retention_policy(self, policy_id: str) -> bool:
        """Delete a retention policy."""
        raise NotImplementedError
    
    def list_retention_policies(self) -> List[RetentionPolicy]:
        """List all retention policies."""
        raise NotImplementedError
    
    def save_assignment(self, assignment: PolicyAssignment) -> bool:
        """Save a policy assignment."""
        raise NotImplementedError
    
    def load_assignment(self, assignment_id: str) -> Optional[PolicyAssignment]:
        """Load a policy assignment by ID."""
        raise NotImplementedError
    
    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete a policy assignment."""
        raise NotImplementedError
    
    def list_assignments(
        self,
        policy_id: Optional[str] = None,
        target_id: Optional[str] = None,
        active_only: bool = False
    ) -> List[PolicyAssignment]:
        """List policy assignments with optional filtering."""
        raise NotImplementedError
    
    def save_enforcement_record(self, record: EnforcementRecord) -> bool:
        """Save an enforcement record to audit trail."""
        raise NotImplementedError
    
    def load_enforcement_record(self, record_id: str) -> Optional[EnforcementRecord]:
        """Load an enforcement record by ID."""
        raise NotImplementedError
    
    def list_enforcement_records(
        self,
        policy_id: Optional[str] = None,
        target_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[EnforcementRecord]:
        """List enforcement records with optional filtering."""
        raise NotImplementedError


class PolicySerializer:
    """Handles serialization and deserialization of policy objects."""
    
    @staticmethod
    def serialize_backup_policy(policy: BackupPolicy) -> Dict[str, Any]:
        """Serialize a backup policy to dictionary."""
        try:
            return policy.to_dict()
        except Exception as e:
            logger.error(f"Failed to serialize backup policy {policy.id}: {e}")
            raise PolicySerializationError(f"Failed to serialize backup policy: {e}")
    
    @staticmethod
    def deserialize_backup_policy(data: Dict[str, Any]) -> BackupPolicy:
        """Deserialize a backup policy from dictionary."""
        try:
            # Parse schedule if present
            schedule = None
            if data.get('schedule'):
                schedule_data = data['schedule']
                schedule = ScheduleConfig(
                    cron_expression=schedule_data.get('cron_expression'),
                    enabled=schedule_data.get('enabled', True),
                    timezone=schedule_data.get('timezone', 'UTC'),
                    next_run=datetime.fromisoformat(schedule_data['next_run']) if schedule_data.get('next_run') else None,
                    last_run=datetime.fromisoformat(schedule_data['last_run']) if schedule_data.get('last_run') else None,
                )
            
            # Parse compliance requirements
            compliance_requirements = []
            for cr_data in data.get('compliance_requirements', []):
                compliance_requirements.append(ComplianceRule(
                    rule_id=cr_data['rule_id'],
                    description=cr_data['description'],
                    minimum_retention_days=cr_data.get('minimum_retention_days'),
                    required_tags=cr_data.get('required_tags', []),
                    immutable_period_days=cr_data.get('immutable_period_days'),
                ))
            
            return BackupPolicy(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                data_selection_refs=data.get('data_selection_refs', []),
                target_repositories=data.get('target_repositories', []),
                backup_tool=data['backup_tool'],
                schedule=schedule,
                execution_params=data.get('execution_params', {}),
                retention_policy_id=data.get('retention_policy_id'),
                tags=data.get('tags', {}),
                compliance_requirements=compliance_requirements,
                status=PolicyStatus(data.get('status', 'draft')),
                priority=data.get('priority', 0),
                created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
                updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
                created_by=data.get('created_by'),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize backup policy: {e}")
            raise PolicySerializationError(f"Failed to deserialize backup policy: {e}")
    
    @staticmethod
    def serialize_retention_policy(policy: RetentionPolicy) -> Dict[str, Any]:
        """Serialize a retention policy to dictionary."""
        try:
            return policy.to_dict()
        except Exception as e:
            logger.error(f"Failed to serialize retention policy {policy.id}: {e}")
            raise PolicySerializationError(f"Failed to serialize retention policy: {e}")
    
    @staticmethod
    def deserialize_retention_policy(data: Dict[str, Any]) -> RetentionPolicy:
        """Deserialize a retention policy from dictionary."""
        try:
            # Parse retention rules
            rules = []
            for rule_data in data.get('rules', []):
                rules.append(RetentionRule(
                    type=RetentionType(rule_data['type']),
                    count=rule_data['count'],
                    minimum_age=timedelta(seconds=rule_data['minimum_age']) if rule_data.get('minimum_age') else None,
                    tag_filters=rule_data.get('tag_filters'),
                ))
            
            # Parse tag-based rules
            tag_based_rules = []
            for tbr_data in data.get('tag_based_rules', []):
                tag_based_rules.append(TagBasedRule(
                    tag_filters=tbr_data['tag_filters'],
                    retention_days=tbr_data.get('retention_days'),
                    keep_count=tbr_data.get('keep_count'),
                    priority=tbr_data.get('priority', 0),
                ))
            
            return RetentionPolicy(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                rules=rules,
                compliance_period=timedelta(seconds=data['compliance_period']) if data.get('compliance_period') else None,
                tag_based_rules=tag_based_rules,
                priority=data.get('priority', 0),
                status=PolicyStatus(data.get('status', 'draft')),
                created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
                updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
                created_by=data.get('created_by'),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize retention policy: {e}")
            raise PolicySerializationError(f"Failed to deserialize retention policy: {e}")
    
    @staticmethod
    def serialize_assignment(assignment: PolicyAssignment) -> Dict[str, Any]:
        """Serialize a policy assignment to dictionary."""
        try:
            return assignment.to_dict()
        except Exception as e:
            logger.error(f"Failed to serialize assignment {assignment.id}: {e}")
            raise PolicySerializationError(f"Failed to serialize assignment: {e}")
    
    @staticmethod
    def deserialize_assignment(data: Dict[str, Any]) -> PolicyAssignment:
        """Deserialize a policy assignment from dictionary."""
        try:
            return PolicyAssignment(
                id=data['id'],
                policy_id=data['policy_id'],
                policy_type=PolicyType(data['policy_type']),
                target_type=TargetType(data['target_type']),
                target_id=data['target_id'],
                priority=data.get('priority', 0),
                active=data.get('active', True),
                conflict_resolution=ConflictResolution(data.get('conflict_resolution', 'priority')),
                assigned_at=datetime.fromisoformat(data['assigned_at']) if data.get('assigned_at') else None,
                assigned_by=data.get('assigned_by'),
                metadata=data.get('metadata', {}),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize assignment: {e}")
            raise PolicySerializationError(f"Failed to deserialize assignment: {e}")
    
    @staticmethod
    def serialize_enforcement_record(record: EnforcementRecord) -> Dict[str, Any]:
        """Serialize an enforcement record to dictionary."""
        try:
            return record.to_dict()
        except Exception as e:
            logger.error(f"Failed to serialize enforcement record {record.id}: {e}")
            raise PolicySerializationError(f"Failed to serialize enforcement record: {e}")
    
    @staticmethod
    def deserialize_enforcement_record(data: Dict[str, Any]) -> EnforcementRecord:
        """Deserialize an enforcement record from dictionary."""
        try:
            return EnforcementRecord(
                id=data['id'],
                policy_id=data['policy_id'],
                target_id=data['target_id'],
                enforcement_type=EnforcementType(data['enforcement_type']),
                execution_time=datetime.fromisoformat(data['execution_time']),
                success=data['success'],
                snapshots_affected=data.get('snapshots_affected', []),
                errors=data.get('errors', []),
                metadata=data.get('metadata', {}),
            )
        except Exception as e:
            logger.error(f"Failed to deserialize enforcement record: {e}")
            raise PolicySerializationError(f"Failed to deserialize enforcement record: {e}")


class FileSystemPolicyStore(IPolicyStore):
    """
    File system-based policy storage implementation.
    
    Stores policies, assignments, and audit trails in JSON files within
    the TimeLocker configuration directory structure.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the file system policy store.
        
        Args:
            config_dir: Configuration directory path (defaults to ~/.config/timelocker)
        """
        if config_dir is None:
            config_dir = Path.home() / ".config" / "timelocker"
        
        self.config_dir = Path(config_dir)
        self.policy_dir = self.config_dir / "policies"
        self.backup_policies_dir = self.policy_dir / "backup"
        self.retention_policies_dir = self.policy_dir / "retention"
        self.assignments_dir = self.policy_dir / "assignments"
        self.audit_dir = self.policy_dir / "audit"
        
        # Create directory structure
        self._ensure_directories()
        
        self.serializer = PolicySerializer()
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for directory in [
            self.backup_policies_dir,
            self.retention_policies_dir,
            self.assignments_dir,
            self.audit_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _get_policy_file(self, policy_id: str, policy_type: str) -> Path:
        """Get the file path for a policy."""
        if policy_type == "backup":
            return self.backup_policies_dir / f"{policy_id}.json"
        elif policy_type == "retention":
            return self.retention_policies_dir / f"{policy_id}.json"
        else:
            raise ValueError(f"Unknown policy type: {policy_type}")
    
    def _get_assignment_file(self, assignment_id: str) -> Path:
        """Get the file path for an assignment."""
        return self.assignments_dir / f"{assignment_id}.json"
    
    def _get_audit_file(self, record_id: str) -> Path:
        """Get the file path for an audit record."""
        return self.audit_dir / f"{record_id}.json"
    
    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Save data to JSON file atomically."""
        try:
            # Write to temporary file first
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            temp_file.replace(file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            return False
    
    def _load_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load data from JSON file."""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {file_path}: {e}")
            return None
    
    # Backup Policy Operations
    
    def save_backup_policy(self, policy: BackupPolicy) -> bool:
        """Save a backup policy."""
        try:
            data = self.serializer.serialize_backup_policy(policy)
            file_path = self._get_policy_file(policy.id, "backup")
            return self._save_json(file_path, data)
        except Exception as e:
            logger.error(f"Failed to save backup policy {policy.id}: {e}")
            raise PolicyStorageError(f"Failed to save backup policy: {e}")
    
    def load_backup_policy(self, policy_id: str) -> Optional[BackupPolicy]:
        """Load a backup policy by ID."""
        try:
            file_path = self._get_policy_file(policy_id, "backup")
            data = self._load_json(file_path)
            if data is None:
                return None
            return self.serializer.deserialize_backup_policy(data)
        except Exception as e:
            logger.error(f"Failed to load backup policy {policy_id}: {e}")
            raise PolicyStorageError(f"Failed to load backup policy: {e}")
    
    def delete_backup_policy(self, policy_id: str) -> bool:
        """Delete a backup policy."""
        try:
            file_path = self._get_policy_file(policy_id, "backup")
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup policy {policy_id}: {e}")
            raise PolicyStorageError(f"Failed to delete backup policy: {e}")
    
    def list_backup_policies(self) -> List[BackupPolicy]:
        """List all backup policies."""
        try:
            policies = []
            for file_path in self.backup_policies_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    try:
                        policy = self.serializer.deserialize_backup_policy(data)
                        policies.append(policy)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize policy from {file_path}: {e}")
            return policies
        except Exception as e:
            logger.error(f"Failed to list backup policies: {e}")
            raise PolicyStorageError(f"Failed to list backup policies: {e}")
    
    # Retention Policy Operations
    
    def save_retention_policy(self, policy: RetentionPolicy) -> bool:
        """Save a retention policy."""
        try:
            data = self.serializer.serialize_retention_policy(policy)
            file_path = self._get_policy_file(policy.id, "retention")
            return self._save_json(file_path, data)
        except Exception as e:
            logger.error(f"Failed to save retention policy {policy.id}: {e}")
            raise PolicyStorageError(f"Failed to save retention policy: {e}")
    
    def load_retention_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Load a retention policy by ID."""
        try:
            file_path = self._get_policy_file(policy_id, "retention")
            data = self._load_json(file_path)
            if data is None:
                return None
            return self.serializer.deserialize_retention_policy(data)
        except Exception as e:
            logger.error(f"Failed to load retention policy {policy_id}: {e}")
            raise PolicyStorageError(f"Failed to load retention policy: {e}")
    
    def delete_retention_policy(self, policy_id: str) -> bool:
        """Delete a retention policy."""
        try:
            file_path = self._get_policy_file(policy_id, "retention")
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete retention policy {policy_id}: {e}")
            raise PolicyStorageError(f"Failed to delete retention policy: {e}")
    
    def list_retention_policies(self) -> List[RetentionPolicy]:
        """List all retention policies."""
        try:
            policies = []
            for file_path in self.retention_policies_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    try:
                        policy = self.serializer.deserialize_retention_policy(data)
                        policies.append(policy)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize policy from {file_path}: {e}")
            return policies
        except Exception as e:
            logger.error(f"Failed to list retention policies: {e}")
            raise PolicyStorageError(f"Failed to list retention policies: {e}")
    
    # Assignment Operations
    
    def save_assignment(self, assignment: PolicyAssignment) -> bool:
        """Save a policy assignment."""
        try:
            data = self.serializer.serialize_assignment(assignment)
            file_path = self._get_assignment_file(assignment.id)
            return self._save_json(file_path, data)
        except Exception as e:
            logger.error(f"Failed to save assignment {assignment.id}: {e}")
            raise PolicyStorageError(f"Failed to save assignment: {e}")
    
    def load_assignment(self, assignment_id: str) -> Optional[PolicyAssignment]:
        """Load a policy assignment by ID."""
        try:
            file_path = self._get_assignment_file(assignment_id)
            data = self._load_json(file_path)
            if data is None:
                return None
            return self.serializer.deserialize_assignment(data)
        except Exception as e:
            logger.error(f"Failed to load assignment {assignment_id}: {e}")
            raise PolicyStorageError(f"Failed to load assignment: {e}")
    
    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete a policy assignment."""
        try:
            file_path = self._get_assignment_file(assignment_id)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete assignment {assignment_id}: {e}")
            raise PolicyStorageError(f"Failed to delete assignment: {e}")
    
    def list_assignments(
        self,
        policy_id: Optional[str] = None,
        target_id: Optional[str] = None,
        active_only: bool = False
    ) -> List[PolicyAssignment]:
        """List policy assignments with optional filtering."""
        try:
            assignments = []
            for file_path in self.assignments_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    try:
                        assignment = self.serializer.deserialize_assignment(data)
                        
                        # Apply filters
                        if policy_id and assignment.policy_id != policy_id:
                            continue
                        if target_id and assignment.target_id != target_id:
                            continue
                        if active_only and not assignment.active:
                            continue
                        
                        assignments.append(assignment)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize assignment from {file_path}: {e}")
            return assignments
        except Exception as e:
            logger.error(f"Failed to list assignments: {e}")
            raise PolicyStorageError(f"Failed to list assignments: {e}")
    
    # Audit Trail Operations
    
    def save_enforcement_record(self, record: EnforcementRecord) -> bool:
        """Save an enforcement record to audit trail."""
        try:
            data = self.serializer.serialize_enforcement_record(record)
            file_path = self._get_audit_file(record.id)
            return self._save_json(file_path, data)
        except Exception as e:
            logger.error(f"Failed to save enforcement record {record.id}: {e}")
            raise PolicyStorageError(f"Failed to save enforcement record: {e}")
    
    def load_enforcement_record(self, record_id: str) -> Optional[EnforcementRecord]:
        """Load an enforcement record by ID."""
        try:
            file_path = self._get_audit_file(record_id)
            data = self._load_json(file_path)
            if data is None:
                return None
            return self.serializer.deserialize_enforcement_record(data)
        except Exception as e:
            logger.error(f"Failed to load enforcement record {record_id}: {e}")
            raise PolicyStorageError(f"Failed to load enforcement record: {e}")
    
    def list_enforcement_records(
        self,
        policy_id: Optional[str] = None,
        target_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[EnforcementRecord]:
        """List enforcement records with optional filtering."""
        try:
            records = []
            for file_path in self.audit_dir.glob("*.json"):
                data = self._load_json(file_path)
                if data:
                    try:
                        record = self.serializer.deserialize_enforcement_record(data)
                        
                        # Apply filters
                        if policy_id and record.policy_id != policy_id:
                            continue
                        if target_id and record.target_id != target_id:
                            continue
                        if start_time and record.execution_time < start_time:
                            continue
                        if end_time and record.execution_time > end_time:
                            continue
                        
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize record from {file_path}: {e}")
            
            # Sort by execution time (most recent first)
            records.sort(key=lambda r: r.execution_time, reverse=True)
            return records
        except Exception as e:
            logger.error(f"Failed to list enforcement records: {e}")
            raise PolicyStorageError(f"Failed to list enforcement records: {e}")
