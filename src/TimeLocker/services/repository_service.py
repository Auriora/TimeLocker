"""
Advanced Repository Service for TimeLocker

This service provides high-level repository operations with proper error handling,
validation, and integration with the service-oriented architecture.
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from ..interfaces.repository_service_interface import IRepositoryService
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext
from ..backup_repository import BackupRepository
from ..interfaces.exceptions import TimeLockerInterfaceError, RepositoryFactoryError
from .validation_service import ValidationService
from ..utils.performance_utils import PerformanceModule

logger = logging.getLogger(__name__)


class RepositoryService(IRepositoryService, ServiceInterface):
    """Advanced repository management service"""

    def __init__(self, validation_service: ValidationService, performance_module: PerformanceModule, policy_integration_service=None):
        self.validation_service = validation_service
        self.performance_module = performance_module
        self.policy_integration_service = policy_integration_service
        self._context: Optional[ServiceContext] = None
        self._initialized = False

    # ServiceInterface implementation
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the repository service with the provided context.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to RepositoryService")
                return False
            
            self._context = context
            
            # Initialize any context-dependent components
            logger.info("RepositoryService initialized successfully")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RepositoryService: {e}")
            return False

    def shutdown(self) -> None:
        """
        Shutdown the repository service and clean up resources.
        """
        try:
            # Clean up any resources
            self._context = None
            self._initialized = False
            logger.info("RepositoryService shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during RepositoryService shutdown: {e}")

    def health_check(self) -> bool:
        """
        Check the health status of the repository service.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        try:
            # Check if service is initialized
            if not self._initialized:
                return False
            
            # Check if validation service is available
            if not self.validation_service:
                return False
            
            # Check if performance module is available
            if not self.performance_module:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"RepositoryService health check failed: {e}")
            return False

    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        capabilities = [
            'repository_check',
            'repository_stats',
            'repository_unlock',
            'repository_migration',
            'retention_policy',
            'repository_prune'
        ]
        
        # Add policy enforcement capability if policy integration is available
        if self.policy_integration_service:
            capabilities.append('policy_enforcement')
        
        return capabilities

    def _parse_restic_error(self, error_output: str) -> str:
        """
        Parse restic error output and return user-friendly error message

        Args:
            error_output: Raw error output from restic command

        Returns:
            User-friendly error message
        """
        if not error_output:
            return "Unknown error occurred"

        # Try to parse JSON error messages
        try:
            for line in error_output.strip().split('\n'):
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get('message_type') == 'exit_error':
                            message = data.get('message', '')
                            # Clean up common error messages
                            if 'repository does not exist' in message:
                                return "Repository does not exist at the specified location"
                            elif 'unable to open config file' in message:
                                return "Repository not found or not initialized"
                            elif 'wrong password' in message.lower():
                                return "Invalid repository password"
                            elif 'repository is locked' in message.lower():
                                return "Repository is locked by another process"
                            else:
                                return message
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

        # Fallback to raw error message, but clean it up
        error_lines = error_output.strip().split('\n')
        # Remove empty lines and common prefixes
        cleaned_lines = []
        for line in error_lines:
            line = line.strip()
            if line and not line.startswith('Fatal:'):
                # Remove common prefixes
                if line.startswith('Fatal: '):
                    line = line[7:]
                cleaned_lines.append(line)

        return ' '.join(cleaned_lines) if cleaned_lines else error_output.strip()

    def check_repository(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Check repository integrity
        
        Args:
            repository: Repository to check
            
        Returns:
            Dictionary with check results and statistics
        """
        with self.performance_module.track_operation("check_repository"):
            try:
                # Run restic check command
                cmd = ['restic', '-r', repository.location(), 'check', '--json']

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                check_results = {
                        'status':     'success' if result.returncode == 0 else 'failed',
                        'exit_code':  result.returncode,
                        'errors':     [],
                        'warnings':   [],
                        'statistics': {}
                }

                if result.returncode != 0:
                    # Parse JSON error messages for better user experience
                    error_message = self._parse_restic_error(result.stderr)
                    check_results['errors'].append(error_message)
                    logger.debug(f"Repository check failed: {error_message}")  # Use debug instead of error
                else:
                    # Parse JSON output if available
                    try:
                        if result.stdout:
                            for line in result.stdout.strip().split('\n'):
                                if line.strip():
                                    data = json.loads(line)
                                    if data.get('message_type') == 'status':
                                        check_results['statistics'].update(data)
                    except json.JSONDecodeError:
                        # Fallback to text parsing
                        check_results['output'] = result.stdout

                logger.info(f"Repository check completed with status: {check_results['status']}")
                return check_results

            except RuntimeError as e:
                # Handle command execution errors (from CommandBuilder.run())
                error_message = self._parse_restic_error(str(e))
                logger.debug(f"Repository check failed: {error_message}")  # Use debug instead of error
                return {
                        'status':     'failed',
                        'exit_code':  1,
                        'errors':     [error_message],
                        'warnings':   [],
                        'statistics': {}
                }
            except Exception as e:
                # Handle other unexpected errors
                error_message = f"Unexpected error during repository check: {e}"
                logger.debug(error_message)  # Use debug instead of error
                return {
                        'status':     'failed',
                        'exit_code':  1,
                        'errors':     [error_message],
                        'warnings':   [],
                        'statistics': {}
                }

    def get_repository_stats(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Get detailed repository statistics
        
        Args:
            repository: Repository to analyze
            
        Returns:
            Dictionary with repository statistics
        """
        with self.performance_module.track_operation("get_repository_stats"):
            try:
                # Run restic stats command using repository environment
                cmd = [
                        'restic',
                        'stats',
                        '--repo',
                        repository.uri(),
                        '--json'
                ]

                env = os.environ.copy()
                env.update(repository.to_env())

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode != 0:
                    raise RepositoryFactoryError(f"Failed to get repository stats: {result.stderr}")

                # Parse JSON output
                stats = {}
                try:
                    stats_data = json.loads(result.stdout)
                    stats = {
                            'total_size':        stats_data.get('total_size', 0),
                            'total_file_count':  stats_data.get('total_file_count', 0),
                            'total_blob_count':  stats_data.get('total_blob_count', 0),
                            'snapshots_count':   stats_data.get('snapshots_count', 0),
                            'index_size':        stats_data.get('index_size', 0),
                            'compression_ratio': stats_data.get('compression_ratio', 0.0),
                            'repository_size':   stats_data.get('repository_size', 0)
                    }
                except json.JSONDecodeError:
                    logger.warning("Failed to parse stats JSON output")
                    stats = {'error': 'Failed to parse statistics'}

                # Get additional info from snapshots
                try:
                    snapshots = repository.list_snapshots()
                    if snapshots:
                        stats['snapshot_count'] = len(snapshots)
                        stats['oldest_snapshot'] = min(s.timestamp for s in snapshots)
                        stats['newest_snapshot'] = max(s.timestamp for s in snapshots)

                        # Calculate time span
                        time_span = stats['newest_snapshot'] - stats['oldest_snapshot']
                        stats['time_span_days'] = time_span / 86400  # Convert to days
                except Exception as e:
                    logger.warning(f"Failed to get snapshot statistics: {e}")

                logger.info("Repository statistics retrieved successfully")
                return stats

            except Exception as e:
                logger.error(f"Failed to get repository stats: {e}")
                raise RepositoryFactoryError(f"Failed to get repository stats: {e}")

    def unlock_repository(self, repository: BackupRepository) -> bool:
        """
        Remove locks from repository
        
        Args:
            repository: Repository to unlock
            
        Returns:
            True if successful, False otherwise
        """
        with self.performance_module.track_operation("unlock_repository"):
            try:
                # Run restic unlock command
                cmd = ['restic', '-r', repository.location(), 'unlock']

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode == 0:
                    logger.info("Repository unlocked successfully")
                    return True
                else:
                    logger.error(f"Failed to unlock repository: {result.stderr}")
                    return False

            except Exception as e:
                logger.error(f"Failed to unlock repository: {e}")
                return False

    def list_available_migrations(self, repository: BackupRepository) -> List[str]:
        """
        List available migrations for repository

        Args:
            repository: Repository to check

        Returns:
            List of available migration names
        """
        with self.performance_module.track_operation("list_available_migrations"):
            try:
                # Run restic migrate command without arguments to list available migrations
                cmd = ['restic', '-r', repository.location(), 'migrate']

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                migrations = []
                if result.returncode == 0:
                    # Parse output to extract migration names
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        # Look for migration names (typically start with lowercase letters)
                        if line and not line.startswith('available migrations:') and not line.startswith('apply'):
                            # Extract migration name from lines like "  upgrade_repo_v2"
                            if line.startswith('  ') and line.strip():
                                migrations.append(line.strip())

                return migrations

            except Exception as e:
                logger.error(f"Failed to list available migrations: {e}")
                return []

    def migrate_repository(self, repository: BackupRepository, migration_name: str = "upgrade_repo_v2") -> bool:
        """
        Migrate repository format

        Args:
            repository: Repository to migrate
            migration_name: Name of migration to apply (default: upgrade_repo_v2)

        Returns:
            True if successful, False otherwise
        """
        with self.performance_module.track_operation("migrate_repository"):
            try:
                # Run restic migrate command
                cmd = ['restic', '-r', repository.location(), 'migrate', migration_name]

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                if result.returncode == 0:
                    logger.info(f"Repository migrated successfully using '{migration_name}'")
                    return True
                else:
                    logger.error(f"Failed to migrate repository: {result.stderr}")
                    return False

            except Exception as e:
                logger.error(f"Failed to migrate repository: {e}")
                return False

    def apply_retention_policy(self, repository: BackupRepository,
                               keep_daily: int = 7, keep_weekly: int = 4,
                               keep_monthly: int = 12, keep_yearly: int = 3,
                               dry_run: bool = False,
                               group_by: str = "host,paths") -> Dict[str, Any]:
        """
        Apply retention policy to repository
        
        Args:
            repository: Repository to apply policy to
            keep_daily: Number of daily snapshots to keep
            keep_weekly: Number of weekly snapshots to keep
            keep_monthly: Number of monthly snapshots to keep
            keep_yearly: Number of yearly snapshots to keep
            dry_run: If True, only show what would be removed
            group_by: Explicit Restic snapshot grouping fields
            
        Returns:
            Dictionary with policy application results
        """
        with self.performance_module.track_operation("apply_retention_policy"):
            try:
                # Build restic forget command
                cmd = ['restic', '-r', repository.location(), 'forget', '--json']
                cmd.extend(['--keep-daily', str(keep_daily)])
                cmd.extend(['--keep-weekly', str(keep_weekly)])
                cmd.extend(['--keep-monthly', str(keep_monthly)])
                cmd.extend(['--keep-yearly', str(keep_yearly)])
                grouping = [item.strip() for item in group_by.split(',')]
                if (
                    not grouping
                    or any(item not in {"host", "paths", "tags"} for item in grouping)
                    or len(grouping) != len(set(grouping))
                ):
                    raise ValueError("group_by contains unsupported grouping fields")
                cmd.extend(['--group-by', ','.join(grouping)])

                if dry_run:
                    cmd.append('--dry-run')

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                policy_results = {
                        'status':            'success' if result.returncode == 0 else 'failed',
                        'dry_run':           dry_run,
                        'removed_snapshots': [],
                        'kept_snapshots':    [],
                        'errors':            []
                }

                if result.returncode != 0:
                    policy_results['errors'].append(result.stderr)
                    logger.error(f"Retention policy application failed: {result.stderr}")
                else:
                    # Parse JSON output
                    try:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                data = json.loads(line)
                                groups = data if isinstance(data, list) else [data]
                                for group in groups:
                                    if not isinstance(group, dict):
                                        continue
                                    if 'remove' in group:
                                        policy_results['removed_snapshots'].extend(group['remove'])
                                    if 'keep' in group:
                                        policy_results['kept_snapshots'].extend(group['keep'])
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse retention policy JSON output")
                        policy_results['output'] = result.stdout

                logger.info(f"Retention policy applied: {len(policy_results['removed_snapshots'])} snapshots marked for removal")
                return policy_results

            except Exception as e:
                logger.error(f"Failed to apply retention policy: {e}")
                raise RepositoryFactoryError(f"Failed to apply retention policy: {e}")

    def prune_repository(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Prune unused data from repository
        
        Args:
            repository: Repository to prune
            
        Returns:
            Dictionary with prune results
        """
        with self.performance_module.track_operation("prune_repository"):
            try:
                # Run restic prune command
                cmd = ['restic', '-r', repository.location(), 'prune', '--json']

                # Set environment for repository access
                env = os.environ.copy()
                if hasattr(repository, 'password'):
                    password = repository.password()
                    if password:
                        env['RESTIC_PASSWORD'] = password

                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                prune_results = {
                        'status':        'success' if result.returncode == 0 else 'failed',
                        'space_freed':   0,
                        'blobs_removed': 0,
                        'errors':        []
                }

                if result.returncode != 0:
                    prune_results['errors'].append(result.stderr)
                    logger.error(f"Repository prune failed: {result.stderr}")
                else:
                    # Parse JSON output
                    try:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                data = json.loads(line)
                                if 'bytes_freed' in data:
                                    prune_results['space_freed'] = data['bytes_freed']
                                if 'blobs_removed' in data:
                                    prune_results['blobs_removed'] = data['blobs_removed']
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse prune JSON output")
                        prune_results['output'] = result.stdout

                logger.info(f"Repository pruned: {prune_results['space_freed']} bytes freed")
                return prune_results

            except Exception as e:
                logger.error(f"Failed to prune repository: {e}")
                raise RepositoryFactoryError(f"Failed to prune repository: {e}")

    def enforce_policy(self, repository: BackupRepository, policy_id: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Enforce retention policy on repository using policy management system
        
        Args:
            repository: Repository to enforce policy on
            policy_id: Optional specific policy ID (otherwise uses assigned policy)
            dry_run: If True, simulate without actually removing snapshots
            
        Returns:
            Dictionary with enforcement results
        """
        with self.performance_module.track_operation("enforce_policy"):
            try:
                if not self.policy_integration_service:
                    raise RepositoryFactoryError(
                        "Policy enforcement not available: policy integration service not configured"
                    )
                
                logger.info(
                    f"{'[DRY RUN] ' if dry_run else ''}Enforcing policy on repository "
                    f"'{repository.name}'"
                )
                
                # Delegate to policy integration service
                result = self.policy_integration_service.enforce_retention_policy_on_repository(
                    repository=repository,
                    policy_id=policy_id,
                    dry_run=dry_run,
                )
                
                logger.info(
                    f"Policy enforcement completed on repository '{repository.name}': "
                    f"{result.get('snapshots_removed', 0)} snapshots removed"
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to enforce policy on repository: {e}")
                raise RepositoryFactoryError(f"Failed to enforce policy: {e}")
