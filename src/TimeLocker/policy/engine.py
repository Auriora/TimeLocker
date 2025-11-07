"""
Policy Engine for enforcement operations.

This module implements the PolicyEngine class that handles policy execution,
enforcement, and coordination with backup tools and repositories. It integrates
with the existing retention logic and repository services for safe operations.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..backup_repository import BackupRepository
from ..backup_snapshot import BackupSnapshot
from ..retention import select_snapshots_to_remove
from .models import (
    RetentionPolicy,
    BackupPolicy,
    EnforcementRecord,
    SnapshotInfo,
    ComplianceStatus,
    ComplianceViolation,
    RequiredAction,
    RetentionRule,
)
from .types import EnforcementType, RetentionType
from .exceptions import (
    PolicyEnforcementError,
    ComplianceViolationError,
    PolicyError,
)

logger = logging.getLogger(__name__)


class RetentionDecision:
    """Represents a decision about snapshot retention."""
    
    def __init__(
        self,
        snapshot: BackupSnapshot,
        should_retain: bool,
        reason: str,
        rule_applied: Optional[str] = None,
    ):
        """
        Initialize retention decision.
        
        Args:
            snapshot: The snapshot being evaluated
            should_retain: Whether the snapshot should be retained
            reason: Reason for the decision
            rule_applied: Name of the retention rule that was applied
        """
        self.snapshot = snapshot
        self.should_retain = should_retain
        self.reason = reason
        self.rule_applied = rule_applied
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'snapshot_id': self.snapshot.id,
            'timestamp': self.snapshot.timestamp.isoformat(),
            'should_retain': self.should_retain,
            'reason': self.reason,
            'rule_applied': self.rule_applied,
        }


class PruneResult:
    """Results from snapshot pruning operation."""
    
    def __init__(
        self,
        success: bool,
        snapshots_removed: List[str],
        snapshots_failed: List[Tuple[str, str]],
        space_freed_bytes: int = 0,
        errors: Optional[List[str]] = None,
    ):
        """
        Initialize prune result.
        
        Args:
            success: Whether the operation succeeded overall
            snapshots_removed: List of snapshot IDs that were removed
            snapshots_failed: List of (snapshot_id, error_message) tuples for failures
            space_freed_bytes: Estimated space freed by pruning
            errors: List of error messages
        """
        self.success = success
        self.snapshots_removed = snapshots_removed
        self.snapshots_failed = snapshots_failed
        self.space_freed_bytes = space_freed_bytes
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""


class EnforcementContext:
    """Context for policy enforcement operations."""
    
    def __init__(
        self,
        repository_id: str,
        repository_uri: str,
        policy_ids: Optional[List[str]] = None,
        dry_run: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize enforcement context.
        
        Args:
            repository_id: Repository identifier
            repository_uri: Repository URI
            policy_ids: Optional list of specific policy IDs to enforce
            dry_run: Whether this is a dry run (no actual changes)
            metadata: Additional context metadata
        """
        self.repository_id = repository_id
        self.repository_uri = repository_uri
        self.policy_ids = policy_ids or []
        self.dry_run = dry_run
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'success': self.success,
            'snapshots_removed': self.snapshots_removed,
            'snapshots_failed': [
                {'snapshot_id': sid, 'error': err}
                for sid, err in self.snapshots_failed
            ],
            'space_freed_bytes': self.space_freed_bytes,
            'errors': self.errors,
        }


