"""
Policy Manager - Central orchestrator for policy operations.

This module implements the PolicyManager class that serves as the main API
interface for policy management, providing CRUD operations, policy assignment,
template management, and coordination with validator and engine components.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ..selection_template_manager import (
    SelectionTemplateManager,
    TemplateNotFoundError
)
from .models import (
    BackupPolicy,
    RetentionPolicy,
    PolicyAssignment,
    ScheduleConfig,
    ComplianceRule,
    RetentionRule,
    SimulationResult,
    SnapshotInfo,
    StorageImpact,
    PolicyConflict,
    EnforcementRecord,
)
from .types import (
    PolicyType,
    TargetType,
    PolicyStatus,
    EnforcementType,
    ConflictResolution,
)
from .exceptions import (
    PolicyError,
    PolicyValidationError,
    PolicyNotFoundError,
    PolicyAssignmentError,
    PolicyCompatibilityError,
    PolicyEnforcementError,
)
from .validator import PolicyValidator
from .engine import PolicyEngine
from .storage import IPolicyStore, FileSystemPolicyStore

logger = logging.getLogger(__name__)


class PolicyManager:
    """
    Central manager for policy operations and coordination.
    
    The PolicyManager serves as the primary interface for all policy-related
    operations, including:
    - Creating and managing backup and retention policies
    - Assigning policies to repositories and backup operations
    - Managing policy templates and duplication
    - Coordinating policy validation and enforcement
    - Applying default policies
    
    This class integrates with PolicyValidator for validation and PolicyEngine
    for enforcement operations.
    """

    # Default retention policy configuration
    DEFAULT_RETENTION_POLICY = {
            'id':          'default-retention',
            'name':        'Default Retention Policy',
            'description': 'Default retention policy to prevent unlimited storage growth',
            'rules':       [
                    {'type': 'last', 'count': 7},  # Keep last 7 snapshots
                    {'type': 'daily', 'count': 7},  # Keep 7 daily snapshots
                    {'type': 'weekly', 'count': 4},  # Keep 4 weekly snapshots
                    {'type': 'monthly', 'count': 6},  # Keep 6 monthly snapshots
            ],
            'priority':    0,
            'status':      'active',
    }

    def __init__(
            self,
            validator: Optional[PolicyValidator] = None,
            engine: Optional[PolicyEngine] = None,
            repository_manager=None,
            config_manager=None,
            policy_store: Optional[IPolicyStore] = None,
            selection_template_manager: Optional[SelectionTemplateManager] = None,
    ):
        """
        Initialize the policy manager.
        
        Args:
            validator: Optional PolicyValidator instance
            engine: Optional PolicyEngine instance
            repository_manager: Optional repository manager for repository operations
            config_manager: Optional configuration manager for system configuration
            policy_store: Optional policy storage implementation
            selection_template_manager: Optional selection template manager for resolving refs
        """
        # Initialize policy storage
        self.policy_store = policy_store or FileSystemPolicyStore()
        self.selection_template_manager = selection_template_manager or SelectionTemplateManager()

        self.validator = validator or PolicyValidator(
                repository_manager=repository_manager,
                config_manager=config_manager,
                selection_template_manager=self.selection_template_manager
        )
        self.engine = engine or PolicyEngine(
                repository_service=None,
                policy_store=self.policy_store
        )
        self.repository_manager = repository_manager
        self.config_manager = config_manager

        # Load existing policies from storage
        self._backup_policies: Dict[str, BackupPolicy] = {}
        self._retention_policies: Dict[str, RetentionPolicy] = {}
        self._policy_assignments: Dict[str, PolicyAssignment] = {}

        self._load_policies_from_storage()

        # Initialize default retention policy if not already present
        self._initialize_default_retention_policy()

        logger.info("PolicyManager initialized")

    def _load_policies_from_storage(self):
        """Load existing policies from storage."""
        try:
            # Load backup policies
            backup_policies = self.policy_store.list_backup_policies()
            for policy in backup_policies:
                policy.data_selection_refs = self._normalize_selection_refs(
                        policy.data_selection_refs,
                        require_all=False
                )
                self._backup_policies[policy.id] = policy
            logger.info(f"Loaded {len(backup_policies)} backup policies from storage")

            # Load retention policies
            retention_policies = self.policy_store.list_retention_policies()
            for policy in retention_policies:
                self._retention_policies[policy.id] = policy
            logger.info(f"Loaded {len(retention_policies)} retention policies from storage")

            # Load assignments
            assignments = self.policy_store.list_assignments()
            for assignment in assignments:
                self._policy_assignments[assignment.id] = assignment
            logger.info(f"Loaded {len(assignments)} policy assignments from storage")

        except Exception as e:
            logger.error(f"Failed to load policies from storage: {e}")
            # Continue with empty storage - don't fail initialization

    def _initialize_default_retention_policy(self):
        """Initialize the default retention policy if not already present."""
        try:
            # Check if default policy already exists
            if self.DEFAULT_RETENTION_POLICY['id'] in self._retention_policies:
                logger.info("Default retention policy already exists")
                return

            default_policy = self._create_retention_policy_from_dict(
                    self.DEFAULT_RETENTION_POLICY
            )
            self._retention_policies[default_policy.id] = default_policy

            # Persist to storage
            self.policy_store.save_retention_policy(default_policy)

            logger.info(f"Initialized default retention policy: {default_policy.id}")
        except Exception as e:
            logger.error(f"Failed to initialize default retention policy: {e}")

    def _normalize_selection_refs(
            self,
            selection_refs: List[str],
            *,
            require_all: bool = True
    ) -> List[str]:
        """
        Resolve selection references to canonical template IDs.
        
        Args:
            selection_refs: Raw selection identifiers from user input or storage
            require_all: Whether to raise if any reference cannot be resolved
        
        Returns:
            List of normalized selection identifiers
        
        Raises:
            PolicyValidationError: When require_all is True and a reference cannot be resolved
        """
        if not selection_refs or self.selection_template_manager is None:
            return selection_refs

        normalized: List[str] = []
        missing: List[str] = []

        for ref in selection_refs:
            if not ref:
                continue
            try:
                template = self.selection_template_manager.resolve_template(ref)
                normalized.append(template.id)
            except TemplateNotFoundError:
                missing.append(ref)
                if not require_all:
                    # Preserve original reference so it can still be displayed/edited
                    normalized.append(ref)

        if missing:
            message = (
                f"Unknown data selection reference(s): {', '.join(missing)}"
            )
            if require_all:
                raise PolicyValidationError(message)
            logger.warning(message)

        return normalized if normalized else selection_refs

    # Backup Policy CRUD Operations

    def create_backup_policy(
            self,
            name: str,
            description: str,
            data_selection_refs: List[str],
            target_repositories: List[str],
            backup_tool: str,
            schedule: Optional[ScheduleConfig] = None,
            execution_params: Optional[Dict[str, Any]] = None,
            retention_policy_id: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None,
            compliance_requirements: Optional[List[ComplianceRule]] = None,
            priority: int = 0,
            status: PolicyStatus = PolicyStatus.DRAFT,
            created_by: Optional[str] = None,
    ) -> BackupPolicy:
        """
        Create a new backup policy with validation.
        
        Args:
            name: Policy name
            description: Policy description
            data_selection_refs: References to data selection configurations
            target_repositories: List of target repository identifiers
            backup_tool: Backup tool identifier (restic, borg, etc.)
            schedule: Optional schedule configuration
            execution_params: Optional execution parameters
            retention_policy_id: Optional retention policy to associate
            tags: Optional policy tags
            compliance_requirements: Optional compliance rules
            priority: Policy priority (default: 0)
            status: Policy status (default: DRAFT)
            created_by: Optional creator identifier
            
        Returns:
            Created BackupPolicy instance
            
        Raises:
            PolicyValidationError: If policy configuration is invalid
        """
        try:
            # Generate unique policy ID
            policy_id = str(uuid.uuid4())

            # Apply default retention policy if none specified
            if retention_policy_id is None:
                retention_policy_id = self.DEFAULT_RETENTION_POLICY['id']
                logger.info(
                        f"No retention policy specified for backup policy '{name}', "
                        f"applying default retention policy"
                )

            # Normalize selection references to canonical template IDs
            normalized_selection_refs = self._normalize_selection_refs(
                    data_selection_refs
            )

            # Create policy object
            policy = BackupPolicy(
                    id=policy_id,
                    name=name,
                    description=description,
                    data_selection_refs=normalized_selection_refs,
                    target_repositories=target_repositories,
                    backup_tool=backup_tool,
                    schedule=schedule,
                    execution_params=execution_params or {},
                    retention_policy_id=retention_policy_id,
                    tags=tags or {},
                    compliance_requirements=compliance_requirements or [],
                    priority=priority,
                    status=status,
                    created_by=created_by,
            )

            # Validate policy
            validation_result = self.validator.validate_backup_policy(policy)

            # Store policy in memory
            self._backup_policies[policy_id] = policy

            # Persist to storage
            self.policy_store.save_backup_policy(policy)

            logger.info(
                    f"Created backup policy '{name}' (ID: {policy_id}) with status {status.value}"
            )

            return policy

        except PolicyValidationError:
            raise
        except Exception as e:
            error_msg = f"Failed to create backup policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg) from e

    def get_backup_policy(self, policy_id: str) -> BackupPolicy:
        """
        Retrieve a backup policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            BackupPolicy instance
            
        Raises:
            PolicyNotFoundError: If policy does not exist
        """
        policy = self._backup_policies.get(policy_id)
        if not policy:
            raise PolicyNotFoundError(
                    f"Backup policy not found: {policy_id}",
                    policy_id=policy_id,
            )
        return policy

    def update_backup_policy(
            self,
            policy_id: str,
            **updates: Any,
    ) -> BackupPolicy:
        """
        Update an existing backup policy.
        
        Args:
            policy_id: Policy identifier
            **updates: Fields to update
            
        Returns:
            Updated BackupPolicy instance
            
        Raises:
            PolicyNotFoundError: If policy does not exist
            PolicyValidationError: If updated configuration is invalid
        """
        try:
            # Get existing policy
            policy = self.get_backup_policy(policy_id)

            # Create updated policy with new values
            policy_dict = policy.to_dict()
            policy_dict.update(updates)
            policy_dict['updated_at'] = datetime.utcnow()

            if 'data_selection_refs' in updates:
                policy_dict['data_selection_refs'] = self._normalize_selection_refs(
                        policy_dict.get('data_selection_refs', [])
                )

            # Reconstruct policy object
            updated_policy = self._create_backup_policy_from_dict(policy_dict)

            # Validate updated policy
            validation_result = self.validator.validate_backup_policy(updated_policy)

            # Store updated policy in memory
            self._backup_policies[policy_id] = updated_policy

            # Persist to storage
            self.policy_store.save_backup_policy(updated_policy)

            logger.info(f"Updated backup policy {policy_id}")

            return updated_policy

        except (PolicyNotFoundError, PolicyValidationError):
            raise
        except Exception as e:
            error_msg = f"Failed to update backup policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e

    def delete_backup_policy(self, policy_id: str, force: bool = False) -> bool:
        """
        Delete a backup policy.
        
        Args:
            policy_id: Policy identifier
            force: If True, delete even if policy has active assignments
            
        Returns:
            True if deleted successfully
            
        Raises:
            PolicyNotFoundError: If policy does not exist
            PolicyError: If policy has active assignments and force=False
        """
        try:
            # Check if policy exists
            policy = self.get_backup_policy(policy_id)

            # Check for active assignments
            if not force:
                assignments = self.get_policy_assignments(policy_id=policy_id)
                active_assignments = [a for a in assignments if a.active]
                if active_assignments:
                    raise PolicyError(
                            f"Cannot delete policy {policy_id}: has {len(active_assignments)} "
                            f"active assignments. Use force=True to delete anyway.",
                            policy_id=policy_id,
                    )

            # Delete policy from memory
            del self._backup_policies[policy_id]

            # Delete from storage
            self.policy_store.delete_backup_policy(policy_id)

            # Remove all assignments
            assignments_to_remove = [
                    aid for aid, a in self._policy_assignments.items()
                    if a.policy_id == policy_id
            ]
            for aid in assignments_to_remove:
                del self._policy_assignments[aid]
                # Delete from storage
                self.policy_store.delete_assignment(aid)

            logger.info(
                    f"Deleted backup policy {policy_id} and {len(assignments_to_remove)} assignments"
            )

            return True

        except (PolicyNotFoundError, PolicyError):
            raise
        except Exception as e:
            error_msg = f"Failed to delete backup policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e

    def list_backup_policies(
            self,
            status: Optional[PolicyStatus] = None,
            backup_tool: Optional[str] = None,
    ) -> List[BackupPolicy]:
        """
        List backup policies with optional filtering.
        
        Args:
            status: Optional filter by policy status
            backup_tool: Optional filter by backup tool
            
        Returns:
            List of BackupPolicy instances matching filters
        """
        policies = list(self._backup_policies.values())

        if status:
            policies = [p for p in policies if p.status == status]
        if backup_tool:
            policies = [p for p in policies if p.backup_tool == backup_tool]

        return policies

    # Retention Policy CRUD Operations

    def create_retention_policy(
            self,
            name: str,
            description: str,
            rules: List[RetentionRule],
            priority: int = 0,
            status: PolicyStatus = PolicyStatus.DRAFT,
            created_by: Optional[str] = None,
    ) -> RetentionPolicy:
        """
        Create a new retention policy with validation.
        
        Args:
            name: Policy name
            description: Policy description
            rules: List of retention rules
            priority: Policy priority (default: 0)
            status: Policy status (default: DRAFT)
            created_by: Optional creator identifier
            
        Returns:
            Created RetentionPolicy instance
            
        Raises:
            PolicyValidationError: If policy configuration is invalid
        """
        try:
            # Generate unique policy ID
            policy_id = str(uuid.uuid4())

            # Create policy object
            policy = RetentionPolicy(
                    id=policy_id,
                    name=name,
                    description=description,
                    rules=rules,
                    priority=priority,
                    status=status,
                    created_by=created_by,
            )

            # Validate policy
            validation_result = self.validator.validate_retention_policy(policy)

            # Store policy in memory
            self._retention_policies[policy_id] = policy

            # Persist to storage
            self.policy_store.save_retention_policy(policy)

            logger.info(
                    f"Created retention policy '{name}' (ID: {policy_id}) with {len(rules)} rules"
            )

            return policy

        except PolicyValidationError:
            raise
        except Exception as e:
            error_msg = f"Failed to create retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg) from e

    def get_retention_policy(self, policy_id: str) -> RetentionPolicy:
        """
        Retrieve a retention policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            RetentionPolicy instance
            
        Raises:
            PolicyNotFoundError: If policy does not exist
        """
        policy = self._retention_policies.get(policy_id)
        if not policy:
            raise PolicyNotFoundError(
                    f"Retention policy not found: {policy_id}",
                    policy_id=policy_id,
            )
        return policy

    def update_retention_policy(
            self,
            policy_id: str,
            **updates: Any,
    ) -> RetentionPolicy:
        """
        Update an existing retention policy.
        
        Args:
            policy_id: Policy identifier
            **updates: Fields to update
            
        Returns:
            Updated RetentionPolicy instance
            
        Raises:
            PolicyNotFoundError: If policy does not exist
            PolicyValidationError: If updated configuration is invalid
        """
        try:
            # Get existing policy
            policy = self.get_retention_policy(policy_id)

            # Create updated policy with new values
            policy_dict = policy.to_dict()
            policy_dict.update(updates)
            policy_dict['updated_at'] = datetime.utcnow()

            # Reconstruct policy object
            updated_policy = self._create_retention_policy_from_dict(policy_dict)

            # Validate updated policy
            validation_result = self.validator.validate_retention_policy(updated_policy)

            # Store updated policy in memory
            self._retention_policies[policy_id] = updated_policy

            # Persist to storage
            self.policy_store.save_retention_policy(updated_policy)

            logger.info(f"Updated retention policy {policy_id}")

            return updated_policy

        except (PolicyNotFoundError, PolicyValidationError):
            raise
        except Exception as e:
            error_msg = f"Failed to update retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e

    def delete_retention_policy(self, policy_id: str, force: bool = False) -> bool:
        """
        Delete a retention policy.
        
        Args:
            policy_id: Policy identifier
            force: If True, delete even if policy is referenced by backup policies
            
        Returns:
            True if deleted successfully
            
        Raises:
            PolicyNotFoundError: If policy does not exist
            PolicyError: If policy is referenced and force=False
        """
        try:
            # Check if policy exists
            policy = self.get_retention_policy(policy_id)

            # Prevent deletion of default policy
            if policy_id == self.DEFAULT_RETENTION_POLICY['id']:
                raise PolicyError(
                        "Cannot delete default retention policy",
                        policy_id=policy_id,
                )

            # Check for references from backup policies
            if not force:
                referencing_policies = [
                        p for p in self._backup_policies.values()
                        if p.retention_policy_id == policy_id
                ]
                if referencing_policies:
                    raise PolicyError(
                            f"Cannot delete retention policy {policy_id}: referenced by "
                            f"{len(referencing_policies)} backup policies. Use force=True to delete anyway.",
                            policy_id=policy_id,
                    )

            # Delete policy from memory
            del self._retention_policies[policy_id]

            # Delete from storage
            self.policy_store.delete_retention_policy(policy_id)

            logger.info(f"Deleted retention policy {policy_id}")

            return True

        except (PolicyNotFoundError, PolicyError):
            raise
        except Exception as e:
            error_msg = f"Failed to delete retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e

    def list_retention_policies(
            self,
            status: Optional[PolicyStatus] = None,
    ) -> List[RetentionPolicy]:
        """
        List retention policies with optional filtering.
        
        Args:
            status: Optional filter by policy status
            
        Returns:
            List of RetentionPolicy instances matching filters
        """
        policies = list(self._retention_policies.values())

        if status:
            policies = [p for p in policies if p.status == status]

        return policies

    # Policy Assignment Operations

    def assign_policy(
            self,
            policy_id: str,
            policy_type: PolicyType,
            target_type: TargetType,
            target_id: str,
            priority: int = 0,
            active: bool = True,
            conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY,
            assigned_by: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyAssignment:
        """
        Assign a policy to repositories or backup operations.
        
        Args:
            policy_id: Policy identifier
            policy_type: Type of policy (BACKUP or RETENTION)
            target_type: Type of target (REPOSITORY, BACKUP_JOB, etc.)
            target_id: Target identifier
            priority: Assignment priority (default: 0)
            active: Whether assignment is active (default: True)
            conflict_resolution: Strategy for resolving conflicts
            assigned_by: Optional assigner identifier
            metadata: Optional additional metadata
            
        Returns:
            Created PolicyAssignment instance
            
        Raises:
            PolicyNotFoundError: If policy does not exist
            PolicyValidationError: If assignment is invalid
            PolicyAssignmentError: If assignment conflicts with existing assignments
        """
        try:
            # Verify policy exists
            if policy_type == PolicyType.BACKUP:
                policy = self.get_backup_policy(policy_id)
            elif policy_type == PolicyType.RETENTION:
                policy = self.get_retention_policy(policy_id)
            else:
                raise PolicyError(f"Unsupported policy type: {policy_type}")

            # Generate unique assignment ID
            assignment_id = str(uuid.uuid4())

            # Create assignment object
            assignment = PolicyAssignment(
                    id=assignment_id,
                    policy_id=policy_id,
                    policy_type=policy_type,
                    target_type=target_type,
                    target_id=target_id,
                    priority=priority,
                    active=active,
                    conflict_resolution=conflict_resolution,
                    assigned_by=assigned_by,
                    metadata=metadata or {},
            )

            # Validate assignment
            validation_result = self.validator.validate_policy_assignment(
                    assignment,
                    policy=policy if policy_type == PolicyType.BACKUP else None,
            )

            # Check for conflicts with existing assignments
            conflicts = self._check_assignment_conflicts(assignment)
            if conflicts:
                logger.warning(
                        f"Assignment has {len(conflicts)} conflicts, "
                        f"using resolution strategy: {conflict_resolution.value}"
                )

            # Store assignment in memory
            self._policy_assignments[assignment_id] = assignment

            # Persist to storage
            self.policy_store.save_assignment(assignment)

            logger.info(
                    f"Assigned {policy_type.value} policy {policy_id} to "
                    f"{target_type.value} {target_id} (assignment ID: {assignment_id})"
            )

            return assignment

        except (PolicyNotFoundError, PolicyValidationError):
            raise
        except Exception as e:
            error_msg = f"Failed to assign policy: {e}"
            logger.error(error_msg)
            raise PolicyAssignmentError(
                    error_msg,
                    policy_id=policy_id,
                    target_id=target_id,
            ) from e

    def unassign_policy(self, assignment_id: str) -> bool:
        """
        Remove a policy assignment.
        
        Args:
            assignment_id: Assignment identifier
            
        Returns:
            True if unassigned successfully
            
        Raises:
            PolicyNotFoundError: If assignment does not exist
        """
        if assignment_id not in self._policy_assignments:
            raise PolicyNotFoundError(
                    f"Policy assignment not found: {assignment_id}",
                    policy_id=assignment_id,
            )

        assignment = self._policy_assignments[assignment_id]

        # Delete from memory
        del self._policy_assignments[assignment_id]

        # Delete from storage
        self.policy_store.delete_assignment(assignment_id)

        logger.info(
                f"Unassigned policy {assignment.policy_id} from "
                f"{assignment.target_type.value} {assignment.target_id}"
        )

        return True

    def get_policy_assignments(
            self,
            policy_id: Optional[str] = None,
            target_id: Optional[str] = None,
            target_type: Optional[TargetType] = None,
            active_only: bool = False,
    ) -> List[PolicyAssignment]:
        """
        Retrieve policy assignments with optional filtering.
        
        Args:
            policy_id: Optional filter by policy ID
            target_id: Optional filter by target ID
            target_type: Optional filter by target type
            active_only: If True, return only active assignments
            
        Returns:
            List of PolicyAssignment instances matching filters
        """
        assignments = list(self._policy_assignments.values())

        if policy_id:
            assignments = [a for a in assignments if a.policy_id == policy_id]
        if target_id:
            assignments = [a for a in assignments if a.target_id == target_id]
        if target_type:
            assignments = [a for a in assignments if a.target_type == target_type]
        if active_only:
            assignments = [a for a in assignments if a.active]

        return assignments

    def update_assignment_status(
            self,
            assignment_id: str,
            active: bool,
    ) -> PolicyAssignment:
        """
        Update the active status of a policy assignment.
        
        Args:
            assignment_id: Assignment identifier
            active: New active status
            
        Returns:
            Updated PolicyAssignment instance
            
        Raises:
            PolicyNotFoundError: If assignment does not exist
        """
        if assignment_id not in self._policy_assignments:
            raise PolicyNotFoundError(
                    f"Policy assignment not found: {assignment_id}",
                    policy_id=assignment_id,
            )

        assignment = self._policy_assignments[assignment_id]
        assignment.active = active

        logger.info(
                f"Updated assignment {assignment_id} status to "
                f"{'active' if active else 'inactive'}"
        )

        return assignment

    # Policy Template and Duplication

    def duplicate_backup_policy(
            self,
            source_policy_id: str,
            new_name: str,
            new_description: Optional[str] = None,
            status: PolicyStatus = PolicyStatus.DRAFT,
    ) -> BackupPolicy:
        """
        Create a duplicate of an existing backup policy.
        
        Args:
            source_policy_id: ID of policy to duplicate
            new_name: Name for the new policy
            new_description: Optional new description
            status: Status for the new policy (default: DRAFT)
            
        Returns:
            New BackupPolicy instance
            
        Raises:
            PolicyNotFoundError: If source policy does not exist
        """
        try:
            # Get source policy
            source_policy = self.get_backup_policy(source_policy_id)

            # Create new policy with duplicated configuration
            new_policy = self.create_backup_policy(
                    name=new_name,
                    description=new_description or f"Copy of {source_policy.description}",
                    data_selection_refs=source_policy.data_selection_refs.copy(),
                    target_repositories=source_policy.target_repositories.copy(),
                    backup_tool=source_policy.backup_tool,
                    schedule=source_policy.schedule,
                    execution_params=source_policy.execution_params.copy(),
                    retention_policy_id=source_policy.retention_policy_id,
                    tags=source_policy.tags.copy(),
                    compliance_requirements=source_policy.compliance_requirements.copy(),
                    priority=source_policy.priority,
                    status=status,
            )

            logger.info(
                    f"Duplicated backup policy {source_policy_id} to new policy {new_policy.id}"
            )

            return new_policy

        except PolicyNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to duplicate backup policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=source_policy_id) from e

    def duplicate_retention_policy(
            self,
            source_policy_id: str,
            new_name: str,
            new_description: Optional[str] = None,
            status: PolicyStatus = PolicyStatus.DRAFT,
    ) -> RetentionPolicy:
        """
        Create a duplicate of an existing retention policy.
        
        Args:
            source_policy_id: ID of policy to duplicate
            new_name: Name for the new policy
            new_description: Optional new description
            status: Status for the new policy (default: DRAFT)
            
        Returns:
            New RetentionPolicy instance
            
        Raises:
            PolicyNotFoundError: If source policy does not exist
        """
        try:
            # Get source policy
            source_policy = self.get_retention_policy(source_policy_id)

            # Create new policy with duplicated configuration
            new_policy = self.create_retention_policy(
                    name=new_name,
                    description=new_description or f"Copy of {source_policy.description}",
                    rules=source_policy.rules.copy(),
                    priority=source_policy.priority,
                    status=status,
            )

            logger.info(
                    f"Duplicated retention policy {source_policy_id} to new policy {new_policy.id}"
            )

            return new_policy

        except PolicyNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to duplicate retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=source_policy_id) from e

    def create_policy_template(
            self,
            template_name: str,
            policy_id: str,
            policy_type: PolicyType,
    ) -> Dict[str, Any]:
        """
        Create a reusable policy template from an existing policy.
        
        Args:
            template_name: Name for the template
            policy_id: ID of policy to use as template
            policy_type: Type of policy (BACKUP or RETENTION)
            
        Returns:
            Template configuration dictionary
            
        Raises:
            PolicyNotFoundError: If policy does not exist
        """
        try:
            # Get policy
            if policy_type == PolicyType.BACKUP:
                policy = self.get_backup_policy(policy_id)
            elif policy_type == PolicyType.RETENTION:
                policy = self.get_retention_policy(policy_id)
            else:
                raise PolicyError(f"Unsupported policy type: {policy_type}")

            # Create template from policy configuration
            template = {
                    'template_name':    template_name,
                    'policy_type':      policy_type.value,
                    'created_at':       datetime.utcnow().isoformat(),
                    'source_policy_id': policy_id,
                    'configuration':    policy.to_dict(),
            }

            logger.info(
                    f"Created policy template '{template_name}' from "
                    f"{policy_type.value} policy {policy_id}"
            )

            return template

        except PolicyNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to create policy template: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e

    # Default Policy Application

    def apply_default_retention_policy(
            self,
            target_type: TargetType,
            target_id: str,
    ) -> PolicyAssignment:
        """
        Apply the default retention policy to a target.
        
        Args:
            target_type: Type of target
            target_id: Target identifier
            
        Returns:
            Created PolicyAssignment instance
        """
        try:
            default_policy_id = self.DEFAULT_RETENTION_POLICY['id']

            assignment = self.assign_policy(
                    policy_id=default_policy_id,
                    policy_type=PolicyType.RETENTION,
                    target_type=target_type,
                    target_id=target_id,
                    priority=0,
                    active=True,
                    assigned_by='system',
                    metadata={'is_default': True},
            )

            logger.info(
                    f"Applied default retention policy to {target_type.value} {target_id}"
            )

            return assignment

        except Exception as e:
            error_msg = f"Failed to apply default retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg) from e

    def get_effective_policies(
            self,
            target_type: TargetType,
            target_id: str,
    ) -> Dict[str, Any]:
        """
        Get the effective policies for a target, resolving conflicts.
        
        Args:
            target_type: Type of target
            target_id: Target identifier
            
        Returns:
            Dictionary with effective backup and retention policies
        """
        # Get all active assignments for this target
        assignments = self.get_policy_assignments(
                target_id=target_id,
                target_type=target_type,
                active_only=True,
        )

        # Separate by policy type
        backup_assignments = [
                a for a in assignments
                if a.policy_type == PolicyType.BACKUP
        ]
        retention_assignments = [
                a for a in assignments
                if a.policy_type == PolicyType.RETENTION
        ]

        # Resolve conflicts by priority (highest priority wins)
        effective_backup = None
        if backup_assignments:
            backup_assignments.sort(key=lambda a: a.priority, reverse=True)
            effective_backup = self.get_backup_policy(backup_assignments[0].policy_id)

        effective_retention = None
        if retention_assignments:
            retention_assignments.sort(key=lambda a: a.priority, reverse=True)
            effective_retention = self.get_retention_policy(retention_assignments[0].policy_id)

        return {
                'backup_policy':        effective_backup,
                'retention_policy':     effective_retention,
                'backup_assignment':    backup_assignments[0] if backup_assignments else None,
                'retention_assignment': retention_assignments[0] if retention_assignments else None,
        }

    # Helper Methods

    def _check_assignment_conflicts(
            self,
            new_assignment: PolicyAssignment,
    ) -> List[PolicyConflict]:
        """
        Check for conflicts with existing assignments.
        
        Args:
            new_assignment: Assignment to check
            
        Returns:
            List of PolicyConflict objects
        """
        conflicts = []

        # Get existing assignments for the same target
        existing = self.get_policy_assignments(
                target_id=new_assignment.target_id,
                target_type=new_assignment.target_type,
                active_only=True,
        )

        # Check for conflicts with same policy type
        for assignment in existing:
            if assignment.policy_type == new_assignment.policy_type:
                conflict = PolicyConflict(
                        policy_id_1=assignment.policy_id,
                        policy_id_2=new_assignment.policy_id,
                        conflict_type="duplicate_assignment",
                        description=(
                                f"Multiple {new_assignment.policy_type.value} policies "
                                f"assigned to same target"
                        ),
                        resolution_strategy=new_assignment.conflict_resolution,
                )
                conflicts.append(conflict)

        return conflicts

    def _create_backup_policy_from_dict(self, data: Dict[str, Any]) -> BackupPolicy:
        """Create BackupPolicy instance from dictionary."""
        from .types import PolicyStatus
        from datetime import datetime

        # Convert string status to enum
        if isinstance(data.get('status'), str):
            data['status'] = PolicyStatus(data['status'])

        # Convert ISO format timestamps to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # Handle schedule
        if data.get('schedule') and isinstance(data['schedule'], dict):
            data['schedule'] = ScheduleConfig(**data['schedule'])

        # Handle compliance requirements
        if data.get('compliance_requirements'):
            data['compliance_requirements'] = [
                    ComplianceRule(**cr) if isinstance(cr, dict) else cr
                    for cr in data['compliance_requirements']
            ]

        return BackupPolicy(**data)

    def _create_retention_policy_from_dict(self, data: Dict[str, Any]) -> RetentionPolicy:
        """Create RetentionPolicy instance from dictionary."""
        from .types import PolicyStatus, RetentionType
        from datetime import datetime, timedelta

        # Convert string status to enum
        if isinstance(data.get('status'), str):
            data['status'] = PolicyStatus(data['status'])

        # Convert ISO format timestamps to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # Handle rules
        if data.get('rules'):
            rules = []
            for rule_data in data['rules']:
                if isinstance(rule_data, dict):
                    # Convert type string to enum
                    if isinstance(rule_data.get('type'), str):
                        rule_data['type'] = RetentionType(rule_data['type'])
                    # Convert minimum_age seconds to timedelta
                    if rule_data.get('minimum_age') is not None:
                        rule_data['minimum_age'] = timedelta(seconds=rule_data['minimum_age'])
                    rules.append(RetentionRule(**rule_data))
                else:
                    rules.append(rule_data)
            data['rules'] = rules

        # Handle compliance_period
        if data.get('compliance_period') is not None:
            if isinstance(data['compliance_period'], (int, float)):
                data['compliance_period'] = timedelta(seconds=data['compliance_period'])

        return RetentionPolicy(**data)

    def list_all_assignments(self) -> List[PolicyAssignment]:
        """
        List all policy assignments.
        
        Returns:
            List of all policy assignments
        """
        try:
            return self.policy_store.list_assignments()
        except Exception as e:
            logger.error(f"Failed to list all assignments: {e}")
            raise PolicyError(f"Failed to list assignments: {e}") from e

    def get_assignments_for_target(self, target_id: str) -> List[PolicyAssignment]:
        """
        Get all policy assignments for a specific target.
        
        Args:
            target_id: Target identifier
            
        Returns:
            List of policy assignments for the target
        """
        try:
            all_assignments = self.policy_store.list_assignments()
            return [a for a in all_assignments if a.target_id == target_id]
        except Exception as e:
            logger.error(f"Failed to get assignments for target {target_id}: {e}")
            raise PolicyError(f"Failed to get assignments for target: {e}") from e

    def delete_assignment(self, assignment_id: str) -> bool:
        """
        Delete a policy assignment.
        
        Args:
            assignment_id: Assignment ID to delete
            
        Returns:
            True if deleted successfully
        """
        return self.unassign_policy(assignment_id)

    def simulate_policy(self, policy_id: str, target: 'PolicyTarget') -> 'SimulationResult':
        """
        Simulate a specific policy for a target.

        Args:
            policy_id: ID of the policy to simulate
            target: Target for simulation

        Returns:
            Simulation result
        """
        if not hasattr(self, 'simulator') or self.simulator is None:
            raise PolicyError("Policy simulator not initialized")
        return self.simulator.simulate_policy(policy_id, target)

    def simulate_all_policies(self, target: 'PolicyTarget') -> 'SimulationResult':
        """
        Simulate all applicable policies for a target.

        Args:
            target: Target for simulation

        Returns:
            Simulation result
        """
        try:
            # Get all assignments for the target
            assignments = self.get_assignments_for_target(target.target_id)

            if not assignments:
                # Return empty simulation result
                from .models import SimulationResult, StorageImpact
                return SimulationResult(
                        policy_id=None,
                        target_id=target.target_id,
                        simulation_time=datetime.now(),
                        snapshots_to_prune=[],
                        snapshots_to_retain=[],
                        storage_impact=StorageImpact(bytes_freed=0, snapshots_removed=0),
                        compliance_warnings=[],
                        conflicts=[]
                )

            # Simulate the highest priority policy
            active_assignments = [a for a in assignments if a.active]
            if not active_assignments:
                from .models import SimulationResult, StorageImpact
                return SimulationResult(
                        policy_id=None,
                        target_id=target.target_id,
                        simulation_time=datetime.now(),
                        snapshots_to_prune=[],
                        snapshots_to_retain=[],
                        storage_impact=StorageImpact(bytes_freed=0, snapshots_removed=0),
                        compliance_warnings=["No active policies found for target"],
                        conflicts=[]
                )

            # Sort by priority and simulate the highest priority policy
            active_assignments.sort(key=lambda a: a.priority, reverse=True)
            highest_priority = active_assignments[0]

            return self.simulator.simulate_policy(highest_priority.policy_id, target)
        except Exception as e:
            logger.error(f"Failed to simulate all policies for target {target.target_id}: {e}")
            raise PolicyError(f"Failed to simulate policies: {e}") from e

    def enforce_policies(self, context: 'EnforcementContext') -> EnforcementRecord:
        """
        Enforce policies based on enforcement context.
        
        Args:
            context: Enforcement context
            
        Returns:
            Enforcement record
        """
        try:
            from .models import EnforcementRecord
            from .types import EnforcementType

            # Get assignments for the repository
            assignments = self.get_assignments_for_target(context.repository_id)

            if not assignments:
                logger.warning(f"No policy assignments found for repository {context.repository_id}")
                return EnforcementRecord(
                        id=str(uuid.uuid4()),
                        policy_id="none",
                        target_id=context.repository_id,
                        enforcement_type=EnforcementType.RETENTION,
                        execution_time=datetime.now(),
                        success=True,
                        snapshots_affected=[],
                        errors=["No policies assigned to repository"],
                        metadata=context.metadata
                )

            # Filter by policy IDs if specified
            if context.policy_ids:
                assignments = [a for a in assignments if a.policy_id in context.policy_ids]

            # Filter active assignments
            active_assignments = [a for a in assignments if a.active]
            if not active_assignments:
                logger.warning(f"No active policy assignments found for repository {context.repository_id}")
                return EnforcementRecord(
                        id=str(uuid.uuid4()),
                        policy_id="none",
                        target_id=context.repository_id,
                        enforcement_type=EnforcementType.RETENTION,
                        execution_time=datetime.now(),
                        success=True,
                        snapshots_affected=[],
                        errors=["No active policies found"],
                        metadata=context.metadata
                )

            # Sort by priority and enforce the highest priority retention policy
            active_assignments.sort(key=lambda a: a.priority, reverse=True)

            # Find the first retention policy
            retention_assignment = None
            for assignment in active_assignments:
                if assignment.policy_type == PolicyType.RETENTION:
                    retention_assignment = assignment
                    break

            if not retention_assignment:
                logger.warning(f"No retention policy assigned to repository {context.repository_id}")
                return EnforcementRecord(
                        id=str(uuid.uuid4()),
                        policy_id="none",
                        target_id=context.repository_id,
                        enforcement_type=EnforcementType.RETENTION,
                        execution_time=datetime.now(),
                        success=True,
                        snapshots_affected=[],
                        errors=["No retention policy assigned"],
                        metadata=context.metadata
                )

            # Get the retention policy
            retention_policy = self.get_retention_policy(retention_assignment.policy_id)

            # Enforce the policy using the engine
            # For now, return a placeholder record
            # Full implementation would integrate with repository service
            logger.info(f"Enforcing retention policy {retention_policy.id} on repository {context.repository_id}")

            return EnforcementRecord(
                    id=str(uuid.uuid4()),
                    policy_id=retention_policy.id,
                    target_id=context.repository_id,
                    enforcement_type=EnforcementType.RETENTION,
                    execution_time=datetime.now(),
                    success=True,
                    snapshots_affected=[],
                    errors=[],
                    metadata={
                            **context.metadata,
                            'dry_run':     context.dry_run,
                            'policy_name': retention_policy.name,
                    }
            )
        except Exception as e:
            logger.error(f"Failed to enforce policies: {e}")
            raise PolicyEnforcementError(f"Policy enforcement failed: {e}") from e

    def get_enforcement_history(
            self,
            policy_id: Optional[str] = None,
            target_id: Optional[str] = None,
            limit: int = 50
    ) -> List[EnforcementRecord]:
        """
        Get policy enforcement history.
        
        Args:
            policy_id: Optional policy ID filter
            target_id: Optional target ID filter
            limit: Maximum number of records to return
            
        Returns:
            List of enforcement records
        """
        try:
            # Get enforcement records from storage
            records = self.policy_store.list_enforcement_records(
                    policy_id=policy_id,
                    target_id=target_id
            )
            # Apply limit
            return records[:limit] if records else []
        except Exception as e:
            logger.error(f"Failed to get enforcement history: {e}")
            # Return empty list if storage doesn't support enforcement records yet
            return []
