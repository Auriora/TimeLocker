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
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from urllib.parse import urlparse
import logging

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
    SUPPORTED_URI_SCHEMES = {'local', 'file', 's3', 'b2', 'azure', 'gcs', 'sftp', 'rest'}

    # Path validation patterns
    INVALID_PATH_CHARS = r'[<>:"|?*]' if os.name == 'nt' else r'[\x00]'

    def __init__(self):
        """Initialize validation service"""
        self._custom_validators: Dict[str, callable] = {}

    def register_custom_validator(self, name: str, validator: callable) -> None:
        """Register a custom validator function"""
        self._custom_validators[name] = validator
        logger.debug(f"Registered custom validator: {name}")

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
                if not parsed.netloc:
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


# Global instance for easy access
validation_service = ValidationService()
