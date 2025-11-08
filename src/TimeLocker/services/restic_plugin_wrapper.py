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
Restic Plugin Wrapper

This module provides a plugin wrapper for Restic backup tool, wrapping
existing Restic functionality with enhanced capabilities and standardized
interfaces for the backup orchestration layer.
"""

import logging
import re
import subprocess
import json
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from .plugin_wrapper import (
    PluginWrapper,
    BackupConfig,
    PluginWrapperError,
    CapabilityNotSupportedError
)
from ..interfaces.data_models import BackupResult, BackupStatus
from .tool_manager import Feature
from ..backup_target import BackupTarget
from ..file_selections import FileSelection

logger = logging.getLogger(__name__)


class ResticPluginWrapper(PluginWrapper):
    """
    Plugin wrapper for Restic backup tool.
    
    This wrapper provides:
    - Standardized interface for Restic operations
    - Enhanced pattern matching (regex translation)
    - Improved error handling and reporting
    - Progress monitoring integration
    - Capability gap filling where needed
    """
    
    def __init__(self):
        """Initialize Restic plugin wrapper"""
        super().__init__("restic")
        self._restic_repository = None
        logger.debug("ResticPluginWrapper initialized")
    
    def get_native_capabilities(self) -> Set[Feature]:
        """
        Get capabilities natively supported by Restic.
        
        Returns:
            Set of natively supported features
        """
        return {
            Feature.INCREMENTAL_BACKUP,
            Feature.FULL_BACKUP,
            Feature.INTEGRITY_VERIFICATION,
            Feature.CHECKSUM_VALIDATION,
            Feature.DATA_DEDUPLICATION,
            Feature.PARALLEL_PROCESSING,
            Feature.COMPRESSION,
            Feature.BANDWIDTH_LIMITING,
            Feature.ENCRYPTION,
            Feature.ENCRYPTION_AT_REST,
            Feature.INCLUDE_PATTERNS,
            Feature.EXCLUDE_PATTERNS,
            Feature.SNAPSHOT_TAGGING,
            Feature.SNAPSHOT_METADATA,
            Feature.SNAPSHOT_COMPARISON,
            Feature.REPOSITORY_LOCKING,
            Feature.REPOSITORY_VERIFICATION,
            Feature.RESUME_SUPPORT,
            Feature.PROGRESS_REPORTING,
            Feature.DRY_RUN
        }
    
    def get_wrapper_capabilities(self) -> Set[Feature]:
        """
        Get capabilities provided by the wrapper.
        
        Returns:
            Set of wrapper-provided features
        """
        return {
            Feature.REGEX_PATTERNS,  # Wrapper translates regex to Restic patterns
            Feature.MULTI_REPOSITORY  # Wrapper can coordinate multi-repo operations
        }
    
    def execute_backup(self, config: BackupConfig) -> BackupResult:
        """
        Execute backup using Restic with standardized interface.
        
        Args:
            config: Standardized backup configuration
            
        Returns:
            BackupResult with operation results
            
        Raises:
            PluginWrapperError: If backup execution fails
        """
        logger.info(f"Executing Restic backup for {len(config.source_paths)} paths")
        
        # Validate configuration
        validation = self.validate_configuration(config)
        if not validation['is_valid']:
            raise PluginWrapperError(
                f"Invalid configuration: {', '.join(validation['errors'])}"
            )
        
        try:
            # Create backup target from configuration
            targets = self._create_backup_targets(config)
            
            # Get or create Restic repository
            repository = self._get_repository(config)
            
            # Execute backup using existing Restic functionality
            result_data = repository.backup_target(targets, tags=config.tags)
            
            # Convert to standardized BackupResult
            return self._convert_restic_result(result_data, config)
            
        except Exception as e:
            logger.error(f"Restic backup failed: {e}")
            return self._create_backup_result(
                status=BackupStatus.FAILED,
                errors=[str(e)]
            )
    
    def validate_configuration(self, config: BackupConfig) -> Dict[str, Any]:
        """
        Validate backup configuration for Restic.
        
        Args:
            config: Backup configuration to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        # Validate source paths
        if not config.source_paths:
            errors.append("At least one source path must be specified")
        else:
            for path in config.source_paths:
                if not Path(path).exists():
                    warnings.append(f"Source path does not exist: {path}")
        
        # Validate repository URI
        if not config.repository_uri:
            errors.append("Repository URI must be specified")
        
        # Validate tool configuration
        if config.tool_configuration:
            tool_config = config.tool_configuration
            
            # Validate parallel operations
            if tool_config.parallel_operations < 1:
                errors.append("parallel_operations must be >= 1")
            elif tool_config.parallel_operations > 16:
                warnings.append(
                    f"parallel_operations {tool_config.parallel_operations} is very high, "
                    "may impact system performance"
                )
            
            # Validate compression level
            if tool_config.compression_level is not None:
                if not (0 <= tool_config.compression_level <= 9):
                    errors.append("compression_level must be between 0 and 9")
            
            # Validate bandwidth limit
            if tool_config.bandwidth_limit is not None:
                if tool_config.bandwidth_limit <= 0:
                    errors.append("bandwidth_limit must be positive")
        
        # Check for regex patterns that need translation
        regex_patterns = self._detect_regex_patterns(
            config.include_patterns + config.exclude_patterns
        )
        if regex_patterns:
            warnings.append(
                f"Found {len(regex_patterns)} regex patterns that will be "
                "translated to Restic glob patterns"
            )
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def translate_selection_rules(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        """
        Translate data selection rules to Restic-specific format.
        
        Restic uses glob patterns, so this method translates regex patterns
        to glob patterns where possible.
        
        Args:
            include_patterns: Include patterns in TimeLocker format
            exclude_patterns: Exclude patterns in TimeLocker format
            
        Returns:
            Dictionary with Restic-specific patterns
        """
        logger.debug(
            f"Translating {len(include_patterns)} include and "
            f"{len(exclude_patterns)} exclude patterns"
        )
        
        translated_include = []
        translated_exclude = []
        unsupported = []
        
        # Translate include patterns
        for pattern in include_patterns:
            translated = self._translate_pattern(pattern)
            if translated:
                translated_include.append(translated)
            else:
                unsupported.append(pattern)
                logger.warning(f"Could not translate include pattern: {pattern}")
        
        # Translate exclude patterns
        for pattern in exclude_patterns:
            translated = self._translate_pattern(pattern)
            if translated:
                translated_exclude.append(translated)
            else:
                unsupported.append(pattern)
                logger.warning(f"Could not translate exclude pattern: {pattern}")
        
        logger.info(
            f"Translated patterns: {len(translated_include)} include, "
            f"{len(translated_exclude)} exclude, {len(unsupported)} unsupported"
        )
        
        return {
            'include': translated_include,
            'exclude': translated_exclude,
            'unsupported': unsupported
        }
    
    def _translate_pattern(self, pattern: str) -> Optional[str]:
        """
        Translate a single pattern from regex to Restic glob format.
        
        Args:
            pattern: Pattern to translate
            
        Returns:
            Translated pattern or None if translation not possible
        """
        # If it's already a glob pattern, return as-is
        if '*' in pattern or '?' in pattern:
            return pattern
        
        # Try to detect and translate common regex patterns
        
        # Pattern: .*\.ext$ -> *.ext
        match = re.match(r'\.\*\\\.(\w+)\$', pattern)
        if match:
            return f"*.{match.group(1)}"
        
        # Pattern: ^/path/.* -> /path/*
        match = re.match(r'\^(/[^*]+)/\.\*', pattern)
        if match:
            return f"{match.group(1)}/*"
        
        # Pattern: .*/filename -> **/filename
        match = re.match(r'\.\*/(.+)', pattern)
        if match:
            return f"**/{match.group(1)}"
        
        # If no translation possible, return original
        # (Restic will treat it as a literal string)
        return pattern
    
    def _detect_regex_patterns(self, patterns: List[str]) -> List[str]:
        """
        Detect patterns that appear to be regex.
        
        Args:
            patterns: List of patterns to check
            
        Returns:
            List of patterns that appear to be regex
        """
        regex_indicators = [r'\\.', r'\d', r'\w', r'\s', r'[', r']', r'(', r')', r'^', r'$']
        regex_patterns = []
        
        for pattern in patterns:
            if any(indicator in pattern for indicator in regex_indicators):
                regex_patterns.append(pattern)
        
        return regex_patterns
    
    def _create_backup_targets(self, config: BackupConfig) -> List[BackupTarget]:
        """
        Create BackupTarget objects from configuration.
        
        Args:
            config: Backup configuration
            
        Returns:
            List of BackupTarget objects
        """
        targets = []
        
        # Translate selection rules
        translated = self.translate_selection_rules(
            config.include_patterns,
            config.exclude_patterns
        )
        
        # Create file selection
        selection = FileSelection()
        
        # Add source paths
        for path in config.source_paths:
            selection.add_path(Path(path))
        
        # Add exclude patterns
        for pattern in translated['exclude']:
            selection.add_exclude_pattern(pattern)
        
        # Create backup target
        target = BackupTarget(
            name=f"backup_{len(targets)}",
            selection=selection,
            tags=config.tags
        )
        
        targets.append(target)
        
        return targets
    
    def _get_repository(self, config: BackupConfig):
        """
        Get or create Restic repository instance.
        
        Args:
            config: Backup configuration
            
        Returns:
            Restic repository instance
        """
        # Import here to avoid circular dependencies
        from ..restic.Repositories.local import LocalResticRepository
        from ..restic.Repositories.s3 import S3ResticRepository
        from ..restic.Repositories.b2 import B2ResticRepository
        from urllib.parse import urlparse
        
        # Parse URI to determine repository type
        parsed = urlparse(config.repository_uri)
        scheme = parsed.scheme.lower() if parsed.scheme else 'local'
        
        # Select appropriate repository class
        if scheme in ['local', 'file', '']:
            repo_class = LocalResticRepository
        elif scheme == 's3':
            repo_class = S3ResticRepository
        elif scheme == 'b2':
            repo_class = B2ResticRepository
        else:
            raise PluginWrapperError(f"Unsupported URI scheme: {scheme}")
        
        # Create repository instance
        # Note: Password should be provided via environment or credential manager
        repository = repo_class(config.repository_uri)
        
        return repository
    
    def _convert_restic_result(
        self,
        restic_data: Dict[str, Any],
        config: BackupConfig
    ) -> BackupResult:
        """
        Convert Restic result data to standardized BackupResult.
        
        Args:
            restic_data: Result data from Restic
            config: Original backup configuration
            
        Returns:
            Standardized BackupResult
        """
        # Extract data from Restic result
        snapshot_id = restic_data.get('snapshot_id', 'unknown')
        files_new = restic_data.get('files_new', 0)
        files_changed = restic_data.get('files_changed', 0)
        files_unmodified = restic_data.get('files_unmodified', 0)
        data_added = restic_data.get('data_added', 0)
        
        total_files = files_new + files_changed + files_unmodified
        
        # Create warnings for any issues
        warnings = []
        if files_unmodified > total_files * 0.9:
            warnings.append(
                f"Most files ({files_unmodified}/{total_files}) were unmodified"
            )
        
        return self._create_backup_result(
            status=BackupStatus.COMPLETED,
            snapshot_id=snapshot_id,
            files_processed=total_files,
            bytes_processed=data_added,
            warnings=warnings
        )
    
    def supports_parallel_operations(self) -> bool:
        """
        Check if Restic supports parallel operations.
        
        Returns:
            True (Restic supports parallel operations)
        """
        return self.has_capability(Feature.PARALLEL_PROCESSING)
    
    def get_optimal_parallel_count(self, job_size: int) -> int:
        """
        Get optimal parallel operation count for Restic.
        
        Args:
            job_size: Estimated job size in bytes
            
        Returns:
            Recommended parallel operation count
        """
        # Restic performs well with 4-8 parallel operations
        # Adjust based on job size
        if job_size < 1024 * 1024 * 100:  # < 100MB
            return 2
        elif job_size < 1024 * 1024 * 1024:  # < 1GB
            return 4
        else:
            return 8
