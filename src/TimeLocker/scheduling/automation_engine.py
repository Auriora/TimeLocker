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

Automation Engine for Scheduled Backup Execution

This module provides the AutomationEngine class that handles the execution
of scheduled backup operations with full TimeLocker integration including
Policy Management, Data Selection, Repository Management, and Monitoring.
"""

import logging
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

from .scheduling_models import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTrigger,
    RetryConfig
)
from .scheduling_exceptions import (
    PolicyValidationError,
    DataSelectionValidationError,
    RepositoryValidationError,
    ExecutionTimeoutError
)
from .integration_clients import (
    PolicyManagementClient,
    DataSelectionClient,
    RepositoryManagementClient,
    MonitoringClient
)
from .audit_logger import SchedulingAuditLogger
from ..interfaces.backup_orchestrator import BackupResult, BackupStatus
from ..interfaces.data_models import BackupJobConfig, ExecutionMode

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity level for execution errors."""
    TRANSIENT = "transient"  # Temporary error, retry likely to succeed
    PERSISTENT = "persistent"  # Persistent error, retry unlikely to help
    FATAL = "fatal"  # Fatal error, do not retry


class AutomationEngine:
    """
    Handles execution of scheduled backup operations.
    
    This engine coordinates the execution of scheduled backups by integrating
    with all TimeLocker systems including Policy Management, Data Selection,
    Repository Management, and Monitoring & Reporting.
    
    Responsibilities:
    - Backup execution coordination
    - Integration with all TimeLocker systems
    - Error handling and retry logic
    - Monitoring and audit logging
    """
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        policy_client: Optional[PolicyManagementClient] = None,
        data_selection_client: Optional[DataSelectionClient] = None,
        repository_client: Optional[RepositoryManagementClient] = None,
        monitoring_client: Optional[MonitoringClient] = None,
        audit_logger: Optional[SchedulingAuditLogger] = None,
        backup_orchestrator=None
    ):
        """
        Initialize automation engine.
        
        Args:
            config_dir: Configuration directory path
            policy_client: Optional PolicyManagementClient instance
            data_selection_client: Optional DataSelectionClient instance
            repository_client: Optional RepositoryManagementClient instance
            monitoring_client: Optional MonitoringClient instance
            audit_logger: Optional SchedulingAuditLogger instance
            backup_orchestrator: Optional backup orchestrator instance
        """
        self.logger = logging.getLogger(f"{__name__}.AutomationEngine")
        self.config_dir = config_dir or Path.home() / ".config" / "timelocker"
        
        # Initialize integration clients
        self.policy_client = policy_client or PolicyManagementClient()
        self.data_selection_client = data_selection_client or DataSelectionClient()
        self.repository_client = repository_client or RepositoryManagementClient()
        self.monitoring_client = monitoring_client or MonitoringClient()
        
        # Initialize audit logger
        self.audit_logger = audit_logger or SchedulingAuditLogger(self.config_dir)
        
        # Lazy-load backup orchestrator
        self._backup_orchestrator = backup_orchestrator
        
        # Execution tracking
        self._execution_history: Dict[str, List[ExecutionResult]] = {}
        self._active_executions: Dict[str, ExecutionContext] = {}
        
        self.logger.debug("AutomationEngine initialized")
    
    @property
    def backup_orchestrator(self):
        """Lazy-load backup orchestrator to avoid circular dependencies."""
        if self._backup_orchestrator is None:
            from ..services.backup_orchestrator import BackupOrchestrator
            from ..interfaces.repository_factory import RepositoryFactory
            from ..services.configuration_service import ConfigurationService
            
            config_service = ConfigurationService()
            repository_factory = RepositoryFactory(config_service)
            self._backup_orchestrator = BackupOrchestrator(
                repository_factory=repository_factory,
                configuration_provider=config_service
            )
        return self._backup_orchestrator
    
    async def execute_scheduled_backup(
        self,
        schedule_id: str,
        execution_context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute a scheduled backup with full integration.
        
        This method orchestrates the complete backup execution workflow:
        1. Retrieve and validate backup policy
        2. Retrieve and validate data selection
        3. Retrieve and validate repository credentials
        4. Execute backup operation
        5. Process and report results
        
        Args:
            schedule_id: Schedule identifier
            execution_context: Execution context information
            
        Returns:
            ExecutionResult with execution details and status
        """
        execution_id = execution_context.execution_id
        start_time = execution_context.start_time
        
        try:
            # Log execution start
            await self.audit_logger.log_execution_start(
                schedule_id,
                execution_id,
                execution_context
            )
            self.monitoring_client.report_execution_start(
                schedule_id,
                execution_id,
                self._context_to_dict(execution_context)
            )
            
            self.logger.info(f"Starting scheduled backup execution: {execution_id}")
            
            # Get schedule configuration
            schedule_config = await self._get_schedule_config(schedule_id)
            
            # Retrieve and validate policy
            self.logger.debug(f"Retrieving backup policy: {schedule_config.policy_id}")
            policy = self.policy_client.get_backup_policy(schedule_config.policy_id)
            if policy is None:
                raise PolicyValidationError(
                    f"Backup policy {schedule_config.policy_id} not found"
                )
            
            await self._validate_policy_for_execution(policy)
            
            # Retrieve and validate data selection
            self.logger.debug("Retrieving data selection configuration")
            data_selection = await self._get_data_selection_from_policy(policy)
            await self._validate_data_selection_for_execution(data_selection)
            
            # Retrieve and validate repository credentials
            self.logger.debug("Retrieving repository configuration")
            repository_config, credentials = await self._get_repository_from_policy(policy)
            await self._validate_repository_access(repository_config, credentials)
            
            # Execute backup operation
            self.logger.info("Executing backup operation")
            backup_job_config = self._create_backup_job_config(
                policy,
                data_selection,
                repository_config,
                credentials,
                execution_context
            )
            
            backup_result = self.backup_orchestrator.execute_backup_job(backup_job_config)
            
            # Process backup result
            execution_time = datetime.utcnow() - start_time
            execution_result = ExecutionResult(
                execution_id=execution_id,
                schedule_id=schedule_id,
                status=self._map_backup_status_to_execution_status(backup_result.status),
                backup_result=backup_result,
                execution_time=execution_time,
                error_details=backup_result.errors if backup_result.errors else None
            )
            
            # Log and report completion
            await self.audit_logger.log_execution_complete(execution_result)
            self.monitoring_client.report_execution_complete(
                self._execution_result_to_dict(execution_result)
            )
            
            self.logger.info(
                f"Scheduled backup execution completed: {execution_id} "
                f"(status: {execution_result.status.value})"
            )
            
            return execution_result
            
        except Exception as e:
            # Handle execution failure
            execution_time = datetime.utcnow() - start_time
            execution_result = ExecutionResult(
                execution_id=execution_id,
                schedule_id=schedule_id,
                status=ExecutionStatus.FAILED,
                execution_time=execution_time,
                error_details=[str(e)]
            )
            
            await self.audit_logger.log_execution_error(execution_result, e)
            self.monitoring_client.report_execution_error(
                self._execution_result_to_dict(execution_result),
                e
            )
            
            self.logger.error(
                f"Scheduled backup execution failed: {execution_id} - {str(e)}",
                exc_info=True
            )
            
            return execution_result
    
    async def _get_schedule_config(self, schedule_id: str):
        """
        Retrieve schedule configuration.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Schedule configuration
            
        Raises:
            ValueError: If schedule not found
        """
        from .schedule_storage import ScheduleStorage
        
        storage = ScheduleStorage(self.config_dir)
        schedule_config = storage.load_schedule(schedule_id)
        
        if schedule_config is None:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        return schedule_config
    
    async def _validate_policy_for_execution(self, policy: Any) -> None:
        """
        Validate that backup policy is suitable for automated execution.
        
        Args:
            policy: Backup policy to validate
            
        Raises:
            PolicyValidationError: If policy validation fails
        """
        from ..policy.types import PolicyStatus
        
        # Check policy status
        if hasattr(policy, 'status') and policy.status != PolicyStatus.ACTIVE:
            raise PolicyValidationError(
                f"Policy {policy.id} status is {policy.status.value}, must be ACTIVE"
            )
        
        # Check for required fields
        if hasattr(policy, 'target_repositories') and not policy.target_repositories:
            raise PolicyValidationError(
                f"Policy {policy.id} has no target repositories configured"
            )
        
        if hasattr(policy, 'data_selection_refs') and not policy.data_selection_refs:
            raise PolicyValidationError(
                f"Policy {policy.id} has no data selection references configured"
            )
        
        # Check for user interaction requirements
        if hasattr(policy, 'requires_user_interaction') and policy.requires_user_interaction:
            raise PolicyValidationError(
                f"Policy {policy.id} requires user interaction and cannot be scheduled"
            )
        
        self.logger.debug(f"Policy {policy.id} validated for execution")
    
    async def _get_data_selection_from_policy(self, policy: Any) -> Any:
        """
        Retrieve data selection configuration from policy.
        
        Args:
            policy: Backup policy
            
        Returns:
            Data selection configuration
            
        Raises:
            DataSelectionValidationError: If data selection cannot be retrieved
        """
        # Get first data selection reference from policy
        if hasattr(policy, 'data_selection_refs') and policy.data_selection_refs:
            selection_id = policy.data_selection_refs[0]
            data_selection = self.data_selection_client.get_selection_template(selection_id)
            
            if data_selection is None:
                raise DataSelectionValidationError(
                    f"Data selection {selection_id} not found"
                )
            
            return data_selection
        
        raise DataSelectionValidationError(
            f"Policy {policy.id} has no data selection references"
        )
    
    async def _validate_data_selection_for_execution(self, data_selection: Any) -> None:
        """
        Validate that data selection is accessible for automated execution.
        
        Args:
            data_selection: Data selection to validate
            
        Raises:
            DataSelectionValidationError: If validation fails
        """
        # Check that all include paths are accessible
        if hasattr(data_selection, 'include_paths'):
            for path in data_selection.include_paths:
                path_obj = Path(path) if isinstance(path, str) else path
                
                if not path_obj.exists():
                    raise DataSelectionValidationError(
                        f"Include path {path_obj} does not exist"
                    )
                
                if not os.access(path_obj, os.R_OK):
                    raise DataSelectionValidationError(
                        f"Include path {path_obj} is not readable"
                    )
        
        self.logger.debug("Data selection validated for execution")
    
    async def _get_repository_from_policy(self, policy: Any) -> tuple[Dict[str, Any], Any]:
        """
        Retrieve repository configuration and credentials from policy.
        
        Args:
            policy: Backup policy
            
        Returns:
            Tuple of (repository_config, credentials)
            
        Raises:
            RepositoryValidationError: If repository cannot be retrieved
        """
        # Get first target repository from policy
        if hasattr(policy, 'target_repositories') and policy.target_repositories:
            repository_id = policy.target_repositories[0]
            repository_config = self.repository_client.get_repository_config(repository_id)
            
            if repository_config is None:
                raise RepositoryValidationError(
                    f"Repository {repository_id} not found"
                )
            
            # Credentials are managed by repository client
            # For now, return None as credentials are handled internally
            credentials = None
            
            return repository_config, credentials
        
        raise RepositoryValidationError(
            f"Policy {policy.id} has no target repositories"
        )
    
    async def _validate_repository_access(
        self,
        repository_config: Dict[str, Any],
        credentials: Any
    ) -> None:
        """
        Validate repository accessibility with provided credentials.
        
        Args:
            repository_config: Repository configuration
            credentials: Repository credentials
            
        Raises:
            RepositoryValidationError: If validation fails
        """
        # Basic validation - check repository configuration
        if not repository_config.get('uri') and not repository_config.get('url'):
            raise RepositoryValidationError(
                "Repository has no URI/URL configured"
            )
        
        # Note: Actual credential validation and repository connection testing
        # should be done at execution time to avoid exposing credentials
        # during validation phase
        
        self.logger.debug("Repository access validated")
    
    def _create_backup_job_config(
        self,
        policy: Any,
        data_selection: Any,
        repository_config: Dict[str, Any],
        credentials: Any,
        execution_context: ExecutionContext
    ) -> BackupJobConfig:
        """
        Create backup job configuration from policy and execution context.
        
        Args:
            policy: Backup policy
            data_selection: Data selection configuration
            repository_config: Repository configuration
            credentials: Repository credentials
            execution_context: Execution context
            
        Returns:
            BackupJobConfig ready for execution
        """
        # Extract repository name
        repository_name = repository_config.get('name', repository_config.get('id', 'unknown'))
        
        # Extract target paths from data selection
        target_paths = []
        if hasattr(data_selection, 'include_paths'):
            target_paths = [str(p) for p in data_selection.include_paths]
        
        # Create backup job configuration
        job_config = BackupJobConfig(
            job_id=execution_context.execution_id,
            repository_name=repository_name,
            target_paths=target_paths,
            execution_mode=ExecutionMode.SCHEDULED,
            tags=[f"schedule:{execution_context.schedule_id}"],
            metadata={
                'schedule_id': execution_context.schedule_id,
                'policy_id': policy.id if hasattr(policy, 'id') else 'unknown',
                'triggered_by': execution_context.triggered_by.value,
                'execution_time': execution_context.start_time.isoformat()
            }
        )
        
        self.logger.debug(f"Created backup job config: {job_config.job_id}")
        return job_config
    
    def _map_backup_status_to_execution_status(self, backup_status: BackupStatus) -> ExecutionStatus:
        """
        Map backup status to execution status.
        
        Args:
            backup_status: Backup operation status
            
        Returns:
            Corresponding execution status
        """
        status_mapping = {
            BackupStatus.COMPLETED: ExecutionStatus.SUCCESS,
            BackupStatus.FAILED: ExecutionStatus.FAILED,
            BackupStatus.CANCELLED: ExecutionStatus.CANCELLED,
            BackupStatus.RETRYING: ExecutionStatus.RETRYING,
        }
        
        return status_mapping.get(backup_status, ExecutionStatus.FAILED)
    
    def _context_to_dict(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Convert execution context to dictionary.
        
        Args:
            context: Execution context
            
        Returns:
            Dictionary representation
        """
        return {
            'execution_id': context.execution_id,
            'schedule_id': context.schedule_id,
            'triggered_by': context.triggered_by.value,
            'start_time': context.start_time.isoformat(),
            'platform': context.platform,
            'user_context': context.user_context
        }
    
    def _execution_result_to_dict(self, result: ExecutionResult) -> Dict[str, Any]:
        """
        Convert execution result to dictionary.
        
        Args:
            result: Execution result
            
        Returns:
            Dictionary representation
        """
        result_dict = {
            'execution_id': result.execution_id,
            'schedule_id': result.schedule_id,
            'status': result.status.value,
            'execution_time_seconds': result.execution_time.total_seconds(),
            'retry_count': result.retry_count
        }
        
        if result.backup_result:
            result_dict.update({
                'backup_success': result.backup_result.status == BackupStatus.COMPLETED,
                'snapshot_id': result.backup_result.snapshot_id,
                'files_processed': result.backup_result.files_processed,
                'bytes_processed': result.backup_result.bytes_processed
            })
        
        if result.error_details:
            result_dict['error_details'] = result.error_details
        
        if result.next_retry_time:
            result_dict['next_retry_time'] = result.next_retry_time.isoformat()
        
        return result_dict
    
    async def execute_with_retry(
        self,
        schedule_id: str,
        execution_context: ExecutionContext,
        retry_config: Optional[RetryConfig] = None
    ) -> ExecutionResult:
        """
        Execute scheduled backup with retry logic and exponential backoff.
        
        This method implements comprehensive retry logic with:
        - Exponential backoff between retries
        - Error classification to determine retry eligibility
        - Progress tracking and logging
        - Monitoring integration
        
        Args:
            schedule_id: Schedule identifier
            execution_context: Execution context
            retry_config: Optional retry configuration (uses defaults if not provided)
            
        Returns:
            ExecutionResult with final execution status
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        attempt = 0
        last_error = None
        
        while attempt < retry_config.max_attempts:
            attempt += 1
            
            try:
                self.logger.info(
                    f"Executing scheduled backup (attempt {attempt}/{retry_config.max_attempts}): "
                    f"{schedule_id}"
                )
                
                # Update execution context for retry
                if attempt > 1:
                    execution_context.triggered_by = ExecutionTrigger.RETRY
                
                # Execute backup
                result = await self.execute_scheduled_backup(schedule_id, execution_context)
                
                # Track execution in history
                self._add_to_execution_history(schedule_id, result)
                
                # Check if execution was successful
                if result.status == ExecutionStatus.SUCCESS:
                    self.logger.info(
                        f"Scheduled backup succeeded on attempt {attempt}: {schedule_id}"
                    )
                    return result
                
                # Classify error to determine if retry is appropriate
                error_severity = self._classify_error(result)
                
                if error_severity == ErrorSeverity.FATAL:
                    self.logger.error(
                        f"Fatal error encountered, not retrying: {schedule_id}"
                    )
                    return result
                
                if error_severity == ErrorSeverity.PERSISTENT and attempt >= 2:
                    self.logger.warning(
                        f"Persistent error detected after {attempt} attempts, "
                        f"stopping retries: {schedule_id}"
                    )
                    return result
                
                # Store error for potential retry
                last_error = result
                
                # Calculate retry delay with exponential backoff
                if attempt < retry_config.max_attempts:
                    delay_minutes = self._calculate_retry_delay(
                        attempt,
                        retry_config
                    )
                    
                    next_retry_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
                    result.next_retry_time = next_retry_time
                    result.retry_count = attempt
                    
                    self.logger.info(
                        f"Scheduling retry {attempt + 1} in {delay_minutes} minutes "
                        f"for {schedule_id}"
                    )
                    
                    # Report retry to monitoring
                    self.monitoring_client.report_execution_complete(
                        self._execution_result_to_dict(result)
                    )
                    
                    # Wait before retry
                    await asyncio.sleep(delay_minutes * 60)
                
            except Exception as e:
                self.logger.error(
                    f"Unexpected error during execution attempt {attempt}: {str(e)}",
                    exc_info=True
                )
                last_error = ExecutionResult(
                    execution_id=execution_context.execution_id,
                    schedule_id=schedule_id,
                    status=ExecutionStatus.FAILED,
                    execution_time=timedelta(),
                    error_details=[str(e)],
                    retry_count=attempt
                )
                
                # Check if we should retry
                if attempt < retry_config.max_attempts:
                    delay_minutes = self._calculate_retry_delay(attempt, retry_config)
                    await asyncio.sleep(delay_minutes * 60)
                else:
                    break
        
        # All retries exhausted
        self.logger.error(
            f"All {retry_config.max_attempts} retry attempts exhausted for {schedule_id}"
        )
        
        if last_error:
            last_error.retry_count = retry_config.max_attempts
            return last_error
        
        # Fallback error result
        return ExecutionResult(
            execution_id=execution_context.execution_id,
            schedule_id=schedule_id,
            status=ExecutionStatus.FAILED,
            execution_time=timedelta(),
            error_details=["All retry attempts exhausted"],
            retry_count=retry_config.max_attempts
        )
    
    def _calculate_retry_delay(
        self,
        attempt: int,
        retry_config: RetryConfig
    ) -> int:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (1-based)
            retry_config: Retry configuration
            
        Returns:
            Delay in minutes
        """
        delay = retry_config.initial_delay_minutes * (
            retry_config.backoff_multiplier ** (attempt - 1)
        )
        
        # Cap at maximum delay
        delay = min(delay, retry_config.max_delay_minutes)
        
        return int(delay)
    
    def _classify_error(self, result: ExecutionResult) -> ErrorSeverity:
        """
        Classify error severity to determine retry eligibility.
        
        Args:
            result: Execution result with error details
            
        Returns:
            Error severity classification
        """
        if not result.error_details:
            return ErrorSeverity.TRANSIENT
        
        error_text = " ".join(result.error_details).lower()
        
        # Fatal errors - do not retry
        fatal_patterns = [
            "policy.*not found",
            "repository.*not found",
            "data selection.*not found",
            "requires user interaction",
            "permission denied",
            "access denied",
            "authentication failed",
            "invalid credentials"
        ]
        
        for pattern in fatal_patterns:
            if pattern in error_text:
                return ErrorSeverity.FATAL
        
        # Persistent errors - retry once or twice
        persistent_patterns = [
            "not readable",
            "does not exist",
            "configuration.*invalid",
            "validation.*failed"
        ]
        
        for pattern in persistent_patterns:
            if pattern in error_text:
                return ErrorSeverity.PERSISTENT
        
        # Transient errors - retry with backoff
        transient_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "unavailable",
            "busy"
        ]
        
        for pattern in transient_patterns:
            if pattern in error_text:
                return ErrorSeverity.TRANSIENT
        
        # Default to transient for unknown errors
        return ErrorSeverity.TRANSIENT
    
    def _add_to_execution_history(
        self,
        schedule_id: str,
        result: ExecutionResult
    ) -> None:
        """
        Add execution result to history.
        
        Args:
            schedule_id: Schedule identifier
            result: Execution result to add
        """
        if schedule_id not in self._execution_history:
            self._execution_history[schedule_id] = []
        
        self._execution_history[schedule_id].append(result)
        
        # Keep only last 100 executions per schedule
        if len(self._execution_history[schedule_id]) > 100:
            self._execution_history[schedule_id] = self._execution_history[schedule_id][-100:]
    
    def get_execution_history(
        self,
        schedule_id: str,
        limit: int = 10
    ) -> List[ExecutionResult]:
        """
        Get execution history for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            limit: Maximum number of results to return
            
        Returns:
            List of execution results (most recent first)
        """
        history = self._execution_history.get(schedule_id, [])
        return list(reversed(history[-limit:]))
    
    def get_execution_statistics(
        self,
        schedule_id: str
    ) -> Dict[str, Any]:
        """
        Get execution statistics for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            Dictionary with execution statistics
        """
        history = self._execution_history.get(schedule_id, [])
        
        if not history:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'success_rate': 0.0,
                'average_execution_time': 0.0,
                'last_execution': None
            }
        
        total = len(history)
        successful = sum(1 for r in history if r.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for r in history if r.status == ExecutionStatus.FAILED)
        
        avg_time = sum(r.execution_time.total_seconds() for r in history) / total
        
        return {
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': failed,
            'success_rate': (successful / total) * 100 if total > 0 else 0.0,
            'average_execution_time': avg_time,
            'last_execution': history[-1] if history else None
        }
    
    def track_execution_progress(
        self,
        execution_id: str,
        progress_data: Dict[str, Any]
    ) -> None:
        """
        Track execution progress for monitoring.
        
        Args:
            execution_id: Execution identifier
            progress_data: Progress information
        """
        self.logger.debug(f"Execution progress for {execution_id}: {progress_data}")
        
        # Report progress to monitoring system
        try:
            self.monitoring_client.report_execution_complete({
                'execution_id': execution_id,
                'status': 'in_progress',
                'progress': progress_data
            })
        except Exception as e:
            self.logger.warning(f"Failed to report progress: {e}")
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel an active execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            True if execution was cancelled, False otherwise
        """
        # Check if execution is active
        if execution_id not in self._active_executions:
            self.logger.warning(f"Execution {execution_id} not found or not active")
            return False
        
        try:
            # Attempt to cancel through backup orchestrator
            cancelled = self.backup_orchestrator.cancel_backup(execution_id)
            
            if cancelled:
                context = self._active_executions.pop(execution_id)
                
                # Create cancellation result
                result = ExecutionResult(
                    execution_id=execution_id,
                    schedule_id=context.schedule_id,
                    status=ExecutionStatus.CANCELLED,
                    execution_time=datetime.utcnow() - context.start_time,
                    error_details=["Execution cancelled by user"]
                )
                
                # Log and report cancellation
                await self.audit_logger.log_execution_complete(result)
                self.monitoring_client.report_execution_complete(
                    self._execution_result_to_dict(result)
                )
                
                self.logger.info(f"Execution cancelled: {execution_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
