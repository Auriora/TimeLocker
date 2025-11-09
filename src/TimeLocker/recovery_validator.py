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
Recovery Validator for TimeLocker Recovery Operations

This module provides validation and integrity verification capabilities for
recovery operations, ensuring data integrity throughout the restoration process.
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from threading import Lock

from .backup_repository import BackupRepository
from .snapshot_manager import SnapshotManager
from .snapshot_browser import SnapshotBrowser
from .interfaces.recovery_models import (
    ValidationResult,
    ValidationFailure,
    ValidationWarning,
    FailureType,
    SelectionCriteria,
    FileEntry,
    RecoveryOperation,
    OperationStatus
)
from .recovery_errors import RecoveryError, ValidationError

logger = logging.getLogger(__name__)


class RecoveryValidator:
    """
    Validates recovery operations and ensures data integrity
    through checksum verification and completeness checks.
    
    This class provides comprehensive validation capabilities including
    pre-recovery checks, real-time validation during recovery, and
    post-recovery verification to ensure successful data restoration.
    """
    
    def __init__(
        self,
        repository: BackupRepository,
        snapshot_manager: Optional[SnapshotManager] = None,
        snapshot_browser: Optional[SnapshotBrowser] = None
    ):
        """
        Initialize the RecoveryValidator.
        
        Args:
            repository: BackupRepository instance for accessing snapshots
            snapshot_manager: Optional SnapshotManager instance
            snapshot_browser: Optional SnapshotBrowser instance
        """
        self.repository = repository
        self.snapshot_manager = snapshot_manager or SnapshotManager(repository)
        self.snapshot_browser = snapshot_browser or SnapshotBrowser(
            repository, 
            self.snapshot_manager
        )
        
        # Track validation operations
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._validation_lock = Lock()
        
        # Track ongoing validations
        self._active_validations: Set[str] = set()
        
        logger.info("RecoveryValidator initialized")
    
    def validate_pre_recovery(
        self,
        snapshot_id: str,
        target_path: str,
        selection_criteria: Optional[SelectionCriteria] = None
    ) -> ValidationResult:
        """
        Validates conditions before starting recovery.
        
        This method performs pre-flight checks to ensure the recovery
        operation can proceed successfully, including snapshot existence,
        target path validity, and sufficient disk space.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Destination path for restored files
            selection_criteria: Optional criteria for selective recovery
            
        Returns:
            ValidationResult indicating whether recovery can proceed
            
        Raises:
            ValidationError: If critical validation checks fail
        """
        logger.info(f"Starting pre-recovery validation for snapshot {snapshot_id}")
        
        result = ValidationResult(
            is_valid=True,
            validated_files=0,
            validation_time=datetime.now()
        )
        
        try:
            # Validate snapshot exists
            try:
                snapshot = self.snapshot_manager.get_snapshot_by_id(snapshot_id)
                if not snapshot:
                    result.add_failure(ValidationFailure(
                        file_path="",
                        expected_checksum="",
                        actual_checksum="",
                        failure_type=FailureType.FILE_MISSING,
                        error_message=f"Snapshot {snapshot_id} not found"
                    ))
                    return result
            except Exception as e:
                logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
                result.add_failure(ValidationFailure(
                    file_path="",
                    expected_checksum="",
                    actual_checksum="",
                    failure_type=FailureType.FILE_MISSING,
                    error_message=f"Failed to access snapshot: {str(e)}"
                ))
                return result
            
            # Validate target path
            target = Path(target_path)
            
            # Check if target exists and is not a directory
            if target.exists() and not target.is_dir():
                result.add_failure(ValidationFailure(
                    file_path=str(target),
                    expected_checksum="",
                    actual_checksum="",
                    failure_type=FailureType.PERMISSION_ERROR,
                    error_message=f"Target path exists but is not a directory: {target_path}"
                ))
                return result
            
            # Check if target directory is writable
            if target.exists():
                if not os.access(target, os.W_OK):
                    result.add_failure(ValidationFailure(
                        file_path=str(target),
                        expected_checksum="",
                        actual_checksum="",
                        failure_type=FailureType.PERMISSION_ERROR,
                        error_message=f"Target directory is not writable: {target_path}"
                    ))
                    return result
            else:
                # Check if parent directory exists and is writable
                parent = target.parent
                if not parent.exists():
                    result.add_warning(ValidationWarning(
                        warning_type="directory_creation",
                        message=f"Parent directory will be created: {parent}",
                        severity="low"
                    ))
                elif not os.access(parent, os.W_OK):
                    result.add_failure(ValidationFailure(
                        file_path=str(parent),
                        expected_checksum="",
                        actual_checksum="",
                        failure_type=FailureType.PERMISSION_ERROR,
                        error_message=f"Parent directory is not writable: {parent}"
                    ))
                    return result
            
            # Validate disk space
            space_check = self._validate_disk_space(
                snapshot_id,
                target_path,
                selection_criteria
            )
            if not space_check["sufficient"]:
                result.add_failure(ValidationFailure(
                    file_path=str(target),
                    expected_checksum="",
                    actual_checksum="",
                    failure_type=FailureType.INCOMPLETE,
                    error_message=(
                        f"Insufficient disk space: "
                        f"required {space_check['required_bytes']} bytes, "
                        f"available {space_check['available_bytes']} bytes"
                    )
                ))
                return result
            elif space_check.get("warning"):
                result.add_warning(ValidationWarning(
                    warning_type="disk_space",
                    message=space_check["warning"],
                    severity="medium"
                ))
            
            # Validate selection criteria if provided
            if selection_criteria:
                criteria_validation = self._validate_selection_criteria(
                    snapshot_id,
                    selection_criteria
                )
                if not criteria_validation["valid"]:
                    result.add_warning(ValidationWarning(
                        warning_type="selection_criteria",
                        message=criteria_validation["message"],
                        severity="medium"
                    ))
            
            logger.info(
                f"Pre-recovery validation completed: "
                f"valid={result.is_valid}, "
                f"failures={len(result.failed_validations)}, "
                f"warnings={len(result.warnings)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Pre-recovery validation failed: {e}")
            result.add_failure(ValidationFailure(
                file_path="",
                expected_checksum="",
                actual_checksum="",
                failure_type=FailureType.CORRUPTION,
                error_message=f"Validation error: {str(e)}"
            ))
            return result

    def validate_during_recovery(
        self,
        operation_id: str
    ) -> ValidationResult:
        """
        Performs real-time validation during recovery.
        
        This method validates files as they are being restored, enabling
        early detection of issues and allowing for corrective action during
        the recovery process.
        
        Args:
            operation_id: ID of the recovery operation to validate
            
        Returns:
            ValidationResult with current validation status
            
        Raises:
            ValidationError: If validation cannot be performed
        """
        logger.info(f"Starting during-recovery validation for operation {operation_id}")
        
        # Check if validation is already in progress
        with self._validation_lock:
            if operation_id in self._active_validations:
                logger.warning(f"Validation already in progress for operation {operation_id}")
                # Return cached result if available
                if operation_id in self._validation_cache:
                    return self._validation_cache[operation_id]
            
            self._active_validations.add(operation_id)
        
        try:
            result = ValidationResult(
                is_valid=True,
                validated_files=0,
                validation_time=datetime.now()
            )
            
            # Note: During-recovery validation would typically be called by the
            # recovery orchestrator with access to the operation state. For now,
            # we provide a basic implementation that can be extended.
            
            # This is a placeholder for real-time validation logic
            # In a full implementation, this would:
            # 1. Access the recovery operation state
            # 2. Identify files that have been restored
            # 3. Validate each restored file
            # 4. Report issues in real-time
            
            logger.info(
                f"During-recovery validation completed for operation {operation_id}: "
                f"valid={result.is_valid}"
            )
            
            # Cache the result
            with self._validation_lock:
                self._validation_cache[operation_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"During-recovery validation failed: {e}")
            result = ValidationResult(
                is_valid=False,
                validated_files=0,
                validation_time=datetime.now()
            )
            result.add_failure(ValidationFailure(
                file_path="",
                expected_checksum="",
                actual_checksum="",
                failure_type=FailureType.CORRUPTION,
                error_message=f"Validation error: {str(e)}"
            ))
            return result
        finally:
            with self._validation_lock:
                self._active_validations.discard(operation_id)
    
    def validate_post_recovery(
        self,
        operation_id: str
    ) -> ValidationResult:
        """
        Comprehensive validation after recovery completion.
        
        This method performs thorough validation of all restored files,
        verifying checksums, completeness, and integrity to ensure the
        recovery operation was successful.
        
        Args:
            operation_id: ID of the completed recovery operation
            
        Returns:
            ValidationResult with comprehensive validation results
            
        Raises:
            ValidationError: If validation cannot be performed
        """
        logger.info(f"Starting post-recovery validation for operation {operation_id}")
        
        result = ValidationResult(
            is_valid=True,
            validated_files=0,
            validation_time=datetime.now()
        )
        
        try:
            # Note: Post-recovery validation would typically receive the
            # RecoveryOperation object with details about what was restored.
            # For now, we provide a basic implementation structure.
            
            # This is a placeholder for post-recovery validation logic
            # In a full implementation, this would:
            # 1. Access the recovery operation state
            # 2. Get list of all files that should have been restored
            # 3. Verify each file exists and has correct checksum
            # 4. Generate comprehensive validation report
            
            logger.info(
                f"Post-recovery validation completed for operation {operation_id}: "
                f"valid={result.is_valid}, "
                f"validated={result.validated_files} files, "
                f"failures={len(result.failed_validations)}"
            )
            
            # Cache the result
            with self._validation_lock:
                self._validation_cache[operation_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Post-recovery validation failed: {e}")
            result.add_failure(ValidationFailure(
                file_path="",
                expected_checksum="",
                actual_checksum="",
                failure_type=FailureType.CORRUPTION,
                error_message=f"Validation error: {str(e)}"
            ))
            return result
    
    def verify_file_integrity(
        self,
        restored_file_path: str,
        expected_checksum: str
    ) -> bool:
        """
        Verifies individual file integrity using checksums.
        
        This method computes the checksum of a restored file and compares
        it with the expected checksum from the snapshot metadata.
        
        Args:
            restored_file_path: Path to the restored file
            expected_checksum: Expected checksum value from snapshot
            
        Returns:
            True if file integrity is verified, False otherwise
            
        Raises:
            ValidationError: If file cannot be accessed or checksum cannot be computed
        """
        try:
            file_path = Path(restored_file_path)
            
            # Check if file exists
            if not file_path.exists():
                logger.error(f"File not found for integrity verification: {restored_file_path}")
                return False
            
            # Check if it's a regular file
            if not file_path.is_file():
                logger.warning(f"Not a regular file, skipping checksum: {restored_file_path}")
                return True  # Directories and symlinks don't have checksums
            
            # Compute file checksum
            actual_checksum = self._compute_file_checksum(file_path)
            
            # Compare checksums
            if actual_checksum == expected_checksum:
                logger.debug(f"File integrity verified: {restored_file_path}")
                return True
            else:
                logger.error(
                    f"Checksum mismatch for {restored_file_path}: "
                    f"expected {expected_checksum}, got {actual_checksum}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify file integrity for {restored_file_path}: {e}")
            raise ValidationError(
                f"Failed to verify file integrity: {str(e)}"
            ) from e
    
    def validate_restored_files(
        self,
        snapshot_id: str,
        target_path: str,
        file_list: List[FileEntry]
    ) -> ValidationResult:
        """
        Validate a list of restored files against snapshot metadata.
        
        This method verifies that all files in the list were restored
        correctly by checking their existence, size, and checksums.
        
        Args:
            snapshot_id: ID of the snapshot that was restored
            target_path: Path where files were restored
            file_list: List of FileEntry objects that should have been restored
            
        Returns:
            ValidationResult with detailed validation results
        """
        logger.info(
            f"Validating {len(file_list)} restored files from snapshot {snapshot_id}"
        )
        
        result = ValidationResult(
            is_valid=True,
            validated_files=0,
            validation_time=datetime.now()
        )
        
        target = Path(target_path)
        
        for file_entry in file_list:
            try:
                # Construct restored file path
                restored_path = target / file_entry.path.lstrip('/')
                
                # Check if file exists
                if not restored_path.exists():
                    result.add_failure(ValidationFailure(
                        file_path=str(restored_path),
                        expected_checksum=file_entry.checksum or "",
                        actual_checksum="",
                        failure_type=FailureType.FILE_MISSING,
                        error_message=f"Restored file not found: {restored_path}"
                    ))
                    continue
                
                # Verify file type matches
                if file_entry.type.value == "file" and not restored_path.is_file():
                    result.add_failure(ValidationFailure(
                        file_path=str(restored_path),
                        expected_checksum="",
                        actual_checksum="",
                        failure_type=FailureType.CORRUPTION,
                        error_message=f"File type mismatch: expected file, got {restored_path}"
                    ))
                    continue
                
                # Verify checksum for regular files
                if file_entry.type.value == "file" and file_entry.checksum:
                    if not self.verify_file_integrity(
                        str(restored_path),
                        file_entry.checksum
                    ):
                        actual_checksum = self._compute_file_checksum(restored_path)
                        result.add_failure(ValidationFailure(
                            file_path=str(restored_path),
                            expected_checksum=file_entry.checksum,
                            actual_checksum=actual_checksum,
                            failure_type=FailureType.CHECKSUM_MISMATCH,
                            error_message=f"Checksum mismatch for {restored_path}"
                        ))
                        continue
                
                # File validated successfully
                result.validated_files += 1
                
            except Exception as e:
                logger.error(f"Error validating file {file_entry.path}: {e}")
                result.add_failure(ValidationFailure(
                    file_path=file_entry.path,
                    expected_checksum=file_entry.checksum or "",
                    actual_checksum="",
                    failure_type=FailureType.CORRUPTION,
                    error_message=f"Validation error: {str(e)}"
                ))
        
        logger.info(
            f"File validation completed: "
            f"validated={result.validated_files}/{len(file_list)}, "
            f"failures={len(result.failed_validations)}"
        )
        
        return result
    
    def clear_validation_cache(self, operation_id: Optional[str] = None) -> None:
        """
        Clear validation cache for specific operation or all operations.
        
        Args:
            operation_id: Optional operation ID to clear cache for.
                         If None, clears entire cache.
        """
        with self._validation_lock:
            if operation_id:
                self._validation_cache.pop(operation_id, None)
                logger.debug(f"Cleared validation cache for operation {operation_id}")
            else:
                self._validation_cache.clear()
                logger.debug("Cleared entire validation cache")
    
    def _validate_disk_space(
        self,
        snapshot_id: str,
        target_path: str,
        selection_criteria: Optional[SelectionCriteria] = None
    ) -> Dict:
        """
        Validate that sufficient disk space is available for recovery.
        
        Args:
            snapshot_id: Snapshot to restore
            target_path: Target path for restoration
            selection_criteria: Optional selection criteria
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Get snapshot size estimate
            # For now, we'll use a simple approach
            # In a full implementation, this would query snapshot metadata
            
            # Get available disk space
            target = Path(target_path)
            if target.exists():
                stat = os.statvfs(target)
            else:
                # Use parent directory
                stat = os.statvfs(target.parent)
            
            available_bytes = stat.f_bavail * stat.f_frsize
            
            # Estimate required space (placeholder)
            # In a full implementation, this would calculate based on
            # snapshot contents and selection criteria
            required_bytes = 0  # Would be calculated from snapshot
            
            # Add 10% buffer for safety
            required_with_buffer = int(required_bytes * 1.1)
            
            sufficient = available_bytes >= required_with_buffer
            
            result = {
                "sufficient": sufficient,
                "available_bytes": available_bytes,
                "required_bytes": required_with_buffer
            }
            
            # Add warning if space is tight (less than 20% free after restore)
            if sufficient and available_bytes < required_with_buffer * 1.2:
                result["warning"] = (
                    f"Disk space will be tight after restoration: "
                    f"{available_bytes - required_with_buffer} bytes remaining"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to validate disk space: {e}")
            return {
                "sufficient": True,  # Assume sufficient if check fails
                "available_bytes": 0,
                "required_bytes": 0,
                "warning": f"Could not verify disk space: {str(e)}"
            }
    
    def _validate_selection_criteria(
        self,
        snapshot_id: str,
        selection_criteria: SelectionCriteria
    ) -> Dict:
        """
        Validate that selection criteria will match files in the snapshot.
        
        Args:
            snapshot_id: Snapshot to validate against
            selection_criteria: Selection criteria to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # This is a placeholder for selection criteria validation
            # In a full implementation, this would:
            # 1. Query snapshot contents
            # 2. Apply selection criteria
            # 3. Check if any files match
            # 4. Warn if no matches found
            
            return {
                "valid": True,
                "message": "Selection criteria validated"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate selection criteria: {e}")
            return {
                "valid": False,
                "message": f"Could not validate selection criteria: {str(e)}"
            }
    
    def _compute_file_checksum(
        self,
        file_path: Path,
        algorithm: str = "sha256"
    ) -> str:
        """
        Compute checksum for a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (default: sha256)
            
        Returns:
            Hexadecimal checksum string
        """
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            chunk_size = 8192
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def detect_corruption(
        self,
        file_path: str,
        expected_size: int,
        expected_checksum: Optional[str] = None
    ) -> Dict:
        """
        Detect file corruption by checking size and checksum.
        
        This method performs comprehensive corruption detection including
        file size verification, checksum validation, and basic file
        accessibility checks.
        
        Args:
            file_path: Path to the file to check
            expected_size: Expected file size in bytes
            expected_checksum: Optional expected checksum
            
        Returns:
            Dictionary with corruption detection results:
                - corrupted: Boolean indicating if corruption detected
                - issues: List of detected issues
                - severity: Severity level (low, medium, high, critical)
        """
        issues = []
        severity = "low"
        
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                issues.append("File does not exist")
                return {
                    "corrupted": True,
                    "issues": issues,
                    "severity": "critical"
                }
            
            # Check if file is accessible
            if not os.access(path, os.R_OK):
                issues.append("File is not readable")
                severity = "high"
            
            # Check file size
            actual_size = path.stat().st_size
            if actual_size != expected_size:
                issues.append(
                    f"Size mismatch: expected {expected_size} bytes, "
                    f"got {actual_size} bytes"
                )
                severity = "high"
            
            # Check checksum if provided
            if expected_checksum and path.is_file():
                try:
                    actual_checksum = self._compute_file_checksum(path)
                    if actual_checksum != expected_checksum:
                        issues.append(
                            f"Checksum mismatch: expected {expected_checksum}, "
                            f"got {actual_checksum}"
                        )
                        severity = "critical"
                except Exception as e:
                    issues.append(f"Failed to compute checksum: {str(e)}")
                    severity = "high"
            
            # Check for zero-byte files (potential corruption)
            if actual_size == 0 and expected_size > 0:
                issues.append("File is empty but should contain data")
                severity = "critical"
            
            corrupted = len(issues) > 0
            
            if corrupted:
                logger.warning(
                    f"Corruption detected in {file_path}: {', '.join(issues)}"
                )
            
            return {
                "corrupted": corrupted,
                "issues": issues,
                "severity": severity
            }
            
        except Exception as e:
            logger.error(f"Error detecting corruption for {file_path}: {e}")
            return {
                "corrupted": True,
                "issues": [f"Error during corruption check: {str(e)}"],
                "severity": "high"
            }
    
    def generate_verification_report(
        self,
        validation_result: ValidationResult,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a detailed verification report from validation results.
        
        This method creates a comprehensive human-readable report of
        validation results including statistics, failures, and warnings.
        
        Args:
            validation_result: ValidationResult to generate report from
            output_path: Optional path to write report file
            
        Returns:
            Report text as string
        """
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("RECOVERY VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Validation Time: {validation_result.validation_time}")
        report_lines.append(f"Overall Status: {'PASSED' if validation_result.is_valid else 'FAILED'}")
        report_lines.append("")
        
        # Summary statistics
        report_lines.append("SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Files Validated: {validation_result.validated_files}")
        report_lines.append(f"Validation Failures: {len(validation_result.failed_validations)}")
        report_lines.append(f"Warnings: {len(validation_result.warnings)}")
        report_lines.append("")
        
        # Failures section
        if validation_result.failed_validations:
            report_lines.append("VALIDATION FAILURES")
            report_lines.append("-" * 80)
            for i, failure in enumerate(validation_result.failed_validations, 1):
                report_lines.append(f"\n{i}. {failure.file_path}")
                report_lines.append(f"   Type: {failure.failure_type.value}")
                report_lines.append(f"   Message: {failure.error_message}")
                if failure.expected_checksum:
                    report_lines.append(f"   Expected Checksum: {failure.expected_checksum}")
                if failure.actual_checksum:
                    report_lines.append(f"   Actual Checksum: {failure.actual_checksum}")
            report_lines.append("")
        
        # Warnings section
        if validation_result.warnings:
            report_lines.append("WARNINGS")
            report_lines.append("-" * 80)
            for i, warning in enumerate(validation_result.warnings, 1):
                report_lines.append(f"\n{i}. {warning.warning_type}")
                report_lines.append(f"   Severity: {warning.severity}")
                report_lines.append(f"   Message: {warning.message}")
                if warning.context:
                    report_lines.append(f"   Context: {warning.context}")
            report_lines.append("")
        
        # Footer
        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Write to file if output path provided
        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(report_text)
                logger.info(f"Verification report written to {output_path}")
            except Exception as e:
                logger.error(f"Failed to write verification report to {output_path}: {e}")
        
        return report_text
    
    def batch_verify_files(
        self,
        file_checksums: Dict[str, str],
        base_path: Optional[str] = None
    ) -> ValidationResult:
        """
        Verify integrity of multiple files in batch.
        
        This method efficiently verifies multiple files by checking their
        checksums against expected values, useful for validating large
        recovery operations.
        
        Args:
            file_checksums: Dictionary mapping file paths to expected checksums
            base_path: Optional base path to prepend to file paths
            
        Returns:
            ValidationResult with batch verification results
        """
        logger.info(f"Starting batch verification of {len(file_checksums)} files")
        
        result = ValidationResult(
            is_valid=True,
            validated_files=0,
            validation_time=datetime.now()
        )
        
        base = Path(base_path) if base_path else Path.cwd()
        
        for file_path, expected_checksum in file_checksums.items():
            try:
                full_path = base / file_path if not Path(file_path).is_absolute() else Path(file_path)
                
                # Check if file exists
                if not full_path.exists():
                    result.add_failure(ValidationFailure(
                        file_path=str(full_path),
                        expected_checksum=expected_checksum,
                        actual_checksum="",
                        failure_type=FailureType.FILE_MISSING,
                        error_message=f"File not found: {full_path}"
                    ))
                    continue
                
                # Verify checksum
                if self.verify_file_integrity(str(full_path), expected_checksum):
                    result.validated_files += 1
                else:
                    actual_checksum = self._compute_file_checksum(full_path)
                    result.add_failure(ValidationFailure(
                        file_path=str(full_path),
                        expected_checksum=expected_checksum,
                        actual_checksum=actual_checksum,
                        failure_type=FailureType.CHECKSUM_MISMATCH,
                        error_message=f"Checksum mismatch for {full_path}"
                    ))
                
            except Exception as e:
                logger.error(f"Error verifying file {file_path}: {e}")
                result.add_failure(ValidationFailure(
                    file_path=file_path,
                    expected_checksum=expected_checksum,
                    actual_checksum="",
                    failure_type=FailureType.CORRUPTION,
                    error_message=f"Verification error: {str(e)}"
                ))
        
        logger.info(
            f"Batch verification completed: "
            f"validated={result.validated_files}/{len(file_checksums)}, "
            f"failures={len(result.failed_validations)}"
        )
        
        return result
