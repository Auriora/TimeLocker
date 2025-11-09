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
Backup Tool Adapter Interface for TimeLocker Recovery Operations

This module defines the abstract base class for backup tool-specific recovery
operations. Each supported backup tool (Restic, Borg, Duplicity) implements
this interface to provide tool-specific functionality while maintaining a
consistent recovery interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from .recovery_models import (
    FileEntry,
    SnapshotListing,
    SelectionCriteria,
    RecoveryOptions,
    ValidationResult
)


class BackupToolType(Enum):
    """Supported backup tool types"""
    RESTIC = "restic"
    BORG = "borg"
    DUPLICITY = "duplicity"
    UNKNOWN = "unknown"


class ToolCapability(Enum):
    """Capabilities that backup tools may support"""
    SNAPSHOT_BROWSING = "snapshot_browsing"
    SELECTIVE_RESTORE = "selective_restore"
    INCREMENTAL_RESTORE = "incremental_restore"
    PARALLEL_RESTORE = "parallel_restore"
    CHECKSUM_VERIFICATION = "checksum_verification"
    COMPRESSION = "compression"
    ENCRYPTION = "encryption"
    DEDUPLICATION = "deduplication"
    SNAPSHOT_COMPARISON = "snapshot_comparison"
    METADATA_EXTRACTION = "metadata_extraction"


@dataclass
class FileSelection:
    """
    Represents a selection of files for restoration.
    
    Attributes:
        include_paths: List of paths to include
        exclude_paths: List of paths to exclude
        include_patterns: List of patterns to include
        exclude_patterns: List of patterns to exclude
        selection_criteria: Optional SelectionCriteria object
    """
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    selection_criteria: Optional[SelectionCriteria] = None
    
    def __post_init__(self):
        """Validate file selection"""
        if not any([
            self.include_paths,
            self.include_patterns,
            self.selection_criteria
        ]):
            # If no includes specified, default to all files
            self.include_paths = ["/"]


