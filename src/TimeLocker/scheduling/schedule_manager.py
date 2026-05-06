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

Schedule Manager

This module provides the central orchestrator for scheduling operations,
coordinating between platform adapters and TimeLocker components.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .platform_detector import PlatformDetector
from .platform_adapter import PlatformAdapter
from .scheduling_configuration import SchedulingConfiguration
from .scheduling_models import (
    ScheduleRequest,
    ScheduleConfig,
    ExecutionResult,
    ScheduleInfo,
    ScheduleStatus,
    ScheduleUpdates,
    ScheduleFilters,
    ValidationResult,
    ScheduleHealthStatus
)
from .scheduling_exceptions import (
    SchedulingError,
    PolicyValidationError,
    DataSelectionValidationError,
    RepositoryValidationError,
    PlatformSchedulerError
)
from .integration_clients import (
    PolicyManagementClient,
    DataSelectionClient,
    RepositoryManagementClient,
    MonitoringClient
)
from .audit_logger import SchedulingAuditLogger
from .schedule_storage import ScheduleStorage
from .schedule_validator import ScheduleValidator
from .schedule_testing import ScheduleTester, TestExecutionResult, HealthCheckResult, DiagnosticResult
from .schedule_utilities import (
    ScheduleConflictDetector,
    AutomaticRescheduler,
    ScheduleOptimizer,
    ScheduleConflict,
    ConflictResolution,
    ScheduleOptimization
)

