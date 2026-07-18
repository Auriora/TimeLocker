"""
Repository Resolver Service for CLI Commands

This service provides centralized repository resolution for all CLI commands,
eliminating duplication and providing consistent repository lookup and credential handling.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from threading import RLock

from ...config import ConfigurationModule
from ...config.configuration_schema import RepositoryConfig
from ...interfaces.exceptions import ConfigurationError, RepositoryNotFoundError
from ...security.credential_manager import CredentialManager, CredentialManagerError
from ...utils.repository_resolver import (
    resolve_repository_uri,
    get_repository_info,
    get_default_repository,
    normalize_repository_uri,
    validate_repository_name_or_uri
)
from ...backup_repository import BackupRepository
from ...backup_manager import BackupManager

logger = logging.getLogger(__name__)


class RepositoryResolver:
    """
    Centralized repository resolution service for CLI commands.
    
    This service provides:
    - Unified repository resolution logic
    - Credential resolution chain (explicit → credential manager → environment → prompt)
    - Backend detection and validation
    - Repository caching mechanism
    - Consistent error handling
    
    Benefits:
    - Eliminates repository resolution duplication across 30+ commands
    - Provides consistent credential handling
    - Reduces code by ~180 lines across commands
    - Improves performance through caching
    
    Credential Resolution Chain:
    1. Explicit password parameter
    2. Credential manager (if unlocked)
    3. Environment variables (RESTIC_PASSWORD, TIMELOCKER_PASSWORD)
    4. Interactive prompt (if allowed)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize repository resolver service.
        
        Args:
            config_dir: Optional specific configuration directory
        """
        self._config_module = ConfigurationModule(config_dir=config_dir)
        self._credential_manager: Optional[CredentialManager] = None
        self._cache_lock = RLock()
        self._repository_cache: Dict[str, Tuple[BackupRepository, float]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Performance tracking
        self._operation_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Initialize credential manager
        self._initialize_credential_manager()
        
        logger.debug("RepositoryResolver initialized")
    
    def _initialize_credential_manager(self) -> None:
        """Initialize credential manager for password resolution."""
        try:
            self._credential_manager = CredentialManager(config_dir=self._config_module.config_dir / "credentials")
            # Try to auto-unlock credential manager (non-interactive)
            try:
                self._credential_manager.ensure_unlocked(allow_prompt=False)
            except Exception as e:
                logger.debug(f"Credential manager auto-unlock failed: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize credential manager: {e}")
            self._credential_manager = None
    
    # Core resolution methods
    
    def resolve_repository(
        self,
        name_or_uri: Optional[str] = None,
        password: Optional[str] = None,
        allow_prompt: bool = False
    ) -> BackupRepository:
        """
        Resolve repository name or URI to a BackupRepository instance.
        
        This method implements the complete resolution chain:
        1. Resolve name/URI to actual URI
        2. Detect backend type
        3. Resolve credentials through credential chain
        4. Create and cache repository instance
        
        Args:
            name_or_uri: Repository name or URI. If None, uses default repository.
            password: Optional explicit password (highest priority in credential chain)
            allow_prompt: Whether to prompt for password if not found
            
        Returns:
            BackupRepository: Configured repository instance
            
        Raises:
            RepositoryNotFoundError: If repository cannot be resolved
            ConfigurationError: If repository configuration is invalid
        """
        self._operation_count += 1
        
        try:
            # Step 1: Resolve to URI
            repository_uri = resolve_repository_uri(name_or_uri, self._config_module.config_dir)
            
            # Step 2: Get repository info (name, metadata)
            repo_info = get_repository_info(name_or_uri or repository_uri, self._config_module.config_dir)
            repository_name = repo_info.get('name', name_or_uri or repository_uri)
            
            # Step 3: Check cache
            cache_key = f"{repository_uri}:{repository_name}"
            cached_repo = self._get_from_cache(cache_key)
            if cached_repo is not None:
                self._cache_hits += 1
                logger.debug(f"Repository cache hit for: {repository_name}")
                return cached_repo
            
            self._cache_misses += 1
            
            # Step 4: Resolve credentials
            resolved_password = self._resolve_credentials(
                repository_name=repository_name,
                repository_uri=repository_uri,
                explicit_password=password,
                allow_prompt=allow_prompt
            )
            
            # Step 5: Create repository instance
            backup_manager = BackupManager()
            repository = backup_manager.from_uri(
                repository_uri,
                password=resolved_password,
                repository_name=repository_name
            )
            
            # Step 6: Validate repository
            self._validate_repository(repository)
            
            # Step 7: Cache repository
            self._add_to_cache(cache_key, repository)
            
            logger.debug(f"Repository resolved successfully: {repository_name}")
            return repository
            
        except (RepositoryNotFoundError, ConfigurationError):
            raise
        except Exception as e:
            logger.error(f"Failed to resolve repository '{name_or_uri}': {e}")
            raise ConfigurationError(f"Failed to resolve repository: {e}")
    
    def resolve_repository_uri(self, name_or_uri: Optional[str] = None) -> str:
        """
        Resolve repository name to URI without creating repository instance.
        
        Args:
            name_or_uri: Repository name or URI. If None, uses default repository.
            
        Returns:
            str: Resolved repository URI
            
        Raises:
            RepositoryNotFoundError: If repository cannot be resolved
        """
        try:
            return resolve_repository_uri(name_or_uri, self._config_module.config_dir)
        except Exception as e:
            logger.error(f"Failed to resolve repository URI for '{name_or_uri}': {e}")
            raise
    
    def resolve_repository_name(self, name_or_uri: str) -> str:
        """
        Resolve repository name or URI to repository name.
        
        Args:
            name_or_uri: Repository name or URI
            
        Returns:
            str: Repository name (or URI if not a named repository)
        """
        try:
            repo_info = get_repository_info(name_or_uri, self._config_module.config_dir)
            return repo_info.get('name', name_or_uri)
        except Exception as e:
            logger.debug(f"Failed to resolve repository name for '{name_or_uri}': {e}")
            return name_or_uri
    
    def get_default_repository(self) -> Optional[str]:
        """
        Get default repository name.
        
        Returns:
            Optional[str]: Default repository name or None
        """
        return get_default_repository(self._config_module.config_dir)
    
    # Credential resolution methods
    
    def _resolve_credentials(
        self,
        repository_name: str,
        repository_uri: str,
        explicit_password: Optional[str] = None,
        allow_prompt: bool = False
    ) -> Optional[str]:
        """
        Resolve repository credentials through the credential chain.
        
        Credential Chain (in order):
        1. Explicit password parameter
        2. Credential manager (if unlocked)
        3. Environment variables (RESTIC_PASSWORD, TIMELOCKER_PASSWORD)
        4. Interactive prompt (if allowed)
        
        Args:
            repository_name: Repository name for credential lookup
            repository_uri: Repository URI for logging
            explicit_password: Explicit password (highest priority)
            allow_prompt: Whether to prompt for password if not found
            
        Returns:
            Optional[str]: Resolved password or None
        """
        # 1. Explicit password (highest priority)
        if explicit_password:
            logger.debug(f"Using explicit password for repository: {repository_name}")
            return explicit_password
        
        # 2. Credential manager
        if self._credential_manager and not self._credential_manager.is_locked():
            try:
                stored_password = self._credential_manager.get_repository_password(
                    repository_name,
                    allow_prompt=False
                )
                if stored_password:
                    logger.debug(f"Using credential manager password for repository: {repository_name}")
                    return stored_password
            except CredentialManagerError as e:
                logger.debug(f"Credential manager lookup failed for '{repository_name}': {e}")
        
        # 3. Environment variables
        import os
        env_password = os.getenv('RESTIC_PASSWORD') or os.getenv('TIMELOCKER_PASSWORD')
        if env_password:
            logger.debug(f"Using environment variable password for repository: {repository_name}")
            return env_password
        
        # 4. Interactive prompt (if allowed)
        if allow_prompt:
            try:
                from rich.prompt import Prompt
                password = Prompt.ask(
                    f"Password for repository '{repository_name}'",
                    password=True
                )
                if password:
                    logger.debug(f"Using prompted password for repository: {repository_name}")
                    return password
            except (KeyboardInterrupt, EOFError):
                logger.debug("User cancelled password prompt")
            except Exception as e:
                logger.warning(f"Failed to prompt for password: {e}")
        
        # No password found
        logger.debug(f"No password resolved for repository: {repository_name}")
        return None
    
    def resolve_credentials(
        self,
        repository_name: str,
        explicit_password: Optional[str] = None,
        allow_prompt: bool = False
    ) -> Optional[str]:
        """
        Public method to resolve credentials for a repository.
        
        Args:
            repository_name: Repository name
            explicit_password: Optional explicit password
            allow_prompt: Whether to prompt for password if not found
            
        Returns:
            Optional[str]: Resolved password or None
        """
        try:
            repository_uri = self.resolve_repository_uri(repository_name)
            return self._resolve_credentials(
                repository_name=repository_name,
                repository_uri=repository_uri,
                explicit_password=explicit_password,
                allow_prompt=allow_prompt
            )
        except Exception as e:
            logger.error(f"Failed to resolve credentials for '{repository_name}': {e}")
            return None
    
    # Backend detection methods
    
    def detect_backend(self, uri: str) -> str:
        """
        Detect backend type from repository URI.
        
        Args:
            uri: Repository URI
            
        Returns:
            str: Backend type (s3, b2, local, sftp, etc.)
        """
        uri_lower = uri.lower()
        
        if uri_lower.startswith(("s3://", "s3:")):
            return "s3"
        elif uri_lower.startswith(("b2://", "b2:")):
            return "b2"
        elif uri_lower.startswith(("sftp://", "sftp:")):
            return "sftp"
        elif uri_lower.startswith(("rest://", "rest:")):
            return "rest"
        elif uri_lower.startswith("rclone:"):
            return "rclone"
        elif uri_lower.startswith(("azure://", "azure:")):
            return "azure"
        elif uri_lower.startswith(("gs://", "gs:")):
            return "gs"
        elif uri_lower.startswith("swift:"):
            return "swift"
        elif uri_lower.startswith(("file://", "/")):
            return "local"
        else:
            return "local"  # Default to local
    
    def get_backend_info(self, uri: str) -> Dict[str, Any]:
        """
        Get backend information from repository URI.
        
        Args:
            uri: Repository URI
            
        Returns:
            Dict[str, Any]: Backend information including type and parsed components
        """
        backend_type = self.detect_backend(uri)
        
        info = {
            'type': backend_type,
            'uri': uri,
            'normalized_uri': normalize_repository_uri(uri)
        }
        
        # Parse backend-specific components
        if backend_type == 's3':
            # Extract bucket and path from s3:host/bucket/path
            if uri.startswith('s3:'):
                parts = uri[3:].split('/', 1)
                info['host'] = parts[0] if parts else ''
                info['path'] = parts[1] if len(parts) > 1 else ''
        elif backend_type == 'b2':
            # Extract bucket and path from b2:bucket/path
            if uri.startswith('b2:'):
                parts = uri[3:].split('/', 1)
                info['bucket'] = parts[0] if parts else ''
                info['path'] = parts[1] if len(parts) > 1 else ''
        elif backend_type == 'local':
            # Extract path
            if uri.startswith('file://'):
                info['path'] = uri[7:]
            else:
                info['path'] = uri
        
        return info
    
    # Validation methods
    
    def _validate_repository(self, repository: BackupRepository) -> None:
        """
        Validate repository instance.
        
        Args:
            repository: Repository instance to validate
            
        Raises:
            ConfigurationError: If repository is invalid
        """
        if repository is None:
            raise ConfigurationError("Repository instance is None")
        
        # Basic validation - repository should have required attributes
        if not hasattr(repository, 'uri'):
            raise ConfigurationError("Repository missing 'uri' attribute")
    
    @staticmethod
    def validate_repository_name_or_uri(value: str) -> None:
        """
        Validate repository name or URI format.
        
        Args:
            value: Repository name or URI to validate
            
        Raises:
            ValueError: If value is invalid
        """
        validate_repository_name_or_uri(value)
    
    # Cache management methods
    
    def _get_from_cache(self, cache_key: str) -> Optional[BackupRepository]:
        """
        Get repository from cache if not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Optional[BackupRepository]: Cached repository or None
        """
        import time
        
        with self._cache_lock:
            if cache_key in self._repository_cache:
                repository, timestamp = self._repository_cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return repository
                else:
                    # Expired, remove from cache
                    del self._repository_cache[cache_key]
        
        return None
    
    def _add_to_cache(self, cache_key: str, repository: BackupRepository) -> None:
        """
        Add repository to cache.
        
        Args:
            cache_key: Cache key
            repository: Repository instance to cache
        """
        import time
        
        with self._cache_lock:
            self._repository_cache[cache_key] = (repository, time.time())
            logger.debug(f"Repository cached: {cache_key}")
    
    def clear_cache(self) -> None:
        """Clear repository cache."""
        with self._cache_lock:
            self._repository_cache.clear()
            logger.debug("Repository cache cleared")
    
    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """
        Set cache TTL.
        
        Args:
            ttl_seconds: Cache TTL in seconds
        """
        self._cache_ttl = ttl_seconds
        logger.debug(f"Repository cache TTL set to {ttl_seconds} seconds")
    
    # Repository configuration methods
    
    def get_repository_config(self, name: str) -> RepositoryConfig:
        """
        Get repository configuration by name.
        
        Args:
            name: Repository name
            
        Returns:
            RepositoryConfig: Repository configuration
            
        Raises:
            RepositoryNotFoundError: If repository not found
        """
        try:
            return self._config_module.get_repository(name)
        except Exception as e:
            logger.error(f"Failed to get repository config for '{name}': {e}")
            raise
    
    def list_repositories(self) -> Dict[str, RepositoryConfig]:
        """
        List all configured repositories.
        
        Returns:
            Dict[str, RepositoryConfig]: Dictionary of repository configurations
        """
        try:
            config = self._config_module.get_config()
            return config.repositories
        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            return {}
    
    # Utility methods
    
    @property
    def config_dir(self) -> Path:
        """Get configuration directory path."""
        return self._config_module.config_dir
    
    @property
    def credential_manager(self) -> Optional[CredentialManager]:
        """Get credential manager instance."""
        return self._credential_manager
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the service.
        
        Returns:
            Dict[str, Any]: Performance statistics
        """
        total_operations = self._operation_count
        hit_rate = (self._cache_hits / total_operations * 100) if total_operations > 0 else 0
        
        return {
            'total_operations': total_operations,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': f"{hit_rate:.1f}%",
            'cache_size': len(self._repository_cache)
        }
