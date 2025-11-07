"""
Policy Integration Service

This module provides integration between policy management and existing
TimeLocker services including repository service, backup orchestrator,
and monitoring/reporting infrastructure.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..backup_repository import BackupRepository
from ..interfaces.backup_orchestrator import BackupStatus
from ..monitoring.status_reporter import StatusReporter, StatusLevel, OperationStatus
from .manager import PolicyManager
from .engine import PolicyEngine
from .models import (
    BackupPolicy,
    RetentionPolicy,
    PolicyAssignment,
    EnforcementRecord,
)
from .types import (
    PolicyType,
    TargetType,
    EnforcementType,
    PolicyStatus,
)
from .exceptions import (
    PolicyError,
    PolicyEnforcementError,
    PolicyNotFoundError,
)

logger = logging.getLogger(__name__)


class PolicyIntegrationService:
    """
    Integrates policy management with existing TimeLocker services.
    
    This service provides:
    - Repository service integration for policy enforcement
    - Backup orchestrator integration for policy-driven operations
    - Monitoring service integration for policy compliance tracking
    - Policy status reporting to monitoring infrastructure
    """
    
    def __init__(
        self,
        policy_manager: PolicyManager,
        policy_engine: PolicyEngine,
        repository_service=None,
        backup_orchestrator=None,
        status_reporter: Optional[StatusReporter] = None,
    ):
        """
        Initialize the policy integration service.
        
        Args:
            policy_manager: PolicyManager instance
            policy_engine: PolicyEngine instance
            repository_service: Optional repository service for enforcement
            backup_orchestrator: Optional backup orchestrator for policy-driven backups
            status_reporter: Optional status reporter for monitoring integration
        """
        self.policy_manager = policy_manager
        self.policy_engine = policy_engine
        self.repository_service = repository_service
        self.backup_orchestrator = backup_orchestrator
        self.status_reporter = status_reporter
        
        logger.info("PolicyIntegrationService initialized")
    
    # Repository Service Integration
    
    def enforce_retention_policy_on_repository(
        self,
        repository: BackupRepository,
        policy_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Enforce retention policy on a repository.
        
        This method integrates with the repository service to apply retention
        policies and prune snapshots according to policy rules.
        
        Args:
            repository: Repository to enforce policy on
            policy_id: Optional specific policy ID (otherwise uses assigned policy)
            dry_run: If True, simulate without actually removing snapshots
            
        Returns:
            Dictionary with enforcement results
            
        Raises:
            PolicyEnforcementError: If enforcement fails
        """
        try:
            operation_id = f"policy-enforcement-{repository.name}-{int(datetime.utcnow().timestamp())}"
            
            # Start monitoring if available
            if self.status_reporter:
                self.status_reporter.start_operation(
                    operation_id=operation_id,
                    operation_type="policy_enforcement",
                    repository_id=repository.name,
                    metadata={
                        'policy_id': policy_id,
                        'dry_run': dry_run,
                    }
                )
            
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Enforcing retention policy on "
                f"repository '{repository.name}'"
            )
            
            # Get effective retention policy
            if policy_id:
                policy = self.policy_manager.get_retention_policy(policy_id)
            else:
                # Get assigned policy for this repository
                effective_policies = self.policy_manager.get_effective_policies(
                    target_type=TargetType.REPOSITORY,
                    target_id=repository.name,
                )
                policy = effective_policies.get('retention_policy')
                
                if not policy:
                    # Apply default retention policy
                    logger.info(
                        f"No retention policy assigned to repository '{repository.name}', "
                        f"applying default policy"
                    )
                    self.policy_manager.apply_default_retention_policy(
                        target_type=TargetType.REPOSITORY,
                        target_id=repository.name,
                    )
                    policy = self.policy_manager.get_retention_policy(
                        self.policy_manager.DEFAULT_RETENTION_POLICY['id']
                    )
            
            # Get snapshots from repository
            snapshots = repository.list_snapshots()
            
            if self.status_reporter:
                self.status_reporter.update_operation(
                    operation_id=operation_id,
                    message=f"Evaluating {len(snapshots)} snapshots against policy",
                    progress_percentage=25,
                )
            
            # Evaluate retention rules
            retention_decisions = self.policy_engine.evaluate_retention_rules(
                snapshots=snapshots,
                policy=policy,
            )
            
            if self.status_reporter:
                self.status_reporter.update_operation(
                    operation_id=operation_id,
                    message="Pruning snapshots according to policy",
                    progress_percentage=50,
                )
            
            # Prune snapshots
            prune_result = self.policy_engine.prune_snapshots(
                repository=repository,
                retention_decisions=retention_decisions,
                dry_run=dry_run,
            )
            
            # Create enforcement record
            enforcement_record = self.policy_engine.create_enforcement_record(
                policy_id=policy.id,
                target_id=repository.name,
                enforcement_type=EnforcementType.RETENTION,
                success=prune_result.success,
                snapshots_affected=prune_result.snapshots_removed,
                errors=prune_result.errors,
                metadata={
                    'dry_run': dry_run,
                    'space_freed_bytes': prune_result.space_freed_bytes,
                    'snapshots_failed': len(prune_result.snapshots_failed),
                },
            )
            
            # Complete monitoring
            if self.status_reporter:
                status_level = StatusLevel.SUCCESS if prune_result.success else StatusLevel.ERROR
                self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=status_level,
                    message=f"Policy enforcement {'completed' if prune_result.success else 'failed'}: "
                            f"{len(prune_result.snapshots_removed)} snapshots removed",
                    metadata={
                        'enforcement_record_id': enforcement_record.id,
                        'snapshots_removed': len(prune_result.snapshots_removed),
                        'space_freed_bytes': prune_result.space_freed_bytes,
                    }
                )
            
            result = {
                'success': prune_result.success,
                'policy_id': policy.id,
                'policy_name': policy.name,
                'repository': repository.name,
                'dry_run': dry_run,
                'snapshots_evaluated': len(snapshots),
                'snapshots_removed': len(prune_result.snapshots_removed),
                'snapshots_failed': len(prune_result.snapshots_failed),
                'space_freed_bytes': prune_result.space_freed_bytes,
                'enforcement_record_id': enforcement_record.id,
                'errors': prune_result.errors,
            }
            
            logger.info(
                f"Policy enforcement {'completed' if prune_result.success else 'failed'} on "
                f"repository '{repository.name}': {len(prune_result.snapshots_removed)} "
                f"snapshots removed"
            )
            
            return result
            
        except PolicyNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to enforce retention policy: {e}"
            logger.error(error_msg)
            
            if self.status_reporter:
                self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=StatusLevel.ERROR,
                    message=error_msg,
                )
            
            raise PolicyEnforcementError(
                error_msg,
                policy_id=policy_id or 'unknown',
                enforcement_type="retention",
            ) from e
    
    # Backup Orchestrator Integration
    
    def execute_policy_driven_backup(
        self,
        policy_id: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a backup operation driven by a backup policy.
        
        This method integrates with the backup orchestrator to execute backups
        according to backup policy configuration.
        
        Args:
            policy_id: Backup policy ID to execute
            dry_run: If True, simulate without actually performing backup
            
        Returns:
            Dictionary with backup results
            
        Raises:
            PolicyError: If backup execution fails
        """
        try:
            if not self.backup_orchestrator:
                raise PolicyError(
                    "Backup orchestrator not available for policy-driven backups",
                    policy_id=policy_id,
                )
            
            # Get backup policy
            policy = self.policy_manager.get_backup_policy(policy_id)
            
            if policy.status != PolicyStatus.ACTIVE:
                raise PolicyError(
                    f"Cannot execute backup: policy status is {policy.status.value}",
                    policy_id=policy_id,
                )
            
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Executing policy-driven backup "
                f"for policy '{policy.name}' (ID: {policy_id})"
            )
            
            results = []
            
            # Execute backup for each target repository
            for repository_name in policy.target_repositories:
                try:
                    # Execute backup using orchestrator
                    backup_result = self.backup_orchestrator.execute_backup(
                        repository_name=repository_name,
                        target_names=policy.data_selection_refs,
                        tags=list(policy.tags.keys()) if policy.tags else None,
                        dry_run=dry_run,
                    )
                    
                    result = {
                        'repository': repository_name,
                        'status': backup_result.status.value,
                        'snapshot_id': backup_result.snapshot_id,
                        'files_processed': backup_result.files_processed,
                        'bytes_processed': backup_result.bytes_processed,
                        'errors': backup_result.errors,
                    }
                    
                    results.append(result)
                    
                    # If backup succeeded and retention policy is configured, enforce it
                    if (backup_result.status == BackupStatus.COMPLETED and
                        policy.retention_policy_id and not dry_run):
                        logger.info(
                            f"Enforcing retention policy after backup on "
                            f"repository '{repository_name}'"
                        )
                        # Note: Would need repository instance here
                        # This is a placeholder for the integration point
                    
                except Exception as e:
                    logger.error(
                        f"Failed to execute backup for repository '{repository_name}': {e}"
                    )
                    results.append({
                        'repository': repository_name,
                        'status': 'failed',
                        'errors': [str(e)],
                    })
            
            overall_success = all(
                r.get('status') in ['completed', BackupStatus.COMPLETED.value]
                for r in results
            )
            
            return {
                'success': overall_success,
                'policy_id': policy_id,
                'policy_name': policy.name,
                'dry_run': dry_run,
                'results': results,
            }
            
        except PolicyNotFoundError:
            raise
        except Exception as e:
            error_msg = f"Failed to execute policy-driven backup: {e}"
            logger.error(error_msg)
            raise PolicyError(error_msg, policy_id=policy_id) from e
    
    # Monitoring Integration
    
    def report_policy_compliance_status(
        self,
        target_type: TargetType,
        target_id: str,
    ) -> Dict[str, Any]:
        """
        Report policy compliance status to monitoring infrastructure.
        
        Args:
            target_type: Type of target to check
            target_id: Target identifier
            
        Returns:
            Dictionary with compliance status
        """
        try:
            # Get effective policies for target
            effective_policies = self.policy_manager.get_effective_policies(
                target_type=target_type,
                target_id=target_id,
            )
            
            compliance_status = {
                'target_type': target_type.value,
                'target_id': target_id,
                'timestamp': datetime.utcnow().isoformat(),
                'backup_policy': None,
                'retention_policy': None,
                'compliant': True,
                'warnings': [],
            }
            
            # Check backup policy
            backup_policy = effective_policies.get('backup_policy')
            if backup_policy:
                compliance_status['backup_policy'] = {
                    'id': backup_policy.id,
                    'name': backup_policy.name,
                    'status': backup_policy.status.value,
                }
            else:
                compliance_status['warnings'].append(
                    "No backup policy assigned to target"
                )
            
            # Check retention policy
            retention_policy = effective_policies.get('retention_policy')
            if retention_policy:
                compliance_status['retention_policy'] = {
                    'id': retention_policy.id,
                    'name': retention_policy.name,
                    'status': retention_policy.status.value,
                }
            else:
                compliance_status['warnings'].append(
                    "No retention policy assigned to target"
                )
                compliance_status['compliant'] = False
            
            # Report to monitoring if available
            if self.status_reporter:
                operation_id = f"compliance-check-{target_id}-{int(datetime.utcnow().timestamp())}"
                status_level = StatusLevel.SUCCESS if compliance_status['compliant'] else StatusLevel.WARNING
                
                self.status_reporter.start_operation(
                    operation_id=operation_id,
                    operation_type="policy_compliance_check",
                    repository_id=target_id,
                    metadata=compliance_status,
                )
                
                self.status_reporter.complete_operation(
                    operation_id=operation_id,
                    status=status_level,
                    message=f"Compliance check: {'compliant' if compliance_status['compliant'] else 'warnings found'}",
                )
            
            return compliance_status
            
        except Exception as e:
            error_msg = f"Failed to report policy compliance status: {e}"
            logger.error(error_msg)
            return {
                'target_type': target_type.value,
                'target_id': target_id,
                'timestamp': datetime.utcnow().isoformat(),
                'compliant': False,
                'error': error_msg,
            }
    
    def get_policy_enforcement_history(
        self,
        target_id: Optional[str] = None,
        policy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get policy enforcement history for monitoring and reporting.
        
        Args:
            target_id: Optional filter by target ID
            policy_id: Optional filter by policy ID
            limit: Maximum number of records to return
            
        Returns:
            List of enforcement records
        """
        try:
            records = self.policy_engine.get_enforcement_history(
                policy_id=policy_id,
                target_id=target_id,
                limit=limit,
            )
            
            return [record.to_dict() for record in records]
            
        except Exception as e:
            logger.error(f"Failed to get policy enforcement history: {e}")
            return []
    
    def get_policy_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of policy status for monitoring dashboard.
        
        Returns:
            Dictionary with policy status summary
        """
        try:
            backup_policies = self.policy_manager.list_backup_policies()
            retention_policies = self.policy_manager.list_retention_policies()
            assignments = self.policy_manager.get_policy_assignments()
            
            # Count policies by status
            backup_by_status = {}
            for policy in backup_policies:
                status = policy.status.value
                backup_by_status[status] = backup_by_status.get(status, 0) + 1
            
            retention_by_status = {}
            for policy in retention_policies:
                status = policy.status.value
                retention_by_status[status] = retention_by_status.get(status, 0) + 1
            
            # Count active assignments
            active_assignments = sum(1 for a in assignments if a.active)
            
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'backup_policies': {
                    'total': len(backup_policies),
                    'by_status': backup_by_status,
                },
                'retention_policies': {
                    'total': len(retention_policies),
                    'by_status': retention_by_status,
                },
                'assignments': {
                    'total': len(assignments),
                    'active': active_assignments,
                    'inactive': len(assignments) - active_assignments,
                },
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get policy status summary: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
            }
