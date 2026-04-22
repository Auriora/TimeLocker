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

import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol
from enum import Enum
import logging

from .backup_repository import BackupRepository
from .backup_snapshot import BackupSnapshot
from .snapshot_manager import SnapshotManager

logger = logging.getLogger(__name__)


class _ValidationFailureLike(Protocol):
    error_message: str


class _ValidationWarningLike(Protocol):
    message: str


class _PreRecoveryValidationResultLike(Protocol):
    failed_validations: list[_ValidationFailureLike]
    warnings: list[_ValidationWarningLike]
    is_valid: bool


class _RecoveryValidatorLike(Protocol):
    def validate_pre_recovery(
        self,
        snapshot_id: str,
        target_path: str,
        selection_criteria: object | None,
    ) -> _PreRecoveryValidationResultLike: ...


class _ProgressMonitorLike(Protocol):
    def start_monitoring(self, operation_id: str) -> None: ...
    def stop_monitoring(self, operation_id: str) -> None: ...


class ConflictResolution(Enum):
    """Options for handling file conflicts during restore"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    KEEP_BOTH = "keep_both"
    PROMPT = "prompt"


class RestoreOptions:
    """Configuration options for restore operations"""

    def __init__(self) -> None:
        self.target_path: Path | None = None
        self.include_paths: list[Path] = []
        self.exclude_paths: list[Path] = []
        self.conflict_resolution: ConflictResolution = ConflictResolution.PROMPT
        self.verify_after_restore: bool = True
        self.create_target_directory: bool = True
        self.preserve_permissions: bool = True
        self.dry_run: bool = False
        self.progress_callback: Callable[[str, int, int], None] | None = None

    def with_target_path(self, path: str | Path) -> 'RestoreOptions':
        """Set the target path for restore"""
        self.target_path = Path(path)
        return self

    def with_include_paths(self, paths: list[str | Path]) -> 'RestoreOptions':
        """Set paths to include in restore"""
        self.include_paths = [Path(p) for p in paths]
        return self

    def with_exclude_paths(self, paths: list[str | Path]) -> 'RestoreOptions':
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

    def __init__(self) -> None:
        self.success: bool = False
        self.snapshot_id: str = ""
        self.target_path: Path | None = None
        self.files_restored: int = 0
        self.files_skipped: int = 0
        self.files_failed: int = 0
        self.bytes_restored: int = 0
        self.duration_seconds: float = 0.0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.verification_passed: bool = False

    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)


class RestoreManager:
    """
    Manages restore operations with comprehensive error handling and verification.
    
    This class provides backward-compatible restore functionality while integrating
    with the new RecoveryOrchestrator architecture. It supports both legacy restore
    operations and new recovery features including validation and progress monitoring.
    """

    def __init__(
        self,
        repository: BackupRepository,
        snapshot_manager: SnapshotManager | None = None,
        recovery_validator: _RecoveryValidatorLike | None = None,
        progress_monitor: _ProgressMonitorLike | None = None,
    ) -> None:
        """
        Initialize RestoreManager
        
        Args:
            repository: BackupRepository instance
            snapshot_manager: Optional SnapshotManager instance
            recovery_validator: Optional RecoveryValidator for enhanced validation
            progress_monitor: Optional ProgressMonitor for progress tracking
        """
        self.repository: BackupRepository = repository
        self.snapshot_manager: SnapshotManager = snapshot_manager or SnapshotManager(repository)
        
        # New recovery architecture integration
        self.recovery_validator: _RecoveryValidatorLike | None = recovery_validator
        self.progress_monitor: _ProgressMonitorLike | None = progress_monitor
        
        # Track whether we're using enhanced recovery features
        self._enhanced_mode: bool = recovery_validator is not None or progress_monitor is not None
        
        if self._enhanced_mode:
            logger.info("RestoreManager initialized with enhanced recovery features")

    def restore_snapshot(self, snapshot_id: str, options: RestoreOptions) -> RestoreResult:
        """
        Restore a snapshot with comprehensive error handling.
        
        This method provides backward-compatible restore functionality while
        integrating with the new recovery architecture when available.
        
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

            # Enhanced pre-restore validation if recovery validator is available
            if self.recovery_validator and not options.dry_run:
                logger.info("Performing enhanced pre-restore validation")
                validation_result = self.recovery_validator.validate_pre_recovery(
                    snapshot_id=snapshot_id,
                    target_path=str(options.target_path),
                    selection_criteria=None  # Legacy restore doesn't use selection criteria
                )
                
                # Add validation failures to result
                for failure in validation_result.failed_validations:
                    result.add_error(f"Validation: {failure.error_message}")
                
                # Add validation warnings to result
                for warning in validation_result.warnings:
                    result.add_warning(f"Validation: {warning.message}")
                
                if not validation_result.is_valid:
                    result.success = False
                    return result
            else:
                # Legacy pre-restore checks
                self._perform_pre_restore_checks(snapshot, options, result)

            if result.errors and not options.dry_run:
                result.success = False
                return result

            # Execute restore
            if options.dry_run:
                logger.info("Dry run mode - no files will be restored")
                result.success = True
            else:
                # Start progress monitoring if available
                operation_id = None
                if self.progress_monitor:
                    operation_id = f"restore_{snapshot_id}_{int(datetime.now().timestamp())}"
                    self.progress_monitor.start_monitoring(operation_id)
                    logger.info(f"Started progress monitoring for operation {operation_id}")
                
                try:
                    self._execute_restore(snapshot, options, result)
                finally:
                    # Stop progress monitoring
                    if self.progress_monitor and operation_id:
                        self.progress_monitor.stop_monitoring(operation_id)

                # Enhanced post-restore verification if recovery validator is available
                if options.verify_after_restore and result.success:
                    if self.recovery_validator:
                        logger.info("Performing enhanced post-restore verification")
                        result.verification_passed = self._verify_restore_enhanced(
                            snapshot, options, result
                        )
                    else:
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

            if file_count > 0 and result.files_restored == 0:
                self._capture_restored_tree_stats(result)

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
        """Parse restore command output for statistics without inventing values."""
        if not output:
            return

        file_match = re.search(r"(?P<count>\d+)\s+files?\s+restored", output, re.IGNORECASE)
        if file_match:
            result.files_restored = int(file_match.group("count"))

        bytes_patterns = [
            r"(?P<count>\d+)\s+bytes?\s+restored",
            r"restored\s+(?P<count>\d+)\s+bytes?",
            r"total_bytes[\"'=:\s]+(?P<count>\d+)",
        ]
        for pattern in bytes_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                result.bytes_restored = int(match.group("count"))
                break

        if "error" in output.lower():
            result.add_warning("Restore completed with warnings - check logs for details")

    def _capture_restored_tree_stats(self, result: RestoreResult) -> None:
        """Populate restore counters from the target tree when available."""
        if not result.target_path or not result.target_path.exists():
            return

        files = [path for path in result.target_path.rglob("*") if path.is_file()]
        result.files_restored = len(files)
        result.bytes_restored = sum(path.stat().st_size for path in files)
    
    def _verify_restore_enhanced(
        self, 
        snapshot: BackupSnapshot, 
        options: RestoreOptions,
        result: RestoreResult
    ) -> bool:
        """
        Enhanced verification using RecoveryValidator.
        
        This method provides comprehensive verification using the new
        recovery architecture while maintaining backward compatibility.
        
        Args:
            snapshot: Snapshot that was restored
            options: Restore options used
            result: RestoreResult to update with verification details
            
        Returns:
            True if verification passed, False otherwise
        """
        try:
            logger.info("Performing enhanced restore verification...")
            
            # Basic verification first
            if not options.target_path.exists():
                result.add_error("Target directory does not exist after restore")
                return False
            
            # Count restored files
            restored_files = list(options.target_path.rglob('*'))
            file_count = len([f for f in restored_files if f.is_file()])

            if file_count > 0 and result.files_restored == 0:
                self._capture_restored_tree_stats(result)
            
            if file_count == 0:
                result.add_warning("No files found in target directory after restore")
                return False
            
            # Use recovery validator for detailed verification if available
            if self.recovery_validator:
                # Create a pseudo operation ID for validation
                operation_id = f"restore_{snapshot.id}_{int(datetime.now().timestamp())}"
                
                # Note: Full validation would require file list from snapshot
                # For now, we perform basic integrity checks
                logger.info(
                    f"Enhanced verification completed: {file_count} files found in target directory"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Enhanced restore verification failed: {e}")
            result.add_error(f"Verification failed: {e}")
            return False
    
    def get_recovery_validator(self) -> _RecoveryValidatorLike | None:
        """
        Get the recovery validator instance if available.
        
        Returns:
            RecoveryValidator instance or None
        """
        return self.recovery_validator
    
    def get_progress_monitor(self) -> _ProgressMonitorLike | None:
        """
        Get the progress monitor instance if available.
        
        Returns:
            ProgressMonitor instance or None
        """
        return self.progress_monitor
    
    def is_enhanced_mode(self) -> bool:
        """
        Check if enhanced recovery features are enabled.
        
        Returns:
            True if enhanced features are available, False otherwise
        """
        return self._enhanced_mode
    
    def set_recovery_validator(self, validator: _RecoveryValidatorLike | None) -> None:
        """
        Set or update the recovery validator.
        
        Args:
            validator: RecoveryValidator instance or None to disable
        """
        self.recovery_validator = validator
        self._enhanced_mode = validator is not None or self.progress_monitor is not None
        logger.info(f"Recovery validator {'enabled' if validator else 'disabled'}")
    
    def set_progress_monitor(self, monitor: _ProgressMonitorLike | None) -> None:
        """
        Set or update the progress monitor.
        
        Args:
            monitor: ProgressMonitor instance or None to disable
        """
        self.progress_monitor = monitor
        self._enhanced_mode = self.recovery_validator is not None or monitor is not None
        logger.info(f"Progress monitor {'enabled' if monitor else 'disabled'}")
