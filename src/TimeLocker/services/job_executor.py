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
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field

from ..interfaces.data_models import (
    BackupJob,
    BackupResult,
    BackupStatus,
    RetryConfig
)
from ..interfaces.backup_orchestrator import BackupExecutionError
from ..utils.error_handling import ErrorContext

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Classification of error types for retry strategy determination"""
    TRANSIENT = "transient"  # Network timeouts, temporary locks, resource unavailability
    CONFIGURATION = "configuration"  # Invalid paths, missing credentials, tool misconfiguration
    TOOL_SPECIFIC = "tool_specific"  # Backup tool crashes, corrupted repositories
    RESOURCE = "resource"  # Insufficient disk space, memory limitations, permission issues
    PERMANENT = "permanent"  # Unrecoverable errors that should not be retried


class RetryStrategy(Enum):
    """Retry strategy for different error categories"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


@dataclass
class ErrorClassification:
    """
    Classification result for an error.
    
    Attributes:
        category: The error category
        strategy: Recommended retry strategy
        should_retry: Whether the error should be retried
        reason: Human-readable reason for the classification
        suggested_action: Suggested remediation action
    """
    category: ErrorCategory
    strategy: RetryStrategy
    should_retry: bool
    reason: str
    suggested_action: Optional[str] = None


@dataclass
class RetryDecision:
    """
    Decision about whether and how to retry an operation.
    
    Attributes:
        should_retry: Whether to retry the operation
        delay_seconds: How long to wait before retrying
        reason: Reason for the decision
        max_attempts_reached: Whether maximum retry attempts have been reached
        error_classification: Classification of the error that triggered this decision
    """
    should_retry: bool
    delay_seconds: float
    reason: str
    max_attempts_reached: bool = False
    error_classification: Optional[ErrorClassification] = None


@dataclass
class ExecutionResult:
    """
    Result of job execution with retry information.
    
    Attributes:
        backup_result: The backup operation result
        total_attempts: Total number of execution attempts
        retry_history: History of retry attempts with errors
        final_error_classification: Classification of the final error if failed
    """
    backup_result: BackupResult
    total_attempts: int
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
    final_error_classification: Optional[ErrorClassification] = None


