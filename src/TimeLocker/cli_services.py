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

from .interfaces import (
    IRepositoryFactory,
    IConfigurationProvider,
    IBackupOrchestrator,
    BackupResult,
    BackupStatus,
    ConfigurationError
)
from .services import (
    RepositoryFactory,
    ConfigurationService,
    BackupOrchestrator,
    ValidationService
)
from .services.snapshot_service import SnapshotService
from .services.repository_service import RepositoryService
from .utils.performance_utils import PerformanceModule
from .config.configuration_module import ConfigurationModule
from .config.configuration_path_resolver import ConfigurationPathResolver
from .backup_target import BackupTarget
from .file_selections import FileSelection, SelectionType

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

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize CLI service manager with dependency injection"""
        import sys
        self._config_dir = Path(config_dir) if config_dir is not None else None
        # Initialize modern services
        self._validation_service = ValidationService()
        self._repository_factory = RepositoryFactory(validation_service=self._validation_service)
        self._performance_module = PerformanceModule()

        # Initialize configuration (new system only)
        self._config_module = ConfigurationModule(config_dir=self._config_dir)

        # Initialize modern config service
        try:
            self._config_service = ConfigurationService(
                    config_path=self._config_module.config_file,
                    validation_service=self._validation_service
            )
        except Exception as e:
            logger.warning(f"Configuration service failed to initialize: {e}")
            self._config_service = None

        # Initialize snapshot service
        self._snapshot_service = SnapshotService(
                validation_service=self._validation_service,
                performance_module=self._performance_module
        )

        # Initialize repository service
        self._repository_service = RepositoryService(
                validation_service=self._validation_service,
                performance_module=self._performance_module
        )
        self._configure_repository_factory_credentials()

        # Initialize backup orchestrator
        self._backup_orchestrator = BackupOrchestrator(
                repository_factory=self._repository_factory,
                configuration_provider=self._config_service
        )

        logger.debug("CLIServiceManager initialized")

    def _configure_repository_factory_credentials(self) -> None:
        """Ensure repository factory uses credential storage aligned with config directory."""
        if self._config_dir is None:
            return
        try:
            from .security.credential_manager import CredentialManager  # lazy import to avoid cycles

            credentials_dir = self._config_dir / "credentials"
            credentials_dir.mkdir(parents=True, exist_ok=True)
            self._repository_factory._credential_manager = CredentialManager(config_dir=credentials_dir)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug("Falling back to default credential manager: %s", exc)

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
    def config_module(self) -> ConfigurationModule:
        """Get configuration module"""
        return self._config_module

    @property
    def config_dir(self) -> Optional[Path]:
        """Return configuration directory used by this manager."""
        return self._config_dir

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
            if self._config_service is not None:
                repositories = self._config_service.get_repositories()
                for repo in repositories:
                    if repo['name'] == repository_input:
                        return repo['uri']

            # Fallback to configuration module
            repo_config = self._config_module.get_repository(repository_input)
            return repo_config.location

        except Exception:
            # If not found in configuration, treat as local path
            if not repository_input.startswith("file://"):
                return f"file://{repository_input}"
            return repository_input

    def _find_repository_name_by_uri(self, repository_uri: str) -> str:
        """
        Find repository name that matches the given URI.

        Args:
            repository_uri: Repository URI to find name for

        Returns:
            Repository name if found, otherwise the URI itself
        """
        try:
            # Try modern config service first
            if self._config_service is not None:
                repositories = self._config_service.get_repositories()
                for repo in repositories:
                    repo_uri = repo.get('uri')
                    if repo_uri == repository_uri:
                        return repo['name']

            # Fallback to configuration module
            config = self._config_module.get_config()
            logger.debug(f"Found {len(config.repositories)} repositories in config module")
            for repo_name, repo_config in config.repositories.items():
                repo_uri = getattr(repo_config, 'uri', None) or getattr(repo_config, 'location', None)
                logger.debug(f"Checking repo '{repo_name}' with URI '{repo_uri}'")
                if repo_uri == repository_uri:
                    logger.debug(f"Found matching repository name: {repo_name}")
                    return repo_name

        except Exception as e:
            logger.debug(f"Could not find repository name for URI {repository_uri}: {e}")

        # If no name found, return the URI itself as fallback
        logger.debug(f"No matching repository found, returning URI as fallback: {repository_uri}")
        return repository_uri

    @staticmethod
    def _looks_like_uri(candidate: str) -> bool:
        """Heuristically determine if candidate string represents a repository URI."""
        if not candidate:
            return False
        if "://" in candidate:
            return True
        prefixes = ("s3:", "b2:", "gs:", "azure:", "rest:", "rclone:", "local:", "minio:", "swift:", "/")
        return candidate.startswith(prefixes)

    def _create_repository_instance(self,
                                    name: Optional[str] = None,
                                    repository: Optional[str] = None,
                                    repository_uri: Optional[str] = None,
                                    password: Optional[str] = None) -> tuple:
        """
        Create repository instance for operations, resolving configuration as needed.

        Returns:
            Tuple of (repository_object, resolved_name, resolved_uri)
        """
        resolved_name = name
        resolved_uri = repository_uri

        candidate = repository
        if resolved_uri is None and candidate:
            if self._looks_like_uri(candidate):
                resolved_uri = candidate
            else:
                resolved_name = candidate

        if resolved_uri is None:
            if not resolved_name:
                raise ConfigurationError("Repository name or URI must be provided")
            repo_info = self.get_repository_by_name(resolved_name)
            if isinstance(repo_info, dict):
                resolved_uri = repo_info.get('uri') or repo_info.get('location')
                if password is None:
                    password = repo_info.get('password')
            else:
                resolved_uri = getattr(repo_info, 'uri', None) or getattr(repo_info, 'location', None)

        if not resolved_uri:
            raise ConfigurationError("Repository URI could not be resolved from configuration")

        if not resolved_name:
            resolved_name = self._find_repository_name_by_uri(resolved_uri)

        repository_instance = self._repository_factory.create_repository(
                resolved_uri,
                password=password,
                repository_name=resolved_name
        )
        return repository_instance, resolved_name, resolved_uri

    def initialize_repository(self,
                              name: str,
                              repository: Optional[str] = None,
                              repository_uri: Optional[str] = None,
                              repository_name: Optional[str] = None,
                              password: Optional[str] = None,
                              **_) -> Dict[str, Any]:
        """Initialize repository (idempotent) and persist password if provided."""
        repo, resolved_name, resolved_uri = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        already_initialized = False
        if hasattr(repo, "is_repository_initialized"):
            try:
                already_initialized = bool(repo.is_repository_initialized())
            except Exception:
                already_initialized = False

        if already_initialized:
            return {"success": True, "already_initialized": True, "uri": resolved_uri}

        if hasattr(repo, "initialize_repository"):
            success = bool(repo.initialize_repository(password))
        else:
            success = bool(repo.initialize())

        if success and password and hasattr(repo, "store_password"):
            try:
                repo.store_password(password)
            except Exception as exc:  # pragma: no cover - best effort storage
                logger.debug("Credential storage after init failed for %s: %s", resolved_name, exc)

        return {"success": success, "already_initialized": already_initialized, "uri": resolved_uri}

    def check_repository(self,
                         name: str,
                         repository: Optional[str] = None,
                         repository_uri: Optional[str] = None,
                         repository_name: Optional[str] = None,
                         password: Optional[str] = None,
                         **_) -> Dict[str, Any]:
        """Run repository integrity check."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.check_repository(repo)

    def get_repository_stats(self,
                             name: str,
                             repository: Optional[str] = None,
                             repository_uri: Optional[str] = None,
                             repository_name: Optional[str] = None,
                             password: Optional[str] = None,
                             **_) -> Dict[str, Any]:
        """Collect repository statistics."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.get_repository_stats(repo)

    def unlock_repository(self,
                          name: str,
                          repository: Optional[str] = None,
                          repository_uri: Optional[str] = None,
                          repository_name: Optional[str] = None,
                          password: Optional[str] = None,
                          **_) -> bool:
        """Remove repository locks."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.unlock_repository(repo)

    def migrate_repository(self,
                           name: str,
                           repository: Optional[str] = None,
                           repository_uri: Optional[str] = None,
                           repository_name: Optional[str] = None,
                           migration: Optional[str] = None,
                           password: Optional[str] = None,
                           **_) -> bool:
        """Execute repository migration."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        migration_name = migration or "upgrade_repo_v2"
        return self._repository_service.migrate_repository(repo, migration_name=migration_name)

    def apply_retention_policy(self,
                               name: str,
                               repository: Optional[str] = None,
                               repository_uri: Optional[str] = None,
                               repository_name: Optional[str] = None,
                               keep_daily: int = 7,
                               keep_weekly: int = 4,
                               keep_monthly: int = 12,
                               keep_yearly: int = 3,
                               dry_run: bool = False,
                               password: Optional[str] = None,
                               **_) -> Dict[str, Any]:
        """Apply forget/retention policy to repository."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.apply_retention_policy(
                repo,
                keep_daily=keep_daily,
                keep_weekly=keep_weekly,
                keep_monthly=keep_monthly,
                keep_yearly=keep_yearly,
                dry_run=dry_run
        )

    def prune_repository(self,
                         name: str,
                         repository: Optional[str] = None,
                         repository_uri: Optional[str] = None,
                         repository_name: Optional[str] = None,
                         password: Optional[str] = None,
                         **_) -> Dict[str, Any]:
        """Prune unreferenced data from repository."""
        repo, _, _ = self._create_repository_instance(
                repository_name or name,
                repository=repository,
                repository_uri=repository_uri,
                password=password
        )
        return self._repository_service.prune_repository(repo)

    def check_all_repositories(self, **_) -> Dict[str, Any]:
        """Run integrity checks for all configured repositories."""
        results: Dict[str, Any] = {}
        overall_success = True
        for repo in self.list_repositories() or []:
            repo_name = repo.get('name') if isinstance(repo, dict) else getattr(repo, 'name', None)
            repo_uri = repo.get('uri') if isinstance(repo, dict) else getattr(repo, 'uri', None)
            if not repo_name:
                repo_name = self._find_repository_name_by_uri(repo_uri or "")
            try:
                check_result = self.check_repository(repo_name, repository=repo_uri, repository_name=repo_name)
                results[repo_name] = check_result
                status = None
                if isinstance(check_result, dict):
                    status = check_result.get('status')
                elif hasattr(check_result, 'success'):
                    status = 'success' if getattr(check_result, 'success', False) else 'failed'
                if status not in (None, 'success', 'ok', True):
                    overall_success = False
            except Exception as exc:
                results[repo_name] = {'status': 'failed', 'errors': [str(exc)]}
                overall_success = False
        return {'success': overall_success, 'results': results}

    def get_all_repository_stats(self, **_) -> List[Dict[str, Any]]:
        """Collect statistics for all configured repositories."""
        stats: List[Dict[str, Any]] = []
        for repo in self.list_repositories() or []:
            repo_name = repo.get('name') if isinstance(repo, dict) else getattr(repo, 'name', None)
            repo_uri = repo.get('uri') if isinstance(repo, dict) else getattr(repo, 'uri', None)
            try:
                repo_stats = self.get_repository_stats(repo_name, repository=repo_uri, repository_name=repo_name)
                if isinstance(repo_stats, dict):
                    repo_stats = {**repo_stats, 'name': repo_name}
                stats.append(repo_stats)
            except Exception as exc:
                stats.append({'name': repo_name, 'error': str(exc)})
        return stats

    def execute_backup_from_cli(self, request: CLIBackupRequest) -> BackupResult:
        """
        Execute backup from CLI request using modern orchestrator.

        Args:
            request: CLI backup request

        Returns:
            BackupResult with operation details
        """
        logger = logging.getLogger(__name__)
        logger.debug(f"execute_backup_from_cli called with repository_uri: {request.repository_uri}")
        logger.debug(f"CLI service received password: {'***' if request.password else 'None'}")
        try:
            # Resolve repository URI
            repository_uri = self.resolve_repository_uri(request.repository_uri)
            logger.debug(f"Resolved repository URI: {repository_uri}")

            # Find repository name that matches this URI
            repository_name = self._find_repository_name_by_uri(repository_uri)
            logger.debug(f"Using repository name for backup: {repository_name}")

            # If using a configured target, get it from configuration
            logger.debug(f"Checking if target_name exists: {request.target_name}")
            if request.target_name:
                logger.debug(f"Target name found: {request.target_name}")
                target_names = [request.target_name]

                # Ensure target exists in configuration
                logger.debug("About to call get_backup_targets()")
                targets = self._config_service.get_backup_targets()
                logger.debug(f"get_backup_targets() returned {len(targets)} targets")

                logger.debug(f"Looking for target '{request.target_name}'")
                logger.debug(f"Available targets: {[t.get('name', 'NO_NAME') for t in targets]}")

                if not any(t['name'] == request.target_name for t in targets):
                    logger.debug(f"Target '{request.target_name}' not found, creating temporary target")
                    # Create temporary target configuration
                    target_config = {
                            'name':             request.target_name,
                            'paths':            [str(p) for p in request.sources],
                            'include_patterns': request.include_patterns,
                            'exclude_patterns': request.exclude_patterns
                    }
                    self._config_service.add_backup_target(target_config)
                else:
                    logger.debug(f"Target '{request.target_name}' found in configuration")

                logger.debug(f"About to call backup orchestrator with repository_name='{repository_name}', target_names={target_names}")

                return self._backup_orchestrator.execute_backup(
                        repository_name=repository_name,
                        target_names=target_names,
                        tags=request.tags,
                        dry_run=request.dry_run,
                        password=request.password
                )
            else:
                # Create ad-hoc backup target
                return self._execute_adhoc_backup(request, repository_uri, repository_name)

        except Exception as e:
            logger.debug(f"Exception caught in CLI service: {e}")
            logger.debug(f"Exception type: {type(e)}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            logger.error(f"CLI backup execution failed: {e}")
            # Return failed result
            return BackupResult(
                    status=BackupStatus.FAILED,
                    repository_name=request.repository_uri,
                    target_names=[request.target_name or "adhoc"],
                    errors=[str(e)]
            )

    def _execute_adhoc_backup(self, request: CLIBackupRequest, repository_uri: str, repository_name: str) -> BackupResult:
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
                    repository_name=repository_name,
                    target_names=[target_name],
                    tags=request.tags,
                    dry_run=request.dry_run,
                    password=request.password
            )
        finally:
            # Clean up temporary target
            self._config_service.remove_backup_target(target_name)

    def verify_backup_integrity(self,
                                repository_input: str,
                                snapshot_id: Optional[str] = None) -> bool:
        """
        Verify backup integrity using modern orchestrator.

        Args:
            repository_input: Repository name or URI
            snapshot_id: Optional specific snapshot to verify

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
            logger.debug(f"Backup verification failed: {e}")  # Use debug instead of error to avoid duplicate error panels
            return False

    def list_repositories(self) -> List[Dict[str, Any]]:
        """
        List all configured repositories.

        Returns:
            List of repository configurations
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_repositories()
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        repos = self._config_module.get_repositories()
        return repos

    def get_repository_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific repository configuration by name.

        Args:
            name: Repository name

        Returns:
            Repository configuration dictionary

        Raises:
            ConfigurationError: If repository is not found
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_repository_by_name(name)
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        try:
            repo_config = self._config_module.get_repository(name)
            # Convert to dictionary format
            if hasattr(repo_config, '__dict__'):
                return {**repo_config.__dict__, 'name': name}
            else:
                return {'name': name, **repo_config}
        except Exception as e:
            raise ConfigurationError(f"Repository '{name}' not found: {e}")

    def list_backup_targets(self) -> List[Dict[str, Any]]:
        """
        List all configured backup targets.

        Returns:
            List of backup target configurations
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_backup_targets()
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        targets = self._config_module.get_backup_targets()
        return targets

    def get_backup_target_by_name(self, name: str) -> Dict[str, Any]:
        """
        Get a specific backup target configuration by name.

        Args:
            name: Backup target name

        Returns:
            Backup target configuration dictionary

        Raises:
            ConfigurationError: If backup target is not found
        """
        if self._config_service is not None:
            try:
                # Try modern configuration service first
                return self._config_service.get_backup_target_by_name(name)
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        try:
            target_config = self._config_module.get_backup_target(name)
            # Convert to dictionary format
            if hasattr(target_config, '__dict__'):
                return {**target_config.__dict__, 'name': name}
            else:
                return {'name': name, **target_config}
        except Exception as e:
            raise ConfigurationError(f"Backup target '{name}' not found: {e}")

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

        if self._config_service is not None:
            try:
                # Try modern configuration service first
                self._config_service.add_repository(repo_config)
                return
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        self._config_module.add_repository(name, uri, description)

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

        if self._config_service is not None:
            try:
                # Try modern configuration service first
                self._config_service.add_backup_target(target_config)
                return
            except Exception:
                # Fallback to configuration module
                pass

        # Use configuration module
        self._config_module.add_backup_target(
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

    def get_repository_service(self) -> RepositoryService:
        """Backward-compatible accessor used by CLI commands expecting a method."""
        return self._repository_service


# Global CLI service manager instance
_cli_service_manager: Optional[CLIServiceManager] = None


def get_cli_service_manager(config_dir: Optional[Path] = None) -> CLIServiceManager:
    """
    Get global CLI service manager instance (singleton pattern).
    
    Returns:
        CLIServiceManager instance
    """
    global _cli_service_manager
    if _cli_service_manager is None:
        _cli_service_manager = CLIServiceManager(config_dir=config_dir)
    else:
        if config_dir is not None:
            desired_dir = Path(config_dir)
            current_dir = _cli_service_manager.config_dir
            if current_dir is None or Path(current_dir) != desired_dir:
                _cli_service_manager = CLIServiceManager(config_dir=desired_dir)
    return _cli_service_manager
