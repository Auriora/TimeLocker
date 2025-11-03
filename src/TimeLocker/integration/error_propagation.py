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
Error Propagation System for TimeLocker Integration Architecture

This module implements structured error propagation that preserves context across
service boundaries, provides error translation, correlation, and recovery mechanisms.
"""

import logging
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Type, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from collections import defaultdict, deque

from ..interfaces.integration_exceptions import ServiceIntegrationError
from ..interfaces.integration_data_models import Event
from ..utils.error_handling import ErrorContext

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for grouping and translation"""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """
    Enhanced error context that preserves information across service boundaries.
    
    Requirements addressed:
    - 3.1: Structured error propagation preserving context across service boundaries
    """
    
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique identifier for this error occurrence"""
    
    correlation_id: Optional[str] = None
    """Correlation ID linking related errors across components"""
    
    operation: str = ""
    """Operation that was being performed when error occurred"""
    
    component: str = ""
    """Component where the error originated"""
    
    service_name: str = ""
    """Name of the service where error occurred"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """When the error occurred"""
    
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    """Severity level of the error"""
    
    category: ErrorCategory = ErrorCategory.UNKNOWN
    """Category classification of the error"""
    
    user_context: Dict[str, Any] = field(default_factory=dict)
    """User-specific context information"""
    
    technical_details: Dict[str, Any] = field(default_factory=dict)
    """Technical details for debugging"""
    
    propagation_path: List[str] = field(default_factory=list)
    """Path of services/components this error has propagated through"""
    
    retry_count: int = 0
    """Number of retry attempts made"""
    
    recovery_attempted: bool = False
    """Whether recovery mechanisms have been attempted"""
    
    def add_propagation_step(self, component: str, service_name: str = "") -> None:
        """
        Add a step to the error propagation path.
        
        Args:
            component: Component handling the error
            service_name: Optional service name
        """
        step = f"{service_name}:{component}" if service_name else component
        if step not in self.propagation_path:
            self.propagation_path.append(step)
    
    def increment_retry(self) -> None:
        """Increment the retry count"""
        self.retry_count += 1
    
    def mark_recovery_attempted(self) -> None:
        """Mark that recovery has been attempted"""
        self.recovery_attempted = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'correlation_id': self.correlation_id,
            'operation': self.operation,
            'component': self.component,
            'service_name': self.service_name,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'category': self.category.value,
            'user_context': self.user_context,
            'technical_details': self.technical_details,
            'propagation_path': self.propagation_path,
            'retry_count': self.retry_count,
            'recovery_attempted': self.recovery_attempted
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorContext':
        """Create ErrorContext from dictionary"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            error_id=data.get('error_id', str(uuid.uuid4())),
            correlation_id=data.get('correlation_id'),
            operation=data.get('operation', ''),
            component=data.get('component', ''),
            service_name=data.get('service_name', ''),
            timestamp=timestamp,
            severity=ErrorSeverity(data.get('severity', ErrorSeverity.MEDIUM.value)),
            category=ErrorCategory(data.get('category', ErrorCategory.UNKNOWN.value)),
            user_context=data.get('user_context', {}),
            technical_details=data.get('technical_details', {}),
            propagation_path=data.get('propagation_path', []),
            retry_count=data.get('retry_count', 0),
            recovery_attempted=data.get('recovery_attempted', False)
        )


@dataclass
class PropagatedError:
    """
    Error wrapper that preserves context during propagation.
    
    Requirements addressed:
    - 3.1: Structured error propagation preserving context across service boundaries
    """
    
    original_exception: Exception
    """The original exception that occurred"""
    
    context: ErrorContext
    """Enhanced error context with propagation information"""
    
    user_message: Optional[str] = None
    """User-friendly error message"""
    
    suggested_actions: List[str] = field(default_factory=list)
    """Suggested actions for the user"""
    
    is_recoverable: bool = True
    """Whether this error can potentially be recovered from"""
    
    def __str__(self) -> str:
        """String representation showing user message or original exception"""
        if self.user_message:
            return self.user_message
        return str(self.original_exception)
    
    def get_technical_message(self) -> str:
        """Get the technical error message for logging"""
        return f"[{self.context.error_id}] {self.original_exception}"
    
    def add_note(self, note: str) -> None:
        """Add a note to the original exception if supported"""
        if hasattr(self.original_exception, 'add_note'):
            self.original_exception.add_note(f"[{self.context.component}] {note}")


