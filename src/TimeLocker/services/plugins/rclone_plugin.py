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
Rclone Backup Engine Plugin

This module provides a plugin implementation for the Rclone backup engine,
enabling cloud storage synchronization with many provider integrations.
"""

import logging
import subprocess
import re
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from ...interfaces.backup_engine_plugin import (
    BackupEnginePlugin,
    BackupEngine,
    ValidationResult,
    EngineCapabilities,
    EngineNotAvailableError,
    EngineConfigurationError
)

logger = logging.getLogger(__name__)


class RcloneEnginePlugin(BackupEnginePlugin):
    """
    Plugin implementation for Rclone backup engine.
    
    Rclone provides cloud storage synchronization with support for many
    cloud providers and protocols.
    """
    
    # Rclone supports many backends - listing common ones
    SUPPORTED_SCHEMES = [
        'local', 'file',
        's3', 'b2', 'azure', 'gcs', 'dropbox', 'onedrive',
        'sftp', 'ftp', 'webdav', 'http',
        'drive',  # Google Drive
        'box', 'mega', 'pcloud', 'swift'
    ]
    
    def __init__(self):
        """Initialize Rclone plugin"""
        self._version: Optional[str] = None
        self._available: Optional[bool] = None
        logger.debug("RcloneEnginePlugin initialized")
    
    @property
    def engine_name(self) -> str:
        """Get engine name"""
        return "rclone"
    
    @property
    def engine_type(self) -> BackupEngine:
        """Get engine type"""
        return BackupEngine.RCLONE
    
    @property
    def engine_version(self) -> str:
        """Get Rclone version"""
        if self._version is None:
            self._detect_version()
        return self._version or "unknown"
    
    def is_available(self) -> bool:
        """Check if Rclone is available on the system"""
        if self._available is not None:
            return self._available
        
        try:
            self._detect_version()
            self._available = self._version is not None
            return self._available
        except Exception as e:
            logger.debug(f"Rclone not available: {e}")
            self._available = False
            return False
    
    def _detect_version(self) -> None:
        """Detect Rclone version from executable"""
        try:
            result = subprocess.run(
                ['rclone', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse version from output like "rclone v1.65.0"
                match = re.search(r'rclone\s+v?(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    self._version = match.group(1)
                    logger.debug(f"Detected Rclone version: {self._version}")
                    return
            
            logger.warning("Could not detect Rclone version")
            self._version = "unknown"
            
        except FileNotFoundError:
            logger.debug("Rclone executable not found in PATH")
            self._version = None
        except subprocess.TimeoutExpired:
            logger.warning("Rclone version check timed out")
            self._version = None
        except Exception as e:
            logger.warning(f"Error detecting Rclone version: {e}")
            self._version = None
    
    def get_capabilities(self) -> EngineCapabilities:
        """Get Rclone capabilities"""
        return EngineCapabilities(
            supports_encryption=True,  # Rclone supports crypt remote
            supports_deduplication=False,
            supports_compression=False,  # Depends on backend
            supports_snapshots=False,
            supports_incremental=True,
            supports_verification=True,
            supports_retention_policies=False,
            supports_tags=False,
            storage_backends=self.SUPPORTED_SCHEMES
        )
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate Rclone-specific configuration.
        
        Args:
            config: Configuration dictionary with Rclone-specific settings
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Validate transfers setting
        if 'transfers' in config:
            transfers = config['transfers']
            if not isinstance(transfers, int) or transfers <= 0:
                errors.append(f"transfers must be a positive integer, got: {transfers}")
            elif transfers > 32:
                warnings.append(
                    f"transfers value {transfers} is very high, may impact performance"
                )
        
        # Validate checkers setting
        if 'checkers' in config:
            checkers = config['checkers']
            if not isinstance(checkers, int) or checkers <= 0:
                errors.append(f"checkers must be a positive integer, got: {checkers}")
        
        # Validate buffer_size
        if 'buffer_size' in config:
            buffer_size = config['buffer_size']
            if not isinstance(buffer_size, str):
                errors.append(f"buffer_size must be a string (e.g., '16M'), got: {buffer_size}")
            elif not re.match(r'^\d+[KMG]?$', buffer_size):
                errors.append(
                    f"Invalid buffer_size format: {buffer_size}. "
                    "Use format like '16M', '256K', or '1G'"
                )
        
        # Validate config_file path if specified
        if 'config_file' in config:
            from pathlib import Path
            config_file = Path(config['config_file'])
            if not config_file.exists():
                warnings.append(
                    f"Rclone config file does not exist: {config_file}"
                )
        
        # Validate use_mmap
        if 'use_mmap' in config and not isinstance(config['use_mmap'], bool):
            errors.append("use_mmap must be a boolean value")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def supports_storage_type(self, storage_type: str) -> bool:
        """Check if Rclone supports the storage type"""
        return storage_type.lower() in self.SUPPORTED_SCHEMES
    
    def get_supported_storage_backends(self) -> List[str]:
        """Get list of supported storage backends"""
        return self.SUPPORTED_SCHEMES.copy()
    
    def create_repository(self, uri: str, password: Optional[str] = None, **kwargs) -> Any:
        """
        Create an Rclone repository instance.
        
        Note: Rclone uses "remotes" configured in its config file.
        This method validates the URI and returns a configuration object.
        
        Args:
            uri: Remote URI in format "remote:path"
            password: Optional password (for crypt remotes)
            **kwargs: Additional parameters
            
        Returns:
            Configuration object for rclone operations
            
        Raises:
            EngineNotAvailableError: If Rclone is not available
            EngineConfigurationError: If configuration is invalid
        """
        if not self.is_available():
            raise EngineNotAvailableError(
                "Rclone engine is not available. Please install rclone."
            )
        
        # Validate URI
        validation = self.validate_uri(uri)
        if not validation.is_valid:
            raise EngineConfigurationError(
                f"Invalid rclone URI: {', '.join(validation.errors)}"
            )
        
        # Return a configuration object
        # In a full implementation, this would return an RcloneRepository class
        logger.info(f"Created Rclone configuration for URI: {uri}")
        
        config = kwargs.get('engine_config', self.get_default_configuration())
        if password:
            config['password'] = password
        
        return {
            'engine': 'rclone',
            'uri': uri,
            'config': config
        }
    
    def validate_uri(self, uri: str) -> ValidationResult:
        """
        Validate a URI for Rclone.
        
        Args:
            uri: URI to validate
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        if not uri or not uri.strip():
            errors.append("URI cannot be empty")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        try:
            # Rclone URIs are typically in format "remote:path"
            # where "remote" is configured in rclone.conf
            
            if ':' in uri:
                parts = uri.split(':', 1)
                remote_name = parts[0]
                path = parts[1] if len(parts) > 1 else ''
                
                # Validate remote name format
                if not re.match(r'^[a-zA-Z0-9_-]+$', remote_name):
                    errors.append(
                        f"Invalid remote name: {remote_name}. "
                        "Remote names should contain only letters, numbers, hyphens, and underscores."
                    )
                
                # Check if path is provided
                if not path:
                    warnings.append(
                        f"No path specified after remote '{remote_name}:'. "
                        "Will use root of remote."
                    )
            else:
                # Local path
                from pathlib import Path
                path = Path(uri)
                if not path.is_absolute():
                    warnings.append(
                        f"Relative path provided: {uri}. "
                        "Consider using absolute paths or rclone remote format."
                    )
        
        except Exception as e:
            errors.append(f"Failed to parse URI: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_default_configuration(self) -> Dict[str, Any]:
        """Get default Rclone configuration"""
        return {
            'transfers': 4,
            'checkers': 8,
            'buffer_size': '16M',
            'use_mmap': False,
        }
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get JSON schema for Rclone configuration"""
        return {
            'type': 'object',
            'properties': {
                'config_file': {
                    'type': 'string',
                    'description': 'Path to rclone configuration file'
                },
                'transfers': {
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 32,
                    'default': 4,
                    'description': 'Number of file transfers to run in parallel'
                },
                'checkers': {
                    'type': 'integer',
                    'minimum': 1,
                    'default': 8,
                    'description': 'Number of checkers to run in parallel'
                },
                'buffer_size': {
                    'type': 'string',
                    'default': '16M',
                    'pattern': '^\\d+[KMG]?$',
                    'description': 'Buffer size for file transfers (e.g., 16M, 256K)'
                },
                'use_mmap': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Use memory mapped files for transfers'
                }
            }
        }
