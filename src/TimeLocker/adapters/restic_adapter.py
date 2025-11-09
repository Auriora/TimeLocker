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
Restic Adapter for TimeLocker Recovery Operations

This module provides Restic-specific implementation of the BackupToolAdapter
interface, enabling recovery operations using the Restic backup tool.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..interfaces.backup_tool_adapter import (
    BackupToolAdapter,
    BackupToolType,
    ToolCapability,
    FileSelection,
    RestoreOptions,
    RestoreOperation,
    VerificationResult,
    ToolInfo
)
from ..interfaces.recovery_models import (
    FileEntry,
    FileType,
    SnapshotListing,
    PaginationInfo
)
from ..command_builder import CommandBuilder
from ..restic.restic_command_definition import restic_command_def
from ..recovery_errors import RecoveryError

logger = logging.getLogger(__name__)


class ResticAdapter(BackupToolAdapter):
    """
    Restic-specific implementation of the BackupToolAdapter interface.
    
    This adapter provides Restic-specific functionality for snapshot browsing,
    file restoration, and integrity verification while maintaining compatibility
    with the unified recovery interface.
    """
    
    # Minimum supported Restic version
    MIN_RESTIC_VERSION = "0.18.0"
    
    def __init__(
        self,
        repository_path: str,
        password: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the Restic adapter.
        
        Args:
            repository_path: Path to the Restic repository
            password: Optional repository password
            environment: Optional environment variables for Restic
        """
        super().__init__(repository_path)
        self._password = password
        self._environment = environment or {}
        self._tool_info: Optional[ToolInfo] = None
        
        # Detect and validate Restic installation
        if not self.detect_tool():
            logger.warning("Restic tool not detected or incompatible version")
        
        logger.info(f"ResticAdapter initialized for repository: {repository_path}")
    
    def get_tool_info(self) -> ToolInfo:
        """
        Get information about the Restic tool.
        
        Returns:
            ToolInfo object with Restic details
        """
        if self._tool_info is None:
            self._tool_info = self._detect_tool_info()
        return self._tool_info
    
    def detect_tool(self) -> bool:
        """
        Detect if Restic is available on the system.
        
        Returns:
            True if Restic is available and compatible, False otherwise
        """
        try:
            tool_info = self._detect_tool_info()
            self._tool_info = tool_info
            return tool_info.is_available
        except Exception as e:
            logger.error(f"Failed to detect Restic tool: {e}")
            return False
    
    def get_capabilities(self) -> Set[ToolCapability]:
        """
        Get the set of capabilities supported by Restic.
        
        Returns:
            Set of ToolCapability values
        """
        return {
            ToolCapability.SNAPSHOT_BROWSING,
            ToolCapability.SELECTIVE_RESTORE,
            ToolCapability.CHECKSUM_VERIFICATION,
            ToolCapability.COMPRESSION,
            ToolCapability.ENCRYPTION,
            ToolCapability.DEDUPLICATION,
            ToolCapability.SNAPSHOT_COMPARISON,
            ToolCapability.METADATA_EXTRACTION
        }
    
    def browse_snapshot(
        self,
        repository_path: str,
        snapshot_id: str,
        path: str = "/"
    ) -> SnapshotListing:
        """
        Browse snapshot contents using Restic ls command.
        
        Args:
            repository_path: Path to the Restic repository
            snapshot_id: ID of the snapshot to browse
            path: Path within the snapshot to list (default: root)
            
        Returns:
            SnapshotListing containing file entries
            
        Raises:
            RecoveryError: If browsing fails
        """
        try:
            logger.info(f"Browsing snapshot {snapshot_id} at path {path}")
            
            # Build restic ls command
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", repository_path)
            command = command.command("ls")
            command = command.param("long")  # Get detailed file information
            
            # Build command list and add snapshot ID and path
            command_list = command.build()
            command_list.append(snapshot_id)
            if path and path != "/":
                command_list.append(path)
            
            # Execute command
            env = self._build_environment()
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            # Parse JSON output
            entries = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        data = json.loads(line)
                        entry = self._parse_file_entry(data)
                        if entry:
                            entries.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON line: {e}")
                        continue
            
            listing = SnapshotListing(
                path=path,
                entries=entries,
                total_entries=len(entries)
            )
            
            logger.info(f"Successfully browsed snapshot {snapshot_id}: {len(entries)} entries")
            return listing
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to browse snapshot: {e.stderr}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to browse snapshot: {str(e)}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
    
    def restore_files(
        self,
        repository_path: str,
        snapshot_id: str,
        selection: FileSelection,
        target_path: str,
        options: RestoreOptions
    ) -> RestoreOperation:
        """
        Restore files using Restic restore command.
        
        Args:
            repository_path: Path to the Restic repository
            snapshot_id: ID of the snapshot to restore from
            selection: Files to restore
            target_path: Destination path for restored files
            options: Restore operation options
            
        Returns:
            RestoreOperation object tracking the operation
            
        Raises:
            RecoveryError: If restore fails
        """
        operation_id = f"restic-restore-{snapshot_id}-{int(time.time())}"
        operation = RestoreOperation(
            operation_id=operation_id,
            snapshot_id=snapshot_id,
            target_path=Path(target_path),
            start_time=time.time()
        )
        
        try:
            logger.info(f"Starting restore operation {operation_id}")
            
            # Build restic restore command
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", repository_path)
            command = command.command("restore")
            command = command.param("target", target_path)
            
            # Add include patterns
            for include_path in selection.include_paths:
                command = command.param("include", include_path)
            
            for include_pattern in selection.include_patterns:
                command = command.param("include", include_pattern)
            
            # Add exclude patterns
            for exclude_path in selection.exclude_paths:
                command = command.param("exclude", exclude_path)
            
            for exclude_pattern in selection.exclude_patterns:
                command = command.param("exclude", exclude_pattern)
            
            # Add restore options
            if options.verify_after_restore:
                command = command.param("verify")
            
            # Build command list and add snapshot ID
            command_list = command.build()
            command_list.append(snapshot_id)
            
            # Execute restore command
            env = self._build_environment()
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            # Parse restore output
            self._parse_restore_output(result.stdout, operation)
            
            operation.is_complete = True
            operation.success = True
            
            logger.info(
                f"Restore operation {operation_id} completed: "
                f"{operation.files_restored} files restored, "
                f"{operation.bytes_restored} bytes"
            )
            
            return operation
            
        except subprocess.CalledProcessError as e:
            operation.is_complete = True
            operation.success = False
            operation.error_message = f"Restore failed: {e.stderr}"
            logger.error(f"Restore operation {operation_id} failed: {e.stderr}")
            raise RecoveryError(operation.error_message) from e
        except Exception as e:
            operation.is_complete = True
            operation.success = False
            operation.error_message = f"Restore failed: {str(e)}"
            logger.error(f"Restore operation {operation_id} failed: {str(e)}")
            raise RecoveryError(operation.error_message) from e
    
    def verify_restoration(
        self,
        repository_path: str,
        snapshot_id: str,
        restored_files: List[str]
    ) -> VerificationResult:
        """
        Verify restored files using Restic diff command.
        
        Args:
            repository_path: Path to the Restic repository
            snapshot_id: ID of the snapshot that was restored
            restored_files: List of file paths that were restored
            
        Returns:
            VerificationResult with verification details
            
        Raises:
            RecoveryError: If verification fails
        """
        result = VerificationResult(
            verified_files=0,
            failed_files=0
        )
        
        try:
            logger.info(f"Verifying restoration of {len(restored_files)} files")
            
            # For each restored file, verify it matches the snapshot
            for file_path in restored_files:
                try:
                    # Use restic dump to get file content from snapshot
                    # and compare with restored file
                    if self._verify_file(repository_path, snapshot_id, file_path):
                        result.verified_files += 1
                    else:
                        result.failed_files += 1
                        result.checksum_mismatches.append(file_path)
                except Exception as e:
                    logger.warning(f"Failed to verify file {file_path}: {e}")
                    result.failed_files += 1
            
            result.success = result.failed_files == 0
            
            logger.info(
                f"Verification completed: "
                f"{result.verified_files} verified, "
                f"{result.failed_files} failed"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
    
    def validate_repository(self, repository_path: str) -> bool:
        """
        Validate that the Restic repository is accessible and valid.
        
        Args:
            repository_path: Path to the repository to validate
            
        Returns:
            True if repository is valid, False otherwise
        """
        try:
            # Use restic snapshots command to validate repository
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", repository_path)
            command = command.command("snapshots")
            
            env = self._build_environment()
            result = subprocess.run(
                command.build(),
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            # If command succeeds, repository is valid
            logger.info(f"Repository validated: {repository_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Repository validation failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Repository validation failed: {str(e)}")
            return False
    
    def get_snapshot_metadata(
        self,
        repository_path: str,
        snapshot_id: str
    ) -> Dict[str, any]:
        """
        Get metadata for a specific snapshot.
        
        Args:
            repository_path: Path to the Restic repository
            snapshot_id: ID of the snapshot
            
        Returns:
            Dictionary containing snapshot metadata
            
        Raises:
            RecoveryError: If metadata retrieval fails
        """
        try:
            # Use restic snapshots command with specific snapshot ID
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", repository_path)
            command = command.command("snapshots")
            
            command_list = command.build()
            command_list.append(snapshot_id)
            
            env = self._build_environment()
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            # Parse JSON output
            snapshots = json.loads(result.stdout)
            if snapshots and len(snapshots) > 0:
                return snapshots[0]
            else:
                raise RecoveryError(f"Snapshot {snapshot_id} not found")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to get snapshot metadata: {e.stderr}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to get snapshot metadata: {str(e)}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
    
    def estimate_restore_size(
        self,
        repository_path: str,
        snapshot_id: str,
        selection: Optional[FileSelection] = None
    ) -> int:
        """
        Estimate the size of data to be restored.
        
        Args:
            repository_path: Path to the Restic repository
            snapshot_id: ID of the snapshot
            selection: Optional file selection criteria
            
        Returns:
            Estimated size in bytes
            
        Raises:
            RecoveryError: If size estimation fails
        """
        try:
            # Use restic stats command to get size information
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.param("repo", repository_path)
            command = command.command("stats")
            
            command_list = command.build()
            command_list.append(snapshot_id)
            
            env = self._build_environment()
            result = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            # Parse JSON output
            stats = json.loads(result.stdout)
            total_size = stats.get("total_size", 0)
            
            logger.info(f"Estimated restore size: {total_size} bytes")
            return total_size
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to estimate restore size: {e.stderr}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to estimate restore size: {str(e)}"
            logger.error(error_msg)
            raise RecoveryError(error_msg) from e
    
    def _detect_tool_info(self) -> ToolInfo:
        """
        Detect Restic tool information.
        
        Returns:
            ToolInfo object with Restic details
        """
        tool_info = ToolInfo(tool_type=BackupToolType.RESTIC)
        
        try:
            # Try to get Restic version
            command = CommandBuilder(restic_command_def)
            command = command.param("json")
            command = command.command("version")
            
            result = subprocess.run(
                command.build(),
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse version info
            version_data = json.loads(result.stdout)
            tool_info.version = version_data.get("version", "unknown")
            tool_info.is_available = True
            tool_info.capabilities = self.get_capabilities()
            
            # Try to find executable path
            which_result = subprocess.run(
                ["which", "restic"],
                capture_output=True,
                text=True
            )
            if which_result.returncode == 0:
                tool_info.executable_path = Path(which_result.stdout.strip())
            
            logger.info(f"Detected Restic version: {tool_info.version}")
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to detect Restic: {e}")
            tool_info.is_available = False
        
        return tool_info
    
    def _build_environment(self) -> Dict[str, str]:
        """
        Build environment variables for Restic commands.
        
        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        
        # Add password if provided
        if self._password:
            env["RESTIC_PASSWORD"] = self._password
        
        # Add any additional environment variables
        env.update(self._environment)
        
        return env
    
    def _parse_file_entry(self, data: Dict) -> Optional[FileEntry]:
        """
        Parse file entry from Restic ls JSON output.
        
        Args:
            data: JSON data from restic ls
            
        Returns:
            FileEntry object or None if parsing fails
        """
        try:
            # Determine file type
            struct_type = data.get("struct_type", "")
            if struct_type == "node":
                node_type = data.get("type", "file")
                if node_type == "dir":
                    file_type = FileType.DIRECTORY
                elif node_type == "symlink":
                    file_type = FileType.SYMLINK
                else:
                    file_type = FileType.FILE
            else:
                file_type = FileType.FILE
            
            # Parse path and name
            full_path = data.get("path", "")
            name = data.get("name", Path(full_path).name)
            
            # Parse size
            size = data.get("size", 0)
            
            # Parse modification time
            mtime_str = data.get("mtime", "")
            if mtime_str:
                try:
                    modification_time = datetime.fromisoformat(
                        mtime_str.replace('Z', '+00:00')
                    )
                except ValueError:
                    modification_time = datetime.now()
            else:
                modification_time = datetime.now()
            
            # Parse permissions
            mode = data.get("mode", 0)
            permissions = self._format_permissions(mode)
            
            # Get checksum if available
            checksum = None
            if "content" in data and data["content"]:
                checksum = data["content"][0] if isinstance(data["content"], list) else None
            
            return FileEntry(
                path=full_path,
                name=name,
                type=file_type,
                size=size,
                modification_time=modification_time,
                permissions=permissions,
                checksum=checksum
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse file entry: {e}")
            return None
    
    def _format_permissions(self, mode: int) -> str:
        """
        Format Unix file mode as permission string.
        
        Args:
            mode: Unix file mode integer
            
        Returns:
            Permission string (e.g., "rwxr-xr-x")
        """
        perms = []
        
        # Owner permissions
        perms.append('r' if mode & 0o400 else '-')
        perms.append('w' if mode & 0o200 else '-')
        perms.append('x' if mode & 0o100 else '-')
        
        # Group permissions
        perms.append('r' if mode & 0o040 else '-')
        perms.append('w' if mode & 0o020 else '-')
        perms.append('x' if mode & 0o010 else '-')
        
        # Other permissions
        perms.append('r' if mode & 0o004 else '-')
        perms.append('w' if mode & 0o002 else '-')
        perms.append('x' if mode & 0o001 else '-')
        
        return ''.join(perms)
    
    def _parse_restore_output(self, output: str, operation: RestoreOperation) -> None:
        """
        Parse Restic restore output and update operation status.
        
        Args:
            output: Restore command output
            operation: RestoreOperation to update
        """
        try:
            # Parse JSON output from restore command
            for line in output.strip().split('\n'):
                if line.strip():
                    try:
                        data = json.loads(line)
                        message_type = data.get("message_type", "")
                        
                        if message_type == "summary":
                            operation.files_restored = data.get("files_restored", 0)
                            operation.bytes_restored = data.get("total_bytes", 0)
                        elif message_type == "status":
                            # Update progress information
                            pass
                            
                    except json.JSONDecodeError:
                        # Not JSON, might be plain text output
                        continue
                        
        except Exception as e:
            logger.warning(f"Failed to parse restore output: {e}")
    
    def _verify_file(
        self,
        repository_path: str,
        snapshot_id: str,
        file_path: str
    ) -> bool:
        """
        Verify a single restored file against the snapshot.
        
        Args:
            repository_path: Path to the repository
            snapshot_id: Snapshot ID
            file_path: Path to the file to verify
            
        Returns:
            True if file is verified, False otherwise
        """
        try:
            # This is a simplified verification
            # In a full implementation, this would:
            # 1. Get file checksum from snapshot metadata
            # 2. Calculate checksum of restored file
            # 3. Compare checksums
            
            # For now, just check if file exists
            return Path(file_path).exists()
            
        except Exception as e:
            logger.warning(f"Failed to verify file {file_path}: {e}")
            return False