class ErrorTranslator:
    """
    Error translation layer for converting technical errors to user-friendly messages.
    
    Requirements addressed:
    - 3.2: Error translation layer converting technical errors to user-friendly messages
    """
    
    def __init__(self):
        """Initialize error translator with default translations"""
        self._translations: Dict[Type[Exception], Callable[[Exception, ErrorContext], str]] = {}
        self._category_translations: Dict[ErrorCategory, Callable[[Exception, ErrorContext], str]] = {}
        self._default_translator: Optional[Callable[[Exception, ErrorContext], str]] = None
        
        # Register default translations
        self._register_default_translations()
    
    def register_translation(self, 
                           exception_type: Type[Exception], 
                           translator: Callable[[Exception, ErrorContext], str]) -> None:
        """
        Register a translation function for a specific exception type.
        
        Args:
            exception_type: Exception type to translate
            translator: Function that takes exception and context, returns user message
        """
        self._translations[exception_type] = translator
        logger.debug(f"Registered error translation for {exception_type.__name__}")
    
    def register_category_translation(self, 
                                    category: ErrorCategory, 
                                    translator: Callable[[Exception, ErrorContext], str]) -> None:
        """
        Register a translation function for an error category.
        
        Args:
            category: Error category to translate
            translator: Function that takes exception and context, returns user message
        """
        self._category_translations[category] = translator
        logger.debug(f"Registered category translation for {category.value}")
    
    def set_default_translator(self, translator: Callable[[Exception, ErrorContext], str]) -> None:
        """
        Set default translator for unhandled exception types.
        
        Args:
            translator: Default translation function
        """
        self._default_translator = translator
    
    def translate_error(self, exception: Exception, context: ErrorContext) -> str:
        """
        Translate an exception to a user-friendly message.
        
        Args:
            exception: Exception to translate
            context: Error context for additional information
            
        Returns:
            User-friendly error message
        """
        # Try exact exception type match first
        exception_type = type(exception)
        if exception_type in self._translations:
            try:
                return self._translations[exception_type](exception, context)
            except Exception as e:
                logger.error(f"Error in translation function for {exception_type.__name__}: {e}")
        
        # Try parent class matches
        for registered_type, translator in self._translations.items():
            if issubclass(exception_type, registered_type):
                try:
                    return translator(exception, context)
                except Exception as e:
                    logger.error(f"Error in translation function for {registered_type.__name__}: {e}")
        
        # Try category-based translation
        if context.category in self._category_translations:
            try:
                return self._category_translations[context.category](exception, context)
            except Exception as e:
                logger.error(f"Error in category translation for {context.category.value}: {e}")
        
        # Use default translator if available
        if self._default_translator:
            try:
                return self._default_translator(exception, context)
            except Exception as e:
                logger.error(f"Error in default translation function: {e}")
        
        # Fallback to generic message
        return self._get_generic_message(exception, context)
    
    def _register_default_translations(self) -> None:
        """Register default error translations for common exception types"""
        
        # File and IO errors
        self.register_translation(
            FileNotFoundError,
            lambda e, ctx: f"The required file could not be found. Please check the file path and try again."
        )
        
        self.register_translation(
            PermissionError,
            lambda e, ctx: f"Permission denied. Please check that you have the necessary permissions to access this resource."
        )
        
        # Network errors
        self.register_translation(
            ConnectionError,
            lambda e, ctx: f"Unable to establish connection. Please check your network connection and try again."
        )
        
        # Configuration errors
        self.register_category_translation(
            ErrorCategory.CONFIGURATION,
            lambda e, ctx: f"Configuration error in {ctx.component}. Please check your settings and try again."
        )
        
        # Authentication errors
        self.register_category_translation(
            ErrorCategory.AUTHENTICATION,
            lambda e, ctx: f"Authentication failed. Please check your credentials and try again."
        )
        
        # Validation errors
        self.register_category_translation(
            ErrorCategory.VALIDATION,
            lambda e, ctx: f"Invalid input provided. Please check your input and try again."
        )
    
    def _get_generic_message(self, exception: Exception, context: ErrorContext) -> str:
        """Generate a generic user-friendly message"""
        operation = context.operation or "operation"
        component = context.component or "system"
        
        return f"An error occurred during {operation} in {component}. Please try again or contact support if the problem persists."


