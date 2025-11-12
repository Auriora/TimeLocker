"""
Base validation classes for the ValidationFramework.

This module provides the foundation for all validators, including the base
Validator class, ValidationResult for reporting, and composite validators
for combining validation logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Callable, Dict
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    
    severity: ValidationSeverity
    field: str
    message: str
    code: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'severity': self.severity.value,
            'field': self.field,
            'message': self.message,
            'code': self.code,
            'context': self.context,
        }


@dataclass
class ValidationResult:
    """
    Result of validation operation.
    
    Provides comprehensive validation feedback including errors, warnings,
    and informational messages.
    """
    
    valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_ERROR",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an error to the validation result.
        
        Args:
            field: Field name that failed validation
            message: Error message
            code: Error code for programmatic handling
            context: Additional context information
        """
        self.valid = False
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))
    
    def add_warning(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_WARNING",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a warning to the validation result.
        
        Args:
            field: Field name
            message: Warning message
            code: Warning code
            context: Additional context information
        """
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))
    
    def add_info(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_INFO",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an informational message to the validation result.
        
        Args:
            field: Field name
            message: Info message
            code: Info code
            context: Additional context information
        """
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            field=field,
            message=message,
            code=code,
            context=context or {}
        ))
    
    def merge(self, other: 'ValidationResult') -> None:
        """
        Merge another validation result into this one.
        
        Args:
            other: ValidationResult to merge
        """
        if not other.valid:
            self.valid = False
        self.issues.extend(other.issues)
        self.metadata.update(other.metadata)
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all error issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def get_info(self) -> List[ValidationIssue]:
        """Get all info issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]
    
    def has_errors(self) -> bool:
        """Check if result has any errors."""
        return not self.valid
    
    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'valid': self.valid,
            'issues': [issue.to_dict() for issue in self.issues],
            'metadata': self.metadata,
        }
    
    def __bool__(self) -> bool:
        """Return True if validation passed."""
        return self.valid


class ValidationError(Exception):
    """
    Exception raised when validation fails.
    
    This exception includes the validation result for detailed error reporting.
    """
    
    def __init__(
        self,
        message: str,
        result: Optional[ValidationResult] = None,
        field: Optional[str] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            result: Optional validation result with details
            field: Optional field name that failed validation
        """
        super().__init__(message)
        self.result = result
        self.field = field
    
    def get_error_messages(self) -> List[str]:
        """Get all error messages from the validation result."""
        if self.result is not None:
            return [issue.message for issue in self.result.get_errors()]
        return [str(self)]


class Validator(ABC):
    """
    Base class for all validators.
    
    Validators implement the validate() method to check if a value meets
    specific criteria and return a ValidationResult.
    """
    
    def __init__(self, field_name: Optional[str] = None):
        """
        Initialize validator.
        
        Args:
            field_name: Optional field name for error reporting
        """
        self.field_name = field_name or "value"
    
    @abstractmethod
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate a value.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            ValidationResult with validation status and issues
        """
        pass
    
    def __call__(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Allow validator to be called as a function."""
        return self.validate(value, context)
    
    def __and__(self, other: 'Validator') -> 'CompositeValidator':
        """Combine validators with AND logic."""
        return CompositeValidator([self, other], require_all=True)
    
    def __or__(self, other: 'Validator') -> 'CompositeValidator':
        """Combine validators with OR logic."""
        return CompositeValidator([self, other], require_all=False)


class CompositeValidator(Validator):
    """
    Validator that combines multiple validators.
    
    Supports both AND (all must pass) and OR (at least one must pass) logic.
    """
    
    def __init__(
        self,
        validators: List[Validator],
        require_all: bool = True,
        field_name: Optional[str] = None
    ):
        """
        Initialize composite validator.
        
        Args:
            validators: List of validators to combine
            require_all: If True, all validators must pass (AND logic).
                        If False, at least one must pass (OR logic).
            field_name: Optional field name for error reporting
        """
        super().__init__(field_name)
        self.validators = validators
        self.require_all = require_all
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate value using all validators.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            ValidationResult combining all validator results
        """
        result = ValidationResult()
        
        if self.require_all:
            # AND logic: all validators must pass
            for validator in self.validators:
                validator_result = validator.validate(value, context)
                result.merge(validator_result)
        else:
            # OR logic: at least one validator must pass
            all_results = [v.validate(value, context) for v in self.validators]
            
            if any(r.valid for r in all_results):
                # At least one passed, so overall validation passes
                result.valid = True
                # Include warnings from all validators
                for r in all_results:
                    for issue in r.get_warnings():
                        result.issues.append(issue)
            else:
                # All failed, combine all errors
                result.valid = False
                for r in all_results:
                    result.merge(r)
        
        return result


class OptionalValidator(Validator):
    """
    Validator that allows None/empty values.
    
    Wraps another validator and only applies it if the value is not None/empty.
    """
    
    def __init__(
        self,
        validator: Validator,
        allow_empty: bool = True,
        field_name: Optional[str] = None
    ):
        """
        Initialize optional validator.
        
        Args:
            validator: Validator to apply if value is present
            allow_empty: If True, empty strings are also considered optional
            field_name: Optional field name for error reporting
        """
        super().__init__(field_name or validator.field_name)
        self.validator = validator
        self.allow_empty = allow_empty
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate value if present.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            ValidationResult
        """
        # Check if value is None or empty
        if value is None:
            return ValidationResult()
        
        if self.allow_empty and isinstance(value, str) and not value.strip():
            return ValidationResult()
        
        # Value is present, apply wrapped validator
        return self.validator.validate(value, context)


class ConditionalValidator(Validator):
    """
    Validator that only applies if a condition is met.
    
    Useful for context-dependent validation.
    """
    
    def __init__(
        self,
        validator: Validator,
        condition: Callable[[Any, Optional[Dict[str, Any]]], bool],
        field_name: Optional[str] = None
    ):
        """
        Initialize conditional validator.
        
        Args:
            validator: Validator to apply if condition is met
            condition: Function that determines if validation should be applied
            field_name: Optional field name for error reporting
        """
        super().__init__(field_name or validator.field_name)
        self.validator = validator
        self.condition = condition
    
    def validate(self, value: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate value if condition is met.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            ValidationResult
        """
        if self.condition(value, context):
            return self.validator.validate(value, context)
        
        # Condition not met, validation passes
        return ValidationResult()
