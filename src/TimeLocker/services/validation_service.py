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

import os
import re
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from urllib.parse import urlparse
from datetime import datetime
import logging

from ..interfaces.repository_management_models import (
    Repository, RepositoryConfig, ValidationResult as RepoValidationResult,
    ConnectivityResult, IntegrityResult, ConfigValidationResult,
    ConnectivityStatus, IntegrityStatus, BackupEngine, RepositoryType
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors"""
    pass


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


class ValidationService:
    """
    Centralized validation service following Single Responsibility Principle.
    
    This service provides consistent validation logic across the TimeLocker
    codebase, eliminating duplication and ensuring consistent error messages.
    """

    # Common file patterns for validation
    SUPPORTED_URI_SCHEMES = {'local', 'file', 's3', 'b2', 'azure', 'gcs', 'sftp', 'rest', 'smb', 'nfs'}

    # Path validation patterns
    INVALID_PATH_CHARS = r'[<>:"|?*]' if os.name == 'nt' else r'[\x00]'
    
    # Performance thresholds (in seconds)
    NETWORK_VALIDATION_THRESHOLD = 15.0
    LOCAL_VALIDATION_THRESHOLD = 3.0
    
    # URI validation patterns
    URI_PATTERNS = {
        'local': re.compile(r'^file://(.+)$'),
        's3': re.compile(r'^s3:(?:https?://)?([^/]+)/(.+)$'),
        'b2': re.compile(r'^b2:([^/]+)/(.+)$'),
        'sftp': re.compile(r'^sftp://([^@]+@)?([^:]+)(?::(\d+))?/(.+)$'),
        'smb': re.compile(r'^smb://([^/]+)/(.+)$'),
        'nfs': re.compile(r'^nfs://([^/]+)/(.+)$'),
    }

    def __init__(self):
        """Initialize validation service"""
        self._custom_validators: Dict[str, callable] = {}

    def register_custom_validator(self, name: str, validator: callable) -> None:
        """Register a custom validator function"""
        self._custom_validators[name] = validator
        logger.debug(f"Registered custom validator: {name}")

    def validate_snapshot_id(self, snapshot_id: str) -> None:
        """
        Validate snapshot ID format.

        Args:
            snapshot_id: The snapshot ID to validate

        Raises:
            ValueError: If snapshot ID format is invalid
        """
        from ..utils.snapshot_validation import validate_snapshot_id_format
        validate_snapshot_id_format(snapshot_id, allow_latest=False)

    def validate_path(self, path: Union[str, Path], must_exist: bool = False) -> ValidationResult:
        """
        Validate a file system path
        
        Args:
            path: Path to validate
            must_exist: Whether the path must exist
            
        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        if not path:
            result.add_error("Path cannot be empty")
            return result

        path_str = str(path)

        # Check for invalid characters
        if re.search(self.INVALID_PATH_CHARS, path_str):
            result.add_error(f"Path contains invalid characters: {path_str}")

        # Check path length (Windows has 260 char limit, Unix typically 4096)
        max_length = 260 if os.name == 'nt' else 4096
        if len(path_str) > max_length:
            result.add_error(f"Path too long ({len(path_str)} > {max_length}): {path_str}")

        # Check if path exists when required
        if must_exist:
            path_obj = Path(path_str)
            if not path_obj.exists():
                result.add_error(f"Path does not exist: {path_str}")
            elif not path_obj.is_dir() and not path_obj.is_file():
                result.add_warning(f"Path is neither file nor directory: {path_str}")

        return result

    def validate_repository_uri(self, uri: str) -> ValidationResult:
        """
        Validate a repository URI
        
        Args:
            uri: Repository URI to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        if not uri:
            result.add_error("Repository URI cannot be empty")
            return result

        try:
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower()

            # Validate scheme
            if scheme and scheme not in self.SUPPORTED_URI_SCHEMES:
                result.add_error(f"Unsupported URI scheme: {scheme}")

            # Validate local/file URIs
            if scheme in {'local', 'file', ''}:
                if not parsed.path:
                    result.add_error("Local repository URI must have a path")
                else:
                    # Validate the path component
                    path_result = self.validate_path(parsed.path, must_exist=False)
                    result.errors.extend(path_result.errors)
                    result.warnings.extend(path_result.warnings)
                    if path_result.has_errors():
                        result.is_valid = False

            # Validate remote URIs
            elif scheme in {'s3', 'b2', 'azure', 'gcs'}:
                # Support both standard format (s3://host/bucket) and restic format (s3:host/bucket)
                # Standard format has netloc, restic format has everything in path
                if not parsed.netloc and not parsed.path:
                    result.add_error(f"{scheme.upper()} URI must have a hostname/bucket")

        except Exception as e:
            result.add_error(f"Invalid URI format: {e}")

        return result

    def validate_backup_target_config(self, config: Dict[str, Any], strict_path_validation: bool = False) -> ValidationResult:
        """
        Validate backup target configuration

        Args:
            config: Backup target configuration dictionary
            strict_path_validation: If True, missing paths are errors; if False, they are warnings

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # Required fields
        required_fields = ['name', 'paths']
        for field in required_fields:
            if field not in config:
                result.add_error(f"Missing required field: {field}")

        # Validate name
        if 'name' in config:
            name = config['name']
            if not name or not isinstance(name, str):
                result.add_error("Backup target name must be a non-empty string")
            elif len(name.strip()) == 0:
                result.add_error("Backup target name cannot be empty or whitespace")

        # Validate paths
        if 'paths' in config:
            paths = config['paths']
            if not isinstance(paths, list):
                result.add_error("Backup target paths must be a list")
            elif len(paths) == 0:
                result.add_error("Backup target must have at least one path")
            else:
                for i, path in enumerate(paths):
                    # Use must_exist=False for backup targets during configuration loading
                    # Missing paths should be warnings, not errors, as they might be temporarily unavailable
                    path_result = self.validate_path(path, must_exist=False)
                    if path_result.has_errors():
                        for error in path_result.errors:
                            result.add_error(f"Path {i + 1}: {error}")
                    if path_result.has_warnings():
                        for warning in path_result.warnings:
                            result.add_warning(f"Path {i + 1}: {warning}")

                    # Handle non-existent paths based on validation mode
                    from pathlib import Path
                    if not Path(path).exists():
                        if strict_path_validation:
                            result.add_error(f"Path {i + 1}: Path does not exist: {path}")
                        else:
                            result.add_warning(f"Path {i + 1}: Path does not exist: {path}")

        # Validate optional fields
        if 'include_patterns' in config:
            patterns = config['include_patterns']
            if not isinstance(patterns, list):
                result.add_error("Include patterns must be a list")

        if 'exclude_patterns' in config:
            patterns = config['exclude_patterns']
            if not isinstance(patterns, list):
                result.add_error("Exclude patterns must be a list")

        return result

    def validate_backup_target_config_for_loading(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate backup target configuration during configuration loading.
        This version logs warnings to files only, not to console.

        Args:
            config: Backup target configuration dictionary

        Returns:
            ValidationResult with validation status and messages
        """
        import logging

        # Get the validation result
        result = self.validate_backup_target_config(config, strict_path_validation=False)

        # Log warnings to file only (not to console)
        if result.has_warnings():
            logger = logging.getLogger(__name__)
            target_name = config.get('name', 'unknown')
            for warning in result.warnings:
                # Log at DEBUG level to avoid console display
                logger.debug(f"Configuration validation warning for target '{target_name}': {warning}")

        return result

    def validate_repository_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate repository configuration
        
        Args:
            config: Repository configuration dictionary
            
        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        # Required fields
        required_fields = ['name', 'uri']
        for field in required_fields:
            if field not in config:
                result.add_error(f"Missing required field: {field}")

        # Validate name
        if 'name' in config:
            name = config['name']
            if not name or not isinstance(name, str):
                result.add_error("Repository name must be a non-empty string")
            elif len(name.strip()) == 0:
                result.add_error("Repository name cannot be empty or whitespace")

        # Validate URI
        if 'uri' in config:
            uri_result = self.validate_repository_uri(config['uri'])
            result.errors.extend(uri_result.errors)
            result.warnings.extend(uri_result.warnings)
            if uri_result.has_errors():
                result.is_valid = False

        return result

    def validate_with_custom(self, validator_name: str, data: Any) -> ValidationResult:
        """
        Validate using a custom registered validator
        
        Args:
            validator_name: Name of the registered validator
            data: Data to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        if validator_name not in self._custom_validators:
            result = ValidationResult(is_valid=False, errors=[], warnings=[])
            result.add_error(f"Unknown validator: {validator_name}")
            return result

        try:
            return self._custom_validators[validator_name](data)
        except Exception as e:
            result = ValidationResult(is_valid=False, errors=[], warnings=[])
            result.add_error(f"Validation error: {e}")
            return result

    # Enhanced Repository Validation Methods

    def validate_repository_uri_comprehensive(self, uri: str) -> ConfigValidationResult:
        """
        Comprehensive repository URI validation for all supported schemes
        
        Args:
            uri: Repository URI to validate
            
        Returns:
            ConfigValidationResult with detailed validation information
        """
        result = ConfigValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])

        if not uri:
            result.errors.append("Repository URI cannot be empty")
            result.is_valid = False
            return result

        try:
            parsed = urlparse(uri)
            scheme = parsed.scheme.lower() if parsed.scheme else 'local'

            # Validate scheme
            if scheme not in self.SUPPORTED_URI_SCHEMES:
                result.errors.append(f"Unsupported URI scheme: {scheme}")
                result.suggestions.append(f"Supported schemes: {', '.join(sorted(self.SUPPORTED_URI_SCHEMES))}")
                result.is_valid = False
                return result

            # Scheme-specific validation
            if scheme in {'local', 'file', ''}:
                self._validate_local_uri(parsed, result)
            elif scheme == 's3':
                self._validate_s3_uri(parsed, result)
            elif scheme == 'b2':
                self._validate_b2_uri(parsed, result)
            elif scheme == 'sftp':
                self._validate_sftp_uri(parsed, result)
            elif scheme in {'smb', 'nfs'}:
                self._validate_network_uri(parsed, result, scheme)

        except Exception as e:
            result.errors.append(f"Invalid URI format: {e}")
            result.is_valid = False

        return result

    def _validate_local_uri(self, parsed, result: ConfigValidationResult) -> None:
        """Validate local/file URI"""
        if not parsed.path:
            result.errors.append("Local repository URI must have a path")
            result.is_valid = False
        else:
            path = Path(parsed.path)
            if not path.is_absolute():
                result.warnings.append("Relative paths may cause issues; consider using absolute paths")
            
            # Check parent directory exists
            if not path.parent.exists():
                result.errors.append(f"Parent directory does not exist: {path.parent}")
                result.is_valid = False
            elif not os.access(path.parent, os.W_OK):
                result.errors.append(f"No write permission to parent directory: {path.parent}")
                result.is_valid = False

    def _validate_s3_uri(self, parsed, result: ConfigValidationResult) -> None:
        """Validate S3 URI"""
        # Handle both s3://bucket/path and s3:endpoint/bucket/path formats
        if parsed.netloc:
            # Standard format: s3://bucket/path
            bucket = parsed.netloc
            path = parsed.path.lstrip('/')
        else:
            # Restic format: s3:endpoint/bucket/path
            parts = parsed.path.lstrip('/').split('/', 2)
            if len(parts) < 2:
                result.errors.append("S3 URI must specify endpoint and bucket")
                result.is_valid = False
                return
            bucket = parts[1]

        if not bucket:
            result.errors.append("S3 URI must specify a bucket name")
            result.is_valid = False
        elif not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', bucket):
            result.errors.append("Invalid S3 bucket name format")
            result.suggestions.append("Bucket names must be 3-63 characters, lowercase, start/end with alphanumeric")
            result.is_valid = False

    def _validate_b2_uri(self, parsed, result: ConfigValidationResult) -> None:
        """Validate Backblaze B2 URI"""
        # Format: b2:bucket/path
        parts = parsed.path.lstrip('/').split('/', 1)
        if not parts or not parts[0]:
            result.errors.append("B2 URI must specify a bucket name")
            result.is_valid = False
        else:
            bucket = parts[0]
            if not re.match(r'^[a-zA-Z0-9\-]+$', bucket):
                result.errors.append("Invalid B2 bucket name format")
                result.suggestions.append("B2 bucket names must contain only letters, numbers, and hyphens")
                result.is_valid = False

    def _validate_sftp_uri(self, parsed, result: ConfigValidationResult) -> None:
        """Validate SFTP URI"""
        if not parsed.hostname:
            result.errors.append("SFTP URI must specify a hostname")
            result.is_valid = False
        
        if parsed.port and (parsed.port < 1 or parsed.port > 65535):
            result.errors.append(f"Invalid SFTP port: {parsed.port}")
            result.is_valid = False
        
        if not parsed.path or parsed.path == '/':
            result.warnings.append("SFTP URI should specify a path for the repository")

    def _validate_network_uri(self, parsed, result: ConfigValidationResult, scheme: str) -> None:
        """Validate SMB/NFS URI"""
        if not parsed.hostname:
            result.errors.append(f"{scheme.upper()} URI must specify a hostname")
            result.is_valid = False
        
        if not parsed.path or parsed.path == '/':
            result.errors.append(f"{scheme.upper()} URI must specify a share/export path")
            result.is_valid = False

    async def validate_connectivity(self, repo: Repository) -> ConnectivityResult:
        """
        Test repository connectivity with timeout handling
        
        Args:
            repo: Repository to test connectivity for
            
        Returns:
            ConnectivityResult with connectivity status and metrics
        """
        start_time = time.time()
        
        try:
            # Determine if this is a network or local repository
            is_network = self._is_network_repository(repo.config.uri)
            timeout = self.NETWORK_VALIDATION_THRESHOLD if is_network else self.LOCAL_VALIDATION_THRESHOLD
            
            # Perform connectivity test with timeout
            success = await asyncio.wait_for(
                self._test_repository_connectivity(repo),
                timeout=timeout
            )
            
            response_time = time.time() - start_time
            
            if success:
                status = ConnectivityStatus.CONNECTED
                return ConnectivityResult(
                    success=True,
                    status=status,
                    response_time=response_time
                )
            else:
                return ConnectivityResult(
                    success=False,
                    status=ConnectivityStatus.DISCONNECTED,
                    response_time=response_time,
                    error_message="Repository is not accessible"
                )
                
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return ConnectivityResult(
                success=False,
                status=ConnectivityStatus.TIMEOUT,
                response_time=response_time,
                error_message=f"Connection timeout after {timeout}s"
            )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            recommendations = []
            
            # Determine appropriate status based on error type
            status = ConnectivityStatus.UNKNOWN
            if "Connection refused" in error_msg or "ConnectionRefusedError" in str(type(e).__name__):
                status = ConnectivityStatus.UNREACHABLE
                recommendations.append("Check if the repository service is running")
                recommendations.append("Verify the repository URL and port are correct")
            elif "Name or service not known" in error_msg or "getaddrinfo failed" in error_msg:
                status = ConnectivityStatus.UNREACHABLE
                recommendations.append("Check DNS configuration and network connectivity")
                recommendations.append("Verify the repository hostname is correct")
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                status = ConnectivityStatus.AUTHENTICATION_FAILED
                recommendations.append("Verify repository credentials are correct")
                recommendations.append("Check if credentials need to be refreshed")
            elif "certificate" in error_msg.lower() or "ssl" in error_msg.lower():
                recommendations.append("Verify SSL/TLS certificate is valid and trusted")
                recommendations.append("Consider using --insecure-tls flag if certificate is self-signed")
                recommendations.append("Check system certificate store is up to date")
            
            return ConnectivityResult(
                success=False,
                status=status,
                response_time=response_time,
                error_message=error_msg,
                recommendations=recommendations
            )

    async def validate_integrity(self, repo: Repository) -> IntegrityResult:
        """
        Check repository integrity
        
        Args:
            repo: Repository to check integrity for
            
        Returns:
            IntegrityResult with integrity status and any issues found
        """
        try:
            # Perform basic integrity checks based on engine type
            if repo.config.engine == BackupEngine.RESTIC:
                return await self._validate_restic_integrity(repo)
            else:
                # For other engines, perform basic checks
                return IntegrityResult(
                    success=True,
                    status=IntegrityStatus.UNKNOWN,
                    issues_found=[],
                    repair_suggestions=["Integrity checking not implemented for this engine type"]
                )
                
        except Exception as e:
            return IntegrityResult(
                success=False,
                status=IntegrityStatus.UNKNOWN,
                issues_found=[f"Integrity check failed: {e}"],
                repair_suggestions=["Check repository accessibility and try again"]
            )

    def validate_repository_configuration(self, config: RepositoryConfig) -> ConfigValidationResult:
        """
        Comprehensive repository configuration validation
        
        Args:
            config: Repository configuration to validate
            
        Returns:
            ConfigValidationResult with detailed validation information
        """
        result = ConfigValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])

        # Validate basic fields
        if not config.name or not config.name.strip():
            result.errors.append("Repository name cannot be empty")
            result.is_valid = False
        elif not re.match(r'^[a-zA-Z0-9_-]+$', config.name):
            result.errors.append("Repository name must contain only letters, numbers, underscores, and hyphens")
            result.is_valid = False

        # Validate URI
        uri_result = self.validate_repository_uri_comprehensive(config.uri)
        result.errors.extend(uri_result.errors)
        result.warnings.extend(uri_result.warnings)
        result.suggestions.extend(uri_result.suggestions)
        if not uri_result.is_valid:
            result.is_valid = False

        # Validate engine configuration
        if config.engine_config:
            engine_result = self._validate_engine_configuration(config.engine, config.engine_config)
            result.errors.extend(engine_result.errors)
            result.warnings.extend(engine_result.warnings)
            result.suggestions.extend(engine_result.suggestions)
            if not engine_result.is_valid:
                result.is_valid = False

        return result

    async def batch_validate(self, repos: List[Repository]) -> List[RepoValidationResult]:
        """
        Validate multiple repositories with performance monitoring
        
        Args:
            repos: List of repositories to validate
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        for repo in repos:
            start_time = time.time()
            
            # Perform connectivity and integrity checks
            connectivity_result = await self.validate_connectivity(repo)
            integrity_result = await self.validate_integrity(repo)
            
            # Create comprehensive validation result
            validation_result = RepoValidationResult(
                success=connectivity_result.success and integrity_result.success,
                timestamp=datetime.utcnow(),
                connectivity_status=connectivity_result.status,
                integrity_status=integrity_result.status
            )
            
            # Add performance metrics
            total_time = time.time() - start_time
            validation_result.performance_metrics['total_validation_time'] = total_time
            validation_result.performance_metrics['connectivity_time'] = connectivity_result.response_time or 0
            
            # Add errors and recommendations
            if not connectivity_result.success:
                validation_result.add_error(f"Connectivity failed: {connectivity_result.error_message}")
            
            if not integrity_result.success:
                validation_result.error_details.extend(integrity_result.issues_found)
            
            # Performance warnings
            is_network = self._is_network_repository(repo.config.uri)
            threshold = self.NETWORK_VALIDATION_THRESHOLD if is_network else self.LOCAL_VALIDATION_THRESHOLD
            
            if total_time > threshold:
                validation_result.add_recommendation(
                    f"Validation took {total_time:.1f}s (threshold: {threshold}s). "
                    f"Consider checking {'network connectivity' if is_network else 'disk performance'}"
                )
            
            results.append(validation_result)
        
        return results

    def _is_network_repository(self, uri: str) -> bool:
        """Check if repository is network-based"""
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'local'
        return scheme in {'s3', 'b2', 'sftp', 'smb', 'nfs', 'azure', 'gcs'}

    async def _test_repository_connectivity(self, repo: Repository) -> bool:
        """
        Test basic repository connectivity
        
        This is a placeholder implementation. In a real system, this would
        perform actual connectivity tests based on the repository type.
        """
        # For local repositories, check if path exists and is accessible
        if repo.config.type == RepositoryType.LOCAL:
            parsed = urlparse(repo.config.uri)
            path = Path(parsed.path if parsed.path else repo.config.uri)
            return path.exists() or path.parent.exists()
        
        # For network repositories, this would perform actual network tests
        # For now, simulate a basic check
        await asyncio.sleep(0.1)  # Simulate network delay
        return True

    async def _validate_restic_integrity(self, repo: Repository) -> IntegrityResult:
        """
        Validate Restic repository integrity
        
        This is a placeholder implementation. In a real system, this would
        run restic check commands.
        """
        # Simulate integrity check
        await asyncio.sleep(0.2)
        
        return IntegrityResult(
            success=True,
            status=IntegrityStatus.VALID,
            issues_found=[],
            repair_suggestions=[]
        )

    def _validate_engine_configuration(self, engine: BackupEngine, config: Dict[str, Any]) -> ConfigValidationResult:
        """
        Validate engine-specific configuration
        
        Args:
            engine: Backup engine type
            config: Engine configuration dictionary
            
        Returns:
            ConfigValidationResult with validation status
        """
        result = ConfigValidationResult(is_valid=True, errors=[], warnings=[], suggestions=[])

        if engine == BackupEngine.RESTIC:
            self._validate_restic_config(config, result)
        elif engine == BackupEngine.RSYNC:
            self._validate_rsync_config(config, result)
        elif engine == BackupEngine.RCLONE:
            self._validate_rclone_config(config, result)

        return result

    def _validate_restic_config(self, config: Dict[str, Any], result: ConfigValidationResult) -> None:
        """Validate Restic engine configuration"""
        if 'compression' in config:
            compression = config['compression']
            valid_compression = {'auto', 'off', 'max'}
            if compression not in valid_compression:
                result.errors.append(f"Invalid compression setting: {compression}")
                result.suggestions.append(f"Valid options: {', '.join(valid_compression)}")
                result.is_valid = False

        if 'pack_size' in config and config['pack_size'] is not None:
            pack_size = config['pack_size']
            if not isinstance(pack_size, int) or pack_size <= 0:
                result.errors.append("Pack size must be a positive integer")
                result.is_valid = False

    def _validate_rsync_config(self, config: Dict[str, Any], result: ConfigValidationResult) -> None:
        """Validate Rsync engine configuration"""
        # Validate boolean options
        bool_options = ['archive_mode', 'compress', 'delete_excluded', 'preserve_permissions', 'preserve_times', 'dry_run']
        for option in bool_options:
            if option in config and not isinstance(config[option], bool):
                result.errors.append(f"{option} must be a boolean value")
                result.is_valid = False

    def _validate_rclone_config(self, config: Dict[str, Any], result: ConfigValidationResult) -> None:
        """Validate Rclone engine configuration"""
        if 'transfers' in config:
            transfers = config['transfers']
            if not isinstance(transfers, int) or transfers <= 0:
                result.errors.append("Transfers must be a positive integer")
                result.is_valid = False

        if 'checkers' in config:
            checkers = config['checkers']
            if not isinstance(checkers, int) or checkers <= 0:
                result.errors.append("Checkers must be a positive integer")
                result.is_valid = False

        if 'buffer_size' in config:
            buffer_size = config['buffer_size']
            if not isinstance(buffer_size, str) or not re.match(r'^\d+[KMG]?$', buffer_size):
                result.errors.append("Buffer size must be in format like '16M', '1G', etc.")
                result.is_valid = False


# Global instance for easy access
validation_service = ValidationService()