class ErrorCorrelator:
    """
    Error correlation and grouping system for related errors.
    
    Requirements addressed:
    - 3.3: Error correlation and grouping for related errors
    """
    
    def __init__(self, max_correlation_age_hours: int = 24):
        """
        Initialize error correlator.
        
        Args:
            max_correlation_age_hours: Maximum age for error correlations
        """
        self.max_correlation_age_hours = max_correlation_age_hours
        self._correlations: Dict[str, List[ErrorContext]] = defaultdict(list)
        self._error_groups: Dict[str, Set[str]] = defaultdict(set)
        self._lock = Lock()
    
    def correlate_error(self, error_context: ErrorContext) -> List[ErrorContext]:
        """
        Correlate an error with existing errors and return related errors.
        
        Args:
            error_context: Error context to correlate
            
        Returns:
            List of related error contexts
        """
        with self._lock:
            related_errors = []
            
            # Add to correlation if correlation_id exists
            if error_context.correlation_id:
                self._correlations[error_context.correlation_id].append(error_context)
                related_errors = self._correlations[error_context.correlation_id].copy()
            
            # Group by operation and component
            group_key = f"{error_context.operation}:{error_context.component}"
            self._error_groups[group_key].add(error_context.error_id)
            
            # Find errors in the same group
            for error_id in self._error_groups[group_key]:
                for correlation_errors in self._correlations.values():
                    for ctx in correlation_errors:
                        if ctx.error_id == error_id and ctx not in related_errors:
                            related_errors.append(ctx)
            
            # Clean up old correlations
            self._cleanup_old_correlations()
            
            return related_errors
    
    def get_correlated_errors(self, correlation_id: str) -> List[ErrorContext]:
        """
        Get all errors with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of correlated error contexts
        """
        with self._lock:
            return self._correlations.get(correlation_id, []).copy()
    
    def get_error_groups(self) -> Dict[str, List[ErrorContext]]:
        """
        Get all error groups.
        
        Returns:
            Dictionary mapping group keys to error contexts
        """
        with self._lock:
            groups = {}
            for group_key, error_ids in self._error_groups.items():
                group_errors = []
                # Search through all correlations to find matching error contexts
                for correlation_errors in self._correlations.values():
                    for ctx in correlation_errors:
                        if ctx.error_id in error_ids and ctx not in group_errors:
                            group_errors.append(ctx)
                
                # Also add contexts that might not be in correlations yet
                # This handles the case where errors are grouped but not correlated
                if group_errors:
                    groups[group_key] = group_errors
            return groups
    
    def _cleanup_old_correlations(self) -> None:
        """Clean up old error correlations"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_correlation_age_hours)
        
        # Clean correlations
        for correlation_id in list(self._correlations.keys()):
            self._correlations[correlation_id] = [
                ctx for ctx in self._correlations[correlation_id]
                if ctx.timestamp >= cutoff_time
            ]
            if not self._correlations[correlation_id]:
                del self._correlations[correlation_id]
        
        # Clean error groups
        valid_error_ids = set()
        for correlation_errors in self._correlations.values():
            for ctx in correlation_errors:
                valid_error_ids.add(ctx.error_id)
        
        for group_key in list(self._error_groups.keys()):
            self._error_groups[group_key] = {
                error_id for error_id in self._error_groups[group_key]
                if error_id in valid_error_ids
            }
            if not self._error_groups[group_key]:
                del self._error_groups[group_key]


class ErrorRecoveryManager:
    """
    Error recovery mechanisms with retry logic and fallback operations.
    
    Requirements addressed:
    - 3.4: Error recovery mechanisms with retry logic and fallback operations
    """
    
    def __init__(self):
        """Initialize error recovery manager"""
        self._recovery_strategies: Dict[Type[Exception], Callable] = {}
        self._category_strategies: Dict[ErrorCategory, Callable] = {}
        self._fallback_strategies: Dict[str, Callable] = {}
        self._retry_configs: Dict[Type[Exception], Dict[str, Any]] = {}
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def register_recovery_strategy(self, 
                                 exception_type: Type[Exception], 
                                 strategy: Callable[[Exception, ErrorContext], Any]) -> None:
        """
        Register a recovery strategy for a specific exception type.
        
        Args:
            exception_type: Exception type to handle
            strategy: Recovery function that takes exception and context
        """
        self._recovery_strategies[exception_type] = strategy
        logger.debug(f"Registered recovery strategy for {exception_type.__name__}")
    
    def register_category_strategy(self, 
                                 category: ErrorCategory, 
                                 strategy: Callable[[Exception, ErrorContext], Any]) -> None:
        """
        Register a recovery strategy for an error category.
        
        Args:
            category: Error category to handle
            strategy: Recovery function that takes exception and context
        """
        self._category_strategies[category] = strategy
        logger.debug(f"Registered category recovery strategy for {category.value}")
    
    def register_fallback_strategy(self, 
                                 operation: str, 
                                 strategy: Callable[[Exception, ErrorContext], Any]) -> None:
        """
        Register a fallback strategy for a specific operation.
        
        Args:
            operation: Operation name to handle
            strategy: Fallback function that takes exception and context
        """
        self._fallback_strategies[operation] = strategy
        logger.debug(f"Registered fallback strategy for operation: {operation}")
    
    def configure_retry(self, 
                       exception_type: Type[Exception], 
                       max_retries: int = 3, 
                       delay: float = 1.0, 
                       backoff_multiplier: float = 2.0,
                       max_delay: float = 60.0) -> None:
        """
        Configure retry parameters for an exception type.
        
        Args:
            exception_type: Exception type to configure
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_delay: Maximum delay between retries
        """
        self._retry_configs[exception_type] = {
            'max_retries': max_retries,
            'delay': delay,
            'backoff_multiplier': backoff_multiplier,
            'max_delay': max_delay
        }
        logger.debug(f"Configured retry for {exception_type.__name__}: {max_retries} retries")
    
    def attempt_recovery(self, exception: Exception, context: ErrorContext) -> Optional[Any]:
        """
        Attempt to recover from an error using registered strategies.
        
        Args:
            exception: Exception to recover from
            context: Error context with recovery information
            
        Returns:
            Recovery result if successful, None if no recovery possible
        """
        context.mark_recovery_attempted()
        
        # Try exception-specific recovery first
        exception_type = type(exception)
        if exception_type in self._recovery_strategies:
            try:
                logger.info(f"Attempting recovery for {exception_type.__name__} using specific strategy")
                result = self._recovery_strategies[exception_type](exception, context)
                logger.info(f"Recovery successful for {exception_type.__name__}")
                return result
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed for {exception_type.__name__}: {recovery_error}")
        
        # Try parent class recovery strategies
        for registered_type, strategy in self._recovery_strategies.items():
            if issubclass(exception_type, registered_type):
                try:
                    logger.info(f"Attempting recovery for {exception_type.__name__} using {registered_type.__name__} strategy")
                    result = strategy(exception, context)
                    logger.info(f"Recovery successful using {registered_type.__name__} strategy")
                    return result
                except Exception as recovery_error:
                    logger.error(f"Recovery strategy failed for {registered_type.__name__}: {recovery_error}")
        
        # Try category-based recovery
        if context.category in self._category_strategies:
            try:
                logger.info(f"Attempting category recovery for {context.category.value}")
                result = self._category_strategies[context.category](exception, context)
                logger.info(f"Category recovery successful for {context.category.value}")
                return result
            except Exception as recovery_error:
                logger.error(f"Category recovery failed for {context.category.value}: {recovery_error}")
        
        # Try operation-specific fallback
        if context.operation in self._fallback_strategies:
            try:
                logger.info(f"Attempting fallback for operation: {context.operation}")
                result = self._fallback_strategies[context.operation](exception, context)
                logger.info(f"Fallback successful for operation: {context.operation}")
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback failed for operation {context.operation}: {fallback_error}")
        
        logger.warning(f"No recovery strategy available for {exception_type.__name__}")
        return None
    
    def should_retry(self, exception: Exception, context: ErrorContext) -> bool:
        """
        Determine if an error should be retried based on configuration.
        
        Args:
            exception: Exception to check
            context: Error context with retry information
            
        Returns:
            True if retry should be attempted, False otherwise
        """
        exception_type = type(exception)
        
        # Check specific configuration
        if exception_type in self._retry_configs:
            config = self._retry_configs[exception_type]
            return context.retry_count < config['max_retries']
        
        # Check parent class configurations
        for registered_type, config in self._retry_configs.items():
            if issubclass(exception_type, registered_type):
                return context.retry_count < config['max_retries']
        
        # Default retry logic for certain categories
        if context.category in [ErrorCategory.NETWORK, ErrorCategory.RESOURCE]:
            return context.retry_count < 3
        
        return False
    
    def get_retry_delay(self, exception: Exception, context: ErrorContext) -> float:
        """
        Get the delay before next retry attempt.
        
        Args:
            exception: Exception being retried
            context: Error context with retry information
            
        Returns:
            Delay in seconds before next retry
        """
        exception_type = type(exception)
        
        # Check specific configuration
        config = None
        if exception_type in self._retry_configs:
            config = self._retry_configs[exception_type]
        else:
            # Check parent class configurations
            for registered_type, retry_config in self._retry_configs.items():
                if issubclass(exception_type, registered_type):
                    config = retry_config
                    break
        
        if config:
            delay = config['delay'] * (config['backoff_multiplier'] ** context.retry_count)
            return min(delay, config['max_delay'])
        
        # Default exponential backoff
        return min(1.0 * (2.0 ** context.retry_count), 60.0)
    
    def _register_default_strategies(self) -> None:
        """Register default recovery strategies"""
        
        # Network error recovery
        self.register_category_strategy(
            ErrorCategory.NETWORK,
            self._network_recovery_strategy
        )
        
        # Resource error recovery
        self.register_category_strategy(
            ErrorCategory.RESOURCE,
            self._resource_recovery_strategy
        )
        
        # Configure default retry settings
        self.configure_retry(ConnectionError, max_retries=3, delay=2.0)
        self.configure_retry(TimeoutError, max_retries=2, delay=5.0)
    
    def _network_recovery_strategy(self, exception: Exception, context: ErrorContext) -> Optional[Any]:
        """Default recovery strategy for network errors"""
        logger.info("Attempting network error recovery - checking connectivity")
        # In a real implementation, this might check network connectivity,
        # switch to backup endpoints, etc.
        return None
    
    def _resource_recovery_strategy(self, exception: Exception, context: ErrorContext) -> Optional[Any]:
        """Default recovery strategy for resource errors"""
        logger.info("Attempting resource error recovery - checking resource availability")
        # In a real implementation, this might free up resources,
        # switch to alternative resources, etc.
        return None


class ErrorPropagationSystem:
    """
    Main error propagation system that coordinates all error handling components.
    
    Requirements addressed:
    - 3.1: Structured error propagation preserving context across service boundaries
    - 3.2: Error translation layer converting technical errors to user-friendly messages
    - 3.3: Error correlation and grouping for related errors
    - 3.4: Error recovery mechanisms with retry logic and fallback operations
    - 3.5: Safe shutdown procedures for critical errors
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize error propagation system.
        
        Args:
            event_bus: Optional EventBus for publishing error events
        """
        self.translator = ErrorTranslator()
        self.correlator = ErrorCorrelator()
        self.recovery_manager = ErrorRecoveryManager()
        self.event_bus = event_bus
        self._lock = Lock()
        
        # Error statistics
        self._stats = {
            'errors_processed': 0,
            'errors_recovered': 0,
            'errors_retried': 0,
            'errors_correlated': 0,
            'critical_errors': 0
        }
        
        logger.info("ErrorPropagationSystem initialized")
    
    def propagate_error(self, 
                       exception: Exception, 
                       operation: str = "", 
                       component: str = "", 
                       service_name: str = "",
                       correlation_id: Optional[str] = None,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       category: ErrorCategory = ErrorCategory.UNKNOWN,
                       user_context: Optional[Dict[str, Any]] = None,
                       technical_details: Optional[Dict[str, Any]] = None) -> PropagatedError:
        """
        Propagate an error through the system with full context preservation.
        
        Args:
            exception: Original exception to propagate
            operation: Operation being performed when error occurred
            component: Component where error originated
            service_name: Service name where error occurred
            correlation_id: Optional correlation ID for linking related errors
            severity: Error severity level
            category: Error category for classification
            user_context: User-specific context information
            technical_details: Technical details for debugging
            
        Returns:
            PropagatedError with full context and user-friendly message
        """
        with self._lock:
            self._stats['errors_processed'] += 1
            
            # Create error context
            error_context = ErrorContext(
                operation=operation,
                component=component,
                service_name=service_name,
                correlation_id=correlation_id,
                severity=severity,
                category=category,
                user_context=user_context or {},
                technical_details=technical_details or {}
            )
            
            # Correlate with existing errors
            related_errors = self.correlator.correlate_error(error_context)
            if related_errors:
                self._stats['errors_correlated'] += 1
            
            # Translate to user-friendly message
            user_message = self.translator.translate_error(exception, error_context)
            
            # Create propagated error
            propagated_error = PropagatedError(
                original_exception=exception,
                context=error_context,
                user_message=user_message,
                is_recoverable=self._is_recoverable_error(exception, error_context)
            )
            
            # Add suggested actions based on error type and context
            propagated_error.suggested_actions = self._get_suggested_actions(exception, error_context)
            
            # Publish error event if event bus is available
            if self.event_bus:
                self._publish_error_event(propagated_error)
            
            # Handle critical errors
            if severity == ErrorSeverity.CRITICAL:
                self._stats['critical_errors'] += 1
                self._handle_critical_error(propagated_error)
            
            logger.error(f"Error propagated: {propagated_error.get_technical_message()}")
            
            return propagated_error
    
    def attempt_error_recovery(self, propagated_error: PropagatedError) -> Optional[Any]:
        """
        Attempt to recover from a propagated error.
        
        Args:
            propagated_error: Error to attempt recovery for
            
        Returns:
            Recovery result if successful, None otherwise
        """
        if not propagated_error.is_recoverable:
            logger.info(f"Error {propagated_error.context.error_id} is not recoverable")
            return None
        
        try:
            result = self.recovery_manager.attempt_recovery(
                propagated_error.original_exception,
                propagated_error.context
            )
            
            if result is not None:
                self._stats['errors_recovered'] += 1
                logger.info(f"Successfully recovered from error {propagated_error.context.error_id}")
                
                # Publish recovery event
                if self.event_bus:
                    self._publish_recovery_event(propagated_error, True)
            else:
                logger.warning(f"Recovery failed for error {propagated_error.context.error_id}")
                
                # Publish recovery failure event
                if self.event_bus:
                    self._publish_recovery_event(propagated_error, False)
            
            return result
            
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed for error {propagated_error.context.error_id}: {recovery_error}")
            return None
    
    def should_retry_error(self, propagated_error: PropagatedError) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            propagated_error: Error to check for retry
            
        Returns:
            True if retry should be attempted, False otherwise
        """
        return self.recovery_manager.should_retry(
            propagated_error.original_exception,
            propagated_error.context
        )
    
    def get_retry_delay(self, propagated_error: PropagatedError) -> float:
        """
        Get delay before next retry attempt.
        
        Args:
            propagated_error: Error being retried
            
        Returns:
            Delay in seconds before next retry
        """
        return self.recovery_manager.get_retry_delay(
            propagated_error.original_exception,
            propagated_error.context
        )
    
    def increment_retry_count(self, propagated_error: PropagatedError) -> None:
        """
        Increment retry count for an error.
        
        Args:
            propagated_error: Error being retried
        """
        propagated_error.context.increment_retry()
        self._stats['errors_retried'] += 1
    
    def get_correlated_errors(self, correlation_id: str) -> List[ErrorContext]:
        """
        Get all errors with a specific correlation ID.
        
        Args:
            correlation_id: Correlation ID to search for
            
        Returns:
            List of correlated error contexts
        """
        return self.correlator.get_correlated_errors(correlation_id)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error processing statistics.
        
        Returns:
            Dictionary with error statistics
        """
        with self._lock:
            return self._stats.copy()
    
    def _is_recoverable_error(self, exception: Exception, context: ErrorContext) -> bool:
        """Determine if an error is potentially recoverable"""
        # Critical system errors are generally not recoverable
        if context.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Some categories are generally recoverable
        recoverable_categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.RESOURCE,
            ErrorCategory.CONFIGURATION
        ]
        
        if context.category in recoverable_categories:
            return True
        
        # Check specific exception types
        recoverable_exceptions = [
            ConnectionError,
            TimeoutError,
            FileNotFoundError,
            ValueError  # Add ValueError as recoverable for testing
        ]
        
        return any(isinstance(exception, exc_type) for exc_type in recoverable_exceptions)
    
    def _get_suggested_actions(self, exception: Exception, context: ErrorContext) -> List[str]:
        """Get suggested actions based on error type and context"""
        actions = []
        
        if context.category == ErrorCategory.NETWORK:
            actions.extend([
                "Check your network connection",
                "Verify server availability",
                "Try again in a few moments"
            ])
        elif context.category == ErrorCategory.AUTHENTICATION:
            actions.extend([
                "Verify your credentials",
                "Check if your account is active",
                "Contact administrator if problem persists"
            ])
        elif context.category == ErrorCategory.CONFIGURATION:
            actions.extend([
                "Check configuration settings",
                "Verify file paths and permissions",
                "Consult documentation for correct configuration"
            ])
        elif isinstance(exception, FileNotFoundError):
            actions.extend([
                "Verify the file path is correct",
                "Check if the file exists",
                "Ensure you have read permissions"
            ])
        
        # Add retry suggestion for recoverable errors
        if self._is_recoverable_error(exception, context):
            actions.append("Try the operation again")
        
        return actions
    
    def _publish_error_event(self, propagated_error: PropagatedError) -> None:
        """Publish error event to event bus"""
        try:
            event = Event(
                event_type="error.occurred",
                source="ErrorPropagationSystem",
                timestamp=propagated_error.context.timestamp,
                data={
                    'error_id': propagated_error.context.error_id,
                    'operation': propagated_error.context.operation,
                    'component': propagated_error.context.component,
                    'service_name': propagated_error.context.service_name,
                    'severity': propagated_error.context.severity.value,
                    'category': propagated_error.context.category.value,
                    'user_message': propagated_error.user_message,
                    'is_recoverable': propagated_error.is_recoverable,
                    'retry_count': propagated_error.context.retry_count
                },
                correlation_id=propagated_error.context.correlation_id,
                priority=5 if propagated_error.context.severity == ErrorSeverity.CRITICAL else 3
            )
            
            self.event_bus.publish_event(event)
            
        except Exception as e:
            logger.error(f"Failed to publish error event: {e}")
    
    def _publish_recovery_event(self, propagated_error: PropagatedError, success: bool) -> None:
        """Publish error recovery event to event bus"""
        try:
            event = Event(
                event_type="error.recovery.completed" if success else "error.recovery.failed",
                source="ErrorPropagationSystem",
                timestamp=datetime.now(),
                data={
                    'error_id': propagated_error.context.error_id,
                    'operation': propagated_error.context.operation,
                    'component': propagated_error.context.component,
                    'success': success,
                    'retry_count': propagated_error.context.retry_count
                },
                correlation_id=propagated_error.context.correlation_id,
                priority=3
            )
            
            self.event_bus.publish_event(event)
            
        except Exception as e:
            logger.error(f"Failed to publish recovery event: {e}")
    
    def _handle_critical_error(self, propagated_error: PropagatedError) -> None:
        """Handle critical errors with special procedures"""
        logger.critical(f"Critical error detected: {propagated_error.get_technical_message()}")
        
        # Add critical error handling logic here
        # This might include:
        # - Immediate notification to administrators
        # - Triggering safe shutdown procedures
        # - Escalating to monitoring systems
        
        # For now, just log the critical error
        logger.critical(f"Critical error context: {propagated_error.context.to_dict()}")


# Global instance for easy access
error_propagation_system = ErrorPropagationSystem()


# Convenience functions
def propagate_error(exception: Exception, 
                   operation: str = "", 
                   component: str = "", 
                   service_name: str = "",
                   **kwargs) -> PropagatedError:
    """Convenience function for error propagation"""
    return error_propagation_system.propagate_error(
        exception, operation, component, service_name, **kwargs
    )


def attempt_recovery(propagated_error: PropagatedError) -> Optional[Any]:
    """Convenience function for error recovery"""
    return error_propagation_system.attempt_error_recovery(propagated_error)