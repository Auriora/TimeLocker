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

"""
CLI Service Integration Layer

This module provides a service layer that integrates the new service-oriented
architecture with the CLI, maintaining backward compatibility while leveraging
modern SOLID principles.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from TimeLocker.interfaces import (
    IRepositoryFactory,
    IConfigurationProvider,
    IBackupOrchestrator,
    BackupResult,
    BackupStatus,
    ConfigurationError
)
from TimeLocker.services import (
    RepositoryFactory,
    ConfigurationService,
    BackupOrchestrator,
    ValidationService
)
from TimeLocker.services.snapshot_service import SnapshotService
from TimeLocker.services.repository_service import RepositoryService
from TimeLocker.utils.performance_monitor import PerformanceMonitor
from TimeLocker.config.configuration_manager import ConfigurationManager, ConfigurationPathResolver
from TimeLocker.backup_target import BackupTarget
from TimeLocker.file_selections import FileSelection, SelectionType

logger = logging.getLogger(__name__)


@dataclass
class CLIBackupRequest:
    """Represents a backup request from the CLI"""
    sources: List[Path]
    repository_uri: str
    password: Optional[str] = None
    target_name: Optional[str] = None
    backup_name: Optional[str] = None
    tags: List[str] = None
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    dry_run: bool = False

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.include_patterns is None:
            self.include_patterns = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []


class CLIServiceManager:
    """
    Service manager for CLI operations that bridges legacy and modern architectures.
    
    This class provides a unified interface for CLI operations while gradually
    migrating from legacy components to the new service-oriented architecture.
    """

    def __init__(self):
        """Initialize CLI service manager with dependency injection"""
        # Initialize modern services
        self._repository_factory = RepositoryFactory()
        self._validation_service = ValidationService()
        self._performance_monitor = PerformanceMonitor()

        # Initialize configuration (hybrid approach for migration)
        self._legacy_config_manager = ConfigurationManager()
        self._config_service = ConfigurationService(
                config_path=self._legacy_config_manager.config_file,
                validation_service=self._validation_service
        )

        # Initialize snapshot service
        self._snapshot_service = SnapshotService(
                validation_service=self._validation_service,
                performance_monitor=self._performance_monitor
        )

        # Initialize repository service
        self._repository_service = RepositoryService(
                validation_service=self._validation_service,
                performance_monitor=self._performance_monitor
        )

        # Initialize backup orchestrator
        self._backup_orchestrator = BackupOrchestrator(
                repository_factory=self._repository_factory,
                configuration_provider=self._config_service
        )

        logger.debug("CLIServiceManager initialized")

    @property
    def repository_factory(self) -> IRepositoryFactory:
        """Get repository factory instance"""
        return self._repository_factory

    @property
    def snapshot_service(self) -> SnapshotService:
        """Get snapshot service instance"""
        return self._snapshot_service

    @property
    def repository_service(self) -> RepositoryService:
        """Get repository service instance"""
        return self._repository_service

    @property
    def configuration_service(self) -> IConfigurationProvider:
        """Get configuration service instance"""
        return self._config_service

    @property
    def backup_orchestrator(self) -> IBackupOrchestrator:
        """Get backup orchestrator instance"""
        return self._backup_orchestrator

    @property
    def legacy_config_manager(self) -> ConfigurationManager:
        """Get legacy configuration manager for backward compatibility"""
        return self._legacy_config_manager

    def resolve_repository_uri(self, repository_input: str) -> str:
        """
        Resolve repository input to URI.
        
        Args:
            repository_input: Repository name or URI
            
        Returns:
            Resolved repository URI
            
        Raises:
            ConfigurationError: If repository cannot be resolved
        """
        # Check if it's already a URI (contains scheme)
        if "://" in repository_input or repository_input.startswith("/"):
            return repository_input

        # Try to resolve as repository name from configuration
        try:
            repositories = self._config_service.get_repositories()
            for repo in repositories:
                if repo['name'] == repository_input:
                    return repo['uri']

            # Fallback to legacy configuration manager
            repo_config = self._legacy_config_manager.get_repository(repository_input)
            return repo_config['uri']

        except Exception:
            # If not found in configuration, treat as local path
            if not repository_input.startswith("file://"):
                return f"file://{repository_input}"
            return repository_input

    def execute_backup_from_cli(self, request: CLIBackupRequest) -> BackupResult:
        """
        Execute backup from CLI request using modern orchestrator.
        
        Args:
            request: CLI backup request
            
        Returns:
            BackupResult with operation details
        """
        try:
            # Resolve repository URI
            repository_uri = self.resolve_repository_uri(request.repository_uri)

            # If using a configured target, get it from configuration
            if request.target_name:
                target_names = [request.target_name]

                # Ensure target exists in configuration
                targets = self._config_service.get_backup_targets()
                if not any(t['name'] == request.target_name for t in targets):
                    # Create temporary target configuration
                    target_config = {
                            'name':             request.target_name,
                            'paths':            [str(p) for p in request.sources],
                            'include_patterns': request.include_patterns,
                            'exclude_patterns': request.exclude_patterns
                    }
                    self._config_service.add_backup_target(target_config)

                return self._backup_orchestrator.execute_backup(
                        repository_name=repository_uri,  # Use URI as name for now
                        target_names=target_names,
                        tags=request.tags,
                        dry_run=request.dry_run
                )
            else:
                # Create ad-hoc backup target
                return self._execute_adhoc_backup(request, repository_uri)

        except Exception as e:
            logger.error(f"CLI backup execution failed: {e}")
            # Return failed result
            return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=request.repository_uri,
                    target_names=[request.target_name or "adhoc"],
                    errors=[str(e)]
            )

    def _execute_adhoc_backup(self, request: CLIBackupRequest, repository_uri: str) -> BackupResult:
        """Execute backup for ad-hoc sources without configured targets"""
        # Create temporary target name
        target_name = request.backup_name or f"cli_backup_{int(time.time())}"

        # Create temporary target configuration
        target_config = {
                'name':             target_name,
                'paths':            [str(p) for p in request.sources],
                'include_patterns': request.include_patterns,
                'exclude_patterns': request.exclude_patterns
        }

        # Add to configuration temporarily
        self._config_service.add_backup_target(target_config)

        try:
            # Execute backup
            return self._backup_orchestrator.execute_backup(
                    repository_name=repository_uri,
                    target_names=[target_name],
                    tags=request.tags,
                    dry_run=request.dry_run
            )
        finally:
            # Clean up temporary target
            self._config_service.remove_backup_target(target_name)

    def verify_backup_integrity(self,
                                repository_input: str,
                                snapshot_id: Optional[str] = None,
                                password: Optional[str] = None) -> bool:
        """
        Verify backup integrity using modern orchestrator.
        
        Args:
            repository_input: Repository name or URI
            snapshot_id: Optional specific snapshot to verify
            password: Optional repository password
            
        Returns:
            True if verification successful
        """
        try:
            repository_uri = self.resolve_repository_uri(repository_input)
            return self._backup_orchestrator.verify_backup_integrity(
                    repository_name=repository_uri,
                    snapshot_id=snapshot_id
            )
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def list_repositories(self) -> List[Dict[str, Any]]:
        """
        List all configured repositories.
        
        Returns:
            List of repository configurations
        """
        try:
            # Try modern configuration service first
            return self._config_service.get_repositories()
        except Exception:
            # Fallback to legacy configuration manager
            legacy_repos = self._legacy_config_manager.list_repositories()
            return [
                    {**repo_config, 'name': name}
                    for name, repo_config in legacy_repos.items()
            ]

    def list_backup_targets(self) -> List[Dict[str, Any]]:
        """
        List all configured backup targets.
        
        Returns:
            List of backup target configurations
        """
        try:
            # Try modern configuration service first
            return self._config_service.get_backup_targets()
        except Exception:
            # Fallback to legacy configuration manager
            legacy_targets = self._legacy_config_manager.list_backup_targets()
            return [
                    {**target_config, 'name': name}
                    for name, target_config in legacy_targets.items()
            ]

    def add_repository(self, name: str, uri: str, description: str = "") -> None:
        """
        Add a new repository configuration.
        
        Args:
            name: Repository name
            uri: Repository URI
            description: Optional description
        """
        repo_config = {
                'name':        name,
                'uri':         uri,
                'description': description,
                'type':        'auto'  # Auto-detect type from URI
        }

        try:
            # Try modern configuration service first
            self._config_service.add_repository(repo_config)
        except Exception:
            # Fallback to legacy configuration manager
            self._legacy_config_manager.add_repository(name, uri, description)

    def add_backup_target(self,
                          name: str,
                          paths: List[str],
                          include_patterns: List[str] = None,
                          exclude_patterns: List[str] = None) -> None:
        """
        Add a new backup target configuration.
        
        Args:
            name: Target name
            paths: List of paths to backup
            include_patterns: Optional include patterns
            exclude_patterns: Optional exclude patterns
        """
        target_config = {
                'name':             name,
                'paths':            paths,
                'include_patterns': include_patterns or [],
                'exclude_patterns': exclude_patterns or []
        }

        try:
            # Try modern configuration service first
            self._config_service.add_backup_target(target_config)
        except Exception:
            # Fallback to legacy configuration manager
            self._legacy_config_manager.add_backup_target(
                    name=name,
                    paths=paths,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns
            )

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
        return self._backup_orchestrator.get_backup_history(repository_name, limit)

    def estimate_backup_size(self,
                             repository_input: str,
                             target_names: List[str]) -> Dict[str, Any]:
        """
        Estimate backup size and duration.
        
        Args:
            repository_input: Repository name or URI
            target_names: Names of backup targets
            
        Returns:
            Dictionary with size and time estimates
        """
        repository_uri = self.resolve_repository_uri(repository_input)
        return self._backup_orchestrator.estimate_backup_size(repository_uri, target_names)


# Global CLI service manager instance
_cli_service_manager: Optional[CLIServiceManager] = None


def get_cli_service_manager() -> CLIServiceManager:
    """
    Get global CLI service manager instance (singleton pattern).
    
    Returns:
        CLIServiceManager instance
    """
    global _cli_service_manager
    if _cli_service_manager is None:
        _cli_service_manager = CLIServiceManager()
    return _cli_service_manager
