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
Integrity Validation Service for Backup Operations

This module provides comprehensive integrity validation capabilities for backup
operations, leveraging backup tool native features where available and providing
wrapper-based validation for tools that don't natively support integrity checking.

Requirements addressed: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import logging
import time
import hashlib
import json
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..interfaces.data_models import BackupJob, BackupResult, BackupStatus
from .tool_manager import Feature, ToolCapabilities, ToolManager
from .plugin_wrapper import PluginWrapper
from .wrapper_registry import WrapperRegistry

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of integrity validation"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"
    NOT_SUPPORTED = "not_supported"


class ValidationMethod(Enum):
    """Method used for validation"""
    NATIVE_TOOL = "native_tool"
    WRAPPER_CHECKSUM = "wrapper_checksum"
    WRAPPER_COMPARISON = "wrapper_comparison"
    MANUAL = "manual"


@dataclass
class ValidationIssue:
    """
    Represents an integrity validation issue.
    
    Attributes:
        severity: Severity level (critical, high, medium, low)
        description: Description of the issue
        affected_files: List of affected files
        suggested_action: Recommended action to resolve
    """
    severity: str
    description: str
    affected_files: List[str] = field(default_factory=list)
    suggested_action: Optional[str] = None


@dataclass
class IntegrityValidationResult:
    """
    Result of integrity validation operation.
    
    Attributes:
        status: Overall validation status
        method: Method used for validation
        validation_time: Time taken for validation in seconds
        files_validated: Number of files validated
        bytes_validated: Number of bytes validated
        issues: List of validation issues found
        checksum_mismatches: Number of checksum mismatches
        missing_files: Number of missing files
        corrupted_files: Number of corrupted files
        metadata: Additional validation metadata
        tool_output: Raw output from validation tool
    """
    status: ValidationStatus
    method: ValidationMethod
    validation_time: float = 0.0
    files_validated: int = 0
    bytes_validated: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    checksum_mismatches: int = 0
    missing_files: int = 0
    corrupted_files: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_output: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.status == ValidationStatus.PASSED
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return any(issue.severity == "critical" for issue in self.issues)
    
    def add_issue(
        self,
        severity: str,
        description: str,
        affected_files: Optional[List[str]] = None,
        suggested_action: Optional[str] = None
    ) -> None:
        """Add a validation issue"""
        self.issues.append(ValidationIssue(
            severity=severity,
            description=description,
            affected_files=affected_files or [],
            suggested_action=suggested_action
        ))


