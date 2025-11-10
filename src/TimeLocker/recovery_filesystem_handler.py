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

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .recovery_errors import (
    FileSystemError,
    FileSystemFullError,
    FileSystemReadOnlyError,
    FileSystemCorruptionError,
    PathTooLongError,
    SymlinkError,
    RestorePermissionError,
    InsufficientSpaceError
)

logger = logging.getLogger(__name__)


@dataclass
class FileSystemInfo:
    """Information about file system state"""
    path: str
    total_space: int
    free_space: int
    used_space: int
    is_writable: bool
    is_readable: bool
    mount_point: str


@dataclass
class AlternativePath:
    """Alternative path for recovery when primary path fails"""
    original_path: str
    alternative_path: str
    reason: str


class FileSystemErrorHandler:
    """
    Handles file system errors during recovery operations with
    alternative path strategies and space management.
    
    This handler provides:
    - File system space checking and management
    - Alternative path resolution for problematic paths
    - Permission error handling
    - Path length validation and truncation
    - Symbolic link handling
    """
    
    def __init__(
        self,
        min_free_space_mb: int = 100,
        max_path_length: int = 255,
        alternative_base_paths: Optional[List[str]] = None
    ):
        """
        Initialize the FileSystemErrorHandler.
        
        Args:
            min_free_space_mb: Minimum free space required in MB
            max_path_length: Maximum allowed path length
            alternative_base_paths: List of alternative base paths to try
        """
        self.min_free_space_mb = min_free_space_mb
        self.max_path_length = max_path_length
        self.alternative_base_paths = alternative_base_paths or []
        
        # Track alternative paths used
        self._alternative_paths: List[AlternativePath] = []
        
        logger.info(
            f"FileSystemErrorHandler initialized with min_free_space={min_free_space_mb}MB, "
            f"max_path_length={max_path_length}"
        )
    
    def check_filesystem_space(self, target_path: str, required_bytes: int) -> bool:
        """
        Check if sufficient space is available on the target file system.
        
        Args:
            target_path: Path to check space for
            required_bytes: Number of bytes required
            
        Returns:
            True if sufficient space is available, False otherwise
            
        Raises:
            FileSystemError: If unable to check file system space
        """
        try:
            path = Path(target_path)
            
            # Get parent directory if path doesn't exist
            check_path = path if path.exists() else path.parent
            
            # Get disk usage statistics
            stat = shutil.disk_usage(check_path)
            
            # Check if we have enough space plus minimum buffer
            min_required = required_bytes + (self.min_free_space_mb * 1024 * 1024)
            
            if stat.free < min_required:
                logger.warning(
                    f"Insufficient space on {check_path}: "
                    f"required {min_required / (1024**3):.2f}GB, "
                    f"available {stat.free / (1024**3):.2f}GB"
                )
                return False
            
            logger.debug(
                f"Sufficient space on {check_path}: "
                f"required {min_required / (1024**3):.2f}GB, "
                f"available {stat.free / (1024**3):.2f}GB"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error checking file system space for {target_path}: {e}")
            raise FileSystemError(f"Unable to check file system space: {e}") from e
    
    def get_filesystem_info(self, path: str) -> FileSystemInfo:
        """
        Get detailed information about a file system.
        
        Args:
            path: Path to get file system info for
            
        Returns:
            FileSystemInfo object with file system details
            
        Raises:
            FileSystemError: If unable to get file system info
        """
        try:
            path_obj = Path(path)
            
            # Get parent directory if path doesn't exist
            check_path = path_obj if path_obj.exists() else path_obj.parent
            
            # Get disk usage
            stat = shutil.disk_usage(check_path)
            
            # Check permissions
            is_writable = os.access(check_path, os.W_OK)
            is_readable = os.access(check_path, os.R_OK)
            
            # Get mount point (Unix-like systems)
            mount_point = str(check_path)
            try:
                import subprocess
                result = subprocess.run(
                    ['df', str(check_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        mount_point = lines[1].split()[-1]
            except Exception:
                pass  # Fall back to path if df command fails
            
            return FileSystemInfo(
                path=str(check_path),
                total_space=stat.total,
                free_space=stat.free,
                used_space=stat.used,
                is_writable=is_writable,
                is_readable=is_readable,
                mount_point=mount_point
            )
            
        except Exception as e:
            logger.error(f"Error getting file system info for {path}: {e}")
            raise FileSystemError(f"Unable to get file system info: {e}") from e
    
    def handle_space_error(
        self,
        target_path: str,
        required_bytes: int
    ) -> Optional[str]:
        """
        Handle insufficient space error by finding alternative path.
        
        Args:
            target_path: Original target path
            required_bytes: Number of bytes required
            
        Returns:
            Alternative path if found, None otherwise
        """
        logger.warning(f"Handling space error for {target_path}")
        
        # Try alternative base paths
        for alt_base in self.alternative_base_paths:
            try:
                alt_path = Path(alt_base) / Path(target_path).name
                
                if self.check_filesystem_space(str(alt_path), required_bytes):
                    logger.info(f"Found alternative path with sufficient space: {alt_path}")
                    
                    # Record alternative path
                    self._alternative_paths.append(AlternativePath(
                        original_path=target_path,
                        alternative_path=str(alt_path),
                        reason="insufficient_space"
                    ))
                    
                    return str(alt_path)
                    
            except Exception as e:
                logger.debug(f"Alternative path {alt_base} not suitable: {e}")
                continue
        
        logger.error(f"No alternative path found with sufficient space for {target_path}")
        return None
    
    def handle_permission_error(
        self,
        target_path: str,
        operation: str = "write"
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle permission error by attempting to fix or find alternative.
        
        Args:
            target_path: Path with permission issues
            operation: Type of operation (read/write)
            
        Returns:
            Tuple of (success, alternative_path or error_message)
        """
        logger.warning(f"Handling permission error for {target_path}")
        
        path = Path(target_path)
        
        # Check if parent directory exists and is writable
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created parent directory: {path.parent}")
                return True, None
            except Exception as e:
                logger.error(f"Failed to create parent directory: {e}")
                return False, f"Cannot create parent directory: {e}"
        
        # Check if we can modify permissions
        try:
            if operation == "write" and not os.access(path.parent, os.W_OK):
                # Try to make parent writable
                try:
                    os.chmod(path.parent, 0o755)
                    logger.info(f"Modified permissions for {path.parent}")
                    return True, None
                except Exception as e:
                    logger.debug(f"Cannot modify permissions: {e}")
        except Exception as e:
            logger.debug(f"Error checking permissions: {e}")
        
        # Try alternative paths
        for alt_base in self.alternative_base_paths:
            try:
                alt_path = Path(alt_base) / path.name
                
                if os.access(alt_path.parent, os.W_OK):
                    logger.info(f"Found alternative path with write access: {alt_path}")
                    
                    # Record alternative path
                    self._alternative_paths.append(AlternativePath(
                        original_path=target_path,
                        alternative_path=str(alt_path),
                        reason="permission_denied"
                    ))
                    
                    return True, str(alt_path)
                    
            except Exception as e:
                logger.debug(f"Alternative path {alt_base} not suitable: {e}")
                continue
        
        return False, "No alternative path with write access found"
    
    def validate_path_length(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate path length and provide truncated alternative if needed.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, truncated_path or None)
        """
        if len(path) <= self.max_path_length:
            return True, None
        
        logger.warning(f"Path exceeds maximum length ({len(path)} > {self.max_path_length}): {path}")
        
        # Try to truncate the filename while keeping directory structure
        path_obj = Path(path)
        
        # Calculate how much we need to truncate
        excess = len(path) - self.max_path_length
        filename = path_obj.name
        
        if len(filename) > excess + 10:  # Keep at least 10 chars of filename
            # Truncate filename
            extension = path_obj.suffix
            name_without_ext = path_obj.stem
            
            # Truncate the name part
            max_name_length = len(name_without_ext) - excess - 3  # -3 for "..."
            if max_name_length > 0:
                truncated_name = name_without_ext[:max_name_length] + "..."
                truncated_filename = truncated_name + extension
                truncated_path = str(path_obj.parent / truncated_filename)
                
                logger.info(f"Truncated path: {truncated_path}")
                
                # Record alternative path
                self._alternative_paths.append(AlternativePath(
                    original_path=path,
                    alternative_path=truncated_path,
                    reason="path_too_long"
                ))
                
                return False, truncated_path
        
        logger.error(f"Cannot truncate path sufficiently: {path}")
        return False, None
    
    def handle_symlink_error(
        self,
        symlink_path: str,
        target_path: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle symbolic link errors during recovery.
        
        Args:
            symlink_path: Path to the symbolic link
            target_path: Target path of the symbolic link
            
        Returns:
            Tuple of (success, error_message or None)
        """
        logger.warning(f"Handling symlink error: {symlink_path} -> {target_path}")
        
        try:
            symlink = Path(symlink_path)
            target = Path(target_path)
            
            # Check if target exists
            if not target.exists():
                logger.warning(f"Symlink target does not exist: {target}")
                # Create a placeholder file instead
                try:
                    symlink.parent.mkdir(parents=True, exist_ok=True)
                    symlink.touch()
                    logger.info(f"Created placeholder file instead of symlink: {symlink}")
                    return True, None
                except Exception as e:
                    return False, f"Cannot create placeholder: {e}"
            
            # Try to create the symlink
            try:
                symlink.parent.mkdir(parents=True, exist_ok=True)
                if symlink.exists():
                    symlink.unlink()
                symlink.symlink_to(target)
                logger.info(f"Successfully created symlink: {symlink} -> {target}")
                return True, None
            except Exception as e:
                logger.error(f"Failed to create symlink: {e}")
                return False, f"Cannot create symlink: {e}"
                
        except Exception as e:
            logger.error(f"Error handling symlink: {e}")
            return False, str(e)
    
    def get_alternative_paths(self) -> List[AlternativePath]:
        """
        Get list of alternative paths used during recovery.
        
        Returns:
            List of AlternativePath objects
        """
        return self._alternative_paths.copy()
    
    def clear_alternative_paths(self) -> None:
        """Clear the list of alternative paths."""
        self._alternative_paths.clear()
        logger.debug("Cleared alternative paths list")
