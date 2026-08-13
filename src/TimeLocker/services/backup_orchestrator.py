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
"""

import logging
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Empty
from threading import Lock

from ..interfaces import (
    IBackupOrchestrator,
    IRepositoryFactory,
    IConfigurationProvider,
    BackupStatus,
    BackupResult,
    BackupOrchestratorError,
    InvalidBackupConfigurationError,
    BackupExecutionError
)
from ..interfaces.data_models import (
    BackupJobConfig,
    BackupJob,
    ValidationResult as JobValidationResult,
    ExecutionMode,
    ExecutionContext,
    ToolConfiguration
)
from ..backup_target import BackupTarget
from ..file_selections import FileSelection, SelectionType
from ..selection_service_interface import SelectionServiceInterface
from ..utils import (
    with_error_handling,
    with_retry,
    profile_operation,
    start_operation_tracking,
    update_operation_tracking,
    complete_operation_tracking
)
from .job_executor import JobExecutor, ErrorClassifier
from .integrity_validation_service import IntegrityValidationService
from .data_selection_integration_service import DataSelectionIntegrationService
from .backup_error_reporter import BackupErrorReporter, BackupError, BackupWarning
from .backup_notification_service import BackupNotificationService, BackupEventType
from .tool_manager import ToolManager
from ..monitoring.notification_service import NotificationService
from ..monitoring.status_reporter import StatusReporter

logger = logging.getLogger(__name__)


class BackupOrchestrator(IBackupOrchestrator):
    """
    High-level backup orchestrator following SRP and coordinating backup workflows.
    
    This orchestrator focuses solely on backup coordination and workflow management,
    delegating specific responsibilities to appropriate services.
    """

    def __init__(self,
                 repository_factory: IRepositoryFactory,
                 configuration_provider: IConfigurationProvider,
                 max_concurrent_backups: int = 2,
                 policy_integration_service=None,
                 selection_service: Optional[SelectionServiceInterface] = None,
                 job_executor: Optional[JobExecutor] = None,
                 integrity_validation_service: Optional[IntegrityValidationService] = None,
                 data_selection_integration_service: Optional[DataSelectionIntegrationService] = None,
                 notification_service: Optional[NotificationService] = None,
                 status_reporter: Optional[StatusReporter] = None,
                 tool_manager: Optional[ToolManager] = None):
        """
        Initialize backup orchestrator.
        
        Args:
            repository_factory: Factory for creating repository instances
            configuration_provider: Provider for configuration access
            max_concurrent_backups: Maximum number of concurrent backup operations
            policy_integration_service: Optional policy integration service for policy-driven backups
            selection_service: Optional selection service for data selection integration
            job_executor: Optional job executor for advanced retry logic
            integrity_validation_service: Optional integrity validation service
            data_selection_integration_service: Optional data selection integration service
            notification_service: Optional notification service for sending notifications
            status_reporter: Optional status reporter for operation tracking
            tool_manager: Optional tool manager for tool capabilities and parallel optimization
        """
        self._repository_factory = repository_factory
        self._configuration_provider = configuration_provider
        self._max_concurrent_backups = max_concurrent_backups
        self._policy_integration_service = policy_integration_service
        self._selection_service = selection_service or SelectionServiceInterface()
        self._job_executor = job_executor or JobExecutor()
        self._integrity_validation_service = integrity_validation_service or IntegrityValidationService()
        self._data_selection_integration_service = data_selection_integration_service or DataSelectionIntegrationService()
        self._tool_manager = tool_manager or ToolManager()
        
        # Initialize notification and error reporting services
        self._notification_service = notification_service or NotificationService()
        self._status_reporter = status_reporter or StatusReporter()
        self._backup_notification_service = BackupNotificationService(
            self._notification_service,
            self._status_reporter
        )
        self._error_reporter = BackupErrorReporter()

        # Track active backup operations
        self._active_backups: Dict[str, BackupResult] = {}
        self._backup_history: List[BackupResult] = []
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_backups)
        self._futures: Dict[str, Future] = {}

        # Job queue management
        self._job_queue: Queue = Queue()
        self._queued_jobs: Dict[str, BackupJobConfig] = {}
        self._queue_lock = Lock()

        logger.debug(f"BackupOrchestrator initialized with max_concurrent_backups={max_concurrent_backups}")

    def execute_backup_job(self, job_config: BackupJobConfig) -> BackupResult:
        """
        Execute a backup job with full orchestration.
        
        This method provides comprehensive job execution including validation,
        preparation, integration with Policy Management and Data Selection systems,
        and proper error handling with retry logic.
        
        Args:
            job_config: Backup job configuration
            
        Returns:
            BackupResult with operation details
            
        Raises:
            BackupOrchestratorError: If backup job cannot be executed
        """
        logger.info(f"Executing backup job: {job_config.job_id}")
        
        try:
            # Validate job configuration
            validation_result = self.validate_job_configuration(job_config)
            if not validation_result.is_valid:
                error_msg = f"Job validation failed: {'; '.join(validation_result.errors)}"
                logger.error(error_msg)
                raise InvalidBackupConfigurationError(error_msg)
            
            # Log warnings
            for warning in validation_result.warnings:
                logger.warning(f"Job validation warning: {warning}")
            
            # Prepare backup job
            backup_job = self.prepare_backup_job(job_config)
            
            # Execute based on mode
            if job_config.dry_run:
                return self._execute_job_dry_run(backup_job)
            else:
                return self._execute_job_with_retry(backup_job)
                
        except Exception as e:
            logger.error(f"Backup job execution failed: {e}")
            raise BackupExecutionError(f"Backup job execution failed: {e}") from e

    def validate_job_configuration(self, job_config: BackupJobConfig) -> JobValidationResult:
        """
        Validate job configuration against tool capabilities and system state.
        
        Args:
            job_config: Job configuration to validate
            
        Returns:
            JobValidationResult with validation details
        """
        logger.debug(f"Validating job configuration: {job_config.job_id}")
        
        result = JobValidationResult(is_valid=True)
        
        try:
            # Validate repository exists
            repositories = self._configuration_provider.get_repositories()
            repo_exists = any(
                r['name'] == job_config.repository_id or r.get('id') == job_config.repository_id
                for r in repositories
            )
            
            if not repo_exists:
                result.add_error(f"Repository '{job_config.repository_id}' not found")
            
            # Validate targets if specified
            if job_config.target_names:
                target_configs = self._configuration_provider.get_backup_targets()
                for target_name in job_config.target_names:
                    target_exists = any(t['name'] == target_name for t in target_configs)
                    if not target_exists:
                        result.add_error(f"Backup target '{target_name}' not found")
            
            # Validate policy if specified
            if job_config.policy_id and self._policy_integration_service:
                try:
                    # Check if policy exists (implementation depends on policy service)
                    logger.debug(f"Policy validation for: {job_config.policy_id}")
                    result.add_warning("Policy validation not fully implemented")
                except Exception as e:
                    result.add_warning(f"Could not validate policy: {e}")
            
            # Validate data selection if specified
            if job_config.data_selection_id:
                logger.debug(f"Data selection validation for: {job_config.data_selection_id}")
                try:
                    # Retrieve and validate selection configuration
                    selection_config = self._data_selection_integration_service.retrieve_selection_config(
                        job_config.data_selection_id
                    )
                    
                    if selection_config:
                        # Validate compatibility with tool
                        compatibility_result = self._data_selection_integration_service.validate_selection_compatibility(
                            selection_config,
                            job_config.tool_type
                        )
                        
                        if not compatibility_result.is_compatible:
                            result.add_error(
                                f"Data selection '{job_config.data_selection_id}' is not compatible "
                                f"with tool '{job_config.tool_type}'"
                            )
                            for feature in compatibility_result.unsupported_features:
                                result.add_error(f"Unsupported feature: {feature}")
                        
                        # Add warnings
                        for warning in compatibility_result.warnings:
                            result.add_warning(f"Data selection: {warning}")
                        
                        result.validation_details['data_selection_compatible'] = compatibility_result.is_compatible
                    else:
                        result.add_error(f"Data selection '{job_config.data_selection_id}' not found")
                        result.validation_details['data_selection_compatible'] = False
                        
                except Exception as e:
                    result.add_warning(f"Could not validate data selection: {e}")
                    result.validation_details['data_selection_compatible'] = False
            
            # Validate retry configuration
            if job_config.retry_config.max_retries < 0:
                result.add_error("max_retries must be non-negative")
            
            # Validate tool type
            supported_tools = ["restic", "borg", "duplicity"]
            if job_config.tool_type not in supported_tools:
                result.add_warning(
                    f"Tool type '{job_config.tool_type}' may not be fully supported. "
                    f"Supported tools: {', '.join(supported_tools)}"
                )
            
            result.validation_details['repository_validated'] = repo_exists
            result.validation_details['targets_validated'] = bool(job_config.target_names)
            result.validation_details['policy_validated'] = bool(job_config.policy_id)
            
            logger.debug(
                f"Job validation complete: valid={result.is_valid}, "
                f"errors={len(result.errors)}, warnings={len(result.warnings)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Job validation failed with exception: {e}")
            result.add_error(f"Validation error: {e}")
            return result

    def prepare_backup_job(self, job_config: BackupJobConfig) -> BackupJob:
        """
        Prepare a backup job for execution.
        
        This method integrates with Policy Management and Data Selection systems
        to build a complete BackupJob ready for execution.
        
        Args:
            job_config: Job configuration
            
        Returns:
            BackupJob ready for execution
            
        Raises:
            BackupOrchestratorError: If job preparation fails
        """
        logger.info(f"Preparing backup job: {job_config.job_id}")
        
        try:
            # Initialize backup job
            backup_job = BackupJob(
                config=job_config,
                tool_configuration=ToolConfiguration(
                    tool_type=job_config.tool_type,
                    parallel_operations=1,
                    encryption_enabled=True,
                    integrity_check_enabled=True
                ),
                execution_context=ExecutionContext(
                    start_time=time.time(),
                    attempt_number=1
                )
            )
            
            # Integrate with Policy Management if policy_id is specified
            if job_config.policy_id and self._policy_integration_service:
                logger.debug(f"Integrating with policy: {job_config.policy_id}")
                try:
                    # Get policy configuration
                    # This would call the policy service to get policy details
                    backup_job.policy_config = {
                        'policy_id': job_config.policy_id,
                        'integrated': True
                    }
                except Exception as e:
                    logger.warning(f"Could not integrate with policy: {e}")
            
            # Integrate with Data Selection if data_selection_id is specified
            if job_config.data_selection_id:
                logger.debug(f"Integrating with data selection: {job_config.data_selection_id}")
                try:
                    # Retrieve data selection configuration
                    selection_config = self._data_selection_integration_service.retrieve_selection_config(
                        job_config.data_selection_id
                    )
                    
                    if selection_config:
                        # Validate compatibility with backup tool
                        compatibility_result = self._data_selection_integration_service.validate_selection_compatibility(
                            selection_config,
                            job_config.tool_type
                        )
                        
                        # Log warnings
                        for warning in compatibility_result.warnings:
                            logger.warning(f"Selection compatibility warning: {warning}")
                        
                        # Apply selection to job
                        backup_job = self._data_selection_integration_service.apply_selection_to_job(
                            backup_job,
                            selection_config
                        )
                        
                        # Store selection config in job metadata
                        backup_job.data_selection_config = {
                            'selection_id': job_config.data_selection_id,
                            'integrated': True,
                            'is_compatible': compatibility_result.is_compatible,
                            'warnings': compatibility_result.warnings,
                            'unsupported_features': compatibility_result.unsupported_features
                        }
                        
                        logger.info(
                            f"Data selection integrated: compatible={compatibility_result.is_compatible}, "
                            f"warnings={len(compatibility_result.warnings)}"
                        )
                    else:
                        logger.warning(f"Data selection config not found: {job_config.data_selection_id}")
                        backup_job.data_selection_config = {
                            'selection_id': job_config.data_selection_id,
                            'integrated': False,
                            'error': 'Selection configuration not found'
                        }
                except Exception as e:
                    logger.error(f"Could not integrate with data selection: {e}")
                    backup_job.data_selection_config = {
                        'selection_id': job_config.data_selection_id,
                        'integrated': False,
                        'error': str(e)
                    }
            
            # Get source paths from targets
            if job_config.target_names:
                target_configs = self._configuration_provider.get_backup_targets()
                for target_name in job_config.target_names:
                    target_config = next(
                        (t for t in target_configs if t['name'] == target_name),
                        None
                    )
                    if target_config:
                        backup_job.source_paths.extend(target_config['paths'])
                        backup_job.exclude_patterns.extend(
                            target_config.get('exclude_patterns', [])
                        )
                        backup_job.include_patterns.extend(
                            target_config.get('include_patterns', [])
                        )
            
            # Configure tool-specific options
            backup_job.tool_configuration.tool_specific_options = {
                'tags': job_config.tags,
                'compression': 'auto',
                'exclude_caches': True
            }
            
            logger.info(
                f"Job prepared: {len(backup_job.source_paths)} source paths, "
                f"{len(backup_job.exclude_patterns)} exclude patterns"
            )
            
            return backup_job
            
        except Exception as e:
            logger.error(f"Job preparation failed: {e}")
            raise BackupOrchestratorError(f"Job preparation failed: {e}") from e

    def queue_backup_job(self, job_config: BackupJobConfig) -> str:
        """
        Queue a backup job for execution.
        
        Args:
            job_config: Job configuration to queue
            
        Returns:
            Job ID for tracking
            
        Raises:
            BackupOrchestratorError: If job cannot be queued
        """
        logger.info(f"Queueing backup job: {job_config.job_id}")
        
        try:
            with self._queue_lock:
                # Validate job before queueing
                validation_result = self.validate_job_configuration(job_config)
                if not validation_result.is_valid:
                    error_msg = f"Cannot queue invalid job: {'; '.join(validation_result.errors)}"
                    raise InvalidBackupConfigurationError(error_msg)
                
                # Add to queue
                self._job_queue.put(job_config)
                self._queued_jobs[job_config.job_id] = job_config
                
                logger.info(
                    f"Job queued: {job_config.job_id}, "
                    f"queue size: {self._job_queue.qsize()}"
                )
                
                return job_config.job_id
                
        except Exception as e:
            logger.error(f"Failed to queue job: {e}")
            raise BackupOrchestratorError(f"Failed to queue job: {e}") from e

    def get_queued_jobs(self) -> List[BackupJobConfig]:
        """
        Get list of queued backup jobs.
        
        Returns:
            List of queued job configurations
        """
        with self._queue_lock:
            return list(self._queued_jobs.values())

    def cancel_queued_job(self, job_id: str) -> bool:
        """
        Cancel a queued backup job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if job was cancelled, False if not found or already running
        """
        logger.info(f"Attempting to cancel queued job: {job_id}")
        
        with self._queue_lock:
            if job_id in self._queued_jobs:
                # Remove from queued jobs
                del self._queued_jobs[job_id]
                
                # Note: Removing from Queue is complex, so we'll mark it as cancelled
                # and skip it during processing
                logger.info(f"Queued job cancelled: {job_id}")
                return True
            
            logger.warning(f"Job not found in queue: {job_id}")
            return False

    def _execute_job_dry_run(self, backup_job: BackupJob) -> BackupResult:
        """
        Execute a dry run of a backup job.
        
        Args:
            backup_job: Backup job to execute
            
        Returns:
            BackupResult with dry run details
        """
        logger.info(f"Executing dry run for job: {backup_job.config.job_id}")
        
        backup_result = BackupResult(
            status=BackupStatus.RUNNING,
            repository_name=backup_job.config.repository_id,
            target_names=backup_job.config.target_names,
            start_time=time.time(),
            metadata={
                'job_id': backup_job.config.job_id,
                'dry_run': True,
                'execution_mode': backup_job.config.execution_mode.value
            }
        )
        
        try:
            # Simulate backup process
            total_files = 0
            total_bytes = 0
            
            for path_str in backup_job.source_paths:
                try:
                    path = Path(path_str)
                    if path.exists():
                        if path.is_file():
                            total_files += 1
                            total_bytes += path.stat().st_size
                        elif path.is_dir():
                            for file_path in path.rglob('*'):
                                if file_path.is_file():
                                    total_files += 1
                                    total_bytes += file_path.stat().st_size
                except Exception as e:
                    backup_result.warnings.append(f"Could not analyze path {path_str}: {e}")
            
            backup_result.files_processed = total_files
            backup_result.bytes_processed = total_bytes
            backup_result.status = BackupStatus.COMPLETED
            backup_result.snapshot_id = f"dry-run-{int(time.time())}"
            backup_result.end_time = time.time()
            
            logger.info(
                f"Dry run completed: {total_files} files, "
                f"{total_bytes / (1024**3):.2f} GB"
            )
            
        except Exception as e:
            backup_result.errors.append(f"Dry run failed: {e}")
            backup_result.status = BackupStatus.FAILED
            backup_result.end_time = time.time()
        
        self._attach_selection_warnings(backup_job, backup_result)
        return backup_result

    def _attach_selection_warnings(self, backup_job: BackupJob, backup_result: BackupResult) -> None:
        """
        Surface selection translation/compatibility warnings to the callers.
        """
        if not backup_job or not backup_result or not backup_job.config:
            return

        warnings_seen: Set[str] = set(backup_result.warnings)

        def append_warning(message: str) -> None:
            if not message:
                return
            if message not in warnings_seen:
                backup_result.warnings.append(message)
                warnings_seen.add(message)

        selection_metadata = backup_job.config.metadata or {}
        selection_warnings = list(selection_metadata.get('selection_warnings', []))
        if selection_warnings:
            backup_result.metadata.setdefault('selection_warnings', []).extend(selection_warnings)
            for warning in selection_warnings:
                append_warning(f"Selection warning: {warning}")

        pattern_entries = selection_metadata.get('unsupported_selection_patterns', []) or []
        if pattern_entries:
            backup_result.metadata.setdefault('unsupported_selection_patterns', []).extend(pattern_entries)
            for entry in pattern_entries:
                pattern = entry.get('pattern', '<pattern>')
                syntax = entry.get('syntax', 'glob')
                reason = entry.get('reason', 'unsupported by backup tool')
                append_warning(
                    f"Selection pattern '{pattern}' ({syntax}) skipped: {reason}"
                )

        selection_config = getattr(backup_job, 'data_selection_config', None) or {}
        compat_warnings = selection_config.get('warnings', []) or []
        if compat_warnings:
            backup_result.metadata.setdefault('selection_warnings', []).extend(compat_warnings)
            for warning in compat_warnings:
                append_warning(f"Selection warning: {warning}")

        unsupported_features = selection_config.get('unsupported_features', []) or []
        if unsupported_features:
            backup_result.metadata.setdefault('unsupported_selection_features', []).extend(unsupported_features)
            for feature in unsupported_features:
                append_warning(
                    f"Selection feature '{feature}' is not supported by tool "
                    f"'{backup_job.config.tool_type}'"
                )

    def _execute_job_with_retry(self, backup_job: BackupJob) -> BackupResult:
        """
        Execute a backup job with advanced retry logic.
        
        This method uses the JobExecutor for sophisticated retry handling
        with error classification and exponential backoff. It also monitors
        parallel execution performance.
        
        Args:
            backup_job: Backup job to execute
            
        Returns:
            BackupResult with execution details
        """
        logger.info(f"Executing job with advanced retry: {backup_job.config.job_id}")
        
        # Start parallel execution monitoring if parallel operations are configured
        if backup_job.tool_configuration and backup_job.tool_configuration.parallel_operations > 1:
            self._tool_manager.monitor_parallel_execution(
                operation_id=backup_job.config.job_id,
                tool_type=backup_job.config.tool_type,
                configured_parallelism=backup_job.tool_configuration.parallel_operations
            )
            logger.debug(
                f"Started parallel execution monitoring for {backup_job.config.job_id} "
                f"with parallelism={backup_job.tool_configuration.parallel_operations}"
            )
        
        # Use JobExecutor for advanced retry logic
        execution_result = self._job_executor.execute_with_retry(
            job=backup_job,
            execution_func=self._execute_backup_job_internal,
            retry_config=backup_job.config.retry_config
        )
        
        # Add retry information to result metadata
        result = execution_result.backup_result
        result.metadata['total_attempts'] = execution_result.total_attempts
        result.metadata['retry_history'] = execution_result.retry_history
        
        if execution_result.final_error_classification:
            result.metadata['final_error_category'] = execution_result.final_error_classification.category.value
            result.metadata['suggested_action'] = execution_result.final_error_classification.suggested_action
        
        # Perform integrity validation if backup completed
        if result.status == BackupStatus.COMPLETED:
            logger.info(f"Performing integrity validation for job: {backup_job.config.job_id}")
            validation_result = self._integrity_validation_service.validate_backup_integrity(
                backup_job,
                result
            )
            
            # Integrate validation results with backup result
            result = self._integrity_validation_service.integrate_validation_with_backup_result(
                result,
                validation_result
            )
            
            logger.info(
                f"Integrity validation complete: status={validation_result.status.value}, "
                f"issues={len(validation_result.issues)}"
            )
        
        # Get parallel execution report if monitoring was enabled
        if backup_job.tool_configuration and backup_job.tool_configuration.parallel_operations > 1:
            parallel_report = self._tool_manager.get_parallel_execution_report(
                backup_job.config.job_id
            )
            if parallel_report:
                result.metadata['parallel_execution'] = parallel_report
                logger.info(
                    f"Parallel execution report for {backup_job.config.job_id}: "
                    f"efficiency={parallel_report['parallel_efficiency']:.2f}, "
                    f"rating={parallel_report['efficiency_rating']}, "
                    f"degradation_events={parallel_report['degradation_events']}"
                )
        
        self._attach_selection_warnings(backup_job, result)
        
        logger.info(
            f"Job execution completed: {backup_job.config.job_id}, "
            f"status={result.status.value}, attempts={execution_result.total_attempts}"
        )
        
        return result

    def _execute_backup_job_internal(self, backup_job: BackupJob) -> BackupResult:
        """
        Internal method to execute a backup job.
        
        Args:
            backup_job: Backup job to execute
            
        Returns:
            BackupResult with execution details
        """
        logger.debug(f"Internal execution for job: {backup_job.config.job_id}")
        
        # Send backup started notification
        self._backup_notification_service.notify_backup_event(
            event_type=BackupEventType.BACKUP_STARTED,
            operation_id=backup_job.config.job_id,
            repository_id=backup_job.config.repository_id,
            message=f"Starting backup for repository {backup_job.config.repository_id}"
        )
        
        backup_result = BackupResult(
            status=BackupStatus.RUNNING,
            repository_name=backup_job.config.repository_id,
            target_names=backup_job.config.target_names,
            start_time=time.time(),
            metadata={
                'job_id': backup_job.config.job_id,
                'attempt': backup_job.execution_context.attempt_number
            }
        )
        
        try:
            # Get repository configuration
            repositories = self._configuration_provider.get_repositories()
            repo_config = next(
                (r for r in repositories 
                 if r['name'] == backup_job.config.repository_id or 
                    r.get('id') == backup_job.config.repository_id),
                None
            )
            
            if not repo_config:
                backup_result.errors.append(
                    f"Repository '{backup_job.config.repository_id}' not found"
                )
                backup_result.status = BackupStatus.FAILED
                return backup_result
            
            # Create repository instance
            password = backup_job.config.metadata.get('password')
            repository = self._repository_factory.create_repository(
                repo_config['uri'],
                password=password,
                repository_name=backup_job.config.repository_id
            )
            
            # Create backup targets
            targets = self._create_backup_targets_from_job(backup_job)
            
            # Execute backup with resource monitoring
            result = repository.backup_target(
                targets,
                backup_job.config.tags
            )
            
            # Update parallel execution metrics if monitoring is enabled
            if backup_job.tool_configuration and backup_job.tool_configuration.parallel_operations > 1:
                try:
                    # Get current system resources
                    system_resources = self._tool_manager.get_parallel_optimizer().get_system_resources()
                    
                    # Update metrics with resource usage
                    self._tool_manager.update_parallel_execution_metrics(
                        operation_id=backup_job.config.job_id,
                        resource_usage={
                            'cpu_usage_percent': system_resources.cpu_usage_percent,
                            'memory_usage_percent': system_resources.memory_usage_percent,
                            'memory_available_gb': system_resources.memory_available_gb
                        }
                    )
                except Exception as e:
                    logger.debug(f"Could not update parallel execution metrics: {e}")
            
            if result and 'snapshot_id' in result:
                backup_result.snapshot_id = result['snapshot_id']
                backup_result.files_processed = result.get('files_processed', 0)
                backup_result.bytes_processed = result.get('bytes_processed', 0)
                backup_result.status = BackupStatus.COMPLETED
                
                logger.info(
                    f"Job completed: {backup_result.snapshot_id}, "
                    f"{backup_result.files_processed} files"
                )
                
                # Send backup completed notification
                duration = time.time() - backup_result.start_time
                self._backup_notification_service.notify_backup_event(
                    event_type=BackupEventType.BACKUP_COMPLETED,
                    operation_id=backup_job.config.job_id,
                    repository_id=backup_job.config.repository_id,
                    message=f"Backup completed successfully",
                    statistics={
                        'files_processed': backup_result.files_processed,
                        'bytes_processed': backup_result.bytes_processed,
                        'duration': duration,
                        'snapshot_id': backup_result.snapshot_id
                    }
                )
            else:
                backup_result.errors.append("Backup completed but no snapshot ID returned")
                backup_result.status = BackupStatus.FAILED
                
                # Create and report error
                error = self._error_reporter.classify_error(
                    Exception("No snapshot ID returned"),
                    context={
                        'operation_id': backup_job.config.job_id,
                        'repository_id': backup_job.config.repository_id,
                        'tool_name': backup_job.config.tool_type
                    }
                )
                self._backup_notification_service.notify_backup_error(
                    operation_id=backup_job.config.job_id,
                    error=error,
                    repository_id=backup_job.config.repository_id
                )
            
            backup_result.end_time = time.time()
            
        except Exception as e:
            backup_result.errors.append(f"Backup execution failed: {e}")
            backup_result.status = BackupStatus.FAILED
            backup_result.end_time = time.time()
            logger.error(f"Job execution failed: {e}")
            
            # Classify and report error with remediation steps
            error = self._error_reporter.classify_error(
                e,
                context={
                    'operation_id': backup_job.config.job_id,
                    'repository_id': backup_job.config.repository_id,
                    'tool_name': backup_job.config.tool_type,
                    'attempt': backup_job.execution_context.attempt_number
                }
            )
            backup_result.metadata['error_details'] = error.to_dict()
            
            # Send error notification with remediation steps
            self._backup_notification_service.notify_backup_error(
                operation_id=backup_job.config.job_id,
                error=error,
                repository_id=backup_job.config.repository_id
            )
        
        return backup_result

    def _create_backup_targets_from_job(self, backup_job: BackupJob) -> List[BackupTarget]:
        """
        Create backup targets from a backup job.
        
        Args:
            backup_job: Backup job
            
        Returns:
            List of BackupTarget instances
        """
        targets = []
        
        # Create a single target from the job's source paths
        selection = FileSelection()
        
        for path in backup_job.source_paths:
            selection.add_path(path, SelectionType.INCLUDE)
        
        for pattern in backup_job.exclude_patterns:
            selection.add_pattern(pattern, SelectionType.EXCLUDE)
        
        for pattern in backup_job.include_patterns:
            selection.add_pattern(pattern, SelectionType.INCLUDE)
        
        cli_options = backup_job.config.metadata.get('cli_options', {})
        target = BackupTarget(
            selection=selection,
            name=f"job-{backup_job.config.job_id}",
            tags=backup_job.config.tags,
            compression=cli_options.get('compression'),
            one_file_system=bool(cli_options.get('one_file_system', False)),
            exclude_files=cli_options.get('exclude_files', []),
            exclude_caches=bool(cli_options.get('exclude_caches', False)),
            backend_options=cli_options.get('backend_options', []),
        )
        
        targets.append(target)
        
        return targets

    @profile_operation("execute_backup")
    @with_error_handling("execute_backup", "BackupOrchestrator")
    def execute_backup(self,
                       repository_name: str,
                       target_names: List[str],
                       tags: Optional[List[str]] = None,
                       dry_run: bool = False,
                       password: Optional[str] = None) -> BackupResult:
        logger = logging.getLogger(__name__)
        logger.debug(f"execute_backup called with repository_name='{repository_name}', target_names={target_names}")
        """
        Execute a backup operation.

        Args:
            repository_name: Name of repository to backup to
            target_names: Names of backup targets to include
            tags: Optional tags to apply to backup
            dry_run: Whether to perform a dry run without actual backup
            password: Optional password for repository access

        Returns:
            BackupResult with operation details

        Raises:
            BackupOrchestratorError: If backup cannot be executed
        """
        operation_id = str(uuid.uuid4())

        logger.debug(f"execute_backup received password: {'***' if password else 'None'}")

        # Create initial backup result
        backup_result = BackupResult(
                status=BackupStatus.PENDING,
                repository_name=repository_name,
                target_names=target_names.copy(),
                start_time=time.time(),
                metadata={'operation_id': operation_id, 'dry_run': dry_run, 'tags': tags or []}
        )

        # Track the operation
        self._active_backups[operation_id] = backup_result

        try:
            # Validate configuration before execution
            if not self.validate_backup_configuration(repository_name, target_names):
                backup_result.status = BackupStatus.FAILED
                backup_result.errors.append("Backup configuration validation failed")
                return backup_result

            # Start performance tracking
            tracking_id = start_operation_tracking(
                    operation_id,
                    "backup_orchestration",
                    metadata={
                            'repository': repository_name,
                            'targets':    target_names,
                            'dry_run':    dry_run
                    }
            )

            backup_result.status = BackupStatus.RUNNING

            # Execute the backup
            if dry_run:
                backup_result = self._execute_dry_run(backup_result)
            else:
                backup_result = self._execute_actual_backup(backup_result, password=password)

            backup_result.end_time = time.time()

            # Complete tracking
            complete_operation_tracking(tracking_id)

            # Move to history
            self._backup_history.append(backup_result)

            return backup_result

        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.errors.append(str(e))
            backup_result.end_time = time.time()
            logger.error(f"Backup execution failed: {e}")
            raise BackupExecutionError(f"Backup execution failed: {e}") from e

        finally:
            # Remove from active backups
            if operation_id in self._active_backups:
                del self._active_backups[operation_id]

    def _execute_dry_run(self, backup_result: BackupResult) -> BackupResult:
        """Execute a dry run backup"""
        logger.info(f"Executing dry run backup for repository: {backup_result.repository_name}")

        try:
            # Get repository configuration
            repositories = self._configuration_provider.get_repositories()
            repo_config = next(
                    (r for r in repositories if r['name'] == backup_result.repository_name),
                    None
            )

            if not repo_config:
                backup_result.errors.append(f"Repository '{backup_result.repository_name}' not found")
                backup_result.status = BackupStatus.FAILED
                return backup_result

            # Get backup targets
            targets = self._get_backup_targets(backup_result.target_names)

            # Simulate backup process
            total_files = 0
            total_bytes = 0

            for target in targets:
                # Estimate files and size (simplified)
                paths = (
                    target.selection.get_backup_paths()
                    if target.selection is not None
                    else []
                )
                for path in paths:
                    try:
                        from pathlib import Path
                        path_obj = Path(path)
                        if path_obj.exists():
                            if path_obj.is_file():
                                total_files += 1
                                total_bytes += path_obj.stat().st_size
                            elif path_obj.is_dir():
                                for file_path in path_obj.rglob('*'):
                                    if file_path.is_file():
                                        total_files += 1
                                        total_bytes += file_path.stat().st_size
                    except Exception as e:
                        backup_result.warnings.append(f"Could not analyze path {path}: {e}")

            backup_result.files_processed = total_files
            backup_result.bytes_processed = total_bytes
            backup_result.status = BackupStatus.COMPLETED
            backup_result.snapshot_id = f"dry-run-{int(time.time())}"

            logger.info(f"Dry run completed: {total_files} files, {total_bytes} bytes")

        except Exception as e:
            backup_result.errors.append(f"Dry run failed: {e}")
            backup_result.status = BackupStatus.FAILED

        return backup_result

    def _execute_actual_backup(
        self,
        backup_result: BackupResult,
        password: Optional[str] = None,
    ) -> BackupResult:
        """Execute an actual backup"""
        logger.info(f"Executing backup for repository: {backup_result.repository_name}")

        try:
            # Get repository configuration
            repositories = self._configuration_provider.get_repositories()
            repo_config = next(
                    (r for r in repositories if r['name'] == backup_result.repository_name),
                    None
            )

            if not repo_config:
                backup_result.errors.append(f"Repository '{backup_result.repository_name}' not found")
                backup_result.status = BackupStatus.FAILED
                return backup_result

            # Create repository instance
            logger.debug(f"Password retrieved from metadata: {'***' if password else 'None'}")
            logger.debug(f"Repository URI: {repo_config['uri']}")
            repository = self._repository_factory.create_repository(
                repo_config['uri'],
                password=password,
                repository_name=backup_result.repository_name
            )

            # Get backup targets
            targets = self._get_backup_targets(backup_result.target_names)

            # Deterministic target validation must fail before retry handling.
            for target in targets:
                target.validate()

            # Execute backup with retry
            @with_retry(max_retries=3, delay=1.0, backoff_multiplier=2.0)
            def _perform_backup():
                return repository.backup_target(targets, backup_result.metadata.get('tags', []))

            result = _perform_backup()

            if result and 'snapshot_id' in result:
                backup_result.snapshot_id = result['snapshot_id']
                backup_result.files_processed = result.get(
                    'files_processed',
                    result.get('files_new', 0)
                    + result.get('files_changed', 0)
                    + result.get('files_unmodified', 0),
                )
                backup_result.bytes_processed = result.get(
                    'bytes_processed', result.get('data_added', 0)
                )
                backup_result.status = BackupStatus.COMPLETED

                logger.info(f"Backup completed successfully: {backup_result.snapshot_id}")
            else:
                backup_result.errors.append("Backup completed but no snapshot ID returned")
                backup_result.status = BackupStatus.FAILED

        except Exception as e:
            backup_result.errors.append(f"Backup execution failed: {e}")
            backup_result.status = BackupStatus.FAILED
            logger.error(f"Backup execution failed: {e}")

        return backup_result

    def _get_backup_targets(self, target_names: List[str]) -> List[BackupTarget]:
        """Get backup target instances from configuration"""
        targets = []
        target_configs = self._configuration_provider.get_backup_targets()

        logger.debug(f"_get_backup_targets called with target_names: {target_names}")
        logger.debug(f"Available target configs: {[t.get('name', 'NO_NAME') for t in target_configs]}")

        for target_name in target_names:
            target_config = next(
                    (t for t in target_configs if t['name'] == target_name),
                    None
            )

            logger.debug(f"Looking for target '{target_name}', found config: {target_config}")

            if not target_config:
                raise InvalidBackupConfigurationError(f"Backup target '{target_name}' not found")

            # Create FileSelection from target configuration
            selection = FileSelection()

            logger.debug(f"Creating FileSelection for target '{target_name}'")
            logger.debug(f"Target config paths: {target_config.get('paths', [])}")

            # Add paths to selection
            for path in target_config['paths']:
                selection.add_path(path, SelectionType.INCLUDE)
                logger.debug(f"Added path to selection: {path}")

            # Add exclude patterns
            for pattern in target_config.get('exclude_patterns', []):
                selection.add_pattern(pattern, SelectionType.EXCLUDE)

            # Add include patterns
            for pattern in target_config.get('include_patterns', []):
                selection.add_pattern(pattern, SelectionType.INCLUDE)

            logger.debug("FileSelection created, about to create BackupTarget")
            logger.debug(f"selection object: {selection}")

            # Create BackupTarget instance with proper FileSelection
            target = BackupTarget(
                    selection=selection,
                    name=target_config['name'],
                    tags=target_config.get('tags', []),
                    compression=target_config.get('compression'),
                    one_file_system=bool(target_config.get('one_file_system', False)),
                    exclude_files=target_config.get('exclude_files', []),
                    exclude_caches=bool(target_config.get('exclude_caches', False)),
                    backend_options=target_config.get('backend_options', []),
            )

            logger.debug(f"BackupTarget created successfully for '{target_name}'")

            targets.append(target)

        return targets

    def execute_scheduled_backups(self) -> List[BackupResult]:
        """
        Execute all scheduled backup operations.
        
        Returns:
            List of BackupResult objects for each scheduled backup
        """
        # This would integrate with a scheduling system
        # For now, return empty list as placeholder
        logger.info("Scheduled backup execution not yet implemented")
        return []

    def validate_backup_configuration(self,
                                      repository_name: str,
                                      target_names: List[str]) -> bool:
        """
        Validate backup configuration before execution.
        
        Args:
            repository_name: Name of repository to validate
            target_names: Names of backup targets to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            BackupOrchestratorError: If configuration is invalid
        """
        try:
            # Validate repository exists
            repositories = self._configuration_provider.get_repositories()
            repo_exists = any(r['name'] == repository_name for r in repositories)

            if not repo_exists:
                raise InvalidBackupConfigurationError(f"Repository '{repository_name}' not found")

            # Validate all targets exist
            target_configs = self._configuration_provider.get_backup_targets()
            for target_name in target_names:
                target_exists = any(t['name'] == target_name for t in target_configs)
                if not target_exists:
                    raise InvalidBackupConfigurationError(f"Backup target '{target_name}' not found")

            return True

        except Exception as e:
            logger.error(f"Backup configuration validation failed: {e}")
            raise

    def get_backup_status(self, operation_id: str) -> Optional[BackupResult]:
        """
        Get status of a backup operation.
        
        Args:
            operation_id: Unique identifier for backup operation
            
        Returns:
            BackupResult if operation found, None otherwise
        """
        return self._active_backups.get(operation_id)

    def cancel_backup(self, operation_id: str) -> bool:
        """
        Cancel a running backup operation.
        
        Args:
            operation_id: Unique identifier for backup operation
            
        Returns:
            True if backup was cancelled, False if not found or not running
        """
        if operation_id in self._futures:
            future = self._futures[operation_id]
            if not future.done():
                future.cancel()

                # Update backup result
                if operation_id in self._active_backups:
                    backup_result = self._active_backups[operation_id]
                    backup_result.status = BackupStatus.CANCELLED
                    backup_result.end_time = time.time()

                logger.info(f"Cancelled backup operation: {operation_id}")
                return True

        return False

    def list_active_backups(self) -> List[BackupResult]:
        """
        List all currently active backup operations.
        
        Returns:
            List of BackupResult objects for active operations
        """
        return list(self._active_backups.values())

    def get_backup_history(self,
                           repository_name: Optional[str] = None,
                           limit: int = 100) -> List[BackupResult]:
        """
        Get backup operation history.
        
        Args:
            repository_name: Optional repository name to filter by
            limit: Maximum number of results to return
            
        Returns:
            List of BackupResult objects from history
        """
        history = self._backup_history

        if repository_name:
            history = [r for r in history if r.repository_name == repository_name]

        # Sort by start time (most recent first) and limit
        history = sorted(history, key=lambda x: x.start_time or 0, reverse=True)
        return history[:limit]

    def estimate_backup_size(self,
                             repository_name: str,
                             target_names: List[str]) -> Dict[str, Any]:
        """
        Estimate backup size and duration.
        
        Args:
            repository_name: Name of repository
            target_names: Names of backup targets
            
        Returns:
            Dictionary with size and time estimates
        """
        # This would analyze the targets and provide estimates
        # For now, return placeholder data
        return {
                'estimated_files':            0,
                'estimated_bytes':            0,
                'estimated_duration_seconds': 0
        }

    def verify_backup_integrity(self,
                                repository_name: str,
                                snapshot_id: Optional[str] = None) -> bool:
        """
        Verify backup integrity.

        Args:
            repository_name: Name of repository to verify or URI
            snapshot_id: Optional specific snapshot to verify

        Returns:
            True if verification successful

        Raises:
            BackupOrchestratorError: If verification fails
        """
        try:
            # Check if repository_name is a URI or a configured repository name
            repository_uri = repository_name

            # If it looks like a repository name (not a URI), try to find it in configuration
            if not repository_name.startswith(('file://', 'sftp://', 's3:', 'b2:', 'azure:', 'gs:', 'swift:')):
                repositories = self._configuration_provider.get_repositories()
                repo_config = next(
                        (r for r in repositories if r['name'] == repository_name),
                        None
                )

                if not repo_config:
                    raise BackupOrchestratorError(f"Repository '{repository_name}' not found")

                repository_uri = repo_config['uri']

            # Create repository instance directly from URI
            repository = self._repository_factory.create_repository(repository_uri, repository_name=repository_name)

            # Verify backup
            if hasattr(repository, 'verify_backup'):
                return repository.verify_backup(snapshot_id)
            else:
                logger.warning(f"Repository {repository.__class__.__name__} does not support verification")
                return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            raise BackupOrchestratorError(f"Backup verification failed: {e}") from e

    def execute_policy_driven_backup(self, policy_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a backup operation driven by a backup policy.
        
        This method integrates with the policy management system to execute
        backups according to backup policy configuration.
        
        Args:
            policy_id: Backup policy ID to execute
            dry_run: If True, simulate without actually performing backup
            
        Returns:
            Dictionary with backup results
            
        Raises:
            BackupOrchestratorError: If policy-driven backup execution fails
        """
        try:
            if not self._policy_integration_service:
                raise BackupOrchestratorError(
                    "Policy-driven backups not available: policy integration service not configured"
                )
            
            logger.info(
                f"{'[DRY RUN] ' if dry_run else ''}Executing policy-driven backup "
                f"for policy ID: {policy_id}"
            )
            
            # Delegate to policy integration service
            result = self._policy_integration_service.execute_policy_driven_backup(
                policy_id=policy_id,
                dry_run=dry_run,
            )
            
            logger.info(
                f"Policy-driven backup {'completed' if result.get('success') else 'failed'} "
                f"for policy ID: {policy_id}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Policy-driven backup execution failed: {e}")
            raise BackupOrchestratorError(f"Policy-driven backup execution failed: {e}") from e