logger: logging.Logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ScheduleManager:
    """
    Central orchestrator for scheduling operations.
    
    This class coordinates between platform-specific adapters and
    TimeLocker components to provide unified scheduling functionality.
    """
    
    def __init__(
        self,
        config: SchedulingConfiguration | None = None,
        adapter: PlatformAdapter | None = None,
        config_dir: Path | None = None
    ):
        """
        Initialize schedule manager.
        
        Args:
            config: Optional scheduling configuration (loads default if not provided)
            adapter: Optional platform adapter (auto-detects if not provided)
            config_dir: Optional configuration directory
        """
        self.logger: logging.Logger = logging.getLogger(f"{__name__}.ScheduleManager")
        
        # Determine configuration directory
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "scheduling"
        
        self.config_dir: Path = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or use provided configuration
        if config is None:
            config_path = self.config_dir / "scheduling_config.json"
            if config_path.exists():
                self.config: SchedulingConfiguration = SchedulingConfiguration.load_from_file(config_path)
            else:
                self.config = SchedulingConfiguration()
                self.logger.info("Using default scheduling configuration")
        else:
            self.config = config
        
        # Detect or use provided platform adapter
        if adapter is None:
            adapter_class = PlatformDetector.detect_best_scheduler()
            self.adapter: PlatformAdapter = adapter_class()
            self.logger.info(f"Auto-detected platform adapter: {self.adapter.get_platform_name()}")
        else:
            self.adapter = adapter
            self.logger.info(f"Using provided platform adapter: {self.adapter.get_platform_name()}")
        
        # Initialize integration clients
        self.policy_client: PolicyManagementClient = PolicyManagementClient()
        self.data_selection_client: DataSelectionClient = DataSelectionClient()
        self.repository_client: RepositoryManagementClient = RepositoryManagementClient()
        self.monitoring_client: MonitoringClient = MonitoringClient()
        
        # Register for policy update notifications
        self.policy_client.register_policy_update_callback(self._handle_policy_update)
        
        # Initialize audit logger
        self.audit_logger: SchedulingAuditLogger = SchedulingAuditLogger(
            self.config_dir,
            retention_days=self.config.audit_retention_days
        )
        
        # Initialize compliance reporter
        from .compliance_reporter import ComplianceReporter
        self.compliance_reporter = ComplianceReporter(
            audit_logger=self.audit_logger,
            policy_client=self.policy_client
        )
        
        # Initialize schedule storage
        self.storage: ScheduleStorage = ScheduleStorage(self.config_dir / "schedules")
        
        # Initialize validator and tester
        self.validator: ScheduleValidator = ScheduleValidator(
            platform_adapter=self.adapter,
            policy_client=self.policy_client,
            data_selection_client=self.data_selection_client,
            repository_client=self.repository_client
        )
        
        self.tester: ScheduleTester = ScheduleTester(
            platform_adapter=self.adapter,
            validator=self.validator,
            policy_client=self.policy_client,
            data_selection_client=self.data_selection_client,
            repository_client=self.repository_client
        )
        
        # Initialize schedule utilities
        self.conflict_detector: ScheduleConflictDetector = ScheduleConflictDetector(
            max_concurrent_executions=self.config.max_concurrent_executions
        )
        self.auto_rescheduler: AutomaticRescheduler = AutomaticRescheduler(self.conflict_detector)
        self.optimizer: ScheduleOptimizer = ScheduleOptimizer()
        
        # In-memory cache of schedules
        self._schedules: dict[str, ScheduleConfig] = {}
        self._load_schedules_from_storage()
        
        self.logger.info("ScheduleManager initialized successfully")
    
    async def create_scheduled_backup(self, request: ScheduleRequest) -> ScheduleInfo:
        """
        Create a new scheduled backup.
        
        Args:
            request: Schedule creation request
            
        Returns:
            ScheduleInfo: Information about the created schedule
            
        Raises:
            SchedulingError: If schedule creation fails
            PolicyValidationError: If policy validation fails
            DataSelectionValidationError: If data selection validation fails
            RepositoryValidationError: If repository validation fails
        """
        try:
            # Generate unique schedule ID
            schedule_id = str(uuid.uuid4())
            
            # Create schedule configuration
            schedule_config = ScheduleConfig(
                schedule_id=schedule_id,
                name=request.name,
                description=request.description,
                policy_id=request.policy_id,
                schedule_pattern=request.schedule_pattern,
                enabled=request.enabled,
                execution_timeout=request.execution_timeout,
                retry_config=request.retry_config,
                monitoring_config=request.monitoring_config,
                platform_specific_config=request.platform_specific_config,
                created_at=_utc_now(),
                updated_at=_utc_now(),
                created_by=str(request.platform_specific_config.get("created_by", ""))
            )
            
            # Validate schedule configuration
            validation_result = await self.validate_schedule_configuration(schedule_config)
            if not validation_result.is_valid:
                error_msg = f"Schedule validation failed: {', '.join(validation_result.errors)}"
                self.logger.error(error_msg)
                self.audit_logger.log_validation_failure(schedule_id, validation_result.errors)
                raise SchedulingError(error_msg, details={'errors': validation_result.errors})
            
            # Create platform schedule
            try:
                platform_result = await self.adapter.create_schedule(schedule_config)
                
                if not platform_result.success:
                    raise PlatformSchedulerError(
                        f"Platform scheduler failed: {platform_result.error_message}",
                        details={'platform': self.adapter.get_platform_name()}
                    )
                
            except Exception as e:
                self.audit_logger.log_platform_error(schedule_id, self.adapter.get_platform_name(), e)
                raise PlatformSchedulerError(
                    f"Failed to create platform schedule: {e}",
                    details={'platform': self.adapter.get_platform_name()}
                ) from e
            
            # Store schedule configuration
            self._schedules[schedule_id] = schedule_config
            self.storage.save_schedule(schedule_config)
            
            # Log audit event
            self.audit_logger.log_schedule_creation(
                schedule_id,
                {
                    'name': schedule_config.name,
                    'policy_id': schedule_config.policy_id,
                    'schedule_pattern': str(schedule_config.schedule_pattern.pattern_type.value),
                    'enabled': schedule_config.enabled
                },
                created_by=schedule_config.created_by
            )
            
            # Report to monitoring
            self.monitoring_client.report_schedule_created(
                schedule_id,
                {
                    'name': schedule_config.name,
                    'policy_id': schedule_config.policy_id,
                    'enabled': schedule_config.enabled
                }
            )
            
            self.logger.info(f"Created scheduled backup: {schedule_id} ({schedule_config.name})")
            
            # Return schedule info
            return ScheduleInfo(
                schedule_id=schedule_id,
                name=schedule_config.name,
                description=schedule_config.description,
                policy_id=schedule_config.policy_id,
                enabled=schedule_config.enabled,
                next_execution_time=platform_result.next_run,
                health_status=ScheduleHealthStatus.HEALTHY,
                created_at=schedule_config.created_at,
                updated_at=schedule_config.updated_at
            )
            
        except (PolicyValidationError, DataSelectionValidationError, RepositoryValidationError, PlatformSchedulerError):
            raise
        except Exception as e:
            error_msg = f"Failed to create scheduled backup: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def update_scheduled_backup(
        self,
        schedule_id: str,
        updates: ScheduleUpdates
    ) -> ScheduleInfo:
        """
        Update an existing scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            updates: Updates to apply
            
        Returns:
            ScheduleInfo: Updated schedule information
            
        Raises:
            SchedulingError: If update fails
        """
        try:
            # Get existing schedule
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            # Apply updates
            if updates.name is not None:
                schedule_config.name = updates.name
            if updates.description is not None:
                schedule_config.description = updates.description
            if updates.schedule_pattern is not None:
                schedule_config.schedule_pattern = updates.schedule_pattern
            if updates.enabled is not None:
                schedule_config.enabled = updates.enabled
            if updates.execution_timeout is not None:
                schedule_config.execution_timeout = updates.execution_timeout
            if updates.retry_config is not None:
                schedule_config.retry_config = updates.retry_config
            if updates.monitoring_config is not None:
                schedule_config.monitoring_config = updates.monitoring_config
            if updates.platform_specific_config is not None:
                schedule_config.platform_specific_config.update(updates.platform_specific_config)
            
            schedule_config.updated_at = _utc_now()
            
            # Validate updated configuration
            validation_result = await self.validate_schedule_configuration(schedule_config)
            if not validation_result.is_valid:
                error_msg = f"Updated schedule validation failed: {', '.join(validation_result.errors)}"
                self.logger.error(error_msg)
                raise SchedulingError(error_msg, details={'errors': validation_result.errors})
            
            # Update platform schedule
            try:
                platform_result = await self.adapter.update_schedule(schedule_id, schedule_config)
                
                if not platform_result.success:
                    raise PlatformSchedulerError(
                        f"Platform scheduler update failed: {platform_result.error_message}"
                    )
                
            except Exception as e:
                self.audit_logger.log_platform_error(schedule_id, self.adapter.get_platform_name(), e)
                raise PlatformSchedulerError(f"Failed to update platform schedule: {e}") from e
            
            # Store updated configuration
            self._schedules[schedule_id] = schedule_config
            self.storage.save_schedule(schedule_config)
            
            # Log audit event
            update_details = {}
            if updates.name:
                update_details['name'] = updates.name
            if updates.enabled is not None:
                update_details['enabled'] = updates.enabled
            if updates.schedule_pattern:
                update_details['schedule_pattern'] = 'updated'
            
            self.audit_logger.log_schedule_update(schedule_id, update_details)
            
            # Report to monitoring
            self.monitoring_client.report_schedule_updated(schedule_id, update_details)
            
            self.logger.info(f"Updated scheduled backup: {schedule_id}")
            
            # Return updated schedule info
            return ScheduleInfo(
                schedule_id=schedule_id,
                name=schedule_config.name,
                description=schedule_config.description,
                policy_id=schedule_config.policy_id,
                enabled=schedule_config.enabled,
                next_execution_time=platform_result.next_run,
                health_status=ScheduleHealthStatus.HEALTHY,
                created_at=schedule_config.created_at,
                updated_at=schedule_config.updated_at
            )
            
        except (PlatformSchedulerError, SchedulingError):
            raise
        except Exception as e:
            error_msg = f"Failed to update scheduled backup: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def delete_scheduled_backup(self, schedule_id: str) -> bool:
        """
        Delete a scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            SchedulingError: If deletion fails
        """
        try:
            # Check if schedule exists
            if schedule_id not in self._schedules:
                self.logger.warning(f"Schedule not found for deletion: {schedule_id}")
                return False
            
            # Delete from platform scheduler
            try:
                success = await self.adapter.delete_schedule(schedule_id)
                
                if not success:
                    self.logger.warning(f"Platform scheduler deletion returned false for: {schedule_id}")
                
            except Exception as e:
                self.audit_logger.log_platform_error(schedule_id, self.adapter.get_platform_name(), e)
                # Continue with deletion even if platform deletion fails
                self.logger.warning(f"Platform schedule deletion failed, continuing: {e}")
            
            # Remove from memory and storage
            del self._schedules[schedule_id]
            self.storage.delete_schedule(schedule_id)
            
            # Log audit event
            self.audit_logger.log_schedule_deletion(schedule_id)
            
            # Report to monitoring
            self.monitoring_client.report_schedule_deleted(schedule_id)
            
            self.logger.info(f"Deleted scheduled backup: {schedule_id}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete scheduled backup: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def get_schedule_status(self, schedule_id: str) -> ScheduleStatus:
        """
        Get current status of a scheduled backup.
        
        Args:
            schedule_id: Unique identifier for the schedule
            
        Returns:
            ScheduleStatus: Current schedule status
            
        Raises:
            SchedulingError: If status retrieval fails
        """
        try:
            # Check if schedule exists
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            # Get platform status
            try:
                platform_status = await self.adapter.get_schedule_status(schedule_id)
            except Exception as e:
                self.logger.warning(f"Failed to get platform status for {schedule_id}: {e}")
                # Create unknown platform status
                from .scheduling_models import PlatformScheduleStatus
                platform_status = PlatformScheduleStatus(
                    platform_id=schedule_id,
                    is_active=False,
                    last_run_time=None,
                    next_run_time=None
                )
            
            # Determine health status
            health_status = ScheduleHealthStatus.HEALTHY
            if not schedule_config.enabled:
                health_status = ScheduleHealthStatus.UNKNOWN
            elif not platform_status.is_active:
                health_status = ScheduleHealthStatus.ERROR
            
            execution_history = self._get_execution_history(schedule_id)
            last_execution = execution_history[0] if execution_history else None
            
            return ScheduleStatus(
                schedule_id=schedule_id,
                enabled=schedule_config.enabled,
                last_execution=last_execution,
                next_execution_time=platform_status.next_run_time,
                platform_status=platform_status,
                health_status=health_status,
                execution_history=execution_history
            )
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to get schedule status: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def list_scheduled_backups(
        self,
        filters: ScheduleFilters | None = None
    ) -> list[ScheduleInfo]:
        """
        List all scheduled backups with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[ScheduleInfo]: List of scheduled backups
            
        Raises:
            SchedulingError: If listing fails
        """
        try:
            schedules = list(self._schedules.values())
            
            # Apply filters if provided
            if filters:
                if filters.enabled_only:
                    schedules = [s for s in schedules if s.enabled]
                
                if filters.policy_id:
                    schedules = [s for s in schedules if s.policy_id == filters.policy_id]
                
                if filters.name_pattern:
                    import re
                    pattern = re.compile(filters.name_pattern, re.IGNORECASE)
                    schedules = [s for s in schedules if pattern.search(s.name)]
                
            # Convert to ScheduleInfo
            schedule_infos: list[ScheduleInfo] = []
            for schedule in schedules:
                try:
                    # Get next execution time from platform
                    platform_status = await self.adapter.get_schedule_status(schedule.schedule_id)
                    next_execution_time = platform_status.next_run_time
                except Exception as e:
                    self.logger.warning(f"Failed to get platform status for {schedule.schedule_id}: {e}")
                    next_execution_time = None
                
                # Determine health status
                health_status = ScheduleHealthStatus.HEALTHY
                if not schedule.enabled:
                    health_status = ScheduleHealthStatus.UNKNOWN

                if filters and filters.health_status and health_status != filters.health_status:
                    continue
                
                schedule_info = ScheduleInfo(
                    schedule_id=schedule.schedule_id,
                    name=schedule.name,
                    description=schedule.description,
                    policy_id=schedule.policy_id,
                    enabled=schedule.enabled,
                    next_execution_time=next_execution_time,
                    health_status=health_status,
                    created_at=schedule.created_at,
                    updated_at=schedule.updated_at
                )
                
                schedule_infos.append(schedule_info)
            
            return schedule_infos
            
        except Exception as e:
            error_msg = f"Failed to list scheduled backups: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e

    def _get_execution_history(self, schedule_id: str, limit: int = 100) -> list[ExecutionResult]:
        """Return recorded execution history when an execution engine is attached."""
        execution_engine = getattr(self, "automation_engine", None)
        get_history = getattr(execution_engine, "get_execution_history", None)
        if not callable(get_history):
            return []

        try:
            history = get_history(schedule_id, limit=limit)
        except Exception as exc:
            self.logger.debug("Failed to read execution history for %s: %s", schedule_id, exc)
            return []

        if not isinstance(history, list):
            return []
        return [entry for entry in history if isinstance(entry, ExecutionResult)]
    
    async def validate_schedule_configuration(self, config: ScheduleConfig) -> ValidationResult:
        """
        Validate schedule configuration against all integration points.
        
        Args:
            config: Schedule configuration to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Validate policy
            is_valid, errors = self.policy_client.validate_policy_for_scheduling(config.policy_id)
            if not is_valid:
                for error in errors:
                    result.add_error(f"Policy validation: {error}")
            
            # Get policy to check data selection references
            policy = self.policy_client.get_backup_policy(config.policy_id)
            if policy:
                # Validate data selection references
                for selection_ref in policy.data_selection_refs:
                    is_valid, errors = self.data_selection_client.validate_selection_for_scheduling(selection_ref)
                    if not is_valid:
                        for error in errors:
                            result.add_error(f"Data selection validation ({selection_ref}): {error}")
                
                # Validate target repositories
                for repo_id in policy.target_repositories:
                    is_valid, errors = self.repository_client.validate_repository_for_scheduling(repo_id)
                    if not is_valid:
                        for error in errors:
                            result.add_error(f"Repository validation ({repo_id}): {error}")
            
            # Validate platform compatibility
            platform_validation = self.adapter.validate_schedule_config(config)
            if not platform_validation.is_valid:
                for error in platform_validation.errors:
                    result.add_error(f"Platform validation: {error}")
                for warning in platform_validation.warnings:
                    result.add_warning(f"Platform warning: {warning}")
            
        except Exception as e:
            result.add_error(f"Validation error: {str(e)}")
        
        return result
    
    def _load_schedules_from_storage(self) -> None:
        """Load schedules from persistent storage into memory."""
        try:
            schedules = self.storage.list_schedules()
            for schedule in schedules:
                self._schedules[schedule.schedule_id] = schedule
            
            self.logger.info(f"Loaded {len(schedules)} schedules from storage")
            
        except Exception as e:
            self.logger.error(f"Failed to load schedules from storage: {e}")
    
    def get_platform_name(self) -> str:
        """
        Get the name of the current platform adapter.
        
        Returns:
            str: Platform adapter name
        """
        return self.adapter.get_platform_name()

    async def get_schedule_health_summary(self) -> dict[str, object]:
        """
        Get health summary for all schedules.
        
        Returns:
            Dictionary with health summary information
        """
        try:
            schedules = list(self._schedules.values())
            
            total_schedules = len(schedules)
            enabled_schedules = sum(1 for s in schedules if s.enabled)
            disabled_schedules = total_schedules - enabled_schedules
            
            # Get health status for each schedule
            healthy_count = 0
            warning_count = 0
            error_count = 0
            
            for schedule in schedules:
                if not schedule.enabled:
                    continue
                
                try:
                    status = await self.get_schedule_status(schedule.schedule_id)
                    if status.health_status == ScheduleHealthStatus.HEALTHY:
                        healthy_count += 1
                    elif status.health_status == ScheduleHealthStatus.WARNING:
                        warning_count += 1
                    elif status.health_status == ScheduleHealthStatus.ERROR:
                        error_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to get status for schedule {schedule.schedule_id}: {e}")
                    error_count += 1
            
            return {
                'total_schedules': total_schedules,
                'enabled_schedules': enabled_schedules,
                'disabled_schedules': disabled_schedules,
                'healthy_schedules': healthy_count,
                'warning_schedules': warning_count,
                'error_schedules': error_count,
                'platform': self.adapter.get_platform_name(),
                'timestamp': _utc_now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get schedule health summary: {e}")
            return {
                'error': str(e),
                'timestamp': _utc_now().isoformat()
            }
    
    async def get_next_scheduled_runs(self, limit: int = 10) -> list[dict[str, object]]:
        """
        Get the next scheduled backup runs across all schedules.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of upcoming scheduled runs with schedule information
        """
        try:
            upcoming_runs: list[dict[str, object]] = []
            
            for schedule in self._schedules.values():
                if not schedule.enabled:
                    continue
                
                try:
                    platform_status = await self.adapter.get_schedule_status(schedule.schedule_id)
                    
                    if platform_status.next_run_time:
                        upcoming_runs.append({
                            'schedule_id': schedule.schedule_id,
                            'schedule_name': schedule.name,
                            'policy_id': schedule.policy_id,
                            'next_run_time': platform_status.next_run_time,
                            'platform_id': platform_status.platform_id
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get next run for schedule {schedule.schedule_id}: {e}")
                    continue
            
            # Sort by next run time
            upcoming_runs.sort(
                key=lambda run: run["next_run_time"]
                if isinstance(run["next_run_time"], datetime)
                else datetime.max.replace(tzinfo=timezone.utc)
            )
            
            return upcoming_runs[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get next scheduled runs: {e}")
            return []
    
    async def enable_schedule(self, schedule_id: str) -> bool:
        """
        Enable a disabled schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            True if enabled successfully
            
        Raises:
            SchedulingError: If enable operation fails
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            if schedule_config.enabled:
                self.logger.info(f"Schedule {schedule_id} is already enabled")
                return True
            
            # Update configuration
            schedule_config.enabled = True
            schedule_config.updated_at = _utc_now()
            
            # Update platform schedule
            try:
                platform_result = await self.adapter.update_schedule(schedule_id, schedule_config)
                
                if not platform_result.success:
                    raise PlatformSchedulerError(
                        f"Platform scheduler enable failed: {platform_result.error_message}"
                    )
                
            except Exception as e:
                self.audit_logger.log_platform_error(schedule_id, self.adapter.get_platform_name(), e)
                raise PlatformSchedulerError(f"Failed to enable platform schedule: {e}") from e
            
            # Store updated configuration
            self.storage.save_schedule(schedule_config)
            
            # Log audit event
            self.audit_logger.log_schedule_status_change(schedule_id, enabled=True)
            
            # Report to monitoring
            self.monitoring_client.report_schedule_updated(
                schedule_id,
                {'enabled': True}
            )
            
            self.logger.info(f"Enabled schedule: {schedule_id}")
            return True
            
        except (PlatformSchedulerError, SchedulingError):
            raise
        except Exception as e:
            error_msg = f"Failed to enable schedule: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def disable_schedule(self, schedule_id: str) -> bool:
        """
        Disable an enabled schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            True if disabled successfully
            
        Raises:
            SchedulingError: If disable operation fails
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            if not schedule_config.enabled:
                self.logger.info(f"Schedule {schedule_id} is already disabled")
                return True
            
            # Update configuration
            schedule_config.enabled = False
            schedule_config.updated_at = _utc_now()
            
            # Update platform schedule
            try:
                platform_result = await self.adapter.update_schedule(schedule_id, schedule_config)
                
                if not platform_result.success:
                    raise PlatformSchedulerError(
                        f"Platform scheduler disable failed: {platform_result.error_message}"
                    )
                
            except Exception as e:
                self.audit_logger.log_platform_error(schedule_id, self.adapter.get_platform_name(), e)
                raise PlatformSchedulerError(f"Failed to disable platform schedule: {e}") from e
            
            # Store updated configuration
            self.storage.save_schedule(schedule_config)
            
            # Log audit event
            self.audit_logger.log_schedule_status_change(schedule_id, enabled=False)
            
            # Report to monitoring
            self.monitoring_client.report_schedule_updated(
                schedule_id,
                {'enabled': False}
            )
            
            self.logger.info(f"Disabled schedule: {schedule_id}")
            return True
            
        except (PlatformSchedulerError, SchedulingError):
            raise
        except Exception as e:
            error_msg = f"Failed to disable schedule: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def get_audit_trail(
        self,
        schedule_id: str | None = None,
        days: int = 7
    ) -> list[dict[str, object]]:
        """
        Get audit trail for scheduling operations.
        
        Args:
            schedule_id: Optional filter by schedule ID
            days: Number of days to look back
            
        Returns:
            List of audit entries
        """
        try:
            start_date = _utc_now() - timedelta(days=days)
            
            entries = self.audit_logger.get_audit_trail(
                schedule_id=schedule_id,
                start_date=start_date,
                limit=100
            )
            
            return [entry.to_dict() for entry in entries]
            
        except Exception as e:
            self.logger.error(f"Failed to get audit trail: {e}")
            return []
    
    async def test_schedule_execution(
        self,
        schedule_id: str,
        dry_run: bool = True
    ) -> TestExecutionResult:
        """
        Test schedule execution with optional dry-run mode.
        
        Args:
            schedule_id: Schedule identifier
            dry_run: If True, simulate execution without actual backup
            
        Returns:
            TestExecutionResult with test results
            
        Raises:
            SchedulingError: If schedule not found
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            # Run test execution
            result = await self.tester.test_schedule_execution(schedule_config, dry_run)
            
            # Log test execution
            self.audit_logger.log_test_execution(
                schedule_id,
                {
                    'dry_run': dry_run,
                    'success': result.success,
                    'errors': result.errors,
                    'warnings': result.warnings
                }
            )
            
            self.logger.info(f"Test execution completed for schedule {schedule_id}: {'success' if result.success else 'failed'}")
            
            return result
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to test schedule execution: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def check_platform_health(self) -> HealthCheckResult:
        """
        Check health of platform scheduler.
        
        Returns:
            HealthCheckResult with platform scheduler health status
        """
        try:
            result = await self.tester.check_platform_scheduler_health()
            
            self.logger.info(f"Platform health check: {'healthy' if result.is_healthy else 'unhealthy'}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Platform health check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                check_type="platform_scheduler",
                timestamp=_utc_now(),
                details={'error': str(e)},
                issues=[f"Health check error: {str(e)}"],
                recommendations=["Check platform scheduler installation and permissions"]
            )
    
    async def check_system_resources(self) -> HealthCheckResult:
        """
        Check system resources for scheduled backup execution.
        
        Returns:
            HealthCheckResult with system resource status
        """
        try:
            result = await self.tester.check_system_resources()
            
            self.logger.info(f"System resources check: {'healthy' if result.is_healthy else 'issues found'}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"System resources check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                check_type="system_resources",
                timestamp=_utc_now(),
                details={'error': str(e)},
                issues=[f"Health check error: {str(e)}"],
                recommendations=["Check system configuration and permissions"]
            )
    
    async def run_schedule_diagnostic(self, schedule_id: str) -> DiagnosticResult:
        """
        Run comprehensive diagnostic for a schedule.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            DiagnosticResult with diagnostic information
            
        Raises:
            SchedulingError: If schedule not found
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            
            # Run diagnostic
            result = await self.tester.run_diagnostic(schedule_config)
            
            # Log diagnostic execution
            self.audit_logger.log_diagnostic_run(
                schedule_id,
                {
                    'issues_found': len(result.issues_found),
                    'recommendations': len(result.recommendations)
                }
            )
            
            self.logger.info(f"Diagnostic completed for schedule {schedule_id}: {len(result.issues_found)} issues found")
            
            return result
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to run diagnostic: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def check_schedule_conflicts(self, schedule_id: str) -> HealthCheckResult:
        """
        Check for scheduling conflicts with existing schedules.
        
        Args:
            schedule_id: Schedule identifier
            
        Returns:
            HealthCheckResult with conflict information
            
        Raises:
            SchedulingError: If schedule not found
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule_config = self._schedules[schedule_id]
            existing_schedules = list(self._schedules.values())
            
            # Check for conflicts
            result = await self.tester.check_schedule_conflicts(schedule_config, existing_schedules)
            
            self.logger.info(f"Conflict check for schedule {schedule_id}: {len(result.issues)} conflicts found")
            
            return result
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to check schedule conflicts: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e

    def generate_compliance_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        schedule_ids: list[str] | None = None
    ):
        """
        Generate comprehensive compliance report for scheduled backups.
        
        Args:
            start_date: Start of reporting period (default: 30 days ago)
            end_date: End of reporting period (default: now)
            schedule_ids: Optional list of specific schedule IDs to report on
            
        Returns:
            ComplianceReport instance
        """
        try:
            report = self.compliance_reporter.generate_compliance_report(
                start_date=start_date,
                end_date=end_date,
                schedule_ids=schedule_ids
            )
            
            self.logger.info(
                f"Generated compliance report: {report.compliant_schedules} compliant, "
                f"{report.violation_schedules} violations"
            )
            
            return report
            
        except Exception as e:
            error_msg = f"Failed to generate compliance report: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def export_compliance_report(
        self,
        report,
        output_file: Path,
        format: str = 'json'
    ) -> bool:
        """
        Export compliance report to file.
        
        Args:
            report: ComplianceReport instance
            output_file: Path to output file
            format: Output format ('json' or 'html')
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            success = self.compliance_reporter.export_compliance_report(
                report,
                output_file,
                format
            )
            
            if success:
                self.logger.info(f"Exported compliance report to {output_file}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to export compliance report: {e}")
            return False
    
    def get_policy_compliance_summary(self, policy_id: str) -> dict[str, object]:
        """
        Get compliance summary for all schedules using a specific policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            Dictionary with policy compliance summary
        """
        try:
            summary = self.compliance_reporter.get_policy_compliance_summary(policy_id)
            
            self.logger.info(
                f"Policy compliance summary for {policy_id}: "
                f"{summary.get('compliant_count', 0)}/{summary.get('schedule_count', 0)} compliant"
            )
            
            return summary
            
        except Exception as e:
            error_msg = f"Failed to get policy compliance summary: {e}"
            self.logger.error(error_msg)
            return {
                'policy_id': policy_id,
                'error': str(e)
            }
    
    def get_audit_statistics(self) -> dict[str, object]:
        """
        Get statistics about audit logs.
        
        Returns:
            Dictionary containing audit log statistics
        """
        try:
            stats = self.audit_logger.get_audit_statistics()
            
            self.logger.debug(f"Audit statistics: {stats.get('total_entries', 0)} entries")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {e}")
            return {'error': str(e)}
    
    def export_audit_trail(
        self,
        output_file: Path,
        schedule_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> bool:
        """
        Export audit trail to a file for compliance reporting.
        
        Args:
            output_file: Path to output file
            schedule_id: Optional filter by schedule ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            success = self.audit_logger.export_audit_trail(
                output_file,
                schedule_id,
                start_date,
                end_date
            )
            
            if success:
                self.logger.info(f"Exported audit trail to {output_file}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to export audit trail: {e}")
            return False

    
    async def detect_schedule_conflicts(
        self,
        time_window_hours: int = 24
    ) -> list[ScheduleConflict]:
        """
        Detect conflicts between all scheduled backups.
        
        Args:
            time_window_hours: Time window to analyze for conflicts
            
        Returns:
            List of detected conflicts
        """
        try:
            schedules = list(self._schedules.values())
            conflicts = self.conflict_detector.detect_conflicts(schedules, time_window_hours)
            
            self.logger.info(f"Detected {len(conflicts)} schedule conflicts in {time_window_hours}h window")
            
            # Log conflicts for audit
            if conflicts:
                self.audit_logger.log_conflict_detection(
                    {
                        'conflict_count': len(conflicts),
                        'time_window_hours': time_window_hours,
                        'critical_count': sum(1 for c in conflicts if c.severity.value == 'critical'),
                        'high_count': sum(1 for c in conflicts if c.severity.value == 'high')
                    }
                )
            
            return conflicts
            
        except Exception as e:
            error_msg = f"Failed to detect schedule conflicts: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def resolve_schedule_conflicts(
        self,
        conflicts: list[ScheduleConflict] | None = None,
        auto_apply: bool = False
    ) -> list[ConflictResolution]:
        """
        Generate resolutions for schedule conflicts.
        
        Args:
            conflicts: Optional list of conflicts (detects if not provided)
            auto_apply: If True, automatically apply resolutions
            
        Returns:
            List of conflict resolutions
            
        Raises:
            SchedulingError: If resolution fails
        """
        try:
            # Detect conflicts if not provided
            if conflicts is None:
                conflicts = await self.detect_schedule_conflicts()
            
            if not conflicts:
                self.logger.info("No conflicts to resolve")
                return []
            
            # Generate resolutions
            schedules = list(self._schedules.values())
            resolutions = self.auto_rescheduler.resolve_conflicts(schedules, conflicts)
            
            self.logger.info(f"Generated {len(resolutions)} conflict resolutions")
            
            # Apply resolutions if requested
            if auto_apply:
                applied_count = 0
                for resolution in resolutions:
                    schedule_id = resolution.conflict.schedule_id_1
                    try:
                        # Find the schedule to modify
                        if schedule_id in self._schedules:
                            schedule = self._schedules[schedule_id]
                            modified_schedule = self.auto_rescheduler.apply_resolution(schedule, resolution)
                            
                            # Update the schedule
                            await self.update_scheduled_backup(
                                schedule_id,
                                ScheduleUpdates(
                                    schedule_pattern=modified_schedule.schedule_pattern
                                )
                            )
                            
                            applied_count += 1
                            self.logger.info(f"Applied resolution for schedule {schedule_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Failed to apply resolution for {schedule_id}: {e}")
                
                self.logger.info(f"Applied {applied_count}/{len(resolutions)} resolutions")
                
                # Log audit event
                self.audit_logger.log_conflict_resolution(
                    {
                        'resolutions_generated': len(resolutions),
                        'resolutions_applied': applied_count,
                        'auto_apply': auto_apply
                    }
                )
            
            return resolutions
            
        except Exception as e:
            error_msg = f"Failed to resolve schedule conflicts: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def optimize_schedules(
        self,
        auto_apply: bool = False
    ) -> list[ScheduleOptimization]:
        """
        Analyze and optimize schedule configurations.
        
        Args:
            auto_apply: If True, automatically apply optimizations
            
        Returns:
            List of optimization suggestions
            
        Raises:
            SchedulingError: If optimization fails
        """
        try:
            schedules = list(self._schedules.values())
            optimizations = self.optimizer.analyze_schedules(schedules)
            
            self.logger.info(f"Generated {len(optimizations)} optimization suggestions")
            
            # Apply optimizations if requested
            if auto_apply:
                applied_count = 0
                for optimization in optimizations:
                    schedule_id = optimization.schedule_id
                    try:
                        if schedule_id not in self._schedules:
                            continue
                        
                        schedule = self._schedules[schedule_id]
                        
                        # Apply optimization based on type
                        if optimization.optimization_type == "load_distribution":
                            # Update randomize_delay_minutes
                            schedule.schedule_pattern.randomize_delay_minutes = optimization.suggested_value
                            
                        elif optimization.optimization_type == "resource_usage":
                            # Update execution_timeout
                            schedule.execution_timeout = optimization.suggested_value
                            
                        elif optimization.optimization_type == "timing":
                            # Update interval_minutes
                            if schedule.schedule_pattern.interval_minutes:
                                schedule.schedule_pattern.interval_minutes = optimization.suggested_value
                        
                        # Update the schedule
                        await self.update_scheduled_backup(
                            schedule_id,
                            ScheduleUpdates(
                                schedule_pattern=schedule.schedule_pattern,
                                execution_timeout=schedule.execution_timeout
                            )
                        )
                        
                        applied_count += 1
                        self.logger.info(f"Applied optimization for schedule {schedule_id}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to apply optimization for {schedule_id}: {e}")
                
                self.logger.info(f"Applied {applied_count}/{len(optimizations)} optimizations")
                
                # Log audit event
                self.audit_logger.log_optimization(
                    {
                        'optimizations_generated': len(optimizations),
                        'optimizations_applied': applied_count,
                        'auto_apply': auto_apply
                    }
                )
            
            return optimizations
            
        except Exception as e:
            error_msg = f"Failed to optimize schedules: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def optimize_schedule_distribution(
        self,
        time_window_hours: int = 24
    ) -> bool:
        """
        Optimize distribution of schedules across time window.
        
        Args:
            time_window_hours: Time window for distribution
            
        Returns:
            True if optimization was successful
            
        Raises:
            SchedulingError: If optimization fails
        """
        try:
            schedules = list(self._schedules.values())
            
            # Optimize distribution
            optimized_schedules = self.optimizer.optimize_schedule_distribution(
                schedules,
                time_window_hours
            )
            
            # Update schedules
            updated_count = 0
            for optimized in optimized_schedules:
                if optimized.schedule_id in self._schedules:
                    original = self._schedules[optimized.schedule_id]
                    
                    # Check if schedule pattern changed
                    if optimized.schedule_pattern != original.schedule_pattern:
                        await self.update_scheduled_backup(
                            optimized.schedule_id,
                            ScheduleUpdates(
                                schedule_pattern=optimized.schedule_pattern
                            )
                        )
                        updated_count += 1
            
            self.logger.info(f"Optimized distribution: updated {updated_count} schedules")
            
            # Log audit event
            self.audit_logger.log_distribution_optimization(
                {
                    'time_window_hours': time_window_hours,
                    'schedules_updated': updated_count,
                    'total_schedules': len(schedules)
                }
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to optimize schedule distribution: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def reschedule_failed_backup(
        self,
        schedule_id: str,
        failure_reason: str
    ) -> bool:
        """
        Automatically reschedule a failed backup.
        
        Args:
            schedule_id: Schedule identifier
            failure_reason: Reason for failure
            
        Returns:
            True if rescheduling was successful
            
        Raises:
            SchedulingError: If rescheduling fails
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            schedule = self._schedules[schedule_id]
            
            # Check if schedule has retry configuration
            if not schedule.retry_config:
                self.logger.warning(f"No retry configuration for schedule {schedule_id}")
                return False
            
            # Calculate next retry time based on retry config
            retry_delay = timedelta(minutes=schedule.retry_config.initial_delay_minutes)
            next_retry_time = _utc_now() + retry_delay
            
            self.logger.info(
                f"Rescheduling failed backup {schedule_id} for {next_retry_time.isoformat()}"
            )
            
            # Log audit event
            self.audit_logger.log_automatic_reschedule(
                schedule_id,
                {
                    'failure_reason': failure_reason,
                    'next_retry_time': next_retry_time.isoformat(),
                    'retry_delay_minutes': schedule.retry_config.initial_delay_minutes
                }
            )
            
            # Report to monitoring
            self.monitoring_client.report_schedule_rescheduled(
                schedule_id,
                {
                    'reason': 'failure',
                    'next_run_time': next_retry_time.isoformat()
                }
            )
            
            return True
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to reschedule failed backup: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def get_conflict_summary(self) -> dict[str, object]:
        """
        Get summary of schedule conflicts.
        
        Returns:
            Dictionary with conflict summary
        """
        try:
            import asyncio
            
            # Run conflict detection
            conflicts = asyncio.run(self.detect_schedule_conflicts())
            
            # Categorize by severity
            critical = [c for c in conflicts if c.severity.value == 'critical']
            high = [c for c in conflicts if c.severity.value == 'high']
            medium = [c for c in conflicts if c.severity.value == 'medium']
            low = [c for c in conflicts if c.severity.value == 'low']
            
            return {
                'total_conflicts': len(conflicts),
                'critical_conflicts': len(critical),
                'high_conflicts': len(high),
                'medium_conflicts': len(medium),
                'low_conflicts': len(low),
                'requires_immediate_action': len(critical) > 0,
                'timestamp': _utc_now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get conflict summary: {e}")
            return {
                'error': str(e),
                'timestamp': _utc_now().isoformat()
            }
    
    def get_optimization_summary(self) -> dict[str, object]:
        """
        Get summary of optimization opportunities.
        
        Returns:
            Dictionary with optimization summary
        """
        try:
            schedules = list(self._schedules.values())
            optimizations = self.optimizer.analyze_schedules(schedules)
            
            # Categorize by type
            load_dist = [o for o in optimizations if o.optimization_type == 'load_distribution']
            resource = [o for o in optimizations if o.optimization_type == 'resource_usage']
            timing = [o for o in optimizations if o.optimization_type == 'timing']
            
            # Calculate potential improvement
            total_improvement = sum(o.estimated_improvement for o in optimizations)
            avg_improvement = total_improvement / len(optimizations) if optimizations else 0
            
            return {
                'total_optimizations': len(optimizations),
                'load_distribution_opportunities': len(load_dist),
                'resource_usage_opportunities': len(resource),
                'timing_opportunities': len(timing),
                'average_improvement_potential': round(avg_improvement, 2),
                'timestamp': _utc_now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization summary: {e}")
            return {
                'error': str(e),
                'timestamp': _utc_now().isoformat()
            }
    
    async def _handle_policy_update(self, policy_id: str, updates: dict[str, object]) -> None:
        """
        Handle policy update notifications and synchronize affected schedules.
        
        This method is called when a policy is updated to automatically
        update any schedules that use the policy.
        
        Args:
            policy_id: Policy identifier that was updated
            updates: Dictionary of updates made to the policy
        """
        try:
            self.logger.info(f"Handling policy update for {policy_id}")
            
            # Find all schedules using this policy
            affected_schedules = [
                s for s in self._schedules.values()
                if s.policy_id == policy_id
            ]
            
            if not affected_schedules:
                self.logger.debug(f"No schedules affected by policy update: {policy_id}")
                return
            
            self.logger.info(f"Found {len(affected_schedules)} schedules affected by policy update")
            
            # Validate policy is still suitable for scheduling
            is_valid, errors = self.policy_client.validate_policy_for_scheduling(policy_id)
            
            if not is_valid:
                # Policy is no longer valid for scheduling - disable affected schedules
                self.logger.warning(
                    f"Policy {policy_id} is no longer valid for scheduling. "
                    f"Disabling {len(affected_schedules)} affected schedules."
                )
                
                for schedule in affected_schedules:
                    try:
                        await self.disable_schedule(schedule.schedule_id)
                        
                        # Log audit event
                        self.audit_logger.log_schedule_auto_disabled(
                            schedule.schedule_id,
                            {
                                'reason': 'policy_invalid',
                                'policy_id': policy_id,
                                'validation_errors': errors
                            }
                        )
                        
                        # Report to monitoring
                        self.monitoring_client.report_schedule_updated(
                            schedule.schedule_id,
                            {
                                'auto_disabled': True,
                                'reason': 'policy_invalid',
                                'policy_id': policy_id
                            }
                        )
                        
                    except Exception as e:
                        self.logger.error(
                            f"Failed to disable schedule {schedule.schedule_id} "
                            f"after policy invalidation: {e}"
                        )
            else:
                # Policy is still valid - check if schedules need updates
                for schedule in affected_schedules:
                    try:
                        # Re-validate schedule configuration
                        validation_result = await self.validate_schedule_configuration(schedule)
                        
                        if not validation_result.is_valid:
                            self.logger.warning(
                                f"Schedule {schedule.schedule_id} is no longer valid "
                                f"after policy update. Disabling."
                            )
                            
                            await self.disable_schedule(schedule.schedule_id)
                            
                            # Log audit event
                            self.audit_logger.log_schedule_auto_disabled(
                                schedule.schedule_id,
                                {
                                    'reason': 'schedule_invalid_after_policy_update',
                                    'policy_id': policy_id,
                                    'validation_errors': validation_result.errors
                                }
                            )
                        else:
                            # Schedule is still valid - log the policy update
                            self.audit_logger.log_policy_update_processed(
                                schedule.schedule_id,
                                {
                                    'policy_id': policy_id,
                                    'updates': updates,
                                    'schedule_remains_valid': True
                                }
                            )
                            
                            # Report to monitoring
                            self.monitoring_client.report_schedule_updated(
                                schedule.schedule_id,
                                {
                                    'policy_updated': True,
                                    'policy_id': policy_id,
                                    'schedule_validated': True
                                }
                            )
                            
                    except Exception as e:
                        self.logger.error(
                            f"Failed to process policy update for schedule {schedule.schedule_id}: {e}"
                        )
            
            self.logger.info(f"Completed processing policy update for {policy_id}")
            
        except Exception as e:
            self.logger.error(f"Error handling policy update for {policy_id}: {e}", exc_info=True)
    
    async def synchronize_policy_schedules(self, policy_id: str) -> dict[str, object]:
        """
        Synchronize all schedules using a specific policy.
        
        This method validates and updates all schedules that use the specified
        policy, ensuring they are still valid and compatible.
        
        Args:
            policy_id: Policy identifier to synchronize
            
        Returns:
            Dictionary with synchronization results
        """
        try:
            self.logger.info(f"Synchronizing schedules for policy {policy_id}")
            
            # Find all schedules using this policy
            affected_schedules = [
                s for s in self._schedules.values()
                if s.policy_id == policy_id
            ]
            
            if not affected_schedules:
                return {
                    'policy_id': policy_id,
                    'schedules_found': 0,
                    'schedules_validated': 0,
                    'schedules_disabled': 0,
                    'errors': [],
                }
            
            validated_count = 0
            disabled_count = 0
            errors: list[str] = []
            
            # Validate policy
            is_valid, policy_errors = self.policy_client.validate_policy_for_scheduling(policy_id)
            
            if not is_valid:
                # Disable all schedules using invalid policy
                for schedule in affected_schedules:
                    try:
                        await self.disable_schedule(schedule.schedule_id)
                        disabled_count += 1
                    except Exception as e:
                        errors.append(f"Failed to disable schedule {schedule.schedule_id}: {str(e)}")
            else:
                # Validate each schedule
                for schedule in affected_schedules:
                    try:
                        validation_result = await self.validate_schedule_configuration(schedule)
                        
                        if validation_result.is_valid:
                            validated_count += 1
                        else:
                            await self.disable_schedule(schedule.schedule_id)
                            disabled_count += 1
                            errors.append(
                                f"Schedule {schedule.schedule_id} disabled: "
                                f"{', '.join(validation_result.errors)}"
                            )
                    except Exception as e:
                        errors.append(f"Error validating schedule {schedule.schedule_id}: {str(e)}")
            
            result: dict[str, object] = {
                'policy_id': policy_id,
                'schedules_found': len(affected_schedules),
                'schedules_validated': validated_count,
                'schedules_disabled': disabled_count,
                'errors': errors,
            }
            
            # Log audit event
            self.audit_logger.log_policy_synchronization(policy_id, result)
            
            self.logger.info(
                f"Policy synchronization complete for {policy_id}: "
                f"{validated_count} validated, {disabled_count} disabled"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to synchronize policy schedules: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    def get_schedules_by_policy(self, policy_id: str) -> list[ScheduleInfo]:
        """
        Get all schedules that use a specific policy.
        
        Args:
            policy_id: Policy identifier
            
        Returns:
            List of ScheduleInfo for schedules using the policy
        """
        try:
            schedules = [
                s for s in self._schedules.values()
                if s.policy_id == policy_id
            ]
            
            schedule_infos: list[ScheduleInfo] = []
            for schedule in schedules:
                schedule_info = ScheduleInfo(
                    schedule_id=schedule.schedule_id,
                    name=schedule.name,
                    description=schedule.description,
                    policy_id=schedule.policy_id,
                    enabled=schedule.enabled,
                    next_execution_time=None,  # Would need to query platform
                    health_status=ScheduleHealthStatus.HEALTHY if schedule.enabled else ScheduleHealthStatus.UNKNOWN,
                    created_at=schedule.created_at,
                    updated_at=schedule.updated_at
                )
                schedule_infos.append(schedule_info)
            
            self.logger.debug(f"Found {len(schedule_infos)} schedules for policy {policy_id}")
            return schedule_infos
            
        except Exception as e:
            self.logger.error(f"Failed to get schedules by policy: {e}")
            return []
    
    def register_health_check_webhook(
        self,
        webhook_url: str,
        schedule_id: str | None = None
    ) -> None:
        """
        Register a health check webhook for monitoring integration.
        
        Args:
            webhook_url: URL to call for health checks
            schedule_id: Optional schedule ID to associate with webhook
        """
        self.monitoring_client.register_health_check_webhook(webhook_url, schedule_id)
        self.logger.info(f"Registered health check webhook for schedule {schedule_id or 'all'}")
    
    def unregister_health_check_webhook(self, webhook_url: str) -> None:
        """
        Unregister a health check webhook.
        
        Args:
            webhook_url: URL to unregister
        """
        self.monitoring_client.unregister_health_check_webhook(webhook_url)
        self.logger.info(f"Unregistered health check webhook: {webhook_url}")
    
    async def send_health_check_pings(self) -> dict[str, object]:
        """
        Send health check pings for all enabled schedules.
        
        Returns:
            Dictionary with ping results
        """
        try:
            enabled_schedules = [s for s in self._schedules.values() if s.enabled]
            
            total_schedules = len(enabled_schedules)
            pings_sent = 0
            errors: list[str] = []
            
            for schedule in enabled_schedules:
                try:
                    # Get schedule status
                    status = await self.get_schedule_status(schedule.schedule_id)
                    
                    # Determine health status
                    health_status = 'healthy'
                    if status.health_status == ScheduleHealthStatus.WARNING:
                        health_status = 'warning'
                    elif status.health_status == ScheduleHealthStatus.ERROR:
                        health_status = 'error'
                    elif status.health_status == ScheduleHealthStatus.UNKNOWN:
                        health_status = 'unknown'
                    
                    # Send ping
                    await self.monitoring_client.send_health_check_ping(
                        schedule.schedule_id,
                        health_status,
                        {
                            'schedule_name': schedule.name,
                            'policy_id': schedule.policy_id,
                            'next_execution': status.next_execution_time.isoformat() if status.next_execution_time else None
                        }
                    )
                    
                    pings_sent += 1
                    
                except Exception as e:
                    error_msg = f"Failed to send ping for schedule {schedule.schedule_id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            self.logger.info(
                f"Sent {pings_sent} health check pings "
                f"({len(errors)} errors)"
            )
            
            return {
                'total_schedules': total_schedules,
                'pings_sent': pings_sent,
                'errors': errors,
            }
            
        except Exception as e:
            error_msg = f"Failed to send health check pings: {e}"
            self.logger.error(error_msg)
            return {
                'error': str(e),
                'timestamp': _utc_now().isoformat()
            }
    
    async def report_scheduling_metrics(self) -> None:
        """
        Report comprehensive scheduling metrics to monitoring system.
        """
        try:
            # Gather metrics
            health_summary = await self.get_schedule_health_summary()
            next_runs = await self.get_next_scheduled_runs(limit=10)
            conflict_summary = self.get_conflict_summary()
            optimization_summary = self.get_optimization_summary()
            
            metrics = {
                'health_summary': health_summary,
                'next_runs_count': len(next_runs),
                'next_runs': next_runs,
                'conflict_summary': conflict_summary,
                'optimization_summary': optimization_summary,
                'timestamp': _utc_now().isoformat()
            }
            
            # Report to monitoring
            self.monitoring_client.report_scheduling_metrics(metrics)
            
            # Report next scheduled runs
            if next_runs:
                self.monitoring_client.report_next_scheduled_runs(next_runs)
            
            self.logger.info("Reported scheduling metrics to monitoring system")
            
        except Exception as e:
            self.logger.error(f"Failed to report scheduling metrics: {e}")
    
    async def monitor_schedule_health(self, schedule_id: str) -> None:
        """
        Monitor and report health status for a specific schedule.
        
        Args:
            schedule_id: Schedule identifier
        """
        try:
            if schedule_id not in self._schedules:
                raise SchedulingError(f"Schedule not found: {schedule_id}")
            
            # Get schedule status
            status = await self.get_schedule_status(schedule_id)
            
            # Map health status to string
            health_status_map = {
                ScheduleHealthStatus.HEALTHY: 'healthy',
                ScheduleHealthStatus.WARNING: 'warning',
                ScheduleHealthStatus.ERROR: 'error',
                ScheduleHealthStatus.UNKNOWN: 'unknown'
            }
            
            health_status = health_status_map.get(status.health_status, 'unknown')
            
            # Prepare details
            details = {
                'schedule_name': self._schedules[schedule_id].name,
                'policy_id': self._schedules[schedule_id].policy_id,
                'enabled': status.enabled,
                'next_execution': status.next_execution_time.isoformat() if status.next_execution_time else None,
                'platform_active': status.platform_status.is_active if status.platform_status else False
            }
            
            # Report to monitoring
            self.monitoring_client.report_schedule_health_status(
                schedule_id,
                health_status,
                details
            )
            
            # Send health check ping
            await self.monitoring_client.send_health_check_ping(
                schedule_id,
                health_status,
                details
            )
            
            self.logger.debug(f"Monitored health for schedule {schedule_id}: {health_status}")
            
        except SchedulingError:
            raise
        except Exception as e:
            error_msg = f"Failed to monitor schedule health: {e}"
            self.logger.error(error_msg)
            raise SchedulingError(error_msg) from e
    
    async def monitor_all_schedules(self) -> dict[str, object]:
        """
        Monitor health status for all schedules and report to monitoring system.
        
        Returns:
            Dictionary with monitoring results
        """
        try:
            enabled_schedules = [s for s in self._schedules.values() if s.enabled]
            
            total_schedules = len(enabled_schedules)
            monitored = 0
            healthy = 0
            warning = 0
            error = 0
            unknown = 0
            errors: list[str] = []
            
            for schedule in enabled_schedules:
                try:
                    await self.monitor_schedule_health(schedule.schedule_id)
                    monitored += 1
                    
                    # Get status to update counts
                    status = await self.get_schedule_status(schedule.schedule_id)
                    if status.health_status == ScheduleHealthStatus.HEALTHY:
                        healthy += 1
                    elif status.health_status == ScheduleHealthStatus.WARNING:
                        warning += 1
                    elif status.health_status == ScheduleHealthStatus.ERROR:
                        error += 1
                    else:
                        unknown += 1
                        
                except Exception as e:
                    error_msg = f"Failed to monitor schedule {schedule.schedule_id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Report overall metrics
            await self.report_scheduling_metrics()
            
            self.logger.info(
                f"Monitored {monitored} schedules: "
                f"{healthy} healthy, {warning} warning, "
                f"{error} error, {unknown} unknown"
            )
            
            return {
                'total_schedules': total_schedules,
                'monitored': monitored,
                'healthy': healthy,
                'warning': warning,
                'error': error,
                'unknown': unknown,
                'errors': errors,
            }
            
        except Exception as e:
            error_msg = f"Failed to monitor all schedules: {e}"
            self.logger.error(error_msg)
            return {
                'error': str(e),
                'timestamp': _utc_now().isoformat()
            }