@dataclass
class RestoreOptions:
    """
    Tool-specific restore operation options.
    
    Attributes:
        target_path: Destination path for restored files
        overwrite_existing: Whether to overwrite existing files
        preserve_permissions: Whether to preserve file permissions
        preserve_timestamps: Whether to preserve file timestamps
        verify_after_restore: Whether to verify files after restoration
        parallel_operations: Number of parallel restore operations
        tool_specific_options: Dictionary of tool-specific options
    """
    target_path: Path
    overwrite_existing: bool = False
    preserve_permissions: bool = True
    preserve_timestamps: bool = True
    verify_after_restore: bool = True
    parallel_operations: int = 1
    tool_specific_options: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate restore options"""
        if not self.target_path:
            raise ValueError("target_path cannot be empty")
        if self.parallel_operations < 1:
            raise ValueError("parallel_operations must be >= 1")


@dataclass
class RestoreOperation:
    """
    Represents an active restore operation.
    
    Attributes:
        operation_id: Unique identifier for the operation
        snapshot_id: ID of the snapshot being restored
        target_path: Destination path
        files_restored: Number of files successfully restored
        files_failed: Number of files that failed to restore
        bytes_restored: Total bytes restored
        start_time: When the operation started
        is_complete: Whether the operation is complete
        success: Whether the operation was successful
        error_message: Error message if operation failed
    """
    operation_id: str
    snapshot_id: str
    target_path: Path
    files_restored: int = 0
    files_failed: int = 0
    bytes_restored: int = 0
    start_time: Optional[float] = None
    is_complete: bool = False
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class VerificationResult:
    """
    Results of restoration verification.
    
    Attributes:
        verified_files: Number of files verified
        failed_files: Number of files that failed verification
        checksum_mismatches: List of files with checksum mismatches
        missing_files: List of files that should exist but don't
        success: Whether verification was successful overall
        details: Additional verification details
    """
    verified_files: int
    failed_files: int
    checksum_mismatches: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    success: bool = True
    details: Dict[str, any] = field(default_factory=dict)


@dataclass
class ToolInfo:
    """
    Information about a backup tool.
    
    Attributes:
        tool_type: Type of backup tool
        version: Tool version string
        executable_path: Path to tool executable
        is_available: Whether the tool is available on the system
        capabilities: Set of supported capabilities
        configuration: Tool-specific configuration
    """
    tool_type: BackupToolType
    version: Optional[str] = None
    executable_path: Optional[Path] = None
    is_available: bool = False
    capabilities: Set[ToolCapability] = field(default_factory=set)
    configuration: Dict[str, any] = field(default_factory=dict)


class BackupToolAdapter(ABC):
    """
    Abstract base class for backup tool-specific recovery operations.
    
    Each supported backup tool implements this interface to provide
    tool-specific functionality while maintaining a consistent recovery
    interface across different backup engines.
    
    This adapter pattern allows TimeLocker to support multiple backup
    tools (Restic, Borg, Duplicity) with a unified recovery API.
    """
    
    def __init__(self, repository_path: str):
        """
        Initialize the backup tool adapter.
        
        Args:
            repository_path: Path to the backup repository
        """
        self.repository_path = repository_path
        self._tool_info: Optional[ToolInfo] = None
    
    @abstractmethod
    def get_tool_info(self) -> ToolInfo:
        """
        Get information about the backup tool.
        
        This method provides details about the tool including version,
        availability, and supported capabilities.
        
        Returns:
            ToolInfo object with tool details
        """
        pass
    
    @abstractmethod
    def detect_tool(self) -> bool:
        """
        Detect if the backup tool is available on the system.
        
        This method checks if the tool executable exists and is accessible,
        and verifies that it's a compatible version.
        
        Returns:
            True if tool is available and compatible, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Set[ToolCapability]:
        """
        Get the set of capabilities supported by this tool.
        
        Different backup tools support different features. This method
        returns the set of capabilities that this tool provides.
        
        Returns:
            Set of ToolCapability values
        """
        pass
    
    @abstractmethod
    def browse_snapshot(
        self,
        repository_path: str,
        snapshot_id: str,
        path: str = "/"
    ) -> SnapshotListing:
        """
        Browse snapshot contents using tool-specific implementation.
        
        This method provides tool-specific snapshot browsing functionality,
        returning a standardized SnapshotListing object.
        
        Args:
            repository_path: Path to the backup repository
            snapshot_id: ID of the snapshot to browse
            path: Path within the snapshot to list (default: root)
            
        Returns:
            SnapshotListing containing file entries
            
        Raises:
            NotImplementedError: If tool doesn't support snapshot browsing
            Exception: For tool-specific errors
        """
        pass
    
    @abstractmethod
    def restore_files(
        self,
        repository_path: str,
        snapshot_id: str,
        selection: FileSelection,
        target_path: str,
        options: RestoreOptions
    ) -> RestoreOperation:
        """
        Restore files using tool-specific implementation.
        
        This method performs the actual file restoration using the
        backup tool's native restore functionality.
        
        Args:
            repository_path: Path to the backup repository
            snapshot_id: ID of the snapshot to restore from
            selection: Files to restore
            target_path: Destination path for restored files
            options: Restore operation options
            
        Returns:
            RestoreOperation object tracking the operation
            
        Raises:
            Exception: For tool-specific restore errors
        """
        pass
    
    @abstractmethod
    def verify_restoration(
        self,
        repository_path: str,
        snapshot_id: str,
        restored_files: List[str]
    ) -> VerificationResult:
        """
        Verify restored files using tool-specific verification.
        
        This method validates that files were restored correctly by
        comparing checksums and verifying file integrity.
        
        Args:
            repository_path: Path to the backup repository
            snapshot_id: ID of the snapshot that was restored
            restored_files: List of file paths that were restored
            
        Returns:
            VerificationResult with verification details
            
        Raises:
            NotImplementedError: If tool doesn't support verification
            Exception: For tool-specific verification errors
        """
        pass
    
    def supports_capability(self, capability: ToolCapability) -> bool:
        """
        Check if the tool supports a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if capability is supported, False otherwise
        """
        return capability in self.get_capabilities()
    
    def validate_repository(self, repository_path: str) -> bool:
        """
        Validate that the repository is accessible and valid.
        
        This method performs basic validation to ensure the repository
        exists and is in a valid format for this backup tool.
        
        Args:
            repository_path: Path to the repository to validate
            
        Returns:
            True if repository is valid, False otherwise
        """
        # Default implementation - subclasses should override
        return Path(repository_path).exists()
    
    def get_snapshot_metadata(
        self,
        repository_path: str,
        snapshot_id: str
    ) -> Dict[str, any]:
        """
        Get metadata for a specific snapshot.
        
        This method retrieves snapshot metadata such as creation time,
        size, number of files, etc.
        
        Args:
            repository_path: Path to the backup repository
            snapshot_id: ID of the snapshot
            
        Returns:
            Dictionary containing snapshot metadata
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement get_snapshot_metadata"
        )
    
    def estimate_restore_size(
        self,
        repository_path: str,
        snapshot_id: str,
        selection: Optional[FileSelection] = None
    ) -> int:
        """
        Estimate the size of data to be restored.
        
        This method calculates the total size of files that would be
        restored based on the selection criteria.
        
        Args:
            repository_path: Path to the backup repository
            snapshot_id: ID of the snapshot
            selection: Optional file selection criteria
            
        Returns:
            Estimated size in bytes
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement estimate_restore_size"
        )
