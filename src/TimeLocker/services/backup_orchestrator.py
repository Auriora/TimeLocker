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
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, Future

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
from ..backup_target import BackupTarget
from ..file_selections import FileSelection, SelectionType
from ..utils import (
    with_error_handling,
    with_retry,
    profile_operation,
    start_operation_tracking,
    update_operation_tracking,
    complete_operation_tracking
)

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
                 max_concurrent_backups: int = 2):
        """
        Initialize backup orchestrator.
        
        Args:
            repository_factory: Factory for creating repository instances
            configuration_provider: Provider for configuration access
            max_concurrent_backups: Maximum number of concurrent backup operations
        """
        self._repository_factory = repository_factory
        self._configuration_provider = configuration_provider
        self._max_concurrent_backups = max_concurrent_backups

        # Track active backup operations
        self._active_backups: Dict[str, BackupResult] = {}
        self._backup_history: List[BackupResult] = []
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_backups)
        self._futures: Dict[str, Future] = {}

        logger.debug(f"BackupOrchestrator initialized with max_concurrent_backups={max_concurrent_backups}")

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
                metadata={'operation_id': operation_id, 'dry_run': dry_run, 'tags': tags or [], 'password': password}
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
                backup_result = self._execute_actual_backup(backup_result)

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
                for path in target.paths:
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

    def _execute_actual_backup(self, backup_result: BackupResult) -> BackupResult:
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
            password = backup_result.metadata.get('password')
            logger.debug(f"Password retrieved from metadata: {'***' if password else 'None'}")
            logger.debug(f"Repository URI: {repo_config['uri']}")
            repository = self._repository_factory.create_repository(repo_config['uri'], password=password)

            # Get backup targets
            targets = self._get_backup_targets(backup_result.target_names)

            # Execute backup with retry
            @with_retry(max_retries=3, delay=1.0, backoff_multiplier=2.0)
            def _perform_backup():
                return repository.backup_target(targets, backup_result.metadata.get('tags', []))

            result = _perform_backup()

            if result and 'snapshot_id' in result:
                backup_result.snapshot_id = result['snapshot_id']
                backup_result.files_processed = result.get('files_processed', 0)
                backup_result.bytes_processed = result.get('bytes_processed', 0)
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
                    tags=target_config.get('tags', [])
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
            repository = self._repository_factory.create_repository(repository_uri)

            # Verify backup
            if hasattr(repository, 'verify_backup'):
                return repository.verify_backup(snapshot_id)
            else:
                logger.warning(f"Repository {repository.__class__.__name__} does not support verification")
                return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            raise BackupOrchestratorError(f"Backup verification failed: {e}") from e
