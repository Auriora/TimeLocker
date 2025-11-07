"""
Policy Simulator for dry-run operations and preview capabilities.

This module implements the PolicySimulator class that provides simulation
and preview functionality for policy operations, allowing administrators to
see the effects of policies before actual enforcement.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from ..backup_repository import BackupRepository
from ..backup_snapshot import BackupSnapshot
from .models import (
    RetentionPolicy,
    BackupPolicy,
    PolicyAssignment,
    SimulationResult,
    SnapshotInfo,
    StorageImpact,
    PolicyConflict,
)
from .types import PolicyType, TargetType, ConflictResolution
from .exceptions import PolicyError, PolicyValidationError
from .engine import PolicyEngine, RetentionDecision

logger = logging.getLogger(__name__)


class PolicySimulator:
    """
    Provides simulation and preview capabilities for policy operations.
    
    The PolicySimulator allows administrators to:
    - Preview the effects of retention policies before enforcement
    - Simulate policy assignments and detect conflicts
    - Analyze storage impact of policy changes
    - Validate policy configurations in a safe environment
    """
    
    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        """
        Initialize the policy simulator.
        
        Args:
            policy_engine: Optional PolicyEngine instance for evaluation logic
        """
        self.policy_engine = policy_engine or PolicyEngine()
    
    def simulate_retention_policy(
        self,
        policy: RetentionPolicy,
        repository: BackupRepository,
        target_id: str,
    ) -> SimulationResult:
        """
        Simulate retention policy enforcement on a repository.
        
        This method performs a dry-run of retention policy enforcement,
        showing which snapshots would be retained or pruned without
        actually modifying the repository.
        
        Args:
            policy: Retention policy to simulate
            repository: Repository to simulate against
            target_id: Target identifier for the simulation
            
        Returns:
            SimulationResult with detailed preview information
            
        Raises:
            PolicyError: If simulation fails
        """
        try:
            logger.info(
                f"Simulating retention policy '{policy.name}' (ID: {policy.id}) "
                f"on repository '{repository.name}'"
            )
            
            # Get all snapshots from repository
            snapshots = repository.list_snapshots()
            
            if not snapshots:
                logger.info("No snapshots found in repository")
                return SimulationResult(
                    policy_id=policy.id,
                    target_id=target_id,
                    simulation_time=datetime.utcnow(),
                    snapshots_to_prune=[],
                    snapshots_to_retain=[],
                    storage_impact=StorageImpact(
                        snapshots_to_remove=0,
                        estimated_space_freed_bytes=0,
                        snapshots_to_retain=0,
                        total_retained_size_bytes=0,
                    ),
                    compliance_warnings=[],
                    conflicts=[],
                )
            
            # Evaluate retention rules
            retention_decisions = self.policy_engine.evaluate_retention_rules(
                snapshots, policy
            )
            
            # Separate snapshots into prune and retain lists
            snapshots_to_prune = []
            snapshots_to_retain = []
            
            for decision in retention_decisions:
                snapshot_info = self._create_snapshot_info(decision.snapshot)
                
                if decision.should_retain:
                    snapshots_to_retain.append(snapshot_info)
                else:
                    snapshots_to_prune.append(snapshot_info)
            
            # Calculate storage impact
            storage_impact = self._calculate_storage_impact(
                snapshots_to_prune, snapshots_to_retain
            )
            
            # Check for compliance warnings
            compliance_warnings = self._check_compliance_warnings(
                policy, retention_decisions
            )
            
            result = SimulationResult(
                policy_id=policy.id,
                target_id=target_id,
                simulation_time=datetime.utcnow(),
                snapshots_to_prune=snapshots_to_prune,
                snapshots_to_retain=snapshots_to_retain,
                storage_impact=storage_impact,
                compliance_warnings=compliance_warnings,
                conflicts=[],
            )
            
            logger.info(
                f"Simulation complete: {len(snapshots_to_retain)} to retain, "
                f"{len(snapshots_to_prune)} to prune, "
                f"~{storage_impact.estimated_space_freed_bytes} bytes to free"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to simulate retention policy: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy.id) from e
    
    def preview_policy_assignment(
        self,
        policy: RetentionPolicy,
        target_type: TargetType,
        target_id: str,
        existing_assignments: Optional[List[PolicyAssignment]] = None,
    ) -> SimulationResult:
        """
        Preview the effects of assigning a policy to a target.
        
        This method shows what would happen if a policy is assigned to a
        target, including conflict detection with existing assignments.
        
        Args:
            policy: Policy to preview
            target_type: Type of target for assignment
            target_id: Target identifier
            existing_assignments: Optional list of existing policy assignments
            
        Returns:
            SimulationResult with preview information and conflicts
            
        Raises:
            PolicyError: If preview fails
        """
        try:
            logger.info(
                f"Previewing assignment of policy '{policy.name}' to "
                f"{target_type.value} '{target_id}'"
            )
            
            # Detect conflicts with existing assignments
            conflicts = []
            if existing_assignments:
                conflicts = self.detect_policy_conflicts(
                    policy, existing_assignments, target_type, target_id
                )
            
            # Create basic simulation result
            result = SimulationResult(
                policy_id=policy.id,
                target_id=target_id,
                simulation_time=datetime.utcnow(),
                snapshots_to_prune=[],
                snapshots_to_retain=[],
                storage_impact=None,
                compliance_warnings=[],
                conflicts=conflicts,
            )
            
            if conflicts:
                logger.warning(
                    f"Found {len(conflicts)} conflict(s) with existing assignments"
                )
            else:
                logger.info("No conflicts detected with existing assignments")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to preview policy assignment: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy.id) from e
    
    def detect_policy_conflicts(
        self,
        new_policy: RetentionPolicy,
        existing_assignments: List[PolicyAssignment],
        target_type: TargetType,
        target_id: str,
    ) -> List[PolicyConflict]:
        """
        Detect conflicts between a new policy and existing assignments.
        
        This method identifies overlapping policy assignments and determines
        if they would conflict when applied to the same target.
        
        Args:
            new_policy: New policy being assigned
            existing_assignments: List of existing policy assignments
            target_type: Type of target for the new assignment
            target_id: Target identifier
            
        Returns:
            List of PolicyConflict objects describing conflicts
        """
        conflicts = []
        
        try:
            logger.debug(
                f"Checking for conflicts with {len(existing_assignments)} "
                f"existing assignments"
            )
            
            for assignment in existing_assignments:
                # Check if assignment applies to the same target
                if not self._assignments_overlap(
                    assignment, target_type, target_id
                ):
                    continue
                
                # Check if it's the same policy type
                if assignment.policy_type != PolicyType.RETENTION:
                    continue
                
                # Found an overlapping assignment
                conflict_type = self._determine_conflict_type(
                    new_policy, assignment
                )
                
                if conflict_type:
                    conflict = PolicyConflict(
                        policy_id_1=new_policy.id,
                        policy_id_2=assignment.policy_id,
                        conflict_type=conflict_type,
                        description=self._create_conflict_description(
                            new_policy, assignment, conflict_type
                        ),
                        resolution_strategy=assignment.conflict_resolution,
                    )
                    conflicts.append(conflict)
                    logger.debug(
                        f"Detected {conflict_type} conflict between "
                        f"{new_policy.id} and {assignment.policy_id}"
                    )
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting policy conflicts: {e}")
            return conflicts
    
    def simulate_conflict_resolution(
        self,
        conflicts: List[PolicyConflict],
        policies: Dict[str, RetentionPolicy],
        resolution_strategy: ConflictResolution,
    ) -> Dict[str, Any]:
        """
        Simulate how conflicts would be resolved with a given strategy.
        
        Args:
            conflicts: List of policy conflicts
            policies: Dictionary mapping policy IDs to policy objects
            resolution_strategy: Strategy to use for resolution
            
        Returns:
            Dictionary with resolution details
        """
        try:
            logger.info(
                f"Simulating conflict resolution for {len(conflicts)} conflicts "
                f"using strategy: {resolution_strategy.value}"
            )
            
            resolution_results = []
            
            for conflict in conflicts:
                policy1 = policies.get(conflict.policy_id_1)
                policy2 = policies.get(conflict.policy_id_2)
                
                if not policy1 or not policy2:
                    logger.warning(
                        f"Cannot resolve conflict: missing policy data"
                    )
                    continue
                
                # Determine which policy would be applied
                winning_policy = self._resolve_conflict(
                    policy1, policy2, resolution_strategy
                )
                
                resolution_results.append({
                    'conflict': conflict.to_dict(),
                    'winning_policy_id': winning_policy.id,
                    'winning_policy_name': winning_policy.name,
                    'resolution_strategy': resolution_strategy.value,
                })
            
            return {
                'conflicts_resolved': len(resolution_results),
                'resolution_strategy': resolution_strategy.value,
                'resolutions': resolution_results,
            }
            
        except Exception as e:
            error_msg = f"Failed to simulate conflict resolution: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg) from e
    
    def compare_policies(
        self,
        policy1: RetentionPolicy,
        policy2: RetentionPolicy,
        snapshots: List[BackupSnapshot],
    ) -> Dict[str, Any]:
        """
        Compare the effects of two different retention policies.
        
        This method simulates both policies on the same set of snapshots
        and provides a comparison of their effects.
        
        Args:
            policy1: First retention policy
            policy2: Second retention policy
            snapshots: Snapshots to evaluate against both policies
            
        Returns:
            Dictionary with comparison results
        """
        try:
            logger.info(
                f"Comparing policies '{policy1.name}' and '{policy2.name}' "
                f"on {len(snapshots)} snapshots"
            )
            
            # Evaluate both policies
            decisions1 = self.policy_engine.evaluate_retention_rules(
                snapshots, policy1
            )
            decisions2 = self.policy_engine.evaluate_retention_rules(
                snapshots, policy2
            )
            
            # Analyze differences
            retain1 = {d.snapshot.id for d in decisions1 if d.should_retain}
            retain2 = {d.snapshot.id for d in decisions2 if d.should_retain}
            
            only_in_policy1 = retain1 - retain2
            only_in_policy2 = retain2 - retain1
            in_both = retain1 & retain2
            
            # Calculate storage differences
            size1 = sum(
                d.snapshot.size_bytes or 0
                for d in decisions1
                if d.should_retain and d.snapshot.size_bytes
            )
            size2 = sum(
                d.snapshot.size_bytes or 0
                for d in decisions2
                if d.should_retain and d.snapshot.size_bytes
            )
            
            comparison = {
                'policy1': {
                    'id': policy1.id,
                    'name': policy1.name,
                    'snapshots_retained': len(retain1),
                    'estimated_size_bytes': size1,
                },
                'policy2': {
                    'id': policy2.id,
                    'name': policy2.name,
                    'snapshots_retained': len(retain2),
                    'estimated_size_bytes': size2,
                },
                'differences': {
                    'snapshots_only_in_policy1': len(only_in_policy1),
                    'snapshots_only_in_policy2': len(only_in_policy2),
                    'snapshots_in_both': len(in_both),
                    'size_difference_bytes': abs(size1 - size2),
                },
            }
            
            logger.info(
                f"Comparison complete: Policy1 retains {len(retain1)}, "
                f"Policy2 retains {len(retain2)}, "
                f"{len(in_both)} in common"
            )
            
            return comparison
            
        except Exception as e:
            error_msg = f"Failed to compare policies: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg) from e
    
    def _create_snapshot_info(self, snapshot: BackupSnapshot) -> SnapshotInfo:
        """
        Create SnapshotInfo from BackupSnapshot.
        
        Args:
            snapshot: BackupSnapshot object
            
        Returns:
            SnapshotInfo object
        """
        return SnapshotInfo(
            snapshot_id=snapshot.id,
            timestamp=snapshot.timestamp,
            tags=snapshot.tags or {},
            size_bytes=snapshot.size_bytes,
            repository_id=getattr(snapshot.repository, 'name', None),
        )
    
    def _calculate_storage_impact(
        self,
        snapshots_to_prune: List[SnapshotInfo],
        snapshots_to_retain: List[SnapshotInfo],
    ) -> StorageImpact:
        """
        Calculate storage impact of policy enforcement.
        
        Args:
            snapshots_to_prune: Snapshots that would be removed
            snapshots_to_retain: Snapshots that would be kept
            
        Returns:
            StorageImpact with size estimates
        """
        space_freed = sum(
            s.size_bytes for s in snapshots_to_prune if s.size_bytes
        )
        space_retained = sum(
            s.size_bytes for s in snapshots_to_retain if s.size_bytes
        )
        
        return StorageImpact(
            snapshots_to_remove=len(snapshots_to_prune),
            estimated_space_freed_bytes=space_freed,
            snapshots_to_retain=len(snapshots_to_retain),
            total_retained_size_bytes=space_retained,
        )
    
    def _check_compliance_warnings(
        self,
        policy: RetentionPolicy,
        retention_decisions: List[RetentionDecision],
    ) -> List[str]:
        """
        Check for compliance warnings in retention decisions.
        
        Args:
            policy: Retention policy being applied
            retention_decisions: List of retention decisions
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check if compliance period is defined
        if policy.compliance_period:
            min_age = datetime.utcnow() - policy.compliance_period
            
            for decision in retention_decisions:
                if not decision.should_retain:
                    if decision.snapshot.timestamp > min_age:
                        warnings.append(
                            f"Snapshot {decision.snapshot.id} from "
                            f"{decision.snapshot.timestamp} is within "
                            f"compliance period but marked for removal"
                        )
        
        # Check if all snapshots would be removed
        retained_count = sum(1 for d in retention_decisions if d.should_retain)
        if retained_count == 0 and len(retention_decisions) > 0:
            warnings.append(
                "Warning: All snapshots would be removed by this policy"
            )
        
        return warnings
    
    def _assignments_overlap(
        self,
        assignment: PolicyAssignment,
        target_type: TargetType,
        target_id: str,
    ) -> bool:
        """
        Check if an assignment overlaps with a target.
        
        Args:
            assignment: Existing policy assignment
            target_type: Target type to check
            target_id: Target ID to check
            
        Returns:
            True if the assignment applies to the target
        """
        # Direct match
        if (assignment.target_type == target_type and
            assignment.target_id == target_id):
            return True
        
        # System-wide policies apply to everything
        if assignment.target_type == TargetType.SYSTEM:
            return True
        
        return False
    
    def _determine_conflict_type(
        self,
        new_policy: RetentionPolicy,
        assignment: PolicyAssignment,
    ) -> Optional[str]:
        """
        Determine the type of conflict between policies.
        
        Args:
            new_policy: New policy being assigned
            assignment: Existing policy assignment
            
        Returns:
            Conflict type string or None if no conflict
        """
        # If it's the same policy, no conflict
        if new_policy.id == assignment.policy_id:
            return None
        
        # Different policies on same target = overlap conflict
        return "overlapping_assignment"
    
    def _create_conflict_description(
        self,
        new_policy: RetentionPolicy,
        assignment: PolicyAssignment,
        conflict_type: str,
    ) -> str:
        """
        Create a human-readable conflict description.
        
        Args:
            new_policy: New policy being assigned
            assignment: Existing policy assignment
            conflict_type: Type of conflict
            
        Returns:
            Conflict description string
        """
        if conflict_type == "overlapping_assignment":
            return (
                f"Policy '{new_policy.name}' (ID: {new_policy.id}) would "
                f"overlap with existing assignment of policy "
                f"{assignment.policy_id} on {assignment.target_type.value} "
                f"'{assignment.target_id}'"
            )
        
        return f"Conflict of type '{conflict_type}' detected"
    
    def _resolve_conflict(
        self,
        policy1: RetentionPolicy,
        policy2: RetentionPolicy,
        strategy: ConflictResolution,
    ) -> RetentionPolicy:
        """
        Resolve conflict between two policies using a strategy.
        
        Args:
            policy1: First policy
            policy2: Second policy
            strategy: Resolution strategy
            
        Returns:
            The winning policy based on strategy
        """
        if strategy == ConflictResolution.PRIORITY:
            # Higher priority wins
            return policy1 if policy1.priority >= policy2.priority else policy2
        
        elif strategy == ConflictResolution.MOST_RESTRICTIVE:
            # Policy that retains more snapshots is more restrictive
            total_retention1 = sum(rule.count for rule in policy1.rules)
            total_retention2 = sum(rule.count for rule in policy2.rules)
            return policy1 if total_retention1 >= total_retention2 else policy2
        
        elif strategy == ConflictResolution.LEAST_RESTRICTIVE:
            # Policy that retains fewer snapshots is less restrictive
            total_retention1 = sum(rule.count for rule in policy1.rules)
            total_retention2 = sum(rule.count for rule in policy2.rules)
            return policy1 if total_retention1 <= total_retention2 else policy2
        
        else:
            # Default to priority
            return policy1 if policy1.priority >= policy2.priority else policy2
