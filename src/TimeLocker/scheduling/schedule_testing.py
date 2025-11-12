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

Schedule Testing and Debugging Tools

This module provides testing and debugging capabilities for scheduled backups,
including test execution, health checks, and diagnostic tools.
"""

import logging
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .scheduling_models import (
    ScheduleConfig,
    ExecutionContext,
    ExecutionTrigger,
    ExecutionStatus,
    ValidationResult
)
from .scheduling_exceptions import SchedulingError
from .schedule_validator import ScheduleValidator
from .platform_adapter import PlatformAdapter
from .integration_clients import (
    PolicyManagementClient,
    DataSelectionClient,
    RepositoryManagementClient
)

logger = logging.getLogger(__name__)


@dataclass
class TestExecutionResult:
    """Result of a test execution."""
    success: bool
    schedule_id: str
    test_type: str
    execution_time: timedelta
    validation_result: Optional[ValidationResult] = None
    simulation_result: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    is_healthy: bool
    check_type: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class DiagnosticResult:
    """Result of diagnostic analysis."""
    schedule_id: str
    timestamp: datetime
    platform_info: Dict[str, Any]
    configuration_status: Dict[str, Any]
    integration_status: Dict[str, Any]
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ScheduleTester:
    """
    Testing and debugging tools for scheduled backups.
    
    Provides test execution, simulation, health checks, and diagnostics.
    """
    
    def __init__(
        self,
        platform_adapter: PlatformAdapter,
        validator: Optional[ScheduleValidator] = None,
        policy_client: Optional[PolicyManagementClient] = None,
        data_selection_client: Optional[DataSelectionClient] = None,
        repository_client: Optional[RepositoryManagementClient] = None
    ):
        """
        Initialize schedule tester.
        
        Args:
            platform_adapter: Platform adapter for platform-specific operations
            validator: Optional schedule validator
            policy_client: Optional policy management client
            data_selection_client: Optional data selection client
            repository_client: Optional repository management client
        """
        self.logger = logging.getLogger(f"{__name__}.ScheduleTester")
        self.platform_adapter = platform_adapter
        
        # Initialize validator
        if validator is None:
            self.validator = ScheduleValidator(
                platform_adapter=platform_adapter,
                policy_client=policy_client,
                data_selection_client=data_selection_client,
                repository_client=repository_client
            )
        else:
            self.validator = validator
        
        # Initialize integration clients
        self.policy_client = policy_client or PolicyManagementClient()
        self.data_selection_client = data_selection_client or DataSelectionClient()
        self.repository_client = repository_client or RepositoryManagementClient()
    
    async def test_schedule_execution(
        self,
        config: ScheduleConfig,
        dry_run: bool = True
    ) -> TestExecutionResult:
        """
        Test schedule execution with optional dry-run mode.
        
        Args:
            config: Schedule configuration to test
            dry_run: If True, simulate execution without actual backup
            
        Returns:
            TestExecutionResult with test results
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate configuration
            validation_result = self.validator.validate_dry_run_configuration(config)
            
            if not validation_result.is_valid:
                return TestExecutionResult(
                    success=False,
                    schedule_id=config.schedule_id,
                    test_type="dry_run" if dry_run else "live_test",
                    execution_time=datetime.utcnow() - start_time,
                    validation_result=validation_result,
                    errors=validation_result.errors,
                    warnings=validation_result.warnings
                )
            
            # Simulate backup execution
            if dry_run:
                simulation_result = await self._simulate_backup_execution(config)
                
                return TestExecutionResult(
                    success=simulation_result['success'],
                    schedule_id=config.schedule_id,
                    test_type="dry_run",
                    execution_time=datetime.utcnow() - start_time,
                    validation_result=validation_result,
                    simulation_result=simulation_result,
                    warnings=validation_result.warnings,
                    metadata={
                        'simulated': True,
                        'policy_id': config.policy_id
                    }
                )
            else:
                # Perform actual test execution
                # This would integrate with the automation engine
                self.logger.warning("Live test execution not yet implemented")
                return TestExecutionResult(
                    success=False,
                    schedule_id=config.schedule_id,
                    test_type="live_test",
                    execution_time=datetime.utcnow() - start_time,
                    validation_result=validation_result,
                    errors=["Live test execution not yet implemented"],
                    warnings=validation_result.warnings
                )
                
        except Exception as e:
            self.logger.error(f"Test execution failed for schedule {config.schedule_id}: {e}")
            return TestExecutionResult(
                success=False,
                schedule_id=config.schedule_id,
                test_type="dry_run" if dry_run else "live_test",
                execution_time=datetime.utcnow() - start_time,
                errors=[f"Test execution error: {str(e)}"]
            )
    
    async def _simulate_backup_execution(self, config: ScheduleConfig) -> Dict[str, Any]:
        """
        Simulate backup execution without performing actual backup.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Dictionary with simulation results
        """
        simulation_result = {
            'success': True,
            'steps_completed': [],
            'steps_failed': [],
            'warnings': []
        }
        
        try:
            # Step 1: Retrieve policy
            policy = self.policy_client.get_backup_policy(config.policy_id)
            if policy:
                simulation_result['steps_completed'].append('policy_retrieval')
            else:
                simulation_result['steps_failed'].append('policy_retrieval')
                simulation_result['success'] = False
                return simulation_result
            
            # Step 2: Retrieve data selections
            data_selections = getattr(policy, 'data_selection_refs', [])
            for selection_ref in data_selections:
                template = self.data_selection_client.get_selection_template(selection_ref)
                if template:
                    simulation_result['steps_completed'].append(f'data_selection_{selection_ref}')
                else:
                    simulation_result['steps_failed'].append(f'data_selection_{selection_ref}')
                    simulation_result['warnings'].append(f"Failed to retrieve data selection: {selection_ref}")
            
            # Step 3: Retrieve repository configurations
            repositories = getattr(policy, 'target_repositories', [])
            for repo_id in repositories:
                repo_config = self.repository_client.get_repository_config(repo_id)
                if repo_config:
                    simulation_result['steps_completed'].append(f'repository_{repo_id}')
                else:
                    simulation_result['steps_failed'].append(f'repository_{repo_id}')
                    simulation_result['warnings'].append(f"Failed to retrieve repository: {repo_id}")
            
            # Step 4: Simulate backup operation
            simulation_result['steps_completed'].append('backup_simulation')
            simulation_result['simulated_files'] = 100
            simulation_result['simulated_size_bytes'] = 1024 * 1024 * 100  # 100 MB
            
            # Step 5: Simulate monitoring notification
            if config.monitoring_config:
                simulation_result['steps_completed'].append('monitoring_notification')
            
            return simulation_result
            
        except Exception as e:
            simulation_result['success'] = False
            simulation_result['steps_failed'].append(f'simulation_error: {str(e)}')
            return simulation_result
    
    async def check_platform_scheduler_health(self) -> HealthCheckResult:
        """
        Check health of platform scheduler.
        
        Returns:
            HealthCheckResult with platform scheduler health status
        """
        try:
            platform_name = self.platform_adapter.get_platform_name()
            
            # Check if platform scheduler is available and running
            is_available = await self._check_scheduler_availability(platform_name)
            
            details = {
                'platform': platform_name,
                'scheduler_available': is_available,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            issues = []
            recommendations = []
            
            if not is_available:
                issues.append(f"Platform scheduler ({platform_name}) is not available")
                recommendations.append(f"Ensure {platform_name} is installed and running")
            
            return HealthCheckResult(
                is_healthy=is_available,
                check_type="platform_scheduler",
                timestamp=datetime.utcnow(),
                details=details,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Platform scheduler health check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                check_type="platform_scheduler",
                timestamp=datetime.utcnow(),
                details={'error': str(e)},
                issues=[f"Health check error: {str(e)}"],
                recommendations=["Check platform scheduler installation and permissions"]
            )
    
    async def _check_scheduler_availability(self, platform_name: str) -> bool:
        """
        Check if platform scheduler is available.
        
        Args:
            platform_name: Name of the platform scheduler
            
        Returns:
            True if scheduler is available
        """
        try:
            if platform_name == "systemd":
                result = subprocess.run(
                    ["systemctl", "--user", "status"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            
            elif platform_name == "cron":
                result = subprocess.run(
                    ["crontab", "-l"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode in [0, 1]  # 0=has entries, 1=no entries
            
            elif platform_name == "windows_task_scheduler":
                result = subprocess.run(
                    ["schtasks", "/query"],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            
            elif platform_name == "launchd":
                return Path("/bin/launchctl").exists()
            
            else:
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.logger.warning(f"Scheduler availability check failed: {e}")
            return False
    
    async def check_system_resources(self) -> HealthCheckResult:
        """
        Check system resources for scheduled backup execution.
        
        Returns:
            HealthCheckResult with system resource status
        """
        try:
            details = {}
            issues = []
            recommendations = []
            
            # Check disk space
            disk_usage = shutil.disk_usage("/")
            free_gb = disk_usage.free / (1024 ** 3)
            total_gb = disk_usage.total / (1024 ** 3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            details['disk_free_gb'] = round(free_gb, 2)
            details['disk_total_gb'] = round(total_gb, 2)
            details['disk_usage_percent'] = round(usage_percent, 2)
            
            if usage_percent > 90:
                issues.append(f"Disk usage is very high ({usage_percent:.1f}%)")
                recommendations.append("Free up disk space before scheduling backups")
            elif usage_percent > 80:
                recommendations.append(f"Disk usage is high ({usage_percent:.1f}%), monitor space")
            
            # Check if TimeLocker executable is accessible
            timelocker_path = shutil.which("timelocker")
            details['timelocker_executable'] = timelocker_path or "not found"
            
            if not timelocker_path:
                issues.append("TimeLocker executable not found in PATH")
                recommendations.append("Ensure TimeLocker is installed and in PATH")
            
            # Check Python version
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            details['python_version'] = python_version
            
            is_healthy = len(issues) == 0
            
            return HealthCheckResult(
                is_healthy=is_healthy,
                check_type="system_resources",
                timestamp=datetime.utcnow(),
                details=details,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"System resources health check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                check_type="system_resources",
                timestamp=datetime.utcnow(),
                details={'error': str(e)},
                issues=[f"Health check error: {str(e)}"],
                recommendations=["Check system configuration and permissions"]
            )
    
    async def run_diagnostic(self, config: ScheduleConfig) -> DiagnosticResult:
        """
        Run comprehensive diagnostic for a schedule configuration.
        
        Args:
            config: Schedule configuration to diagnose
            
        Returns:
            DiagnosticResult with diagnostic information
        """
        try:
            # Gather platform information
            platform_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'adapter': self.platform_adapter.get_platform_name()
            }
            
            # Check configuration status
            validation_result = self.validator.validate_schedule_configuration(config, comprehensive=True)
            configuration_status = {
                'is_valid': validation_result.is_valid,
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            }
            
            # Check integration status
            integration_status = await self._check_integration_status(config)
            
            # Collect issues and recommendations
            issues_found = []
            recommendations = []
            
            if not validation_result.is_valid:
                issues_found.extend(validation_result.errors)
                recommendations.append("Fix configuration errors before scheduling")
            
            if validation_result.warnings:
                recommendations.extend([f"Consider: {w}" for w in validation_result.warnings])
            
            if not integration_status['policy_accessible']:
                issues_found.append("Policy is not accessible")
                recommendations.append("Verify policy exists and is configured correctly")
            
            if not integration_status['all_repositories_accessible']:
                issues_found.append("Some repositories are not accessible")
                recommendations.append("Verify repository configurations and credentials")
            
            return DiagnosticResult(
                schedule_id=config.schedule_id,
                timestamp=datetime.utcnow(),
                platform_info=platform_info,
                configuration_status=configuration_status,
                integration_status=integration_status,
                issues_found=issues_found,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Diagnostic failed for schedule {config.schedule_id}: {e}")
            return DiagnosticResult(
                schedule_id=config.schedule_id,
                timestamp=datetime.utcnow(),
                platform_info={'error': str(e)},
                configuration_status={'error': str(e)},
                integration_status={'error': str(e)},
                issues_found=[f"Diagnostic error: {str(e)}"],
                recommendations=["Check logs for detailed error information"]
            )
    
    async def _check_integration_status(self, config: ScheduleConfig) -> Dict[str, Any]:
        """
        Check status of all integration points.
        
        Args:
            config: Schedule configuration
            
        Returns:
            Dictionary with integration status
        """
        status = {
            'policy_accessible': False,
            'data_selections_accessible': [],
            'repositories_accessible': [],
            'all_data_selections_accessible': True,
            'all_repositories_accessible': True
        }
        
        try:
            # Check policy
            policy = self.policy_client.get_backup_policy(config.policy_id)
            status['policy_accessible'] = policy is not None
            
            if policy:
                # Check data selections
                data_selections = getattr(policy, 'data_selection_refs', [])
                for selection_ref in data_selections:
                    template = self.data_selection_client.get_selection_template(selection_ref)
                    accessible = template is not None
                    status['data_selections_accessible'].append({
                        'id': selection_ref,
                        'accessible': accessible
                    })
                    if not accessible:
                        status['all_data_selections_accessible'] = False
                
                # Check repositories
                repositories = getattr(policy, 'target_repositories', [])
                for repo_id in repositories:
                    repo_config = self.repository_client.get_repository_config(repo_id)
                    accessible = repo_config is not None
                    status['repositories_accessible'].append({
                        'id': repo_id,
                        'accessible': accessible
                    })
                    if not accessible:
                        status['all_repositories_accessible'] = False
            
        except Exception as e:
            self.logger.error(f"Integration status check failed: {e}")
            status['error'] = str(e)
        
        return status
    
    async def check_schedule_conflicts(
        self,
        config: ScheduleConfig,
        existing_schedules: List[ScheduleConfig]
    ) -> HealthCheckResult:
        """
        Check for scheduling conflicts with existing schedules.
        
        Args:
            config: Schedule configuration to check
            existing_schedules: List of existing schedule configurations
            
        Returns:
            HealthCheckResult with conflict information
        """
        try:
            conflicts = []
            warnings = []
            
            # Check for same policy scheduled multiple times
            same_policy_schedules = [
                s for s in existing_schedules
                if s.policy_id == config.policy_id and s.schedule_id != config.schedule_id
            ]
            
            if same_policy_schedules:
                warnings.append(
                    f"Policy {config.policy_id} is already scheduled {len(same_policy_schedules)} time(s)"
                )
            
            # Check for overlapping backup windows
            # This is a simplified check - real implementation would need more sophisticated logic
            if config.schedule_pattern.backup_window:
                for existing in existing_schedules:
                    if existing.schedule_id == config.schedule_id:
                        continue
                    
                    if existing.schedule_pattern.backup_window:
                        # Check for window overlap
                        if self._windows_overlap(
                            config.schedule_pattern.backup_window,
                            existing.schedule_pattern.backup_window
                        ):
                            warnings.append(
                                f"Backup window overlaps with schedule {existing.name}"
                            )
            
            is_healthy = len(conflicts) == 0
            
            return HealthCheckResult(
                is_healthy=is_healthy,
                check_type="schedule_conflicts",
                timestamp=datetime.utcnow(),
                details={
                    'conflicts_found': len(conflicts),
                    'warnings_found': len(warnings)
                },
                issues=conflicts,
                recommendations=warnings
            )
            
        except Exception as e:
            self.logger.error(f"Conflict check failed: {e}")
            return HealthCheckResult(
                is_healthy=False,
                check_type="schedule_conflicts",
                timestamp=datetime.utcnow(),
                details={'error': str(e)},
                issues=[f"Conflict check error: {str(e)}"],
                recommendations=["Review schedule configuration"]
            )
    
    def _windows_overlap(self, window1, window2) -> bool:
        """
        Check if two backup windows overlap.
        
        Args:
            window1: First backup window
            window2: Second backup window
            
        Returns:
            True if windows overlap
        """
        # Simple overlap check - assumes same day
        return not (
            window1.end_time <= window2.start_time or
            window2.end_time <= window1.start_time
        )