class ErrorClassifier:
    """
    Classifies errors to determine appropriate retry strategies.
    
    This class analyzes exceptions and error messages to categorize them
    and recommend appropriate retry strategies.
    """
    
    def __init__(self):
        """Initialize error classifier with pattern mappings"""
        # Patterns for transient errors
        self._transient_patterns = [
            "timeout", "timed out", "connection refused", "connection reset",
            "temporary failure", "temporarily unavailable", "try again",
            "network error", "connection error", "socket error",
            "locked", "lock", "busy", "in use"
        ]
        
        # Patterns for configuration errors
        self._configuration_patterns = [
            "not found", "does not exist", "invalid path", "permission denied",
            "access denied", "authentication failed", "invalid credentials",
            "configuration error", "invalid configuration", "missing required"
        ]
        
        # Patterns for resource errors
        self._resource_patterns = [
            "no space left", "disk full", "out of memory", "insufficient",
            "quota exceeded", "limit exceeded", "too many", "resource exhausted"
        ]
        
        # Patterns for tool-specific errors
        self._tool_patterns = [
            "repository", "snapshot", "backup tool", "restic", "borg",
            "corrupted", "integrity", "checksum", "verification failed"
        ]
    
    def classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorClassification:
        """
        Classify an error to determine retry strategy.
        
        Args:
            error: The exception to classify
            context: Optional context information about the error
            
        Returns:
            ErrorClassification with category and retry strategy
        """
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        logger.debug(f"Classifying error: {error_type}: {error_message}")
        
        # Check for transient errors
        if self._matches_patterns(error_message, self._transient_patterns):
            return ErrorClassification(
                category=ErrorCategory.TRANSIENT,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                should_retry=True,
                reason="Transient error detected - likely temporary network or resource issue",
                suggested_action="Retry with exponential backoff"
            )
        
        # Check for configuration errors
        if self._matches_patterns(error_message, self._configuration_patterns):
            return ErrorClassification(
                category=ErrorCategory.CONFIGURATION,
                strategy=RetryStrategy.NO_RETRY,
                should_retry=False,
                reason="Configuration error detected - requires manual intervention",
                suggested_action="Check configuration, paths, and credentials"
            )
        
        # Check for resource errors
        if self._matches_patterns(error_message, self._resource_patterns):
            return ErrorClassification(
                category=ErrorCategory.RESOURCE,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                should_retry=True,
                reason="Resource constraint detected - may resolve with time",
                suggested_action="Free up resources or retry with longer delays"
            )
        
        # Check for tool-specific errors
        if self._matches_patterns(error_message, self._tool_patterns):
            return ErrorClassification(
                category=ErrorCategory.TOOL_SPECIFIC,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                should_retry=True,
                reason="Backup tool error detected - may be recoverable",
                suggested_action="Verify repository integrity and retry"
            )
        
        # Default to permanent error if no pattern matches
        return ErrorClassification(
            category=ErrorCategory.PERMANENT,
            strategy=RetryStrategy.NO_RETRY,
            should_retry=False,
            reason="Unclassified error - treating as permanent to avoid infinite retries",
            suggested_action="Review error details and logs for root cause"
        )
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given patterns"""
        return any(pattern in text for pattern in patterns)


class JobExecutor:
    """
    Executes backup jobs with advanced retry logic and error handling.
    
    This class provides sophisticated retry mechanisms with error classification,
    exponential backoff, and integration with existing error handling utilities.
    """
    
    def __init__(self, error_classifier: Optional[ErrorClassifier] = None):
        """
        Initialize job executor.
        
        Args:
            error_classifier: Optional custom error classifier
        """
        self._error_classifier = error_classifier or ErrorClassifier()
        logger.debug("JobExecutor initialized")
    
    def execute_with_retry(
        self,
        job: BackupJob,
        execution_func: Callable[[BackupJob], BackupResult],
        retry_config: Optional[RetryConfig] = None
    ) -> ExecutionResult:
        """
        Execute a backup job with configurable retry logic.
        
        This method implements sophisticated retry logic with error classification,
        exponential backoff, and comprehensive error tracking.
        
        Args:
            job: The backup job to execute
            execution_func: Function that performs the actual backup execution
            retry_config: Optional retry configuration (uses job config if not provided)
            
        Returns:
            ExecutionResult with backup result and retry information
            
        Raises:
            BackupExecutionError: If backup fails after all retry attempts
        """
        # Use provided retry config or get from job
        config = retry_config or job.config.retry_config
        max_attempts = config.max_retries + 1
        
        retry_history = []
        last_error = None
        last_classification = None
        
        logger.info(
            f"Starting job execution with retry: {job.config.job_id}, "
            f"max_attempts={max_attempts}"
        )
        
        for attempt in range(1, max_attempts + 1):
            # Update execution context
            job.execution_context.attempt_number = attempt
            
            try:
                # Calculate and apply delay for retry attempts
                if attempt > 1:
                    delay = self._calculate_retry_delay(
                        attempt=attempt,
                        config=config,
                        last_classification=last_classification
                    )
                    
                    logger.info(
                        f"Retry attempt {attempt}/{max_attempts} after {delay:.2f}s delay "
                        f"for job {job.config.job_id}"
                    )
                    time.sleep(delay)
                
                # Execute the backup job
                logger.debug(f"Executing attempt {attempt} for job {job.config.job_id}")
                backup_result = execution_func(job)
                
                # Check if execution was successful
                if backup_result.status == BackupStatus.COMPLETED:
                    logger.info(
                        f"Job {job.config.job_id} completed successfully on attempt {attempt}"
                    )
                    
                    return ExecutionResult(
                        backup_result=backup_result,
                        total_attempts=attempt,
                        retry_history=retry_history
                    )
                
                # Execution completed but with failure status
                error_msg = "; ".join(backup_result.errors) if backup_result.errors else "Unknown error"
                last_error = BackupExecutionError(error_msg)
                
                # Classify the error
                last_classification = self._error_classifier.classify_error(
                    last_error,
                    context={
                        'job_id': job.config.job_id,
                        'attempt': attempt,
                        'backup_result': backup_result
                    }
                )
                
                # Record retry attempt
                retry_history.append({
                    'attempt': attempt,
                    'error': error_msg,
                    'classification': last_classification,
                    'timestamp': time.time()
                })
                
                # Determine if we should retry
                retry_decision = self.handle_execution_error(
                    last_error,
                    attempt,
                    max_attempts,
                    last_classification
                )
                
                if not retry_decision.should_retry:
                    logger.warning(
                        f"Not retrying job {job.config.job_id}: {retry_decision.reason}"
                    )
                    break
                
                logger.warning(
                    f"Job {job.config.job_id} failed on attempt {attempt}: {error_msg}. "
                    f"Will retry. Classification: {last_classification.category.value}"
                )
                
                # Add error to execution context
                job.execution_context.previous_errors.append(error_msg)
                
            except Exception as e:
                # Unexpected exception during execution
                logger.error(f"Exception during job execution attempt {attempt}: {e}")
                last_error = e
                
                # Classify the exception
                last_classification = self._error_classifier.classify_error(
                    e,
                    context={
                        'job_id': job.config.job_id,
                        'attempt': attempt
                    }
                )
                
                # Record retry attempt
                retry_history.append({
                    'attempt': attempt,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'classification': last_classification,
                    'timestamp': time.time()
                })
                
                # Determine if we should retry
                retry_decision = self.handle_execution_error(
                    e,
                    attempt,
                    max_attempts,
                    last_classification
                )
                
                if not retry_decision.should_retry:
                    logger.error(
                        f"Not retrying job {job.config.job_id} after exception: "
                        f"{retry_decision.reason}"
                    )
                    break
                
                # Add error to execution context
                job.execution_context.previous_errors.append(str(e))
        
        # All retry attempts exhausted
        logger.error(
            f"Job {job.config.job_id} failed after {max_attempts} attempts. "
            f"Final error: {last_error}"
        )
        
        # Create final backup result
        final_result = BackupResult(
            status=BackupStatus.FAILED,
            repository_name=job.config.repository_id,
            target_names=job.config.target_names,
            start_time=job.execution_context.start_time,
            end_time=time.time(),
            errors=[
                f"Failed after {max_attempts} attempts",
                f"Final error: {last_error}"
            ],
            metadata={
                'job_id': job.config.job_id,
                'total_attempts': max_attempts,
                'final_classification': last_classification.category.value if last_classification else None
            }
        )
        
        return ExecutionResult(
            backup_result=final_result,
            total_attempts=max_attempts,
            retry_history=retry_history,
            final_error_classification=last_classification
        )
    
    def handle_execution_error(
        self,
        error: Exception,
        attempt: int,
        max_attempts: int,
        classification: Optional[ErrorClassification] = None
    ) -> RetryDecision:
        """
        Determine retry strategy based on error type and attempt count.
        
        This method analyzes the error and current attempt to decide whether
        to retry and how long to wait.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum number of attempts allowed
            classification: Optional pre-computed error classification
            
        Returns:
            RetryDecision with retry recommendation
        """
        # Check if max attempts reached
        if attempt >= max_attempts:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0,
                reason=f"Maximum retry attempts ({max_attempts}) reached",
                max_attempts_reached=True,
                error_classification=classification
            )
        
        # Classify error if not already classified
        if classification is None:
            classification = self._error_classifier.classify_error(error)
        
        # Determine retry based on classification
        if not classification.should_retry:
            return RetryDecision(
                should_retry=False,
                delay_seconds=0,
                reason=f"Error category {classification.category.value} should not be retried: {classification.reason}",
                error_classification=classification
            )
        
        # Calculate delay based on strategy
        delay = 0.0
        if classification.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = 2.0 ** (attempt - 1)  # 1, 2, 4, 8, 16...
        elif classification.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = attempt * 2.0  # 2, 4, 6, 8...
        elif classification.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        
        # Cap delay at reasonable maximum
        delay = min(delay, 60.0)
        
        return RetryDecision(
            should_retry=True,
            delay_seconds=delay,
            reason=f"Retrying {classification.category.value} error with {classification.strategy.value}",
            error_classification=classification
        )
    
    def _calculate_retry_delay(
        self,
        attempt: int,
        config: RetryConfig,
        last_classification: Optional[ErrorClassification]
    ) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (1-indexed)
            config: Retry configuration
            last_classification: Classification of the last error
            
        Returns:
            Delay in seconds
        """
        # Use classification strategy if available
        if last_classification:
            if last_classification.strategy == RetryStrategy.IMMEDIATE:
                return 0.0
            elif last_classification.strategy == RetryStrategy.LINEAR_BACKOFF:
                delay = config.base_delay_seconds * attempt
                return min(delay, config.max_delay_seconds)
        
        # Default to exponential backoff
        delay = config.base_delay_seconds * (config.backoff_multiplier ** (attempt - 2))
        return min(delay, config.max_delay_seconds)
