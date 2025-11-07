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
Rsync Backup Engine Plugin

This module provides a plugin implementation for the Rsync backup engine,
enabling simple file synchronization without encryption or deduplication.
"""

import logging
import subprocess
import re
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


class RsyncEnginePlugin(BackupEnginePlugin):
    """
    Plugin implementation for Rsync backup engine.
    
    Rsync provides simple file synchronization with efficient delta transfer
    but without encryption, deduplication, or snapshot support.
    """
    
    SUPPORTED_SCHEMES = ['local', 'file', 'rsync', 'ssh']
    
    def __init__(self):
        """Initialize Rsync plugin"""
        self._version: Optional[str] = None
        self._available: Optional[bool] = None
        logger.debug("RsyncEnginePlugin initialized")
    
    @property
    def engine_name(self) -> str:
        """Get engine name"""
        return "rsync"
    
    @property
    def engine_type(self) -> BackupEngine:
        """Get engine type"""
        return BackupEngine.RSYNC
    
    @property
    def engine_version(self) -> str:
        """Get Rsync version"""
        if self._version is None:
            self._detect_version()
        return self._version or "unknown"
    
    def is_available(self) -> bool:
        """Check if Rsync is available on the system"""
        if self._available is not None:
            return self._available
        
        try:
            self._detect_version()
            self._available = self._version is not None
            return self._available
        except Exception as e:
            logger.debug(f"Rsync not available: {e}")
            self._available = False
            return False
    
    def _detect_version(self) -> None:
        """Detect Rsync version from executable"""
        try:
            result = subprocess.run(
                ['rsync', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse version from output like "rsync  version 3.2.7  protocol version 31"
                match = re.search(r'rsync\s+version\s+(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    self._version = match.group(1)
                    logger.debug(f"Detected Rsync version: {self._version}")
                    return
            
            logger.warning("Could not detect Rsync version")
            self._version = "unknown"
            
        except FileNotFoundError:
            logger.debug("Rsync executable not found in PATH")
            self._version = None
        except subprocess.TimeoutExpired:
            logger.warning("Rsync version check timed out")
            self._version = None
        except Exception as e:
            logger.warning(f"Error detecting Rsync version: {e}")
            self._version = None
    
    def get_capabilities(self) -> EngineCapabilities:
        """Get Rsync capabilities"""
        return EngineCapabilities(
            supports_encryption=False,
            supports_deduplication=False,
            supports_compression=True,
            supports_snapshots=False,
            supports_incremental=True,
            supports_verification=True,
            supports_retention_policies=False,
            supports_tags=False,
            storage_backends=self.SUPPORTED_SCHEMES
        )
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate Rsync-specific configuration.
        
        Args:
            config: Configuration dictionary with Rsync-specific settings
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Validate boolean options
        bool_options = [
            'archive_mode', 'compress', 'delete_excluded',
            'preserve_permissions', 'preserve_times', 'dry_run'
        ]
        
        for option in bool_options:
            if option in config and not isinstance(config[option], bool):
                errors.append(f"{option} must be a boolean value")
        
        # Warn about dry_run mode
        if config.get('dry_run', False):
            warnings.append(
                "dry_run mode is enabled - no actual changes will be made"
            )
        
        # Validate exclude patterns if present
        if 'exclude_patterns' in config:
            if not isinstance(config['exclude_patterns'], list):
                errors.append("exclude_patterns must be a list")
            else:
                for pattern in config['exclude_patterns']:
                    if not isinstance(pattern, str):
                        errors.append(f"Invalid exclude pattern (must be string): {pattern}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def supports_storage_type(self, storage_type: str) -> bool:
        """Check if Rsync supports the storage type"""
        return storage_type.lower() in self.SUPPORTED_SCHEMES
    
    def get_supported_storage_backends(self) -> List[str]:
        """Get list of supported storage backends"""
        return self.SUPPORTED_SCHEMES.copy()
    
    def create_repository(self, uri: str, password: Optional[str] = None, **kwargs) -> Any:
        """
        Create an Rsync repository instance.
        
        Note: Rsync doesn't have a traditional "repository" concept.
        This method validates the URI and returns a configuration object
        that can be used for rsync operations.
        
        Args:
            uri: Destination URI for rsync
            password: Not used for rsync (SSH keys should be used instead)
            **kwargs: Additional parameters
            
        Returns:
            Configuration object for rsync operations
            
        Raises:
            EngineNotAvailableError: If Rsync is not available
            EngineConfigurationError: If configuration is invalid
        """
        if not self.is_available():
            raise EngineNotAvailableError(
                "Rsync engine is not available. Please install rsync."
            )
        
        # Validate URI
        validation = self.validate_uri(uri)
        if not validation.is_valid:
            raise EngineConfigurationError(
                f"Invalid rsync URI: {', '.join(validation.errors)}"
            )
        
        if password:
            logger.warning(
                "Password provided for rsync, but rsync typically uses SSH keys. "
                "Password will be ignored."
            )
        
        # Return a simple configuration object
        # In a full implementation, this would return an RsyncRepository class
        logger.info(f"Created Rsync configuration for URI: {uri}")
        
        return {
            'engine': 'rsync',
            'uri': uri,
            'config': kwargs.get('engine_config', self.get_default_configuration())
        }
    
    def validate_uri(self, uri: str) -> ValidationResult:
        """
        Validate a URI for Rsync.
        
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
            # Rsync supports several URI formats:
            # - /local/path
            # - user@host:/remote/path
            # - rsync://user@host/module/path
            # - ssh://user@host/path
            
            if '://' in uri:
                # URL format
                parsed = urlparse(uri)
                scheme = parsed.scheme.lower()
                
                if scheme not in self.SUPPORTED_SCHEMES:
                    errors.append(
                        f"Unsupported URI scheme: {scheme}. "
                        f"Supported schemes: {', '.join(self.SUPPORTED_SCHEMES)}"
                    )
                
                if scheme in ['rsync', 'ssh'] and not parsed.netloc:
                    errors.append(f"{scheme.upper()} URI must include hostname")
                    
            elif ':' in uri and not uri.startswith('/'):
                # SSH-style format: user@host:path
                if '@' not in uri.split(':')[0]:
                    warnings.append(
                        "SSH-style URI without username - will use current user"
                    )
            else:
                # Local path
                from pathlib import Path
                path = Path(uri)
                if not path.is_absolute():
                    warnings.append(
                        f"Relative path provided: {uri}. "
                        "Consider using absolute paths for clarity."
                    )
        
        except Exception as e:
            errors.append(f"Failed to parse URI: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def get_default_configuration(self) -> Dict[str, Any]:
        """Get default Rsync configuration"""
        return {
            'archive_mode': True,
            'compress': True,
            'delete_excluded': False,
            'preserve_permissions': True,
            'preserve_times': True,
            'dry_run': False,
        }
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get JSON schema for Rsync configuration"""
        return {
            'type': 'object',
            'properties': {
                'archive_mode': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Enable archive mode (recursive, preserve attributes)'
                },
                'compress': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Compress data during transfer'
                },
                'delete_excluded': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Delete excluded files from destination'
                },
                'preserve_permissions': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Preserve file permissions'
                },
                'preserve_times': {
                    'type': 'boolean',
                    'default': True,
                    'description': 'Preserve modification times'
                },
                'dry_run': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Perform a trial run with no changes made'
                },
                'exclude_patterns': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Patterns to exclude from sync'
                }
            }
        }
