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

Integration Clients for Scheduling System

This module provides client interfaces for integrating with other TimeLocker
systems including Policy Management, Data Selection, Repository Management,
and Monitoring & Reporting.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..selection_template_manager import TemplateNotFoundError

logger = logging.getLogger(__name__)


class PolicyManagementClient:
    """
    Client for integrating with Policy Management system.
    
    Provides methods to retrieve and validate backup policies for
    scheduled execution, including policy update handling and schedule
    synchronization.
    """
    
    def __init__(self, policy_manager=None):
        """
        Initialize policy management client.
        
        Args:
            policy_manager: Optional PolicyManager instance
        """
        self.logger = logging.getLogger(f"{__name__}.PolicyManagementClient")
        self._policy_manager = policy_manager
        self._policy_update_callbacks = []
    
    def get_backup_policy(self, policy_id: str) -> Optional[Any]:
        """
        Retrieve a backup policy by ID.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            BackupPolicy instance or None if not found
        """
        try:
            if self._policy_manager is None:
                # Lazy load policy manager
                from ..policy import PolicyManager
                self._policy_manager = PolicyManager()
            
            policy = self._policy_manager.get_backup_policy(policy_id)
            self.logger.debug(f"Retrieved backup policy: {policy_id}")
            return policy
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve backup policy {policy_id}: {e}")
            return None
    
    def validate_policy_for_scheduling(self, policy_id: str) -> tuple[bool, List[str]]:
        """
        Validate that a backup policy is suitable for scheduled execution.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            policy = self.get_backup_policy(policy_id)
            
            if policy is None:
                return False, [f"Policy {policy_id} not found"]
            
            errors = []
            
            # Check policy status
            from ..policy.types import PolicyStatus
            if policy.status != PolicyStatus.ACTIVE:
                errors.append(f"Policy status is {policy.status.value}, must be ACTIVE for scheduling")
            
            # Check for required fields
            if not policy.target_repositories:
                errors.append("Policy has no target repositories configured")
            
            if not policy.data_selection_refs:
                errors.append("Policy has no data selection references configured")
            
            # Check for user interaction requirements
            if hasattr(policy, 'requires_user_interaction') and policy.requires_user_interaction:
                errors.append("Policy requires user interaction and cannot be scheduled")
            
            is_valid = len(errors) == 0
            self.logger.debug(f"Policy {policy_id} validation: {'valid' if is_valid else 'invalid'}")
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.error(f"Failed to validate policy {policy_id}: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def register_policy_update_callback(self, callback) -> None:
        """
        Register a callback to be notified of policy updates.
        
        Args:
            callback: Callable that accepts (policy_id, updates) parameters
        """
        if callback not in self._policy_update_callbacks:
            self._policy_update_callbacks.append(callback)
            self.logger.debug(f"Registered policy update callback: {callback.__name__}")
    
    def unregister_policy_update_callback(self, callback) -> None:
        """
        Unregister a policy update callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._policy_update_callbacks:
            self._policy_update_callbacks.remove(callback)
            self.logger.debug(f"Unregistered policy update callback: {callback.__name__}")
    
    async def notify_policy_update(self, policy_id: str, updates: Dict[str, Any]) -> None:
        """
        Notify registered callbacks of policy updates.
        
        This method should be called when a policy is updated to trigger
        automatic schedule updates.
        
        Args:
            policy_id: Policy identifier that was updated
            updates: Dictionary of updates made to the policy
        """
        self.logger.info(f"Notifying {len(self._policy_update_callbacks)} callbacks of policy update: {policy_id}")
        
        for callback in self._policy_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(policy_id, updates)
                else:
                    callback(policy_id, updates)
            except Exception as e:
                self.logger.error(f"Error in policy update callback {callback.__name__}: {e}")
    
    def get_policy_schedule_requirements(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get scheduling requirements from a backup policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Dictionary with scheduling requirements or None if not found
        """
        try:
            policy = self.get_backup_policy(policy_id)
            
            if policy is None:
                return None
            
            requirements = {
                'policy_id': policy_id,
                'requires_scheduling': True,
                'min_interval_hours': None,
                'max_interval_hours': None,
                'preferred_time_window': None,
                'retention_requirements': None
            }
            
            # Extract scheduling hints from policy if available
            if hasattr(policy, 'schedule_hints'):
                requirements.update(policy.schedule_hints)
            
            # Extract retention requirements
            if hasattr(policy, 'retention_policy'):
                requirements['retention_requirements'] = {
                    'keep_daily': getattr(policy.retention_policy, 'keep_daily', None),
                    'keep_weekly': getattr(policy.retention_policy, 'keep_weekly', None),
                    'keep_monthly': getattr(policy.retention_policy, 'keep_monthly', None)
                }
            
            self.logger.debug(f"Retrieved schedule requirements for policy {policy_id}")
            return requirements
            
        except Exception as e:
            self.logger.error(f"Failed to get policy schedule requirements {policy_id}: {e}")
            return None
    
    def check_policy_compatibility_for_automation(self, policy_id: str) -> tuple[bool, List[str]]:
        """
        Check if a policy is compatible with automated execution.
        
        This performs deeper validation than validate_policy_for_scheduling,
        checking for specific automation requirements.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Tuple of (is_compatible, incompatibility_reasons)
        """
        try:
            policy = self.get_backup_policy(policy_id)
            
            if policy is None:
                return False, [f"Policy {policy_id} not found"]
            
            reasons = []
            
            # Check for interactive requirements
            if hasattr(policy, 'requires_user_interaction') and policy.requires_user_interaction:
                reasons.append("Policy requires user interaction")
            
            # Check for manual approval requirements
            if hasattr(policy, 'requires_manual_approval') and policy.requires_manual_approval:
                reasons.append("Policy requires manual approval before execution")
            
            # Check for dynamic path requirements
            if hasattr(policy, 'uses_dynamic_paths') and policy.uses_dynamic_paths:
                reasons.append("Policy uses dynamic paths that may not be available during automated execution")
            
            # Check for credential requirements
            if hasattr(policy, 'credential_requirements'):
                cred_reqs = policy.credential_requirements
                if cred_reqs.get('requires_interactive_auth'):
                    reasons.append("Policy requires interactive authentication")
            
            is_compatible = len(reasons) == 0
            self.logger.debug(
                f"Policy {policy_id} automation compatibility: "
                f"{'compatible' if is_compatible else 'incompatible'}"
            )
            
            return is_compatible, reasons
            
        except Exception as e:
            self.logger.error(f"Failed to check policy automation compatibility {policy_id}: {e}")
            return False, [f"Compatibility check error: {str(e)}"]
    
    def list_policies_for_scheduling(self) -> List[Dict[str, Any]]:
        """
        List all policies that are suitable for scheduling.
        
        Returns:
            List of policy information dictionaries
        """
        try:
            if self._policy_manager is None:
                from ..policy import PolicyManager
                self._policy_manager = PolicyManager()
            
            # Get all policies
            all_policies = self._policy_manager.list_backup_policies()
            
            # Filter for schedulable policies
            schedulable_policies = []
            for policy in all_policies:
                is_valid, _ = self.validate_policy_for_scheduling(policy.id)
                if is_valid:
                    schedulable_policies.append({
                        'id': policy.id,
                        'name': policy.name if hasattr(policy, 'name') else policy.id,
                        'status': policy.status.value if hasattr(policy, 'status') else 'unknown',
                        'target_repositories': policy.target_repositories if hasattr(policy, 'target_repositories') else [],
                        'data_selection_refs': policy.data_selection_refs if hasattr(policy, 'data_selection_refs') else []
                    })
            
            self.logger.debug(f"Found {len(schedulable_policies)} schedulable policies")
            return schedulable_policies
            
        except Exception as e:
            self.logger.error(f"Failed to list policies for scheduling: {e}")
            return []


class DataSelectionClient:
    """
    Client for integrating with Data Selection system.
    
    Provides methods to retrieve and validate data selection configurations
    for scheduled backups.
    """
    
    def __init__(self, selection_manager=None):
        """
        Initialize data selection client.
        
        Args:
            selection_manager: Optional SelectionManager instance
        """
        self.logger = logging.getLogger(f"{__name__}.DataSelectionClient")
        self._selection_manager = selection_manager

    def _get_selection_manager(self):
        """Lazy-load and cache the SelectionManager instance."""
        if self._selection_manager is None:
            from ..selection_manager import SelectionManager
            self._selection_manager = SelectionManager()
        return self._selection_manager

    def _resolve_template(self, template_ref: str):
        """
        Resolve a template reference (ID or name) to the canonical template.
        """
        manager = self._get_selection_manager()
        try:
            template = manager.template_manager.resolve_template(template_ref)
            if template_ref != template.id:
                self.logger.info(
                    "Resolved data selection reference '%s' to template '%s'",
                    template_ref,
                    template.id
                )
            return template
        except TemplateNotFoundError:
            self.logger.warning(
                "Data selection template not found: %s",
                template_ref
            )
            return None
        except Exception as exc:
            self.logger.error(
                "Failed to resolve data selection template %s: %s",
                template_ref,
                exc
            )
            return None
    
    def get_selection_template(self, template_id: str) -> Optional[Any]:
        """
        Retrieve a data selection template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Selection template or None if not found
        """
        template = self._resolve_template(template_id)
        if template:
            self.logger.debug(
                "Retrieved selection template '%s' (canonical id: %s)",
                template_id,
                template.id
            )
        return template
    
    def validate_selection_for_scheduling(self, template_id: str) -> tuple[bool, List[str]]:
        """
        Validate that a data selection is accessible for scheduled execution.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        template = self.get_selection_template(template_id)
        
        if template is None:
            return False, [f"Selection template {template_id} not found"]
        
        errors = []
        
        # Basic validation - template exists and is accessible
        is_valid = len(errors) == 0
        self.logger.debug(
            "Selection template %s validation: %s",
            template_id,
            'valid' if is_valid else 'invalid'
        )
        
        return is_valid, errors


class RepositoryManagementClient:
    """
    Client for integrating with Repository Management system.
    
    Provides methods to retrieve and validate repository configurations
    and credentials for scheduled backups.
    """
    
    def __init__(self, repository_manager=None):
        """
        Initialize repository management client.
        
        Args:
            repository_manager: Optional repository manager instance
        """
        self.logger = logging.getLogger(f"{__name__}.RepositoryManagementClient")
        self._repository_manager = repository_manager
    
    def get_repository_config(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve repository configuration by ID.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            Repository configuration or None if not found
        """
        try:
            if self._repository_manager is None:
                # Lazy load repository manager
                from ..config import ConfigurationModule
                config_module = ConfigurationModule()
                repositories = config_module.get_repositories()
                
                for repo in repositories:
                    if repo.get('name') == repository_id or repo.get('id') == repository_id:
                        self.logger.debug(f"Retrieved repository config: {repository_id}")
                        return repo
                
                return None
            
            # Use repository manager if available
            config = self._repository_manager.get_repository(repository_id)
            self.logger.debug(f"Retrieved repository config: {repository_id}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve repository config {repository_id}: {e}")
            return None
    
    def validate_repository_for_scheduling(self, repository_id: str) -> tuple[bool, List[str]]:
        """
        Validate that a repository is accessible for scheduled execution.
        
        Args:
            repository_id: Repository identifier
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            config = self.get_repository_config(repository_id)
            
            if config is None:
                return False, [f"Repository {repository_id} not found"]
            
            errors = []
            
            # Check for required configuration
            if not config.get('uri') and not config.get('url'):
                errors.append("Repository has no URI/URL configured")
            
            # Check credentials availability
            # Note: Actual credential validation should be done at execution time
            # to avoid exposing credentials during validation
            
            is_valid = len(errors) == 0
            self.logger.debug(f"Repository {repository_id} validation: {'valid' if is_valid else 'invalid'}")
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.error(f"Failed to validate repository {repository_id}: {e}")
            return False, [f"Validation error: {str(e)}"]


class MonitoringClient:
    """
    Client for integrating with Monitoring & Reporting system.
    
    Provides methods to report scheduling events, status updates,
    execution results, health checks, and scheduling-specific metrics
    to the monitoring system.
    """
    
    def __init__(self, monitoring_service=None):
        """
        Initialize monitoring client.
        
        Args:
            monitoring_service: Optional MonitoringService instance
        """
        self.logger = logging.getLogger(f"{__name__}.MonitoringClient")
        self._monitoring_service = monitoring_service
        self._health_check_webhooks = []
        self._metrics_cache = {}
    
    def report_schedule_created(self, schedule_id: str, schedule_config: Dict[str, Any]) -> None:
        """
        Report schedule creation to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
            schedule_config: Schedule configuration details
        """
        try:
            if self._monitoring_service is None:
                # Lazy load monitoring service
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            # Log to activity logger
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=schedule_id,
                    operation_type="schedule_created",
                    message=f"Schedule created: {schedule_config.get('name', schedule_id)}",
                    metadata=schedule_config
                )
            )
            
            self.logger.debug(f"Reported schedule creation: {schedule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule creation: {e}")
    
    def report_schedule_updated(self, schedule_id: str, updates: Dict[str, Any]) -> None:
        """
        Report schedule update to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
            updates: Update details
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=schedule_id,
                    operation_type="schedule_updated",
                    message=f"Schedule updated: {schedule_id}",
                    metadata=updates
                )
            )
            
            self.logger.debug(f"Reported schedule update: {schedule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule update: {e}")
    
    def report_schedule_deleted(self, schedule_id: str) -> None:
        """
        Report schedule deletion to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=schedule_id,
                    operation_type="schedule_deleted",
                    message=f"Schedule deleted: {schedule_id}",
                    metadata={}
                )
            )
            
            self.logger.debug(f"Reported schedule deletion: {schedule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule deletion: {e}")
    
    def report_execution_start(self, schedule_id: str, execution_id: str, context: Dict[str, Any]) -> None:
        """
        Report backup execution start to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
            execution_id: Execution identifier
            context: Execution context
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=execution_id,
                    operation_type="scheduled_backup_started",
                    message=f"Scheduled backup started: {schedule_id}",
                    metadata={
                        'schedule_id': schedule_id,
                        **context
                    }
                )
            )
            
            self.logger.debug(f"Reported execution start: {execution_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report execution start: {e}")
    
    def report_execution_complete(self, execution_result: Dict[str, Any]) -> None:
        """
        Report backup execution completion to monitoring system.
        
        Args:
            execution_result: Execution result details
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            from ..monitoring.status_reporter import StatusLevel
            
            # Determine status level from execution result
            status = execution_result.get('status', 'unknown')
            status_level = StatusLevel.SUCCESS if status == 'success' else StatusLevel.ERROR
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=execution_result.get('execution_id', 'unknown'),
                    operation_type="scheduled_backup_completed",
                    message=f"Scheduled backup completed: {status}",
                    status=status_level,
                    metadata=execution_result
                )
            )
            
            self.logger.debug(f"Reported execution completion: {execution_result.get('execution_id')}")
            
        except Exception as e:
            self.logger.error(f"Failed to report execution completion: {e}")
    
    def report_execution_error(self, execution_result: Dict[str, Any], error: Exception) -> None:
        """
        Report backup execution error to monitoring system.
        
        Args:
            execution_result: Execution result details
            error: Exception that occurred
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            from ..monitoring.status_reporter import StatusLevel
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=execution_result.get('execution_id', 'unknown'),
                    operation_type="scheduled_backup_failed",
                    message=f"Scheduled backup failed: {str(error)}",
                    status=StatusLevel.ERROR,
                    metadata={
                        **execution_result,
                        'error_type': type(error).__name__,
                        'error_message': str(error)
                    }
                )
            )
            
            self.logger.debug(f"Reported execution error: {execution_result.get('execution_id')}")
            
        except Exception as e:
            self.logger.error(f"Failed to report execution error: {e}")
    
    def _create_operation_status(
        self,
        operation_id: str,
        operation_type: str,
        message: str,
        status=None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create an OperationStatus object for logging.
        
        Args:
            operation_id: Operation identifier
            operation_type: Type of operation
            message: Status message
            status: Optional status level
            metadata: Optional metadata
            
        Returns:
            OperationStatus instance
        """
        from ..monitoring.status_reporter import OperationStatus, StatusLevel
        
        if status is None:
            status = StatusLevel.INFO
        
        return OperationStatus(
            operation_id=operation_id,
            operation_type=operation_type,
            status=status,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
    
    def register_health_check_webhook(self, webhook_url: str, schedule_id: Optional[str] = None) -> None:
        """
        Register a health check webhook for monitoring integration.
        
        Args:
            webhook_url: URL to call for health checks
            schedule_id: Optional schedule ID to associate with webhook
        """
        webhook_config = {
            'url': webhook_url,
            'schedule_id': schedule_id,
            'registered_at': datetime.now()
        }
        
        self._health_check_webhooks.append(webhook_config)
        self.logger.info(f"Registered health check webhook: {webhook_url}")
    
    def unregister_health_check_webhook(self, webhook_url: str) -> None:
        """
        Unregister a health check webhook.
        
        Args:
            webhook_url: URL to unregister
        """
        self._health_check_webhooks = [
            w for w in self._health_check_webhooks
            if w['url'] != webhook_url
        ]
        self.logger.info(f"Unregistered health check webhook: {webhook_url}")
    
    async def send_health_check_ping(
        self,
        schedule_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send health check ping to registered webhooks.
        
        Args:
            schedule_id: Schedule identifier
            status: Health status ('healthy', 'warning', 'error')
            details: Optional additional details
        """
        # Find webhooks for this schedule
        webhooks = [
            w for w in self._health_check_webhooks
            if w['schedule_id'] is None or w['schedule_id'] == schedule_id
        ]
        
        if not webhooks:
            self.logger.debug(f"No health check webhooks registered for schedule {schedule_id}")
            return
        
        ping_data = {
            'schedule_id': schedule_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        for webhook in webhooks:
            try:
                # Send webhook ping (would use requests or httpx in real implementation)
                self.logger.info(
                    f"Sending health check ping to {webhook['url']} "
                    f"for schedule {schedule_id}: {status}"
                )
                
                # In a real implementation, this would make an HTTP request
                # For now, just log it
                self.logger.debug(f"Health check ping data: {ping_data}")
                
            except Exception as e:
                self.logger.error(f"Failed to send health check ping to {webhook['url']}: {e}")
    
    def report_schedule_rescheduled(self, schedule_id: str, details: Dict[str, Any]) -> None:
        """
        Report schedule rescheduling to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
            details: Rescheduling details
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=schedule_id,
                    operation_type="schedule_rescheduled",
                    message=f"Schedule rescheduled: {schedule_id}",
                    metadata=details
                )
            )
            
            self.logger.debug(f"Reported schedule rescheduling: {schedule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule rescheduling: {e}")
    
    def report_scheduling_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Report scheduling-specific metrics to monitoring system.
        
        Args:
            metrics: Dictionary of metrics to report
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            # Update metrics cache
            self._metrics_cache.update(metrics)
            self._metrics_cache['last_updated'] = datetime.now().isoformat()
            
            # Log metrics
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id='scheduling_metrics',
                    operation_type="scheduling_metrics",
                    message="Scheduling metrics update",
                    metadata=metrics
                )
            )
            
            self.logger.debug(f"Reported scheduling metrics: {len(metrics)} metrics")
            
        except Exception as e:
            self.logger.error(f"Failed to report scheduling metrics: {e}")
    
    def get_cached_metrics(self) -> Dict[str, Any]:
        """
        Get cached scheduling metrics.
        
        Returns:
            Dictionary of cached metrics
        """
        return self._metrics_cache.copy()
    
    def report_schedule_health_status(
        self,
        schedule_id: str,
        health_status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report schedule health status to monitoring system.
        
        Args:
            schedule_id: Schedule identifier
            health_status: Health status ('healthy', 'warning', 'error', 'unknown')
            details: Optional health status details
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            from ..monitoring.status_reporter import StatusLevel
            
            # Map health status to status level
            status_mapping = {
                'healthy': StatusLevel.SUCCESS,
                'warning': StatusLevel.WARNING,
                'error': StatusLevel.ERROR,
                'unknown': StatusLevel.INFO
            }
            
            status_level = status_mapping.get(health_status, StatusLevel.INFO)
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=schedule_id,
                    operation_type="schedule_health_status",
                    message=f"Schedule health status: {health_status}",
                    status=status_level,
                    metadata={
                        'health_status': health_status,
                        **(details or {})
                    }
                )
            )
            
            self.logger.debug(f"Reported schedule health status: {schedule_id} - {health_status}")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule health status: {e}")
    
    def report_next_scheduled_runs(self, upcoming_runs: List[Dict[str, Any]]) -> None:
        """
        Report upcoming scheduled runs to monitoring system.
        
        Args:
            upcoming_runs: List of upcoming scheduled run information
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id='next_scheduled_runs',
                    operation_type="next_scheduled_runs",
                    message=f"Next {len(upcoming_runs)} scheduled runs",
                    metadata={
                        'upcoming_runs': upcoming_runs,
                        'count': len(upcoming_runs)
                    }
                )
            )
            
            self.logger.debug(f"Reported {len(upcoming_runs)} upcoming scheduled runs")
            
        except Exception as e:
            self.logger.error(f"Failed to report next scheduled runs: {e}")
    
    def report_schedule_conflict(
        self,
        conflict_details: Dict[str, Any]
    ) -> None:
        """
        Report schedule conflict to monitoring system.
        
        Args:
            conflict_details: Conflict information
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            from ..monitoring.status_reporter import StatusLevel
            
            # Determine severity
            severity = conflict_details.get('severity', 'medium')
            status_level = StatusLevel.WARNING if severity in ['low', 'medium'] else StatusLevel.ERROR
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id=conflict_details.get('conflict_id', 'unknown'),
                    operation_type="schedule_conflict",
                    message=f"Schedule conflict detected: {severity} severity",
                    status=status_level,
                    metadata=conflict_details
                )
            )
            
            self.logger.info(f"Reported schedule conflict: {severity} severity")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule conflict: {e}")
    
    def report_schedule_optimization(
        self,
        optimization_details: Dict[str, Any]
    ) -> None:
        """
        Report schedule optimization to monitoring system.
        
        Args:
            optimization_details: Optimization information
        """
        try:
            if self._monitoring_service is None:
                from ..monitoring import MonitoringService
                self._monitoring_service = MonitoringService()
            
            self._monitoring_service.activity_logger.log_backup_event(
                self._create_operation_status(
                    operation_id='schedule_optimization',
                    operation_type="schedule_optimization",
                    message="Schedule optimization performed",
                    metadata=optimization_details
                )
            )
            
            self.logger.debug("Reported schedule optimization")
            
        except Exception as e:
            self.logger.error(f"Failed to report schedule optimization: {e}")
