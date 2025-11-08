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
Plugin Wrapper System for Backup Tools

This module provides a plugin wrapper system that standardizes backup tool
interfaces and fills capability gaps for different backup engines. The wrapper
layer sits between the backup orchestration layer and the actual backup tools,
providing consistent interfaces and enhanced capabilities.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from pathlib import Path

from ..interfaces.data_models import (
    BackupResult,
    BackupStatus,
    BackupJob,
    ToolConfiguration
)
from .tool_manager import Feature, ToolCapabilities

logger = logging.getLogger(__name__)


@dataclass
class BackupConfig:
    """
    Standardized backup configuration for plugin wrappers.
    
    Attributes:
        source_paths: List of paths to backup
        repository_uri: Repository URI
        exclude_patterns: Patterns to exclude
        include_patterns: Patterns to include
        tags: Tags to apply to backup
        tool_configuration: Tool-specific configuration
        dry_run: Whether to perform a dry run
        metadata: Additional metadata
    """
    source_paths: List[Path]
    repository_uri: str
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    tool_configuration: Optional[ToolConfiguration] = None
    dry_run: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginWrapperError(Exception):
    """Base exception for plugin wrapper errors"""
    pass


class CapabilityNotSupportedError(PluginWrapperError):
    """Raised when a required capability is not supported"""
    pass


class PluginWrapper(ABC):
    """
    Base class for backup tool plugin wrappers.
    
    Plugin wrappers provide:
    - Standardized interfaces across different backup tools
    - Capability gap filling where possible
    - Translation between TimeLocker and tool-specific formats
    - Enhanced error handling and reporting
    
    Subclasses must implement all abstract methods to provide
    tool-specific functionality.
    """
    
    def __init__(self, tool_name: str):
        """
        Initialize plugin wrapper.
        
        Args:
            tool_name: Name of the backup tool being wrapped
        """
        self.tool_name = tool_name
        self._capabilities: Optional[ToolCapabilities] = None
        logger.debug(f"Initialized {self.__class__.__name__} for {tool_name}")
    
    @abstractmethod
    def get_native_capabilities(self) -> Set[Feature]:
        """
        Get capabilities natively supported by the tool.
        
        Returns:
            Set of Feature enums representing native capabilities
        """
        pass
    
    @abstractmethod
    def get_wrapper_capabilities(self) -> Set[Feature]:
        """
        Get capabilities provided by the wrapper.
        
        These are features not natively supported by the tool but
        implemented by the wrapper to provide consistent functionality.
        
        Returns:
            Set of Feature enums representing wrapper-provided capabilities
        """
        pass
    
    @abstractmethod
    def execute_backup(self, config: BackupConfig) -> BackupResult:
        """
        Execute backup using wrapped tool with standardized interface.
        
        Args:
            config: Standardized backup configuration
            
        Returns:
            BackupResult with operation results
            
        Raises:
            PluginWrapperError: If backup execution fails
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: BackupConfig) -> Dict[str, Any]:
        """
        Validate backup configuration for this tool.
        
        Args:
            config: Backup configuration to validate
            
        Returns:
            Dictionary with validation results:
            - is_valid: bool
            - errors: List[str]
            - warnings: List[str]
        """
        pass
    
    @abstractmethod
    def translate_selection_rules(
        self,
        include_patterns: List[str],
        exclude_patterns: List[str]
    ) -> Dict[str, List[str]]:
        """
        Translate data selection rules to tool-specific format.
        
        Args:
            include_patterns: Include patterns in TimeLocker format
            exclude_patterns: Exclude patterns in TimeLocker format
            
        Returns:
            Dictionary with tool-specific patterns:
            - include: List[str]
            - exclude: List[str]
            - unsupported: List[str] (patterns that couldn't be translated)
        """
        pass
    
    def get_all_capabilities(self) -> Set[Feature]:
        """
        Get all available capabilities (native + wrapper).
        
        Returns:
            Set of all available features
        """
        return self.get_native_capabilities() | self.get_wrapper_capabilities()
    
    def has_capability(self, feature: Feature) -> bool:
        """
        Check if a capability is available.
        
        Args:
            feature: Feature to check
            
        Returns:
            True if feature is available (native or wrapper)
        """
        return feature in self.get_all_capabilities()
    
    def is_native_capability(self, feature: Feature) -> bool:
        """
        Check if a capability is natively supported.
        
        Args:
            feature: Feature to check
            
        Returns:
            True if feature is natively supported
        """
        return feature in self.get_native_capabilities()
    
    def is_wrapper_capability(self, feature: Feature) -> bool:
        """
        Check if a capability is provided by wrapper.
        
        Args:
            feature: Feature to check
            
        Returns:
            True if feature is provided by wrapper
        """
        return feature in self.get_wrapper_capabilities()
    
    def get_capability_info(self) -> Dict[str, Any]:
        """
        Get detailed capability information.
        
        Returns:
            Dictionary with capability details
        """
        native = self.get_native_capabilities()
        wrapper = self.get_wrapper_capabilities()
        
        return {
            'tool_name': self.tool_name,
            'native_features': [f.value for f in native],
            'wrapper_features': [f.value for f in wrapper],
            'total_features': len(native) + len(wrapper),
            'native_count': len(native),
            'wrapper_count': len(wrapper)
        }
    
    def check_required_capabilities(
        self,
        required_features: Set[Feature]
    ) -> Dict[str, Any]:
        """
        Check if required capabilities are available.
        
        Args:
            required_features: Set of required features
            
        Returns:
            Dictionary with check results:
            - all_supported: bool
            - missing_features: List[Feature]
            - native_features: List[Feature]
            - wrapper_features: List[Feature]
        """
        available = self.get_all_capabilities()
        native = self.get_native_capabilities()
        wrapper = self.get_wrapper_capabilities()
        
        missing = required_features - available
        supported_native = required_features & native
        supported_wrapper = required_features & wrapper
        
        return {
            'all_supported': len(missing) == 0,
            'missing_features': list(missing),
            'native_features': list(supported_native),
            'wrapper_features': list(supported_wrapper)
        }
    
    def _create_backup_result(
        self,
        status: BackupStatus,
        snapshot_id: Optional[str] = None,
        files_processed: int = 0,
        bytes_processed: int = 0,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ) -> BackupResult:
        """
        Helper method to create standardized BackupResult.
        
        Args:
            status: Backup status
            snapshot_id: Optional snapshot ID
            files_processed: Number of files processed
            bytes_processed: Number of bytes processed
            errors: List of errors
            warnings: List of warnings
            
        Returns:
            BackupResult instance
        """
        import time
        
        return BackupResult(
            status=status,
            repository_name=self.tool_name,
            target_names=[],
            start_time=time.time(),
            end_time=time.time(),
            snapshot_id=snapshot_id,
            files_processed=files_processed,
            bytes_processed=bytes_processed,
            errors=errors or [],
            warnings=warnings or []
        )
