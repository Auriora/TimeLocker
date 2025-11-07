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
Restic Backup Engine Plugin

This module provides a plugin implementation for the Restic backup engine,
wrapping existing Restic functionality in the plugin interface.
"""

import logging
import subprocess
import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from packaging import version

from ...interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    ValidationResult,
    EngineCapabilities,
    EngineNotAvailableError,
    EngineConfigurationError
)
from ...backup_repository import BackupRepository

logger = logging.getLogger(__name__)


class ResticEnginePlugin(BackupEnginePlugin):
    """
    Plugin implementation for Restic backup engine.
    
    Restic provides encrypted, deduplicated backups with snapshot support
    and comprehensive storage backend compatibility.
    """
    
    RESTIC_MIN_VERSION = "0.18.0"
    SUPPORTED_SCHEMES = ['local', 'file', 's3', 'b2', 'sftp', 'rest']
    
    def __init__(self):
        """Initialize Restic plugin"""
        self._version: Optional[str] = None
        self._available: Optional[bool] = None
        logger.debug("ResticEnginePlugin initialized")
    
    @property
    def engine_name(self) -> str:
        """Get engine name"""
        return "restic"
    
    @property
    def engine_type(self) -> BackupEngine:
        """Get engine type"""
        return BackupEngine.RESTIC
    
    @property
    def engine_version(self) -> str:
        """Get Restic version"""
        if self._version is None:
            self._detect_version()
        return self._version or "unknown"
    
    def is_available(self) -> bool:
        """Check if Restic is available on the system"""
        if self._available is not None:
            return self._available
        
        try:
            self._detect_version()
            self._available = self._version is not None
            return self._available
        except Exception as e:
            logger.debug(f"Restic not available: {e}")
            self._available = False
            return False
    
    def _detect_version(self) -> None:
        """Detect Restic version from executable"""
        try:
            # Try JSON version output first
            result = subprocess.run(
                ['restic', '--json', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                try:
                    version_data = json.loads(result.stdout)
                    self._version = version_data.get('version', 'unknown')
                    logger.debug(f"Detected Restic version: {self._version}")
                    return
                except json.JSONDecodeError:
                    pass
            
            # Fallback to text parsing
            result = subprocess.run(
                ['restic', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse version from output like "restic 0.18.0 compiled with go1.23.4"
                match = re.search(r'restic\s+(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    self._version = match.group(1)
                    logger.debug(f"Detected Restic version: {self._version}")
                    return
            
            logger.warning("Could not detect Restic version")
            self._version = "unknown"
            
        except FileNotFoundError:
            logger.debug("Restic executable not found in PATH")
            self._version = None
        except subprocess.TimeoutExpired:
            logger.warning("Restic version check timed out")
            self._version = None
        except Exception as e:
            logger.warning(f"Error detecting Restic version: {e}")
            self._version = None
    
    def get_capabilities(self) -> EngineCapabilities:
        """Get Restic capabilities"""
        return EngineCapabilities(
            supports_encryption=True,
            supports_deduplication=True,
            supports_compression=True,
            supports_snapshots=True,
            supports_incremental=True,
            supports_verification=True,
            supports_retention_policies=True,
            supports_tags=True,
            storage_backends=self.SUPPORTED_SCHEMES
        )
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate Restic-specific configuration.
        
        Args:
            config: Configuration dictionary with Restic-specific settings
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Validate compression setting
        if 'compression' in config:
            valid_compression = ['auto', 'off', 'max']
            if config['compression'] not in valid_compression:
                errors.append(
                    f"Invalid compression value: {config['compression']}. "
                    f"Must be one of: {', '.join(valid_compression)}"
                )
        
        # Validate pack_size if specified
        if 'pack_size' in config:
            pack_size = config['pack_size']
            if not isinstance(pack_size, int) or pack_size <= 0:
                errors.append(f"pack_size must be a positive integer, got: {pack_size}")
            elif pack_size < 4 * 1024 * 1024:  # 4MB minimum
                warnings.append(
                    f"pack_size {pack_size} is very small, may impact performance"
                )
        
        # Validate cache_dir if specified
        if 'cache_dir' in config:
            from pathlib import Path
            cache_dir = Path(config['cache_dir'])
            if not cache_dir.is_absolute():
                warnings.append(
                    f"cache_dir should be an absolute path: {cache_dir}"
                )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def supports_storage_type(self, storage_type: str) -> bool:
        """Check if Restic supports the storage type"""
        return storage_type.lower() in self.SUPPORTED_SCHEMES
    
    def get_supported_storage_backends(self) -> List[str]:
        """Get list of supported storage backends"""
        return self.SUPPORTED_SCHEMES.copy()
    
    def create_repository(self, uri: str, password: Optional[str] = None, **kwargs) -> BackupRepository:
        """
        Create a Restic repository instance.
        
        Args:
            uri: Repository URI
            password: Optional repository password
            **kwargs: Additional parameters (credential_manager, repository_name, etc.)
            
        Returns:
            BackupRepository instance
            
        Raises:
            EngineNotAvailableError: If Restic is not available
            EngineConfigurationError: If repository creation fails
        """
        if not self.is_available():
            raise EngineNotAvailableError(
                f"Restic engine is not available. Please install Restic {self.RESTIC_MIN_VERSION} or later."
            )
        
        # Validate URI
        validation = self.validate_uri(uri)
        if not validation.is_valid:
            raise EngineConfigurationError(
                f"Invalid repository URI: {', '.join(validation.errors)}"
            )
        
        try:
            # Parse URI to determine repository type
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower() if parsed.scheme else 'local'
            
            # Import appropriate repository class
            if scheme in ['local', 'file', '']:
                from ...restic.Repositories.local import LocalResticRepository
                repo_class = LocalResticRepository
            elif scheme == 's3':
                from ...restic.Repositories.s3 import S3ResticRepository
                repo_class = S3ResticRepository
            elif scheme == 'b2':
                from ...restic.Repositories.b2 import B2ResticRepository
                repo_class = B2ResticRepository
            else:
                raise EngineConfigurationError(
                    f"Unsupported URI scheme for Restic: {scheme}"
                )
            
            # Create repository instance
            if password:
                kwargs['password'] = password
            
            # Use from_parsed_uri if available
            if hasattr(repo_class, 'from_parsed_uri'):
                repository = repo_class.from_parsed_uri(parsed, **kwargs)
            else:
                repository = repo_class(uri, **kwargs)
            
            logger.info(f"Created Restic repository for URI: {uri}")
            return repository
            
        except ImportError as e:
            raise EngineConfigurationError(
                f"Failed to import Restic repository class: {e}"
            ) from e
        except Exception as e:
            raise EngineConfigurationError(
                f"Failed to create Restic repository: {e}"
            ) from e
    
    def validate_uri(self, uri: str) -> ValidationResult:
        """
        Validate a repository URI for Restic.
        
        Args:
            uri: Repository URI to validate
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        if not uri or not uri.strip():
            errors.append("Repository URI cannot be empty")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        try:
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower() if parsed.scheme else 'local'
            
            # Check if scheme is supported
            if scheme and scheme not in self.SUPPORTED_SCHEMES:
                errors.append(
                    f"Unsupported URI scheme: {scheme}. "
                    f"Supported schemes: {', '.join(self.SUPPORTED_SCHEMES)}"
                )
            
            # Validate scheme-specific requirements
            if scheme == 's3':
                if not parsed.netloc:
                    errors.append("S3 URI must include bucket name")
            elif scheme == 'b2':
                if not parsed.netloc:
                    errors.append("B2 URI must include bucket name")
            elif scheme == 'sftp':
                if not parsed.netloc:
                    errors.append("SFTP URI must include hostname")
            elif scheme in ['local', 'file', '']:
                # Local path validation
                if parsed.netloc and parsed.netloc != 'localhost':
                    warnings.append(
                        f"Local URI should not have network location: {parsed.netloc}"
                    )
            
        except Exception as e:
            errors.append(f"Failed to parse URI: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_default_configuration(self) -> Dict[str, Any]:
        """Get default Restic configuration"""
        return {
            'compression': 'auto',
            'exclude_caches': True,
            'one_file_system': False,
        }
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get JSON schema for Restic configuration"""
        return {
            'type': 'object',
            'properties': {
                'compression': {
                    'type': 'string',
                    'enum': ['auto', 'off', 'max'],
                    'default': 'auto',
                    'description': 'Compression level for backup data'
                },
                'pack_size': {
                    'type': 'integer',
                    'minimum': 4194304,  # 4MB
                    'description': 'Target pack size in bytes'
                },
                'cache_dir': {
                    'type': 'string',
                    'description': 'Custom cache directory path'
                },
                'exclude_caches': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Exclude cache directories from backup'
                },
                'one_file_system': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Stay within one filesystem during backup'
                }
            }
        }
