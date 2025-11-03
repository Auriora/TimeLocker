"""
Existing Repository Handler for TimeLocker

This module provides functionality for detecting existing repositories,
handling connection vs re-initialization choices, and managing data loss
confirmation mechanisms.
"""

import asyncio
import logging
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urlparse

from ..interfaces.repository_management_models import (
    Repository, RepositoryConfig, BackupEngine, RepositoryType,
    ExistingRepositoryInfo, RepositoryCreationOptions,
    RepositoryError, DataLossConfirmationError, CredentialError
)
from ..backup_repository import BackupRepository
from .repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class ExistingRepositoryHandler:
    """
    Handles detection and management of existing repositories.
    
    Provides methods for detecting existing repositories, extracting metadata,
    handling connection vs re-initialization choices, and managing data loss
    confirmation mechanisms with detailed warnings.
    """
    
    def __init__(self, repository_factory: Optional[RepositoryFactory] = None):
        """
        Initialize Existing Repository Handler.
        
        Args:
            repository_factory: Factory for creating repository instances
        """
        self._repository_factory = repository_factory or RepositoryFactory()
        self._credential_prompter: Optional[Callable[[str], Optional[str]]] = None
        
        logger.debug("ExistingRepositoryHandler initialized")
    
    def set_credential_prompter(self, prompter: Callable[[str], Optional[str]]) -> None:
        """
        Set credential prompter function for interactive credential requests.
        
        Args:
            prompter: Function that prompts for credentials and returns them
        """
        self._credential_prompter = prompter
    
    async def detect_existing_repository(self, uri: str) -> Optional[ExistingRepositoryInfo]:
        """
        Detect if a repository already exists at the specified URI.
        
        Args:
            uri: Repository URI to check
            
        Returns:
            ExistingRepositoryInfo: Information about existing repository, or None if not found
        """
        try:
            logger.debug(f"Detecting existing repository at: {uri}")
            
            # Determine repository type from URI
            repo_type = self._detect_repository_type(uri)
            engine_type = BackupEngine.RESTIC  # Default assumption
            
            # Check based on repository type
            if repo_type == RepositoryType.LOCAL:
                return await self._detect_local_repository(uri, engine_type)
            elif repo_type in [RepositoryType.S3, RepositoryType.B2]:
                return await self._detect_cloud_repository(uri, engine_type)
            elif repo_type in [RepositoryType.SFTP, RepositoryType.SMB, RepositoryType.NFS]:
                return await self._detect_network_repository(uri, engine_type)
            else:
                logger.warning(f"Unsupported repository type for detection: {repo_type}")
                return None
                
        except Exception as e:
            logger.debug(f"No existing repository found at {uri}: {e}")
            return None
    
    def _detect_repository_type(self, uri: str) -> RepositoryType:
        """
        Detect repository type from URI.
        
        Args:
            uri: Repository URI
            
        Returns:
            RepositoryType: Detected repository type
        """
        if not uri:
            return RepositoryType.LOCAL
        
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'local'
        
        type_mapping = {
            'file': RepositoryType.LOCAL,
            'local': RepositoryType.LOCAL,
            's3': RepositoryType.S3,
            'b2': RepositoryType.B2,
            'sftp': RepositoryType.SFTP,
            'smb': RepositoryType.SMB,
            'nfs': RepositoryType.NFS
        }
        
        return type_mapping.get(scheme, RepositoryType.LOCAL)
    
    async def _detect_local_repository(self, uri: str, engine_type: BackupEngine) -> Optional[ExistingRepositoryInfo]:
        """
        Detect existing local repository.
        
        Args:
            uri: Local repository URI
            engine_type: Backup engine type
            
        Returns:
            ExistingRepositoryInfo: Repository information if found
        """
        try:
            # Parse local path
            parsed = urlparse(uri)
            path = parsed.path if parsed.path else uri
            
            # Check if path exists and contains repository files
            repo_path = Path(path)
            if not repo_path.exists():
                return None
            
            # Check for Restic repository markers
            if engine_type == BackupEngine.RESTIC:
                config_file = repo_path / "config"
                if not config_file.exists():
                    return None
                
                # Extract repository metadata
                metadata = await self._extract_restic_metadata(str(repo_path))
                
                # Get directory statistics
                size_info = await self._get_directory_size(repo_path)
                
                return ExistingRepositoryInfo(
                    uri=uri,
                    engine_type=engine_type,
                    requires_credentials=True,  # Assume encrypted
                    metadata=metadata,
                    last_modified=datetime.fromtimestamp(config_file.stat().st_mtime),
                    estimated_size=size_info.get('total_size'),
                    snapshot_count=metadata.get('snapshot_count')
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to detect local repository at {uri}: {e}")
            return None
    
    async def _detect_cloud_repository(self, uri: str, engine_type: BackupEngine) -> Optional[ExistingRepositoryInfo]:
        """
        Detect existing cloud repository.
        
        Args:
            uri: Cloud repository URI
            engine_type: Backup engine type
            
        Returns:
            ExistingRepositoryInfo: Repository information if found
        """
        try:
            # Create temporary repository instance for testing
            temp_repo = self._repository_factory.create_repository(uri)
            
            # Try to access repository without credentials first
            if await self._test_repository_access(temp_repo, require_unlock=False):
                metadata = await self._extract_repository_metadata(temp_repo)
                
                return ExistingRepositoryInfo(
                    uri=uri,
                    engine_type=engine_type,
                    requires_credentials=True,
                    metadata=metadata,
                    last_modified=datetime.utcnow(),  # Cloud repos don't have simple modification times
                    snapshot_count=metadata.get('snapshot_count')
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to detect cloud repository at {uri}: {e}")
            return None
    
    async def _detect_network_repository(self, uri: str, engine_type: BackupEngine) -> Optional[ExistingRepositoryInfo]:
        """
        Detect existing network repository.
        
        Args:
            uri: Network repository URI
            engine_type: Backup engine type
            
        Returns:
            ExistingRepositoryInfo: Repository information if found
        """
        try:
            # Network repositories require more complex detection
            # This is a simplified implementation
            temp_repo = self._repository_factory.create_repository(uri)
            
            if await self._test_repository_access(temp_repo, require_unlock=False):
                metadata = await self._extract_repository_metadata(temp_repo)
                
                return ExistingRepositoryInfo(
                    uri=uri,
                    engine_type=engine_type,
                    requires_credentials=True,
                    metadata=metadata,
                    last_modified=datetime.utcnow(),
                    snapshot_count=metadata.get('snapshot_count')
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to detect network repository at {uri}: {e}")
            return None
    
    async def _extract_restic_metadata(self, repo_path: str) -> Dict[str, Any]:
        """
        Extract metadata from Restic repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Dict[str, Any]: Repository metadata
        """
        metadata = {}
        
        try:
            # Try to get repository info without password (limited info)
            cmd = ['restic', '-r', repo_path, 'snapshots', '--json', '--no-lock']
            
            # Run with minimal environment to avoid password prompts
            env = os.environ.copy()
            env.pop('RESTIC_PASSWORD', None)
            env.pop('RESTIC_PASSWORD_FILE', None)
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Parse snapshot information
                try:
                    snapshots = json.loads(stdout.decode())
                    metadata['snapshot_count'] = len(snapshots) if snapshots else 0
                    
                    if snapshots:
                        # Get date range
                        timestamps = [s.get('time') for s in snapshots if s.get('time')]
                        if timestamps:
                            metadata['oldest_snapshot'] = min(timestamps)
                            metadata['newest_snapshot'] = max(timestamps)
                            
                except json.JSONDecodeError:
                    logger.debug("Failed to parse snapshot JSON")
            
            # Try to get repository stats
            cmd = ['restic', '-r', repo_path, 'stats', '--json', '--no-lock']
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                try:
                    stats = json.loads(stdout.decode())
                    metadata.update(stats)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse stats JSON")
            
        except Exception as e:
            logger.debug(f"Failed to extract Restic metadata: {e}")
        
        return metadata
    
    async def _get_directory_size(self, path: Path) -> Dict[str, Any]:
        """
        Get directory size information.
        
        Args:
            path: Directory path
            
        Returns:
            Dict[str, Any]: Size information
        """
        try:
            total_size = 0
            file_count = 0
            
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
            
            return {
                'total_size': total_size,
                'file_count': file_count
            }
            
        except Exception as e:
            logger.debug(f"Failed to get directory size: {e}")
            return {}
    
    async def _test_repository_access(self, repository: BackupRepository, require_unlock: bool = True) -> bool:
        """
        Test if repository is accessible.
        
        Args:
            repository: Repository to test
            require_unlock: Whether to require unlocking the repository
            
        Returns:
            bool: True if accessible
        """
        try:
            # This is a simplified test - in practice, you'd use repository-specific methods
            if hasattr(repository, 'list_snapshots'):
                snapshots = repository.list_snapshots()
                return True
            return False
            
        except Exception as e:
            logger.debug(f"Repository access test failed: {e}")
            return False
    
    async def _extract_repository_metadata(self, repository: BackupRepository) -> Dict[str, Any]:
        """
        Extract metadata from repository.
        
        Args:
            repository: Repository instance
            
        Returns:
            Dict[str, Any]: Repository metadata
        """
        metadata = {}
        
        try:
            if hasattr(repository, 'list_snapshots'):
                snapshots = repository.list_snapshots()
                metadata['snapshot_count'] = len(snapshots)
                
                if snapshots:
                    timestamps = [s.timestamp for s in snapshots]
                    metadata['oldest_snapshot'] = min(timestamps)
                    metadata['newest_snapshot'] = max(timestamps)
            
        except Exception as e:
            logger.debug(f"Failed to extract repository metadata: {e}")
        
        return metadata
    
    async def connect_to_existing_repository(self, config: RepositoryConfig,
                                           existing_info: ExistingRepositoryInfo,
                                           credentials: Optional[Dict[str, str]] = None) -> Repository:
        """
        Connect to an existing repository.
        
        Args:
            config: Repository configuration
            existing_info: Information about existing repository
            credentials: Optional credentials for repository access
            
        Returns:
            Repository: Connected repository instance
            
        Raises:
            CredentialError: If credentials are required but not provided
        """
        try:
            # Handle credential requirements
            if existing_info.requires_credentials and not credentials:
                if self._credential_prompter:
                    password = self._credential_prompter(f"Password for repository {config.uri}")
                    if password:
                        credentials = {'password': password}
                
                if not credentials:
                    raise CredentialError(f"Credentials required to unlock existing repository at {config.uri}")
            
            # Create repository instance with credentials
            repo_kwargs = {}
            if credentials:
                repo_kwargs.update(credentials)
            
            repo_instance = self._repository_factory.create_repository(
                config.uri,
                repository_name=config.name,
                **repo_kwargs
            )
            
            # Test access to existing repository
            if not await self._test_repository_access(repo_instance):
                raise RepositoryError(f"Cannot access existing repository at {config.uri}")
            
            # Update configuration with existing repository metadata
            config.metadata.update(existing_info.metadata)
            
            # Create repository object
            from ..interfaces.repository_management_models import RepositoryStatus
            repository = Repository(
                config=config,
                status=RepositoryStatus.ACTIVE
            )
            
            logger.info(f"Connected to existing repository: {config.name}")
            return repository
            
        except Exception as e:
            logger.error(f"Failed to connect to existing repository {config.name}: {e}")
            raise RepositoryError(f"Failed to connect to existing repository: {e}")
    
    async def reinitialize_repository(self, config: RepositoryConfig,
                                    existing_info: ExistingRepositoryInfo,
                                    force_confirm: bool = False) -> Repository:
        """
        Re-initialize an existing repository (destructive operation).
        
        Args:
            config: Repository configuration
            existing_info: Information about existing repository
            force_confirm: Whether confirmation has been provided
            
        Returns:
            Repository: Re-initialized repository instance
            
        Raises:
            DataLossConfirmationError: If confirmation is required but not provided
        """
        if not force_confirm:
            raise DataLossConfirmationError(
                self._generate_data_loss_warning(existing_info)
            )
        
        try:
            # Backup existing repository metadata if possible
            backup_metadata = {
                'original_uri': existing_info.uri,
                'original_metadata': existing_info.metadata,
                'backup_timestamp': datetime.utcnow().isoformat(),
                'estimated_size': existing_info.estimated_size,
                'snapshot_count': existing_info.snapshot_count
            }
            
            logger.warning(f"Re-initializing repository at {config.uri} - all data will be lost")
            
            # Create new repository instance (this will overwrite existing data)
            repo_instance = self._repository_factory.create_repository(
                config.uri,
                repository_name=config.name
            )
            
            # Initialize the repository (destructive operation)
            if hasattr(repo_instance, 'init'):
                await asyncio.to_thread(repo_instance.init)
            
            # Store backup metadata in new configuration
            config.metadata['backup_info'] = backup_metadata
            
            # Create repository object
            from ..interfaces.repository_management_models import RepositoryStatus
            repository = Repository(
                config=config,
                status=RepositoryStatus.ACTIVE
            )
            
            logger.info(f"Re-initialized repository: {config.name}")
            return repository
            
        except Exception as e:
            logger.error(f"Failed to re-initialize repository {config.name}: {e}")
            raise RepositoryError(f"Failed to re-initialize repository: {e}")
    
    def _generate_data_loss_warning(self, existing_info: ExistingRepositoryInfo) -> str:
        """
        Generate detailed warning about data loss.
        
        Args:
            existing_info: Information about existing repository
            
        Returns:
            str: Formatted warning message
        """
        size_info = existing_info.format_size()
        modified_info = existing_info.last_modified.strftime("%Y-%m-%d %H:%M:%S") if existing_info.last_modified else "Unknown"
        snapshot_info = f"{existing_info.snapshot_count} snapshots" if existing_info.snapshot_count else "Unknown number of snapshots"
        
        return (
            "⚠️  WARNING: REPOSITORY RE-INITIALIZATION WILL PERMANENTLY DELETE ALL DATA ⚠️\n"
            f"Repository URI: {existing_info.uri}\n"
            f"Engine: {existing_info.engine_type.value}\n"
            f"Size: {size_info}\n"
            f"Last modified: {modified_info}\n"
            f"Snapshots: {snapshot_info}\n"
            "\nThis action cannot be undone. All backup data will be permanently lost.\n"
            "Type 'DELETE ALL DATA' to confirm re-initialization."
        )
    
    async def require_data_loss_confirmation(self, existing_info: ExistingRepositoryInfo,
                                           confirmation_prompter: Optional[Callable[[str], str]] = None) -> bool:
        """
        Require explicit user confirmation for operations that cause data loss.
        
        Args:
            existing_info: Information about existing repository
            confirmation_prompter: Function to prompt user for confirmation
            
        Returns:
            bool: True if user provided correct confirmation
        """
        warning_message = self._generate_data_loss_warning(existing_info)
        
        if confirmation_prompter:
            user_input = confirmation_prompter(warning_message)
            return user_input.strip() == "DELETE ALL DATA"
        
        # If no prompter provided, require explicit confirmation through exception
        raise DataLossConfirmationError(warning_message)