class PolicyEngine:
    """
    Executes policy enforcement and coordinates with backup systems.
    
    The PolicyEngine is responsible for:
    - Evaluating retention rules against snapshots
    - Coordinating snapshot pruning with backup tools
    - Tracking enforcement results and audit logs
    - Validating compliance requirements
    """
    
    def __init__(self, repository_service=None, policy_store=None):
        """
        Initialize the policy engine.
        
        Args:
            repository_service: Optional repository service for advanced operations
            policy_store: Optional policy storage for persisting enforcement records
        """
        self.repository_service = repository_service
        self.policy_store = policy_store
        self._enforcement_history: List[EnforcementRecord] = []
    
    def evaluate_retention_rules(
        self,
        snapshots: List[BackupSnapshot],
        policy: RetentionPolicy,
    ) -> List[RetentionDecision]:
        """
        Evaluate which snapshots should be retained or pruned based on policy.
        
        This method uses the existing retention.py logic to determine which
        snapshots should be removed according to the retention policy rules.
        
        Args:
            snapshots: List of snapshots to evaluate
            policy: Retention policy to apply
            
        Returns:
            List of RetentionDecision objects for each snapshot
            
        Raises:
            PolicyEnforcementError: If evaluation fails
        """
        try:
            if not snapshots:
                logger.info("No snapshots to evaluate")
                return []
            
            logger.info(
                f"Evaluating retention rules for {len(snapshots)} snapshots "
                f"using policy '{policy.name}' (ID: {policy.id})"
            )
            
            # Build retention parameters from policy rules
            retention_params = self._build_retention_params(policy.rules)
            
            # Use existing retention logic to select snapshots for removal
            snapshots_to_remove = select_snapshots_to_remove(
                snapshots,
                **retention_params
            )
            
            # Create set of snapshot IDs to remove for quick lookup
            remove_ids = {s.id for s in snapshots_to_remove}
            
            # Build retention decisions for all snapshots
            decisions = []
            for snapshot in snapshots:
                should_retain = snapshot.id not in remove_ids
                
                if should_retain:
                    reason = self._determine_retention_reason(
                        snapshot, policy.rules, snapshots
                    )
                    rule_applied = self._find_applied_rule(snapshot, policy.rules)
                else:
                    reason = "Snapshot does not match any retention rule"
                    rule_applied = None
                
                decision = RetentionDecision(
                    snapshot=snapshot,
                    should_retain=should_retain,
                    reason=reason,
                    rule_applied=rule_applied,
                )
                decisions.append(decision)
            
            retained_count = sum(1 for d in decisions if d.should_retain)
            removed_count = len(decisions) - retained_count
            
            logger.info(
                f"Retention evaluation complete: {retained_count} to retain, "
                f"{removed_count} to remove"
            )
            
            return decisions
            
        except Exception as e:
            error_msg = f"Failed to evaluate retention rules: {e}"
            logger.error(error_msg)
            raise PolicyEnforcementError(
                error_msg,
                policy_id=policy.id,
                enforcement_type="retention_evaluation",
            ) from e
    
    def _build_retention_params(self, rules: List[RetentionRule]) -> Dict[str, int]:
        """
        Build retention parameters for the retention module.
        
        Args:
            rules: List of retention rules from policy
            
        Returns:
            Dictionary of retention parameters
        """
        params = {
            'keep_last': 0,
            'keep_daily': 0,
            'keep_weekly': 0,
            'keep_monthly': 0,
            'keep_yearly': 0,
        }
        
        for rule in rules:
            if rule.type == RetentionType.LAST:
                params['keep_last'] = max(params['keep_last'], rule.count)
            elif rule.type == RetentionType.DAILY:
                params['keep_daily'] = max(params['keep_daily'], rule.count)
            elif rule.type == RetentionType.WEEKLY:
                params['keep_weekly'] = max(params['keep_weekly'], rule.count)
            elif rule.type == RetentionType.MONTHLY:
                params['keep_monthly'] = max(params['keep_monthly'], rule.count)
            elif rule.type == RetentionType.YEARLY:
                params['keep_yearly'] = max(params['keep_yearly'], rule.count)
        
        return params
    
    def _determine_retention_reason(
        self,
        snapshot: BackupSnapshot,
        rules: List[RetentionRule],
        all_snapshots: List[BackupSnapshot],
    ) -> str:
        """
        Determine why a snapshot is being retained.
        
        Args:
            snapshot: The snapshot being retained
            rules: List of retention rules
            all_snapshots: All snapshots being evaluated
            
        Returns:
            Human-readable reason for retention
        """
        # Sort snapshots by timestamp (newest first)
        sorted_snapshots = sorted(
            all_snapshots,
            key=lambda s: s.timestamp,
            reverse=True
        )
        
        # Check if it's in the "last N" snapshots
        for rule in rules:
            if rule.type == RetentionType.LAST:
                if snapshot in sorted_snapshots[:rule.count]:
                    return f"Retained as one of the last {rule.count} snapshots"
        
        # Check time-based retention
        snapshot_date = snapshot.timestamp.date()
        for rule in rules:
            if rule.type == RetentionType.DAILY:
                return f"Retained for daily retention (keep {rule.count} days)"
            elif rule.type == RetentionType.WEEKLY:
                return f"Retained for weekly retention (keep {rule.count} weeks)"
            elif rule.type == RetentionType.MONTHLY:
                return f"Retained for monthly retention (keep {rule.count} months)"
            elif rule.type == RetentionType.YEARLY:
                return f"Retained for yearly retention (keep {rule.count} years)"
        
        return "Retained by retention policy"
    
    def _find_applied_rule(
        self,
        snapshot: BackupSnapshot,
        rules: List[RetentionRule],
    ) -> Optional[str]:
        """
        Find which rule caused a snapshot to be retained.
        
        Args:
            snapshot: The snapshot being evaluated
            rules: List of retention rules
            
        Returns:
            Name of the applied rule or None
        """
        for rule in rules:
            if rule.type != RetentionType.TAG_BASED:
                return f"{rule.type.value}_{rule.count}"
        return None
    
    def prune_snapshots(
        self,
        repository: BackupRepository,
        retention_decisions: List[RetentionDecision],
        dry_run: bool = False,
    ) -> PruneResult:
        """
        Safely remove snapshots according to retention decisions.
        
        This method coordinates with the backup repository to remove snapshots
        that have been marked for pruning, with proper error handling and
        audit logging.
        
        Args:
            repository: Repository containing the snapshots
            retention_decisions: List of retention decisions
            dry_run: If True, simulate without actually removing snapshots
            
        Returns:
            PruneResult with operation details
            
        Raises:
            PolicyEnforcementError: If pruning fails critically
        """
        try:
            # Filter decisions to get snapshots to remove
            snapshots_to_remove = [
                d.snapshot for d in retention_decisions
                if not d.should_retain
            ]
            
            if not snapshots_to_remove:
                logger.info("No snapshots to prune")
                return PruneResult(
                    success=True,
                    snapshots_removed=[],
                    snapshots_failed=[],
                )
            
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Pruning {len(snapshots_to_remove)} "
                f"snapshots from repository"
            )
            
            if dry_run:
                # In dry-run mode, just return what would be removed
                snapshot_ids = [s.id for s in snapshots_to_remove]
                logger.info(
                    f"[DRY RUN] Would remove snapshots: {', '.join(snapshot_ids)}"
                )
                return PruneResult(
                    success=True,
                    snapshots_removed=snapshot_ids,
                    snapshots_failed=[],
                )
            
            # Actually remove snapshots
            removed = []
            failed = []
            
            for snapshot in snapshots_to_remove:
                try:
                    # Use the snapshot's delete method which calls repository.forget_snapshot
                    result = snapshot.delete(prune=False)
                    removed.append(snapshot.id)
                    logger.debug(f"Removed snapshot {snapshot.id}: {result}")
                except Exception as e:
                    error_msg = f"Failed to remove snapshot: {e}"
                    failed.append((snapshot.id, error_msg))
                    logger.error(f"Failed to remove snapshot {snapshot.id}: {e}")
            
            # If we have a repository service, run prune to reclaim space
            space_freed = 0
            if self.repository_service and removed:
                try:
                    prune_result = self.repository_service.prune_repository(repository)
                    space_freed = prune_result.get('space_freed', 0)
                    logger.info(f"Repository pruned: {space_freed} bytes freed")
                except Exception as e:
                    logger.warning(f"Failed to prune repository after snapshot removal: {e}")
            
            success = len(failed) == 0
            result = PruneResult(
                success=success,
                snapshots_removed=removed,
                snapshots_failed=failed,
                space_freed_bytes=space_freed,
            )
            
            logger.info(
                f"Pruning complete: {len(removed)} removed, {len(failed)} failed"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to prune snapshots: {e}"
            logger.error(error_msg)
            raise PolicyEnforcementError(
                error_msg,
                enforcement_type="snapshot_pruning",
            ) from e
    
    def validate_compliance(
        self,
        policy: RetentionPolicy,
        snapshots: List[BackupSnapshot],
        enforcement_history: Optional[List[EnforcementRecord]] = None,
    ) -> ComplianceStatus:
        """
        Validate policy compliance and identify violations.
        
        This method checks if the current snapshot state and enforcement
        history comply with the policy's compliance requirements.
        
        Args:
            policy: Retention policy with compliance requirements
            snapshots: Current snapshots in the repository
            enforcement_history: Optional history of enforcement operations
            
        Returns:
            ComplianceStatus with compliance assessment
        """
        try:
            violations = []
            
            # Check compliance period requirements
            if policy.compliance_period:
                min_age = datetime.utcnow() - policy.compliance_period
                
                # Check if any snapshots within compliance period would be removed
                for snapshot in snapshots:
                    if snapshot.timestamp > min_age:
                        # This snapshot is within compliance period
                        # Verify it won't be removed by retention rules
                        decisions = self.evaluate_retention_rules([snapshot], policy)
                        if decisions and not decisions[0].should_retain:
                            violation = ComplianceViolation(
                                rule_id="compliance_period",
                                description=(
                                    f"Snapshot {snapshot.id} from {snapshot.timestamp} "
                                    f"is within compliance period but marked for removal"
                                ),
                                severity="critical",
                                snapshot_ids=[snapshot.id],
                            )
                            violations.append(violation)
            
            # Check minimum retention requirements from compliance rules
            # (This would be expanded based on specific compliance requirements)
            
            # Determine if compliant
            compliant = len(violations) == 0
            
            # Determine next required action
            next_action = None
            if not compliant:
                next_action = RequiredAction(
                    action_type="resolve_violations",
                    description=f"Resolve {len(violations)} compliance violation(s)",
                    priority="high" if any(v.severity == "critical" for v in violations) else "normal",
                )
            
            status = ComplianceStatus(
                policy_id=policy.id,
                target_id="",  # Will be set by caller
                compliant=compliant,
                violations=violations,
                next_required_action=next_action,
            )
            
            logger.info(
                f"Compliance validation complete for policy {policy.id}: "
                f"{'compliant' if compliant else f'{len(violations)} violations'}"
            )
            
            return status
            
        except Exception as e:
            error_msg = f"Failed to validate compliance: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy.id) from e
    
    def create_enforcement_record(
        self,
        policy_id: str,
        target_id: str,
        enforcement_type: EnforcementType,
        success: bool,
        snapshots_affected: List[str],
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnforcementRecord:
        """
        Create an enforcement record for audit logging.
        
        Args:
            policy_id: ID of the policy that was enforced
            target_id: ID of the target (repository, backup job, etc.)
            enforcement_type: Type of enforcement operation
            success: Whether the enforcement succeeded
            snapshots_affected: List of snapshot IDs affected
            errors: Optional list of error messages
            metadata: Optional additional metadata
            
        Returns:
            EnforcementRecord for audit trail
        """
        record = EnforcementRecord(
            id=str(uuid.uuid4()),
            policy_id=policy_id,
            target_id=target_id,
            enforcement_type=enforcement_type,
            execution_time=datetime.utcnow(),
            success=success,
            snapshots_affected=snapshots_affected,
            errors=errors or [],
            metadata=metadata or {},
        )
        
        # Store in history
        self._enforcement_history.append(record)
        
        # Persist to storage if available
        if self.policy_store:
            try:
                self.policy_store.save_enforcement_record(record)
            except Exception as e:
                logger.error(f"Failed to persist enforcement record to storage: {e}")
        
        logger.info(
            f"Created enforcement record {record.id} for policy {policy_id}: "
            f"{'success' if success else 'failed'}, "
            f"{len(snapshots_affected)} snapshots affected"
        )
        
        return record
    
    def get_enforcement_history(
        self,
        policy_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[EnforcementRecord]:
        """
        Retrieve enforcement history records.
        
        Args:
            policy_id: Optional filter by policy ID
            target_id: Optional filter by target ID
            limit: Optional limit on number of records to return
            
        Returns:
            List of enforcement records matching filters
        """
        records = self._enforcement_history
        
        # Apply filters
        if policy_id:
            records = [r for r in records if r.policy_id == policy_id]
        if target_id:
            records = [r for r in records if r.target_id == target_id]
        
        # Sort by execution time (newest first)
        records = sorted(records, key=lambda r: r.execution_time, reverse=True)
        
        # Apply limit
        if limit:
            records = records[:limit]
        
        return records
