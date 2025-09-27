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
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Union
from enum import Enum
import logging

from .backup_repository import BackupRepository
from .backup_snapshot import BackupSnapshot
from .snapshot_manager import SnapshotManager
from .recovery_errors import (
    RestoreError, RestoreTargetError, RestorePermissionError,
    RestoreVerificationError, FileConflictError, InsufficientSpaceError,
    SnapshotCorruptedError, RestoreInterruptedError
)

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """Options for handling file conflicts during restore"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    KEEP_BOTH = "keep_both"
    PROMPT = "prompt"


class RestoreOptions:
    """Configuration options for restore operations"""

    def __init__(self):
        self.target_path: Optional[Path] = None
        self.include_paths: List[Path] = []
        self.exclude_paths: List[Path] = []
        self.conflict_resolution: ConflictResolution = ConflictResolution.PROMPT
        self.verify_after_restore: bool = True
        self.create_target_directory: bool = True
        self.preserve_permissions: bool = True
        self.dry_run: bool = False
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None

    def with_target_path(self, path: Union[str, Path]) -> 'RestoreOptions':
        """Set the target path for restore"""
        self.target_path = Path(path)
        return self

    def with_include_paths(self, paths: List[Union[str, Path]]) -> 'RestoreOptions':
        """Set paths to include in restore"""
        self.include_paths = [Path(p) for p in paths]
        return self

    def with_exclude_paths(self, paths: List[Union[str, Path]]) -> 'RestoreOptions':
        """Set paths to exclude from restore"""
        self.exclude_paths = [Path(p) for p in paths]
        return self

    def with_conflict_resolution(self, resolution: ConflictResolution) -> 'RestoreOptions':
        """Set conflict resolution strategy"""
        self.conflict_resolution = resolution
        return self

    def with_verification(self, verify: bool = True) -> 'RestoreOptions':
        """Enable/disable post-restore verification"""
        self.verify_after_restore = verify
        return self

    def with_dry_run(self, dry_run: bool = True) -> 'RestoreOptions':
        """Enable/disable dry run mode"""
        self.dry_run = dry_run
        return self

    def with_progress_callback(self, callback: Callable[[str, int, int], None]) -> 'RestoreOptions':
        """Set progress callback function"""
        self.progress_callback = callback
        return self


class RestoreResult:
    """Result of a restore operation"""

    def __init__(self):
        self.success: bool = False
        self.snapshot_id: str = ""
        self.target_path: Optional[Path] = None
        self.files_restored: int = 0
        self.files_skipped: int = 0
        self.files_failed: int = 0
        self.bytes_restored: int = 0
        self.duration_seconds: float = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.verification_passed: bool = False

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)

    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)


class RestoreManager:
    """Manages restore operations with comprehensive error handling and verification"""

    def __init__(self, repository: BackupRepository, snapshot_manager: Optional[SnapshotManager] = None):
        """
        Initialize RestoreManager
        
        Args:
            repository: BackupRepository instance
            snapshot_manager: Optional SnapshotManager instance
        """
        self.repository = repository
        self.snapshot_manager = snapshot_manager or SnapshotManager(repository)

    def restore_snapshot(self, snapshot_id: str, options: RestoreOptions) -> RestoreResult:
        """
        Restore a snapshot with comprehensive error handling
        
        Args:
            snapshot_id: ID of snapshot to restore
            options: Restore configuration options
            
        Returns:
            RestoreResult with operation details
            
        Raises:
            RestoreError: If restore operation fails
        """
        result = RestoreResult()
        result.snapshot_id = snapshot_id
        start_time = datetime.now()

        try:
            # Get snapshot
            snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)

            # Validate restore options
            self._validate_restore_options(options, result)

            # Pre-restore checks
            self._perform_pre_restore_checks(snapshot, options, result)

            if result.errors and not options.dry_run:
                result.success = False
                return result

            # Execute restore
            if options.dry_run:
                logger.info("Dry run mode - no files will be restored")
                result.success = True
            else:
                self._execute_restore(snapshot, options, result)

                # Post-restore verification
                if options.verify_after_restore and result.success:
                    result.verification_passed = self._verify_restore(snapshot, options, result)

        except Exception as e:
            logger.error(f"Restore operation failed: {e}")
            result.add_error(f"Restore failed: {e}")
            result.success = False

        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()

        return result

    def restore_latest_snapshot(self, options: RestoreOptions) -> RestoreResult:
        """
        Restore the latest available snapshot
        
        Args:
            options: Restore configuration options
            
        Returns:
            RestoreResult with operation details
        """
        latest_snapshot = self.snapshot_manager.get_latest_snapshot()
        if not latest_snapshot:
            result = RestoreResult()
            result.add_error("No snapshots found in repository")
            return result

        return self.restore_snapshot(latest_snapshot.id, options)

    def _validate_restore_options(self, options: RestoreOptions, result: RestoreResult):
        """Validate restore options"""
        if not options.target_path:
            result.add_error("Target path is required for restore operation")
            return

        result.target_path = options.target_path

        # Check if target path is valid
        try:
            if options.target_path.exists() and not options.target_path.is_dir():
                result.add_error(f"Target path exists but is not a directory: {options.target_path}")
        except PermissionError:
            result.add_error(f"Permission denied accessing target path: {options.target_path}")

    def _perform_pre_restore_checks(self, snapshot: BackupSnapshot,
                                    options: RestoreOptions, result: RestoreResult):
        """Perform pre-restore validation checks"""
        try:
            # Check snapshot integrity
            if not snapshot.verify():
                result.add_warning("Snapshot verification failed - restore may be incomplete")

            # Check target directory (only create if not in dry run mode)
            if options.create_target_directory and not options.target_path.exists() and not options.dry_run:
                try:
                    options.target_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created target directory: {options.target_path}")
                except PermissionError:
                    result.add_error(f"Permission denied creating target directory: {options.target_path}")
                    return

            # Check available space (only if target exists or will be created)
            if (options.target_path.exists() or options.create_target_directory) and not options.dry_run:
                target_for_check = options.target_path if options.target_path.exists() else options.target_path.parent
                self._check_available_space(snapshot, target_for_check, result)

            # Check for file conflicts
            if options.target_path.exists():
                self._check_file_conflicts(snapshot, options, result)

        except Exception as e:
            result.add_error(f"Pre-restore check failed: {e}")

    def _execute_restore(self, snapshot: BackupSnapshot, options: RestoreOptions, result: RestoreResult):
        """Execute the actual restore operation"""
        try:
            logger.info(f"Starting restore of snapshot {snapshot.id} to {options.target_path}")

            # Call repository restore method
            restore_output = snapshot.restore(options.target_path)

            # Parse restore output for statistics (implementation depends on repository type)
            self._parse_restore_output(restore_output, result)

            result.success = True
            logger.info(f"Restore completed successfully: {result.files_restored} files restored")

        except Exception as e:
            logger.error(f"Restore execution failed: {e}")
            result.add_error(f"Restore execution failed: {e}")
            result.success = False

    def _verify_restore(self, snapshot: BackupSnapshot, options: RestoreOptions,
                        result: RestoreResult) -> bool:
        """Verify the restored files"""
        try:
            logger.info("Verifying restored files...")

            # Basic verification - check if target directory exists and has content
            if not options.target_path.exists():
                result.add_error("Target directory does not exist after restore")
                return False

            # Count restored files
            restored_files = list(options.target_path.rglob('*'))
            file_count = len([f for f in restored_files if f.is_file()])

            if file_count == 0:
                result.add_warning("No files found in target directory after restore")
                return False

            logger.info(f"Verification completed: {file_count} files found in target directory")
            return True

        except Exception as e:
            logger.error(f"Restore verification failed: {e}")
            result.add_error(f"Verification failed: {e}")
            return False

    def _check_available_space(self, snapshot: BackupSnapshot, target_path: Path, result: RestoreResult):
        """Check if there's enough space for restore"""
        try:
            # Get snapshot size
            snapshot_stats = snapshot.get_stats()
            required_bytes = snapshot_stats.get('total_size', 0)

            # Get available space
            stat = shutil.disk_usage(target_path)
            available_bytes = stat.free

            if required_bytes > available_bytes:
                result.add_error(f"Insufficient disk space: need {required_bytes} bytes, "
                                 f"available {available_bytes} bytes")

        except Exception as e:
            result.add_warning(f"Could not check available disk space: {e}")

    def _check_file_conflicts(self, snapshot: BackupSnapshot, options: RestoreOptions, result: RestoreResult):
        """Check for potential file conflicts"""
        try:
            # This is a simplified check - in a real implementation,
            # we would need to examine the snapshot contents
            existing_files = list(options.target_path.rglob('*'))
            if existing_files:
                file_count = len([f for f in existing_files if f.is_file()])
                if file_count > 0:
                    if options.conflict_resolution == ConflictResolution.SKIP:
                        result.add_warning(f"Target directory contains {file_count} files - "
                                           "conflicts will be skipped")
                    elif options.conflict_resolution == ConflictResolution.OVERWRITE:
                        result.add_warning(f"Target directory contains {file_count} files - "
                                           "existing files will be overwritten")
                    else:
                        result.add_warning(f"Target directory contains {file_count} files - "
                                           "manual conflict resolution may be required")

        except Exception as e:
            result.add_warning(f"Could not check for file conflicts: {e}")

    def _parse_restore_output(self, output: str, result: RestoreResult):
        """Parse restore command output for statistics"""
        # This is a simplified implementation
        # Real implementation would parse actual restic output
        result.files_restored = 1  # Placeholder
        result.bytes_restored = 0  # Placeholder

        if "error" in output.lower():
            result.add_warning("Restore completed with warnings - check logs for details")