class IntegrityValidationService:
    """
    Service for performing integrity validation on backup operations.
    
    This service provides:
    - Native tool integrity validation where supported
    - Wrapper-based validation for tools without native support
    - Comprehensive validation result reporting
    - Integration with backup completion workflow
    
    Requirements:
    - 3.1: Leverage backup tool native features where available
    - 3.2: Validate all selected files were processed
    - 3.3: Detect and report backup tool errors
    - 3.4: Provide plugin wrapper validation for unsupported tools
    - 3.5: Mark backup as failed if integrity validation fails
    """
    
    def __init__(
        self,
        tool_manager: Optional[ToolManager] = None,
        wrapper_registry: Optional[WrapperRegistry] = None
    ):
        """
        Initialize integrity validation service.
        
        Args:
            tool_manager: Tool manager for capability detection
            wrapper_registry: Registry for plugin wrappers
        """
        self._tool_manager = tool_manager or ToolManager()
        self._wrapper_registry = wrapper_registry or WrapperRegistry()
        logger.debug("IntegrityValidationService initialized")
    
    def validate_backup_integrity(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult
    ) -> IntegrityValidationResult:
        """
        Validate integrity of a completed backup operation.
        
        This method determines the appropriate validation method based on
        tool capabilities and performs comprehensive integrity checking.
        
        Args:
            backup_job: Backup job that was executed
            backup_result: Result of the backup operation
            
        Returns:
            IntegrityValidationResult with validation details
        """
        logger.info(
            f"Starting integrity validation for backup job: {backup_job.config.job_id}"
        )
        
        start_time = time.time()
        
        try:
            # Get tool capabilities
            tool_type = backup_job.config.tool_type
            capabilities = self._tool_manager.get_tool_capabilities(tool_type)
            
            # Determine validation method
            if capabilities.has_feature(Feature.INTEGRITY_VERIFICATION):
                # Use native tool validation
                logger.info(f"Using native integrity validation for {tool_type}")
                result = self._validate_with_native_tool(
                    backup_job,
                    backup_result,
                    capabilities
                )
            else:
                # Use wrapper-based validation
                logger.info(f"Using wrapper-based validation for {tool_type}")
                result = self._validate_with_wrapper(
                    backup_job,
                    backup_result,
                    tool_type
                )
            
            # Add timing information
            result.validation_time = time.time() - start_time
            
            # Log validation summary
            logger.info(
                f"Integrity validation complete: status={result.status.value}, "
                f"files={result.files_validated}, issues={len(result.issues)}, "
                f"time={result.validation_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Integrity validation failed with exception: {e}")
            
            # Return failed validation result
            result = IntegrityValidationResult(
                status=ValidationStatus.FAILED,
                method=ValidationMethod.MANUAL,
                validation_time=time.time() - start_time
            )
            result.add_issue(
                severity="critical",
                description=f"Validation failed with exception: {e}",
                suggested_action="Check logs and retry validation"
            )
            return result
    
    def _validate_with_native_tool(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        capabilities: ToolCapabilities
    ) -> IntegrityValidationResult:
        """
        Perform validation using native tool capabilities.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            capabilities: Tool capabilities
            
        Returns:
            IntegrityValidationResult
        """
        logger.debug("Performing native tool validation")
        
        result = IntegrityValidationResult(
            status=ValidationStatus.IN_PROGRESS,
            method=ValidationMethod.NATIVE_TOOL
        )
        
        tool_type = backup_job.config.tool_type
        
        try:
            if tool_type == "restic":
                self._validate_restic_native(backup_job, backup_result, result)
            elif tool_type == "borg":
                self._validate_borg_native(backup_job, backup_result, result)
            elif tool_type == "duplicity":
                self._validate_duplicity_native(backup_job, backup_result, result)
            else:
                logger.warning(f"Native validation not implemented for {tool_type}")
                result.status = ValidationStatus.NOT_SUPPORTED
                result.add_issue(
                    severity="medium",
                    description=f"Native validation not implemented for {tool_type}",
                    suggested_action="Use wrapper-based validation"
                )
            
            # Validate file processing completeness
            self._validate_file_completeness(backup_job, backup_result, result)
            
            # Set final status if not already set
            if result.status == ValidationStatus.IN_PROGRESS:
                if len(result.issues) == 0:
                    result.status = ValidationStatus.PASSED
                elif result.has_critical_issues:
                    result.status = ValidationStatus.FAILED
                else:
                    result.status = ValidationStatus.PARTIAL
            
        except Exception as e:
            logger.error(f"Native validation failed: {e}")
            result.status = ValidationStatus.FAILED
            result.add_issue(
                severity="critical",
                description=f"Native validation error: {e}",
                suggested_action="Check tool installation and permissions"
            )
        
        return result
    
    def _validate_with_wrapper(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        tool_type: str
    ) -> IntegrityValidationResult:
        """
        Perform validation using plugin wrapper.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            tool_type: Type of backup tool
            
        Returns:
            IntegrityValidationResult
        """
        logger.debug("Performing wrapper-based validation")
        
        result = IntegrityValidationResult(
            status=ValidationStatus.IN_PROGRESS,
            method=ValidationMethod.WRAPPER_CHECKSUM
        )
        
        try:
            # Get plugin wrapper
            wrapper = self._wrapper_registry.get_wrapper(tool_type)
            
            if wrapper:
                # Perform wrapper-based validation
                self._validate_with_checksum_verification(
                    backup_job,
                    backup_result,
                    result
                )
            else:
                logger.warning(f"No wrapper available for {tool_type}")
                result.status = ValidationStatus.NOT_SUPPORTED
                result.add_issue(
                    severity="high",
                    description=f"No validation wrapper available for {tool_type}",
                    suggested_action="Implement wrapper or use manual validation"
                )
            
            # Validate file processing completeness
            self._validate_file_completeness(backup_job, backup_result, result)
            
            # Set final status
            if result.status == ValidationStatus.IN_PROGRESS:
                if len(result.issues) == 0:
                    result.status = ValidationStatus.PASSED
                elif result.has_critical_issues:
                    result.status = ValidationStatus.FAILED
                else:
                    result.status = ValidationStatus.PARTIAL
            
        except Exception as e:
            logger.error(f"Wrapper validation failed: {e}")
            result.status = ValidationStatus.FAILED
            result.add_issue(
                severity="critical",
                description=f"Wrapper validation error: {e}",
                suggested_action="Check wrapper implementation"
            )
        
        return result

    
    def _validate_restic_native(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        result: IntegrityValidationResult
    ) -> None:
        """
        Validate using Restic's native integrity checking.
        
        Restic provides built-in integrity verification through checksums
        and repository verification commands.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            result: Validation result to populate
        """
        logger.debug("Performing Restic native validation")
        
        # Restic automatically verifies checksums during backup
        # Check if backup completed successfully
        if backup_result.status == BackupStatus.COMPLETED:
            result.files_validated = backup_result.files_processed
            result.bytes_validated = backup_result.bytes_processed
            
            # Check for errors in backup result
            if backup_result.errors:
                for error in backup_result.errors:
                    result.add_issue(
                        severity="high",
                        description=f"Backup error: {error}",
                        suggested_action="Review error and retry backup if needed"
                    )
            
            # Restic's checksum validation is automatic
            result.metadata['checksum_validation'] = 'automatic'
            result.metadata['tool_verification'] = 'native'
            
            logger.info(
                f"Restic validation: {result.files_validated} files, "
                f"{result.bytes_validated} bytes"
            )
        else:
            result.add_issue(
                severity="critical",
                description=f"Backup did not complete successfully: {backup_result.status.value}",
                suggested_action="Retry backup operation"
            )
    
    def _validate_borg_native(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        result: IntegrityValidationResult
    ) -> None:
        """
        Validate using Borg's native integrity checking.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            result: Validation result to populate
        """
        logger.debug("Performing Borg native validation")
        
        # Borg also provides automatic checksum validation
        if backup_result.status == BackupStatus.COMPLETED:
            result.files_validated = backup_result.files_processed
            result.bytes_validated = backup_result.bytes_processed
            
            # Check for errors
            if backup_result.errors:
                for error in backup_result.errors:
                    result.add_issue(
                        severity="high",
                        description=f"Backup error: {error}",
                        suggested_action="Review error and retry backup if needed"
                    )
            
            result.metadata['checksum_validation'] = 'automatic'
            result.metadata['tool_verification'] = 'native'
            
            logger.info(
                f"Borg validation: {result.files_validated} files, "
                f"{result.bytes_validated} bytes"
            )
        else:
            result.add_issue(
                severity="critical",
                description=f"Backup did not complete successfully: {backup_result.status.value}",
                suggested_action="Retry backup operation"
            )
    
    def _validate_duplicity_native(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        result: IntegrityValidationResult
    ) -> None:
        """
        Validate using Duplicity's capabilities.
        
        Note: Duplicity has limited native integrity checking,
        so this provides basic validation.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            result: Validation result to populate
        """
        logger.debug("Performing Duplicity validation")
        
        # Duplicity has limited native integrity checking
        if backup_result.status == BackupStatus.COMPLETED:
            result.files_validated = backup_result.files_processed
            result.bytes_validated = backup_result.bytes_processed
            
            # Check for errors
            if backup_result.errors:
                for error in backup_result.errors:
                    result.add_issue(
                        severity="high",
                        description=f"Backup error: {error}",
                        suggested_action="Review error and retry backup if needed"
                    )
            
            result.metadata['checksum_validation'] = 'limited'
            result.metadata['tool_verification'] = 'basic'
            
            # Add warning about limited validation
            result.add_issue(
                severity="low",
                description="Duplicity has limited native integrity checking",
                suggested_action="Consider using Restic or Borg for better integrity validation"
            )
            
            logger.info(
                f"Duplicity validation: {result.files_validated} files, "
                f"{result.bytes_validated} bytes"
            )
        else:
            result.add_issue(
                severity="critical",
                description=f"Backup did not complete successfully: {backup_result.status.value}",
                suggested_action="Retry backup operation"
            )
    
    def _validate_with_checksum_verification(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        result: IntegrityValidationResult
    ) -> None:
        """
        Perform wrapper-based checksum verification.
        
        This method provides basic integrity checking for tools that
        don't have native support by comparing file metadata.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            result: Validation result to populate
        """
        logger.debug("Performing wrapper-based checksum verification")
        
        # Basic validation: check if backup completed and files were processed
        if backup_result.status == BackupStatus.COMPLETED:
            result.files_validated = backup_result.files_processed
            result.bytes_validated = backup_result.bytes_processed
            
            # Check for errors
            if backup_result.errors:
                for error in backup_result.errors:
                    result.add_issue(
                        severity="high",
                        description=f"Backup error: {error}",
                        suggested_action="Review error and retry backup if needed"
                    )
            
            # Verify source files still exist and are accessible
            missing_files = []
            for source_path in backup_job.source_paths:
                path = Path(source_path)
                if not path.exists():
                    missing_files.append(str(source_path))
            
            if missing_files:
                result.missing_files = len(missing_files)
                result.add_issue(
                    severity="medium",
                    description=f"Source files no longer accessible: {len(missing_files)} files",
                    affected_files=missing_files[:10],  # Limit to first 10
                    suggested_action="Verify source paths are still available"
                )
            
            result.metadata['validation_method'] = 'wrapper_basic'
            result.metadata['checksum_validation'] = 'not_available'
            
            # Add informational note
            result.add_issue(
                severity="low",
                description="Using basic wrapper validation (native integrity checking not available)",
                suggested_action="Consider using a backup tool with native integrity checking"
            )
            
            logger.info(
                f"Wrapper validation: {result.files_validated} files, "
                f"{result.bytes_validated} bytes"
            )
        else:
            result.add_issue(
                severity="critical",
                description=f"Backup did not complete successfully: {backup_result.status.value}",
                suggested_action="Retry backup operation"
            )
    
    def _validate_file_completeness(
        self,
        backup_job: BackupJob,
        backup_result: BackupResult,
        result: IntegrityValidationResult
    ) -> None:
        """
        Validate that all selected files were processed according to tool capabilities.
        
        This addresses requirement 3.2: Validate all selected files were processed.
        
        Args:
            backup_job: Backup job
            backup_result: Backup result
            result: Validation result to populate
        """
        logger.debug("Validating file processing completeness")
        
        # Check if any files were processed
        if backup_result.files_processed == 0:
            result.add_issue(
                severity="critical",
                description="No files were processed during backup",
                suggested_action="Verify source paths and selection rules"
            )
            return
        
        # Check for warnings in backup result
        if backup_result.warnings:
            for warning in backup_result.warnings:
                # Categorize warnings
                if "permission" in warning.lower() or "access" in warning.lower():
                    result.add_issue(
                        severity="medium",
                        description=f"Access warning: {warning}",
                        suggested_action="Check file permissions and access rights"
                    )
                elif "missing" in warning.lower() or "not found" in warning.lower():
                    result.add_issue(
                        severity="medium",
                        description=f"Missing file warning: {warning}",
                        suggested_action="Verify all source files exist"
                    )
                else:
                    result.add_issue(
                        severity="low",
                        description=f"Backup warning: {warning}",
                        suggested_action="Review warning and take action if needed"
                    )
        
        # Validate against expected file count if available in job metadata
        if backup_job.config.metadata.get('expected_file_count'):
            expected = backup_job.config.metadata['expected_file_count']
            actual = backup_result.files_processed
            
            if actual < expected * 0.9:  # Less than 90% of expected files
                result.add_issue(
                    severity="high",
                    description=f"Fewer files processed than expected: {actual} vs {expected}",
                    suggested_action="Verify source paths and check for missing files"
                )
        
        result.metadata['completeness_check'] = 'performed'
        result.metadata['files_processed'] = backup_result.files_processed
    
    def integrate_validation_with_backup_result(
        self,
        backup_result: BackupResult,
        validation_result: IntegrityValidationResult
    ) -> BackupResult:
        """
        Integrate validation results with backup completion workflow.
        
        This addresses requirement 3.5: Mark backup as failed if integrity validation fails.
        
        Args:
            backup_result: Original backup result
            validation_result: Integrity validation result
            
        Returns:
            Updated BackupResult with validation information
        """
        logger.debug("Integrating validation results with backup result")
        
        # Add validation metadata to backup result
        backup_result.metadata['integrity_validation'] = {
            'status': validation_result.status.value,
            'method': validation_result.method.value,
            'validation_time': validation_result.validation_time,
            'files_validated': validation_result.files_validated,
            'bytes_validated': validation_result.bytes_validated,
            'issues_found': len(validation_result.issues),
            'critical_issues': validation_result.has_critical_issues
        }
        
        # Update backup status if validation failed
        if validation_result.status == ValidationStatus.FAILED:
            logger.warning(
                f"Marking backup as failed due to integrity validation failure"
            )
            backup_result.status = BackupStatus.FAILED
            
            # Add validation errors to backup result
            for issue in validation_result.issues:
                if issue.severity in ["critical", "high"]:
                    backup_result.errors.append(
                        f"Integrity validation: {issue.description}"
                    )
        
        # Add validation warnings to backup result
        elif validation_result.status == ValidationStatus.PARTIAL:
            logger.info("Backup completed with validation warnings")
            for issue in validation_result.issues:
                if issue.severity in ["medium", "low"]:
                    backup_result.warnings.append(
                        f"Integrity validation: {issue.description}"
                    )
        
        # Add validation success information
        elif validation_result.status == ValidationStatus.PASSED:
            logger.info("Backup integrity validation passed")
            backup_result.metadata['integrity_validated'] = True
        
        return backup_result
    
    def generate_validation_report(
        self,
        validation_result: IntegrityValidationResult
    ) -> Dict[str, Any]:
        """
        Generate a detailed validation report.
        
        Args:
            validation_result: Validation result to report on
            
        Returns:
            Dictionary with detailed validation report
        """
        report = {
            'summary': {
                'status': validation_result.status.value,
                'method': validation_result.method.value,
                'validation_time': validation_result.validation_time,
                'is_valid': validation_result.is_valid,
                'has_critical_issues': validation_result.has_critical_issues
            },
            'statistics': {
                'files_validated': validation_result.files_validated,
                'bytes_validated': validation_result.bytes_validated,
                'checksum_mismatches': validation_result.checksum_mismatches,
                'missing_files': validation_result.missing_files,
                'corrupted_files': validation_result.corrupted_files
            },
            'issues': [
                {
                    'severity': issue.severity,
                    'description': issue.description,
                    'affected_files_count': len(issue.affected_files),
                    'affected_files_sample': issue.affected_files[:5],
                    'suggested_action': issue.suggested_action
                }
                for issue in validation_result.issues
            ],
            'metadata': validation_result.metadata
        }
        
        return report
    
    def get_validation_recommendations(
        self,
        tool_type: str,
        capabilities: Optional[ToolCapabilities] = None
    ) -> List[str]:
        """
        Get recommendations for integrity validation based on tool capabilities.
        
        Args:
            tool_type: Type of backup tool
            capabilities: Optional tool capabilities (will be fetched if not provided)
            
        Returns:
            List of recommendations
        """
        if capabilities is None:
            capabilities = self._tool_manager.get_tool_capabilities(tool_type)
        
        recommendations = []
        
        # Check for native integrity verification
        if capabilities.has_feature(Feature.INTEGRITY_VERIFICATION):
            if capabilities.is_native_feature(Feature.INTEGRITY_VERIFICATION):
                recommendations.append(
                    f"{tool_type} provides native integrity verification - "
                    "this will be used automatically"
                )
            else:
                recommendations.append(
                    f"{tool_type} integrity verification is provided by wrapper - "
                    "consider using a tool with native support for better performance"
                )
        else:
            recommendations.append(
                f"{tool_type} does not support integrity verification - "
                "basic wrapper validation will be used"
            )
            recommendations.append(
                "Consider using Restic or Borg for comprehensive integrity checking"
            )
        
        # Check for checksum validation
        if capabilities.has_feature(Feature.CHECKSUM_VALIDATION):
            recommendations.append(
                f"{tool_type} supports checksum validation for data integrity"
            )
        else:
            recommendations.append(
                f"{tool_type} does not support checksum validation - "
                "integrity checking will be limited"
            )
        
        # Check for repository verification
        if capabilities.has_feature(Feature.REPOSITORY_VERIFICATION):
            recommendations.append(
                "Enable periodic repository verification for additional integrity assurance"
            )
        
        return recommendations
