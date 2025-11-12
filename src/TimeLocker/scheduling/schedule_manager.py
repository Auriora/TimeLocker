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
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from .platform_detector import PlatformDetector
from .platform_adapter import PlatformAdapter
from .scheduling_configuration import SchedulingConfiguration
from .scheduling_models import (
    ScheduleRequest,
    ScheduleConfig,
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

logger = logging.getLogger(__name__)


class ScheduleManager:
    """
    Central orchestrator for scheduling operations.
    
    This class coordinates between platform-specific adapters and
    TimeLocker components to provide unified scheduling functionality.
    """
    
    def __init__(
        self,
        config: Optional[SchedulingConfiguration] = None,
        adapter: Optional[PlatformAdapter] = None,
        config_dir: Optional[Path] = None
    ):
        """
        Initialize schedule manager.
        
        Args:
            config: Optional scheduling configuration (loads default if not provided)
            adapter: Optional platform adapter (auto-detects if not provided)
            config_dir: Optional configuration directory
        """
        self.logger = logging.getLogger(f"{__name__}.ScheduleManager")
        
        # Determine configuration directory
        if config_dir is None:
            from ..config.configuration_path_resolver import ConfigurationPathResolver
            config_dir = ConfigurationPathResolver.get_config_directory() / "scheduling"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or use provided configuration
        if config is None:
            config_path = self.config_dir / "scheduling_config.json"
            if config_path.exists():
                self.config = SchedulingConfiguration.load_from_file(config_path)
            else:
                self.config = SchedulingConfiguration()
                self.logger.info("Using default scheduling configuration")
        else:
            self.config = config
        
        # Detect or use provided platform adapter
        if adapter is None:
            adapter_class = PlatformDetector.detect_best_scheduler()
            self.adapter = adapter_class()
            self.logger.info(f"Auto-detected platform adapter: {self.adapter.get_platform_name()}")
        else:
            self.adapter = adapter
            self.logger.info(f"Using provided platform adapter: {self.adapter.get_platform_name()}")
        
        # Initialize integration clients
        self.policy_client = PolicyManagementClient()
        self.data_selection_client = DataSelectionClient()
        self.repository_client = RepositoryManagementClient()
        self.monitoring_client = MonitoringClient()
        
        # Initialize audit logger
        self.audit_logger = SchedulingAuditLogger(
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
        self.storage = ScheduleStorage(self.config_dir / "schedules")
        
        # Initialize validator and tester
        self.validator = ScheduleValidator(
            platform_adapter=self.adapter,
            policy_client=self.policy_client,
            data_selection_client=self.data_selection_client,
            repository_client=self.repository_client
        )
        
        self.tester = ScheduleTester(
            platform_adapter=self.adapter,
            validator=self.validator,
            policy_client=self.policy_client,
            data_selection_client=self.data_selection_client,
            repository_client=self.repository_client
        )
        
        # In-memory cache of schedules
        self._schedules: Dict[str, ScheduleConfig] = {}
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
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=""  # TODO: Get from context
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
            
            schedule_config.updated_at = datetime.utcnow()
            
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
            if updates.name: update_details['name'] = updates.name
            if updates.enabled is not None: update_details['enabled'] = updates.enabled
            if updates.schedule_pattern: update_details['schedule_pattern'] = 'updated'
            
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
            
            # TODO: Get execution history from execution tracking system
            # For now, return empty history
            execution_history = []
            last_execution = None
            
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
        filters: Optional[ScheduleFilters] = None
    ) -> List[ScheduleInfo]:
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
                
                # TODO: Filter by health_status when we have execution tracking
            
            # Convert to ScheduleInfo
            schedule_infos = []
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

    async def get_schedule_health_summary(self) -> Dict[str, Any]:
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
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get schedule health summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def get_next_scheduled_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the next scheduled backup runs across all schedules.
        
        Args:
            limit: Maximum number of runs to return
            
        Returns:
            List of upcoming scheduled runs with schedule information
        """
        try:
            upcoming_runs = []
            
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
            upcoming_runs.sort(key=lambda x: x['next_run_time'])
            
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
            schedule_config.updated_at = datetime.utcnow()
            
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
            schedule_config.updated_at = datetime.utcnow()
            
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
        schedule_id: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for scheduling operations.
        
        Args:
            schedule_id: Optional filter by schedule ID
            days: Number of days to look back
            
        Returns:
            List of audit entries
        """
        try:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            
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
                timestamp=datetime.utcnow(),
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
                timestamp=datetime.utcnow(),
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        schedule_ids: Optional[List[str]] = None
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
    
    def get_policy_compliance_summary(self, policy_id: str) -> Dict[str, Any]:
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
    
    def get_audit_statistics(self) -> Dict[str, Any]:
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
        schedule_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
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
