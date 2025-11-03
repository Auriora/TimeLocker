"""
Configuration error handler for TimeLocker.

This module provides comprehensive error handling and recovery strategies
for configuration operations, following the Single Responsibility Principle
by focusing solely on error handling and recovery.
"""

import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..interfaces.exceptions import (
    ConfigurationError,
    ConfigurationStoreError,
    ConfigurationLockError,
    ConfigurationBackupError,
    ConfigurationWatchError,
    ConfigurationValidationError,
    ConfigurationMigrationError,
    ConfigurationCorruptionError
)

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Recovery actions for configuration errors"""
    RETRY = "retry"
    RESTORE_BACKUP = "restore_backup"
    RESET_TO_DEFAULTS = "reset_to_defaults"
    MANUAL_INTERVENTION = "manual_intervention"
    IGNORE = "ignore"
    FAIL = "fail"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for configuration errors"""
    error_type: str
    error_message: str
    operation: str
    timestamp: datetime
    severity: ErrorSeverity
    recovery_action: RecoveryAction
    retry_count: int = 0
    max_retries: int = 3
    backoff_seconds: float = 1.0
    context_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}


class ConfigurationErrorHandler:
    """
    Configuration error handler with recovery strategies.
    
    Provides comprehensive error handling, retry mechanisms, and automatic
    recovery strategies for configuration operations.
    """

    def __init__(self, backup_manager=None, lock_manager=None, performance_monitor=None):
        """
        Initialize the error handler.
        
        Args:
            backup_manager: Configuration backup manager for recovery
            lock_manager: Configuration lock manager for cleanup
            performance_monitor: Performance monitor for error tracking
        """
        self.backup_manager = backup_manager
        self.lock_manager = lock_manager
        self.performance_monitor = performance_monitor
        
        # Error tracking
        self._error_history: List[ErrorContext] = []
        self._error_callbacks: List[Callable[[ErrorContext], None]] = []
        
        # Retry configuration
        self.default_max_retries = 3
        self.default_backoff_base = 1.0
        self.max_backoff = 30.0
        
        # Recovery strategies
        self._recovery_strategies: Dict[Type[Exception], Callable[[Exception, ErrorContext], RecoveryAction]] = {
            ConfigurationStoreError: self._handle_store_error,
            ConfigurationLockError: self._handle_lock_error,
            ConfigurationBackupError: self._handle_backup_error,
            ConfigurationWatchError: self._handle_watch_error,
            ConfigurationValidationError: self._handle_validation_error,
            ConfigurationMigrationError: self._handle_migration_error,
            ConfigurationCorruptionError: self._handle_corruption_error,
            ConfigurationError: self._handle_generic_error
        }

    def handle_error(self, error: Exception, operation: str, context_data: Optional[Dict[str, Any]] = None) -> RecoveryAction:
        """
        Handle a configuration error and determine recovery action.
        
        Args:
            error: The exception that occurred
            operation: The operation that failed
            context_data: Additional context information
            
        Returns:
            Recommended recovery action
        """
        try:
            # Determine error severity
            severity = self._determine_severity(error)
            
            # Create error context
            error_context = ErrorContext(
                error_type=type(error).__name__,
                error_message=str(error),
                operation=operation,
                timestamp=datetime.now(),
                severity=severity,
                recovery_action=RecoveryAction.FAIL,  # Default, will be updated
                context_data=context_data or {}
            )
            
            # Find appropriate recovery strategy
            recovery_action = self._get_recovery_strategy(error, error_context)
            error_context.recovery_action = recovery_action
            
            # Add to error history
            self._error_history.append(error_context)
            self._cleanup_error_history()
            
            # Track error in performance monitor
            if self.performance_monitor:
                self.performance_monitor.track_operation(f"error_{operation}", 0.0, False)
            
            # Notify error callbacks
            self._notify_error_callbacks(error_context)
            
            logger.error(f"Configuration error in {operation}: {error} (Recovery: {recovery_action.value})")
            
            return recovery_action
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return RecoveryAction.FAIL

    def retry_with_backoff(self, operation: Callable, operation_name: str, 
                          max_retries: Optional[int] = None, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute an operation with exponential backoff retry.
        
        Args:
            operation: Function to execute
            operation_name: Name of the operation for logging
            max_retries: Maximum number of retries
            context_data: Additional context information
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If all retries are exhausted
        """
        max_retries = max_retries or self.default_max_retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    # Final attempt failed
                    recovery_action = self.handle_error(e, operation_name, context_data)
                    if recovery_action == RecoveryAction.RETRY:
                        # Override max retries for critical operations
                        logger.warning(f"Extending retries for critical operation: {operation_name}")
                        max_retries += 2
                        continue
                    else:
                        raise e
                
                # Calculate backoff delay
                backoff_delay = min(
                    self.default_backoff_base * (2 ** attempt),
                    self.max_backoff
                )
                
                logger.warning(f"Operation {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                             f"retrying in {backoff_delay:.1f}s: {e}")
                
                time.sleep(backoff_delay)
        
        # This should not be reached, but just in case
        raise last_exception or ConfigurationError("Retry operation failed")

    def recover_from_error(self, error_context: ErrorContext) -> bool:
        """
        Attempt to recover from a configuration error.
        
        Args:
            error_context: Error context information
            
        Returns:
            True if recovery was successful
        """
        try:
            recovery_action = error_context.recovery_action
            
            if recovery_action == RecoveryAction.RESTORE_BACKUP:
                return self._restore_from_backup(error_context)
            
            elif recovery_action == RecoveryAction.RESET_TO_DEFAULTS:
                return self._reset_to_defaults(error_context)
            
            elif recovery_action == RecoveryAction.RETRY:
                # Retry is handled by the caller
                return True
            
            elif recovery_action == RecoveryAction.IGNORE:
                logger.warning(f"Ignoring error in {error_context.operation}: {error_context.error_message}")
                return True
            
            elif recovery_action == RecoveryAction.MANUAL_INTERVENTION:
                logger.error(f"Manual intervention required for {error_context.operation}: {error_context.error_message}")
                return False
            
            else:  # FAIL
                logger.error(f"No recovery possible for {error_context.operation}: {error_context.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            return False

    def add_error_callback(self, callback: Callable[[ErrorContext], None]) -> None:
        """
        Add a callback for error notifications.
        
        Args:
            callback: Function to call when errors occur
        """
        self._error_callbacks.append(callback)

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and trends.
        
        Returns:
            Error statistics dictionary
        """
        if not self._error_history:
            return {
                'total_errors': 0,
                'error_rate': 0.0,
                'most_common_errors': [],
                'recovery_success_rate': 0.0
            }
        
        # Calculate statistics
        total_errors = len(self._error_history)
        
        # Error counts by type
        error_counts = {}
        recovery_attempts = 0
        recovery_successes = 0
        
        for error_ctx in self._error_history:
            error_type = error_ctx.error_type
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            if error_ctx.recovery_action in [RecoveryAction.RESTORE_BACKUP, RecoveryAction.RESET_TO_DEFAULTS]:
                recovery_attempts += 1
                # Assume success if no subsequent errors of same type
                recovery_successes += 1  # Simplified for now
        
        # Most common errors
        most_common = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate error rate (errors per hour)
        if self._error_history:
            time_span = datetime.now() - self._error_history[0].timestamp
            hours = max(time_span.total_seconds() / 3600, 1)  # At least 1 hour
            error_rate = total_errors / hours
        else:
            error_rate = 0.0
        
        return {
            'total_errors': total_errors,
            'error_rate': error_rate,
            'most_common_errors': [{'type': error_type, 'count': count} for error_type, count in most_common],
            'recovery_success_rate': recovery_successes / recovery_attempts if recovery_attempts > 0 else 0.0,
            'error_counts_by_type': error_counts,
            'recent_errors': len([e for e in self._error_history if datetime.now() - e.timestamp < timedelta(hours=1)])
        }

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent error information.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error information
        """
        recent_errors = self._error_history[-limit:] if limit > 0 else self._error_history
        
        return [
            {
                'error_type': error_ctx.error_type,
                'error_message': error_ctx.error_message,
                'operation': error_ctx.operation,
                'timestamp': error_ctx.timestamp.isoformat(),
                'severity': error_ctx.severity.value,
                'recovery_action': error_ctx.recovery_action.value,
                'retry_count': error_ctx.retry_count
            }
            for error_ctx in reversed(recent_errors)
        ]

    # Private helper methods

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine the severity of an error"""
        if isinstance(error, ConfigurationCorruptionError):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ConfigurationLockError, ConfigurationBackupError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ConfigurationValidationError, ConfigurationMigrationError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _get_recovery_strategy(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """Get the appropriate recovery strategy for an error"""
        error_type = type(error)
        
        # Find the most specific handler
        for exception_type, handler in self._recovery_strategies.items():
            if issubclass(error_type, exception_type):
                return handler(error, context)
        
        # Default to generic handler
        return self._handle_generic_error(error, context)

    def _handle_store_error(self, error: ConfigurationStoreError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration store errors"""
        if "permission" in str(error).lower():
            return RecoveryAction.MANUAL_INTERVENTION
        elif "disk" in str(error).lower() or "space" in str(error).lower():
            return RecoveryAction.MANUAL_INTERVENTION
        elif context.retry_count < 2:
            return RecoveryAction.RETRY
        else:
            return RecoveryAction.RESTORE_BACKUP

    def _handle_lock_error(self, error: ConfigurationLockError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration lock errors"""
        if "timeout" in str(error).lower():
            if context.retry_count < 3:
                return RecoveryAction.RETRY
            else:
                # Force release stale locks
                if self.lock_manager:
                    try:
                        cleaned = self.lock_manager.cleanup_stale_locks()
                        if cleaned > 0:
                            return RecoveryAction.RETRY
                    except Exception:
                        pass
                return RecoveryAction.MANUAL_INTERVENTION
        else:
            return RecoveryAction.RETRY

    def _handle_backup_error(self, error: ConfigurationBackupError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration backup errors"""
        if "space" in str(error).lower():
            return RecoveryAction.MANUAL_INTERVENTION
        elif context.retry_count < 2:
            return RecoveryAction.RETRY
        else:
            return RecoveryAction.IGNORE  # Continue without backup

    def _handle_watch_error(self, error: ConfigurationWatchError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration watch errors"""
        return RecoveryAction.IGNORE  # Watching is not critical

    def _handle_validation_error(self, error: ConfigurationValidationError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration validation errors"""
        if context.severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.RESTORE_BACKUP
        else:
            return RecoveryAction.RESET_TO_DEFAULTS

    def _handle_migration_error(self, error: ConfigurationMigrationError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration migration errors"""
        return RecoveryAction.MANUAL_INTERVENTION

    def _handle_corruption_error(self, error: ConfigurationCorruptionError, context: ErrorContext) -> RecoveryAction:
        """Handle configuration corruption errors"""
        return RecoveryAction.RESTORE_BACKUP

    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """Handle generic configuration errors"""
        if context.retry_count < self.default_max_retries:
            return RecoveryAction.RETRY
        else:
            return RecoveryAction.FAIL

    def _restore_from_backup(self, error_context: ErrorContext) -> bool:
        """Restore configuration from backup"""
        if not self.backup_manager:
            logger.error("No backup manager available for recovery")
            return False
        
        try:
            # Get the most recent backup
            backups = self.backup_manager.list_backups(limit=1)
            if not backups:
                logger.error("No backups available for recovery")
                return False
            
            backup_id = backups[0]['backup_id']
            success = self.backup_manager.restore_backup(backup_id, error_context.context_data.get('config_file'))
            
            if success:
                logger.info(f"Successfully restored configuration from backup {backup_id}")
            else:
                logger.error(f"Failed to restore configuration from backup {backup_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during backup restoration: {e}")
            return False

    def _reset_to_defaults(self, error_context: ErrorContext) -> bool:
        """Reset configuration to defaults"""
        try:
            # This would need to be implemented by the calling code
            # as it requires access to the configuration module
            logger.warning("Configuration reset to defaults requested - manual implementation required")
            return False
            
        except Exception as e:
            logger.error(f"Error during configuration reset: {e}")
            return False

    def _notify_error_callbacks(self, error_context: ErrorContext) -> None:
        """Notify registered error callbacks"""
        for callback in self._error_callbacks:
            try:
                callback(error_context)
            except Exception as e:
                logger.warning(f"Error callback failed: {e}")

    def _cleanup_error_history(self) -> None:
        """Clean up old error history entries"""
        # Keep only last 1000 errors
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-500:]
        
        # Remove errors older than 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        self._error_history = [
            error_ctx for error_ctx in self._error_history
            if error_ctx.timestamp > cutoff_date
        ]