"""
Copyright ©  Bruce Cherrington

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(antml:parameter name="text">"""
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
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PolicyManagementClient:
    """
    Client for integrating with Policy Management system.
    
    Provides methods to retrieve and validate backup policies for
    scheduled execution.
    """
    
    def __init__(self, policy_manager=None):
        """
        Initialize policy management client.
        
        Args:
            policy_manager: Optional PolicyManager instance
        """
        self.logger = logging.getLogger(f"{__name__}.PolicyManagementClient")
        self._policy_manager = policy_manager
    
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
    
    def get_selection_template(self, template_id: str) -> Optional[Any]:
        """
        Retrieve a data selection template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Selection template or None if not found
        """
        try:
            if self._selection_manager is None:
                # Lazy load selection manager
                from ..selection_manager import SelectionManager
                self._selection_manager = SelectionManager()
            
            # Get template from selection manager
            template = self._selection_manager.get_template(template_id)
            self.logger.debug(f"Retrieved selection template: {template_id}")
            return template
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve selection template {template_id}: {e}")
            return None
    
    def validate_selection_for_scheduling(self, template_id: str) -> tuple[bool, List[str]]:
        """
        Validate that a data selection is accessible for scheduled execution.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            template = self.get_selection_template(template_id)
            
            if template is None:
                return False, [f"Selection template {template_id} not found"]
            
            errors = []
            
            # Basic validation - template exists and is accessible
            # More detailed validation would check path accessibility
            # but that's better done at execution time
            
            is_valid = len(errors) == 0
            self.logger.debug(f"Selection template {template_id} validation: {'valid' if is_valid else 'invalid'}")
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.error(f"Failed to validate selection template {template_id}: {e}")
            return False, [f"Validation error: {str(e)}"]


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
    and execution results to the monitoring system.
    """
    
    def __init__(self, monitoring_service=None):
        """
        Initialize monitoring client.
        
        Args:
            monitoring_service: Optional MonitoringService instance
        """
        self.logger = logging.getLogger(f"{__name__}.MonitoringClient")
        self._monitoring_service = monitoring_service
    
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
