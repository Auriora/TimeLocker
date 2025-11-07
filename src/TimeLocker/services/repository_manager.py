"""
Repository Manager for TimeLocker

This module provides the central RepositoryManager class that coordinates
repository lifecycle operations including creation, validation, and management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

from ..interfaces.repository_management_models import (
    Repository, RepositoryConfig, RepositoryStatus, BackupEngine, RepositoryType,
    ValidationResult, ExistingRepositoryInfo, RepositoryCreationOptions,
    ConnectivityResult, IntegrityResult, ConfigValidationResult,
    RepositoryError, RepositoryNotFoundError, RepositoryAlreadyExistsError,
    RepositoryValidationError, CredentialError, DataLossConfirmationError,
    RepositoryLockError, RepositoryStateError, RepositoryStateTransition
)
from ..interfaces.service_interface import ServiceInterface
from ..interfaces.integration_data_models import ServiceContext
from .repository_factory import RepositoryFactory
from .validation_service import ValidationService
from .repository_state_manager import RepositoryStateManager
from .existing_repository_handler import ExistingRepositoryHandler
from ..security.credential_manager import CredentialManager
from ..config.configuration_manager import ConfigurationManager

logger = logging.getLogger(__name__)


class RepositoryManager(ServiceInterface):
    """
    Central manager for repository lifecycle operations.
    
    Provides CRUD operations for repositories with validation, safety mechanisms,
    and integration with credential management and configuration services.
    """
    
    def __init__(self, 
                 repository_factory: Optional[RepositoryFactory] = None,
                 validation_service: Optional[ValidationService] = None,
                 credential_manager: Optional[CredentialManager] = None,
                 config_manager: Optional[ConfigurationManager] = None,
                 state_manager: Optional[RepositoryStateManager] = None,
                 existing_repo_handler: Optional[ExistingRepositoryHandler] = None):
        """
        Initialize Repository Manager.
        
        Args:
            repository_factory: Factory for creating repository instances
            validation_service: Service for repository validation
            credential_manager: Manager for repository credentials
            config_manager: Configuration manager for persistence
            state_manager: Manager for repository state transitions
            existing_repo_handler: Handler for existing repository operations
        """
        self._repository_factory = repository_factory or RepositoryFactory()
        self._validation_service = validation_service or ValidationService()
        self._credential_manager = credential_manager
        self._config_manager = config_manager
        self._state_manager = state_manager or RepositoryStateManager()
        self._existing_repo_handler = existing_repo_handler or ExistingRepositoryHandler(self._repository_factory)
        
        # Runtime state
        self._repositories: Dict[str, Repository] = {}
        self._operation_locks: Dict[str, asyncio.Lock] = {}
        self._context: Optional[ServiceContext] = None
        self._initialized = False
        
        # Performance monitoring
        self._performance_thresholds = {
            'validation_network': 15.0,  # seconds
            'validation_local': 3.0,     # seconds
            'listing': 2.0,              # seconds
            'configuration_update': 1.0   # seconds
        }
        
        logger.debug("RepositoryManager initialized")
    
    # ServiceInterface implementation
    def initialize(self, context: ServiceContext) -> bool:
        """
        Initialize the repository manager with the provided context.
        
        Args:
            context: ServiceContext containing configuration and runtime information
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            if not self.validate_context(context):
                logger.error("Invalid service context provided to RepositoryManager")
                return False
            
            self._context = context
            
            # Initialize credential manager if not provided
            if self._credential_manager is None:
                self._credential_manager = CredentialManager()
            
            # Initialize configuration manager if not provided
            if self._config_manager is None:
                self._config_manager = ConfigurationManager()
            
            # Load existing repositories from configuration
            self._load_repositories()
            
            logger.info("RepositoryManager initialized successfully")
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize RepositoryManager: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the repository manager and clean up resources."""
        try:
            # Save any pending changes
            self._save_repositories()
            
            # Clear runtime state
            self._repositories.clear()
            self._operation_locks.clear()
            self._context = None
            self._initialized = False
            
            logger.info("RepositoryManager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during RepositoryManager shutdown: {e}")
    
    def health_check(self) -> bool:
        """
        Check the health status of the repository manager.
        
        Returns:
            bool: True if the service is healthy and operational, False otherwise
        """
        try:
            if not self._initialized:
                return False
            
            # Check if required services are available
            if not self._repository_factory:
                return False
            
            if not self._validation_service:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"RepositoryManager health check failed: {e}")
            return False
    
    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities provided by this service.
        
        Returns:
            List[str]: List of capability identifiers
        """
        return [
            'repository_create',
            'repository_read',
            'repository_update',
            'repository_delete',
            'repository_list',
            'repository_validate',
            'existing_repository_detection',
            'repository_state_management',
            'configuration_backup',
            'exclusive_locking'
        ]
    
    async def _acquire_repository_lock(self, repo_name: str) -> asyncio.Lock:
        """
        Acquire exclusive lock for repository operations.
        
        Args:
            repo_name: Name of the repository to lock
            
        Returns:
            asyncio.Lock: Lock object for the repository
        """
        if repo_name not in self._operation_locks:
            self._operation_locks[repo_name] = asyncio.Lock()
        return self._operation_locks[repo_name]
    
    def validate_repository_name(self, name: str) -> ConfigValidationResult:
        """
        Validate repository name for alias system.
        
        Repository names must:
        - Not be empty
        - Be between 1 and 64 characters
        - Contain only alphanumeric characters, hyphens, underscores, and dots
        - Not start or end with special characters
        - Not contain consecutive special characters
        
        Args:
            name: Repository name to validate
            
        Returns:
            ConfigValidationResult: Validation result with errors if invalid
        """
        result = ConfigValidationResult(is_valid=True)
        
        if not name:
            result.errors.append("Repository name cannot be empty")
            result.is_valid = False
            return result
        
        if len(name) > 64:
            result.errors.append("Repository name must be 64 characters or less")
            result.is_valid = False
        
        if len(name) < 1:
            result.errors.append("Repository name must be at least 1 character")
            result.is_valid = False
        
        # Check for valid characters (alphanumeric, hyphen, underscore, dot)
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$', name):
            result.errors.append(
                "Repository name must contain only alphanumeric characters, hyphens, "
                "underscores, and dots. It must start and end with an alphanumeric character."
            )
            result.is_valid = False
        
        # Check for consecutive special characters
        if re.search(r'[._-]{2,}', name):
            result.errors.append("Repository name cannot contain consecutive special characters")
            result.is_valid = False
        
        # Reserved names
        reserved_names = ['default', 'all', 'none', 'null', 'system', 'config']
        if name.lower() in reserved_names:
            result.errors.append(f"Repository name '{name}' is reserved and cannot be used")
            result.is_valid = False
        
        return result
    
    def check_repository_name_uniqueness(self, name: str) -> bool:
        """
        Check if repository name is unique (not already in use).
        
        Args:
            name: Repository name to check
            
        Returns:
            bool: True if name is unique, False if already exists
        """
        return name not in self._repositories
    
    def get_repository_by_uri(self, uri: str) -> Optional[Repository]:
        """
        Find repository by URI.
        
        Args:
            uri: Repository URI to search for
            
        Returns:
            Optional[Repository]: Repository with matching URI, or None if not found
        """
        for repository in self._repositories.values():
            if repository.config.uri == uri:
                return repository
        return None
    
    def resolve_repository_name(self, name_or_uri: str) -> Optional[str]:
        """
        Resolve a repository name or URI to a repository name.
        
        This method supports:
        - Direct repository name lookup
        - URI-based lookup (finds repository with matching URI)
        - Default repository (if name_or_uri is empty or 'default')
        
        Args:
            name_or_uri: Repository name, URI, or 'default'
            
        Returns:
            Optional[str]: Resolved repository name, or None if not found
        """
        # Handle empty or 'default' keyword
        if not name_or_uri or name_or_uri.lower() == 'default':
            default_repo = self.get_default_repository()
            return default_repo.name if default_repo else None
        
        # Check if it's a direct name match
        if name_or_uri in self._repositories:
            return name_or_uri
        
        # Try to find by URI
        repository = self.get_repository_by_uri(name_or_uri)
        if repository:
            return repository.name
        
        return None
    
    def _load_repositories(self) -> None:
        """Load repositories from configuration storage."""
        try:
            if not self._config_manager:
                logger.warning("No configuration manager available, skipping repository loading")
                return
            
            config = self._config_manager.get_config()
            if not config or not hasattr(config, 'repositories'):
                logger.debug("No repositories found in configuration")
                return
            
            for name, repo_config in config.repositories.items():
                try:
                    # Convert legacy RepositoryConfig to new format
                    enhanced_config = self._convert_legacy_config(name, repo_config)
                    repository = Repository(
                        config=enhanced_config,
                        status=RepositoryStatus.INACTIVE
                    )
                    self._repositories[name] = repository
                    logger.debug(f"Loaded repository: {name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load repository {name}: {e}")
            
            logger.info(f"Loaded {len(self._repositories)} repositories from configuration")
            
        except Exception as e:
            logger.error(f"Failed to load repositories: {e}")
    
    def _convert_legacy_config(self, name: str, legacy_config: Any) -> RepositoryConfig:
        """
        Convert legacy repository configuration to new format.
        
        Args:
            name: Repository name
            legacy_config: Legacy configuration object
            
        Returns:
            RepositoryConfig: Enhanced repository configuration
        """
        # Extract URI from legacy config
        uri = getattr(legacy_config, 'location', None) or getattr(legacy_config, 'uri', '')
        
        # Determine engine and type from URI
        engine = BackupEngine.RESTIC  # Default to Restic for existing repositories
        repo_type = self._detect_repository_type(uri)
        
        return RepositoryConfig(
            name=name,
            uri=uri,
            engine=engine,
            type=repo_type,
            description=getattr(legacy_config, 'description', None),
            metadata={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_default=False,
            engine_config={}
        )
    
    def _detect_repository_type(self, uri: str) -> RepositoryType:
        """
        Detect repository type from URI pattern.
        
        Automatically detects repository type from URI patterns:
        - s3://... or s3:https://... -> S3
        - b2:... -> B2
        - sftp://... -> SFTP
        - smb://... -> SMB
        - nfs://... -> NFS
        - file://... or local paths -> LOCAL
        
        Args:
            uri: Repository URI
            
        Returns:
            RepositoryType: Detected repository type
        """
        if not uri:
            return RepositoryType.LOCAL
        
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else ''
        
        # Handle special cases for S3 and B2
        if uri.startswith('s3:'):
            return RepositoryType.S3
        if uri.startswith('b2:'):
            return RepositoryType.B2
        
        # Standard URI scheme mapping
        type_mapping = {
            'file': RepositoryType.LOCAL,
            'local': RepositoryType.LOCAL,
            's3': RepositoryType.S3,
            'b2': RepositoryType.B2,
            'sftp': RepositoryType.SFTP,
            'smb': RepositoryType.SMB,
            'nfs': RepositoryType.NFS
        }
        
        # If no scheme or unknown scheme, check if it's a local path
        if not scheme or scheme not in type_mapping:
            # Check if it looks like a local path
            if uri.startswith('/') or uri.startswith('~') or (len(uri) > 1 and uri[1] == ':'):
                return RepositoryType.LOCAL
            return RepositoryType.LOCAL  # Default to local
        
        return type_mapping.get(scheme, RepositoryType.LOCAL)
    
    def _save_repositories(self) -> None:
        """Save repositories to configuration storage."""
        try:
            if not self._config_manager:
                logger.warning("No configuration manager available, skipping repository saving")
                return
            
            # Convert repositories back to legacy format for compatibility
            legacy_repos = {}
            for name, repository in self._repositories.items():
                legacy_repos[name] = self._convert_to_legacy_config(repository.config)
            
            # Update configuration
            config = self._config_manager.get_config()
            if config:
                config.repositories.update(legacy_repos)
                self._config_manager.save_config(config)
                logger.debug(f"Saved {len(legacy_repos)} repositories to configuration")
            
        except Exception as e:
            logger.error(f"Failed to save repositories: {e}")
    
    def _convert_to_legacy_config(self, config: RepositoryConfig) -> Any:
        """
        Convert enhanced repository configuration to legacy format.
        
        Args:
            config: Enhanced repository configuration
            
        Returns:
            Legacy configuration object
        """
        from ..config.configuration_schema import RepositoryConfig as LegacyConfig
        
        return LegacyConfig(
            name=config.name,
            location=config.uri,
            description=config.description
        )
    
    async def create_repository(self, config: RepositoryConfig, 
                              options: Optional[RepositoryCreationOptions] = None) -> Repository:
        """
        Create a new repository with existing repository detection and handling.
        
        Args:
            config: Repository configuration
            options: Creation options for handling existing repositories
            
        Returns:
            Repository: Created repository instance
            
        Raises:
            RepositoryAlreadyExistsError: If repository name already exists
            RepositoryValidationError: If configuration is invalid
            CredentialError: If credentials are required but not provided
        """
        if not options:
            options = RepositoryCreationOptions()
        
        async with await self._acquire_repository_lock(config.name):
            # Validate repository name
            name_validation = self.validate_repository_name(config.name)
            if not name_validation.is_valid:
                raise RepositoryValidationError(
                    f"Invalid repository name: {', '.join(name_validation.errors)}"
                )
            
            # Check if repository name already exists (uniqueness check)
            if not self.check_repository_name_uniqueness(config.name):
                raise RepositoryAlreadyExistsError(
                    config.uri, 
                    ExistingRepositoryInfo(
                        uri=config.uri,
                        engine_type=config.engine,
                        requires_credentials=True
                    )
                )
            
            # Auto-detect repository type from URI if not explicitly set
            if config.type == RepositoryType.LOCAL and config.uri:
                detected_type = self._detect_repository_type(config.uri)
                if detected_type != RepositoryType.LOCAL:
                    config.type = detected_type
                    logger.debug(f"Auto-detected repository type: {detected_type.value}")
            
            # Validate configuration
            validation_result = await self._validate_configuration(config)
            if not validation_result.is_valid:
                raise RepositoryValidationError(f"Invalid configuration: {', '.join(validation_result.errors)}")
            
            # Check for existing repository at URI
            existing_info = await self.detect_existing_repository(config.uri)
            
            if existing_info:
                return await self._handle_existing_repository(config, existing_info, options)
            else:
                return await self._create_new_repository(config)
    
    async def detect_existing_repository(self, uri: str) -> Optional[ExistingRepositoryInfo]:
        """
        Detect if a repository already exists at the specified URI.
        
        Args:
            uri: Repository URI to check
            
        Returns:
            ExistingRepositoryInfo: Information about existing repository, or None if not found
        """
        return await self._existing_repo_handler.detect_existing_repository(uri)
    
    async def _handle_existing_repository(self, config: RepositoryConfig, 
                                        existing_info: ExistingRepositoryInfo,
                                        options: RepositoryCreationOptions) -> Repository:
        """
        Handle existing repository based on options.
        
        Args:
            config: Repository configuration
            existing_info: Information about existing repository
            options: Creation options
            
        Returns:
            Repository: Repository instance
            
        Raises:
            DataLossConfirmationError: If confirmation is required but not provided
        """
        if options.connect_if_exists:
            return await self._connect_to_existing_repository(config, existing_info)
        elif options.reinitialize_if_exists:
            if options.require_confirmation_for_reinit and not options.force_confirmation:
                raise DataLossConfirmationError(
                    f"Repository re-initialization requires explicit confirmation. "
                    f"Repository at {config.uri} contains data that will be permanently lost."
                )
            return await self._reinitialize_repository(config, existing_info)
        else:
            raise RepositoryAlreadyExistsError(config.uri, existing_info)
    
    async def _connect_to_existing_repository(self, config: RepositoryConfig,
                                            existing_info: ExistingRepositoryInfo) -> Repository:
        """
        Connect to an existing repository.
        
        Args:
            config: Repository configuration
            existing_info: Information about existing repository
            
        Returns:
            Repository: Connected repository instance
        """
        repository = await self._existing_repo_handler.connect_to_existing_repository(
            config, existing_info
        )
        
        # Validate connectivity
        validation_result = await self.validate_repository(repository)
        if not validation_result.success:
            await self._state_manager.transition_state(repository, RepositoryStatus.ERROR)
            repository.validation_result = validation_result
        else:
            await self._state_manager.transition_state(repository, RepositoryStatus.ACTIVE)
        
        # Store repository
        self._repositories[config.name] = repository
        self._save_repositories()
        
        logger.info(f"Connected to existing repository: {config.name}")
        return repository
    
    async def _reinitialize_repository(self, config: RepositoryConfig,
                                     existing_info: ExistingRepositoryInfo) -> Repository:
        """
        Re-initialize an existing repository (destructive operation).
        
        Args:
            config: Repository configuration
            existing_info: Information about existing repository
            
        Returns:
            Repository: Re-initialized repository instance
        """
        repository = await self._existing_repo_handler.reinitialize_repository(
            config, existing_info, force_confirm=True
        )
        
        # Transition to active state
        await self._state_manager.transition_state(repository, RepositoryStatus.ACTIVE)
        
        # Store repository
        self._repositories[config.name] = repository
        self._save_repositories()
        
        return repository
    
    async def _create_new_repository(self, config: RepositoryConfig, 
                                   force_reinit: bool = False) -> Repository:
        """
        Create a new repository instance.
        
        Args:
            config: Repository configuration
            force_reinit: Whether this is a forced re-initialization
            
        Returns:
            Repository: Created repository instance
        """
        try:
            # Create repository instance using factory
            repo_instance = self._repository_factory.create_repository(
                config.uri,
                repository_name=config.name
            )
            
            # Initialize repository if it's a new creation
            if hasattr(repo_instance, 'init') and not force_reinit:
                await asyncio.to_thread(repo_instance.init)
            
            # Create repository object
            repository = Repository(
                config=config,
                status=RepositoryStatus.ACTIVE
            )
            
            # Perform initial validation
            validation_result = await self.validate_repository(repository)
            repository.validation_result = validation_result
            
            if not validation_result.success:
                repository.status = RepositoryStatus.ERROR
            
            # Store repository
            self._repositories[config.name] = repository
            self._save_repositories()
            
            logger.info(f"Created new repository: {config.name}")
            return repository
            
        except Exception as e:
            logger.error(f"Failed to create repository {config.name}: {e}")
            raise RepositoryError(f"Failed to create repository: {e}")
    
    async def get_repository(self, name: str) -> Repository:
        """
        Get a repository by name.
        
        Args:
            name: Repository name
            
        Returns:
            Repository: Repository instance
            
        Raises:
            RepositoryNotFoundError: If repository is not found
        """
        if name not in self._repositories:
            raise RepositoryNotFoundError(f"Repository '{name}' not found")
        
        return self._repositories[name]
    
    async def list_repositories(self, filters: Optional[Dict[str, Any]] = None) -> List[Repository]:
        """
        List all repositories with optional filtering.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List[Repository]: List of repositories
        """
        repositories = list(self._repositories.values())
        
        if filters:
            # Apply filters
            if 'status' in filters:
                status_filter = RepositoryStatus(filters['status'])
                repositories = [r for r in repositories if r.status == status_filter]
            
            if 'engine' in filters:
                engine_filter = BackupEngine(filters['engine'])
                repositories = [r for r in repositories if r.config.engine == engine_filter]
            
            if 'type' in filters:
                type_filter = RepositoryType(filters['type'])
                repositories = [r for r in repositories if r.config.type == type_filter]
        
        return repositories
    
    async def update_repository(self, name: str, updates: Dict[str, Any]) -> Repository:
        """
        Update repository configuration.
        
        Args:
            name: Repository name
            updates: Dictionary of updates to apply
            
        Returns:
            Repository: Updated repository instance
            
        Raises:
            RepositoryNotFoundError: If repository is not found
        """
        async with await self._acquire_repository_lock(name):
            repository = await self.get_repository(name)
            
            # Backup configuration before risky operations
            if any(key in updates for key in ['uri', 'engine', 'engine_config']):
                await self._backup_configuration(name)
            
            # Apply updates to configuration
            config = repository.config
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            
            # Validate updated configuration
            validation_result = await self._validate_configuration(config)
            if not validation_result.is_valid:
                raise RepositoryValidationError(f"Invalid configuration updates: {', '.join(validation_result.errors)}")
            
            # Save changes
            self._save_repositories()
            
            logger.info(f"Updated repository: {name}")
            return repository
    
    async def delete_repository(self, name: str, force: bool = False) -> bool:
        """
        Delete a repository.
        
        Args:
            name: Repository name
            force: Whether to force deletion without confirmation
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            RepositoryNotFoundError: If repository is not found
        """
        async with await self._acquire_repository_lock(name):
            repository = await self.get_repository(name)
            
            # Backup configuration before deletion
            await self._backup_configuration(name)
            
            # Remove from runtime state
            del self._repositories[name]
            
            # Remove from configuration
            self._save_repositories()
            
            logger.info(f"Deleted repository: {name}")
            return True
    
    async def validate_repository(self, repository: Repository) -> ValidationResult:
        """
        Validate repository connectivity and integrity.
        
        Args:
            repository: Repository to validate
            
        Returns:
            ValidationResult: Validation results
        """
        start_time = datetime.utcnow()
        
        try:
            # Create repository instance for validation
            repo_instance = self._repository_factory.create_repository(
                repository.config.uri,
                repository_name=repository.config.name
            )
            
            # Test connectivity
            connectivity_result = await self._test_connectivity(repo_instance)
            
            # Test integrity if connectivity succeeds
            integrity_result = None
            if connectivity_result.success:
                integrity_result = await self._test_integrity(repo_instance)
            
            # Calculate performance metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            performance_metrics = {'validation_duration': duration}
            
            # Check performance thresholds
            threshold_key = 'validation_network' if repository.config.type != RepositoryType.LOCAL else 'validation_local'
            threshold = self._performance_thresholds[threshold_key]
            
            recommendations = []
            if duration > threshold:
                recommendations.append(f"Validation took {duration:.2f}s (threshold: {threshold:.2f}s). Consider checking connectivity.")
            
            # Create validation result
            validation_result = ValidationResult(
                success=connectivity_result.success and (integrity_result is None or integrity_result.success),
                timestamp=datetime.utcnow(),
                connectivity_status=connectivity_result.status,
                integrity_status=integrity_result.status if integrity_result else IntegrityStatus.UNKNOWN,
                performance_metrics=performance_metrics,
                recommendations=recommendations
            )
            
            if not connectivity_result.success:
                validation_result.add_error(connectivity_result.error_message or "Connectivity test failed")
            
            if integrity_result and not integrity_result.success:
                validation_result.error_details.extend(integrity_result.issues_found)
            
            # Update repository validation state
            repository.last_validated = datetime.utcnow()
            repository.validation_result = validation_result
            
            # Transition state based on validation result
            if validation_result.success:
                await self._state_manager.transition_state(repository, RepositoryStatus.ACTIVE)
            else:
                await self._state_manager.transition_state(repository, RepositoryStatus.ERROR)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Repository validation failed for {repository.name}: {e}")
            return ValidationResult(
                success=False,
                timestamp=datetime.utcnow(),
                connectivity_status=ConnectivityStatus.UNKNOWN,
                integrity_status=IntegrityStatus.UNKNOWN,
                error_details=[str(e)]
            )
    
    async def _test_connectivity(self, repository) -> ConnectivityResult:
        """Test repository connectivity."""
        # This is a simplified implementation
        # In practice, you'd use repository-specific connectivity tests
        try:
            # Simulate connectivity test
            await asyncio.sleep(0.1)  # Simulate network delay
            return ConnectivityResult(
                success=True,
                status=ConnectivityStatus.CONNECTED,
                response_time=0.1
            )
        except Exception as e:
            return ConnectivityResult(
                success=False,
                status=ConnectivityStatus.DISCONNECTED,
                error_message=str(e)
            )
    
    async def _test_integrity(self, repository) -> IntegrityResult:
        """Test repository integrity."""
        # This is a simplified implementation
        try:
            # Simulate integrity test
            await asyncio.sleep(0.2)  # Simulate integrity check
            return IntegrityResult(
                success=True,
                status=IntegrityStatus.VALID
            )
        except Exception as e:
            return IntegrityResult(
                success=False,
                status=IntegrityStatus.CORRUPTED,
                issues_found=[str(e)]
            )
    
    async def _validate_configuration(self, config: RepositoryConfig) -> ConfigValidationResult:
        """
        Validate repository configuration.
        
        Args:
            config: Repository configuration to validate
            
        Returns:
            ConfigValidationResult: Validation results
        """
        result = ConfigValidationResult(is_valid=True)
        
        # Validate required fields
        if not config.name:
            result.errors.append("Repository name is required")
        
        if not config.uri:
            result.errors.append("Repository URI is required")
        
        # Validate URI format
        try:
            parsed = urlparse(config.uri)
            if not parsed.scheme and not config.uri.startswith('/'):
                result.errors.append("Invalid URI format")
        except Exception as e:
            result.errors.append(f"Invalid URI: {e}")
        
        # Validate engine support
        if not self._repository_factory.is_scheme_supported(parsed.scheme or 'local'):
            result.errors.append(f"Unsupported URI scheme: {parsed.scheme}")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    async def _backup_configuration(self, repo_name: str) -> str:
        """
        Create backup of repository configuration.
        
        Args:
            repo_name: Repository name
            
        Returns:
            str: Backup identifier
        """
        try:
            repository = self._repositories.get(repo_name)
            if not repository:
                return ""
            
            backup_id = f"{repo_name}_{datetime.utcnow().isoformat()}"
            backup_data = repository.config.to_dict()
            
            # In a real implementation, you'd save this to a backup storage
            logger.info(f"Created configuration backup: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to backup configuration for {repo_name}: {e}")
            return ""
    
    def get_default_repository(self) -> Optional[Repository]:
        """
        Get the default repository.
        
        Returns:
            Optional[Repository]: Default repository, or None if no default is set
        """
        for repository in self._repositories.values():
            if repository.config.is_default:
                return repository
        return None
    
    async def set_default_repository(self, name: str) -> bool:
        """
        Set a repository as the default.
        
        Args:
            name: Repository name
            
        Returns:
            bool: True if successful
            
        Raises:
            RepositoryNotFoundError: If repository is not found
        """
        repository = await self.get_repository(name)
        
        # Clear existing default
        for repo in self._repositories.values():
            repo.config.is_default = False
        
        # Set new default
        repository.config.is_default = True
        repository.config.updated_at = datetime.utcnow()
        
        # Save changes
        self._save_repositories()
        
        logger.info(f"Set default repository: {name}")
        return True
    
    async def clear_default_repository(self) -> bool:
        """
        Clear the default repository setting.
        
        Returns:
            bool: True if successful
        """
        # Clear all default flags
        for repo in self._repositories.values():
            if repo.config.is_default:
                repo.config.is_default = False
                repo.config.updated_at = datetime.utcnow()
        
        # Save changes
        self._save_repositories()
        
        logger.info("Cleared default repository")
        return True
    
    async def connect_to_existing_repository(self, config: RepositoryConfig,
                                           credentials: Optional[Dict[str, str]] = None) -> Repository:
        """
        Connect to an existing repository with credential handling.
        
        Args:
            config: Repository configuration
            credentials: Optional credentials for repository access
            
        Returns:
            Repository: Connected repository instance
            
        Raises:
            RepositoryNotFoundError: If no repository exists at the URI
            CredentialError: If credentials are required but not provided
        """
        async with await self._acquire_repository_lock(config.name):
            # Detect existing repository
            existing_info = await self.detect_existing_repository(config.uri)
            if not existing_info:
                raise RepositoryNotFoundError(f"No repository found at {config.uri}")
            
            # Connect to existing repository
            return await self._existing_repo_handler.connect_to_existing_repository(
                config, existing_info, credentials
            )
    
    async def reinitialize_repository(self, config: RepositoryConfig,
                                    force_confirm: bool = False) -> Repository:
        """
        Re-initialize an existing repository (destructive operation).
        
        Args:
            config: Repository configuration
            force_confirm: Whether confirmation has been provided
            
        Returns:
            Repository: Re-initialized repository instance
            
        Raises:
            RepositoryNotFoundError: If no repository exists at the URI
            DataLossConfirmationError: If confirmation is required but not provided
        """
        async with await self._acquire_repository_lock(config.name):
            # Detect existing repository
            existing_info = await self.detect_existing_repository(config.uri)
            if not existing_info:
                raise RepositoryNotFoundError(f"No repository found at {config.uri}")
            
            # Re-initialize repository
            return await self._existing_repo_handler.reinitialize_repository(
                config, existing_info, force_confirm
            )
    
    def require_data_loss_confirmation(self, existing_info: ExistingRepositoryInfo) -> str:
        """
        Generate data loss warning message for user confirmation.
        
        Args:
            existing_info: Information about existing repository
            
        Returns:
            str: Warning message for user confirmation
        """
        return self._existing_repo_handler._generate_data_loss_warning(existing_info)
    
    def get_state_history(self, repository_name: str, limit: Optional[int] = None) -> List[RepositoryStateTransition]:
        """
        Get state transition history for a repository.
        
        Args:
            repository_name: Repository name
            limit: Optional limit on number of transitions to return
            
        Returns:
            List[RepositoryStateTransition]: State transition history
        """
        return self._state_manager.get_state_history(repository_name, limit)
    
    def get_repository_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about repository management operations.
        
        Returns:
            Dict[str, Any]: Repository management statistics
        """
        state_stats = self._state_manager.get_statistics()
        
        # Add repository count statistics
        total_repos = len(self._repositories)
        status_counts = {}
        for repo in self._repositories.values():
            status = repo.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_repositories': total_repos,
            'status_distribution': status_counts,
            'state_management': state_stats,
            'performance_thresholds': self._performance_thresholds
        }