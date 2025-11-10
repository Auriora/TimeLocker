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
import time
from typing import Dict, Any, Optional, Callable, Type, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .recovery_errors import (
    RecoveryError,
    RestoreError,
    RestoreTargetError,
    RestorePermissionError,
    RestoreVerificationError,
    RestoreInterruptedError,
    FileConflictError,
    SnapshotCorruptedError,
    InsufficientSpaceError,
    ValidationError,
    SnapshotNotFoundError
)

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of recovery errors for classification"""
    TRANSIENT = "transient"  # Temporary errors that may resolve with retry
    PERMANENT = "permanent"  # Errors that won't resolve with retry
    CONFIGURATION = "configuration"  # Configuration or setup errors
    RESOURCE = "resource"  # Resource availability errors
    NETWORK = "network"  # Network-related errors
    FILESYSTEM = "filesystem"  # File system errors
    CORRUPTION = "corruption"  # Data corruption errors


class ErrorSeverity(Enum):
    """Severity levels for recovery errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Actions to take in response to recovery errors"""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SKIP_FILE = "skip_file"
    CONTINUE = "continue"
    ABORT = "abort"
    ESCALATE = "escalate"
    ALTERNATIVE_PATH = "alternative_path"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 30.0
    retry_on_categories: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.TRANSIENT,
        ErrorCategory.NETWORK
    ])


@dataclass
class RecoveryContext:
    """Context information for recovery operations"""
    operation_id: str
    snapshot_id: str
    target_path: str
    current_file: Optional[str] = None
    files_processed: int = 0
    total_files: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorHandlingResult:
    """Result of error handling decision"""
    action: RecoveryAction
    should_retry: bool
    retry_delay: float = 0.0
    alternative_path: Optional[str] = None
    error_message: str = ""
    context_updates: Dict[str, Any] = field(default_factory=dict)


class RecoveryErrorHandler:
    """
    Centralized error handling for recovery operations with configurable
    retry policies and intelligent error classification.
    
    This handler provides:
    - Automatic error classification and categorization
    - Configurable retry policies with exponential backoff
    - Transient error detection and handling
    - Error escalation for non-recoverable errors
    - Context-aware error handling decisions
    """
    
    def __init__(self, retry_policy: Optional[RetryPolicy] = None):
        """
        Initialize the RecoveryErrorHandler.
        
        Args:
            retry_policy: Optional custom retry policy configuration
        """
        self.retry_policy = retry_policy or RetryPolicy()
        
        # Error classification mappings
        self._error_categories: Dict[Type[Exception], ErrorCategory] = {
            RestoreInterruptedError: ErrorCategory.TRANSIENT,
            InsufficientSpaceError: ErrorCategory.RESOURCE,
            RestorePermissionError: ErrorCategory.FILESYSTEM,
            RestoreTargetError: ErrorCategory.CONFIGURATION,
            FileConflictError: ErrorCategory.FILESYSTEM,
            SnapshotCorruptedError: ErrorCategory.CORRUPTION,
            SnapshotNotFoundError: ErrorCategory.PERMANENT,
            ValidationError: ErrorCategory.CORRUPTION,
        }
        
        # Error severity mappings
        self._error_severities: Dict[Type[Exception], ErrorSeverity] = {
            SnapshotCorruptedError: ErrorSeverity.CRITICAL,
            InsufficientSpaceError: ErrorSeverity.HIGH,
            RestorePermissionError: ErrorSeverity.HIGH,
            RestoreVerificationError: ErrorSeverity.HIGH,
            RestoreInterruptedError: ErrorSeverity.MEDIUM,
            FileConflictError: ErrorSeverity.LOW,
            ValidationError: ErrorSeverity.MEDIUM,
        }
        
        # Error handling strategies
        self._error_strategies: Dict[Type[Exception], Callable] = {
            RestoreInterruptedError: self._handle_interrupted_error,
            InsufficientSpaceError: self._handle_space_error,
            RestorePermissionError: self._handle_permission_error,
            FileConflictError: self._handle_conflict_error,
            SnapshotCorruptedError: self._handle_corruption_error,
            RestoreTargetError: self._handle_target_error,
        }
        
        # Error history for pattern detection
        self._error_history: List[Dict[str, Any]] = []
        
        # Custom error callbacks
        self._error_callbacks: List[Callable[[Exception, RecoveryContext], None]] = []
        
        logger.info("RecoveryErrorHandler initialized with retry policy: "
                   f"max_retries={self.retry_policy.max_retries}, "
                   f"initial_delay={self.retry_policy.initial_delay}s")
    
    def handle_recovery_error(
        self,
        error: Exception,
        context: RecoveryContext
    ) -> ErrorHandlingResult:
        """
        Handle a recovery error and determine the appropriate action.
        
        This method analyzes the error, classifies it, and determines the
        best course of action based on error type, context, and retry policy.
        
        Args:
            error: The exception that occurred
            context: Current recovery operation context
            
        Returns:
            ErrorHandlingResult with recommended action and details
        """
        try:
            # Classify the error
            category = self._classify_error(error)
            severity = self._determine_severity(error)
            
            # Log the error with context
            self._log_error(error, context, category, severity)
            
            # Record in error history
            self._record_error(error, context, category, severity)
            
            # Notify callbacks
            self._notify_callbacks(error, context)
            
            # Determine if retry is appropriate
            should_retry = self.should_retry(error, context.retry_count)
            
            # Get error-specific handling strategy
            result = self._get_error_strategy(error, context, should_retry)
            
            # Apply retry policy if needed
            if result.should_retry:
                result.retry_delay = self._calculate_retry_delay(context.retry_count)
            
            logger.info(f"Error handling decision for {type(error).__name__}: "
                       f"action={result.action.value}, should_retry={result.should_retry}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}", exc_info=True)
            # Fail safe - abort on handler errors
            return ErrorHandlingResult(
                action=RecoveryAction.ABORT,
                should_retry=False,
                error_message=f"Error handler failure: {e}"
            )
    
    def should_retry(self, error: Exception, attempt_count: int) -> bool:
        """
        Determine if an operation should be retried based on error type and attempt count.
        
        Args:
            error: The exception that occurred
            attempt_count: Number of previous retry attempts
            
        Returns:
            True if the operation should be retried, False otherwise
        """
        # Check if max retries exceeded
        if attempt_count >= self.retry_policy.max_retries:
            logger.debug(f"Max retries ({self.retry_policy.max_retries}) exceeded")
            return False
        
        # Classify error
        category = self._classify_error(error)
        
        # Check if error category is retryable
        if category not in self.retry_policy.retry_on_categories:
            logger.debug(f"Error category {category.value} is not retryable")
            return False
        
        # Check for specific non-retryable errors
        non_retryable_types = (
            SnapshotNotFoundError,
            SnapshotCorruptedError,
            RestoreTargetError,
        )
        
        if isinstance(error, non_retryable_types):
            logger.debug(f"Error type {type(error).__name__} is not retryable")
            return False
        
        # Check error message for non-retryable indicators
        error_msg = str(error).lower()
        non_retryable_keywords = [
            "not found",
            "does not exist",
            "corrupted",
            "invalid",
            "permission denied",
        ]
        
        for keyword in non_retryable_keywords:
            if keyword in error_msg:
                logger.debug(f"Error message contains non-retryable keyword: {keyword}")
                return False
        
        logger.debug(f"Error is retryable (attempt {attempt_count + 1}/{self.retry_policy.max_retries})")
        return True
    
    def escalate_error(
        self,
        error: Exception,
        context: RecoveryContext,
        reason: str = ""
    ) -> None:
        """
        Escalate an error that cannot be automatically resolved.
        
        This method logs the error with full context and notifies any
        registered escalation handlers.
        
        Args:
            error: The exception to escalate
            context: Recovery operation context
            reason: Optional reason for escalation
        """
        severity = self._determine_severity(error)
        category = self._classify_error(error)
        
        escalation_msg = (
            f"ESCALATED ERROR in recovery operation {context.operation_id}: "
            f"{type(error).__name__}: {error}"
        )
        
        if reason:
            escalation_msg += f" | Reason: {reason}"
        
        escalation_msg += (
            f" | Category: {category.value}, Severity: {severity.value}"
            f" | Snapshot: {context.snapshot_id}, Target: {context.target_path}"
        )
        
        if context.current_file:
            escalation_msg += f" | Current file: {context.current_file}"
        
        # Log based on severity
        if severity in (ErrorSeverity.CRITICAL, ErrorSeverity.HIGH):
            logger.error(escalation_msg, exc_info=True)
        else:
            logger.warning(escalation_msg)
        
        # Record escalation in error history
        self._record_error(error, context, category, severity, escalated=True)
        
        # Notify callbacks
        self._notify_callbacks(error, context)
    
    def register_error_callback(
        self,
        callback: Callable[[Exception, RecoveryContext], None]
    ) -> None:
        """
        Register a callback to be notified of recovery errors.
        
        Args:
            callback: Function to call when errors occur
        """
        self._error_callbacks.append(callback)
        logger.debug(f"Registered error callback: {callback.__name__}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recovery errors.
        
        Returns:
            Dictionary containing error statistics
        """
        if not self._error_history:
            return {
                'total_errors': 0,
                'errors_by_category': {},
                'errors_by_severity': {},
                'escalated_errors': 0,
                'retry_success_rate': 0.0
            }
        
        # Count errors by category and severity
        category_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        escalated_count = 0
        
        for error_record in self._error_history:
            category = error_record.get('category', 'unknown')
            severity = error_record.get('severity', 'unknown')
            
            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if error_record.get('escalated', False):
                escalated_count += 1
        
        return {
            'total_errors': len(self._error_history),
            'errors_by_category': category_counts,
            'errors_by_severity': severity_counts,
            'escalated_errors': escalated_count,
            'recent_errors': self._error_history[-10:] if len(self._error_history) > 10 else self._error_history
        }
    
    # Private helper methods
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an error into a category"""
        error_type = type(error)
        
        # Check exact type match
        if error_type in self._error_categories:
            return self._error_categories[error_type]
        
        # Check parent classes
        for registered_type, category in self._error_categories.items():
            if isinstance(error, registered_type):
                return self._error_categories[registered_type]
        
        # Check error message for hints
        error_msg = str(error).lower()
        
        if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout']):
            return ErrorCategory.NETWORK
        elif any(keyword in error_msg for keyword in ['permission', 'access denied']):
            return ErrorCategory.FILESYSTEM
        elif any(keyword in error_msg for keyword in ['space', 'disk full']):
            return ErrorCategory.RESOURCE
        elif any(keyword in error_msg for keyword in ['corrupt', 'invalid', 'checksum']):
            return ErrorCategory.CORRUPTION
        
        # Default to transient for unknown errors
        return ErrorCategory.TRANSIENT
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine the severity of an error"""
        error_type = type(error)
        
        # Check exact type match
        if error_type in self._error_severities:
            return self._error_severities[error_type]
        
        # Check parent classes
        for registered_type, severity in self._error_severities.items():
            if isinstance(error, registered_type):
                return self._error_severities[registered_type]
        
        # Default severity based on error category
        category = self._classify_error(error)
        
        if category == ErrorCategory.CORRUPTION:
            return ErrorSeverity.CRITICAL
        elif category in (ErrorCategory.RESOURCE, ErrorCategory.PERMANENT):
            return ErrorSeverity.HIGH
        elif category in (ErrorCategory.NETWORK, ErrorCategory.FILESYSTEM):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _get_error_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Get the appropriate error handling strategy"""
        error_type = type(error)
        
        # Find specific strategy
        for registered_type, strategy in self._error_strategies.items():
            if isinstance(error, registered_type):
                return strategy(error, context, should_retry)
        
        # Default strategy
        return self._handle_generic_error(error, context, should_retry)
    
    def _handle_interrupted_error(
        self,
        error: RestoreInterruptedError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle interrupted restore operations"""
        if should_retry:
            return ErrorHandlingResult(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                should_retry=True,
                error_message="Restore interrupted, will retry with backoff"
            )
        else:
            return ErrorHandlingResult(
                action=RecoveryAction.ABORT,
                should_retry=False,
                error_message="Restore interrupted and max retries exceeded"
            )
    
    def _handle_space_error(
        self,
        error: InsufficientSpaceError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle insufficient space errors"""
        return ErrorHandlingResult(
            action=RecoveryAction.ESCALATE,
            should_retry=False,
            error_message="Insufficient disk space - manual intervention required"
        )
    
    def _handle_permission_error(
        self,
        error: RestorePermissionError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle permission errors"""
        if context.current_file:
            # Try to continue with other files
            return ErrorHandlingResult(
                action=RecoveryAction.SKIP_FILE,
                should_retry=False,
                error_message=f"Permission denied for {context.current_file}, skipping"
            )
        else:
            return ErrorHandlingResult(
                action=RecoveryAction.ESCALATE,
                should_retry=False,
                error_message="Permission error - manual intervention required"
            )
    
    def _handle_conflict_error(
        self,
        error: FileConflictError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle file conflict errors"""
        return ErrorHandlingResult(
            action=RecoveryAction.SKIP_FILE,
            should_retry=False,
            error_message="File conflict detected, skipping file"
        )
    
    def _handle_corruption_error(
        self,
        error: SnapshotCorruptedError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle snapshot corruption errors"""
        return ErrorHandlingResult(
            action=RecoveryAction.ABORT,
            should_retry=False,
            error_message="Snapshot corrupted - cannot continue recovery"
        )
    
    def _handle_target_error(
        self,
        error: RestoreTargetError,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle target path errors"""
        return ErrorHandlingResult(
            action=RecoveryAction.ESCALATE,
            should_retry=False,
            error_message="Invalid target path - manual intervention required"
        )
    
    def _handle_generic_error(
        self,
        error: Exception,
        context: RecoveryContext,
        should_retry: bool
    ) -> ErrorHandlingResult:
        """Handle generic errors"""
        if should_retry:
            return ErrorHandlingResult(
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                should_retry=True,
                error_message=f"Generic error, will retry: {error}"
            )
        else:
            return ErrorHandlingResult(
                action=RecoveryAction.ABORT,
                should_retry=False,
                error_message=f"Generic error and max retries exceeded: {error}"
            )
    
    def _calculate_retry_delay(self, attempt_count: int) -> float:
        """Calculate retry delay with exponential backoff"""
        delay = self.retry_policy.initial_delay * (
            self.retry_policy.backoff_multiplier ** attempt_count
        )
        return min(delay, self.retry_policy.max_delay)
    
    def _log_error(
        self,
        error: Exception,
        context: RecoveryContext,
        category: ErrorCategory,
        severity: ErrorSeverity
    ) -> None:
        """Log error with context information"""
        log_msg = (
            f"Recovery error in operation {context.operation_id}: "
            f"{type(error).__name__}: {error} | "
            f"Category: {category.value}, Severity: {severity.value}"
        )
        
        if context.current_file:
            log_msg += f" | File: {context.current_file}"
        
        log_msg += f" | Progress: {context.files_processed}/{context.total_files}"
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.error(log_msg, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_msg)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def _record_error(
        self,
        error: Exception,
        context: RecoveryContext,
        category: ErrorCategory,
        severity: ErrorSeverity,
        escalated: bool = False
    ) -> None:
        """Record error in history for pattern detection"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'category': category.value,
            'severity': severity.value,
            'operation_id': context.operation_id,
            'snapshot_id': context.snapshot_id,
            'current_file': context.current_file,
            'retry_count': context.retry_count,
            'escalated': escalated
        }
        
        self._error_history.append(error_record)
        
        # Keep only recent errors (last 1000)
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-500:]
    
    def _notify_callbacks(self, error: Exception, context: RecoveryContext) -> None:
        """Notify registered error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error, context)
            except Exception as e:
                logger.warning(f"Error callback {callback.__name__} failed: {e}")
