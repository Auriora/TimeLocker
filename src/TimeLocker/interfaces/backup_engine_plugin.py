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
Backup Engine Plugin Interface

This module defines the abstract interface for backup engine plugins,
enabling extensible support for different backup strategies (Restic, Rsync, Rclone, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from .repository_management_models import BackupEngine as _RepoBackupEngine


BackupEngine = _RepoBackupEngine


class RepositoryType(Enum):
    """Enumeration of repository storage types"""
    LOCAL = "local"
    S3 = "s3"
    B2 = "b2"
    SFTP = "sftp"
    SMB = "smb"
    NFS = "nfs"
    REST = "rest"


@dataclass
class ValidationResult:
    """Result of configuration or availability validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings"""
        return len(self.warnings) > 0


@dataclass
class EngineCapabilities:
    """Capabilities and features supported by a backup engine"""
    supports_encryption: bool = False
    supports_deduplication: bool = False
    supports_compression: bool = False
    supports_snapshots: bool = False
    supports_incremental: bool = False
    supports_verification: bool = False
    supports_retention_policies: bool = False
    supports_tags: bool = False
    storage_backends: List[str] = None
    
    def __post_init__(self):
        if self.storage_backends is None:
            self.storage_backends = []

    def __contains__(self, item: str) -> bool:
        """Allow `'field_name' in capabilities` style checks used by tests."""
        return hasattr(self, item)

    @property
    def supported_backends(self) -> List[str]:
        """Backwards-compatible alias expected by older tests."""
        return self.storage_backends


class BackupEnginePlugin(ABC):
    """
    Abstract base class for backup engine plugins.
    
    This interface defines the contract that all backup engine implementations
    must follow, enabling consistent repository operations across different
    backup strategies.
    """
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """
        Get the name of the backup engine.
        
        Returns:
            Engine name (e.g., 'restic', 'rsync', 'rclone')
        """
        pass
    
    @property
    @abstractmethod
    def engine_type(self) -> BackupEngine:
        """
        Get the engine type enum value.
        
        Returns:
            BackupEngine enum value
        """
        pass
    
    @property
    @abstractmethod
    def engine_version(self) -> str:
        """
        Get the version of the backup engine executable.
        
        Returns:
            Version string (e.g., '0.18.0')
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the backup engine is available on the system.
        
        Returns:
            True if engine executable is found and functional, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> EngineCapabilities:
        """
        Get the capabilities and features supported by this engine.
        
        Returns:
            EngineCapabilities describing what features are supported
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate engine-specific configuration.
        
        Args:
            config: Engine-specific configuration dictionary
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        pass
    
    @abstractmethod
    def supports_storage_type(self, storage_type: str) -> bool:
        """
        Check if the engine supports a specific storage backend type.
        
        Args:
            storage_type: Storage type identifier (e.g., 's3', 'local', 'sftp')
            
        Returns:
            True if storage type is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_storage_backends(self) -> List[str]:
        """
        Get list of supported storage backend types.
        
        Returns:
            List of storage backend identifiers (e.g., ['local', 's3', 'b2'])
        """
        pass
    
    @abstractmethod
    def create_repository(self, uri: str, password: Optional[str] = None, **kwargs) -> Any:
        """
        Create a repository instance for this engine.
        
        Args:
            uri: Repository URI
            password: Optional repository password
            **kwargs: Additional engine-specific parameters
            
        Returns:
            Repository instance compatible with BackupRepository interface
            
        Raises:
            EngineError: If repository creation fails
        """
        pass
    
    @abstractmethod
    def validate_uri(self, uri: str) -> ValidationResult:
        """
        Validate a repository URI for this engine.
        
        Args:
            uri: Repository URI to validate
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        pass
    
    def get_default_configuration(self) -> Dict[str, Any]:
        """
        Get default configuration for this engine.
        
        Returns:
            Dictionary with default configuration values
        """
        return {}
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for engine configuration validation.
        
        Returns:
            JSON schema dictionary describing valid configuration
        """
        return {}


class PluginError(Exception):
    """Base exception for plugin-related errors"""
    pass


class EngineNotAvailableError(PluginError):
    """Raised when a backup engine is not available on the system"""
    pass


class EngineConfigurationError(PluginError):
    """Raised when engine configuration is invalid"""
    pass


class UnsupportedStorageTypeError(PluginError):
    """Raised when a storage type is not supported by the engine"""
    pass
